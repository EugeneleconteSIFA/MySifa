# Prompt Cursor — MyExpé : Parser Excel déterministe pour grilles tarifaires

## Contexte et règles absolues

MySifa est une app FastAPI + HTML/CSS/JS vanilla.
- Backend Python 3 / FastAPI — `main.py`
- Frontend HTML/CSS/JS généré en chaînes Python dans `app/web/*.py`
- DB SQLite — `data/production.db` (chemin dans `.env` via `DB_PATH`)
- **Dernière migration : v85** → les nouvelles commencent à **v86** (vérifier le max avant d'assigner)
- Conventions : `_migrate()` dans `app/core/database.py`, migrations numérotées et idempotentes
- Objet d'état `S`, `api()`, `escHtml`/`escAttr`, `showToast` (jamais `alert()`), variables CSS, pas d'emojis
- **Ne jamais modifier `DB_PATH` dans `.env`.** Ne jamais toucher à `data/production.db` directement.

---

## Objectif

Remplacer le bouton "Parser avec IA" de la fiche transporteur (onglet Tarifs) par un **parser openpyxl déterministe** capable de traiter les grilles Excel volumineuses (CEVA 2200+ lignes, TRANSBENELUX, Compte 100346) sans passer par l'API Anthropic.

Le endpoint IA existant (`POST /expe/transporteurs/{id}/tarif/parse`) est conservé tel quel — il reste utile pour les PDFs et les formats exotiques. On ajoute un **nouveau endpoint Excel** et on met à jour l'UI pour proposer les deux options selon le type de fichier.

---

## Fichiers concernés

| Fichier | Ce qui change |
|---|---|
| `app/routers/expe_departs.py` | Nouveau endpoint `POST /transporteurs/{id}/tarifs/parse-excel` |
| `app/web/expe_assets.py` | UI : remplacer "Parser avec IA" par "Parser (Excel)" si le fichier uploadé est .xlsx, garder "Parser avec IA" pour les PDFs |

**Aucune migration nécessaire** — on réutilise les tables `expe_tarifs` et `expe_tarifs_frais` existantes.

---

## Étape 1 — Nouveau endpoint `POST /transporteurs/{id}/tarifs/parse-excel`

Ajouter dans `app/routers/expe_departs.py`, **juste après** le endpoint `parse_tarif_ia` existant (vers la ligne 1098).

**Logique complète** (copier-coller et adapter) :

```python
@router.post("/transporteurs/{transporteur_id}/tarifs/parse-excel")
async def parse_tarif_excel(request: Request, transporteur_id: int):
    """
    Parser déterministe openpyxl pour grilles tarifaires Excel.
    Ne dépend pas de l'API Anthropic — traite les fichiers volumineux (2000+ lignes).
    Formats reconnus : Compte 100346, CEVA Logistics, TRANSBENELUX, générique.
    """
    user = _require_expe_write(request)

    with get_db() as conn:
        trp = conn.execute(
            "SELECT * FROM expe_transporteurs WHERE id=?", (transporteur_id,)
        ).fetchone()
    if not trp:
        raise HTTPException(status_code=404, detail="Transporteur introuvable")
    if not trp["tarif_url"]:
        raise HTTPException(status_code=400, detail="Aucun fichier tarif uploadé pour ce transporteur")

    filepath = _resolve_tarif_path(trp["tarif_url"])
    if not filepath:
        raise HTTPException(status_code=404, detail="Fichier tarif introuvable sur le disque")

    ext = os.path.splitext(filepath)[1].lower()
    if ext not in (".xlsx", ".xls"):
        raise HTTPException(
            status_code=400,
            detail=f"Ce endpoint ne traite que les fichiers Excel (.xlsx). Fichier reçu : {ext}. "
                   "Utilisez le bouton 'Parser avec IA' pour les PDFs."
        )

    try:
        import openpyxl
        import math
    except ImportError:
        raise HTTPException(status_code=503, detail="openpyxl non installé — lancer : pip install openpyxl")

    wb = openpyxl.load_workbook(filepath, data_only=True)
    source_name = trp["tarif_filename"] or os.path.basename(trp["tarif_url"])

    # ── Détection de format ────────────────────────────────────────────────
    fmt = _detect_tarif_format(wb)

    if fmt == "compte100346":
        lignes_data, frais_data = _parse_compte100346(wb, source_name)
    elif fmt == "ceva":
        lignes_data, frais_data = _parse_ceva(wb, source_name)
    elif fmt == "transbenelux":
        lignes_data, frais_data = _parse_transbenelux(wb, source_name)
    else:
        # Format non reconnu : retourner la structure pour diagnostic
        structure = []
        for ws in wb.worksheets:
            preview = []
            for r in range(1, min(6, ws.max_row + 1)):
                row_vals = [str(ws.cell(row=r, column=c).value or "")[:30]
                            for c in range(1, min(ws.max_column + 1, 8))]
                preview.append(row_vals)
            structure.append({"sheet": ws.title, "preview": preview})
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Format non reconnu automatiquement. Voici la structure du fichier.",
                "structure": structure,
                "hint": "Communiquer la structure à l'équipe pour ajouter le support de ce format."
            }
        )

    if not lignes_data:
        raise HTTPException(
            status_code=422,
            detail=f"Format '{fmt}' détecté mais aucune ligne extraite. Vérifier le fichier."
        )

    now = datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")
    email = user.get("email") or user.get("identifiant")

    with get_db() as conn:
        for lg in lignes_data:
            conn.execute(
                """INSERT INTO expe_tarifs
                   (transporteur_id, type_envoi, base_calcul, zone_type, zone_valeur,
                    tranche_min, tranche_max, prix, unite, mini_perception,
                    actif, source_filename, created_at, created_by_email)
                   VALUES (?,?,?,?,?,?,?,?,?,?,0,?,?,?)""",
                (
                    transporteur_id,
                    lg.get("type_envoi"), lg.get("base_calcul"),
                    lg.get("zone_type"), lg.get("zone_valeur"),
                    lg.get("tranche_min", 0), lg.get("tranche_max"),
                    lg.get("prix", 0), lg.get("unite"),
                    lg.get("mini_perception"),
                    source_name, now, email,
                ),
            )
        for fr in frais_data:
            conn.execute(
                """INSERT OR IGNORE INTO expe_tarifs_frais
                   (transporteur_id, libelle, mode, valeur, mini, applique_defaut)
                   VALUES (?,?,?,?,?,?)""",
                (
                    transporteur_id,
                    fr.get("libelle"), fr.get("mode"),
                    fr.get("valeur", 0), fr.get("mini"),
                    fr.get("applique_defaut", 1),
                ),
            )
        conn.commit()

    return {
        "format_detecte": fmt,
        "lignes_extraites": len(lignes_data),
        "frais_extraits": len(frais_data),
        "actif": 0,
        "apercu_lignes": lignes_data[:10],
        "message": f"{len(lignes_data)} lignes extraites (format {fmt}) — à valider avant activation.",
    }
```

---

## Étape 2 — Fonctions de parsing à ajouter dans `app/routers/expe_departs.py`

Ajouter **juste avant** le endpoint `parse_tarif_excel` (ou dans une section utilitaires vers le haut du fichier, après les autres helpers `_`).

### 2.1 — Helpers communs

```python
def _tarif_float(v, default=None):
    """Convertit une valeur de cellule en float, None si impossible."""
    import math as _math
    try:
        f = float(str(v).strip().replace(",", "."))
        return None if _math.isnan(f) else f
    except Exception:
        return default


def _tarif_dept_from_label(label):
    """
    Extrait le code département depuis des formats variés :
      '(59) NORD'  →  '59'
      '59 - NORD'  →  '59'
      'FR59'       →  '59'
      '02'         →  '02'
    """
    s = str(label or "").strip()
    # Format (XX) NOM
    m = re.search(r"\((\w{1,3})\)", s)
    if m:
        code = m.group(1)
        return code.upper() if code.upper() in ("2A", "2B") else code.zfill(2)
    # Format FRXX ou FR2A
    m = re.match(r"^FR(\w{2,3})$", s.upper())
    if m:
        code = m.group(1)
        return code.upper() if code.upper() in ("2A", "2B") else code.lstrip("0").zfill(2)
    # Format XX - NOM
    m = re.match(r"^(\d{2,3})\s*[-–]?\s*", s)
    if m:
        code = m.group(1)
        return code.zfill(2) if len(code) <= 3 else None
    return None


def _tarif_unite_norm(v):
    s = str(v or "").strip().upper()
    if "100" in s:
        return "au_100kg"
    if "KG" in s and "100" not in s:
        return "au_kg"
    return "forfait"


def _tarif_find_header_row(ws, keywords, max_scan=40):
    """Retourne le numéro de la première ligne contenant un keyword (insensible à la casse)."""
    keywords_up = [k.upper() for k in keywords]
    for r in range(1, max_scan + 1):
        for c in range(1, min(ws.max_column + 1, 20)):
            val = str(ws.cell(row=r, column=c).value or "").upper()
            if any(k in val for k in keywords_up):
                return r
    return None
```

### 2.2 — Détection de format

```python
def _detect_tarif_format(wb):
    """
    Détecte le format de la grille tarifaire en examinant noms de feuilles + cellules clés.
    Retourne : 'compte100346' | 'ceva' | 'transbenelux' | 'generique'
    """
    sheet_names = " | ".join(ws.title.upper() for ws in wb.worksheets)

    # CEVA : feuilles contenant MESSAGERIE ou SMARTPAL ou CONDITIONS
    if any(k in sheet_names for k in ("MESSAGERIE", "SMARTPAL", "SMART PAL", "CONDITIONS COMMERCIALES")):
        return "ceva"

    # TRANSBENELUX
    if any(k in sheet_names for k in ("BENELUX", "TRANSBENELUX", "SIFA VERS FRANCE")):
        return "transbenelux"

    # Compte 100346 : A8 contient "POIDS" ou "PALETTE"
    for ws in wb.worksheets:
        a8 = str(ws["A8"].value or "").upper()
        if "POIDS" in a8 or "PALETTE" in a8:
            return "compte100346"

    return "generique"
```

### 2.3 — Parser Compte 100346

```python
def _parse_compte100346(wb, source_filename):
    """
    Format SIFA 010126 - P U (Compte 100346) :
    - Feuille avec A8 = "POIDS" ou "PALETTE"
    - Ligne 10 : bornes basses (DE)
    - Ligne 11 : bornes hautes (A)
    - Ligne 12 : unité (Forfait / Prx/100Kg)
    - Données à partir de la ligne 13
    - Col A : "(XX) NOM DÉPARTEMENT"
    """
    rows = []
    for ws in wb.worksheets:
        a8 = str(ws["A8"].value or "").upper()
        if "POIDS" in a8:
            base_calcul, type_envoi = "poids", "messagerie"
        elif "PALETTE" in a8:
            base_calcul, type_envoi = "palette", "messagerie"
        else:
            continue

        cols = []
        for c in range(3, ws.max_column + 1):
            tmax = _tarif_float(ws.cell(row=11, column=c).value)
            if tmax is None:
                continue
            tmin = _tarif_float(ws.cell(row=10, column=c).value, default=0)
            unite = _tarif_unite_norm(ws.cell(row=12, column=c).value)
            cols.append((c, tmin, tmax, unite))

        for r in range(13, ws.max_row + 1):
            dept = _tarif_dept_from_label(ws.cell(row=r, column=1).value)
            if not dept:
                continue
            for (c, tmin, tmax, unite) in cols:
                price = _tarif_float(ws.cell(row=r, column=c).value)
                if price is None:
                    continue
                rows.append({
                    "type_envoi": type_envoi,
                    "base_calcul": base_calcul,
                    "zone_type": "departement",
                    "zone_valeur": dept,
                    "tranche_min": tmin,
                    "tranche_max": int(tmax) if base_calcul == "palette" else tmax,
                    "prix": round(price, 4),
                    "unite": unite,
                    "mini_perception": None,
                    "source_filename": source_filename,
                })

    return rows, []
```

### 2.4 — Parser CEVA

```python
def _parse_ceva(wb, source_filename):
    rows = []
    frais = []
    for ws in wb.worksheets:
        t = ws.title.upper().replace(" ", "")
        if "MESSAGERIE" in t or ("TARIF" in t and "GN" in t):
            rows += _parse_ceva_messagerie(ws, source_filename)
        elif "PALETTE" in t or "SMARTPAL" in t or "SMART" in t:
            rows += _parse_ceva_palettes(ws, source_filename)
        elif "CONDITION" in t or "COMMERCIALE" in t or "ANNEXE" in t:
            frais += _parse_ceva_frais(ws)
    return rows, frais


def _parse_ceva_messagerie(ws, source_filename):
    rows = []
    header_row = _tarif_find_header_row(
        ws, ["DÉPARTEMENT", "DEPARTEMENT", "ZONE", "CODE POSTAL", "CP"]
    )
    if header_row is None:
        return rows

    cols = []
    for c in range(2, ws.max_column + 1):
        val = str(ws.cell(row=header_row, column=c).value or "").strip()
        if not val:
            continue
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*[-àaÀ]\s*(\d+(?:[.,]\d+)?)", val)
        if m:
            tmin = _tarif_float(m.group(1), 0)
            tmax = _tarif_float(m.group(2))
            unite = "forfait" if (tmax is not None and tmax <= 100) else "au_100kg"
            cols.append((c, tmin, tmax, unite))

    for r in range(header_row + 1, ws.max_row + 1):
        zone_lbl = str(ws.cell(row=r, column=1).value or "").strip()
        if not zone_lbl:
            continue
        dept = _tarif_dept_from_label(zone_lbl)
        cp_m = re.match(r"^(\d{5})\b", zone_lbl)
        if dept:
            zone_type, zone_valeur = "departement", dept
        elif cp_m:
            zone_type, zone_valeur = "code_postal", cp_m.group(1)
        else:
            continue
        for (c, tmin, tmax, unite) in cols:
            if tmin is None:
                continue
            price = _tarif_float(ws.cell(row=r, column=c).value)
            if price is None:
                continue
            rows.append({
                "type_envoi": "messagerie",
                "base_calcul": "poids",
                "zone_type": zone_type,
                "zone_valeur": zone_valeur,
                "tranche_min": tmin,
                "tranche_max": tmax,
                "prix": round(price, 4),
                "unite": unite,
                "mini_perception": None,
                "source_filename": source_filename,
            })
    return rows


def _parse_ceva_palettes(ws, source_filename):
    rows = []
    header_row = _tarif_find_header_row(ws, ["DÉPARTEMENT", "DEPARTEMENT", "ZONE", "PALETTE", "PAL"])
    if header_row is None:
        return rows
    cols = []
    for c in range(2, ws.max_column + 1):
        val = str(ws.cell(row=header_row, column=c).value or "").strip()
        m = re.match(r"^(\d+)\s*(?:palette|pal\.?)?$", val, re.IGNORECASE)
        if m:
            nb = int(m.group(1))
            if 1 <= nb <= 20:
                cols.append((c, nb))
    if not cols:
        cols = [(c, i) for i, c in enumerate(range(2, min(ws.max_column + 1, 7)), start=1)]
    for r in range(header_row + 1, ws.max_row + 1):
        dept = _tarif_dept_from_label(ws.cell(row=r, column=1).value)
        if not dept:
            continue
        for (c, nb) in cols:
            price = _tarif_float(ws.cell(row=r, column=c).value)
            if price is None:
                continue
            rows.append({
                "type_envoi": "messagerie",
                "base_calcul": "palette",
                "zone_type": "departement",
                "zone_valeur": dept,
                "tranche_min": nb,
                "tranche_max": nb,
                "prix": round(price, 4),
                "unite": "forfait",
                "mini_perception": None,
                "source_filename": source_filename,
            })
    return rows


def _parse_ceva_frais(ws):
    frais = []
    PATTERNS = [
        (r"gasoil|carburant|fuel",               "Gasoil",                   "pct_transport",       1),
        (r"sûreté|surete|sécurité|securite",     "Taxe sûreté/sécurité",     "forfait_expedition",  1),
        (r"prise.{0,10}rdv|rendez.{0,5}vous",   "Prise de RDV",             "forfait_expedition",  0),
        (r"hayon|tail.?lift",                    "Hayon",                    "par_palette",          0),
        (r"ville.{0,15}excentr",                 "Ville excentrée",          "forfait_expedition",  0),
        (r"co2|contribution",                    "CO2",                      "forfait_expedition",  1),
        (r"centre.{0,10}urbain|urban",           "Centres urbains",          "forfait_expedition",  0),
    ]
    seen = set()
    for r in range(1, ws.max_row + 1):
        for c in range(1, min(ws.max_column + 1, 10)):
            cell = str(ws.cell(row=r, column=c).value or "").strip()
            if not cell:
                continue
            for pattern, libelle, mode, defaut in PATTERNS:
                if libelle in seen:
                    continue
                if re.search(pattern, cell, re.IGNORECASE):
                    for cc in range(c + 1, min(c + 6, ws.max_column + 1)):
                        val = _tarif_float(ws.cell(row=r, column=cc).value)
                        if val is not None and val > 0:
                            frais.append({"libelle": libelle, "mode": mode,
                                          "valeur": val, "mini": None, "applique_defaut": defaut})
                            seen.add(libelle)
                            break
                    break
    return frais
```

### 2.5 — Parser TRANSBENELUX

```python
def _parse_transbenelux(wb, source_filename):
    rows = []
    for ws in wb.worksheets:
        header_row = _tarif_find_header_row(ws, ["PALETTE", "PAL", "FRANCE", "DÉPARTEMENT"])
        if header_row is None:
            continue
        cols = []
        for c in range(2, ws.max_column + 1):
            val = str(ws.cell(row=header_row, column=c).value or "").strip()
            m = re.fullmatch(r"(\d{1,2})", val)
            if m:
                nb = int(m.group(1))
                if 1 <= nb <= 20:
                    cols.append((c, nb))
        if not cols:
            continue
        for r in range(header_row + 1, ws.max_row + 1):
            dept = _tarif_dept_from_label(ws.cell(row=r, column=1).value)
            if not dept:
                continue
            for (c, nb) in cols:
                raw = str(ws.cell(row=r, column=c).value or "").strip().upper()
                if raw in ("", "FO", "PU", "PP", "-", "NC", "N/A"):
                    continue
                price = _tarif_float(raw)
                if price is None or price <= 0:
                    continue
                rows.append({
                    "type_envoi": "affretement" if nb > 6 else "messagerie",
                    "base_calcul": "palette",
                    "zone_type": "departement",
                    "zone_valeur": dept,
                    "tranche_min": nb,
                    "tranche_max": nb,
                    "prix": round(price, 4),
                    "unite": "forfait",
                    "mini_perception": None,
                    "source_filename": source_filename,
                })
    return rows, []
```

---

## Étape 3 — Mise à jour de l'UI dans `app/web/expe_assets.py`

### 3.1 — Logique de choix du bouton de parsing

Dans la fonction qui rend les actions de l'onglet Tarifs (chercher `Parser avec IA` dans `expe_assets.py`), remplacer le bouton unique par une logique qui choisit le bon endpoint selon l'extension du fichier uploadé.

Le transporteur courant en édition est `T.editId`. Son `tarif_filename` est dans `T.data` ou chargé depuis `S.transporteurs`.

**Pattern à appliquer :**

```js
// Déterminer si le fichier uploadé est un Excel ou un PDF
function _tarifsFileExt() {
  const trp = (S.transporteurs || []).find(t => Number(t.id) === Number(T.editId));
  const fname = (trp && (trp.tarif_filename || trp.tarif_url)) || '';
  const ext = fname.split('.').pop().toLowerCase();
  return ext;
}

async function parserTarifs() {
  const ext = _tarifsFileExt();
  const isExcel = ['xlsx', 'xls'].includes(ext);
  const endpoint = isExcel
    ? '/api/expe/transporteurs/' + T.editId + '/tarifs/parse-excel'
    : '/api/expe/transporteurs/' + T.editId + '/tarif/parse';

  const btn = document.getElementById('btn-parser-tarif');
  if (btn) btn.disabled = true;
  const label = isExcel ? 'Analyse Excel en cours...' : 'Analyse IA en cours...';
  if (btn) btn.textContent = label;

  try {
    const data = await api(endpoint, { method: 'POST' });
    showToast(data.message || 'Extraction terminée.', 'success');
    await loadTarifsTransporteur(T.editId);
  } catch (e) {
    const detail = e?.detail;
    if (detail && typeof detail === 'object' && detail.structure) {
      // Format non reconnu : afficher la structure dans un toast d'erreur
      showToast('Format non reconnu. Contacter l\'équipe pour ajouter le support de ce format.', 'danger');
      console.error('Structure du fichier :', detail.structure);
    } else {
      showToast(String(detail || e?.message || 'Erreur lors du parsing.'), 'danger');
    }
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = isExcel ? 'Parser (Excel)' : 'Parser avec IA';
    }
  }
}
```

### 3.2 — Mise à jour du label du bouton

Dans le rendu de l'onglet Tarifs (zone des boutons d'action), remplacer le texte du bouton "Parser avec IA" par un texte dynamique :

```js
// AVANT :
h('button', { type:'button', className:'btn btn-ghost', onClick:()=>parserTarifIA() }, 'Parser avec IA')

// APRÈS (id ajouté pour manipulation dynamique) :
h('button', {
  type: 'button',
  id: 'btn-parser-tarif',
  className: 'btn btn-ghost',
  onClick: () => parserTarifs()
}, ['xlsx','xls'].includes(_tarifsFileExt()) ? 'Parser (Excel)' : 'Parser avec IA')
```

---

## Étape 4 — Vérification `openpyxl` dans `requirements.txt`

Vérifier que `openpyxl` est présent dans `requirements.txt`. Si non, l'ajouter :

```
openpyxl>=3.1.0
```

---

## Résumé des fichiers modifiés

| Fichier | Ce qui change |
|---|---|
| `app/routers/expe_departs.py` | Helpers `_tarif_*` + parsers `_parse_*` + endpoint `parse-excel` |
| `app/web/expe_assets.py` | Fonction `parserTarifs()` + bouton dynamique Excel/IA |
| `requirements.txt` | Vérifier `openpyxl` présent |

**Aucune migration DB.** Aucune modification de `config.py`. Aucun changement à `main.py`.

---

## Vérification finale

Après implémentation, tester dans cet ordre :

1. Lancer l'app (`uvicorn main:app --reload`) — aucune erreur au démarrage.
2. Ouvrir la fiche d'un transporteur ayant un fichier `.xlsx` uploadé → onglet Tarifs → le bouton affiche "Parser (Excel)".
3. Cliquer "Parser (Excel)" → vérifier le toast succès avec le nombre de lignes.
4. Vérifier que les lignes apparaissent dans la section Brouillons.
5. Ouvrir la fiche d'un transporteur ayant un `.pdf` uploadé → onglet Tarifs → le bouton affiche "Parser avec IA".
6. Tester avec un fichier format inconnu → vérifier que le toast d'erreur s'affiche (pas de crash serveur).

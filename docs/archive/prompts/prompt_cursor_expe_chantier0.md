# Prompt Cursor — MyExpé Chantier 0 : Fondation tarifs structurés

## Contexte et règles absolues

MySifa est une app FastAPI + HTML/CSS/JS vanilla. Stack :
- Backend Python 3 / FastAPI — point d'entrée `main.py`
- Frontend HTML/CSS/JS généré en chaînes Python dans `app/web/*.py`
- DB SQLite — fichier actif : `data/production.db` (chemin dans `.env` via `DB_PATH`)
- Migrations dans `app/core/database.py`, fonction `_migrate()`, versionnées dans `schema_migrations`
- **Dernière migration : v61** (`postits_hidden`) → les nouvelles commencent à **v62**
- Conventions : objet d'état `S`, fonction `api(path, options)`, `escHtml`/`escAttr`, `showToast` (jamais `alert()`), variables CSS, pas d'emojis dans les messages/toasts/labels

**Ne jamais modifier `DB_PATH` dans `.env`. Ne jamais toucher à `data/production.db` directement.**

---

## Fichiers concernés par ce chantier

| Fichier | Rôle |
|---|---|
| `app/core/database.py` | Migrations v62, v63, v64 |
| `app/services/expe_transporteurs_seed.py` | Mettre à jour les seeds avec les nouvelles colonnes |
| `app/web/expe_assets.py` | Supprimer `EXPE_TRP_META` (migré en base) |
| `app/routers/expe_departs.py` | Ajouter `transporteur_id` dans CRUD départs |
| `app/routers/expe_departs.py` | Nouveaux endpoints : import CSV, validation tarif, parse Anthropic |
| `app/web/expe_page.py` (ou fichier équivalent de la page MyExpé) | UI : onglet Tarifs dans la fiche transporteur |
| `config.py` | Ajouter `ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")` |

---

## Étape 1 — Dette technique : migrations v62 et v63

### Migration v62 — `expe_departs_transporteur_fk`

Dans `app/core/database.py`, ajouter après la dernière migration (v61) :

```python
if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=62 LIMIT 1").fetchone():
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(expe_departs)").fetchall()}
    if "transporteur_id" not in cols:
        conn.execute(
            "ALTER TABLE expe_departs ADD COLUMN transporteur_id INTEGER REFERENCES expe_transporteurs(id)"
        )
    conn.commit()
    _record_schema_migration(conn, 62, "expe_departs_transporteur_fk")
```

**Pas de back-fill automatique** — le champ reste NULL pour les départs existants. L'UI proposera de lier manuellement si besoin (hors scope de ce chantier).

### Migration v63 — `expe_transporteurs_capacites`

```python
if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=63 LIMIT 1").fetchone():
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(expe_transporteurs)").fetchall()}
    for col, defn in [
        ("palette_max",     "INTEGER"),
        ("poids_max_kg",    "REAL"),
        ("accepte_poids",   "INTEGER DEFAULT 1"),
        ("accepte_palette", "INTEGER DEFAULT 1"),
    ]:
        if col not in cols:
            conn.execute(f"ALTER TABLE expe_transporteurs ADD COLUMN {col} {defn}")
    conn.commit()
    _record_schema_migration(conn, 63, "expe_transporteurs_capacites")
```

---

## Étape 2 — Schéma tarifs : migration v64

### Migration v64 — `expe_tarifs_schema`

```python
if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=64 LIMIT 1").fetchone():
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS expe_tarifs (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            transporteur_id  INTEGER NOT NULL,
            type_envoi       TEXT NOT NULL,
            base_calcul      TEXT NOT NULL,
            zone_type        TEXT NOT NULL,
            zone_valeur      TEXT NOT NULL,
            tranche_min      REAL NOT NULL DEFAULT 0,
            tranche_max      REAL,
            prix             REAL NOT NULL,
            unite            TEXT NOT NULL,
            mini_perception  REAL,
            valid_from       TEXT,
            valid_to         TEXT,
            actif            INTEGER DEFAULT 0,
            source_filename  TEXT,
            created_at       TEXT,
            created_by_email TEXT,
            FOREIGN KEY (transporteur_id) REFERENCES expe_transporteurs(id)
        );
        CREATE INDEX IF NOT EXISTS idx_expe_tarifs_lookup
            ON expe_tarifs(transporteur_id, type_envoi, zone_type, zone_valeur, actif);

        CREATE TABLE IF NOT EXISTS expe_tarifs_frais (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            transporteur_id  INTEGER NOT NULL,
            libelle          TEXT NOT NULL,
            mode             TEXT NOT NULL,
            valeur           REAL NOT NULL,
            mini             REAL,
            applique_defaut  INTEGER DEFAULT 1,
            FOREIGN KEY (transporteur_id) REFERENCES expe_transporteurs(id)
        );
    """)
    conn.commit()
    _record_schema_migration(conn, 64, "expe_tarifs_schema")
```

**Valeurs autorisées (pour référence — ne pas ajouter de CHECK en DB, valider côté Python) :**
- `type_envoi` : `'messagerie'` | `'ramasse'` | `'affretement'` | `'express_intl'`
- `base_calcul` : `'poids'` | `'palette'` | `'metre_plancher'`
- `zone_type` : `'departement'` | `'code_postal'` | `'zone_intl'` | `'pays'`
- `unite` : `'forfait'` | `'au_100kg'` | `'au_kg'`
- `mode` (frais) : `'pct_transport'` | `'forfait_expedition'` | `'par_palette'`

---

## Étape 3 — Mettre à jour le seed transporteurs

Dans `app/services/expe_transporteurs_seed.py`, ajouter les champs capacité aux 4 entrées existantes :

```python
EXPE_TRANSPORTEURS_SEED = [
    {
        "nom": "Coupé",
        "taxe_carburant_pct": 12.8,
        # ... champs existants inchangés ...
        "palette_max": 5,
        "poids_max_kg": None,
        "accepte_poids": 1,
        "accepte_palette": 1,
    },
    {
        "nom": "Ceva",
        "taxe_carburant_pct": 12.8,
        # ...
        "palette_max": 4,
        "poids_max_kg": 2000.0,
        "accepte_poids": 1,
        "accepte_palette": 1,
    },
    {
        "nom": "Coquelle",
        "taxe_carburant_pct": 12.8,
        # ...
        "palette_max": 33,
        "poids_max_kg": None,
        "accepte_poids": 0,
        "accepte_palette": 1,
    },
    {
        "nom": "Dimotrans",
        "taxe_carburant_pct": 12.8,
        # ...
        "palette_max": 28,
        "poids_max_kg": None,
        "accepte_poids": 0,
        "accepte_palette": 1,
    },
]
```

La fonction `seed_expe_transporteurs_if_empty` insère uniquement si la table est vide — elle ne met pas à jour les lignes existantes. Ajouter une fonction séparée `update_expe_transporteurs_capacites(conn)` qui fait un `UPDATE ... WHERE nom=?` pour les 4 transporteurs avec les nouvelles colonnes, et appeler cette fonction depuis `_migrate()` dans le bloc v63 après le commit.

---

## Étape 4 — Supprimer `EXPE_TRP_META` de `expe_assets.py`

Dans `app/web/expe_assets.py`, lignes ~104-147 :

```js
// SUPPRIMER ce bloc entier :
const EXPE_TRP_META={
  'Coupé':{poids:true,palette:true,palMax:5},
  'Ceva':{poids:true,palette:true,palMax:4},
  'Coquelle':{palette:true,palMax:33},
  'Dimotrans':{palette:true,palMax:28}
};
```

Remplacer tous les usages de `EXPE_TRP_META[nom]` dans le même fichier par une lecture depuis `S.transporteurs` (l'objet transporteur venant de l'API, qui contient désormais `palette_max`, `accepte_poids`, `accepte_palette`).

Exemple de remplacement :
```js
// AVANT :
const m = EXPE_TRP_META[nom];
if (!m) return '';
if (m.palMax) out.push('Max ' + m.palMax + ' pal.');

// APRÈS (nom est le nom du transporteur, S.transporteurs est le tableau de l'API) :
const trp = (S.transporteurs || []).find(t => t.nom === nom);
if (!trp) return '';
if (trp.palette_max) out.push('Max ' + trp.palette_max + ' pal.');
```

---

## Étape 5 — Endpoints tarifs dans `app/routers/expe_departs.py`

Ajouter les 4 endpoints suivants. Tous nécessitent `_require_expe_write`.

### 5.1 — `GET /expe/transporteurs/{id}/tarifs`

Retourne les lignes `expe_tarifs` + `expe_tarifs_frais` du transporteur.

```python
@router.get("/transporteurs/{transporteur_id}/tarifs")
def list_tarifs(request: Request, transporteur_id: int):
    _require_expe(request)
    with get_db() as conn:
        lignes = conn.execute(
            "SELECT * FROM expe_tarifs WHERE transporteur_id=? ORDER BY type_envoi, zone_valeur, tranche_min",
            (transporteur_id,)
        ).fetchall()
        frais = conn.execute(
            "SELECT * FROM expe_tarifs_frais WHERE transporteur_id=? ORDER BY libelle",
            (transporteur_id,)
        ).fetchall()
        return {"lignes": [dict(r) for r in lignes], "frais": [dict(r) for r in frais]}
```

### 5.2 — `POST /expe/transporteurs/{id}/tarifs/import-csv`

Importe un CSV normalisé (colonnes : `type_envoi, base_calcul, zone_type, zone_valeur, tranche_min, tranche_max, prix, unite, mini_perception, valid_from, valid_to`) en lignes `expe_tarifs` avec `actif=0`.

```python
@router.post("/transporteurs/{transporteur_id}/tarifs/import-csv")
async def import_tarifs_csv(request: Request, transporteur_id: int, file: UploadFile = File(...)):
    user = _require_expe_write(request)
    import csv, io
    now = datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))  # utf-8-sig gère le BOM Excel

    COLS_OBLIGATOIRES = {"type_envoi","base_calcul","zone_type","zone_valeur","tranche_min","prix","unite"}
    rows = list(reader)
    if not rows:
        raise HTTPException(400, "CSV vide")
    if not COLS_OBLIGATOIRES.issubset(set(rows[0].keys())):
        raise HTTPException(400, f"Colonnes manquantes. Attendu : {', '.join(sorted(COLS_OBLIGATOIRES))}")

    inserted = 0
    with get_db() as conn:
        # Vérifier que le transporteur existe
        if not conn.execute("SELECT 1 FROM expe_transporteurs WHERE id=?", (transporteur_id,)).fetchone():
            raise HTTPException(404, "Transporteur introuvable")
        for row in rows:
            def _f(k): return row.get(k, "").strip() or None
            def _r(k): v=_f(k); return float(v) if v is not None else None
            conn.execute("""
                INSERT INTO expe_tarifs
                (transporteur_id, type_envoi, base_calcul, zone_type, zone_valeur,
                 tranche_min, tranche_max, prix, unite, mini_perception,
                 valid_from, valid_to, actif, source_filename, created_at, created_by_email)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,0,?,?,?)
            """, (
                transporteur_id,
                _f("type_envoi"), _f("base_calcul"), _f("zone_type"), _f("zone_valeur"),
                float(row.get("tranche_min","0") or 0),
                _r("tranche_max"), float(row.get("prix","0") or 0), _f("unite"),
                _r("mini_perception"), _f("valid_from"), _f("valid_to"),
                file.filename, now, user["email"]
            ))
            inserted += 1
        conn.commit()
    return {"inserted": inserted, "actif": 0, "message": f"{inserted} lignes importées en brouillon — à valider."}
```

### 5.3 — `POST /expe/transporteurs/{id}/tarifs/valider`

Passe les lignes `actif=0` du transporteur en `actif=1` (validation humaine).

Body JSON : `{ "ids": [1, 2, 3] }` — liste des IDs à activer. Si `ids` est vide ou absent, activer TOUTES les lignes `actif=0` du transporteur.

```python
@router.post("/transporteurs/{transporteur_id}/tarifs/valider")
def valider_tarifs(request: Request, transporteur_id: int, body: dict = Body(...)):
    _require_expe_write(request)
    ids = body.get("ids") or []
    with get_db() as conn:
        if ids:
            placeholders = ",".join("?" * len(ids))
            conn.execute(
                f"UPDATE expe_tarifs SET actif=1 WHERE transporteur_id=? AND id IN ({placeholders})",
                (transporteur_id, *ids)
            )
        else:
            conn.execute(
                "UPDATE expe_tarifs SET actif=1 WHERE transporteur_id=? AND actif=0",
                (transporteur_id,)
            )
        conn.commit()
        updated = conn.execute(
            "SELECT COUNT(*) AS n FROM expe_tarifs WHERE transporteur_id=? AND actif=1",
            (transporteur_id,)
        ).fetchone()["n"]
    return {"actives": updated}
```

### 5.4 — `POST /expe/transporteurs/{id}/tarif/parse`

Parsing IA : lit le fichier tarif déjà uploadé sur le transporteur (`tarif_url`), l'envoie à l'API Anthropic avec un prompt d'extraction structurée, insère le résultat en `actif=0`.

**Important :**
- La clé Anthropic vient de `config.ANTHROPIC_API_KEY` — jamais exposée au frontend.
- Utiliser le SDK `anthropic` (`pip install anthropic`).
- Pour un `.xlsx` : convertir en CSV texte avec `openpyxl` avant d'envoyer.
- Pour un `.pdf` : encoder en base64 et envoyer en `document` (type `application/pdf`).
- Insérer les lignes extraites en `actif=0`, retourner un aperçu des lignes parsées pour affichage dans l'UI de validation.

```python
@router.post("/transporteurs/{transporteur_id}/tarif/parse")
async def parse_tarif_ia(request: Request, transporteur_id: int):
    user = _require_expe_write(request)
    from config import ANTHROPIC_API_KEY
    if not ANTHROPIC_API_KEY:
        raise HTTPException(503, "Clé Anthropic non configurée — ajouter ANTHROPIC_API_KEY dans .env")

    with get_db() as conn:
        trp = conn.execute(
            "SELECT * FROM expe_transporteurs WHERE id=?", (transporteur_id,)
        ).fetchone()
        if not trp:
            raise HTTPException(404, "Transporteur introuvable")
        if not trp["tarif_url"]:
            raise HTTPException(400, "Aucun fichier tarif uploadé pour ce transporteur")

    # Lire le fichier
    import os, base64
    filepath = trp["tarif_url"]  # chemin relatif dans data/uploads/transporteurs/
    if not os.path.isfile(filepath):
        filepath = os.path.join("data/uploads/transporteurs", os.path.basename(trp["tarif_url"]))
    if not os.path.isfile(filepath):
        raise HTTPException(404, "Fichier tarif introuvable sur le disque")

    ext = os.path.splitext(filepath)[1].lower()

    # Préparer le contenu à envoyer à Anthropic
    if ext in (".xlsx", ".xls"):
        import openpyxl, io
        wb = openpyxl.load_workbook(filepath, data_only=True)
        parts = []
        for ws in wb.worksheets:
            parts.append(f"=== Feuille : {ws.title} ===")
            for row in ws.iter_rows(values_only=True):
                line = "\t".join("" if c is None else str(c) for c in row)
                if line.strip():
                    parts.append(line)
        file_text = "\n".join(parts)
        content_block = {"type": "text", "text": f"Voici la grille tarifaire au format texte (extrait Excel) :\n\n{file_text}"}
    elif ext == ".pdf":
        with open(filepath, "rb") as f:
            b64 = base64.standard_b64encode(f.read()).decode("utf-8")
        content_block = {
            "type": "document",
            "source": {"type": "base64", "media_type": "application/pdf", "data": b64}
        }
    else:
        raise HTTPException(400, f"Format non supporté : {ext}. Uploader un .xlsx ou .pdf.")

    # Prompt d'extraction structurée
    PROMPT_EXTRACTION = """Tu es un expert en tarification transport en France.
Analyse cette grille tarifaire et extrait TOUTES les lignes tarifaires au format JSON strict.

Retourne UNIQUEMENT un objet JSON avec deux clés :
- "lignes" : liste de lignes tarifaires
- "frais" : liste de frais annexes (gasoil, sûreté, hayon, RDV, etc.)

Chaque ligne tarifaire a ces champs (tous requis sauf mention) :
{
  "type_envoi": "messagerie" | "ramasse" | "affretement" | "express_intl",
  "base_calcul": "poids" | "palette" | "metre_plancher",
  "zone_type": "departement" | "code_postal" | "zone_intl" | "pays",
  "zone_valeur": "59" (numéro département) | "59200" (CP) | "7" (zone intl) | "DE" (pays),
  "tranche_min": 0,  (nombre, borne basse dans l'unité de base_calcul)
  "tranche_max": 10, (nombre ou null si illimité)
  "prix": 12.50,     (nombre)
  "unite": "forfait" | "au_100kg" | "au_kg",
  "mini_perception": 8.50 (nombre ou null)
}

Chaque frais annexe a ces champs :
{
  "libelle": "Gasoil",
  "mode": "pct_transport" | "forfait_expedition" | "par_palette",
  "valeur": 12.8,
  "mini": null,
  "applique_defaut": 1  (1 si toujours appliqué, 0 si optionnel)
}

Règles importantes :
- Si la grille est par poids avec des tranches forfait puis au 100kg : utilise unite="forfait" pour les tranches ≤ 100 kg et unite="au_100kg" pour les tranches > 100 kg.
- Si la grille est par palette : base_calcul="palette", unite="forfait" (le prix est le total pour N palettes).
- zone_valeur pour les départements français : toujours en 2 caractères ("01".."95", "2A", "2B") ou 3 pour DOM ("971".."976").
- Si une cellule est vide ou marquée "NC" / "-" : ignorer cette ligne.
- Extraire les frais depuis les onglets "Conditions commerciales" ou équivalents.

Ne retourne rien d'autre que le JSON.
"""

    import anthropic as _anthropic
    client = _anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=8192,
        messages=[{
            "role": "user",
            "content": [
                content_block,
                {"type": "text", "text": PROMPT_EXTRACTION}
            ]
        }]
    )

    import json
    raw = message.content[0].text.strip()
    # Nettoyer si le modèle a enveloppé dans ```json ... ```
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    data = json.loads(raw)

    now = datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")
    lignes_data = data.get("lignes", [])
    frais_data = data.get("frais", [])

    with get_db() as conn:
        for lg in lignes_data:
            conn.execute("""
                INSERT INTO expe_tarifs
                (transporteur_id, type_envoi, base_calcul, zone_type, zone_valeur,
                 tranche_min, tranche_max, prix, unite, mini_perception,
                 actif, source_filename, created_at, created_by_email)
                VALUES (?,?,?,?,?,?,?,?,?,?,0,?,?,?)
            """, (
                transporteur_id,
                lg.get("type_envoi"), lg.get("base_calcul"), lg.get("zone_type"), lg.get("zone_valeur"),
                lg.get("tranche_min", 0), lg.get("tranche_max"),
                lg.get("prix", 0), lg.get("unite"), lg.get("mini_perception"),
                trp["tarif_filename"] or trp["tarif_url"], now, user["email"]
            ))
        for fr in frais_data:
            # INSERT OR IGNORE pour éviter les doublons si on parse plusieurs fois
            conn.execute("""
                INSERT OR IGNORE INTO expe_tarifs_frais
                (transporteur_id, libelle, mode, valeur, mini, applique_defaut)
                VALUES (?,?,?,?,?,?)
            """, (
                transporteur_id,
                fr.get("libelle"), fr.get("mode"), fr.get("valeur", 0),
                fr.get("mini"), fr.get("applique_defaut", 1)
            ))
        conn.commit()

    return {
        "lignes_extraites": len(lignes_data),
        "frais_extraits": len(frais_data),
        "actif": 0,
        "apercu_lignes": lignes_data[:10],  # aperçu des 10 premières pour l'UI
        "message": f"{len(lignes_data)} lignes et {len(frais_data)} frais extraits — à valider avant activation."
    }
```

---

## Étape 6 — Ajouter `ANTHROPIC_API_KEY` dans `config.py`

Dans `config.py` (racine, source de vérité) :

```python
import os
# ... après les autres os.getenv ...
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
```

Ajouter `ANTHROPIC_API_KEY=` dans `.env` (vide pour l'instant — Eugène renseigne la valeur manuellement sur le VPS).

---

## Étape 7 — UI : onglet Tarifs dans la fiche transporteur

Dans la page MyExpé (fichier `app/web/expe_page.py` ou le fichier qui rend la section transporteurs), ajouter un onglet **"Tarifs"** dans la fiche/modal de chaque transporteur.

### 7.1 — Structure de l'onglet

L'onglet Tarifs contient 3 sections :

**Section A — Brouillons en attente de validation**

Tableau des lignes `actif=0` avec colonnes : Type, Base, Zone, Tranche, Prix, Unité, Mini. Au-dessus un bandeau d'avertissement :

```
Ces lignes sont en brouillon — elles ne sont PAS utilisées par le comparateur.
[Tout activer]  [Activer la sélection]
```

Chaque ligne a une checkbox pour la sélection individuelle. Le bouton "Tout activer" appelle `POST /expe/transporteurs/{id}/tarifs/valider` avec body `{}`. "Activer la sélection" envoie `{ "ids": [...] }`.

**Section B — Tarifs actifs**

Tableau des lignes `actif=1`, même colonnes, en lecture seule. Badge vert "Actif" dans le header.

**Section C — Frais annexes**

Tableau des `expe_tarifs_frais` : Libellé, Mode, Valeur, Mini, Inclus auto (checkbox).

### 7.2 — Actions disponibles en haut de l'onglet

```
[Importer CSV]   [Parser avec IA]   (si lignes actif=0 : bandeau validation)
```

**Bouton "Importer CSV"** : ouvre un `<input type="file" accept=".csv">`, lit le fichier, le poste en `multipart/form-data` sur `POST /expe/transporteurs/{id}/tarifs/import-csv`. Toast succès avec le nombre de lignes importées + message "Validez les lignes pour les activer."

**Bouton "Parser avec IA"** : appelle `POST /expe/transporteurs/{id}/tarif/parse`. Pendant l'appel, afficher un état de chargement sur le bouton ("Analyse en cours..."). Toast succès avec le nombre de lignes extraites. Rechargement de la liste des brouillons.

### 7.3 — Chargement des données

```js
async function loadTarifsTransporteur(transporteurId) {
  const data = await api('/expe/transporteurs/' + transporteurId + '/tarifs');
  S.tarifs_lignes = data.lignes || [];
  S.tarifs_frais = data.frais || [];
  renderTarifsOnglet();
}
```

Appeler `loadTarifsTransporteur(id)` à chaque ouverture de l'onglet Tarifs.

### 7.4 — Rendu du tableau (exemple pour les brouillons)

```js
function renderBrouillons() {
  const brouillons = S.tarifs_lignes.filter(l => l.actif === 0);
  if (!brouillons.length) return '<p style="color:var(--muted);font-size:13px">Aucun brouillon.</p>';
  const rows = brouillons.map(l => `
    <tr>
      <td><input type="checkbox" class="tarif-check" data-id="${escAttr(String(l.id))}"></td>
      <td>${escHtml(l.type_envoi)}</td>
      <td>${escHtml(l.base_calcul)}</td>
      <td>${escHtml(l.zone_type)} ${escHtml(l.zone_valeur)}</td>
      <td>${l.tranche_min} – ${l.tranche_max ?? '∞'}</td>
      <td>${l.prix}</td>
      <td>${escHtml(l.unite)}</td>
      <td>${l.mini_perception ?? '—'}</td>
    </tr>
  `).join('');
  return `<table class="data-table"><thead><tr>
    <th></th><th>Type</th><th>Base</th><th>Zone</th><th>Tranche</th><th>Prix</th><th>Unité</th><th>Mini perception</th>
  </tr></thead><tbody>${rows}</tbody></table>`;
}
```

---

## Résumé des fichiers à modifier

| Fichier | Ce qui change |
|---|---|
| `app/core/database.py` | Migrations v62, v63, v64 |
| `app/services/expe_transporteurs_seed.py` | Ajout `palette_max`, `poids_max_kg`, `accepte_poids`, `accepte_palette` dans le seed + `update_expe_transporteurs_capacites()` |
| `app/web/expe_assets.py` | Suppression de `EXPE_TRP_META`, remplacement par lecture depuis `S.transporteurs` |
| `app/routers/expe_departs.py` | 4 nouveaux endpoints tarifs (list, import-csv, valider, parse) |
| `app/web/expe_page.py` (ou équivalent) | Onglet Tarifs dans la fiche transporteur |
| `config.py` | `ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")` |
| `.env` | Ajouter la ligne `ANTHROPIC_API_KEY=` (valeur vide, à renseigner sur le VPS) |

**Ne pas toucher à** `frontend/`, `routers/` (racine), ni à `data/production.db`.

---

## Vérification finale

Après implémentation, tester dans cet ordre :

1. Lancer l'app (`uvicorn main:app --reload`) — vérifier qu'aucune erreur de migration ne s'affiche.
2. Vérifier en SQLite que les tables `expe_tarifs` et `expe_tarifs_frais` existent et que `expe_transporteurs` a les 4 nouvelles colonnes.
3. Ouvrir la fiche d'un transporteur → onglet Tarifs → vérifier que le tableau se charge (vide).
4. Importer un petit CSV test (2-3 lignes) → vérifier l'insertion en `actif=0`.
5. Cliquer "Tout activer" → vérifier que les lignes passent en `actif=1`.
6. Tester "Parser avec IA" seulement si `ANTHROPIC_API_KEY` est renseignée dans `.env`.

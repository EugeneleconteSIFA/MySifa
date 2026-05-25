# Prompt Cursor — MyExpé Chantier 1 : Comparateur de prix

## Prérequis

**Le Chantier 0 doit être entièrement appliqué avant de commencer celui-ci.**
En particulier :
- Les tables `expe_tarifs` et `expe_tarifs_frais` doivent exister (migration v64).
- `expe_transporteurs` doit avoir les colonnes `palette_max`, `poids_max_kg`, `accepte_poids`, `accepte_palette` (migration v63).
- Des données tarifaires `actif=1` doivent être présentes pour tester le moteur.

## Contexte et règles absolues

MySifa est une app FastAPI + HTML/CSS/JS vanilla.
- Backend Python 3 / FastAPI — point d'entrée `main.py`
- Frontend HTML/CSS/JS généré en chaînes Python dans `app/web/*.py`
- DB SQLite — fichier actif : `data/production.db`
- Objet d'état `S`, fonction `api(path, options)`, `escHtml`/`escAttr`, `showToast`, variables CSS, pas d'emojis
- **Ne jamais modifier `DB_PATH` dans `.env`.**
- Le router MyExpé est enregistré dans `main.py` : `app.include_router(expe_departs_router, prefix="/api/expe")`

---

## Fichiers concernés par ce chantier

| Fichier | Ce qui change |
|---|---|
| `app/routers/expe_departs.py` | Endpoint `POST /expe/comparateur` |
| `app/web/expe_page.py` | Section comparateur dans la page MyExpé |
| `app/web/expe_assets.py` | JS partagé : fonction `ouvrirComparateur(depart)` |

---

## Étape 1 — Moteur de calcul backend

### 1.1 — Endpoint `POST /expe/comparateur`

Ajouter dans `app/routers/expe_departs.py` :

```python
@router.post("/comparateur")
def comparateur(request: Request, body: dict = Body(...)):
    """
    Calcule le prix de chaque transporteur éligible pour un envoi.
    Body attendu :
      { poids_total_kg: float, nb_palette: float, code_postal_destination: str, type_envoi: str }
    type_envoi : 'messagerie' | 'ramasse' | 'affretement' | 'express_intl'
    """
    _require_expe(request)

    poids = float(body.get("poids_total_kg") or 0)
    nb_pal = float(body.get("nb_palette") or 0)
    cp = str(body.get("code_postal_destination") or "").strip()
    type_envoi = str(body.get("type_envoi") or "messagerie").strip()

    if not cp:
        raise HTTPException(400, "code_postal_destination est obligatoire")

    dept = _deduire_departement(cp)

    with get_db() as conn:
        eligibles, non_eligibles = _calculer_comparateur(
            conn, poids, nb_pal, dept, cp, type_envoi
        )

    return {
        "departement_deduit": dept,
        "eligibles": eligibles,
        "non_eligibles": non_eligibles
    }
```

### 1.2 — Fonction `_deduire_departement(cp)`

```python
def _deduire_departement(cp: str) -> str:
    """
    Déduit le département depuis le code postal.
    Gère les cas spéciaux : Corse (2A/2B), DOM (971-976), Paris 75.
    """
    cp = cp.strip().upper()
    if len(cp) < 2:
        return cp
    # DOM : 971xx → '971', 972xx → '972', etc.
    if cp.startswith("97") and len(cp) >= 3:
        return cp[:3]
    # Corse : 20xxx → distinguer 2A (200xx-201xx) et 2B (202xx-206xx)
    if cp.startswith("20") and len(cp) == 5:
        num = int(cp) if cp.isdigit() else 0
        return "2A" if num <= 20190 else "2B"
    # Cas général : 2 premiers chiffres, avec leading zero
    dept = cp[:2]
    # Forcer le padding à 2 chiffres (ex: '01'..'09')
    return dept
```

### 1.3 — Fonction `_calculer_comparateur(conn, poids, nb_pal, dept, cp, type_envoi)`

```python
def _calculer_comparateur(conn, poids, nb_pal, dept, cp, type_envoi):
    """
    Pour chaque transporteur actif, vérifie l'éligibilité et calcule le prix total.
    Retourne (eligibles, non_eligibles).
    """
    transporteurs = conn.execute(
        "SELECT * FROM expe_transporteurs WHERE actif=1"
    ).fetchall()

    eligibles = []
    non_eligibles = []

    for trp in transporteurs:
        raisons_ineligibilite = []

        # --- Filtres d'éligibilité ---

        # 1. Zone : vérifier que le transporteur couvre ce type d'envoi
        zone_col = {
            "messagerie":    "zone_messagerie",
            "ramasse":       "zone_messagerie",
            "affretement":   "zone_affretement",
            "express_intl":  "zone_france",
        }.get(type_envoi, "zone_france")
        if not trp[zone_col]:
            raisons_ineligibilite.append(f"hors zone ({type_envoi})")

        # 2. Capacité palette
        if trp["palette_max"] is not None and nb_pal > 0 and nb_pal > trp["palette_max"]:
            raisons_ineligibilite.append(f"capacité dépassée ({nb_pal} pal. > max {trp['palette_max']})")

        # 3. Type accepté
        if trp["accepte_poids"] == 0 and (poids > 0 and nb_pal == 0):
            raisons_ineligibilite.append("n'accepte pas le tarif au poids")
        if trp["accepte_palette"] == 0 and nb_pal > 0:
            raisons_ineligibilite.append("n'accepte pas les palettes")

        # 4. Vérifier qu'il existe une ligne tarifaire active
        ligne = _trouver_ligne_tarif(conn, trp["id"], type_envoi, dept, cp, poids, nb_pal)
        if not ligne and not raisons_ineligibilite:
            raisons_ineligibilite.append("aucune grille tarifaire pour ce poids/zone")

        if raisons_ineligibilite:
            non_eligibles.append({
                "transporteur_id": trp["id"],
                "transporteur": trp["nom"],
                "raison": " · ".join(raisons_ineligibilite)
            })
            continue

        # --- Calcul du prix ---
        prix_base, detail = _calculer_prix_base(ligne, poids, nb_pal)
        frais_list, prix_frais = _appliquer_frais(conn, trp["id"], prix_base)
        prix_total = prix_base + prix_frais

        eligibles.append({
            "transporteur_id": trp["id"],
            "transporteur": trp["nom"],
            "prix_ht": round(prix_total, 2),
            "prix_base_ht": round(prix_base, 2),
            "detail_calcul": {
                "base": detail,
                "frais": frais_list,
            },
            "delai_jours": None,  # Chantier 3 : à remplir depuis expe_delais
        })

    # Trier par prix croissant, marquer le moins cher
    eligibles.sort(key=lambda x: x["prix_ht"])
    if eligibles:
        eligibles[0]["moins_cher"] = True

    return eligibles, non_eligibles
```

### 1.4 — Fonction `_trouver_ligne_tarif(...)`

Résolution de zone du plus précis au plus large : code postal exact → département → zone_intl.

```python
def _trouver_ligne_tarif(conn, transporteur_id, type_envoi, dept, cp, poids, nb_pal):
    """
    Cherche la ligne expe_tarifs la plus précise pour cet envoi.
    Retourne la ligne SQLite Row ou None.
    """
    # Choisir la valeur de la base_calcul selon le type
    # On essaie d'abord palette si nb_pal > 0, sinon poids
    tentatives = []
    if nb_pal > 0:
        tentatives.append(("palette", nb_pal))
    if poids > 0:
        tentatives.append(("poids", poids))

    zones_par_priorite = [
        ("code_postal", cp),
        ("departement", dept),
    ]

    for base_calcul, valeur_base in tentatives:
        for zone_type, zone_valeur in zones_par_priorite:
            ligne = conn.execute("""
                SELECT * FROM expe_tarifs
                WHERE transporteur_id=?
                  AND type_envoi=?
                  AND base_calcul=?
                  AND zone_type=?
                  AND zone_valeur=?
                  AND actif=1
                  AND tranche_min <= ?
                  AND (tranche_max IS NULL OR tranche_max > ?)
                ORDER BY tranche_min DESC
                LIMIT 1
            """, (
                transporteur_id, type_envoi, base_calcul,
                zone_type, zone_valeur,
                valeur_base, valeur_base
            )).fetchone()
            if ligne:
                return ligne
    return None
```

### 1.5 — Fonction `_calculer_prix_base(ligne, poids, nb_pal)`

```python
def _calculer_prix_base(ligne, poids, nb_pal):
    """
    Calcule le prix de base selon l'unité de la ligne tarifaire.
    Retourne (prix_ht, detail_str).
    """
    unite = ligne["unite"]
    prix = ligne["prix"]
    mini = ligne["mini_perception"] or 0
    base_calcul = ligne["base_calcul"]

    if unite == "forfait":
        prix_calc = prix
        detail = f"forfait {prix:.2f} €"
    elif unite == "au_100kg":
        prix_calc = prix * poids / 100
        detail = f"{prix:.4f} €/100kg × {poids} kg = {prix_calc:.2f} €"
    elif unite == "au_kg":
        prix_calc = prix * poids
        detail = f"{prix:.4f} €/kg × {poids} kg = {prix_calc:.2f} €"
    else:
        prix_calc = prix
        detail = f"{prix:.2f} € (unité inconnue : {unite})"

    # Appliquer le mini de perception
    if mini and prix_calc < mini:
        detail += f" → mini perception {mini:.2f} €"
        prix_calc = mini

    return prix_calc, detail
```

### 1.6 — Fonction `_appliquer_frais(conn, transporteur_id, prix_base)`

Applique les frais `applique_defaut=1` du transporteur.

```python
def _appliquer_frais(conn, transporteur_id, prix_base):
    """
    Applique tous les frais par défaut du transporteur.
    Retourne (liste_frais_détaillée, total_frais_ht).
    """
    frais_rows = conn.execute("""
        SELECT * FROM expe_tarifs_frais
        WHERE transporteur_id=? AND applique_defaut=1
        ORDER BY libelle
    """, (transporteur_id,)).fetchall()

    frais_list = []
    total_frais = 0.0

    for fr in frais_rows:
        mode = fr["mode"]
        valeur = fr["valeur"] or 0
        mini_fr = fr["mini"] or 0

        if mode == "pct_transport":
            montant = prix_base * valeur / 100
            if mini_fr and montant < mini_fr:
                montant = mini_fr
            detail = f"{valeur}% du transport = {montant:.2f} €"
        elif mode == "forfait_expedition":
            montant = valeur
            detail = f"forfait {valeur:.2f} €"
        elif mode == "par_palette":
            # nb_palette n'est pas accessible ici — utiliser valeur directement
            # Amélioration future : passer nb_pal en argument
            montant = valeur
            detail = f"{valeur:.2f} €"
        else:
            montant = valeur
            detail = f"{valeur:.2f} €"

        frais_list.append({
            "libelle": fr["libelle"],
            "montant": round(montant, 2),
            "detail": detail,
        })
        total_frais += montant

    return frais_list, total_frais
```

---

## Étape 2 — UI : section Comparateur dans la page MyExpé

### 2.1 — Emplacement dans `app/web/expe_page.py`

Ajouter un onglet "Comparateur" (ou une section dédiée) dans la page MyExpé, accessible depuis la navigation de la page. La section s'appelle `#section-comparateur`.

### 2.2 — Formulaire d'entrée

```js
function renderComparateur() {
  // Préserve les valeurs si déjà saisies
  const f = S.comparateur_form || {};
  return `
  <div style="max-width:640px">
    <h2 style="font-size:15px;font-weight:700;color:var(--text);margin:0 0 20px">
      Comparer les transporteurs
    </h2>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px">

      <label style="display:flex;flex-direction:column;gap:6px;font-size:12px;
             font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--text2)">
        Poids total (kg)
        <input id="cmp-poids" type="number" min="0" step="0.1"
               value="${escAttr(String(f.poids_total_kg||''))}"
               style="background:var(--bg);border:1px solid var(--border);border-radius:10px;
                      padding:12px 16px;color:var(--text);font-size:14px"
               placeholder="ex : 340">
      </label>

      <label style="display:flex;flex-direction:column;gap:6px;font-size:12px;
             font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--text2)">
        Nombre de palettes
        <input id="cmp-pal" type="number" min="0" step="1"
               value="${escAttr(String(f.nb_palette||''))}"
               style="background:var(--bg);border:1px solid var(--border);border-radius:10px;
                      padding:12px 16px;color:var(--text);font-size:14px"
               placeholder="ex : 3">
      </label>

      <label style="display:flex;flex-direction:column;gap:6px;font-size:12px;
             font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--text2)">
        Code postal destination
        <input id="cmp-cp" type="text" maxlength="10"
               value="${escAttr(f.code_postal_destination||'')}"
               style="background:var(--bg);border:1px solid var(--border);border-radius:10px;
                      padding:12px 16px;color:var(--text);font-size:14px"
               placeholder="ex : 75011">
      </label>

      <label style="display:flex;flex-direction:column;gap:6px;font-size:12px;
             font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--text2)">
        Type d'envoi
        <select id="cmp-type"
               style="background:var(--bg);border:1px solid var(--border);border-radius:10px;
                      padding:12px 16px;color:var(--text);font-size:14px">
          <option value="messagerie" ${(f.type_envoi||'messagerie')==='messagerie'?'selected':''}>Messagerie</option>
          <option value="ramasse"    ${f.type_envoi==='ramasse'?'selected':''}>Ramasse</option>
          <option value="affretement" ${f.type_envoi==='affretement'?'selected':''}>Affrètement</option>
        </select>
      </label>
    </div>

    <button id="btn-comparer"
            style="background:var(--accent);color:#0a0e17;border:none;border-radius:10px;
                   padding:12px 24px;font-weight:700;font-size:14px;cursor:pointer">
      Comparer
    </button>

    <div id="cmp-resultats" style="margin-top:24px"></div>
  </div>
  `;
}
```

Après injection dans le DOM :
```js
document.getElementById('btn-comparer').onclick = lancerComparateur;
```

### 2.3 — Fonction `lancerComparateur()`

```js
async function lancerComparateur() {
  const poids = parseFloat(document.getElementById('cmp-poids').value) || 0;
  const nb_palette = parseFloat(document.getElementById('cmp-pal').value) || 0;
  const cp = document.getElementById('cmp-cp').value.trim();
  const type_envoi = document.getElementById('cmp-type').value;

  if (!cp) { showToast('Code postal destination obligatoire','danger'); return; }
  if (!poids && !nb_palette) { showToast('Saisir au moins un poids ou un nombre de palettes','danger'); return; }

  // Sauvegarder pour pré-remplissage si re-render
  S.comparateur_form = { poids_total_kg: poids, nb_palette, code_postal_destination: cp, type_envoi };

  const btn = document.getElementById('btn-comparer');
  btn.disabled = true;
  btn.textContent = 'Calcul en cours...';
  document.getElementById('cmp-resultats').innerHTML =
    '<p style="color:var(--muted);font-size:13px">Calcul en cours...</p>';

  try {
    const data = await api('/expe/comparateur', {
      method: 'POST',
      body: JSON.stringify({ poids_total_kg: poids, nb_palette, code_postal_destination: cp, type_envoi })
    });
    renderResultatsComparateur(data);
  } catch(e) {
    showToast(e.message || 'Erreur lors du calcul','danger');
    document.getElementById('cmp-resultats').innerHTML = '';
  } finally {
    btn.disabled = false;
    btn.textContent = 'Comparer';
  }
}
```

### 2.4 — Fonction `renderResultatsComparateur(data)`

```js
function renderResultatsComparateur(data) {
  const el = document.getElementById('cmp-resultats');
  if (!el) return;

  const elig = data.eligibles || [];
  const noelig = data.non_eligibles || [];

  if (!elig.length && !noelig.length) {
    el.innerHTML = '<p style="color:var(--muted);font-size:13px">Aucun résultat.</p>';
    return;
  }

  let html = '';

  // Département déduit (info contextuelle)
  if (data.departement_deduit) {
    html += `<p style="font-size:12px;color:var(--muted);margin:0 0 16px">
      Département déduit du code postal : <strong>${escHtml(data.departement_deduit)}</strong>
    </p>`;
  }

  // Tableau des éligibles
  if (elig.length) {
    html += `<div style="margin-bottom:24px">
      <div style="font-size:12px;font-weight:600;text-transform:uppercase;
                  letter-spacing:.5px;color:var(--text2);margin-bottom:10px">
        ${elig.length} transporteur${elig.length>1?'s':''} éligible${elig.length>1?'s':''}
      </div>
      <div style="display:flex;flex-direction:column;gap:8px">`;

    elig.forEach((e, i) => {
      const moinsCher = e.moins_cher;
      html += `
      <div style="background:var(--card);border:1px solid ${moinsCher?'var(--accent)':'var(--border)'};
                  border-radius:12px;padding:16px;position:relative">
        ${moinsCher ? `<span style="position:absolute;top:12px;right:12px;background:var(--accent);
                       color:#0a0e17;font-size:11px;font-weight:700;padding:3px 8px;
                       border-radius:6px">Moins cher</span>` : ''}
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
          <span style="font-size:15px;font-weight:700;color:var(--text)">
            ${escHtml(e.transporteur)}
          </span>
          <span style="font-size:18px;font-weight:700;color:${moinsCher?'var(--accent)':'var(--text)'}">
            ${e.prix_ht.toFixed(2)} €
          </span>
          <span style="font-size:12px;color:var(--muted)">HT</span>
        </div>
        <details style="font-size:12px;color:var(--text2)">
          <summary style="cursor:pointer;color:var(--muted);margin-bottom:4px">
            Détail du calcul
          </summary>
          <div style="margin-top:8px;padding:10px;background:var(--bg);border-radius:8px;
                      display:flex;flex-direction:column;gap:4px">
            <div>Base : ${escHtml(e.detail_calcul.base)}</div>
            ${(e.detail_calcul.frais||[]).map(fr =>
              `<div>${escHtml(fr.libelle)} : ${escHtml(fr.detail)}</div>`
            ).join('')}
            <div style="border-top:1px solid var(--border);margin-top:6px;padding-top:6px;
                        font-weight:700;color:var(--text)">
              Total : ${e.prix_ht.toFixed(2)} € HT
            </div>
          </div>
        </details>
      </div>`;
    });

    html += `</div></div>`;
  }

  // Section non éligibles (pliable)
  if (noelig.length) {
    html += `<details style="margin-top:8px">
      <summary style="font-size:12px;color:var(--muted);cursor:pointer">
        ${noelig.length} transporteur${noelig.length>1?'s':''} non éligible${noelig.length>1?'s':''} — voir les raisons
      </summary>
      <div style="margin-top:8px;display:flex;flex-direction:column;gap:6px">`;

    noelig.forEach(ne => {
      html += `
      <div style="background:var(--card);border:1px solid var(--border);border-radius:10px;
                  padding:12px 16px;display:flex;justify-content:space-between;align-items:center">
        <span style="font-size:13px;color:var(--text2)">${escHtml(ne.transporteur)}</span>
        <span style="font-size:12px;color:var(--muted)">${escHtml(ne.raison)}</span>
      </div>`;
    });

    html += `</div></details>`;
  }

  el.innerHTML = html;
}
```

---

## Étape 3 — Bouton "Comparer" sur les lignes de `expe_departs`

### 3.1 — Modifier le rendu des lignes de départs

Dans `app/web/expe_page.py` (ou `expe_assets.py`), dans la fonction qui rend chaque ligne de la liste des départs (`renderDeparts`, `renderEntries` ou équivalent), ajouter un bouton "Comparer" à côté des boutons existants (modifier, valider...).

**Le bouton n'apparaît que si le départ a un `code_postal_destination` non vide.**

```js
// Dans la fonction de rendu de chaque ligne départ :
const canCompare = d.code_postal_destination && (d.poids_total_kg || d.nb_palette);
const btnComparer = canCompare
  ? `<button class="btn-ghost" title="Comparer les prix pour ce départ"
             onclick="ouvrirComparateurDepuisDepart(${d.id},
               ${parseFloat(d.poids_total_kg)||0},
               ${parseFloat(d.nb_palette)||0},
               '${escAttr(d.code_postal_destination||'')}')">
       <!-- icône balance SVG 16px -->
       <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
         <line x1="2" y1="12" x2="22" y2="12"/>
         <path d="M6 12l-4 8h8L6 12z"/>
         <path d="M18 12l-4 8h8L18 12z"/>
         <line x1="12" y1="2" x2="12" y2="12"/>
       </svg>
     </button>`
  : '';
```

### 3.2 — Fonction `ouvrirComparateurDepuisDepart(...)`

Dans `app/web/expe_assets.py`, ajouter :

```js
function ouvrirComparateurDepuisDepart(departId, poids, nb_palette, cp) {
  // Pré-remplir l'objet form du comparateur
  S.comparateur_form = {
    poids_total_kg: poids,
    nb_palette: nb_palette,
    code_postal_destination: cp,
    type_envoi: nb_palette >= 6 ? 'affretement' : 'messagerie',
    _source_depart_id: departId,
  };

  // Naviguer vers la section comparateur (basculer l'onglet actif si la page a des onglets)
  // Puis déclencher le calcul automatiquement
  if (typeof basculerOngletExpe === 'function') {
    basculerOngletExpe('comparateur');  // adapter au nom réel de la fonction de navigation
  }

  // Attendre le render, puis lancer
  requestAnimationFrame(() => {
    // Pré-remplir les champs si déjà présents dans le DOM
    const fPoids = document.getElementById('cmp-poids');
    const fPal   = document.getElementById('cmp-pal');
    const fCp    = document.getElementById('cmp-cp');
    const fType  = document.getElementById('cmp-type');
    if (fPoids) fPoids.value = poids || '';
    if (fPal)   fPal.value   = nb_palette || '';
    if (fCp)    fCp.value    = cp || '';
    if (fType)  fType.value  = nb_palette >= 6 ? 'affretement' : 'messagerie';
    // Lancer la comparaison automatiquement
    if (typeof lancerComparateur === 'function') lancerComparateur();
  });
}
```

---

## Étape 4 — Wiring dans `main.py`

L'endpoint `/api/expe/comparateur` est déjà couvert par le router existant :
```python
app.include_router(expe_departs_router, prefix="/api/expe")
```
**Aucune modification de `main.py` nécessaire.**

---

## Résumé des fichiers à modifier

| Fichier | Ce qui change |
|---|---|
| `app/routers/expe_departs.py` | Endpoint `POST /comparateur` + 4 fonctions utilitaires `_deduire_departement`, `_calculer_comparateur`, `_trouver_ligne_tarif`, `_calculer_prix_base`, `_appliquer_frais` |
| `app/web/expe_page.py` | Section comparateur : `renderComparateur()`, `lancerComparateur()`, `renderResultatsComparateur()` |
| `app/web/expe_assets.py` | Fonction partagée `ouvrirComparateurDepuisDepart()` + bouton dans le rendu des lignes départs |

---

## Vérification finale

Tester dans cet ordre :

1. Vérifier que des lignes `expe_tarifs` avec `actif=1` existent pour au moins un transporteur (pré-requis Chantier 0).
2. Appeler manuellement `POST /api/expe/comparateur` via curl ou l'UI avec un poids et un CP connus.
3. Vérifier que la réponse contient au moins un éligible avec `prix_ht` > 0 et un `detail_calcul` correct.
4. Vérifier qu'un transporteur sans grille tarifaire apparaît dans `non_eligibles` avec la bonne raison.
5. Ouvrir la section Comparateur dans l'UI → saisir un envoi → vérifier l'affichage du tableau trié par prix.
6. Sur une ligne départ avec CP renseigné → cliquer le bouton balance → vérifier que le formulaire est pré-rempli et le calcul se lance.
7. Vérifier le thème light (body.light) : les cartes résultats et le badge "Moins cher" doivent rester lisibles.

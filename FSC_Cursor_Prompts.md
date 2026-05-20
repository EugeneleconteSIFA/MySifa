# MySifa — Prompts Cursor : Traçabilité FSC Chain of Custody

> **Contexte global** — MySifa est une application FastAPI + SQLite + HTML/JS vanilla.
> Backend : `app/routers/` — Frontend (HTML généré en Python) : `app/web/` — DB : `app/core/database.py`.
> Dernière migration active : **v29** (`audit_logs`). Les nouvelles migrations commencent à **v30**.
> Config centrale : `config.py` à la racine (ne jamais importer depuis `app/config.py`).
> Design system : variables CSS `--accent`, `--success`, `--danger`, `--muted`, `--card`, `--border`, `--text`.
> Toasts : `showToast(message, type)` avec `type` parmi `success`, `danger`, `info`. Jamais d'`alert()`.
> Toute interpolation de données dans le DOM : `escHtml()` et `escAttr()` obligatoires.

---

## Prompt 1 — Type de claim FSC sur les réceptions de bobines

### Objectif
Ajouter un champ `fsc_type_claim` sur la table `stock_receptions` pour enregistrer précisément le type de certification FSC du lot receptionné. C'est le champ pivot de toute la traçabilité FSC : sans lui, on ne sait pas si une bobine est FSC 100%, FSC Mix ou FSC Recycled.

### Contexte code existant

**Table cible :** `stock_receptions` (colonnes actuelles : `id`, `created_at`, `created_by`, `created_by_name`, `note`, `nb_bobines`, `fournisseur`, `certificat_fsc`)

**Endpoint POST existant** dans `app/routers/stock.py` (ligne ~863) :
```python
@router.post("/api/stock/receptions")
async def create_reception(request: Request):
    user = require_stock(request)
    body = await request.json()
    codes = [str(c).strip() for c in (body.get("codes") or []) if str(c).strip()]
    note = (body.get("note") or "").strip() or None
    fournisseur = (body.get("fournisseur") or "").strip() or None
    certificat_fsc = (body.get("certificat_fsc") or "").strip() or None
    # INSERT INTO stock_receptions (created_at, created_by, created_by_name, note, nb_bobines, fournisseur, certificat_fsc)
```

**GET existant** dans `app/routers/stock.py` (ligne ~841) :
```python
@router.get("/api/stock/receptions")
def list_receptions(request: Request, limit: int = 50):
    # SELECT r.*, GROUP_CONCAT(i.code_barre, '||') as codes FROM stock_receptions r ...
```

**Endpoint lookup en fabrication** `GET /api/fabrication/receptions/lookup` (ligne ~873 de `fabrication.py`) :
```python
# SELECT r.id AS reception_id, r.fournisseur, r.certificat_fsc
# FROM stock_reception_items i JOIN stock_receptions r ON r.id = i.reception_id
```
Ce endpoint devra aussi retourner `fsc_type_claim`.

### Ce qu'il faut faire

**1. Migration DB dans `app/core/database.py`**

Ajouter après la migration v29 (ligne ~1436), suivre exactement ce pattern :

```python
# v30 — FSC : type de claim sur les réceptions de bobines
if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=30 LIMIT 1").fetchone():
    conn.executescript("""
        ALTER TABLE stock_receptions ADD COLUMN fsc_type_claim TEXT DEFAULT 'non_fsc';
    """)
    conn.commit()
    _record_schema_migration(conn, 30, "stock_receptions_fsc_type_claim")
```

Valeurs acceptées pour `fsc_type_claim` : `fsc_100` | `fsc_mix_credit` | `fsc_mix` | `fsc_recycled` | `non_fsc`

**2. Backend `app/routers/stock.py`**

- Dans `create_reception` : extraire `fsc_type_claim` du body, valider qu'il est dans les valeurs autorisées, l'ajouter au INSERT.
- Dans `list_receptions` : inclure `fsc_type_claim` dans le SELECT (il est dans `r.*` donc déjà là, mais vérifier).
- Ajouter une route `PATCH /api/stock/receptions/{reception_id}` pour permettre la correction a posteriori d'une réception (champs éditables : `fournisseur`, `certificat_fsc`, `fsc_type_claim`, `note`). Utiliser `require_stock_write`.

- Dans `GET /api/fabrication/receptions/lookup` (`fabrication.py`) : ajouter `r.fsc_type_claim` dans le SELECT et le retourner dans la réponse.

**3. Frontend `app/web/stock_page.py`**

Dans le formulaire de création de réception (modal ou section dédiée), ajouter **avant** le champ certificat FSC :

```html
<label>Type de certification FSC</label>
<select id="fsc-type-claim" required>
  <option value="non_fsc" selected>Non FSC</option>
  <option value="fsc_100">FSC 100%</option>
  <option value="fsc_mix_credit">FSC Mix Credit</option>
  <option value="fsc_mix">FSC Mix</option>
  <option value="fsc_recycled">FSC Recycled</option>
</select>
```

Ce champ est **obligatoire**. Si `non_fsc` est sélectionné, le champ `certificat_fsc` peut rester vide (ne pas le requérir). Si une valeur FSC est choisie, rendre `certificat_fsc` obligatoire.

Dans la liste des réceptions existantes, afficher un **badge coloré** `fsc_type_claim` :
- `fsc_100` → badge vert (`--success`) — texte "FSC 100%"
- `fsc_mix*` → badge bleu (`--accent`) — texte "FSC Mix"
- `fsc_recycled` → badge bleu — texte "FSC Recycled"
- `non_fsc` → badge gris (`--muted`) — texte "Non FSC"

**Pattern badge** (cohérent avec le reste de MySifa) :
```html
<span style="background:var(--accent-bg);color:var(--accent);
             padding:2px 8px;border-radius:6px;font-size:11px;font-weight:600">
  FSC 100%
</span>
```

### Tests à vérifier
- Créer une réception avec chaque type de claim → vérifier en DB.
- Créer une réception `fsc_100` sans certificat → doit être bloqué côté frontend.
- Appeler `/api/fabrication/receptions/lookup?code_barre=XXXX` sur une bobine réceptionnée en FSC 100% → la réponse doit inclure `fsc_type_claim: "fsc_100"`.

---

## Prompt 2 — Flag FSC requis sur les dossiers du planning

### Objectif
Permettre au planificateur de marquer un dossier comme "certification FSC requise" au moment de sa création ou de son édition dans le planning. Ce flag est la clé qui conditionne toute la validation en production.

### Contexte code existant

**Table cible :** `planning_entries` (colonnes actuelles importantes : `id`, `machine_id`, `reference`, `client`, `description`, `statut`, `duree_heures`, `commentaire`, `exigences_production`, `date_livraison`, `laize`, `ref_produit`)

**Endpoint PATCH existant** dans `app/routers/planning.py` (ligne ~1368) :
```python
async def update_entry(machine_id: int, entry_id: int, request: Request):
    require_admin(request)
    body = await request.json()
    # Met à jour les champs via UPDATE SET ... WHERE id=? AND machine_id=?
```

**Endpoint POST existant** dans `app/routers/planning.py` (ligne ~1274) :
```python
async def add_entry(machine_id: int, request: Request):
    require_admin(request)
    body = await request.json()
    # INSERT INTO planning_entries (machine_id, position, reference, client, ...)
```

L'endpoint `GET /api/planning/entries` ou `GET /api/planning/machines/{id}/entries` retourne les dossiers avec tous leurs champs — `fsc_requis` sera automatiquement inclus après la migration.

### Ce qu'il faut faire

**1. Migration DB dans `app/core/database.py`**

```python
# v31 — FSC : flag certification requise sur les dossiers planning
if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=31 LIMIT 1").fetchone():
    conn.executescript("""
        ALTER TABLE planning_entries ADD COLUMN fsc_requis INTEGER DEFAULT 0;
        ALTER TABLE planning_entries ADD COLUMN fsc_type_requis TEXT DEFAULT '';
    """)
    conn.commit()
    _record_schema_migration(conn, 31, "planning_entries_fsc_requis")
```

`fsc_requis` : 0 ou 1 (boolean SQLite).
`fsc_type_requis` : `fsc_100` | `fsc_mix` | `fsc_recycled` | `''` (vide si `fsc_requis = 0`).

**2. Backend `app/routers/planning.py`**

Dans `add_entry` : accepter `fsc_requis` (int, default 0) et `fsc_type_requis` (str, default '') du body, les inclure dans l'INSERT.

Dans `update_entry` : accepter `fsc_requis` et `fsc_type_requis` dans le body, les inclure dans le SET dynamique du UPDATE. Ajouter au log d'audit si la valeur change (le pattern d'audit est déjà en place dans cet endpoint — suivre le même pattern que pour `statut`).

Les GET retournent déjà tous les champs de `planning_entries` via `SELECT *` — rien à changer.

**3. Frontend `app/web/planning_page.py`**

Dans le **panneau d'édition d'un dossier** (le drawer ou modal latéral qui s'ouvre lors du clic sur "Modifier" dans la timeline) :

Ajouter une section "Certification FSC" avec :
```html
<div style="display:flex;align-items:center;gap:12px;margin-top:12px">
  <input type="checkbox" id="fsc-requis-chk" onchange="onFscRequisChange()">
  <label for="fsc-requis-chk" style="font-weight:600;cursor:pointer">
    Certification FSC requise sur ce dossier
  </label>
</div>
<div id="fsc-type-wrap" style="display:none;margin-top:8px">
  <select id="fsc-type-requis">
    <option value="fsc_100">FSC 100%</option>
    <option value="fsc_mix">FSC Mix</option>
    <option value="fsc_recycled">FSC Recycled</option>
  </select>
</div>
```

```javascript
function onFscRequisChange() {
  const checked = document.getElementById('fsc-requis-chk').checked;
  document.getElementById('fsc-type-wrap').style.display = checked ? 'block' : 'none';
}
```

Dans la **vue timeline/liste** du planning, sur chaque dossier ayant `fsc_requis = 1`, afficher un badge discret :
```html
<span title="Certification FSC requise" style="
  background:var(--accent-bg);color:var(--accent);
  font-size:10px;font-weight:700;padding:1px 5px;border-radius:4px;
  margin-left:4px;vertical-align:middle">FSC</span>
```

### Tests à vérifier
- Créer un dossier avec `fsc_requis=1`, `fsc_type_requis='fsc_100'` → vérifier en DB.
- Modifier un dossier existant pour activer FSC → vérifier l'entrée dans `audit_logs`.
- Le badge FSC apparaît bien dans la timeline.
- Appeler `GET /api/planning/machines/{id}/entries` → les champs `fsc_requis` et `fsc_type_requis` sont présents dans la réponse.

---

## Prompt 3 — Alerte en production si bobine non-FSC sur dossier FSC

### Objectif
Quand un opérateur scanne une bobine en production sur un dossier qui requiert une certification FSC, MySifa doit détecter l'incompatibilité et afficher une alerte de confirmation. C'est la sécurité fonctionnelle centrale pour la certification.

### Contexte code existant

**Endpoint POST** `app/routers/fabrication.py` (ligne ~904) :
```python
@router.post("/api/fabrication/matieres")
async def add_matiere(request: Request):
    # Insère dans fab_matieres_utilisees, puis appelle _link_matiere_to_reception()
    # Retourne {"success": True, "id": new_id, "matiere": d}
```

**Fonction de liaison** `_link_matiere_to_reception` (ligne ~983) :
```python
def _link_matiere_to_reception(conn, matiere_id, code_barre, fournisseur_fsc_id):
    # Recherche dans stock_reception_items par code_barre
    # Si trouvé : UPDATE fab_matieres_utilisees SET reception_id=?, liaison_mode='reception'
    # Sinon : liaison manuelle via fournisseur_fsc_id
```

Après l'appel à cette fonction, on sait :
- `reception.fsc_type_claim` (si liaison via réception)
- `fournisseur_manual` et `certificat_fsc_manual` (si liaison manuelle)

**Table `planning_entries`** a maintenant (après Prompt 2) : `fsc_requis INTEGER`, `fsc_type_requis TEXT`.

**Table `fab_matieres_utilisees`** : `id`, `machine_id`, `machine_nom`, `operateur`, `no_dossier`, `code_barre`, `scanned_at`, `reception_id`, `liaison_mode`, `fournisseur_manual`, `certificat_fsc_manual`

### Ce qu'il faut faire

**1. Migration DB dans `app/core/database.py`**

```python
# v32 — FSC : champs alerte sur fab_matieres_utilisees
if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=32 LIMIT 1").fetchone():
    conn.executescript("""
        ALTER TABLE fab_matieres_utilisees ADD COLUMN fsc_warning INTEGER DEFAULT 0;
        ALTER TABLE fab_matieres_utilisees ADD COLUMN fsc_warning_note TEXT;
    """)
    conn.commit()
    _record_schema_migration(conn, 32, "fab_matieres_fsc_warning")
```

**2. Backend `app/routers/fabrication.py`**

Créer une fonction utilitaire de vérification FSC :

```python
FSC_CLAIM_HIERARCHY = {
    'fsc_100': {'fsc_100'},
    'fsc_mix': {'fsc_100', 'fsc_mix_credit', 'fsc_mix'},
    'fsc_recycled': {'fsc_100', 'fsc_recycled'},
}

def _check_fsc_compatibility(dossier_fsc_type: str, bobine_fsc_type: str | None) -> bool:
    """True si la bobine est compatible avec le type FSC requis sur le dossier."""
    if not bobine_fsc_type or bobine_fsc_type == 'non_fsc':
        return False
    allowed = FSC_CLAIM_HIERARCHY.get(dossier_fsc_type, set())
    return bobine_fsc_type in allowed
```

Dans `add_matiere`, après `_link_matiere_to_reception`, ajouter la vérification :

```python
# Vérification FSC
fsc_warning = False
fsc_warning_message = None
if no_dossier:
    entry = conn.execute(
        "SELECT fsc_requis, fsc_type_requis FROM planning_entries WHERE reference=? LIMIT 1",
        (no_dossier,)
    ).fetchone()
    if entry and entry["fsc_requis"]:
        # Récupérer le fsc_type_claim de la bobine scannée
        row_matiere = conn.execute(
            """SELECT COALESCE(sr.fsc_type_claim, fmu.certificat_fsc_manual) as bobine_fsc_type
               FROM fab_matieres_utilisees fmu
               LEFT JOIN stock_receptions sr ON sr.id = fmu.reception_id
               WHERE fmu.id=?""",
            (new_id,)
        ).fetchone()
        bobine_fsc = row_matiere["bobine_fsc_type"] if row_matiere else None
        if not _check_fsc_compatibility(entry["fsc_type_requis"], bobine_fsc):
            fsc_warning = True
            fsc_warning_message = (
                f"Cette bobine ({code_barre}) n'est pas certifiée {entry['fsc_type_requis'].upper().replace('_', ' ')}. "
                f"Le dossier {no_dossier} requiert une certification FSC."
            )
```

Si `fsc_warning = True` et que le body contient `fsc_warning_confirmed: true` avec une `fsc_warning_note` non vide : enregistrer l'avertissement en DB et continuer. Sinon : retourner la réponse avec `warning: true` sans bloquer (laisser le frontend gérer la confirmation) :

```python
return {
    "success": True,
    "id": new_id,
    "matiere": d,
    "warning": fsc_warning,
    "warning_message": fsc_warning_message,
}
```

Si le scan est re-soumis avec `fsc_warning_confirmed: true` et `fsc_warning_note` : mettre à jour `fsc_warning=1` et `fsc_warning_note` sur la ligne nouvellement créée.

**3. Frontend `app/web/fabrication_page.py`**

Dans la fonction JS de scan de bobine (celle qui appelle `POST /api/fabrication/matieres`), après réception de la réponse :

```javascript
async function submitScanBobine(codeBarre, confirmed = false, warningNote = '') {
  const body = { code_barre: codeBarre, no_dossier: S.dossierActif };
  if (confirmed) {
    body.fsc_warning_confirmed = true;
    body.fsc_warning_note = warningNote;
  }
  const res = await api('/api/fabrication/matieres', { method: 'POST', body: JSON.stringify(body) });

  if (res.warning && !confirmed) {
    // Afficher modal de confirmation FSC
    showFscWarningModal(res.warning_message, codeBarre, async (note) => {
      await submitScanBobine(codeBarre, true, note);
    });
    return;
  }
  // Traitement normal du scan...
  showToast('Bobine enregistrée.', 'success');
  renderMatieres();
}
```

Modal de confirmation :
```javascript
function showFscWarningModal(message, codeBarre, onConfirm) {
  document.getElementById('mroot').innerHTML = `
    <div class="modal-overlay" onclick="closeFscWarning()">
      <div class="modal-box" onclick="event.stopPropagation()"
           style="border-top:4px solid var(--danger);max-width:480px">
        <div style="font-size:15px;font-weight:700;color:var(--danger);margin-bottom:12px">
          Alerte certification FSC
        </div>
        <p style="color:var(--text2);font-size:13px;margin-bottom:16px">
          ${escHtml(message)}
        </p>
        <label style="font-size:12px;font-weight:600;color:var(--text2);
                      text-transform:uppercase;letter-spacing:.5px">
          Raison de l'utilisation (obligatoire)
        </label>
        <textarea id="fsc-warn-note" rows="2" style="width:100%;margin-top:6px"
                  placeholder="Ex : matière FSC en attente de livraison, autorisation responsable..."></textarea>
        <div style="display:flex;gap:10px;margin-top:16px;justify-content:flex-end">
          <button class="btn btn-ghost" onclick="closeFscWarning()">Annuler</button>
          <button class="btn btn-danger" onclick="confirmFscWarning('${escAttr(codeBarre)}')">
            Confirmer quand même
          </button>
        </div>
      </div>
    </div>`;
}

function confirmFscWarning(codeBarre) {
  const note = document.getElementById('fsc-warn-note')?.value?.trim();
  if (!note) { showToast('La raison est obligatoire.', 'danger'); return; }
  closeFscWarning();
  // onConfirm est stocké en closure — adapter selon l'architecture JS existante
}
```

Dans la liste des matières scannées (`renderMatieres()`), afficher une icône ⚠ sur les lignes avec `fsc_warning = 1`, avec un tooltip affichant `fsc_warning_note`.

### Tests à vérifier
- Scanner une bobine non-FSC sur un dossier `fsc_requis=1` → modal d'alerte apparaît.
- Annuler → la bobine n'est pas enregistrée (le scan initial a bien été créé en DB mais sans confirmation, le comportement dépend du choix d'implémentation — supprimer le scan si non confirmé est plus propre).
- Confirmer avec note → bobine enregistrée avec `fsc_warning=1` et la note.
- Scanner une bobine FSC 100% sur un dossier FSC 100% → aucune alerte.
- Scanner une bobine FSC Mix sur un dossier FSC 100% → alerte (incompatible).

---

## Prompt 4 — Rapport de traçabilité FSC par dossier

### Objectif
Créer un endpoint qui reconstitue la chaîne de traçabilité FSC complète pour un dossier donné, et une UI exportable (impression PDF) pour l'auditeur FSC.

### Contexte code existant

Les données existent déjà mais sont dispersées :
- `planning_entries` : infos dossier (reference = no_dossier, client, machine, fsc_requis, fsc_type_requis)
- `fab_matieres_utilisees` : bobines scannées par dossier (via `no_dossier`)
- `stock_reception_items` + `stock_receptions` + `fournisseurs_fsc` : remontée vers fournisseur FSC

Le GET existant `GET /api/fabrication/matieres?no_dossier=XXX` retourne les bobines d'un dossier mais sans la synthèse FSC ni les détails complets.

### Ce qu'il faut faire

**1. Nouveau endpoint dans `app/routers/fabrication.py`**

```python
@router.get("/api/fabrication/tracabilite/{no_dossier}")
def get_tracabilite_dossier(no_dossier: str, request: Request):
    """Rapport de traçabilité FSC complet pour un dossier."""
    user = get_current_user(request)
    _check_fab_access(user)

    with get_db() as conn:
        # 1. Infos dossier
        entry = conn.execute(
            """SELECT reference, client, description, statut, machine_id,
                      fsc_requis, fsc_type_requis, date_livraison
               FROM planning_entries WHERE reference=? LIMIT 1""",
            (no_dossier,)
        ).fetchone()

        # 2. Bobines scannées avec toute la chaîne
        rows = conn.execute(
            """SELECT
                 fmu.id, fmu.code_barre, fmu.scanned_at, fmu.operateur,
                 fmu.machine_nom, fmu.liaison_mode,
                 fmu.fsc_warning, fmu.fsc_warning_note,
                 COALESCE(sr.fournisseur, fmu.fournisseur_manual) AS fournisseur,
                 COALESCE(sr.certificat_fsc, fmu.certificat_fsc_manual) AS certificat_fsc,
                 COALESCE(sr.fsc_type_claim, NULL) AS fsc_type_claim,
                 sr.id AS reception_id,
                 sr.created_at AS reception_date,
                 ff.licence AS fournisseur_licence,
                 ff.certificat AS fournisseur_certificat
               FROM fab_matieres_utilisees fmu
               LEFT JOIN stock_receptions sr ON sr.id = (
                   SELECT i.reception_id FROM stock_reception_items i
                   WHERE trim(i.code_barre) = trim(fmu.code_barre)
                   ORDER BY i.scanned_at DESC LIMIT 1
               )
               LEFT JOIN fournisseurs_fsc ff ON ff.nom = COALESCE(sr.fournisseur, fmu.fournisseur_manual)
               WHERE fmu.no_dossier = ?
               ORDER BY fmu.scanned_at ASC""",
            (no_dossier,)
        ).fetchall()

    bobines = []
    nb_conformes = 0
    fsc_requis = entry["fsc_requis"] if entry else 0
    fsc_type_requis = entry["fsc_type_requis"] if entry else ""

    for r in rows:
        d = dict(r)
        if fsc_requis:
            bobine_claim = d.get("fsc_type_claim")
            conforme = _check_fsc_compatibility(fsc_type_requis, bobine_claim)
            d["fsc_conforme"] = conforme
            if conforme:
                nb_conformes += 1
        else:
            d["fsc_conforme"] = None  # Non applicable
        bobines.append(d)

    nb_total = len(bobines)
    if fsc_requis and nb_total > 0:
        statut_global = "conforme" if nb_conformes == nb_total else "non_conforme"
    elif fsc_requis and nb_total == 0:
        statut_global = "en_attente"
    else:
        statut_global = "non_applicable"

    return {
        "dossier": dict(entry) if entry else {"reference": no_dossier},
        "bobines": bobines,
        "synthese": {
            "nb_bobines_total": nb_total,
            "nb_bobines_fsc_conformes": nb_conformes if fsc_requis else None,
            "nb_bobines_non_conformes": (nb_total - nb_conformes) if fsc_requis else None,
            "statut_global": statut_global,
            "genere_a": datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S"),
        }
    }
```

**2. Frontend — Bouton "Rapport FSC" dans `app/web/fabrication_page.py`**

Dans la section dossier actif (là où est affiché le `no_dossier` en cours), ajouter un bouton "Rapport traçabilité FSC" **visible uniquement si le dossier a `fsc_requis = 1`** :

```javascript
// Dans la fonction qui affiche le dossier actif (ex: renderDossier())
if (dossier.fsc_requis) {
  document.getElementById('fsc-btn-wrap').innerHTML = `
    <button class="btn btn-ghost" style="font-size:12px"
            onclick="openTracabiliteModal('${escAttr(dossier.reference)}')">
      Rapport FSC
    </button>`;
}

async function openTracabiliteModal(noDossier) {
  const data = await api(`/api/fabrication/tracabilite/${encodeURIComponent(noDossier)}`);
  // Afficher dans #mroot une modal full-screen avec le rapport
  const statutColor = data.synthese.statut_global === 'conforme'
    ? 'var(--success)' : data.synthese.statut_global === 'non_conforme'
    ? 'var(--danger)' : 'var(--muted)';

  document.getElementById('mroot').innerHTML = `
    <div class="modal-overlay">
      <div class="modal-box" style="max-width:780px;max-height:90vh;overflow-y:auto">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
          <div>
            <div style="font-size:16px;font-weight:700">Rapport de traçabilité FSC</div>
            <div style="color:var(--muted);font-size:13px">Dossier ${escHtml(noDossier)}</div>
          </div>
          <div style="display:flex;gap:8px">
            <button class="btn btn-ghost" style="font-size:12px" onclick="window.print()">
              Exporter PDF
            </button>
            <button class="btn btn-ghost" onclick="document.getElementById('mroot').innerHTML=''">
              Fermer
            </button>
          </div>
        </div>

        <!-- Badge statut global -->
        <div style="padding:10px 16px;border-radius:8px;background:${statutColor}20;
                    border:1px solid ${statutColor};margin-bottom:16px;
                    font-weight:700;color:${statutColor}">
          ${data.synthese.statut_global === 'conforme' ? 'Conforme FSC'
            : data.synthese.statut_global === 'non_conforme' ? 'Non conforme — ' + data.synthese.nb_bobines_non_conformes + ' bobine(s) en écart'
            : 'Certification FSC non requise sur ce dossier'}
        </div>

        <!-- Tableau des bobines -->
        <table style="width:100%;border-collapse:collapse;font-size:13px">
          <thead>
            <tr style="background:var(--card);border-bottom:2px solid var(--border)">
              <th style="text-align:left;padding:8px">Code barre</th>
              <th style="text-align:left;padding:8px">Fournisseur</th>
              <th style="text-align:left;padding:8px">Certificat FSC</th>
              <th style="text-align:left;padding:8px">Type claim</th>
              <th style="text-align:left;padding:8px">Statut</th>
              <th style="text-align:left;padding:8px">Scanné le</th>
            </tr>
          </thead>
          <tbody>
            ${data.bobines.map(b => `
              <tr style="border-bottom:1px solid var(--border)">
                <td style="padding:8px;font-family:monospace">${escHtml(b.code_barre)}</td>
                <td style="padding:8px">${escHtml(b.fournisseur || '—')}</td>
                <td style="padding:8px">${escHtml(b.certificat_fsc || '—')}</td>
                <td style="padding:8px">
                  <span style="font-size:11px;font-weight:600;padding:2px 6px;border-radius:4px;
                    background:${b.fsc_type_claim === 'fsc_100' ? 'var(--success)20' : 'var(--accent-bg)'};
                    color:${b.fsc_type_claim === 'fsc_100' ? 'var(--success)' : 'var(--accent)'}">
                    ${escHtml(b.fsc_type_claim || 'Non FSC')}
                  </span>
                </td>
                <td style="padding:8px">
                  ${b.fsc_conforme === true
                    ? '<span style="color:var(--success)">✓ Conforme</span>'
                    : b.fsc_conforme === false
                    ? '<span style="color:var(--danger)">✗ Écart' + (b.fsc_warning ? ' (confirmé)' : '') + '</span>'
                    : '<span style="color:var(--muted)">—</span>'}
                </td>
                <td style="padding:8px;color:var(--muted);font-size:12px">
                  ${escHtml(b.scanned_at || '')} · ${escHtml(b.operateur || '')}
                </td>
              </tr>`).join('')}
          </tbody>
        </table>

        <!-- Footer rapport -->
        <div style="margin-top:16px;padding-top:12px;border-top:1px solid var(--border);
                    font-size:11px;color:var(--muted)">
          Généré le ${escHtml(data.synthese.genere_a)} · MySifa · SIFA
        </div>
      </div>
    </div>`;
}
```

Ajouter une feuille CSS `@media print` pour masquer la sidebar et le header lors de l'export PDF :
```css
@media print {
  .sidebar, .topbar, .mobile-topbar { display: none !important; }
  #mroot .modal-overlay { position: static; background: none; }
  #mroot .modal-box { box-shadow: none; max-height: none; }
  button { display: none !important; }
}
```

### Tests à vérifier
- Appeler `GET /api/fabrication/tracabilite/OF12345` → réponse JSON structurée avec dossier, bobines, synthèse.
- Dossier avec 3 bobines FSC 100% et 1 bobine non-FSC → `statut_global: "non_conforme"`, `nb_bobines_non_conformes: 1`.
- Dossier sans `fsc_requis` → `statut_global: "non_applicable"`, `fsc_conforme: null` sur toutes les bobines.
- Export PDF via `window.print()` → sidebar masquée, tableau lisible.

---

## Prompt 5 — Spécifications matière sur les bobines (Phase 2)

### Objectif
Enrichir les `stock_reception_items` avec les caractéristiques physiques des bobines (laize, grammage, métrage, type de support). Ces données sont nécessaires pour la définition des groupes de produits FSC et la réconciliation des volumes.

### Contexte code existant

**Table cible :** `stock_reception_items` (colonnes actuelles : `id`, `reception_id`, `code_barre`, `scanned_at`)

**POST `/api/stock/receptions`** crée la réception et les items en masse :
```python
conn.executemany(
    "INSERT INTO stock_reception_items (reception_id, code_barre, scanned_at) VALUES (?,?,?)",
    [(reception_id, code, now) for code in codes],
)
```

La table `planning_entries` a déjà une colonne `laize REAL` — les specs sont connues au niveau du dossier, pas au niveau de la bobine. L'objectif ici est de les capturer **à la réception** (au niveau bobine ou au niveau du lot entier).

### Ce qu'il faut faire

**1. Migration DB dans `app/core/database.py`**

```python
# v33 — FSC : spécifications matière sur les bobines
if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=33 LIMIT 1").fetchone():
    conn.executescript("""
        ALTER TABLE stock_reception_items ADD COLUMN no_lot_fournisseur TEXT;
        ALTER TABLE stock_reception_items ADD COLUMN laize_mm REAL;
        ALTER TABLE stock_reception_items ADD COLUMN grammage REAL;
        ALTER TABLE stock_reception_items ADD COLUMN metrage_initial REAL;
        ALTER TABLE stock_reception_items ADD COLUMN type_matiere TEXT;
    """)
    conn.commit()
    _record_schema_migration(conn, 33, "stock_reception_items_specs_matiere")
```

`type_matiere` : `papier` | `carton` | `film` | `etiquette` | `autre`

**2. Backend `app/routers/stock.py`**

Dans `POST /api/stock/receptions` : accepter un objet `specs_matiere` dans le body contenant `no_lot_fournisseur`, `laize_mm`, `grammage`, `metrage_initial`, `type_matiere`. Ces specs s'appliquent à **tous les items du lot** (une bobine du même BL a les mêmes specs) :

```python
specs = body.get("specs_matiere") or {}
no_lot = (specs.get("no_lot_fournisseur") or "").strip() or None
laize = _to_float(specs.get("laize_mm"))
grammage = _to_float(specs.get("grammage"))
metrage = _to_float(specs.get("metrage_initial"))
type_mat = (specs.get("type_matiere") or "").strip() or None

conn.executemany(
    """INSERT INTO stock_reception_items
       (reception_id, code_barre, scanned_at, no_lot_fournisseur,
        laize_mm, grammage, metrage_initial, type_matiere)
       VALUES (?,?,?,?,?,?,?,?)""",
    [(reception_id, code, now, no_lot, laize, grammage, metrage, type_mat)
     for code in codes],
)
```

Dans `GET /api/stock/receptions` : inclure les specs dans les items retournés (modifier la requête pour JOINer ou retourner les items enrichis).

Dans `GET /api/fabrication/tracabilite/{no_dossier}` (Prompt 4) : inclure `laize_mm`, `grammage`, `metrage_initial`, `type_matiere` dans la réponse pour chaque bobine.

**3. Frontend `app/web/stock_page.py`**

Dans le formulaire de réception, après le champ `certificat_fsc`, ajouter une section "Spécifications matière (optionnel)" repliable par défaut :

```html
<details style="margin-top:12px">
  <summary style="cursor:pointer;font-weight:600;font-size:13px;color:var(--text2)">
    Spécifications matière (optionnel)
  </summary>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px">
    <div>
      <label>Type de support</label>
      <select id="type-matiere">
        <option value="">— Non renseigné —</option>
        <option value="papier">Papier</option>
        <option value="carton">Carton</option>
        <option value="film">Film</option>
        <option value="etiquette">Étiquette</option>
        <option value="autre">Autre</option>
      </select>
    </div>
    <div>
      <label>N° lot fournisseur</label>
      <input type="text" id="no-lot-fournisseur" placeholder="Ex: LOT-2026-001">
    </div>
    <div>
      <label>Laize (mm)</label>
      <input type="number" id="laize-mm" min="1" max="9999" step="1" placeholder="Ex: 380">
    </div>
    <div>
      <label>Grammage (g/m²)</label>
      <input type="number" id="grammage" min="1" max="9999" step="0.1" placeholder="Ex: 80">
    </div>
    <div>
      <label>Métrage initial (m)</label>
      <input type="number" id="metrage-initial" min="1" step="1" placeholder="Ex: 10000">
    </div>
  </div>
</details>
```

Dans la liste des réceptions, afficher les specs dans le détail de chaque réception (section dépliable par item).

### Tests à vérifier
- Créer une réception avec specs → les items en DB ont bien `laize_mm`, `grammage`, etc.
- Créer une réception sans specs → les champs sont NULL, pas d'erreur.
- Le rapport de traçabilité (Prompt 4) inclut les specs matière par bobine.

---

## Notes transverses pour Cursor

### Pattern de migration à respecter
```python
if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=N LIMIT 1").fetchone():
    conn.executescript("ALTER TABLE ...")
    conn.commit()
    _record_schema_migration(conn, N, "nom_court_migration")
```

### Pattern de requête avec get_db()
```python
with get_db() as conn:
    row = conn.execute("SELECT ...", (param,)).fetchone()
    return dict(row) if row else {}
```

### Accès utilisateur
- `get_current_user(request)` → tous les rôles connectés
- `require_stock(request)` → rôles avec accès stock (logistique, superadmin, direction, administration)
- `require_stock_write(request)` → idem + vérification write
- `require_admin(request)` → superadmin, direction, administration

### Ne jamais
- Utiliser `app/config.py` (vieille copie) — toujours `from config import ...` (racine)
- Coder des couleurs en dur dans le HTML — toujours `var(--accent)`, `var(--success)`, etc.
- Utiliser `alert()` — toujours `showToast(message, type)`
- Interpoler des données utilisateur sans `escHtml()` / `escAttr()`
- Modifier les fichiers dans `frontend/` ou `routers/` à la racine (ce sont des shims)

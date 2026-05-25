# MySifa — Prompts Cursor : MyAO Phase 2

> 4 prompts à exécuter dans l'ordre. Chacun suppose que le précédent est commité.
> Toutes les bases sont déjà en place (email, DB, backends, frontend).

---

## PROMPT 1 — Correction : re-envoi fournisseurs après premier envoi

```
Tu travailles sur MySifa (FastAPI + SQLite + HTML/CSS/JS vanilla).

### Contexte du bug

Dans app/web/ao_page.py, le bouton "Envoyer aux fournisseurs" est conditionnel :
- Il s'affiche UNIQUEMENT si `st === 'brouillon'`
- Une fois l'AO passé à 'envoyee', le bouton disparaît

Problème : on peut ajouter de nouveaux fournisseurs après le premier envoi (le backend `add_fournisseur`
ne vérifie pas le statut brouillon), mais il n'y a aucun moyen de leur envoyer l'invitation depuis l'UI.

Le backend `POST /api/ao/{ao_id}/envoyer` gère déjà ce cas correctement : il n'envoie qu'aux
fournisseurs avec `statut='invite' AND date_envoi IS NULL`. Il ne faut PAS modifier le backend.

---

### Modifications à faire dans app/web/ao_page.py

**1. Fonction `renderDetailHeader()`**

Trouver ce bloc :
```javascript
if (st === 'brouillon') {
    const dis = (lignes < 1 || fournis < 1) ? ' disabled' : '';
    actions += '<button class="btn btn-accent" type="button" id="btn-envoyer"'+dis+'>Envoyer aux fournisseurs</button>';
}
```

Remplacer par :
```javascript
if (st === 'brouillon') {
  const dis = (lignes < 1 || fournis < 1) ? ' disabled' : '';
  actions += '<button class="btn btn-accent" type="button" id="btn-envoyer"'+dis+'>Envoyer aux fournisseurs</button>';
} else if (st === 'envoyee') {
  // Fournisseurs ajoutés après le premier envoi (date_envoi IS NULL, statut='invite')
  const nonenvoyes = (d.fournisseurs||[]).filter(f => !f.date_envoi && f.statut === 'invite').length;
  if (nonenvoyes > 0) {
    actions += '<button class="btn btn-accent" type="button" id="btn-envoyer">Envoyer aux nouveaux ('+nonenvoyes+')</button>';
  }
}
```

**2. Fonction `openModalConfirmEnvoi(n)`**

Elle existe déjà et gère le cas correctement — aucune modification.

**3. Bind dans `bindDetailEvents()`**

Le handler `btn-envoyer` existe déjà et appelle `openModalConfirmEnvoi(n)` puis `POST /api/ao/{id}/envoyer`.
Vérifier que le handler est bien attaché même quand `st === 'envoyee'` — il devrait l'être car
`bindDetailEvents()` est appelé après le render du header.

---

### Contraintes

- Ne modifier que app/web/ao_page.py
- Ne jamais modifier DB_PATH ni le backend
- Importer config depuis `config` (racine)
- Variables CSS uniquement, pas de couleurs codées en dur
```

---

## PROMPT 2 — Référentiel fournisseurs (carnet d'adresses)

```
Tu travailles sur MySifa (FastAPI + SQLite + HTML/CSS/JS vanilla).
La config centrale est config.py (racine). Les migrations sont dans app/core/database.py, _migrate().

### Objectif

Créer un référentiel de fournisseurs récurrents, indépendant des AO.
Quand on ajoute un fournisseur à un AO, on peut le sélectionner depuis ce référentiel
plutôt que de ressaisir son nom et son email à la main.

---

### 1. Base de données — app/core/database.py

Trouver le numéro de migration le plus élevé dans _migrate() et ajouter une migration numérotée M+1 :

```sql
CREATE TABLE IF NOT EXISTS ao_carnet_fournisseurs (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  nom         TEXT NOT NULL,
  email       TEXT NOT NULL,
  pays        TEXT,          -- ex: 'Italie', 'Espagne', 'Allemagne' — libre
  notes       TEXT,
  created_at  TEXT NOT NULL
)
```

Pattern exact à respecter :
```python
if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=N LIMIT 1").fetchone():
    conn.execute("""CREATE TABLE IF NOT EXISTS ao_carnet_fournisseurs (...)""")
    _record_schema_migration(conn, N, "ao_carnet_fournisseurs")
```

---

### 2. Backend — app/routers/ao.py

Ajouter à la fin du fichier, dans le même router (`/api/ao`) :

```python
# ─── Carnet fournisseurs ─────────────────────────────────────────

@router.get("/carnet-fournisseurs")
def list_carnet(request: Request):
    _require_ao(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM ao_carnet_fournisseurs ORDER BY nom COLLATE NOCASE"
        ).fetchall()
    return [_row_dict(r) for r in rows]


@router.post("/carnet-fournisseurs")
async def create_carnet(request: Request):
    _require_ao(request)
    body = await request.json()
    nom = (body.get("nom") or "").strip()
    email = (body.get("email") or "").strip().lower()
    if not nom or not email:
        raise HTTPException(status_code=400, detail="Nom et email obligatoires.")
    pays = (body.get("pays") or "").strip() or None
    notes = (body.get("notes") or "").strip() or None
    now = _now_paris_iso()
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO ao_carnet_fournisseurs (nom, email, pays, notes, created_at) VALUES (?,?,?,?,?)",
            (nom, email, pays, notes, now),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM ao_carnet_fournisseurs WHERE id=?", (cur.lastrowid,)).fetchone()
    return _row_dict(row)


@router.put("/carnet-fournisseurs/{entry_id}")
async def update_carnet(request: Request, entry_id: int):
    _require_ao(request)
    body = await request.json()
    nom = (body.get("nom") or "").strip()
    email = (body.get("email") or "").strip().lower()
    if not nom or not email:
        raise HTTPException(status_code=400, detail="Nom et email obligatoires.")
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE ao_carnet_fournisseurs SET nom=?, email=?, pays=?, notes=? WHERE id=?",
            (nom, email, (body.get("pays") or "").strip() or None,
             (body.get("notes") or "").strip() or None, entry_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Entrée introuvable")
        conn.commit()
        row = conn.execute("SELECT * FROM ao_carnet_fournisseurs WHERE id=?", (entry_id,)).fetchone()
    return _row_dict(row)


@router.delete("/carnet-fournisseurs/{entry_id}")
def delete_carnet(request: Request, entry_id: int):
    _require_ao(request)
    with get_db() as conn:
        cur = conn.execute("DELETE FROM ao_carnet_fournisseurs WHERE id=?", (entry_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Entrée introuvable")
        conn.commit()
    return {"ok": True}
```

---

### 3. Frontend — app/web/ao_page.py

**A. État S — ajouter** :
```javascript
carnet: [],   // référentiel fournisseurs
```

**B. Charger le carnet au démarrage** dans `init()` :
```javascript
await Promise.all([loadList(), loadCarnet()]);
```

Ajouter la fonction :
```javascript
async function loadCarnet() {
  S.carnet = await api('/api/ao/carnet-fournisseurs');
}
```

**C. Modal "Ajouter un fournisseur" — enrichir**

Modifier `openModalFourni()` et la modal correspondante dans `renderModal()`.

Remplacer le contenu de la modal `'fourni'` par :
```html
<h3>Ajouter un fournisseur</h3>
<!-- Picker depuis le carnet -->
<div class="field">
  <label>Sélectionner depuis le carnet</label>
  <select id="m-carnet-pick">
    <option value="">— Saisie manuelle —</option>
    <!-- options générées dynamiquement depuis S.carnet -->
  </select>
</div>
<div id="m-fourni-form">
  <div class="field"><label>Nom</label><input id="m-nom"></div>
  <div class="field"><label>Email</label><input type="email" id="m-mail"></div>
</div>
<label style="font-size:12px;color:var(--muted);display:flex;align-items:center;gap:6px;cursor:pointer;margin-bottom:14px">
  <input type="checkbox" id="m-save-carnet"> Enregistrer dans le carnet
</label>
<div class="modal-actions">
  <button class="btn btn-ghost" id="m-cancel">Annuler</button>
  <button class="btn btn-accent" id="m-ok">Ajouter</button>
</div>
```

Comportement JS dans la modal :
- Quand on sélectionne une entrée du carnet → pré-remplir `m-nom` et `m-mail`
- La checkbox "Enregistrer dans le carnet" : si cochée + saisie manuelle → POST /api/ao/carnet-fournisseurs après ajout fournisseur
- Le select génère les options depuis `S.carnet` via `escHtml()`

**D. Section `contact_fournisseur` dans `render()`**

Remplacer :
```javascript
area.innerHTML = renderSectionPlaceholder('Fournisseurs', 'Référentiel fournisseurs — contenu à venir.');
```
Par :
```javascript
area.innerHTML = renderCarnet();
bindCarnetEvents();
```

Implémenter `renderCarnet()` :
- Header : "Carnet fournisseurs" + bouton "+ Ajouter"
- Tableau : Nom | Email | Pays | Modifier | Supprimer
- Si vide : état vide "Aucun fournisseur dans le carnet."
- Modal ajout/modification (pattern identique aux autres modals de la page)
- DELETE avec confirmation

**E. Fonctions à ajouter** :
- `renderCarnet()` → retourne HTML string
- `bindCarnetEvents()` → attache les événements
- `openModalCarnetEntry(edit)` → modal ajout/modif (champs : nom, email, pays, notes)

---

### Contraintes

- Ne jamais modifier DB_PATH
- Importer config depuis `config` (racine)
- Variables CSS uniquement
- escHtml() + escAttr() sur toutes les données utilisateur
- Pattern migration exact avec guard schema_migrations
```

---

## PROMPT 3 — Référentiel produits

```
Tu travailles sur MySifa (FastAPI + SQLite + HTML/CSS/JS vanilla).
La config centrale est config.py (racine). Les migrations sont dans app/core/database.py, _migrate().

### Objectif

Créer un catalogue de produits récurrents.
Quand on ajoute une ligne à un AO, on peut sélectionner un produit depuis ce catalogue
pour pré-remplir ref_produit, désignation, unité — et modifier les valeurs si besoin.

---

### 1. Base de données — app/core/database.py

Trouver le numéro de migration le plus élevé et ajouter une migration M+1 :

```sql
CREATE TABLE IF NOT EXISTS ao_produits (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  ref         TEXT NOT NULL,          -- référence produit
  designation TEXT NOT NULL,
  unite       TEXT DEFAULT 'unité',
  notes       TEXT,
  created_at  TEXT NOT NULL
)
```

Pattern exact : guard `schema_migrations`, `IF NOT EXISTS`, `_record_schema_migration(conn, N, "ao_produits")`.

---

### 2. Backend — app/routers/ao.py

Ajouter à la fin du fichier dans le même router (`/api/ao`) :

```python
# ─── Catalogue produits ──────────────────────────────────────────

@router.get("/produits")
def list_produits(request: Request):
    _require_ao(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM ao_produits ORDER BY ref COLLATE NOCASE"
        ).fetchall()
    return [_row_dict(r) for r in rows]


@router.post("/produits")
async def create_produit(request: Request):
    _require_ao(request)
    body = await request.json()
    ref = (body.get("ref") or "").strip()
    designation = (body.get("designation") or "").strip()
    if not ref or not designation:
        raise HTTPException(status_code=400, detail="Référence et désignation obligatoires.")
    unite = (body.get("unite") or "unité").strip() or "unité"
    notes = (body.get("notes") or "").strip() or None
    now = _now_paris_iso()
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO ao_produits (ref, designation, unite, notes, created_at) VALUES (?,?,?,?,?)",
            (ref, designation, unite, notes, now),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM ao_produits WHERE id=?", (cur.lastrowid,)).fetchone()
    return _row_dict(row)


@router.put("/produits/{produit_id}")
async def update_produit(request: Request, produit_id: int):
    _require_ao(request)
    body = await request.json()
    ref = (body.get("ref") or "").strip()
    designation = (body.get("designation") or "").strip()
    if not ref or not designation:
        raise HTTPException(status_code=400, detail="Référence et désignation obligatoires.")
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE ao_produits SET ref=?, designation=?, unite=?, notes=? WHERE id=?",
            (ref, designation, (body.get("unite") or "unité").strip() or "unité",
             (body.get("notes") or "").strip() or None, produit_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Produit introuvable")
        conn.commit()
        row = conn.execute("SELECT * FROM ao_produits WHERE id=?", (produit_id,)).fetchone()
    return _row_dict(row)


@router.delete("/produits/{produit_id}")
def delete_produit(request: Request, produit_id: int):
    _require_ao(request)
    with get_db() as conn:
        cur = conn.execute("DELETE FROM ao_produits WHERE id=?", (produit_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Produit introuvable")
        conn.commit()
    return {"ok": True}
```

---

### 3. Frontend — app/web/ao_page.py

**A. État S — ajouter** :
```javascript
produits: [],   // catalogue produits
```

**B. Charger au démarrage** dans `init()` :
```javascript
await Promise.all([loadList(), loadCarnet(), loadProduits()]);
```

Ajouter :
```javascript
async function loadProduits() {
  S.produits = await api('/api/ao/produits');
}
```

**C. Modal "Ajouter une ligne" — enrichir**

Modifier la modal `'ligne'` dans `renderModal()`.

En haut de la modal, avant les champs, ajouter un picker produit :
```html
<div class="field">
  <label>Produit du catalogue</label>
  <select id="m-produit-pick">
    <option value="">— Saisie manuelle —</option>
    <!-- options générées depuis S.produits -->
  </select>
</div>
```

Comportement : quand on sélectionne un produit → pré-remplir `m-ref`, `m-des`, `m-unite`.
Le fournisseur peut modifier les valeurs après sélection (les champs restent éditables).

Checkbox en bas : "Enregistrer dans le catalogue"
- Si cochée + saisie manuelle → POST /api/ao/produits après ajout ligne.

**D. Section `produits` dans `render()`**

Remplacer :
```javascript
area.innerHTML = renderSectionPlaceholder('Produits', 'Référentiel produits — contenu à venir.');
```
Par :
```javascript
area.innerHTML = renderProduits();
bindProduitsEvents();
```

Implémenter `renderProduits()` :
- Header : "Catalogue produits" + bouton "+ Ajouter un produit"
- Tableau : Référence | Désignation | Unité | Modifier | Supprimer
- Si vide : état vide "Aucun produit dans le catalogue."
- Searchbar filtre sur ref + designation (pattern CLAUDE.md : focus préservé, filtre oninput)
- Modals ajout/modification (champs : ref, designation, unite, notes)
- DELETE avec confirmation

**E. Fonctions à ajouter** :
- `renderProduits()` → HTML string
- `bindProduitsEvents()` → événements
- `openModalProduit(edit)` → modal ajout/modif

---

### Contraintes

- Ne jamais modifier DB_PATH
- Importer config depuis `config` (racine)
- Variables CSS uniquement
- escHtml() + escAttr() sur toutes les données utilisateur
- Pattern migration exact avec guard schema_migrations
- La searchbar doit respecter le pattern CLAUDE.md : focus préservé après re-render,
  filtre oninput, Escape vide le champ, message "Aucun résultat pour « X »"
```

---

## PROMPT 4 — Badges notifications + nettoyage section clients

```
Tu travailles sur MySifa (FastAPI + SQLite + HTML/CSS/JS vanilla).

### Objectif

1. Afficher un badge dans l'onglet "Messagerie" quand des messages fournisseur non lus existent
2. Supprimer la section sidebar "Clients" (placeholder vide, pas prévue pour l'instant)
3. Améliorer l'onglet "Fournisseurs" : afficher un indicateur de messages non lus par fournisseur

---

### 1. Endpoint backend — app/routers/ao.py

Ajouter à la fin du fichier :

```python
@router.get("/{ao_id}/non-lus")
def non_lus(request: Request, ao_id: int):
    """Retourne le nombre de messages fournisseur non lus, par fournisseur."""
    _require_ao(request)
    with get_db() as conn:
        _get_ao_or_404(conn, ao_id)
        rows = conn.execute(
            """SELECT ao_fournisseur_id, COUNT(*) AS n
               FROM ao_messages
               WHERE ao_fournisseur_id IN (
                 SELECT id FROM ao_fournisseurs WHERE ao_id=?
               ) AND expediteur='fournisseur' AND lu=0
               GROUP BY ao_fournisseur_id""",
            (ao_id,),
        ).fetchall()
    return {str(r["ao_fournisseur_id"]): int(r["n"]) for r in rows}
```

---

### 2. Frontend — app/web/ao_page.py

**A. État S — ajouter** :
```javascript
nonLus: {},   // {fourni_id: nb_messages_non_lus}
```

**B. Charger les non-lus dans `loadDetail(id)`**

Après le chargement du détail, ajouter :
```javascript
try {
  S.nonLus = await api('/api/ao/' + id + '/non-lus');
} catch(e) {
  S.nonLus = {};
}
```

**C. Onglet "Messagerie" — ajouter un badge**

Dans la fonction `renderDetailHeader()`, dans la génération des onglets :

Trouver la ligne qui génère les tabs (map sur `['lignes','fournisseurs','comparaison','messages','documents']`).
Pour l'onglet `'messages'`, calculer le total des messages non lus :

```javascript
const totalNonLus = Object.values(S.nonLus || {}).reduce((a, b) => a + b, 0);
```

Modifier le label de l'onglet messages :
```javascript
'messages': 'Messagerie' + (totalNonLus > 0
  ? ' <span class="nav-badge" style="background:var(--danger);color:#fff;font-size:10px;padding:1px 6px;border-radius:999px;font-weight:700">'+totalNonLus+'</span>'
  : '')
```

**D. Onglet "Fournisseurs" — badge par ligne**

Dans `renderFournisseurs()`, pour chaque fournisseur `f`, récupérer `S.nonLus[f.id] || 0`.
Si > 0 : afficher dans la colonne Statut un badge rouge à côté du badge statut :
```javascript
const nb = S.nonLus[String(f.id)] || 0;
const unreadBadge = nb > 0
  ? ' <span style="background:var(--danger);color:#fff;font-size:10px;padding:1px 6px;border-radius:999px;font-weight:700;display:inline-block">'+nb+' msg</span>'
  : '';
```

**E. Supprimer la section "Clients" de la sidebar**

Dans `buildAoSidebarNavStructure()`, supprimer l'entrée `contact_client` :
```javascript
// SUPPRIMER cette ligne :
{kind:'btn', section:'contact_client', icon:'user', label:'Client', sub:true},
```

Dans `render()`, supprimer le bloc :
```javascript
// SUPPRIMER ce bloc :
} else if (S.section === 'contact_client') {
    area.innerHTML = renderSectionPlaceholder('Clients', 'Référentiel clients — contenu à venir.');
}
```

Dans `aoMobileTitle()`, supprimer l'entrée `contact_client`.

---

### 3. Reset des non-lus au chargement de l'onglet messagerie

Dans `setTab()`, quand `tab === 'messages'`, après `loadMessages()` :
```javascript
// Recharger les non-lus (ils ont été marqués lu côté backend par loadMessages)
S.nonLus = await api('/api/ao/' + id + '/non-lus');
render();
```

---

### Contraintes

- Ne jamais modifier DB_PATH
- Ne modifier que app/routers/ao.py et app/web/ao_page.py
- Variables CSS uniquement, pas de couleurs codées en dur
- escHtml() + escAttr() sur toutes les données interpolées
```

---

## Tests manuels à faire après chaque prompt

**Après prompt 1** :
- Créer un AO → ajouter lignes + fournisseur → envoyer
- Ajouter un 2ème fournisseur → vérifier que "Envoyer aux nouveaux (1)" apparaît
- Cliquer → confirmer → vérifier que seul le nouveau reçoit l'email (ou tente l'envoi)

**Après prompt 2** :
- Aller dans "Fournisseurs" sidebar → ajouter une entrée au carnet
- Ouvrir un AO → ajouter fournisseur → sélectionner depuis le carnet → champs pré-remplis
- Tester la checkbox "Enregistrer dans le carnet"

**Après prompt 3** :
- Aller dans "Produits" sidebar → ajouter des produits
- Ouvrir un AO brouillon → ajouter ligne → sélectionner depuis le catalogue → champs pré-remplis
- Tester la searchbar (filtre, focus préservé, Escape)

**Après prompt 4** :
- Depuis le portail fournisseur, envoyer un message
- Revenir sur l'UI interne → badge rouge sur l'onglet "Messagerie"
- Vérifier que le badge disparaît après lecture
- Vérifier que la section "Clients" n'apparaît plus dans la sidebar

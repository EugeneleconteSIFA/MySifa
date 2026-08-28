# Prompt Cursor — MyDevis : correctifs + import données + UX patron

## Contexte et état actuel

MySifa est une app FastAPI + HTML/CSS/JS vanilla. Tout le frontend est dans
`app/web/html.py` (~8000 lignes). L'état global est l'objet `S`, les appels
API passent par `api(path, options)`.

**Ce qui existe déjà et fonctionne (ne pas toucher) :**
- Router `app/routers/matiere_prix.py` — toutes les routes `/api/matiere/...`
- Section `renderMatierePrix()` dans `app/web/html.py`
- Migrations 11 et 15 dans `app/core/database.py`
- Accès : `ROLES_DEVIS = {direction, superadmin}` dans `config.py`
- Script `scripts/import_matieres.py`

**Problèmes à corriger :**

---

## Problème 1 — `code` obligatoire bloque la saisie manuelle

Dans `app/routers/matiere_prix.py`, la route `POST /api/matiere/params` fait :
```python
if not cat or not code or not des:
    raise HTTPException(400, "categorie, code et designation sont obligatoires")
```

Dans la migration 11 (`app/core/database.py`) : `code TEXT NOT NULL`

**Fix :**

a) Dans `app/core/database.py`, ajouter une migration pour rendre `code` nullable :
```python
# Après la migration 15, ajouter :
if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=16 LIMIT 1").fetchone():
    try:
        # Recréer la table sans la contrainte NOT NULL sur code
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS matiere_params_new (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                categorie        TEXT NOT NULL DEFAULT '',
                code             TEXT,
                designation      TEXT NOT NULL,
                fournisseur      TEXT,
                poids_m2         REAL,
                prix_eur_m2      REAL,
                prix_usd_kg      REAL,
                taux_change      REAL DEFAULT 1.0,
                incidence_dollar REAL DEFAULT 1.0,
                transport_total  REAL DEFAULT 0,
                appellation      TEXT,
                grammage         INTEGER,
                notes            TEXT,
                updated_at       TEXT
            );
            INSERT INTO matiere_params_new SELECT * FROM matiere_params;
            DROP TABLE matiere_params;
            ALTER TABLE matiere_params_new RENAME TO matiere_params;
        """)
    except Exception:
        pass
    _record_schema_migration(conn, 16, "matiere_params_code_nullable")
```

b) Dans `app/routers/matiere_prix.py`, route `create_param` :
```python
# Remplacer :
if not cat or not code or not des:
# Par :
if not cat or not des:
```
Et pour `code` dans l'INSERT : utiliser `(body.get("code") or "").strip() or None`

c) Dans `app/web/html.py`, dans `openMatiereParamModal`, ligne de validation :
```js
// Remplacer :
if(!body.categorie||!body.code||!body.designation)
// Par :
if(!body.categorie||!body.designation)
```

---

## Problème 2 — Modal Base matière sans champs prix

Dans `openMatiereBaseModal` (`app/web/html.py`), il manque les champs
`prix_cohesio` et `prix_rotoflex`. Sans ces champs, on ne peut pas saisir
un prix manuellement — la ligne s'affiche avec `—` partout.

**Fix :** Ajouter ces deux champs dans le `grid` de `openMatiereBaseModal`,
juste avant `rotoflex_supplement_eur_m2` :

```js
matiereAddLabeledInput(grid,'Prix Cohésio €/m²','prix_cohesio',
    row&&row.prix_cohesio!=null?row.prix_cohesio:'','number');
matiereAddLabeledInput(grid,'Prix Rotoflex €/m²','prix_rotoflex',
    row&&row.prix_rotoflex!=null?row.prix_rotoflex:'','number');
```

Et dans la section de parsing des inputs (avant l'appel API dans `btnOk.onclick`),
s'assurer que les valeurs vides sont bien converties en `null` :
```js
// Already done by the existing number-parsing logic (v===''?null:parseFloat(...))
// No change needed there.
```

---

## Problème 3 — Labels techniques incompréhensibles pour le patron

Dans `renderMatierePrix()` (`app/web/html.py`), améliorer les labels partout.

### Onglet Paramètres — en-têtes de colonnes :

```js
// Remplacer le tableau des headers params :
['Catégorie','Code','Désignation','Fournisseur','Poids m²','Prix €/m²','USD/kg','Tx change','Incidence','Transport','Appellation','Notes','']
// Par :
['Catégorie','Réf.','Désignation','Fournisseur','Poids m²','Prix €/m²','Prix USD/kg','Taux USD→EUR','Incidence taxe','Transport €/m²','Code app.','Notes','']
```

### Modal Paramètres — labels des champs :

```js
// Dans le tableau `fields` de openMatiereParamModal, remplacer :
['Taux change','taux_change', ...]
['Incidence dollar','incidence_dollar', ...]
['Transport','transport_total', ...]
// Par :
['Taux de change USD→EUR  (ex: 0.85)','taux_change', ...]
['Incidence taxe/transport import  (ex: 1.075)','incidence_dollar', ...]
['Transport au m²  (€/m², ex: 0.06)','transport_total', ...]
```

### Onglet Base matière — explication en haut :

```js
// Remplacer le texte explicatif actuel par quelque chose de plus clair :
h('p', {style:{margin:'0 0 6px',color:'var(--text2)',fontSize:'13px'}},
  'Prix matière = frontal + silicone + adhésif + glassine. ' +
  'La marge d\'erreur est ajoutée pour les commerciaux (prix en vert = prix à donner, ' +
  'prix barré = prix de revient).'
)
```

---

## Problème 4 — La section Base matière doit grouper par famille (VELIN, COUCHE…)

Actuellement les lignes de `matiere_base` sont groupées par `frontal`
(ex: "Velin Etiwell 68 g"). C'est correct mais on perd la notion de famille
(VELIN, COUCHE, THERMIQUE ECO…).

Ajouter une colonne `groupe` à `matiere_base` et l'utiliser pour le groupement visuel.

### a) Migration dans `app/core/database.py` :
La migration 16 (définie au problème 1) doit aussi faire :
```python
# Dans le même bloc version=16 :
mb_cols = {r["name"] for r in conn.execute("PRAGMA table_info(matiere_base)").fetchall()}
if "groupe" not in mb_cols:
    conn.execute("ALTER TABLE matiere_base ADD COLUMN groupe TEXT")
```

### b) Router `app/routers/matiere_prix.py` :

Route `GET /api/matiere/base` — ajouter `groupe` à l'ORDER BY :
```python
ORDER BY groupe, frontal, designation, id
```

Route `POST /api/matiere/base` et `PUT /api/matiere/base/{id}` — ajouter
`groupe` dans les champs éditables.

Route `GET /api/matiere/base` — conserver.

### c) Modal Base matière dans `app/web/html.py` :
Ajouter en premier champ du `grid` :
```js
matiereAddLabeledInput(grid,'Famille (VELIN, COUCHE, THERMIQUE ECO…)','groupe',
    row&&row.groupe||'','text');
```

### d) Affichage groupé dans `renderMatierePrix` :

Dans la boucle de construction de `baseBody`, remplacer le groupement par `frontal`
par un groupement à deux niveaux :

```js
// Trier d'abord par groupe puis par frontal puis désignation
rows.sort((a,b)=>{
  const ga=String(a.groupe||'ZZZ'), gb=String(b.groupe||'ZZZ');
  if(ga!==gb)return ga.localeCompare(gb,'fr');
  const fa=String(a.frontal||''), fb=String(b.frontal||'');
  if(fa!==fb)return fa.localeCompare(fb,'fr');
  return String(a.designation||'').localeCompare(String(b.designation||''),'fr');
});

let lastGroupe=null, lastFrontal=null;
rows.forEach(r=>{
  const grp=(r.groupe||'').toUpperCase()||'AUTRES';
  const front=r.frontal||'— (sans frontal)';

  // En-tête de famille (VELIN, COUCHE…)
  if(grp!==lastGroupe){
    lastGroupe=grp; lastFrontal=null;
    baseBody.push(
      h('tr',{className:'matiere-group matiere-group-famille'},
        h('td',{colSpan:11,style:{background:'var(--accent)',color:'#fff',padding:'4px 12px',fontSize:'11px',fontWeight:'700',letterSpacing:'1px',textTransform:'uppercase'}},grp)
      )
    );
  }

  // Sous-en-tête de frontal (Velin Etiwell 68g…)
  if(front!==lastFrontal){
    lastFrontal=front;
    baseBody.push(
      h('tr',{className:'matiere-group'},
        h('td',{colSpan:11,style:{paddingLeft:'20px',fontStyle:'italic'}},front)
      )
    );
  }

  // Ligne de données
  baseBody.push(h('tr',null,
    h('td',{style:{fontFamily:'monospace',paddingLeft:'28px'}},r.ref_interne!=null?String(r.ref_interne):'—'),
    h('td',null,r.designation||''),
    h('td',null,r.type_adhesion||''),
    h('td',null,r.adhesif||''),
    h('td',null,r.silicone||''),
    h('td',null,r.glassine||''),
    h('td',null,matierePriceCell(r.prix_cohesio,r.prix_cohesio_majore,marge)),
    h('td',null,matierePriceCell(r.prix_rotoflex,r.prix_rotoflex_majore,marge)),
    h('td',null,r.marqueur||''),
    h('td',null,
      h('button',{className:'btn-ghost',title:'Modifier',onClick:()=>openMatiereBaseModal(r)},iconEl('edit',14)),
      h('button',{className:'btn-ghost',title:'Supprimer',onClick:async()=>{
        if(!confirm('Supprimer cette ligne ?'))return;
        try{
          await api('/api/matiere/base/'+r.id,{method:'DELETE'});
          showToast('Ligne supprimée','success');
          await loadMatierePrixPage();
        }catch(e){showToast(e.message||'Suppression impossible','danger');}
      }},'×')
    )
  ));
});
```

Mettre à jour les en-têtes du tableau Base matière (10 cols au lieu de 11) :
```js
// Supprimer la colonne 'Frontal' (maintenant dans le sous-en-tête de groupe)
['Réf.','Désignation','Type','Adhésif','Silicone','Glassine','Cohésio €/m²','Rotoflex €/m²','Marqueur','']
```
Et mettre à jour `colSpan` à `10` partout dans les lignes de groupe.

---

## Bonus — Searchbar sticky

Dans `renderMatierePrix`, wraper la searchbar et la barre de config dans un
div sticky pour qu'elles restent visibles en scrollant :

```js
// Remplacer :
return h('div', null, ..., tabBar, search, margeRow, h('div',{style:{overflowX:'auto'}}, ...))
// Par :
const stickyHeader = h('div', {style:{
  position:'sticky',top:0,zIndex:10,
  background:'var(--bg)',
  paddingBottom:'8px',
  borderBottom:'1px solid var(--border)',
  marginBottom:'12px'
}}, tabBar, search, margeRow);

return h('div', null, ..., stickyHeader, h('div',{style:{overflowX:'auto'}}, ...))
```

---

## Résumé des fichiers à modifier

| Fichier | Modifications |
|---|---|
| `app/core/database.py` | Migration 16 : code nullable + colonne groupe |
| `app/routers/matiere_prix.py` | code non obligatoire, groupe dans CRUD base |
| `app/web/html.py` | Labels, champs prix modal base, groupement 2 niveaux, sticky header |

---

## Comment peupler la DB avec les données Excel

Après avoir appliqué les corrections ci-dessus, copier le fichier Excel dans
`data/` puis lancer :

```bash
python scripts/import_matieres.py data/Prix_matieres.xlsx
```

Puis déployer sur le VPS avec :
```bash
./deploy.sh --db
```

OU en production, utiliser directement le bouton "Importer Excel" dans l'interface
(onglet MyDevis → bouton en haut à droite). Cocher "Remplacer toutes les lignes"
pour un import complet depuis le classeur SIFA.

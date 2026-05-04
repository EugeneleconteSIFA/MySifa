# Prompt Cursor — MyDevis : visibilité + onglets Paramètres & Base matière

## Contexte projet

MySifa est une app FastAPI + HTML/CSS/JS vanilla (frontend servi en tant que chaîne Python dans `app/web/html.py`).
L'état central frontend est l'objet `S`, les mises à jour passent par `set({...})`, les appels API par `api(path, options)`.
Le fichier principal du frontend est `app/web/html.py` (~7 500 lignes).
La base de données est SQLite, les migrations suivent le pattern `_migrate()` dans `app/core/database.py`.
Les rôles existants sont : `superadmin`, `direction`, `administration`, `fabrication`, `logistique`, `comptabilite`, `expedition`, `commercial`.

---

## Objectif

Implémenter les 3 choses suivantes, dans l'ordre :

---

### 1. Rendre MyDevis visible pour `direction` et `superadmin`

Dans `app/web/html.py`, la fonction qui construit le portail d'accueil contient :

```js
if(isCom){
  apps.push(h('div',{className:'portal-app portal-app--disabled'},
    h('div',{className:'portal-app-icon',style:{opacity:.4}},iconEl('file-text',28)),
    h('div',{className:'portal-app-name',style:{opacity:.5}},'MyDevis'),
    h('div',{className:'portal-app-desc'},'Devis & Chiffrage'),
    h('span',{className:'badge-dev'},'En développement')
  ));
}
```

**Modification à faire :**
- Garder l'entrée MyDevis dans le bloc `if(isCom)` pour les commerciaux (désactivée, badge "En développement"), **tel quel**.
- Ajouter une seconde entrée MyDevis **avant** le bloc `if(isCom)`, déclenchée uniquement pour `direction` et `superadmin` :
  - Cliquable → navigue vers la page devis (section `devis` du SPA ou une nouvelle section `matiere_prix`)
  - Icône : `file-text` (même icône, opacité normale)
  - Nom : `MyDevis`
  - Description : `Paramètres matière & Base prix`
  - **Pas** de badge "En développement" — elle est fonctionnelle

La condition à utiliser est : `u.role === 'direction' || u.role === 'superadmin'`
(la variable user est accessible via `S.user` ou via le pattern déjà utilisé dans la page portail).

---

### 2. Nouvelle section `matiere_prix` dans le SPA

Cette section est accessible uniquement aux rôles `direction` et `superadmin`.
Elle comporte **deux onglets** : `Paramètres` et `Base matière`.

#### Architecture des données

**DB — migrations à ajouter dans `app/core/database.py` (dans `_migrate()`) :**

```sql
-- Table des matières premières (paramètres unitaires)
CREATE TABLE IF NOT EXISTS matiere_params (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  categorie TEXT NOT NULL,        -- ex: 'Silicone', 'Glassine', 'Adhésif permanent', etc.
  code TEXT NOT NULL,             -- ex: 'S', 'GLS', 'P', 'E'
  designation TEXT NOT NULL,      -- ex: 'Silicone Phoenix Release'
  fournisseur TEXT,
  poids_m2 REAL,                  -- poids au m² en kg
  prix_eur_m2 REAL,               -- prix en € par m²
  prix_usd_kg REAL,               -- prix en USD/kg (si import)
  taux_change REAL DEFAULT 1.0,   -- taux de conversion USD→EUR
  incidence_dollar REAL DEFAULT 1.0, -- coefficient incidence dollar/taxes
  transport_total REAL DEFAULT 0, -- coût transport au m²
  appellation TEXT,               -- code court (GLS, EN, CO…)
  grammage INTEGER,               -- grammage en g/m²
  notes TEXT,
  updated_at TEXT
);

-- Table base matières (prix calculés par combinaison)
CREATE TABLE IF NOT EXISTS matiere_base (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ref_interne INTEGER,            -- référence numérique interne (ex: 1012, 1141)
  designation TEXT NOT NULL,      -- désignation complète
  frontal TEXT,                   -- type de papier frontal (ex: 'Velin Etiwell 68 g')
  type_adhesion TEXT,             -- ex: 'Permanent', 'Enlevable', 'Congélation', 'Pneu'
  adhesif TEXT,                   -- référence adhésif (ex: '2028Y/19')
  silicone TEXT,                  -- ex: 'Sans silicone', 'Silicone Phoenix Release'
  glassine TEXT,                  -- ex: 'Glassine 58 g chinois LK'
  marqueur TEXT,                  -- lettre de marqueur optionnel (B, H, etc.)
  prix_cohesio REAL,              -- prix au m² pour machine Cohésio
  prix_rotoflex REAL,             -- prix au m² pour machine Rotoflex
  updated_at TEXT
);

-- Paramètre global : marge d'erreur (%)
CREATE TABLE IF NOT EXISTS matiere_config (
  cle TEXT PRIMARY KEY,
  valeur TEXT NOT NULL,
  updated_at TEXT
);
INSERT OR IGNORE INTO matiere_config (cle, valeur, updated_at) VALUES ('marge_erreur', '5', datetime('now'));
INSERT OR IGNORE INTO matiere_config (cle, valeur, updated_at) VALUES ('taux_change_usd', '0.85', datetime('now'));
```

Utiliser la version `_migrate()` avec le guard `if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=N LIMIT 1").fetchone()` (choisir le prochain numéro de version disponible).

---

#### API — nouveau fichier `app/routers/matiere_prix.py`

Créer ce router FastAPI et l'enregistrer dans `main.py` avec le préfixe `/api/matiere`.

Routes :

```
GET  /api/matiere/config                      → { marge_erreur: float, taux_change_usd: float }
POST /api/matiere/config                      → body { marge_erreur, taux_change_usd }

GET  /api/matiere/params?q=&categorie=        → liste des matiere_params
POST /api/matiere/params                      → créer
PUT  /api/matiere/params/{id}                 → mettre à jour
DELETE /api/matiere/params/{id}               → supprimer

GET  /api/matiere/base?q=&frontal=&type=      → liste des matiere_base (avec prix majoré = prix * (1 + marge_erreur/100))
POST /api/matiere/base                        → créer
PUT  /api/matiere/base/{id}                   → mettre à jour
DELETE /api/matiere/base/{id}                 → supprimer

POST /api/matiere/import-excel                → upload .xlsx, parse et importe les deux feuilles
```

**Authentification :** Toutes ces routes nécessitent `role in ('superadmin', 'direction')`. Utiliser le même pattern que les autres routers (session cookie + vérification rôle).

**Route import Excel :** Parser les deux feuilles du fichier uploadé :
- Feuille `Parametres` → insérer dans `matiere_params` (tenter de mapper les colonnes connues, stocker le reste dans `notes`)
- Feuille `Base_matières` → insérer dans `matiere_base`
- Retourner `{ imported_params: N, imported_base: M, errors: [...] }`

---

#### Frontend — section `matiere_prix` dans `app/web/html.py`

Ajouter dans l'état global `S` :
```js
matiereTab: 'base',           // 'base' | 'params'
matiereParams: [],
matiereBase: [],
matiereConfig: { marge_erreur: 5, taux_change_usd: 0.85 },
matiereSearch: '',
matiereLoading: false,
```

**Fonction `renderMatierePrix()`** — structure HTML :

```
┌─────────────────────────────────────────────────────────┐
│  MyDevis — Paramètres matière                           │
│  [Onglet: Base matière]  [Onglet: Paramètres]           │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │  🔍  Rechercher...  (searchbar pleine largeur)   │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  [Marge d'erreur: __5__ %]  (visible sur les deux onglets)│
│                                                         │
│  ── contenu de l'onglet actif ────────────────────────  │
└─────────────────────────────────────────────────────────┘
```

**Searchbar :**
- Input de type text, placeholder `Rechercher par désignation, frontal, adhésif, type…`
- Filtre en temps réel (pas besoin d'appui sur Entrée) sur tous les champs textuels de la ligne
- La recherche est insensible à la casse et aux accents (`normalize('NFD').replace(/[̀-ͯ]/g, '')`)
- Style cohérent avec le reste de l'app (variable CSS `--border`, `--bg`, `--text`)

**Marge d'erreur :**
- Affichée en haut des deux onglets sous la searchbar
- Input numérique (min 0, max 50, step 0.5), suffixe `%`
- Sauvegarde automatique dès que la valeur change (debounce 800ms → `POST /api/matiere/config`)
- Quand la marge est > 0, le prix affiché dans "Base matière" est : `prix_brut × (1 + marge/100)` avec le prix brut grisé à côté en petit

---

**Onglet "Base matière" :**

Tableau avec les colonnes :
| Réf. | Désignation | Frontal | Type | Adhésif | Silicone | Glassine | Cohésio €/m² | Rotoflex €/m² | Marqueur |
|---|---|---|---|---|---|---|---|---|---|

- Les prix Cohésio et Rotoflex s'affichent en `font-family: monospace`, 4 décimales, couleur `--ok` (vert)
- Si marge > 0 : afficher `prix_majoré` en vert + `prix_brut` grisé barré en 11px à côté
- Les lignes sont regroupées visuellement par `frontal` (en-tête de groupe gris, style `.plan-group-header` ou similaire existant dans le projet)
- Bouton `+` en haut à droite pour ajouter une ligne manuellement
- Chaque ligne a un bouton d'édition (crayon) et de suppression (×)
- Bouton `Importer Excel` en haut à droite (ouvre un input file acceptant `.xlsx`)

**Onglet "Paramètres" :**

Tableau avec les colonnes :
| Catégorie | Code | Désignation | Fournisseur | Poids m² | Prix €/m² | Prix USD/kg | Tx change | Incidence | Transport | Appellation | Notes |

- Même logique de groupement par `categorie`
- Même boutons +, crayon, ×
- Le champ `prix_eur_m2` est calculé automatiquement si `prix_usd_kg` et `poids_m2` et `taux_change` et `incidence_dollar` sont renseignés : `prix_usd_kg × poids_m2 × incidence_dollar × taux_change`
- Ce calcul est indicatif et affiché en italique avec la mention `(calculé)`

**Modaux d'édition/création :**
- Utiliser le pattern existant : `document.getElementById("mroot").innerHTML = ...`
- Formulaire en grille 2 colonnes (`.form-grid` existant)
- Boutons `Enregistrer` et `Annuler`
- Toast de confirmation via `showToast(message, 'success')` ou `showToast(message, 'danger')`

---

### 3. Navigation vers la section

Dans la sidebar de l'app principale (la fonction qui construit la nav avec les `{key, label, icon}`), ajouter pour les rôles `direction` et `superadmin` :

```js
{ key: 'matiere_prix', label: 'Base matière', icon: 'layers' }
```

Positionner cette entrée après `rentabilite` dans la liste.

Et dans le switch de rendu des sections (le `if(S.page==='xxx') return renderXxx()`), ajouter :

```js
if(S.page === 'matiere_prix') return renderMatierePrix();
```

---

## Contraintes de style à respecter

- **Aucun emoji** dans les labels, toasts, messages
- Ton direct, professionnel
- Toasts via `showToast(msg, type)` — `type` ∈ `success | danger | info`
- Thème dark/light via variables CSS (`--bg`, `--card`, `--border`, `--text`, `--text2`, `--muted`, `--accent`, `--ok`, `--danger`)
- `parseFloat` toujours (jamais `parseInt`) pour les prix
- `INSERT OR IGNORE` pour les seeds
- Ne pas bloquer si une mise à jour config échoue : `try/except: pass` côté Python, catch silencieux côté JS avec toast danger

---

## Résumé des fichiers à modifier/créer

| Fichier | Action |
|---|---|
| `app/core/database.py` | Ajouter migration tables `matiere_params`, `matiere_base`, `matiere_config` |
| `app/routers/matiere_prix.py` | Créer — toutes les routes `/api/matiere/...` |
| `main.py` | Enregistrer le nouveau router |
| `app/web/html.py` | (1) Visibilité portail, (2) état S + renderMatierePrix(), (3) entrée sidebar |

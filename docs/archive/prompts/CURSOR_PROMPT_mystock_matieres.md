# Prompt Cursor — Extension MyStock : Gestion des matières premières

## Contexte

Tu travailles sur **MySifa**, un outil de gestion de production industrielle.
- Backend : Python 3 / FastAPI — point d'entrée `main.py`
- Frontend : HTML/CSS/JS vanilla généré en chaînes Python dans `app/web/*.py`
- DB : SQLite — chemin défini par `DB_PATH` dans `config.py` racine
- Auth : sessions cookie `sifa_token`
- Migrations DB : pattern `_migrate()` dans `app/core/database.py`, table `schema_migrations`

**Fichiers concernés par ce chantier :**
- `app/core/database.py` — schéma + migrations
- `app/routers/stock.py` — tous les endpoints API stock
- `app/web/stock_page.py` — toute la page MyStock en HTML/JS inline

**Règle critique DB :** Ne jamais modifier `DB_PATH` dans `.env`. Ne jamais toucher à `data/production.db` directement. Toute nouvelle colonne ou table passe par une migration numérotée dans `_migrate()`.

---

## Périmètre de ce chantier

Ce chantier ajoute **4 fonctionnalités** à MyStock :

1. **Gestion des stocks de matières premières** (Mandrins, Palettes, Adhésifs, Cartons) avec 4 types de mouvements : entrée, sortie, ajustement d'inventaire, transfert entre emplacements. Les références sont gérables via l'interface par les admins.
2. **Refonte de la sidebar** en 3 sections clairement séparées : Matières premières / Produits / Autres.
3. **Refonte du tableau de bord** (renommer "Dashboard" → "Tableau de bord") avec alertes stocks bas, derniers mouvements, raccourcis d'action rapide.
4. **Nouvel onglet "Historique des mouvements"** unifié (matières premières + produits finis), filtrable par type, catégorie, référence, date.

---

## ÉTAPE 1 — Migrations DB (`app/core/database.py`)

### 1.1 Vérifier le numéro de migration courant

Avant tout, inspecter `app/core/database.py` pour identifier le numéro de migration le plus élevé déjà présent dans `_migrate()`. Les nouvelles migrations utilisent les numéros suivants.

### 1.2 Nouvelles tables à créer (dans `_migrate()`)

Ajouter 3 nouvelles migrations numérotées dans `_migrate()`, en respectant le pattern existant :

```python
if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=N LIMIT 1").fetchone():
    # DDL ici
    conn.execute("INSERT INTO schema_migrations(version) VALUES(N)")
```

**Migration N : Table `matieres_premieres` (référentiel)**

```sql
CREATE TABLE IF NOT EXISTS matieres_premieres (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    categorie TEXT NOT NULL CHECK(categorie IN ('mandrin','palette','adhesif','carton')),
    reference TEXT NOT NULL,
    designation TEXT NOT NULL,
    seuil_alerte REAL DEFAULT 0,   -- quantité minimale en palettes, déclenchant une alerte
    actif INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
    updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
    UNIQUE(categorie, reference)
);
```

**Migration N+1 : Table `mp_stock` (stock courant par matière)**

```sql
CREATE TABLE IF NOT EXISTS mp_stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    matiere_id INTEGER NOT NULL UNIQUE REFERENCES matieres_premieres(id),
    quantite REAL DEFAULT 0,    -- en palettes
    updated_at TEXT,
    updated_by_name TEXT
);
```

**Migration N+2 : Table `mp_mouvements` (historique des mouvements matières)**

```sql
CREATE TABLE IF NOT EXISTS mp_mouvements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    matiere_id INTEGER NOT NULL REFERENCES matieres_premieres(id),
    type_mouvement TEXT NOT NULL CHECK(type_mouvement IN ('entree','sortie','ajustement','transfert')),
    quantite REAL NOT NULL,         -- toujours positif, le type indique le sens
    quantite_avant REAL,
    quantite_apres REAL,
    ref_bl TEXT,                    -- référence bon de livraison / fournisseur (pour entrées)
    note TEXT,                      -- commentaire libre
    emplacement_source TEXT,        -- pour les transferts
    emplacement_dest TEXT,          -- pour les transferts
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
    created_by INTEGER,
    created_by_name TEXT
);
```

---

## ÉTAPE 2 — Nouveaux endpoints API (`app/routers/stock.py`)

Ajouter les routes suivantes. Utiliser les helpers d'auth existants : `require_stock()` pour la lecture, `require_stock_write()` pour les modifications. Pour les opérations admin (CRUD référentiel), vérifier que le rôle est `superadmin`, `direction` ou `administration`.

### 2.1 Référentiel matières premières

```
GET  /api/stock/matieres                     → liste toutes les matières actives + stock courant
POST /api/stock/matieres                     → créer une nouvelle référence matière (admin uniquement)
PUT  /api/stock/matieres/{matiere_id}        → modifier designation, seuil_alerte, actif (admin uniquement)
DELETE /api/stock/matieres/{matiere_id}      → désactiver (soft delete : actif=0) si aucun mouvement, sinon erreur 400 (admin uniquement)
```

**GET /api/stock/matieres** — réponse attendue :
```json
[
  {
    "id": 1,
    "categorie": "mandrin",
    "reference": "76MM-3P",
    "designation": "Mandrin 76mm 3 pouces",
    "seuil_alerte": 5.0,
    "actif": 1,
    "quantite": 12.0,       // depuis mp_stock, 0 si absent
    "en_alerte": false      // true si quantite <= seuil_alerte et seuil_alerte > 0
  }
]
```

**POST /api/stock/matieres** — body :
```json
{
  "categorie": "mandrin",
  "reference": "76MM-3P",
  "designation": "Mandrin 76mm 3 pouces",
  "seuil_alerte": 5.0
}
```
Après création, insérer une ligne dans `mp_stock` avec `quantite=0`.

### 2.2 Mouvements matières premières

```
POST /api/stock/matieres/mouvement           → enregistrer un mouvement
GET  /api/stock/matieres/{matiere_id}/mouvements  → historique d'une matière (50 derniers)
```

**POST /api/stock/matieres/mouvement** — body :
```json
{
  "matiere_id": 1,
  "type_mouvement": "entree",   // entree | sortie | ajustement | transfert
  "quantite": 10.0,             // toujours positif
  "ref_bl": "BL-2024-001",      // optionnel, surtout pour entrées
  "note": "Réception fournisseur X",  // optionnel
  "emplacement_source": null,   // pour transferts uniquement
  "emplacement_dest": null      // pour transferts uniquement
}
```

**Logique côté serveur :**
1. Récupérer `quantite_avant` depuis `mp_stock` (0 si absent)
2. Calculer `quantite_apres` :
   - `entree` : `quantite_avant + quantite`
   - `sortie` : `quantite_avant - quantite` → si résultat < 0, retourner erreur 400 `{"detail": "Stock insuffisant."}`
   - `ajustement` : `quantite` est la nouvelle valeur absolue, donc `quantite_apres = quantite` et `quantite` réelle du mouvement = `abs(quantite_apres - quantite_avant)`
   - `transfert` : ne modifie pas le stock global (déplace entre emplacements), `quantite_apres = quantite_avant`
3. Mettre à jour `mp_stock` (upsert)
4. Insérer dans `mp_mouvements` avec `created_by` et `created_by_name` depuis la session

### 2.3 Historique unifié

```
GET /api/stock/historique-mouvements    → historique unifié MP + produits finis
```

**Paramètres query string :**
- `type_stock` : `tout` | `mp` | `produits` (défaut : `tout`)
- `categorie` : `mandrin` | `palette` | `adhesif` | `carton` (filtrage MP, ignoré si `type_stock=produits`)
- `reference` : filtrage par texte sur la référence (LIKE insensible à la casse)
- `type_mouvement` : `entree` | `sortie` | `ajustement` | `inventaire` | `transfert` (optionnel)
- `date_debut` : format `YYYY-MM-DD` (optionnel)
- `date_fin` : format `YYYY-MM-DD` (optionnel)
- `limit` : entier, défaut 200, max 500

**Logique :** faire deux requêtes SQLite séparées (une sur `mp_mouvements JOIN matieres_premieres`, une sur `mouvements_stock JOIN produits`), normaliser les champs, fusionner et trier par `created_at DESC`.

**Format de chaque ligne retournée :**
```json
{
  "id": "mp-42",           // préfixe "mp-" pour MP, "pf-" pour produits finis
  "type_stock": "mp",      // "mp" ou "produit"
  "categorie": "mandrin",  // pour MP ; null pour produits
  "reference": "76MM-3P",
  "designation": "Mandrin 76mm 3 pouces",
  "type_mouvement": "entree",
  "quantite": 10.0,
  "quantite_avant": 2.0,
  "quantite_apres": 12.0,
  "ref_bl": "BL-2024-001",
  "note": "Réception fournisseur X",
  "created_at": "2024-05-22T10:30:00",
  "created_by_name": "Jean Dupont"
}
```

### 2.4 Dashboard — mettre à jour l'endpoint existant

Modifier `GET /api/stock/dashboard` pour ajouter :
- `alertes_mp` : liste des matières avec `quantite <= seuil_alerte AND seuil_alerte > 0`
- `derniers_mouvements_mp` : 5 derniers mouvements MP (mêmes champs que ci-dessus)

La réponse existante ne doit pas être cassée — ajouter des clés, ne pas en supprimer.

---

## ÉTAPE 3 — Refonte de la sidebar (`app/web/stock_page.py`)

### 3.1 Nouveaux onglets

Ajouter deux nouveaux onglets dans l'état JS `S` :
- `matieres` : onglet Matières premières
- `historique` : onglet Historique des mouvements

Modifier `S.tab` pour accepter ces nouvelles valeurs.

### 3.2 Structure sidebar en 3 sections

La sidebar doit avoir des séparateurs de section visuels. Voici la structure exacte :

```
[Logo MySifa]
─────────────────────────────
Tableau de bord              ← (pas de label de section au-dessus)

─── MATIÈRES PREMIÈRES ─────  ← label de section (12px, uppercase, muted, letter-spacing)
Matières premières

─── PRODUITS ───────────────  ← label de section
Référentiel
Inventaire
Réception matière

─── OUTILS ─────────────────  ← label de section
Historique mouvements
Étiquettes traça
─────────────────────────────
[sidebar-bottom : user chip, thème, logout, version]
```

**CSS pour les labels de section :**
```css
.nav-section-label {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  color: var(--muted);
  font-weight: 600;
  padding: 14px 16px 6px 16px;
  user-select: none;
}
```

**Règle d'affichage :**
- Si `S.tracaOnly` (rôle fabrication) : afficher seulement "Étiquettes traça", sans sections
- Si `S.stockReadOnly` (rôle commercial) : masquer l'onglet Inventaire, afficher le reste en lecture seule
- L'onglet Matières premières est visible pour tous les rôles ayant accès à MyStock

### 3.3 Icônes SVG à utiliser pour les nouveaux onglets

Utiliser la fonction `icon(name, size)` existante, ou inliner du SVG cohérent avec les icônes déjà présentes. Suggestions :
- Matières premières : icône `layers` (empilement / palettes)
- Historique mouvements : icône `clock` ou `list`

---

## ÉTAPE 4 — Tableau de bord (`buildDashboard()`)

Renommer le label "Dashboard" en "Tableau de bord" partout (sidebar, titre de page, `buildDashboard()`, appels API).

### Nouvelle structure du tableau de bord

**Zone 1 — Raccourcis d'action rapide (en haut, visible immédiatement)**

Une rangée de boutons :
```
[+ Réception matière (PF)]  [+ Entrée MP]  [+ Sortie MP]  [+ Ajustement MP]
```
Ces boutons ouvrent directement la modal correspondante (même comportement que les boutons d'action dans les autres onglets). Ne pas afficher si `S.stockReadOnly`.

**Zone 2 — Alertes stocks bas**

Titre : "Stocks à réapprovisionner"

Deux sous-sections côte à côte (ou empilées sur mobile) :
- **Matières premières en alerte** : liste des matières avec `quantite <= seuil_alerte`, une ligne par référence avec la catégorie (badge coloré), la désignation, le stock actuel et le seuil
- **Produits finis en alerte** : reprendre les données d'alerte existantes du dashboard

Si aucune alerte : afficher un état vide "Tous les stocks sont au-dessus des seuils." en couleur `--success`.

**Zone 3 — Derniers mouvements (bas du dashboard)**

Titre : "Activité récente"

Liste des 10 derniers mouvements toutes catégories confondues (MP + produits finis), avec :
- Badge type de stock (MP / PF)
- Référence + désignation (tronquée à 30 chars)
- Type de mouvement (badge coloré : vert=entrée, rouge=sortie, orange=ajustement, bleu=transfert)
- Quantité
- Opérateur + date relative ("il y a 2h", "hier", etc.)

### Données à charger

Au chargement du dashboard, appeler :
- `GET /api/stock/dashboard` → stats produits + alertes MP + derniers mouvements MP
- `GET /api/stock/historique-mouvements?limit=10` → activité récente unifiée

---

## ÉTAPE 5 — Onglet Matières premières (`buildMatieres()`)

### 5.1 Structure de la page

**En-tête de page :**
- Titre "Matières premières"
- Bouton "Gérer les références" (visible uniquement pour `superadmin`, `direction`, `administration`) → ouvre le panneau de gestion des références

**Filtre par catégorie (pills/onglets horizontaux) :**
```
[Tout]  [Mandrins]  [Palettes]  [Adhésifs]  [Cartons]
```
Filtre local sur `S.matieres`, sans appel API supplémentaire.

**Searchbar :**
Filtre en temps réel sur référence + désignation. Appliquer le pattern de préservation du focus décrit dans CLAUDE.md.

**Liste des matières :**
Une ligne (card) par référence, affichant :
- Badge catégorie (couleur distincte par catégorie : mandrin=#7c3aed, palette=#0891b2, adhesif=#d97706, carton=#059669)
- Référence (monospace, bold)
- Désignation
- Stock actuel en palettes (grand, prominent)
- Indicateur d'alerte : si `en_alerte`, afficher une pastille rouge + texte "Sous le seuil (min. X pal.)"
- Boutons d'action (visibles si non `stockReadOnly`) : Entrée | Sortie | Ajustement | Transfert

Sur mobile, les boutons d'action peuvent être dans un menu (3 points) pour économiser l'espace.

### 5.2 Modals de mouvement

**Modal commune pour Entrée / Sortie / Ajustement / Transfert** (une seule modal, contenu adapté au type) :

Champs communs :
- Matière (pré-remplie si action depuis une ligne, sinon sélecteur)
- Type de mouvement (si ouvert depuis le bouton global du dashboard, sinon verrouillé)
- Quantité en palettes (`<input type="number" step="0.5" min="0.5">`)
- Note (champ texte optionnel)

Champs additionnels selon type :
- **Entrée** : Référence BL / Fournisseur (texte, optionnel)
- **Sortie** : rien de plus (avertissement si stock insuffisant affiché sous le champ quantité en temps réel)
- **Ajustement** : champ "Nouveau stock" remplace "Quantité" (valeur absolue). Afficher "Stock actuel : X pal." au-dessus.
- **Transfert** : Emplacement source + Emplacement destination (textes libres, optionnels)

Après soumission réussie : fermer la modal, toast de confirmation, recharger `S.matieres` via API.

### 5.3 Panneau de gestion des références (admin uniquement)

Déclenché par "Gérer les références" → ouvre une modal pleine hauteur (drawer) avec :
- Liste de toutes les références par catégorie (actives + inactives)
- Formulaire d'ajout : Catégorie (select), Référence (texte), Désignation (texte), Seuil d'alerte (number)
- Sur chaque ligne : bouton Modifier (ouvre formulaire inline), bouton Désactiver/Réactiver
- Pas de suppression définitive si des mouvements existent (le backend renvoie 400, afficher l'erreur)

---

## ÉTAPE 6 — Onglet Historique des mouvements (`buildHistorique()`)

### 6.1 Structure

**Barre de filtres (sticky sous la searchbar globale) :**

```
[Type de stock ▼]  [Catégorie ▼]  [Mouvement ▼]  [Date début]  [Date fin]  [Appliquer]  [Export CSV]
```

Sur mobile : les filtres s'affichent dans un panneau collapsible ("Filtres" avec chevron).

**Options des filtres :**
- Type de stock : Tout / Matières premières / Produits finis
- Catégorie : Tout / Mandrins / Palettes / Adhésifs / Cartons (désactivé si Type = Produits finis)
- Mouvement : Tout / Entrée / Sortie / Ajustement / Inventaire / Transfert
- Date début / Date fin : `<input type="date">`

**Comportement :** appel API `GET /api/stock/historique-mouvements?...` avec les filtres actifs à chaque clic "Appliquer". Charger les 200 premiers par défaut au montage.

### 6.2 Tableau des mouvements

**Format desktop (table) :**

| Date | Type | Catégorie / Produit | Référence | Mouvement | Qté | Avant | Après | Ref BL / Note | Opérateur |
|---|---|---|---|---|---|---|---|---|---|

**Format mobile (cards) :**
Une card par mouvement avec :
- En-tête : date + badge type stock + badge type mouvement (coloré)
- Corps : référence en bold + désignation
- Footer : Qté / Avant→Après / Opérateur
- Si ref_bl ou note : ligne grisée en dessous

**Badges couleur type mouvement :**
- `entree` / `inventaire` → vert (`--success`)
- `sortie` → rouge (`--danger`)
- `ajustement` → orange (`--warn`)
- `transfert` → bleu (`--accent`)

**Badges type stock :**
- `mp` → fond violet clair, texte "Matière"
- `produit` → fond bleu-gris clair, texte "Produit"

### 6.3 Export CSV

Bouton "Export CSV" : appel `GET /api/stock/historique-mouvements?...&format=csv` avec les mêmes filtres actifs. L'endpoint retourne un fichier CSV téléchargeable (`Content-Disposition: attachment; filename="historique_stock_YYYYMMDD.csv"`).

Ajouter ce paramètre `format=csv` à l'endpoint existant. Colonnes CSV : Date, Type stock, Catégorie, Référence, Désignation, Mouvement, Quantité, Avant, Après, Ref BL, Note, Opérateur.

---

## Règles design à respecter absolument

### Variables CSS
Ne jamais coder de couleurs en dur. Toujours utiliser les variables CSS :
```css
--bg, --card, --border, --text, --text2, --muted
--accent, --accent-bg
--success, --warn, --danger
```
Tester que le thème light (`body.light`) fonctionne correctement sur toutes les nouvelles UI.

### Composants
- **Boutons** : `border-radius: 10px`, `font-weight: 700`, `transition: filter .15s`
- **Inputs** : `border-radius: 10px`, `padding: 12px 16px`, focus avec `border-color: var(--accent)` + box-shadow `rgba(34,211,238,.12)`
- **Cards** : `background: var(--card)`, `border: 1px solid var(--border)`, `border-radius: 12px`
- **Toasts** : utiliser `showToast(message, type)` — types `success`, `danger`, `info`. Aucun `alert()`.

### Mobile first
Toutes les nouvelles interfaces doivent être immédiatement utilisables sur mobile (portrait, ~375px). En particulier :
- Les modals de mouvement doivent s'afficher en plein écran sur mobile
- La liste des matières doit avoir des zones de tap suffisamment grandes (min 44px de hauteur)
- Les filtres de l'historique doivent être accessibles via un panneau collapsible

### Searchbars
Appliquer le pattern de préservation du focus défini dans CLAUDE.md : sauvegarder `activeElement`, `selectionStart`, `selectionEnd` avant tout re-render, restaurer après.

### Messages
- Erreurs : factuelles et actionnables. Ex. : "Stock insuffisant — stock actuel : 3 pal." pas "Une erreur s'est produite."
- Succès : courts. Ex. : "Mouvement enregistré." pas "Votre mouvement a bien été enregistré avec succès !"
- Aucun emoji dans les messages ou toasts.

---

## Ce qu'il ne faut PAS toucher

- **`data/production.db`** : ne jamais manipuler directement, ni modifier `DB_PATH`
- **`config.py` (racine)** : source de vérité pour la config — ne pas modifier `app/config.py`
- **`frontend/` et `routers/` (racine)** : shims de compatibilité — ne rien y ajouter
- **`app/web/traca_guide_js.py`** : module de traçabilité — ne pas toucher
- **Les endpoints existants** : ne pas modifier leurs signatures ni leur comportement. Seulement ajouter des clés à la réponse de `/api/stock/dashboard`.
- **La logique FIFO des produits finis** : ne pas modifier `apply_fifo_sortie()`
- **Les rôles et permissions existants** : ne pas modifier la logique de `require_stock()` et `require_stock_write()`

---

## Ordre d'implémentation recommandé

1. Migrations DB (`app/core/database.py`) → tester en lançant l'app, vérifier que les tables sont créées
2. Endpoints API matières premières (`app/routers/stock.py`) → tester avec curl ou HTTPie
3. Endpoint historique unifié → tester les filtres
4. Mise à jour endpoint dashboard
5. Refonte sidebar + renommage Dashboard (changements CSS/JS dans `stock_page.py`)
6. Onglet Matières premières (`buildMatieres()`) — vue liste + modals mouvement
7. Panneau de gestion des références admin
8. Tableau de bord rénové (`buildDashboard()`)
9. Onglet Historique (`buildHistorique()`)
10. Vérification thème light sur toutes les nouvelles UI
11. Test mobile sur toutes les nouvelles UI (utiliser les DevTools navigateur, viewport 375px)

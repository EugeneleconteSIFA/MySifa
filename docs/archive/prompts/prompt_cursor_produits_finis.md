# Prompt Cursor — Onglet "Produits finis" dans MyStock

## Contexte

Dans `app/web/stock_page.py`, la page MyStock contient déjà un onglet "Matières premières". Je veux ajouter un onglet **"Produits finis"** en suivant exactement la même architecture de la page (variables CSS, composants, conventions JS).

## Ce qu'il faut faire

### 1. Ajouter l'onglet dans la navigation de la page stock

Dans `stock_page.py`, repère les onglets existants (matières premières, etc.) et ajoute un bouton onglet **"Produits finis"** avec le même style. L'onglet doit être activé/désactivé via la même logique JS que les autres onglets.

---

### 2. Structure du panneau "Produits finis"

Le panneau (`id="tab-produits-finis"`) doit suivre cette structure HTML/CSS :

#### A — Barre de contrôle (toujours visible en haut du panneau)

```
[ Rechercher un produit (réf, désignation, OF…) ]   [ Rechercher un emplacement ]   [+ Entrée]  [- Sortie]
```

- Deux inputs de recherche côte à côte (filtrent la liste en temps réel, `oninput`)
- Bouton **"Entrée"** : class `btn btn-accent`, ouvre la modal d'entrée
- Bouton **"Sortie"** : class `btn btn-danger`, ouvre la modal de sortie
- Respecter la règle de focus : sauvegarder/restaurer `document.activeElement` avant tout re-render

#### B — Tableau de bord (deux colonnes)

**Colonne gauche — Stock actuel**

Tableau ou liste de cards avec pour chaque produit :
- Référence produit (bold)
- Désignation
- Quantité en stock (avec unité)
- Emplacement (badge coloré)
- Date dernière entrée (format `DD/MM/YYYY`)
- Bouton "Détail" → ouvre modal historique

Filtrage en temps réel selon la searchbar produit ET la searchbar emplacement (les deux s'appliquent simultanément).

**Colonne droite — Derniers mouvements**

Liste des 20 derniers mouvements (entrées + sorties), triés du plus récent au plus ancien :
- Icône ↑ (entrée, couleur `--success`) ou ↓ (sortie, couleur `--danger`)
- Référence produit + quantité
- Emplacement
- Horodatage (`DD/MM HH:MM`)
- Utilisateur

#### C — Ligne de KPI (bas du panneau, avant la liste)

3 cartes `.card` côte à côte :
- **Références en stock** : nombre de références distinctes avec quantité > 0
- **Mouvements aujourd'hui** : nb d'entrées + sorties du jour
- **Emplacements occupés** : nb d'emplacements avec au moins un produit

---

### 3. Modals

#### Modal "Entrée produit" (`id="modal-pf-entree"`)

Champs :
- **Référence produit** : input texte avec autocomplete/picker (cherche dans les produits connus), obligatoire
- **Désignation** : input texte, auto-rempli si ref connue, éditable
- **Quantité** : input number (min 0.01, step 0.01), obligatoire
- **Unité** : select (pièces, kg, m, bobines…)
- **Emplacement** : input texte avec picker (cherche dans les emplacements existants), obligatoire
- **N° OF** : input texte, facultatif
- **Commentaire** : textarea, facultatif

Boutons : "Annuler" (ghost) + "Enregistrer" (accent)

#### Modal "Sortie produit" (`id="modal-pf-sortie"`)

Mêmes champs que l'entrée, plus :
- **Motif / Destinataire** : input texte, facultatif

Boutons : "Annuler" (ghost) + "Enregistrer" (danger)

#### Modal "Détail produit" (`id="modal-pf-detail"`)

- En-tête : référence + désignation + stock actuel
- Tableau de l'historique complet des mouvements sur cette référence (date, type, quantité, emplacement, OF, utilisateur)
- Bouton fermer

---

### 4. Backend — `app/routers/stock.py`

Ajouter les endpoints suivants :

```
GET  /api/stock/produits-finis              → liste tous les produits finis avec stock actuel
GET  /api/stock/produits-finis/mouvements   → liste les N derniers mouvements (param: limit=20)
GET  /api/stock/produits-finis/{ref}        → détail + historique d'une référence
POST /api/stock/produits-finis/entree       → enregistre une entrée
POST /api/stock/produits-finis/sortie       → enregistre une sortie
```

Body POST entrée/sortie (JSON) :
```json
{
  "reference": "string",
  "designation": "string",
  "quantite": 0.0,
  "unite": "string",
  "emplacement": "string",
  "no_of": "string|null",
  "commentaire": "string|null"
}
```

---

### 5. Base de données — `app/core/database.py`

Ajouter deux tables via une **migration numérotée** (pattern `schema_migrations`) :

```sql
-- Table produits finis (catalogue)
CREATE TABLE IF NOT EXISTS produits_finis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reference TEXT NOT NULL UNIQUE,
    designation TEXT NOT NULL,
    unite TEXT DEFAULT 'pièces',
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime'))
);

-- Table mouvements produits finis
CREATE TABLE IF NOT EXISTS pf_mouvements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reference TEXT NOT NULL,
    designation TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('entree', 'sortie')),
    quantite REAL NOT NULL,
    unite TEXT DEFAULT 'pièces',
    emplacement TEXT NOT NULL,
    no_of TEXT,
    commentaire TEXT,
    user_login TEXT,
    date_mouvement TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime'))
);
```

Le stock actuel par référence+emplacement se calcule par agrégation sur `pf_mouvements` (somme des entrées - somme des sorties).

---

### 6. Conventions à respecter impérativement

- **Couleurs** : uniquement via variables CSS (`--accent`, `--danger`, `--success`, `--card`, `--border`, `--text`, `--text2`, `--muted`, `--bg`)
- **Toasts** : `showToast(message, 'success'|'danger'|'info')` — jamais de `alert()`
- **Icônes** : SVG inline, pas d'emojis dans les icônes fonctionnelles
- **État JS** : dans l'objet `S` central — pas de variables globales séparées
- **Searchbar** : restaurer focus + caret après tout re-render (voir règle dans CLAUDE.md)
- **quantite** est `REAL` → toujours `parseFloat()` côté JS
- **Migrations DB** : vérifier `schema_migrations` avant création de table, incrémenter le numéro de version
- **Imports config** : toujours depuis `config` (racine), jamais `app.config`
- **Messages** : ton factuel, pas d'emojis — ex. "Entrée enregistrée." pas "Super, c'est fait !"
- **Actions destructives** (sortie importante) : demander confirmation via modal, pas window.confirm

---

### 7. Annonce de mise à jour

Une fois le développement terminé, proposer le HTML d'annonce à poster via `POST /api/updates` :
- `scope` : `"stock"`
- `titre` : `"MyStock — Produits finis"`
- Message décrivant la nouvelle fonctionnalité, au format template CLAUDE.md

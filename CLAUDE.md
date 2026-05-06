# MySifa — Instructions pour Claude / Cursor / Windsurf

## Contexte projet

MySifa est un outil interne de gestion de production industrielle développé pour SIFA. Il est utilisé quotidiennement par des opérateurs, des responsables de production et des administrateurs. L'outil tourne sur un VPS Linux et est servi via FastAPI.

**Modules actifs :**

| Module | Route | Description |
|---|---|---|
| MyProd | `/prod` | Saisie de production opérateur |
| Planning machine | `/planning` | Planning atelier multi-machines |
| MyStock | `/stock` | Gestion des stocks et emplacements |
| MyCompta | `/compta` | Suivi comptable |
| MyExpé | `/expe` | Gestion des départs |
| Planning RH | `/planning-rh` | Planning du personnel |
| Paie | `/paie` | Module paie |
| Paramètres | `/settings` | Gestion comptes, rôles, annonces (super admin) |

---

## Stack technique

- **Backend** : Python 3 / FastAPI — point d'entrée `main.py` à la racine
- **Frontend** : HTML/CSS/JS vanilla, généré côté serveur en chaînes Python (dans `app/web/*.py`)
- **Base de données** : SQLite unique — fichier actif : `data/production.db` (chemin défini par `DB_PATH` dans `config.py`)
- **Auth** : sessions cookie (`sifa_token`), durée 6h
- **Migrations DB** : pattern `_migrate()` dans `app/core/database.py`, versionnées via la table `schema_migrations`

**Rôles disponibles :**
`superadmin`, `direction`, `administration`, `fabrication`, `logistique`, `comptabilite`, `expedition`, `commercial`

---

## Structure des fichiers

```
MySifa/
├── main.py                   # Point d'entrée FastAPI (lancer l'app depuis ici)
├── config.py                 # Configuration centrale (DB_PATH, rôles, constantes) — SOURCE DE VÉRITÉ
├── database.py               # Shim de compatibilité → pointe vers app/core/database.py
├── operations.json           # Référentiel codes opérations (severity, label, category)
├── requirements.txt
│
├── app/
│   ├── core/
│   │   └── database.py       # Schéma DB, migrations, helpers get_db() — NE PAS DUPLIQUER
│   ├── routers/              # Tous les endpoints FastAPI (source réelle)
│   │   ├── auth.py
│   │   ├── fabrication.py    # API saisie de production
│   │   ├── planning.py       # API planning machine
│   │   ├── settings.py       # API paramètres + annonces MAJ
│   │   ├── stock.py, compta.py, expe_departs.py, paie.py, planning_rh.py …
│   ├── web/                  # Pages HTML/CSS/JS (source réelle)
│   │   ├── html.py           # Layout commun, login, portail, sidebar (~8700 lignes)
│   │   ├── planning_page.py  # Page planning (~3100 lignes)
│   │   ├── fabrication_page.py # Page saisie production (~2200 lignes)
│   │   ├── stock_page.py     # Page stock (~3200 lignes)
│   │   ├── settings_page.py  # Page paramètres admin (~1500 lignes)
│   │   └── …
│   ├── services/             # Logique métier réutilisable
│   └── models/               # Modèles Pydantic
│
├── frontend/                 # Shims de compatibilité → pointent vers app/web/ (ne pas modifier)
├── routers/                  # Shims de compatibilité → pointent vers app/routers/ (ne pas modifier)
│
├── data/
│   ├── production.db         # BASE ACTIVE — ne jamais supprimer ni écraser
│   ├── uploads/              # Fichiers uploadés par les utilisateurs
│   └── emplacements_plan.csv
│
├── scripts/                  # Scripts de maintenance one-shot (migrations, imports, repairs)
└── tools/                    # Utilitaires (backup, import CSV, deploy)
```

**Règle absolue sur la DB — CRITIQUE, NE JAMAIS ENFREINDRE :**

La base de données active sur le VPS est `/home/sifa/production-saas/app/data/production.db`.
Ce chemin est défini dans `.env` via `DB_PATH=/home/sifa/production-saas/app/data/production.db`.

- **Ne jamais modifier `DB_PATH` dans `.env`**, ni directement ni via `sed`, ni via un script
- **Ne jamais déplacer, renommer, remplacer ou créer un symlink** sur `app/data/production.db`
- **Ne jamais copier une autre DB par-dessus** sans backup explicite et confirmation de l'utilisateur
- Les fichiers `mysifa.db` (racine ou data/) sont des fantômes vides — les ignorer
- `production.db` à la racine est une ancienne archive — ne pas utiliser
- En local (Mac), la base active est `data/production.db` — les données à jour sont toujours sur le VPS

Ces règles ont été violées deux fois par des IA (Cursor puis Claude) et ont causé des pertes de données. Toute modification de chemin DB nécessite une confirmation explicite de l'utilisateur.

**Règle absolue sur config.py :** `config.py` à la racine est la source de vérité. `app/config.py` est une vieille copie incomplète. Tout import de configuration doit venir de `config.py` (racine).

---

## Conventions de code

**JavaScript (frontend)**
- État central dans un objet `S` — ne jamais stocker d'état dans des variables globales séparées
- Fonctions de rendu : `render()`, `renderEntries()`, `renderTL()` — elles reconstruisent le DOM
- Appels API via la fonction locale `api(path, options)` qui gère credentials et JSON
- Les modals sont injectés dans `document.getElementById("mroot").innerHTML = …`
- `escHtml()` et `escAttr()` obligatoires pour toute interpolation de données utilisateur dans le HTML
- `duree_heures` est `REAL` en DB — toujours `parseFloat()`, jamais `parseInt()`
- `date_operation` est stocké en `"%Y-%m-%dT%H:%M:%S"` heure Paris (pas de timezone dans la chaîne)

**Python (backend)**
- Migrations DB : `if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=N LIMIT 1").fetchone()`
- Seeds idempotents : toujours `INSERT OR IGNORE`
- Ne jamais bloquer une saisie pour une erreur de mise à jour planning : `try/except: pass`
- Imports de config toujours depuis `config` (racine), jamais depuis `app.config`

---

## Design system — règles à respecter absolument

### Thème et variables CSS

```css
/* Dark (défaut) */
--bg: #0a0e17
--card: #111827
--border: #1e293b
--text: #f1f5f9
--text2: #cbd5e1
--muted: #94a3b8
--accent: #22d3ee
--accent-bg: rgba(34,211,238,0.12)
--success: #34d399   /* alias --ok */
--warn: #fbbf24
--danger: #f87171

/* Light (body.light) */
--bg: #f1f5f9
--card: #ffffff
--border: #e2e8f0
--text: #0f172a
--accent: #0891b2
```

**Ne jamais utiliser de couleurs codées en dur** — toujours les variables CSS. Le thème light doit être testé systématiquement si on modifie des couleurs.

### Typographie
- Police : `'Segoe UI', system-ui, sans-serif`
- Tailles courantes : labels 12px / corps 13px / titres 15px / brand 32px
- Labels formulaires : uppercase, letter-spacing 0.5px, font-weight 600

### Composants communs

**Boutons**
```css
.btn { border-radius: 10px; padding: 10px 18px; font-weight: 700; transition: filter .15s }
.btn:hover { filter: brightness(1.05) }
/* Variantes : .btn-accent (fond --accent), .btn-danger (fond --danger), .btn-ghost (transparent) */
```

**Inputs / Champs**
```css
background: var(--bg); border: 1px solid var(--border); border-radius: 10px;
padding: 12px 16px; color: var(--text); font-size: 14px;
transition: border-color .15s
input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(34,211,238,.12) }
```

**Cards**
```css
background: var(--card); border: 1px solid var(--border); border-radius: 12px;
```

**Toasts** : `showToast(message, type)` — `type` parmi `success`, `danger`, `info`. Jamais de popup `alert()`.

**Icônes** : SVG inline via la fonction `icon(name, size)` — pas d'emojis dans les icônes fonctionnelles.

---

## Cohérence inter-applications — règle fondamentale

**Toutes les pages de MySifa partagent exactement la même sidebar et le même footer.** Quand on crée un nouvel onglet ou une nouvelle application, copier fidèlement la structure de `app/web/html.py` :

### Sidebar (structure invariable)
```
Logo MySifa (haut)
─────────────────
Liens de navigation (.nav-btn)
  → icône SVG + label + badge optionnel (.nav-badge)
  → état actif : class .active + background accent-bg + couleur accent
─────────────────
.sidebar-bottom (bas, collé au bas via margin-top:auto)
  → .user-chip (nom + rôle de l'utilisateur connecté)
  → .theme-btn (bascule dark/light)
  → .logout-btn (déconnexion)
  → .version (numéro de version monospace)
```

**Ne jamais omettre le `.sidebar-bottom`**. Ne jamais changer l'ordre des éléments du bas. Le bouton logout doit toujours être présent.

### Topbar mobile
La topbar mobile (`.mobile-topbar`) est toujours présente et contient :
- Bouton menu hamburger (`.mobile-menu-btn`) → toggle classe `sb-open` sur `body`
- Titre de la page courante + sous-titre optionnel (`.mobile-topbar-sub`)
- Bouton retour portail (`.mobile-home-btn`) si pertinent

### Comportement sidebar mobile
- La sidebar est fixée, masquée via `translateX(-105%)` sur mobile
- `body.sb-open` l'affiche
- Un overlay `.sidebar-overlay` ferme la sidebar au clic en dehors

### Liens de navigation
Toujours inclure les liens vers les modules auxquels l'utilisateur a accès (vérifiés via le contexte de session). La cohérence des icônes entre pages est obligatoire — si un module utilise un certain SVG dans une page, il doit utiliser le même dans toutes les autres.

---

## UX — principes fondamentaux

**L'utilisateur d'abord.** Chaque fonctionnalité doit être immédiatement compréhensible sans explication. Si ça nécessite un guide, c'est que l'interface n'est pas assez claire.

**Visuel et direct.** Préférer les états visuels (couleurs, indicateurs, badges) aux messages texte. Un statut doit se lire en un coup d'œil, pas en lisant une phrase.

**Intuitif.** Les actions courantes (saisir, filtrer, chercher, valider) doivent être accessibles sans navigation. Les actions destructives demandent toujours une confirmation.

**Réactif.** Toute action utilisateur doit avoir un retour immédiat (toast, état de chargement, changement visuel). Ne jamais laisser l'utilisateur se demander si son action a été prise en compte.

**Cohérent.** Le même mot, la même couleur, le même geste doit signifier la même chose partout dans l'application. Si un bouton bleu confirme dans une page, il confirme partout.

---

## Searchbars — règles de comportement obligatoires

Les searchbars sont un point de friction fréquent. Règles à respecter impérativement :

### Ne jamais perdre le focus après un `render()`

Quand une searchbar déclenche un re-render du DOM (`renderEntries()`, `renderTL()`, etc.), le champ perd son focus si le DOM est reconstruit. **Pattern obligatoire :**

```javascript
// Avant le render, sauvegarder l'état du focus
function renderEntries() {
  const ae = document.activeElement;
  const focusId = ae?.id;
  const caretStart = ae?.selectionStart;
  const caretEnd = ae?.selectionEnd;

  // … reconstruction du DOM …

  // Après le render, restaurer le focus ET la position du curseur
  if (focusId) {
    const el = document.getElementById(focusId);
    if (el) {
      el.focus();
      if (caretStart != null) {
        try { el.setSelectionRange(caretStart, caretEnd); } catch(e) {}
      }
    }
  }
}
```

### Ne jamais reconstruire le conteneur de la searchbar elle-même
La searchbar doit être dans un conteneur qui n'est pas re-rendu. Seule la liste de résultats est reconstruite.

### Comportement attendu d'une searchbar
- Filtre dès le premier caractère saisi (pas de bouton "Rechercher")
- Résultats en temps réel à chaque `oninput`
- Touche `Escape` vide le champ et restaure la liste complète
- Message explicite si aucun résultat : "Aucun résultat pour « [terme] »"
- Le placeholder décrit les champs cherchés : ex. `"Rechercher (client, OF, réf produit…)"`

### Searchbar dans un picker/modal
Autofocus automatique à l'ouverture :
```javascript
requestAnimationFrame(() => { document.getElementById("search-id")?.focus(); });
```
Les touches `ArrowUp` / `ArrowDown` / `Enter` naviguent dans les résultats sans soumettre le formulaire.

---

## Terminologie métier (à respecter partout, y compris dans les messages)

| Terme technique | Affiché / utilisé |
|---|---|
| `statut = attente` | En attente |
| `statut = en_cours` | En cours |
| `statut = termine` | Terminé |
| `statut_reel = reellement_en_saisie` | ⚙ en saisie |
| `statut_reel = reellement_termine` | ✓ saisie terminé |
| `operation_code = 01` | Début de production |
| `operation_code = 89` | Fin de production |
| `fin_dossier = true` | Dossier clôturé |
| `no_dossier` | Référence dossier |
| `planning_entries` | Dossiers au planning |
| `production_data` | Saisies de production |
| Machines | Cohésio 1, Cohésio 2, DSI, Repiquage |

---

## Ton et style éditorial

- **Pas d'emojis** dans les messages, toasts, labels, annonces ou release notes
- Icônes neutres acceptées : →, ·, ✓, ×, ▸ et SVG inline
- Ton **professionnel et direct** — pas de formules commerciales, pas de "Bonjour !", pas de "De belles nouveautés vous attendent"
- Les messages d'erreur sont **factuels et actionnables** : "Durée invalide — valeur entre 0.25 et 24h." plutôt que "Oups, quelque chose s'est mal passé."
- Les confirmations de succès sont **courtes** : "Saisie enregistrée." pas "Votre saisie a bien été enregistrée avec succès !"

---

## Annonces de mise à jour (MAJ importantes)

Quand une mise à jour significative est développée (nouvelle fonctionnalité, changement d'interface, correction majeure), **proposer systématiquement un message d'annonce** à insérer via l'API `POST /api/updates`.

Le message (`message` field) doit être en **HTML** et respecter les codes visuels de MySifa :

```html
<!-- Template annonce MAJ — à adapter -->
<div style="font-size:13px;line-height:1.7;color:var(--text2)">
  <div style="font-size:15px;font-weight:700;color:var(--text);margin-bottom:12px">
    Mise à jour — v0.X.Y
  </div>

  <div style="margin-bottom:10px;font-weight:600;color:var(--text);font-size:12px;
       text-transform:uppercase;letter-spacing:.5px">Nouveautés</div>
  <ul style="margin:0 0 14px 0;padding-left:18px">
    <li style="margin-bottom:5px">Description précise et factuelle de la nouveauté.</li>
    <li style="margin-bottom:5px">Autre nouveauté.</li>
  </ul>

  <div style="margin-bottom:10px;font-weight:600;color:var(--text);font-size:12px;
       text-transform:uppercase;letter-spacing:.5px">Corrections</div>
  <ul style="margin:0;padding-left:18px">
    <li style="margin-bottom:5px">Correction décrite sobrement.</li>
  </ul>
</div>
```

**Champs à renseigner :**
- `scope` : identifiant de la page concernée (`planning`, `prod`, `stock`, `global`, etc.)
- `titre` : titre court en style release notes, ex. `"Planning — Filtres et performances"`
- `message` : HTML ci-dessus
- `active` : `true`

---

## Points d'attention critiques

**Base de données**
- `duree_heures` est `REAL` — toujours `parseFloat()` côté JS
- `date_operation` stocké en `"%Y-%m-%dT%H:%M:%S"` heure Paris (pas de timezone dans la chaîne)
- `TERMINE_KEEP = 2` : les 2 derniers dossiers terminés restent visibles dans la liste
- Toute nouvelle colonne doit être ajoutée via une migration numérotée dans `_migrate()`

**Frontend**
- La scroll position doit être préservée après tout `renderEntries()` ou drag & drop
- `_autoScrollKey` est basé uniquement sur l'ID du dossier `en_cours`
- Les slots timeline sont positionnés en absolu sur les jours travaillés uniquement (jours off filtrés)
- Ne jamais reconstruire le DOM d'une modal ouverte pendant un refresh automatique — vérifier `document.getElementById("mroot").firstElementChild` avant tout re-render global

**Routing**
- `frontend/` et `routers/` à la racine sont des **shims** — ne pas y ajouter de logique
- Tout nouveau router doit être créé dans `app/routers/` et enregistré dans `main.py`
- Toute nouvelle page doit être créée dans `app/web/` et enregistrée dans `main.py`

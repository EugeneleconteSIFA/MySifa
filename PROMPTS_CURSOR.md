# Prompts Cursor — MySifa améliorations planning

Chaque prompt est autonome et peut être donné tel quel à Cursor.
Ordre suggéré : 1 → 2 → 3 → 4 → 5 → 6 → 7.

---

## PROMPT 1 — Slot trop étroit : affichage client vertical

**Fichier ciblé :** `app/web/planning_page.py`

**Contexte précis :**
Dans la fonction `mkTL()`, la ligne 2186 contient la condition `${w>5?...}` qui décide si le contenu du slot est affiché. Quand `w <= 5` (largeur en % de la timeline), le slot est affiché vide — aucun texte. C'est le cas des dossiers très courts (ex. 1h sur une vue 2 semaines).

**Ce qu'il faut faire :**
Remplacer le bloc :
```js
${w>5?`<div class="slot-inner">...(contenu complet)...</div>`:""}
```
par une logique à trois niveaux :

- **`w > 5`** (slot large) → comportement inchangé : `.slot-inner` avec `.line1`, `.line2`, `.line3`
- **`w > 1.8 && w <= 5`** (slot étroit) → afficher le nom du client verticalement :
  - Texte = `cli.slice(0, 6) + (cli.length > 6 ? '.' : '')`, en majuscules
  - Style : `writing-mode: vertical-rl; text-orientation: mixed; transform: rotate(180deg); font-size: 9px; font-weight: 700; color: #1e293b; overflow: hidden; max-height: 100%; pointer-events: none; white-space: nowrap;`
  - Entourer d'un `<div>` avec `overflow:hidden; height:100%; display:flex; align-items:center; justify-content:center;`
- **`w <= 1.8`** (slot minuscule) → rien, comme actuellement

**Règles impératives :**
- Ne modifier que la partie HTML du slot (le template string dans `mkTL`)
- Ne pas toucher au CSS existant des classes `.slot`, `.slot-inner`, `.line1`, `.line2`, `.line3`
- `cli` est déjà calculé juste avant : `const cli=(s.client||"").trim()||(s.numero_of||s.reference||"—");`
- Vérifier que le thème light est toujours lisible (la couleur `#1e293b` est valide en light et dark pour ce cas)

---

## PROMPT 2 — Ajouter la vue "4 semaines"

**Fichier ciblé :** `app/web/planning_page.py`

**Contexte précis — 6 endroits à modifier :**

**A. Ligne ~589 — init localStorage :**
```js
let _planView=localStorage.getItem("mysifa.planning.view")||"2w";
if(_planView==="4w")_planView="2w";  // ← SUPPRIMER cette ligne
```
Supprimer uniquement la ligne `if(_planView==="4w")_planView="2w";`.

**B. Lignes ~960–992 — 4 fonctions loadDayWorked / loadDayHoraires / loadHolidays / loadCalendarComments :**
Chacune contient `const nb=S.view==="1w"?6:13;`
Remplacer par : `const nb=S.view==="1w"?6:S.view==="4w"?27:13;`

**C. Ligne ~1556 — calcul `nw` dans le premier bloc `renderTL` :**
```js
const nw=S.view==="1w"?1:2;
```
Remplacer par : `const nw=S.view==="1w"?1:S.view==="4w"?4:2;`

**D. Ligne ~1825 — même calcul `nw` dans le second bloc `renderTL` (après drag & drop) :**
Même remplacement : `const nw=S.view==="1w"?1:S.view==="4w"?4:2;`

**E. Ligne ~1615 — HTML des boutons de vue :**
```html
<button type="button" class="view-tab ${S.view==="1w"?"active":""}" onclick="setView('1w')">Semaine</button>
<button type="button" class="view-tab ${S.view==="2w"?"active":""}" onclick="setView('2w')">2 semaines</button>
```
Ajouter après le bouton "2 semaines" :
```html
<button type="button" class="view-tab ${S.view==="4w"?"active":""}" onclick="setView('4w')">4 semaines</button>
```

**F. Ligne ~3643 — fonction `setView` :**
```js
function setView(v){
  if(v==="4w")v="2w";  // ← SUPPRIMER cette ligne
  ...
}
```
Supprimer uniquement la ligne `if(v==="4w")v="2w";`.

**Règles impératives :**
- Ne modifier que ces 6 points, rien d'autre
- La vue 4 semaines affiche les semaines à partir du lundi courant (même logique `S.wo * 7` que pour 2 semaines), en empilant 4 blocs timeline au lieu de 2
- Vérifier que `buildLegend(sl, m1, nw)` aux lignes ~1676 et ~1855 reçoit bien le `nw` mis à jour (il doit l'être automatiquement puisqu'il utilise la variable locale déjà modifiée)

---

## PROMPT 3 — Afficher "qté. étiq." dans le slot si un OF PDF est lié

**Fichiers ciblés :**
1. `app/routers/planning.py` — endpoint timeline
2. `app/web/planning_page.py` — rendu du slot et tooltip

**Contexte précis :**
L'OF PDF est importé et lié via `/api/of/validate`. Il stocke `qte_etiquettes` dans la table `of` (ou similaire). La timeline est chargée via `GET /api/machines/{machine_id}/timeline` qui retourne `{ slots: [...] }`. Chaque slot est un objet avec les champs du dossier (client, laize, format_l, format_h, date_livraison, etc.).

**Étape 1 — Backend (`app/routers/planning.py`) :**
Dans l'endpoint qui construit les slots de timeline, vérifier la jointure avec la table `of`. S'assurer que chaque slot retourne deux champs supplémentaires :
- `qte_etiquettes` : valeur numérique si un OF lié existe et a ce champ renseigné, sinon `null`
- `has_of` : booléen `true` si un OF est lié à ce dossier

Si la jointure n'existe pas encore : faire un `LEFT JOIN` sur la table `of` via la clé étrangère `of_id` (ou `entry_id`) et sélectionner `of.qte_etiquettes`.

**Étape 2 — Frontend (`app/web/planning_page.py`) :**

*A. Dans la fonction `mkTL`, juste après la ligne `const cli=...` (~ligne 2154) :*
```js
const qteEtiq = (s.qte_etiquettes != null && s.has_of) ? s.qte_etiquettes : null;
```

*B. Modifier le `.slot-inner` (condition `w>5`, ligne ~2186) pour ajouter une ligne "qté. étiq." après `.line3` :*
```js
${qteEtiq != null ? `<span class="line3" style="color:var(--accent);margin-top:2px">qté. étiq. : ${escAttr(String(qteEtiq))}</span>` : ""}
```
Cette ligne s'insère entre `.line3` et `.line-exig`.

*C. Dans la fonction `showTip` (ligne ~2321), ajouter dans `tip-grid` après la ligne Statut :*
```js
${qteEtiq != null ? `<span class="k">Qté étiquettes</span><span class="v" style="color:var(--accent);font-weight:600">${d.qteEtiq}</span>` : ""}
```
Pour cela, ajouter `data-qte-etiq="${escAttr(qteEtiq!=null?String(qteEtiq):"")}"`  dans les attributs `data-*` du div `.slot` (aux côtés de `data-ref`, `data-fmt`, etc.).

**Règles impératives :**
- Afficher la ligne uniquement si `has_of === true` ET `qte_etiquettes` est une valeur non nulle (pas 0 accepté comme valeur valide)
- Ne pas casser le layout quand `qteEtiq` est null
- Respecter le design : couleur `var(--accent)` pour distinguer visuellement cette info OF

---

## PROMPT 4 — Bug mobile : sidebar inaccessible dans MyProd (fabrication_page)

**Fichier ciblé :** `app/web/fabrication_page.py`

**Contexte précis du bug :**
Sur mobile, quand l'utilisateur ouvre le menu sidebar en appuyant sur le bouton hamburger, la sidebar s'affiche (classe `sb-open` sur `body`) mais les clics à l'intérieur de la sidebar ne fonctionnent pas — comme si un rideau transparent était posé dessus.

**Cause identifiée :**
La hiérarchie des `z-index` est cassée dans `fabrication_page.py` :
- `#mroot` → `z-index: 1100` (ligne ~328) avec `pointer-events:none` mais **`#mroot>*{pointer-events:auto}`**
- `.fab-sidebar` → `z-index: 300` (ligne ~568)
- `.fab-sidebar-overlay` → `z-index: 190`
- `.fab-topbar.mobile-topbar` → `z-index: 200`

Résultat : quand `#mroot` contient un enfant (dock, widget, ou tout élément persistant injecté par `mysifa_dock.js`, `support_widget.js` ou autre), cet enfant à z-index effectif 1100 capture les événements et bloque les interactions avec la sidebar à z-index 300.

**Ce qu'il faut faire :**
Deux corrections CSS dans le bloc `<style>` de `fabrication_page.py` :

1. Dans la media query `@media(max-width:900px)`, ajouter :
```css
body.sb-open .fab-sidebar { z-index: 4000; }
body.sb-open .fab-sidebar-overlay { z-index: 3900; }
```

2. Ajouter aussi une règle pour que `#mroot` et ses enfants ne bloquent pas les interactions quand la sidebar est ouverte :
```css
body.sb-open #mroot { pointer-events: none !important; }
body.sb-open #mroot > * { pointer-events: none !important; }
```

**Règle impérative :**
- Ne modifier que le CSS dans le bloc `<style>` de `fabrication_page.py`, pas la logique JS
- Vérifier que ces règles n'entrent pas en conflit avec les modals/overlays à z-index 9000+ (ils ne seront pas affectés car ils s'ouvrent après fermeture de la sidebar)

---

## PROMPT 5 — Formulaire dossier : sections + champs département et RDV

**Fichiers ciblés :**
1. `app/core/database.py` — migration DB
2. `app/routers/planning.py` — endpoints GET/PUT entries
3. `app/web/planning_page.py` — fonctions `dossierFields()`, `getFormData()`, `openEdit()`

**Contexte :**
La fonction `dossierFields(numero_of, client, ref_produit, laize, date_livraison, commentaire, exigences_production, fl, fh, dur, statut, showStatut, aPlacer=1, fscRequis=0, fscType="")` (ligne ~2810 dans `planning_page.py`) génère tous les champs du formulaire en une liste plate. Il faut la restructurer en sections, ajouter deux nouveaux champs, et adapter toute la chaîne backend.

---

### Étape 1 — Migration DB (`app/core/database.py`)

Ajouter dans la fonction `_migrate()`, après la dernière migration numérotée existante :

```python
# Migration N+1 : champs département livraison et prise de RDV sur planning_entries
ver = <PROCHAIN_NUMERO>
if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=? LIMIT 1", (ver,)).fetchone():
    conn.execute("ALTER TABLE planning_entries ADD COLUMN departement_livraison TEXT DEFAULT ''")
    conn.execute("ALTER TABLE planning_entries ADD COLUMN prise_rdv INTEGER DEFAULT 0")
    conn.execute("INSERT INTO schema_migrations(version) VALUES(?)", (ver,))
    conn.commit()
```
Remplacer `<PROCHAIN_NUMERO>` par le numéro suivant la dernière migration dans le fichier.

---

### Étape 2 — Backend (`app/routers/planning.py`)

- Dans l'endpoint GET entries : s'assurer que `departement_livraison` et `prise_rdv` sont retournés dans chaque objet entrée
- Dans l'endpoint PUT/PATCH entry (modification) : accepter et persister `departement_livraison` (TEXT) et `prise_rdv` (INTEGER 0/1)

---

### Étape 3 — Frontend (`app/web/planning_page.py`)

**A. Modifier la signature de `dossierFields` pour accepter les deux nouveaux paramètres :**
```js
function dossierFields(numero_of, client, ref_produit, laize, date_livraison, commentaire,
  exigences_production, fl, fh, dur, statut, showStatut, aPlacer=1, fscRequis=0, fscType="",
  deptLivraison="", priseRdv=0)
```

**B. Restructurer le HTML retourné en 4 sections visuelles sur desktop :**

Utiliser une grille 2 colonnes sur desktop (`@media(min-width:901px)`) et colonne unique sur mobile.
Section container : `background:var(--bg); border:1px solid var(--border); border-radius:10px; padding:14px 16px; margin-bottom:12px`
Label de section : `font-size:10px; text-transform:uppercase; letter-spacing:.6px; font-weight:700; color:var(--muted); margin-bottom:12px; display:block`

Structure des sections :

**Section 1 — Informations générales** (colonne unique)
- Numéro d'OF (`f-of`)
- Client (`f-cli`)
- Durée (`f-dur` + barre de progression)
- Statut si `showStatut`
- Case "À placer au planning" (`f-aplacer`)

**Section 2 — Fiche produit** (grille 2 col sur desktop)
- Réf produit (`f-rp`)
- Laize mm (`f-laize`)
- Largeur mm (`f-fl`)
- Hauteur mm (`f-fh`)
- Certification FSC (case + select type) — sur toute la largeur

**Section 3 — Livraison** (grille 2 col sur desktop)
- Date de livraison (`f-dl`)
- Département de livraison (`f-dept`) : input texte, placeholder "Ex : 75, 69, Rhône…"
- Case à cocher "Prise de RDV" (`f-rdv`) : checkbox + label "Prendre un Rendez-Vous"

**Section 4 — Particularités et commentaires** (colonne unique)
- Commentaire (`f-com`)
- Exigences de production (`f-exig` — textarea)

**C. Modifier `getFormData()` pour inclure les deux nouveaux champs :**
```js
departement_livraison: (document.getElementById("f-dept")?.value || "").trim(),
prise_rdv: document.getElementById("f-rdv")?.checked ? 1 : 0,
```

**D. Modifier tous les appels à `dossierFields()` (openEdit, openAdd, openInsert) pour passer les deux nouveaux champs depuis `e.departement_livraison` et `e.prise_rdv`.**

**Règles impératives :**
- Respecter les variables CSS du design system pour toutes les couleurs (pas de couleurs hardcodées)
- Les sections doivent être cohérentes avec le thème light (tester `body.light`)
- Sur mobile (`max-width:900px`) : toujours une seule colonne, les sections s'empilent normalement
- La validation existante ne change pas : seul `numero_of` est requis

---

## PROMPT 6 — Ajouter un dossier : onglets "Manuel" et "Depuis un OF PDF"

**Fichier ciblé :** `app/web/planning_page.py`

**Contexte :**
La fonction `openAdd()` (ligne ~2900) affiche un modal simple avec `dossierFields()`. Il faut la transformer en modal à deux onglets. L'infrastructure OF PDF existe déjà dans la page : `_ofPlanningParsed`, `ofPlanningHandleFile()`, `/api/of/parse`, `/api/of/validate`. Il faut la réutiliser dans ce nouveau contexte.

**Architecture du nouveau modal :**

```
┌─────────────────────────────────────────┐
│ Ajouter un dossier                   [×]│
├─────────────────────────────────────────┤
│ [Manuel]  [Depuis un OF PDF]            │
├─────────────────────────────────────────┤
│ (contenu de l'onglet actif)             │
└─────────────────────────────────────────┘
```

**Ce qu'il faut faire :**

**A. Modifier `openAdd()` :**
Remplacer l'appel actuel à `modalHTML(...)` par un HTML custom injecté dans `#mroot` :
- Modal avec deux onglets : "Manuel" (actif par défaut) et "Depuis un OF PDF"
- Même style visuel que les autres modals : `.modal-backdrop`, largeur max 680px, header, footer avec boutons
- État de l'onglet actif stocké dans une variable locale `let _addTab = 'manual'`

**Onglet "Manuel" :**
Contient exactement `dossierFields("","","","","","","","","",8,"attente",false)` (le formulaire actuel avec les sections du prompt 5).
Bouton footer : `+ Ajouter` → appelle `submitAdd()` inchangée.

**Onglet "Depuis un OF PDF" :**
Contient une zone de dépôt PDF identique à celle utilisée dans l'import OF existant :
```html
<div class="of-dropzone" id="add-of-dropzone">
  [icône upload]
  Déposer le PDF de l'OF ici
  ou cliquer pour sélectionner
  .pdf uniquement
</div>
<input type="file" accept=".pdf" id="add-of-file-input" style="display:none">
```
- Au drop/sélection d'un fichier : appeler `/api/of/parse` (FormData avec le fichier)
- Pendant le parsing : afficher un état "Analyse en cours…"
- Après parsing réussi : afficher le formulaire pré-rempli avec les données de l'OF (réutiliser `dossierFields` avec les valeurs extraites) + un message "Vérifiez les informations avant de valider"
- Les champs non reconnus par l'OF restent vides et éditables
- Bouton footer : `Valider et créer le dossier` → crée l'entrée via `POST /api/machines/${MID}/entries` PUIS lie l'OF via `POST /api/of/validate` (avec l'ID de l'entrée nouvellement créée)

**B. Ajouter la fonction `openAddSwitchTab(tab)` :**
Bascule entre les onglets, met à jour les classes `.active` sur les boutons d'onglet, et re-rend le contenu de la zone.

**Règles impératives :**
- Les onglets utilisent le même style `.view-tab` / `.view-tabs` déjà présent dans la page
- Si l'utilisateur switch d'onglet, le formulaire est réinitialisé (pas de mémoire entre les onglets)
- En cas d'erreur de parsing PDF : `showToast("Erreur lecture PDF.", "danger")` et retour à la dropzone
- L'OF est lié APRÈS la création de l'entrée (deux appels API séquentiels), avec gestion d'erreur si le second échoue (toast warning, l'entrée est quand même créée)
- Pas de régression sur `openInsert()` ni `submitAdd()` existants

---

## PROMPT 7 — Vue Expé : renommages et sélecteur de vue planning

**Fichiers ciblés :** Page Expédition (chercher dans `app/web/` le fichier qui gère la route `/expe` — probablement `expe_page.py` ou `expe_departs_page.py`)

**Contexte :**
Dans la page Expédition, il existe un bouton/lien libellé "Vue planning" qui redirige vers `/planning`. Il faut :
1. Renommer ce bouton en **"Planning : Production"**
2. Ajouter un sélecteur de mode qui permet de choisir entre **"Planning : Production"**, **"Planning : Expédition"** et **"Planning : Production + Expédition"**

**Ce qu'il faut faire :**

**A. Renommer le bouton existant :**
Chercher dans la page Expédition toute occurrence de `"vue planning"`, `"Vue planning"`, `"Vue Planning"`, ou tout lien vers `/planning`. Le remplacer par le label **"Planning : Production"**.

**B. Ajouter un sélecteur de vue planning :**
À côté du bouton/lien renommé, ajouter un `<select>` (ou un groupe de boutons `.view-tab`) permettant de choisir entre les 3 modes :
```
Planning : Production          → /planning
Planning : Expédition          → /planning?vue=expe
Planning : Production + Expédition → /planning?vue=prod_expe
```
Le sélecteur persiste son choix dans `localStorage` (clé : `"mysifa.expe.planning.vue"`).

**C. Dans `app/web/planning_page.py` :**
Lire le paramètre URL `vue` (`URLSearchParams`) en JS au chargement de la page. Le stocker dans `S.planningVue` (valeurs : `"prod"` | `"expe"` | `"prod_expe"`). Par défaut : `"prod"`.
Pour le moment, **les trois vues sont visuellement identiques** — ne pas différencier le rendu. Afficher simplement un badge/label discret sous la topbar mobile ou dans le header indiquant la vue active ("Production", "Expédition", "Production + Expédition") pour confirmation visuelle.

**D. Dans `app/web/planning_page.py`, modifier le titre de la topbar mobile :**
Actuellement `"Planning"`. Le rendre dynamique selon `S.planningVue` :
- `"prod"` → `"Planning · Production"`
- `"expe"` → `"Planning · Expédition"`
- `"prod_expe"` → `"Planning · Prod + Expé"`

**Règles impératives :**
- Le comportement par défaut de `/planning` (sans paramètre `vue`) reste **inchangé** — vue Production, comme aujourd'hui
- Pas de modification de la logique de rendu des slots pour l'instant (les vues sont identiques)
- Le sélecteur dans la page Expé doit utiliser les classes CSS existantes du design system (`.btn`, `.btn-accent`, ou `.view-tab`)
- Ne pas modifier le routing FastAPI (côté Python) — tout est géré côté JS via le paramètre URL

---

*Généré le 27/05/2026 — à partir de l'analyse de `planning_page.py` (4145 lignes) et `fabrication_page.py` (3771 lignes)*

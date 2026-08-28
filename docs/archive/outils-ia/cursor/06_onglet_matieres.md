# Cursor Prompt 06 — Frontend : Onglet Matières premières

## Prérequis

Les prompts 01 à 05 ont été exécutés. L'API MP existe, la sidebar a l'onglet `matieres`.

## Contexte

Fichier à modifier : `app/web/stock_page.py`

Ajouter la fonction `buildMatieres()` qui construit tout le contenu de l'onglet "Matières premières". Elle est appelée quand `S.tab === 'matieres'`.

Les données sont chargées depuis `GET /api/stock/matieres` et stockées dans `S.matieres` (tableau).

---

## Chargement des données

```javascript
async function loadMatieres() {
  S.matieres = await api('/api/stock/matieres');
  buildMatieres();
}
```

Appeler `loadMatieres()` lors du clic sur l'onglet "Matières premières" et après chaque mouvement réussi.

---

## Structure de la page

### En-tête

- Titre : "Matières premières"
- À droite : bouton "Gérer les références" — visible uniquement si le rôle est `superadmin`, `direction` ou `administration` (vérifier depuis `S.user.role`). Ce bouton ouvre le panneau de gestion (voir section dédiée ci-dessous).

### Filtre par catégorie (pills)

Une rangée de pills filtrantes, stockée dans `S.matieresCat` (défaut : `'tout'`) :

```
[Tout]  [Mandrins]  [Palettes]  [Adhésifs]  [Cartons]
```

Clic sur une pill → met à jour `S.matieresCat` → appelle `buildMatieres()` (filtre local, sans appel API).

Style des pills :
```css
/* Pill inactive */
background: var(--card);
border: 1px solid var(--border);
border-radius: 20px;
padding: 6px 14px;
font-size: 12px;
font-weight: 600;
color: var(--text2);
cursor: pointer;

/* Pill active */
background: var(--accent-bg);
border-color: var(--accent);
color: var(--accent);
```

### Searchbar

Input texte, filtre en temps réel sur `reference` + `designation`. Appliquer le pattern de préservation du focus (sauvegarder `activeElement` + `selectionStart`/`selectionEnd` avant `buildMatieres()`, restaurer après). Stocker la valeur dans `S.matieresQ`.

Placeholder : `"Rechercher (référence, désignation…)"`

### Liste des matières

Filtrer `S.matieres` selon `S.matieresCat` et `S.matieresQ`, puis afficher une card par référence.

**Structure d'une card :**

```
┌─────────────────────────────────────────────────────────┐
│ [badge catégorie]  RÉFÉRENCE              [12 pal.]     │
│ Désignation                           [⚠ Sous le seuil] │
│                        [Entrée] [Sortie] [Ajust.] [Trf] │
└─────────────────────────────────────────────────────────┘
```

Détail :
- **Badge catégorie** (couleurs identiques au tableau de bord) :
  - `mandrin` → fond `rgba(124,58,237,0.15)`, texte `#7c3aed`, label "Mandrin"
  - `palette` → fond `rgba(8,145,178,0.15)`, texte `#0891b2`, label "Palette"
  - `adhesif` → fond `rgba(217,119,6,0.15)`, texte `#d97706`, label "Adhésif"
  - `carton` → fond `rgba(5,150,105,0.15)`, texte `#059669`, label "Carton"
- **Référence** : monospace, bold, 14px
- **Stock** : affiché en grand (`font-size: 20px; font-weight: 700; color: var(--text)`) + unité "pal."
- **Alerte** : si `en_alerte`, afficher `⚠ Sous le seuil (min. X pal.)` en `color: var(--warn); font-size: 12px`
- **Boutons d'action** : visibles uniquement si `!S.stockReadOnly`
  - Entrée (fond `--success` atténué) → `openModalMouvement('entree', matiere)`
  - Sortie (fond `--danger` atténué) → `openModalMouvement('sortie', matiere)`
  - Ajust. (fond `--warn` atténué) → `openModalMouvement('ajustement', matiere)`
  - Transfert (fond `--accent` atténué) → `openModalMouvement('transfert', matiere)`

**Sur mobile (< 640px) :** les 4 boutons d'action passent dans un menu déroulant (un bouton "···" qui affiche un petit menu inline) pour garder la card compacte.

**Si aucun résultat après filtrage :** afficher `"Aucune matière correspondant à « [terme] »."` centré, couleur `var(--muted)`.

---

## Modal de mouvement

Fonction `openModalMouvement(type, matiere)`. Injecter dans `document.getElementById("mroot")`.

### Champs communs à tous les types

- **Matière** : si `matiere` est fourni, afficher la référence + désignation en lecture seule. Sinon, afficher un select avec toutes les matières actives.
- **Type de mouvement** : affiché en lecture seule (verrouillé sur le type passé en paramètre), avec une icône et un label lisible :
  - `entree` → "Entrée en stock"
  - `sortie` → "Sortie de stock"
  - `ajustement` → "Ajustement d'inventaire"
  - `transfert` → "Transfert"
- **Note** : textarea optionnel, placeholder `"Commentaire (optionnel)"`

### Champs spécifiques

**Entrée uniquement :**
- Champ "Référence BL / Fournisseur" (texte, optionnel, placeholder `"BL-2024-001"`)
- Champ "Quantité (palettes)" : `<input type="number" min="0.5" step="0.5">`

**Sortie uniquement :**
- Champ "Quantité (palettes)" : `<input type="number" min="0.5" step="0.5">`
- Afficher sous le champ : `"Stock actuel : X pal."` en temps réel. Si la quantité saisie dépasse le stock, afficher `"Stock insuffisant."` en `var(--danger)`.

**Ajustement :**
- Champ "Nouveau stock (palettes)" remplace "Quantité" : `<input type="number" min="0" step="0.5">`
- Afficher : `"Stock actuel : X pal."` au-dessus du champ pour guider l'utilisateur.

**Transfert :**
- Champ "Quantité (palettes)" : `<input type="number" min="0.5" step="0.5">`
- Champ "Emplacement source" (texte libre, optionnel)
- Champ "Emplacement destination" (texte libre, optionnel)

### Soumission

```javascript
async function submitMouvement() {
  const body = { matiere_id, type_mouvement, quantite, ref_bl, note, emplacement_source, emplacement_dest };
  const res = await api('/api/stock/matieres/mouvement', { method: 'POST', body });
  if (res.ok) {
    closeMroot();
    showToast("Mouvement enregistré.", "success");
    await loadMatieres();
  } else {
    showToast(res.detail || "Erreur lors de l'enregistrement.", "danger");
  }
}
```

---

## Panneau de gestion des références (admin)

Déclenché par "Gérer les références". Ouvre un drawer (modal pleine hauteur à droite sur desktop, plein écran sur mobile).

### Contenu

**Liste des références existantes** par catégorie, avec pour chaque ligne :
- Badge catégorie + Référence + Désignation + Seuil + Statut (actif/inactif)
- Bouton "Modifier" → affiche un formulaire inline en dessous de la ligne (expand)
- Bouton "Désactiver" / "Réactiver" → appelle `PUT /api/stock/matieres/{id}` avec `{actif: 0}` ou `{actif: 1}`

**Formulaire d'ajout** (en bas du drawer) :
- Catégorie (select : Mandrin / Palette / Adhésif / Carton)
- Référence (texte, ex. "76MM-3P")
- Désignation (texte)
- Seuil d'alerte (number, en palettes, 0 = pas d'alerte)
- Bouton "Ajouter"

Après ajout réussi : recharger la liste des références dans le drawer + recharger `S.matieres`.

Si le backend retourne 400 (référence dupliquée) : afficher l'erreur sous le formulaire, ne pas fermer le drawer.

---

## Vérification

- [ ] La liste s'affiche et se filtre par catégorie et par searchbar
- [ ] Le focus de la searchbar est préservé après `buildMatieres()`
- [ ] Les 4 types de modaux s'ouvrent correctement et ont les bons champs
- [ ] Un mouvement Entrée incrémente le stock (visible après rechargement)
- [ ] Une Sortie avec quantité > stock affiche l'erreur sans planter
- [ ] Un Ajustement remplace le stock par la valeur absolue saisie
- [ ] Sur mobile (375px), les cards sont lisibles et les boutons d'action accessibles
- [ ] Le panneau admin s'ouvre uniquement pour les bons rôles
- [ ] Thème light : aucune couleur illisible

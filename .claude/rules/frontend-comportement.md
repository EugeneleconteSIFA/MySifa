---
paths:
  - "app/web/**/*.py"
  - "static/**/*.js"
---
## Fluidité des postes — mode éco automatique

Tous les postes de l'atelier ne se valent pas. `static/mysifa_perf.js`, chargé
dans le `<head>` de chaque page **sans `defer`**, compte les images réellement
affichées pendant une seconde après le chargement. Sous 30 images par seconde
(ou sur un faisceau d'indices : peu de cœurs, peu de RAM, rendu lent), il pose
`perf-eco` sur `<html>` et `<body>` — plus `reduce-anim`, que `motion.js` lit
déjà — et `static/mysifa_perf.css` coupe le fond animé, les `backdrop-filter`
et les transitions.

**Conséquences pour toute nouvelle page ou tout nouvel effet :**

- Un nouveau document HTML complet (un `app/web/*_page.py` de plus) doit
  inclure `mysifa_perf.css` **et** `mysifa_perf.js` dans son `<head>`, comme il
  inclut déjà `mysifa_theme.js`. Sans ça, la page reste lourde sur les postes
  lents alors que tout le reste de MySifa s'est allégé.
- Un effet coûteux (filtre SVG, `backdrop-filter`, animation d'un `filter` ou
  d'un `box-shadow`, animation plein écran) doit être écrit pour pouvoir
  disparaître : soit il tombe déjà sous une règle de `mysifa_perf.css`, soit on
  y ajoute la règle correspondante dans le même commit.
- Le verdict est **collant** : un poste passé en éco n'en ressort pas tout
  seul, puisqu'une nouvelle mesure se ferait effets coupés et serait bonne par
  construction. Le retour se fait dans Mon profil → « Fluidité de l'affichage »,
  bouton « Refaire la mesure ».
- L'utilisateur garde la main : Automatique / Complet / Allégé dans Mon profil
  (clé localStorage `mysifa_perf_mode`).

Côté serveur, chaque session remonte un relevé (`POST /api/perf/releve`, table
`perf_releves`). La vue `/perf-postes` (superadmin et direction, accessible depuis
Paramètres → Audit & qualité) classe les postes du plus lent au plus fluide et liste les pages les plus lourdes. Piège
de lecture : un poste déjà en éco mesure sans les effets, donc son FPS est bon
— c'est son passage en éco qui est le signal, pas son chiffre.

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

**Feedback cliquable sur le logo et tous les éléments interactifs de la
sidebar.** Le logo de chaque module (ex. `My<span>Qualité</span>`,
`My<span>Sifa</span>`, `My<span>Prod</span>`...) DOIT être cliquable pour
revenir au menu général du module — et cette cliquabilité DOIT être
visible :

- `cursor:pointer` sur le `.logo`
- Effet `:hover` cohérent avec les `.nav-btn` (fond `var(--accent-bg)`,
  couleur du texte principal qui bascule sur `var(--accent)`)
- `title=""` avec un texte explicite (ex. "Menu MyQualité")
- Handler `onclick="setView(\'menu\')"` ou équivalent

Règle générale : **tout élément cliquable de la sidebar (logo, cards,
badges, boutons)** doit avoir un état hover visible et un `cursor:pointer`.
Sans feedback visuel, l'utilisateur n'a aucun moyen de savoir qu'il
peut cliquer — bug rencontré sur le logo MyQualité (juillet 2026, ajouté
sans hover initialement).

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

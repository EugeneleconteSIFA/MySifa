# Cursor Prompt 04 — Frontend : Refonte sidebar MyStock

## Prérequis

Les prompts 01, 02, 03 ont été exécutés. L'API MP et l'historique existent.

## Contexte

Fichier à modifier : `app/web/stock_page.py`

Ce fichier contient une seule grande chaîne HTML/CSS/JS. La sidebar est construite en JS via la fonction `render()` (ou équivalent). L'état global JS est l'objet `S`.

**Lire le fichier avant de commencer** pour localiser exactement :
- La fonction JS qui construit la sidebar
- La liste des onglets actuels (`dashboard`, `referentiel`, `inventaire`, `reception`, `traca`)
- La variable `S.tab` et son initialisation
- Les conditions d'affichage par rôle (`S.tracaOnly`, `S.stockReadOnly`)

---

## Tâche

### 1. Ajouter deux nouveaux onglets à `S`

Étendre l'objet `S` pour accepter deux nouvelles valeurs de `S.tab` :
- `matieres` — onglet Matières premières
- `historique` — onglet Historique des mouvements

S'assurer que `render()` et `buildPage()` (ou l'équivalent qui dispatche selon `S.tab`) gèrent ces deux nouvelles valeurs sans erreur. Pour l'instant, elles peuvent afficher un contenu vide ou un placeholder — les vrais contenus viennent dans les prompts 05, 06 et 07.

### 2. Renommer "Dashboard" en "Tableau de bord"

Partout dans le fichier : label dans la sidebar, titre de page affiché dans le contenu, et dans le `<title>` si présent.

### 3. Restructurer la sidebar en 3 sections

Remplacer la liste d'onglets actuelle par cette structure avec des séparateurs de section.

**Structure exacte :**

```
Tableau de bord          ← premier item, pas de label de section au-dessus

── MATIÈRES PREMIÈRES ─  ← label de section
Matières premières

── PRODUITS ────────────  ← label de section
Référentiel
Inventaire
Réception matière

── OUTILS ──────────────  ← label de section
Historique mouvements
Étiquettes traça
```

**Icônes SVG à utiliser :**
- Tableau de bord : icône existante `grid`
- Matières premières : icône `layers` (3 rectangles empilés) — SVG inline
- Référentiel : icône existante `tag`
- Inventaire : icône existante `clipboard`
- Réception matière : icône existante `inbox`
- Historique mouvements : icône `clock` — SVG inline
- Étiquettes traça : icône existante `printer`

**SVG pour `layers` (à inliner) :**
```svg
<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polygon points="12 2 2 7 12 12 22 7 12 2"/>
  <polyline points="2 17 12 22 22 17"/>
  <polyline points="2 12 12 17 22 12"/>
</svg>
```

**SVG pour `clock` (à inliner) :**
```svg
<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="10"/>
  <polyline points="12 6 12 12 16 14"/>
</svg>
```

### 4. CSS pour les labels de section

Ajouter ce style dans le bloc `<style>` existant :

```css
.nav-section-label {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  color: var(--muted);
  font-weight: 600;
  padding: 14px 16px 4px 16px;
  user-select: none;
  pointer-events: none;
}
```

Les labels de section sont des `<div class="nav-section-label">` insérés entre les groupes de `.nav-btn`.

### 5. Règles d'affichage par rôle (ne pas casser l'existant)

- Si `S.tracaOnly` (rôle `fabrication`) : afficher uniquement "Étiquettes traça", sans labels de section
- Si `S.stockReadOnly` (rôle `commercial`) : masquer l'onglet Inventaire, afficher le reste normalement
- L'onglet "Matières premières" est visible pour tous les rôles ayant accès à MyStock (sauf `tracaOnly`)
- L'onglet "Historique mouvements" est visible pour tous sauf `tracaOnly`

### 6. Mobile topbar

La topbar mobile affiche le titre de l'onglet actif. S'assurer que les nouveaux onglets ont un titre défini :
- `matieres` → "Matières premières"
- `historique` → "Historique"

---

## Ce qu'il ne faut pas toucher

- La logique du `.sidebar-bottom` (user chip, thème, logout, version) — ne pas la déplacer ni la modifier
- La logique d'auth et de session
- Les fonctions `buildReferentielPage()`, `buildInventaire()`, `buildReception()`, `buildTraca()` — les laisser intactes
- Le comportement de la searchbar globale

---

## Vérification

Charger MyStock dans le navigateur. Vérifier :
- [ ] Les 3 labels de section apparaissent avec le bon style
- [ ] Tous les onglets existants fonctionnent encore normalement
- [ ] Les onglets "Matières premières" et "Historique mouvements" apparaissent et sont cliquables (contenu vide accepté pour l'instant)
- [ ] Sur mobile (viewport 375px), la sidebar s'ouvre et ferme correctement
- [ ] Le thème light (`body.light`) n'altère pas les labels de section

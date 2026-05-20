# Prompt Cursor — Ajout de 3 nouvelles palettes de thème

## Contexte

MySifa dispose d'un système de thèmes CSS géré par `static/mysifa_theme.js` et `static/mysifa_theme.css`.
Les préférences sont sauvegardées en `localStorage` (`mysifa_palette`, `mysifa_style`, `theme`) et synchronisées
côté serveur via `PUT /api/auth/me`.

Actuellement 3 palettes existent : `mysifa` (Cyan, défaut), `forge` (Ambre), `cocon` (Pivoine).

L'objectif est d'ajouter 3 nouvelles palettes : **Forêt**, **Cendre** et **Braise**.
Chaque palette a une variante dark et une variante light (`body.palette-xxx.light`).

---

## Fichiers à modifier (dans cet ordre)

### 1. `static/mysifa_theme.css`

Ajouter les 3 nouveaux blocs de variables CSS à la fin du fichier, avant les règles `style-mini` / `style-round`.

```css
/* ── Palette Forêt (vert profond / mousse) ── */
body.palette-foret {
  --bg: #081a0f;
  --card: #0f2416;
  --border: #1a3d24;
  --text: #e8f5e9;
  --text2: #a5c8a8;
  --muted: #5a8a65;
  --accent: #4caf72;
  --accent-bg: rgba(76, 175, 114, 0.13);
  --filter-input-bg: #0b1f12;
  --success: #34d399;
  --warn: #fbbf24;
  --danger: #f87171;
  --c1: #4caf72;
  --c2: #a5c8a8;
  --c3: #34d399;
  --c4: #fbbf24;
  --c5: #f87171;
}
body.palette-foret.light {
  --bg: #f0f7f1;
  --card: #ffffff;
  --border: #c3dfc8;
  --text: #0f2414;
  --text2: #2d5e35;
  --muted: #5a8a65;
  --accent: #2d7a42;
  --accent-bg: rgba(45, 122, 66, 0.10);
  --filter-input-bg: #ffffff;
  --success: #059669;
  --warn: #b45309;
  --danger: #dc2626;
  --c1: #2d7a42;
  --c2: #2d5e35;
  --c3: #059669;
  --c4: #b45309;
  --c5: #dc2626;
}

/* ── Palette Cendre (gris · ardoise froide) ── */
body.palette-cendre {
  --bg: #0f1115;
  --card: #1a1d24;
  --border: #2c3040;
  --text: #e8eaf0;
  --text2: #9ba0b2;
  --muted: #636878;
  --accent: #94a3b8;
  --accent-bg: rgba(148, 163, 184, 0.12);
  --filter-input-bg: #131619;
  --success: #34d399;
  --warn: #fbbf24;
  --danger: #f87171;
  --c1: #94a3b8;
  --c2: #9ba0b2;
  --c3: #34d399;
  --c4: #fbbf24;
  --c5: #f87171;
}
body.palette-cendre.light {
  --bg: #f4f5f7;
  --card: #ffffff;
  --border: #d1d5db;
  --text: #111827;
  --text2: #374151;
  --muted: #9ca3af;
  --accent: #475569;
  --accent-bg: rgba(71, 85, 105, 0.10);
  --filter-input-bg: #ffffff;
  --success: #059669;
  --warn: #b45309;
  --danger: #dc2626;
  --c1: #475569;
  --c2: #374151;
  --c3: #059669;
  --c4: #b45309;
  --c5: #dc2626;
}

/* ── Palette Braise (brun-noir / orange brûlé) ── */
body.palette-braise {
  --bg: #1a0a00;
  --card: #281400;
  --border: #4d2400;
  --text: #fff0e8;
  --text2: #ffb87a;
  --muted: #a06040;
  --accent: #ff6c20;
  --accent-bg: rgba(255, 108, 32, 0.14);
  --filter-input-bg: #1f0d00;
  --success: #34d399;
  --warn: #fbbf24;
  --danger: #ff6060;
  --c1: #ff6c20;
  --c2: #ffb87a;
  --c3: #34d399;
  --c4: #fbbf24;
  --c5: #ff6060;
}
body.palette-braise.light {
  --bg: #fff7f0;
  --card: #fffefb;
  --border: #f0d0b0;
  --text: #2a0f00;
  --text2: #7a3010;
  --muted: #b07040;
  --accent: #c04010;
  --accent-bg: rgba(192, 64, 16, 0.09);
  --filter-input-bg: #fffefb;
  --success: #2e7d32;
  --warn: #d06000;
  --danger: #c0392b;
  --c1: #c04010;
  --c2: #7a3010;
  --c3: #2e7d32;
  --c4: #d06000;
  --c5: #c0392b;
}
```

---

### 2. `static/mysifa_theme.js`

Modifier les 3 tableaux de constantes pour inclure les nouvelles palettes :

```js
// Ligne ~12 — remplacer :
var PALETTES = ['mysifa', 'forge', 'cocon'];
// par :
var PALETTES = ['mysifa', 'forge', 'cocon', 'foret', 'cendre', 'braise'];

// Ligne ~14 — remplacer :
var THEME_CLASSES = ['light', 'palette-forge', 'palette-cocon', 'style-mini', 'style-round'];
// par :
var THEME_CLASSES = ['light', 'palette-forge', 'palette-cocon', 'palette-foret', 'palette-cendre', 'palette-braise', 'style-mini', 'style-round'];
```

Aucune autre modification dans ce fichier. La logique `normalizePalette`, `applyPrefs`, `setPrefs`, etc. fonctionne
déjà de façon générique via les tableaux PALETTES et THEME_CLASSES.

---

### 3. `app/web/profil_page.py`

**A — Ajouter les 3 nouvelles entrées dans le tableau `PALETTE_DEF`** (après l'entrée `cocon`) :

```js
{id:'foret',  name:'Forêt',   sub:'Vert profond · mousse',
  prev:`<div style="background:#081a0f;width:100%;height:100%;border-radius:6px;display:flex;align-items:center;justify-content:center;gap:5px">
    <div style="width:9px;height:9px;border-radius:50%;background:#4caf72"></div>
    <div style="width:9px;height:9px;border-radius:50%;background:#4caf72;opacity:.55"></div>
    <div style="width:9px;height:9px;border-radius:50%;background:#a5c8a8;opacity:.6"></div>
  </div>`},
{id:'cendre', name:'Cendre',  sub:'Gris ardoise · froid',
  prev:`<div style="background:#0f1115;width:100%;height:100%;border-radius:6px;display:flex;align-items:center;justify-content:center;gap:5px">
    <div style="width:9px;height:9px;border-radius:50%;background:#94a3b8"></div>
    <div style="width:9px;height:9px;border-radius:50%;background:#94a3b8;opacity:.6"></div>
    <div style="width:9px;height:9px;border-radius:50%;background:#636878;opacity:.7"></div>
  </div>`},
{id:'braise', name:'Braise',  sub:'Orange brûlé · brun',
  prev:`<div style="background:#1a0a00;width:100%;height:100%;border-radius:6px;display:flex;align-items:center;justify-content:center;gap:5px">
    <div style="width:9px;height:9px;border-radius:50%;background:#ff6c20"></div>
    <div style="width:9px;height:9px;border-radius:50%;background:#ff6c20;opacity:.55"></div>
    <div style="width:9px;height:9px;border-radius:50%;background:#ffb87a;opacity:.65"></div>
  </div>`},
```

**B — Ajouter les règles de hover box-shadow** pour les 3 nouvelles palettes dans le bloc `<style>` en tête de page.
Chercher les lignes existantes :
```css
body.palette-forge .nav-btn:hover:not(.active){...}
body.palette-cocon .nav-btn:hover:not(.active){...}
```
Et ajouter immédiatement après :
```css
body.palette-foret .nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(76,175,114,.28),0 0 16px rgba(76,175,114,.14)}
body.palette-cendre .nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(148,163,184,.28),0 0 16px rgba(148,163,184,.14)}
body.palette-braise .nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(255,108,32,.28),0 0 16px rgba(255,108,32,.14)}
```

Chercher les lignes existantes :
```css
body.palette-forge .theme-btn:hover{...}
body.palette-cocon .theme-btn:hover{...}
```
Et ajouter immédiatement après :
```css
body.palette-foret .theme-btn:hover{box-shadow:0 0 0 1px rgba(76,175,114,.24),0 0 18px rgba(76,175,114,.12)}
body.palette-cendre .theme-btn:hover{box-shadow:0 0 0 1px rgba(148,163,184,.24),0 0 18px rgba(148,163,184,.12)}
body.palette-braise .theme-btn:hover{box-shadow:0 0 0 1px rgba(255,108,32,.24),0 0 18px rgba(255,108,32,.12)}
```

---

### 4. `app/web/html.py` (optionnel mais recommandé)

Dans le bloc `<style>` global (chercher `body.palette-forge .nav-btn:hover:not(.active)` et
`body.palette-cocon .nav-btn:hover:not(.active)`), ajouter les mêmes règles de hover
que ci-dessus pour que le glow soit cohérent sur toutes les pages, pas seulement le profil.

---

## Règles à ne pas enfreindre

- Ne pas modifier `DB_PATH` dans `.env` ni toucher `data/production.db`.
- Ne pas modifier `app/config.py` — seul `config.py` à la racine est la source de vérité.
- Ne pas ajouter de couleurs codées en dur dans les composants — uniquement via les variables CSS.
- Ne pas créer de nouveaux fichiers JS ou CSS séparés — tout dans `mysifa_theme.css` et `mysifa_theme.js`.
- Les shims `frontend/` et `routers/` à la racine ne doivent pas être modifiés.

## Vérification

Après les modifications :
1. Ouvrir la page `/profil` — l'onglet "Thème et apparence" doit afficher 6 cartes de palette.
2. Sélectionner "Forêt" : le fond doit virer au vert sombre (`#081a0f`), l'accent au vert (`#4caf72`).
3. Activer le mode clair avec Forêt : fond `#f0f7f1`, accent `#2d7a42`.
4. Répéter pour Cendre et Braise.
5. Recharger la page : la préférence doit être restaurée depuis `localStorage`.

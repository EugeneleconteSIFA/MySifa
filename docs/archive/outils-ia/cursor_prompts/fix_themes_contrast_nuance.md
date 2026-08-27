# Prompt Cursor — Refonte du contraste et de la nuance des 4 palettes de thème

## Problème à corriger

Les 4 palettes (Pivoine, Forêt, Cendre, Braise) manquent de contraste et de nuance.
L'objectif est de les aligner sur la logique des palettes **Cyan** (défaut) et **Ambre** qui fonctionnent bien :

**Ce qui fait que Cyan et Ambre fonctionnent :**
1. `--bg` est quasi-noir (~#0a–#0f) et `--card` s'en détache clairement (~10–15 pts de delta luminosité)
2. `--text2` est **neutre et désaturé** — il N'EST PAS de la couleur de l'accent
3. `--accent` est la **seule** couleur vive — tout le reste est des neutres teintés
4. En mode clair, `--bg` est distinctement teinté (pas blanc, pas gris générique) et `--card` est blanc pur `#ffffff` — fort contraste

**Ce qui ne va pas dans les palettes actuelles :**
- Pivoine : `--text2: #e8b0c8` → trop rose, même famille que l'accent `#ff5c98`
- Forêt : `--bg: #081a0f` trop vert/lisible, `--text2: #a5c8a8` trop vert, quasi identique à l'accent
- Cendre : `--accent: #94a3b8` → gris sur gris, aucun caractère
- Braise : `--bg: #1a0a00` pas assez profond, `--text2: #ffb87a` trop orange, même famille que l'accent

---

## Fichier à modifier : `static/mysifa_theme.css`

Remplacer **intégralement** les 4 blocs de palettes (Pivoine/cocon, Forêt, Cendre, Braise) par les valeurs suivantes.
Ne pas toucher aux blocs `style-mini` et `style-round`.

---

### Palette Pivoine (cocon)

```css
/* ── Palette Pivoine (fond quasi-noir / magenta vif) ── */
body.palette-pivoine,
body.palette-cocon {
  --bg: #0e040c;
  --card: #1c0d18;
  --border: #3d1834;
  --text: #faeef6;
  --text2: #b888a4;
  --muted: #7a4870;
  --accent: #f03888;
  --accent-bg: rgba(240, 56, 136, 0.14);
  --filter-input-bg: #120810;
  --success: #34d399;
  --warn: #f0b240;
  --danger: #ff6060;
  --c1: #f03888;
  --c2: #b888a4;
  --c3: #34d399;
  --c4: #f0b240;
  --c5: #ff6060;
}
body.palette-pivoine.light,
body.palette-cocon.light {
  --bg: #faedf4;
  --card: #ffffff;
  --border: #eec8dc;
  --text: #1a0412;
  --text2: #5c1840;
  --muted: #a86088;
  --accent: #c01460;
  --accent-bg: rgba(192, 20, 96, 0.09);
  --filter-input-bg: #ffffff;
  --success: #2e7d32;
  --warn: #d06000;
  --danger: #c0392b;
  --c1: #c01460;
  --c2: #5c1840;
  --c3: #2e7d32;
  --c4: #d06000;
  --c5: #c0392b;
}
```

**Changements clés :**
- `--bg` : `#1a0a14` → `#0e040c` (quasi-noir, juste un soupçon de magenta)
- `--card` : `#2a1020` → `#1c0d18` (delta visible vs bg)
- `--text2` : `#e8b0c8` → `#b888a4` (mauve désaturé, pas rose vif)
- `--accent` : `#ff5c98` → `#f03888` (plus vivid, plus magenta)
- Light `--bg` : `#fef8f2` → `#faedf4` (teinté rose distinctement)
- Light `--card` : `#fffdfb` → `#ffffff` (blanc pur, contraste fort)

---

### Palette Forêt

```css
/* ── Palette Forêt (quasi-noir / vert vif) ── */
body.palette-foret {
  --bg: #060d08;
  --card: #0e1c12;
  --border: #1c3820;
  --text: #eef5ef;
  --text2: #8fa898;
  --muted: #506058;
  --accent: #3dd67e;
  --accent-bg: rgba(61, 214, 126, 0.13);
  --filter-input-bg: #08110a;
  --success: #34d399;
  --warn: #fbbf24;
  --danger: #f87171;
  --c1: #3dd67e;
  --c2: #8fa898;
  --c3: #34d399;
  --c4: #fbbf24;
  --c5: #f87171;
}
body.palette-foret.light {
  --bg: #ecf5ed;
  --card: #ffffff;
  --border: #bfdfc6;
  --text: #06160a;
  --text2: #2a5034;
  --muted: #5a7860;
  --accent: #187a3a;
  --accent-bg: rgba(24, 122, 58, 0.10);
  --filter-input-bg: #ffffff;
  --success: #059669;
  --warn: #b45309;
  --danger: #dc2626;
  --c1: #187a3a;
  --c2: #2a5034;
  --c3: #059669;
  --c4: #b45309;
  --c5: #dc2626;
}
```

**Changements clés :**
- `--bg` : `#081a0f` → `#060d08` (beaucoup plus sombre, quasi-noir avec micro-tinte verte)
- `--card` : `#0f2416` → `#0e1c12` (delta propre, forêt profonde)
- `--text2` : `#a5c8a8` → `#8fa898` (sage gris-vert désaturé, pas vert vif)
- `--accent` : `#4caf72` → `#3dd67e` (plus lumineux, plus contrasté sur le fond sombre)
- Light `--bg` : `#f0f7f1` → `#ecf5ed` (teinté vert distinctement, pas beige ni gris)
- Light `--card` : `#ffffff` (blanc pur)

---

### Palette Cendre

**Problème central** : l'accent gris `#94a3b8` sur fond gris = thème plat, aucun caractère.
Solution : le fond/card/texte restent gris-froids, mais l'accent devient **bleu acier** — métallique, froid, distinctif.

```css
/* ── Palette Cendre (quasi-noir froid / bleu acier) ── */
body.palette-cendre {
  --bg: #080a0f;
  --card: #11151e;
  --border: #202840;
  --text: #edf0f8;
  --text2: #848ea8;
  --muted: #505870;
  --accent: #6496c8;
  --accent-bg: rgba(100, 150, 200, 0.13);
  --filter-input-bg: #0b0e16;
  --success: #34d399;
  --warn: #fbbf24;
  --danger: #f87171;
  --c1: #6496c8;
  --c2: #848ea8;
  --c3: #34d399;
  --c4: #fbbf24;
  --c5: #f87171;
}
body.palette-cendre.light {
  --bg: #edf0f7;
  --card: #ffffff;
  --border: #cdd4e4;
  --text: #080c1a;
  --text2: #303a58;
  --muted: #8890a8;
  --accent: #2a5c9a;
  --accent-bg: rgba(42, 92, 154, 0.09);
  --filter-input-bg: #ffffff;
  --success: #059669;
  --warn: #b45309;
  --danger: #dc2626;
  --c1: #2a5c9a;
  --c2: #303a58;
  --c3: #059669;
  --c4: #b45309;
  --c5: #dc2626;
}
```

**Changements clés :**
- `--bg` : `#0f1115` → `#080a0f` (plus profond, bleu-noir)
- `--card` : `#1a1d24` → `#11151e` (delta propre, nuit froide)
- `--text2` : `#9ba0b2` → `#848ea8` (ardoise désaturée, pas accent)
- `--accent` : `#94a3b8` (gris) → `#6496c8` (**bleu acier** — unique, froid, distinctif)
- Light `--bg` : `#f4f5f7` (gris neutre) → `#edf0f7` (distinctement bleu-froid, comme Ambre a `#EFF3FA`)
- Light `--accent` : `#475569` (slate) → `#2a5c9a` (bleu acier profond, lisible)

---

### Palette Braise

```css
/* ── Palette Braise (quasi-noir chaud / orange brûlé) ── */
body.palette-braise {
  --bg: #0e0500;
  --card: #1c0d00;
  --border: #3d1e00;
  --text: #fdf0e6;
  --text2: #b8907a;
  --muted: #806050;
  --accent: #f07030;
  --accent-bg: rgba(240, 112, 48, 0.14);
  --filter-input-bg: #120700;
  --success: #34d399;
  --warn: #fbbf24;
  --danger: #ff6060;
  --c1: #f07030;
  --c2: #b8907a;
  --c3: #34d399;
  --c4: #fbbf24;
  --c5: #ff6060;
}
body.palette-braise.light {
  --bg: #fdf0e6;
  --card: #ffffff;
  --border: #efd8c0;
  --text: #180800;
  --text2: #5c2800;
  --muted: #a06040;
  --accent: #b83c00;
  --accent-bg: rgba(184, 60, 0, 0.09);
  --filter-input-bg: #ffffff;
  --success: #2e7d32;
  --warn: #d06000;
  --danger: #c0392b;
  --c1: #b83c00;
  --c2: #5c2800;
  --c3: #2e7d32;
  --c4: #d06000;
  --c5: #c0392b;
}
```

**Changements clés :**
- `--bg` : `#1a0a00` → `#0e0500` (beaucoup plus sombre, quasi-noir chaud)
- `--card` : `#281400` → `#1c0d00` (delta bien visible sur le fond très sombre)
- `--text2` : `#ffb87a` → `#b8907a` (brun-beige désaturé — pas orange, pas dans la famille de l'accent)
- `--accent` : `#ff6c20` → `#f07030` (légèrement moins saturé pour éviter la fatigue visuelle)
- Light `--bg` : `#fff7f0` → `#fdf0e6` (crème chaud marqué, distinctif)
- Light `--card` : `#fffefb` → `#ffffff` (blanc pur, contraste fort)

---

## Fichier à modifier : `app/web/profil_page.py`

Mettre à jour les `prev` des 4 palettes dans `PALETTE_DEF` pour refléter les nouvelles couleurs.
Chercher la constante `PALETTE_DEF` et remplacer les 4 entrées concernées :

```js
{id:'pivoine', name:'Pivoine', sub:'Rose vif · quasi-noir',
  prev:`<div style="background:#0e040c;width:100%;height:100%;border-radius:6px;display:flex;align-items:center;justify-content:center;gap:5px">
    <div style="width:9px;height:9px;border-radius:50%;background:#f03888"></div>
    <div style="width:9px;height:9px;border-radius:50%;background:#f03888;opacity:.5"></div>
    <div style="width:9px;height:9px;border-radius:50%;background:#b888a4;opacity:.55"></div>
  </div>`},
{id:'cocon',  name:'Pivoine',  sub:'Rose vif · quasi-noir',
  prev:`<div style="background:#0e040c;width:100%;height:100%;border-radius:6px;display:flex;align-items:center;justify-content:center;gap:5px">
    <div style="width:9px;height:9px;border-radius:50%;background:#f03888"></div>
    <div style="width:9px;height:9px;border-radius:50%;background:#f03888;opacity:.5"></div>
    <div style="width:9px;height:9px;border-radius:50%;background:#b888a4;opacity:.55"></div>
  </div>`},
{id:'foret',  name:'Forêt',   sub:'Vert vif · quasi-noir',
  prev:`<div style="background:#060d08;width:100%;height:100%;border-radius:6px;display:flex;align-items:center;justify-content:center;gap:5px">
    <div style="width:9px;height:9px;border-radius:50%;background:#3dd67e"></div>
    <div style="width:9px;height:9px;border-radius:50%;background:#3dd67e;opacity:.5"></div>
    <div style="width:9px;height:9px;border-radius:50%;background:#8fa898;opacity:.6"></div>
  </div>`},
{id:'cendre', name:'Cendre',  sub:'Bleu acier · nuit froide',
  prev:`<div style="background:#080a0f;width:100%;height:100%;border-radius:6px;display:flex;align-items:center;justify-content:center;gap:5px">
    <div style="width:9px;height:9px;border-radius:50%;background:#6496c8"></div>
    <div style="width:9px;height:9px;border-radius:50%;background:#6496c8;opacity:.55"></div>
    <div style="width:9px;height:9px;border-radius:50%;background:#848ea8;opacity:.65"></div>
  </div>`},
{id:'braise', name:'Braise',  sub:'Orange brûlé · quasi-noir',
  prev:`<div style="background:#0e0500;width:100%;height:100%;border-radius:6px;display:flex;align-items:center;justify-content:center;gap:5px">
    <div style="width:9px;height:9px;border-radius:50%;background:#f07030"></div>
    <div style="width:9px;height:9px;border-radius:50%;background:#f07030;opacity:.5"></div>
    <div style="width:9px;height:9px;border-radius:50%;background:#b8907a;opacity:.65"></div>
  </div>`},
```

Note : si la palette `cocon` et `pivoine` sont deux entrées séparées dans `PALETTE_DEF`, les mettre à jour toutes les deux avec les mêmes valeurs. Si c'est une seule entrée avec `id:'cocon'`, garder ce seul id.

---

## Aussi à mettre à jour : les règles de hover box-shadow dans `profil_page.py`

Chercher les lignes de hover existantes (ex. `body.palette-forge .theme-btn:hover{...}`) et remplacer les règles pour les 4 palettes :

```css
body.palette-pivoine .nav-btn:hover:not(.active),
body.palette-cocon .nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(240,56,136,.28),0 0 16px rgba(240,56,136,.14)}

body.palette-foret .nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(61,214,126,.28),0 0 16px rgba(61,214,126,.14)}

body.palette-cendre .nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(100,150,200,.28),0 0 16px rgba(100,150,200,.14)}

body.palette-braise .nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(240,112,48,.28),0 0 16px rgba(240,112,48,.14)}

body.palette-pivoine .theme-btn:hover,
body.palette-cocon .theme-btn:hover{box-shadow:0 0 0 1px rgba(240,56,136,.24),0 0 18px rgba(240,56,136,.12)}

body.palette-foret .theme-btn:hover{box-shadow:0 0 0 1px rgba(61,214,126,.24),0 0 18px rgba(61,214,126,.12)}

body.palette-cendre .theme-btn:hover{box-shadow:0 0 0 1px rgba(100,150,200,.24),0 0 18px rgba(100,150,200,.12)}

body.palette-braise .theme-btn:hover{box-shadow:0 0 0 1px rgba(240,112,48,.24),0 0 18px rgba(240,112,48,.12)}
```

---

## Règles à ne pas enfreindre

- Ne pas modifier `DB_PATH` dans `.env` ni toucher `data/production.db`
- Ne pas modifier `app/config.py`
- Ne pas ajouter de couleurs codées en dur dans les composants — uniquement via les variables CSS
- Ne pas créer de nouveaux fichiers — tout dans `mysifa_theme.css`
- Ne pas modifier les palettes **Ambre** (`palette-forge`) et **Cyan** (`palette-mysifa`)
- Ne pas modifier les blocs `style-mini` et `style-round`

## Vérification

1. Sélectionner "Forêt" en dark : fond quasi-noir `#060d08`, cards distinctement plus claires, accent vert vif `#3dd67e`, textes secondaires en sage-gris — PAS en vert
2. Sélectionner "Cendre" en dark : fond bleu-noir `#080a0f`, accent **bleu acier** `#6496c8` — PAS gris
3. Sélectionner "Braise" en dark : fond brun-noir `#0e0500`, texte secondaire brun-beige `#b8907a` — PAS orange
4. Sélectionner "Pivoine" en dark : fond quasi-noir `#0e040c`, accent magenta vif `#f03888`, texte secondaire mauve désaturé `#b888a4`
5. Chaque palette en mode clair : bg distinctement teinté + cards blanc pur `#ffffff`

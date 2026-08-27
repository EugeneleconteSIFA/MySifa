---
paths:
  - "app/web/**/*.py"
  - "static/**/*.css"
  - "app/frontend/**/*"
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

**Règles absolues sur les boutons — à respecter partout, sans exception**

1. **Pas de fond transparent au repos.** Un bouton avec `background: transparent`
   sur un fond de page `var(--bg)` est visuellement absent tant que le curseur
   n'est pas dessus — l'utilisateur ne voit pas l'affordance. Toujours donner
   un fond explicite :
   - Bouton posé **sur la page** (fond `var(--bg)`) → `background: var(--card)`
     (blanc en mode clair, sombre en mode dark) pour contraster avec le fond.
   - Bouton posé **à l'intérieur d'une card / modal** (fond `var(--card)`) →
     `background: var(--bg)` (gris clair / plus sombre) pour contraster avec
     la card.
   - Bouton **actif / sélectionné** → `background: var(--accent-bg)` +
     `border: 1px solid var(--accent)` + `color: var(--accent)`.
   - Bouton **danger / destructif** → fond `var(--danger)` + texte blanc.

   La variante `.btn-ghost` de la CSS globale reste tolérée uniquement pour
   des cas très localisés (ex. bouton "×" de fermeture posé sur un fond déjà
   coloré) — jamais comme choix par défaut pour un CTA visible dans la page.

2. **Cohérence hover.** Si le repos est `var(--card)`, le hover doit être
   `var(--bg)` (effet "s'assombrit" en mode clair, "s'éclaircit" en mode
   dark). Et **toujours définir le `mouseleave` symétrique** qui rétablit le
   fond de repos — sinon le bouton "reste" en état hover après un clic.
   Anti-pattern classique : `mouseleave` qui remet `transparent` alors que le
   repos est `var(--card)` → flash inversé au sortir du bouton.

3. **Boutons à fond coloré (accent, success, danger, warn) — la couleur du
   texte et de l'icône dépend du thème.** Un bouton `background: var(--accent)`
   (cyan) affiche du texte lisible en mode dark avec `color: #0a0e17` (le fond
   dark), mais en mode light il faut du texte foncé pour rester lisible sur
   le cyan. Pattern à adopter :
   ```css
   /* Sur fond --accent : texte foncé qui reste lisible dans les 2 thèmes */
   .btn-accent { background: var(--accent); color: var(--bg); }
   ```
   Le principe : `color: var(--bg)` produit **automatiquement** un texte
   contrasté (foncé sur clair, clair sur foncé) parce que `--bg` bascule
   avec le thème. Idem pour un bouton `background: var(--danger)` (rouge)
   qui reste toujours foncé → `color: #ffffff` est acceptable. Le point clé :
   **jamais** `color: var(--text)` ou `color: var(--text2)` sur un bouton à
   fond coloré — ces variables suivent le thème et vont produire du texte
   sombre sur fond sombre en mode dark, invisible.

   Bug historique : une IA a mis `color: var(--text2)` sur un badge cyan
   `background: var(--accent-bg)` — invisible en mode dark (text2 = clair
   sur accent-bg qui est déjà clair). Toujours tester dans les deux thèmes
   à chaque ajout de composant à fond coloré.

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

---

## Ou vivent les couleurs (depuis le 27 aout 2026)

Le bloc `:root{...}` / `body.light{...}` etait redeclare dans **25 fichiers**
de `app/web/`. Il est maintenant defini une seule fois dans
`app/web/components/theme.py`.

```python
from app.web.components import bloc_tokens, T

html = "<style>%s .carte{background:%s;color:%s}</style>" % (
    bloc_tokens(), T.CARD, T.TEXT,
)
```

- `T.CARD`, `T.BG`, `T.TEXT`, `T.TEXT2`, `T.MUTED`, `T.BORDER`, `T.ACCENT`,
  `T.ACCENT_BG`, `T.SUCCESS`, `T.WARN`, `T.DANGER`, `T.SERIE`.
- Sur un fond colore : `T.SUR_ACCENT` (= `var(--bg)`), jamais `T.TEXT`.

**Une nouvelle couleur hexadecimale ecrite en dur dans `app/web/**.py` ou
`static/**.css` est refusee par le hook** `.claude/hooks/apres_edition.py`.
Exception legitime (SVG, PDF reportlab, favicon, definition du theme) :
ajouter le commentaire `hex-ok` sur la ligne.

L'existant (1 594 occurrences) n'est pas migre d'un coup : il se resorbe au fil
des passages sur chaque page. Le hook empeche seulement que ca reparte a la
hausse.

## Donnees utilisateur dans le HTML

`escHtml()` / `escAttr()` cote Python, `textContent` cote JS. `innerHTML` sur
une saisie libre (note de production, commentaire de tache, message) est une
XSS stockee. Le hook avertit a chaque nouvel usage de `innerHTML` — l'avertissement
ne bloque pas, mais il n'est pas decoratif : verifier que la donnee injectee
est echappee ou qu'elle ne vient pas d'un utilisateur.

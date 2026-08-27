# Prompt Windsurf — Fix double wrapper fab-of-panel

## Problème
`renderMain` (quand `fabTab === 'of'`) enveloppe dans `div.fab-of-panel`.
`renderOfPanel` et `renderFichesPanel` retournent eux aussi `div.fab-of-panel`.
Double imbrication → contenu invisible à cause du CSS overflow:hidden / min-height:0.

## Fix — `app/web/fabrication_page.py`

### Dans `renderOfPanel`

Cherche la dernière ligne de la fonction :
```javascript
  return h('div',{className:'fab-of-panel'},
    h('div',{className:'fab-of-toolbar'},
```
Remplace `className:'fab-of-panel'` par `className:'fab-of-inner'` :
```javascript
  return h('div',{className:'fab-of-inner'},
    h('div',{className:'fab-of-toolbar'},
```

### Dans `renderFichesPanel`

Même correction — remplace le wrapper externe :
```javascript
  return h('div',{className:'fab-of-panel'},
```
Par :
```javascript
  return h('div',{className:'fab-of-inner'},
```

### Dans le CSS (cherche `.fab-of-panel{`)

Ajouter juste après la règle `.fab-of-panel{...}` :
```css
.fab-of-inner{flex:1;display:flex;flex-direction:column;min-height:0;overflow:hidden}
```

---

## Action requise sur le VPS (en dehors de Windsurf)
Redémarrer le serveur FastAPI après tout déploiement pour que les changements Python soient pris en compte.

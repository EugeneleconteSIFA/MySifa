# Prompt Cursor — Fix + UI/UX onglet Produits finis

## Contexte

L'onglet "Produits finis" affiche "Aucun stock enregistré" et "Aucun mouvement" alors qu'il y a des données en base. Il faut corriger ça ET améliorer l'UI/UX.

---

## 1. Diagnostic — Corrections à faire impérativement

### A. Vérifier la forme de la réponse API vs ce que le JS consomme

Ouvrir `app/routers/stock.py`, chercher l'endpoint `GET /api/stock/produits-finis`.

**Check 1 — Le retour JSON doit correspondre exactement aux clés lues en JS :**
- Si l'API retourne `{"stock": [...], "mouvements": [...]}`, le JS doit faire `data.stock` et `data.mouvements`
- Si l'API retourne `{"items": [...]}`, le JS doit faire `data.items`
- Chercher dans `stock_page.py` le fetch de cet endpoint et vérifier que les clés correspondent

**Fix typique :** si le JS fait `S.stock = data.stock ?? []` mais l'API retourne directement un array `[...]`, alors `data.stock` est `undefined` → list vide. Corriger soit le retour API soit la lecture JS pour qu'ils correspondent.

### B. Vérifier la requête SQL de calcul du stock

Dans `stock.py`, l'endpoint GET doit calculer le stock par agrégation sur `pf_mouvements`. La requête correcte est :

```sql
SELECT
    reference,
    designation,
    unite,
    emplacement,
    SUM(CASE WHEN type = 'entree' THEN quantite ELSE -quantite END) as stock_actuel,
    MAX(date_mouvement) as derniere_entree
FROM pf_mouvements
GROUP BY reference, emplacement
HAVING stock_actuel > 0
ORDER BY reference
```

**Erreurs fréquentes à corriger :**
- `HAVING SUM(quantite) > 0` sans distinguer entrée/sortie → toujours positif même après sorties
- `WHERE type = 'entree'` → exclut les sorties, donc le stock ne soustrait jamais rien
- `HAVING SUM(...) > 0` absent → retourne les refs avec stock = 0
- Si la requête retourne une liste vide, tester directement en Python : `conn.execute("SELECT COUNT(*) FROM pf_mouvements").fetchone()` et logger le résultat

### C. Vérifier que les tables existent réellement

Dans `app/core/database.py`, s'assurer que la migration a bien créé les tables `produits_finis` ET `pf_mouvements`. Ajouter un log au démarrage :

```python
# Dans _migrate() ou après, vérifier que les tables sont là
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("[DB] Tables:", [t[0] for t in tables])
```

Relancer l'app et vérifier dans les logs que `pf_mouvements` apparaît bien.

### D. Vérifier l'URL de l'endpoint

Dans `stock_page.py`, chercher le fetch de chargement des produits finis. L'URL doit correspondre exactement à ce qui est déclaré dans `stock.py`.

- Si le router est préfixé `/api/stock` et l'endpoint est `/produits-finis`, l'URL complète est `/api/stock/produits-finis`
- Vérifier dans `main.py` comment le router stock est inclus (`prefix=...`)

---

## 2. Améliorations UI/UX à apporter

Une fois les bugs corrigés, améliorer l'interface :

### A. État vide — affichage contextuel

Remplacer les messages génériques par des états vides utiles :

```html
<!-- Quand stock vide ET aucun mouvement jamais enregistré -->
<div style="text-align:center;padding:48px 24px;color:var(--muted)">
  <div style="font-size:32px;margin-bottom:12px">·</div>
  <div style="font-size:14px;font-weight:600;color:var(--text2);margin-bottom:6px">Aucun produit en stock</div>
  <div style="font-size:13px">Utilisez le bouton "Entrée" pour enregistrer votre premier mouvement.</div>
</div>

<!-- Quand stock vide à cause d'un filtre actif -->
<div style="text-align:center;padding:32px;color:var(--muted);font-size:13px">
  Aucun résultat pour « [terme] »
</div>
```

### B. Layout tableau de bord — amélioration visuelle

Revoir la disposition :

```
┌─────────────────────────────────────────────────────────────┐
│  [KPI: Références] [KPI: Mouvements aujourd'hui] [KPI: Empl]│  ← 3 cards KPI en haut
├──────────────────────────────────┬──────────────────────────┤
│ Barre: [🔍 Produit] [🔍 Empl]  [+ Entrée] [- Sortie]       │  ← contrôles
├──────────────────────────────────┬──────────────────────────┤
│  STOCK ACTUEL                    │  DERNIERS MOUVEMENTS     │
│  (liste filtrée, scrollable)     │  (20 derniers, scrollable)│
└──────────────────────────────────┴──────────────────────────┘
```

Corrections spécifiques :

**Cards KPI** : ajouter une couleur d'accent sur la valeur principale
```html
<div class="card" style="padding:16px 20px;flex:1">
  <div style="font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);margin-bottom:6px">Références en stock</div>
  <div style="font-size:24px;font-weight:700;color:var(--accent)" id="kpi-refs">—</div>
</div>
```

**Liste stock** : chaque ligne doit être une card légère avec hover, pas juste du texte
```css
.pf-stock-item {
  display:flex; align-items:center; gap:12px;
  padding:12px 16px; border-radius:10px;
  border:1px solid var(--border); background:var(--card);
  margin-bottom:6px; cursor:pointer; transition:border-color .15s
}
.pf-stock-item:hover { border-color:var(--accent) }
```

**Badge emplacement** : toujours affiché avec fond `--accent-bg` et couleur `--accent`
```html
<span style="background:var(--accent-bg);color:var(--accent);border-radius:6px;padding:2px 8px;font-size:11px;font-weight:600">
  {emplacement}
</span>
```

**Colonne mouvements** : icône directionnelle bien visible
```html
<!-- Entrée -->
<span style="color:var(--success);font-weight:700;font-size:16px">↑</span>
<!-- Sortie -->
<span style="color:var(--danger);font-weight:700;font-size:16px">↓</span>
```

### C. Modals — améliorations

**Modal entrée/sortie** :
- Le champ "Référence" doit avoir un `datalist` ou une liste déroulante autocomplete basée sur les refs connues (charger une fois au montage via `/api/stock/produits-finis`)
- Le champ "Emplacement" : idem avec liste des emplacements existants
- Après submit réussi → fermer la modal + rafraîchir stock + mouvements + KPIs + toast "Entrée enregistrée."
- Désactiver le bouton "Enregistrer" pendant le POST (attribut `disabled`) pour éviter les doubles clics

**Autofocus** : à l'ouverture de la modal :
```javascript
requestAnimationFrame(() => { document.getElementById("pf-entree-ref")?.focus(); });
```

### D. Chargement initial

Ajouter un indicateur de chargement pendant le fetch initial :
```javascript
// Avant le fetch
document.getElementById("pf-stock-list").innerHTML = 
  '<div style="padding:32px;text-align:center;color:var(--muted);font-size:13px">Chargement…</div>';
```

---

## 3. Ordre d'exécution

1. **D'abord** : corriger le bug de données (section 1) — sans ça rien d'autre ne sert
2. **Ensuite** : appliquer les améliorations UI (section 2)
3. **Tester** : entrée d'un produit → vérifier que le stock apparaît → sortir une partie → vérifier que le stock diminue → vérifier les mouvements

Ne pas modifier `DB_PATH` ni le schéma de tables existantes dans la migration, seulement ajouter des colonnes si nécessaire via une migration numérotée.

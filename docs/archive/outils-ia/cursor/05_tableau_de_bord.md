# Cursor Prompt 05 — Frontend : Tableau de bord rénové

## Prérequis

Les prompts 01 à 04 ont été exécutés. L'API dashboard retourne `alertes_mp` et `derniers_mouvements_mp`. La sidebar est restructurée.

## Contexte

Fichier à modifier : `app/web/stock_page.py`

Localiser la fonction `buildDashboard()` (ou son équivalent). Elle construit le contenu HTML de l'onglet "Tableau de bord". L'objectif est de la réécrire pour y ajouter 3 zones, tout en conservant les stats existantes sur les produits finis.

L'API `GET /api/stock/dashboard` retourne maintenant aussi `alertes_mp` et `derniers_mouvements_mp`. L'API `GET /api/stock/historique-mouvements?limit=10` retourne l'activité récente unifiée.

---

## Structure du tableau de bord

### Zone 1 — Raccourcis d'action rapide (tout en haut)

Une rangée de 4 boutons. Visible uniquement si `!S.stockReadOnly`.

```
[+ Réception matière]  [+ Entrée MP]  [+ Sortie MP]  [+ Ajustement MP]
```

Comportement de chaque bouton :
- **Réception matière** → appeler la fonction existante qui ouvre la modal de réception produit fini (comportement identique au bouton FAB existant sur l'onglet Réception)
- **Entrée MP** → appeler `openModalMouvement('entree')` (nouvelle fonction, voir prompt 06)
- **Sortie MP** → appeler `openModalMouvement('sortie')`
- **Ajustement MP** → appeler `openModalMouvement('ajustement')`

Style des boutons :
```css
/* Rangée */
display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 24px;

/* Chaque bouton */
background: var(--card);
border: 1px solid var(--border);
border-radius: 10px;
padding: 12px 16px;
font-size: 13px;
font-weight: 600;
color: var(--text);
cursor: pointer;
transition: border-color .15s, background .15s;

/* Hover */
border-color: var(--accent);
background: var(--accent-bg);
```

Sur mobile (< 640px) : les boutons passent en `flex-direction: column`, chacun prend toute la largeur.

---

### Zone 2 — Alertes stocks bas

Titre de section : "Stocks à réapprovisionner"

Deux blocs côte à côte sur desktop, empilés sur mobile :

**Bloc gauche — Matières premières en alerte** (données de `S.dashboard.alertes_mp`)

Si aucune alerte : afficher `"Toutes les matières sont au-dessus des seuils."` en couleur `var(--success)`, taille 13px.

Si alertes : une ligne par matière :
```
[badge catégorie]  RÉFÉRENCE — Désignation     3 pal. / min. 5 pal.
```

Badge catégorie (couleurs fixes) :
- `mandrin` → fond `rgba(124,58,237,0.15)`, texte `#7c3aed`
- `palette` → fond `rgba(8,145,178,0.15)`, texte `#0891b2`
- `adhesif` → fond `rgba(217,119,6,0.15)`, texte `#d97706`
- `carton` → fond `rgba(5,150,105,0.15)`, texte `#059669`

Chaque ligne est cliquable → naviguer vers l'onglet `matieres` (`S.tab = 'matieres'`).

**Bloc droit — Produits finis en alerte** (données existantes du dashboard)

Conserver le comportement actuel. Si aucun produit en alerte, afficher le même message positif.

---

### Zone 3 — Activité récente (en bas)

Titre de section : "Activité récente"

Liste des 10 derniers mouvements toutes catégories (données de `GET /api/stock/historique-mouvements?limit=10`). Charger cet endpoint séparément au montage du dashboard, stocker dans `S.dashboard.activiteRecente`.

**Format de chaque ligne :**

```
[badge type stock]  [badge type mouvement]  Référence · Désignation    Qté  ·  Opérateur  ·  il y a Xh
```

**Badges type stock :**
- `mp` → `"MP"`, fond `rgba(124,58,237,0.12)`, texte `#7c3aed`
- `produit` → `"PF"`, fond `rgba(34,211,238,0.12)`, texte `var(--accent)`

**Badges type mouvement (couleur de fond) :**
- `entree` / `inventaire` → `var(--success)` avec opacité 0.15, texte `var(--success)`
- `sortie` → `var(--danger)` avec opacité 0.15, texte `var(--danger)`
- `ajustement` → `var(--warn)` avec opacité 0.15, texte `var(--warn)`
- `transfert` → `var(--accent)` avec opacité 0.15, texte `var(--accent)`

**Temps relatif :** implémenter une petite fonction JS `timeAgo(isoString)` qui retourne :
- "il y a Xm" si < 1h
- "il y a Xh" si < 24h
- "hier" si hier
- la date formatée `DD/MM` sinon

Si la liste est vide : "Aucun mouvement enregistré."

---

## Chargement des données

Au montage de l'onglet dashboard (quand `S.tab === 'dashboard'`), effectuer deux appels en parallèle :

```javascript
async function loadDashboard() {
  const [dash, activite] = await Promise.all([
    api('/api/stock/dashboard'),
    api('/api/stock/historique-mouvements?limit=10')
  ]);
  S.dashboard = { ...dash, activiteRecente: activite };
  buildDashboard();
}
```

---

## Design global

- Les sections sont séparées par un `border-top: 1px solid var(--border)` avec `padding-top: 24px`
- Titres de section : `font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text); margin-bottom: 14px`
- Toutes les couleurs via variables CSS — ne jamais coder de couleur en dur
- Tester le thème light : les badges avec opacité fonctionnent dans les deux thèmes

---

## Vérification

- [ ] Les 4 raccourcis apparaissent et sont cliquables (même si la modal n'est pas encore implémentée, pas d'erreur JS)
- [ ] Les alertes MP s'affichent si des matières ont `quantite <= seuil_alerte`
- [ ] L'activité récente affiche les mouvements des deux types (MP et produits finis)
- [ ] Sur mobile (375px), les raccourcis sont en colonne, les deux blocs d'alertes sont empilés
- [ ] Thème light : aucune couleur illisible

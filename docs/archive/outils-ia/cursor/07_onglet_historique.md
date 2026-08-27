# Cursor Prompt 07 — Frontend : Onglet Historique des mouvements

## Prérequis

Les prompts 01 à 06 ont été exécutés. L'API `/api/stock/historique-mouvements` existe, la sidebar a l'onglet `historique`.

## Contexte

Fichier à modifier : `app/web/stock_page.py`

Ajouter la fonction `buildHistorique()` appelée quand `S.tab === 'historique'`.

---

## État JS à ajouter dans `S`

```javascript
S.historique = [];           // données chargées depuis l'API
S.historiqueFiltres = {
  type_stock: 'tout',        // 'tout' | 'mp' | 'produits'
  categorie: '',             // '' | 'mandrin' | 'palette' | 'adhesif' | 'carton'
  type_mouvement: '',        // '' | 'entree' | 'sortie' | 'ajustement' | 'inventaire' | 'transfert'
  date_debut: '',            // 'YYYY-MM-DD'
  date_fin: '',              // 'YYYY-MM-DD'
};
S.historiqueLoading = false;
```

---

## Chargement des données

```javascript
async function loadHistorique() {
  S.historiqueLoading = true;
  buildHistorique(); // pour afficher l'état de chargement
  const f = S.historiqueFiltres;
  const params = new URLSearchParams({ limit: 200 });
  if (f.type_stock !== 'tout') params.set('type_stock', f.type_stock);
  if (f.categorie) params.set('categorie', f.categorie);
  if (f.type_mouvement) params.set('type_mouvement', f.type_mouvement);
  if (f.date_debut) params.set('date_debut', f.date_debut);
  if (f.date_fin) params.set('date_fin', f.date_fin);
  S.historique = await api('/api/stock/historique-mouvements?' + params.toString());
  S.historiqueLoading = false;
  buildHistorique();
}
```

Appeler `loadHistorique()` au premier clic sur l'onglet et à chaque clic "Appliquer" dans les filtres.

---

## Structure de la page

### En-tête

- Titre : "Historique des mouvements"
- À droite : bouton "Export CSV" → déclenche le téléchargement (voir ci-dessous)

### Barre de filtres

**Sur desktop** : rangée horizontale sticky juste en dessous de la searchbar globale.

**Sur mobile** : un bouton "Filtres ▾" qui expand/collapse le panneau de filtres (toggle `S.historiqueFiltresOpen`).

Champs de filtres :

| Label | Champ | Type |
|---|---|---|
| Type de stock | `type_stock` | `<select>` : Tout / Matières premières / Produits finis |
| Catégorie | `categorie` | `<select>` : Tout / Mandrins / Palettes / Adhésifs / Cartons — désactivé si `type_stock === 'produits'` |
| Mouvement | `type_mouvement` | `<select>` : Tout / Entrée / Sortie / Ajustement / Inventaire / Transfert |
| Du | `date_debut` | `<input type="date">` |
| Au | `date_fin` | `<input type="date">` |

Bouton "Appliquer" → appelle `loadHistorique()`.
Bouton "Réinitialiser" → remet tous les filtres à leur valeur par défaut et rappelle `loadHistorique()`.

Style des selects et inputs de filtre : cohérent avec les autres inputs de MyStock (border-radius 10px, padding 10px 14px, border var(--border), focus border-color var(--accent)).

---

## Affichage des données

### État de chargement

Pendant `S.historiqueLoading` : afficher un spinner centré (reprendre le spinner existant dans le fichier).

### État vide

Si `S.historique.length === 0` après chargement : afficher "Aucun mouvement trouvé pour ces critères." en `var(--muted)`, centré.

### Format desktop (table)

Table HTML avec `table-layout: fixed`, `width: 100%`, `border-collapse: collapse`.

Colonnes et largeurs suggérées :

| Colonne | Contenu | Largeur |
|---|---|---|
| Date | `DD/MM/YYYY HH:MM` | 120px |
| Type | Badge "MP" ou "PF" | 60px |
| Mouvement | Badge type mouvement | 100px |
| Référence | `reference` monospace | 120px |
| Désignation | tronquée à 30 chars | auto |
| Quantité | nombre + "pal." (MP) ou unité (PF) | 80px |
| Avant → Après | `X → Y` en `var(--muted)` | 100px |
| Ref BL / Note | texte grisé, tronqué | 140px |
| Opérateur | `created_by_name` | 110px |

En-tête de table : `font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--muted); border-bottom: 2px solid var(--border)`.

Lignes : `border-bottom: 1px solid var(--border); padding: 10px 8px; font-size: 13px`. Hover : `background: var(--accent-bg)`.

### Format mobile (cards)

En dessous de 768px, remplacer la table par des cards empilées.

**Structure d'une card :**
```
┌─────────────────────────────────────────────────────┐
│ [badge MP/PF] [badge mouvement]        22/05 10:30  │
│ RÉFÉRENCE · Désignation (tronquée)                  │
│ ──────────────────────────────────────────────────  │
│ +10 pal.   2 → 12 pal.           Jean Dupont        │
│ BL-2024-001 · Commentaire ici (si présent)          │
└─────────────────────────────────────────────────────┘
```

---

## Badges

**Badges type stock :**
```css
/* MP */
background: rgba(124,58,237,0.12);
color: #7c3aed;
font-size: 10px; font-weight: 700; border-radius: 4px; padding: 2px 6px;

/* PF */
background: rgba(34,211,238,0.12);
color: var(--accent);
font-size: 10px; font-weight: 700; border-radius: 4px; padding: 2px 6px;
```

**Badges type mouvement :**
```css
/* entree, inventaire */
background: rgba(52,211,153,0.15); color: var(--success);

/* sortie */
background: rgba(248,113,113,0.15); color: var(--danger);

/* ajustement */
background: rgba(251,191,36,0.15); color: var(--warn);

/* transfert */
background: rgba(34,211,238,0.15); color: var(--accent);

/* commun */
font-size: 11px; font-weight: 600; border-radius: 4px; padding: 2px 8px;
```

---

## Export CSV

Bouton "Export CSV" dans l'en-tête. Au clic :

```javascript
function exportHistoriqueCSV() {
  const f = S.historiqueFiltres;
  const params = new URLSearchParams({ limit: 500, format: 'csv' });
  if (f.type_stock !== 'tout') params.set('type_stock', f.type_stock);
  if (f.categorie) params.set('categorie', f.categorie);
  if (f.type_mouvement) params.set('type_mouvement', f.type_mouvement);
  if (f.date_debut) params.set('date_debut', f.date_debut);
  if (f.date_fin) params.set('date_fin', f.date_fin);
  window.location.href = '/api/stock/historique-mouvements?' + params.toString();
}
```

Le backend retourne un fichier CSV téléchargeable (`Content-Disposition: attachment`), le navigateur le télécharge directement.

---

## Vérification

- [ ] La page charge les données au premier affichage de l'onglet
- [ ] Chaque filtre fonctionne (tester type stock, catégorie, type mouvement, dates)
- [ ] "Réinitialiser" remet tout à zéro et recharge
- [ ] Les badges MP/PF et les badges de type mouvement ont les bonnes couleurs
- [ ] Sur desktop : la table affiche toutes les colonnes avec les bons alignements
- [ ] Sur mobile (375px) : les cards sont lisibles, les filtres collapsibles fonctionnent
- [ ] L'export CSV déclenche bien un téléchargement (tester avec quelques mouvements)
- [ ] Thème light : tous les badges restent lisibles (opacités testées sur fond clair)
- [ ] Si aucun résultat : message vide affiché proprement

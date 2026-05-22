# Cursor Prompt 03 — API : Historique unifié + mise à jour Dashboard

## Prérequis

Les prompts 01 et 02 ont été exécutés. Les tables et routes MP existent.

## Contexte

Fichier à modifier : `app/routers/stock.py`

Deux modifications :
1. Ajouter le nouvel endpoint `GET /api/stock/historique-mouvements`
2. Étendre l'endpoint existant `GET /api/stock/dashboard` (ajouter des clés, ne rien casser)

---

## 1. GET /api/stock/historique-mouvements

Historique unifié matières premières + produits finis, filtrable. Accès `require_stock`.

### Paramètres query string

| Param | Valeurs | Défaut |
|---|---|---|
| `type_stock` | `tout`, `mp`, `produits` | `tout` |
| `categorie` | `mandrin`, `palette`, `adhesif`, `carton` | (aucun) |
| `reference` | texte libre, filtre LIKE insensible à la casse | (aucun) |
| `type_mouvement` | `entree`, `sortie`, `ajustement`, `inventaire`, `transfert` | (aucun) |
| `date_debut` | `YYYY-MM-DD` | (aucun) |
| `date_fin` | `YYYY-MM-DD` | (aucun) |
| `limit` | entier | `200` (max `500`) |
| `format` | `json`, `csv` | `json` |

### Logique

Faire deux requêtes SQLite séparées, normaliser, fusionner, trier.

**Requête MP (`mp_mouvements JOIN matieres_premieres`) :**
```sql
SELECT
    'mp-' || m.id AS id,
    'mp' AS type_stock,
    mp.categorie,
    mp.reference,
    mp.designation,
    m.type_mouvement,
    m.quantite,
    m.quantite_avant,
    m.quantite_apres,
    m.ref_bl,
    m.note,
    m.created_at,
    m.created_by_name
FROM mp_mouvements m
JOIN matieres_premieres mp ON mp.id = m.matiere_id
WHERE 1=1
-- filtres appliqués dynamiquement selon les paramètres
```

**Requête produits finis (`mouvements_stock JOIN produits`) :**
```sql
SELECT
    'pf-' || m.id AS id,
    'produit' AS type_stock,
    NULL AS categorie,
    p.reference,
    p.designation,
    m.type_mouvement,
    m.quantite,
    m.quantite_avant,
    m.quantite_apres,
    NULL AS ref_bl,
    m.note,
    m.created_at,
    m.created_by_name
FROM mouvements_stock m
JOIN produits p ON p.id = m.produit_id
WHERE 1=1
-- filtres appliqués dynamiquement
```

Construire les clauses WHERE dynamiquement en Python selon les paramètres reçus. Appliquer les filtres pertinents à chaque requête (ex. `categorie` ne s'applique qu'aux MP).

Fusionner les deux listes en Python, trier par `created_at DESC`, appliquer `limit`.

### Réponse JSON

```json
[
  {
    "id": "mp-42",
    "type_stock": "mp",
    "categorie": "mandrin",
    "reference": "76MM-3P",
    "designation": "Mandrin 76mm 3 pouces",
    "type_mouvement": "entree",
    "quantite": 10.0,
    "quantite_avant": 2.0,
    "quantite_apres": 12.0,
    "ref_bl": "BL-2024-001",
    "note": null,
    "created_at": "2024-05-22T10:30:00",
    "created_by_name": "Jean Dupont"
  }
]
```

### Format CSV (si `format=csv`)

Retourner une `Response` avec :
- `Content-Type: text/csv; charset=utf-8`
- `Content-Disposition: attachment; filename="historique_stock_YYYYMMDD.csv"`

Colonnes CSV dans cet ordre :
`Date,Type stock,Catégorie,Référence,Désignation,Mouvement,Quantité,Avant,Après,Ref BL,Note,Opérateur`

---

## 2. Étendre GET /api/stock/dashboard

Localiser l'endpoint `GET /api/stock/dashboard` dans `stock.py`. **Ne pas modifier la structure de réponse existante.** Ajouter deux nouvelles clés à la fin du dict retourné.

**Nouvelle clé `alertes_mp` :**
```python
alertes_mp = conn.execute("""
    SELECT mp.id, mp.categorie, mp.reference, mp.designation, mp.seuil_alerte,
           COALESCE(s.quantite, 0) as quantite
    FROM matieres_premieres mp
    LEFT JOIN mp_stock s ON s.matiere_id = mp.id
    WHERE mp.actif = 1 AND mp.seuil_alerte > 0 AND COALESCE(s.quantite, 0) <= mp.seuil_alerte
    ORDER BY mp.categorie, mp.reference
""").fetchall()
```

**Nouvelle clé `derniers_mouvements_mp` :**
```python
derniers_mouvements_mp = conn.execute("""
    SELECT m.type_mouvement, m.quantite, m.quantite_apres, m.created_at, m.created_by_name,
           mp.reference, mp.designation, mp.categorie
    FROM mp_mouvements m
    JOIN matieres_premieres mp ON mp.id = m.matiere_id
    ORDER BY m.created_at DESC
    LIMIT 5
""").fetchall()
```

Ajouter ces deux clés à la réponse existante sans toucher au reste.

---

## Vérification

```bash
# Historique JSON
curl "http://localhost:8000/api/stock/historique-mouvements?limit=10"

# Historique filtré MP uniquement
curl "http://localhost:8000/api/stock/historique-mouvements?type_stock=mp&categorie=mandrin"

# Dashboard avec nouvelles clés
curl http://localhost:8000/api/stock/dashboard
# → vérifier que alertes_mp et derniers_mouvements_mp sont présents
# → vérifier que les clés existantes sont toujours là et non modifiées
```

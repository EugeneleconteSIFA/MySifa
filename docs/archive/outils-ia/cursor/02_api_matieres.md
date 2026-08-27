# Cursor Prompt 02 — API : Référentiel et mouvements matières premières

## Prérequis

Le prompt 01 a été exécuté : les tables `matieres_premieres`, `mp_stock` et `mp_mouvements` existent dans la DB.

## Contexte

Fichier à modifier : `app/routers/stock.py`

Helpers d'auth existants à réutiliser :
- `require_stock(request)` → lecture (direction, administration, logistique, commercial)
- `require_stock_write(request)` → écriture (bloque commercial)
- Pour les routes admin (CRUD référentiel) : vérifier que `session["role"] in ["superadmin","direction","administration"]`

La session utilisateur est accessible via `request.session`. L'utilisateur connecté a les champs `id`, `nom`, `role`.

---

## Routes à ajouter

### GET /api/stock/matieres

Retourne toutes les matières avec leur stock courant. Jointure `matieres_premieres LEFT JOIN mp_stock`.

Réponse :
```json
[
  {
    "id": 1,
    "categorie": "mandrin",
    "reference": "76MM-3P",
    "designation": "Mandrin 76mm 3 pouces",
    "seuil_alerte": 5.0,
    "actif": 1,
    "quantite": 12.0,
    "en_alerte": false
  }
]
```

`en_alerte` est `true` si `quantite <= seuil_alerte AND seuil_alerte > 0`.
Retourner uniquement les matières `actif = 1`.
Trier par `categorie ASC, reference ASC`.

---

### POST /api/stock/matieres

Créer une nouvelle référence. Admin uniquement.

Body :
```json
{
  "categorie": "mandrin",
  "reference": "76MM-3P",
  "designation": "Mandrin 76mm 3 pouces",
  "seuil_alerte": 5.0
}
```

Logique :
1. Insérer dans `matieres_premieres`
2. Insérer une ligne dans `mp_stock` avec `quantite=0` pour cette nouvelle matière
3. En cas de contrainte UNIQUE violée, retourner `400` avec `{"detail": "Cette référence existe déjà dans cette catégorie."}`

---

### PUT /api/stock/matieres/{matiere_id}

Modifier désignation, seuil_alerte, ou actif. Admin uniquement.

Body (tous les champs optionnels) :
```json
{
  "designation": "Mandrin 76mm 3 pouces kraft",
  "seuil_alerte": 8.0,
  "actif": 1
}
```

Mettre à jour `updated_at` avec `strftime('%Y-%m-%dT%H:%M:%S','now','localtime')`.

---

### DELETE /api/stock/matieres/{matiere_id}

Soft delete (passer `actif=0`). Admin uniquement.

Avant de désactiver, vérifier s'il existe des mouvements dans `mp_mouvements` pour cette matière. Si oui et que `quantite` dans `mp_stock` > 0, retourner `400` : `{"detail": "Impossible de désactiver une matière avec du stock en cours."}`. Si des mouvements existent mais stock = 0, autoriser le soft delete.

---

### POST /api/stock/matieres/mouvement

Enregistrer un mouvement. Accès `require_stock_write`.

Body :
```json
{
  "matiere_id": 1,
  "type_mouvement": "entree",
  "quantite": 10.0,
  "ref_bl": "BL-2024-001",
  "note": "Réception fournisseur X",
  "emplacement_source": null,
  "emplacement_dest": null
}
```

Logique côté serveur :
1. Récupérer `quantite_avant` depuis `mp_stock` (0 si la ligne n'existe pas encore)
2. Calculer `quantite_apres` :
   - `entree` → `quantite_avant + quantite`
   - `sortie` → `quantite_avant - quantite`. Si résultat < 0 : retourner `400` `{"detail": "Stock insuffisant — stock actuel : X pal."}`
   - `ajustement` → `quantite` est la nouvelle valeur absolue. `quantite_apres = quantite`. Stocker la différence absolue dans le champ `quantite` du mouvement.
   - `transfert` → stock global inchangé. `quantite_apres = quantite_avant`. Enregistrer `emplacement_source` et `emplacement_dest`.
3. Upsert dans `mp_stock` : `INSERT OR REPLACE INTO mp_stock(matiere_id, quantite, updated_at, updated_by_name) VALUES(...)`
4. Insérer dans `mp_mouvements` avec `created_by` et `created_by_name` depuis la session

Retourner `{"ok": true, "quantite_apres": X}`.

---

### GET /api/stock/matieres/{matiere_id}/mouvements

Historique des 50 derniers mouvements d'une matière. Accès `require_stock`.

Réponse : liste ordonnée par `created_at DESC`, avec tous les champs de `mp_mouvements` + `reference` et `designation` de `matieres_premieres`.

---

## Vérification

Tester manuellement avec curl ou le client HTTP de Cursor :

```bash
# Créer une référence
curl -X POST http://localhost:8000/api/stock/matieres \
  -H "Content-Type: application/json" \
  -d '{"categorie":"mandrin","reference":"TEST-01","designation":"Test mandrin","seuil_alerte":5}'

# Enregistrer une entrée
curl -X POST http://localhost:8000/api/stock/matieres/mouvement \
  -H "Content-Type: application/json" \
  -d '{"matiere_id":1,"type_mouvement":"entree","quantite":10}'

# Vérifier le stock
curl http://localhost:8000/api/stock/matieres
```

Vérifier que le stock s'incrémente correctement et qu'une tentative de sortie avec quantité > stock retourne bien 400.

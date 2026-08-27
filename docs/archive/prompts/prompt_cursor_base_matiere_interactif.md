# Prompt Cursor — Base matière interactive avec sélection de composants

## Contexte

Dans MyDevis (`app/web/html.py`), la page « Base matière » affiche des lignes provenant de la table `matiere_base`. Chaque ligne comporte quatre champs texte libre : `frontal`, `adhesif`, `silicone`, `glassine`. Ces champs sont actuellement saisis manuellement dans `openMatiereBaseModal`.

Le backend (`app/routers/matiere_prix.py`) fait déjà le calcul de prix via `prix_cohesio_from_params` : il prend ces quatre labels et les matche (fuzzy) contre les désignations de `matiere_params` pour sommer les `prix_eur_m2`. Il retourne déjà `prix_cohesio_calc`, `prix_rotoflex_calc`, `prix_cohesio_majore`, `prix_rotoflex_majore` dans chaque ligne de `GET /api/matiere/base`.

**Le problème :** la saisie libre génère des erreurs de correspondance. Il faut remplacer ces champs texte par des sélecteurs qui pointent vers les entrées de `matiere_params`, et afficher le prix calculé en temps réel dans le formulaire.

---

## Ce qui doit être fait

### 1. Migration DB (nouvelle version après v16)

Ajouter dans `app/core/database.py`, après la migration v16, une migration **v17** qui :

```sql
ALTER TABLE matiere_base ADD COLUMN param_id_frontal INTEGER REFERENCES matiere_params(id);
ALTER TABLE matiere_base ADD COLUMN param_id_adhesif  INTEGER REFERENCES matiere_params(id);
ALTER TABLE matiere_base ADD COLUMN param_id_silicone INTEGER REFERENCES matiere_params(id);
ALTER TABLE matiere_base ADD COLUMN param_id_glassine INTEGER REFERENCES matiere_params(id);
```

Suivre le pattern existant (guard `IF NOT EXISTS`, `_record_schema_migration(conn, 17, "matiere_base_param_ids")`).

---

### 2. Backend — `app/routers/matiere_prix.py`

**a) Modifier `create_base` et `update_base`** pour accepter les nouveaux champs `param_id_frontal`, `param_id_adhesif`, `param_id_silicone`, `param_id_glassine` dans le body et les persister.

**b) Modifier `prix_cohesio_from_params`** (ou `_row_base_with_marge`) : si les `param_id_*` sont présents et non nuls, faire un lookup direct par ID au lieu du fuzzy match texte :

```python
def prix_cohesio_from_ids(base: dict, params_by_id: dict[int, dict]) -> float:
    total = 0.0
    for field in ("param_id_frontal", "param_id_adhesif", "param_id_silicone", "param_id_glassine"):
        pid = base.get(field)
        if pid and pid in params_by_id:
            eur = _float_safe(params_by_id[pid].get("prix_eur_m2"))
            if eur:
                total += eur
    return total
```

Appeler cette fonction en priorité dans `_row_base_with_marge` quand au moins un `param_id_*` est non nul, sinon fallback sur le fuzzy texte existant.

**c) Ajouter un endpoint GET `/api/matiere/params/by-category`** (ou réutiliser `/api/matiere/params?categorie=…`) pour permettre au frontend de charger les composants filtrés par catégorie. Aucun changement nécessaire si le endpoint `GET /api/matiere/params` existant supporte déjà `?categorie=`.

---

### 3. Frontend — `app/web/html.py`

#### a) Pools de catégories (correspondance avec `_split_param_pools` backend)

Le backend catégorise les params ainsi :
- **Frontal** : tout ce qui n'est pas GLS, S, linerless, E, P (i.e. tous les autres)
- **Adhésif** : `categorie` normalisé en `e` ou `p`
- **Silicone** : `categorie` normalisé en `s` ou `linerless`
- **Glassine** : `categorie` normalisé en `gls` ou valeur brute `"GLS"`

#### b) Modifier `openMatiereBaseModal(row)` dans `html.py`

Remplacer les quatre appels `matiereAddLabeledInput` pour `frontal`, `adhesif`, `silicone`, `glassine` par **des sélecteurs avec recherche** :

```javascript
function buildComponentSelector(grid, labelText, fieldName, paramPool, currentParamId, currentText, onChangeCb) {
  // Crée un <select> ou une combobox avec :
  // - une option vide ("— aucun")
  // - les entrées de paramPool triées (designation + prix_eur_m2 affiché en hint)
  // - présélection sur currentParamId si fourni, sinon fuzzy match sur currentText
  // - onChange appelle onChangeCb(selectedId, selectedDesignation, selectedEurM2)
}
```

**Comportement attendu :**
- Le sélecteur affiche : `Désignation (0,1234 €/m²)` pour chaque ligne
- Il y a un champ de filtre texte libre au-dessus du select (type-to-search)
- La valeur stockée est le `param_id` (integer), mais on affiche et on sauvegarde aussi la désignation dans le champ texte correspondant (pour compatibilité avec le fuzzy match si l'ID vient à manquer)

**Bloc de prévisualisation des prix dans le modal :**

Ajouter en bas du formulaire (avant les boutons) un bloc de prévisualisation mis à jour en temps réel :

```
Composition sélectionnée
  Frontal    : Couché 115 g              0,1234 €/m²
  Adhésif    : Permanent 2288/55         0,0456 €/m²
  Silicone   : ——                        ——
  Glassine   : Glassine 58g chinois LK   0,0321 €/m²
  ─────────────────────────────────────────────────
  Prix de revient Cohésio                0,2011 €/m²
  + Supplément Rotoflex (0,06)           0,0600 €/m²
  Prix de revient Rotoflex               0,2611 €/m²
  ─────────────────────────────────────────────────
  Prix Cohésio (+5% marge)               0,2112 €/m²   ← en vert
  Prix Rotoflex (+5% marge)              0,2742 €/m²   ← en vert
```

Ce calcul se fait **entièrement côté JS** sans appel API, en réutilisant les données `S.matiereParams` déjà chargées en mémoire.

#### c) Charger les `matiereParams` au chargement de la page Base matière

S'assurer que `loadMatierePrixPage()` charge aussi `S.matiereParams` (ce qui est déjà le cas si le fetch `GET /api/matiere/params` est présent dans cette fonction). Sinon l'ajouter.

#### d) Pré-remplissage des sélecteurs à l'édition

Quand `row.param_id_frontal` est non nul → présélectionner cet ID dans le sélecteur frontal.
Sinon, si `row.frontal` est un texte → tenter un fuzzy match JS pour présélectionner le bon item (même logique que `_eur_best_match` mais côté JS).

#### e) Sauvegarde

Lors du save, inclure dans le body envoyé au PUT/POST :
- `frontal` (designation texte — pour rétrocompatibilité)
- `adhesif`, `silicone`, `glassine` (idem)
- `param_id_frontal`, `param_id_adhesif`, `param_id_silicone`, `param_id_glassine` (les IDs — null si non sélectionné)
- **Ne pas** inclure `prix_cohesio` et `prix_rotoflex` dans le body : le backend les recalcule depuis les params_ids. (Les champs `prix_cohesio` / `prix_rotoflex` dans `matiere_base` peuvent rester comme cache/override manuel si renseignés manuellement, mais en mode interactif ils ne sont pas envoyés.)

---

### 4. Affichage dans le tableau Base matière

Dans `renderMatierePrix`, pour les colonnes `Cohésio €/m²` et `Rotoflex €/m²` :
- Si `r.prix_cohesio_calc != null` → afficher `prix_cohesio_majore` en vert (avec barré `prix_cohesio_calc`) — **déjà le cas via `matierePriceCell`**
- Ajouter une icône ou badge discret `⚙` sur les lignes où le prix est calculé depuis les composants (i.e. `prix_cohesio_calc != null`) pour les distinguer des lignes avec prix saisis manuellement

---

## Contraintes à respecter

- **Pas d'emojis** dans les labels/messages. Utiliser `✓`, `×`, `—` uniquement.
- Toasts : `showToast(msg, 'success'|'danger'|'info')` uniquement.
- JS vanilla, pas de librairies externes. Le select natif HTML avec un input de filtre au-dessus suffit.
- Suivre le pattern `_marge_factor` existant : ne jamais hardcoder 5 %, toujours lire depuis `S.matiereConfig.marge_erreur`.
- Le supplément Rotoflex doit lire `row.rotoflex_supplement_eur_m2` s'il est renseigné sur la ligne, sinon `S.matiereConfig.supplement_rotoflex_eur_m2`.
- Migration DB : toujours avec guard `if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=17 LIMIT 1").fetchone()` et `try/except: pass` sur chaque ALTER.
- Ne pas bloquer la sauvegarde si aucun composant n'est sélectionné (les quatre champs peuvent être vides/null — prix restent manuels).

---

## Fichiers concernés

| Fichier | Modification |
|---|---|
| `app/core/database.py` | Migration v17 : 4 colonnes `param_id_*` sur `matiere_base` |
| `app/routers/matiere_prix.py` | Lookup par ID dans `_row_base_with_marge`, accept `param_id_*` dans create/update |
| `app/web/html.py` | `openMatiereBaseModal` : sélecteurs composants + prévisualisation prix live |

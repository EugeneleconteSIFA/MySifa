# Prompt Cursor — MyExpé Chantier 3 : Carte des délais industrialisée

## Contexte

**Ce chantier est parallelisable** — il ne dépend pas des Chantiers 1 et 2. Il dépend uniquement des migrations de base (Chantier 0 doit être appliqué, dernière migration v64 minimum).

Les migrations de Chantier 2 utilisent v65 et v66. Ce chantier utilise **v67**.

## Règles absolues

- MySifa, FastAPI + HTML/CSS/JS vanilla, DB SQLite `data/production.db`
- **Ne jamais modifier `DB_PATH` dans `.env`.**
- `DELAIS_FRANCE_DEFAULT` et `build_delais_france_default()` sont dans `app/web/expe_france_delais_data.py` — ne pas les modifier
- Tout le JS de la carte est dans `app/web/expe_assets.py` (lignes ~875-1200)
- L'objectif est de remplacer les lectures/écritures `localStorage` par des appels API, sans changer le comportement visible de la carte

---

## Fichiers concernés

| Fichier | Ce qui change |
|---|---|
| `app/core/database.py` | Migration v67 (`expe_delais`) + seed initial |
| `app/routers/expe_departs.py` | 3 nouveaux endpoints délais |
| `app/web/expe_assets.py` | Remplacement des fonctions `localStorage` par appels API |

---

## Étape 1 — Migration v67 et seed initial

Dans `app/core/database.py`, ajouter après la dernière migration existante :

```python
if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=67 LIMIT 1").fetchone():
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS expe_delais (
            departement      TEXT NOT NULL,
            type_envoi       TEXT NOT NULL DEFAULT 'default',
            transporteur_id  INTEGER,
            delai_jours      INTEGER,
            zone_label       TEXT NOT NULL DEFAULT 'france',
            delai_texte      TEXT NOT NULL DEFAULT 'J+2',
            updated_at       TEXT,
            updated_by_email TEXT,
            PRIMARY KEY (departement, type_envoi, COALESCE(transporteur_id, -1))
        );
    """)
    conn.commit()

    # Seed depuis les défauts existants
    from app.web.expe_france_delais_data import DELAIS_FRANCE_DEFAULT
    from datetime import datetime
    from zoneinfo import ZoneInfo
    _PARIS = ZoneInfo("Europe/Paris")
    now = datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")

    for dept, data in DELAIS_FRANCE_DEFAULT.items():
        delai_texte = data.get("delai", "J+2")
        zone_label = data.get("zone", "france")
        # Convertir "J+N" en entier
        try:
            delai_jours = int(delai_texte.replace("J+", "").strip())
        except (ValueError, AttributeError):
            delai_jours = 2
        conn.execute("""
            INSERT OR IGNORE INTO expe_delais
            (departement, type_envoi, transporteur_id, delai_jours, zone_label, delai_texte, updated_at)
            VALUES (?, 'default', NULL, ?, ?, ?, ?)
        """, (dept, delai_jours, zone_label, delai_texte, now))
    conn.commit()
    _record_schema_migration(conn, 67, "expe_delais")
```

**Structure de la table :**
- `departement` : `'01'`..`'95'`, `'2A'`, `'2B'`, `'971'`..`'976'`
- `type_envoi` : `'default'` (utilisé partout pour l'instant), `'messagerie'`, `'affretement'`
- `transporteur_id` : NULL = délai générique (c'est le cas de départ)
- `delai_texte` : ex. `'J+1'`, `'J+2'`, `'J+3'`, `'J+5'` — format affiché sur la carte
- `zone_label` : `'france'` | `'france_hors_paris'` | `'affretement'` | `'messagerie'`
- `PRIMARY KEY` sur `(departement, type_envoi, COALESCE(transporteur_id, -1))` : SQLite ne supporte pas directement `COALESCE` dans la PK. **Alternative propre** : utiliser `INSERT OR REPLACE` plutôt qu'une PK composite. Modifier la table pour utiliser un index unique à la place :

```python
# Version corrigée de la migration v67 — sans COALESCE dans PK :
conn.executescript("""
    CREATE TABLE IF NOT EXISTS expe_delais (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        departement      TEXT NOT NULL,
        type_envoi       TEXT NOT NULL DEFAULT 'default',
        transporteur_id  INTEGER,
        delai_jours      INTEGER,
        zone_label       TEXT NOT NULL DEFAULT 'france',
        delai_texte      TEXT NOT NULL DEFAULT 'J+2',
        updated_at       TEXT,
        updated_by_email TEXT
    );
    CREATE UNIQUE INDEX IF NOT EXISTS idx_expe_delais_unique
        ON expe_delais(departement, type_envoi, COALESCE(transporteur_id, -1));
""")
```

Le seed utilise `INSERT OR IGNORE` (l'index unique garantit l'idempotence).

---

## Étape 2 — Endpoints délais

Ajouter dans `app/routers/expe_departs.py` :

### 2.1 — `GET /expe/delais` — Charger tous les délais

Retourne un dict `{dept: {delai, zone, label}}` compatible avec `DELAIS_FRANCE_DEFAULT` pour que le JS puisse l'utiliser tel quel.

```python
@router.get("/delais")
def get_delais(request: Request, type_envoi: str = "default"):
    _require_expe(request)
    with get_db() as conn:
        # Charger les délais génériques (transporteur_id IS NULL) pour le type demandé
        # Fallback sur 'default' si le type n'a pas de données
        rows = conn.execute("""
            SELECT departement, delai_texte, zone_label
            FROM expe_delais
            WHERE type_envoi=? AND transporteur_id IS NULL
        """, (type_envoi,)).fetchall()

        if not rows and type_envoi != "default":
            rows = conn.execute("""
                SELECT departement, delai_texte, zone_label
                FROM expe_delais
                WHERE type_envoi='default' AND transporteur_id IS NULL
            """).fetchall()

    # Charger les labels depuis le module Python (évite de les dupliquer en DB)
    from app.web.expe_france_delais_data import DELAIS_FRANCE_DEFAULT
    result = {}
    for r in rows:
        dept = r["departement"]
        default_label = DELAIS_FRANCE_DEFAULT.get(dept, {}).get("label", dept)
        result[dept] = {
            "delai":  r["delai_texte"],
            "zone":   r["zone_label"],
            "label":  default_label,
        }
    return result
```

### 2.2 — `PUT /expe/delais` — Sauvegarder un ou plusieurs délais

Body JSON : `{ "overrides": { "59": {"delai": "J+1", "zone": "france"}, "75": {"delai": "J+2", "zone": "france_hors_paris"} } }`

```python
@router.put("/delais")
def save_delais(request: Request, body: dict = Body(...)):
    user = _require_expe_write(request)
    # Restriction : seuls superadmin, direction, administration, expedition peuvent modifier les délais
    role = user.get("role", "")
    if role not in {"superadmin", "direction", "administration", "expedition"}:
        raise HTTPException(403, "Accès refusé — rôle insuffisant pour modifier les délais")

    overrides = body.get("overrides") or {}
    if not overrides:
        raise HTTPException(400, "overrides est vide")

    now = datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")
    type_envoi = body.get("type_envoi", "default")

    with get_db() as conn:
        for dept, data in overrides.items():
            delai_texte = str(data.get("delai") or "J+2").strip()
            zone_label = str(data.get("zone") or "france").strip()
            try:
                delai_jours = int(delai_texte.replace("J+", "").strip())
            except (ValueError, AttributeError):
                delai_jours = 2

            # INSERT OR REPLACE grâce à l'index unique
            conn.execute("""
                INSERT INTO expe_delais
                    (departement, type_envoi, transporteur_id, delai_jours, zone_label, delai_texte, updated_at, updated_by_email)
                VALUES (?, ?, NULL, ?, ?, ?, ?, ?)
                ON CONFLICT(departement, type_envoi, COALESCE(transporteur_id, -1))
                DO UPDATE SET
                    delai_jours=excluded.delai_jours,
                    zone_label=excluded.zone_label,
                    delai_texte=excluded.delai_texte,
                    updated_at=excluded.updated_at,
                    updated_by_email=excluded.updated_by_email
            """, (dept, type_envoi, delai_jours, zone_label, delai_texte, now, user["email"]))
        conn.commit()

    return {"updated": len(overrides)}
```

**Note SQLite** : `ON CONFLICT ... DO UPDATE` (UPSERT) est disponible à partir de SQLite 3.24.0 (2018). La version sur le VPS Ubuntu est très probablement ≥ 3.24. Si ce n'est pas le cas, utiliser à la place :
```python
# Fallback SQLite < 3.24 :
conn.execute("DELETE FROM expe_delais WHERE departement=? AND type_envoi=? AND transporteur_id IS NULL", (dept, type_envoi))
conn.execute("INSERT INTO expe_delais (...) VALUES (...)", ...)
```

### 2.3 — `POST /expe/delais/reset` — Réinitialiser aux valeurs par défaut

```python
@router.post("/delais/reset")
def reset_delais(request: Request, body: dict = Body(default={})):
    user = _require_expe_write(request)
    role = user.get("role", "")
    if role not in {"superadmin", "direction", "administration", "expedition"}:
        raise HTTPException(403, "Accès refusé")

    type_envoi = body.get("type_envoi", "default")
    now = datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")

    from app.web.expe_france_delais_data import DELAIS_FRANCE_DEFAULT

    with get_db() as conn:
        # Supprimer les overrides existants pour ce type
        conn.execute(
            "DELETE FROM expe_delais WHERE type_envoi=? AND transporteur_id IS NULL",
            (type_envoi,)
        )
        # Réinsérer les défauts
        for dept, data in DELAIS_FRANCE_DEFAULT.items():
            delai_texte = data.get("delai", "J+2")
            zone_label = data.get("zone", "france")
            try:
                delai_jours = int(delai_texte.replace("J+", "").strip())
            except (ValueError, AttributeError):
                delai_jours = 2
            conn.execute("""
                INSERT INTO expe_delais
                (departement, type_envoi, transporteur_id, delai_jours, zone_label, delai_texte, updated_at, updated_by_email)
                VALUES (?, ?, NULL, ?, ?, ?, ?, ?)
            """, (dept, type_envoi, delai_jours, zone_label, delai_texte, now, user["email"]))
        conn.commit()

    return {"reset": True, "type_envoi": type_envoi}
```

---

## Étape 3 — Modifier `app/web/expe_assets.py`

### 3.1 — Ce qu'on supprime

Les 4 fonctions suivantes sont à **supprimer entièrement** de `expe_assets.py` :

```js
// SUPPRIMER ces 4 fonctions :
function expeLoadDelaisOverrides() { ... }    // ligne ~913
function expeSaveDelaisOverrides(ov) { ... }  // ligne ~919
function expeMergeDelais() { ... }            // ligne ~923
// Et dans expeResetDelais() : les appels à localStorage.removeItem
```

Et supprimer la constante :
```js
const EXPE_LS_DELAIS_KEY = 'mysifa_expe_delais_v2';  // SUPPRIMER
```

### 3.2 — Nouvelles fonctions de chargement

Remplacer `expeLoadDelaisOverrides` + `expeMergeDelais` par une seule fonction async :

```js
async function expeLoadDelaisFromAPI(typeEnvoi) {
  typeEnvoi = typeEnvoi || 'default';
  try {
    const data = await api('/expe/delais?type_envoi=' + encodeURIComponent(typeEnvoi));
    // data = { "59": {delai:"J+1", zone:"france", label:"Nord"}, ... }
    // Merger avec les défauts (pour les départements manquants en DB)
    DELAIS_FRANCE = Object.assign({}, DELAIS_FRANCE_DEFAULT, data);
  } catch(e) {
    console.warn('[expe] Impossible de charger les délais depuis l\'API, utilisation des défauts.', e);
    DELAIS_FRANCE = JSON.parse(JSON.stringify(DELAIS_FRANCE_DEFAULT));
  }
}
```

### 3.3 — Modifier `expeResetDelais()`

Remplacer l'implémentation complète :

```js
// AVANT :
function expeResetDelais(){
  if(!confirm('Réinitialiser tous les délais aux valeurs par défaut ?'))return;
  try{localStorage.removeItem(EXPE_LS_DELAIS_KEY);}catch(e){}
  expeMergeDelais();
  applyDelaisToMap();
  showToast('Délais réinitialisés.','success');
  refreshExpeCartePanel();
}

// APRÈS :
async function expeResetDelais(){
  if(!confirm('Réinitialiser tous les délais aux valeurs par défaut ? Cette action s\'applique à tous les utilisateurs.'))return;
  try {
    await api('/expe/delais/reset', { method: 'POST', body: JSON.stringify({ type_envoi: 'default' }) });
    await expeLoadDelaisFromAPI();
    applyDelaisToMap();
    showToast('Délais réinitialisés.','success');
    refreshExpeCartePanel();
  } catch(e) {
    showToast(e.message || 'Erreur lors de la réinitialisation','danger');
  }
}
```

### 3.4 — Modifier `saveEditDelais()`

Remplacer l'implémentation complète :

```js
// AVANT :
function saveEditDelais(){
  if(!C.editDept||!expeCanEditDelais())return;
  const delInp=document.getElementById('expe-carte-edit-delai');
  const zoneSel=document.getElementById('expe-carte-edit-zone');
  const delai=(delInp&&delInp.value||'').trim();
  const zone=zoneSel&&zoneSel.value;
  if(!delai){showToast('Délai obligatoire','danger');return;}
  const ov=expeLoadDelaisOverrides();
  ov[C.editDept]={delai:delai,zone:zone||DELAIS_FRANCE[C.editDept].zone};
  expeSaveDelaisOverrides(ov);
  expeMergeDelais();
  applyDelaisToMap();
  highlightDept(C.editDept);
  showToast('Délai enregistré.','success');
}

// APRÈS :
async function saveEditDelais(){
  if(!C.editDept||!expeCanEditDelais())return;
  const delInp=document.getElementById('expe-carte-edit-delai');
  const zoneSel=document.getElementById('expe-carte-edit-zone');
  const delai=(delInp&&delInp.value||'').trim();
  const zone=zoneSel&&zoneSel.value;
  if(!delai){showToast('Délai obligatoire','danger');return;}

  // Optimistic update local immédiat (UX réactive)
  if(!DELAIS_FRANCE[C.editDept]){
    DELAIS_FRANCE[C.editDept]={label:C.editDept,zone:'france',delai:'J+2'};
  }
  DELAIS_FRANCE[C.editDept].delai=delai;
  DELAIS_FRANCE[C.editDept].zone=zone||DELAIS_FRANCE[C.editDept].zone;
  applyDelaisToMap();
  highlightDept(C.editDept);

  // Persister en base
  try {
    await api('/expe/delais', {
      method: 'PUT',
      body: JSON.stringify({
        overrides: {
          [C.editDept]: { delai: delai, zone: zone||DELAIS_FRANCE[C.editDept].zone }
        },
        type_envoi: 'default'
      })
    });
    showToast('Délai enregistré.','success');
  } catch(e) {
    showToast(e.message || 'Erreur — délai non sauvegardé','danger');
    // Recharger depuis l'API pour annuler l'update optimiste
    await expeLoadDelaisFromAPI();
    applyDelaisToMap();
  }
}
```

### 3.5 — Modifier le point d'initialisation de la carte

Chercher dans `expe_assets.py` la ligne qui appelle `expeMergeDelais()` (appelée au chargement de la page, probablement dans une fonction d'init de la section carte ou dans le chargement général de MyExpé).

**Exemple — si l'init ressemble à :**
```js
// AVANT :
expeMergeDelais();
applyDelaisToMap();

// APRÈS — rendre async :
expeLoadDelaisFromAPI().then(() => {
  applyDelaisToMap();
});
```

Si l'init est dans une fonction async existante, utiliser directement `await expeLoadDelaisFromAPI()`.

**Chercher aussi** tout appel à `expeMergeDelais()` dans le fichier et le remplacer par `await expeLoadDelaisFromAPI()` ou par `expeLoadDelaisFromAPI().then(applyDelaisToMap)` selon le contexte (sync vs async).

### 3.6 — `getDeptData()` reste inchangée

La fonction `getDeptData(num)` lit `DELAIS_FRANCE[k]` — elle reste exactement comme elle est. Seule la façon dont `DELAIS_FRANCE` est peuplé change (API au lieu de localStorage).

```js
// NE PAS MODIFIER :
function getDeptData(num){
  const k=String(num||'').trim();
  return DELAIS_FRANCE[k]||null;
}
```

---

## Étape 4 — Charger les délais au montage de la section MyExpé

Dans `app/web/expe_page.py` (ou `app/web/html.py`), trouver le point d'entrée qui charge la page MyExpé (`/expe`). Ajouter le chargement des délais au montage, avant l'appel à `applyDelaisToMap()`.

**Pattern typique :**

```js
// Dans la fonction de chargement de la section MyExpé (async) :
async function chargerExpe() {
  // ... chargements existants (départs, transporteurs, etc.) ...

  // Charger les délais depuis l'API (remplace expeMergeDelais)
  await expeLoadDelaisFromAPI();
  applyDelaisToMap();

  // ... suite du rendu ...
}
```

S'assurer que `expeLoadDelaisFromAPI` est toujours appelée **avant** `applyDelaisToMap()` — l'ordre est critique.

---

## Vérification de la bascule complète

Après application, s'assurer qu'aucun appel à `localStorage` ne reste pour les délais. Chercher dans `expe_assets.py` :

```
EXPE_LS_DELAIS_KEY       → ne doit plus exister
localStorage.*delai      → ne doit plus exister
expeLoadDelaisOverrides  → ne doit plus exister
expeSaveDelaisOverrides  → ne doit plus exister
expeMergeDelais          → ne doit plus exister (sauf si renommée)
```

---

## Résumé des fichiers à modifier

| Fichier | Ce qui change |
|---|---|
| `app/core/database.py` | Migration v67 : table `expe_delais` + seed depuis `DELAIS_FRANCE_DEFAULT` |
| `app/routers/expe_departs.py` | 3 endpoints : `GET /delais`, `PUT /delais`, `POST /delais/reset` |
| `app/web/expe_assets.py` | Supprimer 4 fonctions localStorage · Ajouter `expeLoadDelaisFromAPI()` · Modifier `saveEditDelais()` et `expeResetDelais()` en async · Remplacer tous les appels à `expeMergeDelais()` |

---

## Vérification finale

1. Lancer l'app — vérifier qu'il n'y a pas d'erreur de migration.
2. En SQLite : `SELECT COUNT(*) FROM expe_delais` → doit retourner ~100 lignes (un par département).
3. `GET /api/expe/delais` → doit retourner le dict complet de tous les départements.
4. Ouvrir la carte dans MyExpé → vérifier que les couleurs sont correctes (identiques à avant).
5. Passer en mode édition → sélectionner un département → changer le délai → "Enregistrer" → vérifier que la carte se met à jour.
6. Recharger la page → vérifier que le délai modifié est persisté (et non revenu au défaut).
7. Cliquer "Réinitialiser" → vérifier que les délais retournent aux valeurs de `DELAIS_FRANCE_DEFAULT`.
8. Se connecter sur un autre poste (ou autre navigateur) → vérifier que les délais modifiés en étape 6 sont bien visibles (c'est la validation de la migration depuis le localStorage).
9. Vérifier que `localStorage` ne contient plus de clé `mysifa_expe_delais_v2` après utilisation.

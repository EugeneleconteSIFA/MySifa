# Prompts Windsurf — Bridge Access : OF + Fiche technique

Exécuter dans l'ordre. Les fichiers `api_keys` (migration v89), les endpoints de gestion
des clés dans `settings.py` et l'onglet UI "Clés API" dans `/settings` sont corrects —
ne pas y toucher.

---

## PROMPT A — Migration DB + réécriture bridge + main.py

### A1 — Migration v90 dans `app/core/database.py`

Dans la fonction `_migrate(conn)`, après le bloc `version=89`, ajoute avant l'appel final
à `_record_schema_migration(conn, SCHEMA_MIGRATION_VERSION_BASELINE, ...)` :

```python
    # v90 — Fiches techniques produits (bridge Access)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=90 LIMIT 1").fetchone():
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS fiches_techniques (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                ref_produit          TEXT NOT NULL UNIQUE,
                designation          TEXT,
                machine              TEXT,
                laize                REAL,
                format               TEXT,
                matiere              TEXT,
                ref_matiere          TEXT,
                glassine             TEXT,
                ref_adhesif          TEXT,
                qte_adhesif_g        REAL,
                qte_adhesif_kg       REAL,
                adhesif_label        TEXT,
                qte_au_mille         REAL,
                nb_levees            INTEGER,
                conditionnement      TEXT,
                tolerance            TEXT,
                cartons_type         TEXT,
                mandrins_dia         TEXT,
                mandrin_longueur     REAL,
                nb_mandrins          INTEGER,
                nb_tubes             INTEGER,
                bobinettes_completes TEXT,
                outil_1_forme        TEXT,
                outil_1_numero       TEXT,
                outil_1_angle        TEXT,
                outil_1_mag          TEXT,
                outil_1_cp           TEXT,
                outil_1_hauteur      REAL,
                outil_1_fournisseur  TEXT,
                outil_2_forme        TEXT,
                outil_2_numero       TEXT,
                outil_2_angle        TEXT,
                outil_2_cp           TEXT,
                outil_alt_forme      TEXT,
                outil_alt_numero     TEXT,
                outil_alt_angle      TEXT,
                outil_alt_fournisseur TEXT,
                date_import          TEXT,
                imported_by          TEXT,
                updated_at           TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_ft_ref ON fiches_techniques(ref_produit);
        """)
        conn.commit()
        _record_schema_migration(conn, 90, "fiches_techniques")
```

Différence avec `of_imports` : pas de `of_numero`, `date_creation`, `delai_client`,
`qte_etiquettes`, `qte_bobines`, `metrage`, `pdf_filename`, `statut` — ces champs sont
propres à une commande, pas à un produit.

---

### A2 — Réécrire intégralement `app/routers/api_bridge.py`

Remplace tout le contenu par :

```python
"""
Pont API — Access → MySifa
Authentification : header X-Api-Key (pas de session cookie).

Endpoints :
  GET  /api/bridge/health                → ping sans auth
  POST /api/bridge/of                    → insère un OF dans of_imports        (scope of:write)
  GET  /api/bridge/of                    → liste les OF importés                (scope of:read)
  POST /api/bridge/fiche-technique       → crée/met à jour une fiche technique  (scope fiche:write)
  GET  /api/bridge/fiche-technique       → liste les fiches techniques           (scope fiche:read)
  GET  /api/bridge/fiche-technique/{ref} → fiche d'un produit                   (scope fiche:read)
"""
import hashlib
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.core.database import get_db

router = APIRouter(prefix="/api/bridge", tags=["bridge"])


# ── Auth ─────────────────────────────────────────────────────────────

def _require_scope(raw_key: Optional[str], required_scope: str) -> None:
    if not raw_key:
        raise HTTPException(status_code=401, detail="Clé API manquante (header X-Api-Key).")
    h = hashlib.sha256(raw_key.encode()).hexdigest()
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, scopes, is_active FROM api_keys WHERE key_hash=? LIMIT 1", (h,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Clé API invalide.")
        if not row["is_active"]:
            raise HTTPException(status_code=403, detail="Clé API révoquée.")
        scopes = [s.strip() for s in (row["scopes"] or "").split(",")]
        if required_scope not in scopes:
            raise HTTPException(
                status_code=403,
                detail=f"Scope '{required_scope}' non autorisé pour cette clé."
            )
        try:
            conn.execute(
                "UPDATE api_keys SET last_used_at=? WHERE id=?",
                (datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), row["id"])
            )
            conn.commit()
        except Exception:
            pass


# ── Champs communs OF + Fiche technique ──────────────────────────────
# (extraits en classe de base pour éviter la duplication)

class _TechFields(BaseModel):
    machine:              Optional[str]   = None
    laize:                Optional[float] = None
    format:               Optional[str]   = None
    matiere:              Optional[str]   = None
    ref_matiere:          Optional[str]   = None
    glassine:             Optional[str]   = None
    ref_adhesif:          Optional[str]   = None
    qte_adhesif_g:        Optional[float] = None
    qte_adhesif_kg:       Optional[float] = None
    adhesif_label:        Optional[str]   = None
    qte_au_mille:         Optional[float] = None
    nb_levees:            Optional[int]   = None
    conditionnement:      Optional[str]   = None
    tolerance:            Optional[str]   = None
    cartons_type:         Optional[str]   = None
    mandrins_dia:         Optional[str]   = None
    mandrin_longueur:     Optional[float] = None
    nb_mandrins:          Optional[int]   = None
    nb_tubes:             Optional[int]   = None
    bobinettes_completes: Optional[str]   = None
    outil_1_forme:        Optional[str]   = None
    outil_1_numero:       Optional[str]   = None
    outil_1_angle:        Optional[str]   = None
    outil_1_mag:          Optional[str]   = None
    outil_1_cp:           Optional[str]   = None
    outil_1_hauteur:      Optional[float] = None
    outil_1_fournisseur:  Optional[str]   = None
    outil_2_forme:        Optional[str]   = None
    outil_2_numero:       Optional[str]   = None
    outil_2_angle:        Optional[str]   = None
    outil_2_cp:           Optional[str]   = None
    outil_alt_forme:      Optional[str]   = None
    outil_alt_numero:     Optional[str]   = None
    outil_alt_angle:      Optional[str]   = None
    outil_alt_fournisseur:Optional[str]   = None


# ── Modèles ───────────────────────────────────────────────────────────

class OFIn(_TechFields):
    """Ordre de Fabrication — un enregistrement par commande."""
    of_numero:      Optional[str]  = None  # n° OF Access
    reference:      Optional[str]  = None  # référence produit
    date_creation:  Optional[str]  = None  # "YYYY-MM-DD"
    delai_client:   Optional[str]  = None
    qte_etiquettes: Optional[int]  = None
    qte_bobines:    Optional[float]= None
    metrage:        Optional[int]  = None
    source:         Optional[str]  = "access_bridge"


class FicheTechniqueIn(_TechFields):
    """Fiche technique produit — une par référence (UNIQUE), mise à jour si existe."""
    ref_produit:  str             # obligatoire, clé UNIQUE
    designation:  Optional[str]  = None


# ── Endpoints ─────────────────────────────────────────────────────────

@router.get("/health")
def bridge_health():
    return {"status": "ok", "service": "mysifa-bridge"}


# ─── OF ───────────────────────────────────────────────────────────────

@router.post("/of", status_code=201)
def push_of(
    body: OFIn,
    x_api_key: Optional[str] = Header(default=None),
):
    """
    Insère un OF dans of_imports.
    Idempotent sur (of_numero, reference) : si la combinaison existe déjà,
    retourne is_duplicate=true sans créer de doublon.
    """
    _require_scope(x_api_key, "of:write")
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    with get_db() as conn:
        # Vérification doublon
        if body.of_numero and body.reference:
            dup = conn.execute(
                """SELECT id FROM of_imports
                   WHERE LOWER(TRIM(COALESCE(of_numero,'')))=LOWER(TRIM(?))
                     AND LOWER(TRIM(COALESCE(reference,'')))=LOWER(TRIM(?))
                   LIMIT 1""",
                (body.of_numero, body.reference)
            ).fetchone()
            if dup:
                return {"inserted": False, "is_duplicate": True, "id": dup["id"]}

        data = body.model_dump(exclude={"source"})
        data["date_import"]  = now
        data["imported_by"]  = f"access_bridge:{body.source or 'api'}"
        data["statut"]       = "en_attente"

        cols = list(data.keys())
        vals = list(data.values())
        cur  = conn.execute(
            f"INSERT INTO of_imports ({', '.join(cols)}) VALUES ({', '.join('?'*len(cols))})",
            vals
        )
        conn.commit()
        return {"inserted": True, "is_duplicate": False, "id": cur.lastrowid}


@router.get("/of")
def list_of(x_api_key: Optional[str] = Header(default=None)):
    """Liste les OF importés, du plus récent au plus ancien."""
    _require_scope(x_api_key, "of:read")
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, of_numero, reference, date_creation, delai_client,
                      machine, laize, format, qte_etiquettes, metrage,
                      date_import, imported_by, statut
               FROM of_imports
               ORDER BY date_import DESC
               LIMIT 500"""
        ).fetchall()
    return {"of": [dict(r) for r in rows]}


# ─── Fiche technique ──────────────────────────────────────────────────

@router.post("/fiche-technique", status_code=201)
def push_fiche_technique(
    body: FicheTechniqueIn,
    x_api_key: Optional[str] = Header(default=None),
):
    """
    Crée ou met à jour la fiche technique d'un produit (UPSERT sur ref_produit).
    Si la référence existe déjà → mise à jour complète.
    """
    _require_scope(x_api_key, "fiche:write")
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    data = body.model_dump()
    data["updated_at"]  = now
    data["date_import"] = now   # sera écrasé par updated_at si la fiche existe déjà

    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM fiches_techniques WHERE LOWER(TRIM(ref_produit))=LOWER(TRIM(?)) LIMIT 1",
            (body.ref_produit.strip(),)
        ).fetchone()

        if existing:
            # Mise à jour — on ne change pas date_import, on met updated_at
            update_data = {k: v for k, v in data.items() if k not in ("date_import",)}
            update_data["imported_by"] = "access_bridge"
            set_clause = ", ".join(f"{k}=?" for k in update_data)
            conn.execute(
                f"UPDATE fiches_techniques SET {set_clause} WHERE id=?",
                list(update_data.values()) + [existing["id"]]
            )
            conn.commit()
            return {"action": "updated", "id": existing["id"], "ref_produit": body.ref_produit}
        else:
            data["imported_by"] = "access_bridge"
            cols = list(data.keys())
            vals = list(data.values())
            cur  = conn.execute(
                f"INSERT INTO fiches_techniques ({', '.join(cols)}) VALUES ({', '.join('?'*len(cols))})",
                vals
            )
            conn.commit()
            return {"action": "created", "id": cur.lastrowid, "ref_produit": body.ref_produit}


@router.get("/fiche-technique")
def list_fiches_techniques(x_api_key: Optional[str] = Header(default=None)):
    """Liste toutes les fiches techniques."""
    _require_scope(x_api_key, "fiche:read")
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, ref_produit, designation, machine, laize, format,
                      matiere, date_import, updated_at
               FROM fiches_techniques
               ORDER BY ref_produit ASC"""
        ).fetchall()
    return {"fiches": [dict(r) for r in rows]}


@router.get("/fiche-technique/{ref_produit}")
def get_fiche_technique(
    ref_produit: str,
    x_api_key: Optional[str] = Header(default=None),
):
    """Retourne la fiche technique complète d'un produit."""
    _require_scope(x_api_key, "fiche:read")
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM fiches_techniques WHERE LOWER(TRIM(ref_produit))=LOWER(TRIM(?)) LIMIT 1",
            (ref_produit.strip(),)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Fiche technique '{ref_produit}' introuvable.")
    return dict(row)
```

---

### A3 — Corriger le scope par défaut dans `app/routers/settings.py`

Cherche la ligne :
```python
scopes: str = "production:read,production:write"
```
Remplace par :
```python
scopes: str = "of:write,of:read,fiche:write,fiche:read"
```

---

### A4 — Finaliser `main.py`

L'import est déjà présent ligne 67 :
```python
from app.routers.api_bridge import router as bridge_router
```

Cherche le bloc `app.include_router(of_import_router, prefix="")` et ajoute juste après :
```python
app.include_router(bridge_router)
```

---

## PROMPT B — UI : onglet "OF + Fiche technique" dans MyProd

**Fichier :** `app/web/fabrication_page.py`

### Contexte important

- L'onglet `of` existe déjà avec `switchFabTab('of')` et `loadOfImports()`
- La fonction `renderOfPanel()` (vers ligne 1618) affiche la liste des OFs
- Il ne faut **pas supprimer** la logique OF existante — uniquement l'encapsuler dans un sous-onglet

### Ce qu'il faut faire

#### B1 — Renommer le bouton de l'onglet

Cherche les deux occurrences du bouton qui fait `switchFabTab('of')` (il y en a une desktop
et une mobile, vers les lignes 2745 et 2935). Elles ressemblent à :
```javascript
h('button',{className:'fab-tab-btn'+(S.fabTab==='of'?' active':''),onClick:()=>{ void switchFabTab('of'); }}, ...
```
Dans le texte affiché du bouton, remplace `'OF'` (ou le label actuel) par :
```
'OF + Fiche technique'
```

#### B2 — Ajouter un sous-état dans S

Dans l'objet d'état initial `S` (cherche `const S = {` ou `let S = {`), ajoute un champ :
```javascript
ofSubTab: 'of',   // 'of' | 'fiche'
```

#### B3 — Ajouter les fonctions de chargement des fiches techniques

Après la fonction `loadOfImports()` (vers ligne 1489), ajoute :

```javascript
async function loadFiches(){
  set({fichesLoading:true});
  try{
    const data = await apiFetch('/api/bridge/fiche-technique', {
      headers:{'X-Api-Key': S.bridgeApiKey || ''}
    });
    set({fiches: Array.isArray(data.fiches) ? data.fiches : [], fichesLoading:false});
  }catch(e){
    set({fichesLoading:false});
  }
}
```

> Note : `S.bridgeApiKey` n'est pas encore implémenté — pour l'instant, l'endpoint
> `/api/bridge/fiche-technique` sans clé retournera 401. C'est prévu : la connexion
> directe depuis le frontend viendra plus tard. Pour l'instant, laisser la liste vide
> si non authentifié, sans erreur visible.

#### B4 — Modifier `switchFabTab` pour le chargement

Dans la fonction `switchFabTab` (vers ligne 1452), dans le bloc `if(tab==='of')`, ajoute :
```javascript
  if(tab==='of'){
    await loadOfImports();
    await loadFiches();   // ← ajouter cette ligne
  }
```

#### B5 — Remplacer `renderOfPanel()` par un panel avec deux sous-onglets

Cherche la fonction `renderOfPanel()` (vers ligne 1618). Enveloppe son contenu existant
dans une structure à deux sous-onglets. La fonction doit devenir :

```javascript
function renderOfPanel(){
  const subTab = S.ofSubTab || 'of';

  // ── Barre de sous-onglets ──────────────────────────────────────────
  const subTabBar = h('div',{style:'display:flex;gap:6px;margin-bottom:18px'},
    h('button',{
      style:`padding:7px 16px;border-radius:8px;border:none;font-size:12px;font-weight:600;
             cursor:pointer;font-family:inherit;transition:background .15s,color .15s;
             background:${subTab==='of'?'rgba(34,211,238,.15)':'transparent'};
             color:${subTab==='of'?'var(--accent)':'var(--muted)'};`,
      onClick:()=>{ set({ofSubTab:'of'}); renderApp(); }
    }, 'OF'),
    h('button',{
      style:`padding:7px 16px;border-radius:8px;border:none;font-size:12px;font-weight:600;
             cursor:pointer;font-family:inherit;transition:background .15s,color .15s;
             background:${subTab==='fiche'?'rgba(34,211,238,.15)':'transparent'};
             color:${subTab==='fiche'?'var(--accent)':'var(--muted)'};`,
      onClick:()=>{ set({ofSubTab:'fiche'}); renderApp(); }
    }, 'Fiche technique')
  );

  // ── Contenu selon sous-onglet ──────────────────────────────────────
  const content = subTab === 'of'
    ? renderOfSubPanel()          // ← tout le contenu OF actuel (voir ci-dessous)
    : renderFicheSubPanel();      // ← nouveau panel fiche technique

  return h('div',{className:'fab-of-panel'}, subTabBar, content);
}
```

#### B6 — Renommer le contenu OF actuel

Le code actuel de `renderOfPanel()` (la partie qui construit la liste des OF avec
`h('table',{className:'fab-of-table'},...`) devient une nouvelle fonction
`renderOfSubPanel()` — copier/coller le contenu existant dans cette nouvelle fonction,
sans y toucher.

#### B7 — Créer `renderFicheSubPanel()`

Ajoute cette nouvelle fonction après `renderOfPanel()` :

```javascript
function renderFicheSubPanel(){
  if(S.fichesLoading){
    return h('div',{style:'padding:32px;text-align:center;color:var(--muted);font-size:13px'},
      'Chargement…');
  }
  const fiches = S.fiches || [];
  if(fiches.length === 0){
    return h('div',{style:'padding:32px;text-align:center;color:var(--muted);font-size:13px'},
      'Aucune fiche technique importée.');
  }

  const LABELS = {
    ref_produit:'Référence', designation:'Désignation', machine:'Machine',
    laize:'Laize', format:'Format', matiere:'Matière', updated_at:'Mis à jour'
  };
  const COLS = Object.keys(LABELS);

  return h('div',{style:'overflow:auto;flex:1'},
    h('table',{className:'fab-of-table',style:'min-width:700px'},
      h('thead',null,
        h('tr',null, ...COLS.map(k=>
          h('th',{key:k,style:'text-align:left'}, LABELS[k])
        ))
      ),
      h('tbody',null,
        ...fiches.map((f,i)=>
          h('tr',{key:f.id||i},
            ...COLS.map(k=>
              h('td',{key:k}, f[k] != null ? String(f[k]) : '—')
            )
          )
        )
      )
    )
  );
}
```

---

## Résumé des fichiers modifiés

| Fichier | Modification |
|---|---|
| `app/core/database.py` | Migration v90 : table `fiches_techniques` |
| `app/routers/api_bridge.py` | Réécriture complète — OF + fiche technique |
| `app/routers/settings.py` | Scope par défaut `of:write,of:read,fiche:write,fiche:read` |
| `main.py` | Ajout `app.include_router(bridge_router)` |
| `app/web/fabrication_page.py` | Onglet "OF + Fiche technique" avec deux sous-onglets |

## Points d'attention

- **Ne pas toucher** `app/routers/of_import.py` ni la logique d'import PDF existante —
  le bridge API est un canal supplémentaire, pas un remplacement
- **`data/production.db` et `DB_PATH`** : ne jamais modifier
- **`duree_heures` est REAL** — toujours `parseFloat()` si utilisé en JS
- Le sous-onglet "Fiche technique" dans MyProd affiche une liste vide tant qu'aucune
  fiche n'est poussée via le bridge — c'est le comportement attendu

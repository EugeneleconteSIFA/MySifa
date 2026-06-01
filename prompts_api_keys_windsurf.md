# Prompts Windsurf — Système de clés API MySifa

Exécute ces 3 prompts dans l'ordre. Chaque prompt est autonome mais s'appuie sur le précédent.

---

## PROMPT 1 — Migration DB : table `api_keys`

**Fichier à modifier :** `app/core/database.py`

Dans la fonction `_migrate(conn)`, après le bloc `version=88` (ligne ~2780), ajoute le bloc suivant **avant** l'appel final à `_record_schema_migration(conn, SCHEMA_MIGRATION_VERSION_BASELINE, ...)` :

```python
    # v89 — Table des clés API (pont Access ↔ MySifa)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=89 LIMIT 1").fetchone():
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                key_prefix  TEXT NOT NULL,
                key_hash    TEXT NOT NULL UNIQUE,
                scopes      TEXT NOT NULL DEFAULT 'production:read,production:write',
                is_active   INTEGER NOT NULL DEFAULT 1,
                created_by  TEXT,
                created_at  TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
                last_used_at TEXT,
                revoked_at  TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
            CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active);
        """)
        conn.commit()
        _record_schema_migration(conn, 89, "api_keys")
```

**Règle de migration :** respecter exactement le pattern existant — `if not conn.execute(...).fetchone()` + `executescript` + `conn.commit()` + `_record_schema_migration`.

**Ne rien toucher d'autre dans ce fichier.**

---

## PROMPT 2 — Endpoints backend : gestion et authentification des clés API

### 2a — Créer `app/routers/api_bridge.py` (nouveau fichier)

Crée ce fichier de zéro :

```python
"""
Pont API — Access ↔ MySifa
Authentification par clé API (header X-Api-Key), pas de session cookie.
Scope requis par endpoint :
  - POST /api/bridge/production   → production:write
  - GET  /api/bridge/dossiers     → production:read
"""
import hashlib
import secrets
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

from app.core.database import get_db

router = APIRouter(prefix="/api/bridge", tags=["bridge"])


# ── helpers ──────────────────────────────────────────────────────────

def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _require_scope(raw_key: Optional[str], required_scope: str):
    """Vérifie la clé API et le scope requis. Lève 401/403 si invalide."""
    if not raw_key:
        raise HTTPException(status_code=401, detail="Clé API manquante (header X-Api-Key).")
    h = _hash_key(raw_key)
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
            raise HTTPException(status_code=403, detail=f"Scope '{required_scope}' non autorisé pour cette clé.")
        # Mise à jour last_used_at (best-effort)
        try:
            conn.execute(
                "UPDATE api_keys SET last_used_at=? WHERE id=?",
                (datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), row["id"])
            )
            conn.commit()
        except Exception:
            pass


# ── modèles Pydantic ─────────────────────────────────────────────────

class ProductionEntryIn(BaseModel):
    operateur: str
    date_operation: str          # format: "YYYY-MM-DDTHH:MM:SS"
    operation_code: str          # ex: "01", "89", etc.
    no_dossier: Optional[str] = None
    duree_heures: Optional[float] = None
    commentaire: Optional[str] = None
    metrage_prevu: Optional[float] = None
    metrage_reel: Optional[float] = None
    source: Optional[str] = "access_bridge"  # traçabilité


# ── endpoints ────────────────────────────────────────────────────────

@router.get("/health")
def bridge_health():
    """Vérification de disponibilité sans authentification."""
    return {"status": "ok", "service": "mysifa-bridge"}


@router.get("/dossiers")
def get_dossiers(
    statut: Optional[str] = None,
    x_api_key: Optional[str] = Header(default=None),
):
    """
    Retourne la liste des dossiers de planning.
    Paramètre optionnel : ?statut=en_cours | attente | termine
    """
    _require_scope(x_api_key, "production:read")
    with get_db() as conn:
        q = "SELECT * FROM planning_entries"
        params = []
        if statut:
            q += " WHERE statut=?"
            params.append(statut)
        q += " ORDER BY created_at DESC LIMIT 500"
        rows = conn.execute(q, params).fetchall()
    return {"dossiers": [dict(r) for r in rows]}


@router.post("/production", status_code=201)
def push_production_entry(
    entry: ProductionEntryIn,
    x_api_key: Optional[str] = Header(default=None),
):
    """
    Insère une saisie de production reçue depuis le pont Access.
    Idempotent : si la combinaison (operateur, date_operation, operation_code, no_dossier)
    existe déjà, retourne 200 avec is_duplicate=true sans créer de doublon.
    """
    _require_scope(x_api_key, "production:write")
    with get_db() as conn:
        # Vérification doublon
        existing = conn.execute(
            """SELECT id FROM production_data
               WHERE operateur=? AND date_operation=? AND operation_code=?
                 AND COALESCE(no_dossier,'')=COALESCE(?,'') LIMIT 1""",
            (entry.operateur, entry.date_operation, entry.operation_code, entry.no_dossier)
        ).fetchone()
        if existing:
            return {"inserted": False, "is_duplicate": True, "id": existing["id"]}

        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        cur = conn.execute(
            """INSERT INTO production_data
               (operateur, date_operation, operation_code, no_dossier,
                duree_heures, commentaire, metrage_prevu, metrage_reel,
                est_manuel, modifie_par, modifie_le, modifie_note)
               VALUES (?,?,?,?,?,?,?,?,1,?,?,?)""",
            (
                entry.operateur, entry.date_operation, entry.operation_code, entry.no_dossier,
                entry.duree_heures, entry.commentaire, entry.metrage_prevu, entry.metrage_reel,
                f"bridge:{entry.source}", now, f"Import pont Access ({entry.source})"
            )
        )
        conn.commit()
        return {"inserted": True, "is_duplicate": False, "id": cur.lastrowid}
```

### 2b — Ajouter les endpoints de gestion dans `app/routers/settings.py`

À la **fin** du fichier `app/routers/settings.py`, ajoute les routes suivantes.

Ajoute d'abord ces imports en haut du fichier si absents :
```python
import hashlib
import secrets
from typing import Optional
from pydantic import BaseModel
```

Puis ajoute à la fin du fichier :

```python
# ══════════════════════════════════════════════════════════════════
# Gestion des clés API (superadmin uniquement)
# ══════════════════════════════════════════════════════════════════

def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


class ApiKeyCreateIn(BaseModel):
    name: str
    scopes: str = "production:read,production:write"


@router.get("/api/settings/api-keys")
def list_api_keys(request: Request):
    require_superadmin(request)
    from database import get_db
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, name, key_prefix, scopes, is_active,
                      created_by, created_at, last_used_at, revoked_at
               FROM api_keys ORDER BY created_at DESC"""
        ).fetchall()
    return {"keys": [dict(r) for r in rows]}


@router.post("/api/settings/api-keys")
def create_api_key(body: ApiKeyCreateIn, request: Request):
    require_superadmin(request)
    user = get_current_user(request)
    from database import get_db

    raw = "msk_" + secrets.token_hex(32)   # 68 chars, préfixe "msk_"
    h = _hash_key(raw)
    prefix = raw[:12]  # affiché dans la liste pour identification visuelle

    with get_db() as conn:
        conn.execute(
            """INSERT INTO api_keys (name, key_prefix, key_hash, scopes, is_active, created_by)
               VALUES (?,?,?,?,1,?)""",
            (body.name.strip(), prefix, h, body.scopes.strip(), user.get("email", ""))
        )
        conn.commit()

    # La clé brute n'est retournée QU'UNE SEULE FOIS ici — elle n'est jamais stockée en clair
    return {"key": raw, "prefix": prefix, "name": body.name}


@router.patch("/api/settings/api-keys/{key_id}/revoke")
def revoke_api_key(key_id: int, request: Request):
    require_superadmin(request)
    from database import get_db
    from datetime import datetime
    with get_db() as conn:
        row = conn.execute("SELECT id FROM api_keys WHERE id=?", (key_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Clé introuvable.")
        conn.execute(
            "UPDATE api_keys SET is_active=0, revoked_at=? WHERE id=?",
            (datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), key_id)
        )
        conn.commit()
    return {"revoked": True, "id": key_id}


@router.delete("/api/settings/api-keys/{key_id}")
def delete_api_key(key_id: int, request: Request):
    require_superadmin(request)
    from database import get_db
    with get_db() as conn:
        conn.execute("DELETE FROM api_keys WHERE id=?", (key_id,))
        conn.commit()
    return {"deleted": True, "id": key_id}
```

### 2c — Enregistrer le router bridge dans `main.py`

Dans `main.py`, ajoute l'import et l'inclusion du router bridge. Cherche les lignes où les autres routers sont inclus (pattern `app.include_router(...)`) et ajoute :

```python
from app.routers.api_bridge import router as bridge_router
app.include_router(bridge_router)
```

---

## PROMPT 3 — Interface utilisateur : section "Clés API" dans `/settings`

**Fichier à modifier :** `app/web/settings_page.py`

### Contexte UI à respecter impérativement
- Design system : variables CSS `--bg`, `--card`, `--border`, `--text`, `--accent`, `--ok`, `--danger`, `--warn`, `--muted`
- Pas d'emojis — icônes SVG inline uniquement
- Toasts via `showToast(msg, type)` — jamais `alert()`
- Boutons : classe `.btn` avec `.btn-accent` ou `.btn-danger`
- La page utilise des onglets — cherche le pattern `data-tab` dans `SETTINGS_HTML`

### Ce qu'il faut ajouter

#### Étape 3a — Ajouter un onglet "API" dans la sidebar de settings

Dans `SETTINGS_HTML`, dans la liste des boutons `.nav-btn` (sidebar gauche des paramètres), ajoute un bouton :

```html
<button class="nav-btn" onclick="showTab('api')" id="tab-api">
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
  Clés API
</button>
```

#### Étape 3b — Ajouter le panneau de contenu pour l'onglet "api"

Dans `SETTINGS_HTML`, après le dernier panneau `<div id="panel-..." ...>`, ajoute :

```html
<!-- ═══════════════════════ PANEL API ═══════════════════════ -->
<div id="panel-api" class="tab-panel" style="display:none">
  <div style="max-width:860px">
    <div style="margin-bottom:24px">
      <div style="font-size:18px;font-weight:700;color:var(--text);margin-bottom:6px">Clés API</div>
      <div style="font-size:13px;color:var(--muted)">
        Générez des clés pour permettre à des scripts externes (pont Access) d'accéder à MySifa.
        La clé secrète n'est affichée qu'une seule fois à la création — conservez-la.
      </div>
    </div>

    <!-- Formulaire création -->
    <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:24px">
      <div style="font-size:13px;font-weight:600;color:var(--text);margin-bottom:14px;text-transform:uppercase;letter-spacing:.5px">Nouvelle clé</div>
      <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end">
        <div style="flex:1;min-width:200px">
          <label style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:6px">Nom</label>
          <input id="ak-name" type="text" placeholder="ex: Pont Access Usine"
            style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px 14px;color:var(--text);font-size:13px;outline:none;font-family:inherit"
            onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'">
        </div>
        <button class="btn btn-accent" onclick="createApiKey()" style="white-space:nowrap">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="margin-right:6px"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          Générer la clé
        </button>
      </div>
    </div>

    <!-- Alerte clé générée (affichée une seule fois) -->
    <div id="ak-reveal" style="display:none;background:rgba(34,211,238,.1);border:1px solid var(--accent);border-radius:12px;padding:16px 20px;margin-bottom:24px">
      <div style="font-size:12px;font-weight:600;color:var(--accent);margin-bottom:8px;text-transform:uppercase;letter-spacing:.5px">
        Copiez cette clé maintenant — elle ne sera plus affichée
      </div>
      <div style="display:flex;gap:10px;align-items:center">
        <code id="ak-reveal-value" style="flex:1;font-family:monospace;font-size:13px;color:var(--text);word-break:break-all;background:var(--bg);padding:10px 14px;border-radius:8px;border:1px solid var(--border)"></code>
        <button class="btn btn-ghost" onclick="copyApiKey()" title="Copier" style="border:1px solid var(--border);padding:10px 12px">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
        </button>
      </div>
    </div>

    <!-- Liste des clés -->
    <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden">
      <div style="padding:16px 20px;border-bottom:1px solid var(--border);font-size:13px;font-weight:600;color:var(--text)">Clés existantes</div>
      <div id="ak-list" style="padding:8px 0">
        <div style="padding:24px;text-align:center;color:var(--muted);font-size:13px">Chargement…</div>
      </div>
    </div>
  </div>
</div>
```

#### Étape 3c — Ajouter le JavaScript de l'onglet API

Dans le bloc `<script>` de `SETTINGS_HTML` (ou juste avant la balise `</script>` de fermeture), ajoute :

```javascript
// ── Clés API ──────────────────────────────────────────────────────
async function loadApiKeys() {
  const res = await fetch('/api/settings/api-keys', {credentials:'include'});
  const data = await res.json();
  const list = document.getElementById('ak-list');
  if (!data.keys || data.keys.length === 0) {
    list.innerHTML = '<div style="padding:24px;text-align:center;color:var(--muted);font-size:13px">Aucune clé créée.</div>';
    return;
  }
  list.innerHTML = data.keys.map(k => `
    <div style="display:flex;align-items:center;gap:14px;padding:12px 20px;border-bottom:1px solid var(--border);flex-wrap:wrap">
      <div style="flex:1;min-width:160px">
        <div style="font-size:13px;font-weight:600;color:var(--text)">${escHtml(k.name)}</div>
        <div style="font-size:11px;color:var(--muted);margin-top:2px;font-family:monospace">${escHtml(k.key_prefix)}…</div>
      </div>
      <div style="font-size:11px;color:var(--muted)">${escHtml(k.scopes||'')}</div>
      <div style="font-size:11px;color:var(--muted)">${k.last_used_at ? 'Dernière utilisation : '+escHtml(k.last_used_at.replace('T',' ').slice(0,16)) : 'Jamais utilisée'}</div>
      <div>
        <span style="display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;${k.is_active ? 'background:rgba(52,211,153,.15);color:var(--ok)' : 'background:rgba(248,113,113,.15);color:var(--danger)'}">
          ${k.is_active ? 'Active' : 'Révoquée'}
        </span>
      </div>
      <div style="display:flex;gap:6px">
        ${k.is_active ? `<button class="btn btn-ghost" style="padding:6px 12px;font-size:12px;border:1px solid var(--border)" onclick="revokeApiKey(${k.id})">Révoquer</button>` : ''}
        <button class="btn btn-ghost" style="padding:6px 12px;font-size:12px;border:1px solid rgba(248,113,113,.4);color:var(--danger)" onclick="deleteApiKey(${k.id})">Supprimer</button>
      </div>
    </div>
  `).join('');
}

async function createApiKey() {
  const name = document.getElementById('ak-name').value.trim();
  if (!name) { showToast('Donnez un nom à cette clé.', 'danger'); return; }
  const res = await fetch('/api/settings/api-keys', {
    method:'POST', credentials:'include',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({name})
  });
  if (!res.ok) { showToast('Erreur lors de la création.', 'danger'); return; }
  const data = await res.json();
  document.getElementById('ak-name').value = '';
  document.getElementById('ak-reveal-value').textContent = data.key;
  document.getElementById('ak-reveal').style.display = 'block';
  showToast('Clé créée. Copiez-la maintenant.', 'success');
  loadApiKeys();
}

function copyApiKey() {
  const val = document.getElementById('ak-reveal-value').textContent;
  navigator.clipboard.writeText(val).then(() => showToast('Clé copiée.', 'success'));
}

async function revokeApiKey(id) {
  if (!confirm('Révoquer cette clé ? Le pont Access ne pourra plus s\'authentifier.')) return;
  const res = await fetch(`/api/settings/api-keys/${id}/revoke`, {method:'PATCH', credentials:'include'});
  if (!res.ok) { showToast('Erreur lors de la révocation.', 'danger'); return; }
  showToast('Clé révoquée.', 'success');
  loadApiKeys();
}

async function deleteApiKey(id) {
  if (!confirm('Supprimer définitivement cette clé ?')) return;
  const res = await fetch(`/api/settings/api-keys/${id}`, {method:'DELETE', credentials:'include'});
  if (!res.ok) { showToast('Erreur lors de la suppression.', 'danger'); return; }
  showToast('Clé supprimée.', 'success');
  loadApiKeys();
}

// Charger les clés quand l'onglet API est ouvert
const _origShowTab = typeof showTab === 'function' ? showTab : null;
// Hooks sur le bouton tab-api
document.getElementById('tab-api')?.addEventListener('click', () => loadApiKeys());
```

#### Étape 3d — S'assurer que l'onglet "api" est géré par `showTab`

Vérifie que la fonction `showTab(name)` dans le script de la page gère bien tous les panneaux de façon générique (en cherchant tous les `.tab-panel` et cachant ceux qui ne correspondent pas). Si elle filtre par liste de noms explicite, ajoute `'api'` à cette liste.

---

## PROMPT 4 — Script exemple pour le pont Access (fichier de documentation)

Crée `scripts/bridge_access_example.py` :

```python
"""
Exemple de script pont Access → MySifa
Lit des enregistrements depuis une base Access (.accdb) et les envoie
à MySifa via l'API bridge.

Dépendances :
  pip install pyodbc requests

Configuration :
  Remplacer ACCESS_DB_PATH et MYSIFA_API_KEY ci-dessous.
"""

import pyodbc
import requests
from datetime import datetime

# ── Configuration ───────────────────────────────────────────────────
ACCESS_DB_PATH = r"C:\Chemin\Vers\VotreBase.accdb"
MYSIFA_BASE_URL = "https://votre-domaine.com"   # ou http://IP:PORT en local
MYSIFA_API_KEY  = "msk_VOTRE_CLE_ICI"

HEADERS = {
    "X-Api-Key": MYSIFA_API_KEY,
    "Content-Type": "application/json",
}

# ── Connexion Access ─────────────────────────────────────────────────
conn_str = (
    r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
    f"DBQ={ACCESS_DB_PATH};"
)

def get_access_rows():
    """Lit les saisies à synchroniser depuis Access."""
    conn = pyodbc.connect(conn_str)
    cur  = conn.cursor()
    # Adapter la requête SQL à la structure réelle de votre base Access
    cur.execute("""
        SELECT operateur, date_operation, code_operation, no_dossier, duree_heures
        FROM saisies_production
        WHERE synchronise = 0
        ORDER BY date_operation ASC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def push_to_mysifa(row):
    """Envoie une saisie vers MySifa."""
    payload = {
        "operateur":       row.operateur,
        "date_operation":  row.date_operation.strftime("%Y-%m-%dT%H:%M:%S") if hasattr(row.date_operation, 'strftime') else str(row.date_operation),
        "operation_code":  str(row.code_operation).zfill(2),
        "no_dossier":      row.no_dossier,
        "duree_heures":    float(row.duree_heures) if row.duree_heures else None,
        "source":          "access_bridge",
    }
    resp = requests.post(
        f"{MYSIFA_BASE_URL}/api/bridge/production",
        json=payload,
        headers=HEADERS,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def main():
    rows = get_access_rows()
    print(f"{len(rows)} enregistrement(s) à synchroniser.")
    ok, dup, err = 0, 0, 0
    for row in rows:
        try:
            result = push_to_mysifa(row)
            if result.get("is_duplicate"):
                dup += 1
            else:
                ok  += 1
        except Exception as e:
            print(f"  Erreur : {e}")
            err += 1
    print(f"Résultat — OK:{ok}  Doublons:{dup}  Erreurs:{err}")


if __name__ == "__main__":
    main()
```

---

## Résumé des fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `app/core/database.py` | Ajouter migration v89 (table `api_keys`) |
| `app/routers/api_bridge.py` | Créer (nouveau router — endpoints pont) |
| `app/routers/settings.py` | Ajouter 4 endpoints de gestion des clés |
| `app/web/settings_page.py` | Ajouter onglet "Clés API" + UI + JS |
| `main.py` | Enregistrer `api_bridge` router |
| `scripts/bridge_access_example.py` | Créer (exemple de script pont) |

## Points d'attention pour Windsurf

1. **Ne jamais modifier `DB_PATH`** ni déplacer `data/production.db`
2. **La clé brute n'est jamais stockée** — seul le SHA-256 est en base (`key_hash`)
3. **`duree_heures` est `REAL`** — toujours `parseFloat()` côté JS, `float()` côté Python
4. **Pas d'emojis** dans les messages, toasts ou labels
5. **Thème light** : tester que la section API reste lisible avec `body.light`
6. Le router bridge utilise `get_db()` importé depuis `app.core.database`, pas depuis `database` (shim racine)

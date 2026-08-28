# MySifa — Tableaux de bord personnalisés — Prompts Windsurf

Donne ces prompts à Windsurf **dans l'ordre**. Attends que chaque étape compile et fonctionne avant de passer à la suivante.

---

## PROMPT 1 — Migration base de données (v87 + v88)

**Fichier cible :** `app/core/database.py`

Ajoute deux nouvelles migrations à la fin de la fonction `_migrate(conn)`, juste avant l'appel `_record_schema_migration(conn, SCHEMA_MIGRATION_VERSION_BASELINE, ...)` (dernière ligne de `_migrate`). La dernière migration existante est la v86.

### Migration v87 — Table `dashboards`

```python
# v87 — Tableaux de bord : référentiel créé par le superadmin
if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=87 LIMIT 1").fetchone():
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS dashboards (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            titre       TEXT NOT NULL,
            description TEXT DEFAULT '',
            widget_type TEXT NOT NULL CHECK(widget_type IN ('stock_alerts','planning_summary','expe_today')),
            config_json TEXT NOT NULL DEFAULT '{}',
            actif       INTEGER NOT NULL DEFAULT 1,
            created_by_id INTEGER REFERENCES users(id),
            created_at  TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
            updated_at  TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime'))
        );
        CREATE INDEX IF NOT EXISTS idx_dashboards_actif ON dashboards(actif);
    """)
    conn.commit()
    _record_schema_migration(conn, 87, "dashboards")
```

### Migration v88 — Table `user_dashboards`

```python
# v88 — Tableaux de bord : association utilisateur ↔ dashboard
if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=88 LIMIT 1").fetchone():
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS user_dashboards (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            dashboard_id INTEGER NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
            pos_x        REAL NOT NULL DEFAULT 20,
            pos_y        REAL NOT NULL DEFAULT 80,
            minimized    INTEGER NOT NULL DEFAULT 0,
            added_at     TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
            UNIQUE(user_id, dashboard_id)
        );
        CREATE INDEX IF NOT EXISTS idx_user_dashboards_user ON user_dashboards(user_id);
    """)
    conn.commit()
    _record_schema_migration(conn, 88, "user_dashboards")
```

**Vérification :** Relance l'app. Les deux tables doivent apparaître dans la base sans erreur. Aucun autre fichier ne doit être modifié dans cette étape.

---

## PROMPT 2 — Backend : router API des dashboards

**Fichier à créer :** `app/routers/dashboards.py`
**Fichier à modifier :** `main.py`

### 2a — Créer `app/routers/dashboards.py`

Ce router expose tous les endpoints REST pour les dashboards. Respecte scrupuleusement les patterns existants du projet : `get_current_user` et `require_superadmin` importés depuis `app.services.auth_service`, `get_db` depuis `app.core.database`. Toutes les routes commencent par `/api/dashboards`.

```python
"""
Router : Tableaux de bord personnalisés (Dashboards).

Endpoints superadmin (CRUD référentiel) :
  GET    /api/dashboards/admin          — liste tous les dashboards
  POST   /api/dashboards/admin          — créer un dashboard
  PATCH  /api/dashboards/admin/{id}     — modifier un dashboard
  DELETE /api/dashboards/admin/{id}     — supprimer un dashboard

Endpoints utilisateur :
  GET    /api/dashboards/me             — mes dashboards actifs (avec données)
  GET    /api/dashboards/available      — dashboards actifs disponibles à ajouter
  POST   /api/dashboards/me/{id}/add    — ajouter un dashboard à mon portail
  DELETE /api/dashboards/me/{id}        — supprimer définitivement de mon portail
  PATCH  /api/dashboards/me/{id}/state  — sauvegarder position / état minimized

Endpoints données widgets :
  GET    /api/dashboards/widget/stock_alerts    — articles sous seuil (matières premières)
  GET    /api/dashboards/widget/planning_summary — résumé planning du jour
  GET    /api/dashboards/widget/expe_today       — départs du jour / lendemain
"""

import json
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.services.auth_service import get_current_user, require_superadmin

router = APIRouter(tags=["dashboards"])


# ─── Modèles Pydantic ────────────────────────────────────────────────────────

class DashboardCreate(BaseModel):
    titre: str
    description: str = ""
    widget_type: str  # 'stock_alerts' | 'planning_summary' | 'expe_today'
    config_json: dict = {}
    actif: bool = True

class DashboardUpdate(BaseModel):
    titre: Optional[str] = None
    description: Optional[str] = None
    config_json: Optional[dict] = None
    actif: Optional[bool] = None

class DashboardStateUpdate(BaseModel):
    pos_x: Optional[float] = None
    pos_y: Optional[float] = None
    minimized: Optional[bool] = None


# ─── SUPERADMIN : CRUD référentiel ───────────────────────────────────────────

@router.get("/api/dashboards/admin")
def admin_list_dashboards(request: Request, user=Depends(require_superadmin)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, titre, description, widget_type, config_json, actif, created_at, updated_at "
            "FROM dashboards ORDER BY id DESC"
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        try:
            d["config_json"] = json.loads(d["config_json"] or "{}")
        except Exception:
            d["config_json"] = {}
        result.append(d)
    return result

@router.post("/api/dashboards/admin")
def admin_create_dashboard(body: DashboardCreate, request: Request, user=Depends(require_superadmin)):
    allowed = {"stock_alerts", "planning_summary", "expe_today"}
    if body.widget_type not in allowed:
        raise HTTPException(400, "widget_type invalide")
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO dashboards (titre, description, widget_type, config_json, actif, created_by_id, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (body.titre, body.description, body.widget_type, json.dumps(body.config_json),
             1 if body.actif else 0, user["id"], now, now)
        )
        conn.commit()
        new_id = cur.lastrowid
    return {"id": new_id, "ok": True}

@router.patch("/api/dashboards/admin/{dashboard_id}")
def admin_update_dashboard(dashboard_id: int, body: DashboardUpdate, request: Request, user=Depends(require_superadmin)):
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    fields, vals = [], []
    if body.titre is not None:
        fields.append("titre=?"); vals.append(body.titre)
    if body.description is not None:
        fields.append("description=?"); vals.append(body.description)
    if body.config_json is not None:
        fields.append("config_json=?"); vals.append(json.dumps(body.config_json))
    if body.actif is not None:
        fields.append("actif=?"); vals.append(1 if body.actif else 0)
    if not fields:
        return {"ok": True}
    fields.append("updated_at=?"); vals.append(now)
    vals.append(dashboard_id)
    with get_db() as conn:
        conn.execute(f"UPDATE dashboards SET {', '.join(fields)} WHERE id=?", vals)
        conn.commit()
    return {"ok": True}

@router.delete("/api/dashboards/admin/{dashboard_id}")
def admin_delete_dashboard(dashboard_id: int, request: Request, user=Depends(require_superadmin)):
    with get_db() as conn:
        conn.execute("DELETE FROM user_dashboards WHERE dashboard_id=?", (dashboard_id,))
        conn.execute("DELETE FROM dashboards WHERE id=?", (dashboard_id,))
        conn.commit()
    return {"ok": True}


# ─── UTILISATEUR : gestion de son portail ────────────────────────────────────

@router.get("/api/dashboards/available")
def list_available_dashboards(request: Request):
    """Retourne tous les dashboards actifs que l'utilisateur peut ajouter à son portail."""
    user = get_current_user(request)
    with get_db() as conn:
        # Dashboards actifs que l'utilisateur n'a PAS encore ajouté
        rows = conn.execute(
            """SELECT d.id, d.titre, d.description, d.widget_type, d.config_json
               FROM dashboards d
               WHERE d.actif = 1
                 AND d.id NOT IN (
                     SELECT dashboard_id FROM user_dashboards WHERE user_id = ?
                 )
               ORDER BY d.id""",
            (user["id"],)
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        try:
            d["config_json"] = json.loads(d["config_json"] or "{}")
        except Exception:
            d["config_json"] = {}
        result.append(d)
    return result

@router.get("/api/dashboards/me")
def list_my_dashboards(request: Request):
    """Retourne les dashboards actifs de l'utilisateur avec leur état (position, minimized)."""
    user = get_current_user(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT d.id, d.titre, d.description, d.widget_type, d.config_json,
                      ud.pos_x, ud.pos_y, ud.minimized
               FROM user_dashboards ud
               JOIN dashboards d ON d.id = ud.dashboard_id
               WHERE ud.user_id = ? AND d.actif = 1
               ORDER BY ud.added_at""",
            (user["id"],)
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        try:
            d["config_json"] = json.loads(d["config_json"] or "{}")
        except Exception:
            d["config_json"] = {}
        result.append(d)
    return result

@router.post("/api/dashboards/me/{dashboard_id}/add")
def add_dashboard_to_portal(dashboard_id: int, request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        exists = conn.execute(
            "SELECT 1 FROM dashboards WHERE id=? AND actif=1", (dashboard_id,)
        ).fetchone()
        if not exists:
            raise HTTPException(404, "Dashboard introuvable ou inactif")
        # Calcule une position décalée pour éviter la superposition
        count = conn.execute(
            "SELECT COUNT(*) FROM user_dashboards WHERE user_id=?", (user["id"],)
        ).fetchone()[0]
        pos_x = 20 + (count * 30)
        pos_y = 80 + (count * 30)
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        conn.execute(
            "INSERT OR IGNORE INTO user_dashboards (user_id, dashboard_id, pos_x, pos_y, added_at) "
            "VALUES (?,?,?,?,?)",
            (user["id"], dashboard_id, pos_x, pos_y, now)
        )
        conn.commit()
    return {"ok": True}

@router.delete("/api/dashboards/me/{dashboard_id}")
def remove_dashboard_from_portal(dashboard_id: int, request: Request):
    """Suppression définitive du dashboard du portail de l'utilisateur."""
    user = get_current_user(request)
    with get_db() as conn:
        conn.execute(
            "DELETE FROM user_dashboards WHERE user_id=? AND dashboard_id=?",
            (user["id"], dashboard_id)
        )
        conn.commit()
    return {"ok": True}

@router.patch("/api/dashboards/me/{dashboard_id}/state")
def update_dashboard_state(dashboard_id: int, body: DashboardStateUpdate, request: Request):
    """Sauvegarde la position et l'état minimized du post-it."""
    user = get_current_user(request)
    fields, vals = [], []
    if body.pos_x is not None:
        fields.append("pos_x=?"); vals.append(body.pos_x)
    if body.pos_y is not None:
        fields.append("pos_y=?"); vals.append(body.pos_y)
    if body.minimized is not None:
        fields.append("minimized=?"); vals.append(1 if body.minimized else 0)
    if not fields:
        return {"ok": True}
    vals.extend([user["id"], dashboard_id])
    with get_db() as conn:
        conn.execute(
            f"UPDATE user_dashboards SET {', '.join(fields)} WHERE user_id=? AND dashboard_id=?",
            vals
        )
        conn.commit()
    return {"ok": True}


# ─── DONNÉES WIDGETS ─────────────────────────────────────────────────────────

@router.get("/api/dashboards/widget/stock_alerts")
def widget_stock_alerts(request: Request, categories: str = ""):
    """
    Retourne les matières premières dont le stock actuel (mp_stock.quantite)
    est inférieur ou égal au seuil d'alerte (matieres_premieres.seuil_alerte).
    Paramètre optionnel : categories — liste séparée par virgules parmi
    mandrin,palette,adhesif,carton. Si vide, retourne toutes les catégories.
    """
    user = get_current_user(request)
    cat_filter = [c.strip() for c in categories.split(",") if c.strip()] if categories else []
    with get_db() as conn:
        base_q = """
            SELECT mp.id, mp.categorie, mp.reference, mp.designation,
                   mp.seuil_alerte, COALESCE(s.quantite, 0) AS quantite_actuelle,
                   mp.seuil_alerte - COALESCE(s.quantite, 0) AS manque
            FROM matieres_premieres mp
            LEFT JOIN mp_stock s ON s.matiere_id = mp.id
            WHERE mp.actif = 1
              AND mp.seuil_alerte > 0
              AND COALESCE(s.quantite, 0) <= mp.seuil_alerte
        """
        params = []
        if cat_filter:
            placeholders = ",".join("?" for _ in cat_filter)
            base_q += f" AND mp.categorie IN ({placeholders})"
            params.extend(cat_filter)
        base_q += " ORDER BY mp.categorie, mp.designation"
        rows = conn.execute(base_q, params).fetchall()
    return [dict(r) for r in rows]

@router.get("/api/dashboards/widget/planning_summary")
def widget_planning_summary(request: Request):
    """
    Résumé du planning du jour et de demain :
    - Nombre de dossiers par statut (attente, en_cours, termine)
    - Machines actives
    """
    user = get_current_user(request)
    today = date.today().isoformat()
    with get_db() as conn:
        # Dossiers dont la date prévue inclut aujourd'hui (approximation : statut en cours ou attente)
        rows = conn.execute(
            """SELECT pe.statut, m.nom as machine, pe.reference, pe.client, pe.duree_heures
               FROM planning_entries pe
               LEFT JOIN machines m ON m.id = pe.machine_id
               WHERE pe.statut IN ('en_cours','attente')
               ORDER BY pe.machine_id, pe.position""",
        ).fetchall()
        en_cours = [dict(r) for r in rows if r["statut"] == "en_cours"]
        attente  = [dict(r) for r in rows if r["statut"] == "attente"]
        termine_today = conn.execute(
            """SELECT COUNT(*) FROM planning_entries
               WHERE statut='termine'
                 AND DATE(updated_at)=?""",
            (today,)
        ).fetchone()[0]
    return {
        "en_cours": en_cours,
        "attente_count": len(attente),
        "termine_today": termine_today,
    }

@router.get("/api/dashboards/widget/expe_today")
def widget_expe_today(request: Request):
    """
    Départs du jour et du lendemain (statut en_attente ou valide).
    """
    user = get_current_user(request)
    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, date_enlevement, client, transporteur, nb_palette,
                      poids_total_kg, statut, ref_sifa
               FROM expe_departs
               WHERE date_enlevement IN (?,?)
                 AND statut IN ('en_attente','valide')
               ORDER BY date_enlevement, id""",
            (today, tomorrow)
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["est_aujourd_hui"] = d["date_enlevement"] == today
        result.append(d)
    return result
```

### 2b — Enregistrer le router dans `main.py`

Ajoute l'import et l'enregistrement du router dashboards dans `main.py`, en suivant exactement le pattern des autres routers.

Dans le bloc d'imports en haut du fichier, ajoute :
```python
from app.routers.dashboards import router as dashboards_router
```

Dans le bloc `app.include_router(...)`, ajoute après le dernier router existant :
```python
app.include_router(dashboards_router)
```

**Vérification :** Relance l'app. Vérifie que `/api/dashboards/me` retourne `[]` pour un utilisateur connecté. Vérifie que `/api/dashboards/admin` retourne `[]` pour le superadmin.

---

## PROMPT 3 — Frontend : post-its flottants sur le portail

**Fichier cible :** `app/web/html.py`

Ce fichier est très long (~11 750 lignes). Lis-le entièrement avant de modifier quoi que ce soit.

### Contexte
Le portail est rendu par la fonction JS `renderPortal()`. Le post-it système existant (`postits`) est une feature différente — ne pas la modifier. On ajoute une couche indépendante de post-its "dashboards".

### 3a — Ajouter les styles CSS

Dans le bloc de styles CSS global (la grande chaîne Python contenant tout le CSS), ajoute les règles suivantes **à la fin du bloc CSS**, avant la fermeture `</style>` :

```css
/* ── Dashboards flottants ─────────────────────────── */
.db-fab{
  position:fixed;bottom:24px;right:24px;z-index:300;
  width:48px;height:48px;border-radius:50%;
  background:var(--accent);border:none;cursor:pointer;
  display:flex;align-items:center;justify-content:center;
  box-shadow:0 4px 16px rgba(34,211,238,.35);
  transition:transform .15s,box-shadow .15s;
}
.db-fab:hover{transform:scale(1.08);box-shadow:0 6px 22px rgba(34,211,238,.45)}
.db-fab svg{color:#000;flex-shrink:0}
.db-fab-badge{
  position:absolute;top:-4px;right:-4px;
  min-width:18px;height:18px;padding:0 5px;
  border-radius:999px;background:var(--danger);
  color:#fff;font-size:10px;font-weight:700;
  display:flex;align-items:center;justify-content:center;
  pointer-events:none;
}
.db-panel{
  position:fixed;z-index:290;
  width:300px;min-height:80px;
  background:var(--card);border:1px solid var(--border);
  border-radius:14px;box-shadow:0 8px 32px rgba(0,0,0,.28);
  display:flex;flex-direction:column;
  transition:opacity .2s,transform .2s;
  overflow:hidden;
}
.db-panel--hidden{opacity:0;pointer-events:none;transform:scale(.96)}
.db-panel-head{
  display:flex;align-items:center;gap:8px;
  padding:10px 12px;cursor:grab;user-select:none;
  border-bottom:1px solid var(--border);
  background:var(--card);
}
.db-panel-head:active{cursor:grabbing}
.db-panel-title{
  flex:1;font-size:13px;font-weight:700;
  color:var(--text);white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis;
}
.db-panel-type{
  font-size:10px;font-weight:600;color:var(--muted);
  text-transform:uppercase;letter-spacing:.5px;flex-shrink:0;
}
.db-panel-btn{
  width:26px;height:26px;border-radius:8px;border:none;
  background:transparent;cursor:pointer;
  display:flex;align-items:center;justify-content:center;
  color:var(--muted);transition:background .12s,color .12s;flex-shrink:0;
}
.db-panel-btn:hover{background:var(--accent-bg);color:var(--accent)}
.db-panel-btn--danger:hover{background:rgba(248,113,113,.12);color:var(--danger)}
.db-panel-body{
  padding:12px;overflow-y:auto;max-height:320px;
  font-size:13px;color:var(--text2);
}
.db-panel--mini .db-panel-body{display:none}
.db-panel--mini .db-panel-head{border-bottom:none}
.db-widget-row{
  display:flex;align-items:center;gap:8px;
  padding:6px 0;border-bottom:1px solid var(--border);
}
.db-widget-row:last-child{border-bottom:none}
.db-widget-badge{
  font-size:11px;font-weight:700;padding:2px 7px;
  border-radius:6px;flex-shrink:0;
}
.db-widget-badge--danger{background:rgba(248,113,113,.15);color:var(--danger)}
.db-widget-badge--warn{background:rgba(251,191,36,.15);color:var(--warn)}
.db-widget-badge--ok{background:rgba(52,211,153,.15);color:var(--success)}
.db-widget-label{flex:1;font-size:12px;color:var(--text2);line-height:1.35}
.db-widget-empty{
  text-align:center;color:var(--muted);font-size:12px;padding:16px 0;
}
.db-add-modal-overlay{
  position:fixed;inset:0;z-index:400;
  background:rgba(0,0,0,.55);backdrop-filter:blur(3px);
  display:flex;align-items:center;justify-content:center;
}
.db-add-modal{
  background:var(--card);border:1px solid var(--border);
  border-radius:16px;width:360px;max-width:92vw;
  box-shadow:0 16px 48px rgba(0,0,0,.4);
  display:flex;flex-direction:column;overflow:hidden;
}
.db-add-modal-head{
  display:flex;align-items:center;justify-content:space-between;
  padding:16px 20px;border-bottom:1px solid var(--border);
}
.db-add-modal-title{font-size:15px;font-weight:700;color:var(--text)}
.db-add-modal-body{padding:16px 20px;display:flex;flex-direction:column;gap:10px}
.db-add-item{
  display:flex;align-items:center;gap:12px;
  padding:10px 12px;border-radius:10px;border:1px solid var(--border);
  cursor:pointer;transition:border-color .12s,background .12s;
}
.db-add-item:hover{border-color:var(--accent);background:var(--accent-bg)}
.db-add-item-icon{
  width:36px;height:36px;border-radius:10px;
  background:var(--accent-bg);display:flex;align-items:center;justify-content:center;
  flex-shrink:0;
}
.db-add-item-name{font-size:13px;font-weight:700;color:var(--text)}
.db-add-item-desc{font-size:11px;color:var(--muted);margin-top:2px}
.db-add-empty{text-align:center;color:var(--muted);font-size:13px;padding:16px 0}
```

### 3b — Ajouter le JavaScript

Dans le bloc JavaScript global (avant la fermeture `</script>`), ajoute le bloc suivant. Place-le **après** les fonctions du portail existantes (`attachPortalReorder`, etc.) et **avant** le code d'initialisation de l'app (`initApp()` ou équivalent).

```javascript
// ══════════════════════════════════════════════════════
// DASHBOARDS FLOTTANTS — Post-its personnalisés
// ══════════════════════════════════════════════════════

const DB = {
  panels: {},        // dashboard_id → { el, data, dragging }
  visible: true,     // tous visibles ou tous cachés
  fabEl: null,
  badgeEl: null,
};

// Labels lisibles pour les types de widgets
const DB_WIDGET_LABELS = {
  stock_alerts:     'Stocks',
  planning_summary: 'Planning',
  expe_today:       'Expéditions',
};

// Icône SVG selon le type de widget (inline, taille 18px)
function dbWidgetIcon(type) {
  const icons = {
    stock_alerts:     '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>',
    planning_summary: '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>',
    expe_today:       '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="1" y="3" width="15" height="13"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/></svg>',
  };
  return icons[type] || '';
}

// ── Initialisation ─────────────────────────────────────

async function dbInit() {
  let dashboards = [];
  try {
    const r = await fetch('/api/dashboards/me', { credentials: 'include' });
    if (r.ok) dashboards = await r.json();
  } catch(e) { return; }

  if (!dashboards.length) return;

  // Créer le bouton FAB
  dbCreateFab(dashboards.length);

  // Créer un panel pour chaque dashboard
  dashboards.forEach(d => dbCreatePanel(d));
}

function dbCreateFab(count) {
  const fab = document.createElement('button');
  fab.className = 'db-fab';
  fab.title = 'Mes tableaux de bord';
  fab.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>';

  const badge = document.createElement('span');
  badge.className = 'db-fab-badge';
  badge.textContent = count;
  fab.appendChild(badge);
  DB.badgeEl = badge;

  // Bouton + (ajouter un dashboard)
  const fabAdd = document.createElement('button');
  fabAdd.className = 'db-fab';
  fabAdd.style.cssText = 'bottom:80px;right:24px;width:38px;height:38px;background:var(--card);border:1px solid var(--border);box-shadow:0 2px 8px rgba(0,0,0,.2)';
  fabAdd.title = 'Ajouter un tableau de bord';
  fabAdd.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>';
  fabAdd.addEventListener('click', (e) => { e.stopPropagation(); dbOpenAddModal(); });

  fab.addEventListener('click', dbToggleAll);

  document.body.appendChild(fab);
  document.body.appendChild(fabAdd);
  DB.fabEl = fab;
  DB.fabAddEl = fabAdd;
}

function dbUpdateBadge() {
  if (!DB.badgeEl) return;
  const count = Object.keys(DB.panels).length;
  DB.badgeEl.textContent = count;
}

// ── Création d'un panel ───────────────────────────────

function dbCreatePanel(data) {
  const id = data.id;
  const panel = document.createElement('div');
  panel.className = 'db-panel';
  panel.style.cssText = `left:${data.pos_x}px;top:${data.pos_y}px`;
  panel.dataset.dbId = id;

  // En-tête
  const head = document.createElement('div');
  head.className = 'db-panel-head';

  const iconWrap = document.createElement('span');
  iconWrap.innerHTML = dbWidgetIcon(data.widget_type);
  iconWrap.style.cssText = 'color:var(--accent);display:flex;flex-shrink:0';

  const title = document.createElement('span');
  title.className = 'db-panel-title';
  title.textContent = data.titre;

  const typeLabel = document.createElement('span');
  typeLabel.className = 'db-panel-type';
  typeLabel.textContent = DB_WIDGET_LABELS[data.widget_type] || data.widget_type;

  // Bouton minimiser
  const btnMini = document.createElement('button');
  btnMini.className = 'db-panel-btn';
  btnMini.title = data.minimized ? 'Développer' : 'Réduire';
  btnMini.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"/></svg>';
  btnMini.addEventListener('click', (e) => { e.stopPropagation(); dbToggleMini(id, btnMini); });

  // Bouton fermer (désactiver définitivement)
  const btnClose = document.createElement('button');
  btnClose.className = 'db-panel-btn db-panel-btn--danger';
  btnClose.title = 'Désactiver ce tableau de bord';
  btnClose.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
  btnClose.addEventListener('click', (e) => { e.stopPropagation(); dbRemovePanel(id); });

  head.appendChild(iconWrap);
  head.appendChild(title);
  head.appendChild(typeLabel);
  head.appendChild(btnMini);
  head.appendChild(btnClose);

  // Corps
  const body = document.createElement('div');
  body.className = 'db-panel-body';
  body.innerHTML = '<div class="db-widget-empty">Chargement…</div>';

  panel.appendChild(head);
  panel.appendChild(body);
  document.body.appendChild(panel);

  // État minimized
  if (data.minimized) {
    panel.classList.add('db-panel--mini');
    btnMini.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>';
  }

  DB.panels[id] = { el: panel, data, btnMini };

  // Drag
  dbAttachDrag(panel, head, id);

  // Charger les données du widget
  dbLoadWidget(id, data.widget_type, data.config_json, body);
}

// ── Drag & drop ───────────────────────────────────────

function dbAttachDrag(panel, handle, id) {
  let startX, startY, startLeft, startTop, dragging = false;

  function onMouseDown(e) {
    if (e.target.closest('.db-panel-btn')) return;
    e.preventDefault();
    dragging = true;
    startX = e.clientX;
    startY = e.clientY;
    const r = panel.getBoundingClientRect();
    startLeft = r.left;
    startTop = r.top;
    panel.style.transition = 'none';
    panel.style.zIndex = 350;
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  }

  function onMouseMove(e) {
    if (!dragging) return;
    const dx = e.clientX - startX;
    const dy = e.clientY - startY;
    const newX = Math.max(0, Math.min(window.innerWidth - 310, startLeft + dx));
    const newY = Math.max(0, Math.min(window.innerHeight - 60, startTop + dy));
    panel.style.left = newX + 'px';
    panel.style.top  = newY + 'px';
  }

  function onMouseUp(e) {
    if (!dragging) return;
    dragging = false;
    panel.style.transition = '';
    panel.style.zIndex = 290;
    const r = panel.getBoundingClientRect();
    window.removeEventListener('mousemove', onMouseMove);
    window.removeEventListener('mouseup', onMouseUp);
    // Sauvegarder la position
    fetch(`/api/dashboards/me/${id}/state`, {
      method: 'PATCH', credentials: 'include',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ pos_x: r.left, pos_y: r.top }),
    }).catch(() => {});
  }

  handle.addEventListener('mousedown', onMouseDown);

  // Touch support
  handle.addEventListener('touchstart', (e) => {
    if (e.target.closest('.db-panel-btn')) return;
    const t = e.touches[0];
    startX = t.clientX; startY = t.clientY;
    const r = panel.getBoundingClientRect();
    startLeft = r.left; startTop = r.top;
    panel.style.transition = 'none';
  }, { passive: true });
  handle.addEventListener('touchmove', (e) => {
    const t = e.touches[0];
    const dx = t.clientX - startX; const dy = t.clientY - startY;
    const newX = Math.max(0, Math.min(window.innerWidth - 310, startLeft + dx));
    const newY = Math.max(0, Math.min(window.innerHeight - 60, startTop + dy));
    panel.style.left = newX + 'px'; panel.style.top = newY + 'px';
    e.preventDefault();
  }, { passive: false });
  handle.addEventListener('touchend', () => {
    panel.style.transition = '';
    const r = panel.getBoundingClientRect();
    fetch(`/api/dashboards/me/${id}/state`, {
      method: 'PATCH', credentials: 'include',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ pos_x: r.left, pos_y: r.top }),
    }).catch(() => {});
  });
}

// ── Minimiser / développer ────────────────────────────

function dbToggleMini(id, btnMini) {
  const p = DB.panels[id];
  if (!p) return;
  const isMini = p.el.classList.toggle('db-panel--mini');
  btnMini.title = isMini ? 'Développer' : 'Réduire';
  const arrowUp = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"/></svg>';
  const arrowDn = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>';
  btnMini.innerHTML = isMini ? arrowDn : arrowUp;
  fetch(`/api/dashboards/me/${id}/state`, {
    method: 'PATCH', credentials: 'include',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ minimized: isMini }),
  }).catch(() => {});
}

// ── Afficher / cacher tous les panels ─────────────────

function dbToggleAll() {
  DB.visible = !DB.visible;
  Object.values(DB.panels).forEach(p => {
    p.el.classList.toggle('db-panel--hidden', !DB.visible);
  });
  if (DB.fabAddEl) DB.fabAddEl.style.display = DB.visible ? '' : 'none';
}

// ── Supprimer définitivement un panel ─────────────────

async function dbRemovePanel(id) {
  const p = DB.panels[id];
  if (!p) return;
  // Animation de sortie
  p.el.classList.add('db-panel--hidden');
  await new Promise(r => setTimeout(r, 200));
  p.el.remove();
  delete DB.panels[id];
  dbUpdateBadge();
  // Masquer le FAB si plus aucun panel
  if (Object.keys(DB.panels).length === 0 && DB.fabEl) {
    DB.fabEl.style.display = 'none';
    if (DB.fabAddEl) DB.fabAddEl.style.display = 'none';
  }
  // Appel API
  fetch(`/api/dashboards/me/${id}`, { method: 'DELETE', credentials: 'include' }).catch(() => {});
}

// ── Chargement des données du widget ──────────────────

async function dbLoadWidget(id, widgetType, config, bodyEl) {
  try {
    let url = `/api/dashboards/widget/${widgetType}`;
    if (widgetType === 'stock_alerts' && config && config.categories && config.categories.length) {
      url += '?categories=' + encodeURIComponent(config.categories.join(','));
    }
    const r = await fetch(url, { credentials: 'include' });
    if (!r.ok) { bodyEl.innerHTML = '<div class="db-widget-empty">Erreur de chargement.</div>'; return; }
    const data = await r.json();
    bodyEl.innerHTML = dbRenderWidget(widgetType, data);
  } catch(e) {
    bodyEl.innerHTML = '<div class="db-widget-empty">Erreur réseau.</div>';
  }
}

function dbRenderWidget(type, data) {
  if (type === 'stock_alerts') {
    if (!data.length) return '<div class="db-widget-empty">Aucun article sous le seuil d\'alerte.</div>';
    return data.map(item => {
      const pct = item.seuil_alerte > 0 ? Math.round((item.quantite_actuelle / item.seuil_alerte) * 100) : 0;
      const cls = pct === 0 ? 'danger' : pct < 50 ? 'warn' : 'ok';
      const cat = { mandrin: 'Mandrin', palette: 'Palette', adhesif: 'Adhésif', carton: 'Carton' }[item.categorie] || item.categorie;
      return `<div class="db-widget-row">
        <span class="db-widget-badge db-widget-badge--${cls}">${cat}</span>
        <span class="db-widget-label">${escHtml(item.designation)}<br><span style="font-size:11px;color:var(--muted)">Stock : ${item.quantite_actuelle} / seuil : ${item.seuil_alerte}</span></span>
      </div>`;
    }).join('');
  }

  if (type === 'planning_summary') {
    const { en_cours, attente_count, termine_today } = data;
    if (!en_cours.length && !attente_count && !termine_today) {
      return '<div class="db-widget-empty">Aucun dossier en cours.</div>';
    }
    let html = '';
    en_cours.forEach(d => {
      html += `<div class="db-widget-row">
        <span class="db-widget-badge db-widget-badge--ok">En cours</span>
        <span class="db-widget-label">${escHtml(d.reference)} — ${escHtml(d.machine || '')}<br><span style="font-size:11px;color:var(--muted)">${escHtml(d.client || '')}</span></span>
      </div>`;
    });
    if (attente_count) {
      html += `<div class="db-widget-row">
        <span class="db-widget-badge db-widget-badge--warn">Attente</span>
        <span class="db-widget-label">${attente_count} dossier${attente_count > 1 ? 's' : ''} en attente</span>
      </div>`;
    }
    if (termine_today) {
      html += `<div class="db-widget-row">
        <span class="db-widget-badge db-widget-badge--ok">Terminé</span>
        <span class="db-widget-label">${termine_today} dossier${termine_today > 1 ? 's' : ''} terminé${termine_today > 1 ? 's' : ''} aujourd'hui</span>
      </div>`;
    }
    return html;
  }

  if (type === 'expe_today') {
    if (!data.length) return '<div class="db-widget-empty">Aucun départ prévu aujourd\'hui ni demain.</div>';
    return data.map(d => {
      const label = d.est_aujourd_hui ? "Aujourd'hui" : "Demain";
      const cls = d.est_aujourd_hui ? 'danger' : 'warn';
      return `<div class="db-widget-row">
        <span class="db-widget-badge db-widget-badge--${cls}">${label}</span>
        <span class="db-widget-label">${escHtml(d.client || '—')}<br><span style="font-size:11px;color:var(--muted)">${escHtml(d.transporteur || '')} · ${d.nb_palette || 0} pal. · ${d.poids_total_kg || 0} kg</span></span>
      </div>`;
    }).join('');
  }

  return '<div class="db-widget-empty">Type de widget non reconnu.</div>';
}

// ── Modal "Ajouter un tableau de bord" ────────────────

async function dbOpenAddModal() {
  let available = [];
  try {
    const r = await fetch('/api/dashboards/available', { credentials: 'include' });
    if (r.ok) available = await r.json();
  } catch(e) {}

  const overlay = document.createElement('div');
  overlay.className = 'db-add-modal-overlay';
  overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });

  const modal = document.createElement('div');
  modal.className = 'db-add-modal';

  const head = document.createElement('div');
  head.className = 'db-add-modal-head';
  head.innerHTML = `<span class="db-add-modal-title">Ajouter un tableau de bord</span>`;
  const btnCloseModal = document.createElement('button');
  btnCloseModal.className = 'db-panel-btn';
  btnCloseModal.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
  btnCloseModal.addEventListener('click', () => overlay.remove());
  head.appendChild(btnCloseModal);

  const body = document.createElement('div');
  body.className = 'db-add-modal-body';

  if (!available.length) {
    body.innerHTML = '<div class="db-add-empty">Tous les tableaux de bord disponibles sont déjà sur votre portail.</div>';
  } else {
    available.forEach(d => {
      const item = document.createElement('div');
      item.className = 'db-add-item';
      item.innerHTML = `
        <div class="db-add-item-icon" style="color:var(--accent)">${dbWidgetIcon(d.widget_type)}</div>
        <div>
          <div class="db-add-item-name">${escHtml(d.titre)}</div>
          <div class="db-add-item-desc">${escHtml(d.description || DB_WIDGET_LABELS[d.widget_type] || '')}</div>
        </div>`;
      item.addEventListener('click', async () => {
        item.style.opacity = '0.5';
        try {
          const r = await fetch(`/api/dashboards/me/${d.id}/add`, {
            method: 'POST', credentials: 'include',
          });
          if (r.ok) {
            overlay.remove();
            // Recharger les dashboards et recréer le panel
            const r2 = await fetch('/api/dashboards/me', { credentials: 'include' });
            const all = await r2.json();
            const newD = all.find(x => x.id === d.id);
            if (newD) {
              dbCreatePanel(newD);
              dbUpdateBadge();
              if (DB.fabEl) DB.fabEl.style.display = '';
              if (DB.fabAddEl) DB.fabAddEl.style.display = '';
            }
            showToast('Tableau de bord ajouté.', 'success');
          } else {
            showToast('Erreur lors de l\'ajout.', 'danger');
          }
        } catch(e) {
          showToast('Erreur réseau.', 'danger');
        }
      });
      body.appendChild(item);
    });
  }

  modal.appendChild(head);
  modal.appendChild(body);
  overlay.appendChild(modal);
  document.body.appendChild(overlay);
}
```

### 3c — Appeler `dbInit()` au chargement du portail

Dans la fonction `renderPortal()` (vers la ligne 3731), **à la fin**, après `setTimeout(()=>{if(apps.length)attachPortalReorder(appsWrap);},0);`, ajoute :

```javascript
// Initialiser les dashboards flottants (post-its)
setTimeout(() => { if (typeof dbInit === 'function') dbInit(); }, 100);
```

**Vérification :**
1. Connecte-toi sur le portail — sans dashboards assignés, aucun FAB ne doit apparaître.
2. Ajoute-toi un dashboard via l'API (POST `/api/dashboards/me/{id}/add`), recharge — le FAB doit apparaître.
3. Le post-it doit être draggable, minimisable, et sa position doit persister après rechargement.

---

## PROMPT 4 — Frontend Settings : builder de dashboards (superadmin)

**Fichier cible :** `app/web/settings_page.py`

### Contexte
La page Settings (`/settings`) est rendue depuis `app/web/settings_page.py`. Elle contient plusieurs onglets (comptes, rôles, annonces, etc.). Ajoute un nouvel onglet **"Tableaux de bord"** visible uniquement pour le superadmin.

### 4a — Ajouter l'onglet dans la barre de navigation des settings

Repère le bloc qui génère les onglets de la page settings (boutons de navigation d'onglets, souvent sous forme de `tab-btn` ou équivalent). Ajoute un onglet "Tableaux de bord" avec l'icône grille, visible uniquement si `S.user.role === 'superadmin'`.

```javascript
// Dans le rendu des onglets settings, ajouter (après les onglets existants) :
if(isSuper){
  tabs.push({id:'dashboards', label:'Tableaux de bord', icon:'grid'});
}
```

### 4b — Ajouter le contenu de l'onglet

Ajoute une fonction `renderSettingsDashboards()` dans le JS de la page settings. Voici le code complet de cette fonction :

```javascript
async function renderSettingsDashboards() {
  const root = document.getElementById('settings-tab-content');
  if (!root) return;
  root.innerHTML = '<div style="padding:20px;color:var(--muted);font-size:13px">Chargement…</div>';

  let dashboards = [];
  try {
    const r = await fetch('/api/dashboards/admin', { credentials: 'include' });
    if (r.ok) dashboards = await r.json();
  } catch(e) {}

  const WIDGET_TYPES = [
    { value: 'stock_alerts',     label: 'Alertes stock matières premières' },
    { value: 'planning_summary', label: 'Résumé planning production' },
    { value: 'expe_today',       label: 'Départs expédition du jour' },
  ];
  const CATEGORIES_MP = ['mandrin','palette','adhesif','carton'];

  function renderList() {
    const listEl = document.createElement('div');
    listEl.style.cssText = 'display:flex;flex-direction:column;gap:10px;margin-top:16px';

    if (!dashboards.length) {
      listEl.innerHTML = '<div style="color:var(--muted);font-size:13px;text-align:center;padding:24px 0">Aucun tableau de bord créé.</div>';
    } else {
      dashboards.forEach(d => {
        const card = document.createElement('div');
        card.style.cssText = 'background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px 16px;display:flex;align-items:center;gap:12px';

        const typeInfo = WIDGET_TYPES.find(t => t.value === d.widget_type) || { label: d.widget_type };
        const statusBadge = d.actif
          ? '<span style="font-size:11px;font-weight:700;padding:2px 8px;border-radius:6px;background:rgba(52,211,153,.15);color:var(--success)">Actif</span>'
          : '<span style="font-size:11px;font-weight:700;padding:2px 8px;border-radius:6px;background:var(--accent-bg);color:var(--muted)">Inactif</span>';

        card.innerHTML = `
          <div style="flex:1;min-width:0">
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
              <span style="font-size:14px;font-weight:700;color:var(--text)">${escHtml(d.titre)}</span>
              ${statusBadge}
            </div>
            <div style="font-size:12px;color:var(--muted);margin-top:4px">${escHtml(typeInfo.label)}</div>
            ${d.description ? `<div style="font-size:12px;color:var(--text2);margin-top:2px">${escHtml(d.description)}</div>` : ''}
          </div>
          <div style="display:flex;gap:8px;flex-shrink:0">
            <button class="btn btn-ghost" style="padding:6px 12px;font-size:12px" data-edit="${d.id}">Modifier</button>
            <button class="btn btn-ghost" style="padding:6px 12px;font-size:12px;color:var(--danger)" data-del="${d.id}">Supprimer</button>
          </div>`;

        card.querySelector('[data-edit]').addEventListener('click', () => openDashboardModal(d));
        card.querySelector('[data-del]').addEventListener('click', () => deleteDashboard(d.id, d.titre));
        listEl.appendChild(card);
      });
    }
    return listEl;
  }

  async function deleteDashboard(id, titre) {
    if (!confirm(`Supprimer le tableau de bord "${titre}" ? Il sera retiré du portail de tous les utilisateurs.`)) return;
    try {
      const r = await fetch(`/api/dashboards/admin/${id}`, { method: 'DELETE', credentials: 'include' });
      if (r.ok) {
        dashboards = dashboards.filter(d => d.id !== id);
        rebuildPage();
        showToast('Tableau de bord supprimé.', 'success');
      } else {
        showToast('Erreur lors de la suppression.', 'danger');
      }
    } catch(e) { showToast('Erreur réseau.', 'danger'); }
  }

  function openDashboardModal(existing) {
    const isEdit = !!existing;
    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;inset:0;z-index:400;background:rgba(0,0,0,.55);backdrop-filter:blur(3px);display:flex;align-items:center;justify-content:center';
    overlay.addEventListener('click', e => { if(e.target===overlay) overlay.remove(); });

    const modal = document.createElement('div');
    modal.style.cssText = 'background:var(--card);border:1px solid var(--border);border-radius:16px;width:420px;max-width:92vw;box-shadow:0 16px 48px rgba(0,0,0,.4);display:flex;flex-direction:column;overflow:hidden';

    const head = document.createElement('div');
    head.style.cssText = 'display:flex;align-items:center;justify-content:space-between;padding:16px 20px;border-bottom:1px solid var(--border)';
    head.innerHTML = `<span style="font-size:15px;font-weight:700;color:var(--text)">${isEdit ? 'Modifier' : 'Nouveau tableau de bord'}</span>`;
    const btnX = document.createElement('button');
    btnX.className = 'db-panel-btn';
    btnX.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
    btnX.addEventListener('click', () => overlay.remove());
    head.appendChild(btnX);

    const body = document.createElement('div');
    body.style.cssText = 'padding:20px;display:flex;flex-direction:column;gap:14px';

    // Champ titre
    const fTitre = document.createElement('div');
    fTitre.innerHTML = `<label style="font-size:12px;font-weight:600;color:var(--text);text-transform:uppercase;letter-spacing:.5px;display:block;margin-bottom:6px">Titre</label>
      <input id="db-f-titre" type="text" placeholder="Ex: Stocks à réapprovisionner" value="${escAttr(existing?.titre||'')}" style="width:100%;box-sizing:border-box;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px 14px;color:var(--text);font-size:14px">`;

    // Champ description
    const fDesc = document.createElement('div');
    fDesc.innerHTML = `<label style="font-size:12px;font-weight:600;color:var(--text);text-transform:uppercase;letter-spacing:.5px;display:block;margin-bottom:6px">Description <span style="color:var(--muted);font-weight:400">(optionnel)</span></label>
      <input id="db-f-desc" type="text" placeholder="Ex: Mandrins, cartons, palettes et adhésif" value="${escAttr(existing?.description||'')}" style="width:100%;box-sizing:border-box;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px 14px;color:var(--text);font-size:14px">`;

    // Champ type (désactivé en édition)
    const fType = document.createElement('div');
    const typeOpts = WIDGET_TYPES.map(t =>
      `<option value="${t.value}" ${(existing?.widget_type===t.value||(!existing&&t.value==='stock_alerts'))?'selected':''}>${t.label}</option>`
    ).join('');
    fType.innerHTML = `<label style="font-size:12px;font-weight:600;color:var(--text);text-transform:uppercase;letter-spacing:.5px;display:block;margin-bottom:6px">Type de widget</label>
      <select id="db-f-type" ${isEdit?'disabled':''} style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px 14px;color:var(--text);font-size:14px">${typeOpts}</select>
      ${isEdit?'<div style="font-size:11px;color:var(--muted);margin-top:4px">Le type ne peut pas être modifié après création.</div>':''}`;

    // Config dynamique selon le type (stock_alerts → catégories)
    const fConfig = document.createElement('div');
    fConfig.id = 'db-f-config';

    function renderConfigFields(type, currentConfig) {
      fConfig.innerHTML = '';
      if (type === 'stock_alerts') {
        const cats = currentConfig?.categories || [];
        fConfig.innerHTML = `<div>
          <label style="font-size:12px;font-weight:600;color:var(--text);text-transform:uppercase;letter-spacing:.5px;display:block;margin-bottom:8px">Catégories affichées</label>
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            ${CATEGORIES_MP.map(c => `
              <label style="display:flex;align-items:center;gap:6px;font-size:13px;color:var(--text2);cursor:pointer;padding:6px 10px;border-radius:8px;border:1px solid var(--border);background:var(--bg)">
                <input type="checkbox" value="${c}" ${cats.includes(c)||!cats.length?'checked':''} style="accent-color:var(--accent)">
                ${c.charAt(0).toUpperCase()+c.slice(1)}
              </label>`).join('')}
          </div>
          <div style="font-size:11px;color:var(--muted);margin-top:6px">Si aucune sélectionnée, toutes les catégories sont affichées.</div>
        </div>`;
      }
      // Pour planning_summary et expe_today : pas de config supplémentaire pour l'instant
    }

    const initType = existing?.widget_type || 'stock_alerts';
    renderConfigFields(initType, existing?.config_json || {});

    fType.querySelector('select')?.addEventListener('change', (e) => {
      renderConfigFields(e.target.value, {});
    });

    // Champ actif
    const fActif = document.createElement('div');
    fActif.innerHTML = `<label style="display:flex;align-items:center;gap:10px;cursor:pointer;font-size:13px;color:var(--text2)">
      <input id="db-f-actif" type="checkbox" ${(existing?.actif!==false)?'checked':''} style="accent-color:var(--accent);width:16px;height:16px">
      Dashboard actif (visible par les utilisateurs)
    </label>`;

    // Bouton soumettre
    const footer = document.createElement('div');
    footer.style.cssText = 'padding:0 20px 20px;display:flex;justify-content:flex-end;gap:10px';
    const btnCancel = document.createElement('button');
    btnCancel.className = 'btn btn-ghost';
    btnCancel.textContent = 'Annuler';
    btnCancel.addEventListener('click', () => overlay.remove());

    const btnSave = document.createElement('button');
    btnSave.className = 'btn btn-accent';
    btnSave.textContent = isEdit ? 'Enregistrer' : 'Créer';
    btnSave.addEventListener('click', async () => {
      const titre = document.getElementById('db-f-titre')?.value?.trim();
      if (!titre) { showToast('Le titre est requis.', 'danger'); return; }
      const widget_type = document.getElementById('db-f-type')?.value || initType;
      const desc = document.getElementById('db-f-desc')?.value?.trim() || '';
      const actif = document.getElementById('db-f-actif')?.checked !== false;

      // Collecter config
      let config_json = {};
      if (widget_type === 'stock_alerts') {
        const checked = [...document.querySelectorAll('#db-f-config input[type=checkbox]:checked')].map(el => el.value);
        if (checked.length && checked.length < CATEGORIES_MP.length) {
          config_json.categories = checked;
        }
      }

      btnSave.disabled = true;
      btnSave.textContent = isEdit ? 'Enregistrement…' : 'Création…';

      try {
        let r;
        if (isEdit) {
          r = await fetch(`/api/dashboards/admin/${existing.id}`, {
            method: 'PATCH', credentials: 'include',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ titre, description: desc, config_json, actif }),
          });
        } else {
          r = await fetch('/api/dashboards/admin', {
            method: 'POST', credentials: 'include',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ titre, description: desc, widget_type, config_json, actif }),
          });
        }
        if (r.ok) {
          overlay.remove();
          // Recharger la liste
          const r2 = await fetch('/api/dashboards/admin', { credentials: 'include' });
          if (r2.ok) dashboards = await r2.json();
          rebuildPage();
          showToast(isEdit ? 'Tableau de bord modifié.' : 'Tableau de bord créé.', 'success');
        } else {
          const err = await r.json().catch(() => ({}));
          showToast(err.detail || 'Erreur lors de la sauvegarde.', 'danger');
          btnSave.disabled = false;
          btnSave.textContent = isEdit ? 'Enregistrer' : 'Créer';
        }
      } catch(e) {
        showToast('Erreur réseau.', 'danger');
        btnSave.disabled = false;
        btnSave.textContent = isEdit ? 'Enregistrer' : 'Créer';
      }
    });

    body.appendChild(fTitre);
    body.appendChild(fDesc);
    body.appendChild(fType);
    body.appendChild(fConfig);
    body.appendChild(fActif);
    footer.appendChild(btnCancel);
    footer.appendChild(btnSave);
    modal.appendChild(head);
    modal.appendChild(body);
    modal.appendChild(footer);
    overlay.appendChild(modal);
    document.body.appendChild(overlay);
    requestAnimationFrame(() => document.getElementById('db-f-titre')?.focus());
  }

  function rebuildPage() {
    root.innerHTML = '';
    buildPage();
  }

  function buildPage() {
    const wrap = document.createElement('div');
    wrap.style.cssText = 'max-width:760px;margin:0 auto;padding:0 0 40px';

    const topRow = document.createElement('div');
    topRow.style.cssText = 'display:flex;align-items:center;justify-content:space-between;margin-bottom:4px';
    const h = document.createElement('div');
    h.innerHTML = '<div style="font-size:16px;font-weight:700;color:var(--text)">Tableaux de bord</div><div style="font-size:13px;color:var(--muted);margin-top:4px">Créez des tableaux de bord que les utilisateurs peuvent ajouter à leur portail.</div>';
    const btnNew = document.createElement('button');
    btnNew.className = 'btn btn-accent';
    btnNew.innerHTML = '+ Nouveau';
    btnNew.style.cssText = 'flex-shrink:0;padding:8px 16px;font-size:13px';
    btnNew.addEventListener('click', () => openDashboardModal(null));
    topRow.appendChild(h);
    topRow.appendChild(btnNew);
    wrap.appendChild(topRow);
    wrap.appendChild(renderList());
    root.appendChild(wrap);
  }

  buildPage();
}
```

### 4c — Appeler la fonction lors de l'activation de l'onglet

Dans le gestionnaire de changement d'onglet de la page settings (là où `renderSettings*` est appelé selon l'onglet actif), ajoute :

```javascript
case 'dashboards':
  renderSettingsDashboards();
  break;
```

**Vérification :**
1. En tant que superadmin, va dans `Paramètres` → onglet "Tableaux de bord".
2. Crée un dashboard de type "Alertes stock matières premières" avec le titre "Stocks à réapprovisionner".
3. Connecte-toi avec un autre compte, va sur le portail, clique sur le bouton "+" flottant.
4. Le dashboard doit apparaître dans la liste "Ajouter un tableau de bord".
5. Clique "Ajouter" — le post-it apparaît sur le portail avec les vraies données de stock.
6. Drag & drop — la position persiste après rechargement.
7. Bouton X (rouge) — le dashboard disparaît définitivement du portail.

---

## Notes d'intégration inter-prompts

- Les fonctions `escHtml()`, `escAttr()`, et `showToast()` sont déjà disponibles globalement dans `html.py` — ne pas les redéfinir.
- L'objet `S` (état central) ne doit pas être modifié pour les dashboards — tout l'état des panels est dans l'objet `DB`.
- Le style CSS utilise exclusivement les variables CSS de MySifa (`--bg`, `--card`, `--border`, `--text`, `--accent`, `--danger`, `--warn`, `--success`, `--muted`).
- Sur mobile (viewport < 768px), les panels se positionnent dans les 20 premières pixels du bas — le drag fonctionne en touch.

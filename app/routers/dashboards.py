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

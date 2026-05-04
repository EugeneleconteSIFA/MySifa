"""MySifa — Planning RH (Personnel) — API v1.0

Routes /api/rh/*
Lecture  : fabrication, logistique, direction, superadmin
Écriture : direction, superadmin (configurateurs)
"""
from datetime import datetime, date, timedelta
from typing import Optional

from fastapi import APIRouter, Request, HTTPException

from database import get_db
from app.services.auth_service import get_current_user
from config import ROLES_PLANNING_RH_VIEW, ROLES_PLANNING_RH_EDIT

router = APIRouter(prefix="/api/rh", tags=["planning_rh"])


# ── Helpers accès ────────────────────────────────────────────────
def _require_view(request: Request) -> dict:
    user = get_current_user(request)
    # Check role OR planning_rh override
    has_override = False
    overrides_raw = user.get("access_overrides")
    if overrides_raw:
        try:
            import json
            overrides = json.loads(overrides_raw) if isinstance(overrides_raw, str) else overrides_raw
            has_override = overrides.get("planning_rh") is True
        except:
            pass
    if user.get("role") not in ROLES_PLANNING_RH_VIEW and not has_override:
        raise HTTPException(403, "Accès non autorisé au planning RH")
    return user


def _require_edit(request: Request) -> dict:
    user = get_current_user(request)
    # Check role OR planning_rh override
    has_override = False
    overrides_raw = user.get("access_overrides")
    if overrides_raw:
        try:
            import json
            overrides = json.loads(overrides_raw) if isinstance(overrides_raw, str) else overrides_raw
            has_override = overrides.get("planning_rh") is True
        except:
            pass
    if user.get("role") not in ROLES_PLANNING_RH_EDIT and not has_override:
        raise HTTPException(403, "Modification réservée aux configurateurs (direction / superadmin)")
    return user


def _week_bounds(semaine: str):
    """Retourne (lundi, dimanche) pour une semaine '2026-W17'."""
    try:
        year_str, w_str = semaine.split("-W")
        monday = date.fromisocalendar(int(year_str), int(w_str), 1)
        sunday = monday + timedelta(days=6)
        return monday, sunday
    except (ValueError, AttributeError):
        raise HTTPException(400, f"Format de semaine invalide : '{semaine}' (attendu YYYY-WNN)")


# ── Personnel planifiable ────────────────────────────────────────
@router.get("/personnel")
def get_personnel(request: Request):
    _require_view(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, nom, email, role, machine_id, actif
               FROM users
               WHERE (role IN ('fabrication','logistique') OR email = 'mlesaffre@sifa.pro') AND actif = 1
               ORDER BY nom COLLATE NOCASE"""
        ).fetchall()
    return {"personnel": [dict(r) for r in rows]}


# ── Planning : affectations hebdomadaires ────────────────────────
@router.get("/planning")
def get_planning(
    request: Request,
    from_week: Optional[str] = None,
    to_week: Optional[str] = None,
):
    user = _require_view(request)
    role = user.get("role")

    with get_db() as conn:
        q = """
            SELECT p.id, p.user_id, u.nom AS user_nom, u.role AS user_role,
                   p.semaine, p.machine_id,
                   m.code AS machine_code, m.nom AS machine_nom,
                   p.poste, p.creneau, p.created_by, p.created_at
            FROM rh_planning_postes p
            JOIN users u ON u.id = p.user_id
            LEFT JOIN machines m ON m.id = p.machine_id
        """
        params: list = []
        conds: list = []

        if from_week:
            conds.append("p.semaine >= ?")
            params.append(from_week)
        if to_week:
            conds.append("p.semaine <= ?")
            params.append(to_week)

        # Opérateurs : uniquement leur propre planning
        if role in ("fabrication", "logistique", "expedition"):
            conds.append("p.user_id = ?")
            params.append(user["id"])

        if conds:
            q += " WHERE " + " AND ".join(conds)
        q += " ORDER BY p.semaine, u.nom COLLATE NOCASE"

        rows = conn.execute(q, params).fetchall()
    return {"planning": [dict(r) for r in rows]}


@router.post("/planning")
async def create_planning(request: Request):
    editor = _require_edit(request)
    body = await request.json()

    user_id  = body.get("user_id")
    semaine  = body.get("semaine")
    machine_id = body.get("machine_id")   # peut être None (resp_atelier / logistique)
    poste    = body.get("poste")
    creneau  = body.get("creneau", "journee")
    force    = bool(body.get("force", False))  # passer outre un congé partiel

    if not user_id or not semaine or not poste:
        raise HTTPException(400, "Champs obligatoires manquants : user_id, semaine, poste")

    # Validation format semaine
    monday, sunday = _week_bounds(semaine)

    with get_db() as conn:
        # Vérification utilisateur planifiable
        user_row = conn.execute(
            "SELECT id, nom, role FROM users WHERE id = ? AND actif = 1", (user_id,)
        ).fetchone()
        if not user_row:
            raise HTTPException(404, "Utilisateur introuvable")

        # Déjà affecté cette semaine ?
        existing = conn.execute(
            "SELECT id, poste, machine_id FROM rh_planning_postes WHERE user_id = ? AND semaine = ?",
            (user_id, semaine),
        ).fetchone()
        if existing:
            raise HTTPException(
                409,
                f"{user_row['nom']} est déjà affecté cette semaine "
                f"(poste : {existing['poste']}). Retirez d'abord cette affectation.",
            )

        # Congé qui chevauche la semaine ?
        conge = conn.execute(
            """SELECT id, date_debut, date_fin, nb_jours, type_conge FROM rh_conges
               WHERE user_id = ? AND statut != 'refuse'
               AND date_debut <= ? AND date_fin >= ?""",
            (user_id, sunday.isoformat(), monday.isoformat()),
        ).fetchone()
        if conge:
            # Calculer les jours ouvrés de la semaine concernés par le congé
            JOURS_NOMS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]
            friday = monday + timedelta(days=4)
            d_deb = date.fromisoformat(conge["date_debut"])
            d_fin = date.fromisoformat(conge["date_fin"])
            cur_day = max(d_deb, monday)
            end_day = min(d_fin, friday)
            conge_days: list[str] = []
            while cur_day <= end_day:
                if cur_day.weekday() < 5:          # lundi–vendredi uniquement
                    conge_days.append(JOURS_NOMS[cur_day.weekday()])
                cur_day += timedelta(days=1)

            is_full_week = len(conge_days) >= 5    # semaine entière → blocage dur

            if is_full_week:
                raise HTTPException(
                    409,
                    f"{user_row['nom']} est en congé toute la semaine "
                    f"({conge['date_debut']} → {conge['date_fin']}, {conge['type_conge']}). "
                    f"Impossible de l'affecter.",
                )
            elif not force:
                # Congé partiel : informer et demander confirmation (force=True)
                from fastapi.responses import JSONResponse
                days_str = ", ".join(conge_days) if conge_days else conge["date_debut"]
                return JSONResponse(
                    status_code=409,
                    content={
                        "detail": (
                            f"{user_row['nom']} est en congé le(s) {days_str} cette semaine "
                            f"({conge['type_conge']}). Affecter quand même ?"
                        ),
                        "can_force": True,
                        "conge_days": conge_days,
                        "conge_type": conge["type_conge"],
                    },
                )
            # force=True → on continue malgré le congé partiel

        now = datetime.now().isoformat()
        cur = conn.execute(
            """INSERT INTO rh_planning_postes
                   (user_id, semaine, machine_id, poste, creneau, created_by, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, semaine, machine_id, poste, creneau, editor.get("email"), now),
        )
        conn.commit()
        new_id = cur.lastrowid

        row = conn.execute(
            """SELECT p.id, p.user_id, u.nom AS user_nom, u.role AS user_role,
                      p.semaine, p.machine_id,
                      m.code AS machine_code, m.nom AS machine_nom,
                      p.poste, p.creneau, p.created_by, p.created_at
               FROM rh_planning_postes p
               JOIN users u ON u.id = p.user_id
               LEFT JOIN machines m ON m.id = p.machine_id
               WHERE p.id = ?""",
            (new_id,),
        ).fetchone()
    return dict(row)


@router.delete("/planning/{plan_id}")
def delete_planning(plan_id: int, request: Request):
    _require_edit(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM rh_planning_postes WHERE id = ?", (plan_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Affectation introuvable")
        conn.execute("DELETE FROM rh_planning_postes WHERE id = ?", (plan_id,))
        conn.commit()
    return {"ok": True}


# ── Congés ───────────────────────────────────────────────────────
@router.get("/conges")
def get_conges(
    request: Request,
    user_id: Optional[int] = None,
    annee: Optional[int] = None,
):
    _require_view(request)
    with get_db() as conn:
        q = """SELECT c.id, c.user_id, u.nom AS user_nom,
                      c.date_debut, c.date_fin, c.nb_jours,
                      c.type_conge, c.note, c.statut,
                      c.created_by, c.created_at
               FROM rh_conges c
               JOIN users u ON u.id = c.user_id"""
        params: list = []
        conds: list = []
        if user_id:
            conds.append("c.user_id = ?")
            params.append(user_id)
        if annee:
            conds.append(
                "(strftime('%Y', c.date_debut) = ? OR strftime('%Y', c.date_fin) = ?)"
            )
            params.extend([str(annee), str(annee)])
        if conds:
            q += " WHERE " + " AND ".join(conds)
        q += " ORDER BY c.date_debut DESC"
        rows = conn.execute(q, params).fetchall()
    return {"conges": [dict(r) for r in rows]}


@router.post("/conges")
async def create_conge(request: Request):
    editor = _require_edit(request)
    body = await request.json()

    user_id    = body.get("user_id")
    date_debut = body.get("date_debut")
    date_fin   = body.get("date_fin")
    nb_jours   = body.get("nb_jours")
    type_conge = body.get("type_conge", "CP")
    note       = body.get("note", "")

    if not all([user_id, date_debut, date_fin, nb_jours is not None]):
        raise HTTPException(400, "Champs obligatoires : user_id, date_debut, date_fin, nb_jours")

    try:
        d_deb = date.fromisoformat(date_debut)
        d_fin = date.fromisoformat(date_fin)
        nb    = float(nb_jours)
    except (ValueError, TypeError):
        raise HTTPException(400, "Format de date invalide ou nb_jours non numérique")

    if d_fin < d_deb:
        raise HTTPException(400, "La date de fin doit être ≥ à la date de début")
    if nb <= 0:
        raise HTTPException(400, "Le nombre de jours doit être supérieur à 0")

    with get_db() as conn:
        user_row = conn.execute(
            "SELECT id, nom FROM users WHERE id = ? AND actif = 1", (user_id,)
        ).fetchone()
        if not user_row:
            raise HTTPException(404, "Utilisateur introuvable")

        # Conflits avec des affectations planning existantes
        existing_assignments = conn.execute(
            """SELECT p.semaine, p.poste, m.nom AS machine_nom
               FROM rh_planning_postes p
               LEFT JOIN machines m ON m.id = p.machine_id
               WHERE p.user_id = ?""",
            (user_id,),
        ).fetchall()

        conflicting = []
        for a in existing_assignments:
            try:
                ay, aw = a["semaine"].split("-W")
                mon = date.fromisocalendar(int(ay), int(aw), 1)
                sun = mon + timedelta(days=6)
            except (ValueError, AttributeError):
                continue
            if d_deb <= sun and d_fin >= mon:
                conflicting.append(a["semaine"])

        if conflicting:
            weeks_str = ", ".join(sorted(set(conflicting)))
            raise HTTPException(
                409,
                f"{user_row['nom']} est déjà affecté à un poste pour les semaines : {weeks_str}. "
                f"Retirez ces affectations avant de saisir les congés.",
            )

        now = datetime.now().isoformat()
        cur = conn.execute(
            """INSERT INTO rh_conges
                   (user_id, date_debut, date_fin, nb_jours, type_conge, note,
                    statut, created_by, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 'pose', ?, ?)""",
            (user_id, date_debut, date_fin, nb, type_conge, note or None,
             editor.get("email"), now),
        )
        conn.commit()
        new_id = cur.lastrowid

        row = conn.execute(
            """SELECT c.id, c.user_id, u.nom AS user_nom,
                      c.date_debut, c.date_fin, c.nb_jours,
                      c.type_conge, c.note, c.statut, c.created_at
               FROM rh_conges c JOIN users u ON u.id = c.user_id
               WHERE c.id = ?""",
            (new_id,),
        ).fetchone()
    return dict(row)


@router.put("/conges/{conge_id}")
async def update_conge(conge_id: int, request: Request):
    _require_edit(request)
    body = await request.json()

    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM rh_conges WHERE id = ?", (conge_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(404, "Congé introuvable")

        allowed = {"date_debut", "date_fin", "nb_jours", "type_conge", "note", "statut"}
        fields = {k: v for k, v in body.items() if k in allowed}
        if not fields:
            raise HTTPException(400, "Aucun champ modifiable fourni")

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [conge_id]
        conn.execute(f"UPDATE rh_conges SET {set_clause} WHERE id = ?", vals)
        conn.commit()

        row = conn.execute(
            """SELECT c.id, c.user_id, u.nom AS user_nom,
                      c.date_debut, c.date_fin, c.nb_jours,
                      c.type_conge, c.note, c.statut, c.created_at
               FROM rh_conges c JOIN users u ON u.id = c.user_id
               WHERE c.id = ?""",
            (conge_id,),
        ).fetchone()
        return dict(row)


@router.delete("/conges/{conge_id}")
def delete_conge(conge_id: int, request: Request):
    _require_edit(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM rh_conges WHERE id = ?", (conge_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Congé introuvable")
        conn.execute("DELETE FROM rh_conges WHERE id = ?", (conge_id,))
        conn.commit()
    return {"ok": True}


# ── Soldes congés ────────────────────────────────────────────────
@router.get("/soldes")
def get_soldes(request: Request, annee: Optional[int] = None):
    _require_view(request)
    year = annee or datetime.now().year

    with get_db() as conn:
        staff = conn.execute(
            """SELECT id, nom FROM users
               WHERE (role IN ('fabrication','logistique') OR email = 'mlesaffre@sifa.pro') AND actif = 1
               ORDER BY nom COLLATE NOCASE"""
        ).fetchall()

        soldes_raw = conn.execute(
            "SELECT * FROM rh_conges_soldes WHERE annee = ?", (year,)
        ).fetchall()
        soldes_map = {r["user_id"]: dict(r) for r in soldes_raw}

        poses = conn.execute(
            """SELECT user_id, type_conge, SUM(nb_jours) AS total
               FROM rh_conges
               WHERE strftime('%Y', date_debut) = ? AND statut != 'refuse'
               GROUP BY user_id, type_conge""",
            (str(year),),
        ).fetchall()
        poses_map: dict = {}
        for p in poses:
            uid = p["user_id"]
            if uid not in poses_map:
                poses_map[uid] = {"CP": 0.0, "RTT": 0.0, "maladie": 0.0, "autre": 0.0}
            tc = p["type_conge"]
            if tc in poses_map[uid]:
                poses_map[uid][tc] = float(p["total"])

        result = []
        for s in staff:
            uid = s["id"]
            sol = soldes_map.get(uid, {})
            pos = poses_map.get(uid, {"CP": 0.0, "RTT": 0.0, "maladie": 0.0, "autre": 0.0})
            quota_cp  = float(sol.get("quota_cp") if "quota_cp" in sol else 25)
            quota_rtt = float(sol.get("quota_rtt") if "quota_rtt" in sol else 0)
            result.append({
                "user_id":       uid,
                "user_nom":      s["nom"],
                "annee":         year,
                "quota_cp":      quota_cp,
                "quota_rtt":     quota_rtt,
                "poses_cp":      pos.get("CP",      0.0),
                "poses_rtt":     pos.get("RTT",     0.0),
                "poses_maladie": pos.get("maladie", 0.0),
                "poses_autre":   pos.get("autre",   0.0),
                "restant_cp":    round(quota_cp  - pos.get("CP",  0.0), 1),
                "restant_rtt":   round(quota_rtt - pos.get("RTT", 0.0), 1),
                "note":          sol.get("note") or "",
                "solde_id":      sol.get("id"),
            })

    return {"soldes": result, "annee": year}


@router.put("/soldes")
async def update_solde(request: Request):
    editor = _require_edit(request)
    body = await request.json()

    user_id   = body.get("user_id")
    annee     = int(body.get("annee") or datetime.now().year)
    quota_cp  = float(body.get("quota_cp",  25))
    quota_rtt = float(body.get("quota_rtt", 0))
    note      = body.get("note", "")

    if not user_id:
        raise HTTPException(400, "user_id requis")

    now = datetime.now().isoformat()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO rh_conges_soldes
                   (user_id, annee, quota_cp, quota_rtt, note, updated_by, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id, annee) DO UPDATE SET
                   quota_cp  = excluded.quota_cp,
                   quota_rtt = excluded.quota_rtt,
                   note      = excluded.note,
                   updated_by = excluded.updated_by,
                   updated_at = excluded.updated_at""",
            (user_id, annee, quota_cp, quota_rtt, note or None, editor.get("email"), now),
        )
        conn.commit()
    return {"ok": True}

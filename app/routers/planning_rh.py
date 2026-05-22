"""MySifa — Planning RH (Personnel) — API v1.0

Routes /api/rh/*
Lecture  : fabrication, logistique, comptabilite (lecture seule), administration (lecture seule), direction, superadmin
Écriture : direction, superadmin (configurateurs)
"""
from datetime import datetime, date, timedelta
from typing import Optional

from fastapi import APIRouter, Request, HTTPException

from app.services.audit_service import log_action
from database import get_db
from app.services.auth_service import get_current_user
from config import ROLES_PLANNING_RH_VIEW, ROLES_PLANNING_RH_EDIT, PLANNING_RH_EXCLUDED_NOMS

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
    email = (user.get("email") or "").strip().lower()
    overrides_raw = user.get("access_overrides")
    if overrides_raw:
        try:
            import json
            overrides = json.loads(overrides_raw) if isinstance(overrides_raw, str) else overrides_raw
            has_override = overrides.get("planning_rh") is True
        except:
            pass
    # Manuel Lessafre : accès édition explicite (même si rôle opérateur)
    if email == "mlesaffre@sifa.pro":
        return user
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


JOURS_NOMS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]
JOURS_ABREVS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"]
JOURS_MASK_WEEK = 31   # Lun–Ven (bits 0–4)
JOURS_MASK_ALL = 63    # Lun–Sam (bits 0–5)
JOURS_BIT_SAMEDI = 32


def _bits_to_day_labels(bits: int, short: bool = True) -> list[str]:
    labels = JOURS_ABREVS if short else JOURS_NOMS
    return [labels[i] for i in range(6) if (bits >> i) & 1]


def _same_planning_slot(
    poste: str,
    creneau: str,
    machine_id,
    other_poste: str,
    other_creneau: str,
    other_machine_id,
) -> bool:
    return (
        poste == other_poste
        and creneau == other_creneau
        and (
            machine_id == other_machine_id
            or (machine_id is None and other_machine_id is None)
        )
    )


def _norm_person_nom(val) -> str:
    return str(val or "").strip().lower()


def _planning_rh_nom_excluded(nom) -> bool:
    return _norm_person_nom(nom) in PLANNING_RH_EXCLUDED_NOMS


def _planning_rh_staff_sql_filter() -> tuple[str, list]:
    """Clause SQL + paramètres pour exclure les profils non planifiables."""
    if not PLANNING_RH_EXCLUDED_NOMS:
        return "", []
    clause = " AND " + " AND ".join("lower(trim(nom)) != ?" for _ in PLANNING_RH_EXCLUDED_NOMS)
    return clause, list(PLANNING_RH_EXCLUDED_NOMS)


def _filter_planning_rh_user_rows(rows, nom_key: str = "nom"):
    out = []
    for r in rows:
        d = dict(r)
        nom = d.get(nom_key) or d.get("user_nom") or ""
        if _planning_rh_nom_excluded(nom):
            continue
        out.append(d)
    return out


def _assert_planning_rh_user_allowed(conn, user_id: int) -> None:
    row = conn.execute(
        "SELECT nom FROM users WHERE id = ? AND actif = 1",
        (user_id,),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Utilisateur introuvable")
    if _planning_rh_nom_excluded(row["nom"]):
        raise HTTPException(400, "Ce profil n'est pas planifiable dans le planning RH")


# ── Personnel planifiable ────────────────────────────────────────
@router.get("/personnel")
def get_personnel(request: Request):
    _require_view(request)
    staff_filter, staff_params = _planning_rh_staff_sql_filter()
    with get_db() as conn:
        rows = conn.execute(
            f"""SELECT id, nom, email, role, machine_id, actif
               FROM users
               WHERE (role IN ('fabrication','logistique') OR email = 'mlesaffre@sifa.pro')
                 AND actif = 1{staff_filter}
               ORDER BY nom COLLATE NOCASE""",
            staff_params,
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
                   p.poste, p.creneau, p.jours, p.created_by, p.created_at
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
    return {"planning": _filter_planning_rh_user_rows(rows, "user_nom")}


@router.post("/planning")
async def create_planning(request: Request):
    editor = _require_edit(request)
    body = await request.json()

    user_id    = body.get("user_id")
    semaine    = body.get("semaine")
    machine_id = body.get("machine_id")   # peut être None (resp_atelier / logistique)
    poste      = body.get("poste")
    creneau    = body.get("creneau", "journee")
    force      = bool(body.get("force", False))   # passer outre un congé partiel
    jours_req  = body.get("jours")                # bitmask optionnel (None → auto)

    if not user_id or not semaine or not poste:
        raise HTTPException(400, "Champs obligatoires manquants : user_id, semaine, poste")

    monday, sunday = _week_bounds(semaine)
    friday = monday + timedelta(days=4)

    with get_db() as conn:
        user_row = conn.execute(
            "SELECT id, nom, role FROM users WHERE id = ? AND actif = 1", (user_id,)
        ).fetchone()
        if not user_row:
            raise HTTPException(404, "Utilisateur introuvable")
        if _planning_rh_nom_excluded(user_row["nom"]):
            raise HTTPException(400, "Ce profil n'est pas planifiable dans le planning RH")

        # Affectations existantes cette semaine (plusieurs postes / jours partiels possibles)
        existing_rows = conn.execute(
            """SELECT id, poste, machine_id, creneau, jours
               FROM rh_planning_postes WHERE user_id = ? AND semaine = ?""",
            (user_id, semaine),
        ).fetchall()

        busy_bits = 0
        for ex in existing_rows:
            ex_jours = int(ex["jours"] or 31) & JOURS_MASK_ALL
            busy_bits |= ex_jours
            if _same_planning_slot(
                poste, creneau, machine_id,
                ex["poste"], ex["creneau"], ex["machine_id"],
            ):
                raise HTTPException(
                    409,
                    f"{user_row['nom']} est déjà affecté sur ce poste / créneau cette semaine. "
                    f"Utilisez l'icône œil pour ajuster les jours.",
                )

        assign_days = _bits_to_day_labels(busy_bits)
        is_full_assigned = (busy_bits & JOURS_MASK_WEEK) == JOURS_MASK_WEEK

        # Congé qui chevauche la semaine ?
        conge = conn.execute(
            """SELECT id, date_debut, date_fin, nb_jours, type_conge FROM rh_conges
               WHERE user_id = ? AND statut != 'refuse'
               AND date_debut <= ? AND date_fin >= ?""",
            (user_id, sunday.isoformat(), monday.isoformat()),
        ).fetchone()

        conge_day_bits = 0   # bitmask des jours de congé (Lun=bit0 … Ven=bit4)
        conge_days: list[str] = []

        if conge:
            d_deb = date.fromisoformat(conge["date_debut"])
            d_fin = date.fromisoformat(conge["date_fin"])
            cur_day = max(d_deb, monday)
            end_day = min(d_fin, friday)
            while cur_day <= end_day:
                if cur_day.weekday() < 5:
                    conge_days.append(JOURS_NOMS[cur_day.weekday()])
                    conge_day_bits |= (1 << cur_day.weekday())
                cur_day += timedelta(days=1)

            is_full_week = len(conge_days) >= 5

            if is_full_week:
                raise HTTPException(
                    409,
                    f"{user_row['nom']} est en congé toute la semaine "
                    f"({conge['date_debut']} → {conge['date_fin']}, {conge['type_conge']}). "
                    f"Impossible de l'affecter.",
                )
            elif not force:
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
                        "conflict_type": "conge",
                        "conge_days": conge_days,
                        "conge_type": conge["type_conge"],
                    },
                )
            # force=True → on affecte malgré le congé partiel

        unavailable_bits = (busy_bits | conge_day_bits) & JOURS_MASK_ALL

        if is_full_assigned:
            raise HTTPException(
                409,
                f"{user_row['nom']} est déjà affecté toute la semaine. "
                f"Retirez ou ajustez une affectation existante.",
            )

        # Calculer le bitmask jours final :
        #   - Si le client fournit une valeur explicite → l'utiliser (masquée sur 5 bits)
        #   - Sinon → jours libres (hors congé et hors affectations existantes)
        if jours_req is not None:
            jours = int(jours_req) & JOURS_MASK_ALL
        else:
            jours = JOURS_MASK_WEEK & ~unavailable_bits

        overlap = jours & unavailable_bits
        if overlap:
            if not force:
                from fastapi.responses import JSONResponse

                if busy_bits and not (busy_bits & JOURS_MASK_WEEK == JOURS_MASK_WEEK):
                    days_str = ", ".join(assign_days) if assign_days else "?"
                    return JSONResponse(
                        status_code=409,
                        content={
                            "detail": (
                                f"{user_row['nom']} est déjà affecté le(s) {days_str} cette semaine. "
                                f"Affecter pour les autres jours ?"
                            ),
                            "can_force": True,
                            "conflict_type": "assignment",
                            "busy_days": assign_days,
                        },
                    )
                days_str = ", ".join(_bits_to_day_labels(conge_day_bits, short=False))
                return JSONResponse(
                    status_code=409,
                    content={
                        "detail": (
                            f"{user_row['nom']} est en congé le(s) {days_str} cette semaine "
                            f"({conge['type_conge']}). Affecter quand même ?"
                        ),
                        "can_force": True,
                        "conflict_type": "conge",
                        "conge_days": _bits_to_day_labels(conge_day_bits, short=False),
                        "conge_type": conge["type_conge"],
                    },
                )
            jours = jours & ~unavailable_bits

        if jours == 0:
            raise HTTPException(
                409,
                f"{user_row['nom']} n'a aucun jour disponible cette semaine "
                f"(affectations ou congés).",
            )

        now = datetime.now().isoformat()
        cur = conn.execute(
            """INSERT INTO rh_planning_postes
                   (user_id, semaine, machine_id, poste, creneau, jours, created_by, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, semaine, machine_id, poste, creneau, jours, editor.get("email"), now),
        )
        conn.commit()
        new_id = cur.lastrowid

        row = conn.execute(
            """SELECT p.id, p.user_id, u.nom AS user_nom, u.role AS user_role,
                      p.semaine, p.machine_id,
                      m.code AS machine_code, m.nom AS machine_nom,
                      p.poste, p.creneau, p.jours, p.created_by, p.created_at
               FROM rh_planning_postes p
               JOIN users u ON u.id = p.user_id
               LEFT JOIN machines m ON m.id = p.machine_id
               WHERE p.id = ?""",
            (new_id,),
        ).fetchone()
    return dict(row)


@router.delete("/planning/{plan_id}")
def delete_planning(plan_id: int, request: Request):
    editor = _require_edit(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM rh_planning_postes WHERE id = ?", (plan_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Affectation introuvable")
        conn.execute("DELETE FROM rh_planning_postes WHERE id = ?", (plan_id,))
        conn.commit()
    log_action(
        user=editor,
        action="DELETE",
        module="rh",
        objet=f"Poste RH #{plan_id} supprimé",
        ip=request.client.host if request.client else None,
    )
    return {"ok": True}


@router.put("/planning/{plan_id}")
async def update_planning_jours(plan_id: int, request: Request):
    """Met à jour le bitmask jours d'une affectation existante."""
    editor = _require_edit(request)
    body = await request.json()

    jours = body.get("jours")
    if jours is None:
        raise HTTPException(400, "Champ 'jours' requis (bitmask 0–31)")
    jours = int(jours) & JOURS_MASK_ALL
    if jours == 0:
        raise HTTPException(400, "Au moins un jour doit être sélectionné (lun–ven ou samedi)")

    with get_db() as conn:
        row = conn.execute(
            "SELECT id, user_id, semaine FROM rh_planning_postes WHERE id = ?", (plan_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Affectation introuvable")

        other_busy = 0
        others = conn.execute(
            """SELECT jours FROM rh_planning_postes
               WHERE user_id = ? AND semaine = ? AND id != ?""",
            (row["user_id"], row["semaine"], plan_id),
        ).fetchall()
        for o in others:
            other_busy |= int(o["jours"] or 31) & JOURS_MASK_ALL

        if jours & other_busy:
            days_str = ", ".join(_bits_to_day_labels(other_busy))
            raise HTTPException(
                409,
                f"Chevauchement avec une autre affectation ({days_str}). "
                f"Ajustez les jours sur les deux postes.",
            )

        conn.execute("UPDATE rh_planning_postes SET jours = ? WHERE id = ?", (jours, plan_id))
        conn.commit()

        updated = conn.execute(
            """SELECT p.id, p.user_id, u.nom AS user_nom, u.role AS user_role,
                      p.semaine, p.machine_id,
                      m.code AS machine_code, m.nom AS machine_nom,
                      p.poste, p.creneau, p.jours, p.created_by, p.created_at
               FROM rh_planning_postes p
               JOIN users u ON u.id = p.user_id
               LEFT JOIN machines m ON m.id = p.machine_id
               WHERE p.id = ?""",
            (plan_id,),
        ).fetchone()
    log_action(
        user=editor,
        action="UPDATE",
        module="rh",
        objet=f"Poste RH #{plan_id} modifié",
        detail={"jours": jours},
        ip=request.client.host if request.client else None,
    )
    return dict(updated)


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
    return {"conges": _filter_planning_rh_user_rows(rows, "user_nom")}


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
        if _planning_rh_nom_excluded(user_row["nom"]):
            raise HTTPException(400, "Ce profil n'est pas planifiable dans le planning RH")

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
    user_nom = user_row["nom"] if user_row else ""
    log_action(
        user=editor,
        action="CREATE",
        module="rh",
        objet=f"Congé {type_conge} · {user_nom} · {date_debut} → {date_fin}",
        ip=request.client.host if request.client else None,
    )
    return dict(row)


@router.put("/conges/{conge_id}")
async def update_conge(conge_id: int, request: Request):
    editor = _require_edit(request)
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
    log_action(
        user=editor,
        action="UPDATE",
        module="rh",
        objet=f"Congé #{conge_id} modifié",
        detail=fields or None,
        ip=request.client.host if request.client else None,
    )
    return dict(row)


@router.delete("/conges/{conge_id}")
def delete_conge(conge_id: int, request: Request):
    editor = _require_edit(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM rh_conges WHERE id = ?", (conge_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Congé introuvable")
        conn.execute("DELETE FROM rh_conges WHERE id = ?", (conge_id,))
        conn.commit()
    log_action(
        user=editor,
        action="DELETE",
        module="rh",
        objet=f"Congé #{conge_id} supprimé",
        ip=request.client.host if request.client else None,
    )
    return {"ok": True}


# ── Soldes congés ────────────────────────────────────────────────
@router.get("/soldes")
def get_soldes(request: Request, annee: Optional[int] = None):
    _require_view(request)
    year = annee or datetime.now().year

    staff_filter, staff_params = _planning_rh_staff_sql_filter()
    with get_db() as conn:
        staff = conn.execute(
            f"""SELECT id, nom FROM users
               WHERE (role IN ('fabrication','logistique') OR email = 'mlesaffre@sifa.pro')
                 AND actif = 1{staff_filter}
               ORDER BY nom COLLATE NOCASE""",
            staff_params,
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
        _assert_planning_rh_user_allowed(conn, int(user_id))
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

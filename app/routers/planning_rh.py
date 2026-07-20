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
from config import (
    ROLES_PLANNING_RH_VIEW,
    ROLES_PLANNING_RH_EDIT,
    ROLES_PLANNING_RH_ATELIER_VIEW,
    ROLES_PLANNING_RH_ATELIER_EDIT,
    ROLES_PLANNING_RH_HR_VIEW,
    ROLES_PLANNING_RH_HR_EDIT,
    PLANNING_RH_EXCLUDED_NOMS,
)

router = APIRouter(prefix="/api/rh", tags=["planning_rh"])


# ── Helpers accès ────────────────────────────────────────────────
# Deux vues distinctes exposées par ce module :
#   * "atelier" : planning postes + congés du personnel fabrication/logistique.
#     Vue historique — inchangée. Éditable par direction/superadmin (+ overrides
#     et Manuel Lesaffre en accès explicite).
#   * "rh"      : gestion des congés/soldes de TOUS les employés actifs.
#     Nouvelle vue — comptabilité/direction/superadmin en édition.
#
# Les helpers acceptent un paramètre `scope` qui bascule les rôles vérifiés.
# Les endpoints qui manipulent des congés/soldes acceptent scope depuis la
# query/body ; ceux qui manipulent des postes/machines restent en atelier.

def _has_planning_rh_override(user: dict) -> bool:
    overrides_raw = user.get("access_overrides")
    if not overrides_raw:
        return False
    try:
        import json
        overrides = json.loads(overrides_raw) if isinstance(overrides_raw, str) else overrides_raw
        return overrides.get("planning_rh") is True
    except Exception:
        return False


def _norm_scope(scope) -> str:
    s = str(scope or "").strip().lower()
    return "rh" if s in ("rh", "hr") else "atelier"


def _require_atelier_view(request: Request) -> dict:
    user = get_current_user(request)
    if user.get("role") not in ROLES_PLANNING_RH_ATELIER_VIEW and not _has_planning_rh_override(user):
        raise HTTPException(403, "Accès non autorisé au planning RH atelier")
    return user


def _require_atelier_edit(request: Request) -> dict:
    user = get_current_user(request)
    email = (user.get("email") or "").strip().lower()
    if email == "mlesaffre@sifa.pro":
        return user
    if user.get("role") not in ROLES_PLANNING_RH_ATELIER_EDIT and not _has_planning_rh_override(user):
        raise HTTPException(403, "Modification atelier réservée aux configurateurs (direction / superadmin)")
    return user


def _require_hr_view(request: Request) -> dict:
    user = get_current_user(request)
    if user.get("role") not in ROLES_PLANNING_RH_HR_VIEW:
        raise HTTPException(403, "Accès non autorisé à la vue RH")
    return user


def _require_hr_edit(request: Request) -> dict:
    user = get_current_user(request)
    if user.get("role") not in ROLES_PLANNING_RH_HR_EDIT:
        raise HTTPException(403, "Modification RH réservée à la comptabilité / direction / superadmin")
    return user


def _require_view(request: Request, scope: str = "atelier") -> dict:
    """Vue portée : 'atelier' (défaut) ou 'rh'."""
    return _require_hr_view(request) if _norm_scope(scope) == "rh" else _require_atelier_view(request)


def _require_edit(request: Request, scope: str = "atelier") -> dict:
    """Écriture portée : 'atelier' (postes/planning) ou 'rh' (congés/soldes tous services)."""
    return _require_hr_edit(request) if _norm_scope(scope) == "rh" else _require_atelier_edit(request)


def _require_conge_edit(request: Request) -> dict:
    """Écriture congé/solde : accessible aux éditeurs atelier OU RH.

    Direction/superadmin ont les deux permissions ; comptabilité n'a que RH ;
    Manuel Lesaffre (opérateur avec exception) garde l'accès atelier.
    """
    user = get_current_user(request)
    role = user.get("role")
    email = (user.get("email") or "").strip().lower()
    if email == "mlesaffre@sifa.pro":
        return user
    if (
        role in ROLES_PLANNING_RH_ATELIER_EDIT
        or role in ROLES_PLANNING_RH_HR_EDIT
        or _has_planning_rh_override(user)
    ):
        return user
    raise HTTPException(403, "Modification réservée à la direction, la comptabilité ou un superadmin")


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
def get_personnel(request: Request, scope: str = "atelier"):
    """Renvoie le personnel visible selon la vue.

    * scope='atelier' (défaut) : fabrication + logistique + Manuel Lesaffre.
      Comportement historique — utilisé par la grille postes.
    * scope='rh' : TOUS les utilisateurs actifs (tous services). Utilisé par
      la vue RH pour poser des congés à n'importe quel employé.
    """
    scope = _norm_scope(scope)
    _require_view(request, scope=scope)
    staff_filter, staff_params = _planning_rh_staff_sql_filter()
    with get_db() as conn:
        if scope == "rh":
            rows = conn.execute(
                f"""SELECT id, nom, email, role, machine_id, actif
                   FROM users
                   WHERE actif = 1{staff_filter}
                   ORDER BY role COLLATE NOCASE, nom COLLATE NOCASE""",
                staff_params,
            ).fetchall()
        else:
            rows = conn.execute(
                f"""SELECT id, nom, email, role, machine_id, actif
                   FROM users
                   WHERE (role IN ('fabrication','logistique') OR email = 'mlesaffre@sifa.pro')
                     AND actif = 1{staff_filter}
                   ORDER BY nom COLLATE NOCASE""",
                staff_params,
            ).fetchall()
    return {"personnel": _filter_planning_rh_user_rows(rows)}


@router.get("/machines")
def get_machines(request: Request):
    """Machines actives (pour résoudre machine_id sans accès MyProd › Planning)."""
    _require_atelier_view(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, code, nom FROM machines WHERE actif = 1 ORDER BY nom COLLATE NOCASE"
        ).fetchall()
    return {"machines": [dict(r) for r in rows]}


def _samedi_prod_travaille(conn, machine_id: int, semaine: str) -> tuple[str, bool]:
    """Samedi travaillé côté planning production (aligné GET /api/planning/.../day-work)."""
    monday, _ = _week_bounds(semaine)
    saturday = monday + timedelta(days=5)
    ds = saturday.isoformat()

    row = conn.execute(
        "SELECT is_worked FROM planning_day_worked WHERE machine_id=? AND date=?",
        (machine_id, ds),
    ).fetchone()
    if row is not None:
        return ds, int(row["is_worked"] or 0) == 1

    cfg = conn.execute(
        "SELECT samedi_travaille FROM planning_config WHERE machine_id=? AND semaine=?",
        (machine_id, semaine),
    ).fetchone()
    return ds, bool(cfg and int(cfg["samedi_travaille"] or 0) == 1)


@router.get("/samedi-prod-travaille")
def get_samedi_prod_travaille(request: Request, machine_id: int, semaine: str):
    """Vérifie si le samedi de la semaine est ouvré dans le planning de production."""
    _require_atelier_view(request)
    with get_db() as conn:
        m = conn.execute(
            "SELECT id FROM machines WHERE id=? AND actif=1", (machine_id,)
        ).fetchone()
        if not m:
            raise HTTPException(404, "Machine introuvable")
        ds, worked = _samedi_prod_travaille(conn, machine_id, semaine)
    return {
        "machine_id": machine_id,
        "semaine": semaine,
        "date": ds,
        "samedi_travaille": worked,
    }


# ── Planning : affectations hebdomadaires (atelier uniquement) ──
@router.get("/planning")
def get_planning(
    request: Request,
    from_week: Optional[str] = None,
    to_week: Optional[str] = None,
):
    user = _require_atelier_view(request)
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
    editor = _require_atelier_edit(request)
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
    editor = _require_atelier_edit(request)
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
    editor = _require_atelier_edit(request)
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
    scope: str = "atelier",
):
    """Liste les congés selon la portée demandée.

    * scope='atelier' (défaut) : congés du personnel fabrication/logistique.
    * scope='rh' : congés de TOUS les employés actifs (tous services).
    """
    scope = _norm_scope(scope)
    _require_view(request, scope=scope)
    with get_db() as conn:
        q = """SELECT c.id, c.user_id, u.nom AS user_nom, u.role AS user_role,
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
        if scope == "atelier":
            conds.append(
                "(u.role IN ('fabrication','logistique') OR u.email = 'mlesaffre@sifa.pro')"
            )
        if conds:
            q += " WHERE " + " AND ".join(conds)
        q += " ORDER BY c.date_debut DESC"
        rows = conn.execute(q, params).fetchall()
    return {"conges": _filter_planning_rh_user_rows(rows, "user_nom")}


@router.post("/conges")
async def create_conge(request: Request):
    editor = _require_conge_edit(request)
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
    editor = _require_conge_edit(request)
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
    editor = _require_conge_edit(request)
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
def get_soldes(request: Request, annee: Optional[int] = None, scope: str = "atelier"):
    """Soldes congés selon la portée.

    * scope='atelier' (défaut) : personnel fabrication/logistique.
    * scope='rh' : tous les employés actifs (tous services).
    """
    scope = _norm_scope(scope)
    _require_view(request, scope=scope)
    year = annee or datetime.now().year

    staff_filter, staff_params = _planning_rh_staff_sql_filter()
    with get_db() as conn:
        if scope == "rh":
            staff = conn.execute(
                f"""SELECT id, nom, role FROM users
                   WHERE actif = 1{staff_filter}
                   ORDER BY role COLLATE NOCASE, nom COLLATE NOCASE""",
                staff_params,
            ).fetchall()
        else:
            staff = conn.execute(
                f"""SELECT id, nom, role FROM users
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
                "user_role":     s["role"] if "role" in s.keys() else None,
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
    editor = _require_conge_edit(request)
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


# ══════════════════════════════════════════════════════════════════
# CONFIGURATION DES ÉQUIPES PAR MACHINE (matin / aprem / nuit)
# ══════════════════════════════════════════════════════════════════
# Ces réglages pilotent l'affichage des créneaux dans le planning RH :
# les machines sans ligne dans rh_machine_config utilisent les défauts
# codés côté frontend (compat rétro). Le mode_alternance = 'alterne'
# active la rotation d'équipes A/B semaine paire / impaire.

def _validate_hhmm(val: str, field: str) -> str:
    v = (val or "").strip()
    if not v:
        raise HTTPException(400, f"{field} requis (HH:MM)")
    try:
        h, m = v.split(":")
        hi, mi = int(h), int(m)
        if not (0 <= hi <= 23 and 0 <= mi <= 59):
            raise ValueError()
    except (ValueError, AttributeError):
        raise HTTPException(400, f"{field} invalide (HH:MM attendu)")
    return f"{hi:02d}:{mi:02d}"


def _rh_machine_config_row_to_dict(row) -> dict:
    return {
        "machine_id":       row["machine_id"],
        "matin_actif":      int(row["matin_actif"] or 0),
        "matin_debut":      row["matin_debut"] or "05:00",
        "matin_fin":        row["matin_fin"]   or "13:00",
        "aprem_actif":      int(row["aprem_actif"] or 0),
        "aprem_debut":      row["aprem_debut"] or "13:00",
        "aprem_fin":        row["aprem_fin"]   or "21:00",
        "nuit_actif":       int(row["nuit_actif"] or 0),
        "nuit_debut":       row["nuit_debut"] or "21:00",
        "nuit_fin":         row["nuit_fin"]   or "05:00",
        "mode_alternance":  (row["mode_alternance"] or "identique"),
        "updated_at":       row["updated_at"],
    }


@router.get("/machine-configs")
def list_machine_configs(request: Request):
    """Retourne la config d'équipes pour toutes les machines actives.

    Format : {"configs": [ { machine_id, nom, matin_actif, ... }, ... ]}
    Les machines sans ligne dans rh_machine_config renvoient les défauts.
    """
    _require_atelier_view(request)
    with get_db() as conn:
        machines = conn.execute(
            "SELECT id, nom FROM machines WHERE actif=1 ORDER BY nom"
        ).fetchall()
        configs = {
            r["machine_id"]: _rh_machine_config_row_to_dict(r)
            for r in conn.execute("SELECT * FROM rh_machine_config").fetchall()
        }
    out = []
    for m in machines:
        cfg = configs.get(m["id"])
        if cfg:
            cfg = dict(cfg)
            cfg["nom"] = m["nom"]
            out.append(cfg)
        else:
            out.append({
                "machine_id":      m["id"],
                "nom":             m["nom"],
                "matin_actif":     1,
                "matin_debut":     "05:00",
                "matin_fin":       "13:00",
                "aprem_actif":     1,
                "aprem_debut":     "13:00",
                "aprem_fin":       "21:00",
                "nuit_actif":      0,
                "nuit_debut":      "21:00",
                "nuit_fin":        "05:00",
                "mode_alternance": "identique",
                "updated_at":      None,
            })
    return {"configs": out}


@router.put("/machine-configs/{machine_id}")
async def set_machine_config(machine_id: int, request: Request):
    """Enregistre la configuration d'équipes d'une machine.

    Body (tous les champs optionnels — les manquants gardent leur valeur en base
    ou reçoivent le défaut) :
      matin_actif, matin_debut, matin_fin
      aprem_actif, aprem_debut, aprem_fin
      nuit_actif, nuit_debut, nuit_fin
      mode_alternance : 'identique' | 'alterne'
    """
    editor = _require_atelier_edit(request)
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "Body invalide")

    def as_bool(v, default=0):
        if v is None:
            return default
        try:
            return 1 if int(v) else 0
        except (TypeError, ValueError):
            return default

    matin_actif = as_bool(body.get("matin_actif"), 1)
    aprem_actif = as_bool(body.get("aprem_actif"), 1)
    nuit_actif  = as_bool(body.get("nuit_actif"), 0)

    matin_debut = _validate_hhmm(body.get("matin_debut", "05:00"), "matin_debut")
    matin_fin   = _validate_hhmm(body.get("matin_fin",   "13:00"), "matin_fin")
    aprem_debut = _validate_hhmm(body.get("aprem_debut", "13:00"), "aprem_debut")
    aprem_fin   = _validate_hhmm(body.get("aprem_fin",   "21:00"), "aprem_fin")
    nuit_debut  = _validate_hhmm(body.get("nuit_debut",  "21:00"), "nuit_debut")
    nuit_fin    = _validate_hhmm(body.get("nuit_fin",    "05:00"), "nuit_fin")

    mode = (body.get("mode_alternance") or "identique").strip().lower()
    if mode not in ("identique", "alterne"):
        raise HTTPException(400, "mode_alternance doit être 'identique' ou 'alterne'")

    with get_db() as conn:
        mac = conn.execute(
            "SELECT id, nom FROM machines WHERE id=?", (machine_id,)
        ).fetchone()
        if not mac:
            raise HTTPException(404, "Machine non trouvée")
        conn.execute(
            """INSERT INTO rh_machine_config
                   (machine_id, matin_actif, matin_debut, matin_fin,
                    aprem_actif, aprem_debut, aprem_fin,
                    nuit_actif, nuit_debut, nuit_fin,
                    mode_alternance, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
               ON CONFLICT(machine_id) DO UPDATE SET
                   matin_actif=excluded.matin_actif,
                   matin_debut=excluded.matin_debut,
                   matin_fin=excluded.matin_fin,
                   aprem_actif=excluded.aprem_actif,
                   aprem_debut=excluded.aprem_debut,
                   aprem_fin=excluded.aprem_fin,
                   nuit_actif=excluded.nuit_actif,
                   nuit_debut=excluded.nuit_debut,
                   nuit_fin=excluded.nuit_fin,
                   mode_alternance=excluded.mode_alternance,
                   updated_at=datetime('now')""",
            (
                machine_id, matin_actif, matin_debut, matin_fin,
                aprem_actif, aprem_debut, aprem_fin,
                nuit_actif, nuit_debut, nuit_fin,
                mode,
            ),
        )
        conn.commit()

    try:
        log_action(
            user=editor,
            action="UPDATE",
            module="planning_rh",
            objet=f"Config équipes machine {mac['nom']}",
            detail={
                "matin": {"actif": matin_actif, "debut": matin_debut, "fin": matin_fin},
                "aprem": {"actif": aprem_actif, "debut": aprem_debut, "fin": aprem_fin},
                "nuit":  {"actif": nuit_actif,  "debut": nuit_debut,  "fin": nuit_fin},
                "mode_alternance": mode,
            },
            ip=request.client.host if request.client else None,
        )
    except Exception:
        pass

    return {"ok": True, "machine_id": machine_id}

# ─── v2.2.59 : créneaux de maintenance de l'user courant (Planning RH · Ma semaine) ──

@router.get("/my-maintenance")
def get_my_maintenance(
    request: Request,
    from_week: str,
    to_week: str,
):
    """Liste les créneaux de maintenance où l'user courant est assigné,
    dans la plage de semaines [from_week..to_week]. Payload minimal pour
    l'affichage inline dans « Mon planning »."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(401, "Non connecté")
    lundi_from, _ = _week_bounds(from_week)
    _, dim_to = _week_bounds(to_week)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT e.id, e.date_prevue, e.heure_debut, e.heure_fin,
                      e.machine, e.source, e.nom,
                      (SELECT COUNT(*) FROM maintenance_event_ops
                        WHERE event_id = e.id) AS ops_count,
                      (SELECT COUNT(*) FROM maintenance_event_ops
                        WHERE event_id = e.id AND statut = 'termine') AS ops_termine
               FROM maintenance_events e
               JOIN maintenance_event_operators eo
                 ON eo.event_id = e.id
               WHERE eo.operator_id = ?
                 AND e.date_prevue >= ?
                 AND e.date_prevue <= ?
                 AND COALESCE(e.source, 'planifie') != 'non_planifie'
                 AND e.heure_debut IS NOT NULL AND e.heure_debut != ''
                 AND e.heure_fin IS NOT NULL AND e.heure_fin != ''
               ORDER BY e.date_prevue ASC, e.heure_debut ASC, e.id ASC""",
            (user["id"], lundi_from.isoformat(), dim_to.isoformat()),
        ).fetchall()
    events = [dict(r) for r in rows]
    return {"events": events}


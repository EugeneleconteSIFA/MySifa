"""MySifa — Fabrication API v1.1
Routes : /api/fabrication/*
Accessible : fabrication, admin, superadmin
"""
import json
from datetime import datetime, date, timedelta
from typing import Optional
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Request, HTTPException

_PARIS = ZoneInfo("Europe/Paris")

from app.services.audit_service import log_action
from database import get_db, parse_datetime
from config import classify_operation
from app.services.auth_service import get_current_user, is_fabrication, is_admin
from app.routers.planning import _planned_end_iso_for_machine

router = APIRouter()

# Dossiers saisis hors planning (OF saisi manuellement par l'opérateur)
_FICTIF_PREFIX = "FICTIF:"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _can_edit_matiere_scan(user: dict, row: dict, operateur_courant: str) -> bool:
    """Correction traçabilité : admin, auteur du scan, ou même machine que l'utilisateur."""
    if is_admin(user):
        return True
    if (row.get("operateur") or "").strip() == (operateur_courant or "").strip():
        return True
    uid, mid = user.get("machine_id"), row.get("machine_id")
    if uid is not None and mid is not None:
        try:
            return int(uid) == int(mid)
        except (TypeError, ValueError):
            return False
    return False


def _check_fab_access(user: dict):
    """Fabrication OU admin autorisé pour cette API."""
    if not (is_fabrication(user) or is_admin(user)):
        raise HTTPException(status_code=403, detail="Accès réservé au service Fabrication")


def _today_prefix() -> str:
    return date.today().isoformat()


def _resolve_date_operation(client_raw: Optional[str]) -> str:
    """Horodatage canonique avec secondes (client au clic ou serveur).

    Accepte l'heure envoyée par le navigateur si plausible (±24 h, pas >2 min futur).
    """
    now = datetime.now(_PARIS).replace(tzinfo=None)
    if client_raw:
        raw = str(client_raw).strip()
        if raw:
            dt = parse_datetime(raw)
            if dt is None:
                raise HTTPException(
                    status_code=400,
                    detail="Horodatage invalide (format attendu : YYYY-MM-DDTHH:MM:SS)",
                )
            delta = (dt - now).total_seconds()
            if delta > 120:
                raise HTTPException(
                    status_code=400,
                    detail="Horodatage dans le futur — vérifiez l'heure de l'appareil",
                )
            if delta < -86400:
                raise HTTPException(
                    status_code=400,
                    detail="Horodatage trop ancien",
                )
            return dt.strftime("%Y-%m-%dT%H:%M:%S")
    return now.strftime("%Y-%m-%dT%H:%M:%S")


def _compute_etat(saisies: list) -> str:
    """Calcule l'état machine à partir des saisies du jour (du plus récent au plus vieux)."""
    if not saisies:
        return "sans_session"

    last = saisies[-1]
    code = str(last.get("operation_code") or "").strip()

    if code == "90":  # Annulation saisie : on ignore et on regarde avant
        return _compute_etat(saisies[:-1])
    if code == "87":  # Départ personnel
        return "sans_session"
    if code == "86":  # Arrivée personnel
        return "arrive"
    if code in ("01",):  # Début dossier → production en cours
        return "en_cours_production"
    if code in ("03", "88"):  # Production / Reprise
        return "en_cours_production"
    if code == "89":  # Fin dossier
        return "fin_dossier"

    # Codes 50–85 → arrêt machine
    try:
        if 50 <= int(code) <= 85:
            return "en_arret"
    except (ValueError, TypeError):
        pass

    return "en_cours_production"


def _get_active_dossier(saisies: list):
    """Retourne la ref du dossier actif (dernier Début sans Fin dossier correspondant)."""
    active = None
    for s in saisies:
        code = str(s.get("operation_code") or "").strip()
        if code == "01":
            active = s.get("no_dossier")
        elif code == "89":
            active = None
    return active


def _is_fictif_dossier(no_dossier: Optional[str]) -> bool:
    ref = (no_dossier or "").strip()
    return ref.upper().startswith(_FICTIF_PREFIX)


def _fictif_of_display(no_dossier: str) -> str:
    """Numéro OF affiché (sans préfixe interne)."""
    ref = (no_dossier or "").strip()
    if _is_fictif_dossier(ref):
        return ref[len(_FICTIF_PREFIX) :].strip()
    return ref


def _normalize_fictif_no_dossier(raw: str) -> str:
    """Valide et normalise un n° OF fictif → FICTIF:<of>."""
    s = (raw or "").strip()
    if not s:
        raise HTTPException(
            status_code=400,
            detail="Numéro d'ordre de fabrication requis pour un dossier hors planning",
        )
    if s.upper().startswith(_FICTIF_PREFIX):
        s = s[len(_FICTIF_PREFIX) :].strip()
    if not s:
        raise HTTPException(
            status_code=400,
            detail="Numéro d'ordre de fabrication invalide",
        )
    if len(s) > 80:
        raise HTTPException(
            status_code=400,
            detail="Numéro d'ordre de fabrication trop long (80 caractères max)",
        )
    return _FICTIF_PREFIX + s


def _build_fictif_dossier_dict(no_dossier: str, machine: Optional[dict] = None) -> dict:
    of = _fictif_of_display(no_dossier)
    return {
        "reference": no_dossier.strip(),
        "fictif": True,
        "numero_of": of,
        "client": "",
        "description": "Dossier hors planning",
        "machine_nom": (machine or {}).get("nom"),
        "machine_code": (machine or {}).get("code"),
    }


def _resolve_machine(user: dict, body: dict, conn) -> dict:
    """
    Retourne le dict machine pour la saisie.
    - Opérateur normal : machine liée au compte (machine_id).
    - Admin sans machine liée : utilise machine_id passé dans le body.
    Lève 400 si aucune machine identifiable.
    """
    machine_id = user.get("machine_id")

    # Admin peut surcharger avec le machine_id du body
    if is_admin(user) and body.get("machine_id"):
        try:
            machine_id = int(body["machine_id"])
        except (ValueError, TypeError):
            pass

    if not machine_id:
        raise HTTPException(
            status_code=400,
            detail="Aucune machine liée à votre compte — sélectionnez une machine ou contactez un administrateur",
        )

    m = conn.execute("SELECT * FROM machines WHERE id=?", (machine_id,)).fetchone()
    if not m:
        raise HTTPException(status_code=400, detail=f"Machine introuvable (id={machine_id})")
    return dict(m)


def _machine_sql_match_params(machine_name: str, machine_code: str) -> tuple[str, str, str]:
    """Paramètres (nom, code, code) pour filtrer production_data.machine comme le planning."""
    mn = (machine_name or "").strip()
    mc = (machine_code or "").strip()
    return (mn, mc, mc)


def _first_01_date_iso_for_dossier_on_machine(
    conn, no_dossier: str, machine_name: str, machine_code: str
) -> Optional[str]:
    """Première saisie « Début de production » (01) pour ce dossier sur cette machine (MIN date_operation)."""
    if not (no_dossier or "").strip():
        return None
    mn, mc, mc2 = _machine_sql_match_params(machine_name, machine_code)
    row = conn.execute(
        """SELECT MIN(pd.date_operation) AS dt
           FROM production_data pd
           WHERE trim(pd.no_dossier) = trim(?)
             AND pd.operation_code = '01'
             AND (trim(pd.machine) = trim(?) OR (trim(?) != '' AND trim(pd.machine) = trim(?)))""",
        (no_dossier, mn, mc, mc2),
    ).fetchone()
    if not row or not row["dt"]:
        return None
    s = str(row["dt"]).strip()
    return s or None


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/api/fabrication/operations")
def get_fabrication_operations(request: Request):
    """Référentiel codes opération (SQLite) — même source que Paramètres > Opérations."""
    user = get_current_user(request)
    _check_fab_access(user)
    from app.services.operations_config import categories_for_ui, load_operations_dict

    with get_db() as conn:
        ops = load_operations_dict(conn)
    return {"operations": ops, "categories": categories_for_ui()}


@router.get("/api/fabrication/machines")
def list_machines(request: Request):
    """Liste toutes les machines actives (pour le sélecteur admin)."""
    user = get_current_user(request)
    _check_fab_access(user)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, nom, code, dernier_metrage FROM machines WHERE actif=1 ORDER BY nom"
        ).fetchall()
    return {"machines": [dict(r) for r in rows]}


@router.get("/api/fabrication/fournisseurs-fsc")
def list_fournisseurs_fsc_fabrication(request: Request):
    """Fournisseurs FSC + infos guide traça (page fabrication, sans passer par /api/stock)."""
    user = get_current_user(request)
    _check_fab_access(user)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, nom, licence, certificat, traca_photo_url, traca_explication, traca_exemple_code
               FROM fournisseurs_fsc ORDER BY nom COLLATE NOCASE ASC"""
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/api/fabrication/dossiers")
def list_dossiers(request: Request, machine_id: int = None):
    """Dossiers planning pour le picker début de production.

    Sans recherche (q vide) : uniquement statut attente ou en_cours, ordre position.
    Avec recherche (q) : même périmètre statut, filtre texte côté SQL.
    """
    user = get_current_user(request)
    _check_fab_access(user)

    mid = user.get("machine_id") or machine_id
    q = (request.query_params.get("q") or "").strip()

    statut_sql = "pe.statut IN ('attente','en_cours')"
    order_sql = "pe.position ASC, pe.id ASC"
    params: list = []

    with get_db() as conn:
        if mid:
            where = f"pe.machine_id = ? AND {statut_sql}"
            params.append(mid)
            if q:
                like = f"%{q}%"
                where += (
                    " AND (LOWER(pe.reference) LIKE LOWER(?) OR LOWER(COALESCE(pe.client,'')) LIKE LOWER(?)"
                    " OR LOWER(COALESCE(pe.numero_of,'')) LIKE LOWER(?)"
                    " OR LOWER(COALESCE(pe.ref_produit,'')) LIKE LOWER(?)"
                    " OR LOWER(COALESCE(pe.description,'')) LIKE LOWER(?)"
                    " OR LOWER(COALESCE(pe.dos_rvgi,'')) LIKE LOWER(?))"
                )
                params.extend([like, like, like, like, like, like])
            rows = conn.execute(
                f"""SELECT pe.*, m.nom AS machine_nom, m.code AS machine_code
                    FROM planning_entries pe
                    JOIN machines m ON m.id = pe.machine_id
                    WHERE {where}
                    ORDER BY {order_sql}""",
                params,
            ).fetchall()
            machine = conn.execute(
                "SELECT * FROM machines WHERE id=?", (mid,)
            ).fetchone()
        else:
            # Admin sans machine : toutes machines, même filtre statut
            where = statut_sql
            if q:
                like = f"%{q}%"
                where += (
                    " AND (LOWER(pe.reference) LIKE LOWER(?) OR LOWER(COALESCE(pe.client,'')) LIKE LOWER(?)"
                    " OR LOWER(COALESCE(pe.numero_of,'')) LIKE LOWER(?)"
                    " OR LOWER(COALESCE(pe.ref_produit,'')) LIKE LOWER(?)"
                    " OR LOWER(COALESCE(pe.description,'')) LIKE LOWER(?)"
                    " OR LOWER(COALESCE(pe.dos_rvgi,'')) LIKE LOWER(?))"
                )
                params.extend([like, like, like, like, like, like])
            rows = conn.execute(
                f"""SELECT pe.*, m.nom AS machine_nom, m.code AS machine_code
                    FROM planning_entries pe
                    JOIN machines m ON m.id = pe.machine_id
                    WHERE {where}
                    ORDER BY m.nom ASC, {order_sql}""",
                params,
            ).fetchall()
            machine = None

        return {
            "dossiers": [dict(r) for r in rows],
            "machine": dict(machine) if machine else None,
        }


@router.get("/api/fabrication/session")
def get_session(request: Request, machine_id: int = None):
    """État de session actuel : saisies du jour, état courant, dossier actif."""
    user = get_current_user(request)
    _check_fab_access(user)

    # machine_id : préférence compte utilisateur, sinon query param (admin)
    mid = user.get("machine_id") or machine_id
    
    # Opérateur : operateur_lie si défini, sinon nom de l'utilisateur
    operateur = user.get("operateur_lie") or ""
    if not operateur:
        operateur = user.get("nom") or ""
    
    # Bloquer uniquement si pas d'opérateur ET pas de machine ET pas admin
    if not operateur and not mid and not is_admin(user):
        return {
            "saisies": [],
            "etat": "sans_session",
            "dossier": None,
            "last_saisie": None,
            "operateur": "",
            "machine": None,
        }

    today = _today_prefix()                          # "2026-04-16"
    today_fr = date.today().strftime("%d/%m/%Y")     # "16/04/2026"

    with get_db() as conn:
        if operateur:
            # Filtre : format ISO (YYYY-MM-DD…) OU format français (DD/MM/YYYY…)
            # Cherche soit par operateur_lie, soit par nom d'utilisateur
            rows = conn.execute(
                """SELECT * FROM production_data
                   WHERE (operateur = ? OR operateur = ?) AND (
                     date_operation LIKE ? OR date_operation LIKE ?
                   )
                   ORDER BY date_operation ASC, id ASC""",
                (operateur, user.get("nom") or operateur, today + "%", today_fr + "%"),
            ).fetchall()
        else:
            rows = []

        saisies = [dict(r) for r in rows]
        etat = _compute_etat(saisies)
        active_ref = _get_active_dossier(saisies)

        # Récupérer le dossier actif depuis le planning
        dossier = None
        if active_ref:
            row = conn.execute(
                """SELECT pe.*, m.nom AS machine_nom, m.code AS machine_code
                   FROM planning_entries pe
                   JOIN machines m ON m.id = pe.machine_id
                   WHERE pe.reference = ?""",
                (active_ref,),
            ).fetchone()
            if row:
                dossier = dict(row)
            elif _is_fictif_dossier(active_ref):
                dossier = _build_fictif_dossier_dict(active_ref, None)

        # Info machine
        machine = None
        if mid:
            m = conn.execute("SELECT * FROM machines WHERE id=?", (mid,)).fetchone()
            if m:
                machine = dict(m)

        if dossier and dossier.get("fictif") and machine:
            dossier["machine_nom"] = machine.get("nom")
            dossier["machine_code"] = machine.get("code")

        return {
            "saisies": saisies,
            "etat": etat,
            "dossier": dossier,
            "last_saisie": saisies[-1] if saisies else None,
            "operateur": operateur,
            "machine": machine,
        }


@router.get("/api/fabrication/saisies-jour")
def list_saisies_jour_all(request: Request):
    """Vue admin (lecture seule) : toutes les saisies du jour, triées par machine puis heure."""
    user = get_current_user(request)
    _check_fab_access(user)
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Accès réservé à l'administration")

    today = _today_prefix()
    today_fr = date.today().strftime("%d/%m/%Y")
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT
              pd.*,
              COALESCE(u.nom, pd.operateur) AS operateur_nom
            FROM production_data pd
            LEFT JOIN users u
              ON (
                trim(lower(u.operateur_lie)) = trim(lower(pd.operateur))
                OR trim(lower(u.nom)) = trim(lower(pd.operateur))
              )
            WHERE (date_operation LIKE ? OR date_operation LIKE ?)
            ORDER BY trim(COALESCE(pd.machine,'')) COLLATE NOCASE ASC,
                     pd.date_operation ASC, pd.id ASC
            """,
            (today + "%", today_fr + "%"),
        ).fetchall()
    return {"saisies": [dict(r) for r in rows]}


@router.post("/api/fabrication/saisie")
async def create_saisie(request: Request):
    """Crée une saisie de production. Autorisé pour le rôle Fabrication."""
    user = get_current_user(request)
    _check_fab_access(user)

    body = await request.json()

    op_str = (body.get("operation") or "").strip()
    if not op_str:
        raise HTTPException(status_code=400, detail="Opération manquante")

    cl = classify_operation(op_str)

    # Opérateur : operateur_lie si défini, sinon nom de l'utilisateur
    # machine_id : préférence compte utilisateur
    mid = user.get("machine_id")
    
    operateur = user.get("operateur_lie") or ""
    if is_admin(user) and body.get("operateur"):
        operateur = str(body["operateur"]).strip()
    # Si pas d'opérateur_lié, utiliser le nom de l'utilisateur
    if not operateur:
        operateur = user.get("nom") or ""
    if not operateur:
        raise HTTPException(
            status_code=400,
            detail="Compte utilisateur sans nom — contacter un administrateur",
        )

    date_op = _resolve_date_operation(body.get("date_operation"))

    no_dossier  = (body.get("no_dossier")   or "").strip() or None
    client      = (body.get("client")       or "").strip() or None
    designation = (body.get("designation")  or "").strip() or None
    commentaire = (body.get("commentaire")  or "").strip() or None

    dossier_fictif = bool(body.get("dossier_fictif"))
    numero_of_fictif = (
        (body.get("numero_of_fictif") or body.get("numero_of") or "").strip()
    )
    if dossier_fictif:
        no_dossier = _normalize_fictif_no_dossier(numero_of_fictif or no_dossier or "")
        designation = designation or "Dossier hors planning"
    elif no_dossier and _is_fictif_dossier(no_dossier):
        no_dossier = _normalize_fictif_no_dossier(no_dossier)
        designation = designation or "Dossier hors planning"

    # fin_dossier : booléen transmis par la saisie Fin de production
    # True  → dossier réellement terminé (statut_reel = reellement_termine)
    # False → production entamée mais non clôturée (statut_reel = reellement_en_saisie)
    fin_dossier_flag = bool(body.get("fin_dossier", False))

    # Métrages : début → metrage_prevu, fin → metrage_reel
    metrage_debut  = body.get("metrage_debut")
    metrage_fin    = body.get("metrage_fin")
    qte_etiquettes = body.get("qte_etiquettes")

    def to_float(v):
        try:
            return float(str(v).replace(",", ".")) if v not in (None, "", "null") else None
        except Exception:
            return None

    m_debut = to_float(metrage_debut)
    m_fin   = to_float(metrage_fin)
    m_etiq  = to_float(qte_etiquettes)

    with get_db() as conn:
        # ── Résolution machine (obligatoire pour toute saisie) ────────────────
        machine_obj = _resolve_machine(user, body, conn)
        machine_name = machine_obj["nom"]
        machine_id_resolved = machine_obj["id"]
        dernier_metrage = machine_obj.get("dernier_metrage")  # peut être None

        # ── Validations métrages ──────────────────────────────────────────────
        if cl["code"] == "01" and m_debut is not None:
            # Début dossier : métrage début >= dernier_metrage machine
            if dernier_metrage is not None and m_debut < dernier_metrage:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Métrage invalide : le compteur machine était à {int(dernier_metrage):,} m "
                        f"lors de la dernière saisie. "
                        f"La valeur saisie ({int(m_debut):,} m) ne peut pas être inférieure."
                    ).replace(",", " "),
                )

        if cl["code"] == "89" and m_fin is not None:
            # Fin dossier : métrage fin >= dernier_metrage machine
            if dernier_metrage is not None and m_fin < dernier_metrage:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Métrage invalide : le compteur machine était à {int(dernier_metrage):,} m "
                        f"lors de la dernière saisie. "
                        f"La valeur saisie ({int(m_fin):,} m) ne peut pas être inférieure."
                    ).replace(",", " "),
                )

            # Fin dossier : métrage fin >= métrage début du même dossier
            if no_dossier:
                mn, mc, mc2 = _machine_sql_match_params(machine_name, machine_obj.get("code") or "")
                debut_row = conn.execute(
                    """SELECT COALESCE(metrage_total_debut, metrage_prevu) AS ctr_debut
                       FROM production_data
                       WHERE trim(no_dossier) = trim(?) AND operation_code = '01'
                         AND (trim(machine) = trim(?) OR (trim(?) != '' AND trim(machine) = trim(?)))
                         AND COALESCE(metrage_total_debut, metrage_prevu) IS NOT NULL
                       ORDER BY date_operation ASC, id ASC LIMIT 1""",
                    (no_dossier, mn, mc, mc2),
                ).fetchone()
                if debut_row and debut_row["ctr_debut"] is not None:
                    m_debut_ref = float(debut_row["ctr_debut"])
                    if m_fin < m_debut_ref:
                        raise HTTPException(
                            status_code=400,
                            detail=(
                                f"Métrage invalide : le compteur en fin ({int(m_fin):,} m) "
                                f"ne peut pas être inférieur au compteur en début de dossier "
                                f"({int(m_debut_ref):,} m)."
                            ).replace(",", " "),
                        )

        # ── Insertion ─────────────────────────────────────────────────────────
        row_dict = {
            "operateur": operateur,
            "date_operation": date_op,
            "operation": op_str,
            "no_dossier": no_dossier,
            "machine": machine_name,
        }

        cursor = conn.execute(
            """INSERT INTO production_data
               (import_id, operateur, date_operation, operation, operation_code,
                operation_severity, operation_category, machine, no_dossier, client,
                designation, quantite_a_traiter, quantite_traitee, service,
                metrage_prevu, metrage_reel,
                metrage_total_debut, metrage_total_fin,
                commentaire, data, est_manuel, modifie_par, modifie_le, modifie_note)
               VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,NULL,NULL,?)""",
            (
                operateur, date_op,
                op_str, cl["code"], cl["severity"], cl["category"],
                machine_name, no_dossier, client, designation,
                0,
                m_etiq or 0,
                "fabrication",
                m_debut,          # metrage_prevu  (backward compat)
                m_fin,            # metrage_reel   (backward compat)
                m_debut,          # metrage_total_debut
                m_fin,            # metrage_total_fin
                commentaire,
                json.dumps(row_dict, default=str),
                "Saisie opérateur fabrication",
            ),
        )
        conn.commit()
        new_id = cursor.lastrowid

        # ── Mise à jour dernier_metrage machine ───────────────────────────────
        new_metrage = None
        if cl["code"] == "01" and m_debut is not None:
            new_metrage = m_debut
        elif cl["code"] == "89" and m_fin is not None:
            new_metrage = m_fin

        if new_metrage is not None:
            conn.execute(
                "UPDATE machines SET dernier_metrage=? WHERE id=?",
                (new_metrage, machine_id_resolved),
            )
            conn.commit()

        # ── Sync planning depuis saisie réelle (source de vérité prioritaire) ─
        if no_dossier and cl["code"] in ("01", "89"):
            try:
                pe_row = conn.execute(
                    """SELECT id, statut_reel, statut, duree_heures, planned_start, planned_end,
                              planned_end_manual
                       FROM planning_entries
                       WHERE machine_id = ? AND statut != 'termine'
                         AND (trim(reference) = trim(?) OR trim(COALESCE(numero_of,'')) = trim(?))
                       ORDER BY position ASC LIMIT 1""",
                    (machine_id_resolved, no_dossier, no_dossier),
                ).fetchone()
                if pe_row:
                    pe_id        = pe_row["id"]
                    current_reel = pe_row["statut_reel"] or "reellement_en_attente"
                    duree_h      = float(pe_row["duree_heures"] or 0)
                    manual_end   = int(pe_row["planned_end_manual"] or 0) == 1
                    now_iso      = datetime.now().isoformat()

                    if cl["code"] == "01" and current_reel != "reellement_termine":
                        conn.execute(
                            """UPDATE planning_entries SET statut='attente', statut_force=0,
                                   planned_start=NULL, planned_end=NULL, updated_at=?
                               WHERE machine_id=? AND statut='en_cours' AND id != ?""",
                            (now_iso, machine_id_resolved, pe_id),
                        )
                        mcode = str(machine_obj.get("code") or "")
                        start_iso = (
                            _first_01_date_iso_for_dossier_on_machine(
                                conn, no_dossier, machine_name, mcode
                            )
                            or date_op
                        )
                        dt_start = datetime.fromisoformat(start_iso)
                        if manual_end:
                            conn.execute(
                                """UPDATE planning_entries
                                   SET statut_reel   = 'reellement_en_saisie',
                                       statut        = 'en_cours',
                                       statut_force  = 1,
                                       planned_start = ?,
                                       updated_at    = ?
                                   WHERE id = ?""",
                                (start_iso, now_iso, pe_id),
                            )
                        else:
                            dt_end_new = _planned_end_iso_for_machine(
                                conn, machine_id_resolved, start_iso, duree_h
                            )
                            if not dt_end_new:
                                dt_end_new = (dt_start + timedelta(hours=duree_h)).strftime(
                                    "%Y-%m-%dT%H:%M:%S"
                                )
                            conn.execute(
                                """UPDATE planning_entries
                                   SET statut_reel   = 'reellement_en_saisie',
                                       statut        = 'en_cours',
                                       statut_force  = 1,
                                       planned_start = ?,
                                       planned_end   = ?,
                                       updated_at    = ?
                                   WHERE id = ?""",
                                (start_iso, dt_end_new, now_iso, pe_id),
                            )
                        conn.commit()

                    elif cl["code"] == "89":
                        if fin_dossier_flag:
                            elapsed = 0.0
                            try:
                                debut_iso = _first_01_date_iso_for_dossier_on_machine(
                                    conn,
                                    no_dossier,
                                    machine_name,
                                    str(machine_obj.get("code") or ""),
                                )
                                if debut_iso:
                                    dt_s = datetime.fromisoformat(debut_iso)
                                    dt_e = datetime.fromisoformat(date_op)
                                    elapsed = round((dt_e - dt_s).total_seconds() / 3600, 2)
                            except Exception:
                                pass

                            if elapsed > 0:
                                conn.execute(
                                    """UPDATE planning_entries
                                       SET statut_reel  = 'reellement_termine',
                                           statut       = 'termine',
                                           statut_force = 1,
                                           planned_end  = ?,
                                           duree_heures = ?,
                                           updated_at   = ?
                                       WHERE id = ?""",
                                    (date_op, elapsed, now_iso, pe_id),
                                )
                            else:
                                conn.execute(
                                    """UPDATE planning_entries
                                       SET statut_reel  = 'reellement_termine',
                                           statut       = 'termine',
                                           statut_force = 1,
                                           planned_end  = ?,
                                           updated_at   = ?
                                       WHERE id = ?""",
                                    (date_op, now_iso, pe_id),
                                )
                            conn.commit()

                        else:
                            if current_reel == "reellement_en_attente":
                                conn.execute(
                                    """UPDATE planning_entries SET statut='attente', statut_force=0,
                                           planned_start=NULL, planned_end=NULL, updated_at=?
                                       WHERE machine_id=? AND statut='en_cours' AND id != ?""",
                                    (now_iso, machine_id_resolved, pe_id),
                                )
                                mcode = str(machine_obj.get("code") or "")
                                start_iso = (
                                    _first_01_date_iso_for_dossier_on_machine(
                                        conn, no_dossier, machine_name, mcode
                                    )
                                    or date_op
                                )
                                dt_start = datetime.fromisoformat(start_iso)
                                if manual_end:
                                    conn.execute(
                                        """UPDATE planning_entries
                                           SET statut_reel   = 'reellement_en_saisie',
                                               statut        = 'en_cours',
                                               statut_force  = 1,
                                               planned_start = ?,
                                               updated_at    = ?
                                           WHERE id = ?""",
                                        (start_iso, now_iso, pe_id),
                                    )
                                else:
                                    dt_end_new = _planned_end_iso_for_machine(
                                        conn, machine_id_resolved, start_iso, duree_h
                                    )
                                    if not dt_end_new:
                                        dt_end_new = (
                                            dt_start + timedelta(hours=duree_h)
                                        ).strftime("%Y-%m-%dT%H:%M:%S")
                                    conn.execute(
                                        """UPDATE planning_entries
                                           SET statut_reel   = 'reellement_en_saisie',
                                               statut        = 'en_cours',
                                               statut_force  = 1,
                                               planned_start = ?,
                                               planned_end   = ?,
                                               updated_at    = ?
                                           WHERE id = ?""",
                                        (start_iso, dt_end_new, now_iso, pe_id),
                                    )
                                conn.commit()

            except Exception:
                pass  # Ne jamais bloquer la saisie opérateur

        row = conn.execute(
            "SELECT * FROM production_data WHERE id=?", (new_id,)
        ).fetchone()

    log_action(
        user=user,
        action="CREATE",
        module="fabrication",
        objet=f"Saisie {cl['code']} · {no_dossier or '—'} · {machine_name}",
        detail={"duree_heures": None, "metrage_reel": m_fin, "metrage_prevu": m_debut},
        ip=request.client.host if request.client else None,
    )
    return {"success": True, "id": new_id, "saisie": dict(row)}


# ─── Traçabilité matières ─────────────────────────────────────────────────────

@router.get("/api/fabrication/matieres")
def list_matieres(request: Request, machine_id: int = None, no_dossier: str = None):
    """Retourne les matières scannées : pour une machine (session du jour) ou un dossier."""
    user = get_current_user(request)
    _check_fab_access(user)

    mid = user.get("machine_id") or machine_id
    # Opérateur : operateur_lie si défini, sinon nom de l'utilisateur
    operateur = user.get("operateur_lie") or ""
    if not operateur:
        operateur = user.get("nom") or ""

    with get_db() as conn:
        select_sql = """
            SELECT
              fmu.*,
              sr.id AS reception_id_found,
              COALESCE(sr.fournisseur, fmu.fournisseur_manual) AS fournisseur,
              COALESCE(sr.certificat_fsc, fmu.certificat_fsc_manual) AS certificat_fsc,
              CASE
                WHEN sr.id IS NOT NULL THEN 'reception'
                WHEN fmu.fournisseur_manual IS NOT NULL THEN 'manual'
                ELSE NULL
              END AS liaison_mode_resolved
            FROM fab_matieres_utilisees fmu
            LEFT JOIN stock_receptions sr
              ON sr.id = (
                SELECT i.reception_id
                FROM stock_reception_items i
                WHERE trim(i.code_barre) = trim(fmu.code_barre)
                ORDER BY i.scanned_at DESC, i.id DESC
                LIMIT 1
              )
        """
        if no_dossier:
            rows = conn.execute(
                select_sql + """
                   WHERE fmu.no_dossier = ?
                   ORDER BY fmu.scanned_at ASC""",
                (no_dossier,),
            ).fetchall()
        elif mid:
            today = _today_prefix()
            today_fr = date.today().strftime("%d/%m/%Y")
            rows = conn.execute(
                select_sql + """
                   WHERE fmu.machine_id = ? AND (fmu.scanned_at LIKE ? OR fmu.scanned_at LIKE ?)
                   ORDER BY fmu.scanned_at ASC""",
                (mid, today + "%", today_fr + "%"),
            ).fetchall()
        else:
            rows = []

    matieres = []
    for r in rows:
        d = dict(r)
        # Normalise: si une réception est trouvée, elle prime sur une éventuelle liaison manuelle
        if d.get("reception_id_found"):
            d["reception_id"] = d.get("reception_id_found")
            d["liaison_mode"] = "reception"
        else:
            d["liaison_mode"] = d.get("liaison_mode_resolved") or d.get("liaison_mode")
        d.pop("reception_id_found", None)
        d.pop("liaison_mode_resolved", None)
        matieres.append(d)
    return {"matieres": matieres}


@router.get("/api/fabrication/receptions/lookup")
def lookup_reception_for_barcode(request: Request, code_barre: str):
    """Lookup d'une réception matière depuis un code barre (pour Traça Fabrication)."""
    user = get_current_user(request)
    _check_fab_access(user)
    code = (code_barre or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="Code barre manquant")
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT r.id AS reception_id, r.fournisseur, r.certificat_fsc
            FROM stock_reception_items i
            JOIN stock_receptions r ON r.id = i.reception_id
            WHERE trim(i.code_barre) = trim(?)
            ORDER BY i.scanned_at DESC, i.id DESC
            LIMIT 1
            """,
            (code,),
        ).fetchone()
    if not row:
        return {"found": False}
    d = dict(row)
    return {
        "found": True,
        "reception_id": d.get("reception_id"),
        "fournisseur": d.get("fournisseur"),
        "certificat_fsc": d.get("certificat_fsc"),
    }


@router.post("/api/fabrication/matieres")
async def add_matiere(request: Request):
    """Enregistre un scan de code barre matière. Lié à la machine + dossier actif."""
    user = get_current_user(request)
    _check_fab_access(user)

    body = await request.json()
    code_barre = (body.get("code_barre") or "").strip()
    if not code_barre:
        raise HTTPException(status_code=400, detail="Code barre manquant")

    fournisseur_fsc_id = body.get("fournisseur_fsc_id")
    try:
        fournisseur_fsc_id = int(fournisseur_fsc_id) if fournisseur_fsc_id is not None else None
    except (ValueError, TypeError):
        fournisseur_fsc_id = None

    # Opérateur : operateur_lie si défini, sinon nom de l'utilisateur
    operateur = user.get("operateur_lie") or ""
    if not operateur:
        operateur = user.get("nom") or ""
    if is_admin(user) and body.get("operateur"):
        operateur = str(body["operateur"]).strip()

    no_dossier = (body.get("no_dossier") or "").strip() or None
    scanned_at = datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")

    with get_db() as conn:
        machine_obj = _resolve_machine(user, body, conn)
        machine_id_resolved = machine_obj["id"]
        machine_name = machine_obj["nom"]

        cursor = conn.execute(
            """INSERT INTO fab_matieres_utilisees
               (machine_id, machine_nom, operateur, no_dossier, code_barre, scanned_at)
               VALUES (?,?,?,?,?,?)""",
            (machine_id_resolved, machine_name, operateur, no_dossier, code_barre, scanned_at),
        )
        conn.commit()
        new_id = cursor.lastrowid

        _link_matiere_to_reception(conn, new_id, code_barre, fournisseur_fsc_id)
        conn.commit()

        row = conn.execute(
            """SELECT
                 fmu.*,
                 sr.id AS reception_id_found,
                 COALESCE(sr.fournisseur, fmu.fournisseur_manual) AS fournisseur,
                 COALESCE(sr.certificat_fsc, fmu.certificat_fsc_manual) AS certificat_fsc,
                 CASE
                   WHEN sr.id IS NOT NULL THEN 'reception'
                   WHEN fmu.fournisseur_manual IS NOT NULL THEN 'manual'
                   ELSE NULL
                 END AS liaison_mode_resolved
               FROM fab_matieres_utilisees fmu
               LEFT JOIN stock_receptions sr
                 ON sr.id = (
                   SELECT i.reception_id
                   FROM stock_reception_items i
                   WHERE trim(i.code_barre) = trim(fmu.code_barre)
                   ORDER BY i.scanned_at DESC, i.id DESC
                   LIMIT 1
                 )
               WHERE fmu.id=?""",
            (new_id,),
        ).fetchone()

    d = dict(row) if row else {}
    if d.get("reception_id_found"):
        d["reception_id"] = d.get("reception_id_found")
        d["liaison_mode"] = "reception"
    else:
        d["liaison_mode"] = d.get("liaison_mode_resolved") or d.get("liaison_mode")
    d.pop("reception_id_found", None)
    d.pop("liaison_mode_resolved", None)
    return {"success": True, "id": new_id, "matiere": d}


def _link_matiere_to_reception(conn, matiere_id: int, code_barre: str, fournisseur_fsc_id: int | None) -> None:
    """Lie un scan matière à une réception stock ou à un fournisseur FSC (manuel)."""
    rec = conn.execute(
        """
        SELECT r.id AS reception_id, r.fournisseur, r.certificat_fsc
        FROM stock_reception_items i
        JOIN stock_receptions r ON r.id = i.reception_id
        WHERE trim(i.code_barre) = trim(?)
        ORDER BY i.scanned_at DESC, i.id DESC
        LIMIT 1
        """,
        (code_barre,),
    ).fetchone()
    if rec and rec["reception_id"]:
        conn.execute(
            """UPDATE fab_matieres_utilisees
               SET reception_id=?, liaison_mode='reception',
                   fournisseur_manual=NULL, certificat_fsc_manual=NULL
               WHERE id=?""",
            (int(rec["reception_id"]), matiere_id),
        )
        return
    if not fournisseur_fsc_id:
        raise HTTPException(
            status_code=409,
            detail="Fournisseur requis — liaison manuelle.",
        )
    f = conn.execute(
        "SELECT nom, certificat FROM fournisseurs_fsc WHERE id=?",
        (int(fournisseur_fsc_id),),
    ).fetchone()
    if not f:
        raise HTTPException(status_code=400, detail="Fournisseur introuvable")
    conn.execute(
        """UPDATE fab_matieres_utilisees
           SET reception_id=NULL, liaison_mode='manual',
               fournisseur_manual=?, certificat_fsc_manual=?
           WHERE id=?""",
        (str(f["nom"]), str(f["certificat"] or ""), matiere_id),
    )


@router.patch("/api/fabrication/matieres/{matiere_id}")
async def patch_matiere(matiere_id: int, request: Request):
    """Modifie le code barre d'un scan matière."""
    user = get_current_user(request)
    _check_fab_access(user)

    body = await request.json()
    code_barre = (body.get("code_barre") or "").strip()
    if not code_barre:
        raise HTTPException(status_code=400, detail="Code barre manquant")

    fournisseur_fsc_id = body.get("fournisseur_fsc_id")
    try:
        fournisseur_fsc_id = int(fournisseur_fsc_id) if fournisseur_fsc_id is not None else None
    except (ValueError, TypeError):
        fournisseur_fsc_id = None

    operateur = user.get("operateur_lie") or ""
    if not operateur:
        operateur = user.get("nom") or ""

    with get_db() as conn:
        ex = conn.execute(
            "SELECT * FROM fab_matieres_utilisees WHERE id=?", (matiere_id,)
        ).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Scan non trouvé")
        if not _can_edit_matiere_scan(user, dict(ex), operateur):
            raise HTTPException(status_code=403, detail="Non autorisé")

        try:
            conn.execute("BEGIN")
            conn.execute(
                "UPDATE fab_matieres_utilisees SET code_barre=? WHERE id=?",
                (code_barre, matiere_id),
            )
            _link_matiere_to_reception(conn, matiere_id, code_barre, fournisseur_fsc_id)
            conn.commit()
        except HTTPException:
            conn.rollback()
            raise

        row = conn.execute(
            "SELECT * FROM fab_matieres_utilisees WHERE id=?", (matiere_id,)
        ).fetchone()

    log_action(
        user=user,
        action="UPDATE",
        module="fabrication",
        objet=f"Matière #{matiere_id} modifiée",
        detail={"no_dossier": ex["no_dossier"], "code_barre": code_barre},
        ip=request.client.host if request.client else None,
    )
    return {"success": True, "matiere": dict(row) if row else {}}


@router.delete("/api/fabrication/matieres/{matiere_id}")
async def delete_matiere(matiere_id: int, request: Request):
    """Supprime un scan de matière."""
    user = get_current_user(request)
    _check_fab_access(user)

    # Opérateur : operateur_lie si défini, sinon nom de l'utilisateur
    operateur = user.get("operateur_lie") or ""
    if not operateur:
        operateur = user.get("nom") or ""

    with get_db() as conn:
        ex = conn.execute(
            "SELECT * FROM fab_matieres_utilisees WHERE id=?", (matiere_id,)
        ).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Scan non trouvé")
        if not _can_edit_matiere_scan(user, dict(ex), operateur):
            raise HTTPException(status_code=403, detail="Non autorisé")

        conn.execute("DELETE FROM fab_matieres_utilisees WHERE id=?", (matiere_id,))
        conn.commit()

    log_action(
        user=user,
        action="DELETE",
        module="fabrication",
        objet=f"Matière #{matiere_id} supprimée",
        detail={"no_dossier": ex["no_dossier"], "code_barre": ex["code_barre"]},
        ip=request.client.host if request.client else None,
    )
    return {"success": True}


@router.get("/api/fabrication/traceability")
def get_traceability(request: Request, no_dossier: str = None, machine_id: int = None):
    """Vue traçabilité : dossiers avec matières utilisées + infos production."""
    user = get_current_user(request)
    _check_fab_access(user)

    with get_db() as conn:
        if no_dossier:
            # Détail d'un dossier
            pe_row = conn.execute(
                """SELECT pe.*, m.nom AS machine_nom FROM planning_entries pe
                   LEFT JOIN machines m ON m.id = pe.machine_id
                   WHERE pe.reference = ?""",
                (no_dossier,),
            ).fetchone()
            dossier = dict(pe_row) if pe_row else None

            matieres = conn.execute(
                """SELECT * FROM fab_matieres_utilisees WHERE no_dossier = ?
                   ORDER BY scanned_at ASC""",
                (no_dossier,),
            ).fetchall()

            prod_rows = conn.execute(
                """SELECT operateur, date_operation, operation_code, machine,
                          metrage_prevu, metrage_reel, quantite_traitee
                   FROM production_data
                   WHERE no_dossier = ?
                   ORDER BY date_operation ASC, id ASC""",
                (no_dossier,),
            ).fetchall()

            return {
                "dossier": dossier,
                "matieres": [dict(r) for r in matieres],
                "production": [dict(r) for r in prod_rows],
            }
        else:
            # Liste des dossiers avec au moins une saisie ou matière
            mid = user.get("machine_id") or machine_id
            where = "1=1"
            params: list = []
            if mid and not is_admin(user):
                where = "pe.machine_id = ?"
                params.append(mid)
            elif mid:
                where = "pe.machine_id = ?"
                params.append(mid)

            rows = conn.execute(
                f"""SELECT pe.reference, pe.client, pe.description AS designation, pe.statut,
                           pe.date_livraison, m.nom AS machine_nom,
                           (SELECT COUNT(*) FROM fab_matieres_utilisees fmu
                            WHERE fmu.no_dossier = pe.reference) AS nb_matieres,
                           (SELECT COUNT(*) FROM production_data pd
                            WHERE pd.no_dossier = pe.reference AND pd.operation_code='89') AS nb_fins
                    FROM planning_entries pe
                    LEFT JOIN machines m ON m.id = pe.machine_id
                    WHERE {where}
                    ORDER BY pe.position ASC""",
                params,
            ).fetchall()

            return {"dossiers": [dict(r) for r in rows]}


@router.put("/api/fabrication/saisie/{saisie_id}/commentaire")
async def update_commentaire(saisie_id: int, request: Request):
    """Ajoute ou modifie le commentaire d'une saisie existante."""
    user = get_current_user(request)
    _check_fab_access(user)

    body = await request.json()
    commentaire = (body.get("commentaire") or "").strip() or None

    with get_db() as conn:
        ex = conn.execute(
            "SELECT * FROM production_data WHERE id=?", (saisie_id,)
        ).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Saisie non trouvée")

        # Opérateur : operateur_lie si défini, sinon nom de l'utilisateur
        user_operateur = user.get("operateur_lie") or user.get("nom") or ""
        if not is_admin(user) and ex["operateur"] != user_operateur:
            raise HTTPException(status_code=403, detail="Non autorisé")

        # Commentaire seul : ne pas renseigner modifie_* (badge « Corrigé » réservé
        # aux modifications de données de production dans MyProd > Saisies).
        conn.execute(
            """UPDATE production_data SET commentaire=? WHERE id=?""",
            (commentaire, saisie_id),
        )
        conn.commit()

    log_action(
        user=user,
        action="UPDATE",
        module="fabrication",
        objet=f"Commentaire saisie #{saisie_id}",
        detail={"no_dossier": ex["no_dossier"], "operation_code": ex["operation_code"]},
        ip=request.client.host if request.client else None,
    )
    return {"success": True}

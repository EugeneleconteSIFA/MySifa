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

def _can_edit_matiere_scan(
    user: dict, row: dict, operateur_courant: str, *, from_tracabilite: bool = False
) -> bool:
    """Correction traçabilité : admin, auteur du scan, ou même machine que l'utilisateur."""
    if is_admin(user):
        return True
    if from_tracabilite and is_fabrication(user):
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


def _resolve_fournisseur_fsc_id(conn, fournisseur_fsc_id, fournisseur_manual: str | None) -> int | None:
    """Retrouve un fournisseur FSC à partir de son id ou du nom déjà lié manuellement."""
    if fournisseur_fsc_id is not None:
        try:
            return int(fournisseur_fsc_id)
        except (TypeError, ValueError):
            return None
    nom = (fournisseur_manual or "").strip()
    if not nom:
        return None
    row = conn.execute(
        "SELECT id FROM fournisseurs_fsc WHERE trim(nom)=trim(?) LIMIT 1",
        (nom,),
    ).fetchone()
    return int(row["id"]) if row else None


def _check_fab_access(user: dict):
    """Fabrication OU admin autorisé pour cette API."""
    if not (is_fabrication(user) or is_admin(user)):
        raise HTTPException(status_code=403, detail="Accès réservé au service Fabrication")


def _today_prefix() -> str:
    return date.today().isoformat()


def _enrich_saisies_client(conn, saisies: list) -> None:
    """Complète client depuis planning_entries si absent sur la saisie."""
    missing_refs = {
        (s.get("no_dossier") or "").strip()
        for s in saisies
        if (s.get("no_dossier") or "").strip() and not (s.get("client") or "").strip()
    }
    if not missing_refs:
        return
    placeholders = ",".join("?" * len(missing_refs))
    rows = conn.execute(
        f"""SELECT trim(reference) AS reference, client
            FROM planning_entries
            WHERE trim(reference) IN ({placeholders})""",
        list(missing_refs),
    ).fetchall()
    client_map = {
        (r["reference"] or "").strip(): (r["client"] or "").strip()
        for r in rows
        if (r["client"] or "").strip()
    }
    for s in saisies:
        if (s.get("client") or "").strip():
            continue
        ref = (s.get("no_dossier") or "").strip()
        if ref in client_map:
            s["client"] = client_map[ref]


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
        _enrich_saisies_client(conn, saisies)
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
        saisies = [dict(r) for r in rows]
        _enrich_saisies_client(conn, saisies)
    return {"saisies": saisies}


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
                            """UPDATE planning_entries SET statut='termine', statut_force=1,
                                   updated_at=?
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

FSC_CLAIM_HIERARCHY = {
    "fsc_100": {"fsc_100"},
    "fsc_mix": {"fsc_100", "fsc_mix_credit", "fsc_mix"},
    "fsc_recycled": {"fsc_100", "fsc_recycled"},
}

_FSC_TYPE_LABELS = {
    "fsc_100": "FSC 100%",
    "fsc_mix": "FSC Mix",
    "fsc_recycled": "FSC Recycled",
}


def _fsc_type_label(fsc_type: str) -> str:
    t = (fsc_type or "").strip()
    return _FSC_TYPE_LABELS.get(t, t.replace("_", " ").upper() if t else "FSC")


def _check_fsc_compatibility(dossier_fsc_type: str, bobine_fsc_type: str | None) -> bool:
    """True si la bobine est compatible avec le type FSC requis sur le dossier."""
    if not bobine_fsc_type or bobine_fsc_type == "non_fsc":
        return False
    allowed = FSC_CLAIM_HIERARCHY.get((dossier_fsc_type or "").strip(), set())
    return bobine_fsc_type in allowed


def _bobine_fsc_type_for_matiere(conn, matiere_id: int) -> str:
    row = conn.execute(
        """SELECT COALESCE(sr.fsc_type_claim, 'non_fsc') AS bobine_fsc_type
           FROM fab_matieres_utilisees fmu
           LEFT JOIN stock_receptions sr ON sr.id = fmu.reception_id
           WHERE fmu.id=?""",
        (matiere_id,),
    ).fetchone()
    return (row["bobine_fsc_type"] if row else None) or "non_fsc"


def _fetch_matiere_row(conn, matiere_id: int) -> dict | None:
    row = conn.execute(
        """SELECT
             fmu.*,
             sr.id AS reception_id_found,
             COALESCE(sr.fournisseur, fmu.fournisseur_manual) AS fournisseur,
             COALESCE(sr.certificat_fsc, fmu.certificat_fsc_manual) AS certificat_fsc,
             ff.licence AS fournisseur_licence,
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
           LEFT JOIN fournisseurs_fsc ff
             ON ff.nom = COALESCE(sr.fournisseur, fmu.fournisseur_manual)
           WHERE fmu.id=?""",
        (matiere_id,),
    ).fetchone()
    if not row:
        return None
    d = dict(row)
    if d.get("reception_id_found"):
        d["reception_id"] = d.get("reception_id_found")
        d["liaison_mode"] = "reception"
    else:
        d["liaison_mode"] = d.get("liaison_mode_resolved") or d.get("liaison_mode")
    d.pop("reception_id_found", None)
    d.pop("liaison_mode_resolved", None)
    return d


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
              ff.licence AS fournisseur_licence,
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
            LEFT JOIN fournisseurs_fsc ff
              ON ff.nom = COALESCE(sr.fournisseur, fmu.fournisseur_manual)
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


@router.get("/api/fabrication/tracabilite/{no_dossier}")
def get_tracabilite_dossier(no_dossier: str, request: Request):
    """Rapport de traçabilité FSC complet pour un dossier."""
    user = get_current_user(request)
    _check_fab_access(user)

    ref = (no_dossier or "").strip()
    if not ref:
        raise HTTPException(status_code=400, detail="Référence dossier manquante")

    with get_db() as conn:
        entry = conn.execute(
            """SELECT pe.reference, pe.client, pe.description, pe.statut, pe.machine_id,
                      pe.fsc_requis, pe.fsc_type_requis, pe.date_livraison, pe.numero_of,
                      m.nom AS machine_nom
               FROM planning_entries pe
               LEFT JOIN machines m ON m.id = pe.machine_id
               WHERE pe.reference=? LIMIT 1""",
            (ref,),
        ).fetchone()

        rows = conn.execute(
            """SELECT
                 fmu.id, fmu.code_barre, fmu.scanned_at, fmu.operateur,
                 fmu.machine_nom, fmu.liaison_mode,
                 fmu.fsc_warning, fmu.fsc_warning_note,
                 COALESCE(sr.fournisseur, fmu.fournisseur_manual) AS fournisseur,
                 COALESCE(sr.certificat_fsc, fmu.certificat_fsc_manual) AS certificat_fsc,
                 COALESCE(sr.fsc_type_claim, NULL) AS fsc_type_claim,
                 sr.id AS reception_id,
                 sr.created_at AS reception_date,
                 ff.licence AS fournisseur_licence,
                 ff.certificat AS fournisseur_certificat
               FROM fab_matieres_utilisees fmu
               LEFT JOIN stock_receptions sr ON sr.id = (
                   SELECT i.reception_id FROM stock_reception_items i
                   WHERE trim(i.code_barre) = trim(fmu.code_barre)
                   ORDER BY i.scanned_at DESC, i.id DESC
                   LIMIT 1
               )
               LEFT JOIN fournisseurs_fsc ff
                 ON ff.nom = COALESCE(sr.fournisseur, fmu.fournisseur_manual)
               WHERE fmu.no_dossier = ?
               ORDER BY fmu.scanned_at ASC""",
            (ref,),
        ).fetchall()

    fsc_requis = int(entry["fsc_requis"]) if entry and entry["fsc_requis"] else 0
    fsc_type_requis = (entry["fsc_type_requis"] if entry else None) or ""

    bobines = []
    nb_conformes = 0
    for r in rows:
        d = dict(r)
        if fsc_requis:
            bobine_claim = d.get("fsc_type_claim")
            conforme = _check_fsc_compatibility(fsc_type_requis, bobine_claim)
            d["fsc_conforme"] = conforme
            if conforme:
                nb_conformes += 1
        else:
            d["fsc_conforme"] = None
        bobines.append(d)

    nb_total = len(bobines)
    if fsc_requis and nb_total > 0:
        statut_global = "conforme" if nb_conformes == nb_total else "non_conforme"
    elif fsc_requis and nb_total == 0:
        statut_global = "en_attente"
    else:
        statut_global = "non_applicable"

    dossier_out = dict(entry) if entry else {"reference": ref}
    if not entry and _is_fictif_dossier(ref):
        dossier_out = _build_fictif_dossier_dict(ref, None)

    return {
        "dossier": dossier_out,
        "bobines": bobines,
        "synthese": {
            "nb_bobines_total": nb_total,
            "nb_bobines_fsc_conformes": nb_conformes if fsc_requis else None,
            "nb_bobines_non_conformes": (nb_total - nb_conformes) if fsc_requis else None,
            "statut_global": statut_global,
            "genere_a": datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S"),
        },
    }


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
            SELECT r.id AS reception_id, r.fournisseur, r.certificat_fsc, r.fsc_type_claim,
                   ff.licence AS fournisseur_licence
            FROM stock_reception_items i
            JOIN stock_receptions r ON r.id = i.reception_id
            LEFT JOIN fournisseurs_fsc ff ON ff.nom = r.fournisseur
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
        "fsc_type_claim": d.get("fsc_type_claim") or "non_fsc",
        "fournisseur_licence": d.get("fournisseur_licence") or "",
    }


@router.post("/api/fabrication/matieres")
async def add_matiere(request: Request):
    """Enregistre un scan de code barre matière. Lié à la machine + dossier actif."""
    user = get_current_user(request)
    _check_fab_access(user)

    body = await request.json()

    # Confirmation d'une alerte FSC sur un scan déjà créé
    if body.get("fsc_warning_confirmed"):
        try:
            matiere_id_confirm = int(body.get("matiere_id"))
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Identifiant matière invalide")
        note = (body.get("fsc_warning_note") or "").strip()
        if not note:
            raise HTTPException(
                status_code=400,
                detail="Raison de l'utilisation obligatoire.",
            )
        with get_db() as conn:
            ex = conn.execute(
                "SELECT id FROM fab_matieres_utilisees WHERE id=?",
                (matiere_id_confirm,),
            ).fetchone()
            if not ex:
                raise HTTPException(status_code=404, detail="Scan introuvable")
            conn.execute(
                """UPDATE fab_matieres_utilisees
                   SET fsc_warning=1, fsc_warning_note=?
                   WHERE id=?""",
                (note, matiere_id_confirm),
            )
            conn.commit()
            d = _fetch_matiere_row(conn, matiere_id_confirm)
        return {
            "success": True,
            "id": matiere_id_confirm,
            "matiere": d,
            "warning": False,
            "warning_message": None,
        }

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

        try:
            conn.execute("BEGIN")
            cursor = conn.execute(
                """INSERT INTO fab_matieres_utilisees
                   (machine_id, machine_nom, operateur, no_dossier, code_barre, scanned_at)
                   VALUES (?,?,?,?,?,?)""",
                (machine_id_resolved, machine_name, operateur, no_dossier, code_barre, scanned_at),
            )
            new_id = cursor.lastrowid
            fid = _resolve_fournisseur_fsc_id(conn, fournisseur_fsc_id, None)
            _link_matiere_to_reception(conn, new_id, code_barre, fid)

            fsc_warning = False
            fsc_warning_message = None
            if no_dossier:
                entry = conn.execute(
                    """SELECT fsc_requis, fsc_type_requis FROM planning_entries
                       WHERE reference=? LIMIT 1""",
                    (no_dossier,),
                ).fetchone()
                if entry and entry["fsc_requis"]:
                    dossier_type = (entry["fsc_type_requis"] or "").strip()
                    if dossier_type:
                        bobine_fsc = _bobine_fsc_type_for_matiere(conn, new_id)
                        if not _check_fsc_compatibility(dossier_type, bobine_fsc):
                            label = _fsc_type_label(dossier_type)
                            fsc_warning = True
                            fsc_warning_message = (
                                f"Cette bobine ({code_barre}) n'est pas certifiée {label}. "
                                f"Le dossier {no_dossier} requiert une certification {label}."
                            )

            conn.commit()
        except HTTPException:
            conn.rollback()
            raise
        except Exception:
            conn.rollback()
            raise

        d = _fetch_matiere_row(conn, new_id) or {}

    return {
        "success": True,
        "id": new_id,
        "matiere": d,
        "warning": fsc_warning,
        "warning_message": fsc_warning_message,
    }


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

    from_tracabilite = bool(body.get("tracabilite"))
    fournisseur_fsc_id = body.get("fournisseur_fsc_id")

    operateur = user.get("operateur_lie") or ""
    if not operateur:
        operateur = user.get("nom") or ""

    with get_db() as conn:
        ex = conn.execute(
            "SELECT * FROM fab_matieres_utilisees WHERE id=?", (matiere_id,)
        ).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Scan non trouvé")
        if not _can_edit_matiere_scan(
            user, dict(ex), operateur, from_tracabilite=from_tracabilite
        ):
            raise HTTPException(status_code=403, detail="Non autorisé")

        exd = dict(ex)
        prev_code = (exd.get("code_barre") or "").strip()
        fid = _resolve_fournisseur_fsc_id(
            conn, fournisseur_fsc_id, exd.get("fournisseur_manual")
        )

        if prev_code == code_barre and fid is None:
            return {"success": True, "matiere": exd}

        try:
            conn.execute("BEGIN")
            if prev_code != code_barre:
                conn.execute(
                    "UPDATE fab_matieres_utilisees SET code_barre=? WHERE id=?",
                    (code_barre, matiere_id),
                )
            _link_matiere_to_reception(conn, matiere_id, code_barre, fid)
            conn.commit()
        except HTTPException:
            conn.rollback()
            raise
        except Exception:
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
async def delete_matiere(matiere_id: int, request: Request, tracabilite: bool = False):
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
        if not _can_edit_matiere_scan(
            user, dict(ex), operateur, from_tracabilite=tracabilite
        ):
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
                f"""SELECT pe.id, pe.reference, pe.client, pe.description AS designation, pe.statut,
                           pe.position, pe.date_livraison, m.nom AS machine_nom,
                           pe.fsc_requis, pe.fsc_type_requis,
                           (SELECT COUNT(*) FROM fab_matieres_utilisees fmu
                            WHERE fmu.no_dossier = pe.reference) AS nb_matieres,
                           (SELECT COUNT(*) FROM production_data pd
                            WHERE pd.no_dossier = pe.reference AND pd.operation_code='89') AS nb_fins
                    FROM planning_entries pe
                    LEFT JOIN machines m ON m.id = pe.machine_id
                    WHERE {where}
                    ORDER BY pe.position DESC""",
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

# ─── Endpoints repiquage (code 03 sur machine Repiquage) ──────────────────────


def _is_machine_repiquage(name) -> bool:
    n = (str(name or "")).lower().strip()
    n = (n.replace("é", "e").replace("è", "e").replace("ê", "e")
          .replace("à", "a").replace("â", "a")
          .replace("î", "i").replace("ô", "o"))
    # Forme NFC simple (les accents passent aussi via chars composes)
    n = n.replace("é", "e").replace("è", "e").replace("ê", "e")
    n = n.replace("à", "a").replace("â", "a")
    n = n.replace("î", "i").replace("ô", "o")
    return n == "repiquage" or n == "rep" or n.startswith("rep ")


@router.patch("/api/fabrication/saisie/{saisie_id}/repiquage")
async def update_saisie_repiquage(saisie_id: int, request: Request):
    """Modifie qte etiquettes + commentaire d'une saisie repiquage (code 03 sur machine Repiquage).

    Reserve a l'auteur de la saisie (ou admin). Refuse les autres saisies.
    """
    user = get_current_user(request)
    _check_fab_access(user)

    body = await request.json()
    qte_raw = body.get("qte_etiquettes")
    commentaire = (body.get("commentaire") or "").strip() or None

    try:
        qte = float(str(qte_raw).replace(",", ".")) if qte_raw not in (None, "", "null") else None
    except Exception:
        raise HTTPException(status_code=400, detail="Quantite d'etiquettes invalide")
    if qte is None or qte < 0:
        raise HTTPException(status_code=400, detail="Quantite d'etiquettes invalide")

    with get_db() as conn:
        ex = conn.execute(
            "SELECT * FROM production_data WHERE id=?", (saisie_id,)
        ).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Saisie non trouvee")
        op_code = (ex["operation_code"] or "").strip()
        if op_code != "03" or not _is_machine_repiquage(ex["machine"]):
            raise HTTPException(
                status_code=400,
                detail="Cet endpoint est reserve aux saisies repiquage (code 03 sur machine Repiquage)",
            )

        user_operateur = user.get("operateur_lie") or user.get("nom") or ""
        if not is_admin(user) and ex["operateur"] != user_operateur:
            raise HTTPException(status_code=403, detail="Non autorise")

        now_iso = datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")
        conn.execute(
            """UPDATE production_data
               SET quantite_traitee=?, commentaire=?,
                   modifie_par=?, modifie_le=?, modifie_note=?
               WHERE id=?""",
            (
                qte,
                commentaire,
                user.get("nom") or user.get("email") or "",
                now_iso,
                "Modification saisie repiquage",
                saisie_id,
            ),
        )
        conn.commit()

    log_action(
        user=user,
        action="UPDATE",
        module="fabrication",
        objet=f"Saisie repiquage #{saisie_id} modifiee",
        detail={"no_dossier": ex["no_dossier"], "qte_etiquettes": qte},
        ip=request.client.host if request.client else None,
    )
    return {"success": True}


@router.delete("/api/fabrication/saisie/{saisie_id}/repiquage")
def delete_saisie_repiquage(saisie_id: int, request: Request):
    """Supprime une saisie repiquage (code 03 sur machine Repiquage).

    Reserve a l'auteur de la saisie (ou admin). Refuse les autres saisies.
    """
    user = get_current_user(request)
    _check_fab_access(user)

    with get_db() as conn:
        ex = conn.execute(
            "SELECT * FROM production_data WHERE id=?", (saisie_id,)
        ).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Saisie non trouvee")
        op_code = (ex["operation_code"] or "").strip()
        if op_code != "03" or not _is_machine_repiquage(ex["machine"]):
            raise HTTPException(
                status_code=400,
                detail="Cet endpoint est reserve aux saisies repiquage (code 03 sur machine Repiquage)",
            )

        user_operateur = user.get("operateur_lie") or user.get("nom") or ""
        if not is_admin(user) and ex["operateur"] != user_operateur:
            raise HTTPException(status_code=403, detail="Non autorise")

        conn.execute("DELETE FROM production_data WHERE id=?", (saisie_id,))
        conn.commit()

    log_action(
        user=user,
        action="DELETE",
        module="fabrication",
        objet=f"Saisie repiquage #{saisie_id} supprimee",
        detail={"no_dossier": ex["no_dossier"]},
        ip=request.client.host if request.client else None,
    )
    return {"success": True}


# -- Helpers compteur cartons repiquage --------------------------------------

# Filtre SQL pour ne considerer que les saisies repiquage (toutes variantes
# de nom de machine "Repiquage" / "rep" / etc.) Evite que des saisies code 03
# d'autres machines polluent les compteurs.
_REP_MACHINE_FILTER = (
    "(lower(trim(COALESCE(machine,''))) LIKE 'repiquage%' "
    "OR lower(trim(COALESCE(machine,''))) = 'rep' "
    "OR lower(trim(COALESCE(machine,''))) LIKE 'rep %')"
)


def _rep_get_equipe_members(conn, operateur: str):
    """Renvoie la liste des noms d'operateurs de l'equipe matin/aprem
    a laquelle appartient `operateur` aujourd'hui sur la machine Repiquage.

    Lit rh_planning_postes pour la semaine ISO en cours, machine 'Repiquage',
    et retourne la liste des user_nom du meme creneau (matin ou aprem) que
    l'operateur, le jour de la semaine etant inclus dans le bitmask `jours`.

    Renvoie None si l'operateur n'est pas trouve dans le planning (fallback).
    """
    if not operateur:
        return None
    today = date.today()
    try:
        iso_year, iso_week, iso_weekday = today.isocalendar()
    except (ValueError, AttributeError):
        return None
    semaine = f"{iso_year}-W{iso_week:02d}"
    day_bit = 1 << (iso_weekday - 1)  # 1..7, Lun=bit0

    # Trouver le machine_id Repiquage
    mach = conn.execute(
        "SELECT id FROM machines WHERE actif=1 AND ("
        "lower(trim(COALESCE(nom,''))) LIKE 'repiquage%' "
        "OR lower(trim(COALESCE(nom,''))) = 'rep')"
    ).fetchone()
    if not mach:
        return None
    repiquage_machine_id = int(mach["id"])

    # 1) Trouver le creneau de l'operateur courant
    row = conn.execute(
        """SELECT p.creneau, p.jours
           FROM rh_planning_postes p
           JOIN users u ON u.id = p.user_id
           WHERE p.semaine = ? AND p.machine_id = ?
             AND trim(lower(u.nom)) = trim(lower(?))""",
        (semaine, repiquage_machine_id, operateur),
    ).fetchone()
    if not row:
        return None
    creneau = (row["creneau"] or "").strip()
    jours = int(row["jours"] or 0)
    if not (jours & day_bit):
        return None  # operateur present cette semaine mais pas ce jour

    # 2) Lister les operateurs sur le meme creneau ce jour-la
    members = conn.execute(
        """SELECT DISTINCT u.nom
           FROM rh_planning_postes p
           JOIN users u ON u.id = p.user_id
           WHERE p.semaine = ? AND p.machine_id = ?
             AND p.creneau = ?
             AND (p.jours & ?) != 0""",
        (semaine, repiquage_machine_id, creneau, day_bit),
    ).fetchall()
    noms = [m["nom"] for m in members if m["nom"]]
    if not noms:
        return None
    return noms


def _rep_today_isoformat() -> str:
    return datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")


def _rep_get_carton_courant(conn, no_dossier: str, operateur: str) -> int:
    row = conn.execute(
        "SELECT nb_etiquettes FROM repiquage_carton_courant "
        "WHERE no_dossier=? AND operateur=?",
        (no_dossier, operateur),
    ).fetchone()
    return int(row["nb_etiquettes"]) if row else 0


def _rep_set_carton_courant(conn, no_dossier: str, operateur: str, nb: int) -> None:
    now = _rep_today_isoformat()
    if nb <= 0:
        conn.execute(
            "DELETE FROM repiquage_carton_courant "
            "WHERE no_dossier=? AND operateur=?",
            (no_dossier, operateur),
        )
        return
    conn.execute(
        """INSERT INTO repiquage_carton_courant
              (no_dossier, operateur, nb_etiquettes, updated_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(no_dossier, operateur) DO UPDATE SET
              nb_etiquettes=excluded.nb_etiquettes,
              updated_at=excluded.updated_at""",
        (no_dossier, operateur, int(nb), now),
    )


def _rep_get_etiq_par_carton(conn, no_dossier: str):
    row = conn.execute(
        "SELECT etiquettes_par_carton FROM planning_entries "
        "WHERE trim(reference) = trim(?) LIMIT 1",
        (no_dossier,),
    ).fetchone()
    if not row or row["etiquettes_par_carton"] is None:
        return None
    try:
        v = int(row["etiquettes_par_carton"])
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None


def _rep_get_or_create_saisie_03(conn, operateur: str, no_dossier: str, machine_name: str):
    today = _today_prefix()
    today_fr = date.today().strftime("%d/%m/%Y")
    sql = (
        "SELECT * FROM production_data "
        "WHERE trim(operateur)=trim(?) AND trim(no_dossier)=trim(?) "
        "  AND operation_code='03' AND " + _REP_MACHINE_FILTER + " "
        "  AND (date_operation LIKE ? OR date_operation LIKE ?) "
        "ORDER BY id DESC LIMIT 1"
    )
    row = conn.execute(sql, (operateur, no_dossier, today + "%", today_fr + "%")).fetchone()
    if row:
        return dict(row)

    pe_row = conn.execute(
        "SELECT client, description FROM planning_entries "
        "WHERE trim(reference)=trim(?) LIMIT 1",
        (no_dossier,),
    ).fetchone()
    client = (pe_row["client"] if pe_row else None) or None
    designation = (pe_row["description"] if pe_row else None) or None

    now_iso = _rep_today_isoformat()
    cur = conn.execute(
        """INSERT INTO production_data
           (operateur, date_operation, operation, operation_code,
            operation_severity, operation_category, machine,
            no_dossier, client, designation,
            quantite_a_traiter, quantite_traitee, nb_cartons,
            service, data, est_manuel)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
        (
            operateur, now_iso, "03 - Production", "03",
            "info", "production", machine_name,
            no_dossier, client, designation,
            0, 0, 0,
            "fabrication",
            json.dumps(
                {"operateur": operateur, "no_dossier": no_dossier,
                 "machine": machine_name, "source": "repiquage"},
                default=str,
            ),
        ),
    )
    new_id = cur.lastrowid
    return {
        "id": new_id,
        "operateur": operateur,
        "no_dossier": no_dossier,
        "machine": machine_name,
        "quantite_traitee": 0,
        "nb_cartons": 0,
    }


def _rep_increment_saisie_03(conn, saisie_id: int, delta_etiq: int, delta_cartons: int) -> None:
    if delta_etiq == 0 and delta_cartons == 0:
        return
    now_iso = _rep_today_isoformat()
    conn.execute(
        """UPDATE production_data
           SET quantite_traitee = COALESCE(quantite_traitee, 0) + ?,
               nb_cartons = COALESCE(nb_cartons, 0) + ?,
               modifie_le = ?
           WHERE id=?""",
        (delta_etiq, delta_cartons, now_iso, saisie_id),
    )


def _rep_aggregate(conn, no_dossier: str, operateur: str, today_only: bool):
    """Renvoie (nb_cartons, qte_etiq) sur le dossier - machine Repiquage.

    Compteur "jour" : limite a l'equipe (matin/aprem) de l'operateur courant
    via le planning_rh. Fallback : tous operateurs si l'operateur n'est pas
    trouve dans le planning ce jour-la.
    Compteur "cumul" : toutes dates, tous operateurs.
    Garanti par construction : Jour <= Cumul.
    """
    today = _today_prefix()
    today_fr = date.today().strftime("%d/%m/%Y")
    if today_only:
        equipe = _rep_get_equipe_members(conn, operateur)
        if equipe:
            placeholders = ",".join(["?"] * len(equipe))
            sql = (
                "SELECT COALESCE(SUM(nb_cartons),0) AS c, "
                "       COALESCE(SUM(quantite_traitee),0) AS e "
                "FROM production_data "
                "WHERE trim(no_dossier)=trim(?) AND operation_code='03' "
                "  AND " + _REP_MACHINE_FILTER + " "
                "  AND (date_operation LIKE ? OR date_operation LIKE ?) "
                "  AND trim(lower(operateur)) IN (" + placeholders + ")"
            )
            params = [no_dossier, today + "%", today_fr + "%"]
            params.extend([str(n).strip().lower() for n in equipe])
            row = conn.execute(sql, params).fetchone()
        else:
            # Fallback : pas d'equipe identifiee, on prend tout le jour
            sql = (
                "SELECT COALESCE(SUM(nb_cartons),0) AS c, "
                "       COALESCE(SUM(quantite_traitee),0) AS e "
                "FROM production_data "
                "WHERE trim(no_dossier)=trim(?) AND operation_code='03' "
                "  AND " + _REP_MACHINE_FILTER + " "
                "  AND (date_operation LIKE ? OR date_operation LIKE ?)"
            )
            row = conn.execute(sql, (no_dossier, today + "%", today_fr + "%")).fetchone()
    else:
        sql = (
            "SELECT COALESCE(SUM(nb_cartons),0) AS c, "
            "       COALESCE(SUM(quantite_traitee),0) AS e "
            "FROM production_data "
            "WHERE trim(no_dossier)=trim(?) AND operation_code='03' "
            "  AND " + _REP_MACHINE_FILTER
        )
        row = conn.execute(sql, (no_dossier,)).fetchone()
    return int(row["c"] or 0), int(row["e"] or 0)


def _rep_operateur(user: dict) -> str:
    op = (user.get("operateur_lie") or "").strip()
    if not op:
        op = (user.get("nom") or "").strip()
    if not op:
        raise HTTPException(
            status_code=400,
            detail="Compte sans nom — contactez un administrateur",
        )
    return op


# -- Endpoints compteur cartons repiquage ------------------------------------

@router.get("/api/fabrication/repiquage/carton-courant")
def get_carton_courant(request: Request, no_dossier: str):
    """Renvoie l'etat du carton courant + agregats jour/cumul pour ce dossier."""
    user = get_current_user(request)
    _check_fab_access(user)
    no_dossier = (no_dossier or "").strip()
    if not no_dossier:
        raise HTTPException(400, "no_dossier requis")

    operateur = _rep_operateur(user)
    with get_db() as conn:
        nb_courant = _rep_get_carton_courant(conn, no_dossier, operateur)
        etiq_par_carton = _rep_get_etiq_par_carton(conn, no_dossier)
        jour_c, jour_e = _rep_aggregate(conn, no_dossier, operateur, today_only=True)
        cum_c, cum_e = _rep_aggregate(conn, no_dossier, operateur, today_only=False)
        pe = conn.execute(
            "SELECT reference, client, description "
            "FROM planning_entries WHERE trim(reference)=trim(?) LIMIT 1",
            (no_dossier,),
        ).fetchone()
        dossier_info = dict(pe) if pe else None

    return {
        "no_dossier": no_dossier,
        "operateur": operateur,
        "nb_etiquettes_courant": nb_courant,
        "etiquettes_par_carton": etiq_par_carton,
        "jour": {"nb_cartons": jour_c, "qte_etiq": jour_e},
        "cumul": {"nb_cartons": cum_c, "qte_etiq": cum_e},
        "dossier": dossier_info,
    }


@router.post("/api/fabrication/repiquage/incrementer-carton-courant")
async def incrementer_carton_courant(request: Request):
    """Ajoute N etiquettes dans le carton courant.

    Si le total atteint/depasse `etiquettes_par_carton`, ferme automatiquement
    les cartons complets et reporte le reliquat dans le nouveau carton courant.
    """
    user = get_current_user(request)
    _check_fab_access(user)
    body = await request.json()

    no_dossier = (body.get("no_dossier") or "").strip()
    if not no_dossier:
        raise HTTPException(400, "no_dossier requis")
    try:
        delta = int(body.get("delta") or 0)
    except (TypeError, ValueError):
        raise HTTPException(400, "delta invalide")
    if delta <= 0:
        raise HTTPException(400, "delta doit etre positif")

    operateur = _rep_operateur(user)
    with get_db() as conn:
        machine_obj = _resolve_machine(user, body, conn)
        etiq_par_carton = _rep_get_etiq_par_carton(conn, no_dossier)
        nb_courant = _rep_get_carton_courant(conn, no_dossier, operateur)
        new_total = nb_courant + delta

        if etiq_par_carton and etiq_par_carton > 0:
            nb_cartons_fermes = new_total // etiq_par_carton
            reliquat = new_total % etiq_par_carton
        else:
            # Pas de parametrage : on accumule sans jamais fermer auto
            nb_cartons_fermes = 0
            reliquat = new_total

        if nb_cartons_fermes > 0:
            saisie = _rep_get_or_create_saisie_03(
                conn, operateur, no_dossier, machine_obj["nom"]
            )
            _rep_increment_saisie_03(
                conn,
                saisie["id"],
                nb_cartons_fermes * (etiq_par_carton or 0),
                nb_cartons_fermes,
            )

        _rep_set_carton_courant(conn, no_dossier, operateur, reliquat)
        conn.commit()

        jour_c, jour_e = _rep_aggregate(conn, no_dossier, operateur, today_only=True)
        cum_c, cum_e = _rep_aggregate(conn, no_dossier, operateur, today_only=False)

    log_action(
        user=user,
        action="UPDATE",
        module="fabrication",
        objet=f"Repiquage +{delta} etiq dossier {no_dossier}",
        detail={
            "delta_etiq": delta,
            "cartons_fermes_auto": nb_cartons_fermes,
            "reliquat": reliquat,
        },
        ip=request.client.host if request.client else None,
    )
    return {
        "success": True,
        "nb_etiquettes_courant": reliquat,
        "cartons_fermes_auto": nb_cartons_fermes,
        "etiquettes_par_carton": etiq_par_carton,
        "jour": {"nb_cartons": jour_c, "qte_etiq": jour_e},
        "cumul": {"nb_cartons": cum_c, "qte_etiq": cum_e},
    }


@router.post("/api/fabrication/repiquage/ajouter-cartons-complets")
async def ajouter_cartons_complets(request: Request):
    """Ajoute N cartons complets a la saisie du jour sans toucher au carton courant.

    Correspond au geste "+1 carton" choisi "Continuer quand meme" dans le modal.
    Necessite que etiquettes_par_carton soit defini.
    """
    user = get_current_user(request)
    _check_fab_access(user)
    body = await request.json()

    no_dossier = (body.get("no_dossier") or "").strip()
    if not no_dossier:
        raise HTTPException(400, "no_dossier requis")
    try:
        nb = int(body.get("nb") or 0)
    except (TypeError, ValueError):
        raise HTTPException(400, "nb invalide")
    if nb <= 0:
        raise HTTPException(400, "nb doit etre positif")

    operateur = _rep_operateur(user)
    with get_db() as conn:
        machine_obj = _resolve_machine(user, body, conn)
        etiq_par_carton = _rep_get_etiq_par_carton(conn, no_dossier)
        if not etiq_par_carton or etiq_par_carton <= 0:
            raise HTTPException(
                400,
                "Parametrage 'etiquettes par carton' manquant pour ce dossier. "
                "Definissez-le avant d'utiliser ce mode.",
            )

        saisie = _rep_get_or_create_saisie_03(
            conn, operateur, no_dossier, machine_obj["nom"]
        )
        _rep_increment_saisie_03(
            conn, saisie["id"], nb * etiq_par_carton, nb,
        )
        conn.commit()

        nb_courant = _rep_get_carton_courant(conn, no_dossier, operateur)
        jour_c, jour_e = _rep_aggregate(conn, no_dossier, operateur, today_only=True)
        cum_c, cum_e = _rep_aggregate(conn, no_dossier, operateur, today_only=False)

    log_action(
        user=user,
        action="UPDATE",
        module="fabrication",
        objet=f"Repiquage +{nb} cartons dossier {no_dossier}",
        detail={"nb_cartons": nb, "etiq_par_carton": etiq_par_carton},
        ip=request.client.host if request.client else None,
    )
    return {
        "success": True,
        "nb_etiquettes_courant": nb_courant,
        "etiquettes_par_carton": etiq_par_carton,
        "jour": {"nb_cartons": jour_c, "qte_etiq": jour_e},
        "cumul": {"nb_cartons": cum_c, "qte_etiq": cum_e},
    }


@router.post("/api/fabrication/repiquage/fermer-carton-courant")
async def fermer_carton_courant(request: Request):
    """Ferme le carton courant en le considerant comme plein.

    Geste "+1 carton" choisi "Fermer le carton" dans le modal : l'operateur
    declare qu'il vient de finir les etiquettes manquantes. On ajoute le
    complement (etiquettes_par_carton - nb_courant) puis +1 carton ferme.
    Necessite que etiquettes_par_carton soit defini.
    """
    user = get_current_user(request)
    _check_fab_access(user)
    body = await request.json()

    no_dossier = (body.get("no_dossier") or "").strip()
    if not no_dossier:
        raise HTTPException(400, "no_dossier requis")

    operateur = _rep_operateur(user)
    with get_db() as conn:
        machine_obj = _resolve_machine(user, body, conn)
        etiq_par_carton = _rep_get_etiq_par_carton(conn, no_dossier)
        if not etiq_par_carton or etiq_par_carton <= 0:
            raise HTTPException(
                400,
                "Parametrage 'etiquettes par carton' manquant pour ce dossier.",
            )

        nb_courant = _rep_get_carton_courant(conn, no_dossier, operateur)
        if nb_courant >= etiq_par_carton:
            # Pathologique : courant >= seuil. On clipote a etiq_par_carton.
            nb_courant = etiq_par_carton

        delta_etiq_a_ajouter = etiq_par_carton  # total du carton ferme
        # Note : les nb_courant etiq deja "presentes" dans le courant viennent
        # uniquement d'incrementer-carton-courant qui ne les a PAS encore
        # comptees dans production_data. On les ajoute donc maintenant.

        saisie = _rep_get_or_create_saisie_03(
            conn, operateur, no_dossier, machine_obj["nom"]
        )
        _rep_increment_saisie_03(
            conn, saisie["id"], delta_etiq_a_ajouter, 1,
        )
        _rep_set_carton_courant(conn, no_dossier, operateur, 0)
        conn.commit()

        jour_c, jour_e = _rep_aggregate(conn, no_dossier, operateur, today_only=True)
        cum_c, cum_e = _rep_aggregate(conn, no_dossier, operateur, today_only=False)

    log_action(
        user=user,
        action="UPDATE",
        module="fabrication",
        objet=f"Repiquage fermeture carton dossier {no_dossier}",
        detail={
            "etiq_completees": etiq_par_carton - nb_courant,
            "nb_courant_avant": nb_courant,
            "etiq_par_carton": etiq_par_carton,
        },
        ip=request.client.host if request.client else None,
    )
    return {
        "success": True,
        "nb_etiquettes_courant": 0,
        "etiquettes_par_carton": etiq_par_carton,
        "jour": {"nb_cartons": jour_c, "qte_etiq": jour_e},
        "cumul": {"nb_cartons": cum_c, "qte_etiq": cum_e},
    }


@router.post("/api/fabrication/repiquage/retirer-carton-complet")
async def retirer_carton_complet(request: Request):
    """Retire 1 carton complet de la saisie du jour (geste -1 carton).

    Refuse si la saisie du jour est a 0 carton (rien a retirer).
    Decremente quantite_traitee et nb_cartons de la ligne 03 du jour.
    """
    user = get_current_user(request)
    _check_fab_access(user)
    body = await request.json()

    no_dossier = (body.get("no_dossier") or "").strip()
    if not no_dossier:
        raise HTTPException(400, "no_dossier requis")

    operateur = _rep_operateur(user)
    with get_db() as conn:
        machine_obj = _resolve_machine(user, body, conn)
        etiq_par_carton = _rep_get_etiq_par_carton(conn, no_dossier)
        if not etiq_par_carton or etiq_par_carton <= 0:
            raise HTTPException(
                400,
                "Parametrage 'etiquettes par carton' manquant pour ce dossier.",
            )

        today = _today_prefix()
        today_fr = date.today().strftime("%d/%m/%Y")
        sql_ret = (
            "SELECT id, nb_cartons, quantite_traitee FROM production_data "
            "WHERE trim(operateur)=trim(?) AND trim(no_dossier)=trim(?) "
            "  AND operation_code='03' AND " + _REP_MACHINE_FILTER + " "
            "  AND (date_operation LIKE ? OR date_operation LIKE ?) "
            "ORDER BY id DESC LIMIT 1"
        )
        row = conn.execute(
            sql_ret, (operateur, no_dossier, today + "%", today_fr + "%")
        ).fetchone()
        if not row or int(row["nb_cartons"] or 0) <= 0:
            raise HTTPException(
                400,
                "Aucun carton a retirer aujourd'hui pour ce dossier.",
            )

        _rep_increment_saisie_03(
            conn, int(row["id"]), -etiq_par_carton, -1,
        )
        conn.commit()

        nb_courant = _rep_get_carton_courant(conn, no_dossier, operateur)
        jour_c, jour_e = _rep_aggregate(conn, no_dossier, operateur, today_only=True)
        cum_c, cum_e = _rep_aggregate(conn, no_dossier, operateur, today_only=False)

    log_action(
        user=user,
        action="UPDATE",
        module="fabrication",
        objet=f"Repiquage -1 carton dossier {no_dossier}",
        detail={"etiq_retirees": etiq_par_carton},
        ip=request.client.host if request.client else None,
    )
    return {
        "success": True,
        "nb_etiquettes_courant": nb_courant,
        "etiquettes_par_carton": etiq_par_carton,
        "jour": {"nb_cartons": jour_c, "qte_etiq": jour_e},
        "cumul": {"nb_cartons": cum_c, "qte_etiq": cum_e},
    }


@router.post("/api/fabrication/repiquage/ajuster-compteur")
async def ajuster_compteur(request: Request):
    """Ajuste manuellement le compteur jour ou cumul (admin uniquement).

    Body : {no_dossier, scope: 'jour'|'cumul', nb_cartons_cible: int}
    - scope='jour'  : ajuste la saisie 03 du jour de l'operateur (modifie ses cartons)
    - scope='cumul' : cree une ligne d'ajustement (positif ou negatif) datee
                       d'aujourd'hui pour atteindre la valeur cible sur le dossier.

    L'ajustement est trace via une saisie 03 marquee dans le commentaire.
    """
    user = get_current_user(request)
    if not is_admin(user):
        raise HTTPException(403, "Reserve aux administrateurs")
    body = await request.json()

    no_dossier = (body.get("no_dossier") or "").strip()
    if not no_dossier:
        raise HTTPException(400, "no_dossier requis")
    scope = (body.get("scope") or "").strip().lower()
    if scope not in ("jour", "cumul"):
        raise HTTPException(400, "scope doit etre 'jour' ou 'cumul'")
    try:
        cible = int(body.get("nb_cartons_cible"))
    except (TypeError, ValueError):
        raise HTTPException(400, "nb_cartons_cible invalide")
    if cible < 0:
        raise HTTPException(400, "nb_cartons_cible doit etre >= 0")

    operateur = _rep_operateur(user)
    with get_db() as conn:
        machine_obj = _resolve_machine(user, body, conn)
        etiq_par_carton = _rep_get_etiq_par_carton(conn, no_dossier) or 0

        if scope == "jour":
            # Ajuste la saisie 03 du jour de l'operateur courant
            saisie = _rep_get_or_create_saisie_03(
                conn, operateur, no_dossier, machine_obj["nom"]
            )
            actuel_cartons = int(saisie.get("nb_cartons") or 0)
            actuel_etiq = int(saisie.get("quantite_traitee") or 0)
            delta_cartons = cible - actuel_cartons
            # Recalcul cible etiquettes : cartons * epc (si defini) sinon proportionnel
            if etiq_par_carton > 0:
                cible_etiq = cible * etiq_par_carton
            else:
                cible_etiq = actuel_etiq + delta_cartons  # fallback
            delta_etiq = cible_etiq - actuel_etiq
            _rep_increment_saisie_03(
                conn, saisie["id"], delta_etiq, delta_cartons,
            )
        else:
            # scope == 'cumul' : on ajoute une ligne d'ajustement aujourd'hui
            cum_c, _cum_e = _rep_aggregate(
                conn, no_dossier, operateur, today_only=False,
            )
            delta_cartons = cible - cum_c
            if etiq_par_carton > 0:
                delta_etiq = delta_cartons * etiq_par_carton
            else:
                delta_etiq = delta_cartons
            if delta_cartons == 0 and delta_etiq == 0:
                return {"success": True, "unchanged": True}
            # Une ligne d'ajustement dediee (commentaire identifiant)
            pe_row = conn.execute(
                "SELECT client, description FROM planning_entries "
                "WHERE trim(reference)=trim(?) LIMIT 1",
                (no_dossier,),
            ).fetchone()
            client = (pe_row["client"] if pe_row else None) or None
            designation = (pe_row["description"] if pe_row else None) or None
            now_iso = _rep_today_isoformat()
            # Date d'operation : par defaut maintenant, sinon la date fournie
            # (utilisee pour reporter de la production sur une date passee).
            date_raw = (body.get("date_operation") or "").strip()
            if date_raw:
                # Accepte YYYY-MM-DD ou YYYY-MM-DDTHH:MM:SS
                try:
                    if "T" in date_raw:
                        dt_op = datetime.fromisoformat(date_raw[:19])
                    else:
                        # Date pure : on attache l'heure courante locale pour le tri
                        d_only = date.fromisoformat(date_raw[:10])
                        now_t = datetime.now(_PARIS).time()
                        dt_op = datetime.combine(d_only, now_t.replace(microsecond=0))
                    date_op_val = dt_op.strftime("%Y-%m-%dT%H:%M:%S")
                except ValueError:
                    raise HTTPException(400, "date_operation invalide")
            else:
                date_op_val = now_iso
            commentaire = (
                f"Ajustement manuel cumul par {user.get('nom') or user.get('email')} "
                f"(delta {delta_cartons:+d} cartons, {delta_etiq:+d} etiq.)"
            )
            if date_raw:
                commentaire += f" - date reportee : {date_raw[:10]}"
            conn.execute(
                """INSERT INTO production_data
                   (operateur, date_operation, operation, operation_code,
                    operation_severity, operation_category, machine,
                    no_dossier, client, designation,
                    quantite_a_traiter, quantite_traitee, nb_cartons,
                    service, data, est_manuel, commentaire,
                    modifie_par, modifie_le, modifie_note)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)""",
                (
                    operateur, date_op_val, "03 - Production", "03",
                    "info", "production", machine_obj["nom"],
                    no_dossier, client, designation,
                    0, delta_etiq, delta_cartons,
                    "fabrication",
                    json.dumps(
                        {
                            "operateur": operateur, "no_dossier": no_dossier,
                            "machine": machine_obj["nom"],
                            "source": "repiquage_ajustement_cumul",
                            "delta_cartons": delta_cartons, "delta_etiq": delta_etiq,
                            "date_reportee": date_raw[:10] if date_raw else None,
                        },
                        default=str,
                    ),
                    commentaire,
                    user.get("nom") or user.get("email") or "",
                    now_iso,
                    "Ajustement manuel cumul (admin)",
                ),
            )

        conn.commit()
        nb_courant = _rep_get_carton_courant(conn, no_dossier, operateur)
        jour_c, jour_e = _rep_aggregate(conn, no_dossier, operateur, today_only=True)
        cum_c2, cum_e2 = _rep_aggregate(conn, no_dossier, operateur, today_only=False)

    log_action(
        user=user,
        action="UPDATE",
        module="fabrication",
        objet=f"Repiquage ajustement {scope} dossier {no_dossier}",
        detail={"scope": scope, "nb_cartons_cible": cible},
        ip=request.client.host if request.client else None,
    )
    return {
        "success": True,
        "nb_etiquettes_courant": nb_courant,
        "etiquettes_par_carton": etiq_par_carton or None,
        "jour": {"nb_cartons": jour_c, "qte_etiq": jour_e},
        "cumul": {"nb_cartons": cum_c2, "qte_etiq": cum_e2},
    }


@router.get("/api/fabrication/repiquage/historique")
def get_repiquage_historique(request: Request, no_dossier: str):
    """Historique des saisies code 03 (Repiquage) pour un dossier.

    Renvoie toutes les lignes, tous operateurs, triees par date desc.
    Inclut un flag is_ajustement deduit du commentaire et de est_manuel.
    """
    user = get_current_user(request)
    _check_fab_access(user)
    no_dossier = (no_dossier or "").strip()
    if not no_dossier:
        raise HTTPException(400, "no_dossier requis")

    with get_db() as conn:
        rows = conn.execute(
            """SELECT pd.id, pd.operateur, pd.date_operation, pd.machine,
                      pd.quantite_traitee, pd.nb_cartons, pd.commentaire,
                      pd.est_manuel, pd.modifie_par, pd.modifie_le, pd.modifie_note,
                      pd.data
               FROM production_data pd
               WHERE pd.no_dossier = ? AND pd.operation_code = '03'
                 AND (lower(trim(pd.machine)) LIKE 'repiquage%'
                      OR lower(trim(pd.machine)) = 'rep'
                      OR lower(trim(pd.machine)) LIKE 'rep %')
               ORDER BY pd.date_operation DESC, pd.id DESC""",
            (no_dossier,),
        ).fetchall()

    out = []
    for r in rows:
        d = dict(r)
        comm = (d.get("commentaire") or "").lower()
        d["is_ajustement"] = (
            int(d.get("est_manuel") or 0) == 1
            or "ajustement" in comm
        )
        out.append(d)
    return {"no_dossier": no_dossier, "saisies": out}


# -- Endpoints fil de discussion repiquage ----------------------------------

_REP_DISCUSSION_TYPES = ("observation", "dysfonctionnement", "commentaire")


@router.get("/api/fabrication/repiquage/discussion")
def get_repiquage_discussion(request: Request, no_dossier: str):
    """Liste les messages du fil pour un dossier (tri chronologique croissant)."""
    user = get_current_user(request)
    _check_fab_access(user)
    no_dossier = (no_dossier or "").strip()
    if not no_dossier:
        raise HTTPException(400, "no_dossier requis")
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, no_dossier, user_id, user_nom, type, message, created_at
               FROM repiquage_discussion
               WHERE trim(no_dossier) = trim(?)
               ORDER BY created_at ASC, id ASC""",
            (no_dossier,),
        ).fetchall()
    return {"no_dossier": no_dossier, "messages": [dict(r) for r in rows]}


@router.post("/api/fabrication/repiquage/discussion")
async def post_repiquage_discussion(request: Request):
    """Poste un message dans le fil. Si type=dysfonctionnement, notif superadmin."""
    user = get_current_user(request)
    _check_fab_access(user)
    body = await request.json()

    no_dossier = (body.get("no_dossier") or "").strip()
    if not no_dossier:
        raise HTTPException(400, "no_dossier requis")

    type_msg = (body.get("type") or "commentaire").strip().lower()
    if type_msg not in _REP_DISCUSSION_TYPES:
        raise HTTPException(400, f"type invalide (attendu : {', '.join(_REP_DISCUSSION_TYPES)})")

    message = (body.get("message") or "").strip()
    if not message:
        raise HTTPException(400, "Message requis")
    if len(message) > 4000:
        raise HTTPException(400, "Message trop long (max 4000 caracteres)")

    user_nom = (user.get("nom") or user.get("email") or "Operateur").strip()
    user_id = int(user.get("id")) if user.get("id") is not None else None
    now = datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")

    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO repiquage_discussion
               (no_dossier, user_id, user_nom, type, message, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (no_dossier, user_id, user_nom, type_msg, message, now),
        )
        new_id = cur.lastrowid

        # Notif superadmin pour les dysfonctionnements
        if type_msg == "dysfonctionnement":
            from config import SUPERADMIN_EMAIL
            try:
                pe = conn.execute(
                    "SELECT client FROM planning_entries "
                    "WHERE trim(reference)=trim(?) LIMIT 1",
                    (no_dossier,),
                ).fetchone()
                client_label = (pe["client"] if pe else "") or ""
                subject = f"[Repiquage] Dysfonctionnement signale - OF {no_dossier}"
                if client_label:
                    subject += f" ({client_label})"
                body_msg = (
                    f"L'operateur {user_nom} a signale un dysfonctionnement "
                    f"sur le dossier {no_dossier}"
                    + (f" ({client_label})" if client_label else "")
                    + f".\n\nMessage :\n{message}\n\n"
                    f"A consulter dans le fil de discussion du dossier."
                )
                conn.execute(
                    """INSERT INTO messages
                       (from_user_id, from_email, from_name, to_email, subject, body, created_at)
                       VALUES (?,?,?,?,?,?,?)""",
                    (
                        user_id,
                        (user.get("email") or "").strip().lower(),
                        f"[Repiquage] {user_nom}",
                        (SUPERADMIN_EMAIL or "").strip().lower(),
                        subject,
                        body_msg,
                        now,
                    ),
                )
            except Exception:
                # Ne jamais bloquer le post pour un echec de notif
                pass
        conn.commit()

        row = conn.execute(
            "SELECT id, no_dossier, user_id, user_nom, type, message, created_at "
            "FROM repiquage_discussion WHERE id=?",
            (new_id,),
        ).fetchone()

    log_action(
        user=user,
        action="CREATE",
        module="fabrication",
        objet=f"Discussion repiquage dossier {no_dossier}",
        detail={"type": type_msg, "len": len(message)},
        ip=request.client.host if request.client else None,
    )
    return dict(row) if row else {"success": True, "id": new_id}


@router.delete("/api/fabrication/repiquage/discussion/{msg_id}")
def delete_repiquage_discussion(msg_id: int, request: Request):
    """Supprime un message du fil. Reserve a l'auteur ou aux admins."""
    user = get_current_user(request)
    _check_fab_access(user)
    with get_db() as conn:
        ex = conn.execute(
            "SELECT id, user_id, user_nom FROM repiquage_discussion WHERE id=?",
            (msg_id,),
        ).fetchone()
        if not ex:
            raise HTTPException(404, "Message introuvable")

        is_author = (
            user.get("id") is not None
            and ex["user_id"] is not None
            and int(user["id"]) == int(ex["user_id"])
        )
        if not (is_admin(user) or is_author):
            raise HTTPException(403, "Non autorise")

        conn.execute("DELETE FROM repiquage_discussion WHERE id=?", (msg_id,))
        conn.commit()

    log_action(
        user=user,
        action="DELETE",
        module="fabrication",
        objet=f"Discussion repiquage message #{msg_id}",
        ip=request.client.host if request.client else None,
    )
    return {"success": True}

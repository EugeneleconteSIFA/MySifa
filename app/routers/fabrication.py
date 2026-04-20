"""MySifa — Fabrication API v1.1
Routes : /api/fabrication/*
Accessible : fabrication, admin, superadmin
"""
import json
from datetime import datetime, date
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Request, HTTPException

_PARIS = ZoneInfo("Europe/Paris")

from database import get_db
from config import classify_operation
from app.services.auth_service import get_current_user, is_fabrication, is_admin

router = APIRouter()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _check_fab_access(user: dict):
    """Fabrication OU admin autorisé pour cette API."""
    if not (is_fabrication(user) or is_admin(user)):
        raise HTTPException(status_code=403, detail="Accès réservé au service Fabrication")


def _today_prefix() -> str:
    return date.today().isoformat()


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


# ─── Endpoints ────────────────────────────────────────────────────────────────

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


@router.get("/api/fabrication/dossiers")
def list_dossiers(request: Request):
    """Dossiers du planning pour la machine liée à l'opérateur (statut attente + en_cours)."""
    user = get_current_user(request)
    _check_fab_access(user)

    machine_id = user.get("machine_id")

    with get_db() as conn:
        if machine_id:
            rows = conn.execute(
                """SELECT pe.*, m.nom AS machine_nom, m.code AS machine_code
                   FROM planning_entries pe
                   JOIN machines m ON m.id = pe.machine_id
                   WHERE pe.machine_id = ? AND pe.statut IN ('attente','en_cours')
                   ORDER BY pe.position ASC""",
                (machine_id,),
            ).fetchall()
            machine = conn.execute(
                "SELECT * FROM machines WHERE id=?", (machine_id,)
            ).fetchone()
        else:
            # Admin sans machine liée : tous les dossiers de toutes les machines
            rows = conn.execute(
                """SELECT pe.*, m.nom AS machine_nom, m.code AS machine_code
                   FROM planning_entries pe
                   JOIN machines m ON m.id = pe.machine_id
                   WHERE pe.statut IN ('attente','en_cours')
                   ORDER BY m.nom, pe.position ASC"""
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

    operateur = user.get("operateur_lie") or ""
    # machine_id : préférence compte utilisateur, sinon query param (admin)
    mid = user.get("machine_id") or machine_id

    if not operateur and not is_admin(user):
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
            rows = conn.execute(
                """SELECT * FROM production_data
                   WHERE operateur = ? AND (
                     date_operation LIKE ? OR date_operation LIKE ?
                   )
                   ORDER BY date_operation ASC, id ASC""",
                (operateur, today + "%", today_fr + "%"),
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

        # Info machine
        machine = None
        if mid:
            m = conn.execute("SELECT * FROM machines WHERE id=?", (mid,)).fetchone()
            if m:
                machine = dict(m)

        return {
            "saisies": saisies,
            "etat": etat,
            "dossier": dossier,
            "last_saisie": saisies[-1] if saisies else None,
            "operateur": operateur,
            "machine": machine,
        }


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

    # Opérateur : issu du compte sauf si admin
    operateur = user.get("operateur_lie") or ""
    if is_admin(user) and body.get("operateur"):
        operateur = str(body["operateur"]).strip()
    if not operateur:
        raise HTTPException(
            status_code=400,
            detail="Compte non lié à un opérateur — contacter un administrateur",
        )

    date_op = datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")

    no_dossier  = (body.get("no_dossier")   or "").strip() or None
    client      = (body.get("client")       or "").strip() or None
    designation = (body.get("designation")  or "").strip() or None
    commentaire = (body.get("commentaire")  or "").strip() or None

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
                debut_row = conn.execute(
                    """SELECT COALESCE(metrage_total_debut, metrage_prevu) AS ctr_debut
                       FROM production_data
                       WHERE no_dossier = ? AND operation_code = '01'
                         AND COALESCE(metrage_total_debut, metrage_prevu) IS NOT NULL
                       ORDER BY date_operation DESC LIMIT 1""",
                    (no_dossier,),
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

        row = conn.execute(
            "SELECT * FROM production_data WHERE id=?", (new_id,)
        ).fetchone()

    return {"success": True, "id": new_id, "saisie": dict(row)}


# ─── Traçabilité matières ─────────────────────────────────────────────────────

@router.get("/api/fabrication/matieres")
def list_matieres(request: Request, machine_id: int = None, no_dossier: str = None):
    """Retourne les matières scannées : pour une machine (session du jour) ou un dossier."""
    user = get_current_user(request)
    _check_fab_access(user)

    mid = user.get("machine_id") or machine_id
    operateur = user.get("operateur_lie") or ""

    with get_db() as conn:
        if no_dossier:
            rows = conn.execute(
                """SELECT * FROM fab_matieres_utilisees
                   WHERE no_dossier = ?
                   ORDER BY scanned_at ASC""",
                (no_dossier,),
            ).fetchall()
        elif mid:
            today = _today_prefix()
            today_fr = date.today().strftime("%d/%m/%Y")
            rows = conn.execute(
                """SELECT * FROM fab_matieres_utilisees
                   WHERE machine_id = ? AND (scanned_at LIKE ? OR scanned_at LIKE ?)
                   ORDER BY scanned_at ASC""",
                (mid, today + "%", today_fr + "%"),
            ).fetchall()
        else:
            rows = []

    return {"matieres": [dict(r) for r in rows]}


@router.post("/api/fabrication/matieres")
async def add_matiere(request: Request):
    """Enregistre un scan de code barre matière. Lié à la machine + dossier actif."""
    user = get_current_user(request)
    _check_fab_access(user)

    body = await request.json()
    code_barre = (body.get("code_barre") or "").strip()
    if not code_barre:
        raise HTTPException(status_code=400, detail="Code barre manquant")

    operateur = user.get("operateur_lie") or ""
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
        row = conn.execute(
            "SELECT * FROM fab_matieres_utilisees WHERE id=?", (new_id,)
        ).fetchone()

    return {"success": True, "id": new_id, "matiere": dict(row)}


@router.delete("/api/fabrication/matieres/{matiere_id}")
async def delete_matiere(matiere_id: int, request: Request):
    """Supprime un scan de matière."""
    user = get_current_user(request)
    _check_fab_access(user)

    operateur = user.get("operateur_lie") or ""

    with get_db() as conn:
        ex = conn.execute(
            "SELECT * FROM fab_matieres_utilisees WHERE id=?", (matiere_id,)
        ).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Scan non trouvé")
        if not is_admin(user) and ex["operateur"] != operateur:
            raise HTTPException(status_code=403, detail="Non autorisé")

        conn.execute("DELETE FROM fab_matieres_utilisees WHERE id=?", (matiere_id,))
        conn.commit()

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
                   ORDER BY date_operation ASC""",
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

        operateur = user.get("operateur_lie") or ""
        if not is_admin(user) and ex["operateur"] != operateur:
            raise HTTPException(status_code=403, detail="Non autorisé")

        conn.execute(
            """UPDATE production_data
               SET commentaire=?, modifie_par=?, modifie_le=?, modifie_note=?
               WHERE id=?""",
            (
                commentaire,
                user["email"],
                datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S"),
                "Commentaire opérateur fabrication",
                saisie_id,
            ),
        )
        conn.commit()

    return {"success": True}

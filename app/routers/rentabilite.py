"""
SIFA — Rentabilité v1.0
Import devis, liaison dossiers, comparaison théorique/réel.
Accès : direction + administration uniquement.
"""
from datetime import datetime
from fastapi import APIRouter, Request, UploadFile, File, HTTPException
from database import get_db
from services.auth_service import get_current_user
from services.devis_parser import parse_devis
from config import ROLES_ADMIN

router = APIRouter()


def require_rentabilite(request: Request) -> dict:
    """Direction et Administration uniquement."""
    user = get_current_user(request)
    if user["role"] not in ROLES_ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Accès réservé à la Direction et l'Administration"
        )
    return user


def _comparaison_from_no_dossiers(conn, devis_row, no_dossiers: list[str]) -> dict:
    """Calcule la comparaison devis vs réel pour une liste de no_dossier (production_data)."""
    d = devis_row
    no_dossiers = [str(x).strip() for x in (no_dossiers or []) if str(x or "").strip()]
    if not no_dossiers:
        return {"devis": dict(d), "reel": None, "message": "Aucun dossier lié"}

    placeholders = ",".join("?" * len(no_dossiers))

    qte_reel = conn.execute(
        f"""SELECT COALESCE(SUM(quantite_traitee), 0) as qte
            FROM production_data
            WHERE no_dossier IN ({placeholders}) AND operation_code='89'""",
        no_dossiers,
    ).fetchone()["qte"]

    metrage_reel = conn.execute(
        f"""SELECT COALESCE(SUM(metrage_reel), 0) as met
            FROM production_data
            WHERE no_dossier IN ({placeholders}) AND operation_code='89'""",
        no_dossiers,
    ).fetchone()["met"]

    tps_calage_reel = conn.execute(
        f"""
        SELECT COALESCE(SUM(
            CASE WHEN operation_code='02'
            THEN (julianday(lead_date) - julianday(date_operation)) * 1440
            ELSE 0 END
        ), 0) as tps
        FROM (
            SELECT date_operation, operation_code,
                   LEAD(date_operation) OVER (PARTITION BY operateur ORDER BY date_operation) as lead_date
            FROM production_data
            WHERE no_dossier IN ({placeholders})
        ) WHERE operation_code='02'
        """,
        no_dossiers,
    ).fetchone()["tps"]

    tps_prod_reel = conn.execute(
        f"""
        SELECT COALESCE(SUM(
            CASE WHEN operation_code IN ('03','88')
            THEN (julianday(lead_date) - julianday(date_operation)) * 1440
            ELSE 0 END
        ), 0) as tps
        FROM (
            SELECT date_operation, operation_code,
                   LEAD(date_operation) OVER (PARTITION BY operateur ORDER BY date_operation) as lead_date
            FROM production_data
            WHERE no_dossier IN ({placeholders})
        ) WHERE operation_code IN ('03','88')
        """,
        no_dossiers,
    ).fetchone()["tps"]

    vitesse_reel = (metrage_reel / tps_prod_reel) if tps_prod_reel > 0 else 0
    tps_total_reel = tps_calage_reel + tps_prod_reel
    vitesse_avec_calage = (metrage_reel / tps_total_reel) if tps_total_reel > 0 else 0

    tps_total_theo = (d["temps_calage_mn"] or 0) + (d["temps_production_mn"] or 0)
    vitesse_theo_avec_calage = ((d["metrage_production_ml"] or 0) / tps_total_theo) if tps_total_theo > 0 else 0

    def pct_diff(reel, theo):
        if theo and theo != 0:
            return round((reel - theo) / theo * 100, 1)
        return None

    def fmt_pct(v):
        if v is None:
            return None
        return f"+{v}%" if v > 0 else f"{v}%"

    reel = {
        "temps_calage_mn":      round(tps_calage_reel, 1),
        "temps_production_mn":  round(tps_prod_reel, 1),
        "metrage_ml":           round(metrage_reel, 1),
        "qte_etiquettes":       round(qte_reel, 0),
        "vitesse":              round(vitesse_reel, 2),
        "vitesse_avec_calage":  round(vitesse_avec_calage, 2),
    }

    theo = {
        "temps_calage_mn":      d["temps_calage_mn"],
        "temps_production_mn":  d["temps_production_mn"],
        "metrage_ml":           d["metrage_production_ml"],
        "qte_etiquettes":       d["qte_etiquettes"],
        "vitesse":              d["vitesse_theorique"],
        "vitesse_avec_calage":  round(vitesse_theo_avec_calage, 2),
    }

    ecarts = {
        "temps_calage_mn":      fmt_pct(pct_diff(reel["temps_calage_mn"],     theo["temps_calage_mn"])),
        "temps_production_mn":  fmt_pct(pct_diff(reel["temps_production_mn"], theo["temps_production_mn"])),
        "metrage_ml":           fmt_pct(pct_diff(reel["metrage_ml"],           theo["metrage_ml"])),
        "qte_etiquettes":       fmt_pct(pct_diff(reel["qte_etiquettes"],       theo["qte_etiquettes"])),
        "vitesse":              fmt_pct(pct_diff(reel["vitesse"],              theo["vitesse"])),
        "vitesse_avec_calage":  fmt_pct(pct_diff(reel["vitesse_avec_calage"],  theo["vitesse_avec_calage"])),
    }

    score = 0
    if reel["vitesse"] > (theo["vitesse"] or 0):
        score += 1
    if reel["temps_calage_mn"] < (theo["temps_calage_mn"] or 999):
        score += 1
    if reel["qte_etiquettes"] >= (theo["qte_etiquettes"] or 0):
        score += 1

    if score == 3:
        conclusion = {"label": "Excellent", "color": "success"}
    elif score == 2:
        conclusion = {"label": "Bon",        "color": "success"}
    elif score == 1:
        conclusion = {"label": "Mitigé",     "color": "warn"}
    else:
        conclusion = {"label": "À améliorer", "color": "danger"}

    return {
        "devis":      dict(d),
        "dossiers":   no_dossiers,
        "theorique":  theo,
        "reel":       reel,
        "ecarts":     ecarts,
        "conclusion": conclusion,
    }


# ── Rentabilité v2 (Planning-based) ───────────────────────────────
@router.get("/api/rentabilite/planning-entries")
def list_planning_entries(request: Request):
    """Liste toutes les entrées planning (toutes machines) pour la vue Rentabilité."""
    require_rentabilite(request)
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT
              e.*,
              m.nom AS machine_nom,
              m.code AS machine_code
            FROM planning_entries e
            JOIN machines m ON m.id = e.machine_id
            WHERE m.actif = 1
            ORDER BY m.nom ASC, e.position ASC
            """
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/api/rentabilite/links/{planning_entry_id}")
def get_links(planning_entry_id: int, request: Request):
    require_rentabilite(request)
    with get_db() as conn:
        ex = conn.execute("SELECT id FROM planning_entries WHERE id=?", (planning_entry_id,)).fetchone()
        if not ex:
            raise HTTPException(404, "Entrée planning introuvable")
        link = conn.execute(
            "SELECT devis_id, updated_at FROM rent_links WHERE planning_entry_id=?",
            (planning_entry_id,),
        ).fetchone()
        prod = conn.execute(
            "SELECT no_dossier FROM rent_prod_links WHERE planning_entry_id=? ORDER BY no_dossier",
            (planning_entry_id,),
        ).fetchall()
    return {
        "planning_entry_id": planning_entry_id,
        "devis_id": (link["devis_id"] if link else None),
        "updated_at": (link["updated_at"] if link else None),
        "no_dossiers": [r["no_dossier"] for r in prod],
    }


@router.put("/api/rentabilite/links/{planning_entry_id}")
async def put_links(planning_entry_id: int, request: Request):
    require_rentabilite(request)
    body = await request.json()
    devis_id = body.get("devis_id")
    no_dossiers = body.get("no_dossiers") or []
    no_dossiers = [str(x).strip() for x in no_dossiers if str(x or "").strip()]

    now = datetime.now().isoformat()
    with get_db() as conn:
        ex = conn.execute("SELECT id FROM planning_entries WHERE id=?", (planning_entry_id,)).fetchone()
        if not ex:
            raise HTTPException(404, "Entrée planning introuvable")
        if devis_id is not None:
            dv = conn.execute("SELECT id FROM devis WHERE id=?", (int(devis_id),)).fetchone()
            if not dv:
                raise HTTPException(404, "Devis introuvable")

        conn.execute(
            """INSERT INTO rent_links (planning_entry_id, devis_id, updated_at)
               VALUES (?,?,?)
               ON CONFLICT(planning_entry_id) DO UPDATE
                 SET devis_id=excluded.devis_id, updated_at=excluded.updated_at""",
            (planning_entry_id, int(devis_id) if devis_id is not None else None, now),
        )
        conn.execute("DELETE FROM rent_prod_links WHERE planning_entry_id=?", (planning_entry_id,))
        for dos in no_dossiers:
            conn.execute(
                "INSERT OR IGNORE INTO rent_prod_links (planning_entry_id, no_dossier) VALUES (?,?)",
                (planning_entry_id, dos),
            )
        conn.commit()
    return {"success": True}


@router.get("/api/rentabilite/planning/{planning_entry_id}/comparaison")
def comparaison_for_planning(planning_entry_id: int, request: Request):
    """Comparaison basée sur le devis lié + les no_dossier liés à une entrée planning."""
    require_rentabilite(request)
    with get_db() as conn:
        ex = conn.execute("SELECT id FROM planning_entries WHERE id=?", (planning_entry_id,)).fetchone()
        if not ex:
            raise HTTPException(404, "Entrée planning introuvable")
        link = conn.execute(
            "SELECT devis_id FROM rent_links WHERE planning_entry_id=?",
            (planning_entry_id,),
        ).fetchone()
        if not link or not link["devis_id"]:
            return {"devis": None, "reel": None, "message": "Aucun devis lié"}
        d = conn.execute("SELECT * FROM devis WHERE id=?", (int(link["devis_id"]),)).fetchone()
        if not d:
            raise HTTPException(404, "Devis introuvable")
        prod = conn.execute(
            "SELECT no_dossier FROM rent_prod_links WHERE planning_entry_id=?",
            (planning_entry_id,),
        ).fetchall()
        no_dossiers = [r["no_dossier"] for r in prod]
        return _comparaison_from_no_dossiers(conn, d, no_dossiers)


@router.get("/api/rentabilite/no-dossiers")
def suggest_no_dossiers(request: Request, q: str = "", limit: int = 12):
    """Suggestions no_dossier depuis production_data (pour autocomplétion)."""
    require_rentabilite(request)
    qn = str(q or "").strip()
    try:
        lim = max(1, min(int(limit), 50))
    except Exception:
        lim = 12
    with get_db() as conn:
        if qn:
            rows = conn.execute(
                """
                SELECT DISTINCT no_dossier
                FROM production_data
                WHERE no_dossier IS NOT NULL AND TRIM(no_dossier) != ''
                  AND LOWER(no_dossier) LIKE LOWER(?)
                ORDER BY no_dossier
                LIMIT ?
                """,
                (f"%{qn}%", lim),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT DISTINCT no_dossier
                FROM production_data
                WHERE no_dossier IS NOT NULL AND TRIM(no_dossier) != ''
                ORDER BY no_dossier
                LIMIT ?
                """,
                (lim,),
            ).fetchall()
    return [r["no_dossier"] for r in rows]

# ── Import d'un devis ─────────────────────────────────────────────
@router.post("/api/rentabilite/devis/import")
async def import_devis(request: Request, file: UploadFile = File(...)):
    require_rentabilite(request)
    contents = await file.read()
    filename = file.filename or "devis.xlsx"

    parsed = parse_devis(contents, filename)
    return {
        "preview": parsed,
        "parse_errors": parsed.get("parse_errors", []),
    }


# ── Valider et sauvegarder un devis ──────────────────────────────
@router.post("/api/rentabilite/devis")
async def create_devis(request: Request):
    user = require_rentabilite(request)
    body = await request.json()

    now = datetime.now().isoformat()
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO devis
               (filename, client, date_devis, format_h, format_v, laize, nb_couleurs,
                temps_calage_mn, metrage_calage_ml, temps_production_mn,
                metrage_production_ml, vitesse_theorique, qte_etiquettes, gache,
                statut, note, imported_at, imported_by)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                body.get("filename", ""),
                body.get("client", ""),
                body.get("date_devis", ""),
                body.get("format_h", 0),
                body.get("format_v", 0),
                body.get("laize", 0),
                body.get("nb_couleurs", 0),
                body.get("temps_calage_mn", 0),
                body.get("metrage_calage_ml", 0),
                body.get("temps_production_mn", 0),
                body.get("metrage_production_ml", 0),
                body.get("vitesse_theorique", 0),
                body.get("qte_etiquettes", 0),
                body.get("gache", 0),
                "en_attente",
                body.get("note", ""),
                now,
                user["email"],
            )
        )
        devis_id = cursor.lastrowid
        conn.commit()
    return {"success": True, "devis_id": devis_id}


# ── Liste des devis ───────────────────────────────────────────────
@router.get("/api/rentabilite/devis")
def list_devis(request: Request):
    require_rentabilite(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT d.*,
                      COUNT(dd.id) as nb_dossiers_lies
               FROM devis d
               LEFT JOIN devis_dossiers dd ON dd.devis_id=d.id
               GROUP BY d.id
               ORDER BY d.imported_at DESC"""
        ).fetchall()
    return [dict(r) for r in rows]


# ── Détail d'un devis ─────────────────────────────────────────────
@router.get("/api/rentabilite/devis/{devis_id}")
def get_devis(devis_id: int, request: Request):
    require_rentabilite(request)
    with get_db() as conn:
        d = conn.execute("SELECT * FROM devis WHERE id=?", (devis_id,)).fetchone()
        if not d:
            raise HTTPException(status_code=404, detail="Devis non trouvé")
        dossiers = conn.execute(
            "SELECT no_dossier FROM devis_dossiers WHERE devis_id=?", (devis_id,)
        ).fetchall()
    return {**dict(d), "dossiers_lies": [r["no_dossier"] for r in dossiers]}


# ── Modifier un devis ─────────────────────────────────────────────
@router.put("/api/rentabilite/devis/{devis_id}")
async def update_devis(devis_id: int, request: Request):
    require_rentabilite(request)
    body = await request.json()
    with get_db() as conn:
        ex = conn.execute("SELECT * FROM devis WHERE id=?", (devis_id,)).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Devis non trouvé")
        conn.execute(
            """UPDATE devis SET client=?,date_devis=?,format_h=?,format_v=?,laize=?,
               nb_couleurs=?,temps_calage_mn=?,metrage_calage_ml=?,temps_production_mn=?,
               metrage_production_ml=?,vitesse_theorique=?,qte_etiquettes=?,gache=?,note=?
               WHERE id=?""",
            (
                body.get("client", ex["client"]),
                body.get("date_devis", ex["date_devis"]),
                body.get("format_h", ex["format_h"]),
                body.get("format_v", ex["format_v"]),
                body.get("laize", ex["laize"]),
                body.get("nb_couleurs", ex["nb_couleurs"]),
                body.get("temps_calage_mn", ex["temps_calage_mn"]),
                body.get("metrage_calage_ml", ex["metrage_calage_ml"]),
                body.get("temps_production_mn", ex["temps_production_mn"]),
                body.get("metrage_production_ml", ex["metrage_production_ml"]),
                body.get("vitesse_theorique", ex["vitesse_theorique"]),
                body.get("qte_etiquettes", ex["qte_etiquettes"]),
                body.get("gache", ex["gache"]),
                body.get("note", ex["note"]),
                devis_id,
            )
        )
        conn.commit()
    return {"success": True}


# ── Supprimer un devis ────────────────────────────────────────────
@router.delete("/api/rentabilite/devis/{devis_id}")
def delete_devis(devis_id: int, request: Request):
    require_rentabilite(request)
    with get_db() as conn:
        conn.execute("DELETE FROM devis_dossiers WHERE devis_id=?", (devis_id,))
        conn.execute("DELETE FROM devis WHERE id=?", (devis_id,))
        conn.commit()
    return {"success": True}


# ── Lier des dossiers à un devis ──────────────────────────────────
@router.put("/api/rentabilite/devis/{devis_id}/dossiers")
async def link_dossiers(devis_id: int, request: Request):
    require_rentabilite(request)
    body = await request.json()
    no_dossiers = body.get("dossiers", [])

    with get_db() as conn:
        ex = conn.execute("SELECT id FROM devis WHERE id=?", (devis_id,)).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Devis non trouvé")
        conn.execute("DELETE FROM devis_dossiers WHERE devis_id=?", (devis_id,))
        for dos in no_dossiers:
            if dos:
                conn.execute(
                    "INSERT INTO devis_dossiers (devis_id, no_dossier) VALUES (?,?)",
                    (devis_id, str(dos).strip()),
                )
        statut = "lie" if no_dossiers else "en_attente"
        conn.execute("UPDATE devis SET statut=? WHERE id=?", (statut, devis_id))
        conn.commit()
    return {"success": True}


# ── Calcul rentabilité devis vs réel ─────────────────────────────
@router.get("/api/rentabilite/devis/{devis_id}/comparaison")
def comparaison(devis_id: int, request: Request):
    require_rentabilite(request)

    with get_db() as conn:
        d = conn.execute("SELECT * FROM devis WHERE id=?", (devis_id,)).fetchone()
        if not d:
            raise HTTPException(status_code=404, detail="Devis non trouvé")

        dossiers = conn.execute(
            "SELECT no_dossier FROM devis_dossiers WHERE devis_id=?", (devis_id,)
        ).fetchall()
        no_dossiers = [r["no_dossier"] for r in dossiers]

        if not no_dossiers:
            return {"devis": dict(d), "reel": None, "message": "Aucun dossier lié à ce devis"}

        placeholders = ",".join("?" * len(no_dossiers))

        qte_reel = conn.execute(
            f"""SELECT COALESCE(SUM(quantite_traitee), 0) as qte
                FROM production_data
                WHERE no_dossier IN ({placeholders}) AND operation_code='89'""",
            no_dossiers,
        ).fetchone()["qte"]

        metrage_reel = conn.execute(
            f"""SELECT COALESCE(SUM(metrage_reel), 0) as met
                FROM production_data
                WHERE no_dossier IN ({placeholders}) AND operation_code='89'""",
            no_dossiers,
        ).fetchone()["met"]

        tps_calage_reel = conn.execute(
            f"""
            SELECT COALESCE(SUM(
                CASE WHEN operation_code='02'
                THEN (julianday(lead_date) - julianday(date_operation)) * 1440
                ELSE 0 END
            ), 0) as tps
            FROM (
                SELECT date_operation, operation_code,
                       LEAD(date_operation) OVER (PARTITION BY operateur ORDER BY date_operation) as lead_date
                FROM production_data
                WHERE no_dossier IN ({placeholders})
            ) WHERE operation_code='02'
            """,
            no_dossiers,
        ).fetchone()["tps"]

        tps_prod_reel = conn.execute(
            f"""
            SELECT COALESCE(SUM(
                CASE WHEN operation_code IN ('03','88')
                THEN (julianday(lead_date) - julianday(date_operation)) * 1440
                ELSE 0 END
            ), 0) as tps
            FROM (
                SELECT date_operation, operation_code,
                       LEAD(date_operation) OVER (PARTITION BY operateur ORDER BY date_operation) as lead_date
                FROM production_data
                WHERE no_dossier IN ({placeholders})
            ) WHERE operation_code IN ('03','88')
            """,
            no_dossiers,
        ).fetchone()["tps"]

    vitesse_reel = (metrage_reel / tps_prod_reel) if tps_prod_reel > 0 else 0
    tps_total_reel = tps_calage_reel + tps_prod_reel
    vitesse_avec_calage = (metrage_reel / tps_total_reel) if tps_total_reel > 0 else 0

    tps_total_theo = (d["temps_calage_mn"] or 0) + (d["temps_production_mn"] or 0)
    vitesse_theo_avec_calage = ((d["metrage_production_ml"] or 0) / tps_total_theo) if tps_total_theo > 0 else 0

    def pct_diff(reel, theo):
        if theo and theo != 0:
            return round((reel - theo) / theo * 100, 1)
        return None

    def fmt_pct(v):
        if v is None:
            return None
        return f"+{v}%" if v > 0 else f"{v}%"

    reel = {
        "temps_calage_mn":      round(tps_calage_reel, 1),
        "temps_production_mn":  round(tps_prod_reel, 1),
        "metrage_ml":           round(metrage_reel, 1),
        "qte_etiquettes":       round(qte_reel, 0),
        "vitesse":              round(vitesse_reel, 2),
        "vitesse_avec_calage":  round(vitesse_avec_calage, 2),
    }

    theo = {
        "temps_calage_mn":      d["temps_calage_mn"],
        "temps_production_mn":  d["temps_production_mn"],
        "metrage_ml":           d["metrage_production_ml"],
        "qte_etiquettes":       d["qte_etiquettes"],
        "vitesse":              d["vitesse_theorique"],
        "vitesse_avec_calage":  round(vitesse_theo_avec_calage, 2),
    }

    ecarts = {
        "temps_calage_mn":      fmt_pct(pct_diff(reel["temps_calage_mn"],     theo["temps_calage_mn"])),
        "temps_production_mn":  fmt_pct(pct_diff(reel["temps_production_mn"], theo["temps_production_mn"])),
        "metrage_ml":           fmt_pct(pct_diff(reel["metrage_ml"],           theo["metrage_ml"])),
        "qte_etiquettes":       fmt_pct(pct_diff(reel["qte_etiquettes"],       theo["qte_etiquettes"])),
        "vitesse":              fmt_pct(pct_diff(reel["vitesse"],              theo["vitesse"])),
        "vitesse_avec_calage":  fmt_pct(pct_diff(reel["vitesse_avec_calage"],  theo["vitesse_avec_calage"])),
    }

    score = 0
    if reel["vitesse"] > (theo["vitesse"] or 0): score += 1
    if reel["temps_calage_mn"] < (theo["temps_calage_mn"] or 999): score += 1
    if reel["qte_etiquettes"] >= (theo["qte_etiquettes"] or 0): score += 1

    if score == 3:   conclusion = {"label": "Excellent", "color": "success"}
    elif score == 2: conclusion = {"label": "Bon",        "color": "success"}
    elif score == 1: conclusion = {"label": "Mitigé",     "color": "warn"}
    else:            conclusion = {"label": "À améliorer", "color": "danger"}

    return {
        "devis":      dict(d),
        "dossiers":   no_dossiers,
        "theorique":  theo,
        "reel":       reel,
        "ecarts":     ecarts,
        "conclusion": conclusion,
    }


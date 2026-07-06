"""SIFA — Saisies v0.8 — commentaire + métrages"""
import json
import io
import pandas as pd
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import StreamingResponse
from database import get_db, parse_french_number, parse_datetime
from config import classify_operation
from services.auth_service import get_current_user, is_admin, is_fabrication, can_view_all_prod
from services.prod_machine_filter import append_machine_filter

router = APIRouter()

_FICTIF_PREFIX = "FICTIF:"


def _is_fictif_dossier(no_dossier: Optional[str]) -> bool:
    return (no_dossier or "").strip().upper().startswith(_FICTIF_PREFIX)


def _normalize_fictif_no_dossier(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        raise HTTPException(status_code=400, detail="Dossier fictif requis")
    if s.upper().startswith(_FICTIF_PREFIX):
        s = s[len(_FICTIF_PREFIX) :].strip()
    if not s:
        raise HTTPException(status_code=400, detail="Dossier fictif invalide")
    return _FICTIF_PREFIX + s


def _fictif_of_display(no_dossier: str) -> str:
    ref = (no_dossier or "").strip()
    if _is_fictif_dossier(ref):
        return ref[len(_FICTIF_PREFIX) :].strip()
    return ref


def _resolve_target_dossier_meta(conn, to_ref: str) -> dict:
    """Métadonnées du dossier cible (planning prioritaire, sinon ref brute)."""
    ref = (to_ref or "").strip()
    if not ref:
        raise HTTPException(status_code=400, detail="Dossier cible requis")
    if _is_fictif_dossier(ref):
        raise HTTPException(status_code=400, detail="Le dossier cible ne peut pas être fictif")

    row = conn.execute(
        """SELECT reference, numero_of, client, description, statut
           FROM planning_entries
           WHERE TRIM(COALESCE(numero_of,'')) = TRIM(?)
              OR TRIM(COALESCE(reference,'')) = TRIM(?)
           ORDER BY CASE statut WHEN 'en_cours' THEN 0 WHEN 'attente' THEN 1 ELSE 2 END, id DESC
           LIMIT 1""",
        (ref, ref),
    ).fetchone()
    if row:
        nd = (row["numero_of"] or row["reference"] or ref).strip()
        return {
            "no_dossier": nd,
            "client": (row["client"] or "").strip(),
            "designation": (row["description"] or "").strip(),
            "planning_reference": (row["reference"] or "").strip(),
            "planning_statut": row["statut"],
        }

    prod = conn.execute(
        """SELECT no_dossier, client, designation FROM production_data
           WHERE TRIM(no_dossier) = TRIM(?)
           LIMIT 1""",
        (ref,),
    ).fetchone()
    if prod:
        return {
            "no_dossier": (prod["no_dossier"] or ref).strip(),
            "client": (prod["client"] or "").strip(),
            "designation": (prod["designation"] or "").strip(),
            "planning_reference": None,
            "planning_statut": None,
        }

    return {"no_dossier": ref, "client": "", "designation": "", "planning_reference": None, "planning_statut": None}


# Filtre SQL : exclure les saisies "personnelles/dossier" (01 Début, 89 Fin,
# 86 Arrivée, 87 Départ) quand la machine est Repiquage. Ces saisies n'ont pas
# de sens pour l'atelier Repiquage qui utilise un comptage par cartons.
_REPIQUAGE_HIDE_CODES = ("01", "89", "86", "87")
_REPIQUAGE_HIDE_FILTER = (
    "NOT (operation_code IN ('01','89','86','87') AND "
    "(lower(trim(COALESCE(machine,''))) LIKE 'repiquage%' "
    " OR lower(trim(COALESCE(machine,''))) = 'rep' "
    " OR lower(trim(COALESCE(machine,''))) LIKE 'rep %'))"
)


def normalize_date_operation(val):
    dt = parse_datetime(val)
    return dt.strftime('%Y-%m-%dT%H:%M:%S') if dt else val


@router.get("/api/saisies")
def list_saisies(
    request: Request,
    operateur: Optional[List[str]] = Query(default=None),
    no_dossier: Optional[List[str]] = Query(default=None),
    machine: Optional[List[str]] = Query(default=None),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 500, offset: int = 0,
):
    user = get_current_user(request)
    # Pour fabrication: utiliser nom si operateur_lie n'est pas défini
    user_operateur = user.get("operateur_lie") or user.get("nom") or ""
    operateurs = [o for o in (operateur or []) if o]
    dossiers   = [d for d in (no_dossier or []) if d]
    machines   = [m for m in (machine or []) if m]

    where, params = ["1=1"], []
    # Toujours masquer les saisies obsoletes sur la machine Repiquage
    # (Debut/Fin de production, Arrivee/Depart personnel).
    where.append(_REPIQUAGE_HIDE_FILTER)
    if can_view_all_prod(user):
        if operateurs:
            where.append(f"operateur IN ({','.join('?'*len(operateurs))})")
            params.extend(operateurs)
        if dossiers:
            where.append(f"no_dossier IN ({','.join('?'*len(dossiers))})")
            params.extend(dossiers)
    else:
        # Pour fabrication: filtrer par operateur_lie ou nom utilisateur
        if user_operateur:
            where.append("operateur = ?"); params.append(user_operateur)
        else:
            where.append("1=0")
    if date_from: where.append("date_operation >= ?"); params.append(date_from)
    if date_to:   where.append("date_operation <= ?"); params.append(date_to+'T23:59:59')

    with get_db() as conn:
        if machines:
            append_machine_filter(where, params, conn, machines)
        wc = " AND ".join(where)
        total = conn.execute(f"SELECT COUNT(*) as c FROM production_data WHERE {wc}", params).fetchone()["c"]
        rows  = conn.execute(
            f"""SELECT id,import_id,operateur,date_operation,operation,operation_code,
                       operation_severity,operation_category,machine,no_dossier,client,designation,
                       quantite_a_traiter,quantite_traitee,metrage_prevu,metrage_reel,
                       metrage_total_debut,metrage_total_fin,
                       commentaire,service,est_manuel,modifie_par,modifie_le,modifie_note
                FROM production_data WHERE {wc}
                ORDER BY date_operation ASC, id ASC LIMIT ? OFFSET ?""",
            params + [limit, offset]
        ).fetchall()
    # --- Mouvements stock EP/SP/EM/SM avec no_dossier ---------------------
    stock_rows: list = []
    try:
        with get_db() as conn2:
            stock_rows = _fetch_stock_saisies_saisies(
                conn2,
                date_from=date_from,
                date_to=date_to,
                operateurs=operateurs if can_view_all_prod(user) else ([user_operateur] if user_operateur else []),
                user_email=(user.get("email") or None) if not can_view_all_prod(user) else None,
                user_id=(user.get("id")) if not can_view_all_prod(user) else None,
                dossiers=dossiers if can_view_all_prod(user) else None,
                machines=machines if can_view_all_prod(user) else None,
            )
    except Exception:
        # Ne pas casser /api/saisies si le join stock echoue -- degradation gracieuse.
        stock_rows = []

    rows_out = [dict(r) for r in rows]
    for r in rows_out:
        r["kind"] = "prod"
    rows_out.extend(stock_rows)
    # Retri : date_operation ASC, id ASC
    rows_out.sort(key=lambda r: ((r.get("date_operation") or ""), str(r.get("kind") or ""), int(r.get("id") or 0)))

    return {"total": total + len(stock_rows), "rows": rows_out}


# ----------------------------------------------------------------------------
# Timeline unifiee : mouvements MyStock EP/SP/EM/SM rattaches a un dossier
# ----------------------------------------------------------------------------

_STOCK_LABELS_S = {
    "EP": "Entree Z1",
    "SP": "Sortie produit fini",
    "EM": "Entree matiere",
    "SM": "Sortie matiere",
}


def _normalize_stock_pf_row(r: dict) -> Optional[dict]:
    tm = (r.get("type_mouvement") or "").strip()
    code = "EP" if tm == "entree" else ("SP" if tm == "sortie" else None)
    if not code:
        return None
    return {
        "id": r["id"],
        "kind": "stock_pf",
        "operateur": r.get("created_by") or "",
        "operateur_nom": r.get("created_by_name") or "",
        "date_operation": r.get("created_at") or "",
        "operation": _STOCK_LABELS_S[code],
        "operation_code": code,
        "operation_severity": "info",
        "operation_category": "stock_pf",
        "machine": r.get("pe_machine") or "",
        "no_dossier": r.get("no_dossier") or "",
        "client": r.get("pe_client") or "",
        "designation": r.get("pe_description") or "",
        "quantite_traitee": r.get("quantite"),
        "quantite_a_traiter": None,
        "quantite_avant": r.get("quantite_avant"),
        "quantite_apres": r.get("quantite_apres"),
        "emplacement": r.get("emplacement") or "",
        "produit_id": r.get("produit_id"),
        "produit_reference": r.get("produit_reference") or "",
        "produit_designation": r.get("produit_designation") or "",
        "note": r.get("note") or "",
        "commentaire": r.get("note") or "",
        "service": "fabrication",
    }


def _normalize_stock_mp_row(r: dict) -> Optional[dict]:
    tm = (r.get("type_mouvement") or "").strip()
    code = "EM" if tm == "entree" else ("SM" if tm == "sortie" else None)
    if not code:
        return None
    return {
        "id": r["id"],
        "kind": "stock_mp",
        "operateur": r.get("created_by_email") or "",
        "operateur_nom": r.get("created_by_name") or "",
        "date_operation": r.get("created_at") or "",
        "operation": _STOCK_LABELS_S[code],
        "operation_code": code,
        "operation_severity": "info",
        "operation_category": "stock_mp",
        "machine": r.get("machine") or "",
        "no_dossier": r.get("no_dossier") or "",
        "client": r.get("client") or "",
        "designation": r.get("designation") or "",
        "quantite_traitee": r.get("quantite"),
        "quantite_a_traiter": None,
        "quantite_avant": r.get("quantite_avant"),
        "quantite_apres": r.get("quantite_apres"),
        "emplacement_source": r.get("emplacement_source") or "",
        "emplacement_dest": r.get("emplacement_dest") or "",
        "matiere_id": r.get("matiere_id"),
        "matiere_reference": r.get("matiere_reference") or "",
        "matiere_designation": r.get("matiere_designation") or "",
        "ref_bl": r.get("ref_bl") or "",
        "laize_id": r.get("laize_id"),
        "note": r.get("note") or "",
        "commentaire": r.get("note") or "",
        "service": "fabrication",
    }


def _fetch_stock_saisies_saisies(
    conn,
    *,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    operateurs: Optional[list] = None,
    dossiers: Optional[list] = None,
    machines: Optional[list] = None,
    user_email: Optional[str] = None,
    user_id: Optional[int] = None,
    limit: int = 500,
) -> list:
    """Retourne les mouvements stock EP/SP/EM/SM eligibles pour /api/saisies.
    Filtres facultatifs : plage date, operateurs, dossiers, machines.
    """
    result: list = []

    # -- PF (mouvements_stock) -------------------------------------------------
    pf_where = ["ms.no_dossier IS NOT NULL", "trim(ms.no_dossier) != ''"]
    pf_args: list = []
    if date_from:
        pf_where.append("ms.created_at >= ?"); pf_args.append(date_from)
    if date_to:
        pf_where.append("ms.created_at <= ?"); pf_args.append(date_to + "T23:59:59")
    if user_email:
        pf_where.append("LOWER(TRIM(COALESCE(ms.created_by,''))) = LOWER(TRIM(?))")
        pf_args.append(user_email)
    if operateurs:
        # Filtre par nom operateur -> jointure users pour matcher created_by (email)
        ops = [o for o in operateurs if o]
        if ops:
            ph = ",".join("?" * len(ops))
            pf_where.append(
                f"EXISTS (SELECT 1 FROM users u2 WHERE LOWER(TRIM(u2.email)) = LOWER(TRIM(ms.created_by)) "
                f"AND (u2.operateur_lie IN ({ph}) OR u2.nom IN ({ph})))"
            )
            pf_args.extend(ops); pf_args.extend(ops)
    if dossiers:
        ph = ",".join("?" * len(dossiers))
        pf_where.append(f"ms.no_dossier IN ({ph})")
        pf_args.extend(dossiers)
    if machines:
        ph = ",".join("?" * len(machines))
        pf_where.append(f"m.nom IN ({ph})")
        pf_args.extend(machines)

    pf_sql = f"""
        SELECT
          ms.id, ms.produit_id, ms.emplacement, ms.type_mouvement, ms.quantite,
          ms.quantite_avant, ms.quantite_apres, ms.note, ms.created_at,
          ms.created_by, ms.created_by_name, ms.no_dossier,
          p.reference AS produit_reference,
          p.designation AS produit_designation,
          pe.client AS pe_client,
          pe.description AS pe_description,
          m.nom AS pe_machine
        FROM mouvements_stock ms
        LEFT JOIN produits p ON p.id = ms.produit_id
        LEFT JOIN planning_entries pe ON trim(pe.reference) = trim(ms.no_dossier)
        LEFT JOIN machines m ON m.id = pe.machine_id
        WHERE {" AND ".join(pf_where)}
        ORDER BY ms.created_at DESC
        LIMIT ?
    """
    for r in conn.execute(pf_sql, pf_args + [limit]).fetchall():
        norm = _normalize_stock_pf_row(dict(r))
        if norm:
            result.append(norm)

    # -- MP (mp_mouvements) ----------------------------------------------------
    mp_where = ["mm.no_dossier IS NOT NULL", "trim(mm.no_dossier) != ''"]
    mp_args: list = []
    if date_from:
        mp_where.append("mm.created_at >= ?"); mp_args.append(date_from)
    if date_to:
        mp_where.append("mm.created_at <= ?"); mp_args.append(date_to + "T23:59:59")
    if user_id is not None:
        try:
            mp_where.append("mm.created_by = ?"); mp_args.append(int(user_id))
        except (TypeError, ValueError):
            pass
    if operateurs:
        ops = [o for o in operateurs if o]
        if ops:
            ph = ",".join("?" * len(ops))
            mp_where.append(
                f"EXISTS (SELECT 1 FROM users u3 WHERE u3.id = mm.created_by "
                f"AND (u3.operateur_lie IN ({ph}) OR u3.nom IN ({ph})))"
            )
            mp_args.extend(ops); mp_args.extend(ops)
    if dossiers:
        ph = ",".join("?" * len(dossiers))
        mp_where.append(f"mm.no_dossier IN ({ph})")
        mp_args.extend(dossiers)
    if machines:
        ph = ",".join("?" * len(machines))
        mp_where.append(f"mm.machine IN ({ph})")
        mp_args.extend(machines)

    mp_sql = f"""
        SELECT
          mm.id, mm.matiere_id, mm.type_mouvement, mm.quantite,
          mm.quantite_avant, mm.quantite_apres, mm.ref_bl, mm.note,
          mm.emplacement_source, mm.emplacement_dest,
          mm.created_at, mm.created_by, mm.created_by_name,
          mm.no_dossier, mm.machine, mm.client, mm.designation, mm.laize_id,
          mp.reference AS matiere_reference,
          mp.designation AS matiere_designation,
          u.email AS created_by_email
        FROM mp_mouvements mm
        LEFT JOIN matieres_premieres mp ON mp.id = mm.matiere_id
        LEFT JOIN users u ON u.id = mm.created_by
        WHERE {" AND ".join(mp_where)}
        ORDER BY mm.created_at DESC
        LIMIT ?
    """
    for r in conn.execute(mp_sql, mp_args + [limit]).fetchall():
        norm = _normalize_stock_mp_row(dict(r))
        if norm:
            result.append(norm)

    return result


@router.get("/api/saisies/reassign/fictif-sources")
def list_fictif_dossier_sources(request: Request):
    """Dossiers fictifs (FICTIF:…) présents dans les saisies."""
    user = get_current_user(request)
    if is_fabrication(user):
        raise HTTPException(status_code=403, detail="Action réservée aux administrateurs")
    with get_db() as conn:
        rows = conn.execute(
            """SELECT no_dossier, COUNT(*) AS nb_saisies
               FROM production_data
               WHERE no_dossier IS NOT NULL AND TRIM(no_dossier) != ''
                 AND UPPER(no_dossier) LIKE 'FICTIF:%'
               GROUP BY no_dossier
               ORDER BY no_dossier"""
        ).fetchall()
    out = []
    for r in rows:
        nd = str(r["no_dossier"] or "").strip()
        if not nd:
            continue
        out.append(
            {
                "no_dossier": nd,
                "of_display": _fictif_of_display(nd),
                "nb_saisies": int(r["nb_saisies"] or 0),
            }
        )
    return out


@router.get("/api/saisies/reassign/target-dossiers")
def suggest_target_dossiers(request: Request, q: str = "", limit: int = 20):
    """Suggestions de dossiers réels (planning + production), hors FICTIF:."""
    user = get_current_user(request)
    if is_fabrication(user):
        raise HTTPException(status_code=403, detail="Action réservée aux administrateurs")
    qn = (q or "").strip()
    try:
        lim = max(1, min(int(limit), 50))
    except Exception:
        lim = 20
    like = f"%{qn}%"
    seen: set[str] = set()
    out: list[dict] = []

    with get_db() as conn:
        if qn:
            plan_rows = conn.execute(
                """SELECT reference, numero_of, client, description, statut
                   FROM planning_entries
                   WHERE TRIM(COALESCE(reference,'')) != ''
                     AND (
                       LOWER(reference) LIKE LOWER(?)
                       OR LOWER(COALESCE(numero_of,'')) LIKE LOWER(?)
                       OR LOWER(COALESCE(client,'')) LIKE LOWER(?)
                     )
                   ORDER BY CASE statut WHEN 'en_cours' THEN 0 WHEN 'attente' THEN 1 ELSE 2 END,
                            reference
                   LIMIT ?""",
                (like, like, like, lim * 2),
            ).fetchall()
        else:
            plan_rows = conn.execute(
                """SELECT reference, numero_of, client, description, statut
                   FROM planning_entries
                   WHERE TRIM(COALESCE(reference,'')) != ''
                   ORDER BY updated_at DESC
                   LIMIT ?""",
                (lim,),
            ).fetchall()

        for r in plan_rows:
            nd = (r["numero_of"] or r["reference"] or "").strip()
            if not nd or _is_fictif_dossier(nd) or nd in seen:
                continue
            seen.add(nd)
            out.append(
                {
                    "no_dossier": nd,
                    "reference": (r["reference"] or "").strip(),
                    "numero_of": (r["numero_of"] or "").strip(),
                    "client": (r["client"] or "").strip(),
                    "description": (r["description"] or "").strip(),
                    "statut": r["statut"],
                    "source": "planning",
                }
            )
            if len(out) >= lim:
                break

        if len(out) < lim and qn:
            prod_rows = conn.execute(
                """SELECT DISTINCT no_dossier, client, designation
                   FROM production_data
                   WHERE no_dossier IS NOT NULL AND TRIM(no_dossier) != ''
                     AND UPPER(no_dossier) NOT LIKE 'FICTIF:%'
                     AND LOWER(no_dossier) LIKE LOWER(?)
                   ORDER BY no_dossier
                   LIMIT ?""",
                (like, lim),
            ).fetchall()
            for r in prod_rows:
                nd = str(r["no_dossier"] or "").strip()
                if not nd or nd in seen:
                    continue
                seen.add(nd)
                out.append(
                    {
                        "no_dossier": nd,
                        "reference": nd,
                        "numero_of": "",
                        "client": (r["client"] or "").strip(),
                        "description": (r["description"] or "").strip(),
                        "statut": None,
                        "source": "production",
                    }
                )
                if len(out) >= lim:
                    break

    return out[:lim]


@router.post("/api/saisies/reassign/fictif")
async def reassign_fictif_dossier(request: Request):
    """Rattache toutes les saisies d'un dossier FICTIF:… à un dossier réel existant."""
    user = get_current_user(request)
    if is_fabrication(user):
        raise HTTPException(status_code=403, detail="Action réservée aux administrateurs")
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Action réservée aux administrateurs")

    body = await request.json()
    from_raw = (body.get("from_no_dossier") or body.get("from") or "").strip()
    to_raw = (body.get("to_no_dossier") or body.get("to") or "").strip()
    if not from_raw or not to_raw:
        raise HTTPException(status_code=400, detail="from_no_dossier et to_no_dossier requis")

    from_ref = _normalize_fictif_no_dossier(from_raw)
    if from_ref.lower() == to_raw.strip().lower():
        raise HTTPException(status_code=400, detail="Le dossier cible doit être différent du fictif")

    now = datetime.now().isoformat()
    note = f"Rattachement {from_ref} → {to_raw.strip()}"

    with get_db() as conn:
        target = _resolve_target_dossier_meta(conn, to_raw)
        to_ref = target["no_dossier"]
        client = target.get("client") or ""
        designation = target.get("designation") or ""

        rows = conn.execute(
            "SELECT id, data FROM production_data WHERE TRIM(no_dossier) = TRIM(?)",
            (from_ref,),
        ).fetchall()
        if not rows:
            raise HTTPException(status_code=404, detail=f"Aucune saisie pour {from_ref}")

        updated_saisies = 0
        for r in rows:
            data = {}
            if r["data"]:
                try:
                    data = json.loads(r["data"])
                except Exception:
                    data = {}
            if not isinstance(data, dict):
                data = {}
            data["no_dossier"] = to_ref
            if client:
                data["client"] = client
            if designation:
                data["designation"] = designation
            conn.execute(
                """UPDATE production_data SET
                   no_dossier=?, client=?, designation=?, data=?,
                   modifie_par=?, modifie_le=?, modifie_note=?
                   WHERE id=?""",
                (
                    to_ref,
                    client or None,
                    designation or None,
                    json.dumps(data, default=str),
                    user["email"],
                    now,
                    note,
                    r["id"],
                ),
            )
            updated_saisies += 1

        mat_res = conn.execute(
            "UPDATE fab_matieres_utilisees SET no_dossier=? WHERE TRIM(no_dossier)=TRIM(?)",
            (to_ref, from_ref),
        )
        updated_matieres = mat_res.rowcount

        link_rows = conn.execute(
            "SELECT id, planning_entry_id FROM rent_prod_links WHERE TRIM(no_dossier)=TRIM(?)",
            (from_ref,),
        ).fetchall()
        updated_links = 0
        for lk in link_rows:
            dup = conn.execute(
                "SELECT 1 FROM rent_prod_links WHERE planning_entry_id=? AND TRIM(no_dossier)=TRIM(?)",
                (lk["planning_entry_id"], to_ref),
            ).fetchone()
            if dup:
                conn.execute("DELETE FROM rent_prod_links WHERE id=?", (lk["id"],))
            else:
                conn.execute(
                    "UPDATE rent_prod_links SET no_dossier=? WHERE id=?",
                    (to_ref, lk["id"]),
                )
                updated_links += 1

        conn.commit()

    return {
        "success": True,
        "from_no_dossier": from_ref,
        "to_no_dossier": to_ref,
        "updated_saisies": updated_saisies,
        "updated_matieres": updated_matieres,
        "updated_links": updated_links,
        "target": target,
    }


@router.put("/api/saisies/{row_id}")
async def update_saisie(row_id: int, request: Request):
    user = get_current_user(request)
    if is_fabrication(user):
        raise HTTPException(status_code=403, detail="Modification non autorisée — rôle Fabrication")
    body = await request.json()
    with get_db() as conn:
        ex = conn.execute("SELECT * FROM production_data WHERE id=?", (row_id,)).fetchone()
        if not ex: raise HTTPException(status_code=404, detail="Ligne non trouvée")
        # Pour fabrication: utiliser nom si operateur_lie n'est pas défini
        user_operateur = user.get("operateur_lie") or user.get("nom") or ""
        if not is_admin(user) and ex["operateur"] != user_operateur:
            raise HTTPException(status_code=403, detail="Modification non autorisée")

        # Opérateur : modifiable uniquement par admin.
        operateur_new = (body.get("operateur") if "operateur" in body else ex["operateur"]) or ""
        operateur_new = str(operateur_new).strip()
        if not is_admin(user):
            operateur_new = ex["operateur"]
        if not operateur_new:
            raise HTTPException(status_code=400, detail="Opérateur manquant")

        op_str = body.get("operation", ex["operation"]) or ""
        cl = classify_operation(op_str)
        new_data = json.loads(ex["data"]) if ex["data"] else {}
        date_op = normalize_date_operation(body.get("date_operation", ex["date_operation"]))
        new_data.update(body)
        new_data["date_operation"] = date_op
        new_data["operateur"] = operateur_new

        def _ex(col): return ex[col] if col in ex.keys() else None
        conn.execute(
            """UPDATE production_data SET
               operateur=?,
               operation=?,operation_code=?,operation_severity=?,operation_category=?,
               date_operation=?,machine=?,no_dossier=?,client=?,designation=?,
               quantite_a_traiter=?,quantite_traitee=?,
               metrage_prevu=?,metrage_reel=?,
               metrage_total_debut=?,metrage_total_fin=?,
               commentaire=?,
               modifie_par=?,modifie_le=?,modifie_note=?,data=? WHERE id=?""",
            (operateur_new,
             op_str, cl["code"], cl["severity"], cl["category"],
             date_op,
             body.get("machine",     _ex("machine")),
             body.get("no_dossier",  _ex("no_dossier")),
             body.get("client",      _ex("client")),
             body.get("designation", _ex("designation")),
             parse_french_number(body.get("quantite_a_traiter", _ex("quantite_a_traiter"))),
             parse_french_number(body.get("quantite_traitee",   _ex("quantite_traitee"))),
             body.get("metrage_prevu")       if "metrage_prevu"       in body else _ex("metrage_prevu"),
             body.get("metrage_reel")        if "metrage_reel"        in body else _ex("metrage_reel"),
             body.get("metrage_total_debut") if "metrage_total_debut" in body else _ex("metrage_total_debut"),
             body.get("metrage_total_fin")   if "metrage_total_fin"   in body else _ex("metrage_total_fin"),
             body.get("commentaire")         if "commentaire"         in body else _ex("commentaire"),
             user["email"], datetime.now().isoformat(), body.get("note", ""),
             json.dumps(new_data, default=str), row_id)
        )
        conn.commit()
    return {"success": True}


@router.post("/api/saisies")
async def add_saisie(request: Request):
    user = get_current_user(request)
    if is_fabrication(user):
        raise HTTPException(status_code=403, detail="Ajout non autorisé — rôle Fabrication")
    body = await request.json()

    op_str = (body.get("operation") or "").strip()
    if not op_str:
        raise HTTPException(status_code=400, detail="Le champ Opération est obligatoire")
    cl = classify_operation(op_str)

    operateur = (body.get("operateur") or "").strip()
    if not is_admin(user):
        operateur = user.get("operateur_lie", "") or ""
    if not operateur:
        raise HTTPException(status_code=400, detail="Opérateur manquant")

    date_op = (body.get("date_operation") or "").strip()
    if not date_op or date_op == "Invalid Date":
        date_op = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    date_op = normalize_date_operation(date_op)

    no_dossier   = (body.get("no_dossier")  or "").strip() or None
    machine      = (body.get("machine")     or "").strip() or None
    client       = (body.get("client")      or "").strip() or None
    designation  = (body.get("designation") or "").strip() or None
    service      = (body.get("service")     or "").strip() or None
    commentaire  = (body.get("commentaire") or "").strip() or None
    qte_a = parse_french_number(body.get("quantite_a_traiter", 0))
    qte_t = parse_french_number(body.get("quantite_traitee",   0))
    met_p   = body.get("metrage_prevu")       or None
    met_r   = body.get("metrage_reel")        or None
    met_td  = body.get("metrage_total_debut") or None
    met_tf  = body.get("metrage_total_fin")   or None

    row_dict = {"operateur": operateur, "date_operation": date_op,
                "operation": op_str, "no_dossier": no_dossier,
                "machine": machine, "quantite_a_traiter": qte_a,
                "quantite_traitee": qte_t, "commentaire": commentaire}
    try:
        with get_db() as conn:
            cursor = conn.execute(
                """INSERT INTO production_data
                   (import_id,operateur,date_operation,operation,operation_code,
                    operation_severity,operation_category,machine,no_dossier,client,
                    designation,quantite_a_traiter,quantite_traitee,service,
                    metrage_prevu,metrage_reel,metrage_total_debut,metrage_total_fin,
                    commentaire,data,est_manuel,modifie_par,modifie_le,modifie_note)
                   VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?,?)""",
                (operateur, date_op, op_str, cl["code"], cl["severity"], cl["category"],
                 machine, no_dossier, client, designation, qte_a, qte_t, service,
                 met_p, met_r, met_td, met_tf, commentaire,
                 json.dumps(row_dict, default=str),
                 user["email"], datetime.now().isoformat(),
                 body.get("note", "Ajout manuel"))
            )
            conn.commit()
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur : {str(e)}")
    return {"success": True, "id": cursor.lastrowid}


@router.delete("/api/saisies/bulk")
async def bulk_delete(request: Request):
    user = get_current_user(request)
    if is_fabrication(user):
        raise HTTPException(status_code=403, detail="Suppression non autorisée")
    body = await request.json()
    ids = body.get("ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="Aucun id fourni")
    deleted = 0
    with get_db() as conn:
        for row_id in ids:
            ex = conn.execute("SELECT * FROM production_data WHERE id=?", (row_id,)).fetchone()
            if not ex: continue
            if not is_admin(user) and (not ex["est_manuel"] or ex["modifie_par"] != user["email"]):
                continue
            conn.execute("DELETE FROM production_data WHERE id=?", (row_id,))
            deleted += 1
        conn.commit()
    return {"success": True, "deleted": deleted}


@router.delete("/api/saisies/{row_id}")
def delete_saisie(row_id: int, request: Request):
    user = get_current_user(request)
    if is_fabrication(user):
        raise HTTPException(status_code=403, detail="Suppression non autorisée")
    with get_db() as conn:
        ex = conn.execute("SELECT * FROM production_data WHERE id=?", (row_id,)).fetchone()
        if not ex: raise HTTPException(status_code=404, detail="Ligne non trouvée")
        if not is_admin(user) and (not ex["est_manuel"] or ex["modifie_par"] != user["email"]):
            raise HTTPException(status_code=403, detail="Suppression non autorisée")
        conn.execute("DELETE FROM production_data WHERE id=?", (row_id,))
        conn.commit()
    return {"success": True}


@router.get("/api/saisies/export-modifiees")
def export_saisies_modifiees(request: Request):
    user = get_current_user(request)
    # Pour fabrication: utiliser nom si operateur_lie n'est pas défini
    user_operateur = user.get("operateur_lie") or user.get("nom") or ""
    where = ["(est_manuel=1 OR modifie_par IS NOT NULL)"]
    params = []
    if is_fabrication(user):
        if user_operateur:
            where.append("operateur=?"); params.append(user_operateur)
        else:
            raise HTTPException(status_code=403, detail="Compte non lié")
    with get_db() as conn:
        rows = conn.execute(
            f"""SELECT operateur,date_operation,operation,operation_code,operation_severity,
                       machine,no_dossier,client,designation,quantite_a_traiter,quantite_traitee,
                       metrage_prevu,metrage_reel,commentaire,
                       est_manuel,modifie_par,modifie_le,modifie_note
                FROM production_data WHERE {" AND ".join(where)}
                ORDER BY date_operation ASC""", params
        ).fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail="Aucune saisie modifiée")
    df = pd.DataFrame([dict(r) for r in rows])
    df.rename(columns={
        "operateur":"Opérateur","date_operation":"Date","operation":"Opération",
        "operation_code":"Code","operation_severity":"Sévérité","machine":"Machine",
        "no_dossier":"No Dossier","client":"Client","designation":"Désignation",
        "quantite_a_traiter":"Qté prévue","quantite_traitee":"Qté traitée",
        "metrage_prevu":"Métrage prévu (m)","metrage_reel":"Métrage réel (m)",
        "metrage_total_debut":"Métrage total début (m)","metrage_total_fin":"Métrage total fin (m)",
        "commentaire":"Commentaire",
        "est_manuel":"Ajout manuel","modifie_par":"Modifié par",
        "modifie_le":"Modifié le","modifie_note":"Note",
    }, inplace=True)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Saisies modifiées")
    buf.seek(0)
    return StreamingResponse(buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="saisies_modifiees.xlsx"'})


@router.get("/api/saisies/export")
def export_saisies(
    request: Request,
    operateur: Optional[List[str]] = Query(default=None),
    no_dossier: Optional[List[str]] = Query(default=None),
    machine: Optional[List[str]] = Query(default=None),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    """Export Excel des saisies avec les filtres appliqués (même filtres que /api/saisies)."""
    user = get_current_user(request)
    # Pour fabrication: utiliser nom si operateur_lie n'est pas défini
    user_operateur = user.get("operateur_lie") or user.get("nom") or ""
    operateurs = [o for o in (operateur or []) if o]
    dossiers   = [d for d in (no_dossier or []) if d]
    machines   = [m for m in (machine or []) if m]

    where, params = ["1=1"], []
    # Toujours masquer les saisies obsoletes sur la machine Repiquage
    # (Debut/Fin de production, Arrivee/Depart personnel).
    where.append(_REPIQUAGE_HIDE_FILTER)
    if can_view_all_prod(user):
        if operateurs:
            where.append(f"operateur IN ({','.join('?'*len(operateurs))})")
            params.extend(operateurs)
        if dossiers:
            where.append(f"no_dossier IN ({','.join('?'*len(dossiers))})")
            params.extend(dossiers)
    else:
        # Pour fabrication: filtrer par operateur_lie ou nom utilisateur
        if user_operateur:
            where.append("operateur = ?"); params.append(user_operateur)
        else:
            where.append("1=0")
    if date_from: where.append("date_operation >= ?"); params.append(date_from)
    if date_to:   where.append("date_operation <= ?"); params.append(date_to+'T23:59:59')

    with get_db() as conn:
        if machines:
            append_machine_filter(where, params, conn, machines)
        wc = " AND ".join(where)
        rows = conn.execute(
            f"""SELECT id,operateur,date_operation,operation,operation_code,
                       operation_severity,operation_category,machine,no_dossier,client,designation,
                       quantite_a_traiter,quantite_traitee,metrage_prevu,metrage_reel,
                       metrage_total_debut,metrage_total_fin,
                       commentaire,service,est_manuel,modifie_par,modifie_le,modifie_note
                FROM production_data WHERE {wc}
                ORDER BY date_operation ASC, id ASC""",
            params
        ).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="Aucune saisie à exporter")

    df = pd.DataFrame([dict(r) for r in rows])
    df.rename(columns={
        "id":"ID","operateur":"Opérateur","date_operation":"Date","operation":"Opération",
        "operation_code":"Code","operation_severity":"Sévérité","operation_category":"Catégorie",
        "machine":"Machine","no_dossier":"No Dossier","client":"Client","designation":"Désignation",
        "quantite_a_traiter":"Qté prévue","quantite_traitee":"Qté traitée",
        "metrage_prevu":"Métrage prévu (m)","metrage_reel":"Métrage réel (m)",
        "metrage_total_debut":"Métrage total début (m)","metrage_total_fin":"Métrage total fin (m)",
        "commentaire":"Commentaire","service":"Service",
        "est_manuel":"Ajout manuel","modifie_par":"Modifié par",
        "modifie_le":"Modifié le","modifie_note":"Note",
    }, inplace=True)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Saisies")
    buf.seek(0)
    return StreamingResponse(buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="saisies.xlsx"'})

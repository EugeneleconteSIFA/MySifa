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

router = APIRouter()

def normalize_date_operation(val):
    dt = parse_datetime(val)
    return dt.strftime('%Y-%m-%dT%H:%M:%S') if dt else val


@router.get("/api/saisies")
def list_saisies(
    request: Request,
    operateur: Optional[List[str]] = Query(default=None),
    no_dossier: Optional[List[str]] = Query(default=None),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 500, offset: int = 0,
):
    user = get_current_user(request)
    operateurs = [o for o in (operateur or []) if o]
    dossiers   = [d for d in (no_dossier or []) if d]

    where, params = ["1=1"], []
    if can_view_all_prod(user):
        if operateurs:
            where.append(f"operateur IN ({','.join('?'*len(operateurs))})")
            params.extend(operateurs)
        if dossiers:
            where.append(f"no_dossier IN ({','.join('?'*len(dossiers))})")
            params.extend(dossiers)
    else:
        if user.get("operateur_lie"):
            where.append("operateur = ?"); params.append(user["operateur_lie"])
        else:
            where.append("1=0")
    if date_from: where.append("date_operation >= ?"); params.append(date_from)
    if date_to:   where.append("date_operation <= ?"); params.append(date_to+'T23:59:59')
    wc = " AND ".join(where)

    with get_db() as conn:
        total = conn.execute(f"SELECT COUNT(*) as c FROM production_data WHERE {wc}", params).fetchone()["c"]
        rows  = conn.execute(
            f"""SELECT id,import_id,operateur,date_operation,operation,operation_code,
                       operation_severity,operation_category,machine,no_dossier,client,designation,
                       quantite_a_traiter,quantite_traitee,metrage_prevu,metrage_reel,
                       commentaire,service,est_manuel,modifie_par,modifie_le,modifie_note
                FROM production_data WHERE {wc}
                ORDER BY date_operation ASC, id ASC LIMIT ? OFFSET ?""",
            params + [limit, offset]
        ).fetchall()
    return {"total": total, "rows": [dict(r) for r in rows]}


@router.put("/api/saisies/{row_id}")
async def update_saisie(row_id: int, request: Request):
    user = get_current_user(request)
    if is_fabrication(user):
        raise HTTPException(status_code=403, detail="Modification non autorisée — rôle Fabrication")
    body = await request.json()
    with get_db() as conn:
        ex = conn.execute("SELECT * FROM production_data WHERE id=?", (row_id,)).fetchone()
        if not ex: raise HTTPException(status_code=404, detail="Ligne non trouvée")
        if not is_admin(user) and ex["operateur"] != user.get("operateur_lie"):
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

        conn.execute(
            """UPDATE production_data SET
               operateur=?,
               operation=?,operation_code=?,operation_severity=?,operation_category=?,
               date_operation=?,machine=?,no_dossier=?,client=?,designation=?,
               quantite_a_traiter=?,quantite_traitee=?,
               metrage_prevu=?,metrage_reel=?,commentaire=?,
               modifie_par=?,modifie_le=?,modifie_note=?,data=? WHERE id=?""",
            (operateur_new,
             op_str, cl["code"], cl["severity"], cl["category"],
             date_op,
             body.get("machine",        ex["machine"]),
             body.get("no_dossier",     ex["no_dossier"]),
             body.get("client",         ex["client"]),
             body.get("designation",    ex["designation"]),
             parse_french_number(body.get("quantite_a_traiter", ex["quantite_a_traiter"])),
             parse_french_number(body.get("quantite_traitee",   ex["quantite_traitee"])),
             body.get("metrage_prevu") if "metrage_prevu" in body else ex["metrage_prevu"] if "metrage_prevu" in ex.keys() else None,
             body.get("metrage_reel")  if "metrage_reel"  in body else ex["metrage_reel"]  if "metrage_reel"  in ex.keys() else None,
             body.get("commentaire")   if "commentaire"  in body else ex["commentaire"] if "commentaire" in ex.keys() else None,
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
    met_p = body.get("metrage_prevu") or None
    met_r = body.get("metrage_reel")  or None

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
                    metrage_prevu,metrage_reel,commentaire,
                    data,est_manuel,modifie_par,modifie_le,modifie_note)
                   VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?,?)""",
                (operateur, date_op, op_str, cl["code"], cl["severity"], cl["category"],
                 machine, no_dossier, client, designation, qte_a, qte_t, service,
                 met_p, met_r, commentaire,
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
    where = ["(est_manuel=1 OR modifie_par IS NOT NULL)"]
    params = []
    if is_fabrication(user):
        if user.get("operateur_lie"):
            where.append("operateur=?"); params.append(user["operateur_lie"])
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

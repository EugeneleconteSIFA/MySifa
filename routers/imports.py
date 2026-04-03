"""SIFA — Imports v0.8 — extraction métrages (premier nombre après '=')"""
import os, json, io, re
import pandas as pd
from datetime import datetime
from fastapi import APIRouter, Request, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from database import get_db, parse_file, map_columns, parse_french_number, is_duplicate, parse_datetime
from config import UPLOAD_DIR, classify_operation
from services.auth_service import require_admin

router = APIRouter()


def extract_metrage(val):
    """
    Extrait le premier nombre après le premier '=' dans une chaîne matière.
    Ex: '886 0314  L:510 = 23353 + 1 0003  L:510 = ...' → 23353.0
    Retourne None si pas de '=' ou pas de nombre.
    """
    if not val:
        return None
    s = str(val)
    idx = s.find('=')
    if idx == -1:
        return None
    after = s[idx+1:].strip()
    # Premier nombre (entier ou décimal) après le '='
    m = re.match(r'[\s]*([\d\s]+)', after)
    if m:
        try:
            return float(m.group(1).replace(' ', ''))
        except ValueError:
            return None
    return None


# Ajout des colonnes matières dans le COLUMN_MAP de database.py
# On les mappe ici directement pour l'import
MATIERE_COLS_PREVUES = [
    "matières prévues", "matieres prevues", "matière prévue", "matiere prevue"
]
MATIERE_COLS_REELLES = [
    "matières utilisées", "matieres utilisees", "matière utilisée", "matiere utilisee"
]

def find_matiere_col(df_cols, candidates):
    """Trouve la colonne matière dans le dataframe."""
    for col in df_cols:
        if col.strip().lower() in candidates:
            return col
    return None


@router.post("/api/import")
async def import_file(request: Request, file: UploadFile = File(...)):
    require_admin(request)
    contents = await file.read()
    filename = file.filename or "unknown"
    save_path = os.path.join(UPLOAD_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}")
    with open(save_path, "wb") as f:
        f.write(contents)

    try:
        df = parse_file(contents, filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    df.columns = [str(c).strip() for c in df.columns]
    col_map = map_columns(df)

    # Détection colonnes matières
    col_mat_prev = find_matiere_col(df.columns, MATIERE_COLS_PREVUES)
    col_mat_reel = find_matiere_col(df.columns, MATIERE_COLS_REELLES)

    # Pré-calculer une correspondance "champ logique" → "nom de colonne d'origine".
    # Permet d'éviter de parcourir col_map à chaque appel de g(field) dans la boucle.
    field_to_orig = {}
    for orig, mapped in col_map.items():
        if mapped not in field_to_orig:
            field_to_orig[mapped] = orig

    classify_cache = {}

    inserted = doublons = 0

    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO imports (filename,imported_at,row_count,columns,file_path) VALUES (?,?,?,?,?)",
            (filename, datetime.now().isoformat(), len(df),
             json.dumps(list(df.columns)), save_path)
        )
        import_id = cursor.lastrowid

        for _, row in df.iterrows():
            row_dict = {str(k): None if pd.isna(v) else str(v) for k, v in row.items()}

            op_str    = row_dict.get(field_to_orig.get("operation")) or ""
            if op_str in classify_cache:
                cl = classify_cache[op_str]
            else:
                cl = classify_cache[op_str] = classify_operation(op_str)

            operateur = row_dict.get(field_to_orig.get("operateur"))
            _raw_date = row_dict.get(field_to_orig.get("date_operation"))
            _dt = parse_datetime(_raw_date)
            date_op = _dt.strftime('%Y-%m-%dT%H:%M:%S') if _dt else _raw_date
            if isinstance(row_dict, dict) and 'date_operation' in row_dict:
                row_dict['date_operation'] = date_op
            no_dos    = row_dict.get(field_to_orig.get("no_dossier"))

            if is_duplicate(conn, operateur, date_op, cl["code"], no_dos):
                doublons += 1
                continue

            # Extraction métrages
            metrage_prevu = extract_metrage(row_dict.get(col_mat_prev) if col_mat_prev else None)
            metrage_reel  = extract_metrage(row_dict.get(col_mat_reel)  if col_mat_reel  else None)

            conn.execute(
                """INSERT INTO production_data
                   (import_id,operateur,date_operation,operation,operation_code,
                    operation_severity,operation_category,service,machine,no_dossier,
                    client,designation,quantite_a_traiter,quantite_traitee,
                    no_cde,date_exp,date_liv,type_dossier,data,est_manuel,
                    metrage_prevu,metrage_reel)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,?,?)""",
                (import_id, operateur, date_op, op_str.strip(),
                 cl["code"], cl["severity"], cl["category"],
                 row_dict.get(field_to_orig.get("service")),
                 row_dict.get(field_to_orig.get("machine")),
                 no_dos,
                 row_dict.get(field_to_orig.get("client")),
                 row_dict.get(field_to_orig.get("designation")),
                 parse_french_number(row_dict.get(field_to_orig.get("quantite_a_traiter"))),
                 parse_french_number(row_dict.get(field_to_orig.get("quantite_traitee"))),
                 row_dict.get(field_to_orig.get("no_cde")),
                 row_dict.get(field_to_orig.get("date_exp")),
                 row_dict.get(field_to_orig.get("date_liv")),
                 row_dict.get(field_to_orig.get("type_dossier")),
                 json.dumps(row_dict, default=str),
                 metrage_prevu, metrage_reel)
            )
            inserted += 1

        conn.execute("UPDATE imports SET row_count=? WHERE id=?", (inserted, import_id))
        conn.commit()

    return {
        "success": True, "import_id": import_id, "filename": filename,
        "rows_imported": inserted, "doublons_ignores": doublons,
        "columns": list(df.columns), "mapped_columns": col_map,
        "metrages": {
            "colonne_prevue": col_mat_prev,
            "colonne_reelle": col_mat_reel,
        }
    }


@router.get("/api/imports")
def list_imports(request: Request):
    require_admin(request)
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM imports ORDER BY imported_at DESC").fetchall()
    return [dict(r) for r in rows]


@router.get("/api/imports/{import_id}/data")
def get_import_data(import_id: int, request: Request, limit: int = 500, offset: int = 0):
    require_admin(request)
    with get_db() as conn:
        imp = conn.execute("SELECT * FROM imports WHERE id=?", (import_id,)).fetchone()
        if not imp:
            raise HTTPException(status_code=404, detail="Import non trouvé")
        rows = conn.execute(
            "SELECT data FROM production_data WHERE import_id=? LIMIT ? OFFSET ?",
            (import_id, limit, offset)
        ).fetchall()
    return {"import": dict(imp), "data": [json.loads(r["data"]) for r in rows], "total": imp["row_count"]}


@router.delete("/api/imports/{import_id}")
def delete_import(import_id: int, request: Request):
    require_admin(request)
    with get_db() as conn:
        imp = conn.execute("SELECT * FROM imports WHERE id=?", (import_id,)).fetchone()
        if not imp:
            raise HTTPException(status_code=404, detail="Import non trouvé")
        deleted = conn.execute(
            "DELETE FROM production_data WHERE import_id=?", (import_id,)
        ).rowcount
        conn.execute("DELETE FROM imports WHERE id=?", (import_id,))
        conn.commit()
    fp = imp["file_path"]
    if fp and os.path.exists(fp):
        try:
            os.remove(fp)
        except Exception:
            pass
    return {"success": True, "lignes_supprimees": deleted}


@router.get("/api/imports/{import_id}/export")
def export_import(import_id: int, request: Request):
    require_admin(request)
    with get_db() as conn:
        imp = conn.execute("SELECT * FROM imports WHERE id=?", (import_id,)).fetchone()
        if not imp:
            raise HTTPException(status_code=404, detail="Import non trouvé")
        rows = conn.execute(
            """SELECT operateur,date_operation,operation,operation_code,operation_severity,
                      machine,no_dossier,client,designation,quantite_a_traiter,quantite_traitee,
                      metrage_prevu,metrage_reel,commentaire,service,
                      est_manuel,modifie_par,modifie_le,modifie_note
               FROM production_data WHERE import_id=? ORDER BY date_operation ASC""",
            (import_id,)
        ).fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail="Aucune donnée")
    df = pd.DataFrame([dict(r) for r in rows])
    df.rename(columns={
        "operateur": "Opérateur", "date_operation": "Date et Heure d'Opération",
        "operation": "Opération", "operation_code": "Code",
        "operation_severity": "Sévérité", "machine": "Machine",
        "no_dossier": "No Dossier", "client": "Client",
        "designation": "Désignation produit",
        "quantite_a_traiter": "Quantité à traiter",
        "quantite_traitee": "Quantité traitée",
        "metrage_prevu": "Métrage prévu (m)",
        "metrage_reel": "Métrage réel (m)",
        "commentaire": "Commentaire",
        "service": "Service",
        "est_manuel": "Ajout manuel", "modifie_par": "Modifié par",
        "modifie_le": "Modifié le", "modifie_note": "Note modification",
    }, inplace=True)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Saisies")
    buf.seek(0)
    safe = imp["filename"].rsplit(".", 1)[0]
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{safe}_export.xlsx"'}
    )

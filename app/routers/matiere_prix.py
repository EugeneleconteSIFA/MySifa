"""
SIFA — MyDevis : paramètres matière & base prix.
Accès : direction + superadmin uniquement.
"""
import io
import re
import unicodedata
from datetime import datetime
from typing import Any, Optional

import pandas as pd
from fastapi import APIRouter, Body, File, HTTPException, Query, Request, UploadFile

from database import get_db
from services.auth_service import get_current_user

router = APIRouter()


def _require_dir_super(request: Request) -> dict:
    user = get_current_user(request)
    if user["role"] not in ("superadmin", "direction"):
        raise HTTPException(
            status_code=403,
            detail="Accès réservé à la Direction et au super admin",
        )
    return user


def _norm_header(s: Any) -> str:
    t = str(s or "").strip().lower()
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9]+", "_", t)
    return t.strip("_")


def _cfg_dict(conn) -> dict[str, str]:
    rows = conn.execute("SELECT cle, valeur FROM matiere_config").fetchall()
    return {r["cle"]: r["valeur"] for r in rows}


def _marge_factor(conn) -> float:
    cfg = _cfg_dict(conn)
    try:
        m = float(cfg.get("marge_erreur", 5))
    except (TypeError, ValueError):
        m = 5.0
    return 1.0 + max(0.0, m) / 100.0


def _row_base_with_marge(conn, row: dict) -> dict:
    d = dict(row)
    fac = _marge_factor(conn)
    pc = d.get("prix_cohesio")
    pr = d.get("prix_rotoflex")
    try:
        d["prix_cohesio_majore"] = float(pc) * fac if pc is not None else None
    except (TypeError, ValueError):
        d["prix_cohesio_majore"] = None
    try:
        d["prix_rotoflex_majore"] = float(pr) * fac if pr is not None else None
    except (TypeError, ValueError):
        d["prix_rotoflex_majore"] = None
    return d


@router.get("/config")
def get_config(request: Request):
    _require_dir_super(request)
    with get_db() as conn:
        cfg = _cfg_dict(conn)
        try:
            marge = float(cfg.get("marge_erreur", 5))
        except (TypeError, ValueError):
            marge = 5.0
        try:
            taux = float(cfg.get("taux_change_usd", 0.85))
        except (TypeError, ValueError):
            taux = 0.85
    return {"marge_erreur": marge, "taux_change_usd": taux}


@router.post("/config")
def post_config(request: Request, body: dict = Body(...)):
    _require_dir_super(request)
    try:
        marge = body.get("marge_erreur")
        taux = body.get("taux_change_usd")
        now = datetime.now().isoformat()
        with get_db() as conn:
            if marge is not None:
                try:
                    mv = float(marge)
                except (TypeError, ValueError):
                    mv = 5.0
                mv = max(0.0, min(50.0, mv))
                conn.execute(
                    """INSERT INTO matiere_config (cle, valeur, updated_at) VALUES (?,?,?)
                       ON CONFLICT(cle) DO UPDATE SET valeur=excluded.valeur, updated_at=excluded.updated_at""",
                    ("marge_erreur", str(mv), now),
                )
            if taux is not None:
                try:
                    tv = float(taux)
                except (TypeError, ValueError):
                    tv = 0.85
                conn.execute(
                    """INSERT INTO matiere_config (cle, valeur, updated_at) VALUES (?,?,?)
                       ON CONFLICT(cle) DO UPDATE SET valeur=excluded.valeur, updated_at=excluded.updated_at""",
                    ("taux_change_usd", str(tv), now),
                )
            conn.commit()
    except Exception:
        pass
    return get_config(request)


def _params_filters(q: Optional[str], categorie: Optional[str]):
    clauses: list[str] = ["1=1"]
    args: list[Any] = []
    if categorie and str(categorie).strip():
        clauses.append("LOWER(TRIM(categorie)) = LOWER(TRIM(?))")
        args.append(str(categorie).strip())
    if q and str(q).strip():
        qq = "%" + str(q).strip().lower() + "%"
        clauses.append(
            """(
            LOWER(COALESCE(categorie,'')) LIKE ?
            OR LOWER(COALESCE(code,'')) LIKE ?
            OR LOWER(COALESCE(designation,'')) LIKE ?
            OR LOWER(COALESCE(fournisseur,'')) LIKE ?
            OR LOWER(COALESCE(appellation,'')) LIKE ?
            OR LOWER(COALESCE(notes,'')) LIKE ?
            )"""
        )
        args.extend([qq, qq, qq, qq, qq, qq])
    return " AND ".join(clauses), args


@router.get("/params")
def list_params(
    request: Request,
    q: Optional[str] = None,
    categorie: Optional[str] = None,
):
    _require_dir_super(request)
    where, args = _params_filters(q, categorie)
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM matiere_params WHERE {where} ORDER BY categorie, code, id",
            args,
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("/params")
def create_param(request: Request, body: dict = Body(...)):
    _require_dir_super(request)
    cat = (body.get("categorie") or "").strip()
    code = (body.get("code") or "").strip()
    des = (body.get("designation") or "").strip()
    if not cat or not code or not des:
        raise HTTPException(status_code=400, detail="categorie, code et designation sont obligatoires")
    now = datetime.now().isoformat()
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO matiere_params (
                categorie, code, designation, fournisseur, poids_m2, prix_eur_m2, prix_usd_kg,
                taux_change, incidence_dollar, transport_total, appellation, grammage, notes, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                cat,
                code,
                des,
                body.get("fournisseur"),
                body.get("poids_m2"),
                body.get("prix_eur_m2"),
                body.get("prix_usd_kg"),
                body.get("taux_change", 1.0),
                body.get("incidence_dollar", 1.0),
                body.get("transport_total", 0),
                body.get("appellation"),
                body.get("grammage"),
                body.get("notes"),
                now,
            ),
        )
        conn.commit()
        rid = cur.lastrowid
        row = conn.execute("SELECT * FROM matiere_params WHERE id=?", (rid,)).fetchone()
    return dict(row)


@router.put("/params/{param_id}")
def update_param(request: Request, param_id: int, body: dict = Body(...)):
    _require_dir_super(request)
    now = datetime.now().isoformat()
    fields = [
        "categorie",
        "code",
        "designation",
        "fournisseur",
        "poids_m2",
        "prix_eur_m2",
        "prix_usd_kg",
        "taux_change",
        "incidence_dollar",
        "transport_total",
        "appellation",
        "grammage",
        "notes",
    ]
    sets = []
    args: list[Any] = []
    for f in fields:
        if f in body:
            sets.append(f"{f}=?")
            args.append(body[f])
    if not sets:
        raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour")
    sets.append("updated_at=?")
    args.append(now)
    args.append(param_id)
    with get_db() as conn:
        conn.execute(f"UPDATE matiere_params SET {', '.join(sets)} WHERE id=?", args)
        conn.commit()
        row = conn.execute("SELECT * FROM matiere_params WHERE id=?", (param_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Ligne introuvable")
    return dict(row)


@router.delete("/params/{param_id}")
def delete_param(request: Request, param_id: int):
    _require_dir_super(request)
    with get_db() as conn:
        conn.execute("DELETE FROM matiere_params WHERE id=?", (param_id,))
        conn.commit()
    return {"ok": True}


def _base_filters(q: Optional[str], frontal: Optional[str], type_: Optional[str]):
    clauses: list[str] = ["1=1"]
    args: list[Any] = []
    if frontal and str(frontal).strip():
        clauses.append("LOWER(TRIM(frontal)) = LOWER(TRIM(?))")
        args.append(str(frontal).strip())
    if type_ and str(type_).strip():
        clauses.append("LOWER(TRIM(type_adhesion)) = LOWER(TRIM(?))")
        args.append(str(type_).strip())
    if q and str(q).strip():
        qq = "%" + str(q).strip().lower() + "%"
        clauses.append(
            """(
            COALESCE(CAST(ref_interne AS TEXT),'') LIKE ?
            OR LOWER(COALESCE(designation,'')) LIKE ?
            OR LOWER(COALESCE(frontal,'')) LIKE ?
            OR LOWER(COALESCE(type_adhesion,'')) LIKE ?
            OR LOWER(COALESCE(adhesif,'')) LIKE ?
            OR LOWER(COALESCE(silicone,'')) LIKE ?
            OR LOWER(COALESCE(glassine,'')) LIKE ?
            OR LOWER(COALESCE(marqueur,'')) LIKE ?
            )"""
        )
        args.extend([qq, qq, qq, qq, qq, qq, qq, qq])
    return " AND ".join(clauses), args


@router.get("/base")
def list_base(
    request: Request,
    q: Optional[str] = None,
    frontal: Optional[str] = None,
    type_: Optional[str] = Query(None, alias="type"),
):
    _require_dir_super(request)
    where, args = _base_filters(q, frontal, type_)
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM matiere_base WHERE {where} ORDER BY frontal, designation, id",
            args,
        ).fetchall()
        return [_row_base_with_marge(conn, dict(r)) for r in rows]


@router.post("/base")
def create_base(request: Request, body: dict = Body(...)):
    _require_dir_super(request)
    des = (body.get("designation") or "").strip()
    if not des:
        raise HTTPException(status_code=400, detail="designation obligatoire")
    now = datetime.now().isoformat()
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO matiere_base (
                ref_interne, designation, frontal, type_adhesion, adhesif, silicone, glassine,
                marqueur, prix_cohesio, prix_rotoflex, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                body.get("ref_interne"),
                des,
                body.get("frontal"),
                body.get("type_adhesion"),
                body.get("adhesif"),
                body.get("silicone"),
                body.get("glassine"),
                body.get("marqueur"),
                body.get("prix_cohesio"),
                body.get("prix_rotoflex"),
                now,
            ),
        )
        conn.commit()
        rid = cur.lastrowid
        row = conn.execute("SELECT * FROM matiere_base WHERE id=?", (rid,)).fetchone()
        return _row_base_with_marge(conn, dict(row))


@router.put("/base/{base_id}")
def update_base(request: Request, base_id: int, body: dict = Body(...)):
    _require_dir_super(request)
    now = datetime.now().isoformat()
    fields = [
        "ref_interne",
        "designation",
        "frontal",
        "type_adhesion",
        "adhesif",
        "silicone",
        "glassine",
        "marqueur",
        "prix_cohesio",
        "prix_rotoflex",
    ]
    sets = []
    args: list[Any] = []
    for f in fields:
        if f in body:
            sets.append(f"{f}=?")
            args.append(body[f])
    if not sets:
        raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour")
    sets.append("updated_at=?")
    args.append(now)
    args.append(base_id)
    with get_db() as conn:
        conn.execute(f"UPDATE matiere_base SET {', '.join(sets)} WHERE id=?", args)
        conn.commit()
        row = conn.execute("SELECT * FROM matiere_base WHERE id=?", (base_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Ligne introuvable")
        return _row_base_with_marge(conn, dict(row))


@router.delete("/base/{base_id}")
def delete_base(request: Request, base_id: int):
    _require_dir_super(request)
    with get_db() as conn:
        conn.execute("DELETE FROM matiere_base WHERE id=?", (base_id,))
        conn.commit()
    return {"ok": True}


def _find_sheet(sheets: dict, *candidates: str) -> Optional[str]:
    norm_map = {_norm_header(k): k for k in sheets.keys()}
    for c in candidates:
        nk = _norm_header(c)
        if nk in norm_map:
            return norm_map[nk]
        if c in sheets:
            return c
    for k in sheets.keys():
        nk = _norm_header(k)
        for c in candidates:
            if nk == _norm_header(c):
                return k
    return None


def _pick_col(norm_cols: dict[str, str], *aliases: str) -> Optional[str]:
    for a in aliases:
        na = _norm_header(a)
        if na in norm_cols:
            return norm_cols[na]
    return None


def _float_cell(v: Any) -> Optional[float]:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip().replace("\u202f", "").replace("\xa0", "").replace(" ", "").replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _int_cell(v: Any) -> Optional[int]:
    f = _float_cell(v)
    if f is None:
        return None
    try:
        return int(round(f))
    except (TypeError, ValueError):
        return None


def _str_cell(v: Any) -> Optional[str]:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip()
    return s or None


@router.post("/import-excel")
async def import_excel(request: Request, file: UploadFile = File(...)):
    _require_dir_super(request)
    if not file.filename or not str(file.filename).lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="Fichier .xlsx ou .xlsm attendu")
    raw = await file.read()
    errors: list[str] = []
    imported_params = 0
    imported_base = 0
    try:
        sheets = pd.read_excel(io.BytesIO(raw), sheet_name=None, engine="openpyxl")
    except Exception as e:
        return {"imported_params": 0, "imported_base": 0, "errors": [f"Lecture Excel: {e}"]}

    sh_p = _find_sheet(sheets, "Parametres", "Paramètres", "parametres")
    sh_b = _find_sheet(sheets, "Base_matières", "Base_matieres", "Base matières")

    now = datetime.now().isoformat()

    with get_db() as conn:
        if sh_p:
            df = sheets[sh_p]
            df = df.dropna(how="all")
            if len(df.columns):
                norm_cols = {_norm_header(c): c for c in df.columns}
                c_cat = _pick_col(norm_cols, "categorie", "catégorie", "category")
                c_code = _pick_col(norm_cols, "code")
                c_des = _pick_col(norm_cols, "designation", "désignation", "libelle", "libellé")
                c_four = _pick_col(norm_cols, "fournisseur", "supplier")
                c_pm2 = _pick_col(norm_cols, "poids_m2", "poids m2", "poids_m", "kg_m2", "kg/m2")
                c_peur = _pick_col(norm_cols, "prix_eur_m2", "prix eur", "eur_m2", "€/m2", "eur m2")
                c_usd = _pick_col(norm_cols, "prix_usd_kg", "usd kg", "usd_kg", "$/kg")
                c_tx = _pick_col(norm_cols, "taux_change", "taux change", "taux", "change")
                c_inc = _pick_col(norm_cols, "incidence_dollar", "incidence", "incidence dollar")
                c_tr = _pick_col(norm_cols, "transport_total", "transport", "frais transport")
                c_app = _pick_col(norm_cols, "appellation")
                c_gr = _pick_col(norm_cols, "grammage", "g/m2", "gsm")
                c_notes = _pick_col(norm_cols, "notes", "remarques", "commentaire")
                used = {
                    c_cat,
                    c_code,
                    c_des,
                    c_four,
                    c_pm2,
                    c_peur,
                    c_usd,
                    c_tx,
                    c_inc,
                    c_tr,
                    c_app,
                    c_gr,
                    c_notes,
                }
                for idx, row in df.iterrows():
                    cat = _str_cell(c_cat and row.get(c_cat))
                    code = _str_cell(c_code and row.get(c_code))
                    des = _str_cell(c_des and row.get(c_des))
                    if not cat or not code or not des:
                        errors.append(f"Parametres ligne {idx}: categorie/code/designation manquants — ignoré")
                        continue
                    note_parts = []
                    if c_notes:
                        n0 = _str_cell(row.get(c_notes))
                        if n0:
                            note_parts.append(n0)
                    for ec in df.columns:
                        if ec in used or ec is None:
                            continue
                        v = row.get(ec)
                        if v is not None and not (isinstance(v, float) and pd.isna(v)) and str(v).strip():
                            note_parts.append(f"{ec}={v}")
                    notes_val = " | ".join(note_parts) if note_parts else None
                    txv = _float_cell(row.get(c_tx)) if c_tx else None
                    if txv is None:
                        txv = 1.0
                    incv = _float_cell(row.get(c_inc)) if c_inc else None
                    if incv is None:
                        incv = 1.0
                    try:
                        conn.execute(
                            """INSERT INTO matiere_params (
                                categorie, code, designation, fournisseur, poids_m2, prix_eur_m2, prix_usd_kg,
                                taux_change, incidence_dollar, transport_total, appellation, grammage, notes, updated_at
                            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (
                                cat,
                                code,
                                des,
                                _str_cell(c_four and row.get(c_four)) if c_four else None,
                                _float_cell(row.get(c_pm2)) if c_pm2 else None,
                                _float_cell(row.get(c_peur)) if c_peur else None,
                                _float_cell(row.get(c_usd)) if c_usd else None,
                                txv,
                                incv,
                                _float_cell(row.get(c_tr)) if c_tr else 0,
                                _str_cell(c_app and row.get(c_app)) if c_app else None,
                                _int_cell(row.get(c_gr)) if c_gr else None,
                                notes_val,
                                now,
                            ),
                        )
                        imported_params += 1
                    except Exception as e:
                        errors.append(f"Parametres ligne {idx}: {e}")
            else:
                errors.append("Feuille Parametres sans colonnes")
        else:
            errors.append("Feuille Parametres introuvable")

        if sh_b:
            df = sheets[sh_b]
            df = df.dropna(how="all")
            if len(df.columns):
                norm_cols = {_norm_header(c): c for c in df.columns}
                c_ref = _pick_col(norm_cols, "ref_interne", "ref", "reference", "réf", "ref.")
                c_des = _pick_col(norm_cols, "designation", "désignation", "libelle")
                c_front = _pick_col(norm_cols, "frontal", "papier frontal", "support")
                c_type = _pick_col(norm_cols, "type_adhesion", "type adhesion", "type", "adhesion")
                c_adh = _pick_col(norm_cols, "adhesif", "adhésif")
                c_sil = _pick_col(norm_cols, "silicone")
                c_gla = _pick_col(norm_cols, "glassine")
                c_mar = _pick_col(norm_cols, "marqueur")
                c_pc = _pick_col(norm_cols, "prix_cohesio", "cohesio", "cohésio", "prix cohesio")
                c_pr = _pick_col(norm_cols, "prix_rotoflex", "rotoflex", "prix rotoflex")
                for idx, row in df.iterrows():
                    des = _str_cell(c_des and row.get(c_des)) or _str_cell(row.get(df.columns[0]))
                    if not des:
                        errors.append(f"Base_matières ligne {idx}: designation manquante — ignoré")
                        continue
                    try:
                        conn.execute(
                            """INSERT INTO matiere_base (
                                ref_interne, designation, frontal, type_adhesion, adhesif, silicone, glassine,
                                marqueur, prix_cohesio, prix_rotoflex, updated_at
                            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                            (
                                _int_cell(row.get(c_ref)) if c_ref else None,
                                des,
                                _str_cell(c_front and row.get(c_front)) if c_front else None,
                                _str_cell(c_type and row.get(c_type)) if c_type else None,
                                _str_cell(c_adh and row.get(c_adh)) if c_adh else None,
                                _str_cell(c_sil and row.get(c_sil)) if c_sil else None,
                                _str_cell(c_gla and row.get(c_gla)) if c_gla else None,
                                _str_cell(c_mar and row.get(c_mar)) if c_mar else None,
                                _float_cell(row.get(c_pc)) if c_pc else None,
                                _float_cell(row.get(c_pr)) if c_pr else None,
                                now,
                            ),
                        )
                        imported_base += 1
                    except Exception as e:
                        errors.append(f"Base_matières ligne {idx}: {e}")
            else:
                errors.append("Feuille Base_matières sans colonnes")
        else:
            errors.append("Feuille Base_matières introuvable")

        conn.commit()

    return {"imported_params": imported_params, "imported_base": imported_base, "errors": errors}

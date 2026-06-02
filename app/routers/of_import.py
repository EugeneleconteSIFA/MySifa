"""MySifa — Import OF PDF pour MyProd."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from io import BytesIO
from typing import Any, Optional
from zoneinfo import ZoneInfo

import pdfplumber
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response

from config import UPLOAD_DIR
from database import get_db
from services.auth_service import get_current_user, require_superadmin

router = APIRouter()

_PARIS = ZoneInfo("Europe/Paris")
OF_UPLOAD_DIR = os.path.join(UPLOAD_DIR, "of")
OF_ALLOWED_ROLES = frozenset({"superadmin", "direction", "administration"})

OF_REAL_FIELDS = frozenset({
    "laize", "qte_adhesif_g", "qte_adhesif_kg", "qte_au_mille",
    "qte_bobines", "mandrin_longueur", "outil_1_hauteur",
})
OF_INT_FIELDS = frozenset({
    "nb_levees", "qte_etiquettes", "metrage", "nb_cartons",
    "nb_mandrins", "nb_tubes",
})

OF_DATA_FIELDS = [
    "of_numero", "date_creation", "delai_client", "reference", "machine",
    "laize", "format", "matiere", "ref_matiere", "glassine", "ref_adhesif",
    "qte_adhesif_g", "qte_adhesif_kg", "adhesif_label", "qte_au_mille", "nb_levees",
    "qte_etiquettes", "qte_bobines", "metrage", "conditionnement", "tolerance",
    "cartons_type", "nb_cartons", "mandrins_dia", "mandrin_longueur", "nb_mandrins",
    "nb_tubes", "bobinettes_completes", "outil_1_forme", "outil_1_numero",
    "outil_1_angle", "outil_1_mag", "outil_1_cp", "outil_1_hauteur", "outil_1_fournisseur",
    "outil_2_forme", "outil_2_numero", "outil_2_angle", "outil_2_cp",
    "outil_alt_forme", "outil_alt_numero", "outil_alt_angle", "outil_alt_fournisseur",
]

_PATTERNS = {
    # "OF n° 123456" ou "OF : 123456 + Stock" (un mot après +)
    "of_numero": r"OF\s*(?:n[°o]|n°|:)\s*(\d+(?:\s*\+\s*[\w]+)?)",
    "date_creation": r"Date cr[eé]a\.\s*([\d/]+)",
    "delai_client": r"D[eé]lai client\s*([\d/]+)",
    "reference": r"R[eé]f\s*:\s*([\w/]+)",
    "machine": r"Machine\s*:\s*(.+?)(?:\n|$)",
    "laize": r"Laize\s+(\d+)",
    "format": r"Format\s*:\s*([\d x]+mm)",
    "matiere": r"Mati[eè]re\s+(.+?)(?:\n|$)",
    "ref_adhesif": r"R[eé]f,?\s*Adh[eé]sif\s+(\d+)",
    "qte_adhesif_g": r"Qt[eé]\s*:\s*([\d,\.]+)\s*g",
    "qte_adhesif_kg": r"Qt[eé] totale\s+([\d,\.]+)\s*kg",
    "qte_au_mille": r"Quantit[eé] au mille\s+([\d,\.]+)",
    "nb_levees": r"Nb de lev[eé]es\s+(\d+)",
    "qte_etiquettes": r"Quantit[eé] [eé]tiq\.\s+([\d\s]+)",
    "qte_bobines": r"Quantit[eé] bobines\s+([\d,\.]+)",
    "metrage": r"M[eé]trage\s+([\d\s]+)",
    "conditionnement": r"Conditionnement\s+(.+?)(?:\n|$)",
    "tolerance": r"Tolerance\s+(.+?)(?:\n|$)",
    "cartons_type": r"Cartons\s+(Carton.+?)(?:\n|$)",
    "mandrins_dia": r"Mandrins dia\.\s+(.+?)(?:Long\.|$)",
    "mandrin_longueur": r"Long\.\s+([\d,\.]+)",
    "nb_cartons": r"Cartons\s+(\d+)(?!\s*x)",
    "nb_mandrins": r"Mandrins\s+(\d+)",
    "nb_tubes": r"Tubes\s+(\d+)",
    "bobinettes_completes": r"Bobinettes compl[eè]tes\s+(\w+)",
}


def _now_paris_iso() -> str:
    return datetime.now(_PARIS).replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%S")


def _require_of_access(request: Request) -> dict:
    user = get_current_user(request)
    if user.get("role") not in OF_ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Accès réservé à l'administration")
    return user


def _clean_num(raw: Optional[str]) -> Optional[float]:
    if raw is None:
        return None
    s = str(raw).strip().replace(" ", "").replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _clean_int(raw: Optional[str]) -> Optional[int]:
    f = _clean_num(raw)
    if f is None:
        return None
    return int(round(f))


def _normalize_field(key: str, value: Optional[str]) -> Any:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if key in OF_REAL_FIELDS:
        return _clean_num(text)
    if key in OF_INT_FIELDS:
        return _clean_int(text)
    return text


def _extract_pdf_text(content: bytes) -> str:
    parts: list[str] = []
    with pdfplumber.open(BytesIO(content)) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    return "\n".join(parts)


def parse_of_pdf(content: bytes) -> dict[str, Any]:
    text = _extract_pdf_text(content)
    if not text.strip():
        raise HTTPException(status_code=400, detail="PDF illisible ou vide.")

    result: dict[str, Any] = {k: None for k in OF_DATA_FIELDS}
    for key, pattern in _PATTERNS.items():
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if m:
            result[key] = _normalize_field(key, m.group(1))
    return result


def _coerce_payload(data: dict) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in OF_DATA_FIELDS:
        raw = data.get(key)
        if raw is None or raw == "":
            out[key] = None
            continue
        if key in OF_REAL_FIELDS:
            out[key] = _clean_num(str(raw))
        elif key in OF_INT_FIELDS:
            out[key] = _clean_int(str(raw))
        else:
            out[key] = str(raw).strip()
    return out


def _row_dict(row) -> dict:
    return dict(row) if row else {}


@router.post("/api/of/parse")
async def parse_of(request: Request, file: UploadFile = File(...)):
    _require_of_access(request)
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Fichier PDF requis.")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Fichier vide.")
    return parse_of_pdf(content)


@router.post("/api/of/validate")
async def validate_of(
    request: Request,
    file: UploadFile = File(...),
    data: str = Form(...),
):
    user = _require_of_access(request)
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Fichier PDF requis.")
    try:
        payload = json.loads(data)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Données JSON invalides.") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Données JSON invalides.")

    fields = _coerce_payload(payload)
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Fichier vide.")

    os.makedirs(OF_UPLOAD_DIR, exist_ok=True)
    of_num = (fields.get("of_numero") or "inconnu").strip()
    safe_of = re.sub(r"[^\w\-]+", "_", str(of_num))
    ts = datetime.now(_PARIS).replace(tzinfo=None).strftime("%Y%m%d_%H%M%S")
    pdf_filename = f"{safe_of}_{ts}.pdf"
    dest_path = os.path.join(OF_UPLOAD_DIR, pdf_filename)
    with open(dest_path, "wb") as f:
        f.write(content)

    now = _now_paris_iso()
    imported_by = user.get("nom") or user.get("email") or str(user.get("id", ""))
    cols = list(OF_DATA_FIELDS) + ["pdf_filename", "date_import", "imported_by", "statut"]
    placeholders = ", ".join("?" * len(cols))
    values = [fields.get(c) for c in OF_DATA_FIELDS]
    values.extend([pdf_filename, now, imported_by, "valide"])

    with get_db() as conn:
        cur = conn.execute(
            f"INSERT INTO of_imports ({', '.join(cols)}) VALUES ({placeholders})",
            values,
        )
        conn.commit()
        new_id = cur.lastrowid

    # Auto-link : relier les dossiers planning dont le numero_of correspond
    of_num_clean = (fields.get("of_numero") or "").strip()
    if of_num_clean:
        with get_db() as conn2:
            conn2.execute(
                """UPDATE planning_entries
                   SET of_import_id = ?
                   WHERE LOWER(TRIM(numero_of)) = LOWER(TRIM(?))
                     AND (of_import_id IS NULL OR of_import_id != ?)""",
                (new_id, of_num_clean, new_id),
            )
            conn2.commit()

    return {"id": new_id, "pdf_filename": pdf_filename}


@router.get("/api/of/list")
def list_of_imports(request: Request):
    _require_of_access(request)
    q      = (request.query_params.get("q")      or "").strip()
    offset = int(request.query_params.get("offset") or 0)
    limit  = int(request.query_params.get("limit")  or 50)
    limit  = min(limit, 200)   # plafond de sécurité

    like = f"%{q}%"
    search_filter = ""
    params_count: list = []
    params_rows:  list = []

    if q:
        search_filter = """AND (
            LOWER(COALESCE(o.of_numero,''))    LIKE LOWER(?)
         OR LOWER(COALESCE(o.reference,''))   LIKE LOWER(?)
         OR LOWER(COALESCE(o.machine,''))     LIKE LOWER(?)
         OR LOWER(COALESCE(o.delai_client,'')) LIKE LOWER(?)
        )"""
        params_count = [like, like, like, like]
        params_rows  = [like, like, like, like, limit, offset]
    else:
        params_rows = [limit, offset]

    with get_db() as conn:
        total = conn.execute(
            f"""SELECT COUNT(DISTINCT o.id)
                FROM of_imports o
                LEFT JOIN planning_entries pe ON pe.of_import_id = o.id
                WHERE 1=1 {search_filter}""",
            params_count,
        ).fetchone()[0]

        rows = conn.execute(
            f"""SELECT
                    o.id, o.of_numero, o.reference, o.machine, o.delai_client,
                    o.format, o.date_creation, o.qte_etiquettes, o.qte_bobines,
                    o.metrage, o.matiere, o.conditionnement, o.outil_1_numero,
                    o.nb_mandrins, o.nb_cartons, o.nb_tubes,
                    o.date_import, o.statut, o.pdf_filename, o.imported_by,
                    CASE WHEN pe.of_import_id IS NOT NULL THEN 1 ELSE 0 END AS lie
                FROM of_imports o
                LEFT JOIN planning_entries pe ON pe.of_import_id = o.id
                WHERE 1=1 {search_filter}
                GROUP BY o.id
                ORDER BY COALESCE(o.date_creation, o.date_import) DESC
                LIMIT ? OFFSET ?""",
            params_rows,
        ).fetchall()

    return {
        "total":  total,
        "offset": offset,
        "limit":  limit,
        "rows":   [{**_row_dict(r), "lie": bool(r["lie"])} for r in rows],
    }


@router.patch("/api/of/{of_id}")
async def update_of_import(of_id: int, request: Request):
    """Modifier les champs éditables d'un OF importé."""
    _require_of_access(request)
    body = await request.json()

    EDITABLE = {
        "of_numero", "reference", "machine", "delai_client",
        "format", "date_creation", "qte_etiquettes", "qte_bobines", "metrage",
        "matiere", "conditionnement", "outil_1_numero",
        "nb_mandrins", "nb_cartons", "nb_tubes",
    }
    updates = {k: v for k, v in body.items() if k in EDITABLE}
    if not updates:
        raise HTTPException(status_code=400, detail="Aucun champ modifiable fourni.")

    with get_db() as conn:
        row = conn.execute("SELECT id FROM of_imports WHERE id=?", (of_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="OF introuvable.")
        set_clause = ", ".join(f"{k}=?" for k in updates)
        conn.execute(
            f"UPDATE of_imports SET {set_clause} WHERE id=?",
            list(updates.values()) + [of_id],
        )
        conn.commit()
    return {"updated": True, "id": of_id}


@router.get("/api/of/planning/{entry_id}")
def get_of_for_planning_entry(entry_id: int, request: Request):
    get_current_user(request)  # authentification simple, pas de rôle requis
    with get_db() as conn:
        entry = conn.execute(
            "SELECT of_import_id, numero_of FROM planning_entries WHERE id=?",
            (entry_id,),
        ).fetchone()
    if not entry or not entry["of_import_id"]:
        return {"linked": False, "entry_numero_of": entry["numero_of"] if entry else None}
    with get_db() as conn:
        row = conn.execute(
            """SELECT id, of_numero, reference, machine, pdf_filename,
                      date_import, imported_by, delai_client, qte_etiquettes, metrage
               FROM of_imports WHERE id=?""",
            (entry["of_import_id"],),
        ).fetchone()
    if not row:
        return {"linked": False, "entry_numero_of": entry["numero_of"]}
    return {"linked": True, "of": _row_dict(row), "entry_numero_of": entry["numero_of"]}


@router.get("/api/of/{of_id}/pdf-preview")
def preview_of_pdf(of_id: int, request: Request):
    get_current_user(request)
    with get_db() as conn:
        row = conn.execute(
            """SELECT id, of_numero, reference, date_creation, delai_client,
                      machine, format, matiere, laize, qte_etiquettes, qte_bobines,
                      metrage, conditionnement, nb_cartons, nb_mandrins, nb_tubes,
                      mandrins_dia, outil_1_numero, pdf_filename
               FROM of_imports WHERE id=?""",
            (of_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="OF introuvable.")

    # OF importé via PDF → servir le fichier original
    if row["pdf_filename"]:
        path = os.path.join(OF_UPLOAD_DIR, row["pdf_filename"])
        if not os.path.isfile(path):
            raise HTTPException(status_code=404, detail="Fichier PDF introuvable.")
        return FileResponse(
            path,
            media_type="application/pdf",
            filename=row["pdf_filename"],
            headers={"Content-Disposition": f'inline; filename="{row["pdf_filename"]}"'},
        )

    # OF importé via API (pas de PDF) → générer depuis le template vierge
    try:
        from app.services.of_pdf_generator import generate_of_pdf
        pdf_bytes = generate_of_pdf(dict(row))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur génération PDF : {exc}") from exc

    safe_num = re.sub(r"[^\w\-]+", "_", str(row["of_numero"] or of_id))
    filename = f"OF_{safe_num}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get("/api/of/{of_id}/pdf")
def download_of_pdf(request: Request, of_id: int):
    _require_of_access(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT pdf_filename FROM of_imports WHERE id=?",
            (of_id,),
        ).fetchone()
    if not row or not row["pdf_filename"]:
        raise HTTPException(status_code=404, detail="OF introuvable.")
    path = os.path.join(OF_UPLOAD_DIR, row["pdf_filename"])
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Fichier PDF introuvable.")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=row["pdf_filename"],
        headers={"Content-Disposition": f'attachment; filename="{row["pdf_filename"]}"'},
    )


@router.delete("/api/of/bulk")
async def bulk_delete_of(request: Request):
    """Suppression en masse d'OFs. Body JSON : {"ids": [1, 2, 3]}"""
    require_superadmin(request)
    body = await request.json()
    ids  = [int(i) for i in (body.get("ids") or []) if str(i).isdigit()]
    if not ids:
        raise HTTPException(status_code=400, detail="Liste d'ids vide.")
    placeholders = ",".join("?" * len(ids))
    with get_db() as conn:
        conn.execute(f"DELETE FROM of_imports WHERE id IN ({placeholders})", ids)
        conn.commit()
    return {"deleted": len(ids), "ids": ids}


@router.delete("/api/of/{of_id}")
def delete_of_import(request: Request, of_id: int):
    require_superadmin(request)
    with get_db() as conn:
        row = conn.execute("SELECT id FROM of_imports WHERE id=?", (of_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="OF introuvable.")
        conn.execute("DELETE FROM of_imports WHERE id=?", (of_id,))
        conn.commit()
    return {"ok": True}


# ══════════════════════════════════════════════════
# Fiches techniques
# ══════════════════════════════════════════════════

@router.get("/api/fiches-techniques/list")
def list_fiches(request: Request):
    _require_of_access(request)
    q      = (request.query_params.get("q")      or "").strip()
    offset = int(request.query_params.get("offset") or 0)
    limit  = min(int(request.query_params.get("limit") or 50), 200)

    like = f"%{q}%"
    where = "WHERE 1=1"
    params_c: list = []
    params_r: list = []
    if q:
        where += " AND (LOWER(COALESCE(reference,'')) LIKE LOWER(?) OR LOWER(COALESCE(format,'')) LIKE LOWER(?) OR LOWER(COALESCE(support,'')) LIKE LOWER(?) OR LOWER(COALESCE(machine,'')) LIKE LOWER(?))"
        params_c = [like, like, like, like]
        params_r = [like, like, like, like, limit, offset]
    else:
        params_r = [limit, offset]

    with get_db() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM fiches_techniques {where}", params_c).fetchone()[0]
        rows  = conn.execute(
            f"SELECT * FROM fiches_techniques {where} ORDER BY date_import DESC LIMIT ? OFFSET ?",
            params_r,
        ).fetchall()
    return {"total": total, "offset": offset, "limit": limit, "rows": [_row_dict(r) for r in rows]}


@router.patch("/api/fiches-techniques/{fiche_id}")
async def update_fiche(fiche_id: int, request: Request):
    _require_of_access(request)
    body = await request.json()
    EDITABLE = {
        "reference","designation","client","format",
        "eti_laize","eti_longueur","eti_rayons","eti_perforations",
        "mod_laize","mod_longueur","mod_nb_front",
        "support","matiere","glassine","laize_optimale","laize_optionnelle",
        "epaisseur","adhesif","qte_au_mille",
        "machine","nb_couleurs","recto","verso",
        "tete1_pantone","tete1_couleur","tete1_anilox","tete1_composition",
        "tete2_pantone","tete2_couleur","tete2_anilox","tete2_composition",
        "tete3_pantone","tete3_couleur","tete3_anilox","tete3_composition",
        "remarque","mandrin_dia","mandrin_longueur","enroulement","nb_etiq_bobin",
        "dia_ext","poids","conditionnement","cales_sachets","cartons",
        "nb_au_sol","nb_etage","nb_bobines_carton",
        "palette_type","palette_nb_cartons_sol","palette_nb_cartons_hauteur","palette_hauteur_max",
        "particularite","notes",
    }
    updates = {k: v for k, v in body.items() if k in EDITABLE}
    if not updates:
        raise HTTPException(status_code=400, detail="Aucun champ modifiable.")
    with get_db() as conn:
        if not conn.execute("SELECT id FROM fiches_techniques WHERE id=?", (fiche_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Fiche introuvable.")
        conn.execute(
            f"UPDATE fiches_techniques SET {', '.join(f'{k}=?' for k in updates)} WHERE id=?",
            list(updates.values()) + [fiche_id],
        )
        conn.commit()
    return {"updated": True, "id": fiche_id}


@router.get("/api/fiches-techniques/{fiche_id}/pdf-preview")
def preview_fiche_pdf(fiche_id: int, request: Request):
    """Génère et retourne le PDF d'une fiche technique (auth session)."""
    get_current_user(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM fiches_techniques WHERE id=?", (fiche_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Fiche introuvable.")
    try:
        from app.services.fiche_pdf import generate_fiche_pdf
        pdf_bytes = generate_fiche_pdf(dict(row))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur génération PDF : {exc}") from exc
    ref = re.sub(r"[^\w\-]+", "_", str(row["reference"] or fiche_id))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="fiche_{ref}.pdf"'},
    )


@router.delete("/api/fiches-techniques/bulk")
async def bulk_delete_fiches(request: Request):
    """Suppression en masse de fiches techniques. Body JSON : {"ids": [1, 2, 3]}"""
    require_superadmin(request)
    body = await request.json()
    ids  = [int(i) for i in (body.get("ids") or []) if str(i).isdigit()]
    if not ids:
        raise HTTPException(status_code=400, detail="Liste d'ids vide.")
    placeholders = ",".join("?" * len(ids))
    with get_db() as conn:
        conn.execute(f"DELETE FROM fiches_techniques WHERE id IN ({placeholders})", ids)
        conn.commit()
    return {"deleted": len(ids), "ids": ids}


@router.delete("/api/fiches-techniques/{fiche_id}")
def delete_fiche(fiche_id: int, request: Request):
    require_superadmin(request)
    with get_db() as conn:
        conn.execute("DELETE FROM fiches_techniques WHERE id=?", (fiche_id,))
        conn.commit()
    return {"deleted": True, "id": fiche_id}

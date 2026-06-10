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
            """SELECT pe.of_import_id, pe.numero_of, pe.ref_produit,
                      pe.machine_id, m.nom AS machine_nom
               FROM planning_entries pe
               LEFT JOIN machines m ON m.id = pe.machine_id
               WHERE pe.id = ?""",
            (entry_id,),
        ).fetchone()
    if not entry:
        return {"linked": False, "entry_numero_of": None, "ref_produit": None, "fiche_id": None}

    of_import_id = entry["of_import_id"]
    numero_of    = entry["numero_of"]
    ref_produit  = entry["ref_produit"]
    machine_nom  = entry["machine_nom"]

    # Pré-calculer ref_produit_norm pour aider à désambiguïser la lookup OF
    # (cf. _lookup_of_by_numero en bas de ce module — phase 2 du cascade).
    try:
        from app.services.fiche_ref_parser import normalize_ref_produit as _norm_rp
        _ref_produit_norm_for_of_lookup = _norm_rp(ref_produit) if ref_produit else None
    except Exception:
        _ref_produit_norm_for_of_lookup = None

    row = None

    # 1. Lien direct par of_import_id
    if of_import_id:
        with get_db() as c:
            row = c.execute(
                """SELECT id, of_numero, reference, machine, pdf_filename,
                          date_import, imported_by, delai_client, qte_etiquettes, metrage
                   FROM of_imports WHERE id=?""",
                (of_import_id,),
            ).fetchone()

    # 2. Fallback : of_import_id absent ou lien mort → chercher par numero_of
    # Skippe si l'utilisateur a déjà géré manuellement (flag of_link_user_managed=1)
    if not row and numero_of:
        _skip_auto = False
        try:
            with get_db() as _c_check:
                _pe_cols = {r["name"] for r in _c_check.execute("PRAGMA table_info(planning_entries)").fetchall()}
                if "of_link_user_managed" in _pe_cols:
                    _flag = _c_check.execute(
                        "SELECT COALESCE(of_link_user_managed,0) FROM planning_entries WHERE id=?",
                        (entry_id,),
                    ).fetchone()
                    _skip_auto = bool(_flag and int(_flag[0] or 0) == 1)
        except Exception:
            _skip_auto = False

        if not _skip_auto:
            row = _lookup_of_by_numero(numero_of, _ref_produit_norm_for_of_lookup)
            if row:
                # Persister le lien via planning_of_links (trigger sync of_import_id)
                try:
                    with get_db() as c2:
                        c2.execute(
                            "INSERT OR IGNORE INTO planning_of_links "
                            "(planning_entry_id, of_import_id, position, created_by, created_at) "
                            "VALUES (?, ?, 0, 'auto_lookup', ?)",
                            (entry_id, row["id"], _now_paris_iso()),
                        )
                        c2.commit()
                except Exception:
                    pass

    # Chercher la fiche technique par ref_produit.
    # On matche en priorité sur la clé produit normalisée (ref_produit_norm,
    # XXX/NNNN) — insensible à la variante machine/laize présente dans le
    # libellé de la fiche, et tolère "1315-0004" côté dossier vs "1315/0004
    # - COHESIO 1" côté fiche. Si plusieurs fiches partagent la même clé
    # produit (cas fréquent : une variante par machine), on privilégie celle
    # dont la machine correspond à la machine du planning. Fallback sur la
    # référence textuelle complète pour les fiches non encore re-parsées.
    fiche_id = None
    if ref_produit:
        try:
            from app.services.fiche_ref_parser import normalize_ref_produit
            norm = normalize_ref_produit(ref_produit)
        except Exception:
            norm = None
        with get_db() as conn3:
            if norm:
                # ORDER BY : la fiche dont la machine matche la machine du
                # dossier au planning passe en premier ; en cas d'absence
                # de machine sur la fiche, on garde quand même un candidat ;
                # en dernier recours, fiche dont la machine ne matche pas.
                fiche = conn3.execute(
                    """SELECT id FROM fiches_techniques
                       WHERE ref_produit_norm = ?
                       ORDER BY
                         CASE
                           WHEN LOWER(TRIM(COALESCE(machine,''))) = LOWER(TRIM(COALESCE(?,''))) AND TRIM(COALESCE(machine,'')) != '' THEN 0
                           WHEN TRIM(COALESCE(machine,'')) = '' THEN 1
                           ELSE 2
                         END,
                         id
                       LIMIT 1""",
                    (norm, machine_nom or ""),
                ).fetchone()
                if fiche:
                    fiche_id = fiche["id"]
            if fiche_id is None:
                fiche = conn3.execute(
                    "SELECT id FROM fiches_techniques WHERE LOWER(TRIM(reference))=LOWER(TRIM(?)) LIMIT 1",
                    (ref_produit,),
                ).fetchone()
                if fiche:
                    fiche_id = fiche["id"]

    # Récupère la liste complète des OF liés (multi via planning_of_links).
    # `of` (singular) reste = premier lien (rétrocompat panneau planning).
    ofs_list: list = []
    try:
        with get_db() as c3:
            ofs_rows = c3.execute(
                """SELECT o.id, o.of_numero, o.reference, o.machine, o.pdf_filename,
                          o.date_import, o.imported_by, o.delai_client, o.qte_etiquettes, o.metrage
                    FROM planning_of_links pl
                    JOIN of_imports o ON o.id = pl.of_import_id
                    WHERE pl.planning_entry_id = ?
                    ORDER BY pl.position ASC, pl.id ASC""",
                (entry_id,),
            ).fetchall()
            ofs_list = [_row_dict(r) for r in ofs_rows]
    except Exception:
        ofs_list = []

    base = {"entry_numero_of": numero_of, "ref_produit": ref_produit,
            "fiche_id": fiche_id, "ofs": ofs_list}

    if not row:
        return {"linked": False, **base}
    return {"linked": True, "of": _row_dict(row), **base}


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


# ─────────────────────────────────────────────────────────────────────────────
# Backfill ref_produit_norm (admin)
#
# Re-parse toutes les fiches_techniques et planning_entries pour remplir
# ref_produit_norm, machine, laize_mm, conditionnement_norm. Idempotent :
# ne touche que les colonnes vides ou désynchronisées. Ne modifie jamais
# une machine/conditionnement déjà saisi à la main.
#
# Usage :
#   POST /api/admin/backfill-ref-produit-norm            → applique
#   POST /api/admin/backfill-ref-produit-norm?dry_run=1  → simulation (lecture seule)
#
# Réservé au superadmin (le backfill modifie potentiellement plusieurs centaines
# de lignes en une fois — pas une action quotidienne).
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/api/admin/backfill-ref-produit-norm")
def admin_backfill_ref_produit_norm(request: Request):
    require_superadmin(request)

    dry_run = (request.query_params.get("dry_run") or "").lower() in ("1", "true", "yes", "on")

    try:
        from app.services.fiche_ref_parser import (
            parse_fiche_reference,
            normalize_ref_produit,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Parser indisponible : {exc}")

    fiches_total = 0
    fiches_updated = 0
    fiches_unchanged = 0
    fiches_no_match = 0
    fiches_preview: list = []

    pe_total = 0
    pe_updated = 0
    pe_unchanged = 0
    pe_no_match = 0
    pe_preview: list = []

    with get_db() as conn:
        ft_cols = {r["name"] for r in conn.execute("PRAGMA table_info(fiches_techniques)").fetchall()}
        if "ref_produit_norm" not in ft_cols:
            raise HTTPException(
                status_code=500,
                detail="Migration 101 non appliquée (colonne ref_produit_norm absente). Redémarre le service pour déclencher la migration.",
            )

        rows = conn.execute(
            "SELECT id, reference, ref_produit_norm, machine, laize_mm, "
            "       conditionnement, conditionnement_norm "
            "FROM fiches_techniques"
        ).fetchall()
        fiches_total = len(rows)

        for row in rows:
            parsed = parse_fiche_reference(row["reference"])
            updates: dict = {}

            new_norm = parsed.get("ref_produit_norm")
            cur_norm = (row["ref_produit_norm"] or "").strip()
            if new_norm and new_norm != cur_norm:
                updates["ref_produit_norm"] = new_norm

            # Ne pas écraser une machine saisie à la main.
            new_machine = parsed.get("machine")
            cur_machine = (row["machine"] or "").strip()
            if new_machine and not cur_machine:
                updates["machine"] = new_machine

            new_laize = parsed.get("laize_mm")
            if new_laize and not row["laize_mm"]:
                updates["laize_mm"] = new_laize

            new_cond = parsed.get("conditionnement_norm")
            cur_cond_norm = (row["conditionnement_norm"] or "").strip()
            cur_cond_raw = (row["conditionnement"] or "").strip()
            if new_cond and not cur_cond_norm and not cur_cond_raw:
                updates["conditionnement_norm"] = new_cond

            if not updates:
                if new_norm:
                    fiches_unchanged += 1
                else:
                    fiches_no_match += 1
                continue

            fiches_updated += 1
            if len(fiches_preview) < 25:
                fiches_preview.append({
                    "id": row["id"],
                    "reference": row["reference"],
                    "updates": updates,
                })
            if not dry_run:
                set_clause = ", ".join(f"{k}=?" for k in updates)
                conn.execute(
                    f"UPDATE fiches_techniques SET {set_clause} WHERE id=?",
                    list(updates.values()) + [row["id"]],
                )

        pe_rows = conn.execute(
            "SELECT id, ref_produit, ref_produit_norm "
            "FROM planning_entries "
            "WHERE ref_produit IS NOT NULL AND TRIM(ref_produit) != ''"
        ).fetchall()
        pe_total = len(pe_rows)

        for row in pe_rows:
            norm = normalize_ref_produit(row["ref_produit"])
            if not norm:
                pe_no_match += 1
                continue
            cur = (row["ref_produit_norm"] or "").strip()
            if norm == cur:
                pe_unchanged += 1
                continue
            pe_updated += 1
            if len(pe_preview) < 25:
                pe_preview.append({
                    "id": row["id"],
                    "ref_produit": row["ref_produit"],
                    "ref_produit_norm": norm,
                })
            if not dry_run:
                conn.execute(
                    "UPDATE planning_entries SET ref_produit_norm=? WHERE id=?",
                    (norm, row["id"]),
                )

        if not dry_run:
            conn.commit()

    return {
        "dry_run": dry_run,
        "fiches_techniques": {
            "total": fiches_total,
            "updated": fiches_updated,
            "unchanged": fiches_unchanged,
            "no_match": fiches_no_match,
            "preview": fiches_preview,
        },
        "planning_entries": {
            "total": pe_total,
            "updated": pe_updated,
            "unchanged": pe_unchanged,
            "no_match": pe_no_match,
            "preview": pe_preview,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Lookup OF par numero, en cascade.
#
# Ordre des passes :
#   1. Match exact (LOWER/TRIM, + normalisation numérique 9931861.0 → 9931861)
#   2. Match exact après retrait du préfixe "OF "
#   3. Extraction du numéro racine 99XXXXX dans le numero, puis recherche
#      d'OF dont l'of_numero contient ce numéro. Désambiguïsation par
#      ref_produit_norm si fourni (l'OF dont la référence matche le produit
#      du planning passe en premier), puis par date_import desc.
#
# Lecture seule (SELECT). Retourne None si rien ne matche.
# ─────────────────────────────────────────────────────────────────────────────

_OF_RACINE_RE = re.compile(r"\b(99\d{5})\b")
_OF_PREFIX_RE = re.compile(r"^\s*OF\s+(.+?)\s*$", re.IGNORECASE)

_OF_SELECT_COLS = (
    "id, of_numero, reference, machine, pdf_filename, "
    "date_import, imported_by, delai_client, qte_etiquettes, metrage"
)


def _lookup_of_candidates(num: Optional[str], ref_produit_norm: Optional[str] = None):
    """Lookup OF en cascade — distingue match certain vs ambigu.

    Retourne un tuple (certain_row_or_None, candidates_list).

    - Phase 1 (match exact, avec ou sans préfixe "OF ") → (row, [])
    - Phase 2 (extraction racine 99XXXXX), 1 seul candidat → (row, [])
    - Phase 2 avec 2+ candidats et désambiguïsation par ref_produit_norm
      identifie UN unique gagnant → (row, [])
    - Phase 2 avec 2+ candidats sans désambiguïsation possible
      → (None, candidates_list)  [le caller doit demander un choix humain]
    - Aucun match → (None, [])

    Lecture seule.
    """
    if not num:
        return (None, [])
    s = str(num).strip()
    if not s:
        return (None, [])

    candidates_exact: list = [s]
    try:
        candidates_exact.append(str(int(float(s))))
    except (ValueError, OverflowError):
        pass

    m_prefix = _OF_PREFIX_RE.match(s)
    if m_prefix:
        inner = m_prefix.group(1).strip()
        candidates_exact.append(inner)
        try:
            candidates_exact.append(str(int(float(inner))))
        except (ValueError, OverflowError):
            pass

    try:
        from app.services.fiche_ref_parser import normalize_ref_produit
    except Exception:
        normalize_ref_produit = None

    with get_db() as c:
        # Phase 1 : exact match en cascade
        for cand in dict.fromkeys(candidates_exact):
            r = c.execute(
                f"""SELECT {_OF_SELECT_COLS}
                    FROM of_imports
                    WHERE LOWER(TRIM(of_numero)) = LOWER(TRIM(?))
                    LIMIT 1""",
                (cand,),
            ).fetchone()
            if r:
                return (r, [])

        # Phase 2 : extraction du numéro racine 99XXXXX
        m = _OF_RACINE_RE.search(s)
        if not m:
            return (None, [])
        racine = m.group(1)

        rows = c.execute(
            f"""SELECT {_OF_SELECT_COLS}
                FROM of_imports
                WHERE of_numero LIKE ?
                ORDER BY
                  CASE WHEN TRIM(of_numero) = ? THEN 0
                       WHEN of_numero LIKE ? THEN 1
                       ELSE 2
                  END,
                  date_import DESC,
                  id DESC""",
            ("%" + racine + "%", racine, racine + "%"),
        ).fetchall()

        if not rows:
            return (None, [])

        if len(rows) == 1:
            return (rows[0], [])

        # Plusieurs candidats : essayer la désambiguïsation par ref_produit_norm
        if ref_produit_norm and normalize_ref_produit is not None:
            matched_by_ref = []
            for r in rows:
                if not r["reference"]:
                    continue
                r_norm = normalize_ref_produit(r["reference"])
                if r_norm and r_norm == ref_produit_norm:
                    matched_by_ref.append(r)
            if len(matched_by_ref) == 1:
                return (matched_by_ref[0], [])

        # Pas de désambiguïsation possible → ambigu (human-in-the-loop)
        return (None, [dict(r) for r in rows])


def _lookup_of_by_numero(num: Optional[str], ref_produit_norm: Optional[str] = None):
    """Variante "match certain uniquement" pour les appels qui ne gèrent pas
    l'ambiguïté (ex. lookup à la volée depuis /api/of/planning/{id}).

    Retourne la row si match certain, None sinon. Voir _lookup_of_candidates
    pour le détail de la cascade.
    """
    certain, _ = _lookup_of_candidates(num, ref_produit_norm)
    return certain


# ─────────────────────────────────────────────────────────────────────────────
# Relink OF en batch (admin)
#
# Parcourt les planning_entries qui ont un numero_of mais pas de of_import_id
# (ou un lien mort), tente une lookup via _lookup_of_by_numero, et persiste
# le lien si trouvé. Idempotent.
#
# Usage :
#   POST /api/admin/relink-of            → applique
#   POST /api/admin/relink-of?dry_run=1  → simulation (lecture seule)
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/api/admin/relink-of")
def admin_relink_of(request: Request):
    require_superadmin(request)

    dry_run = (request.query_params.get("dry_run") or "").lower() in ("1", "true", "yes", "on")

    try:
        from app.services.fiche_ref_parser import normalize_ref_produit
    except Exception:
        normalize_ref_produit = None

    total = 0
    relinked = 0
    already_linked = 0
    unmatched = 0
    pending_for_review = 0
    preview: list = []
    pending_preview: list = []

    with get_db() as conn:
        pe_cols = {r["name"] for r in conn.execute("PRAGMA table_info(planning_entries)").fetchall()}
        has_norm = "ref_produit_norm" in pe_cols

        sql = (
            "SELECT id, numero_of, ref_produit, "
            + ("ref_produit_norm, " if has_norm else "")
            + "of_import_id "
            "FROM planning_entries "
            "WHERE numero_of IS NOT NULL AND TRIM(numero_of) != ''"
        )
        rows = conn.execute(sql).fetchall()
        total = len(rows)

        for row in rows:
            # Si lien déjà en place et OF existe, on saute
            if row["of_import_id"]:
                check = conn.execute(
                    "SELECT 1 FROM of_imports WHERE id=?",
                    (row["of_import_id"],),
                ).fetchone()
                if check:
                    already_linked += 1
                    continue
                # lien mort, on retente

            ref_norm = None
            if has_norm:
                ref_norm = (row["ref_produit_norm"] or "").strip() or None
            if not ref_norm and normalize_ref_produit is not None:
                ref_norm = normalize_ref_produit(row["ref_produit"])

            certain, candidates = _lookup_of_candidates(row["numero_of"], ref_norm)

            if certain:
                relinked += 1
                if len(preview) < 30:
                    preview.append({
                        "planning_id": row["id"],
                        "planning_numero_of": row["numero_of"],
                        "planning_ref_produit": row["ref_produit"],
                        "of_id": certain["id"],
                        "of_numero": certain["of_numero"],
                        "of_reference": certain["reference"],
                    })
                if not dry_run:
                    conn.execute(
                        "INSERT OR IGNORE INTO planning_of_links "
                        "(planning_entry_id, of_import_id, position, created_by, created_at) "
                        "VALUES (?, ?, 0, 'admin_relink', ?)",
                        (row["id"], certain["id"], _now_paris_iso()),
                    )
                continue

            if candidates:
                # Ambigu : on n'auto-link pas, le service admin choisira via l'UI
                pending_for_review += 1
                if len(pending_preview) < 15:
                    pending_preview.append({
                        "planning_id": row["id"],
                        "planning_numero_of": row["numero_of"],
                        "planning_ref_produit": row["ref_produit"],
                        "candidates_count": len(candidates),
                        "candidates_sample": [
                            {"of_id": c["id"], "of_numero": c["of_numero"]}
                            for c in candidates[:3]
                        ],
                    })
                continue

            unmatched += 1

        if not dry_run:
            conn.commit()

    return {
        "dry_run": dry_run,
        "total_with_numero_of": total,
        "already_linked": already_linked,
        "relinked": relinked,
        "pending_for_review": pending_for_review,
        "pending_preview": pending_preview,
        "unmatched": unmatched,
        "preview": preview,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Mappings OF "à valider" — human-in-the-loop
#
# Quand la lookup automatique trouve PLUSIEURS OF candidats pour un même
# planning_entry (extraction racine 99XXXXX avec multiples matchs et sans
# désambiguïsation possible), on ne lie pas automatiquement : le service
# administration choisit le bon OF via une UI dédiée dans la page Fiches+OF.
#
# Endpoints :
#   GET  /api/admin/of-link-pending/count  → juste le nombre (pour le badge)
#   GET  /api/admin/of-link-pending        → liste détaillée avec candidats
#   POST /api/admin/link-planning-of       → enregistre un choix manuel
# ─────────────────────────────────────────────────────────────────────────────


def _iter_pending_planning_rows(conn):
    """Itère sur les planning_entries sans of_import_id mais avec un numero_of.
    Yield un tuple (row, ref_produit_norm, candidates) UNIQUEMENT pour les cas
    ambigus (2+ candidats sans désambiguïsation possible).
    """
    pe_cols = {r["name"] for r in conn.execute("PRAGMA table_info(planning_entries)").fetchall()}
    has_norm = "ref_produit_norm" in pe_cols

    try:
        from app.services.fiche_ref_parser import normalize_ref_produit
    except Exception:
        normalize_ref_produit = None

    sql = (
        "SELECT pe.id, pe.numero_of, pe.ref_produit, "
        + ("pe.ref_produit_norm, " if has_norm else "")
        + "pe.machine_id, m.nom AS machine_nom "
        "FROM planning_entries pe "
        "LEFT JOIN machines m ON m.id = pe.machine_id "
        "WHERE pe.numero_of IS NOT NULL AND TRIM(pe.numero_of) != '' "
        "AND pe.of_import_id IS NULL"
    )
    for row in conn.execute(sql).fetchall():
        ref_norm = None
        if has_norm:
            ref_norm = (row["ref_produit_norm"] or "").strip() or None
        if not ref_norm and normalize_ref_produit is not None:
            ref_norm = normalize_ref_produit(row["ref_produit"])

        certain, candidates = _lookup_of_candidates(row["numero_of"], ref_norm)
        if certain:
            continue
        if not candidates or len(candidates) < 2:
            continue
        yield row, ref_norm, candidates


@router.get("/api/admin/of-link-pending/count")
def admin_of_link_pending_count(request: Request):
    """Badge unifié : ambigus (à arbitrer) + dossiers sans aucun OF (à associer)."""
    _require_of_access(request)
    ambigus = 0
    sans_of = 0
    with get_db() as conn:
        for _ in _iter_pending_planning_rows(conn):
            ambigus += 1
        sans_of = conn.execute(_DOSSIERS_SANS_OF_COUNT_SQL).fetchone()[0]
    return {"count": ambigus + sans_of, "ambigus": ambigus, "sans_of": sans_of}


@router.get("/api/admin/of-link-pending")
def admin_of_link_pending(request: Request):
    _require_of_access(request)
    items: list = []
    with get_db() as conn:
        for row, ref_norm, candidates in _iter_pending_planning_rows(conn):
            items.append({
                "planning_id": row["id"],
                "numero_of": row["numero_of"],
                "ref_produit": row["ref_produit"],
                "ref_produit_norm": ref_norm,
                "machine": row["machine_nom"],
                "candidates": candidates,
            })
    return {"total": len(items), "items": items}


@router.post("/api/admin/link-planning-of")
async def admin_link_planning_of(request: Request):
    _require_of_access(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Body JSON requis.")

    planning_id = body.get("planning_id")
    of_id = body.get("of_id")  # null = délier

    if not isinstance(planning_id, int):
        raise HTTPException(status_code=400, detail="planning_id (int) requis.")
    if of_id is not None and not isinstance(of_id, int):
        raise HTTPException(status_code=400, detail="of_id doit etre int ou null.")

    with get_db() as conn:
        pe = conn.execute(
            "SELECT id FROM planning_entries WHERE id=?", (planning_id,)
        ).fetchone()
        if not pe:
            raise HTTPException(status_code=404, detail="Planning introuvable.")

        if of_id is not None:
            oi = conn.execute(
                "SELECT id FROM of_imports WHERE id=?", (of_id,)
            ).fetchone()
            if not oi:
                raise HTTPException(status_code=404, detail="OF introuvable.")

        if of_id is None:
            # "délier" = retirer TOUS les liens pour ce planning
            conn.execute(
                "DELETE FROM planning_of_links WHERE planning_entry_id=?",
                (planning_id,),
            )
        else:
            user = get_current_user(request)
            who = (user.get("nom") or user.get("email") or str(user.get("id", ""))) if user else ""
            conn.execute(
                "INSERT OR IGNORE INTO planning_of_links "
                "(planning_entry_id, of_import_id, position, created_by, created_at) "
                "VALUES (?, ?, 0, ?, ?)",
                (planning_id, of_id, who, _now_paris_iso()),
            )
        # Action manuelle : désactive l'auto-link futur pour ce planning
        try:
            conn.execute("UPDATE planning_entries SET of_link_user_managed=1 WHERE id=?", (planning_id,))
        except Exception:
            pass
        conn.commit()

    return {"linked": True, "planning_id": planning_id, "of_id": of_id}


# ─────────────────────────────────────────────────────────────────────────────
# Dossiers sans aucun OF lié (planning_of_links vide)
# ─────────────────────────────────────────────────────────────────────────────

_DOSSIERS_SANS_OF_COUNT_SQL = (
    "SELECT COUNT(*) FROM planning_entries pe "
    "WHERE NOT EXISTS (SELECT 1 FROM planning_of_links pl "
    "                  WHERE pl.planning_entry_id = pe.id) "
    "AND COALESCE(pe.statut, '') != 'termine'"
)


@router.get("/api/admin/dossiers-sans-of/count")
def admin_dossiers_sans_of_count(request: Request):
    _require_of_access(request)
    with get_db() as conn:
        n = conn.execute(_DOSSIERS_SANS_OF_COUNT_SQL).fetchone()[0]
    return {"count": int(n)}


@router.get("/api/admin/dossiers-sans-of")
def admin_dossiers_sans_of(request: Request):
    _require_of_access(request)
    rows = []
    with get_db() as conn:
        rows = conn.execute(
            """SELECT pe.id, pe.numero_of, pe.ref_produit, pe.ref_produit_norm,
                       pe.machine_id, m.nom AS machine_nom,
                       pe.created_at AS planning_created_at,
                       pe.statut, pe.duree_heures, pe.format_l, pe.format_h
               FROM planning_entries pe
               LEFT JOIN machines m ON m.id = pe.machine_id
               WHERE NOT EXISTS (
                  SELECT 1 FROM planning_of_links pl
                  WHERE pl.planning_entry_id = pe.id
               )
               AND COALESCE(pe.statut, '') != 'termine'
               ORDER BY pe.created_at DESC, pe.id DESC"""
        ).fetchall()
    items = [{
        "planning_id": r["id"],
        "numero_of": r["numero_of"],
        "ref_produit": r["ref_produit"],
        "ref_produit_norm": r["ref_produit_norm"],
        "machine": r["machine_nom"],
        "statut": r["statut"],
        "duree_heures": r["duree_heures"],
        "created_at": r["planning_created_at"],
    } for r in rows]
    return {"total": len(items), "items": items}


# ─────────────────────────────────────────────────────────────────────────────
# Liens multi-OF par planning_entry (POST = ajoute, DELETE = retire)
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/api/admin/planning-of-links")
async def admin_add_planning_of_links(request: Request):
    user = _require_of_access(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Body JSON requis.")

    planning_id = body.get("planning_id")
    of_ids = body.get("of_ids")
    if not isinstance(planning_id, int):
        raise HTTPException(status_code=400, detail="planning_id (int) requis.")
    if not isinstance(of_ids, list) or not of_ids:
        raise HTTPException(status_code=400, detail="of_ids (liste non vide) requis.")
    of_ids = [int(x) for x in of_ids if isinstance(x, int) or (isinstance(x, str) and x.isdigit())]
    of_ids = list(dict.fromkeys(of_ids))  # dedup, garde ordre
    if not of_ids:
        raise HTTPException(status_code=400, detail="of_ids invalides.")

    who = (user.get("nom") or user.get("email") or str(user.get("id", ""))) if user else ""
    now = _now_paris_iso()
    added = 0
    skipped_existing = 0
    not_found: list = []
    with get_db() as conn:
        pe = conn.execute("SELECT id FROM planning_entries WHERE id=?", (planning_id,)).fetchone()
        if not pe:
            raise HTTPException(status_code=404, detail="Planning introuvable.")
        # Récupère la position max actuelle pour append à la fin
        cur_max = conn.execute(
            "SELECT COALESCE(MAX(position), -1) FROM planning_of_links WHERE planning_entry_id=?",
            (planning_id,),
        ).fetchone()[0]
        next_pos = int(cur_max) + 1
        for of_id in of_ids:
            oi = conn.execute("SELECT id FROM of_imports WHERE id=?", (of_id,)).fetchone()
            if not oi:
                not_found.append(of_id)
                continue
            cur = conn.execute(
                "SELECT id FROM planning_of_links WHERE planning_entry_id=? AND of_import_id=?",
                (planning_id, of_id),
            ).fetchone()
            if cur:
                skipped_existing += 1
                continue
            conn.execute(
                "INSERT INTO planning_of_links "
                "(planning_entry_id, of_import_id, position, created_by, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (planning_id, of_id, next_pos, who, now),
            )
            next_pos += 1
            added += 1
        # Action manuelle : désactive l'auto-link futur pour ce planning
        try:
            conn.execute("UPDATE planning_entries SET of_link_user_managed=1 WHERE id=?", (planning_id,))
        except Exception:
            pass
        conn.commit()
    return {
        "planning_id": planning_id,
        "added": added,
        "skipped_existing": skipped_existing,
        "not_found": not_found,
    }


@router.delete("/api/admin/planning-of-links")
async def admin_remove_planning_of_link(request: Request):
    _require_of_access(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Body JSON requis.")
    planning_id = body.get("planning_id")
    of_id = body.get("of_id")
    if not isinstance(planning_id, int) or not isinstance(of_id, int):
        raise HTTPException(status_code=400, detail="planning_id et of_id (int) requis.")
    with get_db() as conn:
        cur = conn.execute(
            "DELETE FROM planning_of_links WHERE planning_entry_id=? AND of_import_id=?",
            (planning_id, of_id),
        )
        # Action manuelle : désactive l'auto-link futur pour ce planning
        try:
            conn.execute("UPDATE planning_entries SET of_link_user_managed=1 WHERE id=?", (planning_id,))
        except Exception:
            pass
        conn.commit()
        deleted = cur.rowcount or 0
    return {"deleted": int(deleted), "planning_id": planning_id, "of_id": of_id}


# ─────────────────────────────────────────────────────────────────────────────
# Recherche d'OF (picker dans l'UI "Dossiers sans OF" et panneau planning)
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/api/of/search")
def of_search(request: Request):
    _require_of_access(request)
    q = (request.query_params.get("q") or "").strip()
    try:
        limit = int(request.query_params.get("limit") or 20)
    except Exception:
        limit = 20
    limit = max(1, min(limit, 50))
    rows = []
    with get_db() as conn:
        if q:
            like = f"%{q}%"
            rows = conn.execute(
                f"""SELECT {_OF_SELECT_COLS}
                    FROM of_imports
                    WHERE LOWER(COALESCE(of_numero,''))    LIKE LOWER(?)
                       OR LOWER(COALESCE(reference,''))   LIKE LOWER(?)
                       OR LOWER(COALESCE(machine,''))     LIKE LOWER(?)
                    ORDER BY date_import DESC, id DESC
                    LIMIT ?""",
                (like, like, like, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                f"""SELECT {_OF_SELECT_COLS}
                    FROM of_imports
                    ORDER BY date_import DESC, id DESC
                    LIMIT ?""",
                (limit,),
            ).fetchall()
    return {"items": [_row_dict(r) for r in rows]}

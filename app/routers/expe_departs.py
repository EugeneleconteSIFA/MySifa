"""
MyExpé — suivi des départs (exportations).
Accès : utilisateurs avec droit application « expe ».
"""
import csv
import io
import json
import os
import re
import shutil
import sqlite3
import unicodedata
import uuid
from io import BytesIO
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Body, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse

from app.services.audit_service import log_action
from app.services.email_service import email_expe_rfq_transport, send_email
from config import public_base_url
from app.services.expe_transporteurs_seed import seed_expe_transporteurs_if_empty
from database import get_db
from services.auth_service import get_current_user, user_can_write_expe, user_has_app_access

router = APIRouter()

_PARIS = ZoneInfo("Europe/Paris")

TARIF_UPLOAD_DIR = "data/uploads/transporteurs"
os.makedirs(TARIF_UPLOAD_DIR, exist_ok=True)

_ALLOWED_TARIF_EXT = {".pdf", ".xlsx", ".xls", ".jpg", ".jpeg", ".png", ".webp", ".gif"}


def _require_expe(request: Request) -> dict:
    user = get_current_user(request)
    if not user_has_app_access(user, "expe"):
        raise HTTPException(status_code=403, detail="Accès MyExpé requis")
    return user


def _require_expe_write(request: Request) -> dict:
    user = _require_expe(request)
    if not user_can_write_expe(user):
        raise HTTPException(status_code=403, detail="Accès MyExpé en lecture seule")
    return user


def _today_paris_iso() -> str:
    return datetime.now(_PARIS).date().isoformat()


def _norm_search(s: str) -> str:
    t = unicodedata.normalize("NFD", (s or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _row_blob(d: dict) -> str:
    parts = [
        d.get("date_enlevement"),
        d.get("affreteurs"),
        d.get("transporteur"),
        d.get("client"),
        d.get("code_postal_destination"),
        d.get("ref_sifa"),
        d.get("arc"),
        d.get("no_cde_transport"),
        d.get("no_bl"),
        d.get("type_palette_label"),
        d.get("type_palette_reference"),
        d.get("nb_palette"),
        d.get("poids_total_kg"),
        d.get("date_livraison"),
        d.get("created_by_email"),
        d.get("validated_by_email"),
        d.get("validated_at"),
    ]
    return _norm_search(" ".join(str(p) for p in parts if p is not None and str(p) != ""))


_HIST_SEARCH_COLS = (
    "d.date_enlevement",
    "d.affreteurs",
    "d.transporteur",
    "d.client",
    "d.code_postal_destination",
    "d.ref_sifa",
    "d.arc",
    "d.no_cde_transport",
    "d.no_bl",
    "mp.reference",
    "mp.designation",
    "d.nb_palette",
    "d.poids_total_kg",
    "d.date_livraison",
    "d.created_by_email",
    "d.validated_by_email",
    "d.validated_at",
)


def _historique_search_clause(q: str) -> tuple[str, list[Any]]:
    """Clause SQL AND … pour la recherche multi-mots (tous les tokens requis)."""
    qt = _norm_search(q)
    if not qt:
        return "", []
    tokens = [t for t in qt.split(" ") if t]
    if not tokens:
        return "", []
    parts: list[str] = []
    params: list[Any] = []
    ncols = len(_HIST_SEARCH_COLS)
    for tok in tokens:
        likes = " OR ".join(
            f"LOWER(COALESCE(CAST({c} AS TEXT), '')) LIKE ?" for c in _HIST_SEARCH_COLS
        )
        parts.append(f"({likes})")
        params.extend([f"%{tok}%"] * ncols)
    return " AND ".join(parts), params


_DEPARTS_SELECT = """
    SELECT d.*,
           mp.reference AS type_palette_reference,
           mp.designation AS type_palette_designation
    FROM expe_departs d
    LEFT JOIN matieres_premieres mp ON mp.id = d.type_palette_matiere_id
"""


def _depart_dict(row) -> dict:
    d = dict(row)
    ref = (d.get("type_palette_reference") or "").strip()
    des = (d.get("type_palette_designation") or "").strip()
    if ref:
        d["type_palette_label"] = f"{ref} — {des}" if des else ref
    else:
        d["type_palette_label"] = None
    return d


def _validate_type_palette_matiere_id(conn, matiere_id: Any) -> Optional[int]:
    if matiere_id is None or matiere_id == "":
        return None
    try:
        mid = int(matiere_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Type de palette invalide.")
    row = conn.execute(
        """SELECT id FROM matieres_premieres
           WHERE id=? AND actif=1 AND categorie='palette'""",
        (mid,),
    ).fetchone()
    if not row:
        raise HTTPException(
            status_code=400,
            detail="Type de palette introuvable ou inactif (réf. MyStock).",
        )
    return mid


def _date_prefix(raw: str) -> str:
    """Extrait YYYY-MM-DD depuis une saisie date ou datetime."""
    s = (raw or "").strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return s


def _now_paris_iso() -> str:
    return datetime.now(_PARIS).replace(tzinfo=None).isoformat(timespec="seconds")


def _f(body: dict, key: str) -> Any:
    v = body.get(key)
    if v is None or v == "":
        return None
    return v


def _float_opt(body: dict, key: str) -> Any:
    v = body.get(key)
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(",", ".").replace("\u202f", "").replace(" ", ""))
    except ValueError:
        return None


def _int_flag(body: dict, key: str, default: Optional[int] = None) -> Optional[int]:
    if key not in body:
        return default
    v = body.get(key)
    if v is None or v == "":
        return 0
    if v in (1, True, "1", "true", "True"):
        return 1
    return 0


def _int_opt(body: dict, key: str) -> Any:
    v = body.get(key)
    if v is None or v == "":
        return None
    try:
        return int(v)
    except (ValueError, TypeError):
        return None


def _safe_tarif_filename(name: str) -> str:
    base = Path(name or "tarif").name
    base = re.sub(r"[^\w.\- ]", "_", base, flags=re.UNICODE).strip("._ ") or "tarif"
    return base[:120]


def _tarif_abs_root() -> str:
    from config import BASE_DIR

    return os.path.abspath(os.path.join(BASE_DIR, TARIF_UPLOAD_DIR))


def _resolve_tarif_path(tarif_url: Optional[str]) -> Optional[str]:
    if not tarif_url:
        return None
    from config import BASE_DIR

    p = tarif_url.strip()
    if not p:
        return None
    if not os.path.isabs(p):
        p = os.path.join(BASE_DIR, p)
    abs_p = os.path.abspath(p)
    root = _tarif_abs_root()
    if abs_p != root and not abs_p.startswith(root + os.sep):
        return None
    return abs_p if os.path.isfile(abs_p) else None


def _unlink_tarif(tarif_url: Optional[str]) -> None:
    p = _resolve_tarif_path(tarif_url)
    if p:
        try:
            os.unlink(p)
        except OSError:
            pass


@router.get("/matieres-palettes")
def list_matieres_palettes_expe(request: Request):
    """Références palettes actives (catégorie palette, MyStock matières premières)."""
    _require_expe(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, reference, designation, palettes_par_pile
               FROM matieres_premieres
               WHERE actif=1 AND categorie='palette'
               ORDER BY reference COLLATE NOCASE"""
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/departs/jour")
def list_departs_jour(
    request: Request,
    date: Optional[str] = Query(None, description="YYYY-MM-DD (défaut : jour Paris)"),
):
    _require_expe(request)
    with get_db() as conn:
        rows = conn.execute(
            f"""{_DEPARTS_SELECT}
               WHERE d.statut = 'en_attente'
               ORDER BY d.date_enlevement ASC, d.id ASC""",
        ).fetchall()
    return [_depart_dict(r) for r in rows]


@router.post("/departs")
def create_depart(request: Request, body: dict = Body(...)):
    user = _require_expe_write(request)
    date_enl = _date_prefix(str(body.get("date_enlevement") or "").strip())
    if not date_enl or not re.match(r"^\d{4}-\d{2}-\d{2}$", date_enl):
        raise HTTPException(status_code=400, detail="Date d'enlèvement obligatoire (YYYY-MM-DD)")
    now = datetime.now(_PARIS).replace(tzinfo=None).isoformat(timespec="seconds")
    email = (user.get("email") or user.get("identifiant") or "").strip() or None

    def _f(key: str) -> Any:
        v = body.get(key)
        if v is None or v == "":
            return None
        return v

    def _float_opt(key: str) -> Any:
        v = body.get(key)
        if v is None or v == "":
            return None
        try:
            return float(str(v).replace(",", ".").replace("\u202f", "").replace(" ", ""))
        except ValueError:
            return None

    with get_db() as conn:
        type_palette_id = _validate_type_palette_matiere_id(
            conn, body.get("type_palette_matiere_id")
        )
        cur = conn.execute(
            """INSERT INTO expe_departs (
                date_enlevement, affreteurs, transporteur, transporteur_id, client,
                code_postal_destination,
                ref_sifa, arc, no_cde_transport, no_bl, type_palette_matiere_id,
                nb_palette, poids_total_kg, date_livraison,
                statut, created_at, created_by_email
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'en_attente', ?, ?)""",
            (
                date_enl,
                _f("affreteurs"),
                _f("transporteur"),
                _int_opt(body, "transporteur_id"),
                _f("client"),
                _f("code_postal_destination"),
                _f("ref_sifa"),
                _f("arc"),
                _f("no_cde_transport"),
                _f("no_bl"),
                type_palette_id,
                _float_opt("nb_palette"),
                _float_opt("poids_total_kg"),
                _f("date_livraison"),
                now,
                email,
            ),
        )
        conn.commit()
        rid = cur.lastrowid
        row = conn.execute(
            f"{_DEPARTS_SELECT} WHERE d.id=?", (rid,)
        ).fetchone()
    client_nom = (body.get("client") or "").strip() or "—"
    log_action(
        user=user,
        action="CREATE",
        module="expe",
        objet=f"Départ {client_nom} · {date_enl}",
        ip=request.client.host if request.client else None,
    )
    return _depart_dict(row)


@router.post("/departs/{depart_id}/valider")
def valider_depart(request: Request, depart_id: int):
    user = _require_expe_write(request)
    now = datetime.now(_PARIS).replace(tzinfo=None).isoformat(timespec="seconds")
    email = (user.get("email") or user.get("identifiant") or "").strip() or None
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, statut FROM expe_departs WHERE id=?",
            (depart_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Départ introuvable")
        if row["statut"] != "en_attente":
            raise HTTPException(status_code=400, detail="Ce départ est déjà validé ou annulé")
        conn.execute(
            """UPDATE expe_departs SET statut='valide', validated_at=?, validated_by_email=?
               WHERE id=?""",
            (now, email, depart_id),
        )
        conn.commit()
        out = conn.execute(
            f"{_DEPARTS_SELECT} WHERE d.id=?", (depart_id,)
        ).fetchone()
    client_nom = (out["client"] or "").strip() if out else "—"
    log_action(
        user=user,
        action="VALIDATE",
        module="expe",
        objet=f"Départ #{depart_id} validé · {client_nom}",
        ip=request.client.host if request.client else None,
    )
    return _depart_dict(out)


@router.post("/departs/{depart_id}/invalider")
def invalider_depart(request: Request, depart_id: int):
    """Remet un départ validé dans le suivi du jour (statut en_attente)."""
    user = _require_expe_write(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, statut, client FROM expe_departs WHERE id=?",
            (depart_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Départ introuvable")
        if row["statut"] != "valide":
            raise HTTPException(
                status_code=400,
                detail="Seuls les départs validés peuvent être remis en suivi.",
            )
        conn.execute(
            """UPDATE expe_departs
               SET statut='en_attente', validated_at=NULL, validated_by_email=NULL
               WHERE id=?""",
            (depart_id,),
        )
        conn.commit()
        out = conn.execute(
            f"{_DEPARTS_SELECT} WHERE d.id=?", (depart_id,)
        ).fetchone()
    client_nom = (out["client"] or "").strip() if out else "—"
    log_action(
        user=user,
        action="UPDATE",
        module="expe",
        objet=f"Départ #{depart_id} remis en suivi · {client_nom}",
        ip=request.client.host if request.client else None,
    )
    return _depart_dict(out)


@router.put("/departs/{depart_id}")
async def update_depart(request: Request, depart_id: int, body: dict = Body(...)):
    """Modifie un départ (en attente ou validé)."""
    user = _require_expe_write(request)

    def _f(key: str) -> Any:
        v = body.get(key)
        if v is None or v == "":
            return None
        return v

    def _float_opt(key: str) -> Any:
        v = body.get(key)
        if v is None or v == "":
            return None
        try:
            return float(str(v).replace(",", ".").replace("\u202f", "").replace(" ", ""))
        except ValueError:
            return None

    sets = []
    args: list[Any] = []

    # Optionnel : permettre de modifier la date d'enlèvement si fournie
    if "date_enlevement" in body:
        date_enl = _date_prefix(str(body.get("date_enlevement") or "").strip())
        if not date_enl or not re.match(r"^\d{4}-\d{2}-\d{2}$", date_enl):
            raise HTTPException(status_code=400, detail="Date d'enlèvement invalide (YYYY-MM-DD)")
        sets.append("date_enlevement=?")
        args.append(date_enl)

    fields_text = [
        "affreteurs",
        "transporteur",
        "client",
        "code_postal_destination",
        "ref_sifa",
        "arc",
        "no_cde_transport",
        "no_bl",
        "date_livraison",
    ]
    for k in fields_text:
        if k in body:
            sets.append(f"{k}=?")
            args.append(_f(k))

    if "transporteur_id" in body:
        sets.append("transporteur_id=?")
        args.append(_int_opt(body, "transporteur_id"))

    if "type_palette_matiere_id" in body:
        sets.append("type_palette_matiere_id=?")
        args.append(None)  # remplacé après ouverture connexion

    fields_num = ["nb_palette", "poids_total_kg"]
    for k in fields_num:
        if k in body:
            sets.append(f"{k}=?")
            args.append(_float_opt(k))

    if not sets:
        raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour")

    with get_db() as conn:
        if "type_palette_matiere_id" in body:
            idx = next(i for i, s in enumerate(sets) if s.startswith("type_palette_matiere_id"))
            args[idx] = _validate_type_palette_matiere_id(
                conn, body.get("type_palette_matiere_id")
            )
        ex = conn.execute("SELECT id, statut FROM expe_departs WHERE id=?", (depart_id,)).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Départ introuvable")
        if ex["statut"] not in ("en_attente", "valide"):
            raise HTTPException(status_code=409, detail="Modification impossible : départ annulé")

        conn.execute(f"UPDATE expe_departs SET {', '.join(sets)} WHERE id=?", (*args, depart_id))
        conn.commit()
        row = conn.execute(
            f"{_DEPARTS_SELECT} WHERE d.id=?", (depart_id,)
        ).fetchone()
    client_nom = (row["client"] or "").strip() if row else "—"
    log_action(
        user=user,
        action="UPDATE",
        module="expe",
        objet=f"Départ #{depart_id} · {client_nom}",
        ip=request.client.host if request.client else None,
    )
    return _depart_dict(row)


@router.delete("/departs/{depart_id}")
def delete_depart(request: Request, depart_id: int):
    """Supprime un départ (en attente ou validé)."""
    user = _require_expe_write(request)
    client_nom = ""
    with get_db() as conn:
        ex = conn.execute(
            "SELECT id, statut, client FROM expe_departs WHERE id=?", (depart_id,)
        ).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Départ introuvable")
        if ex["statut"] not in ("en_attente", "valide"):
            raise HTTPException(status_code=409, detail="Suppression impossible : départ annulé")
        client_nom = (ex["client"] or "").strip() or "—"
        conn.execute("DELETE FROM expe_departs WHERE id=?", (depart_id,))
        conn.commit()
    log_action(
        user=user,
        action="DELETE",
        module="expe",
        objet=f"Départ #{depart_id} supprimé · {client_nom}",
        ip=request.client.host if request.client else None,
    )
    return {"ok": True}


@router.get("/departs/historique")
def historique_departs(
    request: Request,
    q: str = "",
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
):
    _require_expe(request)
    search_sql, search_params = _historique_search_clause(q)
    where = "WHERE d.statut = 'valide'"
    if search_sql:
        where += f" AND ({search_sql})"
    offset = (page - 1) * limit
    with get_db() as conn:
        total = conn.execute(
            f"""SELECT COUNT(*) AS n
                FROM expe_departs d
                LEFT JOIN matieres_premieres mp ON mp.id = d.type_palette_matiere_id
                {where}""",
            search_params,
        ).fetchone()["n"]
        rows = conn.execute(
            f"""{_DEPARTS_SELECT}
                {where}
                ORDER BY datetime(COALESCE(d.validated_at, d.created_at)) DESC, d.id DESC
                LIMIT ? OFFSET ?""",
            (*search_params, limit, offset),
        ).fetchall()
    pages = max(1, (int(total) + limit - 1) // limit) if total else 1
    if page > pages:
        page = pages
    return {
        "rows": [_depart_dict(r) for r in rows],
        "total": int(total),
        "page": page,
        "limit": limit,
        "pages": pages,
    }


# ─── Transporteurs ───────────────────────────────────────────────────


@router.get("/transporteurs")
def list_transporteurs(request: Request):
    _require_expe(request)
    with get_db() as conn:
        seed_expe_transporteurs_if_empty(conn)
        conn.commit()
        rows = conn.execute(
            """SELECT * FROM expe_transporteurs
               ORDER BY actif DESC, nom ASC"""
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("/transporteurs")
def create_transporteur(request: Request, body: dict = Body(...)):
    user = _require_expe_write(request)
    nom = (body.get("nom") or "").strip()
    if not nom:
        raise HTTPException(status_code=400, detail="Nom du transporteur obligatoire")
    now = _now_paris_iso()
    taxe = _float_opt(body, "taxe_carburant_pct")
    if taxe is None:
        taxe = 0.0
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO expe_transporteurs (
                nom, taxe_carburant_pct, contact_nom, contact_email, contact_tel,
                zone_france, zone_france_hors_paris, zone_affretement, zone_messagerie,
                palette_max, poids_max_kg, accepte_poids, accepte_palette,
                actif, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                nom,
                taxe,
                _f(body, "contact_nom"),
                _f(body, "contact_email"),
                _f(body, "contact_tel"),
                _int_flag(body, "zone_france", 1),
                _int_flag(body, "zone_france_hors_paris", 0),
                _int_flag(body, "zone_affretement", 0),
                _int_flag(body, "zone_messagerie", 0),
                _int_opt(body, "palette_max"),
                _float_opt(body, "poids_max_kg"),
                _int_flag(body, "accepte_poids", 1),
                _int_flag(body, "accepte_palette", 1),
                _int_flag(body, "actif", 1),
                now,
            ),
        )
        conn.commit()
        rid = cur.lastrowid
        row = conn.execute(
            "SELECT * FROM expe_transporteurs WHERE id=?", (rid,)
        ).fetchone()
    log_action(
        user=user,
        action="CREATE",
        module="expe",
        objet=f"Transporteur {nom}",
        ip=request.client.host if request.client else None,
    )
    return dict(row)


@router.put("/transporteurs/{transporteur_id}")
def update_transporteur(
    request: Request, transporteur_id: int, body: dict = Body(...)
):
    user = _require_expe_write(request)
    sets = []
    args: list[Any] = []

    if "nom" in body:
        nom = (body.get("nom") or "").strip()
        if not nom:
            raise HTTPException(status_code=400, detail="Nom du transporteur obligatoire")
        sets.append("nom=?")
        args.append(nom)

    if "taxe_carburant_pct" in body:
        taxe = _float_opt(body, "taxe_carburant_pct")
        sets.append("taxe_carburant_pct=?")
        args.append(0.0 if taxe is None else taxe)

    for k in ("contact_nom", "contact_email", "contact_tel"):
        if k in body:
            sets.append(f"{k}=?")
            args.append(_f(body, k))

    for k in (
        "zone_france",
        "zone_france_hors_paris",
        "zone_affretement",
        "zone_messagerie",
        "actif",
        "accepte_poids",
        "accepte_palette",
    ):
        if k in body:
            sets.append(f"{k}=?")
            args.append(_int_flag(body, k, 0))

    if "palette_max" in body:
        sets.append("palette_max=?")
        args.append(_int_opt(body, "palette_max"))

    if "poids_max_kg" in body:
        sets.append("poids_max_kg=?")
        args.append(_float_opt(body, "poids_max_kg"))

    if not sets:
        raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour")

    sets.append("updated_at=?")
    args.append(_now_paris_iso())

    with get_db() as conn:
        ex = conn.execute(
            "SELECT id, nom FROM expe_transporteurs WHERE id=?",
            (transporteur_id,),
        ).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Transporteur introuvable")
        conn.execute(
            f"UPDATE expe_transporteurs SET {', '.join(sets)} WHERE id=?",
            (*args, transporteur_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM expe_transporteurs WHERE id=?", (transporteur_id,)
        ).fetchone()
    nom_log = (row["nom"] or ex["nom"] or "").strip() if row else f"#{transporteur_id}"
    log_action(
        user=user,
        action="UPDATE",
        module="expe",
        objet=f"Transporteur {nom_log}",
        ip=request.client.host if request.client else None,
    )
    return dict(row)


@router.delete("/transporteurs/{transporteur_id}")
def delete_transporteur(request: Request, transporteur_id: int):
    user = _require_expe_write(request)
    now = _now_paris_iso()
    with get_db() as conn:
        ex = conn.execute(
            "SELECT id, nom FROM expe_transporteurs WHERE id=?",
            (transporteur_id,),
        ).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Transporteur introuvable")
        conn.execute(
            "UPDATE expe_transporteurs SET actif=0, updated_at=? WHERE id=?",
            (now, transporteur_id),
        )
        conn.commit()
    nom_log = (ex["nom"] or "").strip() or f"#{transporteur_id}"
    log_action(
        user=user,
        action="DELETE",
        module="expe",
        objet=f"Transporteur {nom_log} (désactivé)",
        ip=request.client.host if request.client else None,
    )
    return {"ok": True}


@router.post("/transporteurs/{transporteur_id}/tarif")
async def upload_transporteur_tarif(
    request: Request,
    transporteur_id: int,
    fichier: UploadFile = File(...),
):
    user = _require_expe_write(request)
    raw_name = fichier.filename or "tarif"
    safe_name = _safe_tarif_filename(raw_name)
    ext = Path(safe_name).suffix.lower()
    if ext not in _ALLOWED_TARIF_EXT:
        raise HTTPException(
            status_code=400,
            detail="Format non accepté (PDF, Excel, image).",
        )
    content = await fichier.read()
    if not content:
        raise HTTPException(status_code=400, detail="Fichier vide.")
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Fichier trop volumineux (max 15 Mo).")

    stored_name = f"{uuid.uuid4().hex}_{safe_name}"
    rel_url = f"{TARIF_UPLOAD_DIR}/{stored_name}"
    from config import BASE_DIR

    dest_path = os.path.join(BASE_DIR, rel_url)
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    with get_db() as conn:
        ex = conn.execute(
            "SELECT id, nom, tarif_url FROM expe_transporteurs WHERE id=?",
            (transporteur_id,),
        ).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Transporteur introuvable")
        old_url = ex["tarif_url"]
        try:
            with open(dest_path, "wb") as out:
                shutil.copyfileobj(BytesIO(content), out)
        except OSError:
            raise HTTPException(status_code=500, detail="Enregistrement du fichier impossible.")
        now = _now_paris_iso()
        conn.execute(
            """UPDATE expe_transporteurs
               SET tarif_filename=?, tarif_url=?, updated_at=?
               WHERE id=?""",
            (safe_name, rel_url, now, transporteur_id),
        )
        conn.commit()
    _unlink_tarif(old_url)
    nom_log = (ex["nom"] or "").strip() or f"#{transporteur_id}"
    log_action(
        user=user,
        action="UPDATE",
        module="expe",
        objet=f"Transporteur {nom_log} · tarif",
        ip=request.client.host if request.client else None,
    )
    return {"ok": True, "tarif_url": rel_url}


@router.delete("/transporteurs/{transporteur_id}/tarif")
def delete_transporteur_tarif(request: Request, transporteur_id: int):
    user = _require_expe_write(request)
    with get_db() as conn:
        ex = conn.execute(
            "SELECT id, nom, tarif_url FROM expe_transporteurs WHERE id=?",
            (transporteur_id,),
        ).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Transporteur introuvable")
        old_url = ex["tarif_url"]
        now = _now_paris_iso()
        conn.execute(
            """UPDATE expe_transporteurs
               SET tarif_filename=NULL, tarif_url=NULL, updated_at=?
               WHERE id=?""",
            (now, transporteur_id),
        )
        conn.commit()
    _unlink_tarif(old_url)
    nom_log = (ex["nom"] or "").strip() or f"#{transporteur_id}"
    log_action(
        user=user,
        action="UPDATE",
        module="expe",
        objet=f"Transporteur {nom_log} · tarif supprimé",
        ip=request.client.host if request.client else None,
    )
    return {"ok": True}


@router.get("/transporteurs/{transporteur_id}/tarif")
def get_transporteur_tarif(request: Request, transporteur_id: int):
    _require_expe(request)
    with get_db() as conn:
        ex = conn.execute(
            "SELECT tarif_url, tarif_filename FROM expe_transporteurs WHERE id=?",
            (transporteur_id,),
        ).fetchone()
    if not ex:
        raise HTTPException(status_code=404, detail="Transporteur introuvable")
    if not ex["tarif_url"]:
        raise HTTPException(status_code=404, detail="Aucun tarif enregistré")
    path = _resolve_tarif_path(ex["tarif_url"])
    if not path:
        raise HTTPException(status_code=404, detail="Fichier tarif introuvable")
    filename = (ex["tarif_filename"] or Path(path).name) or "tarif"
    return FileResponse(path=path, filename=filename)


# ─── Tarifs structurés ─────────────────────────────────────────────


@router.get("/transporteurs/{transporteur_id}/tarifs")
def list_tarifs(request: Request, transporteur_id: int):
    _require_expe(request)
    with get_db() as conn:
        if not conn.execute(
            "SELECT 1 FROM expe_transporteurs WHERE id=?", (transporteur_id,)
        ).fetchone():
            raise HTTPException(status_code=404, detail="Transporteur introuvable")
        lignes = conn.execute(
            """SELECT * FROM expe_tarifs WHERE transporteur_id=?
               ORDER BY type_envoi, zone_valeur, tranche_min""",
            (transporteur_id,),
        ).fetchall()
        frais = conn.execute(
            """SELECT * FROM expe_tarifs_frais WHERE transporteur_id=?
               ORDER BY libelle""",
            (transporteur_id,),
        ).fetchall()
    return {"lignes": [dict(r) for r in lignes], "frais": [dict(r) for r in frais]}


@router.post("/transporteurs/{transporteur_id}/tarifs/import-csv")
async def import_tarifs_csv(
    request: Request,
    transporteur_id: int,
    file: UploadFile = File(...),
):
    user = _require_expe_write(request)
    now = datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    cols_oblig = {
        "type_envoi",
        "base_calcul",
        "zone_type",
        "zone_valeur",
        "tranche_min",
        "prix",
        "unite",
    }
    rows = list(reader)
    if not rows:
        raise HTTPException(status_code=400, detail="CSV vide")
    if not cols_oblig.issubset(set(rows[0].keys())):
        raise HTTPException(
            status_code=400,
            detail=f"Colonnes manquantes. Attendu : {', '.join(sorted(cols_oblig))}",
        )

    def _csv_f(row: dict, k: str) -> Any:
        v = (row.get(k) or "").strip()
        return v or None

    def _csv_r(row: dict, k: str) -> Any:
        v = _csv_f(row, k)
        return float(v) if v is not None else None

    inserted = 0
    with get_db() as conn:
        if not conn.execute(
            "SELECT 1 FROM expe_transporteurs WHERE id=?", (transporteur_id,)
        ).fetchone():
            raise HTTPException(status_code=404, detail="Transporteur introuvable")
        for row in rows:
            conn.execute(
                """INSERT INTO expe_tarifs
                   (transporteur_id, type_envoi, base_calcul, zone_type, zone_valeur,
                    tranche_min, tranche_max, prix, unite, mini_perception,
                    valid_from, valid_to, actif, source_filename, created_at, created_by_email)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,0,?,?,?)""",
                (
                    transporteur_id,
                    _csv_f(row, "type_envoi"),
                    _csv_f(row, "base_calcul"),
                    _csv_f(row, "zone_type"),
                    _csv_f(row, "zone_valeur"),
                    float(row.get("tranche_min") or 0),
                    _csv_r(row, "tranche_max"),
                    float(row.get("prix") or 0),
                    _csv_f(row, "unite"),
                    _csv_r(row, "mini_perception"),
                    _csv_f(row, "valid_from"),
                    _csv_f(row, "valid_to"),
                    file.filename,
                    now,
                    user.get("email") or user.get("identifiant"),
                ),
            )
            inserted += 1
        conn.commit()
    return {
        "inserted": inserted,
        "actif": 0,
        "message": f"{inserted} lignes importées en brouillon — à valider.",
    }


@router.post("/transporteurs/{transporteur_id}/tarifs/valider")
def valider_tarifs(
    request: Request, transporteur_id: int, body: dict = Body(...)
):
    _require_expe_write(request)
    ids = body.get("ids") or []
    with get_db() as conn:
        if not conn.execute(
            "SELECT 1 FROM expe_transporteurs WHERE id=?", (transporteur_id,)
        ).fetchone():
            raise HTTPException(status_code=404, detail="Transporteur introuvable")
        if ids:
            placeholders = ",".join("?" * len(ids))
            conn.execute(
                f"""UPDATE expe_tarifs SET actif=1
                    WHERE transporteur_id=? AND id IN ({placeholders})""",
                (transporteur_id, *ids),
            )
        else:
            conn.execute(
                "UPDATE expe_tarifs SET actif=1 WHERE transporteur_id=? AND actif=0",
                (transporteur_id,),
            )
        conn.commit()
        updated = conn.execute(
            "SELECT COUNT(*) AS n FROM expe_tarifs WHERE transporteur_id=? AND actif=1",
            (transporteur_id,),
        ).fetchone()["n"]
    return {"actives": updated}


@router.delete("/transporteurs/{transporteur_id}/tarifs")
def vider_tarifs_transporteur(request: Request, transporteur_id: int):
    """Supprime toutes les lignes tarifaires importées (grille + frais annexes)."""
    user = _require_expe_write(request)
    with get_db() as conn:
        ex = conn.execute(
            "SELECT id, nom FROM expe_transporteurs WHERE id=?",
            (transporteur_id,),
        ).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Transporteur introuvable")
        n_lignes = conn.execute(
            "SELECT COUNT(*) AS n FROM expe_tarifs WHERE transporteur_id=?",
            (transporteur_id,),
        ).fetchone()["n"]
        n_frais = conn.execute(
            "SELECT COUNT(*) AS n FROM expe_tarifs_frais WHERE transporteur_id=?",
            (transporteur_id,),
        ).fetchone()["n"]
        conn.execute(
            "DELETE FROM expe_tarifs WHERE transporteur_id=?",
            (transporteur_id,),
        )
        conn.execute(
            "DELETE FROM expe_tarifs_frais WHERE transporteur_id=?",
            (transporteur_id,),
        )
        conn.commit()
    nom_log = (ex["nom"] or "").strip() or f"#{transporteur_id}"
    log_action(
        user=user,
        action="DELETE",
        module="expe",
        objet=f"Transporteur {nom_log} · tarifs vidés ({n_lignes} lignes, {n_frais} frais)",
        ip=request.client.host if request.client else None,
    )
    return {"deleted_lignes": n_lignes, "deleted_frais": n_frais}


_PROMPT_EXTRACTION_TARIF = """Tu es un expert en tarification transport en France.
Analyse cette grille tarifaire et extrait TOUTES les lignes tarifaires au format JSON strict.

Retourne UNIQUEMENT un objet JSON avec deux clés :
- "lignes" : liste de lignes tarifaires
- "frais" : liste de frais annexes (gasoil, sûreté, hayon, RDV, etc.)

Chaque ligne tarifaire a ces champs (tous requis sauf mention) :
{
  "type_envoi": "messagerie" | "ramasse" | "affretement" | "express_intl",
  "base_calcul": "poids" | "palette" | "metre_plancher",
  "zone_type": "departement" | "code_postal" | "zone_intl" | "pays",
  "zone_valeur": "59" (numéro département) | "59200" (CP) | "7" (zone intl) | "DE" (pays),
  "tranche_min": 0,
  "tranche_max": 10,
  "prix": 12.50,
  "unite": "forfait" | "au_100kg" | "au_kg",
  "mini_perception": 8.50
}

Chaque frais annexe a ces champs :
{
  "libelle": "Gasoil",
  "mode": "pct_transport" | "forfait_expedition" | "par_palette",
  "valeur": 12.8,
  "mini": null,
  "applique_defaut": 1
}

Règles importantes :
- Si la grille est par poids avec des tranches forfait puis au 100kg : utilise unite="forfait" pour les tranches ≤ 100 kg et unite="au_100kg" pour les tranches > 100 kg.
- Si la grille est par palette : base_calcul="palette", unite="forfait".
- zone_valeur pour les départements français : toujours en 2 caractères ("01".."95", "2A", "2B") ou 3 pour DOM ("971".."976").
- Si une cellule est vide ou marquée "NC" / "-" : ignorer cette ligne.
- Extraire les frais depuis les onglets "Conditions commerciales" ou équivalents.

Ne retourne rien d'autre que le JSON.
"""


def _parse_tarif_json_raw(raw: str) -> dict:
    text = (raw or "").strip()
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
            if text.startswith("json"):
                text = text[4:]
    return json.loads(text.strip())


@router.post("/transporteurs/{transporteur_id}/tarif/parse")
async def parse_tarif_ia(request: Request, transporteur_id: int):
    user = _require_expe_write(request)
    from config import ANTHROPIC_API_KEY

    if not ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Clé Anthropic non configurée — ajouter ANTHROPIC_API_KEY dans .env",
        )

    with get_db() as conn:
        trp = conn.execute(
            "SELECT * FROM expe_transporteurs WHERE id=?", (transporteur_id,)
        ).fetchone()
    if not trp:
        raise HTTPException(status_code=404, detail="Transporteur introuvable")
    if not trp["tarif_url"]:
        raise HTTPException(status_code=400, detail="Aucun fichier tarif uploadé pour ce transporteur")

    filepath = _resolve_tarif_path(trp["tarif_url"])
    if not filepath:
        raise HTTPException(status_code=404, detail="Fichier tarif introuvable sur le disque")

    ext = os.path.splitext(filepath)[1].lower()

    if ext in (".xlsx", ".xls"):
        import openpyxl

        wb = openpyxl.load_workbook(filepath, data_only=True)
        parts = []
        for ws in wb.worksheets:
            parts.append(f"=== Feuille : {ws.title} ===")
            for row in ws.iter_rows(values_only=True):
                line = "\t".join("" if c is None else str(c) for c in row)
                if line.strip():
                    parts.append(line)
        file_text = "\n".join(parts)
        content_block = {
            "type": "text",
            "text": f"Voici la grille tarifaire au format texte (extrait Excel) :\n\n{file_text}",
        }
    elif ext == ".pdf":
        import base64

        with open(filepath, "rb") as f:
            b64 = base64.standard_b64encode(f.read()).decode("utf-8")
        content_block = {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": b64,
            },
        }
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Format non supporté : {ext}. Uploader un .xlsx ou .pdf.",
        )

    import anthropic as _anthropic

    client = _anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=8192,
        messages=[
            {
                "role": "user",
                "content": [
                    content_block,
                    {"type": "text", "text": _PROMPT_EXTRACTION_TARIF},
                ],
            }
        ],
    )

    raw = message.content[0].text
    data = _parse_tarif_json_raw(raw)

    now = datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")
    lignes_data = data.get("lignes", [])
    frais_data = data.get("frais", [])
    source_name = trp["tarif_filename"] or trp["tarif_url"]
    email = user.get("email") or user.get("identifiant")

    with get_db() as conn:
        for lg in lignes_data:
            conn.execute(
                """INSERT INTO expe_tarifs
                   (transporteur_id, type_envoi, base_calcul, zone_type, zone_valeur,
                    tranche_min, tranche_max, prix, unite, mini_perception,
                    actif, source_filename, created_at, created_by_email)
                   VALUES (?,?,?,?,?,?,?,?,?,?,0,?,?,?)""",
                (
                    transporteur_id,
                    lg.get("type_envoi"),
                    lg.get("base_calcul"),
                    lg.get("zone_type"),
                    lg.get("zone_valeur"),
                    lg.get("tranche_min", 0),
                    lg.get("tranche_max"),
                    lg.get("prix", 0),
                    lg.get("unite"),
                    lg.get("mini_perception"),
                    source_name,
                    now,
                    email,
                ),
            )
        for fr in frais_data:
            conn.execute(
                """INSERT OR IGNORE INTO expe_tarifs_frais
                   (transporteur_id, libelle, mode, valeur, mini, applique_defaut)
                   VALUES (?,?,?,?,?,?)""",
                (
                    transporteur_id,
                    fr.get("libelle"),
                    fr.get("mode"),
                    fr.get("valeur", 0),
                    fr.get("mini"),
                    fr.get("applique_defaut", 1),
                ),
            )
        conn.commit()

    return {
        "lignes_extraites": len(lignes_data),
        "frais_extraits": len(frais_data),
        "actif": 0,
        "apercu_lignes": lignes_data[:10],
        "message": (
            f"{len(lignes_data)} lignes et {len(frais_data)} frais extraits — "
            "à valider avant activation."
        ),
    }


def _tarif_float(v, default=None):
    """Convertit une valeur de cellule en float, None si impossible."""
    import math as _math

    try:
        f = float(str(v).strip().replace(",", "."))
        return None if _math.isnan(f) else f
    except Exception:
        return default


def _tarif_dept_from_label(label):
    """
    Extrait le code département depuis des formats variés :
      '(59) NORD'  →  '59'
      '59 - NORD'  →  '59'
      'FR59'       →  '59'
      '02'         →  '02'
    """
    s = str(label or "").strip()
    m = re.search(r"\((\w{1,3})\)", s)
    if m:
        code = m.group(1)
        return code.upper() if code.upper() in ("2A", "2B") else code.zfill(2)
    m = re.match(r"^FR(\w{2,3})$", s.upper())
    if m:
        code = m.group(1)
        return code.upper() if code.upper() in ("2A", "2B") else code.lstrip("0").zfill(2)
    m = re.match(r"^(\d{2,3})\s*[-–]?\s*", s)
    if m:
        code = m.group(1)
        return code.zfill(2) if len(code) <= 3 else None
    return None


def _tarif_unite_norm(v):
    s = str(v or "").strip().upper()
    if "100" in s:
        return "au_100kg"
    if "KG" in s and "100" not in s:
        return "au_kg"
    return "forfait"


def _tarif_find_header_row(ws, keywords, max_scan=40):
    """Retourne le numéro de la première ligne contenant un keyword (insensible à la casse)."""
    keywords_up = [k.upper() for k in keywords]
    for r in range(1, max_scan + 1):
        for c in range(1, min(ws.max_column + 1, 20)):
            val = str(ws.cell(row=r, column=c).value or "").upper()
            if any(k in val for k in keywords_up):
                return r
    return None


def _detect_tarif_format(wb):
    """
    Détecte le format de la grille tarifaire en examinant noms de feuilles + cellules clés.
    Retourne : 'compte100346' | 'ceva' | 'transbenelux' | 'generique'
    """
    sheet_names = " | ".join(ws.title.upper() for ws in wb.worksheets)

    if any(k in sheet_names for k in ("MESSAGERIE", "SMARTPAL", "SMART PAL", "CONDITIONS COMMERCIALES")):
        return "ceva"

    if any(k in sheet_names for k in ("BENELUX", "TRANSBENELUX", "SIFA VERS FRANCE")):
        return "transbenelux"

    for ws in wb.worksheets:
        a8 = str(ws["A8"].value or "").upper()
        if "POIDS" in a8 or "PALETTE" in a8:
            return "compte100346"

    return "generique"


def _parse_compte100346(wb, source_filename):
    """
    Format SIFA 010126 - P U (Compte 100346) :
    - Feuille avec A8 = "POIDS" ou "PALETTE"
    - Ligne 10 : bornes basses (DE)
    - Ligne 11 : bornes hautes (A)
    - Ligne 12 : unité (Forfait / Prx/100Kg)
    - Données à partir de la ligne 13
    - Col A : "(XX) NOM DÉPARTEMENT"
    """
    rows = []
    for ws in wb.worksheets:
        a8 = str(ws["A8"].value or "").upper()
        if "POIDS" in a8:
            base_calcul, type_envoi = "poids", "messagerie"
        elif "PALETTE" in a8:
            base_calcul, type_envoi = "palette", "messagerie"
        else:
            continue

        cols = []
        for c in range(3, ws.max_column + 1):
            tmax = _tarif_float(ws.cell(row=11, column=c).value)
            if tmax is None:
                continue
            tmin = _tarif_float(ws.cell(row=10, column=c).value, default=0)
            unite = _tarif_unite_norm(ws.cell(row=12, column=c).value)
            cols.append((c, tmin, tmax, unite))

        for r in range(13, ws.max_row + 1):
            dept = _tarif_dept_from_label(ws.cell(row=r, column=1).value)
            if not dept:
                continue
            for c, tmin, tmax, unite in cols:
                price = _tarif_float(ws.cell(row=r, column=c).value)
                if price is None:
                    continue
                rows.append(
                    {
                        "type_envoi": type_envoi,
                        "base_calcul": base_calcul,
                        "zone_type": "departement",
                        "zone_valeur": dept,
                        "tranche_min": tmin,
                        "tranche_max": int(tmax) if base_calcul == "palette" else tmax,
                        "prix": round(price, 4),
                        "unite": unite,
                        "mini_perception": None,
                        "source_filename": source_filename,
                    }
                )

    return rows, []


def _parse_ceva_messagerie(ws, source_filename):
    rows = []
    header_row = _tarif_find_header_row(
        ws, ["DÉPARTEMENT", "DEPARTEMENT", "ZONE", "CODE POSTAL", "CP"]
    )
    if header_row is None:
        return rows

    cols = []
    for c in range(2, ws.max_column + 1):
        val = str(ws.cell(row=header_row, column=c).value or "").strip()
        if not val:
            continue
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*[-àaÀ]\s*(\d+(?:[.,]\d+)?)", val)
        if m:
            tmin = _tarif_float(m.group(1), 0)
            tmax = _tarif_float(m.group(2))
            unite = "forfait" if (tmax is not None and tmax <= 100) else "au_100kg"
            cols.append((c, tmin, tmax, unite))

    for r in range(header_row + 1, ws.max_row + 1):
        zone_lbl = str(ws.cell(row=r, column=1).value or "").strip()
        if not zone_lbl:
            continue
        dept = _tarif_dept_from_label(zone_lbl)
        cp_m = re.match(r"^(\d{5})\b", zone_lbl)
        if dept:
            zone_type, zone_valeur = "departement", dept
        elif cp_m:
            zone_type, zone_valeur = "code_postal", cp_m.group(1)
        else:
            continue
        for c, tmin, tmax, unite in cols:
            if tmin is None:
                continue
            price = _tarif_float(ws.cell(row=r, column=c).value)
            if price is None:
                continue
            rows.append(
                {
                    "type_envoi": "messagerie",
                    "base_calcul": "poids",
                    "zone_type": zone_type,
                    "zone_valeur": zone_valeur,
                    "tranche_min": tmin,
                    "tranche_max": tmax,
                    "prix": round(price, 4),
                    "unite": unite,
                    "mini_perception": None,
                    "source_filename": source_filename,
                }
            )
    return rows


def _parse_ceva_palettes(ws, source_filename):
    rows = []
    header_row = _tarif_find_header_row(ws, ["DÉPARTEMENT", "DEPARTEMENT", "ZONE", "PALETTE", "PAL"])
    if header_row is None:
        return rows
    cols = []
    for c in range(2, ws.max_column + 1):
        val = str(ws.cell(row=header_row, column=c).value or "").strip()
        m = re.match(r"^(\d+)\s*(?:palette|pal\.?)?$", val, re.IGNORECASE)
        if m:
            nb = int(m.group(1))
            if 1 <= nb <= 20:
                cols.append((c, nb))
    if not cols:
        cols = [(c, i) for i, c in enumerate(range(2, min(ws.max_column + 1, 7)), start=1)]
    for r in range(header_row + 1, ws.max_row + 1):
        dept = _tarif_dept_from_label(ws.cell(row=r, column=1).value)
        if not dept:
            continue
        for c, nb in cols:
            price = _tarif_float(ws.cell(row=r, column=c).value)
            if price is None:
                continue
            rows.append(
                {
                    "type_envoi": "messagerie",
                    "base_calcul": "palette",
                    "zone_type": "departement",
                    "zone_valeur": dept,
                    "tranche_min": nb,
                    "tranche_max": nb,
                    "prix": round(price, 4),
                    "unite": "forfait",
                    "mini_perception": None,
                    "source_filename": source_filename,
                }
            )
    return rows


def _parse_ceva_frais(ws):
    frais = []
    patterns = [
        (r"gasoil|carburant|fuel", "Gasoil", "pct_transport", 1),
        (r"sûreté|surete|sécurité|securite", "Taxe sûreté/sécurité", "forfait_expedition", 1),
        (r"prise.{0,10}rdv|rendez.{0,5}vous", "Prise de RDV", "forfait_expedition", 0),
        (r"hayon|tail.?lift", "Hayon", "par_palette", 0),
        (r"ville.{0,15}excentr", "Ville excentrée", "forfait_expedition", 0),
        (r"co2|contribution", "CO2", "forfait_expedition", 1),
        (r"centre.{0,10}urbain|urban", "Centres urbains", "forfait_expedition", 0),
    ]
    seen = set()
    for r in range(1, ws.max_row + 1):
        for c in range(1, min(ws.max_column + 1, 10)):
            cell = str(ws.cell(row=r, column=c).value or "").strip()
            if not cell:
                continue
            for pattern, libelle, mode, defaut in patterns:
                if libelle in seen:
                    continue
                if re.search(pattern, cell, re.IGNORECASE):
                    for cc in range(c + 1, min(c + 6, ws.max_column + 1)):
                        val = _tarif_float(ws.cell(row=r, column=cc).value)
                        if val is not None and val > 0:
                            frais.append(
                                {
                                    "libelle": libelle,
                                    "mode": mode,
                                    "valeur": val,
                                    "mini": None,
                                    "applique_defaut": defaut,
                                }
                            )
                            seen.add(libelle)
                            break
                    break
    return frais


def _parse_ceva(wb, source_filename):
    rows = []
    frais = []
    for ws in wb.worksheets:
        t = ws.title.upper().replace(" ", "")
        if "MESSAGERIE" in t or ("TARIF" in t and "GN" in t):
            rows += _parse_ceva_messagerie(ws, source_filename)
        elif "PALETTE" in t or "SMARTPAL" in t or "SMART" in t:
            rows += _parse_ceva_palettes(ws, source_filename)
        elif "CONDITION" in t or "COMMERCIALE" in t or "ANNEXE" in t:
            frais += _parse_ceva_frais(ws)
    return rows, frais


def _parse_transbenelux(wb, source_filename):
    rows = []
    for ws in wb.worksheets:
        header_row = _tarif_find_header_row(ws, ["PALETTE", "PAL", "FRANCE", "DÉPARTEMENT"])
        if header_row is None:
            continue
        cols = []
        for c in range(2, ws.max_column + 1):
            val = str(ws.cell(row=header_row, column=c).value or "").strip()
            m = re.fullmatch(r"(\d{1,2})", val)
            if m:
                nb = int(m.group(1))
                if 1 <= nb <= 20:
                    cols.append((c, nb))
        if not cols:
            continue
        for r in range(header_row + 1, ws.max_row + 1):
            dept = _tarif_dept_from_label(ws.cell(row=r, column=1).value)
            if not dept:
                continue
            for c, nb in cols:
                raw = str(ws.cell(row=r, column=c).value or "").strip().upper()
                if raw in ("", "FO", "PU", "PP", "-", "NC", "N/A"):
                    continue
                price = _tarif_float(raw)
                if price is None or price <= 0:
                    continue
                rows.append(
                    {
                        "type_envoi": "affretement" if nb > 6 else "messagerie",
                        "base_calcul": "palette",
                        "zone_type": "departement",
                        "zone_valeur": dept,
                        "tranche_min": nb,
                        "tranche_max": nb,
                        "prix": round(price, 4),
                        "unite": "forfait",
                        "mini_perception": None,
                        "source_filename": source_filename,
                    }
                )
    return rows, []


@router.post("/transporteurs/{transporteur_id}/tarifs/parse-excel")
async def parse_tarif_excel(request: Request, transporteur_id: int):
    """
    Parser déterministe openpyxl pour grilles tarifaires Excel.
    Ne dépend pas de l'API Anthropic — traite les fichiers volumineux (2000+ lignes).
    Formats reconnus : Compte 100346, CEVA Logistics, TRANSBENELUX, générique.
    """
    user = _require_expe_write(request)

    with get_db() as conn:
        trp = conn.execute(
            "SELECT * FROM expe_transporteurs WHERE id=?", (transporteur_id,)
        ).fetchone()
    if not trp:
        raise HTTPException(status_code=404, detail="Transporteur introuvable")
    if not trp["tarif_url"]:
        raise HTTPException(status_code=400, detail="Aucun fichier tarif uploadé pour ce transporteur")

    filepath = _resolve_tarif_path(trp["tarif_url"])
    if not filepath:
        raise HTTPException(status_code=404, detail="Fichier tarif introuvable sur le disque")

    ext = os.path.splitext(filepath)[1].lower()
    if ext not in (".xlsx", ".xls"):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Ce endpoint ne traite que les fichiers Excel (.xlsx). Fichier reçu : {ext}. "
                "Utilisez le bouton 'Parser avec IA' pour les PDFs."
            ),
        )

    try:
        import openpyxl
    except ImportError:
        raise HTTPException(
            status_code=503, detail="openpyxl non installé — lancer : pip install openpyxl"
        )

    wb = openpyxl.load_workbook(filepath, data_only=True)
    source_name = trp["tarif_filename"] or os.path.basename(trp["tarif_url"])

    fmt = _detect_tarif_format(wb)

    if fmt == "compte100346":
        lignes_data, frais_data = _parse_compte100346(wb, source_name)
    elif fmt == "ceva":
        lignes_data, frais_data = _parse_ceva(wb, source_name)
    elif fmt == "transbenelux":
        lignes_data, frais_data = _parse_transbenelux(wb, source_name)
    else:
        structure = []
        for ws in wb.worksheets:
            preview = []
            for r in range(1, min(6, ws.max_row + 1)):
                row_vals = [
                    str(ws.cell(row=r, column=c).value or "")[:30]
                    for c in range(1, min(ws.max_column + 1, 8))
                ]
                preview.append(row_vals)
            structure.append({"sheet": ws.title, "preview": preview})
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Format non reconnu automatiquement. Voici la structure du fichier.",
                "structure": structure,
                "hint": "Communiquer la structure à l'équipe pour ajouter le support de ce format.",
            },
        )

    if not lignes_data:
        raise HTTPException(
            status_code=422,
            detail=f"Format '{fmt}' détecté mais aucune ligne extraite. Vérifier le fichier.",
        )

    now = datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")
    email = user.get("email") or user.get("identifiant")

    with get_db() as conn:
        for lg in lignes_data:
            conn.execute(
                """INSERT INTO expe_tarifs
                   (transporteur_id, type_envoi, base_calcul, zone_type, zone_valeur,
                    tranche_min, tranche_max, prix, unite, mini_perception,
                    actif, source_filename, created_at, created_by_email)
                   VALUES (?,?,?,?,?,?,?,?,?,?,0,?,?,?)""",
                (
                    transporteur_id,
                    lg.get("type_envoi"),
                    lg.get("base_calcul"),
                    lg.get("zone_type"),
                    lg.get("zone_valeur"),
                    lg.get("tranche_min", 0),
                    lg.get("tranche_max"),
                    lg.get("prix", 0),
                    lg.get("unite"),
                    lg.get("mini_perception"),
                    source_name,
                    now,
                    email,
                ),
            )
        for fr in frais_data:
            conn.execute(
                """INSERT OR IGNORE INTO expe_tarifs_frais
                   (transporteur_id, libelle, mode, valeur, mini, applique_defaut)
                   VALUES (?,?,?,?,?,?)""",
                (
                    transporteur_id,
                    fr.get("libelle"),
                    fr.get("mode"),
                    fr.get("valeur", 0),
                    fr.get("mini"),
                    fr.get("applique_defaut", 1),
                ),
            )
        conn.commit()

    return {
        "format_detecte": fmt,
        "lignes_extraites": len(lignes_data),
        "frais_extraits": len(frais_data),
        "actif": 0,
        "apercu_lignes": lignes_data[:10],
        "message": (
            f"{len(lignes_data)} lignes extraites (format {fmt}) — "
            "à valider avant activation."
        ),
    }


# ─── Comparateur de prix ───────────────────────────────────────────


def _deduire_departement(cp: str) -> str:
    """Déduit le département depuis le code postal (Corse, DOM, cas général)."""
    cp = (cp or "").strip().upper()
    if len(cp) < 2:
        return cp
    if cp.startswith("97") and len(cp) >= 3:
        return cp[:3]
    if cp.startswith("20") and len(cp) == 5 and cp.isdigit():
        num = int(cp)
        return "2A" if num <= 20190 else "2B"
    return cp[:2]


def _trouver_ligne_tarif(
    conn,
    transporteur_id: int,
    type_envoi: str,
    dept: str,
    cp: str,
    poids: float,
    nb_pal: float,
):
    """Cherche la ligne expe_tarifs la plus précise (CP → département, palette → poids)."""
    _MP_PAR_PALETTE = 0.4  # 1 palette 80x120 = 0.4 mètre plancher
    tentatives: list[tuple[str, float]] = []
    if nb_pal > 0:
        tentatives.append(("palette", nb_pal))
        tentatives.append(("metre_plancher", round(nb_pal * _MP_PAR_PALETTE, 4)))
    if poids > 0:
        tentatives.append(("poids", poids))

    zones_par_priorite = [
        ("code_postal", cp),
        ("departement", dept),
    ]

    for base_calcul, valeur_base in tentatives:
        for zone_type, zone_valeur in zones_par_priorite:
            ligne = conn.execute(
                """
                SELECT * FROM expe_tarifs
                WHERE transporteur_id=?
                  AND type_envoi=?
                  AND base_calcul=?
                  AND zone_type=?
                  AND zone_valeur=?
                  AND actif=1
                  AND tranche_min <= ?
                  AND (tranche_max IS NULL OR tranche_max > ?)
                ORDER BY tranche_min DESC
                LIMIT 1
                """,
                (
                    transporteur_id,
                    type_envoi,
                    base_calcul,
                    zone_type,
                    zone_valeur,
                    valeur_base,
                    valeur_base,
                ),
            ).fetchone()
            if ligne:
                return ligne
    return None


_METHODE_TARIF_LIBELLE: dict[str, str] = {
    "poids": "Tarif au poids",
    "palette": "Tarif à la palette",
    "metre_plancher": "Tarif au mètre plancher",
}


def _trouver_toutes_lignes_tarif(
    conn,
    transporteur_id: int,
    type_envoi: str,
    dept: str,
    cp: str,
    poids: float,
    nb_pal: float,
) -> list[sqlite3.Row]:
    """Collecte toutes les lignes expe_tarifs applicables (palette, MP, poids)."""
    _MP_PAR_PALETTE = 0.4
    tentatives: list[tuple[str, float]] = []
    if nb_pal > 0:
        tentatives.append(("palette", nb_pal))
        tentatives.append(("metre_plancher", round(nb_pal * _MP_PAR_PALETTE, 4)))
    if poids > 0:
        tentatives.append(("poids", poids))

    zones_par_priorite = [
        ("code_postal", cp),
        ("departement", dept),
    ]

    result: list[sqlite3.Row] = []
    for base_calcul, valeur_base in tentatives:
        ligne: sqlite3.Row | None = None
        for zone_type, zone_valeur in zones_par_priorite:
            row = conn.execute(
                """
                SELECT * FROM expe_tarifs
                WHERE transporteur_id=?
                  AND type_envoi=?
                  AND base_calcul=?
                  AND zone_type=?
                  AND zone_valeur=?
                  AND actif=1
                  AND tranche_min <= ?
                  AND (tranche_max IS NULL OR tranche_max > ?)
                ORDER BY tranche_min DESC
                LIMIT 1
                """,
                (
                    transporteur_id,
                    type_envoi,
                    base_calcul,
                    zone_type,
                    zone_valeur,
                    valeur_base,
                    valeur_base,
                ),
            ).fetchone()
            if row:
                ligne = row
                break
        if ligne:
            result.append(ligne)
    return result


def _calculer_prix_base(ligne, poids: float, nb_pal: float) -> tuple[float, str]:
    """Calcule le prix de base selon l'unité de la ligne tarifaire."""
    unite = ligne["unite"]
    prix = float(ligne["prix"] or 0)
    mini = float(ligne["mini_perception"] or 0)
    base_calcul = ligne["base_calcul"]

    if unite == "forfait":
        prix_calc = prix
        detail = f"forfait {prix:.2f} €"
    elif unite == "au_100kg":
        ref = poids if base_calcul == "poids" else nb_pal
        prix_calc = prix * ref / 100
        detail = f"{prix:.4f} €/100kg × {ref} = {prix_calc:.2f} €"
    elif unite == "au_kg":
        ref = poids if base_calcul == "poids" else nb_pal
        prix_calc = prix * ref
        detail = f"{prix:.4f} €/kg × {ref} = {prix_calc:.2f} €"
    else:
        prix_calc = prix
        detail = f"{prix:.2f} € (unité inconnue : {unite})"

    if mini and prix_calc < mini:
        detail += f" → mini perception {mini:.2f} €"
        prix_calc = mini

    return prix_calc, detail


def _appliquer_frais(
    conn, transporteur_id: int, prix_base: float, nb_pal: float = 0
) -> tuple[list[dict], float]:
    """Applique les frais par défaut du transporteur."""
    frais_rows = conn.execute(
        """
        SELECT * FROM expe_tarifs_frais
        WHERE transporteur_id=? AND applique_defaut=1
        ORDER BY libelle
        """,
        (transporteur_id,),
    ).fetchall()

    frais_list: list[dict] = []
    total_frais = 0.0

    for fr in frais_rows:
        mode = fr["mode"]
        valeur = float(fr["valeur"] or 0)
        mini_fr = float(fr["mini"] or 0)

        if mode == "pct_transport":
            montant = prix_base * valeur / 100
            if mini_fr and montant < mini_fr:
                montant = mini_fr
            detail = f"{valeur}% du transport = {montant:.2f} €"
        elif mode == "forfait_expedition":
            montant = valeur
            detail = f"forfait {valeur:.2f} €"
        elif mode == "par_palette":
            montant = valeur * nb_pal if nb_pal > 0 else valeur
            detail = (
                f"{valeur:.2f} €/pal × {nb_pal} = {montant:.2f} €"
                if nb_pal > 0
                else f"{valeur:.2f} €"
            )
        else:
            montant = valeur
            detail = f"{valeur:.2f} €"

        frais_list.append(
            {
                "libelle": fr["libelle"],
                "montant": round(montant, 2),
                "detail": detail,
            }
        )
        total_frais += montant

    return frais_list, total_frais


def _calculer_comparateur(
    conn,
    poids: float,
    nb_pal: float,
    dept: str,
    cp: str,
    type_envoi: str,
) -> tuple[list[dict], list[dict]]:
    """Éligibilité et prix pour chaque transporteur actif."""
    transporteurs = conn.execute(
        "SELECT * FROM expe_transporteurs WHERE actif=1"
    ).fetchall()

    eligibles: list[dict] = []
    non_eligibles: list[dict] = []

    zone_col = {
        "messagerie": "zone_messagerie",
        "ramasse": "zone_messagerie",
        "affretement": "zone_affretement",
        "express_intl": "zone_france",
    }.get(type_envoi, "zone_france")

    for trp in transporteurs:
        raisons_ineligibilite: list[str] = []

        if not trp[zone_col]:
            raisons_ineligibilite.append(f"hors zone ({type_envoi})")

        pal_max = trp["palette_max"]
        if pal_max is not None and nb_pal > 0 and nb_pal > float(pal_max):
            raisons_ineligibilite.append(
                f"capacité dépassée ({nb_pal:g} pal. > max {pal_max})"
            )

        if trp["accepte_poids"] == 0 and poids > 0 and nb_pal == 0:
            raisons_ineligibilite.append("n'accepte pas le tarif au poids")
        if trp["accepte_palette"] == 0 and nb_pal > 0:
            raisons_ineligibilite.append("n'accepte pas les palettes")

        lignes = _trouver_toutes_lignes_tarif(
            conn, trp["id"], type_envoi, dept, cp, poids, nb_pal
        )
        if not lignes and not raisons_ineligibilite:
            raisons_ineligibilite.append("aucune grille tarifaire pour ce poids/zone")

        if raisons_ineligibilite:
            non_eligibles.append(
                {
                    "transporteur_id": trp["id"],
                    "transporteur": trp["nom"],
                    "raison": " · ".join(raisons_ineligibilite),
                }
            )
            continue

        for ligne in lignes:
            prix_base, detail = _calculer_prix_base(ligne, poids, nb_pal)
            frais_list, prix_frais = _appliquer_frais(conn, trp["id"], prix_base, nb_pal)
            prix_total = prix_base + prix_frais
            base_calcul = ligne["base_calcul"] or ""

            eligibles.append(
                {
                    "transporteur_id": trp["id"],
                    "transporteur": trp["nom"],
                    "prix_ht": round(prix_total, 2),
                    "prix_base_ht": round(prix_base, 2),
                    "methode_tarification": _METHODE_TARIF_LIBELLE.get(
                        base_calcul, base_calcul
                    ),
                    "detail_calcul": {
                        "base": detail,
                        "frais": frais_list,
                    },
                    "delai_jours": None,
                }
            )

    eligibles.sort(key=lambda x: x["prix_ht"])
    if eligibles:
        eligibles[0]["moins_cher"] = True

    return eligibles, non_eligibles


@router.post("/comparateur")
def comparateur(request: Request, body: dict = Body(...)):
    """Calcule le prix de chaque transporteur éligible pour un envoi."""
    _require_expe(request)

    poids = float(body.get("poids_total_kg") or 0)
    nb_pal = float(body.get("nb_palette") or 0)
    cp = str(body.get("code_postal_destination") or "").strip()
    type_envoi = str(body.get("type_envoi") or "messagerie").strip()

    if not cp:
        raise HTTPException(
            status_code=400, detail="code_postal_destination est obligatoire"
        )
    if not poids and not nb_pal:
        raise HTTPException(
            status_code=400,
            detail="Saisir au moins un poids ou un nombre de palettes",
        )

    dept = _deduire_departement(cp)

    with get_db() as conn:
        eligibles, non_eligibles = _calculer_comparateur(
            conn, poids, nb_pal, dept, cp, type_envoi
        )

    return {
        "departement_deduit": dept,
        "eligibles": eligibles,
        "non_eligibles": non_eligibles,
    }


# ─── Demandes de devis (prospection parallèle) ─────────────────────

EXPE_DEVIS_CC = "expeditions@sifa.pro"


@router.post("/devis/demandes")
def creer_demande_devis(request: Request, body: dict = Body(...)):
    user = _require_expe_write(request)
    now = datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")
    email = (user.get("email") or user.get("identifiant") or "").strip() or None
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO expe_demandes_devis
            (depart_id, poids_total_kg, nb_palette, code_postal_destination,
             type_envoi, contraintes, statut, created_at, created_by_email)
            VALUES (?,?,?,?,?,?,'ouverte',?,?)
            """,
            (
                body.get("depart_id"),
                body.get("poids_total_kg"),
                body.get("nb_palette"),
                (body.get("code_postal_destination") or "").strip(),
                (body.get("type_envoi") or "messagerie").strip(),
                (body.get("contraintes") or "").strip() or None,
                now,
                email,
            ),
        )
        conn.commit()
        demande = conn.execute(
            "SELECT * FROM expe_demandes_devis WHERE id=?", (cur.lastrowid,)
        ).fetchone()
    return dict(demande)


@router.get("/devis/demandes")
def list_demandes_devis(request: Request, statut: str = "ouverte"):
    _require_expe(request)
    with get_db() as conn:
        if statut == "toutes":
            rows = conn.execute(
                "SELECT * FROM expe_demandes_devis ORDER BY created_at DESC LIMIT 100"
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM expe_demandes_devis WHERE statut=?
                   ORDER BY created_at DESC LIMIT 100""",
                (statut,),
            ).fetchall()
        result = []
        for d in rows:
            dd = dict(d)
            counts = conn.execute(
                """
                SELECT
                  SUM(CASE WHEN statut IN ('envoyee','ouvert','recue','retenue','refusee')
                      THEN 1 ELSE 0 END) AS envoyes,
                  SUM(CASE WHEN statut IN ('recue','retenue') THEN 1 ELSE 0 END) AS recues,
                  SUM(CASE WHEN statut='retenue' THEN 1 ELSE 0 END) AS retenues
                FROM expe_devis_reponses WHERE demande_id=?
                """,
                (dd["id"],),
            ).fetchone()
            dd["nb_envoyes"] = counts["envoyes"] or 0
            dd["nb_recus"] = counts["recues"] or 0
            dd["nb_retenus"] = counts["retenues"] or 0
            result.append(dd)
    return result


@router.get("/devis/demandes/{demande_id}")
def get_demande_devis(request: Request, demande_id: int):
    _require_expe(request)
    with get_db() as conn:
        demande = conn.execute(
            "SELECT * FROM expe_demandes_devis WHERE id=?", (demande_id,)
        ).fetchone()
        if not demande:
            raise HTTPException(status_code=404, detail="Demande introuvable")
        reponses = conn.execute(
            """SELECT * FROM expe_devis_reponses WHERE demande_id=?
               ORDER BY sent_at""",
            (demande_id,),
        ).fetchall()
    return {"demande": dict(demande), "reponses": [dict(r) for r in reponses]}


@router.post("/devis/demandes/{demande_id}/envoyer")
def envoyer_rfq(request: Request, demande_id: int, body: dict = Body(...)):
    user = _require_expe_write(request)
    now = datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")
    reply_to = (user.get("email") or user.get("identifiant") or "").strip() or None

    with get_db() as conn:
        demande_row = conn.execute(
            "SELECT * FROM expe_demandes_devis WHERE id=?", (demande_id,)
        ).fetchone()
        if not demande_row:
            raise HTTPException(status_code=404, detail="Demande introuvable")
        demande = dict(demande_row)

        destinataires: list[dict] = []
        trp_ids = body.get("transporteur_ids") or []
        if trp_ids:
            placeholders = ",".join("?" * len(trp_ids))
            trps = conn.execute(
                f"""SELECT id, nom, contact_email FROM expe_transporteurs
                    WHERE id IN ({placeholders}) AND actif=1""",
                trp_ids,
            ).fetchall()
            for t in trps:
                email_addr = (t["contact_email"] or "").strip()
                if email_addr and "@" in email_addr:
                    destinataires.append(
                        {
                            "transporteur_id": t["id"],
                            "nom": t["nom"],
                            "email": email_addr,
                        }
                    )

        for extra in body.get("transporteur_extras") or []:
            email_addr = (extra.get("email") or "").strip()
            if email_addr and "@" in email_addr:
                destinataires.append(
                    {
                        "transporteur_id": None,
                        "nom": extra.get("nom") or email_addr,
                        "email": email_addr,
                    }
                )

        if not destinataires:
            raise HTTPException(
                status_code=400,
                detail="Aucun destinataire valide — vérifier les emails des transporteurs",
            )

        envois_ok: list[str] = []
        envois_ko: list[str] = []
        for dest in destinataires:
            import uuid as _uuid

            email_norm = (dest.get("email") or "").strip().lower()
            token_row = conn.execute(
                "SELECT token FROM expe_portal_transporteurs WHERE LOWER(email)=LOWER(?) AND actif=1 LIMIT 1",
                (email_norm,),
            ).fetchone()
            if token_row and token_row["token"]:
                token = str(token_row["token"])
            else:
                token = str(_uuid.uuid4())
                conn.execute(
                    """
                    INSERT OR IGNORE INTO expe_portal_transporteurs
                    (email, token, transporteur_id, prospect_id, created_at, actif)
                    VALUES (?,?,?,?,?,1)
                    """,
                    (
                        email_norm,
                        token,
                        dest.get("transporteur_id"),
                        None,
                        now,
                    ),
                )
                row2 = conn.execute(
                    "SELECT token FROM expe_portal_transporteurs WHERE LOWER(email)=LOWER(?) AND actif=1 LIMIT 1",
                    (email_norm,),
                ).fetchone()
                if row2 and row2["token"]:
                    token = str(row2["token"])
            portail_lien = f"{public_base_url()}/portail/expe/{token}"
            sujet, corps_html = email_expe_rfq_transport(
                demande=demande, user=user, portail_lien=portail_lien
            )

            ok = send_email(
                to=dest["email"],
                subject=sujet,
                html_body=corps_html,
                reply_to=reply_to,
                cc=EXPE_DEVIS_CC,
            )
            statut_envoi = "envoyee" if ok else "echec"
            existing = conn.execute(
                """
                SELECT id, statut, prix FROM expe_devis_reponses
                WHERE demande_id=?
                  AND LOWER(TRIM(COALESCE(destinataire_email,''))) = LOWER(TRIM(COALESCE(?,'')))
                ORDER BY id DESC
                LIMIT 1
                """,
                (demande_id, email_norm),
            ).fetchone()
            if existing:
                keep_statut = existing["statut"]
                if keep_statut not in ("recue", "retenue"):
                    keep_statut = statut_envoi
                conn.execute(
                    """
                    UPDATE expe_devis_reponses
                    SET transporteur_id=?, nom_transporteur=?, statut=?,
                        sent_at=CASE WHEN ? IS NOT NULL THEN ? ELSE sent_at END,
                        destinataire_email=?
                    WHERE id=?
                    """,
                    (
                        dest["transporteur_id"],
                        dest["nom"],
                        keep_statut,
                        now if ok else None,
                        now if ok else None,
                        email_norm,
                        int(existing["id"]),
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO expe_devis_reponses
                    (demande_id, transporteur_id, nom_transporteur, statut, sent_at, destinataire_email)
                    VALUES (?,?,?,?,?,?)
                    """,
                    (
                        demande_id,
                        dest["transporteur_id"],
                        dest["nom"],
                        statut_envoi,
                        now if ok else None,
                        email_norm,
                    ),
                )
            if ok:
                envois_ok.append(dest["nom"])
            else:
                envois_ko.append(dest["nom"])
        conn.commit()

    return {
        "envoyes": len(envois_ok),
        "echecs": len(envois_ko),
        "destinataires_ok": envois_ok,
        "destinataires_ko": envois_ko,
    }


@router.put("/devis/reponses/{reponse_id}")
def saisir_reponse_devis(request: Request, reponse_id: int, body: dict = Body(...)):
    _require_expe_write(request)
    now = datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")
    with get_db() as conn:
        rep = conn.execute(
            "SELECT * FROM expe_devis_reponses WHERE id=?", (reponse_id,)
        ).fetchone()
        if not rep:
            raise HTTPException(status_code=404, detail="Réponse introuvable")
        conn.execute(
            """
            UPDATE expe_devis_reponses
            SET prix=?, delai_jours=?, commentaire=?, statut='recue', recu_at=?
            WHERE id=?
            """,
            (
                body.get("prix"),
                body.get("delai_jours"),
                (body.get("commentaire") or "").strip() or None,
                now,
                reponse_id,
            ),
        )
        conn.commit()
        updated = conn.execute(
            "SELECT * FROM expe_devis_reponses WHERE id=?", (reponse_id,)
        ).fetchone()
    return dict(updated)


@router.post("/devis/reponses/{reponse_id}/retenir")
def retenir_reponse_devis(request: Request, reponse_id: int):
    _require_expe_write(request)
    with get_db() as conn:
        rep = conn.execute(
            "SELECT * FROM expe_devis_reponses WHERE id=?", (reponse_id,)
        ).fetchone()
        if not rep:
            raise HTTPException(status_code=404, detail="Réponse introuvable")
        demande_id = rep["demande_id"]
        conn.execute(
            """
            UPDATE expe_devis_reponses SET statut='refusee'
            WHERE demande_id=? AND id!=? AND statut NOT IN ('retenue','refusee')
            """,
            (demande_id, reponse_id),
        )
        conn.execute(
            "UPDATE expe_devis_reponses SET statut='retenue' WHERE id=?",
            (reponse_id,),
        )
        conn.execute(
            "UPDATE expe_demandes_devis SET statut='cloturee' WHERE id=?",
            (demande_id,),
        )
        conn.commit()
    return {"statut": "cloturee", "retenu": reponse_id}


@router.delete("/devis/demandes/{demande_id}")
def supprimer_demande_devis(request: Request, demande_id: int):
    _require_expe_write(request)
    with get_db() as conn:
        if not conn.execute(
            "SELECT 1 FROM expe_demandes_devis WHERE id=?", (demande_id,)
        ).fetchone():
            raise HTTPException(status_code=404, detail="Demande introuvable")
        conn.execute("DELETE FROM expe_devis_reponses WHERE demande_id=?", (demande_id,))
        conn.execute("DELETE FROM expe_demandes_devis WHERE id=?", (demande_id,))
        conn.commit()
    return {"deleted": demande_id}


# ─── Prospects transporteurs ───────────────────────────────────────


@router.get("/prospects")
def list_prospects(request: Request):
    _require_expe(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM expe_transporteurs_prospects
               ORDER BY statut_demarchage, nom"""
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("/prospects")
def creer_prospect(request: Request, body: dict = Body(...)):
    _require_expe_write(request)
    nom = (body.get("nom") or "").strip()
    if not nom:
        raise HTTPException(status_code=400, detail="Nom obligatoire")
    now = datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO expe_transporteurs_prospects
            (nom, contact_nom, contact_email, contact_tel, zone_couverte,
             type_service, capacite_max_pal, statut_demarchage, notes, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                nom,
                (body.get("contact_nom") or "").strip() or None,
                (body.get("contact_email") or "").strip() or None,
                (body.get("contact_tel") or "").strip() or None,
                (body.get("zone_couverte") or "").strip() or None,
                (body.get("type_service") or "messagerie").strip(),
                body.get("capacite_max_pal"),
                (body.get("statut_demarchage") or "a_contacter").strip(),
                (body.get("notes") or "").strip() or None,
                now,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM expe_transporteurs_prospects WHERE id=?", (cur.lastrowid,)
        ).fetchone()
    return dict(row)


@router.put("/prospects/{prospect_id}")
def modifier_prospect(request: Request, prospect_id: int, body: dict = Body(...)):
    _require_expe_write(request)
    now = datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")
    champs = [
        "nom",
        "contact_nom",
        "contact_email",
        "contact_tel",
        "zone_couverte",
        "type_service",
        "capacite_max_pal",
        "statut_demarchage",
        "notes",
    ]
    sets = ["updated_at=?"]
    args: list[Any] = [now]
    for c in champs:
        if c in body:
            sets.append(f"{c}=?")
            v = body[c]
            if c == "nom":
                v = (v or "").strip()
            elif isinstance(v, str):
                v = v.strip() or None
            args.append(v)
    args.append(prospect_id)
    with get_db() as conn:
        conn.execute(
            f"UPDATE expe_transporteurs_prospects SET {', '.join(sets)} WHERE id=?",
            args,
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM expe_transporteurs_prospects WHERE id=?", (prospect_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Prospect introuvable")
    return dict(row)


@router.delete("/prospects/{prospect_id}")
def supprimer_prospect(request: Request, prospect_id: int):
    _require_expe_write(request)
    with get_db() as conn:
        conn.execute(
            "DELETE FROM expe_transporteurs_prospects WHERE id=?", (prospect_id,)
        )
        conn.commit()
    return {"deleted": prospect_id}


# ─── Délais carte France ───────────────────────────────────────────

_DELAIS_EDIT_ROLES = {"superadmin", "direction", "administration", "expedition"}


def _delai_jours_from_texte(delai_texte: str) -> int:
    try:
        return int(str(delai_texte).replace("J+", "").strip())
    except (ValueError, AttributeError):
        return 2


@router.get("/delais")
def get_delais(request: Request, type_envoi: str = "default"):
    _require_expe(request)
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT departement, delai_texte, zone_label
            FROM expe_delais
            WHERE type_envoi=? AND transporteur_id IS NULL
            """,
            (type_envoi,),
        ).fetchall()

        if not rows and type_envoi != "default":
            rows = conn.execute(
                """
                SELECT departement, delai_texte, zone_label
                FROM expe_delais
                WHERE type_envoi='default' AND transporteur_id IS NULL
                """
            ).fetchall()

    from app.web.expe_france_delais_data import DELAIS_FRANCE_DEFAULT

    result: dict[str, dict] = {}
    for r in rows:
        dept = r["departement"]
        default_label = DELAIS_FRANCE_DEFAULT.get(dept, {}).get("label", dept)
        result[dept] = {
            "delai": r["delai_texte"],
            "zone": r["zone_label"],
            "label": default_label,
        }
    return result


@router.put("/delais")
def save_delais(request: Request, body: dict = Body(...)):
    user = _require_expe_write(request)
    role = (user.get("role") or "").strip()
    if role not in _DELAIS_EDIT_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Accès refusé — rôle insuffisant pour modifier les délais",
        )

    overrides = body.get("overrides") or {}
    if not overrides:
        raise HTTPException(status_code=400, detail="overrides est vide")

    now = datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")
    type_envoi = (body.get("type_envoi") or "default").strip()
    email = (user.get("email") or user.get("identifiant") or "").strip() or None

    with get_db() as conn:
        for dept, data in overrides.items():
            delai_texte = str(data.get("delai") or "J+2").strip()
            zone_label = str(data.get("zone") or "france").strip()
            delai_jours = _delai_jours_from_texte(delai_texte)
            conn.execute(
                """
                DELETE FROM expe_delais
                WHERE departement=? AND type_envoi=? AND transporteur_id IS NULL
                """,
                (dept, type_envoi),
            )
            conn.execute(
                """
                INSERT INTO expe_delais
                (departement, type_envoi, transporteur_id, delai_jours, zone_label,
                 delai_texte, updated_at, updated_by_email)
                VALUES (?, ?, NULL, ?, ?, ?, ?, ?)
                """,
                (dept, type_envoi, delai_jours, zone_label, delai_texte, now, email),
            )
        conn.commit()

    return {"updated": len(overrides)}


@router.post("/delais/reset")
def reset_delais(request: Request, body: dict = Body(default_factory=dict)):
    user = _require_expe_write(request)
    role = (user.get("role") or "").strip()
    if role not in _DELAIS_EDIT_ROLES:
        raise HTTPException(status_code=403, detail="Accès refusé")

    type_envoi = (body.get("type_envoi") or "default").strip()
    now = datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")
    email = (user.get("email") or user.get("identifiant") or "").strip() or None

    from app.web.expe_france_delais_data import DELAIS_FRANCE_DEFAULT

    with get_db() as conn:
        conn.execute(
            "DELETE FROM expe_delais WHERE type_envoi=? AND transporteur_id IS NULL",
            (type_envoi,),
        )
        for dept, data in DELAIS_FRANCE_DEFAULT.items():
            delai_texte = data.get("delai", "J+2")
            zone_label = data.get("zone", "france")
            delai_jours = _delai_jours_from_texte(str(delai_texte))
            conn.execute(
                """
                INSERT INTO expe_delais
                (departement, type_envoi, transporteur_id, delai_jours, zone_label,
                 delai_texte, updated_at, updated_by_email)
                VALUES (?, ?, NULL, ?, ?, ?, ?, ?)
                """,
                (dept, type_envoi, delai_jours, zone_label, delai_texte, now, email),
            )
        conn.commit()

    return {"reset": True, "type_envoi": type_envoi}

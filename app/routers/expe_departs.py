"""
MyExpé — suivi des départs (exportations).
Accès : utilisateurs avec droit application « expe ».
"""
import os
import re
import shutil
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
        d.get("nb_palette"),
        d.get("poids_total_kg"),
        d.get("date_livraison"),
        d.get("created_by_email"),
        d.get("validated_by_email"),
        d.get("validated_at"),
    ]
    return _norm_search(" ".join(str(p) for p in parts if p is not None and str(p) != ""))


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


@router.get("/departs/jour")
def list_departs_jour(
    request: Request,
    date: Optional[str] = Query(None, description="YYYY-MM-DD (défaut : jour Paris)"),
):
    _require_expe(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM expe_departs
               WHERE statut = 'en_attente'
               ORDER BY date_enlevement ASC, id ASC""",
        ).fetchall()
    return [dict(r) for r in rows]


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
        cur = conn.execute(
            """INSERT INTO expe_departs (
                date_enlevement, affreteurs, transporteur, client, code_postal_destination,
                ref_sifa, arc, no_cde_transport, no_bl, nb_palette, poids_total_kg, date_livraison,
                statut, created_at, created_by_email
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?, 'en_attente', ?, ?)""",
            (
                date_enl,
                _f("affreteurs"),
                _f("transporteur"),
                _f("client"),
                _f("code_postal_destination"),
                _f("ref_sifa"),
                _f("arc"),
                _f("no_cde_transport"),
                _f("no_bl"),
                _float_opt("nb_palette"),
                _float_opt("poids_total_kg"),
                _f("date_livraison"),
                now,
                email,
            ),
        )
        conn.commit()
        rid = cur.lastrowid
        row = conn.execute("SELECT * FROM expe_departs WHERE id=?", (rid,)).fetchone()
    client_nom = (body.get("client") or "").strip() or "—"
    log_action(
        user=user,
        action="CREATE",
        module="expe",
        objet=f"Départ {client_nom} · {date_enl}",
        ip=request.client.host if request.client else None,
    )
    return dict(row)


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
        out = conn.execute("SELECT * FROM expe_departs WHERE id=?", (depart_id,)).fetchone()
    client_nom = (out["client"] or "").strip() if out else "—"
    log_action(
        user=user,
        action="VALIDATE",
        module="expe",
        objet=f"Départ #{depart_id} validé · {client_nom}",
        ip=request.client.host if request.client else None,
    )
    return dict(out)


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

    fields_num = ["nb_palette", "poids_total_kg"]
    for k in fields_num:
        if k in body:
            sets.append(f"{k}=?")
            args.append(_float_opt(k))

    if not sets:
        raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour")

    with get_db() as conn:
        ex = conn.execute("SELECT id, statut FROM expe_departs WHERE id=?", (depart_id,)).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Départ introuvable")
        if ex["statut"] not in ("en_attente", "valide"):
            raise HTTPException(status_code=409, detail="Modification impossible : départ annulé")

        conn.execute(f"UPDATE expe_departs SET {', '.join(sets)} WHERE id=?", (*args, depart_id))
        conn.commit()
        row = conn.execute("SELECT * FROM expe_departs WHERE id=?", (depart_id,)).fetchone()
    client_nom = (row["client"] or "").strip() if row else "—"
    log_action(
        user=user,
        action="UPDATE",
        module="expe",
        objet=f"Départ #{depart_id} · {client_nom}",
        ip=request.client.host if request.client else None,
    )
    return dict(row)


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
    limit: int = Query(500, ge=1, le=2000),
):
    _require_expe(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM expe_departs
               WHERE statut = 'valide'
               ORDER BY datetime(COALESCE(validated_at, created_at)) DESC, id DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
    data = [dict(r) for r in rows]
    qt = _norm_search(q)
    if not qt:
        return data
    tokens = [t for t in qt.split(" ") if t]
    if not tokens:
        return data
    out = []
    for d in data:
        blob = _row_blob(d)
        if all(tok in blob for tok in tokens):
            out.append(d)
    return out


# ─── Transporteurs ───────────────────────────────────────────────────


@router.get("/transporteurs")
def list_transporteurs(request: Request):
    _require_expe(request)
    with get_db() as conn:
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
                actif, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
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
    ):
        if k in body:
            sets.append(f"{k}=?")
            args.append(_int_flag(body, k, 0))

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

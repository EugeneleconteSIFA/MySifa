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
                date_enlevement, affreteurs, transporteur, transporteur_id, client,
                code_postal_destination,
                ref_sifa, arc, no_cde_transport, no_bl, nb_palette, poids_total_kg, date_livraison,
                statut, created_at, created_by_email
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?, 'en_attente', ?, ?)""",
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

    if "transporteur_id" in body:
        sets.append("transporteur_id=?")
        args.append(_int_opt(body, "transporteur_id"))

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

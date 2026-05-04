"""
MyExpé — suivi des départs (exportations).
Accès : utilisateurs avec droit application « expe ».
"""
import re
import unicodedata
from datetime import datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Body, HTTPException, Query, Request

from database import get_db
from services.auth_service import get_current_user, user_has_app_access

router = APIRouter()

_PARIS = ZoneInfo("Europe/Paris")


def _require_expe(request: Request) -> dict:
    user = get_current_user(request)
    if not user_has_app_access(user, "expe"):
        raise HTTPException(status_code=403, detail="Accès MyExpé requis")
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


@router.get("/departs/jour")
def list_departs_jour(
    request: Request,
    date: Optional[str] = Query(None, description="YYYY-MM-DD (défaut : jour Paris)"),
):
    _require_expe(request)
    day = _date_prefix(date) if date else _today_paris_iso()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", day):
        raise HTTPException(status_code=400, detail="Paramètre date invalide (attendu YYYY-MM-DD)")
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM expe_departs
               WHERE statut = 'en_attente'
                 AND substr(date_enlevement, 1, 10) = ?
               ORDER BY date_enlevement ASC, id ASC""",
            (day,),
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("/departs")
def create_depart(request: Request, body: dict = Body(...)):
    user = _require_expe(request)
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
    return dict(row)


@router.post("/departs/{depart_id}/valider")
def valider_depart(request: Request, depart_id: int):
    user = _require_expe(request)
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
    return dict(out)


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

"""MySifa — Post-its draggables (portail + pages applicatives si multi-page).

Le contenu d'un post-it est une suite de blocs (prise de notes libre, menu « / »
côté page) rangée en JSON dans `postits.contenu`. Chaque enregistrement réécrit
la liste entière : un post-it est petit, et un seul utilisateur l'édite.
"""

import json
import re

from fastapi import APIRouter, HTTPException, Request

from database import get_db
from services.auth_service import get_current_user

router = APIRouter(tags=["postits"])

_POSTIT_COLS = "id, user_id, type, title, pos_x, pos_y, width, multi_page, hidden, color, contenu, created_at"
_POSTIT_DEFAULT_COLORS = {"today": "#22d3ee", "someday": "#fbbf24"}
_COLOR_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

# Format d'édition (pas un référentiel métier) : les types que l'éditeur sait
# afficher. Un type inconnu est refusé plutôt que perdu en silence.
BLOC_TYPES = ("p", "h1", "h2", "h3", "todo", "puce", "num", "citation", "encadre", "code", "sep")
BLOCS_MAX = 400
BLOC_TEXTE_MAX = 4000
BLOC_RETRAIT_MAX = 3


def _bloc_propre(b: dict) -> dict:
    t = str(b.get("type") or "p")
    texte = "" if t == "sep" else str(b.get("texte") if b.get("texte") is not None else "")
    try:
        retrait = max(0, min(BLOC_RETRAIT_MAX, int(b.get("retrait") or 0)))
    except (TypeError, ValueError):
        retrait = 0
    out = {"type": t, "texte": texte}
    if retrait:
        out["retrait"] = retrait
    if t == "todo":
        out["coche"] = bool(b.get("coche"))
    return out


def normaliser_blocs(valeur) -> list[dict]:
    """Contrôle une liste de blocs reçue de la page. Lève 400 si elle est invalide."""
    if not isinstance(valeur, list):
        raise HTTPException(400, "Contenu invalide — liste de blocs attendue.")
    if len(valeur) > BLOCS_MAX:
        raise HTTPException(400, f"Post-it trop long — {BLOCS_MAX} blocs au plus.")
    out = []
    for b in valeur:
        if not isinstance(b, dict):
            raise HTTPException(400, "Contenu invalide — bloc mal formé.")
        t = str(b.get("type") or "p")
        if t not in BLOC_TYPES:
            raise HTTPException(400, f"Type de bloc inconnu : {t}.")
        propre = _bloc_propre(b)
        if len(propre["texte"]) > BLOC_TEXTE_MAX:
            raise HTTPException(400, f"Bloc trop long — {BLOC_TEXTE_MAX} caractères au plus.")
        out.append(propre)
    return out


def lire_blocs(brut) -> list[dict]:
    """Contenu stocké → blocs. Tolérant : un contenu illisible donne un post-it vide."""
    try:
        data = json.loads(brut) if brut else []
    except (TypeError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    return [_bloc_propre(b) for b in data if isinstance(b, dict) and str(b.get("type") or "p") in BLOC_TYPES]


def _sortie(row) -> dict:
    p = dict(row)
    p["blocs"] = lire_blocs(p.pop("contenu", None))
    return p


def _default_postit_color(ptype: str) -> str:
    return _POSTIT_DEFAULT_COLORS.get(ptype, "#22d3ee")


def _normalize_postit_color(value, ptype: str | None = None) -> str:
    if value is None or (isinstance(value, str) and not str(value).strip()):
        if ptype in _POSTIT_DEFAULT_COLORS:
            return _default_postit_color(ptype)
        raise HTTPException(400, "Couleur invalide — format #RRGGBB")
    s = str(value).strip()
    if not _COLOR_HEX_RE.match(s):
        raise HTTPException(400, "Couleur invalide — format #RRGGBB")
    return s.lower()


def _user_id(request: Request) -> int:
    return int(get_current_user(request)["id"])


def _get_postit_or_404(conn, postit_id: int, user_id: int) -> dict:
    row = conn.execute(
        f"SELECT {_POSTIT_COLS} FROM postits WHERE id=? AND user_id=?",
        (postit_id, user_id),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Post-it introuvable")
    return dict(row)


@router.get("/api/postits")
def list_postits(request: Request):
    user_id = _user_id(request)
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT {_POSTIT_COLS} FROM postits WHERE user_id=? ORDER BY id",
            (user_id,),
        ).fetchall()
    return [_sortie(r) for r in rows]


@router.post("/api/postits")
async def create_postit(request: Request):
    user_id = _user_id(request)
    body = await request.json()
    ptype = str(body.get("type") or "").strip()
    title = str(body.get("title") or "").strip()
    if ptype not in ("today", "someday"):
        raise HTTPException(400, "Type invalide — today ou someday")
    if not title:
        raise HTTPException(400, "Titre obligatoire")
    color = _normalize_postit_color(body.get("color"), ptype)
    blocs = normaliser_blocs(body.get("blocs") or [])
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO postits (user_id, type, title, color, contenu) VALUES (?,?,?,?,?)",
            (user_id, ptype, title, color, json.dumps(blocs, ensure_ascii=False)),
        )
        pid = cur.lastrowid
        row = conn.execute(
            f"SELECT {_POSTIT_COLS} FROM postits WHERE id=?",
            (pid,),
        ).fetchone()
        conn.commit()
    return _sortie(row)


@router.delete("/api/postits/{postit_id}")
def delete_postit(postit_id: int, request: Request):
    user_id = _user_id(request)
    with get_db() as conn:
        _get_postit_or_404(conn, postit_id, user_id)
        conn.execute("DELETE FROM postits WHERE id=?", (postit_id,))
        conn.commit()
    return {"ok": True}


@router.patch("/api/postits/{postit_id}")
async def patch_postit(postit_id: int, request: Request):
    user_id = _user_id(request)
    body = await request.json()
    updates = []
    params = []
    if "title" in body:
        title = str(body.get("title") or "").strip()
        if not title:
            raise HTTPException(400, "Titre obligatoire")
        updates.append("title=?")
        params.append(title)
    if "multi_page" in body:
        updates.append("multi_page=?")
        params.append(1 if body.get("multi_page") else 0)
    if "hidden" in body:
        updates.append("hidden=?")
        params.append(1 if body.get("hidden") else 0)
    if "color" in body:
        updates.append("color=?")
        params.append(_normalize_postit_color(body.get("color")))
    if "blocs" in body:
        updates.append("contenu=?")
        params.append(json.dumps(normaliser_blocs(body.get("blocs")), ensure_ascii=False))
    if not updates:
        raise HTTPException(400, "Aucune modification")
    with get_db() as conn:
        _get_postit_or_404(conn, postit_id, user_id)
        params.append(postit_id)
        conn.execute(
            f"UPDATE postits SET {', '.join(updates)} WHERE id=?",
            params,
        )
        row = conn.execute(
            f"SELECT {_POSTIT_COLS} FROM postits WHERE id=?",
            (postit_id,),
        ).fetchone()
        conn.commit()
    out = _sortie(row)
    out["ok"] = True
    return out


@router.patch("/api/postits/{postit_id}/pos")
async def update_postit_pos(postit_id: int, request: Request):
    user_id = _user_id(request)
    body = await request.json()
    try:
        x = int(body.get("x", 0))
        y = int(body.get("y", 0))
    except (TypeError, ValueError):
        raise HTTPException(400, "Position invalide")
    with get_db() as conn:
        _get_postit_or_404(conn, postit_id, user_id)
        conn.execute("UPDATE postits SET pos_x=?, pos_y=? WHERE id=?", (x, y, postit_id))
        conn.commit()
    return {"ok": True}


@router.post("/api/postits/{postit_id}/tasks")
async def add_task(postit_id: int, request: Request):
    """Ajoute une case à cocher en fin de post-it (action de l'assistant IA)."""
    user_id = _user_id(request)
    body = await request.json()
    text = str(body.get("text") if body.get("text") is not None else "")
    with get_db() as conn:
        p = _get_postit_or_404(conn, postit_id, user_id)
        blocs = lire_blocs(p.get("contenu"))
        bloc = {"type": "todo", "texte": text, "coche": False}
        blocs.append(bloc)
        blocs = normaliser_blocs(blocs)
        conn.execute(
            "UPDATE postits SET contenu=? WHERE id=?",
            (json.dumps(blocs, ensure_ascii=False), postit_id),
        )
        conn.commit()
    return {"ok": True, "bloc": blocs[-1], "index": len(blocs) - 1}

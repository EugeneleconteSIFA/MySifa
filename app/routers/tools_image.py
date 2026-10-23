"""MyTools › Image et BAT — projets enregistrés.

Prefix /api/tools/image, session MySifa. Un projet n'est visible que de son
auteur : tout autre utilisateur reçoit 404, comme pour un projet inexistant.

  GET    /projets                    mes projets (sans les réglages)
  POST   /projets                    création (multipart : fichier, vignette, donnees JSON)
  GET    /projets/{id}               détail et réglages
  PUT    /projets/{id}               « Enregistrer » : écrase réglages, vignette, et
                                     l'image d'origine si un fichier est joint
  PATCH  /projets/{id}               renommer
  POST   /projets/{id}/dupliquer     copie (fichiers recopiés)
  DELETE /projets/{id}
  GET    /projets/{id}/fichier       image d'origine (pièce jointe)
  GET    /projets/{id}/vignette      vignette (pièce jointe)

Fichiers sous TOOLS_IMAGE_DIR (hors de UPLOADS_ROOT, jamais servis tels
quels). Le type est lu dans les premiers octets, jamais dans l'en-tête envoyé
par le navigateur. Toute écriture journalise explicitement (log_action).
"""
from __future__ import annotations

import json
import os
import unicodedata
import uuid
from datetime import datetime
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Body, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response

from app.core.database import get_db
from app.services.audit_service import log_action
from app.services.auth_service import get_current_user
from config import (
    TOOLS_IMAGE_DIR,
    TOOLS_IMAGE_PROJETS_MAX,
    TOOLS_IMAGE_TAILLE_MAX_MO,
    TOOLS_IMAGE_VIGNETTE_MAX_KO,
)

router = APIRouter(prefix="/api/tools/image", tags=["tools_image"])

MODES = ("ameliorer", "vectoriser")
NOM_MAX = 120
REGLAGES_MAX_OCTETS = 20000
# Types admis, reconnus à leur signature : (mime, extension).
_EXT = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/gif": "gif", "image/bmp": "bmp"}


def type_image(octets: bytes) -> Optional[str]:
    """Type d'image d'après la signature du fichier, ou None."""
    if octets.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if octets.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(octets) >= 12 and octets[:4] == b"RIFF" and octets[8:12] == b"WEBP":
        return "image/webp"
    if octets[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if octets[:2] == b"BM" and len(octets) > 26:
        return "image/bmp"
    return None


def _maintenant() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _uid(user: dict) -> int:
    return int(user.get("id") or 0)


def _chemin(nom: str) -> str:
    base = os.path.basename(nom or "")
    if not base or base != nom or "." not in base or base.startswith("."):
        raise HTTPException(status_code=404, detail="Fichier introuvable.")
    return os.path.join(TOOLS_IMAGE_DIR, base)


def _ecrire(octets: bytes, mime: str) -> str:
    os.makedirs(TOOLS_IMAGE_DIR, exist_ok=True)
    nom = uuid.uuid4().hex + "." + _EXT[mime]
    with open(os.path.join(TOOLS_IMAGE_DIR, nom), "wb") as f:
        f.write(octets)
    return nom


def _lire(nom: str) -> bytes:
    p = _chemin(nom)
    if not os.path.isfile(p):
        raise HTTPException(status_code=404, detail="Fichier introuvable.")
    with open(p, "rb") as f:
        return f.read()


def _effacer(nom: Optional[str]) -> None:
    if not nom:
        return
    try:
        os.remove(_chemin(nom))
    except Exception:
        pass


def _nom_propre(v, defaut: str = "") -> str:
    s = " ".join(str(v or "").split())[:NOM_MAX]
    return s or defaut


def _reglages(brut) -> tuple[str, str]:
    """Valide les réglages envoyés : (mode, JSON compact)."""
    if not isinstance(brut, dict):
        raise HTTPException(status_code=400, detail="Réglages illisibles.")
    mode = brut.get("mode") if brut.get("mode") in MODES else "ameliorer"
    for cle in ("r", "v"):
        if cle in brut and not isinstance(brut[cle], dict):
            raise HTTPException(status_code=400, detail="Réglages illisibles.")
    garde = {k: brut[k] for k in ("mode", "r", "v", "comparaison") if k in brut}
    garde["mode"] = mode
    texte = json.dumps(garde, ensure_ascii=False, separators=(",", ":"))
    if len(texte.encode("utf-8")) > REGLAGES_MAX_OCTETS:
        raise HTTPException(status_code=413, detail="Réglages trop volumineux.")
    return mode, texte


def _donnees(texte: str) -> dict:
    try:
        d = json.loads(texte or "{}")
    except ValueError:
        d = None
    if not isinstance(d, dict):
        raise HTTPException(status_code=400, detail="Données du projet illisibles.")
    return d


async def _image_jointe(f: Optional[UploadFile], max_octets: int, quoi: str) -> Optional[tuple[bytes, str]]:
    if f is None:
        return None
    octets = await f.read(max_octets + 1)
    if len(octets) > max_octets:
        lim = f"{max_octets // (1024 * 1024)} Mo" if max_octets >= 1024 * 1024 else f"{max_octets // 1024} Ko"
        raise HTTPException(status_code=413, detail=f"{quoi} trop volumineuse — {lim} au plus.")
    if not octets:
        raise HTTPException(status_code=400, detail=f"{quoi} vide.")
    mime = type_image(octets)
    if not mime:
        raise HTTPException(status_code=415, detail=f"{quoi} refusée — PNG, JPG, WebP, GIF ou BMP attendu.")
    return octets, mime


def _max_fichier() -> int:
    return TOOLS_IMAGE_TAILLE_MAX_MO * 1024 * 1024


def _max_vignette() -> int:
    return TOOLS_IMAGE_VIGNETTE_MAX_KO * 1024


def _projet(conn, pid: int, user: dict) -> dict:
    r = conn.execute("SELECT * FROM tools_image_projets WHERE id = ?", (pid,)).fetchone()
    # Le projet d'un autre est introuvable, pas interdit : on ne dit pas qu'il existe.
    if not r or int(r["user_id"]) != _uid(user):
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    return dict(r)


def _resume(r: dict) -> dict:
    return {"id": r["id"], "nom": r["nom"], "mode": r["mode"], "nom_source": r["nom_source"],
            "taille": r["taille"], "mime": r["mime"], "vignette": bool(r.get("vignette")),
            "cree_le": r["cree_le"], "maj_le": r["maj_le"]}


def _objet(r: dict) -> str:
    return f"Image · projet n° {r['id']} · {r.get('nom') or ''}"[:300]


def _piece_jointe(octets: bytes, mime: str, nom: str) -> Response:
    ascii_ = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode("ascii").replace('"', "") or "image"
    return Response(content=octets, media_type=mime, headers={
        "Content-Disposition": f"attachment; filename=\"{ascii_}\"; filename*=UTF-8''{quote(nom)}",
        "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


# ── Routes ──────────────────────────────────────────────────────────────

@router.get("/projets")
def liste(request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM tools_image_projets WHERE user_id = ? ORDER BY maj_le DESC, id DESC", (_uid(user),)
        ).fetchall()
    return {"projets": [_resume(dict(r)) for r in rows], "max": TOOLS_IMAGE_PROJETS_MAX,
            "taille_max_mo": TOOLS_IMAGE_TAILLE_MAX_MO}


@router.post("/projets")
async def creer(request: Request, fichier: UploadFile = File(...), vignette: Optional[UploadFile] = File(None),
                donnees: str = Form(...)):
    user = get_current_user(request)
    d = _donnees(donnees)
    mode, reglages = _reglages(d.get("reglages"))
    orig = await _image_jointe(fichier, _max_fichier(), "Image")
    vig = await _image_jointe(vignette, _max_vignette(), "Vignette")
    nom_source = _nom_propre(d.get("nom_source"), "image")
    nom = _nom_propre(d.get("nom"), nom_source)
    with get_db() as conn:
        n = conn.execute("SELECT COUNT(*) FROM tools_image_projets WHERE user_id = ?", (_uid(user),)).fetchone()[0]
        if n >= TOOLS_IMAGE_PROJETS_MAX:
            raise HTTPException(status_code=409, detail=f"{TOOLS_IMAGE_PROJETS_MAX} projets au plus — supprimer d'anciens projets.")
        f_nom = _ecrire(orig[0], orig[1])
        v_nom = _ecrire(vig[0], vig[1]) if vig else None
        t = _maintenant()
        cur = conn.execute(
            "INSERT INTO tools_image_projets (user_id, nom, mode, reglages, nom_source, fichier, mime, taille, vignette, cree_le, maj_le)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (_uid(user), nom, mode, reglages, nom_source, f_nom, orig[1], len(orig[0]), v_nom, t, t))
        conn.commit()
        r = _projet(conn, cur.lastrowid, user)
    log_action(user=user, action="CREATE", module="tools", objet=_objet(r),
               detail={"mode": mode, "taille": r["taille"], "type": r["mime"]}, request=request)
    return _resume(r)


@router.get("/projets/{pid}")
def detail(pid: int, request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        r = _projet(conn, pid, user)
    out = _resume(r)
    try:
        out["reglages"] = json.loads(r["reglages"] or "{}")
    except ValueError:
        out["reglages"] = {}
    return out


@router.put("/projets/{pid}")
async def enregistrer(pid: int, request: Request, donnees: str = Form(...),
                      fichier: Optional[UploadFile] = File(None), vignette: Optional[UploadFile] = File(None)):
    user = get_current_user(request)
    d = _donnees(donnees)
    mode, reglages = _reglages(d.get("reglages"))
    orig = await _image_jointe(fichier, _max_fichier(), "Image")
    vig = await _image_jointe(vignette, _max_vignette(), "Vignette")
    with get_db() as conn:
        r = _projet(conn, pid, user)
        nom = _nom_propre(d.get("nom"), r["nom"])
        nom_source = _nom_propre(d.get("nom_source"), r["nom_source"])
        anciens = []
        f_nom, mime, taille = r["fichier"], r["mime"], r["taille"]
        if orig:
            anciens.append(r["fichier"])
            f_nom, mime, taille = _ecrire(orig[0], orig[1]), orig[1], len(orig[0])
        v_nom = r["vignette"]
        if vig:
            anciens.append(r["vignette"])
            v_nom = _ecrire(vig[0], vig[1])
        conn.execute(
            "UPDATE tools_image_projets SET nom = ?, mode = ?, reglages = ?, nom_source = ?, fichier = ?, mime = ?,"
            " taille = ?, vignette = ?, maj_le = ? WHERE id = ?",
            (nom, mode, reglages, nom_source, f_nom, mime, taille, v_nom, _maintenant(), pid))
        conn.commit()
        r2 = _projet(conn, pid, user)
    for a in anciens:
        _effacer(a)
    log_action(user=user, action="UPDATE", module="tools", objet=_objet(r2),
               detail={"mode": mode, "image_remplacee": bool(orig),
                       "nom": {"avant": r["nom"], "apres": nom} if nom != r["nom"] else None}, request=request)
    return _resume(r2)


@router.patch("/projets/{pid}")
def renommer(pid: int, request: Request, corps: dict = Body(...)):
    user = get_current_user(request)
    nom = _nom_propre(corps.get("nom") if isinstance(corps, dict) else None)
    if not nom:
        raise HTTPException(status_code=400, detail="Nom du projet obligatoire.")
    with get_db() as conn:
        r = _projet(conn, pid, user)
        conn.execute("UPDATE tools_image_projets SET nom = ?, maj_le = ? WHERE id = ?", (nom, _maintenant(), pid))
        conn.commit()
        r2 = _projet(conn, pid, user)
    log_action(user=user, action="UPDATE", module="tools", objet=_objet(r2),
               detail={"nom": {"avant": r["nom"], "apres": nom}}, request=request)
    return _resume(r2)


@router.post("/projets/{pid}/dupliquer")
def dupliquer(pid: int, request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        r = _projet(conn, pid, user)
        n = conn.execute("SELECT COUNT(*) FROM tools_image_projets WHERE user_id = ?", (_uid(user),)).fetchone()[0]
        if n >= TOOLS_IMAGE_PROJETS_MAX:
            raise HTTPException(status_code=409, detail=f"{TOOLS_IMAGE_PROJETS_MAX} projets au plus — supprimer d'anciens projets.")
        f_nom = _ecrire(_lire(r["fichier"]), r["mime"])
        v_nom = None
        if r["vignette"]:
            try:
                v = _lire(r["vignette"])
                v_nom = _ecrire(v, type_image(v) or "image/png")
            except HTTPException:
                v_nom = None
        t = _maintenant()
        nom = _nom_propre(f"{r['nom']} (copie)")
        cur = conn.execute(
            "INSERT INTO tools_image_projets (user_id, nom, mode, reglages, nom_source, fichier, mime, taille, vignette, cree_le, maj_le)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (_uid(user), nom, r["mode"], r["reglages"], r["nom_source"], f_nom, r["mime"], r["taille"], v_nom, t, t))
        conn.commit()
        r2 = _projet(conn, cur.lastrowid, user)
    log_action(user=user, action="DUPLICATE", module="tools", objet=_objet(r2),
               detail={"source": r["id"]}, request=request)
    return _resume(r2)


@router.delete("/projets/{pid}")
def supprimer(pid: int, request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        r = _projet(conn, pid, user)
        conn.execute("DELETE FROM tools_image_projets WHERE id = ?", (pid,))
        conn.commit()
    _effacer(r["fichier"])
    _effacer(r["vignette"])
    log_action(user=user, action="DELETE", module="tools", objet=_objet(r), request=request)
    return {"ok": True}


@router.get("/projets/{pid}/fichier")
def fichier(pid: int, request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        r = _projet(conn, pid, user)
    nom = (r["nom_source"] or "image") + "." + _EXT.get(r["mime"], "png")
    return _piece_jointe(_lire(r["fichier"]), r["mime"], nom)


@router.get("/projets/{pid}/vignette")
def vignette(pid: int, request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        r = _projet(conn, pid, user)
    if not r["vignette"]:
        raise HTTPException(status_code=404, detail="Pas de vignette.")
    octets = _lire(r["vignette"])
    mime = type_image(octets) or "application/octet-stream"
    return _piece_jointe(octets, mime, f"vignette-{r['id']}.{_EXT.get(mime, 'bin')}")

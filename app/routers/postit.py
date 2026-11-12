"""MySifa — Notes : post-its flottants, espace Mes notes (/note), partage et rédaction à plusieurs.

Une note est une ligne de `postits` (voir app/services/notes.py). Le post-it
flottant n'en est qu'une présentation : `sur_ecran = 1`. Retirer un post-it de
l'écran ne supprime pas la note ; la suppression passe par la corbeille.

Droits (`droit_sur`) : l'auteur fait tout ; un partage donne, sur la note et
ses sous-pages, la lecture ou l'écriture. Une note sans droit répond 404.

Rédaction à plusieurs : l'éditeur envoie des opérations par bloc
(`POST …/frappe`) et suit celles des autres par un flux en attente longue
(`GET …/flux`), qui porte aussi la présence (qui est dans la note, dans quel
bloc). Le flux relit la base : il fonctionne quel que soit le nombre de
processus du serveur.
"""

import asyncio
import json
import os
import re
import uuid
from datetime import datetime

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from config import UPLOAD_DIR
from database import get_db
from services.auth_service import get_current_user
from app.services.notes import (
    BLOC_TYPES,  # noqa: F401 — réexporté
    DROITS_PARTAGE,
    appliquer_ops,
    controler_parent,
    descendants,
    exiger_droit,
    liste_notes,
    liste_partagees,
    lire_blocs,
    maintenant,
    marquer_reset,
    nouvel_uid,
    normaliser_blocs,
    noter_presence,
    ops_depuis,
    presences,
    quitter,
    titre_propre,
)

router = APIRouter(tags=["postits"])

_POSTIT_COLS = (
    "id, user_id, type, title, pos_x, pos_y, width, multi_page, hidden, color, contenu, created_at, "
    "sur_ecran, parent_id, ordre, modifie_le, supprime_le, revision"
)
_POSTIT_DEFAULT_COLORS = {"today": "#22d3ee", "someday": "#fbbf24"}
_COLOR_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

FLUX_ATTENTE_S = 20
FLUX_PAS_S = 0.35
IMAGE_MAX_MO = 10
# Signatures binaires des formats acceptés : jamais de SVG (script possible).
_IMAGES = (
    (b"\x89PNG\r\n\x1a\n", "image/png", "png"),
    (b"\xff\xd8\xff", "image/jpeg", "jpg"),
    (b"GIF87a", "image/gif", "gif"),
    (b"GIF89a", "image/gif", "gif"),
)


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
    """Note dont l'utilisateur est l'auteur (post-it, corbeille, réglages)."""
    row = conn.execute(
        f"SELECT {_POSTIT_COLS} FROM postits WHERE id=? AND user_id=?",
        (postit_id, user_id),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Note introuvable")
    return dict(row)


def _lire(conn, postit_id: int) -> dict:
    return _sortie(conn.execute(f"SELECT {_POSTIT_COLS} FROM postits WHERE id=?", (postit_id,)).fetchone())


def _detail(conn, note: dict, droit: str, user_id: int) -> dict:
    out = _lire(conn, note["id"])
    out["droit"] = droit
    if droit == "proprio":
        out["partages"] = [dict(r) for r in conn.execute(
            """SELECT s.user_id, s.droit, u.nom FROM note_partages s LEFT JOIN users u ON u.id = s.user_id
                WHERE s.note_id=? ORDER BY u.nom""", (note["id"],)).fetchall()]
    else:
        r = conn.execute("SELECT nom FROM users WHERE id=?", (note["user_id"],)).fetchone()
        out["proprietaire"] = r["nom"] if r else ""
        out["sur_ecran"] = 0
    return out


# ── Lecture ─────────────────────────────────────────────────────────────

@router.get("/api/postits")
def list_postits(request: Request, ecran: int = 0):
    """Notes de l'utilisateur, contenu compris. `?ecran=1` : seulement les post-its posés sur l'écran."""
    user_id = _user_id(request)
    sql = f"SELECT {_POSTIT_COLS} FROM postits WHERE user_id=? AND supprime_le IS NULL"
    if ecran:
        sql += " AND sur_ecran=1"
    with get_db() as conn:
        rows = conn.execute(sql + " ORDER BY id", (user_id,)).fetchall()
        out = [_sortie(r) for r in rows]
        if out:
            partagees = {r[0] for r in conn.execute(
                f"SELECT DISTINCT note_id FROM note_partages WHERE note_id IN ({','.join('?' * len(out))})",
                [p["id"] for p in out]).fetchall()}
            for p in out:
                p["partagee"] = p["id"] in partagees
    return out


@router.get("/api/postits/notes")
def list_notes(request: Request, corbeille: int = 0):
    """Arbre de l'espace Mes notes (titres, extraits, texte pour la recherche) et notes partagées avec moi."""
    user_id = _user_id(request)
    with get_db() as conn:
        out = {"notes": liste_notes(conn, user_id, corbeille=bool(corbeille))}
        if not corbeille:
            out["partagees"] = liste_partagees(conn, user_id)
        return out


@router.get("/api/postits/annuaire")
def annuaire(request: Request):
    """Collègues avec qui partager une note : nom et rôle, rien d'autre."""
    user_id = _user_id(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, nom, role FROM users WHERE COALESCE(actif,1)=1 AND id<>? AND id>0 ORDER BY nom COLLATE NOCASE",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/api/postits/images/{image_id}")
def get_image(image_id: int, request: Request):
    user_id = _user_id(request)
    with get_db() as conn:
        img = conn.execute("SELECT * FROM note_images WHERE id=?", (image_id,)).fetchone()
        if not img:
            raise HTTPException(404, "Image introuvable")
        exiger_droit(conn, user_id, img["note_id"], "lire")
    chemin = os.path.join(UPLOAD_DIR, img["chemin"])
    if not os.path.isfile(chemin):
        raise HTTPException(404, "Image introuvable")
    # Format contrôlé à l'envoi (PNG, JPEG, GIF, WebP) : affichage en ligne,
    # sans reniflage du type par le navigateur.
    return FileResponse(chemin, media_type=img["mime"], headers={
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private, max-age=86400",
        "Content-Security-Policy": "default-src 'none'",
    })


@router.get("/api/postits/{postit_id}")
def get_postit(postit_id: int, request: Request):
    user_id = _user_id(request)
    with get_db() as conn:
        droit, note = exiger_droit(conn, user_id, postit_id, "lire")
        return _detail(conn, note, droit, user_id)


# ── Création, corbeille ─────────────────────────────────────────────────

@router.post("/api/postits")
async def create_postit(request: Request):
    user_id = _user_id(request)
    body = await request.json()
    ptype = str(body.get("type") or "someday").strip()
    if ptype not in ("today", "someday"):
        raise HTTPException(400, "Type invalide — today ou someday")
    title = titre_propre(body.get("title"), defaut="Sans titre")
    color = _normalize_postit_color(body.get("color"), ptype)
    blocs = normaliser_blocs(body.get("blocs") or [])
    sur_ecran = 0 if body.get("sur_ecran") in (0, False, "0") else 1
    now = maintenant()
    with get_db() as conn:
        auteur = user_id
        parent_id = None
        if body.get("parent_id") not in (None, "", 0, "0"):
            try:
                pid = int(body.get("parent_id"))
            except (TypeError, ValueError):
                raise HTTPException(400, "Note parente invalide.")
            droit, parent = exiger_droit(conn, user_id, pid, "ecrire")
            if parent.get("supprime_le"):
                raise HTTPException(400, "Note parente introuvable.")
            # Sous-page d'une note partagée : elle appartient à l'auteur de la
            # note, comme le reste de l'arborescence, et hérite du partage.
            auteur = int(parent["user_id"])
            parent_id = pid
            if droit != "proprio":
                sur_ecran = 0
        ordre = conn.execute(
            "SELECT COALESCE(MAX(ordre), -1) + 1 FROM postits WHERE user_id=? AND parent_id IS ?",
            (auteur, parent_id),
        ).fetchone()[0]
        cur = conn.execute(
            """INSERT INTO postits (user_id, type, title, color, contenu, sur_ecran, parent_id, ordre, modifie_le)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (auteur, ptype, title, color, json.dumps(blocs, ensure_ascii=False),
             sur_ecran, parent_id, ordre, now),
        )
        out = _lire(conn, cur.lastrowid)
        conn.commit()
    return out


@router.delete("/api/postits/{postit_id}")
def delete_postit(postit_id: int, request: Request):
    """Met la note et ses sous-pages à la corbeille (restaurables). Auteur seulement."""
    user_id = _user_id(request)
    with get_db() as conn:
        _get_postit_or_404(conn, postit_id, user_id)
        ids = [postit_id] + descendants(conn, user_id, postit_id)
        now = maintenant()
        conn.executemany(
            "UPDATE postits SET supprime_le=? WHERE id=? AND user_id=? AND supprime_le IS NULL",
            [(now, i, user_id) for i in ids],
        )
        conn.commit()
    return {"ok": True, "nb": len(ids)}


@router.post("/api/postits/{postit_id}/restaurer")
def restore_postit(postit_id: int, request: Request):
    """Sort une note de la corbeille, avec les sous-pages supprimées en même temps qu'elle."""
    user_id = _user_id(request)
    with get_db() as conn:
        p = _get_postit_or_404(conn, postit_id, user_id)
        if not p.get("supprime_le"):
            raise HTTPException(400, "Cette note n'est pas dans la corbeille.")
        quand = p["supprime_le"]
        ids = [postit_id] + descendants(conn, user_id, postit_id)
        conn.executemany(
            "UPDATE postits SET supprime_le=NULL WHERE id=? AND user_id=? AND supprime_le=?",
            [(i, user_id, quand) for i in ids],
        )
        if p.get("parent_id"):
            vivant = conn.execute(
                "SELECT 1 FROM postits WHERE id=? AND user_id=? AND supprime_le IS NULL",
                (p["parent_id"], user_id),
            ).fetchone()
            if not vivant:
                conn.execute("UPDATE postits SET parent_id=NULL WHERE id=?", (postit_id,))
        out = _lire(conn, postit_id)
        conn.commit()
    return out


@router.delete("/api/postits/{postit_id}/definitif")
def purge_postit(postit_id: int, request: Request):
    """Supprime pour de bon une note déjà à la corbeille, ses sous-pages, leurs images et partages."""
    user_id = _user_id(request)
    with get_db() as conn:
        p = _get_postit_or_404(conn, postit_id, user_id)
        if not p.get("supprime_le"):
            raise HTTPException(400, "Mettre la note à la corbeille avant de la supprimer définitivement.")
        ids = [postit_id] + descendants(conn, user_id, postit_id)
        marques = ",".join("?" * len(ids))
        fichiers = [r[0] for r in conn.execute(
            f"SELECT chemin FROM note_images WHERE note_id IN ({marques})", ids).fetchall()]
        for table in ("note_images", "note_partages", "note_ops", "note_presences"):
            conn.execute(f"DELETE FROM {table} WHERE note_id IN ({marques})", ids)
        conn.executemany("DELETE FROM postits WHERE id=? AND user_id=?", [(i, user_id) for i in ids])
        conn.commit()
    for f in fichiers:
        try:
            os.remove(os.path.join(UPLOAD_DIR, f))
        except OSError:
            pass
    return {"ok": True, "nb": len(ids)}


# ── Modification ────────────────────────────────────────────────────────

@router.patch("/api/postits/{postit_id}")
async def patch_postit(postit_id: int, request: Request):
    """Réglages du post-it (auteur) ; titre et contenu complet (écriture).

    `blocs` remplace tout le contenu : les éditeurs ouverts sur la note
    rechargent. L'édition courante passe par `…/frappe`.
    """
    user_id = _user_id(request)
    body = await request.json()
    reglages = ("multi_page", "hidden", "sur_ecran", "color", "ordre", "parent_id")
    with get_db() as conn:
        besoin = "proprio" if any(k in body for k in reglages) else "ecrire"
        exiger_droit(conn, user_id, postit_id, besoin)
        updates, params = [], []
        if "multi_page" in body:
            updates.append("multi_page=?")
            params.append(1 if body.get("multi_page") else 0)
        if "hidden" in body:
            updates.append("hidden=?")
            params.append(1 if body.get("hidden") else 0)
        if "sur_ecran" in body:
            updates.append("sur_ecran=?")
            params.append(1 if body.get("sur_ecran") else 0)
        if "color" in body:
            updates.append("color=?")
            params.append(_normalize_postit_color(body.get("color")))
        if "ordre" in body:
            try:
                ordre = int(body.get("ordre"))
            except (TypeError, ValueError):
                raise HTTPException(400, "Ordre invalide.")
            updates.append("ordre=?")
            params.append(ordre)
        if "parent_id" in body:
            updates.append("parent_id=?")
            params.append(controler_parent(conn, user_id, postit_id, body.get("parent_id")))
        if "blocs" in body:
            updates.append("contenu=?")
            params.append(json.dumps(normaliser_blocs(body.get("blocs")), ensure_ascii=False))
            updates.append("modifie_le=?")
            params.append(maintenant())
        if "title" not in body and not updates:
            raise HTTPException(400, "Aucune modification")
        if updates:
            conn.execute(f"UPDATE postits SET {', '.join(updates)} WHERE id=?", params + [postit_id])
            if "blocs" in body:
                marquer_reset(conn, postit_id, user_id, str(body.get("client") or ""))
            conn.commit()
        if "title" in body:
            titre_propre(body.get("title"))
            appliquer_ops(conn, postit_id, user_id, str(body.get("client") or ""),
                          [{"t": "titre", "titre": body.get("title")}])
        out = _lire(conn, postit_id)
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
    """Ajoute une case à cocher en fin de note (action de l'assistant IA)."""
    user_id = _user_id(request)
    body = await request.json()
    text = str(body.get("text") if body.get("text") is not None else "")
    with get_db() as conn:
        _, note = exiger_droit(conn, user_id, postit_id, "ecrire")
        blocs = lire_blocs(note.get("contenu"))
        bloc = {"uid": nouvel_uid(), "type": "todo", "texte": text, "coche": False}
        apres = blocs[-1]["uid"] if blocs else None
        res = appliquer_ops(conn, postit_id, user_id, "assistant", [{"t": "ins", "apres": apres, "bloc": bloc}])
        blocs = lire_blocs(conn.execute("SELECT contenu FROM postits WHERE id=?", (postit_id,)).fetchone()[0])
    return {"ok": True, "bloc": blocs[-1], "index": len(blocs) - 1, "revision": res["revision"]}


# ── Rédaction à plusieurs ───────────────────────────────────────────────

@router.post("/api/postits/{postit_id}/frappe")
async def envoyer_ops(postit_id: int, request: Request):
    """Opérations d'un éditeur : {client, ops:[…]}. Rend la nouvelle révision."""
    user_id = _user_id(request)
    body = await request.json()
    with get_db() as conn:
        exiger_droit(conn, user_id, postit_id, "ecrire")
        return appliquer_ops(conn, postit_id, user_id, str(body.get("client") or ""), body.get("ops"))


def _etat_flux(note_id: int, user_id: int, client: str, depuis: int, bloc):
    with get_db() as conn:
        exiger_droit(conn, user_id, note_id, "lire")
        noter_presence(conn, note_id, user_id, client, bloc)
        rev = int(conn.execute("SELECT revision FROM postits WHERE id=?", (note_id,)).fetchone()[0] or 0)
        ops, reset = ([], False) if rev <= depuis else ops_depuis(conn, note_id, depuis)
        return rev, ops, reset, presences(conn, note_id, client, user_id)


def _signature(pres) -> str:
    return "|".join(sorted("%s:%s" % (p["client"], p["bloc"] or "") for p in pres))


@router.get("/api/postits/{postit_id}/flux")
async def flux(postit_id: int, request: Request, depuis: int = 0, client: str = "", bloc: str = "", sig: str = ""):
    """Attente longue : rend dès qu'il y a du nouveau (opérations ou présence), sinon après 20 s."""
    user_id = _user_id(request)
    bloc = bloc or None
    fin = asyncio.get_event_loop().time() + FLUX_ATTENTE_S
    while True:
        rev, ops, reset, pres = _etat_flux(postit_id, user_id, client, depuis, bloc)
        signature = _signature(pres)
        if rev > depuis or reset or signature != sig or asyncio.get_event_loop().time() >= fin:
            return {"revision": rev, "ops": ops, "reset": reset, "presences": pres, "sig": signature}
        if await request.is_disconnected():
            return {"revision": rev, "ops": [], "reset": False, "presences": pres, "sig": signature}
        await asyncio.sleep(FLUX_PAS_S)


@router.post("/api/postits/{postit_id}/presence-fin")
async def fin_presence(postit_id: int, request: Request):
    user_id = _user_id(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    with get_db() as conn:
        exiger_droit(conn, user_id, postit_id, "lire")
        quitter(conn, postit_id, str(body.get("client") or ""))
    return {"ok": True}


# ── Partage ─────────────────────────────────────────────────────────────

@router.put("/api/postits/{postit_id}/partages")
async def partager(postit_id: int, request: Request):
    """Partage la note (et ses sous-pages) avec un collègue : {user_id, droit: lire|ecrire}."""
    user_id = _user_id(request)
    body = await request.json()
    droit = str(body.get("droit") or "ecrire")
    if droit not in DROITS_PARTAGE:
        raise HTTPException(400, "Droit invalide — lire ou ecrire.")
    try:
        cible = int(body.get("user_id"))
    except (TypeError, ValueError):
        raise HTTPException(400, "Collègue invalide.")
    if cible == user_id:
        raise HTTPException(400, "Vous êtes déjà l'auteur de cette note.")
    with get_db() as conn:
        _, note = exiger_droit(conn, user_id, postit_id, "proprio")
        if note.get("supprime_le"):
            raise HTTPException(400, "Cette note est dans la corbeille.")
        if not conn.execute("SELECT 1 FROM users WHERE id=? AND COALESCE(actif,1)=1", (cible,)).fetchone():
            raise HTTPException(400, "Collègue introuvable.")
        conn.execute(
            """INSERT INTO note_partages (note_id, user_id, droit, partage_par, cree_le) VALUES (?,?,?,?,?)
               ON CONFLICT(note_id, user_id) DO UPDATE SET droit=excluded.droit""",
            (postit_id, cible, droit, user_id, maintenant()),
        )
        conn.commit()
        return _detail(conn, note, "proprio", user_id)["partages"]


@router.delete("/api/postits/{postit_id}/partages/{cible}")
def retirer_partage(postit_id: int, cible: int, request: Request):
    """L'auteur retire un partage ; un invité peut aussi quitter une note partagée avec lui."""
    user_id = _user_id(request)
    with get_db() as conn:
        if cible != user_id:
            exiger_droit(conn, user_id, postit_id, "proprio")
        conn.execute("DELETE FROM note_partages WHERE note_id=? AND user_id=?", (postit_id, cible))
        conn.commit()
    return {"ok": True}


# ── Images ──────────────────────────────────────────────────────────────

@router.post("/api/postits/{postit_id}/images")
async def envoyer_image(postit_id: int, request: Request, fichier: UploadFile = File(...)):
    user_id = _user_id(request)
    brut = await fichier.read(IMAGE_MAX_MO * 1024 * 1024 + 1)
    if len(brut) > IMAGE_MAX_MO * 1024 * 1024:
        raise HTTPException(400, f"Image trop lourde — {IMAGE_MAX_MO} Mo au plus.")
    mime = ext = None
    for signature, m, e in _IMAGES:
        if brut.startswith(signature):
            mime, ext = m, e
            break
    if not mime and brut[:4] == b"RIFF" and brut[8:12] == b"WEBP":
        mime, ext = "image/webp", "webp"
    if not mime:
        raise HTTPException(400, "Format non pris en charge — PNG, JPEG, GIF ou WebP.")
    with get_db() as conn:
        exiger_droit(conn, user_id, postit_id, "ecrire")
        relatif = os.path.join("notes", datetime.now().strftime("%Y/%m"), f"{uuid.uuid4().hex}.{ext}")
        complet = os.path.join(UPLOAD_DIR, relatif)
        os.makedirs(os.path.dirname(complet), exist_ok=True)
        with open(complet, "wb") as f:
            f.write(brut)
        cur = conn.execute(
            "INSERT INTO note_images (note_id, user_id, chemin, nom, mime, taille, cree_le) VALUES (?,?,?,?,?,?,?)",
            (postit_id, user_id, relatif, (fichier.filename or "")[:200], mime, len(brut), maintenant()),
        )
        conn.commit()
        iid = cur.lastrowid
    return {"id": iid, "url": f"/api/postits/images/{iid}"}

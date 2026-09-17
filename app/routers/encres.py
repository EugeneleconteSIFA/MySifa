"""
Couleurs d'encre — API du référentiel (Paramètres › Fabrication › Impression).

Le référentiel donne au BAT la teinte écran d'une encre. Écriture réservée aux
mêmes rôles que les seuils d'arrêt et les alertes maintenance ; lecture ouverte
à tout compte connecté, la teinte d'un Pantone n'a rien de sensible.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from database import get_db
from app.services.audit_service import log_action
from app.services.auth_service import get_current_user
from app.services import encres_couleurs as svc

router = APIRouter()


def _require_admin(request: Request) -> dict:
    from app.routers.settings import _require_alerts_admin
    return _require_alerts_admin(request)


class EncreIn(BaseModel):
    code: str
    hex: str
    libelle: Optional[str] = None
    actif: bool = True


def _valider(body: EncreIn) -> tuple:
    code = " ".join((body.code or "").split())
    if not code:
        raise HTTPException(400, "Code manquant — ex. 485 C.")
    if len(code) > 40:
        raise HTTPException(400, "Code trop long — 40 caractères au plus.")
    hx = svc.normaliser_hex(body.hex)
    if not hx:
        raise HTTPException(400, "Teinte invalide — format #RRGGBB.")
    cle = svc.cle(code)
    if not cle:
        raise HTTPException(400, "Code invalide.")
    libelle = (body.libelle or "").strip()[:80] or None
    return code, cle, hx, libelle


def _row(r: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": r["id"], "code": r["code"], "cle": r["cle"],
        "libelle": r["libelle"], "hex": r["hex"], "actif": bool(r["actif"]),
        "updated_at": r["updated_at"] or r["created_at"],
        "updated_by": r["updated_by"],
    }


def _ip(request: Request) -> Optional[str]:
    return request.client.host if request.client else None


@router.get("/api/encres")
def lister(request: Request):
    get_current_user(request)
    with get_db() as conn:
        try:
            rows = conn.execute(
                "SELECT * FROM encres_couleurs ORDER BY actif DESC, cle"
            ).fetchall()
        except sqlite3.Error:
            rows = []
    return {"encres": [_row(r) for r in rows]}


@router.get("/api/encres/palette")
def palette(request: Request):
    """Liste compacte pour la recherche à la saisie : [clé, libellé, teinte].

    Chargée une fois par page par static/mysifa_encre_picker.js. Format en
    tableaux plutôt qu'en objets : ~3 200 lignes, le poids compte."""
    get_current_user(request)
    with get_db() as conn:
        try:
            rows = conn.execute(
                "SELECT cle, libelle, hex FROM encres_couleurs WHERE actif=1 ORDER BY cle"
            ).fetchall()
        except sqlite3.Error:
            rows = []
    return {"encres": [[r[0], r[1] or "", r[2]] for r in rows]}


@router.get("/api/encres/resoudre")
def resoudre_lot(request: Request, d: List[str] = Query(default=[])):
    """Teinte de plusieurs désignations, exactement comme le BAT la calcule.

    GET et non POST : c'est une lecture, elle n'a rien à faire au journal.
    Une désignation sans teinte connue renvoie null (pas le gris neutre)."""
    get_current_user(request)
    from app.services.bat_etiquette import _guess_hex, _PANTONE_FALLBACK
    with get_db() as conn:
        encres = svc.charger(conn)
    out: Dict[str, Optional[str]] = {}
    for des in d[:200]:
        hx = _guess_hex(des, encres) if (des or "").strip() else _PANTONE_FALLBACK
        out[des] = None if hx == _PANTONE_FALLBACK else hx
    return {"teintes": out}


@router.get("/api/encres/tester")
def tester(request: Request, designation: str = ""):
    """Ce que le BAT afficherait pour une désignation saisie."""
    get_current_user(request)
    from app.services.bat_etiquette import _guess_hex, _PANTONE_FALLBACK
    with get_db() as conn:
        encres = svc.charger(conn)
    hx = svc.resoudre(designation, encres)
    if hx:
        source = "referentiel"
    else:
        hx = _guess_hex(designation)
        source = "nom" if hx != _PANTONE_FALLBACK else None
        if source is None:
            hx = None
    return {"designation": designation, "cles": svc.candidats(designation)[:4],
            "hex": hx, "source": source}


@router.get("/api/encres/a-rapprocher")
def a_rapprocher(request: Request):
    """Désignations réellement saisies (fiches techniques, fiches MyAO) et
    leur teinte actuelle. C'est la liste de travail pour compléter le
    référentiel : on y voit ce qui tombe encore sur le violet neutre."""
    get_current_user(request)
    from app.services.bat_etiquette import _BASIC_INKS
    compte: Dict[str, int] = {}

    def ajouter(val: Any) -> None:
        s = " ".join(str(val or "").split()).upper()
        if s:
            compte[s] = compte.get(s, 0) + 1

    with get_db() as conn:
        encres = svc.charger(conn)
        try:
            for r in conn.execute(
                "SELECT tete1_pantone, tete2_pantone, tete3_pantone,"
                " tete1_couleur, tete2_couleur, tete3_couleur FROM fiches_techniques"
            ):
                for v in r:
                    ajouter(v)
        except sqlite3.Error:
            pass
        try:
            for (fj,) in conn.execute(
                "SELECT fiche_json FROM ao_produits WHERE fiche_json IS NOT NULL"
            ):
                try:
                    imp = (json.loads(fj) or {}).get("impressions_detail") or {}
                except (TypeError, ValueError):
                    continue
                for face in ("recto_details", "verso_details"):
                    for d in imp.get(face) or []:
                        if isinstance(d, dict):
                            ajouter(d.get("couleur"))
        except sqlite3.Error:
            pass

    lignes = []
    for designation, n in compte.items():
        hx = svc.resoudre(designation, encres)
        source = "referentiel" if hx else None
        if not hx:
            low = designation.lower()
            for k, v in _BASIC_INKS.items():
                if k in low:
                    hx, source = v, "nom"
                    break
        lignes.append({"designation": designation, "occurrences": n,
                       "hex": hx, "source": source,
                       "cle_proposee": svc.cle(designation)})
    lignes.sort(key=lambda x: (x["source"] is not None, -x["occurrences"], x["designation"]))
    return {
        "lignes": lignes,
        "sans_teinte": sum(1 for x in lignes if x["source"] is None),
    }


@router.post("/api/encres")
def creer(body: EncreIn, request: Request):
    user = _require_admin(request)
    code, cle, hx, libelle = _valider(body)
    now = datetime.now().isoformat(timespec="seconds")
    with get_db() as conn:
        if conn.execute("SELECT 1 FROM encres_couleurs WHERE cle=?", (cle,)).fetchone():
            raise HTTPException(400, f"Une couleur existe déjà pour ce code ({cle}).")
        cur = conn.execute(
            """INSERT INTO encres_couleurs
               (code, cle, libelle, hex, actif, created_at, updated_at, updated_by)
               VALUES (?,?,?,?,?,?,?,?)""",
            (code, cle, libelle, hx, 1 if body.actif else 0, now, now, user.get("nom")),
        )
        conn.commit()
        new_id = cur.lastrowid
    log_action(user=user, action="CREATE", module="settings",
               objet=f"Couleur d'encre {cle}", detail={"hex": hx}, ip=_ip(request))
    return {"success": True, "id": new_id, "cle": cle}


@router.put("/api/encres/{encre_id}")
def modifier(encre_id: int, body: EncreIn, request: Request):
    user = _require_admin(request)
    code, cle, hx, libelle = _valider(body)
    now = datetime.now().isoformat(timespec="seconds")
    with get_db() as conn:
        avant = conn.execute("SELECT * FROM encres_couleurs WHERE id=?", (encre_id,)).fetchone()
        if not avant:
            raise HTTPException(404, "Couleur introuvable.")
        if conn.execute(
            "SELECT 1 FROM encres_couleurs WHERE cle=? AND id<>?", (cle, encre_id)
        ).fetchone():
            raise HTTPException(400, f"Une couleur existe déjà pour ce code ({cle}).")
        conn.execute(
            """UPDATE encres_couleurs
               SET code=?, cle=?, libelle=?, hex=?, actif=?, updated_at=?, updated_by=?
               WHERE id=?""",
            (code, cle, libelle, hx, 1 if body.actif else 0, now, user.get("nom"), encre_id),
        )
        conn.commit()
    log_action(user=user, action="UPDATE", module="settings",
               objet=f"Couleur d'encre {cle}",
               detail={"avant": avant["hex"], "apres": hx}, ip=_ip(request))
    return {"success": True, "cle": cle}


@router.delete("/api/encres/{encre_id}")
def supprimer(encre_id: int, request: Request):
    user = _require_admin(request)
    with get_db() as conn:
        row = conn.execute("SELECT cle FROM encres_couleurs WHERE id=?", (encre_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Couleur introuvable.")
        conn.execute("DELETE FROM encres_couleurs WHERE id=?", (encre_id,))
        conn.commit()
    log_action(user=user, action="DELETE", module="settings",
               objet=f"Couleur d'encre {row['cle']}", ip=_ip(request))
    return {"success": True}

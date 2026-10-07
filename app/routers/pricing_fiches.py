"""Coûts matières — fiches techniques matières et produits (BOM).

Lecture et saisie des caractéristiques, rendu PDF à visualiser dans la page
ou à télécharger.
"""

from __future__ import annotations

import io
import re

from fastapi import APIRouter, Body, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from database import get_db
from app.routers.pricing import _require_read, _require_write
from app.services.pricing import fiche_technique as ft

router = APIRouter()

_OBJETS = ("matiere", "produit")


def _charger(conn, objet: str, objet_id: int) -> dict:
    if objet not in _OBJETS:
        raise HTTPException(status_code=404, detail="Type de fiche inconnu.")
    o = ft.matiere(conn, objet_id) if objet == "matiere" else ft.produit(conn, objet_id)
    if not o:
        raise HTTPException(status_code=404, detail="Fiche introuvable.")
    return o


def _reponse(objet: str, o: dict) -> dict:
    if objet == "matiere":
        titre = o.get("designation") or o.get("reference")
        herite = ft.sources_matiere(o)
        composants = []
    else:
        titre = o.get("designation") or o.get("code")
        herite = {k: {"valeur": v, "source": "composants"}
                  for k, v in ft.donnees_produit({**o, "fiche": {"data": {}}}).items()}
        composants = [
            {"role": c["role"], "matiere_id": c["matiere"]["id"],
             "reference": c["matiere"]["reference"], "designation": c["matiere"]["designation"],
             "renseignee": bool(c["matiere"]["fiche"]["data"])}
            for c in o["composants"]
        ]
    return {
        "objet": objet,
        "id": o["id"],
        "titre": titre,
        "champs": ft.champs_def(objet),
        "data": o["fiche"]["data"],
        # Valeurs reprises de la base ou des composants quand la fiche se tait :
        # l'écran les montre en indication, le PDF les imprime.
        "herite": herite,
        "composants": composants,
        "updated_at": o["fiche"]["updated_at"],
        "updated_by_name": o["fiche"]["updated_by_name"],
    }


@router.get("/api/pricing/fiches/{objet}/{objet_id}")
def get_fiche(request: Request, objet: str, objet_id: int):
    _require_read(request)
    with get_db() as conn:
        return _reponse(objet, _charger(conn, objet, objet_id))


@router.put("/api/pricing/fiches/{objet}/{objet_id}")
def put_fiche(request: Request, objet: str, objet_id: int, body: dict = Body(...)):
    user = _require_write(request)
    with get_db() as conn:
        _charger(conn, objet, objet_id)
        ft.ecrire(conn, objet, objet_id, body.get("data") or {},
                  user.get("nom") or user.get("name") or user.get("email") or "")
        return _reponse(objet, _charger(conn, objet, objet_id))


@router.get("/api/pricing/fiches/{objet}/{objet_id}/pdf")
def pdf_fiche(request: Request, objet: str, objet_id: int, telecharger: bool = Query(False)):
    _require_read(request)
    with get_db() as conn:
        o = _charger(conn, objet, objet_id)
    try:
        contenu = ft.pdf_matiere(o) if objet == "matiere" else ft.pdf_produit(o)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Génération PDF impossible : {exc}") from exc
    ref = o.get("reference") if objet == "matiere" else o.get("code")
    nom = "fiche-technique-" + (re.sub(r"[^\w\-]+", "_", ref or str(objet_id))[:50]) + ".pdf"
    mode = "attachment" if telecharger else "inline"
    return StreamingResponse(
        io.BytesIO(contenu),
        media_type="application/pdf",
        headers={"Content-Disposition": f'{mode}; filename="{nom}"', "Cache-Control": "no-store"},
    )

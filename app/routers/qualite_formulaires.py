"""MyQualité › Formulaires — création et publication de formulaires.

Lot 1 : éditeur et versions publiées. L'envoi aux fournisseurs, au personnel
et aux clients (lien personnel, suivi, relances) suit le modèle d'EUDR
(`qualite_eudr.py`) et viendra s'appuyer sur `qualite_formulaires_versions`.

Lecture : rôles qualité en lecture (`_require_qualite_view`).
Écriture : rôles qualité (`_require_qualite_access`).
Structure et règles : `app/services/qualite_formulaires.py`.
"""
from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException, Request

from app.core.database import get_db
from app.routers.qualite import _require_qualite_access, _require_qualite_view
from app.services import qualite_formulaires as formulaires
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/qualite/formulaires", tags=["qualite_formulaires"])


def _auteur(user: dict) -> str | None:
    return (user.get("nom") or user.get("email") or user.get("identifiant") or None)


def _objet(fid: int, titre: str | None) -> str:
    return f"Formulaire #{fid}" + (f" · {titre}" if titre else "")


def _lire_ou_404(conn, fid: int) -> dict:
    d = formulaires.lire(conn, fid)
    if d is None:
        raise HTTPException(status_code=404, detail="Formulaire introuvable.")
    return d


@router.get("")
def liste(request: Request):
    _require_qualite_view(request)
    with get_db() as conn:
        return {"formulaires": formulaires.liste(conn)}


@router.post("")
def creer(request: Request, body: dict = Body(default={})):
    user = _require_qualite_access(request)
    with get_db() as conn:
        try:
            fid = formulaires.creer(conn, titre=body.get("titre") or "", description=body.get("description") or "",
                                    schema=body.get("schema"), auteur=_auteur(user))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        conn.commit()
        d = formulaires.lire(conn, fid)
    log_action(user=user, action="CREATE", module="qualite", objet=_objet(fid, d["titre"]), request=request)
    return d


@router.get("/{fid}")
def detail(fid: int, request: Request):
    _require_qualite_view(request)
    with get_db() as conn:
        return _lire_ou_404(conn, fid)


@router.put("/{fid}")
def enregistrer(fid: int, request: Request, body: dict = Body(...)):
    user = _require_qualite_access(request)
    with get_db() as conn:
        d = _lire_ou_404(conn, fid)
        if d["statut"] == "archive":
            raise HTTPException(status_code=409, detail="Formulaire archivé — le restaurer pour le modifier.")
        try:
            formulaires.enregistrer(conn, fid, titre=body.get("titre"), description=body.get("description"),
                                    schema=body.get("schema"), auteur=_auteur(user))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        conn.commit()
        d = formulaires.lire(conn, fid)
    # Appelé par l'enregistrement automatique de l'éditeur (après 2 s sans
    # frappe) : une ligne de journal par pause de saisie, pas par touche.
    log_action(user=user, action="UPDATE", module="qualite", objet=_objet(fid, d["titre"]),
               detail={"nb_questions": d["nb_questions"]}, request=request)
    return d


@router.post("/{fid}/publier")
def publier(fid: int, request: Request):
    user = _require_qualite_access(request)
    with get_db() as conn:
        _lire_ou_404(conn, fid)
        try:
            numero = formulaires.publier(conn, fid, auteur=_auteur(user))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        conn.commit()
        d = formulaires.lire(conn, fid)
    log_action(user=user, action="PUBLISH", module="qualite", objet=_objet(fid, d["titre"]),
               detail={"version": numero}, request=request)
    return d


@router.post("/{fid}/dupliquer")
def dupliquer(fid: int, request: Request):
    user = _require_qualite_access(request)
    with get_db() as conn:
        _lire_ou_404(conn, fid)
        nouveau = formulaires.dupliquer(conn, fid, auteur=_auteur(user))
        conn.commit()
        d = formulaires.lire(conn, nouveau)
    log_action(user=user, action="DUPLICATE", module="qualite", objet=_objet(nouveau, d["titre"]),
               detail={"source": fid}, request=request)
    return d


@router.post("/{fid}/archiver")
def archiver(fid: int, request: Request):
    user = _require_qualite_access(request)
    with get_db() as conn:
        d = _lire_ou_404(conn, fid)
        formulaires.changer_statut(conn, fid, "archive", auteur=_auteur(user))
        conn.commit()
    log_action(user=user, action="ARCHIVE", module="qualite", objet=_objet(fid, d["titre"]), request=request)
    return {"ok": True}


@router.post("/{fid}/restaurer")
def restaurer(fid: int, request: Request):
    user = _require_qualite_access(request)
    with get_db() as conn:
        d = _lire_ou_404(conn, fid)
        statut = "publie" if d["version_courante"] else "brouillon"
        formulaires.changer_statut(conn, fid, statut, auteur=_auteur(user))
        conn.commit()
    log_action(user=user, action="RESTORE", module="qualite", objet=_objet(fid, d["titre"]), request=request)
    return {"ok": True}


@router.delete("/{fid}")
def supprimer(fid: int, request: Request):
    user = _require_qualite_access(request)
    with get_db() as conn:
        d = _lire_ou_404(conn, fid)
        try:
            formulaires.supprimer(conn, fid)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        conn.commit()
    log_action(user=user, action="DELETE", module="qualite", objet=_objet(fid, d["titre"]), request=request)
    return {"ok": True}

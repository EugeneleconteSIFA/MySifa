"""MyExpé — grilles tarifaires des transporteurs (API interne).

Monté sous `/api/expe`. L'onglet Tarifs de la fiche transporteur ne charge
plus les lignes de prix : il lit le résumé des grilles, puis une page de zones
à la fois. Un fichier déposé (PDF, Excel, CSV) est lu côté serveur et devient
une ou plusieurs grilles brouillon, à activer après contrôle.

Logique : `app/services/expe_grilles.py` (états, remplacement, retour
arrière) et `app/services/expe_tarif_lecture.py` (lecture des fichiers).
"""

from fastapi import APIRouter, Body, File, Form, HTTPException, Query, Request, UploadFile

from app.routers.expe_departs import _require_expe, _require_expe_write
from app.services import expe_grilles as grilles
from app.services import ia_usage
from app.services.audit_service import log_action
from app.services.expe_tarif_lecture import LectureErreur, lire
from database import get_db

router = APIRouter()

_TAILLE_MAX = 25 * 1024 * 1024


def _transporteur(conn, transporteur_id: int):
    trp = conn.execute(
        "SELECT id, nom FROM expe_transporteurs WHERE id=?", (transporteur_id,)
    ).fetchone()
    if not trp:
        raise HTTPException(status_code=404, detail="Transporteur introuvable")
    return trp


def _nom(trp) -> str:
    return (trp["nom"] or "").strip() or f"#{trp['id']}"


def _email(user: dict) -> str:
    return user.get("email") or user.get("identifiant") or ""


def _ip(request: Request):
    return request.client.host if request.client else None


@router.get("/transporteurs/{transporteur_id}/tarifs")
def resume_tarifs(request: Request, transporteur_id: int):
    """Grilles (sans leurs prix) et frais annexes d'un transporteur."""
    _require_expe(request)
    with get_db() as conn:
        _transporteur(conn, transporteur_id)
        frais = conn.execute(
            "SELECT * FROM expe_tarifs_frais WHERE transporteur_id=? ORDER BY libelle",
            (transporteur_id,),
        ).fetchall()
        return {
            "grilles": grilles.lister(conn, transporteur_id),
            "frais": [dict(r) for r in frais],
        }


@router.get("/transporteurs/{transporteur_id}/tarifs/grilles/{grille_id}/matrice")
def matrice_grille(
    request: Request,
    transporteur_id: int,
    grille_id: int,
    q: str = Query("", max_length=60),
    offset: int = Query(0, ge=0),
    limite: int = Query(60, ge=1, le=200),
):
    _require_expe(request)
    with get_db() as conn:
        try:
            return grilles.matrice(conn, transporteur_id, grille_id, q, offset, limite)
        except grilles.GrilleErreur as e:
            raise HTTPException(status_code=404, detail=str(e))


@router.post("/transporteurs/{transporteur_id}/tarifs/importer")
def importer_grille(
    request: Request,
    transporteur_id: int,
    file: UploadFile = File(...),
    ia: str = Form("1"),
):
    """Lit un fichier de tarifs et le range en grilles brouillon."""
    user = _require_expe_write(request)
    contenu = file.file.read(_TAILLE_MAX + 1)
    if len(contenu) > _TAILLE_MAX:
        raise HTTPException(status_code=413, detail="Fichier trop lourd — 25 Mo au plus.")
    nom = file.filename or "tarif"
    with get_db() as conn:
        trp = _transporteur(conn, transporteur_id)
    try:
        with ia_usage.suivi(user, "tarif_transport", "expe"):
            lu = lire(contenu, nom, ia=ia not in ("0", "false", "non"))
    except LectureErreur as e:
        raise HTTPException(status_code=422, detail=str(e))
    with get_db() as conn:
        try:
            ids = grilles.creer_brouillons(
                conn,
                transporteur_id,
                lu["lignes"],
                source_filename=nom,
                methode=lu["methode"],
                email=_email(user),
                date_effet=lu["date_effet"],
                frais=lu["frais"],
            )
        except grilles.GrilleErreur as e:
            raise HTTPException(status_code=422, detail=str(e))
        conn.commit()
        crees = [g for g in grilles.lister(conn, transporteur_id) if g["id"] in ids]
    log_action(
        user=user,
        action="IMPORT",
        module="expe",
        objet=f"Transporteur {_nom(trp)} · grille importée ({nom})",
        detail={"grilles": ids, "methode": lu["methode"], "lignes": sum(g["nb_lignes"] for g in crees)},
        ip=_ip(request),
    )
    return {
        "grilles": crees,
        "methode": lu["methode"],
        "date_effet": lu["date_effet"],
        "avertissements": lu["avertissements"],
    }


def _changer_etat(request: Request, transporteur_id: int, grille_id: int, geste: str):
    user = _require_expe_write(request)
    with get_db() as conn:
        trp = _transporteur(conn, transporteur_id)
        try:
            if geste == "activer":
                res = grilles.activer(conn, transporteur_id, grille_id, _email(user))
            else:
                res = grilles.archiver(conn, transporteur_id, grille_id)
        except grilles.GrilleErreur as e:
            raise HTTPException(status_code=400, detail=str(e))
        conn.commit()
        g = conn.execute("SELECT libelle FROM expe_tarif_grilles WHERE id=?", (grille_id,)).fetchone()
    log_action(
        user=user,
        action="UPDATE",
        module="expe",
        objet=f"Transporteur {_nom(trp)} · grille « {g['libelle'] if g else grille_id} » "
              + ("activée" if geste == "activer" else "archivée"),
        detail=res,
        ip=_ip(request),
    )
    return res


@router.post("/transporteurs/{transporteur_id}/tarifs/grilles/{grille_id}/activer")
def activer_grille(request: Request, transporteur_id: int, grille_id: int):
    return _changer_etat(request, transporteur_id, grille_id, "activer")


@router.post("/transporteurs/{transporteur_id}/tarifs/grilles/{grille_id}/archiver")
def archiver_grille(request: Request, transporteur_id: int, grille_id: int):
    return _changer_etat(request, transporteur_id, grille_id, "archiver")


@router.patch("/transporteurs/{transporteur_id}/tarifs/grilles/{grille_id}")
def modifier_grille(request: Request, transporteur_id: int, grille_id: int, body: dict = Body(...)):
    _require_expe_write(request)
    with get_db() as conn:
        _transporteur(conn, transporteur_id)
        try:
            g = grilles.modifier(conn, transporteur_id, grille_id, body or {})
        except grilles.GrilleErreur as e:
            raise HTTPException(status_code=400, detail=str(e))
        conn.commit()
    return {"grille": g}


@router.delete("/transporteurs/{transporteur_id}/tarifs/grilles/{grille_id}")
def supprimer_grille(request: Request, transporteur_id: int, grille_id: int):
    user = _require_expe_write(request)
    with get_db() as conn:
        trp = _transporteur(conn, transporteur_id)
        try:
            n = grilles.supprimer(conn, transporteur_id, grille_id)
        except grilles.GrilleErreur as e:
            raise HTTPException(status_code=400, detail=str(e))
        conn.commit()
    log_action(
        user=user,
        action="DELETE",
        module="expe",
        objet=f"Transporteur {_nom(trp)} · grille supprimée",
        detail={"grille": grille_id, "lignes": n},
        ip=_ip(request),
    )
    return {"deleted_lignes": n}


@router.delete("/transporteurs/{transporteur_id}/tarifs")
def vider_tarifs(request: Request, transporteur_id: int):
    """Supprime toutes les grilles, leurs lignes et les frais annexes."""
    user = _require_expe_write(request)
    with get_db() as conn:
        trp = _transporteur(conn, transporteur_id)
        res = grilles.vider(conn, transporteur_id)
        conn.commit()
    log_action(
        user=user,
        action="DELETE",
        module="expe",
        objet=f"Transporteur {_nom(trp)} · tarifs vidés",
        detail=res,
        ip=_ip(request),
    )
    return res

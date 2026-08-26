"""API — clients et fournisseurs alignés sur RVGI.

Lecture seule côté RVGI, écriture côté MySifa uniquement. Rien n'est jamais
renvoyé vers l'ERP : le miroir est monté en `mode=ro`, et ce module n'a même
pas de quoi lui écrire.

Toutes les routes sont réservées au super-administrateur, comme le référentiel
clients qu'elles prolongent.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.services import rvgi_tiers as tiers
from app.services.audit_service import log_action
from database import get_db
from services.auth_service import require_superadmin

router = APIRouter(prefix="/api/rvgi-tiers", tags=["rvgi-tiers"])


def _perimetre(p: str) -> str:
    if p not in tiers.PERIMETRES:
        raise HTTPException(400, "Périmètre inconnu — attendu : client ou fournisseur.")
    return p


def _nom(user) -> str:
    if isinstance(user, dict):
        return str(user.get("nom") or user.get("email") or "")
    return ""


def _journal(request: Request, user, action: str, objet: str) -> None:
    """L'audit ne doit jamais faire échouer l'action — il la raconte, c'est tout."""
    log_action(user=user if isinstance(user, dict) else {}, action=action,
               module="settings", objet=objet,
               ip=request.client.host if request.client else None)


class LienIn(BaseModel):
    perimetre: str
    fiche_id: int
    rvgi_numero: Optional[int] = None      # None = détacher


class ImportIn(BaseModel):
    perimetre: str
    numeros: List[int]


@router.get("/etat")
def etat(request: Request, perimetre: str = Query("client", max_length=16)):
    """Ce qu'une synchro ferait, avant de la lancer."""
    require_superadmin(request)
    p = _perimetre(perimetre)
    with get_db() as conn:
        return tiers.etat(conn, p)


@router.post("/synchroniser")
def synchroniser(request: Request, perimetre: str = Query("client", max_length=16),
                 importer: bool = Query(True),
                 inclure_bloques: bool = Query(False)):
    """Rapprocher, importer, puis laisser RVGI réécrire ce qu'il connaît."""
    user = require_superadmin(request)
    p = _perimetre(perimetre)
    try:
        with get_db() as conn:
            res = tiers.synchroniser(conn, p, _nom(user), "manuel",
                                     importer=importer,
                                     inclure_bloques=inclure_bloques)
            conn.commit()
    except FileNotFoundError as e:
        raise HTTPException(503, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    _journal(request, user, "SYNC",
             "RVGI · %s · %d liés, %d créés, %d mis à jour"
             % (p, res["lies"], res["nouveaux"], res["mis_a_jour"]))
    return res


@router.get("/a-confirmer")
def a_confirmer(request: Request, perimetre: str = Query("client", max_length=16),
                limite: int = Query(200, ge=1, le=1000)):
    """Les rapprochements probables que personne n'a encore validés.

    On rend côte à côte ce que MySifa porte et ce que RVGI porte : c'est en
    les voyant l'un en face de l'autre qu'on tranche, pas sur un score.
    """
    require_superadmin(request)
    p = _perimetre(perimetre)
    plan = tiers.PLAN[p]
    try:
        rvgi = tiers.lire_rvgi(p)
    except FileNotFoundError as e:
        raise HTTPException(503, str(e))
    with get_db() as conn:
        lignes = [dict(r) for r in conn.execute(
            'SELECT * FROM "%s" WHERE rvgi_etat=\'a_confirmer\' '
            "ORDER BY rvgi_score DESC, id LIMIT ?" % plan["table"], (int(limite),))]
    out = []
    for f in lignes:
        r = rvgi.get(int(f["rvgi_numero"] or 0)) or {}
        out.append({
            "id": f["id"],
            "motif": f.get("rvgi_motif"),
            "score": f.get("rvgi_score"),
            "mysifa": {"nom": f.get(plan["cle_nom"]), "siret": f.get(plan["cle_siret"]),
                       "ville": f.get("ville"), "email": f.get("email")},
            "rvgi": {"numero": f.get("rvgi_numero"), "code": r.get("code"),
                     "rs": r.get("rs"), "siret": r.get("siret"),
                     "ville": r.get("vil"), "mail": r.get("mail"),
                     "actif": r.get("bloq") != tiers.BLOQ_INACTIF},
        })
    return {"perimetre": p, "total": len(out), "lignes": out}


@router.get("/a-mapper")
def a_mapper(request: Request, perimetre: str = Query("client", max_length=16),
             limite: int = Query(120, ge=1, le=400)):
    """Tout ce qui attend une décision : proposé, et ressemblant.

    Le rapprochement automatique tourne à chaque synchro et ne pose un lien
    que sur du certain — SIRET, code ERP, nom normalisé identique. Ce qui
    reste demande un œil : cette route le rassemble, avec les meilleurs
    candidats de l'ERP en face.
    """
    require_superadmin(request)
    p = _perimetre(perimetre)
    try:
        with get_db() as conn:
            return tiers.a_mapper(conn, p, limite)
    except FileNotFoundError as e:
        raise HTTPException(503, str(e))


@router.post("/lier")
def lier(corps: LienIn, request: Request):
    """Confirmer, corriger ou défaire un lien. Détacher rouvre la saisie."""
    user = require_superadmin(request)
    p = _perimetre(corps.perimetre)
    try:
        with get_db() as conn:
            tiers.confirmer(conn, p, int(corps.fiche_id), corps.rvgi_numero)
            conn.commit()
    except ValueError as e:
        raise HTTPException(409, str(e))
    _journal(request, user, "UPDATE",
             "RVGI · %s #%s → %s" % (p, corps.fiche_id,
                                     corps.rvgi_numero or "détaché"))
    return {"ok": True, "perimetre": p, "fiche_id": corps.fiche_id,
            "rvgi_numero": corps.rvgi_numero, "par": _nom(user)}


@router.get("/candidats")
def candidats(request: Request, perimetre: str = Query("client", max_length=16),
              q: str = Query("", max_length=80), limite: int = Query(20, ge=1, le=60)):
    """Le sélecteur « lier à une fiche RVGI »."""
    require_superadmin(request)
    p = _perimetre(perimetre)
    if len(q.strip()) < 2:
        return {"candidats": []}
    try:
        return {"candidats": tiers.candidats(p, q, limite)}
    except FileNotFoundError as e:
        raise HTTPException(503, str(e))


@router.get("/rvgi-seuls")
def liste_rvgi_seuls(request: Request, perimetre: str = Query("client", max_length=16),
                     q: str = Query("", max_length=80),
                     inclure_bloques: bool = Query(False),
                     limite: int = Query(200, ge=1, le=1000)):
    """Les fiches de l'ERP qu'aucune fiche MySifa ne porte."""
    require_superadmin(request)
    p = _perimetre(perimetre)
    try:
        with get_db() as conn:
            return {"perimetre": p,
                    "lignes": tiers.rvgi_seuls(conn, p, q, limite, inclure_bloques)}
    except FileNotFoundError as e:
        raise HTTPException(503, str(e))


@router.post("/importer")
def importer(corps: ImportIn, request: Request):
    """Créer dans MySifa des fiches RVGI choisies une par une."""
    user = require_superadmin(request)
    p = _perimetre(corps.perimetre)
    voulus = {int(n) for n in (corps.numeros or [])}
    if not voulus:
        raise HTTPException(400, "Aucune fiche RVGI sélectionnée.")
    try:
        rvgi = {n: r for n, r in tiers.lire_rvgi(p).items() if n in voulus}
    except FileNotFoundError as e:
        raise HTTPException(503, str(e))
    if not rvgi:
        raise HTTPException(404, "Ces fiches ne sont pas dans le miroir de RVGI.")
    with get_db() as conn:
        # `inclure_bloques` : la sélection est explicite, on ne va pas refuser
        # une fiche que quelqu'un a cochée sciemment.
        n = tiers.importer_manquants(conn, p, rvgi, inclure_bloques=True)
        tiers.appliquer(conn, p, rvgi)
        conn.commit()
    _journal(request, user, "CREATE", "RVGI · %s · %d fiches importées" % (p, n))
    return {"ok": True, "importes": n, "par": _nom(user)}


@router.get("/fiche")
def fiche(request: Request, perimetre: str = Query("client", max_length=16),
          numero: int = Query(...)):
    """La fiche RVGI brute, telle quelle, pour la montrer à côté de MySifa."""
    require_superadmin(request)
    p = _perimetre(perimetre)
    try:
        r = tiers.fiche_rvgi(p, numero)
    except FileNotFoundError as e:
        raise HTTPException(503, str(e))
    if r is None:
        raise HTTPException(404, "Fiche RVGI introuvable.")
    return {"perimetre": p, "numero": numero, "fiche": r,
            "champs_pilotes": tiers.champs_pilotes(p)}


@router.get("/contacts")
def contacts(request: Request, numero: int = Query(...)):
    """Les interlocuteurs d'un fournisseur dans RVGI (`fic_foui`)."""
    require_superadmin(request)
    try:
        return {"numero": numero, "contacts": tiers.contacts_rvgi(numero)}
    except FileNotFoundError as e:
        raise HTTPException(503, str(e))


@router.get("/adresses")
def adresses(request: Request, numero: int = Query(...)):
    """Les adresses de livraison d'un client dans RVGI (`fic_clta`)."""
    require_superadmin(request)
    try:
        return {"numero": numero, "adresses": tiers.adresses_rvgi(numero)}
    except FileNotFoundError as e:
        raise HTTPException(503, str(e))

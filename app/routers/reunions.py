"""MySifa — Points de production : reunions et comptes-rendus (endpoints)."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

from config import CODE_ANNUL_DOS, CODE_DEBUT_DOS, CODE_FIN_DOS, ROLES_PROD
from database import get_db
from services.auth_service import effective_role, get_current_user
from app.services import rapport_dossier as rd
from app.services import reunion as rn

router = APIRouter()


def _autorise(request: Request) -> Dict[str, Any]:
    user = get_current_user(request)
    if effective_role(user) not in ROLES_PROD:
        raise HTTPException(status_code=403, detail="Acces reserve a la production.")
    return user


def _auteur(user: Dict[str, Any]) -> str:
    return str(user.get("nom") or user.get("email") or "?")


def _bornes(debut: str, fin: str) -> Dict[str, str]:
    return {"debut": f"{debut}T00:00:00", "fin": f"{fin}T23:59:59"}


def _detail_prod(conn, r: Dict[str, Any]) -> Dict[str, Any]:
    """Les chiffres de la plage — recalcules a chaque lecture, jamais figes.

    C'est le choix retenu : une reunion garde ses notes et ses decisions, pas
    ses chiffres. Rouverte plus tard, elle montre l'atelier tel qu'il apparait
    ce jour-la.
    """
    b = _bornes(r["date_debut"], r["date_fin"])
    # Une reunion peut regarder une machine, plusieurs, ou tout l'atelier.
    machine = rd.machines_demandees(r.get("machines") or r.get("machine") or "")
    dispo = rd.machines_periode(conn, b["debut"], b["fin"], CODE_FIN_DOS)
    hors = rd.postes_hors_production(conn)
    if not machine:
        # « Toutes » veut dire toutes les machines de PRODUCTION : un poste
        # marque hors production dans les Parametres n'a ni cycle ni compteur,
        # et ses chiffres n'ont pas le meme sens. Il reste dans le selecteur —
        # un clic le ramene — mais il n'entre pas par defaut. La liste est
        # resolue ici et pas dans le service : rien n'est retire en silence,
        # l'ecran affiche exactement le perimetre qu'il a demande.
        exclus = {m.strip().lower() for m in hors}
        machine = [m for m in dispo if m.strip().lower() not in exclus]
    return {
        "atelier": rd.retour_atelier(conn, machine, b["debut"], b["fin"],
                                     code_fin=CODE_FIN_DOS),
        "frise": rd.frise(conn, b["debut"], b["fin"], machine, code_fin=CODE_FIN_DOS,
                          code_debut=CODE_DEBUT_DOS, code_annul=CODE_ANNUL_DOS),
        "comptes_rendus": rd.comptes_rendus_periode(conn, b["debut"], b["fin"],
                                                    machine=machine,
                                                    code_fin=CODE_FIN_DOS),
        "machines": dispo,
        "machines_hors_production": hors,
    }


@router.get("/api/reunions")
def liste_reunions(request: Request, limite: int = 100):
    """Les reunions, la plus recente en tete."""
    _autorise(request)
    with get_db() as conn:
        return {"reunions": rn.liste(conn, limite)}


@router.get("/api/reunions/contexte")
def contexte(request: Request):
    """De quoi ouvrir la page : reunion en cours, plage proposee, participants."""
    user = _autorise(request)
    with get_db() as conn:
        ouverte = rn.ouverte_de(conn, _auteur(user))
        veille = (date.today() - timedelta(days=1)).isoformat()
        jour = rd.dernier_jour_saisi(conn, veille) or veille
        rows = conn.execute(
            """SELECT id, nom FROM users
                WHERE actif=1 AND TRIM(COALESCE(nom,'')) <> ''
                ORDER BY nom"""
        ).fetchall()
    return {
        "ouverte": ouverte,
        "jour_propose": jour,
        "titre_propose": rn.titre_par_defaut(),
        "personnes": [dict(r) for r in rows],
    }


@router.post("/api/reunions")
async def lancer_reunion(request: Request):
    """Ouvre un point de production sur une plage de dates."""
    user = _autorise(request)
    body = await request.json()
    with get_db() as conn:
        r = rn.lancer(
            conn, _auteur(user),
            str(body.get("date_debut") or ""), str(body.get("date_fin") or ""),
            str(body.get("titre") or ""), str(body.get("machine") or ""),
            [str(x) for x in (body.get("participants") or [])],
            [str(x) for x in (body.get("machines") or [])],
        )
    if not r:
        raise HTTPException(status_code=400, detail="Reunion non creee.")
    return r


@router.get("/api/reunions/{reunion_id}")
def detail_reunion(reunion_id: int, request: Request, avec_prod: bool = True):
    """Le compte-rendu, et les chiffres de sa plage."""
    _autorise(request)
    with get_db() as conn:
        r = rn.reunion(conn, reunion_id)
        if not r:
            raise HTTPException(status_code=404, detail="Reunion introuvable.")
        prod = _detail_prod(conn, r) if avec_prod else None
    return {"reunion": r, "prod": prod}


@router.post("/api/reunions/{reunion_id}")
async def enregistrer_reunion(reunion_id: int, request: Request):
    """Met a jour titre, notes, plage, machine ou participants."""
    user = _autorise(request)
    body = await request.json()
    parts = body.get("participants")
    machs = body.get("machines")
    with get_db() as conn:
        r = rn.enregistrer(
            conn, reunion_id, _auteur(user),
            titre=body.get("titre"), notes=body.get("notes"),
            date_debut=body.get("date_debut"), date_fin=body.get("date_fin"),
            machine=body.get("machine"),
            noms_machines=[str(x) for x in machs] if machs is not None else None,
            noms_participants=[str(x) for x in parts] if parts is not None else None,
        )
    if not r:
        raise HTTPException(status_code=404, detail="Reunion introuvable.")
    return r


@router.post("/api/reunions/{reunion_id}/clore")
async def clore_reunion(reunion_id: int, request: Request):
    """Clot le point, ou le rouvre. Clore ne verrouille rien."""
    user = _autorise(request)
    body = await request.json() if await request.body() else {}
    with get_db() as conn:
        r = rn.clore(conn, reunion_id, _auteur(user), bool(body.get("rouvrir", False)))
    if not r:
        raise HTTPException(status_code=404, detail="Reunion introuvable.")
    return r


@router.delete("/api/reunions/{reunion_id}")
def supprimer_reunion(reunion_id: int, request: Request):
    _autorise(request)
    with get_db() as conn:
        ok = rn.supprimer(conn, reunion_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Reunion introuvable.")
    return {"supprimee": True}


@router.post("/api/reunions/{reunion_id}/actions")
async def ajouter_action(reunion_id: int, request: Request):
    """Une action : un quoi, un qui, un pour quand. Le quoi suffit."""
    _autorise(request)
    body = await request.json()
    with get_db() as conn:
        a = rn.ajouter_action(conn, reunion_id, str(body.get("texte") or ""),
                              str(body.get("responsable") or ""),
                              str(body.get("echeance") or ""))
    if not a:
        raise HTTPException(status_code=400, detail="Action vide ou reunion introuvable.")
    return a


@router.post("/api/reunions/actions/{action_id}")
async def modifier_action(action_id: int, request: Request):
    """Corrige une action ou la coche. Un texte vide la supprime."""
    user = _autorise(request)
    body = await request.json()
    fait = body.get("fait")
    with get_db() as conn:
        a = rn.modifier_action(conn, action_id, _auteur(user),
                               texte=body.get("texte"),
                               responsable=body.get("responsable"),
                               echeance=body.get("echeance"),
                               fait=None if fait is None else bool(fait))
    return {"action": a, "supprimee": a is None}

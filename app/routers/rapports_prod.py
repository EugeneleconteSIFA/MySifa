"""MySifa — Comptes-rendus de dossier et retour a l'atelier (endpoints)."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request

from config import CODE_DEBUT_DOS, CODE_FIN_DOS, ROLES_PROD
from database import get_db
from services.auth_service import effective_role, get_current_user
from app.services import rapport_dossier as rd

router = APIRouter()

_JOURS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")


def _autorise(request: Request) -> Dict[str, Any]:
    user = get_current_user(request)
    if effective_role(user) not in ROLES_PROD:
        raise HTTPException(status_code=403, detail="Acces reserve a la production.")
    return user


def _bornes(mode: str = "jour", jour: Optional[str] = None,
            year: Optional[int] = None, week: Optional[int] = None) -> Dict[str, Any]:
    """Bornes '%Y-%m-%dT%H:%M:%S' de la periode demandee.

    Deux modes, parce que les deux usages n'ont pas la meme maille :
    - `jour`    : le point de production du matin regarde la veille ;
    - `semaine` : la feuille affichee a la machine couvre la semaine ISO,
      avec la meme definition que le rapport hebdomadaire (lundi -> dimanche).

    Defaut : la veille. C'est la vue qu'on ouvre le plus souvent.
    """
    mode = (mode or "jour").strip().lower()

    if mode == "semaine":
        if not year or not week:
            precedente = date.today() - timedelta(days=7)
            y, w, _ = precedente.isocalendar()
            year, week = int(y), int(w)
        try:
            debut_j = date.fromisocalendar(int(year), int(week), 1)
        except ValueError:
            raise HTTPException(status_code=400, detail="Semaine ISO invalide.")
        fin_j = debut_j + timedelta(days=6)
        label = f"Semaine {int(week)} ({int(year)})"
    else:
        mode = "jour"
        if jour:
            try:
                debut_j = datetime.strptime(jour.strip()[:10], "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Date invalide (attendu AAAA-MM-JJ).")
        else:
            debut_j = date.today() - timedelta(days=1)
        fin_j = debut_j
        y, w, _ = debut_j.isocalendar()
        year, week = int(y), int(w)
        label = f"{_JOURS[debut_j.weekday()].capitalize()} {debut_j.strftime('%d/%m/%Y')}"

    return {
        "mode": mode,
        "year": int(year), "week": int(week),
        "jour": debut_j.isoformat(),
        "debut": debut_j.strftime("%Y-%m-%dT00:00:00"),
        "fin": fin_j.strftime("%Y-%m-%dT23:59:59"),
        "label": label,
        "du": debut_j.strftime("%d/%m/%Y"), "au": fin_j.strftime("%d/%m/%Y"),
    }


@router.get("/api/rapports-prod/periode")
def periode(request: Request, mode: str = "jour", jour: str | None = None,
            year: int | None = None, week: int | None = None):
    """Bornes de la periode visee et machines qui y ont cloture un dossier."""
    _autorise(request)
    b = _bornes(mode, jour, year, week)
    with get_db() as conn:
        machines = rd.machines_periode(conn, b["debut"], b["fin"], CODE_FIN_DOS)
    return {**b, "machines": machines}


@router.get("/api/rapports-prod/comptes-rendus")
def liste_comptes_rendus(request: Request, mode: str = "jour", jour: str | None = None,
                         year: int | None = None, week: int | None = None,
                         machine: str = "", limite: int = 200):
    """Les comptes-rendus de la periode, en projection compacte."""
    _autorise(request)
    b = _bornes(mode, jour, year, week)
    with get_db() as conn:
        lignes = rd.comptes_rendus_periode(
            conn, b["debut"], b["fin"], machine=machine or "",
            code_fin=CODE_FIN_DOS, limite=int(limite),
        )
    return {"periode": b, "machine": machine or "", "lignes": lignes}


@router.get("/api/rapports-prod/recherche")
def recherche(request: Request, q: str = "", limite: int = 20):
    """N'importe quel dossier portant des saisies — sans condition de date."""
    _autorise(request)
    terme = (q or "").strip()
    if len(terme) < 2:
        return {"dossiers": [], "total": 0}
    with get_db() as conn:
        found = rd.rechercher_dossiers(conn, terme, limite=int(limite), code_fin=CODE_FIN_DOS)
    return {"dossiers": found, "total": len(found)}


@router.get("/api/rapports-prod/retour-atelier")
def retour_atelier(request: Request, machine: str = "", mode: str = "jour",
                   jour: str | None = None, year: int | None = None,
                   week: int | None = None):
    """Le retour d'une periode pour une machine — matiere de la feuille atelier."""
    _autorise(request)
    if not (machine or "").strip():
        raise HTTPException(status_code=400, detail="Machine non precisee.")
    b = _bornes(mode, jour, year, week)
    with get_db() as conn:
        data = rd.retour_atelier(conn, machine.strip(), b["debut"], b["fin"],
                                 code_fin=CODE_FIN_DOS)
    return {**data, "periode": b}


def _auteur(user: Dict[str, Any]) -> str:
    """Meme convention que produits_memoire : le nom, sinon l'email."""
    return str(user.get("nom") or user.get("email") or "?")


@router.post("/api/rapports-prod/dossier/{no_dossier:path}/info-prod")
async def ecrire_info_prod(no_dossier: str, request: Request):
    """Saisit ou corrige l'info prod d'un dossier, depuis le compte-rendu.

    L'info prod est obligatoire a la cloture, mais elle est parfois oubliee, ou
    ecrite trop vite. Le compte-rendu est l'endroit ou le manque se voit — donc
    l'endroit ou il doit pouvoir se combler, sans renvoyer vers la Tracabilite.
    Meme regle qu'ailleurs : un texte vide efface la ligne, et le dernier
    auteur est conserve.
    """
    user = _autorise(request)
    body = await request.json()
    texte = str(body.get("texte") or "")
    from app.services import produit_memoire as pm
    with get_db() as conn:
        ligne = pm.enregistrer_info_prod(conn, no_dossier, texte, _auteur(user))
    return {"no_dossier": no_dossier, "info_prod": ligne}


@router.post("/api/rapports-prod/seuil/{saisie_id}/explication")
async def ecrire_explication(saisie_id: int, request: Request):
    """Explique apres coup un seuil d'arret franchi.

    La feuille atelier signale les seuils « sans explication — a poser au point
    de production ». C'est bien la qu'on obtient la reponse : elle se saisit
    donc ici, et la ligne cesse d'etre en attente.
    """
    user = _autorise(request)
    body = await request.json()
    texte = str(body.get("texte") or "").strip()
    if not texte:
        raise HTTPException(status_code=400, detail="Explication vide.")
    from app.services import arret_seuils as asv
    with get_db() as conn:
        n = asv.enregistrer_explication(conn, int(saisie_id), texte)
        conn.commit()
    if not n:
        raise HTTPException(status_code=404,
                            detail="Aucun franchissement rattache a cette saisie.")
    return {"saisie_id": int(saisie_id), "lignes": n, "par": _auteur(user)}


@router.get("/api/rapports-prod/dossier/{no_dossier:path}")
def compte_rendu_dossier(no_dossier: str, request: Request):
    """Le compte-rendu complet d'un dossier, clot ou non, quelle que soit sa date."""
    _autorise(request)
    with get_db() as conn:
        cr = rd.compte_rendu(conn, no_dossier,
                             code_fin=CODE_FIN_DOS, code_debut=CODE_DEBUT_DOS)
    if not cr.get("existe"):
        raise HTTPException(status_code=404,
                            detail=f"Aucune saisie pour le dossier {no_dossier}.")
    return cr

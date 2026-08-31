"""MySifa — Comptes-rendus de dossier et retour a l'atelier (endpoints)."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request

from config import CODE_ANNUL_DOS, CODE_DEBUT_DOS, CODE_FIN_DOS, ROLES_PROD
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


def _jour_ou_400(valeur: str, champ: str) -> date:
    try:
        return datetime.strptime(valeur.strip()[:10], "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400,
                            detail=f"{champ} invalide (attendu AAAA-MM-JJ).")


def _bornes(mode: str = "jour", jour: Optional[str] = None,
            year: Optional[int] = None, week: Optional[int] = None,
            du: Optional[str] = None, au: Optional[str] = None) -> Dict[str, Any]:
    """Bornes '%Y-%m-%dT%H:%M:%S' de la periode demandee.

    Trois modes, parce que les usages n'ont pas la meme maille :
    - `plage`   : deux dates libres. C'est ce que l'onglet MyProd envoie, parce
      qu'il lit la barre de filtres de la page Production plutot que d'avoir
      ses propres selecteurs — un ecran qui redemande ce que la page sait deja
      n'est pas emboite, il est pose a cote ;
    - `jour`    : une journee. Le point de production du matin regarde la veille ;
    - `semaine` : la semaine ISO (lundi -> dimanche), maille de la feuille
      affichee a la machine.

    Defaut : la veille.
    """
    mode = (mode or "jour").strip().lower()

    if mode == "plage":
        if not du and not au:
            mode = "jour"
        else:
            debut_j = _jour_ou_400(du, "Date de debut") if du else _jour_ou_400(au, "Date de fin")
            fin_j = _jour_ou_400(au, "Date de fin") if au else debut_j
            if fin_j < debut_j:
                debut_j, fin_j = fin_j, debut_j
            y, w, _ = debut_j.isocalendar()
            label = (f"{_JOURS[debut_j.weekday()].capitalize()} {debut_j.strftime('%d/%m/%Y')}"
                     if debut_j == fin_j
                     else f"Du {debut_j.strftime('%d/%m/%Y')} au {fin_j.strftime('%d/%m/%Y')}")
            return {
                "mode": "plage", "year": int(y), "week": int(w),
                "jour": debut_j.isoformat(),
                "debut": debut_j.strftime("%Y-%m-%dT00:00:00"),
                "fin": fin_j.strftime("%Y-%m-%dT23:59:59"),
                "label": label,
                "du": debut_j.strftime("%d/%m/%Y"), "au": fin_j.strftime("%d/%m/%Y"),
            }

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
            year: int | None = None, week: int | None = None,
            du: str | None = None, au: str | None = None):
    """Bornes de la periode visee et machines qui y ont cloture un dossier."""
    _autorise(request)
    b = _bornes(mode, jour, year, week, du, au)
    with get_db() as conn:
        machines = rd.machines_periode(conn, b["debut"], b["fin"], CODE_FIN_DOS)
    return {**b, "machines": machines}


@router.get("/api/rapports-prod/comptes-rendus")
def liste_comptes_rendus(request: Request, mode: str = "jour", jour: str | None = None,
                         year: int | None = None, week: int | None = None,
                         du: str | None = None, au: str | None = None,
                         machine: str = "", limite: int = 200):
    """Les comptes-rendus de la periode, en projection compacte."""
    _autorise(request)
    b = _bornes(mode, jour, year, week, du, au)
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
                   week: int | None = None, du: str | None = None,
                   au: str | None = None):
    """Le retour d'une periode pour une machine — matiere de la feuille atelier."""
    _autorise(request)
    # machine vide = toutes les machines de la periode. Une feuille « atelier »
    # a du sens meme sans machine : c'est la journee de l'atelier.
    b = _bornes(mode, jour, year, week, du, au)
    with get_db() as conn:
        data = rd.retour_atelier(conn, (machine or "").strip(), b["debut"], b["fin"],
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


@router.post("/api/rapports-prod/ecrit/valider")
async def valider_ecrit(request: Request):
    """Marque une remontee comme traitee, ou revient dessus.

    Valider n'efface rien : la remontee reste affichee, marquee. Ce qui
    disparait de l'ecran n'est jamais relu.
    """
    user = _autorise(request)
    body = await request.json()
    cle = str(body.get("cle") or "").strip()
    if not cle:
        raise HTTPException(status_code=400, detail="Remontee non precisee.")
    with get_db() as conn:
        etat = rd.valider_ecrit(conn, cle, str(body.get("no_dossier") or ""),
                                bool(body.get("valide", True)), _auteur(user))
    return etat


@router.post("/api/rapports-prod/ecrit/masquer")
async def masquer_ecrit(request: Request):
    """Sort une remontee hors sujet de la liste, sans rien effacer.

    Masquer n'est pas valider : « 10h » n'a pas ete traite, il n'y avait rien a
    traiter.
    """
    user = _autorise(request)
    body = await request.json()
    cle = str(body.get("cle") or "").strip()
    if not cle:
        raise HTTPException(status_code=400, detail="Remontee non precisee.")
    with get_db() as conn:
        etat = rd.masquer_ecrit(conn, cle, str(body.get("no_dossier") or ""),
                                bool(body.get("masque", True)), _auteur(user))
    return etat


@router.get("/api/rapports-prod/frise")
def frise(request: Request, machine: str = "", mode: str = "jour",
          jour: str | None = None, year: int | None = None,
          week: int | None = None, du: str | None = None, au: str | None = None):
    """La frise de production de la periode : une ligne par machine."""
    _autorise(request)
    b = _bornes(mode, jour, year, week, du, au)
    with get_db() as conn:
        data = rd.frise(conn, b["debut"], b["fin"], (machine or "").strip(),
                        code_fin=CODE_FIN_DOS, code_debut=CODE_DEBUT_DOS,
                        code_annul=CODE_ANNUL_DOS)
    return {**data, "periode": b}


@router.post("/api/rapports-prod/dossier/{no_dossier:path}/note")
async def ajouter_note(no_dossier: str, request: Request):
    """Ajoute un commentaire sur le dossier, ou en reponse a une remontee."""
    user = _autorise(request)
    body = await request.json()
    texte = str(body.get("texte") or "").strip()
    if not texte:
        raise HTTPException(status_code=400, detail="Commentaire vide.")
    with get_db() as conn:
        note = rd.ajouter_note(conn, no_dossier, texte, _auteur(user),
                               str(body.get("cle_reponse") or ""))
    if not note:
        raise HTTPException(status_code=400, detail="Commentaire non enregistre.")
    return note


@router.post("/api/rapports-prod/note/{note_id}")
async def modifier_note(note_id: int, request: Request):
    """Corrige un commentaire ajoute ici. Un texte vide le supprime."""
    user = _autorise(request)
    body = await request.json()
    with get_db() as conn:
        note = rd.modifier_note(conn, int(note_id), str(body.get("texte") or ""), _auteur(user))
    return {"note": note, "supprimee": note is None}


@router.post("/api/rapports-prod/saisie/{saisie_id}/commentaire")
async def modifier_commentaire(saisie_id: int, request: Request):
    """Corrige le commentaire porte par une saisie de production."""
    _autorise(request)
    body = await request.json()
    with get_db() as conn:
        ok = rd.modifier_commentaire_saisie(conn, int(saisie_id), str(body.get("texte") or ""))
    if not ok:
        raise HTTPException(status_code=404, detail="Saisie introuvable.")
    return {"saisie_id": int(saisie_id), "ok": True}


@router.get("/api/rapports-prod/dossier/{no_dossier:path}")
def compte_rendu_dossier(no_dossier: str, request: Request):
    """Le compte-rendu complet d'un dossier, clot ou non, quelle que soit sa date."""
    _autorise(request)
    with get_db() as conn:
        cr = rd.compte_rendu(conn, no_dossier, code_fin=CODE_FIN_DOS,
                             code_debut=CODE_DEBUT_DOS, code_annul=CODE_ANNUL_DOS)
    if not cr.get("existe"):
        raise HTTPException(status_code=404,
                            detail=f"Aucune saisie pour le dossier {no_dossier}.")
    return cr

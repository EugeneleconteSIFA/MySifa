"""MySifa — Comptes-rendus de dossier et retour a l'atelier (endpoints)."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request

from config import CODE_DEBUT_DOS, CODE_FIN_DOS, ROLES_PROD
from database import get_db
from services.auth_service import effective_role, get_current_user
from app.services import rapport_dossier as rd

router = APIRouter()


def _autorise(request: Request) -> Dict[str, Any]:
    user = get_current_user(request)
    if effective_role(user) not in ROLES_PROD:
        raise HTTPException(status_code=403, detail="Acces reserve a la production.")
    return user


def _bornes_semaine(year: Optional[int], week: Optional[int]) -> Dict[str, Any]:
    """Bornes '%Y-%m-%dT%H:%M:%S' d'une semaine ISO. Defaut : semaine passee.

    Meme definition de la semaine que le rapport hebdomadaire — lundi 00:00:00
    au dimanche 23:59:59.
    """
    if not year or not week:
        precedente = date.today() - timedelta(days=7)
        y, w, _ = precedente.isocalendar()
        year, week = int(y), int(w)
    try:
        lundi = date.fromisocalendar(int(year), int(week), 1)
    except ValueError:
        raise HTTPException(status_code=400, detail="Semaine ISO invalide.")
    dimanche = lundi + timedelta(days=6)
    return {
        "year": int(year), "week": int(week),
        "debut": lundi.strftime("%Y-%m-%dT00:00:00"),
        "fin": dimanche.strftime("%Y-%m-%dT23:59:59"),
        "label": f"Semaine {int(week)} ({int(year)})",
        "du": lundi.strftime("%d/%m/%Y"), "au": dimanche.strftime("%d/%m/%Y"),
    }


@router.get("/api/rapports-prod/semaine")
def semaine_courante(request: Request, year: int | None = None, week: int | None = None):
    """Bornes de la semaine visee et machines qui ont cloture un dossier."""
    _autorise(request)
    bornes = _bornes_semaine(year, week)
    with get_db() as conn:
        machines = rd.machines_periode(conn, bornes["debut"], bornes["fin"], CODE_FIN_DOS)
    return {**bornes, "machines": machines}


@router.get("/api/rapports-prod/comptes-rendus")
def liste_comptes_rendus(request: Request, year: int | None = None,
                         week: int | None = None, machine: str = "",
                         limite: int = 200):
    """Les comptes-rendus de la periode, en projection compacte."""
    _autorise(request)
    bornes = _bornes_semaine(year, week)
    with get_db() as conn:
        lignes = rd.comptes_rendus_periode(
            conn, bornes["debut"], bornes["fin"],
            machine=machine or "", code_fin=CODE_FIN_DOS, limite=int(limite),
        )
    return {"semaine": bornes, "machine": machine or "", "lignes": lignes}


@router.get("/api/rapports-prod/dossier/{no_dossier:path}")
def compte_rendu_dossier(no_dossier: str, request: Request):
    """Le compte-rendu complet d'un dossier."""
    _autorise(request)
    with get_db() as conn:
        cr = rd.compte_rendu(conn, no_dossier,
                             code_fin=CODE_FIN_DOS, code_debut=CODE_DEBUT_DOS)
    if not cr.get("existe"):
        raise HTTPException(status_code=404,
                            detail=f"Aucune saisie pour le dossier {no_dossier}.")
    return cr


@router.get("/api/rapports-prod/retour-atelier")
def retour_atelier(request: Request, machine: str = "", year: int | None = None,
                   week: int | None = None):
    """Le retour d'une semaine pour une machine — matiere de la feuille atelier."""
    _autorise(request)
    if not (machine or "").strip():
        raise HTTPException(status_code=400, detail="Machine non precisee.")
    bornes = _bornes_semaine(year, week)
    with get_db() as conn:
        data = rd.retour_atelier(conn, machine.strip(), bornes["debut"],
                                 bornes["fin"], code_fin=CODE_FIN_DOS)
    return {**data, "semaine": bornes}

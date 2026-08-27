"""
Seuils d'arret — API de configuration et de lecture.

La configuration suit la regle du projet : rien de specifique a SIFA n'est
ecrit dans le code. Les seuils sont un referentiel metier, donc une table,
donc un CRUD accessible aux memes roles que les alertes maintenance — ceux
qui reglent deja ce que l'atelier voit a l'ecran.

La lecture, elle, est ouverte a tous : un franchissement de seuil n'est pas
une donnee sensible, c'est la matiere du point de production.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from database import get_db
from app.services.audit_service import log_action
from app.services.auth_service import get_current_user
from app.services import arret_seuils as svc

router = APIRouter()

_CIBLE_TYPES = ("code", "categorie", "defaut")
_MODES = ("permanent", "repetition")


def _require_admin(request: Request) -> dict:
    from app.routers.settings import _require_alerts_admin
    return _require_alerts_admin(request)


class SeuilIn(BaseModel):
    cible_type: str
    cible: str = ""
    machine: Optional[str] = None
    mode: str
    repetitions: int = 0
    libelle: Optional[str] = None
    actif: bool = True


class ParamsIn(BaseModel):
    duree_unitaire_min: Optional[float] = None
    duree_cumul_min: Optional[float] = None


def _valider(body: SeuilIn) -> None:
    if body.cible_type not in _CIBLE_TYPES:
        raise HTTPException(400, "Cible invalide — code, categorie ou defaut.")
    if body.mode not in _MODES:
        raise HTTPException(400, "Mode invalide — permanent ou repetition.")
    if body.cible_type != "defaut" and not (body.cible or "").strip():
        raise HTTPException(400, "Cible manquante.")
    if body.mode == "repetition" and not (2 <= int(body.repetitions) <= 50):
        raise HTTPException(400, "Repetitions invalides — valeur entre 2 et 50.")


# ─── Configuration ───────────────────────────────────────────────────────────

@router.get("/api/arret-seuils/config")
def lire_config(request: Request):
    get_current_user(request)
    with get_db() as conn:
        regles = svc.charger_regles(conn)
        params = svc.charger_params(conn)
    return {
        "regles": regles,
        "params": {
            "duree_unitaire_min": params["duree_unitaire_min"],
            "duree_cumul_min": params["duree_cumul_min"],
        },
        "categories_surveillees": sorted(params["categories_surveillees"]),
    }


@router.post("/api/arret-seuils/regles")
def creer_regle(body: SeuilIn, request: Request):
    user = _require_admin(request)
    _valider(body)
    now = datetime.now().isoformat(timespec="seconds")
    machine = (body.machine or "").strip() or None
    with get_db() as conn:
        exist = conn.execute(
            """SELECT id FROM arret_seuils
               WHERE cible_type=? AND cible=? AND COALESCE(machine,'')=?""",
            (body.cible_type, body.cible.strip(), machine or ""),
        ).fetchone()
        if exist:
            raise HTTPException(400, "Une regle existe deja pour cette cible.")
        cur = conn.execute(
            """INSERT INTO arret_seuils
               (cible_type, cible, machine, mode, repetitions, libelle, actif,
                created_at, updated_at, updated_par)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (body.cible_type, body.cible.strip(), machine, body.mode,
             int(body.repetitions), (body.libelle or "").strip() or None,
             1 if body.actif else 0, now, now, user.get("nom")),
        )
        conn.commit()
        new_id = cur.lastrowid
    log_action(user=user, action="CREATE", module="settings",
               objet=f"Seuil arret {body.cible_type}:{body.cible or 'defaut'}",
               ip=request.client.host if request.client else None)
    return {"success": True, "id": new_id}


@router.put("/api/arret-seuils/regles/{regle_id}")
def modifier_regle(regle_id: int, body: SeuilIn, request: Request):
    user = _require_admin(request)
    _valider(body)
    now = datetime.now().isoformat(timespec="seconds")
    machine = (body.machine or "").strip() or None
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM arret_seuils WHERE id=?", (regle_id,)).fetchone():
            raise HTTPException(404, "Regle introuvable.")
        conn.execute(
            """UPDATE arret_seuils
               SET cible_type=?, cible=?, machine=?, mode=?, repetitions=?,
                   libelle=?, actif=?, updated_at=?, updated_par=?
               WHERE id=?""",
            (body.cible_type, body.cible.strip(), machine, body.mode,
             int(body.repetitions), (body.libelle or "").strip() or None,
             1 if body.actif else 0, now, user.get("nom"), regle_id),
        )
        conn.commit()
    log_action(user=user, action="UPDATE", module="settings",
               objet=f"Seuil arret #{regle_id}",
               ip=request.client.host if request.client else None)
    return {"success": True}


@router.delete("/api/arret-seuils/regles/{regle_id}")
def supprimer_regle(regle_id: int, request: Request):
    user = _require_admin(request)
    with get_db() as conn:
        row = conn.execute("SELECT * FROM arret_seuils WHERE id=?", (regle_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Regle introuvable.")
        if row["cible_type"] == "defaut":
            raise HTTPException(400, "La regle par defaut ne peut pas etre supprimee.")
        conn.execute("DELETE FROM arret_seuils WHERE id=?", (regle_id,))
        conn.commit()
    log_action(user=user, action="DELETE", module="settings",
               objet=f"Seuil arret #{regle_id}",
               ip=request.client.host if request.client else None)
    return {"success": True}


@router.put("/api/arret-seuils/params")
def modifier_params(body: ParamsIn, request: Request):
    user = _require_admin(request)
    maj: List[tuple] = []
    if body.duree_unitaire_min is not None:
        if not (5 <= body.duree_unitaire_min <= 480):
            raise HTTPException(400, "Duree invalide — valeur entre 5 et 480 minutes.")
        maj.append(("duree_unitaire_min", str(float(body.duree_unitaire_min))))
    if body.duree_cumul_min is not None:
        if not (5 <= body.duree_cumul_min <= 960):
            raise HTTPException(400, "Duree invalide — valeur entre 5 et 960 minutes.")
        maj.append(("duree_cumul_min", str(float(body.duree_cumul_min))))
    if not maj:
        return {"success": True}
    with get_db() as conn:
        for cle, valeur in maj:
            conn.execute(
                """INSERT INTO arret_seuils_params (cle, valeur) VALUES (?,?)
                   ON CONFLICT(cle) DO UPDATE SET valeur=excluded.valeur""",
                (cle, valeur),
            )
        conn.commit()
    log_action(user=user, action="UPDATE", module="settings",
               objet="Seuils arret — durees",
               ip=request.client.host if request.client else None)
    return {"success": True}


# ─── Lecture ─────────────────────────────────────────────────────────────────

@router.get("/api/arret-seuils/franchis")
def lire_franchis(request: Request, depuis: str | None = None,
                  jusqu_a: str | None = None, jours: int = 7):
    """Les seuils franchis sur une periode. Par defaut, les 7 derniers jours."""
    get_current_user(request)
    if depuis and jusqu_a:
        debut, fin = depuis, jusqu_a + "T23:59:59"
    else:
        n = max(1, min(int(jours or 7), 120))
        debut = (date.today() - timedelta(days=n - 1)).isoformat()
        fin = date.today().isoformat() + "T23:59:59"
    with get_db() as conn:
        rows = svc.franchissements(conn, debut, fin)
    return {
        "debut": debut, "fin": fin,
        "total": len(rows),
        "sans_explication": sum(1 for r in rows if r.get("explication_exigee")),
        "franchis": rows,
    }

"""API de l'app ADV (/adv) — carnet de commandes et préparations.

Lecture : le carnet RVGI (miroir, lecture seule) croisé avec MySifa, calculé
par `app/services/adv_commandes.py`.

Écriture, dans la base MySifa uniquement — jamais dans RVGI :
- l'état d'une préparation (`adv_prepas`), par la logistique ;
- une étape de la chaîne fixée à la main (`adv_forcages`), par l'ADV.

Une ligne de commande se désigne par sa clé métier `numero` + `ligne`, comme
dans `rvgi_rattachements` : l'id du miroir change à chaque synchro.
"""

import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services import adv_commandes as adv
from app.services import adv_mise_en_forme as mef
from app.services.audit_service import log_action
from services.auth_service import effective_role, get_current_user
from config import ADV_ETATS, ADV_PREPA_STATUTS, ROLES_ADV, ROLES_ADV_PREPA
from database import get_db

router = APIRouter()

_RE_NUMERO = re.compile(r"^\d{1,12}$")
_LIB_PREPA = dict(ADV_PREPA_STATUTS)
_LIB_ETAT = dict(ADV_ETATS)


def _exiger(request: Request, roles) -> dict:
    user = get_current_user(request)
    if effective_role(user) not in roles:
        raise HTTPException(status_code=403, detail="Accès réservé au service ADV.")
    return user


def _cle(numero: str, ligne: int):
    if not _RE_NUMERO.match(str(numero or "")):
        raise HTTPException(status_code=400, detail="Numéro de commande invalide.")
    if not (0 <= int(ligne) <= 9999):
        raise HTTPException(status_code=400, detail="Ligne de commande invalide.")
    return str(numero), int(ligne)


def _nom(user: dict) -> str:
    return (user.get("nom") or user.get("email") or "").strip()


def _servir(fn, *args):
    try:
        return fn(*args)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/api/adv/commandes")
def commandes(request: Request):
    # Le carnet complet est à l'ADV et à la direction ; la logistique et
    # l'expédition n'ont que l'onglet Prépa (/api/adv/prepa).
    _exiger(request, ROLES_ADV)
    data = _servir(adv.construire)
    data["droits"] = {"adv": True, "prepa": True}
    # Les règles de couleur voyagent avec le carnet : une requête, pas deux.
    with get_db() as conn:
        data["mises_en_forme"] = mef.lister(conn)
    return data


@router.get("/api/adv/prepa")
def prepa(request: Request, horizon: Optional[int] = None):
    user = _exiger(request, ROLES_ADV_PREPA)
    data = _servir(adv.prepa, None, horizon)
    data["droits"] = {"adv": effective_role(user) in ROLES_ADV, "prepa": True}
    return data


class PrepaIn(BaseModel):
    statut: str
    note: Optional[str] = None


@router.put("/api/adv/prepa/{numero}/{ligne}")
def maj_prepa(numero: str, ligne: int, body: PrepaIn, request: Request):
    user = _exiger(request, ROLES_ADV_PREPA)
    numero, ligne = _cle(numero, ligne)
    if body.statut not in _LIB_PREPA:
        raise HTTPException(status_code=400, detail="Statut de préparation inconnu.")
    note = (body.note or "").strip()[:500] or None
    quand = adv.maintenant()
    with get_db() as conn:
        avant = conn.execute(
            "SELECT statut, note FROM adv_prepas WHERE numero=? AND ligne=?",
            (numero, ligne)).fetchone()
        conn.execute("""
            INSERT INTO adv_prepas (numero, ligne, statut, note, maj_le, maj_par)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(numero, ligne) DO UPDATE SET
                statut=excluded.statut, note=excluded.note,
                maj_le=excluded.maj_le, maj_par=excluded.maj_par
        """, (numero, ligne, body.statut, note, quand, _nom(user)))
        conn.commit()
    log_action(user=user, action="UPDATE", module="adv",
               objet="Prépa · commande %s ligne %s → %s" % (numero, ligne, _LIB_PREPA[body.statut]),
               detail={"avant": dict(avant) if avant else None,
                       "apres": {"statut": body.statut, "note": note}},
               request=request)
    return {"ok": True, "statut": body.statut, "maj_le": quand, "maj_par": _nom(user)}


class ForcageIn(BaseModel):
    valeur: Optional[str] = None     # None ou "" : on rend la main au calcul
    note: Optional[str] = None


@router.put("/api/adv/forcage/{numero}/{ligne}/{etape}")
def forcer(numero: str, ligne: int, etape: str, body: ForcageIn, request: Request):
    user = _exiger(request, ROLES_ADV)
    numero, ligne = _cle(numero, ligne)
    if etape not in adv.ETAPES:
        raise HTTPException(status_code=400, detail="Étape inconnue.")
    valeur = (body.valeur or "").strip() or None
    if valeur and valeur not in _LIB_ETAT:
        raise HTTPException(status_code=400, detail="Valeur inconnue.")
    note = (body.note or "").strip()[:500] or None
    quand = adv.maintenant()
    with get_db() as conn:
        avant = conn.execute(
            "SELECT valeur, note FROM adv_forcages WHERE numero=? AND ligne=? AND etape=?",
            (numero, ligne, etape)).fetchone()
        if valeur:
            conn.execute("""
                INSERT INTO adv_forcages (numero, ligne, etape, valeur, note, maj_le, maj_par)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(numero, ligne, etape) DO UPDATE SET
                    valeur=excluded.valeur, note=excluded.note,
                    maj_le=excluded.maj_le, maj_par=excluded.maj_par
            """, (numero, ligne, etape, valeur, note, quand, _nom(user)))
        else:
            conn.execute("DELETE FROM adv_forcages WHERE numero=? AND ligne=? AND etape=?",
                         (numero, ligne, etape))
        conn.commit()
    log_action(user=user, action="UPDATE" if valeur else "DELETE", module="adv",
               objet="Étape %s · commande %s ligne %s%s" % (
                   etape, numero, ligne, (" → " + _LIB_ETAT[valeur]) if valeur else " · calcul rétabli"),
               detail={"avant": dict(avant) if avant else None,
                       "apres": {"valeur": valeur, "note": note} if valeur else None},
               request=request)
    return {"ok": True}


# ── Mise en forme conditionnelle du carnet ───────────────────────────────────

@router.get("/api/adv/mises-en-forme")
def mises_en_forme(request: Request):
    _exiger(request, ROLES_ADV)
    with get_db() as conn:
        return {"regles": mef.lister(conn), "referentiel": mef.referentiel()}


class MisesEnFormeIn(BaseModel):
    regles: list


@router.put("/api/adv/mises-en-forme")
def enregistrer_mises_en_forme(body: MisesEnFormeIn, request: Request):
    """Remplace le jeu de règles commun au service."""
    user = _exiger(request, ROLES_ADV)
    try:
        regles = mef.valider(body.regles)
    except mef.RegleInvalide as e:
        raise HTTPException(status_code=400, detail=str(e))
    with get_db() as conn:
        avant = mef.lister(conn)
        apres = mef.enregistrer(conn, regles, adv.maintenant(), _nom(user))
    log_action(user=user, action="UPDATE", module="adv",
               objet="Mise en forme du carnet · %d règle(s)" % len(apres),
               detail={"avant": [{k: r[k] for k in ("colonne", "operateur", "cible", "valeur", "ton")} for r in avant],
                       "apres": regles},
               request=request)
    return {"regles": apres}

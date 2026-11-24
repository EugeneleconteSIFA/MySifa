"""API de l'app ADV (/adv) — carnet de commandes et préparations.

Lecture : le carnet RVGI (miroir, lecture seule) croisé avec MySifa, calculé
par `app/services/adv_commandes.py`.

Écriture, dans la base MySifa uniquement — jamais dans RVGI :
- l'état d'une préparation (`adv_prepas`), par la logistique ;
- une étape de la chaîne fixée à la main (`adv_forcages`), par l'ADV ;
- une préparation marquée « urgente » (`adv_urgences`), par l'ADV.

Une ligne de commande se désigne par sa clé métier `numero` + `ligne`, comme
dans `rvgi_rattachements` : l'id du miroir change à chaque synchro.
"""

import json
import re
import time
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services import adv_commandes as adv
from app.services import adv_mise_en_forme as mef
from app.services.audit_service import log_action
from services.auth_service import effective_role, get_current_user
from config import ADV_ETATS, ADV_PREPA_STATUTS, ADV_REPIQUAGE_STATUTS, ROLES_ADV, ROLES_ADV_PREPA
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
    user = _exiger(request, ROLES_ADV)
    data = _servir(adv.construire)
    data["droits"] = {"adv": True, "prepa": True}
    # Les règles de couleur et l'ordre des colonnes de la personne voyagent
    # avec le carnet : une requête, pas trois.
    with get_db() as conn:
        data["mises_en_forme"] = mef.lister(conn)
        data["colonnes_ordre"] = _ordre_colonnes(conn, user)
    return data


@router.get("/api/adv/prepa")
def prepa(request: Request, horizon: Optional[int] = None):
    user = _exiger(request, ROLES_ADV_PREPA)
    data = _servir(adv.prepa, None, horizon)
    data["droits"] = {"adv": effective_role(user) in ROLES_ADV, "prepa": True}
    return data


@router.get("/api/adv/prepa/historique")
def historique_prepa(request: Request, jours: int = 30):
    """Les préparations passées « Prête » ces derniers jours, même parties."""
    _exiger(request, ROLES_ADV_PREPA)
    if jours not in adv.HISTORIQUE_JOURS:
        jours = 30
    return _servir(adv.historique_prepa, jours)


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


# ── Ordre des préparations fixé à la main ────────────────────────────────────
# L'administration et la direction (ROLES_ADV) imposent l'ordre ; la logistique
# le voit. On reçoit la liste ordonnée des lignes concernées — le haut d'un
# groupe, jusqu'à la ligne déplacée — et chacune prend son rang. Les lignes
# qui ne sont pas envoyées gardent l'ordre automatique (date d'expédition).

_RE_CLE = re.compile(r"^(\d{1,12})-(\d{1,4})$")
MAX_ORDRE = 300


class OrdrePrepaIn(BaseModel):
    lignes: list


# ── Bulles rouges du portail ─────────────────────────────────────────────────
# Le portail s'ouvre souvent : le carnet n'est pas recalculé plus d'une fois
# par minute pour elles. Une écriture ADV (urgence, prépa) remet à zéro.
_BADGES_TTL = 60
_badges_cache = {"t": 0.0, "data": None}


def _badges_invalider():
    _badges_cache["t"] = 0.0


@router.get("/api/adv/badges")
def badges(request: Request):
    user = _exiger(request, ROLES_ADV_PREPA)
    if not _badges_cache["data"] or time.time() - _badges_cache["t"] > _BADGES_TTL:
        try:
            _badges_cache["data"] = adv.badges()
        except FileNotFoundError:
            _badges_cache["data"] = {"present": False, "urgentes": 0, "retard": 0, "semaine": 0}
        _badges_cache["t"] = time.time()
    d = _badges_cache["data"]
    # L'administration suit les expéditions (en retard + sous 7 jours) ; la
    # logistique et l'expédition, les préparations urgentes.
    if effective_role(user) in ROLES_ADV:
        return {"vue": "carnet", "nombre": d["retard"] + d["semaine"],
                "retard": d["retard"], "semaine": d["semaine"]}
    return {"vue": "prepa", "nombre": d["urgentes"], "urgentes": d["urgentes"]}


class UrgenceIn(BaseModel):
    urgente: bool = True


@router.put("/api/adv/prepa/urgence/{numero}/{ligne}")
def marquer_urgente(numero: str, ligne: int, body: UrgenceIn, request: Request):
    user = _exiger(request, ROLES_ADV)
    numero, ligne = _cle(numero, ligne)
    with get_db() as conn:
        if body.urgente:
            conn.execute("""
                INSERT INTO adv_urgences (numero, ligne, maj_le, maj_par) VALUES (?, ?, ?, ?)
                ON CONFLICT(numero, ligne) DO UPDATE SET maj_le=excluded.maj_le, maj_par=excluded.maj_par
            """, (numero, ligne, adv.maintenant(), _nom(user)))
        else:
            conn.execute("DELETE FROM adv_urgences WHERE numero=? AND ligne=?", (numero, ligne))
        conn.commit()
    _badges_invalider()
    log_action(user=user, action="UPDATE", module="adv",
               objet="Préparation %s-L%d · %s" % (numero, ligne, "marquée urgente" if body.urgente else "urgence retirée"),
               request=request)
    return {"ok": True, "urgente": bool(body.urgente)}


class JourPrepaIn(BaseModel):
    jour: Optional[str] = None          # « AAAA-MM-JJ » ; None : jour calculé


_RE_JOUR = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@router.put("/api/adv/prepa/jour/{numero}/{ligne}")
def fixer_jour_prepa(numero: str, ligne: int, body: JourPrepaIn, request: Request):
    """Planning de prépa : l'ADV déplace une préparation sur un autre jour."""
    user = _exiger(request, ROLES_ADV)
    numero, ligne = _cle(numero, ligne)
    jour = (body.jour or "").strip() or None
    if jour:
        try:
            if not _RE_JOUR.match(jour):
                raise ValueError
            date.fromisoformat(jour)
        except ValueError:
            raise HTTPException(status_code=400, detail="Jour invalide — format AAAA-MM-JJ.")
        if jour < adv.aujourdhui_paris().isoformat():
            raise HTTPException(status_code=400, detail="Jour passé — une préparation se planifie à partir d'aujourd'hui.")
    with get_db() as conn:
        avant = conn.execute("SELECT jour FROM adv_prepa_jours WHERE numero=? AND ligne=?",
                             (numero, ligne)).fetchone()
        if jour:
            conn.execute("""
                INSERT INTO adv_prepa_jours (numero, ligne, jour, maj_le, maj_par) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(numero, ligne) DO UPDATE SET jour=excluded.jour, maj_le=excluded.maj_le, maj_par=excluded.maj_par
            """, (numero, ligne, jour, adv.maintenant(), _nom(user)))
        else:
            conn.execute("DELETE FROM adv_prepa_jours WHERE numero=? AND ligne=?", (numero, ligne))
        conn.commit()
    log_action(user=user, action="UPDATE", module="adv",
               objet="Préparation %s-L%d · jour %s" % (numero, ligne, jour or "calculé"),
               detail={"avant": avant["jour"] if avant else None, "apres": jour},
               request=request)
    return {"ok": True, "jour": jour}


@router.put("/api/adv/prepa/ordre")
def ordonner_prepa(body: OrdrePrepaIn, request: Request):
    user = _exiger(request, ROLES_ADV)
    if not isinstance(body.lignes, list) or not body.lignes or len(body.lignes) > MAX_ORDRE:
        raise HTTPException(status_code=400, detail="Liste de lignes invalide.")
    cles, vus = [], set()
    for c in body.lignes:
        m = _RE_CLE.match(str(c))
        if not m:
            raise HTTPException(status_code=400, detail="Ligne de commande invalide.")
        if m.group(0) in vus:
            continue
        vus.add(m.group(0))
        cles.append((m.group(1), int(m.group(2))))
    quand, par = adv.maintenant(), _nom(user)
    with get_db() as conn:
        # Les rangs déjà posés ailleurs (autre groupe) sont conservés ; ceux
        # de la liste sont réécrits de 1 à n dans l'ordre reçu.
        for rang, (numero, ligne) in enumerate(cles, start=1):
            conn.execute("""
                INSERT INTO adv_prepa_priorites (numero, ligne, rang, maj_le, maj_par)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(numero, ligne) DO UPDATE SET
                    rang=excluded.rang, maj_le=excluded.maj_le, maj_par=excluded.maj_par
            """, (numero, ligne, rang, quand, par))
        conn.commit()
    log_action(user=user, action="UPDATE", module="adv",
               objet="Ordre des préparations · %d ligne(s) placée(s)" % len(cles),
               detail={"ordre": ["%s-%s" % c for c in cles]}, request=request)
    return {"ok": True, "lignes": len(cles)}


@router.delete("/api/adv/prepa/ordre")
def ordre_automatique(request: Request):
    """Retire tous les rangs fixés : la Prépa reprend l'ordre par date d'expédition."""
    user = _exiger(request, ROLES_ADV)
    with get_db() as conn:
        n = conn.execute("SELECT COUNT(*) FROM adv_prepa_priorites").fetchone()[0]
        conn.execute("DELETE FROM adv_prepa_priorites")
        conn.commit()
    log_action(user=user, action="DELETE", module="adv",
               objet="Ordre des préparations · retour à l'ordre automatique (%d rang(s) retiré(s))" % n,
               request=request)
    return {"ok": True, "retires": n}


# ── Repiquage d'une ligne : statut fixé à la main ────────────────────────────
_LIB_REPIQUAGE = dict(ADV_REPIQUAGE_STATUTS)


class RepiquageIn(BaseModel):
    statut: Optional[str] = None      # None ou "" : rend la main au planning


@router.put("/api/adv/repiquage/{numero}/{ligne}")
def fixer_repiquage(numero: str, ligne: int, body: RepiquageIn, request: Request):
    """Statut du repiquage de la ligne (à faire, en cours, terminé), ou retour au calcul.

    L'étape Prod du carnet n'est « faite » que quand l'impression ET le
    repiquage le sont ; le statut se lit sur le dossier de repiquage du
    planning, et l'ADV peut le fixer quand le planning ne le dit pas.
    """
    user = _exiger(request, ROLES_ADV)
    numero, ligne = _cle(numero, ligne)
    statut = (body.statut or "").strip() or None
    if statut and statut not in _LIB_REPIQUAGE:
        raise HTTPException(status_code=400, detail="Statut de repiquage inconnu.")
    with get_db() as conn:
        avant = conn.execute("SELECT statut FROM adv_repiquages WHERE numero=? AND ligne=?",
                             (numero, ligne)).fetchone()
        if statut:
            conn.execute("""
                INSERT INTO adv_repiquages (numero, ligne, statut, maj_le, maj_par) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(numero, ligne) DO UPDATE SET
                    statut=excluded.statut, maj_le=excluded.maj_le, maj_par=excluded.maj_par
            """, (numero, ligne, statut, adv.maintenant(), _nom(user)))
        else:
            conn.execute("DELETE FROM adv_repiquages WHERE numero=? AND ligne=?", (numero, ligne))
        conn.commit()
    log_action(user=user, action="UPDATE" if statut else "DELETE", module="adv",
               objet="Repiquage · commande %s ligne %s%s" % (
                   numero, ligne, (" → " + _LIB_REPIQUAGE[statut]) if statut else " · statut du planning rétabli"),
               detail={"avant": dict(avant) if avant else None, "apres": statut}, request=request)
    return {"ok": True, "statut": statut}


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
    if valeur == "probable":
        raise HTTPException(status_code=400, detail="« Probable » se calcule, il ne se fixe pas — choisir Oui ou Non.")
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


# ── Préférences par utilisateur : ordre des colonnes du carnet ───────────────

_CLE_ORDRE = "carnet.colonnes"


def _ordre_valide(ordre) -> list:
    """Clés de colonne connues, sans doublon — le reste est ignoré."""
    vus, out = set(), []
    for c in ordre if isinstance(ordre, list) else []:
        c = str(c)
        if c in mef.TYPES and c not in vus:
            vus.add(c)
            out.append(c)
    return out


def _ordre_colonnes(conn, user) -> list:
    try:
        r = conn.execute("SELECT valeur FROM adv_preferences WHERE user_id=? AND cle=?",
                         (user.get("id"), _CLE_ORDRE)).fetchone()
        return _ordre_valide(json.loads(r["valeur"])) if r else []
    except Exception:
        return []


class OrdreIn(BaseModel):
    ordre: list


@router.put("/api/adv/preferences/colonnes")
def enregistrer_ordre(body: OrdreIn, request: Request):
    """L'ordre des colonnes de la personne connectée ; liste vide = ordre par défaut."""
    user = _exiger(request, ROLES_ADV)
    ordre = _ordre_valide(body.ordre)
    with get_db() as conn:
        if ordre:
            conn.execute("""
                INSERT INTO adv_preferences (user_id, cle, valeur, maj_le) VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, cle) DO UPDATE SET valeur=excluded.valeur, maj_le=excluded.maj_le
            """, (user.get("id"), _CLE_ORDRE, json.dumps(ordre), adv.maintenant()))
        else:
            conn.execute("DELETE FROM adv_preferences WHERE user_id=? AND cle=?", (user.get("id"), _CLE_ORDRE))
        conn.commit()
    return {"ordre": ordre}

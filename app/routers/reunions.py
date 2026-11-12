"""MySifa — Reunions : espace commun, points de production, actions (endpoints).

Deux publics :
  - l'espace Reunions (`/reunions`) : direction, administration, superadmin
    (ROLES_REUNIONS). Chaque lecture
    passe par `rn.peut_voir` — liste, detail, precedente. Les chiffres de
    production d'une reunion ne sont servis qu'aux roles de production.
  - l'onglet Actions de MyProd : roles de production (`_autorise`). Le suivi
    ne montre que les actions des reunions que la personne voit.

Modifier une reunion : son createur, ses participants, le superadmin. La voir
par son type ou son role ne suffit pas. Changer sa visibilite ou la supprimer :
son createur et le superadmin seulement.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request

from config import (CODE_ANNUL_DOS, CODE_ARRIVEE, CODE_DEBUT_DOS,
                    CODE_DEPART, CODE_FIN_DOS, PROD_VITESSE_MAX_M_MIN, ROLE_LABELS,
                    ROLES_PROD, ROLES_REUNIONS)
from database import get_db
from services.auth_service import (can_access_settings_communication, effective_role,
                                   get_current_user, is_superadmin)
from app.services.audit_service import log_action
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


def _lecteur(request: Request):
    """(user, qui) pour les lectures de reunions. L'espace Reunions est reserve
    a ROLES_REUNIONS ; ROLES_PROD garde l'acces pour l'onglet Actions de MyProd,
    qui passe par les memes endpoints."""
    user = get_current_user(request)
    if effective_role(user) not in (ROLES_REUNIONS | ROLES_PROD):
        raise HTTPException(status_code=403, detail="Acces reserve.")
    return user, rn.lecteur(user, effective_role(user), is_superadmin(user))


def _espace(request: Request) -> Dict[str, Any]:
    user = get_current_user(request)
    if effective_role(user) not in ROLES_REUNIONS:
        raise HTTPException(status_code=403, detail="Espace Reunions reserve a la direction et a l'administration.")
    return user


def _voit_prod(user: Dict[str, Any]) -> bool:
    return effective_role(user) in ROLES_PROD


def _reunion_visible(conn, reunion_id: int, qui) -> Dict[str, Any]:
    r = rn.reunion(conn, reunion_id)
    if not r or not rn.peut_voir(r, qui):
        # 404 et non 403 : ne pas confirmer qu'une reunion existe.
        raise HTTPException(status_code=404, detail="Reunion introuvable.")
    return r


def _est_createur(r: Dict[str, Any], qui) -> bool:
    if qui.get("superadmin"):
        return True
    if r.get("ouverte_par_id") not in (None, "") and qui.get("id") is not None:
        return str(r["ouverte_par_id"]) == str(qui["id"])
    return str(r.get("ouverte_par") or "").strip().lower() == qui.get("nom", "").lower() != ""


def _peut_modifier(r: Dict[str, Any], qui) -> bool:
    if _est_createur(r, qui):
        return True
    nom = qui.get("nom", "").lower()
    for p in r.get("participants") or []:
        if (qui.get("id") is not None and p.get("user_id") not in (None, "")
                and str(p["user_id"]) == str(qui["id"])) or (nom and str(p.get("nom") or "").lower() == nom):
            return True
    return False


def _avec_droits(r: Dict[str, Any], qui) -> Dict[str, Any]:
    r["droits"] = {"modifier": _peut_modifier(r, qui), "gerer": _est_createur(r, qui)}
    return r


def _admin_types(request: Request) -> Dict[str, Any]:
    user = get_current_user(request)
    if not can_access_settings_communication(user):
        raise HTTPException(status_code=403, detail="Reserve a la direction.")
    return user


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
                                     code_fin=CODE_FIN_DOS,
                                     vitesse_max=PROD_VITESSE_MAX_M_MIN),
        # `presence=True` : le point de production lit les pointages 86/87.
        # C'est ce qui empeche un dossier ouvert le vendredi et repris le lundi
        # de se dessiner en un seul rectangle qui traverse un samedi ou la
        # machine n'a vu personne. La frise de /prod#retour, elle, ne le
        # demande pas et garde son trace.
        "frise": rd.frise(conn, b["debut"], b["fin"], machine, code_fin=CODE_FIN_DOS,
                          code_debut=CODE_DEBUT_DOS, code_annul=CODE_ANNUL_DOS,
                          presence=True, code_arrivee=CODE_ARRIVEE,
                          code_depart=CODE_DEPART),
        "comptes_rendus": rd.comptes_rendus_periode(conn, b["debut"], b["fin"],
                                                    machine=machine,
                                                    code_fin=CODE_FIN_DOS,
                                                    vitesse_max=PROD_VITESSE_MAX_M_MIN),
        "machines": dispo,
        "machines_hors_production": hors,
    }


@router.get("/api/reunions")
def liste_reunions(request: Request, limite: int = 100, type: Optional[int] = None):
    """Les reunions que la personne voit, la plus recente en tete."""
    _, qui = _lecteur(request)
    with get_db() as conn:
        return {"reunions": rn.liste(conn, limite, qui=qui, type_id=type)}


@router.get("/api/reunions/types")
def types_reunion(request: Request):
    """Les types actifs, pour choisir. Declaree avant /api/reunions/{id}."""
    get_current_user(request)
    with get_db() as conn:
        return {"types": rn.types(conn, actifs_seulement=True)}


@router.get("/api/reunions/types/admin")
def types_admin(request: Request):
    """Tous les types, actifs ou non (Parametres)."""
    _admin_types(request)
    with get_db() as conn:
        types = rn.types(conn)
        for t in types:
            t["nb_reunions"] = conn.execute(
                "SELECT COUNT(*) FROM reunions WHERE type_id=?", (t["id"],)).fetchone()[0]
    return {"types": types, "visibilites": rn.VISIBILITE_LIBELLES,
            "roles": [{"code": k, "libelle": v} for k, v in ROLE_LABELS.items()]}


@router.post("/api/reunions/types/admin")
async def creer_type(request: Request):
    user = _admin_types(request)
    body = await request.json()
    with get_db() as conn:
        try:
            t = rn.enregistrer_type(conn, None, body)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    log_action(user=user, action="CREATE", module="reunions",
               objet=f"Type de reunion · {t['libelle']}", detail=t, request=request)
    return t


@router.put("/api/reunions/types/admin/{type_id}")
async def modifier_type(type_id: int, request: Request):
    user = _admin_types(request)
    body = await request.json()
    with get_db() as conn:
        avant = rn.type_reunion(conn, type_id)
        try:
            t = rn.enregistrer_type(conn, type_id, body)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    log_action(user=user, action="UPDATE", module="reunions",
               objet=f"Type de reunion · {t['libelle']}", detail={"avant": avant, "apres": t},
               request=request)
    return t


@router.delete("/api/reunions/types/admin/{type_id}")
def supprimer_type(type_id: int, request: Request):
    user = _admin_types(request)
    with get_db() as conn:
        avant = rn.type_reunion(conn, type_id)
        try:
            res = rn.supprimer_type(conn, type_id)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
    log_action(user=user, action="DELETE" if res == "supprime" else "UPDATE",
               module="reunions", objet=f"Type de reunion · {(avant or {}).get('libelle', type_id)}",
               detail={"resultat": res}, request=request)
    return {"resultat": res}


@router.get("/api/reunions/actions")
def suivi_actions(request: Request):
    """Le suivi des actions, toutes reunions confondues. Declaree avant
    /api/reunions/{reunion_id} : sinon « actions » serait lu comme un id.
    Une action d'une reunion que la personne ne voit pas n'y figure pas."""
    user = _autorise(request)
    qui = rn.lecteur(user, effective_role(user), is_superadmin(user))
    with get_db() as conn:
        return {"actions": rn.toutes_actions(conn, qui), "statuts": rn.action_statuts()}


@router.post("/api/reunions/actions")
async def creer_action(request: Request):
    """Une action creee depuis le suivi, hors reunion. Declaree avant
    /api/reunions/{reunion_id} pour la meme raison que le suivi."""
    _autorise(request)
    body = await request.json()
    with get_db() as conn:
        a = rn.ajouter_action(conn, None, str(body.get("texte") or ""),
                              str(body.get("responsable") or ""),
                              str(body.get("echeance") or ""))
    if not a:
        raise HTTPException(status_code=400, detail="Action vide.")
    return a


@router.get("/api/reunions/contexte")
def contexte(request: Request):
    """De quoi ouvrir la page : reunion en cours, plage proposee, participants,
    types de reunion et roles (pour regler la visibilite)."""
    user, qui = _lecteur(request)
    with get_db() as conn:
        ouverte = rn.ouverte_de(conn, _auteur(user))
        veille = (date.today() - timedelta(days=1)).isoformat()
        jour = rd.dernier_jour_saisi(conn, veille) or veille
        rows = conn.execute(
            """SELECT id, nom FROM users
                WHERE actif=1 AND TRIM(COALESCE(nom,'')) <> ''
                ORDER BY nom"""
        ).fetchall()
        types = rn.types(conn, actifs_seulement=True)
    return {
        "ouverte": ouverte if ouverte and rn.peut_voir(ouverte, qui) else None,
        "jour_propose": jour,
        "titre_propose": rn.titre_par_defaut(),
        "personnes": [dict(r) for r in rows],
        "types": types,
        "visibilites": rn.VISIBILITE_LIBELLES,
        "roles": [{"code": k, "libelle": v} for k, v in ROLE_LABELS.items()],
        "moi": {"id": user.get("id"), "nom": _auteur(user), "role": effective_role(user),
                "voit_prod": _voit_prod(user), "admin_types": can_access_settings_communication(user)},
    }


@router.post("/api/reunions")
async def lancer_reunion(request: Request):
    """Ouvre une reunion. Sans `espace`, c'est un point de production lance
    depuis MyProd (reprise de la reunion ouverte, roles de production) ; avec
    `espace: true`, une reunion de l'espace commun, toujours creee."""
    body = await request.json()
    espace = bool(body.get("espace"))
    user = _espace(request) if espace else _autorise(request)
    roles = body.get("roles_visibles")
    with get_db() as conn:
        r = rn.lancer(
            conn, _auteur(user),
            str(body.get("date_debut") or (date.today().isoformat() if espace else "")),
            str(body.get("date_fin") or ""),
            str(body.get("titre") or ""), str(body.get("machine") or ""),
            [str(x) for x in (body.get("participants") or [])],
            [str(x) for x in (body.get("machines") or [])],
            type_id=body.get("type_id"), visibilite=body.get("visibilite"),
            roles_visibles=[str(x) for x in roles] if isinstance(roles, list) else None,
            auteur_id=user.get("id"), reprendre=not espace,
        )
    if not r:
        raise HTTPException(status_code=400, detail="Reunion non creee.")
    qui = rn.lecteur(user, effective_role(user), is_superadmin(user))
    return _avec_droits(r, qui)


@router.get("/api/reunions/{reunion_id}")
def detail_reunion(reunion_id: int, request: Request, avec_prod: bool = True):
    """Le compte-rendu, et les chiffres de sa plage quand son type en a et que
    la personne est de la production."""
    user, qui = _lecteur(request)
    with get_db() as conn:
        r = _reunion_visible(conn, reunion_id, qui)
        chiffres = bool((r.get("type") or {}).get("chiffres_prod", True))
        prod = _detail_prod(conn, r) if avec_prod and chiffres and _voit_prod(user) else None
        ecoutes = [dict(e) for e in conn.execute(
            """SELECT id, statut, demarre_le, duree_s, valide_le FROM reunion_ecoutes
                WHERE reunion_id=? ORDER BY id""", (reunion_id,)).fetchall()] \
            if rn._table_existe(conn, "reunion_ecoutes") else []
    r["ecoutes"] = ecoutes
    return {"reunion": _avec_droits(r, qui), "prod": prod}


@router.get("/api/reunions/{reunion_id}/precedente")
def precedente_reunion(reunion_id: int, request: Request):
    """Les notes du point precedent — relues pendant celui-ci, jamais modifiees."""
    _, qui = _lecteur(request)
    with get_db() as conn:
        _reunion_visible(conn, reunion_id, qui)
        p = rn.precedente(conn, reunion_id)
        if p and not rn.reunion_visible(conn, p["id"], qui):
            p = None
    return {"precedente": p}


@router.post("/api/reunions/{reunion_id}")
async def enregistrer_reunion(reunion_id: int, request: Request):
    """Met a jour titre, notes, decisions, plage, machine ou participants ;
    type et visibilite pour son createur."""
    user, qui = _lecteur(request)
    body = await request.json()
    parts = body.get("participants")
    machs = body.get("machines")
    roles = body.get("roles_visibles")
    with get_db() as conn:
        actuelle = _reunion_visible(conn, reunion_id, qui)
        if not _peut_modifier(actuelle, qui):
            raise HTTPException(status_code=403, detail="Seuls le createur et les participants modifient cette reunion.")
        gerer = _est_createur(actuelle, qui)
        if not gerer and any(k in body for k in ("visibilite", "roles_visibles", "type_id")):
            raise HTTPException(status_code=403, detail="Seul le createur change le type ou la visibilite.")
        r = rn.enregistrer(
            conn, reunion_id, _auteur(user),
            titre=body.get("titre"), notes=body.get("notes"),
            date_debut=body.get("date_debut"), date_fin=body.get("date_fin"),
            machine=body.get("machine"),
            noms_machines=[str(x) for x in machs] if machs is not None else None,
            noms_participants=[str(x) for x in parts] if parts is not None else None,
            decisions=body.get("decisions"),
            type_id=body.get("type_id"), visibilite=body.get("visibilite"),
            roles_visibles=[str(x) for x in roles] if isinstance(roles, list) else None,
        )
    if not r:
        raise HTTPException(status_code=404, detail="Reunion introuvable.")
    if "visibilite" in body or "roles_visibles" in body:
        log_action(user=user, action="UPDATE", module="reunions",
                   objet=f"Reunion · {r.get('titre')}",
                   detail={"visibilite": {"avant": [actuelle.get("visibilite"), actuelle.get("roles_visibles")],
                                          "apres": [r.get("visibilite"), r.get("roles_visibles")]}},
                   request=request)
    return _avec_droits(r, qui)


@router.post("/api/reunions/{reunion_id}/clore")
async def clore_reunion(reunion_id: int, request: Request):
    """Clot le point, ou le rouvre. Clore ne verrouille rien."""
    user, qui = _lecteur(request)
    body = await request.json() if await request.body() else {}
    with get_db() as conn:
        if not _peut_modifier(_reunion_visible(conn, reunion_id, qui), qui):
            raise HTTPException(status_code=403, detail="Seuls le createur et les participants modifient cette reunion.")
        r = rn.clore(conn, reunion_id, _auteur(user), bool(body.get("rouvrir", False)))
    if not r:
        raise HTTPException(status_code=404, detail="Reunion introuvable.")
    return _avec_droits(r, qui)


@router.delete("/api/reunions/{reunion_id}")
def supprimer_reunion(reunion_id: int, request: Request):
    _, qui = _lecteur(request)
    with get_db() as conn:
        if not _est_createur(_reunion_visible(conn, reunion_id, qui), qui):
            raise HTTPException(status_code=403, detail="Seul le createur supprime cette reunion.")
        ok = rn.supprimer(conn, reunion_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Reunion introuvable.")
    return {"supprimee": True}


@router.post("/api/reunions/{reunion_id}/actions")
async def ajouter_action(reunion_id: int, request: Request):
    """Une action : un quoi, un qui, un pour quand. Le quoi suffit."""
    _, qui = _lecteur(request)
    body = await request.json()
    with get_db() as conn:
        if not _peut_modifier(_reunion_visible(conn, reunion_id, qui), qui):
            raise HTTPException(status_code=403, detail="Seuls le createur et les participants modifient cette reunion.")
        a = rn.ajouter_action(conn, reunion_id, str(body.get("texte") or ""),
                              str(body.get("responsable") or ""),
                              str(body.get("echeance") or ""))
    if not a:
        raise HTTPException(status_code=400, detail="Action vide ou reunion introuvable.")
    return a


@router.post("/api/reunions/actions/{action_id}")
async def modifier_action(action_id: int, request: Request):
    """Corrige une action ou la coche. Un texte vide la supprime.

    Une action hors reunion se gere depuis le suivi (roles de production) ; une
    action de reunion, par qui voit la reunion — le responsable coche ce qu'on
    lui a confie."""
    user, qui = _lecteur(request)
    body = await request.json()
    fait = body.get("fait")
    with get_db() as conn:
        row = conn.execute("SELECT reunion_id FROM reunion_actions WHERE id=?", (action_id,)).fetchone()
        if not row:
            return {"action": None, "supprimee": True}
        if row["reunion_id"] is None:
            if not _voit_prod(user):
                raise HTTPException(status_code=403, detail="Acces reserve a la production.")
        else:
            _reunion_visible(conn, row["reunion_id"], qui)
        a = rn.modifier_action(conn, action_id, _auteur(user),
                               texte=body.get("texte"),
                               responsable=body.get("responsable"),
                               echeance=body.get("echeance"),
                               fait=None if fait is None else bool(fait),
                               statut=body.get("statut"))
    return {"action": a, "supprimee": a is None}

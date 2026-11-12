"""MySifa — Reunions, mode ecoute : enregistrement, suivi, validation du brief.

Tout utilisateur connecte peut lancer une ecoute. Une ecoute n'est visible que
de la personne qui l'a lancee (et du superadmin) jusqu'a sa validation : la
transcription brute ne circule pas. Le brief valide devient une reunion, avec
la visibilite de son type.

Enregistre AVANT le router des reunions dans main.py : `/api/reunions/ecoutes`
serait sinon lu comme `/api/reunions/{reunion_id}`.

Journal : demarrage, arret, validation, abandon et relance sont journalises
ici (module `reunions_ecoute`, contenu jamais recopie). Les morceaux d'audio
sont exclus du journal automatique (`/morceau`, audit_taxonomy.SKIP_SUFFIXES).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request

from config import (ECOUTE_DIR, ECOUTE_DUREE_MAX_H, ECOUTE_MORCEAU_MAX_MO,
                    ECOUTE_RETENTION_JOURS, ROLE_LABELS, ROLES_REUNIONS)
from database import get_db
from services.auth_service import effective_role, get_current_user, is_superadmin
from app.services import reunion as rn
from app.services import reunion_ecoute as ec
from app.services.audit_service import log_action

router = APIRouter()


def _qui(request: Request):
    user = get_current_user(request)
    if effective_role(user) not in ROLES_REUNIONS:
        raise HTTPException(status_code=403, detail="Espace Reunions reserve a la direction et a l'administration.")
    return user, rn.lecteur(user, effective_role(user), is_superadmin(user))


def _auteur(user: Dict[str, Any]) -> str:
    return str(user.get("nom") or user.get("email") or "?")


def _ecoute_visible(conn, ecoute_id: int, qui, avec_texte: bool = False) -> Dict[str, Any]:
    e = ec.ecoute(conn, ecoute_id, avec_texte=avec_texte)
    if not e or not ec.visible(e, qui):
        raise HTTPException(status_code=404, detail="Ecoute introuvable.")
    return e


def _objet(e: Dict[str, Any]) -> str:
    return f"Ecoute n° {e['id']}" + (f" · {e['titre']}" if e.get("titre") else "")


def _attente_min(conn, e: Dict[str, Any]) -> Optional[int]:
    """Estimation du delai avant le brief : la file devant elle, puis sa propre
    duree (facteur ~1,05 mesure au bench du 2026-11-05), plus la marge du
    brief. Indicatif : affiche « ~N min »."""
    if e.get("statut") not in ec.EN_TRAITEMENT:
        return None
    devant = conn.execute(
        """SELECT COALESCE(SUM(COALESCE(duree_s, nb_morceaux * 30)), 0) FROM reunion_ecoutes
            WHERE statut IN (?, ?) AND id < ?""",
        (ec.A_TRANSCRIRE, ec.TRANSCRIPTION, e["id"]),
    ).fetchone()[0] or 0
    propre = 0 if e["statut"] == ec.A_STRUCTURER else float(e.get("duree_s") or (e.get("nb_morceaux") or 0) * 30) * 1.05
    p = float(e.get("progression") or 0)
    if e["statut"] == ec.TRANSCRIPTION and p >= 0.03 and e.get("transcription_debut"):
        # En cours : le rythme réellement observé remplace celui du bench.
        ecoule = (datetime.now() - datetime.fromisoformat(e["transcription_debut"][:19])).total_seconds()
        propre = max(0.0, ecoule * (1 - p) / p)
    return max(1, int(round((float(devant) * 1.05 + propre) / 60)) + 1)


@router.get("/api/reunions/ecoutes")
def mes_ecoutes(request: Request):
    """Mes ecoutes en cours et recentes, et celle qui enregistre encore."""
    user, qui = _qui(request)
    with get_db() as conn:
        liste = ec.liste_de(conn, qui)
        for e in liste:
            e["attente_min"] = _attente_min(conn, e)
        return {"ecoutes": liste, "en_cours": ec.en_cours_de(conn, qui),
                "statuts": ec.STATUTS}


@router.post("/api/reunions/ecoutes")
async def demarrer(request: Request):
    """Demarre une ecoute. Si la personne en a une qui enregistre encore (page
    rechargee, onglet rouvert), elle lui est rendue : on reprend, on n'empile
    pas un second enregistrement."""
    user, qui = _qui(request)
    body = await request.json() if await request.body() else {}
    with get_db() as conn:
        deja = ec.en_cours_de(conn, qui)
        if deja:
            return dict(deja, reprise=True)
        reunion_id = body.get("reunion_id")
        if reunion_id:
            r = rn.reunion(conn, int(reunion_id))
            if not r or not rn.peut_voir(r, qui):
                raise HTTPException(status_code=404, detail="Reunion introuvable.")
        e = ec.creer(conn, _auteur(user), user.get("id"), body.get("type_id"),
                     str(body.get("titre") or ""), reunion_id)
    log_action(user=user, action="CREATE", module="reunions_ecoute", objet=_objet(e), request=request)
    return dict(e, reprise=False)


@router.post("/api/reunions/ecoutes/{ecoute_id}/morceau")
async def recevoir_morceau(ecoute_id: int, request: Request, n: int, mime: str = ""):
    """Un morceau d'audio (30 s), corps brut. Rejouable : renvoyer le meme
    numero apres une coupure reseau remplace le precedent."""
    _, qui = _qui(request)
    donnees = await request.body()
    with get_db() as conn:
        e = _ecoute_visible(conn, ecoute_id, qui)
        debut = datetime.fromisoformat(e["demarre_le"][:19])
        if datetime.now() - debut > timedelta(hours=ECOUTE_DUREE_MAX_H):
            ec.arreter(conn, ECOUTE_DIR, ecoute_id)
            raise HTTPException(status_code=409,
                                detail=f"Durée maximale atteinte ({ECOUTE_DUREE_MAX_H} h) — écoute arrêtée.")
        try:
            return ec.ajouter_morceau(conn, ECOUTE_DIR, ecoute_id, n, donnees,
                                      mime or request.headers.get("content-type", ""),
                                      ECOUTE_MORCEAU_MAX_MO * 1024 * 1024)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc))


@router.post("/api/reunions/ecoutes/{ecoute_id}/arreter")
async def arreter(ecoute_id: int, request: Request):
    """Fin de l'enregistrement : type, titre et reunion de rattachement
    choisis a l'arret. Rend l'estimation du delai avant le brief."""
    user, qui = _qui(request)
    body = await request.json() if await request.body() else {}
    with get_db() as conn:
        _ecoute_visible(conn, ecoute_id, qui)
        reunion_id = body.get("reunion_id")
        if reunion_id and not rn.reunion_visible(conn, int(reunion_id), qui):
            raise HTTPException(status_code=404, detail="Reunion introuvable.")
        try:
            e = ec.arreter(conn, ECOUTE_DIR, ecoute_id, body.get("nb_morceaux"), body.get("duree_s"),
                           body.get("type_id"), body.get("titre"), reunion_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        e["attente_min"] = _attente_min(conn, e)
    log_action(user=user, action="UPDATE", module="reunions_ecoute", objet=_objet(e),
               detail={"evenement": "arret", "statut": e["statut"], "morceaux": e["nb_morceaux"],
                       "manquants": len(e["morceaux_manquants"])}, request=request)
    return e


@router.get("/api/reunions/ecoutes/{ecoute_id}")
def detail(ecoute_id: int, request: Request):
    """L'ecoute avec sa transcription et son brief, et de quoi le valider :
    types, annuaire, reunions recentes ou le rattacher."""
    user, qui = _qui(request)
    with get_db() as conn:
        e = _ecoute_visible(conn, ecoute_id, qui, avec_texte=True)
        e["attente_min"] = _attente_min(conn, e)
        if e["statut"] == ec.PROPOSITION and not e.get("proposition"):
            e["proposition"] = ec.brief_vide(e)
        personnes = [dict(r) for r in conn.execute(
            """SELECT id, nom FROM users WHERE actif=1 AND TRIM(COALESCE(nom,''))<>''
                ORDER BY nom""").fetchall()]
        recentes = [{"id": r["id"], "titre": r["titre"], "date_debut": r["date_debut"],
                     "type": r.get("type")} for r in rn.liste(conn, 30, qui=qui)]
        types = rn.types(conn, actifs_seulement=True)
    return {"ecoute": e, "personnes": personnes, "reunions": recentes, "types": types,
            "visibilites": rn.VISIBILITE_LIBELLES,
            "roles": [{"code": k, "libelle": v} for k, v in ROLE_LABELS.items()]}


@router.post("/api/reunions/ecoutes/{ecoute_id}/valider")
async def valider(ecoute_id: int, request: Request):
    """Le brief relu devient une reunion (ou complete celle de rattachement),
    ses actions entrent au suivi."""
    user, qui = _qui(request)
    body = await request.json()
    with get_db() as conn:
        _ecoute_visible(conn, ecoute_id, qui)
        cible = body.get("reunion_id")
        if cible:
            r = rn.reunion(conn, int(cible))
            if not r or not rn.peut_voir(r, qui):
                raise HTTPException(status_code=404, detail="Reunion introuvable.")
        try:
            res = ec.valider(conn, ecoute_id, body, _auteur(user), user.get("id"),
                             ECOUTE_RETENTION_JOURS, jour=body.get("date"))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    r = res["reunion"]
    log_action(user=user, action="VALIDATE", module="reunions_ecoute", objet=_objet(res["ecoute"]),
               detail={"reunion_id": r["id"], "actions": len(body.get("actions") or [])},
               request=request)
    return res


@router.post("/api/reunions/ecoutes/{ecoute_id}/relancer")
def relancer(ecoute_id: int, request: Request):
    user, qui = _qui(request)
    with get_db() as conn:
        _ecoute_visible(conn, ecoute_id, qui)
        try:
            e = ec.relancer(conn, ecoute_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        e["attente_min"] = _attente_min(conn, e)
    log_action(user=user, action="UPDATE", module="reunions_ecoute", objet=_objet(e),
               detail={"evenement": "relance"}, request=request)
    return e


@router.post("/api/reunions/ecoutes/{ecoute_id}/abandonner")
def abandonner(ecoute_id: int, request: Request):
    """Efface l'audio et la transcription. Une ecoute validee ne s'abandonne
    plus : c'est la reunion qu'elle a produite qu'on supprime."""
    user, qui = _qui(request)
    with get_db() as conn:
        e = _ecoute_visible(conn, ecoute_id, qui)
        if e["statut"] == ec.VALIDEE:
            raise HTTPException(status_code=400, detail="Brief déjà validé — supprimer la réunion à la place.")
        e = ec.abandonner(conn, ECOUTE_DIR, ecoute_id)
    log_action(user=user, action="DELETE", module="reunions_ecoute", objet=_objet(e), request=request)
    return e

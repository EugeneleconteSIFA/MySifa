"""MySifa — MyProd › Production › Erreurs & Qualité : les écarts de saisie à traiter.

Les écarts eux-mêmes sont ceux de la file Cohérence, famille « prod »
(`app/services/coherence.py`) : une seule définition de ce qui est anormal.
Cette route en fait une liste de travail pour MyProd, avec deux gestes :

- Valider  : l'écart est normal, il sort de la pastille (statut « expliqué »,
             avec qui et quand).
- Corriger : la correction propre à chaque type, après aperçu.
    prod.dossier_fictif       rattacher toutes les saisies au vrai dossier ;
    prod.calage_non_reporte   reporter les heures déclarées en forçant ;
    prod.calage_signale       corriger les trois heures, puis les reporter ;
    autres                    ouvrir la saisie concernée (aucune correction devinée).

  GET  /api/prod/ecarts                  liste des écarts ouverts + action de chacun
  GET  /api/prod/ecarts/count            pour les pastilles
  POST /api/prod/ecarts/{id}/valider
  GET  /api/prod/ecarts/{id}/correction  aperçu de la correction
  POST /api/prod/ecarts/{id}/corriger

Réservé aux rôles d'administration (ceux qui corrigent des saisies).
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Request

from database import get_db
from app.services import coherence, calage_cloture
from app.services.audit_service import log_action
from app.services.auth_service import get_current_user, is_admin

router = APIRouter(prefix="/api/prod/ecarts", tags=["prod-ecarts"])
_PARIS = ZoneInfo("Europe/Paris")

# Règle -> geste proposé par « Corriger ».
ACTIONS = {
    "prod.dossier_fictif": "rattacher",
    "prod.calage_non_reporte": "reappliquer",
    "prod.calage_signale": "heures",
}
# Règles dont la correction est d'ouvrir une saisie précise.
SAISIE_A_OUVRIR = {"prod.quantite_vs_of", "prod.quantite_non_saisie", "prod.info_prod_absente",
                   "prod.seuils_sans_explication", "prod.saisie_ouverte"}


def _maintenant() -> datetime:
    return datetime.now(_PARIS).replace(tzinfo=None)


def _admin(request: Request) -> dict:
    user = get_current_user(request)
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Réservé aux responsables de production.")
    return user


def _qui(user: dict) -> str:
    return user.get("nom") or user.get("email") or ""


def _ecart(conn, ecart_id: int) -> Dict[str, Any]:
    r = conn.execute("SELECT * FROM coherence_ecarts WHERE id=? AND famille='prod'", (ecart_id,)).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Écart introuvable.")
    d = dict(r)
    try:
        d["donnees"] = json.loads(d.get("donnees_json") or "{}")
    except Exception:
        d["donnees"] = {}
    return d


def _action(regle: str) -> str:
    if regle in ACTIONS:
        return ACTIONS[regle]
    if regle in SAISIE_A_OUVRIR:
        return "saisie"
    return "lien"


def _resoudre(conn, ecart_id: int, qui: str, comment: str) -> None:
    conn.execute(
        """UPDATE coherence_ecarts SET statut='resolu', resolu_le=?, explication=?,
                  explique_par=?, explique_le=? WHERE id=?""",
        (_maintenant().strftime("%Y-%m-%dT%H:%M:%S"), comment[:1000], qui,
         _maintenant().strftime("%Y-%m-%dT%H:%M:%S"), ecart_id))


def _saisie_concernee(conn, e: Dict[str, Any]) -> Optional[dict]:
    """La saisie à ouvrir pour corriger un écart « autre »."""
    dos = e["objet_ref"]
    regle = e["regle"]
    row = None
    if regle == "prod.seuils_sans_explication":
        from app.services import rapport_dossier
        for sx in rapport_dossier.seuils_franchis(conn, dos):
            if sx.get("sans_explication") and sx.get("saisie_id"):
                row = conn.execute("SELECT * FROM production_data WHERE id=?", (sx["saisie_id"],)).fetchone()
                break
    elif regle == "prod.saisie_ouverte":
        from app.services import rapport_dossier
        t = rapport_dossier.temps_par_categorie(rapport_dossier._saisies(conn, dos))
        for o in t.get("saisies_ouvertes") or []:
            if o.get("saisie_id"):
                row = conn.execute("SELECT * FROM production_data WHERE id=?", (o["saisie_id"],)).fetchone()
                break
    if row is None:
        # Quantité, info prod : c'est la saisie de clôture qui porte la valeur.
        row = conn.execute(
            """SELECT * FROM production_data WHERE trim(no_dossier)=trim(?) AND operation_code='89'
                  AND COALESCE(est_annule,0)=0 ORDER BY date_operation DESC, id DESC LIMIT 1""",
            (dos,)).fetchone()
    return dict(row) if row else None


def _candidats_fictif(conn, of: str) -> list:
    """Vrais dossiers qui portent le même OF que le dossier fictif."""
    of = (of or "").strip()
    if not of:
        return []
    vus, out = set(), []
    for r in conn.execute(
            """SELECT reference AS no_dossier, client, statut FROM planning_entries
                WHERE trim(reference) = trim(?) OR trim(COALESCE(numero_of,'')) = trim(?)
                   OR reference LIKE ?
                ORDER BY id DESC LIMIT 10""", (of, of, of + "%")).fetchall():
        if r["no_dossier"] and r["no_dossier"] not in vus and not r["no_dossier"].startswith("FICTIF:"):
            vus.add(r["no_dossier"])
            out.append({"no_dossier": r["no_dossier"], "client": r["client"],
                        "source": "planning", "statut": r["statut"]})
    for r in conn.execute(
            """SELECT DISTINCT no_dossier, client FROM production_data
                WHERE no_dossier LIKE ? AND no_dossier NOT LIKE 'FICTIF:%' LIMIT 10""",
            (of + "%",)).fetchall():
        if r["no_dossier"] not in vus:
            vus.add(r["no_dossier"])
            out.append({"no_dossier": r["no_dossier"], "client": r["client"], "source": "saisies"})
    return out


@router.get("")
def lister(request: Request):
    _admin(request)
    with get_db() as conn:
        if "coherence_ecarts" not in coherence._tables(conn):
            return {"ecarts": [], "total": 0}
        res = coherence.lister(conn, famille="prod", statut="ouvert", limite=300)
    for e in res["ecarts"]:
        e["action"] = _action(e["regle"])
    res["total"] = len(res["ecarts"])
    return res


@router.get("/count")
def compter(request: Request):
    user = get_current_user(request)
    if not is_admin(user):
        return {"n": 0}
    with get_db() as conn:
        n, _sig = coherence.compter_ouverts(conn, "prod")
    return {"n": n}


@router.post("/{ecart_id}/valider")
async def valider(ecart_id: int, request: Request):
    user = _admin(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    texte = (body.get("commentaire") or "").strip() or "Validé dans MyProd."
    with get_db() as conn:
        e = _ecart(conn, ecart_id)
        coherence.expliquer(conn, ecart_id, texte, _qui(user))
        decl_id = e["donnees"].get("declaration_id")
        if decl_id:
            calage_cloture.marquer_traite(conn, int(decl_id), _qui(user), _maintenant())
            conn.commit()
    log_action(user=user, action="UPDATE", module="saisies",
               objet=f"Écart validé · {e['titre']}", detail={"regle": e["regle"], "commentaire": texte},
               ip=request.client.host if request.client else None)
    return {"success": True}


@router.get("/{ecart_id}/correction")
def apercu(ecart_id: int, request: Request):
    _admin(request)
    with get_db() as conn:
        e = _ecart(conn, ecart_id)
        action = _action(e["regle"])
        out: Dict[str, Any] = {"ecart": {k: e[k] for k in ("id", "regle", "titre", "detail", "objet_ref")},
                               "action": action}
        if action == "rattacher":
            out["candidats"] = _candidats_fictif(conn, e["donnees"].get("of", ""))
            out["no_dossier"] = e["objet_ref"]
        elif action in ("reappliquer", "heures"):
            decl = calage_cloture.lire_declaration_id(conn, int(e["donnees"]["declaration_id"]))
            if not decl:
                raise HTTPException(status_code=404, detail="Déclaration introuvable.")
            out["declaration"] = {k: decl.get(k) for k in (
                "id", "no_dossier", "machine", "debut_calage_declare", "fin_calage_declare",
                "fin_prod_declare", "debut_calage_mesure", "fin_calage_mesure", "fin_prod_mesure",
                "calage_mesure_min", "declare_par", "declare_le", "signalement")}
            if action == "reappliquer":
                declare = {"debut_calage": calage_cloture._dt(decl["debut_calage_declare"]),
                           "fin_calage": calage_cloture._dt(decl["fin_calage_declare"]),
                           "fin_prod": calage_cloture._dt(decl["fin_prod_declare"])}
                try:
                    out["apercu"] = calage_cloture.forcer_heures(
                        conn, decl["id"], declare, "", _maintenant(), simuler=True)
                except ValueError as err:
                    out["erreur"] = str(err)
        elif action == "saisie":
            out["saisie"] = _saisie_concernee(conn, e)
        else:
            from app.services.coherence import REGLES
            out["lien"] = REGLES[e["regle"]].lien if e["regle"] in REGLES else "/prod"
    return out


@router.post("/{ecart_id}/corriger")
async def corriger(ecart_id: int, request: Request):
    user = _admin(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    qui = _qui(user)
    with get_db() as conn:
        e = _ecart(conn, ecart_id)
        action = _action(e["regle"])
        if action == "rattacher":
            cible = (body.get("to_no_dossier") or "").strip()
            if not cible:
                raise HTTPException(status_code=400, detail="Choisissez le dossier de rattachement.")
            from app.routers.saisies import rattacher_fictif
            res = rattacher_fictif(conn, e["objet_ref"], cible, user.get("email") or qui)
            _resoudre(conn, ecart_id, qui, f"Rattaché à {res['to_no_dossier']} depuis MyProd.")
            detail = {"vers": res["to_no_dossier"], "saisies": res["updated_saisies"]}
        elif action in ("reappliquer", "heures"):
            decl_id = int(e["donnees"]["declaration_id"])
            decl = calage_cloture.lire_declaration_id(conn, decl_id)
            if not decl:
                raise HTTPException(status_code=404, detail="Déclaration introuvable.")
            if action == "heures":
                try:
                    declare = calage_cloture.lire_declaration(body)
                except ValueError as err:
                    raise HTTPException(status_code=400, detail=str(err))
                if not declare:
                    raise HTTPException(status_code=400, detail="Les trois heures sont requises.")
            else:
                declare = {"debut_calage": calage_cloture._dt(decl["debut_calage_declare"]),
                           "fin_calage": calage_cloture._dt(decl["fin_calage_declare"]),
                           "fin_prod": calage_cloture._dt(decl["fin_prod_declare"])}
            try:
                res = calage_cloture.forcer_heures(conn, decl_id, declare, qui, _maintenant())
            except (ValueError, LookupError) as err:
                raise HTTPException(status_code=400, detail=str(err))
            _resoudre(conn, ecart_id, qui, "Heures du dossier de prod reportées depuis MyProd.")
            detail = {"changements": len(res["changements"])}
        else:
            raise HTTPException(status_code=409,
                                detail="Cet écart se corrige dans la saisie concernée, puis se valide.")
        conn.commit()
        try:
            coherence.rafraichir_saisies(conn)
        except Exception:
            pass
    log_action(user=user, action="UPDATE", module="saisies",
               objet=f"Écart corrigé · {e['titre']}", detail=dict(detail, regle=e["regle"]),
               ip=request.client.host if request.client else None)
    return {"success": True, **detail}

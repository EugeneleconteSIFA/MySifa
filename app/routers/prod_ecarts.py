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
  GET  /api/prod/ecarts/reglages         catégories et leur prise en compte
  PUT  /api/prod/ecarts/reglages         {regle, compte} : compte ou non dans « À traiter »

Réservé aux rôles d'administration (ceux qui corrigent des saisies).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
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
    # Dossier « en cours » sans saisie : la correction est presque toujours
    # dans les saisies de la machine (faites sous un autre numéro, ou dossier
    # fini sans fin de production) — on les montre, avec le planning à côté.
    "prod.en_cours_sans_saisie": "machine_saisies",
    "prod.retard_prevu": "planning",
    "prod.info_prod_absente": "info_prod",
}
# Règles dont la correction est d'ouvrir une saisie précise.
SAISIE_A_OUVRIR = {"prod.quantite_vs_of", "prod.quantite_non_saisie",
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


def _lien_planning(conn, pe_id) -> Optional[str]:
    """Le planning ouvert sur la fiche du dossier, à la semaine où il est
    planifié (planning_url.js : machine, semaine, dossier)."""
    if not pe_id:
        return None
    r = conn.execute("SELECT machine_id, planned_start FROM planning_entries WHERE id=?",
                     (pe_id,)).fetchone()
    if not r or not r["machine_id"]:
        return None
    url = f"/planning?machine={int(r['machine_id'])}&dossier={int(pe_id)}"
    debut = calage_cloture._dt(r["planned_start"]) if r["planned_start"] else None
    if debut:
        lundi = (debut - timedelta(days=debut.weekday())).date().isoformat()
        url += f"&semaine={lundi}"
    return url


def _candidats(conn, q: str, fictif: Optional[dict] = None, limite: int = 20) -> list:
    """Dossiers réels où rattacher un fictif : par référence, OF, réf produit,
    client ou désignation. Sans recherche, ceux qui portent le numéro noté par
    l'opérateur (souvent la réf produit). Les dossiers de la même machine et
    pas encore terminés passent devant."""
    q = (q or "").strip()
    if not q and fictif:
        q = str(fictif.get("of") or "").strip()
    if not q:
        return []
    like = f"%{q}%"
    machine = (fictif or {}).get("machine") or ""
    out, vus = [], set()
    for r in conn.execute(
            """SELECT pe.id, pe.reference AS no_dossier, pe.client, pe.description, pe.ref_produit,
                      pe.numero_of, pe.statut, pe.planned_start, m.nom AS machine
                 FROM planning_entries pe LEFT JOIN machines m ON m.id = pe.machine_id
                WHERE pe.reference NOT LIKE 'FICTIF:%'
                  AND (pe.reference LIKE ? OR COALESCE(pe.numero_of,'') LIKE ?
                       OR COALESCE(pe.ref_produit,'') LIKE ? OR COALESCE(pe.ref_produit_norm,'') LIKE ?
                       OR COALESCE(pe.client,'') LIKE ? OR COALESCE(pe.description,'') LIKE ?)
                ORDER BY (trim(COALESCE(m.nom,'')) = trim(?)) DESC,
                         (pe.statut <> 'termine') DESC, pe.id DESC
                LIMIT ?""", (like, like, like, like, like, like, machine, limite)).fetchall():
        if r["no_dossier"] and r["no_dossier"] not in vus:
            vus.add(r["no_dossier"])
            out.append({"no_dossier": r["no_dossier"], "client": r["client"],
                        "designation": r["description"], "ref_produit": r["ref_produit"],
                        "statut": r["statut"], "machine": r["machine"],
                        "planned_start": r["planned_start"], "source": "planning"})
    for r in conn.execute(
            """SELECT no_dossier, MAX(client) AS client, MAX(machine) AS machine,
                      MAX(date_operation) AS derniere
                 FROM production_data
                WHERE no_dossier LIKE ? AND no_dossier NOT LIKE 'FICTIF:%'
                GROUP BY no_dossier ORDER BY derniere DESC LIMIT 10""", (like,)).fetchall():
        if r["no_dossier"] not in vus:
            vus.add(r["no_dossier"])
            out.append({"no_dossier": r["no_dossier"], "client": r["client"],
                        "machine": r["machine"], "derniere": r["derniere"], "source": "saisies"})
    return out


def _saisies_machine(conn, pe_id) -> Dict[str, Any]:
    """Pour un dossier « en cours » sans saisie : sa fiche au planning et les
    saisies de sa machine depuis la veille de son démarrage prévu — c'est là
    qu'on voit une saisie faite sous un autre numéro, ou la fin oubliée."""
    pe = conn.execute(
        """SELECT pe.*, m.nom AS machine_nom, m.code AS machine_code
             FROM planning_entries pe LEFT JOIN machines m ON m.id = pe.machine_id
            WHERE pe.id=?""", (pe_id,)).fetchone()
    if not pe:
        return {"dossier": None, "saisies": []}
    debut = calage_cloture._dt(pe["planned_start"]) if pe["planned_start"] else None
    depuis = ((debut or _maintenant()) - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00")
    rows = conn.execute(
        """SELECT * FROM production_data
            WHERE COALESCE(est_annule,0)=0
              AND (trim(machine)=trim(?) OR trim(machine)=trim(?))
              AND date_operation >= ?
            ORDER BY date_operation DESC, id DESC LIMIT 80""",
        (pe["machine_nom"] or "", pe["machine_code"] or "", depuis)).fetchall()
    return {
        "dossier": {"id": pe["id"], "reference": pe["reference"], "client": pe["client"],
                    "description": pe["description"], "ref_produit": pe["ref_produit"],
                    "machine": pe["machine_nom"], "statut": pe["statut"],
                    "planned_start": pe["planned_start"], "planned_end": pe["planned_end"]},
        "saisies": [dict(r) for r in rows],
        "depuis": depuis,
    }


def regles_hors_compteur(conn) -> list:
    """Catégories d'écart réglées pour ne pas compter dans « À traiter ».

    Elles restent dans la liste, consultables et traitables : seul le
    compteur (pastilles, notification) les ignore."""
    try:
        return [r[0] for r in conn.execute(
            "SELECT regle FROM prod_ecarts_reglages WHERE compte = 0"
        ).fetchall()]
    except Exception:
        return []  # base non migrée : tout compte


@router.get("")
def lister(request: Request):
    _admin(request)
    with get_db() as conn:
        if "coherence_ecarts" not in coherence._tables(conn):
            return {"ecarts": [], "total": 0, "hors_compteur": []}
        res = coherence.lister(conn, famille="prod", statut="ouvert", limite=300)
        res["hors_compteur"] = regles_hors_compteur(conn)
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
        n, _sig = coherence.compter_ouverts(conn, "prod", exclure=regles_hors_compteur(conn))
    return {"n": n}


@router.get("/reglages")
def lire_reglages(request: Request):
    """Toutes les catégories de la famille prod, ouvertes ou non : on règle
    aussi une catégorie qui n'a aucun écart aujourd'hui."""
    _admin(request)
    from app.services.coherence import REGLES
    with get_db() as conn:
        hors = set(regles_hors_compteur(conn))
        ouverts = {}
        if "coherence_ecarts" in coherence._tables(conn):
            ouverts = {r["regle"]: int(r["n"]) for r in conn.execute(
                """SELECT regle, COUNT(*) AS n FROM coherence_ecarts
                    WHERE statut = 'ouvert' AND famille = 'prod' GROUP BY regle"""
            ).fetchall()}
    regles = [
        {"regle": r.code, "titre": r.titre, "description": r.description,
         "compte": r.code not in hors, "ouverts": ouverts.get(r.code, 0)}
        for r in REGLES.values() if r.famille == "prod"
    ]
    regles.sort(key=lambda x: (-x["ouverts"], x["titre"]))
    return {"regles": regles}


@router.put("/reglages")
async def ecrire_reglage(request: Request):
    user = _admin(request)
    body = await request.json()
    regle = str(body.get("regle") or "").strip()
    from app.services.coherence import REGLES
    if regle not in REGLES or REGLES[regle].famille != "prod":
        raise HTTPException(status_code=400, detail="Catégorie d'écart inconnue.")
    compte = 1 if body.get("compte") else 0
    with get_db() as conn:
        conn.execute(
            """INSERT INTO prod_ecarts_reglages (regle, compte, updated_at, updated_by)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(regle) DO UPDATE SET compte = excluded.compte,
                   updated_at = excluded.updated_at, updated_by = excluded.updated_by""",
            (regle, compte, _maintenant().isoformat(timespec="seconds"), _qui(user)),
        )
        conn.commit()
    try:
        # La pastille du portail est mise en cache : elle suit tout de suite.
        from app.services import notifications
        notifications._cache.pop("prod.ecarts", None)
    except Exception:
        pass
    log_action(
        user=user, action="UPDATE", module="saisies",
        objet=f"À traiter · {REGLES[regle].titre} : {'compté' if compte else 'non compté'}",
        detail={"regle": regle, "compte": bool(compte)},
        ip=request.client.host if request.client else None,
    )
    return {"success": True, "regle": regle, "compte": bool(compte)}


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
            out["candidats"] = _candidats(conn, "", e["donnees"])
            out["recherche"] = e["donnees"].get("of", "")
            out["no_dossier"] = e["objet_ref"]
            out["fictif"] = e["donnees"]
        elif action == "machine_saisies":
            out.update(_saisies_machine(conn, e["donnees"].get("planning_entry_id")))
            out["lien"] = _lien_planning(conn, e["donnees"].get("planning_entry_id"))
        elif action == "info_prod":
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
            out["lien"] = (_lien_planning(conn, e["donnees"].get("planning_entry_id"))
                           or (REGLES[e["regle"]].lien if e["regle"] in REGLES else "/prod"))
    return out


@router.get("/{ecart_id}/candidats")
def chercher_candidats(ecart_id: int, request: Request, q: str = ""):
    """Recherche du dossier où rattacher un fictif (référence, OF, réf produit,
    client, désignation)."""
    _admin(request)
    with get_db() as conn:
        e = _ecart(conn, ecart_id)
        return {"candidats": _candidats(conn, q, e["donnees"])}


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
        elif action == "info_prod":
            texte = str(body.get("texte") or "").strip()
            if not texte:
                raise HTTPException(status_code=400, detail="Info prod vide — « R.A.S. » si rien à signaler.")
            from app.services import produit_memoire as pm
            pm.enregistrer_info_prod(conn, e["objet_ref"], texte, qui)
            _resoudre(conn, ecart_id, qui, "Info prod saisie depuis MyProd.")
            detail = {"info_prod": texte[:200]}
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

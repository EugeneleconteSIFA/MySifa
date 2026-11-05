"""
MyTools › Étiquettes spécifiques — fonctions avancées (API).

Même préfixe que app/routers/print_specifiques.py (/api/print/specifiques) :
mêmes droits (ROLES_MYPRINT), même module MyPrint au journal d'audit, dont le
middleware trace chaque écriture.

  GET  /sources/{type}/recherche?q=&dossier=   enregistrements MySifa (dossier, of, produit, client, matiere, lot)
  GET  /sources/{type}/{id}                    champs à plat, liés compris (dossier → OF, produit, client)
  POST /sources/{type}/lire                    plusieurs enregistrements (impression en série depuis une liste)
  GET  /modeles/{id}/versions                  historique des versions
  POST /modeles/{id}/versions/{n}/restaurer    revenir à une version (enregistrée comme nouvelle version)
  GET  /modeles/{id}/compteurs                 dernier numéro mémorisé de chaque compteur / SSCC
  POST /modeles/{id}/compteurs/{nom}           corriger le dernier numéro d'un compteur (jamais d'un SSCC)
  POST /modeles/{id}/imprimer-serie            une étiquette (× quantité) par enregistrement
  POST /ia/controler                           contrôle avant impression par l'IA
  POST /modeles/{id}/soumettre | approuver | refuser   validation (approbation : rôles qualité)
  GET  /modeles/{id}/approbations              statut et historique d'approbation
  GET  /modeles/{id}/production                modèle approuvé, tel que l'atelier l'imprime
  POST /modeles/{id}/rendu                     étiquette remplie : valeurs, objets visibles, ZPL
  GET  /production/pour-dossier?dossier=&usage=   modèles approuvés applicables à un dossier
  GET  /balances · POST /balances · PATCH /balances/{id}   profils de balance (pesée)
  POST /modeles/{id}/reference · GET …/reference.png        étiquette de référence du client
  GET  /articles/erp?q=                        articles RVGI (miroir, lecture seule)
"""

from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.core.database import get_db
from app.routers.print_specifiques import (
    _SOURCES_DIR, _creer_job, _imprimante, _invalide, _modele, _now, _payload, _production, _quantite,
    _serialize_modele, _sortie, _user, concepteur,
)
from app.services import etiq_specifiques as es
from app.services.audit_service import log_action
from app.services.etiq_specifiques import EtiquetteInvalide

router = APIRouter(tags=["print"], prefix="/api/print/specifiques")


# ─── Sources de données ─────────────────────────────────────────────────

def _type_source(t: str) -> str:
    from app.services.etiq_sources import TYPES
    if t not in TYPES:
        raise HTTPException(status_code=404, detail="Source inconnue.")
    return t


@router.get("/sources/{type_}/recherche")
def sources_recherche(type_: str, request: Request, q: str = "", dossier: str = "", limit: int = 20):
    _user(request)
    from app.services.etiq_sources import rechercher
    with get_db() as conn:
        return {"items": rechercher(conn, _type_source(type_), q[:100], limit, dossier[:60])}


@router.get("/sources/{type_}/{id_}")
def sources_lire(type_: str, id_: int, request: Request):
    _user(request)
    from config import public_base_url
    from app.services.etiq_sources import lire
    with get_db() as conn:
        champs = lire(conn, _type_source(type_), id_, public_base_url())
    if not champs:
        raise HTTPException(status_code=404, detail="Enregistrement introuvable.")
    return {"id": id_, "type": type_, "champs": champs}


class LirePayload(BaseModel):
    ids: list[int] = []


@router.post("/sources/{type_}/lire")
def sources_lire_plusieurs(type_: str, payload: LirePayload, request: Request):
    """Lecture seule (POST pour porter la liste) : rien n'est écrit."""
    _user(request)
    from config import public_base_url
    from app.services.etiq_sources import lire
    ids = [int(i) for i in (payload.ids or [])][: es.QUANTITE_MAX]
    base = public_base_url()
    with get_db() as conn:
        t = _type_source(type_)
        out = [{"id": i, "champs": lire(conn, t, i, base)} for i in ids]
    return {"items": [x for x in out if x["champs"]]}


# ─── Versions ───────────────────────────────────────────────────────────

@router.get("/modeles/{modele_id}/versions")
def versions(modele_id: int, request: Request):
    _user(request)
    from app.services.etiq_bibliotheque import lister_versions
    with get_db() as conn:
        row = _modele(conn, modele_id)
        actuelle = {"version": row["version"] if "version" in row.keys() else 1, "nom": row["nom"],
                    "created_at": row["updated_at"] or row["created_at"],
                    "created_by": row["updated_by"] or row["created_by"], "actuelle": True,
                    "largeur_mm": row["largeur_mm"], "hauteur_mm": row["hauteur_mm"], "dpi": row["dpi"]}
        try:
            lay = json.loads(row["layout_json"] or "{}")
        except Exception:
            lay = {}
        actuelle["nb_elements"] = len(lay.get("elements") or [])
        actuelle["nb_variables"] = len(lay.get("variables") or [])
        return {"versions": [actuelle] + lister_versions(conn, modele_id)}


@router.get("/modeles/{modele_id}/versions/{version}")
def version_detail(modele_id: int, version: int, request: Request):
    _user(request)
    with get_db() as conn:
        _modele(conn, modele_id)
        v = conn.execute("SELECT * FROM etiq_modeles_versions WHERE modele_id=? AND version=?",
                         (modele_id, version)).fetchone()
    if not v:
        raise HTTPException(status_code=404, detail="Version introuvable.")
    try:
        layout = es.normaliser_layout(v["layout_json"])
    except EtiquetteInvalide:
        layout = {"elements": [], "variables": [], "calques": []}
    return {"version": v["version"], "largeur_mm": v["largeur_mm"], "hauteur_mm": v["hauteur_mm"],
            "dpi": v["dpi"], "layout": layout, "created_at": v["created_at"], "created_by": v["created_by"]}


@router.post("/modeles/{modele_id}/versions/{version}/restaurer")
def version_restaurer(modele_id: int, version: int, request: Request):
    user = _user(request)
    from app.services.etiq_bibliotheque import enregistrer_version, violations_verrous
    with get_db() as conn:
        row = _modele(conn, modele_id)
        v = conn.execute("SELECT * FROM etiq_modeles_versions WHERE modele_id=? AND version=?",
                         (modele_id, version)).fetchone()
        if not v:
            raise HTTPException(status_code=404, detail="Version introuvable.")
        try:
            ancien, cible = es.normaliser_layout(row["layout_json"]), es.normaliser_layout(v["layout_json"])
        except EtiquetteInvalide as e:
            _invalide(e)
        if not concepteur(user):
            ko = violations_verrous(ancien, cible)
            if ko:
                raise HTTPException(status_code=403, detail=" ".join(ko[:3]))
        suivante = enregistrer_version(conn, row, user.get("email"))
        conn.execute(
            "UPDATE etiq_modeles SET layout_json=?, largeur_mm=?, hauteur_mm=?, dpi=?, version=?, updated_at=?,"
            " updated_by=? WHERE id=?",
            (json.dumps(cible, ensure_ascii=False), v["largeur_mm"], v["hauteur_mm"], v["dpi"], suivante, _now(),
             user.get("email"), modele_id))
        conn.commit()
        res = _serialize_modele(_modele(conn, modele_id), complet=True)
    # Après le commit : log_action ouvre sa propre connexion.
    log_action(user=user, action="UPDATE", module="print", request=request,
               objet=f"Étiquette « {row['nom']} » · retour à la version {version}",
               detail={"avant": row["version"] if "version" in row.keys() else None, "apres": suivante})
    return res


# ─── Compteurs ──────────────────────────────────────────────────────────

@router.get("/modeles/{modele_id}/compteurs")
def compteurs(modele_id: int, request: Request):
    _user(request)
    with get_db() as conn:
        row = _modele(conn, modele_id)
        try:
            layout = es.normaliser_layout(row["layout_json"])
            plan = es.plan_serie(conn, modele_id, layout, 1)
            prochaines = es.valeurs_etiquette(layout, plan, 0, {})
        except EtiquetteInvalide as e:
            _invalide(e)
        out = []
        for v in layout["variables"]:
            if v["type"] not in ("compteur", "sscc"):
                continue
            cle = es.cle_compteur(modele_id, v)
            r = conn.execute("SELECT dernier, updated_at, updated_by FROM etiq_compteurs WHERE cle=?", (cle,)).fetchone()
            out.append({"nom": v["nom"], "libelle": v["libelle"], "type": v["type"],
                        "reprise": v.get("reprise", True), "dernier": r["dernier"] if r else None,
                        "maj_le": r["updated_at"] if r else None, "maj_par": r["updated_by"] if r else None,
                        "prochain": prochaines.get(v["nom"]), "prochain_numero": plan[v["nom"]]["premier"]})
    return {"compteurs": out}


class CompteurPayload(BaseModel):
    dernier: int


@router.post("/modeles/{modele_id}/compteurs/{nom}")
def compteur_corriger(modele_id: int, nom: str, payload: CompteurPayload, request: Request):
    """Reprise à un numéro donné (rouleau perdu, série refaite). Un SSCC ne se
    corrige jamais : revenir en arrière réémettrait un numéro déjà sorti."""
    user = _user(request)
    if payload.dernier < 0:
        raise HTTPException(status_code=400, detail="Numéro invalide — entier positif attendu.")
    with get_db() as conn:
        row = _modele(conn, modele_id)
        layout = es.normaliser_layout(row["layout_json"])
        var = next((v for v in layout["variables"] if v["nom"] == nom), None)
        if not var or var["type"] != "compteur":
            raise HTTPException(status_code=404 if not var else 400,
                                detail="Compteur introuvable." if not var else "Un SSCC ne se corrige pas.")
        cle = es.cle_compteur(modele_id, var)
        avant = conn.execute("SELECT dernier FROM etiq_compteurs WHERE cle=?", (cle,)).fetchone()
        conn.execute(
            "INSERT INTO etiq_compteurs (cle,dernier,updated_at,updated_by) VALUES (?,?,?,?) "
            "ON CONFLICT(cle) DO UPDATE SET dernier=excluded.dernier, updated_at=excluded.updated_at,"
            " updated_by=excluded.updated_by", (cle, payload.dernier, _now(), user.get("email")))
        conn.commit()
    log_action(user=user, action="UPDATE", module="print", request=request,
               objet=f"Étiquette « {row['nom']} » · compteur {var['libelle']}",
               detail={"avant": avant["dernier"] if avant else None, "apres": payload.dernier})
    return {"ok": True}


# ─── Impression en série (une étiquette par enregistrement) ────────────

class SeriePayload(BaseModel):
    imprimante_id: int
    enregistrements: list[dict] = []
    quantite: int = 1          # étiquettes différentes par enregistrement
    exemplaires: int = 1       # copies identiques de chacune
    departs: dict = {}


@router.post("/modeles/{modele_id}/imprimer-serie")
def imprimer_serie(modele_id: int, payload: SeriePayload, request: Request):
    """Chemin d'impression intégré (ZPL ou PDF selon l'imprimante). Quand le
    module d'impression (static/mysifa_etiq_impression.js) est chargé, la page
    passe par lui ; celui-ci reste le repli."""
    user = _user(request)
    email = user.get("email")
    enr = [{str(k)[:40]: str(v)[:500] for k, v in (e or {}).items()} for e in (payload.enregistrements or [])]
    if not enr:
        raise HTTPException(status_code=400, detail="Aucun enregistrement à imprimer.")
    par = max(1, min(es.QUANTITE_MAX, int(payload.quantite or 1)))
    total = _quantite(len(enr) * par)
    ex = max(1, min(99, int(payload.exemplaires or 1)))
    with get_db() as conn:
        row = _production(conn, modele_id)   # version approuvée
        imp = _imprimante(conn, payload.imprimante_id)
        sortie = _sortie(imp)
        if conn.in_transaction:
            conn.commit()
        conn.execute("BEGIN IMMEDIATE")
        try:
            layout = es.normaliser_layout(row["layout_json"])
            for i, e in enumerate(enr):
                try:
                    es.controler_saisies(layout, e)
                except EtiquetteInvalide as err:
                    raise EtiquetteInvalide(f"Ligne {i + 1} : {err}")
            p = es.plan_serie(conn, modele_id, layout, total, payload.departs)
            es.reserver_serie(conn, p, total, email)
            from datetime import datetime
            maintenant = datetime.now()
            valeurs = [es.valeurs_etiquette(layout, p, i, enr[i // par], maintenant) for i in range(total)]
            zpl = es.rendre_lot(layout, row["largeur_mm"], row["hauteur_mm"], row["dpi"], valeurs, ex)
        except EtiquetteInvalide as e:
            conn.rollback()
            _invalide(e)
        plages = {nom: {"premier": valeurs[0][nom], "dernier": valeurs[-1][nom]} for nom in p}
        cur = conn.execute(
            "INSERT INTO etiq_impressions (modele_id,imprimante_id,quantite,exemplaires,valeurs_json,plages_json,"
            "layout_json,zpl,valeurs_serie_json,format_sortie,created_at,created_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (modele_id, imp["id"], total, ex, json.dumps({"_enregistrements": len(enr), "_par": par}),
             json.dumps(plages, ensure_ascii=False), row["layout_json"], zpl,
             json.dumps(valeurs, ensure_ascii=False), sortie, _now(), email))
        impression_id = cur.lastrowid
        conn.commit()
        try:
            corps = _payload(sortie, zpl, layout, row["largeur_mm"], row["hauteur_mm"], valeurs, ex)
        except Exception as e:
            raise HTTPException(status_code=500, detail=(
                f"Numéros réservés mais rendu en échec ({type(e).__name__}). "
                "Relancer depuis l'historique (Réimprimer)."))
        job_id = _creer_job(conn, imp, corps, sortie, email, {"modele_id": modele_id, "impression_id": impression_id})
        conn.execute("UPDATE etiq_impressions SET job_id=? WHERE id=?", (job_id, impression_id))
        conn.commit()
    log_action(user=user, action="CREATE", module="print", request=request,
               objet=f"Étiquette « {row['nom']} » · série de {len(enr)} enregistrement(s), {total} étiquette(s)",
               detail={"imprimante": imp["nom"], "plages": plages})
    return {"ok": True, "impression_id": impression_id, "job_id": job_id, "sortie": sortie,
            "imprimante": imp["nom"], "quantite": total, "plages": plages}


# ─── Contrôle IA avant impression ──────────────────────────────────────

class ControlePayload(BaseModel):
    modele_id: Optional[int] = None
    largeur_mm: float = 100
    hauteur_mm: float = 150
    dpi: int = 203
    layout: dict = {}
    valeurs: dict = {}
    usage: str = ""
    alertes: list = []
    image_png: str = ""
    modele: Optional[str] = None


@router.post("/ia/controler")
def ia_controler(payload: ControlePayload, request: Request):
    user = _user(request)
    from app.services import ia_usage
    from app.services.etiq_specifiques_ia_controle import controler
    l, h, d = es.normaliser_format(payload.largeur_mm, payload.hauteur_mm, payload.dpi)
    try:
        layout = es.normaliser_layout(payload.layout)
        valeurs = {str(k)[:40]: str(v)[:500] for k, v in (payload.valeurs or {}).items()}
        alertes = [str(a)[:300] for a in (payload.alertes or [])][:40]
        with ia_usage.suivi(user, "etiquettes", "controle"):
            return controler(l, h, d, layout, valeurs, (payload.usage or "")[:20], alertes,
                             payload.image_png or "", modele=payload.modele)
    except EtiquetteInvalide as e:
        _invalide(e)


# ─── Validation des modèles ────────────────────────────────────────────

def _qualite(user: dict) -> bool:
    from app.routers.qualite import ROLES_QUALITE
    from app.services.auth_service import is_superadmin
    return is_superadmin(user) or user.get("role") in ROLES_QUALITE


class ApprobationPayload(BaseModel):
    commentaire: str = ""


def _changer_statut(modele_id: int, request: Request, action: str, commentaire: str) -> dict:
    user = _user(request)
    from app.services.etiq_validation import journaliser
    from app.services.auth_service import is_superadmin
    with get_db() as conn:
        row = _modele(conn, modele_id)
        version = int(row["version"] or 1)
        statut = row["statut_validation"] or "brouillon"
        if action == "demande":
            if statut == "approuve":
                raise HTTPException(status_code=409, detail="Version déjà approuvée.")
            conn.execute("UPDATE etiq_modeles SET statut_validation='a_approuver' WHERE id=?", (modele_id,))
        else:
            if not _qualite(user):
                raise HTTPException(status_code=403, detail="Approbation réservée aux rôles qualité.")
            if action == "approuve" and row["updated_by"] == user.get("email") and not is_superadmin(user):
                raise HTTPException(status_code=403, detail="Une modification s'approuve par une autre personne que son auteur.")
            if action == "refuse" and not commentaire.strip():
                raise HTTPException(status_code=400, detail="Motif du refus obligatoire.")
            if action == "approuve":
                conn.execute("UPDATE etiq_modeles SET statut_validation='approuve', version_approuvee=?, approuve_par=?,"
                             " approuve_le=? WHERE id=?", (version, user.get("email"), _now(), modele_id))
            else:
                conn.execute("UPDATE etiq_modeles SET statut_validation='brouillon' WHERE id=?", (modele_id,))
        journaliser(conn, modele_id, version, action, user.get("email"), commentaire)
        conn.commit()
        res = _serialize_modele(_modele(conn, modele_id), complet=True)
    libelle = {"demande": "soumise à approbation", "approuve": "approuvée", "refuse": "refusée"}[action]
    log_action(user=user, action="VALIDATE" if action == "approuve" else "UPDATE", module="print", request=request,
               objet=f"Étiquette « {row['nom']} » · version {version} {libelle}", detail={"commentaire": commentaire[:300]})
    return res


@router.post("/modeles/{modele_id}/soumettre")
def soumettre(modele_id: int, payload: ApprobationPayload, request: Request):
    return _changer_statut(modele_id, request, "demande", payload.commentaire or "")


@router.post("/modeles/{modele_id}/approuver")
def approuver(modele_id: int, payload: ApprobationPayload, request: Request):
    return _changer_statut(modele_id, request, "approuve", payload.commentaire or "")


@router.post("/modeles/{modele_id}/refuser")
def refuser(modele_id: int, payload: ApprobationPayload, request: Request):
    return _changer_statut(modele_id, request, "refuse", payload.commentaire or "")


@router.get("/modeles/{modele_id}/approbations")
def approbations(modele_id: int, request: Request):
    user = _user(request)
    from app.services.etiq_validation import etat, historique
    with get_db() as conn:
        row = _modele(conn, modele_id)
        return dict(etat(row), version=row["version"], historique=historique(conn, modele_id),
                    peut_approuver=_qualite(user))


@router.get("/modeles/{modele_id}/production")
def production(modele_id: int, request: Request):
    _user(request)
    with get_db() as conn:
        m = dict(_production(conn, modele_id))
    m.pop("layout_json", None)
    return m


class RenduPayload(BaseModel):
    enregistrement: dict = {}
    source: Optional[dict] = None     # {"type": "dossier", "id": 12} : remplit les variables liées
    index: int = 0
    brouillon: bool = False           # True : version en cours d'édition, pas la production


@router.post("/modeles/{modele_id}/rendu")
def rendu(modele_id: int, payload: RenduPayload, request: Request):
    """Lecture seule (aucun compteur réservé). Sert à l'impression automatique,
    au kiosque et à l'aperçu avec données."""
    _user(request)
    from config import public_base_url
    from app.services.etiq_sources import lire
    from app.services.etiq_validation import rendu as faire
    with get_db() as conn:
        _modele(conn, modele_id)
        enr = dict(payload.enregistrement or {})
        if payload.source and payload.source.get("type"):
            champs = lire(conn, _type_source(str(payload.source["type"])), int(payload.source.get("id") or 0), public_base_url())
            lay = (_production(conn, modele_id) if not payload.brouillon else
                   {"layout": es.normaliser_layout(_modele(conn, modele_id)["layout_json"])})["layout"]
            for v in lay["variables"]:
                if v["type"] == "source" and v.get("champ") in champs and v["nom"] not in enr:
                    enr[v["nom"]] = champs[v["champ"]]
        try:
            return faire(conn, modele_id, enr, max(0, min(es.QUANTITE_MAX, payload.index)), not payload.brouillon)
        except EtiquetteInvalide as e:
            raise HTTPException(status_code=409, detail=str(e))


@router.get("/production/pour-dossier")
def pour_dossier(request: Request, dossier: str = "", usage: str = ""):
    _user(request)
    from app.services.etiq_validation import pour_dossier as chercher
    with get_db() as conn:
        return {"modeles": chercher(conn, dossier[:60], usage[:20])}


# ─── Balances (pesée) ──────────────────────────────────────────────────

_CHAMPS_BALANCE = ("nom", "vitesse", "bits", "parite", "stop", "commande", "motif", "unite", "decimales",
                   "stable_seulement", "actif")


class BalancePayload(BaseModel):
    nom: Optional[str] = None
    vitesse: Optional[int] = None
    bits: Optional[int] = None
    parite: Optional[str] = None
    stop: Optional[int] = None
    commande: Optional[str] = None
    motif: Optional[str] = None
    unite: Optional[str] = None
    decimales: Optional[int] = None
    stable_seulement: Optional[bool] = None
    actif: Optional[bool] = None


def _balance_valide(d: dict) -> dict:
    import re as _re
    out = {}
    if d.get("nom") is not None:
        out["nom"] = d["nom"].strip()[:80] or "Balance"
    if d.get("vitesse") is not None:
        if d["vitesse"] not in (1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200):
            raise HTTPException(status_code=400, detail="Vitesse invalide — 1 200 à 115 200 bauds.")
        out["vitesse"] = d["vitesse"]
    if d.get("bits") is not None:
        out["bits"] = 7 if d["bits"] == 7 else 8
    if d.get("parite") is not None:
        out["parite"] = d["parite"] if d["parite"] in ("none", "even", "odd") else "none"
    if d.get("stop") is not None:
        out["stop"] = 2 if d["stop"] == 2 else 1
    if d.get("commande") is not None:
        out["commande"] = d["commande"][:40]
    if d.get("motif") is not None:
        try:
            _re.compile(d["motif"])
        except _re.error:
            raise HTTPException(status_code=400, detail="Motif de lecture invalide (expression régulière).")
        out["motif"] = d["motif"][:200]
    if d.get("unite") is not None:
        out["unite"] = d["unite"][:10]
    if d.get("decimales") is not None:
        out["decimales"] = max(0, min(4, d["decimales"]))
    for k in ("stable_seulement", "actif"):
        if d.get(k) is not None:
            out[k] = 1 if d[k] else 0
    return out


@router.get("/balances")
def balances(request: Request):
    _user(request)
    with get_db() as conn:
        return {"balances": [dict(r) for r in conn.execute(
            "SELECT id,cle,nom,vitesse,bits,parite,stop,commande,motif,unite,decimales,stable_seulement,actif"
            " FROM etiq_balances ORDER BY nom").fetchall()]}


@router.post("/balances")
def balance_creer(payload: BalancePayload, request: Request):
    user = _user(request)
    if not concepteur(user):
        raise HTTPException(status_code=403, detail="Réservé aux concepteurs d'étiquettes.")
    d = _balance_valide(payload.dict())
    import secrets as _s
    with get_db() as conn:
        cur = conn.execute("INSERT INTO etiq_balances (cle,nom,created_at) VALUES (?,?,?)",
                           ("b_" + _s.token_hex(4), d.get("nom") or "Balance", _now()))
        bid = cur.lastrowid
        if d:
            conn.execute(f"UPDATE etiq_balances SET {', '.join(k + '=?' for k in d)} WHERE id=?", (*d.values(), bid))
        conn.commit()
    return {"ok": True, "id": bid}


@router.patch("/balances/{balance_id}")
def balance_modifier(balance_id: int, payload: BalancePayload, request: Request):
    user = _user(request)
    if not concepteur(user):
        raise HTTPException(status_code=403, detail="Réservé aux concepteurs d'étiquettes.")
    d = _balance_valide(payload.dict())
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM etiq_balances WHERE id=?", (balance_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Balance introuvable.")
        if d:
            d["updated_at"], d["updated_by"] = _now(), user.get("email")
            conn.execute(f"UPDATE etiq_balances SET {', '.join(k + '=?' for k in d)} WHERE id=?", (*d.values(), balance_id))
            conn.commit()
    return {"ok": True}


# ─── Étiquette de référence du client (comparaison visuelle) ───────────

def _chemin_reference(modele_id: int) -> str:
    import os
    return os.path.join(_SOURCES_DIR, f"reference_{int(modele_id)}.png")


@router.post("/modeles/{modele_id}/reference")
async def reference_deposer(modele_id: int, request: Request):
    """Image ou PDF (première page) de l'étiquette du client, ramené en PNG.
    Corps : multipart, champ « fichier »."""
    user = _user(request)
    import io
    import os
    form = await request.form()
    f = form.get("fichier")
    if not f or not getattr(f, "filename", ""):
        raise HTTPException(status_code=400, detail="Joindre l'image ou le PDF de référence.")
    brut = await f.read()
    if not brut or len(brut) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Fichier vide ou de plus de 15 Mo.")
    from PIL import Image
    try:
        if brut[:4] == b"%PDF":
            import pypdfium2
            doc = pypdfium2.PdfDocument(brut)
            img = doc[0].render(scale=200 / 72).to_pil()
        else:
            img = Image.open(io.BytesIO(brut))
            img.load()
    except ImportError:
        raise HTTPException(status_code=400, detail="Lecture des PDF indisponible sur ce serveur — déposer une image.")
    except Exception:
        raise HTTPException(status_code=400, detail="Fichier illisible — image PNG, JPEG ou PDF.")
    img = img.convert("RGB")
    img.thumbnail((2400, 2400))
    with get_db() as conn:
        row = _modele(conn, modele_id)
    os.makedirs(_SOURCES_DIR, exist_ok=True)
    img.save(_chemin_reference(modele_id), "PNG")
    log_action(user=user, action="UPDATE", module="print", request=request,
               objet=f"Étiquette « {row['nom']} » · référence client déposée")
    return {"ok": True, "largeur_px": img.size[0], "hauteur_px": img.size[1]}


@router.get("/modeles/{modele_id}/reference.png")
def reference_lire(modele_id: int, request: Request):
    import os
    from fastapi.responses import FileResponse
    _user(request)
    with get_db() as conn:
        _modele(conn, modele_id)
    chemin = _chemin_reference(modele_id)
    if not os.path.exists(chemin):
        raise HTTPException(status_code=404, detail="Aucune étiquette de référence.")
    return FileResponse(chemin, media_type="image/png", headers={"Cache-Control": "no-store"})


# ─── Articles RVGI (miroir, lecture seule) ─────────────────────────────

@router.get("/articles/erp")
def articles_erp(request: Request, q: str = "", limit: int = 20):
    """Articles vendus (fic_art) du miroir RVGI : référence code1/code2,
    libellés, référence client, format, poids. Lecture seule, corbeille = 0."""
    _user(request)
    from app.services import erp_mirror as miroir
    if not miroir.miroir_present():
        return {"items": [], "miroir": False}
    q = (q or "").strip()[:60]
    with miroir.get_erp_db() as c:
        if "fic_art" not in miroir.tables_presentes(c):
            return {"items": [], "miroir": False}
        sql = ("SELECT code1, code2, libc1, libc2, libc3, libc4, cltc2, ftl, fth, pdsn FROM fic_art WHERE corbeille = 0")
        params: list = []
        if q:
            sql += " AND (libc1 LIKE ? OR cltc2 LIKE ? OR (code1 || '/' || code2) LIKE ?)"
            params += [f"%{q}%"] * 3
        sql += " ORDER BY code1, code2 LIMIT ?"
        params.append(max(1, min(50, int(limit or 20))))
        rows = c.execute(sql, params).fetchall()
    from app.services.etiq_sources import article_erp_champs
    return {"items": [article_erp_champs(dict(r)) for r in rows], "miroir": True}

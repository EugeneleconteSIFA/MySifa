"""
MyTools › Étiquettes — atelier : impression automatique, parc d'imprimantes,
kiosque. Compagnon de app/routers/etiq_impression.py (même famille d'API).

Préfixe /api/tools/etiquettes/atelier

  GET    /regles                  règles + référentiels (machines, codes d'opération, modèles, imprimantes)
  POST   /regles                  créer          (admin imprimantes)
  PATCH  /regles/{id}             modifier       (admin imprimantes)
  DELETE /regles/{id}             supprimer      (admin imprimantes)
  POST   /regles/{id}/essai       déclenche la règle comme une saisie (dossier facultatif)
  GET    /parc                    état de chaque imprimante (?rafraichir=1 : interroge le réseau)
  GET    /kiosque                 modèles approuvés et leurs champs à saisir
  GET    /kiosque/scan?code=      un code scanné → modèle ou dossier (champs pré-remplis)
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from config import ETIQ_PORTS_RESEAU, ETIQ_TIMEOUT_RESEAU_S
from app.core.database import get_db
from app.routers.etiq_impression import _admin, _colonnes, _exiger_admin, _now, _profil, _user
from app.services import etiq_auto
from app.services.audit_service import log_action
from app.services.etiq_envoi import etat_complet

router = APIRouter(tags=["print"], prefix="/api/tools/etiquettes/atelier")


# ─── Référentiels ───────────────────────────────────────────────────────

def _machines(conn) -> list:
    cols = _colonnes(conn, "machines")
    if not cols:
        return []
    filtre = " WHERE COALESCE(actif,1)=1" if "actif" in cols else ""
    return [{"id": r["id"], "nom": r["nom"]} for r in
            conn.execute(f"SELECT id, nom FROM machines{filtre} ORDER BY nom COLLATE NOCASE").fetchall()]


def _operations(conn) -> list:
    try:
        from app.services.operations_config import load_operations_dict
        ops = load_operations_dict(conn)
    except Exception:
        ops = {}
    return [{"code": c, "libelle": (o or {}).get("label") or c} for c, o in sorted(ops.items())]


def _modeles(conn, approuves_seulement: bool) -> list:
    cols = _colonnes(conn, "etiq_modeles")
    if not cols:
        return []
    champs = ["id", "nom", "largeur_mm", "hauteur_mm", "layout_json"]
    for c in ("usage", "client", "statut_validation", "version_approuvee", "dossier_id"):
        if c in cols:
            champs.append(c)
    q = f"SELECT {','.join(champs)} FROM etiq_modeles WHERE archive=0"
    if approuves_seulement and "version_approuvee" in cols:
        q += " AND version_approuvee IS NOT NULL"
    out = []
    for r in conn.execute(q + " ORDER BY nom COLLATE NOCASE").fetchall():
        d = {k: r[k] for k in r.keys() if k != "layout_json"}
        try:
            lay = json.loads(r["layout_json"] or "{}")
        except ValueError:
            lay = {}
        d["saisies"] = [{"nom": v.get("nom"), "libelle": v.get("libelle") or v.get("nom"), "type": v.get("type"),
                         "champ": v.get("champ") or "", "valeur": v.get("valeur") or "",
                         "obligatoire": bool(v.get("obligatoire", v.get("type") == "saisie"))}
                        for v in lay.get("variables") or [] if v.get("type") in ("saisie", "source")]
        d["approuve"] = ("version_approuvee" not in cols) or bool(r["version_approuvee"])
        out.append(d)
    return out


def _imprimantes(conn) -> list:
    cols = _colonnes(conn, "imprimantes")
    return [_profil(r, cols) for r in conn.execute(
        "SELECT * FROM imprimantes WHERE actif=1 ORDER BY nom COLLATE NOCASE").fetchall()]


# ─── Règles d'impression automatique ────────────────────────────────────

def _regles(conn) -> list:
    if not _colonnes(conn, "etiq_regles_auto"):
        raise HTTPException(status_code=503, detail="Impression automatique indisponible : migration en attente.")
    rows = conn.execute(
        "SELECT r.*, m.nom AS machine_nom, e.nom AS modele_nom, i.nom AS imprimante_nom "
        "FROM etiq_regles_auto r LEFT JOIN machines m ON m.id=r.machine_id "
        "LEFT JOIN etiq_modeles e ON e.id=r.modele_id LEFT JOIN imprimantes i ON i.id=r.imprimante_id "
        "ORDER BY m.nom COLLATE NOCASE, r.operation_code").fetchall()
    return [dict(r) for r in rows]


@router.get("/regles")
def lister_regles(request: Request):
    user = _user(request)
    with get_db() as conn:
        return {"regles": _regles(conn), "machines": _machines(conn), "operations": _operations(conn),
                "modeles": [{"id": m["id"], "nom": m["nom"], "approuve": m["approuve"]} for m in _modeles(conn, False)],
                "imprimantes": [{"id": p["id"], "nom": p["nom"], "modes": p["modes"]} for p in _imprimantes(conn)],
                "peut_administrer": _admin(user)}


class ReglePayload(BaseModel):
    machine_id: Optional[int] = None
    operation_code: Optional[str] = None
    modele_id: Optional[int] = None
    imprimante_id: Optional[int] = None
    exemplaires: Optional[int] = None
    fin_dossier_seulement: Optional[bool] = None
    actif: Optional[bool] = None
    note: Optional[str] = None


def _valider_regle(conn, v: dict) -> dict:
    out = {}
    if "machine_id" in v:
        if not conn.execute("SELECT 1 FROM machines WHERE id=?", (v["machine_id"],)).fetchone():
            raise HTTPException(status_code=400, detail="Machine introuvable.")
        out["machine_id"] = int(v["machine_id"])
    if "operation_code" in v:
        code = str(v["operation_code"] or "").strip()
        if code not in {o["code"] for o in _operations(conn)}:
            raise HTTPException(status_code=400, detail="Code d'opération inconnu.")
        out["operation_code"] = code
    if "modele_id" in v:
        if not conn.execute("SELECT 1 FROM etiq_modeles WHERE id=? AND archive=0", (v["modele_id"],)).fetchone():
            raise HTTPException(status_code=400, detail="Modèle introuvable.")
        out["modele_id"] = int(v["modele_id"])
    if "imprimante_id" in v:
        row = conn.execute("SELECT * FROM imprimantes WHERE id=? AND actif=1", (v["imprimante_id"],)).fetchone()
        if not row:
            raise HTTPException(status_code=400, detail="Imprimante introuvable.")
        if not {"reseau", "agent"} & set(_profil(row, _colonnes(conn, "imprimantes"))["modes"]):
            raise HTTPException(status_code=400, detail="Imprimante sans envoi direct (réseau ou agent) : "
                                                        "une impression automatique n'aurait personne pour la recevoir.")
        out["imprimante_id"] = int(v["imprimante_id"])
    if "exemplaires" in v:
        out["exemplaires"] = max(1, min(99, int(v["exemplaires"] or 1)))
    if "fin_dossier_seulement" in v:
        out["fin_dossier_seulement"] = 1 if v["fin_dossier_seulement"] else 0
    if "actif" in v:
        out["actif"] = 1 if v["actif"] else 0
    if "note" in v:
        out["note"] = (v["note"] or "").strip()[:300] or None
    return out


@router.post("/regles")
def creer_regle(payload: ReglePayload, request: Request):
    user = _exiger_admin(request)
    v = {k: val for k, val in payload.model_dump().items() if k in payload.model_fields_set}
    with get_db() as conn:
        _regles(conn)
        d = _valider_regle(conn, v)
        for k in ("machine_id", "operation_code", "modele_id", "imprimante_id"):
            if k not in d:
                raise HTTPException(status_code=400, detail="Machine, code d'opération, modèle et imprimante requis.")
        d.update(created_at=_now(), created_by=user.get("email"))
        cur = conn.execute(f"INSERT INTO etiq_regles_auto ({','.join(d)}) VALUES ({','.join('?' * len(d))})",
                           tuple(d.values()))
        conn.commit()
        rid = cur.lastrowid
        r = next(x for x in _regles(conn) if x["id"] == rid)
    log_action(user=user, action="CREATE", module="print",
               objet=f"Impression automatique · {r['machine_nom']} · code {r['operation_code']}",
               detail={"modele": r["modele_nom"], "imprimante": r["imprimante_nom"]}, request=request)
    return r


@router.patch("/regles/{rid}")
def modifier_regle(rid: int, payload: ReglePayload, request: Request):
    user = _exiger_admin(request)
    v = {k: val for k, val in payload.model_dump().items() if k in payload.model_fields_set}
    with get_db() as conn:
        avant = next((x for x in _regles(conn) if x["id"] == rid), None)
        if not avant:
            raise HTTPException(status_code=404, detail="Règle introuvable.")
        d = _valider_regle(conn, v)
        if d:
            d.update(updated_at=_now(), updated_by=user.get("email"))
            conn.execute(f"UPDATE etiq_regles_auto SET {','.join(k + '=?' for k in d)} WHERE id=?", (*d.values(), rid))
            conn.commit()
        r = next(x for x in _regles(conn) if x["id"] == rid)
    log_action(user=user, action="UPDATE", module="print",
               objet=f"Impression automatique · {r['machine_nom']} · code {r['operation_code']}",
               detail={k: {"avant": avant.get(k), "apres": r.get(k)} for k in d if k not in ("updated_at", "updated_by")},
               request=request)
    return r


@router.delete("/regles/{rid}")
def supprimer_regle(rid: int, request: Request):
    user = _exiger_admin(request)
    with get_db() as conn:
        r = next((x for x in _regles(conn) if x["id"] == rid), None)
        if not r:
            raise HTTPException(status_code=404, detail="Règle introuvable.")
        conn.execute("DELETE FROM etiq_regles_auto WHERE id=?", (rid,))
        conn.commit()
    log_action(user=user, action="DELETE", module="print",
               objet=f"Impression automatique · {r['machine_nom']} · code {r['operation_code']}", request=request)
    return {"ok": True}


class EssaiPayload(BaseModel):
    dossier: Optional[str] = None


@router.post("/regles/{rid}/essai")
def essayer_regle(rid: int, payload: EssaiPayload, request: Request):
    """Joue la règle comme le ferait une saisie, tout de suite (pas de fil)."""
    user = _exiger_admin(request)
    with get_db() as conn:
        r = next((x for x in _regles(conn) if x["id"] == rid), None)
    if not r:
        raise HTTPException(status_code=404, detail="Règle introuvable.")
    res = etiq_auto.apres_saisie(machine_id=r["machine_id"], machine_nom=r["machine_nom"] or "", code=r["operation_code"],
                                 fin_dossier=True, no_dossier=(payload.dossier or "").strip()[:60] or None,
                                 operateur=user.get("nom") or "", email=user.get("email"), synchrone=True)
    return {"resultats": [x for x in (res or []) if x.get("regle_id") in (None, rid)] or res or []}


# ─── Parc ───────────────────────────────────────────────────────────────

@router.get("/parc")
def parc(request: Request, rafraichir: int = 0):
    _user(request)
    with get_db() as conn:
        profils = _imprimantes(conn)
        depuis = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S")
        stats = {}
        if _colonnes(conn, "etiq_journal_impression"):
            for r in conn.execute(
                    "SELECT imprimante_id, SUM(etiquettes*exemplaires) AS n, MAX(created_at) AS dernier, "
                    "SUM(CASE WHEN created_at>=? THEN etiquettes*exemplaires ELSE 0 END) AS n30, "
                    "SUM(CASE WHEN statut='erreur' AND created_at>=? THEN 1 ELSE 0 END) AS erreurs30 "
                    "FROM etiq_journal_impression WHERE statut NOT IN ('telecharge','pdf','prepare') "
                    "GROUP BY imprimante_id", (depuis, depuis)).fetchall():
                stats[r["imprimante_id"]] = dict(r)
        etats = {r["imprimante_id"]: dict(r) for r in conn.execute("SELECT * FROM etiq_parc_etat").fetchall()} \
            if _colonnes(conn, "etiq_parc_etat") else {}
    interrogeables = [p for p in profils if "reseau" in p["modes"] and p["langage"] == "zpl"]
    if rafraichir and interrogeables:
        t = min(2.5, ETIQ_TIMEOUT_RESEAU_S)
        with ThreadPoolExecutor(max_workers=min(8, len(interrogeables))) as ex:
            resultats = list(ex.map(lambda p: (p["id"], etat_complet(p["ip"], int(p["port"]), t)), interrogeables))
        with get_db() as conn:
            if _colonnes(conn, "etiq_parc_etat"):
                for pid, e in resultats:
                    conn.execute("INSERT INTO etiq_parc_etat (imprimante_id,vu_le,en_ligne,etat_json) VALUES (?,?,?,?) "
                                 "ON CONFLICT(imprimante_id) DO UPDATE SET vu_le=excluded.vu_le, "
                                 "en_ligne=excluded.en_ligne, etat_json=excluded.etat_json",
                                 (pid, _now(), 1 if e.get("en_ligne") else 0, json.dumps(e, ensure_ascii=False)))
                    etats[pid] = {"vu_le": _now(), "en_ligne": 1 if e.get("en_ligne") else 0,
                                  "etat_json": json.dumps(e, ensure_ascii=False)}
                conn.commit()
    out = []
    for p in profils:
        e = etats.get(p["id"]) or {}
        try:
            detail = json.loads(e.get("etat_json") or "{}")
        except ValueError:
            detail = {}
        s = stats.get(p["id"]) or {}
        out.append({"id": p["id"], "nom": p["nom"], "poste": p["poste"], "langage": p["langage"], "dpi": p["dpi"],
                    "ip": p["ip"], "port": p["port"], "modes": p["modes"], "rfid": p["rfid"],
                    "interrogeable": p in interrogeables, "vu_le": e.get("vu_le"), "etat": detail,
                    "etiquettes_total": s.get("n") or 0, "etiquettes_30j": s.get("n30") or 0,
                    "erreurs_30j": s.get("erreurs30") or 0, "derniere_impression": s.get("dernier")})
    return {"imprimantes": out, "ports_reseau": list(ETIQ_PORTS_RESEAU)}


# ─── Kiosque ────────────────────────────────────────────────────────────

@router.get("/kiosque")
def kiosque(request: Request):
    _user(request)
    with get_db() as conn:
        return {"modeles": [m for m in _modeles(conn, True) if m["approuve"]]}


@router.get("/kiosque/scan")
def kiosque_scan(request: Request, code: str):
    """Code scanné à l'atelier : n° ou nom de modèle, sinon référence dossier."""
    _user(request)
    c = (code or "").strip()[:120]
    if not c:
        raise HTTPException(status_code=400, detail="Code vide.")
    with get_db() as conn:
        modeles = [m for m in _modeles(conn, True) if m["approuve"]]
        num = c[1:] if c[:1] in ("M", "m") and c[1:].isdigit() else c
        m = next((x for x in modeles if str(x["id"]) == num or x["nom"].lower() == c.lower()), None)
        if m:
            return {"type": "modele", "modele": m}
        pe = conn.execute("SELECT id, reference FROM planning_entries WHERE reference=? ORDER BY id DESC LIMIT 1",
                          (c,)).fetchone() if _colonnes(conn, "planning_entries") else None
        if pe:
            try:
                from app.services import etiq_sources
                champs = etiq_sources.lire(conn, "dossier", pe["id"])
            except Exception:
                champs = {}
            return {"type": "dossier", "id": pe["id"], "reference": pe["reference"], "champs": champs}
    raise HTTPException(status_code=404, detail=f"« {c} » : ni modèle approuvé, ni dossier connu.")

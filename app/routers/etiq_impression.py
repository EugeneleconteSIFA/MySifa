"""
MyTools › Étiquettes — chaîne d'impression : profils d'imprimante, impression
d'un modèle vectoriel ou d'un rendu (PDF / image), journal, vérification par
scan, aperçu interne.

Préfixe /api/tools/etiquettes/impression (module « tools » de la taxonomie
d'audit ; chaque écriture journalise elle-même sous « print »).

  GET    /config                         langages, modes, ports admis, droits
  GET    /profils                        imprimantes actives (toutes pour l'admin, ?tous=1)
  POST   /profils                        créer un profil              (admin imprimantes)
  PATCH  /profils/{id}                   modifier                     (admin imprimantes)
  DELETE /profils/{id}                   désactiver (le journal garde son nom)
  POST   /profils/{id}/test              étiquette de test
  GET    /profils/{id}/etat              état d'une Zebra réseau (~HS)
  POST   /apercu.png                     aperçu raster interne d'un modèle
  POST   /imprimer                       modèle vectoriel + enregistrements
  POST   /rendu                          rendu existant (PDF ou image) d'un poste traça
  GET    /journal                        consultation filtrable
  GET    /journal/{id}                   détail (données, codes attendus)
  POST   /journal/{id}/reimprimer        même série, mêmes numéros, autre imprimante possible
  POST   /journal/{id}/resultat          issue d'un envoi fait par le navigateur
  POST   /journal/{id}/verification      lecture du code imprimé, comparée à l'attendu

Modes d'envoi : reseau (socket 9100 depuis le serveur), agent (file
print_jobs, agent local du réseau usine), navigateur (Zebra Browser Print sur
le poste : le serveur rend le flux, le navigateur l'envoie et rend compte),
fichier (flux à télécharger), pdf (repli universel). « auto » choisit agent si
le profil en a un, sinon réseau s'il a une adresse, sinon fichier.

Aucune donnée ne sort vers un service extérieur : l'aperçu est dessiné par
app/services/etiq_zpl.py.
"""

from __future__ import annotations

import base64
import binascii
import json
import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel

from config import (
    ETIQ_MODES_ENVOI,
    ETIQ_PORTS_RESEAU,
    ETIQ_RENDU_MAX_OCTETS,
    ETIQ_TIMEOUT_RESEAU_S,
    ROLES_MYPRINT,
)
from app.core.database import get_db
from app.services import etiq_zpl as ez
from app.services.audit_service import log_action
from app.services.auth_service import can_access_settings_printers, get_current_user, is_superadmin
from app.services.etiq_envoi import envoyer_reseau, etat_zpl
from app.services.etiq_zpl import ImpressionImpossible

router = APIRouter(tags=["print"], prefix="/api/tools/etiquettes/impression")

TABLE = "etiq_journal_impression"
MODELE_MAX_OCTETS = 4 * 1024 * 1024
DONNEES_MAX_OCTETS = 2 * 1024 * 1024
STATUTS = {
    "prepare": "Préparée", "envoye": "Envoyée", "en_file": "En file (agent)", "imprime": "Imprimée",
    "telecharge": "Fichier téléchargé", "pdf": "PDF ouvert", "erreur": "Erreur",
}
_HOTE_RE = re.compile(r"^[A-Za-z0-9.\-:\[\]]{1,253}$")
try:
    from config import ETIQ_GS1_PREFIXE as _PREFIXE_GS1
except ImportError:
    _PREFIXE_GS1 = ""
# Partition EPC (RFID) : longueur du préfixe entreprise GS1 de config.py.
_LONGUEUR_PREFIXE_GS1 = len(_PREFIXE_GS1) if 6 <= len(_PREFIXE_GS1 or "") <= 12 else 7


# ─── Accès ──────────────────────────────────────────────────────────────

def _user(request: Request) -> dict:
    user = get_current_user(request)
    if not (is_superadmin(user) or user.get("role") in ROLES_MYPRINT):
        raise HTTPException(status_code=403, detail="Accès réservé aux utilisateurs des étiquettes.")
    return user


def _admin(user: dict) -> bool:
    return is_superadmin(user) or bool(can_access_settings_printers(user))


def _exiger_admin(request: Request) -> dict:
    user = _user(request)
    if not _admin(user):
        raise HTTPException(status_code=403, detail="Profils d'imprimante : réservé aux administrateurs des imprimantes.")
    return user


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _colonnes(conn, table: str) -> set:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _exiger_journal(conn) -> None:
    if not _colonnes(conn, TABLE):
        raise HTTPException(status_code=503, detail="Journal d'impression indisponible : migration en attente.")


def _erreur(e: Exception):
    raise HTTPException(status_code=400, detail=str(e))


# ─── Profils (table imprimantes) ────────────────────────────────────────

_CHAMPS_PROFIL = ("decalage_x_mm", "decalage_y_mm", "vitesse", "contraste", "ecart_mm", "mode_envoi", "rfid")


def _profil(row, cols: set) -> dict:
    d = {
        "id": row["id"], "nom": row["nom"], "poste": row["poste"] or "", "langage": row["langage"] or "zpl",
        "dpi": row["dpi"], "largeur_mm": row["largeur_mm"], "hauteur_mm": row["hauteur_mm"],
        "ip": row["ip_locale"] or "", "port": row["port"], "agent_id": row["agent_id"],
        "actif": bool(row["actif"]), "note": row["note"] or "",
        "type_connexion": row["type_connexion"] if "type_connexion" in cols else "tcp_ip",
    }
    for c in _CHAMPS_PROFIL:
        d[c] = row[c] if c in cols else None
    d["decalage_x_mm"] = d["decalage_x_mm"] or 0
    d["decalage_y_mm"] = d["decalage_y_mm"] or 0
    d["ecart_mm"] = 2 if d["ecart_mm"] is None else d["ecart_mm"]
    d["mode_envoi"] = d["mode_envoi"] or "auto"
    d["rfid"] = bool(d["rfid"]) and d["langage"] == "zpl"
    d["gs1_longueur_prefixe"] = _LONGUEUR_PREFIXE_GS1
    d["modes"] = _modes_possibles(d)
    return d


def _modes_possibles(p: dict) -> list:
    modes = []
    if p.get("agent_id"):
        modes.append("agent")
    if p.get("ip") and p.get("type_connexion") != "windows_local" and int(p.get("port") or 0) in ETIQ_PORTS_RESEAU:
        modes.append("reseau")
    if p.get("langage") != "pdf":
        modes += ["navigateur", "fichier"]
    modes.append("pdf")
    return modes


def _lire_profil(conn, profil_id) -> dict:
    if not profil_id:
        raise HTTPException(status_code=400, detail="Choisir une imprimante.")
    row = conn.execute("SELECT * FROM imprimantes WHERE id=?", (int(profil_id),)).fetchone()
    if not row or not row["actif"]:
        raise HTTPException(status_code=404, detail="Imprimante introuvable ou désactivée.")
    return _profil(row, _colonnes(conn, "imprimantes"))


class ProfilPayload(BaseModel):
    nom: Optional[str] = None
    poste: Optional[str] = None
    langage: Optional[str] = None
    dpi: Optional[int] = None
    largeur_mm: Optional[float] = None
    hauteur_mm: Optional[float] = None
    ip: Optional[str] = None
    port: Optional[int] = None
    agent_id: Optional[int] = None
    decalage_x_mm: Optional[float] = None
    decalage_y_mm: Optional[float] = None
    vitesse: Optional[int] = None
    contraste: Optional[int] = None
    ecart_mm: Optional[float] = None
    mode_envoi: Optional[str] = None
    rfid: Optional[bool] = None
    note: Optional[str] = None
    actif: Optional[bool] = None


def _valeurs_profil(p: ProfilPayload, creation: bool) -> dict:
    v = {k: val for k, val in p.model_dump().items() if val is not None or k in ("vitesse", "contraste")}
    if not creation:
        v = {k: val for k, val in v.items() if k in p.model_fields_set}
    out = {}
    if "nom" in v:
        nom = (v["nom"] or "").strip()[:80]
        if not nom:
            raise HTTPException(status_code=400, detail="Nom de l'imprimante requis.")
        out["nom"] = nom
    if "poste" in v:
        out["poste"] = (v["poste"] or "").strip()[:80] or None
    if "langage" in v:
        if v["langage"] not in ez.LANGAGES:
            raise HTTPException(status_code=400, detail="Langage invalide — ZPL, EPL, TSPL ou PDF.")
        out["langage"] = v["langage"]
    if "dpi" in v:
        if int(v["dpi"]) not in ez.DPI_ADMIS:
            raise HTTPException(status_code=400, detail="Résolution invalide — 203, 300 ou 600 dpi.")
        out["dpi"] = int(v["dpi"])
    for k in ("largeur_mm", "hauteur_mm"):
        if k in v:
            f = float(v[k])
            if not 5 <= f <= ez.FORMAT_MAX_MM:
                raise HTTPException(status_code=400, detail=f"Format invalide — entre 5 et {ez.FORMAT_MAX_MM} mm.")
            out[k] = int(round(f))
    if "ip" in v:
        ip = (v["ip"] or "").strip()
        if ip and not _HOTE_RE.match(ip):
            raise HTTPException(status_code=400, detail="Adresse réseau invalide.")
        out["ip_locale"] = ip
    if "port" in v:
        port = int(v["port"])
        if not 1 <= port <= 65535:
            raise HTTPException(status_code=400, detail="Port invalide (1-65535).")
        out["port"] = port
    if "agent_id" in v:
        out["agent_id"] = v["agent_id"] or None
    for k, mini, maxi in (("decalage_x_mm", -50, 50), ("decalage_y_mm", -50, 50), ("ecart_mm", 0, 20)):
        if k in v:
            f = float(v[k])
            if not mini <= f <= maxi:
                raise HTTPException(status_code=400, detail=f"{k} hors bornes ({mini} à {maxi} mm).")
            out[k] = round(f, 2)
    if "vitesse" in v:
        out["vitesse"] = None if v["vitesse"] in (None, 0) else max(1, min(14, int(v["vitesse"])))
    if "contraste" in v:
        out["contraste"] = None if v["contraste"] is None else max(0, min(30, int(v["contraste"])))
    if "mode_envoi" in v:
        if v["mode_envoi"] not in ETIQ_MODES_ENVOI:
            raise HTTPException(status_code=400, detail="Mode d'envoi invalide.")
        out["mode_envoi"] = v["mode_envoi"]
    if "rfid" in v:
        out["rfid"] = 1 if v["rfid"] else 0
    if "note" in v:
        out["note"] = (v["note"] or "").strip()[:500] or None
    if "actif" in v:
        out["actif"] = 1 if v["actif"] else 0
    return out


@router.get("/config")
def config(request: Request):
    user = _user(request)
    return {"langages": list(ez.LANGAGES), "dpi": list(ez.DPI_ADMIS), "modes": ETIQ_MODES_ENVOI,
            "ports_reseau": list(ETIQ_PORTS_RESEAU), "statuts": STATUTS, "symbologies": list(ez.SYMBOLOGIES),
            "peut_administrer": _admin(user), "enregistrements_max": ez.ENREGISTREMENTS_MAX,
            "copies_max": ez.COPIES_MAX}


@router.get("/profils")
def lister_profils(request: Request, tous: int = 0):
    user = _user(request)
    with get_db() as conn:
        cols = _colonnes(conn, "imprimantes")
        q = "SELECT * FROM imprimantes"
        if not (tous and _admin(user)):
            q += " WHERE actif=1"
        rows = conn.execute(q + " ORDER BY actif DESC, COALESCE(poste,''), nom COLLATE NOCASE").fetchall()
        agents = {r["id"]: r["nom"] for r in conn.execute("SELECT id,nom FROM print_agents").fetchall()} \
            if _colonnes(conn, "print_agents") else {}
    out = []
    for r in rows:
        p = _profil(r, cols)
        p["agent_nom"] = agents.get(p["agent_id"]) or ""
        out.append(p)
    return {"profils": out, "agents": [{"id": k, "nom": v} for k, v in agents.items()],
            "peut_administrer": _admin(user)}


@router.post("/profils")
def creer_profil(payload: ProfilPayload, request: Request):
    user = _exiger_admin(request)
    v = _valeurs_profil(payload, creation=True)
    if "nom" not in v:
        raise HTTPException(status_code=400, detail="Nom de l'imprimante requis.")
    v.setdefault("ip_locale", "")
    v.setdefault("port", 9100)
    v.setdefault("langage", "zpl")
    v.setdefault("dpi", 203)
    v.setdefault("largeur_mm", 100)
    v.setdefault("hauteur_mm", 50)
    v["actif"] = 1
    v["created_at"] = _now()
    v["created_by"] = user.get("email")
    with get_db() as conn:
        cols = _colonnes(conn, "imprimantes")
        v = {k: val for k, val in v.items() if k in cols}
        cur = conn.execute(f"INSERT INTO imprimantes ({','.join(v)}) VALUES ({','.join('?' * len(v))})",
                           tuple(v.values()))
        pid = cur.lastrowid
        conn.commit()
        row = conn.execute("SELECT * FROM imprimantes WHERE id=?", (pid,)).fetchone()
        p = _profil(row, cols)
    log_action(user=user, action="CREATE", module="print", objet=f"Imprimante {p['nom']}",
               detail={k: p[k] for k in ("langage", "dpi", "ip", "port", "poste", "mode_envoi")}, request=request)
    return p


@router.patch("/profils/{profil_id}")
def modifier_profil(profil_id: int, payload: ProfilPayload, request: Request):
    user = _exiger_admin(request)
    v = _valeurs_profil(payload, creation=False)
    with get_db() as conn:
        cols = _colonnes(conn, "imprimantes")
        avant = conn.execute("SELECT * FROM imprimantes WHERE id=?", (profil_id,)).fetchone()
        if not avant:
            raise HTTPException(status_code=404, detail="Imprimante introuvable.")
        v = {k: val for k, val in v.items() if k in cols}
        if v:
            conn.execute(f"UPDATE imprimantes SET {','.join(k + '=?' for k in v)} WHERE id=?",
                         (*v.values(), profil_id))
            conn.commit()
        p = _profil(conn.execute("SELECT * FROM imprimantes WHERE id=?", (profil_id,)).fetchone(), cols)
    a = _profil(avant, cols)
    diff = {k: {"avant": a.get(k), "apres": p.get(k)} for k in p if k != "modes" and a.get(k) != p.get(k)}
    log_action(user=user, action="UPDATE", module="print", objet=f"Imprimante {p['nom']}", detail=diff,
               request=request)
    return p


@router.delete("/profils/{profil_id}")
def desactiver_profil(profil_id: int, request: Request):
    user = _exiger_admin(request)
    with get_db() as conn:
        row = conn.execute("SELECT nom FROM imprimantes WHERE id=?", (profil_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Imprimante introuvable.")
        conn.execute("UPDATE imprimantes SET actif=0 WHERE id=?", (profil_id,))
        conn.commit()
    log_action(user=user, action="DELETE", module="print", objet=f"Imprimante {row['nom']}",
               detail="désactivée (le journal garde son nom)", request=request)
    return {"ok": True}


def _modele_test(p: dict) -> dict:
    l, h = float(p["largeur_mm"] or 100), float(p["hauteur_mm"] or 50)
    return {"largeur_mm": l, "hauteur_mm": h, "layout": {"variables": [], "elements": [
        {"type": "cadre", "x": 1, "y": 1, "largeur": l - 2, "hauteur": h - 2, "epaisseur": 0.4},
        {"type": "texte", "x": 4, "y": 4, "valeur": f"Test {p['nom']}", "taille": min(6, h / 6), "gras": True},
        {"type": "texte", "x": 4, "y": 4 + min(8, h / 4), "valeur":
            f"{p['langage'].upper()} {p['dpi']} dpi {l:g}x{h:g} mm", "taille": min(4, h / 8)},
        {"type": "code_barre", "x": 4, "y": min(h - 14, 4 + min(16, h / 2.2)), "symbologie": "code128",
         "valeur": "TEST-" + str(p["id"]), "hauteur": min(10, h / 5)},
    ]}}


@router.post("/profils/{profil_id}/test")
def tester_profil(profil_id: int, request: Request):
    user = _user(request)
    with get_db() as conn:
        p = _lire_profil(conn, profil_id)
    modele = _modele_test(p)
    return _executer(user, request, p, None, modele=modele, enregistrements=[{}], valeurs=None, copies=1,
                     source="test", modele_id=None, modele_nom="Étiquette de test")


@router.get("/profils/{profil_id}/etat")
def etat_profil(profil_id: int, request: Request):
    _user(request)
    with get_db() as conn:
        p = _lire_profil(conn, profil_id)
    if "reseau" not in p["modes"]:
        raise HTTPException(status_code=409, detail="État lisible seulement pour une imprimante réseau directe.")
    if p["langage"] != "zpl":
        return {"repond": None, "lisible": False, "message": "Interrogation d'état réservée aux imprimantes ZPL."}
    try:
        return etat_zpl(p["ip"], int(p["port"]), timeout=min(3.0, ETIQ_TIMEOUT_RESEAU_S))
    except OSError as e:
        return {"repond": False, "lisible": False, "message": f"Injoignable — {e.strerror or type(e).__name__}."}


# ─── Préparation d'une impression ───────────────────────────────────────

def _charger_modele(conn, modele: dict) -> tuple:
    """(modèle à dessiner, id en base ou None, nom). Un modèle passé sans
    mise en page est relu en base (étiquettes spécifiques)."""
    if not isinstance(modele, dict):
        raise HTTPException(status_code=400, detail="Modèle manquant.")
    mid = modele.get("id")
    try:
        mid = int(mid) if mid not in (None, "") else None
    except (TypeError, ValueError):
        mid = None
    lay = ez.layout_de(modele)
    if mid and not lay["elements"] and _colonnes(conn, "etiq_modeles"):
        # Modèle passé par son seul id : la production imprime sa version
        # APPROUVÉE (etiq_validation_modeles), jamais un brouillon.
        from app.services.etiq_auto import modele_approuve
        try:
            modele = modele_approuve(conn, mid)
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))
    elif mid and _colonnes(conn, "etiq_modeles"):
        if not conn.execute("SELECT 1 FROM etiq_modeles WHERE id=?", (mid,)).fetchone():
            mid = None
    if len(json.dumps(modele, ensure_ascii=False)) > MODELE_MAX_OCTETS:
        raise HTTPException(status_code=413, detail="Modèle trop lourd (images) — 4 Mo au plus.")
    return modele, mid, str(modele.get("nom") or "")[:120]


def _valeurs(conn, modele: dict, modele_id, enregistrements: list, email: str) -> tuple:
    """Valeurs de chaque étiquette, calculées comme l'éditeur les calcule
    (etiq_specifiques : formules, dates, sources) ; compteurs et SSCC non
    fournis réservés en base quand le modèle y est enregistré. Rend
    (valeurs, visible)."""
    try:
        from app.services import etiq_specifiques as es
    except Exception:
        es = None
    if es is None:
        lay = ez.layout_de(modele)
        return [ez.valeurs_enregistrement(lay, r) for r in enregistrements], None
    try:
        layout = es.normaliser_layout(ez.layout_de(modele))
    except Exception as e:
        _erreur(e)
    fournis = set().union(*[{str(k).lower() for k in r} for r in enregistrements]) if enregistrements else set()
    series = [v for v in layout.get("variables", []) if v["type"] in ("compteur", "sscc") and v["nom"] not in fournis]
    n = len(enregistrements)
    plan = {}
    noms_series = {s["nom"] for s in series}
    if series and modele_id:
        # Sous verrou d'écriture : deux impressions simultanées du même SSCC
        # se sérialisent, la seconde relit le dernier numéro sorti.
        if conn.in_transaction:
            conn.commit()
        conn.execute("BEGIN IMMEDIATE")
        try:
            plan = {k: v for k, v in es.plan_serie(conn, modele_id, layout, n).items() if k in noms_series}
            es.reserver_serie(conn, plan, n, email)
            conn.commit()
        except Exception as e:
            conn.rollback()
            _erreur(e)
    elif series:
        try:
            plan = {k: v for k, v in es.plan_serie(None, 0, layout, n).items() if k in noms_series}
        except Exception as e:
            _erreur(e)
    maintenant = datetime.now()
    out = []
    try:
        for i, rec in enumerate(enregistrements):
            saisies = {str(k).lower(): ("" if v is None else str(v)[:500]) for k, v in rec.items()}
            vals = es.valeurs_etiquette(layout, plan, i, saisies, maintenant)
            for k, v in saisies.items():
                vals.setdefault(k, v)
                if k in {x["nom"] for x in layout.get("variables", []) if x["type"] in ("compteur", "sscc")}:
                    vals[k] = v
            out.append(vals)
    except Exception as e:
        _erreur(e)
    visible = getattr(es, "element_visible", None)
    return out, visible


def _resoudre_mode(p: dict, demande: Optional[str]) -> str:
    mode = demande if demande in ETIQ_MODES_ENVOI else (p.get("mode_envoi") or "auto")
    if mode == "auto":
        mode = "agent" if "agent" in p["modes"] else ("reseau" if "reseau" in p["modes"] else
                                                       ("fichier" if p["langage"] != "pdf" else "pdf"))
    if mode not in p["modes"]:
        raise HTTPException(status_code=409, detail=f"Mode « {ETIQ_MODES_ENVOI.get(mode, mode)} » indisponible "
                                                    f"pour l'imprimante {p['nom']}.")
    return mode


def _contenu(p: dict, mode: str, modele: Optional[dict], valeurs: Optional[list], visible, copies: int,
             images=None) -> tuple:
    """(octets, langage effectif). En mode pdf, le PDF au format de l'étiquette."""
    prof = dict(p)
    if mode == "pdf":
        prof["langage"] = "pdf"
    if images is not None:
        return ez.generer_depuis_images(images, prof, copies, seuil=int(prof.get("seuil") or 128),
                                        tramage=prof.get("tramage") or "seuil"), prof["langage"]
    return ez.generer(modele, [], prof, copies, valeurs=valeurs, visible=visible), prof["langage"]


def _sortie_agent(p: dict, langage: str) -> str:
    if langage != "pdf":
        return langage
    return "pdf" if p.get("type_connexion") == "windows_local" else "pdf_brut"


def _cles_systeme() -> set:
    """Variables fournies par MySifa à toute étiquette (préfixe GS1, licence
    FSC…) : utiles à l'impression, du bruit dans le résumé du journal."""
    try:
        from app.services.etiq_specifiques import valeurs_systeme
        return set(valeurs_systeme())
    except Exception:
        return set()


def _journaliser(conn, user: dict, p: dict, mode: str, langage: str, source: str, modele_id, modele_nom: str,
                 modele: Optional[dict], enregistrements: list, valeurs: list, attendus: list, copies: int,
                 contenu_source: Optional[bytes], reimpression_de=None, origine: Optional[str] = None) -> int:
    donnees = json.dumps({"enregistrements": enregistrements, "valeurs": valeurs}, ensure_ascii=False)
    if len(donnees) > DONNEES_MAX_OCTETS:
        donnees = json.dumps({"enregistrements": enregistrements[:200], "valeurs": valeurs[:200],
                              "tronque": True}, ensure_ascii=False)
    cur = conn.execute(
        f"INSERT INTO {TABLE} (created_at,created_by,created_by_nom,source,modele_id,modele_nom,imprimante_id,"
        "imprimante_nom,langage,mode_envoi,etiquettes,exemplaires,resume,donnees_json,modele_json,contenu,"
        "attendu_json,statut,reimpression_de) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'prepare',?)",
        (_now(), user.get("email"), user.get("nom") or "", source, modele_id, modele_nom, p["id"], p["nom"],
         langage, mode, max(1, len(valeurs or [None])), copies,
         ez.resume_donnees(valeurs if source != "rendu" else enregistrements, ignorer=_cles_systeme()),
         donnees, json.dumps(modele, ensure_ascii=False) if modele else None, contenu_source,
         json.dumps(attendus[:5000], ensure_ascii=False), reimpression_de))
    if origine and "origine" in _colonnes(conn, TABLE):
        conn.execute(f"UPDATE {TABLE} SET origine=? WHERE id=?", (origine[:300], cur.lastrowid))
    return cur.lastrowid


def _executer(user: dict, request: Request, p: dict, mode_demande: Optional[str], *, modele: Optional[dict],
              enregistrements: list, valeurs: Optional[list], copies: int, source: str, modele_id,
              modele_nom: str, visible=None, images=None, contenu_source: Optional[bytes] = None,
              attendus: Optional[list] = None, reimpression_de=None, origine: Optional[str] = None) -> dict:
    mode = _resoudre_mode(p, mode_demande)
    email = user.get("email")
    with get_db() as conn:
        _exiger_journal(conn)
        if modele is not None and valeurs is None:
            valeurs, visible = _valeurs(conn, modele, modele_id, enregistrements, email)
        try:
            contenu, langage = _contenu(p, mode, modele, valeurs, visible, copies, images)
            if attendus is None:
                attendus = ez.codes_attendus(modele, [], valeurs=valeurs, visible=visible) if modele else []
                if modele and p.get("rfid") and langage == "zpl":
                    prof = ez.normaliser_profil(p, modele)
                    for i, v in enumerate(valeurs or []):
                        epc = ez.epc_etiquette(modele, v, prof, visible)
                        if epc:
                            attendus.append({"index": i, "element": "RFID", "symbologie": "epc", "donnee": epc})
        except ImpressionImpossible as e:
            _erreur(e)
        jid = _journaliser(conn, user, p, mode, langage, source, modele_id, modele_nom, modele, enregistrements,
                           valeurs or [], attendus, copies, contenu_source, reimpression_de, origine)
        conn.commit()
        statut, erreur, job_id = "prepare", None, None
        if mode == "reseau":
            try:
                envoyer_reseau(p["ip"], int(p["port"]), contenu, timeout=ETIQ_TIMEOUT_RESEAU_S)
                statut = "envoye"
            except ImpressionImpossible as e:
                statut, erreur = "erreur", str(e)
        elif mode == "agent":
            cur = conn.execute(
                "INSERT INTO print_jobs (imprimante_id,agent_id,usage_key,template_id,payload,payload_langage,"
                "status,created_at,created_by,data_json) VALUES (?,?,?,NULL,?,?,'pending',?,?,?)",
                (p["id"], p["agent_id"], "etiquette_mytools", contenu, _sortie_agent(p, langage), _now(), email,
                 json.dumps({"journal_id": jid, "copies": 1, "duplex": "simplex", "format": "A4", "bin": None,
                             "color": "monochrome", "filename": f"etiquettes_{jid}.pdf"}, ensure_ascii=False)))
            job_id = cur.lastrowid
            statut = "en_file"
        elif mode == "fichier":
            statut = "telecharge"
        elif mode == "pdf":
            statut = "pdf"
        conn.execute(f"UPDATE {TABLE} SET statut=?, erreur=?, job_id=? WHERE id=?", (statut, erreur, job_id, jid))
        conn.commit()
    n = max(1, len(valeurs or [None]))
    log_action(user=user, action="PRINT", module="print",
               objet=f"{modele_nom or 'Étiquette'} · {n} × {copies} · {p['nom']}",
               detail={"journal_id": jid, "mode": mode, "langage": langage, "statut": statut, "erreur": erreur,
                       "source": source, "reimpression_de": reimpression_de}, request=request)
    rep = {"journal_id": jid, "statut": statut, "statut_libelle": STATUTS.get(statut, statut), "erreur": erreur,
           "mode": mode, "langage": langage, "imprimante": p["nom"], "etiquettes": n, "exemplaires": copies,
           "attendus": attendus[:50], "job_id": job_id}
    if mode in ("fichier", "navigateur", "pdf"):
        ext = ez.EXTENSIONS.get(langage, "prn")
        rep.update({"contenu_b64": base64.b64encode(contenu).decode("ascii"), "mime": ez.MIMES.get(langage),
                    "nom_fichier": f"etiquettes_{jid}.{ext}"})
    return rep


# ─── Aperçu ─────────────────────────────────────────────────────────────

class ApercuPayload(BaseModel):
    modele: dict
    enregistrement: dict = {}
    profil_id: Optional[int] = None
    dpi: Optional[int] = None


@router.post("/apercu.png")
def apercu(payload: ApercuPayload, request: Request):
    _user(request)
    with get_db() as conn:
        modele, mid, _ = _charger_modele(conn, payload.modele)
        prof = _lire_profil(conn, payload.profil_id) if payload.profil_id else {"dpi": payload.dpi or 203}
        try:
            from app.services import etiq_specifiques as es
            layout = es.normaliser_layout(ez.layout_de(modele))
            plan = es.plan_serie(conn if mid else None, mid or 0, layout, 1)
            vals = es.valeurs_etiquette(layout, plan, 0, {str(k).lower(): str(v) for k, v in
                                                         (payload.enregistrement or {}).items()})
            visible = getattr(es, "element_visible", None)
        except Exception:
            vals, visible = ez.valeurs_enregistrement(ez.layout_de(modele), payload.enregistrement), None
    try:
        png = ez.apercu_png(modele, vals, {"dpi": prof["dpi"]}, visible=visible)
    except ImpressionImpossible as e:
        _erreur(e)
    return Response(content=png, media_type="image/png", headers={"Cache-Control": "no-store"})


# ─── Impression d'un modèle ─────────────────────────────────────────────

class ImprimerPayload(BaseModel):
    modele: dict
    enregistrements: list = []
    quantite: int = 1          # exemplaires identiques de chaque étiquette
    serie: Optional[int] = None  # N étiquettes distinctes (compteurs) depuis un seul enregistrement
    profil_id: int
    mode: Optional[str] = None
    source: Optional[str] = None   # modele (défaut) | kiosque


def _enregistrements(liste, serie) -> list:
    recs = [r for r in (liste or []) if isinstance(r, dict)] or [{}]
    if serie:
        n = int(serie)
        if n < 1 or n > ez.ENREGISTREMENTS_MAX:
            raise HTTPException(status_code=400, detail=f"Série invalide — entre 1 et {ez.ENREGISTREMENTS_MAX}.")
        if len(recs) == 1:
            recs = [dict(recs[0]) for _ in range(n)]
    if len(recs) > ez.ENREGISTREMENTS_MAX:
        raise HTTPException(status_code=400, detail=f"Trop d'étiquettes — {ez.ENREGISTREMENTS_MAX} au plus.")
    return recs


def _copies(q) -> int:
    try:
        q = int(q)
    except (TypeError, ValueError):
        q = 0
    if q < 1 or q > ez.COPIES_MAX:
        raise HTTPException(status_code=400, detail=f"Quantité invalide — entre 1 et {ez.COPIES_MAX}.")
    return q


@router.post("/imprimer")
def imprimer(payload: ImprimerPayload, request: Request):
    user = _user(request)
    copies = _copies(payload.quantite)
    recs = _enregistrements(payload.enregistrements, payload.serie)
    with get_db() as conn:
        modele, mid, nom = _charger_modele(conn, payload.modele)
        p = _lire_profil(conn, payload.profil_id)
    return _executer(user, request, p, payload.mode, modele=modele, enregistrements=recs, valeurs=None,
                     copies=copies, source="kiosque" if payload.source == "kiosque" else "modele",
                     modele_id=mid, modele_nom=nom)


# ─── Impression d'un rendu (postes traça) ───────────────────────────────

class RenduPayload(BaseModel):
    nom: str = ""
    pdf_b64: Optional[str] = None
    image_b64: Optional[str] = None
    largeur_mm: Optional[float] = None
    hauteur_mm: Optional[float] = None
    donnees: dict = {}
    attendu: list = []        # [{"symbologie", "donnee"}] — codes que le rendu porte
    quantite: int = 1
    profil_id: int
    mode: Optional[str] = None
    seuil: int = 128
    tramage: str = "seuil"


def _decoder_b64(s: str) -> bytes:
    s = s.split(",", 1)[-1] if s.startswith("data:") else s
    try:
        brut = base64.b64decode(s, validate=False)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=400, detail="Rendu illisible (base64 attendu).")
    if len(brut) > ETIQ_RENDU_MAX_OCTETS:
        raise HTTPException(status_code=413, detail="Rendu trop lourd.")
    return brut


def _images_rendu(brut: bytes, est_pdf: bool, p: dict) -> list:
    try:
        if est_pdf:
            return ez.pdf_vers_images(brut, int(p["dpi"]))
        return [ez.decoder_image_rendu(base64.b64encode(brut).decode("ascii"))]
    except ImpressionImpossible as e:
        _erreur(e)


@router.post("/rendu")
def imprimer_rendu(payload: RenduPayload, request: Request):
    """Repli des postes traça sans modèle vectoriel : le PDF (ou l'image) que
    le poste produisait déjà est tramé au format et à la résolution du profil."""
    user = _user(request)
    copies = _copies(payload.quantite)
    if not payload.pdf_b64 and not payload.image_b64:
        raise HTTPException(status_code=400, detail="Rendu manquant (PDF ou image).")
    est_pdf = bool(payload.pdf_b64)
    brut = _decoder_b64(payload.pdf_b64 or payload.image_b64)
    with get_db() as conn:
        p = _lire_profil(conn, payload.profil_id)
    if payload.largeur_mm and payload.hauteur_mm:
        p = dict(p, largeur_mm=payload.largeur_mm, hauteur_mm=payload.hauteur_mm)
    images = _images_rendu(brut, est_pdf, p)
    attendus = [{"index": 0, "element": a.get("element") or a.get("symbologie") or "code",
                 "symbologie": a.get("symbologie") or "code128", "donnee": str(a.get("donnee") or "")[:500]}
                for a in (payload.attendu or [])[:50] if isinstance(a, dict) and a.get("donnee")]
    donnees = {str(k)[:40]: str(v)[:300] for k, v in list((payload.donnees or {}).items())[:40]}
    p_rendu = dict(p, seuil=max(1, min(254, payload.seuil)),
                   tramage="diffusion" if payload.tramage == "diffusion" else "seuil")
    return _executer(user, request, p_rendu, payload.mode, modele=None, enregistrements=[donnees],
                     valeurs=[donnees] * len(images), copies=copies, source="rendu", modele_id=None,
                     modele_nom=(payload.nom or "Rendu")[:120], images=images,
                     contenu_source=(b"PDF:" if est_pdf else b"IMG:") + brut, attendus=attendus)


# ─── Journal ────────────────────────────────────────────────────────────

def _ligne(r) -> dict:
    d = {k: r[k] for k in r.keys() if k not in ("donnees_json", "modele_json", "contenu", "attendu_json")}
    js = r["job_status"] if "job_status" in r.keys() else None
    if d.get("statut") == "en_file" and js == "done":
        d["statut"] = "imprime"
    elif d.get("statut") == "en_file" and js == "error":
        d["statut"] = "erreur"
        d["erreur"] = d.get("erreur") or r["job_erreur"]
    d["statut_libelle"] = STATUTS.get(d.get("statut"), d.get("statut"))
    d.pop("job_status", None)
    d.pop("job_erreur", None)
    return d


@router.get("/journal")
def journal(request: Request, du: Optional[str] = None, au: Optional[str] = None, imprimante: Optional[int] = None,
            modele: Optional[int] = None, utilisateur: Optional[str] = None, statut: Optional[str] = None,
            verif: Optional[str] = None, q: Optional[str] = None, source: Optional[str] = None,
            limite: int = 200, decalage: int = 0):
    _user(request)
    where, args = [], []
    date_re = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    if du and date_re.match(du):
        where.append("j.created_at >= ?"); args.append(du + "T00:00:00")
    if au and date_re.match(au):
        where.append("j.created_at <= ?"); args.append(au + "T23:59:59")
    if imprimante:
        where.append("j.imprimante_id = ?"); args.append(imprimante)
    if modele:
        where.append("j.modele_id = ?"); args.append(modele)
    if utilisateur:
        where.append("j.created_by = ?"); args.append(utilisateur[:120])
    if statut in STATUTS:
        if statut == "imprime":
            where.append("j.statut='en_file' AND pj.status='done'")
        elif statut == "erreur":
            where.append("(j.statut='erreur' OR (j.statut='en_file' AND pj.status='error'))")
        else:
            where.append("j.statut = ?"); args.append(statut)
    if source in ("modele", "rendu", "auto", "test", "kiosque"):
        where.append("j.source = ?"); args.append(source)
    if verif in ("ok", "ecart"):
        where.append("j.verif_statut = ?"); args.append(verif)
    elif verif == "aucune":
        where.append("j.verif_statut IS NULL")
    if q:
        like = "%" + q.strip()[:80] + "%"
        where.append("(j.modele_nom LIKE ? OR j.resume LIKE ? OR j.imprimante_nom LIKE ? OR j.created_by_nom LIKE ?)")
        args += [like] * 4
    limite = max(1, min(500, int(limite)))
    with get_db() as conn:
        _exiger_journal(conn)
        jointure = f"FROM {TABLE} j LEFT JOIN print_jobs pj ON pj.id=j.job_id"
        cj = _colonnes(conn, TABLE)
        extra = "".join(f"j.{c}," for c in ("verif_note", "origine") if c in cj)
        clause = (" WHERE " + " AND ".join(where)) if where else ""
        total = conn.execute(f"SELECT COUNT(*) {jointure}{clause}", args).fetchone()[0]
        rows = conn.execute(
            f"SELECT j.id,j.created_at,j.created_by,j.created_by_nom,j.source,j.modele_id,j.modele_nom,"
            f"j.imprimante_id,j.imprimante_nom,j.langage,j.mode_envoi,j.etiquettes,j.exemplaires,j.resume,"
            f"j.statut,j.erreur,j.job_id,j.reimpression_de,j.verif_statut,j.verif_lu,j.verif_at,j.verif_par,{extra}"
            f"pj.status AS job_status,pj.erreur AS job_erreur {jointure}{clause} "
            f"ORDER BY j.created_at DESC, j.id DESC LIMIT ? OFFSET ?", (*args, limite, max(0, int(decalage)))
        ).fetchall()
        utilisateurs = [dict(r) for r in conn.execute(
            f"SELECT created_by AS email, MAX(created_by_nom) AS nom FROM {TABLE} GROUP BY created_by "
            "ORDER BY nom COLLATE NOCASE").fetchall()]
    return {"lignes": [_ligne(r) for r in rows], "total": total, "utilisateurs": utilisateurs}


def _ligne_complete(conn, jid: int):
    _exiger_journal(conn)
    r = conn.execute(f"SELECT j.*, pj.status AS job_status, pj.erreur AS job_erreur FROM {TABLE} j "
                     "LEFT JOIN print_jobs pj ON pj.id=j.job_id WHERE j.id=?", (jid,)).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Impression introuvable dans le journal.")
    return r


@router.get("/journal/{jid}")
def journal_detail(jid: int, request: Request):
    _user(request)
    with get_db() as conn:
        r = _ligne_complete(conn, jid)
    d = _ligne(r)
    try:
        donnees = json.loads(r["donnees_json"] or "{}")
    except ValueError:
        donnees = {}
    ign = _cles_systeme()
    d["valeurs"] = [{k: v for k, v in (x or {}).items() if not str(k).startswith("_") and k not in ign}
                    for x in (donnees.get("valeurs") or [])[:100]]
    d["tronque"] = bool(donnees.get("tronque")) or len(donnees.get("valeurs") or []) > 100
    d["attendus"] = json.loads(r["attendu_json"] or "[]")[:200]
    d["reimprimable"] = bool(r["modele_json"] or r["contenu"])
    return d


class ReimprimerPayload(BaseModel):
    profil_id: Optional[int] = None
    mode: Optional[str] = None
    quantite: Optional[int] = None


@router.post("/journal/{jid}/reimprimer")
def reimprimer(jid: int, payload: ReimprimerPayload, request: Request):
    """Mêmes étiquettes, mêmes valeurs : aucun compteur ne bouge. Sur la même
    imprimante ou une autre (le flux est régénéré pour son langage)."""
    user = _user(request)
    with get_db() as conn:
        r = _ligne_complete(conn, jid)
        p = _lire_profil(conn, payload.profil_id or r["imprimante_id"])
    copies = _copies(payload.quantite or r["exemplaires"] or 1)
    donnees = json.loads(r["donnees_json"] or "{}")
    if donnees.get("tronque"):
        raise HTTPException(status_code=409, detail="Série trop longue pour être réimprimée depuis le journal.")
    attendus = json.loads(r["attendu_json"] or "[]")
    if r["modele_json"]:
        modele = json.loads(r["modele_json"])
        visible = None
        try:
            from app.services import etiq_specifiques as es
            visible = getattr(es, "element_visible", None)
        except Exception:
            pass
        return _executer(user, request, p, payload.mode, modele=modele,
                         enregistrements=donnees.get("enregistrements") or [{}], valeurs=donnees.get("valeurs") or [{}],
                         copies=copies, source=r["source"], modele_id=r["modele_id"], modele_nom=r["modele_nom"] or "",
                         visible=visible, attendus=attendus, reimpression_de=jid)
    brut = bytes(r["contenu"] or b"")
    if not brut:
        raise HTTPException(status_code=409, detail="Impression sans modèle ni rendu conservé : réimpression impossible.")
    est_pdf, brut = brut.startswith(b"PDF:"), brut[4:]
    images = _images_rendu(brut, est_pdf, p)
    recs = donnees.get("enregistrements") or [{}]
    return _executer(user, request, p, payload.mode, modele=None, enregistrements=recs, valeurs=recs * len(images),
                     copies=copies, source="rendu", modele_id=None, modele_nom=r["modele_nom"] or "",
                     images=images, contenu_source=bytes(r["contenu"]), attendus=attendus, reimpression_de=jid)


class ResultatPayload(BaseModel):
    statut: str
    erreur: Optional[str] = None


@router.post("/journal/{jid}/resultat")
def resultat(jid: int, payload: ResultatPayload, request: Request):
    """Issue d'un envoi fait par le navigateur (Zebra Browser Print)."""
    user = _user(request)
    if payload.statut not in ("envoye", "erreur"):
        raise HTTPException(status_code=400, detail="Statut invalide.")
    with get_db() as conn:
        r = _ligne_complete(conn, jid)
        if r["created_by"] != user.get("email") and not is_superadmin(user):
            raise HTTPException(status_code=403, detail="Seul l'auteur de l'impression en rend compte.")
        if r["statut"] not in ("prepare", "envoye", "erreur"):
            raise HTTPException(status_code=409, detail="Cette impression n'attend pas de compte rendu.")
        conn.execute(f"UPDATE {TABLE} SET statut=?, erreur=? WHERE id=?",
                     (payload.statut, (payload.erreur or "")[:500] or None, jid))
        conn.commit()
    log_action(user=user, action="UPDATE", module="print", objet=f"Impression n°{jid} · {r['imprimante_nom']}",
               detail={"statut": payload.statut, "erreur": payload.erreur}, request=request)
    return {"ok": True, "statut": payload.statut, "statut_libelle": STATUTS[payload.statut]}


class VerificationPayload(BaseModel):
    lu: str
    note: Optional[str] = None   # note ISO saisie ou lue par le vérificateur


@router.post("/journal/{jid}/verification")
def verification(jid: int, payload: VerificationPayload, request: Request):
    """Le code imprimé, scanné, est comparé aux codes attendus de l'impression."""
    user = _user(request)
    lu = (payload.lu or "").strip()[:500]
    if not lu:
        raise HTTPException(status_code=400, detail="Lecture vide.")
    with get_db() as conn:
        r = _ligne_complete(conn, jid)
        attendus = json.loads(r["attendu_json"] or "[]")
        if not attendus:
            raise HTTPException(status_code=409, detail="Aucun code-barres attendu sur cette impression.")
        donnee, note = ez.lecture_verificateur(lu)
        note = ez.note_iso(payload.note) or note
        res = ez.verifier_lecture(donnee, attendus)
        if note:
            res["note"] = note
            # Une note D ou F rend le code non conforme même s'il se lit.
            if note in ("D", "F") and res["statut"] == "ok":
                res["statut"] = "ecart"
                res["motif"] = f"Note ISO {note} : impression à reprendre (contraste, vitesse, tête)."
        conn.execute(f"UPDATE {TABLE} SET verif_statut=?, verif_lu=?, verif_detail=?, verif_at=?, verif_par=? "
                     "WHERE id=?", (res["statut"], res["lu"][:500], json.dumps(res, ensure_ascii=False), _now(),
                                    user.get("email"), jid))
        if note and "verif_note" in _colonnes(conn, TABLE):
            conn.execute(f"UPDATE {TABLE} SET verif_note=? WHERE id=?", (note, jid))
        conn.commit()
    log_action(user=user, action="VALIDATE", module="print",
               objet=f"Vérification impression n°{jid} · {r['modele_nom'] or ''}".strip(),
               detail={"resultat": res["statut"], "element": res.get("element"), "note": res.get("note")},
               request=request)
    return res

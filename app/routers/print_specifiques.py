"""
MyPrint — étiquettes spécifiques (API).

Préfixe /api/print/specifiques : le journal d'audit range ces écritures sous
le module MyPrint sans entrée supplémentaire dans la taxonomie.

  GET    /bootstrap                     dossiers, étiquettes, référentiels
  POST   /dossiers                      crée un dossier
  PATCH  /dossiers/{id}                 renomme
  DELETE /dossiers/{id}                 archive (refusé s'il reste des étiquettes)
  GET    /modeles/{id}                  étiquette complète
  POST   /modeles                       crée
  PATCH  /modeles/{id}                  enregistre
  POST   /modeles/{id}/dupliquer        copie (même dossier ou autre)
  DELETE /modeles/{id}                  archive
  POST   /apercu                        ZPL + valeurs d'exemple (sans rien consommer)
  POST   /apercu.png                    rendu exact du ZPL (labelary)
  POST   /modeles/{id}/plan             plages qu'une impression prendrait
  POST   /modeles/{id}/imprimer         série → un job MyPrint
  GET    /modeles/{id}/impressions      historique
  POST   /impressions/{id}/reimprimer   même ZPL, mêmes numéros
  POST   /ia/proposer                   assistant : consigne → mise en page
  POST   /ia/depuis-photo               photo(s) + explication → nouvelle étiquette
  GET    /modeles/{id}/sources/{fichier} photo source d'une étiquette créée par l'IA
  POST   /demandes                      demande de nouveau format (+ pièces)
  GET    /demandes                      toutes (super admin) ou les miennes
  GET    /demandes/{id}
  PATCH  /demandes/{id}                 statut, réponse (super admin)
  POST   /demandes/{id}/generer         premier jet par l'IA (super admin)
  GET    /pieces/{id}                   téléchargement d'une pièce jointe

Sources de données, séries, versions, compteurs et contrôle IA :
app/routers/etiq_avance.py (même préfixe).
"""

from __future__ import annotations

import json
import os
import re
import secrets
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from config import (
    ETIQ_GS1_PREFIXE, ETIQ_IA_MODELE, ETIQ_PHOTO_IMAGE_MAX_OCTETS, ETIQ_PHOTO_MAX_FICHIERS, ETIQ_PIECE_MAX_OCTETS,
    ETIQ_ROLES_CONCEPTION, ETIQ_UPLOAD_DIR, ETIQ_USAGES, FSC_LICENCE_SIFA, ROLES_MYPRINT, etiq_ia_modeles,
    etiq_usages, public_base_url,
)
from app.core.database import get_db
from app.services.auth_service import get_current_user, is_superadmin
from app.services import etiq_specifiques as es
from app.services.etiq_specifiques import EtiquetteInvalide

router = APIRouter(tags=["print"], prefix="/api/print/specifiques")

STATUTS_DEMANDE = {
    "nouvelle": "Nouvelle",
    "en_cours": "En cours",
    "livree": "Livrée",
    "refusee": "Refusée",
}
_MIME_PIECES = {
    "application/pdf", "image/png", "image/jpeg", "image/gif", "image/webp",
    "text/plain", "text/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
# Ce que l'assistant lit réellement (etiq_specifiques_ia._blocs_pieces) : une
# création depuis photo n'accepte que ces formats. HEIC n'est pas lu par
# l'API ; le navigateur le convertit en JPEG avant l'envoi.
_MIME_PHOTO = {"application/pdf", "image/png", "image/jpeg", "image/gif", "image/webp"}
# Photos sources conservées à côté des pièces des demandes, sans table :
# source_<id étiquette>_<aléa>.<ext>. Le nom porte l'étiquette, le motif
# ci-dessous est le seul accepté au téléchargement.
_SOURCES_DIR = os.path.join(ETIQ_UPLOAD_DIR, "sources")
_SOURCE_RE = re.compile(r"^source_(\d+)_[0-9a-f]{16}\.(jpg|png|gif|webp|pdf)$")
_EXT_MIME = {"jpg": "image/jpeg", "png": "image/png", "gif": "image/gif", "webp": "image/webp",
             "pdf": "application/pdf"}
_MIME_EXT = {v: k for k, v in _EXT_MIME.items()}


# ─── Helpers ────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _user(request: Request) -> dict:
    user = get_current_user(request)
    if not (is_superadmin(user) or user.get("role") in ROLES_MYPRINT):
        raise HTTPException(status_code=403, detail="Accès réservé aux utilisateurs MyPrint.")
    return user


def _super(request: Request) -> dict:
    user = _user(request)
    if not is_superadmin(user):
        raise HTTPException(status_code=403, detail="Réservé au super admin.")
    return user


def concepteur(user: dict) -> bool:
    """Peut modifier les objets figés et les calques verrouillés."""
    return is_superadmin(user) or user.get("role") in ETIQ_ROLES_CONCEPTION


def _usage(v) -> Optional[str]:
    if v is None:
        return None
    v = str(v).strip().lower()
    return v if v in dict(ETIQ_USAGES) else ""


def _invalide(e: EtiquetteInvalide):
    raise HTTPException(status_code=400, detail=str(e))


def _serialize_modele(row, complet: bool = False) -> dict:
    d = {
        "id": row["id"], "dossier_id": row["dossier_id"], "nom": row["nom"],
        "description": row["description"] or "",
        "largeur_mm": row["largeur_mm"], "hauteur_mm": row["hauteur_mm"], "dpi": row["dpi"],
        "duplique_de": row["duplique_de"], "demande_id": row["demande_id"],
        "usage": row["usage"] if "usage" in row.keys() else "",
        "client": row["client"] if "client" in row.keys() else "",
        "version": row["version"] if "version" in row.keys() else 1,
        **_etat_validation(row),
        "created_at": row["created_at"], "created_by": row["created_by"],
        "updated_at": row["updated_at"], "updated_by": row["updated_by"],
    }
    if complet:
        try:
            d["layout"] = es.normaliser_layout(row["layout_json"])
        except EtiquetteInvalide:
            d["layout"] = {"elements": [], "variables": []}
        d["avertissements"] = es.controles(d["layout"])
        d["sources"] = _sources(row["id"])
    return d


def _etat_validation(row) -> dict:
    from app.services.etiq_validation import etat
    return etat(row)


def _sources(modele_id: int) -> list[dict]:
    """Photos d'origine d'une étiquette créée depuis une photo."""
    try:
        noms = sorted(os.listdir(_SOURCES_DIR))
    except OSError:
        return []
    out = []
    for n in noms:
        m = _SOURCE_RE.match(n)
        if m and int(m.group(1)) == int(modele_id):
            out.append({"fichier": n, "mime": _EXT_MIME[m.group(2)],
                        "url": f"{router.prefix}/modeles/{modele_id}/sources/{n}"})
    return out


def _modele(conn, modele_id: int):
    row = conn.execute("SELECT * FROM etiq_modeles WHERE id=? AND archive=0", (modele_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Étiquette introuvable.")
    return row


def _production(conn, modele_id: int) -> dict:
    """Format et mise en page de la version APPROUVÉE (etiq_validation.py) :
    ce que l'atelier imprime, quel que soit le brouillon en cours."""
    _modele(conn, modele_id)
    from app.services.etiq_validation import modele_production
    try:
        return modele_production(conn, modele_id)
    except EtiquetteInvalide as e:
        raise HTTPException(status_code=409, detail=str(e))


def _dossier_actif(conn, dossier_id) -> None:
    if not conn.execute("SELECT 1 FROM etiq_dossiers WHERE id=? AND archive=0", (dossier_id,)).fetchone():
        raise HTTPException(status_code=404, detail="Dossier introuvable.")


def _imprimante(conn, imprimante_id):
    """Toute imprimante active. Le format de sortie suit son langage :
    ZPL pour les Zebra, PDF pour les autres (voir `_sortie`)."""
    if not imprimante_id:
        raise HTTPException(status_code=400, detail="Choisir une imprimante.")
    cols = {r[1] for r in conn.execute("PRAGMA table_info(imprimantes)").fetchall()}
    tc = "type_connexion" if "type_connexion" in cols else "'tcp_ip' AS type_connexion"
    imp = conn.execute(
        f"SELECT id,nom,agent_id,langage,actif,dpi,{tc} FROM imprimantes WHERE id=?", (int(imprimante_id),)
    ).fetchone()
    if not imp or not imp["actif"]:
        raise HTTPException(status_code=404, detail="Imprimante introuvable ou désactivée.")
    return imp


def _sortie(imp) -> str:
    """zpl | pdf (file Windows, SumatraPDF) | pdf_brut (PDF envoyé tel quel
    sur le port 9100 : les laser de bureau Brother, Lexmark, OKI, HP le lisent
    directement — l'agent l'envoie comme n'importe quel flux brut)."""
    if (imp["langage"] or "zpl") == "zpl":
        return "zpl"
    return "pdf" if (imp["type_connexion"] or "tcp_ip") == "windows_local" else "pdf_brut"


def _creer_job(conn, imp, payload: bytes, sortie: str, email: str, data: dict) -> int:
    if sortie == "pdf":
        # Options lues par l'agent et passées à SumatraPDF (comme /api/print/pdf).
        data = dict(data, copies=1, duplex="simplex", format="A4", bin=None, color="monochrome",
                    filename=f"etiquettes_{data.get('impression_id', '')}.pdf")
    cur = conn.execute(
        "INSERT INTO print_jobs (imprimante_id,agent_id,usage_key,template_id,payload,payload_langage,"
        "status,created_at,created_by,data_json) VALUES (?,?,?,NULL,?,?,'pending',?,?,?)",
        (imp["id"], imp["agent_id"], "etiquette_specifique", payload, sortie,
         _now(), email, json.dumps(data, ensure_ascii=False)),
    )
    return cur.lastrowid


def _payload(sortie: str, zpl: str, layout: dict, largeur_mm, hauteur_mm, valeurs: list, exemplaires: int) -> bytes:
    if sortie == "zpl":
        return zpl.encode("utf-8")
    from app.services.etiq_specifiques_pdf import rendre_pdf
    return rendre_pdf(layout, largeur_mm, hauteur_mm, valeurs, exemplaires)


# ─── Bootstrap ──────────────────────────────────────────────────────────

@router.get("/bootstrap")
def bootstrap(request: Request):
    user = _user(request)
    sup = is_superadmin(user)
    with get_db() as conn:
        dossiers = [dict(r) for r in conn.execute(
            "SELECT d.id,d.nom,d.description,d.created_at,"
            " (SELECT COUNT(*) FROM etiq_modeles m WHERE m.dossier_id=d.id AND m.archive=0) AS nb"
            " FROM etiq_dossiers d WHERE d.archive=0 ORDER BY d.nom COLLATE NOCASE").fetchall()]
        modeles = [_serialize_modele(r) for r in conn.execute(
            "SELECT * FROM etiq_modeles WHERE archive=0 ORDER BY nom COLLATE NOCASE").fetchall()]
        if sup:
            nb_dem = conn.execute(
                "SELECT COUNT(*) FROM etiq_demandes WHERE statut IN ('nouvelle','en_cours')").fetchone()[0]
        else:
            nb_dem = conn.execute(
                "SELECT COUNT(*) FROM etiq_demandes WHERE created_by=? AND statut IN ('nouvelle','en_cours')",
                (user.get("email"),)).fetchone()[0]
    return {
        "dossiers": dossiers, "modeles": modeles,
        "is_super": sup, "demandes_ouvertes": nb_dem,
        "referentiel": {
            "symbologies": es.SYMBOLOGIES, "types_variable": es.TYPES_VARIABLE,
            "dpi": list(es.DPI_ADMIS), "statuts_demande": STATUTS_DEMANDE,
            "quantite_max": es.QUANTITE_MAX,
            "modeles_ia": etiq_ia_modeles(),
            "usages": etiq_usages(),
            "pictos": _pictos_ref(),
            "sources": _sources_ref(),
            "formats_date": [{"format": f, "libelle": l} for f, l in _formats_date()],
            "fonctions": sorted(_fonctions()),
            "calques_defaut": [dict(c) for c in es.CALQUES_DEFAUT],
            "gs1": {"prefixe": ETIQ_GS1_PREFIXE, "ai": _ai_ref()},
            "fsc_licence": FSC_LICENCE_SIFA,
            "base_url": public_base_url(),
            "concepteur": concepteur(user),
            "approbateur": _approbateur(user),
            "statuts_validation": {"brouillon": "Brouillon", "a_approuver": "À approuver", "approuve": "Approuvée"},
            "modele_ia_defaut": ETIQ_IA_MODELE if any(m["id"] == ETIQ_IA_MODELE for m in etiq_ia_modeles())
            else etiq_ia_modeles()[0]["id"],
        },
    }


def _approbateur(user: dict) -> bool:
    from app.routers.qualite import ROLES_QUALITE
    return is_superadmin(user) or user.get("role") in ROLES_QUALITE


def _pictos_ref():
    from app.services.etiq_pictos import referentiel
    return referentiel()


def _sources_ref():
    from app.services.etiq_sources import referentiel
    return referentiel()


def _formats_date():
    from app.services.etiq_formules import FORMATS_DATE
    return FORMATS_DATE


def _fonctions():
    from app.services.etiq_formules import FONCTIONS
    return FONCTIONS.keys()


def _ai_ref():
    from app.services.etiq_gs1 import AI
    return {k: {"libelle": v[0], "fixe": v[1], "max": v[2], "type": v[3]} for k, v in AI.items()}


# ─── Dossiers ───────────────────────────────────────────────────────────

class DossierPayload(BaseModel):
    nom: str
    description: Optional[str] = ""


@router.post("/dossiers")
def create_dossier(payload: DossierPayload, request: Request):
    user = _user(request)
    nom = (payload.nom or "").strip()[:80]
    if not nom:
        raise HTTPException(status_code=400, detail="Nom du dossier obligatoire.")
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO etiq_dossiers (nom,description,created_at,created_by) VALUES (?,?,?,?)",
            (nom, (payload.description or "")[:500], _now(), user.get("email")))
        conn.commit()
        return {"ok": True, "id": cur.lastrowid}


@router.patch("/dossiers/{dossier_id}")
def patch_dossier(dossier_id: int, payload: DossierPayload, request: Request):
    _user(request)
    nom = (payload.nom or "").strip()[:80]
    if not nom:
        raise HTTPException(status_code=400, detail="Nom du dossier obligatoire.")
    with get_db() as conn:
        _dossier_actif(conn, dossier_id)
        conn.execute("UPDATE etiq_dossiers SET nom=?, description=? WHERE id=?",
                     (nom, (payload.description or "")[:500], dossier_id))
        conn.commit()
    return {"ok": True}


@router.delete("/dossiers/{dossier_id}")
def delete_dossier(dossier_id: int, request: Request):
    _user(request)
    with get_db() as conn:
        _dossier_actif(conn, dossier_id)
        n = conn.execute("SELECT COUNT(*) FROM etiq_modeles WHERE dossier_id=? AND archive=0",
                         (dossier_id,)).fetchone()[0]
        if n:
            raise HTTPException(status_code=409,
                                detail=f"Le dossier contient encore {n} étiquette(s) — les déplacer ou les archiver d'abord.")
        conn.execute("UPDATE etiq_dossiers SET archive=1 WHERE id=?", (dossier_id,))
        conn.commit()
    return {"ok": True}


# ─── Modèles ────────────────────────────────────────────────────────────

class ModelePayload(BaseModel):
    dossier_id: Optional[int] = None
    nom: Optional[str] = None
    description: Optional[str] = None
    largeur_mm: Optional[float] = None
    hauteur_mm: Optional[float] = None
    dpi: Optional[int] = None
    layout: Optional[dict] = None
    usage: Optional[str] = None
    client: Optional[str] = None
    motif: Optional[str] = None


@router.get("/modeles/{modele_id}")
def get_modele(modele_id: int, request: Request):
    _user(request)
    with get_db() as conn:
        return _serialize_modele(_modele(conn, modele_id), complet=True)


@router.post("/modeles")
def create_modele(payload: ModelePayload, request: Request):
    user = _user(request)
    nom = (payload.nom or "").strip()[:120]
    if not nom:
        raise HTTPException(status_code=400, detail="Nom de l'étiquette obligatoire.")
    l, h, d = es.normaliser_format(payload.largeur_mm, payload.hauteur_mm, payload.dpi)
    try:
        layout = es.normaliser_layout(payload.layout or {})
    except EtiquetteInvalide as e:
        _invalide(e)
    with get_db() as conn:
        _dossier_actif(conn, payload.dossier_id)
        now = _now()
        cur = conn.execute(
            "INSERT INTO etiq_modeles (dossier_id,nom,description,largeur_mm,hauteur_mm,dpi,layout_json,"
            "usage,client,created_at,created_by,updated_at,updated_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (payload.dossier_id, nom, (payload.description or "")[:1000], l, h, d,
             json.dumps(layout, ensure_ascii=False), _usage(payload.usage) or "", (payload.client or "").strip()[:120],
             now, user.get("email"), now, user.get("email")))
        conn.commit()
        return {"ok": True, "id": cur.lastrowid}


@router.patch("/modeles/{modele_id}")
def patch_modele(modele_id: int, payload: ModelePayload, request: Request):
    user = _user(request)
    with get_db() as conn:
        row = _modele(conn, modele_id)
        champs = {}
        if payload.nom is not None:
            nom = payload.nom.strip()[:120]
            if not nom:
                raise HTTPException(status_code=400, detail="Nom de l'étiquette obligatoire.")
            champs["nom"] = nom
        if payload.description is not None:
            champs["description"] = payload.description[:1000]
        if payload.usage is not None:
            champs["usage"] = _usage(payload.usage) or ""
        if payload.client is not None:
            champs["client"] = payload.client.strip()[:120]
        if payload.dossier_id is not None and payload.dossier_id != row["dossier_id"]:
            _dossier_actif(conn, payload.dossier_id)
            champs["dossier_id"] = payload.dossier_id
        if any(v is not None for v in (payload.largeur_mm, payload.hauteur_mm, payload.dpi)):
            l, h, d = es.normaliser_format(
                payload.largeur_mm if payload.largeur_mm is not None else row["largeur_mm"],
                payload.hauteur_mm if payload.hauteur_mm is not None else row["hauteur_mm"],
                payload.dpi if payload.dpi is not None else row["dpi"])
            champs.update({"largeur_mm": l, "hauteur_mm": h, "dpi": d})
        if payload.layout is not None:
            try:
                nouveau = es.normaliser_layout(payload.layout)
                if not concepteur(user):
                    from app.services.etiq_bibliotheque import violations_verrous
                    ko = violations_verrous(es.normaliser_layout(row["layout_json"]), nouveau)
                    if ko:
                        raise HTTPException(status_code=403, detail=" ".join(ko[:3]))
                champs["layout_json"] = json.dumps(nouveau, ensure_ascii=False)
            except EtiquetteInvalide as e:
                _invalide(e)
            if champs["layout_json"] == row["layout_json"]:
                champs.pop("layout_json")
        if not champs:
            return _serialize_modele(row, complet=True)
        # Nouvelle version dès que le dessin change (mise en page ou format) :
        # l'état précédent est rangé, on peut y revenir.
        if any(k in champs and champs[k] != row[k] for k in ("layout_json", "largeur_mm", "hauteur_mm", "dpi")):
            from app.services.etiq_bibliotheque import enregistrer_version
            champs["version"] = enregistrer_version(conn, row, user.get("email"), payload.motif or "")
            # Modifiée : la production garde la version approuvée jusqu'à la
            # prochaine approbation.
            champs["statut_validation"] = "brouillon"
        champs["updated_at"] = _now()
        champs["updated_by"] = user.get("email")
        sets = ", ".join(f"{k}=?" for k in champs)
        conn.execute(f"UPDATE etiq_modeles SET {sets} WHERE id=?", (*champs.values(), modele_id))
        conn.commit()
        return _serialize_modele(_modele(conn, modele_id), complet=True)


class DupliquerPayload(BaseModel):
    dossier_id: Optional[int] = None
    nom: Optional[str] = None
    client: Optional[str] = None


@router.post("/modeles/{modele_id}/dupliquer")
def dupliquer_modele(modele_id: int, payload: DupliquerPayload, request: Request):
    user = _user(request)
    with get_db() as conn:
        row = _modele(conn, modele_id)
        dossier_id = payload.dossier_id or row["dossier_id"]
        _dossier_actif(conn, dossier_id)
        nom = (payload.nom or "").strip()[:120] or f"{row['nom']} (copie)"
        now = _now()
        cur = conn.execute(
            "INSERT INTO etiq_modeles (dossier_id,nom,description,largeur_mm,hauteur_mm,dpi,layout_json,"
            "usage,client,duplique_de,created_at,created_by,updated_at,updated_by)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (dossier_id, nom, row["description"], row["largeur_mm"], row["hauteur_mm"], row["dpi"],
             row["layout_json"], row["usage"] if "usage" in row.keys() else "",
             (payload.client if payload.client is not None else (row["client"] if "client" in row.keys() else ""))[:120],
             modele_id, now, user.get("email"), now, user.get("email")))
        conn.commit()
        return {"ok": True, "id": cur.lastrowid}


@router.delete("/modeles/{modele_id}")
def archive_modele(modele_id: int, request: Request):
    user = _user(request)
    with get_db() as conn:
        _modele(conn, modele_id)
        conn.execute("UPDATE etiq_modeles SET archive=1, updated_at=?, updated_by=? WHERE id=?",
                     (_now(), user.get("email"), modele_id))
        conn.commit()
    return {"ok": True}


# ─── Aperçu ─────────────────────────────────────────────────────────────

class ApercuPayload(BaseModel):
    modele_id: Optional[int] = None
    largeur_mm: float = 100
    hauteur_mm: float = 150
    dpi: int = 203
    layout: dict = {}
    saisies: dict = {}


def _apercu(payload: ApercuPayload) -> dict:
    l, h, d = es.normaliser_format(payload.largeur_mm, payload.hauteur_mm, payload.dpi)
    try:
        layout = es.normaliser_layout(payload.layout)
        with get_db() as conn:
            plan = es.plan_serie(conn, payload.modele_id or 0, layout, 1)
        vals = es.valeurs_etiquette(layout, plan, 0, payload.saisies or {})
    except EtiquetteInvalide as e:
        _invalide(e)
    return {"zpl": es.rendre_zpl(layout, l, h, d, vals), "valeurs": vals,
            "avertissements": es.controles(layout), "format": [l, h, d]}


@router.post("/apercu")
def apercu(payload: ApercuPayload, request: Request):
    _user(request)
    return _apercu(payload)


@router.post("/apercu.png")
def apercu_png(payload: ApercuPayload, request: Request):
    _user(request)
    from app.routers.print import _labelary_render_zpl
    r = _apercu(payload)
    l, h, d = r["format"]
    png = _labelary_render_zpl(r["zpl"], d, int(round(l)), int(round(h)))
    return Response(content=png, media_type="image/png")


# ─── Impression ─────────────────────────────────────────────────────────

class PlanPayload(BaseModel):
    quantite: int = 1
    departs: dict = {}
    saisies: dict = {}


def _quantite(q) -> int:
    try:
        q = int(q)
    except (TypeError, ValueError):
        q = 0
    if q < 1 or q > es.QUANTITE_MAX:
        raise HTTPException(status_code=400, detail=f"Quantité invalide — entre 1 et {es.QUANTITE_MAX}.")
    return q


@router.post("/modeles/{modele_id}/plan")
def plan(modele_id: int, payload: PlanPayload, request: Request):
    """Ce que l'impression émettrait : première et dernière valeur de chaque série."""
    _user(request)
    q = _quantite(payload.quantite)
    with get_db() as conn:
        row = _production(conn, modele_id)
        try:
            layout = es.normaliser_layout(row["layout_json"])
            p = es.plan_serie(conn, modele_id, layout, q, payload.departs)
            premiere = es.valeurs_etiquette(layout, p, 0, payload.saisies or {})
            derniere = es.valeurs_etiquette(layout, p, q - 1, payload.saisies or {})
        except EtiquetteInvalide as e:
            _invalide(e)
    return {"plages": {nom: {"premier": premiere[nom], "dernier": derniere[nom], "numero": v["premier"]}
                       for nom, v in p.items()}}


class ImprimerPayload(BaseModel):
    imprimante_id: int
    quantite: int = 1
    exemplaires: int = 1
    saisies: dict = {}
    departs: dict = {}


@router.post("/modeles/{modele_id}/imprimer")
def imprimer(modele_id: int, payload: ImprimerPayload, request: Request):
    user = _user(request)
    email = user.get("email")
    q = _quantite(payload.quantite)
    ex = max(1, min(99, int(payload.exemplaires or 1)))
    saisies = {k: str(v)[:500] for k, v in (payload.saisies or {}).items()}
    with get_db() as conn:
        row = _production(conn, modele_id)   # version approuvée, jamais le brouillon
        imp = _imprimante(conn, payload.imprimante_id)
        sortie = _sortie(imp)
        # 1. Sous verrou d'écriture : lecture des compteurs, réservation, trace.
        # Deux impressions simultanées du même SSCC liraient sinon le même
        # « dernier ». La seconde attend la fin de la première puis relit.
        if conn.in_transaction:
            conn.commit()
        conn.execute("BEGIN IMMEDIATE")
        try:
            layout = es.normaliser_layout(row["layout_json"])
            es.controler_saisies(layout, saisies)
            p = es.plan_serie(conn, modele_id, layout, q, payload.departs)
            es.reserver_serie(conn, p, q, email)
            zpl, valeurs = es.rendre_serie(layout, row["largeur_mm"], row["hauteur_mm"], row["dpi"],
                                           p, q, saisies, ex)
        except EtiquetteInvalide as e:
            conn.rollback()
            _invalide(e)
        plages = {nom: {"premier": valeurs[0][nom], "dernier": valeurs[-1][nom]} for nom in p}
        cur = conn.execute(
            "INSERT INTO etiq_impressions (modele_id,imprimante_id,quantite,exemplaires,valeurs_json,plages_json,"
            "layout_json,zpl,valeurs_serie_json,format_sortie,created_at,created_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (modele_id, imp["id"], q, ex, json.dumps(saisies, ensure_ascii=False),
             json.dumps(plages, ensure_ascii=False), row["layout_json"], zpl,
             json.dumps(valeurs, ensure_ascii=False), sortie, _now(), email))
        impression_id = cur.lastrowid
        conn.commit()
        # 2. Hors verrou : le rendu PDF d'une grande série prend du temps, il
        # ne doit pas bloquer les autres écritures. S'il échoue, les numéros
        # sont réservés et tracés : la réimpression depuis l'historique les
        # ressort à l'identique.
        try:
            corps = _payload(sortie, zpl, layout, row["largeur_mm"], row["hauteur_mm"], valeurs, ex)
        except Exception as e:
            raise HTTPException(status_code=500, detail=(
                f"Numéros réservés mais rendu en échec ({type(e).__name__}). "
                "Relancer depuis l'historique (Réimprimer)."))
        job_id = _creer_job(conn, imp, corps, sortie, email, {"modele_id": modele_id, "impression_id": impression_id})
        conn.execute("UPDATE etiq_impressions SET job_id=? WHERE id=?", (job_id, impression_id))
        conn.commit()
    return {"ok": True, "impression_id": impression_id, "job_id": job_id, "sortie": sortie,
            "imprimante": imp["nom"], "quantite": q, "plages": plages}


@router.get("/modeles/{modele_id}/impressions")
def impressions(modele_id: int, request: Request):
    _user(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT i.id,i.quantite,i.exemplaires,i.plages_json,i.valeurs_json,i.created_at,i.created_by,"
            " i.reimpression_de,i.imprimante_id,p.nom AS imprimante,j.status AS job_status,j.erreur AS job_erreur"
            " FROM etiq_impressions i LEFT JOIN imprimantes p ON p.id=i.imprimante_id"
            " LEFT JOIN print_jobs j ON j.id=i.job_id"
            " WHERE i.modele_id=? ORDER BY i.created_at DESC, i.id DESC LIMIT 200", (modele_id,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["plages"] = json.loads(d.pop("plages_json") or "{}")
        d["valeurs"] = json.loads(d.pop("valeurs_json") or "{}")
        out.append(d)
    return out


class ReimprimerPayload(BaseModel):
    imprimante_id: Optional[int] = None


@router.post("/impressions/{impression_id}/reimprimer")
def reimprimer(impression_id: int, payload: ReimprimerPayload, request: Request):
    """Mêmes étiquettes, mêmes numéros, aucun compteur ne bouge — sur la même
    imprimante ou une autre, en ZPL ou en PDF selon celle-ci."""
    user = _user(request)
    with get_db() as conn:
        src = conn.execute("SELECT * FROM etiq_impressions WHERE id=?", (impression_id,)).fetchone()
        if not src:
            raise HTTPException(status_code=404, detail="Impression introuvable.")
        imp = _imprimante(conn, payload.imprimante_id or src["imprimante_id"])
        sortie = _sortie(imp)
        brut = src["valeurs_serie_json"] if "valeurs_serie_json" in src.keys() else None
        valeurs = json.loads(brut) if brut else None
        if sortie != "zpl" and not valeurs:
            raise HTTPException(status_code=409, detail=(
                "Impression antérieure au PDF : réimprimable seulement sur une imprimante ZPL."))
        largeur = hauteur = 0
        if sortie != "zpl":
            m = conn.execute("SELECT largeur_mm,hauteur_mm FROM etiq_modeles WHERE id=?",
                             (src["modele_id"],)).fetchone()
            largeur, hauteur = m["largeur_mm"], m["hauteur_mm"]
        try:
            layout = es.normaliser_layout(src["layout_json"])
        except EtiquetteInvalide as e:
            _invalide(e)
        corps = _payload(sortie, src["zpl"], layout, largeur, hauteur, valeurs or [], src["exemplaires"])
        cur = conn.execute(
            "INSERT INTO etiq_impressions (modele_id,imprimante_id,quantite,exemplaires,valeurs_json,plages_json,"
            "layout_json,zpl,valeurs_serie_json,format_sortie,reimpression_de,created_at,created_by)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (src["modele_id"], imp["id"], src["quantite"], src["exemplaires"], src["valeurs_json"],
             src["plages_json"], src["layout_json"], src["zpl"], brut, sortie, impression_id,
             _now(), user.get("email")))
        nid = cur.lastrowid
        job_id = _creer_job(conn, imp, corps, sortie, user.get("email"),
                            {"modele_id": src["modele_id"], "impression_id": nid, "reimpression_de": impression_id})
        conn.execute("UPDATE etiq_impressions SET job_id=? WHERE id=?", (job_id, nid))
        conn.commit()
    return {"ok": True, "impression_id": nid, "job_id": job_id, "imprimante": imp["nom"], "sortie": sortie}


# ─── Assistant IA ───────────────────────────────────────────────────────

class IaPayload(BaseModel):
    consigne: str
    largeur_mm: float = 100
    hauteur_mm: float = 150
    dpi: int = 203
    layout: dict = {}
    modele: Optional[str] = None


@router.post("/ia/proposer")
def ia_proposer(payload: IaPayload, request: Request):
    user = _user(request)
    if not (payload.consigne or "").strip():
        raise HTTPException(status_code=400, detail="Décrire la modification souhaitée.")
    from app.services import ia_usage
    from app.services.etiq_specifiques_ia import proposer
    l, h, d = es.normaliser_format(payload.largeur_mm, payload.hauteur_mm, payload.dpi)
    try:
        layout = es.normaliser_layout(payload.layout)
        with ia_usage.suivi(user, "etiquettes", "print"):
            return proposer(payload.consigne[:4000], l, h, d, layout, modele=payload.modele)
    except EtiquetteInvalide as e:
        _invalide(e)


@router.post("/ia/depuis-photo")
async def ia_depuis_photo(
    request: Request,
    consigne: str = Form(""),
    nom: str = Form(""),
    dossier_id: Optional[int] = Form(None),
    largeur_mm: Optional[float] = Form(None),
    hauteur_mm: Optional[float] = Form(None),
    dpi: int = Form(203),
    modele: Optional[str] = Form(None),
    usage: str = Form(""),
    client: str = Form(""),
    fichiers: list[UploadFile] = File(default=[]),
):
    """Accès direct (tout utilisateur MyPrint) : photo(s) ou PDF d'une
    étiquette existante + explication → nouvelle étiquette dans le dossier,
    prête à relire dans l'éditeur. Les fichiers sont conservés comme source."""
    user = _user(request)
    from app.services import ia_usage
    from app.services.etiq_specifiques_ia import choisir_modele, contexte_photo, proposer
    try:
        choisir_modele(modele)  # refus immédiat, avant de lire les fichiers
    except EtiquetteInvalide as e:
        _invalide(e)
    consigne = (consigne or "").strip()
    nom = (nom or "").strip()[:120]
    if not consigne:
        raise HTTPException(status_code=400, detail="Expliquer l'étiquette : ce qui change d'une impression à l'autre, les codes attendus.")
    if len(consigne) > 4000:
        raise HTTPException(status_code=400, detail="Explication trop longue — 4 000 caractères au plus.")
    if not nom:
        raise HTTPException(status_code=400, detail="Nom de l'étiquette obligatoire.")
    if not dossier_id:
        raise HTTPException(status_code=400, detail="Choisir le dossier où créer l'étiquette.")
    if (largeur_mm is None) != (hauteur_mm is None) or any(v is not None and v <= 0 for v in (largeur_mm, hauteur_mm)):
        raise HTTPException(status_code=400, detail="Format incomplet — donner largeur et hauteur, ou aucune des deux.")
    with get_db() as conn:
        _dossier_actif(conn, dossier_id)

    fichiers = [f for f in (fichiers or []) if f and f.filename]
    if not fichiers:
        raise HTTPException(status_code=400, detail="Joindre au moins une photo ou un PDF de l'étiquette.")
    if len(fichiers) > ETIQ_PHOTO_MAX_FICHIERS:
        raise HTTPException(status_code=400, detail=f"{ETIQ_PHOTO_MAX_FICHIERS} fichiers au plus.")
    pieces = []
    for f in fichiers:
        mime = (f.content_type or "").lower()
        if mime == "image/jpg":
            mime = "image/jpeg"
        if mime not in _MIME_PHOTO:
            raise HTTPException(status_code=400,
                                detail=f"« {f.filename} » : format non accepté — photo JPEG, PNG, WebP ou PDF.")
        contenu = await f.read()
        if not contenu:
            raise HTTPException(status_code=400, detail=f"« {f.filename} » est vide.")
        if len(contenu) > ETIQ_PIECE_MAX_OCTETS:
            raise HTTPException(status_code=400,
                                detail=f"« {f.filename} » dépasse {ETIQ_PIECE_MAX_OCTETS // (1024 * 1024)} Mo.")
        if mime.startswith("image/") and len(contenu) > ETIQ_PHOTO_IMAGE_MAX_OCTETS:
            raise HTTPException(status_code=400, detail=(
                f"« {f.filename} » dépasse {ETIQ_PHOTO_IMAGE_MAX_OCTETS // (1024 * 1024)} Mo — "
                "réduire la photo avant de l'envoyer."))
        pieces.append({"mime": mime, "contenu": contenu, "nom": f.filename[:200]})

    libre = largeur_mm is None
    l, h, d = es.normaliser_format(largeur_mm or 100, hauteur_mm or 150, dpi)
    contexte = contexte_photo(None if libre else l, None if libre else h) + f"\nNom de l'étiquette : {nom}"
    try:
        with ia_usage.suivi(user, "etiquettes", "photo"):
            res = proposer(consigne, l, h, d, {"elements": [], "variables": []}, pieces, contexte,
                           modele=modele, format_libre=libre)
    except EtiquetteInvalide as e:
        _invalide(e)
    if not libre:
        # Format imposé : la réponse ne le change pas.
        res["largeur_mm"], res["hauteur_mm"] = l, h

    description = res["resume"] + f" (créée depuis une photo : {res['modele_libelle']})"
    if res["remarques"]:
        description += "\nÀ vérifier : " + " · ".join(res["remarques"])
    os.makedirs(_SOURCES_DIR, exist_ok=True)
    ecrits = []
    now = _now()
    try:
        with get_db() as conn:
            _dossier_actif(conn, dossier_id)
            cur = conn.execute(
                "INSERT INTO etiq_modeles (dossier_id,nom,description,largeur_mm,hauteur_mm,dpi,layout_json,"
                "usage,client,created_at,created_by,updated_at,updated_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (dossier_id, nom, description[:1000], res["largeur_mm"], res["hauteur_mm"], d,
                 json.dumps(res["layout"], ensure_ascii=False), _usage(usage) or "", (client or "").strip()[:120],
                 now, user.get("email"), now, user.get("email")))
            mid = cur.lastrowid
            for p in pieces:
                chemin = os.path.join(_SOURCES_DIR, f"source_{mid}_{secrets.token_hex(8)}.{_MIME_EXT[p['mime']]}")
                with open(chemin, "wb") as fh:
                    fh.write(p["contenu"])
                ecrits.append(chemin)
            conn.commit()
    except Exception:
        for c in ecrits:
            try:
                os.remove(c)
            except OSError:
                pass
        raise
    return {"ok": True, "modele_id": mid, "resume": res["resume"], "remarques": res["remarques"],
            "champs_detectes": res.get("champs_detectes", []),
            "modele_libelle": res["modele_libelle"], "largeur_mm": res["largeur_mm"],
            "hauteur_mm": res["hauteur_mm"]}


@router.get("/modeles/{modele_id}/sources/{fichier}")
def get_source(modele_id: int, fichier: str, request: Request):
    _user(request)
    m = _SOURCE_RE.match(fichier or "")
    if not m or int(m.group(1)) != modele_id:
        raise HTTPException(status_code=404, detail="Fichier introuvable.")
    with get_db() as conn:
        _modele(conn, modele_id)
    chemin = os.path.join(_SOURCES_DIR, fichier)
    if not os.path.exists(chemin):
        raise HTTPException(status_code=404, detail="Fichier absent du serveur.")
    return FileResponse(chemin, media_type=_EXT_MIME[m.group(2)], filename=fichier,
                        content_disposition_type="inline")


# ─── Demandes de nouveau format ─────────────────────────────────────────

def _serialize_demande(conn, r) -> dict:
    d = dict(r)
    d["statut_label"] = STATUTS_DEMANDE.get(d["statut"], d["statut"])
    d["pieces"] = [dict(p) for p in conn.execute(
        "SELECT id,original_name,mime_type,taille FROM etiq_demande_pieces WHERE demande_id=? ORDER BY id",
        (d["id"],)).fetchall()]
    if d.get("dossier_id"):
        x = conn.execute("SELECT nom FROM etiq_dossiers WHERE id=?", (d["dossier_id"],)).fetchone()
        d["dossier_nom"] = x["nom"] if x else ""
    return d


def _demande_visible(conn, demande_id: int, user: dict):
    r = conn.execute("SELECT * FROM etiq_demandes WHERE id=?", (demande_id,)).fetchone()
    if not r or (not is_superadmin(user) and r["created_by"] != user.get("email")):
        raise HTTPException(status_code=404, detail="Demande introuvable.")
    return r


@router.post("/demandes")
async def create_demande(
    request: Request,
    titre: str = Form(...),
    description: str = Form(...),
    client: str = Form(""),
    dossier_id: Optional[int] = Form(None),
    largeur_mm: Optional[float] = Form(None),
    hauteur_mm: Optional[float] = Form(None),
    fichiers: list[UploadFile] = File(default=[]),
):
    user = _user(request)
    titre, description = (titre or "").strip()[:150], (description or "").strip()[:5000]
    if not titre or not description:
        raise HTTPException(status_code=400, detail="Titre et description obligatoires.")
    lus = []
    for f in fichiers or []:
        if not f or not f.filename:
            continue
        contenu = await f.read()
        mime = (f.content_type or "").lower()
        if mime not in _MIME_PIECES:
            raise HTTPException(status_code=400,
                                detail=f"« {f.filename} » : format non accepté (PDF, image, Excel, Word, texte).")
        if len(contenu) > ETIQ_PIECE_MAX_OCTETS:
            raise HTTPException(status_code=400,
                                detail=f"« {f.filename} » dépasse {ETIQ_PIECE_MAX_OCTETS // (1024 * 1024)} Mo.")
        lus.append((f.filename[:200], mime, contenu))
    os.makedirs(ETIQ_UPLOAD_DIR, exist_ok=True)
    with get_db() as conn:
        if dossier_id:
            _dossier_actif(conn, dossier_id)
        now = _now()
        cur = conn.execute(
            "INSERT INTO etiq_demandes (dossier_id,client,titre,description,largeur_mm,hauteur_mm,statut,"
            "created_at,created_by) VALUES (?,?,?,?,?,?,'nouvelle',?,?)",
            (dossier_id or None, (client or "").strip()[:120], titre, description,
             largeur_mm, hauteur_mm, now, user.get("email")))
        did = cur.lastrowid
        for nom, mime, contenu in lus:
            ext = os.path.splitext(nom)[1].lower()[:10]
            disque = f"{did}_{secrets.token_hex(8)}{ext}"
            with open(os.path.join(ETIQ_UPLOAD_DIR, disque), "wb") as fh:
                fh.write(contenu)
            conn.execute(
                "INSERT INTO etiq_demande_pieces (demande_id,filename,original_name,mime_type,taille,created_at)"
                " VALUES (?,?,?,?,?,?)", (did, disque, nom, mime, len(contenu), now))
        conn.commit()
    return {"ok": True, "id": did}


@router.get("/demandes")
def list_demandes(request: Request):
    user = _user(request)
    with get_db() as conn:
        if is_superadmin(user):
            rows = conn.execute("SELECT * FROM etiq_demandes ORDER BY "
                                "CASE statut WHEN 'nouvelle' THEN 0 WHEN 'en_cours' THEN 1 ELSE 2 END,"
                                " created_at DESC LIMIT 300").fetchall()
        else:
            rows = conn.execute("SELECT * FROM etiq_demandes WHERE created_by=? ORDER BY created_at DESC LIMIT 300",
                                (user.get("email"),)).fetchall()
        return [_serialize_demande(conn, r) for r in rows]


@router.get("/demandes/{demande_id}")
def get_demande(demande_id: int, request: Request):
    user = _user(request)
    with get_db() as conn:
        return _serialize_demande(conn, _demande_visible(conn, demande_id, user))


class DemandePatch(BaseModel):
    statut: Optional[str] = None
    reponse: Optional[str] = None
    modele_id: Optional[int] = None


@router.patch("/demandes/{demande_id}")
def patch_demande(demande_id: int, payload: DemandePatch, request: Request):
    user = _super(request)
    with get_db() as conn:
        _demande_visible(conn, demande_id, user)
        champs = {}
        if payload.statut is not None:
            if payload.statut not in STATUTS_DEMANDE:
                raise HTTPException(status_code=400, detail="Statut inconnu.")
            champs["statut"] = payload.statut
        if payload.reponse is not None:
            champs["reponse"] = payload.reponse[:3000]
        if payload.modele_id is not None:
            _modele(conn, payload.modele_id)
            champs["modele_id"] = payload.modele_id
        if champs:
            champs["traite_at"], champs["traite_par"] = _now(), user.get("email")
            sets = ", ".join(f"{k}=?" for k in champs)
            conn.execute(f"UPDATE etiq_demandes SET {sets} WHERE id=?", (*champs.values(), demande_id))
            conn.commit()
        return _serialize_demande(conn, _demande_visible(conn, demande_id, user))


class GenererPayload(BaseModel):
    dossier_id: Optional[int] = None
    consigne: Optional[str] = ""
    modele: Optional[str] = None


@router.post("/demandes/{demande_id}/generer")
def generer_depuis_demande(demande_id: int, payload: GenererPayload, request: Request):
    """Premier jet par l'IA : crée une étiquette dans le dossier, la rattache
    à la demande et passe la demande en cours. Le super admin la relit dans
    l'éditeur avant de la livrer."""
    user = _super(request)
    from app.services.etiq_specifiques_ia import choisir_modele, proposer
    try:
        choisir_modele(payload.modele)  # refus immédiat, avant de lire les pièces
    except EtiquetteInvalide as e:
        _invalide(e)
    with get_db() as conn:
        dem = _demande_visible(conn, demande_id, user)
        dossier_id = payload.dossier_id or dem["dossier_id"]
        if not dossier_id:
            raise HTTPException(status_code=400, detail="Choisir le dossier où créer l'étiquette.")
        _dossier_actif(conn, dossier_id)
        pieces = []
        for p in conn.execute("SELECT * FROM etiq_demande_pieces WHERE demande_id=? ORDER BY id",
                              (demande_id,)).fetchall():
            chemin = os.path.join(ETIQ_UPLOAD_DIR, p["filename"])
            if os.path.exists(chemin):
                with open(chemin, "rb") as fh:
                    pieces.append({"mime": p["mime_type"], "contenu": fh.read(), "nom": p["original_name"]})
    l, h, d = es.normaliser_format(dem["largeur_mm"] or 100, dem["hauteur_mm"] or 150, 203)
    contexte = (f"Demande de nouveau format.\nClient : {dem['client'] or '—'}\nTitre : {dem['titre']}\n"
                f"Description : {dem['description']}")
    consigne = (payload.consigne or "").strip() or "Construis cette étiquette à partir de la demande et des pièces jointes."
    from app.services import ia_usage
    try:
        with ia_usage.suivi(user, "etiquettes", "demande"):
            res = proposer(consigne[:4000], l, h, d, {"elements": [], "variables": []}, pieces, contexte,
                           modele=payload.modele)
    except EtiquetteInvalide as e:
        _invalide(e)
    now = _now()
    description = res["resume"] + f" (brouillon : {res['modele_libelle']})"
    if res["remarques"]:
        description += "\nÀ vérifier : " + " · ".join(res["remarques"])
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO etiq_modeles (dossier_id,nom,description,largeur_mm,hauteur_mm,dpi,layout_json,demande_id,"
            "created_at,created_by,updated_at,updated_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (dossier_id, dem["titre"][:120], description[:1000], res["largeur_mm"], res["hauteur_mm"], d,
             json.dumps(res["layout"], ensure_ascii=False), demande_id, now, user.get("email"), now, user.get("email")))
        mid = cur.lastrowid
        conn.execute("UPDATE etiq_demandes SET modele_id=?, statut=CASE WHEN statut='nouvelle' THEN 'en_cours' ELSE statut END,"
                     " dossier_id=?, traite_at=?, traite_par=? WHERE id=?",
                     (mid, dossier_id, now, user.get("email"), demande_id))
        conn.commit()
    return {"ok": True, "modele_id": mid, "resume": res["resume"], "remarques": res["remarques"],
            "champs_detectes": res.get("champs_detectes", []),
            "modele_libelle": res["modele_libelle"]}


@router.get("/pieces/{piece_id}")
def get_piece(piece_id: int, request: Request):
    user = _user(request)
    with get_db() as conn:
        p = conn.execute("SELECT * FROM etiq_demande_pieces WHERE id=?", (piece_id,)).fetchone()
        if not p:
            raise HTTPException(status_code=404, detail="Pièce introuvable.")
        _demande_visible(conn, p["demande_id"], user)
    chemin = os.path.join(ETIQ_UPLOAD_DIR, p["filename"])
    if not os.path.exists(chemin):
        raise HTTPException(status_code=404, detail="Fichier absent du serveur.")
    inline = (p["mime_type"] or "").startswith("image/") or p["mime_type"] == "application/pdf"
    return FileResponse(chemin, media_type=p["mime_type"] or "application/octet-stream",
                        filename=p["original_name"],
                        content_disposition_type="inline" if inline else "attachment")

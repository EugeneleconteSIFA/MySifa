"""
MySifa — module impression cloud (v1.5.0).

Architecture :

  Téléphone opérateur (5G)  →  MySifa VPS  →  POST /api/print/label
                                   ↓
                              print_jobs (SQLite)
                                   ↓
   Agent local (Raspberry Pi sur le LAN usine) → GET /api/print/agent/jobs
                                   ↓
                         socket TCP 9100 → Imprimante Zebra/Brother

Endpoints admin (superadmin uniquement) :
  GET    /api/print/agents                — liste des agents locaux
  POST   /api/print/agents                — crée un agent, renvoie le token en clair (1 seule fois)
  PATCH  /api/print/agents/{id}           — renomme / active
  DELETE /api/print/agents/{id}           — supprime un agent
  GET    /api/print/imprimantes           — liste toutes les imprimantes
  POST   /api/print/imprimantes           — crée une imprimante (+ seed template par défaut)
  PATCH  /api/print/imprimantes/{id}      — édition
  DELETE /api/print/imprimantes/{id}      — suppression
  GET    /api/print/templates             — liste tous les templates
  POST   /api/print/templates             — crée un template
  PATCH  /api/print/templates/{id}        — édition (contenu ZPL/EPL)
  DELETE /api/print/templates/{id}        — suppression
  POST   /api/print/test                  — impression de test sur une imprimante

Endpoints utilisateur (tous rôles connectés) :
  GET    /api/print/usages                — liste des usages métier disponibles
  GET    /api/print/my-imprimantes        — liste des imprimantes accessibles (toutes actives)
  GET    /api/print/my-defaults           — mes imprimantes par défaut par usage
  PUT    /api/print/my-defaults           — met à jour mes défauts
  POST   /api/print/label                 — émet un job d'impression

Endpoints agent (auth par X-Agent-Token) :
  POST   /api/print/agent/heartbeat       — ping l'agent (met à jour last_heartbeat)
  GET    /api/print/agent/jobs            — récupère jusqu'à N jobs pending
  POST   /api/print/agent/jobs/{id}/ack   — accuse réception (succès ou erreur)
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional

from pathlib import Path
import urllib.error
import urllib.request

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.services.auth_service import get_current_user, require_superadmin
from app.services.print_render import (
    LANGAGES,
    USAGES,
    default_templates_seed,
    get_default_template,
    list_default_templates,
    render_template,
    usage_label,
)

router = APIRouter(tags=["print"], prefix="/api/print")


# ─── Helpers ──────────────────────────────────────────────────────────

def _now() -> str:
    # v1.5.1 — timestamp UTC ISO avec Z. Sans TZ, le browser interprete la string
    # comme "heure locale" et affiche l'agent "Hors ligne (120min)" en ete francais
    # alors qu'il vient tout juste d'envoyer un heartbeat depuis un VPS en UTC.
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _agent_from_token(request: Request) -> dict:
    """Auth d'un agent local via header X-Agent-Token."""
    token = request.headers.get("X-Agent-Token", "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="X-Agent-Token manquant.")
    h = _hash_token(token)
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, nom, actif FROM print_agents WHERE token_hash=? LIMIT 1",
            (h,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Token invalide.")
    if not row["actif"]:
        raise HTTPException(status_code=403, detail="Agent désactivé.")
    return {"id": row["id"], "nom": row["nom"]}


def _serialize_agent(row) -> dict:
    return {
        "id": row["id"],
        "nom": row["nom"],
        "actif": bool(row["actif"]),
        "last_heartbeat": row["last_heartbeat"],
        "last_ip": row["last_ip"],
        "created_at": row["created_at"],
        "note": row["note"],
    }


def _serialize_imprimante(row) -> dict:
    # v1.6 — `type_connexion` peut valoir 'tcp_ip' (defaut) ou 'windows_local'.
    # Pour 'windows_local', `ip_locale`/`port` ne sont pas utilises et
    # `nom_queue_windows` designe la queue installee sur le PC hote (cote agent).
    try:
        type_connexion = row["type_connexion"] or "tcp_ip"
    except (IndexError, KeyError):
        type_connexion = "tcp_ip"
    try:
        nom_queue_windows = row["nom_queue_windows"]
    except (IndexError, KeyError):
        nom_queue_windows = None
    return {
        "id": row["id"],
        "nom": row["nom"],
        "poste": row["poste"],
        "agent_id": row["agent_id"],
        "type_connexion": type_connexion,
        "ip_locale": row["ip_locale"],
        "port": row["port"],
        "nom_queue_windows": nom_queue_windows,
        "langage": row["langage"],
        "largeur_mm": row["largeur_mm"],
        "hauteur_mm": row["hauteur_mm"],
        "dpi": row["dpi"],
        "actif": bool(row["actif"]),
        "note": row["note"],
    }


def _serialize_template(row) -> dict:
    return {
        "id": row["id"],
        "imprimante_id": row["imprimante_id"],
        "usage_key": row["usage_key"],
        "usage_label": usage_label(row["usage_key"]),
        "nom": row["nom"],
        "contenu": row["contenu"],
        "actif": bool(row["actif"]),
        "updated_at": row["updated_at"],
        "updated_by": row["updated_by"],
    }


# ═══════════════════════════════════════════════════════════════════════
# ENDPOINTS ADMIN — Agents locaux
# ═══════════════════════════════════════════════════════════════════════

class AgentCreate(BaseModel):
    nom: str = Field(min_length=1, max_length=80)
    note: Optional[str] = None


class AgentPatch(BaseModel):
    nom: Optional[str] = None
    actif: Optional[bool] = None
    note: Optional[str] = None


@router.get("/agents")
def list_agents(request: Request):
    require_superadmin(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id,nom,actif,last_heartbeat,last_ip,created_at,note FROM print_agents ORDER BY nom"
        ).fetchall()
    return [_serialize_agent(r) for r in rows]


@router.post("/agents")
def create_agent(payload: AgentCreate, request: Request):
    require_superadmin(request)
    token = secrets.token_urlsafe(32)
    h = _hash_token(token)
    now = _now()
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO print_agents (nom,token_hash,actif,created_at,note) VALUES (?,?,1,?,?)",
            (payload.nom.strip(), h, now, (payload.note or "").strip() or None),
        )
        conn.commit()
        aid = cur.lastrowid
    return {"id": aid, "nom": payload.nom, "token": token, "note": (
        "Copie ce token dans le fichier de config de l'agent local. "
        "Il ne sera plus affiché ensuite."
    )}


@router.patch("/agents/{agent_id}")
def patch_agent(agent_id: int, payload: AgentPatch, request: Request):
    require_superadmin(request)
    fields, values = [], []
    if payload.nom is not None:
        fields.append("nom=?"); values.append(payload.nom.strip())
    if payload.actif is not None:
        fields.append("actif=?"); values.append(1 if payload.actif else 0)
    if payload.note is not None:
        fields.append("note=?"); values.append(payload.note.strip() or None)
    if not fields:
        raise HTTPException(status_code=400, detail="Aucun champ à modifier.")
    values.append(agent_id)
    with get_db() as conn:
        cur = conn.execute(f"UPDATE print_agents SET {','.join(fields)} WHERE id=?", values)
        conn.commit()
        if not cur.rowcount:
            raise HTTPException(status_code=404, detail="Agent introuvable.")
    return {"ok": True}


@router.delete("/agents/{agent_id}")
def delete_agent(agent_id: int, request: Request):
    require_superadmin(request)
    with get_db() as conn:
        cur = conn.execute("DELETE FROM print_agents WHERE id=?", (agent_id,))
        conn.commit()
        if not cur.rowcount:
            raise HTTPException(status_code=404, detail="Agent introuvable.")
    return {"ok": True}


# ═══════════════════════════════════════════════════════════════════════
# ENDPOINTS ADMIN — Imprimantes
# ═══════════════════════════════════════════════════════════════════════

TYPES_CONNEXION = ("tcp_ip", "windows_local")


class ImprimanteBase(BaseModel):
    nom: str = Field(min_length=1, max_length=80)
    poste: Optional[str] = None
    agent_id: Optional[int] = None
    # v1.6 — `type_connexion` determine si on cible IP:port ou une queue Windows.
    type_connexion: str = "tcp_ip"
    ip_locale: Optional[str] = None            # requis si type_connexion='tcp_ip'
    port: Optional[int] = 9100
    nom_queue_windows: Optional[str] = None    # requis si type_connexion='windows_local'
    langage: str = "zpl"
    largeur_mm: int = 102
    hauteur_mm: int = 152
    dpi: int = 203
    note: Optional[str] = None


class ImprimantePatch(BaseModel):
    nom: Optional[str] = None
    poste: Optional[str] = None
    agent_id: Optional[int] = None
    type_connexion: Optional[str] = None
    ip_locale: Optional[str] = None
    port: Optional[int] = None
    nom_queue_windows: Optional[str] = None
    langage: Optional[str] = None
    largeur_mm: Optional[int] = None
    hauteur_mm: Optional[int] = None
    dpi: Optional[int] = None
    actif: Optional[bool] = None
    note: Optional[str] = None


def _validate_imprimante(payload) -> None:
    if payload.langage and payload.langage not in LANGAGES:
        raise HTTPException(status_code=400, detail=f"Langage invalide (attendu: {LANGAGES}).")
    if payload.port is not None and not (1 <= int(payload.port) <= 65535):
        raise HTTPException(status_code=400, detail="Port invalide (1-65535).")
    tc = getattr(payload, "type_connexion", None)
    if tc is not None and tc not in TYPES_CONNEXION:
        raise HTTPException(status_code=400, detail=f"Type de connexion invalide (attendu: {TYPES_CONNEXION}).")


@router.get("/imprimantes")
def list_imprimantes(request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id,nom,poste,agent_id,type_connexion,ip_locale,port,nom_queue_windows,"
            "langage,largeur_mm,hauteur_mm,dpi,actif,note "
            "FROM imprimantes ORDER BY COALESCE(poste,''), nom"
        ).fetchall()
    return [_serialize_imprimante(r) for r in rows]


@router.post("/imprimantes")
def create_imprimante(payload: ImprimanteBase, request: Request):
    u = require_superadmin(request)
    _validate_imprimante(payload)
    tc = (payload.type_connexion or "tcp_ip").strip()
    if tc not in TYPES_CONNEXION:
        raise HTTPException(status_code=400, detail=f"Type de connexion invalide (attendu: {TYPES_CONNEXION}).")
    # v1.7 — une imprimante de langage="pdf" DOIT etre en windows_local
    # (SumatraPDF ne sait envoyer qu'a une queue Windows locale). Cette
    # contrainte evite de creer une config incoherente qui echouerait
    # silencieusement cote agent.
    if payload.langage == "pdf" and tc != "windows_local":
        raise HTTPException(
            status_code=400,
            detail=("Une imprimante PDF (bureautique) doit etre en 'windows_local' "
                    "avec un nom de queue Windows. SumatraPDF, utilise cote agent, "
                    "ne peut envoyer qu'a une queue Windows locale."),
        )
    # Normalise selon type_connexion : champs non utilises = valeurs vides
    # plutot que NULL pour rester compatible avec la contrainte NOT NULL heritee.
    if tc == "tcp_ip":
        if not payload.ip_locale or not str(payload.ip_locale).strip():
            raise HTTPException(status_code=400, detail="IP requise pour une imprimante TCP/IP.")
        ip = str(payload.ip_locale).strip()
        port = int(payload.port or 9100)
        queue = None
    else:  # windows_local
        if not payload.nom_queue_windows or not str(payload.nom_queue_windows).strip():
            raise HTTPException(status_code=400, detail="Nom de la queue Windows requis pour une imprimante locale.")
        ip = ""
        port = 0
        queue = str(payload.nom_queue_windows).strip()
    now = _now()
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO imprimantes (nom,poste,agent_id,type_connexion,ip_locale,port,nom_queue_windows,"
            "langage,largeur_mm,hauteur_mm,dpi,actif,created_at,created_by,note) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,1,?,?,?)",
            (
                payload.nom.strip(), (payload.poste or "").strip() or None, payload.agent_id,
                tc, ip, port, queue,
                payload.langage,
                int(payload.largeur_mm), int(payload.hauteur_mm), int(payload.dpi),
                now, u.get("email"), (payload.note or "").strip() or None,
            ),
        )
        iid = cur.lastrowid
        # Seed des templates par défaut (uniquement pour le ZPL — les autres langages
        # nécessitent que l'admin écrive lui-même son gabarit).
        if payload.langage == "zpl":
            for tpl in default_templates_seed():
                conn.execute(
                    "INSERT INTO imprimante_templates (imprimante_id,usage_key,nom,contenu,actif,updated_at,updated_by) "
                    "VALUES (?,?,?,?,1,?,?)",
                    (iid, tpl["usage_key"], tpl["nom"], tpl["contenu"], now, u.get("email")),
                )
        conn.commit()
    return {"id": iid, "ok": True}


@router.patch("/imprimantes/{imprimante_id}")
def patch_imprimante(imprimante_id: int, payload: ImprimantePatch, request: Request):
    require_superadmin(request)
    _validate_imprimante(payload)
    fields, values = [], []
    for f in ("nom", "poste", "agent_id", "type_connexion", "ip_locale", "port",
              "nom_queue_windows", "langage",
              "largeur_mm", "hauteur_mm", "dpi", "note"):
        val = getattr(payload, f)
        if val is not None:
            if isinstance(val, str):
                val = val.strip() or None
            fields.append(f"{f}=?")
            values.append(val)
    if payload.actif is not None:
        fields.append("actif=?"); values.append(1 if payload.actif else 0)
    if not fields:
        raise HTTPException(status_code=400, detail="Aucun champ à modifier.")
    values.append(imprimante_id)
    with get_db() as conn:
        cur = conn.execute(f"UPDATE imprimantes SET {','.join(fields)} WHERE id=?", values)
        conn.commit()
        if not cur.rowcount:
            raise HTTPException(status_code=404, detail="Imprimante introuvable.")
    return {"ok": True}


@router.delete("/imprimantes/{imprimante_id}")
def delete_imprimante(imprimante_id: int, request: Request):
    require_superadmin(request)
    with get_db() as conn:
        cur = conn.execute("DELETE FROM imprimantes WHERE id=?", (imprimante_id,))
        conn.commit()
        if not cur.rowcount:
            raise HTTPException(status_code=404, detail="Imprimante introuvable.")
    return {"ok": True}


# ═══════════════════════════════════════════════════════════════════════
# ENDPOINTS ADMIN — Templates
# ═══════════════════════════════════════════════════════════════════════

class TemplateCreate(BaseModel):
    imprimante_id: int
    usage_key: str
    nom: str
    contenu: str


class TemplatePatch(BaseModel):
    nom: Optional[str] = None
    contenu: Optional[str] = None
    actif: Optional[bool] = None


@router.get("/templates")
def list_templates(request: Request, imprimante_id: Optional[int] = None):
    require_superadmin(request)
    q = ("SELECT id,imprimante_id,usage_key,nom,contenu,actif,updated_at,updated_by "
         "FROM imprimante_templates")
    args: list = []
    if imprimante_id:
        q += " WHERE imprimante_id=?"; args.append(imprimante_id)
    q += " ORDER BY imprimante_id, usage_key, nom"
    with get_db() as conn:
        rows = conn.execute(q, args).fetchall()
    return [_serialize_template(r) for r in rows]


@router.post("/templates")
def create_template(payload: TemplateCreate, request: Request):
    u = require_superadmin(request)
    now = _now()
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO imprimante_templates (imprimante_id,usage_key,nom,contenu,actif,updated_at,updated_by) "
            "VALUES (?,?,?,?,1,?,?)",
            (payload.imprimante_id, payload.usage_key.strip(), payload.nom.strip(),
             payload.contenu, now, u.get("email")),
        )
        conn.commit()
    return {"id": cur.lastrowid, "ok": True}


@router.patch("/templates/{template_id}")
def patch_template(template_id: int, payload: TemplatePatch, request: Request):
    u = require_superadmin(request)
    fields, values = [], []
    if payload.nom is not None:
        fields.append("nom=?"); values.append(payload.nom.strip())
    if payload.contenu is not None:
        fields.append("contenu=?"); values.append(payload.contenu)
    if payload.actif is not None:
        fields.append("actif=?"); values.append(1 if payload.actif else 0)
    if not fields:
        raise HTTPException(status_code=400, detail="Aucun champ à modifier.")
    fields.append("updated_at=?"); values.append(_now())
    fields.append("updated_by=?"); values.append(u.get("email"))
    values.append(template_id)
    with get_db() as conn:
        cur = conn.execute(f"UPDATE imprimante_templates SET {','.join(fields)} WHERE id=?", values)
        conn.commit()
        if not cur.rowcount:
            raise HTTPException(status_code=404, detail="Template introuvable.")
    return {"ok": True}


@router.delete("/templates/{template_id}")
def delete_template(template_id: int, request: Request):
    require_superadmin(request)
    with get_db() as conn:
        cur = conn.execute("DELETE FROM imprimante_templates WHERE id=?", (template_id,))
        conn.commit()
        if not cur.rowcount:
            raise HTTPException(status_code=404, detail="Template introuvable.")
    return {"ok": True}


# ═══════════════════════════════════════════════════════════════════════
# ENDPOINTS USER — usages, defaults, impression
# ═══════════════════════════════════════════════════════════════════════

@router.get("/usages")
def list_usages(request: Request):
    get_current_user(request)
    return USAGES


@router.get("/my-imprimantes")
def list_my_imprimantes(request: Request):
    get_current_user(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id,nom,poste,langage FROM imprimantes WHERE actif=1 ORDER BY COALESCE(poste,''), nom"
        ).fetchall()
    return [{"id": r["id"], "nom": r["nom"], "poste": r["poste"], "langage": r["langage"]} for r in rows]


@router.get("/my-defaults")
def get_my_defaults(request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT usage_key,imprimante_id FROM user_printer_defaults WHERE user_email=?",
            (user.get("email"),),
        ).fetchall()
    return {r["usage_key"]: r["imprimante_id"] for r in rows}


class MyDefaultsPayload(BaseModel):
    defaults: dict


@router.put("/my-defaults")
def set_my_defaults(payload: MyDefaultsPayload, request: Request):
    user = get_current_user(request)
    email = user.get("email")
    now = _now()
    with get_db() as conn:
        for usage_key, imp_id in (payload.defaults or {}).items():
            if imp_id in (None, 0, ""):
                conn.execute(
                    "DELETE FROM user_printer_defaults WHERE user_email=? AND usage_key=?",
                    (email, usage_key),
                )
                continue
            conn.execute(
                "INSERT INTO user_printer_defaults (user_email,usage_key,imprimante_id,updated_at) "
                "VALUES (?,?,?,?) "
                "ON CONFLICT(user_email,usage_key) DO UPDATE SET imprimante_id=excluded.imprimante_id, updated_at=excluded.updated_at",
                (email, usage_key, int(imp_id), now),
            )
        conn.commit()
    return {"ok": True}


class LabelRequest(BaseModel):
    usage_key: str
    data: dict
    imprimante_id: Optional[int] = None       # override du défaut utilisateur
    copies: int = 1                            # nombre de copies (bobines à étiqueter)


@router.post("/label")
def emit_label(payload: LabelRequest, request: Request):
    """Émet 1..N jobs d'impression pour une même donnée.

    - Résolution de l'imprimante :
        1. `imprimante_id` explicite dans le payload
        2. sinon défaut utilisateur (user_printer_defaults) pour cet usage
        3. sinon erreur 409 → le client doit demander à l'utilisateur de choisir
    - Cherche le template associé à cette imprimante pour cet usage_key.
      Si absent, 409 avec message explicite.
    - Crée un job par copie, statut=pending. L'agent local les récupérera.
    """
    user = get_current_user(request)
    email = user.get("email")
    copies = max(1, min(999, int(payload.copies or 1)))

    with get_db() as conn:
        # Résolution imprimante
        imp_id = payload.imprimante_id
        if not imp_id:
            row = conn.execute(
                "SELECT imprimante_id FROM user_printer_defaults WHERE user_email=? AND usage_key=?",
                (email, payload.usage_key),
            ).fetchone()
            if row:
                imp_id = row["imprimante_id"]
        if not imp_id:
            raise HTTPException(
                status_code=409,
                detail=("Aucune imprimante configurée pour cet usage. "
                        "Configure une imprimante par défaut dans ton profil, "
                        "ou passe imprimante_id dans la requête."),
            )
        imp = conn.execute(
            "SELECT id,nom,agent_id,langage,actif FROM imprimantes WHERE id=?",
            (imp_id,),
        ).fetchone()
        if not imp:
            raise HTTPException(status_code=404, detail="Imprimante introuvable.")
        if not imp["actif"]:
            raise HTTPException(status_code=409, detail="Imprimante désactivée.")
        # Cherche le template
        tpl = conn.execute(
            "SELECT id,contenu FROM imprimante_templates "
            "WHERE imprimante_id=? AND usage_key=? AND actif=1 LIMIT 1",
            (imp_id, payload.usage_key),
        ).fetchone()
        if not tpl:
            raise HTTPException(
                status_code=409,
                detail=(f"Aucun template actif pour l'usage « {payload.usage_key} » "
                        f"sur l'imprimante « {imp['nom']} ». À configurer dans /settings > Imprimantes."),
            )
        # Rendu + insertion des jobs
        try:
            payload_bytes = render_template(tpl["contenu"], payload.data or {}, imp["langage"])
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erreur rendu template: {e}")
        now = _now()
        job_ids = []
        import json as _json
        data_json = _json.dumps(payload.data or {}, ensure_ascii=False)
        for _ in range(copies):
            cur = conn.execute(
                "INSERT INTO print_jobs (imprimante_id,agent_id,usage_key,template_id,payload,"
                "payload_langage,status,created_at,created_by,data_json) "
                "VALUES (?,?,?,?,?,?,'pending',?,?,?)",
                (imp_id, imp["agent_id"], payload.usage_key, tpl["id"],
                 payload_bytes, imp["langage"], now, email, data_json),
            )
            job_ids.append(cur.lastrowid)
        conn.commit()
    return {"ok": True, "job_ids": job_ids, "imprimante": imp["nom"], "copies": copies}


# ═══════════════════════════════════════════════════════════════════════
# ENDPOINT USER — Impression PDF bureautique (OF, fiches techniques) (v1.7)
# ═══════════════════════════════════════════════════════════════════════
#
# Pipeline :
#   Front (MyProd Fiches/OF) → POST /api/print/pdf {entity_type, entity_id,
#     imprimante_id, copies, duplex, format, bin, color}
#   → resolve imprimante (id explicite ou defaut utilisateur)
#   → fetch le PDF selon entity_type :
#        - "of"    : lit `of_imports.pdf_filename`, charge le fichier disque
#        - "fiche" : appelle generate_fiche_pdf(row_dict) a la volee
#   → stocke le PDF en BLOB dans print_jobs.payload avec payload_langage="pdf"
#   → serialise les params impression (copies, duplex, ...) dans data_json
#   → agent local (Windows) recupere le job, decode le PDF, invoque SumatraPDF
#     avec les params extraits de data_json.

_PDF_DUPLEX_VALUES = ("simplex", "long-edge", "short-edge")
_PDF_COLOR_VALUES = ("color", "monochrome")
_PDF_FORMAT_VALUES = ("A4", "A5", "A3", "Letter", "Legal")


class PdfPrintRequest(BaseModel):
    entity_type: str = Field(..., description="'of' ou 'fiche'")
    entity_id: int
    imprimante_id: Optional[int] = None
    copies: int = 1
    # Options impression bureautique (interpretees par l'agent via SumatraPDF)
    duplex: str = "simplex"                # simplex | long-edge | short-edge
    format: str = "A4"                     # A4 | A5 | A3 | Letter | Legal
    bin: Optional[str] = None              # nom du bac (ex: "Tray1"); None = defaut driver
    color: str = "color"                   # color | monochrome


def _fetch_pdf_bytes(entity_type: str, entity_id: int) -> tuple[bytes, str]:
    """Retourne (pdf_bytes, filename_suggere) pour l'entite demandee.

    - 'of'    : lit le PDF importe depuis of_imports.pdf_filename (sur disque).
    - 'fiche' : appelle app.services.fiche_pdf.generate_fiche_pdf() a la volee.

    Leve HTTPException si l'entite est introuvable ou le PDF absent.
    """
    et = (entity_type or "").strip().lower()
    if et not in ("of", "fiche"):
        raise HTTPException(status_code=400, detail="entity_type invalide (attendu: 'of' ou 'fiche').")

    with get_db() as conn:
        if et == "of":
            row = conn.execute(
                "SELECT id, of_numero, pdf_filename FROM of_imports WHERE id=? LIMIT 1",
                (entity_id,),
            ).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="OF introuvable.")
            pdf_filename = row["pdf_filename"]
            if not pdf_filename:
                raise HTTPException(status_code=409, detail="Cet OF n'a pas de PDF associe.")
            # OF_UPLOAD_DIR est defini dans of_import.py — on le reimporte pour rester DRY.
            try:
                from app.routers.of_import import OF_UPLOAD_DIR  # type: ignore
            except Exception:
                # Fallback : reconstitue le chemin depuis data/uploads/of/
                from pathlib import Path as _P
                OF_UPLOAD_DIR = str(_P(__file__).resolve().parent.parent.parent / "data" / "uploads" / "of")
            import os as _os
            path = _os.path.join(OF_UPLOAD_DIR, pdf_filename)
            if not _os.path.isfile(path):
                raise HTTPException(status_code=404, detail=f"PDF introuvable sur le serveur : {pdf_filename}")
            with open(path, "rb") as f:
                return f.read(), pdf_filename
        # et == "fiche"
        row = conn.execute(
            "SELECT * FROM fiches_techniques WHERE id=? LIMIT 1",
            (entity_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Fiche technique introuvable.")
        try:
            from app.services.fiche_pdf import generate_fiche_pdf
            pdf_bytes = generate_fiche_pdf(dict(row))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erreur generation PDF fiche : {e}")
        ref = row["reference"] if "reference" in row.keys() else f"fiche-{entity_id}"
        return pdf_bytes, f"fiche_{ref}.pdf"


@router.post("/pdf")
def emit_pdf_print(payload: PdfPrintRequest, request: Request):
    """Emet un job d'impression PDF (bureautique) vers une imprimante rattachee
    a un agent local Windows equipe de SumatraPDF.

    - Resolution imprimante :
        1. `imprimante_id` explicite
        2. sinon defaut utilisateur pour l'usage_key deduit de entity_type
           ('of_document' pour 'of', 'fiche_technique' pour 'fiche')
        3. sinon erreur 409 → le client doit demander a l'utilisateur de choisir
    - L'imprimante DOIT etre de langage 'pdf' (sinon 409).
    - Le PDF est stocke tel quel en BLOB. Les params sont dans data_json,
      l'agent les lit et les passe a SumatraPDF.
    """
    user = get_current_user(request)
    email = user.get("email")
    copies = max(1, min(999, int(payload.copies or 1)))

    # Validation options
    duplex = (payload.duplex or "simplex").strip().lower()
    if duplex not in _PDF_DUPLEX_VALUES:
        raise HTTPException(status_code=400, detail=f"duplex invalide (attendu: {_PDF_DUPLEX_VALUES}).")
    color = (payload.color or "color").strip().lower()
    if color not in _PDF_COLOR_VALUES:
        raise HTTPException(status_code=400, detail=f"color invalide (attendu: {_PDF_COLOR_VALUES}).")
    fmt = (payload.format or "A4").strip()
    if fmt not in _PDF_FORMAT_VALUES:
        raise HTTPException(status_code=400, detail=f"format invalide (attendu: {_PDF_FORMAT_VALUES}).")

    # Deduit l'usage_key depuis entity_type (pour resolution du defaut utilisateur)
    et = (payload.entity_type or "").strip().lower()
    if et == "of":
        usage_key = "of_document"
    elif et == "fiche":
        usage_key = "fiche_technique"
    else:
        raise HTTPException(status_code=400, detail="entity_type invalide (attendu: 'of' ou 'fiche').")

    # Recupere le PDF (leve HTTPException si probleme)
    pdf_bytes, filename = _fetch_pdf_bytes(et, payload.entity_id)

    with get_db() as conn:
        # Resolution imprimante
        imp_id = payload.imprimante_id
        if not imp_id:
            row = conn.execute(
                "SELECT imprimante_id FROM user_printer_defaults WHERE user_email=? AND usage_key=?",
                (email, usage_key),
            ).fetchone()
            if row:
                imp_id = row["imprimante_id"]
        if not imp_id:
            raise HTTPException(
                status_code=409,
                detail=("Aucune imprimante configuree pour cet usage. "
                        "Choisis une imprimante dans le popup, ou fixe un defaut dans ton profil."),
            )
        imp = conn.execute(
            "SELECT id,nom,agent_id,langage,actif FROM imprimantes WHERE id=?",
            (imp_id,),
        ).fetchone()
        if not imp:
            raise HTTPException(status_code=404, detail="Imprimante introuvable.")
        if not imp["actif"]:
            raise HTTPException(status_code=409, detail="Imprimante desactivee.")
        if imp["langage"] != "pdf":
            raise HTTPException(
                status_code=409,
                detail=(f"L'imprimante « {imp['nom']} » n'est pas configuree pour le PDF "
                        f"(langage={imp['langage']}). Choisis une imprimante bureautique "
                        f"(langage=pdf) pour imprimer un document."),
            )

        # Prepare data_json pour l'agent (options SumatraPDF)
        import json as _json
        print_options = {
            "copies": copies,          # SumatraPDF gere les copies via `-print-settings copies=N`
            "duplex": duplex,          # simplex | long-edge | short-edge
            "format": fmt,             # A4 | A5 | A3 | Letter | Legal
            "bin": payload.bin,        # None ou nom du bac
            "color": color,            # color | monochrome
            "filename": filename,      # nom suggere pour le fichier temp cote agent
        }
        data_json = _json.dumps(print_options, ensure_ascii=False)

        # Un seul job (pas N jobs comme pour les etiquettes) — les copies sont
        # gerees par SumatraPDF via -print-settings copies=N. Simplifie le suivi
        # et evite d'ouvrir/fermer SumatraPDF N fois.
        now = _now()
        cur = conn.execute(
            "INSERT INTO print_jobs (imprimante_id,agent_id,usage_key,template_id,payload,"
            "payload_langage,status,created_at,created_by,data_json) "
            "VALUES (?,?,?,?,?,?,'pending',?,?,?)",
            (imp_id, imp["agent_id"], usage_key, None, pdf_bytes,
             "pdf", now, email, data_json),
        )
        job_id = cur.lastrowid
        conn.commit()

    return {
        "ok": True,
        "job_id": job_id,
        "imprimante": imp["nom"],
        "copies": copies,
        "filename": filename,
        "size_bytes": len(pdf_bytes),
    }


class TestPrintPayload(BaseModel):
    imprimante_id: int


# ─── Aperçu WYSIWYG d'un template ZPL via labelary.com ────────────────

def _labelary_render_zpl(zpl: str, dpi: int, width_mm: int, height_mm: int) -> bytes:
    """Rend un template ZPL en PNG via l'API publique labelary.com.
    Renvoie le PNG en bytes. Leve HTTPException si erreur reseau ou API.
    """
    dpmm = max(6, min(24, round(dpi / 25.4)))  # 8dpmm = 203dpi, 12 = 300dpi, 24 = 600dpi
    # Labelary attend width/height en INCHES avec 1 decimale max
    width_in = round(max(0.5, width_mm / 25.4), 1)
    height_in = round(max(0.5, height_mm / 25.4), 1)
    url = f"http://api.labelary.com/v1/printers/{dpmm}dpmm/labels/{width_in}x{height_in}/0/"
    req = urllib.request.Request(
        url,
        data=zpl.encode("utf-8"),
        headers={"Accept": "image/png", "Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=f"Labelary HTTP {e.code} : {detail or e.reason}")
    except urllib.error.URLError as e:
        raise HTTPException(status_code=502, detail=f"Labelary reseau : {e.reason}")


class PreviewPayload(BaseModel):
    contenu: str = Field(min_length=1)
    langage: str = "zpl"
    largeur_mm: int = 102
    hauteur_mm: int = 152
    dpi: int = 203


@router.post("/preview")
def preview_template(payload: PreviewPayload, request: Request):
    """Rend un template en PNG (via labelary) pour aperçu dans l'UI editeur.
    Utilise des donnees mock pour les placeholders (lot demo, fournisseur demo, etc.).
    """
    require_superadmin(request)
    if payload.langage != "zpl":
        raise HTTPException(status_code=400, detail="Apercu supporte uniquement le ZPL pour l'instant.")
    # Donnees mock pour resoudre les placeholders
    mock = {
        "lot_numero": "LOT-2026-07-DEMO-42",
        "fournisseur": "Papeterie Exemple SA",
        "fsc_label": "FSC C012345",
        "fsc_banner": "FSC",
        "ref_produit": "PAPIER-KRAFT-80G",
        "code_barre": "MYSIFA-2026-07-DEMO",
        "operateur_nom": "Eugene L.",
        "date_reception": "20/07/2026",
    }
    try:
        rendered_bytes = render_template(payload.contenu, mock, payload.langage)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur rendu template : {e}")
    rendered_str = rendered_bytes.decode("utf-8", errors="replace")
    png = _labelary_render_zpl(
        rendered_str,
        int(payload.dpi or 203),
        int(payload.largeur_mm or 102),
        int(payload.hauteur_mm or 152),
    )
    return Response(content=png, media_type="image/png")


@router.get("/templates/defaults")
def list_default_templates_gallery(request: Request):
    """Galerie de templates predefinis (bobine, colis, emplacement, etc.)
    utilisee dans le modal 'Nouveau template' pour demarrer depuis un modele."""
    require_superadmin(request)
    return {"templates": list_default_templates()}


@router.get("/templates/defaults/{key}")
def get_default_template_content(key: str, request: Request):
    """Renvoie le contenu complet (avec ZPL) d'un template predefini."""
    require_superadmin(request)
    t = get_default_template(key)
    if not t:
        raise HTTPException(status_code=404, detail="Template predefini introuvable.")
    return t


@router.get("/agent-script")
def download_agent_script(request: Request):
    """Sert print_agent.py a un agent authentifie via X-Agent-Token.
    Utilise par install_agent_windows.ps1 pour telecharger automatiquement
    l'agent Python au demarrage (evite au user de copier 2 fichiers)."""
    _agent_from_token(request)  # auth via X-Agent-Token
    py_path = Path(__file__).resolve().parent.parent.parent / "tools" / "print_agent" / "print_agent.py"
    if not py_path.is_file():
        raise HTTPException(status_code=404, detail="print_agent.py introuvable sur le serveur.")
    return FileResponse(
        path=str(py_path),
        media_type="text/x-python",
        filename="print_agent.py",
    )


@router.get("/installer/windows")
def download_windows_installer(request: Request):
    """Sert le script PowerShell d'install de l'agent MySifa pour PC Windows hote.
    Utilise par le wizard 'Comment connecter mon imprimante' cote UI.
    """
    require_superadmin(request)
    # Le fichier vit dans le repo à tools/print_agent/install_agent_windows.ps1
    # Chemin resolu depuis app/routers/print.py : ../../../tools/print_agent/...
    ps1_path = Path(__file__).resolve().parent.parent.parent / "tools" / "print_agent" / "install_agent_windows.ps1"
    if not ps1_path.is_file():
        raise HTTPException(status_code=404, detail="Installeur introuvable sur le serveur.")
    return FileResponse(
        path=str(ps1_path),
        media_type="text/plain",
        filename="install_agent_windows.ps1",
    )


@router.post("/test")
def test_print(payload: TestPrintPayload, request: Request):
    """Impression de test : envoie une petite étiquette hardcodée à l'imprimante."""
    u = require_superadmin(request)
    with get_db() as conn:
        imp = conn.execute(
            "SELECT id,nom,agent_id,langage,largeur_mm,hauteur_mm,dpi,actif FROM imprimantes WHERE id=?",
            (payload.imprimante_id,),
        ).fetchone()
        if not imp:
            raise HTTPException(status_code=404, detail="Imprimante introuvable.")
        if not imp["actif"]:
            raise HTTPException(status_code=409, detail="Imprimante désactivée.")

        # Template de test hardcodé (ZPL simple 3"x2" équivalent)
        if imp["langage"] == "zpl":
            tpl = (
                "^XA^CI28^PW600^LL400"
                "^FO40,40^A0N,40,40^FDMySifa - Impression test^FS"
                "^FO40,110^A0N,26,26^FDImprimante: {{nom}}^FS"
                "^FO40,150^A0N,26,26^FDDate: {{now:%d/%m/%Y %H:%M}}^FS"
                "^FO40,200^BY2^BCN,80,Y,N,N^FDMYSIFA-TEST^FS"
                "^XZ"
            )
        else:
            tpl = "MySifa test\nImprimante {{nom}}\n{{now:%d/%m/%Y %H:%M}}\n"

        try:
            payload_bytes = render_template(tpl, {"nom": imp["nom"]}, imp["langage"])
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erreur rendu: {e}")

        now = _now()
        cur = conn.execute(
            "INSERT INTO print_jobs (imprimante_id,agent_id,usage_key,template_id,payload,"
            "payload_langage,status,created_at,created_by,data_json) "
            "VALUES (?,?,?,?,?,?,'pending',?,?,?)",
            (imp["id"], imp["agent_id"], "test", None, payload_bytes,
             imp["langage"], now, u.get("email"), "{}"),
        )
        conn.commit()
    return {"ok": True, "job_id": cur.lastrowid, "message": f"Test envoyé à {imp['nom']}."}


# ═══════════════════════════════════════════════════════════════════════
# ENDPOINTS AGENT (auth par X-Agent-Token)
# ═══════════════════════════════════════════════════════════════════════

@router.post("/agent/heartbeat")
def agent_heartbeat(request: Request):
    agent = _agent_from_token(request)
    now = _now()
    client_ip = request.client.host if request.client else None
    with get_db() as conn:
        conn.execute(
            "UPDATE print_agents SET last_heartbeat=?, last_ip=? WHERE id=?",
            (now, client_ip, agent["id"]),
        )
        # Retourne aussi la liste des imprimantes rattachées à cet agent
        # (l'agent en a besoin pour connaître les ip/port cibles).
        rows = conn.execute(
            "SELECT id,nom,type_connexion,ip_locale,port,nom_queue_windows,langage "
            "FROM imprimantes WHERE agent_id=? AND actif=1",
            (agent["id"],),
        ).fetchall()
        conn.commit()
    def _hb_imp(r):
        tc = "tcp_ip"
        queue = None
        try:
            tc = (r["type_connexion"] or "tcp_ip")
        except (IndexError, KeyError):
            pass
        try:
            queue = r["nom_queue_windows"]
        except (IndexError, KeyError):
            pass
        return {
            "id": r["id"], "nom": r["nom"],
            "type_connexion": tc,
            "ip": r["ip_locale"], "port": r["port"],
            "nom_queue_windows": queue,
            "langage": r["langage"],
        }
    return {
        "ok": True,
        "server_time": now,
        "imprimantes": [_hb_imp(r) for r in rows],
    }


@router.get("/agent/jobs")
def agent_get_jobs(request: Request, limit: int = 20):
    agent = _agent_from_token(request)
    limit = max(1, min(100, int(limit)))
    now = _now()
    with get_db() as conn:
        # On sélectionne les jobs pending pour les imprimantes rattachées à cet
        # agent (ou celles dont agent_id est NULL — pas encore rattachées).
        rows = conn.execute(
            "SELECT pj.id,pj.imprimante_id,pj.payload,pj.payload_langage,pj.tentatives,"
            "pj.data_json,"  # v1.7 — options impression PDF (copies/duplex/format/bin/color)
            "i.nom AS imp_nom,i.type_connexion,i.ip_locale,i.port,i.nom_queue_windows "
            "FROM print_jobs pj JOIN imprimantes i ON i.id=pj.imprimante_id "
            "WHERE pj.status='pending' AND (i.agent_id=? OR i.agent_id IS NULL) "
            "ORDER BY pj.id ASC LIMIT ?",
            (agent["id"], limit),
        ).fetchall()
        picked_ids = [r["id"] for r in rows]
        if picked_ids:
            qmarks = ",".join(["?"] * len(picked_ids))
            conn.execute(
                f"UPDATE print_jobs SET status='picked', picked_at=?, agent_id=?, "
                f"tentatives=tentatives+1 WHERE id IN ({qmarks})",
                [now, agent["id"], *picked_ids],
            )
            conn.commit()
    import base64
    def _imp_info(r):
        tc = "tcp_ip"
        try:
            tc = (r["type_connexion"] or "tcp_ip")
        except (IndexError, KeyError):
            pass
        info = {
            "id": r["imprimante_id"], "nom": r["imp_nom"],
            "type_connexion": tc,
            "ip": r["ip_locale"], "port": r["port"],
        }
        if tc == "windows_local":
            try:
                info["nom_queue_windows"] = r["nom_queue_windows"]
            except (IndexError, KeyError):
                info["nom_queue_windows"] = None
        return info
    # v1.7 — parse data_json cote serveur (evite a l'agent de gerer un decode
    # JSON eventuellement bugue). Pour les jobs pre-v1.7 (langage zpl/epl/escpos)
    # data_json contient juste les data metier du template — inutile pour l'agent.
    # Pour les jobs PDF, il contient {copies, duplex, format, bin, color, filename}.
    import json as _json
    def _parse_options(raw):
        if not raw:
            return {}
        try:
            v = _json.loads(raw)
            return v if isinstance(v, dict) else {}
        except Exception:
            return {}
    return {
        "jobs": [
            {
                "id": r["id"],
                "imprimante": _imp_info(r),
                "langage": r["payload_langage"],
                "payload_b64": base64.b64encode(bytes(r["payload"])).decode("ascii"),
                "tentatives": r["tentatives"] + 1,
                # v1.7 — expose les options d'impression a l'agent (utile pour PDF/SumatraPDF).
                # Vide {} pour les jobs pre-v1.7 ou pour les etiquettes qui n'ont pas d'options.
                "options": _parse_options(r["data_json"]) if r["payload_langage"] == "pdf" else {},
            }
            for r in rows
        ]
    }


class AgentAck(BaseModel):
    ok: bool = True
    erreur: Optional[str] = None


@router.post("/agent/jobs/{job_id}/ack")
def agent_ack(job_id: int, payload: AgentAck, request: Request):
    agent = _agent_from_token(request)
    now = _now()
    with get_db() as conn:
        if payload.ok:
            cur = conn.execute(
                "UPDATE print_jobs SET status='done', ack_at=?, erreur=NULL "
                "WHERE id=? AND agent_id=?",
                (now, job_id, agent["id"]),
            )
        else:
            # Après 3 tentatives, on marque failed définitif ; sinon on repasse pending pour retry.
            row = conn.execute(
                "SELECT tentatives FROM print_jobs WHERE id=? AND agent_id=?",
                (job_id, agent["id"]),
            ).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Job introuvable.")
            if row["tentatives"] >= 3:
                cur = conn.execute(
                    "UPDATE print_jobs SET status='failed', ack_at=?, erreur=? WHERE id=?",
                    (now, (payload.erreur or "")[:500], job_id),
                )
            else:
                cur = conn.execute(
                    "UPDATE print_jobs SET status='pending', erreur=? WHERE id=?",
                    ((payload.erreur or "")[:500], job_id),
                )
        conn.commit()
        if not cur.rowcount:
            raise HTTPException(status_code=404, detail="Job introuvable.")
    return {"ok": True}

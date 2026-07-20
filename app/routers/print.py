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

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.services.auth_service import get_current_user, require_superadmin
from app.services.print_render import (
    LANGAGES,
    USAGES,
    default_templates_seed,
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
    return {
        "id": row["id"],
        "nom": row["nom"],
        "poste": row["poste"],
        "agent_id": row["agent_id"],
        "ip_locale": row["ip_locale"],
        "port": row["port"],
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

class ImprimanteBase(BaseModel):
    nom: str = Field(min_length=1, max_length=80)
    poste: Optional[str] = None
    agent_id: Optional[int] = None
    ip_locale: str = Field(min_length=1, max_length=64)
    port: int = 9100
    langage: str = "zpl"
    largeur_mm: int = 102
    hauteur_mm: int = 152
    dpi: int = 203
    note: Optional[str] = None


class ImprimantePatch(BaseModel):
    nom: Optional[str] = None
    poste: Optional[str] = None
    agent_id: Optional[int] = None
    ip_locale: Optional[str] = None
    port: Optional[int] = None
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


@router.get("/imprimantes")
def list_imprimantes(request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id,nom,poste,agent_id,ip_locale,port,langage,largeur_mm,hauteur_mm,dpi,actif,note "
            "FROM imprimantes ORDER BY COALESCE(poste,''), nom"
        ).fetchall()
    return [_serialize_imprimante(r) for r in rows]


@router.post("/imprimantes")
def create_imprimante(payload: ImprimanteBase, request: Request):
    u = require_superadmin(request)
    _validate_imprimante(payload)
    now = _now()
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO imprimantes (nom,poste,agent_id,ip_locale,port,langage,largeur_mm,hauteur_mm,dpi,"
            "actif,created_at,created_by,note) VALUES (?,?,?,?,?,?,?,?,?,1,?,?,?)",
            (
                payload.nom.strip(), (payload.poste or "").strip() or None, payload.agent_id,
                payload.ip_locale.strip(), int(payload.port), payload.langage,
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
    for f in ("nom", "poste", "agent_id", "ip_locale", "port", "langage",
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


class TestPrintPayload(BaseModel):
    imprimante_id: int


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
            "SELECT id,nom,ip_locale,port,langage FROM imprimantes WHERE agent_id=? AND actif=1",
            (agent["id"],),
        ).fetchall()
        conn.commit()
    return {
        "ok": True,
        "server_time": now,
        "imprimantes": [
            {"id": r["id"], "nom": r["nom"], "ip": r["ip_locale"], "port": r["port"],
             "langage": r["langage"]}
            for r in rows
        ],
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
            "i.nom AS imp_nom,i.ip_locale,i.port "
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
    return {
        "jobs": [
            {
                "id": r["id"],
                "imprimante": {
                    "id": r["imprimante_id"], "nom": r["imp_nom"],
                    "ip": r["ip_locale"], "port": r["port"],
                },
                "langage": r["payload_langage"],
                "payload_b64": base64.b64encode(bytes(r["payload"])).decode("ascii"),
                "tentatives": r["tentatives"] + 1,
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

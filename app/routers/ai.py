"""MySifa — Agent IA (widget présent sur tout le site).

  GET  /api/ai/brief                        résumé de la journée (direction)
  GET  /api/ai/config                       le widget s'affiche-t-il, quels modèles
  POST /api/ai/chat                         une question → réponse + actions proposées
  POST /api/ai/actions/{jeton}/confirmer    exécute une action proposée
  POST /api/ai/actions/{jeton}/annuler

La logique vit dans app/services/agent_ia.py (lecture, boucle) et
app/services/agent_actions.py (catalogue fermé des écritures, exécution).
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from config import AGENT_IA_ACTION_TTL_MIN, AGENT_IA_MODELE, AGENT_IA_RATE_MAX, ROLES_AGENT_IA, agent_ia_modeles
from database import get_db
from services.auth_service import get_current_user
from app.services.ai_context import BRIEF_ROLES
from app.services.ai_data import build_daily_brief
from app.services import agent_ia, agent_actions
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/ai", tags=["agent-ia"])

RATE_WINDOW_SEC = 60.0
_rate_buckets: dict[Any, list[float]] = {}


def _agent_autorise(user: dict) -> bool:
    return user.get("role") == "superadmin" or user.get("role") in ROLES_AGENT_IA


def _user_agent(request: Request) -> dict:
    user = get_current_user(request)
    if not _agent_autorise(user):
        raise HTTPException(403, detail="Agent IA non ouvert pour ce rôle.")
    return user


def _check_rate_limit(user: dict) -> None:
    uid = user.get("id") or user.get("email") or "?"
    now = time.time()
    for key in list(_rate_buckets):
        _rate_buckets[key] = [t for t in _rate_buckets[key] if t > now - RATE_WINDOW_SEC]
        if not _rate_buckets[key]:
            del _rate_buckets[key]
    times = _rate_buckets.setdefault(uid, [])
    if len(times) >= AGENT_IA_RATE_MAX:
        raise HTTPException(429, detail="Trop de requêtes — attendre une minute.")
    times.append(now)


@router.get("/brief")
def ai_brief(request: Request):
    """Résumé JSON de la journée — direction et superadmin uniquement."""
    user = get_current_user(request)
    if user.get("role", "") not in BRIEF_ROLES:
        raise HTTPException(403, detail="Accès réservé à la direction.")
    with get_db() as conn:
        return build_daily_brief(conn)


@router.get("/config")
def ai_config(request: Request):
    user = get_current_user(request)
    actif = _agent_autorise(user)
    return {
        "actif": actif,
        "modeles": agent_ia_modeles() if actif else [],
        "defaut": agent_ia.choisir_modele(None)["id"] if actif else AGENT_IA_MODELE,
    }


class Message(BaseModel):
    role: str      # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    module: Optional[str] = None
    page: Optional[dict] = None       # {url, titre}
    modele: Optional[str] = None


@router.post("/chat")
def chat(req: ChatRequest, request: Request):
    user = _user_agent(request)
    _check_rate_limit(user)
    # Historique borné : les 30 derniers messages, texte seul, alternance garantie.
    hist: list[dict] = []
    for m in req.messages[-30:]:
        if m.role not in ("user", "assistant") or not (m.content or "").strip():
            continue
        if hist and hist[-1]["role"] == m.role:
            hist[-1]["content"] += "\n\n" + m.content[:8000]
        else:
            hist.append({"role": m.role, "content": m.content[:8000]})
    while hist and hist[0]["role"] != "user":
        hist.pop(0)
    if not hist or hist[-1]["role"] != "user":
        raise HTTPException(400, detail="Message vide.")
    page = dict(req.page or {})
    if req.module and not page.get("titre"):
        page["titre"] = req.module
    with get_db() as conn:
        try:
            res = agent_ia.converser(conn, user, hist, page, req.modele,
                                     contexte={"app": request.app, "cookies": dict(request.cookies)})
        except agent_ia.ErreurAgent as e:
            raise HTTPException(503 if "clé" in str(e) else 502, detail=str(e))
    # La conversation n'est pas journalisée (module « ai » aveugle au contenu) :
    # seulement le fait qu'il y a eu lecture, et quels outils.
    if res["outils"]:
        log_action(user=user, action="SEARCH", module="ai",
                   objet=f"Agent IA · {len(res['outils'])} outil(s)",
                   detail={"outils": sorted(set(res["outils"])), "modele": res["modele"]}, request=request)
    return {"reply": res["reponse"], "actions": res["actions"], "modele": res["modele"]}


def _action(conn, jeton: str, user: dict):
    row = conn.execute("SELECT * FROM ai_actions WHERE jeton=?", (jeton,)).fetchone()
    if not row or row["user_email"] != (user.get("email") or ""):
        raise HTTPException(404, detail="Action introuvable.")
    return row


@router.post("/actions/{jeton}/confirmer")
async def confirmer_action(jeton: str, request: Request):
    user = _user_agent(request)
    now = datetime.now()
    with get_db() as conn:
        row = _action(conn, jeton, user)
        if row["statut"] != "proposee":
            raise HTTPException(409, detail="Action déjà traitée.")
        cree = datetime.fromisoformat(row["created_at"])
        if now - cree > timedelta(minutes=AGENT_IA_ACTION_TTL_MIN):
            conn.execute("UPDATE ai_actions SET statut='expiree', traite_at=? WHERE id=?",
                         (now.strftime("%Y-%m-%dT%H:%M:%S"), row["id"]))
            conn.commit()
            raise HTTPException(410, detail="Proposition expirée — redemander à l'agent.")
        # Passage atomique : deux clics rapides n'exécutent qu'une fois.
        cur = conn.execute("UPDATE ai_actions SET statut='en_cours' WHERE id=? AND statut='proposee'", (row["id"],))
        conn.commit()
        if cur.rowcount != 1:
            raise HTTPException(409, detail="Action déjà traitée.")
        action = dict(row)
    res = await agent_actions.executer(request, action)
    statut = "executee" if res["ok"] else "echec"
    with get_db() as conn:
        conn.execute("UPDATE ai_actions SET statut=?, resultat_json=?, traite_at=? WHERE id=?",
                     (statut, json.dumps(res, ensure_ascii=False, default=str)[:20000],
                      datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), action["id"]))
        conn.commit()
    log_action(user=user, action="VALIDATE", module="ai",
               objet=f"Agent IA · {action['libelle']}" + ("" if res["ok"] else " · échec"),
               detail={"resume": action["resume"], "chemin": action["chemin"], "statut": res.get("statut_http"),
                       "message": res.get("message")}, request=request)
    return res


@router.post("/actions/{jeton}/annuler")
def annuler_action(jeton: str, request: Request):
    user = _user_agent(request)
    with get_db() as conn:
        row = _action(conn, jeton, user)
        if row["statut"] == "proposee":
            conn.execute("UPDATE ai_actions SET statut='annulee', traite_at=? WHERE id=?",
                         (datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), row["id"]))
            conn.commit()
    return {"ok": True}

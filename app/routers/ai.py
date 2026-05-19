"""MySifa — Agent IA (Claude via Anthropic SDK)."""
from __future__ import annotations

import json
import os
import time
from typing import Any, Optional

import anthropic
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from database import get_db
from services.auth_service import get_current_user
from app.services.ai_context import (
    BRIEF_ROLES,
    build_system_prompt,
    get_tools_for_role,
    get_user_scope,
)
from app.services.ai_data import (
    build_daily_brief,
    execute_pending_action,
    fetch_context_for_role,
    tool_expe_detail,
    tool_planning_close_dossier_prepare,
    tool_planning_client_schedule,
    tool_planning_detail,
    tool_production_detail,
    tool_stock_adjust_prepare,
    tool_stock_search,
)

router = APIRouter(prefix="/api/ai", tags=["agent-ia"])

ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
MAX_TOKENS = 1024
MAX_TOOL_LOOPS = 6
RATE_LIMIT_MAX = 20
RATE_LIMIT_WINDOW_SEC = 60.0

# user_id → timestamps des requêtes (nettoyage lazy à chaque appel)
_rate_buckets: dict[Any, list[float]] = {}
# user_id → action en attente de confirmation
_pending_actions: dict[Any, dict[str, Any]] = {}

TOOLS: list[dict[str, Any]] = [
    {
        "name": "production_detail",
        "description": (
            "Détail de la production sur N jours : saisies par jour pour une machine, "
            "ou synthèse par machine si machine_nom absent."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "machine_nom": {
                    "type": "string",
                    "description": "Nom de la machine (ex. Cohésio 1). Optionnel.",
                },
                "jours": {
                    "type": "integer",
                    "description": "Nombre de jours à remonter (défaut 7, max 90).",
                },
            },
        },
    },
    {
        "name": "planning_detail",
        "description": (
            "Liste des dossiers au planning machine, filtrable par machine, client et statut. "
            "Pour les dates de passage (« quand »), préférer planning_client_schedule."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "machine_nom": {
                    "type": "string",
                    "description": "Nom de la machine. Optionnel.",
                },
                "client": {
                    "type": "string",
                    "description": "Filtrer par nom de client (fragment). Optionnel.",
                },
                "statut": {
                    "type": "string",
                    "description": "attente | en_cours | termine. Optionnel.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Nombre max de dossiers (défaut 10, max 30).",
                },
            },
        },
    },
    {
        "name": "planning_client_schedule",
        "description": (
            "Dates estimées de passage en production pour les dossiers d'un client "
            "(file d'attente, début/fin en heures ouvrées machine). À utiliser pour "
            "répondre aux questions « quand », « à quelle date », « position N »."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "client": {
                    "type": "string",
                    "description": "Nom ou fragment du client (ex. SNV).",
                },
                "machine_nom": {
                    "type": "string",
                    "description": "Limiter à une machine. Optionnel.",
                },
            },
            "required": ["client"],
        },
    },
    {
        "name": "stock_search",
        "description": "Recherche un article en stock par référence ou désignation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Référence ou fragment de désignation.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "expe_detail",
        "description": "Expéditions à venir (en attente ou validées) sur une période.",
        "input_schema": {
            "type": "object",
            "properties": {
                "jours": {
                    "type": "integer",
                    "description": "Horizon en jours à partir d'aujourd'hui (défaut 14, max 60).",
                },
            },
        },
    },
    {
        "name": "planning_close_dossier",
        "description": (
            "Demande la clôture d'un dossier planning (statut terminé). "
            "Nécessite une confirmation explicite de l'utilisateur avant exécution."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "entry_id": {
                    "type": "integer",
                    "description": "ID de l'entrée planning_entries.",
                },
            },
            "required": ["entry_id"],
        },
    },
    {
        "name": "stock_adjust",
        "description": (
            "Demande un ajustement de stock à un emplacement. "
            "Nécessite une confirmation explicite avant exécution."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "reference": {"type": "string", "description": "Référence produit."},
                "emplacement": {"type": "string", "description": "Code emplacement."},
                "nouvelle_quantite": {
                    "type": "number",
                    "description": "Quantité cible après ajustement.",
                },
                "raison": {"type": "string", "description": "Motif de l'ajustement."},
            },
            "required": ["reference", "emplacement", "nouvelle_quantite", "raison"],
        },
    },
]


class Message(BaseModel):
    role: str      # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    module: Optional[str] = None   # module actif côté client


class ChatResponse(BaseModel):
    reply: str
    status: Optional[str] = None   # "ok" | "err" | "info" | None


def _extract_confirm_payload(message: str) -> dict[str, Any] | None:
    marker = "[CONFIRM_ACTION:"
    if marker not in message:
        return None
    start = message.index(marker) + len(marker)
    end = message.rindex("]")
    return json.loads(message[start:end])


def _check_rate_limit(user: dict) -> None:
    """Max 20 requêtes / minute par utilisateur (nettoyage lazy des entrées expirées)."""
    uid = _user_key(user)
    now = time.time()
    cutoff = now - RATE_LIMIT_WINDOW_SEC

    for key in list(_rate_buckets):
        _rate_buckets[key] = [t for t in _rate_buckets[key] if t > cutoff]
        if not _rate_buckets[key]:
            del _rate_buckets[key]

    times = _rate_buckets.setdefault(uid, [])
    times[:] = [t for t in times if t > cutoff]
    if len(times) >= RATE_LIMIT_MAX:
        raise HTTPException(429, detail="Trop de requêtes.")
    times.append(now)


def _tools_for_role(role: str) -> list[dict[str, Any]]:
    allowed = set(get_tools_for_role(role))
    return [t for t in TOOLS if t["name"] in allowed]


def _user_key(user: dict) -> Any:
    uid = user.get("id")
    if uid is not None:
        return uid
    return user.get("email") or "unknown"


def _is_confirmation(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return False
    if t in ("oui", "ok", "confirme", "oui, confirme", "oui confirme"):
        return True
    return any(w in ("oui", "ok", "confirme") for w in t.replace(",", " ").split())


def _is_cancellation(text: str) -> bool:
    t = (text or "").strip().lower()
    return t in ("non", "annuler", "annule", "cancel") or t.startswith("annul")


@router.get("/brief")
def ai_brief(request: Request):
    """Résumé JSON de la journée — direction et superadmin uniquement."""
    user = get_current_user(request)
    role = user.get("role", "")
    if role not in BRIEF_ROLES:
        raise HTTPException(403, detail="Accès réservé à la direction.")

    with get_db() as conn:
        return build_daily_brief(conn)


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request):
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(503, detail="ANTHROPIC_API_KEY non configurée.")

    user = get_current_user(request)
    role = user.get("role", "")
    scope = get_user_scope(role)
    if not scope:
        raise HTTPException(403, detail="Aucun accès agent IA pour ce rôle.")

    _check_rate_limit(user)

    ukey = _user_key(user)
    last_user_msg = next(
        (m.content for m in reversed(req.messages) if m.role == "user"),
        "",
    )

    if _is_cancellation(last_user_msg):
        _pending_actions.pop(ukey, None)

    if _is_confirmation(last_user_msg):
        pending = _pending_actions.pop(ukey, None)
        if pending:
            with get_db() as conn:
                try:
                    result = execute_pending_action(conn, user, pending)
                    return JSONResponse({"reply": result, "status": "ok"})
                except Exception as e:
                    return JSONResponse(
                        {"reply": f"Erreur lors de l'exécution : {e}", "status": "err"}
                    )

    allowed_tools = _tools_for_role(role)
    client = anthropic.Anthropic(api_key=api_key)
    system = build_system_prompt(user, req.module)

    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    final_reply = ""
    final_status: str | None = None

    with get_db() as conn:
        context_data = fetch_context_for_role(conn, user)
        if context_data:
            system += f"\n\n--- Données actuelles ---\n{context_data}"

        for _ in range(MAX_TOOL_LOOPS):
            kwargs: dict[str, Any] = {
                "model": ANTHROPIC_MODEL,
                "max_tokens": MAX_TOKENS,
                "system": system,
                "messages": messages,
            }
            if allowed_tools:
                kwargs["tools"] = allowed_tools

            try:
                response = client.messages.create(**kwargs)
            except anthropic.APIError as e:
                raise HTTPException(502, detail=f"Erreur API Anthropic : {e}")

            stop = response.stop_reason
            content = response.content

            if stop == "end_turn":
                for block in content:
                    if block.type == "text":
                        final_reply += block.text
                break

            if stop != "tool_use":
                final_reply = "Je n'ai pas pu traiter cette demande."
                final_status = "err"
                break

            # Traitement tool_use
            messages.append({"role": "assistant", "content": [b.model_dump() for b in content]})
            tool_results = []
            for block in content:
                if block.type != "tool_use":
                    continue
                result, status = await _dispatch_tool(
                    conn, user, block.name, block.input, allowed_tools, ukey
                )
                final_status = status
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })
            messages.append({"role": "user", "content": tool_results})

    return JSONResponse({"reply": final_reply or "OK.", "status": final_status})


async def _dispatch_tool(
    conn,
    user: dict,
    name: str,
    inp: dict,
    allowed_tools: list[dict[str, Any]],
    user_key: Any,
) -> tuple[str, str]:
    """Dispatch vers les fonctions outils."""
    allowed_names = {t["name"] for t in allowed_tools}
    if name not in allowed_names:
        return ("Accès non autorisé à cet outil.", "err")

    scope = get_user_scope(user.get("role", ""))
    inp = inp if isinstance(inp, dict) else {}

    try:
        if name == "production_detail":
            if "production" not in scope:
                return ("Accès production non autorisé pour ce rôle.", "err")
            return (tool_production_detail(conn, inp), "ok")

        if name == "planning_detail":
            if "planning" not in scope:
                return ("Accès planning non autorisé pour ce rôle.", "err")
            return (tool_planning_detail(conn, inp), "ok")

        if name == "planning_client_schedule":
            if "planning" not in scope:
                return ("Accès planning non autorisé pour ce rôle.", "err")
            return (tool_planning_client_schedule(conn, inp), "ok")

        if name == "stock_search":
            if "stock" not in scope:
                return ("Accès stock non autorisé pour ce rôle.", "err")
            return (tool_stock_search(conn, inp), "ok")

        if name == "expe_detail":
            if "expe" not in scope:
                return ("Accès expéditions non autorisé pour ce rôle.", "err")
            return (tool_expe_detail(conn, inp), "ok")

        if name == "planning_close_dossier":
            msg = tool_planning_close_dossier_prepare(conn, inp)
            payload = _extract_confirm_payload(msg)
            if payload:
                _pending_actions[user_key] = payload
            return (msg, "info")

        if name == "stock_adjust":
            msg = tool_stock_adjust_prepare(conn, inp)
            payload = _extract_confirm_payload(msg)
            if payload:
                _pending_actions[user_key] = payload
            return (msg, "info")

        return (f"Outil inconnu : {name}.", "err")
    except Exception as e:
        return (f"Erreur lecture données : {e}", "err")

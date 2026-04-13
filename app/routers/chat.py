"""
SIFA — Chatbot v0.1

Endpoint: POST /api/chat
Widget:  /static/chatbot_widget.js

Principe:
- L'utilisateur parle en français
- Le serveur appelle un LLM (Anthropic Messages API) avec outils (tool_use)
- Les outils exécutent des actions MyProd (planning) / MyStock (stock) via DB interne

Sécurité:
- Auth obligatoire (session cookie)
- Planning: admin uniquement
- Stock: rôles stock (direction/administration/logistique)
"""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import date, datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from database import get_db
from services.auth_service import get_current_user, user_has_app_access

router = APIRouter(prefix="/api", tags=["chatbot"])

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-7-sonnet-latest")


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class ChatResponse(BaseModel):
    reply: str
    status: Optional[str] = None  # "ok" | "err" | "info" | None


TOOLS: list[dict[str, Any]] = [
    {
        "name": "planning_add",
        "description": "Ajoute une référence/dossier au planning d'une machine.",
        "input_schema": {
            "type": "object",
            "properties": {
                "machine_id": {"type": "integer", "description": "ID machine (défaut 1)"},
                "reference": {"type": "string", "description": "Référence à planifier (ex: 4521, REF-123)"},
                "duree_heures": {"type": "number", "description": "Durée estimée (2..30), défaut 8"},
                "commentaire": {"type": "string", "description": "Commentaire optionnel"},
            },
            "required": ["reference"],
        },
    },
    {
        "name": "planning_view",
        "description": "Affiche les prochaines entrées du planning d'une machine.",
        "input_schema": {
            "type": "object",
            "properties": {
                "machine_id": {"type": "integer", "description": "ID machine (défaut 1)"},
                "limit": {"type": "integer", "description": "Nombre max d'entrées (défaut 10)"},
            },
            "required": [],
        },
    },
    {
        "name": "stock_add",
        "description": "Ajoute du stock à un emplacement (entrée).",
        "input_schema": {
            "type": "object",
            "properties": {
                "reference": {"type": "string", "description": "Référence produit"},
                "designation": {"type": "string", "description": "Désignation (si produit inexistant)"},
                "emplacement": {"type": "string", "description": "Emplacement (A121..C123)"},
                "quantite": {"type": "number", "description": "Quantité (>0)"},
                "unite": {"type": "string", "description": "Unité (défaut unité)"},
                "note": {"type": "string", "description": "Note optionnelle"},
            },
            "required": ["reference", "emplacement", "quantite"],
        },
    },
    {
        "name": "stock_view",
        "description": "Consulte le stock d'une référence ou d'un emplacement.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reference": {"type": "string", "description": "Référence (optionnel)"},
                "emplacement": {"type": "string", "description": "Emplacement (optionnel)"},
                "limit": {"type": "integer", "description": "Limite (défaut 15)"},
            },
            "required": [],
        },
    },
]


def _anthropic_call(payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        ANTHROPIC_URL,
        data=data,
        method="POST",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM indisponible: {e}")


def _system_prompt() -> str:
    today = date.today().isoformat()
    now = datetime.now().strftime("%H:%M")
    return f"""Tu es l'assistant SIFA intégré dans mysifa.com.
Tu aides sur:
- Planning (MyProd): ajouter/consulter des entrées (machine, référence, durée, commentaire).
- Stock (MyStock): ajouter/consulter du stock (référence, emplacement, quantité).

Date: {today} — Heure: {now}

Règles:
- Réponds en français, concis et actionnable.
- Si une info manque (ex: emplacement, quantité), pose une question courte.
- Avant une action potentiellement destructive, demande confirmation (ici: ne supprime rien).
- N'invente pas de données.
"""


def _require_stock(user: dict) -> None:
    if not user_has_app_access(user, "stock"):
        raise HTTPException(status_code=403, detail="Accès stock réservé (direction/administration/logistique).")


def _require_admin(user: dict) -> None:
    if not user_has_app_access(user, "planning"):
        raise HTTPException(status_code=403, detail="Accès planning réservé.")


def _tool_planning_add(user: dict, inp: dict) -> tuple[str, str]:
    _require_admin(user)
    machine_id = int(inp.get("machine_id") or 1)
    reference = str(inp.get("reference") or "").strip()
    if not reference:
        return ("Il me faut une référence (ex: 4521).", "info")
    duree = float(inp.get("duree_heures") or 8)
    if duree < 2 or duree > 720:
        return ("Durée invalide (entre 2 et 720 heures).", "err")
    commentaire = (inp.get("commentaire") or "").strip()
    now = datetime.now().isoformat()
    with get_db() as conn:
        mac = conn.execute("SELECT id, nom FROM machines WHERE id=? AND actif=1", (machine_id,)).fetchone()
        if not mac:
            return (f"Machine {machine_id} introuvable.", "err")
        max_pos = conn.execute(
            "SELECT COALESCE(MAX(position),0) FROM planning_entries WHERE machine_id=?",
            (machine_id,),
        ).fetchone()[0]
        pos = int(max_pos) + 1
        conn.execute(
            """INSERT INTO planning_entries
               (machine_id, position, reference, client, description, format_l, format_h,
                dos_rvgi, duree_heures, statut, notes, created_at, updated_at, commentaire)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                machine_id,
                pos,
                reference,
                "",
                "",
                None,
                None,
                None,
                duree,
                "attente",
                "",
                now,
                now,
                commentaire,
            ),
        )
        # Invalider les plans calculés des "attente"
        conn.execute(
            "UPDATE planning_entries SET planned_start=NULL, planned_end=NULL WHERE machine_id=? AND statut='attente'",
            (machine_id,),
        )
        conn.commit()
    return (f"Ajouté au planning (machine {machine_id}) : **{reference}** — {duree:g}h.", "ok")


def _tool_planning_view(user: dict, inp: dict) -> tuple[str, str]:
    _require_admin(user)
    machine_id = int(inp.get("machine_id") or 1)
    limit = int(inp.get("limit") or 10)
    limit = max(1, min(25, limit))
    with get_db() as conn:
        mac = conn.execute("SELECT id, nom FROM machines WHERE id=? AND actif=1", (machine_id,)).fetchone()
        if not mac:
            return (f"Machine {machine_id} introuvable.", "err")
        rows = conn.execute(
            """SELECT id, position, reference, duree_heures, statut, commentaire
               FROM planning_entries
               WHERE machine_id=?
               ORDER BY position ASC
               LIMIT ?""",
            (machine_id, limit),
        ).fetchall()
    if not rows:
        return (f"Aucune entrée au planning (machine {machine_id}).", "info")
    lines = [f"📋 Planning machine {machine_id} (top {len(rows)}) :"]
    for r in rows:
        ref = r["reference"]
        st = r["statut"]
        dh = r["duree_heures"]
        lines.append(f"- #{r['position']} — **{ref}** ({dh:g}h) [{st}]")
    return ("\n".join(lines), "info")


def _ensure_produit(conn, reference: str, designation: Optional[str], unite: str) -> int:
    row = conn.execute("SELECT id FROM produits WHERE reference=?", (reference,)).fetchone()
    if row:
        return int(row["id"])
    des = (designation or reference).strip() or reference
    now = datetime.now().isoformat()
    cur = conn.execute(
        """INSERT INTO produits (reference,designation,description,unite,created_at,updated_at)
           VALUES (?,?,?,?,?,?)""",
        (reference, des, "", unite or "unité", now, now),
    )
    return int(cur.lastrowid)


def _tool_stock_add(user: dict, inp: dict) -> tuple[str, str]:
    _require_stock(user)
    reference = str(inp.get("reference") or "").strip().upper()
    emplacement = str(inp.get("emplacement") or "").strip().upper()
    try:
        quantite = float(inp.get("quantite"))
    except Exception:
        quantite = 0.0
    if not reference:
        return ("Il me faut une référence.", "info")
    if not emplacement:
        return ("Il me faut un emplacement (ex: A121).", "info")
    if quantite <= 0:
        return ("La quantité doit être positive.", "err")
    unite = (inp.get("unite") or "unité").strip() or "unité"
    note = (inp.get("note") or "").strip()
    now = datetime.now().isoformat()
    with get_db() as conn:
        produit_id = _ensure_produit(conn, reference, inp.get("designation"), unite)
        ex = conn.execute(
            "SELECT quantite FROM stock_emplacements WHERE produit_id=? AND emplacement=?",
            (produit_id, emplacement),
        ).fetchone()
        qte_avant = float(ex["quantite"]) if ex else 0.0
        qte_apres = qte_avant + quantite
        if ex:
            conn.execute(
                "UPDATE stock_emplacements SET quantite=?,updated_at=?,updated_by=? WHERE produit_id=? AND emplacement=?",
                (qte_apres, now, user.get("email", ""), produit_id, emplacement),
            )
        else:
            conn.execute(
                "INSERT INTO stock_emplacements (produit_id,emplacement,quantite,updated_at,updated_by) VALUES (?,?,?,?,?)",
                (produit_id, emplacement, qte_apres, now, user.get("email", "")),
            )
        conn.execute(
            """INSERT INTO mouvements_stock
               (produit_id,emplacement,type_mouvement,quantite,quantite_avant,quantite_apres,note,created_at,created_by)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                produit_id,
                emplacement,
                "entree",
                float(quantite),
                qte_avant,
                qte_apres,
                note,
                now,
                user.get("email", ""),
            ),
        )
        conn.commit()
    return (f"Stock mis à jour : **{reference}** @ {emplacement} (+{quantite:g} {unite}).", "ok")


def _tool_stock_view(user: dict, inp: dict) -> tuple[str, str]:
    _require_stock(user)
    reference = (inp.get("reference") or "").strip().upper()
    emplacement = (inp.get("emplacement") or "").strip().upper()
    limit = int(inp.get("limit") or 15)
    limit = max(1, min(50, limit))
    with get_db() as conn:
        if reference:
            rows = conn.execute(
                """SELECT p.reference,p.designation,p.unite,s.emplacement,s.quantite,s.updated_at
                   FROM stock_emplacements s
                   JOIN produits p ON p.id=s.produit_id
                   WHERE p.reference=? AND s.quantite>0
                   ORDER BY s.emplacement
                   LIMIT ?""",
                (reference, limit),
            ).fetchall()
        elif emplacement:
            rows = conn.execute(
                """SELECT p.reference,p.designation,p.unite,s.emplacement,s.quantite,s.updated_at
                   FROM stock_emplacements s
                   JOIN produits p ON p.id=s.produit_id
                   WHERE s.emplacement=? AND s.quantite>0
                   ORDER BY p.reference
                   LIMIT ?""",
                (emplacement, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT p.reference,p.designation,p.unite,s.emplacement,s.quantite,s.updated_at
                   FROM stock_emplacements s
                   JOIN produits p ON p.id=s.produit_id
                   WHERE s.quantite>0
                   ORDER BY s.updated_at DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()
    if not rows:
        return ("Aucun résultat.", "info")
    lines = ["📦 Stock :"]
    for r in rows:
        lines.append(f"- **{r['reference']}** — {r['emplacement']} : {r['quantite']:g} {r['unite']}")
    return ("\n".join(lines), "info")


async def execute_tool(user: dict, tool_name: str, tool_input: dict) -> tuple[str, str]:
    if tool_name == "planning_add":
        return _tool_planning_add(user, tool_input)
    if tool_name == "planning_view":
        return _tool_planning_view(user, tool_input)
    if tool_name == "stock_add":
        return _tool_stock_add(user, tool_input)
    if tool_name == "stock_view":
        return _tool_stock_view(user, tool_input)
    return (f"Outil inconnu: {tool_name}", "err")


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request):
    user = get_current_user(request)
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY non configurée")

    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    payload: dict[str, Any] = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 800,
        "system": _system_prompt(),
        "tools": TOOLS,
        "messages": messages,
    }

    final_reply = ""
    final_status: Optional[str] = None

    # Boucle tool_use
    for _ in range(5):
        data = _anthropic_call(payload)
        stop_reason = data.get("stop_reason")
        content = data.get("content", [])

        if stop_reason == "end_turn":
            for block in content:
                if block.get("type") == "text":
                    final_reply += block.get("text", "")
            break

        if stop_reason != "tool_use":
            final_reply = "Je n'ai pas pu traiter cette demande."
            final_status = "err"
            break

        # Ajouter l'assistant avec tool_use à l'historique
        messages.append({"role": "assistant", "content": content})

        tool_results = []
        for block in content:
            if block.get("type") != "tool_use":
                continue
            tool_name = block.get("name")
            tool_input = block.get("input") or {}
            tool_id = block.get("id")

            msg, status = await execute_tool(user, str(tool_name), dict(tool_input))
            final_status = status
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": msg,
                }
            )

        messages.append({"role": "user", "content": tool_results})
        payload["messages"] = messages

    return JSONResponse({"reply": final_reply or "OK.", "status": final_status})


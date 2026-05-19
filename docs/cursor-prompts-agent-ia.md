# Cursor Prompts — Agent IA MySifa

Prompts à exécuter dans l'ordre. Chacun est autonome.

---

## Contexte à copier en tête de chaque prompt

> Coller ce bloc AVANT le prompt concerné à chaque fois que tu l'envoies à Cursor.

```
Contexte général — MySifa :

MySifa est un outil de gestion de production industrielle développé pour SIFA (Loos, 59).
Il tourne sur un VPS Linux, servi via FastAPI (Python 3). Le frontend est du HTML/CSS/JS vanilla
généré en chaînes Python dans app/web/. La DB est SQLite (data/production.db).
La config centrale est config.py à la racine (source de vérité — ne jamais utiliser app/config.py).
Les imports DB se font via `from database import get_db`.

Modules actifs : MyProd (/prod), Planning (/planning), MyStock (/stock),
MyCompta (/compta), MyExpé (/expe), Planning RH (/planning-rh), Paie (/paie), Paramètres (/settings).

Rôles : superadmin, direction, administration, fabrication, logistique, comptabilite, expedition, commercial.

Design system (variables CSS obligatoires, jamais de couleurs en dur) :
--bg:#0a0e17 / --card:#111827 / --border:#1e293b / --text:#f1f5f9 / --text2:#cbd5e1
--muted:#94a3b8 / --accent:#22d3ee / --accent-bg:rgba(34,211,238,0.12)
--ok:#34d399 / --warn:#fbbf24 / --danger:#f87171
Police : 'Segoe UI', system-ui. Toasts via showToast(msg, type). Pas d'emojis fonctionnels.

Point d'attention UI : une calculette flottante (.calc-fab) est déjà positionnée en
bottom: max(24px, env(safe-area-inset-bottom,0px)) / right: max(24px, env(safe-area-inset-right,0px)) / z-index: 8000
dans app/web/html.py. Tout bouton flottant ajouté doit éviter cette position.
```

---

---

## Prompt 0 — Nettoyage du prototype existant

```
Contexte : MySifa est une app FastAPI + SQLite. Un prototype de chatbot existe mais est à supprimer entièrement avant de recommencer proprement.

Fichiers à supprimer complètement :
- app/routers/chat.py
- routers/chat.py
- app/static/chatbot_widget.js
- static/chatbot_widget.js

Modifications dans main.py (racine) :
- Retirer la ligne : from routers.chat import router as chat_router
- Retirer la ligne : app.include_router(chat_router)
- Laisser le reste du fichier intact

Vérifier aussi dans app/web/html.py s'il y a une balise <script src="/static/chatbot_widget.js"> ou une référence à /api/chat — la retirer si présente.

Ne rien créer. Ne rien modifier d'autre. Juste nettoyer.
```

---

## Prompt 1 — Backend socle

```
Contexte projet : MySifa, FastAPI + SQLite. Point d'entrée app/main.py (ou main.py racine). Config dans config.py (racine) — source de vérité. Auth via services/auth_service.py. Import DB via `from database import get_db`. SDK Anthropic à utiliser : package `anthropic` (pas urllib).

Fichiers à créer / modifier :

--- 1. requirements.txt ---
Ajouter la ligne : anthropic>=0.30.0
(Ne pas toucher aux autres dépendances)

--- 2. Créer app/services/ai_context.py ---

Ce fichier construit le contexte système envoyé à Claude.

```python
"""MySifa — Contexte et utilitaires pour l'agent IA."""
from __future__ import annotations
from datetime import datetime
import zoneinfo

PARIS = zoneinfo.ZoneInfo("Europe/Paris")

# Accès IA restreint au superadmin uniquement pour l'instant.
# Pour ouvrir à d'autres rôles plus tard, ajouter les entrées ici.
ROLE_SCOPE: dict[str, list[str]] = {
    "superadmin": ["production", "planning", "stock", "expe", "rh", "paie", "admin"],
}

def get_user_scope(role: str) -> list[str]:
    return ROLE_SCOPE.get(role, [])

def build_system_prompt(user: dict, module_actif: str | None = None) -> str:
    now = datetime.now(PARIS)
    role = user.get("role", "")
    nom = user.get("nom", "Utilisateur")
    scope = get_user_scope(role)
    date_str = now.strftime("%A %d %B %Y, %H:%M")

    scope_desc = ", ".join(scope) if scope else "aucun module"

    return f"""Tu es l'assistant intégré de MySifa, l'outil de gestion de production de SIFA.
Tu réponds uniquement en français. Sois direct, factuel, concis.

Utilisateur : {nom} — rôle : {role}
Date et heure : {date_str} (heure de Paris)
Module actif : {module_actif or "portail"}
Périmètre autorisé : {scope_desc}

Règles strictes :
- Tu ne peux accéder qu'aux données du périmètre de l'utilisateur.
- Tu ne modifies rien sans confirmation explicite de l'utilisateur (sauf les actions de lecture).
- Si une information manque pour répondre, pose une question courte.
- Les réponses sont courtes (3-6 lignes max sauf si un tableau ou une liste est demandé).
- Ne jamais inventer de données. Si tu ne sais pas, dis-le.
- Ton ton est professionnel et direct — pas de formules commerciales.
"""
```

--- 3. Créer app/routers/ai.py ---

```python
"""MySifa — Agent IA (Claude via Anthropic SDK)."""
from __future__ import annotations

import os
from typing import Any, Optional

import anthropic
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from database import get_db
from services.auth_service import get_current_user
from app.services.ai_context import build_system_prompt, get_user_scope
from app.services.ai_data import fetch_context_for_role   # créé au prompt 2

router = APIRouter(prefix="/api/ai", tags=["agent-ia"])

ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
MAX_TOKENS = 1024
MAX_TOOL_LOOPS = 6

# Outils disponibles — étendus au prompt 2
TOOLS: list[dict[str, Any]] = []


class Message(BaseModel):
    role: str      # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    module: Optional[str] = None   # module actif côté client


class ChatResponse(BaseModel):
    reply: str
    status: Optional[str] = None   # "ok" | "err" | "info" | None


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

    client = anthropic.Anthropic(api_key=api_key)
    system = build_system_prompt(user, req.module)

    # Récupérer un snapshot des données pertinentes pour enrichir le contexte
    with get_db() as conn:
        context_data = fetch_context_for_role(conn, user)

    if context_data:
        system += f"\n\n--- Données actuelles ---\n{context_data}"

    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    final_reply = ""
    final_status: str | None = None

    for _ in range(MAX_TOOL_LOOPS):
        kwargs: dict[str, Any] = {
            "model": ANTHROPIC_MODEL,
            "max_tokens": MAX_TOKENS,
            "system": system,
            "messages": messages,
        }
        if TOOLS:
            kwargs["tools"] = TOOLS

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

        # Traitement tool_use (implémenté au prompt 2)
        messages.append({"role": "assistant", "content": [b.model_dump() for b in content]})
        tool_results = []
        for block in content:
            if block.type != "tool_use":
                continue
            result, status = await _dispatch_tool(conn, user, block.name, block.input)
            final_status = status
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            })
        messages.append({"role": "user", "content": tool_results})

    return JSONResponse({"reply": final_reply or "OK.", "status": final_status})


async def _dispatch_tool(conn, user: dict, name: str, inp: dict) -> tuple[str, str]:
    """Dispatch vers les fonctions outils — complété au prompt 2."""
    return (f"Outil '{name}' non encore implémenté.", "info")
```

--- 4. Enregistrer le router dans app/main.py ---
Ajouter dans app/main.py (ou main.py selon lequel est le point d'entrée réel) :
- Import : `from app.routers.ai import router as ai_router`
- Enregistrement : `app.include_router(ai_router)`

Placer après les autres include_router existants.

Conventions MySifa à respecter :
- Imports config depuis `config` (racine), jamais `app.config`
- Ne jamais modifier DB_PATH
- Pas de SQL libre accessible depuis l'agent
```

---

## Prompt 2 — Data fetcher (lecture seule)

```
Contexte projet : MySifa, FastAPI + SQLite. Les tables principales : production_data, planning_entries, machines, produits, stock_emplacements, mouvements_stock, rh_conges, expe_departs, users. La DB est accédée via `from database import get_db` — conn = sqlite3.Connection avec row_factory = sqlite3.Row. Le fichier app/services/ai_context.py existe déjà (créé au prompt précédent).

Fichier à créer : app/services/ai_data.py

Ce fichier contient UNIQUEMENT des fonctions de lecture (SELECT). Aucun INSERT, UPDATE, DELETE.
Les fonctions reçoivent un `conn` déjà ouvert et un `user` dict.
Elles retournent des strings formatées lisibles par Claude.

```python
"""MySifa — Fonctions de lecture de données pour l'agent IA.
Lecture seule. Aucune modification de la DB.
"""
from __future__ import annotations
from datetime import date, datetime, timedelta
from app.services.ai_context import get_user_scope


def fetch_context_for_role(conn, user: dict) -> str:
    """Snapshot des données pertinentes selon le rôle — injecté dans le system prompt."""
    role = user.get("role", "")
    scope = get_user_scope(role)
    parts: list[str] = []

    if "production" in scope or "planning_read" in scope:
        parts.append(_production_today(conn))
        parts.append(_planning_status(conn))

    if "stock" in scope:
        parts.append(_stock_snapshot(conn))

    if "expe" in scope:
        parts.append(_expe_upcoming(conn))

    if "rh" in scope:
        parts.append(_rh_absences(conn))

    return "\n\n".join(p for p in parts if p)


def _production_today(conn) -> str:
    today = date.today().isoformat()
    rows = conn.execute("""
        SELECT m.nom as machine, COUNT(*) as nb_saisies,
               ROUND(SUM(p.duree_heures), 1) as total_heures
        FROM production_data p
        JOIN machines m ON m.id = p.machine_id
        WHERE date(p.date_operation) = ?
        GROUP BY m.id
        ORDER BY m.nom
    """, (today,)).fetchall()
    if not rows:
        return f"Production aujourd'hui ({today}) : aucune saisie."
    lines = [f"Production aujourd'hui ({today}) :"]
    for r in rows:
        lines.append(f"  - {r['machine']} : {r['nb_saisies']} saisies, {r['total_heures']}h")
    return "\n".join(lines)


def _planning_status(conn) -> str:
    rows = conn.execute("""
        SELECT m.nom as machine,
               SUM(CASE WHEN pe.statut = 'en_cours' THEN 1 ELSE 0 END) as en_cours,
               SUM(CASE WHEN pe.statut = 'attente' THEN 1 ELSE 0 END) as en_attente,
               SUM(CASE WHEN pe.statut = 'termine' THEN 1 ELSE 0 END) as termines
        FROM planning_entries pe
        JOIN machines m ON m.id = pe.machine_id
        GROUP BY m.id
        ORDER BY m.nom
    """).fetchall()
    if not rows:
        return "Planning : aucune entrée."
    lines = ["Planning machines :"]
    for r in rows:
        lines.append(f"  - {r['machine']} : {r['en_cours']} en cours, {r['en_attente']} en attente, {r['termines']} terminés")
    return "\n".join(lines)


def _stock_snapshot(conn) -> str:
    # Articles avec stock faible (quantité <= seuil_alerte si défini, sinon <= 5)
    rows = conn.execute("""
        SELECT p.reference, p.designation, p.unite,
               SUM(s.quantite) as total
        FROM stock_emplacements s
        JOIN produits p ON p.id = s.produit_id
        WHERE s.quantite > 0
        GROUP BY p.id
        ORDER BY total ASC
        LIMIT 5
    """).fetchall()
    if not rows:
        return "Stock : aucun article en stock."
    lines = ["Stock (5 articles les plus bas) :"]
    for r in rows:
        lines.append(f"  - {r['reference']} — {r['designation']} : {r['total']} {r['unite']}")
    return "\n".join(lines)


def _expe_upcoming(conn) -> str:
    today = date.today().isoformat()
    in_7 = (date.today() + timedelta(days=7)).isoformat()
    rows = conn.execute("""
        SELECT client, transporteur, date_enlevement, statut
        FROM expe_departs
        WHERE statut IN ('en_attente', 'valide')
          AND date(date_enlevement) BETWEEN ? AND ?
        ORDER BY date_enlevement ASC
        LIMIT 5
    """, (today, in_7)).fetchall()
    if not rows:
        return "Expéditions : aucun départ dans les 7 prochains jours."
    lines = ["Expéditions à venir (7j) :"]
    for r in rows:
        lines.append(f"  - {r['date_enlevement'][:10]} · {r['client']} · {r['transporteur']} [{r['statut']}]")
    return "\n".join(lines)


def _rh_absences(conn) -> str:
    today = date.today().isoformat()
    in_14 = (date.today() + timedelta(days=14)).isoformat()
    rows = conn.execute("""
        SELECT u.nom, c.type_conge, c.date_debut, c.date_fin, c.statut
        FROM rh_conges c
        JOIN users u ON u.id = c.user_id
        WHERE c.statut IN ('pose', 'valide')
          AND date(c.date_fin) >= ?
          AND date(c.date_debut) <= ?
        ORDER BY c.date_debut ASC
        LIMIT 8
    """, (today, in_14)).fetchall()
    if not rows:
        return "RH : aucune absence dans les 14 prochains jours."
    lines = ["Absences / congés (14j) :"]
    for r in rows:
        lines.append(f"  - {r['nom']} · {r['type_conge']} du {r['date_debut'][:10]} au {r['date_fin'][:10]} [{r['statut']}]")
    return "\n".join(lines)
```

Ensuite, dans app/routers/ai.py, mettre à jour TOOLS avec les outils de lecture ci-dessous, et compléter _dispatch_tool() :

TOOLS à ajouter :
1. `production_detail` — production d'une machine sur N jours (params: machine_nom optionnel, jours int défaut 7)
2. `planning_detail` — liste des dossiers d'une machine (params: machine_nom optionnel, statut optionnel, limit int défaut 10)
3. `stock_search` — chercher un article par référence ou désignation (params: query string)
4. `expe_detail` — expéditions sur une période (params: jours int défaut 14)

Chaque outil fait un SELECT en lecture seule. Aucun INSERT/UPDATE/DELETE.
Retourner une string lisible (pas du JSON brut).

Convention : conn dans _dispatch_tool est passé via `with get_db() as conn` dans le handler principal — ouvrir une nouvelle connexion dans _dispatch_tool si nécessaire.
```

---

## Prompt 3 — Interface chat (portail MySifa)

```
Contexte projet : MySifa, FastAPI + SQLite. Le portail est généré dans app/web/html.py (~8700 lignes). Chaque page inclut une sidebar avec .sidebar-bottom (logout, theme, version). Le design system est défini par des variables CSS : --bg, --card, --border, --text, --text2, --muted, --accent (#22d3ee), --accent-bg, --ok, --warn, --danger. Police : 'Segoe UI', system-ui. Toasts via showToast(msg, type). Pas d'emojis dans les icônes fonctionnelles.

La variable JS `window.__MYSIFA_APP__` est définie sur chaque page ('portal', 'prod', 'planning', 'stock', etc.).
L'utilisateur connecté est accessible via window.__MYSIFA_USER__ = { nom, role } (à injecter si pas encore présent).

Fichier concerné : app/web/html.py

Tâche : Intégrer le widget chat agent IA dans le portail.

--- PARTIE 1 : Injecter __MYSIFA_USER__ ---
Dans la fonction qui génère les pages du portail (chercher où __MYSIFA_APP__ est défini), ajouter juste après :
  window.__MYSIFA_USER__ = { nom: "{nom}", role: "{role}" };
En remplaçant {nom} et {role} par les valeurs de l'utilisateur connecté (variables Python injectées dans la chaîne HTML).

--- PARTIE 2 : CSS du widget chat ---
Ajouter dans le bloc <style> commun (ou dans une balise <style> dédiée en fin de <head>) :

```css
/* ── Agent IA — Widget chat ─────────────────────────────── */
#ai-chat-btn {
  position: fixed;
  bottom: max(24px, env(safe-area-inset-bottom, 0px));
  right: max(84px, calc(env(safe-area-inset-right, 0px) + 84px));
  /* Décalé à gauche de la calculette (.calc-fab est à right:24px, width:52px + 8px gap = 84px) */
  z-index: 8001;
  width: 48px; height: 48px; border-radius: 50%;
  background: var(--accent); border: none; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4px 16px rgba(34,211,238,0.35);
  transition: transform .18s, box-shadow .18s;
}
#ai-chat-btn:hover { transform: scale(1.08); box-shadow: 0 6px 24px rgba(34,211,238,0.5); }
#ai-chat-btn svg { display: block; color: var(--bg); }

#ai-chat-panel {
  position: fixed; bottom: 84px; right: 84px; z-index: 8002;
  width: 360px; height: 500px;
  background: var(--card); border: 1px solid var(--border); border-radius: 14px;
  box-shadow: 0 12px 48px rgba(0,0,0,0.5);
  display: flex; flex-direction: column;
  transform-origin: bottom right;
  transform: scale(0.9) translateY(10px); opacity: 0; pointer-events: none;
  transition: transform .2s cubic-bezier(.34,1.56,.64,1), opacity .15s;
  overflow: hidden;
}
#ai-chat-panel.open { transform: scale(1) translateY(0); opacity: 1; pointer-events: all; }

#ai-chat-header {
  padding: 12px 16px; background: var(--card);
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; gap: 10px; flex-shrink: 0;
}
#ai-chat-header .ai-dot {
  width: 8px; height: 8px; border-radius: 50%; background: var(--accent);
  box-shadow: 0 0 6px var(--accent); animation: ai-pulse 2s infinite;
}
@keyframes ai-pulse { 0%,100%{opacity:1} 50%{opacity:.3} }
#ai-chat-header .ai-title { flex:1; font-size:13px; font-weight:700; color:var(--text); }
#ai-chat-header .ai-sub { font-size:10px; color:var(--muted); display:block; font-weight:400; }
#ai-chat-close {
  background:none; border:none; cursor:pointer; color:var(--muted);
  padding:4px; border-radius:6px; display:flex; align-items:center; transition:color .15s;
}
#ai-chat-close:hover { color:var(--text); }

#ai-messages {
  flex:1; overflow-y:auto; padding:14px; display:flex; flex-direction:column;
  gap:8px; scrollbar-width:thin; scrollbar-color:var(--border) transparent;
}
.ai-msg { display:flex; flex-direction:column; max-width:86%; }
.ai-msg.bot  { align-self:flex-start; }
.ai-msg.user { align-self:flex-end; }
.ai-label { font-size:10px; color:var(--muted); margin-bottom:3px; }
.ai-msg.user .ai-label { text-align:right; }
.ai-bubble {
  padding:8px 12px; border-radius:10px; font-size:13px;
  line-height:1.5; word-break:break-word;
}
.ai-msg.bot  .ai-bubble { background:var(--bg); border:1px solid var(--border); color:var(--text); border-bottom-left-radius:3px; }
.ai-msg.user .ai-bubble { background:var(--accent); color:var(--bg); font-weight:600; border-bottom-right-radius:3px; }
.ai-status { display:inline-block; font-size:10px; padding:2px 7px; border-radius:20px; margin-top:4px; font-weight:600; }
.ai-status.ok   { background:rgba(52,211,153,.15); color:var(--ok);    border:1px solid var(--ok); }
.ai-status.err  { background:rgba(248,113,113,.15); color:var(--danger);border:1px solid var(--danger); }
.ai-status.info { background:var(--accent-bg);      color:var(--accent);border:1px solid var(--accent); }

#ai-typing {
  display:none; align-self:flex-start;
  padding:8px 12px; background:var(--bg); border:1px solid var(--border);
  border-radius:10px; border-bottom-left-radius:3px;
  gap:4px; align-items:center;
}
#ai-typing.visible { display:flex; }
.ai-dot-t { width:5px; height:5px; border-radius:50%; background:var(--muted); animation:ai-bounce 1.2s infinite; }
.ai-dot-t:nth-child(2){animation-delay:.2s} .ai-dot-t:nth-child(3){animation-delay:.4s}
@keyframes ai-bounce{0%,60%,100%{transform:translateY(0)}30%{transform:translateY(-4px)}}

#ai-input-area {
  padding:10px 12px; border-top:1px solid var(--border);
  display:flex; gap:8px; align-items:flex-end; flex-shrink:0; background:var(--card);
}
#ai-input {
  flex:1; background:var(--bg); border:1px solid var(--border); border-radius:8px;
  color:var(--text); font-size:13px; font-family:inherit; padding:8px 12px;
  resize:none; max-height:80px; min-height:36px; outline:none; line-height:1.4;
  transition:border-color .15s;
}
#ai-input:focus { border-color:var(--accent); box-shadow:0 0 0 3px rgba(34,211,238,.1); }
#ai-send {
  width:36px; height:36px; border-radius:8px; background:var(--accent);
  border:none; cursor:pointer; display:flex; align-items:center; justify-content:center;
  flex-shrink:0; transition:filter .15s;
}
#ai-send:hover { filter:brightness(1.1); }
#ai-send:disabled { opacity:.4; cursor:not-allowed; }
#ai-send svg { color:var(--bg); }

@media (max-width:640px) {
  /* Sur mobile, les deux boutons s'empilent verticalement */
  #ai-chat-btn  { right: max(24px, env(safe-area-inset-right, 0px)); bottom: 84px; }
  #ai-chat-panel { width: calc(100vw - 24px); right: 12px; bottom: 140px; }
}
```

--- PARTIE 3 : HTML du widget ---
Avant la fermeture de </body> dans le layout commun, injecter :

```html
<!-- Agent IA -->
<div id="ai-chat-root">
  <button id="ai-chat-btn" aria-label="Assistant IA" title="Assistant MySifa">
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
    </svg>
  </button>
  <div id="ai-chat-panel" role="dialog" aria-label="Assistant MySifa">
    <div id="ai-chat-header">
      <span class="ai-dot"></span>
      <div class="ai-title">Assistant MySifa<span class="ai-sub">Posez vos questions sur la production, le stock…</span></div>
      <button id="ai-chat-close" aria-label="Fermer">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="1" y1="1" x2="13" y2="13"/><line x1="13" y1="1" x2="1" y2="13"/></svg>
      </button>
    </div>
    <div id="ai-messages"></div>
    <div id="ai-typing"><span class="ai-dot-t"></span><span class="ai-dot-t"></span><span class="ai-dot-t"></span></div>
    <div id="ai-input-area">
      <textarea id="ai-input" placeholder="Votre question…" rows="1" aria-label="Message"></textarea>
      <button id="ai-send" aria-label="Envoyer">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M22 2L11 13"/><path d="M22 2L15 22l-4-9-9-4 20-7z"/></svg>
      </button>
    </div>
  </div>
</div>
```

--- PARTIE 4 : JS du widget ---
Ajouter après le HTML ci-dessus, dans une balise <script> :

```javascript
(function(){
  'use strict';
  // Accès restreint au superadmin uniquement
  const user = window.__MYSIFA_USER__ || {};
  if(user.role !== 'superadmin') return;

  // Masquer sur login et portail d'accueil
  const app = window.__MYSIFA_APP__;
  if(app === 'portal' || app === 'login' || !app) return;

  const btn    = document.getElementById('ai-chat-btn');
  const panel  = document.getElementById('ai-chat-panel');
  const close  = document.getElementById('ai-chat-close');
  const msgs   = document.getElementById('ai-messages');
  const input  = document.getElementById('ai-input');
  const send   = document.getElementById('ai-send');
  const typing = document.getElementById('ai-typing');

  let open = false, loading = false;
  const history = [];

  // Message d'accueil personnalisé selon rôle
  const user = window.__MYSIFA_USER__ || {};
  const greetings = {
    fabrication:   'Production du jour, état des machines — posez vos questions.',
    logistique:    'Stock, emplacements, expéditions à venir — posez vos questions.',
    direction:     'KPIs, synthèse production, planning, stock — posez vos questions.',
    administration:'Congés, paie, expéditions — posez vos questions.',
  };
  const greeting = greetings[user.role] || 'Posez vos questions sur MySifa.';
  addBot(greeting, null);

  btn.addEventListener('click', toggle);
  close.addEventListener('click', toggle);
  document.addEventListener('click', e=>{
    if(open && !panel.contains(e.target) && e.target !== btn){ open=false; panel.classList.remove('open'); }
  });
  input.addEventListener('keydown', e=>{ if(e.key==='Enter'&&!e.shiftKey){ e.preventDefault(); handleSend(); } });
  input.addEventListener('input', ()=>{ input.style.height='auto'; input.style.height=Math.min(input.scrollHeight,80)+'px'; });
  send.addEventListener('click', handleSend);

  function toggle(){ open=!open; panel.classList.toggle('open',open); if(open) setTimeout(()=>input.focus(),200); }

  function fmt(t){ return String(t||'').replace(/\*\*(.*?)\*\*/g,'<strong>$1</strong>').replace(/\n/g,'<br>'); }
  function scrollEnd(){ setTimeout(()=>{ msgs.scrollTop=msgs.scrollHeight; },30); }

  function addBot(text, status){
    const w=document.createElement('div'); w.className='ai-msg bot';
    w.innerHTML=`<div class="ai-label">MySifa</div><div class="ai-bubble">${fmt(text)}</div>`;
    if(status){ const s=document.createElement('span'); s.className=`ai-status ${status}`; s.textContent=status==='ok'?'Action effectuée':status==='err'?'Erreur':'Info'; w.appendChild(s); }
    msgs.appendChild(w); scrollEnd();
  }
  function addUser(text){
    const w=document.createElement('div'); w.className='ai-msg user';
    w.innerHTML=`<div class="ai-label">Vous</div><div class="ai-bubble">${String(text).replace(/</g,'&lt;')}</div>`;
    msgs.appendChild(w); scrollEnd();
  }
  function setLoading(v){ loading=v; send.disabled=v; input.disabled=v; typing.classList.toggle('visible',v); if(v)scrollEnd(); }

  async function handleSend(){
    const text=input.value.trim(); if(!text||loading) return;
    addUser(text);
    history.push({role:'user',content:text});
    input.value=''; input.style.height='auto';
    setLoading(true);
    try{
      const res=await fetch('/api/ai/chat',{
        method:'POST', credentials:'include',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({ messages:history, module: app||null })
      });
      const data=await res.json().catch(()=>({}));
      if(!res.ok) throw new Error(data.detail||`HTTP ${res.status}`);
      addBot(data.reply||'OK.', data.status||null);
      history.push({role:'assistant',content:data.reply||''});
    } catch(err){
      addBot('Erreur de connexion. Réessayez dans un instant.','err');
    } finally { setLoading(false); }
  }
})();
```

Conventions :
- Aucun emoji dans les labels ou titres
- Pas d'alert() — showToast() si besoin de toasts hors widget
- Tester thème light (body.light) : les variables CSS doivent s'adapter automatiquement
- Le widget ne doit pas apparaître sur la page login (/) ni sur le portail d'accueil
```

---

## Prompt 4 — Droits par rôle (filtrage serveur)

```
Contexte : MySifa, FastAPI. Les fichiers app/routers/ai.py et app/services/ai_context.py existent (créés aux prompts précédents). ROLE_SCOPE dans ai_context.py définit le périmètre par rôle.

Fichiers concernés :
- app/routers/ai.py
- app/services/ai_context.py

Tâche : Renforcer le filtrage par rôle — le contexte et les outils disponibles varient selon le rôle de l'utilisateur connecté.

1. Dans app/services/ai_context.py, ajouter la fonction `get_tools_for_role(role: str) -> list[str]` :
   - superadmin → toutes les fonctions (seul rôle autorisé pour l'instant)
   - tous les autres rôles → [] (accès refusé)
   
   Note : cette fonction est le point central pour étendre l'accès plus tard — il suffira d'ajouter des entrées ici.

2. Dans app/routers/ai.py, endpoint POST /api/ai/chat :
   - Avant d'appeler Claude, filtrer TOOLS pour ne garder que ceux autorisés via get_tools_for_role(role)
   - Si aucun outil autorisé → appel Claude sans outils (lecture seule du contexte injecté)
   - Dans _dispatch_tool(), vérifier que le tool appelé est dans la liste autorisée pour le rôle avant d'exécuter — retourner une erreur "Accès non autorisé à cet outil." sinon

3. Dans build_system_prompt(), adapter le message selon le rôle :
   - Ajouter une phrase explicite : "Tu ne peux accéder qu'aux données suivantes : [liste scope]."
   - Pour fabrication : préciser que l'accès est limité à leurs propres saisies et leur machine
   - Pour direction : préciser qu'ils voient tous les modules

4. Rate limiting basique dans le endpoint /api/ai/chat :
   - Stocker en mémoire (dict global) le nombre de requêtes par user_id dans la dernière minute
   - Si > 20 requêtes/minute → retourner HTTPException 429 "Trop de requêtes."
   - Nettoyer les entrées > 1 min à chaque appel (pas de cron, nettoyage lazy)
```

---

## Prompt 5 — Capacités avancées

```
Contexte : MySifa, FastAPI + SQLite. app/routers/ai.py et app/services/ai_data.py existent. Le portail a le widget chat intégré.

Fichiers concernés :
- app/services/ai_data.py (nouvelles fonctions)
- app/routers/ai.py (nouvelle route)

Tâche A — Détection d'anomalies :
Dans app/services/ai_data.py, créer fetch_anomalies(conn) → str :
- Dossiers en_cours depuis plus de 48h sans nouvelle saisie de production
- Machines sans aucune saisie aujourd'hui (jours ouvrés seulement — exclure sam/dim)
- Articles en rupture de stock (quantité = 0) ayant eu un mouvement dans les 30 derniers jours
- Expéditions en_attente dont date_enlevement est dépassée
Retourner une string formatée listant les anomalies trouvées, ou une string vide s'il n'y en a pas.

Injecter fetch_anomalies() dans fetch_context_for_role() pour les rôles direction et superadmin.

Tâche B — Actions avec confirmation :
Ajouter 2 nouveaux outils dans TOOLS (app/routers/ai.py) pour les rôles direction/superadmin/administration :

Outil `planning_close_dossier` :
- Paramètre : entry_id (int)
- Comportement : NE PAS exécuter directement. Retourner un message de confirmation avec les détails du dossier : "Confirmes-tu la clôture du dossier #{reference} — {client} ?"
- L'action réelle (UPDATE statut='termine') n'est déclenchée que si le message suivant de l'utilisateur contient explicitement "oui", "confirme" ou "ok"
- Implémenter via un flag S.pendingAction en JS côté widget : si le bot retourne un message contenant "[CONFIRM_ACTION:{json}]", afficher deux boutons "Confirmer" / "Annuler" sous le message. "Confirmer" envoie un message "oui, confirme" en automatique.

Outil `stock_adjust` :
- Paramètres : reference (str), emplacement (str), nouvelle_quantite (float), raison (str)
- Même pattern de confirmation avant d'exécuter le UPDATE

Tâche C — Route GET /api/ai/brief :
Créer une route GET /api/ai/brief qui retourne un résumé JSON de la journée :
{
  "date": "2026-05-19",
  "production": "...",  # résumé _production_today()
  "anomalies": "...",   # fetch_anomalies()
  "expe": "...",        # _expe_upcoming() sur 48h
  "rh": "..."           # absences du jour
}
Accessible uniquement aux rôles direction et superadmin.
Utile pour un futur scheduled task "brief quotidien".
```

---

## Ordre d'exécution

1. Prompt 0 — Nettoyage *(5 min)*
2. Prompt 1 — Backend socle *(tester /api/ai/chat en curl avant de continuer)*
3. Prompt 2 — Data fetcher *(tester que le contexte injecté est cohérent)*
4. Prompt 3 — Frontend widget *(tester visuellement sur chaque module)*
5. Prompt 4 — Droits par rôle *(tester avec différents comptes)*
6. Prompt 5 — Capacités avancées *(une fois les phases 1-4 stables)*

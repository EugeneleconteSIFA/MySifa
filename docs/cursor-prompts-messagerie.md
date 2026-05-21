# Cursor Prompts — Messagerie MySifa

Prompts à exécuter dans l'ordre. Chacun est autonome et testable.

L'équipe SIFA n'utilise pas d'outil de messagerie dédié. MySifa doit couvrir
les trois cas d'usage suivants :

1. **Commentaires contextuels** — fils de discussion attachés à un dossier planning
   ou une saisie fabrication (Prompts 1–5).
2. **Messages directs** — conversations privées entre deux collègues (Prompt 6).
3. **Canaux d'équipe** — espaces de discussion par rôle ou thème (#général,
   #fabrication, #logistique…) (Prompt 6).

Les Prompts 1–5 peuvent être exécutés indépendamment des Prompts 6–7.
Le Prompt 6 pose les fondations DB et API du chat ; le Prompt 7 est l'interface.

---

## Contexte à copier en tête de chaque prompt

> Coller ce bloc AVANT le prompt concerné à chaque fois.

```
Contexte général — MySifa :

MySifa est un outil de gestion de production industrielle pour SIFA (Loos, 59).
FastAPI (Python 3) + SQLite. Frontend : HTML/CSS/JS vanilla généré en chaînes Python dans app/web/.
Config centrale : config.py à la racine (source de vérité — jamais app/config.py).
Import DB : `from database import get_db` (conn = sqlite3.Connection avec row_factory = sqlite3.Row).
Auth : services/auth_service.py → get_current_user(request) retourne dict {id, nom, email, role, ...}.

Design system (variables CSS — jamais de couleurs en dur) :
--bg:#0a0e17 / --card:#111827 / --border:#1e293b / --text:#f1f5f9 / --text2:#cbd5e1
--muted:#94a3b8 / --accent:#22d3ee / --accent-bg:rgba(34,211,238,0.12)
--ok:#34d399 / --warn:#fbbf24 / --danger:#f87171
Police : 'Segoe UI', system-ui. Toasts via showToast(msg, type). Pas d'emojis fonctionnels.
Bouton flottant existant (.calc-fab) : bottom:24px / right:24px / z-index:8000.

Rôles : superadmin, direction, administration, fabrication, logistique, comptabilite, expedition, commercial.

Les shims frontend/ et routers/ à la racine pointent vers app/. Ne pas y ajouter de logique.
Tout nouveau router → app/routers/ + enregistrement dans main.py.
Toute nouvelle page → app/web/ + enregistrement dans main.py.
```

---

---

## Prompt 1 — Migration DB + backend API

```
Contexte projet : MySifa, FastAPI + SQLite.

Tâche : Créer les tables DB et le router API pour la messagerie contextuelle.

--- PARTIE 1 : Migration DB dans app/core/database.py ---

Dans la fonction _migrate() (qui contient les blocs
`if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=N LIMIT 1").fetchone():`),
ajouter une nouvelle migration à la suite du dernier numéro de version existant.

Trouver le numéro de la dernière migration (ex: version=14) et ajouter juste après :

```python
if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=15 LIMIT 1").fetchone():
    conn.execute("""
        CREATE TABLE IF NOT EXISTS contextual_messages (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            module        TEXT    NOT NULL,
            object_type   TEXT    NOT NULL,
            object_id     TEXT    NOT NULL,
            from_user_id  INTEGER NOT NULL,
            from_nom      TEXT    NOT NULL,
            body          TEXT    NOT NULL,
            to_user_id    INTEGER DEFAULT NULL,
            is_alert      INTEGER NOT NULL DEFAULT 0,
            created_at    TEXT    NOT NULL,
            deleted_at    TEXT    DEFAULT NULL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_ctxmsg_ctx
        ON contextual_messages(module, object_type, object_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_ctxmsg_to
        ON contextual_messages(to_user_id, created_at)
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS contextual_message_reads (
            message_id INTEGER NOT NULL,
            user_id    INTEGER NOT NULL,
            read_at    TEXT    NOT NULL,
            PRIMARY KEY (message_id, user_id)
        )
    """)
    conn.execute(
        "INSERT OR IGNORE INTO schema_migrations (version, name, applied_at) VALUES (?,?,?)",
        (15, "contextual_messages", datetime.utcnow().isoformat())
    )
    conn.commit()
```

Adapter le numéro 15 au prochain numéro disponible réel si besoin.
Ne pas modifier les migrations existantes. Ne pas toucher à DB_PATH.

--- PARTIE 2 : Créer app/routers/messaging.py ---

```python
"""MySifa — Messagerie contextuelle.

Fil de commentaires attaché à n'importe quel objet métier (dossier planning,
saisie fabrication, etc.) + alertes ciblées utilisateur.

Routes : /api/messaging/*
Accès  : tout utilisateur authentifié (droits filtrés par module).
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from database import get_db
from services.auth_service import get_current_user

router = APIRouter(prefix="/api/messaging", tags=["messaging"])

_PARIS = ZoneInfo("Europe/Paris")
_MAX_BODY = 2000
_MODULES_ALLOWED = frozenset({"planning", "fabrication", "expe", "stock", "rh", "global"})
_OBJECT_TYPES_ALLOWED = frozenset({
    "planning_entry", "production_dossier", "expe_depart",
    "stock_article", "rh_conge", "alert", "free"
})


def _now_iso() -> str:
    return datetime.now(_PARIS).replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%S")


def _require_auth(request: Request) -> dict:
    return get_current_user(request)


# ─── Thread (fil de commentaires) ────────────────────────────────────────────

@router.get("/thread")
def get_thread(
    request: Request,
    module: str,
    object_type: str,
    object_id: str,
):
    """Retourne les messages d'un fil (non supprimés), du plus ancien au plus récent."""
    user = _require_auth(request)
    if module not in _MODULES_ALLOWED:
        raise HTTPException(400, f"Module inconnu : {module}")

    with get_db() as conn:
        rows = conn.execute(
            """SELECT cm.id, cm.from_user_id, cm.from_nom, cm.body,
                      cm.to_user_id, cm.is_alert, cm.created_at,
                      (SELECT 1 FROM contextual_message_reads r
                       WHERE r.message_id = cm.id AND r.user_id = ? LIMIT 1) as is_read
               FROM contextual_messages cm
               WHERE cm.module = ? AND cm.object_type = ? AND cm.object_id = ?
                 AND cm.deleted_at IS NULL
               ORDER BY cm.created_at ASC
               LIMIT 200""",
            (user["id"], module, object_type, str(object_id)),
        ).fetchall()

        # Marquer tous ces messages comme lus pour l'utilisateur courant
        now = _now_iso()
        for row in rows:
            if not row["is_read"]:
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO contextual_message_reads (message_id, user_id, read_at)"
                        " VALUES (?,?,?)",
                        (row["id"], user["id"], now),
                    )
                except Exception:
                    pass
        conn.commit()

    return [
        {
            "id": r["id"],
            "from_user_id": r["from_user_id"],
            "from_nom": r["from_nom"],
            "body": r["body"],
            "to_user_id": r["to_user_id"],
            "is_alert": bool(r["is_alert"]),
            "created_at": r["created_at"],
            "is_mine": r["from_user_id"] == user["id"],
        }
        for r in rows
    ]


@router.post("/thread")
async def post_message(request: Request):
    """Créer un message dans un fil. Optionnel : to_user_id pour alerte ciblée."""
    user = _require_auth(request)
    body_data = await request.json()

    module      = (body_data.get("module") or "").strip()
    object_type = (body_data.get("object_type") or "").strip()
    object_id   = str(body_data.get("object_id") or "").strip()
    body_text   = (body_data.get("body") or "").strip()
    to_user_id  = body_data.get("to_user_id")  # None = fil partagé
    is_alert    = int(bool(body_data.get("is_alert", False)))

    if module not in _MODULES_ALLOWED:
        raise HTTPException(400, f"Module inconnu : {module}")
    if not object_id:
        raise HTTPException(400, "object_id requis")
    if not body_text:
        raise HTTPException(400, "Message vide")
    if len(body_text) > _MAX_BODY:
        raise HTTPException(400, f"Message trop long (max {_MAX_BODY} caractères)")

    # Valider to_user_id si fourni
    if to_user_id is not None:
        try:
            to_user_id = int(to_user_id)
        except (TypeError, ValueError):
            raise HTTPException(400, "to_user_id invalide")

    now = _now_iso()
    with get_db() as conn:
        # Vérifier que l'utilisateur cible existe si fourni
        if to_user_id is not None:
            target = conn.execute(
                "SELECT id FROM users WHERE id = ? LIMIT 1", (to_user_id,)
            ).fetchone()
            if not target:
                raise HTTPException(404, "Utilisateur cible introuvable")

        cur = conn.execute(
            """INSERT INTO contextual_messages
               (module, object_type, object_id, from_user_id, from_nom,
                body, to_user_id, is_alert, created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                module, object_type, object_id,
                user["id"], user.get("nom") or user.get("email", ""),
                body_text, to_user_id, is_alert, now,
            ),
        )
        msg_id = cur.lastrowid
        # L'auteur a implicitement lu son propre message
        conn.execute(
            "INSERT OR IGNORE INTO contextual_message_reads (message_id, user_id, read_at)"
            " VALUES (?,?,?)",
            (msg_id, user["id"], now),
        )
        conn.commit()

    return {"id": msg_id, "created_at": now}


@router.delete("/{msg_id}")
def delete_message(msg_id: int, request: Request):
    """Soft-delete d'un message (auteur ou admin uniquement)."""
    user = _require_auth(request)
    role = user.get("role", "")
    is_admin = role in {"superadmin", "direction", "administration"}

    with get_db() as conn:
        row = conn.execute(
            "SELECT id, from_user_id, deleted_at FROM contextual_messages WHERE id = ? LIMIT 1",
            (msg_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Message introuvable")
        if row["deleted_at"] is not None:
            raise HTTPException(410, "Message déjà supprimé")
        if not is_admin and row["from_user_id"] != user["id"]:
            raise HTTPException(403, "Vous ne pouvez supprimer que vos propres messages")

        conn.execute(
            "UPDATE contextual_messages SET deleted_at = ? WHERE id = ?",
            (_now_iso(), msg_id),
        )
        conn.commit()

    return {"deleted": True}


# ─── Boîte de réception (alertes + non-lus) ──────────────────────────────────

@router.get("/inbox")
def inbox(request: Request):
    """Messages non lus adressés à l'utilisateur courant (alertes ciblées)."""
    user = _require_auth(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT cm.id, cm.module, cm.object_type, cm.object_id,
                      cm.from_nom, cm.body, cm.is_alert, cm.created_at
               FROM contextual_messages cm
               WHERE cm.to_user_id = ?
                 AND cm.deleted_at IS NULL
                 AND NOT EXISTS (
                     SELECT 1 FROM contextual_message_reads r
                     WHERE r.message_id = cm.id AND r.user_id = ?
                 )
               ORDER BY cm.created_at DESC
               LIMIT 50""",
            (user["id"], user["id"]),
        ).fetchall()

    return [dict(r) for r in rows]


@router.post("/inbox/read")
async def mark_inbox_read(request: Request):
    """Marquer une liste de message_ids comme lus."""
    user = _require_auth(request)
    body_data = await request.json()
    ids = body_data.get("ids") or []
    if not isinstance(ids, list):
        raise HTTPException(400, "ids doit être une liste")
    ids = [int(i) for i in ids if str(i).isdigit()]
    if not ids:
        return {"marked": 0}

    now = _now_iso()
    with get_db() as conn:
        for mid in ids:
            conn.execute(
                "INSERT OR IGNORE INTO contextual_message_reads (message_id, user_id, read_at)"
                " VALUES (?,?,?)",
                (mid, user["id"], now),
            )
        conn.commit()

    return {"marked": len(ids)}


# ─── Badge counts (sidebar) ──────────────────────────────────────────────────

@router.get("/badge")
def badge_counts(request: Request):
    """
    Retourne le nombre de messages non lus par module pour l'utilisateur courant.
    Utilisé pour les badges dans la sidebar.
    Inclut : messages de fils partagés (to_user_id IS NULL) + alertes ciblées.
    """
    user = _require_auth(request)
    uid = user["id"]

    with get_db() as conn:
        # Alertes ciblées non lues (inbox)
        inbox_count = conn.execute(
            """SELECT COUNT(*) as c FROM contextual_messages
               WHERE to_user_id = ? AND deleted_at IS NULL
                 AND NOT EXISTS (
                     SELECT 1 FROM contextual_message_reads r
                     WHERE r.message_id = contextual_messages.id AND r.user_id = ?
                 )""",
            (uid, uid),
        ).fetchone()["c"]

        # Compte par module (messages de fils, hors messages de l'utilisateur lui-même)
        rows = conn.execute(
            """SELECT module, COUNT(*) as c
               FROM contextual_messages
               WHERE deleted_at IS NULL
                 AND from_user_id != ?
                 AND to_user_id IS NULL
                 AND NOT EXISTS (
                     SELECT 1 FROM contextual_message_reads r
                     WHERE r.message_id = contextual_messages.id AND r.user_id = ?
                 )
               GROUP BY module""",
            (uid, uid),
        ).fetchall()

    per_module = {r["module"]: r["c"] for r in rows}
    per_module["inbox"] = inbox_count

    return per_module
```

--- PARTIE 3 : Enregistrer dans main.py ---

Dans main.py (racine), ajouter :

Import :
    from app.routers.messaging import router as messaging_router

Enregistrement (après les autres include_router) :
    app.include_router(messaging_router)

--- Vérification ---
Lancer le serveur et tester :
  curl -b "sifa_token=..." http://localhost:8000/api/messaging/badge
  → Doit retourner {"inbox": 0}
```

---

## Prompt 2 — Composant JS thread réutilisable

```
Contexte projet : MySifa. Le router /api/messaging/* est opérationnel (créé au prompt 1).
Design system : variables CSS --bg, --card, --border, --text, --text2, --muted, --accent, --ok, --warn, --danger.
Police : 'Segoe UI', system-ui. Helpers disponibles dans les pages : escHtml(s), showToast(msg, type).

Tâche : Créer le composant JS thread réutilisable qui s'injecte dans n'importe quelle page.

Créer le fichier static/messaging_thread.js :

```javascript
/**
 * MySifa — Composant fil de discussion contextuel.
 * Usage :
 *   const thread = initMsgThread(containerId, {
 *     module: 'planning',
 *     objectType: 'planning_entry',
 *     objectId: '42',
 *     currentUser: { id: 1, nom: 'Jean Dupont' },
 *     canDelete: true,   // admin ou auteur — géré aussi côté API
 *     compact: false,    // true = version réduite sans label "Fil de discussion"
 *   });
 *   thread.destroy(); // stopper le polling
 */

(function (global) {
  'use strict';

  function escHtmlLocal(s) {
    return String(s || '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function fmtTime(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    const now = new Date();
    const isToday =
      d.getDate() === now.getDate() &&
      d.getMonth() === now.getMonth() &&
      d.getFullYear() === now.getFullYear();
    if (isToday) {
      return d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    }
    return d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' }) +
      ' ' + d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  }

  function renderMessages(container, messages, currentUserId) {
    const list = container.querySelector('.msg-thread-list');
    if (!list) return;

    if (messages.length === 0) {
      list.innerHTML =
        '<div class="msg-thread-empty">Aucun commentaire pour l\'instant.</div>';
      return;
    }

    list.innerHTML = messages.map(function (m) {
      const isMine = m.from_user_id === currentUserId || m.is_mine;
      const alertBadge = m.is_alert
        ? '<span class="msg-alert-badge">Alerte</span>'
        : '';
      return (
        '<div class="msg-bubble-wrap ' + (isMine ? 'mine' : 'theirs') + '" data-id="' + m.id + '">' +
          '<div class="msg-meta">' +
            escHtmlLocal(m.from_nom) + ' · ' + fmtTime(m.created_at) + alertBadge +
          '</div>' +
          '<div class="msg-bubble">' + escHtmlLocal(m.body) + '</div>' +
          (isMine || (window.__MYSIFA_ROLE__ &&
            ['superadmin','direction','administration'].includes(window.__MYSIFA_ROLE__))
            ? '<button class="msg-del-btn" data-id="' + m.id + '" title="Supprimer">' +
                '<svg width="10" height="10" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="1" y1="1" x2="13" y2="13"/><line x1="13" y1="1" x2="1" y2="13"/></svg>' +
              '</button>'
            : '') +
        '</div>'
      );
    }).join('');

    // Scroll to bottom
    list.scrollTop = list.scrollHeight;

    // Bind delete buttons
    list.querySelectorAll('.msg-del-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        const mid = btn.getAttribute('data-id');
        if (!confirm('Supprimer ce message ?')) return;
        fetch('/api/messaging/' + mid, {
          method: 'DELETE',
          credentials: 'include',
        }).then(function (r) {
          if (r.ok) {
            const wrap = btn.closest('.msg-bubble-wrap');
            if (wrap) wrap.remove();
            if (list.querySelectorAll('.msg-bubble-wrap').length === 0) {
              list.innerHTML =
                '<div class="msg-thread-empty">Aucun commentaire pour l\'instant.</div>';
            }
          } else {
            r.json().then(function (j) {
              if (window.showToast) showToast(j.detail || 'Erreur suppression', 'danger');
            });
          }
        });
      });
    });
  }

  function initMsgThread(containerId, opts) {
    const container = document.getElementById(containerId);
    if (!container) return { destroy: function () {} };

    const module     = opts.module;
    const objectType = opts.objectType;
    const objectId   = String(opts.objectId);
    const currentUser = opts.currentUser || {};
    const compact    = opts.compact || false;

    // ── CSS inline (injecté une seule fois) ──
    if (!document.getElementById('msg-thread-style')) {
      const style = document.createElement('style');
      style.id = 'msg-thread-style';
      style.textContent = `
        .msg-thread-root { display:flex; flex-direction:column; gap:0; }
        .msg-thread-header {
          font-size:11px; font-weight:700; color:var(--text2);
          text-transform:uppercase; letter-spacing:.5px;
          padding:0 0 8px 0; border-bottom:1px solid var(--border);
          margin-bottom:10px; display:flex; align-items:center; gap:8px;
        }
        .msg-thread-count {
          font-size:11px; background:var(--accent-bg); color:var(--accent);
          padding:2px 7px; border-radius:20px; font-weight:700;
        }
        .msg-thread-list {
          display:flex; flex-direction:column; gap:8px;
          max-height:240px; overflow-y:auto; padding-right:4px;
          scrollbar-width:thin; scrollbar-color:var(--border) transparent;
        }
        .msg-thread-empty { font-size:12px; color:var(--muted); text-align:center; padding:16px 0; }
        .msg-bubble-wrap { display:flex; flex-direction:column; max-width:88%; position:relative; }
        .msg-bubble-wrap.mine  { align-self:flex-end; align-items:flex-end; }
        .msg-bubble-wrap.theirs{ align-self:flex-start; align-items:flex-start; }
        .msg-meta {
          font-size:10px; color:var(--muted); margin-bottom:3px;
          display:flex; align-items:center; gap:5px;
        }
        .msg-alert-badge {
          font-size:9px; font-weight:700; background:rgba(251,191,36,.15);
          color:var(--warn); border:1px solid var(--warn);
          padding:1px 5px; border-radius:20px;
        }
        .msg-bubble {
          padding:7px 11px; border-radius:10px; font-size:13px;
          line-height:1.5; word-break:break-word; white-space:pre-wrap;
        }
        .msg-bubble-wrap.mine .msg-bubble {
          background:var(--accent); color:var(--bg);
          font-weight:600; border-bottom-right-radius:3px;
        }
        .msg-bubble-wrap.theirs .msg-bubble {
          background:var(--bg); border:1px solid var(--border);
          color:var(--text); border-bottom-left-radius:3px;
        }
        .msg-del-btn {
          display:none; background:none; border:none; cursor:pointer;
          color:var(--muted); padding:2px; border-radius:4px; margin-top:2px;
          transition:color .15s;
        }
        .msg-bubble-wrap:hover .msg-del-btn { display:flex; align-items:center; }
        .msg-del-btn:hover { color:var(--danger); }
        .msg-thread-input-area {
          display:flex; gap:6px; margin-top:10px; align-items:flex-end;
          border-top:1px solid var(--border); padding-top:10px;
        }
        .msg-thread-input {
          flex:1; background:var(--bg); border:1px solid var(--border);
          border-radius:8px; color:var(--text); font-size:13px;
          font-family:inherit; padding:7px 10px; resize:none;
          min-height:34px; max-height:80px; outline:none; line-height:1.4;
          transition:border-color .15s;
        }
        .msg-thread-input:focus { border-color:var(--accent); box-shadow:0 0 0 3px rgba(34,211,238,.1); }
        .msg-thread-send {
          width:34px; height:34px; border-radius:8px;
          background:var(--accent); border:none; cursor:pointer;
          display:flex; align-items:center; justify-content:center;
          flex-shrink:0; transition:filter .15s;
        }
        .msg-thread-send:hover { filter:brightness(1.1); }
        .msg-thread-send:disabled { opacity:.4; cursor:not-allowed; }
        .msg-thread-send svg { color:var(--bg); }
        .msg-thread-loading { font-size:11px; color:var(--muted); padding:8px 0; text-align:center; }
      `;
      document.head.appendChild(style);
    }

    // ── HTML du composant ──
    container.innerHTML =
      '<div class="msg-thread-root">' +
        (!compact
          ? '<div class="msg-thread-header">' +
              '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
                '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>' +
              '</svg>' +
              'Fil de discussion' +
              '<span class="msg-thread-count" id="' + containerId + '-count">0</span>' +
            '</div>'
          : '') +
        '<div class="msg-thread-list msg-thread-loading">Chargement…</div>' +
        '<div class="msg-thread-input-area">' +
          '<textarea class="msg-thread-input" id="' + containerId + '-input"' +
            ' placeholder="Ajouter un commentaire…" rows="1" maxlength="2000"></textarea>' +
          '<button class="msg-thread-send" id="' + containerId + '-send" title="Envoyer">' +
            '<svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">' +
              '<path d="M22 2L11 13"/><path d="M22 2L15 22l-4-9-9-4 20-7z"/>' +
            '</svg>' +
          '</button>' +
        '</div>' +
      '</div>';

    const inputEl = document.getElementById(containerId + '-input');
    const sendBtn = document.getElementById(containerId + '-send');
    const countEl = document.getElementById(containerId + '-count');
    let messages = [];
    let pollTimer = null;

    // ── Charger les messages ──
    async function load() {
      try {
        const r = await fetch(
          '/api/messaging/thread?module=' + encodeURIComponent(module) +
          '&object_type=' + encodeURIComponent(objectType) +
          '&object_id=' + encodeURIComponent(objectId),
          { credentials: 'include' }
        );
        if (!r.ok) throw new Error('HTTP ' + r.status);
        messages = await r.json();
        renderMessages(container, messages, currentUser.id);
        if (countEl) countEl.textContent = messages.length;
      } catch (e) {
        const list = container.querySelector('.msg-thread-list');
        if (list) list.innerHTML =
          '<div class="msg-thread-empty">Impossible de charger les commentaires.</div>';
      }
    }

    // ── Envoyer ──
    async function send() {
      const text = (inputEl.value || '').trim();
      if (!text || sendBtn.disabled) return;
      sendBtn.disabled = true;
      try {
        const r = await fetch('/api/messaging/thread', {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            module, object_type: objectType, object_id: objectId, body: text,
          }),
        });
        if (!r.ok) {
          const j = await r.json().catch(() => ({}));
          if (window.showToast) showToast(j.detail || 'Erreur envoi', 'danger');
          return;
        }
        inputEl.value = '';
        inputEl.style.height = 'auto';
        await load();
      } finally {
        sendBtn.disabled = false;
        inputEl.focus();
      }
    }

    inputEl.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
    });
    inputEl.addEventListener('input', function () {
      inputEl.style.height = 'auto';
      inputEl.style.height = Math.min(inputEl.scrollHeight, 80) + 'px';
    });
    sendBtn.addEventListener('click', send);

    // ── Polling toutes les 30s ──
    load();
    pollTimer = setInterval(load, 30000);

    return {
      reload: load,
      destroy: function () {
        if (pollTimer) clearInterval(pollTimer);
        container.innerHTML = '';
      },
    };
  }

  global.initMsgThread = initMsgThread;
})(window);
```

Ensuite, dans app/web/html.py, dans la fonction qui génère le layout commun (chercher la balise </head> ou la liste des <link> CSS), ajouter :
    <script src="/static/messaging_thread.js" defer></script>

Placer après les autres balises <link> et <script> existantes.

Et dans main.py, vérifier que le dossier static/ est bien monté :
    app.mount("/static", StaticFiles(directory="static"), name="static")
(Déjà présent normalement — ne pas dupliquer.)
```

---

## Prompt 3 — Intégration planning machine

```
Contexte projet : MySifa. Le composant initMsgThread() est disponible dans static/messaging_thread.js.
Le router /api/messaging/* est opérationnel.
Fichier concerné : app/web/planning_page.py (~3700 lignes).

Dans ce fichier, la variable Python PLANNING_HTML contient le HTML complet de la page.
La fonction JS openEdit(id) ouvre un modal de modification d'un dossier planning.
Elle appelle document.getElementById("mroot").innerHTML = modalHTML(...) avec :
  - fieldsHtml + traceHtml + resetBlock comme contenu
  - "Enregistrer" et submitEdit(id) comme action principale

Tâche : Ajouter un fil de commentaires en bas du modal openEdit.

--- Modification dans la fonction openEdit(id) (vers ligne 2947) ---

À la fin de la fonction, AVANT la ligne :
  document.getElementById("mroot").innerHTML = modalHTML(...)

Ajouter la variable suivante :

```javascript
  const threadSection = `
    <div style="margin-top:18px;padding-top:16px;border-top:1px solid var(--border2)">
      <div id="planning-thread-${id}"></div>
    </div>`;
```

Puis modifier l'appel à modalHTML pour inclure threadSection dans le contenu :
  Remplacer : fieldsHtml + traceHtml + resetBlock
  Par        : fieldsHtml + traceHtml + resetBlock + threadSection

Enfin, après l'appel à document.getElementById("mroot").innerHTML = modalHTML(...),
ajouter immédiatement (toujours dans openEdit) :

```javascript
  // Initialiser le fil de commentaires pour ce dossier
  requestAnimationFrame(function() {
    if (typeof initMsgThread === 'function') {
      const _planningThread = initMsgThread('planning-thread-' + id, {
        module: 'planning',
        objectType: 'planning_entry',
        objectId: id,
        currentUser: { id: window.__MYSIFA_UID__ || 0, nom: window.__MYSIFA_NOM__ || '' },
        compact: false,
      });
      // Stopper le polling si le modal est fermé
      const closeBtn = document.querySelector('#mroot .close-btn, #mroot [onclick*="closeM"]');
      if (closeBtn) {
        const origClick = closeBtn.onclick;
        closeBtn.onclick = function(e) {
          _planningThread.destroy();
          if (origClick) origClick.call(this, e);
        };
      }
    }
  });
```

--- Variable window.__MYSIFA_UID__ et __MYSIFA_NOM__ ---

Dans la section <script> qui définit window.__MYSIFA_APP__ (chercher cette variable dans PLANNING_HTML),
ajouter juste après :
  window.__MYSIFA_UID__  = USER_ID_PLACEHOLDER;   // à remplacer par la valeur Python injectée
  window.__MYSIFA_NOM__  = "USER_NOM_PLACEHOLDER"; // idem
  window.__MYSIFA_ROLE__ = "USER_ROLE_PLACEHOLDER";

Dans la fonction Python planning_page(), injecter ces valeurs via .replace() :
  html = html.replace("USER_ID_PLACEHOLDER", str(user.get("id", 0)))
  html = html.replace('"USER_NOM_PLACEHOLDER"', json.dumps(user.get("nom") or ""))
  html = html.replace('"USER_ROLE_PLACEHOLDER"', json.dumps(user.get("role") or ""))

(Ajouter `import json` en haut du fichier si absent.)

--- Aucune autre modification ---
Ne pas toucher aux autres fonctions JS. Ne pas modifier la structure modalHTML.
```

---

## Prompt 4 — Intégration fabrication (MyProd)

```
Contexte projet : MySifa. Le composant initMsgThread() est disponible.
Fichier concerné : app/web/fabrication_page.py (~3100 lignes).

Dans ce fichier, la variable FABRICATION_HTML contient le HTML de la page.
La page a un système d'onglets en bas (.fab-tab-nav) avec des boutons .fab-tab-btn.
Les saisies de production sont affichées sous forme de tableau.
Les dossiers sont identifiés par no_dossier (string).

Tâche : Ajouter un onglet "Commentaires" dans la zone d'onglets de la page,
avec un fil de commentaires lié au dossier actif.

--- PARTIE 1 : Ajouter l'onglet dans le HTML ---

Dans FABRICATION_HTML, trouver la section .fab-tab-nav (contient des boutons .fab-tab-btn).
À la suite du dernier bouton .fab-tab-btn existant, ajouter :

```html
<button class="fab-tab-btn" id="tab-btn-comments" onclick="switchTab('comments')" title="Commentaires">
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
  Commentaires
  <span class="msg-tab-badge" id="fab-comments-badge" style="display:none;background:var(--danger);color:#fff;font-size:9px;font-weight:700;border-radius:20px;padding:1px 5px;margin-left:4px"></span>
</button>
```

--- PARTIE 2 : Ajouter le panneau de contenu de l'onglet ---

Chercher les panneaux d'onglets existants (divs avec id correspondant aux onglets, gérés par switchTab).
Ajouter à la suite du dernier panneau d'onglet :

```html
<div id="tab-panel-comments" class="fab-tab-panel" style="display:none;padding:14px;overflow-y:auto">
  <div id="fab-comments-thread-wrap">
    <div id="fab-msg-thread-root"></div>
  </div>
</div>
```

--- PARTIE 3 : JS — Initialiser le thread lors du changement d'onglet ---

Dans la fonction JS switchTab(name) (ou la logique qui affiche/cache les panneaux),
ajouter la gestion de l'onglet 'comments' :

```javascript
if (name === 'comments') {
  const dossierRef = S.activeDossier || S.no_dossier || null; // adapter selon la variable d'état réelle
  if (!dossierRef) {
    document.getElementById('fab-msg-thread-root').innerHTML =
      '<div style="font-size:12px;color:var(--muted);padding:16px;text-align:center">Sélectionner un dossier pour afficher les commentaires.</div>';
    return;
  }
  if (window._fabMsgThread) { window._fabMsgThread.destroy(); }
  window._fabMsgThread = initMsgThread('fab-msg-thread-root', {
    module: 'fabrication',
    objectType: 'production_dossier',
    objectId: dossierRef,
    currentUser: { id: window.__MYSIFA_UID__ || 0, nom: window.__MYSIFA_NOM__ || '' },
    compact: false,
  });
}
```

Note : adapter S.activeDossier au nom réel de la variable d'état qui contient le no_dossier
actif dans la page fabrication. Chercher dans l'objet d'état S (défini en haut du JS) la clé
qui correspond au dossier en cours de consultation.

--- PARTIE 4 : Variables window.__MYSIFA_UID__ / __NOM__ / __ROLE__ ---

Si déjà présentes (injectées au prompt 3 dans planning), vérifier qu'elles sont aussi
injectées dans la page fabrication via les mêmes .replace() dans fabrication_page() Python.
Sinon, appliquer le même pattern que pour le planning.

--- PARTIE 5 : Badge non-lu sur l'onglet ---

Après le chargement initial de la page (dans le DOMContentLoaded ou après l'init JS),
ajouter un appel pour afficher le badge :

```javascript
async function updateFabCommentsBadge() {
  if (typeof initMsgThread === 'undefined') return;
  const dossierRef = S.activeDossier || S.no_dossier || null;
  if (!dossierRef) return;
  try {
    const r = await fetch('/api/messaging/badge', { credentials: 'include' });
    if (!r.ok) return;
    const data = await r.json();
    const badge = document.getElementById('fab-comments-badge');
    if (!badge) return;
    const count = data['fabrication'] || 0;
    if (count > 0) {
      badge.textContent = count > 9 ? '9+' : String(count);
      badge.style.display = '';
    } else {
      badge.style.display = 'none';
    }
  } catch (e) {}
}
updateFabCommentsBadge();
```
```

---

## Prompt 5 — Badges sidebar + page Boîte de réception

```
Contexte projet : MySifa. Le composant initMsgThread() et le router /api/messaging/* sont opérationnels.
Fichier principal : app/web/html.py (~10700 lignes) — contient le layout commun, la sidebar, le portail.

Tâche A : Ajouter les badges non-lus dans la sidebar.
Tâche B : Créer la page /inbox (boîte de réception des alertes ciblées).

--- PARTIE A : Badges sidebar ---

Dans app/web/html.py, trouver la génération HTML de la sidebar (chercher .nav-btn, les liens de
navigation vers /planning, /prod, /stock, etc.).

Pour chaque lien de navigation qui a un module correspondant, ajouter un span badge :
Chercher le pattern des liens nav existants et ajouter, dans chaque lien :
  <span class="nav-badge" id="nav-badge-{module}" style="display:none"></span>

Exemple pour le lien planning :
  <a href="/planning" class="nav-btn ...">
    ...Planning...
    <span class="nav-badge" id="nav-badge-planning" style="display:none"></span>
  </a>

Modules à badger : planning, prod (module=fabrication), stock, expe.

CSS à ajouter dans le bloc <style> commun :
```css
.nav-badge-msg {
  font-size:9px; font-weight:800; background:var(--danger); color:#fff;
  border-radius:20px; padding:1px 5px; min-width:16px; text-align:center;
  line-height:16px; display:inline-block;
}
```

Ajouter aussi un lien "Boîte de réception" dans la sidebar (dans la section navigation,
au-dessus de .sidebar-bottom) :
```html
<a href="/inbox" class="nav-btn {active_inbox}">
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
    <path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>
  </svg>
  Messages
  <span class="nav-badge-msg" id="nav-badge-inbox" style="display:none"></span>
</a>
```

Dans le <script> commun du layout (ou avant </body>), ajouter la fonction de mise à jour des badges :
```javascript
(async function updateMsgBadges() {
  try {
    const r = await fetch('/api/messaging/badge', { credentials: 'include' });
    if (!r.ok) return;
    const data = await r.json();
    const map = { planning: 'planning', fabrication: 'prod', stock: 'stock', expe: 'expe', inbox: 'inbox' };
    for (const [key, badgeId] of Object.entries(map)) {
      const el = document.getElementById('nav-badge-' + badgeId);
      if (!el) continue;
      const count = data[key] || 0;
      if (count > 0) {
        el.textContent = count > 9 ? '9+' : String(count);
        el.style.display = '';
      } else {
        el.style.display = 'none';
      }
    }
  } catch (e) {}
})();
```

--- PARTIE B : Page /inbox ---

Créer le fichier app/web/inbox_page.py :

```python
"""MySifa — Boîte de réception (alertes ciblées et messages non lus).
Route : /inbox
Accès : tout utilisateur authentifié.
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import APP_VERSION
from services.auth_service import get_current_user
from app.web.access_denied import access_denied_response

router = APIRouter()


@router.get("/inbox", response_class=HTMLResponse)
def inbox_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/inbox", status_code=302)
        raise
    nom = (user.get("nom") or "").strip() or user.get("email", "")
    uid = str(user.get("id", 0))
    role = user.get("role", "")
    html = (
        INBOX_HTML
        .replace("__V_LABEL__", f"v{APP_VERSION}")
        .replace("__USER_NOM__", nom)
        .replace("__USER_ID__", uid)
        .replace("__USER_ROLE__", role)
    )
    return HTMLResponse(content=html)


INBOX_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17">
<title>Messages — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="stylesheet" href="/static/support_widget.css">
<link rel="stylesheet" href="/static/mysifa_theme.css">
<script src="/static/messaging_thread.js" defer></script>
<style>
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;
  --muted:#94a3b8;--accent:#22d3ee;--accent-bg:rgba(34,211,238,0.12);
  --ok:#34d399;--warn:#fbbf24;--danger:#f87171;
  --sidebar-w:260px;
}
body.light{
  --bg:#f1f5f9;--card:#fff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;
  --muted:#64748b;--accent:#0891b2;--accent-bg:rgba(8,145,178,.08);
}
html,body{height:100%;overflow:hidden}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;font-size:14px}
#app{display:grid;grid-template-columns:var(--sidebar-w) 1fr;height:100vh;overflow:hidden}

/* Sidebar — reprendre exactement la sidebar de html.py */
/* (À remplacer par le composant sidebar commun si disponible) */

.main{overflow-y:auto;padding:28px 32px;display:flex;flex-direction:column;gap:20px}
.page-title{font-size:20px;font-weight:800;letter-spacing:-.3px}
.page-sub{font-size:13px;color:var(--muted)}

.inbox-section{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden}
.inbox-section-hdr{
  padding:14px 18px;border-bottom:1px solid var(--border);
  display:flex;align-items:center;gap:10px;
}
.inbox-section-title{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--text2);flex:1}
.inbox-count{font-size:11px;background:var(--accent-bg);color:var(--accent);padding:2px 8px;border-radius:20px;font-weight:700}

.inbox-empty{padding:24px;font-size:13px;color:var(--muted);text-align:center}

.inbox-item{
  padding:14px 18px;border-bottom:1px solid var(--border);
  display:flex;flex-direction:column;gap:5px;cursor:pointer;
  transition:background .12s;
}
.inbox-item:last-child{border-bottom:none}
.inbox-item:hover{background:var(--accent-bg)}
.inbox-item.unread .inbox-item-body{font-weight:600;color:var(--text)}
.inbox-item-meta{font-size:11px;color:var(--muted);display:flex;align-items:center;gap:6px}
.inbox-item-from{font-weight:700;color:var(--text2)}
.inbox-alert-badge{
  font-size:9px;font-weight:700;background:rgba(251,191,36,.15);
  color:var(--warn);border:1px solid var(--warn);
  padding:1px 5px;border-radius:20px;
}
.inbox-item-body{font-size:13px;color:var(--text2);line-height:1.5;white-space:pre-wrap;overflow:hidden;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
.inbox-item-ctx{font-size:11px;color:var(--muted)}

.mark-all-btn{
  background:none;border:1.5px solid var(--border);border-radius:8px;
  color:var(--text2);font-size:12px;font-weight:600;cursor:pointer;
  padding:5px 12px;font-family:inherit;transition:all .15s;
}
.mark-all-btn:hover{border-color:var(--accent);color:var(--accent)}
</style>
</head>
<body>
<script>
  window.__MYSIFA_APP__ = 'inbox';
  window.__MYSIFA_UID__  = __USER_ID__;
  window.__MYSIFA_NOM__  = "__USER_NOM__";
  window.__MYSIFA_ROLE__ = "__USER_ROLE__";
</script>

<div id="app">
  <!-- Sidebar : copier la sidebar de html.py avec le lien /inbox marqué actif -->
  <!-- (À adapter selon la structure réelle de html.py) -->

  <div class="main">
    <div>
      <div class="page-title">Messages</div>
      <div class="page-sub">Alertes et commentaires qui vous sont adressés</div>
    </div>

    <div class="inbox-section">
      <div class="inbox-section-hdr">
        <div class="inbox-section-title">Non lus</div>
        <span class="inbox-count" id="inbox-count">0</span>
        <button class="mark-all-btn" onclick="markAllRead()">Tout marquer lu</button>
      </div>
      <div id="inbox-list"><div class="inbox-empty">Chargement…</div></div>
    </div>
  </div>
</div>

<script>
const MODULE_LABELS = {
  planning: 'Planning', fabrication: 'MyProd', stock: 'MyStock',
  expe: 'MyExpé', rh: 'Planning RH', global: 'MySifa',
};

function fmtDatetime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' }) + ' ' +
         d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
}

function escHtml(s) {
  return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

let _messages = [];

async function loadInbox() {
  try {
    const r = await fetch('/api/messaging/inbox', { credentials: 'include' });
    if (!r.ok) throw new Error();
    _messages = await r.json();
    renderInbox(_messages);
  } catch (e) {
    document.getElementById('inbox-list').innerHTML =
      '<div class="inbox-empty">Impossible de charger la boîte de réception.</div>';
  }
}

function renderInbox(msgs) {
  const el = document.getElementById('inbox-list');
  const countEl = document.getElementById('inbox-count');
  if (countEl) countEl.textContent = msgs.length;
  if (msgs.length === 0) {
    el.innerHTML = '<div class="inbox-empty">Aucun message non lu.</div>';
    return;
  }
  el.innerHTML = msgs.map(function (m) {
    const mod = MODULE_LABELS[m.module] || m.module;
    const alertBadge = m.is_alert
      ? '<span class="inbox-alert-badge">Alerte</span>'
      : '';
    return (
      '<div class="inbox-item unread" data-id="' + m.id + '" onclick="markRead(' + m.id + ', this)">' +
        '<div class="inbox-item-meta">' +
          '<span class="inbox-item-from">' + escHtml(m.from_nom) + '</span>' +
          ' · ' + fmtDatetime(m.created_at) + alertBadge +
        '</div>' +
        '<div class="inbox-item-body">' + escHtml(m.body) + '</div>' +
        '<div class="inbox-item-ctx">' + mod + ' · ' + escHtml(m.object_id) + '</div>' +
      '</div>'
    );
  }).join('');
}

async function markRead(id, el) {
  try {
    await fetch('/api/messaging/inbox/read', {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids: [id] }),
    });
    if (el) el.classList.remove('unread');
    _messages = _messages.filter(function (m) { return m.id !== id; });
    const countEl = document.getElementById('inbox-count');
    if (countEl) countEl.textContent = _messages.length;
  } catch (e) {}
}

async function markAllRead() {
  const ids = _messages.map(function (m) { return m.id; });
  if (!ids.length) return;
  try {
    await fetch('/api/messaging/inbox/read', {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids }),
    });
    _messages = [];
    renderInbox([]);
  } catch (e) {}
}

loadInbox();
</script>
</body>
</html>
"""
```

Enregistrer dans main.py :
  Import  : from app.web.inbox_page import router as inbox_page_router
  Ajout   : app.include_router(inbox_page_router)

Dans la sidebar de inbox_page.py, utiliser la même structure que les autres pages
(copier depuis app/web/html.py le composant sidebar commun).
Marquer le lien "Messages" comme actif (class active + styles accent).
```

---

## Prompt 6 — Chat interne : canaux + messages directs (DB + API)

```
Contexte projet : MySifa, FastAPI + SQLite. L'équipe n'a pas d'outil de messagerie dédié.
MySifa doit proposer un chat interne complet : messages directs (DMs) entre collègues
et canaux d'équipe par rôle ou thème.
Config DB : DB_PATH dans config.py. Migrations via schema_migrations dans app/core/database.py.

--- PARTIE 1 : Migration DB dans app/core/database.py ---

Trouver le numéro de la dernière migration existante (ex: version=15 ajouté au Prompt 1)
et ajouter la migration suivante (version=16) :

```python
if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=16 LIMIT 1").fetchone():
    # ── Canaux (généraux ou DMs) ──
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_channels (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            type         TEXT    NOT NULL DEFAULT 'channel', -- 'channel' | 'direct'
            name         TEXT    DEFAULT NULL,               -- NULL pour les DMs
            description  TEXT    DEFAULT NULL,
            created_by   INTEGER REFERENCES users(id),
            created_at   TEXT    NOT NULL,
            archived_at  TEXT    DEFAULT NULL
        )
    """)
    # ── Membres d'un canal ──
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_members (
            channel_id   INTEGER NOT NULL REFERENCES chat_channels(id),
            user_id      INTEGER NOT NULL REFERENCES users(id),
            joined_at    TEXT    NOT NULL,
            last_read_at TEXT    DEFAULT NULL,
            PRIMARY KEY (channel_id, user_id)
        )
    """)
    # ── Messages ──
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id   INTEGER NOT NULL REFERENCES chat_channels(id),
            user_id      INTEGER NOT NULL REFERENCES users(id),
            user_nom     TEXT    NOT NULL,
            body         TEXT    NOT NULL,
            created_at   TEXT    NOT NULL,
            deleted_at   TEXT    DEFAULT NULL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_chat_msg_chan
        ON chat_messages(channel_id, created_at)
    """)
    conn.execute(
        "INSERT OR IGNORE INTO schema_migrations (version, name, applied_at) VALUES (?,?,?)",
        (16, "chat_channels_messages", datetime.utcnow().isoformat())
    )
    conn.commit()
```

--- PARTIE 2 : Créer app/routers/chat.py ---

ATTENTION : ne pas confondre avec l'ancien prototype chat.py supprimé lors du déploiement
de l'agent IA. Ce nouveau fichier est différent — il gère le chat interne entre utilisateurs.

```python
"""MySifa — Chat interne (DMs + canaux d'équipe).

Routes : /api/chat/*
Accès  : tout utilisateur authentifié.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from database import get_db
from services.auth_service import get_current_user

router = APIRouter(prefix="/api/chat", tags=["chat"])

_PARIS = ZoneInfo("Europe/Paris")
_MAX_BODY = 4000
_PAGE_SIZE = 50  # messages par page (pagination inverse)


def _now_iso() -> str:
    return datetime.now(_PARIS).replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%S")


def _require(request: Request) -> dict:
    return get_current_user(request)


# ─── Canaux ──────────────────────────────────────────────────────────────────

@router.get("/channels")
def list_channels(request: Request):
    """Liste les canaux dont l'utilisateur est membre, avec compte de non-lus."""
    user = _require(request)
    uid = user["id"]
    with get_db() as conn:
        rows = conn.execute(
            """SELECT c.id, c.type, c.name, c.description, c.created_at,
                      cm.last_read_at,
                      (SELECT COUNT(*) FROM chat_messages m
                       WHERE m.channel_id = c.id AND m.deleted_at IS NULL
                         AND m.user_id != ?
                         AND (cm.last_read_at IS NULL OR m.created_at > cm.last_read_at)
                      ) as unread_count,
                      (SELECT MAX(m2.created_at) FROM chat_messages m2
                       WHERE m2.channel_id = c.id AND m2.deleted_at IS NULL
                      ) as last_message_at,
                      (SELECT m3.body FROM chat_messages m3
                       WHERE m3.channel_id = c.id AND m3.deleted_at IS NULL
                       ORDER BY m3.created_at DESC LIMIT 1
                      ) as last_message_body,
                      (SELECT m4.user_nom FROM chat_messages m4
                       WHERE m4.channel_id = c.id AND m4.deleted_at IS NULL
                       ORDER BY m4.created_at DESC LIMIT 1
                      ) as last_message_from
               FROM chat_channels c
               JOIN chat_members cm ON cm.channel_id = c.id AND cm.user_id = ?
               WHERE c.archived_at IS NULL
               ORDER BY last_message_at DESC NULLS LAST""",
            (uid, uid),
        ).fetchall()

        # Pour les DMs, récupérer le nom de l'autre participant
        result = []
        for r in rows:
            d = dict(r)
            if d["type"] == "direct":
                other = conn.execute(
                    """SELECT u.nom, u.id FROM chat_members cm2
                       JOIN users u ON u.id = cm2.user_id
                       WHERE cm2.channel_id = ? AND cm2.user_id != ?
                       LIMIT 1""",
                    (d["id"], uid),
                ).fetchone()
                d["display_name"] = other["nom"] if other else "Utilisateur inconnu"
                d["other_user_id"] = other["id"] if other else None
            else:
                d["display_name"] = d["name"] or "Canal sans nom"
                d["other_user_id"] = None
            result.append(d)

    return result


@router.post("/channels")
async def create_channel(request: Request):
    """
    Créer un canal ou démarrer un DM.
    Pour un DM : { type: 'direct', user_id: 42 }
    Pour un canal : { type: 'channel', name: 'fabrication', description: '...', member_ids: [1,2,3] }
    """
    user = _require(request)
    uid = user["id"]
    data = await request.json()
    ch_type = (data.get("type") or "channel").strip()
    if ch_type not in ("channel", "direct"):
        raise HTTPException(400, "type doit être 'channel' ou 'direct'")

    now = _now_iso()

    with get_db() as conn:
        if ch_type == "direct":
            other_id = data.get("user_id")
            if not other_id:
                raise HTTPException(400, "user_id requis pour un DM")
            other_id = int(other_id)
            if other_id == uid:
                raise HTTPException(400, "Impossible de créer un DM avec soi-même")

            # Vérifier si un DM existe déjà entre ces deux utilisateurs
            existing = conn.execute(
                """SELECT c.id FROM chat_channels c
                   JOIN chat_members cm1 ON cm1.channel_id = c.id AND cm1.user_id = ?
                   JOIN chat_members cm2 ON cm2.channel_id = c.id AND cm2.user_id = ?
                   WHERE c.type = 'direct' AND c.archived_at IS NULL
                   LIMIT 1""",
                (uid, other_id),
            ).fetchone()
            if existing:
                return {"id": existing["id"], "existing": True}

            cur = conn.execute(
                "INSERT INTO chat_channels (type, created_by, created_at) VALUES ('direct',?,?)",
                (uid, now),
            )
            ch_id = cur.lastrowid
            for member_id in (uid, other_id):
                conn.execute(
                    "INSERT OR IGNORE INTO chat_members (channel_id, user_id, joined_at) VALUES (?,?,?)",
                    (ch_id, member_id, now),
                )

        else:  # channel
            name = (data.get("name") or "").strip()
            if not name:
                raise HTTPException(400, "name requis pour un canal")
            if len(name) > 60:
                raise HTTPException(400, "Nom de canal trop long (max 60 caractères)")
            # Vérifier doublon de nom
            dupe = conn.execute(
                "SELECT id FROM chat_channels WHERE type='channel' AND lower(name)=lower(?) AND archived_at IS NULL LIMIT 1",
                (name,),
            ).fetchone()
            if dupe:
                raise HTTPException(409, f"Un canal '{name}' existe déjà")

            description = (data.get("description") or "").strip() or None
            cur = conn.execute(
                "INSERT INTO chat_channels (type, name, description, created_by, created_at) VALUES ('channel',?,?,?,?)",
                (name, description, uid, now),
            )
            ch_id = cur.lastrowid

            # Créateur + membres fournis
            member_ids = list({uid} | set(int(m) for m in (data.get("member_ids") or [])))
            for mid in member_ids:
                conn.execute(
                    "INSERT OR IGNORE INTO chat_members (channel_id, user_id, joined_at) VALUES (?,?,?)",
                    (ch_id, mid, now),
                )

        conn.commit()

    return {"id": ch_id, "existing": False}


@router.post("/channels/{channel_id}/join")
def join_channel(channel_id: int, request: Request):
    """Rejoindre un canal existant (canaux publics uniquement — pas les DMs)."""
    user = _require(request)
    with get_db() as conn:
        ch = conn.execute(
            "SELECT id, type FROM chat_channels WHERE id=? AND archived_at IS NULL LIMIT 1",
            (channel_id,),
        ).fetchone()
        if not ch:
            raise HTTPException(404, "Canal introuvable")
        if ch["type"] == "direct":
            raise HTTPException(403, "Impossible de rejoindre un DM")
        conn.execute(
            "INSERT OR IGNORE INTO chat_members (channel_id, user_id, joined_at) VALUES (?,?,?)",
            (channel_id, user["id"], _now_iso()),
        )
        conn.commit()
    return {"joined": True}


@router.get("/channels/{channel_id}/members")
def channel_members(channel_id: int, request: Request):
    user = _require(request)
    with get_db() as conn:
        _assert_member(conn, channel_id, user["id"])
        rows = conn.execute(
            """SELECT u.id, u.nom, u.role, cm.joined_at
               FROM chat_members cm JOIN users u ON u.id = cm.user_id
               WHERE cm.channel_id = ?
               ORDER BY u.nom""",
            (channel_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# ─── Messages ────────────────────────────────────────────────────────────────

@router.get("/channels/{channel_id}/messages")
def get_messages(
    channel_id: int,
    request: Request,
    before: Optional[str] = None,  # ISO datetime — pagination "charger plus"
):
    """Messages d'un canal (les N plus récents, ou avant 'before' pour la pagination)."""
    user = _require(request)
    with get_db() as conn:
        _assert_member(conn, channel_id, user["id"])

        if before:
            rows = conn.execute(
                """SELECT id, user_id, user_nom, body, created_at
                   FROM chat_messages
                   WHERE channel_id=? AND deleted_at IS NULL AND created_at < ?
                   ORDER BY created_at DESC LIMIT ?""",
                (channel_id, before, _PAGE_SIZE),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT id, user_id, user_nom, body, created_at
                   FROM chat_messages
                   WHERE channel_id=? AND deleted_at IS NULL
                   ORDER BY created_at DESC LIMIT ?""",
                (channel_id, _PAGE_SIZE),
            ).fetchall()

        # Marquer comme lu (mettre à jour last_read_at)
        conn.execute(
            "UPDATE chat_members SET last_read_at=? WHERE channel_id=? AND user_id=?",
            (_now_iso(), channel_id, user["id"]),
        )
        conn.commit()

    uid = user["id"]
    messages = [
        {
            "id": r["id"],
            "user_id": r["user_id"],
            "user_nom": r["user_nom"],
            "body": r["body"],
            "created_at": r["created_at"],
            "is_mine": r["user_id"] == uid,
        }
        for r in reversed(rows)  # remettre en ordre chronologique
    ]
    return {"messages": messages, "has_more": len(rows) == _PAGE_SIZE}


@router.post("/channels/{channel_id}/messages")
async def send_message(channel_id: int, request: Request):
    """Envoyer un message dans un canal."""
    user = _require(request)
    data = await request.json()
    body = (data.get("body") or "").strip()
    if not body:
        raise HTTPException(400, "Message vide")
    if len(body) > _MAX_BODY:
        raise HTTPException(400, f"Message trop long (max {_MAX_BODY} caractères)")

    now = _now_iso()
    with get_db() as conn:
        _assert_member(conn, channel_id, user["id"])
        cur = conn.execute(
            "INSERT INTO chat_messages (channel_id, user_id, user_nom, body, created_at) VALUES (?,?,?,?,?)",
            (channel_id, user["id"], user.get("nom") or user.get("email", ""), body, now),
        )
        # Mettre à jour last_read_at de l'expéditeur
        conn.execute(
            "UPDATE chat_members SET last_read_at=? WHERE channel_id=? AND user_id=?",
            (now, channel_id, user["id"]),
        )
        conn.commit()
    return {"id": cur.lastrowid, "created_at": now}


@router.delete("/channels/{channel_id}/messages/{msg_id}")
def delete_message(channel_id: int, msg_id: int, request: Request):
    """Soft-delete (auteur ou admin)."""
    user = _require(request)
    is_admin = user.get("role") in {"superadmin", "direction", "administration"}
    with get_db() as conn:
        row = conn.execute(
            "SELECT user_id, deleted_at FROM chat_messages WHERE id=? AND channel_id=? LIMIT 1",
            (msg_id, channel_id),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Message introuvable")
        if row["deleted_at"]:
            raise HTTPException(410, "Message déjà supprimé")
        if not is_admin and row["user_id"] != user["id"]:
            raise HTTPException(403, "Vous ne pouvez supprimer que vos propres messages")
        conn.execute(
            "UPDATE chat_messages SET deleted_at=? WHERE id=?", (_now_iso(), msg_id)
        )
        conn.commit()
    return {"deleted": True}


# ─── Utilitaires ─────────────────────────────────────────────────────────────

@router.get("/users")
def list_users(request: Request, q: str = ""):
    """Liste des utilisateurs actifs (pour démarrer un DM ou ajouter à un canal)."""
    _require(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, nom, role FROM users WHERE actif=1 ORDER BY nom",
        ).fetchall()
    users = [dict(r) for r in rows]
    if q:
        ql = q.lower()
        users = [u for u in users if ql in (u.get("nom") or "").lower()]
    return users


@router.get("/unread")
def unread_total(request: Request):
    """Nombre total de messages non lus sur tous les canaux (pour badge sidebar)."""
    user = _require(request)
    uid = user["id"]
    with get_db() as conn:
        row = conn.execute(
            """SELECT COUNT(*) as c
               FROM chat_messages m
               JOIN chat_members cm ON cm.channel_id = m.channel_id AND cm.user_id = ?
               WHERE m.deleted_at IS NULL AND m.user_id != ?
                 AND (cm.last_read_at IS NULL OR m.created_at > cm.last_read_at)""",
            (uid, uid),
        ).fetchone()
    return {"unread": row["c"]}


@router.post("/channels/seed-defaults")
def seed_default_channels(request: Request):
    """
    Crée les canaux par défaut si absents : #général, #fabrication, #logistique.
    Réservé au superadmin. Idempotent.
    """
    user = _require(request)
    if user.get("role") != "superadmin":
        raise HTTPException(403, "Réservé au superadmin")

    defaults = [
        ("général",    "Canal général — toute l'équipe", None),
        ("fabrication","Équipe fabrication",              ["fabrication", "direction", "administration", "superadmin"]),
        ("logistique", "Équipe logistique",               ["logistique", "direction", "administration", "superadmin"]),
    ]
    now = _now_iso()
    created = []
    with get_db() as conn:
        for name, desc, roles in defaults:
            existing = conn.execute(
                "SELECT id FROM chat_channels WHERE type='channel' AND lower(name)=lower(?) AND archived_at IS NULL LIMIT 1",
                (name,),
            ).fetchone()
            if existing:
                continue
            cur = conn.execute(
                "INSERT INTO chat_channels (type, name, description, created_by, created_at) VALUES ('channel',?,?,?,?)",
                (name, desc, user["id"], now),
            )
            ch_id = cur.lastrowid
            # Ajouter les utilisateurs dont le rôle correspond
            if roles:
                members = conn.execute(
                    f"SELECT id FROM users WHERE actif=1 AND role IN ({','.join('?' * len(roles))})",
                    roles,
                ).fetchall()
            else:
                members = conn.execute("SELECT id FROM users WHERE actif=1").fetchall()
            for m in members:
                conn.execute(
                    "INSERT OR IGNORE INTO chat_members (channel_id, user_id, joined_at) VALUES (?,?,?)",
                    (ch_id, m["id"], now),
                )
            created.append(name)
        conn.commit()
    return {"created": created}


# ─── Helpers privés ──────────────────────────────────────────────────────────

def _assert_member(conn, channel_id: int, user_id: int) -> None:
    """Lève 403 si l'utilisateur n'est pas membre du canal."""
    row = conn.execute(
        "SELECT 1 FROM chat_members WHERE channel_id=? AND user_id=? LIMIT 1",
        (channel_id, user_id),
    ).fetchone()
    if not row:
        raise HTTPException(403, "Accès refusé à ce canal")
```

--- PARTIE 3 : Enregistrer dans main.py ---

Import  : from app.routers.chat import router as chat_router
Ajout   : app.include_router(chat_router)

--- PARTIE 4 : Initialiser les canaux par défaut ---

Après déploiement, appeler une fois :
  curl -X POST -b "sifa_token=..." http://localhost:8000/api/chat/channels/seed-defaults

Ou ajouter dans le lifespan de main.py (après le sync emplacements_plan) :
  try:
      from app.routers.chat import seed_default_channels_on_startup
      seed_default_channels_on_startup()
  except Exception as e:
      print(f"[MySifa] chat seed ignoré ({e})")

--- Vérification ---
  curl -b "sifa_token=..." http://localhost:8000/api/chat/channels
  → Doit retourner la liste des canaux dont l'utilisateur est membre
  curl -b "sifa_token=..." http://localhost:8000/api/chat/unread
  → Doit retourner {"unread": 0}
```

---

## Prompt 7 — Interface chat (/messages)

```
Contexte projet : MySifa. Le router /api/chat/* est opérationnel (créé au Prompt 6).
Design system : variables CSS --bg, --card, --border, --text, --text2, --muted, --accent, --danger.
Taille sidebar applicative : --sidebar-w = 260px. Même structure que les autres pages MySifa.
Polling : pas de WebSocket — requêtes GET toutes les 5s sur le canal actif.

Tâche : Créer la page /messages (chat interne complet).

Créer le fichier app/web/messages_page.py :

La page /messages doit avoir :
- Colonne gauche (280px) : liste des canaux et DMs avec badge non-lus
- Colonne centrale : fil de messages du canal actif + input
- En-tête : nom du canal / nom du correspondant DM
- Boutons : "Nouveau DM" (picker utilisateur), "Nouveau canal" (admin uniquement)

Structure HTML générale :

```html
<div id="chat-app">
  <!-- Sidebar MySifa (identique aux autres pages, lien /messages actif) -->
  <div id="chat-wrap">
    <div id="chat-left">
      <div id="chat-left-head">
        <div class="chat-section-title">Canaux</div>
        <button id="btn-new-channel" title="Nouveau canal" onclick="openNewChannel()">+</button>
      </div>
      <div id="chat-channels-list"><!-- rendu par JS --></div>
      <div class="chat-section-title" style="margin-top:12px">Messages directs</div>
      <div id="chat-dms-list"><!-- rendu par JS --></div>
      <div id="chat-left-foot">
        <button onclick="openNewDm()">
          <!-- icône + --> Nouveau message
        </button>
      </div>
    </div>
    <div id="chat-main">
      <div id="chat-header"><!-- nom canal / DM + membres --></div>
      <div id="chat-messages"><!-- fil messages --></div>
      <div id="chat-input-area">
        <textarea id="chat-input" placeholder="Message…" rows="1"></textarea>
        <button id="chat-send"><!-- icône envoi --></button>
      </div>
    </div>
  </div>
</div>
```

CSS à respecter :
- Layout : grid 3 colonnes (sidebar MySifa | liste canaux | messages)
- Liste canaux : fond --card, bordure droite --border, overflow-y auto
- Item canal actif : background var(--accent-bg), color var(--accent), font-weight 700
- Badge non-lu : fond var(--danger), texte blanc, border-radius 20px, font-size 9px
- Messages : même style que le composant initMsgThread (bubbles mine/theirs)
- Input : même style que #ai-input dans l'agent IA
- Pas d'emoji dans les labels fonctionnels

Comportement JS :

1. Au chargement : appeler GET /api/chat/channels, séparer canaux (type=channel)
   et DMs (type=direct), rendre les deux listes avec badge non-lus.

2. Clic sur un canal/DM : charger GET /api/chat/channels/{id}/messages,
   rendre les messages, démarrer le polling toutes les 5s (clearInterval si on change de canal).

3. Polling (5s) : GET /api/chat/channels/{id}/messages — si le dernier message_id
   reçu est différent du dernier connu, ajouter les nouveaux messages sans reconstruire tout le DOM.
   Aussi, toutes les 10s, rafraîchir la liste gauche pour mettre à jour les badges.

4. Envoi : POST /api/chat/channels/{id}/messages avec { body: texte }.
   Après succès, appeler load() pour rafraîchir immédiatement.

5. "Nouveau DM" : afficher un picker (modal ou inline) avec GET /api/chat/users.
   Searchbar pour filtrer par nom. Clic sur un utilisateur → POST /api/chat/channels
   avec { type: 'direct', user_id: id } → si existing:true, ouvrir le canal existant,
   sinon ouvrir le canal créé.

6. "Nouveau canal" (superadmin/direction/administration uniquement) :
   Modal avec champs : nom (requis), description (optionnel), membres (multi-select sur /api/chat/users).
   POST /api/chat/channels avec { type: 'channel', name, description, member_ids }.

7. "Charger plus" : bouton en haut du fil, appelle GET ...?before={oldest_created_at}.
   Insérer les messages au début du fil sans perdre la position de scroll.

8. Suppression message : bouton × visible au hover sur ses propres messages (ou admin).
   DELETE /api/chat/channels/{id}/messages/{msg_id} + retirer du DOM.

Python (router) :

```python
"""MySifa — Page Chat interne (/messages)."""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from config import APP_VERSION
from services.auth_service import get_current_user

router = APIRouter()

@router.get("/messages", response_class=HTMLResponse)
def messages_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/messages", status_code=302)
        raise
    import json
    html = (
        MESSAGES_HTML
        .replace("__V_LABEL__", f"v{APP_VERSION}")
        .replace("__USER_ID__", str(user.get("id", 0)))
        .replace('"__USER_NOM__"', json.dumps(user.get("nom") or ""))
        .replace('"__USER_ROLE__"', json.dumps(user.get("role") or ""))
    )
    return HTMLResponse(content=html)

MESSAGES_HTML = r"""
<!-- HTML complet de la page, généré selon les specs ci-dessus -->
<!-- Reprendre exactement la structure sidebar de html.py -->
<!-- window.__MYSIFA_UID__ = __USER_ID__; -->
<!-- window.__MYSIFA_NOM__ = "__USER_NOM__"; -->
<!-- window.__MYSIFA_ROLE__ = "__USER_ROLE__"; -->
"""
```

Enregistrer dans main.py :
  Import  : from app.web.messages_page import router as messages_page_router
  Ajout   : app.include_router(messages_page_router)

Ajouter le lien /messages dans la sidebar de toutes les pages existantes
(dans app/web/html.py, app/web/planning_page.py, app/web/fabrication_page.py, etc.)
avec un badge qui affiche le total non-lu via GET /api/chat/unread au chargement de page.

Icône suggérée pour la sidebar :
<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
  stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
</svg>
```

---

## Ordre d'exécution complet

| # | Prompt | Périmètre | Durée est. |
|---|--------|-----------|-----------|
| 1 | Migration DB + API commentaires contextuels | `/api/messaging/*` | 15 min |
| 2 | Composant JS thread réutilisable | `static/messaging_thread.js` | 10 min |
| 3 | Intégration planning | Modal `openEdit()` | 15 min |
| 4 | Intégration fabrication | Onglet "Commentaires" | 15 min |
| 5 | Badges sidebar + /inbox | `html.py` + page inbox | 20 min |
| 6 | DB + API chat (DMs + canaux) | `/api/chat/*` | 20 min |
| 7 | Interface /messages | Page chat complète | 45 min |

Les Prompts 1–5 (commentaires contextuels) sont indépendants des Prompts 6–7 (chat).
Commencer par 6 si le chat est la priorité ; commencer par 1 si les commentaires sur dossiers le sont.

## Points d'attention (tous prompts)

- Tester systématiquement en **thème light** (`body.light`).
- Le `no_dossier` dans fabrication est une **string** — `object_id` en DB est TEXT.
- Pour le chat (Prompt 7), le polling à **5s** est intentionnel pour un chat temps-quasi-réel
  sans WebSocket. Sur un VPS avec 10–20 utilisateurs simultanés, c'est négligeable.
- Les canaux par défaut (#général, #fabrication, #logistique) sont créés via
  `POST /api/chat/channels/seed-defaults` une seule fois après déploiement.
- `window.__MYSIFA_UID__` doit être un **entier** JS, pas une string.
  Utiliser `.replace("__USER_ID__", str(user["id"]))` sans guillemets dans le template HTML.

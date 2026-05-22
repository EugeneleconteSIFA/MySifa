# Cursor Prompts — Évolutions Messagerie MySifa v2

Prompts à exécuter dans l'ordre. Chacun est autonome et testable.

**Fonctionnalités couvertes :**
- Bouton `+` avec envoi de GIF (GIPHY)
- @mentions avec autocomplete et toast de notification
- Popup permission notifications navigateur
- Emoji de canal dans les réglages
- (Bonus) Réactions emoji UI frontend
- (Bonus) Modifier un message
- (Bonus) Épingler des messages

---

## Contexte (à coller en tête de chaque prompt)

```
Contexte général — MySifa :
MySifa est un outil de gestion de production industrielle pour SIFA.
FastAPI (Python 3) + SQLite. Frontend : HTML/CSS/JS vanilla généré en chaînes Python dans app/web/.
Config centrale : config.py à la racine (jamais app/config.py).
Import DB : `from database import get_db` (sqlite3.Connection avec row_factory = Row).
Auth : from services.auth_service import get_current_user → dict {id, nom, email, role, ...}.
Migrations DB : pattern `if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=N LIMIT 1").fetchone():`
La dernière migration est la v50. Les nouvelles migrations commencent à v51.
Seeds idempotents : toujours INSERT OR IGNORE.

Design system (variables CSS — jamais de couleurs en dur) :
--bg:#0a0e17 / --card:#111827 / --border:#1e293b / --text:#f1f5f9 / --text2:#cbd5e1
--muted:#94a3b8 / --accent:#22d3ee / --accent-bg:rgba(34,211,238,0.12)
--ok:#34d399 / --warn:#fbbf24 / --danger:#f87171
Police : 'Segoe UI', system-ui. Toasts via showToast(msg, type). Pas d'emojis dans les labels fonctionnels (SVG inline uniquement).
Thème light : body.light. Tester les deux thèmes.
Ton : professionnel, factuel, direct. Pas de "Bonjour !", pas de "Parfait !".

Fichier messagerie frontend : app/web/messages_page.py (HTML/CSS/JS inline, ~890 lignes)
Fichier API chat : app/routers/chat.py
Fichier migrations : app/core/database.py
```

---

## Prompt 1 — Migrations DB v51-v54

**Fichier à modifier : `app/core/database.py`, dans la fonction `_migrate()`.**
Ajouter les blocs suivants APRÈS le bloc de la migration v50.

### v51 — Emoji de canal
```python
if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=51 LIMIT 1").fetchone():
    cols = {r[1] for r in conn.execute("PRAGMA table_info(chat_channels)").fetchall()}
    if 'emoji' not in cols:
        conn.execute("ALTER TABLE chat_channels ADD COLUMN emoji TEXT DEFAULT NULL")
    conn.commit()
    _record_schema_migration(conn, 51, "chat_channels_emoji")
```

### v52 — Table chat_mentions
```python
if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=52 LIMIT 1").fetchone():
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_mentions (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id        INTEGER NOT NULL REFERENCES chat_messages(id) ON DELETE CASCADE,
            channel_id        INTEGER NOT NULL,
            mentioned_user_id INTEGER,
            is_all            INTEGER NOT NULL DEFAULT 0,
            created_at        TEXT    NOT NULL,
            read_at           TEXT    DEFAULT NULL
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_mentions_user ON chat_mentions(mentioned_user_id, read_at)"
    )
    conn.commit()
    _record_schema_migration(conn, 52, "chat_mentions")
```

### v53 — Préférences notifications utilisateur
```python
if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=53 LIMIT 1").fetchone():
    cols = {r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
    if 'notif_asked_at' not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN notif_asked_at TEXT DEFAULT NULL")
    if 'notif_browser' not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN notif_browser INTEGER NOT NULL DEFAULT 0")
    conn.commit()
    _record_schema_migration(conn, 53, "users_notif_prefs")
```

### v54 — Colonne edited_at sur chat_messages
```python
if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=54 LIMIT 1").fetchone():
    cols = {r[1] for r in conn.execute("PRAGMA table_info(chat_messages)").fetchall()}
    if 'edited_at' not in cols:
        conn.execute("ALTER TABLE chat_messages ADD COLUMN edited_at TEXT DEFAULT NULL")
    conn.commit()
    _record_schema_migration(conn, 54, "chat_messages_edited_at")
```

---

## Prompt 2 — Backend API (mentions, emoji canal, GIPHY proxy, notif prefs, edit)

**Fichier principal à modifier : `app/routers/chat.py`**
**Fichier `config.py` (racine) :** ajouter `GIPHY_API_KEY = os.getenv("GIPHY_API_KEY", "")` si la variable n'existe pas déjà.
**Fichier `.env` :** ajouter `GIPHY_API_KEY=votre_clé_ici` (clé gratuite sur developers.giphy.com).

### 2.1 — Inclure `emoji` et `mention_count` dans GET /api/chat/channels

Dans la fonction `list_channels`, modifier le SELECT pour ajouter :
- `c.emoji` dans les colonnes sélectionnées
- Une sous-requête `mention_count` :
```sql
(SELECT COUNT(*) FROM chat_mentions mn
 WHERE mn.channel_id = c.id
   AND mn.mentioned_user_id = ?
   AND mn.read_at IS NULL
) as mention_count
```
Passer `uid` en paramètre supplémentaire pour cette sous-requête. Le résultat doit inclure `emoji` et `mention_count` dans chaque canal retourné.

### 2.2 — Parsing des mentions à l'envoi d'un message

Dans la fonction `send_message` (route `POST /api/chat/channels/{channel_id}/messages`), après le `conn.commit()` final, ajouter un bloc try/except pour parser les mentions :

```python
try:
    if body:
        import re as _re
        now_m = _now_iso()
        members = conn.execute(
            """SELECT u.id, u.nom FROM chat_members cm
               JOIN users u ON u.id = cm.user_id
               WHERE cm.channel_id = ? AND u.id != ?""",
            (channel_id, user["id"])
        ).fetchall()
        msg_id = cur.lastrowid
        # @tous / @all → mentionner tous les membres
        if _re.search(r'@(tous|all)\b', body, _re.IGNORECASE):
            for m in members:
                conn.execute(
                    """INSERT INTO chat_mentions
                       (message_id, channel_id, mentioned_user_id, is_all, created_at)
                       VALUES (?,?,?,1,?)""",
                    (msg_id, channel_id, m["id"], now_m)
                )
        else:
            # @NomPrenom → correspondance sur le nom (insensible à la casse)
            tokens = _re.findall(r'@(\w+)', body)
            for token in tokens:
                for m in members:
                    if (m["nom"] or "").lower().startswith(token.lower()):
                        conn.execute(
                            """INSERT INTO chat_mentions
                               (message_id, channel_id, mentioned_user_id, is_all, created_at)
                               VALUES (?,?,?,0,?)""",
                            (msg_id, channel_id, m["id"], now_m)
                        )
                        break
        conn.commit()
except Exception:
    pass
```

### 2.3 — Route PATCH /api/chat/channels/{channel_id}

```python
@router.patch("/channels/{channel_id}")
async def update_channel(channel_id: int, request: Request):
    """Mettre à jour nom, description et emoji d'un canal. Réservé admins ou créateur."""
    user = _require(request)
    is_admin = user.get("role") in {"superadmin", "direction", "administration"}
    data = await request.json()
    with get_db() as conn:
        ch = conn.execute(
            "SELECT id, type, created_by FROM chat_channels WHERE id=? AND archived_at IS NULL LIMIT 1",
            (channel_id,)
        ).fetchone()
        if not ch:
            raise HTTPException(404, "Canal introuvable")
        if ch["type"] == "direct":
            raise HTTPException(400, "Impossible de modifier un DM")
        if not is_admin and ch["created_by"] != user["id"]:
            raise HTTPException(403, "Action réservée aux administrateurs ou au créateur")
        name = (data.get("name") or "").strip()
        description = (data.get("description") or "").strip() or None
        emoji = (data.get("emoji") or "").strip() or None
        if not name:
            raise HTTPException(400, "Nom requis")
        if len(name) > 60:
            raise HTTPException(400, "Nom trop long (max 60 caractères)")
        if emoji and len(emoji) > 4:
            raise HTTPException(400, "Emoji invalide")
        conn.execute(
            "UPDATE chat_channels SET name=?, description=?, emoji=? WHERE id=?",
            (name, description, emoji, channel_id)
        )
        conn.commit()
    return {"updated": True}
```

### 2.4 — Route GET /api/chat/mentions/unread

```python
@router.get("/mentions/unread")
def unread_mentions(request: Request):
    """Nombre total de mentions non lues pour l'utilisateur connecté."""
    user = _require(request)
    uid = user["id"]
    with get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as n FROM chat_mentions WHERE mentioned_user_id=? AND read_at IS NULL",
            (uid,)
        ).fetchone()
    return {"count": int(row["n"] if row else 0)}
```

### 2.5 — Route GET /api/chat/giphy/search

```python
@router.get("/giphy/search")
def giphy_search(request: Request, q: str = "", limit: int = 24):
    """Proxy GIPHY search. Nécessite GIPHY_API_KEY dans config.py."""
    _require(request)
    from config import GIPHY_API_KEY
    if not GIPHY_API_KEY:
        return {"data": [], "disabled": True}
    limit = max(1, min(int(limit), 48))
    try:
        import httpx
        r = httpx.get(
            "https://api.giphy.com/v1/gifs/search",
            params={"api_key": GIPHY_API_KEY, "q": q, "limit": limit, "rating": "pg", "lang": "fr"},
            timeout=8.0
        )
        r.raise_for_status()
        gifs = r.json().get("data", [])
    except Exception:
        raise HTTPException(502, "Erreur GIPHY")
    return {"data": [_fmt_gif(g) for g in gifs], "disabled": False}


@router.get("/giphy/trending")
def giphy_trending(request: Request, limit: int = 24):
    """Proxy GIPHY trending."""
    _require(request)
    from config import GIPHY_API_KEY
    if not GIPHY_API_KEY:
        return {"data": [], "disabled": True}
    limit = max(1, min(int(limit), 48))
    try:
        import httpx
        r = httpx.get(
            "https://api.giphy.com/v1/gifs/trending",
            params={"api_key": GIPHY_API_KEY, "limit": limit, "rating": "pg"},
            timeout=8.0
        )
        r.raise_for_status()
        gifs = r.json().get("data", [])
    except Exception:
        raise HTTPException(502, "Erreur GIPHY")
    return {"data": [_fmt_gif(g) for g in gifs], "disabled": False}


def _fmt_gif(g: dict) -> dict:
    images = g.get("images", {})
    preview = images.get("fixed_height_small", {}).get("url", "")
    original = images.get("original", {}).get("url", "")
    downsized = images.get("downsized", {}).get("url", original)
    return {
        "id": g.get("id", ""),
        "title": g.get("title", ""),
        "url": downsized or original,
        "preview_url": preview or downsized or original,
    }
```

Si `httpx` n'est pas installé, ajouter `httpx` dans `requirements.txt`.

### 2.6 — Support gif_url dans send_message

Dans `send_message`, dans le bloc `else` (JSON body, pas multipart), ajouter après la lecture du body :
```python
gif_url = (data.get("gif_url") or "").strip()
if gif_url:
    allowed_prefixes = (
        "https://media.giphy.com/",
        "https://media0.giphy.com/",
        "https://media1.giphy.com/",
        "https://media2.giphy.com/",
        "https://media3.giphy.com/",
        "https://media4.giphy.com/",
    )
    if not any(gif_url.startswith(p) for p in allowed_prefixes):
        raise HTTPException(400, "URL GIF non autorisée")
    att_url = gif_url
    att_name = "GIF"
    att_mime = "image/gif"
    att_size = 0
```
Adapter la condition `if not body and not upload` en `if not body and not upload and not gif_url`.

### 2.7 — Route PATCH /api/users/me/notif-prefs

```python
@router.patch("/notif-prefs")
async def update_notif_prefs(request: Request):
    """Enregistre la préférence notifications navigateur."""
    user = _require(request)
    data = await request.json()
    browser_notif = 1 if data.get("browser_notif") else 0
    now = _now_iso()
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET notif_browser=?, notif_asked_at=? WHERE id=?",
            (browser_notif, now, user["id"])
        )
        conn.commit()
    return {"ok": True}
```
**Note :** cette route doit être dans le router `chat` avec le prefix `/api/chat`, ou dans un router `users` avec le prefix `/api/users/me`. Choisir en cohérence avec le reste de l'app et mettre à jour l'URL côté frontend en conséquence.

### 2.8 — Route PATCH /api/chat/channels/{channel_id}/messages/{msg_id} (édition)

```python
@router.patch("/channels/{channel_id}/messages/{msg_id}")
async def edit_message(channel_id: int, msg_id: int, request: Request):
    """Modifier un message (auteur uniquement, 15 min max après envoi)."""
    user = _require(request)
    data = await request.json()
    new_body = (data.get("body") or "").strip()
    if not new_body:
        raise HTTPException(400, "Message vide")
    if len(new_body) > _MAX_BODY:
        raise HTTPException(400, f"Message trop long (max {_MAX_BODY} caractères)")
    with get_db() as conn:
        row = conn.execute(
            "SELECT user_id, created_at, deleted_at FROM chat_messages WHERE id=? AND channel_id=? LIMIT 1",
            (msg_id, channel_id)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Message introuvable")
        if row["deleted_at"]:
            raise HTTPException(410, "Message supprimé")
        if row["user_id"] != user["id"]:
            raise HTTPException(403, "Vous ne pouvez modifier que vos propres messages")
        try:
            from datetime import datetime as _dt
            sent = _dt.fromisoformat(row["created_at"])
            age = (_dt.now() - sent).total_seconds()
            if age > 900:
                raise HTTPException(403, "Modification impossible après 15 minutes")
        except HTTPException:
            raise
        except Exception:
            pass
        conn.execute(
            "UPDATE chat_messages SET body=?, edited_at=? WHERE id=?",
            (new_body, _now_iso(), msg_id)
        )
        conn.commit()
    return {"edited": True, "body": new_body}
```

Dans `_MSG_SELECT`, ajouter `m.edited_at` à la liste des colonnes.
Dans `_message_dict`, ajouter `"edited_at": row["edited_at"] or ""`.

---

## Prompt 3 — Frontend: Bouton "+" et GIF picker

**Fichier à modifier : `app/web/messages_page.py`**

### 3.1 — CSS (ajouter dans le bloc `<style>`, après les styles de `#chat-attach`)

```css
/* Bouton + et actions étendues */
#chat-action-expand {
  width:36px;height:36px;border-radius:8px;background:transparent;
  border:1px solid var(--border);cursor:pointer;display:flex;align-items:center;justify-content:center;
  flex-shrink:0;color:var(--text2);font-size:22px;font-weight:300;line-height:1;
  transition:border-color .15s,color .15s,background .15s;font-family:inherit;
}
#chat-action-expand.open,#chat-action-expand:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
#chat-action-btns{display:none;align-items:center;gap:6px;flex-shrink:0}
#chat-action-btns.show{display:flex}
#chat-gif-btn{
  font-size:11px;font-weight:800;padding:0 8px;color:var(--accent);
  border:1px solid var(--accent);border-radius:8px;height:36px;
  background:transparent;cursor:pointer;font-family:inherit;letter-spacing:.5px;
  transition:background .15s;
}
#chat-gif-btn:hover{background:var(--accent-bg)}
/* Picker GIF */
.chat-gif-grid{
  display:grid;grid-template-columns:repeat(3,1fr);gap:6px;
  max-height:260px;overflow-y:auto;margin-top:10px;
  scrollbar-width:thin;scrollbar-color:var(--border) transparent;
}
.chat-gif-item{border-radius:6px;overflow:hidden;cursor:pointer;aspect-ratio:1;background:var(--border)}
.chat-gif-item img{width:100%;height:100%;object-fit:cover;display:block}
.chat-gif-item:hover{opacity:.82}
```

### 3.2 — HTML de la zone de saisie

Remplacer l'intégralité du contenu de `<div id="chat-input-area" style="display:none">` par :

```html
<input type="file" id="chat-file-input" accept=".jpg,.jpeg,.png,.webp,.gif,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.zip">
<button type="button" id="chat-action-expand" aria-label="Plus d'options" onclick="toggleChatActions()">+</button>
<div id="chat-action-btns">
  <button type="button" id="chat-attach" aria-label="Pièce jointe" title="Pièce jointe" onclick="document.getElementById('chat-file-input').click()">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>
  </button>
  <button type="button" id="chat-gif-btn" aria-label="Envoyer un GIF" title="Envoyer un GIF" onclick="openGifPicker()">GIF</button>
</div>
<div id="chat-input-wrap" style="flex:1;min-width:0;position:relative">
  <div id="mention-dropdown" style="display:none"></div>
  <textarea id="chat-input" placeholder="Message…" rows="1" aria-label="Message"></textarea>
</div>
<button type="button" id="chat-send" aria-label="Envoyer" onclick="sendMessage()">
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
</button>
```

**Important :** retirer `flex:1` du style de `#chat-input` (il est maintenant sur `#chat-input-wrap`). Mettre à jour la règle CSS de `#chat-input` pour qu'il fasse `width:100%` au lieu de `flex:1`.

### 3.3 — JS : fonctions bouton + et GIF picker

Ajouter dans le bloc `<script>` :

```javascript
// ── Bouton + ──────────────────────────────────────────────
function toggleChatActions(){
  const btns=document.getElementById('chat-action-btns');
  const btn=document.getElementById('chat-action-expand');
  const isOpen=btns.classList.contains('show');
  if(isOpen){closeChatActions();}
  else{btns.classList.add('show');btn.classList.add('open');}
}
function closeChatActions(){
  document.getElementById('chat-action-btns').classList.remove('show');
  document.getElementById('chat-action-expand').classList.remove('open');
}
// Fermer le menu si on focus le textarea
document.getElementById('chat-input').addEventListener('focus',()=>{
  if(document.getElementById('chat-action-btns').classList.contains('show'))closeChatActions();
});

// ── GIF picker ────────────────────────────────────────────
async function openGifPicker(){
  closeChatActions();
  const overlay=document.createElement('div');
  overlay.className='chat-modal-overlay';
  overlay.onclick=e=>{if(e.target===overlay)closeModal();};
  overlay.innerHTML=
    '<div class="chat-modal" role="dialog" style="width:min(500px,100%)">'+
    '<h3>GIF</h3>'+
    '<input type="search" id="gif-search" placeholder="Rechercher un GIF…" autocomplete="off" style="width:100%;margin-bottom:4px">'+
    '<div id="gif-grid" class="chat-gif-grid"><p style="grid-column:1/-1;text-align:center;color:var(--muted);font-size:12px;padding:20px 0">Chargement…</p></div>'+
    '</div>';
  document.getElementById('mroot').appendChild(overlay);
  requestAnimationFrame(()=>document.getElementById('gif-search')?.focus());
  loadGifs('');
  let gifDebounce=null;
  document.getElementById('gif-search').oninput=function(){
    clearTimeout(gifDebounce);
    gifDebounce=setTimeout(()=>loadGifs(this.value.trim()),400);
  };
}

async function loadGifs(q){
  const grid=document.getElementById('gif-grid');
  if(!grid)return;
  grid.innerHTML='<p style="grid-column:1/-1;text-align:center;color:var(--muted);font-size:12px;padding:20px 0">Chargement…</p>';
  try{
    const ep=q?'/api/chat/giphy/search?q='+encodeURIComponent(q):'/api/chat/giphy/trending';
    const res=await api(ep);
    if(res.disabled){
      grid.innerHTML='<p style="grid-column:1/-1;text-align:center;color:var(--muted);font-size:12px;padding:20px 0">GIFs non activés — configurer GIPHY_API_KEY.</p>';
      return;
    }
    const gifs=res.data||[];
    if(!gifs.length){
      grid.innerHTML='<p style="grid-column:1/-1;text-align:center;color:var(--muted);font-size:12px;padding:20px 0">Aucun résultat.</p>';
      return;
    }
    grid.innerHTML=gifs.map(g=>
      '<div class="chat-gif-item" onclick="selectGif(\''+esc(g.url)+'\')">'+
      '<img src="'+esc(g.preview_url||g.url)+'" alt="'+esc(g.title||'GIF')+'" loading="lazy"></div>'
    ).join('');
  }catch(e){
    if(grid)grid.innerHTML='<p style="grid-column:1/-1;text-align:center;color:var(--danger);font-size:12px;padding:20px 0">Erreur de chargement.</p>';
  }
}

async function selectGif(gifUrl){
  closeModal();
  if(!activeId)return;
  const btn=document.getElementById('chat-send');
  if(btn)btn.disabled=true;
  try{
    await api('/api/chat/channels/'+activeId+'/messages',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({body:'',gif_url:gifUrl})
    });
    await loadMessages(false);
  }catch(e){
    showToast(e.message||'Envoi impossible','danger');
  }finally{
    if(btn)btn.disabled=false;
  }
}
```

Dans la fonction `sendMessage()`, après `inp.value=''`, ajouter `closeChatActions();`.

---

## Prompt 4 — Frontend: @mentions autocomplete + toast notification

**Fichier à modifier : `app/web/messages_page.py`**

### 4.1 — CSS (ajouter dans le bloc `<style>`)

```css
/* @mentions dropdown */
#mention-dropdown{
  position:absolute;bottom:calc(100% + 4px);left:0;right:0;
  background:var(--card);border:1px solid var(--border);border-radius:10px;
  max-height:200px;overflow-y:auto;z-index:200;
  box-shadow:0 8px 32px rgba(0,0,0,.35);
}
.mention-item{
  display:flex;align-items:center;gap:8px;padding:9px 12px;cursor:pointer;
  font-size:13px;color:var(--text);border-bottom:1px solid var(--border);
}
.mention-item:last-child{border-bottom:none}
.mention-item:hover,.mention-item.focused{background:var(--accent-bg);color:var(--accent)}
.mention-item .mi-name{font-weight:600}
.mention-item .mi-role{font-size:11px;color:var(--muted)}
/* Badge @mention sur canal */
.chat-mention-badge{
  flex-shrink:0;min-width:18px;height:16px;padding:0 5px;border-radius:20px;
  background:var(--warn);color:#0a0e17;font-size:9px;font-weight:800;
  display:inline-flex;align-items:center;justify-content:center;margin-left:2px;
}
.chat-mention-badge.hidden{display:none}
/* Toast @mention (apparaît en haut, centré) */
.mention-toast{
  position:fixed;top:20px;left:50%;transform:translateX(-50%);z-index:10002;
  background:var(--card);border:1px solid var(--warn);border-radius:12px;
  padding:12px 18px;font-size:13px;font-weight:600;color:var(--text);
  box-shadow:0 10px 36px rgba(0,0,0,.45);max-width:360px;width:calc(100% - 40px);
  text-align:center;animation:toast-in .2s ease;cursor:pointer;
}
```

### 4.2 — Variables JS à ajouter (avec les autres variables en haut du `<script>`)

```javascript
let channelMembers = [];
let mentionQuery = null;
let mentionStart = 0;
let mentionFocusIdx = -1;
```

### 4.3 — Chargement des membres dans selectChannel()

Dans `selectChannel(id)`, après `await loadMessages(true)`, ajouter :
```javascript
try{
  channelMembers = await api('/api/chat/channels/'+id+'/members')||[];
}catch(e){ channelMembers=[]; }
```

### 4.4 — Autocomplétion @mention

Remplacer le listener `input` existant de `#chat-input` par :
```javascript
document.getElementById('chat-input').addEventListener('input',function(){
  this.style.height='auto';
  this.style.height=Math.min(this.scrollHeight,80)+'px';
  // Détection @ pour mention
  const val=this.value;
  const cur=this.selectionStart;
  const before=val.substring(0,cur);
  const atMatch=before.match(/@(\w*)$/);
  if(atMatch){
    mentionQuery=atMatch[1].toLowerCase();
    mentionStart=before.lastIndexOf('@');
    renderMentionDropdown();
  }else{
    closeMentionDropdown();
  }
});
```

### 4.5 — Fonctions mention dropdown

```javascript
function renderMentionDropdown(){
  const dd=document.getElementById('mention-dropdown');
  if(!dd)return;
  const q=mentionQuery||'';
  const myUid=window.__MYSIFA_UID__;
  const candidates=[
    {id:'all',nom:'tous',role:'Mentionner tout le canal'},
    ...channelMembers.filter(m=>m.user_id!==myUid)
  ].filter(m=>{
    const name=(m.id==='all'?'tous':m.nom||'').toLowerCase();
    return !q||name.startsWith(q);
  }).slice(0,8);
  if(!candidates.length){closeMentionDropdown();return;}
  mentionFocusIdx=-1;
  dd.style.display='';
  dd.innerHTML=candidates.map((m,i)=>
    '<div class="mention-item" data-idx="'+i+'" data-nom="'+(m.id==='all'?'tous':esc(m.nom))+'" onclick="insertMention(\''+(m.id==='all'?'tous':esc(m.nom))+'\')">'+
    '<span class="mi-name">'+(m.id==='all'?'@tous':'@'+esc(m.nom))+'</span>'+
    '<span class="mi-role">'+esc(m.id==='all'?'Tout le canal':ROLE_LABELS[m.role]||m.role||'')+'</span>'+
    '</div>'
  ).join('');
}
function closeMentionDropdown(){
  mentionQuery=null;
  const dd=document.getElementById('mention-dropdown');
  if(dd)dd.style.display='none';
}
function insertMention(nom){
  const inp=document.getElementById('chat-input');
  const val=inp.value;
  const before=val.substring(0,mentionStart);
  const after=val.substring(inp.selectionStart);
  inp.value=before+'@'+nom+' '+after;
  inp.focus();
  const pos=before.length+nom.length+2;
  inp.setSelectionRange(pos,pos);
  closeMentionDropdown();
}
document.addEventListener('click',e=>{
  if(!e.target.closest('#chat-input-wrap')&&!e.target.closest('#mention-dropdown'))closeMentionDropdown();
});
```

### 4.6 — Navigation clavier dans le dropdown

Dans le listener `keydown` existant de `#chat-input`, **avant** la vérification `Enter` pour envoyer, ajouter :
```javascript
if(mentionQuery!==null&&document.getElementById('mention-dropdown').style.display!=='none'){
  const items=document.querySelectorAll('.mention-item');
  if(e.key==='ArrowDown'){
    e.preventDefault();
    mentionFocusIdx=Math.min(mentionFocusIdx+1,items.length-1);
    items.forEach((el,i)=>el.classList.toggle('focused',i===mentionFocusIdx));
    return;
  }
  if(e.key==='ArrowUp'){
    e.preventDefault();
    mentionFocusIdx=Math.max(mentionFocusIdx-1,0);
    items.forEach((el,i)=>el.classList.toggle('focused',i===mentionFocusIdx));
    return;
  }
  if(e.key==='Enter'&&mentionFocusIdx>=0){
    e.preventDefault();
    const nom=items[mentionFocusIdx]?.dataset.nom;
    if(nom)insertMention(nom);
    return;
  }
  if(e.key==='Escape'){closeMentionDropdown();return;}
}
```

### 4.7 — Highlight des @mentions dans les bulles

Dans `buildMsgEl(m)`, sur la ligne qui construit `bubble` à partir du texte (après `let bubble=body?esc(body):''`), ajouter :
```javascript
bubble=bubble.replace(/@(\w+)/g,'<span style="color:var(--accent);font-weight:700">@$1</span>');
```

### 4.8 — Toast @mention à la réception

Dans `pollMessages()`, après `appendNewMessages(fresh)`, ajouter :
```javascript
fresh.filter(m=>!m.is_mine).forEach(m=>{
  const myNom=(window.__MYSIFA_NOM__||'').toLowerCase().replace(/\s/g,'');
  const body=(m.body||'').toLowerCase();
  const mentioned=body.includes('@'+myNom)||body.includes('@tous')||body.includes('@all');
  if(mentioned)showMentionToast(m.user_nom,m.body,activeId);
});
```

Ajouter la fonction :
```javascript
function showMentionToast(from,body,chanId){
  const existing=document.querySelector('.mention-toast');
  if(existing)existing.remove();
  const t=document.createElement('div');
  t.className='mention-toast';
  const ch=channels.find(c=>c.id===chanId);
  const chanName=ch?(ch.display_name||ch.name||'Canal'):'Canal';
  t.innerHTML=
    '<div style="font-size:11px;color:var(--warn);font-weight:700;margin-bottom:4px">Mention · '+esc(chanName)+'</div>'+
    '<div style="color:var(--text2)">'+esc(from)+' : '+esc((body||'').substring(0,80))+'</div>';
  t.onclick=()=>{t.remove();selectChannel(chanId);};
  document.body.appendChild(t);
  setTimeout(()=>t.remove(),6000);
}
```

### 4.9 — Badge @mention dans la liste des canaux

Dans `renderChannelLists()`, dans la fonction `mkItem(c)`, ajouter :
```javascript
const mCount=Number(c.mention_count)||0;
const mBadge=mCount>0?'<span class="chat-mention-badge">@</span>':'';
```
Insérer `mBadge` à côté du badge de non-lus, à l'intérieur du `.chat-chan-body` ou en dehors, après le badge unread.

Également afficher l'emoji du canal dans son nom :
```javascript
const chanEmoji=(c.emoji&&c.type==='channel')?'<span style="margin-right:5px">'+esc(c.emoji)+'</span>':'';
// Dans chat-chan-name : chanEmoji + esc(c.display_name||...)
```

---

## Prompt 5 — Frontend: Popup permission notifications navigateur

**Fichier à modifier : `app/web/messages_page.py`**

**Contexte :** les utilisateurs n'entendent pas le son do-mi car l'AudioContext nécessite une interaction utilisateur pour se déverrouiller. Ce popup résout les deux problèmes en même temps : déverrouillage du son ET activation des notifications navigateur.

### 5.1 — CSS

```css
#notif-perm-modal{
  position:fixed;inset:0;z-index:20000;background:rgba(0,0,0,.7);
  display:flex;align-items:center;justify-content:center;padding:20px;
}
.notif-perm-card{
  background:var(--card);border:1px solid var(--border);border-radius:16px;
  padding:28px 24px;width:min(380px,100%);text-align:center;
  box-shadow:0 24px 64px rgba(0,0,0,.5);
}
.notif-perm-card h2{margin:0 0 8px;font-size:16px;font-weight:700;color:var(--text)}
.notif-perm-card p{margin:0 0 20px;font-size:13px;color:var(--text2);line-height:1.6}
.notif-perm-actions{display:flex;gap:10px;justify-content:center}
.notif-perm-actions button{
  padding:10px 20px;border-radius:10px;font-size:13px;font-weight:700;
  cursor:pointer;font-family:inherit;border:1px solid var(--border);
  background:transparent;color:var(--text2);transition:border-color .15s;
}
.notif-perm-actions button.primary{background:var(--accent);color:var(--bg);border-color:var(--accent)}
.notif-perm-actions button:hover:not(.primary){border-color:var(--muted)}
```

### 5.2 — HTML

Ajouter juste avant `<div id="mroot"></div>` :
```html
<div id="notif-perm-modal" style="display:none" role="dialog" aria-modal="true" aria-label="Notifications">
  <div class="notif-perm-card">
    <div style="margin-bottom:14px">
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
    </div>
    <h2>Notifications</h2>
    <p>Recevoir des alertes quand vous recevez un message ou êtes mentionné, même si l'onglet est en arrière-plan ?</p>
    <div class="notif-perm-actions">
      <button type="button" onclick="dismissNotifPerm(false)">Non merci</button>
      <button type="button" class="primary" onclick="dismissNotifPerm(true)">Activer</button>
    </div>
  </div>
</div>
```

### 5.3 — JS

```javascript
const NOTIF_PERM_KEY='mysifa_notif_asked_v1';

function checkNotifPermission(){
  if(localStorage.getItem(NOTIF_PERM_KEY))return;
  if(typeof Notification!=='undefined'&&Notification.permission!=='default')return;
  setTimeout(()=>{
    document.getElementById('notif-perm-modal').style.display='flex';
  },3500);
}

async function dismissNotifPerm(enable){
  document.getElementById('notif-perm-modal').style.display='none';
  localStorage.setItem(NOTIF_PERM_KEY,'1');
  // Déverrouille l'AudioContext — cette interaction utilisateur suffit
  try{_getAudioCtx();}catch(e){}
  const granted=false;
  if(enable){
    try{
      const perm=await Notification.requestPermission();
      // Remplacer l'URL ci-dessous selon le router choisi au Prompt 2.7
      await api('/api/chat/notif-prefs',{
        method:'PATCH',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({browser_notif:perm==='granted'})
      });
    }catch(e){}
  }else{
    try{
      await api('/api/chat/notif-prefs',{
        method:'PATCH',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({browser_notif:false})
      });
    }catch(e){}
  }
}

function sendBrowserNotif(title,body,channelId){
  if(typeof Notification==='undefined')return;
  if(Notification.permission!=='granted')return;
  if(document.visibilityState==='visible')return;
  try{
    const n=new Notification(title,{
      body:(body||'').substring(0,100),
      icon:'/static/mys_icon_192.png',
      tag:'chat-'+channelId,
    });
    n.onclick=()=>{window.focus();selectChannel(channelId);n.close();};
  }catch(e){}
}
```

Dans `pollMessages()`, après `playNotifSound()`, ajouter :
```javascript
const fresh2=fresh.filter(m=>!m.is_mine);
if(fresh2.length){
  const ch=channels.find(c=>c.id===activeId);
  const chanName=ch?(ch.display_name||ch.name||'Canal'):'Message';
  const latest=fresh2[fresh2.length-1];
  sendBrowserNotif(latest.user_nom+' · '+chanName,latest.body,activeId);
}
```

Appeler `checkNotifPermission()` dans la fonction `init()`, après `await loadChannels()`.

---

## Prompt 6 — Frontend: Emoji de canal et réglages

**Fichier à modifier : `app/web/messages_page.py`**

### 6.1 — Bouton réglages dans le header

Dans le HTML de `<div id="chat-header-top">`, ajouter un bouton après le bouton son :
```html
<button type="button" id="chan-settings-btn" class="hbtn" title="Réglages du canal"
  onclick="openChannelSettings()" style="display:none" aria-label="Réglages du canal">
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93l-1.41 1.41M4.93 4.93l1.41 1.41M21 12h-2M5 12H3M19.07 19.07l-1.41-1.41M4.93 19.07l1.41-1.41M12 21v-2M12 5V3"/></svg>
</button>
```

### 6.2 — Afficher l'emoji dans le header et la sidebar

Dans `selectChannel(id)` :
```javascript
// Header titre avec emoji
const ch=channels.find(c=>c.id===id);
if(ch){
  const emojiPfx=ch.emoji?ch.emoji+' ':(ch.type==='channel'?'':'');
  document.getElementById('chat-header-title').textContent=emojiPfx+(ch.display_name||ch.name||'Canal');
  // ...
  // Afficher/masquer le bouton réglages
  const sb=document.getElementById('chan-settings-btn');
  if(sb) sb.style.display=(ch.type==='channel'&&ADMIN_ROLES.has(window.__MYSIFA_ROLE__))?'':'none';
}
```

### 6.3 — Fonction openChannelSettings()

```javascript
async function openChannelSettings(){
  const ch=channels.find(c=>c.id===activeId);
  if(!ch||ch.type==='direct')return;
  const overlay=document.createElement('div');
  overlay.className='chat-modal-overlay';
  overlay.onclick=e=>{if(e.target===overlay)closeModal();};
  overlay.innerHTML=
    '<div class="chat-modal" role="dialog">'+
    '<h3>Réglages — '+esc(ch.display_name||ch.name||'Canal')+'</h3>'+
    '<label for="cs-emoji">Emoji du canal</label>'+
    '<input type="text" id="cs-emoji" maxlength="4" placeholder="ex. 🔧 📦 🔑" value="'+esc(ch.emoji||'')+'">'+
    '<p style="font-size:11px;color:var(--muted);margin:-8px 0 14px">Un seul emoji. Laissez vide pour aucun.</p>'+
    '<label for="cs-name">Nom</label>'+
    '<input type="text" id="cs-name" maxlength="60" value="'+esc(ch.name||'')+'">'+
    '<label for="cs-desc">Description</label>'+
    '<textarea id="cs-desc" rows="2">'+esc(ch.description||'')+'</textarea>'+
    '<div class="chat-modal-actions">'+
    '<button type="button" onclick="closeModal()">Annuler</button>'+
    '<button type="button" class="primary" id="cs-save-btn">Enregistrer</button>'+
    '</div></div>';
  document.getElementById('mroot').appendChild(overlay);
  document.getElementById('cs-save-btn').onclick=async()=>{
    const emoji=(document.getElementById('cs-emoji').value||'').trim();
    const name=(document.getElementById('cs-name').value||'').trim();
    const description=(document.getElementById('cs-desc').value||'').trim();
    if(!name){showToast('Nom requis','danger');return;}
    try{
      await api('/api/chat/channels/'+activeId,{
        method:'PATCH',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({emoji,name,description})
      });
      closeModal();
      await loadChannels();
      const upd=channels.find(c=>c.id===activeId);
      if(upd){
        const e2=upd.emoji?upd.emoji+' ':'';
        document.getElementById('chat-header-title').textContent=e2+(upd.display_name||upd.name||'Canal');
      }
      showToast('Canal mis à jour','success');
    }catch(e){showToast(e.message||'Erreur','danger');}
  };
  requestAnimationFrame(()=>document.getElementById('cs-emoji')?.focus());
}
```

---

## Prompt 7 (bonus) — Réactions emoji UI frontend

**Contexte :** le backend est déjà implémenté (`POST /api/chat/channels/{id}/messages/{id}/reactions`). Les emojis autorisés sont définis dans `_ALLOWED_EMOJIS = {"👍", "✅", "👀", "⚠️", "🔧", "❌"}`. Les messages reçus via l'API incluent déjà `reactions[]`.

**Fichier à modifier : `app/web/messages_page.py`**

### 7.1 — CSS

```css
/* Réactions */
.msg-reactions{display:flex;flex-wrap:wrap;gap:4px;margin-top:5px}
.react-chip{
  display:inline-flex;align-items:center;gap:4px;padding:2px 8px;border-radius:20px;
  border:1px solid var(--border);background:transparent;font-size:12px;cursor:pointer;
  font-family:inherit;transition:background .1s,border-color .1s;line-height:1.5;
}
.react-chip.mine{border-color:var(--accent);background:var(--accent-bg)}
.react-chip:hover{border-color:var(--accent);background:var(--accent-bg)}
.react-chip .rc-count{font-size:11px;color:var(--muted);font-weight:600}
.react-picker{
  display:none;position:absolute;
  background:var(--card);border:1px solid var(--border);border-radius:10px;
  padding:6px;box-shadow:0 8px 32px rgba(0,0,0,.35);z-index:100;white-space:nowrap;
}
.react-picker.show{display:flex;gap:4px}
.chat-msg.mine .react-picker{right:0}
.chat-msg.theirs .react-picker{left:0}
.react-pick-btn{
  font-size:18px;padding:4px 6px;border-radius:6px;border:none;
  background:transparent;cursor:pointer;line-height:1;
}
.react-pick-btn:hover{background:var(--accent-bg)}
```

### 7.2 — Modifier buildMsgEl()

Après la ligne `wrap.innerHTML = ...`, ajouter :
```javascript
// Chips réactions existantes
if(m.reactions&&m.reactions.length){
  const rDiv=document.createElement('div');
  rDiv.className='msg-reactions';
  m.reactions.forEach(r=>{
    const btn=document.createElement('button');
    btn.type='button';
    btn.className='react-chip'+(r.reacted_by_me?' mine':'');
    btn.title=(r.users||[]).slice(0,5).join(', ');
    btn.innerHTML=r.emoji+' <span class="rc-count">'+r.count+'</span>';
    btn.onclick=()=>toggleReaction(m.id,r.emoji);
    rDiv.appendChild(btn);
  });
  const bubble=wrap.querySelector('.chat-msg-bubble');
  if(bubble)bubble.after(rDiv);
}
// Picker emoji (au survol)
const picker=document.createElement('div');
picker.className='react-picker';
picker.style.position='absolute';
picker.style.top='-44px';
['👍','✅','👀','⚠️','🔧','❌'].forEach(emoji=>{
  const b=document.createElement('button');
  b.type='button';b.className='react-pick-btn';b.textContent=emoji;
  b.onclick=e=>{e.stopPropagation();picker.classList.remove('show');toggleReaction(m.id,emoji);};
  picker.appendChild(b);
});
wrap.style.position='relative';
wrap.appendChild(picker);
wrap.addEventListener('mouseenter',()=>picker.classList.add('show'));
wrap.addEventListener('mouseleave',()=>picker.classList.remove('show'));
```

### 7.3 — Fonction toggleReaction()

```javascript
async function toggleReaction(msgId,emoji){
  if(!activeId)return;
  try{
    await api('/api/chat/channels/'+activeId+'/messages/'+msgId+'/reactions',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({emoji})
    });
    await loadMessages(false);
  }catch(e){
    showToast(e.message||'Réaction impossible','danger');
  }
}
```

---

## Prompt 8 (bonus) — Modifier un message

**Fichier à modifier : `app/web/messages_page.py`**
**Prérequis :** Prompt 2 (route PATCH /messages/{id}) et migration v54 déjà appliqués.

### 8.1 — CSS

```css
.chat-msg-edit{
  position:absolute;top:-4px;right:20px;width:20px;height:20px;border-radius:50%;
  border:1px solid var(--border);background:var(--card);color:var(--muted);
  font-size:11px;line-height:1;cursor:pointer;display:none;align-items:center;justify-content:center;
  font-family:inherit;padding:0;
}
.chat-msg:hover .chat-msg-edit{display:flex}
.chat-msg.mine .chat-msg-edit{right:auto;left:20px}
.chat-msg-edited{font-size:10px;color:var(--muted);font-style:italic;margin-left:6px}
.msg-edit-area{
  width:100%;background:var(--bg);border:1px solid var(--accent);border-radius:8px;
  padding:8px 10px;color:var(--text);font-size:13px;font-family:inherit;
  resize:none;outline:none;min-height:36px;max-height:120px;line-height:1.4;
}
.msg-edit-actions{display:flex;gap:6px;margin-top:6px;justify-content:flex-end}
.msg-edit-actions button{
  padding:5px 12px;border-radius:7px;font-size:12px;font-weight:700;
  cursor:pointer;font-family:inherit;border:1px solid var(--border);background:transparent;color:var(--text2);
}
.msg-edit-actions button.primary{background:var(--accent);color:var(--bg);border-color:var(--accent)}
```

### 8.2 — Modifier buildMsgEl()

Dans la construction de `wrap.innerHTML`, modifier la condition `canDel` et ajouter le bouton edit :
```javascript
const msgAge=Date.now()-new Date((m.created_at||'').replace(' ','T')).getTime();
const canEdit=m.is_mine&&!m.attachment_url&&msgAge<900000;

// Ajouter dans innerHTML après le bouton delete :
// (canEdit ? '<button type="button" class="chat-msg-edit" title="Modifier" onclick="startEdit('+m.id+')">✎</button>' : '')

// Afficher "(modifié)" si edited_at :
// Dans le label ou après la bulle : (m.edited_at ? '<span class="chat-msg-edited">(modifié)</span>' : '')
```

### 8.3 — Fonction startEdit()

```javascript
function startEdit(msgId){
  const wrap=document.querySelector('.chat-msg[data-id="'+msgId+'"]');
  if(!wrap)return;
  const bubble=wrap.querySelector('.chat-msg-bubble');
  if(!bubble)return;
  const msg=messages.find(m=>m.id===msgId);
  if(!msg)return;
  const originalText=msg.body||'';
  const originalHtml=bubble.innerHTML;
  bubble.innerHTML=
    '<textarea class="msg-edit-area" id="edit-ta-'+msgId+'">'+esc(originalText)+'</textarea>'+
    '<div class="msg-edit-actions">'+
    '<button type="button" onclick="cancelEdit(\''+msgId+'\',\''+encodeURIComponent(originalHtml)+'\')">Annuler</button>'+
    '<button type="button" class="primary" onclick="saveEdit('+msgId+')">Enregistrer</button>'+
    '</div>';
  requestAnimationFrame(()=>{
    const ta=document.getElementById('edit-ta-'+msgId);
    if(ta){ta.focus();ta.style.height=ta.scrollHeight+'px';}
  });
}

function cancelEdit(msgId,originalHtml){
  const wrap=document.querySelector('.chat-msg[data-id="'+msgId+'"]');
  if(!wrap)return;
  const bubble=wrap.querySelector('.chat-msg-bubble');
  if(bubble)bubble.innerHTML=decodeURIComponent(originalHtml);
}

async function saveEdit(msgId){
  const ta=document.getElementById('edit-ta-'+msgId);
  if(!ta)return;
  const newBody=ta.value.trim();
  if(!newBody){showToast('Message vide','danger');return;}
  try{
    await api('/api/chat/channels/'+activeId+'/messages/'+msgId,{
      method:'PATCH',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({body:newBody})
    });
    await loadMessages(false);
    showToast('Message modifié','success');
  }catch(e){
    showToast(e.message||'Modification impossible','danger');
  }
}
```

---

## Prompt 9 (bonus) — Épingler des messages

**Fichiers à modifier : `app/routers/chat.py` et `app/web/messages_page.py`**

### 9.1 — Migration v55 (ajouter dans database.py)

```python
if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=55 LIMIT 1").fetchone():
    cols = {r[1] for r in conn.execute("PRAGMA table_info(chat_messages)").fetchall()}
    if 'pinned_at' not in cols:
        conn.execute("ALTER TABLE chat_messages ADD COLUMN pinned_at TEXT DEFAULT NULL")
    if 'pinned_by' not in cols:
        conn.execute("ALTER TABLE chat_messages ADD COLUMN pinned_by INTEGER DEFAULT NULL")
    conn.commit()
    _record_schema_migration(conn, 55, "chat_messages_pin")
```

### 9.2 — Routes backend (dans chat.py)

```python
@router.post("/channels/{channel_id}/messages/{msg_id}/pin")
def pin_message(channel_id: int, msg_id: int, request: Request):
    user = _require(request)
    is_admin = user.get("role") in {"superadmin", "direction", "administration"}
    with get_db() as conn:
        ch = conn.execute(
            "SELECT created_by FROM chat_channels WHERE id=? AND archived_at IS NULL LIMIT 1",
            (channel_id,)
        ).fetchone()
        if not ch:
            raise HTTPException(404, "Canal introuvable")
        if not is_admin and ch["created_by"] != user["id"]:
            raise HTTPException(403, "Réservé aux administrateurs ou au créateur du canal")
        msg = conn.execute(
            "SELECT id FROM chat_messages WHERE id=? AND channel_id=? AND deleted_at IS NULL LIMIT 1",
            (msg_id, channel_id)
        ).fetchone()
        if not msg:
            raise HTTPException(404, "Message introuvable")
        conn.execute(
            "UPDATE chat_messages SET pinned_at=?, pinned_by=? WHERE id=?",
            (_now_iso(), user["id"], msg_id)
        )
        conn.commit()
    return {"pinned": True}


@router.delete("/channels/{channel_id}/messages/{msg_id}/pin")
def unpin_message(channel_id: int, msg_id: int, request: Request):
    user = _require(request)
    is_admin = user.get("role") in {"superadmin", "direction", "administration"}
    with get_db() as conn:
        ch = conn.execute(
            "SELECT created_by FROM chat_channels WHERE id=? LIMIT 1", (channel_id,)
        ).fetchone()
        if not is_admin and (not ch or ch["created_by"] != user["id"]):
            raise HTTPException(403, "Réservé aux administrateurs")
        conn.execute(
            "UPDATE chat_messages SET pinned_at=NULL, pinned_by=NULL WHERE id=? AND channel_id=?",
            (msg_id, channel_id)
        )
        conn.commit()
    return {"unpinned": True}


@router.get("/channels/{channel_id}/pinned")
def pinned_messages(channel_id: int, request: Request):
    user = _require(request)
    uid = user["id"]
    with get_db() as conn:
        _assert_member(conn, channel_id, uid)
        rows = conn.execute(
            f"""SELECT {_MSG_SELECT}
               FROM chat_messages m
               LEFT JOIN users u ON u.id = m.user_id
               WHERE m.channel_id=? AND m.pinned_at IS NOT NULL AND m.deleted_at IS NULL
               ORDER BY m.pinned_at DESC LIMIT 10""",
            (channel_id,)
        ).fetchall()
        reactions_map = _fetch_reactions_map(conn, [r["id"] for r in rows], uid)
    return [_message_dict(r, uid, reactions_map.get(r["id"], [])) for r in rows]
```

Ajouter `m.pinned_at, m.pinned_by` dans `_MSG_SELECT` et `_message_dict`.

### 9.3 — Frontend

**Bouton "Messages épinglés" dans le header :**
Ajouter un bouton `.hbtn` avec une icône punaise, visible sur les canaux (pas les DMs). Au clic → `openPinnedMessages()`.

**Style pour les messages épinglés :**
```css
.chat-msg.pinned .chat-msg-bubble{border-top:2px solid var(--warn)}
```

**Bouton épingler dans buildMsgEl :**
Pour les admins, ajouter un bouton "Épingler/Désépingler" au hover.

**Fonction openPinnedMessages() :**
Ouvre un modal listant les messages épinglés via `GET /api/chat/channels/{id}/pinned`. Chaque message est affiché avec son texte, son auteur, et un bouton "Désépingler" pour les admins.

---

## Prompt 10 — Annonce de mise à jour

Exécuter une fois le déploiement fait, via `POST /api/updates` (authentifié en super admin) :

```json
{
  "scope": "messages",
  "titre": "Messagerie — GIFs, mentions et notifications",
  "active": true,
  "message": "<div style=\"font-size:13px;line-height:1.7;color:var(--text2)\"><div style=\"font-size:15px;font-weight:700;color:var(--text);margin-bottom:12px\">Mise à jour — Messagerie</div><div style=\"margin-bottom:10px;font-weight:600;color:var(--text);font-size:12px;text-transform:uppercase;letter-spacing:.5px\">Nouveautés</div><ul style=\"margin:0 0 14px 0;padding-left:18px\"><li style=\"margin-bottom:5px\">Envoi de GIFs — cliquer sur + dans la barre de saisie, puis GIF.</li><li style=\"margin-bottom:5px\">Mentions — taper @ pour taguer un collègue. @tous pour tout le canal.</li><li style=\"margin-bottom:5px\">Notifications navigateur — une demande d'activation s'affichera automatiquement.</li><li style=\"margin-bottom:5px\">Emoji de canal — les administrateurs peuvent personnaliser l'icône de chaque canal depuis les réglages.</li></ul><div style=\"margin-top:14px;padding-top:12px;border-top:1px solid var(--border);font-size:11px;color:var(--muted);line-height:1.6\">Vos retours sont les bienvenus.<br><span style=\"color:var(--text2);font-weight:600\">Eugène</span></div></div>"
}
```

---

## Notes d'implémentation

**Ordre recommandé :** Prompt 1 → Prompt 2 → Prompt 3 → Prompt 4 → Prompt 5 → Prompt 6, puis les bonus dans n'importe quel ordre.

**Clé GIPHY :** compte gratuit sur [developers.giphy.com](https://developers.giphy.com) → créer une app → copier la clé dans `.env` sous `GIPHY_API_KEY=...`. La limite gratuite (1000 req/h) est largement suffisante pour un usage interne.

**`httpx` :** si non présent, ajouter `httpx` dans `requirements.txt` et relancer `pip install -r requirements.txt`.

**Règles DB :** ne jamais modifier `DB_PATH` dans `.env`. Les migrations sont idempotentes — safe de les relancer.

**Thème light :** après chaque prompt, tester avec `body.light` que les couleurs restent lisibles (notamment les badges, le toast mention, et les chips réactions).

"""MySifa — Page Chat interne (/messages)."""

import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import APP_VERSION
from services.auth_service import get_current_user

router = APIRouter()


@router.get("/messages", response_class=HTMLResponse)
def messages_page(request: Request):
    """Redirection — le chat est dans le widget flottant."""
    return RedirectResponse(url="/", status_code=302)


MESSAGES_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17">
<title>Messages — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="stylesheet" href="/static/mysifa_theme.css">
<link rel="stylesheet" href="/static/mysifa_user_chip.css">
<link rel="stylesheet" href="/static/mysifa_chat_nav.css">
<link rel="stylesheet" href="/static/support_widget.css">
<style>
:root{
  --bg:#0a0e17;--card:#111827;--border:#1e293b;
  --text:#f1f5f9;--text2:#cbd5e1;--muted:#94a3b8;
  --accent:#22d3ee;--accent-bg:rgba(34,211,238,0.12);
  --ok:#34d399;--warn:#fbbf24;--danger:#f87171;
  --sidebar-w:260px;
}
body.light{
  --bg:#f1f5f9;--card:#fff;--border:#e2e8f0;
  --text:#0f172a;--text2:#475569;--muted:#64748b;
  --accent:#0891b2;--accent-bg:rgba(8,145,178,0.10);
  --ok:#059669;--danger:#dc2626;
}
*{box-sizing:border-box}
body{margin:0;font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
#chat-app{display:flex;min-height:100vh}
.sidebar{
  width:var(--sidebar-w);background:var(--card);border-right:1px solid var(--border);
  padding:20px 12px;display:flex;flex-direction:column;flex-shrink:0;
  height:100vh;position:sticky;top:0;overflow-y:auto;scrollbar-width:none;
}
.sidebar::-webkit-scrollbar{width:0}
.logo{padding:0 8px;margin-bottom:24px}
.logo-brand{font-size:15px;font-weight:800}.logo-brand span{color:var(--accent)}
.logo-sub{font-size:10px;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase;margin-top:2px}
.nav-btn{
  display:flex;align-items:center;gap:10px;width:100%;text-align:left;
  padding:10px 12px;border-radius:8px;border:none;background:transparent;
  color:var(--text2);font-size:13px;font-weight:500;cursor:pointer;
  font-family:inherit;transition:background .15s,color .15s;margin-bottom:2px;
}
.nav-btn:hover,.nav-btn.active{background:var(--accent-bg);color:var(--accent)}
.back-mysifa{border:none!important;background:transparent!important;font-weight:400!important;color:var(--text2)!important;padding:8px 10px!important}
.back-mysifa .wm{font-weight:800;color:var(--text)}.back-mysifa .wm span{color:var(--accent)}
.sidebar-bottom{margin-top:auto;display:flex;flex-direction:column;gap:6px;padding-bottom:8px}
.user-chip{padding:10px 12px;border-radius:8px;background:var(--accent-bg);cursor:pointer}
.user-chip .uc-name{font-size:12px;font-weight:600;color:var(--text)}
.user-chip .uc-role{font-size:10px;color:var(--accent);text-transform:uppercase;letter-spacing:.5px}
.theme-btn,.logout-btn{
  display:flex;align-items:center;gap:8px;padding:10px 12px;border-radius:8px;
  border:1px solid var(--border);background:transparent;color:var(--text2);
  cursor:pointer;font-size:12px;width:100%;font-family:inherit;
}
.logout-btn{border:none}.logout-btn:hover{color:var(--danger);background:rgba(248,113,113,.1)}
.version{font-size:10px;color:var(--muted);font-family:monospace;padding:4px 12px}
#chat-wrap{flex:1;display:flex;min-width:0;min-height:100vh}
#chat-left{
  width:280px;flex-shrink:0;background:var(--card);border-right:1px solid var(--border);
  display:flex;flex-direction:column;min-height:100vh;overflow:hidden;
}
.chat-list-section{display:flex;flex-direction:column;flex:1;min-height:0;overflow:hidden}
.chat-list-section-dms{border-top:1px solid var(--border)}
#chat-left-head,#chat-dm-head{
  display:flex;align-items:center;justify-content:space-between;gap:8px;
  padding:14px 12px 8px;flex-shrink:0;
}
.chat-section-title{font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.6px;padding:0 4px}
#btn-new-channel{
  width:28px;height:28px;border-radius:8px;border:1px solid var(--border);
  background:transparent;color:var(--text2);cursor:pointer;font-size:16px;
  font-weight:700;line-height:1;font-family:inherit;
}
#btn-new-channel:hover{border-color:var(--accent);color:var(--accent)}
#chat-channels-list,#chat-dms-list{overflow-y:auto;padding:4px 6px;flex:1;min-height:0;scrollbar-width:thin;scrollbar-color:var(--border) transparent}
#chat-left-foot{padding:10px 12px;border-top:1px solid var(--border);flex-shrink:0}
#chat-left-foot button{
  width:100%;display:flex;align-items:center;justify-content:center;gap:8px;
  padding:10px;border-radius:10px;border:1px solid var(--border);
  background:var(--accent-bg);color:var(--accent);font-size:12px;font-weight:700;
  cursor:pointer;font-family:inherit;
}
#chat-left-foot button:hover{filter:brightness(1.05)}
.chat-chan-item{
  display:flex;align-items:flex-start;gap:8px;width:100%;text-align:left;
  padding:10px 10px;border-radius:8px;border:none;background:transparent;
  color:var(--text2);cursor:pointer;font-family:inherit;font-size:13px;
  transition:background .15s,color .15s;
}
.chat-chan-item:hover{background:var(--accent-bg);color:var(--text)}
.chat-chan-item.active{background:var(--accent-bg);color:var(--accent);font-weight:700}
.chat-chan-body{flex:1;min-width:0}
.chat-chan-name{font-size:13px;font-weight:inherit;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.chat-chan-preview{font-size:11px;color:var(--muted);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-weight:400}
.chat-unread-badge{
  flex-shrink:0;min-width:18px;height:16px;padding:0 5px;border-radius:20px;
  background:var(--danger);color:#fff;font-size:9px;font-weight:800;
  display:inline-flex;align-items:center;justify-content:center;
}
.chat-unread-badge.hidden{display:none}
#chat-main{flex:1;display:flex;flex-direction:column;min-width:0;background:var(--bg)}
#chat-header{
  padding:14px 18px;border-bottom:1px solid var(--border);background:var(--card);
  flex-shrink:0;
}
#chat-header-top{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}
#chat-header-titles{flex:1;min-width:0}
#chat-header-title{font-size:15px;font-weight:700;color:var(--text)}
#chat-header-sub{font-size:11px;color:var(--muted);margin-top:3px}
.hbtn{
  flex-shrink:0;width:36px;height:36px;border-radius:8px;border:1px solid var(--border);
  background:var(--bg);color:var(--text2);cursor:pointer;
  display:inline-flex;align-items:center;justify-content:center;
  transition:border-color .15s,color .15s,background .15s;
}
.hbtn:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
#chat-messages{
  flex:1;overflow-y:auto;padding:16px 18px;display:flex;flex-direction:column;
  gap:8px;scrollbar-width:thin;scrollbar-color:var(--border) transparent;
}
#chat-messages #chat-load-more{
  align-self:center;padding:6px 14px;border-radius:8px;border:1px solid var(--border);
  background:transparent;color:var(--text2);font-size:11px;font-weight:600;
  cursor:pointer;font-family:inherit;margin-bottom:8px;width:auto;
}
#chat-messages #chat-load-more:hover{border-color:var(--accent);color:var(--accent)}
#chat-empty{
  flex:1;display:flex;align-items:center;justify-content:center;
  color:var(--muted);font-size:13px;padding:40px;text-align:center;
}
.chat-msg{display:flex;flex-direction:column;max-width:78%;position:relative}
.chat-msg.mine{align-self:flex-end}
.chat-msg.theirs{align-self:flex-start}
.chat-msg-label{font-size:10px;color:var(--muted);margin-bottom:3px}
.chat-msg.mine .chat-msg-label{text-align:right}
.chat-msg-bubble{
  padding:8px 12px;border-radius:10px;font-size:13px;line-height:1.5;word-break:break-word;
}
.chat-msg.theirs .chat-msg-bubble{background:var(--card);border:1px solid var(--border);color:var(--text);border-bottom-left-radius:3px}
.chat-msg.mine .chat-msg-bubble{background:var(--accent);color:var(--bg);font-weight:600;border-bottom-right-radius:3px}
.chat-msg-del{
  position:absolute;top:-4px;right:-4px;width:20px;height:20px;border-radius:50%;
  border:1px solid var(--border);background:var(--card);color:var(--muted);
  font-size:12px;line-height:1;cursor:pointer;display:none;align-items:center;justify-content:center;
  font-family:inherit;padding:0;
}
.chat-msg:hover .chat-msg-del{display:flex}
.chat-msg.mine .chat-msg-del{right:auto;left:-4px}
#chat-input-area{
  padding:10px 14px;border-top:1px solid var(--border);
  display:flex;gap:8px;align-items:flex-end;flex-shrink:0;background:var(--card);
}
#chat-input{
  flex:1;background:var(--bg);border:1px solid var(--border);border-radius:8px;
  color:var(--text);font-size:13px;font-family:inherit;padding:8px 12px;
  resize:none;max-height:80px;min-height:36px;outline:none;line-height:1.4;
  transition:border-color .15s;
}
#chat-input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.1)}
#chat-send{
  width:36px;height:36px;border-radius:8px;background:var(--accent);
  border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;
  flex-shrink:0;transition:filter .15s;
}
#chat-send:hover{filter:brightness(1.1)}
#chat-send:disabled{opacity:.4;cursor:not-allowed}
#chat-send svg{color:var(--bg)}
#chat-attach{
  width:36px;height:36px;border-radius:8px;background:transparent;
  border:1px solid var(--border);cursor:pointer;display:flex;align-items:center;justify-content:center;
  flex-shrink:0;color:var(--muted);transition:border-color .15s,color .15s,background .15s;
}
#chat-attach:hover{color:var(--accent);border-color:var(--accent);background:var(--accent-bg)}
#chat-file-input{display:none}
#chat-pending-row{padding:6px 14px 0;display:none}
#chat-pending-row.show{display:block}
.chat-pending-chip{display:flex;align-items:center;gap:8px;padding:6px 10px;background:var(--bg);
  border:1px solid var(--border);border-radius:8px;font-size:12px;color:var(--text2)}
.chat-pending-chip button{background:none;border:none;color:var(--muted);cursor:pointer;font-size:16px;line-height:1}
.chat-pending-chip button:hover{color:var(--danger)}
.chat-msg-attach{display:block;margin-top:6px}
.chat-msg-attach-img img{max-width:280px;max-height:200px;border-radius:8px;display:block}
.chat-msg-attach-file{display:inline-flex;padding:6px 10px;background:var(--accent-bg);
  border:1px solid rgba(34,211,238,.25);border-radius:8px;font-size:12px;color:var(--accent);text-decoration:none}
.chat-msg.mine .chat-msg-attach-file{background:rgba(0,0,0,.12);border-color:rgba(255,255,255,.25);color:var(--bg)}
.chat-modal-overlay{
  position:fixed;inset:0;z-index:10000;background:rgba(0,0,0,.55);
  display:flex;align-items:center;justify-content:center;padding:20px;
}
.chat-modal{
  background:var(--card);border:1px solid var(--border);border-radius:14px;
  padding:20px;width:min(440px,100%);max-height:80vh;overflow-y:auto;
  box-shadow:0 24px 64px rgba(0,0,0,.45);
}
.chat-modal h3{margin:0 0 14px;font-size:15px;font-weight:700}
.chat-modal label{display:block;font-size:11px;font-weight:600;color:var(--muted);
  text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px}
.chat-modal input,.chat-modal textarea{
  width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;
  padding:10px 12px;color:var(--text);font-size:13px;font-family:inherit;
  margin-bottom:12px;outline:none;
}
.chat-modal input:focus,.chat-modal textarea:focus{border-color:var(--accent)}
.chat-user-list{max-height:220px;overflow-y:auto;border:1px solid var(--border);border-radius:8px;margin-bottom:12px}
.chat-user-row{
  display:block;width:100%;text-align:left;padding:10px 12px;border:none;
  border-bottom:1px solid var(--border);background:transparent;color:var(--text);
  cursor:pointer;font-size:13px;font-family:inherit;
}
.chat-user-row:last-child{border-bottom:none}
.chat-user-row:hover{background:var(--accent-bg);color:var(--accent)}
.chat-member-chips{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px;max-height:120px;overflow-y:auto}
.chat-member-chip{
  display:flex;align-items:center;gap:6px;padding:4px 10px;border-radius:20px;
  background:var(--accent-bg);color:var(--accent);font-size:11px;font-weight:600;
}
.chat-member-chip button{border:none;background:transparent;color:var(--muted);cursor:pointer;font-size:14px;padding:0;line-height:1}
.chat-modal-actions{display:flex;gap:8px;justify-content:flex-end;margin-top:4px}
.chat-modal-actions button{
  padding:9px 16px;border-radius:8px;font-size:13px;font-weight:700;
  cursor:pointer;font-family:inherit;border:1px solid var(--border);
  background:transparent;color:var(--text2);
}
.chat-modal-actions button.primary{background:var(--accent);color:var(--bg);border-color:var(--accent)}
.toast{
  position:fixed;bottom:22px;right:22px;z-index:10001;padding:11px 16px;
  border-radius:10px;font-size:13px;font-weight:600;box-shadow:0 10px 36px rgba(0,0,0,.4);
  border:1px solid var(--border);animation:toast-in .2s ease;
}
.toast.success{background:rgba(52,211,153,.15);color:var(--ok)}
.toast.danger{background:rgba(248,113,113,.15);color:var(--danger)}
.toast.info{background:var(--accent-bg);color:var(--accent)}
@keyframes toast-in{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.sidebar-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:200}
body.sb-open .sidebar-overlay{display:block}
@media (max-width:900px){
  .sidebar{position:fixed;left:0;top:0;bottom:0;z-index:300;transform:translateX(-105%);transition:transform .18s ease}
  body.sb-open .sidebar{transform:translateX(0)}
  #chat-left{width:100%;max-width:100%;position:absolute;left:0;top:0;bottom:0;z-index:50;
    transform:translateX(-105%);transition:transform .18s ease}
  body.chat-list-open #chat-left{transform:translateX(0)}
  body.chat-active #chat-left{transform:translateX(-105%)}
}
</style>
</head>
<body>
<script src="/static/mysifa_theme.js"></script>
<script src="/static/mysifa_user_chip.js"></script>
<div class="sidebar-overlay" id="sb-ov" onclick="document.body.classList.remove('sb-open')"></div>
<div id="chat-app">
  <aside class="sidebar">
    <div class="logo">
      <div class="logo-brand">My<span>Sifa</span></div>
      <div class="logo-sub">Messages</div>
    </div>
    <button type="button" class="nav-btn active" onclick="location.href='/messages'">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
      Messages
      <span class="chat-nav-badge hidden" data-mysifa-chat-badge></span>
    </button>
    <div class="sidebar-bottom">
      <button type="button" class="nav-btn back-mysifa" onclick="location.href='/'">
        ← Retour <span class="wm">My<span>Sifa</span></span>
      </button>
      <div class="user-chip" id="sb-user-chip" onclick="location.href='/profil'" title="Mon profil"></div>
      <button type="button" class="theme-btn" id="btn-theme">
        <span class="theme-ico" id="theme-ico"></span>
        <span id="theme-label">Mode clair</span>
      </button>
      <button type="button" class="logout-btn" id="btn-logout">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
        Déconnexion
      </button>
      <div class="version">Messages · __V_LABEL__</div>
    </div>
  </aside>
  <div id="chat-wrap">
    <div id="chat-left">
      <div class="chat-list-section chat-list-section-channels">
        <div id="chat-left-head">
          <div class="chat-section-title">Canaux</div>
          <button type="button" id="btn-new-channel" title="Nouveau canal" style="display:none" onclick="openNewChannel()">+</button>
        </div>
        <div id="chat-channels-list"></div>
      </div>
      <div class="chat-list-section chat-list-section-dms">
        <div id="chat-dm-head">
          <div class="chat-section-title">Messages directs</div>
        </div>
        <div id="chat-dms-list"></div>
      </div>
      <div id="chat-left-foot">
        <button type="button" onclick="openNewDm()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          Nouveau message
        </button>
      </div>
    </div>
    <div id="chat-main">
      <div id="chat-header" style="display:none">
        <div id="chat-header-top">
          <div id="chat-header-titles">
            <div id="chat-header-title">—</div>
            <div id="chat-header-sub"></div>
          </div>
          <button type="button" id="sound-toggle-btn" onclick="toggleSound()" class="hbtn"
            title="Couper le son" aria-label="Activer ou couper la sonnerie">
            <span id="sound-toggle-icon" aria-hidden="true"></span>
          </button>
        </div>
      </div>
      <div id="chat-empty">Sélectionnez un canal ou démarrez une conversation.</div>
      <div id="chat-messages" style="display:none"></div>
      <div id="chat-pending-row"></div>
      <div id="chat-input-area" style="display:none">
        <input type="file" id="chat-file-input" accept=".jpg,.jpeg,.png,.webp,.gif,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.zip">
        <button type="button" id="chat-attach" aria-label="Pièce jointe" title="Pièce jointe" onclick="document.getElementById('chat-file-input').click()">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>
        </button>
        <textarea id="chat-input" placeholder="Message…" rows="1" aria-label="Message"></textarea>
        <button type="button" id="chat-send" aria-label="Envoyer" onclick="sendMessage()">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
        </button>
      </div>
    </div>
  </div>
</div>
<div id="mroot"></div>
<script src="/static/support_widget.js"></script>
<script src="/static/mysifa_chat_badge.js"></script>
<script>
window.__MYSIFA_UID__ = __USER_ID__;
window.__MYSIFA_NOM__ = __USER_NOM_JSON__;
window.__MYSIFA_ROLE__ = __USER_ROLE_JSON__;
window.__MYSIFA_AVATAR__ = __USER_AVATAR_JSON__;

const ADMIN_ROLES = new Set(['superadmin','direction','administration']);
const ROLE_LABELS = {
  direction:'Direction',administration:'Administration',fabrication:'Fabrication',
  logistique:'Logistique',comptabilite:'Comptabilité',expedition:'Expédition',
  commercial:'Commercial',superadmin:'Super admin'
};

let channels = [];
let activeId = null;
let messages = [];
let hasMore = false;
let lastMsgId = 0;
let pollTimer = null;
let listPollTimer = null;
let allUsers = [];
let newChannelMembers = [];
let pendingChatFile = null;

// ── Sonnerie notification ─────────────────────────────────
let _audioCtx = null;
let _soundEnabled = localStorage.getItem('chat_sound') !== '0';

const ICO_VOLUME='<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/></svg>';
const ICO_VOLUME_OFF='<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/></svg>';

function _getAudioCtx(){
  if(!_audioCtx){
    _audioCtx=new (window.AudioContext||window.webkitAudioContext)();
  }
  if(_audioCtx.state==='suspended')_audioCtx.resume();
  return _audioCtx;
}

function playNotifSound(){
  if(!_soundEnabled)return;
  try{
    const ctx=_getAudioCtx();
    const osc=ctx.createOscillator();
    const gain=ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.type='sine';
    osc.frequency.setValueAtTime(523,ctx.currentTime);
    osc.frequency.setValueAtTime(659,ctx.currentTime+0.12);
    gain.gain.setValueAtTime(0,ctx.currentTime);
    gain.gain.linearRampToValueAtTime(0.25,ctx.currentTime+0.01);
    gain.gain.exponentialRampToValueAtTime(0.001,ctx.currentTime+0.45);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime+0.45);
  }catch(e){}
}

function syncSoundToggleUI(){
  const btn=document.getElementById('sound-toggle-btn');
  const ico=document.getElementById('sound-toggle-icon');
  if(!btn||!ico)return;
  btn.title=_soundEnabled?'Couper le son':'Activer le son';
  ico.innerHTML=_soundEnabled?ICO_VOLUME:ICO_VOLUME_OFF;
}

function toggleSound(){
  _soundEnabled=!_soundEnabled;
  localStorage.setItem('chat_sound',_soundEnabled?'1':'0');
  syncSoundToggleUI();
  if(_soundEnabled){
    try{_getAudioCtx();}catch(e){}
  }
}

function esc(s){
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');
}
function showToast(msg,type){
  const t=document.createElement('div');
  t.className='toast '+(type||'info');
  t.textContent=msg;
  document.body.appendChild(t);
  setTimeout(()=>t.remove(),3200);
}
async function api(path,opts){
  const r=await fetch(path,{credentials:'include',...opts});
  if(r.status===401){location.href='/?next=/messages';throw new Error('auth');}
  if(!r.ok){
    let d='Erreur';
    try{const j=await r.json();d=(j&&j.detail)?(typeof j.detail==='string'?j.detail:JSON.stringify(j.detail)):d;}catch(e){}
    throw new Error(d);
  }
  if(r.status===204)return null;
  const ct=r.headers.get('content-type')||'';
  if(ct.includes('application/json'))return r.json();
  return null;
}
function fmtTime(iso){
  if(!iso)return '';
  try{
    const d=new Date(iso.replace(' ','T'));
    const now=new Date();
    const same=d.toDateString()===now.toDateString();
    if(same)return d.toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit'});
    return d.toLocaleDateString('fr-FR',{day:'2-digit',month:'short'})+' '+d.toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit'});
  }catch(e){return iso;}
}
function stopPolling(){
  if(pollTimer){clearInterval(pollTimer);pollTimer=null;}
  if(listPollTimer){clearInterval(listPollTimer);listPollTimer=null;}
}
function startPolling(){
  stopPolling();
  if(!activeId)return;
  pollTimer=setInterval(pollMessages,5000);
  listPollTimer=setInterval(loadChannels,10000);
}

async function loadChannels(){
  try{
    channels=await api('/api/chat/channels')||[];
    renderChannelLists();
    if(window.MySifaChatBadge)MySifaChatBadge.refresh();
  }catch(e){
    if(e.message!=='auth')showToast(e.message||'Chargement impossible','danger');
  }
}

function renderChannelLists(){
  const chans=channels.filter(c=>c.type==='channel');
  const dms=channels.filter(c=>c.type==='direct');
  const mkItem=(c)=>{
    const unread=Number(c.unread_count)||0;
    const badge=unread>0?'<span class="chat-unread-badge">'+esc(unread>99?'99+':String(unread))+'</span>':'';
    const prev=c.last_message_body?(esc(c.last_message_from||'')+': '+esc(c.last_message_body)):'';
    const active=c.id===activeId?' active':'';
    return '<button type="button" class="chat-chan-item'+active+'" data-id="'+c.id+'" onclick="selectChannel('+c.id+')">'+
      '<div class="chat-chan-body"><div class="chat-chan-name">'+esc(c.display_name||(c.name||'Canal'))+'</div>'+
      (prev?'<div class="chat-chan-preview">'+prev+'</div>':'')+
      '</div>'+badge+'</button>';
  };
  document.getElementById('chat-channels-list').innerHTML=chans.length?chans.map(mkItem).join(''):'<p style="padding:8px 10px;font-size:12px;color:var(--muted);margin:0">Aucun canal</p>';
  document.getElementById('chat-dms-list').innerHTML=dms.length?dms.map(mkItem).join(''):'<p style="padding:8px 10px;font-size:12px;color:var(--muted);margin:0">Aucun message direct</p>';
}

async function selectChannel(id){
  activeId=id;
  pendingChatFile=null;
  renderPendingChatFile();
  renderChannelLists();
  document.body.classList.add('chat-active');
  document.body.classList.remove('chat-list-open');
  document.getElementById('chat-empty').style.display='none';
  document.getElementById('chat-header').style.display='';
  document.getElementById('chat-messages').style.display='';
  document.getElementById('chat-input-area').style.display='';
  const ch=channels.find(c=>c.id===id);
  if(ch){
    document.getElementById('chat-header-title').textContent=ch.display_name||(ch.name||'Canal');
    const sub=ch.type==='direct'?'Message direct':(ch.description||'Canal d\'équipe');
    document.getElementById('chat-header-sub').textContent=sub;
  }
  messages=[];
  hasMore=false;
  lastMsgId=0;
  await loadMessages(true);
  startPolling();
}

async function loadMessages(reset){
  if(!activeId)return;
  const box=document.getElementById('chat-messages');
  if(reset){
    box.innerHTML='<p style="text-align:center;color:var(--muted);font-size:12px;padding:20px">Chargement…</p>';
  }
  try{
    const data=await api('/api/chat/channels/'+activeId+'/messages');
    messages=data.messages||[];
    hasMore=!!data.has_more;
    lastMsgId=messages.length?Math.max(...messages.map(m=>m.id)):0;
    renderMessages(true);
    updateLoadMoreBtn();
    scrollToBottom();
    await loadChannels();
  }catch(e){
    showToast(e.message||'Chargement impossible','danger');
  }
}

function updateLoadMoreBtn(){
  const box=document.getElementById('chat-messages');
  let btn=box.querySelector('#chat-load-more');
  if(hasMore&&messages.length){
    if(!btn){
      btn=document.createElement('button');
      btn.type='button';
      btn.id='chat-load-more';
      btn.textContent='Charger plus';
      btn.onclick=loadMoreMessages;
      box.insertBefore(btn,box.firstChild);
    }
  }else if(btn){
    btn.remove();
  }
}

function renderMessages(fullRebuild){
  const box=document.getElementById('chat-messages');
  if(fullRebuild){
    const frag=document.createDocumentFragment();
    messages.forEach(m=>frag.appendChild(buildMsgEl(m)));
    box.innerHTML='';
    box.appendChild(frag);
    updateLoadMoreBtn();
    return;
  }
}

function chatAttachmentHtml(m){
  if(!m.attachment_url)return '';
  const url=esc(m.attachment_url);
  const name=esc(m.attachment_name||'Pièce jointe');
  const mime=(m.attachment_mime||'').toLowerCase();
  if(mime.indexOf('image/')===0){
    return '<a class="chat-msg-attach chat-msg-attach-img" href="'+url+'" target="_blank" rel="noopener noreferrer">'+
      '<img src="'+url+'" alt="'+name+'"></a>';
  }
  return '<a class="chat-msg-attach chat-msg-attach-file" href="'+url+'" target="_blank" rel="noopener noreferrer" download>'+name+'</a>';
}

function renderPendingChatFile(){
  const row=document.getElementById('chat-pending-row');
  if(!row)return;
  if(!pendingChatFile){row.classList.remove('show');row.innerHTML='';return;}
  row.classList.add('show');
  row.innerHTML='<div class="chat-pending-chip"><span>'+esc(pendingChatFile.name)+'</span>'+
    '<button type="button" aria-label="Retirer" onclick="clearPendingChatFile()">×</button></div>';
}

function clearPendingChatFile(){
  pendingChatFile=null;
  renderPendingChatFile();
}

function buildMsgEl(m){
  const wrap=document.createElement('div');
  wrap.className='chat-msg '+(m.is_mine?'mine':'theirs');
  wrap.dataset.id=String(m.id);
  const canDel=m.is_mine||ADMIN_ROLES.has(window.__MYSIFA_ROLE__);
  const body=(m.body||'').trim();
  let bubble=body?esc(body):'';
  if(m.attachment_url)bubble+=(bubble?'<br>':'')+chatAttachmentHtml(m);
  if(!bubble)bubble='<span style="color:var(--muted);font-size:12px">Pièce jointe</span>';
  wrap.innerHTML=
    '<div class="chat-msg-label">'+esc(m.user_nom)+' · '+esc(fmtTime(m.created_at))+'</div>'+
    '<div class="chat-msg-bubble">'+bubble+'</div>'+
    (canDel?'<button type="button" class="chat-msg-del" title="Supprimer" onclick="deleteMsg('+m.id+')">×</button>':'');
  return wrap;
}

function appendNewMessages(msgs){
  const box=document.getElementById('chat-messages');
  const wasBottom=isNearBottom(box);
  msgs.forEach(m=>{
    if(messages.some(x=>x.id===m.id))return;
    messages.push(m);
    box.appendChild(buildMsgEl(m));
    if(m.id>lastMsgId)lastMsgId=m.id;
  });
  if(wasBottom)scrollToBottom();
}

function isNearBottom(el){
  return el.scrollHeight-el.scrollTop-el.clientHeight<80;
}
function scrollToBottom(){
  const box=document.getElementById('chat-messages');
  requestAnimationFrame(()=>{box.scrollTop=box.scrollHeight;});
}

async function pollMessages(){
  if(!activeId)return;
  try{
    const data=await api('/api/chat/channels/'+activeId+'/messages');
    const incoming=data.messages||[];
    if(!incoming.length)return;
    const fresh=incoming.filter(m=>m.id>lastMsgId);
    if(fresh.some(m=>!m.is_mine))playNotifSound();
    if(fresh.length)appendNewMessages(fresh);
    const maxId=Math.max(...incoming.map(m=>m.id));
    if(maxId>lastMsgId)lastMsgId=maxId;
  }catch(e){}
}

async function loadMoreMessages(){
  if(!activeId||!messages.length||!hasMore)return;
  const oldest=messages[0].created_at;
  const box=document.getElementById('chat-messages');
  const prevH=box.scrollHeight;
  const prevTop=box.scrollTop;
  try{
    const data=await api('/api/chat/channels/'+activeId+'/messages?before='+encodeURIComponent(oldest));
    const older=data.messages||[];
    hasMore=!!data.has_more;
    if(older.length){
      const merged=[...older,...messages.filter(m=>!older.some(o=>o.id===m.id))];
      messages=merged;
      renderMessages(true);
      requestAnimationFrame(()=>{
        box.scrollTop=box.scrollHeight-prevH+prevTop;
      });
    }
    updateLoadMoreBtn();
  }catch(e){
    showToast(e.message||'Chargement impossible','danger');
  }
}

async function sendMessage(){
  const inp=document.getElementById('chat-input');
  const body=(inp.value||'').trim();
  const file=pendingChatFile;
  if((!body&&!file)||!activeId)return;
  const btn=document.getElementById('chat-send');
  btn.disabled=true;
  try{
    if(file){
      const fd=new FormData();
      if(body)fd.append('body',body);
      fd.append('file',file);
      await api('/api/chat/channels/'+activeId+'/messages',{method:'POST',body:fd});
    }else{
      await api('/api/chat/channels/'+activeId+'/messages',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({body})
      });
    }
    inp.value='';
    inp.style.height='auto';
    pendingChatFile=null;
    renderPendingChatFile();
    await loadMessages(false);
  }catch(e){
    showToast(e.message||'Envoi impossible','danger');
  }finally{
    btn.disabled=false;
  }
}

async function deleteMsg(msgId){
  if(!activeId||!confirm('Supprimer ce message ?'))return;
  try{
    await api('/api/chat/channels/'+activeId+'/messages/'+msgId,{method:'DELETE'});
    messages=messages.filter(m=>m.id!==msgId);
    const el=document.querySelector('.chat-msg[data-id="'+msgId+'"]');
    if(el)el.remove();
    showToast('Message supprimé','success');
  }catch(e){
    showToast(e.message||'Suppression impossible','danger');
  }
}

function closeModal(){document.getElementById('mroot').innerHTML='';}

async function openNewDm(){
  try{
    allUsers=await api('/api/chat/users')||[];
  }catch(e){
    showToast(e.message||'Chargement impossible','danger');
    return;
  }
  const overlay=document.createElement('div');
  overlay.className='chat-modal-overlay';
  overlay.onclick=e=>{if(e.target===overlay)closeModal();};
  overlay.innerHTML=
    '<div class="chat-modal" role="dialog">'+
    '<h3>Nouveau message</h3>'+
    '<label for="dm-search">Rechercher un collègue</label>'+
    '<input type="search" id="dm-search" placeholder="Nom…" autocomplete="off">'+
    '<div class="chat-user-list" id="dm-user-list"></div>'+
    '<div class="chat-modal-actions"><button type="button" onclick="closeModal()">Annuler</button></div>'+
    '</div>';
  document.getElementById('mroot').appendChild(overlay);
  const renderUsers=(q)=>{
    const ql=(q||'').toLowerCase();
    const list=allUsers.filter(u=>!ql||(u.nom||'').toLowerCase().includes(ql));
    const el=document.getElementById('dm-user-list');
    if(!list.length){el.innerHTML='<p style="padding:12px;margin:0;font-size:12px;color:var(--muted)">Aucun résultat</p>';return;}
    el.innerHTML=list.map(u=>'<button type="button" class="chat-user-row" data-uid="'+u.id+'">'+
      esc(u.nom)+' <span style="color:var(--muted);font-size:11px">'+esc(ROLE_LABELS[u.role]||u.role||'')+'</span></button>').join('');
    el.querySelectorAll('.chat-user-row').forEach(btn=>{
      btn.onclick=async()=>{
        const uid=parseInt(btn.dataset.uid,10);
        closeModal();
        try{
          const r=await api('/api/chat/channels',{
            method:'POST',headers:{'Content-Type':'application/json'},
            body:JSON.stringify({type:'direct',user_id:uid})
          });
          await loadChannels();
          selectChannel(r.id);
        }catch(e){showToast(e.message||'Impossible','danger');}
      };
    });
  };
  renderUsers('');
  const search=document.getElementById('dm-search');
  search.oninput=()=>renderUsers(search.value);
  requestAnimationFrame(()=>search.focus());
}

async function openNewChannel(){
  try{
    allUsers=await api('/api/chat/users')||[];
  }catch(e){
    showToast(e.message||'Chargement impossible','danger');
    return;
  }
  newChannelMembers=[];
  const overlay=document.createElement('div');
  overlay.className='chat-modal-overlay';
  overlay.onclick=e=>{if(e.target===overlay)closeModal();};
  overlay.innerHTML=
    '<div class="chat-modal" role="dialog">'+
    '<h3>Nouveau canal</h3>'+
    '<label for="ch-name">Nom</label><input type="text" id="ch-name" maxlength="60" placeholder="ex. commercial">'+
    '<label for="ch-desc">Description</label><textarea id="ch-desc" rows="2" placeholder="Optionnel"></textarea>'+
    '<label for="ch-member-search">Ajouter des membres</label>'+
    '<input type="search" id="ch-member-search" placeholder="Nom…">'+
    '<div class="chat-member-chips" id="ch-member-chips"></div>'+
    '<div class="chat-user-list" id="ch-user-pick" style="max-height:160px"></div>'+
    '<div class="chat-modal-actions">'+
    '<button type="button" onclick="closeModal()">Annuler</button>'+
    '<button type="button" class="primary" id="ch-create-btn">Créer</button></div></div>';
  document.getElementById('mroot').appendChild(overlay);
  function renderChips(){
    document.getElementById('ch-member-chips').innerHTML=newChannelMembers.map(m=>
      '<span class="chat-member-chip">'+esc(m.nom)+
      '<button type="button" data-id="'+m.id+'" title="Retirer">×</button></span>').join('');
    document.querySelectorAll('.chat-member-chip button').forEach(b=>{
      b.onclick=()=>{
        const id=parseInt(b.dataset.id,10);
        newChannelMembers=newChannelMembers.filter(x=>x.id!==id);
        renderChips();renderPick(document.getElementById('ch-member-search').value);
      };
    });
  }
  function renderPick(q){
    const ql=(q||'').toLowerCase();
    const picked=new Set(newChannelMembers.map(m=>m.id));
    const list=allUsers.filter(u=>!picked.has(u.id)&&(!ql||(u.nom||'').toLowerCase().includes(ql)));
    const el=document.getElementById('ch-user-pick');
    if(!list.length){el.innerHTML='<p style="padding:10px;margin:0;font-size:12px;color:var(--muted)">—</p>';return;}
    el.innerHTML=list.map(u=>'<button type="button" class="chat-user-row" data-uid="'+u.id+'" data-nom="'+esc(u.nom)+'">'+esc(u.nom)+'</button>').join('');
    el.querySelectorAll('.chat-user-row').forEach(btn=>{
      btn.onclick=()=>{
        newChannelMembers.push({id:parseInt(btn.dataset.uid,10),nom:btn.getAttribute('data-nom')});
        renderChips();renderPick(document.getElementById('ch-member-search').value);
      };
    });
  }
  renderChips();renderPick('');
  document.getElementById('ch-member-search').oninput=function(){renderPick(this.value);};
  document.getElementById('ch-create-btn').onclick=async()=>{
    const name=(document.getElementById('ch-name').value||'').trim();
    if(!name){showToast('Nom requis','danger');return;}
    const description=(document.getElementById('ch-desc').value||'').trim();
    try{
      const r=await api('/api/chat/channels',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({
          type:'channel',name,description,
          member_ids:newChannelMembers.map(m=>m.id)
        })
      });
      closeModal();
      await loadChannels();
      selectChannel(r.id);
      showToast('Canal créé','success');
    }catch(e){showToast(e.message||'Création impossible','danger');}
  };
}

document.getElementById('chat-input').addEventListener('keydown',e=>{
  if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMessage();}
});
document.getElementById('chat-input').addEventListener('input',function(){
  this.style.height='auto';
  this.style.height=Math.min(this.scrollHeight,80)+'px';
});
document.getElementById('chat-file-input').addEventListener('change',function(){
  pendingChatFile=(this.files&&this.files[0])||null;
  renderPendingChatFile();
  this.value='';
});

const ICO_MOON='<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
const ICO_SUN='<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/></svg>';
function syncThemeBtn(){
  const isLight=(window.MySifaTheme?MySifaTheme.loadPrefs():{mode:'dark'}).mode==='light';
  document.getElementById('theme-ico').innerHTML=isLight?ICO_SUN:ICO_MOON;
  document.getElementById('theme-label').textContent=isLight?'Mode sombre':'Mode clair';
}
document.getElementById('btn-theme').onclick=()=>{
  if(window.MySifaTheme)MySifaTheme.toggleMode();
  syncThemeBtn();
};
document.getElementById('btn-logout').onclick=async()=>{
  try{await fetch('/api/auth/logout',{method:'POST',credentials:'include'});}catch(e){}
  location.href='/';
};

(async function init(){
  syncSoundToggleUI();
  if(ADMIN_ROLES.has(window.__MYSIFA_ROLE__)){
    document.getElementById('btn-new-channel').style.display='';
  }
  const chip=document.getElementById('sb-user-chip');
  if(chip&&window.MySifaUserChip){
    const editIco='<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>';
    MySifaUserChip.fill(chip,{
      nom:window.__MYSIFA_NOM__||'',
      role:window.__MYSIFA_ROLE__||'',
      avatar_url:window.__MYSIFA_AVATAR__||''
    },{roleLabels:ROLE_LABELS,editIconHtml:editIco});
  }
  if(window.MySifaTheme)MySifaTheme.applyTheme();
  syncThemeBtn();
  await loadChannels();
  const params=new URLSearchParams(location.search);
  const openId=parseInt(params.get('channel')||'0',10);
  if(openId)selectChannel(openId);
})();
</script>
</body>
</html>
"""

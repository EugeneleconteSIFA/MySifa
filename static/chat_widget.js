/**
 * MySifa — Widget chat flottant (barre portail / bulle apps).
 * Requiert : window.__MYSIFA_APP__ (optionnel, défaut 'unknown')
 * Lit l'utilisateur depuis window.__MYSIFA_UID__ ou GET /api/auth/me
 */
(function () {
  'use strict';

  const CW = {
    uid: 0,
    nom: '',
    role: '',
    isPortal: false,
    open: false,
    activeId: null,
    channels: [],
    lastMsgId: 0,
    pollTimer: null,
    typingPollTimer: null,
    _lastTypingSent: 0,
    memberReadStatus: {},
    bgPollTimer: null,
    prevUnreadTotal: 0,
    _chatSynced: false,
    soundEnabled: localStorage.getItem('chat_sound') !== '0',
    _audioCtx: null,
    _audioUnlocked: false,
    avatarByUserId: {},
    _inited: false,
    _initPromise: null,
    pendingFile: null,
  };

  const ICO_MSG =
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>';
  const ICO_SEND =
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>';
  const ICO_ATTACH =
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>';
  const ICO_PLUS =
    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>';
  const ICO_SETTINGS =
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>';

  const ADMIN_ROLES = new Set(['superadmin', 'direction', 'administration']);
  const CW_EMOJIS = ['👍', '✅', '👀', '⚠️', '🔧', '❌'];
  const CW_MANAGE_ROLES = new Set(['superadmin', 'direction']);
  const ROLE_LABELS = {
    direction: 'Direction',
    administration: 'Administration',
    fabrication: 'Fabrication',
    logistique: 'Logistique',
    comptabilite: 'Comptabilité',
    expedition: 'Expédition',
    commercial: 'Commercial',
    superadmin: 'Super admin',
  };

  const CW_STYLES = `
@keyframes cwPulse{0%,100%{opacity:1}50%{opacity:.3}}
#cw-bar{position:fixed;bottom:24px;left:24px;right:auto!important;z-index:9100;width:340px;max-width:calc(100vw - 48px);
  background:var(--card);border:1px solid var(--border);border-radius:14px;padding:12px 16px;
  display:none;align-items:center;gap:12px;cursor:pointer;transition:border-color .15s,box-shadow .18s,transform .18s;
  font-family:inherit;box-shadow:0 4px 16px rgba(0,0,0,.2)}
/* Barre : desktop portail uniquement — bulle : mobile + apps desktop */
body:not(.cw-use-bubble) #cw-bar{display:flex!important}
body.cw-use-bubble #cw-bar{display:none!important}
body:not(.cw-use-bubble) #cw-bubble{display:none!important}
body.cw-use-bubble #cw-bubble{display:flex!important}
#cw-bar:hover{border-color:var(--accent);box-shadow:0 6px 20px rgba(0,0,0,.28)}
#cw-bar.cw-portal-accent{background:var(--accent);border:none;
  box-shadow:0 4px 16px rgba(34,211,238,0.35)}
#cw-bar.cw-portal-accent:hover{box-shadow:0 6px 24px rgba(34,211,238,0.5);transform:scale(1.01)}
#cw-bar.cw-portal-accent.cw-bar-active{box-shadow:0 6px 24px rgba(34,211,238,0.5)}
#cw-bar.cw-portal-accent #cw-bar-icon{background:rgba(10,14,23,.18);color:var(--bg)}
#cw-bar.cw-portal-accent #cw-bar-icon svg{color:var(--bg)}
body.light #cw-bar.cw-portal-accent #cw-bar-icon{background:rgba(255,255,255,.22)}
#cw-bar.cw-portal-accent #cw-bar-title,#cw-bar.cw-portal-accent #cw-bar-preview{color:var(--bg)}
#cw-bar.cw-portal-accent #cw-bar-preview{opacity:.88}
#cw-bar-icon{width:38px;height:38px;border-radius:50%;background:var(--accent-bg);
  display:flex;align-items:center;justify-content:center;flex-shrink:0;color:var(--accent)}
#cw-bar-text{flex:1;min-width:0}
#cw-bar-title{font-size:13px;font-weight:700;color:var(--text);display:flex;align-items:center;gap:8px}
#cw-bar-preview{font-size:11px;color:var(--muted);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#cw-bar-icon-wrap{position:relative;flex-shrink:0}
#cw-bar-badge,#cw-bubble-badge{display:none;min-width:18px;height:18px;padding:0 5px;border-radius:99px;
  background:var(--danger);color:#fff;font-size:10px;font-weight:800;line-height:1;
  align-items:center;justify-content:center;box-shadow:0 2px 8px rgba(0,0,0,.3);pointer-events:none}
#cw-bar-badge{position:absolute;top:-6px;right:-6px}
#cw-bar.cw-portal-accent #cw-bar-badge{background:#fff;color:#0a0e17;border:2px solid rgba(10,14,23,.15)}
body.light #cw-bar.cw-portal-accent #cw-bar-badge{border-color:rgba(15,23,42,.12)}
#cw-bubble{position:fixed;z-index:9100;
  right:max(24px,env(safe-area-inset-right,0px));
  bottom:max(24px,env(safe-area-inset-bottom,0px));
  left:auto!important;
  width:48px;height:48px;border-radius:50%;background:var(--accent);border:none;
  display:flex;align-items:center;justify-content:center;cursor:pointer;
  transition:transform .18s,box-shadow .18s;color:var(--bg);overflow:visible;
  box-shadow:0 4px 16px rgba(34,211,238,0.35)}
#cw-bubble:hover{transform:scale(1.08);box-shadow:0 6px 24px rgba(34,211,238,0.5)}
#cw-bubble svg{color:var(--bg);position:relative;z-index:0}
#cw-bubble-badge{position:absolute;top:-6px;right:-6px;z-index:2;
  border:2px solid var(--bg)}
body.light #cw-bubble-badge{border-color:#fff}
#cw-panel{position:fixed;z-index:9101;width:440px;height:580px;max-height:calc(100vh - 64px);
  background:var(--card);border:1px solid var(--border);border-radius:14px;display:flex;overflow:hidden;
  font-family:'Segoe UI',system-ui,sans-serif;font-size:13px;
  box-shadow:0 12px 48px rgba(0,0,0,0.5)}
#cw-panel.cw-hidden{display:none!important}
#cw-panel.cw-mode-bubble{bottom:auto;right:auto;left:auto}
#cw-panel.cw-mode-bar{bottom:90px;left:24px;right:auto;width:440px}
#cw-panel-left{width:168px;flex-shrink:0;border-right:1px solid var(--border);
  display:flex;flex-direction:column;overflow:hidden;min-height:0}
.cw-list-section{display:flex;flex-direction:column;flex:1;min-height:0;overflow:hidden}
.cw-list-section-dms{border-top:1px solid var(--border)}
.cw-section-row{display:flex;align-items:center;justify-content:space-between;padding:12px 12px 6px;gap:6px;flex-shrink:0}
.cw-section-row.cw-section-discussion{padding-top:12px}
#cw-channels,#cw-dms{flex:1;min-height:0;overflow-y:auto;scrollbar-width:thin;scrollbar-color:var(--border) transparent}
.cw-section-label{font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;
  letter-spacing:.5px;flex:1;min-width:0}
.cw-section-add{width:26px;height:26px;border-radius:8px;border:1px solid var(--border);background:transparent;
  color:var(--accent);cursor:pointer;display:flex;align-items:center;justify-content:center;padding:0;flex-shrink:0}
.cw-section-add:hover{background:var(--accent-bg);border-color:var(--accent)}
.cw-section-add.cw-hidden{display:none}
.cw-channel-item{padding:9px 12px;font-size:13px;color:var(--text2);display:flex;align-items:center;
  gap:8px;cursor:pointer;transition:background .1s;border:none;background:transparent;width:100%;
  text-align:left;font-family:inherit}
.cw-avatar,.cw-avatar-ph{width:28px;height:28px;border-radius:50%;flex-shrink:0}
.cw-avatar{object-fit:cover;border:1px solid var(--border);display:block}
.cw-avatar-ph{display:inline-flex;align-items:center;justify-content:center;
  background:var(--accent-bg);color:var(--accent);font-size:10px;font-weight:700;letter-spacing:.3px}
.cw-avatar-ph.cw-chan-emoji{font-size:17px;font-weight:400;letter-spacing:0;line-height:1;
  text-transform:none;background:var(--accent-bg);color:var(--text)}
.cw-header-avatar .cw-avatar-ph.cw-chan-emoji{font-size:20px}
.cw-chan-body{flex:1;min-width:0;display:flex;align-items:center;gap:6px}
.cw-msg-meta{display:flex;align-items:center;gap:6px;margin-bottom:4px}
.cw-msg-meta .cw-avatar,.cw-msg-meta .cw-avatar-ph{width:20px;height:20px;font-size:9px}
.cw-msg-meta-text{font-size:11px;color:var(--muted)}
.cw-header-avatar{flex-shrink:0;display:flex}
.cw-header-avatar.cw-hidden{display:none}
.cw-header-avatar .cw-avatar,.cw-header-avatar .cw-avatar-ph{width:32px;height:32px;font-size:11px}
.cw-dm-row{display:flex;align-items:center;gap:10px}
.cw-dm-row .cw-avatar,.cw-dm-row .cw-avatar-ph{width:32px;height:32px;font-size:11px}
.cw-member-row{display:flex;align-items:center;gap:10px;padding:10px 0;border-bottom:1px solid var(--border);position:relative}
.cw-member-row:last-child{border-bottom:none}
.cw-member-body{flex:1;min-width:0}
.cw-member-role{font-size:11px;color:var(--muted);margin-top:2px}
.cw-member-actions-btn{background:none;border:1px solid var(--border);border-radius:8px;
  color:var(--muted);cursor:pointer;width:28px;height:28px;display:flex;align-items:center;
  justify-content:center;flex-shrink:0;font-size:16px;padding:0;font-family:inherit;
  margin-left:auto;transition:border-color .1s,color .1s}
.cw-member-actions-btn:hover{border-color:var(--accent);color:var(--accent)}
.cw-member-dropdown{position:absolute;right:14px;top:40px;z-index:20;
  background:var(--card);border:1px solid var(--border);border-radius:10px;
  min-width:170px;box-shadow:0 8px 24px rgba(0,0,0,.35);overflow:hidden}
.cw-member-dropdown.cw-hidden{display:none}
.cw-dropdown-item{display:block;width:100%;text-align:left;padding:10px 14px;
  background:none;border:none;border-bottom:1px solid var(--border);
  color:var(--text2);font-size:13px;cursor:pointer;font-family:inherit}
.cw-dropdown-item:last-child{border-bottom:none}
.cw-dropdown-item:hover{background:var(--accent-bg);color:var(--accent)}
.cw-dropdown-item.cw-danger:hover{background:rgba(248,113,113,.1);color:var(--danger)}
.cw-channel-item:hover{background:rgba(255,255,255,.04)}
body.light .cw-channel-item:hover{background:rgba(0,0,0,.04)}
.cw-channel-item.cw-active{background:var(--accent-bg);color:var(--accent);font-weight:600}
.cw-channel-item.cw-unread .cw-chan-label{font-weight:700;color:var(--text)}
.cw-channel-item.cw-active.cw-unread .cw-chan-label{color:var(--accent)}
.cw-unread-badge{margin-left:auto;background:var(--danger);color:#fff;font-size:10px;font-weight:800;
  min-width:18px;height:18px;padding:0 5px;border-radius:99px;flex-shrink:0;
  display:inline-flex;align-items:center;justify-content:center}
.cw-chan-label{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;min-width:0}
#cw-panel-right{flex:1;display:flex;flex-direction:column;min-width:0;position:relative}
#cw-panel-header{padding:12px 14px;border-bottom:1px solid var(--border);display:flex;align-items:center;
  font-size:14px;font-weight:600;color:var(--text);gap:8px;min-height:48px}
#cw-panel-title{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cw-header-btn{background:none;border:1px solid var(--border);border-radius:8px;color:var(--muted);
  cursor:pointer;display:flex;align-items:center;justify-content:center;width:32px;height:32px;padding:0;flex-shrink:0}
.cw-header-btn:hover{color:var(--accent);border-color:var(--accent);background:var(--accent-bg)}
.cw-header-btn.cw-hidden{display:none}
#cw-close{background:none;border:none;color:var(--muted);font-size:20px;
  cursor:pointer;line-height:1;padding:0 4px;font-family:inherit;flex-shrink:0}
#cw-close:hover{color:var(--text)}
#cw-messages{flex:1;overflow-y:auto;padding:12px 14px;display:flex;flex-direction:column;gap:10px;min-height:0}
.cw-msg-wrap{position:relative;display:flex;flex-direction:column;max-width:82%;word-break:break-word}
.cw-msg-wrap.cw-mine{align-self:flex-end;align-items:flex-end}
.cw-msg-wrap.cw-theirs{align-self:flex-start;align-items:flex-start}
.cw-msg-bubble-wrap{position:relative;display:inline-block;max-width:100%}
.cw-react-picker{display:none;position:absolute;top:100%;left:0;right:auto;
  margin-top:-10px;background:var(--card);border:1px solid var(--border);border-radius:10px;
  padding:4px 6px;gap:2px;z-index:12;white-space:nowrap;box-shadow:0 4px 16px rgba(0,0,0,.3);
  pointer-events:auto}
.cw-msg-wrap:hover .cw-react-picker,.cw-msg-bubble-wrap:hover .cw-react-picker,
.cw-react-picker:hover{display:flex}
.cw-msg-wrap.cw-mine .cw-react-picker{left:auto;right:0}
.cw-msg-wrap.cw-theirs .cw-react-picker{left:0;right:auto}
/* ── Header message (nom + heure + bouton ⋮ inline) ──── */
.cw-msg-header{display:flex;align-items:center;gap:8px;margin-bottom:4px;position:relative}
.cw-msg-wrap.cw-mine .cw-msg-header{flex-direction:row-reverse}
.cw-msg-header-text{font-size:11px;color:var(--muted);line-height:1.2;white-space:nowrap}
/* ── Bouton ⋮ inline (sobre, toujours visible) ───────── */
.cw-msg-menu-btn{display:inline-flex;align-items:center;justify-content:center;
  width:14px;height:14px;flex-shrink:0;line-height:1;vertical-align:middle;
  border:none;background:transparent;
  color:var(--text2);cursor:pointer;font-family:inherit;padding:0;margin:0;
  opacity:.5;transition:opacity .15s}
.cw-msg-menu-btn svg{display:block;width:14px;height:14px}
.cw-msg-menu-btn:hover,
.cw-msg-menu-btn:focus-visible,
.cw-msg-menu-btn[aria-expanded="true"]{opacity:1}
.cw-msg-menu-btn:focus{outline:none}
/* ── Dropdown ─────────────────────────────────────────── */
/* Par défaut (messages reçus) : bouton à gauche → menu s'ouvre vers la droite */
.cw-msg-menu{position:absolute;top:calc(100% + 4px);left:0;right:auto;background:var(--card);
  border:1px solid var(--border);border-radius:12px;padding:6px;
  box-shadow:0 12px 32px rgba(0,0,0,.45);z-index:300;min-width:184px;
  display:none;opacity:0;transform:translateY(-4px) scale(.97);
  transform-origin:top left;
  transition:opacity .14s ease,transform .14s ease}
.cw-msg-menu.cw-open{display:block;opacity:1;transform:translateY(0) scale(1)}
/* Mes messages : bouton à droite → menu s'ouvre vers la gauche, sous le bouton */
.cw-msg-wrap.cw-mine .cw-msg-menu{left:auto;right:0;transform-origin:top right}
.cw-msg-menu.cw-menu-up{top:auto;bottom:calc(100% + 4px);transform-origin:bottom left}
.cw-msg-wrap.cw-mine .cw-msg-menu.cw-menu-up{transform-origin:bottom right}
.cw-msg-menu-item{display:flex;align-items:center;gap:10px;width:100%;padding:9px 12px;
  border:none;background:transparent;color:var(--text2);font-size:13px;cursor:pointer;
  font-family:inherit;border-radius:8px;text-align:left;white-space:nowrap;
  transition:background .12s,color .12s}
.cw-msg-menu-item svg{flex-shrink:0;width:15px;height:15px;color:currentColor;opacity:.8}
.cw-msg-menu-item:hover{background:var(--accent-bg);color:var(--accent)}
.cw-msg-menu-item:hover svg{opacity:1}
.cw-msg-menu-sep{height:1px;background:var(--border);margin:5px 4px}
.cw-msg-menu-item.cw-danger{color:var(--danger)}
.cw-msg-menu-item.cw-danger:hover{background:rgba(248,113,113,.12);color:var(--danger)}
/* ── Reply context ──────────────────────────────────────── */
.cw-msg-reply-ctx{padding:5px 9px;margin-bottom:5px;border-left:3px solid var(--accent);
  background:var(--accent-bg);border-radius:6px;opacity:.7;cursor:pointer;font-size:11px;line-height:1.4}
.cw-reply-name{font-weight:700;color:var(--text);margin-bottom:1px}
.cw-reply-body{color:var(--text2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:220px}
/* ── Forwarded ──────────────────────────────────────────── */
.cw-msg-fwd-tag{font-size:10px;font-weight:600;color:var(--muted);text-transform:uppercase;
  letter-spacing:.5px;margin-bottom:4px;display:flex;align-items:center;gap:4px}
.cw-msg-fwd{border-left:3px solid var(--muted)!important;padding-left:9px!important;
  border-radius:0 10px 10px 10px!important}
.cw-msg-wrap.cw-mine .cw-msg-fwd{border-radius:10px 0 10px 10px!important}
/* ── Deleted ────────────────────────────────────────────── */
.cw-msg-deleted{font-style:italic;color:var(--muted)!important;
  background:transparent!important;border-style:dashed!important}
/* ── Edited ─────────────────────────────────────────────── */
.cw-msg-edited-lbl{font-size:10px;color:var(--muted);font-style:italic;margin-left:5px}
/* ── Date separator ─────────────────────────────────────── */
.cw-date-sep{display:flex;align-items:center;gap:10px;margin:4px 0;flex-shrink:0;width:100%}
.cw-date-sep::before,.cw-date-sep::after{content:'';flex:1;height:1px;background:var(--border)}
.cw-date-sep-lbl{font-size:10px;font-weight:700;color:var(--muted);letter-spacing:.5px;
  text-transform:uppercase;white-space:nowrap;padding:0 4px}
/* ── Reply bar ──────────────────────────────────────────── */
#cw-reply-bar{padding:6px 12px;background:var(--card);border-top:1px solid var(--border);
  display:none;align-items:center;gap:8px;flex-shrink:0}
#cw-reply-bar.cw-show{display:flex}
.cw-rp-preview{flex:1;min-width:0;padding:4px 9px;border-left:3px solid var(--accent);
  background:var(--accent-bg);border-radius:6px;font-size:12px}
.cw-rp-name{font-weight:700;color:var(--text)}
.cw-rp-body{color:var(--text2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cw-rp-cancel{width:22px;height:22px;border-radius:6px;border:1px solid var(--border);
  background:transparent;color:var(--muted);cursor:pointer;font-size:14px;
  display:flex;align-items:center;justify-content:center;flex-shrink:0;line-height:1}
.cw-rp-cancel:hover{border-color:var(--danger);color:var(--danger)}
/* ── Edit inline ────────────────────────────────────────── */
.cw-edit-ta{width:100%;background:var(--bg);border:1px solid var(--accent);
  border-radius:8px;padding:6px 10px;color:var(--text);font-size:13px;
  font-family:inherit;resize:none;outline:none;line-height:1.4;
  min-height:36px;max-height:100px;box-sizing:border-box}
.cw-edit-row{display:flex;gap:6px;margin-top:5px;justify-content:flex-end}
.cw-edit-row button{padding:4px 11px;border-radius:7px;font-size:12px;font-weight:700;
  cursor:pointer;font-family:inherit;border:1px solid var(--border);
  background:transparent;color:var(--text2)}
.cw-edit-row .ok{background:var(--accent);color:var(--bg);border-color:var(--accent)}
.cw-react-btn{background:none;border:none;cursor:pointer;font-size:16px;
  padding:2px 4px;border-radius:6px;line-height:1.2;transition:background .1s}
.cw-react-btn:hover{background:var(--accent-bg)}
.cw-reactions{display:flex;flex-wrap:wrap;gap:4px;margin-top:4px}
.cw-reaction-pill{position:relative;display:inline-flex;align-items:center;gap:4px;padding:2px 8px;
  border-radius:99px;font-size:12px;cursor:pointer;border:1px solid var(--border);
  background:transparent;color:var(--text2);font-family:inherit;transition:border-color .1s,background .1s}
#cw-reaction-tip-float{
  display:none;position:fixed;z-index:9125;pointer-events:none;
  background:var(--card);border:1px solid var(--border);border-radius:8px;
  padding:8px 10px;font-size:12px;line-height:1.45;color:var(--text2);
  box-shadow:0 8px 24px rgba(0,0,0,.35);max-width:240px;max-height:180px;overflow-y:auto;
}
#cw-reaction-tip-float .cw-tip-name{display:block;color:var(--text)}
#cw-reaction-tip-float .cw-tip-name+.cw-tip-name{margin-top:4px}
.cw-reaction-pill:hover{border-color:var(--accent);background:var(--accent-bg)}
.cw-reaction-pill.cw-reacted{border-color:var(--accent);background:var(--accent-bg);color:var(--accent);font-weight:600}
.cw-reaction-count{font-size:12px;font-weight:600}
.cw-msg-mine{background:var(--accent-bg);border:1px solid rgba(34,211,238,.2);
  border-radius:10px 0 10px 10px;padding:8px 12px;font-size:13px;color:var(--text);
  white-space:pre-wrap;word-break:break-word}
.cw-msg-theirs{background:rgba(255,255,255,.05);border:1px solid var(--border);
  border-radius:0 10px 10px 10px;padding:8px 12px;font-size:13px;color:var(--text);
  white-space:pre-wrap;word-break:break-word}
body.light .cw-msg-theirs{background:rgba(0,0,0,.04)}
#cw-typing-bar{height:20px;padding:0 14px;font-size:11px;color:var(--muted);display:flex;align-items:center;gap:6px;min-height:20px;transition:opacity .2s;flex-shrink:0}
.cw-typing-dot{width:5px;height:5px;border-radius:50%;background:var(--muted);display:inline-block;animation:cwTypDot 1.2s ease-in-out infinite}
.cw-typing-dot:nth-child(2){animation-delay:.2s}
.cw-typing-dot:nth-child(3){animation-delay:.4s}
@keyframes cwTypDot{0%,80%,100%{transform:scale(.6);opacity:.4}40%{transform:scale(1);opacity:1}}
.cw-read-receipt{text-align:right;font-size:10px;padding:0 2px 4px;display:flex;align-items:center;justify-content:flex-end;gap:4px}
.cw-read-receipt.cw-read-vu{color:var(--accent)}
.cw-read-receipt.cw-read-count{color:var(--muted)}
#cw-input-row{padding:10px 12px;border-top:1px solid var(--border);display:flex;gap:8px;align-items:center}
#cw-input{flex:1;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:8px 12px;
  font-size:13px;line-height:1.3;color:var(--text);resize:none;font-family:inherit;
  height:38px;min-height:38px;max-height:96px;box-sizing:border-box;overflow-y:auto;outline:none}
#cw-input:focus{border-color:var(--accent)}
#cw-send{width:38px;height:38px;box-sizing:border-box;background:var(--accent-bg);
  border:1px solid rgba(34,211,238,.3);border-radius:10px;padding:0;
  cursor:pointer;display:flex;align-items:center;justify-content:center;color:var(--accent);flex-shrink:0}
#cw-send:hover{filter:brightness(1.05)}
#cw-send:disabled{opacity:.5;cursor:not-allowed}
#cw-attach{width:38px;height:38px;box-sizing:border-box;background:transparent;
  border:1px solid var(--border);border-radius:10px;padding:0;cursor:pointer;
  display:flex;align-items:center;justify-content:center;color:var(--muted);flex-shrink:0}
#cw-attach:hover{color:var(--accent);border-color:var(--accent);background:var(--accent-bg)}
#cw-file-input{display:none}
#cw-pending-row{padding:6px 12px 0;border-top:1px solid var(--border);display:none}
#cw-pending-row.cw-show{display:block}
.cw-pending-chip{display:flex;align-items:center;gap:8px;padding:6px 10px;background:var(--bg);
  border:1px solid var(--border);border-radius:8px;font-size:12px;color:var(--text2)}
.cw-pending-chip button{background:none;border:none;color:var(--muted);cursor:pointer;font-size:16px;line-height:1;padding:0 2px}
.cw-pending-chip button:hover{color:var(--danger)}
.cw-msg-attach{display:block;margin-top:6px}
.cw-msg-attach-img img{max-width:220px;max-height:160px;border-radius:8px;display:block}
.upd-overlay{position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:9010;display:flex;align-items:center;justify-content:center;padding:16px}
.upd-card{background:var(--card);border:1px solid var(--border);border-radius:18px;padding:28px 22px;width:min(540px,100%);max-height:88vh;overflow-y:auto;box-shadow:0 24px 64px rgba(0,0,0,.55)}
.upd-card .upd-body{font-size:13px;line-height:1.8;color:var(--text2)}
.upd-card .upd-body ul{padding-left:18px;margin:8px 0}
.upd-ok-btn{margin-top:16px;width:100%;padding:12px;border-radius:10px;background:var(--accent);color:var(--bg);border:none;font-weight:700;cursor:pointer;font-family:inherit}
.cw-msg-attach-file{display:inline-flex;align-items:center;gap:6px;padding:6px 10px;
  background:var(--accent-bg);border:1px solid rgba(34,211,238,.25);border-radius:8px;
  font-size:12px;color:var(--accent);text-decoration:none}
.cw-msg-attach-file:hover{filter:brightness(1.05)}
.cw-msg-mine .cw-msg-attach-file{background:rgba(0,0,0,.15);border-color:rgba(255,255,255,.2);color:var(--bg)}
#cw-dm-picker{position:absolute;inset:0;background:var(--card);z-index:2;display:flex;flex-direction:column}
#cw-dm-picker.cw-hidden{display:none}
#cw-dm-search{margin:12px;padding:10px 12px;background:var(--bg);border:1px solid var(--border);border-radius:10px;
  color:var(--text);font-size:13px;font-family:inherit}
#cw-dm-list{flex:1;overflow-y:auto}
.cw-dm-row{width:100%;text-align:left;padding:12px 14px;border:none;border-bottom:1px solid var(--border);
  background:transparent;color:var(--text);font-size:13px;cursor:pointer;font-family:inherit}
.cw-dm-row:hover{background:var(--accent-bg);color:var(--accent)}
#cw-empty-hint{flex:1;display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:13px;padding:16px;text-align:center}
#cw-overlay{position:absolute;inset:0;background:var(--card);z-index:3;display:flex;flex-direction:column;overflow:hidden}
#cw-overlay.cw-hidden{display:none}
.cw-overlay-head{padding:12px 14px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:8px}
.cw-overlay-head h3{margin:0;font-size:14px;font-weight:700;color:var(--text);flex:1}
.cw-overlay-back{background:none;border:none;color:var(--muted);font-size:18px;cursor:pointer;padding:0 4px}
.cw-overlay-back:hover{color:var(--text)}
.cw-overlay-body{flex:1;overflow-y:auto;padding:12px 14px}
.cw-overlay-body label{display:block;font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;
  letter-spacing:.5px;margin:10px 0 6px}
.cw-overlay-body label:first-child{margin-top:0}
.cw-overlay-body input,.cw-overlay-body textarea{width:100%;box-sizing:border-box;background:var(--bg);
  border:1px solid var(--border);border-radius:10px;padding:10px 12px;color:var(--text);font-size:13px;font-family:inherit}
.cw-overlay-body textarea{resize:vertical;min-height:56px}
.cw-member-role{font-size:11px;color:var(--muted);margin-top:2px}
.cw-member-chips{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}
.cw-member-chip{display:inline-flex;align-items:center;gap:5px;padding:4px 8px 4px 4px;border-radius:8px;
  background:var(--accent-bg);color:var(--accent);font-size:12px;font-weight:600}
.cw-member-chip .cw-avatar,.cw-member-chip .cw-avatar-ph{width:18px;height:18px;font-size:8px}
.cw-member-chip button{background:none;border:none;color:var(--muted);cursor:pointer;font-size:14px;padding:0 2px}
.cw-user-pick{max-height:140px;overflow-y:auto;border:1px solid var(--border);border-radius:10px}
.cw-user-pick .cw-dm-row:last-child{border-bottom:none}
.cw-overlay-actions{padding:10px 14px;border-top:1px solid var(--border);display:flex;gap:8px;justify-content:flex-end}
.cw-btn-ghost,.cw-btn-primary{padding:9px 16px;border-radius:10px;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit}
.cw-btn-ghost{background:transparent;border:1px solid var(--border);color:var(--text2)}
.cw-btn-primary{background:var(--accent);border:none;color:#0a0e17}
.cw-btn-primary:disabled{opacity:.5;cursor:not-allowed}
.cw-overlay-err{font-size:12px;color:var(--danger);margin-top:8px}
.cw-settings-section{margin-top:16px;padding-top:14px;border-top:1px solid var(--border)}
.cw-settings-section:first-child{margin-top:0;padding-top:0;border-top:none}
.cw-settings-section-title{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);margin:0 0 10px}
.cw-settings-hint{font-size:11px;color:var(--muted);margin:-6px 0 10px;line-height:1.5}
#cw-back-list.cw-hidden{display:none}
.cw-list-topbar{display:none}
@media (max-width:900px){
  .cw-list-topbar{
    display:flex;align-items:center;justify-content:space-between;gap:10px;
    padding:12px 14px 10px;border-bottom:1px solid var(--border);
    flex-shrink:0;background:var(--card);border-radius:14px 14px 0 0;
  }
  body.cw-chat-active .cw-list-topbar{display:none}
  #cw-list-title{font-size:14px;font-weight:700;color:var(--text)}
  #cw-close-list,#cw-close{
    min-width:40px;min-height:40px;display:flex;align-items:center;justify-content:center;
    border-radius:10px;border:1px solid var(--border);background:var(--bg);color:var(--text2);
    font-size:22px;cursor:pointer;z-index:5;pointer-events:auto;
  }
  body.cw-panel-open #cw-list-topbar{pointer-events:auto}
  #cw-close-list:hover,#cw-close:hover{color:var(--accent);border-color:var(--accent)}
  #cw-panel{
    position:fixed!important;top:auto!important;
    left:max(12px,env(safe-area-inset-left,0px))!important;
    right:max(12px,env(safe-area-inset-right,0px))!important;
    width:auto!important;max-width:min(420px,calc(100vw - 24px))!important;
    margin-left:auto!important;margin-right:auto!important;
    border-radius:14px!important;border:1px solid var(--border)!important;
    box-shadow:0 12px 48px rgba(0,0,0,.5)!important;
    z-index:9115!important;
  }
  #cw-panel-left{
    width:100%;max-width:100%;flex:1;min-width:0;border-right:none;
    position:relative;display:flex;flex-direction:column;min-height:0;
  }
  body.cw-chat-active #cw-panel-left{display:none!important;pointer-events:none}
  #cw-panel-right{flex:1;width:100%;min-width:0;min-height:0;display:flex;flex-direction:column}
  body:not(.cw-chat-active) #cw-panel-right{
    visibility:hidden;pointer-events:none;width:0;flex:0;overflow:hidden;
  }
  body.cw-chat-active #cw-panel-right{
    visibility:visible;pointer-events:auto;width:100%;flex:1;min-height:0;
  }
  #cw-panel-header{padding:12px 14px}
  #cw-input-row{
    padding-bottom:max(10px,env(safe-area-inset-bottom,0px));
    padding-left:max(8px,env(safe-area-inset-left,0px));
    padding-right:max(8px,env(safe-area-inset-right,0px));
  }
  #cw-messages{padding-left:max(10px,env(safe-area-inset-left,0px));
    padding-right:max(10px,env(safe-area-inset-right,0px))}
  .cw-msg-wrap{max-width:88%}
  .cw-msg-attach-img img{max-width:min(240px,100%)}
  .cw-react-picker{margin-top:-8px}
  #cw-back-list{display:flex!important}
  /* iOS Safari : empêche le zoom automatique au focus d'un champ
     (déclenché lorsque font-size < 16px). On force 16px sur mobile. */
  #cw-input,
  .cw-edit-area,
  #cw-fwd-search,
  .cw-modal input[type="search"],
  .cw-modal input[type="text"],
  .cw-modal textarea{font-size:16px!important}
}
@media (max-width:900px) and (orientation:landscape){
  body.cw-mobile #cw-panel.cw-hidden{display:none!important}
  body.cw-mobile.cw-panel-open #cw-panel:not(.cw-hidden){
    display:flex!important;
    flex-direction:row!important;
    align-items:stretch!important;
    top:max(8px,env(safe-area-inset-top,0px))!important;
    left:max(12px,env(safe-area-inset-left,0px))!important;
    right:max(12px,env(safe-area-inset-right,0px))!important;
    bottom:max(62px,calc(env(safe-area-inset-bottom,0px) + 62px))!important;
    width:auto!important;
    max-width:none!important;
    margin:0!important;
    height:calc(100dvh - 72px)!important;
    max-height:calc(100dvh - 72px)!important;
    min-height:0!important;
  }
  body.cw-mobile.cw-panel-open #cw-panel-left{
    display:flex!important;
    pointer-events:auto!important;
    flex:0 0 min(168px,34vw)!important;
    width:min(168px,34vw)!important;
    max-width:34vw!important;
    min-width:120px!important;
    border-right:1px solid var(--border)!important;
  }
  body.cw-mobile.cw-panel-open.cw-chat-active #cw-panel-left{
    display:flex!important;
  }
  body.cw-mobile.cw-panel-open #cw-panel-right{
    display:flex!important;
    flex:1!important;
    min-width:0!important;
    width:auto!important;
    visibility:visible!important;
    pointer-events:auto!important;
  }
  body.cw-mobile.cw-panel-open:not(.cw-chat-active) #cw-panel-right{
    visibility:hidden!important;
    pointer-events:none!important;
    width:0!important;
    flex:0!important;
    overflow:hidden!important;
  }
  body.cw-mobile.cw-panel-open.cw-chat-active #cw-panel-right{
    visibility:visible!important;
    pointer-events:auto!important;
    flex:1!important;
    width:auto!important;
  }
  body.cw-mobile.cw-panel-open.cw-chat-active .cw-list-topbar{display:none}
  #cw-panel-header{padding:8px 12px}
  #cw-messages{padding:8px 10px}
  .cw-msg-wrap{max-width:72%}
}
.cw-icon-wrap{position:relative;display:inline-block;flex-shrink:0}
.cw-humeur-badge{position:absolute;bottom:-2px;left:-2px;font-size:14px;line-height:1;pointer-events:auto;filter:drop-shadow(0 1px 2px rgba(0,0,0,.5));cursor:default}
`;

  function escAttr(s) {
    return escCW(s);
  }

  function escCW(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function cwInitials(nom) {
    const p = String(nom || '')
      .trim()
      .split(/\s+/)
      .filter(Boolean);
    if (!p.length) return '?';
    if (p.length === 1) return p[0].slice(0, 2).toUpperCase();
    return (p[0][0] + p[p.length - 1][0]).toUpperCase();
  }

  function cacheUserAvatar(userId, nom, avatarUrl) {
    if (!userId) return;
    CW.avatarByUserId[userId] = {
      nom: nom || '',
      avatar_url: avatarUrl ? String(avatarUrl).trim() : '',
    };
  }

  function cwAvatarHtml(nom, avatarUrl, size) {
    const sz = size || 28;
    const url = avatarUrl ? String(avatarUrl).trim() : '';
    if (url) {
      return (
        '<img class="cw-avatar" src="' +
        escCW(url) +
        '" alt="" width="' +
        sz +
        '" height="' +
        sz +
        '">'
      );
    }
    return (
      '<span class="cw-avatar-ph" aria-hidden="true">' + escCW(cwInitials(nom)) + '</span>'
    );
  }

  const HUMEUR_LABELS={
    '😊':'Joyeux','😩':'Épuisé','😢':'Triste','🤒':'Malade','😐':'Normal',
    '😠':'Colère','🥵':'Chaud','🥶':'Froid','🤮':'Nauséeux','🥱':'Fatigué'
  };

  /** Icône liste / en-tête : emoji canal ou initiales ; avatar photo pour les DM. */
  function cwChannelIconHtml(ch, size) {
    const sz = size || 28;
    if (!ch) return cwAvatarHtml('', '', sz);

    let iconHtml;

    if (ch.type === 'direct') {
      const nom = ch.display_name || ch.name || '';
      if (ch.other_user_id) cacheUserAvatar(ch.other_user_id, nom, ch.other_user_avatar_url || '');
      iconHtml = cwAvatarHtml(nom, ch.other_user_avatar_url || '', sz);
    } else {
      const emoji = (ch.emoji || '').trim();
      if (emoji) {
        const fs = Math.max(14, Math.round(sz * 0.6));
        iconHtml =
          '<span class="cw-avatar-ph cw-chan-emoji" aria-hidden="true" style="width:' +
          sz +
          'px;height:' +
          sz +
          'px;font-size:' +
          fs +
          'px">' +
          escCW(emoji) +
          '</span>';
      } else {
        iconHtml = cwAvatarHtml(ch.display_name || ch.name || 'Canal', '', sz);
      }
    }

    const humeur = ch.type === 'direct' ? (ch.other_user_humeur || '') : '';
    if (humeur) {
      return (
        '<span class="cw-icon-wrap">' +
        iconHtml +
        '<span class="cw-humeur-badge" title="' + escCW(HUMEUR_LABELS[humeur] || '') + '">' +
        escCW(humeur) +
        '</span></span>'
      );
    }
    return iconHtml;
  }

  function fmtTime(iso) {
    if (!iso) return '';
    try {
      const s = String(iso).trim();
      const d = new Date(s.includes('T') ? s : s.replace(' ', 'T'));
      return d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    } catch (e) {
      return '';
    }
  }

  function unlockAudio() {
    if (CW._audioUnlocked) return;
    try {
      if (!CW._audioCtx) CW._audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      if (CW._audioCtx.state === 'suspended') CW._audioCtx.resume();
      CW._audioUnlocked = true;
    } catch (e) {}
  }

  async function jouerSon() {
    if (!CW.soundEnabled) return;
    try {
      if (!CW._audioCtx) CW._audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const ctx = CW._audioCtx;
      if (ctx.state === 'suspended') await ctx.resume();
      const t = ctx.currentTime;
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.connect(g);
      g.connect(ctx.destination);
      o.type = 'sine';
      o.frequency.setValueAtTime(523, t);
      o.frequency.setValueAtTime(659, t + 0.12);
      g.gain.setValueAtTime(0, t);
      g.gain.linearRampToValueAtTime(0.3, t + 0.02);
      g.gain.exponentialRampToValueAtTime(0.001, t + 0.45);
      o.start(t);
      o.stop(t + 0.45);
    } catch (e) {}
  }

  function shouldPlayNotifSound(total) {
    if (!CW._chatSynced) return false;
    const prev = CW.prevUnreadTotal || 0;
    if (total <= prev) return false;
    if (!CW.open) return true;
    return CW.channels.some(
      (c) => c.id !== CW.activeId && (Number(c.unread_count) || 0) > 0
    );
  }

  async function api(path, opts) {
    const r = await fetch(path, { credentials: 'include', ...(opts || {}) });
    if (r.status === 401) throw new Error('auth');
    if (!r.ok) {
      let d = 'Erreur';
      try {
        const j = await r.json();
        d = j.detail ? (typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail)) : d;
      } catch (e) {}
      throw new Error(d);
    }
    if (r.status === 204) return null;
    const ct = r.headers.get('content-type') || '';
    if (ct.includes('application/json')) return r.json();
    return null;
  }

  function syncFromWindow() {
    CW.uid = Number(window.__MYSIFA_UID__) || 0;
    CW.nom = window.__MYSIFA_NOM__ || '';
    CW.role = window.__MYSIFA_ROLE__ || '';
    CW.isPortal = window.__MYSIFA_APP__ === 'portal';
  }

  async function fetchMe() {
    try {
      const u = await api('/api/auth/me');
      if (u && u.id) {
        window.__MYSIFA_UID__ = u.id;
        window.__MYSIFA_NOM__ = u.nom || '';
        window.__MYSIFA_ROLE__ = u.role || '';
        syncFromWindow();
        return true;
      }
    } catch (e) {}
    return false;
  }

  function injectStyles() {
    if (document.getElementById('cw-styles')) return;
    const st = document.createElement('style');
    st.id = 'cw-styles';
    st.textContent = CW_STYLES;
    document.head.appendChild(st);
  }

  function removeChatDom() {
    document.querySelectorAll('#cw-bubble,#cw-bar').forEach((el) => el.remove());
    const panel = document.getElementById('cw-panel');
    if (panel) panel.remove();
  }

  function onChatTriggerClick(e) {
    e.stopPropagation();
    e.preventDefault();
    unlockAudio();
    if (CW.open) closePanel();
    else void openPanel();
  }

  function syncChatTriggerMode() {
    const bar = document.getElementById('cw-bar');
    const panel = document.getElementById('cw-panel');
    if (bar) bar.classList.toggle('cw-portal-accent', CW.isPortal);
    if (panel) {
      const bubbleMode = useChatBubbleTrigger();
      panel.classList.toggle('cw-mode-bubble', bubbleMode);
      panel.classList.toggle('cw-mode-bar', !bubbleMode);
    }
  }

  function setChatTriggerActive(active) {
    const bar = document.getElementById('cw-bar');
    const bub = document.getElementById('cw-bubble');
    if (bar) bar.classList.toggle('cw-bar-active', active);
    if (bub) bub.classList.toggle('cw-bubble-active', active);
  }

  function buildDom() {
    const bubbles = document.querySelectorAll('#cw-bubble');
    const existingPanel = document.getElementById('cw-panel');
    const existingBar = document.getElementById('cw-bar');
    if (bubbles.length === 1 && existingBar && existingPanel) return;
    removeChatDom();

    syncFromWindow();

    const bar = document.createElement('button');
    bar.type = 'button';
    bar.id = 'cw-bar';
    bar.setAttribute('aria-label', 'Messagerie');
    bar.innerHTML =
      '<span class="cw-bar-icon-wrap" id="cw-bar-icon-wrap">' +
      '<span id="cw-bar-icon">' +
      ICO_MSG +
      '</span><span id="cw-bar-badge" aria-label=""></span></span>' +
      '<span class="cw-bar-text" id="cw-bar-text">' +
      '<span id="cw-bar-title">Messagerie</span>' +
      '<span id="cw-bar-preview">Aucun message non lu</span></span>';
    bar.addEventListener('click', onChatTriggerClick);
    document.body.appendChild(bar);

    const bub = document.createElement('button');
    bub.type = 'button';
    bub.id = 'cw-bubble';
    bub.setAttribute('aria-label', 'Messagerie');
    bub.innerHTML =
      '<span class="cw-bubble-ico" aria-hidden="true">' +
      ICO_MSG +
      '</span><span id="cw-bubble-badge" aria-label=""></span>';
    bub.addEventListener('click', onChatTriggerClick);
    document.body.appendChild(bub);

    const panel = document.createElement('div');
    panel.id = 'cw-panel';
    panel.className = 'cw-hidden cw-mode-bubble cw-mode-bar';
    panel.innerHTML =
      '<div id="cw-panel-left">' +
      '<div class="cw-list-topbar">' +
      '<span id="cw-list-title">Messagerie</span>' +
      '<button type="button" id="cw-close-list" aria-label="Fermer la messagerie">×</button></div>' +
      '<div class="cw-list-section cw-list-section-channels">' +
      '<div class="cw-section-row"><span class="cw-section-label">Canaux</span>' +
      '<button type="button" class="cw-section-add cw-hidden" id="cw-add-channel" title="Nouveau canal" aria-label="Nouveau canal">' +
      ICO_PLUS +
      '</button></div><div id="cw-channels"></div></div>' +
      '<div class="cw-list-section cw-list-section-dms">' +
      '<div class="cw-section-row cw-section-discussion"><span class="cw-section-label">Discussion</span>' +
      '<button type="button" class="cw-section-add" id="cw-add-dm" title="Nouvelle discussion" aria-label="Nouvelle discussion">' +
      ICO_PLUS +
      '</button></div><div id="cw-dms"></div></div></div>' +
      '<div id="cw-panel-right">' +
      '<div id="cw-overlay" class="cw-hidden"></div>' +
      '<div id="cw-dm-picker" class="cw-hidden">' +
      '<input type="search" id="cw-dm-search" placeholder="Rechercher un collègue…" autocomplete="off">' +
      '<div id="cw-dm-list"></div></div>' +
      '<div id="cw-panel-header">' +
      '<button type="button" class="cw-header-btn cw-hidden" id="cw-back-list" aria-label="Retour aux conversations">←</button>' +
      '<span id="cw-header-avatar" class="cw-header-avatar cw-hidden"></span>' +
      '<span id="cw-panel-title">Messagerie</span>' +
      '<button type="button" class="cw-header-btn cw-hidden" id="cw-channel-info" title="Réglages du canal" aria-label="Réglages du canal">' +
      ICO_SETTINGS +
      '</button>' +
      '<button type="button" id="cw-close" aria-label="Fermer">×</button></div>' +
      '<div id="cw-messages"><div id="cw-empty-hint">Sélectionnez un canal</div></div>' +
      '<div id="cw-typing-bar"></div>' +
      '<div id="cw-pending-row"></div>' +
      '<div id="cw-input-row">' +
      '<input type="file" id="cw-file-input" accept=".jpg,.jpeg,.png,.webp,.gif,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.zip">' +
      '<button type="button" id="cw-attach" aria-label="Pièce jointe" title="Pièce jointe">' +
      ICO_ATTACH +
      '</button>' +
      '<textarea id="cw-input" rows="1" placeholder="Message…"></textarea>' +
      '<button type="button" id="cw-send" aria-label="Envoyer">' +
      ICO_SEND +
      '</button></div></div>';
    document.body.appendChild(panel);

    document.getElementById('cw-close').addEventListener('click', (e) => {
      e.stopPropagation();
      closePanel();
    });
    document.getElementById('cw-close-list')?.addEventListener('click', (e) => {
      e.stopPropagation();
      closePanel();
    });
    document.getElementById('cw-back-list')?.addEventListener('click', mobileBackToList);
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && CW.open) closePanel();
    });
    document.getElementById('cw-attach').addEventListener('click', () => {
      document.getElementById('cw-file-input')?.click();
    });
    const fileInp = document.getElementById('cw-file-input');
    if (fileInp) {
      fileInp.addEventListener('change', () => {
        const f = fileInp.files && fileInp.files[0];
        CW.pendingFile = f || null;
        renderPendingAttachment();
        fileInp.value = '';
      });
    }
    document.getElementById('cw-send').addEventListener('click', () => sendMessage());
    document.getElementById('cw-add-dm').addEventListener('click', () => openNewDm());
    document.getElementById('cw-add-channel').addEventListener('click', () => openNewChannel());
    document.getElementById('cw-channel-info').addEventListener('click', () => openChannelSettings());
    syncAdminButtons();
    const inp = document.getElementById('cw-input');
    inp.addEventListener('keydown', (e) => {
      const CM = window.ChatMentions;
      if (CM && CM.handleEnterKey) {
        CM.handleEnterKey(e, inp, sendMessage, null);
        return;
      }
      if (e.key === 'Enter' && (e.shiftKey || e.ctrlKey || e.altKey)) {
        e.preventDefault();
        const start = inp.selectionStart;
        const end = inp.selectionEnd;
        inp.value = inp.value.slice(0, start) + '\n' + inp.value.slice(end);
        inp.setSelectionRange(start + 1, start + 1);
        inp.dispatchEvent(new Event('input', { bubbles: true }));
        return;
      }
      if (e.key === 'Enter') {
        e.preventDefault();
        sendMessage();
      }
    });
    inp.addEventListener('input', function () {
      resizeCwInput(this);
      signalTyping();
    });
    const msgBox = document.getElementById('cw-messages');
    if (msgBox) msgBox.addEventListener('scroll', hideReactionTip, { passive: true });
    syncChatTriggerMode();
    syncMobileChatUi();
    dockLayout();
  }

  function stopTypingPolls() {
    if (CW.typingPollTimer) {
      clearInterval(CW.typingPollTimer);
      CW.typingPollTimer = null;
    }
    const bar = document.getElementById('cw-typing-bar');
    if (bar) bar.innerHTML = '';
  }

  function signalTyping() {
    if (!CW.activeId) return;
    const now = Date.now();
    if (now - CW._lastTypingSent < 2800) return;
    CW._lastTypingSent = now;
    api('/api/chat/channels/' + CW.activeId + '/typing', { method: 'POST' }).catch(() => {});
  }

  async function pollTyping() {
    if (!CW.activeId || !CW.open) return;
    try {
      const data = await api('/api/chat/channels/' + CW.activeId + '/typing');
      const bar = document.getElementById('cw-typing-bar');
      if (!bar) return;
      const typists = data.typists || [];
      if (!typists.length) {
        bar.innerHTML = '';
        return;
      }
      let label = '';
      if (typists.length === 1) {
        label = escCW(typists[0]) + " est en train d'écrire";
      } else if (typists.length === 2) {
        label = escCW(typists[0]) + ' et ' + escCW(typists[1]) + ' écrivent';
      } else {
        label = typists.length + ' personnes écrivent';
      }
      bar.innerHTML =
        '<span class="cw-typing-dot"></span>' +
        '<span class="cw-typing-dot"></span>' +
        '<span class="cw-typing-dot"></span>' +
        '<span style="margin-left:4px">' +
        label +
        '</span>';
    } catch (e) {}
  }

  function startTypingPoll() {
    stopTypingPolls();
    if (CW.typingPollTimer) clearInterval(CW.typingPollTimer);
    CW.typingPollTimer = setInterval(pollTyping, 2500);
    pollTyping();
  }

  async function fetchReadStatus(channelId) {
    try {
      const members = await api('/api/chat/channels/' + channelId + '/members');
      const status = {};
      (members || []).forEach((m) => {
        status[m.id] = m.last_read_at || null;
      });
      CW.memberReadStatus = status;
      updateReadReceipts();
    } catch (e) {}
  }

  function appendReadReceipt(msgWrap, className, content, asHtml) {
    const receipt = document.createElement('div');
    receipt.className = 'cw-read-receipt ' + className;
    if (asHtml) receipt.innerHTML = content;
    else receipt.textContent = content;
    msgWrap.appendChild(receipt);
  }

  function updateReadReceipts() {
    document.querySelectorAll('.cw-read-receipt').forEach((el) => el.remove());

    const ch = CW.channels.find((c) => c.id === CW.activeId);
    if (!ch) return;
    const box = document.getElementById('cw-messages');
    if (!box) return;

    const myMsgs = [...box.querySelectorAll('.cw-msg-wrap.cw-mine[data-id]')].reverse();
    if (!myMsgs.length) return;

    if (ch.type === 'direct') {
      const otherId = ch.other_user_id;
      const otherReadAt = CW.memberReadStatus[otherId];
      if (!otherReadAt) return;

      for (const msgWrap of myMsgs) {
        const msgAt = msgWrap.dataset.at;
        if (!msgAt) continue;
        if (otherReadAt >= msgAt) {
          appendReadReceipt(
            msgWrap,
            'cw-read-vu',
            '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor"' +
              ' stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
              '<polyline points="20 6 9 17 4 12"/></svg>Vu',
            true
          );
          break;
        }
      }
    } else {
      const lastMyMsg = myMsgs[0];
      if (!lastMyMsg) return;
      const lastAt = lastMyMsg.dataset.at;
      if (!lastAt) return;
      const readCount = Object.entries(CW.memberReadStatus).filter(
        ([uid, at]) => Number(uid) !== Number(CW.uid) && at && at >= lastAt
      ).length;
      if (readCount > 0) {
        appendReadReceipt(
          lastMyMsg,
          'cw-read-count',
          readCount + ' vu' + (readCount > 1 ? 's' : ''),
          false
        );
      }
    }
  }

  const CW_INPUT_MIN_H = 38;

  function resizeCwInput(el) {
    if (!el) return;
    el.style.height = CW_INPUT_MIN_H + 'px';
    if (!el.value) return;
    el.style.height = 'auto';
    el.style.height = Math.min(Math.max(CW_INPUT_MIN_H, el.scrollHeight), 96) + 'px';
  }

  const CW_MOBILE_BP = '(max-width: 900px)';
  const CW_MOBILE_LANDSCAPE_BP = '(max-width: 900px) and (orientation: landscape)';

  function isCwMobile() {
    return window.matchMedia(CW_MOBILE_BP).matches;
  }

  function isCwMobileLandscape() {
    return window.matchMedia(CW_MOBILE_LANDSCAPE_BP).matches;
  }

  /** Bulle (mobile + desktop hors portail) vs barre bas-gauche (portail desktop). */
  function useChatBubbleTrigger() {
    return isCwMobile() || !CW.isPortal;
  }

  const CW_PANEL_DOCK_STYLE_KEYS = [
    'display',
    'flexDirection',
    'alignItems',
    'width',
    'height',
    'maxHeight',
    'minHeight',
    'left',
    'right',
    'bottom',
    'top',
    'maxWidth',
    'marginLeft',
    'marginRight',
    'borderRadius',
  ];

  function clearPanelDockStyles(panel) {
    if (!panel) return;
    CW_PANEL_DOCK_STYLE_KEYS.forEach((k) => {
      panel.style[k] = '';
    });
  }

  function syncMobileChatUi() {
    const mobile = isCwMobile();
    const landscape = isCwMobileLandscape();
    const bubbleTrigger = useChatBubbleTrigger();
    document.body.classList.toggle('cw-mobile', mobile);
    document.body.classList.toggle('cw-use-bubble', bubbleTrigger);
    document.body.classList.toggle('cw-mobile-landscape', mobile && landscape);
    document.body.classList.toggle('cw-panel-open', bubbleTrigger && CW.open);
    document.body.classList.toggle('cw-chat-active', mobile && CW.open && !!CW.activeId);
    const backBtn = document.getElementById('cw-back-list');
    if (backBtn) {
      backBtn.classList.toggle('cw-hidden', !mobile || !CW.activeId);
    }
    const panel = document.getElementById('cw-panel');
    if (panel && !bubbleTrigger) {
      clearPanelDockStyles(panel);
    } else if (panel && bubbleTrigger && !CW.open) {
      clearPanelDockStyles(panel);
    }
    syncChatTriggerMode();
    if (bubbleTrigger && CW.open) {
      dockLayout();
      return;
    }
    if (!mobile && CW.open) positionDesktopPanel();
  }

  function mobileBackToList() {
    CW.activeId = null;
    CW.lastMsgId = 0;
    stopTypingPolls();
    if (CW.pollTimer) {
      clearInterval(CW.pollTimer);
      CW.pollTimer = null;
    }
    const box = document.getElementById('cw-messages');
    if (box) box.innerHTML = '<div id="cw-empty-hint">Sélectionnez un canal</div>';
    updateChannelHeader();
    renderChannelLists();
    syncMobileChatUi();
  }

  function dockLayout() {
    if (window.MySifaDock && typeof window.MySifaDock.layout === 'function') {
      window.MySifaDock.layout();
    }
  }

  /** Desktop portail : panneau au-dessus de la barre messagerie (bas-gauche). */
  function positionDesktopPanel() {
    if (isCwMobile() || useChatBubbleTrigger()) return;
    const bar = document.getElementById('cw-bar');
    const panel = document.getElementById('cw-panel');
    if (!bar || !panel || panel.classList.contains('cw-hidden')) return;
    const gap = 14;
    const rect = bar.getBoundingClientRect();
    panel.style.left = Math.max(12, rect.left) + 'px';
    panel.style.right = 'auto';
    panel.style.bottom = window.innerHeight - rect.top + gap + 'px';
    panel.style.top = 'auto';
  }

  function attachmentHtml(msg) {
    if (!msg.attachment_url) return '';
    const url = escAttr(msg.attachment_url);
    const name = escCW(msg.attachment_name || 'Pièce jointe');
    const mime = (msg.attachment_mime || '').toLowerCase();
    if (mime.indexOf('image/') === 0) {
      return (
        '<a class="cw-msg-attach cw-msg-attach-img" href="' +
        url +
        '" target="_blank" rel="noopener noreferrer">' +
        '<img src="' +
        url +
        '" alt="' +
        name +
        '"></a>'
      );
    }
    return (
      '<a class="cw-msg-attach cw-msg-attach-file" href="' +
      url +
      '" target="_blank" rel="noopener noreferrer" download>' +
      name +
      '</a>'
    );
  }

  function renderPendingAttachment() {
    const row = document.getElementById('cw-pending-row');
    if (!row) return;
    if (!CW.pendingFile) {
      row.classList.remove('cw-show');
      row.innerHTML = '';
      return;
    }
    row.classList.add('cw-show');
    row.innerHTML =
      '<div class="cw-pending-chip"><span>' +
      escCW(CW.pendingFile.name) +
      '</span><button type="button" aria-label="Retirer la pièce jointe" id="cw-pending-clear">×</button></div>';
    document.getElementById('cw-pending-clear')?.addEventListener('click', () => {
      CW.pendingFile = null;
      renderPendingAttachment();
    });
  }

  function getReactionTipEl() {
    let tip = document.getElementById('cw-reaction-tip-float');
    if (!tip) {
      tip = document.createElement('div');
      tip.id = 'cw-reaction-tip-float';
      tip.setAttribute('role', 'tooltip');
      document.body.appendChild(tip);
    }
    return tip;
  }

  function hideReactionTip() {
    const tip = document.getElementById('cw-reaction-tip-float');
    if (tip) tip.style.display = 'none';
  }

  function positionReactionTip(anchor, tip) {
    const r = anchor.getBoundingClientRect();
    const gap = 6;
    let top = r.top - tip.offsetHeight - gap;
    let left = r.left + r.width / 2 - tip.offsetWidth / 2;
    const pad = 8;
    if (top < pad) top = r.bottom + gap;
    if (left < pad) left = pad;
    if (left + tip.offsetWidth > window.innerWidth - pad) {
      left = window.innerWidth - tip.offsetWidth - pad;
    }
    tip.style.top = top + 'px';
    tip.style.left = left + 'px';
  }

  function showReactionTip(btn, users) {
    if (!users || !users.length) return;
    const tip = getReactionTipEl();
    tip.innerHTML = users
      .map((u) => '<span class="cw-tip-name">' + escCW(u) + '</span>')
      .join('');
    tip.style.display = 'block';
    positionReactionTip(btn, tip);
  }

  function attachReactionTip(btn) {
    let users = [];
    try {
      users = JSON.parse(btn.getAttribute('data-users') || '[]');
    } catch (e) {
      users = [];
    }
    if (!users.length) return;
    btn.addEventListener('mouseenter', () => showReactionTip(btn, users));
    btn.addEventListener('mouseleave', hideReactionTip);
    btn.addEventListener('focus', () => showReactionTip(btn, users));
    btn.addEventListener('blur', hideReactionTip);
  }

  function buildReactionsHtml(reactions) {
    if (!reactions || !reactions.length) return '';
    return (
      '<div class="cw-reactions">' +
      reactions
        .map((rx) => {
          const mine = !!rx.reacted_by_me;
          const users = rx.users || [];
          const label = mine
            ? 'Retirer votre réaction ' + rx.emoji
            : users.length
              ? users.join(', ')
              : 'Réagir ' + rx.emoji;
          return (
            '<button type="button" class="cw-reaction-pill' +
            (mine ? ' cw-reacted' : '') +
            '" data-emoji="' +
            rx.emoji +
            '" data-mine="' +
            (mine ? '1' : '0') +
            '" data-users="' +
            escAttr(JSON.stringify(users)) +
            '" title="' +
            escCW(label) +
            '" aria-label="' +
            escCW(rx.emoji + ' — ' + (users.length ? users.join(', ') : '')) +
            '">' +
            rx.emoji +
            '<span class="cw-reaction-count">' +
            rx.count +
            '</span></button>'
          );
        })
        .join('') +
      '</div>'
    );
  }

  function bindReactionHandlers(wrap, msgId) {
    wrap.querySelectorAll('.cw-reaction-pill').forEach((btn) => attachReactionTip(btn));
    wrap.querySelectorAll('.cw-react-btn, .cw-reaction-pill').forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const emoji = btn.dataset.emoji;
        if (!emoji || !CW.activeId) return;
        try {
          await api(
            '/api/chat/channels/' + CW.activeId + '/messages/' + msgId + '/reactions',
            {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ emoji }),
            }
          );
          await refreshVisibleReactions();
        } catch (ex) {}
      });
    });
  }

  async function refreshVisibleReactions() {
    if (!CW.activeId) return;
    const box = document.getElementById('cw-messages');
    if (!box) return;
    try {
      const data = await api('/api/chat/channels/' + CW.activeId + '/messages');
      (data.messages || []).forEach((m) => {
        const wrap = box.querySelector('.cw-msg-wrap[data-id="' + m.id + '"]');
        if (!wrap) return;
        const html = buildReactionsHtml(m.reactions || []);
        const existing = wrap.querySelector('.cw-reactions');
        if (html) {
          if (existing) existing.outerHTML = html;
          else wrap.insertAdjacentHTML('beforeend', html);
        } else if (existing) existing.remove();
        bindReactionHandlers(wrap, m.id);
      });
      hideReactionTip();
    } catch (e) {}
  }

  // ── Date separators ──────────────────────────────────────
  function cwDateKey(iso) {
    if (!iso) return '';
    try { const d = new Date(iso.replace(' ','T')); return d.getFullYear()+'-'+(d.getMonth()+1)+'-'+d.getDate(); } catch(e) { return ''; }
  }
  function cwFmtDate(iso) {
    try {
      const d = new Date(iso.replace(' ','T'));
      const now = new Date();
      const diff = Math.round((new Date(now.getFullYear(),now.getMonth(),now.getDate()) - new Date(d.getFullYear(),d.getMonth(),d.getDate()))/86400000);
      if (diff === 0) return "Aujourd'hui";
      if (diff === 1) return 'Hier';
      return d.toLocaleDateString('fr-FR',{weekday:'long',day:'numeric',month:'long',year:'numeric'});
    } catch(e) { return ''; }
  }
  function cwBuildDateSep(iso) {
    const el = document.createElement('div');
    el.className = 'cw-date-sep';
    el.dataset.dk = cwDateKey(iso);
    el.innerHTML = '<span class="cw-date-sep-lbl">' + escCW(cwFmtDate(iso)) + '</span>';
    return el;
  }
  // ── Reply bar ─────────────────────────────────────────────
  function cwEnsureReplyBar() {
    if (document.getElementById('cw-reply-bar')) return;
    const panel = document.getElementById('cw-panel');
    const inputRow = document.getElementById('cw-input-row') || (panel && panel.querySelector('#cw-pending-row'));
    if (!inputRow) return;
    const bar = document.createElement('div');
    bar.id = 'cw-reply-bar';
    bar.innerHTML = '<div class="cw-rp-preview"><div class="cw-rp-name" id="cw-rp-name"></div><div class="cw-rp-body" id="cw-rp-body"></div></div><button type="button" class="cw-rp-cancel" id="cw-rp-cancel">×</button>';
    inputRow.parentNode.insertBefore(bar, inputRow);
    document.getElementById('cw-rp-cancel').addEventListener('click', cwCancelReply);
  }
  function cwStartReply(msg) {
    CW._replyToId = msg.id;
    cwEnsureReplyBar();
    const bar = document.getElementById('cw-reply-bar');
    if (bar) bar.classList.add('cw-show');
    const n = document.getElementById('cw-rp-name');
    const b = document.getElementById('cw-rp-body');
    if (n) n.textContent = msg.user_nom || '';
    if (b) b.textContent = (msg.body || '(pièce jointe)').substring(0,80);
    const inp = document.getElementById('cw-input');
    if (inp) inp.focus();
  }
  function cwCancelReply() {
    CW._replyToId = null;
    const bar = document.getElementById('cw-reply-bar');
    if (bar) bar.classList.remove('cw-show');
  }
  // ── Delete ────────────────────────────────────────────────
  async function cwDeleteMsg(msgId) {
    if (!CW.activeId) return;
    try {
      await api('/api/chat/channels/'+CW.activeId+'/messages/'+msgId, {method:'DELETE'});
      const wrap = document.querySelector('.cw-msg-wrap[data-id="'+msgId+'"]');
      if (wrap) {
        const mine = wrap.classList.contains('cw-mine');
        const bbl = wrap.querySelector('.cw-msg-mine,.cw-msg-theirs');
        if (bbl) { bbl.innerHTML = 'Message supprimé.'; bbl.className = (mine?'cw-msg-mine':'cw-msg-theirs')+' cw-msg-deleted'; }
        wrap.querySelectorAll('.cw-msg-reply-ctx,.cw-msg-fwd-tag,.cw-reactions,.cw-msg-menu-btn,.cw-msg-menu,.cw-react-picker').forEach(e=>e.remove());
      }
    } catch(e) { console.warn('[cw]',e); }
  }
  // ── Edit ──────────────────────────────────────────────────
  function cwStartEdit(wrap, msg) {
    const bbl = wrap.querySelector('.cw-msg-mine,.cw-msg-theirs');
    if (!bbl) return;
    const origHtml = bbl.innerHTML;
    const txt = (msg.body||'').replace(/</g,'&lt;');
    bbl.innerHTML = '<textarea class="cw-edit-ta" rows="2">'+txt+'</textarea><div class="cw-edit-row"><button type="button">Annuler</button><button type="button" class="ok">Enregistrer</button></div>';
    const ta = bbl.querySelector('.cw-edit-ta');
    const [cancelBtn, saveBtn] = bbl.querySelectorAll('.cw-edit-row button');
    if (ta) { ta.focus(); ta.style.height = ta.scrollHeight+'px'; }
    cancelBtn.addEventListener('click', () => { bbl.innerHTML = origHtml; });
    saveBtn.addEventListener('click', async () => {
      const nb = (ta.value||'').trim();
      if (!nb) return;
      try {
        await api('/api/chat/channels/'+CW.activeId+'/messages/'+msg.id, {
          method:'PATCH', headers:{'Content-Type':'application/json'}, body:JSON.stringify({body:nb})
        });
        bbl.innerHTML = origHtml;
        // Reload to get updated content
        const box = document.getElementById('cw-messages');
        if (box) { const was = isNearBottom(box,40); await CW.selectChannel(CW.activeId); if(was) scrollMessagesBottom(); }
      } catch(e) { console.warn('[cw]',e); }
    });
  }
  // ── Forward ───────────────────────────────────────────────
  async function cwStartForward(msg) {
    let users = [];
    try { users = (await api('/api/chat/users'))||[]; } catch(e) { return; }
    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;inset:0;z-index:9500;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center;padding:16px';
    let sel = new Set();
    function renderList(q) {
      const ql=(q||'').toLowerCase();
      const list=users.filter(u=>Number(u.id)!==Number(CW.uid)&&(!ql||(u.nom||'').toLowerCase().includes(ql)));
      const el=overlay.querySelector('#cw-fwd-list');
      if(!el) return;
      el.innerHTML=list.map(u=>'<button type="button" style="display:block;width:100%;text-align:left;padding:10px 12px;border:none;border-bottom:1px solid var(--border);background:'+(sel.has(u.id)?'var(--accent-bg)':'')+';color:'+(sel.has(u.id)?'var(--accent)':'var(--text)')+';font-family:inherit;font-size:13px;cursor:pointer" data-uid="'+u.id+'">'+escCW(u.nom||'')+(sel.has(u.id)?' ✓':'')+'</button>').join('')||'<p style="padding:10px;color:var(--muted);font-size:12px;margin:0">Aucun résultat</p>';
      el.querySelectorAll('button[data-uid]').forEach(b=>{b.addEventListener('click',()=>{const id=parseInt(b.dataset.uid,10);if(sel.has(id))sel.delete(id);else sel.add(id);const sb=overlay.querySelector('#cw-fwd-ok');if(sb)sb.disabled=sel.size===0;renderList(overlay.querySelector('#cw-fwd-search').value);});});
    }
    overlay.innerHTML='<div style="background:var(--card);border:1px solid var(--border);border-radius:14px;padding:20px;width:min(420px,100%);max-height:80vh;overflow-y:auto">'+
      '<div style="font-size:15px;font-weight:700;margin-bottom:12px">Transférer le message</div>'+
      '<div style="padding:5px 9px;margin-bottom:10px;border-left:3px solid var(--muted);background:var(--accent-bg);border-radius:6px;font-size:12px;color:var(--text2)">'+escCW((msg.body||'(pièce jointe)').substring(0,60))+'</div>'+
      '<input type="search" id="cw-fwd-search" placeholder="Rechercher…" style="width:100%;padding:8px 12px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-family:inherit;margin-bottom:8px;box-sizing:border-box">'+
      '<div id="cw-fwd-list" style="max-height:180px;overflow-y:auto;border:1px solid var(--border);border-radius:8px"></div>'+
      '<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:12px">'+
      '<button type="button" style="padding:9px 16px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-family:inherit;font-size:13px" onclick="this.closest(\'[style*=fixed]\').remove()">Annuler</button>'+
      '<button type="button" id="cw-fwd-ok" disabled style="padding:9px 16px;border-radius:8px;border:none;background:var(--accent);color:var(--bg);font-weight:700;cursor:pointer;font-family:inherit;font-size:13px">Transférer</button></div></div>';
    document.body.appendChild(overlay);
    overlay.addEventListener('click',e=>{if(e.target===overlay)overlay.remove();});
    renderList('');
    overlay.querySelector('#cw-fwd-search').addEventListener('input',function(){renderList(this.value);});
    overlay.querySelector('#cw-fwd-ok').addEventListener('click',async()=>{
      if(!sel.size)return;
      try {
        await api('/api/chat/channels/'+CW.activeId+'/messages/'+msg.id+'/forward',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_ids:[...sel]})});
        overlay.remove();
      } catch(e){console.warn('[cw]',e);}
    });
    setTimeout(()=>overlay.querySelector('#cw-fwd-search').focus(),50);
  }
  // ── Close menus on outside click ──────────────────────────
  document.addEventListener('click',()=>{
    document.querySelectorAll('.cw-msg-menu.cw-open').forEach(m=>m.classList.remove('cw-open'));
  });

  function renderMsg(msg) {
    const mine = Number(msg.user_id) === Number(CW.uid) || msg.is_mine;
    cacheUserAvatar(msg.user_id, msg.user_nom, msg.avatar_url);

    const pickerBtns = CW_EMOJIS.map(
      (e) =>
        '<button type="button" class="cw-react-btn" data-emoji="' +
        e +
        '" title="' +
        e +
        '" aria-label="Réagir ' +
        e +
        '">' +
        e +
        '</button>'
    ).join('');
    const picker = '<div class="cw-react-picker" aria-label="Réactions">' + pickerBtns + '</div>';

    const body = (msg.body || '').trim();
    let bodyHtml = '';
    if (body) {
      if (window.ChatMentions && window.ChatMentions.formatBodyHtml) {
        bodyHtml = window.ChatMentions.formatBodyHtml(body, [], escCW);
      } else {
        bodyHtml = escCW(body).replace(/\r\n/g, '\n').replace(/\n/g, '<br>');
      }
    }
    const bubble =
      '<div class="' +
      (mine ? 'cw-msg-mine' : 'cw-msg-theirs') +
      '">' +
      bodyHtml +
      attachmentHtml(msg) +
      '</div>';

    const rxHtml = buildReactionsHtml(msg.reactions || []);

    const wrap = document.createElement('div');
    wrap.className = 'cw-msg-wrap ' + (mine ? 'cw-mine' : 'cw-theirs');
    wrap.dataset.id = String(msg.id);
    if (msg.created_at) wrap.dataset.at = String(msg.created_at);
    wrap.style.position = 'relative';
    wrap._cwMsg = msg; // store msg data for actions

    // ── Soft-deleted placeholder ───────────────────────────
    if (msg.is_soft_deleted) {
      const cls = mine ? 'cw-msg-mine' : 'cw-msg-theirs';
      wrap.innerHTML = '<div class="cw-msg-bubble-wrap"><div class="'+cls+' cw-msg-deleted">Message supprimé.</div></div>';
      return wrap;
    }

    // ── Reply context ──────────────────────────────────────
    let replyHtml = '';
    if (msg.reply_to) {
      const rb = msg.reply_to.is_soft_deleted ? '<em>Message supprimé</em>' : escCW((msg.reply_to.body||'').substring(0,80));
      replyHtml = '<div class="cw-msg-reply-ctx" data-reply-id="'+msg.reply_to.id+'"><div class="cw-reply-name">'+escCW(msg.reply_to.user_nom||'')+'</div><div class="cw-reply-body">'+rb+'</div></div>';
    }

    // ── Forwarded indicator ────────────────────────────────
    let fwdHtml = '';
    if (msg.is_forwarded) {
      fwdHtml = '<div class="cw-msg-fwd-tag"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="15 10 20 15 15 20"/><path d="M4 4v7a4 4 0 0 0 4 4h12"/></svg>Transféré'+(msg.forwarded_from_nom?' · '+escCW(msg.forwarded_from_nom):'')+'</div>';
    }
    const fwdCls = msg.is_forwarded ? ' cw-msg-fwd' : '';

    // ── Edited label ───────────────────────────────────────
    let editedLbl = '';
    if (msg.edited_at) {
      try {
        const ed = new Date(msg.edited_at.replace(' ','T'));
        editedLbl = '<span class="cw-msg-edited-lbl">modifié le '+ed.toLocaleDateString('fr-FR',{day:'2-digit',month:'2-digit'})+'</span>';
      } catch(e) {}
    }

    const bubbleFull = '<div class="'+(mine?'cw-msg-mine':'cw-msg-theirs')+fwdCls+'">' + bodyHtml + attachmentHtml(msg) + '</div>';

    wrap.innerHTML =
      '<div class="cw-msg-bubble-wrap">' + replyHtml + fwdHtml + bubbleFull + picker + '</div>' + rxHtml;
    bindReactionHandlers(wrap, msg.id);

    // ── Scroll to reply on click ───────────────────────────
    const rctx = wrap.querySelector('.cw-msg-reply-ctx');
    if (rctx) {
      rctx.addEventListener('click', () => {
        const id = rctx.dataset.replyId;
        const target = document.querySelector('.cw-msg-wrap[data-id="'+id+'"]');
        if (target) { target.scrollIntoView({behavior:'smooth',block:'center'}); target.style.outline='2px solid var(--accent)'; setTimeout(()=>{target.style.outline='';},1200); }
      });
    }

    // ── Header : nom · heure [modifié] + bouton ⋮ ─────────
    const ch = CW.channels.find(c=>c.id===CW.activeId);
    const isAdmin = ['superadmin','direction','administration'].includes(CW.role);
    const msgAge = Date.now()-new Date((msg.created_at||'').replace(' ','T')).getTime();
    const canEdit = mine && !msg.attachment_url && msgAge < 900000;
    const canDel = mine;
    const canPin = ch && ch.type==='channel' && isAdmin;

    const header = document.createElement('div');
    header.className = 'cw-msg-header';

    const headerText = document.createElement('span');
    headerText.className = 'cw-msg-header-text';
    headerText.textContent = (mine ? '' : (msg.user_nom||'') + ' · ') + fmtTime(msg.created_at||'');
    if (editedLbl) headerText.innerHTML += '<span class="cw-msg-edited-lbl">modifié</span>';

    const menuBtn = document.createElement('button');
    menuBtn.type = 'button';
    menuBtn.className = 'cw-msg-menu-btn';
    menuBtn.title = 'Options';
    menuBtn.setAttribute('aria-label', 'Options du message');
    menuBtn.setAttribute('aria-haspopup', 'true');
    menuBtn.setAttribute('aria-expanded', 'false');
    menuBtn.innerHTML =
      '<svg viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">'+
      '<circle cx="8" cy="3" r="1.5"/><circle cx="8" cy="8" r="1.5"/><circle cx="8" cy="13" r="1.5"/>'+
      '</svg>';

    const menu = document.createElement('div');
    menu.className = 'cw-msg-menu';
    menu.setAttribute('role', 'menu');

    // Icones SVG inline pour les actions
    const ICO = {
      reply: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="9 17 4 12 9 7"/><path d="M20 18v-2a4 4 0 0 0-4-4H4"/></svg>',
      edit:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4z"/></svg>',
      fwd:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="15 17 20 12 15 7"/><path d="M4 18v-2a4 4 0 0 1 4-4h12"/></svg>',
      pin:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="12" y1="17" x2="12" y2="22"/><path d="M5 17h14l-2-5V5a2 2 0 0 0-2-2H9a2 2 0 0 0-2 2v7z"/></svg>',
      unpin: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="2" y1="2" x2="22" y2="22"/><path d="M5 17h14l-2-5V5a2 2 0 0 0-2-2H9"/></svg>',
      del:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"/></svg>',
    };

    const mkItem = (icon, label, cls, cb) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'cw-msg-menu-item'+(cls?' '+cls:'');
      b.setAttribute('role', 'menuitem');
      b.innerHTML = icon + '<span>' + escCW(label) + '</span>';
      b.addEventListener('click', e => { e.stopPropagation(); closeMenu(); cb(); });
      return b;
    };
    const addSep = () => {
      const s = document.createElement('div');
      s.className = 'cw-msg-menu-sep';
      s.setAttribute('role', 'separator');
      menu.appendChild(s);
    };

    menu.appendChild(mkItem(ICO.reply, 'Répondre', '', ()=>cwStartReply(msg)));
    if (canEdit) menu.appendChild(mkItem(ICO.edit, 'Modifier', '', ()=>cwStartEdit(wrap,msg)));
    menu.appendChild(mkItem(ICO.fwd, 'Transférer', '', ()=>cwStartForward(msg)));
    if (canPin) menu.appendChild(mkItem(
      msg.pinned_at?ICO.unpin:ICO.pin,
      msg.pinned_at?'Désépingler':'Épingler', '', ()=>{
        api('/api/chat/channels/'+CW.activeId+'/messages/'+msg.id+'/pin',{method:msg.pinned_at?'DELETE':'POST'}).then(()=>CW.selectChannel(CW.activeId)).catch(()=>{});
      }
    ));
    if (canDel) {
      addSep();
      menu.appendChild(mkItem(ICO.del, 'Supprimer', 'cw-danger', ()=>cwDeleteMsg(msg.id)));
    }

    const closeMenu = () => {
      menu.classList.remove('cw-open','cw-menu-up');
      menuBtn.setAttribute('aria-expanded', 'false');
    };
    const openMenu = () => {
      // Décision flip up/down : si pas assez de place sous le bouton, on ouvre vers le haut.
      menu.classList.remove('cw-menu-up');
      menu.classList.add('cw-open');
      menuBtn.setAttribute('aria-expanded', 'true');
      requestAnimationFrame(() => {
        const rect = menu.getBoundingClientRect();
        const box = document.getElementById('cw-messages');
        const limit = box ? box.getBoundingClientRect().bottom : window.innerHeight;
        if (rect.bottom > limit - 8) menu.classList.add('cw-menu-up');
      });
    };

    menuBtn.addEventListener('click', e => {
      e.stopPropagation();
      const was = menu.classList.contains('cw-open');
      document.querySelectorAll('.cw-msg-menu.cw-open').forEach(m => {
        m.classList.remove('cw-open','cw-menu-up');
        const b = m.parentElement && m.parentElement.querySelector('.cw-msg-menu-btn');
        if (b) b.setAttribute('aria-expanded', 'false');
      });
      if (!was) openMenu();
    });

    // Ordre DOM : [⋮, menu, nom/heure]
    // - Messages reçus (flex normal)     → ⋮ à gauche, nom/heure à droite
    // - Mes messages   (flex-direction:row-reverse) → ⋮ à droite, heure à gauche
    header.appendChild(menuBtn);
    header.appendChild(menu);
    header.appendChild(headerText);
    wrap.insertBefore(header, wrap.firstChild);
    return wrap;
  }

  function isNearBottom(el, tol) {
    return el.scrollHeight - el.scrollTop - el.clientHeight < (tol || 40);
  }

  function scrollMessagesBottom() {
    const box = document.getElementById('cw-messages');
    if (box) requestAnimationFrame(() => { box.scrollTop = box.scrollHeight; });
  }

  function renderChannelItem(ch) {
    const btn = document.createElement('button');
    btn.type = 'button';
    const unread = Number(ch.unread_count) || 0;
    let cls = 'cw-channel-item';
    if (ch.id === CW.activeId) cls += ' cw-active';
    if (unread > 0) cls += ' cw-unread';
    btn.className = cls;
    btn.dataset.id = String(ch.id);
    const label = ch.display_name || ch.name || (ch.type === 'direct' ? 'Message' : 'Canal');
    btn.innerHTML =
      cwChannelIconHtml(ch, 28) +
      '<span class="cw-chan-body"><span class="cw-chan-label">' +
      escCW(label) +
      '</span>' +
      (unread > 0
        ? '<span class="cw-unread-badge">' + escCW(unread > 99 ? '99+' : unread) + '</span>'
        : '') +
      '</span>';
    btn.addEventListener('click', () => selectChannel(ch.id));
    return btn;
  }

  function renderChannelLists() {
    const chans = CW.channels.filter((c) => c.type === 'channel');
    const dms = CW.channels.filter((c) => c.type === 'direct');
    const chEl = document.getElementById('cw-channels');
    const dmEl = document.getElementById('cw-dms');
    if (!chEl || !dmEl) return;
    chEl.innerHTML = '';
    dmEl.innerHTML = '';
    chans.forEach((c) => chEl.appendChild(renderChannelItem(c)));
    dms.forEach((c) => dmEl.appendChild(renderChannelItem(c)));
    if (!chans.length) chEl.innerHTML = '<p style="padding:8px 12px;font-size:12px;color:var(--muted);margin:0">—</p>';
    if (!dms.length) dmEl.innerHTML = '<p style="padding:8px 12px;font-size:12px;color:var(--muted);margin:0">—</p>';
  }

  function syncAdminButtons() {
    const btn = document.getElementById('cw-add-channel');
    if (!btn) return;
    btn.classList.toggle('cw-hidden', !ADMIN_ROLES.has(CW.role));
  }

  function updateChannelHeader() {
    const ch = CW.channels.find((c) => c.id === CW.activeId);
    const title = document.getElementById('cw-panel-title');
    const avWrap = document.getElementById('cw-header-avatar');
    const infoBtn = document.getElementById('cw-channel-info');
    if (title) {
      title.textContent = ch
        ? ch.display_name || ch.name || (ch.type === 'direct' ? 'Message' : 'Canal')
        : 'Messagerie';
    }
    if (avWrap) {
      if (ch) {
        avWrap.innerHTML = cwChannelIconHtml(ch, 32);
        avWrap.classList.remove('cw-hidden');
      } else {
        avWrap.innerHTML = '';
        avWrap.classList.add('cw-hidden');
      }
    }
    if (infoBtn) {
      const show = !!(ch && ch.type === 'channel');
      infoBtn.classList.toggle('cw-hidden', !show);
    }
  }

  function closeOverlay() {
    const ov = document.getElementById('cw-overlay');
    if (ov) {
      ov.classList.add('cw-hidden');
      ov.innerHTML = '';
    }
  }

  async function loadChannels() {
    await syncChatState(false);

    if (!CW.activeId && CW.channels.length && !isCwMobile()) {
      let pick = CW.channels[0];
      let maxU = -1;
      CW.channels.forEach((c) => {
        const u = Number(c.unread_count) || 0;
        if (u > maxU) {
          maxU = u;
          pick = c;
        }
      });
      await selectChannel(pick.id);
    } else if (CW.activeId) {
      await selectChannel(CW.activeId);
    } else {
      syncMobileChatUi();
    }
  }

  async function selectChannel(id) {
    stopTypingPolls();
    CW.activeId = id;
    CW.lastMsgId = 0;
    CW.pendingFile = null;
    renderPendingAttachment();
    CW.memberReadStatus = {};
    renderChannelLists();
    closeOverlay();
    updateChannelHeader();

    const picker = document.getElementById('cw-dm-picker');
    if (picker) picker.classList.add('cw-hidden');

    const box = document.getElementById('cw-messages');
    if (!box) return;
    box.innerHTML = '<p style="text-align:center;color:var(--muted);font-size:13px;padding:12px">Chargement…</p>';

    try {
      const data = await api('/api/chat/channels/' + id + '/messages');
      const msgs = data.messages || [];
      box.innerHTML = '';
      let _lastDk = '';
      msgs.forEach((m) => {
        const dk = cwDateKey(m.created_at||'');
        if (dk && dk !== _lastDk) { _lastDk = dk; box.appendChild(cwBuildDateSep(m.created_at)); }
        box.appendChild(renderMsg(m));
        if (m.id > CW.lastMsgId) CW.lastMsgId = m.id;
      });
      if (!msgs.length) {
        box.innerHTML = '<div id="cw-empty-hint">Aucun message — soyez le premier.</div>';
      }
      scrollMessagesBottom();
      fetchReadStatus(id);

      if (CW.pollTimer) clearInterval(CW.pollTimer);
      CW.pollTimer = setInterval(pollMessages, 5000);
      startTypingPoll();
      await syncChatState(false);
    } catch (e) {
      console.error('[chat_widget] selectChannel id=' + id + ' a échoué :', e);
      box.innerHTML = '<div id="cw-empty-hint">Chargement impossible.</div>';
    }
    syncMobileChatUi();
  }

  async function pollMessages() {
    if (!CW.activeId || !CW.open) return;
    const box = document.getElementById('cw-messages');
    if (!box) return;
    const wasBottom = isNearBottom(box, 40);
    try {
      let path = '/api/chat/channels/' + CW.activeId + '/messages';
      if (CW.lastMsgId > 0) path += '?after=' + CW.lastMsgId;
      const data = await api(path);
      const incoming = data.messages || [];
      if (!incoming.length) return;
      const hint = box.querySelector('#cw-empty-hint');
      if (hint) hint.remove();
      let played = false;
      const _lastWrap = box.querySelector('.cw-msg-wrap:last-of-type');
      let _pollLastDk = _lastWrap ? cwDateKey(_lastWrap.dataset.at||'') : '';
      incoming.forEach((m) => {
        if (m.id <= CW.lastMsgId) return;
        if (Number(m.user_id) !== Number(CW.uid) && !played) {
          unlockAudio();
          jouerSon();
          played = true;
        }
        const dk = cwDateKey(m.created_at||'');
        if (dk && dk !== _pollLastDk) { _pollLastDk = dk; box.appendChild(cwBuildDateSep(m.created_at)); }
        box.appendChild(renderMsg(m));
        if (m.id > CW.lastMsgId) CW.lastMsgId = m.id;
      });
      if (wasBottom) scrollMessagesBottom();
      await syncChatState(false);
      fetchReadStatus(CW.activeId);
    } catch (e) {}
  }

  async function sendMessage() {
    if (!CW.activeId) return;
    const inp = document.getElementById('cw-input');
    const rawBody = (inp && inp.value) || '';
    const body = window.ChatMentions
      ? window.ChatMentions.trimChatBody(rawBody)
      : rawBody.replace(/^\s+|\s+$/g, '');
    const file = CW.pendingFile;
    if (!body && !file) return;
    const btn = document.getElementById('cw-send');
    if (btn) btn.disabled = true;
    try {
      let sent;
      if (file) {
        const fd = new FormData();
        if (body) fd.append('body', body);
        fd.append('file', file);
        sent = await api('/api/chat/channels/' + CW.activeId + '/messages', {
          method: 'POST',
          body: fd,
        });
      } else {
        sent = await api('/api/chat/channels/' + CW.activeId + '/messages', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ body, reply_to_id: CW._replyToId || undefined }),
        });
        cwCancelReply();
      }
      if (inp) {
        inp.value = '';
        resizeCwInput(inp);
      }
      CW.pendingFile = null;
      renderPendingAttachment();
      const box = document.getElementById('cw-messages');
      if (box && sent && sent.id) {
        const hint = box.querySelector('#cw-empty-hint');
        if (hint) hint.remove();
        const m = {
          id: sent.id,
          user_id: CW.uid,
          user_nom: CW.nom,
          body: sent.body != null ? sent.body : body,
          created_at: sent.created_at || new Date().toISOString().slice(0, 19).replace('T', ' '),
          attachment_url: sent.attachment_url || '',
          attachment_name: sent.attachment_name || '',
          attachment_mime: sent.attachment_mime || '',
          is_mine: true,
        };
        box.appendChild(renderMsg(m));
        if (sent.id > CW.lastMsgId) CW.lastMsgId = sent.id;
      } else {
        await pollMessages();
      }
      stopTypingPolls();
      scrollMessagesBottom();
      fetchReadStatus(CW.activeId);
      await syncChatState(false);
    } catch (e) {
      console.warn('[chat]', e.message);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  function applyGlobalBadges(total, data) {
    const barBadge = document.getElementById('cw-bar-badge');
    const bubBadge = document.getElementById('cw-bubble-badge');
    const preview = document.getElementById('cw-bar-preview');
    const label = total > 99 ? '99+' : String(total);

    if (barBadge) {
      if (total > 0) {
        barBadge.textContent = label;
        barBadge.style.display = 'inline-flex';
      } else barBadge.style.display = 'none';
    }
    if (bubBadge) {
      if (total > 0) {
        bubBadge.textContent = label;
        bubBadge.style.display = 'inline-flex';
        bubBadge.setAttribute('aria-label', label + ' non lu' + (total > 1 ? 's' : ''));
      } else {
        bubBadge.style.display = 'none';
        bubBadge.setAttribute('aria-label', '');
      }
    }

    if (preview) {
      const lm = data && data.last_message;
      if (lm && lm.body) {
        const who = lm.from_nom || lm.user_nom || 'Collègue';
        const prev = who + ' : ' + String(lm.body).slice(0, 48);
        preview.textContent = prev + (String(lm.body).length > 48 ? '…' : '');
      } else if (total > 0) {
        preview.textContent =
          total + ' message' + (total > 1 ? 's' : '') + ' non lu' + (total > 1 ? 's' : '');
      } else {
        preview.textContent = 'Aucun message non lu';
      }
    }

    if (window.MySifaChatBadge && typeof window.MySifaChatBadge.refresh === 'function') {
      window.MySifaChatBadge.refresh();
    }
  }

  async function syncChatState(playSoundOnNew) {
    if (!CW.uid) return;
    try {
      const [unreadData, channels] = await Promise.all([
        api('/api/chat/unread'),
        api('/api/chat/channels'),
      ]);
      const total = Number(unreadData.unread) || 0;
      CW.channels = channels || [];
      renderChannelLists();
      applyGlobalBadges(total, unreadData);

      if (playSoundOnNew && shouldPlayNotifSound(total)) {
        unlockAudio();
        await jouerSon();
      }
      CW.prevUnreadTotal = total;
      CW._chatSynced = true;
    } catch (e) {}
  }

  function startBgPoll() {
    if (CW.bgPollTimer) clearInterval(CW.bgPollTimer);
    CW.bgPollTimer = setInterval(() => syncChatState(true), 5000);
    syncChatState(false);
  }

  function stopBgPoll() {
    if (CW.bgPollTimer) clearInterval(CW.bgPollTimer);
    CW.bgPollTimer = null;
  }

  async function refreshBadge() {
    await syncChatState(false);
  }

  function canManageChannel(ch) {
    return (
      ADMIN_ROLES.has(CW.role) ||
      !!(ch && ch.created_by && Number(ch.created_by) === Number(CW.uid))
    );
  }

  function renderSettingsMemberRows(membersEl, members, ch, canManage) {
    if (!membersEl) return;
    membersEl.innerHTML = '';
    if (!members.length) {
      membersEl.innerHTML =
        '<p style="color:var(--muted);font-size:13px;margin:0">Aucun membre.</p>';
      return;
    }
    members.forEach((m) => {
      const rl = ROLE_LABELS[m.role] || m.role || '';
      cacheUserAvatar(m.id, m.nom, m.avatar_url);
      const isSelf = Number(m.id) === Number(CW.uid);
      const row = document.createElement('div');
      row.className = 'cw-member-row';
      row.innerHTML =
        cwAvatarHtml(m.nom, m.avatar_url, 32) +
        '<div class="cw-member-body"><div>' +
        escCW(m.nom || 'Utilisateur') +
        '</div><div class="cw-member-role">' +
        escCW(rl) +
        '</div></div>' +
        (!isSelf
          ? '<button type="button" class="cw-member-actions-btn" title="Actions" aria-label="Actions">⋮</button>' +
            '<div class="cw-member-dropdown cw-hidden">' +
            '<button type="button" class="cw-dropdown-item" data-action="dm">Envoyer un message</button>' +
            (canManage
              ? '<button type="button" class="cw-dropdown-item cw-danger" data-action="remove">Retirer du canal</button>'
              : '') +
            '</div>'
          : '');
      const actBtn = row.querySelector('.cw-member-actions-btn');
      const dropdown = row.querySelector('.cw-member-dropdown');
      if (actBtn && dropdown) {
        actBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          membersEl.querySelectorAll('.cw-member-dropdown').forEach((d) => {
            if (d !== dropdown) d.classList.add('cw-hidden');
          });
          dropdown.classList.toggle('cw-hidden');
        });
        document.addEventListener('click', function closeDD(e) {
          if (!dropdown.contains(e.target) && e.target !== actBtn) {
            dropdown.classList.add('cw-hidden');
            document.removeEventListener('click', closeDD);
          }
        });
        dropdown.querySelectorAll('.cw-dropdown-item').forEach((item) => {
          item.addEventListener('click', async (e) => {
            e.stopPropagation();
            dropdown.classList.add('cw-hidden');
            const action = item.dataset.action;
            if (action === 'dm') {
              closeOverlay();
              try {
                const r = await api('/api/chat/channels', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ type: 'direct', user_id: m.id }),
                });
                await loadChannels();
                await selectChannel(r.id);
              } catch (ex) {}
            }
            if (action === 'remove') {
              if (
                !window.confirm('Retirer ' + (m.nom || 'cet utilisateur') + ' du canal ?')
              ) {
                return;
              }
              try {
                await api('/api/chat/channels/' + CW.activeId + '/members/' + m.id, {
                  method: 'DELETE',
                });
                await refreshChannelSettingsMembers(ch, canManage);
                await syncChatState(false);
              } catch (ex) {
                window.alert(ex.message || 'Erreur lors de la suppression.');
              }
            }
          });
        });
      }
      membersEl.appendChild(row);
    });
  }

  async function refreshChannelSettingsMembers(ch, canManage) {
    const membersEl = document.getElementById('cw-settings-members');
    if (!membersEl) return;
    try {
      const members =
        (await api('/api/chat/channels/' + CW.activeId + '/members')) || [];
      renderSettingsMemberRows(membersEl, members, ch, canManage);
      const memberIds = new Set(members.map((m) => m.id));
      const pickEl = document.getElementById('cw-settings-user-pick');
      if (pickEl) {
        pickEl._memberIds = memberIds;
        if (pickEl._allUsers) {
          renderSettingsAddPick(pickEl._allUsers, memberIds, ch, canManage);
        }
      }
    } catch (e) {
      membersEl.innerHTML = '<p class="cw-overlay-err">Chargement impossible.</p>';
    }
  }

  function renderSettingsAddPick(users, memberIds, ch, canManage) {
    const pickEl = document.getElementById('cw-settings-user-pick');
    const searchEl = document.getElementById('cw-settings-add-search');
    if (!pickEl || !canManage) return;
    const ids = pickEl._memberIds || memberIds;
    const q = (searchEl && searchEl.value) || '';
    const ql = q.toLowerCase();
    const list = users.filter(
      (u) =>
        u.id !== CW.uid &&
        !ids.has(u.id) &&
        (!ql || (u.nom || '').toLowerCase().includes(ql))
    );
    if (!list.length) {
      pickEl.innerHTML =
        '<p style="padding:10px;margin:0;font-size:12px;color:var(--muted)">—</p>';
      return;
    }
    pickEl.innerHTML = list
      .map(
        (u) =>
          '<button type="button" class="cw-dm-row" data-uid="' +
          u.id +
          '">' +
          escCW(u.nom) +
          ' <span style="color:var(--muted);font-size:11px">' +
          escCW(ROLE_LABELS[u.role] || u.role || '') +
          '</span></button>'
      )
      .join('');
    pickEl.querySelectorAll('.cw-dm-row').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const uid = parseInt(btn.getAttribute('data-uid'), 10);
        try {
          await api('/api/chat/channels/' + CW.activeId + '/members', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: uid }),
          });
          if (searchEl) searchEl.value = '';
          await refreshChannelSettingsMembers(ch, canManage);
          await syncChatState(false);
        } catch (ex) {
          window.alert(ex.message || 'Ajout impossible.');
        }
      });
    });
  }

  async function openChannelSettings() {
    if (!CW.activeId) return;
    const ch = CW.channels.find((c) => c.id === CW.activeId);
    if (!ch || ch.type !== 'channel') return;
    const canManage = canManageChannel(ch);
    closeOverlay();
    const picker = document.getElementById('cw-dm-picker');
    if (picker) picker.classList.add('cw-hidden');
    const ov = document.getElementById('cw-overlay');
    if (!ov) return;
    ov.classList.remove('cw-hidden');
    const chTitle = escCW(ch.display_name || ch.name || 'Canal');
    ov.innerHTML =
      '<div class="cw-overlay-head"><button type="button" class="cw-overlay-back" id="cw-ov-back" aria-label="Retour">×</button>' +
      '<h3>Réglages — ' +
      chTitle +
      '</h3></div>' +
      '<div class="cw-overlay-body" id="cw-ov-body"><p style="color:var(--muted);font-size:13px;margin:0">Chargement…</p></div>' +
      (canManage
        ? '<div class="cw-overlay-actions">' +
          '<button type="button" class="cw-btn-ghost" id="cw-settings-cancel">Annuler</button>' +
          '<button type="button" class="cw-btn-primary" id="cw-settings-save">Enregistrer</button></div>'
        : '<div class="cw-overlay-actions">' +
          '<button type="button" class="cw-btn-primary" id="cw-settings-close">Fermer</button></div>');
    document.getElementById('cw-ov-back').addEventListener('click', closeOverlay);
    document.getElementById('cw-settings-cancel')?.addEventListener('click', closeOverlay);
    document.getElementById('cw-settings-close')?.addEventListener('click', closeOverlay);

    const body = document.getElementById('cw-ov-body');
    if (!body) return;

    let generalHtml = '';
    if (canManage) {
      generalHtml =
        '<div class="cw-settings-section">' +
        '<p class="cw-settings-section-title">Général</p>' +
        '<label for="cw-cs-emoji">Icône du canal</label>' +
        '<input type="text" id="cw-cs-emoji" maxlength="4" placeholder="ex. 🔧 📦" value="' +
        escAttr(ch.emoji || '') +
        '">' +
        '<p class="cw-settings-hint">Un seul emoji. Laissez vide pour aucun.</p>' +
        '<label for="cw-cs-name">Nom</label>' +
        '<input type="text" id="cw-cs-name" maxlength="60" value="' +
        escAttr(ch.name || '') +
        '">' +
        '<label for="cw-cs-desc">Description</label>' +
        '<textarea id="cw-cs-desc" rows="2">' +
        escCW(ch.description || '') +
        '</textarea></div>';
    } else {
      const pfx = ch.emoji ? ch.emoji + ' ' : '';
      generalHtml =
        '<div class="cw-settings-section">' +
        '<p class="cw-settings-section-title">Général</p>' +
        '<p style="margin:0 0 6px;font-size:14px;font-weight:600;color:var(--text)">' +
        escCW(pfx + (ch.name || ch.display_name || 'Canal')) +
        '</p>' +
        (ch.description
          ? '<p style="margin:0;font-size:13px;color:var(--text2)">' + escCW(ch.description) + '</p>'
          : '<p style="margin:0;font-size:12px;color:var(--muted)">Sans description</p>') +
        '</div>';
    }

    body.innerHTML =
      generalHtml +
      '<div class="cw-settings-section">' +
      '<p class="cw-settings-section-title">Membres</p>' +
      '<div id="cw-settings-members"><p style="color:var(--muted);font-size:13px;margin:0">Chargement…</p></div>' +
      (canManage
        ? '<label for="cw-settings-add-search" style="margin-top:12px">Ajouter un membre</label>' +
          '<input type="search" id="cw-settings-add-search" placeholder="Rechercher un collègue…" autocomplete="off">' +
          '<div class="cw-user-pick" id="cw-settings-user-pick"></div>'
        : '') +
      '</div>';

    document.getElementById('cw-settings-save')?.addEventListener('click', async () => {
      const emoji = (document.getElementById('cw-cs-emoji')?.value || '').trim();
      const name = (document.getElementById('cw-cs-name')?.value || '').trim();
      const description = (document.getElementById('cw-cs-desc')?.value || '').trim();
      if (!name) {
        window.alert('Nom requis.');
        return;
      }
      try {
        await api('/api/chat/channels/' + CW.activeId, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ emoji: emoji || null, name, description }),
        });
        await loadChannels();
        updateChannelHeader();
        renderChannelLists();
        closeOverlay();
      } catch (ex) {
        window.alert(ex.message || 'Enregistrement impossible.');
      }
    });

    try {
      const members =
        (await api('/api/chat/channels/' + CW.activeId + '/members')) || [];
      const memberIds = new Set(members.map((m) => m.id));
      renderSettingsMemberRows(
        document.getElementById('cw-settings-members'),
        members,
        ch,
        canManage
      );
      if (canManage) {
        let users = [];
        try {
          users = (await api('/api/chat/users')) || [];
        } catch (e) {
          users = [];
        }
        const pickEl = document.getElementById('cw-settings-user-pick');
        if (pickEl) {
          pickEl._allUsers = users;
          pickEl._memberIds = memberIds;
          renderSettingsAddPick(users, memberIds, ch, canManage);
          const searchEl = document.getElementById('cw-settings-add-search');
          if (searchEl) {
            searchEl.oninput = () =>
              renderSettingsAddPick(users, pickEl._memberIds, ch, canManage);
          }
        }
      }
    } catch (e) {
      body.innerHTML += '<p class="cw-overlay-err">Chargement des membres impossible.</p>';
    }
  }

  async function openNewChannel() {
    if (!ADMIN_ROLES.has(CW.role)) return;
    closeOverlay();
    const picker = document.getElementById('cw-dm-picker');
    if (picker) picker.classList.add('cw-hidden');
    let users = [];
    try {
      users = (await api('/api/chat/users')) || [];
    } catch (e) {
      return;
    }
    const ov = document.getElementById('cw-overlay');
    if (!ov) return;
    let picked = [];
    ov.classList.remove('cw-hidden');
    ov.innerHTML =
      '<div class="cw-overlay-head"><button type="button" class="cw-overlay-back" id="cw-ov-back" aria-label="Retour">×</button>' +
      '<h3>Nouveau canal</h3></div>' +
      '<div class="cw-overlay-body">' +
      '<label for="cw-ch-name">Nom</label><input type="text" id="cw-ch-name" maxlength="60" placeholder="ex. commercial">' +
      '<label for="cw-ch-desc">Description</label><textarea id="cw-ch-desc" rows="2" placeholder="Optionnel"></textarea>' +
      '<label for="cw-ch-member-search">Membres</label>' +
      '<div class="cw-member-chips" id="cw-ch-chips"></div>' +
      '<input type="search" id="cw-ch-member-search" placeholder="Ajouter un collègue…">' +
      '<div class="cw-user-pick" id="cw-ch-user-pick"></div>' +
      '<p class="cw-overlay-err cw-hidden" id="cw-ch-err"></p></div>' +
      '<div class="cw-overlay-actions">' +
      '<button type="button" class="cw-btn-ghost" id="cw-ch-cancel">Annuler</button>' +
      '<button type="button" class="cw-btn-primary" id="cw-ch-create">Créer</button></div>';
    document.getElementById('cw-ov-back').addEventListener('click', closeOverlay);
    document.getElementById('cw-ch-cancel').addEventListener('click', closeOverlay);

    function renderChips() {
      const el = document.getElementById('cw-ch-chips');
      if (!el) return;
      el.innerHTML = picked
        .map(
          (m) =>
            '<span class="cw-member-chip">' +
            cwAvatarHtml(m.nom, m.avatar_url, 18) +
            escCW(m.nom) +
            '<button type="button" data-id="' +
            m.id +
            '" title="Retirer">×</button></span>'
        )
        .join('');
      el.querySelectorAll('.cw-member-chip button').forEach((b) => {
        b.addEventListener('click', () => {
          const mid = parseInt(b.getAttribute('data-id'), 10);
          picked = picked.filter((x) => x.id !== mid);
          renderChips();
          renderPick(document.getElementById('cw-ch-member-search').value);
        });
      });
    }

    function renderPick(q) {
      const el = document.getElementById('cw-ch-user-pick');
      if (!el) return;
      const ql = (q || '').toLowerCase();
      const pickedIds = new Set(picked.map((m) => m.id));
      const list = users.filter(
        (u) => u.id !== CW.uid && !pickedIds.has(u.id) && (!ql || (u.nom || '').toLowerCase().includes(ql))
      );
      if (!list.length) {
        el.innerHTML = '<p style="padding:10px;margin:0;font-size:12px;color:var(--muted)">—</p>';
        return;
      }
      el.innerHTML = '';
      list.forEach((u) => {
        const row = document.createElement('button');
        row.type = 'button';
        row.className = 'cw-dm-row';
        row.innerHTML =
          cwAvatarHtml(u.nom, u.avatar_url, 28) +
          '<span>' +
          escCW(u.nom || 'Utilisateur') +
          '</span>';
        row.addEventListener('click', () => {
          picked.push({
            id: u.id,
            nom: u.nom || 'Utilisateur',
            avatar_url: u.avatar_url || '',
          });
          renderChips();
          renderPick(document.getElementById('cw-ch-member-search').value);
        });
        el.appendChild(row);
      });
    }

    renderChips();
    renderPick('');
    const search = document.getElementById('cw-ch-member-search');
    if (search) search.oninput = () => renderPick(search.value);

    document.getElementById('cw-ch-create').addEventListener('click', async () => {
      const errEl = document.getElementById('cw-ch-err');
      const name = (document.getElementById('cw-ch-name').value || '').trim();
      if (!name) {
        if (errEl) {
          errEl.textContent = 'Nom requis.';
          errEl.classList.remove('cw-hidden');
        }
        return;
      }
      const description = (document.getElementById('cw-ch-desc').value || '').trim();
      const btn = document.getElementById('cw-ch-create');
      if (btn) btn.disabled = true;
      try {
        const r = await api('/api/chat/channels', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            type: 'channel',
            name,
            description,
            member_ids: picked.map((m) => m.id),
          }),
        });
        closeOverlay();
        await loadChannels();
        await selectChannel(r.id);
      } catch (e) {
        if (errEl) {
          errEl.textContent = e.message || 'Création impossible.';
          errEl.classList.remove('cw-hidden');
        }
      } finally {
        if (btn) btn.disabled = false;
      }
    });
    requestAnimationFrame(() => document.getElementById('cw-ch-name')?.focus());
  }

  async function openNewDm() {
    closeOverlay();
    const picker = document.getElementById('cw-dm-picker');
    const list = document.getElementById('cw-dm-list');
    const search = document.getElementById('cw-dm-search');
    if (!picker || !list) return;
    picker.classList.remove('cw-hidden');
    let users = [];
    try {
      users = (await api('/api/chat/users')) || [];
    } catch (e) {
      list.innerHTML = '<p style="padding:12px;color:var(--muted);font-size:12px">Erreur chargement</p>';
      return;
    }
    function renderList(q) {
      const ql = (q || '').toLowerCase();
      const filtered = users.filter((u) => !ql || (u.nom || '').toLowerCase().includes(ql));
      if (!filtered.length) {
        list.innerHTML = '<p style="padding:12px;color:var(--muted);font-size:12px">Aucun résultat</p>';
        return;
      }
      list.innerHTML = '';
      filtered.forEach((u) => {
        const row = document.createElement('button');
        row.type = 'button';
        row.className = 'cw-dm-row';
        row.innerHTML =
          cwAvatarHtml(u.nom, u.avatar_url, 32) +
          '<span>' +
          escCW(u.nom || 'Utilisateur') +
          '</span>';
        row.addEventListener('click', async () => {
          picker.classList.add('cw-hidden');
          try {
            const r = await api('/api/chat/channels', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ type: 'direct', user_id: u.id }),
            });
            await loadChannels();
            await selectChannel(r.id);
          } catch (e) {}
        });
        list.appendChild(row);
      });
    }
    renderList('');
    if (search) {
      search.value = '';
      search.oninput = () => renderList(search.value);
      requestAnimationFrame(() => search.focus());
    }
  }

  let _panelToggleGen = 0;

  function closePanel() {
    _panelToggleGen += 1;
    CW.open = false;
    const panel = document.getElementById('cw-panel');
    if (panel) panel.classList.add('cw-hidden');
    setChatTriggerActive(false);
    document.body.classList.remove('cw-panel-open', 'cw-chat-active');
    if (CW.pollTimer) {
      clearInterval(CW.pollTimer);
      CW.pollTimer = null;
    }
    stopTypingPolls();
    const picker = document.getElementById('cw-dm-picker');
    if (picker) picker.classList.add('cw-hidden');
    closeOverlay();
    hideReactionTip();
    syncMobileChatUi();
    dockLayout();
  }

  async function openPanel() {
    const panel = document.getElementById('cw-panel');
    if (!panel) return;
    const gen = (_panelToggleGen += 1);
    CW.open = true;
    setChatTriggerActive(true);
    panel.classList.remove('cw-hidden');
    syncChatTriggerMode();
    syncMobileChatUi();
    dockLayout();
    try {
      await _getAudioCtx();
    } catch (e) {}
    if (!CW.open || gen !== _panelToggleGen) return;
    if (!CW.channels.length) await loadChannels();
    else if (CW.activeId) await selectChannel(CW.activeId);
    else if (!isCwMobile()) await loadChannels();
    else syncMobileChatUi();
    if (!CW.open || gen !== _panelToggleGen) return;
    syncChatState(false);
    if (!isCwMobile()) {
      requestAnimationFrame(() => {
        if (!CW.open || gen !== _panelToggleGen) return;
        if (useChatBubbleTrigger()) dockLayout();
        else positionDesktopPanel();
        requestAnimationFrame(() => {
          if (!CW.open || gen !== _panelToggleGen) return;
          if (useChatBubbleTrigger()) dockLayout();
          else positionDesktopPanel();
        });
      });
    }
    dockLayout();
  }

  async function togglePanel(force) {
    const next = typeof force === 'boolean' ? force : !CW.open;
    if (!next) {
      closePanel();
      return;
    }
    if (CW.open) return;
    await openPanel();
  }

  function _getAudioCtx() {
    if (!CW._audioCtx) CW._audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    if (CW._audioCtx.state === 'suspended') return CW._audioCtx.resume();
    return Promise.resolve();
  }

  CW.syncUser = function () {
    const wasPortal = CW.isPortal;
    syncFromWindow();
    if (!CW.uid) return;
    if (!CW._inited) {
      CW.init();
      return;
    }
    if (wasPortal !== CW.isPortal) {
      CW.destroy();
      CW.init();
      return;
    }
    syncAdminButtons();
    refreshBadge();
    syncMobileChatUi();
    dockLayout();
  };

  function hasCorrectChatTrigger() {
    return !!document.getElementById('cw-bubble') && !!document.getElementById('cw-bar');
  }

  CW.init = async function () {
    if (CW._inited && hasCorrectChatTrigger() && document.getElementById('cw-panel')) {
      return true;
    }
    if (CW._initPromise) return CW._initPromise;
    CW._initPromise = (async () => {
      try {
        if (!window.__MYSIFA_APP__) window.__MYSIFA_APP__ = 'unknown';
        syncFromWindow();
        if (!CW.uid) {
          const ok = await fetchMe();
          if (!ok) return false;
        }
        if (document.getElementById('cw-panel') || document.querySelectorAll('#cw-bubble').length) {
          removeChatDom();
        }
        CW._inited = true;

        injectStyles();
        buildDom();
        syncAdminButtons();
        syncMobileChatUi();
        dockLayout();
        document.addEventListener('click', unlockAudio, { once: false, capture: true });
        startBgPoll();
        checkChatUpdates();
        return true;
      } catch (e) {
        CW._inited = false;
        return false;
      } finally {
        CW._initPromise = null;
      }
    })();
    return CW._initPromise;
  };

  async function checkChatUpdates() {
    try {
      const updates = await fetch('/api/updates/pending?scope=messages', { credentials: 'include' }).then(
        (r) => (r.ok ? r.json() : [])
      );
      if (!updates || !updates.length) return;
      const overlay = document.createElement('div');
      overlay.className = 'upd-overlay';
      const ids = updates.map((u) => u.id);
      const bodies = updates
        .map((u) => '<div class="upd-body">' + u.message + '</div>')
        .join('<hr style="border:none;border-top:1px solid var(--border);margin:16px 0">');
      overlay.innerHTML =
        '<div class="upd-card">' +
        bodies +
        '<button type="button" class="upd-ok-btn" onclick="Promise.all([' +
        ids.join(',') +
        '].map(function(id){return fetch(\'/api/updates/\'+id+\'/acknowledge\',{method:\'POST\',credentials:\'include\'});})).catch(function(){});this.closest(\'.upd-overlay\').remove()">Compris</button></div>';
      document.body.appendChild(overlay);
    } catch (e) {}
  }

  CW.ensureReady = async function () {
    syncFromWindow();
    if (!CW.uid) await fetchMe();
    if (!CW.uid) return false;
    return CW.init();
  };

  CW.destroy = function () {
    if (CW.pollTimer) clearInterval(CW.pollTimer);
    stopTypingPolls();
    stopBgPoll();
    CW._chatSynced = false;
    CW.prevUnreadTotal = 0;
    ['cw-bar', 'cw-bubble', 'cw-panel', 'cw-styles'].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.remove();
    });
    CW._inited = false;
    CW._initPromise = null;
    CW.open = false;
    document.body.classList.remove('cw-mobile', 'cw-panel-open', 'cw-chat-active');
    dockLayout();
  };

  function boot() {
    const run = () => {
      void CW.ensureReady();
    };
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', run, { once: true });
    } else {
      run();
    }
  }

  window.addEventListener('resize', () => {
    syncMobileChatUi();
    dockLayout();
    if (CW.open && !isCwMobile() && !useChatBubbleTrigger()) positionDesktopPanel();
  });

  if (typeof window.matchMedia === 'function') {
    [CW_MOBILE_BP, CW_MOBILE_LANDSCAPE_BP, '(orientation: landscape)', '(orientation: portrait)'].forEach((q) => {
      const mq = window.matchMedia(q);
      const onMq = () => {
        syncMobileChatUi();
        dockLayout();
      };
      if (mq.addEventListener) mq.addEventListener('change', onMq);
      else if (mq.addListener) mq.addListener(onMq);
    });
  }
  window.addEventListener('orientationchange', () => {
    setTimeout(() => {
      syncMobileChatUi();
      dockLayout();
    }, 80);
  });

  CW.renderMsg = renderMsg;
  CW.selectChannel = selectChannel;
  CW.sendMessage = sendMessage;
  CW.api = api;
  CW.escCW = escCW;
  CW.fmtTime = fmtTime;
  CW.checkChatUpdates = checkChatUpdates;

  boot();
  window._CW = CW;
})();

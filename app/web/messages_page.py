"""MySifa — Page Chat interne (/messages)."""

import json

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
    nom = json.dumps((user.get("nom") or "").strip() or user.get("email", ""))
    role = json.dumps(user.get("role", ""))
    avatar = json.dumps(user.get("avatar_url") or "")
    html = (
        MESSAGES_HTML.replace("__V_LABEL__", f"v{APP_VERSION}")
        .replace("__USER_ID__", str(user.get("id", 0)))
        .replace("__USER_NOM_JSON__", nom)
        .replace("__USER_ROLE_JSON__", role)
        .replace("__USER_AVATAR_JSON__", avatar)
    )
    return HTMLResponse(content=html)


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
.chat-msg.pinned .chat-msg-bubble{border-top:2px solid var(--warn)}
.chat-msg-del{
  position:absolute;top:-4px;right:-4px;width:20px;height:20px;border-radius:50%;
  border:1px solid var(--border);background:var(--card);color:var(--muted);
  font-size:12px;line-height:1;cursor:pointer;display:none;align-items:center;justify-content:center;
  font-family:inherit;padding:0;
}
.chat-msg:hover .chat-msg-del{display:flex}
.chat-msg.mine .chat-msg-del{right:auto;left:-4px}
.chat-msg-edit{
  position:absolute;top:-4px;right:20px;width:20px;height:20px;border-radius:50%;
  border:1px solid var(--border);background:var(--card);color:var(--muted);
  font-size:11px;line-height:1;cursor:pointer;display:none;align-items:center;justify-content:center;
  font-family:inherit;padding:0;
}
.chat-msg:hover .chat-msg-edit{display:flex}
.chat-msg.mine .chat-msg-edit{right:auto;left:20px}
.chat-msg-pin{
  position:absolute;top:-4px;right:38px;width:20px;height:20px;border-radius:50%;
  border:1px solid var(--border);background:var(--card);color:var(--muted);
  font-size:9px;line-height:1;cursor:pointer;display:none;align-items:center;justify-content:center;
  font-family:inherit;padding:0;
}
.chat-msg:hover .chat-msg-pin{display:flex}
.chat-msg.mine .chat-msg-pin{right:auto;left:38px}
.chat-msg-pin.pinned-active{color:var(--warn);border-color:var(--warn)}
.chat-pinned-item{padding:10px 0;border-bottom:1px solid var(--border)}
.chat-pinned-item:last-child{border-bottom:none}
.chat-pinned-item-meta{font-size:10px;color:var(--muted);margin-bottom:4px}
.chat-pinned-item-body{font-size:13px;color:var(--text);line-height:1.5;word-break:break-word}
.chat-pinned-unpin{margin-top:6px;font-size:11px;font-weight:700;padding:4px 10px;border-radius:7px;
  border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-family:inherit}
.chat-pinned-unpin:hover{border-color:var(--warn);color:var(--warn)}
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
#chat-input-area{
  padding:10px 14px;border-top:1px solid var(--border);
  display:flex;gap:8px;align-items:flex-end;flex-shrink:0;background:var(--card);
}
#chat-input{
  width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;
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
/* Bouton + et actions étendues */
#chat-action-expand{
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
  display:grid;grid-template-columns:repeat(3,1fr);gap:8px;
  max-height:360px;overflow-y:auto;margin-top:10px;
  scrollbar-width:thin;scrollbar-color:var(--border) transparent;
}
.chat-gif-item{
  border-radius:6px;overflow:hidden;cursor:pointer;
  aspect-ratio:1;background:var(--bg);border:1px solid var(--border);
  display:flex;align-items:center;justify-content:center;padding:4px;
  min-height:0;
}
.chat-gif-item img{max-width:100%;max-height:100%;width:auto;height:auto;object-fit:contain;display:block}
.chat-gif-item:hover{border-color:var(--accent);background:var(--accent-bg)}
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
<script src="/static/mysifa_favicon_badge.js"></script>
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
          <div style="display:flex;gap:6px;align-items:center;flex-shrink:0">
          <button type="button" id="sound-toggle-btn" onclick="toggleSound()" class="hbtn"
            title="Couper le son" aria-label="Activer ou couper la sonnerie">
            <span id="sound-toggle-icon" aria-hidden="true"></span>
          </button>
          <button type="button" id="chan-pinned-btn" class="hbtn" title="Messages épinglés"
            onclick="openPinnedMessages()" style="display:none" aria-label="Messages épinglés">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="12" y1="17" x2="12" y2="22"/><path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6h1a2 2 0 0 0 0-4H8a2 2 0 0 0 0 4h1v4.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24Z"/></svg>
          </button>
          <button type="button" id="chan-settings-btn" class="hbtn" title="Réglages du canal"
            onclick="openChannelSettings()" style="display:none" aria-label="Réglages du canal">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93l-1.41 1.41M4.93 4.93l1.41 1.41M21 12h-2M5 12H3M19.07 19.07l-1.41-1.41M4.93 19.07l1.41-1.41M12 21v-2M12 5V3"/></svg>
          </button>
          </div>
        </div>
      </div>
      <div id="chat-empty">Sélectionnez un canal ou démarrez une conversation.</div>
      <div id="chat-messages" style="display:none"></div>
      <div id="chat-pending-row"></div>
      <div id="chat-input-area" style="display:none">
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
      </div>
    </div>
  </div>
</div>
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
<div id="mroot"></div>
<script src="/static/support_widget.js"></script>
<script src="/static/mysifa_chat_badge.js"></script>
<script src="/static/chat_widget.js"></script>
<script src="/static/chat_widget_v2.js"></script>
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
let channelMembers = [];
let mentionQuery = null;
let mentionStart = 0;
let mentionFocusIdx = -1;

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

const NOTIF_PERM_KEY='mysifa_notif_asked_v1';

async function checkUpdates(){
  try{
    const updates=await fetch('/api/updates/pending?scope=messages',{credentials:'include'}).then(r=>r.ok?r.json():[]);
    if(!updates||!updates.length)return;
    showUpdatePopup(updates);
  }catch(e){}
}

function showUpdatePopup(updates){
  const overlay=document.createElement('div');
  overlay.className='upd-overlay';
  overlay.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:9000;display:flex;align-items:center;justify-content:center;padding:16px';
  const ids=updates.map(u=>u.id);
  const bodies=updates.map(u=>'<div class="upd-body">'+u.message+'</div>').join('<hr style="border:none;border-top:1px solid var(--border);margin:16px 0">');
  overlay.innerHTML='<div class="upd-card" style="background:var(--card);border:1px solid var(--border);border-radius:18px;padding:28px;max-width:540px;max-height:88vh;overflow-y:auto">'
    +bodies
    +'<button type="button" class="upd-ok-btn" style="margin-top:16px;width:100%;padding:12px;border-radius:10px;background:var(--accent);color:var(--bg);border:none;font-weight:700;cursor:pointer;font-family:inherit" onclick="'
    +'Promise.all(['+ids.join(',')+'].map(id=>fetch(\'/api/updates/\'+id+\'/acknowledge\',{method:\'POST\',credentials:\'include\'}))).catch(()=>{});this.closest(\'.upd-overlay\').remove()">Compris</button></div>';
  document.body.appendChild(overlay);
}

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
  try{_getAudioCtx();}catch(e){}
  if(enable){
    try{
      const perm=await Notification.requestPermission();
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
    const mCount=Number(c.mention_count)||0;
    const mBadge=mCount>0?'<span class="chat-mention-badge">@</span>':'';
    const chanEmoji=(c.emoji&&c.type==='channel')?'<span style="margin-right:5px">'+esc(c.emoji)+'</span>':'';
    const prev=c.last_message_body?(esc(c.last_message_from||'')+': '+esc(c.last_message_body)):'';
    const active=c.id===activeId?' active':'';
    return '<button type="button" class="chat-chan-item'+active+'" data-id="'+c.id+'" onclick="selectChannel('+c.id+')">'+
      '<div class="chat-chan-body"><div class="chat-chan-name">'+chanEmoji+esc(c.display_name||(c.name||'Canal'))+'</div>'+
      (prev?'<div class="chat-chan-preview">'+prev+'</div>':'')+
      '</div>'+badge+mBadge+'</button>';
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
    const emojiPfx=ch.emoji?ch.emoji+' ':'';
    document.getElementById('chat-header-title').textContent=emojiPfx+(ch.display_name||ch.name||'Canal');
    const sub=ch.type==='direct'?'Message direct':(ch.description||'Canal d\'équipe');
    document.getElementById('chat-header-sub').textContent=sub;
    const pb=document.getElementById('chan-pinned-btn');
    if(pb)pb.style.display=ch.type==='channel'?'':'none';
    const sb=document.getElementById('chan-settings-btn');
    const canManage=ADMIN_ROLES.has(window.__MYSIFA_ROLE__)||(ch.created_by&&Number(ch.created_by)===Number(window.__MYSIFA_UID__));
    if(sb)sb.style.display=(ch.type==='channel')?'':'none';
    if(sb)sb.title=canManage?'Réglages du canal':'Membres du canal';
  }
  messages=[];
  hasMore=false;
  lastMsgId=0;
  await loadMessages(true);
  try{
    channelMembers=await api('/api/chat/channels/'+id+'/members')||[];
  }catch(e){channelMembers=[];}
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
  wrap.className='chat-msg '+(m.is_mine?'mine':'theirs')+(m.pinned_at?' pinned':'');
  wrap.dataset.id=String(m.id);
  const ch=channels.find(c=>c.id===activeId);
  const canDel=m.is_mine||ADMIN_ROLES.has(window.__MYSIFA_ROLE__);
  const canPin=ch&&ch.type==='channel'&&ADMIN_ROLES.has(window.__MYSIFA_ROLE__);
  const msgAge=Date.now()-new Date((m.created_at||'').replace(' ','T')).getTime();
  const canEdit=m.is_mine&&!m.attachment_url&&msgAge<900000;
  const body=(m.body||'').trim();
  let bubble=body?esc(body):'';
  if(bubble)bubble=bubble.replace(/@(\w+)/g,'<span style="color:var(--accent);font-weight:700">@$1</span>');
  if(m.attachment_url)bubble+=(bubble?'<br>':'')+chatAttachmentHtml(m);
  if(!bubble)bubble='<span style="color:var(--muted);font-size:12px">Pièce jointe</span>';
  wrap.innerHTML=
    '<div class="chat-msg-label">'+esc(m.user_nom)+' · '+esc(fmtTime(m.created_at))+(m.edited_at?'<span class="chat-msg-edited">(modifié)</span>':'')+'</div>'+
    '<div class="chat-msg-bubble">'+bubble+'</div>'+
    (canDel?'<button type="button" class="chat-msg-del" title="Supprimer" onclick="deleteMsg('+m.id+')">×</button>':'')+
    (canEdit?'<button type="button" class="chat-msg-edit" title="Modifier" onclick="startEdit('+m.id+')">✎</button>':'')+
    (canPin?'<button type="button" class="chat-msg-pin'+(m.pinned_at?' pinned-active':'')+'" title="'+(m.pinned_at?'Désépingler':'Épingler')+'" onclick="togglePin('+m.id+','+(m.pinned_at?'true':'false')+')" aria-label="'+(m.pinned_at?'Désépingler':'Épingler')+'"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><line x1="12" y1="17" x2="12" y2="22"/><path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6h1a2 2 0 0 0 0-4H8a2 2 0 0 0 0 4h1v4.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24Z"/></svg></button>':'');
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
    const bubbleEl=wrap.querySelector('.chat-msg-bubble');
    if(bubbleEl)bubbleEl.after(rDiv);
  }
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
  return wrap;
}

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
    const fresh2=fresh.filter(m=>!m.is_mine);
    if(fresh2.length){
      const ch=channels.find(c=>c.id===activeId);
      const chanName=ch?(ch.display_name||ch.name||'Canal'):'Message';
      const latest=fresh2[fresh2.length-1];
      sendBrowserNotif(latest.user_nom+' · '+chanName,latest.body,activeId);
    }
    if(fresh.length)appendNewMessages(fresh);
    fresh.filter(m=>!m.is_mine).forEach(m=>{
      const myNom=(window.__MYSIFA_NOM__||'').toLowerCase().replace(/\s/g,'');
      const body=(m.body||'').toLowerCase();
      const mentioned=body.includes('@'+myNom)||body.includes('@tous')||body.includes('@all');
      if(mentioned)showMentionToast(m.user_nom,m.body,activeId);
    });
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
    closeChatActions();
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

async function togglePin(msgId,isPinned){
  if(!activeId)return;
  try{
    if(isPinned){
      await api('/api/chat/channels/'+activeId+'/messages/'+msgId+'/pin',{method:'DELETE'});
      showToast('Message désépinglé','success');
    }else{
      await api('/api/chat/channels/'+activeId+'/messages/'+msgId+'/pin',{method:'POST'});
      showToast('Message épinglé','success');
    }
    await loadMessages(false);
  }catch(e){
    showToast(e.message||'Action impossible','danger');
  }
}

async function openPinnedMessages(){
  if(!activeId)return;
  const ch=channels.find(c=>c.id===activeId);
  if(!ch||ch.type==='direct')return;
  let pinned=[];
  try{
    pinned=await api('/api/chat/channels/'+activeId+'/pinned')||[];
  }catch(e){
    showToast(e.message||'Chargement impossible','danger');
    return;
  }
  const overlay=document.createElement('div');
  overlay.className='chat-modal-overlay';
  overlay.onclick=e=>{if(e.target===overlay)closeModal();};
  const isAdmin=ADMIN_ROLES.has(window.__MYSIFA_ROLE__);
  let listHtml='';
  if(!pinned.length){
    listHtml='<p style="color:var(--muted);font-size:13px;margin:0">Aucun message épinglé.</p>';
  }else{
    listHtml=pinned.map(m=>{
      const body=esc((m.body||'').trim()||'(pièce jointe)');
      const unpinBtn=isAdmin
        ?'<button type="button" class="chat-pinned-unpin" onclick="unpinFromModal('+m.id+')">Désépingler</button>'
        :'';
      return '<div class="chat-pinned-item">'+
        '<div class="chat-pinned-item-meta">'+esc(m.user_nom)+' · '+esc(fmtTime(m.created_at))+'</div>'+
        '<div class="chat-pinned-item-body">'+body+'</div>'+
        unpinBtn+'</div>';
    }).join('');
  }
  overlay.innerHTML=
    '<div class="chat-modal" role="dialog" style="width:min(480px,100%)">'+
    '<h3>Messages épinglés</h3>'+
    '<div id="pinned-list">'+listHtml+'</div>'+
    '<div class="chat-modal-actions" style="margin-top:14px">'+
    '<button type="button" class="primary" onclick="closeModal()">Fermer</button>'+
    '</div></div>';
  document.getElementById('mroot').appendChild(overlay);
}

async function unpinFromModal(msgId){
  if(!activeId)return;
  try{
    await api('/api/chat/channels/'+activeId+'/messages/'+msgId+'/pin',{method:'DELETE'});
    showToast('Message désépinglé','success');
    closeModal();
    await loadMessages(false);
  }catch(e){
    showToast(e.message||'Désépinglage impossible','danger');
  }
}

function canManageChannel(ch){
  return ADMIN_ROLES.has(window.__MYSIFA_ROLE__)||(ch.created_by&&Number(ch.created_by)===Number(window.__MYSIFA_UID__));
}

function renderSettingsMembersList(members,canManage){
  const el=document.getElementById('cs-members-list');
  if(!el)return;
  if(!members.length){
    el.innerHTML='<p style="padding:8px 0;margin:0;font-size:12px;color:var(--muted)">Aucun membre.</p>';
    return;
  }
  el.innerHTML=members.map(m=>{
    const rl=ROLE_LABELS[m.role]||m.role||'';
    const isSelf=Number(m.id)===Number(window.__MYSIFA_UID__);
    const removeBtn=(!isSelf&&canManage)
      ?'<button type="button" class="chat-user-row" style="justify-content:center;color:var(--danger);margin-top:4px" data-remove="'+m.id+'">Retirer</button>'
      :'';
    return '<div style="padding:8px 0;border-bottom:1px solid var(--border)">'+
      '<div style="font-weight:600;font-size:13px">'+esc(m.nom)+'</div>'+
      '<div style="font-size:11px;color:var(--muted)">'+esc(rl)+'</div>'+removeBtn+'</div>';
  }).join('');
  el.querySelectorAll('[data-remove]').forEach(btn=>{
    btn.onclick=async()=>{
      const uid=parseInt(btn.dataset.remove,10);
      const m=members.find(x=>x.id===uid);
      if(!confirm('Retirer '+(m?.nom||'ce membre')+' du canal ?'))return;
      try{
        await api('/api/chat/channels/'+activeId+'/members/'+uid,{method:'DELETE'});
        await refreshSettingsMembers(canManage);
        await loadChannels();
        showToast('Membre retiré','success');
      }catch(e){showToast(e.message||'Retrait impossible','danger');}
    };
  });
}

async function refreshSettingsMembers(canManage){
  const members=await api('/api/chat/channels/'+activeId+'/members')||[];
  channelMembers=members;
  renderSettingsMembersList(members,canManage);
  const pick=document.getElementById('cs-user-pick');
  if(pick&&pick._allUsers){
    const ids=new Set(members.map(m=>m.id));
    pick._memberIds=ids;
    renderSettingsAddPick(pick._allUsers,ids,canManage);
  }
}

function renderSettingsAddPick(users,memberIds,canManage){
  const pick=document.getElementById('cs-user-pick');
  const search=document.getElementById('cs-add-search');
  if(!pick||!canManage)return;
  const ids=pick._memberIds||memberIds;
  const ql=(search?.value||'').toLowerCase();
  const list=users.filter(u=>!ids.has(u.id)&&(!ql||(u.nom||'').toLowerCase().includes(ql)));
  if(!list.length){pick.innerHTML='<p style="padding:10px;margin:0;font-size:12px;color:var(--muted)">—</p>';return;}
  pick.innerHTML=list.map(u=>'<button type="button" class="chat-user-row" data-uid="'+u.id+'">'+esc(u.nom)+
    ' <span style="color:var(--muted);font-size:11px">'+esc(ROLE_LABELS[u.role]||u.role||'')+'</span></button>').join('');
  pick.querySelectorAll('.chat-user-row').forEach(btn=>{
    btn.onclick=async()=>{
      const uid=parseInt(btn.dataset.uid,10);
      try{
        await api('/api/chat/channels/'+activeId+'/members',{
          method:'POST',headers:{'Content-Type':'application/json'},
          body:JSON.stringify({user_id:uid})
        });
        if(search)search.value='';
        await refreshSettingsMembers(canManage);
        await loadChannels();
        showToast('Membre ajouté','success');
      }catch(e){showToast(e.message||'Ajout impossible','danger');}
    };
  });
}

async function openChannelSettings(){
  const ch=channels.find(c=>c.id===activeId);
  if(!ch||ch.type==='direct')return;
  const canManage=canManageChannel(ch);
  const overlay=document.createElement('div');
  overlay.className='chat-modal-overlay';
  overlay.onclick=e=>{if(e.target===overlay)closeModal();};
  const generalBlock=canManage
    ?('<label for="cs-emoji">Icône du canal</label>'+
      '<input type="text" id="cs-emoji" maxlength="4" placeholder="ex. 🔧 📦 🔑" value="'+esc(ch.emoji||'')+'">'+
      '<p style="font-size:11px;color:var(--muted);margin:-8px 0 14px">Un seul emoji. Laissez vide pour aucun.</p>'+
      '<label for="cs-name">Nom</label>'+
      '<input type="text" id="cs-name" maxlength="60" value="'+esc(ch.name||'')+'">'+
      '<label for="cs-desc">Description</label>'+
      '<textarea id="cs-desc" rows="2">'+esc(ch.description||'')+'</textarea>')
    :('<p style="margin:0 0 8px;font-size:14px;font-weight:600;color:var(--text)">'+
      esc((ch.emoji?ch.emoji+' ':'')+(ch.name||ch.display_name||'Canal'))+'</p>'+
      (ch.description?'<p style="margin:0;font-size:13px;color:var(--text2)">'+esc(ch.description)+'</p>':
        '<p style="margin:0;font-size:12px;color:var(--muted)">Sans description</p>'));
  const addBlock=canManage
    ?('<label for="cs-add-search" style="margin-top:12px">Ajouter un membre</label>'+
      '<input type="search" id="cs-add-search" placeholder="Rechercher un collègue…" autocomplete="off">'+
      '<div class="chat-user-list" id="cs-user-pick" style="max-height:140px"></div>')
    :'';
  overlay.innerHTML=
    '<div class="chat-modal" role="dialog" style="max-height:88vh;overflow-y:auto">'+
    '<h3>Réglages — '+esc(ch.display_name||ch.name||'Canal')+'</h3>'+
    generalBlock+
    '<div style="margin-top:16px;padding-top:14px;border-top:1px solid var(--border)">'+
    '<div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);margin-bottom:10px">Membres</div>'+
    '<div id="cs-members-list"><p style="color:var(--muted);font-size:12px">Chargement…</p></div>'+
    addBlock+'</div>'+
    '<div class="chat-modal-actions">'+
    (canManage?'<button type="button" onclick="closeModal()">Annuler</button><button type="button" class="primary" id="cs-save-btn">Enregistrer</button>':
      '<button type="button" class="primary" onclick="closeModal()">Fermer</button>')+
    '</div></div>';
  document.getElementById('mroot').appendChild(overlay);
  if(canManage){
    document.getElementById('cs-save-btn').onclick=async()=>{
      const emoji=(document.getElementById('cs-emoji').value||'').trim();
      const name=(document.getElementById('cs-name').value||'').trim();
      const description=(document.getElementById('cs-desc').value||'').trim();
      if(!name){showToast('Nom requis','danger');return;}
      try{
        await api('/api/chat/channels/'+activeId,{
          method:'PATCH',
          headers:{'Content-Type':'application/json'},
          body:JSON.stringify({emoji:emoji||null,name,description})
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
    try{
      allUsers=await api('/api/chat/users')||[];
    }catch(e){allUsers=[];}
    const pick=document.getElementById('cs-user-pick');
    if(pick){
      pick._allUsers=allUsers;
      const search=document.getElementById('cs-add-search');
      if(search)search.oninput=()=>renderSettingsAddPick(allUsers,pick._memberIds||new Set(),canManage);
    }
  }
  try{
    await refreshSettingsMembers(canManage);
  }catch(e){
    const el=document.getElementById('cs-members-list');
    if(el)el.innerHTML='<p style="color:var(--danger);font-size:12px">Chargement impossible.</p>';
  }
  if(canManage)requestAnimationFrame(()=>document.getElementById('cs-emoji')?.focus());
}

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

document.getElementById('chat-input').addEventListener('focus',()=>{
  if(document.getElementById('chat-action-btns').classList.contains('show'))closeChatActions();
});
function renderMentionDropdown(){
  const dd=document.getElementById('mention-dropdown');
  if(!dd)return;
  const q=mentionQuery||'';
  const myUid=window.__MYSIFA_UID__;
  const candidates=[
    {id:'all',nom:'tous',role:'Mentionner tout le canal'},
    ...channelMembers.filter(m=>(m.id||m.user_id)!==myUid)
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
document.addEventListener('click',e=>{
  if(!e.target.closest('#chat-input-wrap')&&!e.target.closest('#mention-dropdown'))closeMentionDropdown();
});

document.getElementById('chat-input').addEventListener('keydown',e=>{
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
  if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMessage();}
});
document.getElementById('chat-input').addEventListener('input',function(){
  this.style.height='auto';
  this.style.height=Math.min(this.scrollHeight,80)+'px';
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
  checkNotifPermission();
  checkUpdates();
  const params=new URLSearchParams(location.search);
  const openId=parseInt(params.get('channel')||'0',10);
  if(openId)selectChannel(openId);
})();
</script>
</body>
</html>
"""

"""MySifa — MyStock v2.1 (standalone page /stock)
Fixes:
- appendChild error (null children)
- Search input cursor inversion (no re-render on input)
- Navigation / back button
- Add product/emplacement button restored
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from services.auth_service import get_current_user, user_has_app_access
from app.web.access_denied import access_denied_response
from app.web.traca_guide_js import TRACA_GUIDE_SCRIPT_BLOCK

router = APIRouter()


@router.get("/stock", response_class=HTMLResponse)
def stock_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/stock", status_code=302)
        raise
    # Les fabricants peuvent accéder uniquement via ?tab=traca (outil d'étiquettes)
    tab_param = request.query_params.get("tab", "")
    if not user_has_app_access(user, "stock"):
        if user.get("role") == "fabrication" and tab_param == "traca":
            pass  # autorisé → accès limité au traça dans le JS
        else:
            return access_denied_response("MyStock")
    # Important: prevent iOS/PWA from serving stale HTML/JS.
    return HTMLResponse(
        content=STOCK_HTML,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


STOCK_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#0a0e17">
<title>MyStock — MySifa</title>
<link rel="icon" type="image/png" sizes="512x512" href="/static/mys_icon_512.png">
<link rel="apple-touch-icon" href="/static/mys_icon_180.png">
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="stylesheet" href="/static/support_widget.css">
<link rel="stylesheet" href="/static/mysifa_theme.css">
<link rel="stylesheet" href="/static/mysifa_user_chip.css">
<link rel="stylesheet" href="/static/mysifa_ai_chat.css">
<link rel="stylesheet" href="/static/mysifa_dock.css">
<style>
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;
  --muted:#94a3b8;--accent:#22d3ee;--accent-bg:rgba(34,211,238,.12);
  --success:#34d399;--warn:#fbbf24;--danger:#f87171;--c2:#a78bfa;
}
body.light{
  --bg:#f1f5f9;--card:#fff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;
  --muted:#94a3b8;--accent:#0891b2;--accent-bg:rgba(8,145,178,.10);
  --success:#059669;--warn:#d97706;--danger:#dc2626;--c2:#7c3aed;
}
html,body{height:100%}
#root{display:flex;flex:1;flex-direction:column;min-height:0}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);display:flex;flex-direction:column;min-height:100%}::-webkit-scrollbar{width:4px;height:4px}::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px}
button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
button:focus:not(:focus-visible){outline:none}
input,select{font-family:inherit}

/* ── Layout desktop / mobile ── */
.app-layout{display:flex;flex:1;overflow:hidden}

/* Sidebar desktop — bloc du bas collé au bas de l'écran, navigation seule zone scrollable */
.sidebar{width:220px;background:var(--card);border-right:1px solid var(--border);
  display:flex;flex-direction:column;flex-shrink:0;height:100vh;min-height:100vh;
  position:sticky;top:0;overflow:hidden}
.sidebar::-webkit-scrollbar{width:0}
.sidebar-logo{padding:20px 16px 8px;flex-shrink:0}.logo-brand{font-size:15px;font-weight:800}.logo-brand span{color:var(--accent)}
.logo-sub{font-size:10px;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase;margin-top:2px}
.nav-btn{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:8px;
  border:none;background:transparent;color:var(--text2);cursor:pointer;font-size:13px;
  font-weight:500;width:100%;text-align:left;font-family:inherit;transition:all .15s;margin-bottom:2px}
.nav-btn:hover,.nav-btn.active{background:var(--accent-bg);color:var(--accent)}
.nav-section-label{font-size:10px;text-transform:uppercase;letter-spacing:.8px;color:var(--muted);
  font-weight:600;padding:14px 16px 4px 16px;user-select:none;pointer-events:none}
.nav-btn--mysifa-portal{align-items:baseline;flex-wrap:wrap;gap:4px 8px;line-height:1.35}
.nav-btn--mysifa-portal:hover{background:var(--accent-bg)}
.nav-btn--mysifa-portal:hover .mysifa-back-preamble{color:var(--text2)}
.nav-btn--mysifa-portal:hover .mysifa-back-brand{color:var(--text)}
.nav-btn--mysifa-portal:hover .mysifa-back-accent{color:var(--accent)}
.mysifa-back-preamble{font-size:13px;font-weight:500;color:var(--text2);letter-spacing:0}
.mysifa-back-brand{font-size:14px;font-weight:800;letter-spacing:-.5px;color:var(--text);white-space:nowrap}
.mysifa-back-accent{color:var(--accent)}
.sidebar-nav{padding:8px 8px;flex:1;min-height:0;overflow-y:auto;-webkit-overflow-scrolling:touch}
.sidebar-nav::-webkit-scrollbar{width:4px}
.sidebar-nav::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px}
.sidebar-bottom{padding:12px 8px;border-top:1px solid var(--border);display:flex;flex-direction:column;
  gap:6px;flex-shrink:0;margin-top:auto;background:var(--card)}
.user-chip{padding:10px 12px;border-radius:8px;background:var(--accent-bg);cursor:pointer}
.user-chip:hover{background:rgba(34,211,238,.18)}
.user-chip .uc-top{display:flex;align-items:center;gap:10px;margin-bottom:6px}
.user-chip .uc-avatar{width:36px;height:36px;min-width:36px;border-radius:50%;object-fit:cover;border:1px solid var(--border);flex-shrink:0;display:block}
.user-chip .uc-info{flex:1;min-width:0}
.user-chip .uc-name,.uc-name{font-size:12px;font-weight:600;color:var(--text)}
.user-chip .uc-role,.uc-role{font-size:10px;color:var(--accent);text-transform:uppercase;letter-spacing:.5px}
.user-chip .uc-profil{font-size:10px;color:var(--accent);margin-top:3px;display:flex;align-items:center;gap:4px}
.back-mysifa{
  border:none!important;background:transparent!important;font-weight:400!important;
  color:var(--text2)!important;padding:8px 10px!important;
}
.back-mysifa:hover{color:var(--text)!important;background:transparent!important}
.back-mysifa .wm{font-weight:800;color:var(--text)}
.back-mysifa .wm span{color:var(--accent)}
.theme-btn,.logout-btn{display:flex;align-items:center;gap:8px;padding:10px 12px;border-radius:8px;
  border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;
  font-size:12px;width:100%;font-family:inherit;transition:all .15s}
.theme-btn:hover{background:var(--accent-bg);color:var(--accent);border-color:var(--accent)}
.theme-btn .theme-ico{font-size:14px;line-height:1}
.theme-btn .theme-label{white-space:nowrap}
@media (display-mode:standalone),(max-width:900px){
  .theme-btn .theme-label{display:none}
  .theme-btn{justify-content:center}
}.logout-btn{border:none}.logout-btn:hover{color:var(--danger);background:rgba(248,113,113,.1)}
.version{font-size:10px;color:var(--muted);font-family:monospace;padding:4px 12px}

/* Main area */
.main-area{flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0}

/* topbar mobile : mysifa_mobile_topbar.css */
.mobile-print-btn{
  display:none;align-items:center;justify-content:center;width:40px;height:40px;border-radius:10px;
  border:1px solid var(--border);background:var(--card);color:var(--text2);cursor:pointer;font-family:inherit;flex-shrink:0;
}
.mobile-print-btn:hover,.mobile-print-btn.active{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}

/* Sidebar overlay mobile */
.sidebar-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:200}
body.sb-open .sidebar-overlay{display:block}
@media(max-width:900px){
  .sidebar{position:fixed;left:0;top:0;bottom:0;height:auto;max-height:100vh;z-index:300;    transform:translateX(-105%);transition:transform .18s ease;
    box-shadow:0 16px 48px rgba(0,0,0,.55)}
  body.sb-open .sidebar{transform:translateX(0)}
  .mobile-print-btn{display:inline-flex}
  /* La topbar est fixed → on décale uniquement la barre de recherche. */
  body.has-topbar .search-bar-wrap{margin-top:74px}
}

/* Messagerie — mobile paysage uniquement (vue split liste + conversation) */
@media (max-width:900px) and (orientation:landscape){
  body.mysifa-app-stock #cw-panel:not(.cw-hidden){
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
    z-index:8015!important;
  }
  body.mysifa-app-stock.cw-mobile #cw-panel-left{
    display:flex!important;
    pointer-events:auto!important;
    flex:0 0 min(200px,36vw)!important;
    width:min(200px,36vw)!important;
    min-width:140px!important;
    max-width:40vw!important;
    border-right:1px solid var(--border)!important;
  }
  body.mysifa-app-stock.cw-mobile #cw-panel-right{
    display:flex!important;
    flex-direction:column!important;
    flex:1!important;
    min-width:0!important;
    min-height:0!important;
    overflow:hidden!important;
  }
  body.mysifa-app-stock.cw-mobile:not(.cw-chat-active) #cw-panel-right{
    visibility:hidden!important;
    flex:0!important;
    width:0!important;
    overflow:hidden!important;
    pointer-events:none!important;
  }
  body.mysifa-app-stock.cw-mobile.cw-chat-active #cw-panel-right{
    visibility:visible!important;
    flex:1!important;
    width:auto!important;
    pointer-events:auto!important;
  }
  body.mysifa-app-stock.cw-mobile #cw-messages{
    flex:1!important;
    min-height:0!important;
    overflow-y:auto!important;
  }
  body.mysifa-app-stock.cw-mobile #cw-input-row{
    flex-shrink:0!important;
  }
  body.mysifa-app-stock.cw-mobile.cw-chat-active .cw-list-topbar{display:none!important}
}

/* Scroll area */
.scroll-area{flex:1;overflow-y:auto}

/* ── Search bar ── */
.search-bar-wrap{padding:12px 16px;background:var(--bg);border-bottom:1px solid var(--border);
  position:sticky;top:0;z-index:90}
.search-row{display:flex;gap:8px;align-items:center}
.search-input{flex:1;background:var(--card);border:1.5px solid var(--border);border-radius:12px;
  padding:12px 16px;color:var(--text);font-size:15px;font-family:inherit;outline:none;
  transition:border-color .15s;direction:ltr;unicode-bidi:normal}
.search-input:focus{border-color:var(--accent)}
.search-icon-btn{width:44px;height:44px;border-radius:12px;border:1.5px solid var(--border);
  background:var(--card);color:var(--text2);cursor:pointer;font-size:20px;
  display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:all .15s}
.search-icon-btn svg{width:20px;height:20px;display:block}
.search-icon-btn:hover,.search-icon-btn.active{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.search-icon-btn.listening{animation:pulse-ring 1s infinite}
@keyframes pulse-ring{0%,100%{box-shadow:0 0 0 0 rgba(34,211,238,.4)}50%{box-shadow:0 0 0 8px rgba(34,211,238,0)}}
.search-results{background:var(--card);border:1px solid var(--border);border-radius:12px;
  margin-top:8px;overflow:hidden;box-shadow:0 8px 24px rgba(0,0,0,.3)}
.search-section-title{font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;
  letter-spacing:.5px;padding:10px 14px 4px}
.search-item{padding:12px 14px;cursor:pointer;display:flex;justify-content:space-between;
  align-items:center;border-bottom:1px solid var(--border);transition:background .1s}
.search-item:last-child{border-bottom:none}
.search-item:hover{background:var(--accent-bg)}
.si-ref{font-family:monospace;font-weight:700;font-size:13px;color:var(--text)}
.si-des{font-size:11px;color:var(--muted);margin-top:1px}
.si-badge{font-family:monospace;font-size:11px;font-weight:700;color:var(--accent);
  background:var(--accent-bg);padding:3px 8px;border-radius:10px;white-space:nowrap}

/* ── Content ── */
.content{padding:16px;max-width:900px}
.card{background:var(--card);border:1px solid var(--border);border-radius:14px;overflow:hidden;margin-bottom:12px}
.card-header{padding:14px 16px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap}
.card-title{font-size:14px;font-weight:700}
.card-empty{padding:32px 16px;text-align:center;color:var(--muted);font-size:13px}

/* ── Users (admin) ── */
.users-head{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;width:100%}
.users-tools{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.users-filter{background:var(--bg);border:1.5px solid var(--border);border-radius:12px;padding:10px 12px;color:var(--text);font-size:13px;outline:none;min-width:220px}
.users-filter:focus{border-color:var(--accent)}
.users-row{padding:12px 16px;display:flex;align-items:center;justify-content:space-between;gap:12px;border-bottom:1px solid var(--border)}
.users-row:last-child{border-bottom:none}
.users-main{min-width:0}
.users-name{font-size:13px;font-weight:800;color:var(--text);display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.users-meta{font-size:11px;color:var(--muted);margin-top:2px;display:flex;gap:10px;flex-wrap:wrap}
.users-meta code{font-family:monospace;color:var(--text2)}
.users-actions{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end}
.pill{font-size:10px;font-weight:800;border-radius:999px;padding:3px 9px;border:1px solid var(--border);color:var(--text2);background:transparent;text-transform:uppercase;letter-spacing:.04em}
.pill.ok{border-color:rgba(52,211,153,.45);color:var(--success);background:rgba(52,211,153,.10)}
.pill.off{border-color:rgba(248,113,113,.45);color:var(--danger);background:rgba(248,113,113,.10)}

/* ── Formulaire ajout produit ── */
.add-form{padding:16px;display:flex;flex-direction:column;gap:10px}
.add-form-inner{display:flex;flex-direction:column;gap:10px}
.add-form-row{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.add-form-actions{display:flex;align-items:center}
.add-form-actions .btn{color:var(--card)}
.empl-combo-wrap{position:relative;width:100%}
.empl-suggestions{
  position:absolute;top:100%;left:0;right:0;z-index:120;
  background:var(--card);border:1px solid var(--border);border-radius:0 0 10px 10px;
  max-height:220px;overflow-y:auto;box-shadow:0 8px 24px rgba(0,0,0,.3);
}
.empl-suggest-item{
  padding:10px 14px;cursor:pointer;font-size:13px;font-family:monospace;font-weight:700;
  border-bottom:1px solid var(--border);transition:background .1s;
}
.empl-suggest-item:hover{background:var(--accent-bg);color:var(--accent)}
.empl-suggest-add{
  padding:10px 14px;cursor:pointer;font-size:13px;font-weight:700;
  border-top:2px solid var(--border);
  background:rgba(167,139,250,.14);color:var(--c2);
}
.empl-suggest-add:hover{background:rgba(167,139,250,.26);color:var(--text)}
body.light .empl-suggest-add{background:rgba(124,58,237,.12);color:#5b21b6}
body.light .empl-suggest-add:hover{background:rgba(124,58,237,.2);color:#1e1b4b}
.field-label{font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px;display:block}
.field-input{width:100%;background:var(--bg);border:1.5px solid var(--border);border-radius:10px;
  padding:10px 13px;color:var(--text);font-size:14px;font-family:inherit;outline:none;
  transition:border-color .15s;direction:ltr}
.field-input:focus{border-color:var(--accent)}
.field-input.empl-upper{text-transform:uppercase}
.field-input.empl-upper::placeholder{
  text-transform:none;
  color:var(--text2);
  opacity:.88;
}
body.light .field-input.empl-upper::placeholder{
  color:#64748b;
  opacity:.95;
}
.btn{background:var(--accent);color:var(--text);border:none;border-radius:10px;padding:10px 20px;
  font-size:13px;font-weight:700;cursor:pointer;font-family:inherit;transition:filter .15s,box-shadow .15s,transform .05s;white-space:nowrap}
.btn:hover{filter:brightness(1.05);box-shadow:0 0 0 4px rgba(34,211,238,.18)}
.btn:active{transform:translateY(1px)}
.btn-ghost{background:transparent;color:var(--text2);border:1px solid var(--border);border-radius:10px;
  padding:10px 16px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;transition:all .15s}
.btn-ghost:hover{border-color:var(--accent);color:var(--accent)}
.btn-sm{background:var(--accent);color:var(--text);border:none;border-radius:8px;padding:7px 14px;
  font-size:12px;font-weight:700;cursor:pointer;font-family:inherit;transition:filter .15s,box-shadow .15s,transform .05s}
.btn-sm:hover{filter:brightness(1.05);box-shadow:0 0 0 4px rgba(34,211,238,.18)}
.btn-sm:active{transform:translateY(1px)}
.btn-danger{background:rgba(248,113,113,.15);color:var(--danger);border:1px solid rgba(248,113,113,.3);
  border-radius:8px;padding:6px 12px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit}

/* ── Scorecard ── */
.scorecard{background:var(--card);border:1.5px solid var(--border);border-radius:16px;padding:20px;margin-bottom:16px}
.sc-ref{font-family:monospace;font-size:clamp(18px,4.5vw,22px);font-weight:800;color:var(--text);letter-spacing:.02em;margin-bottom:8px;line-height:1.15}
.sc-des{font-size:15px;font-weight:600;color:var(--text2);margin-bottom:16px;line-height:1.35}
.sc-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:12px}
.sc-stat{background:var(--bg);border-radius:10px;padding:12px}
.sc-stat-label{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;font-weight:600;margin-bottom:4px}
.sc-stat-value{font-size:22px;font-weight:800;font-family:monospace}
.sc-stat-sub{font-size:11px;color:var(--muted);margin-top:2px}

/* ── Rows ── */
.empl-row{padding:12px 16px;display:flex;justify-content:space-between;align-items:center;
  border-bottom:1px solid var(--border);cursor:pointer;transition:background .1s}
.empl-row:last-child{border-bottom:none}
.empl-row:hover{background:var(--accent-bg)}
.empl-row.alerte{border-left:3px solid var(--warn)}
.empl-code{font-family:monospace;font-weight:800;font-size:14px;color:var(--accent)}
.empl-info{font-size:11px;color:var(--muted);margin-top:2px}
.empl-qte{font-family:monospace;font-weight:700;font-size:13px;text-align:right}
.empl-date{font-size:11px;color:var(--muted);text-align:right;margin-top:2px}

/* ── Action bar ── */
.action-bar{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap}
.action-btn{flex:1;min-width:90px;padding:12px 8px;border-radius:12px;border:none;
  font-size:13px;font-weight:700;cursor:pointer;font-family:inherit;
  display:flex;align-items:center;justify-content:center;gap:5px;transition:opacity .15s}
.action-btn:active{opacity:.75}
.action-btn.entree{background:rgba(52,211,153,.2);color:var(--success)}
.action-btn.sortie{background:rgba(248,113,113,.2);color:var(--danger)}
.action-btn.inventaire{background:rgba(167,139,250,.2);color:var(--c2)}

/* ── Historique mouvements ── */
.mvt-row{padding:10px 16px;display:flex;gap:10px;align-items:flex-start;border-bottom:1px solid var(--border)}
.mvt-row:last-child{border-bottom:none}
.mvt-icon{width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:15px;flex-shrink:0}
.mvt-icon.entree{background:rgba(52,211,153,.15);color:var(--success)}
.mvt-icon.sortie{background:rgba(248,113,113,.15);color:var(--danger)}
.mvt-icon.inventaire{background:rgba(167,139,250,.15);color:var(--c2)}
.mvt-body{flex:1;min-width:0}
.mvt-line1{font-size:13px;font-weight:600;display:flex;justify-content:space-between;align-items:center;gap:8px}
.mvt-ref-link{background:none;border:none;padding:0;margin:0;color:var(--text);cursor:pointer;
  font-weight:800;font-family:inherit;text-align:left}
.mvt-ref-link:hover{text-decoration:underline;filter:brightness(1.05)}
.mvt-ref-link:active{transform:translateY(1px)}
.mvt-empl-link{background:none;border:none;padding:0;margin:0;color:var(--text);cursor:pointer;
  font-weight:700;font-family:inherit;text-align:left}
.mvt-empl-link:hover{text-decoration:underline;filter:brightness(1.05)}
.mvt-empl-link:active{transform:translateY(1px)}
.mvt-qte-entree{color:var(--success);font-family:monospace;font-weight:700}
.mvt-qte-sortie{color:var(--danger);font-family:monospace;font-weight:700}
.mvt-qte-inventaire{color:var(--c2);font-family:monospace;font-weight:700}
.mvt-line2{font-size:11px;color:var(--muted);margin-top:2px}
.mvt-note{font-size:11px;color:var(--text2);margin-top:2px;font-style:italic}

/* ── Stats dashboard ── */
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:16px}
.dash-page{display:flex;flex-direction:column;gap:0;padding-bottom:8px}
.dash-title{font-size:22px;font-weight:800;letter-spacing:-.3px;color:var(--text);margin:0 0 20px}
.dash-kpi-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-bottom:20px}
.dash-kpi-grid .stat-card{display:flex;flex-direction:column;justify-content:center;min-height:88px}
@media(max-width:900px){.dash-kpi-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:480px){.dash-kpi-grid{grid-template-columns:1fr}}
.dash-quick-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px;margin-bottom:20px}
.dash-quick-card-title{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);margin:0 0 12px}
.dash-quick-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}
.dash-quick-btn{background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:12px 14px;
  font-size:12px;font-weight:600;color:var(--text);cursor:pointer;font-family:inherit;text-align:left;
  transition:border-color .15s,background .15s;line-height:1.35}
.dash-quick-btn:hover{border-color:var(--accent);background:var(--accent-bg);color:var(--accent)}
.dash-quick-btn-accent{background:var(--accent-bg);border-color:rgba(34,211,238,.35);color:var(--accent);font-weight:700}
.dash-quick-btn-accent:hover{filter:brightness(1.05)}
@media(max-width:768px){.dash-quick-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:480px){.dash-quick-grid{grid-template-columns:1fr}}
.dash-section{border-top:1px solid var(--border);padding-top:22px;margin-top:22px}
.dash-section-title{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;
  color:var(--muted);margin:0 0 14px}
.dash-alert-block{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px 16px;
  display:flex;flex-direction:column;min-height:100px}
.dash-alert-block h4{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);margin:0 0 12px;flex-shrink:0}
.dash-alert-rows{flex:1;min-height:0}
.dash-alert-ok{font-size:13px;color:var(--success);line-height:1.55;padding:8px 0}
.dash-alert-row{display:flex;align-items:center;gap:10px;padding:10px 8px;margin:0 -8px;border-bottom:1px solid var(--border);
  cursor:pointer;font-size:13px;color:var(--text);border-radius:8px;transition:background .12s}
.dash-alert-row:last-child{border-bottom:none}
.dash-alert-row:hover{background:var(--accent-bg)}
.dash-alert-main{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.dash-alert-qty{margin-left:auto;white-space:nowrap;color:var(--text2);font-size:11px;flex-shrink:0;text-align:right}
.dash-mp-cat{font-size:10px;font-weight:700;padding:2px 8px;border-radius:6px;text-transform:uppercase;flex-shrink:0}
.dash-mp-cat-mandrin{background:rgba(124,58,237,.15);color:#7c3aed}
.dash-mp-cat-palette{background:rgba(8,145,178,.15);color:#0891b2}
.dash-mp-cat-adhesif{background:rgba(217,119,6,.15);color:#d97706}
.dash-mp-cat-carton{background:rgba(5,150,105,.15);color:#059669}
.dash-act-card{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden}
.dash-act-list{display:flex;flex-direction:column}
.dash-act-row{display:flex;align-items:center;gap:10px;padding:10px 16px;border-bottom:1px solid var(--border);font-size:13px;color:var(--text)}
.dash-act-row:last-child{border-bottom:none}
.dash-act-row:hover{background:var(--accent-bg)}
.dash-act-badges{display:flex;gap:6px;flex-shrink:0}
.dash-act-main{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  font-family:ui-monospace,monospace;font-weight:700;color:var(--text)}
.dash-act-qte{flex-shrink:0;font-weight:800;font-family:ui-monospace,monospace;font-size:13px;color:var(--accent);white-space:nowrap}
.dash-act-row .dash-act-qte.dash-act-qte-entree{color:var(--success)}
.dash-act-row .dash-act-qte.dash-act-qte-sortie{color:var(--danger)}
.dash-act-meta{flex-shrink:0;font-size:11px;color:var(--muted);white-space:nowrap;display:inline-flex;align-items:center;flex-wrap:wrap;gap:0}
.dash-act-meta .mvt-empl-link{color:var(--muted);font-size:11px;font-weight:600}
.dash-act-main .mvt-ref-link{font-family:inherit;font-size:inherit;font-weight:inherit;color:inherit}
.dash-act-des{color:var(--text2);font-weight:400}
.dash-act-empty{padding:28px 16px;text-align:center;color:var(--muted);font-size:13px}
.dash-badge{font-size:10px;font-weight:700;padding:2px 8px;border-radius:6px;letter-spacing:.3px;flex-shrink:0;white-space:nowrap}
.dash-badge-stock-mp{background:rgba(124,58,237,.12);color:#7c3aed}
.dash-badge-stock-pf{background:color-mix(in srgb,var(--accent) 12%,transparent);color:var(--accent)}
.dash-badge-mvt-entree{background:color-mix(in srgb,var(--success) 15%,transparent);color:var(--success)}
.dash-badge-mvt-sortie{background:color-mix(in srgb,var(--danger) 15%,transparent);color:var(--danger)}
.dash-badge-mvt-ajustement{background:color-mix(in srgb,var(--warn) 15%,transparent);color:var(--warn)}
.dash-badge-mvt-transfert{background:color-mix(in srgb,var(--accent) 15%,transparent);color:var(--accent)}
.dash-badge-mvt-inventaire{background:color-mix(in srgb,var(--success) 15%,transparent);color:var(--success)}
/* ── Matières premières ── */
.mp-page{padding:0 0 24px}
.mp-pills{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px}
.mp-pill{background:var(--card);border:1px solid var(--border);border-radius:20px;padding:6px 14px;
  font-size:12px;font-weight:600;color:var(--text2);cursor:pointer;font-family:inherit;transition:all .15s}
.mp-pill:hover{border-color:var(--accent);color:var(--accent)}
.mp-pill.active{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}
.mp-search-wrap{margin-bottom:16px}
.mp-search{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:12px 16px;
  color:var(--text);font-size:14px;font-family:inherit}
.mp-search:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12)}
.mp-list{display:flex;flex-direction:column;gap:12px}
.mp-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px 16px}
.mp-card-top{display:flex;align-items:flex-start;gap:10px;flex-wrap:wrap}
.mp-card-ref{font-family:ui-monospace,monospace;font-size:14px;font-weight:700;color:var(--text);flex:1;min-width:120px}
.mp-card-stock{font-size:20px;font-weight:700;color:var(--text);white-space:nowrap}
.mp-card-des{font-size:13px;color:var(--text2);margin-top:6px;width:100%}
.mp-card-warn{font-size:12px;color:var(--warn);margin-top:4px}
.mp-card-actions{margin-top:12px;display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end}
.mp-card-actions-desktop{display:flex;gap:8px;flex-wrap:wrap}
.mp-card-actions-mobile{display:none;position:relative}
.mp-act-btn{border:none;border-radius:8px;padding:8px 12px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit}
.mp-act-entree{background:color-mix(in srgb,var(--success) 15%,transparent);color:var(--success)}
.mp-act-sortie{background:color-mix(in srgb,var(--danger) 15%,transparent);color:var(--danger)}
.mp-act-ajust{background:color-mix(in srgb,var(--warn) 15%,transparent);color:var(--warn)}
.mp-act-transf{background:color-mix(in srgb,var(--accent) 15%,transparent);color:var(--accent)}
.mp-menu-btn{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:8px 14px;font-size:16px;cursor:pointer;color:var(--text2)}
.mp-menu-drop{position:absolute;right:0;top:100%;margin-top:4px;background:var(--card);border:1px solid var(--border);
  border-radius:10px;padding:6px;min-width:140px;z-index:50;box-shadow:0 8px 24px rgba(0,0,0,.25)}
.mp-menu-drop button{display:block;width:100%;text-align:left;margin-bottom:4px}
.mp-empty{text-align:center;color:var(--muted);font-size:13px;padding:32px 16px}
#mroot{position:fixed;inset:0;z-index:550;pointer-events:none}
#mroot:not(:empty){pointer-events:auto}
.mp-modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.7);display:flex;align-items:center;justify-content:center;padding:18px}
.mp-modal{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:20px;width:100%;max-width:420px;max-height:90vh;overflow-y:auto}
.mp-modal h3{margin:0 0 16px;font-size:16px;font-weight:700;color:var(--text)}
.mp-field{margin-bottom:12px}
.mp-field label{display:block;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);margin-bottom:6px}
.mp-field input,.mp-field select,.mp-field textarea{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px 12px;color:var(--text);font-size:14px;font-family:inherit}
.mp-field textarea{min-height:72px;resize:vertical}
.mp-readonly{padding:10px 12px;background:var(--bg);border:1px solid var(--border);border-radius:10px;font-size:13px;color:var(--text2)}
.mp-hint{font-size:12px;color:var(--muted);margin-top:4px}
.mp-hint.err{color:var(--danger)}
.mp-modal-actions{display:flex;gap:10px;margin-top:16px}
.mp-drawer-overlay{position:fixed;inset:0;background:rgba(0,0,0,.55);display:flex;justify-content:flex-end}
.mp-drawer{background:var(--card);border-left:1px solid var(--border);width:100%;max-width:480px;height:100%;display:flex;flex-direction:column}
.mp-drawer-head{display:flex;align-items:center;justify-content:space-between;padding:16px 18px;border-bottom:1px solid var(--border);flex-shrink:0}
.mp-drawer-body{flex:1;overflow-y:auto;padding:16px 18px}
.mp-drawer-foot{padding:16px 18px;border-top:1px solid var(--border);flex-shrink:0}
.mp-admin-row{padding:12px 0;border-bottom:1px solid var(--border)}
.mp-admin-row:last-child{border-bottom:none}
.mp-admin-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}
.mp-admin-edit{background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:12px;margin-top:10px}
.mp-admin-err{font-size:12px;color:var(--danger);margin-top:8px}
@media(max-width:640px){
  .mp-card-actions-desktop{display:none}
  .mp-card-actions-mobile{display:block}
  .mp-drawer{max-width:100%}
}
/* ── Historique mouvements ── */
.hist-page{padding:0 0 24px}
.hist-title{font-size:22px;font-weight:800;letter-spacing:-.3px;color:var(--text);margin:0 0 4px}
.hist-subtitle{font-size:12px;color:var(--muted);margin:0}
.hist-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:18px}
.hist-head-actions{display:flex;gap:8px;flex-shrink:0}
.hist-filters-toggle{display:none;width:100%;justify-content:center;margin-bottom:10px}
.hist-filters-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px;margin-bottom:18px}
.hist-filters-card.sticky{position:sticky;top:0;z-index:20;box-shadow:0 4px 20px rgba(0,0,0,.12)}
body.light .hist-filters-card.sticky{box-shadow:0 4px 16px rgba(15,23,42,.08)}
.hist-filters-card-title{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);margin:0 0 12px}
.hist-filters-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;align-items:end}
.hist-filter-field{display:flex;flex-direction:column;gap:6px;min-width:0}
.hist-filter-field label{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted)}
.hist-filter-field input,.hist-filter-field select{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:10px;
  padding:10px 14px;color:var(--text);font-size:13px;font-family:inherit}
.hist-filter-field input:focus,.hist-filter-field select:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12)}
.hist-filter-field select:disabled{opacity:.55;cursor:not-allowed}
.hist-filters-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px;padding-top:12px;border-top:1px solid var(--border)}
.hist-loading{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;padding:56px 16px;
  color:var(--muted);font-size:13px;background:var(--card);border:1px solid var(--border);border-radius:12px}
.hist-spinner{width:28px;height:28px;border:2px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:hist-spin .7s linear infinite}
@keyframes hist-spin{to{transform:rotate(360deg)}}
.hist-empty{text-align:center;color:var(--muted);font-size:13px;padding:48px 20px;background:var(--card);
  border:1px solid var(--border);border-radius:12px;line-height:1.5}
.hist-results-card{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden}
.hist-results-head{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 16px;
  border-bottom:1px solid var(--border);background:#fff;color:#0f172a;flex-wrap:wrap}
.hist-results-head-left{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;min-width:0}
.hist-results-head-nav{display:flex;align-items:center;gap:8px;flex-shrink:0;flex-wrap:wrap}
.hist-results-head .hist-results-title{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:#64748b}
.hist-results-head .hist-count{font-size:12px;font-weight:600;color:#475569}
.hist-results-head .hist-pagination-info{font-size:12px;color:#475569;font-weight:600;min-width:88px;text-align:center;white-space:nowrap}
.hist-results-head-nav .btn{min-width:96px}
.hist-results-title{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted)}
.hist-count{font-size:12px;font-weight:600;color:var(--text2)}
.hist-table-wrap{display:block;overflow-x:auto;-webkit-overflow-scrolling:touch}
.hist-table{width:100%;min-width:1040px;border-collapse:collapse;font-size:13px}
.hist-unite{font-size:12px;color:var(--text2);white-space:nowrap}
.hist-table thead th{font-size:10px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);
  background:var(--bg);border-bottom:1px solid var(--border);padding:11px 14px;text-align:left;font-weight:600;white-space:nowrap}
.hist-table tbody td{padding:12px 14px;border-bottom:1px solid var(--border);color:var(--text);vertical-align:middle}
.hist-table tbody tr:last-child td{border-bottom:none}
.hist-table tbody tr:hover{background:var(--accent-bg)}
.hist-cell-badges{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.hist-ref{font-family:ui-monospace,monospace;font-size:12px;font-weight:700;color:var(--text)}
.hist-ref .mvt-ref-link,.hist-card-ref .mvt-ref-link{font-family:inherit;font-size:inherit;font-weight:inherit;color:inherit}
.hist-empl{font-size:12px;white-space:nowrap}
.hist-empl-chain{display:inline-flex;align-items:center;flex-wrap:wrap;gap:0}
.hist-empl-sep{color:var(--muted);pointer-events:none}
.hist-des{color:var(--text2);font-size:13px}
.hist-muted{color:var(--muted);font-size:12px;white-space:nowrap}
.hist-qte{font-weight:700;font-family:ui-monospace,monospace;font-size:13px}
.hist-qte-entree{color:var(--success)}
.hist-qte-sortie{color:var(--danger)}
.hist-op{font-size:12px;color:var(--text2)}
.hist-note-cell{max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.hist-badge{font-size:10px;font-weight:700;border-radius:6px;padding:2px 8px;display:inline-block;white-space:nowrap;line-height:1.4}
.hist-badge-stock-mp{background:rgba(124,58,237,.12);color:#7c3aed}
.hist-badge-stock-pf{background:color-mix(in srgb,var(--accent) 12%,transparent);color:var(--accent)}
.hist-badge-mvt-entree,.hist-badge-mvt-inventaire{background:color-mix(in srgb,var(--success) 15%,transparent);color:var(--success)}
.hist-badge-mvt-sortie{background:color-mix(in srgb,var(--danger) 15%,transparent);color:var(--danger)}
.hist-badge-mvt-ajustement{background:color-mix(in srgb,var(--warn) 15%,transparent);color:var(--warn)}
.hist-badge-mvt-transfert{background:color-mix(in srgb,var(--accent) 15%,transparent);color:var(--accent)}
.hist-cards{display:none;flex-direction:column;gap:0}
.hist-card{padding:14px 16px;border-bottom:1px solid var(--border)}
.hist-card:last-child{border-bottom:none}
.hist-card-top{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:10px}
.hist-card-badges{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
.hist-card-date{font-size:11px;color:var(--muted);white-space:nowrap}
.hist-card-ref{font-family:ui-monospace,monospace;font-size:13px;font-weight:700;color:var(--text);margin-bottom:2px}
.hist-card-des{font-size:12px;color:var(--text2);line-height:1.4;margin-bottom:10px}
.hist-card-stats{display:grid;grid-template-columns:auto 1fr;gap:4px 12px;font-size:12px}
.hist-card-stats dt{color:var(--muted);font-weight:600}
.hist-card-stats dd{margin:0;color:var(--text2)}
.hist-card-note{font-size:12px;color:var(--muted);margin-top:10px;padding-top:10px;border-top:1px solid var(--border);line-height:1.45}
@media(max-width:1100px){
  .hist-col-optional{display:none}
  .hist-table{min-width:720px}
}
@media(max-width:1000px){
  .hist-filters-grid{grid-template-columns:repeat(3,minmax(0,1fr))}
}
@media(max-width:768px){
  .hist-filters-toggle{display:flex}
  .hist-filters-card.collapsed .hist-filters-grid,.hist-filters-card.collapsed .hist-filters-actions{display:none}
  .hist-filters-grid{grid-template-columns:1fr 1fr;gap:10px}
  .hist-head{flex-direction:column;align-items:stretch}
  .hist-head-actions{width:100%}
  .hist-head-actions .btn{flex:1}
  .hist-table-wrap{display:none}
  .hist-cards{display:flex}
  .hist-results-head{flex-direction:column;align-items:stretch}
  .hist-results-head-nav{width:100%;justify-content:space-between}
  .hist-results-head-nav .btn{flex:1;min-width:0}
}
@media(max-width:480px){
  .hist-filters-grid{grid-template-columns:1fr}
  .hist-title{font-size:18px}
}
.stat-card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:16px}
.stat-label{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;font-weight:600;margin-bottom:6px}
.stat-value{font-size:26px;font-weight:800;font-family:monospace}
.stat-value.accent{color:var(--accent)}
.stat-value.warn{color:var(--warn)}

/* ── Étiquettes traçabilité ── */
.traca-section-title{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:var(--muted);margin:16px 0 10px;padding:0 2px}
.traca-postes-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;margin-bottom:8px}
.traca-poste-card{background:var(--card);border:1.5px solid var(--border);border-radius:14px;
  padding:16px 12px;cursor:pointer;transition:all .15s;text-align:center;user-select:none}
.traca-poste-card:hover{border-color:var(--accent);background:var(--accent-bg);transform:translateY(-1px)}
.traca-poste-card:active{transform:scale(.97)}
.traca-poste-icon{display:flex;align-items:center;justify-content:center;
  width:44px;height:44px;border-radius:12px;margin:0 auto 10px;font-size:22px}
.traca-poste-label{font-size:12px;font-weight:700;color:var(--text);line-height:1.3}
.traca-poste-count{font-size:10px;color:var(--muted);margin-top:3px}
.traca-back-bar{display:flex;align-items:center;gap:10px;margin-bottom:16px}
.traca-back-btn{display:flex;align-items:center;gap:5px;background:none;border:none;
  padding:6px 10px;border-radius:10px;cursor:pointer;font-size:13px;font-weight:600;
  color:var(--text2);font-family:inherit;transition:background .1s}
.traca-back-btn:hover{background:var(--accent-bg);color:var(--accent)}
.traca-poste-heading{font-size:16px;font-weight:800;color:var(--text)}
.traca-etiq-list{display:flex;flex-direction:column;gap:10px}
.traca-etiq-card{background:var(--card);border:1.5px solid var(--border);border-radius:14px;
  padding:14px 16px;display:flex;align-items:center;gap:14px;transition:border-color .15s}
.traca-etiq-card:hover{border-color:var(--accent)}
.traca-etiq-icon-wrap{width:40px;height:40px;border-radius:10px;flex-shrink:0;
  display:flex;align-items:center;justify-content:center}
.traca-etiq-body{flex:1;min-width:0}
.traca-etiq-label{font-size:14px;font-weight:700;margin-bottom:3px}
.traca-etiq-meta{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.traca-format-badge{font-size:10px;font-weight:700;padding:2px 7px;border-radius:6px;
  background:var(--accent-bg);color:var(--accent);letter-spacing:.3px}
.traca-printer-badge{font-size:10px;color:var(--muted);display:flex;align-items:center;gap:3px}
.traca-print-btn{flex-shrink:0;display:flex;align-items:center;gap:6px;
  padding:8px 14px;border-radius:10px;border:none;cursor:pointer;
  font-size:12px;font-weight:700;font-family:inherit;
  background:var(--accent);color:#fff;transition:opacity .15s}
.traca-print-btn:active{opacity:.75}
.traca-dev-banner{display:flex;align-items:center;gap:10px;background:var(--accent-bg);
  border:1px solid var(--accent);border-radius:10px;padding:10px 14px;
  font-size:12px;color:var(--accent);margin-bottom:14px;font-weight:600}
/* ── Formulaire étiquette palettes ── */
.etiq-form-row{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px}
.etiq-form-field{display:flex;flex-direction:column;gap:4px}
.etiq-form-label{font-size:11px;font-weight:600;opacity:0.6;text-transform:uppercase;letter-spacing:.4px}
.etiq-preview-section{margin-top:4px;margin-bottom:4px}
.etiq-preview-title{font-size:11px;opacity:0.5;margin-bottom:8px;font-style:italic}
.etiq-preview-grid{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:4px}
.etiq-label-card{width:105px;height:50px;border:1.5px solid #444;border-radius:2px;
  padding:3px 5px;display:flex;flex-direction:column;justify-content:space-between;
  background:#fff;color:#000;font-family:Arial,sans-serif;flex-shrink:0;position:relative}
.etiq-lbl-brand{font-size:6px;color:#888;letter-spacing:.3px;text-transform:uppercase}
.etiq-lbl-ref{font-size:8.5px;font-weight:700;line-height:1.15;flex:1;display:flex;align-items:center;
  overflow:hidden;word-break:break-all}
.etiq-lbl-palette{font-size:11px;font-weight:900;text-align:right;letter-spacing:.5px;line-height:1}
.etiq-lbl-num{font-size:7px;position:absolute;top:3px;right:5px;color:#aaa;font-style:italic}
.etiq-more-note{font-size:11px;opacity:0.5;padding:8px 0;font-style:italic}

/* ── Inventaire chaîne ── */
.nav-wip-badge{margin-left:auto;font-size:14px;line-height:1;padding:2px 4px;border-radius:4px;cursor:pointer;opacity:.75;transition:opacity .15s;background:none;border:none;color:inherit;flex-shrink:0}
.nav-wip-badge:hover{opacity:1;background:rgba(255,200,0,.15)}
.wip-page{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:60px 20px;text-align:center;gap:12px}
.wip-page-icon{font-size:52px;line-height:1}
.wip-page-title{font-size:17px;font-weight:700;color:var(--text)}
.wip-page-sub{font-size:13px;color:var(--muted);max-width:280px}
.wip-admin-banner{display:flex;align-items:center;gap:10px;background:rgba(255,180,0,.12);border:1px solid rgba(255,180,0,.35);border-radius:8px;padding:10px 14px;margin-bottom:14px;font-size:12px;color:var(--warn);font-weight:600}
.inv-item{padding:13px 16px;display:flex;align-items:center;gap:12px;border-bottom:1px solid var(--border);cursor:pointer;transition:background .1s}
.inv-item:last-child{border-bottom:none}
.inv-item:hover{background:var(--accent-bg)}
.inv-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}
.inv-dot.urgent{background:var(--danger)}
.inv-dot.attention{background:var(--warn)}
.inv-label{flex:1;min-width:0}
.inv-ref{font-family:monospace;font-weight:700;font-size:13px}
.inv-empl{font-size:11px;color:var(--muted);margin-top:2px}
.inv-days{font-size:12px;font-weight:700;white-space:nowrap}
.inv-days.urgent{color:var(--danger)}
.inv-days.attention{color:var(--warn)}

/* ── Modal mouvement (bottom sheet) ── */
.modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:500;
  display:flex;flex-direction:column;justify-content:flex-end}
@media(min-width:600px){.modal-overlay{align-items:center;justify-content:center}}
.modal-sheet{background:var(--card);border-radius:20px 20px 0 0;padding:24px 20px;
  max-height:90vh;overflow-y:auto;width:100%}
@media(min-width:600px){.modal-sheet{border-radius:20px;max-width:480px}}
.modal-handle{width:40px;height:4px;background:var(--border);border-radius:2px;margin:0 auto 20px;display:block}
.modal-title{font-size:17px;font-weight:800;margin-bottom:6px}
.modal-sub{font-size:12px;color:var(--muted);margin-bottom:18px}
.mvt-origin-group{display:flex;gap:10px;flex-wrap:wrap;margin-top:6px}
.mvt-origin-label{display:inline-flex;align-items:center;gap:7px;font-size:13px;cursor:pointer;padding:7px 12px;border:1.5px solid var(--border);border-radius:8px;background:var(--bg);transition:background .15s,border-color .15s;user-select:none}
.mvt-origin-label:hover{background:var(--accent-bg);border-color:var(--accent)}
.mvt-origin-label input[type=checkbox]{accent-color:var(--accent);width:15px;height:15px;cursor:pointer;flex-shrink:0;margin:0}
.mvt-type-btns{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:20px}
.mvt-type-btn{padding:13px 6px;border-radius:12px;border:1.5px solid var(--border);
  background:transparent;color:var(--text2);cursor:pointer;font-size:12px;font-weight:700;
  font-family:inherit;text-align:center;transition:all .15s}
.mvt-type-btn.sel-entree{background:rgba(52,211,153,.15);color:var(--success);border-color:var(--success)}
.mvt-type-btn.sel-sortie{background:rgba(248,113,113,.15);color:var(--danger);border-color:var(--danger)}
.mvt-type-btn.sel-inventaire{background:rgba(167,139,250,.15);color:var(--c2);border-color:var(--c2)}
.modal-field{margin-bottom:14px}
.empl-suggestions{background:var(--bg);border:1px solid var(--border);border-radius:8px;
  margin-top:4px;overflow:hidden;max-height:140px;overflow-y:auto}
.empl-sugg-item{padding:10px 14px;cursor:pointer;font-family:monospace;font-size:13px;
  font-weight:700;border-bottom:1px solid var(--border);transition:background .1s}
.empl-sugg-item:last-child{border-bottom:none}
.empl-sugg-item:hover{background:var(--accent-bg);color:var(--accent)}
.unit-suggest-item{padding:10px 14px;cursor:pointer;font-family:inherit;font-size:13px;
  font-weight:700;border-bottom:1px solid var(--border);transition:background .1s}
.unit-suggest-item:last-child{border-bottom:none}
.unit-suggest-item:hover{background:var(--accent-bg);color:var(--accent)}
.unit-suggest-add{padding:10px 14px;cursor:pointer;font-size:12px;font-weight:800;color:var(--c2);
  background:rgba(167,139,250,.10);border-top:1px solid rgba(167,139,250,.35)}
.unit-suggest-add:hover{background:rgba(167,139,250,.16)}
.modal-actions{display:grid;grid-template-columns:1fr 2fr;gap:10px;margin-top:16px}
.btn-cancel{background:transparent;border:1.5px solid var(--border);border-radius:12px;
  padding:13px;font-size:14px;font-weight:700;color:var(--text2);cursor:pointer;font-family:inherit}
.support-btn{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:8px;border:1px solid var(--border);
  background:transparent;color:var(--text2);cursor:pointer;font-size:12px;width:100%;font-family:inherit;transition:all .15s}
.support-btn:hover{background:var(--accent-bg);color:var(--accent);border-color:var(--accent)}
.support-ico{display:inline-flex;align-items:center;justify-content:center}

/* Modal contact support (messagerie interne) */
.contact-modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:650;display:flex;align-items:center;justify-content:center;padding:18px}
.contact-modal{width:100%;max-width:560px;background:var(--card);border:1px solid var(--border);border-radius:16px;padding:18px 18px 16px;box-shadow:0 24px 64px rgba(0,0,0,.4);position:relative}
.contact-modal h3{font-size:16px;font-weight:800;margin:0 0 12px;padding-right:34px}
.ref-import-drop{border:1.5px dashed var(--border);border-radius:12px;padding:24px 16px;text-align:center;
  background:var(--bg);cursor:pointer;transition:border-color .15s,background .15s}
.ref-import-drop:hover,.ref-import-drop.dragover{border-color:var(--accent);background:var(--accent-bg)}
.ref-import-drop-title{font-size:13px;font-weight:700;color:var(--text);margin-bottom:4px}
.ref-import-drop-sub{font-size:11px;color:var(--muted)}
.ref-import-table-wrap{max-height:320px;overflow:auto;margin:14px 0;border:1px solid var(--border);border-radius:10px}
.ref-import-table{width:100%;border-collapse:collapse;font-size:12px}
.ref-import-table th{position:sticky;top:0;background:var(--card);padding:8px 10px;text-align:left;
  font-size:10px;text-transform:uppercase;letter-spacing:.4px;color:var(--muted);border-bottom:1px solid var(--border)}
.ref-import-table td{padding:8px 10px;border-bottom:1px solid var(--border);vertical-align:top}
.ref-import-table tr:last-child td{border-bottom:none}
.ref-import-badge{display:inline-block;padding:2px 8px;border-radius:20px;font-size:10px;font-weight:700}
.ref-import-badge.create{background:rgba(52,211,153,.15);color:var(--success)}
.ref-import-badge.update{background:rgba(34,211,238,.15);color:var(--accent)}
.ref-import-badge.unchanged{background:rgba(148,163,184,.12);color:var(--muted)}
.ref-import-badge.error{background:rgba(248,113,113,.15);color:var(--danger)}
.ref-header-actions{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
/* ── Référentiel (onglet Réf. & unités de vente) ── */
.content.ref-page{max-width:960px;padding:24px 22px 40px}
.ref-page-hero{margin-bottom:28px}
.ref-page-title{font-size:22px;font-weight:800;letter-spacing:-.3px;margin:0 0 10px;color:var(--text)}
.ref-page-desc{font-size:13px;color:var(--muted);line-height:1.65;margin:0;max-width:640px}
.ref-stat-pill{display:inline-flex;align-items:center;gap:12px;margin-top:18px;padding:14px 18px;
  background:var(--card);border:1px solid var(--border);border-radius:14px}
.ref-stat-pill .stat-label{margin:0;font-size:10px}
.ref-stat-pill .stat-value{font-size:22px;line-height:1}
.ref-card{background:var(--card);border:1px solid var(--border);border-radius:16px;margin-bottom:20px;overflow:hidden}
.ref-card-header{padding:18px 22px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap}
.ref-card-header .card-title{font-size:15px;font-weight:800}
.ref-card-body{padding:20px 22px 22px}
.ref-card-desc{font-size:13px;color:var(--muted);line-height:1.6;margin:0 0 18px;max-width:560px}
.ref-card-body .ref-card-desc:last-child{margin-bottom:0}
.contact-modal.ref-import-modal{padding:22px 24px 20px}
.contact-modal.ref-import-modal h3{margin-bottom:16px;font-size:17px}
.ref-card-actions{display:flex;gap:10px;flex-wrap:wrap;padding-top:4px}
.ref-units-card .ref-card-body{padding-top:6px}
.ref-units-card .ref-card-desc{margin-bottom:16px}
.ref-page .btn-ghost-sm{padding:9px 14px;border-radius:10px}
.ref-import-drop{padding:36px 24px;border-radius:14px;margin-top:4px}
.ref-import-drop-title{font-size:14px;margin-bottom:8px}
.ref-import-drop-sub{font-size:12px;line-height:1.5}
.ref-import-table-wrap{margin:18px 0;border-radius:12px}
.ref-import-table th,.ref-import-table td{padding:10px 14px}
.btn-ghost-sm{background:transparent;border:1px solid var(--border);border-radius:8px;padding:7px 12px;
  font-size:12px;font-weight:700;color:var(--text2);cursor:pointer;font-family:inherit;display:inline-flex;
  align-items:center;gap:6px;transition:all .15s}
.btn-ghost-sm:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.contact-close{position:absolute;top:14px;right:14px;width:32px;height:32px;border-radius:10px;border:1px solid var(--border);
  background:var(--bg);color:var(--muted);cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:18px;line-height:1}
.contact-close:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.contact-modal label{display:block;font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin:10px 0 4px}
.contact-modal input,.contact-modal textarea{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px 12px;color:var(--text);font-size:13px;font-family:inherit;outline:none}
.contact-modal textarea{min-height:140px;resize:vertical}
.contact-modal input:focus,.contact-modal textarea:focus{border-color:var(--accent)}
.contact-actions{display:flex;gap:10px;justify-content:flex-end;margin-top:14px}
.btn-sec{background:transparent;border:1px solid var(--border);color:var(--muted);border-radius:12px;
  padding:12px 14px;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit;transition:box-shadow .2s,border-color .15s,color .15s,filter .15s}
.btn-sec:hover{box-shadow:0 0 0 1px rgba(34,211,238,.32),0 0 20px rgba(34,211,238,.2);border-color:rgba(34,211,238,.45);color:var(--accent)}
.btn-sec:active{transform:translateY(1px)}
.btn-confirm{border:none;border-radius:12px;padding:13px;font-size:14px;font-weight:700;
  cursor:pointer;font-family:inherit;color:#0a0e17}
.btn-confirm.entree{background:var(--success)}
.btn-confirm.sortie{background:var(--danger)}
.btn-confirm.inventaire{background:var(--c2)}

/* ── Toast ── */
.toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);z-index:600;
  background:var(--card);border-radius:12px;padding:12px 20px;font-size:14px;font-weight:600;
  box-shadow:0 8px 32px rgba(0,0,0,.4);animation:fadeUp .25s;white-space:nowrap;
  border-left:3px solid var(--accent)}
.toast.error{border-left-color:var(--danger);color:var(--danger)}
.toast.warn{border-left-color:var(--warn);color:var(--warn)}
@keyframes fadeUp{from{opacity:0;transform:translateX(-50%) translateY(10px)}to{opacity:1;transform:translateX(-50%) translateY(0)}}

/* ── FAB ── */
.fab{position:fixed;bottom:24px;right:24px;width:52px;height:52px;border-radius:26px;
  background:var(--accent);color:#0a0e17;border:none;font-size:22px;cursor:pointer;
  box-shadow:0 4px 20px rgba(34,211,238,.4);display:flex;align-items:center;justify-content:center;
  z-index:200;transition:transform .15s;font-weight:700}
.fab:active{transform:scale(.9)}

/* ── Caméra ── */
.camera-modal{position:fixed;inset:0;background:rgba(0,0,0,.9);z-index:600;
  display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;padding:20px}
.camera-wrap{position:relative;width:100%;max-width:360px}
.camera-video{width:100%;border-radius:16px;display:block}
.camera-frame{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
  width:200px;height:200px;border:2px solid var(--accent);border-radius:12px;
  box-shadow:0 0 0 2000px rgba(0,0,0,.5);pointer-events:none}
.camera-hint{font-size:13px;color:var(--text2);text-align:center;max-width:300px}
.camera-result{background:var(--accent-bg);border:1px solid var(--accent);border-radius:10px;
  padding:12px 20px;font-family:monospace;font-size:14px;color:var(--accent);text-align:center;min-width:200px}
.btn-close-cam{background:var(--danger);color:#fff;border:none;border-radius:12px;
  padding:12px 32px;font-size:14px;font-weight:700;cursor:pointer;font-family:inherit}

/* ── Réception matière ─────────────────────────────────────── */
.recep-page{padding:20px;max-width:860px;margin:0 auto;display:flex;flex-direction:column;gap:20px}
.recep-head-row{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;flex-wrap:wrap;width:100%}
.recep-head-row .recep-title{flex:1;min-width:0;margin:0}
.recep-title{font-size:18px;font-weight:800}
.recep-title span{color:var(--accent)}
.recep-layout{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:700px){.recep-layout{grid-template-columns:1fr}}
.recep-card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:16px;display:flex;flex-direction:column;gap:12px}
.recep-card-title{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;color:var(--muted);display:flex;align-items:center;gap:7px}
/* Scanner vidéo */
.recep-video-wrap{position:relative;border-radius:12px;overflow:hidden;background:#000;aspect-ratio:4/3;max-height:260px;display:flex;align-items:center;justify-content:center}
.recep-video{width:100%;height:100%;object-fit:cover}
.recep-scan-frame{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
  width:65%;max-width:200px;aspect-ratio:1;border:2.5px solid var(--accent);border-radius:10px;pointer-events:none}
.recep-scan-frame::before,.recep-scan-frame::after{content:'';position:absolute;width:20px;height:20px}
.recep-scan-line{position:absolute;top:50%;left:6%;right:6%;height:2px;background:linear-gradient(90deg,transparent,var(--accent),transparent);animation:scanline 1.8s ease-in-out infinite}
@keyframes scanline{0%,100%{top:15%}50%{top:85%}}
.recep-cam-placeholder{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;color:var(--muted);padding:30px;text-align:center;aspect-ratio:4/3;max-height:260px}
.recep-cam-icon{font-size:40px;opacity:.4}
/* Tableau scannés */
.recep-table-wrap{overflow-x:auto}
.recep-table{width:100%;border-collapse:collapse}
.recep-table th{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.8px;padding:6px 10px;border-bottom:1px solid var(--border);text-align:left;font-weight:700}
.recep-table td{padding:7px 10px;font-size:13px;border-bottom:1px solid rgba(255,255,255,.04);color:var(--text2);vertical-align:middle}
.recep-table tr:last-child td{border-bottom:none}
.recep-table tr.recep-row-new td{animation:rowflash .5s ease-out}
@keyframes rowflash{from{background:rgba(34,211,238,.18)}to{background:transparent}}
.recep-code{font-family:monospace;font-size:13px;font-weight:700;color:var(--text)}
.recep-del-btn{border:none;background:transparent;color:var(--muted);cursor:pointer;padding:3px 6px;border-radius:4px;font-size:13px;line-height:1;transition:color .1s}
.recep-del-btn:hover{color:var(--danger)}
.recep-empty{padding:30px;text-align:center;color:var(--muted);font-size:13px}
/* Actions */
.recep-actions{display:flex;gap:8px;flex-wrap:wrap;align-items:center;justify-content:flex-end}
.recep-count{font-size:12px;color:var(--muted);flex:1}
.recep-count strong{color:var(--accent)}
.recep-note-inp{width:100%;background:var(--bg);border:1.5px solid var(--border);border-radius:8px;padding:8px 12px;font-size:13px;color:var(--text);font-family:inherit;outline:none;transition:border-color .15s}
.recep-note-inp:focus{border-color:var(--accent)}
.recep-note-inp::placeholder{color:var(--muted)}
/* Historique */
.recep-hist{background:var(--card);border:1px solid var(--border);border-radius:14px;overflow:hidden}
.recep-hist-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
.recep-hist-row{min-width:min(100%,560px)}
.recep-hist-head{padding:12px 16px;border-bottom:1px solid var(--border);font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;color:var(--muted);display:flex;align-items:center;gap:7px}
.recep-hist-row{display:flex;align-items:center;gap:12px;padding:10px 16px;border-bottom:1px solid rgba(255,255,255,.04);transition:background .1s;cursor:pointer}
.recep-hist-row:last-child{border-bottom:none}
.recep-hist-row:hover{background:rgba(34,211,238,.04)}
.recep-hist-date{font-size:12px;font-family:monospace;color:var(--text2);white-space:nowrap;flex-shrink:0}
.recep-hist-count{background:var(--accent-bg);color:var(--accent);font-size:11px;font-weight:700;padding:2px 9px;border-radius:20px;white-space:nowrap;flex-shrink:0}
.recep-hist-note{font-size:12px;color:var(--muted);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.recep-hist-four{font-size:11px;color:var(--accent);font-weight:600;flex-shrink:0;max-width:100px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.recep-hist-user{font-size:11px;color:var(--muted);flex-shrink:0}
/* Fournisseur search */
.recep-fourn-wrap{margin-top:8px}
.recep-fourn-label{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:var(--muted);margin-bottom:4px;display:flex;align-items:center;gap:6px}
.recep-fourn-search-wrap{position:relative}
.recep-fourn-inp{width:100%;background:var(--bg);border:1.5px solid var(--border);border-radius:8px;padding:9px 12px;font-size:13px;color:var(--text);outline:none;transition:border-color .15s;box-sizing:border-box}
.recep-fourn-inp:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12)}
body.light .recep-fourn-inp:focus{box-shadow:0 0 0 3px rgba(8,145,178,.12)}
.recep-fourn-sel{width:100%;background:var(--bg);border:1.5px solid var(--border);border-radius:8px;padding:9px 12px;font-size:13px;color:var(--text);outline:none;transition:border-color .15s,box-shadow .15s;box-sizing:border-box;font-family:inherit;cursor:pointer;margin-top:0;margin-bottom:12px;-webkit-appearance:none;appearance:none}
.recep-fourn-sel:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12)}
body.light .recep-fourn-sel:focus{box-shadow:0 0 0 3px rgba(8,145,178,.12)}
.recep-fourn-inp::placeholder{color:var(--muted)}
.recep-fourn-inp.recep-fourn-selected{border-color:var(--accent);background:var(--accent-bg);font-weight:600}
.recep-fourn-clear{position:absolute;right:6px;top:50%;transform:translateY(-50%);background:var(--border);border:none;border-radius:50%;width:22px;height:22px;cursor:pointer;font-size:12px;color:var(--text2);display:flex;align-items:center;justify-content:center}
.recep-fourn-clear:hover{background:var(--danger);color:#fff}
.recep-fourn-dropdown{position:absolute;top:100%;left:0;right:0;background:var(--card);border:1px solid var(--border);border-radius:8px;max-height:220px;overflow-y:auto;z-index:50;display:none;box-shadow:0 8px 24px rgba(0,0,0,.12)}
.recep-fourn-dropdown.open{display:block}
.recep-fourn-item{display:flex;align-items:center;justify-content:space-between;padding:8px 12px;cursor:pointer;font-size:13px;transition:background .1s}
.recep-fourn-item:hover{background:var(--accent-bg)}
.recep-fourn-item-nom{font-weight:600;color:var(--text)}
.recep-fourn-item-cert{font-size:10px;color:var(--muted);font-family:monospace}
.recep-fourn-empty{padding:12px;text-align:center;color:var(--muted);font-size:12px}
.recep-fourn-fsc{margin-top:4px;font-size:11px;color:var(--muted);padding-left:2px}
.recep-fourn-fsc strong{color:var(--text2)}
.recep-hist-empty{padding:24px;text-align:center;color:var(--muted);font-size:13px}
/* Détail lot (expandable) */
.recep-hist-detail{padding:8px 16px 12px;display:flex;flex-wrap:wrap;gap:6px}
.recep-hist-chip{font-family:monospace;font-size:11px;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:3px 9px;color:var(--text2)}
/* Input manuel */
.recep-manual-wrap{display:flex;gap:8px}
.recep-manual-inp{flex:1;background:var(--bg);border:1.5px solid var(--border);border-radius:8px;padding:9px 12px;font-size:13px;color:var(--text);font-family:monospace;outline:none;transition:border-color .15s}
.recep-manual-inp:focus{border-color:var(--accent)}
.recep-manual-inp::placeholder{color:var(--muted)}
.btn-recep{display:inline-flex;align-items:center;gap:6px;padding:9px 16px;border-radius:9px;border:none;cursor:pointer;font-family:inherit;font-size:13px;font-weight:700;transition:all .15s;white-space:nowrap}
.btn-recep:hover{filter:brightness(1.1);transform:translateY(-1px)}
.btn-recep:active{transform:translateY(0)}
.btn-recep:disabled{opacity:.4;cursor:not-allowed;transform:none;filter:none}
.btn-recep-primary{background:var(--accent);color:#0a0e17}
.btn-recep-success{background:var(--success);color:#0a0e17}
.btn-recep-danger{background:var(--danger);color:#fff}
.btn-recep-ghost{background:var(--accent-bg);color:var(--accent);border:1px solid rgba(34,211,238,.3)}
.btn-recep-muted{background:transparent;color:var(--text2);border:1px solid var(--border)}
.btn-recep-muted:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.recep-dup-badge{font-size:10px;padding:2px 6px;border-radius:5px;background:rgba(251,191,36,.2);color:var(--warn);font-weight:700;margin-left:6px}
</style>
</head>
<body>
<script src="/static/mysifa_theme.js"></script>
<script src="/static/mysifa_favicon_badge.js"></script>
<script src="/static/mysifa_user_chip.js"></script>
<div id="root"></div>
<div id="mroot"></div>
<script src="/static/support_widget.js"></script>
<script>window.__MYSIFA_APP__='stock';</script>
<script src="/static/mysifa_dock.js"></script>
<script src="/static/mysifa_calc.js"></script>
<script src="/static/chat_widget.js"></script>
<script src="/static/mysifa_ai_chat.js"></script>
<script>
/*__TRACA_GUIDE__*/
const API = window.location.origin;

// ── State ───────────────────────────────────────────────────────
let S = {
  user: null,
  tab: 'dashboard',
  stockReadOnly: false,
  tracaOnly: false,   // fabrication : accès limité à l'onglet traça
  sidebarOpen: false,
  searchQuery: '',
  searchResults: null,
  selProduit: null,
  selEmpl: null,
  dashboard: null,
  inventaireList: [],
  modalMvt: null,
  modalType: 'entree',
  toast: null,
  listening: false,
  scanning: false,
  cameraStream: null,
  barcodeReader: null,
  emplSuggestions: [],
  showAddForm: false,
  // Nouveau support (messagerie interne)
  contactOpen: false,
  contactSubject: '',
  contactMessage: '',
  contactSending: false,
  // Unités de vente personnalisées
  unitModalOpen: false,
  unitNewLabel: '',
  unitNewBase: 'cartons',
  unitNewQty: '',
  // Étiquettes traçabilité
  tracaPoste: null,
  tracaPrintModal: null,
  // Réception matière
  recepItems: [],          // [{code, ts, isNew}] — tableau temporaire en cours de scan
  recepNote: '',           // note optionnelle sur la réception
  recepScanning: false,    // caméra active
  recepStream: null,       // MediaStream (caméra)
  recepBarcodeReader: null, // ZXing reader instance
  recepHistory: [],        // lots passés (chargés depuis API)
  recepHistLoading: false,
  recepExpandedId: null,   // lot ouvert dans l'historique
  recepManual: '',         // valeur du champ saisie manuelle
  recepFournisseur: '',     // fournisseur sélectionné
  recepFournisseurSearch: '', // texte de recherche fournisseur
  recepFournisseurOpen: false, // dropdown ouvert
  recepFscTypeClaim: 'fsc_mix', // type certification lot (défaut FSC Mix)
  // Import référentiel références / unités
  importRefsOpen: false,
  importRefsPreview: null,
  importRefsLoading: false,
  importRefsApplying: false,
  // Matières premières
  matieres: null,
  matieresCat: 'tout',
  matieresQ: '',
  matieresCardMenuId: null,
  mpModal: null,
  addPfModalOpen: false,
  matieresAdminOpen: false,
  matieresAdminList: null,
  matieresAdminEditId: null,
  matieresAdminAddError: '',
  matieresAdminSaving: false,
  // Historique mouvements
  historique: [],
  historiqueFiltres: {
    type_stock: 'tout',
    categorie: '',
    type_mouvement: '',
    date_debut: '',
    date_fin: '',
  },
  historiqueLoading: false,
  historiqueFiltresOpen: false,
  historiquePage: 0,
  historiqueHasMore: false,
};

const HIST_PAGE_SIZE = 50;

const ROLE_LABELS = {
  direction:'Direction', administration:'Administration', fabrication:'Fabrication',
  logistique:'Logistique', comptabilite:'Comptabilité', expedition:'Expédition',
  commercial:'Commercial', superadmin:'Super admin',
};

// ── Fournisseurs FSC (chargés depuis la base via API) ──
let FOURNISSEURS_FSC = [
  { nom: 'Avery', licence: 'FSC-C004451', certificat: 'CU-COC-807907' },
  { nom: 'Fedrigoni', licence: 'FSC-C011937', certificat: 'FCBA-COC-000059' },
  { nom: 'Feys', licence: 'FSC-C017070', certificat: 'SGSCH-COC-004366' },
  { nom: 'Burgo / Mosaico', licence: 'FSC-C004657', certificat: 'SGSCH-COC-002122' },
  { nom: 'Foucherf', licence: 'FSC-C215283', certificat: 'BV-COC-215283' },
  { nom: 'Frimpeks UK', licence: 'FSC-C160714', certificat: 'INT-COC-002144' },
  { nom: 'Frimpeks Italy', licence: 'FSC-C164660', certificat: 'INT-COC-001611' },
  { nom: 'Frimpeks Turkey', licence: 'FSC-C129558', certificat: 'NEO-COC-129558' },
  { nom: 'Grand Ouest', licence: 'FSC-C148933', certificat: 'IMO-COC-209345' },
  { nom: 'Guyenne', licence: 'FSC-C114338', certificat: 'FCBA-COC-000352' },
  { nom: 'Itasa', licence: 'FSC-C160893', certificat: 'AEN-COC-000369' },
  { nom: 'Kanzan', licence: 'FSC-C007179', certificat: 'TUVDC-COC-100605' },
  { nom: 'Lefrancq', licence: 'FSC-C135176', certificat: 'FCBA-COC-000478' },
  { nom: 'Likexin', licence: 'FSC-C128270', certificat: 'ESTS-COC-242264' },
  { nom: 'Mitsubishi', licence: 'FSC-C014541', certificat: 'SGSCH-COC-002664' },
  { nom: 'Rheno', licence: 'FSC-C104291', certificat: 'CU-COC-815304' },
  { nom: 'Ricoh', licence: 'FSC-C001858', certificat: 'IMO-COC-261828' },
  { nom: 'Sato', licence: 'FSC-C207483', certificat: 'TUEV-COC-002274' },
  { nom: 'Shine', licence: 'FSC-C210420', certificat: 'ESTS-COC-241843' },
  { nom: 'Suzhou', licence: 'FSC-C140235', certificat: 'RR-COC-000252' },
  { nom: 'Techmay', licence: 'FSC-C199493', certificat: 'FCBA-COC-000616' },
  { nom: 'Torrespapel', licence: 'FSC-C011032', certificat: 'SGSCH-COC-003753' },
  { nom: 'UPM', licence: 'FSC-C012530', certificat: 'SGSCH-COC-004879' },
  { nom: 'Xinzhu', licence: 'FSC-C177953', certificat: 'SGSHK-COC-331526' },
];

async function loadFournisseursFSC() {
  try {
    const data = await api('/api/stock/fournisseurs');
    FOURNISSEURS_FSC = Array.isArray(data) ? data : [];
  } catch(e) { /* garder la liste précédente si erreur */ }
}

function fournisseurSuggestions(query) {
  if (!query) return [];
  const q = query.toLowerCase();
  return FOURNISSEURS_FSC
    .filter(f => f.nom.toLowerCase().includes(q))
    .sort((a, b) => {
      const aStarts = a.nom.toLowerCase().startsWith(q) ? 0 : 1;
      const bStarts = b.nom.toLowerCase().startsWith(q) ? 0 : 1;
      if (aStarts !== bStarts) return aStarts - bStarts;
      return a.nom.localeCompare(b.nom, 'fr');
    });
}

// ── API ─────────────────────────────────────────────────────────
async function api(p, o) {
  try {
    const r = await fetch(API + p, { credentials: 'include', ...o });
    if (r.status === 401) { window.location.href = '/'; return null; }
    if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || 'Erreur ' + r.status); }
    return await r.json();
  } catch(e) {
    if (e.message && e.message.includes('Failed to fetch')) throw new Error('API non disponible');
    throw e;
  }
}

async function apiUpload(path, formData) {
  const r = await fetch(API + path, { method: 'POST', credentials: 'include', body: formData });
  if (r.status === 401) { window.location.href = '/'; return null; }
  if (!r.ok) {
    const e = await r.json().catch(() => ({}));
    const detail = e.detail;
    throw new Error(typeof detail === 'string' ? detail : (detail?.msg || 'Erreur ' + r.status));
  }
  return await r.json();
}

async function downloadRefsExport() {
  try {
    const r = await fetch(API + '/api/stock/produits/export?format=csv', { credentials: 'include' });
    if (r.status === 401) { window.location.href = '/'; return; }
    if (!r.ok) throw new Error('Export impossible');
    const blob = await r.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'references_unites_vente.csv';
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 800);
    showToast('Export CSV téléchargé');
  } catch(e) {
    showToast(e.message || 'Export impossible', 'error');
  }
}

function printRefsExport() {
  window.open(API + '/api/stock/produits/export?format=print', '_blank', 'noopener');
}

function showToast(m, t='success') {
  S.toast = { message: m, type: t };
  renderToast();
  setTimeout(() => { S.toast = null; renderToast(); }, 3000);
}

// ── Helpers ─────────────────────────────────────────────────────
const fN = n => n != null ? Number(n).toLocaleString('fr-FR') : '0';
const fD = d => d ? d.slice(0,10).split('-').reverse().join('/') : '—';
const joursDepuis = d => { if (!d) return null; return Math.round((Date.now() - new Date(d).getTime()) / 86400000); };
// Singulier si 0 ou 1, pluriel (base + "s") si > 1
function fU(qty, unite) {
  const u = String(unite || '').trim();
  if (!u) return fN(qty);
  const n = parseFloat(qty) || 0;
  // Abréviation pour les unités longues
  const uLow = u.toLowerCase();
  if(uLow === 'étiquettes' || uLow === 'etiquettes' || uLow === 'étiquette' || uLow === 'etiquette'){
    return fN(n) + '\u00a0eti.';
  }
  return fN(n) + '\u00a0' + (Math.abs(n) > 1 ? u + 's' : u);
}
// ── Icons (Feather-ish, inline SVG) ─────────────────────────────
function icon(name, size=16){
  const a = `width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"`;
  const p = {
    'grid': '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>',
    'layers': '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
    'clock': '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    'clipboard': '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/>',
    'users': '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    'sun': '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>',
    'moon': '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>',
    'log-out': '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
    'menu': '<line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/>',
    'home': '<path d="M3 10.5L12 3l9 7.5"/><path d="M5 10v11h14V10"/><path d="M10 21v-6h4v6"/>',
    'refresh-ccw': '<polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-4.5"/>',
    'printer': '<polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/>',
    'package': '<line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/>',
    'briefcase': '<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/><line x1="12" y1="12" x2="12" y2="12"/>',
    'cpu': '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/>',
    'truck': '<rect x="1" y="3" width="15" height="13"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/>',
    'arrow-left': '<line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>',
    'settings': '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
    'tag': '<path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/>',
    'chevron-right': '<polyline points="9 18 15 12 9 6"/>',
    'atelier': '<path d="M2 20h20"/><path d="M4 20V10l8-6 8 6v10"/><path d="M9 20v-5h6v5"/><path d="M10 10h4"/><path d="M12 10v5"/>',
    'scan': '<rect x="3" y="3" width="5" height="5"/><rect x="16" y="3" width="5" height="5"/><rect x="3" y="16" width="5" height="5"/><line x1="21" y1="16" x2="21" y2="21"/><line x1="16" y1="21" x2="21" y2="21"/><line x1="11" y1="3" x2="11" y2="7"/><line x1="11" y1="11" x2="11" y2="17"/><line x1="3" y1="11" x2="7" y2="11"/><line x1="11" y1="11" x2="17" y2="11"/>',
    'inbox': '<polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>',
    'check-circle': '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
    'upload': '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>',
    'download': '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
    'edit': '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>',
    'plus-circle': '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/>',
    'mail': '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
  };
  return `<svg ${a} aria-hidden="true" style="display:inline-block;vertical-align:middle;flex-shrink:0">${p[name]||p['grid']}</svg>`;
}
function iconEl(name, size=16){
  const s = document.createElement('span');
  s.style.cssText = 'display:inline-flex;align-items:center;flex-shrink:0';
  s.innerHTML = icon(name, size);
  return s;
}

// ── DOM helper — safe contre null/false ─────────────────────────
function el(tag, attrs, ...children) {
  const e = document.createElement(tag);
  if (attrs) {
    const { cls, className, on, style: s, html, ...rest } = attrs;
    const cn = cls || className;
    if (cn) e.className = cn;
    if (on) Object.entries(on).forEach(([ev,fn]) => e.addEventListener(ev, fn));
    if (s && typeof s === 'object') Object.assign(e.style, s);
    if (html) { e.innerHTML = html; }
    Object.entries(rest).forEach(([k,v]) => {
      if (v === null || v === undefined || v === false) return;
      if (k === 'disabled' && v) { e.disabled = true; return; }
      e.setAttribute(k, v);
    });
  }
  children.flat(Infinity).forEach(c => {
    if (c == null || c === false || c === undefined) return;
    if (c instanceof Node) { e.appendChild(c); return; }
    if (typeof c === 'string' || typeof c === 'number') {
      e.appendChild(document.createTextNode(String(c)));
    }
  });
  return e;
}

// ── Loaders ─────────────────────────────────────────────────────
let searchTimer = null;
function doSearch(q) {
  S.searchQuery = q;
  clearTimeout(searchTimer);
  if (!q || q.length < 1) { S.searchResults = null; updateSearchResults(); return; }
  searchTimer = setTimeout(async () => {
    try {
      const r = await api('/api/stock/search?q=' + encodeURIComponent(q) + '&limit=8');
      S.searchResults = r;
    } catch(e) {}
    updateSearchResults();
  }, 220);
}

async function loadProduit(id) {
  try {
    const d = await api('/api/stock/produits/' + id);
    if (d) { S.selProduit = d; S.selEmpl = null; S.searchResults = null; clearSearch(); render(); }
  } catch(e) { showToast(e.message, 'error'); }
}

async function loadEmplacement(empl) {
  try {
    const d = await api('/api/stock/emplacements/' + encodeURIComponent(empl));
    if (d) { S.selEmpl = d; S.selProduit = null; S.searchResults = null; clearSearch(); render(); }
  } catch(e) { showToast(e.message, 'error'); }
}

function parseHistEmplacements(raw) {
  const s = String(raw || '').trim();
  if (!s) return [];
  if (s.includes('→')) {
    const parts = s.split('→').map(p => p.trim()).filter(Boolean);
    return parts.length ? parts : [s];
  }
  return [s];
}

async function openHistoriqueRef(m) {
  if (!m) return;
  if (m.type_stock === 'mp') {
    const ref = (m.reference || '').trim();
    if (m.matiere_id || ref) {
      S.matieresQ = ref;
      S.matieresCat = 'tout';
      goToTab('matieres');
    }
    return;
  }
  if (m.produit_id) {
    await loadProduit(m.produit_id);
    return;
  }
  const ref = (m.reference || '').trim();
  if (!ref) return;
  try {
    const r = await api('/api/stock/search?q=' + encodeURIComponent(ref) + '&limit=10');
    const p = (r && r.produits || []).find(x => (x.reference || '').toUpperCase() === ref.toUpperCase());
    if (p && p.id) await loadProduit(p.id);
    else showToast('Référence introuvable.', 'error');
  } catch (e) { showToast(e.message, 'error'); }
}

function stockHistRefLink(m, label) {
  const txt = label != null ? label : (m.reference || '—');
  const can = m.type_stock === 'mp'
    ? !!(m.matiere_id || (m.reference || '').trim())
    : !!(m.produit_id || (m.reference || '').trim());
  if (!can || txt === '—') return el('span', null, txt);
  return el('button', {
    cls: 'mvt-ref-link', type: 'button',
    on: { click: (e) => { e.stopPropagation(); openHistoriqueRef(m); } },
  }, txt);
}

function stockHistEmplLinks(raw) {
  const codes = parseHistEmplacements(raw);
  if (!codes.length) return el('span', { cls: 'hist-muted' }, '—');
  if (codes.length === 1) {
    return el('button', {
      cls: 'mvt-empl-link', type: 'button',
      on: { click: (e) => { e.stopPropagation(); loadEmplacement(codes[0]); } },
    }, codes[0]);
  }
  const wrap = el('span', { cls: 'hist-empl-chain' });
  codes.forEach((code, i) => {
    if (i) wrap.appendChild(el('span', { cls: 'hist-empl-sep' }, ' → '));
    wrap.appendChild(el('button', {
      cls: 'mvt-empl-link', type: 'button',
      on: { click: (e) => { e.stopPropagation(); loadEmplacement(code); } },
    }, code));
  });
  return wrap;
}

function stockHistMetaSep(parent) {
  if (parent.childNodes.length) parent.appendChild(el('span', { cls: 'hist-empl-sep' }, ' · '));
}

function stockHistMetaRow(m) {
  const empl = dashActEmplacement(m);
  const actor = (m.created_by_name || '').trim();
  const when = timeAgo(m.created_at);
  const meta = el('span', { cls: 'dash-act-meta' });
  if (empl) {
    meta.appendChild(stockHistEmplLinks(empl));
  }
  if (actor) {
    stockHistMetaSep(meta);
    meta.appendChild(el('span', null, actor));
  }
  if (when) {
    stockHistMetaSep(meta);
    meta.appendChild(el('span', null, when));
  }
  return meta.childNodes.length ? meta : null;
}

async function loadDashboard() {
  try {
    const [dash, activite] = await Promise.all([
      api('/api/stock/dashboard'),
      api('/api/stock/historique-mouvements?limit=10').catch(() => []),
    ]);
    if (dash) {
      S.dashboard = {
        ...dash,
        activiteRecente: Array.isArray(activite) ? activite : [],
      };
      renderContent();
    }
  } catch (e) {}
}

async function loadInventaireList() {
  try { const d = await api('/api/stock/inventaire/produits-a-inventorier'); if (d) { S.inventaireList = d; renderContent(); } } catch(e) {}
}

async function submitMouvement(body) {
  try {
    const r = await api('/api/stock/mouvement', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body) });
    if (!r) return;
    showToast('Stock mis à jour → ' + fN(r.quantite_apres));
    S.modalMvt = null;
    document.querySelector('.modal-overlay')?.remove();
    if (S.selProduit) await loadProduit(S.selProduit.produit.id);
    else if (S.selEmpl) await loadEmplacement(S.selEmpl.emplacement);
    else if (S.tab === 'dashboard') await loadDashboard();
    else if (S.tab === 'inventaire') await loadInventaireList();
  } catch(e) { showToast(e.message, 'error'); }
}

// Emplacements chargés depuis /api/stock/emplacements-list (plan + stock réel)
let _emplListFromDB = [];
const LS_STOCK_EMPL_CUSTOM = 'mysifa_stock_empl_custom';
const STOCK_UNITS_BASE = ['cartons','bobines','étiquettes','palettes','paravents','boîtes'];
const LS_STOCK_UNITS_CUSTOM = 'mysifa_stock_units_custom_v1';

async function fetchEmplacementsFromDB() {
  try {
    const r = await api('/api/stock/emplacements-list');
    if (r && Array.isArray(r.emplacements)) {
      _emplListFromDB = r.emplacements;
    }
  } catch(e) { _emplListFromDB = []; }
}

function loadPageEmplCustom() {
  try {
    const j = localStorage.getItem(LS_STOCK_EMPL_CUSTOM);
    const a = j ? JSON.parse(j) : [];
    if (!Array.isArray(a)) return [];
    return [...new Set(a.map(x => String(x || '').trim().toUpperCase()).filter(Boolean))];
  } catch(e) { return []; }
}
function savePageEmplCustom(arr) {
  try { localStorage.setItem(LS_STOCK_EMPL_CUSTOM, JSON.stringify([...new Set(arr)])); } catch(e) {}
}
function addPageCustomEmplacement(code) {
  const t = String(code || '').trim().toUpperCase();
  if (!isStockEmplacementCode(t)) return false;
  const cur = loadPageEmplCustom();
  if (cur.includes(t)) return false;
  cur.push(t); savePageEmplCustom(cur); return true;
}
function allPageEmplacementChoices() {
  return [...new Set([..._emplListFromDB, ...loadPageEmplCustom()])].sort();
}
function isStockEmplacementCode(s) {
  const t = String(s || '').trim().toUpperCase();
  if (t.length < 2) return false;
  const c0 = t.charCodeAt(0);
  if (c0 < 65 || c0 > 90) return false;
  for (let i = 1; i < t.length; i++) {
    const c = t.charCodeAt(i);
    if (c < 48 || c > 57) return false;
  }
  return true;
}
const ADD_PF_FIELD_IDS = {
  emplInput: 'dash-add-pf-empl-input',
  emplList: 'dash-add-pf-empl-suggestions',
  unitInput: 'dash-add-pf-unit-input',
  unitList: 'dash-add-pf-unit-suggestions',
};

function hideAddEmplDropdown(listId) {
  const list = document.getElementById(listId);
  if (list) list.style.display = 'none';
}
function refreshAddEmplDropdownInner(inputId, listId) {
  const input = document.getElementById(inputId);
  const list = document.getElementById(listId);
  if (!input || !list) return;
  const q = String(input.value || '').trim().toUpperCase();
  const all = allPageEmplacementChoices();
  let filtered = q ? all.filter(c => c.startsWith(q)) : all.slice();
  filtered = filtered.slice(0, 24);
  list.innerHTML = '';
  filtered.forEach(code => {
    const row = document.createElement('div');
    row.className = 'empl-suggest-item';
    row.textContent = code;
    row.addEventListener('mousedown', e => { e.preventDefault(); input.value = code; hideAddEmplDropdown(listId); });
    list.appendChild(row);
  });
  const addRow = document.createElement('div');
  addRow.className = 'empl-suggest-add';
  addRow.textContent = '+ Ajouter emplacement';
  addRow.addEventListener('mousedown', e => {
    e.preventDefault();
    const raw = String(input.value || '').trim().toUpperCase();
    if (!isStockEmplacementCode(raw)) {
      showToast('Format invalide : une lettre puis des chiffres (ex. Z999)', 'error');
      return;
    }
    if (addPageCustomEmplacement(raw)) showToast('Emplacement ajouté : ' + raw);
    else showToast('Emplacement déjà dans la liste', 'warn');
    input.value = raw;
    hideAddEmplDropdown(listId);
    refreshAddEmplDropdownInner(inputId, listId);
  });
  list.appendChild(addRow);
}
function wireAddEmplCombo(inputId, listId) {
  const input = document.getElementById(inputId);
  if (!input || input.dataset.wired === '1') return;
  input.dataset.wired = '1';
  const list = document.getElementById(listId);
  input.addEventListener('focus', () => {
    if (list) { list.style.display = 'block'; refreshAddEmplDropdownInner(inputId, listId); }
  });
  input.addEventListener('input', () => {
    if (list) { list.style.display = 'block'; refreshAddEmplDropdownInner(inputId, listId); }
  });
  input.addEventListener('blur', () => { setTimeout(() => hideAddEmplDropdown(listId), 200); });
}

function loadPageUnitCustom(){
  try{
    const j=localStorage.getItem(LS_STOCK_UNITS_CUSTOM);
    const a=j?JSON.parse(j):[];
    if(!Array.isArray(a)) return [];
    return a
      .map(x=>({
        label:String(x&&x.label||'').trim(),
        base:String(x&&x.base||'').trim().toLowerCase(),
        qty:Number(x&&x.qty),
      }))
      .filter(x=>x.label && STOCK_UNITS_BASE.includes(x.base) && isFinite(x.qty) && x.qty>0);
  }catch(e){ return []; }
}
function savePageUnitCustom(arr){
  try{ localStorage.setItem(LS_STOCK_UNITS_CUSTOM, JSON.stringify(arr)); }catch(e){}
}
function addPageCustomUnit(label, base, qty){
  const l=String(label||'').trim();
  const b=String(base||'').trim().toLowerCase();
  const q=Number(qty);
  if(!l) return {ok:false, reason:"Libellé obligatoire"};
  if(!STOCK_UNITS_BASE.includes(b)) return {ok:false, reason:"Base invalide"};
  if(!isFinite(q) || q<=0) return {ok:false, reason:"Quantité invalide"};
  const cur=loadPageUnitCustom();
  const key=l.toLowerCase();
  if(cur.some(x=>String(x.label||'').trim().toLowerCase()===key)){
    return {ok:false, reason:"Unité déjà existante"};
  }
  cur.push({label:l, base:b, qty:q});
  savePageUnitCustom(cur);
  return {ok:true};
}
function getUnitBase(label){
  const l=String(label||'').trim().toLowerCase();
  if(!l) return '';
  if(STOCK_UNITS_BASE.includes(l)) return l;
  const u=loadPageUnitCustom().find(x=>String(x.label||'').trim().toLowerCase()===l);
  return u ? u.base : l;
}
function allUnitLabels(){
  const custom=loadPageUnitCustom().map(x=>x.label);
  return [...new Set([...STOCK_UNITS_BASE, ...custom])];
}
function hideAddUnitDropdown(listId){
  const list=document.getElementById(listId);
  if(list) list.style.display='none';
}
function refreshAddUnitDropdownInner(inputId, listId){
  const input=document.getElementById(inputId);
  const list=document.getElementById(listId);
  if(!input || !list) return;
  const q=String(input.value||'').trim().toLowerCase();
  const all=allUnitLabels();
  let filtered=q ? all.filter(x=>String(x||'').toLowerCase().includes(q)) : all.slice();
  filtered = filtered.slice(0, 24);
  list.innerHTML='';
  filtered.forEach(lbl=>{
    const row=document.createElement('div');
    row.className='unit-suggest-item';
    row.textContent=lbl;
    row.addEventListener('mousedown', e=>{ e.preventDefault(); input.value=lbl; hideAddUnitDropdown(listId); });
    list.appendChild(row);
  });
  const addRow=document.createElement('div');
  addRow.className='unit-suggest-add';
  addRow.textContent='+ Autre (créer unité)';
  addRow.addEventListener('mousedown', e=>{
    e.preventDefault();
    S.unitModalOpen=true;
    S.unitNewLabel=String(input.value||'').trim();
    S.unitNewBase=STOCK_UNITS_BASE.includes(q)?q:'cartons';
    S.unitNewQty='';
    render();
  });
  list.appendChild(addRow);
}
function wireAddUnitCombo(inputId, listId){
  const input=document.getElementById(inputId);
  if(!input || input.dataset.wired==='1') return;
  input.dataset.wired='1';
  const list=document.getElementById(listId);
  input.addEventListener('focus', ()=>{
    if(list){ list.style.display='block'; refreshAddUnitDropdownInner(inputId, listId); }
  });
  input.addEventListener('input', ()=>{
    if(list){ list.style.display='block'; refreshAddUnitDropdownInner(inputId, listId); }
  });
  input.addEventListener('blur', ()=>{ setTimeout(()=>hideAddUnitDropdown(listId), 200); });
}

function _checkUnitQtyRange(unite, qte){
  const u=String(unite||'').trim().toLowerCase();
  const n=Number(qte);
  if(!u || !isFinite(n)) return null;
  const rules=[
    {u:'étiquettes',min:10000,max:10000000,label:'étiquettes'},
    {u:'bobines',min:10,max:2000,label:'bobines'},
    {u:'cartons',min:1,max:1000,label:'cartons'},
    {u:'palettes',min:1,max:3,label:'palettes'},
  ];
  const r=rules.find(x=>x.u===u);
  if(!r) return null;
  if(n<r.min || n>r.max){
    return `Alerte unité/quantité : pour ${r.label}, la quantité attendue est entre ${r.min} et ${r.max}.`;
  }
  return null;
}

async function createProduit(ref, commentaire, quantite, emplacement, uniteVente) {
  try {
    const empl = (emplacement || '').trim().toUpperCase();
    if (!empl || !isStockEmplacementCode(empl)) {
      showToast('Emplacement obligatoire (ex. A121)', 'error');
      return;
    }
    const qte = Number(typeof quantite === 'string' ? quantite.replace(',','.') : quantite);
    if (quantite === '' || quantite == null || Number.isNaN(qte) || qte <= 0) {
      showToast('Quantité obligatoire (nombre supérieur à 0)', 'error');
      return;
    }
    const unite = (uniteVente || '').trim();
    if(!unite){
      showToast("Unité de vente obligatoire", "error");
      return;
    }
    const base = getUnitBase(unite);
    const warn = _checkUnitQtyRange(base, qte);
    if(warn){
      const ok = confirm(warn + "\n\nVoulez-vous continuer quand même ?");
      if(!ok) return;
    }
    const body = { reference: ref, quantite: qte, unite };
    if (commentaire) body.commentaire = commentaire;
    const r = await api('/api/stock/produits', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body) });
    if (!r || r.id == null) return;
    await api('/api/stock/mouvement', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({
      produit_id: r.id, emplacement: empl, type_mouvement: 'entree', quantite: qte, note: commentaire || ''
    }) });
    const msg = r.existing
      ? ('Référence déjà en base — ' + fU(qte, unite) + ' ajoutée(s) en ' + empl)
      : ('Produit créé — ' + fU(qte, unite) + ' en ' + empl);
    showToast(msg);
    S.showAddForm = false;
    closeDashboardAddPfModal();
    await loadDashboard();
    renderContent();
  } catch(e) { showToast(e.message, 'error'); }
}

// ── Sidebar toggle ───────────────────────────────────────────────
function toggleSidebar() { S.sidebarOpen = !S.sidebarOpen; document.body.classList.toggle('sb-open', S.sidebarOpen); }
function closeSidebar() { S.sidebarOpen = false; document.body.classList.remove('sb-open'); }

// ── Navigation ──────────────────────────────────────────────────
function goToTab(tab) {
  // Fabrication : accès limité au traça
  if (S.tracaOnly && tab !== 'traca') return;
  // Arrêter la caméra si on quitte l'onglet réception
  if (tab !== 'reception' && S.recepScanning) recepStopCamera();
  S.tab = tab; S.selProduit = null; S.selEmpl = null; S.searchResults = null; S.showAddForm = false;
  if (tab !== 'dashboard') closeDashboardAddPfModal();
  if (tab !== 'traca') S.tracaPoste = null;
  clearSearch(); closeSidebar();
  if (tab === 'historique') S.historiqueLoading = true;
  updateNavActive();
  renderContent();
  if (tab === 'dashboard') loadDashboard();
  else if (tab === 'referentiel') loadDashboard();
  else if (tab === 'inventaire') loadInventaireList();
  else if (tab === 'reception') loadRecepHistory();
  else if (tab === 'matieres') loadMatieres();
  else if (tab === 'historique') loadHistorique();
}

function updateNavActive() {
  document.querySelectorAll('.nav-btn[data-tab]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === S.tab && !S.selProduit && !S.selEmpl);
  });
}

function clearSearch() {
  S.searchQuery = '';
  const inp = document.getElementById('main-search');
  if (inp) { inp.value = ''; }
  const res = document.getElementById('search-results-wrap');
  if (res) res.innerHTML = '';
}

// ── Micro ────────────────────────────────────────────────────────
function voiceFullTranscript(results) {
  let t = '';
  for (let i = 0; i < results.length; i++) t += results[i][0].transcript;
  return t;
}
function stockNormalizeVoiceTranscript(raw) {
  if (raw == null) return '';
  let s = String(raw).trim();
  if (!s) return '';
  s = s.normalize('NFD').replace(/\p{M}+/gu, '');
  s = s.replace(/\s+/g, ' ');
  s = s.replace(/\b(?:a|ah|ha|as)\s+(\d{2,4})\b/gi, 'A$1');
  s = s.replace(/\b([a-z])\s+(\d{2,4})\b/gi, (_, L, d) => L.toUpperCase() + d);
  s = s.replace(/\b([A-Z])\s+(\d{2,4})\b/g, '$1$2');
  return s.trim();
}
function stockVoiceSilenceStop(recog, ms) {
  const gap = ms || 3800;
  let iv = null, touched = Date.now();
  const touch = () => { touched = Date.now(); };
  const clearIv = () => { if (iv) { clearInterval(iv); iv = null; } };
  const start = () => {
    touch();
    clearIv();
    iv = setInterval(() => {
      if (Date.now() - touched >= gap) {
        clearIv();
        try { recog && recog.stop(); } catch (e) {}
      }
    }, 350);
  };
  const stop = () => { clearIv(); };
  return { start, stop, touch };
}
function tryStockVoiceCandidates(raw) {
  const base = String(raw || '').trim();
  const norm = stockNormalizeVoiceTranscript(base);
  const list = [];
  const add = x => { const t = String(x || '').trim(); if (t && !list.includes(t)) list.push(t); };
  add(norm);
  add(base);
  const cu = base.replace(/\s+/g, '').toUpperCase();
  const nu = norm.replace(/\s+/g, '').toUpperCase();
  if (cu) add(cu);
  if (nu && nu !== cu) add(nu);
  return list;
}
async function stockResolveVoiceSearchBestQuery(raw) {
  const cand = tryStockVoiceCandidates(raw);
  for (const q of cand) {
    if (q.length < 1) continue;
    try {
      const r = await api('/api/stock/search?q=' + encodeURIComponent(q) + '&limit=14');
      const empls = r && r.emplacements || [];
      const prods = r && r.produits || [];
      if (empls.length || prods.length) {
        const compact = q.replace(/\s+/g, '').toUpperCase();
        if (/^[A-Z]\d{2,4}$/.test(compact)) {
          const ex = empls.find(e => String(e.emplacement || '').replace(/\s+/g, '').toUpperCase() === compact);
          if (ex) return { q: ex.emplacement, r };
        }
        return { q, r };
      }
    } catch (e) {}
  }
  return { q: cand[0] || String(raw || '').trim(), r: null };
}
function startVoiceSearch() {
  if (location.protocol !== 'https:') { showToast('Micro disponible sur mysifa.com (HTTPS)', 'warn'); return; }
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { showToast('Micro non supporté', 'error'); return; }
  if (window.__mysifaPageVoiceRecog) {
    try { window.__mysifaPageVoiceRecog.stop(); } catch (e) {}
    window.__mysifaPageVoiceRecog = null;
  }
  const r = new SR();
  window.__mysifaPageVoiceRecog = r;
  r.lang = 'fr-FR';
  r.interimResults = true;
  const silence = stockVoiceSilenceStop(r, 3800);
  S.listening = true;
  const micBtn = document.getElementById('mic-btn');
  const iconSvg = (kind) => {
    const common = `fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"`;
    if (kind === 'dictaphone') {
      return `<svg viewBox="0 0 24 24" aria-hidden="true"><path ${common} d="M12 14a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v5a3 3 0 0 0 3 3z"/><path ${common} d="M19 11a7 7 0 0 1-14 0"/><path ${common} d="M12 18v3"/><path ${common} d="M8 21h8"/></svg>`;
    }
    if (kind === 'record') {
      return `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="5.5" fill="currentColor"/></svg>`;
    }
    return '';
  };
  if (micBtn) {
    micBtn.classList.add('listening', 'active');
    micBtn.innerHTML = iconSvg('record');
    micBtn.style.color = 'var(--danger)';
  }
  r.onresult = e => {
    silence.touch();
    const raw = voiceFullTranscript(e.results);
    const fixed = stockNormalizeVoiceTranscript(raw);
    const show = fixed || raw;
    const inp = document.getElementById('main-search');
    if (inp) { inp.value = show; }
    S.searchQuery = show;
    let hasFinal = false;
    for (let i = e.resultIndex; i < e.results.length; i++) {
      if (e.results[i].isFinal) { hasFinal = true; break; }
    }
    if (hasFinal) {
      (async () => {
        const { q } = await stockResolveVoiceSearchBestQuery(raw);
        const fi = document.getElementById('main-search');
        if (fi) fi.value = q;
        S.searchQuery = q;
        doSearch(q);
      })();
    }
  };
  const end = () => {
    silence.stop();
    window.__mysifaPageVoiceRecog = null;
    S.listening = false;
    if (micBtn) {
      micBtn.classList.remove('listening', 'active');
      micBtn.innerHTML = iconSvg('dictaphone');
      micBtn.style.color = '';
    }
  };
  r.onerror = end;
  r.onend = end;
  r.onstart = () => { silence.start(); };
  r.start();
}

// ── Caméra ───────────────────────────────────────────────────────
async function startCamera() {
  if (S.scanning) return;
  S.scanning = true;

  // Overlay créé en premier (synchrone) — le geste utilisateur est encore actif
  const overlay = el('div', { cls:'camera-modal' });
  const wrap = el('div', { cls:'camera-wrap' });
  const video = el('video', { cls:'camera-video', autoplay:'', playsinline:'' });
  const frame = el('div', { cls:'camera-frame' });
  wrap.append(video, frame);
  const hint = el('p', { cls:'camera-hint' }, 'Pointez vers un code-barres ou emplacement (ex: B211)');
  const resultEl = el('div', { cls:'camera-result' }, 'En attente…');
  const closeBtn = el('button', { cls:'btn-close-cam', on:{ click: () => stopCamera(overlay) } }, '✕ Fermer');
  overlay.append(wrap, hint, resultEl, closeBtn);
  document.body.appendChild(overlay);

  try {
    // getUserMedia est le PREMIER await — Android exige que la demande de permission
    // intervienne avant tout await long (ex: chargement CDN ZXing) pour que le dialog s'affiche
    if (!navigator.mediaDevices?.getUserMedia) throw new Error('Caméra non disponible (page non HTTPS ?)');
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
    S.cameraStream = stream;
    video.srcObject = stream;

    const useNativeDetector = isAndroid && ('BarcodeDetector' in window);

    // Délai de latence avant activation — évite les scans parasites au démarrage
    const SCAN_DELAY_MS = 1500;
    const scanStartTime = Date.now();
    resultEl.textContent = 'Positionnez-vous devant le code…';
    setTimeout(() => { if (S.scanning) resultEl.textContent = 'En attente…'; }, SCAN_DELAY_MS);

    // Arrêt immédiat dès détection — évite tout callback supplémentaire
    let searchDetected = false;
    const onSearchCode = (text) => {
      if (Date.now() - scanStartTime < SCAN_DELAY_MS) return;
      if (searchDetected) return;
      searchDetected = true;
      S.scanning = false;
      if (S.barcodeReader) { try { S.barcodeReader.reset(); } catch(e) {} S.barcodeReader = null; }
      if (S.cameraStream) { S.cameraStream.getTracks().forEach(t => t.stop()); S.cameraStream = null; }
      const upper = text.trim().toUpperCase();
      resultEl.textContent = '✅ ' + upper; resultEl.style.color = 'var(--success)';
      setTimeout(() => { overlay.remove(); handleScan(upper); }, 600);
    };

    // ZXing nécessaire sur iOS et pour QR codes sur Android
    if (typeof ZXing === 'undefined') {
      resultEl.textContent = 'Chargement scanner…';
      await new Promise((res, rej) => {
        const s = document.createElement('script');
        s.src = 'https://cdn.jsdelivr.net/npm/@zxing/library@0.19.1/umd/index.min.js';
        s.onload = res; s.onerror = rej; document.head.appendChild(s);
      });
      resultEl.textContent = 'En attente…';
    }

    if (useNativeDetector) {
      // Android : BarcodeDetector (codes 1D) + ZXing decodeFromStream (QR)
      const qrHints = new Map();
      qrHints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS, [ZXing.BarcodeFormat.QR_CODE]);
      qrHints.set(ZXing.DecodeHintType.TRY_HARDER, true);
      const qrReader = new ZXing.BrowserMultiFormatReader(qrHints);
      S.barcodeReader = qrReader;

      const detector = new BarcodeDetector({
        formats: ['code_128', 'ean_13', 'ean_8', 'data_matrix', 'code_39', 'upc_a', 'upc_e']
      });
      const barcodeLoop = async () => {
        if (!S.scanning) return;
        if (video.readyState < 2 || !video.videoWidth) { setTimeout(barcodeLoop, 100); return; }
        try {
          const found = await detector.detect(video);
          if (found.length > 0) { onSearchCode(found[0].rawValue); return; }
        } catch(e) {}
        if (S.scanning) setTimeout(barcodeLoop, 150);
      };
      setTimeout(barcodeLoop, 500);

      // ZXing decodeFromStream pour QR (seule méthode fiable sur Android pour les QR)
      qrReader.decodeFromStream(stream, video, (result) => {
        if (result) onSearchCode(result.getText());
      });
    } else {
      // iOS + fallback : ZXing canvas loop tous formats
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d', { willReadFrequently: true });
      const hints = new Map();
      hints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS, [ZXing.BarcodeFormat.CODE_128,ZXing.BarcodeFormat.EAN_13,ZXing.BarcodeFormat.QR_CODE]);
      hints.set(ZXing.DecodeHintType.TRY_HARDER, true);
      const reader = new ZXing.BrowserMultiFormatReader(hints);
      S.barcodeReader = reader;
      const loop = () => {
        if (!S.scanning) return;
        if (video.readyState < 2 || !video.videoWidth) { setTimeout(loop, 100); return; }
        try {
          canvas.width = video.videoWidth; canvas.height = video.videoHeight;
          ctx.drawImage(video, 0, 0);
          const img = ctx.getImageData(0, 0, canvas.width, canvas.height);
          const lum = new ZXing.RGBLuminanceSource(img.data, canvas.width, canvas.height);
          const bmp = new ZXing.BinaryBitmap(new ZXing.HybridBinarizer(lum));
          const result = reader.decode(bmp);
          if (result) { onSearchCode(result.getText()); return; }
        } catch(e) {}
        if (S.scanning) setTimeout(loop, 150);
      };
      setTimeout(loop, 400);
    }
  } catch(e) {
    showToast(e.message.includes('HTTPS') ? e.message : 'Accès caméra refusé', 'error');
    stopCamera(overlay);
  }
}

function stopCamera(overlay) {
  if (S.cameraStream) { S.cameraStream.getTracks().forEach(t => t.stop()); S.cameraStream = null; }
  if (S.barcodeReader) { try { S.barcodeReader.reset(); } catch(e) {} S.barcodeReader = null; }
  S.scanning = false; overlay?.remove();
}

function handleScan(text) {
  if (/^[A-N]\d{3}$/i.test(text)) loadEmplacement(text);
  else { const inp = document.getElementById('main-search'); if(inp) inp.value = text; doSearch(text); }
}

// ── Modal entrée depuis un emplacement ───────────────────────────
function openEmplEntreeModal(codeEmpl) {
  document.querySelector('.modal-overlay')?.remove();
  let _pid = null; // produit_id résolu après lookup

  const overlay = el('div', { cls:'modal-overlay', on:{ click: e => { if(e.target===overlay) overlay.remove(); }}});
  const sheet   = el('div', { cls:'modal-sheet' });
  sheet.addEventListener('click', e => e.stopPropagation());

  // Champ référence avec suggestions
  const refInp   = el('input', { cls:'field-input', type:'text', placeholder:'Référence existante (ex. 973/0019)', autocomplete:'off', style:{direction:'ltr'} });
  const suggWrap = el('div', { cls:'empl-suggestions' });
  const refError = el('div', { cls:'field-error', style:{color:'var(--danger)',fontSize:'12px',marginTop:'4px',display:'none'} });

  let refTimer = null;
  refInp.addEventListener('input', () => {
    _pid = null; refError.style.display = 'none';
    clearTimeout(refTimer);
    const q = refInp.value.trim();
    if (!q) { suggWrap.innerHTML = ''; suggWrap.style.display = 'none'; return; }
    refTimer = setTimeout(async () => {
      try {
        const r = await api('/api/stock/search?q=' + encodeURIComponent(q) + '&limit=6');
        const prods = (r && r.produits) || [];
        suggWrap.innerHTML = '';
        if (!prods.length) { suggWrap.style.display = 'none'; return; }
        prods.forEach(p => {
          const item = el('div', { cls:'empl-suggestion-item',
            on:{ click: () => {
              refInp.value = p.reference; _pid = p.id;
              refError.style.display = 'none';
              suggWrap.innerHTML = ''; suggWrap.style.display = 'none';
            }}
          }, el('span',{style:{fontWeight:'600',marginRight:'8px'}},p.reference), el('span',{style:{color:'var(--muted)',fontSize:'12px'}},p.designation||''));
          suggWrap.appendChild(item);
        });
        suggWrap.style.display = '';
      } catch(e) {}
    }, 200);
  });

  const qteInp  = el('input', { cls:'field-input', type:'number', placeholder:'0', min:'0', inputmode:'numeric', style:{direction:'ltr'} });
  const today   = new Date().toISOString().slice(0,10);
  const dateInp = el('input', { cls:'field-input', type:'date', value:today });
  const noteInp = el('input', { cls:'field-input', type:'text', placeholder:'Réf BL, lot…', style:{direction:'ltr'} });

  // ── Origine : Production / Sous-traitance ───────────────────────
  const prodDateInp2 = el('input', { cls:'field-input', type:'date', value:today, style:{direction:'ltr'} });
  const prodDateField2 = el('div', { cls:'modal-field', style:{display:'none', marginTop:'2px'} },
    el('label', { cls:'field-label' }, 'Date de production'),
    prodDateInp2
  );
  const prodCb2      = el('input', { type:'checkbox', id:'empl-prod-check' });
  const sousTraitCb2 = el('input', { type:'checkbox', id:'empl-strait-check' });
  prodCb2.addEventListener('change', () => {
    if (prodCb2.checked) { sousTraitCb2.checked = false; prodDateField2.style.display = ''; }
    else { prodDateField2.style.display = 'none'; }
  });
  sousTraitCb2.addEventListener('change', () => {
    if (sousTraitCb2.checked) { prodCb2.checked = false; prodDateField2.style.display = 'none'; }
  });
  const origineWrap2 = el('div', { cls:'modal-field' },
    el('label', { cls:'field-label' }, 'Origine'),
    el('div', { cls:'mvt-origin-group' },
      el('label', { cls:'mvt-origin-label' }, prodCb2, 'Production'),
      el('label', { cls:'mvt-origin-label' }, sousTraitCb2, 'Sous-traitance')
    ),
    prodDateField2
  );

  const confirmBtn = el('button', { cls:'btn-confirm entree', on:{ click: async () => {
    const ref  = refInp.value.trim().toUpperCase();
    const qte  = parseFloat(qteInp.value);
    const empl = codeEmpl;
    if (!ref) { showToast('Référence requise', 'error'); return; }
    if (!qte || qte <= 0) { showToast('Quantité requise', 'error'); return; }
    // Résolution produit_id si non connu via suggestion
    if (!_pid) {
      try {
        const r = await api('/api/stock/search?q=' + encodeURIComponent(ref) + '&limit=10');
        const match = (r && r.produits || []).find(p => p.reference.toUpperCase() === ref);
        if (!match) {
          refError.textContent = 'Référence produit non existante';
          refError.style.display = '';
          return;
        }
        _pid = match.id;
      } catch(e) { showToast(e.message, 'error'); return; }
    }
    let prefix = '';
    if (prodCb2.checked) {
      const dp = prodDateInp2.value ? prodDateInp2.value : '';
      prefix = dp ? 'Production | ' + dp : 'Production';
    } else if (sousTraitCb2.checked) {
      prefix = 'Sous-traitance';
    }
    const userNote = noteInp.value.trim();
    const finalNote = [prefix, userNote].filter(Boolean).join(' | ');
    await submitMouvement({ produit_id: _pid, emplacement: empl, type_mouvement:'entree', quantite: qte, date_entree: dateInp.value||today, note: finalNote });
    overlay.remove();
  }}}, '↓ Valider entrée');

  sheet.append(
    el('span',{cls:'modal-handle'}),
    el('div',{cls:'modal-title'},'↓ Entrée — '+codeEmpl),
    el('div',{cls:'modal-sub'},'Ajouter du stock à cet emplacement'),
    el('div',{cls:'modal-field'}, el('label',{cls:'field-label'},'Référence produit *'),
      el('div',{style:{position:'relative'}}, refInp, suggWrap), refError),
    el('div',{cls:'modal-field'}, el('label',{cls:'field-label'},'Quantité *'), qteInp),
    el('div',{cls:'modal-field'}, el('label',{cls:'field-label'},'Date du stock'), dateInp),
    origineWrap2,
    el('div',{cls:'modal-field'}, el('label',{cls:'field-label'},'Commentaire (optionnel)'), noteInp),
    el('div',{cls:'modal-actions'},
      el('button',{cls:'btn-cancel',on:{click:()=>overlay.remove()}},'Annuler'),
      confirmBtn
    )
  );
  overlay.appendChild(sheet);
  document.body.appendChild(overlay);
  setTimeout(()=>refInp.focus(), 80);
}

// ── Modal mouvement ──────────────────────────────────────────────
function openMvtModal(produit_id, ref, emplacement, type='entree') {
  S.modalMvt = { produit_id, ref, emplacement: emplacement || '' };
  S.modalType = type;
  S.emplSuggestions = [];
  document.querySelector('.modal-overlay')?.remove();
  document.body.appendChild(buildMvtModal());
}

let emplTimer = null;
let emplInpRef = null;
function searchEmplSugg(q, suggWrap) {
  clearTimeout(emplTimer);
  if (!q) { suggWrap.innerHTML = ''; return; }
  emplTimer = setTimeout(async () => {
    try {
      const r = await api('/api/stock/search?q=' + encodeURIComponent(q) + '&limit=6');
      const list = (r?.emplacements || []).map(e => e.emplacement);
      suggWrap.innerHTML = '';
      list.forEach(emp => {
        const item = el('div', { cls:'empl-sugg-item', on:{ click: () => {
          emplInpRef.value = emp;
          suggWrap.innerHTML = '';
        }}}, emp);
        suggWrap.appendChild(item);
      });
    } catch(e) {}
  }, 180);
}

function buildMvtModal() {
  const { produit_id, ref, emplacement } = S.modalMvt;
  const type = S.modalType;

  const overlay = el('div', { cls:'modal-overlay', on:{ click: e => { if(e.target===overlay){S.modalMvt=null;overlay.remove();} }}});
  const sheet = el('div', { cls:'modal-sheet' });
  sheet.addEventListener('click', e => e.stopPropagation());

  const typeBtns = el('div', { cls:'mvt-type-btns' },
    ...['entree','sortie','inventaire'].map(t => {
      const labels = {entree:'↓ Entrée', sortie:'↑ Sortie', inventaire:'= Inventaire'};
      const b = el('button', { cls:'mvt-type-btn'+(S.modalType===t?' sel-'+t:''), on:{ click: () => {
        S.modalType = t;
        overlay.remove();
        document.body.appendChild(buildMvtModal());
      }}}, labels[t]);
      return b;
    })
  );

  const emplInp = el('input', { cls:'field-input empl-upper', type:'text', placeholder:'Ex: a123, b211…', value: emplacement, style:{direction:'ltr'} });
  emplInpRef = emplInp;
  const suggWrap = el('div', { cls:'empl-suggestions' });
  emplInp.addEventListener('input', e => { emplInp.value = e.target.value.toUpperCase(); searchEmplSugg(emplInp.value, suggWrap); });

  const qteInp = el('input', { cls:'field-input', type:'number', placeholder:'0', min:'0', inputmode:'numeric', style:{direction:'ltr'} });

  const today = new Date().toISOString().slice(0,10);
  const dateInp = el('input', { cls:'field-input', type:'date', value:today });
  const dateField = el('div', { cls:'modal-field', style:{display: type==='sortie' ? 'none' : ''} }, el('label', { cls:'field-label' }, 'Date du stock'), dateInp);

  const noteInp = el('input', { cls:'field-input', type:'text', placeholder:'Réf BL, raison…', style:{direction:'ltr'} });

  // ── Origine : Production / Sous-traitance (entrée uniquement) ──
  let prodCheckbox = null, sousTraitCheckbox = null, prodDateInp = null;
  let origineWrap = null;
  if (type === 'entree') {
    prodDateInp = el('input', { cls:'field-input', type:'date', value:today, style:{direction:'ltr'} });
    const prodDateField = el('div', { cls:'modal-field', style:{display:'none', marginTop:'2px'} },
      el('label', { cls:'field-label' }, 'Date de production'),
      prodDateInp
    );

    prodCheckbox     = el('input', { type:'checkbox', id:'prod-check' });
    sousTraitCheckbox = el('input', { type:'checkbox', id:'strait-check' });

    prodCheckbox.addEventListener('change', () => {
      if (prodCheckbox.checked) { sousTraitCheckbox.checked = false; prodDateField.style.display = ''; }
      else { prodDateField.style.display = 'none'; }
    });
    sousTraitCheckbox.addEventListener('change', () => {
      if (sousTraitCheckbox.checked) { prodCheckbox.checked = false; prodDateField.style.display = 'none'; }
    });

    origineWrap = el('div', { cls:'modal-field' },
      el('label', { cls:'field-label' }, 'Origine'),
      el('div', { cls:'mvt-origin-group' },
        el('label', { cls:'mvt-origin-label' }, prodCheckbox, 'Production'),
        el('label', { cls:'mvt-origin-label' }, sousTraitCheckbox, 'Sous-traitance')
      ),
      prodDateField
    );
  }

  // ── Expédition (sortie uniquement) ──────────────────────────────
  let expCheckbox = null, expWrap = null;
  if (type === 'sortie') {
    expCheckbox = el('input', { type:'checkbox', id:'expedition-check' });
    expWrap = el('div', { cls:'modal-field' },
      el('label', { cls:'field-label' }, 'Livraison'),
      el('div', { cls:'mvt-origin-group' },
        el('label', { cls:'mvt-origin-label' }, expCheckbox, 'Expédition')
      )
    );
  }

  const confirmBtn = el('button', { cls:'btn-confirm '+type, on:{ click: async () => {
    const qte = parseFloat(qteInp.value);
    const empl = emplInp.value.trim().toUpperCase();
    if (!empl) { showToast('Emplacement requis','error'); return; }
    if (!qte||qte<=0) { showToast('Quantité requise','error'); return; }

    // Préfixe selon case cochée
    let prefix = '';
    if (type === 'entree') {
      if (prodCheckbox && prodCheckbox.checked) {
        const dp = prodDateInp && prodDateInp.value ? prodDateInp.value : '';
        prefix = dp ? 'Production | ' + dp : 'Production';
      } else if (sousTraitCheckbox && sousTraitCheckbox.checked) {
        prefix = 'Sous-traitance';
      }
    } else if (type === 'sortie' && expCheckbox && expCheckbox.checked) {
      prefix = 'Expédition';
    }
    const userNote = noteInp.value.trim();
    const finalNote = [prefix, userNote].filter(Boolean).join(' | ');

    await submitMouvement({ produit_id, emplacement:empl, type_mouvement:S.modalType, quantite:qte, date_entree:dateInp.value||today, note:finalNote });
  }}}, type==='entree'?'Valider entrée':type==='sortie'?'Valider sortie':'Valider inventaire');

  sheet.append(...[
    el('span',{cls:'modal-handle'}),
    el('div',{cls:'modal-title'}, '📦 '+ref),
    el('div',{cls:'modal-sub'}, 'Mouvement de stock'),
    typeBtns,
    el('div',{cls:'modal-field'}, el('label',{cls:'field-label'},'Emplacement'), emplInp, suggWrap),
    el('div',{cls:'modal-field'}, el('label',{cls:'field-label'},'Quantité'), qteInp),
    dateField,
    origineWrap,
    expWrap,
    el('div',{cls:'modal-field'}, el('label',{cls:'field-label'},'Commentaire (optionnel)'), noteInp),
    el('div',{cls:'modal-actions'},
      el('button',{cls:'btn-cancel', on:{click:()=>{S.modalMvt=null;overlay.remove();}}},'Annuler'),
      confirmBtn
    )
  ].filter(Boolean));
  overlay.appendChild(sheet);
  return overlay;
}

function buildSearchBar() {
  const wrap = el('div', { cls:'search-bar-wrap', id:'search-bar-wrap' });
  const row = el('div', { cls:'search-row' });

  const inp = el('input', {
    cls:'search-input', type:'text', id:'main-search',
    placeholder:'Rechercher…',
    style:{direction:'ltr'}
  });
  inp.addEventListener('input', e => doSearch(e.target.value));
  inp.addEventListener('keydown', e => { if (e.key === 'Escape') clearSearch(); });

  const iconSvg = (kind) => {
    const common = `fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"`;
    if (kind === 'dictaphone') {
      return `<svg viewBox="0 0 24 24" aria-hidden="true"><path ${common} d="M12 14a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v5a3 3 0 0 0 3 3z"/><path ${common} d="M19 11a7 7 0 0 1-14 0"/><path ${common} d="M12 18v3"/><path ${common} d="M8 21h8"/></svg>`;
    }
    if (kind === 'camera') {
      return `<svg viewBox="0 0 24 24" aria-hidden="true"><path ${common} d="M20 18a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3V9a3 3 0 0 1 3-3h1.2a2 2 0 0 0 1.6-.8l.6-.8A2 2 0 0 1 12.9 4h2.2a2 2 0 0 1 1.5.7l.6.7a2 2 0 0 0 1.6.8H17a3 3 0 0 1 3 3z"/><circle cx="12" cy="13" r="3.5" ${common}/><path ${common} d="M17.5 9.5h.01"/></svg>`;
    }
    if (kind === 'record') {
      return `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="5.5" fill="currentColor"/></svg>`;
    }
    return '';
  };

  const micBtn = el('button', { cls:'search-icon-btn', id:'mic-btn', on:{ click:startVoiceSearch } });
  micBtn.innerHTML = S.listening ? iconSvg('record') : iconSvg('dictaphone');
  if (S.listening) micBtn.style.color = 'var(--danger)';

  const camBtn = el('button', { cls:'search-icon-btn', id:'cam-btn', on:{ click:startCamera } });
  camBtn.innerHTML = iconSvg('camera');

  row.append(inp, micBtn, camBtn);
  wrap.appendChild(row);
  wrap.appendChild(el('div', { id:'search-results-wrap' }));
  return wrap;
}

function updateSearchResults() {
  let wrap = document.getElementById('search-results-wrap');
  if (!wrap) return;
  wrap.innerHTML = '';
  const q = S.searchQuery;
  const res = S.searchResults;
  if (!res || !q) return;
  const { produits=[], emplacements=[] } = res;
  if (!produits.length && !emplacements.length) {
    wrap.appendChild(el('div',{cls:'search-results'},el('div',{cls:'card-empty'},'Aucun résultat pour \"'+q+'\"')));
    return;
  }
  const box = el('div',{cls:'search-results'});
  if (produits.length) {
    box.appendChild(el('div',{cls:'search-section-title'},'📦 Produits'));
    produits.forEach(p => box.appendChild(
      el('div',{cls:'search-item',on:{click:()=>loadProduit(p.id)}},
        el('div',null,el('div',{cls:'si-ref'},p.reference),el('div',{cls:'si-des'},p.designation)),
        el('div',{cls:'si-badge'},fU(p.stock_total, p.unite))
      )
    ));
  }
  if (emplacements.length) {
    box.appendChild(el('div',{cls:'search-section-title'},'📍 Emplacements'));
    emplacements.forEach(e => box.appendChild(
      el('div',{cls:'search-item',on:{click:()=>loadEmplacement(e.emplacement)}},
        el('div',null,el('div',{cls:'si-ref'},e.emplacement),el('div',{cls:'si-des'},e.nb_refs+' référence'+(e.nb_refs>1?'s':''))),
        el('div',{cls:'si-badge'},fN(e.total_unites))
      )
    ));
  }
  wrap.appendChild(box);
}

function renderToast() {
  document.querySelector('.toast')?.remove();
  if (!S.toast) return;
  const t = el('div', { cls:'toast'+(S.toast.type!=='success'?' '+S.toast.type:'') }, S.toast.message);
  document.body.appendChild(t);
}

function buildMvtHistory(mouvements, unite='', opts=null) {
  return el('div',{cls:'card'},
    el('div',{cls:'card-header'},el('div',{cls:'card-title'},'🕐 Historique')),
    mouvements.length===0?el('div',{cls:'card-empty'},'Aucun mouvement'):
    el('div',null,...mouvements.slice(0,15).map(m=>{
      const icons={entree:'↓',sortie:'↑',inventaire:'='};
      const signe=m.type_mouvement==='entree'?'+':m.type_mouvement==='sortie'?'-':'=';
      const actor = (m.created_by_nom || m.created_by_name || '').trim();
      const unit = (m.unite || unite || '').trim();
      const refTxt = m.reference || m.emplacement || '';
      const primary = (opts && opts.primary) ? String(opts.primary) : '';
      return el('div',{cls:'mvt-row'},
        el('div',{cls:'mvt-icon '+m.type_mouvement},icons[m.type_mouvement]||'·'),
        el('div',{cls:'mvt-body'},
          el('div',{cls:'mvt-line1'},
            (primary === 'emplacement' && m.emplacement)
              ? el('button',{cls:'mvt-empl-link',type:'button',on:{click:()=>loadEmplacement(m.emplacement)}},m.emplacement)
              : ((m.produit_id && m.reference)
                ? el('button',{cls:'mvt-ref-link',type:'button',on:{click:()=>loadProduit(m.produit_id)}},refTxt)
                : el('span',null,refTxt)),
            el('span',{cls:'mvt-qte-'+m.type_mouvement},signe+fU(m.quantite, unit))
          ),
          el('div',{cls:'mvt-line2'},
            fD(m.created_at),
            (m.emplacement ? el('span',null,' · ') : null),
            (m.emplacement ? stockHistEmplLinks(m.emplacement) : null),
            (actor ? el('span',null,' · '+actor) : null),
          ),
          m.note?el('div',{cls:'mvt-note'},m.note):null
        )
      );
    }))
  );
}


function buildReferentielPage() {
  const s = (S.dashboard && S.dashboard.stats) ? S.dashboard.stats : {};
  return el('div', { cls: 'content ref-page' },
    el('div', { cls: 'ref-page-hero' },
      el('h2', { cls: 'ref-page-title' }, 'Références et unités de vente'),
      el('p', { cls: 'ref-page-desc' },
        'Gérez le référentiel des références produit et de leur unité de vente (import CSV ou Excel, export, impression).'
      ),
      (s.nb_refs != null) ? el('div', { cls: 'ref-stat-pill' },
        el('div', null,
          el('div', { cls: 'stat-label' }, 'Références en base'),
          el('div', { cls: 'stat-value accent' }, String(s.nb_refs || 0))
        )
      ) : null
    ),
    buildReferentielCard(),
    (!S.stockReadOnly) ? el('div', { cls: 'ref-card ref-units-card' },
      el('div', { cls: 'ref-card-header' },
        el('div', { cls: 'card-title' }, 'Unités de vente personnalisées')
      ),
      el('div', { cls: 'ref-card-body' },
        el('p', { cls: 'ref-card-desc' },
          'Créez une unité composite (ex. 500 cartons) utilisable lors de l\'ajout au stock.'
        ),
        el('button', {
          cls: 'btn-ghost-sm', type: 'button',
          on: { click: () => { S.unitModalOpen = true; S.unitNewLabel = ''; S.unitNewBase = 'cartons'; S.unitNewQty = ''; render(); } },
        }, iconEl('plus-circle', 14), ' Créer une unité de vente')
      )
    ) : null
  );
}

function buildReferentielCard() {
  const actions = el('div', { cls: 'ref-header-actions' });
  if (!S.stockReadOnly) {
    actions.appendChild(el('button', {
      cls: 'btn-ghost-sm', type: 'button',
      on: { click: () => { S.importRefsOpen = true; S.importRefsPreview = null; render(); } },
    }, iconEl('upload', 14), ' Importer'));
  }
  actions.appendChild(el('button', {
    cls: 'btn-ghost-sm', type: 'button', on: { click: downloadRefsExport },
  }, iconEl('download', 14), ' Exporter CSV'));
  actions.appendChild(el('button', {
    cls: 'btn-ghost-sm', type: 'button', on: { click: printRefsExport },
  }, iconEl('printer', 14), ' Imprimer'));

  return el('div', { cls: 'ref-card' },
    el('div', { cls: 'ref-card-header' },
      el('div', { cls: 'card-title' }, 'Références et unités de vente'),
      actions
    ),
    el('div', { cls: 'ref-card-body' },
      el('p', { cls: 'ref-card-desc' },
        'Importez ou exportez le référentiel des références produit et de leur unité de vente (CSV ou Excel).'
      )
    )
  );
}

async function previewRefsImport(file) {
  if (!file) return;
  S.importRefsLoading = true;
  render();
  try {
    const fd = new FormData();
    fd.append('file', file);
    const d = await apiUpload('/api/stock/produits/import/preview', fd);
    S.importRefsPreview = d;
    const st = d.stats || {};
    showToast((st.create || 0) + (st.update || 0) + ' ligne(s) à traiter');
  } catch(e) {
    S.importRefsPreview = null;
    showToast(e.message || 'Import impossible', 'error');
  } finally {
    S.importRefsLoading = false;
    render();
  }
}

async function confirmRefsImport() {
  const prev = S.importRefsPreview;
  if (!prev || !prev.rows) return;
  const rows = prev.rows.filter(r => r.action === 'create' || r.action === 'update');
  if (!rows.length) {
    showToast('Aucune ligne à importer', 'warn');
    return;
  }
  S.importRefsApplying = true;
  render();
  try {
    const d = await api('/api/stock/produits/import/confirm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rows }),
    });
    const a = d.applied || {};
    showToast(
      (a.create || 0) + ' créée(s), ' + (a.update || 0) + ' mise(s) à jour'
      + ((a.skipped || 0) ? ', ' + a.skipped + ' ignorée(s)' : '')
    );
    S.importRefsOpen = false;
    S.importRefsPreview = null;
    await loadDashboard();
  } catch(e) {
    showToast(e.message || 'Import impossible', 'error');
  } finally {
    S.importRefsApplying = false;
    render();
  }
}

function renderImportRefsModal() {
  const ov = el('div', { cls: 'contact-modal-overlay', on: {
    click: (e) => {
      if (e.target === ov && !S.importRefsApplying) {
        S.importRefsOpen = false;
        S.importRefsPreview = null;
        render();
      }
    },
  }});
  const box = el('div', { cls: 'contact-modal ref-import-modal', style: { maxWidth: '720px' } });
  const close = () => {
    if (S.importRefsApplying) return;
    S.importRefsOpen = false;
    S.importRefsPreview = null;
    render();
  };
  box.appendChild(el('button', { cls: 'contact-close', type: 'button', on: { click: close } }, '×'));
  box.appendChild(el('h3', null, 'Importer références et unités de vente'));

  if (!S.importRefsPreview) {
    const fileInp = el('input', { type: 'file', accept: '.csv,.xlsx,.xls,.xlsm', style: { display: 'none' } });
    const drop = el('div', { cls: 'ref-import-drop' },
      el('div', { cls: 'ref-import-drop-title' }, 'Glisser un fichier ici ou cliquer pour parcourir'),
      el('div', { cls: 'ref-import-drop-sub' }, 'CSV, Excel (.xlsx, .xls) — colonnes : référence, unité de vente, désignation (facultatif)')
    );
    drop.addEventListener('click', () => fileInp.click());
    drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('dragover'); });
    drop.addEventListener('dragleave', () => drop.classList.remove('dragover'));
    drop.addEventListener('drop', e => {
      e.preventDefault();
      drop.classList.remove('dragover');
      const f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (f) previewRefsImport(f);
    });
    fileInp.addEventListener('change', e => {
      const f = e.target.files && e.target.files[0];
      if (f) previewRefsImport(f);
    });
    box.appendChild(drop);
    box.appendChild(fileInp);
    if (S.importRefsLoading) {
      box.appendChild(el('div', { style: { marginTop: '12px', fontSize: '12px', color: 'var(--accent)' } }, 'Analyse du fichier…'));
    }
    const cancelOnly = el('div', { cls: 'contact-actions' });
    cancelOnly.appendChild(el('button', { cls: 'btn-cancel', type: 'button', on: { click: close } }, 'Fermer'));
    box.appendChild(cancelOnly);
  } else {
    const st = S.importRefsPreview.stats || {};
    box.appendChild(el('div', { style: { fontSize: '12px', color: 'var(--muted)', marginBottom: '10px' } },
      'Fichier : ' + (S.importRefsPreview.filename || '') + ' — '
      + (st.create || 0) + ' création(s), ' + (st.update || 0) + ' mise(s) à jour, '
      + (st.unchanged || 0) + ' inchangée(s), ' + (st.error || 0) + ' erreur(s)'
    ));
    const wrap = el('div', { cls: 'ref-import-table-wrap' });
    const table = el('table', { cls: 'ref-import-table' });
    const thead = el('thead', null, el('tr', null,
      el('th', null, 'Ligne'), el('th', null, 'Référence'), el('th', null, 'Unité'),
      el('th', null, 'Désignation'), el('th', null, 'Action')
    ));
    const tbody = el('tbody', null);
    (S.importRefsPreview.rows || []).forEach(r => {
      const badge = el('span', { cls: 'ref-import-badge ' + (r.action || 'error') }, r.action || 'error');
      tbody.appendChild(el('tr', null,
        el('td', null, String(r.line || '')),
        el('td', { style: { fontFamily: 'monospace', fontWeight: '700' } }, r.reference || '—'),
        el('td', null, r.unite || '—'),
        el('td', null, r.designation || '—'),
        el('td', null, badge, el('div', { style: { display: 'block', fontSize: '10px', color: 'var(--muted)', marginTop: '2px' } }, r.message || ''))
      ));
    });
    table.appendChild(thead);
    table.appendChild(tbody);
    wrap.appendChild(table);
    box.appendChild(wrap);
    const actions = el('div', { cls: 'contact-actions' });
    actions.appendChild(el('button', { cls: 'btn-cancel', type: 'button', on: { click: close } }, 'Annuler'));
    const nApply = (S.importRefsPreview.rows || []).filter(r => r.action === 'create' || r.action === 'update').length;
    const okBtn = el('button', { cls: 'btn', type: 'button' },
      S.importRefsApplying ? 'Import…' : ('Valider l\'import (' + nApply + ')'));
    okBtn.disabled = !!S.importRefsApplying || nApply === 0;
    okBtn.addEventListener('click', () => confirmRefsImport());
    actions.appendChild(okBtn);
    box.appendChild(actions);
  }

  ov.appendChild(box);
  document.body.appendChild(ov);
}

const MP_CAT_LABELS = { mandrin: 'Mandrin', palette: 'Palette', adhesif: 'Adhésif', carton: 'Carton' };

function mpCategorieKey(cat) {
  return String(cat || '').trim().toLowerCase();
}
function mpUniteNom(cat) {
  return mpCategorieKey(cat) === 'carton' ? 'unité' : 'palette';
}
function mpUniteShort(cat) {
  return mpCategorieKey(cat) === 'carton' ? 'u.' : 'pal.';
}
function mpQuantiteFieldLabel(cat) {
  return mpCategorieKey(cat) === 'carton' ? 'Quantité (unités)' : 'Quantité (palettes)';
}
function mpSeuilFieldLabel(cat) {
  return mpCategorieKey(cat) === 'carton' ? 'Seuil d\'alerte (u.)' : 'Seuil d\'alerte (pal.)';
}
function mpStockLine(qty, cat) {
  return fN(qty) + ' ' + mpUniteShort(cat);
}
function mpQuantiteInputAttrs(cat) {
  const carton = mpCategorieKey(cat) === 'carton';
  return { type: 'number', min: carton ? '1' : '0.5', step: carton ? '1' : '0.5' };
}
const MVT_TYPE_LABELS = {
  entree: 'Entrée', sortie: 'Sortie', ajustement: 'Ajustement',
  transfert: 'Transfert', inventaire: 'Inventaire',
};

function timeAgo(iso) {
  if (!iso) return '';
  const t = new Date(String(iso).replace(' ', 'T'));
  if (Number.isNaN(t.getTime())) return '';
  const now = new Date();
  const diffMs = now - t;
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 60) return 'il y a ' + Math.max(1, diffMin) + 'm';
  const diffH = Math.floor(diffMs / 3600000);
  if (diffH < 24) return 'il y a ' + diffH + 'h';
  const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startYesterday = new Date(startToday.getTime() - 86400000);
  if (t >= startYesterday && t < startToday) return 'hier';
  const dd = String(t.getDate()).padStart(2, '0');
  const mm = String(t.getMonth() + 1).padStart(2, '0');
  return dd + '/' + mm;
}

const MP_MVT_TITLES = {
  entree: 'Entrée en stock',
  sortie: 'Sortie de stock',
  ajustement: 'Ajustement d\'inventaire',
  transfert: 'Transfert',
};
const MP_PILL_CATS = [
  { id: 'tout', label: 'Tout' },
  { id: 'mandrin', label: 'Mandrins' },
  { id: 'palette', label: 'Palettes' },
  { id: 'adhesif', label: 'Adhésifs' },
  { id: 'carton', label: 'Cartons' },
];

function isMatieresAdmin() {
  return S.user && ['superadmin', 'direction', 'administration'].includes(S.user.role);
}

function closeMroot() {
  const m = document.getElementById('mroot');
  if (m) m.innerHTML = '';
  S.mpModal = null;
  S.addPfModalOpen = false;
}

function closeDashboardAddPfModal() {
  closeMroot();
}

function openDashboardAddPfModal() {
  S.addPfModalOpen = true;
  renderDashboardAddPfModal();
}

function filterMatieresList() {
  const list = S.matieres || [];
  const cat = S.matieresCat || 'tout';
  const q = (S.matieresQ || '').trim().toLowerCase();
  return list.filter(m => {
    if (cat !== 'tout' && m.categorie !== cat) return false;
    if (!q) return true;
    const ref = (m.reference || '').toLowerCase();
    const des = (m.designation || '').toLowerCase();
    return ref.includes(q) || des.includes(q);
  });
}

async function loadMatieres() {
  try {
    const d = await api('/api/stock/matieres');
    S.matieres = Array.isArray(d) ? d : [];
  } catch (e) {
    S.matieres = [];
    showToast(e.message, 'error');
  }
  renderMatieresView();
}

function renderMatieresView() {
  if (S.tab !== 'matieres') return;
  const ae = document.activeElement;
  const focusId = ae?.id;
  const caretStart = ae?.selectionStart;
  const caretEnd = ae?.selectionEnd;
  const area = document.getElementById('scroll-area');
  if (!area) return;
  area.innerHTML = '';
  const content = buildMatieres();
  if (content) area.appendChild(content);
  if (focusId) {
    const el = document.getElementById(focusId);
    if (el) {
      el.focus();
      if (caretStart != null) {
        try { el.setSelectionRange(caretStart, caretEnd); } catch (e) {}
      }
    }
  }
}

function matieresCardActions(m) {
  if (S.stockReadOnly) return null;
  const mk = (lbl, cls, type) => el('button', {
    cls: 'mp-act-btn ' + cls,
    type: 'button',
    on: { click: (e) => { e.stopPropagation(); S.matieresCardMenuId = null; openModalMouvement(type, m); } },
  }, lbl);
  const desktop = el('div', { cls: 'mp-card-actions-desktop' },
    mk('Entrée', 'mp-act-entree', 'entree'),
    mk('Sortie', 'mp-act-sortie', 'sortie'),
    mk('Ajust.', 'mp-act-ajust', 'ajustement'),
    mk('Transfert', 'mp-act-transf', 'transfert'),
  );
  const mobileWrap = el('div', { cls: 'mp-card-actions-mobile' });
  const menuBtn = el('button', {
    cls: 'mp-menu-btn',
    type: 'button',
    on: { click: (e) => {
      e.stopPropagation();
      S.matieresCardMenuId = S.matieresCardMenuId === m.id ? null : m.id;
      renderMatieresView();
    } },
  }, '···');
  mobileWrap.appendChild(menuBtn);
  if (S.matieresCardMenuId === m.id) {
    const drop = el('div', { cls: 'mp-menu-drop' },
      mk('Entrée', 'mp-act-entree', 'entree'),
      mk('Sortie', 'mp-act-sortie', 'sortie'),
      mk('Ajust.', 'mp-act-ajust', 'ajustement'),
      mk('Transfert', 'mp-act-transf', 'transfert'),
    );
    mobileWrap.appendChild(drop);
  }
  return el('div', { cls: 'mp-card-actions' }, desktop, mobileWrap);
}

function buildMatieres() {
  if (S.matieres === null) {
    return el('div', { cls: 'content' }, el('div', { cls: 'hist-page' },
      el('div', { cls: 'card-empty' }, 'Chargement…')));
  }
  const filtered = filterMatieresList();
  const q = (S.matieresQ || '').trim();
  const head = el('div', { cls: 'hist-head' },
    el('div', null,
      el('h2', { cls: 'hist-title' }, 'Matières premières'),
      el('p', { cls: 'hist-subtitle' },
        'Mandrins, palettes, adhésifs et cartons — entrées et sorties par emplacement'),
    ),
    isMatieresAdmin()
      ? el('div', { cls: 'hist-head-actions' },
          el('button', {
            cls: 'btn btn-ghost',
            type: 'button',
            on: { click: () => openMatieresAdminDrawer() },
          }, 'Gérer les références'),
        )
      : null,
  );
  const pills = el('div', { cls: 'mp-pills' },
    ...MP_PILL_CATS.map(p => el('button', {
      cls: 'mp-pill' + (S.matieresCat === p.id ? ' active' : ''),
      type: 'button',
      on: { click: () => { S.matieresCat = p.id; renderMatieresView(); } },
    }, p.label)),
  );
  const searchInp = el('input', {
    cls: 'mp-search',
    id: 'matieres-search',
    attrs: {
      type: 'text',
      placeholder: 'Rechercher (référence, désignation…)',
      autocomplete: 'off',
    },
  });
  searchInp.value = S.matieresQ || '';
  searchInp.addEventListener('input', (e) => {
    S.matieresQ = e.target.value;
    renderMatieresView();
  });
  searchInp.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      S.matieresQ = '';
      renderMatieresView();
    }
  });
  const list = el('div', { cls: 'mp-list' });
  if (!filtered.length) {
    list.appendChild(el('div', { cls: 'mp-empty' },
      q
        ? 'Aucune matière correspondant à « ' + q + ' ».'
        : 'Aucune matière dans cette catégorie.',
    ));
  } else {
    filtered.forEach(m => {
      const seuil = parseFloat(m.seuil_alerte) || 0;
      list.appendChild(el('div', { cls: 'mp-card' },
        el('div', { cls: 'mp-card-top' },
          dashMpCatBadge(m.categorie),
          el('span', { cls: 'mp-card-ref' }, m.reference || ''),
          el('span', { cls: 'mp-card-stock' }, mpStockLine(m.quantite, m.categorie)),
        ),
        el('div', { cls: 'mp-card-des' }, m.designation || ''),
        m.en_alerte
          ? el('div', { cls: 'mp-card-warn' }, 'Sous le seuil (min. ' + mpStockLine(seuil, m.categorie) + ')')
          : null,
        matieresCardActions(m),
      ));
    });
  }
  return el('div', { cls: 'content' },
    el('div', { cls: 'hist-page' }, head, pills,
      el('div', { cls: 'mp-search-wrap' }, searchInp), list));
}

function buildMpEmplacementField() {
  const emplInp = el('input', {
    cls: 'field-input empl-upper',
    attrs: { type: 'text', placeholder: 'Ex: A123, B211…', autocomplete: 'off' },
    style: { direction: 'ltr' },
  });
  const suggWrap = el('div', { cls: 'empl-suggestions' });
  emplInp.addEventListener('input', e => {
    emplInp.value = e.target.value.toUpperCase();
    searchEmplSugg(emplInp.value, suggWrap);
  });
  const wrap = el('div', { cls: 'mp-field' },
    el('label', null, 'Emplacement'),
    emplInp,
    suggWrap,
  );
  return { wrap, emplInp };
}

function mpEmplacementValue(emplInp) {
  return String(emplInp?.value || '').trim().toUpperCase();
}

function validateMpEmplacement(empl) {
  if (!empl) return 'Emplacement obligatoire.';
  if (!isStockEmplacementCode(empl)) return 'Format invalide — une lettre puis des chiffres (ex. A123).';
  return null;
}

function openModalMouvement(type, matiere) {
  (async () => {
    if (!S.matieres) {
      try {
        const d = await api('/api/stock/matieres');
        S.matieres = Array.isArray(d) ? d : [];
      } catch (e) {
        S.matieres = [];
      }
    }
    renderMpMouvementModal(type, matiere);
  })();
}

function renderMpMouvementModal(type, matiere) {
  const typeMvt = (type || 'entree').toLowerCase();
  const list = (S.matieres || []).filter(m => m.actif !== 0);
  let mat = matiere || null;
  if (!mat && list.length === 1) mat = list[0];
  closeMroot();
  const mroot = document.getElementById('mroot');
  if (!mroot) return;
  S.mpModal = { type: typeMvt, matiere: mat, matiereId: mat ? mat.id : null };
  const stockActuel = mat ? (parseFloat(mat.quantite) || 0) : 0;
  const mpCat = mat ? mat.categorie : (list.find(x => x.id === S.mpModal.matiereId)?.categorie || '');

  const overlay = el('div', {
    cls: 'mp-modal-overlay',
    on: { click: (e) => { if (e.target === overlay) closeMroot(); } },
  });
  const box = el('div', { cls: 'mp-modal' });
  box.appendChild(el('h3', null, MP_MVT_TITLES[typeMvt] || typeMvt));

  if (mat) {
    box.appendChild(el('div', { cls: 'mp-field' },
      el('label', null, 'Matière'),
      el('div', { cls: 'mp-readonly' }, (mat.reference || '') + ' — ' + (mat.designation || '')),
    ));
  } else {
    const sel = el('select', { id: 'mp-modal-matiere-select' });
    sel.appendChild(el('option', { value: '' }, '— Choisir une matière —'));
    list.forEach(item => {
      sel.appendChild(el('option', {
        value: String(item.id),
        selected: S.mpModal.matiereId === item.id ? true : null,
      }, item.reference + ' — ' + item.designation));
    });
    sel.addEventListener('change', () => {
      const id = parseInt(sel.value, 10);
      const found = list.find(x => x.id === id);
      renderMpMouvementModal(typeMvt, found || null);
    });
    box.appendChild(el('div', { cls: 'mp-field' }, el('label', null, 'Matière'), sel));
  }

  box.appendChild(el('div', { cls: 'mp-field' },
    el('label', null, 'Type de mouvement'),
    el('div', { cls: 'mp-readonly' }, MP_MVT_TITLES[typeMvt] || typeMvt),
  ));

  const hintEl = el('div', { cls: 'mp-hint' }, '');
  const errEl = el('div', { cls: 'mp-hint err', style: { display: 'none' } }, '');

  if (typeMvt === 'entree') {
    const { wrap: emplWrap, emplInp } = buildMpEmplacementField();
    const blInp = el('input', { attrs: { type: 'text', placeholder: 'BL-2024-001' } });
    const qInp = el('input', { attrs: mpQuantiteInputAttrs(mpCat) });
    box.appendChild(emplWrap);
    box.appendChild(el('div', { cls: 'mp-field' },
      el('label', null, 'Référence BL / Fournisseur'),
      blInp,
    ));
    box.appendChild(el('div', { cls: 'mp-field' },
      el('label', null, mpQuantiteFieldLabel(mpCat)),
      qInp,
    ));
    S.mpModal.getBody = () => ({
      matiere_id: S.mpModal.matiereId,
      type_mouvement: 'entree',
      quantite: parseFloat(qInp.value),
      ref_bl: (blInp.value || '').trim() || null,
      note: null,
      emplacement_source: null,
      emplacement_dest: mpEmplacementValue(emplInp) || null,
    });
    S.mpModal.validate = () => {
      const q = parseFloat(qInp.value);
      if (!S.mpModal.matiereId) return 'Matière obligatoire.';
      const emplErr = validateMpEmplacement(mpEmplacementValue(emplInp));
      if (emplErr) return emplErr;
      if (!q || q <= 0) return 'Quantité invalide.';
      return null;
    };
  } else if (typeMvt === 'sortie') {
    const { wrap: emplWrap, emplInp } = buildMpEmplacementField();
    hintEl.textContent = 'Stock actuel : ' + mpStockLine(stockActuel, mpCat);
    const qInp = el('input', { attrs: mpQuantiteInputAttrs(mpCat) });
    const checkQ = () => {
      const q = parseFloat(qInp.value);
      if (q > stockActuel) {
        errEl.style.display = '';
        errEl.textContent = 'Stock insuffisant.';
      } else {
        errEl.style.display = 'none';
      }
    };
    qInp.addEventListener('input', checkQ);
    box.appendChild(emplWrap);
    box.appendChild(el('div', { cls: 'mp-field' },
      el('label', null, mpQuantiteFieldLabel(mpCat)),
      qInp,
      hintEl,
      errEl,
    ));
    S.mpModal.getBody = () => ({
      matiere_id: S.mpModal.matiereId,
      type_mouvement: 'sortie',
      quantite: parseFloat(qInp.value),
      ref_bl: null,
      note: null,
      emplacement_source: mpEmplacementValue(emplInp) || null,
      emplacement_dest: null,
    });
    S.mpModal.validate = () => {
      const q = parseFloat(qInp.value);
      if (!S.mpModal.matiereId) return 'Matière obligatoire.';
      const emplErr = validateMpEmplacement(mpEmplacementValue(emplInp));
      if (emplErr) return emplErr;
      if (!q || q <= 0) return 'Quantité invalide.';
      if (q > stockActuel) return 'Stock insuffisant.';
      return null;
    };
  } else if (typeMvt === 'ajustement') {
    hintEl.textContent = 'Stock actuel : ' + mpStockLine(stockActuel, mpCat);
    const qInp = el('input', { attrs: { type: 'number', min: '0', step: mpCategorieKey(mpCat) === 'carton' ? '1' : '0.5' } });
    box.appendChild(el('div', { cls: 'mp-field' },
      hintEl,
      el('label', null, 'Nouveau stock (' + (mpCategorieKey(mpCat) === 'carton' ? 'unités' : 'palettes') + ')'),
      qInp,
    ));
    S.mpModal.getBody = () => ({
      matiere_id: S.mpModal.matiereId,
      type_mouvement: 'ajustement',
      quantite: parseFloat(qInp.value),
      ref_bl: null,
      note: null,
      emplacement_source: null,
      emplacement_dest: null,
    });
    S.mpModal.validate = () => {
      const q = parseFloat(qInp.value);
      if (!S.mpModal.matiereId) return 'Matière obligatoire.';
      if (Number.isNaN(q) || q < 0) return 'Quantité invalide.';
      return null;
    };
  } else if (typeMvt === 'transfert') {
    const qInp = el('input', { attrs: mpQuantiteInputAttrs(mpCat) });
    const srcInp = el('input', { attrs: { type: 'text' } });
    const dstInp = el('input', { attrs: { type: 'text' } });
    box.appendChild(el('div', { cls: 'mp-field' }, el('label', null, mpQuantiteFieldLabel(mpCat)), qInp));
    box.appendChild(el('div', { cls: 'mp-field' }, el('label', null, 'Emplacement source'), srcInp));
    box.appendChild(el('div', { cls: 'mp-field' }, el('label', null, 'Emplacement destination'), dstInp));
    S.mpModal.getBody = () => ({
      matiere_id: S.mpModal.matiereId,
      type_mouvement: 'transfert',
      quantite: parseFloat(qInp.value),
      ref_bl: null,
      note: null,
      emplacement_source: (srcInp.value || '').trim() || null,
      emplacement_dest: (dstInp.value || '').trim() || null,
    });
    S.mpModal.validate = () => {
      const q = parseFloat(qInp.value);
      if (!S.mpModal.matiereId) return 'Matière obligatoire.';
      if (!q || q <= 0) return 'Quantité invalide.';
      return null;
    };
  }

  const noteTa = el('textarea', { attrs: { placeholder: 'Commentaire (optionnel)' } });
  box.appendChild(el('div', { cls: 'mp-field' }, el('label', null, 'Note'), noteTa));
  const prevGetBody = S.mpModal.getBody;
  if (prevGetBody) {
    S.mpModal.getBody = () => {
      const b = prevGetBody();
      b.note = (noteTa.value || '').trim() || null;
      return b;
    };
  } else {
    S.mpModal.getBody = () => ({
      matiere_id: S.mpModal.matiereId,
      type_mouvement: typeMvt,
      quantite: 0,
      ref_bl: null,
      note: (noteTa.value || '').trim() || null,
      emplacement_source: null,
      emplacement_dest: null,
    });
    S.mpModal.validate = () => 'Type de mouvement non reconnu.';
  }

  const actions = el('div', { cls: 'mp-modal-actions' },
    el('button', { cls: 'btn-cancel', type: 'button', on: { click: closeMroot } }, 'Annuler'),
    el('button', { cls: 'btn', type: 'button', on: { click: submitMpMouvement } }, 'Valider'),
  );
  box.appendChild(actions);
  overlay.appendChild(box);
  mroot.appendChild(overlay);
}

async function submitMpMouvement() {
  if (!S.mpModal) return;
  const err = S.mpModal.validate ? S.mpModal.validate() : null;
  if (err) { showToast(err, 'error'); return; }
  const body = S.mpModal.getBody();
  try {
    const res = await api('/api/stock/matieres/mouvement', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (res && res.ok) {
      closeMroot();
      showToast('Mouvement enregistré.', 'success');
      await loadMatieres();
      if (S.tab === 'dashboard') await loadDashboard();
    }
  } catch (e) {
    showToast(e.message || 'Erreur lors de l\'enregistrement.', 'error');
  }
}

async function loadMatieresAdminList() {
  try {
    const d = await api('/api/stock/matieres?all=1');
    S.matieresAdminList = Array.isArray(d) ? d : [];
  } catch (e) {
    S.matieresAdminList = [];
    showToast(e.message, 'error');
  }
}

async function openMatieresAdminDrawer() {
  if (!isMatieresAdmin()) return;
  S.matieresAdminOpen = true;
  S.matieresAdminEditId = null;
  S.matieresAdminAddError = '';
  await loadMatieresAdminList();
  renderMatieresAdminDrawer();
}

function closeMatieresAdminDrawer() {
  S.matieresAdminOpen = false;
  S.matieresAdminEditId = null;
  closeMroot();
}

function renderMatieresAdminDrawer() {
  closeMroot();
  if (!S.matieresAdminOpen) return;
  const mroot = document.getElementById('mroot');
  if (!mroot) return;
  const overlay = el('div', {
    cls: 'mp-drawer-overlay',
    on: { click: (e) => { if (e.target === overlay) closeMatieresAdminDrawer(); } },
  });
  const drawer = el('div', { cls: 'mp-drawer', on: { click: (e) => e.stopPropagation() } });
  drawer.appendChild(el('div', { cls: 'mp-drawer-head' },
    el('h3', { style: { margin: 0, fontSize: '16px' } }, 'Références matières premières'),
    el('button', { cls: 'btn-cancel', type: 'button', on: { click: closeMatieresAdminDrawer } }, '×'),
  ));
  const body = el('div', { cls: 'mp-drawer-body' });
  const list = S.matieresAdminList || [];
  const byCat = {};
  list.forEach(item => {
    const c = item.categorie || 'autre';
    if (!byCat[c]) byCat[c] = [];
    byCat[c].push(item);
  });
  ['mandrin', 'palette', 'adhesif', 'carton'].forEach(cat => {
    if (!byCat[cat] || !byCat[cat].length) return;
    body.appendChild(el('div', { style: { fontSize: '11px', fontWeight: '600', color: 'var(--muted)', margin: '12px 0 8px', textTransform: 'uppercase' } },
      MP_CAT_LABELS[cat] || cat));
    byCat[cat].forEach(item => {
      body.appendChild(buildMatieresAdminRow(item));
    });
  });
  drawer.appendChild(body);
  drawer.appendChild(buildMatieresAdminAddForm());
  overlay.appendChild(drawer);
  mroot.appendChild(overlay);
}

function buildMatieresAdminRow(item) {
  const row = el('div', { cls: 'mp-admin-row' });
  const actif = item.actif !== 0;
  row.appendChild(el('div', { style: { display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' } },
    dashMpCatBadge(item.categorie),
    el('strong', null, item.reference || ''),
    el('span', { style: { color: 'var(--text2)', fontSize: '13px' } }, item.designation || ''),
    el('span', { style: { fontSize: '12px', color: 'var(--muted)' } }, 'Seuil ' + mpStockLine(item.seuil_alerte, item.categorie)),
    el('span', { style: { fontSize: '11px', fontWeight: '600', color: actif ? 'var(--success)' : 'var(--muted)' } },
      actif ? 'Actif' : 'Inactif'),
  ));
  const actions = el('div', { cls: 'mp-admin-actions' },
    el('button', {
      cls: 'btn-ghost',
      type: 'button',
      on: { click: () => {
        S.matieresAdminEditId = S.matieresAdminEditId === item.id ? null : item.id;
        renderMatieresAdminDrawer();
      } },
    }, S.matieresAdminEditId === item.id ? 'Fermer' : 'Modifier'),
    el('button', {
      cls: 'btn-ghost',
      type: 'button',
      on: { click: () => toggleMatieresActif(item) },
    }, actif ? 'Désactiver' : 'Réactiver'),
  );
  row.appendChild(actions);
  if (S.matieresAdminEditId === item.id) {
    row.appendChild(buildMatieresAdminEditForm(item));
  }
  return row;
}

function buildMatieresAdminEditForm(item) {
  const desInp = el('input', { attrs: { type: 'text' } });
  desInp.value = item.designation || '';
  const seuilInp = el('input', { attrs: { type: 'number', min: '0', step: '0.5' } });
  seuilInp.value = String(item.seuil_alerte ?? 0);
  const wrap = el('div', { cls: 'mp-admin-edit' },
    el('div', { cls: 'mp-field' }, el('label', null, 'Désignation'), desInp),
    el('div', { cls: 'mp-field' }, el('label', null, mpSeuilFieldLabel(item.categorie)), seuilInp),
    el('button', {
      cls: 'btn',
      type: 'button',
      on: { click: async () => {
        try {
          await api('/api/stock/matieres/' + item.id, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              designation: desInp.value.trim(),
              seuil_alerte: parseFloat(seuilInp.value) || 0,
            }),
          });
          showToast('Référence mise à jour.', 'success');
          S.matieresAdminEditId = null;
          await loadMatieresAdminList();
          await loadMatieres();
          renderMatieresAdminDrawer();
        } catch (e) {
          showToast(e.message, 'error');
        }
      } },
    }, 'Enregistrer'),
  );
  return wrap;
}

async function toggleMatieresActif(item) {
  const actif = item.actif !== 0;
  if (actif && !confirm('Désactiver la référence « ' + item.reference + ' » ?')) return;
  try {
    if (actif) {
      await api('/api/stock/matieres/' + item.id, { method: 'DELETE' });
      showToast('Référence désactivée.', 'success');
    } else {
      await api('/api/stock/matieres/' + item.id, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ actif: 1 }),
      });
      showToast('Référence réactivée.', 'success');
    }
    await loadMatieresAdminList();
    await loadMatieres();
    renderMatieresAdminDrawer();
  } catch (e) {
    showToast(e.message, 'error');
  }
}

function buildMatieresAdminAddForm() {
  const foot = el('div', { cls: 'mp-drawer-foot' });
  foot.appendChild(el('div', { style: { fontSize: '12px', fontWeight: '600', marginBottom: '12px', color: 'var(--text)' } }, 'Ajouter une référence'));
  const catSel = el('select');
  [['mandrin', 'Mandrin'], ['palette', 'Palette'], ['adhesif', 'Adhésif'], ['carton', 'Carton']].forEach(([v, l]) => {
    catSel.appendChild(el('option', { value: v }, l));
  });
  const refInp = el('input', { attrs: { type: 'text', placeholder: '76MM-3P' } });
  const desInp = el('input', { attrs: { type: 'text' } });
  const seuilInp = el('input', { attrs: { type: 'number', min: '0', step: '0.5', value: '0' } });
  const errEl = el('div', { cls: 'mp-admin-err' }, S.matieresAdminAddError || '');
  foot.append(
    el('div', { cls: 'mp-field' }, el('label', null, 'Catégorie'), catSel),
    el('div', { cls: 'mp-field' }, el('label', null, 'Référence'), refInp),
    el('div', { cls: 'mp-field' }, el('label', null, 'Désignation'), desInp),
    el('div', { cls: 'mp-field' }, el('label', null, 'Seuil d\'alerte (0 = pas d\'alerte)'), seuilInp),
    el('div', { cls: 'mp-hint' }, 'Mandrins, palettes, adhésifs : pal. — cartons : u.'),
    errEl,
    el('button', {
      cls: 'btn',
      type: 'button',
      style: { width: '100%', marginTop: '8px' },
      on: { click: async () => {
        S.matieresAdminAddError = '';
        errEl.textContent = '';
        const ref = refInp.value.trim();
        const des = desInp.value.trim();
        if (!ref || !des) {
          S.matieresAdminAddError = 'Référence et désignation obligatoires.';
          errEl.textContent = S.matieresAdminAddError;
          return;
        }
        try {
          await api('/api/stock/matieres', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              categorie: catSel.value,
              reference: ref,
              designation: des,
              seuil_alerte: parseFloat(seuilInp.value) || 0,
            }),
          });
          showToast('Référence ajoutée.', 'success');
          refInp.value = '';
          desInp.value = '';
          seuilInp.value = '0';
          await loadMatieresAdminList();
          await loadMatieres();
          renderMatieresAdminDrawer();
        } catch (e) {
          S.matieresAdminAddError = e.message || 'Erreur.';
          errEl.textContent = S.matieresAdminAddError;
        }
      } },
    }, 'Ajouter'),
  );
  return foot;
}

window._stockOpenModalMouvement = openModalMouvement;

function fDateTime(iso) {
  if (!iso) return '—';
  const s = String(iso);
  const parts = s.slice(0, 10).split('-');
  const hm = s.length >= 16 ? s.slice(11, 16) : '';
  if (parts.length === 3) {
    return parts[2] + '/' + parts[1] + '/' + parts[0] + (hm ? ' ' + hm : '');
  }
  return fD(iso);
}

function truncStr(s, max) {
  const t = (s || '').trim();
  if (t.length <= max) return t;
  return t.slice(0, max) + '…';
}

function histStockBadge(typeStock) {
  const ts = typeStock === 'mp' ? 'mp' : 'pf';
  const lbl = ts === 'mp' ? 'MP' : 'PF';
  return el('span', { cls: 'hist-badge hist-badge-stock-' + ts }, lbl);
}

function histMvtBadge(typeMvt) {
  const t = (typeMvt || '').toLowerCase();
  const cls = 'hist-badge hist-badge-mvt-' + (t || 'entree');
  return el('span', { cls }, MVT_TYPE_LABELS[t] || t);
}

function resetHistoriqueFiltres() {
  S.historiqueFiltres = {
    type_stock: 'tout',
    categorie: '',
    type_mouvement: '',
    date_debut: '',
    date_fin: '',
  };
  S.historiquePage = 0;
  loadHistorique();
}

function historiqueGoPage(delta) {
  const next = (S.historiquePage || 0) + delta;
  if (next < 0) return;
  if (delta > 0 && !S.historiqueHasMore) return;
  S.historiquePage = next;
  loadHistorique();
}

function buildHistoriqueResultsHead(rowsLen) {
  const page = S.historiquePage || 0;
  const hasPrev = page > 0;
  const hasNext = !!S.historiqueHasMore;
  const start = page * HIST_PAGE_SIZE + (rowsLen ? 1 : 0);
  const end = page * HIST_PAGE_SIZE + rowsLen;
  const countLbl = rowsLen
    ? (start === end ? String(start) : start + '–' + end)
      + (hasNext ? '+' : '') + ' mouvement' + (rowsLen > 1 ? 's' : '')
    : (page > 0 ? 'Page ' + (page + 1) : '0 mouvement');
  const rangeInfo = rowsLen
    ? (start === end ? String(start) : start + '–' + end) + (hasNext ? '+' : '')
    : '—';
  const showNav = rowsLen > 0 || page > 0;
  const left = el('div', { cls: 'hist-results-head-left' },
    el('span', { cls: 'hist-results-title' }, 'Résultats'),
    el('span', { cls: 'hist-count' }, countLbl),
  );
  const nav = el('div', { cls: 'hist-results-head-nav' },
    el('button', {
      cls: 'btn btn-ghost',
      type: 'button',
      disabled: !hasPrev ? true : null,
      on: { click: () => historiqueGoPage(-1) },
    }, 'Précédent'),
    el('span', { cls: 'hist-pagination-info' },
      'Page ' + (page + 1) + (showNav ? ' · ' + rangeInfo : '')),
    el('button', {
      cls: 'btn btn-ghost',
      type: 'button',
      disabled: !hasNext ? true : null,
      on: { click: () => historiqueGoPage(1) },
    }, 'Suivant'),
  );
  if (!showNav) nav.style.display = 'none';
  return el('div', { cls: 'hist-results-head' }, left, nav);
}

function exportHistoriqueCSV() {
  const f = S.historiqueFiltres;
  const params = new URLSearchParams({ limit: '500', format: 'csv' });
  if (f.type_stock !== 'tout') params.set('type_stock', f.type_stock);
  if (f.categorie) params.set('categorie', f.categorie);
  if (f.type_mouvement) params.set('type_mouvement', f.type_mouvement);
  if (f.date_debut) params.set('date_debut', f.date_debut);
  if (f.date_fin) params.set('date_fin', f.date_fin);
  window.location.href = API + '/api/stock/historique-mouvements?' + params.toString();
}

async function loadHistorique(resetPage) {
  if (resetPage) S.historiquePage = 0;
  S.historiqueLoading = true;
  renderHistoriqueView();
  try {
    const f = S.historiqueFiltres;
    const page = S.historiquePage || 0;
    const params = new URLSearchParams({
      limit: String(HIST_PAGE_SIZE),
      offset: String(page * HIST_PAGE_SIZE),
    });
    if (f.type_stock !== 'tout') params.set('type_stock', f.type_stock);
    if (f.categorie) params.set('categorie', f.categorie);
    if (f.type_mouvement) params.set('type_mouvement', f.type_mouvement);
    if (f.date_debut) params.set('date_debut', f.date_debut);
    if (f.date_fin) params.set('date_fin', f.date_fin);
    const d = await api('/api/stock/historique-mouvements?' + params.toString());
    const rows = Array.isArray(d) ? d : [];
    S.historiqueHasMore = rows.length >= HIST_PAGE_SIZE;
    S.historique = rows;
  } catch (e) {
    S.historique = [];
    S.historiqueHasMore = false;
    showToast(e.message, 'error');
  }
  S.historiqueLoading = false;
  renderHistoriqueView();
  const area = document.getElementById('scroll-area');
  if (area) area.scrollTop = 0;
}

function renderHistoriqueView() {
  if (S.tab !== 'historique') return;
  const area = document.getElementById('scroll-area');
  if (!area) return;
  area.innerHTML = '';
  const content = buildHistorique();
  if (content) area.appendChild(content);
}

function buildHistoriqueFilterField(label, inputEl) {
  return el('div', { cls: 'hist-filter-field' }, el('label', null, label), inputEl);
}

function buildHistoriqueFiltersBar() {
  const f = S.historiqueFiltres;
  const typeStockSel = el('select', { id: 'hist-f-type-stock' });
  [['tout', 'Tout'], ['mp', 'Matières premières'], ['produits', 'Produits finis']].forEach(([v, l]) => {
    typeStockSel.appendChild(el('option', { value: v, selected: f.type_stock === v ? true : null }, l));
  });
  typeStockSel.addEventListener('change', () => {
    f.type_stock = typeStockSel.value;
    if (f.type_stock === 'produits') f.categorie = '';
    renderHistoriqueView();
  });

  const catSel = el('select', { id: 'hist-f-categorie', disabled: f.type_stock === 'produits' ? true : null });
  [['', 'Tout'], ['mandrin', 'Mandrins'], ['palette', 'Palettes'], ['adhesif', 'Adhésifs'], ['carton', 'Cartons']].forEach(([v, l]) => {
    catSel.appendChild(el('option', { value: v, selected: f.categorie === v ? true : null }, l));
  });
  catSel.addEventListener('change', () => { f.categorie = catSel.value; });

  const mvtSel = el('select', { id: 'hist-f-mvt' });
  [['', 'Tout'], ['entree', 'Entrée'], ['sortie', 'Sortie'], ['ajustement', 'Ajustement'],
    ['inventaire', 'Inventaire'], ['transfert', 'Transfert']].forEach(([v, l]) => {
    mvtSel.appendChild(el('option', { value: v, selected: f.type_mouvement === v ? true : null }, l));
  });
  mvtSel.addEventListener('change', () => { f.type_mouvement = mvtSel.value; });

  const dateDebut = el('input', { type: 'date', id: 'hist-f-date-debut' });
  dateDebut.value = f.date_debut || '';
  dateDebut.addEventListener('change', () => { f.date_debut = dateDebut.value; });

  const dateFin = el('input', { type: 'date', id: 'hist-f-date-fin' });
  dateFin.value = f.date_fin || '';
  dateFin.addEventListener('change', () => { f.date_fin = dateFin.value; });

  const collapseMobile = typeof window !== 'undefined' && window.innerWidth <= 768 && !S.historiqueFiltresOpen;
  const bar = el('div', {
    cls: 'hist-filters-card sticky' + (collapseMobile ? ' collapsed' : ''),
  });
  bar.appendChild(el('div', { cls: 'hist-filters-card-title' }, 'Critères de recherche'));
  const grid = el('div', { cls: 'hist-filters-grid' },
    buildHistoriqueFilterField('Type de stock', typeStockSel),
    buildHistoriqueFilterField('Catégorie', catSel),
    buildHistoriqueFilterField('Mouvement', mvtSel),
    buildHistoriqueFilterField('Du', dateDebut),
    buildHistoriqueFilterField('Au', dateFin),
  );
  const actions = el('div', { cls: 'hist-filters-actions' },
    el('button', { cls: 'btn btn-accent', type: 'button', on: { click: () => loadHistorique(true) } }, 'Appliquer'),
    el('button', { cls: 'btn btn-ghost', type: 'button', on: { click: resetHistoriqueFiltres } }, 'Réinitialiser'),
  );
  bar.append(grid, actions);
  return bar;
}

function histUniteLabel(m) {
  const u = String(m.unite || '').trim();
  if (u) return u;
  if (m.type_stock === 'mp') return mpUniteNom(m.categorie);
  return '—';
}

function histQteLabel(m) {
  const t = (m.type_mouvement || '').toLowerCase();
  const sign = t === 'entree' ? '+' : (t === 'sortie' ? '−' : '');
  const qte = (sign || '') + fN(m.quantite);
  const cls = 'hist-qte' + (t === 'entree' ? ' hist-qte-entree' : t === 'sortie' ? ' hist-qte-sortie' : '');
  return { qte, cls };
}

function buildHistoriqueTableRow(m) {
  const { qte, cls: qteCls } = histQteLabel(m);
  const avant = m.quantite_avant != null ? fN(m.quantite_avant) : '—';
  const apres = m.quantite_apres != null ? fN(m.quantite_apres) : '—';
  const blNote = [m.ref_bl, m.note].filter(Boolean).join(' · ');
  const op = (m.created_by_name || '').trim() || '—';
  return el('tr', null,
    el('td', { cls: 'hist-muted' }, fDateTime(m.created_at)),
    el('td', null, el('div', { cls: 'hist-cell-badges' }, histStockBadge(m.type_stock), histMvtBadge(m.type_mouvement))),
    el('td', { cls: 'hist-ref' }, stockHistRefLink(m)),
    el('td', { cls: 'hist-des hist-col-optional', title: m.designation || '' }, truncStr(m.designation, 36) || '—'),
    el('td', { cls: 'hist-empl' }, stockHistEmplLinks(m.emplacement)),
    el('td', { cls: 'hist-unite' }, histUniteLabel(m)),
    el('td', null, el('span', { cls: qteCls }, qte)),
    el('td', { cls: 'hist-muted hist-col-optional' }, avant + ' → ' + apres),
    el('td', { cls: 'hist-note-cell hist-muted hist-col-optional', title: blNote }, truncStr(blNote, 40) || '—'),
    el('td', { cls: 'hist-op hist-col-optional' }, op),
  );
}

function buildHistoriqueCard(m) {
  const { qte, cls: qteCls } = histQteLabel(m);
  const avant = m.quantite_avant != null ? fN(m.quantite_avant) : '—';
  const apres = m.quantite_apres != null ? fN(m.quantite_apres) : '—';
  const op = (m.created_by_name || '').trim();
  const blNote = [m.ref_bl, m.note].filter(Boolean).join(' · ');
  const stats = el('dl', { cls: 'hist-card-stats' },
    el('dt', null, 'Emplacement'),
    el('dd', null, stockHistEmplLinks(m.emplacement)),
    el('dt', null, 'Unité'),
    el('dd', null, histUniteLabel(m)),
    el('dt', null, 'Quantité'),
    el('dd', null, el('span', { cls: qteCls }, qte)),
    el('dt', null, 'Stock'),
    el('dd', null, avant + ' → ' + apres),
  );
  if (op) stats.append(el('dt', null, 'Opérateur'), el('dd', null, op));
  return el('div', { cls: 'hist-card' },
    el('div', { cls: 'hist-card-top' },
      el('div', { cls: 'hist-card-badges' }, histStockBadge(m.type_stock), histMvtBadge(m.type_mouvement)),
      el('span', { cls: 'hist-card-date' }, fDateTime(m.created_at)),
    ),
    el('div', { cls: 'hist-card-ref' }, stockHistRefLink(m)),
    m.designation ? el('div', { cls: 'hist-card-des' }, m.designation) : null,
    stats,
    blNote ? el('div', { cls: 'hist-card-note' }, blNote) : null,
  );
}

function buildHistorique() {
  const head = el('div', { cls: 'hist-head' },
    el('div', null,
      el('h2', { cls: 'hist-title' }, 'Historique des mouvements'),
      el('p', { cls: 'hist-subtitle' }, 'Entrées, sorties et ajustements — matières premières et produits finis'),
    ),
    el('div', { cls: 'hist-head-actions' },
      el('button', { cls: 'btn btn-ghost', type: 'button', on: { click: exportHistoriqueCSV } }, 'Export CSV'),
    ),
  );

  const toggleBtn = el('button', {
    cls: 'btn btn-ghost hist-filters-toggle',
    type: 'button',
    on: { click: () => {
      S.historiqueFiltresOpen = !S.historiqueFiltresOpen;
      renderHistoriqueView();
    } },
  }, 'Filtres ' + (S.historiqueFiltresOpen ? '▴' : '▾'));

  const body = el('div', { cls: 'hist-page' }, head, toggleBtn, buildHistoriqueFiltersBar());

  if (S.historiqueLoading) {
    body.appendChild(el('div', { cls: 'hist-loading' },
      el('div', { cls: 'hist-spinner' }),
      'Chargement…',
    ));
    return el('div', { cls: 'content' }, body);
  }

  const rows = S.historique || [];
  const page = S.historiquePage || 0;
  if (!rows.length) {
    const emptyMsg = page > 0
      ? 'Aucun mouvement sur cette page.'
      : 'Aucun mouvement trouvé pour ces critères.';
    if (page > 0) {
      body.appendChild(el('div', { cls: 'hist-results-card' },
        buildHistoriqueResultsHead(0),
        el('div', { cls: 'hist-empty', style: { border: 'none', borderRadius: 0 } }, emptyMsg),
      ));
    } else {
      body.appendChild(el('div', { cls: 'hist-empty' }, emptyMsg));
    }
    return el('div', { cls: 'content' }, body);
  }

  const table = el('table', { cls: 'hist-table' });
  const thead = el('thead', null, el('tr', null,
    el('th', null, 'Date'),
    el('th', null, 'Stock / Mouvement'),
    el('th', null, 'Référence'),
    el('th', { cls: 'hist-col-optional' }, 'Désignation'),
    el('th', null, 'Emplacement'),
    el('th', null, 'Unité'),
    el('th', null, 'Quantité'),
    el('th', { cls: 'hist-col-optional' }, 'Avant → Après'),
    el('th', { cls: 'hist-col-optional' }, 'Ref BL / Note'),
    el('th', { cls: 'hist-col-optional' }, 'Opérateur'),
  ));
  const tbody = el('tbody', null, ...rows.map(buildHistoriqueTableRow));
  table.append(thead, tbody);

  const cards = el('div', { cls: 'hist-cards' }, ...rows.map(buildHistoriqueCard));
  const resultsCard = el('div', { cls: 'hist-results-card' },
    buildHistoriqueResultsHead(rows.length),
    el('div', { cls: 'hist-table-wrap' }, table),
    cards,
  );
  body.appendChild(resultsCard);

  return el('div', { cls: 'content' }, body);
}

function openReceptionQuick() {
  goToTab('reception');
  requestAnimationFrame(() => {
    setTimeout(() => { try { recepStartCamera(); } catch (e) {} }, 100);
  });
}

function dashMpCatBadge(categorie) {
  const c = (categorie || '').toLowerCase();
  const lbl = MP_CAT_LABELS[c] || categorie || '—';
  return el('span', { cls: 'dash-mp-cat dash-mp-cat-' + c }, lbl);
}

function dashMvtBadge(type) {
  const t = (type || '').toLowerCase();
  const cls = 'dash-badge dash-badge-mvt-' + (t || 'entree');
  return el('span', { cls }, MVT_TYPE_LABELS[t] || t);
}

function dashStockTypeBadge(typeStock) {
  const ts = typeStock === 'mp' ? 'mp' : 'pf';
  const lbl = ts === 'mp' ? 'MP' : 'PF';
  return el('span', { cls: 'dash-badge dash-badge-stock-' + ts }, lbl);
}

function buildDashboardKpis(s) {
  const kpis = [
    { label: 'Références', value: s.nb_refs || 0, mod: 'accent' },
    { label: 'Emplacements occupés', value: s.nb_empl_occupes || 0, mod: 'accent' },
    { label: 'Unités en stock', value: s.total_unites || 0, mod: 'accent' },
    { label: 'À inventorier', value: s.nb_a_inventorier || 0, mod: (s.nb_a_inventorier > 0 ? 'warn' : 'accent') },
  ];
  return el('div', { cls: 'dash-kpi-grid' },
    ...kpis.map(k => el('div', { cls: 'stat-card' },
      el('div', { cls: 'stat-label' }, k.label),
      el('div', { cls: 'stat-value ' + k.mod }, fN(k.value)),
    )),
  );
}

function buildDashboardShortcuts() {
  const mk = (label, onClick, extraCls) => el('button', {
    cls: 'dash-quick-btn' + (extraCls ? ' ' + extraCls : ''),
    type: 'button',
    on: { click: onClick },
  }, label);
  return el('div', { cls: 'dash-quick-card' },
    el('div', { cls: 'dash-quick-card-title' }, 'Actions rapides'),
    el('div', { cls: 'dash-quick-grid' },
      mk('Ajouter stock produits finis', openDashboardAddPfModal, 'dash-quick-btn-accent'),
      mk('Réception matière', openReceptionQuick),
      mk('Entrée MP', () => openModalMouvement('entree')),
      mk('Sortie MP', () => openModalMouvement('sortie')),
      mk('Ajustement MP', () => openModalMouvement('ajustement')),
    ),
  );
}

function buildDashboardAlertes(d) {
  const alertesMp = d.alertes_mp || [];
  const mpRows = alertesMp.length
      ? el('div', { cls: 'dash-alert-rows' }, ...alertesMp.map(a => el('div', {
          cls: 'dash-alert-row',
          on: { click: () => goToTab('matieres') },
        },
          dashMpCatBadge(a.categorie),
          el('span', { cls: 'dash-alert-main' },
            (a.reference || '') + ' — ' + (a.designation || '')
          ),
          el('span', { cls: 'dash-alert-qty' },
            mpStockLine(a.quantite, a.categorie) + ' / min. ' + mpStockLine(a.seuil_alerte, a.categorie)
          ),
        )))
      : el('div', { cls: 'dash-alert-ok' }, 'Toutes les matières sont au-dessus des seuils.');
  return el('div', { cls: 'dash-section' },
    el('div', { cls: 'dash-section-title' }, 'Stocks à réapprovisionner'),
    el('div', { cls: 'dash-alert-block' }, mpRows),
  );
}

function dashActUniteLabel(m) {
  const u = String(m.unite || '').trim();
  if (u) return u;
  if (m.type_stock === 'mp') return mpUniteNom(m.categorie);
  return '';
}

function dashActQteDisplay(m) {
  const unit = dashActUniteLabel(m);
  const t = (m.type_mouvement || '').toLowerCase();
  const sign = t === 'entree' ? '+' : (t === 'sortie' ? '−' : '');
  const n = m.quantite;
  const text = unit ? (sign || '') + fU(n, unit) : (sign || '') + fN(n);
  const cls = 'dash-act-qte' + (t === 'entree' ? ' dash-act-qte-entree' : t === 'sortie' ? ' dash-act-qte-sortie' : '');
  return { text, cls };
}

function dashActEmplacement(m) {
  const e = String(m.emplacement || '').trim();
  return e || null;
}

function buildDashboardActivite(d) {
  const rows = d.activiteRecente || [];
  const list = el('div', { cls: 'dash-act-list' });
  if (!rows.length) {
    list.appendChild(el('div', { cls: 'dash-act-empty' }, 'Aucun mouvement enregistré.'));
  } else {
    rows.forEach(m => {
      const ref = (m.reference || '—').trim();
      const des = (m.designation || '').trim();
      const { text: qteText, cls: qteCls } = dashActQteDisplay(m);
      const empl = dashActEmplacement(m);
      const actor = (m.created_by_name || '').trim();
      const when = timeAgo(m.created_at);
      const fullTitle = [ref, des, empl, qteText, actor, when].filter(Boolean).join(' · ');
      const mainEl = el('span', { cls: 'dash-act-main', title: fullTitle });
      mainEl.appendChild(stockHistRefLink(m, ref));
      if (des) {
        mainEl.appendChild(el('span', null, ' · '));
        mainEl.appendChild(el('span', { cls: 'dash-act-des' }, truncStr(des, 48)));
      }
      list.appendChild(el('div', { cls: 'dash-act-row' },
        el('div', { cls: 'dash-act-badges' },
          dashStockTypeBadge(m.type_stock),
          dashMvtBadge(m.type_mouvement),
        ),
        mainEl,
        el('span', { cls: qteCls }, qteText),
        stockHistMetaRow(m),
      ));
    });
  }
  return el('div', { cls: 'dash-section' },
    el('div', { cls: 'dash-section-title' }, 'Activité récente'),
    el('div', { cls: 'dash-act-card' }, list),
  );
}

function renderDashboardAddPfModal() {
  const mroot = document.getElementById('mroot');
  if (!mroot) return;
  mroot.innerHTML = '';
  S.mpModal = null;

  const F = ADD_PF_FIELD_IDS;
  const refI = el('input', { cls: 'field-input', id: 'dash-add-pf-ref', placeholder: 'Référence (neuve ou déjà en base)', autocomplete: 'off', style: { direction: 'ltr' } });
  const qtyI = el('input', { cls: 'field-input', id: 'dash-add-pf-qty', type: 'text', inputmode: 'decimal', placeholder: 'Quantité', autocomplete: 'off', style: { direction: 'ltr' } });
  const unitWrap = el('div', { cls: 'empl-combo-wrap' });
  const unitInp = el('input', {
    cls: 'field-input', type: 'text', id: F.unitInput,
    placeholder: 'Unité de vente (ex. cartons, 500 cartons…)', autocomplete: 'off',
    title: 'Obligatoire — suggestions + ligne violette « Autre »', style: { direction: 'ltr' },
  });
  const unitList = el('div', { cls: 'empl-suggestions', id: F.unitList, style: { display: 'none' } });
  unitWrap.appendChild(unitInp);
  unitWrap.appendChild(unitList);
  const emplWrap = el('div', { cls: 'empl-combo-wrap' });
  const emplInp = el('input', {
    cls: 'field-input empl-upper', type: 'text', id: F.emplInput,
    placeholder: 'Emplacement (ex. a121, z999…)', autocomplete: 'off',
    title: 'Obligatoire — suggestions + ligne violette « Ajouter emplacement »', style: { direction: 'ltr' },
  });
  const emplList = el('div', { cls: 'empl-suggestions', id: F.emplList, style: { display: 'none' } });
  emplWrap.appendChild(emplInp);
  emplWrap.appendChild(emplList);
  const comI = el('input', { cls: 'field-input', id: 'dash-add-pf-comment', placeholder: 'Commentaire (facultatif)', autocomplete: 'off', style: { direction: 'ltr' } });

  const today = new Date().toISOString().slice(0, 10);
  const prodDateInp = el('input', { cls: 'field-input', type: 'date', value: today, style: { direction: 'ltr' } });
  const prodDateField = el('div', { cls: 'modal-field', style: { display: 'none', marginTop: '6px' } },
    el('label', { cls: 'field-label' }, 'Date de production'),
    prodDateInp,
  );
  const prodCb = el('input', { type: 'checkbox', id: 'dash-add-pf-prod-check' });
  const sousTraitCb = el('input', { type: 'checkbox', id: 'dash-add-pf-strait-check' });
  prodCb.addEventListener('change', () => {
    if (prodCb.checked) { sousTraitCb.checked = false; prodDateField.style.display = ''; }
    else { prodDateField.style.display = 'none'; }
  });
  sousTraitCb.addEventListener('change', () => {
    if (sousTraitCb.checked) { prodCb.checked = false; prodDateField.style.display = 'none'; }
  });
  const origineBlock = el('div', { cls: 'modal-field', style: { marginBottom: '0' } },
    el('label', { cls: 'field-label' }, 'Origine'),
    el('div', { cls: 'mvt-origin-group' },
      el('label', { cls: 'mvt-origin-label' }, prodCb, 'Production'),
      el('label', { cls: 'mvt-origin-label' }, sousTraitCb, 'Sous-traitance'),
    ),
    prodDateField,
  );

  const resetForm = () => {
    refI.value = '';
    qtyI.value = '';
    comI.value = '';
    emplInp.value = '';
    unitInp.value = '';
    prodCb.checked = false;
    sousTraitCb.checked = false;
    prodDateField.style.display = 'none';
  };

  const submitBtn = el('button', { cls: 'btn btn-accent', type: 'button' }, 'Ajouter au stock');
  submitBtn.addEventListener('click', async () => {
    const raw = (refI.value || '').trim();
    const ref = raw.toUpperCase();
    if (!ref) { showToast('Référence requise', 'error'); return; }
    const qRaw = (qtyI.value || '').trim();
    const emplVal = String((emplInp.value || '').trim().toUpperCase());
    if (!emplVal || !isStockEmplacementCode(emplVal)) {
      showToast('Emplacement obligatoire (une lettre puis des chiffres, ex. Z999)', 'error');
      return;
    }
    const qte = parseFloat(qRaw.replace(',', '.'));
    if (!qRaw || Number.isNaN(qte) || qte <= 0) {
      showToast('Quantité obligatoire (nombre supérieur à 0)', 'error');
      return;
    }
    let prefix = '';
    if (prodCb.checked) {
      const dp = prodDateInp.value;
      prefix = dp ? 'Production | ' + dp : 'Production';
    } else if (sousTraitCb.checked) {
      prefix = 'Sous-traitance';
    }
    const userNote = (comI.value || '').trim();
    const finalNote = [prefix, userNote].filter(Boolean).join(' | ');
    await createProduit(ref, finalNote, qte, emplVal, unitInp.value);
    resetForm();
  });

  const overlay = el('div', {
    id: 'dash-add-pf-overlay',
    cls: 'modal-overlay',
    on: { click: (e) => { if (e.target === overlay) closeDashboardAddPfModal(); } },
  });
  const sheet = el('div', { cls: 'modal-sheet', on: { click: (e) => e.stopPropagation() } },
    el('span', { cls: 'modal-handle' }),
    el('div', { cls: 'modal-title' }, 'Ajouter stock produits finis'),
    el('div', { cls: 'modal-sub', style: { marginBottom: '14px', lineHeight: '1.45' } },
      'Même référence qu\'un produit existant : une entrée de stock est enregistrée, sans dupliquer la fiche.'),
    el('div', { cls: 'modal-field' },
      el('label', { cls: 'field-label' }, 'Référence *'),
      refI,
    ),
    el('div', { cls: 'add-form-row', style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' } },
      el('div', null, el('label', { cls: 'field-label' }, 'Quantité *'), qtyI),
      el('div', null, el('label', { cls: 'field-label' }, 'Unité de vente *'), unitWrap),
    ),
    el('div', { cls: 'modal-field' },
      el('label', { cls: 'field-label' }, 'Emplacement *'),
      emplWrap,
    ),
    origineBlock,
    el('div', { cls: 'modal-field', style: { marginTop: '10px' } },
      el('label', { cls: 'field-label' }, 'Commentaire'),
      comI,
    ),
    el('div', { style: { display: 'flex', gap: '10px', marginTop: '18px' } },
      el('button', { cls: 'btn-cancel', type: 'button', style: { flex: 1 }, on: { click: closeDashboardAddPfModal } }, 'Annuler'),
      el('div', { style: { flex: 2 } }, submitBtn),
    ),
  );
  overlay.appendChild(sheet);
  mroot.appendChild(overlay);

  requestAnimationFrame(() => {
    wireAddEmplCombo(F.emplInput, F.emplList);
    wireAddUnitCombo(F.unitInput, F.unitList);
    refI.focus();
  });
}

function buildDashboard() {
  const d = S.dashboard;
  if (!d) return el('div',{cls:'content dash-page'},el('div',{cls:'card-empty'},'Chargement…'));
  const s = d.stats||{};
  const parts = [
    el('h2',{cls:'dash-title'},'Tableau de bord'),
    buildDashboardKpis(s),
  ];
  if (!S.stockReadOnly) parts.push(buildDashboardShortcuts());
  parts.push(buildDashboardAlertes(d));
  parts.push(buildDashboardActivite(d));
  return el('div',{cls:'content dash-page'},...parts);
}

function clearSel() {
  S.selProduit = null;
  S.selEmpl = null;
  renderContent();
  updateNavActive();
}

function buildProduitDetail() {
  const sel = S.selProduit;
  if (!sel || !sel.produit) return el('div',{cls:'content'},el('div',{cls:'card-empty'},'Données produit indisponibles'));
  const p = sel.produit;
  const empls = sel.emplacements || [];
  const unite = p.unite || 'étiquettes';

  const back = el('button',{cls:'btn-ghost',style:{marginBottom:'14px'},on:{click:clearSel}},'← Retour au tableau de bord');

  const emplBlock = empls.length === 0
    ? el('div',{cls:'card'},el('div',{cls:'card-empty'},'Aucun stock actif pour cette référence.'))
    : el('div',{cls:'card'},
        el('div',{cls:'card-header'},el('div',{cls:'card-title'},'Stock par emplacement')),
        el('div',null,...empls.map(e => el('div',{
          cls:'empl-row',
          on:{click:()=>loadEmplacement(e.emplacement)}
        },
          el('div',null,
            el('div',{cls:'empl-code'},e.emplacement),
            el('div',{cls:'empl-info'},'FIFO lot : '+fD(e.date_fifo_empl)+(e.alerte_inventaire?' · inventaire':'')+(e.jours_stock!=null?' · ~'+e.jours_stock+'j':''))
          ),
          el('div',null,
            el('div',{cls:'empl-qte'},fU(e.quantite, unite)),
            el('div',{cls:'empl-date'},fD(e.updated_at||e.date_fifo_empl))
          )
        )))
      );

  const actions = S.stockReadOnly ? el('div') : el('div',{cls:'action-bar',style:{marginTop:'14px'}},
    el('button',{cls:'action-btn entree',on:{click:()=>openMvtModal(p.id,p.reference,'','entree')}},'↓ Entrée'),
    el('button',{cls:'action-btn sortie',on:{click:()=>openMvtModal(p.id,p.reference,'','sortie')}},'↑ Sortie'),
    el('button',{cls:'action-btn inventaire',on:{click:()=>openMvtModal(p.id,p.reference,'','inventaire')}},'= Inventaire')
  );

  return el('div',{cls:'content'},
    back,
    el('div',{cls:'scorecard'},
      el('div',{cls:'sc-ref'},p.reference),
      el('div',{cls:'sc-des'},p.designation||'—'),
      el('div',{cls:'sc-stats'},
        el('div',{cls:'sc-stat'},el('div',{cls:'sc-stat-label'},'Stock total'),el('div',{cls:'sc-stat-value'},fU(sel.stock_total, unite))),
        el('div',{cls:'sc-stat'},el('div',{cls:'sc-stat-label'},'Lots actifs'),el('div',{cls:'sc-stat-value'},String(sel.nb_lots||0))),
        sel.jours_stock != null
          ? el('div',{cls:'sc-stat'},el('div',{cls:'sc-stat-label'},'Ancienneté'),el('div',{cls:'sc-stat-value'},String(sel.jours_stock)+' j'))
          : null
      )
    ),
    actions,
    emplBlock,
    buildMvtHistory(sel.mouvements||[], unite, { primary:'emplacement' })
  );
}

function buildEmplacementDetail() {
  const sel = S.selEmpl;
  if (!sel || sel.emplacement == null) return el('div',{cls:'content'},el('div',{cls:'card-empty'},'Emplacement introuvable'));
  const refs = sel.refs || [];
  const code = sel.emplacement;

  const back = el('button',{cls:'btn-ghost',style:{marginBottom:'14px'},on:{click:clearSel}},'← Retour au tableau de bord');

  const actions = S.stockReadOnly ? null : el('div',{cls:'action-bar',style:{marginTop:'14px'}},
    el('button',{cls:'action-btn entree',on:{click:()=>openEmplEntreeModal(code)}},'↓ Entrée')
  );

  const head = el('div',{cls:'scorecard'},
    el('div',{cls:'sc-ref'},code),
    el('div',{cls:'sc-des'},(sel.nb_refs||0)+' réf. · '+fN(sel.total_unites)+' u. en stock'),
    el('div',{cls:'sc-stats'},
      el('div',{cls:'sc-stat'},el('div',{cls:'sc-stat-label'},'Références'),el('div',{cls:'sc-stat-value'},String(refs.length))),
      el('div',{cls:'sc-stat'},el('div',{cls:'sc-stat-label'},'Unités'),el('div',{cls:'sc-stat-value'},fN(sel.total_unites)))
    )
  );

  const refBlock = refs.length === 0
    ? el('div',{cls:'card'},el('div',{cls:'card-empty'},'Aucune unité stockée à cet emplacement (lots actifs).'))
    : el('div',{cls:'card'},
        el('div',{cls:'card-header'},el('div',{cls:'card-title'},'Produits à cet emplacement')),
        el('div',null,...refs.map(r => el('div',{
          cls:'empl-row',
          on:{click:()=>loadProduit(r.id)}
        },
          el('div',null,el('div',{cls:'empl-code'},r.reference),el('div',{cls:'empl-info'},r.designation||'')),
          el('div',null,el('div',{cls:'empl-qte'},fU(r.quantite, r.unite||'')),el('div',{cls:'empl-date'},fD(r.date_fifo)))
        )))
      );

  return el('div',{cls:'content'}, back, head, actions, refBlock, buildMvtHistory(sel.mouvements||[], '', { primary:'emplacement' }));
}
// ── Config traçabilité ────────────────────────────────────────────
const TRACA_POSTES = [
  { id:'bureaux',    label:'Bureaux',      icon:'briefcase', color:'#6366f1', colorBg:'rgba(99,102,241,.12)' },
  { id:'cohesio1',   label:'Cohésio 1',    icon:'cpu',       color:'#f59e0b', colorBg:'rgba(245,158,11,.12)' },
  { id:'cohesio2',   label:'Cohésio 2',    icon:'cpu',       color:'#f59e0b', colorBg:'rgba(245,158,11,.12)' },
  { id:'logistique', label:'Logistique',   icon:'truck',     color:'#10b981', colorBg:'rgba(16,185,129,.12)' },
];

const TRACA_FORMATS = [
  { id:'a4p',     label:'A4 paysage',   dims:'297×210 mm' },
  { id:'120x105', label:'120×105 mm',   dims:'120×105 mm' },
  { id:'105x50',  label:'105×50 mm',    dims:'105×50 mm'  },
  { id:'40x20',   label:'40×20 mm',     dims:'40×20 mm'   },
  { id:'40x30',   label:'40×30 mm',     dims:'40×30 mm'   },
];

const TRACA_ETIQUETTES = [
  // Logistique
  { id:'id_palette_a4',   label:'Identification palette',  format:'a4p',    postes:['logistique']               },
  { id:'nb_palettes_logi',label:'Nombre de palettes',      format:'120x105',postes:['logistique']               },
  // Bureaux
  { id:'id_plaque',       label:'Identification plaques',  format:'105x50', postes:['bureaux']                  },
  { id:'id_cliche',       label:'Identification clichés',  format:'105x50', postes:['bureaux']                  },
  // Cohésio
  { id:'nb_palettes_c',   label:'Nombre de palettes',      format:'105x50', postes:['cohesio1','cohesio2']      },
  { id:'id_carton',       label:'Identification carton',   format:'105x50', postes:['cohesio1','cohesio2']      },
  { id:'id_bobine',       label:'Identification bobine',   format:'40x20',  postes:['cohesio1','cohesio2']      },
];

// ── Helpers impression ────────────────────────────────────────────
function _printWin(title, pageSize, css, body) {
  const w = window.open('', '_blank');
  if (!w) { showToast('Autorisez les popups pour imprimer', 'error'); return null; }
  w.document.write(`<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8">
<title>${title}</title>
<style>
@page { size: ${pageSize}; margin: 0; }
*{ margin:0; padding:0; box-sizing:border-box; }
body{ font-family: Arial, Helvetica, sans-serif; background:#fff; }
${css}
</style>
</head><body>${body}<script>window.onload=function(){window.focus();window.print();}<\/script></body></html>`);
  w.document.close();
  return w;
}

function _inp(placeholder, opts={}) {
  return el('input', { cls:'field-input', attrs:{ type: opts.type||'text', placeholder, autocomplete:'off', ...(opts.attrs||{}) }, style: opts.style||{} });
}

// ── 1. Logistique — Identification palette (A4 paysage) ───────────
function buildIdPaletteA4Form() {
  let _ref='', _qty='', _unit=allUnitLabels()[0]||'étiquettes', _qctn='';
  function doPrint() {
    const ref = _ref.trim(), qty = _qty.trim(), qctn = _qctn.trim();
    if (!ref) { showToast('Référence requise', 'error'); return; }
    // Format nombre avec points entre milliers
    function fmtNb(n){return String(n).replace(/\B(?=(\d{3})+(?!\d))/g,'.');}
    // Abréviation étiquettes → ETQ
    const unitDisplay = (_unit||'').toLowerCase()==='étiquettes'?'ETQ':(_unit||'').toUpperCase();
    const quv = qty ? fmtNb(qty) + '\u00a0' + unitDisplay : '';
    const unitLow = _unit.toLowerCase().replace(/s$/, '');  // 'cartons' → 'carton'
    const showCtn = !!qctn && unitLow !== 'carton';
    const qctnNum = parseInt(qctn) || 0;
    const ctnLabel = qctnNum === 1 ? '1\u00a0CARTON' : (fmtNb(qctn) + '\u00a0CARTONS');
    _printWin('Palette — '+ref, '297mm 210mm',
      `.label{width:297mm;height:210mm;padding:14mm 18mm;display:flex;flex-direction:column;
              align-items:center;justify-content:center;gap:10mm;
              text-align:center;page-break-after:always;page-break-inside:avoid;
              font-family:'Berlin Sans FB','Berlin Sans FB Demi',Arial,sans-serif;text-transform:uppercase}
       .ref{font-size:112pt;font-weight:900;letter-spacing:1pt;word-break:break-all;line-height:1.1;text-decoration:underline}
       .quv{font-size:100pt;font-weight:800;color:#111}
       .qctn{font-size:72pt;font-weight:700;color:#333}`,
      `<div class="label">
         <div class="ref">${ref} FS</div>
         ${quv?`<div class="quv">${quv}</div>`:''}
         ${showCtn?`<div class="qctn">(${ctnLabel})</div>`:''}
       </div>`);
  }
  const rInp=_inp('Référence produit — ex. 1077/0026'); rInp.addEventListener('input',e=>{_ref=e.target.value;});
  // Quantité
  const qtyInp=_inp('Quantité — ex. 500',{type:'number',attrs:{min:'1',step:'1'}});
  qtyInp.style.width='100%';
  qtyInp.addEventListener('input',e=>{_qty=e.target.value;});
  // Sélecteur unité de vente (même liste que le dashboard add-form)
  const unitSel=document.createElement('select');
  unitSel.className='field-input';
  unitSel.style.cssText='width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:8px 10px;font-size:13px;color:var(--text);font-family:inherit;cursor:pointer;outline:none';
  allUnitLabels().forEach(u=>{
    const opt=document.createElement('option');
    opt.value=u; opt.textContent=u;
    if(u===_unit) opt.selected=true;
    unitSel.appendChild(opt);
  });
  unitSel.addEventListener('change',e=>{_unit=e.target.value;});
  // Cartons
  const cInp=_inp('Quantité cartons — ex. 20',{type:'text'}); cInp.addEventListener('input',e=>{_qctn=e.target.value;});
  const btn=el('button',{cls:'traca-print-btn',style:{width:'100%',marginTop:'12px',justifyContent:'center'}},iconEl('printer',15),' Imprimer');
  btn.addEventListener('click',doPrint);
  // Ligne qty + unité côte-à-côte
  const qtyUnitRow=el('div',{cls:'etiq-form-row'},
    el('div',{cls:'etiq-form-field',style:{flex:'1'}},el('label',{cls:'etiq-form-label'},'Quantité'),qtyInp),
    el('div',{cls:'etiq-form-field',style:{flex:'1.6'}},el('label',{cls:'etiq-form-label'},'Unité de vente'),unitSel)
  );
  return el('div',null,
    el('div',{cls:'etiq-form-field'},el('label',{cls:'etiq-form-label'},'Référence produit *'),rInp),
    qtyUnitRow,
    el('div',{cls:'etiq-form-field'},el('label',{cls:'etiq-form-label'},'Quantité cartons'),cInp),
    btn);
}

// ── 2. Logistique — Nombre de palettes (120mm × 105mm) ────────────
function buildNbPalettesLogiForm() {
  let _n='';
  function doPrint() {
    const n=parseInt(_n)||0;
    if(n<1||n>500){showToast('Nombre invalide (1–500)','error');return;}
    let html='';
    for(let i=1;i<=n;i++)
      html+=`<div class="label"><div class="head">PALETTE</div><div class="num">${i}/${n}</div></div>`;
    _printWin('Palettes','120mm 105mm',
      `.label{width:120mm;height:105mm;display:flex;flex-direction:column;align-items:center;
              justify-content:center;gap:7mm;text-align:center;
              page-break-after:always;page-break-inside:avoid}
       .head{font-size:62pt;font-weight:900;letter-spacing:4pt;text-transform:uppercase}
       .num{font-size:86pt;font-weight:900;letter-spacing:2pt}`,html);
  }
  const nInp=_inp('Nombre de palettes — ex. 8',{type:'number',attrs:{min:'1',max:'500'},style:{width:'140px'}});
  nInp.addEventListener('input',e=>{_n=e.target.value;});
  const btn=el('button',{cls:'traca-print-btn',style:{width:'100%',marginTop:'12px',justifyContent:'center'}},iconEl('printer',15),' Imprimer');
  btn.addEventListener('click',doPrint);
  return el('div',null,
    el('div',{cls:'etiq-form-field'},el('label',{cls:'etiq-form-label'},'Nombre de palettes *'),nInp),
    btn);
}

// ── 3. Bureaux — Identification plaques (105mm × 74mm + EAN128) ───
function buildIdPlaqueForm() {
  let _num='', _fl='', _fw='', _note='';
  const JSBARCODE_CDN='https://cdnjs.cloudflare.com/ajax/libs/jsbarcode/3.11.6/JsBarcode.all.min.js';
  function doPrint() {
    const num=_num.trim(), fl=_fl.trim(), fw=_fw.trim(), note=_note.trim();
    if(!num){showToast('Numéro de plaque requis','error');return;}
    const fmt=fl&&fw?`${fl} × ${fw} mm`:'';
    const w=_printWin('Plaque '+num,'105mm 74mm',
      `.label{width:105mm;height:74mm;padding:3mm 4mm;display:flex;flex-direction:column;
              align-items:center;justify-content:center;text-align:center;gap:1.5mm;
              page-break-after:always;page-break-inside:avoid}
       .head{font-size:14pt;font-weight:700;text-transform:uppercase;letter-spacing:.5pt;color:#555}
       .num{font-size:88pt;font-weight:900;letter-spacing:.5pt;line-height:0.95}
       .fmt{font-size:16pt;font-weight:600;color:#333}
       .note{font-size:12pt;font-weight:500;color:#444;margin-top:1mm}
       .bar{display:flex;justify-content:center;margin-top:1.5mm}
       svg{max-width:97mm;height:10mm}`,
      `<div class="label">
         <div class="head">Plaque N°</div>
         <div class="num">${num}</div>
         ${fmt?`<div class="fmt">${fmt}</div>`:''}
         ${note?`<div class="note">${note}</div>`:''}
         <div class="bar"><svg id="bc"></svg></div>
       </div>
       <script src="${JSBARCODE_CDN}"><\/script>
       <script>window.onload=function(){try{JsBarcode('#bc','${num}',{format:'CODE128',displayValue:false,margin:0,height:36});}catch(e){}window.focus();window.print();}<\/script>`);
    if(w) w.document.close();
  }
  const nInp=_inp('N° de plaque — ex. 1234'); nInp.addEventListener('input',e=>{_num=e.target.value;});
  const lInp=_inp('L (mm)',{style:{width:'90px'}}); lInp.addEventListener('input',e=>{_fl=e.target.value;});
  const wInp=_inp('l (mm)',{style:{width:'90px'}}); wInp.addEventListener('input',e=>{_fw=e.target.value;});
  const noteInp=_inp('Note (optionnel)'); noteInp.addEventListener('input',e=>{_note=e.target.value;});
  const btn=el('button',{cls:'traca-print-btn',style:{width:'100%',marginTop:'12px',justifyContent:'center'}},iconEl('printer',15),' Imprimer');
  btn.addEventListener('click',doPrint);
  return el('div',null,
    el('div',{cls:'etiq-form-field'},el('label',{cls:'etiq-form-label'},'Numéro de plaque *'),nInp),
    el('div',{cls:'etiq-form-row'},
      el('div',{cls:'etiq-form-field'},el('label',{cls:'etiq-form-label'},'Format L (mm)'),lInp),
      el('div',{cls:'etiq-form-field'},el('label',{cls:'etiq-form-label'},'Format l (mm)'),wInp)),
    el('div',{cls:'etiq-form-field'},el('label',{cls:'etiq-form-label'},'Note'),noteInp),
    btn);
}

// ── 4. Bureaux — Identification clichés (105mm × 74mm + EAN128) ───
function buildIdClicheForm() {
  let _num='', _fl='', _fw='';
  const JSBARCODE_CDN='https://cdnjs.cloudflare.com/ajax/libs/jsbarcode/3.11.6/JsBarcode.all.min.js';
  function doPrint() {
    const num=_num.trim(), fl=_fl.trim(), fw=_fw.trim();
    if(!num){showToast('Numéro de cliché requis','error');return;}
    const fmt=fl&&fw?`${fl} × ${fw} mm`:'';
    const w=_printWin('Cliché '+num,'105mm 74mm',
      `.label{width:105mm;height:74mm;padding:3mm 4mm;display:flex;flex-direction:column;
              align-items:center;justify-content:center;text-align:center;gap:1.5mm;
              page-break-after:always;page-break-inside:avoid}
       .head{font-size:14pt;font-weight:700;text-transform:uppercase;letter-spacing:.5pt;color:#555}
       .num{font-size:88pt;font-weight:900;letter-spacing:.5pt;line-height:0.95}
       .fmt{font-size:16pt;font-weight:600;color:#333}
       .bar{display:flex;justify-content:center;margin-top:1.5mm}
       svg{max-width:97mm;height:10mm}`,
      `<div class="label">
         <div class="head">Cliché N°</div>
         <div class="num">${num}</div>
         ${fmt?`<div class="fmt">${fmt}</div>`:''}
         <div class="bar"><svg id="bc"></svg></div>
       </div>
       <script src="${JSBARCODE_CDN}"><\/script>
       <script>window.onload=function(){try{JsBarcode('#bc','${num}',{format:'CODE128',displayValue:false,margin:0,height:36});}catch(e){}window.focus();window.print();}<\/script>`);
    if(w) w.document.close();
  }
  const nInp=_inp('N° de cliché — ex. 5678'); nInp.addEventListener('input',e=>{_num=e.target.value;});
  const lInp=_inp('L (mm)',{style:{width:'90px'}}); lInp.addEventListener('input',e=>{_fl=e.target.value;});
  const wInp=_inp('l (mm)',{style:{width:'90px'}}); wInp.addEventListener('input',e=>{_fw=e.target.value;});
  const btn=el('button',{cls:'traca-print-btn',style:{width:'100%',marginTop:'12px',justifyContent:'center'}},iconEl('printer',15),' Imprimer');
  btn.addEventListener('click',doPrint);
  return el('div',null,
    el('div',{cls:'etiq-form-field'},el('label',{cls:'etiq-form-label'},'Numéro de cliché *'),nInp),
    el('div',{cls:'etiq-form-row'},
      el('div',{cls:'etiq-form-field'},el('label',{cls:'etiq-form-label'},'Format L (mm)'),lInp),
      el('div',{cls:'etiq-form-field'},el('label',{cls:'etiq-form-label'},'Format l (mm)'),wInp)),
    btn);
}

// ── 5. Cohésio 1 & 2 — Nombre de palettes (105mm × 50mm) ─────────
function buildNbPalettesCForm() {
  let _ref='', _n='';
  function doPrint() {
    const ref=_ref.trim(), n=parseInt(_n)||0;
    if(!ref){showToast('Référence requise','error');return;}
    if(n<1||n>500){showToast('Nombre invalide (1–500)','error');return;}
    let html='';
    for(let i=1;i<=n;i++)
      html+=`<div class="label">
        <div class="l1">Produit\u00a0: ${ref}</div>
        <div class="l2">Palette n.\u00a0:</div>
        <div class="l3">${i}/${n}</div>
      </div>`;
    _printWin('Palettes — '+ref,'105mm 50mm',
      `.label{width:105mm;height:50mm;padding:2mm 3mm;display:flex;flex-direction:column;
              align-items:center;justify-content:center;gap:1mm;
              page-break-after:always;page-break-inside:avoid;text-align:center}
       .l1{font-size:28pt;font-weight:700;word-break:break-all;line-height:1.2}
       .l2{font-size:28pt;font-weight:700;line-height:1.2}
       .l3{font-size:43pt;font-weight:900;line-height:1.1;margin-top:1.5mm}`,
      html);
  }
  const rInp=_inp('Référence — ex. 1077/0026'); rInp.addEventListener('input',e=>{_ref=e.target.value.toUpperCase();});
  const nInp=_inp('Nb palettes',{type:'number',attrs:{min:'1',max:'500'},style:{width:'120px'}}); nInp.addEventListener('input',e=>{_n=e.target.value;});
  const btn=el('button',{cls:'traca-print-btn',style:{width:'100%',marginTop:'12px',justifyContent:'center'}},iconEl('printer',15),' Imprimer');
  btn.addEventListener('click',doPrint);
  return el('div',null,
    el('div',{cls:'etiq-form-row'},
      el('div',{cls:'etiq-form-field',style:{flex:'1'}},el('label',{cls:'etiq-form-label'},'Référence produit *'),rInp),
      el('div',{cls:'etiq-form-field'},el('label',{cls:'etiq-form-label'},'Nb palettes *'),nInp)),
    btn);
}

// ── 6. Cohésio 1 & 2 — Identification carton (105mm × 50mm) ──────
function buildIdCartonForm() {
  let _ref='', _bpc='', _epb='';
  function doPrint() {
    const ref=_ref.trim(), bpc=_bpc.trim(), epb=_epb.trim();
    if(!ref){showToast('Référence requise','error');return;}
    const cond=[bpc?bpc+' bob/ctn':'', epb?epb+' étiq/bob':''].filter(Boolean).join(' · ');
    _printWin('Carton — '+ref,'105mm 50mm',
      `.label{width:105mm;height:50mm;padding:3mm 4mm;display:flex;flex-direction:column;justify-content:space-between;page-break-after:always;page-break-inside:avoid}
       .ref{font-size:20pt;font-weight:900;word-break:break-all}
       .cond{font-size:13pt;font-weight:600;color:#333}`,
      `<div class="label"><div class="ref">${ref}</div>${cond?`<div class="cond">${cond}</div>`:''}</div>`);
  }
  const rInp=_inp('Référence — ex. 1077/0026'); rInp.addEventListener('input',e=>{_ref=e.target.value.toUpperCase();});
  const bInp=_inp('Bobines/carton — ex. 12',{type:'number',style:{width:'130px'}}); bInp.addEventListener('input',e=>{_bpc=e.target.value;});
  const eInp=_inp('Étiquettes/bobine — ex. 500',{type:'number',style:{width:'160px'}}); eInp.addEventListener('input',e=>{_epb=e.target.value;});
  const btn=el('button',{cls:'traca-print-btn',style:{width:'100%',marginTop:'12px',justifyContent:'center'}},iconEl('printer',15),' Imprimer');
  btn.addEventListener('click',doPrint);
  return el('div',null,
    el('div',{cls:'etiq-form-field'},el('label',{cls:'etiq-form-label'},'Référence produit *'),rInp),
    el('div',{cls:'etiq-form-row'},
      el('div',{cls:'etiq-form-field'},el('label',{cls:'etiq-form-label'},'Bobines / carton'),bInp),
      el('div',{cls:'etiq-form-field'},el('label',{cls:'etiq-form-label'},'Étiquettes / bobine'),eInp)),
    btn);
}

// ── 7. Cohésio 1 & 2 — Identification bobine (40×20 ou 40×30) ────
function buildIdBobineForm() {
  let _ref='', _epb='', _fmt='40x20';
  function doPrint() {
    const ref=_ref.trim(), epb=_epb.trim();
    if(!ref){showToast('Référence requise','error');return;}
    const [pw, ph] = _fmt==='40x30' ? ['40mm','30mm'] : ['40mm','20mm'];
    const fsRef = _fmt==='40x30' ? '10pt' : '8pt';
    const fsCond = _fmt==='40x30' ? '9pt' : '7pt';
    _printWin('Bobine — '+ref,`${pw} ${ph}`,
      `.label{width:${pw};height:${ph};padding:1.5mm 2mm;display:flex;flex-direction:column;justify-content:space-between;page-break-after:always;page-break-inside:avoid}
       .ref{font-size:${fsRef};font-weight:900;word-break:break-all;line-height:1.2}
       .cond{font-size:${fsCond};font-weight:600;color:#333}`,
      `<div class="label"><div class="ref">${ref}</div>${epb?`<div class="cond">${epb} étiq/bob</div>`:''}</div>`);
  }
  const rInp=_inp('Référence — ex. 1077/0026'); rInp.addEventListener('input',e=>{_ref=e.target.value.toUpperCase();});
  const eInp=_inp('Étiquettes/bobine — ex. 500',{type:'number',style:{width:'170px'}}); eInp.addEventListener('input',e=>{_epb=e.target.value;});
  // Sélecteur format
  const fmtSel = el('select',{cls:'field-input',style:{width:'140px'}},
    el('option',{attrs:{value:'40x20',selected:'true'}},'40 × 20 mm'),
    el('option',{attrs:{value:'40x30'}},'40 × 30 mm'));
  fmtSel.addEventListener('change',e=>{_fmt=e.target.value;});
  const btn=el('button',{cls:'traca-print-btn',style:{width:'100%',marginTop:'12px',justifyContent:'center'}},iconEl('printer',15),' Imprimer');
  btn.addEventListener('click',doPrint);
  return el('div',null,
    el('div',{cls:'etiq-form-field'},el('label',{cls:'etiq-form-label'},'Référence produit *'),rInp),
    el('div',{cls:'etiq-form-row'},
      el('div',{cls:'etiq-form-field'},el('label',{cls:'etiq-form-label'},'Étiquettes / bobine'),eInp),
      el('div',{cls:'etiq-form-field'},el('label',{cls:'etiq-form-label'},'Format'),fmtSel)),
    btn);
}

function openTracaPrint(etiq) {
  const overlay = el('div', { cls:'modal-overlay', on:{ click:e=>{ if(e.target===overlay){ overlay.remove(); } } } });
  const fmtObj = TRACA_FORMATS.find(f=>f.id===etiq.format)||{label:etiq.format,dims:''};

  const formBuilders = {
    id_palette_a4:    buildIdPaletteA4Form,
    nb_palettes_logi: buildNbPalettesLogiForm,
    id_plaque:        buildIdPlaqueForm,
    id_cliche:        buildIdClicheForm,
    nb_palettes_c:    buildNbPalettesCForm,
    id_carton:        buildIdCartonForm,
    id_bobine:        buildIdBobineForm,
  };
  const builder = formBuilders[etiq.id];
  const formContent = builder ? builder() : el('div',{cls:'traca-dev-banner'},iconEl('settings',14),' À venir.');

  const sheet = el('div', { cls:'modal-sheet' },
    el('span',{cls:'modal-handle'}),
    el('div',{cls:'modal-title'}, iconEl('printer',17), '\u00a0'+etiq.label),
    el('div',{cls:'modal-sub'}, 'Format\u00a0: ', el('strong',null,fmtObj.label+' ('+fmtObj.dims+')')),
    formContent,
    el('button',{cls:'btn-ghost',style:{width:'100%',marginTop:'10px'},on:{click:()=>overlay.remove()}},'Fermer')
  );
  overlay.appendChild(sheet);
  document.body.appendChild(overlay);
}

function buildTracaPosteView(poste) {
  const etiquettes = TRACA_ETIQUETTES.filter(e=>e.postes.includes(poste.id));
  const backBar = el('div',{cls:'traca-back-bar'},
    el('button',{cls:'traca-back-btn',on:{click:()=>{ S.tracaPoste=null; renderContent(); }}},
      iconEl('arrow-left',15), ' Postes'),
    el('span',{cls:'traca-poste-heading'}, poste.label)
  );
  let listEl;
  if (etiquettes.length===0) {
    listEl = el('div',{cls:'card'},el('div',{cls:'card-empty'},'Aucune étiquette configurée pour ce poste.'));
  } else {
    const cards = etiquettes.map(etiq=>{
      const fmtObj = TRACA_FORMATS.find(f=>f.id===etiq.format)||{label:etiq.format,dims:''};
      const card = el('div',{cls:'traca-etiq-card'},
        el('div',{cls:'traca-etiq-icon-wrap',style:{background:poste.colorBg,color:poste.color}},
          iconEl('tag',18)),
        el('div',{cls:'traca-etiq-body'},
          el('div',{cls:'traca-etiq-label'},etiq.label),
          el('div',{cls:'traca-etiq-meta'},
            el('span',{cls:'traca-format-badge'},fmtObj.label),
            el('span',{cls:'traca-printer-badge'},
              iconEl('printer',10),
              '\u00a0'+(etiq.printer||'Non configurée'))
          )
        ),
        el('button',{cls:'traca-print-btn',on:{click:()=>openTracaPrint(etiq)}},
          iconEl('printer',13),' Imprimer')
      );
      return card;
    });
    listEl = el('div',{cls:'traca-etiq-list'},...cards);
  }
  return el('div',{cls:'content'}, backBar, listEl);
}

function buildTraca() {
  if (S.tracaPoste) {
    const poste = TRACA_POSTES.find(p=>p.id===S.tracaPoste);
    if (poste) return buildTracaPosteView(poste);
  }
  // Vue sélection poste
  const cards = TRACA_POSTES.map(poste=>{
    const count = TRACA_ETIQUETTES.filter(e=>e.postes.includes(poste.id)).length;
    const card = el('div',{cls:'traca-poste-card',on:{click:()=>{ S.tracaPoste=poste.id; renderContent(); }}},
      el('div',{cls:'traca-poste-icon',style:{background:poste.colorBg,color:poste.color}},
        iconEl(poste.icon,22)),
      el('div',{cls:'traca-poste-label'},poste.label),
      el('div',{cls:'traca-poste-count'},count+' étiquette'+(count>1?'s':''))
    );
    return card;
  });
  return el('div',{cls:'content'},
    el('div',{cls:'traca-section-title'},'Sélectionner un poste de travail'),
    el('div',{cls:'traca-postes-grid'},...cards)
  );
}

function buildInventaire() {
  const isSuperAdmin = S.user && S.user.role === 'superadmin';

  // Utilisateurs non-superadmin : page "en cours de développement"
  if (!isSuperAdmin) {
    return el('div',{cls:'content'},
      el('div',{cls:'card'},
        el('div',{cls:'wip-page'},
          el('div',{cls:'wip-page-icon'},'🚧'),
          el('div',{cls:'wip-page-title'},'En cours de développement'),
          el('div',{cls:'wip-page-sub'},"Cette fonctionnalité sera bientôt disponible.")
        )
      )
    );
  }

  // Superadmin : bannière avertissement + contenu normal
  const list = S.inventaireList||[];
  return el('div',{cls:'content'},
    el('div',{cls:'wip-admin-banner'},
      '⚠️ Attention — cet onglet est en cours de développement pour les autres utilisateurs.'
    ),
    el('div',{cls:'card',style:{marginBottom:'12px'}},
      el('div',{cls:'card-header'},
        el('div',{cls:'card-title'},'⚠ À inventorier ('+list.length+')'),
        el('button',{cls:'btn-sm',on:{click:()=>loadInventaireList()}}, iconEl('refresh-ccw',14), ' Rafraîchir')
      ),
      el('div',{style:{padding:'10px 16px 12px',fontSize:'12px',color:'var(--muted)'}},'Non inventoriés depuis plus de 6 mois. Cliquez pour inventorier.')
    ),
    list.length===0
      ? el('div',{cls:'card'},el('div',{cls:'card-empty'},'✅ Tous les stocks ont été inventoriés récemment'))
      : el('div',{cls:'card'},el('div',null,...list.slice(0,50).map(item=>{
          const j=item.jours_depuis;
          const cls=j>365?'urgent':'attention';
          return el('div',{cls:'inv-item',on:{click:()=>openMvtModal(item.id,item.reference,item.emplacement,'inventaire')}},
            el('div',{cls:'inv-dot '+cls}),
            el('div',{cls:'inv-label'},el('div',{cls:'inv-ref'},item.reference),el('div',{cls:'inv-empl'},item.emplacement+' · '+fN(item.quantite)+' '+item.unite)),
            el('div',{cls:'inv-days '+cls},j===9999?'Jamais':j+'j')
          );
        })))
  );
}

function renderContent() {
  const area = document.getElementById('scroll-area');
  if (!area) return;
  area.innerHTML = '';

  let content;
  if (S.selProduit) content = buildProduitDetail();
  else if (S.selEmpl) content = buildEmplacementDetail();
  else if (S.tab === 'dashboard') content = buildDashboard();
  else if (S.tab === 'matieres') {
    content = buildMatieres();
  }
  else if (S.tab === 'referentiel') content = buildReferentielPage();
  else if (S.tab === 'inventaire') content = buildInventaire();
  else if (S.tab === 'traca') content = buildTraca();
  else if (S.tab === 'reception') content = buildReception();
  else if (S.tab === 'historique') content = buildHistorique();
  else content = buildDashboard();

  if (content) area.appendChild(content);
}

// ── Réception matière ───────────────────────────────────────────

const FSC_CLAIM_LABELS = {
  non_fsc: 'Non FSC',
  fsc_100: 'FSC 100%',
  fsc_mix_credit: 'FSC Mix Credit',
  fsc_mix: 'FSC Mix',
  fsc_recycled: 'FSC Recycled',
};

function fscClaimBadge(claim) {
  const c = (claim || 'non_fsc').trim();
  const label = FSC_CLAIM_LABELS[c] || c;
  let bg = 'rgba(148,163,184,.12)';
  let color = 'var(--muted)';
  if (c === 'fsc_100') {
    bg = 'rgba(52,211,153,.12)';
    color = 'var(--success)';
  } else if (c === 'fsc_recycled' || c.startsWith('fsc_mix')) {
    bg = 'var(--accent-bg)';
    color = 'var(--accent)';
  }
  return el('span', {
    title: 'Type de certification FSC',
    style: {
      background: bg,
      color,
      padding: '2px 8px',
      borderRadius: '6px',
      fontSize: '11px',
      fontWeight: '600',
      flexShrink: '0',
    },
  }, label);
}

function recepFscTypeRequiresCert(claim) {
  return (claim || 'non_fsc') !== 'non_fsc';
}

async function loadRecepHistory() {
  S.recepHistLoading = true; renderContent();
  try {
    const d = await api('/api/stock/receptions?limit=50');
    if (d) S.recepHistory = d.receptions || [];
  } catch(e) { showToast('Erreur chargement historique : ' + e.message, 'error'); }
  S.recepHistLoading = false; renderContent();
}

function recepAddCode(code) {
  const c = (code || '').trim();
  if (!c) return;
  // Doublon dans la session en cours → juste signaler, on ajoute quand même (deux bobines peuvent avoir le même code dans des cas rares)
  const isDup = S.recepItems.some(i => i.code === c);
  const now = new Date();
  const ts = String(now.getHours()).padStart(2,'0') + ':' + String(now.getMinutes()).padStart(2,'0') + ':' + String(now.getSeconds()).padStart(2,'0');
  S.recepItems = [...S.recepItems, { code: c, ts, isNew: true, isDup }];
  // Effacer le flag "nouveau" après 600ms (animation CSS)
  setTimeout(() => {
    S.recepItems = S.recepItems.map(i => i.code === c ? { ...i, isNew: false } : i);
    renderContent();
  }, 600);
  renderContent();
}

// ── ZXing Loader ─────────────────────────────────────────────────
async function loadZXing() {
  if (typeof ZXing !== 'undefined') return true;
  return new Promise((resolve) => {
    const s = document.createElement('script');
    s.src = 'https://cdn.jsdelivr.net/npm/@zxing/library@0.19.1/umd/index.min.js';
    s.onload = () => resolve(true);
    s.onerror = () => { showToast('Erreur chargement scanner', 'error'); resolve(false); };
    document.head.appendChild(s);
  });
}

let _recepLastCode = null;
let _recepLastCodeTs = 0;

// Détection plateforme
const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
const isAndroid = /Android/.test(navigator.userAgent);

// Helper pour trouver la caméra arrière
async function getBackCameraDeviceId() {
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const videoDevices = devices.filter(d => d.kind === 'videoinput');
    console.log('[Scan] Périphériques vidéo trouvés:', videoDevices.map(d => d.label));

    // Chercher une caméra arrière
    const backCamera = videoDevices.find(d => {
      const label = d.label.toLowerCase();
      return label.includes('back') || label.includes('rear') || label.includes('environment') || label.includes('arrière');
    });

    if (backCamera) {
      console.log('[Scan] Caméra arrière trouvée:', backCamera.label, 'ID:', backCamera.deviceId);
      return backCamera.deviceId;
    }

    // Fallback: première caméra
    console.log('[Scan] Utilisation première caméra disponible');
    return videoDevices[0]?.deviceId || null;
  } catch(e) {
    console.error('[Scan] Erreur enumerateDevices:', e);
    return null;
  }
}

async function recepStartCamera() {
  if (S.recepScanning) return;
  S.recepScanning = true;

  // Overlay créé en premier (synchrone) — le geste utilisateur est encore actif
  const overlay = el('div', { cls: 'camera-modal recep-overlay' });
  const wrap = el('div', { cls: 'camera-wrap' });
  const video = el('video', { cls: 'camera-video', autoplay: '', playsinline: '' });
  const frame = el('div', { cls: 'camera-frame' });
  wrap.append(video, frame);
  const hint = el('p', { cls: 'camera-hint' }, 'Pointez vers le code-barres de la bobine');
  const resultEl = el('div', { cls: 'camera-result' }, 'En attente…');
  const closeBtn = el('button', { cls: 'btn-close-cam', on: { click: () => recepStopCamera(overlay) } }, '✕ Fermer');
  overlay.append(wrap, hint, resultEl, closeBtn);
  document.body.appendChild(overlay);

  try {
    // getUserMedia est le PREMIER await — Android refuse silencieusement si on a fait
    // un await long (chargement ZXing CDN) avant : le "user gesture token" est expiré
    if (!navigator.mediaDevices?.getUserMedia) throw new Error('Caméra non disponible (page non HTTPS ?)');
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } }
    });
    S.recepStream = stream;
    video.srcObject = stream;

    // Stratégie de décodage selon la plateforme :
    // Android Chrome 83+ → BarcodeDetector (Google ML Kit natif) : gère nativement l'autofocus
    //   et les codes 1D fins. ZXing JS ne peut pas rivaliser avec le moteur natif de l'OS.
    // iOS + fallback Android → ZXing (BarcodeDetector absent sur Safari)
    const useNativeDetector = isAndroid && ('BarcodeDetector' in window);

    // Délai de latence avant activation — évite les scans parasites au démarrage
    const RECEP_SCAN_DELAY_MS = 1500;
    const recepScanStartTime = Date.now();
    resultEl.textContent = 'Positionnez-vous devant le code…';
    setTimeout(() => { if (S.recepScanning) resultEl.textContent = 'En attente…'; }, RECEP_SCAN_DELAY_MS);

    // Callback partagé — arrêt IMMÉDIAT des deux moteurs dès détection
    // (évite que ZXing continue d'appeler le callback pendant le délai d'animation)
    let recepDetected = false;
    const onRecepCode = (code) => {
      if (Date.now() - recepScanStartTime < RECEP_SCAN_DELAY_MS) return;
      if (recepDetected) return;
      recepDetected = true;
      // Stopper tout immédiatement — plus aucun callback possible après ça
      S.recepScanning = false;
      if (S.recepBarcodeReader) { try { S.recepBarcodeReader.reset(); } catch(e) {} S.recepBarcodeReader = null; }
      if (S.recepStream) { S.recepStream.getTracks().forEach(t => t.stop()); S.recepStream = null; }
      resultEl.textContent = '✅ ' + code;
      resultEl.style.color = 'var(--success)';
      // Garder l'overlay 600ms pour l'animation, puis fermer et ajouter
      setTimeout(() => { overlay.remove(); recepAddCode(code); }, 600);
    };

    // ZXing nécessaire sur iOS et pour QR codes sur Android
    if (typeof ZXing === 'undefined') {
      resultEl.textContent = 'Chargement scanner…';
      await new Promise((res, rej) => {
        const s = document.createElement('script');
        s.src = 'https://cdn.jsdelivr.net/npm/@zxing/library@0.19.1/umd/index.min.js';
        s.onload = res; s.onerror = rej; document.head.appendChild(s);
      });
      resultEl.textContent = 'En attente…';
    }

    if (useNativeDetector) {
      // ── Android : BarcodeDetector (codes 1D) + ZXing decodeFromStream (QR) ──────
      const qrHints = new Map();
      qrHints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS, [ZXing.BarcodeFormat.QR_CODE]);
      qrHints.set(ZXing.DecodeHintType.TRY_HARDER, true);
      const qrReader = new ZXing.BrowserMultiFormatReader(qrHints);
      S.recepBarcodeReader = qrReader;

      // Moteur 1 : BarcodeDetector pour codes 1D (ML Kit natif, autofocus natif)
      const detector = new BarcodeDetector({
        formats: ['code_128', 'ean_13', 'ean_8', 'data_matrix', 'code_39', 'upc_a', 'upc_e']
      });
      const barcodeLoop = async () => {
        if (!S.recepScanning) return;
        if (video.readyState < 2 || !video.videoWidth) { setTimeout(barcodeLoop, 100); return; }
        try {
          const found = await detector.detect(video);
          if (found.length > 0) { onRecepCode(found[0].rawValue); return; }
        } catch(e) {}
        if (S.recepScanning) setTimeout(barcodeLoop, 150);
      };
      setTimeout(barcodeLoop, 500);

      // Moteur 2 : ZXing decodeFromStream pour QR codes
      // decodeFromStream est la seule méthode ZXing qui fonctionne pour les QR sur Android
      // (drawImage canvas ne capture pas correctement les frames live sur certains Android Chrome)
      // Le double scan est évité par l'arrêt immédiat dans onRecepCode (reader.reset() + stream stop)
      qrReader.decodeFromStream(stream, video, (result) => {
        if (result) onRecepCode(result.getText().trim());
      });

    } else {
      // ── iOS + fallback : ZXing canvas loop tous formats ──────────────────────────
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d', { willReadFrequently: true });
      const hints = new Map();
      hints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS, [
        ZXing.BarcodeFormat.CODE_128, ZXing.BarcodeFormat.EAN_13, ZXing.BarcodeFormat.EAN_8,
        ZXing.BarcodeFormat.QR_CODE, ZXing.BarcodeFormat.DATA_MATRIX, ZXing.BarcodeFormat.CODE_39
      ]);
      hints.set(ZXing.DecodeHintType.TRY_HARDER, true);
      const reader = new ZXing.BrowserMultiFormatReader(hints);
      S.recepBarcodeReader = reader;
      const loop = () => {
        if (!S.recepScanning) return;
        if (video.readyState < 2 || !video.videoWidth) { setTimeout(loop, 100); return; }
        try {
          canvas.width = video.videoWidth; canvas.height = video.videoHeight;
          ctx.drawImage(video, 0, 0);
          const img = ctx.getImageData(0, 0, canvas.width, canvas.height);
          const lum = new ZXing.RGBLuminanceSource(img.data, canvas.width, canvas.height);
          const bmp = new ZXing.BinaryBitmap(new ZXing.HybridBinarizer(lum));
          const result = reader.decode(bmp);
          if (result) { onRecepCode(result.getText().trim()); return; }
        } catch(e) {}
        if (S.recepScanning) setTimeout(loop, 150);
      };
      setTimeout(loop, 400);
    }
  } catch(e) {
    showToast(e.message.includes('HTTPS') ? e.message : 'Accès caméra refusé', 'error');
    recepStopCamera(overlay);
  }
}

function recepStopCamera(overlay) {
  if (S.recepStream) { S.recepStream.getTracks().forEach(t => t.stop()); S.recepStream = null; }
  if (S.recepBarcodeReader) { try { S.recepBarcodeReader.reset(); } catch(e) {} S.recepBarcodeReader = null; }
  S.recepScanning = false;
  // Retirer l'overlay du body (passé en paramètre ou recherche de secours)
  if (overlay) { overlay.remove(); } else { document.querySelector('.camera-modal.recep-overlay')?.remove(); }
}

async function recepValider() {
  if (!S.recepItems.length) return;
  if (!S.recepFournisseur) {
    showToast('Veuillez sélectionner un fournisseur avant de valider la réception', 'error');
    return;
  }
  const claim = S.recepFscTypeClaim || 'fsc_mix';
  const fsc = FOURNISSEURS_FSC.find(f => f.nom === S.recepFournisseur);
  const cert = fsc ? String(fsc.certificat || '').trim() : '';
  if (recepFscTypeRequiresCert(claim) && !cert) {
    showToast('Certificat FSC requis pour une réception certifiée FSC.', 'error');
    return;
  }
  try {
    const codes = S.recepItems.map(i => i.code);
    const d = await api('/api/stock/receptions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        codes,
        note: S.recepNote,
        fournisseur: S.recepFournisseur,
        certificat_fsc: recepFscTypeRequiresCert(claim) ? cert : '',
        fsc_type_claim: claim,
      }),
    });
    if (d && d.success) {
      showToast(d.nb_bobines + ' bobine' + (d.nb_bobines > 1 ? 's' : '') + ' enregistrée' + (d.nb_bobines > 1 ? 's' : ''));
      S.recepItems = []; S.recepNote = ''; S.recepFournisseur = ''; S.recepFournisseurSearch = ''; S.recepFournisseurOpen = false;
      S.recepFscTypeClaim = 'fsc_mix';
      recepStopCamera();
      await loadRecepHistory();
    }
  } catch(e) { showToast('Erreur : ' + e.message, 'error'); }
}

function buildReception() {
  const wrap = el('div', { cls: 'recep-page' });

  const tracaGuideBtn = el('button', {
    type: 'button',
    style: {
      display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', borderRadius: '6px',
      border: '1.5px solid #fb923c', background: 'rgba(251,146,60,.10)', color: '#fb923c',
      fontSize: '12px', fontWeight: '600', cursor: 'pointer', fontFamily: 'inherit', whiteSpace: 'nowrap',
      flexShrink: '0', alignSelf: 'flex-start',
    },
    on: {
      mouseenter: (e) => { e.currentTarget.style.opacity = '0.75'; },
      mouseleave: (e) => { e.currentTarget.style.opacity = '1'; },
      click: () => {
        const f = FOURNISSEURS_FSC.find((x) => x.nom === S.recepFournisseur);
        if (typeof showTracaGuide === 'function') {
          showTracaGuide(f ? f.id : null, S.recepFournisseur || '', FOURNISSEURS_FSC);
        }
      },
    },
  }, iconEl('scan', 12), ' Quel code scanner ?');

  wrap.appendChild(el('div', { cls: 'recep-head-row' },
    el('div', { cls: 'recep-title' }, 'Réception ', el('span', null, 'matière')),
    tracaGuideBtn
  ));

  // ── Grille scanner + saisie manuelle ──
  const grid = el('div', { cls: 'recep-layout' });

  // Colonne gauche : caméra
  const camCard = el('div', { cls: 'recep-card' },
    el('div', { cls: 'recep-card-title' }, iconEl('scan', 14), ' Scanner une bobine')
  );

  // L'overlay caméra est géré par recepStartCamera() directement sur document.body
  // — pas besoin d'un état S.recepScanning dans l'UI de la card
  const placeholder = el('div', { cls: 'recep-cam-placeholder' },
    iconEl('scan', 40),
    el('div', null, 'Appuyez sur "Démarrer" pour activer la caméra')
  );
  camCard.appendChild(placeholder);
  camCard.appendChild(el('button', { cls: 'btn-recep btn-recep-primary', on: { click: recepStartCamera } }, iconEl('scan', 14), ' Démarrer le scan'));
  grid.appendChild(camCard);

  // Colonne droite : saisie manuelle + note
  const manCard = el('div', { cls: 'recep-card' },
    el('div', { cls: 'recep-card-title' }, iconEl('tag', 14), ' Saisie manuelle'),
    el('div', { style: { fontSize: '11px', color: 'var(--muted)', marginBottom: '2px' } }, 'Saisissez ou collez un code-barres puis appuyez sur Entrée'),
    (() => {
      const wrap2 = el('div', { cls: 'recep-manual-wrap' });
      const inp = el('input', { cls: 'recep-manual-inp', attrs: { type: 'text', placeholder: 'Ex: 3700123456789', autocomplete: 'off', autocorrect: 'off', spellcheck: 'false' } });
      inp.value = S.recepManual || '';
      inp.addEventListener('input', e => { S.recepManual = e.target.value; });
      inp.addEventListener('keydown', e => {
        if (e.key === 'Enter') {
          e.preventDefault();
          if (S.recepManual.trim()) { recepAddCode(S.recepManual); S.recepManual = ''; inp.value = ''; inp.focus(); }
        }
      });
      const btn = el('button', { cls: 'btn-recep btn-recep-ghost', on: { click: () => {
        if (S.recepManual.trim()) { recepAddCode(S.recepManual); S.recepManual = ''; inp.value = ''; inp.focus(); }
      }}}, '+ Ajouter');
      wrap2.append(inp, btn);
      return wrap2;
    })(),
    el('div', { cls: 'recep-card-title', style: { marginTop: '8px' } }, iconEl('inbox', 14), ' Note (optionnel)'),
    (() => {
      const inp = el('input', { cls: 'recep-note-inp', attrs: { type: 'text', placeholder: 'Ex: Livraison fournisseur X, bon de livraison 123…' } });
      inp.value = S.recepNote || '';
      inp.addEventListener('input', e => { S.recepNote = e.target.value; });
      return inp;
    })()
  );
  grid.appendChild(manCard);
  wrap.appendChild(grid);

  // ── Tableau bobines scannées ──
  const tableCard = el('div', { cls: 'recep-card' });
  const tableHead = el('div', { style: { display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' } },
    el('div', { cls: 'recep-card-title', style: { flex: '1' } }, iconEl('package', 14), ' Bobines scannées'),
    el('div', { cls: 'recep-count' }, 'Total : ', el('strong', null, String(S.recepItems.length)), ' bobine' + (S.recepItems.length !== 1 ? 's' : ''))
  );
  tableCard.appendChild(tableHead);

  // ── Fournisseur puis type FSC (même style champs MySifa) ──
  const fourWrap = el('div', { cls: 'recep-fourn-wrap' });

  const fourLabel = el('div', { cls: 'recep-fourn-label' }, iconEl('truck', 13), ' Fournisseur', el('span', { style: { color: 'var(--danger)', marginLeft: '4px' } }, '*'));
  fourWrap.appendChild(fourLabel);
  const fourSearchWrap = el('div', { cls: 'recep-fourn-search-wrap' });
  const fourInp = el('input', {
    cls: 'recep-fourn-inp' + (S.recepFournisseur ? ' recep-fourn-selected' : ''),
    attrs: {
      type: 'text',
      placeholder: 'Rechercher un fournisseur…',
      autocomplete: 'off',
      autocorrect: 'off',
      spellcheck: 'false',
    },
  });
  const dropdown = el('div', { cls: 'recep-fourn-dropdown' });

  // Helper: update dropdown content without destroying the input
  function updateFourDropdown(query) {
    dropdown.innerHTML = '';
    dropdown.classList.add('open');
    const suggestions = query ? fournisseurSuggestions(query) : [];
    if (suggestions.length > 0) {
      suggestions.forEach(f => {
        const item = el('div', { cls: 'recep-fourn-item', on: { mousedown: (e) => {
          e.preventDefault(); // évite blur avant click
          S.recepFournisseur = f.nom;
          S.recepFournisseurSearch = '';
          S.recepFournisseurOpen = false;
          renderContent(); // full re-render only on selection
        }}},
          el('span', { cls: 'recep-fourn-item-nom' }, f.nom),
          el('span', { cls: 'recep-fourn-item-cert' }, f.certificat)
        );
        dropdown.appendChild(item);
      });
    } else if (query) {
      dropdown.appendChild(el('div', { cls: 'recep-fourn-empty' }, 'Aucun fournisseur trouvé'));
    } else {
      dropdown.classList.remove('open');
    }
  }

  if (S.recepFournisseur) {
    // Afficher le fournisseur sélectionné + bouton pour changer
    fourInp.value = S.recepFournisseur;
    fourInp.setAttribute('readonly', 'true');
    const clearBtn = el('button', { cls: 'recep-fourn-clear', on: { click: (e) => {
      e.stopPropagation();
      S.recepFournisseur = ''; S.recepFournisseurSearch = ''; S.recepFournisseurOpen = false;
      renderContent();
      setTimeout(() => { const i = document.querySelector('.recep-fourn-inp:not([readonly])'); if (i) i.focus(); }, 50);
    }}}, '✕');
    fourSearchWrap.append(fourInp, clearBtn);
  } else {
    fourInp.value = S.recepFournisseurSearch || '';
    fourSearchWrap.append(fourInp, dropdown);
    // Events sur l'input — DOM patching, NO renderContent
    fourInp.addEventListener('input', (e) => {
      S.recepFournisseurSearch = e.target.value;
      S.recepFournisseurOpen = true;
      updateFourDropdown(e.target.value);
    });
    fourInp.addEventListener('focus', () => {
      S.recepFournisseurOpen = true;
      if (S.recepFournisseurSearch) updateFourDropdown(S.recepFournisseurSearch);
    });
    fourInp.addEventListener('blur', () => {
      setTimeout(() => { dropdown.classList.remove('open'); S.recepFournisseurOpen = false; }, 200);
    });
  }
  fourWrap.appendChild(fourSearchWrap);
  // Afficher le certificat FSC si fournisseur sélectionné et claim FSC
  if (S.recepFournisseur && recepFscTypeRequiresCert(S.recepFscTypeClaim)) {
    const fsc = FOURNISSEURS_FSC.find(f => f.nom === S.recepFournisseur);
    const certTxt = fsc && fsc.certificat ? fsc.certificat : '—';
    const certBlock = el('div', { cls: 'recep-fourn-fsc' },
      'Certificat FSC : ',
      el('strong', null, certTxt)
    );
    if (fsc && fsc.licence) {
      certBlock.appendChild(document.createTextNode(' — Licence : '));
      certBlock.appendChild(el('strong', null, fsc.licence));
    }
    if (!fsc || !String(fsc.certificat || '').trim()) {
      certBlock.appendChild(el('span', { style: { color: 'var(--danger)', marginLeft: '8px', fontSize: '12px' } }, 'Certificat manquant pour ce fournisseur'));
    }
    fourWrap.appendChild(certBlock);
  }

  const fscClaim = S.recepFscTypeClaim || 'fsc_mix';
  const fscTypeLbl = el('div', { cls: 'recep-fourn-label', style: { marginTop: '4px' } }, iconEl('clipboard', 13), ' Type de certification FSC');
  const fscTypeSel = el('select', {
    cls: 'recep-fourn-sel',
    attrs: { id: 'fsc-type-claim' },
    on: {
      mousedown: () => {
        // Fermer le dropdown fournisseur avant l'ouverture du select (sinon il capte le clic).
        try { dropdown.classList.remove('open'); } catch(e) {}
        S.recepFournisseurOpen = false;
      },
      focus: () => {
        try { dropdown.classList.remove('open'); } catch(e) {}
        S.recepFournisseurOpen = false;
      },
      change: (e) => {
        S.recepFscTypeClaim = e.target.value;
        renderContent();
      },
    },
  },
    el('option', { attrs: { value: 'non_fsc', selected: fscClaim === 'non_fsc' } }, 'Non FSC'),
    el('option', { attrs: { value: 'fsc_100', selected: fscClaim === 'fsc_100' } }, 'FSC 100%'),
    el('option', { attrs: { value: 'fsc_mix_credit', selected: fscClaim === 'fsc_mix_credit' } }, 'FSC Mix Credit'),
    el('option', { attrs: { value: 'fsc_mix', selected: fscClaim === 'fsc_mix' } }, 'FSC Mix'),
    el('option', { attrs: { value: 'fsc_recycled', selected: fscClaim === 'fsc_recycled' } }, 'FSC Recycled')
  );
  fourWrap.append(fscTypeLbl, fscTypeSel);

  tableCard.appendChild(fourWrap);

  if (S.recepItems.length === 0) {
    tableCard.appendChild(el('div', { cls: 'recep-empty' }, 'Aucune bobine scannée — commencez par activer le scan ou saisissez un code manuellement'));
  } else {
    const tableWrap = el('div', { cls: 'recep-table-wrap' });
    const table = el('table', { cls: 'recep-table' });
    table.appendChild(el('thead', null, el('tr', null,
      el('th', null, '#'),
      el('th', null, 'Code-barres'),
      el('th', null, 'Heure'),
      el('th', null, '')
    )));
    const tbody = el('tbody');
    S.recepItems.forEach((item, i) => {
      const tr = el('tr', { cls: item.isNew ? 'recep-row-new' : '' },
        el('td', null, String(i + 1)),
        el('td', null,
          el('span', { cls: 'recep-code' }, item.code),
          item.isDup ? el('span', { cls: 'recep-dup-badge' }, 'doublon') : null
        ),
        el('td', null, item.ts),
        el('td', null, el('button', { cls: 'recep-del-btn', attrs: { title: 'Supprimer' }, on: { click: () => {
          S.recepItems = S.recepItems.filter((_, j) => j !== i);
          renderContent();
        }}}, '✕'))
      );
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    tableWrap.appendChild(table);
    tableCard.appendChild(tableWrap);

    // Actions
    const actions = el('div', { cls: 'recep-actions', style: { marginTop: '12px' } },
      el('button', { cls: 'btn-recep btn-recep-muted', on: { click: () => {
        if (confirm('Vider la liste des ' + S.recepItems.length + ' bobines scannées ?')) { S.recepItems = []; renderContent(); }
      }}}, '🗑 Vider la liste'),
      el('button', { cls: 'btn-recep btn-recep-success', on: { click: recepValider } },
        iconEl('check-circle', 15), ' Valider la réception (' + S.recepItems.length + ')')
    );
    tableCard.appendChild(actions);
  }
  wrap.appendChild(tableCard);

  // ── Historique ──
  const hist = el('div', { cls: 'recep-hist' });
  hist.appendChild(el('div', { cls: 'recep-hist-head' }, iconEl('truck', 14), ' Historique des réceptions'));

  if (S.recepHistLoading) {
    hist.appendChild(el('div', { cls: 'recep-hist-empty' }, '⏳ Chargement…'));
  } else if (!S.recepHistory.length) {
    hist.appendChild(el('div', { cls: 'recep-hist-empty' }, 'Aucune réception enregistrée'));
  } else {
    const histScroll = el('div', { cls: 'recep-hist-scroll' });
    S.recepHistory.forEach(lot => {
      const dateStr = lot.created_at ? lot.created_at.slice(0,16).replace('T', ' ') : '—';
      const isOpen = S.recepExpandedId === lot.id;
      const row = el('div', { cls: 'recep-hist-row', on: { click: () => {
        S.recepExpandedId = isOpen ? null : lot.id;
        renderContent();
      }}},
        el('span', { cls: 'recep-hist-date' }, dateStr),
        el('span', { cls: 'recep-hist-count' }, lot.nb_bobines + ' bobine' + (lot.nb_bobines !== 1 ? 's' : '')),
        fscClaimBadge(lot.fsc_type_claim),
        el('span', { cls: 'recep-hist-note' }, lot.note || ''),
        el('span', { cls: 'recep-hist-four' }, lot.fournisseur || ''),
        el('span', { cls: 'recep-hist-user' }, lot.created_by_name || '')
      );
      histScroll.appendChild(row);
      if (isOpen) {
        const detail = el('div', { cls: 'recep-hist-detail', style: { padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: '10px' } });
        if (lot.items && lot.items.length) {
          const chips = el('div', { style: { display: 'flex', flexWrap: 'wrap', gap: '6px' } });
          lot.items.forEach(code => chips.appendChild(el('span', { cls: 'recep-hist-chip' }, code)));
          detail.appendChild(chips);
        }
        if (!S.stockReadOnly) {
          const editClaim = el('select', { cls: 'form-sel', style: { maxWidth: '280px' } },
            ...Object.entries(FSC_CLAIM_LABELS).map(([v, lbl]) =>
              el('option', { attrs: { value: v, selected: (lot.fsc_type_claim || 'non_fsc') === v } }, lbl)
            )
          );
          const editFour = el('input', { cls: 'recep-note-inp', attrs: { type: 'text', placeholder: 'Fournisseur' }, style: { maxWidth: '280px' } });
          editFour.value = lot.fournisseur || '';
          const editCert = el('input', { cls: 'recep-note-inp', attrs: { type: 'text', placeholder: 'Certificat FSC' }, style: { maxWidth: '280px' } });
          editCert.value = lot.certificat_fsc || '';
          const editNote = el('input', { cls: 'recep-note-inp', attrs: { type: 'text', placeholder: 'Note' }, style: { maxWidth: '400px' } });
          editNote.value = lot.note || '';
          const saveBtn = el('button', {
            cls: 'btn-recep btn-recep-ghost',
            style: { alignSelf: 'flex-start' },
            on: {
              click: async (e) => {
                e.stopPropagation();
                const claim = editClaim.value;
                const cert = editCert.value.trim();
                if (recepFscTypeRequiresCert(claim) && !cert) {
                  showToast('Certificat FSC requis pour une réception certifiée FSC.', 'error');
                  return;
                }
                try {
                  await api('/api/stock/receptions/' + lot.id, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                      fournisseur: editFour.value.trim() || null,
                      certificat_fsc: recepFscTypeRequiresCert(claim) ? cert : '',
                      fsc_type_claim: claim,
                      note: editNote.value.trim() || null,
                    }),
                  });
                  showToast('Réception mise à jour.', 'success');
                  await loadRecepHistory();
                } catch (err) {
                  showToast('Erreur : ' + (err.message || 'mise à jour impossible'), 'error');
                }
              },
            },
          }, 'Enregistrer les modifications');
          detail.appendChild(el('div', { style: { fontSize: '11px', color: 'var(--muted)', fontWeight: '700', textTransform: 'uppercase' } }, 'Corriger la réception'));
          detail.appendChild(editClaim);
          detail.appendChild(editFour);
          detail.appendChild(editCert);
          detail.appendChild(editNote);
          detail.appendChild(saveBtn);
        }
        histScroll.appendChild(detail);
      }
    });
    hist.appendChild(histScroll);
  }
  wrap.appendChild(hist);
  return wrap;
}

const STOCK_TAB_DOC_TITLES = {
  dashboard: 'Tableau de bord — MyStock — MySifa',
  matieres: 'Matières premières — MyStock — MySifa',
  referentiel: 'Référentiel — MyStock — MySifa',
  inventaire: 'Inventaire — MyStock — MySifa',
  reception: 'Réception matière — MyStock — MySifa',
  historique: 'Historique — MyStock — MySifa',
  traca: 'Étiquettes traça — MyStock — MySifa',
};

const STOCK_TAB_MOBILE_TITLES = {
  dashboard: 'Tableau de bord',
  matieres: 'Matières premières',
  referentiel: 'Référentiel',
  inventaire: 'Inventaire',
  reception: 'Réception matière',
  historique: 'Historique',
  traca: 'Étiquettes traça',
};

function stockMobileTabTitle() {
  if (S.selProduit || S.selEmpl) return 'Stock';
  return STOCK_TAB_MOBILE_TITLES[S.tab] || 'MyStock';
}

function buildSidebarNavStructure() {
  if (S.tracaOnly) {
    return [{ kind: 'btn', tab: 'traca', icon: 'printer', label: 'Étiquettes traça' }];
  }
  const items = [
    { kind: 'btn', tab: 'dashboard', icon: 'grid', label: 'Tableau de bord' },
    { kind: 'sep', label: 'Matières premières' },
    { kind: 'btn', tab: 'matieres', icon: 'layers', label: 'Matières premières' },
    { kind: 'btn', tab: 'reception', icon: 'inbox', label: 'Réception matière' },
    { kind: 'sep', label: 'Produits' },
    { kind: 'btn', tab: 'referentiel', icon: 'tag', label: 'Référentiel' },
  ];
  if (!S.stockReadOnly) {
    items.push({ kind: 'btn', tab: 'inventaire', icon: 'clipboard', label: 'Inventaire' });
  }
  items.push(
    { kind: 'sep', label: 'Outils' },
    { kind: 'btn', tab: 'historique', icon: 'clock', label: 'Historique mouvements' },
    { kind: 'btn', tab: 'traca', icon: 'printer', label: 'Étiquettes traça' },
  );
  return items;
}

function renderSidebarNavBtn(n) {
  const isSuperAdmin = S.user && S.user.role === 'superadmin';
  const wipBadge = n.tab === 'inventaire'
    ? el('button', { cls: 'nav-wip-badge', type: 'button', title: 'En cours de développement', on: { click: e => {
        e.stopPropagation();
        if (!isSuperAdmin) {
          showToast('🚧 En cours de développement', 'warn');
        } else {
          showToast('⚠️ Cet onglet est en cours de développement pour les autres utilisateurs', 'warn');
        }
      } } }, '🚧')
    : null;
  return el('button', { cls: 'nav-btn' + (S.tab === n.tab ? ' active' : ''), 'data-tab': n.tab, on: { click: () => goToTab(n.tab) } },
    iconEl(n.icon, 16),
    el('span', null, ' ' + n.label),
    wipBadge
  );
}

function buildStockTabPlaceholder(title) {
  return el('div', { cls: 'content' },
    el('div', { cls: 'card' },
      el('div', { cls: 'card-title' }, title),
      el('div', { cls: 'card-empty' }, 'Contenu à venir.')
    )
  );
}

function render() {
  // La modale "contact support" est montée sur <body> : il faut la synchroniser
  // avec l'état à chaque rendu pour éviter un overlay "figé" (ex: reste sur "Envoi…").
  try{
    document.querySelectorAll('.contact-modal-overlay').forEach(n=>n.remove());
    document.querySelectorAll('.unit-modal-overlay').forEach(n=>n.remove());
    document.querySelectorAll('.ref-import-modal-overlay').forEach(n=>n.remove());
  }catch(e){}

  const root = document.getElementById('root');
  root.innerHTML = '';

  const overlay = el('div', { cls:'sidebar-overlay', on:{ click: closeSidebar } });
  root.appendChild(overlay);

  const layout = el('div', { cls:'app-layout' });
  const isLight = document.body.classList.contains('light');
  const sidebar = el('div', { cls:'sidebar' },
    el('div', { cls:'sidebar-logo' },
      el('div', { cls:'logo-brand' }, 'My', el('span',null,'Stock')),
      el('div', { cls:'logo-sub' }, 'by SIFA')
    ),
    el('div', { cls:'sidebar-nav' },
      ...buildSidebarNavStructure().map(item => {
        if (item.kind === 'sep') return el('div', { cls: 'nav-section-label' }, item.label);
        return renderSidebarNavBtn(item);
      })
    ),
    el('div', { cls:'sidebar-bottom' },
      el('button', { cls:'nav-btn back-mysifa', on:{ click:()=>{ window.location.href='/'; } } },
        '← Retour ',
        el('span', { cls:'wm' }, 'My', el('span', null, 'Sifa'))
      ),
      S.user ? (window.MySifaUserChip
        ? MySifaUserChip.element(S.user, el, iconEl, { title:'Modifier mon profil' })
        : el('div', { cls:'user-chip', style:{ cursor:'pointer' }, attrs:{ title:'Modifier mon profil' }, on:{ click:()=>{ window.location.href='/profil'; } } },
            el('div', { cls:'uc-name' }, S.user.nom||''),
            el('div', { cls:'uc-role' }, ROLE_LABELS[S.user.role] || S.user.role || ''),
            el('div', { cls:'uc-profil' }, iconEl('edit',10), ' Mon profil')
          )
      ) : null,
      (() => {
        if(!S.user) return null;
        const b=el('button',{cls:'support-btn',type:'button',on:{click:()=>{S.contactOpen=true; render();}}});
        const ico=el('span',{cls:'support-ico'}); ico.innerHTML=window.MySifaSupport?.iconSvg?.()||'';
        b.append(ico, el('span',null,'Contacter le support'));
        return b;
      })(),
      el('button', { cls:'theme-btn', on:{ click:()=>{ if(window.MySifaTheme)MySifaTheme.toggleMode(); render(); } } },
        el('span', { cls:'theme-ico' }, iconEl(isLight ? 'sun' : 'moon', 16)),
        el('span', { cls:'theme-label' }, isLight ? 'Mode clair' : 'Mode sombre')
      ),      el('button', { cls:'logout-btn', on:{ click: async ()=>{ await api('/api/auth/logout',{method:'POST'}); window.location.href='/'; } } }, iconEl('log-out',14), ' Déconnexion'),
      el('div', { cls:'version' }, 'MyStock v2.1')
    )
  );

  const main = el('div', { cls:'main-area' },
    el('div', { cls:'mobile-topbar' },
      el('button', { cls:'mobile-menu-btn', on:{ click:toggleSidebar }, attrs:{ 'aria-label':'Menu', type:'button' } },
        el('span', { attrs:{ style:'display: inline-flex; align-items: center; flex-shrink: 0;' } }, iconEl('menu',20))
      ),
      el('div', null,
        el('div', { cls:'mobile-topbar-title' }, stockMobileTabTitle()),
        el('div', { cls:'mobile-topbar-sub' }, 'Inventaire, mouvements et emplacements')
      ),
      el('button', { cls:'mobile-print-btn'+(S.tab==='traca'?' active':''), on:{ click:()=>goToTab('traca') }, attrs:{ 'aria-label':'Étiquettes traça', type:'button', title:'Étiquettes traçabilité' } },
        el('span', { attrs:{ style:'display: inline-flex; align-items: center; flex-shrink: 0;' } }, iconEl('printer',20))
      ),
      el('button', { cls:'mobile-home-btn', on:{ click:()=>window.location.href='/' }, attrs:{ 'aria-label':'Accueil', type:'button' } },
        el('span', { attrs:{ style:'display: inline-flex; align-items: center; flex-shrink: 0;' } }, iconEl('home',20))
      )
    ),
    S.tracaOnly ? null : buildSearchBar(),
    el('div', { cls:'scroll-area', id:'scroll-area' })
  );

  layout.append(sidebar, main);
  root.appendChild(layout);

  document.title = STOCK_TAB_DOC_TITLES[S.tab] || 'MyStock — MySifa';

  if(S.contactOpen){
    const ov = el('div', { cls:'contact-modal-overlay', on:{ click:(e)=>{ if(e.target===ov){ S.contactOpen=false; render(); } } } });
    const box = el('div', { cls:'contact-modal' });
    box.appendChild(el('button',{cls:'contact-close',type:'button',on:{click:()=>{S.contactOpen=false; render();}}},'×'));
    box.appendChild(el('h3',null,'Contacter le support'));

    const subj = el('input',{type:'text',placeholder:'Objet (facultatif)'});
    subj.value = S.contactSubject || '';
    subj.addEventListener('input', ()=>{ S.contactSubject = subj.value; });
    box.appendChild(el('label',null,'Objet'));
    box.appendChild(subj);

    const msg = el('textarea',{placeholder:'Message *'});
    msg.value = S.contactMessage || '';
    msg.addEventListener('input', ()=>{ S.contactMessage = msg.value; });
    box.appendChild(el('label',null,'Message'));
    box.appendChild(msg);

    const actions = el('div',{cls:'contact-actions'});
    actions.appendChild(el('button',{cls:'btn-cancel',type:'button',on:{click:()=>{S.contactOpen=false; render();}}},'Annuler'));
    const send = el('button',{cls:'btn',type:'button'}, S.contactSending ? 'Envoi…' : 'Envoyer');
    send.disabled = !!S.contactSending;
    send.addEventListener('click', async ()=>{
      if(S.contactSending) return;
      const message = String(S.contactMessage||'').trim();
      const subject = String(S.contactSubject||'').trim();
      if(!message){ showToast('Message obligatoire','error'); return; }
      S.contactSending = true; render();
      try{
        await api('/api/messages/contact',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({subject,message})});
        showToast('Message envoyé au support','success');
        S.contactOpen=false; S.contactSending=false; S.contactSubject=''; S.contactMessage='';
        render();
      }catch(e){
        S.contactSending=false; render();
        showToast('Envoi impossible','error');
      }
    });
    actions.appendChild(send);
    box.appendChild(actions);
    ov.appendChild(box);
    document.body.appendChild(ov);
  }

  if(S.unitModalOpen){
    const ov=el('div',{cls:'unit-modal-overlay contact-modal-overlay',on:{click:(e)=>{ if(e.target===ov){ S.unitModalOpen=false; render(); } }}});
    const box=el('div',{cls:'contact-modal'});
    box.appendChild(el('button',{cls:'contact-close',type:'button',on:{click:()=>{S.unitModalOpen=false; render();}}},'×'));
    box.appendChild(el('h3',null,'Créer une unité de vente'));

    const lab=el('input',{type:'text',placeholder:'Libellé (ex. 500 cartons)'});
    lab.value=S.unitNewLabel||'';
    lab.addEventListener('input',()=>{S.unitNewLabel=lab.value;});
    box.appendChild(el('label',null,'Libellé *'));
    box.appendChild(lab);

    // Base: même UX que "Unité de vente" (champ + suggestions), sans option "Autre"
    const baseWrap = el('div', { cls: 'empl-combo-wrap' });
    const baseInp = el('input', { cls:'field-input', type:'text', id:'stock-page-unit-base-input',
      placeholder:'Base * (cartons, bobines, étiquettes, palettes)', autocomplete:'off', style:{direction:'ltr'} });
    const baseList = el('div', { cls:'empl-suggestions', id:'stock-page-unit-base-suggestions', style:{ display:'none' } });
    baseInp.value = String(S.unitNewBase || 'cartons');
    baseInp.addEventListener('input', ()=>{ S.unitNewBase = baseInp.value; });
    baseInp.addEventListener('focus', ()=>{ baseList.style.display='block'; refreshUnitBaseDropdown(); });
    baseInp.addEventListener('blur', ()=>{ setTimeout(()=>{ baseList.style.display='none'; }, 200); });
    baseWrap.appendChild(baseInp);
    baseWrap.appendChild(baseList);
    box.appendChild(el('label',null,'Base *'));
    box.appendChild(baseWrap);

    function refreshUnitBaseDropdown(){
      const q = String(baseInp.value||'').trim().toLowerCase();
      baseList.innerHTML='';
      let filtered = q ? STOCK_UNITS_BASE.filter(x=>String(x).toLowerCase().includes(q)) : STOCK_UNITS_BASE.slice();
      filtered.slice(0, 24).forEach(lbl=>{
        const row=document.createElement('div');
        row.className='unit-suggest-item';
        row.textContent=lbl;
        row.addEventListener('mousedown', e=>{ e.preventDefault(); baseInp.value=lbl; S.unitNewBase=lbl; baseList.style.display='none'; });
        baseList.appendChild(row);
      });
    }

    const qty=el('input',{type:'text',inputmode:'numeric',placeholder:'Quantité (ex. 500)'});
    qty.value=String(S.unitNewQty||'');
    qty.addEventListener('input',()=>{S.unitNewQty=qty.value;});
    box.appendChild(el('label',null,'Quantité *'));
    box.appendChild(qty);

    const actions=el('div',{cls:'contact-actions'});
    actions.appendChild(el('button',{cls:'btn-cancel',type:'button',on:{click:()=>{S.unitModalOpen=false; render();}}},'Annuler'));
    const create=el('button',{cls:'btn',type:'button'},'Créer');
    create.addEventListener('click',()=>{
      const l=String(S.unitNewLabel||'').trim();
      const b=String(S.unitNewBase||'cartons').trim().toLowerCase();
      const q=Number(String(S.unitNewQty||'').trim().replace(',','.'));
      const r=addPageCustomUnit(l,b,q);
      if(!r.ok){ showToast(r.reason||'Erreur','error'); return; }
      // affecte dans le champ unité si présent
      try{
        const inp=document.getElementById(ADD_PF_FIELD_IDS.unitInput);
        if(inp) inp.value=l;
      }catch(e){}
      S.unitModalOpen=false;
      render();
      showToast('Unité ajoutée : '+l,'success');
    });
    actions.appendChild(create);
    box.appendChild(actions);

    ov.appendChild(box);
    document.body.appendChild(ov);
  }

  if (S.importRefsOpen) renderImportRefsModal();

  renderContent();

  if (S.addPfModalOpen && !document.getElementById('dash-add-pf-overlay')) {
    renderDashboardAddPfModal();
  }

  // Calculette flottante (montée une seule fois, persiste entre les rendus)
  window._calc_mount && window._calc_mount();
  if(window.MySifaDock&&typeof window.MySifaDock.layout==='function')window.MySifaDock.layout();
}

async function init() {
  document.body.classList.add('has-topbar','mysifa-app-stock');
  const user = await api('/api/auth/me').catch(()=>null);
  if (user && window.MySifaTheme) MySifaTheme.mergeFromUser(user);
  if (!user) { window.location.href='/'; return; }
  S.user = user;
  window.S = S;
  window.__MYSIFA_UID__=user.id;
  window.__MYSIFA_NOM__=user.nom||'';
  window.__MYSIFA_ROLE__=user.role||'';
  window.__MYSIFA_USER__={nom:user.nom||'',role:user.role||''};
  if(window._CW&&typeof window._CW.ensureReady==='function')await window._CW.ensureReady();
  else if(window._CW&&typeof window._CW.syncUser==='function')window._CW.syncUser();
  if(typeof initAiChatWidget==='function')initAiChatWidget();
  S.stockReadOnly = (user.role === 'commercial');
  // Fabrication : accès restreint à l'onglet traça uniquement
  S.tracaOnly = (user.role === 'fabrication');
  // Charger les fournisseurs FSC
  await loadFournisseursFSC();
  // Charger la liste complète des emplacements depuis la base de données
  await fetchEmplacementsFromDB();
  // Onglet initial via URL param ?tab=...
  const urlTab = new URLSearchParams(window.location.search).get('tab');
  if (urlTab && ['dashboard','matieres','referentiel','stock','inventaire','reception','historique','traca'].includes(urlTab)) {
    S.tab = urlTab;
  }
  // Forcer traça si accès restreint
  if (S.tracaOnly) S.tab = 'traca';
  render();
  if (S.tab === 'traca') { /* rien à charger */ }
  else if (S.tab === 'reception') { await loadRecepHistory(); }
  else if (S.tab === 'inventaire') { await loadInventaireList(); }
  else if (S.tab === 'matieres') { await loadMatieres(); }
  else if (S.tab === 'historique') { await loadHistorique(); }
  else if (S.tab === 'referentiel') { await loadDashboard(); }
  else { await loadDashboard(); }
}

init();
</script>
</body>
</html>"""

STOCK_HTML = STOCK_HTML.replace("/*__TRACA_GUIDE__*/", TRACA_GUIDE_SCRIPT_BLOCK)

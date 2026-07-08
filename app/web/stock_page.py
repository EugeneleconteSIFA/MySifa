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
<link rel="icon" type="image/svg+xml" href="/static/stock_favicon.svg">
<link rel="icon" type="image/png" sizes="32x32" href="/static/stock_favicon-32.png">
<link rel="apple-touch-icon" sizes="180x180" href="/static/stock_favicon-180.png">
<link rel="manifest" href="/manifest-stock.webmanifest">
<meta name="apple-mobile-web-app-title" content="MyStock">
<link rel="stylesheet" href="/static/support_widget.css">
<link rel="stylesheet" href="/static/mysifa_theme.css">
<link rel="stylesheet" href="/static/mysifa_user_chip.css">
<link rel="stylesheet" href="/static/mysifa_ai_chat.css">
<link rel="stylesheet" href="/static/mysifa_dock.css">
<link rel="stylesheet" href="/static/mysifa_postit.css">
<link rel="stylesheet" href="/static/mysifa_cmdk.css">
<style>
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;
  --muted:#94a3b8;--accent:#22d3ee;--accent-bg:rgba(34,211,238,.12);
  --success:#34d399;--warn:#fbbf24;--danger:#f87171;--c2:#a78bfa;--violet:#8b5cf6;
  --pf-entree:#059669;--pf-sortie:#dc2626;
}
body.light{
  --bg:#f1f5f9;--card:#fff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;
  --muted:#94a3b8;--accent:#0891b2;--accent-bg:rgba(8,145,178,.10);
  --success:#059669;--warn:#d97706;--danger:#dc2626;--c2:#7c3aed;--violet:#8b5cf6;
  --pf-entree:#047857;--pf-sortie:#b91c1c;
}
html,body{height:100%}
#root{display:flex;flex:1;flex-direction:column;min-height:0}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);display:flex;flex-direction:column;min-height:100%;position:relative}
/* Fond petits points (cohérence visuelle avec MyProd + portail) */
body::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='28' height='28'%3E%3Ccircle cx='1.5' cy='1.5' r='1.2' fill='rgba(255,255,255,0.07)'/%3E%3C/svg%3E");background-size:28px 28px;background-repeat:repeat}
body.light::before{background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='28' height='28'%3E%3Ccircle cx='1.5' cy='1.5' r='1.2' fill='rgba(0,0,0,0.055)'/%3E%3C/svg%3E")}
#root{position:relative;z-index:1}::-webkit-scrollbar{width:4px;height:4px}::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px}
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
  font-weight:600;padding:10px 14px 4px 14px;user-select:none;cursor:pointer;display:flex;align-items:center;justify-content:space-between;border-radius:6px;transition:background .15s,opacity .15s}
.nav-section-label:hover{background:rgba(148,163,184,.08);opacity:1}
.nav-section-label .ngl-chevron{display:inline-flex;flex-shrink:0;transition:transform .2s;opacity:.55}
.nav-section-label.ngl-collapsed .ngl-chevron{transform:rotate(-90deg)}
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
.btn{background:var(--accent);color:var(--bg);border:none;border-radius:10px;padding:10px 20px;
  font-size:13px;font-weight:700;cursor:pointer;font-family:inherit;transition:filter .15s,box-shadow .15s,transform .05s;white-space:nowrap}
.btn:hover{filter:brightness(1.05);box-shadow:0 0 0 4px rgba(34,211,238,.18)}
.btn:active{transform:translateY(1px)}
body.light .btn{color:#fff}
.btn-ghost{background:transparent;color:var(--text2);border:1px solid var(--border);border-radius:10px;
  padding:10px 16px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;transition:all .15s}
.btn-ghost:hover{border-color:var(--accent);color:var(--accent)}
.btn-sm{background:var(--accent);color:var(--bg);border:none;border-radius:8px;padding:7px 14px;
  font-size:12px;font-weight:700;cursor:pointer;font-family:inherit;transition:filter .15s,box-shadow .15s,transform .05s}
body.light .btn-sm{color:#fff}
.btn-sm:hover{filter:brightness(1.05);box-shadow:0 0 0 4px rgba(34,211,238,.18)}
.btn-sm:active{transform:translateY(1px)}
.btn-danger{background:rgba(248,113,113,.15);color:var(--danger);border:1px solid rgba(248,113,113,.3);
  border-radius:8px;padding:6px 12px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit}
.btn.btn-accent{background:var(--accent);color:var(--bg);border:none}
body.light .btn.btn-accent{color:#fff}
.btn.btn-danger{background:var(--danger);color:#fff;border:none}
.btn.btn-danger:hover{filter:brightness(1.05)}
.btn-soft{background:transparent;border:1px solid transparent}
.btn.btn-soft-entree{
  background:color-mix(in srgb,var(--success) 18%,transparent);
  border-color:color-mix(in srgb,var(--success) 32%,transparent);
  color:var(--success)!important;
}
.btn.btn-soft-entree:hover{border-color:var(--success);color:var(--success);filter:brightness(1.05)}
.btn.btn-soft-sortie{
  background:color-mix(in srgb,var(--danger) 18%,transparent);
  border-color:color-mix(in srgb,var(--danger) 32%,transparent);
  color:var(--danger)!important;
}
.btn.btn-soft-sortie:hover{border-color:var(--danger);color:var(--danger);filter:brightness(1.05)}

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
.empl-code.empl-au-sol{font-family:inherit;color:var(--warn)}
.empl-au-sol-hint{font-size:12px;color:var(--warn);margin-top:8px;line-height:1.5;font-weight:600}
.empl-code.empl-sortie-prod{font-family:inherit;color:var(--success)}
.empl-sortie-prod-hint{font-size:12px;color:var(--success);margin-top:8px;line-height:1.5;font-weight:600}
.a-exp-list{display:flex;flex-direction:column;gap:8px;max-height:min(60vh,420px);overflow-y:auto;margin-top:12px}
.a-exp-row{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 14px;border:1px solid var(--border);border-radius:10px;cursor:pointer;transition:background .12s,border-color .12s}
.a-exp-row:hover{background:var(--accent-bg);border-color:rgba(34,211,238,.35)}
.a-exp-ref{font-family:monospace;font-weight:800;font-size:14px;color:var(--accent)}
.a-exp-des{font-size:12px;color:var(--text2);margin-top:2px}
.a-exp-qte{font-size:13px;font-weight:700;color:var(--text);white-space:nowrap}
.mvt-empl-link-au-sol{color:var(--warn)!important}
.mvt-empl-link-sortie-prod{color:var(--success)!important}
.pf-empl-badge.pf-empl-au-sol{background:rgba(251,191,36,.12);color:var(--warn);border-color:rgba(251,191,36,.4)}
.pf-empl-badge.pf-empl-sortie-prod{background:rgba(52,211,153,.12);color:var(--success);border-color:rgba(52,211,153,.4)}
.empl-suggest-au-sol{font-weight:700;color:var(--warn)}
.empl-suggest-sortie-prod{font-weight:700;color:var(--success)}
.empl-info{font-size:11px;color:var(--muted);margin-top:2px}
.empl-qte{font-family:monospace;font-weight:700;font-size:13px;text-align:right}
.empl-date{font-size:11px;color:var(--muted);text-align:right;margin-top:2px}
.empl-row-right{display:flex;align-items:center;gap:10px;flex-shrink:0}
.empl-lot-out-btn{display:inline-flex;align-items:center;justify-content:center;width:36px;height:36px;padding:0;
  border-radius:10px;border:1px solid color-mix(in srgb,var(--danger) 35%,transparent);
  background:color-mix(in srgb,var(--danger) 12%,transparent);color:var(--danger);cursor:pointer;flex-shrink:0}
.empl-lot-out-btn:hover{border-color:var(--danger);background:color-mix(in srgb,var(--danger) 22%,transparent)}
.empl-lot-actions{display:flex;align-items:center;gap:6px;flex-shrink:0}
.empl-lot-exp-btn{display:inline-flex;align-items:center;justify-content:center;width:36px;height:36px;padding:0;
  border-radius:10px;border:1px solid rgba(251,191,36,.4);
  background:rgba(251,191,36,.08);color:var(--warn);cursor:pointer;flex-shrink:0;transition:border-color .15s,background .15s}
.empl-lot-exp-btn:hover{border-color:var(--warn);background:rgba(251,191,36,.14)}
body.light .empl-lot-exp-btn{border-color:rgba(217,119,6,.35);background:rgba(251,191,36,.1)}
.empl-lot-move-btn{display:inline-flex;align-items:center;justify-content:center;width:36px;height:36px;padding:0;
  border-radius:10px;border:1px solid rgba(139,92,246,.4);
  background:rgba(139,92,246,.08);color:#8b5cf6;cursor:pointer;flex-shrink:0;transition:border-color .15s,background .15s}
.empl-lot-move-btn:hover{border-color:#8b5cf6;background:rgba(139,92,246,.14)}
body.light .empl-lot-move-btn{border-color:rgba(124,58,237,.35);background:rgba(139,92,246,.1)}

/* ── Action bar ── */
.action-bar{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap}
.action-btn{flex:1;min-width:90px;padding:12px 8px;border-radius:12px;border:1px solid transparent;
  font-size:13px;font-weight:700;cursor:pointer;font-family:inherit;
  display:flex;align-items:center;justify-content:center;gap:5px;
  transition:border-color .15s,opacity .15s,filter .15s}
.action-btn:hover{filter:brightness(1.05)}
.action-btn:active{opacity:.75}
.action-btn.entree{background:color-mix(in srgb,var(--success) 20%,transparent);color:var(--success)}
.action-btn.entree:hover{border-color:var(--success)}
.action-btn.sortie{background:color-mix(in srgb,var(--danger) 20%,transparent);color:var(--danger)}
.action-btn.sortie:hover{border-color:var(--danger)}
.action-btn.pf-entree{background:color-mix(in srgb,var(--pf-entree) 24%,transparent);color:var(--pf-entree)}
.action-btn.pf-entree:hover{border-color:var(--pf-entree)}
.action-btn.pf-sortie{background:color-mix(in srgb,var(--pf-sortie) 24%,transparent);color:var(--pf-sortie)}
.action-btn.pf-sortie:hover{border-color:var(--pf-sortie)}
.action-btn.inventaire{background:color-mix(in srgb,var(--c2) 20%,transparent);color:var(--c2)}
.action-btn.inventaire:hover{border-color:var(--c2)}
/* Bouton inventaire violet forcé (indépendant du thème de palette) */
.action-btn.empl-inv-btn{background:rgba(139,92,246,.20);color:#8b5cf6;border:1.5px solid rgba(139,92,246,.45)}
.action-btn.empl-inv-btn:hover{background:rgba(139,92,246,.32);border-color:#8b5cf6}
body.light .action-btn.empl-inv-btn{color:#7c3aed;border-color:rgba(124,58,237,.45)}
body.light .action-btn.empl-inv-btn:hover{border-color:#7c3aed}

/* Bloc info dernier inventaire sur la scorecard emplacement */
.empl-inv-info{margin-top:12px;padding:10px 14px;border-radius:10px;border:1.5px solid var(--border);background:var(--bg);display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
.empl-inv-label{display:flex;align-items:center;gap:8px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.4px;color:var(--text2)}
.empl-inv-dot{display:inline-block;width:10px;height:10px;border-radius:50%}
.empl-inv-detail{display:flex;align-items:baseline;gap:0;font-family:monospace;flex-wrap:wrap}
.empl-inv-jours{font-size:17px;font-weight:800;padding:2px 12px;border-radius:8px;letter-spacing:.3px}
.empl-inv-meta{font-size:11px;color:var(--text2);margin-left:6px;font-family:'Segoe UI',system-ui,sans-serif}
.empl-inv-c-vert{border-color:color-mix(in srgb,var(--success) 40%,transparent)}
.empl-inv-c-vert .empl-inv-dot{background:var(--success)}
.empl-inv-c-vert .empl-inv-jours{background:color-mix(in srgb,var(--success) 22%,transparent);color:var(--success)}
.empl-inv-c-jaune{border-color:color-mix(in srgb,var(--warn) 40%,transparent)}
.empl-inv-c-jaune .empl-inv-dot{background:var(--warn)}
.empl-inv-c-jaune .empl-inv-jours{background:color-mix(in srgb,var(--warn) 22%,transparent);color:var(--warn)}
.empl-inv-c-orange{border-color:color-mix(in srgb,#fb923c 40%,transparent)}
.empl-inv-c-orange .empl-inv-dot{background:#fb923c}
.empl-inv-c-orange .empl-inv-jours{background:color-mix(in srgb,#fb923c 26%,transparent);color:#fb923c}
.empl-inv-c-rouge{border-color:color-mix(in srgb,var(--danger) 40%,transparent)}
.empl-inv-c-rouge .empl-inv-dot{background:var(--danger)}
.empl-inv-c-rouge .empl-inv-jours{background:color-mix(in srgb,var(--danger) 22%,transparent);color:var(--danger)}

/* ── Historique mouvements ── */
.mvt-row{padding:10px 16px;display:flex;gap:10px;align-items:flex-start;border-bottom:1px solid var(--border)}
.mvt-row:last-child{border-bottom:none}
.mvt-icon{width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:15px;flex-shrink:0}
.mvt-icon.entree{background:rgba(52,211,153,.15);color:var(--success)}
.mvt-icon.sortie{background:rgba(248,113,113,.15);color:var(--danger)}
.mvt-icon.pf-entree{background:color-mix(in srgb,var(--pf-entree) 18%,transparent);color:var(--pf-entree)}
.mvt-icon.pf-sortie{background:color-mix(in srgb,var(--pf-sortie) 18%,transparent);color:var(--pf-sortie)}
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
.mvt-qte-pf-entree{color:var(--pf-entree);font-family:monospace;font-weight:700}
.mvt-qte-pf-sortie{color:var(--pf-sortie);font-family:monospace;font-weight:700}
.mvt-qte-inventaire{color:var(--c2);font-family:monospace;font-weight:700}
.mvt-line2{font-size:11px;color:var(--muted);margin-top:2px}
.mvt-line1{align-items:flex-start}
.mvt-line1-right{display:flex;flex-direction:column;align-items:flex-end;gap:2px;flex-shrink:0}
.mvt-solde{font-size:11px;color:var(--muted);font-family:monospace;font-weight:500;line-height:1;white-space:nowrap}
.mvt-note{font-size:11px;color:var(--text2);margin-top:2px;font-style:italic}
.hist-solde-avant{color:var(--muted)}
.hist-solde-arrow{color:var(--muted);margin:0 4px}
.hist-solde-apres{color:var(--text);font-weight:800;font-family:monospace}

/* ── Stats dashboard ── */
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:16px}
.dash-page{display:flex;flex-direction:column;gap:0;padding-bottom:8px}
.dash-title{font-size:22px;font-weight:800;letter-spacing:-.3px;color:var(--text);margin:0 0 20px}
.dash-kpi-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-bottom:20px}
.dash-kpi-grid .stat-card{display:flex;flex-direction:column;justify-content:center;min-height:88px}
@media(max-width:900px){
  .dash-kpi-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-bottom:14px}
  .dash-kpi-grid .stat-card{min-height:0;padding:10px 12px;border-radius:10px}
  .dash-kpi-grid .stat-label{font-size:8px;margin-bottom:3px;letter-spacing:.35px;line-height:1.25}
  .dash-kpi-grid .stat-value{font-size:18px;line-height:1.1}
}
@media(max-width:480px){
  .dash-kpi-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}
  .dash-kpi-grid .stat-card{padding:8px 10px;border-radius:8px}
  .dash-kpi-grid .stat-label{font-size:7px;margin-bottom:2px}
  .dash-kpi-grid .stat-value{font-size:15px}
}
.dash-quick-card{
  background:linear-gradient(145deg,var(--accent-bg) 0%,var(--card) 42%);
  border:1.5px solid rgba(34,211,238,.32);border-radius:14px;padding:18px 16px 16px;margin-bottom:20px;
  box-shadow:0 6px 24px rgba(34,211,238,.08)}
body.light .dash-quick-card{box-shadow:0 4px 18px rgba(8,145,178,.1);border-color:rgba(8,145,178,.28)}
.dash-quick-card-head{display:flex;align-items:center;gap:12px;margin-bottom:14px}
.dash-quick-card-icon{
  display:flex;align-items:center;justify-content:center;flex-shrink:0;
  width:40px;height:40px;border-radius:11px;background:var(--accent-bg);color:var(--accent);
  border:1px solid rgba(34,211,238,.35)}
.dash-quick-card-title{font-size:14px;font-weight:800;color:var(--text);margin:0;letter-spacing:-.2px}
.dash-quick-card-sub{font-size:11px;color:var(--muted);margin-top:3px;font-weight:500;line-height:1.35}
.dash-quick-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(148px,1fr));gap:10px}
.dash-quick-btn{
  display:flex;flex-direction:column;align-items:flex-start;gap:10px;
  background:var(--bg);border:1.5px solid var(--border);border-radius:12px;padding:14px 14px 12px;
  font-size:12px;font-weight:700;color:var(--text);cursor:pointer;font-family:inherit;text-align:left;
  transition:border-color .15s,background .15s,transform .12s,box-shadow .15s;line-height:1.35}
.dash-quick-btn:hover{transform:translateY(-1px);box-shadow:0 4px 14px rgba(0,0,0,.12)}
body.light .dash-quick-btn:hover{box-shadow:0 4px 12px rgba(15,23,42,.08)}
.dash-quick-btn-icon{
  display:flex;align-items:center;justify-content:center;width:42px;height:42px;border-radius:11px;flex-shrink:0}
.dash-quick-btn-label{font-size:12px;font-weight:700;line-height:1.35}
.dash-quick-btn--accent{background:rgba(34,211,238,.1);border-color:rgba(34,211,238,.45);color:var(--accent)}
.dash-quick-btn--accent .dash-quick-btn-icon{background:rgba(34,211,238,.2);color:var(--accent)}
.dash-quick-btn--accent:hover{background:rgba(34,211,238,.16);border-color:var(--accent)}
.dash-quick-btn--warn{background:rgba(251,191,36,.08);border-color:rgba(251,191,36,.4);color:var(--warn)}
.dash-quick-btn--warn .dash-quick-btn-icon{background:rgba(251,191,36,.18);color:var(--warn)}
.dash-quick-btn--warn:hover{background:rgba(251,191,36,.14);border-color:var(--warn)}
.dash-quick-btn--success{background:rgba(52,211,153,.08);border-color:rgba(52,211,153,.4);color:var(--success)}
.dash-quick-btn--success .dash-quick-btn-icon{background:rgba(52,211,153,.18);color:var(--success)}
.dash-quick-btn--success:hover{background:rgba(52,211,153,.14);border-color:var(--success)}
.dash-quick-btn--danger{background:rgba(248,113,113,.08);border-color:rgba(248,113,113,.4);color:var(--danger)}
.dash-quick-btn--danger .dash-quick-btn-icon{background:rgba(248,113,113,.18);color:var(--danger)}
.dash-quick-btn--danger:hover{background:rgba(248,113,113,.14);border-color:var(--danger)}
.dash-quick-btn--pf-entree{background:color-mix(in srgb,var(--pf-entree) 10%,transparent);border-color:color-mix(in srgb,var(--pf-entree) 45%,transparent);color:var(--pf-entree)}
.dash-quick-btn--pf-entree .dash-quick-btn-icon{background:color-mix(in srgb,var(--pf-entree) 20%,transparent);color:var(--pf-entree)}
.dash-quick-btn--pf-entree:hover{background:color-mix(in srgb,var(--pf-entree) 16%,transparent);border-color:var(--pf-entree)}
.dash-quick-btn--pf-sortie{background:color-mix(in srgb,var(--pf-sortie) 10%,transparent);border-color:color-mix(in srgb,var(--pf-sortie) 45%,transparent);color:var(--pf-sortie)}
.dash-quick-btn--pf-sortie .dash-quick-btn-icon{background:color-mix(in srgb,var(--pf-sortie) 20%,transparent);color:var(--pf-sortie)}
.dash-quick-btn--pf-sortie:hover{background:color-mix(in srgb,var(--pf-sortie) 16%,transparent);border-color:var(--pf-sortie)}
.dash-quick-btn--neutral{background:var(--card);border-color:var(--border);color:var(--text2)}
.dash-quick-btn--neutral .dash-quick-btn-icon{background:var(--accent-bg);color:var(--accent);border:1px solid rgba(34,211,238,.2)}
.dash-quick-btn--neutral:hover{border-color:var(--accent);color:var(--accent)}
@media(max-width:768px){.dash-quick-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}}
@media(max-width:480px){
  .dash-quick-card{padding:14px 12px 12px}
  .dash-quick-card-head{gap:10px;margin-bottom:12px}
  .dash-quick-card-icon{width:36px;height:36px}
  .dash-quick-card-title{font-size:13px}
  .dash-quick-btn{padding:12px 12px 10px;gap:8px}
  .dash-quick-btn-icon{width:36px;height:36px;border-radius:10px}
  .dash-quick-btn-label{font-size:11px}
}
.dash-section{border-top:1px solid var(--border);padding-top:22px;margin-top:22px}
.dash-section-title{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;
  color:var(--muted);margin:0 0 14px;display:flex;align-items:center;justify-content:space-between}
.dash-section-toggle{background:none;border:1px solid var(--border);border-radius:6px;
  color:var(--muted);font-size:11px;font-weight:500;padding:3px 8px;cursor:pointer;
  text-transform:none;letter-spacing:0;transition:border-color .15s,color .15s;line-height:1.4}
.dash-section-toggle:hover{border-color:var(--accent);color:var(--accent)}
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
.dash-mp-cat-frontal{background:rgba(14,165,233,.15);color:#0ea5e9}
.dash-mp-cat-frontal-couche{background:rgba(125,211,252,.22);color:#0284c7}
.dash-mp-cat-frontal-synthetique{background:rgba(34,211,238,.18);color:#0891b2}
.dash-mp-cat-frontal-thermiques{background:rgba(99,102,241,.20);color:#4f46e5}
.dash-mp-cat-frontal-velin{background:rgba(30,58,138,.22);color:#1e3a8a}
.dash-mp-cat-glassine{background:rgba(236,72,153,.15);color:#ec4899}
.dash-mp-cat-palette{background:rgba(8,145,178,.15);color:#0891b2}
.dash-mp-cat-adhesif{background:rgba(217,119,6,.15);color:#d97706}
.dash-mp-cat-carton{background:rgba(5,150,105,.15);color:#059669}
.dash-mp-cat-complexe{background:rgba(99,102,241,.15);color:#6366f1}
.dash-mp-cat-autre{background:rgba(148,163,184,.18);color:#64748b}
.dash-mp-cat-negoce{background:rgba(34,211,238,.15);color:var(--accent)}
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
/* Pills frontal éclatées par sous-section — teintes bleues distinctes */
.mp-pill-frontal-couche:hover{border-color:#0284c7;color:#0284c7}
.mp-pill-frontal-couche.active{background:rgba(125,211,252,.22);border-color:#0284c7;color:#0284c7}
.mp-pill-frontal-synthetique:hover{border-color:#0891b2;color:#0891b2}
.mp-pill-frontal-synthetique.active{background:rgba(34,211,238,.18);border-color:#0891b2;color:#0891b2}
.mp-pill-frontal-thermiques:hover{border-color:#4f46e5;color:#4f46e5}
.mp-pill-frontal-thermiques.active{background:rgba(99,102,241,.20);border-color:#4f46e5;color:#4f46e5}
.mp-pill-frontal-velin:hover{border-color:#1e3a8a;color:#1e3a8a}
.mp-pill-frontal-velin.active{background:rgba(30,58,138,.22);border-color:#1e3a8a;color:#1e3a8a}
.mp-search-wrap{
  margin-bottom:18px;position:relative;display:flex;align-items:center;
  background:var(--card);border:1.5px solid var(--accent);border-radius:12px;
  box-shadow:0 0 0 3px var(--accent-bg);transition:border-color .15s,box-shadow .15s
}
.mp-search-wrap:focus-within{
  border-color:var(--accent);
  box-shadow:0 0 0 4px color-mix(in srgb,var(--accent) 22%,transparent)
}
body.light .mp-search-wrap:focus-within{
  box-shadow:0 0 0 4px rgba(8,145,178,.14)
}
.mp-search-icon{
  position:absolute;left:14px;top:50%;transform:translateY(-50%);
  display:flex;align-items:center;color:var(--accent);pointer-events:none;z-index:1
}
.mp-search{
  width:100%;background:transparent;border:none;border-radius:12px;
  padding:14px 16px 14px 46px;color:var(--text);font-size:15px;font-weight:500;
  font-family:inherit
}
.mp-search::placeholder{color:var(--muted);font-weight:500;opacity:1}
.mp-search:focus{outline:none}
.mp-list{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:12px;align-items:start}
.mp-list > .mp-section-head,.mp-list > .mp-subsection-head,.mp-list > .mp-empty{grid-column:1/-1}
@media (max-width:780px){.mp-list{grid-template-columns:1fr}}
.mp-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px 16px;cursor:pointer;transition:border-color .15s}
.mp-card:hover{border-color:var(--accent)}
.mp-card-top{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.mp-card-ref{font-family:ui-monospace,monospace;font-size:14px;font-weight:700;color:var(--text);flex:1;min-width:0}
.mp-card-top-end{display:flex;align-items:center;gap:8px;flex-shrink:0;margin-left:auto}
.mp-card-stock-total{
  font-family:ui-monospace,monospace;font-size:13px;font-weight:700;color:var(--accent);
  white-space:nowrap;line-height:1.2
}
.mp-card-stock-total.alert{color:var(--warn)}
.mp-card-mid{display:flex;align-items:flex-end;gap:12px;margin-top:8px}
.mp-card-info{flex:1;min-width:0}
.mp-card-side{display:flex;flex-direction:column;align-items:flex-end;gap:6px;flex-shrink:0}
.mp-card-stock-mini{font-size:12px;font-weight:600;color:var(--muted);margin-top:4px;line-height:1.3}
.mp-card-stock-mini.alert{color:var(--warn)}
.mp-act-icon{display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;padding:0;
  border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text2);cursor:pointer;
  flex-shrink:0;transition:border-color .15s,color .15s,background .15s;font-family:inherit}
.mp-act-icon:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.mp-card-des{font-size:13px;color:var(--text2);line-height:1.4}
.mp-card-meta{font-size:12px;color:var(--muted);margin-top:4px}
.mp-card-warn{font-size:12px;color:var(--warn);margin-top:4px}
.mp-card-actions-inline{display:flex;gap:6px;flex-wrap:nowrap}
.mp-card-actions-inline .mp-act-btn{flex:none;min-width:0;padding:6px 10px;font-size:11px;border-radius:8px;white-space:nowrap}
.action-bar .mp-act-btn{flex:1;min-width:90px;padding:12px 8px;border-radius:12px;font-size:13px;font-weight:700;
  display:flex;align-items:center;justify-content:center;gap:5px;border:1px solid transparent;
  transition:border-color .15s,opacity .15s,filter .15s}
.action-bar .mp-act-btn:hover{filter:brightness(1.05)}
.action-bar .mp-act-btn.mp-act-entree:hover{border-color:var(--success)}
.action-bar .mp-act-btn.mp-act-sortie:hover{border-color:var(--danger)}
.mp-act-btn{border:1px solid transparent;border-radius:8px;padding:8px 12px;font-size:12px;font-weight:600;cursor:pointer;
  font-family:inherit;transition:border-color .15s,opacity .15s,filter .15s}
.mp-act-btn:hover{filter:brightness(1.05)}
.mp-act-entree{background:color-mix(in srgb,var(--success) 15%,transparent);color:var(--success)}
.mp-act-entree:hover{border-color:var(--success)}
.mp-act-sortie{background:color-mix(in srgb,var(--danger) 15%,transparent);color:var(--danger)}
.mp-act-sortie:hover{border-color:var(--danger)}
.mp-act-edit{background:color-mix(in srgb,var(--muted) 18%,transparent);color:var(--text2)}
.mp-act-ajust{background:color-mix(in srgb,var(--warn) 15%,transparent);color:var(--warn)}
.mp-act-transf{background:color-mix(in srgb,var(--accent) 15%,transparent);color:var(--accent)}
.mp-menu-btn{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:8px 14px;font-size:16px;cursor:pointer;color:var(--text2)}
.mp-menu-drop{position:absolute;right:0;top:100%;margin-top:4px;background:var(--card);border:1px solid var(--border);
  border-radius:10px;padding:6px;min-width:140px;z-index:50;box-shadow:0 8px 24px rgba(0,0,0,.25)}
.mp-menu-drop button{display:block;width:100%;text-align:left;margin-bottom:4px}
.mp-empty{text-align:center;color:var(--muted);font-size:13px;padding:32px 16px}
/* ── Convertir une unité de vente (référentiel) ── */
.ref-convert-unite-card .cu-sugg-empty{padding:14px;color:var(--muted);font-size:13px;text-align:center}
.cu-sugg-list{margin-top:8px;border:1px solid var(--border);border-radius:10px;overflow:hidden}
.cu-sugg-row{display:flex;align-items:center;justify-content:space-between;gap:10px;
  padding:10px 14px;cursor:pointer;font-size:13px;border-bottom:1px solid var(--border);transition:background .15s}
.cu-sugg-row:last-child{border-bottom:none}
.cu-sugg-row:hover{background:var(--accent-bg)}
.cu-sugg-main{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cu-sugg-ref{font-family:monospace;font-weight:700;color:var(--text)}
.cu-sugg-des{color:var(--text2);font-size:12px}
.cu-sugg-unit{flex-shrink:0;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.4px;
  padding:3px 9px;border-radius:999px;background:var(--accent-bg);color:var(--accent);border:1px solid var(--border)}
.cu-prod-card{display:flex;justify-content:space-between;align-items:flex-start;gap:14px;
  padding:14px 16px;background:var(--bg);border:1px solid var(--border);border-radius:10px;margin-top:8px}
.cu-prod-info{flex:1;min-width:0}
.cu-prod-ref{font-family:monospace;font-weight:800;font-size:15px;color:var(--text)}
.cu-prod-des{font-size:12px;color:var(--text2);margin:2px 0 6px}
.cu-prod-stock{font-size:12px;color:var(--muted)}
.cu-prod-stock strong{color:var(--text)}
.cu-prod-reset{flex-shrink:0}
.cu-row{margin-top:14px;display:flex;flex-direction:column;gap:6px}
.cu-row .cu-label{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted)}
.cu-row .cu-label .cu-label-unit{color:var(--text);font-weight:800;text-transform:none;letter-spacing:0}
.cu-row select,.cu-row input{background:var(--bg);border:1px solid var(--border);border-radius:10px;
  padding:10px 14px;color:var(--text);font-size:14px;font-family:inherit;outline:none;width:100%}
.cu-row select:focus,.cu-row input:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-bg)}
.cu-input-row{display:flex;gap:8px;align-items:center}
.cu-input-row input{flex:1}
.cu-reverse{flex-shrink:0;white-space:nowrap}
.cu-preview{margin-top:12px;padding:10px 14px;background:var(--accent-bg);border:1px solid var(--border);
  border-radius:8px;font-size:13px;color:var(--text);display:flex;align-items:center;gap:6px}
.cu-actions{margin-top:16px;display:flex;justify-content:flex-end;gap:8px}
/* ── Vue Production (fabrication) ── */
.prod-view{padding:16px 16px 24px 10px}
.prod-head{margin-bottom:18px}
.prod-head-title{font-size:22px;font-weight:800;color:var(--text);margin:0 0 4px 0}
.prod-head-sub{font-size:13px;color:var(--muted);line-height:1.5}
.prod-action-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:24px}
.prod-action-card{display:flex;align-items:center;gap:14px;padding:18px 16px;border-radius:14px;
  border:1px solid var(--border);background:var(--card);cursor:pointer;text-align:left;
  font-family:inherit;color:var(--text);transition:all .15s;min-height:88px}
.prod-action-card:hover{border-color:var(--accent);transform:translateY(-1px);
  box-shadow:0 4px 16px rgba(0,0,0,.18)}
.prod-action-ico{flex-shrink:0;width:48px;height:48px;border-radius:12px;display:flex;
  align-items:center;justify-content:center;color:#fff}
.prod-action-txt{flex:1;min-width:0}
.prod-action-title{font-size:15px;font-weight:800;color:var(--text);margin-bottom:2px}
.prod-action-sub{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;font-weight:600}
.prod-action-mp-in .prod-action-ico{background:#0ea5e9}
.prod-action-mp-out .prod-action-ico{background:#f59e0b}
.prod-action-z1-in .prod-action-ico{background:var(--success)}
.prod-action-z1-out .prod-action-ico{background:var(--danger)}
.prod-z1-card{padding:18px}
.prod-z1-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;
  margin-bottom:14px;flex-wrap:wrap}
.prod-z1-title{display:flex;align-items:center;gap:8px;font-size:15px;font-weight:700;color:var(--text);margin-bottom:4px}
.prod-z1-sub{font-size:12px;color:var(--muted)}
.prod-z1-refresh{display:inline-flex;align-items:center;gap:6px;padding:8px 12px;border-radius:8px;
  border:1px solid var(--border);background:var(--bg);color:var(--text2);cursor:pointer;font-size:12px;font-weight:600;font-family:inherit}
.prod-z1-refresh:hover{border-color:var(--accent);color:var(--accent)}
.prod-z1-list{display:flex;flex-direction:column;gap:8px}
.prod-z1-row{display:flex;justify-content:space-between;align-items:center;gap:14px;padding:12px 14px;
  background:var(--bg);border:1px solid var(--border);border-radius:10px}
.prod-z1-row:hover{border-color:var(--accent)}
.prod-z1-left{flex:1;min-width:0}
.prod-z1-ref{font-family:monospace;font-size:14px;font-weight:800;color:var(--text)}
.prod-z1-des{font-size:12px;color:var(--text2);margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.prod-z1-meta{display:flex;flex-wrap:wrap;gap:14px;margin-top:6px;font-size:11px;color:var(--muted)}
.prod-z1-meta-date,.prod-z1-meta-op{display:inline-flex;align-items:center;gap:4px}
.prod-z1-qty{font-size:15px;font-weight:800;color:var(--success);
  font-variant-numeric:tabular-nums;text-align:right}
.prod-z1-right{display:flex;flex-direction:column;align-items:flex-end;gap:6px;flex-shrink:0}
.prod-z1-actions{display:flex;gap:6px}
.prod-z1-btn{display:inline-flex;align-items:center;gap:4px;padding:5px 9px;border-radius:7px;
  border:1px solid var(--border);background:var(--card);color:var(--text2);cursor:pointer;
  font-size:11px;font-weight:700;font-family:inherit;transition:all .15s}
.prod-z1-btn:hover{border-color:var(--accent);color:var(--accent)}
.prod-z1-btn-add:hover{border-color:var(--success);color:var(--success)}
.prod-z1-btn-edit:hover{border-color:var(--warn);color:var(--warn)}
.prod-z1-empty{padding:32px 16px}
.prod-z1-empty-hint{font-size:12px;color:var(--muted);margin-top:6px}
@media (max-width:900px){
  .prod-action-grid{grid-template-columns:repeat(2,1fr);gap:10px}
  .prod-action-card{padding:16px 12px;min-height:80px}
  .prod-action-title{font-size:14px}
  .prod-action-ico{width:42px;height:42px;border-radius:10px}
  .prod-view{padding:12px 12px 24px 12px}
}
@media (max-width:480px){
  .prod-z1-meta{gap:10px;font-size:10px}
  .prod-z1-ref{font-size:13px}
  .prod-z1-qty{font-size:14px}
}
/* ── Produits finis (onglet) ── */
.pf-tab{padding:16px 16px 24px 10px}
.pf-toolbar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:16px}
.pf-toolbar-search{flex:1;min-width:240px;position:relative}
.pf-toolbar-searchbox{position:relative;display:flex;align-items:center;gap:8px;flex-wrap:wrap;
  background:var(--card);border:1px solid var(--border);border-radius:10px;padding:8px 12px 8px 34px;min-height:44px}
.pf-toolbar-searchbox:focus-within{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-bg)}
.pf-toolbar-search-icon{position:absolute;left:10px;top:50%;transform:translateY(-50%);color:var(--muted);display:flex;pointer-events:none}
.pf-toolbar-searchbox input{flex:1;min-width:180px;border:none;background:transparent;padding:0;font-size:14px;color:var(--text);outline:none}
.pf-toolbar-searchbox input::placeholder{color:var(--muted)}
.pf-tags{display:flex;flex-wrap:wrap;gap:6px}
.pf-tags-below{margin-top:8px}
.pf-tag{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--border);
  background:var(--bg);color:var(--text2);border-radius:999px;padding:5px 10px;font-size:12px;font-weight:700}
.pf-tag-kind{font-size:10px;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.35px}
.pf-tag-x{border:none;background:transparent;color:var(--muted);cursor:pointer;padding:0 2px;font-weight:900;font-size:14px;line-height:1}
.pf-tag-x:hover{color:var(--accent)}
.pf-search-dd{position:absolute;left:0;right:0;top:100%;margin-top:6px;z-index:160}
.pf-search-dd .empl-suggestions{background:var(--card);border-radius:10px}
.pf-sugg-item{padding:10px 14px;cursor:pointer;font-family:inherit;font-size:13px;color:var(--text);
  border-bottom:1px solid var(--border);line-height:1.35}
.pf-sugg-item:last-child{border-bottom:none}
.pf-sugg-item:hover{background:var(--accent-bg)}
.pf-sugg-item .pf-sugg-kind{font-size:10px;color:var(--muted);font-weight:800;text-transform:uppercase;letter-spacing:.35px}
.pf-sugg-item .pf-sugg-main{font-weight:700}
.pf-sugg-item .pf-sugg-sub{color:var(--text2);font-weight:600}
.pf-search-hint{font-size:11px;color:var(--muted);margin-top:6px}
.pf-toolbar-actions{display:flex;gap:8px;flex-shrink:0}
.pf-kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px}
@media(max-width:700px){.pf-kpis{grid-template-columns:1fr}}
.pf-kpi{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px 16px}
.pf-kpi-label{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);margin-bottom:6px}
.pf-kpi-value{font-size:24px;font-weight:700;font-family:ui-monospace,monospace;color:var(--accent)}
.pf-grid{display:grid;grid-template-columns:1fr 340px;gap:16px;align-items:start}
@media(max-width:960px){.pf-grid{grid-template-columns:1fr}}
.pf-col-title{font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);margin-bottom:10px}
.pf-stock-list{display:flex;flex-direction:column;gap:6px;max-height:calc(100vh - 340px);overflow-y:auto}
.pf-stock-item{display:flex;align-items:flex-start;gap:12px;padding:12px 16px;border-radius:10px;
  border:1px solid var(--border);background:var(--card);cursor:pointer;transition:border-color .15s,background .15s}
.pf-stock-item:hover{border-color:var(--accent);background:color-mix(in srgb,var(--accent) 6%,var(--card))}
.pf-stock-item-main{flex:1;min-width:0}
.pf-stock-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px 16px}
.pf-stock-ref{font-family:ui-monospace,monospace;font-size:14px;font-weight:700;color:var(--text);margin-bottom:4px}
.pf-stock-ref .mvt-ref-link{font-family:inherit;font-size:inherit;font-weight:inherit;color:inherit}
.pf-stock-des{font-size:13px;color:var(--text2);margin-bottom:8px;line-height:1.4}
.pf-stock-row{display:flex;flex-wrap:wrap;align-items:center;gap:8px;font-size:12px;color:var(--muted)}
.pf-stock-qte{font-family:ui-monospace,monospace;font-weight:700;color:var(--accent);font-size:13px}
.pf-empl-badge{font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px;
  background:var(--accent-bg);color:var(--accent);border:1px solid color-mix(in srgb,var(--accent) 35%,transparent)}
.pf-stock-meta{margin-top:6px;font-size:11px;color:var(--muted)}
.pf-stock-actions{margin-top:10px;display:flex;justify-content:flex-end}
.pf-mvt-list{display:flex;flex-direction:column;gap:8px;max-height:calc(100vh - 320px);overflow-y:auto}
.pf-mvt-item{display:flex;gap:10px;align-items:flex-start;padding:10px 12px;background:var(--card);
  border:1px solid var(--border);border-radius:10px;font-size:12px}
.pf-mvt-icon{font-size:16px;font-weight:700;line-height:1;flex-shrink:0;width:20px;text-align:center}
.pf-mvt-icon.entree{color:var(--success)}
.pf-mvt-icon.sortie{color:var(--danger)}
.pf-empty-state{text-align:center;padding:48px 24px;color:var(--muted)}
.pf-empty-state-title{font-size:14px;font-weight:600;color:var(--text2);margin:12px 0 6px}
.pf-empty-state-hint{font-size:13px;line-height:1.5}
.pf-mvt-main{flex:1;min-width:0}
.pf-mvt-line{display:flex;align-items:baseline;gap:6px;flex-wrap:wrap}
.pf-mvt-ref{font-weight:700;color:var(--text)}
.pf-mvt-ref .mvt-ref-link{font-family:inherit;font-size:inherit;font-weight:inherit;color:inherit}
.pf-mvt-qte{font-family:ui-monospace,monospace;font-size:12px;color:var(--text2)}
.pf-mvt-sub{color:var(--muted);margin-top:2px;font-size:11px}
.pf-mvt-user{color:var(--text2);font-size:11px;flex-shrink:0;text-align:right;max-width:90px;overflow:hidden;text-overflow:ellipsis}
.pf-empty{padding:24px;text-align:center;color:var(--muted);font-size:13px}
.pf-detail-table{width:100%;border-collapse:collapse;font-size:12px}
.pf-detail-table th,.pf-detail-table td{padding:8px 10px;border-bottom:1px solid var(--border);text-align:left}
.pf-detail-table th{font-size:10px;text-transform:uppercase;letter-spacing:.4px;color:var(--muted);font-weight:600}
/* Négoce — contrôles tri + ruptures */
.ng-controls{display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:12px}
.ng-controls-group{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.ng-controls-label{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);margin-right:2px}
.ng-chip{font-size:12px;font-weight:600;padding:5px 12px;border-radius:20px;border:1px solid var(--border);background:var(--card);color:var(--text2);cursor:pointer;transition:border-color .15s,background .15s,color .15s}
.ng-chip:hover{border-color:var(--accent);color:var(--text)}
.ng-chip.active{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}
.ng-toggle{display:inline-flex;align-items:center;gap:10px;font-size:12px;font-weight:600;
  color:var(--text2);cursor:pointer;user-select:none;padding:6px 12px 6px 6px;border-radius:999px;
  border:1px solid var(--border);background:var(--bg);transition:border-color .15s,background .15s,color .15s}
.ng-toggle:hover{border-color:var(--accent);color:var(--text)}
.ng-toggle.is-on{border-color:var(--accent);background:var(--accent-bg);color:var(--accent)}
.ng-toggle .ng-toggle-input{position:absolute;opacity:0;width:0;height:0;pointer-events:none}
.ng-toggle .ng-toggle-switch{position:relative;display:inline-block;width:34px;height:18px;
  border-radius:999px;background:var(--border);transition:background .18s ease}
.ng-toggle .ng-toggle-thumb{position:absolute;top:2px;left:2px;width:14px;height:14px;border-radius:50%;
  background:#fff;box-shadow:0 1px 2px rgba(0,0,0,.25);transition:transform .18s ease}
.ng-toggle.is-on .ng-toggle-switch{background:var(--accent)}
.ng-toggle.is-on .ng-toggle-thumb{transform:translateX(16px)}
.ng-toggle .ng-toggle-label{line-height:1}
.pf-stock-item.ng-rupture{opacity:0.78}
.pf-stock-item.ng-rupture:hover{opacity:1}
.ng-rupture-badge{font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px;background:color-mix(in srgb,var(--danger) 14%,transparent);color:var(--danger);border:1px solid color-mix(in srgb,var(--danger) 35%,transparent);text-transform:uppercase;letter-spacing:.4px}
/* Négoce — fiche détail */
.ng-detail{display:flex;flex-direction:column;gap:18px;max-width:1100px;margin:0 auto}
.ng-detail-header{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:20px 24px;display:flex;align-items:flex-start;gap:20px;flex-wrap:wrap}
.ng-detail-header-main{flex:1;min-width:240px}
.ng-detail-ref{font-family:ui-monospace,monospace;font-size:22px;font-weight:800;color:var(--text);letter-spacing:.5px}
.ng-detail-des{font-size:14px;color:var(--text2);margin-top:4px;line-height:1.5}
.ng-detail-unite{font-size:11px;color:var(--muted);margin-top:6px;text-transform:uppercase;letter-spacing:.4px}
.ng-detail-stock{text-align:right;flex-shrink:0}
.ng-detail-stock-label{font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);font-weight:600;margin-bottom:4px}
.ng-detail-stock-value{font-family:ui-monospace,monospace;font-size:28px;font-weight:800;color:var(--accent);line-height:1}
.ng-detail-stock-value.rupture{color:var(--danger)}
.ng-detail-actions{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.ng-detail-grid{display:grid;grid-template-columns:1fr 1.4fr;gap:18px}
@media(max-width:960px){.ng-detail-grid{grid-template-columns:1fr}}
.ng-detail-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px 18px}
.ng-detail-card-title{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);margin-bottom:10px}
.ng-empl-row{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px 12px;border-radius:10px;border:1px solid var(--border);margin-bottom:6px;background:var(--bg)}
.ng-empl-row:last-child{margin-bottom:0}
.ng-empl-code{font-family:ui-monospace,monospace;font-weight:700;color:var(--text);font-size:13px}
.ng-empl-qte{font-family:ui-monospace,monospace;font-weight:700;color:var(--accent);font-size:13px}
#mroot{position:fixed;inset:0;z-index:550;pointer-events:none}
#mroot:empty{display:none;position:static;inset:auto;width:0;height:0;overflow:hidden;z-index:auto}
#mroot>*{pointer-events:auto}
body.sb-open #mroot{pointer-events:none!important;z-index:50!important}
body.sb-open #mroot>*{pointer-events:none!important}
.mp-modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.7);display:flex;align-items:center;justify-content:center;padding:18px}
.mp-modal{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:20px;width:100%;max-width:480px;max-height:90vh;overflow-y:auto}
.mp-modal > h3{margin:0 0 16px;font-size:16px;font-weight:700;color:var(--text)}
.mp-modal.mp-modal-mvt{padding:0;overflow:visible;display:flex;flex-direction:column}
.mp-modal-mvt-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;padding:16px 20px;flex-shrink:0}
.mp-modal-mvt-head h3{margin:0;font-size:16px;font-weight:700}
.mp-modal-mvt-head-entree{background:color-mix(in srgb,var(--success) 16%,transparent);
  border-bottom:1px solid color-mix(in srgb,var(--success) 32%,transparent)}
.mp-modal-mvt-head-entree h3{color:var(--success)}
.mp-modal-mvt-head-sortie{background:color-mix(in srgb,var(--danger) 16%,transparent);
  border-bottom:1px solid color-mix(in srgb,var(--danger) 32%,transparent)}
.mp-modal-mvt-head-sortie h3{color:var(--danger)}
.mp-modal-mvt-head-pf-entree{background:color-mix(in srgb,var(--pf-entree) 18%,transparent);
  border-bottom:1px solid color-mix(in srgb,var(--pf-entree) 35%,transparent)}
.mp-modal-mvt-head-pf-entree h3{color:var(--pf-entree)}
.mp-modal-mvt-head-pf-sortie{background:color-mix(in srgb,var(--pf-sortie) 18%,transparent);
  border-bottom:1px solid color-mix(in srgb,var(--pf-sortie) 35%,transparent)}
.mp-modal-mvt-head-pf-sortie h3{color:var(--pf-sortie)}
.mp-modal-mvt-head-ajustement{background:color-mix(in srgb,var(--warn) 14%,transparent);
  border-bottom:1px solid color-mix(in srgb,var(--warn) 28%,transparent)}
.mp-modal-mvt-head-ajustement h3{color:var(--warn)}
.mp-modal-mvt-head-transfert{background:color-mix(in srgb,var(--accent) 14%,transparent);
  border-bottom:1px solid color-mix(in srgb,var(--accent) 28%,transparent)}
.mp-modal-mvt-head-transfert h3{color:var(--accent)}
.mp-modal-mvt-body{padding:16px 20px 20px;overflow-y:auto;overflow-x:visible;flex:1}
.mp-field.empl-field-wrap,.mp-field.ref-field-wrap{position:relative;overflow:visible}
.mp-modal-mvt-body .mp-field.empl-field-wrap:focus-within,.mp-modal-mvt-body .mp-field.ref-field-wrap:focus-within{z-index:30}
.empl-combo-wrap .empl-suggestions{
  position:absolute;top:100%;left:0;right:0;z-index:400;display:block;
  margin-top:4px;max-height:200px;overflow-y:auto;
  background:var(--card);border:1px solid var(--border);border-radius:8px;
  box-shadow:0 8px 24px rgba(0,0,0,.28)}
body.light .empl-combo-wrap .empl-suggestions{box-shadow:0 8px 20px rgba(15,23,42,.12)}
.mp-modal-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:16px}
.mp-modal-head h3{margin:0;font-size:16px;font-weight:700;color:var(--text)}
.mp-modal-close{background:transparent;border:none;color:var(--text2);font-size:22px;line-height:1;cursor:pointer;
  display:inline-flex;align-items:center;justify-content:center;width:32px;height:32px;
  border-radius:8px;flex-shrink:0;font-family:inherit;transition:background .15s,color .15s}
.mp-modal-close:hover{color:var(--text);background:color-mix(in srgb,var(--text) 10%,transparent)}
.mp-modal-mvt-head-pf-entree .mp-modal-close{color:color-mix(in srgb,var(--pf-entree) 75%,var(--text))}
.mp-modal-mvt-head-pf-entree .mp-modal-close:hover{background:color-mix(in srgb,var(--pf-entree) 18%,transparent);color:var(--pf-entree)}
.mp-modal-mvt-head-pf-sortie .mp-modal-close{color:color-mix(in srgb,var(--pf-sortie) 75%,var(--text))}
.mp-modal-mvt-head-pf-sortie .mp-modal-close:hover{background:color-mix(in srgb,var(--pf-sortie) 18%,transparent);color:var(--pf-sortie)}
.mp-modal-mvt-head-entree .mp-modal-close{color:color-mix(in srgb,var(--success) 70%,var(--text))}
.mp-modal-mvt-head-entree .mp-modal-close:hover{background:color-mix(in srgb,var(--success) 18%,transparent);color:var(--success)}
.mp-modal-mvt-head-sortie .mp-modal-close{color:color-mix(in srgb,var(--danger) 70%,var(--text))}
.mp-modal-mvt-head-sortie .mp-modal-close:hover{background:color-mix(in srgb,var(--danger) 18%,transparent);color:var(--danger)}
.mp-modal-sub{font-size:12px;color:var(--muted);margin:-8px 0 14px;line-height:1.5}
.mp-field{margin-bottom:12px}
.mp-field label{display:block;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);margin-bottom:6px}
.mp-field input:not([type=checkbox]):not([type=radio]),.mp-field select,.mp-field textarea{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px 12px;color:var(--text);font-size:14px;font-family:inherit;transition:border-color .15s,box-shadow .15s}
.mp-field input:focus:not([type=checkbox]):not([type=radio]),.mp-field select:focus,.mp-field textarea:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12)}
body.light .mp-field input:focus:not([type=checkbox]):not([type=radio]),body.light .mp-field select:focus,body.light .mp-field textarea:focus{box-shadow:0 0 0 3px rgba(8,145,178,.12)}
.mp-field input[type=checkbox],.mp-field input[type=radio]{width:auto;padding:0;margin:0;flex-shrink:0;accent-color:var(--accent)}
.mp-field textarea{min-height:72px;resize:vertical}
.mp-readonly{padding:10px 12px;background:var(--bg);border:1px solid var(--border);border-radius:10px;font-size:13px;color:var(--text2)}
.mp-hint{font-size:12px;color:var(--muted);margin-top:4px}
.mp-hint.err{color:var(--danger)}
.mp-modal-actions{display:flex;gap:10px;margin-top:16px;align-items:center;justify-content:flex-end;flex-wrap:wrap}
.mp-modal-actions .btn-ghost{min-width:96px}
.mp-modal-actions .btn{min-width:120px}
.mp-modal-actions .btn-ghost:hover{border-color:var(--text2);color:var(--text);background:color-mix(in srgb,var(--text) 6%,transparent)}
.mp-modal-actions-right{display:flex;gap:10px;margin-left:auto}
.mp-btn-icon-danger{display:inline-flex;align-items:center;justify-content:center;width:40px;height:40px;padding:0;
  border:1px solid color-mix(in srgb,var(--danger) 35%,transparent);border-radius:10px;
  background:color-mix(in srgb,var(--danger) 12%,transparent);color:var(--danger);cursor:pointer;font-family:inherit;
  transition:border-color .15s,background .15s}
.mp-btn-icon-danger:hover{border-color:var(--danger);background:color-mix(in srgb,var(--danger) 22%,transparent)}
.mp-btn-icon-danger:disabled{opacity:.4;cursor:not-allowed}
.mp-drawer-overlay{position:fixed;inset:0;background:rgba(0,0,0,.55);display:flex;justify-content:flex-end}
.mp-drawer{background:var(--card);border-left:1px solid var(--border);width:100%;max-width:480px;height:100%;display:flex;flex-direction:column}
.mp-drawer-head{display:flex;align-items:center;justify-content:space-between;padding:16px 18px;border-bottom:1px solid var(--border);flex-shrink:0}
.mp-drawer-body{flex:1 1 0;min-height:80px;overflow-y:auto;padding:16px 18px}
.mp-drawer-foot{padding:16px 18px;border-top:1px solid var(--border);flex:0 1 auto;max-height:70vh;overflow-y:auto}
.mp-admin-row{padding:12px 0;border-bottom:1px solid var(--border)}
.mp-admin-row:last-child{border-bottom:none}
.mp-admin-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}
.mp-admin-edit{background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:12px;margin-top:10px}
.mp-admin-err{font-size:12px;color:var(--danger);margin-top:8px}
@media(max-width:640px){
  .mp-drawer{max-width:100%}
}
/* ── Historique mouvements ── */
.hist-page{padding:0 0 24px}
.hist-title{font-size:22px;font-weight:800;letter-spacing:-.3px;color:var(--text);margin:0 0 4px}
.hist-subtitle{font-size:12px;color:var(--muted);margin:0}
.hist-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:18px}
.hist-head-actions{display:flex;gap:8px;flex-shrink:0}
.hist-export-btn{
  display:inline-flex;align-items:center;gap:8px;flex-shrink:0;
  background:rgba(52,211,153,.1);border:1.5px solid rgba(52,211,153,.45);color:var(--success);
  border-radius:10px;padding:10px 16px;font-size:12px;font-weight:700;font-family:inherit;
  cursor:pointer;transition:border-color .15s,background .15s,filter .15s}
.hist-export-btn:hover{background:rgba(52,211,153,.16);border-color:var(--success);filter:brightness(1.05)}
.hist-export-btn:active{transform:translateY(1px)}
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
  border-bottom:1px solid var(--border);background:var(--bg);color:var(--text);flex-wrap:wrap}
.hist-results-head-left{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;min-width:0}
.hist-results-head-nav{display:flex;align-items:center;gap:8px;flex-shrink:0;flex-wrap:wrap}
.hist-results-head .hist-results-title{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted)}
.hist-results-head .hist-count{font-size:12px;font-weight:600;color:var(--text2)}
.hist-results-head .hist-pagination-info{font-size:12px;color:var(--text2);font-weight:600;min-width:88px;text-align:center;white-space:nowrap}
.hist-results-head-nav .btn{min-width:96px}
.hist-results-title{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted)}
.hist-count{font-size:12px;font-weight:600;color:var(--text2)}
.hist-table-wrap{display:block;overflow-x:auto;-webkit-overflow-scrolling:touch}
.hist-table{width:100%;min-width:1200px;border-collapse:collapse;font-size:13px}
.hist-unite{font-size:12px;color:var(--text2);white-space:nowrap}
.hist-table thead th{font-size:10px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);
  background:var(--bg);border-bottom:1px solid var(--border);padding:11px 14px;text-align:left;font-weight:600;white-space:nowrap}
.hist-table tbody td{padding:12px 14px;border-bottom:1px solid var(--border);color:var(--text);vertical-align:middle}
.hist-table tbody tr:last-child td{border-bottom:none}
.hist-table tbody tr:hover{background:var(--accent-bg)}
.mon-page .mon-actions{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:16px}
.mon-page .mon-actions .mon-snapshot-select{flex:1;min-width:200px;max-width:420px;background:var(--bg);border:1px solid var(--border);
  border-radius:10px;padding:10px 14px;color:var(--text);font-size:14px}
.mon-page .mon-filters-row{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:14px}
.mon-page .mon-search-wrap{flex:1;min-width:220px;display:flex;align-items:center;gap:8px;background:#fff;
  border:1px solid var(--border);border-radius:10px;padding:0 12px}
.mon-page .mon-search-wrap input{flex:1;border:none;background:transparent;padding:12px 0;color:var(--text);font-size:14px;outline:none}
.mon-page .mon-search-wrap:focus-within{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12)}
.content.mon-page.hist-page,.content:has(> .hist-page){padding:16px 20px 24px 24px;max-width:none;width:100%}
.mon-statut{display:inline-flex;align-items:center;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.4px;padding:3px 10px;border-radius:20px}
.mon-statut-ok{background:rgba(52,211,153,.12);color:var(--success)}
.mon-statut-ecart{background:rgba(248,113,113,.12);color:var(--danger)}
.mon-statut-warn{background:rgba(251,191,36,.12);color:var(--warn)}
.mon-ecart-danger{color:var(--danger);font-weight:700;font-variant-numeric:tabular-nums}
.mon-qty-neg{color:var(--danger);font-weight:600}
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
  .hist-head-actions .hist-export-btn{width:100%;justify-content:center}
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
.stat-value.danger{color:var(--danger)}

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
/* -- Affiches memo (groupe Communication, poste Bureaux) -- */
.traca-group-title{display:flex;align-items:center;gap:10px;margin:22px 0 12px;
  font-size:11px;font-weight:800;color:var(--muted);text-transform:uppercase;letter-spacing:1.5px}
.traca-group-title::after{content:"";flex:1;height:1px;background:var(--border)}
.traca-aff-card{background:var(--card);border:1.5px solid var(--border);border-radius:14px;
  padding:14px 16px;display:flex;align-items:center;gap:14px;transition:border-color .15s}
.traca-aff-card:hover{border-color:var(--accent)}
.traca-aff-card--cyan{border-left:4px solid #22d3ee}
.traca-aff-card--amber{border-left:4px solid #fbbf24}
.traca-aff-card--violet{border-left:4px solid #8b5cf6}
body.light .traca-aff-card--cyan{border-left-color:#0891b2}
body.light .traca-aff-card--amber{border-left-color:#b45309}
body.light .traca-aff-card--violet{border-left-color:#7c3aed}
.traca-aff-body{flex:1;min-width:0;display:flex;flex-direction:column;gap:3px}
.traca-aff-title{font-size:14px;font-weight:700;color:var(--text)}
.traca-aff-sub{font-size:12px;color:var(--text2);line-height:1.4}
.traca-aff-sub b{color:var(--text)}
.traca-aff-actions{display:flex;gap:6px;flex-shrink:0}
.traca-aff-btn{display:inline-flex;align-items:center;gap:6px;padding:8px 12px;
  border-radius:9px;border:1px solid var(--border);background:transparent;
  color:var(--text2);font-size:12px;font-weight:700;cursor:pointer;font-family:inherit;
  text-decoration:none;transition:border-color .15s,color .15s,background .15s}
.traca-aff-btn:hover{color:var(--text);border-color:var(--accent);background:var(--accent-bg)}
.traca-aff-dot{width:8px;height:8px;border-radius:50%;display:inline-block;flex-shrink:0}
.traca-aff-btn--dark .traca-aff-dot{background:#0a0e17;box-shadow:inset 0 0 0 1px rgba(148,163,184,.45)}
.traca-aff-btn--light .traca-aff-dot{background:#f1f5f9;box-shadow:inset 0 0 0 1px rgba(148,163,184,.45)}
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

/* ── Inventaire v2 (par emplacement, thème violet forcé) ── */
/* Variables violet INDÉPENDANTES du thème de palette (cendre, ambre, etc.) */
:root{
  --inv-v:#8b5cf6;            /* violet principal */
  --inv-v-strong:#7c3aed;     /* violet plus foncé pour bordures et hover */
  --inv-v-light:#a78bfa;      /* violet clair pour accents */
  --inv-v-bg:rgba(139,92,246,.22);          /* fond violet doux */
  --inv-v-bg-strong:rgba(139,92,246,.36);   /* fond violet renforcé (hover) */
  --inv-v-bg-soft:rgba(139,92,246,.10);     /* fond violet très léger */
  --inv-v-shadow:rgba(139,92,246,.45);       /* ombre violette */
  --inv-v-text:#0a0e17;        /* texte sur fond violet — dark theme = noir */
}
body.light{
  --inv-v-text:#ffffff;        /* texte sur fond violet — light theme = blanc */
}

.invv2-page-header{margin-bottom:12px}
.invv2-page-title{font-size:22px;font-weight:800;color:var(--inv-v);letter-spacing:.3px}
.invv2-page-sub{font-size:12px;color:var(--text2);margin-top:4px;font-weight:500}
.invv2-legend{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:10px;padding:10px 14px;background:var(--card);border:1px solid var(--border);border-left:4px solid var(--inv-v);border-radius:10px}
.invv2-legend-item{display:flex;align-items:center;gap:6px;font-size:11px;color:var(--text);font-weight:700;text-transform:uppercase;letter-spacing:.4px}
.invv2-dot{display:inline-block;width:10px;height:10px;border-radius:50%}
.invv2-c-vert .invv2-dot{background:#34d399}
.invv2-c-jaune .invv2-dot{background:#fbbf24}
.invv2-c-orange .invv2-dot{background:#fb923c}
.invv2-c-rouge .invv2-dot{background:#f87171}
.invv2-search-wrap{margin-bottom:10px}
.invv2-search-input{width:100%;border:1.5px solid var(--border);transition:border-color .15s,box-shadow .15s}
.invv2-search-input:focus{border-color:var(--inv-v);box-shadow:0 0 0 3px var(--inv-v-bg-soft);outline:none}
.invv2-list-card{padding:0;overflow:hidden;border:1.5px solid var(--inv-v-bg-soft)}
.invv2-empl-row{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 16px;cursor:pointer;border-bottom:1px solid var(--border);transition:background .15s,border-color .15s,box-shadow .15s;position:relative}
.invv2-empl-row:last-child{border-bottom:0}
.invv2-empl-row::before{content:'';position:absolute;left:0;top:0;bottom:0;width:3px;background:transparent;transition:background .15s}
.invv2-empl-row:hover{background:var(--inv-v-bg)}
.invv2-empl-row:hover::before{background:var(--inv-v)}
.invv2-empl-main{flex:1;min-width:0;display:flex;flex-direction:column;gap:3px}
.invv2-empl-code{font-size:16px;font-weight:800;color:var(--text);font-family:monospace;letter-spacing:.3px}
.invv2-empl-meta{font-size:11px;color:var(--text2);line-height:1.4}
.invv2-empl-right{display:flex;flex-direction:column;align-items:flex-end;gap:2px;flex-shrink:0}
.invv2-jours{font-weight:800;font-size:19px;padding:5px 14px;border-radius:10px;min-width:78px;text-align:center;line-height:1.2;font-family:monospace;border:1.5px solid transparent}
.invv2-jours-sub{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.4px;text-align:right;max-width:180px;font-weight:600}
.invv2-c-vert .invv2-jours{background:rgba(52,211,153,.18);color:#16a34a;border-color:rgba(52,211,153,.50)}
.invv2-c-jaune .invv2-jours{background:rgba(251,191,36,.22);color:#fbbf24;border-color:rgba(251,191,36,.55)}
.invv2-c-orange .invv2-jours{background:rgba(251,146,60,.20);color:#fb923c;border-color:rgba(251,146,60,.50)}
.invv2-c-rouge .invv2-jours{background:rgba(248,113,113,.20);color:#dc2626;border-color:rgba(248,113,113,.50)}
body:not(.light) .invv2-c-vert .invv2-jours{color:#34d399}
body:not(.light) .invv2-c-jaune .invv2-jours{color:#fbbf24}
body:not(.light) .invv2-c-orange .invv2-jours{color:#fb923c}
body:not(.light) .invv2-c-rouge .invv2-jours{color:#f87171}

/* Plan entrepôt */
.plan-allee{flex:0 0 auto;width:fit-content;min-width:120px;background:var(--card);border:1px solid var(--border);border-radius:12px;padding:12px 14px;overflow:visible}
.plan-allee-hd{display:flex;align-items:center;gap:10px;margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid var(--border)}
.plan-allee-letter{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:8px;background:rgba(34,211,238,.12);color:var(--accent);font-size:14px;font-weight:800;font-family:ui-monospace,monospace;flex-shrink:0}
body.light .plan-allee-letter{background:rgba(8,145,178,.12)}
.plan-allee-label{font-size:12px;font-weight:700;color:var(--text);text-transform:uppercase;letter-spacing:.5px}
.plan-allee-body{display:flex;flex-direction:column;gap:5px}
.plan-rangee{display:flex;flex-wrap:nowrap;gap:4px}
.plan-pill{position:relative;display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:8px;border:1px solid var(--border);background:var(--bg);font-family:ui-monospace,monospace;font-size:12px;font-weight:700;color:var(--text);letter-spacing:.03em;transition:border-color .15s,background .15s;cursor:pointer;font-family:inherit}
.plan-pill:hover{border-color:var(--accent);background:rgba(34,211,238,.06)}
body.light .plan-pill:hover{background:rgba(8,145,178,.06)}
.plan-pill-code{font-family:ui-monospace,monospace}
.plan-pill-dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:#94a3b8;flex-shrink:0}
.plan-pill-c-vert .plan-pill-dot{background:#34d399;box-shadow:0 0 0 2px rgba(52,211,153,.18)}
.plan-pill-c-jaune .plan-pill-dot{background:#fbbf24;box-shadow:0 0 0 2px rgba(251,191,36,.22)}
.plan-pill-c-orange .plan-pill-dot{background:#fb923c;box-shadow:0 0 0 2px rgba(251,146,60,.20)}
.plan-pill-c-rouge .plan-pill-dot{background:#f87171;box-shadow:0 0 0 2px rgba(248,113,113,.20)}

/* Tooltip custom emplacement (position:fixed, attaché au body) */
.plan-pill-tip{position:fixed;min-width:200px;max-width:260px;background:var(--card);border:1px solid var(--border);border-radius:10px;padding:10px 12px;box-shadow:0 8px 24px rgba(0,0,0,.35);opacity:0;visibility:hidden;pointer-events:none;transition:opacity .12s ease;z-index:9000;font-family:'Segoe UI',system-ui,sans-serif;font-weight:500;letter-spacing:normal;text-align:left;white-space:normal}
body.light .plan-pill-tip{box-shadow:0 8px 24px rgba(15,23,42,.12)}
.plan-pill-tip.show{opacity:1;visibility:visible}
.plan-pill-tip-code{font-family:ui-monospace,monospace;font-size:13px;font-weight:800;color:var(--text);margin-bottom:6px;letter-spacing:.03em}
.plan-pill-tip-row{font-size:12px;color:var(--text2);line-height:1.4;display:flex;align-items:center;gap:6px;margin-top:2px}
.plan-pill-tip-jours{font-weight:700}
.plan-pill-tip-jours.plan-pill-c-vert{color:#16a34a}
body:not(.light) .plan-pill-tip-jours.plan-pill-c-vert{color:#34d399}
.plan-pill-tip-jours.plan-pill-c-jaune{color:#d97706}
body:not(.light) .plan-pill-tip-jours.plan-pill-c-jaune{color:#fbbf24}
.plan-pill-tip-jours.plan-pill-c-orange{color:#ea580c}
body:not(.light) .plan-pill-tip-jours.plan-pill-c-orange{color:#fb923c}
.plan-pill-tip-jours.plan-pill-c-rouge{color:#dc2626}
body:not(.light) .plan-pill-tip-jours.plan-pill-c-rouge{color:#f87171}
.plan-pill-tip-sub,.plan-pill-tip-refs{color:var(--muted);font-size:11px}
.plan-legend{display:flex;flex-wrap:wrap;gap:10px;margin-top:8px;font-size:11px;color:var(--muted)}
.plan-legend-item{display:inline-flex;align-items:center;gap:5px;padding:2px 8px;border-radius:6px;background:var(--card);border:1px solid var(--border);font-weight:600}

/* Détail emplacement (violet forcé) */
.invv2-detail .invv2-back{margin-bottom:14px;color:var(--inv-v);font-weight:700}
.invv2-detail .invv2-back:hover{background:var(--inv-v-bg-soft)}
.invv2-scorecard{background:linear-gradient(135deg,var(--card) 0%,var(--inv-v-bg-soft) 100%);border:1.5px solid var(--inv-v-bg);border-left:6px solid var(--inv-v);border-radius:12px;padding:18px 20px;margin-bottom:14px;box-shadow:0 2px 8px var(--inv-v-bg-soft)}
.invv2-detail-title{font-size:24px;font-weight:800;color:var(--inv-v);font-family:monospace;letter-spacing:.3px;margin-bottom:10px;text-shadow:0 0 1px var(--inv-v-bg)}
.invv2-last-info{font-size:13px;color:var(--text);margin-bottom:14px;font-weight:500}
.invv2-last-info strong{color:var(--inv-v);font-weight:800}
.invv2-last-info.invv2-last-none{color:var(--text2);font-style:italic}
.invv2-detail-stats{display:flex;gap:10px;flex-wrap:wrap}
.invv2-stat{background:var(--card);border:1.5px solid var(--inv-v-bg);border-radius:10px;padding:8px 14px;min-width:90px}
.invv2-stat-label{font-size:10px;color:var(--text2);text-transform:uppercase;letter-spacing:.5px;font-weight:700;margin-bottom:2px}
.invv2-stat-value{font-size:18px;font-weight:800;color:var(--inv-v);line-height:1.1;font-family:monospace}

/* Header carte avec bouton "Ajouter un produit" */
.invv2-prod-card{margin-bottom:4px;border:1.5px solid var(--inv-v-bg)}
.invv2-prod-card .card-header{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:12px 16px;border-bottom:1.5px solid var(--inv-v-bg);background:var(--inv-v-bg-soft)}
.invv2-prod-card .card-title{color:var(--inv-v);font-weight:800;letter-spacing:.2px}
.invv2-btn-add-product{background:var(--inv-v);color:var(--inv-v-text);border:0;border-radius:8px;padding:8px 14px;font-weight:800;font-size:12px;cursor:pointer;font-family:inherit;display:inline-flex;align-items:center;gap:6px;transition:filter .15s,box-shadow .15s;box-shadow:0 2px 6px var(--inv-v-shadow)}
.invv2-btn-add-product:hover{filter:brightness(1.06);box-shadow:0 3px 10px var(--inv-v-shadow)}
.invv2-btn-add-product:active{transform:translateY(1px)}
.invv2-prod-list{padding:0}
.invv2-prod-row{display:flex;align-items:center;gap:14px;padding:12px 16px;border-bottom:1px solid var(--border);transition:background .2s,border-color .2s;position:relative}
.invv2-prod-row:last-child{border-bottom:0}
.invv2-prod-row:not(.invv2-validated):hover{background:var(--inv-v-bg-soft)}
.invv2-prod-row.invv2-validated{background:color-mix(in srgb,var(--success) 18%,transparent);border-left:4px solid var(--success)}
.invv2-prod-row.invv2-added{border-left:4px solid var(--inv-v)}
.invv2-prod-row.invv2-added.invv2-validated{border-left:4px solid var(--success)}
.invv2-prod-main{flex:1;min-width:0}
.invv2-prod-ref{font-family:monospace;font-weight:800;font-size:14px;color:var(--text);letter-spacing:.2px;display:flex;align-items:center;gap:6px}
.invv2-prod-badge-new{display:inline-block;background:var(--inv-v);color:var(--inv-v-text);font-size:9px;font-weight:800;padding:2px 6px;border-radius:4px;letter-spacing:.5px;text-transform:uppercase}
.invv2-prod-info{font-size:11px;color:var(--text2);margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.invv2-prod-qty{display:flex;flex-direction:column;align-items:flex-end;gap:1px;font-family:monospace;min-width:100px;text-align:right}
.invv2-prod-qty-main{font-size:14px;font-weight:700;color:var(--text)}
.invv2-prod-qty-new{font-size:15px;font-weight:800;color:var(--inv-v)}
.invv2-prod-qty-old{font-size:11px;color:var(--muted);text-decoration:line-through}
.invv2-prod-actions{display:flex;gap:6px;flex-shrink:0}
.invv2-btn-modify{background:var(--inv-v-bg);color:var(--inv-v);border:1.5px solid var(--inv-v);border-radius:8px;padding:7px 14px;font-weight:800;font-size:12px;cursor:pointer;font-family:inherit;transition:filter .15s,background .15s}
.invv2-btn-modify:hover{background:var(--inv-v-bg-strong)}
.invv2-btn-validate{background:var(--success);color:var(--inv-v-text);border:0;border-radius:8px;padding:7px 12px;font-weight:900;font-size:14px;cursor:pointer;min-width:38px;font-family:inherit;line-height:1;transition:filter .15s;box-shadow:0 2px 6px color-mix(in srgb,var(--success) 30%,transparent)}
.invv2-btn-validate:hover{filter:brightness(1.06)}
.invv2-btn-cancel{background:var(--success);color:var(--inv-v-text);border:0;border-radius:8px;padding:7px 12px;font-weight:900;font-size:14px;cursor:pointer;min-width:38px;font-family:inherit;line-height:1;transition:filter .15s,background .15s,color .15s}
.invv2-btn-cancel:hover{background:var(--danger);color:#fff}
.invv2-btn-note{background:transparent;color:var(--text2);border:1.5px solid var(--border);border-radius:8px;padding:7px 12px;font-weight:700;font-size:12px;cursor:pointer;font-family:inherit;transition:border-color .15s,color .15s,background .15s}
.invv2-btn-note:hover{border-color:var(--inv-v);color:var(--inv-v);background:var(--inv-v-bg-soft)}
.invv2-btn-note.has-comment{border-color:var(--inv-v);color:var(--inv-v);background:var(--inv-v-bg-soft);font-weight:800}
.invv2-prod-comment-preview{margin-top:6px;font-size:12px;color:var(--text2);background:var(--inv-v-bg-soft);border:1px dashed var(--inv-v-bg);border-radius:8px;padding:6px 10px;line-height:1.4;display:flex;align-items:flex-start;gap:8px;font-style:italic}
.invv2-prod-comment-tag{font-style:normal;font-weight:800;font-size:10px;letter-spacing:.5px;text-transform:uppercase;color:var(--inv-v);background:var(--card);border:1px solid var(--inv-v-bg);border-radius:5px;padding:1px 6px;flex-shrink:0;margin-top:1px}
.invv2-empty-card{margin-bottom:4px;border:1.5px solid var(--inv-v-bg)}
.invv2-action-bar{display:flex;justify-content:center;margin:16px 0 4px}
.invv2-btn-to-validate{background:var(--card);border:1.5px solid var(--inv-v-bg);color:var(--text2);border-radius:12px;padding:12px 28px;font-weight:700;font-size:14px;opacity:.9}
.invv2-btn-validate-all{background:var(--inv-v);color:var(--inv-v-text);border:0;border-radius:12px;padding:14px 36px;font-weight:800;font-size:15px;cursor:pointer;font-family:inherit;box-shadow:0 4px 16px var(--inv-v-shadow);transition:filter .15s,transform .1s,box-shadow .15s;letter-spacing:.3px}
.invv2-btn-validate-all:hover{filter:brightness(1.08);box-shadow:0 6px 20px var(--inv-v-shadow)}
.invv2-btn-validate-all:active{transform:translateY(1px)}
.invv2-history-card{margin-top:4px;border:1.5px solid var(--inv-v-bg)}
.invv2-history-card .card-header{background:var(--inv-v-bg-soft);border-bottom:1.5px solid var(--inv-v-bg)}
.invv2-history-card .card-title{color:var(--inv-v);font-weight:800}
.invv2-hist-list{padding:0}
.invv2-hist-row{display:grid;grid-template-columns:110px 1fr auto;gap:12px;padding:10px 16px;border-bottom:1px solid var(--border);font-size:13px;align-items:center;transition:background .15s}
.invv2-hist-row:last-child{border-bottom:0}
.invv2-hist-row:hover{background:var(--inv-v-bg-soft)}
.invv2-hist-date{color:var(--inv-v);font-weight:700;font-family:monospace}
.invv2-hist-op{color:var(--text)}
.invv2-hist-meta{font-size:11px;color:var(--text2);font-family:monospace;font-weight:600}
.invv2-btn-more{background:transparent;border:1.5px solid var(--inv-v);color:var(--inv-v);border-radius:8px;padding:9px 14px;font-weight:800;font-size:12px;cursor:pointer;font-family:inherit;width:calc(100% - 24px);margin:10px 12px 10px;transition:background .15s,color .15s}
.invv2-btn-more:hover{background:var(--inv-v);color:var(--inv-v-text)}
.invv2-hist-block{border-bottom:1px solid var(--border)}
.invv2-hist-block:last-child{border-bottom:0}
.invv2-hist-block .invv2-hist-row{border-bottom:0}
.invv2-hist-comments{padding:0 16px 12px 16px;display:flex;flex-direction:column;gap:6px}
.invv2-hist-comment{background:var(--inv-v-bg-soft);border-left:3px solid var(--inv-v);border-radius:6px;padding:8px 12px}
.invv2-hist-comment-head{font-size:12px;color:var(--text);margin-bottom:3px;line-height:1.4}
.invv2-hist-comment-ref{font-family:monospace;font-weight:800;color:var(--inv-v)}
.invv2-hist-comment-des{color:var(--text2);font-weight:500}
.invv2-hist-comment-body{font-size:13px;color:var(--text);line-height:1.5;white-space:pre-wrap;word-break:break-word}

/* Modals violets — texte boutons selon thème */
.btn-confirm.invv2-confirm{background:var(--inv-v);color:var(--inv-v-text);font-weight:800}
.btn-confirm.invv2-confirm:hover{filter:brightness(1.06)}
.invv2-modal-title{color:var(--inv-v);font-weight:800}
.invv2-modal-sub-empl{color:var(--inv-v);font-weight:700}

/* Mobile */
@media (max-width: 720px){
  .invv2-empl-row{padding:12px}
  .invv2-empl-code{font-size:14px}
  .invv2-jours{font-size:16px;padding:4px 10px;min-width:66px}
  .invv2-jours-sub{font-size:9px;max-width:140px}
  .invv2-legend{gap:6px;padding:8px 10px}
  .invv2-legend-item{font-size:10px}
  .invv2-prod-card .card-header{flex-wrap:wrap;gap:8px}
  .invv2-prod-row{flex-wrap:wrap;gap:10px}
  .invv2-prod-main{flex:1 1 100%;min-width:0}
  .invv2-prod-qty{min-width:auto;flex-direction:row;align-items:baseline;gap:8px}
  .invv2-prod-actions{margin-left:auto}
  .invv2-hist-row{grid-template-columns:1fr;gap:2px}
  .invv2-hist-date{font-size:12px}
  .invv2-hist-op{font-size:12px}
  .invv2-detail-title{font-size:20px}
}

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
.mvt-type-btn.sel-pf-entree{background:color-mix(in srgb,var(--pf-entree) 18%,transparent);color:var(--pf-entree);border-color:var(--pf-entree)}
.mvt-type-btn.sel-pf-sortie{background:color-mix(in srgb,var(--pf-sortie) 18%,transparent);color:var(--pf-sortie);border-color:var(--pf-sortie)}
.mvt-type-btn.sel-inventaire{background:rgba(167,139,250,.15);color:var(--c2);border-color:var(--c2)}
.modal-field{margin-bottom:14px}
.empl-suggestions{background:var(--bg);border:1px solid var(--border);border-radius:8px;
  margin-top:4px;overflow:hidden;max-height:140px;overflow-y:auto}
.empl-sugg-item-with-unit{display:flex;align-items:center;gap:10px;justify-content:space-between}
.empl-sugg-item-label{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.empl-sugg-item-unit-badge{flex-shrink:0;font-family:'Segoe UI',system-ui,sans-serif;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.4px;padding:3px 8px;border-radius:999px;background:var(--accent-bg);color:var(--accent);border:1px solid var(--border)}
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
.ref-client-search-wrap{margin-bottom:14px}
.ref-client-search{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:12px 16px;
  color:var(--text);font-size:14px;font-family:inherit;transition:border-color .15s}
.ref-client-search:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12)}
.ref-client-hint{font-size:12px;color:var(--muted);margin:0 0 12px;line-height:1.55}
.ref-client-units{margin:0 0 14px;padding:12px 14px;background:var(--accent-bg);border:1px solid var(--border);border-radius:10px;font-size:13px;color:var(--text2);line-height:1.5}
.ref-client-units strong{color:var(--text);font-weight:700}
.ref-client-results{margin-top:4px}
.ref-client-table{width:100%;border-collapse:collapse;font-size:13px}
.ref-client-table th{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.4px;color:var(--muted);
  text-align:left;padding:8px 10px;border-bottom:1px solid var(--border)}
.ref-client-table td{padding:10px;border-bottom:1px solid var(--border);vertical-align:top}
.ref-client-table tr:last-child td{border-bottom:none}
.ref-client-table .ref-col{font-family:monospace;font-weight:700;color:var(--text)}
.ref-client-empty{font-size:13px;color:var(--muted);padding:8px 0}
.ref-client-loading{font-size:12px;color:var(--accent);padding:8px 0}
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
.btn-confirm.pf-entree{background:var(--pf-entree)}
.btn-confirm.pf-sortie{background:var(--pf-sortie)}
.btn-confirm.inventaire{background:var(--c2)}
.mp-modal-actions .btn.btn-pf-entree{background:var(--pf-entree);color:#0a0e17;border:none;font-weight:700}
.mp-modal-actions .btn.btn-pf-sortie{background:var(--pf-sortie);color:#fff;border:none;font-weight:700}
body.light .mp-modal-actions .btn.btn-pf-entree{color:#fff}

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
<script src="/static/mysifa_postit.js"></script>
<script src="/static/mysifa_cmdk.js"></script>
<script src="/static/mysifa_calc.js"></script>
<script src="/static/chat_mentions.js"></script>
<script src="/static/chat_widget.js?v=11"></script>
<script src="/static/chat_widget_v2.js?v=7"></script>
<script src="/static/mysifa_ai_chat.js"></script>
<script>
/*__TRACA_GUIDE__*/
const API = window.location.origin;

// ── State ───────────────────────────────────────────────────────
let S = {
  user: null,
  tab: 'dashboard',
  stockReadOnly: false,
  tracaOnly: false,
  fabStockMode: false,  // fabrication : accès limité aux sections Matières premières + Outils
  sidebarOpen: false,
  searchQuery: '',
  searchResults: null,
  selProduit: null,
  selEmpl: null,
  dashboard: null,
  inventaireList: [],
  // Inventaire v2 (par emplacement)
  invV2List: null,           // [{emplacement, label, nb_refs, total_qte, jours_depuis, couleur, ...}]
  invV2Detail: null,         // {emplacement, refs, history, last_inventaire}
  invV2Search: '',           // recherche emplacement
  invV2Validated: {},        // { [produit_id]: true } produits validés (vert)
  invV2Modifs: {},           // { [produit_id]: {qte_avant, qte_apres} } modifs en attente
  invV2Comments: {},         // { [produit_id]: string } commentaires en attente (visibles après validation)
  invV2HistoryExpanded: false,
  invV2Submitting: false,
  invAlertCount: null,       // nb d'emplacements rouge/orange (inventaire en retard)
  planEntrepot: null,        // codes emplacements_plan
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
  refClientQ: '',
  refClientResults: null,
  refClientLoading: false,
  // Matières premières
  matieres: null,
  matieresCat: 'tout',
  matieresQ: '',
  matieresCardMenuId: null,
  selMatiere: null,
  mpModal: null,
  pfModal: null,
  addPfModalOpen: false,
  matieresAdminOpen: false,
  matieresAdminList: null,
  matieresAdminEditId: null,
  matieresAdminAddError: '',
  matieresAdminSaving: false,
  matieresAdminFilterCat: 'tout',
  matieresAdminFilterQ: '',
  matieresAdminAddSeed: null,
  mpSousSections: null,
  // Produits finis (onglet dédié)
  pfStock: null,
  pfMouvements: null,
  pfCatalogue: null,
  pfKpis: null,
  pfQ: '',
  pfEmplQ: '',
  pfLoading: false,
  pfTotalMouvements: 0,
  pfModal: null,
  pfConfirmSortie: null,
  // Produits de négoce (onglet dédié)
  ngStock: null,
  ngMouvements: null,
  ngCatalogue: null,
  ngKpis: null,
  ngLoading: false,
  ngTotalMouvements: 0,
  ngModal: null,
  ngFilters: null,
  ngSelDetail: null,
  ngSelDetailLoading: false,
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
  // Monitoring réconciliation ERP
  monitoring: null,
  // Valorisation stock (Contrôle)
  valorisation: null,
  // Référentiel laizes (chargé une fois au boot)
  laizes: null,
  // Compteur matières incomplètes (frontal/glassine/complexe sans laize/prix/métrage)
  matieresIncompleteCount: 0,
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
    if (!r.ok) {
      const e = await r.json().catch(() => ({}));
      throw new Error(apiErrorDetail(e.detail, r.status));
    }
    return await r.json();
  } catch(e) {
    if (e.message && e.message.includes('Failed to fetch')) throw new Error('API non disponible');
    throw e;
  }
}

function apiErrorDetail(detail, status) {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map(d => d.msg || d.message || JSON.stringify(d)).join(' — ');
  }
  if (detail && typeof detail === 'object') {
    return detail.msg || detail.message || JSON.stringify(detail);
  }
  return 'Erreur ' + status;
}

async function apiUpload(path, formData) {
  const r = await fetch(API + path, { method: 'POST', credentials: 'include', body: formData });
  if (r.status === 401) { window.location.href = '/'; return null; }
  if (!r.ok) {
    let detail = null;
    const ct = (r.headers.get('content-type') || '').toLowerCase();
    if (ct.includes('application/json')) {
      const e = await r.json().catch(() => ({}));
      detail = e.detail;
    } else {
      detail = await r.text().catch(() => null);
    }
    const msg = apiErrorDetail(detail, r.status);
    const err = new Error(msg);
    err.status = r.status;
    throw err;
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
function escHtml(s) {
  if (s == null || s === undefined) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
function escAttr(s) { return escHtml(s).replace(/'/g, '&#39;'); }

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
function refUnitePluriel(unite, qty) {
  const u = String(unite || '').trim();
  if (!u) return '—';
  const n = Number(qty) || 0;
  const uLow = u.toLowerCase();
  if (uLow === 'étiquettes' || uLow === 'etiquettes' || uLow === 'étiquette' || uLow === 'etiquette') {
    return n > 1 ? 'étiquettes' : 'étiquette';
  }
  return n > 1 ? u + 's' : u;
}
function refClientUnitsSummary(rows) {
  const counts = new Map();
  rows.forEach(r => {
    const u = String(r.unite || '').trim();
    counts.set(u, (counts.get(u) || 0) + 1);
  });
  const entries = [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'fr'));
  if (!entries.length) return '—';
  return entries.map(([u, n]) => {
    if (!u) return fN(n) + ' sans unité';
    return fN(n) + ' par ' + refUnitePluriel(u, n);
  }).join(', ');
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
    'move': '<polyline points="5 9 2 12 5 15"/><polyline points="9 5 12 2 15 5"/><polyline points="15 19 12 22 9 19"/><polyline points="19 9 22 12 19 15"/>',
    'atelier': '<path d="M2 20h20"/><path d="M4 20V10l8-6 8 6v10"/><path d="M9 20v-5h6v5"/><path d="M10 10h4"/><path d="M12 10v5"/>',
    'scan': '<rect x="3" y="3" width="5" height="5"/><rect x="16" y="3" width="5" height="5"/><rect x="3" y="16" width="5" height="5"/><line x1="21" y1="16" x2="21" y2="21"/><line x1="16" y1="21" x2="21" y2="21"/><line x1="11" y1="3" x2="11" y2="7"/><line x1="11" y1="11" x2="11" y2="17"/><line x1="3" y1="11" x2="7" y2="11"/><line x1="11" y1="11" x2="17" y2="11"/>',
    'inbox': '<polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>',
    'check-circle': '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
    'upload': '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>',
    'download': '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
    'edit': '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>',
    'copy': '<rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
    'trash-2': '<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/>',
    'search': '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
    'plus-circle': '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/>',
    'zap': '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    'mail': '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    'shopping-cart': '<circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/>',
    'trash': '<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
    'euro': '<path d="M4 10h12"/><path d="M4 14h9"/><path d="M19 6a7.7 7.7 0 0 0-5.2-2A7.9 7.9 0 0 0 6 12c0 4.4 3.5 8 7.8 8 2 0 3.8-.8 5.2-2"/>',
    // dollar-sign (Lucide) — utilisé pour le toggle « prix en USD » de la valorisation
    'dollar-sign': '<line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
    'alert-triangle': '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
    'file-text': '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>',
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
    else if (typeof s === 'string') e.style.cssText = s;
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
    if (d) {
      S.selProduit = d;
      S.selEmpl = null;
      S.selMatiere = null;
      S.searchResults = null;
      clearSearch();
      closeSidebar();
      if (typeof stockSyncUrl === 'function') stockSyncUrl();
      render();
    }
  } catch(e) { showToast(e.message, 'error'); }
}

async function openPfProduitPage(reference, produitId) {
  const pid = parseInt(produitId, 10);
  if (pid > 0) {
    await loadProduit(pid);
    return;
  }
  const ref = String(reference || '').trim();
  if (!ref) return;
  try {
    const r = await api('/api/stock/search?q=' + encodeURIComponent(ref) + '&limit=10');
    const p = (r && r.produits || []).find(x => (x.reference || '').toUpperCase() === ref.toUpperCase());
    if (p && p.id) await loadProduit(p.id);
    else showToast('Référence introuvable.', 'error');
  } catch (e) { showToast(e.message, 'error'); }
}

// Renvoie true si l'événement clic doit laisser le navigateur ouvrir l'URL
// (nouvel onglet/fenêtre) au lieu d'exécuter la navigation interne JS.
function stockClickOpensNewTab(e) {
  if (!e) return false;
  // Cmd (macOS), Ctrl (Win/Linux), Shift, Alt, ou clic milieu
  return !!(e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button === 1);
}

function stockDeepLinkUrl(params) {
  const sp = new URLSearchParams();
  Object.keys(params || {}).forEach(k => {
    if (params[k] != null && params[k] !== '') sp.set(k, String(params[k]));
  });
  return '/stock?' + sp.toString();
}

function stockPfRefLink(reference, produitId, label) {
  const txt = label != null ? label : (reference || '—');
  if (!reference || txt === '—') return el('span', null, txt);
  const pid = parseInt(produitId, 10);
  const href = stockDeepLinkUrl(pid > 0
    ? { tab: 'produits-finis', produit: pid }
    : { tab: 'produits-finis', ref: reference });
  return el('a', {
    cls: 'mvt-ref-link',
    href: href,
    style: 'text-decoration:none',
    on: { click: (e) => {
      if (stockClickOpensNewTab(e)) return; // laisse le navigateur ouvrir en nouvel onglet
      e.preventDefault();
      e.stopPropagation();
      openPfProduitPage(reference, produitId);
    } },
  }, txt);
}

function stockMpRefLink(matiereId, label, options) {
  const mid = parseInt(matiereId, 10);
  const opts = options || {};
  const txt = label != null ? label : '';
  if (!mid) return el('span', null, txt);
  const href = stockDeepLinkUrl({ tab: 'matieres', matiere: mid });
  const baseStyle = opts.style || 'text-decoration:none';
  return el('a', {
    cls: 'mvt-ref-link',
    href: href,
    style: baseStyle,
    title: opts.title || null,
    on: { click: (e) => {
      if (stockClickOpensNewTab(e)) return;
      e.preventDefault();
      e.stopPropagation();
      loadMatiere(mid);
    } },
  }, txt);
}

async function loadEmplacement(empl) {
  try {
    const d = await api('/api/stock/emplacements/' + encodeURIComponent(empl));
    if (d) {
      S.selEmpl = d; S.selProduit = null; S.searchResults = null;
      clearSearch();
      if (typeof stockSyncUrl === 'function') stockSyncUrl();
      render();
    }
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
    if (m.matiere_id) {
      await loadMatiere(m.matiere_id);
      return;
    }
    const ref = (m.reference || '').trim();
    if (ref) {
      try {
        if (!S.matieres) {
          const d = await api('/api/stock/matieres');
          S.matieres = Array.isArray(d) ? d : [];
        }
        const found = (S.matieres || []).find(x =>
          (x.reference || '').toUpperCase() === ref.toUpperCase()
        );
        if (found) await loadMatiere(found.id);
        else {
          S.matieresQ = ref;
          S.matieresCat = 'tout';
          goToTab('matieres');
        }
      } catch (e) {
        showToast(e.message, 'error');
      }
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
  const _emplLinkCls = (code) => {
    if (isStockEmplacementAuSol(code)) return 'mvt-empl-link mvt-empl-link-au-sol';
    if (isStockEmplacementSortieProd(code)) return 'mvt-empl-link mvt-empl-link-sortie-prod';
    return 'mvt-empl-link';
  };
  if (codes.length === 1) {
    return el('button', {
      cls: _emplLinkCls(codes[0]),
      type: 'button',
      on: { click: (e) => { e.stopPropagation(); loadEmplacement(codes[0]); } },
    }, stockEmplLabel(codes[0]));
  }
  const wrap = el('span', { cls: 'hist-empl-chain' });
  codes.forEach((code, i) => {
    if (i) wrap.appendChild(el('span', { cls: 'hist-empl-sep' }, ' → '));
    wrap.appendChild(el('button', {
      cls: _emplLinkCls(code),
      type: 'button',
      on: { click: (e) => { e.stopPropagation(); loadEmplacement(code); } },
    }, stockEmplLabel(code)));
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
      if (S.tab === 'referentiel') renderReferentielView();
      else renderContent();
    }
  } catch (e) {}
}

async function loadInventaireList() {
  // Inventaire v2 : liste des emplacements avec jours depuis dernier inventaire complet.
  S.invV2Detail = null;
  S.invV2Validated = {};
  S.invV2Modifs = {};
  S.invV2Comments = {};
  S.invV2HistoryExpanded = false;
  try {
    const d = await api('/api/stock/inventaire-v2/emplacements');
    if (d) {
      S.invV2List = Array.isArray(d) ? d : [];
      _updateInvAlertCount();
      renderContent();
    }
  } catch(e) { showToast(e.message, 'error'); }
}

function _updateInvAlertCount() {
  const list = S.invV2List || [];
  S.invAlertCount = list.filter(e => e.couleur === 'rouge' || e.couleur === 'orange').length || null;
}

async function loadInvAlertCountBackground() {
  try {
    const d = await api('/api/stock/inventaire-v2/emplacements');
    if (Array.isArray(d)) {
      S.invV2List = d;
      _updateInvAlertCount();
      render(); // refresh sidebar badge
    }
  } catch(e) {}
}

// ── Référentiel laizes (chargé une fois au boot) ─────────────────
async function loadLaizesReferentiel() {
  try {
    const d = await api('/api/admin/mp_laizes');
    if (Array.isArray(d)) S.laizes = d;
  } catch(e) { S.laizes = []; }
}

async function loadMatieresIncompleteCount() {
  try {
    const d = await api('/api/stock/matieres/incompletes');
    S.matieresIncompleteCount = d?.count || 0;
  } catch(e) { S.matieresIncompleteCount = 0; }
}

async function loadInventaireEmpl(code) {
  try {
    const d = await api('/api/stock/inventaire-v2/emplacement/' + encodeURIComponent(code));
    if (d) {
      // Bascule sur l'onglet inventaire et nettoie tout autre détail
      S.tab = 'inventaire';
      S.selEmpl = null;
      S.selProduit = null;
      S.selMatiere = null;
      S.invV2Detail = d;
      S.invV2Validated = {};
      S.invV2Modifs = {};
      S.invV2Comments = {};
      S.invV2HistoryExpanded = false;
      try { updateNavActive(); } catch(e){}
      renderContent();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  } catch(e) { showToast(e.message, 'error'); }
}

function openEmplInventaireConfirm(code) {
  closeMroot();
  const label = (typeof stockEmplLabel === 'function') ? stockEmplLabel(code) : code;
  const overlay = el('div', { cls:'modal-overlay', on:{ click: e => { if(e.target===overlay) closeMroot(); }}});
  const sheet = el('div', { cls:'modal-sheet', style:{ maxWidth:'440px' } },
    el('span', { cls:'modal-handle' }),
    el('div', { cls:'modal-title invv2-modal-title' }, 'Lancer un inventaire ?'),
    el('div', { cls:'modal-sub' },
      'Vous êtes sur le point de lancer un inventaire pour l\'emplacement ',
      el('span', { cls:'invv2-modal-sub-empl' }, label),
      '. Toutes les références présentes devront être comptées et validées.'
    ),
    el('div', { style:{ fontSize:'12px', color:'var(--muted)', marginBottom:'14px', lineHeight:'1.5' } },
      'Aucune modification ne sera appliquée tant que vous n\'aurez pas validé l\'inventaire complet en fin de procédure.'
    ),
    el('div', { cls:'modal-actions', style:{ marginTop:'14px' } },
      el('button', { cls:'btn-cancel', on:{ click: closeMroot } }, 'Annuler'),
      el('button', { cls:'btn-confirm invv2-confirm', on:{ click: () => {
        closeMroot();
        loadInventaireEmpl(code);
      }}}, 'Lancer l\'inventaire')
    )
  );
  sheet.addEventListener('click', e => e.stopPropagation());
  overlay.appendChild(sheet);
  document.getElementById('mroot').appendChild(overlay);
}

function clearInventaireEmpl() {
  S.invV2Detail = null;
  S.invV2Validated = {};
  S.invV2Modifs = {};
  S.invV2Comments = {};
  S.invV2HistoryExpanded = false;
  loadInventaireList();
}

function invV2ToggleValidate(pid) {
  S.invV2Validated[pid] = true;
  renderContent();
}

function invV2CancelValidate(pid) {
  const d = S.invV2Detail;
  const row = d && (d.refs || []).find(r => r.produit_id === pid);
  const isAdded = !!(row && row._added);
  // Modal de confirmation pour annuler la validation
  closeMroot();
  const overlay = el('div', { cls:'modal-overlay', on:{ click: e => { if(e.target===overlay) closeMroot(); }}});
  const sheet = el('div', { cls:'modal-sheet', style: { maxWidth: '420px' } },
    el('span', { cls:'modal-handle' }),
    el('div', { cls:'modal-title invv2-modal-title' }, isAdded ? 'Retirer ce produit ?' : 'Annuler la validation ?'),
    el('div', { cls:'modal-sub' }, isAdded
      ? 'Ce produit a été ajouté manuellement. Il sera retiré de cet inventaire.'
      : 'Voulez-vous vraiment annuler ce que vous venez de valider ? La ligne redeviendra modifiable.'
    ),
    el('div', { cls:'modal-actions', style:{marginTop:'20px'} },
      el('button', { cls:'btn-cancel', on:{ click: closeMroot } }, 'Non, garder'),
      el('button', { cls:'btn-confirm invv2-confirm', on:{ click: () => {
        delete S.invV2Validated[pid];
        delete S.invV2Modifs[pid];
        if (isAdded && d) {
          d.refs = d.refs.filter(r => r.produit_id !== pid);
        }
        closeMroot();
        renderContent();
      }}}, isAdded ? 'Oui, retirer' : 'Oui, annuler')
    )
  );
  overlay.appendChild(sheet);
  document.getElementById('mroot').appendChild(overlay);
}

function invV2OpenModifyModal(pid, currentQty, reference, designation, unite) {
  closeMroot();
  let valStr = String(currentQty != null ? currentQty : '');
  let commentStr = S.invV2Comments[pid] || '';
  const overlay = el('div', { cls:'modal-overlay', on:{ click: e => { if(e.target===overlay) closeMroot(); }}});
  const inp = el('input', {
    cls:'field-input',
    type:'number', step:'0.01', min:'0', value: valStr, autocomplete:'off', inputmode:'decimal',
    style:{ width:'100%', fontSize:'16px', textAlign:'right', fontFamily:'monospace', direction:'ltr' }
  });
  inp.addEventListener('input', e => { valStr = e.target.value; });
  inp.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); commentInp.focus(); } });
  const commentInp = el('textarea', {
    cls:'field-input',
    placeholder:'Commentaire (optionnel — visible une fois l\'inventaire validé)',
    rows: 3,
    maxlength: 1000,
    style:{ width:'100%', resize:'vertical', fontFamily:'inherit', fontSize:'13px', lineHeight:'1.5' }
  });
  commentInp.value = commentStr;
  commentInp.addEventListener('input', e => { commentStr = e.target.value; });
  const validateBtn = el('button', { cls:'btn-confirm invv2-confirm', on:{ click: () => {
    const q = parseFloat(valStr);
    if (isNaN(q) || q < 0) { showToast('Quantité invalide.', 'error'); return; }
    S.invV2Modifs[pid] = { qte_avant: parseFloat(currentQty)||0, qte_apres: q };
    S.invV2Validated[pid] = true;
    const txt = (commentStr || '').trim();
    if (txt) S.invV2Comments[pid] = txt;
    else delete S.invV2Comments[pid];
    closeMroot();
    renderContent();
  }}}, 'Valider');
  const sheet = el('div', { cls:'modal-sheet', style: { maxWidth: '460px' } },
    el('span', { cls:'modal-handle' }),
    el('div', { cls:'modal-title invv2-modal-title' }, 'Modifier la quantité'),
    el('div', { cls:'modal-sub' }, escHtml(reference) + (designation ? ' — ' + escHtml(designation) : '')),
    el('div', { cls:'modal-field' },
      el('label', { cls:'field-label' }, 'Quantité réelle comptée' + (unite ? ' ('+escHtml(unite)+')' : '')),
      inp
    ),
    el('div', { cls:'modal-field' },
      el('label', { cls:'field-label' }, 'Commentaire'),
      commentInp
    ),
    el('div', { cls:'modal-actions', style:{marginTop:'14px'} },
      el('button', { cls:'btn-cancel', on:{ click: closeMroot } }, 'Annuler'),
      validateBtn
    )
  );
  overlay.appendChild(sheet);
  document.getElementById('mroot').appendChild(overlay);
  requestAnimationFrame(() => { try { inp.focus(); inp.select(); } catch(e){} });
}

function invV2OpenCommentModal(pid, reference, designation) {
  closeMroot();
  let commentStr = S.invV2Comments[pid] || '';
  const overlay = el('div', { cls:'modal-overlay', on:{ click: e => { if(e.target===overlay) closeMroot(); }}});
  const ta = el('textarea', {
    cls:'field-input',
    placeholder:'Note libre · visible une fois l\'inventaire validé',
    rows: 4,
    maxlength: 1000,
    style:{ width:'100%', resize:'vertical', fontFamily:'inherit', fontSize:'13px', lineHeight:'1.5' }
  });
  ta.value = commentStr;
  ta.addEventListener('input', e => { commentStr = e.target.value; });
  const saveBtn = el('button', { cls:'btn-confirm invv2-confirm', on:{ click: () => {
    const txt = (commentStr || '').trim();
    if (txt) S.invV2Comments[pid] = txt;
    else delete S.invV2Comments[pid];
    closeMroot();
    renderContent();
  }}}, 'Enregistrer');
  const actions = [
    el('button', { cls:'btn-cancel', on:{ click: closeMroot } }, 'Annuler'),
    saveBtn,
  ];
  if (S.invV2Comments[pid]) {
    actions.splice(1, 0, el('button', {
      cls:'btn-ghost', style:{ color:'var(--danger)' },
      on:{ click: () => { delete S.invV2Comments[pid]; closeMroot(); renderContent(); } }
    }, 'Supprimer'));
  }
  const sheet = el('div', { cls:'modal-sheet', style: { maxWidth: '460px' } },
    el('span', { cls:'modal-handle' }),
    el('div', { cls:'modal-title invv2-modal-title' }, 'Note d\'inventaire'),
    el('div', { cls:'modal-sub' }, escHtml(reference) + (designation ? ' — ' + escHtml(designation) : '')),
    el('div', { cls:'modal-field' },
      el('label', { cls:'field-label' }, 'Commentaire'),
      ta
    ),
    el('div', { cls:'modal-actions', style:{marginTop:'14px',gap:'8px',flexWrap:'wrap'} }, ...actions)
  );
  overlay.appendChild(sheet);
  document.getElementById('mroot').appendChild(overlay);
  requestAnimationFrame(() => { try { ta.focus(); } catch(e){} });
}

function invV2OpenAddProductModal() {
  const d = S.invV2Detail;
  if (!d) return;
  closeMroot();
  let _pid = null, _ref = '', _designation = '', _unite = '';

  const overlay = el('div', { cls:'modal-overlay', on:{ click: e => { if(e.target===overlay) closeMroot(); }}});

  const refInp = el('input', {
    cls:'field-input',
    type:'text', placeholder:'Référence produit (ex. 973/0019)', autocomplete:'off',
    style:{ direction:'ltr' }
  });
  const suggWrap = el('div', { cls:'empl-suggestions', style:{ display:'none' } });
  const refError = el('div', { style:{ color:'var(--danger)', fontSize:'12px', marginTop:'4px', display:'none' } });

  let refTimer = null;
  refInp.addEventListener('input', () => {
    _pid = null; refError.style.display = 'none';
    clearTimeout(refTimer);
    const q = refInp.value.trim();
    if (!q) { suggWrap.innerHTML = ''; suggWrap.style.display = 'none'; return; }
    refTimer = setTimeout(async () => {
      try {
        const r = await api('/api/stock/search?q=' + encodeURIComponent(q) + '&limit=8');
        const prods = (r && r.produits) || [];
        suggWrap.innerHTML = '';
        if (!prods.length) { suggWrap.style.display = 'none'; return; }
        prods.forEach(p => {
          const item = el('div', { cls:'empl-suggestion-item',
            on:{ click: () => {
              refInp.value = p.reference;
              _pid = p.id; _ref = p.reference;
              _designation = p.designation || '';
              _unite = p.unite || '';
              refError.style.display = 'none';
              suggWrap.innerHTML = ''; suggWrap.style.display = 'none';
              try { qteInp.focus(); } catch(e){}
            }}
          },
            el('span', { style:{ fontWeight:'700', marginRight:'8px' } }, p.reference),
            el('span', { style:{ color:'var(--muted)', fontSize:'12px' } }, p.designation || '')
          );
          suggWrap.appendChild(item);
        });
        suggWrap.style.display = '';
      } catch(e) { /* silence */ }
    }, 180);
  });

  const qteInp = el('input', {
    cls:'field-input',
    type:'number', step:'0.01', min:'0', placeholder:'0', inputmode:'decimal',
    style:{ direction:'ltr', textAlign:'right', fontFamily:'monospace', fontSize:'16px' }
  });

  const confirmBtn = el('button', { cls:'btn-confirm invv2-confirm', on:{ click: async () => {
    const ref = refInp.value.trim();
    const qte = parseFloat(qteInp.value);
    if (!ref) { showToast('Référence requise.', 'error'); return; }
    if (!qte || qte <= 0) { showToast('Quantité requise (> 0).', 'error'); return; }
    if (!_pid) {
      try {
        const r = await api('/api/stock/search?q=' + encodeURIComponent(ref) + '&limit=10');
        const match = (r && r.produits || []).find(p =>
          (p.reference || '').toUpperCase() === ref.toUpperCase()
        );
        if (!match) {
          refError.textContent = 'Référence produit introuvable.';
          refError.style.display = '';
          return;
        }
        _pid = match.id; _ref = match.reference;
        _designation = match.designation || '';
        _unite = match.unite || '';
      } catch(e) { showToast(e.message, 'error'); return; }
    }
    const existing = (d.refs || []).find(r => r.produit_id === _pid);
    if (existing) {
      // Si déjà présent, on bascule sur "modifier" pour cette ligne
      closeMroot();
      const qActuelle = parseFloat(existing.quantite) || 0;
      showToast('Produit déjà présent — ouvrez « Modifier ».', 'info');
      return;
    }
    d.refs.push({
      produit_id: _pid,
      reference: _ref,
      designation: _designation,
      unite: _unite,
      quantite: 0,
      nb_lots: 0,
      lots: [],
      _added: true,
    });
    S.invV2Modifs[_pid] = { qte_avant: 0, qte_apres: qte };
    S.invV2Validated[_pid] = true;
    closeMroot();
    renderContent();
    showToast(_ref + ' ajouté · ' + fU(qte, _unite));
  }}}, 'Ajouter le produit');

  const sheet = el('div', { cls:'modal-sheet', style:{ maxWidth:'480px' } },
    el('span', { cls:'modal-handle' }),
    el('div', { cls:'modal-title invv2-modal-title' }, 'Ajouter un produit à l\'inventaire'),
    el('div', { cls:'modal-sub' },
      'Emplacement ',
      el('span', { cls:'invv2-modal-sub-empl' }, d.label || d.emplacement)
    ),
    el('div', { cls:'modal-field' },
      el('label', { cls:'field-label' }, 'Référence produit *'),
      refInp, suggWrap, refError
    ),
    el('div', { cls:'modal-field' },
      el('label', { cls:'field-label' }, 'Quantité comptée *' + (_unite ? ' ('+_unite+')' : '')),
      qteInp
    ),
    el('div', { cls:'modal-actions', style:{ marginTop:'14px' } },
      el('button', { cls:'btn-cancel', on:{ click: closeMroot } }, 'Annuler'),
      confirmBtn
    )
  );
  sheet.addEventListener('click', e => e.stopPropagation());
  overlay.appendChild(sheet);
  document.getElementById('mroot').appendChild(overlay);
  requestAnimationFrame(() => { try { refInp.focus(); } catch(e){} });
}

function invV2ValidateFullInventaire() {
  const d = S.invV2Detail; if (!d) return;
  const modifications = Object.keys(S.invV2Modifs).map(pid => ({
    produit_id: parseInt(pid, 10),
    qte_apres: parseFloat(S.invV2Modifs[pid].qte_apres),
  }));
  const refsById = {};
  (d.refs || []).forEach(r => { refsById[r.produit_id] = r; });
  const commentaires = Object.keys(S.invV2Comments).map(pid => {
    const r = refsById[parseInt(pid, 10)] || {};
    return {
      produit_id: parseInt(pid, 10),
      reference: r.reference || '',
      designation: r.designation || '',
      commentaire: S.invV2Comments[pid],
    };
  }).filter(c => (c.commentaire || '').trim());
  const nbProduits = (d.refs || []).length;
  const nbModifs = modifications.length;
  const nbComments = commentaires.length;

  closeMroot();
  const overlay = el('div', { cls:'modal-overlay', on:{ click: e => { if(e.target===overlay) closeMroot(); }}});
  const confirmBtn = el('button', { cls:'btn-confirm invv2-confirm', on:{ click: async () => {
    if (S.invV2Submitting) return;
    S.invV2Submitting = true;
    confirmBtn.disabled = true;
    confirmBtn.textContent = 'Validation en cours…';
    try {
      const r = await api('/api/stock/inventaire-v2/valider', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({
          emplacement: d.emplacement,
          nb_produits: nbProduits,
          modifications,
          commentaires,
        })
      });
      if (r && r.success) {
        showToast('Inventaire validé · ' + (r.nb_modifications||0) + ' modification(s) appliquée(s).');
        closeMroot();
        clearInventaireEmpl();
      }
    } catch(e) {
      showToast(e.message || 'Erreur lors de la validation.', 'error');
      confirmBtn.disabled = false;
      confirmBtn.textContent = 'Confirmer la validation';
    } finally {
      S.invV2Submitting = false;
    }
  }}}, 'Confirmer la validation');

  const sheet = el('div', { cls:'modal-sheet', style: { maxWidth: '460px' } },
    el('span', { cls:'modal-handle' }),
    el('div', { cls:'modal-title invv2-modal-title' }, "Valider l'inventaire ?"),
    el('div', { cls:'modal-sub' },
      'Emplacement ' + escHtml(d.label || d.emplacement) + ' · ' +
      nbProduits + ' produit' + (nbProduits>1?'s':'') + ' inventorié' + (nbProduits>1?'s':'') + ' · ' +
      nbModifs + ' modification' + (nbModifs>1?'s':'') + ' à appliquer' +
      (nbComments ? ' · ' + nbComments + ' note' + (nbComments>1?'s':'') : '') + '.'
    ),
    el('div', { style:{fontSize:'12px',color:'var(--muted)',marginBottom:'14px',lineHeight:'1.5'} },
      'Les ajustements de stock seront appliqués maintenant et tracés dans l\'historique des mouvements.'
    ),
    el('div', { cls:'modal-actions', style:{marginTop:'14px'} },
      el('button', { cls:'btn-cancel', on:{ click: closeMroot } }, 'Annuler'),
      confirmBtn
    )
  );
  overlay.appendChild(sheet);
  document.getElementById('mroot').appendChild(overlay);
}

async function submitMouvement(body) {
  try {
    const r = await api('/api/stock/mouvement', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body) });
    if (!r) return;
    showToast('Stock mis à jour → ' + fN(r.quantite_apres));
    S.modalMvt = null;
    S.pfModal = null;
    document.querySelector('.modal-overlay')?.remove();
    closeMroot();
    if (S.selProduit) await loadProduit(S.selProduit.produit.id);
    else if (S.selEmpl) await loadEmplacement(S.selEmpl.emplacement);
    else if (S.tab === 'dashboard') await loadDashboard();
    else if (S.tab === 'produits-finis') await loadProduitsFinis();
    else if (S.tab === 'inventaire') await loadInventaireList();
  } catch(e) { showToast(e.message, 'error'); }
}

function fmtStockParisNow() {
  const d = new Date();
  try {
    const parts = new Intl.DateTimeFormat('fr-FR', {
      timeZone: 'Europe/Paris',
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', hour12: false,
    }).formatToParts(d);
    const g = (t) => (parts.find(p => p.type === t) || {}).value || '';
    return g('day') + '/' + g('month') + '/' + g('year') + ' ' + g('hour') + ':' + g('minute');
  } catch (e) {
    return fDateTime(d.toISOString().slice(0, 16));
  }
}

function buildLotTransporteurBtn(produitId, emplacement, row) {
  const qLot = row.quantite_lot_fifo != null ? row.quantite_lot_fifo : row.quantite;
  const unite = row.unite || (S.selProduit && S.selProduit.produit && S.selProduit.produit.unite) || '';
  const refLabel = row.reference || (S.selProduit && S.selProduit.produit && S.selProduit.produit.reference) || '';
  return el('button', {
    cls: 'empl-lot-exp-btn',
    type: 'button',
    attrs: {
      title: 'Sortir pour expédition transporteur',
      'aria-label': 'Transporteur — expédition',
    },
    on: { click: (ev) => {
      ev.stopPropagation();
      sortirLot(produitId, emplacement, qLot, unite, refLabel, row.nb_lots, { expedition: true });
    }},
  }, iconEl('truck', 18));
}

function buildLotOutBtn(produitId, emplacement, row) {
  const qLot = row.quantite_lot_fifo != null ? row.quantite_lot_fifo : row.quantite;
  const unite = row.unite || (S.selProduit && S.selProduit.produit && S.selProduit.produit.unite) || '';
  const refLabel = row.reference || (S.selProduit && S.selProduit.produit && S.selProduit.produit.reference) || '';
  return el('button', {
    cls: 'empl-lot-out-btn',
    type: 'button',
    attrs: { title: 'Sortir le lot FIFO', 'aria-label': 'Sortir le lot FIFO' },
    on: { click: (ev) => {
      ev.stopPropagation();
      sortirLot(produitId, emplacement, qLot, unite, refLabel, row.nb_lots);
    }},
  }, iconEl('trash-2', 18));
}

function buildLotMoveBtn(produitId, emplacement, row) {
  const qLot = row.quantite_lot_fifo != null ? row.quantite_lot_fifo : row.quantite;
  const unite = row.unite || (S.selProduit && S.selProduit.produit && S.selProduit.produit.unite) || '';
  const refLabel = row.reference || (S.selProduit && S.selProduit.produit && S.selProduit.produit.reference) || '';
  return el('button', {
    cls: 'empl-lot-move-btn',
    type: 'button',
    attrs: { title: 'Déplacer le lot', 'aria-label': 'Déplacer le lot' },
    on: { click: (ev) => {
      ev.stopPropagation();
      openMoveLotModal(produitId, emplacement, qLot, unite, refLabel, row.nb_lots);
    }},
  }, iconEl('move', 18));
}

function buildLotActionBtns(produitId, emplacement, row) {
  if (S.stockReadOnly) return null;
  return el('div', { cls: 'empl-lot-actions' },
    buildLotTransporteurBtn(produitId, emplacement, row),
    buildLotOutBtn(produitId, emplacement, row),
    buildLotMoveBtn(produitId, emplacement, row),
  );
}

async function openMoveLotModal(produitId, emplacement, qLot, unite, refLabel, nbLots) {
  document.querySelector('.modal-overlay')?.remove();
  
  const qLabel = fU(qLot, unite || '');
  const locLbl = stockEmplLabel(emplacement);
  const loc = refLabel ? (refLabel + ' · ' + locLbl) : locLbl;
  
  const overlay = el('div', { cls:'modal-overlay', on:{ click: e => { if(e.target===overlay) closeMroot(); }}});
  const sheet = el('div', { cls:'modal-sheet', style: { maxWidth: '480px' } });
  sheet.addEventListener('click', e => e.stopPropagation());
  
  // Destination emplacement input with suggestions
  const destEmplInp = el('input', { 
    cls:'field-input', 
    type:'text', 
    placeholder:'Emplacement destination (ex. A001)', 
    autocomplete:'off',
    style:{direction:'ltr', textTransform:'uppercase'}
  });
  const suggWrap = el('div', { cls:'empl-suggestions', style:{position:'absolute', top:'100%', left:'0', right:'0', zIndex:'120'} });
  const destError = el('div', { cls:'field-error', style:{color:'var(--danger)',fontSize:'12px',marginTop:'4px',display:'none'} });
  
  let destTimer = null;
  let selectedDestEmpl = null;
  
  destEmplInp.addEventListener('input', () => {
    selectedDestEmpl = null;
    destError.style.display = 'none';
    clearTimeout(destTimer);
    const q = destEmplInp.value.trim().toUpperCase();
    if (!q) { suggWrap.innerHTML = ''; suggWrap.style.display = 'none'; return; }
    destTimer = setTimeout(() => {
      const empls = getStockEmplacements();
      const filtered = empls.filter(e => e.includes(q)).slice(0, 8);
      suggWrap.innerHTML = '';
      if (!filtered.length) { suggWrap.style.display = 'none'; return; }
      filtered.forEach(code => {
        const _dCls = 'empl-suggest-item' + (isStockEmplacementAuSol(code) ? ' empl-suggest-au-sol' : isStockEmplacementSortieProd(code) ? ' empl-suggest-sortie-prod' : '');
        const _dTxt = isStockEmplacementAuSol(code) ? (STOCK_EMPL_AU_SOL_LABEL + ' — stock à expédier') : isStockEmplacementSortieProd(code) ? STOCK_EMPL_SORTIE_PROD_LABEL : code;
        const row = el('div', { cls: _dCls,
          on:{ click: () => {
            destEmplInp.value = code;
            selectedDestEmpl = code;
            suggWrap.innerHTML = '';
            suggWrap.style.display = 'none';
          }}
        }, _dTxt);
        suggWrap.appendChild(row);
      });
      suggWrap.style.display = '';
    }, 150);
  });
  
  const confirmBtn = el('button', { 
    cls:'btn-confirm', 
    style:{background:'var(--violet)', color:'#fff'},
    on:{ click: async () => {
      const destEmpl = (destEmplInp.value.trim().toUpperCase() || selectedDestEmpl);
      if (!destEmpl) { showToast('Emplacement destination requis', 'error'); return; }
      if (destEmpl === emplacement) { showToast('Même emplacement que la source', 'error'); return; }
      
      // Confirmation modal
      const confirmOverlay = el('div', { cls:'modal-overlay', on:{ click: e => { if(e.target===confirmOverlay) closeMroot(); }}});
      const confirmSheet = el('div', { cls:'modal-sheet', style: { maxWidth: '420px' } });
      confirmSheet.addEventListener('click', e => e.stopPropagation());
      
      const qtyHighlight = el('span', { style:{fontWeight:'800', fontSize:'18px', color:'var(--violet)'} }, qLabel);
      const destHighlight = el('span', { style:{fontWeight:'700', color:'var(--violet)'} }, stockEmplLabel(destEmpl));
      
      confirmSheet.appendChild(el('div', { cls:'modal-title' }, 'Confirmer le déplacement'));
      confirmSheet.appendChild(el('div', { cls:'modal-sub' }, 
        'Déplacer ', qtyHighlight, ' vers ', destHighlight, ' ?'
      ));
      if (nbLots > 1) {
        confirmSheet.appendChild(el('div', { cls:'mp-hint', style:{marginTop:'8px'} }, 
          nbLots + ' lots actifs à cet emplacement — seul le plus ancien sera déplacé.'
        ));
      }
      
      confirmSheet.appendChild(el('div', { cls:'modal-actions', style:{marginTop:'20px'} },
        el('button', { cls:'btn-cancel', type:'button', on:{ click:() => confirmOverlay.remove() } }, 'Annuler'),
        el('button', {
          cls:'btn-confirm',
          style:{background:'var(--violet)', color:'#fff'},
          on:{ click: async () => {
            try {
              const r = await api('/api/stock/deplacer-lot', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  produit_id: produitId,
                  emplacement_source: emplacement,
                  emplacement_destination: destEmpl,
                }),
              });
              if (!r) return;
              showToast('Lot déplacé — stock : ' + fN(r.quantite_apres));
              confirmOverlay.remove();
              overlay.remove();
              if (S.selProduit) await loadProduit(S.selProduit.produit.id);
              else if (S.selEmpl) await loadEmplacement(S.selEmpl.emplacement);
              else if (S.tab === 'produits-finis') await loadProduitsFinis();
              else if (S.tab === 'dashboard') await loadDashboard();
            } catch (e) { showToast(e.message, 'error'); }
          }}
        }, 'Faire le déplacement')
      ));
      
      confirmOverlay.appendChild(confirmSheet);
      document.body.appendChild(confirmOverlay);
    }}
  }, 'Déplacer');
  
  const destField = el('div', { cls:'modal-field', style:{position:'relative'} },
    el('label', { cls:'field-label' }, 'Emplacement destination'),
    destEmplInp,
    suggWrap,
    destError
  );
  
  sheet.appendChild(el('div', { cls:'modal-title' }, 'Déplacer le lot'));
  sheet.appendChild(el('div', { cls:'modal-sub' }, 
    'Déplacer ', el('span', { style:{fontWeight:'700', fontSize:'16px', color:'var(--violet)'} }, qLabel), 
    ' depuis ', el('span', { style:{fontWeight:'600'} }, loc)
  ));
  if (nbLots > 1) {
    sheet.appendChild(el('div', { cls:'mp-hint', style:{marginTop:'8px'} }, 
      nbLots + ' lots actifs à cet emplacement — seul le plus ancien sera déplacé.'
    ));
  }
  sheet.appendChild(destField);
  sheet.appendChild(el('div', { cls:'modal-actions', style:{marginTop:'20px'} },
    el('button', { cls:'btn-cancel', type:'button', on:{ click:() => overlay.remove() } }, 'Annuler'),
    confirmBtn
  ));
  
  overlay.appendChild(sheet);
  document.body.appendChild(overlay);
  destEmplInp.focus();
}

async function sortirLot(produitId, emplacement, qLot, unite, refLabel, nbLots, opts) {
  const expedition = !!(opts && opts.expedition);
  const qLabel = fU(qLot, unite || '');
  const locLbl = stockEmplLabel(emplacement);
  const loc = refLabel ? (refLabel + ' · ' + locLbl) : locLbl;
  let msg = expedition
    ? ('Expédition transporteur — sortir le lot FIFO (' + qLabel + ') — ' + loc + ' ?')
    : ('Sortir le lot FIFO (' + qLabel + ') — ' + loc + ' ?');
  if (nbLots > 1) {
    msg += '\n\n' + nbLots + ' lots actifs à cet emplacement — seul le plus ancien sera retiré.';
  }
  if (!confirm(msg)) return;
  const payload = { produit_id: produitId, emplacement };
  if (expedition) {
    payload.note = 'Expédition transporteur — ' + fmtStockParisNow();
  }
  try {
    const r = await api('/api/stock/sortir-lot', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!r) return;
    showToast(expedition ? 'Lot expédié — stock : ' + fN(r.quantite_apres) : 'Lot sorti — stock : ' + fN(r.quantite_apres));
    if (S.selProduit) await loadProduit(S.selProduit.produit.id);
    else if (S.selEmpl) await loadEmplacement(S.selEmpl.emplacement);
    else if (S.tab === 'produits-finis') await loadProduitsFinis();
    else if (S.tab === 'dashboard') await loadDashboard();
  } catch (e) { showToast(e.message, 'error'); }
}

// Emplacements chargés depuis /api/stock/emplacements-list (plan + stock réel)
let _emplListFromDB = [];
const STOCK_EMPL_AU_SOL = 'Z0';
const STOCK_EMPL_AU_SOL_LABEL = 'Au sol - à expédier';
const STOCK_EMPL_SORTIE_PROD = 'Z1';
const STOCK_EMPL_SORTIE_PROD_LABEL = 'En attente - sortie de prod';
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
const _STOCK_ZONES_SPECIALES = [STOCK_EMPL_AU_SOL, STOCK_EMPL_SORTIE_PROD];
function allPageEmplacementChoices() {
  const base = [...new Set([..._emplListFromDB, ...loadPageEmplCustom()])]
    .filter(c => !_STOCK_ZONES_SPECIALES.includes(c))
    .sort();
  return [..._STOCK_ZONES_SPECIALES, ...base];
}
function isStockEmplacementAuSol(code) {
  return String(code || '').trim().toUpperCase() === STOCK_EMPL_AU_SOL;
}
function isStockEmplacementSortieProd(code) {
  return String(code || '').trim().toUpperCase() === STOCK_EMPL_SORTIE_PROD;
}
function isStockZoneSpeciale(code) {
  return _STOCK_ZONES_SPECIALES.includes(String(code || '').trim().toUpperCase());
}
function isStockEmplacementCode(s) {
  if (isStockZoneSpeciale(s)) return true;
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
function stockEmplLabel(code) {
  if (isStockEmplacementAuSol(code)) return STOCK_EMPL_AU_SOL_LABEL;
  if (isStockEmplacementSortieProd(code)) return STOCK_EMPL_SORTIE_PROD_LABEL;
  return String(code || '').trim().toUpperCase();
}
function stockEmplCodeClass(code) {
  if (isStockEmplacementAuSol(code)) return 'empl-code empl-au-sol';
  if (isStockEmplacementSortieProd(code)) return 'empl-code empl-sortie-prod';
  return 'empl-code';
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
    let extraCls = '';
    let label = code;
    if (isStockEmplacementAuSol(code)) { extraCls = ' empl-suggest-au-sol'; label = STOCK_EMPL_AU_SOL_LABEL + ' — stock à expédier'; }
    else if (isStockEmplacementSortieProd(code)) { extraCls = ' empl-suggest-sortie-prod'; label = STOCK_EMPL_SORTIE_PROD_LABEL; }
    row.className = 'empl-suggest-item' + extraCls;
    row.textContent = label;
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
  // Accès restreints selon le mode
  if (S.tracaOnly && tab !== 'traca') return;
  if (S.fabStockMode && !['production','matieres','historique','traca','plan-entrepot'].includes(tab)) return;
  // Arrêter la caméra si on quitte l'onglet réception
  if (tab !== 'reception' && S.recepScanning) recepStopCamera();
  S.tab = tab; S.selProduit = null; S.selEmpl = null; S.selMatiere = null; S.searchResults = null; S.showAddForm = false;
  if (tab !== 'produits-finis') { S.pfModal = null; closeMroot(); }
  if (tab !== 'negoce') { S.ngModal = null; S.ngSelDetail = null; S.ngSelDetailLoading = false; }
  if (tab !== 'referentiel') {
    S.refClientQ = '';
    S.refClientResults = null;
    S.refClientLoading = false;
    clearTimeout(_refClientSearchTimer);
  }
  if (tab !== 'dashboard') closeDashboardAddPfModal();
  if (tab !== 'traca') S.tracaPoste = null;
  if (tab !== 'monitoring') {
    if (S.monitoring) {
      S.monitoring.query = '';
      S.monitoring.filterStatut = null;
      S.monitoring.monPage = 'quantites';
    }
  }
  if (tab !== 'valorisation') {
    if (S.valorisation) {
      S.valorisation.query = '';
      S.valorisation.filterCategorie = null;
      S.valorisation.filterSousSection = null;
      S.valorisation.sortColumn = null;
      S.valorisation.sortDirection = 'asc';
    }
  }
  clearSearch(); closeSidebar();
  if (tab === 'historique') S.historiqueLoading = true;
  updateNavActive();
  stockSyncUrl();
  renderContent();
  if (tab === 'dashboard') loadDashboard();
  else if (tab === 'referentiel') loadDashboard();
  else if (tab === 'inventaire') loadInventaireList();
  else if (tab === 'reception') loadRecepHistory();
  else if (tab === 'matieres') loadMatieres();
  else if (tab === 'produits-finis') loadProduitsFinis();
  else if (tab === 'negoce') loadNegoce();
  else if (tab === 'historique') loadHistorique();
  else if (tab === 'plan-entrepot') loadPlanEntrepot();
  else if (tab === 'monitoring') loadMonitoring();
  else if (tab === 'valorisation') loadValorisation();
  else if (tab === 'production') loadProduction();
}

function updateNavActive() {
  document.querySelectorAll('.nav-btn[data-tab]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === S.tab && !S.selProduit && !S.selEmpl && !S.selMatiere);
  });
}

// Synchronise l'URL avec l'état courant (onglet + sélection) sans recharger la page.
// Permet de revenir au même endroit après un refresh ou un Cmd+clic.
function stockSyncUrl() {
  try {
    const sp = new URLSearchParams();
    if (S.tab && S.tab !== 'dashboard') sp.set('tab', S.tab);
    if (S.selMatiere && S.selMatiere.matiere && S.selMatiere.matiere.id) {
      sp.set('matiere', String(S.selMatiere.matiere.id));
    } else if (S.selProduit && S.selProduit.id) {
      sp.set('produit', String(S.selProduit.id));
    } else if (S.selEmpl && S.selEmpl.code) {
      sp.set('empl', S.selEmpl.code);
    }
    const qs = sp.toString();
    const url = '/stock' + (qs ? ('?' + qs) : '');
    if (window.location.pathname + window.location.search !== url) {
      history.replaceState(null, '', url);
    }
  } catch (e) { /* silencieux — l'URL est juste un confort */ }
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

  const confirmBtn = el('button', { cls:'btn-confirm pf-entree', on:{ click: async () => {
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

async function resolvePfProduitByRef(ref) {
  const term = String(ref || '').trim();
  if (!term) return null;
  const upper = term.toUpperCase();
  try {
    const r = await api('/api/stock/search?q=' + encodeURIComponent(term) + '&limit=15');
    const list = (r && r.produits) ? r.produits : [];
    let found = list.find(p => String(p.reference || '').toUpperCase() === upper);
    if (found) return found;
    if (list.length === 1) return list[0];
    const rows = await api('/api/stock/produits?q=' + encodeURIComponent(term) + '&limit=15');
    const arr = Array.isArray(rows) ? rows : [];
    found = arr.find(p => String(p.reference || '').toUpperCase() === upper);
    if (found) return found;
    return arr.length === 1 ? arr[0] : null;
  } catch (e) {
    return null;
  }
}

function wireStockProduitSearch(refInp, suggWrap, onSelect) {
  let timer = null;
  const runSearch = async (q) => {
    if (!q || q.length < 1) {
      suggWrap.innerHTML = '';
      return;
    }
    try {
      const r = await api('/api/stock/search?q=' + encodeURIComponent(q) + '&limit=8');
      const list = (r && r.produits) ? r.produits : [];
      suggWrap.innerHTML = '';
      if (!list.length) {
        suggWrap.appendChild(el('div', { cls: 'empl-sugg-item muted' }, 'Aucun résultat pour « ' + q + ' »'));
        suggWrap.style.display = 'block';
        return;
      }
      list.forEach(p => {
        const label = (p.reference || '') + (p.designation ? ' — ' + p.designation : '');
        const unite = String(p.unite || '').trim();
        const row = el('div', {
          cls: 'empl-sugg-item empl-sugg-item-with-unit',
          on: { mousedown: (e) => { e.preventDefault(); onSelect(p); } },
        },
          el('span', { cls: 'empl-sugg-item-label' }, label),
          unite ? el('span', { cls: 'empl-sugg-item-unit-badge' }, unite) : null,
        );
        suggWrap.appendChild(row);
      });
      suggWrap.style.display = 'block';
    } catch (e) {
      suggWrap.innerHTML = '';
      suggWrap.style.display = 'none';
    }
  };
  refInp.addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(() => runSearch(refInp.value.trim()), 220);
  });
  refInp.addEventListener('focus', () => {
    runSearch(refInp.value.trim());
  });
  refInp.addEventListener('keydown', async (e) => {
    if (e.key !== 'Enter') return;
    e.preventDefault();
    const p = await resolvePfProduitByRef(refInp.value);
    if (p) onSelect(p);
    else showToast('Référence introuvable.', 'error');
  });
  refInp.addEventListener('blur', () => {
    setTimeout(() => {
      if (document.activeElement === refInp) return;
      suggWrap.innerHTML = '';
      suggWrap.style.display = 'none';
    }, 220);
  });
}

function wireStockEmplSearch(emplInp, suggWrap) {
  let timer = null;
  const pick = (code) => {
    emplInp.value = String(code || '').toUpperCase();
    suggWrap.innerHTML = '';
    suggWrap.style.display = 'none';
  };
  const renderList = (codes) => {
    suggWrap.innerHTML = '';
    if (!codes.length) {
      suggWrap.appendChild(el('div', { cls: 'empl-sugg-item muted' }, 'Aucun emplacement'));
      suggWrap.style.display = 'block';
      return;
    }
    codes.forEach(code => {
      suggWrap.appendChild(el('div', {
        cls: 'empl-sugg-item',
        on: { mousedown: (e) => { e.preventDefault(); pick(code); } },
      }, stockEmplLabel(code)));
    });
    suggWrap.style.display = 'block';
  };
  const runLocal = (q) => {
    const qq = String(q || '').trim().toUpperCase();
    if (!qq) return allPageEmplacementChoices().slice(0, 12);
    return allPageEmplacementChoices().filter(c => c.includes(qq)).slice(0, 12);
  };
  const runSearch = async (q) => {
    const local = runLocal(q);
    if (!q) {
      renderList(local);
      return;
    }
    renderList(local);
    try {
      const r = await api('/api/stock/search?q=' + encodeURIComponent(q) + '&limit=8');
      const fromApi = (r?.emplacements || []).map(e => e.emplacement);
      renderList([...new Set([...local, ...fromApi])].slice(0, 12));
    } catch (e) {
      renderList(local);
    }
  };
  emplInp.addEventListener('focus', () => {
    runSearch(emplInp.value.trim());
  });
  emplInp.addEventListener('input', () => {
    emplInp.value = emplInp.value.toUpperCase();
    const q = emplInp.value.trim();
    clearTimeout(timer);
    timer = setTimeout(() => runSearch(q), 180);
  });
  emplInp.addEventListener('blur', () => {
    setTimeout(() => {
      if (document.activeElement === emplInp) return;
      suggWrap.innerHTML = '';
      suggWrap.style.display = 'none';
    }, 220);
  });
}

function searchEmplSugg(q, suggWrap, emplInp) {
  const inp = emplInp || emplInpRef;
  if (!inp) return;
  clearTimeout(emplTimer);
  if (!q) { suggWrap.innerHTML = ''; return; }
  emplTimer = setTimeout(async () => {
    try {
      const local = allPageEmplacementChoices().filter(c => c.includes(String(q).toUpperCase())).slice(0, 8);
      const r = await api('/api/stock/search?q=' + encodeURIComponent(q) + '&limit=8');
      const fromApi = (r?.emplacements || []).map(e => e.emplacement);
      const list = [...new Set([...local, ...fromApi])].slice(0, 12);
      suggWrap.innerHTML = '';
      list.forEach(emp => {
        suggWrap.appendChild(el('div', {
          cls: 'empl-sugg-item',
          on: { mousedown: (e) => {
            e.preventDefault();
            inp.value = emp;
            suggWrap.innerHTML = '';
          }},
        }, stockEmplLabel(emp)));
      });
    } catch (e) {}
  }, 220);
}

function buildMvtModal() {
  const { produit_id, ref, emplacement } = S.modalMvt;
  const type = S.modalType;

  const overlay = el('div', { cls:'modal-overlay', on:{ click: e => { if(e.target===overlay){S.modalMvt=null;overlay.remove();} }}});
  const sheet = el('div', { cls:'modal-sheet' });
  sheet.addEventListener('click', e => e.stopPropagation());

  const pfSelCls = { entree: 'pf-entree', sortie: 'pf-sortie', inventaire: 'inventaire' };
  const typeBtns = el('div', { cls:'mvt-type-btns' },
    ...['entree','sortie','inventaire'].map(t => {
      const labels = {entree:'↓ Entrée', sortie:'↑ Sortie', inventaire:'= Inventaire'};
      const b = el('button', { cls:'mvt-type-btn'+(S.modalType===t?' sel-'+pfSelCls[t]:''), on:{ click: () => {
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
  emplInp.addEventListener('input', e => {
    emplInp.value = e.target.value.toUpperCase();
    searchEmplSugg(emplInp.value, suggWrap, emplInp);
  });

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

  const confirmPfCls = type === 'inventaire' ? 'inventaire' : ('pf-' + type);
  const confirmBtn = el('button', { cls:'btn-confirm '+confirmPfCls, on:{ click: async () => {
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
    produits.forEach(p => {
      const isNegoce = (p.type === 'negoce');
      box.appendChild(
        el('div',{cls:'search-item',on:{click:()=>{
          if (isNegoce) {
            S.searchResults = null; clearSearch();
            if (S.tab !== 'negoce') goToTab('negoce');
            loadNgDetail(p.reference);
          } else {
            loadProduit(p.id);
          }
        }}},
          el('div',null,
            el('div',{cls:'si-ref'},p.reference),
            el('div',{cls:'si-des'},p.designation + (isNegoce ? ' · négoce' : '')),
          ),
          el('div',{cls:'si-badge'},fU(p.stock_total, p.unite))
        )
      );
    });
  }
  if (emplacements.length) {
    box.appendChild(el('div',{cls:'search-section-title'},'📍 Emplacements'));
    emplacements.forEach(e => box.appendChild(
      el('div',{cls:'search-item',on:{click:()=>loadEmplacement(e.emplacement)}},
        el('div',null,
          el('div',{cls:'si-ref'},stockEmplLabel(e.emplacement)),
          el('div',{cls:'si-des'},
            isStockEmplacementAuSol(e.emplacement)
              ? 'Stock à expédier · ' + e.nb_refs + ' référence' + (e.nb_refs > 1 ? 's' : '')
              : isStockEmplacementSortieProd(e.emplacement)
                ? 'Sortie de prod · ' + e.nb_refs + ' référence' + (e.nb_refs > 1 ? 's' : '')
                : e.nb_refs + ' référence' + (e.nb_refs > 1 ? 's' : '')
          ),
        ),
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
      const primary = (opts && opts.primary) ? String(opts.primary) : '';
      const refTxt = m.reference || (primary === 'emplacement' ? '' : m.emplacement) || '';
      const t = m.type_mouvement || '';
      const pfIconCls = (t === 'entree' || t === 'sortie') ? 'pf-' + t : t;
      const pfQteCls = (t === 'entree' || t === 'sortie') ? 'mvt-qte-pf-' + t : 'mvt-qte-' + t;
      const showEmplOnLine2 = primary !== 'emplacement' && m.emplacement;
      return el('div',{cls:'mvt-row'},
        el('div',{cls:'mvt-icon '+pfIconCls},icons[t]||'·'),
        el('div',{cls:'mvt-body'},
          el('div',{cls:'mvt-line1'},
            (m.produit_id && m.reference)
              ? el('button',{cls:'mvt-ref-link',type:'button',on:{click:()=>loadProduit(m.produit_id)}},m.reference)
              : el('span',null,refTxt || '—'),
            el('span',{cls:pfQteCls},signe+fU(m.quantite, unit))
          ),
          el('div',{cls:'mvt-line2'},
            fD(m.created_at),
            (showEmplOnLine2 ? el('span',null,' · ') : null),
            (showEmplOnLine2 ? stockHistEmplLinks(m.emplacement) : null),
            (actor ? el('span',null,' · '+actor) : null),
            (m.quantite_apres != null)
              ? el('span',null,' · Solde '+fU(m.quantite_apres, unit))
              : null,
          ),
          m.note?el('div',{cls:'mvt-note'},m.note):null
        )
      );
    }))
  );
}


let _refClientSearchTimer = null;

async function loadRefClientSearch(q) {
  const term = String(q || '').trim();
  if (!term) {
    S.refClientResults = null;
    S.refClientLoading = false;
    renderReferentielView();
    return;
  }
  S.refClientLoading = true;
  renderReferentielView();
  try {
    const rows = await api('/api/stock/produits?client=' + encodeURIComponent(term) + '&limit=500');
    S.refClientResults = Array.isArray(rows) ? rows : [];
  } catch (e) {
    S.refClientResults = [];
    showToast(e.message || 'Recherche impossible', 'error');
  } finally {
    S.refClientLoading = false;
    renderReferentielView();
  }
}

function onRefClientSearchInput(val) {
  S.refClientQ = val;
  clearTimeout(_refClientSearchTimer);
  const q = String(val || '').trim();
  if (!q) {
    S.refClientResults = null;
    S.refClientLoading = false;
    renderReferentielView();
    return;
  }
  S.refClientLoading = true;
  renderReferentielView();
  _refClientSearchTimer = setTimeout(() => loadRefClientSearch(q), 280);
}

function renderReferentielView() {
  if (S.tab !== 'referentiel' || S.selProduit || S.selEmpl) return;
  const ae = document.activeElement;
  const focusId = ae?.id;
  const caretStart = ae?.selectionStart;
  const caretEnd = ae?.selectionEnd;
  const area = document.getElementById('scroll-area');
  if (!area) return;
  area.innerHTML = '';
  const content = buildReferentielPage();
  if (content) area.appendChild(content);
  if (focusId) {
    const foc = document.getElementById(focusId);
    if (foc) {
      foc.focus();
      if (caretStart != null) {
        try { foc.setSelectionRange(caretStart, caretEnd); } catch (e) {}
      }
    }
  }
}

function buildReferentielClientSearchCard() {
  const q = String(S.refClientQ || '').trim();
  const searchInp = el('input', {
    cls: 'ref-client-search',
    id: 'ref-client-search',
    attrs: {
      type: 'text',
      placeholder: 'Numéro client (ex. 12345)',
      autocomplete: 'off',
    },
  });
  searchInp.value = S.refClientQ || '';
  searchInp.addEventListener('input', (e) => onRefClientSearchInput(e.target.value));
  searchInp.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      S.refClientQ = '';
      S.refClientResults = null;
      S.refClientLoading = false;
      clearTimeout(_refClientSearchTimer);
      renderReferentielView();
    }
  });

  const bodyKids = [
    el('p', { cls: 'ref-client-hint' },
      'Les références sont au format numéro client / numéro article. '
      + 'Saisissez un numéro client pour lister les références et les unités de vente associées.'
    ),
    el('div', { cls: 'ref-client-search-wrap' }, searchInp),
  ];

  if (S.refClientLoading) {
    bodyKids.push(el('div', { cls: 'ref-client-loading' }, 'Recherche…'));
  } else if (q) {
    const rows = S.refClientResults;
    if (rows === null) {
      /* attente debounce / API */
    } else if (!rows.length) {
      bodyKids.push(el('div', { cls: 'ref-client-empty' }, 'Aucun résultat pour « ' + q + ' »'));
    } else {
      const unitKinds = [...new Set(rows.map(r => String(r.unite || '').trim()).filter(Boolean))];
      const unitsSummary = refClientUnitsSummary(rows);
      bodyKids.push(el('div', { cls: 'ref-client-units' },
        el('span', null, rows.length + ' référence' + (rows.length > 1 ? 's' : '') + ' — '),
        el('strong', null, 'Unité' + (unitKinds.length > 1 ? 's' : '') + ' de vente : '),
        unitsSummary,
      ));
      const wrap = el('div', { cls: 'ref-client-results' });
      const table = el('table', { cls: 'ref-client-table' });
      table.appendChild(el('thead', null, el('tr', null,
        el('th', null, 'Référence'),
        el('th', null, 'Unité de vente'),
        el('th', null, 'Désignation'),
      )));
      const tbody = el('tbody', null);
      rows.slice().sort((a, b) => String(a.reference || '').localeCompare(String(b.reference || '')))
        .forEach(r => {
          tbody.appendChild(el('tr', null,
            el('td', { cls: 'ref-col' }, r.reference || '—'),
            el('td', null, r.unite || '—'),
            el('td', null, r.designation || '—'),
          ));
        });
      table.appendChild(tbody);
      wrap.appendChild(table);
      bodyKids.push(wrap);
    }
  }

  return el('div', { cls: 'ref-card ref-client-card' },
    el('div', { cls: 'ref-card-header' },
      el('div', { cls: 'card-title' }, 'Recherche par numéro client'),
    ),
    el('div', { cls: 'ref-card-body' }, ...bodyKids),
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
    buildReferentielClientSearchCard(),
    buildReferentielCard(),
    (!S.stockReadOnly) ? buildConvertUniteCard() : null,
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

// ── Modifier une unité de vente (référentiel) ────────────────────────
function _cuEnsureState() {
  if (!S.convUnit) {
    S.convUnit = {
      produit: null,         // {id, reference, designation, unite, stock_total}
      query: '',
      suggestions: [],
      suggLoading: false,
      newUnite: '',
      direction: 'origin_per_new', // 'origin_per_new' (N origine = 1 nouveau) ou 'new_per_origin'
      valeur: '',
      busy: false,
    };
  }
  return S.convUnit;
}

let _convUnitTimer = null;
async function _cuSearchProduit(q) {
  const st = _cuEnsureState();
  st.query = q;
  st.suggestions = [];
  if (!q || !q.trim()) {
    renderReferentielView();
    return;
  }
  st.suggLoading = true;
  renderReferentielView();
  try {
    const r = await api('/api/stock/search?q=' + encodeURIComponent(q.trim()) + '&limit=8');
    st.suggestions = (r && r.produits) ? r.produits : [];
  } catch (e) {
    st.suggestions = [];
  }
  st.suggLoading = false;
  renderReferentielView();
}

async function _cuSelectProduit(p) {
  const st = _cuEnsureState();
  // Récupérer le stock total via /api/stock/produits/{id}
  let stockTotal = 0;
  try {
    const d = await api('/api/stock/produits/' + p.id);
    stockTotal = Number(d.stock_total) || 0;
  } catch (e) {
    stockTotal = Number(p.stock_total) || 0;
  }
  st.produit = {
    id: p.id,
    reference: p.reference,
    designation: p.designation || '',
    unite: p.unite || '',
    stock_total: stockTotal,
  };
  st.query = '';
  st.suggestions = [];
  st.newUnite = '';
  st.valeur = '';
  st.direction = 'origin_per_new';
  renderReferentielView();
}

function _cuReset() {
  S.convUnit = null;
  renderReferentielView();
}

function _cuComputeFactor() {
  const st = _cuEnsureState();
  const v = parseFloat(String(st.valeur || '').replace(',', '.'));
  if (!isFinite(v) || v <= 0) return null;
  // direction = origin_per_new : N origine dans 1 nouveau → facteur = 1/N
  // direction = new_per_origin : M nouveau dans 1 origine → facteur = M
  return st.direction === 'origin_per_new' ? (1 / v) : v;
}

function _cuPreviewLine() {
  const st = _cuEnsureState();
  if (!st.produit || !st.newUnite) return '';
  const factor = _cuComputeFactor();
  if (factor == null) return '';
  const newStock = (st.produit.stock_total || 0) * factor;
  const oldUnite = st.produit.unite || '';
  return 'Stock actuel : ' + fU(st.produit.stock_total || 0, oldUnite)
    + '  →  ' + fU(newStock, st.newUnite);
}

async function _cuSubmit() {
  const st = _cuEnsureState();
  if (st.busy) return;
  if (!st.produit) { showToast('Sélectionnez un produit.', 'error'); return; }
  if (!st.newUnite || !String(st.newUnite).trim()) {
    showToast('Choisissez la nouvelle unité.', 'error'); return;
  }
  if ((st.newUnite || '').trim().toLowerCase() === (st.produit.unite || '').trim().toLowerCase()) {
    showToast('La nouvelle unité doit être différente de l\'actuelle.', 'error'); return;
  }
  const factor = _cuComputeFactor();
  if (factor == null) { showToast('Valeur invalide.', 'error'); return; }
  st.busy = true;
  renderReferentielView();
  try {
    const r = await api('/api/stock/produits/' + st.produit.id + '/convertir-unite', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        nouvelle_unite: String(st.newUnite).trim(),
        facteur: factor,
      }),
    });
    showToast('Unité changée : ' + (r.ancienne_unite || '?') + ' → '
      + (r.nouvelle_unite || '?') + ' (stock ' + fN(r.stock_total_avant || 0)
      + ' → ' + fN(r.stock_total_apres || 0) + ')', 'success');
    _cuReset();
  } catch (e) {
    st.busy = false;
    showToast(e.message || 'Échec de la conversion.', 'error');
    renderReferentielView();
  }
}

function buildConvertUniteCard() {
  const st = _cuEnsureState();
  const body = el('div', { cls: 'ref-card-body' });
  body.appendChild(el('p', { cls: 'ref-card-desc' },
    'Changez l\'unité de vente d\'une référence et appliquez la conversion '
    + 'sur toutes les quantités en stock. Les mouvements historiques sont préservés.',
  ));

  // Picker produit
  if (!st.produit) {
    const inp = el('input', {
      cls: 'ref-client-search',
      id: 'cu-produit-search',
      attrs: { type: 'text', placeholder: 'Rechercher une référence produit…', autocomplete: 'off' },
    });
    inp.value = st.query || '';
    inp.addEventListener('input', (e) => {
      st.query = e.target.value;
      clearTimeout(_convUnitTimer);
      _convUnitTimer = setTimeout(() => _cuSearchProduit(st.query), 220);
    });
    body.appendChild(el('div', { cls: 'ref-client-search-wrap' }, inp));

    if (st.suggLoading) {
      body.appendChild(el('div', { cls: 'cu-sugg-empty' }, 'Recherche…'));
    } else if (st.query && !st.suggestions.length) {
      body.appendChild(el('div', { cls: 'cu-sugg-empty' }, 'Aucun résultat pour « ' + st.query + ' »'));
    } else if (st.suggestions.length) {
      const sw = el('div', { cls: 'cu-sugg-list' });
      st.suggestions.forEach(p => {
        sw.appendChild(el('div', {
          cls: 'cu-sugg-row',
          on: { click: () => _cuSelectProduit(p) },
        },
          el('div', { cls: 'cu-sugg-main' },
            el('span', { cls: 'cu-sugg-ref' }, p.reference || '—'),
            p.designation ? el('span', { cls: 'cu-sugg-des' }, ' — ' + p.designation) : null,
          ),
          el('span', { cls: 'cu-sugg-unit' }, p.unite || '—'),
        ));
      });
      body.appendChild(sw);
    }
  } else {
    // Produit sélectionné
    body.appendChild(el('div', { cls: 'cu-prod-card' },
      el('div', { cls: 'cu-prod-info' },
        el('div', { cls: 'cu-prod-ref' }, st.produit.reference || '—'),
        el('div', { cls: 'cu-prod-des' }, st.produit.designation || ''),
        el('div', { cls: 'cu-prod-stock' },
          'Unité actuelle : ', el('strong', null, st.produit.unite || '—'),
          ' · Stock total : ', el('strong', null, fU(st.produit.stock_total || 0, st.produit.unite || '')),
        ),
      ),
      el('button', {
        cls: 'btn-ghost-sm cu-prod-reset', type: 'button',
        on: { click: () => { st.produit = null; st.newUnite = ''; st.valeur = ''; renderReferentielView(); } },
      }, '× Changer'),
    ));

    // Sélecteur nouvelle unité
    const allUnites = [...new Set([...PF_UNITES, ...STOCK_UNITS_BASE])].filter(u => u && u.toLowerCase() !== (st.produit.unite || '').toLowerCase());
    const unitSel = el('select', { id: 'cu-new-unite' });
    unitSel.appendChild(el('option', { value: '' }, '— Nouvelle unité —'));
    allUnites.forEach(u => {
      unitSel.appendChild(el('option', { value: u, selected: st.newUnite === u ? true : null }, u));
    });
    unitSel.addEventListener('change', () => { st.newUnite = unitSel.value; renderReferentielView(); });
    body.appendChild(el('div', { cls: 'cu-row' },
      el('label', { cls: 'cu-label' }, 'Nouvelle unité de vente'),
      unitSel,
    ));

    // Direction + valeur
    if (st.newUnite) {
      const oldU = st.produit.unite || 'origine';
      const newU = st.newUnite || 'nouvelle';
      const firstU = st.direction === 'origin_per_new' ? oldU : newU;
      const secondU = st.direction === 'origin_per_new' ? newU : oldU;
      const labelNode = el('label', { cls: 'cu-label' },
        'Combien de ',
        el('strong', { cls: 'cu-label-unit' }, firstU),
        ' dans 1 ',
        el('strong', { cls: 'cu-label-unit' }, secondU),
        ' ?',
      );

      const qInp = el('input', {
        id: 'cu-valeur',
        attrs: { type: 'number', min: '0', step: 'any', inputmode: 'decimal', placeholder: 'ex. 500' },
      });
      qInp.value = String(st.valeur || '');
      qInp.addEventListener('input', () => { st.valeur = qInp.value; renderReferentielView(); });

      const reverseBtn = el('button', {
        cls: 'btn-ghost-sm cu-reverse', type: 'button',
        attrs: { title: 'Inverser le sens de calcul' },
        on: { click: () => {
          st.direction = st.direction === 'origin_per_new' ? 'new_per_origin' : 'origin_per_new';
          renderReferentielView();
        } },
      }, iconEl('refresh-ccw', 12), ' Inverser');

      body.appendChild(el('div', { cls: 'cu-row' },
        labelNode,
        el('div', { cls: 'cu-input-row' }, qInp, reverseBtn),
      ));

      const preview = _cuPreviewLine();
      if (preview) {
        body.appendChild(el('div', { cls: 'cu-preview' },
          iconEl('refresh-ccw', 12),
          ' ' + preview,
        ));
      }

      body.appendChild(el('div', { cls: 'cu-actions' },
        el('button', {
          cls: 'btn-ghost-sm', type: 'button',
          on: { click: () => _cuReset() },
        }, 'Annuler'),
        el('button', {
          cls: 'btn btn-accent', type: 'button',
          attrs: { disabled: st.busy ? 'disabled' : null },
          on: { click: () => _cuSubmit() },
        }, st.busy ? 'Conversion…' : 'Valider la conversion'),
      ));
    }
  }

  return el('div', { cls: 'ref-card ref-convert-unite-card' },
    el('div', { cls: 'ref-card-header' },
      el('div', { cls: 'card-title' }, 'Modifier une unité de vente'),
    ),
    body,
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
    if (S.refClientQ.trim()) await loadRefClientSearch(S.refClientQ);
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

const MP_CAT_LABELS = { mandrin: 'Mandrin', palette: 'Palette', adhesif: 'Adhésif', carton: 'Carton', frontal: 'Frontal', glassine: 'Glassine', complexe: 'Complexe', autre: 'Autre' };

function mpCategorieKey(cat) {
  return String(cat || '').trim().toLowerCase();
}
function mpCtx(catOrMatiere) {
  if (catOrMatiere && typeof catOrMatiere === 'object') {
    return {
      categorie: mpCategorieKey(catOrMatiere.categorie),
      palettes_par_pile: parseFloat(catOrMatiere.palettes_par_pile) || 0,
      couleur: (catOrMatiere.couleur || '').trim(),
    };
  }
  return { categorie: mpCategorieKey(catOrMatiere), palettes_par_pile: 0, couleur: '' };
}
function mpIsBobineCategory(catOrMatiere) {
  const c = mpCtx(catOrMatiere).categorie;
  return c === 'frontal' || c === 'glassine' || c === 'complexe';
}
function mpIsGlassineCategory(catOrMatiere) {
  return mpCtx(catOrMatiere).categorie === 'glassine';
}
function mpUniteNom(catOrMatiere) {
  const c = mpCtx(catOrMatiere).categorie;
  if (mpIsBobineCategory(c)) return 'bobine';
  if (c === 'carton') return 'palette';
  if (c === 'palette') return 'palette';
  if (c === 'autre') return 'unite';
  return 'palette';
}
function mpUniteShort(catOrMatiere) {
  const u = mpUniteNom(catOrMatiere);
  if (u === 'bobine') return 'bob.';
  if (u === 'palette') return 'pal.';
  if (u === 'unite') return 'u.';
  return 'pal.';
}
function mpQuantiteFieldLabel(catOrMatiere) {
  const u = mpUniteNom(catOrMatiere);
  if (u === 'bobine') return 'Quantité (bobines)';
  if (u === 'palette') return 'Quantité (palettes)';
  if (u === 'unite') return 'Quantité (unités)';
  return 'Quantité (palettes)';
}
function mpSeuilFieldLabel(catOrMatiere) {
  const u = mpUniteNom(catOrMatiere);
  if (u === 'bobine') return 'Seuil d\'alerte (bobines)';
  if (u === 'palette') return 'Seuil d\'alerte (pal.)';
  if (u === 'unite') return 'Seuil d\'alerte (u.)';
  return 'Seuil d\'alerte (pal.)';
}
function mpStockMini(qty, catOrMatiere) {
  return fN(qty) + ' ' + mpUniteShort(mpCtx(catOrMatiere));
}
function mpStockLine(qty, catOrMatiere) {
  const ctx = mpCtx(catOrMatiere);
  return fN(qty) + ' ' + mpUniteShort(ctx);
}
function mpStockTotalLabel(catOrMatiere) {
  return 'Stock';
}
function mpQuantiteInputAttrs(catOrMatiere) {
  const c = mpCtx(catOrMatiere).categorie;
  if (c === 'palette') return { type: 'number', min: '40', step: '1' };
  if (mpIsBobineCategory(c) || c === 'mandrin' || c === 'carton') {
    return { type: 'number', min: '1', step: '1' };
  }
  if (c === 'autre') return { type: 'number', min: '0', step: '1' };
  return { type: 'number', min: '0.5', step: '0.5' };
}
function mpAdminHint(cat) {
  if (cat === 'palette') return 'Stock géré en palettes. Quantité minimale par saisie : 40.';
  if (cat === 'carton') return 'Stock géré en palettes.';
  if (cat === 'frontal') return 'Stock géré en bobines (réception par scan possible). Une sous-section permet de regrouper les frontaux par usage.';
  if (mpIsBobineCategory(cat)) return 'Stock géré en bobines (réception par scan possible).';
  if (cat === 'autre') return 'Stock géré en unités. Une sous-section permet de regrouper des références par usage.';
  return 'Stock géré en palettes (pal.).';
}
function mpIsPaletteCategory(catOrMatiere) {
  return mpCtx(catOrMatiere).categorie === 'palette';
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
const PF_MVT_TITLES = {
  entree: 'Entrée produit fini',
  sortie: 'Sortie produit fini',
};
const MP_PILL_CATS = [
  { id: 'tout', label: 'Tout' },
  { id: 'mandrin', label: 'Mandrins' },
  { id: 'palette', label: 'Palettes' },
  { id: 'adhesif', label: 'Adhésifs' },
  { id: 'carton', label: 'Cartons' },
  { id: 'frontal', label: 'Frontaux' },
  { id: 'glassine', label: 'Glassines' },
  { id: 'complexe', label: 'Complexes' },
  { id: 'autre', label: 'Autre' },
];

// Slug normalisé (sans accents, lowercase, alphanumérique) pour clé pill / classe CSS
function mpSousSectionSlug(ss) {
  return String(ss || '').toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '');
}

// Préfixe d'identifiant pour les pills de sous-section frontal promues en catégorie de 1er niveau.
// Exemple : 'frontal:couche' (slug normalisé).
const MP_FRONTAL_SS_PREFIX = 'frontal:';

function mpParseFrontalSsPillId(id) {
  // Renvoie { categorie:'frontal', sousSection:'<label>' } si l'id est une pill SS frontal, sinon null
  if (typeof id !== 'string' || id.indexOf(MP_FRONTAL_SS_PREFIX) !== 0) return null;
  return { categorie: 'frontal', sousSectionSlug: id.slice(MP_FRONTAL_SS_PREFIX.length) };
}

// Donne la liste des sous-sections frontal présentes dans une liste de matières.
// Renvoie [{ slug, label, count }] triés alpha. count peut inclure les "sans sous-section"
// sous une entrée slug='' / label='Sans sous-section' si certains items n'ont pas de SS.
function mpFrontalSousSections(matieres) {
  const map = new Map();
  let noneCount = 0;
  (matieres || []).forEach(m => {
    if (String(m.categorie || '').toLowerCase() !== 'frontal') return;
    const ss = (m.sous_section || '').trim();
    if (!ss) { noneCount += 1; return; }
    const slug = mpSousSectionSlug(ss);
    if (!slug) { noneCount += 1; return; }
    if (!map.has(slug)) map.set(slug, { slug, label: ss, count: 0 });
    map.get(slug).count += 1;
  });
  const out = Array.from(map.values()).sort((a, b) => a.label.localeCompare(b.label, 'fr'));
  if (noneCount > 0) out.push({ slug: '', label: 'Sans sous-section', count: noneCount });
  return out;
}

const MP_CATEGORIES_LAIZEES = new Set(['frontal', 'glassine', 'complexe']);
function mpIsLaizeeCategory(cat) {
  return MP_CATEGORIES_LAIZEES.has((cat || '').toLowerCase());
}

// Catégories qui ont la notion d'unité d'achat + conditionnement (unités/palette)
const MP_CATEGORIES_AVEC_CONDITIONNEMENT = new Set(['carton', 'adhesif', 'mandrin']);
function mpHasConditionnement(cat) {
  return MP_CATEGORIES_AVEC_CONDITIONNEMENT.has((cat || '').toLowerCase());
}
function mpUniteAchat(cat) {
  const c = (cat || '').toLowerCase();
  if (c === 'carton') return 'carton';
  if (c === 'adhesif') return 'kg';
  if (c === 'mandrin') return 'tube';
  return 'unité';
}

function isMatieresAdmin() {
  return S.user && ['superadmin', 'direction', 'administration'].includes(S.user.role);
}

function closeMroot() {
  const m = document.getElementById('mroot');
  if (m) m.innerHTML = '';
  S.mpModal = null;
  S.pfModal = null;
  S.addPfModalOpen = false;
}

function closeDashboardAddPfModal() {
  closeMroot();
}

function openDashboardAddPfModal() {
  S.addPfModalOpen = true;
  renderDashboardAddPfModal();
}

// Sentinelle pour "Sans sous-section" (string vide ou null en DB)
const MP_SOUS_SECTION_NONE = '__none__';

function filterMatieresList() {
  const list = S.matieres || [];
  const cat = S.matieresCat || 'tout';
  const ss = S.matieresSousSection || null;
  const q = (S.matieresQ || '').trim().toLowerCase();
  return list.filter(m => {
    if (cat !== 'tout' && m.categorie !== cat) return false;
    // Filtre sous-section (uniquement quand la catégorie courante en supporte une)
    if (ss && mpCategorieHasSousSection(cat)) {
      const matSs = (m.sous_section || '').trim();
      if (ss === MP_SOUS_SECTION_NONE) {
        if (matSs) return false;
      } else {
        if (matSs.toLowerCase() !== ss.toLowerCase()) return false;
      }
    }
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
  if (S.selMatiere && S.selMatiere.matiere) {
    const updated = (S.matieres || []).find(m => m.id === S.selMatiere.matiere.id);
    if (updated) S.selMatiere.matiere = updated;
  }
  renderMatieresView();
}

async function loadMatiere(id) {
  if (!id) return;
  try {
    if (!S.matieres) {
      const d = await api('/api/stock/matieres');
      S.matieres = Array.isArray(d) ? d : [];
    }
    let matiere = (S.matieres || []).find(m => m.id === id);
    if (!matiere) {
      const d = await api('/api/stock/matieres');
      S.matieres = Array.isArray(d) ? d : [];
      matiere = S.matieres.find(m => m.id === id);
    }
    if (!matiere) {
      showToast('Référence introuvable.', 'error');
      return;
    }
    const mouvements = await api('/api/stock/matieres/' + id + '/mouvements');
    S.selMatiere = {
      matiere,
      mouvements: Array.isArray(mouvements) ? mouvements : [],
    };
    S.selProduit = null;
    S.selEmpl = null;
    S.searchResults = null;
    clearSearch();
    if (S.tab !== 'matieres') S.tab = 'matieres';
    closeSidebar();
    if (typeof stockSyncUrl === 'function') stockSyncUrl();
    render();
  } catch (e) {
    showToast(e.message, 'error');
  }
}

async function refreshSelMatiere() {
  if (!S.selMatiere || !S.selMatiere.matiere) return;
  const id = S.selMatiere.matiere.id;
  try {
    const d = await api('/api/stock/matieres');
    S.matieres = Array.isArray(d) ? d : [];
    const matiere = S.matieres.find(m => m.id === id) || S.selMatiere.matiere;
    const mouvements = await api('/api/stock/matieres/' + id + '/mouvements');
    S.selMatiere = {
      matiere,
      mouvements: Array.isArray(mouvements) ? mouvements : [],
    };
    renderContent();
    updateNavActive();
  } catch (e) {
    showToast(e.message, 'error');
  }
}

function clearMatiereSel() {
  S.selMatiere = null;
  if (typeof stockSyncUrl === 'function') stockSyncUrl();
  renderContent();
  updateNavActive();
}

function mpMvtEmplacementLabel(m) {
  const t = (m.type_mouvement || '').toLowerCase();
  if (t === 'entree') return m.emplacement_dest || '';
  if (t === 'sortie') return m.emplacement_source || '';
  if (t === 'transfert') {
    const a = m.emplacement_source || '';
    const b = m.emplacement_dest || '';
    if (a && b) return a + ' → ' + b;
    return a || b;
  }
  return m.emplacement_dest || m.emplacement_source || '';
}

function buildMpMvtHistory(mouvements, matiere) {
  const mpCat = matiere || null;
  return el('div', { cls: 'card' },
    el('div', { cls: 'card-header' }, el('div', { cls: 'card-title' }, 'Historique des mouvements')),
    !mouvements.length
      ? el('div', { cls: 'card-empty' }, 'Aucun mouvement')
      : el('div', null, ...mouvements.slice(0, 30).map(m => {
          const icons = { entree: '↓', sortie: '↑', ajustement: '=', transfert: '↔' };
          const t = (m.type_mouvement || '').toLowerCase();
          const signe = t === 'entree' ? '+' : t === 'sortie' ? '−' : t === 'ajustement' ? '=' : '';
          const actor = (m.created_by_name || '').trim();
          const empl = mpMvtEmplacementLabel(m);
          const noteParts = [];
          if (m.ref_bl) noteParts.push('BL ' + m.ref_bl);
          if (m.prix_eur_m2 != null && m.prix_eur_m2 > 0) {
            noteParts.push('Prix ' + parseFloat(m.prix_eur_m2).toLocaleString('fr-FR', { minimumFractionDigits: 4, maximumFractionDigits: 4 }) + ' €/m²');
          }
          if (m.note) noteParts.push(m.note);
          return el('div', { cls: 'mvt-row' },
            el('div', { cls: 'mvt-icon ' + t }, icons[t] || '·'),
            el('div', { cls: 'mvt-body' },
              el('div', { cls: 'mvt-line1' },
                el('span', null, MVT_TYPE_LABELS[t] || t),
                el('div', { cls: 'mvt-line1-right' },
                  el('span', { cls: 'mvt-qte-' + t }, signe + mpStockLine(m.quantite, mpCat)),
                  (m.quantite_apres != null)
                    ? el('span', { cls: 'mvt-solde' }, 'Solde ' + mpStockLine(m.quantite_apres, mpCat))
                    : null,
                ),
              ),
              el('div', { cls: 'mvt-line2' },
                fD(m.created_at),
                empl ? el('span', null, ' · ' + empl) : null,
                actor ? el('span', null, ' · ' + actor) : null,
              ),
              noteParts.length
                ? el('div', { cls: 'mvt-note' }, noteParts.join(' · '))
                : null,
            ),
          );
        })),
  );
}

function buildMatiereDetail() {
  const sel = S.selMatiere;
  if (!sel || !sel.matiere) {
    return el('div', { cls: 'content' }, el('div', { cls: 'card-empty' }, 'Référence introuvable'));
  }
  const m = sel.matiere;
  const mouvements = sel.mouvements || [];
  const seuil = parseFloat(m.seuil_alerte) || 0;

  const back = el('button', {
    cls: 'btn-ghost',
    style: { marginBottom: '14px' },
    type: 'button',
    on: { click: clearMatiereSel },
  }, '← Retour aux matières premières');

  const actionBtns = [];
  if (!S.stockReadOnly) {
    actionBtns.push(
      el('button', {
        cls: 'mp-act-btn mp-act-entree',
        type: 'button',
        on: { click: () => openModalMouvement('entree', m) },
      }, '↓ Entrée'),
      el('button', {
        cls: 'mp-act-btn mp-act-sortie',
        type: 'button',
        on: { click: () => openModalMouvement('sortie', m) },
      }, '↑ Sortie'),
    );
    if (isMatieresAdmin()) {
      actionBtns.push(el('button', {
        cls: 'action-btn inventaire',
        type: 'button',
        on: { click: () => openModalMouvement('ajustement', m) },
      }, '= Ajustement'));
    }
  }
  if (isMatieresAdmin()) {
    actionBtns.push(el('button', {
      cls: 'mp-act-icon',
      type: 'button',
      style: { flex: '0 0 auto', minWidth: '44px' },
      attrs: { title: 'Modifier la référence', 'aria-label': 'Modifier la référence' },
      on: { click: () => openMatiereRefEditModal(m) },
    }, iconEl('edit', 16)));
  }
  const actions = actionBtns.length
    ? el('div', { cls: 'action-bar', style: { marginTop: '14px' } }, ...actionBtns)
    : null;

  const meta = [];
  if (mpIsGlassineCategory(m) && m.couleur) {
    meta.push('Couleur : ' + m.couleur);
  }
  if (mpHasConditionnement(m.categorie) && m.unites_par_palette > 0) {
    const u = mpUniteAchat(m.categorie);
    meta.push('Conditionnement : ' + Number(m.unites_par_palette).toLocaleString('fr-FR') + ' ' + u + '/palette');
  }
  if (seuil > 0) meta.push('Seuil min. ' + mpStockLine(seuil, m));

  // Détail laizes pour les matières frontal/glassine/complexe
  let laizeDetail = null;
  if (m.laizee && Array.isArray(m.stock_par_laize)) {
    if (m.stock_par_laize.length === 0) {
      laizeDetail = el('div', {
        style: 'background:rgba(251,146,60,0.10);border:1px solid rgba(251,146,60,0.40);border-radius:10px;padding:12px 14px;margin-top:14px;font-size:13px;color:var(--text)',
      },
        el('strong', null, 'Référence à compléter — '),
        'aucune laize associée. Édite la matière pour ajouter les laizes, le prix au m² et le métrage de la bobine.'
      );
    } else {
      const tbl = el('table', {
        style: 'width:100%;border-collapse:collapse;margin-top:6px',
      });
      tbl.appendChild(el('thead', null,
        el('tr', null,
          el('th', { style: 'text-align:left;padding:8px 10px;font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid var(--border)' }, 'Laize'),
          el('th', { style: 'text-align:right;padding:8px 10px;font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid var(--border)' }, 'Métrage'),
          el('th', { style: 'text-align:right;padding:8px 10px;font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid var(--border)' }, 'Stock'),
          el('th', { style: 'text-align:right;padding:8px 10px;font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid var(--border)' }, 'Valorisation'),
        )
      ));
      const tbody = el('tbody');
      const prix_m2_matiere = parseFloat(m.prix_eur_m2 || 0);
      const metres = parseFloat(m.metres_lineaires_par_bobine || 0);
      const prixParLaize = !!m.prix_par_laize;
      m.stock_par_laize.forEach(spl => {
        const prix_m2 = prixParLaize
          ? parseFloat(spl.prix_eur_m2 != null ? spl.prix_eur_m2 : 0)
          : prix_m2_matiere;
        const valoBobine = (parseFloat(spl.valeur_mm || 0) / 1000) * metres * prix_m2;
        const valo = valoBobine * parseFloat(spl.quantite || 0);
        const metrageTotal = metres * parseFloat(spl.quantite || 0);
        tbody.appendChild(el('tr', { style: 'border-bottom:1px solid var(--border)' },
          el('td', { style: 'padding:8px 10px;font-size:13px;color:var(--text);font-weight:600' },
            (spl.label || (spl.valeur_mm + ' mm')) + (prixParLaize && prix_m2 > 0
              ? ' · ' + prix_m2.toLocaleString('fr-FR', { minimumFractionDigits: 4, maximumFractionDigits: 4 }) + ' €/m²'
              : '')),
          el('td', { style: 'padding:8px 10px;font-size:13px;text-align:right;font-variant-numeric:tabular-nums;color:' + (metrageTotal > 0 ? 'var(--text)' : 'var(--muted)') },
            metrageTotal > 0 ? Math.round(metrageTotal).toLocaleString('fr-FR') + ' m' : '—'),
          el('td', { style: 'padding:8px 10px;font-size:13px;text-align:right;font-variant-numeric:tabular-nums' },
            fN(spl.quantite) + ' bob.'),
          el('td', { style: 'padding:8px 10px;font-size:13px;text-align:right;font-variant-numeric:tabular-nums;color:' + (valo > 0 ? 'var(--text)' : 'var(--muted)') },
            valo > 0 ? valo.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €' : '—'),
        ));
      });
      tbl.appendChild(tbody);
      const paramsLine = el('div', { style: 'font-size:12px;color:var(--text2);margin-top:8px' },
        prixParLaize
          ? el('span', null, 'Tarification : ', el('strong', null, 'prix par laize'))
          : el('span', null, 'Prix m² : ', el('strong', null, prix_m2_matiere > 0 ? prix_m2_matiere.toLocaleString('fr-FR', { minimumFractionDigits: 4, maximumFractionDigits: 4 }) + ' €' : 'non défini')),
        ' · Métrage bobine : ', el('strong', null, metres > 0 ? metres.toLocaleString('fr-FR') + ' m' : 'non défini'),
      );
      laizeDetail = el('div', {
        style: 'background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px 16px;margin-top:14px',
      },
        el('div', { style: 'font-size:13px;font-weight:700;color:var(--text);margin-bottom:8px' }, 'Stocks par laize'),
        tbl,
        paramsLine,
      );
    }
  }

  return el('div', { cls: 'content' },
    back,
    el('div', { cls: 'scorecard' },
      el('div', { style: { display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginBottom: '8px' } },
        dashMpCatBadge(m.categorie, m.sous_section),
        m.en_alerte ? el('span', { style: { fontSize: '12px', color: 'var(--warn)', fontWeight: '600' } }, 'Sous le seuil') : null,
      ),
      el('div', { cls: 'sc-ref' }, m.reference || ''),
      el('div', { cls: 'sc-des' }, m.designation || '—'),
      meta.length
        ? el('div', { style: { fontSize: '12px', color: 'var(--muted)', marginTop: '6px' } }, meta.join(' · '))
        : null,
      el('div', { cls: 'sc-stats' },
        el('div', { cls: 'sc-stat' },
          el('div', { cls: 'sc-stat-label' }, 'Stock actuel'),
          el('div', { cls: 'sc-stat-value' }, mpStockLine(m.quantite, m)),
        ),
        el('div', { cls: 'sc-stat' },
          el('div', { cls: 'sc-stat-label' }, 'Mouvements'),
          el('div', { cls: 'sc-stat-value' }, String(mouvements.length)),
        ),
      ),
    ),
    actions,
    laizeDetail,
    buildMpMvtHistory(mouvements, m),
  );
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
  const content = S.selMatiere ? buildMatiereDetail() : buildMatieres();
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

const PF_UNITES = ['étiquette', 'pièces', 'kg', 'm', 'bobines', 'cartons', 'palettes', 'étiquettes', 'boîtes'];

function normalizePfMvt(m) {
  if (!m || typeof m !== 'object') return m;
  const type = (m.type || m.type_mouvement || '').toLowerCase();
  return {
    ...m,
    type: type === 'entree' || type === 'sortie' ? type : type,
    date_mouvement: m.date_mouvement || m.created_at,
    user_login: m.user_login || m.created_by_name || m.created_by || '—',
  };
}

function buildPfEmptyState(title, hint) {
  return el('div', { cls: 'pf-empty-state' },
    el('div', { style: { fontSize: '32px', marginBottom: '4px', color: 'var(--muted)' } }, '·'),
    el('div', { cls: 'pf-empty-state-title' }, title),
    el('div', { cls: 'pf-empty-state-hint' }, hint),
  );
}

function pfFmtShortDateTime(iso) {
  if (!iso) return '—';
  const s = String(iso);
  const d = s.slice(0, 10).split('-');
  const hm = s.length >= 16 ? s.slice(11, 16) : '';
  if (d.length === 3) return d[2] + '/' + d[1] + (hm ? ' ' + hm : '');
  return fD(iso);
}

function filterPfStockList() {
  const list = S.pfStock || [];
  const fs = S.pfFilters || { refs: [], empls: [], q: '' };
  const q = String(fs.q || '').trim().toLowerCase();
  const refSet = new Set((fs.refs || []).map(x => String(x || '').trim().toUpperCase()).filter(Boolean));
  const emplSet = new Set((fs.empls || []).map(x => String(x || '').trim().toUpperCase()).filter(Boolean));
  return list.filter(row => {
    if (refSet.size) {
      const r = String(row.reference || '').trim().toUpperCase();
      if (!refSet.has(r)) return false;
    }
    if (emplSet.size) {
      const e = String(row.emplacement || '').trim().toUpperCase();
      if (!emplSet.has(e)) return false;
    }
    if (q) {
      const hay = [
        row.reference,
        row.designation,
        row.no_of,
      ].map(x => String(x || '').toLowerCase()).join(' ');
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

function filterPfMouvementsList() {
  const list = S.pfMouvements || [];
  const fs = S.pfFilters || { refs: [], empls: [], q: '' };
  const q = String(fs.q || '').trim().toLowerCase();
  const refSet = new Set((fs.refs || []).map(x => String(x || '').trim().toUpperCase()).filter(Boolean));
  const emplSet = new Set((fs.empls || []).map(x => String(x || '').trim().toUpperCase()).filter(Boolean));
  return list.filter(m => {
    if (refSet.size) {
      const r = String(m.reference || '').trim().toUpperCase();
      if (!refSet.has(r)) return false;
    }
    if (emplSet.size) {
      const e = String(m.emplacement || '').trim().toUpperCase();
      if (!emplSet.has(e)) return false;
    }
    if (q) {
      const hay = [
        m.reference,
        m.emplacement,
        m.user_login,
      ].map(x => String(x || '').toLowerCase()).join(' ');
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

async function loadProduitsFinis() {
  S.pfLoading = true;
  S.pfStock = null;
  renderProduitsFinisView();
  try {
    const [data, mvts] = await Promise.all([
      api('/api/stock/produits-finis'),
      api('/api/stock/produits-finis/mouvements?limit=20'),
    ]);
    const payload = data && typeof data === 'object' && !Array.isArray(data) ? data : {};
    S.pfStock = payload.stock || payload.items || (Array.isArray(data) ? data : []);
    S.pfCatalogue = payload.catalogue || [];
    S.pfKpis = payload.kpis || { references: 0, mouvements_aujourdhui: 0, emplacements_occupes: 0 };
    S.pfTotalMouvements = Number(S.pfKpis.total_mouvements) || 0;
    const mvtsList = Array.isArray(mvts)
      ? mvts
      : (mvts && (mvts.mouvements || mvts.items)) || [];
    S.pfMouvements = mvtsList.map(normalizePfMvt);
  } catch (e) {
    S.pfStock = [];
    S.pfCatalogue = [];
    S.pfMouvements = [];
    S.pfKpis = { references: 0, mouvements_aujourdhui: 0, emplacements_occupes: 0 };
    S.pfTotalMouvements = 0;
    showToast(e.message || 'Chargement impossible.', 'error');
  }
  S.pfLoading = false;
  renderProduitsFinisView();
}

function renderProduitsFinisView() {
  if (S.tab !== 'produits-finis') return;
  const ae = document.activeElement;
  const focusId = ae?.id;
  const caretStart = ae?.selectionStart;
  const caretEnd = ae?.selectionEnd;
  const area = document.getElementById('scroll-area');
  if (!area) return;
  area.innerHTML = '';
  const content = buildProduitsFinisTab();
  if (content) area.appendChild(content);
  if (focusId) {
    const elFocus = document.getElementById(focusId);
    if (elFocus) {
      elFocus.focus();
      if (caretStart != null) {
        try { elFocus.setSelectionRange(caretStart, caretEnd); } catch (e) {}
      }
    }
  }
}

function pfAddFilterTag(kind, value) {
  const v = String(value || '').trim();
  if (!v) return;
  if (!S.pfFilters) S.pfFilters = { refs: [], empls: [], q: '' };
  const fs = S.pfFilters;
  if (kind === 'ref') {
    const ref = v.toUpperCase();
    if (!fs.refs) fs.refs = [];
    if (!fs.refs.includes(ref)) fs.refs.push(ref);
  } else if (kind === 'empl') {
    const empl = v.toUpperCase();
    if (!fs.empls) fs.empls = [];
    if (!fs.empls.includes(empl)) fs.empls.push(empl);
  }
  fs.q = '';
}

function pfRemoveFilterTag(kind, value) {
  if (!S.pfFilters) return;
  const fs = S.pfFilters;
  const v = String(value || '').trim().toUpperCase();
  if (!v) return;
  if (kind === 'ref') fs.refs = (fs.refs || []).filter(x => String(x || '').toUpperCase() !== v);
  if (kind === 'empl') fs.empls = (fs.empls || []).filter(x => String(x || '').toUpperCase() !== v);
}

function buildPfUnifiedSearch() {
  if (!S.pfFilters) S.pfFilters = { refs: [], empls: [], q: '' };
  const fs = S.pfFilters;

  const inp = el('input', {
    id: 'pf-search',
    type: 'text',
    placeholder: 'Rechercher (réf, empl, désignation…)',
    autocomplete: 'off',
    spellcheck: 'false',
  });
  inp.value = String(fs.q || '');

  const dd = el('div', { cls: 'pf-search-dd' });
  const ddList = el('div', { cls: 'empl-suggestions', style: { display: 'none' } });
  dd.appendChild(ddList);

  function renderDropdown() {
    const q = String(fs.q || '').trim();
    ddList.innerHTML = '';
    if (!q) { ddList.style.display = 'none'; return; }

    const prod = pfProduitSuggestions(q).slice(0, 8);
    const empls = pfEmplacementChoices(q).slice(0, 8);

    const pushItem = (kind, label, sub) => {
      const kindLbl = kind === 'ref' ? 'Réf' : 'Empl';
      ddList.appendChild(el('div', {
        cls: 'pf-sugg-item',
        on: { mousedown: (e) => {
          e.preventDefault(); // évite blur avant click
          fs.q = '';
          ddList.style.display = 'none';
          if (kind === 'ref') {
            // Ouvre directement la fiche produit
            openPfProduitPage(label);
          } else {
            // Ouvre directement la fiche emplacement
            loadEmplacement(label);
          }
        } },
      },
      el('span', { cls: 'pf-sugg-kind' }, kindLbl),
      el('span', null, ' · '),
      el('span', { cls: 'pf-sugg-main' }, label),
      sub ? el('span', null, ' — ') : null,
      sub ? el('span', { cls: 'pf-sugg-sub' }, sub) : null,
      ));
    };

    prod.forEach(p => pushItem('ref', String(p.reference || '').toUpperCase(), p.designation || ''));
    empls.forEach(e => pushItem('empl', String(e || '').toUpperCase(), ''));

    ddList.style.display = (ddList.childNodes.length ? 'block' : 'none');
  }

  inp.addEventListener('input', (e) => {
    fs.q = e.target.value;
    renderProduitsFinisView();
  });

  inp.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (String(fs.q || '').trim()) {
        fs.q = '';
      } else {
        fs.refs = [];
        fs.empls = [];
      }
      renderProduitsFinisView();
      return;
    }
    if (e.key === 'Backspace' && !String(fs.q || '').trim()) {
      const lastRef = (fs.refs || []).slice(-1)[0];
      const lastEmpl = (fs.empls || []).slice(-1)[0];
      // Priorité: dernier tag ajouté (refs en dernier si présent, sinon empls)
      if (lastRef) fs.refs = (fs.refs || []).slice(0, -1);
      else if (lastEmpl) fs.empls = (fs.empls || []).slice(0, -1);
      renderProduitsFinisView();
      return;
    }
    if (e.key === 'Enter') {
      // Sélection rapide: 1ère suggestion si dropdown ouvert
      const first = ddList.firstElementChild;
      if (first) {
        e.preventDefault();
        first.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
      }
    }
  });

  const tags = el('div', { cls: 'pf-tags pf-tags-below' },
    ...(fs.refs || []).map(r => el('span', { cls: 'pf-tag' },
      el('span', { cls: 'pf-tag-kind' }, 'Réf'),
      el('span', null, r),
      el('button', { cls: 'pf-tag-x', attrs: { type: 'button', title: 'Retirer' }, on: { click: () => { pfRemoveFilterTag('ref', r); renderProduitsFinisView(); } } }, '×'),
    )),
    ...(fs.empls || []).map(e => el('span', { cls: 'pf-tag' },
      el('span', { cls: 'pf-tag-kind' }, 'Empl'),
      el('span', null, e),
      el('button', { cls: 'pf-tag-x', attrs: { type: 'button', title: 'Retirer' }, on: { click: () => { pfRemoveFilterTag('empl', e); renderProduitsFinisView(); } } }, '×'),
    )),
  );

  const box = el('div', { cls: 'pf-toolbar-search' },
    el('span', { cls: 'pf-toolbar-search-icon' }, iconEl('search', 16)),
    el('div', { cls: 'pf-toolbar-searchbox' }, inp),
    tags,
    dd,
  );

  // Après render, recalcul suggestions
  requestAnimationFrame(renderDropdown);
  return box;
}

function buildProduitsFinisTab() {
  const wrap = el('div', { cls: 'content pf-tab', id: 'tab-produits-finis' });

  const kpis = S.pfKpis || {};
  wrap.appendChild(el('div', { cls: 'pf-kpis' },
    el('div', { cls: 'card pf-kpi', style: { padding: '16px 20px' } },
      el('div', { cls: 'pf-kpi-label' }, 'Références en stock'),
      el('div', { cls: 'pf-kpi-value', id: 'kpi-refs' }, S.pfLoading && S.pfStock === null ? '—' : String(kpis.references ?? 0)),
    ),
    el('div', { cls: 'card pf-kpi', style: { padding: '16px 20px' } },
      el('div', { cls: 'pf-kpi-label' }, 'Mouvements aujourd\'hui'),
      el('div', { cls: 'pf-kpi-value', id: 'kpi-mvt-today' }, S.pfLoading && S.pfStock === null ? '—' : String(kpis.mouvements_aujourdhui ?? 0)),
    ),
    el('div', { cls: 'card pf-kpi', style: { padding: '16px 20px' } },
      el('div', { cls: 'pf-kpi-label' }, 'Emplacements occupés'),
      el('div', { cls: 'pf-kpi-value', id: 'kpi-empl' }, S.pfLoading && S.pfStock === null ? '—' : String(kpis.emplacements_occupes ?? 0)),
    ),
  ));

  const toolbar = el('div', { cls: 'pf-toolbar' },
    buildPfUnifiedSearch(),
    el('div', { cls: 'pf-toolbar-actions' },
      S.stockReadOnly ? null : el('button', {
        cls: 'btn btn-soft btn-soft-entree',
        type: 'button',
        on: { click: () => openPfMvtModal('entree') },
      }, iconEl('upload', 14), ' Entrée'),
      S.stockReadOnly ? null : el('button', {
        cls: 'btn btn-soft btn-soft-sortie',
        type: 'button',
        on: { click: () => openPfMvtModal('sortie') },
      }, iconEl('download', 14), ' Sortie'),
      el('button', {
        cls: 'btn-ghost',
        type: 'button',
        on: { click: () => openPfExportCsvModal() },
        style: { padding: '10px 14px' },
      }, iconEl('download', 16), ' Export CSV'),
    ),
  );
  wrap.appendChild(toolbar);

  const stockList = el('div', { cls: 'pf-stock-list', id: 'pf-stock-list' });
  const mvtList = el('div', { cls: 'pf-mvt-list', id: 'pf-mvt-list' });

  if (S.pfLoading && S.pfStock === null) {
    stockList.appendChild(el('div', { cls: 'pf-empty', style: { padding: '32px', textAlign: 'center', fontSize: '13px' } }, 'Chargement…'));
    mvtList.appendChild(el('div', { cls: 'pf-empty', style: { padding: '32px', textAlign: 'center', fontSize: '13px' } }, 'Chargement…'));
  } else {
    const filtered = filterPfStockList();
    const fs = S.pfFilters || { refs: [], empls: [], q: '' };
    const tagsTxt = []
      .concat((fs.refs || []).map(r => 'Réf: ' + r))
      .concat((fs.empls || []).map(e => 'Empl: ' + e));
    const hasFilter = !!((fs.refs || []).length || (fs.empls || []).length || String(fs.q || '').trim());
    const neverHadMvt = !S.pfTotalMouvements;

    if (!filtered.length) {
      if (hasFilter) {
        stockList.appendChild(el('div', { cls: 'pf-empty', style: { padding: '32px', textAlign: 'center', fontSize: '13px' } },
          'Aucun résultat pour ' + (tagsTxt.length ? tagsTxt.join(' · ') : 'ce filtre') + '.',
        ));
      } else if (neverHadMvt) {
        stockList.appendChild(buildPfEmptyState(
          'Aucun produit en stock',
          'Utilisez le bouton « Entrée » pour enregistrer votre premier mouvement.',
        ));
      } else {
        stockList.appendChild(buildPfEmptyState('Aucun produit en stock', 'Tous les emplacements sont vides.'));
      }
    } else {
      filtered.forEach(row => {
        const item = el('div', {
          cls: 'pf-stock-item',
          on: { click: () => openPfProduitPage(row.reference, row.produit_id) },
        },
          el('div', { cls: 'pf-stock-item-main' },
            el('div', { cls: 'pf-stock-ref' }, stockPfRefLink(row.reference, row.produit_id)),
            el('div', { cls: 'pf-stock-des' }, row.designation || '—'),
            el('div', { cls: 'pf-stock-row', style: { marginTop: '6px' } },
              el('span', { cls: 'pf-stock-qte' }, fU(row.quantite, row.unite)),
              el('span', {
                cls: 'pf-empl-badge' + (isStockEmplacementAuSol(row.emplacement) ? ' pf-empl-au-sol' : isStockEmplacementSortieProd(row.emplacement) ? ' pf-empl-sortie-prod' : ''),
              }, stockEmplLabel(row.emplacement) || '—'),
            ),
            el('div', { cls: 'pf-stock-meta' }, 'Dernière entrée : ' + fD(row.derniere_entree)),
          ),
        );
        stockList.appendChild(item);
      });
    }

    const mvts = filterPfMouvementsList();
    if (!mvts.length) {
      mvtList.appendChild(el('div', { cls: 'pf-empty', style: { padding: '24px', textAlign: 'center', fontSize: '13px' } },
        hasFilter ? 'Aucun mouvement pour ce filtre.' : (neverHadMvt ? 'Aucun mouvement enregistré.' : 'Aucun mouvement récent.'),
      ));
    } else {
      mvts.forEach(m => {
        const isEntree = m.type === 'entree';
        mvtList.appendChild(el('div', { cls: 'pf-mvt-item' },
          el('span', { cls: 'pf-mvt-icon ' + (isEntree ? 'entree' : 'sortie') }, isEntree ? '↑' : '↓'),
          el('div', { cls: 'pf-mvt-main' },
            el('div', { cls: 'pf-mvt-line' },
              el('span', { cls: 'pf-mvt-ref' }, stockPfRefLink(m.reference, m.produit_id)),
              el('span', { cls: 'pf-mvt-qte' }, fU(m.quantite, m.unite)),
            ),
            el('div', { cls: 'pf-mvt-sub' },
              (m.emplacement || '—') + ' · ' + pfFmtShortDateTime(m.date_mouvement)
              + (m.quantite_apres != null ? ' · Solde ' + fU(m.quantite_apres, m.unite) : ''),
            ),
          ),
          el('div', { cls: 'pf-mvt-user' }, m.user_login || '—'),
        ));
      });
    }
  }

  wrap.appendChild(el('div', { cls: 'pf-grid' },
    el('div', { cls: 'pf-col-stock' },
      el('div', { cls: 'pf-col-title' }, 'Stock actuel'),
      stockList,
    ),
    el('div', { cls: 'pf-col-mvts' },
      el('div', { cls: 'pf-col-title' }, 'Derniers mouvements'),
      mvtList,
    ),
  ));
  return wrap;
}

function escCsv(v) {
  const s = String(v ?? '');
  if (s.includes('"') || s.includes(';') || s.includes('\n') || s.includes('\r')) {
    return '"' + s.replaceAll('"', '""') + '"';
  }
  return s;
}

function pfExportFilteredStockRows(filters) {
  const list = Array.isArray(S.pfStock) ? S.pfStock : [];
  const refSet = new Set((filters?.refs || []).map(x => String(x || '').trim().toUpperCase()).filter(Boolean));
  const emplSet = new Set((filters?.empls || []).map(x => String(x || '').trim().toUpperCase()).filter(Boolean));
  return list.filter(r => {
    if (refSet.size) {
      const rr = String(r.reference || '').trim().toUpperCase();
      if (!refSet.has(rr)) return false;
    }
    if (emplSet.size) {
      const ee = String(r.emplacement || '').trim().toUpperCase();
      if (!emplSet.has(ee)) return false;
    }
    return true;
  });
}

function downloadCsvText(filename, csvText) {
  const blob = new Blob([csvText], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 800);
}

function openPfExportCsvModal() {
  if (!S.pfExportFilters) S.pfExportFilters = { refs: [], empls: [], qRef: '', qEmpl: '' };
  S.pfExportModalOpen = true;
  renderPfExportCsvModal();
}

function closePfExportCsvModal() {
  S.pfExportModalOpen = false;
  S.pfExportFilters = S.pfExportFilters || { refs: [], empls: [], qRef: '', qEmpl: '' };
  const m = document.getElementById('mroot');
  if (m) m.innerHTML = '';
}

function pfExportAddTag(kind, value) {
  if (!S.pfExportFilters) S.pfExportFilters = { refs: [], empls: [], qRef: '', qEmpl: '' };
  const fs = S.pfExportFilters;
  const v = String(value || '').trim();
  if (!v) return;
  if (kind === 'ref') {
    const ref = v.toUpperCase();
    if (!fs.refs.includes(ref)) fs.refs.push(ref);
    fs.qRef = '';
  } else if (kind === 'empl') {
    const empl = v.toUpperCase();
    if (!fs.empls.includes(empl)) fs.empls.push(empl);
    fs.qEmpl = '';
  }
}

function pfExportRemoveTag(kind, value) {
  if (!S.pfExportFilters) return;
  const fs = S.pfExportFilters;
  const v = String(value || '').trim().toUpperCase();
  if (kind === 'ref') fs.refs = (fs.refs || []).filter(x => String(x || '').toUpperCase() !== v);
  if (kind === 'empl') fs.empls = (fs.empls || []).filter(x => String(x || '').toUpperCase() !== v);
}

function renderPfExportCsvModal() {
  const mroot = document.getElementById('mroot');
  if (!mroot) return;
  mroot.innerHTML = '';
  if (!S.pfExportModalOpen) return;

  if (!S.pfExportFilters) S.pfExportFilters = { refs: [], empls: [], qRef: '', qEmpl: '' };
  const fs = S.pfExportFilters;

  const overlay = el('div', {
    id: 'modal-pf-export-csv',
    cls: 'mp-modal-overlay',
    on: { click: (e) => { if (e.target === overlay) closePfExportCsvModal(); } },
  });

  const box = el('div', { cls: 'mp-modal', style: { maxWidth: '560px' } });
  box.appendChild(el('div', { style: { fontWeight: '800', fontSize: '15px', marginBottom: '10px', color: 'var(--text)' } }, 'Exporter stock produits finis (CSV)'));
  box.appendChild(el('div', { style: { fontSize: '12px', color: 'var(--text2)', lineHeight: '1.5', marginBottom: '14px' } },
    'Par défaut : toutes les références et tous les emplacements. Ajoutez des tags pour filtrer.',
  ));

  const mkTag = (kind, v) => el('span', { cls: 'pf-tag', style: { background: 'var(--bg)' } },
    el('span', { cls: 'pf-tag-kind' }, kind === 'ref' ? 'Réf' : 'Empl'),
    el('span', null, v),
    el('button', { cls: 'pf-tag-x', attrs: { type: 'button', title: 'Retirer' }, on: { click: () => { pfExportRemoveTag(kind, v); renderPfExportCsvModal(); } } }, '×'),
  );

  function buildPicker(kind) {
    const isRef = kind === 'ref';
    const qKey = isRef ? 'qRef' : 'qEmpl';
    const inputId = isRef ? 'pf-export-ref' : 'pf-export-empl';
    const placeholder = isRef ? 'Ajouter une référence…' : 'Ajouter un emplacement…';
    const tags = isRef ? (fs.refs || []) : (fs.empls || []);

    const inp = el('input', {
      cls: 'field-input' + (isRef ? '' : ' empl-upper'),
      id: inputId,
      type: 'text',
      placeholder,
      autocomplete: 'off',
      spellcheck: 'false',
      style: { direction: 'ltr' },
    });
    inp.value = String(fs[qKey] || '');

    const suggWrap = el('div', { cls: 'empl-suggestions', style: { display: 'none' } });

    const refreshSugg = () => {
      const q = String(fs[qKey] || '').trim();
      suggWrap.innerHTML = '';
      if (!q) { suggWrap.style.display = 'none'; return; }
      const list = isRef
        ? pfProduitSuggestions(q).slice(0, 10).map(p => ({ value: String(p.reference || '').toUpperCase(), label: (p.reference || '') + (p.designation ? ' — ' + p.designation : '') }))
        : pfEmplacementChoices(q).slice(0, 12).map(e => ({ value: String(e || '').toUpperCase(), label: String(e || '').toUpperCase() }));
      list.forEach(it => {
        suggWrap.appendChild(el('div', {
          cls: 'empl-sugg-item',
          on: { mousedown: (e) => {
            e.preventDefault();
            pfExportAddTag(kind, it.value);
            renderPfExportCsvModal();
            requestAnimationFrame(() => { try { document.getElementById(inputId)?.focus(); } catch (e2) {} });
          } },
        }, (isRef ? ('Réf: ' + it.label) : ('Empl: ' + it.label))));
      });
      suggWrap.style.display = list.length ? 'block' : 'none';
    };

    inp.addEventListener('input', (e) => {
      fs[qKey] = e.target.value;
      renderPfExportCsvModal();
    });
    inp.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        fs[qKey] = '';
        renderPfExportCsvModal();
        return;
      }
      if (e.key === 'Enter') {
        const first = suggWrap.firstElementChild;
        if (first) {
          e.preventDefault();
          first.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
          return;
        }
      }
      if (e.key === 'Backspace' && !String(fs[qKey] || '').trim() && tags.length) {
        if (isRef) fs.refs = fs.refs.slice(0, -1);
        else fs.empls = fs.empls.slice(0, -1);
        renderPfExportCsvModal();
      }
    });

    const tagsRow = el('div', { cls: 'pf-tags', style: { marginTop: '8px' } }, ...tags.map(v => mkTag(kind, v)));

    // sync dropdown after DOM is in place
    requestAnimationFrame(refreshSugg);

    return el('div', { cls: 'modal-field' },
      el('label', { cls: 'field-label' }, isRef ? 'Références (optionnel)' : 'Emplacements (optionnel)'),
      el('div', { cls: 'empl-combo-wrap' }, inp, suggWrap),
      tagsRow,
    );
  }

  box.appendChild(buildPicker('ref'));
  box.appendChild(buildPicker('empl'));

  const previewCount = pfExportFilteredStockRows(fs).length;
  box.appendChild(el('div', { style: { marginTop: '6px', fontSize: '12px', color: 'var(--muted)' } },
    'Lignes exportées : ' + fN(previewCount),
  ));

  const onExport = () => {
    const rows = pfExportFilteredStockRows(fs);
    const header = ['reference', 'designation', 'no_of', 'emplacement', 'quantite', 'unite', 'derniere_entree'];
    const lines = [header.join(';')].concat(rows.map(r => ([
      escCsv(String(r.reference || '').trim().toUpperCase()),
      escCsv(r.designation || ''),
      escCsv(r.no_of || ''),
      escCsv(String(r.emplacement || '').trim().toUpperCase()),
      escCsv(r.quantite ?? ''),
      escCsv(r.unite || ''),
      escCsv(r.derniere_entree || ''),
    ]).join(';')));
    const ymd = new Date().toISOString().slice(0, 10);
    downloadCsvText('stock_produits_finis_' + ymd + '.csv', lines.join('\n'));
    closePfExportCsvModal();
    showToast('Export CSV téléchargé.');
  };

  box.appendChild(el('div', { cls: 'mp-modal-actions', style: { marginTop: '16px' } },
    el('button', { cls: 'btn-cancel', type: 'button', on: { click: closePfExportCsvModal } }, 'Fermer'),
    el('button', { cls: 'btn btn-accent', type: 'button', on: { click: onExport } }, 'Exporter'),
  ));

  overlay.appendChild(box);
  mroot.appendChild(overlay);

  requestAnimationFrame(() => { try { document.getElementById('pf-export-ref')?.focus(); } catch (e) {} });
}

function pfCatalogueFind(ref) {
  const r = String(ref || '').trim().toUpperCase();
  return (S.pfCatalogue || []).find(c => String(c.reference || '').toUpperCase() === r) || null;
}

function pfEmplacementChoices(filter) {
  const q = String(filter || '').trim().toUpperCase();
  const fromStock = [...new Set((S.pfStock || []).map(r => String(r.emplacement || '').toUpperCase()).filter(Boolean))];
  const fromDb = allPageEmplacementChoices();
  const all = [...new Set([...fromStock, ...fromDb])].sort();
  if (!q) return all.slice(0, 12);
  return all.filter(e => e.includes(q)).slice(0, 12);
}

function pfProduitSuggestions(filter) {
  const q = String(filter || '').trim().toLowerCase();
  const cat = S.pfCatalogue || [];
  if (!q) return cat.slice(0, 15);
  return cat.filter(c => {
    const hay = (String(c.reference || '') + ' ' + String(c.designation || '')).toLowerCase();
    return hay.includes(q);
  }).slice(0, 15);
}

function buildPfRefPickerField(refInp, desInp, uniteSel, onPick) {
  const datalistId = 'pf-ref-datalist-' + Math.random().toString(36).slice(2, 8);
  const dl = el('datalist', { id: datalistId });
  (S.pfCatalogue || []).slice(0, 200).forEach(c => {
    dl.appendChild(el('option', { attrs: { value: c.reference || '' } }));
  });
  refInp.setAttribute('list', datalistId);
  const suggWrap = el('div', { cls: 'empl-suggestions', style: { display: 'none' } });
  const applyPick = (c) => {
    refInp.value = c.reference || '';
    desInp.value = c.designation || '';
    if (uniteSel && c.unite) uniteSel.value = c.unite;
    suggWrap.innerHTML = '';
    suggWrap.style.display = 'none';
    if (onPick) onPick(c);
  };
  refInp.addEventListener('input', () => {
    const picked = pfCatalogueFind(refInp.value);
    if (picked) {
      desInp.value = picked.designation || '';
      if (uniteSel && picked.unite) uniteSel.value = picked.unite;
    }
  });
  wireStockProduitSearch(refInp, suggWrap, applyPick);
  const refCombo = el('div', { cls: 'empl-combo-wrap' }, refInp, suggWrap);
  return { suggWrap, datalist: dl, refCombo };
}

function pfStockAtEmpl(reference, emplacement) {
  const ref = String(reference || '').trim().toUpperCase();
  const empl = String(emplacement || '').trim().toUpperCase();
  const row = (S.pfStock || []).find(r =>
    String(r.reference || '').toUpperCase() === ref
    && String(r.emplacement || '').toUpperCase() === empl,
  );
  return row ? (parseFloat(row.quantite) || 0) : 0;
}

function buildPfEmplPickerField(emplInp) {
  const datalistId = 'pf-empl-datalist-' + Math.random().toString(36).slice(2, 8);
  const dl = el('datalist', { id: datalistId });
  pfEmplacementChoices('').forEach(code => {
    dl.appendChild(el('option', { attrs: { value: code } }));
  });
  emplInp.setAttribute('list', datalistId);
  const suggWrap = el('div', { cls: 'empl-suggestions', style: { display: 'none' } });
  wireStockEmplSearch(emplInp, suggWrap);
  const emplCombo = el('div', { cls: 'empl-combo-wrap' }, emplInp, suggWrap);
  return { suggWrap, datalist: dl, emplCombo, emplInp };
}

function openPfMvtModal(type, preset) {
  if (S.stockReadOnly) return;
  const typeMvt = type === 'sortie' ? 'sortie' : 'entree';
  S.pfModal = { type: typeMvt, preset: preset || null };
  renderPfMvtModal();
}

function closePfModals() {
  S.pfModal = null;
  S.pfConfirmSortie = null;
  const mroot = document.getElementById('mroot');
  if (mroot) mroot.innerHTML = '';
}

function renderPfMvtModal() {
  closePfModals();
  const modal = S.pfModal;
  if (!modal) return;
  const mroot = document.getElementById('mroot');
  if (!mroot) return;
  const typeMvt = modal.type;
  const isSortie = typeMvt === 'sortie';
  const modalId = isSortie ? 'modal-pf-sortie' : 'modal-pf-entree';
  const headCls = isSortie ? 'mp-modal-mvt-head-pf-sortie' : 'mp-modal-mvt-head-pf-entree';

  const overlay = el('div', {
    id: modalId,
    cls: 'mp-modal-overlay',
    on: { click: (e) => { if (e.target === overlay) closePfModals(); } },
  });
  const box = el('div', { cls: 'mp-modal mp-modal-mvt' });
  box.appendChild(el('div', { cls: 'mp-modal-mvt-head ' + headCls },
    el('h3', null, isSortie ? 'Sortie produit' : 'Entrée produit'),
    el('button', { cls: 'mp-modal-close', type: 'button', on: { click: closePfModals } }, '×'),
  ));
  const body = el('div', { cls: 'mp-modal-mvt-body' });

  const preset = modal.preset || {};
  const refFieldId = isSortie ? 'pf-sortie-ref' : 'pf-entree-ref';
  const refInp = el('input', {
    cls: 'field-input',
    id: refFieldId,
    attrs: { type: 'text', placeholder: 'Référence produit', autocomplete: 'off', required: true },
    style: { direction: 'ltr' },
  });
  refInp.value = preset.reference || '';
  const desInp = el('input', {
    cls: 'field-input',
    attrs: { type: 'text', placeholder: 'Désignation', autocomplete: 'off' },
    style: { direction: 'ltr' },
  });
  desInp.value = preset.designation || '';
  const uniteSel = el('select', { cls: 'field-input' });
  PF_UNITES.forEach(u => {
    const o = el('option', { attrs: { value: u } }, u);
    if ((preset.unite || 'pièces') === u) o.selected = true;
    uniteSel.appendChild(o);
  });
  const { refCombo, datalist: refDl } = buildPfRefPickerField(refInp, desInp, uniteSel);

  const qInp = el('input', {
    cls: 'field-input',
    attrs: { type: 'number', min: '0.01', step: '0.01', inputmode: 'decimal', required: true },
    style: { direction: 'ltr' },
  });
  const emplInp = el('input', {
    cls: 'field-input empl-upper',
    attrs: { type: 'text', placeholder: 'Emplacement', autocomplete: 'off', required: true },
    style: { direction: 'ltr' },
  });
  emplInp.value = (preset.emplacement || '').toUpperCase();
  const { emplCombo, datalist: emplDl } = buildPfEmplPickerField(emplInp);
  const hintEl = el('div', { cls: 'mp-hint', style: { display: isSortie ? '' : 'none' } }, '');
  const errEl = el('div', { cls: 'mp-hint err', style: { display: 'none' } }, '');
  const ofInp = el('input', {
    cls: 'field-input',
    attrs: { type: 'text', placeholder: 'N° OF (facultatif)', autocomplete: 'off' },
    style: { direction: 'ltr' },
  });
  const comTa = el('textarea', {
    cls: 'field-input',
    attrs: { rows: '2', placeholder: 'Commentaire (facultatif)' },
    style: { resize: 'vertical', minHeight: '60px' },
  });
  const motifInp = isSortie ? el('input', {
    cls: 'field-input',
    attrs: { type: 'text', placeholder: 'Motif / destinataire (facultatif)', autocomplete: 'off' },
    style: { direction: 'ltr' },
  }) : null;

  body.appendChild(el('div', { cls: 'mp-field ref-field-wrap' },
    el('label', null, 'Référence produit *'), refCombo, refDl,
  ));
  body.appendChild(el('div', { cls: 'mp-field' }, el('label', null, 'Désignation'), desInp));
  body.appendChild(el('div', { cls: 'mp-field' },
    el('label', null, 'Quantité *'),
    qInp,
    isSortie ? hintEl : null,
    isSortie ? errEl : null,
  ));
  body.appendChild(el('div', { cls: 'mp-field' }, el('label', null, 'Unité'), uniteSel));
  body.appendChild(el('div', { cls: 'mp-field empl-field-wrap' },
    el('label', null, 'Emplacement *'), emplCombo, emplDl,
  ));
  body.appendChild(el('div', { cls: 'mp-field' }, el('label', null, 'N° OF'), ofInp));
  if (motifInp) body.appendChild(el('div', { cls: 'mp-field' }, el('label', null, 'Motif / destinataire'), motifInp));
  body.appendChild(el('div', { cls: 'mp-field' }, el('label', null, 'Commentaire'), comTa));

  const collectBody = () => ({
    reference: refInp.value.trim().toUpperCase(),
    designation: desInp.value.trim(),
    quantite: parseFloat(qInp.value),
    unite: uniteSel.value || 'pièces',
    emplacement: emplInp.value.trim().toUpperCase(),
    no_of: ofInp.value.trim() || null,
    commentaire: comTa.value.trim() || null,
    motif_destinataire: motifInp ? (motifInp.value.trim() || null) : null,
  });

  const validate = () => {
    const b = collectBody();
    if (!b.reference) return 'Référence obligatoire.';
    if (!b.emplacement) return 'Emplacement obligatoire.';
    if (!b.quantite || b.quantite < 0.01) return 'Quantité invalide — minimum 0,01.';
    if (!b.designation) b.designation = b.reference;
    return null;
  };

  const refreshStockHint = () => {
    if (!isSortie) return;
    const b = collectBody();
    const stock = pfStockAtEmpl(b.reference, b.emplacement);
    if (!b.reference || !b.emplacement) {
      hintEl.textContent = '';
      errEl.style.display = 'none';
      return;
    }
    hintEl.textContent = 'Stock à cet emplacement : ' + fU(stock, uniteSel.value || 'étiquette');
    const q = parseFloat(qInp.value);
    if (q > stock) {
      errEl.style.display = '';
      errEl.textContent = 'Stock insuffisant.';
    } else {
      errEl.style.display = 'none';
    }
  };
  if (isSortie) {
    refInp.addEventListener('input', refreshStockHint);
    emplInp.addEventListener('input', refreshStockHint);
    qInp.addEventListener('input', refreshStockHint);
    refreshStockHint();
  }

  const saveBtn = el('button', {
    cls: 'btn ' + (isSortie ? 'btn-danger' : 'btn-accent'),
    type: 'button',
  }, 'Enregistrer');

  const doSubmit = async () => {
    const err = validate();
    if (err) { showToast(err, 'error'); return; }
    const b = collectBody();
    if (!b.designation) b.designation = b.reference;
    if (isSortie) {
      const stock = pfStockAtEmpl(b.reference, b.emplacement);
      if (b.quantite > stock) {
        showToast('Stock insuffisant.', 'error');
        return;
      }
    }
    const path = isSortie ? '/api/stock/produits-finis/sortie' : '/api/stock/produits-finis/entree';
    saveBtn.disabled = true;
    try {
      await api(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(b),
      });
      showToast(isSortie ? 'Sortie enregistrée.' : 'Entrée enregistrée.');
      closePfModals();
      await loadProduitsFinis();
    } catch (e) {
      showToast(e.message || 'Enregistrement impossible.', 'error');
      saveBtn.disabled = false;
    }
  };

  const onSave = () => {
    const err = validate();
    if (err) { showToast(err, 'error'); return; }
    if (isSortie) {
      renderPfSortieConfirmModal(collectBody(), doSubmit);
      return;
    }
    doSubmit();
  };
  saveBtn.addEventListener('click', onSave);

  body.appendChild(el('div', { cls: 'mp-modal-actions' },
    el('button', { cls: 'btn btn-ghost', type: 'button', on: { click: closePfModals } }, 'Annuler'),
    saveBtn,
  ));
  box.appendChild(body);
  overlay.appendChild(box);
  mroot.appendChild(overlay);
  requestAnimationFrame(() => { document.getElementById(refFieldId)?.focus(); });
}

function renderPfSortieConfirmModal(body, onConfirm) {
  closePfModals();
  S.pfConfirmSortie = body;
  const mroot = document.getElementById('mroot');
  if (!mroot) return;
  const overlay = el('div', {
    cls: 'mp-modal-overlay',
    on: { click: (e) => { if (e.target === overlay) closePfModals(); } },
  });
  const box = el('div', { cls: 'mp-modal' },
    el('h3', null, 'Confirmer la sortie'),
    el('p', { style: { fontSize: '13px', color: 'var(--text2)', lineHeight: '1.6', marginBottom: '16px' } },
      'Sortie de ' + fU(body.quantite, body.unite) + ' — réf. ' + body.reference
      + ' depuis ' + body.emplacement + '.',
    ),
    el('div', { cls: 'mp-modal-actions' },
      el('button', { cls: 'btn btn-ghost', type: 'button', on: { click: () => {
        S.pfModal = { type: 'sortie' };
        renderPfMvtModal();
      } } }, 'Retour'),
      el('button', {
        cls: 'btn btn-danger',
        type: 'button',
        on: { click: async (e) => {
          const btn = e.currentTarget;
          btn.disabled = true;
          try { await onConfirm(); } catch (err) { btn.disabled = false; }
        } },
      }, 'Confirmer la sortie'),
    ),
  );
  overlay.appendChild(box);
  mroot.appendChild(overlay);
}

async function openPfDetailModal(reference) {
  const ref = String(reference || '').trim().toUpperCase();
  if (!ref) return;
  closePfModals();
  const mroot = document.getElementById('mroot');
  if (!mroot) return;
  const overlay = el('div', {
    id: 'modal-pf-detail',
    cls: 'mp-modal-overlay',
    on: { click: (e) => { if (e.target === overlay) closePfModals(); } },
  });
  const box = el('div', { cls: 'mp-modal', style: { maxWidth: '560px' } },
    el('div', { cls: 'mp-modal-head' },
      el('h3', null, 'Détail produit'),
      el('button', { cls: 'mp-modal-close', type: 'button', on: { click: closePfModals } }, '×'),
    ),
    el('div', { cls: 'pf-empty' }, 'Chargement…'),
  );
  overlay.appendChild(box);
  mroot.appendChild(overlay);
  try {
    const d = await api('/api/stock/produits-finis/' + encodeURIComponent(ref));
    box.innerHTML = '';
    box.appendChild(el('div', { cls: 'mp-modal-head' },
      el('h3', null, d.reference || ref),
      el('button', { cls: 'mp-modal-close', type: 'button', on: { click: closePfModals } }, '×'),
    ));
    box.appendChild(el('p', { style: { fontSize: '13px', color: 'var(--text2)', marginBottom: '8px' } }, d.designation || '—'));
    box.appendChild(el('p', { style: { fontSize: '13px', fontWeight: '700', color: 'var(--accent)', marginBottom: '16px' } },
      'Stock actuel : ' + fU(d.stock_total, d.unite),
    ));
    const hist = d.historique || [];
    if (!hist.length) {
      box.appendChild(el('div', { cls: 'pf-empty' }, 'Aucun mouvement enregistré.'));
    } else {
      const table = el('table', { cls: 'pf-detail-table' });
      const thead = el('thead', null, el('tr', null,
        el('th', null, 'Date'),
        el('th', null, 'Type'),
        el('th', null, 'Qté'),
        el('th', null, 'Empl.'),
        el('th', null, 'Solde'),
        el('th', null, 'OF'),
        el('th', null, 'Utilisateur'),
      ));
      table.appendChild(thead);
      const tbody = el('tbody', null);
      hist.forEach(raw => {
        const m = normalizePfMvt(raw);
        const t = m.type === 'entree' ? 'Entrée' : (m.type === 'sortie' ? 'Sortie' : (m.type || '—'));
        const solde = m.quantite_apres != null ? fU(m.quantite_apres, m.unite || d.unite) : '—';
        tbody.appendChild(el('tr', null,
          el('td', null, fDateTime(m.date_mouvement)),
          el('td', null, t),
          el('td', null, fU(m.quantite, m.unite)),
          el('td', null, m.emplacement || '—'),
          el('td', null, solde),
          el('td', null, m.no_of || '—'),
          el('td', null, m.user_login || '—'),
        ));
      });
      table.appendChild(tbody);
      box.appendChild(table);
    }
    box.appendChild(el('div', { cls: 'mp-modal-actions', style: { marginTop: '16px' } },
      el('button', { cls: 'btn btn-ghost', type: 'button', on: { click: closePfModals } }, 'Fermer'),
    ));
  } catch (e) {
    box.innerHTML = '';
    box.appendChild(el('div', { cls: 'pf-empty' }, e.message || 'Chargement impossible.'));
    box.appendChild(el('div', { cls: 'mp-modal-actions' },
      el('button', { cls: 'btn btn-ghost', type: 'button', on: { click: closePfModals } }, 'Fermer'),
    ));
  }
}

// ══════════════════════════════════════════════════════════════
// PRODUITS DE NÉGOCE
// ══════════════════════════════════════════════════════════════

const NG_UNITES = ['rouleau', 'pièces', 'kg', 'm', 'boîtes', 'cartons', 'palettes'];

async function loadNegoce() {
  S.ngLoading = true;
  S.ngStock = null;
  renderNegoceView();
  try {
    const [data, mvts] = await Promise.all([
      api('/api/stock/negoce'),
      api('/api/stock/negoce/mouvements?limit=20'),
    ]);
    const payload = data && typeof data === 'object' && !Array.isArray(data) ? data : {};
    S.ngStock = payload.stock || (Array.isArray(data) ? data : []);
    S.ngCatalogue = payload.catalogue || [];
    S.ngKpis = payload.kpis || { references: 0, mouvements_aujourdhui: 0, emplacements_occupes: 0 };
    S.ngTotalMouvements = Number(S.ngKpis.total_mouvements) || 0;
    const mvtsList = Array.isArray(mvts) ? mvts : (mvts && (mvts.mouvements || mvts.items)) || [];
    S.ngMouvements = mvtsList.map(normalizePfMvt);
  } catch (e) {
    S.ngStock = [];
    S.ngCatalogue = [];
    S.ngMouvements = [];
    S.ngKpis = { references: 0, mouvements_aujourdhui: 0, emplacements_occupes: 0 };
    S.ngTotalMouvements = 0;
    showToast(e.message || 'Chargement impossible.', 'error');
  }
  S.ngLoading = false;
  // Recharger la fiche détail si elle est ouverte
  if (S.ngSelDetail && S.ngSelDetail.reference && !S.ngSelDetail.error) {
    const refToReload = String(S.ngSelDetail.reference).toUpperCase();
    try {
      const fresh = await api('/api/stock/negoce/' + encodeURIComponent(refToReload));
      S.ngSelDetail = fresh;
    } catch (e) { /* silencieux : on garde l'ancien état */ }
  }
  renderNegoceView();
}

function renderNegoceView() {
  if (S.tab !== 'negoce') return;
  const ae = document.activeElement;
  const focusId = ae?.id;
  const caretStart = ae?.selectionStart;
  const caretEnd = ae?.selectionEnd;
  const area = document.getElementById('scroll-area');
  if (!area) return;
  area.innerHTML = '';
  const content = (S.ngSelDetail || S.ngSelDetailLoading) ? buildNegoceDetail() : buildNegoceTab();
  if (content) area.appendChild(content);
  if (focusId) {
    const elFocus = document.getElementById(focusId);
    if (elFocus) {
      elFocus.focus();
      if (caretStart != null) {
        try { elFocus.setSelectionRange(caretStart, caretEnd); } catch (e) {}
      }
    }
  }
}

function buildNgCatalogueRows() {
  // Agrège ngStock par référence et fusionne avec ngCatalogue (tous produits, même stock=0)
  const stockByRef = {};
  (S.ngStock || []).forEach(r => {
    const ref = String(r.reference || '').toUpperCase();
    if (!stockByRef[ref]) {
      stockByRef[ref] = { quantite: 0, derniere_entree: null, unite: r.unite, designation: r.designation, emplacements: [] };
    }
    const q = parseFloat(r.quantite || 0);
    stockByRef[ref].quantite += q;
    const empl = String(r.emplacement || '').toUpperCase().trim();
    if (empl && q > 0 && !stockByRef[ref].emplacements.includes(empl)) {
      stockByRef[ref].emplacements.push(empl);
    }
    const de = r.derniere_entree;
    if (de && (!stockByRef[ref].derniere_entree || de > stockByRef[ref].derniere_entree)) {
      stockByRef[ref].derniere_entree = de;
    }
  });
  const seen = new Set();
  const rows = [];
  // Produits du catalogue en premier (incluant 0-stock)
  (S.ngCatalogue || []).forEach(c => {
    const ref = String(c.reference || '').toUpperCase();
    seen.add(ref);
    const s = stockByRef[ref] || { quantite: 0, derniere_entree: null, emplacements: [] };
    rows.push({ reference: ref, designation: c.designation || s.designation || ref, unite: c.unite || s.unite || 'rouleau', quantite: s.quantite, derniere_entree: s.derniere_entree, emplacements: (s.emplacements || []).slice().sort() });
  });
  // Produits en stock mais pas encore dans le catalogue (cas rare)
  Object.entries(stockByRef).forEach(([ref, s]) => {
    if (!seen.has(ref)) {
      rows.push({ reference: ref, designation: s.designation || ref, unite: s.unite || 'rouleau', quantite: s.quantite, derniere_entree: s.derniere_entree, emplacements: (s.emplacements || []).slice().sort() });
    }
  });
  return rows;
}

function filterNgStockList() {
  const list = buildNgCatalogueRows();
  const fs = S.ngFilters || { refs: [], empls: [], q: '', sort: 'ref', hideRupture: false };
  const q = String(fs.q || '').trim().toLowerCase();
  const refSet = new Set((fs.refs || []).map(x => String(x || '').trim().toUpperCase()).filter(Boolean));
  const emplSet = new Set((fs.empls || []).map(x => String(x || '').trim().toUpperCase()).filter(Boolean));
  const filtered = list.filter(row => {
    if (refSet.size && !refSet.has(String(row.reference || '').toUpperCase())) return false;
    if (emplSet.size) {
      const has = (row.emplacements || []).some(e => emplSet.has(String(e || '').toUpperCase()));
      if (!has) return false;
    }
    if (fs.hideRupture && !(parseFloat(row.quantite) > 0)) return false;
    if (q) {
      const hay = [row.reference, row.designation].map(x => String(x || '').toLowerCase()).join(' ');
      if (!hay.includes(q)) return false;
    }
    return true;
  });
  const sort = fs.sort || 'ref';
  if (sort === 'qte') {
    filtered.sort((a, b) => (parseFloat(b.quantite) || 0) - (parseFloat(a.quantite) || 0) || String(a.reference).localeCompare(String(b.reference)));
  } else if (sort === 'recent') {
    filtered.sort((a, b) => String(b.derniere_entree || '').localeCompare(String(a.derniere_entree || '')) || String(a.reference).localeCompare(String(b.reference)));
  } else {
    filtered.sort((a, b) => String(a.reference || '').localeCompare(String(b.reference || '')));
  }
  return filtered;
}

function filterNgMouvementsList() {
  const list = S.ngMouvements || [];
  const fs = S.ngFilters || { refs: [], empls: [], q: '' };
  const q = String(fs.q || '').trim().toLowerCase();
  const refSet = new Set((fs.refs || []).map(x => String(x || '').trim().toUpperCase()).filter(Boolean));
  const emplSet = new Set((fs.empls || []).map(x => String(x || '').trim().toUpperCase()).filter(Boolean));
  return list.filter(m => {
    if (refSet.size && !refSet.has(String(m.reference || '').toUpperCase())) return false;
    if (emplSet.size && !emplSet.has(String(m.emplacement || '').toUpperCase())) return false;
    if (q) {
      const hay = [m.reference, m.emplacement, m.user_login].map(x => String(x || '').toLowerCase()).join(' ');
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

function ngEmplacementChoices(filter) {
  const q = String(filter || '').trim().toUpperCase();
  const fromStock = [...new Set((S.ngStock || []).map(r => String(r.emplacement || '').toUpperCase()).filter(Boolean))];
  const fromDb = allPageEmplacementChoices();
  const all = [...new Set([...fromStock, ...fromDb])].sort();
  if (!q) return all.slice(0, 12);
  return all.filter(e => e.includes(q)).slice(0, 12);
}

function ngProduitSuggestions(filter) {
  const q = String(filter || '').trim().toLowerCase();
  const cat = S.ngCatalogue || [];
  if (!q) return cat.slice(0, 15);
  return cat.filter(c => {
    const hay = (String(c.reference || '') + ' ' + String(c.designation || '')).toLowerCase();
    return hay.includes(q);
  }).slice(0, 15);
}

function ngCatalogueFind(ref) {
  const r = String(ref || '').trim().toUpperCase();
  return (S.ngCatalogue || []).find(c => String(c.reference || '').toUpperCase() === r) || null;
}

function ngStockAtEmpl(reference, emplacement) {
  const ref = String(reference || '').trim().toUpperCase();
  const empl = String(emplacement || '').trim().toUpperCase();
  const row = (S.ngStock || []).find(r =>
    String(r.reference || '').toUpperCase() === ref
    && String(r.emplacement || '').toUpperCase() === empl,
  );
  return row ? (parseFloat(row.quantite) || 0) : 0;
}

function ngAddFilterTag(kind, value) {
  const v = String(value || '').trim();
  if (!v) return;
  if (!S.ngFilters) S.ngFilters = { refs: [], empls: [], q: '', sort: 'ref', hideRupture: false };
  const fs = S.ngFilters;
  if (kind === 'ref') {
    const ref = v.toUpperCase();
    if (!fs.refs) fs.refs = [];
    if (!fs.refs.includes(ref)) fs.refs.push(ref);
  } else if (kind === 'empl') {
    const empl = v.toUpperCase();
    if (!fs.empls) fs.empls = [];
    if (!fs.empls.includes(empl)) fs.empls.push(empl);
  }
  if (!S.ngFilters) S.ngFilters = { refs: [], empls: [], q: '', sort: 'ref', hideRupture: false };
  S.ngFilters.q = '';
}

function ngRemoveFilterTag(kind, value) {
  if (!S.ngFilters) return;
  const fs = S.ngFilters;
  const v = String(value || '').trim().toUpperCase();
  if (kind === 'ref') fs.refs = (fs.refs || []).filter(x => String(x || '').toUpperCase() !== v);
  if (kind === 'empl') fs.empls = (fs.empls || []).filter(x => String(x || '').toUpperCase() !== v);
}

function buildNgUnifiedSearch() {
  if (!S.ngFilters) S.ngFilters = { refs: [], empls: [], q: '', sort: 'ref', hideRupture: false };
  const fs = S.ngFilters;

  const inp = el('input', {
    id: 'ng-search',
    type: 'text',
    placeholder: 'Rechercher (réf, empl, désignation…)',
    autocomplete: 'off',
    spellcheck: 'false',
  });
  inp.value = String(fs.q || '');

  const dd = el('div', { cls: 'pf-search-dd' });
  const ddList = el('div', { cls: 'empl-suggestions', style: { display: 'none' } });
  dd.appendChild(ddList);

  function renderDropdown() {
    const q = String(fs.q || '').trim();
    ddList.innerHTML = '';
    if (!q) { ddList.style.display = 'none'; return; }
    const prod = ngProduitSuggestions(q).slice(0, 8);
    const empls = ngEmplacementChoices(q).slice(0, 8);
    const pushItem = (kind, label, sub) => {
      const kindLbl = kind === 'ref' ? 'Réf' : 'Empl';
      ddList.appendChild(el('div', {
        cls: 'pf-sugg-item',
        on: { mousedown: (e) => {
          e.preventDefault();
          fs.q = '';
          ddList.style.display = 'none';
          if (kind === 'ref') {
            // Ouvre directement la fiche produit
            openPfProduitPage(label);
          } else {
            // Ouvre directement la fiche emplacement
            loadEmplacement(label);
          }
        } },
      },
      el('span', { cls: 'pf-sugg-kind' }, kindLbl),
      el('span', null, ' · '),
      el('span', { cls: 'pf-sugg-main' }, label),
      sub ? el('span', null, ' — ') : null,
      sub ? el('span', { cls: 'pf-sugg-sub' }, sub) : null,
      ));
    };
    prod.forEach(p => pushItem('ref', String(p.reference || '').toUpperCase(), p.designation || ''));
    empls.forEach(e => pushItem('empl', String(e || '').toUpperCase(), ''));
    ddList.style.display = (ddList.childNodes.length ? 'block' : 'none');
  }

  inp.addEventListener('input', (e) => { fs.q = e.target.value; renderNegoceView(); });
  inp.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (String(fs.q || '').trim()) { fs.q = ''; } else { fs.refs = []; fs.empls = []; }
      renderNegoceView(); return;
    }
    if (e.key === 'Backspace' && !String(fs.q || '').trim()) {
      const lastRef = (fs.refs || []).slice(-1)[0];
      const lastEmpl = (fs.empls || []).slice(-1)[0];
      if (lastRef) fs.refs = (fs.refs || []).slice(0, -1);
      else if (lastEmpl) fs.empls = (fs.empls || []).slice(0, -1);
      renderNegoceView(); return;
    }
    if (e.key === 'Enter') {
      const first = ddList.firstElementChild;
      if (first) { e.preventDefault(); first.dispatchEvent(new MouseEvent('mousedown', { bubbles: true })); }
    }
  });

  const tags = el('div', { cls: 'pf-tags pf-tags-below' },
    ...(fs.refs || []).map(r => el('span', { cls: 'pf-tag' },
      el('span', { cls: 'pf-tag-kind' }, 'Réf'),
      el('span', null, r),
      el('button', { cls: 'pf-tag-x', attrs: { type: 'button', title: 'Retirer' }, on: { click: () => { ngRemoveFilterTag('ref', r); renderNegoceView(); } } }, '×'),
    )),
    ...(fs.empls || []).map(e => el('span', { cls: 'pf-tag' },
      el('span', { cls: 'pf-tag-kind' }, 'Empl'),
      el('span', null, e),
      el('button', { cls: 'pf-tag-x', attrs: { type: 'button', title: 'Retirer' }, on: { click: () => { ngRemoveFilterTag('empl', e); renderNegoceView(); } } }, '×'),
    )),
  );

  const box = el('div', { cls: 'pf-toolbar-search' },
    el('span', { cls: 'pf-toolbar-search-icon' }, iconEl('search', 16)),
    el('div', { cls: 'pf-toolbar-searchbox' }, inp),
    tags,
    dd,
  );
  requestAnimationFrame(renderDropdown);
  return box;
}

function buildNgRefPickerField(refInp, desInp, uniteSel, onPick) {
  const suggWrap = el('div', { cls: 'empl-suggestions', style: { display: 'none' } });
  const applyPick = (c) => {
    refInp.value = c.reference || '';
    desInp.value = c.designation || '';
    if (uniteSel && c.unite) uniteSel.value = c.unite;
    suggWrap.innerHTML = '';
    suggWrap.style.display = 'none';
    if (onPick) onPick(c);
  };
  refInp.addEventListener('input', () => {
    const picked = ngCatalogueFind(refInp.value);
    if (picked) {
      desInp.value = picked.designation || '';
      if (uniteSel && picked.unite) uniteSel.value = picked.unite;
    }
  });
  wireStockProduitSearch(refInp, suggWrap, applyPick);
  const refCombo = el('div', { cls: 'empl-combo-wrap' }, refInp, suggWrap);
  return { suggWrap, refCombo };
}

function buildNgEmplPickerField(emplInp) {
  const suggWrap = el('div', { cls: 'empl-suggestions', style: { display: 'none' } });
  wireStockEmplSearch(emplInp, suggWrap);
  const emplCombo = el('div', { cls: 'empl-combo-wrap' }, emplInp, suggWrap);
  return { suggWrap, emplCombo, emplInp };
}

function dashNegoceBadge() {
  return el('span', { cls: 'dash-mp-cat dash-mp-cat-negoce' }, 'NÉGOCE');
}

function negoceCardActions(row) {
  if (S.stockReadOnly) return null;
  const hasStock = (parseFloat(row.quantite) || 0) > 0;
  return el('div', {
    cls: 'mp-card-actions-inline',
    on: { click: (e) => e.stopPropagation() },
  },
    el('button', {
      cls: 'mp-act-btn mp-act-entree',
      type: 'button',
      on: { click: (e) => {
        e.stopPropagation();
        openNgMvtModal('entree', { reference: row.reference, designation: row.designation, unite: row.unite });
      } },
    }, '↓ Entrée'),
    el('button', {
      cls: 'mp-act-btn mp-act-sortie',
      type: 'button',
      attrs: hasStock ? {} : { disabled: 'disabled' },
      style: hasStock ? {} : { opacity: '0.5', cursor: 'not-allowed' },
      on: { click: (e) => {
        e.stopPropagation();
        openNgMvtModal('sortie', { reference: row.reference, designation: row.designation, unite: row.unite });
      } },
    }, '↑ Sortie'),
  );
}

function negoceCardEditBtn(row) {
  if (S.stockReadOnly) return null;
  return el('button', {
    cls: 'mp-act-icon',
    type: 'button',
    attrs: { title: 'Modifier la référence', 'aria-label': 'Modifier la référence' },
    on: { click: (e) => { e.stopPropagation(); openNgCatalogueModal(row.reference); } },
  }, iconEl('edit', 16));
}

function buildNegoceTab() {
  if (S.ngLoading && S.ngStock === null) {
    return el('div', { cls: 'content' }, el('div', { cls: 'hist-page' },
      el('div', { cls: 'card-empty' }, 'Chargement…')));
  }

  if (!S.ngFilters) S.ngFilters = { refs: [], empls: [], q: '', sort: 'ref', hideRupture: false };
  const fs = S.ngFilters;
  const q = String(fs.q || '').trim();
  const filtered = filterNgStockList();

  const head = el('div', { cls: 'hist-head' },
    el('div', null,
      el('h2', { cls: 'hist-title' }, 'Produits de négoce'),
      el('p', { cls: 'hist-subtitle' },
        'Produits revendus en l\'état (sans transformation)'),
    ),
    S.stockReadOnly ? null : el('div', { cls: 'hist-head-actions' },
      el('button', {
        cls: 'btn',
        type: 'button',
        on: { click: () => openNgCatalogueModal() },
      }, 'Gérer les références'),
    ),
  );

  const searchInp = el('input', {
    cls: 'mp-search',
    id: 'negoce-search',
    attrs: {
      type: 'search',
      placeholder: 'Rechercher un produit (référence, désignation…)',
      autocomplete: 'off',
      spellcheck: 'false',
    },
  });
  searchInp.value = q;
  searchInp.addEventListener('input', (e) => {
    fs.q = e.target.value;
    renderNegoceView();
  });
  searchInp.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      fs.q = '';
      renderNegoceView();
    }
  });
  const searchWrap = el('div', { cls: 'mp-search-wrap' },
    el('span', { cls: 'mp-search-icon', attrs: { 'aria-hidden': 'true' } }, iconEl('search', 18)),
    searchInp,
  );

  const list = el('div', { cls: 'mp-list' });

  if (!filtered.length) {
    list.appendChild(el('div', { cls: 'mp-empty' },
      q
        ? 'Aucun produit correspondant à « ' + q + ' ».'
        : 'Aucun produit de négoce enregistré.',
    ));
  } else {
    filtered.forEach(row => {
      const hasStock = (parseFloat(row.quantite) || 0) > 0;
      const stockCls = hasStock ? '' : ' alert';
      const topEnd = [
        el('span', { cls: 'mp-card-stock-total' + stockCls },
          hasStock ? fU(row.quantite, row.unite) : 'Rupture'),
      ];
      const editBtn = negoceCardEditBtn(row);
      if (editBtn) topEnd.push(editBtn);

      const infoChildren = [
        el('div', { cls: 'mp-card-des' }, row.designation || '—'),
        el('span', { cls: 'mp-card-stock-mini' + stockCls },
          hasStock ? 'Stock : ' + fU(row.quantite, row.unite) : 'Aucun stock'),
      ];
      if (row.derniere_entree) {
        infoChildren.push(el('div', { cls: 'mp-card-meta' },
          'Dernière entrée : ' + fD(row.derniere_entree)));
      }
      const empls = (row.emplacements || []);
      if (empls.length) {
        const emplLabel = empls.slice(0, 3).join(', ') + (empls.length > 3 ? ' +' + (empls.length - 3) : '');
        infoChildren.push(el('div', { cls: 'mp-card-meta' },
          (empls.length > 1 ? 'Emplacements : ' : 'Emplacement : ') + emplLabel));
      }

      list.appendChild(el('div', {
        cls: 'mp-card',
        on: { click: () => loadNgDetail(row.reference) },
      },
        el('div', { cls: 'mp-card-top' },
          dashNegoceBadge(),
          el('span', { cls: 'mp-card-ref' }, row.reference || ''),
          el('div', { cls: 'mp-card-top-end' }, ...topEnd),
        ),
        el('div', { cls: 'mp-card-mid' },
          el('div', { cls: 'mp-card-info' }, ...infoChildren),
          el('div', { cls: 'mp-card-side' }, negoceCardActions(row)),
        ),
      ));
    });
  }

  return el('div', { cls: 'content' },
    el('div', { cls: 'hist-page' }, head, searchWrap, list));
}

function closeNgModals() {
  S.ngModal = null;
  const mroot = document.getElementById('mroot');
  if (mroot) mroot.innerHTML = '';
}

function openNgMvtModal(type, preset) {
  if (S.stockReadOnly) return;
  S.ngModal = { type: type === 'sortie' ? 'sortie' : 'entree', preset: preset || null };
  renderNgMvtModal();
}

function renderNgMvtModal() {
  const modal = S.ngModal;
  if (!modal) return;
  const mroot = document.getElementById('mroot');
  if (!mroot) return;
  mroot.innerHTML = '';
  const isSortie = modal.type === 'sortie';
  const headCls = isSortie ? 'mp-modal-mvt-head-pf-sortie' : 'mp-modal-mvt-head-pf-entree';

  const overlay = el('div', {
    id: isSortie ? 'modal-ng-sortie' : 'modal-ng-entree',
    cls: 'mp-modal-overlay',
    on: { click: (e) => { if (e.target === overlay) closeNgModals(); } },
  });
  const box = el('div', { cls: 'mp-modal mp-modal-mvt' });
  box.appendChild(el('div', { cls: 'mp-modal-mvt-head ' + headCls },
    el('h3', null, isSortie ? 'Sortie négoce' : 'Entrée négoce'),
    el('button', { cls: 'mp-modal-close', type: 'button', on: { click: closeNgModals } }, '×'),
  ));
  const body = el('div', { cls: 'mp-modal-mvt-body' });

  const preset = modal.preset || {};
  const refFieldId = isSortie ? 'ng-sortie-ref' : 'ng-entree-ref';
  const refInp = el('input', {
    cls: 'field-input',
    id: refFieldId,
    attrs: { type: 'text', placeholder: 'Référence produit', autocomplete: 'off', required: true },
    style: { direction: 'ltr' },
  });
  refInp.value = preset.reference || '';
  const desInp = el('input', {
    cls: 'field-input',
    attrs: { type: 'text', placeholder: 'Désignation', autocomplete: 'off' },
    style: { direction: 'ltr' },
  });
  desInp.value = preset.designation || '';
  const uniteSel = el('select', { cls: 'field-input' });
  NG_UNITES.forEach(u => {
    const o = el('option', { attrs: { value: u } }, u);
    if ((preset.unite || 'rouleau') === u) o.selected = true;
    uniteSel.appendChild(o);
  });
  const { refCombo } = buildNgRefPickerField(refInp, desInp, uniteSel);

  const qInp = el('input', {
    cls: 'field-input',
    attrs: { type: 'number', min: '0.01', step: '0.01', inputmode: 'decimal', required: true },
    style: { direction: 'ltr' },
  });
  const emplInp = el('input', {
    cls: 'field-input empl-upper',
    attrs: { type: 'text', placeholder: 'Emplacement', autocomplete: 'off', required: true },
    style: { direction: 'ltr' },
  });
  emplInp.value = (preset.emplacement || '').toUpperCase();
  const { emplCombo } = buildNgEmplPickerField(emplInp);
  const hintEl = el('div', { cls: 'mp-hint', style: { display: isSortie ? '' : 'none' } }, '');
  const errEl = el('div', { cls: 'mp-hint err', style: { display: 'none' } }, '');
  const comTa = el('textarea', {
    cls: 'field-input',
    attrs: { rows: '2', placeholder: 'Commentaire (facultatif)' },
    style: { resize: 'vertical', minHeight: '60px' },
  });
  const motifInp = isSortie ? el('input', {
    cls: 'field-input',
    attrs: { type: 'text', placeholder: 'Motif / destinataire (facultatif)', autocomplete: 'off' },
    style: { direction: 'ltr' },
  }) : null;

  body.appendChild(el('div', { cls: 'mp-field ref-field-wrap' }, el('label', null, 'Référence produit *'), refCombo));
  body.appendChild(el('div', { cls: 'mp-field' }, el('label', null, 'Désignation'), desInp));
  body.appendChild(el('div', { cls: 'mp-field' },
    el('label', null, 'Quantité *'), qInp,
    isSortie ? hintEl : null,
    isSortie ? errEl : null,
  ));
  body.appendChild(el('div', { cls: 'mp-field' }, el('label', null, 'Unité'), uniteSel));
  body.appendChild(el('div', { cls: 'mp-field empl-field-wrap' }, el('label', null, 'Emplacement *'), emplCombo));
  if (motifInp) body.appendChild(el('div', { cls: 'mp-field' }, el('label', null, 'Motif / destinataire'), motifInp));
  body.appendChild(el('div', { cls: 'mp-field' }, el('label', null, 'Commentaire'), comTa));

  const collectBody = () => ({
    reference: refInp.value.trim().toUpperCase(),
    designation: desInp.value.trim(),
    quantite: parseFloat(qInp.value),
    unite: uniteSel.value || 'rouleau',
    emplacement: emplInp.value.trim().toUpperCase(),
    commentaire: comTa.value.trim() || null,
    motif_destinataire: motifInp ? (motifInp.value.trim() || null) : null,
  });

  const refreshStockHint = () => {
    if (!isSortie) return;
    const b = collectBody();
    const stock = ngStockAtEmpl(b.reference, b.emplacement);
    if (!b.reference || !b.emplacement) { hintEl.textContent = ''; errEl.style.display = 'none'; return; }
    hintEl.textContent = 'Stock à cet emplacement : ' + fU(stock, uniteSel.value || 'rouleau');
    const q = parseFloat(qInp.value);
    if (q > stock) { errEl.style.display = ''; errEl.textContent = 'Stock insuffisant.'; }
    else { errEl.style.display = 'none'; }
  };
  if (isSortie) {
    refInp.addEventListener('input', refreshStockHint);
    emplInp.addEventListener('input', refreshStockHint);
    qInp.addEventListener('input', refreshStockHint);
    refreshStockHint();
  }

  const saveBtn = el('button', { cls: 'btn ' + (isSortie ? 'btn-danger' : 'btn-accent'), type: 'button' }, 'Enregistrer');

  const doSubmit = async () => {
    const b = collectBody();
    if (!b.reference) { showToast('Référence obligatoire.', 'error'); return; }
    if (!b.emplacement) { showToast('Emplacement obligatoire.', 'error'); return; }
    if (!b.quantite || b.quantite < 0.01) { showToast('Quantité invalide — minimum 0,01.', 'error'); return; }
    if (!b.designation) b.designation = b.reference;
    if (isSortie) {
      const stock = ngStockAtEmpl(b.reference, b.emplacement);
      if (b.quantite > stock) { showToast('Stock insuffisant.', 'error'); return; }
    }
    const path = isSortie ? '/api/stock/negoce/sortie' : '/api/stock/negoce/entree';
    saveBtn.disabled = true;
    try {
      await api(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) });
      showToast(isSortie ? 'Sortie enregistrée.' : 'Entrée enregistrée.');
      closeNgModals();
      await loadNegoce();
    } catch (e) {
      showToast(e.message || 'Enregistrement impossible.', 'error');
      saveBtn.disabled = false;
    }
  };

  const onSave = () => {
    const b = collectBody();
    if (!b.reference) { showToast('Référence obligatoire.', 'error'); return; }
    if (!b.emplacement) { showToast('Emplacement obligatoire.', 'error'); return; }
    if (!b.quantite || b.quantite < 0.01) { showToast('Quantité invalide — minimum 0,01.', 'error'); return; }
    if (!b.designation) b.designation = b.reference;
    if (isSortie) {
      const stock = ngStockAtEmpl(b.reference, b.emplacement);
      if (b.quantite > stock) { showToast('Stock insuffisant.', 'error'); return; }
      // Confirmation sortie
      const overlay2 = el('div', {
        cls: 'mp-modal-overlay',
        on: { click: (e) => { if (e.target === overlay2) { overlay2.remove(); renderNgMvtModal(); } } },
      });
      const box2 = el('div', { cls: 'mp-modal' },
        el('h3', null, 'Confirmer la sortie'),
        el('p', { style: { fontSize: '13px', color: 'var(--text2)', lineHeight: '1.6', marginBottom: '16px' } },
          'Sortie de ' + fU(b.quantite, b.unite) + ' — réf. ' + b.reference + ' depuis ' + b.emplacement + '.',
        ),
        el('div', { cls: 'mp-modal-actions' },
          el('button', { cls: 'btn btn-ghost', type: 'button', on: { click: () => { overlay2.remove(); renderNgMvtModal(); } } }, 'Retour'),
          el('button', { cls: 'btn btn-danger', type: 'button', on: { click: async (e2) => {
            e2.currentTarget.disabled = true;
            await doSubmit();
            overlay2.remove();
          } } }, 'Confirmer la sortie'),
        ),
      );
      overlay2.appendChild(box2);
      mroot.innerHTML = '';
      mroot.appendChild(overlay2);
      return;
    }
    doSubmit();
  };
  saveBtn.addEventListener('click', onSave);

  body.appendChild(el('div', { cls: 'mp-modal-actions' },
    el('button', { cls: 'btn btn-ghost', type: 'button', on: { click: closeNgModals } }, 'Annuler'),
    saveBtn,
  ));
  box.appendChild(body);
  overlay.appendChild(box);
  mroot.appendChild(overlay);
  requestAnimationFrame(() => { document.getElementById(refFieldId)?.focus(); });
}

async function loadNgDetail(reference) {
  const ref = String(reference || '').trim().toUpperCase();
  if (!ref) return;
  S.ngSelDetailLoading = true;
  S.ngSelDetail = null;
  renderNegoceView();
  try {
    const d = await api('/api/stock/negoce/' + encodeURIComponent(ref));
    S.ngSelDetail = d;
  } catch (e) {
    S.ngSelDetail = { error: e.message || 'Chargement impossible.', reference: ref };
    showToast(e.message || 'Chargement impossible.', 'error');
  }
  S.ngSelDetailLoading = false;
  renderNegoceView();
}

function closeNgDetail() {
  S.ngSelDetail = null;
  S.ngSelDetailLoading = false;
  renderNegoceView();
}

function buildNegoceMvtHistory(mouvements, unite) {
  return el('div', { cls: 'card' },
    el('div', { cls: 'card-header' }, el('div', { cls: 'card-title' }, 'Historique des mouvements')),
    !mouvements.length
      ? el('div', { cls: 'card-empty' }, 'Aucun mouvement')
      : el('div', null, ...mouvements.slice(0, 30).map(raw => {
          const m = normalizePfMvt(raw);
          const t = (m.type || '').toLowerCase();
          const icons = { entree: '↓', sortie: '↑', ajustement: '=', transfert: '↔' };
          const signe = t === 'entree' ? '+' : t === 'sortie' ? '−' : t === 'ajustement' ? '=' : '';
          const actor = (m.user_login || '').trim();
          const empl = m.emplacement || '';
          const note = (m.commentaire || m.motif_destinataire || '').trim();
          return el('div', { cls: 'mvt-row' },
            el('div', { cls: 'mvt-icon ' + t }, icons[t] || '·'),
            el('div', { cls: 'mvt-body' },
              el('div', { cls: 'mvt-line1' },
                el('span', null, t === 'entree' ? 'Entrée' : (t === 'sortie' ? 'Sortie' : (t || '—'))),
                el('span', { cls: 'mvt-qte-' + t }, signe + fU(m.quantite, m.unite || unite)),
              ),
              el('div', { cls: 'mvt-line2' },
                fD(m.date_mouvement),
                empl ? el('span', null, ' · ' + (stockEmplLabel(empl) || empl)) : null,
                actor ? el('span', null, ' · ' + actor) : null,
                (m.quantite_apres != null)
                  ? el('span', null, ' · Solde ' + fU(m.quantite_apres, m.unite || unite))
                  : null,
              ),
              note ? el('div', { cls: 'mvt-note' }, note) : null,
            ),
          );
        })),
  );
}

function buildNegoceDetail() {
  const back = el('button', {
    cls: 'btn-ghost',
    style: { marginBottom: '14px' },
    type: 'button',
    on: { click: closeNgDetail },
  }, '← Retour aux produits de négoce');

  if (S.ngSelDetailLoading && !S.ngSelDetail) {
    return el('div', { cls: 'content' }, back,
      el('div', { cls: 'card-empty' }, 'Chargement…'));
  }
  const d = S.ngSelDetail || {};
  if (d.error) {
    return el('div', { cls: 'content' }, back,
      el('div', { cls: 'card-empty' }, d.error));
  }

  const ref = String(d.reference || '').toUpperCase();
  const unite = d.unite || 'rouleau';
  const stockTotal = parseFloat(d.stock_total) || 0;
  const hasStock = stockTotal > 0;
  const empls = Array.isArray(d.emplacements) ? d.emplacements : [];
  const hist = Array.isArray(d.historique) ? d.historique : [];

  const actionBtns = [];
  if (!S.stockReadOnly) {
    actionBtns.push(
      el('button', {
        cls: 'mp-act-btn mp-act-entree',
        type: 'button',
        on: { click: () => openNgMvtModal('entree', { reference: ref, designation: d.designation, unite }) },
      }, '↓ Entrée'),
      el('button', {
        cls: 'mp-act-btn mp-act-sortie',
        type: 'button',
        attrs: hasStock ? {} : { disabled: 'disabled' },
        style: hasStock ? {} : { opacity: '0.5', cursor: 'not-allowed' },
        on: { click: () => openNgMvtModal('sortie', { reference: ref, designation: d.designation, unite }) },
      }, '↑ Sortie'),
      el('button', {
        cls: 'mp-act-icon',
        type: 'button',
        style: { flex: '0 0 auto', minWidth: '44px' },
        attrs: { title: 'Modifier la référence', 'aria-label': 'Modifier la référence' },
        on: { click: () => openNgCatalogueModal(ref) },
      }, iconEl('edit', 16)),
    );
  }
  const actions = actionBtns.length
    ? el('div', { cls: 'action-bar', style: { marginTop: '14px' } }, ...actionBtns)
    : null;

  const emplCard = empls.length
    ? el('div', { cls: 'card', style: { marginTop: '16px' } },
        el('div', { cls: 'card-header' },
          el('div', { cls: 'card-title' }, 'Répartition par emplacement'),
        ),
        el('div', null, ...empls.map(e => {
          const code = String(e.emplacement || '').toUpperCase();
          return el('div', { cls: 'empl-row' },
            el('span', { cls: 'empl-code' }, stockEmplLabel(code) || code || '—'),
            el('span', { cls: 'empl-qte' }, fU(e.quantite, e.unite || unite)),
          );
        })),
      )
    : null;

  return el('div', { cls: 'content' },
    back,
    el('div', { cls: 'scorecard' },
      el('div', { style: { display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginBottom: '8px' } },
        dashNegoceBadge(),
        hasStock ? null : el('span', { style: { fontSize: '12px', color: 'var(--warn)', fontWeight: '600' } }, 'Rupture'),
      ),
      el('div', { cls: 'sc-ref' }, ref || ''),
      el('div', { cls: 'sc-des' }, d.designation || '—'),
      el('div', { style: { fontSize: '12px', color: 'var(--muted)', marginTop: '6px' } }, 'Unité : ' + unite),
      el('div', { cls: 'sc-stats' },
        el('div', { cls: 'sc-stat' },
          el('div', { cls: 'sc-stat-label' }, 'Stock actuel'),
          el('div', { cls: 'sc-stat-value' }, fU(stockTotal, unite)),
        ),
        el('div', { cls: 'sc-stat' },
          el('div', { cls: 'sc-stat-label' }, 'Mouvements'),
          el('div', { cls: 'sc-stat-value' }, String(hist.length)),
        ),
      ),
    ),
    actions,
    emplCard,
    buildNegoceMvtHistory(hist, unite),
  );
}

function openNgCatalogueModal(focusRef) {
  closeNgModals();
  const mroot = document.getElementById('mroot');
  if (!mroot) return;
  const state = {
    q: focusRef ? String(focusRef).toUpperCase() : '',
    editing: null, // ref en cours d'édition
  };
  const overlay = el('div', {
    id: 'modal-ng-catalogue',
    cls: 'mp-modal-overlay',
    on: { click: (e) => { if (e.target === overlay) closeNgModals(); } },
  });
  const box = el('div', { cls: 'mp-modal', style: { maxWidth: '720px' } });
  overlay.appendChild(box);
  mroot.appendChild(overlay);

  function renderCatalogueContent() {
    const ae = document.activeElement;
    const focusId = ae?.id;
    const caretStart = ae?.selectionStart;
    box.innerHTML = '';
    box.appendChild(el('div', { cls: 'mp-modal-head' },
      el('h3', null, 'Catalogue négoce'),
      el('button', { cls: 'mp-modal-close', type: 'button', on: { click: closeNgModals } }, '×'),
    ));
    box.appendChild(el('p', { style: { fontSize: '12px', color: 'var(--text2)', marginBottom: '14px', lineHeight: '1.5' } },
      'Référence, désignation et unité éditables. Les produits sans stock peuvent être supprimés.',
    ));

    // Formulaire d'ajout
    const addRef = el('input', { cls: 'field-input', attrs: { type: 'text', placeholder: 'Référence *', autocomplete: 'off' }, style: { direction: 'ltr' } });
    const addDes = el('input', { cls: 'field-input', attrs: { type: 'text', placeholder: 'Désignation', autocomplete: 'off' }, style: { direction: 'ltr' } });
    const addUnite = el('select', { cls: 'field-input' });
    NG_UNITES.forEach(u => { const o = el('option', { attrs: { value: u } }, u); if (u === 'rouleau') o.selected = true; addUnite.appendChild(o); });
    const addBtn = el('button', { cls: 'btn btn-accent', type: 'button', style: { flexShrink: '0' } }, 'Ajouter');
    addBtn.addEventListener('click', async () => {
      const ref = addRef.value.trim().toUpperCase();
      const des = addDes.value.trim();
      const unite = addUnite.value || 'rouleau';
      if (!ref) { showToast('Référence obligatoire.', 'error'); return; }
      addBtn.disabled = true;
      try {
        await api('/api/stock/negoce/produit', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ reference: ref, designation: des || ref, unite }),
        });
        showToast('Produit ajouté.');
        await loadNegoce();
        renderCatalogueContent();
      } catch (e) {
        showToast(e.message || 'Erreur lors de l\'ajout.', 'error');
        addBtn.disabled = false;
      }
    });
    box.appendChild(el('div', { cls: 'mp-field', style: { display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'flex-end', marginBottom: '14px' } },
      el('div', { style: { flex: '1', minWidth: '120px' } }, el('label', null, 'Réf.'), addRef),
      el('div', { style: { flex: '2', minWidth: '160px' } }, el('label', null, 'Désignation'), addDes),
      el('div', { style: { flex: '1', minWidth: '100px' } }, el('label', null, 'Unité'), addUnite),
      addBtn,
    ));

    // Searchbar dans le catalogue
    const searchInp = el('input', {
      id: 'ng-cat-search',
      cls: 'field-input',
      type: 'text',
      placeholder: 'Rechercher (réf, désignation…)',
      autocomplete: 'off',
      style: { direction: 'ltr', marginBottom: '12px' },
    });
    searchInp.value = state.q;
    searchInp.addEventListener('input', (e) => { state.q = e.target.value; renderCatalogueContent(); });
    searchInp.addEventListener('keydown', (e) => { if (e.key === 'Escape') { state.q = ''; renderCatalogueContent(); } });
    box.appendChild(searchInp);

    // Liste existante (filtrée)
    const cat = S.ngCatalogue || [];
    const stockByRef = {};
    (S.ngStock || []).forEach(r => {
      const k = String(r.reference || '').toUpperCase();
      stockByRef[k] = (stockByRef[k] || 0) + parseFloat(r.quantite || 0);
    });
    const q = state.q.trim().toLowerCase();
    const filteredCat = q
      ? cat.filter(c => (String(c.reference || '') + ' ' + String(c.designation || '')).toLowerCase().includes(q))
      : cat;

    if (!filteredCat.length) {
      const msg = q ? 'Aucun résultat pour « ' + state.q + ' ».' : 'Catalogue vide.';
      box.appendChild(el('div', { cls: 'pf-empty', style: { padding: '16px', textAlign: 'center', fontSize: '13px' } }, msg));
    } else {
      const tbl = el('table', { cls: 'pf-detail-table', style: { width: '100%', marginTop: '0' } });
      tbl.appendChild(el('thead', null, el('tr', null,
        el('th', null, 'Référence'), el('th', null, 'Désignation'), el('th', null, 'Unité'), el('th', null, 'Stock'), el('th', { style: { textAlign: 'right' } }, ''),
      )));
      const tbody = el('tbody', null);
      filteredCat.forEach(c => {
        const ref = String(c.reference || '').toUpperCase();
        const stock = stockByRef[ref] || 0;
        const isEditing = state.editing === ref;

        const refCell = el('td', { style: { fontFamily: 'monospace', fontWeight: '700' } });
        const desCell = el('td', null);
        const uniteCell = el('td', null);
        const stockCell = el('td', null,
          stock > 0 ? fU(stock, c.unite) : el('span', { style: { color: 'var(--muted)' } }, '0'),
        );
        const actCell = el('td', { style: { textAlign: 'right', whiteSpace: 'nowrap' } });

        if (isEditing) {
          const desInp = el('input', { cls: 'field-input', attrs: { type: 'text', value: c.designation || '', autocomplete: 'off' }, style: { direction: 'ltr', fontSize: '12px', padding: '6px 10px' } });
          desInp.value = c.designation || '';
          const uniteSel = el('select', { cls: 'field-input', style: { fontSize: '12px', padding: '6px 10px' } });
          NG_UNITES.forEach(u => { const o = el('option', { attrs: { value: u } }, u); if (u === (c.unite || 'rouleau')) o.selected = true; uniteSel.appendChild(o); });
          refCell.textContent = ref;
          desCell.appendChild(desInp);
          uniteCell.appendChild(uniteSel);
          const saveBtn = el('button', { cls: 'btn-ghost', type: 'button', style: { padding: '4px 8px', color: 'var(--success)', fontSize: '12px', fontWeight: '700' } }, '✓');
          const cancelBtn = el('button', { cls: 'btn-ghost', type: 'button', style: { padding: '4px 8px', color: 'var(--muted)', fontSize: '12px' } }, '×');
          saveBtn.addEventListener('click', async () => {
            const newDes = desInp.value.trim();
            const newUnite = uniteSel.value || 'rouleau';
            saveBtn.disabled = true;
            try {
              await api('/api/stock/negoce/produit', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ reference: ref, designation: newDes || ref, unite: newUnite }),
              });
              showToast('Produit modifié.');
              state.editing = null;
              await loadNegoce();
              renderCatalogueContent();
            } catch (e) {
              showToast(e.message || 'Modification impossible.', 'error');
              saveBtn.disabled = false;
            }
          });
          cancelBtn.addEventListener('click', () => { state.editing = null; renderCatalogueContent(); });
          actCell.appendChild(saveBtn);
          actCell.appendChild(cancelBtn);
        } else {
          refCell.appendChild(el('button', {
            cls: 'mvt-ref-link', type: 'button',
            on: { click: () => { closeNgModals(); loadNgDetail(ref); } },
          }, ref));
          desCell.textContent = c.designation || '—';
          uniteCell.textContent = c.unite || '—';
          const editBtn = el('button', {
            cls: 'btn-ghost', type: 'button',
            style: { padding: '4px 8px', color: 'var(--text2)', fontSize: '12px' },
            attrs: { title: 'Modifier' },
            on: { click: () => { state.editing = ref; renderCatalogueContent(); } },
          }, iconEl('edit', 14) || '✎');
          const delBtn = el('button', {
            cls: 'btn-ghost', type: 'button',
            style: { padding: '4px 8px', color: 'var(--danger)', opacity: stock > 0 ? '0.35' : '1', cursor: stock > 0 ? 'not-allowed' : 'pointer', fontSize: '12px', marginLeft: '4px' },
            attrs: { title: stock > 0 ? 'Stock non nul — soldez avant suppression' : 'Supprimer', disabled: stock > 0 ? '' : null },
          }, iconEl('trash', 14));
          if (stock <= 0) {
            delBtn.addEventListener('click', async () => {
              if (!confirm('Supprimer « ' + ref + ' » du catalogue négoce ?')) return;
              delBtn.disabled = true;
              try {
                await api('/api/stock/negoce/produit/' + encodeURIComponent(ref), { method: 'DELETE' });
                showToast('Produit supprimé.');
                await loadNegoce();
                renderCatalogueContent();
              } catch (e) {
                showToast(e.message || 'Suppression impossible.', 'error');
                delBtn.disabled = false;
              }
            });
          }
          actCell.appendChild(editBtn);
          actCell.appendChild(delBtn);
        }

        tbody.appendChild(el('tr', null, refCell, desCell, uniteCell, stockCell, actCell));
      });
      tbl.appendChild(tbody);
      box.appendChild(el('div', { style: { maxHeight: '320px', overflowY: 'auto' } }, tbl));
    }

    box.appendChild(el('div', { cls: 'mp-modal-actions', style: { marginTop: '16px' } },
      el('button', { cls: 'btn btn-ghost', type: 'button', on: { click: closeNgModals } }, 'Fermer'),
    ));

    // Restaurer le focus
    if (focusId) {
      const elFocus = document.getElementById(focusId);
      if (elFocus) {
        elFocus.focus();
        if (caretStart != null) { try { elFocus.setSelectionRange(caretStart, caretStart); } catch (e) {} }
      }
    }
  }

  renderCatalogueContent();
  requestAnimationFrame(() => {
    const searchEl = document.getElementById('ng-cat-search');
    if (searchEl) { searchEl.focus(); if (state.q) searchEl.setSelectionRange(state.q.length, state.q.length); }
  });
}

// ══════════════════════════════════════════════════════════════
// FIN PRODUITS DE NÉGOCE
// ══════════════════════════════════════════════════════════════

function mpCardEditBtn(m) {
  if (!isMatieresAdmin()) return null;
  return el('button', {
    cls: 'mp-act-icon',
    type: 'button',
    attrs: { title: 'Modifier la référence', 'aria-label': 'Modifier la référence' },
    on: { click: (e) => { e.stopPropagation(); openMatiereRefEditModal(m); } },
  }, iconEl('edit', 16));
}

function mpCardCopyBtn(m) {
  if (!isMatieresAdmin()) return null;
  return el('button', {
    cls: 'mp-act-icon',
    type: 'button',
    attrs: { title: 'Copier vers une nouvelle référence', 'aria-label': 'Copier la référence' },
    on: { click: (e) => { e.stopPropagation(); openMatiereCopyFromCard(m); } },
  }, iconEl('copy', 16));
}

// Ouvre le drawer admin avec le formulaire d'ajout pré-rempli à partir de cette matière
async function openMatiereCopyFromCard(m) {
  if (!isMatieresAdmin() || !m) return;
  S.matieresAdminOpen = true;
  S.matieresAdminEditId = null;
  S.matieresAdminAddError = '';
  // Pré-remplit la graine avant de charger la liste pour que le rendu initial l'utilise
  S.matieresAdminAddSeed = {
    categorie: m.categorie,
    reference: '',
    designation: m.designation || '',
    seuil_alerte: m.seuil_alerte || 0,
    palettes_par_pile: m.palettes_par_pile || null,
    couleur: m.couleur || '',
    sous_section: m.sous_section || '',
    metres_lineaires_par_bobine: m.metres_lineaires_par_bobine || null,
    prix_eur_m2: m.prix_eur_m2 || null,
    unites_par_palette: m.unites_par_palette || null,
    stock_par_laize: Array.isArray(m.stock_par_laize) ? m.stock_par_laize.slice() : [],
  };
  await Promise.all([loadMatieresAdminList(), loadMpSousSections()]);
  renderMatieresAdminDrawer();
  showToast('Référence copiée — saisis la nouvelle référence.', 'info');
}

function matieresCardActions(m) {
  if (S.stockReadOnly) return null;
  return el('div', {
    cls: 'mp-card-actions-inline',
    on: { click: (e) => e.stopPropagation() },
  },
    el('button', {
      cls: 'mp-act-btn mp-act-entree',
      type: 'button',
      on: { click: (e) => {
        e.stopPropagation();
        openModalMouvement('entree', m);
      } },
    }, '↓ Entrée'),
    el('button', {
      cls: 'mp-act-btn mp-act-sortie',
      type: 'button',
      on: { click: (e) => {
        e.stopPropagation();
        openModalMouvement('sortie', m);
      } },
    }, '↑ Sortie'),
  );
}

async function saveMatiereRef(item, payload) {
  await api('/api/stock/matieres/' + item.id, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

function matiereRefEditPayload(item, fields) {
  const ref = fields.refInp.value.trim();
  const des = fields.desInp.value.trim();
  if (!ref || !des) return { error: 'Référence et description obligatoires.' };
  const payload = {
    reference: ref,
    designation: des,
    seuil_alerte: parseFloat(fields.seuilInp.value) || 0,
  };
  if (mpIsGlassineCategory(item) && fields.couleurInp) {
    payload.couleur = fields.couleurInp.value.trim() || des;
  }
  if (fields.hasSousSection && fields.sousSectionSel) {
    // sous_section toujours envoye pour les categories qui la supportent (autorise vidage)
    payload.sous_section = fields.sousSectionSel.getValue();
  }
  if (fields.hasCond && fields.uppInp) {
    const raw = (fields.uppInp.value || '').replace(',', '.').trim();
    if (raw === '') {
      payload.unites_par_palette = null;
    } else {
      const upp = parseFloat(raw);
      if (isNaN(upp) || upp <= 0) {
        return { error: 'Unités par palette : valeur > 0 obligatoire.' };
      }
      payload.unites_par_palette = upp;
    }
  }
  return { payload };
}

// Catégories dont la sous-section est gérée (cohérent avec backend _MP_CATEGORIES_WITH_SOUS_SECTION).
const MP_CATEGORIES_WITH_SOUS_SECTION = new Set(['autre', 'frontal']);
function mpCategorieHasSousSection(cat) {
  return MP_CATEGORIES_WITH_SOUS_SECTION.has(mpCategorieKey(cat));
}

function appendMatiereRefEditFields(parent, item) {
  const refInp = el('input', { attrs: { type: 'text' } });
  refInp.value = item.reference || '';
  const desInp = el('input', { attrs: { type: 'text' } });
  desInp.value = item.designation || '';
  const seuilStep = mpIsBobineCategory(item) || mpIsPaletteCategory(item)
    || mpCategorieKey(item.categorie) === 'carton' || mpCategorieKey(item.categorie) === 'mandrin' ? '1' : '0.5';
  const seuilInp = el('input', { attrs: { type: 'number', min: '0', step: seuilStep } });
  seuilInp.value = String(item.seuil_alerte ?? 0);
  const pppWrap = el('div', { cls: 'mp-field', style: { display: 'none' } });
  const pppInp = el('input', { attrs: { type: 'number', min: '1', step: '1' } });
  pppInp.value = String(item.palettes_par_pile > 0 ? item.palettes_par_pile : '');
  pppWrap.append(el('label', null, 'Palettes par pile'), pppInp);
  const couleurWrap = el('div', { cls: 'mp-field', style: { display: mpIsGlassineCategory(item) ? '' : 'none' } });
  const couleurInp = el('input', { attrs: { type: 'text', placeholder: 'Ex. Blanc, Kraft…' } });
  couleurInp.value = item.couleur || '';
  couleurWrap.append(el('label', null, 'Couleur'), couleurInp);
  // Bloc laizes (frontal/glassine/complexe)
  const isLaizee = mpIsLaizeeCategory(item.categorie);
  const laizeWrap = el('div', { style: 'display:' + (isLaizee ? '' : 'none') + ';border-top:1px dashed var(--border);padding-top:10px;margin-top:6px' });
  const metresInp = el('input', { attrs: { type: 'number', min: '0', step: '1', placeholder: 'Ex. 5000' } });
  metresInp.value = String(item.metres_lineaires_par_bobine != null ? item.metres_lineaires_par_bobine : '');
  const prixM2Inp = el('input', { attrs: { type: 'number', min: '0', step: '0.0001', placeholder: 'Ex. 0,0550' } });
  prixM2Inp.value = String(item.prix_eur_m2 != null ? item.prix_eur_m2 : '');
  const prixM2Field = el('div', { cls: 'mp-field' },
    el('label', null, 'Prix au m² (€) — commun à toutes les laizes'), prixM2Inp);
  // Radio « prix unique / prix par laize »
  const prixModeName = 'prixmode-' + item.id;
  const prixModeUniInp = el('input', { type: 'radio', name: prixModeName, value: '0' });
  const prixModeLaiInp = el('input', { type: 'radio', name: prixModeName, value: '1' });
  const isPrixParLaize = !!item.prix_par_laize;
  if (isPrixParLaize) prixModeLaiInp.checked = true; else prixModeUniInp.checked = true;
  const prixModeField = el('div', { cls: 'mp-field' },
    el('label', null, 'Tarification'),
    el('div', { style: 'display:flex;gap:14px;flex-wrap:wrap;margin-top:4px' },
      el('label', { style: 'display:inline-flex;align-items:center;gap:6px;cursor:pointer;font-size:13px;font-weight:600;color:var(--text)' },
        prixModeUniInp, el('span', null, 'Prix unique')),
      el('label', { style: 'display:inline-flex;align-items:center;gap:6px;cursor:pointer;font-size:13px;font-weight:600;color:var(--text)' },
        prixModeLaiInp, el('span', null, 'Prix par laize')),
    ),
  );
  // Map des prix pré-remplis par laize_id (persistants même si la case est décochée puis recochée)
  const laizePriceInputs = {};
  const laizePriceValues = {};
  (item.stock_par_laize || []).forEach(spl => {
    if (spl && spl.prix_eur_m2 != null) laizePriceValues[spl.laize_id] = String(spl.prix_eur_m2);
  });
  // Bloc « prix €/m² par laize sélectionnée » — visible uniquement en mode par laize
  const laizePricesGrid = el('div', {
    cls: 'mp-laize-prices',
    style: 'display:flex;flex-direction:column;gap:6px;margin-top:6px',
  });
  const laizePricesEmpty = el('div', { cls: 'mp-hint',
    style: 'font-size:12px;color:var(--muted);font-style:italic' }, 'Coche au moins une laize ci-dessous pour saisir son prix.');
  const laizePricesField = el('div', { cls: 'mp-field' },
    el('label', null, 'Prix €/m² par laize'),
    laizePricesGrid,
    laizePricesEmpty,
  );
  // Vue laize (compact, comme avant : flex-wrap horizontal)
  const laizeChecks = el('div', { cls: 'mp-laize-grid',
    style: 'display:flex;flex-wrap:wrap;gap:6px;margin-top:6px' });
  const currentLaizeIds = new Set((item.stock_par_laize || []).map(s => s.laize_id));
  const laizeMetaById = {};
  (S.laizes || []).filter(l => l.actif || currentLaizeIds.has(l.id)).forEach(l => {
    const lid = 'editmat-laize-' + item.id + '-' + l.id;
    const inp = el('input', { type: 'checkbox', id: lid, value: String(l.id) });
    if (currentLaizeIds.has(l.id)) inp.checked = true;
    const lbl = el('label', {
      'for': lid,
      style: 'display:inline-flex;align-items:center;gap:6px;padding:5px 10px;border:1px solid ' + (inp.checked ? 'var(--accent)' : 'var(--border)') + ';border-radius:6px;cursor:pointer;font-size:12px;font-weight:600;background:' + (inp.checked ? 'var(--accent-bg)' : 'var(--bg)') + ';color:var(--text);user-select:none;transition:border-color .15s,background .15s;line-height:1' },
      inp, el('span', null, l.label),
    );
    laizeMetaById[l.id] = { label: l.label, checkbox: inp };
    inp.addEventListener('change', () => {
      lbl.style.borderColor = inp.checked ? 'var(--accent)' : 'var(--border)';
      lbl.style.background = inp.checked ? 'var(--accent-bg)' : 'var(--bg)';
      // Persiste la saisie courante avant re-render
      Object.entries(laizePriceInputs).forEach(([k, elInp]) => {
        laizePriceValues[k] = (elInp.value || '').trim();
      });
      renderLaizePrices();
    });
    laizeChecks.appendChild(lbl);
  });
  // Génère la liste des inputs prix par laize cochée
  function renderLaizePrices() {
    laizePricesGrid.innerHTML = '';
    Object.keys(laizePriceInputs).forEach(k => { delete laizePriceInputs[k]; });
    const selected = Object.entries(laizeMetaById)
      .filter(([, meta]) => meta.checkbox.checked)
      .map(([id, meta]) => ({ id: parseInt(id, 10), label: meta.label }));
    if (!selected.length) {
      laizePricesEmpty.style.display = '';
      return;
    }
    laizePricesEmpty.style.display = 'none';
    selected.forEach(({ id, label }) => {
      const priceInp = el('input', {
        attrs: { type: 'number', min: '0', step: '0.0001', placeholder: '€/m²' },
        style: 'flex:1;min-width:120px;padding:8px 12px;font-size:13px',
      });
      if (laizePriceValues[id] != null) priceInp.value = laizePriceValues[id];
      laizePriceInputs[id] = priceInp;
      const row = el('div', {
        style: 'display:flex;align-items:center;gap:10px',
      },
        el('div', {
          style: 'min-width:80px;font-size:12px;font-weight:700;color:var(--text);padding:6px 10px;border:1px solid var(--accent);background:var(--accent-bg);border-radius:6px;text-align:center',
        }, label),
        priceInp,
        el('span', { style: 'font-size:12px;color:var(--muted);font-weight:600' }, '€/m²'),
      );
      laizePricesGrid.appendChild(row);
    });
  }
  // Bascule affichage prix unique vs prix par laize
  function applyPrixMode() {
    const parLaize = prixModeLaiInp.checked;
    prixM2Field.style.display = parLaize ? 'none' : '';
    laizePricesField.style.display = parLaize ? '' : 'none';
    if (parLaize) renderLaizePrices();
  }
  prixModeUniInp.addEventListener('change', applyPrixMode);
  prixModeLaiInp.addEventListener('change', applyPrixMode);
  laizeWrap.append(
    el('div', { cls: 'mp-field' }, el('label', null, 'Mètres linéaires par bobine'), metresInp),
    prixModeField,
    prixM2Field,
    laizePricesField,
    el('div', { cls: 'mp-field' },
      el('label', null, 'Laizes disponibles'),
      laizeChecks,
    ),
  );
  applyPrixMode();
  // Bloc conditionnement (carton / adhésif / mandrin) — unités par palette
  const hasCond = mpHasConditionnement(item.categorie);
  const uppWrap = el('div', { cls: 'mp-field', style: { display: hasCond ? '' : 'none' } });
  const uniteAchat = mpUniteAchat(item.categorie);
  const uppInp = el('input', { attrs: { type: 'number', min: '0', step: '1', placeholder: 'Ex. 260' } });
  uppInp.value = String(item.unites_par_palette != null && item.unites_par_palette > 0 ? item.unites_par_palette : '');
  uppWrap.append(el('label', null, uniteAchat.charAt(0).toUpperCase() + uniteAchat.slice(1) + ' par palette'), uppInp);
  // Sous-section (catégories autre + frontal) — cloisonnée par catégorie
  const hasSousSection = mpCategorieHasSousSection(item.categorie);
  const sousSectionSel = hasSousSection
    ? buildMpSousSectionSelector(item.sous_section || '', item.categorie)
    : null;
  const sousSectionWrap = hasSousSection
    ? sousSectionSel.el
    : el('div', { style: { display: 'none' } });
  parent.append(
    el('div', { cls: 'mp-field' },
      el('label', null, 'Catégorie'),
      el('div', { cls: 'mp-readonly' }, MP_CAT_LABELS[item.categorie] || item.categorie || '—'),
    ),
    el('div', { cls: 'mp-field' }, el('label', null, 'Référence'), refInp),
    el('div', { cls: 'mp-field' }, el('label', null, 'Description'), desInp),
    couleurWrap,
    pppWrap,
    uppWrap,
    sousSectionWrap,
    el('div', { cls: 'mp-field' }, el('label', null, mpSeuilFieldLabel(item)), seuilInp),
    laizeWrap,
    el('div', { cls: 'mp-hint' }, '0 = pas d\'alerte stock bas.'),
  );
  return { refInp, desInp, seuilInp, pppInp, couleurInp, metresInp, prixM2Inp, laizeChecks, isLaizee, sousSectionSel, hasSousSection, uppInp, hasCond, prixModeUniInp, prixModeLaiInp, laizePriceInputs };
}

async function submitMatiereRefEdit(item, fields, onSaved) {
  const parsed = matiereRefEditPayload(item, fields);
  if (parsed.error) {
    showToast(parsed.error, 'error');
    return;
  }
  try {
    await saveMatiereRef(item, parsed.payload);
    // Si matière laizée, mettre aussi à jour la liste des laizes + métrage + prix m²
    if (fields.isLaizee && fields.laizeChecks) {
      const selectedLaizeIds = Array.from(fields.laizeChecks.querySelectorAll('input[type=checkbox]:checked'))
        .map(i => parseInt(i.value, 10)).filter(x => x > 0);
      const metres = parseFloat((fields.metresInp.value || '').replace(',', '.')) || 0;
      const prix = parseFloat((fields.prixM2Inp.value || '').replace(',', '.')) || 0;
      // Mode prix : 0 = unique, 1 = par laize
      const prixParLaize = fields.prixModeLaiInp && fields.prixModeLaiInp.checked ? 1 : 0;
      // Prix par laize : uniquement pour les laizes sélectionnées
      const laizePrices = {};
      if (prixParLaize && fields.laizePriceInputs) {
        selectedLaizeIds.forEach(lid => {
          const inp = fields.laizePriceInputs[lid];
          const raw = inp ? (inp.value || '').replace(',', '.').trim() : '';
          if (raw === '') {
            laizePrices[lid] = null;
          } else {
            const v = parseFloat(raw);
            if (!isNaN(v) && v >= 0) laizePrices[lid] = v;
          }
        });
      }
      await api('/api/stock/matieres/' + item.id + '/laizes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          laize_ids: selectedLaizeIds,
          metres_lineaires_par_bobine: metres,
          prix_eur_m2: prix,
          prix_par_laize: prixParLaize,
          laize_prices: laizePrices,
        }),
      });
      await loadMatieresIncompleteCount();
    }
    if (fields.hasSousSection) {
      await loadMpSousSections();
    }
    showToast('Référence mise à jour.', 'success');
    if (onSaved) await onSaved();
  } catch (e) {
    showToast(e.message, 'error');
  }
}

async function deleteMatiereRef(item) {
  if (!item || !isMatieresAdmin()) return;
  const ref = (item.reference || '').trim() || 'cette référence';
  const qte = parseFloat(item.quantite) || 0;
  let msg = 'Désactiver la référence « ' + ref + ' » ? Elle ne sera plus proposée dans la liste.';
  if (qte > 0) {
    showToast('Impossible de désactiver une référence avec du stock en cours.', 'error');
    return;
  }
  if (!confirm(msg)) return;
  try {
    await api('/api/stock/matieres/' + item.id, { method: 'DELETE' });
    closeMroot();
    showToast('Référence désactivée.', 'success');
    if (S.selMatiere && S.selMatiere.matiere && S.selMatiere.matiere.id === item.id) {
      S.selMatiere = null;
    }
    await loadMatieres();
    renderContent();
    updateNavActive();
  } catch (e) {
    showToast(e.message, 'error');
  }
}

function openMatiereRefEditModal(item) {
  if (!item || !isMatieresAdmin()) return;
  closeMroot();
  const mroot = document.getElementById('mroot');
  if (!mroot) return;
  const overlay = el('div', {
    cls: 'mp-modal-overlay',
    on: { click: (e) => { if (e.target === overlay) closeMroot(); } },
  });
  const box = el('div', { cls: 'mp-modal', on: { click: (e) => e.stopPropagation() } });
  box.appendChild(el('div', { cls: 'mp-modal-head' },
    el('h3', null, 'Modifier la référence'),
    el('button', {
      cls: 'mp-modal-close',
      type: 'button',
      attrs: { title: 'Fermer', 'aria-label': 'Fermer' },
      on: { click: closeMroot },
    }, '×'),
  ));
  box.appendChild(el('div', { cls: 'mp-modal-sub' },
    (item.reference || '') + (item.designation ? ' — ' + item.designation : ''),
  ));
  const fields = appendMatiereRefEditFields(box, item);
  const onSaved = async () => {
    closeMroot();
    await loadMatieres();
    if (S.selMatiere && S.selMatiere.matiere && S.selMatiere.matiere.id === item.id) {
      await refreshSelMatiere();
    }
  };
  const hasStock = (parseFloat(item.quantite) || 0) > 0;
  box.appendChild(el('div', { cls: 'mp-modal-actions' },
    el('button', {
      cls: 'mp-btn-icon-danger',
      type: 'button',
      disabled: hasStock ? true : null,
      attrs: {
        title: hasStock ? 'Stock en cours — désactivation impossible' : 'Désactiver la référence',
        'aria-label': 'Désactiver la référence',
      },
      on: { click: () => deleteMatiereRef(item) },
    }, iconEl('trash-2', 18)),
    el('div', { cls: 'mp-modal-actions-right' },
      el('button', { cls: 'btn-cancel', type: 'button', on: { click: closeMroot } }, 'Annuler'),
      el('button', {
        cls: 'btn',
        type: 'button',
        on: { click: () => submitMatiereRefEdit(item, fields, onSaved) },
      }, 'Enregistrer'),
    ),
  ));
  if (hasStock) {
    box.appendChild(el('div', { cls: 'mp-hint' },
      'Désactivation impossible tant que le stock est supérieur à 0.',
    ));
  }
  overlay.appendChild(box);
  mroot.appendChild(overlay);
  requestAnimationFrame(() => fields.refInp.focus());
}

function buildMatiereRefEditForm(item, onSaved) {
  const wrap = el('div', { cls: 'mp-admin-edit' });
  const fields = appendMatiereRefEditFields(wrap, item);
  wrap.appendChild(el('button', {
    cls: 'btn',
    type: 'button',
    on: { click: () => submitMatiereRefEdit(item, fields, onSaved) },
  }, 'Enregistrer'));
  return wrap;
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
        'Mandrins (pal.), frontaux et glassines (bob.), adhésifs (pal.), palettes (piles), cartons (pal.)'),
    ),
    isMatieresAdmin()
      ? el('div', { cls: 'hist-head-actions' },
          el('button', {
            cls: 'btn',
            type: 'button',
            on: { click: () => openMatieresAdminDrawer() },
          }, 'Gérer les références'),
        )
      : null,
  );
  // Construit la liste réelle des pills : on remplace la pill "frontal" par
  // une pill par sous-section frontale présente. La sélection actuelle est
  // matérialisée par S.matieresCat + S.matieresSousSection.
  const frontalSousSections = mpFrontalSousSections(S.matieres);
  const expandFrontal = frontalSousSections.length > 0;
  const pillDefs = [];
  MP_PILL_CATS.forEach(p => {
    if (p.id === 'frontal' && expandFrontal) {
      // Une pill par sous-section (chaque pill = un (categorie, sous_section))
      frontalSousSections.forEach(ss => {
        pillDefs.push({
          id: MP_FRONTAL_SS_PREFIX + ss.slug,
          label: ss.label,
          cat: 'frontal',
          // Pour la sentinelle "sans sous-section", on conserve slug='' qui sert d'indicateur
          sousSection: ss.slug ? ss.label : null,
          isFrontalSs: true,
          ssSlug: ss.slug,
        });
      });
    } else {
      pillDefs.push({ id: p.id, label: p.label, cat: p.id, sousSection: null });
    }
  });

  // Détermine la pill active à partir de l'état
  const activePillId = (() => {
    const cat = S.matieresCat || 'tout';
    const ss = S.matieresSousSection || null;
    if (cat === 'frontal' && expandFrontal) {
      // Si une sous-section est active, on retrouve son slug. Sinon, on prend la 1re par défaut.
      if (ss) {
        const slug = (ss === MP_SOUS_SECTION_NONE) ? '' : mpSousSectionSlug(ss);
        return MP_FRONTAL_SS_PREFIX + slug;
      }
      // Si pas de sous-section précise mais cat=frontal : on retombe sur la 1re pill ss frontale
      return MP_FRONTAL_SS_PREFIX + (frontalSousSections[0]?.slug || '');
    }
    return cat;
  })();

  const pills = el('div', { cls: 'mp-pills' },
    ...pillDefs.map(d => el('button', {
      cls: 'mp-pill mp-pill-' + d.id.replace(/[^a-z0-9]/g, '-')
        + (activePillId === d.id ? ' active' : ''),
      type: 'button',
      on: { click: () => {
        if (d.isFrontalSs) {
          S.matieresCat = 'frontal';
          // Pas de label de sous-section → sentinelle "sans sous-section"
          S.matieresSousSection = d.sousSection ? d.sousSection : MP_SOUS_SECTION_NONE;
        } else {
          if (S.matieresCat !== d.cat) {
            S.matieresCat = d.cat;
            S.matieresSousSection = null;
          }
        }
        renderMatieresView();
      } },
    }, d.label)),
  );
  // Plus de 2e ligne de sub-pills : les sous-sections frontal sont promues au 1er niveau
  const subPills = null;
  const searchInp = el('input', {
    cls: 'mp-search',
    id: 'matieres-search',
    attrs: {
      type: 'search',
      placeholder: 'Rechercher une matière (référence, désignation, catégorie…)',
      autocomplete: 'off',
      spellcheck: 'false',
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
  const searchWrap = el('div', { cls: 'mp-search-wrap' },
    el('span', { cls: 'mp-search-icon', attrs: { 'aria-hidden': 'true' } }, iconEl('search', 18)),
    searchInp,
  );
  const list = el('div', { cls: 'mp-list' });
  const renderMpCard = (m) => {
    const seuil = parseFloat(m.seuil_alerte) || 0;
    const alertCls = m.en_alerte ? ' alert' : '';
    const infoChildren = [
      el('div', { cls: 'mp-card-des' }, m.designation || '—'),
      el('span', { cls: 'mp-card-stock-mini' + alertCls }, mpStockMini(m.quantite, m)),
    ];
    if (mpIsPaletteCategory(m) && m.palettes_par_pile > 0) {
      infoChildren.push(el('div', { cls: 'mp-card-meta' },
        fN(m.palettes_par_pile) + ' pal. / pile'));
    }
    if (mpIsGlassineCategory(m) && m.couleur) {
      infoChildren.push(el('div', { cls: 'mp-card-meta' }, 'Couleur : ' + m.couleur));
    }
    // Laizes disponibles (frontal / glassine / complexe)
    if (mpIsLaizeeCategory(m.categorie)) {
      const spl = Array.isArray(m.stock_par_laize) ? m.stock_par_laize : [];
      if (spl.length > 0) {
        // Trie par valeur_mm croissant pour un affichage stable
        const sorted = spl.slice().sort((a, b) => (a.valeur_mm || 0) - (b.valeur_mm || 0));
        const chips = sorted.map(s => {
          const label = s.label || ((s.valeur_mm || 0) + ' mm');
          const qty = Number(s.quantite || 0);
          const isEmpty = qty <= 0;
          return el('span', {
            style: 'display:inline-flex;align-items:center;gap:4px;padding:2px 8px;border-radius:999px;'
              + (isEmpty
                  ? 'background:transparent;color:var(--muted);border:1px solid var(--border)'
                  : 'background:var(--accent-bg);color:var(--accent);border:1px solid transparent')
              + ';font-size:11px;font-weight:600;font-variant-numeric:tabular-nums;line-height:1.4',
            title: label + ' — ' + fN(qty) + ' bob.',
          },
            el('span', null, label),
            el('span', { style: 'opacity:.7;font-weight:500' }, fN(qty) + ' bob.'),
          );
        });
        infoChildren.push(el('div', {
          style: 'display:flex;flex-wrap:wrap;gap:4px;margin-top:4px',
        }, ...chips));
      } else {
        infoChildren.push(el('div', { cls: 'mp-card-meta',
          style: 'color:#fb923c;font-weight:600' }, 'Aucune laize configurée'));
      }
    }
    if (m.en_alerte) {
      infoChildren.push(el('div', { cls: 'mp-card-warn' },
        'Sous le seuil (min. ' + mpStockLine(seuil, m) + ')'));
    }
    const topEnd = [
      el('span', {
        cls: 'mp-card-stock-total' + alertCls,
        attrs: { title: mpStockTotalLabel(m) },
      }, mpStockLine(m.quantite, m)),
    ];
    const copyBtn = mpCardCopyBtn(m);
    if (copyBtn) topEnd.push(copyBtn);
    const editBtn = mpCardEditBtn(m);
    if (editBtn) topEnd.push(editBtn);
    list.appendChild(el('div', {
      cls: 'mp-card',
      on: { click: () => loadMatiere(m.id) },
    },
      el('div', { cls: 'mp-card-top' },
        dashMpCatBadge(m.categorie, m.sous_section),
        el('span', { cls: 'mp-card-ref' }, m.reference || ''),
        el('div', { cls: 'mp-card-top-end' }, ...topEnd),
      ),
      el('div', { cls: 'mp-card-mid' },
        el('div', { cls: 'mp-card-info' }, ...infoChildren),
        el('div', { cls: 'mp-card-side' }, matieresCardActions(m)),
      ),
    ));
  };
  const mpSectionHeadStyle = 'margin:14px 4px 4px;font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px';
  const mpSubsectionHeadStyle = 'margin:10px 4px 4px;padding:6px 12px;font-size:12px;font-weight:700;color:var(--accent);background:var(--accent-bg);border-radius:8px;display:inline-block';
  if (!filtered.length) {
    list.appendChild(el('div', { cls: 'mp-empty' },
      q
        ? 'Aucune matière correspondant à « ' + q + ' ».'
        : 'Aucune matière dans cette catégorie.',
    ));
  } else {
    // Plus de bandeau sous-section : les sous-sections frontal sont promues au niveau pill.
    // Cas 1 : pill spécifique (Couché, Mandrins, etc.) → rendu plat, pas de header.
    // Cas 2 : pill "Tout" → on regroupe par "catégorie virtuelle" où les frontaux
    //         sont éclatés par sous_section, exactement comme dans la barre de pills.
    const curCat = S.matieresCat || 'tout';
    if (curCat !== 'tout') {
      filtered.forEach(renderMpCard);
    } else {
      // Construit des buckets par catégorie virtuelle
      const buckets = new Map();
      const keyFor = (m) => {
        const c = mpCategorieKey(m.categorie);
        if (c === 'frontal') {
          const ss = (m.sous_section || '').trim();
          return ss ? ('frontal:' + ss) : 'frontal:';
        }
        return c;
      };
      const labelFor = (m) => {
        const c = mpCategorieKey(m.categorie);
        if (c === 'frontal') {
          const ss = (m.sous_section || '').trim();
          return ss || 'Frontal (sans sous-section)';
        }
        return MP_CAT_LABELS[c] || c;
      };
      filtered.forEach(m => {
        const k = keyFor(m);
        if (!buckets.has(k)) buckets.set(k, { label: labelFor(m), items: [] });
        buckets.get(k).items.push(m);
      });
      const keys = Array.from(buckets.keys()).sort((a, b) => {
        const la = buckets.get(a).label, lb = buckets.get(b).label;
        return la.localeCompare(lb, 'fr');
      });
      keys.forEach(k => {
        const b = buckets.get(k);
        list.appendChild(el('div', { cls: 'mp-section-head', style: mpSectionHeadStyle },
          b.label + ' · ' + b.items.length));
        b.items.forEach(renderMpCard);
      });
    }
  }
  // Bandeau orange si des matières frontal/glassine/complexe sont incomplètes
  const banner = (S.matieresIncompleteCount > 0)
    ? el('div', {
        style: 'background:rgba(251,146,60,0.12);border:1px solid rgba(251,146,60,0.45);border-radius:10px;padding:10px 14px;margin-bottom:12px;color:var(--text);font-size:13px;display:flex;align-items:center;gap:10px',
      },
        iconEl('alert-triangle', 16),
        el('span', null,
          el('strong', null, S.matieresIncompleteCount + (S.matieresIncompleteCount > 1 ? ' matières' : ' matière')),
          ' à compléter (laizes / prix m² / métrage manquant).'
        ),
      )
    : null;
  return el('div', { cls: 'content' },
    el('div', { cls: 'hist-page' }, head, banner, searchWrap, pills, subPills, list));
}

function buildMpEmplacementField() {
  const emplInp = el('input', {
    cls: 'field-input empl-upper',
    attrs: {
      type: 'text',
      placeholder: 'Emplacement (ex. A121, ' + STOCK_EMPL_AU_SOL + ', ' + STOCK_EMPL_SORTIE_PROD + ')…',
      autocomplete: 'off',
    },
    style: { direction: 'ltr' },
  });
  const suggWrap = el('div', { cls: 'empl-suggestions', style: { display: 'none' } });
  wireStockEmplSearch(emplInp, suggWrap);
  const combo = el('div', { cls: 'empl-combo-wrap' }, emplInp, suggWrap);
  const wrap = el('div', { cls: 'mp-field empl-field-wrap' },
    el('label', null, 'Emplacement'),
    combo,
  );
  return { wrap, emplInp };
}

function mpEmplacementValue(emplInp) {
  return String(emplInp?.value || '').trim().toUpperCase();
}

function validateMpEmplacement(empl) {
  if (!empl) return 'Emplacement obligatoire.';
  if (!isStockEmplacementCode(empl)) {
    return 'Format invalide — grille (ex. A123), « ' + STOCK_EMPL_AU_SOL_LABEL + ' » (' + STOCK_EMPL_AU_SOL + ') ou « ' + STOCK_EMPL_SORTIE_PROD_LABEL + ' » (' + STOCK_EMPL_SORTIE_PROD + ').';
  }
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

function renderMpMouvementModal(type, matiere, categorieFilter) {
  const typeMvt = (type || 'entree').toLowerCase();
  const allList = (S.matieres || []).filter(m => m.actif !== 0);
  let mat = matiere || null;
  // Catégorie du filtre : priorité au paramètre, sinon catégorie de la matière sélectionnée
  let cat = (categorieFilter != null) ? String(categorieFilter || '').toLowerCase() : null;
  if (cat == null && mat) cat = mpCategorieKey(mat.categorie);
  if (cat == null) cat = '';
  // Liste filtrée par catégorie (vide = toutes)
  const list = cat
    ? allList.filter(m => mpCategorieKey(m.categorie) === cat)
    : allList;
  // Si la matière courante ne matche plus le filtre, on la désélectionne
  if (mat && cat && mpCategorieKey(mat.categorie) !== cat) mat = null;
  if (!mat && list.length === 1) mat = list[0];
  closeMroot();
  const mroot = document.getElementById('mroot');
  if (!mroot) return;
  S.mpModal = {
    type: typeMvt, matiere: mat, matiereId: mat ? mat.id : null,
    categorie: cat || (mat ? mpCategorieKey(mat.categorie) : ''),
    laizeId: null,
  };
  const stockActuel = mat ? (parseFloat(mat.quantite) || 0) : 0;
  const mpCat = mat || list.find(x => x.id === S.mpModal.matiereId) || null;

  const overlay = el('div', {
    cls: 'mp-modal-overlay',
    on: { click: (e) => { if (e.target === overlay) closeMroot(); } },
  });
  const headTypeCls = ['entree', 'sortie', 'ajustement', 'transfert'].includes(typeMvt) ? typeMvt : '';
  const box = el('div', { cls: 'mp-modal mp-modal-mvt' });
  box.appendChild(el('div', { cls: 'mp-modal-mvt-head mp-modal-mvt-head-' + headTypeCls },
    el('h3', null, MP_MVT_TITLES[typeMvt] || typeMvt),
    el('button', {
      cls: 'mp-modal-close',
      type: 'button',
      attrs: { title: 'Fermer', 'aria-label': 'Fermer' },
      on: { click: closeMroot },
    }, '×'),
  ));
  const body = el('div', { cls: 'mp-modal-mvt-body' });

  // Sélecteur de type de MP (catégorie) — toujours présent
  const catSel = el('select', { id: 'mp-modal-categorie-select' });
  catSel.appendChild(el('option', { value: '' }, '— Tous les types —'));
  const CAT_ORDER = ['frontal', 'glassine', 'mandrin', 'adhesif', 'carton', 'palette'];
  CAT_ORDER.forEach(c => {
    catSel.appendChild(el('option', {
      value: c,
      selected: S.mpModal.categorie === c ? true : null,
    }, MP_CAT_LABELS[c] || c));
  });
  catSel.addEventListener('change', () => {
    renderMpMouvementModal(typeMvt, null, catSel.value || '');
  });
  body.appendChild(el('div', { cls: 'mp-field' },
    el('label', null, 'Type de matière'),
    catSel,
  ));

  if (mat) {
    body.appendChild(el('div', { cls: 'mp-field' },
      el('label', null, 'Matière'),
      el('div', { cls: 'mp-readonly' }, (mat.reference || '') + ' — ' + (mat.designation || '')),
      el('div', { style: { marginTop: '6px' } },
        el('button', {
          cls: 'btn-ghost', type: 'button',
          style: { fontSize: '11px', padding: '4px 8px', border: '1px solid var(--border)',
                   borderRadius: '6px', background: 'transparent', color: 'var(--muted)',
                   cursor: 'pointer', fontFamily: 'inherit' },
          on: { click: () => renderMpMouvementModal(typeMvt, null, S.mpModal.categorie || '') },
        }, '× Changer de matière'),
      ),
    ));
    // Sélecteur de laize pour les matières laizées
    if (mpIsLaizeeCategory(mat.categorie) && Array.isArray(mat.stock_par_laize) && mat.stock_par_laize.length > 0) {
      const laizeSel = el('select', { id: 'mp-modal-laize-select' });
      laizeSel.appendChild(el('option', { value: '' }, '— Choisir la laize —'));
      mat.stock_par_laize.forEach(spl => {
        laizeSel.appendChild(el('option', {
          value: String(spl.laize_id),
          selected: S.mpModal.laizeId === spl.laize_id ? true : null,
        }, (spl.label || (spl.valeur_mm + ' mm')) + ' (stock ' + fN(spl.quantite) + ' bob.)'));
      });
      laizeSel.addEventListener('change', () => {
        const v = parseInt(laizeSel.value, 10);
        S.mpModal.laizeId = v || null;
      });
      body.appendChild(el('div', { cls: 'mp-field' }, el('label', null, 'Laize'), laizeSel));
    } else if (mpIsLaizeeCategory(mat.categorie)) {
      body.appendChild(el('div', {
        cls: 'mp-hint err',
        style: 'background:rgba(251,146,60,0.10);border:1px solid rgba(251,146,60,0.4);padding:8px 10px;border-radius:8px;color:var(--text)' },
        'Aucune laize associée à cette matière. Édite-la pour ajouter ses laizes avant de saisir un mouvement.'));
    }
  } else {
    const sel = el('select', { id: 'mp-modal-matiere-select' });
    const placeholder = list.length
      ? '— Choisir une matière —'
      : (cat ? 'Aucune matière dans cette catégorie' : '— Choisir une matière —');
    sel.appendChild(el('option', { value: '' }, placeholder));
    // Pour les matières laizées, on déplie chaque référence par laize associée
    list.forEach(item => {
      if (item.laizee && Array.isArray(item.stock_par_laize) && item.stock_par_laize.length > 0) {
        item.stock_par_laize.forEach(spl => {
          const val = String(item.id) + ':' + String(spl.laize_id);
          const isSel = (S.mpModal.matiereId === item.id && S.mpModal.laizeId === spl.laize_id);
          sel.appendChild(el('option', { value: val, selected: isSel ? true : null },
            item.reference + ' — ' + (spl.label || (spl.valeur_mm + ' mm')) + ' (' + fN(spl.quantite) + ' bob.)',
          ));
        });
      } else {
        sel.appendChild(el('option', {
          value: String(item.id),
          selected: S.mpModal.matiereId === item.id ? true : null,
        }, item.reference + ' — ' + item.designation));
      }
    });
    sel.addEventListener('change', () => {
      const raw = sel.value;
      if (!raw) { renderMpMouvementModal(typeMvt, null, S.mpModal.categorie || ''); return; }
      const parts = raw.split(':');
      const id = parseInt(parts[0], 10);
      const laizeId = parts.length > 1 ? parseInt(parts[1], 10) : null;
      const found = list.find(x => x.id === id);
      if (found && laizeId) {
        S.mpModal.laizeId = laizeId;
        renderMpMouvementModal(typeMvt, found || null, S.mpModal.categorie || '');
        if (S.mpModal) S.mpModal.laizeId = laizeId;
      } else {
        S.mpModal.laizeId = null;
        renderMpMouvementModal(typeMvt, found || null, S.mpModal.categorie || '');
      }
    });
    body.appendChild(el('div', { cls: 'mp-field' }, el('label', null, 'Matière / laize'), sel));
  }

  const hintEl = el('div', { cls: 'mp-hint' }, '');
  const errEl = el('div', { cls: 'mp-hint err', style: { display: 'none' } }, '');

  if (typeMvt === 'entree') {
    const isLaizeeCat = mpIsLaizeeCategory(S.mpModal.categorie) || (mat && mpIsLaizeeCategory(mat.categorie));
    const hideEmpl = !!S.fabStockMode || isLaizeeCat;
    const emplField = hideEmpl ? null : buildMpEmplacementField();
    const blInp = el('input', { attrs: { type: 'text', placeholder: 'BL-2024-001' } });
    const qInp = el('input', { attrs: mpQuantiteInputAttrs(mpCat) });
    // Prix €/m² de la réception — uniquement pour bobines laizées
    const showPrix = isLaizeeCat && !!mat;
    const prixInp = showPrix ? el('input', {
      attrs: { type: 'number', min: '0', step: '0.0001', placeholder: 'Ex. 0,0550' }
    }) : null;
    const prixHint = showPrix ? el('div', { cls: 'mp-hint',
      style: 'font-size:11px;color:var(--muted);margin-top:4px;line-height:1.4' }, '') : null;
    function computeCurrentPrix() {
      if (!mat) return 0;
      const parLaize = !!mat.prix_par_laize;
      if (parLaize && S.mpModal.laizeId && Array.isArray(mat.stock_par_laize)) {
        const spl = mat.stock_par_laize.find(s => s.laize_id === S.mpModal.laizeId);
        return spl && spl.prix_eur_m2 != null ? parseFloat(spl.prix_eur_m2) : 0;
      }
      return parseFloat(mat.prix_eur_m2 || 0);
    }
    function refreshPrixHint() {
      if (!prixHint) return;
      const p = computeCurrentPrix();
      const modeTxt = mat.prix_par_laize ? ' (par laize)' : ' (matière)';
      if (p > 0) {
        prixHint.textContent = 'Prix courant' + modeTxt + ' : ' + p.toLocaleString('fr-FR', { minimumFractionDigits: 4, maximumFractionDigits: 4 })
          + ' €/m². Laisser vide pour le conserver, sinon le PMP sera recalculé automatiquement.';
      } else {
        prixHint.textContent = 'Aucun prix courant enregistré. Si tu saisis un prix, il devient le prix de référence.';
      }
    }
    if (emplField) body.appendChild(emplField.wrap);
    body.appendChild(el('div', { cls: 'mp-field' },
      el('label', null, 'Référence BL / Fournisseur'),
      blInp,
    ));
    body.appendChild(el('div', { cls: 'mp-field' },
      el('label', null, mpQuantiteFieldLabel(mpCat)),
      qInp,
    ));
    if (prixInp) {
      body.appendChild(el('div', { cls: 'mp-field' },
        el('label', null, 'Prix €/m² de cette réception'),
        prixInp,
        prixHint,
      ));
      refreshPrixHint();
      // Le hint dépend de la laize choisie — on la met à jour au change
      const laizeSelEl = body.querySelector('#mp-modal-laize-select');
      if (laizeSelEl) laizeSelEl.addEventListener('change', refreshPrixHint);
    }
    S.mpModal.getBody = () => {
      const b = {
        matiere_id: S.mpModal.matiereId,
        type_mouvement: 'entree',
        quantite: parseFloat(qInp.value),
        ref_bl: (blInp.value || '').trim() || null,
        note: null,
        emplacement_source: null,
        emplacement_dest: emplField ? (mpEmplacementValue(emplField.emplInp) || null) : null,
      };
      if (prixInp) {
        const raw = (prixInp.value || '').replace(',', '.').trim();
        if (raw !== '') {
          const v = parseFloat(raw);
          if (!isNaN(v) && v >= 0) b.prix_eur_m2 = v;
        }
      }
      return b;
    };
    S.mpModal.validate = () => {
      const q = parseFloat(qInp.value);
      if (!S.mpModal.matiereId) return 'Matière obligatoire.';
      if (emplField) {
        const emplErr = validateMpEmplacement(mpEmplacementValue(emplField.emplInp));
        if (emplErr) return emplErr;
      }
      if (!q || q <= 0) return 'Quantité invalide.';
      if (prixInp && prixInp.value) {
        const raw = prixInp.value.replace(',', '.').trim();
        const v = parseFloat(raw);
        if (isNaN(v) || v < 0) return 'Prix €/m² invalide.';
      }
      return null;
    };
  } else if (typeMvt === 'sortie') {
    const isLaizeeCat = mpIsLaizeeCategory(S.mpModal.categorie) || (mat && mpIsLaizeeCategory(mat.categorie));
    const hideEmpl = !!S.fabStockMode || isLaizeeCat;
    const emplField = hideEmpl ? null : buildMpEmplacementField();
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
    if (emplField) body.appendChild(emplField.wrap);
    body.appendChild(el('div', { cls: 'mp-field' },
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
      emplacement_source: emplField ? (mpEmplacementValue(emplField.emplInp) || null) : null,
      emplacement_dest: null,
    });
    S.mpModal.validate = () => {
      const q = parseFloat(qInp.value);
      if (!S.mpModal.matiereId) return 'Matière obligatoire.';
      if (emplField) {
        const emplErr = validateMpEmplacement(mpEmplacementValue(emplField.emplInp));
        if (emplErr) return emplErr;
      }
      if (!q || q <= 0) return 'Quantité invalide.';
      if (q > stockActuel) return 'Stock insuffisant.';
      return null;
    };
  } else if (typeMvt === 'ajustement') {
    hintEl.textContent = 'Stock actuel : ' + mpStockLine(stockActuel, mpCat);
    const stepAdj = mpIsPaletteCategory(mpCat) || ['carton', 'mandrin'].includes(mpCategorieKey(mpCat?.categorie)) ? '1' : '0.5';
    const qInp = el('input', { attrs: { type: 'number', min: '0', step: stepAdj } });
    body.appendChild(el('div', { cls: 'mp-field' },
      hintEl,
      el('label', null, 'Nouveau stock (' + mpUniteNom(mpCat) + 's)'),
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
    body.appendChild(el('div', { cls: 'mp-field' }, el('label', null, mpQuantiteFieldLabel(mpCat)), qInp));
    body.appendChild(el('div', { cls: 'mp-field' }, el('label', null, 'Emplacement source'), srcInp));
    body.appendChild(el('div', { cls: 'mp-field' }, el('label', null, 'Emplacement destination'), dstInp));
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
  body.appendChild(el('div', { cls: 'mp-field' }, el('label', null, 'Note'), noteTa));
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

  body.appendChild(el('div', { cls: 'mp-modal-actions' },
    el('button', { cls: 'btn-cancel', type: 'button', on: { click: closeMroot } }, 'Annuler'),
    el('button', { cls: 'btn', type: 'button', on: { click: submitMpMouvement } }, 'Valider'),
  ));
  box.appendChild(body);
  overlay.appendChild(box);
  mroot.appendChild(overlay);
}

async function submitMpMouvement() {
  if (!S.mpModal) return;
  const err = S.mpModal.validate ? S.mpModal.validate() : null;
  if (err) { showToast(err, 'error'); return; }
  const body = S.mpModal.getBody();
  // Injecte la laize pour les matières laizées (frontal/glassine/complexe)
  const mat = S.mpModal.matiere;
  if (mat && mpIsLaizeeCategory(mat.categorie)) {
    if (!S.mpModal.laizeId) {
      showToast('Laize obligatoire pour cette catégorie.', 'error');
      return;
    }
    body.laize_id = S.mpModal.laizeId;
  }
  try {
    const res = await api('/api/stock/matieres/mouvement', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (res && res.ok) {
      closeMroot();
      showToast('Mouvement enregistré.', 'success');
      if (S.selMatiere) {
        try {
          const d = await api('/api/stock/matieres');
          S.matieres = Array.isArray(d) ? d : [];
        } catch (e) { /* refreshSelMatiere affichera l'erreur */ }
        await refreshSelMatiere();
      } else {
        await loadMatieres();
        if (S.tab === 'dashboard') await loadDashboard();
      }
    }
  } catch (e) {
    showToast(e.message || 'Erreur lors de l\'enregistrement.', 'error');
  }
}

async function fetchPfStockAtEmpl(produitId, empl) {
  if (!produitId || !empl) return 0;
  try {
    const d = await api('/api/stock/produits/' + produitId);
    const row = (d.emplacements || []).find(e => String(e.emplacement || '').toUpperCase() === empl);
    return row ? (parseFloat(row.quantite) || 0) : 0;
  } catch (e) {
    return 0;
  }
}

function openModalPfMouvement(type, produit) {
  renderPfMouvementModal(type, produit || null);
}

// Z1 enrichi : dossier de prod + palettes
function _fmtDateFRz1(d) {
  const dd = String(d.getDate()).padStart(2, '0');
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  return dd + '/' + mm + '/' + d.getFullYear();
}

async function _fetchZ1DossierContext() {
  try {
    const r = await api('/api/fabrication/dossier-en-cours');
    return {
      dossier: (r && r.dossier) || null,
      precedents: Array.isArray(r && r.precedents) ? r.precedents : [],
      machine: (r && r.machine) || null,
      canSearchAll: !!(r && r.can_search_all),
    };
  } catch (e) {
    return { dossier: null, precedents: [], machine: null, canSearchAll: false };
  }
}

// Retro-compat : garde l'ancien nom si un consommateur externe l'utilise.
async function _fetchDossierEnCours() {
  const ctx = await _fetchZ1DossierContext();
  return ctx.dossier;
}

async function _fetchPaletteTypes() {
  try {
    const r = await api('/api/stock/matieres');
    if (!Array.isArray(r)) return [];
    return r.filter(m => (m.categorie || '').toLowerCase() === 'palette')
            .sort((a, b) => {
              const ea = a.is_europe ? 0 : 1;
              const eb = b.is_europe ? 0 : 1;
              if (ea !== eb) return ea - eb;
              return String(a.reference || '').localeCompare(String(b.reference || ''));
            });
  } catch (e) { return []; }
}

function _renderZ1PalettesBlock(container) {
  if (!container) return;
  container.innerHTML = '';
  const types = (S.pfModal && S.pfModal._paletteTypes) || [];
  const lines = (S.pfModal && S.pfModal.palettesLines) || [];

  const head = el('div', { style: { display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' } },
    el('label', { style: { margin: 0, flex: '1' } }, 'Palettes utilisees'),
    el('button', {
      cls: 'btn btn-ghost',
      type: 'button',
      style: { padding: '4px 10px', fontSize: '12px' },
      on: { click: () => {
        S.pfModal.palettesLines.push({ matiere_id: null, nombre: 1 });
        _renderZ1PalettesBlock(container);
      } },
    }, '+ Ajouter'),
  );
  container.appendChild(head);

  if (!types.length) {
    container.appendChild(el('div', { cls: 'mp-hint' },
      'Aucune palette referencee dans matieres premieres.'));
    return;
  }
  if (!lines.length) {
    container.appendChild(el('div', { cls: 'mp-hint' },
      'Aucune palette. Cliquez sur + Ajouter pour en saisir.'));
    return;
  }

  lines.forEach((line, idx) => {
    const row = el('div', { style: { display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '6px' } });
    const sel = el('select', { style: { flex: '1', padding: '8px', borderRadius: '8px', border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)' } });
    sel.appendChild(el('option', { attrs: { value: '' } }, 'Choisir une palette'));
    types.forEach(t => {
      const opt = el('option', { attrs: { value: String(t.id) } },
        (t.reference || '') + ' ' + (t.designation || '') + (t.is_europe ? ' (EUROPE)' : ''));
      if (line.matiere_id != null && Number(line.matiere_id) === Number(t.id)) opt.selected = true;
      sel.appendChild(opt);
    });
    sel.addEventListener('change', () => {
      const v = sel.value;
      S.pfModal.palettesLines[idx].matiere_id = v ? Number(v) : null;
    });

    const nbInp = el('input', {
      attrs: { type: 'number', min: '1', step: '1', value: String(line.nombre || 1) },
      style: { width: '80px', padding: '8px', borderRadius: '8px', border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)' },
    });
    nbInp.addEventListener('input', () => {
      const v = parseInt(nbInp.value, 10);
      S.pfModal.palettesLines[idx].nombre = Number.isFinite(v) && v > 0 ? v : 1;
    });

    const del = el('button', {
      cls: 'btn btn-ghost',
      type: 'button',
      style: { padding: '4px 10px', fontSize: '12px', color: 'var(--danger)' },
      attrs: { title: 'Supprimer cette palette', 'aria-label': 'Supprimer' },
      on: { click: () => {
        S.pfModal.palettesLines.splice(idx, 1);
        _renderZ1PalettesBlock(container);
      } },
    }, 'X');

    row.appendChild(sel);
    row.appendChild(nbInp);
    row.appendChild(del);
    container.appendChild(row);
  });
}

function _z1IsTermine(d) {
  return !!(d && String(d.statut_reel || '') === 'reellement_termine');
}

function _z1FormatDossierLine(d) {
  if (!d) return '';
  const refLine = (d.ref_produit || '') + (d.description ? ' - ' + d.description : '');
  return refLine;
}

function _z1MakeNoteFromDossier(dossier) {
  if (!dossier || !dossier.no_dossier) return '';
  return 'Production dossier ' + dossier.no_dossier + ' - ' + _fmtDateFRz1(new Date());
}

function _renderZ1DossierBanner(container, ctx) {
  if (!container) return;
  container.innerHTML = '';
  container.style.display = '';

  const dossierSel = (S.pfModal && S.pfModal.dossier) || null;
  const hasSel = !!(dossierSel && dossierSel.no_dossier);
  const canPick = !!ctx && (
    !!ctx.dossier
    || (Array.isArray(ctx.precedents) && ctx.precedents.length > 0)
    || !!ctx.canSearchAll
    || !!S.pfModal._noDossierManual
  );

  // Cas "aucun dossier detecte ET pas selectionne" -> champ libre en direct.
  if (!hasSel && (!ctx || (!ctx.dossier && !(ctx.precedents || []).length && !ctx.canSearchAll))) {
    const inp = el('input', {
      cls: 'field-input',
      attrs: {
        type: 'text',
        placeholder: 'No de dossier (optionnel)',
        autocomplete: 'off',
        value: S.pfModal._noDossierManual || '',
      },
      style: { textTransform: 'uppercase' },
    });
    inp.addEventListener('input', () => {
      inp.value = inp.value.toUpperCase();
      S.pfModal._noDossierManual = inp.value.trim();
    });
    container.appendChild(el('div', { cls: 'mp-field' },
      el('label', null, 'Dossier de production (libre)'),
      inp,
      el('div', { cls: 'mp-hint' },
        'Aucun dossier detecte sur votre profil. Vous pouvez saisir le no manuellement.'),
    ));
    return;
  }

  const termine = _z1IsTermine(dossierSel);
  const bandeauStyle = termine
    ? { background: 'rgba(251,191,36,0.10)', borderColor: 'var(--warn)', color: 'var(--text)' }
    : { background: 'var(--accent-bg)', borderColor: 'var(--accent)', color: 'var(--text)' };

  const label = hasSel
    ? (termine ? 'Dossier selectionne (rattrapage)' : 'Dossier de production en cours')
    : (S.pfModal._noDossierManual
        ? 'Dossier de production (libre)'
        : 'Aucun dossier selectionne');

  const bodyLines = [];
  if (hasSel) {
    const refLine = _z1FormatDossierLine(dossierSel);
    bodyLines.push(el('div', { style: { fontWeight: '700', fontSize: '14px' } },
      (dossierSel.fictif ? '(hors planning) ' : '') + (dossierSel.no_dossier || '')));
    if (dossierSel.client) {
      bodyLines.push(el('div', { style: { fontSize: '12px', color: 'var(--text2)', marginTop: '2px' } },
        'Client : ' + dossierSel.client));
    }
    if (refLine) {
      bodyLines.push(el('div', { style: { fontSize: '12px', color: 'var(--text2)', marginTop: '2px' } },
        'Reference : ' + refLine));
    }
    if (dossierSel.machine_nom) {
      bodyLines.push(el('div', { style: { fontSize: '11px', color: 'var(--muted)', marginTop: '2px' } },
        'Machine : ' + dossierSel.machine_nom));
    }
    if (termine) {
      bodyLines.push(el('div', {
        style: {
          fontSize: '11px',
          color: 'var(--warn)',
          marginTop: '6px',
          fontWeight: '600',
          textTransform: 'uppercase',
          letterSpacing: '.5px',
        },
      }, 'Dossier termine - entree rattrapee'));
    }
  } else if (S.pfModal._noDossierManual) {
    bodyLines.push(el('div', { style: { fontWeight: '700', fontSize: '14px' } },
      String(S.pfModal._noDossierManual).toUpperCase()));
    bodyLines.push(el('div', { style: { fontSize: '11px', color: 'var(--muted)', marginTop: '2px' } },
      'Saisie libre'));
  } else {
    bodyLines.push(el('div', { style: { fontSize: '12px', color: 'var(--muted)' } },
      'Cliquez sur "Choisir un autre dossier" pour en selectionner un.'));
  }

  const pickerLink = canPick
    ? el('button', {
        cls: 'btn btn-ghost',
        type: 'button',
        style: {
          padding: '4px 10px',
          fontSize: '11px',
          color: 'var(--accent)',
          background: 'transparent',
          border: '1px solid var(--border)',
          alignSelf: 'flex-start',
        },
        on: { click: (e) => {
          e.preventDefault();
          _openZ1DossierPicker(container, ctx);
        } },
      }, 'Choisir un autre dossier')
    : null;

  const bandeau = el('div', {
    cls: 'mp-readonly',
    style: bandeauStyle,
  }, ...bodyLines);

  container.appendChild(el('div', { cls: 'mp-field' },
    el('div', {
      style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', marginBottom: '4px' },
    },
      el('label', { style: { margin: 0 } }, label),
      pickerLink,
    ),
    bandeau,
  ));
}

function _z1SetDossier(container, ctx, dossier, manualRef) {
  if (!S.pfModal) return;
  const noteTa = S.pfModal._noteTa || null;
  const prevAuto = S.pfModal._noteAutoLast || '';
  S.pfModal.dossier = dossier || null;
  S.pfModal._noDossierManual = (manualRef || '').trim();
  _renderZ1DossierBanner(container, ctx);

  // Note auto : ne l'ecrase que si vide OU si elle correspond a la note auto precedente.
  if (noteTa) {
    const cur = (noteTa.value || '').trim();
    if (!cur || cur === prevAuto) {
      const newAuto = dossier ? _z1MakeNoteFromDossier(dossier) : '';
      noteTa.value = newAuto;
      S.pfModal._noteAutoLast = newAuto;
    }
  }
}

function _z1DossierRow(dossier, opts) {
  const termine = _z1IsTermine(dossier);
  const badgeText = opts && opts.badge
    ? opts.badge
    : (termine ? 'Termine' : (dossier.statut_reel === 'reellement_en_saisie' ? 'En cours' : ''));
  const badgeStyle = termine
    ? { color: 'var(--warn)', borderColor: 'var(--warn)' }
    : { color: 'var(--accent)', borderColor: 'var(--accent)' };

  const refLine = _z1FormatDossierLine(dossier);
  const cli = dossier.client ? ' - ' + dossier.client : '';

  return el('button', {
    type: 'button',
    cls: 'z1-picker-item',
    style: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: '10px',
      padding: '10px 12px',
      background: 'var(--card)',
      border: '1px solid var(--border)',
      borderRadius: '8px',
      cursor: 'pointer',
      textAlign: 'left',
      color: 'var(--text)',
      width: '100%',
    },
    on: { click: opts && opts.onClick },
  },
    el('div', { style: { flex: '1', minWidth: 0 } },
      el('div', { style: { fontWeight: '700', fontSize: '13px' } },
        (dossier.no_dossier || '') + cli),
      refLine
        ? el('div', {
            style: { fontSize: '11px', color: 'var(--text2)', marginTop: '2px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
          }, refLine)
        : null,
      dossier.machine_nom
        ? el('div', { style: { fontSize: '11px', color: 'var(--muted)', marginTop: '2px' } },
            'Machine : ' + dossier.machine_nom)
        : null,
    ),
    badgeText
      ? el('span', {
          style: Object.assign({
            padding: '2px 8px',
            fontSize: '10px',
            fontWeight: '700',
            textTransform: 'uppercase',
            letterSpacing: '.5px',
            borderRadius: '999px',
            border: '1px solid',
            flex: '0 0 auto',
          }, badgeStyle),
        }, badgeText)
      : null,
  );
}

function _openZ1DossierPicker(bannerContainer, ctx) {
  // Ferme l'eventuel picker precedent.
  const prev = document.getElementById('z1-picker-overlay');
  if (prev) prev.remove();

  const overlay = el('div', {
    attrs: { id: 'z1-picker-overlay' },
    style: {
      position: 'fixed', inset: '0', zIndex: '10001',
      background: 'rgba(0,0,0,0.55)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '20px',
    },
    on: { click: (e) => { if (e.target === overlay) overlay.remove(); } },
  });

  const box = el('div', {
    style: {
      background: 'var(--card)', border: '1px solid var(--border)',
      borderRadius: '12px', width: 'min(520px, 100%)', maxHeight: '80vh',
      display: 'flex', flexDirection: 'column',
      boxShadow: '0 20px 60px rgba(0,0,0,0.45)',
    },
  });

  box.appendChild(el('div', {
    style: {
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '14px 16px', borderBottom: '1px solid var(--border)',
    },
  },
    el('div', { style: { fontWeight: '700', fontSize: '14px' } }, 'Choisir un autre dossier'),
    el('button', {
      cls: 'mp-modal-close', type: 'button',
      attrs: { 'aria-label': 'Fermer' },
      on: { click: () => overlay.remove() },
    }, 'x'),
  ));

  const listWrap = el('div', {
    style: { padding: '14px 16px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' },
  });

  const pick = (dossier) => {
    _z1SetDossier(bannerContainer, ctx, dossier, '');
    overlay.remove();
  };

  // Dossier en cours (accent)
  if (ctx && ctx.dossier) {
    listWrap.appendChild(el('div', {
      style: { fontSize: '11px', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.5px', fontWeight: '600' },
    }, 'Dossier en cours'));
    listWrap.appendChild(_z1DossierRow(ctx.dossier, {
      badge: 'En cours', onClick: () => pick(ctx.dossier),
    }));
  }

  // Precedents (2 max)
  const precedents = (ctx && ctx.precedents) || [];
  if (precedents.length) {
    listWrap.appendChild(el('div', {
      style: { fontSize: '11px', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.5px', fontWeight: '600', marginTop: '4px' },
    }, 'Precedents (' + (ctx.machine ? ctx.machine.nom : 'meme machine') + ')'));
    precedents.forEach(d => {
      listWrap.appendChild(_z1DossierRow(d, { badge: 'Termine', onClick: () => pick(d) }));
    });
  }

  // Saisie libre
  listWrap.appendChild(el('div', {
    style: { fontSize: '11px', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.5px', fontWeight: '600', marginTop: '4px' },
  }, 'Saisie libre'));

  const manualInp = el('input', {
    cls: 'field-input',
    attrs: {
      type: 'text',
      placeholder: 'No de dossier (ex : 12345-01)',
      autocomplete: 'off',
      value: S.pfModal._noDossierManual || '',
    },
    style: { textTransform: 'uppercase', flex: '1' },
  });
  const manualBtn = el('button', {
    cls: 'btn btn-accent', type: 'button',
    style: { padding: '8px 14px', fontSize: '12px' },
    on: { click: () => {
      const v = (manualInp.value || '').trim().toUpperCase();
      if (!v) { manualInp.focus(); return; }
      _z1SetDossier(bannerContainer, ctx, null, v);
      overlay.remove();
    } },
  }, 'Valider');
  listWrap.appendChild(el('div', {
    style: { display: 'flex', gap: '8px', alignItems: 'center' },
  }, manualInp, manualBtn));

  // Recherche globale (chef d'atelier / admin)
  if (ctx && ctx.canSearchAll) {
    listWrap.appendChild(el('div', {
      style: { fontSize: '11px', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.5px', fontWeight: '600', marginTop: '4px' },
    }, 'Recherche libre (toutes machines)'));

    const searchInp = el('input', {
      cls: 'field-input',
      attrs: {
        type: 'text',
        placeholder: 'Reference, client, description...',
        autocomplete: 'off',
      },
    });
    const results = el('div', {
      style: { display: 'flex', flexDirection: 'column', gap: '6px' },
    });
    let searchDebounce = null;
    const runSearch = async () => {
      const q = (searchInp.value || '').trim();
      results.innerHTML = '';
      if (q.length < 2) return;
      try {
        const r = await api('/api/fabrication/dossiers-search?q=' + encodeURIComponent(q));
        const list = (r && r.dossiers) || [];
        if (!list.length) {
          results.appendChild(el('div', { cls: 'mp-hint' }, 'Aucun resultat pour "' + q + '"'));
          return;
        }
        list.forEach(d => results.appendChild(_z1DossierRow(d, { onClick: () => pick(d) })));
      } catch (e) {
        results.appendChild(el('div', { cls: 'mp-hint err' }, 'Erreur de recherche.'));
      }
    };
    searchInp.addEventListener('input', () => {
      clearTimeout(searchDebounce);
      searchDebounce = setTimeout(runSearch, 220);
    });
    listWrap.appendChild(searchInp);
    listWrap.appendChild(results);
    requestAnimationFrame(() => searchInp.focus());
  } else {
    requestAnimationFrame(() => manualInp.focus());
  }

  box.appendChild(listWrap);
  overlay.appendChild(box);
  document.body.appendChild(overlay);
}

async function _initZ1Enrichment(dossierBanner, palettesBlock, noteTa) {
  const [ctx, types] = await Promise.all([_fetchZ1DossierContext(), _fetchPaletteTypes()]);
  if (!S.pfModal) return;
  S.pfModal._z1Ctx = ctx;
  S.pfModal._paletteTypes = types || [];
  S.pfModal._noteTa = noteTa || null;
  // Selection par defaut : dossier actif s'il existe.
  S.pfModal.dossier = ctx.dossier || null;

  _renderZ1DossierBanner(dossierBanner, ctx);
  _renderZ1PalettesBlock(palettesBlock);

  if (ctx.dossier && ctx.dossier.no_dossier && noteTa && !((noteTa.value || '').trim())) {
    const auto = _z1MakeNoteFromDossier(ctx.dossier);
    noteTa.value = auto;
    S.pfModal._noteAutoLast = auto;
  }

  // Pre-remplit la reference produit depuis le dossier actif.
  if (ctx.dossier && ctx.dossier.ref_produit && S.pfModal.refInp
      && !((S.pfModal.refInp.value || '').trim())) {
    const refDossier = String(ctx.dossier.ref_produit).trim();
    S.pfModal.refInp.value = refDossier;
    try {
      const p = await resolvePfProduitByRef(refDossier);
      if (p && S.pfModal && S.pfModal.refInp
          && String(S.pfModal.refInp.value || '').trim().toUpperCase()
              === refDossier.toUpperCase()) {
        renderPfMouvementModal('entree', p, 'Z1');
      }
    } catch (e) {}
  }
}

function renderPfMouvementModal(type, produit, defaultEmpl) {
  const typeMvt = (type || 'entree').toLowerCase();
  if (!['entree', 'sortie'].includes(typeMvt)) return;
  closeMroot();
  const mroot = document.getElementById('mroot');
  if (!mroot) return;
  let prod = produit || null;
  S.pfModal = {
    type: typeMvt,
    produit: prod,
    produitId: prod ? prod.id : null,
    refInp: null,
    defaultEmpl: defaultEmpl || null,
    dossier: null,
    palettesLines: [],
    _paletteTypes: [],
    _noDossierManual: '',
  };
  const _isZ1Entree = typeMvt === 'entree'
    && String(defaultEmpl || '').toUpperCase() === 'Z1';

  const overlay = el('div', {
    cls: 'mp-modal-overlay',
    on: { click: (e) => { if (e.target === overlay) closeMroot(); } },
  });
  const headTypeCls = typeMvt === 'entree' ? 'pf-entree' : 'pf-sortie';
  const box = el('div', { cls: 'mp-modal mp-modal-mvt' });
  box.appendChild(el('div', { cls: 'mp-modal-mvt-head mp-modal-mvt-head-' + headTypeCls },
    el('h3', null, PF_MVT_TITLES[typeMvt] || typeMvt),
    el('button', {
      cls: 'mp-modal-close',
      type: 'button',
      attrs: { title: 'Fermer', 'aria-label': 'Fermer' },
      on: { click: closeMroot },
    }, '×'),
  ));
  const body = el('div', { cls: 'mp-modal-mvt-body' });
  const hintEl = el('div', { cls: 'mp-hint' }, '');
  const errEl = el('div', { cls: 'mp-hint err', style: { display: 'none' } }, '');
  const dossierBanner = el('div', { cls: 'z1-dossier-banner', style: { display: 'none' } });
  if (_isZ1Entree) body.appendChild(dossierBanner);

  if (prod) {
    const unit = (prod.unite || '').trim();
    body.appendChild(el('div', { cls: 'mp-field' },
      el('label', null, 'Produit fini'),
      el('div', { cls: 'mp-readonly' },
        (prod.reference || '') + (prod.designation ? ' — ' + prod.designation : '')
        + (unit ? ' (' + unit + ')' : ''),
      ),
    ));
  } else {
    const refInp = el('input', {
      cls: 'field-input',
      attrs: {
        type: 'text',
        placeholder: 'Référence produit (comme la recherche en haut)…',
        autocomplete: 'off',
      },
      style: { direction: 'ltr' },
    });
    const suggWrap = el('div', { cls: 'empl-suggestions', style: { display: 'none' } });
    S.pfModal.refInp = refInp;
    wireStockProduitSearch(refInp, suggWrap, (p) => {
      renderPfMouvementModal(typeMvt, p, S.pfModal && S.pfModal.defaultEmpl);
    });
    const refCombo = el('div', { cls: 'empl-combo-wrap' }, refInp, suggWrap);
    body.appendChild(el('div', { cls: 'mp-field ref-field-wrap' },
      el('label', null, 'Produit fini'),
      refCombo,
    ));
    requestAnimationFrame(() => refInp.focus());
  }

  const { wrap: emplWrap, emplInp } = buildMpEmplacementField();
  if (defaultEmpl) {
    emplInp.value = String(defaultEmpl).toUpperCase();
  }
  const today = new Date().toISOString().slice(0, 10);
  const dateInp = el('input', { attrs: { type: 'date', value: today } });
  const qInp = el('input', { attrs: { type: 'number', min: '0', step: 'any', inputmode: 'decimal' } });

  let stockEmpl = 0;
  const refreshStockHint = async () => {
    if (typeMvt !== 'sortie' || !S.pfModal.produitId) return;
    const empl = mpEmplacementValue(emplInp);
    if (!empl || !isStockEmplacementCode(empl)) {
      hintEl.textContent = '';
      errEl.style.display = 'none';
      return;
    }
    stockEmpl = await fetchPfStockAtEmpl(S.pfModal.produitId, empl);
    const unit = (S.pfModal.produit?.unite || prod?.unite || '').trim();
    hintEl.textContent = 'Stock à cet emplacement : ' + (unit ? fU(stockEmpl, unit) : fN(stockEmpl));
    checkSortieQte();
  };

  const checkSortieQte = () => {
    if (typeMvt !== 'sortie') return;
    const q = parseFloat(qInp.value);
    if (q > stockEmpl) {
      errEl.style.display = '';
      errEl.textContent = 'Stock insuffisant.';
    } else {
      errEl.style.display = 'none';
    }
  };

  emplInp.addEventListener('input', () => {
    emplInp.value = emplInp.value.toUpperCase();
    refreshStockHint();
  });
  emplInp.addEventListener('change', refreshStockHint);

  if (typeMvt === 'entree') {
    body.appendChild(emplWrap);
    body.appendChild(el('div', { cls: 'mp-field' },
      el('label', null, 'Quantité'),
      qInp,
    ));
    body.appendChild(el('div', { cls: 'mp-field' },
      el('label', null, 'Date du stock'),
      dateInp,
    ));
    S.pfModal.validate = () => {
      if (!S.pfModal.produitId) return 'Produit obligatoire.';
      const emplErr = validateMpEmplacement(mpEmplacementValue(emplInp));
      if (emplErr) return emplErr;
      const q = parseFloat(qInp.value);
      if (!q || q <= 0) return 'Quantité invalide.';
      return null;
    };
    S.pfModal.getBody = () => ({
      produit_id: S.pfModal.produitId,
      emplacement: mpEmplacementValue(emplInp),
      type_mouvement: 'entree',
      quantite: parseFloat(qInp.value),
      date_entree: dateInp.value || today,
      note: null,
    });
  } else {
    qInp.addEventListener('input', checkSortieQte);
    body.appendChild(emplWrap);
    body.appendChild(el('div', { cls: 'mp-field' },
      el('label', null, 'Quantité'),
      qInp,
      hintEl,
      errEl,
    ));
    if (S.pfModal.produitId) refreshStockHint();
    S.pfModal.validate = () => {
      if (!S.pfModal.produitId) return 'Produit obligatoire.';
      const emplErr = validateMpEmplacement(mpEmplacementValue(emplInp));
      if (emplErr) return emplErr;
      const q = parseFloat(qInp.value);
      if (!q || q <= 0) return 'Quantité invalide.';
      if (q > stockEmpl) return 'Stock insuffisant.';
      return null;
    };
    S.pfModal.getBody = () => ({
      produit_id: S.pfModal.produitId,
      emplacement: mpEmplacementValue(emplInp),
      type_mouvement: 'sortie',
      quantite: parseFloat(qInp.value),
      date_entree: today,
      note: null,
    });
  }

  const palettesBlock = el('div', { cls: 'z1-palettes-block' });
  if (_isZ1Entree) {
    body.appendChild(el('div', { cls: 'mp-field' }, palettesBlock));
  }
  const noteTa = el('textarea', { attrs: { placeholder: 'Commentaire (optionnel)' } });
  body.appendChild(el('div', { cls: 'mp-field' }, el('label', null, 'Note'), noteTa));
  const prevGetBody = S.pfModal.getBody;
  S.pfModal.getBody = () => {
    const b = prevGetBody();
    b.note = (noteTa.value || '').trim() || null;
    if (_isZ1Entree) {
      const noDos = (S.pfModal.dossier && S.pfModal.dossier.no_dossier)
        || S.pfModal._noDossierManual
        || null;
      b.no_dossier = noDos ? (String(noDos).trim() || null) : null;
      const cleanPalettes = (S.pfModal.palettesLines || [])
        .filter(l => l && l.matiere_id && Number(l.nombre) > 0)
        .map(l => ({ matiere_id: Number(l.matiere_id), nombre: Number(l.nombre) }));
      if (cleanPalettes.length) b.palettes = cleanPalettes;
    }
    return b;
  };

  const pfBtnCls = typeMvt === 'entree' ? 'btn-pf-entree' : 'btn-pf-sortie';
  body.appendChild(el('div', { cls: 'mp-modal-actions' },
    el('button', { cls: 'btn-cancel', type: 'button', on: { click: closeMroot } }, 'Annuler'),
    el('button', { cls: 'btn ' + pfBtnCls, type: 'button', on: { click: submitPfMouvement } }, 'Valider'),
  ));
  box.appendChild(body);
  overlay.appendChild(box);
  mroot.appendChild(overlay);

  if (_isZ1Entree) {
    requestAnimationFrame(() => {
      _initZ1Enrichment(dossierBanner, palettesBlock, noteTa);
    });
  }
}

async function submitPfMouvement() {
  if (!S.pfModal) return;
  const typeMvt = (S.pfModal.type || 'entree').toLowerCase();
  // Si pas de produit_id mais on a une référence saisie, on tente la résolution.
  // En entrée Z1, on autorise l'auto-création de la référence (unité = étiquette).
  if (!S.pfModal.produitId) {
    const refVal = (S.pfModal.refInp ? S.pfModal.refInp.value : '') || '';
    const refClean = String(refVal).trim().toUpperCase();
    if (!refClean) {
      showToast('Référence obligatoire.', 'error');
      return;
    }
    const p = await resolvePfProduitByRef(refVal);
    if (p) {
      S.pfModal.produitId = p.id;
      S.pfModal.produit = p;
    } else if (typeMvt === 'sortie') {
      showToast('Référence introuvable — sélectionnez un produit dans la liste ou vérifiez la saisie.', 'error');
      return;
    }
    // En entrée : on continuera avec la référence brute → l'endpoint auto-crée le produit.
  }
  // Validation (sauf produitId obligatoire si entrée + auto-create)
  let err = null;
  if (S.pfModal.validate) {
    const origErr = S.pfModal.validate();
    // En entrée auto-create, ignorer l'erreur "Produit obligatoire."
    if (origErr && !(typeMvt === 'entree' && !S.pfModal.produitId && /[Pp]roduit/.test(origErr))) {
      err = origErr;
    }
  }
  if (!err && typeMvt === 'sortie' && S.pfModal.getBody) {
    const b = S.pfModal.getBody();
    const stock = await fetchPfStockAtEmpl(b.produit_id, b.emplacement);
    if (b.quantite > stock) err = 'Stock insuffisant.';
  }
  if (err) { showToast(err, 'error'); return; }
  const body = S.pfModal.getBody();
  // Si entrée sans produit_id : passer par l'endpoint produits-finis/entree qui auto-crée.
  if (typeMvt === 'entree' && !S.pfModal.produitId) {
    const refVal = (S.pfModal.refInp ? S.pfModal.refInp.value : '') || '';
    const payload = {
      reference: String(refVal).trim().toUpperCase(),
      designation: String(refVal).trim().toUpperCase(),
      unite: 'étiquette',
      emplacement: body.emplacement,
      quantite: body.quantite,
      note: body.note,
    };
    try {
      await api('/api/stock/produits-finis/entree', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      showToast('Entrée enregistrée — référence créée.', 'success');
      S.pfModal = null;
      closeMroot();
      if (S.tab === 'production') await loadProduction();
      else if (S.tab === 'produits-finis') await loadProduitsFinis();
      else if (S.tab === 'dashboard') await loadDashboard();
    } catch (e) {
      showToast(e.message || 'Erreur lors de l\'enregistrement.', 'error');
    }
    return;
  }
  await submitMouvement(body);
}

async function loadMpSousSections() {
  // Charge les sous-sections en isolant par catégorie pour éviter tout mélange
  // (les "autre" et les "frontal" ont leurs propres listes).
  try {
    const [autreD, frontalD] = await Promise.all([
      api('/api/stock/matieres/sous-sections?categorie=autre').catch(() => []),
      api('/api/stock/matieres/sous-sections?categorie=frontal').catch(() => []),
    ]);
    S.mpSousSectionsByCat = {
      autre: Array.isArray(autreD) ? autreD : [],
      frontal: Array.isArray(frontalD) ? frontalD : [],
    };
    // Rétrocompat : conserve une liste plate (rare usage en lecture seule éventuelle)
    S.mpSousSections = [
      ...S.mpSousSectionsByCat.autre,
      ...S.mpSousSectionsByCat.frontal,
    ];
  } catch (e) {
    S.mpSousSectionsByCat = { autre: [], frontal: [] };
    S.mpSousSections = [];
  }
}

function mpSousSectionsForCat(cat) {
  const key = mpCategorieKey(cat);
  const byCat = S.mpSousSectionsByCat || {};
  return Array.isArray(byCat[key]) ? byCat[key] : [];
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
  await Promise.all([loadMatieresAdminList(), loadMpSousSections()]);
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

  // Barre filtre — catégorie + recherche libre
  const filterCat = S.matieresAdminFilterCat || 'tout';
  const filterQ = (S.matieresAdminFilterQ || '').trim().toLowerCase();
  const pillBase = 'padding:5px 12px;border-radius:999px;border:1px solid var(--border);background:transparent;color:var(--text2);font-size:11px;font-weight:600;cursor:pointer;transition:all .15s';
  const pillActive = 'padding:5px 12px;border-radius:999px;border:1px solid var(--accent);background:var(--accent-bg);color:var(--accent);font-size:11px;font-weight:700;cursor:pointer';
  const pillsWrap = el('div', { style: 'display:flex;flex-wrap:wrap;gap:6px;padding:10px 14px 4px' });
  const CATS_ORDER = ['tout', 'mandrin', 'frontal', 'glassine', 'palette', 'adhesif', 'carton', 'complexe', 'autre'];
  CATS_ORDER.forEach(c => {
    const isAct = filterCat === c;
    pillsWrap.appendChild(el('button', {
      type: 'button',
      style: isAct ? pillActive : pillBase,
      on: { click: () => { S.matieresAdminFilterCat = c; renderMatieresAdminDrawer(); } },
    }, c === 'tout' ? 'Toutes' : (MP_CAT_LABELS[c] || c)));
  });
  const searchInp = el('input', {
    id: 'mp-admin-search',
    attrs: {
      type: 'search',
      placeholder: 'Rechercher (référence, désignation, sous-section…)',
      autocomplete: 'off',
      spellcheck: 'false',
    },
    style: 'background:var(--bg);border:1px solid var(--border);border-radius:10px;'
      + 'padding:8px 12px;color:var(--text);font-size:13px;font-family:inherit;'
      + 'width:100%;outline:none;transition:border-color .15s',
  });
  searchInp.value = S.matieresAdminFilterQ || '';
  searchInp.addEventListener('input', (e) => {
    S.matieresAdminFilterQ = e.target.value;
    renderMatieresAdminDrawer();
  });
  searchInp.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') { S.matieresAdminFilterQ = ''; renderMatieresAdminDrawer(); }
  });
  pillsWrap.style.padding = '8px 14px 4px';
  drawer.appendChild(pillsWrap);
  drawer.appendChild(el('div', { style: 'padding:0 14px 8px' }, searchInp));

  const body = el('div', { cls: 'mp-drawer-body' });
  const list = (S.matieresAdminList || []).filter(item => {
    if (filterCat !== 'tout' && mpCategorieKey(item.categorie) !== filterCat) return false;
    if (!filterQ) return true;
    const hay = [item.reference, item.designation, item.sous_section, item.couleur]
      .map(x => String(x || '').toLowerCase()).join(' ');
    return hay.includes(filterQ);
  });
  const byCat = {};
  list.forEach(item => {
    const c = item.categorie || 'autre';
    if (!byCat[c]) byCat[c] = [];
    byCat[c].push(item);
  });
  if (!list.length) {
    body.appendChild(el('div', { style: 'padding:30px;text-align:center;color:var(--muted);font-size:13px' },
      filterQ ? ('Aucune référence pour « ' + filterQ + ' ».') : 'Aucune référence dans cette catégorie.'));
  }
  ['mandrin', 'frontal', 'glassine', 'palette', 'adhesif', 'carton', 'complexe', 'autre'].forEach(cat => {
    if (!byCat[cat] || !byCat[cat].length) return;
    body.appendChild(el('div', { style: { fontSize: '11px', fontWeight: '600', color: 'var(--muted)', margin: '12px 0 8px', textTransform: 'uppercase' } },
      MP_CAT_LABELS[cat] || cat));
    if (mpCategorieHasSousSection(cat)) {
      // Regroupement par sous-section (autre + frontal)
      const bySs = {};
      byCat[cat].forEach(item => {
        const ss = (item.sous_section || '').trim() || '— Sans sous-section —';
        if (!bySs[ss]) bySs[ss] = [];
        bySs[ss].push(item);
      });
      Object.keys(bySs).sort((a, b) => a.localeCompare(b, 'fr')).forEach(ss => {
        body.appendChild(el('div', { style: { fontSize: '11px', fontWeight: '600', color: 'var(--text2)', margin: '6px 0 4px 10px' } }, ss));
        bySs[ss].forEach(item => body.appendChild(buildMatieresAdminRow(item)));
      });
    } else {
      byCat[cat].forEach(item => {
        body.appendChild(buildMatieresAdminRow(item));
      });
    }
  });
  drawer.appendChild(body);
  drawer.appendChild(buildMatieresAdminAddForm());
  // Restore focus on search box if it was active before the re-render
  if (document.activeElement && document.activeElement.id === 'mp-admin-search') {
    requestAnimationFrame(() => {
      const inp = document.getElementById('mp-admin-search');
      if (inp) { inp.focus(); inp.setSelectionRange(inp.value.length, inp.value.length); }
    });
  }
  overlay.appendChild(drawer);
  mroot.appendChild(overlay);
  // Si on a une graine d'ajout, faire défiler le footer en vue
  if (S.matieresAdminAddSeed) {
    requestAnimationFrame(() => {
      const foot = drawer.querySelector('.mp-drawer-foot');
      if (foot) foot.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }
}

// Lance "Copier" sur une référence : pré-remplit le formulaire d'ajout
function copyMatiereRefToAddForm(item) {
  if (!item) return;
  S.matieresAdminAddSeed = {
    categorie: item.categorie,
    reference: '',                       // l'utilisateur doit saisir une nouvelle référence
    designation: item.designation || '',
    seuil_alerte: item.seuil_alerte || 0,
    palettes_par_pile: item.palettes_par_pile || null,
    couleur: item.couleur || '',
    sous_section: item.sous_section || '',
    metres_lineaires_par_bobine: item.metres_lineaires_par_bobine || null,
    prix_eur_m2: item.prix_eur_m2 || null,
    stock_par_laize: Array.isArray(item.stock_par_laize) ? item.stock_par_laize.slice() : [],
  };
  S.matieresAdminEditId = null;
  renderMatieresAdminDrawer();
  // Focus sur le champ référence pour saisie immédiate
  requestAnimationFrame(() => {
    const drawer = document.querySelector('.mp-drawer');
    if (!drawer) return;
    const foot = drawer.querySelector('.mp-drawer-foot');
    if (!foot) return;
    const refInp = foot.querySelector('input[type=text]');
    if (refInp) refInp.focus();
  });
  showToast('Référence copiée — saisis la nouvelle référence.', 'info');
}

function buildMatieresAdminRow(item) {
  const row = el('div', { cls: 'mp-admin-row' });
  const actif = item.actif !== 0;
  row.appendChild(el('div', { style: { display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' } },
    dashMpCatBadge(item.categorie),
    el('strong', null, item.reference || ''),
    el('span', { style: { color: 'var(--text2)', fontSize: '13px' } }, item.designation || ''),
    mpIsGlassineCategory(item) && item.couleur
      ? el('span', { style: { fontSize: '12px', color: 'var(--muted)' } }, ' · ' + item.couleur)
      : null,
    (mpCategorieHasSousSection(item.categorie) && item.sous_section)
      ? el('span', { style: 'display:inline-block;padding:2px 8px;border-radius:999px;background:var(--accent-bg);color:var(--accent);font-size:11px;font-weight:600' }, item.sous_section)
      : null,
    el('span', { style: { fontSize: '12px', color: 'var(--muted)' } }, 'Seuil ' + mpStockLine(item.seuil_alerte, item)),
    mpIsPaletteCategory(item) && item.palettes_par_pile > 0
      ? el('span', { style: { fontSize: '12px', color: 'var(--muted)' } },
          ' · ' + fN(item.palettes_par_pile) + ' pal./pile')
      : null,
    el('span', { style: { fontSize: '11px', fontWeight: '600', color: actif ? 'var(--success)' : 'var(--muted)' } },
      actif ? 'Actif' : 'Inactif'),
  ));
  const actions = el('div', { cls: 'mp-admin-actions' });
  if (!S.stockReadOnly && actif) {
    actions.appendChild(el('button', {
      cls: 'mp-act-btn mp-act-entree',
      type: 'button',
      on: { click: (e) => { e.stopPropagation(); openModalMouvement('entree', item); } },
    }, 'Entrée'));
    actions.appendChild(el('button', {
      cls: 'mp-act-btn mp-act-sortie',
      type: 'button',
      on: { click: (e) => { e.stopPropagation(); openModalMouvement('sortie', item); } },
    }, 'Sortie'));
  }
  actions.appendChild(el('button', {
    cls: 'btn-ghost',
    type: 'button',
    on: { click: () => {
      S.matieresAdminEditId = S.matieresAdminEditId === item.id ? null : item.id;
      renderMatieresAdminDrawer();
    } },
  }, S.matieresAdminEditId === item.id ? 'Fermer' : 'Modifier'));
  actions.appendChild(el('button', {
    cls: 'btn-ghost',
    type: 'button',
    title: 'Dupliquer cette référence dans le formulaire d\'ajout',
    on: { click: (e) => { e.stopPropagation(); copyMatiereRefToAddForm(item); } },
  }, 'Copier'));
  actions.appendChild(el('button', {
    cls: 'btn-ghost',
    type: 'button',
    on: { click: () => toggleMatieresActif(item) },
  }, actif ? 'Désactiver' : 'Réactiver'));
  row.appendChild(actions);
  if (S.matieresAdminEditId === item.id) {
    row.appendChild(buildMatieresAdminEditForm(item));
  }
  return row;
}

function buildMatieresAdminEditForm(item) {
  return buildMatiereRefEditForm(item, async () => {
    S.matieresAdminEditId = null;
    await loadMatieresAdminList();
    await loadMatieres();
    renderMatieresAdminDrawer();
  });
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

function buildMpSousSectionSelector(initialValue, categorie) {
  // Selecteur de sous-section, cloisonné par catégorie : 'autre' et 'frontal'
  // ont leurs propres listes, on ne mélange jamais.
  const wrap = el('div', { cls: 'mp-field' });
  const sel = el('select');
  const newInp = el('input', { attrs: { type: 'text', placeholder: 'Nom de la sous-section' } });
  const newWrap = el('div', { style: { display: 'none', marginTop: '6px' } }, newInp);
  // Catégorie courante du selecteur (peut être changée via setCategorie)
  let currentCat = mpCategorieKey(categorie || 'autre');

  function buildOptions(current) {
    sel.innerHTML = '';
    sel.appendChild(el('option', { value: '' }, '— Aucune —'));
    const list = mpSousSectionsForCat(currentCat)
      .slice()
      .sort((a, b) => String(a).localeCompare(String(b), 'fr'));
    // Si la valeur initiale n'est pas dans la liste, on l'ajoute pour l'afficher
    if (current && !list.some(s => String(s).toLowerCase() === String(current).toLowerCase())) {
      list.unshift(current);
    }
    list.forEach(s => {
      sel.appendChild(el('option', { value: s, selected: (s === current ? true : null) }, s));
    });
    sel.appendChild(el('option', { value: '__new__' }, '+ Créer une nouvelle sous-section…'));
  }
  buildOptions(initialValue || '');

  sel.addEventListener('change', () => {
    if (sel.value === '__new__') {
      newWrap.style.display = '';
      requestAnimationFrame(() => newInp.focus());
    } else {
      newWrap.style.display = 'none';
      newInp.value = '';
    }
  });

  wrap.append(
    el('label', null, 'Sous-section'),
    sel,
    newWrap,
  );

  // API publique du composant
  return {
    el: wrap,
    getValue() {
      if (sel.value === '__new__') {
        return (newInp.value || '').trim();
      }
      return (sel.value || '').trim();
    },
    refresh(current) {
      buildOptions(current || '');
      newWrap.style.display = 'none';
      newInp.value = '';
    },
    reset() {
      sel.value = '';
      newWrap.style.display = 'none';
      newInp.value = '';
    },
    setCategorie(cat) {
      const key = mpCategorieKey(cat || 'autre');
      if (key === currentCat) return;
      currentCat = key;
      buildOptions('');
    },
  };
}

function buildMatieresAdminAddForm() {
  const foot = el('div', { cls: 'mp-drawer-foot' });
  foot.appendChild(el('div', { style: { fontSize: '12px', fontWeight: '600', marginBottom: '12px', color: 'var(--text)' } }, 'Ajouter une référence'));
  const catSel = el('select');
  [['mandrin', 'Mandrin'], ['palette', 'Palette'], ['adhesif', 'Adhésif'], ['carton', 'Carton'], ['frontal', 'Frontal'], ['glassine', 'Glassine'], ['complexe', 'Complexe'], ['autre', 'Autre']].forEach(([v, l]) => {
    catSel.appendChild(el('option', { value: v }, l));
  });
  const refInp = el('input', { attrs: { type: 'text', placeholder: '76MM-3P' } });
  const desInp = el('input', { attrs: { type: 'text' } });
  const seuilInp = el('input', { attrs: { type: 'number', min: '0', step: '0.5', value: '0' } });
  const pppWrap = el('div', { cls: 'mp-field' });
  const pppInp = el('input', { attrs: { type: 'number', min: '1', step: '1', placeholder: 'Ex. 24' } });
  const pppLbl = el('label', null, 'Palettes par pile');
  const couleurWrap = el('div', { cls: 'mp-field' });
  const couleurInp = el('input', { attrs: { type: 'text', placeholder: 'Ex. Blanc, Kraft…' } });
  const couleurLbl = el('label', null, 'Couleur');
  const uppWrap = el('div', { cls: 'mp-field' });
  const uppInp = el('input', { attrs: { type: 'number', min: '1', step: '1', placeholder: 'Ex. 260' } });
  const uppLbl = el('label', null, 'Unités par palette');
  const seuilLbl = el('label', null, 'Seuil d\'alerte (0 = pas d\'alerte)');
  const hintEl = el('div', { cls: 'mp-hint' }, '');
  const errEl = el('div', { cls: 'mp-admin-err' }, S.matieresAdminAddError || '');
  // Champs spécifiques aux catégories laizées (frontal, glassine, complexe)
  const laizeWrap = el('div', { style: 'display:none;border-top:1px dashed var(--border);padding-top:10px;margin-top:6px' });
  const metresInp = el('input', { attrs: { type: 'number', min: '0', step: '1', placeholder: 'Ex. 5000' } });
  const prixM2Inp = el('input', { attrs: { type: 'number', min: '0', step: '0.0001', placeholder: 'Ex. 0,0550' } });
  const laizeChecks = el('div', { cls: 'mp-laize-grid',
    style: 'display:flex;flex-wrap:wrap;gap:6px;margin-top:6px' });
  function rebuildLaizeChecks() {
    laizeChecks.innerHTML = '';
    (S.laizes || []).filter(l => l.actif).forEach(l => {
      const id = 'addmat-laize-' + l.id;
      const inp = el('input', { type: 'checkbox', id: id, value: String(l.id) });
      const lbl = el('label', {
        'for': id,
        style: 'display:inline-flex;align-items:center;gap:6px;padding:5px 10px;border:1px solid var(--border);border-radius:6px;cursor:pointer;font-size:12px;font-weight:600;background:var(--bg);color:var(--text);user-select:none;transition:border-color .15s,background .15s;line-height:1' },
        inp,
        el('span', null, l.label),
      );
      // Effet visuel sur sélection
      inp.addEventListener('change', () => {
        lbl.style.borderColor = inp.checked ? 'var(--accent)' : 'var(--border)';
        lbl.style.background = inp.checked ? 'var(--accent-bg)' : 'var(--bg)';
      });
      laizeChecks.appendChild(lbl);
    });
  }
  rebuildLaizeChecks();
  laizeWrap.append(
    el('div', { cls: 'mp-field' }, el('label', null, 'Mètres linéaires par bobine'), metresInp),
    el('div', { cls: 'mp-field' }, el('label', null, 'Prix au m² (€)'), prixM2Inp),
    el('div', { cls: 'mp-field' },
      el('label', null, 'Laizes disponibles'),
      laizeChecks,
    ),
  );
  // Sous-section (visible pour "autre" et "frontal") — cloisonnée par catégorie
  const seed = S.matieresAdminAddSeed || null;
  const initialCat = (seed && seed.categorie) || catSel.value || 'mandrin';
  const sousSectionSel = buildMpSousSectionSelector((seed && seed.sous_section) || '', initialCat);
  const sousSectionWrap = el('div', { style: { display: 'none' } }, sousSectionSel.el);
  function syncAdminAddFields() {
    const cat = catSel.value;
    const isPal = cat === 'palette';
    const isCarton = cat === 'carton';
    const isGlass = cat === 'glassine';
    const hasSousSection = mpCategorieHasSousSection(cat);
    const isLaizee = mpIsLaizeeCategory(cat);
    const hasCond = mpHasConditionnement(cat);
    pppWrap.style.display = isPal ? '' : 'none';
    couleurWrap.style.display = isGlass ? '' : 'none';
    uppWrap.style.display = hasCond ? '' : 'none';
    laizeWrap.style.display = isLaizee ? '' : 'none';
    sousSectionWrap.style.display = hasSousSection ? '' : 'none';
    pppLbl.textContent = 'Palettes par pile';
    if (hasCond) {
      const u = mpUniteAchat(cat);
      uppLbl.textContent = u.charAt(0).toUpperCase() + u.slice(1) + ' par palette';
    }
    seuilLbl.textContent = mpSeuilFieldLabel(cat);
    seuilInp.step = isPal || isCarton || cat === 'mandrin' || mpIsBobineCategory(cat) ? '1' : '0.5';
    hintEl.textContent = mpAdminHint(cat);
    // Bascule la liste de sous-sections vers la bonne catégorie (jamais de mélange)
    if (hasSousSection && sousSectionSel) sousSectionSel.setCategorie(cat);
  }
  catSel.addEventListener('change', syncAdminAddFields);
  pppWrap.append(pppLbl, pppInp);
  couleurWrap.append(couleurLbl, couleurInp);
  uppWrap.append(uppLbl, uppInp);
  // Pré-remplissage si l'utilisateur a cliqué "Copier" sur une référence
  if (seed) {
    catSel.value = seed.categorie || catSel.value;
    refInp.value = seed.reference || '';
    desInp.value = seed.designation || '';
    seuilInp.value = String(seed.seuil_alerte != null ? seed.seuil_alerte : 0);
    if (seed.palettes_par_pile) pppInp.value = String(seed.palettes_par_pile);
    if (seed.couleur) couleurInp.value = seed.couleur;
    if (seed.metres_lineaires_par_bobine) metresInp.value = String(seed.metres_lineaires_par_bobine);
    if (seed.prix_eur_m2) prixM2Inp.value = String(seed.prix_eur_m2);
    if (seed.unites_par_palette) uppInp.value = String(seed.unites_par_palette);
    if (Array.isArray(seed.stock_par_laize)) {
      const seedLaizeIds = new Set(seed.stock_par_laize.map(s => s.laize_id));
      laizeChecks.querySelectorAll('input[type=checkbox]').forEach(inp => {
        const lid = parseInt(inp.value, 10);
        if (seedLaizeIds.has(lid)) {
          inp.checked = true;
          const lbl = inp.parentElement;
          if (lbl) { lbl.style.borderColor = 'var(--accent)'; lbl.style.background = 'var(--accent-bg)'; }
        }
      });
    }
    // Consomme la graine après usage
    S.matieresAdminAddSeed = null;
  }
  syncAdminAddFields();
  foot.append(
    el('div', { cls: 'mp-field' }, el('label', null, 'Catégorie'), catSel),
    el('div', { cls: 'mp-field' }, el('label', null, 'Référence'), refInp),
    el('div', { cls: 'mp-field' }, el('label', null, 'Désignation'), desInp),
    couleurWrap,
    pppWrap,
    uppWrap,
    sousSectionWrap,
    el('div', { cls: 'mp-field' }, seuilLbl, seuilInp),
    laizeWrap,
    hintEl,
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
        const cat = catSel.value;
        if (!ref || !des) {
          S.matieresAdminAddError = 'Référence et désignation obligatoires.';
          errEl.textContent = S.matieresAdminAddError;
          return;
        }
        if (cat === 'palette') {
          const ppp = parseFloat(pppInp.value);
          if (!ppp || ppp <= 0) {
            S.matieresAdminAddError = 'Palettes par pile obligatoire (valeur positive).';
            errEl.textContent = S.matieresAdminAddError;
            return;
          }
        }
        try {
          const payload = {
            categorie: cat,
            reference: ref,
            designation: des,
            seuil_alerte: parseFloat(seuilInp.value) || 0,
          };
          if (cat === 'palette') {
            payload.palettes_par_pile = parseFloat(pppInp.value);
          }
          if (cat === 'glassine') {
            payload.couleur = couleurInp.value.trim() || des;
          }
          if (mpHasConditionnement(cat)) {
            const raw = (uppInp.value || '').replace(',', '.').trim();
            if (raw !== '') {
              const upp = parseFloat(raw);
              if (!isNaN(upp) && upp > 0) {
                payload.unites_par_palette = upp;
              }
            }
          }
          if (mpCategorieHasSousSection(cat)) {
            const ss = sousSectionSel.getValue();
            if (ss) payload.sous_section = ss;
          }
          const created = await api('/api/stock/matieres', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          });
          // Si matière laizée : envoyer laizes + métrage + prix m² sur l'endpoint dédié
          if (mpIsLaizeeCategory(cat) && created && created.id) {
            const selectedLaizeIds = Array.from(laizeChecks.querySelectorAll('input[type=checkbox]:checked'))
              .map(i => parseInt(i.value, 10)).filter(x => x > 0);
            const metres = parseFloat((metresInp.value || '').replace(',', '.')) || 0;
            const prix = parseFloat((prixM2Inp.value || '').replace(',', '.')) || 0;
            if (selectedLaizeIds.length > 0 || metres > 0 || prix > 0) {
              try {
                await api('/api/stock/matieres/' + created.id + '/laizes', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    laize_ids: selectedLaizeIds,
                    metres_lineaires_par_bobine: metres,
                    prix_eur_m2: prix,
                  }),
                });
              } catch (e) {
                showToast('Référence créée mais erreur sur les laizes : ' + e.message, 'danger');
              }
            }
            await loadMatieresIncompleteCount();
          }
          showToast('Référence ajoutée.', 'success');
          refInp.value = '';
          desInp.value = '';
          pppInp.value = '';
          couleurInp.value = '';
          seuilInp.value = '0';
          metresInp.value = '';
          prixM2Inp.value = '';
          laizeChecks.querySelectorAll('input[type=checkbox]').forEach(i => { i.checked = false; });
          if (mpCategorieHasSousSection(cat) && payload.sous_section) {
            // Rafraichit la liste pour que la nouvelle sous-section soit selectionnable
            await loadMpSousSections();
          }
          sousSectionSel.reset();
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
window._stockOpenModalPfMouvement = openModalPfMouvement;

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

// ── Plan entrepôt ──────────────────────────────────────────────────
async function loadPlanEntrepot() {
  S.planEntrepot = null;
  S.planEntrepotInv = {};
  buildPlanEntrepot();
  try {
    const [rPlan, rInv] = await Promise.all([
      fetch('/api/stock/emplacements-plan', { credentials: 'include' }),
      fetch('/api/stock/inventaire-v2/emplacements', { credentials: 'include' }),
    ]);
    S.planEntrepot = rPlan.ok ? await rPlan.json() : [];
    if (rInv.ok) {
      const invList = await rInv.json();
      const map = {};
      (invList || []).forEach(e => { if (e && e.emplacement) map[e.emplacement] = e; });
      S.planEntrepotInv = map;
    }
  } catch(e) { S.planEntrepot = S.planEntrepot || []; }
  buildPlanEntrepot();
}

// Tooltip global pour le Plan entrepôt (attaché au body, position fixed, hors scroll-area)
function getPlanPillTipEl() {
  let t = document.getElementById('plan-pill-tip');
  if (!t) {
    t = document.createElement('div');
    t.id = 'plan-pill-tip';
    t.className = 'plan-pill-tip';
    document.body.appendChild(t);
  }
  return t;
}
function showPlanPillTip(pill, html) {
  const t = getPlanPillTipEl();
  t.innerHTML = html;
  // Préparer pour mesure (visible mais transparent)
  t.style.left = '0px'; t.style.top = '0px';
  t.classList.add('show');
  const r = pill.getBoundingClientRect();
  const tw = t.offsetWidth, th = t.offsetHeight;
  const vw = window.innerWidth, vh = window.innerHeight;
  const margin = 8;
  // Position horizontale : centrée sur la pastille, clampée dans la viewport
  let left = r.left + r.width / 2 - tw / 2;
  if (left < margin) left = margin;
  if (left + tw > vw - margin) left = vw - margin - tw;
  // Position verticale : au-dessus de la pastille, sinon au-dessous
  let top = r.top - th - 10;
  if (top < margin) top = r.bottom + 10;
  if (top + th > vh - margin) top = Math.max(margin, vh - margin - th);
  t.style.left = left + 'px';
  t.style.top = top + 'px';
}
function hidePlanPillTip() {
  const t = document.getElementById('plan-pill-tip');
  if (t) t.classList.remove('show');
}

function buildPlanEntrepot() {
  hidePlanPillTip();
  const area = document.getElementById('scroll-area');
  if (!area) return;
  area.innerHTML = '';

  const codes = S.planEntrepot; // null = loading, [] = empty, [...] = data
  const canAdd = S.user && ['superadmin','direction','administration'].includes(S.user.role);

  const wrap = document.createElement('div');
  wrap.style.cssText = 'padding:20px;max-width:1200px';

  // Header
  const hd = document.createElement('div');
  hd.style.cssText = 'display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:20px';
  hd.innerHTML = '<div><div style="font-size:20px;font-weight:800;color:var(--text);margin-bottom:4px">Plan entrepôt</div>'
    + '<div style="font-size:13px;color:var(--muted)">Référentiel des emplacements magasin'
    + (codes ? ' · <span style="color:var(--accent);font-weight:700">' + codes.length + ' emplacement' + (codes.length>1?'s':'') + '</span>' : '')
    + '</div>'
    + '<div class="plan-legend">'
    +   '<span class="plan-legend-item plan-pill-c-vert"><span class="plan-pill-dot"></span>&lt; 15 j</span>'
    +   '<span class="plan-legend-item plan-pill-c-jaune"><span class="plan-pill-dot"></span>15–30 j</span>'
    +   '<span class="plan-legend-item plan-pill-c-orange"><span class="plan-pill-dot"></span>30–60 j</span>'
    +   '<span class="plan-legend-item plan-pill-c-rouge"><span class="plan-pill-dot"></span>&gt; 60 j / Jamais</span>'
    + '</div>'
    + '</div>';

  if (canAdd) {
    const form = document.createElement('form');
    form.style.cssText = 'display:flex;gap:6px;align-items:center;flex-shrink:0';
    form.innerHTML = '<input id="plan-new-code" type="text" placeholder="Nouveau code (ex. A141)" maxlength="20" autocomplete="off"'
      + ' style="width:180px;padding:9px 12px;border-radius:10px;border:1.5px solid var(--border);background:var(--bg);color:var(--text);font-size:13px;font-family:ui-monospace,monospace;outline:none;text-transform:uppercase">'
      + '<button type="submit" class="btn" style="padding:9px 16px;font-size:13px;color:var(--bg)">Ajouter</button>';
    form.addEventListener('submit', async e => {
      e.preventDefault();
      const inp = document.getElementById('plan-new-code');
      const code = (inp?.value || '').trim().toUpperCase();
      if (!code) return;
      const r = await fetch('/api/stock/emplacements-plan', {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code }),
      });
      if (r.status === 409) { showToast('Emplacement ' + code + ' déjà existant.', 'danger'); return; }
      if (!r.ok) { showToast('Erreur lors de l\'ajout.', 'danger'); return; }
      inp.value = '';
      showToast('Emplacement ' + code + ' ajouté.', 'success');
      loadPlanEntrepot();
    });
    hd.appendChild(form);
  }
  wrap.appendChild(hd);

  if (!codes) {
    const spin = document.createElement('div');
    spin.style.cssText = 'color:var(--muted);font-size:13px;padding:20px 0';
    spin.textContent = 'Chargement…';
    wrap.appendChild(spin);
    area.appendChild(wrap);
    return;
  }
  if (!codes.length) {
    const empty = document.createElement('div');
    empty.style.cssText = 'color:var(--muted);font-size:13px;padding:20px 0';
    empty.textContent = 'Aucun emplacement dans le référentiel.';
    wrap.appendChild(empty);
    area.appendChild(wrap);
    return;
  }

  // Grouper allée / rangée (2 premiers chiffres)
  const byAllee = {};
  codes.forEach(code => {
    const m = code.match(/^([A-Z]+)(\d{1,2})/i);
    const allee = m ? m[1].toUpperCase() : code[0].toUpperCase();
    const rangee = m ? m[2].padStart(2,'0') : '??';
    if (!byAllee[allee]) byAllee[allee] = {};
    if (!byAllee[allee][rangee]) byAllee[allee][rangee] = [];
    byAllee[allee][rangee].push(code);
  });

  const grid = document.createElement('div');
  grid.style.cssText = 'display:flex;flex-wrap:wrap;gap:20px;align-items:flex-start';

  Object.keys(byAllee).sort().forEach(allee => {
    const card = document.createElement('div');
    card.className = 'plan-allee';

    const hdr = document.createElement('div');
    hdr.className = 'plan-allee-hd';
    hdr.innerHTML = '<span class="plan-allee-letter">' + escHtml(allee) + '</span>'
      + '<span class="plan-allee-label">Allée ' + escHtml(allee) + '</span>';
    card.appendChild(hdr);

    const body = document.createElement('div');
    body.className = 'plan-allee-body';

    Object.keys(byAllee[allee]).sort().forEach(rangee => {
      const row = document.createElement('div');
      row.className = 'plan-rangee';
      byAllee[allee][rangee].slice().sort().forEach(code => {
        const inv = (S.planEntrepotInv || {})[code];
        const couleur = inv ? (inv.couleur || 'rouge') : 'rouge';
        const j = inv ? inv.jours_depuis : null;
        const nbRefs = inv ? (inv.nb_refs || 0) : 0;
        const totalQte = inv ? (inv.total_qte || 0) : 0;
        const dDate = inv ? inv.derniere_date : null;
        const op = inv ? (inv.dernier_operateur || '') : '';

        const pill = document.createElement('button');
        pill.type = 'button';
        pill.className = 'plan-pill plan-pill-c-' + couleur;
        pill.style.cursor = 'pointer';
        pill.addEventListener('click', () => loadEmplacement(code));

        const dot = document.createElement('span');
        dot.className = 'plan-pill-dot';
        pill.appendChild(dot);
        const lbl = document.createElement('span');
        lbl.className = 'plan-pill-code';
        lbl.textContent = code;
        pill.appendChild(lbl);

        // Hover : tooltip global positionné en JS (évite le clipping du scroll-area)
        const joursTxt = (j == null)
          ? 'Jamais inventorié'
          : (j + ' j depuis le dernier inventaire');
        const dateTxt = dDate ? ('le ' + fD(dDate) + (op ? ' · ' + op : '')) : '';
        const refsTxt = nbRefs + ' réf' + (nbRefs > 1 ? 's' : '')
          + ' · ' + fN(totalQte) + ' u.';
        const tipHTML =
          '<div class="plan-pill-tip-code">' + escHtml(code) + '</div>'
          + '<div class="plan-pill-tip-row plan-pill-tip-jours plan-pill-c-' + couleur + '">'
          +   '<span class="plan-pill-dot"></span>' + escHtml(joursTxt)
          + '</div>'
          + (dateTxt ? '<div class="plan-pill-tip-row plan-pill-tip-sub">' + escHtml(dateTxt) + '</div>' : '')
          + '<div class="plan-pill-tip-row plan-pill-tip-refs">' + escHtml(refsTxt) + '</div>';

        pill.addEventListener('mouseenter', () => showPlanPillTip(pill, tipHTML));
        pill.addEventListener('mouseleave', hidePlanPillTip);
        pill.addEventListener('focus', () => showPlanPillTip(pill, tipHTML));
        pill.addEventListener('blur', hidePlanPillTip);

        row.appendChild(pill);
      });
      body.appendChild(row);
    });
    card.appendChild(body);
    grid.appendChild(card);
  });

  wrap.appendChild(grid);
  area.appendChild(wrap);
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
  [['', 'Tout'], ['mandrin', 'Mandrins'], ['frontal', 'Frontaux'], ['glassine', 'Glassines'],
    ['palette', 'Palettes'], ['adhesif', 'Adhésifs'], ['carton', 'Cartons']].forEach(([v, l]) => {
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
    el('td', { cls: 'hist-col-optional' },
      el('span', { cls: 'hist-solde-avant' }, avant),
      el('span', { cls: 'hist-solde-arrow' }, '→'),
      el('span', { cls: 'hist-solde-apres' }, apres),
    ),
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
    el('dt', null, 'Solde'),
    el('dd', null,
      el('span', { cls: 'hist-solde-avant' }, avant),
      el('span', { cls: 'hist-solde-arrow' }, '→'),
      el('span', { cls: 'hist-solde-apres' }, apres),
    ),
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
      el('button', { cls: 'hist-export-btn', type: 'button', on: { click: exportHistoriqueCSV } },
        iconEl('download', 16), ' Export CSV'),
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
    el('th', { cls: 'hist-col-optional' }, 'Solde (avant → après)'),
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

function dashMpCatBadge(categorie, sousSection) {
  const c = (categorie || '').toLowerCase();
  const lbl = MP_CAT_LABELS[c] || categorie || '—';
  let extra = '';
  if (c === 'frontal' && sousSection) {
    const k = String(sousSection).toLowerCase()
      .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9]+/g, '');
    if (k) extra = ' dash-mp-cat-frontal-' + k;
  }
  return el('span', { cls: 'dash-mp-cat dash-mp-cat-' + c + extra }, lbl);
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

async function openStockSortieProdQuick() {
  const mroot = document.getElementById('mroot');
  if (!mroot) return;
  closeMroot();
  const overlay = el('div', {
    cls: 'modal-overlay',
    on: { click: (e) => { if (e.target === overlay) closeMroot(); } },
  });
  const sheet = el('div', { cls: 'modal-sheet', style: { maxWidth: '560px' }, on: { click: (e) => e.stopPropagation() } });
  sheet.appendChild(el('div', { cls: 'modal-title' }, 'En attente - sortie de prod'));
  sheet.appendChild(el('div', { cls: 'modal-sub' }, 'Chargement…'));
  overlay.appendChild(sheet);
  mroot.appendChild(overlay);
  try {
    const d = await api('/api/stock/sortie-prod');
    renderStockSortieProdModalContent(sheet, d);
  } catch (e) {
    sheet.innerHTML = '';
    sheet.appendChild(el('div', { cls: 'modal-title' }, 'En attente - sortie de prod'));
    sheet.appendChild(el('div', { cls: 'mp-hint err' }, e.message || 'Erreur de chargement.'));
    sheet.appendChild(el('button', {
      cls: 'btn-cancel', type: 'button', style: { marginTop: '14px', width: '100%' },
      on: { click: closeMroot },
    }, 'Fermer'));
  }
}

function renderStockSortieProdModalContent(sheet, data) {
  sheet.innerHTML = '';
  const refs = data?.refs || [];
  const label = data?.label || STOCK_EMPL_SORTIE_PROD_LABEL;
  sheet.appendChild(el('div', { cls: 'modal-title' }, 'En attente - sortie de prod'));
  sheet.appendChild(el('div', { cls: 'modal-sub' },
    'Références en zone « ' + label + ' » — sorties de production, en attente de rangement.',
  ));
  if (!refs.length) {
    sheet.appendChild(el('div', { cls: 'card-empty', style: { padding: '24px 8px' } },
      'Aucun produit en zone sortie de prod pour le moment.',
    ));
  } else {
    const list = el('div', { cls: 'a-exp-list' });
    refs.forEach(r => {
      list.appendChild(el('div', {
        cls: 'a-exp-row',
        on: { click: () => { closeMroot(); loadProduit(r.id); } },
      },
        el('div', null,
          el('div', { cls: 'a-exp-ref' }, r.reference || '—'),
          el('div', { cls: 'a-exp-des' }, r.designation || ''),
        ),
        el('div', { cls: 'a-exp-qte' }, fU(r.quantite, r.unite || '')),
      ));
    });
    sheet.appendChild(list);
    sheet.appendChild(el('div', {
      style: { fontSize: '12px', color: 'var(--muted)', marginTop: '10px' },
    }, refs.length + ' référence' + (refs.length > 1 ? 's' : '') + ' · ' + fN(data.total_unites || 0) + ' u.'));
  }
  const actions = el('div', { cls: 'modal-actions', style: { marginTop: '16px' } });
  actions.appendChild(el('button', { cls: 'btn-cancel', type: 'button', on: { click: closeMroot } }, 'Fermer'));
  if (refs.length) {
    actions.appendChild(el('button', {
      cls: 'btn btn-accent', type: 'button',
      on: { click: () => { closeMroot(); loadEmplacement(data?.emplacement || STOCK_EMPL_SORTIE_PROD); } },
    }, 'Voir zone ' + label));
  }
  sheet.appendChild(actions);
}

// ── Vue Production (fabrication) ─────────────────
// 4 boutons d'action rapide + liste du contenu Z1 (sortie de prod)

async function loadProduction() {
  S.productionLoading = true;
  renderContent();
  try {
    const tasks = [api('/api/stock/sortie-prod')];
    if (!S.matieres) tasks.push(api('/api/stock/matieres'));
    const res = await Promise.all(tasks);
    S.productionZ1 = res[0] || { refs: [], total_unites: 0, nb_refs: 0 };
    if (!S.matieres && res[1]) {
      S.matieres = Array.isArray(res[1]) ? res[1] : [];
    }
  } catch (e) {
    S.productionZ1 = { refs: [], total_unites: 0, nb_refs: 0, _err: e.message || 'Erreur de chargement.' };
  }
  S.productionLoading = false;
  renderContent();
}

function fmtDateOpProd(iso) {
  if (!iso) return '—';
  const s = String(iso);
  const d = s.slice(0, 10).split('-');
  const hm = s.length >= 16 ? s.slice(11, 16) : '';
  if (d.length === 3) return d[2] + '/' + d[1] + (hm ? ' ' + hm : '');
  return s;
}

function buildProductionActionCard(opts) {
  const card = el('button', {
    cls: 'prod-action-card prod-action-' + opts.kind,
    type: 'button',
    on: { click: opts.onClick },
  });
  const ico = document.createElement('div');
  ico.className = 'prod-action-ico';
  ico.appendChild(iconEl(opts.icon, 22));
  const txt = el('div', { cls: 'prod-action-txt' },
    el('div', { cls: 'prod-action-title' }, opts.title),
    el('div', { cls: 'prod-action-sub' }, opts.sub),
  );
  card.appendChild(ico);
  card.appendChild(txt);
  return card;
}

function buildProductionView() {
  const wrap = el('div', { cls: 'content prod-view' });

  wrap.appendChild(el('div', { cls: 'prod-head' },
    el('h2', { cls: 'prod-head-title' }, 'Production'),
    el('div', { cls: 'prod-head-sub' },
      'Saisie rapide des entrées/sorties matières premières et sortie de production (Z1).'
    ),
  ));

  const grid = el('div', { cls: 'prod-action-grid' });
  grid.appendChild(buildProductionActionCard({
    kind: 'mp-in', icon: 'log-in', title: 'Entrée MP', sub: 'Réception matière',
    onClick: () => openModalMouvement('entree'),
  }));
  grid.appendChild(buildProductionActionCard({
    kind: 'mp-out', icon: 'log-out', title: 'Sortie MP', sub: 'Consommation production',
    onClick: () => openModalMouvement('sortie'),
  }));
  grid.appendChild(buildProductionActionCard({
    kind: 'z1-in', icon: 'plus-circle', title: 'Entrée Z1', sub: 'Sortie de production',
    onClick: () => renderPfMouvementModal('entree', null, STOCK_EMPL_SORTIE_PROD),
  }));
  grid.appendChild(buildProductionActionCard({
    kind: 'z1-out', icon: 'edit', title: 'Sortie Z1', sub: 'Corriger / retirer',
    onClick: () => renderPfMouvementModal('sortie', null, STOCK_EMPL_SORTIE_PROD),
  }));
  wrap.appendChild(grid);

  const z1 = S.productionZ1 || { refs: [], total_unites: 0, nb_refs: 0 };
  const card = el('div', { cls: 'card prod-z1-card' });
  const cardHead = el('div', { cls: 'prod-z1-head' },
    el('div', null,
      el('div', { cls: 'card-title prod-z1-title' },
        iconEl('package', 16),
        ' Contenu Z1 — En attente sortie de prod',
      ),
      el('div', { cls: 'prod-z1-sub' },
        z1.nb_refs ? (
          z1.nb_refs + ' référence' + (z1.nb_refs > 1 ? 's' : '')
          + ' · ' + fN(z1.total_unites || 0) + ' unité' + ((z1.total_unites||0) > 1 ? 's' : '')
        ) : 'Aucun produit en Z1.'
      ),
    ),
    el('button', {
      cls: 'prod-z1-refresh',
      type: 'button',
      attrs: { title: 'Rafraîchir', 'aria-label': 'Rafraîchir' },
      on: { click: () => loadProduction() },
    }, iconEl('refresh-ccw', 14), ' Actualiser'),
  );
  card.appendChild(cardHead);

  if (S.productionLoading) {
    card.appendChild(el('div', { cls: 'card-empty' }, 'Chargement…'));
  } else if (z1._err) {
    card.appendChild(el('div', { cls: 'mp-hint err' }, z1._err));
  } else if (!z1.refs || !z1.refs.length) {
    card.appendChild(el('div', { cls: 'card-empty prod-z1-empty' },
      el('div', { style: { fontSize: '24px', color: 'var(--muted)', marginBottom: '4px' } }, '·'),
      el('div', null, 'Aucune sortie de production enregistrée.'),
      el('div', { cls: 'prod-z1-empty-hint' },
        'Cliquez sur « Entrée Z1 » pour ajouter ce qui sort de production.'
      ),
    ));
  } else {
    const list = el('div', { cls: 'prod-z1-list' });
    const currentName = String((S.user && S.user.nom) || '').trim().toLowerCase();
    z1.refs.forEach(r => {
      const row = el('div', { cls: 'prod-z1-row' });
      const left = el('div', { cls: 'prod-z1-left' },
        el('div', { cls: 'prod-z1-ref' }, r.reference || '—'),
        el('div', { cls: 'prod-z1-des' }, r.designation || ''),
        el('div', { cls: 'prod-z1-meta' },
          el('span', { cls: 'prod-z1-meta-date' },
            iconEl('clock', 11),
            ' ' + fmtDateOpProd(r.derniere_entree || r.date_fifo),
          ),
          el('span', { cls: 'prod-z1-meta-op' },
            iconEl('users', 11),
            ' ' + (r.dernier_operateur || '—'),
          ),
        ),
      );
      const right = el('div', { cls: 'prod-z1-right' });
      right.appendChild(el('div', { cls: 'prod-z1-qty' }, fU(r.quantite || 0, r.unite || '')));
      // Actions : visibles uniquement si l'opérateur de la dernière entrée = utilisateur courant
      const lineOp = String(r.dernier_operateur || '').trim().toLowerCase();
      if (currentName && lineOp && currentName === lineOp) {
        const actions = el('div', { cls: 'prod-z1-actions' });
        actions.appendChild(el('button', {
          cls: 'prod-z1-btn prod-z1-btn-add',
          type: 'button',
          attrs: { title: 'Ajouter une quantité à cette référence' },
          on: { click: (ev) => { ev.stopPropagation(); openProductionAddTo(r); } },
        }, iconEl('plus-circle', 12), ' Ajouter'));
        actions.appendChild(el('button', {
          cls: 'prod-z1-btn prod-z1-btn-edit',
          type: 'button',
          attrs: { title: 'Modifier la quantité totale en Z1' },
          on: { click: (ev) => { ev.stopPropagation(); openProductionEdit(r); } },
        }, iconEl('edit', 12), ' Modifier'));
        right.appendChild(actions);
      }
      row.appendChild(left);
      row.appendChild(right);
      list.appendChild(row);
    });
    card.appendChild(list);
  }

  wrap.appendChild(card);
  return wrap;
}


// ── Production : actions sur lignes Z1 (Ajouter / Modifier) ──────────
function openProductionAddTo(r) {
  // Ouvre la modale Entrée Z1 pré-remplie avec ce produit
  const prod = {
    id: r.id,
    reference: r.reference,
    designation: r.designation,
    unite: r.unite,
  };
  renderPfMouvementModal('entree', prod, STOCK_EMPL_SORTIE_PROD);
}

function openProductionEdit(r) {
  // Modale simple : nouvelle quantité totale en Z1 (via type=inventaire)
  closeMroot();
  const mroot = document.getElementById('mroot');
  if (!mroot) return;
  const overlay = el('div', {
    cls: 'mp-modal-overlay',
    on: { click: (e) => { if (e.target === overlay) closeMroot(); } },
  });
  const box = el('div', { cls: 'mp-modal mp-modal-mvt' });
  box.appendChild(el('div', { cls: 'mp-modal-mvt-head mp-modal-mvt-head-ajustement' },
    el('h3', null, 'Modifier la quantité — Z1'),
    el('button', {
      cls: 'mp-modal-close', type: 'button',
      attrs: { title: 'Fermer', 'aria-label': 'Fermer' },
      on: { click: closeMroot },
    }, '×'),
  ));
  const body = el('div', { cls: 'mp-modal-mvt-body' });
  body.appendChild(el('div', { cls: 'mp-field' },
    el('label', null, 'Référence'),
    el('div', { cls: 'mp-readonly' },
      (r.reference || '—') + (r.designation ? ' — ' + r.designation : ''),
    ),
  ));
  const currentQty = Number(r.quantite || 0);
  body.appendChild(el('div', { cls: 'mp-field' },
    el('label', null, 'Quantité actuelle'),
    el('div', { cls: 'mp-readonly' }, fU(currentQty, r.unite || '')),
  ));
  const qInp = el('input', {
    attrs: { type: 'number', min: '0', step: 'any', inputmode: 'decimal', placeholder: 'Nouvelle quantité totale' },
  });
  qInp.value = String(currentQty);
  body.appendChild(el('div', { cls: 'mp-field' },
    el('label', null, 'Nouvelle quantité (' + (r.unite || '') + ')'),
    qInp,
    el('div', { cls: 'mp-hint' },
      'La quantité saisie remplace le total actuel en Z1 pour cette référence.',
    ),
  ));
  const noteTa = el('textarea', { attrs: { placeholder: 'Raison de la modification (optionnel)' } });
  body.appendChild(el('div', { cls: 'mp-field' }, el('label', null, 'Note'), noteTa));

  const submit = async () => {
    const q = parseFloat(qInp.value);
    if (Number.isNaN(q) || q < 0) {
      showToast('Quantité invalide.', 'error');
      return;
    }
    if (Math.abs(q - currentQty) < 0.0001) {
      showToast('Aucun changement.', 'info');
      closeMroot();
      return;
    }
    try {
      await api('/api/stock/mouvement', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          produit_id: r.id,
          emplacement: STOCK_EMPL_SORTIE_PROD,
          type_mouvement: 'inventaire',
          quantite: q,
          note: (noteTa.value || '').trim() || 'Ajustement Z1',
        }),
      });
      showToast('Quantité modifiée.', 'success');
      closeMroot();
      if (S.tab === 'production') await loadProduction();
    } catch (e) {
      showToast(e.message || 'Erreur lors de la modification.', 'error');
    }
  };

  body.appendChild(el('div', { cls: 'mp-modal-actions' },
    el('button', { cls: 'btn-cancel', type: 'button', on: { click: closeMroot } }, 'Annuler'),
    el('button', { cls: 'btn', type: 'button', on: { click: submit } }, 'Enregistrer'),
  ));
  box.appendChild(body);
  overlay.appendChild(box);
  mroot.appendChild(overlay);
}

function buildDashboardKpis(s) {
  const kpis = [
    {
      label: 'MP à approvisionner',
      value: (S.dashboard && S.dashboard.nb_mp_a_approvisionner != null)
               ? S.dashboard.nb_mp_a_approvisionner : 0,
      mod: (S.dashboard && S.dashboard.nb_mp_a_approvisionner > 0) ? 'warn' : 'accent',
    },
    {
      label: 'Références à expédier',
      value: (S.dashboard && S.dashboard.nb_refs_a_expedier != null)
               ? S.dashboard.nb_refs_a_expedier : 0,
      mod: 'accent',
    },
    {
      label: "Expéditions aujourd'hui",
      value: (S.dashboard && S.dashboard.nb_departs_aujourd_hui != null)
               ? S.dashboard.nb_departs_aujourd_hui : 0,
      mod: (S.dashboard && S.dashboard.nb_departs_aujourd_hui > 0) ? 'ok' : 'muted',
    },
    {
      label: 'Références en stock',
      value: (s && s.nb_refs != null) ? s.nb_refs : 0,
      mod: 'accent',
    },
  ];
  return el('div', { cls: 'dash-kpi-grid' },
    ...kpis.map(k => el('div', { cls: 'stat-card' },
      el('div', { cls: 'stat-label' }, k.label),
      el('div', { cls: 'stat-value ' + k.mod }, fN(k.value)),
    )),
  );
}

async function openStockAExpedierQuick() {
  const mroot = document.getElementById('mroot');
  if (!mroot) return;
  closeMroot();
  const overlay = el('div', {
    cls: 'modal-overlay',
    on: { click: (e) => { if (e.target === overlay) closeMroot(); } },
  });
  const sheet = el('div', { cls: 'modal-sheet', style: { maxWidth: '560px' }, on: { click: (e) => e.stopPropagation() } });
  sheet.appendChild(el('div', { cls: 'modal-title' }, 'Stock à expédier'));
  sheet.appendChild(el('div', { cls: 'modal-sub' }, 'Chargement…'));
  overlay.appendChild(sheet);
  mroot.appendChild(overlay);
  try {
    const d = await api('/api/stock/a-expedier');
    renderStockAExpedierModalContent(sheet, d);
  } catch (e) {
    sheet.innerHTML = '';
    sheet.appendChild(el('div', { cls: 'modal-title' }, 'Stock à expédier'));
    sheet.appendChild(el('div', { cls: 'mp-hint err' }, e.message || 'Erreur de chargement.'));
    sheet.appendChild(el('button', {
      cls: 'btn-cancel', type: 'button', style: { marginTop: '14px', width: '100%' },
      on: { click: closeMroot },
    }, 'Fermer'));
  }
}

function renderStockAExpedierModalContent(sheet, data) {
  sheet.innerHTML = '';
  const refs = data?.refs || [];
  const label = data?.label || STOCK_EMPL_AU_SOL_LABEL;
  sheet.appendChild(el('div', { cls: 'modal-title' }, 'Stock à expédier'));
  sheet.appendChild(el('div', { cls: 'modal-sub' },
    'Références en zone « ' + label + ' » — prêtes à partir prochainement.',
  ));
  if (!refs.length) {
    sheet.appendChild(el('div', { cls: 'card-empty', style: { padding: '24px 8px' } },
      'Aucun produit en zone Au sol pour expédition pour le moment.',
    ));
  } else {
    const list = el('div', { cls: 'a-exp-list' });
    refs.forEach(r => {
      list.appendChild(el('div', {
        cls: 'a-exp-row',
        on: { click: () => { closeMroot(); loadProduit(r.id); } },
      },
        el('div', null,
          el('div', { cls: 'a-exp-ref' }, r.reference || '—'),
          el('div', { cls: 'a-exp-des' }, r.designation || ''),
        ),
        el('div', { cls: 'a-exp-qte' }, fU(r.quantite, r.unite || '')),
      ));
    });
    sheet.appendChild(list);
    sheet.appendChild(el('div', {
      style: { fontSize: '12px', color: 'var(--muted)', marginTop: '10px' },
    }, refs.length + ' référence' + (refs.length > 1 ? 's' : '') + ' · ' + fN(data.total_unites || 0) + ' u.'));
  }
  const actions = el('div', { cls: 'modal-actions', style: { marginTop: '16px' } });
  actions.appendChild(el('button', { cls: 'btn-cancel', type: 'button', on: { click: closeMroot } }, 'Fermer'));
  if (refs.length) {
    actions.appendChild(el('button', {
      cls: 'btn btn-accent', type: 'button',
      on: { click: () => { closeMroot(); loadEmplacement(data?.emplacement || STOCK_EMPL_AU_SOL); } },
    }, 'Voir zone ' + label));
  }
  sheet.appendChild(actions);
}

function buildDashboardShortcuts() {
  const mk = (label, onClick, variant, iconName) => el('button', {
    cls: 'dash-quick-btn dash-quick-btn--' + variant,
    type: 'button',
    on: { click: onClick },
  },
    el('span', { cls: 'dash-quick-btn-icon' }, iconEl(iconName, 20)),
    el('span', { cls: 'dash-quick-btn-label' }, label),
  );
  return el('div', { cls: 'dash-quick-card' },
    el('div', { cls: 'dash-quick-card-head' },
      el('span', { cls: 'dash-quick-card-icon', html: icon('zap', 20) }),
      el('div', null,
        el('div', { cls: 'dash-quick-card-title' }, 'Actions rapides'),
        el('div', { cls: 'dash-quick-card-sub' }, 'Accès direct aux opérations courantes'),
      ),
    ),
    el('div', { cls: 'dash-quick-grid' },
      mk('Ajouter stock produits finis', openDashboardAddPfModal, 'accent', 'plus-circle'),
      mk('Stock à expédier', openStockAExpedierQuick, 'warn', 'package'),
      mk('Sortie de prod', openStockSortieProdQuick, 'success', 'layers'),
      mk('Réception matière', openReceptionQuick, 'warn', 'truck'),
      mk('Entrée PF', () => openModalPfMouvement('entree'), 'pf-entree', 'upload'),
      mk('Sortie PF', () => openModalPfMouvement('sortie'), 'pf-sortie', 'download'),
      mk('Entrée MP', () => openModalMouvement('entree'), 'success', 'upload'),
      mk('Sortie MP', () => openModalMouvement('sortie'), 'danger', 'download'),
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
            mpStockLine(a.quantite, a) + ' / min. ' + mpStockLine(a.seuil_alerte, a)
          ),
        )))
      : el('div', { cls: 'dash-alert-ok' }, 'Toutes les matières sont au-dessus des seuils.');
  const contentAlertes = el('div', { cls: 'dash-alert-block' }, mpRows);
  const toggleAlertes = el('button', { cls: 'dash-section-toggle' }, 'Masquer');
  toggleAlertes.onclick = () => {
    const hidden = contentAlertes.style.display === 'none';
    contentAlertes.style.display = hidden ? '' : 'none';
    toggleAlertes.textContent = hidden ? 'Masquer' : 'Afficher';
  };
  return el('div', { cls: 'dash-section' },
    el('div', { cls: 'dash-section-title' },
      el('span', null, 'Stocks à réapprovisionner'),
      toggleAlertes,
    ),
    contentAlertes,
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
  const contentActiv = el('div', { cls: 'dash-act-card' }, list);
  const toggleActiv = el('button', { cls: 'dash-section-toggle' }, 'Masquer');
  toggleActiv.onclick = () => {
    const hidden = contentActiv.style.display === 'none';
    contentActiv.style.display = hidden ? '' : 'none';
    toggleActiv.textContent = hidden ? 'Masquer' : 'Afficher';
  };
  return el('div', { cls: 'dash-section' },
    el('div', { cls: 'dash-section-title' },
      el('span', null, 'Activité récente'),
      toggleActiv,
    ),
    contentActiv,
  );
}

function renderDashboardAddPfModal() {
  const mroot = document.getElementById('mroot');
  if (!mroot) return;
  mroot.innerHTML = '';
  S.mpModal = null;
  S.pfModal = null;

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
    placeholder: 'Emplacement (ex. A121, ' + STOCK_EMPL_AU_SOL + ', ' + STOCK_EMPL_SORTIE_PROD + ')', autocomplete: 'off',
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
      showToast('Emplacement obligatoire (ex. A121, ' + STOCK_EMPL_AU_SOL + ' ou ' + STOCK_EMPL_SORTIE_PROD + ')', 'error');
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
  S.selMatiere = null;
  if (typeof stockSyncUrl === 'function') stockSyncUrl();
  renderContent();
  updateNavActive();
  if (S.tab === 'produits-finis') loadProduitsFinis();
}

function buildProduitDetail() {
  const sel = S.selProduit;
  if (!sel || !sel.produit) return el('div',{cls:'content'},el('div',{cls:'card-empty'},'Données produit indisponibles'));
  const p = sel.produit;
  const empls = sel.emplacements || [];
  const unite = p.unite || 'étiquettes';

  const backLabel = S.tab === 'produits-finis' ? '← Retour aux produits finis' : '← Retour au tableau de bord';
  const back = el('button',{cls:'btn-ghost',style:{marginBottom:'14px'},on:{click:clearSel}}, backLabel);

  const emplBlock = empls.length === 0
    ? el('div',{cls:'card'},el('div',{cls:'card-empty'},'Aucun stock actif pour cette référence.'))
    : el('div',{cls:'card'},
        el('div',{cls:'card-header'},el('div',{cls:'card-title'},'Stock par emplacement')),
        el('div',null,...empls.map(e => el('div',{
          cls:'empl-row',
          on:{click:()=>loadEmplacement(e.emplacement)}
        },
          el('div',null,
            el('div',{cls:stockEmplCodeClass(e.emplacement)},stockEmplLabel(e.emplacement)),
            el('div',{cls:'empl-info'},'FIFO lot : '+fD(e.date_fifo_empl)+(e.alerte_inventaire?' · inventaire':'')+(e.jours_stock!=null?' · ~'+e.jours_stock+'j':''))
          ),
          el('div',{cls:'empl-row-right'},
            el('div',null,
              el('div',{cls:'empl-qte'},fU(e.quantite, unite)),
              el('div',{cls:'empl-date'},fD(e.updated_at||e.date_fifo_empl))
            ),
            buildLotActionBtns(p.id, e.emplacement, e)
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
    buildMvtHistory(sel.mouvements||[], unite, {})
  );
}

function buildEmplacementDetail() {
  const sel = S.selEmpl;
  if (!sel || sel.emplacement == null) return el('div',{cls:'content'},el('div',{cls:'card-empty'},'Emplacement introuvable'));
  const refs = sel.refs || [];
  const code = sel.emplacement;

  const backLabel = S.tab === 'produits-finis' ? '← Retour aux produits finis' : '← Retour au tableau de bord';
  const back = el('button',{cls:'btn-ghost',style:{marginBottom:'14px'},on:{click:clearSel}}, backLabel);

  const actions = S.stockReadOnly ? null : el('div',{cls:'action-bar',style:{marginTop:'14px'}},
    el('button',{cls:'action-btn entree',on:{click:()=>openEmplEntreeModal(code)}},'↓ Entrée'),
    el('button',{cls:'action-btn empl-inv-btn',type:'button',on:{click:()=>openEmplInventaireConfirm(code)}},'☑ Inventaire')
  );

  // Bloc info inventaire (durée depuis dernier inventaire complet)
  const lastInv = sel.last_inventaire;
  const invJours = sel.inv_jours_depuis;
  const invCouleur = sel.inv_couleur || 'rouge';
  const invInfo = el('div', { cls: 'empl-inv-info empl-inv-c-' + invCouleur },
    el('div', { cls: 'empl-inv-label' },
      el('span', { cls: 'empl-inv-dot' }),
      'Inventaire complet'
    ),
    lastInv
      ? el('div', { cls: 'empl-inv-detail' },
          el('span', { cls: 'empl-inv-jours' }, (invJours == null ? '—' : (invJours + ' j'))),
          el('span', { cls: 'empl-inv-meta' },
            ' · dernier le ' + fD(lastInv.date_validation) + ' par ' + (lastInv.operateur_nom || '—')
          )
        )
      : el('div', { cls: 'empl-inv-detail' },
          el('span', { cls: 'empl-inv-jours' }, 'Jamais'),
          el('span', { cls: 'empl-inv-meta' }, ' · aucun inventaire enregistré')
        )
  );

  const head = el('div',{cls:'scorecard'},
    el('div',{cls:stockEmplCodeClass(code)},stockEmplLabel(code)),
    isStockEmplacementAuSol(code)
      ? el('div',{cls:'empl-au-sol-hint'},'Stock prêt à expédier — ces références partiront prochainement.')
      : isStockEmplacementSortieProd(code)
        ? el('div',{cls:'empl-sortie-prod-hint'},'Stock sorti de production — en attente de rangement ou d\'expédition.')
        : null,
    el('div',{cls:'sc-des'},(sel.nb_refs||0)+' réf. · '+fN(sel.total_unites)+' u. en stock'),
    el('div',{cls:'sc-stats'},
      el('div',{cls:'sc-stat'},el('div',{cls:'sc-stat-label'},'Références'),el('div',{cls:'sc-stat-value'},String(refs.length))),
      el('div',{cls:'sc-stat'},el('div',{cls:'sc-stat-label'},'Unités'),el('div',{cls:'sc-stat-value'},fN(sel.total_unites)))
    ),
    invInfo
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
          el('div',{cls:'empl-row-right'},
            el('div',null,
              el('div',{cls:'empl-qte'},fU(r.quantite, r.unite||'')),
              el('div',{cls:'empl-date'},fD(r.date_fifo))
            ),
            buildLotActionBtns(r.id, code, r)
          )
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

// -- Affiches memo (poste Bureaux > Communication) --
const TRACA_AFFICHES = [
  { id:'expe-z0',        variant:'cyan',
    title:"Tu prepares une expe ?",
    sub:"Pense a deplacer ton stock en <b>Z0</b>.",
    icon:'truck',
    dark:'/static/affiches/affiche-expe-z0.html',
    light:'/static/affiches/affiche-expe-z0-light.html' },
  { id:'palette-z1',     variant:'amber',
    title:"Ta palette est complete ?",
    sub:"Pense a l'ajouter en <b>Z1</b>.",
    icon:'layers',
    dark:'/static/affiches/affiche-palette-z1.html',
    light:'/static/affiches/affiche-palette-z1-light.html' },
  { id:'verif-inv',      variant:'violet',
    title:"Tu verifies un stock ?",
    sub:"Profites-en pour faire l'<b>inventaire</b>.",
    icon:'clipboard',
    dark:'/static/affiches/affiche-verif-inventaire.html',
    light:'/static/affiches/affiche-verif-inventaire-light.html' },
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
</head><body>${body}<script>window.onload=function(){window.focus();window.print();}<\/script><script src="/static/mysifa_impersonate.js"><\/script>
</body></html>`);
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

  // -- Dossier "Communication" - uniquement pour le poste Bureaux --
  let commSection = null;
  if (poste.id === 'bureaux') {
    const POSTE_TINT = {
      cyan:   { bg:'rgba(34,211,238,.14)',  color:'#22d3ee' },
      amber:  { bg:'rgba(251,191,36,.16)',  color:'#fbbf24' },
      violet: { bg:'rgba(139,92,246,.18)',  color:'#a78bfa' },
    };
    const affCards = TRACA_AFFICHES.map(aff=>{
      const tint = POSTE_TINT[aff.variant] || POSTE_TINT.cyan;
      const body = el('div',{cls:'traca-aff-body'});
      body.appendChild(el('div',{cls:'traca-aff-title'},aff.title));
      const subEl = el('div',{cls:'traca-aff-sub'});
      subEl.innerHTML = aff.sub;
      body.appendChild(subEl);
      return el('div',{cls:'traca-aff-card traca-aff-card--'+aff.variant},
        el('div',{cls:'traca-etiq-icon-wrap',style:{background:tint.bg,color:tint.color}},
          iconEl(aff.icon,18)),
        body,
        el('div',{cls:'traca-aff-actions'},
          el('a',{cls:'traca-aff-btn traca-aff-btn--dark',
            attrs:{href:aff.dark,target:'_blank',rel:'noopener'}},
            el('span',{cls:'traca-aff-dot'}), 'Sombre'),
          el('a',{cls:'traca-aff-btn traca-aff-btn--light',
            attrs:{href:aff.light,target:'_blank',rel:'noopener'}},
            el('span',{cls:'traca-aff-dot'}), 'Clair')
        )
      );
    });
    commSection = el('div',null,
      el('div',{cls:'traca-group-title'}, iconEl('folder',12), 'Communication'),
      el('div',{cls:'traca-etiq-list'}, ...affCards)
    );
  }

  return el('div',{cls:'content'}, backBar, listEl, commSection);
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
  if (S.invV2Detail) return buildInventaireEmplDetail();
  return buildInventaireList();
}

function buildInventaireList() {
  const list = S.invV2List || [];
  const q = (S.invV2Search || '').trim().toLowerCase();
  const filtered = q
    ? list.filter(e =>
        String(e.emplacement || '').toLowerCase().includes(q) ||
        String(e.label || '').toLowerCase().includes(q))
    : list;

  // Searchbar dans un conteneur séparé pour ne pas perdre le focus au re-render
  const searchInput = el('input', {
    cls:'field-input invv2-search-input',
    id:'invv2-search', type:'text', placeholder:'Rechercher un emplacement (code ou zone)…',
    value: S.invV2Search || '', autocomplete:'off'
  });
  searchInput.addEventListener('input', e => {
    S.invV2Search = e.target.value;
    invV2RenderListItems();
  });
  searchInput.addEventListener('keydown', e => {
    if (e.key === 'Escape') { S.invV2Search = ''; e.target.value = ''; invV2RenderListItems(); }
  });

  const searchWrap = el('div', { cls:'invv2-search-wrap' }, searchInput);

  const listContainer = el('div', { cls:'card invv2-list-card', id:'invv2-list-container' });
  invV2BuildListItems(listContainer, filtered);

  return el('div', { cls:'content' },
    el('div', { cls:'invv2-page-header' },
      el('div', { cls:'invv2-page-title' }, 'Inventaire'),
      el('div', { cls:'invv2-page-sub' }, 'Emplacements triés du plus ancien au plus récent inventaire')
    ),
    el('div', { cls:'invv2-legend' },
      el('div', { cls:'invv2-legend-item invv2-c-vert' }, el('span', { cls:'invv2-dot' }), '< 15 j'),
      el('div', { cls:'invv2-legend-item invv2-c-jaune' }, el('span', { cls:'invv2-dot' }), '15–30 j'),
      el('div', { cls:'invv2-legend-item invv2-c-orange' }, el('span', { cls:'invv2-dot' }), '30–60 j'),
      el('div', { cls:'invv2-legend-item invv2-c-rouge' }, el('span', { cls:'invv2-dot' }), '> 60 j / Jamais')
    ),
    searchWrap,
    listContainer
  );
}

function invV2RenderListItems() {
  const container = document.getElementById('invv2-list-container');
  if (!container) return;
  const list = S.invV2List || [];
  const q = (S.invV2Search || '').trim().toLowerCase();
  const filtered = q
    ? list.filter(e =>
        String(e.emplacement || '').toLowerCase().includes(q) ||
        String(e.label || '').toLowerCase().includes(q))
    : list;
  container.innerHTML = '';
  invV2BuildListItems(container, filtered);
}

function invV2BuildListItems(container, items) {
  if (!items.length) {
    const q = (S.invV2Search || '').trim();
    container.appendChild(el('div', { cls:'card-empty' },
      q ? 'Aucun résultat pour « ' + q + ' »' : 'Aucun emplacement avec stock à inventorier.'
    ));
    return;
  }
  items.forEach(e => {
    const j = e.jours_depuis;
    const joursLabel = (j == null) ? 'Jamais' : (j + ' j');
    const sub = (j == null)
      ? 'jamais inventorié'
      : ('depuis le ' + fD(e.derniere_date));
    container.appendChild(el('div', {
      cls: 'invv2-empl-row invv2-c-' + e.couleur,
      on: { click: () => loadInventaireEmpl(e.emplacement) }
    },
      el('div', { cls:'invv2-empl-main' },
        el('div', { cls:'invv2-empl-code' }, e.label || e.emplacement),
        el('div', { cls:'invv2-empl-meta' },
          (e.nb_refs || 0) + ' réf · ' + fN(e.total_qte || 0) + ' u.' +
          (e.dernier_operateur ? ' · dernier inv. par ' + e.dernier_operateur : '')
        )
      ),
      el('div', { cls:'invv2-empl-right' },
        el('div', { cls:'invv2-jours invv2-c-' + e.couleur }, joursLabel),
        el('div', { cls:'invv2-jours-sub' }, sub)
      )
    ));
  });
}

function buildInventaireEmplDetail() {
  const d = S.invV2Detail;
  if (!d) return el('div', { cls:'content' }, el('div', { cls:'card-empty' }, 'Emplacement introuvable'));
  const refs = d.refs || [];
  const total = refs.length;
  const validated = refs.filter(r => S.invV2Validated[r.produit_id]).length;
  const allValidated = (total === 0) || (validated === total && total > 0);

  const back = el('button', { cls:'btn-ghost invv2-back', on:{ click: clearInventaireEmpl } }, '← Retour aux emplacements');

  const last = d.last_inventaire;
  const head = el('div', { cls:'invv2-scorecard' },
    el('div', { cls:'invv2-detail-title' }, d.label || d.emplacement),
    last
      ? el('div', { cls:'invv2-last-info' },
          'Dernier inventaire : ',
          el('strong', null, fD(last.date_validation)),
          ' · par ',
          el('strong', null, last.operateur_nom || '—')
        )
      : el('div', { cls:'invv2-last-info invv2-last-none' }, 'Aucun inventaire enregistré pour cet emplacement.'),
    el('div', { cls:'invv2-detail-stats' },
      el('div', { cls:'invv2-stat' },
        el('div', { cls:'invv2-stat-label' }, 'Produits'),
        el('div', { cls:'invv2-stat-value' }, String(total))
      ),
      el('div', { cls:'invv2-stat' },
        el('div', { cls:'invv2-stat-label' }, 'Validés'),
        el('div', { cls:'invv2-stat-value' }, validated + ' / ' + total)
      )
    )
  );

  // Liste des produits
  const addBtn = el('button', {
    cls:'invv2-btn-add-product',
    type:'button',
    title:'Ajouter un produit à cet emplacement',
    on:{ click: () => invV2OpenAddProductModal() }
  }, '+ Ajouter un produit');

  let refsBlock;
  if (total === 0) {
    refsBlock = el('div', { cls:'card invv2-prod-card invv2-empty-card' },
      el('div', { cls:'card-header' },
        el('div', { cls:'card-title' }, 'Produits à inventorier'),
        addBtn
      ),
      el('div', { cls:'card-empty' }, 'Cet emplacement est vide — vous pouvez valider directement l\'inventaire à vide, ou ajouter un produit ci-dessus.')
    );
  } else {
    refsBlock = el('div', { cls:'card invv2-prod-card' },
      el('div', { cls:'card-header' },
        el('div', { cls:'card-title' }, 'Produits à inventorier · ' + total),
        addBtn
      ),
      el('div', { cls:'invv2-prod-list' }, ...refs.map(r => invV2BuildProductRow(r)))
    );
  }

  // Bouton d'action principal
  const actionBar = el('div', { cls:'invv2-action-bar' });
  if (allValidated) {
    actionBar.appendChild(el('button', {
      cls:'invv2-btn-validate-all',
      on:{ click: invV2ValidateFullInventaire }
    }, "Valider l'inventaire"));
  } else {
    actionBar.appendChild(el('div', { cls:'invv2-btn-to-validate' },
      'Produits à valider · ' + validated + ' / ' + total
    ));
  }

  // Historique
  const history = d.history || [];
  const histExpanded = !!S.invV2HistoryExpanded;
  const histVisible = histExpanded ? history : history.slice(0, 5);
  let histBlock;
  if (history.length === 0) {
    histBlock = el('div', { cls:'card invv2-history-card' },
      el('div', { cls:'card-header' }, el('div', { cls:'card-title' }, 'Historique des inventaires')),
      el('div', { cls:'card-empty' }, 'Aucun inventaire enregistré pour cet emplacement.')
    );
  } else {
    const histRows = histVisible.map(h => {
      const comments = Array.isArray(h.commentaires) ? h.commentaires : [];
      const nbCom = comments.length;
      const row = el('div', { cls:'invv2-hist-row' },
        el('div', { cls:'invv2-hist-date' }, fD(h.date_validation)),
        el('div', { cls:'invv2-hist-op' }, h.operateur_nom || '—'),
        el('div', { cls:'invv2-hist-meta' },
          (h.nb_produits || 0) + ' réf · ' + (h.nb_modifications || 0) + ' modif.' +
          (nbCom ? ' · ' + nbCom + ' note' + (nbCom>1?'s':'') : '')
        )
      );
      if (nbCom) {
        const block = el('div', { cls:'invv2-hist-comments' });
        comments.forEach(c => {
          const ref = c.reference || ('#' + (c.produit_id || ''));
          const des = c.designation || '';
          block.appendChild(el('div', { cls:'invv2-hist-comment' },
            el('div', { cls:'invv2-hist-comment-head' },
              el('span', { cls:'invv2-hist-comment-ref' }, ref),
              des ? el('span', { cls:'invv2-hist-comment-des' }, ' — ' + des) : null,
            ),
            el('div', { cls:'invv2-hist-comment-body' }, c.commentaire || '')
          ));
        });
        return el('div', { cls:'invv2-hist-block' }, row, block);
      }
      return row;
    });
    const moreBtn = (history.length > 5)
      ? el('button', { cls:'invv2-btn-more', on:{ click: () => { S.invV2HistoryExpanded = !histExpanded; renderContent(); } } },
          histExpanded ? 'Voir moins' : ('Voir plus (' + (history.length - 5) + ')'))
      : null;
    histBlock = el('div', { cls:'card invv2-history-card' },
      el('div', { cls:'card-header' }, el('div', { cls:'card-title' }, 'Historique des inventaires')),
      el('div', { cls:'invv2-hist-list' }, ...histRows),
      moreBtn
    );
  }

  return el('div', { cls:'content invv2-detail' }, back, head, refsBlock, actionBar, histBlock);
}

function invV2BuildProductRow(r) {
  const pid = r.produit_id;
  const isValidated = !!S.invV2Validated[pid];
  const modif = S.invV2Modifs[pid];
  const commentTxt = S.invV2Comments[pid] || '';
  const hasComment = !!commentTxt;
  const qteActuelle = parseFloat(r.quantite) || 0;
  const unite = r.unite || '';
  const isAdded = !!r._added;

  const nbLots = (r.lots && r.lots.length) || (isAdded ? 0 : 1);
  const lotsTxt = isAdded
    ? 'nouveau produit pour cet emplacement'
    : (nbLots > 1 ? (nbLots + ' lots') : '1 lot');

  // Quantité affichée
  let qtyEl;
  if (modif && Math.abs(modif.qte_apres - modif.qte_avant) > 1e-9) {
    qtyEl = el('div', { cls:'invv2-prod-qty' },
      el('span', { cls:'invv2-prod-qty-new' }, fU(modif.qte_apres, unite)),
      el('span', { cls:'invv2-prod-qty-old' }, fU(modif.qte_avant, unite))
    );
  } else {
    qtyEl = el('div', { cls:'invv2-prod-qty' },
      el('span', { cls:'invv2-prod-qty-main' }, fU(qteActuelle, unite))
    );
  }

  // Bouton Note (toujours dispo, validé ou non)
  const noteBtn = el('button', {
    cls: 'invv2-btn-note' + (hasComment ? ' has-comment' : ''),
    type:'button',
    title: hasComment ? 'Modifier la note' : 'Ajouter une note',
    on:{ click: e => { e.stopPropagation(); invV2OpenCommentModal(pid, r.reference, r.designation); } }
  }, hasComment ? 'Note ●' : 'Note');

  // Boutons
  let buttons;
  if (isValidated) {
    buttons = el('div', { cls:'invv2-prod-actions' },
      noteBtn,
      el('button', {
        cls:'invv2-btn-cancel',
        type:'button',
        title:'Annuler la validation',
        on:{ click: e => { e.stopPropagation(); invV2CancelValidate(pid); } }
      }, '✓')
    );
  } else {
    buttons = el('div', { cls:'invv2-prod-actions' },
      noteBtn,
      el('button', {
        cls:'invv2-btn-modify',
        type:'button',
        title:'Modifier la quantité',
        on:{ click: e => { e.stopPropagation(); invV2OpenModifyModal(pid, qteActuelle, r.reference, r.designation, unite); } }
      }, 'Modifier'),
      el('button', {
        cls:'invv2-btn-validate',
        type:'button',
        title:'Valider',
        on:{ click: e => { e.stopPropagation(); invV2ToggleValidate(pid); } }
      }, '✓')
    );
  }

  const refContent = isAdded
    ? el('div', { cls:'invv2-prod-ref' },
        r.reference || '—',
        el('span', { cls:'invv2-prod-badge-new' }, 'Ajouté')
      )
    : el('div', { cls:'invv2-prod-ref' }, r.reference || '—');

  const infoTxt = (r.designation ? r.designation + ' · ' : '') + lotsTxt;
  const mainChildren = [
    refContent,
    el('div', { cls:'invv2-prod-info' }, infoTxt),
  ];
  if (hasComment) {
    mainChildren.push(el('div', { cls:'invv2-prod-comment-preview', title:'Note en attente (visible après validation)' },
      el('span', { cls:'invv2-prod-comment-tag' }, 'Note'),
      truncStr(commentTxt, 90)
    ));
  }

  return el('div', { cls: 'invv2-prod-row' + (isValidated ? ' invv2-validated' : '') + (isAdded ? ' invv2-added' : '') },
    el('div', { cls:'invv2-prod-main' }, ...mainChildren),
    qtyEl,
    buttons
  );
}

function renderContent() {
  const area = document.getElementById('scroll-area');
  if (!area) return;

  // Détail produit / emplacement / matière : prioritaire sur l'onglet courant
  // (sinon un clic depuis la searchbar globale sur les onglets produits-finis,
  // negoce, referentiel... ne basculerait jamais vers le détail).
  if (S.selProduit || S.selEmpl || S.selMatiere) {
    area.innerHTML = '';
    let content;
    if (S.selProduit) content = buildProduitDetail();
    else if (S.selEmpl) content = buildEmplacementDetail();
    else if (S.selMatiere) content = buildMatiereDetail();
    if (content) area.appendChild(content);
    return;
  }

  if (S.tab === 'produits-finis') {
    renderProduitsFinisView();
    return;
  }
  if (S.tab === 'negoce') {
    renderNegoceView();
    return;
  }
  if (S.tab === 'referentiel') {
    renderReferentielView();
    return;
  }
  if (S.tab === 'monitoring') {
    renderMonitoringView(true);
    return;
  }
  if (S.tab === 'valorisation') {
    renderValorisationView(true);
    return;
  }
  area.innerHTML = '';

  let content;
  if (S.tab === 'production') content = buildProductionView();
  else if (S.tab === 'dashboard') content = buildDashboard();
  else if (S.tab === 'matieres') {
    content = buildMatieres();
  }
  else if (S.tab === 'inventaire') content = buildInventaire();
  else if (S.tab === 'traca') content = buildTraca();
  else if (S.tab === 'reception') content = buildReception();
  else if (S.tab === 'historique') content = buildHistorique();
  else if (S.tab === 'plan-entrepot') { buildPlanEntrepot(); return; }
  else content = buildDashboard();

  if (content) area.appendChild(content);
}

// ── Monitoring réconciliation ERP ───────────────────────────────

function monEnsureState() {
  if (!S.monitoring) {
    S.monitoring = {
      snapshots: [],
      current: null,
      lines: [],
      allLines: [],
      filterStatut: null,
      query: '',
      loading: false,
      importing: false,
      selectedId: null,
      monPage: 'quantites',
      sortColumn: null,
      sortDirection: 'asc',
    };
  }
  return S.monitoring;
}

function monSnapshotLabel(s) {
  const dt = fDateTime(s.created_at);
  const who = (s.created_by_name || '').trim();
  const file = (s.source_filename || '').trim();
  if (who) return dt + ' — ' + who;
  if (file) return dt + ' — ' + file;
  return dt;
}

function monFilteredLines() {
  const m = monEnsureState();
  let rows = m.allLines || m.lines || [];
  if (m.filterStatut === 'sans_corresp') {
    rows = rows.filter(r =>
      r.statut === 'sans_corresp_erp' || r.statut === 'sans_corresp_mysifa'
    );
  } else if (m.filterStatut === 'stock_mysifa_zero') {
    rows = rows.filter(r => r.stock_mysifa === 0);
  } else if (m.filterStatut === 'stock_erp_zero') {
    rows = rows.filter(r => r.stock_erp === 0);
  } else if (m.filterStatut) {
    rows = rows.filter(r => r.statut === m.filterStatut);
  }
  const q = (m.query || '').trim().toLowerCase();
  if (q) {
    rows = rows.filter(r =>
      (r.reference || '').toLowerCase().includes(q) ||
      (r.designation || '').toLowerCase().includes(q)
    );
  }
  // Exclure les références avec stock mySifa = 0 et sans correspondance ERP
  rows = rows.filter(r => {
    const stockMysifa = Number(r.stock_mysifa);
    const isStockMysifaZero = stockMysifa === 0 || r.stock_mysifa == null || r.stock_mysifa === '';
    const isSansCorrespErp = r.statut === 'sans_corresp_erp';
    return !(isStockMysifaZero && isSansCorrespErp);
  });
  // Exclure les lignes où stock ERP et stock Mysifa sont tous deux égaux à 0
  rows = rows.filter(r => {
    const stockErp = Number(r.stock_erp);
    const stockMysifa = Number(r.stock_mysifa);
    const isStockErpZero = stockErp === 0 || r.stock_erp == null || r.stock_erp === '';
    const isStockMysifaZero = stockMysifa === 0 || r.stock_mysifa == null || r.stock_mysifa === '';
    return !(isStockErpZero && isStockMysifaZero);
  });
  // Apply sorting
  if (m.sortColumn) {
    rows.sort((a, b) => {
      let valA, valB;
      switch (m.sortColumn) {
        case 'reference':
          valA = (a.reference || '').toLowerCase();
          valB = (b.reference || '').toLowerCase();
          break;
        case 'designation':
          valA = (a.designation || '').toLowerCase();
          valB = (b.designation || '').toLowerCase();
          break;
        case 'unite':
          valA = (a.unite || '').toLowerCase();
          valB = (b.unite || '').toLowerCase();
          break;
        case 'stock_erp':
          valA = Number(a.stock_erp) || 0;
          valB = Number(b.stock_erp) || 0;
          break;
        case 'stock_mysifa':
          valA = Number(a.stock_mysifa) || 0;
          valB = Number(b.stock_mysifa) || 0;
          break;
        case 'ecart':
          valA = (Number(a.stock_erp) || 0) - (Number(a.stock_mysifa) || 0);
          valB = (Number(b.stock_erp) || 0) - (Number(b.stock_mysifa) || 0);
          break;
        case 'dernier_mvt_erp':
          valA = a.dernier_mvt_erp || '';
          valB = b.dernier_mvt_erp || '';
          break;
        case 'mysifa_date_fifo':
          valA = a.mysifa_date_fifo || '';
          valB = b.mysifa_date_fifo || '';
          break;
        case 'statut':
          valA = (a.statut || '').toLowerCase();
          valB = (b.statut || '').toLowerCase();
          break;
        default:
          return 0;
      }
      if (valA < valB) return m.sortDirection === 'asc' ? -1 : 1;
      if (valA > valB) return m.sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }
  return rows;
}

function monToggleSort(column) {
  const m = monEnsureState();
  if (m.sortColumn === column) {
    m.sortDirection = m.sortDirection === 'asc' ? 'desc' : 'asc';
  } else {
    m.sortColumn = column;
    m.sortDirection = 'asc';
  }
  renderMonitoringView(false);
}

function monFmtEcart(val) {
  if (val == null || val === '') return '—';
  const n = Number(val);
  if (Number.isNaN(n)) return '—';
  const sign = n > 0 ? '+' : '';
  return sign + fN(n);
}

function monStatutBadge(statut) {
  if (statut === 'ok') return el('span', { cls: 'mon-statut mon-statut-ok' }, 'OK');
  if (statut === 'ecart') return el('span', { cls: 'mon-statut mon-statut-ecart' }, 'Écart');
  if (statut === 'sans_corresp_erp') return el('span', { cls: 'mon-statut mon-statut-warn' }, 'Absent ERP');
  if (statut === 'sans_corresp_mysifa') return el('span', { cls: 'mon-statut mon-statut-warn' }, 'Absent MySifa');
  return el('span', { cls: 'mon-statut' }, statut || '—');
}

function monQtyTd(val, unite) {
  const n = val != null && val !== '' ? Number(val) : null;
  const style = n != null && n < 0 ? { color: 'var(--danger)', fontWeight: '600' } : {};
  const txt = val != null && val !== '' ? (unite ? fU(val, unite) : fN(val)) : '—';
  return el('td', { style }, txt);
}

function monEcartTd(ln) {
  if (ln.ecart == null || ln.ecart === '') return el('td', null, '—');
  const cls = ln.statut === 'ecart' ? 'mon-ecart-danger' : '';
  return el('td', null, el('span', { cls }, monFmtEcart(ln.ecart)));
}

function monMvtErpCell(ln) {
  const lib = (ln.erp_dernier_mvt_libelle || '').trim();
  const dt = ln.erp_dernier_mvt_date ? fDateTime(ln.erp_dernier_mvt_date) : '';
  if (!lib && !dt) return el('td', { cls: 'hist-muted' }, '—');
  return el('td', null,
    lib ? el('div', { title: escAttr(lib) }, truncStr(lib, 48)) : null,
    dt ? el('div', { cls: 'hist-muted', style: { fontSize: '11px', marginTop: '2px' } }, dt) : null,
  );
}

function buildMonitoringKpis(snap, allLines) {
  const sansMysifa = (allLines || []).filter(l => l.statut === 'sans_corresp_mysifa').length;
  const sansTotal = (snap.nb_sans_corresp || 0) + sansMysifa;
  const kpis = [
    { label: 'Références comparées', value: snap.nb_matched || 0, mod: 'accent' },
    { label: 'Écarts', value: snap.nb_ecarts || 0, mod: (snap.nb_ecarts > 0 ? 'danger' : 'accent') },
    { label: 'Sans correspondance', value: sansTotal, mod: (sansTotal > 0 ? 'warn' : 'accent') },
    { label: 'Stocks négatifs', value: snap.nb_negatifs || 0, mod: (snap.nb_negatifs > 0 ? 'danger' : 'accent') },
  ];
  return el('div', { cls: 'dash-kpi-grid', style: { marginBottom: '16px' } },
    ...kpis.map(k => el('div', { cls: 'stat-card' },
      el('div', { cls: 'stat-label' }, k.label),
      el('div', { cls: 'stat-value ' + k.mod }, fN(k.value)),
    )),
  );
}

function buildMonitoringTableRow(ln) {
  const ref = ln.reference || '—';
  const des = ln.designation || '—';
  const unite = ln.unite || '';
  return el('tr', null,
    el('td', { cls: 'hist-ref' }, ref),
    el('td', { cls: 'hist-des', title: escAttr(des) }, truncStr(des, 40) || '—'),
    el('td', { cls: 'hist-unite' }, unite || '—'),
    monQtyTd(ln.stock_erp, unite),
    monQtyTd(ln.stock_mysifa, unite),
    monEcartTd(ln),
    monMvtErpCell(ln),
    el('td', { cls: 'hist-muted' }, ln.mysifa_date_fifo ? fDateTime(ln.mysifa_date_fifo) : '—'),
    el('td', null, monStatutBadge(ln.statut)),
  );
}

function renderMonitoringResults(container) {
  if (!container) return;
  container.innerHTML = '';
  const m = monEnsureState();
  if (m.monPage === 'mouvements') {
    renderMonitoringMovements(container);
    return;
  }
  if (m.loading) {
    container.appendChild(el('div', { cls: 'hist-loading' },
      el('div', { cls: 'hist-spinner' }),
      'Chargement…',
    ));
    return;
  }
  if (!m.current) {
    container.appendChild(el('div', { cls: 'hist-empty' },
      'Aucun snapshot — importez un export ERP Table Stocks (.xlsx) pour démarrer la réconciliation.',
    ));
    return;
  }
  const rows = monFilteredLines();
  const q = (m.query || '').trim();
  const card = el('div', { cls: 'hist-results-card' });
  card.appendChild(el('div', { cls: 'hist-results-head' },
    el('div', { cls: 'hist-results-head-left' },
      el('span', { cls: 'hist-results-title' }, 'Lignes comparées'),
      el('span', { cls: 'hist-count' }, fN(rows.length) + ' ligne' + (rows.length > 1 ? 's' : '')),
    ),
  ));
  if (!rows.length) {
    card.appendChild(el('div', { cls: 'hist-empty', style: { border: 'none', borderRadius: '0' } },
      q
        ? 'Aucun résultat pour « ' + escHtml(q) + ' ».'
        : 'Aucune ligne pour ce filtre.',
    ));
  } else {
    const table = el('table', { cls: 'hist-table' });
    const m = monEnsureState();
    const sortIcon = (col) => {
      if (m.sortColumn !== col) return '';
      return m.sortDirection === 'asc' ? ' ▲' : ' ▼';
    };
    table.appendChild(el('thead', null, el('tr', null,
      el('th', { 
        style: { cursor: 'pointer', userSelect: 'none' },
        on: { click: () => monToggleSort('reference') }
      }, 'Référence' + sortIcon('reference')),
      el('th', { 
        style: { cursor: 'pointer', userSelect: 'none' },
        on: { click: () => monToggleSort('designation') }
      }, 'Désignation' + sortIcon('designation')),
      el('th', { 
        style: { cursor: 'pointer', userSelect: 'none' },
        on: { click: () => monToggleSort('unite') }
      }, 'Unité' + sortIcon('unite')),
      el('th', { 
        style: { cursor: 'pointer', userSelect: 'none' },
        on: { click: () => monToggleSort('stock_erp') }
      }, 'Stock ERP' + sortIcon('stock_erp')),
      el('th', { 
        style: { cursor: 'pointer', userSelect: 'none' },
        on: { click: () => monToggleSort('stock_mysifa') }
      }, 'Stock MySifa' + sortIcon('stock_mysifa')),
      el('th', { 
        style: { cursor: 'pointer', userSelect: 'none' },
        on: { click: () => monToggleSort('ecart') }
      }, 'Écart' + sortIcon('ecart')),
      el('th', { 
        style: { cursor: 'pointer', userSelect: 'none' },
        on: { click: () => monToggleSort('dernier_mvt_erp') }
      }, 'Dernier mvt ERP' + sortIcon('dernier_mvt_erp')),
      el('th', { 
        style: { cursor: 'pointer', userSelect: 'none' },
        on: { click: () => monToggleSort('mysifa_date_fifo') }
      }, 'Dernier flux MySifa' + sortIcon('mysifa_date_fifo')),
      el('th', { 
        style: { cursor: 'pointer', userSelect: 'none' },
        on: { click: () => monToggleSort('statut') }
      }, 'Statut' + sortIcon('statut')),
    )));
    const tbody = el('tbody', null);
    rows.forEach(ln => tbody.appendChild(buildMonitoringTableRow(ln)));
    table.appendChild(tbody);
    card.appendChild(el('div', { cls: 'hist-table-wrap' }, table));
  }
  container.appendChild(card);
}

function renderMonitoringMovements(container) {
  if (!container) return;
  container.innerHTML = '';
  const m = monEnsureState();
  if (m.loading) {
    container.appendChild(el('div', { cls: 'hist-loading' },
      el('div', { cls: 'hist-spinner' }),
      'Chargement…',
    ));
    return;
  }
  if (!m.current) {
    container.appendChild(el('div', { cls: 'hist-empty' },
      'Aucun snapshot — importez un export ERP Table Stocks (.xlsx) pour démarrer la réconciliation.',
    ));
    return;
  }
  const cutoff = Date.now() - 7 * 24 * 3600 * 1000;
  let rows = (m.allLines || []).filter(ln => {
    const stockErp = Number(ln.stock_erp);
    const stockMysifa = Number(ln.stock_mysifa);
    const isStockErpZero = stockErp === 0 || ln.stock_erp == null || ln.stock_erp === '';
    const isStockMysifaZero = stockMysifa === 0 || ln.stock_mysifa == null || ln.stock_mysifa === '';
    if (isStockErpZero && isStockMysifaZero) return false;
    const erpMs = ln.erp_dernier_mvt_date ? new Date(ln.erp_dernier_mvt_date).getTime() : 0;
    const erpBougeCetteSemaine = erpMs > cutoff;
    const mysifaBougeCetteSemaine = (ln.mysifa_mvt_semaine_count || 0) > 0;
    return erpBougeCetteSemaine || mysifaBougeCetteSemaine;
  });
  const card = el('div', { cls: 'hist-results-card' });
  card.appendChild(el('div', { cls: 'hist-results-head' },
    el('div', { cls: 'hist-results-head-left' },
      el('span', { cls: 'hist-results-title' }, 'Mouvements de la semaine'),
      el('span', { cls: 'hist-count' }, fN(rows.length) + ' référence(s) avec activité cette semaine'),
    ),
  ));
  if (!rows.length) {
    card.appendChild(el('div', { cls: 'hist-empty', style: { border: 'none', borderRadius: '0' } },
      'Aucun mouvement ERP ou MySifa enregistré sur les 7 derniers jours.',
    ));
  } else {
    const table = el('table', { cls: 'hist-table' });
    table.appendChild(el('thead', null, el('tr', null,
      el('th', null, 'Référence'),
      el('th', null, 'Désignation'),
      el('th', null, 'Dernier mvt ERP'),
      el('th', null, 'Dernier mvt MySifa'),
      el('th', null, 'ERP semaine'),
      el('th', null, 'MySifa semaine'),
      el('th', null, 'Correspondance'),
    )));
    const tbody = el('tbody', null);
    rows.forEach(ln => {
      const erpMs = ln.erp_dernier_mvt_date ? new Date(ln.erp_dernier_mvt_date).getTime() : 0;
      const erpBougeCetteSemaine = erpMs > cutoff;
      const mysifaBougeCetteSemaine = (ln.mysifa_mvt_semaine_count || 0) > 0;
      const erpColor = erpBougeCetteSemaine ? 'var(--text)' : 'var(--muted)';
      const mysifaColor = mysifaBougeCetteSemaine ? 'var(--text)' : 'var(--muted)';
      const erpLib = (ln.erp_dernier_mvt_libelle || '').trim();
      const erpDt = ln.erp_dernier_mvt_date ? fDateTime(ln.erp_dernier_mvt_date) : '';
      const erpQte = ln.erp_dernier_mvt_qte != null ? fN(ln.erp_dernier_mvt_qte) : '';
      const mysifaDt = ln.mysifa_dernier_mvt_date ? fDateTime(ln.mysifa_dernier_mvt_date) : (ln.mysifa_date_fifo ? fDateTime(ln.mysifa_date_fifo) : '');
      let erpBadge = null;
      if (erpBougeCetteSemaine) {
        erpBadge = el('span', { cls: 'mon-statut mon-statut-ok' }, 'Cette semaine');
      } else {
        erpBadge = el('span', { cls: 'hist-muted' }, '—');
      }
      let mysifaBadge = null;
      if (mysifaBougeCetteSemaine) {
        mysifaBadge = el('span', { cls: 'mon-statut mon-statut-ok' }, 'Cette semaine');
      } else if (ln.mysifa_mvt_semaine_count == null) {
        mysifaBadge = el('span', { cls: 'hist-muted' }, '?');
      } else {
        mysifaBadge = el('span', { cls: 'hist-muted' }, '—');
      }
      let correspBadge = null;
      if (erpBougeCetteSemaine && mysifaBougeCetteSemaine) {
        correspBadge = el('span', { cls: 'mon-statut mon-statut-ok' }, 'OK');
      } else if (erpBougeCetteSemaine && !mysifaBougeCetteSemaine) {
        correspBadge = el('span', { cls: 'mon-statut mon-statut-ecart' }, 'ERP sans MySifa');
      } else if (!erpBougeCetteSemaine && mysifaBougeCetteSemaine) {
        correspBadge = el('span', { cls: 'mon-statut mon-statut-warn' }, 'MySifa sans ERP');
      } else {
        correspBadge = el('span', { cls: 'hist-muted' }, '—');
      }
      tbody.appendChild(el('tr', null,
        el('td', { cls: 'hist-ref' }, ln.reference || '—'),
        el('td', { cls: 'hist-des', title: escAttr(ln.designation || '') }, truncStr(ln.designation || '', 40) || '—'),
        el('td', null,
          erpLib ? el('div', { style: { color: erpColor }, title: escAttr(erpLib) }, truncStr(erpLib, 36)) : null,
          erpDt ? el('div', { cls: 'hist-muted', style: { fontSize: '11px', marginTop: '2px', color: erpColor } }, erpDt) : null,
          erpQte ? el('div', { cls: 'hist-muted', style: { fontSize: '11px', marginTop: '2px', color: erpColor } }, erpQte) : null,
        ),
        el('td', null,
          mysifaDt ? el('div', { style: { color: mysifaColor } }, mysifaDt) : el('span', { cls: 'hist-muted' }, '—'),
        ),
        el('td', null, erpBadge),
        el('td', null, mysifaBadge),
        el('td', null, correspBadge),
      ));
    });
    table.appendChild(tbody);
    card.appendChild(el('div', { cls: 'hist-table-wrap' }, table));
  }
  container.appendChild(card);
}

function renderMonitoringView(fullRebuild) {
  if (S.tab !== 'monitoring') return;
  const ae = document.activeElement;
  const focusId = ae?.id;
  const caretStart = ae?.selectionStart;
  const caretEnd = ae?.selectionEnd;
  const area = document.getElementById('scroll-area');
  if (!area) return;
  const resultsOnly = !fullRebuild && document.getElementById('mon-results-wrap');
  if (resultsOnly) {
    renderMonitoringResults(document.getElementById('mon-results-wrap'));
    if (focusId) {
      const foc = document.getElementById(focusId);
      if (foc) {
        foc.focus();
        if (caretStart != null) {
          try { foc.setSelectionRange(caretStart, caretEnd); } catch (e) {}
        }
      }
    }
    return;
  }
  area.innerHTML = '';
  const content = buildMonitoring();
  if (content) area.appendChild(content);
  renderMonitoringResults(document.getElementById('mon-results-wrap'));
  if (focusId) {
    const foc = document.getElementById(focusId);
    if (foc) {
      foc.focus();
      if (caretStart != null) {
        try { foc.setSelectionRange(caretStart, caretEnd); } catch (e) {}
      }
    }
  }
}

function buildMonitoring() {
  const m = monEnsureState();
  const head = el('div', { cls: 'hist-head' },
    el('div', null,
      el('h2', { cls: 'hist-title' }, 'Monitoring stocks PF'),
      el('p', { cls: 'hist-subtitle' }, 'Réconciliation hebdomadaire ERP vs MySifa — produits finis'),
    ),
  );

  const fileInp = el('input', {
    type: 'file',
    accept: '.xlsx',
    style: { display: 'none' },
    id: 'mon-import-file',
  });
  fileInp.addEventListener('change', async () => {
    const f = fileInp.files && fileInp.files[0];
    fileInp.value = '';
    if (!f) return;
    await monitoringImportFile(f);
  });

  const importBtn = el('button', {
    cls: 'btn btn-accent',
    type: 'button',
    disabled: m.importing ? true : null,
    on: { click: () => fileInp.click() },
  }, m.importing ? 'Import en cours…' : 'Importer l\'export ERP (.xlsx)');

  const snapSel = el('select', {
    cls: 'mon-snapshot-select',
    id: 'mon-snapshot-select',
    disabled: !m.snapshots.length ? true : null,
  });
  if (!m.snapshots.length) {
    snapSel.appendChild(el('option', { value: '' }, 'Aucun snapshot'));
  } else {
    m.snapshots.forEach(s => {
      snapSel.appendChild(el('option', {
        value: String(s.id),
        selected: String(m.selectedId) === String(s.id) ? true : null,
      }, monSnapshotLabel(s)));
    });
  }
  snapSel.addEventListener('change', () => {
    const id = parseInt(snapSel.value, 10);
    if (id) loadMonitoringSnapshot(id);
  });

  const actions = el('div', { cls: 'mon-actions', id: 'mon-actions-bar' },
    importBtn,
    fileInp,
    snapSel,
  );

  const kpisWrap = el('div', { id: 'mon-kpis-wrap' });
  if (m.current) kpisWrap.appendChild(buildMonitoringKpis(m.current, m.allLines));

  const pageDefs = [
    { id: 'quantites', label: 'Quantités' },
    { id: 'mouvements', label: 'Mouvements' },
  ];
  const pagePills = el('div', { cls: 'mp-pills', id: 'mon-page-pills' },
    ...pageDefs.map(pd => el('button', {
      cls: 'mp-pill' + (m.monPage === pd.id ? ' active' : ''),
      type: 'button',
      on: { click: () => {
        m.monPage = pd.id;
        renderMonitoringView(true);
      } },
    }, pd.label)),
  );

  let filtersRow = null;
  if (m.monPage === 'quantites') {
    const filterDefs = [
      { id: null, label: 'Tout' },
      { id: 'ecart', label: 'Écarts' },
      { id: 'ok', label: 'OK' },
      { id: 'sans_corresp', label: 'Sans correspondance' },
      { id: 'stock_mysifa_zero', label: 'Stock MySIFA = 0' },
      { id: 'stock_erp_zero', label: 'Stock ERP = 0' },
    ];
    const pills = el('div', { cls: 'mp-pills', id: 'mon-filter-pills' },
      ...filterDefs.map(fd => el('button', {
        cls: 'mp-pill' + (
          (fd.id == null && !m.filterStatut) || m.filterStatut === fd.id ? ' active' : ''
        ),
        type: 'button',
        on: { click: () => {
          m.filterStatut = fd.id;
          renderMonitoringView(true);
        } },
      }, fd.label)),
    );

    const searchInp = el('input', {
      type: 'search',
      id: 'mon-search',
      placeholder: 'Rechercher (référence, désignation…)',
      autocomplete: 'off',
      spellcheck: 'false',
    });
    searchInp.value = m.query || '';
    searchInp.addEventListener('input', (e) => {
      m.query = e.target.value;
      renderMonitoringView(false);
    });
    searchInp.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        m.query = '';
        renderMonitoringView(false);
      }
    });

    filtersRow = el('div', { cls: 'mon-filters-row', id: 'mon-filters-bar' },
      el('div', { cls: 'mon-search-wrap' },
        el('span', { attrs: { 'aria-hidden': 'true' } }, iconEl('search', 18)),
        searchInp,
      ),
      pills,
    );
  }

  const resultsWrap = el('div', { id: 'mon-results-wrap' });

  return el('div', { cls: 'content mon-page hist-page' },
    head,
    actions,
    kpisWrap,
    pagePills,
    filtersRow,
    resultsWrap,
  );
}

async function loadMonitoringSnapshot(snapshotId) {
  const m = monEnsureState();
  m.loading = true;
  renderMonitoringView(false);
  try {
    const d = await api('/api/reconciliation/snapshots/' + snapshotId);
    if (d) {
      m.current = d.snapshot;
      m.lines = d.lines || [];
      m.allLines = d.lines || [];
      m.selectedId = snapshotId;
    }
  } catch (e) {
    showToast(e.message || 'Chargement impossible.', 'error');
  }
  m.loading = false;
  renderMonitoringView(true);
}

async function loadMonitoring(selectSnapshotId) {
  const m = monEnsureState();
  m.loading = true;
  renderMonitoringView(true);
  try {
    const snaps = await api('/api/reconciliation/snapshots');
    m.snapshots = snaps || [];
    let id = selectSnapshotId;
    if (!id && m.snapshots.length) id = m.snapshots[0].id;
    if (id) {
      await loadMonitoringSnapshot(id);
      return;
    }
    m.current = null;
    m.lines = [];
    m.allLines = [];
    m.selectedId = null;
    m.loading = false;
    renderMonitoringView(true);
  } catch (e) {
    m.loading = false;
    showToast(e.message || 'Chargement impossible.', 'error');
    renderMonitoringView(true);
  }
}

async function monitoringImportFile(file) {
  const m = monEnsureState();
  m.importing = true;
  renderMonitoringView(true);
  try {
    const fd = new FormData();
    fd.append('file', file);
    const r = await apiUpload('/api/reconciliation/import', fd);
    const msg = 'Snapshot enregistré'
      + (r.nb_ecarts != null ? ' — ' + r.nb_ecarts + ' écart(s)' : '')
      + '.';
    showToast(msg);
    await loadMonitoring(r.snapshot_id);
  } catch (e) {
    console.error('reconciliation import:', e.message, e);
    const msg = (e && e.message) ? String(e.message) : 'Import impossible.';
    showToast(msg.length > 220 ? msg.slice(0, 217) + '…' : msg, 'error');
    S.toast = { message: msg, type: 'error' };
    renderToast();
    setTimeout(() => { S.toast = null; renderToast(); }, 10000);
  } finally {
    m.importing = false;
    renderMonitoringView(true);
  }
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

// ── Valorisation stock (Contrôle) ────────────────────────────────

function valEnsureState() {
  if (!S.valorisation) {
    S.valorisation = {
      items: [],
      summary: null,
      loading: false,
      query: '',
      filterCategorie: null,
      filterSousSection: null,
      sortColumn: null,
      sortDirection: 'asc',
      historique: null,    // { matiere, historique }
      historiqueLoading: false,
      exporting: false,
      mpCollapsed: false,
      pfCollapsed: false,
      snapshotDate: null };
  }
  return S.valorisation;
}

async function loadValorisation() {
  const v = valEnsureState();
  v.loading = true;
  renderValorisationView(false);
  try {
    const qs = v.snapshotDate ? ('?date=' + encodeURIComponent(v.snapshotDate)) : '';
    const data = await api('/api/stock/valorisation' + qs);
    v.items = Array.isArray(data?.items) ? data.items : [];
    v.summary = data?.summary || null;
  } catch (e) {
    v.items = [];
    v.summary = null;
    showToast('Erreur de chargement : ' + (e?.message || 'inconnue'), 'danger');
  } finally {
    v.loading = false;
    renderValorisationView(true);
  }
}

function valCanSeeUSD() {
  // Direction + superadmin uniquement voient la colonne « Prix unit. réel » et le KPI dédoublé.
  return !!(S.user && (S.user.role === 'superadmin' || S.user.role === 'direction'));
}

function valAbbrUnite(u) {
  // Abréviations pour gagner de la place dans la table (palette → pal., bobine → bob.).
  const s = (u || '').toLowerCase();
  if (s === 'palette') return 'pal.';
  if (s === 'bobine') return 'bob.';
  if (s === 'unite' || s === 'unité') return 'u.';
  return s || '';
}

function valFormatPrixDetail(n) {
  // Comme valFormatEuroDetail mais sans unité (pour composer le sous-titre).
  const num = Number(n || 0);
  return num.toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 4 });
}

function valFormatEuro(n) {
  // Pas de décimales inutiles : 3 840,00 → 3 840 ; 3 840,50 → 3 840,5 ; 2,72 → 2,72.
  const num = Number(n || 0);
  return num.toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 2 }) + ' €';
}

function valFormatEuroDetail(n) {
  // Idem pour les prix unitaires fins : 3,2000 → 3,2 ; 3,2500 → 3,25 ; 0,8945 → 0,8945.
  const num = Number(n || 0);
  return num.toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 4 }) + ' €';
}

function valFormatQte(n) {
  const num = Number(n || 0);
  return num.toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}

function valFormatDate(s) {
  if (!s) return '—';
  try {
    const dt = new Date(s);
    if (isNaN(dt.getTime())) return s;
    return dt.toLocaleDateString('fr-FR') + ' ' + dt.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  } catch (e) { return s; }
}

function valFilteredItems() {
  const v = valEnsureState();
  let rows = v.items || [];
  if (v.filterCategorie) {
    rows = rows.filter(r => r.categorie === v.filterCategorie);
  }
  // Filtre sous_section (seulement pour frontal). v.filterSousSection peut être :
  // - une string non vide → match exact (case-insensitive)
  // - '' (string vide) → frontaux sans sous_section
  // - null → pas de filtre
  if (v.filterCategorie === 'frontal' && v.filterSousSection !== null) {
    const fss = String(v.filterSousSection).toLowerCase();
    rows = rows.filter(r => {
      const ss = (r.sous_section || '').trim().toLowerCase();
      return ss === fss;
    });
  }
  const q = (v.query || '').trim().toLowerCase();
  if (q) {
    rows = rows.filter(r =>
      (r.reference || '').toLowerCase().includes(q) ||
      (r.designation || '').toLowerCase().includes(q) ||
      (r.categorie_label || '').toLowerCase().includes(q)
    );
  }
  if (v.sortColumn) {
    rows = rows.slice().sort((a, b) => {
      let va, vb;
      switch (v.sortColumn) {
        case 'reference': va = (a.reference || '').toLowerCase(); vb = (b.reference || '').toLowerCase(); break;
        case 'designation': va = (a.designation || '').toLowerCase(); vb = (b.designation || '').toLowerCase(); break;
        case 'categorie': va = (a.categorie_label || '').toLowerCase(); vb = (b.categorie_label || '').toLowerCase(); break;
        case 'quantite': va = Number(a.quantite || 0); vb = Number(b.quantite || 0); break;
        case 'prix_unitaire': va = Number(a.prix_unitaire || 0); vb = Number(b.prix_unitaire || 0); break;
        case 'prix_unitaire_reel': va = Number(a.prix_unitaire_reel || a.prix_unitaire || 0); vb = Number(b.prix_unitaire_reel || b.prix_unitaire || 0); break;
        case 'valorisation': va = Number(a.valorisation || 0); vb = Number(b.valorisation || 0); break;
        default: va = 0; vb = 0;
      }
      if (va < vb) return v.sortDirection === 'asc' ? -1 : 1;
      if (va > vb) return v.sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }
  return rows;
}

function valToggleSort(column) {
  const v = valEnsureState();
  if (v.sortColumn === column) {
    v.sortDirection = v.sortDirection === 'asc' ? 'desc' : 'asc';
  } else {
    v.sortColumn = column;
    v.sortDirection = 'asc';
  }
  renderValorisationView(true);
}

function buildValorisationKpis() {
  const v = valEnsureState();
  const pf = (S.valorisation && S.valorisation.pf) ? S.valorisation.pf : null;
  const s = v.summary || { total_mp: 0, total_pf: 0, total_global: 0, nb_refs: 0, nb_refs_valorisees: 0 };
  const pfS = (pf && pf.summary) ? pf.summary : null;
  const pfLoaded = !!pfS;
  const totalMP = Number(s.total_mp || 0);
  const totalPF = pfLoaded ? Number(pfS.total_pf || 0) : 0;
  const totalGlobal = totalMP + totalPF;

  // Dédoublement (Direction / superadmin), affiché si au moins un flag (USD, taxe, transport) actif.
  const canSeeUSD = valCanSeeUSD();
  const nbUsdOnly = Number(s.nb_refs_usd_only || 0);
  const nbTaxOnly = Number(s.nb_refs_tax_only || 0);
  const nbBoth = Number(s.nb_refs_usd_and_tax || 0);
  const nbTransport = Number(s.nb_refs_transport || 0);
  const tauxRaw = Number(s.taux_eur_usd || 0);
  const taxPctRaw = Number(s.import_tax_pct || 0);
  const transportRaw = Number(s.transport_cost_fixed_eur || 0);
  const showReelBreakdown = canSeeUSD
    && (nbUsdOnly + nbTaxOnly + nbBoth + nbTransport) > 0
    && (tauxRaw > 0 || taxPctRaw > 0 || transportRaw > 0);
  const totalMPReel = Number(s.total_mp_reel || s.total_mp || 0);
  // pfHasCharges est calculé plus bas mais nécessaire ici pour le total réel — on le
  // dérive directement à partir de pfS pour éviter la dépendance sur la variable.
  const _pfCharge = pfLoaded ? Number(pfS.charge_production_pct || 0) : 0;
  const _pfStorage = pfLoaded ? Number(pfS.storage_fees_pct || 0) : 0;
  const _pfHasCharges = canSeeUSD && pfLoaded && (_pfCharge > 0 || _pfStorage > 0);
  const totalPFReel = _pfHasCharges ? Number(pfS.total_pf_avec_charges || 0) : totalPF;
  const totalGlobalReel = totalMPReel + totalPFReel;

  const wrap = el('div', { cls: 'val-kpis', style:
    'display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin-bottom:16px;' });

  // Helpers d'affichage des sous-totaux d'un KPI
  const tauxTxt = tauxRaw > 0 ? '1 USD = ' + tauxRaw.toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 4 }) + ' €' : null;
  const taxTxt = taxPctRaw > 0 ? 'Taxe import. ' + taxPctRaw.toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 2 }) + ' %' : null;
  const transportTxt = transportRaw > 0 ? 'Transport ' + transportRaw.toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 2 }) + ' €/réf.' : null;
  const buildBreakdownLabel = () => {
    // Compteurs indépendants par flag (les mêmes lignes peuvent apparaître dans plusieurs).
    const parts = [];
    const nbUsd = nbUsdOnly + nbBoth;
    const nbTax = nbTaxOnly + nbBoth;
    if (nbUsd > 0) parts.push(nbUsd + ' USD');
    if (nbTax > 0) parts.push(nbTax + ' taxées');
    if (nbTransport > 0) parts.push(nbTransport + ' transport');
    return parts.join(' · ');
  };

  // ── Total global ──────────────────────────────────────────────
  // Chiffre recalculé en gros vert au-dessus, chiffre d'origine plus discret dessous
  // dès qu'un breakdown est actif (MP réel OU PF avec charges).
  const totalHasBreakdown = showReelBreakdown || _pfHasCharges;
  const kpiTotalChildren = [
    el('div', { style: 'font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px' }, 'Stock valorisé — Total'),
  ];
  if (totalHasBreakdown) {
    kpiTotalChildren.push(
      el('div', { style: 'font-size:24px;font-weight:800;color:#16a34a' }, valFormatEuro(totalGlobalReel))
    );
    kpiTotalChildren.push(
      el('div', { style: 'font-size:15px;font-weight:700;color:var(--muted);margin-top:4px;display:flex;align-items:baseline;gap:6px' },
        el('span', null, valFormatEuro(totalGlobal)),
        el('span', { style: 'font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.3px' }, 'base')
      )
    );
  } else {
    kpiTotalChildren.push(
      el('div', { style: 'font-size:24px;font-weight:800;color:var(--accent)' }, valFormatEuro(totalGlobal))
    );
  }
  kpiTotalChildren.push(
    el('div', { style: 'font-size:11px;color:var(--muted);margin-top:6px' },
      pfLoaded ? 'MP + PF' : 'MP + PF (chargement PF…)')
  );
  const kpiTotal = el('div', { style:
    'background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px 18px;' },
    ...kpiTotalChildren
  );

  // ── Matières premières — dédoublé EUR / réel si réfs USD ou taxe ──
  // Position inversée quand un breakdown est actif : réel en gros vert au-dessus.
  const kpiMPChildren = [
    el('div', { style: 'font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px' }, 'Matières premières'),
  ];
  if (showReelBreakdown) {
    kpiMPChildren.push(
      el('div', { style: 'font-size:24px;font-weight:800;color:#16a34a' }, valFormatEuro(totalMPReel))
    );
    kpiMPChildren.push(
      el('div', { style: 'font-size:15px;font-weight:700;color:var(--muted);margin-top:4px;display:flex;align-items:baseline;gap:6px' },
        el('span', null, valFormatEuro(totalMP)),
        el('span', { style: 'font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.3px' }, 'base')
      )
    );
    const refsLabel = buildBreakdownLabel();
    const subPieces = [
      `${s.nb_refs_valorisees || 0} / ${s.nb_refs || 0} références valorisées`,
    ];
    if (refsLabel) subPieces.push(refsLabel);
    if (tauxTxt) subPieces.push(tauxTxt);
    if (taxTxt) subPieces.push(taxTxt);
    if (transportTxt) subPieces.push(transportTxt);
    kpiMPChildren.push(
      el('div', { style: 'font-size:11px;color:var(--muted);margin-top:6px;line-height:1.5' },
        subPieces.join(' · ')
      )
    );
  } else {
    const subPieces = [`${s.nb_refs_valorisees || 0} / ${s.nb_refs || 0} références valorisées`];
    if (canSeeUSD && tauxTxt) subPieces.push(tauxTxt);
    if (canSeeUSD && taxTxt) subPieces.push(taxTxt);
    if (canSeeUSD && transportTxt) subPieces.push(transportTxt);
    kpiMPChildren.push(
      el('div', { style: 'font-size:11px;color:var(--muted);margin-top:6px' },
        subPieces.join(' · ')
      )
    );
  }
  const kpiMP = el('div', { style:
    'background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px 18px;' },
    ...kpiMPChildren
  );

  const pfChargePct = _pfCharge;
  const pfStoragePct = _pfStorage;
  const pfHasCharges = _pfHasCharges;
  const pfTotalAvecCharges = pfLoaded ? Number(pfS.total_pf_avec_charges || 0) : 0;

  // Position inversée quand charges activées : « avec charges » en gros vert, base dessous.
  const kpiPFChildren = [
    el('div', { style: 'font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px' }, 'Produits finis'),
  ];
  if (pfHasCharges) {
    kpiPFChildren.push(
      el('div', { style: 'font-size:24px;font-weight:800;color:#16a34a' }, valFormatEuro(pfTotalAvecCharges))
    );
    kpiPFChildren.push(
      el('div', { style: 'font-size:15px;font-weight:700;color:var(--muted);margin-top:4px;display:flex;align-items:baseline;gap:6px' },
        el('span', null, valFormatEuro(totalPF)),
        el('span', { style: 'font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.3px' }, 'base')
      )
    );
  } else {
    kpiPFChildren.push(
      el('div', { style: 'font-size:24px;font-weight:800;color:var(--text)' }, pfLoaded ? valFormatEuro(totalPF) : '—')
    );
  }
  const pfSubPieces = [];
  if (pfLoaded) {
    pfSubPieces.push(`${pfS.nb_refs_valorisees || 0} / ${pfS.nb_refs || 0} références valorisées`);
    if (canSeeUSD && pfChargePct > 0) {
      pfSubPieces.push('Charge prod. ' + pfChargePct.toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 2 }) + ' %');
    }
    if (canSeeUSD && pfStoragePct > 0) {
      pfSubPieces.push('Stockage ' + pfStoragePct.toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 2 }) + ' %');
    }
  } else {
    pfSubPieces.push('Chargement…');
  }
  kpiPFChildren.push(
    el('div', { style: 'font-size:11px;color:var(--muted);margin-top:6px;line-height:1.5' },
      pfSubPieces.join(' · '))
  );

  const kpiPF = el('div', { style:
    'background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px 18px;' + (pfLoaded ? '' : 'opacity:.55') },
    ...kpiPFChildren
  );

  wrap.append(kpiTotal, kpiMP, kpiPF);
  return wrap;
}

function buildValorisationCategoriePills() {
  const v = valEnsureState();
  const s = v.summary || { categories: [] };
  const cats = s.categories || [];
  const items = v.items || [];
  const wrap = el('div', { style:
    'display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px;align-items:center' });

  const base = 'padding:7px 14px;border-radius:999px;border:1px solid var(--border);background:transparent;color:var(--text2);font-size:12px;font-weight:600;cursor:pointer;transition:all .15s;display:inline-flex;align-items:center;gap:6px';
  const active = 'padding:7px 14px;border-radius:999px;border:1px solid var(--accent);background:var(--accent-bg);color:var(--accent);font-size:12px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:6px';

  // Précalcule les totaux par sous-section frontal (à partir des items)
  const frontalBySs = new Map(); // ss(lowercase) → { label, total }
  let frontalSansSsTotal = 0;
  let hasFrontalSansSs = false;
  items.forEach(it => {
    if (String(it.categorie || '').toLowerCase() !== 'frontal') return;
    const ssRaw = (it.sous_section || '').trim();
    if (!ssRaw) {
      frontalSansSsTotal += Number(it.valorisation || 0);
      hasFrontalSansSs = true;
      return;
    }
    const k = ssRaw.toLowerCase();
    if (!frontalBySs.has(k)) frontalBySs.set(k, { label: ssRaw, total: 0 });
    frontalBySs.get(k).total += Number(it.valorisation || 0);
  });
  const frontalSsList = Array.from(frontalBySs.values())
    .sort((a, b) => a.label.localeCompare(b.label, 'fr'));

  // Couleurs frontales par slug
  const frontalAccent = (slug) => (
    slug === 'couche' ? '#0284c7'
    : slug === 'synthetique' ? '#0891b2'
    : slug === 'thermiques' ? '#4f46e5'
    : slug === 'velin' ? '#1e3a8a'
    : 'var(--accent)'
  );
  const frontalActiveStyle = (color) =>
    'padding:7px 14px;border-radius:999px;border:1px solid ' + color
    + ';background:' + color + '14;color:' + color
    + ';font-size:12px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:6px';

  const allBtn = el('button', {
    type: 'button', style: (v.filterCategorie === null) ? active : base,
    on: { click: () => {
      v.filterCategorie = null; v.filterSousSection = null; renderValorisationView(true);
    } } }, 'Toutes catégories',
    el('span', { style: 'opacity:.7;font-weight:600' }, '· ' + valFormatEuro(s.total_mp))
  );
  wrap.appendChild(allBtn);

  cats.forEach(c => {
    if (c.categorie === 'frontal' && frontalSsList.length > 0) {
      // Eclatement par sous-section
      frontalSsList.forEach(ss => {
        const slug = mpSousSectionSlug(ss.label);
        const color = frontalAccent(slug);
        const isActive = v.filterCategorie === 'frontal'
          && v.filterSousSection !== null
          && String(v.filterSousSection).toLowerCase() === ss.label.toLowerCase();
        const styleStr = isActive ? frontalActiveStyle(color) : base;
        const btn = el('button', {
          type: 'button', style: styleStr,
          on: { click: () => {
            if (isActive) {
              v.filterCategorie = null; v.filterSousSection = null;
            } else {
              v.filterCategorie = 'frontal'; v.filterSousSection = ss.label;
            }
            renderValorisationView(true);
          } } }, ss.label,
          el('span', { style: 'opacity:.7;font-weight:600' }, '· ' + valFormatEuro(ss.total))
        );
        wrap.appendChild(btn);
      });
      // Pill "Sans sous-section" seulement s'il existe des frontaux sans SS
      if (hasFrontalSansSs) {
        const isActive = v.filterCategorie === 'frontal' && v.filterSousSection === '';
        const btn = el('button', {
          type: 'button', style: isActive ? active : base,
          on: { click: () => {
            if (isActive) {
              v.filterCategorie = null; v.filterSousSection = null;
            } else {
              v.filterCategorie = 'frontal'; v.filterSousSection = '';
            }
            renderValorisationView(true);
          } } }, 'Frontal (sans sous-section)',
          el('span', { style: 'opacity:.7;font-weight:600' }, '· ' + valFormatEuro(frontalSansSsTotal))
        );
        wrap.appendChild(btn);
      }
    } else {
      const isActive = v.filterCategorie === c.categorie && v.filterSousSection === null;
      const btn = el('button', {
        type: 'button', style: isActive ? active : base,
        on: { click: () => {
          if (isActive) {
            v.filterCategorie = null; v.filterSousSection = null;
          } else {
            v.filterCategorie = c.categorie; v.filterSousSection = null;
          }
          renderValorisationView(true);
        } } }, c.categorie_label,
        el('span', { style: 'opacity:.7;font-weight:600' }, '· ' + valFormatEuro(c.total))
      );
      wrap.appendChild(btn);
    }
  });
  return wrap;
}

async function toggleValorisationUSD(matiereId) {
  const v = valEnsureState();
  try {
    const data = await api('/api/stock/valorisation/' + matiereId + '/prix-en-usd', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    // Mise à jour locale : toutes les lignes (matières laizées : plusieurs lignes par matière)
    if (data?.items_matiere && Array.isArray(data.items_matiere)) {
      const newByKey = new Map(data.items_matiere.map(x => [x.row_key, x]));
      v.items = (v.items || []).map(x => newByKey.has(x.row_key) ? newByKey.get(x.row_key) : x);
    }
    if (data?.summary) v.summary = data.summary;
    renderValorisationView(true);
    showToast(data.prix_en_usd ? 'Référence marquée USD.' : 'Conversion USD retirée.', 'success');
  } catch (e) {
    showToast('Erreur : ' + (e?.message || 'changement impossible'), 'danger');
  }
}

async function toggleValorisationTransport(matiereId) {
  const v = valEnsureState();
  try {
    const data = await api('/api/stock/valorisation/' + matiereId + '/cout-transport', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    if (data?.items_matiere && Array.isArray(data.items_matiere)) {
      const newByKey = new Map(data.items_matiere.map(x => [x.row_key, x]));
      v.items = (v.items || []).map(x => newByKey.has(x.row_key) ? newByKey.get(x.row_key) : x);
    }
    if (data?.summary) v.summary = data.summary;
    renderValorisationView(true);
    const st = Number(data?.cout_transport_inclus || 0);
    const msg = st === 1 ? 'Transport container complet appliqué.'
      : st === 2 ? 'Transport demi-container appliqué.'
      : 'Transport retiré.';
    showToast(msg, 'success');
  } catch (e) {
    showToast('Erreur : ' + (e?.message || 'changement impossible'), 'danger');
  }
}

async function toggleValorisationTaxe(matiereId) {
  const v = valEnsureState();
  try {
    const data = await api('/api/stock/valorisation/' + matiereId + '/taxe-importation', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    if (data?.items_matiere && Array.isArray(data.items_matiere)) {
      const newByKey = new Map(data.items_matiere.map(x => [x.row_key, x]));
      v.items = (v.items || []).map(x => newByKey.has(x.row_key) ? newByKey.get(x.row_key) : x);
    }
    if (data?.summary) v.summary = data.summary;
    renderValorisationView(true);
    showToast(data.taxe_importation ? 'Taxe d\'importation appliquée.' : 'Taxe d\'importation retirée.', 'success');
  } catch (e) {
    showToast('Erreur : ' + (e?.message || 'changement impossible'), 'danger');
  }
}

async function saveValorisationPrice(matiereId, newPrice, inputEl) {
  const v = valEnsureState();
  try {
    const data = await api('/api/stock/valorisation/' + matiereId, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prix_unitaire: newPrice }) });
    // Mise à jour locale silencieuse (pas de full re-render pour préserver le focus)
    if (data?.item) {
      const idx = v.items.findIndex(x => x.id === matiereId);
      if (idx >= 0) v.items[idx] = data.item;
    }
    if (data?.summary) v.summary = data.summary;
    // Met à jour les cellules dépendantes (valorisation ligne + KPIs + pills)
    renderValorisationView(true);
    showToast('Prix enregistré.', 'success');
  } catch (e) {
    showToast('Erreur : ' + (e?.message || 'enregistrement impossible'), 'danger');
    // Restaurer l'ancienne valeur si possible
    if (inputEl) {
      const item = v.items.find(x => x.id === matiereId);
      if (item) inputEl.value = (Number(item.prix_unitaire) || 0).toString().replace('.', ',');
    }
  }
}

function buildValorisationTableRow(item) {
  const rowKey = item.row_key || ('m' + item.id);
  const tr = el('tr', { 'data-row-key': rowKey, style: 'border-bottom:1px solid var(--border)' });

  const tdCat = el('td', { style: 'padding:10px 12px;font-size:12px;color:var(--text2)' });
  // Badge catégorie avec teinte bleue selon la sous-section pour les frontaux
  const badge = dashMpCatBadge(item.categorie, item.sous_section);
  tdCat.appendChild(badge);

  const refLabel = item.reference || '';
  const matiereId = item.matiere_id || item.id;
  const refLink = stockMpRefLink(matiereId, refLabel, {
    title: 'Ouvrir la matière',
    style: 'text-decoration:none;color:var(--text);font-weight:800;font-family:monospace;font-size:13px',
  });
  const refChildren = [refLink];
  if (item.laizee && item.laize_label) {
    refChildren.push(el('span', { style:
      'display:inline-block;margin-left:8px;padding:2px 8px;border-radius:6px;background:rgba(34,211,238,0.10);color:var(--accent);font-size:11px;font-weight:600;letter-spacing:.2px;font-family:inherit' },
      item.laize_label));
  } else if (item.laizee && item.incomplete) {
    refChildren.push(el('span', { style:
      'display:inline-block;margin-left:8px;padding:2px 8px;border-radius:6px;background:rgba(251,146,60,0.15);color:#fb923c;font-size:11px;font-weight:700;font-family:inherit' },
      'Aucune laize'));
  }
  const tdRef = el('td', { style: 'padding:10px 12px;font-size:13px;font-weight:700;color:var(--text);font-family:monospace' }, ...refChildren);
  const desText = item.designation || '';
  const tdDes = el('td', { style: 'padding:10px 12px;font-size:13px;color:var(--text2)' }, desText);
  const tdQte = el('td', { style: 'padding:10px 12px;font-size:13px;color:var(--text);text-align:right;font-variant-numeric:tabular-nums' },
    valFormatQte(item.quantite),
    el('span', { style: 'margin-left:5px;font-size:11px;color:var(--muted);font-weight:500' }, item.unite || '')
  );

  let tdPrix;
  if (item.laizee) {
    // Pour les matières laizées : prix unitaire = valorisation_bobine (lecture seule)
    // + bouton "Paramètres" pour éditer prix m² + métrage au niveau matière
    let display;
    if (item.incomplete) {
      display = el('span', { style: 'color:#fb923c;font-size:12px;font-weight:700' }, 'À configurer');
    } else if ((item.prix_unitaire || 0) > 0) {
      display = valFormatEuroDetail(item.prix_unitaire) + ' /bob.';
    } else {
      display = el('span', { style: 'color:var(--muted)' }, 'non valorisé');
    }
    const params = el('div', { style: 'font-size:10px;color:var(--muted);margin-top:2px' },
      (item.prix_eur_m2 || 0) > 0 ? (item.prix_eur_m2.toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 4 }) + ' €/m²') : 'prix m² ?',
      ' · ',
      (item.metres_lineaires_par_bobine || 0) > 0 ? (item.metres_lineaires_par_bobine.toLocaleString('fr-FR') + ' m') : 'métrage ?',
    );
    const editBtn = el('button', {
      type: 'button', title: 'Éditer prix m² et métrage',
      style: 'background:transparent;border:1px solid var(--border);border-radius:6px;padding:4px 8px;cursor:pointer;color:var(--text2);font-size:11px;margin-top:4px;display:inline-flex;align-items:center;gap:4px',
      on: { click: () => openValorisationParamsModal(item.matiere_id) },
    });
    editBtn.appendChild(iconEl('edit', 11));
    editBtn.appendChild(el('span', null, 'Modifier'));
    tdPrix = el('td', { style: 'padding:10px 12px;text-align:right' },
      el('div', { style: 'display:flex;flex-direction:column;align-items:flex-end' },
        el('div', { style: 'font-size:13px;font-weight:600;color:var(--text);font-variant-numeric:tabular-nums' }, display),
        params,
        editBtn,
      )
    );
  } else if (item.avec_conditionnement) {
    // Cartons / Adhésifs / Mandrins : prix saisi = prix à l'unité d'achat,
    // affichage style frontal (prix palette calculé + sous-titre + bouton Modifier).
    const upp = Number(item.unites_par_palette || 0);
    const prixUnit = Number(item.prix_unitaire || 0);
    const prixPal = Number(item.prix_palette || (upp * prixUnit));
    const uniteAchat = item.unite_achat || 'unité';
    let display;
    if (item.incomplete || upp <= 0 || prixUnit <= 0) {
      display = el('span', { style: 'color:#fb923c;font-size:12px;font-weight:700' }, 'À configurer');
    } else {
      display = valFormatEuroDetail(prixPal) + ' /pal.';
    }
    const prixUnitTxt = prixUnit > 0
      ? (prixUnit.toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 4 }) + ' €/' + uniteAchat)
      : 'prix unité ?';
    const upTxt = upp > 0
      ? (upp.toLocaleString('fr-FR') + ' ' + uniteAchat + '/pal.')
      : 'conditionnement ?';
    const params = el('div', { style: 'font-size:10px;color:var(--muted);margin-top:2px' },
      prixUnitTxt, ' · ', upTxt);
    const editBtn = el('button', {
      type: 'button', title: 'Éditer prix unitaire et conditionnement',
      style: 'background:transparent;border:1px solid var(--border);border-radius:6px;padding:4px 8px;cursor:pointer;color:var(--text2);font-size:11px;margin-top:4px;display:inline-flex;align-items:center;gap:4px',
      on: { click: () => openValorisationConditionnementModal(item.matiere_id || item.id) },
    });
    editBtn.appendChild(iconEl('edit', 11));
    editBtn.appendChild(el('span', null, 'Modifier'));
    tdPrix = el('td', { style: 'padding:10px 12px;text-align:right' },
      el('div', { style: 'display:flex;flex-direction:column;align-items:flex-end' },
        el('div', { style: 'font-size:13px;font-weight:600;color:var(--text);font-variant-numeric:tabular-nums' }, display),
        params,
        editBtn,
      )
    );
  } else {
    const inpId = 'val-price-' + rowKey;
    const inp = el('input', {
      type: 'text', id: inpId, value: (Number(item.prix_unitaire) || 0).toString().replace('.', ','),
        inputmode: 'decimal',
        style: 'width:110px;padding:6px 8px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text);font-size:13px;font-variant-numeric:tabular-nums;text-align:right;transition:border-color .15s' });
    const commit = async () => {
      const raw = (inp.value || '').trim().replace(/\s/g, '').replace(',', '.');
      const num = parseFloat(raw);
      const current = Number(item.prix_unitaire) || 0;
      if (isNaN(num) || num < 0) {
        inp.value = current.toString().replace('.', ',');
        showToast('Prix invalide.', 'danger');
        return;
      }
      if (Math.abs(num - current) < 0.00001) return;
      await saveValorisationPrice(item.matiere_id || item.id, num, inp);
    };
    inp.addEventListener('blur', commit);
    inp.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); inp.blur(); }
      if (e.key === 'Escape') {
        inp.value = (Number(item.prix_unitaire) || 0).toString().replace('.', ',');
        inp.blur();
      }
    });
    inp.addEventListener('focus', () => inp.select());
    tdPrix = el('td', { style: 'padding:10px 12px;text-align:right' },
      inp,
      el('span', { style: 'margin-left:6px;font-size:11px;color:var(--muted)' }, '€/' + (item.unite || ''))
    );
  }

  // "Valorisée" = prix > 0 ET (si conditionnement requis) unites_par_palette > 0
  const valored = (item.prix_unitaire || 0) > 0
    && (!item.avec_conditionnement || (item.unites_par_palette || 0) > 0);
  const valColor = valored ? 'var(--text)' : 'var(--muted)';
  // Une ligne est « réelle » dès qu'au moins un flag (USD, taxe ou transport) est actif
  // ET produit un ajustement (multiplicateur ≠ 1 OU forfait transport > 0).
  const hasReel = valored
    && (item.prix_en_usd || item.taxe_importation || item.cout_transport_inclus)
    && (Number(item.valorisation_reelle || 0) > 0 || Number(item.transport_addon_eur || 0) > 0)
    && Math.abs(Number(item.valorisation_reelle) - Number(item.valorisation)) > 0.005;
  let tdVal;
  if (hasReel) {
    // Empilement : ancienne valorisation barrée (petite, muted) + valorisation réelle (vert gras).
    tdVal = el('td', { style: 'padding:10px 12px;text-align:right;font-variant-numeric:tabular-nums' },
      el('div', { style: 'display:flex;flex-direction:column;align-items:flex-end;line-height:1.2' },
        el('div', {
          style: 'font-size:11px;font-weight:500;color:var(--muted);text-decoration:line-through;text-decoration-color:var(--muted)'
        }, valFormatEuro(item.valorisation)),
        el('div', { style: 'font-size:13px;font-weight:800;color:#16a34a;margin-top:1px' },
          valFormatEuro(item.valorisation_reelle))
      )
    );
  } else {
    tdVal = el('td', { style: 'padding:10px 12px;font-size:13px;font-weight:700;text-align:right;font-variant-numeric:tabular-nums;color:' + valColor },
      valored ? valFormatEuro(item.valorisation) : '—'
    );
  }

  // ── Colonne « Prix unit. réel » : visible uniquement Direction / superadmin ──
  // Mêmes proportions que Prix unitaire (main /pal. + sous-titre €/kg · kg/pal.) mais
  // en vert et sans bouton Modifier. Affichée dès que le prix unitaire diffère de la
  // base (USD, taxe adhésif, ou supplément transport container appliqué).
  const canSeeUSD = valCanSeeUSD();
  const hasPriceMult = valored
    && Number(item.prix_unitaire_reel || 0) > 0
    && Math.abs(Number(item.prix_unitaire_reel) - Number(item.prix_unitaire)) > 0.00005;
  const hasTransportAddon = Number(item.cout_transport_inclus || 0) > 0
    && Number(item.transport_addon_eur || 0) > 0;
  let tdPrixReel = null;
  if (canSeeUSD) {
    if (hasPriceMult) {
      const uniteAbbr = valAbbrUnite(item.unite);
      let mainTxt;
      const subPieces = [];

      if (item.laizee) {
        // Frontal / glassine / complexe : prix réel /bob. + €/m² · m
        const reelBob = Number(item.prix_unitaire_reel || 0);
        const p_m2_reel = Number(item.prix_eur_m2_reel || 0);
        const metres = Number(item.metres_lineaires_par_bobine || 0);
        mainTxt = valFormatEuroDetail(reelBob) + ' /bob.';
        if (p_m2_reel > 0) subPieces.push(valFormatPrixDetail(p_m2_reel) + ' €/m²');
        if (metres > 0) subPieces.push(metres.toLocaleString('fr-FR') + ' m');
      } else if (item.avec_conditionnement) {
        // Cartons / adhésifs / mandrins : prix réel /pal. + €/unité_achat · unités/pal.
        const upp = Number(item.unites_par_palette || 0);
        const prixUnitReel = Number(item.prix_unitaire_reel || 0);
        const prixPalReel = prixUnitReel * upp;
        const uniteAchat = item.unite_achat || 'unité';
        mainTxt = valFormatEuroDetail(prixPalReel) + ' /pal.';
        if (prixUnitReel > 0) subPieces.push(valFormatPrixDetail(prixUnitReel) + ' €/' + uniteAchat);
        if (upp > 0) subPieces.push(upp.toLocaleString('fr-FR') + ' ' + uniteAchat + '/pal.');
      } else {
        // Palette / autre : prix réel /unité de gestion (abrégée)
        const reel = Number(item.prix_unitaire_reel || 0);
        mainTxt = valFormatEuroDetail(reel) + (uniteAbbr ? ' /' + uniteAbbr : '');
      }

      const reelChildren = [
        el('div', { style: 'font-size:13px;font-weight:700;color:#16a34a;font-variant-numeric:tabular-nums;white-space:nowrap' }, mainTxt),
      ];
      if (subPieces.length) {
        reelChildren.push(el('div', {
          style: 'font-size:10px;color:#16a34a;opacity:.75;margin-top:2px;white-space:nowrap'
        }, subPieces.join(' · ')));
      }
      // Supplément transport container : sous-titre indiquant le type (plein ou demi)
      if (hasTransportAddon) {
        const trState = Number(item.cout_transport_inclus || 0);
        const label = trState === 2 ? 'demi-container' : 'container plein';
        reelChildren.push(el('div', {
          style: 'font-size:10px;color:#16a34a;font-weight:700;margin-top:1px;white-space:nowrap'
        }, '+ ' + valFormatEuro(item.transport_addon_eur) + ' transport ' + label));
      }
      tdPrixReel = el('td', { style: 'padding:10px 12px;text-align:right' },
        el('div', { style: 'display:flex;flex-direction:column;align-items:flex-end' }, ...reelChildren)
      );
    } else {
      tdPrixReel = el('td', {
        style: 'padding:10px 12px;text-align:right;font-size:13px;color:var(--muted);font-variant-numeric:tabular-nums'
      }, '—');
    }
  }

  // ── Colonne « Actions » ──
  // Action 1 : horloge → historique des prix
  // Action 2 : $ → toggle prix_en_usd (vert si actif)
  // Action 3 : package → toggle taxe_importation (vert si actif)
  const histBtn = el('button', {
    type: 'button', title: 'Voir l\'historique des prix de cette référence',
    style: 'background:transparent;border:1px solid var(--border);border-radius:8px;width:28px;height:28px;display:inline-flex;align-items:center;justify-content:center;cursor:pointer;color:var(--text2);transition:all .15s',
    on: {
      click: () => openValorisationHistorique(item.matiere_id || item.id),
      mouseenter: (e) => { e.currentTarget.style.background = 'var(--bg)'; e.currentTarget.style.color = 'var(--text)'; },
      mouseleave: (e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text2)'; },
    },
  });
  histBtn.appendChild(iconEl('clock', 14));

  const actionsChildren = [histBtn];
  if (canSeeUSD) {
    // -- Action USD --
    const usdOn = !!item.prix_en_usd;
    const tauxRaw = Number((S.valorisation && S.valorisation.summary && S.valorisation.summary.taux_eur_usd) || 0);
    const tauxTxt = tauxRaw > 0 ? tauxRaw.toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 4 }) : null;
    const usdTitle = usdOn
      ? 'Référence USD — cliquer pour repasser en saisie EUR'
      + (tauxTxt ? ' (taux courant 1 USD = ' + tauxTxt + ' €)' : '')
      : 'Marquer cette référence comme saisie en USD'
      + (tauxTxt ? ' — le prix réel sera multiplié par 1 USD = ' + tauxTxt + ' €' : ' — taux EUR/USD à configurer dans Paramètres');
    const usdBtn = el('button', {
      type: 'button', title: usdTitle,
      style:
        'border-radius:8px;width:28px;height:28px;display:inline-flex;align-items:center;justify-content:center;cursor:pointer;transition:all .15s;'
        + (usdOn
            ? 'background:rgba(34,197,94,0.12);border:1px solid #16a34a;color:#16a34a'
            : 'background:transparent;border:1px solid var(--border);color:var(--text2)'),
      on: {
        click: () => toggleValorisationUSD(item.matiere_id || item.id),
        mouseenter: (e) => {
          if (!usdOn) { e.currentTarget.style.background = 'var(--bg)'; e.currentTarget.style.color = 'var(--text)'; }
        },
        mouseleave: (e) => {
          if (!usdOn) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text2)'; }
        },
      },
    });
    usdBtn.appendChild(iconEl('dollar-sign', 14));
    actionsChildren.push(usdBtn);

    // -- Action Taxe d'importation (adhésifs uniquement) --
    const catLower = String(item.categorie || '').toLowerCase();
    if (catLower === 'adhesif') {
      const taxOn = !!item.taxe_importation;
      const taxRaw = Number((S.valorisation && S.valorisation.summary && S.valorisation.summary.import_tax_pct) || 0);
      const taxTxt = taxRaw > 0 ? taxRaw.toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 2 }) + ' %' : null;
      const taxTitle = taxOn
        ? 'Taxe d\'importation appliquée — cliquer pour la retirer'
        + (taxTxt ? ' (taux courant ' + taxTxt + ')' : '')
        : 'Appliquer la taxe d\'importation à cette référence'
        + (taxTxt ? ' (' + taxTxt + ')' : ' — taux à configurer dans Paramètres');
      const taxBtn = el('button', {
        type: 'button', title: taxTitle,
        style:
          'border-radius:8px;width:28px;height:28px;display:inline-flex;align-items:center;justify-content:center;cursor:pointer;transition:all .15s;'
          + (taxOn
              ? 'background:rgba(34,197,94,0.12);border:1px solid #16a34a;color:#16a34a'
              : 'background:transparent;border:1px solid var(--border);color:var(--text2)'),
        on: {
          click: () => toggleValorisationTaxe(item.matiere_id || item.id),
          mouseenter: (e) => {
            if (!taxOn) { e.currentTarget.style.background = 'var(--bg)'; e.currentTarget.style.color = 'var(--text)'; }
          },
          mouseleave: (e) => {
            if (!taxOn) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text2)'; }
          },
        },
      });
      taxBtn.appendChild(iconEl('package', 14));
      actionsChildren.push(taxBtn);
    }

    // -- Action Coût transport container (bobines uniquement : frontal, glassine, complexe) --
    // 3 états : 0 off (gris) → 1 container complet (camion vert) → 2 demi-container (½ camion vert) → 0
    if (catLower === 'frontal' || catLower === 'glassine' || catLower === 'complexe') {
      const trState = Number(item.cout_transport_inclus || 0);
      const summ = (S.valorisation && S.valorisation.summary) || {};
      const suppFull = Number(summ.container_supplement_eur_per_m2_full || 0);
      const suppHalf = Number(summ.container_supplement_eur_per_m2_half || 0);
      const fmtEur = (n) => n.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 4 });
      let trTitle;
      if (trState === 1) {
        trTitle = 'Transport container complet appliqué — cliquer pour passer au demi-container'
          + (suppFull > 0 ? ' (+ ' + fmtEur(suppFull) + ' €/m²)' : ' — coût container / qté m² à configurer');
      } else if (trState === 2) {
        trTitle = 'Transport demi-container appliqué — cliquer pour retirer le transport'
          + (suppHalf > 0 ? ' (+ ' + fmtEur(suppHalf) + ' €/m²)' : ' — coût demi-container / qté m² à configurer');
      } else {
        trTitle = 'Cliquer pour appliquer un transport container complet'
          + (suppFull > 0 ? ' (+ ' + fmtEur(suppFull) + ' €/m²)' : '');
      }
      const trActive = trState > 0;
      const trBtn = el('button', {
        type: 'button', title: trTitle,
        style:
          'border-radius:8px;width:28px;height:28px;display:inline-flex;align-items:center;justify-content:center;cursor:pointer;transition:all .15s;'
          + (trActive
              ? 'background:rgba(34,197,94,0.12);border:1px solid #16a34a;color:#16a34a'
              : 'background:transparent;border:1px solid var(--border);color:var(--text2)'),
        on: {
          click: () => toggleValorisationTransport(item.matiere_id || item.id),
          mouseenter: (e) => {
            if (!trActive) { e.currentTarget.style.background = 'var(--bg)'; e.currentTarget.style.color = 'var(--text)'; }
          },
          mouseleave: (e) => {
            if (!trActive) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text2)'; }
          },
        },
      });
      // Icône : camion (état 0/1) ou demi-camion custom (état 2)
      if (trState === 2) {
        trBtn.innerHTML = '<svg width="20" height="14" viewBox="0 0 32 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><text x="0" y="18" font-size="17" font-weight="800" font-family="system-ui,-apple-system,sans-serif" stroke="none" fill="currentColor">½</text><rect x="15" y="9" width="9" height="7" rx="0.5"/><path d="M24 11h3l3 3v2h-1"/><circle cx="18.5" cy="18" r="1.7"/><circle cx="27" cy="18" r="1.7"/></svg>';
      } else {
        trBtn.appendChild(iconEl('truck', 14));
      }
      actionsChildren.push(trBtn);
    }
  }
  const tdHist = el('td', {
    style: 'padding:10px 12px;text-align:center;white-space:nowrap'
  }, el('div', { style: 'display:inline-flex;gap:6px;align-items:center' }, ...actionsChildren));

  if (canSeeUSD) {
    tr.append(tdCat, tdRef, tdDes, tdQte, tdPrix, tdPrixReel, tdVal, tdHist);
  } else {
    tr.append(tdCat, tdRef, tdDes, tdQte, tdPrix, tdVal, tdHist);
  }
  return tr;
}

async function openValorisationConditionnementModal(matiereId) {
  // Modal d'édition prix unitaire d'achat + unités par palette.
  // Pour les catégories carton / adhésif / mandrin.
  const v = valEnsureState();
  const item = (v.items || []).find(x => (x.matiere_id || x.id) === matiereId);
  if (!item) { showToast('Référence introuvable.', 'danger'); return; }
  const root = document.getElementById('mroot');
  if (!root) return;
  root.innerHTML = '';
  const overlay = el('div', {
    style: 'position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:9000;display:flex;align-items:center;justify-content:center;padding:20px',
    on: { click: (e) => { if (e.target === overlay) { root.innerHTML = ''; } } },
  });
  const box = el('div', { style: 'background:var(--card);border:1px solid var(--border);border-radius:14px;width:100%;max-width:480px;padding:22px' });
  box.appendChild(el('div', { style: 'font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px' }, 'Prix & conditionnement'));
  box.appendChild(el('div', { style: 'font-size:15px;font-weight:700;color:var(--text);margin-bottom:18px' },
    (item.reference || '') + ' — ' + (item.designation || '')));

  const uniteAchat = item.unite_achat || 'unité';
  const prixInp = el('input', { type: 'number', step: '0.0001', min: '0',
    style: 'width:100%;padding:10px 12px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text);font-size:14px;font-variant-numeric:tabular-nums' });
  prixInp.value = String(Number(item.prix_unitaire || 0) || '');
  const uppInp = el('input', { type: 'number', step: '1', min: '0',
    style: 'width:100%;padding:10px 12px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text);font-size:14px;font-variant-numeric:tabular-nums' });
  uppInp.value = String(Number(item.unites_par_palette || 0) || '');

  box.appendChild(el('label', { style: 'display:block;font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px' }, 'Prix unitaire (€ / ' + uniteAchat + ')'));
  box.appendChild(prixInp);
  box.appendChild(el('div', { style: 'height:14px' }));
  box.appendChild(el('label', { style: 'display:block;font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px' }, uniteAchat + ' par palette'));
  box.appendChild(uppInp);

  // Aperçu prix palette calculé
  const preview = el('div', { style: 'margin-top:12px;font-size:12px;color:var(--text2);background:var(--bg);border:1px dashed var(--border);border-radius:8px;padding:10px 12px' });
  const updatePreview = () => {
    const p = parseFloat((prixInp.value || '').replace(',', '.')) || 0;
    const u = parseFloat((uppInp.value || '').replace(',', '.')) || 0;
    if (p > 0 && u > 0) {
      const total = p * u;
      preview.innerHTML = '';
      preview.append(
        el('span', { style: 'color:var(--muted)' }, 'Prix palette calculé : '),
        el('span', { style: 'font-weight:700;color:var(--text);font-variant-numeric:tabular-nums' },
          total.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 4 }) + ' €/pal.'),
      );
    } else {
      preview.textContent = 'Prix palette : —';
    }
  };
  prixInp.addEventListener('input', updatePreview);
  uppInp.addEventListener('input', updatePreview);
  updatePreview();
  box.appendChild(preview);

  const noteInp = el('input', { type: 'text', placeholder: 'Note optionnelle (motif du changement)',
    style: 'width:100%;padding:10px 12px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text);font-size:13px;margin-top:14px' });
  box.appendChild(noteInp);

  const actions = el('div', { style: 'display:flex;justify-content:flex-end;gap:8px;margin-top:18px' });
  actions.appendChild(el('button', {
    type: 'button',
    style: 'padding:9px 16px;border-radius:10px;border:1px solid var(--border);background:transparent;color:var(--text2);font-weight:600;cursor:pointer',
    on: { click: () => { root.innerHTML = ''; } },
  }, 'Annuler'));
  const saveBtn = el('button', {
    type: 'button',
    style: 'padding:9px 16px;border-radius:10px;border:1px solid var(--accent);background:var(--accent);color:#fff;font-weight:700;cursor:pointer',
    on: { click: async () => {
      const prix = parseFloat((prixInp.value || '').replace(',', '.'));
      const upp = parseFloat((uppInp.value || '').replace(',', '.'));
      if (isNaN(prix) || prix < 0) { showToast('Prix invalide.', 'danger'); return; }
      if (isNaN(upp) || upp <= 0) { showToast('Conditionnement (> 0) obligatoire.', 'danger'); return; }
      try {
        // 1) Conditionnement
        await api('/api/stock/matieres/' + matiereId, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ unites_par_palette: upp }),
        });
        // 2) Prix unitaire d'achat (avec historique)
        await api('/api/stock/valorisation/' + matiereId, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            prix_unitaire: prix,
            note: noteInp.value.trim() || null,
          }),
        });
        showToast('Enregistré.', 'success');
        root.innerHTML = '';
        await loadValorisation();
      } catch (e) {
        showToast('Erreur : ' + (e?.message || 'enregistrement impossible'), 'danger');
      }
    } },
  }, 'Enregistrer');
  actions.appendChild(saveBtn);
  box.appendChild(actions);

  overlay.appendChild(box);
  root.appendChild(overlay);
  setTimeout(() => prixInp.focus(), 50);
}

async function openValorisationParamsModal(matiereId) {
  // Charge l'état courant (prix m² + métrage) et ouvre un modal d'édition
  let info = null;
  try {
    info = await api('/api/stock/matieres/' + matiereId + '/laizes');
  } catch (e) {
    showToast('Erreur chargement : ' + (e?.message || ''), 'danger');
    return;
  }
  const root = document.getElementById('mroot');
  if (!root) return;
  root.innerHTML = '';
  const overlay = el('div', {
    style: 'position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:9000;display:flex;align-items:center;justify-content:center;padding:20px',
    on: { click: (e) => { if (e.target === overlay) { root.innerHTML = ''; } } },
  });
  const box = el('div', { style: 'background:var(--card);border:1px solid var(--border);border-radius:14px;width:100%;max-width:480px;padding:22px' });
  box.appendChild(el('div', { style: 'font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px' }, 'Paramètres valorisation'));
  box.appendChild(el('div', { style: 'font-size:15px;font-weight:700;color:var(--text);margin-bottom:18px' },
    (info.reference || '') + ' — ' + (info.designation || '')));

  const prixInp = el('input', { type: 'number', step: '0.0001', min: '0',
    style: 'width:100%;padding:10px 12px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text);font-size:14px;font-variant-numeric:tabular-nums' });
  prixInp.value = String(info.prix_eur_m2 || '');
  const metresInp = el('input', { type: 'number', step: '1', min: '0',
    style: 'width:100%;padding:10px 12px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text);font-size:14px;font-variant-numeric:tabular-nums' });
  metresInp.value = String(info.metres_lineaires_par_bobine || '');

  box.appendChild(el('label', { style: 'display:block;font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px' }, 'Prix au m² (€)'));
  box.appendChild(prixInp);
  box.appendChild(el('div', { style: 'height:14px' }));
  box.appendChild(el('label', { style: 'display:block;font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px' }, 'Mètres linéaires par bobine'));
  box.appendChild(metresInp);

  const noteInp = el('input', { type: 'text', placeholder: 'Note optionnelle (motif du changement)',
    style: 'width:100%;padding:10px 12px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text);font-size:13px;margin-top:14px' });
  box.appendChild(noteInp);

  const actions = el('div', { style: 'display:flex;justify-content:flex-end;gap:8px;margin-top:18px' });
  actions.appendChild(el('button', {
    type: 'button',
    style: 'padding:9px 16px;border-radius:10px;border:1px solid var(--border);background:transparent;color:var(--text2);font-weight:600;cursor:pointer',
    on: { click: () => { root.innerHTML = ''; } },
  }, 'Annuler'));
  const saveBtn = el('button', {
    type: 'button',
    style: 'padding:9px 16px;border-radius:10px;border:1px solid var(--accent);background:var(--accent);color:#fff;font-weight:700;cursor:pointer',
    on: { click: async () => {
      const prix = parseFloat((prixInp.value || '').replace(',', '.')) || 0;
      const metres = parseFloat((metresInp.value || '').replace(',', '.')) || 0;
      try {
        await api('/api/stock/valorisation/' + matiereId, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            prix_eur_m2: prix,
            metres_lineaires_par_bobine: metres,
            note: noteInp.value.trim() || null,
          }),
        });
        showToast('Paramètres enregistrés.', 'success');
        root.innerHTML = '';
        await loadValorisation();
        loadMatieresIncompleteCount();
      } catch (e) {
        showToast('Erreur : ' + (e?.message || 'enregistrement impossible'), 'danger');
      }
    } },
  }, 'Enregistrer');
  actions.appendChild(saveBtn);
  box.appendChild(actions);

  overlay.appendChild(box);
  root.appendChild(overlay);
  setTimeout(() => prixInp.focus(), 50);
}

function buildValorisationTable() {
  const v = valEnsureState();
  const rows = valFilteredItems();

  const wrap = el('div', { style:
    'background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden' });

  const tableWrap = el('div', { style: 'overflow-x:auto' });
  const table = el('table', { style: 'width:100%;border-collapse:collapse;min-width:880px' });

  const arrow = (col) => {
    if (v.sortColumn !== col) return '';
    return v.sortDirection === 'asc' ? ' ▲' : ' ▼';
  };
  const thStyle = 'padding:12px;font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;text-align:left;background:var(--bg);cursor:pointer;user-select:none;border-bottom:1px solid var(--border);white-space:nowrap';
  const thStyleR = thStyle + ';text-align:right';
  const thStyleC = thStyle + ';text-align:center;cursor:default';

  const canSeeUSD = valCanSeeUSD();
  const thChildren = [
    el('th', { style: thStyle, on: { click: () => valToggleSort('categorie') } }, 'Catégorie' + arrow('categorie')),
    el('th', { style: thStyle, on: { click: () => valToggleSort('reference') } }, 'Référence' + arrow('reference')),
    el('th', { style: thStyle, on: { click: () => valToggleSort('designation') } }, 'Désignation' + arrow('designation')),
    el('th', { style: thStyleR, on: { click: () => valToggleSort('quantite') } }, 'Quantité' + arrow('quantite')),
    el('th', { style: thStyleR, on: { click: () => valToggleSort('prix_unitaire') } }, 'Prix unitaire' + arrow('prix_unitaire')),
  ];
  if (canSeeUSD) {
    thChildren.push(
      el('th', { style: thStyleR + ';color:#16a34a',
        on: { click: () => valToggleSort('prix_unitaire_reel') },
        title: 'Prix unitaire converti via le Taux EUR/USD (MyCouts > Paramètres). Affiché pour les références cochées USD.'
      }, 'Prix unit. réel' + arrow('prix_unitaire_reel'))
    );
  }
  thChildren.push(
    el('th', { style: thStyleR, on: { click: () => valToggleSort('valorisation') } }, 'Valorisation' + arrow('valorisation')),
    el('th', { style: thStyleC }, 'Actions'),
  );
  const thead = el('thead', null, el('tr', null, ...thChildren));

  const colspan = String(thChildren.length);
  const tbody = el('tbody');
  if (!rows.length) {
    const msg = (v.query ? 'Aucun résultat pour « ' + v.query + ' »' : 'Aucune matière à valoriser.');
    tbody.appendChild(el('tr', null,
      el('td', { colspan: colspan, style: 'padding:30px 20px;text-align:center;color:var(--muted);font-size:13px' }, msg)
    ));
  } else {
    // Rendu plat : la pill active (Couché, Synthétique...) suffit à identifier le groupe.
    rows.forEach(item => tbody.appendChild(buildValorisationTableRow(item)));
  }

  table.append(thead, tbody);
  tableWrap.appendChild(table);
  wrap.appendChild(tableWrap);
  return wrap;
}

async function openValorisationHistorique(matiereId) {
  const v = valEnsureState();
  v.historiqueLoading = true;
  v.historique = { matiere: null, historique: [] };
  renderValorisationHistoriqueModal();
  try {
    const data = await api('/api/stock/valorisation/' + matiereId + '/historique');
    v.historique = data;
  } catch (e) {
    v.historique = null;
    showToast('Erreur : ' + (e?.message || 'historique indisponible'), 'danger');
  } finally {
    v.historiqueLoading = false;
    renderValorisationHistoriqueModal();
  }
}

function closeValorisationHistorique() {
  const v = valEnsureState();
  v.historique = null;
  v.historiqueLoading = false;
  renderValorisationHistoriqueModal();
}

function renderValorisationHistoriqueModal() {
  const root = document.getElementById('mroot');
  if (!root) return;
  root.innerHTML = '';
  const v = valEnsureState();
  if (!v.historique && !v.historiqueLoading) return;

  const overlay = el('div', {
    style: 'position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:9000;display:flex;align-items:center;justify-content:center;padding:20px',
    on: { click: (e) => { if (e.target === overlay) closeValorisationHistorique(); } } });

  const box = el('div', { style:
    'background:var(--card);border:1px solid var(--border);border-radius:14px;width:100%;max-width:640px;max-height:80vh;display:flex;flex-direction:column' });

  const head = el('div', { style: 'padding:18px 20px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:flex-start;gap:14px' });
  const mat = (v.historique && v.historique.matiere) || null;
  const headTitles = el('div', null,
    el('div', { style: 'font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px' }, 'Historique des prix'),
    el('div', { style: 'font-size:15px;font-weight:700;color:var(--text)' },
      mat ? (mat.reference + ' — ' + (mat.designation || '')) : 'Chargement…')
  );
  const closeBtn = el('button', {
    type: 'button', style: 'background:transparent;border:1px solid var(--border);border-radius:8px;width:32px;height:32px;color:var(--text2);cursor:pointer;font-size:18px;line-height:1',
    on: { click: closeValorisationHistorique } }, '×');
  head.append(headTitles, closeBtn);

  const body = el('div', { style: 'padding:16px 20px;overflow-y:auto' });
  if (v.historiqueLoading) {
    body.appendChild(el('div', { style: 'padding:30px;text-align:center;color:var(--muted);font-size:13px' }, 'Chargement…'));
  } else if (!v.historique || !v.historique.historique || !v.historique.historique.length) {
    body.appendChild(el('div', { style: 'padding:30px;text-align:center;color:var(--muted);font-size:13px' },
      'Aucun changement de prix enregistré.'));
  } else {
    const list = el('div', { style: 'display:flex;flex-direction:column;gap:10px' });
    v.historique.historique.forEach(h => {
      const item = el('div', { style:
        'border:1px solid var(--border);border-radius:10px;padding:12px 14px;background:var(--bg)' });
      const ligne1 = el('div', { style: 'display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:6px' },
        el('div', { style: 'font-size:13px;font-weight:700;color:var(--text);font-variant-numeric:tabular-nums' },
          (h.prix_avant != null ? valFormatEuroDetail(h.prix_avant) : '—') + '  →  ' + valFormatEuroDetail(h.prix_apres)
        ),
        el('div', { style: 'font-size:11px;color:var(--muted)' }, valFormatDate(h.created_at))
      );
      const ligne2 = el('div', { style: 'font-size:11px;color:var(--text2)' }, 'Par ' + (h.created_by_name || '—'));
      item.append(ligne1, ligne2);
      if (h.note) {
        item.appendChild(el('div', { style: 'font-size:11px;color:var(--text2);margin-top:6px;font-style:italic' }, h.note));
      }
      list.appendChild(item);
    });
    body.appendChild(list);
  }

  box.append(head, body);
  overlay.appendChild(box);
  root.appendChild(overlay);
}

async function exportValorisationExcel() {
  const v = valEnsureState();
  if (v.exporting) return;
  v.exporting = true;
  renderValorisationView(true);
  try {
    const resp = await fetch('/api/stock/valorisation/export', { credentials: 'include' });
    if (!resp.ok) {
      const msg = await resp.text().catch(() => 'erreur');
      throw new Error(msg || 'export impossible');
    }
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const today = new Date().toISOString().slice(0, 10);
    a.download = 'valorisation-stock-' + today + '.xlsx';
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
    showToast('Export terminé.', 'success');
  } catch (e) {
    showToast('Erreur export : ' + (e?.message || 'inconnue'), 'danger');
  } finally {
    v.exporting = false;
    renderValorisationView(true);
  }
}


// ── Valorisation Produits Finis (PF + Négoce) ─────────────────────

function valPFEnsureState() {
  const v = valEnsureState();
  if (!v.pf) {
    v.pf = {
      items: [],
      summary: null,
      loading: false,
      query: '',
      filterSansPrix: false,
      filterNegoce: false,
      filterAvecStock: false,
      sortColumn: null,
      sortDirection: 'asc',
      importing: false,
      exporting: false,
      historique: null,
      historiqueLoading: false,
    };
  }
  return v.pf;
}

async function loadValorisationPF() {
  const pf = valPFEnsureState();
  const v = valEnsureState();
  pf.loading = true;
  renderValorisationView(true);
  try {
    const qs = v.snapshotDate ? ('?date=' + encodeURIComponent(v.snapshotDate)) : '';
    const data = await api('/api/stock/valorisation/pf' + qs);
    pf.items = Array.isArray(data?.items) ? data.items : [];
    pf.summary = data?.summary || null;
  } catch (e) {
    pf.items = [];
    pf.summary = null;
    showToast('Erreur de chargement PF : ' + (e?.message || 'inconnue'), 'danger');
  } finally {
    pf.loading = false;
    renderValorisationView(true);
  }
}

function pfFilteredItems() {
  const pf = valPFEnsureState();
  let rows = pf.items || [];
  if (pf.filterNegoce) {
    rows = rows.filter(r => r.type === 'negoce');
  }
  if (pf.filterSansPrix) {
    rows = rows.filter(r => !r.has_price);
  }
  if (pf.filterAvecStock) {
    rows = rows.filter(r => Number(r.quantite || 0) > 0);
  }
  const q = (pf.query || '').trim().toLowerCase();
  if (q) {
    // Recherche tolérante : on enlève -, /, espace pour matcher la référence
    const qNorm = q.replace(/[-/\s]/g, '');
    rows = rows.filter(r => {
      const refRaw = (r.reference || '').toLowerCase();
      const refNorm = refRaw.replace(/[-/\s]/g, '');
      const des = (r.designation || '').toLowerCase();
      return refRaw.includes(q) || refNorm.includes(qNorm) || des.includes(q);
    });
  }
  if (pf.sortColumn) {
    rows = rows.slice().sort((a, b) => {
      let va, vb;
      switch (pf.sortColumn) {
        case 'reference': va = (a.reference || '').toLowerCase(); vb = (b.reference || '').toLowerCase(); break;
        case 'designation': va = (a.designation || '').toLowerCase(); vb = (b.designation || '').toLowerCase(); break;
        case 'type': va = (a.type_label || '').toLowerCase(); vb = (b.type_label || '').toLowerCase(); break;
        case 'quantite': va = Number(a.quantite || 0); vb = Number(b.quantite || 0); break;
        case 'prix_unitaire_ht': va = Number(a.prix_unitaire_ht || 0); vb = Number(b.prix_unitaire_ht || 0); break;
        case 'valorisation': va = Number(a.valorisation || 0); vb = Number(b.valorisation || 0); break;
        case 'charges_prod': va = Number(a.charges_prod || 0); vb = Number(b.charges_prod || 0); break;
        default: va = 0; vb = 0;
      }
      if (va < vb) return pf.sortDirection === 'asc' ? -1 : 1;
      if (va > vb) return pf.sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }
  return rows;
}

function valTogglePFSort(column) {
  const pf = valPFEnsureState();
  if (pf.sortColumn === column) {
    pf.sortDirection = pf.sortDirection === 'asc' ? 'desc' : 'asc';
  } else {
    pf.sortColumn = column;
    pf.sortDirection = 'asc';
  }
  renderValorisationPFTableOnly();
}

async function savePFPrice(produitId, newPrice, inputEl) {
  const pf = valPFEnsureState();
  try {
    const data = await api('/api/stock/valorisation/pf/' + produitId, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prix_unitaire_ht: newPrice }),
    });
    if (data?.item) {
      const idx = pf.items.findIndex(x => x.id === produitId);
      if (idx >= 0) pf.items[idx] = data.item;
    }
    if (data?.summary) pf.summary = data.summary;
    renderValorisationView(true);
    showToast('Prix enregistré.', 'success');
  } catch (e) {
    showToast('Erreur : ' + (e?.message || 'enregistrement impossible'), 'danger');
    if (inputEl) {
      const item = pf.items.find(x => x.id === produitId);
      if (item) inputEl.value = (Number(item.prix_unitaire_ht) || 0).toString().replace('.', ',');
    }
  }
}

async function openPFHistorique(produitId) {
  const pf = valPFEnsureState();
  pf.historiqueLoading = true;
  pf.historique = { produit: null, historique: [] };
  renderPFHistoriqueModal();
  try {
    const data = await api('/api/stock/valorisation/pf/' + produitId + '/historique');
    pf.historique = data;
  } catch (e) {
    pf.historique = null;
    showToast('Erreur : ' + (e?.message || 'historique indisponible'), 'danger');
  } finally {
    pf.historiqueLoading = false;
    renderPFHistoriqueModal();
  }
}

function closePFHistorique() {
  const pf = valPFEnsureState();
  pf.historique = null;
  pf.historiqueLoading = false;
  renderPFHistoriqueModal();
}

function renderPFHistoriqueModal() {
  const root = document.getElementById('mroot');
  if (!root) return;
  const pf = valPFEnsureState();
  // On ne ré-écrit le mroot que si on doit afficher ce modal
  if (!pf.historique && !pf.historiqueLoading) {
    // Si un autre modal (MP historique) est ouvert, ne pas l'écraser
    const existing = root.firstElementChild;
    if (existing && existing.getAttribute && existing.getAttribute('data-modal') === 'pf-historique') {
      root.innerHTML = '';
    }
    return;
  }
  root.innerHTML = '';

  const overlay = el('div', {
    'data-modal': 'pf-historique',
    style: 'position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:9000;display:flex;align-items:center;justify-content:center;padding:20px',
    on: { click: (e) => { if (e.target === overlay) closePFHistorique(); } },
  });
  const box = el('div', { style:
    'background:var(--card);border:1px solid var(--border);border-radius:14px;width:100%;max-width:640px;max-height:80vh;display:flex;flex-direction:column' });
  const head = el('div', { style: 'padding:18px 20px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:flex-start;gap:14px' });
  const prod = (pf.historique && pf.historique.produit) || null;
  head.append(
    el('div', null,
      el('div', { style: 'font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px' }, 'Historique des prix'),
      el('div', { style: 'font-size:15px;font-weight:700;color:var(--text)' },
        prod ? (prod.reference + ' — ' + (prod.designation || '')) : 'Chargement…')
    ),
    el('button', {
      type: 'button',
      style: 'background:transparent;border:1px solid var(--border);border-radius:8px;width:32px;height:32px;color:var(--text2);cursor:pointer;font-size:18px;line-height:1',
      on: { click: closePFHistorique },
    }, '×'),
  );
  const body = el('div', { style: 'padding:16px 20px;overflow-y:auto' });
  if (pf.historiqueLoading) {
    body.appendChild(el('div', { style: 'padding:30px;text-align:center;color:var(--muted);font-size:13px' }, 'Chargement…'));
  } else if (!pf.historique || !pf.historique.historique || !pf.historique.historique.length) {
    body.appendChild(el('div', { style: 'padding:30px;text-align:center;color:var(--muted);font-size:13px' },
      'Aucun changement de prix enregistré.'));
  } else {
    const list = el('div', { style: 'display:flex;flex-direction:column;gap:10px' });
    pf.historique.historique.forEach(h => {
      const item = el('div', { style:
        'border:1px solid var(--border);border-radius:10px;padding:12px 14px;background:var(--bg)' });
      const ligne1 = el('div', { style: 'display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:6px' },
        el('div', { style: 'font-size:13px;font-weight:700;color:var(--text);font-variant-numeric:tabular-nums' },
          (h.prix_avant != null ? valFormatEuroDetail(h.prix_avant) : '—') + '  →  ' + valFormatEuroDetail(h.prix_apres)
        ),
        el('div', { style: 'font-size:11px;color:var(--muted)' }, valFormatDate(h.created_at)),
      );
      const sourceLabel = h.source === 'import' ? 'Import Excel' : (h.source === 'edition' ? 'Édition manuelle' : (h.source || ''));
      const ligne2 = el('div', { style: 'display:flex;justify-content:space-between;align-items:center;gap:8px;font-size:11px;color:var(--text2)' },
        el('span', null, 'Par ' + (h.created_by_name || '—')),
        sourceLabel ? el('span', { style:
          'padding:2px 8px;border-radius:6px;background:var(--accent-bg);color:var(--accent);font-size:10px;font-weight:700' }, sourceLabel) : el('span'),
      );
      item.append(ligne1, ligne2);
      if (h.note) {
        item.appendChild(el('div', { style: 'font-size:11px;color:var(--text2);margin-top:6px;font-style:italic' }, h.note));
      }
      list.appendChild(item);
    });
    body.appendChild(list);
  }
  box.append(head, body);
  overlay.appendChild(box);
  root.appendChild(overlay);
}

async function importPFExcel(fileInput) {
  const pf = valPFEnsureState();
  const f = fileInput.files && fileInput.files[0];
  if (!f) return;
  if (!/\.(xlsx|xlsm)$/i.test(f.name)) {
    showToast('Format attendu : .xlsx', 'danger');
    fileInput.value = '';
    return;
  }
  pf.importing = true;
  renderValorisationView(true);
  try {
    const form = new FormData();
    form.append('file', f);
    const resp = await fetch('/api/stock/valorisation/pf/import', {
      method: 'POST',
      credentials: 'include',
      body: form,
    });
    if (!resp.ok) {
      const txt = await resp.text();
      let msg = txt;
      try { msg = JSON.parse(txt).detail || msg; } catch (e) {}
      throw new Error(msg || ('HTTP ' + resp.status));
    }
    const data = await resp.json();
    const s = data.stats || {};
    showToast(
      `Import terminé : ${s.lignes_lues || 0} lignes lues, ${s.refs_creees || 0} créées, ${s.refs_mises_a_jour || 0} mises à jour.`,
      'success'
    );
    if (s.avertissements && s.avertissements.length) {
      console.warn('[Valorisation PF] Avertissements import :', s.avertissements);
    }
    await loadValorisationPF();
  } catch (e) {
    showToast('Erreur import : ' + (e?.message || 'échec'), 'danger');
  } finally {
    pf.importing = false;
    fileInput.value = '';
    renderValorisationView(true);
  }
}

async function exportPFExcel() {
  const pf = valPFEnsureState();
  pf.exporting = true;
  renderValorisationView(true);
  try {
    const resp = await fetch('/api/stock/valorisation/pf/export', { credentials: 'include' });
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const d = new Date();
    const pad = (n) => (n < 10 ? '0' + n : '' + n);
    a.download = `valorisation-pf-${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}.xlsx`;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { document.body.removeChild(a); URL.revokeObjectURL(url); }, 100);
  } catch (e) {
    showToast('Erreur export : ' + (e?.message || 'échec'), 'danger');
  } finally {
    pf.exporting = false;
    renderValorisationView(true);
  }
}

function buildValorisationPFToolbar() {
  const pf = valPFEnsureState();
  const wrap = el('div', { style:
    'display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:14px' });

  // Recherche
  const inp = el('input', {
    type: 'search', id: 'val-pf-search', placeholder: 'Rechercher une référence (1004/0053, 1077-0017…)',
    style: 'flex:1;min-width:240px;padding:10px 14px;border:1px solid var(--border);border-radius:10px;background:var(--bg);color:var(--text);font-size:13px;transition:border-color .15s',
  });
  inp.value = pf.query || '';
  inp.addEventListener('input', () => {
    pf.query = inp.value;
    renderValorisationPFTableOnly();
  });
  inp.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') { inp.value = ''; pf.query = ''; renderValorisationPFTableOnly(); }
  });
  wrap.appendChild(inp);

  // Bouton import (cache un input file)
  const fileInput = el('input', { type: 'file', accept: '.xlsx,.xlsm', style: 'display:none' });
  fileInput.addEventListener('change', () => importPFExcel(fileInput));
  const importBtn = el('button', {
    type: 'button', disabled: pf.importing ? true : null, title: 'Importer la feuille Valorisation depuis un fichier Excel',
    style: 'padding:10px 16px;border-radius:10px;border:1px solid var(--accent);background:var(--accent);color:#0a0e17;font-size:13px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:8px;' + (pf.importing ? 'opacity:.6;cursor:wait' : ''),
    on: { click: () => { if (!pf.importing) fileInput.click(); } },
  });
  importBtn.appendChild(iconEl('upload', 14));
  importBtn.appendChild(el('span', null, pf.importing ? 'Import…' : 'Importer Excel'));
  wrap.appendChild(importBtn);
  wrap.appendChild(fileInput);

  // Bouton export
  const exportBtn = el('button', {
    type: 'button', disabled: pf.exporting ? true : null, title: 'Exporter en Excel les prix actuels',
    style: 'padding:10px 16px;border-radius:10px;border:1px solid var(--border);background:var(--card);color:var(--text);font-size:13px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:8px;' + (pf.exporting ? 'opacity:.6;cursor:wait' : ''),
    on: { click: () => { if (!pf.exporting) exportPFExcel(); } },
  });
  exportBtn.appendChild(iconEl('download', 14));
  exportBtn.appendChild(el('span', null, pf.exporting ? 'Export…' : 'Exporter Excel'));
  wrap.appendChild(exportBtn);

  // Refresh
  const refreshBtn = el('button', {
    type: 'button', title: 'Recharger',
    style: 'padding:10px 14px;border-radius:10px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;display:inline-flex;align-items:center',
    on: { click: () => loadValorisationPF() },
  });
  refreshBtn.appendChild(iconEl('refresh-ccw', 14));
  wrap.appendChild(refreshBtn);

  return wrap;
}

function buildValorisationPFFilterPills() {
  const pf = valPFEnsureState();
  const s = pf.summary || { nb_refs: 0, nb_refs_sans_prix: 0, nb_refs_negoce: 0, total_pf: 0 };
  const wrap = el('div', { id: 'val-pf-pills-wrap', style:
    'display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px;align-items:center' });

  const base = 'padding:7px 14px;border-radius:999px;border:1px solid var(--border);background:transparent;color:var(--text2);font-size:12px;font-weight:600;cursor:pointer;transition:all .15s;display:inline-flex;align-items:center;gap:6px';
  const active = 'padding:7px 14px;border-radius:999px;border:1px solid var(--accent);background:var(--accent-bg);color:var(--accent);font-size:12px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:6px';
  const warn = 'padding:7px 14px;border-radius:999px;border:1px solid #fb923c;background:rgba(251,146,60,0.15);color:#fb923c;font-size:12px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:6px';

  const nbAvecStock = (pf.items || []).reduce((n, r) => n + (Number(r.quantite || 0) > 0 ? 1 : 0), 0);

  const refresh = () => { renderValorisationPFPillsOnly(); renderValorisationPFTableOnly(); };

  const allBtn = el('button', {
    type: 'button', style: (!pf.filterSansPrix && !pf.filterNegoce && !pf.filterAvecStock) ? active : base,
    on: { click: () => { pf.filterSansPrix = false; pf.filterNegoce = false; pf.filterAvecStock = false; refresh(); } },
  }, 'Toutes les références',
    el('span', { style: 'opacity:.7;font-weight:600' }, '· ' + (s.nb_refs || 0)),
  );

  const sansPrixBtn = el('button', {
    type: 'button', style: pf.filterSansPrix ? warn : base,
    on: { click: () => { pf.filterSansPrix = !pf.filterSansPrix; refresh(); } },
  }, 'Sans prix',
    el('span', { style: 'opacity:.8;font-weight:700' }, '· ' + (s.nb_refs_sans_prix || 0)),
  );

  const negoceBtn = el('button', {
    type: 'button', style: pf.filterNegoce ? active : base,
    on: { click: () => { pf.filterNegoce = !pf.filterNegoce; refresh(); } },
  }, 'Produits de négoce',
    el('span', { style: 'opacity:.7;font-weight:600' }, '· ' + (s.nb_refs_negoce || 0)),
  );

  const stockBtn = el('button', {
    type: 'button', style: pf.filterAvecStock ? active : base,
    on: { click: () => { pf.filterAvecStock = !pf.filterAvecStock; refresh(); } },
  }, 'Quantité > 0',
    el('span', { style: 'opacity:.7;font-weight:600' }, '· ' + nbAvecStock),
  );

  wrap.append(allBtn, sansPrixBtn, negoceBtn, stockBtn);
  return wrap;
}

function renderValorisationPFPillsOnly() {
  const old = document.getElementById('val-pf-pills-wrap');
  if (!old) return;
  const fresh = buildValorisationPFFilterPills();
  old.replaceWith(fresh);
}

function buildValorisationPFTableRow(item) {
  const tr = el('tr', { 'data-row-key': 'pf' + item.id, style: 'border-bottom:1px solid var(--border)' });

  // Type (badge)
  const isNegoce = item.type === 'negoce';
  const badgeStyle = isNegoce
    ? 'display:inline-block;padding:2px 9px;border-radius:999px;background:rgba(251,191,36,0.15);color:#fbbf24;font-size:11px;font-weight:700;letter-spacing:.2px'
    : 'display:inline-block;padding:2px 9px;border-radius:999px;background:var(--accent-bg);color:var(--accent);font-size:11px;font-weight:700;letter-spacing:.2px';
  const tdType = el('td', { style: 'padding:10px 12px;font-size:12px' },
    el('span', { style: badgeStyle }, item.type_label || (isNegoce ? 'Négoce' : 'Fabriqué')),
  );

  // Référence (cliquable → ouvre le produit fini ; Cmd/Ctrl+clic = nouvel onglet)
  const refLink = stockPfRefLink(item.reference, item.id);
  if (refLink && refLink.tagName === 'A') {
    refLink.title = 'Ouvrir le produit';
    refLink.style.color = 'var(--text)';
    refLink.style.fontWeight = '700';
    refLink.style.fontFamily = 'monospace';
    refLink.style.fontSize = '13px';
  }
  const tdRef = el('td', { style: 'padding:10px 12px;font-size:13px;font-weight:700;color:var(--text);font-family:monospace' }, refLink);

  // Désignation
  const tdDes = el('td', { style: 'padding:10px 12px;font-size:13px;color:var(--text2);max-width:380px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap', title: item.designation || '' }, item.designation || '');

  // Quantité stock
  const tdQte = el('td', { style: 'padding:10px 12px;font-size:13px;color:var(--text);text-align:right;font-variant-numeric:tabular-nums' },
    valFormatQte(item.quantite),
    el('span', { style: 'margin-left:5px;font-size:11px;color:var(--muted);font-weight:500' }, item.unite || ''),
  );

  // Prix unitaire HT — éditable inline
  const inpId = 'val-pf-price-' + item.id;
  const inp = el('input', {
    type: 'text', id: inpId,
    value: (Number(item.prix_unitaire_ht) || 0).toString().replace('.', ','),
    inputmode: 'decimal',
    style: 'width:120px;padding:6px 8px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text);font-size:13px;font-variant-numeric:tabular-nums;text-align:right;transition:border-color .15s',
  });
  const commit = async () => {
    const raw = (inp.value || '').trim().replace(/\s/g, '').replace(',', '.');
    const num = parseFloat(raw);
    const current = Number(item.prix_unitaire_ht) || 0;
    if (isNaN(num) || num < 0) {
      inp.value = current.toString().replace('.', ',');
      showToast('Prix invalide.', 'danger');
      return;
    }
    if (Math.abs(num - current) < 0.00001) return;
    await savePFPrice(item.id, num, inp);
  };
  inp.addEventListener('blur', commit);
  inp.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { e.preventDefault(); inp.blur(); }
    if (e.key === 'Escape') {
      inp.value = (Number(item.prix_unitaire_ht) || 0).toString().replace('.', ',');
      inp.blur();
    }
  });
  inp.addEventListener('focus', () => inp.select());
  const uniteLow = (item.unite || '').toLowerCase()
    .replace(/é/g, 'e').replace(/è/g, 'e').replace(/ê/g, 'e');
  const parMille = item.par_mille || uniteLow === 'etiquette' || uniteLow === 'etiquettes';
  const prixUniteLabel = parMille ? 'Mille' : (item.unite || '');
  const tdPrix = el('td', { style: 'padding:10px 12px;text-align:right' },
    inp,
    el('span', { style: 'margin-left:6px;font-size:11px;color:var(--muted)' }, '€ HT/' + prixUniteLabel),
  );

  // Statut "Sans prix" si pas de prix
  if (!item.has_price) {
    tdPrix.appendChild(el('div', { style: 'font-size:10px;color:#fb923c;font-weight:700;margin-top:3px' }, 'Sans prix'));
  } else if (item.source_prix) {
    tdPrix.appendChild(el('div', { style: 'font-size:10px;color:var(--muted);margin-top:3px' }, item.source_prix));
  }

  // Valorisation
  const valColor = item.has_price ? 'var(--text)' : 'var(--muted)';
  const tdVal = el('td', { style: 'padding:10px 12px;font-size:13px;font-weight:700;text-align:right;font-variant-numeric:tabular-nums;color:' + valColor },
    item.has_price ? valFormatEuro(item.valorisation) : '—',
  );

  // Dont charges de prod. (charge production + frais de stockage appliqués)
  // Réservé Direction + superadmin, comme la colonne « réel » côté MP.
  const canSeeCharges = valCanSeeUSD();
  const chargesProd = Number(item.charges_prod || 0);
  const hasCharges = item.has_price && chargesProd > 0.001;
  const tdCharges = canSeeCharges
    ? el('td', { style: 'padding:10px 12px;font-size:13px;font-weight:700;text-align:right;font-variant-numeric:tabular-nums;color:' + (hasCharges ? '#16a34a' : 'var(--muted)') },
        hasCharges ? valFormatEuro(chargesProd) : '—',
      )
    : null;

  // Historique
  const histBtn = el('button', {
    type: 'button', title: 'Voir l\'historique des prix',
    style: 'background:transparent;border:1px solid var(--border);border-radius:8px;width:28px;height:28px;display:inline-flex;align-items:center;justify-content:center;cursor:pointer;color:var(--text2)',
    on: { click: () => openPFHistorique(item.id) },
  });
  histBtn.appendChild(iconEl('clock', 14));
  const tdHist = el('td', { style: 'padding:10px 12px;text-align:center' }, histBtn);

  tr.append(tdType, tdRef, tdDes, tdQte, tdPrix, tdVal);
  if (tdCharges) tr.append(tdCharges);
  tr.append(tdHist);
  return tr;
}

function buildValorisationPFTable() {
  const pf = valPFEnsureState();
  const rows = pfFilteredItems();
  const wrap = el('div', { style:
    'background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden' });

  const tableWrap = el('div', { style: 'overflow-x:auto' });
  const table = el('table', { style: 'width:100%;border-collapse:collapse;min-width:980px' });

  const arrow = (col) => {
    if (pf.sortColumn !== col) return '';
    return pf.sortDirection === 'asc' ? ' ▲' : ' ▼';
  };
  const thStyle = 'padding:12px;font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;text-align:left;background:var(--bg);cursor:pointer;user-select:none;border-bottom:1px solid var(--border);white-space:nowrap';
  const thStyleR = thStyle + ';text-align:right';
  const thStyleC = thStyle + ';text-align:center;cursor:default';

  // Colonne « Dont charges de prod. » — Direction + superadmin uniquement.
  const canSeeChargesCol = valCanSeeUSD();
  const headerCells = [
    el('th', { style: thStyle, on: { click: () => valTogglePFSort('type') } }, 'Type' + arrow('type')),
    el('th', { style: thStyle, on: { click: () => valTogglePFSort('reference') } }, 'Référence' + arrow('reference')),
    el('th', { style: thStyle, on: { click: () => valTogglePFSort('designation') } }, 'Désignation' + arrow('designation')),
    el('th', { style: thStyleR, on: { click: () => valTogglePFSort('quantite') } }, 'Quantité' + arrow('quantite')),
    el('th', { style: thStyleR, on: { click: () => valTogglePFSort('prix_unitaire_ht') } }, 'Prix HT' + arrow('prix_unitaire_ht')),
    el('th', { style: thStyleR, on: { click: () => valTogglePFSort('valorisation') } }, 'Valorisation' + arrow('valorisation')),
  ];
  if (canSeeChargesCol) {
    headerCells.push(
      el('th', { style: thStyleR + ';color:#16a34a', on: { click: () => valTogglePFSort('charges_prod') }, title: 'Charge de production + frais de stockage appliqués à la valorisation' }, 'Dont charges de prod.' + arrow('charges_prod')),
    );
  }
  headerCells.push(el('th', { style: thStyleC }, 'Historique'));
  const thead = el('thead', null, el('tr', null, ...headerCells));
  const emptyColspan = canSeeChargesCol ? '8' : '7';

  const tbody = el('tbody');
  if (pf.loading && !rows.length) {
    tbody.appendChild(el('tr', null,
      el('td', { colspan: emptyColspan, style: 'padding:30px 20px;text-align:center;color:var(--muted);font-size:13px' }, 'Chargement…'),
    ));
  } else if (!rows.length) {
    let msg;
    if (pf.query) msg = 'Aucun résultat pour « ' + pf.query + ' »';
    else if (pf.filterAvecStock && pf.filterSansPrix) msg = 'Aucune référence sans prix avec du stock.';
    else if (pf.filterAvecStock && pf.filterNegoce) msg = 'Aucun produit de négoce en stock.';
    else if (pf.filterAvecStock) msg = 'Aucune référence en stock.';
    else if (pf.filterSansPrix && pf.filterNegoce) msg = 'Aucun produit de négoce sans prix.';
    else if (pf.filterSansPrix) msg = 'Toutes les références ont un prix renseigné.';
    else if (pf.filterNegoce) msg = 'Aucun produit de négoce enregistré.';
    else msg = 'Aucune référence à valoriser. Importez un fichier Excel pour commencer.';
    tbody.appendChild(el('tr', null,
      el('td', { colspan: emptyColspan, style: 'padding:30px 20px;text-align:center;color:var(--muted);font-size:13px' }, msg),
    ));
  } else {
    rows.forEach(item => tbody.appendChild(buildValorisationPFTableRow(item)));
  }

  table.append(thead, tbody);
  tableWrap.appendChild(table);
  wrap.appendChild(tableWrap);
  return wrap;
}

function buildValorisationSectionChevron(collapsed, onToggle) {
  const btn = el('button', {
    type: 'button',
    title: collapsed ? 'Afficher la section' : 'Masquer la section',
    style: 'background:transparent;border:1px solid var(--border);border-radius:8px;width:28px;height:28px;flex-shrink:0;display:inline-flex;align-items:center;justify-content:center;cursor:pointer;color:var(--text2);transition:transform .15s, background .15s;' + (collapsed ? '' : 'transform:rotate(90deg)'),
    on: { click: onToggle },
  });
  // chevron-right inline SVG (le bouton tourne pour pointer vers le bas)
  btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 6 15 12 9 18"/></svg>';
  return btn;
}

function buildValorisationPFHeader() {
  const v = valEnsureState();
  const pf = valPFEnsureState();
  const s = pf.summary || { total_pf: 0, total_fabrique: 0, total_negoce: 0, nb_refs: 0, nb_refs_valorisees: 0, nb_refs_sans_prix: 0 };
  return el('div', { style: 'display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:12px' },
    el('div', { style: 'display:flex;align-items:center;gap:10px;min-width:0' },
      buildValorisationSectionChevron(!!v.pfCollapsed, () => {
        v.pfCollapsed = !v.pfCollapsed;
        renderValorisationView(true);
      }),
      el('div', null,
        el('h3', { style: 'font-size:16px;font-weight:800;color:var(--text);margin:0;cursor:pointer', on: { click: () => { v.pfCollapsed = !v.pfCollapsed; renderValorisationView(true); } } }, 'Produits finis'),
        el('div', { style: 'font-size:12px;color:var(--muted);margin-top:2px' },
          `${s.nb_refs_valorisees || 0} / ${s.nb_refs || 0} références valorisées · Import Excel → onglet « Valorisation »`),
      ),
    ),
    el('span', { style:
      'padding:5px 12px;border-radius:999px;background:var(--accent-bg);color:var(--accent);font-size:11px;font-weight:700;letter-spacing:.3px' },
      valFormatEuro(s.total_pf)),
  );
}

function renderValorisationPFTableOnly() {
  const area = document.getElementById('val-pf-table-wrap');
  if (!area) { renderValorisationView(true); return; }
  area.innerHTML = '';
  area.appendChild(buildValorisationPFTable());
}

// Remplacement du placeholder par la vraie section PF
function buildValorisationPFSection() {
  const v = valEnsureState();
  const pf = valPFEnsureState();
  const wrap = el('div', { style: 'margin-top:28px' });
  wrap.appendChild(buildValorisationPFHeader());
  if (!v.pfCollapsed) {
    wrap.appendChild(buildValorisationPFToolbar());
    wrap.appendChild(buildValorisationPFFilterPills());
    const tableWrap = el('div', { id: 'val-pf-table-wrap' });
    tableWrap.appendChild(buildValorisationPFTable());
    wrap.appendChild(tableWrap);
  }
  // Auto-chargement à la 1re affichage (même si collapsée pour avoir les KPIs à jour)
  if (!pf.loading && pf.summary === null && (pf.items || []).length === 0) {
    setTimeout(() => loadValorisationPF(), 10);
  }
  return wrap;
}


function buildValorisationMPHeader() {
  const v = valEnsureState();
  const s = v.summary || { total_mp: 0, nb_refs: 0, nb_refs_valorisees: 0 };
  return el('div', { style: 'display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:12px' },
    el('div', { style: 'display:flex;align-items:center;gap:10px;min-width:0' },
      buildValorisationSectionChevron(!!v.mpCollapsed, () => {
        v.mpCollapsed = !v.mpCollapsed;
        renderValorisationView(true);
      }),
      el('div', null,
        el('h3', { style: 'font-size:16px;font-weight:800;color:var(--text);margin:0;cursor:pointer', on: { click: () => { v.mpCollapsed = !v.mpCollapsed; renderValorisationView(true); } } }, 'Matières premières'),
        el('div', { style: 'font-size:12px;color:var(--muted);margin-top:2px' },
          `${s.nb_refs_valorisees || 0} / ${s.nb_refs || 0} références valorisées · Mandrins, palettes, adhésifs, cartons, frontaux, glassines, complexes`)
      ),
    ),
    el('span', { style:
      'padding:5px 12px;border-radius:999px;background:var(--accent-bg);color:var(--accent);font-size:11px;font-weight:700;letter-spacing:.3px' },
      valFormatEuro(s.total_mp))
  );
}

// Toolbar globale (au-dessus des KPIs) : sélecteur de date + export + refresh
// + paramètres MyCouts. Pilote la valorisation du stock TOTAL (MP + PF).
function buildValorisationGlobalToolbar() {
  const v = valEnsureState();
  const wrap = el('div', { style:
    'display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:16px' });

  // ── Sélecteur de date « Valorisation au … » (Direction / superadmin) ──
  if (valCanSeeUSD()) {
    const todayIso = new Date().toISOString().slice(0, 10);
    const isSnapshot = !!v.snapshotDate && v.snapshotDate !== todayIso;
    const dateWrap = el('div', { style:
      'display:inline-flex;align-items:center;gap:10px;padding:6px 14px 6px 12px;border:1px solid ' +
      (isSnapshot ? '#f59e0b' : 'var(--border)') +
      ';border-radius:10px;background:' + (isSnapshot ? 'rgba(245,158,11,0.06)' : 'var(--card)') +
      ';transition:background .15s, border-color .15s;cursor:pointer;user-select:none',
      title: 'Cliquer pour choisir une date'
    });
    // Toute la capsule est cliquable : ouvre le calendrier natif via showPicker().
    // Fallback focus si l'API n'est pas dispo (vieux navigateur).
    dateWrap.addEventListener('click', (ev) => {
      const t = ev.target;
      if (t && (t.tagName === 'INPUT' || t.tagName === 'BUTTON')) return;
      try {
        if (typeof dateInp.showPicker === 'function') dateInp.showPicker();
        else { dateInp.focus(); dateInp.click(); }
      } catch (_e) {
        dateInp.focus();
      }
    });
    dateWrap.addEventListener('mouseenter', () => {
      if (!isSnapshot) dateWrap.style.background = 'var(--bg)';
    });
    dateWrap.addEventListener('mouseleave', () => {
      if (!isSnapshot) dateWrap.style.background = 'var(--card)';
    });
    // Icône calendrier
    const icon = el('span', { style:
      'display:inline-flex;color:' + (isSnapshot ? '#c2410c' : 'var(--muted)') });
    icon.innerHTML = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>';
    // Label
    const lbl = el('span', { style:
      'font-size:11px;font-weight:700;color:' + (isSnapshot ? '#c2410c' : 'var(--muted)') +
      ';text-transform:uppercase;letter-spacing:.5px'
    }, 'Valorisation au');
    // Input date
    const dateInp = el('input', {
      type: 'date', id: 'val-snapshot-date', max: todayIso, min: '2020-01-01',
      title: 'Figer la valorisation à une date passée',
      style: 'padding:4px 6px;border:none;background:transparent;color:var(--text);font-size:14px;font-weight:700;font-family:inherit;outline:none;font-variant-numeric:tabular-nums;cursor:pointer;color-scheme:light dark'
    });
    dateInp.value = v.snapshotDate || todayIso;
    dateInp.addEventListener('change', async () => {
      const iso = dateInp.value || '';
      v.snapshotDate = (iso && iso !== todayIso) ? iso : null;
      await loadValorisation();
      await loadValorisationPF();
    });
    // Lien « Aujourd'hui » (visible seulement en mode snapshot)
    // Chevron pour signaler l'affordance (calendrier ouvrable)
    const chevron = el('span', { style:
      'display:inline-flex;color:' + (isSnapshot ? '#c2410c' : 'var(--muted)') + ';opacity:.6' });
    chevron.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>';
    dateWrap.append(icon, lbl, dateInp, chevron);
    if (isSnapshot) {
      const resetLink = el('button', {
        type: 'button', title: 'Revenir à aujourd\'hui',
        style: 'padding:3px 8px;border:1px solid #f59e0b;border-radius:6px;background:transparent;color:#c2410c;font-size:11px;font-weight:700;cursor:pointer;text-transform:uppercase;letter-spacing:.3px',
        on: {
          click: async () => {
            v.snapshotDate = null;
            dateInp.value = todayIso;
            await loadValorisation();
            await loadValorisationPF();
          },
        },
      }, 'Aujourd\'hui');
      dateWrap.append(resetLink);
    }
    wrap.append(dateWrap);
  }

  // ── Espaceur (pousse les actions à droite) ──
  const spacer = el('div', { style: 'flex:1;min-width:0' });
  wrap.append(spacer);

  // ── Bouton Exporter (dropdown : Excel + 3 vues PDF) ──
  const exportWrap = el('div', { style: 'position:relative;display:inline-flex' });
  const exportBtn = el('button', {
    type: 'button', disabled: v.exporting ? true : null,
      style: 'padding:9px 14px;border-radius:10px;border:1px solid var(--border);background:var(--card);color:var(--text);font-size:13px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:8px;' + (v.exporting ? 'opacity:.6;cursor:wait' : ''),
  });
  exportBtn.appendChild(iconEl('download', 14));
  exportBtn.appendChild(el('span', null, v.exporting ? 'Export en cours…' : 'Exporter'));
  const expChev = el('span', { style: 'display:inline-flex;opacity:.7' });
  expChev.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>';
  exportBtn.appendChild(expChev);

  const exportMenu = el('div', { style:
    'position:absolute;top:calc(100% + 6px);right:0;min-width:260px;background:var(--card);border:1px solid var(--border);border-radius:10px;box-shadow:0 12px 32px rgba(0,0,0,.18);padding:6px;display:none;z-index:100;flex-direction:column;gap:2px'
  });

  const mkOpt = (iconName, label, sub, onClick) => {
    const btn = el('button', {
      type: 'button',
      style: 'display:flex;align-items:flex-start;gap:10px;padding:9px 12px;border:none;background:transparent;color:var(--text);border-radius:8px;cursor:pointer;text-align:left;font-family:inherit;transition:background .12s',
      on: {
        click: () => { exportMenu.style.display = 'none'; onClick(); },
        mouseenter: (e) => { e.currentTarget.style.background = 'var(--bg)'; },
        mouseleave: (e) => { e.currentTarget.style.background = 'transparent'; },
      },
    });
    const iconWrap = el('span', { style: 'display:inline-flex;color:var(--accent);margin-top:2px' });
    iconWrap.appendChild(iconEl(iconName, 15));
    const txt = el('div', { style: 'display:flex;flex-direction:column;line-height:1.3' },
      el('span', { style: 'font-size:13px;font-weight:600;color:var(--text)' }, label),
      el('span', { style: 'font-size:11px;color:var(--muted);margin-top:1px' }, sub),
    );
    btn.append(iconWrap, txt);
    return btn;
  };

  const triggerPdf = (typeVue) => {
    const params = new URLSearchParams();
    if (v.snapshotDate) params.set('date', v.snapshotDate);
    params.set('type', typeVue);
    window.open('/api/stock/valorisation/export-pdf?' + params.toString(), '_blank');
  };

  exportMenu.append(
    mkOpt('file-spreadsheet', 'Excel', 'Détail complet MP (format historique)', () => exportValorisationExcel()),
    mkOpt('list', 'PDF · lignes', 'Tableau ligne par ligne (MP + PF)', () => triggerPdf('lignes')),
    mkOpt('layout', 'PDF · sommaire', 'Totaux + répartition par catégorie', () => triggerPdf('sommaire')),
    mkOpt('bar-chart-2', 'PDF · sommaire + insights', 'Sommaire + graphiques (répartition + top 10)', () => triggerPdf('insights')),
  );

  exportBtn.addEventListener('click', (ev) => {
    ev.stopPropagation();
    const willOpen = exportMenu.style.display !== 'flex';
    exportMenu.style.display = willOpen ? 'flex' : 'none';
    if (willOpen) {
      setTimeout(() => {
        const closer = (e) => {
          if (!exportWrap.contains(e.target)) {
            exportMenu.style.display = 'none';
            document.removeEventListener('click', closer);
          }
        };
        document.addEventListener('click', closer);
      }, 0);
    }
  });

  exportWrap.append(exportBtn, exportMenu);
  wrap.append(exportWrap);

  // ── Bouton Rafraîchir (MP + PF) ──
  const refreshBtn = el('button', {
    type: 'button', title: 'Recharger MP + PF',
      style: 'padding:9px 12px;border-radius:10px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;display:inline-flex;align-items:center;transition:background .15s, color .15s',
    on: {
      click: async () => { await loadValorisation(); await loadValorisationPF(); },
      mouseenter: (e) => { e.currentTarget.style.background = 'var(--bg)'; e.currentTarget.style.color = 'var(--text)'; },
      mouseleave: (e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text2)'; },
    } });
  refreshBtn.appendChild(iconEl('refresh-ccw', 14));
  wrap.append(refreshBtn);

  // ── Bouton Paramètres MyCouts (Direction / superadmin) ──
  if (valCanSeeUSD()) {
    const settingsBtn = el('button', {
      type: 'button',
      title: 'Paramètres MyCouts',
      style: 'padding:9px 12px;border-radius:10px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;display:inline-flex;align-items:center;transition:background .15s, color .15s',
      on: {
        click: () => openValorisationSettingsModal(),
        mouseenter: (e) => { e.currentTarget.style.background = 'var(--bg)'; e.currentTarget.style.color = 'var(--text)'; },
        mouseleave: (e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text2)'; },
      },
    });
    settingsBtn.appendChild(iconEl('settings', 14));
    wrap.append(settingsBtn);
  }

  return wrap;
}

function buildValorisationToolbar() {
  // Toolbar MP simplifiée : uniquement la recherche.
  // Les actions globales (date, export, refresh, settings) sont dans la toolbar
  // globale au-dessus des KPIs.
  const v = valEnsureState();
  const wrap = el('div', { style: 'margin-bottom:14px' });

  const inp = el('input', {
    type: 'search', id: 'val-search', placeholder: 'Rechercher (référence, désignation, catégorie…)',
      style: 'width:100%;padding:10px 14px;border:1px solid var(--border);border-radius:10px;background:var(--bg);color:var(--text);font-size:13px;transition:border-color .15s' });
  inp.value = v.query || '';
  inp.addEventListener('input', () => {
    v.query = inp.value;
    renderValorisationTableOnly();
  });
  inp.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      inp.value = ''; v.query = ''; renderValorisationTableOnly();
    }
  });

  wrap.append(inp);
  return wrap;
}

// ── Modal Paramètres MyCouts (superposé, pas de redirection) ──
async function openValorisationSettingsModal() {
  const v = valEnsureState();
  const root = document.getElementById('mroot');
  if (!root) return;
  root.innerHTML = '';
  const overlay = el('div', {
    style: 'position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:9000;display:flex;align-items:center;justify-content:center;padding:20px',
    on: { click: (e) => { if (e.target === overlay) { root.innerHTML = ''; } } },
  });
  const box = el('div', { style: 'background:var(--card);border:1px solid var(--border);border-radius:14px;width:100%;max-width:540px;max-height:90vh;overflow-y:auto;padding:22px' });
  box.appendChild(el('div', { style: 'font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px' }, 'MyCouts'));
  box.appendChild(el('div', { style: 'font-size:17px;font-weight:800;color:var(--text);margin-bottom:14px' }, 'Paramètres globaux'));

  const loadingMsg = el('div', { style: 'padding:18px 0;color:var(--muted);font-size:13px;text-align:center' }, 'Chargement…');
  box.appendChild(loadingMsg);
  overlay.appendChild(box);
  root.appendChild(overlay);

  let settings;
  try {
    settings = await api('/api/pricing/settings');
  } catch (e) {
    loadingMsg.remove();
    box.appendChild(el('div', { style: 'color:var(--danger);font-size:13px' }, 'Erreur : ' + (e?.message || 'chargement impossible')));
    return;
  }
  loadingMsg.remove();

  // Form fields
  const mkInput = (id, value, step, hint) => {
    const inp = el('input', {
      type: 'number', id: id, step: step, min: '0',
      style: 'width:100%;padding:10px 12px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text);font-size:14px;font-variant-numeric:tabular-nums' });
    inp.value = String(value ?? '');
    return inp;
  };
  const mkLabel = (text, hint) => {
    const wrap = el('div', { style: 'margin-bottom:6px;display:flex;align-items:baseline;justify-content:space-between;gap:8px' },
      el('label', { style: 'font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px' }, text)
    );
    if (hint) wrap.appendChild(el('span', { style: 'font-size:10px;color:var(--muted);font-style:italic' }, hint));
    return wrap;
  };

  const rateInp = mkInput('vsm-rate', settings.eur_usd_rate, '0.0001');
  const taxInp = mkInput('vsm-tax', settings.import_tax_pct || 0, '0.01');
  const chargeProdInp = mkInput('vsm-charge-prod', settings.charge_production_pct || 0, '0.01');
  const storageInp = mkInput('vsm-storage', settings.storage_fees_pct || 0, '0.01');
  const contCostInp = mkInput('vsm-cont-cost', settings.default_container_cost_usd, '1');
  const contHalfInp = mkInput('vsm-cont-half', settings.default_half_container_cost_eur || 0, '1');
  const contKgInp = mkInput('vsm-cont-kg', settings.default_container_kg, '1');
  const marginInp = mkInput('vsm-margin', settings.default_margin_eur_m2, '0.0001');

  // Quantités m² par container (renseignées via /settings > Logistique > Importations).
  // Utilisées pour afficher "soit X EUR/m²" sous les 2 champs coût container.
  const qteM2Full = Number(settings.logistique_qte_m2_container_complet || 0);
  const qteM2Half = Number(settings.logistique_qte_m2_demi_container || 0);
  const fmtEurM2 = (cost, qte) => {
    const c = Number(cost || 0);
    if (c <= 0 || qte <= 0) return null;
    const perM2 = c / qte;
    return 'soit ' + perM2.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 4 }) + ' EUR/m²';
  };
  const mkHintDiv = (id) => el('div', { id: id, style: 'font-size:10px;color:var(--muted);margin-top:4px' });

  const fxDate = settings.eur_usd_rate_updated_at
    ? String(settings.eur_usd_rate_updated_at).replace('T', ' ').slice(0, 16)
    : '—';
  const fxSrc = settings.eur_usd_rate_source || '—';

  // -- Taux EUR/USD --
  box.appendChild(mkLabel('Taux EUR / USD', '1 USD vaut N €'));
  const rateRow = el('div', { style: 'display:flex;gap:8px;align-items:center' });
  rateRow.appendChild(rateInp);
  const refreshFxBtn = el('button', {
    type: 'button', title: 'Récupérer le taux courant depuis exchangerate.host',
    style: 'padding:10px 12px;border:1px solid var(--border);border-radius:8px;background:transparent;color:var(--text2);cursor:pointer;display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:600',
  });
  refreshFxBtn.appendChild(iconEl('refresh-ccw', 12));
  refreshFxBtn.appendChild(el('span', null, 'Rafraîchir'));
  refreshFxBtn.addEventListener('click', async () => {
    refreshFxBtn.disabled = true;
    try {
      const r = await api('/api/pricing/settings/refresh-fx', { method: 'POST' });
      rateInp.value = String(r.eur_usd_rate);
      showToast('Taux rafraîchi : 1 USD = ' + Number(r.eur_usd_rate).toLocaleString('fr-FR', { maximumFractionDigits: 4 }) + ' €', 'success');
    } catch (e) {
      showToast('Erreur : ' + (e?.message || 'rafraîchissement impossible'), 'danger');
    } finally {
      refreshFxBtn.disabled = false;
    }
  });
  rateRow.appendChild(refreshFxBtn);
  box.appendChild(rateRow);
  box.appendChild(el('div', { style: 'font-size:10px;color:var(--muted);margin-top:4px;margin-bottom:14px' },
    'Source : ' + fxSrc + ' · MAJ : ' + fxDate));

  // -- Taxe d'importation --
  box.appendChild(mkLabel('Taxe d\'importation (%)', 'Appliquée aux adhésifs cochés « package »'));
  box.appendChild(taxInp);
  box.appendChild(el('div', { style: 'height:14px' }));

  // -- Charge de production --
  box.appendChild(mkLabel('Charge de production (%)', 'Multiplicateur (1 − charge/100) appliqué à la valo PF'));
  box.appendChild(chargeProdInp);
  box.appendChild(el('div', { style: 'height:14px' }));

  // -- Frais de stockage --
  box.appendChild(mkLabel('Frais de stockage (%)', 'Multiplicateur appliqué à la valo PF'));
  box.appendChild(storageInp);
  box.appendChild(el('div', { style: 'height:14px' }));

  // -- Container — coût par défaut (EUR) --
  box.appendChild(mkLabel('Container — coût par défaut (EUR)'));
  box.appendChild(contCostInp);
  const contFullHint = mkHintDiv('vsm-cont-full-hint');
  const setFullHint = () => {
    const txt = fmtEurM2(contCostInp.value, qteM2Full);
    contFullHint.textContent = txt || '';
    contFullHint.style.display = txt ? 'block' : 'none';
  };
  setFullHint();
  contCostInp.addEventListener('input', setFullHint);
  box.appendChild(contFullHint);
  box.appendChild(el('div', { style: 'height:14px' }));

  // -- Demi-container — coût par défaut (EUR) --
  box.appendChild(mkLabel('Demi-container — coût par défaut (EUR)'));
  box.appendChild(contHalfInp);
  const contHalfHint = mkHintDiv('vsm-cont-half-hint');
  const setHalfHint = () => {
    const txt = fmtEurM2(contHalfInp.value, qteM2Half);
    contHalfHint.textContent = txt || '';
    contHalfHint.style.display = txt ? 'block' : 'none';
  };
  setHalfHint();
  contHalfInp.addEventListener('input', setHalfHint);
  box.appendChild(contHalfHint);
  box.appendChild(el('div', { style: 'height:14px' }));

  // -- Default container kg --
  box.appendChild(mkLabel('Container — capacité par défaut (kg)'));
  box.appendChild(contKgInp);
  box.appendChild(el('div', { style: 'height:14px' }));

  // -- Default margin --
  box.appendChild(mkLabel('Marge par défaut (€ / m²)'));
  box.appendChild(marginInp);

  // -- Actions --
  const actions = el('div', { style: 'display:flex;gap:8px;justify-content:flex-end;margin-top:22px;border-top:1px solid var(--border);padding-top:16px' });
  const cancelBtn = el('button', {
    type: 'button',
    style: 'padding:10px 18px;border-radius:10px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-weight:600',
    on: { click: () => { root.innerHTML = ''; } },
  }, 'Annuler');
  const saveBtn = el('button', {
    type: 'button',
    style: 'padding:10px 18px;border-radius:10px;border:none;background:var(--accent);color:#0a0e17;cursor:pointer;font-weight:800',
  }, 'Enregistrer');
  saveBtn.addEventListener('click', async () => {
    saveBtn.disabled = true;
    try {
      const payload = {
        eur_usd_rate: parseFloat(rateInp.value),
        import_tax_pct: parseFloat(taxInp.value || '0'),
        charge_production_pct: parseFloat(chargeProdInp.value || '0'),
        storage_fees_pct: parseFloat(storageInp.value || '0'),
        default_container_cost_usd: parseFloat(contCostInp.value),
        default_half_container_cost_eur: parseFloat(contHalfInp.value || '0'),
        default_container_kg: parseFloat(contKgInp.value),
        default_margin_eur_m2: parseFloat(marginInp.value),
      };
      for (const k of Object.keys(payload)) {
        if (isNaN(payload[k])) {
          throw new Error('Valeur invalide pour « ' + k + ' ».');
        }
      }
      await api('/api/pricing/settings', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      root.innerHTML = '';
      showToast('Paramètres enregistrés.', 'success');
      await loadValorisation();  // Recharge MP avec les nouveaux taux/taxe
      await loadValorisationPF();  // Recharge PF pour appliquer charge prod / stockage
    } catch (e) {
      showToast('Erreur : ' + (e?.message || 'enregistrement impossible'), 'danger');
      saveBtn.disabled = false;
    }
  });
  actions.appendChild(cancelBtn);
  actions.appendChild(saveBtn);
  box.appendChild(actions);
}

function buildValorisation() {
  const v = valEnsureState();
  const root = el('div', { style: 'padding:18px 20px;max-width:1400px;margin:0 auto' });

  const head = el('div', { style: 'margin-bottom:18px' },
    el('h2', { style: 'font-size:20px;font-weight:800;color:var(--text);margin-bottom:4px' }, 'Valorisation du stock'),
    el('p', { style: 'font-size:12px;color:var(--muted)' },
      'Saisie des prix unitaires (€/unité de gestion) et consolidation par catégorie. Direction · Administration · Super admin.')
  );
  root.appendChild(head);

  // Toolbar globale : date + export + refresh + settings (pilote la valo TOTALE)
  root.appendChild(buildValorisationGlobalToolbar());

  // Bandeau « figée au JJ/MM/AAAA » quand une date passée est sélectionnée
  if (v.snapshotDate) {
    const parts = v.snapshotDate.split('-');
    const fr = parts.length === 3 ? (parts[2] + '/' + parts[1] + '/' + parts[0]) : v.snapshotDate;
    const badge = el('div', { style:
      'display:flex;align-items:center;gap:8px;padding:10px 14px;margin-bottom:14px;border:1px solid #f59e0b;border-radius:10px;background:rgba(245,158,11,0.08);color:#c2410c;font-size:13px;font-weight:600' });
    badge.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>';
    badge.appendChild(el('span', null, 'Valorisation figée au ' + fr + ' — quantités et prix reconstitués à cette date. Paramètres globaux actuels (taux USD, taxe, containers, charges de prod).'));
    root.appendChild(badge);
  }

  if (v.loading && !v.items.length) {
    root.appendChild(el('div', { style: 'padding:60px;text-align:center;color:var(--muted);font-size:13px' }, 'Chargement…'));
    return root;
  }

  root.appendChild(buildValorisationKpis());

  // ── Section Matières premières ──
  root.appendChild(buildValorisationMPHeader());
  if (!v.mpCollapsed) {
    root.appendChild(buildValorisationCategoriePills());
    root.appendChild(buildValorisationToolbar());
    const tableWrap = el('div', { id: 'val-table-wrap' });
    tableWrap.appendChild(buildValorisationTable());
    root.appendChild(tableWrap);
  }

  // ── Section Produits finis ──
  root.appendChild(buildValorisationPFSection());

  return root;
}

function renderValorisationTableOnly() {
  // Re-rendu uniquement de la table, pas de la barre de recherche
  // (pour préserver le focus du champ id "val-search")
  const area = document.getElementById('val-table-wrap');
  if (!area) { renderValorisationView(true); return; }
  area.innerHTML = '';
  area.appendChild(buildValorisationTable());
}

function renderValorisationView(fullRebuild) {
  const area = document.getElementById('scroll-area');
  if (!area) return;
  // Préservation focus + position curseur (règle searchbar CLAUDE.md)
  const ae = document.activeElement;
  const focusId = ae && ae.id;
  const caretStart = ae && ae.selectionStart != null ? ae.selectionStart : null;
  const caretEnd = ae && ae.selectionEnd != null ? ae.selectionEnd : null;

  area.innerHTML = '';
  area.appendChild(buildValorisation());

  if (focusId) {
    const elFocus = document.getElementById(focusId);
    if (elFocus) {
      try { elFocus.focus(); } catch (e) {}
      if (caretStart != null) {
        try { elFocus.setSelectionRange(caretStart, caretEnd); } catch (e) {}
      }
    }
  }
  renderValorisationHistoriqueModal();
}

const STOCK_TAB_DOC_TITLES = {
  dashboard: 'Tableau de bord — MyStock — MySifa',
  matieres: 'Matières premières — MyStock — MySifa',
  'produits-finis': 'Produits finis — MyStock — MySifa',
  negoce: 'Produits de négoce — MyStock — MySifa',
  referentiel: 'Référentiel — MyStock — MySifa',
  inventaire: 'Inventaire — MyStock — MySifa',
  reception: 'Réception matière — MyStock — MySifa',
  historique: 'Historique — MyStock — MySifa',
  traca: 'Étiquettes traça — MyStock — MySifa',
  monitoring: 'Monitoring — MyStock — MySifa',
  valorisation: 'Valorisation — MyStock — MySifa',
  production: 'Production — MyStock — MySifa',
};

const STOCK_TAB_MOBILE_TITLES = {
  dashboard: 'Tableau de bord',
  matieres: 'Matières premières',
  'produits-finis': 'Produits finis',
  negoce: 'Produits de négoce',
  referentiel: 'Référentiel',
  inventaire: 'Inventaire',
  reception: 'Réception matière',
  historique: 'Historique',
  traca: 'Étiquettes traça',
  monitoring: 'Monitoring',
  valorisation: 'Valorisation',
  production: 'Production',
};

function stockMobileTabTitle() {
  if (S.selProduit || S.selEmpl) return 'Stock';
  if (S.selMatiere && S.selMatiere.matiere) return S.selMatiere.matiere.reference || 'Matière première';
  return STOCK_TAB_MOBILE_TITLES[S.tab] || 'MyStock';
}

function buildSidebarNavStructure() {
  if (S.tracaOnly) {
    return [{ kind: 'btn', tab: 'traca', icon: 'printer', label: 'Étiquettes traça' }];
  }
  // Fabrication : vue dédiée Production + sections Matières premières + Outils
  if (S.fabStockMode) {
    return [
      { kind: 'sep', label: 'Production' },
      { kind: 'btn', tab: 'production', icon: 'cpu', label: 'Production' },
      { kind: 'sep', label: 'Matières premières' },
      { kind: 'btn', tab: 'matieres', icon: 'layers', label: 'Matières premières' },
      { kind: 'sep', label: 'Outils' },
      { kind: 'btn', tab: 'historique', icon: 'clock', label: 'Historique mouvements' },
      { kind: 'btn', tab: 'traca', icon: 'printer', label: 'Étiquettes traça' },
      { kind: 'btn', tab: 'plan-entrepot', icon: 'map-pin', label: 'Plan entrepôt' },
    ];
  }
  const items = [
    { kind: 'btn', tab: 'dashboard', icon: 'grid', label: 'Tableau de bord' },
    { kind: 'sep', label: 'Matières premières' },
    { kind: 'btn', tab: 'matieres', icon: 'layers', label: 'Matières premières' },
    { kind: 'btn', tab: 'reception', icon: 'inbox', label: 'Réception matière' },
    { kind: 'sep', label: 'Produits' },
    { kind: 'btn', tab: 'produits-finis', icon: 'package', label: 'Produits finis' },
    { kind: 'btn', tab: 'negoce', icon: 'shopping-cart', label: 'Produits de négoce' },
    { kind: 'btn', tab: 'referentiel', icon: 'tag', label: 'Référentiel' },
  ];
  if (!S.stockReadOnly) {
    items.push({ kind: 'btn', tab: 'inventaire', icon: 'clipboard', label: 'Inventaire' });
  }
  if (S.user && ['superadmin', 'direction', 'administration'].includes(S.user.role)) {
    items.push({ kind: 'sep', label: 'Contrôle' });
    items.push({ kind: 'btn', tab: 'monitoring', icon: 'clipboard', label: 'Monitoring' });
    items.push({ kind: 'btn', tab: 'valorisation', icon: 'euro', label: 'Valorisation' });
  }
  items.push(
    { kind: 'sep', label: 'Outils' },
    { kind: 'btn', tab: 'historique', icon: 'clock', label: 'Historique mouvements' },
    { kind: 'btn', tab: 'traca', icon: 'printer', label: 'Étiquettes traça' },
    { kind: 'btn', tab: 'plan-entrepot', icon: 'map-pin', label: 'Plan entrepôt' },
  );
  return items;
}

function renderSidebarNavBtn(n) {
  const children = [iconEl(n.icon, 16), el('span', null, ' ' + n.label)];
  if (n.tab === 'inventaire' && S.invAlertCount) {
    const badge = document.createElement('span');
    badge.style.cssText = 'margin-left:auto;padding:1px 7px;border-radius:999px;font-size:10px;font-weight:800;background:#fb923c;color:#fff;flex-shrink:0';
    badge.textContent = S.invAlertCount;
    children.push(badge);
  }
  return el('button', { cls: 'nav-btn' + (S.tab === n.tab ? ' active' : ''), 'data-tab': n.tab, on: { click: () => goToTab(n.tab) } },
    ...children
  );
}

function renderSidebarItems(items) {
  if (!S.navCollapsed) S.navCollapsed = new Set();
  const nodes = [];
  let currentGroup = null;
  const CHV = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg>';

  items.forEach(item => {
    if (item.kind === 'sep') {
      currentGroup = item.label;
      const collapsed = S.navCollapsed.has(currentGroup);
      const sepEl = document.createElement('div');
      sepEl.className = 'nav-section-label' + (collapsed ? ' ngl-collapsed' : '');
      sepEl.innerHTML = '<span>' + item.label + '</span><span class="ngl-chevron">' + CHV + '</span>';
      sepEl.addEventListener('click', () => {
        const isNowCollapsed = S.navCollapsed.has(item.label);
        if (isNowCollapsed) S.navCollapsed.delete(item.label); else S.navCollapsed.add(item.label);
        sepEl.classList.toggle('ngl-collapsed', !isNowCollapsed);
        let sib = sepEl.nextElementSibling;
        while (sib && !sib.classList.contains('nav-section-label')) {
          sib.style.display = !isNowCollapsed ? 'none' : '';
          sib = sib.nextElementSibling;
        }
      });
      nodes.push(sepEl);
    } else {
      const btn = renderSidebarNavBtn(item);
      if (currentGroup && S.navCollapsed.has(currentGroup)) btn.style.display = 'none';
      nodes.push(btn);
    }
  });
  return nodes;
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
      ...renderSidebarItems(buildSidebarNavStructure())
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
  if(window.MySifaDock&&typeof window.MySifaDock.bootPageWidgets==='function')window.MySifaDock.bootPageWidgets();
  else if(typeof initAiChatWidget==='function')initAiChatWidget();
  S.stockReadOnly = (user.role === 'commercial');
  S.tracaOnly = false;
  // Fabrication : accès limité aux sections Matières premières + Outils, lecture seule
  S.fabStockMode = (user.role === 'fabrication');
  // Charger les fournisseurs FSC
  await loadFournisseursFSC();
  // Charger le référentiel des laizes (utilisé dans modal matière + valorisation)
  await loadLaizesReferentiel();
  // Compteur matières incomplètes (frontal/glassine/complexe)
  loadMatieresIncompleteCount();
  // Charger la liste complète des emplacements depuis la base de données
  await fetchEmplacementsFromDB();
  // Onglet initial via URL param ?tab=...
  const urlParams = new URLSearchParams(window.location.search);
  const urlTab = urlParams.get('tab');
  if (urlTab && ['dashboard','matieres','produits-finis','negoce','referentiel','stock','inventaire','reception','historique','traca','monitoring','valorisation','production','plan-entrepot'].includes(urlTab)) {
    S.tab = urlTab;
  }
  // Deep-link sur une matière ou un produit (ouvre directement le détail)
  const urlMatiereId = parseInt(urlParams.get('matiere') || '', 10);
  const urlProduitId = parseInt(urlParams.get('produit') || '', 10);
  const urlProduitRef = (urlParams.get('ref') || '').trim();
  if (urlMatiereId > 0 && !S.tracaOnly) {
    S.tab = 'matieres';
  } else if ((urlProduitId > 0 || urlProduitRef) && !S.tracaOnly) {
    S.tab = 'produits-finis';
  }
  if (S.tab === 'monitoring' && S.user
      && !['superadmin', 'direction', 'administration'].includes(S.user.role)) {
    S.tab = 'dashboard';
  }
  if (S.tab === 'valorisation' && S.user
      && !['superadmin', 'direction', 'administration'].includes(S.user.role)) {
    S.tab = 'dashboard';
  }
  // Forcer onglet initial selon le mode d'accès restreint
  if (S.tracaOnly) S.tab = 'traca';
  if (S.fabStockMode) {
    if (!['production','matieres','historique','traca','plan-entrepot'].includes(S.tab)) S.tab = 'production';
  }
  render();
  if (S.tab === 'traca') { /* rien à charger */ }
  else if (S.tab === 'reception') { await loadRecepHistory(); }
  else if (S.tab === 'inventaire') { await loadInventaireList(); }
  else if (S.tab === 'matieres') { await loadMatieres(); }
  else if (S.tab === 'produits-finis') { await loadProduitsFinis(); }
  else if (S.tab === 'negoce') { await loadNegoce(); }
  else if (S.tab === 'historique') { await loadHistorique(); }
  else if (S.tab === 'monitoring') { await loadMonitoring(); }
  else if (S.tab === 'valorisation') { await loadValorisation(); }
  else if (S.tab === 'referentiel') { await loadDashboard(); }
  else if (S.tab === 'plan-entrepot') { await loadPlanEntrepot(); }
  else if (S.tab === 'production') { await loadProduction(); }
  else { await loadDashboard(); }
  // Deep-link : ouvrir la matière ou le produit demandé après le chargement
  if (urlMatiereId > 0 && !S.tracaOnly) {
    try { await loadMatiere(urlMatiereId); } catch (e) { /* silencieux */ }
  } else if (urlProduitId > 0 && !S.tracaOnly) {
    try { await loadProduit(urlProduitId); } catch (e) { /* silencieux */ }
  } else if (urlProduitRef && !S.tracaOnly) {
    try { await openPfProduitPage(urlProduitRef, null); } catch (e) { /* silencieux */ }
  }
  // Charger le compteur d'alertes inventaire en arrière-plan (badge sidebar)
  if (!S.tracaOnly && !S.fabStockMode) loadInvAlertCountBackground();
}

init();
</script>
</body>
</html>"""

STOCK_HTML = STOCK_HTML.replace("/*__TRACA_GUIDE__*/", TRACA_GUIDE_SCRIPT_BLOCK)

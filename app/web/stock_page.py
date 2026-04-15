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

router = APIRouter()


@router.get("/stock", response_class=HTMLResponse)
def stock_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/stock", status_code=302)
        raise
    if not user_has_app_access(user, "stock"):
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

/* Sidebar desktop — bloc du bas collé au bas de l’écran, navigation seule zone scrollable */
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
  gap:6px;flex-shrink:0;margin-top:auto;background:var(--card)}.user-chip{padding:10px 12px;border-radius:8px;background:var(--accent-bg)}
.uc-name{font-size:12px;font-weight:600;color:var(--text)}
.uc-role{font-size:10px;color:var(--accent);text-transform:uppercase;letter-spacing:.5px}
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

/* Mobile topbar (alignée sur MyProd) */
.mobile-topbar{display:none;align-items:center;gap:10px;margin-bottom:14px}
.mobile-menu-btn{display:none;align-items:center;justify-content:center;width:40px;height:40px;border-radius:10px;
  border:1px solid var(--border);background:var(--card);color:var(--text2);cursor:pointer;font-family:inherit;flex-shrink:0}
.mobile-menu-btn:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.mobile-home-btn{display:none;align-items:center;justify-content:center;width:40px;height:40px;border-radius:10px;
  border:1px solid var(--border);background:var(--card);color:var(--text2);cursor:pointer;font-family:inherit;margin-left:auto;flex-shrink:0}
.mobile-home-btn:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.mobile-print-btn{display:none;align-items:center;justify-content:center;width:40px;height:40px;border-radius:10px;
  border:1px solid var(--border);background:var(--card);color:var(--text2);cursor:pointer;font-family:inherit;flex-shrink:0}
.mobile-print-btn:hover,.mobile-print-btn.active{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.mobile-topbar-title{font-size:14px;font-weight:800}
.mobile-topbar-sub{font-size:11px;color:var(--muted);margin-top:2px}

/* Sidebar overlay mobile */
.sidebar-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:200}
body.sb-open .sidebar-overlay{display:block}
@media(max-width:900px){
  .sidebar{position:fixed;left:0;top:0;bottom:0;height:auto;max-height:100vh;z-index:300;    transform:translateX(-105%);transition:transform .18s ease;
    box-shadow:0 16px 48px rgba(0,0,0,.55)}
  body.sb-open .sidebar{transform:translateX(0)}
  .mobile-topbar{display:flex;position:fixed;top:0;left:0;right:0;z-index:120;background:var(--bg);padding:10px 18px;border-bottom:1px solid var(--border)}
  .mobile-menu-btn{display:inline-flex}
  .mobile-home-btn{display:inline-flex}
  .mobile-print-btn{display:inline-flex}
  /* La topbar est fixed → on décale uniquement la barre de recherche. */
  body.has-topbar .search-bar-wrap{margin-top:74px}
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

/* ── Calculette flottante ── */
.calc-fab{position:fixed;bottom:max(24px,env(safe-area-inset-bottom,0px));right:max(24px,env(safe-area-inset-right,0px));width:52px;height:52px;border-radius:50%;background:var(--accent);color:var(--bg);border:none;cursor:pointer;z-index:8000;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 18px rgba(0,0,0,.35);transition:transform .15s,filter .15s}
.calc-fab:hover{filter:brightness(1.1);transform:scale(1.07)}
.calc-fab:active{transform:scale(.96)}
.calc-panel{position:fixed;bottom:86px;right:max(20px,env(safe-area-inset-right,0px));width:260px;background:var(--card);border:1px solid var(--border);border-radius:16px;box-shadow:0 12px 40px rgba(0,0,0,.45);z-index:7999;overflow:hidden;animation:calcUp .2s ease-out}
@keyframes calcUp{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
.calc-display{background:var(--bg);padding:10px 14px 6px;text-align:right}
.calc-expr{font-size:11px;color:var(--muted);min-height:16px;font-family:monospace;word-break:break-all}
.calc-val{font-size:26px;font-weight:700;color:var(--text);font-family:monospace;line-height:1.2;word-break:break-all}
.calc-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--border)}
.calc-key{background:var(--card);border:none;padding:0;height:52px;font-size:17px;font-weight:600;color:var(--text);cursor:pointer;font-family:inherit;transition:background .1s}
.calc-key:hover{background:var(--accent-bg)}
.calc-key:active{background:var(--border)}
.calc-key.op{color:var(--accent)}
.calc-key.eq{background:var(--accent);color:var(--bg)}
.calc-key.eq:hover{filter:brightness(1.08)}
.calc-key.fn{color:var(--text2);font-size:14px}
@media(max-width:480px){.calc-panel{right:12px;width:calc(100vw - 24px);bottom:80px}}

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
</style>
</head>
<body>
<div id="root"></div>
<script src="/static/support_widget.js"></script>
<script>
const API = window.location.origin;

// ── State ───────────────────────────────────────────────────────
let S = {
  user: null,
  tab: 'dashboard',
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
};

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
  return fN(n) + '\u00a0' + (Math.abs(n) > 1 ? u + 's' : u);
}
// ── Icons (Feather-ish, inline SVG) ─────────────────────────────
function icon(name, size=16){
  const a = `width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"`;
  const p = {
    'grid': '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>',
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
    const { cls, on, style: s, html, ...rest } = attrs;
    if (cls) e.className = cls;
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

async function loadDashboard() {
  try { const d = await api('/api/stock/dashboard'); if (d) { S.dashboard = d; renderContent(); } } catch(e) {}
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

const STOCK_EMPL_BASE = ['A121','A122','A123','B121','B122','B123','C121','C122','C123'];
const LS_STOCK_EMPL_CUSTOM = 'mysifa_stock_empl_custom';
const STOCK_UNITS_BASE = ['cartons','bobines','étiquettes','palettes','paravents','boîtes'];
const LS_STOCK_UNITS_CUSTOM = 'mysifa_stock_units_custom_v1';

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
  return [...new Set([...STOCK_EMPL_BASE, ...loadPageEmplCustom()])].sort();
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
function hidePageAddEmplDropdown() {
  const list = document.getElementById('stock-page-add-empl-suggestions');
  if (list) list.style.display = 'none';
}
function refreshPageAddEmplDropdownInner() {
  const input = document.getElementById('stock-page-add-empl-input');
  const list = document.getElementById('stock-page-add-empl-suggestions');
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
    row.addEventListener('mousedown', e => { e.preventDefault(); input.value = code; hidePageAddEmplDropdown(); });
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
    hidePageAddEmplDropdown();
    refreshPageAddEmplDropdownInner();
  });
  list.appendChild(addRow);
}
function wireStockPageAddEmplCombo() {
  const input = document.getElementById('stock-page-add-empl-input');
  if (!input || input.dataset.wired === '1') return;
  input.dataset.wired = '1';
  const list = document.getElementById('stock-page-add-empl-suggestions');
  input.addEventListener('focus', () => {
    if (list) { list.style.display = 'block'; refreshPageAddEmplDropdownInner(); }
  });
  input.addEventListener('input', () => {
    if (list) { list.style.display = 'block'; refreshPageAddEmplDropdownInner(); }
  });
  input.addEventListener('blur', () => { setTimeout(hidePageAddEmplDropdown, 200); });
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
function hidePageAddUnitDropdown(){
  const list=document.getElementById('stock-page-add-unit-suggestions');
  if(list) list.style.display='none';
}
function refreshPageAddUnitDropdownInner(){
  const input=document.getElementById('stock-page-add-unit-input');
  const list=document.getElementById('stock-page-add-unit-suggestions');
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
    row.addEventListener('mousedown', e=>{ e.preventDefault(); input.value=lbl; hidePageAddUnitDropdown(); });
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
function wireStockPageAddUnitCombo(){
  const input=document.getElementById('stock-page-add-unit-input');
  if(!input || input.dataset.wired==='1') return;
  input.dataset.wired='1';
  const list=document.getElementById('stock-page-add-unit-suggestions');
  input.addEventListener('focus', ()=>{
    if(list){ list.style.display='block'; refreshPageAddUnitDropdownInner(); }
  });
  input.addEventListener('input', ()=>{
    if(list){ list.style.display='block'; refreshPageAddUnitDropdownInner(); }
  });
  input.addEventListener('blur', ()=>{ setTimeout(hidePageAddUnitDropdown, 200); });
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
      produit_id: r.id, emplacement: empl, type_mouvement: 'entree', quantite: qte
    }) });
    const msg = r.existing
      ? ('Référence déjà en base — ' + fU(qte, unite) + ' ajoutée(s) en ' + empl)
      : ('Produit créé — ' + fU(qte, unite) + ' en ' + empl);
    showToast(msg);
    S.showAddForm = false;
    await loadDashboard();
    renderContent();
  } catch(e) { showToast(e.message, 'error'); }
}

// ── Sidebar toggle ───────────────────────────────────────────────
function toggleSidebar() { S.sidebarOpen = !S.sidebarOpen; document.body.classList.toggle('sb-open', S.sidebarOpen); }
function closeSidebar() { S.sidebarOpen = false; document.body.classList.remove('sb-open'); }

// ── Navigation ──────────────────────────────────────────────────
function goToTab(tab) {
  S.tab = tab; S.selProduit = null; S.selEmpl = null; S.searchResults = null; S.showAddForm = false;
  if (tab !== 'traca') S.tracaPoste = null;
  clearSearch(); closeSidebar();
  updateNavActive();
  renderContent();
  if (tab === 'dashboard') loadDashboard();
  else if (tab === 'inventaire') loadInventaireList();
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
  try {
    if (typeof ZXing === 'undefined') {
      showToast('Chargement scanner...', 'warn');
      await new Promise((res, rej) => {
        const s = document.createElement('script');
        s.src = 'https://cdn.jsdelivr.net/npm/@zxing/library@0.19.1/umd/index.min.js';
        s.onload = res; s.onerror = rej; document.head.appendChild(s);
      });
    }
  } catch(e) { showToast('Impossible de charger le scanner', 'error'); return; }

  S.scanning = true;
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
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
    S.cameraStream = stream; video.srcObject = stream;
    const hints = new Map();
    hints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS, [ZXing.BarcodeFormat.CODE_128,ZXing.BarcodeFormat.EAN_13,ZXing.BarcodeFormat.QR_CODE]);
    const reader = new ZXing.BrowserMultiFormatReader(hints);
    S.barcodeReader = reader;
    reader.decodeFromVideoDevice(null, video, result => {
      if (!result) return;
      const text = result.getText().trim().toUpperCase();
      resultEl.textContent = '✅ ' + text; resultEl.style.color = 'var(--success)';
      setTimeout(() => { stopCamera(overlay); handleScan(text); }, 600);
    });
  } catch(e) { showToast('Accès caméra refusé', 'error'); stopCamera(overlay); }
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
    await submitMouvement({ produit_id: _pid, emplacement: empl, type_mouvement:'entree', quantite: qte, date_entree: dateInp.value||today, note: noteInp.value.trim() });
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

  const emplInp = el('input', { cls:'field-input empl-upper', type:'text', placeholder:'Ex: a123, b211…', value: emplacement, style:{direction:'ltr'} });  emplInpRef = emplInp;
  const suggWrap = el('div', { cls:'empl-suggestions' });
  emplInp.addEventListener('input', e => { emplInp.value = e.target.value.toUpperCase(); searchEmplSugg(emplInp.value, suggWrap); });

  const qteInp = el('input', { cls:'field-input', type:'number', placeholder:'0', min:'0', inputmode:'numeric', style:{direction:'ltr'} });

  const today = new Date().toISOString().slice(0,10);
  const dateInp = el('input', { cls:'field-input', type:'date', value:today });
  const dateField = el('div', { cls:'modal-field', style:{display: type==='sortie' ? 'none' : ''} }, el('label', { cls:'field-label' }, 'Date du stock'), dateInp);

  const noteInp = el('input', { cls:'field-input', type:'text', placeholder:'Réf BL, raison…', style:{direction:'ltr'} });

  const confirmBtn = el('button', { cls:'btn-confirm '+type, on:{ click: async () => {
    const qte = parseFloat(qteInp.value);
    const empl = emplInp.value.trim().toUpperCase();
    if (!empl) { showToast('Emplacement requis','error'); return; }
    if (!qte||qte<=0) { showToast('Quantité requise','error'); return; }
    await submitMouvement({ produit_id, emplacement:empl, type_mouvement:S.modalType, quantite:qte, date_entree:dateInp.value||today, note:noteInp.value.trim() });
  }}}, type==='entree'?'Valider entrée':type==='sortie'?'Valider sortie':'Valider inventaire');

  sheet.append(
    el('span',{cls:'modal-handle'}),
    el('div',{cls:'modal-title'}, '📦 '+ref),
    el('div',{cls:'modal-sub'}, 'Mouvement de stock'),
    typeBtns,
    el('div',{cls:'modal-field'}, el('label',{cls:'field-label'},'Emplacement'), emplInp, suggWrap),
    el('div',{cls:'modal-field'}, el('label',{cls:'field-label'},'Quantité'), qteInp),
    dateField,
    el('div',{cls:'modal-field'}, el('label',{cls:'field-label'},'Commentaire (optionnel)'), noteInp),
    el('div',{cls:'modal-actions'},
      el('button',{cls:'btn-cancel', on:{click:()=>{S.modalMvt=null;overlay.remove();}}},'Annuler'),
      confirmBtn
    )
  );
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
            fD(m.created_at)+' · '+(m.emplacement||'')+(actor?' · '+actor:'')
          ),
          m.note?el('div',{cls:'mvt-note'},m.note):null
        )
      );
    }))
  );
}

function buildDashboard() {
  const d = S.dashboard;
  if (!d) return el('div',{cls:'content'},el('div',{cls:'card-empty'},'Chargement…'));
  const s = d.stats||{};
  return el('div',{cls:'content'},
    el('div',{cls:'stats-grid'},
      el('div',{cls:'stat-card'},el('div',{cls:'stat-label'},'Références'),el('div',{cls:'stat-value accent'},s.nb_refs||0)),
      el('div',{cls:'stat-card'},el('div',{cls:'stat-label'},'Emplacements occupés'),el('div',{cls:'stat-value accent'},s.nb_empl_occupes||0)),
      el('div',{cls:'stat-card'},el('div',{cls:'stat-label'},'Total unités'),el('div',{cls:'stat-value'},fN(s.total_unites||0))),
      el('div',{cls:'stat-card'},el('div',{cls:'stat-label'},'À inventorier'),el('div',{cls:'stat-value warn'},s.nb_a_inventorier||0))
    ),
    ...(!S.stockReadOnly ? [el('div',{cls:'card',style:{overflow:'visible'}},
      el('div',{cls:'card-header'},el('div',{cls:'card-title'},'➕ Ajouter au stock')),
      el('div',{cls:'add-form'},
        (function(){
          const refI = el('input',{cls:'field-input',placeholder:'Référence (neuve ou déjà en base)',autocomplete:'off',style:{direction:'ltr'}});
          const qtyI = el('input',{cls:'field-input',type:'text',inputmode:'decimal',placeholder:'Quantité *',autocomplete:'off',style:{direction:'ltr'}});
          const unitWrap = el('div', { cls: 'empl-combo-wrap' });
          const unitInp = el('input', { cls: 'field-input', type: 'text', id: 'stock-page-add-unit-input',
            placeholder: 'Unité de vente * (ex. cartons, 500 cartons…)', autocomplete: 'off',
            title: 'Obligatoire — suggestions + ligne violette « Autre »', style: { direction: 'ltr' } });
          const unitList = el('div', { cls: 'empl-suggestions', id: 'stock-page-add-unit-suggestions', style: { display: 'none' } });
          unitWrap.appendChild(unitInp);
          unitWrap.appendChild(unitList);
          const emplWrap = el('div', { cls: 'empl-combo-wrap' });
          const emplInp = el('input', { cls: 'field-input empl-upper', type: 'text', id: 'stock-page-add-empl-input',
            placeholder: 'Emplacement * (ex. a121, z999…)', autocomplete: 'off',
            title: 'Obligatoire — suggestions + ligne violette « Ajouter emplacement »', style: { direction: 'ltr' } });
          const emplList = el('div', { cls: 'empl-suggestions', id: 'stock-page-add-empl-suggestions', style: { display: 'none' } });
          emplWrap.appendChild(emplInp);
          emplWrap.appendChild(emplList);
          const comI = el('input',{cls:'field-input',placeholder:'Commentaire (facultatif)',autocomplete:'off',style:{direction:'ltr'}});
          return el('div',{cls:'add-form-inner'},
            el('div',{style:{fontSize:'12px',color:'var(--muted)',marginBottom:'10px',lineHeight:'1.45'}},
              'Même référence qu’un produit existant : une entrée de stock est enregistrée, sans dupliquer la fiche.'),
            el('div',{cls:'add-form-row',style:{gridTemplateColumns:'1fr'}},
              el('div',null,el('label',{cls:'field-label'},'Référence *'),refI)
            ),
            el('div',{cls:'add-form-row'},
              el('div',null,el('label',{cls:'field-label'},'Quantité *'),qtyI),
              el('div',null,el('label',{cls:'field-label'},'Unité de vente *'),unitWrap)
            ),
            el('div',{cls:'add-form-row',style:{gridTemplateColumns:'1fr'}},
              el('div',null,el('label',{cls:'field-label'},'Emplacement *'),emplWrap)
            ),
            el('div',null,el('label',{cls:'field-label'},'Commentaire'),comI),
            el('div',{cls:'add-form-actions'},
              el('button',{cls:'btn',on:{click:async()=>{
                const raw = (refI.value||'').trim();
                const ref = raw.toUpperCase();
                if(!ref){showToast('Référence requise','error');return;}
                const qRaw = (qtyI.value||'').trim();
                const com = (comI.value||'').trim();
                const emplVal = String((emplInp.value||'').trim().toUpperCase());
                if (!emplVal || !isStockEmplacementCode(emplVal)) {
                  showToast('Emplacement obligatoire (une lettre puis des chiffres, ex. Z999)', 'error');
                  return;
                }
                const qte = parseFloat(qRaw.replace(',','.'));
                if (!qRaw || Number.isNaN(qte) || qte <= 0) {
                  showToast('Quantité obligatoire (nombre supérieur à 0)', 'error');
                  return;
                }
                await createProduit(ref, com, qte, emplVal, unitInp.value);
                refI.value=''; qtyI.value=''; comI.value=''; emplInp.value=''; unitInp.value='';
              }}},'Ajouter au stock')
            )          );
        })()
      )
    )] : []),
    buildMvtHistory(d.derniers_mouvements||[])
  );
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
  { id:'dsi',        label:'DSI',          icon:'cpu',       color:'#64748b', colorBg:'rgba(100,116,139,.12)' },
  { id:'repiquage',  label:'Repiquage',    icon:'atelier',   color:'#64748b', colorBg:'rgba(100,116,139,.12)' },
  { id:'logistique', label:'Logistique',   icon:'truck',     color:'#10b981', colorBg:'rgba(16,185,129,.12)' },
];

const TRACA_FORMATS = [
  { id:'a4',     label:'A4',        dims:'210×297 mm' },
  { id:'105x50', label:'105×50 mm', dims:'105×50 mm'  },
  { id:'40x20',  label:'40×20 mm',  dims:'40×20 mm'   },
];

// { id, label, format, postes[], printer (null=non configurée) }
const TRACA_ETIQUETTES = [
  { id:'nb_palettes',  label:'Nombre de palettes',            format:'105x50', postes:['logistique','cohesio1','cohesio2'], printer:null },
  { id:'id_palette',   label:'Identification palette',         format:'105x50', postes:['logistique'],                      printer:null },
  { id:'id_carton',    label:'Identification carton',          format:'40x20',  postes:['cohesio1','cohesio2'],             printer:null },
  { id:'id_bobine',    label:'Identification bobine',          format:'40x20',  postes:['cohesio1','cohesio2'],             printer:null },
  { id:'id_plaque',    label:'Identification plaques de découpe', format:'a4',  postes:['bureaux'],                         printer:null },
];

function buildNbPalettesForm(etiq) {
  let _ref = '';
  let _n = '';

  const previewGrid = el('div',{cls:'etiq-preview-grid'});
  const previewTitle = el('div',{cls:'etiq-preview-title'},'Renseignez la référence et le nombre de palettes pour voir l\'aperçu.');

  function updatePreview() {
    previewGrid.innerHTML = '';
    const n = parseInt(_n) || 0;
    const ref = _ref.trim();
    if (!ref || n < 1) {
      previewTitle.textContent = 'Renseignez la référence et le nombre de palettes pour voir l\'aperçu.';
      return;
    }
    previewTitle.textContent = n + ' étiquette' + (n > 1 ? 's' : '') + ' — ' + ref;
    const shown = Math.min(n, 10);
    for (let i = 1; i <= shown; i++) {
      const card = el('div',{cls:'etiq-label-card'},
        el('div',{cls:'etiq-lbl-brand'},'MySifa'),
        el('div',{cls:'etiq-lbl-ref'}, ref),
        el('div',{cls:'etiq-lbl-palette'}, 'PALETTE\u00a0' + i + '/' + n)
      );
      previewGrid.appendChild(card);
    }
    if (n > 10) {
      previewGrid.appendChild(
        el('div',{cls:'etiq-more-note'}, '+ ' + (n-10) + ' étiquette' + (n-10>1?'s':'') + ' supplémentaire' + (n-10>1?'s':'') + ' (non affichées)')
      );
    }
  }

  function doPrint() {
    const n = parseInt(_n) || 0;
    const ref = _ref.trim();
    if (!ref) { showToast('Référence produit requise', 'error'); return; }
    if (n < 1 || n > 500) { showToast('Nombre de palettes invalide (1–500)', 'error'); return; }

    let labelsHtml = '';
    for (let i = 1; i <= n; i++) {
      labelsHtml += `<div class="label"><div class="brand">MySifa</div><div class="ref">${ref}</div><div class="palette">PALETTE&nbsp;${i}/${n}</div></div>`;
    }
    const printWin = window.open('', '_blank');
    if (!printWin) { showToast('Le navigateur a bloqué la fenêtre d\'impression — autorisez les popups.', 'error'); return; }
    printWin.document.write(`<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8">
<title>Palettes — ${ref}</title>
<style>
  @page { size: 105mm 50mm; margin: 0; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: Arial, Helvetica, sans-serif; background: #fff; }
  .label { width: 105mm; height: 50mm; padding: 3mm 4mm; display: flex;
           flex-direction: column; justify-content: space-between;
           page-break-after: always; page-break-inside: avoid;
           border: 0.3mm solid #000; }
  .label:last-child { page-break-after: auto; }
  .brand { font-size: 7pt; color: #999; letter-spacing: 0.3pt; text-transform: uppercase; }
  .ref { font-size: 16pt; font-weight: 700; letter-spacing: 0.3pt;
         flex: 1; display: flex; align-items: center; word-break: break-all; }
  .palette { font-size: 22pt; font-weight: 900; letter-spacing: 1pt; text-align: right; }
</style></head><body>${labelsHtml}
<script>window.onload = function(){ window.focus(); window.print(); }<\/script>
</body></html>`);
    printWin.document.close();
  }

  const refInp = el('input',{cls:'field-input',placeholder:'Ex. 1077/0026',autocomplete:'off',style:{direction:'ltr',textTransform:'uppercase'}});
  refInp.addEventListener('input', e => { _ref = e.target.value.toUpperCase(); updatePreview(); });

  const nInp = el('input',{cls:'field-input',type:'number',min:'1',max:'500',placeholder:'Ex. 4',style:{width:'110px'}});
  nInp.addEventListener('input', e => { _n = e.target.value; updatePreview(); });

  const printBtn = el('button',{cls:'traca-print-btn',style:{width:'100%',padding:'12px',fontSize:'14px',marginTop:'14px',justifyContent:'center'}},
    iconEl('printer',16), '\u00a0 Imprimer les étiquettes');
  printBtn.addEventListener('click', doPrint);

  return el('div',null,
    el('div',{cls:'etiq-form-row'},
      el('div',{cls:'etiq-form-field',style:{flex:'1',minWidth:'160px'}},
        el('label',{cls:'etiq-form-label'},'Référence produit *'), refInp),
      el('div',{cls:'etiq-form-field'},
        el('label',{cls:'etiq-form-label'},'Nb palettes *'), nInp)
    ),
    el('div',{cls:'etiq-preview-section'},
      previewTitle,
      previewGrid
    ),
    printBtn
  );
}

function openTracaPrint(etiq) {
  S.tracaPrintModal = etiq;
  const overlay = el('div', { cls:'modal-overlay', on:{ click:e=>{ if(e.target===overlay){ S.tracaPrintModal=null; overlay.remove(); } } } });
  const fmtObj = TRACA_FORMATS.find(f=>f.id===etiq.format)||{label:etiq.format,dims:''};

  // Contenu du formulaire selon le type d'étiquette
  let formContent;
  if (etiq.id === 'nb_palettes') {
    formContent = buildNbPalettesForm(etiq);
  } else {
    formContent = el('div',{cls:'traca-dev-banner'},
      iconEl('settings',14),
      'Formulaire en cours de développement — disponible prochainement.'
    );
  }

  const sheet = el('div', { cls:'modal-sheet' },
    el('span',{cls:'modal-handle'}),
    el('div',{cls:'modal-title'}, iconEl('printer',17), '\u00a0'+etiq.label),
    el('div',{cls:'modal-sub'}, 'Format\u00a0: ',el('strong',null,fmtObj.label),
      etiq.printer ? '\u00a0·\u00a0'+etiq.printer : '\u00a0·\u00a0Imprimante non configurée'),
    formContent,
    el('button',{cls:'btn-ghost',style:{width:'100%',marginTop:'10px'},on:{click:()=>{ overlay.remove(); S.tracaPrintModal=null; }}},'Fermer')
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
  const list = S.inventaireList||[];
  return el('div',{cls:'content'},
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
  else if (S.tab === 'inventaire') content = buildInventaire();
  else if (S.tab === 'traca') content = buildTraca();
  else content = buildDashboard();

  if (content) area.appendChild(content);
  if (S.tab === 'dashboard' && !S.selProduit && !S.selEmpl){
    requestAnimationFrame(() => {
      wireStockPageAddEmplCombo();
      wireStockPageAddUnitCombo();
    });
  }
}

// ── Calculette flottante ────────────────────────────────────────
(function(){
  let _open=false, _expr='', _val='0', _justEq=false;
  const CALC_SVG='<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="2" width="16" height="20" rx="2"/><line x1="8" y1="6" x2="16" y2="6"/><circle cx="8.5" cy="11" r=".8" fill="currentColor" stroke="none"/><circle cx="12" cy="11" r=".8" fill="currentColor" stroke="none"/><circle cx="15.5" cy="11" r=".8" fill="currentColor" stroke="none"/><circle cx="8.5" cy="15" r=".8" fill="currentColor" stroke="none"/><circle cx="12" cy="15" r=".8" fill="currentColor" stroke="none"/><circle cx="15.5" cy="15" r=".8" fill="currentColor" stroke="none"/><line x1="8" y1="19" x2="16" y2="19"/></svg>';
  const KEYS=[['C','⌫','%','÷'],['7','8','9','×'],['4','5','6','−'],['1','2','3','+'],[  '0','.','=']];
  function _press(k){
    if(k==='C'){_expr='';_val='0';_justEq=false;return;}
    if(k==='⌫'){_val=_val.length>1?_val.slice(0,-1):'0';return;}
    if(k==='%'){try{_val=String(parseFloat(_val)/100);}catch(e){}return;}
    if(k==='='){
      try{
        const e=(_justEq?_val:_expr+_val).replace(/÷/g,'/').replace(/×/g,'*').replace(/−/g,'-');
        const r=Function('"use strict";return ('+e+')')();
        _expr=e+'=';_val=String(Math.round(r*1e10)/1e10);_justEq=true;
      }catch(e){_val='Err';_expr='';_justEq=false;}
      return;
    }
    if(['+','-','×','÷','−'].includes(k)){
      if(_justEq){_expr=_val+k;_val='0';_justEq=false;return;}
      _expr+=_val+k;_val='0';return;
    }
    if(_justEq){_expr='';_justEq=false;}
    if(k==='.'){if(_val.includes('.'))return;_val+='.';return;}
    _val=(_val==='0'||_val==='-0')?(_val.startsWith('-')?'-'+k:k):_val+k;
  }
  function _upd(){
    const cv=document.querySelector('#_calc_panel ._cv');
    const ce=document.querySelector('#_calc_panel ._ce');
    const p=document.getElementById('_calc_panel');
    if(cv)cv.textContent=_val;
    if(ce)ce.textContent=_expr;
    if(p)p.style.display=_open?'':'none';
  }
  function _mount(){
    if(document.getElementById('_calc_fab'))return;
    const fab=document.createElement('button');
    fab.id='_calc_fab';fab.className='calc-fab';fab.title='Calculette';
    fab.innerHTML=CALC_SVG;
    fab.onclick=()=>{_open=!_open;_upd();};
    document.body.appendChild(fab);
    const panel=document.createElement('div');
    panel.id='_calc_panel';panel.className='calc-panel';panel.style.display='none';
    const disp=document.createElement('div');disp.className='calc-display';
    const ce=document.createElement('div');ce.className='calc-expr _ce';
    const cv=document.createElement('div');cv.className='calc-val _cv';cv.textContent='0';
    disp.append(ce,cv);panel.appendChild(disp);
    const grid=document.createElement('div');grid.className='calc-grid';
    KEYS.forEach(row=>row.forEach(k=>{
      const b=document.createElement('button');
      b.className='calc-key'+(k==='='?' eq':['+','-','×','÷','−'].includes(k)?' op':['C','⌫','%'].includes(k)?' fn':'');
      b.textContent=k;
      if(k==='0')b.style.gridColumn='span 2';
      b.onclick=()=>{_press(k);_upd();};
      grid.appendChild(b);
    }));
    panel.appendChild(grid);document.body.appendChild(panel);
    document.addEventListener('keydown',e=>{
      if(!_open)return;
      if(e.key>='0'&&e.key<='9'){_press(e.key);_upd();}
      else if(e.key==='.'){_press('.');_upd();}
      else if(e.key==='+'||e.key==='-'){_press(e.key==='+'?'+':'−');_upd();}
      else if(e.key==='*'){_press('×');_upd();}
      else if(e.key==='/'){e.preventDefault();_press('÷');_upd();}
      else if(e.key==='Enter'||e.key==='='){_press('=');_upd();}
      else if(e.key==='Escape'){_open=false;_upd();}
      else if(e.key==='Backspace'){_press('⌫');_upd();}
    });
  }
  window._calcMountStock=_mount;
})();

function render() {
  // La modale "contact support" est montée sur <body> : il faut la synchroniser
  // avec l'état à chaque rendu pour éviter un overlay "figé" (ex: reste sur "Envoi…").
  try{
    document.querySelectorAll('.contact-modal-overlay').forEach(n=>n.remove());
    document.querySelectorAll('.unit-modal-overlay').forEach(n=>n.remove());
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
      ...[
        { tab:'dashboard',  icon:'grid', label:'Dashboard' },
        ...(!S.stockReadOnly ? [{ tab:'inventaire', icon:'clipboard', label:'Inventaire' }] : []),
        { tab:'traca', icon:'printer', label:'Étiquettes traça' },
      ].map(n => el('button', { cls:'nav-btn'+(S.tab===n.tab?' active':''), 'data-tab':n.tab, on:{ click:()=>goToTab(n.tab) } },
        iconEl(n.icon,16),
        el('span', null, ' ' + n.label)
      ))
    ),
    el('div', { cls:'sidebar-bottom' },
      el('button', { cls:'nav-btn nav-btn--mysifa-portal', on:{ click:()=>{ window.location.href='/'; } } },
        el('span', { cls:'mysifa-back-preamble' }, '← Retour '),
        el('span', { cls:'mysifa-back-brand' }, 'My', el('span', { cls:'mysifa-back-accent' }, 'Sifa'))
      ),      S.user ? el('div', { cls:'user-chip' },
        el('div', { cls:'uc-name' }, S.user.nom||''),
        el('div', { cls:'uc-role' }, S.user.role||'')
      ) : null,
      (() => {
        if(!S.user) return null;
        const b=el('button',{cls:'support-btn',type:'button',on:{click:()=>{S.contactOpen=true; render();}}});
        const ico=el('span',{cls:'support-ico'}); ico.innerHTML=window.MySifaSupport?.iconSvg?.()||'';
        b.append(ico, el('span',null,'Contacter le support'));
        return b;
      })(),
      el('button', { cls:'theme-btn', on:{ click:()=>{ document.body.classList.toggle('light'); localStorage.setItem('theme',document.body.classList.contains('light')?'light':'dark'); render(); } } },
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
        el('div', { cls:'mobile-topbar-title' }, 'Stock'),
        el('div', { cls:'mobile-topbar-sub' }, 'Inventaire, mouvements et emplacements')
      ),
      el('button', { cls:'mobile-print-btn'+(S.tab==='traca'?' active':''), on:{ click:()=>goToTab('traca') }, attrs:{ 'aria-label':'Étiquettes traça', type:'button', title:'Étiquettes traçabilité' } },
        el('span', { attrs:{ style:'display: inline-flex; align-items: center; flex-shrink: 0;' } }, iconEl('printer',20))
      ),
      el('button', { cls:'mobile-home-btn', on:{ click:()=>window.location.href='/' }, attrs:{ 'aria-label':'Accueil', type:'button' } },
        el('span', { attrs:{ style:'display: inline-flex; align-items: center; flex-shrink: 0;' } }, iconEl('home',20))
      )
    ),
    buildSearchBar(),
    el('div', { cls:'scroll-area', id:'scroll-area' })
  );

  layout.append(sidebar, main);
  root.appendChild(layout);

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
        const inp=document.getElementById('stock-page-add-unit-input');
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

  renderContent();

  // Calculette flottante (montée une seule fois, persiste entre les rendus)
  window._calcMountStock && window._calcMountStock();
}

async function init() {
  if (localStorage.getItem('theme')==='light') document.body.classList.add('light');
  document.body.classList.add('has-topbar');
  const user = await api('/api/auth/me').catch(()=>null);
  if (!user) { window.location.href='/'; return; }
  S.user = user;
  S.stockReadOnly = (user.role === 'commercial');
  render();
  await loadDashboard();
}

init();
</script>
</body>
</html>"""

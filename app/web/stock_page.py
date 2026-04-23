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

/* ── Réception matière ─────────────────────────────────────── */
.recep-page{padding:20px;max-width:860px;margin:0 auto;display:flex;flex-direction:column;gap:20px}
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
.recep-fourn-inp:focus{border-color:var(--accent)}
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
<div id="root"></div>
<script src="/static/support_widget.js"></script>
<script>
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
    if (Array.isArray(data) && data.length) FOURNISSEURS_FSC = data;
  } catch(e) { /* fallback: keep existing array */ }
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
  // Fabrication : accès limité au traça
  if (S.tracaOnly && tab !== 'traca') return;
  // Arrêter la caméra si on quitte l'onglet réception
  if (tab !== 'reception' && S.recepScanning) recepStopCamera();
  S.tab = tab; S.selProduit = null; S.selEmpl = null; S.searchResults = null; S.showAddForm = false;
  if (tab !== 'traca') S.tracaPoste = null;
  clearSearch(); closeSidebar();
  updateNavActive();
  renderContent();
  if (tab === 'dashboard') loadDashboard();
  else if (tab === 'inventaire') loadInventaireList();
  else if (tab === 'reception') loadRecepHistory();
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

  // Checkbox Expédition (uniquement pour les sorties)
  let expCheckbox = null;
  let expWrap = null;
  if (type === 'sortie') {
    expWrap = el('div', { cls:'modal-field', style:{display:'flex',alignItems:'center',gap:'8px',marginTop:'8px'} });
    expCheckbox = el('input', { type:'checkbox', id:'expedition-check', style:{cursor:'pointer'} });
    const expLabel = el('label', { htmlFor:'expedition-check', style:{cursor:'pointer',fontSize:'13px',color:'var(--text1)'} }, 'Expédition');
    expWrap.append(expCheckbox, expLabel);
    
    // Toggle note input based on checkbox
    expCheckbox.addEventListener('change', e => {
      if (e.target.checked) {
        noteInp.value = 'Expédition';
        noteInp.disabled = true;
        noteInp.style.opacity = '0.5';
      } else {
        noteInp.value = '';
        noteInp.disabled = false;
        noteInp.style.opacity = '1';
      }
    });
  }

  const confirmBtn = el('button', { cls:'btn-confirm '+type, on:{ click: async () => {
    const qte = parseFloat(qteInp.value);
    const empl = emplInp.value.trim().toUpperCase();
    if (!empl) { showToast('Emplacement requis','error'); return; }
    if (!qte||qte<=0) { showToast('Quantité requise','error'); return; }
    const finalNote = (expCheckbox && expCheckbox.checked) ? 'Expédition' : noteInp.value.trim();
    await submitMouvement({ produit_id, emplacement:empl, type_mouvement:S.modalType, quantite:qte, date_entree:dateInp.value||today, note:finalNote });
  }}}, type==='entree'?'Valider entrée':type==='sortie'?'Valider sortie':'Valider inventaire');

  sheet.append(
    el('span',{cls:'modal-handle'}),
    el('div',{cls:'modal-title'}, '📦 '+ref),
    el('div',{cls:'modal-sub'}, 'Mouvement de stock'),
    typeBtns,
    el('div',{cls:'modal-field'}, el('label',{cls:'field-label'},'Emplacement'), emplInp, suggWrap),
    el('div',{cls:'modal-field'}, el('label',{cls:'field-label'},'Quantité'), qteInp),
    dateField,
    el('div',{cls:'modal-field'}, el('label',{cls:'field-label'},'Commentaire (optionnel)'), noteInp, expWrap||null),
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
      el('div',{cls:'stat-card'},el('div',{cls:'stat-label'},'Emplacements occupés'),el('div',{cls:'stat-value accent'},s.nb_empl_occupes||0))
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
  else if (S.tab === 'reception') content = buildReception();
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

// ── Réception matière ───────────────────────────────────────────

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

async function recepStartCamera() {
  const video = document.getElementById('recep-video');
  if (!video) return;
  try {
    // Charger ZXing si nécessaire
    if (typeof ZXing === 'undefined') {
      await new Promise((res, rej) => {
        const s = document.createElement('script');
        s.src = 'https://cdn.jsdelivr.net/npm/@zxing/library@0.19.1/umd/index.min.js';
        s.onload = res; s.onerror = rej; document.head.appendChild(s);
      });
    }
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } }
    });
    S.recepStream = stream;
    S.recepScanning = true;
    video.srcObject = stream;
    await video.play();
    renderContent();
    recepScanLoop();
  } catch(e) {
    showToast('Caméra non disponible : ' + e.message, 'error');
    S.recepScanning = false; S.recepStream = null; renderContent();
  }
}

function recepStopCamera() {
  if (S.recepStream) { S.recepStream.getTracks().forEach(t => t.stop()); S.recepStream = null; }
  if (S.recepBarcodeReader) { try { S.recepBarcodeReader.reset(); } catch(e) {} S.recepBarcodeReader = null; }
  S.recepScanning = false;
  renderContent();
}

let _recepLastCode = null;
let _recepLastCodeTs = 0;

async function recepScanLoop() {
  if (!S.recepScanning) return;
  const video = document.getElementById('recep-video');
  if (!video || video.readyState < 2) { setTimeout(recepScanLoop, 200); return; }

  if (typeof ZXing === 'undefined') {
    showToast('Chargement du scanner...', 'warn');
    setTimeout(recepScanLoop, 500);
    return;
  }

  const hints = new Map();
  hints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS, [
    ZXing.BarcodeFormat.CODE_128,
    ZXing.BarcodeFormat.CODE_39,
    ZXing.BarcodeFormat.EAN_13,
    ZXing.BarcodeFormat.EAN_8,
    ZXing.BarcodeFormat.UPC_A,
    ZXing.BarcodeFormat.UPC_E,
    ZXing.BarcodeFormat.QR_CODE,
    ZXing.BarcodeFormat.DATA_MATRIX,
    ZXing.BarcodeFormat.AZTEC,
    ZXing.BarcodeFormat.PDF_417
  ]);
  S.recepBarcodeReader = new ZXing.BrowserMultiFormatReader(hints);

  const loop = async () => {
    if (!S.recepScanning) return;
    try {
      const result = await S.recepBarcodeReader.decodeFromVideoElement(video);
      if (result) {
        const code = result.getText().trim();
        const now = Date.now();
        // Éviter les doublons immédiats (même code dans les 2 secondes)
        if (code !== _recepLastCode || now - _recepLastCodeTs > 2000) {
          _recepLastCode = code;
          _recepLastCodeTs = now;
          recepAddCode(code);
        }
      }
    } catch(e) { /* ignore frame errors */ }
    if (S.recepScanning) requestAnimationFrame(loop);
  };
  requestAnimationFrame(loop);
}

async function recepValider() {
  if (!S.recepItems.length) return;
  if (!S.recepFournisseur) {
    showToast('Veuillez sélectionner un fournisseur avant de valider la réception', 'error');
    return;
  }
  const fsc = FOURNISSEURS_FSC.find(f => f.nom === S.recepFournisseur);
  try {
    const codes = S.recepItems.map(i => i.code);
    const d = await api('/api/stock/receptions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ codes, note: S.recepNote, fournisseur: S.recepFournisseur, certificat_fsc: fsc ? fsc.certificat : '' }),
    });
    if (d && d.success) {
      showToast(d.nb_bobines + ' bobine' + (d.nb_bobines > 1 ? 's' : '') + ' enregistrée' + (d.nb_bobines > 1 ? 's' : ''));
      S.recepItems = []; S.recepNote = ''; S.recepFournisseur = ''; S.recepFournisseurSearch = ''; S.recepFournisseurOpen = false;
      recepStopCamera();
      await loadRecepHistory();
    }
  } catch(e) { showToast('Erreur : ' + e.message, 'error'); }
}

function buildReception() {
  const wrap = el('div', { cls: 'recep-page' });

  // Titre
  wrap.appendChild(el('div', { cls: 'recep-title' }, 'Réception ', el('span', null, 'matière')));

  // ── Grille scanner + saisie manuelle ──
  const grid = el('div', { cls: 'recep-layout' });

  // Colonne gauche : caméra
  const camCard = el('div', { cls: 'recep-card' },
    el('div', { cls: 'recep-card-title' }, iconEl('scan', 14), ' Scanner une bobine')
  );

  if (S.recepScanning) {
    const videoWrap = el('div', { cls: 'recep-video-wrap' });
    const video = el('video', { id: 'recep-video', cls: 'recep-video', attrs: { autoplay: 'true', playsinline: 'true', muted: 'true' } });
    const frame = el('div', { cls: 'recep-scan-frame' });
    const line  = el('div', { cls: 'recep-scan-line' });
    frame.appendChild(line);
    videoWrap.append(video, frame);
    camCard.appendChild(videoWrap);
    camCard.appendChild(el('button', { cls: 'btn-recep btn-recep-danger', on: { click: recepStopCamera } }, iconEl('x', 14), ' Arrêter le scan'));
    // Démarrer le flux après rendu
    setTimeout(() => {
      const v = document.getElementById('recep-video');
      if (v && S.recepStream) { v.srcObject = S.recepStream; v.play().catch(() => {}); recepScanLoop(); }
    }, 80);
  } else {
    const placeholder = el('div', { cls: 'recep-cam-placeholder' },
      iconEl('scan', 40),
      el('div', null, 'Appuyez sur "Démarrer" pour activer la caméra')
    );
    camCard.appendChild(placeholder);
    camCard.appendChild(el('button', { cls: 'btn-recep btn-recep-primary', on: { click: () => {
      // Monter la vidéo avant de démarrer le stream
      S.recepScanning = true; renderContent();
      setTimeout(recepStartCamera, 80);
    }}}, iconEl('scan', 14), ' Démarrer le scan'));
  }
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

  // ── Barre de recherche fournisseur ──
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
  // Afficher le certificat FSC si fournisseur sélectionné
  if (S.recepFournisseur) {
    const fsc = FOURNISSEURS_FSC.find(f => f.nom === S.recepFournisseur);
    if (fsc) {
      fourWrap.appendChild(el('div', { cls: 'recep-fourn-fsc' }, 'Certificat FSC : ', el('strong', null, fsc.certificat), ' — Licence : ', el('strong', null, fsc.licence)));
    }
  }
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
    S.recepHistory.forEach(lot => {
      const dateStr = lot.created_at ? lot.created_at.slice(0,16).replace('T', ' ') : '—';
      const isOpen = S.recepExpandedId === lot.id;
      const row = el('div', { cls: 'recep-hist-row', on: { click: () => {
        S.recepExpandedId = isOpen ? null : lot.id;
        renderContent();
      }}},
        el('span', { cls: 'recep-hist-date' }, dateStr),
        el('span', { cls: 'recep-hist-count' }, lot.nb_bobines + ' bobine' + (lot.nb_bobines !== 1 ? 's' : '')),
        el('span', { cls: 'recep-hist-note' }, lot.note || ''),
        el('span', { cls: 'recep-hist-four' }, lot.fournisseur || ''),
        el('span', { cls: 'recep-hist-user' }, lot.created_by_name || '')
      );
      hist.appendChild(row);
      if (isOpen && lot.items && lot.items.length) {
        const detail = el('div', { cls: 'recep-hist-detail' });
        lot.items.forEach(code => detail.appendChild(el('span', { cls: 'recep-hist-chip' }, code)));
        hist.appendChild(detail);
      }
    });
  }
  wrap.appendChild(hist);
  return wrap;
}

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
      ...(S.tracaOnly
        ? [{ tab:'traca', icon:'printer', label:'Étiquettes traça' }]
        : [
            { tab:'dashboard',  icon:'grid', label:'Dashboard' },
            ...(!S.stockReadOnly ? [{ tab:'inventaire', icon:'clipboard', label:'Inventaire' }] : []),
            { tab:'reception', icon:'inbox', label:'Réception matière' },
            { tab:'traca', icon:'printer', label:'Étiquettes traça' },
          ]
      ).map(n => el('button', { cls:'nav-btn'+(S.tab===n.tab?' active':''), 'data-tab':n.tab, on:{ click:()=>goToTab(n.tab) } },
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
    S.tracaOnly ? null : buildSearchBar(),
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
  // Fabrication : accès restreint à l'onglet traça uniquement
  S.tracaOnly = (user.role === 'fabrication');
  // Charger les fournisseurs FSC
  await loadFournisseursFSC();
  // Onglet initial via URL param ?tab=...
  const urlTab = new URLSearchParams(window.location.search).get('tab');
  if (urlTab && ['dashboard','stock','inventaire','reception','traca'].includes(urlTab)) {
    S.tab = urlTab;
  }
  // Forcer traça si accès restreint
  if (S.tracaOnly) S.tab = 'traca';
  render();
  if (S.tab === 'traca') { /* rien à charger */ }
  else if (S.tab === 'reception') { await loadRecepHistory(); }
  else if (S.tab === 'inventaire') { await loadInventaireList(); }
  else { await loadDashboard(); }
}

init();
</script>
</body>
</html>"""

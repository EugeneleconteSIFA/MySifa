from config import APP_VERSION, APP_META_DESCRIPTION, APP_PAGE_TITLE, THEME_COLOR_META, ENV_NAME, IS_STAGING
from app.web.expe_assets import (
    EXPE_CARTE_FRANCE_CSS,
    EXPE_CARTE_FRANCE_JS,
    EXPE_COMPARATEUR_CSS,
    EXPE_COMPARATEUR_JS,
    EXPE_DEVIS_CSS,
    EXPE_DEVIS_JS,
    EXPE_TRANSPORTEURS_CSS,
    EXPE_TRANSPORTEURS_JS,
)

_FRONTEND_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="__META_DESCRIPTION__">
<link rel="icon" href="/static/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/static/favicon__FAV_SFX__-32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/static/favicon__FAV_SFX__-16.png">
<link rel="icon" type="image/png" sizes="512x512" href="/static/mys_icon__FAV_SFX2___512.png">
<link rel="apple-touch-icon" __TOUCH_ICON__>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon__FAV_SFX2___192.png">
<link rel="icon" type="image/png" sizes="1024x1024" href="/static/mys_icon__FAV_SFX2___1024.png">
<link rel="manifest" href="__MANIFEST__">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="__BRAND__">
<meta name="theme-color" content="#0a0e17">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="mobile-web-app-capable" content="yes">
<title>__PAGE_TITLE__</title>
<link rel="stylesheet" href="/static/support_widget.css">
<link rel="stylesheet" href="/static/mysifa_theme.css">
<link rel="stylesheet" href="/static/mysifa_user_chip.css">
<link rel="stylesheet" href="/static/mysifa_ai_chat.css">
<link rel="stylesheet" href="/static/mysifa_dock.css">
<link rel="stylesheet" href="/static/mysifa_postit.css">
<link rel="stylesheet" href="/static/mysifa_resize.css">
<link rel="stylesheet" href="/static/mysifa_cmdk.css">
<link rel="stylesheet" href="/static/mysifa_landscape.css">
<link rel="stylesheet" href="/static/motion.css">
<style>
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;
  --muted:#94a3b8;--accent:#22d3ee;--accent-bg:rgba(34,211,238,0.12);
  --filter-input-bg:#1c2838;
  --success:#34d399;--warn:#fbbf24;--danger:#f87171;
  --pf-entree:#059669;--pf-sortie:#dc2626;
  --c1:#22d3ee;--c2:#a78bfa;--c3:#34d399;--c4:#fbbf24;--c5:#f87171
}
body.light{
  --bg:#f1f5f9;--card:#ffffff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;
  --muted:#94a3b8;--accent:#0891b2;--accent-bg:rgba(8,145,178,0.10);
  --filter-input-bg:#ffffff;
  --success:#059669;--warn:#d97706;--danger:#dc2626;
  --pf-entree:#047857;--pf-sortie:#b91c1c;
  --c1:#0891b2;--c2:#7c3aed;--c3:#059669;--c4:#d97706;--c5:#dc2626
}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;overflow-x:hidden}
/* ── Fond animé ── */
body::before{
  content:"";
  position:fixed;inset:0;
  pointer-events:none;z-index:0;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='28' height='28'%3E%3Ccircle cx='1.5' cy='1.5' r='1.2' fill='rgba(255,255,255,0.07)'/%3E%3C/svg%3E");
  background-size:28px 28px;
  background-repeat:repeat;
}
body.light::before{
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='28' height='28'%3E%3Ccircle cx='1.5' cy='1.5' r='1.2' fill='rgba(0,0,0,0.055)'/%3E%3C/svg%3E");
}
body::after{
  content:"";
  position:fixed;inset:0;
  pointer-events:none;z-index:0;
  background-image:
    radial-gradient(ellipse 700px 420px at 20% 40%,rgba(34,211,238,0.055),transparent 72%),
    radial-gradient(ellipse 500px 320px at 75% 65%,rgba(34,211,238,0.035),transparent 68%);
  background-repeat:no-repeat,no-repeat;
  animation:cloud-drift 55s ease-in-out infinite alternate;
}
body.light::after{
  background-image:
    radial-gradient(ellipse 700px 420px at 20% 40%,rgba(8,145,178,0.06),transparent 72%),
    radial-gradient(ellipse 500px 320px at 75% 65%,rgba(8,145,178,0.04),transparent 68%);
}
@keyframes cloud-drift{
  0%  {background-position:-10% 30%,-10% 30%}
  50% {background-position:55% 48%,55% 48%}
  100%{background-position:108% 18%,108% 18%}
}
body.bg-anim-off::before,body.bg-anim-off::after{display:none}
button:focus-visible,.nav-btn:focus-visible,.login-btn:focus-visible,.portal-logout:focus-visible,.theme-btn:focus-visible,.logout-btn:focus-visible,a:focus-visible{
  outline:2px solid var(--accent);outline-offset:2px}
button:focus:not(:focus-visible){outline:none}
::-webkit-scrollbar{width:6px}::-webkit-scrollbar-track{background:var(--bg)}::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
#saisies-scroll-top{overflow-x:auto}
#saisies-scroll-top::-webkit-scrollbar{height:6px}
#saisies-scroll-top::-webkit-scrollbar-thumb{background:var(--accent);border-radius:3px}
.saisies-table-wrap{border-radius:10px;border:1px solid var(--border);overflow:hidden}
.saisies-table-wrap .saisies-bot{max-height:68vh;overflow:auto}
.saisies-table-wrap table thead th{position:sticky;top:0;z-index:5;background:var(--card)}
.login-page{position:relative;z-index:1;min-height:100vh;display:flex;align-items:center;justify-content:center}
.login-theme-btn{position:fixed;top:18px;right:18px;z-index:10;
  display:inline-flex;align-items:center;gap:8px;
  padding:9px 14px;border-radius:10px;border:1px solid var(--border);
  background:var(--card);color:var(--text2);cursor:pointer;
  font-size:12px;font-family:inherit;font-weight:600;
  transition:background .15s,color .15s,border-color .15s,box-shadow .2s}
.login-theme-btn:hover{color:var(--accent);border-color:var(--accent);
  box-shadow:0 0 0 1px rgba(34,211,238,.22),0 0 18px rgba(34,211,238,.14)}
body.light .login-theme-btn:hover{box-shadow:0 0 0 1px rgba(8,145,178,.28),0 0 18px rgba(8,145,178,.12)}
.login-theme-btn .theme-ico{display:inline-flex;align-items:center;line-height:1}
@media (max-width:480px){.login-theme-btn .theme-label{display:none}}
.pwd-wrap{position:relative}
.pwd-wrap input{padding-right:44px}
.pwd-toggle{position:absolute;top:50%;right:8px;transform:translateY(-50%);
  display:inline-flex;align-items:center;justify-content:center;
  width:32px;height:32px;border:none;background:transparent;cursor:pointer;
  color:var(--muted);border-radius:8px;padding:0;font-family:inherit;
  transition:color .15s,background .15s}
.pwd-toggle:hover{color:var(--accent);background:var(--accent-bg)}
.pwd-toggle:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.login-box{width:100%;max-width:420px;padding:24px}
.login-logo{text-align:center;margin-bottom:40px}
.brand{font-size:32px;font-weight:800;letter-spacing:-1px}.brand span{color:var(--accent)}
.tagline{font-size:13px;color:var(--muted);margin-top:6px}
.login-card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:32px}
.login-card h2{font-size:18px;font-weight:700;margin-bottom:6px}
.login-card p{font-size:13px;color:var(--muted);margin-bottom:28px}
.field{margin-bottom:16px}
.field label{display:block;font-size:12px;font-weight:600;color:var(--text2);margin-bottom:6px;text-transform:uppercase;letter-spacing:.5px}
.field input{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:12px 16px;color:var(--text);font-size:14px;font-family:inherit;outline:none;transition:border-color .15s}
.field input:focus{border-color:var(--accent)}
.login-btn{width:100%;background:var(--accent);color:var(--bg);border:none;border-radius:10px;padding:14px;font-size:15px;font-weight:700;cursor:pointer;font-family:inherit;margin-top:8px;transition:opacity .15s}
.login-btn:disabled{opacity:.65;cursor:not-allowed}
.login-error{background:rgba(248,113,113,.12);border:1px solid rgba(248,113,113,.3);border-radius:8px;padding:10px 14px;font-size:13px;color:var(--danger);margin-bottom:16px;display:none}
.login-error.show{display:block}
.login-footer{text-align:center;margin-top:20px;font-size:11px;color:var(--muted)}
/* Bandeau staging v1 — fine bande rouge permanente, n'apparaît que si ENV_NAME=v1.
   Sert aussi de hôte au sélecteur d'impersonation (superadmin only, v1 & prod). */
.staging-bandeau{position:fixed;top:0;left:0;right:0;height:24px;background:#dc2626;color:#fff;
  font-size:11px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;
  display:flex;align-items:center;justify-content:center;gap:10px;
  z-index:9999;font-family:'Segoe UI',system-ui,sans-serif;
  box-shadow:0 1px 6px rgba(220,38,38,.4);padding:0 12px}
.staging-bandeau::before{content:"●";color:#fef2f2;font-size:9px;line-height:1}
.staging-bandeau[hidden]{display:none}
/* Version prod : bandeau indigo (moins alarmant) — affiché uniquement pour superadmin */
.staging-bandeau.env-prod{background:#4f46e5;box-shadow:0 1px 6px rgba(79,70,229,.4)}
/* État impersonation active : ambre pour bien signaler qu'on joue un rôle */
.staging-bandeau.impersonating{background:#d97706;box-shadow:0 1px 6px rgba(217,119,6,.4)}
.staging-bandeau .msf-imp-msg{flex:0 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.staging-bandeau .msf-imp-slot{margin-left:auto;display:flex;align-items:center;gap:6px;text-transform:none;letter-spacing:0;font-weight:600}
.staging-bandeau .msf-imp-slot select{background:rgba(255,255,255,.15);color:#fff;border:1px solid rgba(255,255,255,.35);
  border-radius:6px;padding:2px 6px;font-size:11px;font-family:inherit;font-weight:600;line-height:16px;height:20px;cursor:pointer}
.staging-bandeau .msf-imp-slot select option{color:#111827;background:#fff}
.staging-bandeau .msf-imp-slot button{background:rgba(255,255,255,.2);color:#fff;border:1px solid rgba(255,255,255,.45);
  border-radius:6px;padding:2px 10px;font-size:11px;font-family:inherit;font-weight:700;line-height:16px;height:20px;cursor:pointer;text-transform:uppercase;letter-spacing:.5px}
.staging-bandeau .msf-imp-slot button:hover{background:rgba(255,255,255,.32)}
.staging-bandeau .msf-imp-slot .msf-imp-stop{background:#fff;color:#b45309}
.staging-bandeau .msf-imp-slot .msf-imp-stop:hover{background:#fef3c7}
@media (max-width:640px){
  .staging-bandeau{font-size:10px;gap:6px;padding:0 6px}
  .staging-bandeau .msf-imp-slot select{max-width:110px}
}
body.has-staging-bandeau{padding-top:24px}
body.has-staging-bandeau .sidebar{height:calc(100vh - 24px);top:24px}
body.has-staging-bandeau .mobile-topbar{top:24px}
.app{position:relative;z-index:1;display:flex;min-height:100vh}
.sidebar{width:220px;background:var(--card);border-right:1px solid var(--border);padding:20px 12px;display:flex;flex-direction:column;flex-shrink:0;height:100vh;position:sticky;top:0;overflow-y:auto}
.sidebar::-webkit-scrollbar{width:0}
.sidebar{scrollbar-width:none}
.sidebar-overlay{display:none}
.back-mysifa{
  border:none!important;
  background:transparent!important;
  font-weight:400!important;
  color:var(--text2)!important;
  padding:8px 10px!important;
}
.back-mysifa:hover{color:var(--text)!important;background:transparent!important}
.back-mysifa .wm{font-weight:800;color:var(--text)}
.back-mysifa .wm span{color:var(--accent)}
@media (max-width: 900px){
  .sidebar{position:fixed;left:0;top:0;bottom:0;z-index:9000;transform:translateX(-105%);transition:transform .18s ease;box-shadow:0 16px 48px rgba(0,0,0,.55)}
  body.sb-open .sidebar{transform:translateX(0)}
  .main{padding:18px}
  .sidebar-overlay{display:block;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:8999}
  body:not(.sb-open) .sidebar-overlay{display:none}
}
.logo{padding:0 8px;margin-bottom:32px}
.logo-brand{font-size:15px;font-weight:800}.logo-brand span{color:var(--accent)}
.logo-sub{font-size:10px;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase}
.logo-row{display:flex;align-items:center;justify-content:space-between;gap:10px}
.theme-btn--logo{width:auto;padding:8px 10px}
.theme-btn--logo .theme-ico{display:inline-flex;align-items:center}
.nav-btn{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:8px;border:none;background:transparent;color:var(--text2);cursor:pointer;font-size:13px;font-weight:500;width:100%;text-align:left;font-family:inherit;transition:background .15s,color .15s,box-shadow .2s;margin-bottom:2px}
.nav-btn:hover,.nav-btn.active{background:var(--accent-bg);color:var(--accent)}
.nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(34,211,238,.25),0 0 18px rgba(34,211,238,.15)}
body.palette-ambre .nav-btn:hover:not(.active),body.palette-forge .nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(240,165,0,.28),0 0 16px rgba(240,165,0,.14)}
body.palette-pivoine .nav-btn:hover:not(.active),body.palette-cocon .nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(240,56,136,.28),0 0 16px rgba(240,56,136,.14)}
body.palette-foret .nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(61,214,126,.28),0 0 16px rgba(61,214,126,.14)}
body.palette-cendre .nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(100,150,200,.28),0 0 16px rgba(100,150,200,.14)}
body.palette-braise .nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(240,112,48,.28),0 0 16px rgba(240,112,48,.14)}
body.light .nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(8,145,178,.32),0 0 16px rgba(8,145,178,.12)}
.nav-scroll{flex:1;min-height:0;overflow-y:auto;display:flex;flex-direction:column;gap:2px;margin-bottom:8px;width:100%}
.nav-group-label{font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;
  padding:4px 12px 2px;user-select:none;pointer-events:none;line-height:1.3}
.nav-group-label:not(:first-child){margin-top:10px;padding-top:12px;border-top:1px solid var(--border)}
.sidebar .nav-scroll.tabs{margin:0;flex-wrap:nowrap}
.nav-badge{margin-left:auto;min-width:22px;height:18px;padding:0 6px;border-radius:999px;
  background:rgba(248,113,113,.14);border:1px solid rgba(248,113,113,.35);color:var(--danger);
  display:inline-flex;align-items:center;justify-content:center;font-size:10px;font-weight:800;font-family:monospace}
.nav-badge.hidden{display:none}
.msg-grid{display:flex;gap:16px;align-items:flex-start}
.msg-left{flex:0 0 340px;min-width:240px;max-width:340px}
.msg-right{flex:1;min-width:0}
.msg-list-scroll{display:flex;flex-direction:column;gap:4px;max-height:calc(100vh - 310px);min-height:120px;overflow-y:auto;padding:10px 12px}
@media (max-width:900px){
  .msg-grid{flex-direction:column;gap:0}
  .msg-left{flex:none;width:100%;max-width:100%;min-width:0}
  .msg-right{flex:none;width:100%;min-width:0}
  .msg-list-scroll{max-height:50vh}
  .msg-filter-wrap{flex-direction:column;gap:8px!important;align-items:stretch!important}
  .msg-filter-actions{margin-left:0!important;justify-content:flex-end}
}
.sidebar-bottom{margin-top:auto;display:flex;flex-direction:column;gap:6px;padding-bottom:8px}
.user-chip{padding:10px 12px;border-radius:8px;background:var(--accent-bg)}
.user-chip .uc-name{font-size:12px;font-weight:600;color:var(--text)}
.user-chip .uc-role{font-size:10px;color:var(--accent);text-transform:uppercase;letter-spacing:.5px}
.theme-btn,.logout-btn{display:flex;align-items:center;gap:8px;padding:10px 12px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-size:12px;width:100%;font-family:inherit;transition:background .15s,color .15s,border-color .15s,box-shadow .2s}
.theme-btn:hover{background:var(--accent-bg);color:var(--accent);border-color:var(--accent);box-shadow:0 0 0 1px rgba(34,211,238,.22),0 0 20px rgba(34,211,238,.14)}
body.palette-ambre .theme-btn:hover,body.palette-forge .theme-btn:hover{box-shadow:0 0 0 1px rgba(240,165,0,.28),0 0 18px rgba(240,165,0,.14)}
body.palette-pivoine .theme-btn:hover,body.palette-cocon .theme-btn:hover{box-shadow:0 0 0 1px rgba(240,56,136,.24),0 0 18px rgba(240,56,136,.12)}
body.palette-foret .theme-btn:hover{box-shadow:0 0 0 1px rgba(61,214,126,.24),0 0 18px rgba(61,214,126,.12)}
body.palette-cendre .theme-btn:hover{box-shadow:0 0 0 1px rgba(100,150,200,.24),0 0 18px rgba(100,150,200,.12)}
body.palette-braise .theme-btn:hover{box-shadow:0 0 0 1px rgba(240,112,48,.24),0 0 18px rgba(240,112,48,.12)}
body.light .theme-btn:hover{box-shadow:0 0 0 1px rgba(8,145,178,.28),0 0 18px rgba(8,145,178,.12)}
.theme-btn .theme-ico{font-size:14px;line-height:1}
.theme-btn .theme-label{white-space:nowrap}
@media (display-mode: standalone), (max-width: 900px){
  .theme-btn .theme-label{display:none}
  .theme-btn{justify-content:center}
}
.logout-btn{border:none}.logout-btn:hover{color:var(--danger);background:rgba(248,113,113,.1);box-shadow:0 0 0 1px rgba(248,113,113,.35),0 0 18px rgba(248,113,113,.12)}
.version{font-size:10px;color:var(--muted);font-family:monospace;padding:4px 12px}
.upd-overlay{position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:9000;display:flex;align-items:center;justify-content:center;padding:16px}
.upd-card{background:var(--card);border:1px solid var(--border);border-radius:18px;padding:28px 28px 22px;width:min(540px,100%);max-height:88vh;overflow-y:auto;box-shadow:0 24px 64px rgba(0,0,0,.55)}
.upd-card h2{font-size:16px;font-weight:700;margin:0 0 16px;color:var(--text)}
.upd-card .upd-body{font-size:13px;line-height:1.8;color:var(--text2)}
.upd-card .upd-body ul{padding-left:18px;margin:8px 0}
.upd-card .upd-body li{margin-bottom:6px}
.upd-card .upd-body strong{color:var(--text)}
.upd-ok-btn{display:block;width:100%;margin-top:20px;padding:13px;border-radius:12px;border:none;background:var(--accent);color:#0a0e17;font-size:14px;font-weight:800;cursor:pointer;font-family:inherit;transition:filter .15s}
.upd-ok-btn:hover{filter:brightness(1.08)}
.main{flex:1;padding:28px;overflow-y:auto}.container{max-width:1200px;margin:0 auto}
h1{font-size:22px;font-weight:700;margin-bottom:4px}
.subtitle{font-size:13px;color:var(--muted);margin-bottom:24px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:14px;margin-bottom:24px}
.stat{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px 20px}
.stat-label{font-size:12px;color:var(--text2);font-weight:800;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px}
.stat-value{font-size:26px;font-weight:700;font-family:monospace;line-height:1.1;color:var(--text2)}
.stat-sub{font-size:11px;color:var(--muted);margin-top:4px}
.sanity-banner{display:flex;align-items:center;gap:24px;background:var(--card);border:1px solid var(--border);border-radius:16px;padding:20px 28px;margin-bottom:24px}
.sanity-circle{position:relative;width:80px;height:80px;flex-shrink:0}
.sanity-num{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:800;font-family:monospace}
.si-mention{font-size:18px;font-weight:700;margin-bottom:4px}
.si-label{font-size:12px;color:var(--muted);margin-bottom:10px}
.sanity-pills{display:flex;gap:8px;flex-wrap:wrap}
.sanity-pill{font-size:11px;padding:3px 10px;border-radius:20px;font-weight:600;background:rgba(248,113,113,.12);color:var(--danger)}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden;margin-bottom:16px}
.card-header{padding:14px 20px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
.card-header h3{font-size:14px;font-weight:600;margin:0;line-height:1.2}
.card-empty{padding:24px;text-align:center;color:var(--muted);font-size:13px}
.card-blocked{padding:32px 24px;text-align:center}
.cw-row-bad td{background:rgba(248,113,113,.08)!important}
.cw-row-bad td:first-child{box-shadow:inset 3px 0 0 rgba(248,113,113,.7)}
.cw-row-warn td{background:rgba(251,191,36,.10)!important}
.cw-row-warn td:first-child{box-shadow:inset 3px 0 0 rgba(251,191,36,.7)}
.cw-table{display:block}
.cw-table .tbl-scroll{overflow:auto}
.cw-table .tbl-scroll.top{max-height:14px}
.cw-table .tbl-scroll.top::-webkit-scrollbar{height:10px}
.cw-table .tbl-scroll.bot{max-height:520px}
.cb-icon{font-size:32px;margin-bottom:12px}.cb-msg{font-size:14px;color:var(--muted)}
.filters-panel{margin-bottom:20px}
.filters{display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end}
.filter-group{display:flex;flex-direction:column;gap:6px}
.filter-group--dossier{flex:1;min-width:200px;max-width:300px}
.filter-group label{font-size:10px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
.filter-input{
  background:var(--filter-input-bg);border:1.5px solid var(--border);border-radius:10px;
  padding:10px 14px;color:var(--text);font-size:13px;font-family:inherit;outline:none;
  min-height:40px;box-sizing:border-box;transition:border-color .15s,box-shadow .15s;
}
.filter-input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12)}
body.light .filter-input:focus{box-shadow:0 0 0 3px rgba(8,145,178,.12)}
.filters .filter-input[type=date]{min-width:148px;padding:9px 12px;font-size:12px}
.filters .multisel-trigger{
  min-width:168px;cursor:pointer;display:flex;align-items:center;
  justify-content:space-between;gap:8px;text-align:left;
}
.filters .multisel-trigger-caret{opacity:.55;font-size:10px}
.prod-dossier-filter{position:relative;width:100%}
.filters .prod-dossier-filter .search-bar{
  width:100%;margin-bottom:0;min-height:40px;padding:10px 14px;font-size:13px;
  border-radius:10px;background:var(--filter-input-bg);border:1.5px solid var(--border);
}
.prod-dossier-filter .search-bar:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12)}
body.light .prod-dossier-filter .search-bar:focus{box-shadow:0 0 0 3px rgba(8,145,178,.12)}
.prod-dossier-suggest{position:absolute;top:calc(100% + 4px);left:0;right:0;z-index:80;
  background:var(--card);border:1px solid var(--border);border-radius:10px;max-height:240px;overflow-y:auto;
  box-shadow:0 10px 28px rgba(0,0,0,.35);display:none}
.prod-dossier-suggest.open{display:block}
.prod-dossier-suggest-item{padding:10px 14px;font-size:12px;cursor:pointer;font-family:monospace;
  color:var(--text);border-bottom:1px solid var(--border)}
.prod-dossier-suggest-item:last-child{border-bottom:none}
.prod-dossier-suggest-item:hover,.prod-dossier-suggest-item--hi{background:var(--accent-bg);color:var(--accent)}
.prod-dossier-suggest-empty{padding:12px 14px;font-size:12px;color:var(--muted);line-height:1.45}
.filters-chips-row{margin-top:10px;padding-top:2px}
.prod-dossier-chips{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.prod-dossier-chip{display:inline-flex;align-items:center;gap:4px;padding:3px 8px 3px 10px;border-radius:16px;
  font-size:11px;font-weight:600;font-family:monospace;background:var(--accent-bg);
  border:1px solid rgba(34,211,238,.22);color:var(--text)}
.prod-dossier-chip-remove{
  border:none;background:transparent;color:var(--muted);cursor:pointer;
  font-size:11px;line-height:1;padding:0;width:16px;height:16px;
  display:inline-flex;align-items:center;justify-content:center;border-radius:4px;font-family:inherit;
}
.prod-dossier-chip-remove:hover{color:var(--danger);background:rgba(248,113,113,.12)}
.filters-apply-btn{
  background:var(--accent);color:var(--bg);border:none;border-radius:10px;
  padding:10px 18px;font-size:13px;font-weight:600;min-height:40px;
  cursor:pointer;font-family:inherit;align-self:flex-end;
  transition:filter .15s,box-shadow .15s,transform .05s;
}
.filters-apply-btn:hover{filter:brightness(1.05);box-shadow:0 0 0 4px rgba(34,211,238,.18)}
.filters-apply-btn:active{transform:translateY(1px)}

/* MyProd — mobile : pas de libellés, hauteur des champs = bouton Filtrer */
@media (max-width:900px){
  body.mysifa-app-prod.mysifa-prod-filters-page .filters-panel .filter-group > label{
    display:none;
  }
  body.mysifa-app-prod.mysifa-prod-filters-page .filters-panel .filter-group{
    gap:0;
  }
  body.mysifa-app-prod.mysifa-prod-filters-page .filters{
    align-items:center;
  }
  body.mysifa-app-prod.mysifa-prod-filters-page .filters-apply-btn{
    height:40px;min-height:40px;max-height:40px;
    padding:0 18px;box-sizing:border-box;
    display:inline-flex;align-items:center;justify-content:center;
    align-self:center;
  }
  body.mysifa-app-prod.mysifa-prod-filters-page .filters .filter-input[type=date],
  body.mysifa-app-prod.mysifa-prod-filters-page .filters .multisel-trigger,
  body.mysifa-app-prod.mysifa-prod-filters-page .filters .prod-dossier-filter .search-bar{
    height:40px;min-height:40px;max-height:40px;
    padding:0 12px;font-size:12px;box-sizing:border-box;line-height:1.2;
  }
  body.mysifa-app-prod.mysifa-prod-filters-page .filters .multisel-trigger{
    display:inline-flex;align-items:center;justify-content:space-between;
  }
  body.mysifa-app-prod.mysifa-prod-filters-page .main .container > h1,
  body.mysifa-app-prod.mysifa-prod-filters-page .main .container > .subtitle{
    display:none!important;
  }
  body.mysifa-app-prod.mysifa-prod-filters-page .filters-panel{
    margin-top:0;
    margin-bottom:14px;
  }
}

/* MyProd — mobile paysage : filtres sur une ligne, barre fixe, sans titre dupliqué */
@media (max-width:900px) and (orientation:landscape){
  body.mysifa-app-prod.mysifa-prod-filters-page .main .container > h1,
  body.mysifa-app-prod.mysifa-prod-filters-page .main .container > .subtitle{
    display:none!important;
  }
  body.mysifa-app-prod.mysifa-prod-filters-page.has-topbar .main{
    padding-top:74px;
    overflow:hidden;
    display:flex;
    flex-direction:column;
  }
  body.mysifa-app-prod.mysifa-prod-filters-page .main .container{
    display:flex;
    flex-direction:column;
    flex:1;
    min-height:0;
    max-width:none;
    padding:0 10px 10px;
    overflow:hidden;
  }
  body.mysifa-app-prod.mysifa-prod-filters-page .mobile-topbar{
    padding:8px 12px;
  }
  body.mysifa-app-prod.mysifa-prod-filters-page .filters-panel{
    position:sticky;
    top:0;
    z-index:85;
    flex-shrink:0;
    margin:0 -10px 8px;
    padding:6px 10px;
    background:var(--bg);
    border-bottom:1px solid var(--border);
    box-shadow:0 4px 12px rgba(0,0,0,.12);
  }
  body.mysifa-app-prod.mysifa-prod-filters-page .filters-chips-row{
    display:none;
  }
  body.mysifa-app-prod.mysifa-prod-filters-page .filters{
    flex-wrap:nowrap;
    align-items:center;
    gap:6px;
    overflow-x:auto;
    overflow-y:hidden;
    -webkit-overflow-scrolling:touch;
    scrollbar-width:thin;
    padding-bottom:2px;
  }
  body.mysifa-app-prod.mysifa-prod-filters-page .filter-group{
    flex:0 0 auto;
    flex-direction:column;
    gap:2px;
    min-width:0;
  }
  body.mysifa-app-prod.mysifa-prod-filters-page .filter-group > label{
    display:none;
  }
  body.mysifa-app-prod.mysifa-prod-filters-page .filter-group{
    gap:0;
  }
  body.mysifa-app-prod.mysifa-prod-filters-page .filter-group--dossier{
    min-width:88px;
    max-width:120px;
    flex:0 0 100px;
  }
  body.mysifa-app-prod.mysifa-prod-filters-page .filters .prod-dossier-filter .search-bar{
    height:32px;min-height:32px;max-height:32px;
    padding:0 8px;font-size:11px;
  }
  body.mysifa-app-prod.mysifa-prod-filters-page .filters .filter-input[type=date]{
    min-width:102px;
    width:102px;
    height:32px;min-height:32px;max-height:32px;
    padding:0 8px;font-size:11px;
  }
  body.mysifa-app-prod.mysifa-prod-filters-page .filters .multisel-trigger{
    min-width:72px;
    max-width:96px;
    height:32px;min-height:32px;max-height:32px;
    padding:0 8px;font-size:11px;
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
  }
  body.mysifa-app-prod.mysifa-prod-filters-page .filters-apply-btn{
    height:32px;min-height:32px;max-height:32px;
    padding:0 11px;font-size:11px;
    flex-shrink:0;
    align-self:center;
  }
  body.mysifa-app-prod.mysifa-prod-filters-page .prod-main-scroll{
    flex:1;
    min-height:0;
    overflow-y:auto;
    -webkit-overflow-scrolling:touch;
  }
}

.drop-zone{border:2px dashed var(--border);border-radius:16px;padding:48px 24px;text-align:center;cursor:pointer;background:var(--card);transition:all .2s;margin-bottom:20px}
.drop-zone:hover,.drop-zone.drag{border-color:var(--accent);background:var(--accent-bg)}
.dz-icon{font-size:36px;opacity:.4;margin-bottom:12px}
.dz-title{font-size:16px;font-weight:600;margin-bottom:6px}
.dz-sub{font-size:13px;color:var(--muted)}
table{width:100%;border-collapse:collapse;font-size:12px}
th{padding:8px 12px;text-align:left;font-weight:600;font-size:10px;color:var(--accent);border-bottom:1px solid var(--border);text-transform:uppercase;letter-spacing:.5px;white-space:nowrap;font-family:monospace}
td{padding:7px 12px;color:var(--text2);white-space:nowrap;max-width:200px;overflow:hidden;text-overflow:ellipsis;border-bottom:1px solid var(--border);position:relative}
td.editable{cursor:pointer;transition:background .12s}
td.editable:hover{background:rgba(34,211,238,0.07);color:var(--text)}
td.editable:hover::after{content:'✏';position:absolute;right:5px;top:50%;transform:translateY(-50%);font-size:9px;opacity:.35;pointer-events:none}
td.editing{padding:0!important;background:rgba(34,211,238,0.1)!important;outline:2px solid var(--accent)}
td.editing input,td.editing select{width:100%;height:100%;background:var(--card);border:none;color:var(--text);font-size:12px;font-family:inherit;padding:7px 10px;outline:none}
tr.data-row{position:relative}
.add-row-btn{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:22px;height:22px;background:var(--accent);color:#000;border:2px solid var(--bg);border-radius:50%;cursor:pointer;font-size:14px;font-weight:900;opacity:0;transition:opacity .15s;z-index:30;box-shadow:0 2px 8px rgba(0,0,0,.5);display:flex;align-items:center;justify-content:center;pointer-events:none}
tr.data-row:hover .add-row-btn{opacity:1;pointer-events:auto}
tr.data-row:hover td{background:rgba(34,211,238,0.025)}
.btn-fictif-sm{display:inline-flex;align-items:center;gap:6px;padding:8px 14px;border-radius:10px;border:1px solid rgba(167,139,250,.45);
  background:rgba(167,139,250,.12);color:#a78bfa;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;transition:all .15s}
.btn-fictif-sm:hover{background:rgba(167,139,250,.22);border-color:#a78bfa}
body.light .btn-fictif-sm{color:#7c3aed;border-color:rgba(124,58,237,.35);background:rgba(124,58,237,.08)}
body.light .btn-fictif-sm:hover{background:rgba(124,58,237,.14)}
.fictif-reassign-suggest{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.fictif-reassign-suggest button{font-size:12px;padding:6px 10px;border-radius:8px;border:1px solid var(--border2);
  background:var(--bg);color:var(--text2);cursor:pointer;font-family:inherit}
.fictif-reassign-suggest button:hover{border-color:var(--accent);color:var(--accent)}
tr.data-row.saisie-row-fictif td{color:#a78bfa !important;font-weight:800 !important}
tr.data-row.saisie-row-fictif td span{color:#a78bfa !important;font-weight:800 !important}
tr.data-row.saisie-row-fictif:hover td{background:rgba(167,139,250,.08) !important}
body.light tr.data-row.saisie-row-fictif td,
body.light tr.data-row.saisie-row-fictif td span{color:#7c3aed !important}

/* Formulaire ajout ligne — modal style */
.add-row-modal{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:100;display:flex;align-items:center;justify-content:center}
.add-row-form{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:28px;width:100%;max-width:540px;box-shadow:0 24px 64px rgba(0,0,0,.4);position:relative}
.add-row-form h3{font-size:16px;font-weight:700;margin-bottom:20px;padding-right:34px}
.add-row-close{position:absolute;top:14px;right:14px;width:32px;height:32px;border-radius:10px;
  border:1px solid var(--border);background:var(--bg);color:var(--muted);cursor:pointer;
  display:flex;align-items:center;justify-content:center;font-size:18px;line-height:1}
.add-row-close:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.add-row-header{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:20px;padding-right:34px;cursor:grab;user-select:none}
.add-row-header:active{cursor:grabbing}
.add-row-header h3{margin:0;padding:0}
.add-row-counter{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:800;color:var(--muted);font-family:monospace;white-space:nowrap}
.add-row-nav-btn{width:22px;height:22px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--muted);
  display:inline-flex;align-items:center;justify-content:center;cursor:pointer;line-height:1;font-size:14px;padding:0}
.add-row-nav-btn:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.add-row-nav-btn:active{transform:translateY(1px)}
.prod-synth-key{cursor:pointer;font-weight:700;color:var(--text);text-decoration:underline;text-decoration-color:transparent;transition:text-decoration-color .15s,color .15s}
.prod-synth-key:hover{color:var(--text);text-decoration-color:var(--text2)}
.prod-synth-kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:10px;margin:16px 0}
.prod-synth-kpi{background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px 12px}
.prod-synth-kpi .lbl{font-size:10px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.4px;margin-bottom:4px}
.prod-synth-kpi .val{font-size:15px;font-weight:800;color:var(--text);font-family:monospace}
.prod-synth-sub{font-size:12px;color:var(--muted);margin:-8px 0 12px}
/* ── Modal détail synthèse production (lecture direction) ───────── */
.prod-synth-modal .add-row-form.prod-synth-detail-form{
  max-width:min(920px,96vw);
  max-height:min(92vh,900px);
  overflow:auto;
  padding:26px 28px 24px;
  border-top:3px solid var(--accent);
  box-shadow:0 24px 80px rgba(0,0,0,.45);
}
.prod-synth-detail-head{
  display:flex;
  flex-wrap:wrap;
  align-items:flex-start;
  justify-content:space-between;
  gap:16px;
  margin-bottom:4px;
  padding-right:40px;
}
.prod-synth-detail-title-main{min-width:0;flex:1}
.prod-synth-detail-eyebrow{
  display:block;
  font-size:11px;
  font-weight:700;
  text-transform:uppercase;
  letter-spacing:.55px;
  color:var(--muted);
  margin-bottom:6px;
}
.prod-synth-detail-h3{
  margin:0;
  font-size:22px;
  font-weight:800;
  color:var(--text);
  line-height:1.2;
  letter-spacing:-.02em;
  word-break:break-word;
}
.add-row-form.prod-synth-detail-form h3.prod-synth-detail-h3{
  margin:0;
  padding-right:0;
  font-size:22px;
  font-weight:800;
  line-height:1.2;
}
.prod-synth-modal .add-row-counter{
  flex-shrink:0;
  padding:6px 8px;
  border-radius:10px;
  border:1px solid var(--border);
  background:var(--bg);
  font-size:13px;
}
.prod-synth-modal .add-row-nav-btn{
  width:28px;
  height:28px;
  border-radius:10px;
  font-size:16px;
  font-weight:800;
}
.prod-synth-modal .prod-synth-sub{
  margin:10px 0 0;
  font-size:13px;
  line-height:1.5;
  color:var(--muted);
}
.prod-synth-modal .prod-synth-kpis{
  grid-template-columns:repeat(auto-fit,minmax(132px,1fr));
  gap:12px;
  margin:18px 0 6px;
}
.prod-synth-modal .prod-synth-kpi{
  padding:14px 14px;
  border-radius:12px;
  background:var(--bg);
  border:1px solid var(--border);
}
.prod-synth-modal .prod-synth-kpi .lbl{font-size:11px;margin-bottom:6px}
.prod-synth-modal .prod-synth-kpi .val{font-size:18px;font-weight:800}
.prod-synth-detail-section-h{
  font-size:11px;
  font-weight:700;
  text-transform:uppercase;
  letter-spacing:.5px;
  color:var(--text2);
  margin:22px 0 10px;
  padding-bottom:6px;
  border-bottom:1px solid var(--border);
}
.prod-synth-detail-table-wrap{
  border:1px solid var(--border);
  border-radius:12px;
  overflow:auto;
  max-height:min(440px,52vh);
  background:var(--bg);
}
.prod-synth-modal table.prod-synth-detail-table{
  font-size:14px;
  width:100%;
}
.prod-synth-modal table.prod-synth-detail-table thead th{
  position:sticky;
  top:0;
  z-index:2;
  background:var(--card);
  box-shadow:0 1px 0 var(--border);
  padding:12px 14px;
  font-size:11px;
  font-weight:700;
  color:var(--muted);
  text-transform:uppercase;
  letter-spacing:.45px;
  border-bottom:1px solid var(--border);
}
.prod-synth-modal table.prod-synth-detail-table tbody td{
  padding:12px 14px;
  color:var(--text);
  border-bottom:1px solid var(--border);
  vertical-align:middle;
}
.prod-synth-modal table.prod-synth-detail-table tbody tr:last-child td{border-bottom:none}
.prod-synth-modal table.prod-synth-detail-table tbody tr:nth-child(even) td{
  background:rgba(148,163,184,.05);
}
body.light .prod-synth-modal table.prod-synth-detail-table tbody tr:nth-child(even) td{
  background:rgba(100,116,139,.06);
}
.prod-synth-modal table.prod-synth-detail-table tbody tr:hover td{background:var(--accent-bg)}
.prod-synth-detail-td-num{
  text-align:right;
  font-family:ui-monospace,Consolas,monospace;
  font-variant-numeric:tabular-nums;
  font-weight:700;
  white-space:nowrap;
}
.prod-synth-detail-td-mono{
  font-family:ui-monospace,Consolas,monospace;
  font-weight:700;
  white-space:nowrap;
}
.prod-synth-detail-td-text{white-space:nowrap}
.prod-synth-detail-td-wrap{
  white-space:normal;
  max-width:260px;
  min-width:120px;
  color:var(--text2);
  line-height:1.45;
  font-size:13px;
}
.prod-synth-detail-td-vit{
  text-align:right;
  font-family:ui-monospace,Consolas,monospace;
  font-variant-numeric:tabular-nums;
  font-weight:800;
  color:var(--warn);
  white-space:nowrap;
}
.prod-synth-detail-empty{
  text-align:center;
  padding:26px 18px !important;
  color:var(--muted);
  font-size:14px;
  font-weight:600;
  line-height:1.5;
  white-space:normal;
}
.prod-synth-detail-footer{
  margin-top:18px;
  padding:12px 14px;
  border-radius:10px;
  border:1px solid var(--border);
  background:var(--bg);
  font-size:12px;
  font-weight:600;
  color:var(--text2);
  line-height:1.5;
}
.prod-synth-modal .add-row-close{
  top:16px;
  right:16px;
  width:36px;
  height:36px;
  border-radius:10px;
  font-size:20px;
}
.prod-synth-detail-sessions{display:block}
.prod-synth-sessions-toggle{display:none}

/* MyProd — modal détail synthèse : mobile = KPIs seuls, sessions optionnelles */
@media (max-width:900px){
  .prod-synth-modal.prod-synth-modal--compact{
    align-items:center;
    justify-content:center;
    padding:8px;
  }
  .prod-synth-modal--compact .add-row-form.prod-synth-detail-form{
    max-width:100%;
    width:100%;
    max-height:calc(100dvh - 16px);
    padding:12px 14px 14px;
    overflow:hidden;
    display:flex;
    flex-direction:column;
    border-radius:12px;
  }
  .prod-synth-modal--compact .prod-synth-detail-head{
    padding-right:34px;
    margin-bottom:0;
    gap:8px;
  }
  .prod-synth-modal--compact .prod-synth-detail-h3,
  .prod-synth-modal--compact .add-row-form.prod-synth-detail-form h3.prod-synth-detail-h3{
    font-size:16px;
  }
  .prod-synth-modal--compact .prod-synth-detail-eyebrow{font-size:10px;margin-bottom:4px}
  .prod-synth-modal--compact .prod-synth-sub{
    margin:4px 0 6px;
    font-size:11px;
    line-height:1.35;
  }
  .prod-synth-modal--compact .add-row-counter{padding:4px 6px;font-size:12px}
  .prod-synth-modal--compact .add-row-nav-btn{width:26px;height:26px;font-size:14px}
  .prod-synth-modal--compact .prod-synth-kpis{
    grid-template-columns:repeat(4,minmax(0,1fr));
    gap:6px;
    margin:0;
    flex:1;
    align-content:start;
  }
  .prod-synth-modal--compact .prod-synth-kpi{
    padding:8px 6px;
    border-radius:10px;
    min-width:0;
  }
  .prod-synth-modal--compact .prod-synth-kpi .lbl{
    font-size:9px;
    margin-bottom:3px;
    letter-spacing:.3px;
  }
  .prod-synth-modal--compact .prod-synth-kpi .val{
    font-size:13px;
    line-height:1.2;
    word-break:break-word;
  }
  .prod-synth-modal--compact .prod-synth-sessions-toggle{
    display:block;
    width:100%;
    margin-top:8px;
    flex-shrink:0;
    text-align:center;
    border-radius:10px;
    padding:8px 10px;
    font-size:11px;
  }
  .prod-synth-modal--compact .prod-synth-detail-footer{display:none}
  .prod-synth-modal--compact .prod-synth-detail-sessions{
    display:none;
    flex:1;
    min-height:0;
    margin-top:8px;
    flex-direction:column;
    overflow:hidden;
  }
  .prod-synth-modal--compact.prod-synth-modal--sessions-open .prod-synth-detail-sessions{
    display:flex;
  }
  .prod-synth-modal--compact.prod-synth-modal--sessions-open .prod-synth-kpis{
    flex:0 0 auto;
    grid-template-columns:repeat(4,minmax(0,1fr));
  }
  .prod-synth-modal--compact.prod-synth-modal--sessions-open .prod-synth-sessions-toggle{
    margin-top:6px;
  }
  .prod-synth-modal--compact .prod-synth-detail-section-h{
    margin:0 0 6px;
    padding-bottom:4px;
    font-size:10px;
  }
  .prod-synth-modal--compact .prod-synth-detail-table-wrap{
    flex:1;
    min-height:0;
    max-height:none;
    border-radius:10px;
  }
  .prod-synth-modal--compact .add-row-close{
    top:10px;
    right:10px;
    width:32px;
    height:32px;
    font-size:18px;
  }
}
@media (max-width:900px) and (orientation:landscape){
  .prod-synth-modal--compact .prod-synth-kpis{
    grid-template-columns:repeat(7,minmax(0,1fr));
    gap:5px;
  }
  .prod-synth-modal--compact .prod-synth-kpi{padding:6px 5px}
  .prod-synth-modal--compact .prod-synth-kpi .val{font-size:12px}
  .prod-synth-modal--compact.prod-synth-modal--sessions-open .prod-synth-kpis{
    grid-template-columns:repeat(7,minmax(0,1fr));
  }
}

.add-row-form .form-row{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px}
.add-row-form label{display:block;font-size:10px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}
.add-row-form input,.add-row-form select{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:9px 12px;color:var(--text);font-size:13px;font-family:inherit;outline:none}
.add-row-form input:focus,.add-row-form select:focus{border-color:var(--accent)}
.add-row-form .form-actions{display:flex;gap:10px;justify-content:flex-end;margin-top:20px}
.add-row-form .op-preview{font-size:11px;color:var(--muted);margin-top:4px;min-height:16px}

.sev-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}
.sev-dot.critique{background:var(--danger)}.sev-dot.attention{background:var(--warn)}.sev-dot.info{background:var(--c1)}
.sev-critique{color:var(--danger);font-weight:600}.sev-attention{color:var(--warn);font-weight:600}
.badge{font-size:11px;color:var(--accent);background:var(--accent-bg);padding:3px 10px;border-radius:20px;font-family:monospace}
.badge-ok{color:var(--success);background:rgba(52,211,153,.12)}
.badge-warn{color:var(--warn);background:rgba(251,191,36,.12)}
table.table-std{width:100%;border-collapse:collapse;font-size:13px}
table.table-std th{font-size:10px;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.4px;padding:8px 16px;border-bottom:1px solid var(--border);text-align:left;white-space:nowrap}
table.table-std td{padding:10px 16px;border-bottom:1px solid var(--border)}
table.table-std tr:last-child td{border-bottom:none}
table.table-std tr:hover td{background:var(--accent-bg)}
/* ── MyProd — Import OF PDF ── */
.prod-of-dropzone{border:2px dashed var(--border);border-radius:12px;padding:32px 20px;text-align:center;cursor:pointer;transition:border-color .15s,background .15s}
.prod-of-dropzone:hover,.prod-of-dropzone.prod-of-dropzone--active{border-color:var(--accent);background:var(--accent-bg)}
.prod-of-dropzone-title{font-size:14px;font-weight:700;color:var(--text);margin-bottom:6px}
.prod-of-dropzone-sub{font-size:12px;color:var(--muted)}
.prod-of-preview-table{width:100%;border-collapse:collapse;font-size:12px;margin:12px 0}
.prod-of-preview-table th,.prod-of-preview-table td{padding:8px 10px;border-bottom:1px solid var(--border);text-align:left;vertical-align:middle}
.prod-of-preview-table th{width:38%;font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.4px}
.prod-of-preview-table tr.prod-of-missing td{background:rgba(251,191,36,.08)}
.prod-of-preview-table input{width:100%;padding:8px 10px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text);font-size:13px;font-family:inherit;box-sizing:border-box}
.prod-of-preview-table input:focus{border-color:var(--accent);outline:none;box-shadow:0 0 0 3px rgba(34,211,238,.12)}
.prod-of-statut{font-size:11px;font-weight:700;padding:2px 8px;border-radius:8px;display:inline-block}
.prod-of-statut--valide{color:var(--success);background:rgba(52,211,153,.12)}
.prod-of-statut--attente{color:var(--warn);background:rgba(251,191,36,.12)}
.prod-of-statut--rejete{color:var(--danger);background:rgba(248,113,113,.12)}
.prod-of-row-sub{font-size:11px;color:var(--muted);margin-top:3px;line-height:1.35}
.show-trac-attente-btn{padding:7px 14px;font-size:11px;color:var(--muted);cursor:pointer;text-align:center;
  border-bottom:1px solid var(--border);background:var(--bg);user-select:none;letter-spacing:.3px}
.show-trac-attente-btn:hover{color:var(--accent);background:var(--accent-bg)}
tr.matiere-group td{padding:7px 16px;background:var(--card);font-weight:600;font-size:12px;color:var(--text2);border-bottom:1px solid var(--border);box-shadow:inset 0 1px 0 var(--border)}
.badge-danger{font-size:11px;color:var(--danger);background:rgba(248,113,113,.12);padding:3px 10px;border-radius:20px;font-family:monospace;font-weight:700}
.badge-manuel{font-size:10px;color:var(--c3);background:rgba(52,211,153,.12);padding:2px 7px;border-radius:12px;font-weight:600}
.badge-modif{font-size:10px;color:var(--c4);background:rgba(251,191,36,.12);padding:2px 7px;border-radius:12px;font-weight:600;cursor:help}
.badge-direction{font-size:10px;color:#f472b6;background:rgba(244,114,182,.12);padding:2px 8px;border-radius:20px;font-weight:700;text-transform:uppercase}
.badge-administration{font-size:10px;color:#a78bfa;background:rgba(167,139,250,.12);padding:2px 8px;border-radius:20px;font-weight:700;text-transform:uppercase}
.badge-fabrication{font-size:10px;color:var(--c3);background:rgba(52,211,153,.12);padding:2px 8px;border-radius:20px;font-weight:700;text-transform:uppercase}
.badge-inactif{font-size:10px;color:var(--muted);background:rgba(100,116,139,.12);padding:2px 8px;border-radius:20px;font-weight:700;text-transform:uppercase}
.bar-row{display:flex;align-items:center;gap:10px;margin-bottom:6px;padding:0 16px}
.bar-label{font-size:11px;color:var(--muted);width:160px;text-align:right;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-family:monospace}
.bar-track{flex:1;height:22px;background:var(--bg);border-radius:4px;overflow:hidden}
.bar-fill{height:100%;border-radius:4px;display:flex;align-items:center;padding:0 8px;transition:width .5s}
.bar-val{font-size:10px;color:var(--bg);font-weight:600;font-family:monospace;white-space:nowrap}
/* ── Statut machines ── */
.mst-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px;margin-bottom:24px}
.mst-card{background:var(--card);border:1px solid var(--border);border-radius:14px;overflow:hidden}
.mst-head{display:flex;align-items:center;justify-content:space-between;padding:12px 16px;border-bottom:1px solid var(--border)}
.mst-nom{font-size:14px;font-weight:700;color:var(--text)}
.mst-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}
.mst-body{padding:14px 16px;display:flex;flex-direction:column;gap:8px}
.mst-statut{display:inline-flex;align-items:center;gap:7px;font-size:13px;font-weight:700;padding:5px 12px;border-radius:20px;width:fit-content}
.mst-op{font-size:11px;color:var(--muted)}
.mst-duree{font-size:11px;color:var(--muted);font-variant-numeric:tabular-nums;display:flex;align-items:center;gap:4px}
.mst-duree-val{font-weight:700;color:var(--text)}
.mst-dos{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px 12px;font-size:12px;display:flex;flex-direction:column;gap:3px}
.mst-dos-ref{font-weight:700;color:var(--accent);font-family:monospace;font-size:12px}
.mst-dos-cli{color:var(--text);font-weight:600;font-size:13px}
.mst-dos-des{color:var(--muted);font-size:11px}
/* couleurs par statut */
.mst-production .mst-dot{background:#22c55e}.mst-production .mst-statut{background:rgba(34,197,94,.12);color:#22c55e}
.mst-calage .mst-dot{background:#f97316}.mst-calage .mst-statut{background:rgba(249,115,22,.12);color:#f97316}
.mst-arret .mst-dot{background:#ef4444}.mst-arret .mst-statut{background:rgba(239,68,68,.12);color:#ef4444}
.mst-changement .mst-dot{background:#a78bfa}.mst-changement .mst-statut{background:rgba(167,139,250,.12);color:#a78bfa}
.mst-nettoyage .mst-dot{background:#c084fc}.mst-nettoyage .mst-statut{background:rgba(192,132,252,.12);color:#c084fc}
.mst-eteinte .mst-dot{background:#475569}.mst-eteinte .mst-statut{background:rgba(71,85,105,.12);color:#94a3b8}
.mst-autre .mst-dot{background:#94a3b8}.mst-autre .mst-statut{background:rgba(148,163,184,.12);color:#94a3b8}
.time-kpi{display:grid;grid-template-columns:repeat(auto-fit,minmax(175px,1fr));gap:14px;margin-bottom:24px}
.time-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px 18px}
.tc-label{font-size:11px;color:var(--text2);font-weight:800;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px}
.tc-value{font-size:22px;font-weight:700;font-family:monospace;color:var(--text2)}
.tc-sub{font-size:11px;color:var(--muted);margin-top:3px}
.error-card{border-left:3px solid var(--danger);background:rgba(248,113,113,.06);border-radius:0 8px 8px 0;padding:12px 16px;margin-bottom:8px}
.ec-type{font-size:10px;font-weight:700;color:var(--danger);text-transform:uppercase;letter-spacing:.5px}
.ec-msg{font-size:13px;font-weight:600;color:var(--text)}
.ec-detail{font-size:11px;color:var(--muted);font-family:monospace}
.ec-meta{display:flex;gap:12px;margin-top:6px;font-size:11px;color:var(--text2)}
.section-title{font-size:12px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin:20px 0 10px}
.toast{position:fixed;bottom:max(24px,env(safe-area-inset-bottom,0px));right:max(24px,env(safe-area-inset-right,0px));left:auto;z-index:9999;max-width:min(420px,calc(100vw - 32px));background:var(--card);border-radius:10px;padding:12px 20px;display:flex;align-items:center;gap:10px;box-shadow:0 8px 32px rgba(0,0,0,.4);animation:fadeUp .3s ease-out}
@media (max-width:480px){
  .toast{left:16px;right:16px;bottom:max(16px,env(safe-area-inset-bottom,0px));max-width:none}
}
@keyframes fadeUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
input[type=text],input[type=number],input[type=email],input[type=password],input[type=tel],input[type=date],input[type=time],textarea{
  background:var(--bg);
  border:1px solid var(--border);
  border-radius:8px;
  padding:10px 14px;
  color:var(--text);
  font-size:13px;
  width:100%;
  outline:none;
  font-family:inherit;
}
textarea{min-height:120px;resize:vertical}
select.form-sel{
  background:var(--bg);border:1px solid var(--border);border-radius:8px;
  padding:8px 12px;padding-right:32px;
  color:var(--text);font-size:13px;outline:none;font-family:inherit;
  cursor:pointer;appearance:none;-webkit-appearance:none;
  background-image:url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%2364748b' d='M6 8L1 3h10z'/%3E%3C/svg%3E\");
  background-repeat:no-repeat;background-position:right 10px center;
}
select.form-sel:focus{border-color:var(--accent)}
.btn{background:var(--accent);color:var(--bg);border:none;border-radius:8px;padding:10px 24px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;margin-top:12px;transition:filter .15s,box-shadow .15s,transform .05s}
.btn:hover{filter:brightness(1.05);box-shadow:0 0 0 4px rgba(34,211,238,.18)}
.btn:active{transform:translateY(1px)}
.btn-sm{background:var(--accent);color:var(--bg);border:none;border-radius:6px;padding:6px 14px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;transition:filter .15s,box-shadow .15s,transform .05s}
.btn-sm:hover{filter:brightness(1.05);box-shadow:0 0 0 4px rgba(34,211,238,.18)}
.btn-sm:active{transform:translateY(1px)}
.btn-ghost{background:transparent;color:var(--text2);border:1px solid var(--border);border-radius:6px;padding:6px 14px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;transition:border-color .15s,color .15s,box-shadow .2s}
.btn-ghost:hover{border-color:var(--accent);color:var(--accent);box-shadow:0 0 0 1px rgba(34,211,238,.28),0 0 20px rgba(34,211,238,.16)}
body.light .btn-ghost:hover{box-shadow:0 0 0 1px rgba(8,145,178,.32),0 0 18px rgba(8,145,178,.14)}
.btn-sec{
  background:transparent;
  color:var(--text2);
  border:1px solid var(--border);
  border-radius:8px;
  padding:9px 14px;
  font-size:12px;
  font-weight:600;
  cursor:pointer;
  font-family:inherit;
  transition:border-color .15s,color .15s,box-shadow .2s,transform .05s,filter .15s;
}
.btn-sec:hover{
  border-color:var(--accent);
  color:var(--accent);
  background:var(--accent-bg);
  box-shadow:0 0 0 1px rgba(34,211,238,.22),0 0 18px rgba(34,211,238,.12);
}
body.light .btn-sec:hover{
  box-shadow:0 0 0 1px rgba(8,145,178,.28),0 0 16px rgba(8,145,178,.10);
}
.btn-sec:active{transform:translateY(1px)}
.btn-sec:disabled{opacity:.7;cursor:not-allowed}
.btn-sec.is-active{
  border-color:var(--accent);
  color:var(--accent);
  background:var(--accent-bg);
  box-shadow:0 0 0 1px rgba(34,211,238,.22),0 0 18px rgba(34,211,238,.12);
}
body.light .btn-sec.is-active{
  box-shadow:0 0 0 1px rgba(8,145,178,.28),0 0 16px rgba(8,145,178,.10);
}
/* Modales (contacts expé, édition bobines traçabilité) — styles absents du shell unifié */
.contact-modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:9200;display:flex;align-items:center;justify-content:center;padding:18px;box-sizing:border-box}
body.light .contact-modal-overlay{background:rgba(15,23,42,.42)}
.contact-modal{width:100%;max-width:560px;background:var(--card);border:1px solid var(--border);border-radius:16px;padding:18px 18px 16px;box-shadow:0 24px 64px rgba(0,0,0,.45);position:relative;max-height:min(90vh,calc(100dvh - 36px));overflow:auto}
.contact-modal h3{font-size:16px;font-weight:800;margin:0;padding-right:34px;color:var(--text);line-height:1.25}
.contact-modal-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:12px}
.contact-modal-head h3{padding-right:8px;flex:1}
.contact-close-btn{background:var(--bg);border:1px solid var(--border);cursor:pointer;color:var(--muted);font-size:18px;line-height:1;width:34px;height:34px;border-radius:10px;display:inline-flex;align-items:center;justify-content:center;flex-shrink:0;font-family:inherit;padding:0;transition:border-color .15s,color .15s,background .15s}
.contact-close-btn:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.contact-modal-body{display:block;font-size:13px;color:var(--text)}
.contact-modal-actions{display:flex;gap:10px;justify-content:flex-end;align-items:center;flex-wrap:wrap;margin-top:16px;padding-top:14px;border-top:1px solid var(--border)}
.contact-modal .btn,.contact-modal .btn-sm,.contact-modal .btn-ghost{margin-top:0}
.contact-modal input,.contact-modal select{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px 12px;color:var(--text);font-size:13px;font-family:inherit;outline:none;box-sizing:border-box}
.contact-modal input:focus,.contact-modal select:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12)}
body.light .contact-modal input:focus,body.light .contact-modal select:focus{box-shadow:0 0 0 3px rgba(8,145,178,.12)}
.btn-danger{background:rgba(248,113,113,.15);color:var(--danger);border:1px solid rgba(248,113,113,.3);border-radius:6px;padding:5px 12px;font-size:11px;font-weight:600;cursor:pointer;font-family:inherit}
.msg-sel-btn{
  width:22px;height:22px;border-radius:8px;
  border:1px solid var(--border);
  background:transparent;
  color:var(--muted);
  display:inline-flex;align-items:center;justify-content:center;
  cursor:pointer;
  flex-shrink:0;
  transition:border-color .15s,color .15s,background .15s,box-shadow .2s,transform .05s;
}
.msg-sel-btn:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.msg-sel-btn:active{transform:translateY(1px)}
.msg-sel-btn.on{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.import-row{padding:12px 20px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;gap:12px}
.import-row:hover{background:rgba(255,255,255,.02)}
/* MyCompta — barre d'ajout (acheteurs / comptes) */
.compta-add-bar{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:16px}
.compta-add-bar h3{font-size:15px;font-weight:700;color:var(--text);margin:0 0 14px}
.compta-add-bar-meta{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:14px}
.compta-add-bar-meta .hint{font-size:12px;color:var(--muted)}
.compta-add-bar-fields{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}
.compta-add-bar-fields label{display:block;font-size:10px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}
.compta-add-bar-fields input{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:12px 16px;color:var(--text);font-size:14px;font-family:inherit;outline:none;transition:border-color .15s,box-shadow .15s}
.compta-add-bar-fields input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12)}
body.light .compta-add-bar-fields input:focus{box-shadow:0 0 0 3px rgba(8,145,178,.12)}
.compta-add-bar-actions{display:flex;gap:10px;margin-top:14px;align-items:center}
.dossier-row{padding:14px 20px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center}
.user-row{display:flex;align-items:flex-start;justify-content:space-between;padding:14px 20px;border-bottom:1px solid var(--border);gap:12px}
.ui-name{font-size:14px;font-weight:600;color:var(--text);display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.ui-email{font-size:12px;color:var(--muted);font-family:monospace;margin-top:2px}
.ui-last{font-size:11px;color:var(--muted);margin-top:2px}
.user-actions{display:flex;gap:8px;align-items:center;flex-shrink:0}
.readonly-notice{display:inline-flex;align-items:center;gap:6px;font-size:11px;color:var(--muted);background:rgba(100,116,139,.1);padding:4px 10px;border-radius:20px}
/* Multi-select dropdown */
.multisel-trigger{white-space:nowrap}
.multisel-dropdown label:hover{background:var(--accent-bg);color:var(--text)}
.multisel-dropdown input[type=checkbox]{accent-color:var(--accent);width:14px;height:14px;flex-shrink:0}

/* ── Rentabilité ─────────────────────────────────────────────── */
.compa-table{width:100%;border-collapse:collapse;font-size:13px;margin-top:16px}
.compa-table th{padding:10px 16px;text-align:left;font-size:11px;font-weight:700;
  color:var(--muted);text-transform:uppercase;letter-spacing:.5px;
  border-bottom:2px solid var(--border);white-space:nowrap}
.compa-table td{padding:10px 16px;border-bottom:1px solid var(--border);vertical-align:middle}
.compa-row-label{font-weight:600;color:var(--text);font-size:13px}
.compa-val-theo{font-family:monospace;font-size:14px;color:var(--text2)}
.compa-val-reel{font-family:monospace;font-size:14px;font-weight:700;color:var(--text)}
.ecart-pos{font-family:monospace;font-size:12px;font-weight:700;
  color:var(--success);background:rgba(52,211,153,.12);
  padding:2px 8px;border-radius:20px;white-space:nowrap}
.ecart-neg{font-family:monospace;font-size:12px;font-weight:700;
  color:var(--danger);background:rgba(248,113,113,.12);
  padding:2px 8px;border-radius:20px;white-space:nowrap}
.ecart-neu{font-family:monospace;font-size:12px;color:var(--muted);
  padding:2px 8px;white-space:nowrap}
.conclusion-card{display:flex;align-items:center;gap:16px;
  background:var(--card);border:1px solid var(--border);
  border-radius:12px;padding:18px 24px;margin-bottom:20px}
.conclusion-icon{font-size:32px}
.conclusion-label{font-size:20px;font-weight:800}
.conclusion-sub{font-size:13px;color:var(--muted);margin-top:2px}
.devis-card{background:var(--card);border:1px solid var(--border);
  border-radius:12px;padding:20px;margin-bottom:12px;cursor:pointer;
  transition:border-color .15s}
.devis-card:hover{border-color:var(--accent)}
.devis-card.selected{border-color:var(--accent);background:var(--accent-bg)}
.devis-title{font-size:14px;font-weight:700;color:var(--text);margin-bottom:4px}
.devis-meta{font-size:12px;color:var(--muted);font-family:monospace}
.devis-badges{display:flex;gap:8px;margin-top:8px;flex-wrap:wrap}
.badge-lie{font-size:10px;color:var(--c3);background:rgba(52,211,153,.12);
  padding:2px 8px;border-radius:20px;font-weight:700}
.badge-attente{font-size:10px;color:var(--c4);background:rgba(251,191,36,.12);
  padding:2px 8px;border-radius:20px;font-weight:700}
.form-section{margin-bottom:20px}
.form-section-title{font-size:11px;font-weight:700;color:var(--muted);
  text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px;
  padding-bottom:6px;border-bottom:1px solid var(--border)}
.field-row{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:10px}
.field-row.three{grid-template-columns:1fr 1fr 1fr}
.field-item label{display:block;font-size:11px;color:var(--muted);
  font-weight:600;text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}
.field-item input{width:100%;background:var(--bg);border:1px solid var(--border);
  border-radius:8px;padding:8px 12px;color:var(--text);font-size:13px;
  font-family:inherit;outline:none}
.field-item input:focus{border-color:var(--accent)}
.dos-chip{display:inline-flex;align-items:center;gap:6px;
  background:var(--accent-bg);color:var(--accent);
  border-radius:20px;padding:4px 10px;font-size:12px;font-weight:600;margin:2px}
.dos-chip button{background:none;border:none;color:var(--accent);
  cursor:pointer;font-size:14px;line-height:1;padding:0}
.dos-add-row{display:flex;gap:8px;margin-top:8px}
.dos-add-row select{flex:1;background:var(--bg);border:1px solid var(--border);
  border-radius:8px;padding:8px 12px;color:var(--text);font-size:13px;
  font-family:inherit;outline:none}

/* ── Portail MySifa ─────────────────────────────────────────────── */
.portal-page{position:relative;z-index:1;min-height:100vh;display:flex;flex-direction:column;
  align-items:center;justify-content:flex-start;gap:32px;padding:48px 20px 32px}
.portal-logo{text-align:center}
.portal-logo .brand{font-size:42px;font-weight:800;letter-spacing:-2px}
.portal-logo .brand span{color:var(--accent)}
.portal-logo .tagline{font-size:14px;color:var(--muted);margin-top:8px;letter-spacing:1px}
.portal-search{width:100%;max-width:720px}
.portal-search form{display:flex;gap:10px;align-items:center}
.portal-search input{
  flex:1;
  background:var(--card);
  border:1.5px solid var(--border);
  border-radius:14px;
  padding:14px 16px;
  color:var(--text);
  font-size:14px;
  font-family:inherit;
  outline:none;
  transition:border-color .15s, box-shadow .15s;
}
.portal-search input:focus{border-color:var(--accent);box-shadow:0 0 0 4px rgba(34,211,238,.14)}
.portal-search-input-wrap{position:relative;flex:1}
.portal-search-input-wrap input{width:100%;box-sizing:border-box;padding-left:46px}
.portal-search-glogo{position:absolute;left:14px;top:50%;transform:translateY(-50%);width:20px;height:20px;pointer-events:none;display:flex;align-items:center;justify-content:center}
.portal-search .portal-search-submit{position:absolute;left:-9999px;top:auto;width:1px;height:1px;overflow:hidden}
.portal-search button{
  background:var(--accent);
  color:var(--bg);
  border:none;
  border-radius:14px;
  padding:14px 16px;
  font-size:13px;
  font-weight:800;
  cursor:pointer;
  font-family:inherit;
  display:inline-flex;
  align-items:center;
  gap:8px;
  transition:filter .15s, box-shadow .15s, transform .05s;
}
.portal-search button:hover{filter:brightness(1.05);box-shadow:0 0 0 4px rgba(34,211,238,.18)}
.portal-search button:active{transform:translateY(1px)}
.portal-search-hint{font-size:11px;color:var(--muted);margin-top:8px;text-align:left}
.portal-settings-corner{
  position:fixed;top:20px;right:20px;z-index:100;
  width:52px;height:52px;border-radius:16px;
  display:flex;align-items:center;justify-content:center;
  background:var(--card);border:1px solid var(--border);cursor:pointer;
  color:var(--text2);transition:border-color .15s,background .15s,box-shadow .15s,transform .05s,color .15s;
  padding:0;font-family:inherit}
.portal-settings-corner:hover{
  border-color:var(--accent);background:var(--accent-bg);color:var(--accent);
  box-shadow:0 8px 28px rgba(34,211,238,.12)}
.portal-settings-corner:active{transform:translateY(1px)}
.portal-settings-corner:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.portal-corner-stack{position:fixed;top:20px;right:20px;z-index:120;display:flex;flex-direction:column;gap:10px}
/* Important: must be relative so the badge positions on the right button. */
.portal-corner-stack .portal-settings-corner{position:relative;top:auto;right:auto}
.portal-corner-badge{position:absolute;top:8px;left:8px;min-width:18px;height:18px;padding:0 5px;border-radius:999px;
  background:rgba(248,113,113,.95);color:#fff;font-size:10px;font-weight:800;font-family:monospace;
  display:inline-flex;align-items:center;justify-content:center;box-shadow:0 6px 18px rgba(0,0,0,.25)}
.portal-prof-ring.prof-ring{
  position:absolute;top:-5px;left:-5px;z-index:2;pointer-events:none;
  width:30px;height:30px;background:transparent;border:none;border-radius:50%;
  box-shadow:none;
}
.portal-humeur-badge{
  position:absolute;bottom:-4px;left:-4px;z-index:3;pointer-events:none;
  font-size:16px;line-height:1;
  filter:drop-shadow(0 1px 3px rgba(0,0,0,.55));
}
.portal-prof-ring.prof-ring svg{width:30px;height:30px}
.portal-prof-ring .prof-ring-label{opacity:1;font-size:8px}
.prof-ring{position:relative;flex-shrink:0;width:34px;height:34px}
.prof-ring svg{display:block;width:34px;height:34px}
.prof-ring-track{stroke:var(--border)}
.prof-ring-bar{stroke:var(--accent);stroke-linecap:round;transition:stroke-dashoffset .25s ease}
.prof-ring[data-tier="low"] .prof-ring-bar{stroke:var(--danger)}
.prof-ring[data-tier="mid"] .prof-ring-bar{stroke:var(--warn)}
.prof-ring[data-tier="high"] .prof-ring-bar{stroke:var(--ok)}
.prof-ring-label{
  position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
  font-size:9px;font-weight:800;color:var(--text);letter-spacing:-.02em;
  opacity:0;pointer-events:none;
}
.portal-apps{display:flex;gap:14px;flex-wrap:wrap;justify-content:center;align-items:stretch}
.portal-apps--reorderable .portal-app:not(.portal-app--busy){cursor:grab;touch-action:none}
.portal-apps--reorderable .portal-app--dragging{cursor:grabbing;opacity:.92;z-index:5;
  box-shadow:0 12px 36px rgba(0,0,0,.35);transform:scale(1.02)}
.portal-apps--reorderable .portal-app--placeholder{
  cursor:default;
  background:transparent;
  border:2px dashed rgba(34,211,238,.55);
  box-shadow:none!important;
  transform:none!important;
}
body.light .portal-apps--reorderable .portal-app--placeholder{border-color:rgba(8,145,178,.55)}
.portal-apps--reorderable .portal-app--placeholder:hover{
  border-color:rgba(34,211,238,.75);
  background:rgba(34,211,238,.06);
  box-shadow:none!important;
  transform:none!important;
}
body.light .portal-apps--reorderable .portal-app--placeholder:hover{background:rgba(8,145,178,.06)}
.portal-apps--reorderable .portal-app--placeholder .portal-ph-plus{
  font-size:28px;
  font-weight:900;
  color:var(--muted);
  line-height:1;
  margin-bottom:4px;
}
.portal-apps--reorderable .portal-app--placeholder .portal-ph-label{
  font-size:11px;
  font-weight:800;
  color:var(--muted);
  text-transform:uppercase;
  letter-spacing:.6px;
}
.portal-apps--reorderable .portal-app--disabled{cursor:grab}
.portal-apps-hint{font-size:11px;color:var(--muted);text-align:center;margin:8px 0 0;width:100%;line-height:1.35}
.portal-app{display:flex;flex-direction:column;align-items:center;gap:6px;
  background-color:var(--card);border:1px solid var(--border);border-radius:14px;
  padding:14px 10px;cursor:pointer;transition:all .2s;text-decoration:none;
  width:140px;height:140px;flex:0 0 140px;box-sizing:border-box;
  justify-content:flex-start;aspect-ratio:1/1}
.portal-app--disabled{cursor:default;opacity:.6;position:relative}
.portal-app--disabled:hover{border-color:var(--border);background-color:var(--card)}
.badge-dev{position:absolute;top:8px;right:8px;font-size:9px;font-weight:700;padding:2px 8px;border-radius:20px;background:var(--warn);color:#0a0e17;text-transform:uppercase;letter-spacing:.5px}
.portal-app:hover{border-color:var(--accent);background-color:var(--card);
  transform:translateY(-3px);box-shadow:0 10px 32px rgba(34,211,238,.14)}
.portal-app--busy{pointer-events:none;opacity:.8;position:relative;transform:none!important;box-shadow:none!important}
.portal-app--busy::after{
  content:'Chargement…';position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
  background:rgba(10,14,23,.72);border-radius:16px;font-size:12px;font-weight:700;color:var(--accent);letter-spacing:.02em}
body.light .portal-app--busy::after{background:rgba(255,255,255,.88);color:var(--accent)}
.portal-app-icon{display:flex;align-items:center;justify-content:center;line-height:1;flex-shrink:0;position:relative}
.portal-app-badge{position:absolute;top:-6px;right:-12px;min-width:22px;height:20px;padding:0 7px;border-radius:999px;background:var(--danger);color:#fff;font-size:11px;font-weight:800;font-family:ui-monospace,monospace;display:inline-flex;align-items:center;justify-content:center;box-shadow:0 0 0 2px var(--card);line-height:1;letter-spacing:.5px}
.portal-app-name{font-size:14px;font-weight:800;color:var(--text);flex-shrink:0;text-align:center;line-height:1.2}
.portal-app-desc{font-size:10px;color:var(--muted);text-align:center;max-width:100%;line-height:1.3;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  flex:0 0 auto;margin:0;width:100%}
.portal-user{font-size:12px;color:var(--muted);display:flex;align-items:center;gap:8px}
.portal-logout{background:none;border:none;color:var(--muted);cursor:pointer;
  font-size:12px;font-family:inherit;text-decoration:underline;
  display:inline-flex;align-items:center;gap:6px;line-height:1;padding:4px 6px;border-radius:6px;
  transition:color .15s,box-shadow .2s,background .15s}
.portal-logout:hover{color:var(--accent);text-shadow:0 0 12px rgba(34,211,238,.45);background:rgba(34,211,238,.08)}
.portal-logout:hover:last-of-type{color:var(--danger);text-shadow:0 0 12px rgba(248,113,113,.4);background:rgba(248,113,113,.08)}
body.light .portal-logout:hover{text-shadow:0 0 12px rgba(8,145,178,.35)}
body.light .portal-logout:hover:last-of-type{text-shadow:0 0 12px rgba(220,38,38,.35)}

/* ── Hover tuiles d'application — pastille icône qui passe du fond accent translucide au plein accent ── */
.portal-app{transition:transform .34s cubic-bezier(.22,.61,.36,1),box-shadow .34s cubic-bezier(.22,.61,.36,1),border-color .34s cubic-bezier(.22,.61,.36,1),background-color .34s cubic-bezier(.22,.61,.36,1)}
.portal-app:hover{transform:translateY(-3px);box-shadow:0 12px 26px rgba(27,37,71,.10);border-color:color-mix(in srgb,var(--accent) 30%,var(--border))}
.portal-app-icon{background:var(--accent-bg);color:var(--accent);width:50px;height:50px;border-radius:13px;transition:background .34s cubic-bezier(.22,.61,.36,1),color .34s cubic-bezier(.22,.61,.36,1)}
.portal-app:hover .portal-app-icon{background:var(--accent);color:#fff}
.portal-app--disabled:hover .portal-app-icon{background:var(--accent-bg);color:var(--accent)}

/* ── Pill bar (haut droite) — fusion des 5 cartes corner en un seul cylindre ── */
.portal-corner-stack{padding:8px 6px;background:var(--card);border:1px solid var(--border);border-radius:20px;
  box-shadow:0 8px 32px rgba(0,0,0,.18),inset 0 1px 0 rgba(255,255,255,.04);gap:2px}
body.light .portal-corner-stack{box-shadow:0 8px 32px rgba(15,23,42,.10)}
.portal-corner-stack .portal-settings-corner{
  width:44px;height:44px;border-radius:12px;background:transparent;border:1px solid transparent;
  color:var(--muted);box-shadow:none;transition:background .15s,color .15s,border-color .15s}
.portal-corner-stack .portal-settings-corner:hover{
  background:var(--accent-bg);color:var(--accent);border-color:transparent;box-shadow:none}
.portal-corner-stack .portal-settings-corner:focus-visible{outline:none;box-shadow:0 0 0 3px rgba(34,211,238,.25);background:var(--accent-bg);color:var(--accent)}
.portal-corner-stack .portal-corner-badge{top:4px;left:4px;box-shadow:0 0 0 2px var(--card)}
.portal-corner-stack .portal-prof-ring.prof-ring{top:-2px;left:-2px;width:24px;height:24px}
.portal-corner-stack .portal-prof-ring.prof-ring svg{width:24px;height:24px}
.portal-corner-stack .portal-humeur-badge{bottom:-2px;left:-2px}

/* ── ⌘K badge in the Google search input ── */
.portal-search button.portal-search-cmdk-badge,
.portal-search-cmdk-badge{
  position:absolute;right:14px;top:50%;transform:translateY(-50%);
  display:inline-flex;align-items:center;gap:3px;padding:4px 9px;
  background:transparent!important;border:none!important;border-radius:0!important;
  color:var(--muted)!important;box-shadow:none!important;
  font-family:ui-monospace,'Cascadia Code',monospace;font-size:11px;font-weight:700;
  letter-spacing:.04em;line-height:1;cursor:pointer;user-select:none;
  transition:color .15s;pointer-events:auto;z-index:2}
.portal-search button.portal-search-cmdk-badge:hover,
.portal-search-cmdk-badge:hover{color:var(--accent)!important;filter:none!important;box-shadow:none!important}
.portal-search button.portal-search-cmdk-badge:active,
.portal-search-cmdk-badge:active{transform:translateY(-50%)!important}
.portal-search .portal-search-input-wrap input{padding-right:80px}

@media (max-width:900px){
  /* Portail mobile / tablette : layout vertical, tuiles compactes */
  .portal-page{padding:20px 16px 28px;gap:16px}
  .portal-logo{order:1}
  .portal-logo .brand{font-size:34px;letter-spacing:-1.5px}
  .portal-logo .tagline{font-size:12px;margin-top:4px}
  .portal-corner-stack{
    order:2;
    position:static;
    top:auto;
    right:auto;
    z-index:auto;
    flex-direction:row;
    flex-wrap:wrap;
    justify-content:center;
    gap:8px;
    width:100%;
    margin:0;
  }
  .portal-corner-stack .portal-settings-corner{
    width:40px;
    height:40px;
    border-radius:12px;
  }
  .portal-prof-ring.prof-ring{width:40px;height:40px}
  .portal-search{
    order:3;
    width:100%;
    max-width:100%;
    margin-top:8px;
  }
  .portal-apps-block{order:4;width:100%;max-width:100%}
  .portal-user{order:5;font-size:11px}
  .portal-apps-hint{font-size:10px;margin-top:6px}
  .portal-apps{
    display:grid;
    grid-template-columns:repeat(3, minmax(0, 1fr));
    gap:8px;
    width:100%;
    max-width:min(100%, 320px);
    margin:0 auto;
    justify-items:stretch;
  }
  .portal-app{
    width:auto;
    flex:none;
    height:auto;
    min-height:0;
    aspect-ratio:1;
    max-height:96px;
    padding:8px 4px;
    gap:5px;
    border-radius:12px;
    align-items:center;
    justify-content:center;
  }
  .portal-app:hover{
    transform:none;
    box-shadow:none;
  }
  .portal-app-desc{display:none}
  .portal-app-name{
    font-size:13px;
    font-weight:700;
    line-height:1.15;
    letter-spacing:.01em;
  }
  .portal-app-icon svg{width:28px;height:28px}
  .badge-dev{top:4px;right:4px;font-size:8px;padding:1px 6px}
  .portal-apps--reorderable .portal-app--placeholder .portal-ph-plus{font-size:20px}
  .portal-apps--reorderable .portal-app--placeholder .portal-ph-label{font-size:9px}
}
@media (min-width:520px) and (max-width:900px){
  .portal-apps{
    grid-template-columns:repeat(4, minmax(0, 1fr));
    max-width:min(100%, 400px);
    gap:10px;
  }
  .portal-app{max-height:88px}
}

/* Portail — mobile paysage : header logo + search + corner 3×2, tuiles compactes, footer desktop */
@media (max-width:900px) and (orientation:landscape){
  .portal-page{
    --portal-land-corner:34px;
    --portal-land-corner-gap:4px;
    --portal-land-header-h:calc(var(--portal-land-corner) * 2 + var(--portal-land-corner-gap));
    --portal-land-tile-w:134px;
    --portal-land-tile-h:118px;
    --portal-land-gap:8px;
    display:grid;
    grid-template-columns:auto minmax(0,1fr) auto;
    grid-template-rows:auto minmax(0,1fr) auto;
    gap:6px 10px;
    padding:max(4px,env(safe-area-inset-top,0px)) max(10px,env(safe-area-inset-right,0px)) max(6px,env(safe-area-inset-bottom,0px)) max(10px,env(safe-area-inset-left,0px));
    min-height:100dvh;
    max-height:100dvh;
    height:100dvh;
    overflow:hidden;
    align-items:stretch;
    justify-content:stretch;
    background:var(--bg);
  }
  .portal-logo{
    grid-row:1;
    grid-column:1;
    align-self:center;
    justify-self:start;
    order:unset;
    margin:0;
    text-align:left;
    padding:0 4px 0 2px;
    height:auto;
    display:flex;
    align-items:center;
  }
  .portal-logo .brand{
    font-size:32px;
    font-weight:800;
    letter-spacing:-1.2px;
    line-height:1;
    color:var(--text);
  }
  .portal-logo .brand span{color:var(--accent)}
  .portal-logo .tagline{display:none}
  .portal-search{
    display:flex!important;
    grid-row:1;
    grid-column:2;
    order:unset;
    align-self:center;
    justify-self:center;
    width:100%;
    max-width:min(88%,520px);
    margin:0 auto;
    min-width:0;
    height:auto;
    flex-direction:column;
    justify-content:center;
  }
  .portal-search form{width:100%;align-items:center}
  .portal-search-hint{display:none}
  .portal-search-input-wrap{width:100%}
  .portal-search-input-wrap input{
    width:100%;
    min-height:unset;
    max-height:unset;
    padding:10px 12px;
    padding-left:38px;
    font-size:13px;
    border-radius:12px;
    border-width:1.5px;
    background:var(--card);
    border-color:var(--border);
    color:var(--text);
    box-sizing:border-box;
  }
  .portal-search-input-wrap input:focus{
    border-color:var(--accent);
    box-shadow:0 0 0 4px var(--accent-bg);
  }
  .portal-search-glogo{
    left:11px;
    width:18px;
    height:18px;
  }
  .portal-search-glogo svg{width:18px;height:18px}
  .portal-corner-stack{
    grid-row:1;
    grid-column:3;
    order:unset;
    align-self:center;
    justify-self:end;
    position:static;
    display:grid;
    grid-template-columns:repeat(3,var(--portal-land-corner));
    grid-template-rows:repeat(2,var(--portal-land-corner));
    gap:var(--portal-land-corner-gap);
    width:calc(var(--portal-land-corner) * 3 + var(--portal-land-corner-gap) * 2);
    height:var(--portal-land-header-h);
    margin:0;
  }
  .portal-corner-stack .portal-settings-corner{
    width:100%;
    height:100%;
    min-width:0;
    min-height:0;
    border-radius:8px;
    padding:0;
    background:var(--card);
    border:1px solid var(--border);
    color:var(--text2);
  }
  .portal-corner-stack .portal-settings-corner:hover{
    border-color:var(--accent);
    background:var(--accent-bg);
    color:var(--accent);
  }
  .portal-corner-stack .portal-settings-corner svg{width:16px;height:16px}
  .portal-prof-ring.prof-ring{width:22px;height:22px;top:-2px;left:-2px}
  .portal-prof-ring.prof-ring svg{width:22px;height:22px}
  .portal-corner-badge{top:2px;left:2px;min-width:14px;height:14px;font-size:8px}
  .portal-humeur-badge{bottom:-2px;left:-2px;font-size:13px}
  .portal-apps-block{
    grid-row:2;
    grid-column:1 / -1;
    order:unset;
    min-height:0;
    height:100%;
    width:100%;
    max-width:none;
    margin:0;
    padding:4px 0;
    overflow:hidden;
    display:flex;
    align-items:center;
    justify-content:center;
    box-sizing:border-box;
  }
  .portal-apps-hint{display:none}
  .portal-apps{
    display:grid;
    grid-template-rows:repeat(2,var(--portal-land-tile-h));
    grid-auto-flow:column;
    grid-auto-columns:var(--portal-land-tile-w);
    gap:var(--portal-land-gap);
    width:max-content;
    max-width:100%;
    height:auto;
    max-height:100%;
    margin:0 auto;
    padding:0 4px;
    overflow-x:auto;
    overflow-y:hidden;
    -webkit-overflow-scrolling:touch;
    scrollbar-width:thin;
    scrollbar-color:var(--border) transparent;
    box-sizing:border-box;
    align-content:center;
  }
  .portal-apps::-webkit-scrollbar{height:4px}
  .portal-apps::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px}
  .portal-app{
    width:var(--portal-land-tile-w);
    height:var(--portal-land-tile-h);
    min-width:56px;
    min-height:56px;
    max-width:var(--portal-land-tile-w);
    max-height:var(--portal-land-tile-h);
    flex:none;
    aspect-ratio:unset;
    padding:10px 8px;
    gap:6px;
    border-radius:14px;
    background-color:var(--card);
    border:1px solid var(--border);
    box-sizing:border-box;
    justify-content:center;
  }
  .portal-app:hover{
    transform:none;
    border-color:var(--accent);
    background-color:var(--card);
    box-shadow:none;
  }
  .portal-app-name{
    font-size:12px;
    font-weight:800;
    line-height:1.15;
    color:var(--text);
    max-width:100%;
    overflow:hidden;
    text-overflow:ellipsis;
    white-space:nowrap;
  }
  .portal-app-desc{
    display:-webkit-box;
    -webkit-box-orient:vertical;
    -webkit-line-clamp:2;
    overflow:hidden;
    font-size:10px;
    color:var(--muted);
    text-align:center;
    line-height:1.25;
    max-width:100%;
    flex:0 1 auto;
    margin:0;
    white-space:normal;
  }
  .portal-app-icon svg{width:22px;height:22px;color:var(--text2)}
  .portal-app:hover .portal-app-icon svg{color:var(--accent)}
  .portal-apps--reorderable .portal-app--placeholder{
    width:var(--portal-land-tile-w);
    height:var(--portal-land-tile-h);
    min-width:56px;
    min-height:56px;
    border:2px dashed var(--border);
    background:transparent;
    box-shadow:none;
  }
  .portal-apps--reorderable .portal-app--placeholder:hover{
    border-color:var(--accent);
    background:var(--accent-bg);
  }
  .portal-apps--reorderable .portal-app--placeholder .portal-ph-plus{font-size:22px;color:var(--muted)}
  .portal-apps--reorderable .portal-app--placeholder .portal-ph-label{font-size:10px;color:var(--muted)}
  /* Footer identique au desktop */
  .portal-user{
    grid-row:3;
    grid-column:1 / -1;
    order:unset;
    font-size:12px;
    color:var(--muted);
    display:flex;
    align-items:center;
    gap:8px;
    justify-content:center;
    flex-wrap:wrap;
    height:auto;
    min-height:unset;
    max-height:none;
    margin:0;
    padding:6px 8px 2px;
    border-top:none;
    background:transparent;
    flex-shrink:0;
    overflow:visible;
    box-sizing:border-box;
  }
  .portal-user>span:first-of-type{
    display:inline-flex;
    align-items:center;
    gap:8px;
    max-width:40vw;
    overflow:hidden;
    text-overflow:ellipsis;
    white-space:nowrap;
  }
  .portal-logout{
    background:none;
    border:none;
    border-radius:6px;
    padding:4px 6px;
    font-size:12px;
    font-weight:inherit;
    min-height:unset;
    text-decoration:underline;
    color:var(--muted);
    box-sizing:border-box;
  }
  .portal-logout:hover{
    color:var(--accent);
    background:var(--accent-bg);
    text-shadow:0 0 12px var(--accent-bg);
    border:none;
  }
  .portal-logout:last-of-type:hover{
    color:var(--danger);
    background:var(--accent-bg);
    text-shadow:0 0 12px var(--accent-bg);
  }
  body.light .portal-logout:hover{text-shadow:0 0 12px var(--accent-bg)}
  .portal-logout .theme-label{display:inline}
  .portal-logout .theme-ico,
  .portal-logout svg{width:16px;height:16px;flex-shrink:0}
}

/* ── MyStock ────────────────────────────────────────────────────── */
.stock-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:24px}
@media (max-width:900px){.stock-grid{grid-template-columns:repeat(2,1fr)}}
@media (max-width:520px){.stock-grid{grid-template-columns:1fr}}
.stock-cell{background:var(--card);border:1px solid var(--border);border-radius:12px;
  padding:16px;cursor:pointer;transition:all .15s}
.stock-cell:hover{border-color:var(--accent)}
.stock-cell.active{border-color:var(--accent);background:var(--accent-bg)}
.stock-cell-label{font-size:16px;font-weight:800;font-family:monospace;
  color:var(--accent);margin-bottom:8px}
.stock-cell-items{font-size:11px;color:var(--muted);line-height:1.6}
.stock-cell-empty{font-size:11px;color:var(--border);font-style:italic}
.stock-badge{display:inline-block;background:var(--accent-bg);color:var(--accent);
  border-radius:20px;padding:2px 8px;font-size:10px;font-weight:700;
  font-family:monospace;margin-left:4px}
.mvt-type-entree{color:var(--success);font-weight:700}
.mvt-type-sortie{color:var(--danger);font-weight:700}
.mvt-type-pf-entree{color:var(--pf-entree);font-weight:700}
.mvt-type-pf-sortie{color:var(--pf-sortie);font-weight:700}
.mvt-type-inventaire{color:var(--c2);font-weight:700}
.search-bar{width:100%;background:var(--bg);border:1px solid var(--border);
  border-radius:10px;padding:10px 16px;color:var(--text);font-size:14px;
  font-family:inherit;outline:none;margin-bottom:16px}
.search-bar:focus{border-color:var(--accent)}
.stock-panel{display:flex;gap:20px;align-items:flex-start}
.stock-left{flex:0 0 280px}
.stock-right{flex:1}
.produit-row{padding:10px 16px;border-bottom:1px solid var(--border);
  cursor:pointer;display:flex;justify-content:space-between;align-items:center;
  transition:background .12s}
.produit-row:hover{background:var(--accent-bg)}
.produit-row.active{background:var(--accent-bg);border-left:3px solid var(--accent)}
.produit-ref{font-family:monospace;font-weight:700;font-size:13px;color:var(--text)}
.produit-des{font-size:11px;color:var(--muted);margin-top:2px}
.mouvement-form{background:var(--card);border:1px solid var(--border);
  border-radius:12px;padding:20px;margin-bottom:16px}
.mvt-btns{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap}
.mvt-btn{padding:8px 16px;border-radius:8px;border:1px solid var(--border);
  background:transparent;color:var(--text2);cursor:pointer;font-size:12px;
  font-weight:600;font-family:inherit;transition:all .15s}
.mvt-btn.active-entree{background:rgba(52,211,153,.15);color:var(--success);
  border-color:var(--success)}
.mvt-btn.active-sortie{background:rgba(248,113,113,.15);color:var(--danger);
  border-color:var(--danger)}
.mvt-btn.active-pf-entree{background:color-mix(in srgb,var(--pf-entree) 18%,transparent);color:var(--pf-entree);
  border-color:var(--pf-entree)}
.mvt-btn.active-pf-sortie{background:color-mix(in srgb,var(--pf-sortie) 18%,transparent);color:var(--pf-sortie);
  border-color:var(--pf-sortie)}
.mvt-btn.active-inventaire{background:rgba(167,139,250,.15);color:var(--c2);
  border-color:var(--c2)}
.stock-search-row{display:flex;gap:10px;align-items:stretch;margin-bottom:16px;flex-wrap:wrap}
.stock-search-row .search-bar{margin-bottom:0;flex:1;min-width:180px}
.stock-search-bar{
  position:sticky;top:0;z-index:80;
  width:100%;
  background:var(--card);
  border-bottom:1px solid var(--border);
  padding:10px 20px;
  display:flex;align-items:center;gap:10px;
}
@media (max-width: 900px){
  /* La topbar mobile est fixe : on colle la search juste dessous */
  .stock-search-bar{top:74px;z-index:110}
}
.stock-search-input{
  flex:1;background:var(--bg);
  border:1px solid var(--border);border-radius:10px;
  padding:10px 16px;color:var(--text);font-size:14px;
  font-family:inherit;outline:none;transition:border-color .15s;
}
.stock-search-input:focus{border-color:var(--accent)}
.stock-search-btn{
  width:40px;height:40px;border-radius:10px;
  border:1px solid var(--border);background:var(--bg);
  color:var(--text2);cursor:pointer;font-size:18px;
  display:flex;align-items:center;justify-content:center;
  transition:all .15s;flex-shrink:0;
}
.stock-search-btn svg{width:18px;height:18px;display:block}
.stock-search-btn:hover{border-color:var(--accent);color:var(--accent)}
.stock-search-btn.active{
  border-color:var(--accent);color:var(--accent);
  background:var(--accent-bg);animation:pulse 1s infinite;
}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(34,211,238,.3)}50%{box-shadow:0 0 0 6px rgba(34,211,238,0)}}
.camera-modal{
  position:fixed;inset:0;background:rgba(0,0,0,.85);
  z-index:200;display:flex;flex-direction:column;
  align-items:center;justify-content:center;gap:16px;padding:20px;
}
.camera-video-wrap{
  position:relative;width:100%;max-width:400px;
  border-radius:16px;overflow:hidden;background:#000;
}
.camera-video{width:100%;border-radius:16px;display:block}
.camera-overlay{
  position:absolute;inset:0;display:flex;
  align-items:center;justify-content:center;pointer-events:none;
}
.camera-frame{
  width:200px;height:200px;border-radius:12px;
  border:2px solid var(--accent);
  box-shadow:0 0 0 2000px rgba(0,0,0,.4);
}
.camera-hint{font-size:13px;color:var(--text2);text-align:center;max-width:320px}
.camera-result{
  background:var(--accent-bg);border:1px solid var(--accent);
  border-radius:10px;padding:12px 20px;
  font-family:monospace;font-size:14px;color:var(--accent);
  min-width:200px;text-align:center;
}
.camera-close{
  background:var(--danger);color:#fff;border:none;
  border-radius:10px;padding:10px 28px;font-size:14px;
  font-weight:600;cursor:pointer;font-family:inherit;
}
.search-suggestions{
  position:absolute;top:100%;left:0;right:0;z-index:100;
  background:var(--card);border:1px solid var(--border);
  border-radius:0 0 10px 10px;max-height:200px;overflow-y:auto;
  box-shadow:0 8px 24px rgba(0,0,0,.3);
}
.search-suggestion-item{
  padding:10px 16px;cursor:pointer;font-size:13px;
  border-bottom:1px solid var(--border);display:flex;
  justify-content:space-between;align-items:center;
}
.search-suggestion-item:hover{background:var(--accent-bg);color:var(--accent)}
.search-suggestion-ref{font-family:monospace;font-weight:700}
.search-suggestion-des{font-size:11px;color:var(--muted)}
.search-suggestion-empl .search-suggestion-ref{color:var(--c2)}
.search-suggestion-section{font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;
  letter-spacing:.06em;padding:8px 16px 4px;background:var(--bg);border-bottom:1px solid var(--border)}
.stock-search-wrap{position:relative;flex:1}
/* Saisie emplacement en majuscules, placeholder en « phrase » (seule la 1ʳᵉ lettre en capitale). */
.stock-add-empl-input{text-transform:uppercase}
.stock-add-empl-input::placeholder{
  text-transform:none;
  color:var(--text2);
  opacity:.88;
}
body.light .stock-add-empl-input::placeholder{
  color:#64748b;
  opacity:.95;
}
.stock-empl-suggest-add{
  padding:10px 16px;cursor:pointer;font-size:13px;font-weight:700;
  border-top:2px solid var(--border);
  background:rgba(167,139,250,.14);color:var(--c2);
  transition:background .12s,color .12s;
}
.stock-empl-suggest-add:hover{background:rgba(167,139,250,.26);color:var(--text)}
body.light .stock-empl-suggest-add{background:rgba(124,58,237,.12);color:#5b21b6}
body.light .stock-empl-suggest-add:hover{background:rgba(124,58,237,.2);color:#1e1b4b}
.nav-tabs{display:flex;gap:0;margin-bottom:24px;border-bottom:1px solid var(--border)}
.nav-tab{padding:10px 18px;background:transparent;border:none;border-bottom:2px solid transparent;
  color:var(--text2);cursor:pointer;font-size:13px;font-weight:500;font-family:inherit;
  transition:all .15s;margin-bottom:-1px}
.nav-tab:hover{color:var(--text);background:var(--accent-bg)}
.nav-tab.active{color:var(--accent);border-bottom-color:var(--accent);font-weight:600}

/* ── MyExpé ─────────────────────────────────────────────────────── */
.expe-fields{display:grid;grid-template-columns:repeat(4,minmax(150px,1fr));gap:12px}
@media(max-width:1100px){.expe-fields{grid-template-columns:repeat(2,minmax(150px,1fr))}}
@media(max-width:520px){.expe-fields{grid-template-columns:1fr}}
.expe-field label{display:block;font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.6px;margin-bottom:6px}
.expe-field input,.expe-field select{width:100%;padding:10px 14px;background:var(--bg);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:14px;font-family:inherit;outline:none}
.expe-field input:focus,.expe-field select:focus{border-color:var(--accent)}
.expe-help{font-size:10px;color:var(--muted);margin-top:4px}
.expe-departs-table tbody tr:nth-child(even) td{background:rgba(148,163,184,.06)}
.expe-departs-table tbody tr:hover td{background:rgba(34,211,238,.06)}
.expe-dep-actions-td{max-width:none!important;overflow:visible;text-overflow:clip;white-space:normal;vertical-align:middle}
.expe-day-sep-row td.expe-day-sep-cell {
  padding: 28px 14px 12px !important;
  background: var(--bg) !important;
  border-top: 2px solid var(--border);
}
.expe-departs-table tbody tr.expe-day-sep-row:hover td{background:var(--bg)!important}
.expe-day-sep-label {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--text2);
}
.expe-dep-actions-cell{display:flex;flex-direction:row;align-items:center;justify-content:flex-end;gap:10px}
.expe-dep-acts{display:grid;grid-template-columns:repeat(3,1fr);gap:4px;flex-shrink:0}
.expe-dep-acts .btn-ghost,.expe-dep-acts .btn-danger{width:32px;height:30px;padding:0;margin:0;
  display:flex;align-items:center;justify-content:center;border-radius:6px}
.expe-dep-valider-btn{margin:0;padding:8px 12px;font-size:11px;font-weight:700;border-radius:10px;
  white-space:nowrap;flex-shrink:0}
.expe-dep-invalider-btn{margin:0;padding:8px 12px;font-size:11px;font-weight:700;border-radius:10px;
  white-space:nowrap;flex-shrink:0;background:color-mix(in srgb,var(--warn) 18%,transparent);
  border:1px solid color-mix(in srgb,var(--warn) 45%,var(--border));color:var(--warn)}
.expe-dep-invalider-btn:hover{filter:brightness(1.06)}
.expe-hist-pager{display:flex;align-items:center;justify-content:flex-end;gap:8px;flex-wrap:wrap;
  padding:12px 18px;border-top:1px solid var(--border)}
.expe-hist-pager .page-btn{padding:6px 12px;border-radius:7px;border:1px solid var(--border);
  background:transparent;color:var(--text2);cursor:pointer;font-size:12px;font-family:inherit}
.expe-hist-pager .page-btn:hover:not(:disabled){border-color:var(--accent);color:var(--accent)}
.expe-hist-pager .page-btn:disabled{opacity:.35;cursor:not-allowed}
.expe-hist-pager .page-info{font-size:12px;color:var(--muted);padding:0 4px;white-space:nowrap}
.expe-dep-ab[title],.expe-dep-valider-btn[title],.expe-dep-invalider-btn[title]{position:relative;overflow:visible}
.expe-dep-ab[title]:hover::after,.expe-dep-valider-btn[title]:hover::after,.expe-dep-invalider-btn[title]:hover::after{
  content:attr(title);position:absolute;bottom:calc(100% + 7px);left:50%;transform:translateX(-50%);
  background:var(--card);border:1px solid var(--border);border-radius:7px;
  padding:6px 10px;font-size:10px;font-weight:500;color:var(--text2);line-height:1.4;
  white-space:normal;max-width:240px;text-align:center;
  pointer-events:none;z-index:200;box-shadow:0 4px 16px color-mix(in srgb,var(--bg) 55%,transparent)}
.expe-dep-ab[title]:hover::before,.expe-dep-valider-btn[title]:hover::before,.expe-dep-invalider-btn[title]:hover::before{
  content:'';position:absolute;bottom:calc(100% + 2px);left:50%;transform:translateX(-50%);
  border:5px solid transparent;border-top-color:var(--border);pointer-events:none;z-index:200}
.expe-hist-table th{padding:6px 10px;font-size:9px}

/* MyExpé — onglets internes modal Ajouter départ */
.expe-form-tabs{display:flex;gap:4px;margin-bottom:14px;border-bottom:1px solid var(--border);padding-bottom:0}
.expe-form-tab{background:transparent;border:none;color:var(--muted);font-size:13px;font-weight:600;padding:10px 16px;cursor:pointer;border-bottom:2px solid transparent;display:inline-flex;align-items:center;gap:6px;transition:color .15s,border-color .15s}
.expe-form-tab:hover{color:var(--text2)}
.expe-form-tab.active{color:var(--accent);border-bottom-color:var(--accent)}

/* MyExpé — picker dossier */
.expe-picker-wrap{display:flex;flex-direction:column;gap:10px}
.expe-picker-hint{font-size:11px;color:var(--muted);line-height:1.5;padding:0 2px}
.expe-picker-search{width:100%;padding:10px 14px;border:1px solid var(--border);background:var(--bg);color:var(--text);border-radius:10px;font-size:13px;outline:none;transition:border-color .15s}
.expe-picker-search:focus{border-color:var(--accent)}
.expe-picker-list{max-height:420px;overflow-y:auto;border:1px solid var(--border);border-radius:10px;background:var(--bg);padding:6px}
.expe-picker-section{font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.6px;padding:8px 6px 4px}
.expe-picker-item{padding:10px 12px;margin:2px 0;border:1px solid var(--border);border-radius:8px;cursor:pointer;background:var(--card);transition:border-color .15s,background .15s}
.expe-picker-item:hover{border-color:var(--accent);background:var(--accent-bg)}
.expe-picker-item--active{border-left:3px solid var(--accent)}
.expe-picker-line1{font-size:13px;font-weight:700;display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.expe-picker-ref{color:var(--accent);font-family:monospace}
.expe-picker-sep{color:var(--muted);font-weight:400}
.expe-picker-client{color:var(--text)}
.expe-picker-line2{font-size:12px;color:var(--text2);margin-top:3px}
.expe-picker-meta{font-size:10px;color:var(--muted);display:flex;gap:8px;margin-top:5px;flex-wrap:wrap;align-items:center}
.expe-picker-statut{padding:2px 8px;border-radius:10px;font-weight:700;text-transform:uppercase;letter-spacing:.3px;font-size:9px}
.expe-picker-statut--en_cours{background:rgba(34,211,238,.18);color:var(--accent)}
.expe-picker-statut--attente{background:rgba(251,191,36,.18);color:var(--warn)}
.expe-picker-statut--termine{background:rgba(52,211,153,.18);color:var(--success,#34d399)}
.expe-picker-warn{background:rgba(248,113,113,.15);color:var(--danger);padding:2px 8px;border-radius:10px;font-weight:600;font-size:9px;text-transform:uppercase;letter-spacing:.3px}
.expe-picker-empty{padding:24px 12px;text-align:center;color:var(--muted);font-size:13px}

/* MyExpé — sidebar sections collapsibles */
.expe-sidebar-sections{display:flex;flex-direction:column;gap:2px}
.expe-sec-header{display:flex;align-items:center;gap:8px;background:transparent;border:none;
  padding:14px 16px 6px 12px;cursor:pointer;color:var(--muted);
  font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.7px;
  width:100%;text-align:left;transition:color .15s}
.expe-sec-header:hover{color:var(--text2)}
.expe-sec-header.has-active{color:var(--text2)}
.expe-sec-header .expe-sec-chev{display:inline-flex;transition:transform .15s;flex-shrink:0;color:var(--muted)}
.expe-sec-header.collapsed .expe-sec-chev{opacity:.6}
.expe-sec-header.has-active .expe-sec-chev{color:var(--accent)}
.expe-sec-label{flex:1}
.expe-sec-body{display:flex;flex-direction:column;gap:2px;padding-bottom:4px}

/* MyExpé — Palettes Europe */
.expe-pal-eur-totaux{display:grid;grid-template-columns:repeat(4,minmax(140px,1fr));gap:12px;margin-bottom:14px}
@media(max-width:760px){.expe-pal-eur-totaux{grid-template-columns:repeat(2,1fr)}}
.expe-pal-eur-tot-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px 18px}
.expe-pal-eur-tot-card--ok{border-left:3px solid var(--success,#34d399)}
.expe-pal-eur-tot-card--warn{border-left:3px solid var(--warn)}
.expe-pal-eur-tot-card--bad{border-left:3px solid var(--danger)}
.expe-pal-eur-tot-lbl{font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.6px;margin-bottom:6px}
.expe-pal-eur-tot-val{font-size:24px;font-weight:800;color:var(--text);font-family:monospace}
.expe-pal-eur-recap{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px}
.expe-pal-eur-recap-card{background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:12px 14px}
.expe-pal-eur-recap-card--debt{border-left:3px solid var(--warn)}
.expe-pal-eur-recap-client{font-size:13px;font-weight:700;color:var(--text);margin-bottom:8px;padding-bottom:6px;border-bottom:1px solid var(--border)}
.expe-pal-eur-recap-row{display:flex;justify-content:space-between;align-items:center;padding:3px 0;font-size:12px}
.expe-pal-eur-recap-row--solde{margin-top:6px;padding-top:6px;border-top:1px solid var(--border);font-weight:700}
.expe-pal-eur-recap-lbl{color:var(--text2)}
.expe-pal-eur-recap-val{font-family:monospace;font-weight:600;color:var(--text)}
.expe-pal-eur-recap-val--ok{color:var(--success,#34d399)}
.expe-pal-eur-recap-val--bad{color:var(--danger)}
.expe-pal-eur-recap-val--warn{color:var(--warn)}
.expe-pal-eur-badge{padding:3px 10px;border-radius:12px;font-weight:700;text-transform:uppercase;letter-spacing:.3px;font-size:10px;white-space:nowrap}
.expe-pal-eur-badge--en_attente{background:rgba(251,191,36,.18);color:var(--warn)}
.expe-pal-eur-badge--retournee{background:rgba(52,211,153,.18);color:var(--success,#34d399)}
.expe-pal-eur-badge--perdue{background:rgba(248,113,113,.18);color:var(--danger)}
.expe-pal-eur-acts-cell{white-space:nowrap;text-align:right}
.expe-pal-eur-acts{display:inline-flex;gap:4px;justify-content:flex-end}
.expe-pal-eur-act{width:30px;height:30px;padding:0;display:inline-flex;align-items:center;justify-content:center;
  background:transparent;border:1px solid var(--border);border-radius:7px;cursor:pointer;color:var(--text2);
  transition:border-color .15s,color .15s,background .15s}
.expe-pal-eur-act:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.expe-pal-eur-act--ok:hover{border-color:var(--success,#34d399);color:var(--success,#34d399);background:rgba(52,211,153,.12)}
.expe-pal-eur-act--bad:hover{border-color:var(--danger);color:var(--danger);background:rgba(248,113,113,.12)}
.expe-hist-table td{padding:6px 10px;max-width:140px}
.expe-hist-table td:nth-child(1){max-width:110px} /* Validé le */
.expe-hist-table td:nth-child(2){max-width:120px} /* Par */
.expe-hist-table td:nth-child(4){max-width:160px} /* Client */
.expe-hist-table td:nth-child(5){max-width:160px} /* Réf SIFA */
.expe-hist-table td:nth-child(7){max-width:140px} /* Cde transp. */
.expe-hist-table td:nth-child(8){max-width:140px} /* N° BL */
.expe-hist-table td:nth-child(9){max-width:140px} /* Transp. */
.expe-top3{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;margin-bottom:18px}
.expe-score{background:var(--card);border:1px solid var(--border);border-radius:14px;overflow:hidden;position:relative}
.expe-score .stripe{height:4px}
.expe-score .body{padding:16px 20px}
.expe-score .carrier{font-size:18px;font-weight:800;letter-spacing:-.5px}
.expe-score .price{font-size:28px;font-weight:800;font-family:monospace;margin:8px 0}
.expe-score .price .unit{font-size:13px;font-weight:500;color:var(--muted);margin-left:4px}
.expe-score .medal{font-size:24px;flex-shrink:0}
.expe-note{font-size:10px;color:rgba(148,163,184,.8);margin-top:12px}

/* MyExpé — mobile : titres de page / sections déjà dans la topbar */
@media (max-width:900px){
  body.mysifa-app-expe .main .container > h1,
  body.mysifa-app-expe .main .container > .subtitle{
    display:none!important;
  }
  body.mysifa-app-expe .expe-mobile-hide-head{display:none!important}
  body.mysifa-app-expe .card-header:has(> .expe-mobile-hide-head:only-child){display:none}
  body.mysifa-app-expe .card-header:has(> h3.expe-mobile-hide-head){
    min-height:0;
    padding-top:10px;
    padding-bottom:10px;
  }
}
__EXPE_TRANSPORTEURS_CSS__
__EXPE_COMPARATEUR_CSS__
__EXPE_DEVIS_CSS__
__EXPE_CARTE_FRANCE_CSS__
/* ── Paie (onglet MyCompta) ── */
.paie-layout{display:flex;gap:14px;height:calc(100vh - 210px);overflow:hidden}
.paie-emp-panel{width:252px;flex-shrink:0;display:flex;flex-direction:column;background:var(--card);border:1px solid var(--border);border-radius:14px;overflow:hidden}
.paie-emp-head{padding:10px 12px;border-bottom:1px solid var(--border);flex-shrink:0}
.paie-emp-head input{width:100%;padding:7px 10px;background:var(--bg);border:1.5px solid var(--border);border-radius:8px;color:var(--text);font-size:12px;font-family:inherit;outline:none}
.paie-emp-head input:focus{border-color:var(--accent)}
.paie-emp-hint{font-size:9px;color:var(--muted);margin-top:4px;line-height:1.4}
.paie-emp-list{flex:1;overflow-y:auto;padding:5px}
.paie-emp-item{padding:8px 10px;border-radius:7px;cursor:pointer;border:1px solid transparent;margin-bottom:2px;transition:all .12s}
.paie-emp-item:hover{background:var(--accent-bg);border-color:rgba(34,211,238,.2)}
.paie-emp-item.active{background:var(--accent-bg);border-color:var(--accent)}
.paie-emp-name{font-size:12px;font-weight:700;color:var(--text)}
.paie-emp-sub{font-size:10px;color:var(--muted);margin-top:1px}
.paie-form-col{flex:1;display:flex;flex-direction:column;overflow:hidden;gap:10px}
.paie-period-bar{display:flex;align-items:center;gap:10px;flex-shrink:0;background:var(--card);border:1px solid var(--border);border-radius:11px;padding:9px 14px;flex-wrap:wrap}
.paie-period-nav{display:flex;align-items:center;gap:7px}
.paie-pbtn{padding:5px 10px;border-radius:7px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-size:14px;font-family:inherit;transition:all .12s}
.paie-pbtn:hover{border-color:var(--accent);color:var(--accent)}
.paie-plbl{font-size:14px;font-weight:700;color:var(--accent);min-width:130px;text-align:center}
.paie-xbtn{margin-left:auto;display:flex;align-items:center;gap:7px;padding:7px 13px;border-radius:8px;background:var(--accent);color:#0a0e17;font-weight:700;font-size:11px;border:none;cursor:pointer;font-family:inherit;transition:opacity .15s}
.paie-xbtn:hover{opacity:.85}.paie-xbtn:disabled{opacity:.4;cursor:not-allowed}
.paie-hist-btn{display:flex;align-items:center;gap:6px;padding:7px 11px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);font-size:11px;cursor:pointer;font-family:inherit;transition:all .12s}
.paie-hist-btn:hover{border-color:var(--accent);color:var(--accent)}
.paie-form-scroll{flex:1;overflow-y:auto;padding-right:2px}
.paie-sec{background:var(--card);border:1px solid var(--border);border-radius:12px;margin-bottom:10px;overflow:hidden}
.paie-sec-title{padding:9px 14px;font-size:10px;font-weight:800;color:var(--accent);text-transform:uppercase;letter-spacing:.5px;background:rgba(34,211,238,.04);border-bottom:1px solid var(--border)}
.paie-fgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr))}
.paie-f{padding:8px 12px;border-bottom:1px solid var(--border);border-right:1px solid var(--border);display:flex;flex-direction:column;gap:3px}
.paie-f.full{grid-column:1/-1}
.paie-flbl{font-size:9px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.3px}
.paie-f input,.paie-f select,.paie-f textarea{background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:12px;font-family:inherit;padding:6px 9px;outline:none;width:100%;transition:border-color .12s}
.paie-f input:focus,.paie-f select:focus,.paie-f textarea:focus{border-color:var(--accent)}
.paie-f textarea{resize:vertical;min-height:50px}
.paie-f select option{background:var(--card)}
.paie-emp-hdr{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;background:var(--card);border:1px solid var(--border);border-radius:11px;padding:10px 14px;flex-shrink:0}
.paie-emp-hdr-name{font-size:15px;font-weight:900}
.paie-emp-hdr-meta{display:flex;gap:7px;flex-wrap:wrap;margin-top:4px}
.paie-badge{font-size:10px;font-weight:700;padding:2px 8px;border-radius:5px;background:var(--accent-bg);color:var(--accent);border:1px solid rgba(34,211,238,.3)}
.paie-svbtn{padding:7px 14px;border-radius:7px;background:var(--accent);color:#0a0e17;font-weight:700;font-size:11px;border:none;cursor:pointer;font-family:inherit;transition:all .15s}
.paie-svbtn:hover{opacity:.85}.paie-svbtn.saved{background:var(--ok)}
.paie-ph{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;color:var(--muted);gap:10px;font-size:13px}
.paie-pw{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:32px 28px;max-width:340px;margin:40px auto;text-align:center}
.paie-pw-inp{width:100%;padding:10px 13px;background:var(--bg);border:1.5px solid var(--border);border-radius:9px;color:var(--text);font-size:15px;font-family:inherit;outline:none;text-align:center;letter-spacing:3px;margin:10px 0}
.paie-pw-inp:focus{border-color:var(--accent)}
.paie-pw-btn{width:100%;padding:11px;border-radius:9px;border:none;background:var(--accent);color:#0a0e17;font-weight:800;font-size:13px;cursor:pointer;font-family:inherit;margin-top:6px;transition:opacity .15s}
.paie-pw-btn:hover{opacity:.85}
.paie-unsaved{width:6px;height:6px;border-radius:50%;background:var(--warn);display:inline-block;margin-left:5px;vertical-align:middle}
.paie-hist-modal{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:500;display:flex;align-items:center;justify-content:center;padding:18px}
.paie-hist-card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:18px;width:420px;max-height:60vh;display:flex;flex-direction:column;box-shadow:0 24px 64px rgba(0,0,0,.45)}
.paie-hist-item{display:flex;align-items:center;justify-content:space-between;padding:9px 12px;border-radius:8px;cursor:pointer;border:1px solid transparent;transition:all .12s;margin-bottom:3px}
.paie-hist-item:hover{background:var(--accent-bg);border-color:rgba(34,211,238,.2)}
.paie-hist-item.active{background:var(--accent-bg);border-color:var(--accent)}
/* ── Dashboards flottants ─────────────────────────── */
.db-fab{
  position:fixed;bottom:24px;right:24px;z-index:300;
  width:48px;height:48px;border-radius:50%;
  background:var(--accent);border:none;cursor:pointer;
  display:flex;align-items:center;justify-content:center;
  box-shadow:0 4px 16px rgba(34,211,238,.35);
  transition:transform .15s,box-shadow .15s;
}
.db-fab:hover{transform:scale(1.08);box-shadow:0 6px 22px rgba(34,211,238,.45)}
.db-fab svg{color:#000;flex-shrink:0}
.db-fab-badge{
  position:absolute;top:-4px;right:-4px;
  min-width:18px;height:18px;padding:0 5px;
  border-radius:999px;background:var(--danger);
  color:#fff;font-size:10px;font-weight:700;
  display:flex;align-items:center;justify-content:center;
  pointer-events:none;
}
.db-panel{
  position:fixed;z-index:290;
  width:300px;min-height:80px;
  background:var(--card);border:1px solid var(--border);
  border-radius:14px;box-shadow:0 8px 32px rgba(0,0,0,.28);
  display:flex;flex-direction:column;
  transition:opacity .2s,transform .2s;
  overflow:hidden;
}
.db-panel--hidden{opacity:0;pointer-events:none;transform:scale(.96)}
.db-panel-head{
  display:flex;align-items:center;gap:8px;
  padding:10px 12px;cursor:grab;user-select:none;
  border-bottom:1px solid var(--border);
  background:var(--card);
}
.db-panel-head:active{cursor:grabbing}
.db-panel-title{
  flex:1;font-size:13px;font-weight:700;
  color:var(--text);white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis;
}
.db-panel-type{
  font-size:10px;font-weight:600;color:var(--muted);
  text-transform:uppercase;letter-spacing:.5px;flex-shrink:0;
}
.db-panel-btn{
  width:26px;height:26px;border-radius:8px;border:none;
  background:transparent;cursor:pointer;
  display:flex;align-items:center;justify-content:center;
  color:var(--muted);transition:background .12s,color .12s;flex-shrink:0;
}
.db-panel-btn:hover{background:var(--accent-bg);color:var(--accent)}
.db-panel-btn--danger:hover{background:rgba(248,113,113,.12);color:var(--danger)}
.db-panel-body{
  padding:12px;overflow-y:auto;max-height:320px;
  font-size:13px;color:var(--text2);
}
.db-panel--mini .db-panel-body{display:none}
.db-panel--mini .db-panel-head{border-bottom:none}
.db-widget-row{
  display:flex;align-items:center;gap:8px;
  padding:6px 0;border-bottom:1px solid var(--border);
}
.db-widget-row:last-child{border-bottom:none}
.db-widget-badge{
  font-size:11px;font-weight:700;padding:2px 7px;
  border-radius:6px;flex-shrink:0;
}
.db-widget-badge--danger{background:rgba(248,113,113,.15);color:var(--danger)}
.db-widget-badge--warn{background:rgba(251,191,36,.15);color:var(--warn)}
.db-widget-badge--ok{background:rgba(52,211,153,.15);color:var(--success)}
.db-widget-label{flex:1;font-size:12px;color:var(--text2);line-height:1.35}
.db-widget-empty{
  text-align:center;color:var(--muted);font-size:12px;padding:16px 0;
}
.db-add-modal-overlay{
  position:fixed;inset:0;z-index:400;
  background:rgba(0,0,0,.55);backdrop-filter:blur(3px);
  display:flex;align-items:center;justify-content:center;
}
.db-add-modal{
  background:var(--card);border:1px solid var(--border);
  border-radius:16px;width:360px;max-width:92vw;
  box-shadow:0 16px 48px rgba(0,0,0,.4);
  display:flex;flex-direction:column;overflow:hidden;
}
.db-add-modal-head{
  display:flex;align-items:center;justify-content:space-between;
  padding:16px 20px;border-bottom:1px solid var(--border);
}
.db-add-modal-title{font-size:15px;font-weight:700;color:var(--text)}
.db-add-modal-body{padding:16px 20px;display:flex;flex-direction:column;gap:10px}
.db-add-item{
  display:flex;align-items:center;gap:12px;
  padding:10px 12px;border-radius:10px;border:1px solid var(--border);
  cursor:pointer;transition:border-color .12s,background .12s;
}
.db-add-item:hover{border-color:var(--accent);background:var(--accent-bg)}
.db-add-item-icon{
  width:36px;height:36px;border-radius:10px;
  background:var(--accent-bg);display:flex;align-items:center;justify-content:center;
  flex-shrink:0;
}
.db-add-item-name{font-size:13px;font-weight:700;color:var(--text)}
.db-add-item-desc{font-size:11px;color:var(--muted);margin-top:2px}
.db-add-empty{text-align:center;color:var(--muted);font-size:13px;padding:16px 0}

/* ══════════════════════════════════════════════════════════════════
   Mobile bottom nav bar — portrait only, présente sur toutes les pages
   ══════════════════════════════════════════════════════════════════ */
.mobile-navbar{
  position:fixed;left:0;right:0;bottom:0;z-index:400;
  display:none;
  background:var(--card);
  border-top:1px solid var(--border);
  box-shadow:0 -4px 20px rgba(0,0,0,.18);
  padding:6px 6px calc(6px + env(safe-area-inset-bottom,0px));
  justify-content:space-around;align-items:stretch;
}
body.light .mobile-navbar{box-shadow:0 -4px 20px rgba(15,23,42,.06)}
.mobile-navbar-tab{
  flex:1 1 0;min-width:0;max-width:180px;
  display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;
  padding:6px 2px 4px;border:0;background:transparent;color:var(--muted);
  font-family:inherit;font-size:10px;font-weight:600;letter-spacing:.01em;
  cursor:pointer;position:relative;
  border-radius:10px;transition:color .12s,background .12s;
  overflow:hidden;
}
.mobile-navbar-tab-label{
  max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  line-height:1;font-size:10px;font-weight:600;padding:0 2px;
}
@media (max-width:360px){
  .mobile-navbar-tab-label{font-size:9px}
  .mobile-navbar-tab{padding:6px 0 4px}
  .mobile-navbar-tab-ico{width:36px;height:26px}
}
.mobile-navbar-tab:hover{color:var(--text2)}
.mobile-navbar-tab.active{color:var(--accent)}
.mobile-navbar-tab.active .mobile-navbar-tab-ico{
  background:var(--accent-bg);color:var(--accent);
}
.mobile-navbar-tab-ico{
  width:44px;height:28px;border-radius:14px;
  display:flex;align-items:center;justify-content:center;
  transition:background .12s,color .12s;
  position:relative;color:var(--text2);
}
.mobile-navbar-tab.active .mobile-navbar-tab-ico svg{color:var(--accent)}
.mobile-navbar-tab-badge{
  position:absolute;top:-2px;right:6px;min-width:16px;height:16px;
  padding:0 4px;border-radius:9px;background:var(--danger);color:#fff;
  font-size:9px;font-weight:700;display:flex;align-items:center;justify-content:center;
  box-shadow:0 0 0 2px var(--card);line-height:1;
}
.mobile-navbar-tab.active::before{
  content:"";position:absolute;top:0;left:50%;transform:translateX(-50%);
  width:22px;height:3px;border-radius:0 0 3px 3px;background:var(--accent);
}
/* Visible uniquement en portrait mobile */
@media (max-width:900px) and (orientation:portrait){
  .mobile-navbar{display:flex}
  body.has-mobile-navbar{padding-bottom:calc(66px + env(safe-area-inset-bottom,0px))}
  /* FAB Agent IA caché : accès via l'onglet Agent IA de la nav bar. Le panel reste actif.
     Spécificité boostée pour battre mysifa_ai_chat.css (loaded APRES ce style block). */
  html body #ai-chat-root #ai-chat-btn,
  html body[class] #ai-chat-btn{display:none!important}
  #ai-chat-panel{bottom:calc(70px + env(safe-area-inset-bottom,0px))!important;right:8px!important;left:8px!important;width:auto!important;max-width:none!important}
  /* Widget chat_widget : bulle et barre flottantes cachées.
     Spécificité boostée pour battre body.cw-use-bubble #cw-bubble injecté par chat_widget.js?v=11. */
  html body #cw-bubble,html body #cw-bar,
  html body[class] #cw-bubble,html body[class] #cw-bar{display:none!important}
  #cw-panel{bottom:calc(70px + env(safe-area-inset-bottom,0px))!important}
  /* Palette CmdK : overlay ne couvre pas la nav bar (redondance pour être sûr) */
  html body #cmdk-overlay{bottom:calc(66px + env(safe-area-inset-bottom,0px))!important}
  html body #cmdk-overlay .cmdk-modal{max-height:calc(100vh - 66px - env(safe-area-inset-bottom,0px) - 40px)!important}
}
/* Cacher la nav bar sur login */
body.mysifa-hide-navbar .mobile-navbar{display:none!important}

/* ══════════════════════════════════════════════════════════════════
   Bottom sheet profil (menu badge EL)
   ══════════════════════════════════════════════════════════════════ */
.msf-sheet-backdrop{
  position:fixed;inset:0;z-index:500;background:rgba(0,0,0,.45);
  opacity:0;transition:opacity .18s;pointer-events:none;
}
.msf-sheet-backdrop.open{opacity:1;pointer-events:auto}
.msf-sheet{
  position:fixed;left:0;right:0;bottom:0;z-index:501;
  background:var(--card);border-top:1px solid var(--border);
  border-top-left-radius:20px;border-top-right-radius:20px;
  box-shadow:0 -8px 40px rgba(0,0,0,.25);
  padding:8px 0 calc(16px + env(safe-area-inset-bottom,0px));
  transform:translateY(100%);transition:transform .22s cubic-bezier(.4,0,.2,1);
  max-height:88vh;overflow-y:auto;
}
body.light .msf-sheet{box-shadow:0 -8px 40px rgba(15,23,42,.15)}
.msf-sheet.open{transform:translateY(0)}
.msf-sheet-handle{
  width:38px;height:4px;border-radius:2px;background:var(--border);
  margin:6px auto 10px;
}
.msf-sheet-user{
  display:flex;align-items:center;gap:12px;padding:8px 20px 14px;
  border-bottom:1px solid var(--border);margin-bottom:8px;
}
.msf-sheet-user-avatar{
  width:44px;height:44px;border-radius:50%;
  background:var(--accent);color:#fff;
  display:flex;align-items:center;justify-content:center;
  font-size:16px;font-weight:800;letter-spacing:.02em;flex-shrink:0;
}
.msf-sheet-user-info{flex:1;min-width:0}
.msf-sheet-user-name{font-size:15px;font-weight:700;color:var(--text);line-height:1.2}
.msf-sheet-user-role{font-size:12px;color:var(--muted);margin-top:2px;text-transform:capitalize}
.msf-sheet-list{display:flex;flex-direction:column;padding:0 8px}
.msf-sheet-item{
  display:flex;align-items:center;gap:14px;
  padding:14px 14px;border-radius:12px;
  color:var(--text);font-size:15px;font-weight:500;
  background:transparent;border:0;cursor:pointer;text-align:left;
  transition:background .12s;font-family:inherit;
  position:relative;
}
.msf-sheet-item:hover{background:var(--accent-bg)}
.msf-sheet-item-ico{
  width:32px;height:32px;border-radius:10px;
  background:var(--bg);border:1px solid var(--border);
  display:flex;align-items:center;justify-content:center;color:var(--text2);flex-shrink:0;
}
.msf-sheet-item.danger{color:var(--danger)}
.msf-sheet-item.danger .msf-sheet-item-ico{color:var(--danger);border-color:rgba(248,113,113,.3)}
.msf-sheet-item-label{flex:1;min-width:0}
.msf-sheet-item-badge{
  min-width:20px;height:20px;padding:0 6px;border-radius:10px;
  background:var(--danger);color:#fff;font-size:11px;font-weight:700;
  display:flex;align-items:center;justify-content:center;
}
.msf-sheet-sep{height:1px;background:var(--border);margin:6px 12px}


/* ══════════════════════════════════════════════════════════════════
   Google search — modal centré avec backdrop flou
   ══════════════════════════════════════════════════════════════════ */
.gsm-backdrop{
  position:fixed;inset:0;z-index:600;
  background:rgba(8,12,22,0.55);
  backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);
  opacity:0;transition:opacity .16s ease;pointer-events:none;
}
body.light .gsm-backdrop{background:rgba(15,23,42,0.30)}
.gsm-backdrop.open{opacity:1;pointer-events:auto}
.gsm-modal{
  position:fixed;left:50%;top:50%;z-index:601;
  transform:translate(-50%,-50%) scale(.82);
  transform-origin:center center;
  width:min(92vw,520px);
  background:var(--card);border:1px solid var(--border);
  border-radius:18px;
  box-shadow:0 24px 80px rgba(0,0,0,.45),0 0 0 1px rgba(34,211,238,.06);
  opacity:0;pointer-events:none;
  transition:transform .22s cubic-bezier(.22,.61,.36,1),opacity .18s ease;
  padding:22px 20px 18px;
}
body.light .gsm-modal{box-shadow:0 24px 80px rgba(15,23,42,.18)}
.gsm-modal.open{transform:translate(-50%,-50%) scale(1);opacity:1;pointer-events:auto}
.gsm-modal-head{display:flex;align-items:center;gap:12px;margin-bottom:14px}
.gsm-modal-logo{display:flex;align-items:center;justify-content:center;flex-shrink:0}
.gsm-modal-logo svg{width:28px;height:28px}
.gsm-modal-title{
  font-size:15px;font-weight:700;color:var(--text);flex:1;letter-spacing:-.01em;
}
.gsm-modal-close{
  border:0;background:transparent;color:var(--muted);cursor:pointer;
  width:32px;height:32px;border-radius:8px;
  display:flex;align-items:center;justify-content:center;padding:0;
  transition:background .12s,color .12s;flex-shrink:0;
}
.gsm-modal-close:hover{background:var(--accent-bg);color:var(--accent)}
.gsm-input-wrap{
  position:relative;background:var(--bg);border:1.5px solid var(--border);
  border-radius:12px;padding:12px 14px 12px 42px;
  transition:border-color .12s,box-shadow .12s;
}
.gsm-input-wrap:focus-within{border-color:var(--accent);box-shadow:0 0 0 4px var(--accent-bg)}
.gsm-input-search-ico{
  position:absolute;left:14px;top:50%;transform:translateY(-50%);
  width:18px;height:18px;color:var(--muted);pointer-events:none;
  display:flex;align-items:center;justify-content:center;
}
.gsm-input{
  width:100%;background:transparent;border:0;outline:0;
  color:var(--text);font-family:inherit;font-size:15px;
  padding:0;line-height:1.4;
}
.gsm-input::placeholder{color:var(--muted)}
.gsm-hint{
  font-size:11px;color:var(--muted);margin-top:10px;
  display:flex;gap:10px;flex-wrap:wrap;
}
.gsm-hint kbd{
  font-family:ui-monospace,'Cascadia Code',monospace;font-size:10px;font-weight:700;
  background:var(--bg);border:1px solid var(--border);
  border-radius:5px;padding:2px 6px;color:var(--text2);
}
.gsm-recents{margin-top:14px;padding-top:12px;border-top:1px solid var(--border)}
.gsm-recents-label{
  font-size:10px;font-weight:700;color:var(--muted);letter-spacing:.05em;
  text-transform:uppercase;margin-bottom:8px;
}
.gsm-recents-chips{display:flex;flex-wrap:wrap;gap:6px}
.gsm-recent-chip{
  border:1px solid var(--border);background:var(--bg);color:var(--text2);
  border-radius:999px;padding:6px 12px;font-size:12px;font-weight:500;
  cursor:pointer;font-family:inherit;transition:border-color .12s,background .12s,color .12s;
  display:inline-flex;align-items:center;gap:6px;max-width:100%;
}
.gsm-recent-chip:hover{border-color:var(--accent);background:var(--accent-bg);color:var(--accent)}
.gsm-recent-chip-text{
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:180px;
}
.gsm-recent-chip svg{width:11px;height:11px;flex-shrink:0;color:var(--muted)}
.gsm-recent-chip:hover svg{color:var(--accent)}
@media (max-width:480px){
  .gsm-modal{padding:18px 16px 14px;width:min(94vw,520px)}
  .gsm-modal-logo svg{width:24px;height:24px}
  .gsm-modal-title{font-size:14px}
  .gsm-input{font-size:14px}
  .gsm-recent-chip-text{max-width:120px}
}

/* ══════════════════════════════════════════════════════════════════
   Portail mobile — header refondu (logo + Google + badge profil)
   Masque l'ancienne corner-stack + barre de recherche Google + footer texte
   ══════════════════════════════════════════════════════════════════ */
.portal-mobile-header{
  display:none;
  align-items:center;justify-content:space-between;
  width:100%;max-width:min(100%, 320px);
  padding:0;margin:0 auto 8px;
  gap:12px;
}
@media (min-width:520px) and (max-width:900px){
  .portal-mobile-header{max-width:min(100%, 400px)}
}
.portal-mobile-header-brand{
  font-size:26px;font-weight:800;letter-spacing:-1.1px;color:var(--text);line-height:1;
}
.portal-mobile-header-brand span{color:var(--accent)}
.portal-mobile-header-actions{display:flex;align-items:center;gap:10px}
.portal-mobile-google-btn,.portal-mobile-profile-btn{
  border:1px solid var(--border);background:var(--card);
  border-radius:999px;cursor:pointer;
  display:flex;align-items:center;justify-content:center;
  transition:background .12s,border-color .12s;font-family:inherit;color:var(--text);
}
.portal-mobile-google-btn{
  width:38px;height:38px;padding:0;
}
.portal-mobile-google-btn:hover{border-color:var(--accent);background:var(--accent-bg)}
.portal-mobile-google-btn svg{width:20px;height:20px}
.portal-mobile-profile-btn{
  height:38px;padding:0 12px 0 4px;gap:8px;
  font-size:13px;font-weight:600;
}
.portal-mobile-profile-btn:hover{border-color:var(--accent)}
.portal-mobile-profile-avatar{
  position:relative;
  width:30px;height:30px;border-radius:50%;background:var(--accent);color:#fff;
  display:flex;align-items:center;justify-content:center;
  font-size:11px;font-weight:800;letter-spacing:.02em;overflow:visible;
  flex-shrink:0;
}
.portal-mobile-profile-avatar img{
  width:100%;height:100%;border-radius:50%;object-fit:cover;display:block;
}
.portal-mobile-profile-humeur{
  position:absolute;bottom:-3px;right:-3px;
  min-width:16px;height:16px;padding:0 2px;border-radius:8px;
  background:var(--card);border:1.5px solid var(--border);
  display:flex;align-items:center;justify-content:center;
  font-size:11px;line-height:1;box-shadow:0 1px 3px rgba(0,0,0,.15);
}
.portal-mobile-profile-name{max-width:90px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
@media (max-width:900px) and (orientation:portrait){
  .portal-mobile-header{display:flex}
  /* Masquer les anciens éléments remplacés sur portrait mobile uniquement */
  .portal-page > .portal-corner-stack{display:none!important}
  .portal-page > .portal-search{display:none!important}
  .portal-page > .portal-user{display:none!important}
  .portal-page > .portal-logo{display:none!important}
  /* Le portail-page prend juste ce qu'il faut, plus de gaps parasites */
  .portal-page{padding-top:14px;padding-bottom:20px;gap:14px}
  .portal-apps-block{margin-top:4px}
}

</style>
</head>
<body class="__STAGING_BODY_CLASS__">
<div class="staging-bandeau __STAGING_INITIAL_CLASS__" id="msf-staging-bandeau" __STAGING_INITIAL_HIDDEN__>
  <span class="msf-imp-msg" id="msf-staging-msg">__STAGING_INITIAL_MSG__</span>
  <span class="msf-imp-slot" id="msf-impersonate-slot" hidden></span>
</div>
<script>window.__MYSIFA_ENV__="__ENV_NAME_VALUE__";</script>
<script src="/static/mysifa_theme.js"></script>
<script src="/static/mysifa_user_chip.js"></script>
<div id="root"></div>
<div id="mobile-navbar-root" aria-label="Navigation" role="navigation"></div>
<div id="msf-sheet-backdrop" class="msf-sheet-backdrop" aria-hidden="true"></div>
<div id="msf-sheet-root" class="msf-sheet" role="dialog" aria-modal="true" aria-label="Menu profil"></div>
<div id="gsm-backdrop" class="gsm-backdrop" aria-hidden="true"></div>
<div id="gsm-modal" class="gsm-modal" role="dialog" aria-modal="true" aria-label="Recherche Google" aria-hidden="true"></div>
<script src="/static/support_widget.js"></script>
<script src="/static/mysifa_impersonate.js"></script>
<script>window.__MYSIFA_APP__="__INITIAL_APP_VALUE__";</script>
<script src="/static/mysifa_dock.js"></script>
<script src="/static/mysifa_resize.js"></script>
<script src="/static/mysifa_postit.js"></script>
<script src="/static/mysifa_cmdk.js"></script>
<script src="/static/mysifa_calc.js"></script>
<script src="/static/mysifa_expe_carte.js"></script>
<script src="/static/chat_mentions.js"></script>
<script src="/static/chat_widget.js?v=11"></script>
<script src="/static/mysifa_humeur.js"></script>
<script src="/static/chat_widget_v2.js?v=7"></script>
<script src="/static/mysifa_ai_chat.js"></script>
<script src="/static/mysifa_landscape.js?v=2"></script>
<script src="/static/motion.js" defer></script>
<script>
const API=window.location.origin;
const INITIAL_APP="__INITIAL_APP_VALUE__";
const HAS_INITIAL_APP = !!(INITIAL_APP && INITIAL_APP !== "__INITIAL_APP__");
function isAuthMePath(p){
  return p==='/api/auth/me'||p.startsWith('/api/auth/me?');
}
let authEpoch=0;
let _expeHistSearchT=null;
let _expeLastRenderedInnerTab=null;
let _expeJourInflight=null;
let _portalDragSuppressClick=false;

// ── MyExpé : entrée planning (défaut vue expédition) ─────────────────
const EXPE_PLANNING_ENTRY_URL = '/planning?vue=expe';
function renderExpePlanningNav(){
  if(!canPlanningNav(S.user)) return null;
  return h('button',{
    type:'button',
    className:'nav-btn',
    title:'Planning : Expédition',
    onClick:()=>{ location.href=EXPE_PLANNING_ENTRY_URL; }
  }, iconEl('calendar',15), '  Planning');
}

// ── MyExpé : persistance locale (départs) ─────────────────────────
const LS_EXPE_DEPARTS_STATE = 'mysifa.expe.departs.state.v1';
function expeLoadLocalState(){
  try{
    const raw=localStorage.getItem(LS_EXPE_DEPARTS_STATE);
    if(!raw) return;
    const d=JSON.parse(raw);
    if(d && typeof d==='object'){
      if(typeof d.expeDepartJourDate==='string') S.expeDepartJourDate=d.expeDepartJourDate;
      if(d.expeDepartForm && typeof d.expeDepartForm==='object') S.expeDepartForm={...S.expeDepartForm,...d.expeDepartForm};
      if(typeof d.expeDepartModalOpen==='boolean') S.expeDepartModalOpen=d.expeDepartModalOpen;
      if(d.expeDepartEditId!=null) S.expeDepartEditId=d.expeDepartEditId;
    }
  }catch(e){}
}
function expeSaveLocalState(){
  try{
    const payload={
      expeDepartJourDate: S.expeDepartJourDate||'',
      expeDepartForm: S.expeDepartForm||{},
      expeDepartModalOpen: !!S.expeDepartModalOpen,
      expeDepartEditId: S.expeDepartEditId||null
    };
    localStorage.setItem(LS_EXPE_DEPARTS_STATE, JSON.stringify(payload));
  }catch(e){}
}
function expeScheduleSaveLocal(){
  if(window._expeSaveT) clearTimeout(window._expeSaveT);
  window._expeSaveT=setTimeout(()=>{window._expeSaveT=null;expeSaveLocalState();},250);
}
function apiDetailMsg(detail){
  if(!detail) return '';
  if(typeof detail==='string') return detail;
  if(Array.isArray(detail)){
    return detail.map(x=>{
      if(typeof x==='string') return x;
      if(x && typeof x==='object'){
        const loc=Array.isArray(x.loc)?x.loc.filter(p=>p!=='body').join('.'):'';
        return (loc?loc+': ':'')+(x.msg||x.message||JSON.stringify(x));
      }
      return String(x);
    }).join(' · ');
  }
  if(typeof detail==='object') return detail.msg||detail.message||JSON.stringify(detail);
  return String(detail);
}
function escHtml(s){
  return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function escAttr(s){
  return escHtml(s).replace(/'/g,'&#39;');
}

async function api(p,o){
  try{
    const r=await fetch(API+p,{credentials:'include',...o});
    if(r.status===401){
      // Ne pas forcer la déconnexion sur /me : une réponse 401 tardive (requête lancée avant la connexion)
      // écrasait l’état après un login réussi. checkAuth() gère l’absence de session via authEpoch.
      if(!isAuthMePath(p)){S.user=null;S.app='login';render();}
      return null;
    }
    if(!r.ok){const e=await r.json().catch(()=>({}));throw new Error(apiDetailMsg(e.detail)||('Erreur '+r.status));}
    const ct=r.headers.get('content-type')||'';
    let out;
    if(ct.includes('spreadsheet')||ct.includes('octet-stream'))out=await r.blob();
    else out=await r.json();
    if(shouldRefreshAlertsFromApi(p,o))refreshAlertsBadge().catch(()=>{});
    return out;
  }catch(e){if(e.message.includes('Failed to fetch'))throw new Error('API non disponible');throw e;}
}

function getYesterday(){
  const d=new Date();
  d.setDate(d.getDate()-1);
  const yyyy=d.getFullYear();
  const mm=String(d.getMonth()+1).padStart(2,'0'); // mois 01-12
  const dd=String(d.getDate()).padStart(2,'0');    // jour 01-31
  return yyyy+'-'+mm+'-'+dd; // YYYY-MM-DD
}

let S={
  app: HAS_INITIAL_APP ? INITIAL_APP : 'login',
  page:'production',user:null,
  subPage:'kpis',   // 'kpis' | 'saisies' | 'erreurs'
  machineStatus:null,
  importOpen:false,
  selDossier:null,
  loginSubmitting:false,loginError:null,portalLoading:null,
  sidebarOpen:false,
  expeTab:'suivi_departs',
  expeDepartSubTab:'jour',
  expeDept:'59',
  expeKg:'',
  expeNbPal:'',
  expeFuelPct:'12.80',
  expeResults:null,
  expeShowContacts:false,
  expeContacts:null,
  expeRaw:null,
  expeRawLoading:false,
  expeRawError:null,
  expeDepartJourDate:'',
  expeDepartList:[],
  expeDepartLoading:false,
  expeDepartHist:[],
  expeDepartHistQ:'',
  expeDepartHistLoading:false,
  expeDepartHistPage:1,
  expeDepartHistPages:1,
  expeDepartHistTotal:0,
  expeDepartSubmitting:false,
  expeDepartModalOpen:false,
  expeDepartEditId:null,
  expePaletteTypes:[],
  expePaletteTypesLoading:false,
  // Picker dossier dans Ajouter départ
  expeDepartFormTab:'dossier',           // 'dossier' | 'manuel'
  expeDepartDossiers:[],                  // liste renvoyée par /api/expe/dossiers-disponibles
  expeDepartDossiersLoading:false,
  expeDepartDossierQuery:'',
  expeDepartDossierHi:-1,
  // Onglet Gestion palettes Europe
  expePalettesEuropeData:null,
  expePalettesEuropeLoading:false,
  expePalEurSubTab:'suivi',                // 'suivi' | 'recap'
  expePalettesEuropeStatutFilter:'',     // '' | 'en_attente' | 'retournee' | 'perdue'
  expePalettesEuropeClientFilter:'',
  expePalettesEuropeQuery:'',
  expeDepartForm:{
    date_enlevement:'',
    affreteurs:'',
    transporteur:'',
    client:'',
    code_postal_destination:'',
    ref_sifa:'',
    arc:'',
    no_cde_transport:'',
    no_bl:'',
    type_palette_matiere_id:'',
    nb_palette:'',
    poids_total_kg:'',
    date_livraison:'',
    planning_entry_id:'',                 // lien dossier source
    palette_europe:0,                     // 0 ou 1
  },
  comptaTab:'factor',
  comptaFactorMode:'file',
  comptaPasteText:'',
  comptaAcheteurs:[],
  comptaComptes:[],
  comptaResult:null,
  comptaEditAcheteurId:null,
  comptaEditCompteId:null,
  comptaBanques:[],
  comptaEditBanqueId:null,
  stockView:'grille',
  stockProduits:[],stockSelProduit:null,stockSelEmpl:null,
  stockGlobale:null,stockInvPriorites:[],stockSearch:'',stockGrilleFilter:'',stockMvtType:'entree',
  stockPrefillEmpl:null,stockPrefillRef:null,stockPrefillDes:null,stockPrefillUnit:null,
  filters:{},OPS_CONFIG:{},
  fv:{operateurs:[],dossiers:[],dossierSearchQ:'',date_from:getYesterday(),date_to:getYesterday()},
  dossierFilterHi:-1,
  saisiesOffset:0,
  saisiesLimit:200,
  historique:null,production:null,traceabilite:null,
  tracFilters:{ref:'',client:'',machine:'',statut:''},
  tracSort:{col:null,dir:'asc'},
  tracShowAttente:false,
  imports:[],selImp:null,impData:null,
  ofImports:[],ofImportsLoading:false,ofImportModal:null,
  ofSearch:'',ofPage:0,ofTotal:0,ofSubTab:'of',ofSelected:new Set(),ofEditModal:null,
  fiches:[],fichesLoading:false,ficheSearch:'',fichePage:0,ficheTotal:0,ficheSelected:new Set(),ficheEditModal:null,
ofSearch:'',ofPage:0,ofTotal:0,ofSubTab:'of',
ofSelected:new Set(),
fiches:[],fichesLoading:false,ficheSearch:'',fichePage:0,ficheTotal:0,
ficheSelected:new Set(),ficheEditModal:null,
  saisies:null,
  dossiers:[],
  devisList:[],selDevis:null,comparaison:null,devisPreview:null,
  // Rentabilité v2 (planning-based)
  rentList:null,
  rentSelEntryId:null,
  rentLinksById:{}, // { [planning_entry_id]: {devis_id, no_dossiers[]} }
  rentCompById:{},  // { [planning_entry_id]: comparaison }
  rentQuery:'',
  rentTags:[],      // [{kind,value,label}]
  rentOffset:0,
  rentLimit:12,
  toast:null,
  alertsCount:0,
  selectedRows:new Set(),   // ids des lignes sélectionnées
  sortState:{col:null,asc:true}, // tri tableau saisies
  addRowTemplate:null,
  // Messagerie interne (support)
  msgUnread:0,
  msgList:null,
  msgSelId:null,
  msgSelIds:[],
  msgLoading:false,
  msgFilter:'unread',
  contactOpen:false,
  contactSubject:'',
  contactMessage:'',
  contactSending:false,
  expePoidsGram:'155',
  expePoidsCoeff:'1.05',
  expePoidsRows:[{qty:'',laize:'',dev:''},{qty:'',laize:'',dev:''},{qty:'',laize:'',dev:''},{qty:'',laize:'',dev:''}],
  expoPoidsPalNb:'',
  expoPoidsPalKg:'',
  // ── Paie ──
  paieAuth: sessionStorage.getItem('paie_auth_v1')==='1',
  paieEmployes:[],paieEmpSearch:'',paieEmpLoaded:false,
  paieCurrentEmpId:null,
  paieAnnee:new Date().getFullYear(),paieMois:new Date().getMonth()+1,
  paieVarsCache:{},paiePendingFixed:{},paiePendingVar:{},
  paieExporting:false,paieShowHist:false,paieHistData:null,
};
window.S=S;

// Charger la persistance MyExpé (si présent) avant le 1er render.
expeLoadLocalState();

function set(u){
  Object.assign(S,u);
  if('expeDepartJourDate' in u || 'expeDepartForm' in u || 'expeDepartModalOpen' in u || 'expeDepartEditId' in u){
    expeScheduleSaveLocal();
  }
  render();
}
function toast(m,t='success'){set({toast:{message:m,type:t}});setTimeout(()=>set({toast:null}),3500);}
function showToast(message,type){
  const t=type==='danger'?'error':(type==='success'?'success':'success');
  toast(message,t);
}

// Favicon : base = vrai PNG "MyS" (dark ou light selon env) en résolution 192,
// downscalé sur un canvas 64×64 pour un rendu net, avec pastille de comptage.
const __IS_STAGING_FAV=(window.__MYSIFA_ENV__==='v1')||/^v1\./i.test((window.location&&window.location.hostname)||'');
const __FAV_SFX=__IS_STAGING_FAV?'-light':'';
const __FAV_BASE_SRC='/static/mys_icon'+__FAV_SFX+'_192.png';
const __favBaseImg=new Image();
let __favBaseReady=false;
__favBaseImg.onload=function(){__favBaseReady=true;try{refreshAlertsBadge();}catch(e){}};
__favBaseImg.src=__FAV_BASE_SRC;

function updateFaviconBadge(count){
  // Pastille de comptage désactivée (juillet 2026). Le favicon reste celui servi
  // par le <link rel="icon"> du HTML — pas de canvas overlay, pas d'écrasement.
  return;
}

function __drawFavFallback(ctx){
  const bg=__IS_STAGING_FAV?'#f1f5f9':'#0a0e17';
  const fg=__IS_STAGING_FAV?'#0f172a':'#f1f5f9';
  ctx.fillStyle=bg;
  ctx.beginPath();
  if(typeof ctx.roundRect==='function')ctx.roundRect(0,0,64,64,12);
  else ctx.rect(0,0,64,64);
  ctx.fill();
  ctx.fillStyle=fg;
  ctx.font='bold 40px system-ui';
  ctx.textAlign='center';
  ctx.textBaseline='middle';
  ctx.fillText('M',32,34);
}

async function refreshAlertsBadge(){
  try{
    const r=await api('/api/alerts/count');
    if(r&&typeof r.total==='number'){
      S.alertsCount=r.total;
      updateFaviconBadge(r.total);
    }
  }catch(e){}
}

let _alertsBadgeInterval=null;
function startAlertsBadgePolling(){
  refreshAlertsBadge().catch(()=>{});
  if(_alertsBadgeInterval)return;
  _alertsBadgeInterval=setInterval(()=>{refreshAlertsBadge().catch(()=>{});},60000);
}

function shouldRefreshAlertsFromApi(path,opts){
  const m=String((opts&&opts.method)||'GET').toUpperCase();
  if(m==='GET')return false;
  const p=String(path||'');
  if(p.includes('/api/alerts/count'))return false;
  return /\/api\/(messages|expe\/departs|dossiers|planning)/.test(p);
}

function closeSidebar(){if(S.sidebarOpen){S.sidebarOpen=false;render();}}
function toggleSidebar(){S.sidebarOpen=!S.sidebarOpen;render();}

function h(t,a,...c){
  const el=document.createElement(t);
  if(a)Object.entries(a).forEach(([k,v])=>{
    if(k==='className')el.className=v;
    else if(k==='style'&&typeof v==='object')Object.assign(el.style,v);
    else if(k.startsWith('on'))el.addEventListener(k.slice(2).toLowerCase(),v);
    else if(k==='disabled'||k==='checked'||k==='readonly'||k==='selected'){
      if(v)el.setAttribute(k,'');
      else el.removeAttribute(k);
    }else el.setAttribute(k,v);
  });
  c.flat().forEach(c=>{
    if(c==null)return;
    const prim=typeof c==='string'||typeof c==='number'||typeof c==='boolean';
    el.appendChild(prim?document.createTextNode(String(c)):c);
  });
  return el;
}

// ── Icônes SVG (Feather style) ───────────────────────────────────
function icon(name,size=16){
  const a=`width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"`;
  const p={
    'bar-chart-2': '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
    'calendar': '<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>',
    'trending-up': '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>',
    'users': '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    'user': '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    'pencil': '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>',
    'alert-triangle': '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
    'alert-circle': '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>',
    'wrench': '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
    'package': '<line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/>',
    'search': '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
    'sun': '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>',
    'moon': '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>',
    'log-out': '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
    'trash': '<polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>',
    'cloud-upload': '<polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/>',
    'upload': '<polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/>',
    'download': '<polyline points="8 17 12 21 16 17"/><line x1="12" y1="21" x2="12" y2="12"/><path d="M20.88 18.09A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.29"/>',
    'copy': '<rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
    'save': '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>',
    'eye': '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
    'eye-off': '<path d="M17.94 17.94A10.94 10.94 0 0 1 12 20c-7 0-11-8-11-8a19.78 19.78 0 0 1 5.06-5.94"/><path d="M9.9 4.24A10.94 10.94 0 0 1 12 4c7 0 11 8 11 8a19.74 19.74 0 0 1-3.17 4.19"/><path d="M14.12 14.12A3 3 0 1 1 9.88 9.88"/><line x1="1" y1="1" x2="23" y2="23"/>',
    'clock': '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    'folder': '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>',
    'file': '<path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/>',
    'play': '<polygon points="5 3 19 12 5 21 5 3"/>',
    'check-circle': '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
    'x': '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
    'arrow-right': '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>',
    'menu': '<line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/>',
    'home': '<path d="M3 10.5L12 3l9 7.5"/><path d="M5 10v11h14V10"/><path d="M10 21v-6h4v6"/>',
    // Icône enveloppe (plus explicite qu'un simple "carré + trait")
    'mail': '<path d="M4 6h16v12H4z"/><path d="M4 7l8 6 8-6"/><path d="M4 17l6-5"/><path d="M20 17l-6-5"/>',
    'send': '<line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>',
    'plus': '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
    'edit': '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>',
    'rotate-ccw': '<polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-4.5"/>',
    'rotate-cw': '<polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-.49-4.5"/>',
    'lock': '<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    'box': '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>',
    'calculator': '<rect x="6" y="2.5" width="12" height="19" rx="2"/><line x1="8" y1="7" x2="16" y2="7"/><line x1="9" y1="11" x2="10" y2="11"/><line x1="12" y1="11" x2="13" y2="11"/><line x1="15" y1="11" x2="16" y2="11"/><line x1="9" y1="14" x2="10" y2="14"/><line x1="12" y1="14" x2="13" y2="14"/><line x1="15" y1="14" x2="16" y2="14"/><line x1="9" y1="17" x2="10" y2="17"/><line x1="12" y1="17" x2="13" y2="17"/><line x1="15" y1="17" x2="16" y2="17"/>',
    'truck': '<path d="M3 7h11v10H3z"/><path d="M14 10h4l3 3v4h-7z"/><circle cx="7.5" cy="17" r="2"/><circle cx="17.5" cy="17" r="2"/>',
    'sliders': '<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/>',
    'layers': '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
    'arrow-left': '<line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>',
    'printer': '<polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/>',
    'clipboard': '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/>',
    'activity': '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
    'tool': '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
    'credit-card': '<rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/>',
    'file-text': '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>',
    'grid': '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>',
    'tag': '<path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/>',
    'map-pin': '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>',
    'database': '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14a9 3 0 0 0 18 0V5"/><path d="M3 12a9 3 0 0 0 18 0"/>',
    'users': '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    'palette': '<circle cx="13.5" cy="6.5" r=".5" fill="currentColor"/><circle cx="17.5" cy="10.5" r=".5" fill="currentColor"/><circle cx="8.5" cy="7.5" r=".5" fill="currentColor"/><circle cx="6.5" cy="12.5" r=".5" fill="currentColor"/><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z"/>',
    'shield-check': '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/>',
    // Lucide sticky-note — pastille post-it avec coin replié
    'sticky-note': '<path d="M15.5 3H5a2 2 0 0 0-2 2v14c0 1.1.9 2 2 2h14a2 2 0 0 0 2-2V8.5L15.5 3Z"/><path d="M15 3v6h6"/>',
    // Palette bois — vue de côté : deck supérieur + traverse + 3 pieds
    'pallet': '<rect x="2" y="7" width="20" height="3" rx="0.5"/><rect x="2" y="14" width="20" height="3" rx="0.5"/><line x1="5" y1="10" x2="5" y2="14"/><line x1="12" y1="10" x2="12" y2="14"/><line x1="19" y1="10" x2="19" y2="14"/><line x1="5" y1="17" x2="5" y2="20"/><line x1="12" y1="17" x2="12" y2="20"/><line x1="19" y1="17" x2="19" y2="20"/>',
    'chevron-down': '<polyline points="6 9 12 15 18 9"/>',
    'chevron-right': '<polyline points="9 6 15 12 9 18"/>',
    'external': '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>',
    'link': '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
    'globe': '<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>',
  };
  return `<svg ${a} aria-hidden="true" style="display:inline-block;vertical-align:middle;flex-shrink:0">${p[name]||p['alert-circle']}</svg>`;
}
function iconEl(name,size=16){
  const s=document.createElement('span');
  s.style.cssText='display:inline-flex;align-items:center;flex-shrink:0';
  s.innerHTML=icon(name,size);
  return s;
}
function sidebarUserChip(user,opts){
  if(!user)return null;
  opts=opts||{};
  if(window.MySifaUserChip){
    return MySifaUserChip.element(user,h,iconEl,Object.assign({
      title:'Mon profil',
      onClick:()=>{window.location.href='/profil'}
    },opts));
  }
  return h('div',{
    className:opts.chipClass||'user-chip',
    style:{cursor:'pointer'},
    title:'Mon profil',
    onClick:()=>{window.location.href='/profil'}
  },
    h('div',{className:'uc-name'},user.nom||''),
    h('div',{className:'uc-role'},ROLE_LABELS[user.role]||user.role||''),
    h('div',{className:'uc-profil'},iconEl('edit',10),' Mon profil')
  );
}

const fN=n=>n?Number(n).toLocaleString('fr-FR'):'0';
const fD=d=>d?d.replace(/C$/,'').replace('T',' ').slice(0,16):'-';
const fDSecs=d=>{
  if(!d) return '-';
  const s=String(d).replace(/C$/,'').trim().replace('T',' ');
  const fr=s.match(/^(\d{2}\/\d{2}\/\d{4})\s+(\d{2}):(\d{2})(?::(\d{2}))?/);
  if(fr) return fr[1]+' '+fr[2]+':'+fr[3]+':'+(fr[4]!=null?fr[4]:'00');
  const iso=s.match(/^(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})(?::(\d{2}))?/);
  if(iso) return iso[3]+'/'+iso[2]+'/'+iso[1]+' '+iso[4]+':'+iso[5]+':'+(iso[6]!=null?iso[6]:'00');
  return s.slice(0,19);
};
const opName=s=>{if(!s)return'';const p=s.split(' - ');return p.length>1?p.slice(1).join(' - '):s;};
const fMin=m=>{if(!m&&m!==0)return'-';const hh=Math.floor(m/60),mm=Math.round(m%60);return hh>0?hh+'h '+String(mm).padStart(2,'0')+'min':mm+'min';};
const isAdmin=u=>u&&(u.role==='direction'||u.role==='administration'||u.role==='superadmin');
const canViewAllProd=u=>u&&(isAdmin(u)||u.role==='commercial'||u.role==='expedition');
const isComptaPlanning=u=>u&&(u.role==='comptabilite'||u.role==='logistique');
const canPlanningNav=u=>!!(u&&u.app_access&&u.app_access.planning);
const isFab=u=>u&&u.role==='fabrication';

const ROLE_LABELS={direction:'Direction',administration:'Administration',fabrication:'Fabrication',logistique:'Logistique',comptabilite:'Comptabilité',expedition:'Expédition',commercial:'Commercial',superadmin:'Super admin'};
const isCommercial=u=>u&&u.role==='commercial';
const ROLE_BADGE={direction:'badge-direction',administration:'badge-administration',fabrication:'badge-fabrication',logistique:'badge-fabrication',comptabilite:'badge-administration',expedition:'badge-administration',superadmin:'badge-direction'};

// ── Helpers d'initialisation post-auth (factorisés entre checkAuth et doLogin) ──
// Chacun renvoie true si une redirection (window.location.href=…) a été déclenchée
// — l'appelant doit alors return immédiatement pour ne pas continuer à exécuter.
function _handleNextRedirect(){
  try{
    const sp=new URLSearchParams(window.location.search||'');
    const nxt=(sp.get('next')||'').trim();
    if(nxt && nxt.startsWith('/')){
      window.location.href=nxt;
      return true;
    }
  }catch(e){}
  return false;
}
function _handleProdQueryRouting(){
  if(S.app==='prod' && isComptaPlanning(S.user)){window.location.href='/planning';return true;}
  try{
    const sp=new URLSearchParams(window.location.search||'');
    const p=(sp.get('page')||'').trim();
    if(S.app==='prod' && p==='users'){window.location.href='/settings';return true;}
    if(S.app==='prod' && p==='matiere_prix'){window.location.href='/pricing';return true;}
    if(S.app==='prod' && p==='profil'){window.location.href='/profil';return true;}
    const allowed=new Set(['production','suivi','historique','saisies','import','rentabilite','dossiers','traceabilite','of']);
    if(S.app==='prod' && allowed.has(p)) S.page=p;
  }catch(e){}
  return false;
}
async function _loadInitialAppData(){
  if(S.app==='prod'){
    if(isComptaPlanning(S.user)){window.location.href='/planning';return true;}
    await loadFilters();
    await loadProd();
    await loadHist();
    await loadMachineStatus();
    if(S.page==='of' && canAccessOfTab()){
      await loadOfImports();
      if(S.ofSubTab==='fiche') await loadFiches();
    }
  }else if(S.app==='devis'){
    window.location.href='/pricing';
    return true;
  }else if(S.app==='stock'){
    await loadStockGlobale();
    await loadStockProduits();
  }
  return false;
}

// ── Auth ────────────────────────────────────────────────────────
async function checkAuth(){
  const epoch=authEpoch;
  const user=await api('/api/auth/me');
  if(epoch!==authEpoch)return;
  if(user){
    S.user=user;
    try{ MySifaTheme.mergeFromUser(user); }catch(e){}
    S.app=HAS_INITIAL_APP ? INITIAL_APP : 'portal';
    // Garder le badge Messagerie à jour, même sur le portail
    try{ startMessagesPolling(); }catch(e){}
    try{ startAlertsBadgePolling(); }catch(e){}
    try{ checkGlobalUpdates(); }catch(e){}
    // Badge 'Mappings OF à valider' dans la sidebar (admin/direction/superadmin)
    try{ if(canAccessOfTab()) loadPendingOfCount(); }catch(e){}
    // Support : redirection post-login (ex: /?next=/planning)
    if(_handleNextRedirect()) return;
    if(_handleProdQueryRouting()) return;
    if(await _loadInitialAppData()) return;
  }
  else{S.user=null;S.app='login';}
  render();
  if(S.user&&window.MySifaHumeur)requestAnimationFrame(()=>MySifaHumeur.maybeShow(S.user));
}

let _msgPollStarted=false;
let _mstInterval=null;
function isSuperAdmin(u){return !!(u && u.role==='superadmin');}
async function loadMessagesUnread(){
  if(!isSuperAdmin(S.user))return;
  const r=await api('/api/messages/unread-count');
  if(r && typeof r.count==='number') set({msgUnread:r.count});
}
function startMessagesPolling(){
  if(_msgPollStarted)return;
  _msgPollStarted=true;
  loadMessagesUnread().catch(()=>{});
  setInterval(()=>{loadMessagesUnread().catch(()=>{});},30000);
}
function startMachineStatusPolling(){
  if(_mstInterval)return;
  if(!isAdmin(S.user))return;
  loadMachineStatus().catch(()=>{});
  _mstInterval=setInterval(()=>{loadMachineStatus().catch(()=>{});},15000);
}
function stopMachineStatusPolling(){
  if(_mstInterval){clearInterval(_mstInterval);_mstInterval=null;}
}

// ── Popup annonces globales ───────────────────────────────────────────────────
async function checkGlobalUpdates(){
  try{
    const updates=await fetch('/api/updates/pending?scope=global',{credentials:'include'}).then(r=>r.ok?r.json():[]);
    if(!updates||!updates.length)return;
    const overlay=document.createElement('div');
    overlay.className='upd-overlay';
    const ids=updates.map(u=>u.id);
    const bodies=updates.map(u=>`<div class="upd-body">${u.message}</div>`).join('<hr style="border:none;border-top:1px solid var(--border);margin:16px 0">');
    overlay.innerHTML=`<div class="upd-card">
      ${bodies}
      <button class="upd-ok-btn" onclick="
        Promise.all([${ids.join(',')}].map(id=>fetch('/api/updates/'+id+'/acknowledge',{method:'POST',credentials:'include'}))).catch(()=>{});
        this.closest('.upd-overlay').remove();
      ">Compris</button>
    </div>`;
    document.body.appendChild(overlay);
  }catch(e){}
}

async function refreshPortalData(){
  // Rafraîchit les données clés quand on revient sur l'accueil MySifa
  try{
    const u=await api('/api/auth/me');
    if(u) S.user=u;
  }catch(e){}
  try{ await loadMessagesUnread(); }catch(e){}
  render();
}
async function loadMessages(){
  if(!isSuperAdmin(S.user))return;
  set({msgLoading:true});
  const rows=await api('/api/messages?limit=200');
  set({msgList:Array.isArray(rows)?rows:[],msgLoading:false});
}
async function markMessageRead(id){
  if(!id)return;
  await api('/api/messages/'+id+'/mark-read',{method:'POST'});
  await loadMessagesUnread();
  refreshAlertsBadge().catch(()=>{});
  // Optimistic local update
  try{
    const list=(S.msgList||[]).map(m=>m.id===id?({...m,read_at:m.read_at||new Date().toISOString()}):m);
    set({msgList:list});
  }catch(e){}
}
async function deleteMessage(id){
  if(!id)return;
  await api('/api/messages/'+id,{method:'DELETE'});
  await loadMessagesUnread();
  await loadMessages();
  if(S.msgSelId===id)set({msgSelId:null});
}
async function markAllRead(){
  await api('/api/messages/mark-all-read',{method:'POST'});
  await loadMessagesUnread();
  await loadMessages();
}
async function sendContact(){
  if(S.contactSending)return;
  const subj=(S.contactSubject||'').trim();
  const msg=(S.contactMessage||'').trim();
  if(!msg){toast('Message obligatoire','error');return;}
  set({contactSending:true});
  try{
    await api('/api/messages/contact',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({subject:subj,message:msg})});
    refreshAlertsBadge().catch(()=>{});
    toast('Message envoyé au support');
    set({contactOpen:false,contactSubject:'',contactMessage:'',contactSending:false});
  }catch(e){
    set({contactSending:false});
    toast('Envoi impossible','error');
  }
}
async function doLogin(email,password){
  if(S.loginSubmitting)return;
  S.loginError=null;
  S.loginSubmitting=true;
  render();
  try{
    const r=await api('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,password})});
    if(!r||!r.user){
      S.loginSubmitting=false;
      if(r&&!r.user)S.loginError='Réponse serveur invalide';
      render();
      return;
    }
    authEpoch++;
    // Profil complet : la réponse login ne contient pas tous les champs (adresse, date_naissance).
    try{
      const me=await api('/api/auth/me');
      S.user=me||r.user;
    }catch(e){
      S.user=r.user;
    }
    S.app=HAS_INITIAL_APP ? INITIAL_APP : 'portal';
    // Support : redirection post-login (ex: /?next=/planning)
    if(_handleNextRedirect()) return;
    if(_handleProdQueryRouting()) return;
    S.loginError=null;
    S.fv={
      operateurs:[],
      dossiers:[],
      machines:[],
      date_from:getYesterday(),
      date_to:getYesterday(),
    };
    S.historique=null;
    S.production=null;
    S.traceabilite=null;
    S.saisies=null;
    S.selectedRows=new Set();
    S.sortState={col:null,asc:true};
    // Déverrouiller tout de suite — avant loadFilters/loadHist (sinon bouton « Connexion… » bloqué le temps des APIs)
    S.loginSubmitting=false;
    try{ MySifaTheme.mergeFromUser(S.user); }catch(e){}
    render();
    if(S.user&&window.MySifaHumeur)requestAnimationFrame(()=>MySifaHumeur.maybeShow(S.user));
    checkGlobalUpdates().catch(()=>{});
    if(await _loadInitialAppData()) return;
    render();
  }catch(e){
    S.loginError=e.message||'Erreur de connexion';
    S.loginSubmitting=false;
    render();
  }
}
async function doLogout(){
  authEpoch++;
  await api('/api/auth/logout',{method:'POST'});
  try{ if(typeof clearPostitsUi==='function') clearPostitsUi(); }catch(e){}
  try{ MySifaTheme.applyDefault(); }catch(e){}
  S.user=null;S.app='login';S.historique=null;S.production=null;S.traceabilite=null;
  S.tracFilters={ref:'',client:'',machine:'',statut:''};S.tracSort={col:null,dir:'asc'};
  S.stockGlobale=null;S.stockInvPriorites=[];S.stockProduits=[];S.stockSelProduit=null;S.stockSelEmpl=null;
  S.stockPrefillEmpl=null;S.stockPrefillRef=null;S.stockPrefillDes=null;S.stockPrefillUnit=null;
  S.loginSubmitting=false;S.loginError=null;S.portalLoading=null;
  render();
}

async function loadStockProduits(q=''){
  const url='/api/stock/produits'+(q?'?q='+encodeURIComponent(q):'');
  const d=await api(url);
  if(d)set({stockProduits:d});
}
function stockActor(m){
  if(!m)return'—';
  const n=m.created_by_nom;
  if(n&&String(n).trim())return String(n).trim();
  return m.created_by||'—';
}
async function loadStockGlobale(){
  try{
    const [d,inv]=await Promise.all([
      api('/api/stock/vue-globale'),
      api('/api/stock/inventaire/priorites').catch(()=>[])
    ]);
    if(d)set({stockGlobale:d,stockInvPriorites:Array.isArray(inv)?inv:[]});
  }catch(e){
    console.warn('loadStockGlobale',e.message);
    set({stockGlobale:{grille:[],stats:{nb_refs:0,nb_empl:0,total_unites:0},derniers_mouvements:[]},stockInvPriorites:[]});
  }
}
async function loadStockProduit(id){
  const d=await api('/api/stock/produits/'+encodeURIComponent(id));
  if(d)set({stockSelProduit:d});
}
async function loadStockEmplacement(empl){
  try{hideStockAddEmplDropdown();}catch(e){}
  const d=await api('/api/stock/emplacements/'+encodeURIComponent(empl));
  if(d)set({stockSelEmpl:d,stockView:'emplacement'});
}

async function createProduit(body){
  try{
    const empl=String(body.emplacement||'').trim().toUpperCase();
    const qRaw=body.quantite_emplacement;
    if(!empl||!isStockEmplacementCode(empl)){toast('Emplacement obligatoire (ex. A121)','error');return;}
    const q=(qRaw!=null&&String(qRaw).trim()!==''&&!Number.isNaN(Number(String(qRaw).replace(',','.'))))
      ?Number(String(qRaw).replace(',','.')):NaN;
    if(Number.isNaN(q)||q<=0){toast('Quantité obligatoire (nombre > 0)','error');return;}
    const apiBody={reference:body.reference,designation:body.designation,unite:body.unite||'unité',quantite:q};
    const r=await api('/api/stock/produits',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(apiBody)});
    if(!r||r.id==null)return;
    await api('/api/stock/mouvement',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify({
        produit_id:r.id,emplacement:empl,type_mouvement:'entree',quantite:q,note:''
      })});
    const msg=(r.existing?'Référence déjà en base — entrée de stock':'Produit créé')+' — '+fN(q)+' '+apiBody.unite+' en '+empl;
    toast(msg);await loadStockProduits();await loadStockGlobale();
  }catch(e){toast(e.message,'error');}
}

async function doMouvement(body){
  try{
    const r=await api('/api/stock/mouvement',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!r)return;
    toast('Stock mis à jour — Avant: '+r.quantite_avant+' → Après: '+r.quantite_apres);
    await loadStockGlobale();
    if(S.stockView==='produit'&&S.stockSelProduit) await loadStockProduit(S.stockSelProduit.produit.id);
    else if(S.stockView==='emplacement'&&S.stockSelEmpl) await loadStockEmplacement(S.stockSelEmpl.emplacement);
  }catch(e){toast(e.message,'error');}
}

/** Inventaire ciblé depuis le tableau de bord (une case = emplacement, une réf. = produit). */
async function openInventaireCibleModal(cible){
  try{
    const prev = document.querySelector('.stock-inv-cible-modal');
    if(prev) prev.remove();
  }catch(e){}
  const wrap=document.createElement('div');
  wrap.className='add-row-modal stock-inv-cible-modal';
  wrap.addEventListener('click',e=>{if(e.target===wrap)wrap.remove();});

  const box=document.createElement('div');
  box.className='add-row-form';
  box.style.maxWidth='640px';
  const title=document.createElement('h3');
  const noteI=document.createElement('input');
  noteI.type='text';
  noteI.placeholder='Note (optionnel)';
  noteI.style.width='100%';
  noteI.style.marginBottom='12px';

  let rows=[];
  let subtitle='';
  try{
    if(cible.type==='empl'){
      title.textContent='Inventaire — emplacement '+cible.code;
      const d=await api('/api/stock/emplacements/'+encodeURIComponent(cible.code));
      if(!d){wrap.remove();return;}
      rows=(d.refs||[]).map(r=>({
        produit_id:r.id,
        ref:r.reference,
        des:r.designation||'',
        unite:r.unite||'',
        empl:cible.code,
        sys:Number(r.quantite)||0,
      }));
      subtitle=rows.length?('Comptage pour '+rows.length+' référence(s) en '+cible.code+'.'):('Aucun lot actif en '+cible.code+'.');
    }else{
      title.textContent='Inventaire — réf. '+cible.reference;
      const plist=await api('/api/stock/produits?q='+encodeURIComponent(cible.reference)+'&limit=8');
      if(!plist||!plist.length){toast('Produit introuvable','error');wrap.remove();return;}
      const ru=cible.reference.toUpperCase();
      let p=plist.find(x=>String(x.reference||'').toUpperCase()===ru)||plist[0];
      const detail=await api('/api/stock/produits/'+encodeURIComponent(p.id));
      if(!detail){toast('Fiche produit introuvable','error');wrap.remove();return;}
      rows=(detail.emplacements||[]).map(e=>({
        produit_id:p.id,
        ref:p.reference,
        des:detail.produit&&detail.produit.designation||'',
        unite:detail.produit&&detail.produit.unite||'',
        empl:e.emplacement,
        sys:Number(e.quantite)||0,
      }));
      subtitle=rows.length?('Comptage sur '+rows.length+' emplacement(s) pour '+p.reference+'.'):('Aucun stock actif pour cette référence.');
    }
  }catch(e){
    toast(e.message||'Erreur','error');
    wrap.remove();
    return;
  }

  const sub=document.createElement('p');
  sub.style.fontSize='12px';
  sub.style.color='var(--muted)';
  sub.style.marginBottom='14px';
  sub.textContent=subtitle;

  const tbl=document.createElement('div');
  tbl.style.maxHeight='320px';
  tbl.style.overflowY='auto';
  tbl.style.marginBottom='16px';
  tbl.style.border='1px solid var(--border)';
  tbl.style.borderRadius='10px';

  const inputs=[];
  if(rows.length===0){
    tbl.appendChild(document.createTextNode(''));
  }else{
    const table=document.createElement('table');
    table.style.width='100%';
    table.style.borderCollapse='collapse';
    table.style.fontSize='12px';
    const thead=document.createElement('thead');
    const hr=document.createElement('tr');
    if(cible.type==='empl'){
      ['Référence','Désignation','Qté système','Qté comptée'].forEach(l=>{
        const th=document.createElement('th');
        th.textContent=l;
        th.style.textAlign='left';
        th.style.padding='8px 10px';
        th.style.borderBottom='1px solid var(--border)';
        th.style.color='var(--accent)';
        hr.appendChild(th);
      });
    }else{
      ['Emplacement','Qté système','Qté comptée'].forEach(l=>{
        const th=document.createElement('th');
        th.textContent=l;
        th.style.textAlign='left';
        th.style.padding='8px 10px';
        th.style.borderBottom='1px solid var(--border)';
        th.style.color='var(--accent)';
        hr.appendChild(th);
      });
    }
    thead.appendChild(hr);
    table.appendChild(thead);
    const tb=document.createElement('tbody');
    rows.forEach((R)=>{
      const tr=document.createElement('tr');
      if(cible.type==='empl'){
        const td1=document.createElement('td');
        td1.style.padding='8px 10px';
        td1.style.fontFamily='monospace';
        td1.style.fontWeight='700';
        td1.textContent=R.ref;
        tr.appendChild(td1);
        const td2=document.createElement('td');
        td2.style.padding='8px 10px';
        td2.style.color='var(--text2)';
        td2.textContent=R.des;
        tr.appendChild(td2);
      }else{
        const td0=document.createElement('td');
        td0.style.padding='8px 10px';
        td0.style.fontFamily='monospace';
        td0.style.fontWeight='700';
        td0.textContent=R.empl;
        tr.appendChild(td0);
      }
      const tdSys=document.createElement('td');
      tdSys.style.padding='8px 10px';
      tdSys.style.fontFamily='monospace';
      tdSys.textContent=String(R.sys)+' '+R.unite;
      tr.appendChild(tdSys);
      const tdIn=document.createElement('td');
      tdIn.style.padding='6px 10px';
      const inp=document.createElement('input');
      inp.type='number';
      inp.min='0';
      inp.step='any';
      inp.placeholder=String(R.sys);
      inp.value=String(R.sys);
      inp.style.width='100%';
      inp.style.maxWidth='120px';
      inp.dataset.produitId=String(R.produit_id);
      inp.dataset.emplacement=R.empl;
      inputs.push(inp);
      tdIn.appendChild(inp);
      tr.appendChild(tdIn);
      tb.appendChild(tr);
    });
    table.appendChild(tb);
    tbl.appendChild(table);
  }

  const actions=document.createElement('div');
  actions.className='form-actions';
  actions.style.marginTop='8px';
  const btnAnn=document.createElement('button');
  btnAnn.className='btn-ghost';
  btnAnn.textContent='Annuler';
  btnAnn.onclick=()=>wrap.remove();
  const btnOk=document.createElement('button');
  btnOk.className='btn-sm';
  btnOk.textContent='Valider inventaire';
  if(rows.length===0)btnOk.setAttribute('disabled','');
  btnOk.onclick=async()=>{
    const noteFin=(noteI.value||'').trim()||'Inventaire ciblé (tableau de bord)';
    const lignes=[];
    inputs.forEach(inp=>{
      const raw=String(inp.value||'').replace(',','.');
      if(raw===''||raw===null)return;
      const q=parseFloat(raw);
      if(!isFinite(q)||q<=0)return;
      lignes.push({
        produit_id:parseInt(inp.dataset.produitId,10),
        emplacement:inp.dataset.emplacement,
        quantite:q,
      });
    });
    if(!lignes.length){
      toast('Indiquez au moins une quantité comptée (> 0)','warn');
      return;
    }
    btnOk.disabled=true;
    let ok=0;
    try{
      for(const L of lignes){
        const r=await api('/api/stock/mouvement',{
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body:JSON.stringify({
            produit_id:L.produit_id,
            emplacement:L.emplacement,
            type_mouvement:'inventaire',
            quantite:L.quantite,
            note:noteFin,
          }),
        });
        if(r)ok++;
      }
      toast(ok+' ligne(s) d’inventaire enregistrée(s)');
      wrap.remove();
      await loadStockGlobale();
      render();
    }catch(e){
      toast(e.message||'Erreur','error');
    }finally{
      btnOk.disabled=false;
    }
  };
  actions.appendChild(btnAnn);
  actions.appendChild(btnOk);

  box.appendChild(title);
  box.appendChild(sub);
  box.appendChild(noteI);
  box.appendChild(tbl);
  box.appendChild(actions);
  wrap.appendChild(box);
  document.body.appendChild(wrap);
}

// ── Barre de recherche MyStock (texte + micro + caméra ZXing) ────────────────
let stockSearchState = {
  query: '',
  listening: false,
  scanning: false,
  suggestionProduits: [],
  suggestionEmplacements: [],
  cameraStream: null,
  barcodeReader: null,
};
let stockGrilleFilterTimer = null;
let stockSearchCaret = [0, 0];

const STOCK_EMPLACEMENTS = ['A121','A122','A123','B121','B122','B123','C121','C122','C123'];
function stockIconSvg(kind){
  const common = `fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"`;
  if(kind==='dictaphone'){
    // Micro “outline” (proche du visuel fourni)
    return `<svg viewBox="0 0 24 24" aria-hidden="true"><path ${common} d="M12 14a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v5a3 3 0 0 0 3 3z"/><path ${common} d="M19 11a7 7 0 0 1-14 0"/><path ${common} d="M12 18v3"/><path ${common} d="M8 21h8"/></svg>`;
  }
  if(kind==='camera'){
    // Caméra “outline” arrondie (proche du visuel fourni)
    return `<svg viewBox="0 0 24 24" aria-hidden="true"><path ${common} d="M20 18a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3V9a3 3 0 0 1 3-3h1.2a2 2 0 0 0 1.6-.8l.6-.8A2 2 0 0 1 12.9 4h2.2a2 2 0 0 1 1.5.7l.6.7a2 2 0 0 0 1.6.8H17a3 3 0 0 1 3 3z"/><circle cx="12" cy="13" r="3.5" ${common}/><path ${common} d="M17.5 9.5h.01"/></svg>`;
  }
  if(kind==='record'){
    return `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="5.5" fill="currentColor"/></svg>`;
  }
  return '';
}
/** Emplacements ajoutés côté navigateur (localStorage — non synchronisés avec le serveur). */
const LS_STOCK_EMPL_CUSTOM='mysifa_stock_empl_custom';
function loadStockEmplCustom(){
  try{
    const j=localStorage.getItem(LS_STOCK_EMPL_CUSTOM);
    const a=j?JSON.parse(j):[];
    if(!Array.isArray(a))return [];
    return [...new Set(a.map(x=>String(x||'').trim().toUpperCase()).filter(Boolean))];
  }catch(e){return [];}
}
function saveStockEmplCustom(arr){
  try{localStorage.setItem(LS_STOCK_EMPL_CUSTOM,JSON.stringify([...new Set(arr)]));}catch(e){}
}
function addCustomStockEmplacement(code){
  const t=String(code||'').trim().toUpperCase();
  if(!isStockEmplacementCode(t))return false;
  const cur=loadStockEmplCustom();
  if(cur.includes(t))return false;
  cur.push(t);saveStockEmplCustom(cur);return true;
}
function allStockEmplacementChoices(){
  return [...new Set([...STOCK_EMPLACEMENTS,...loadStockEmplCustom()])].sort();
}
/** Fusionne les emplacements locaux (ex. Z123) avec la réponse /api/stock/search. */
function mergeCustomEmplIntoSearch(apiEmpl, cleaned) {
  const qu = String(cleaned || '').trim().toUpperCase();
  const base = apiEmpl || [];
  if (!qu) return base.slice();
  const have = new Set(base.map(e => String(e.emplacement || '').toUpperCase()));
  const out = base.slice();
  for (const c of loadStockEmplCustom()) {
    const cu = String(c || '').trim().toUpperCase();
    if (!cu || have.has(cu)) continue;
    if (cu.includes(qu) || qu.includes(cu)) {
      out.push({ emplacement: cu, nb_refs: 0, total_unites: 0 });
      have.add(cu);
    }
  }
  return out.sort((a, b) => String(a.emplacement).localeCompare(String(b.emplacement), 'fr'));
}
function stockBoardRefMatches(i, f) {
  if (!f) return true;
  const u = f.toUpperCase();
  return String(i.reference || '').toUpperCase().includes(u) ||
    String(i.designation || '').toUpperCase().includes(u);
}
function stockBoardEmplVisible(empl, items, f) {
  if (!f) return true;
  const u = f.toUpperCase();
  if (String(empl).toUpperCase().includes(u)) return true;
  return items.some(i => stockBoardRefMatches(i, f));
}
function stockBoardItemsForCell(empl, items, f) {
  if (!f) return items;
  const u = f.toUpperCase();
  if (String(empl).toUpperCase().includes(u)) return items;
  return items.filter(i => stockBoardRefMatches(i, f));
}
function scheduleGrilleFilterFromSearch() {
  if (S.stockView !== 'grille') return;
  const el = document.getElementById('stock-search-input');
  if (el && typeof el.selectionStart === 'number') {
    stockSearchCaret = [el.selectionStart, el.selectionEnd];
  }
  clearTimeout(stockGrilleFilterTimer);
  stockGrilleFilterTimer = setTimeout(() => {
    const raw = String(stockSearchState.query || '').trim();
    const v = raw.length >= 2 ? raw.toUpperCase() : '';
    set({ stockGrilleFilter: v });
    requestAnimationFrame(() => {
      const ne = document.getElementById('stock-search-input');
      if (!ne) return;
      try {
        const a = Math.min(stockSearchCaret[0] != null ? stockSearchCaret[0] : 0, ne.value.length);
        const b = Math.min(stockSearchCaret[1] != null ? stockSearchCaret[1] : a, ne.value.length);
        ne.focus();
        ne.setSelectionRange(a, b);
      } catch (e) {}
    });
  }, 200);
}
/** Même règle que l’API : 1 lettre + chiffres (ex. A121, Z999). */
function isStockEmplacementCode(s){
  const t=String(s||'').trim().toUpperCase();
  if(t.length<2)return false;
  const c0=t.charCodeAt(0);
  if(c0<65||c0>90)return false;
  for(let i=1;i<t.length;i++){
    const c=t.charCodeAt(i);
    if(c<48||c>57)return false;
  }
  return true;
}
/** Corrige la reco vocale FR (ex. « à 212 » → A212) et resserre lettre + chiffres. */
function stockNormalizeVoiceTranscript(raw){
  if(raw==null)return '';
  let s=String(raw).trim();
  if(!s)return '';
  s=s.normalize('NFD').replace(/\p{M}+/gu,'');
  s=s.replace(/\s+/g,' ');
  s=s.replace(/\b(?:a|ah|ha|as)\s+(\d{2,4})\b/gi,'A$1');
  s=s.replace(/\b([a-z])\s+(\d{2,4})\b/gi,(_,L,d)=>L.toUpperCase()+d);
  s=s.replace(/\b([A-Z])\s+(\d{2,4})\b/g,'$1$2');
  return s.trim();
}
function stockVoiceSilenceStop(recog,ms){
  const gap=ms||3800;
  let iv=null,touched=Date.now();
  const touch=()=>{touched=Date.now();};
  const clearIv=()=>{if(iv){clearInterval(iv);iv=null;}};
  const start=()=>{
    touch();
    clearIv();
    iv=setInterval(()=>{
      if(Date.now()-touched>=gap){
        clearIv();
        try{recog&&recog.stop();}catch(e){}
      }
    },350);
  };
  const stop=()=>{clearIv();};
  return {start,stop,touch};
}
async function stockResolveVoiceSearchBestQuery(raw){
  const cand=tryStockVoiceCandidates(raw);
  for(const q of cand){
    if(q.length<1)continue;
    try{
      const r=await api('/api/stock/search?q='+encodeURIComponent(q)+'&limit=14');
      const empls=r&&r.emplacements||[];
      const prods=r&&r.produits||[];
      if(empls.length||prods.length){
        const compact=q.replace(/\s+/g,'').toUpperCase();
        if(/^[A-Z]\d{2,4}$/.test(compact)){
          const ex=empls.find(e=>String(e.emplacement||'').replace(/\s+/g,'').toUpperCase()===compact);
          if(ex)return{q:ex.emplacement,r};
        }
        return{q,r};
      }
    }catch(e){}
  }
  return{q:cand[0]||String(raw||'').trim(),r:null};
}
function tryStockVoiceCandidates(raw){
  const base=String(raw||'').trim();
  const norm=stockNormalizeVoiceTranscript(base);
  const list=[];
  const add=x=>{const t=String(x||'').trim();if(t&&!list.includes(t))list.push(t);};
  add(norm);
  add(base);
  const cu=base.replace(/\s+/g,'').toUpperCase();
  const nu=norm.replace(/\s+/g,'').toUpperCase();
  if(cu)add(cu);
  if(nu&&nu!==cu)add(nu);
  return list;
}
function hideStockAddEmplDropdown(){
  const list=document.getElementById('stock-add-empl-suggestions');
  if(list)list.style.display='none';
}
function refreshStockAddEmplDropdownInner(){
  const input=document.getElementById('stock-add-empl-input');
  const list=document.getElementById('stock-add-empl-suggestions');
  if(!input||!list)return;
  const q=String(input.value||'').trim().toUpperCase();
  const all=allStockEmplacementChoices();
  let filtered=q?all.filter(c=>c.startsWith(q)):all.slice();
  filtered=filtered.slice(0,24);
  list.innerHTML='';
  filtered.forEach(code=>{
    const row=document.createElement('div');
    row.className='search-suggestion-item';
    row.textContent=code;
    row.addEventListener('mousedown',e=>{e.preventDefault();input.value=code;hideStockAddEmplDropdown();});
    list.appendChild(row);
  });
  const addRow=document.createElement('div');
  addRow.className='stock-empl-suggest-add';
  addRow.textContent='+ Ajouter emplacement';
  addRow.addEventListener('mousedown',e=>{
    e.preventDefault();
    const raw=String(input.value||'').trim().toUpperCase();
    if(!isStockEmplacementCode(raw)){toast('Format invalide : une lettre puis des chiffres (ex. Z999)','error');return;}
    if(addCustomStockEmplacement(raw))toast('Emplacement ajouté : '+raw);
    else toast('Emplacement déjà dans la liste','warn');
    input.value=raw;
    hideStockAddEmplDropdown();
    refreshStockAddEmplDropdownInner();
  });
  list.appendChild(addRow);
}
function wireStockAddEmplCombo(){
  const input=document.getElementById('stock-add-empl-input');
  if(!input||input.dataset.wired==='1')return;
  input.dataset.wired='1';
  const list=document.getElementById('stock-add-empl-suggestions');
  input.addEventListener('focus',()=>{if(list){list.style.display='block';refreshStockAddEmplDropdownInner();}});
  input.addEventListener('input',()=>{if(list){list.style.display='block';refreshStockAddEmplDropdownInner();}});
  input.addEventListener('blur',()=>{setTimeout(hideStockAddEmplDropdown,200);});
}

function stockVoiceFullTranscript(results) {
  let t = '';
  for (let i = 0; i < results.length; i++) t += results[i][0].transcript;
  return t;
}

function startVoiceSearch() {
  // HTTPS requis pour le micro
  if (location.protocol !== 'https:') {
    toast('Le micro nécessite HTTPS (mysifa.com)', 'warn');
    return;
  }
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    toast('Reconnaissance vocale non supportée — utilisez Chrome ou Safari', 'error');
    return;
  }
  if (!document.getElementById('stock-search-input')) renderStockSearchBar();
  if (!document.getElementById('stock-search-input')) return;

  if (window.__mysifaStockRecog) {
    try { window.__mysifaStockRecog.stop(); } catch (e) {}
    window.__mysifaStockRecog = null;
  }

  const recog = new SpeechRecognition();
  window.__mysifaStockRecog = recog;
  recog.lang = 'fr-FR';
  recog.interimResults = true;
  recog.maxAlternatives = 1;

  const silence = stockVoiceSilenceStop(recog, 3800);

  stockSearchState.listening = true;
  renderStockSearchBar();

  recog.onresult = (e) => {
    silence.touch();
    const transcript = stockVoiceFullTranscript(e.results);
    const fixed = stockNormalizeVoiceTranscript(transcript);
    const field = document.getElementById('stock-search-input');
    const show = fixed || transcript;
    if (field) field.value = show;
    stockSearchState.query = show;
    let hasFinal = false;
    for (let i = e.resultIndex; i < e.results.length; i++) {
      if (e.results[i].isFinal) { hasFinal = true; break; }
    }
    if (hasFinal) {
      (async () => {
        const { q } = await stockResolveVoiceSearchBestQuery(transcript);
        const f = document.getElementById('stock-search-input');
        if (f) f.value = q;
        stockSearchState.query = q;
        doStockSearch(q.trim());
      })();
    }
  };
  recog.onerror = () => { silence.stop(); window.__mysifaStockRecog = null; stockSearchState.listening = false; renderStockSearchBar(); };
  recog.onend = () => { silence.stop(); window.__mysifaStockRecog = null; stockSearchState.listening = false; renderStockSearchBar(); };
  recog.onstart = () => { silence.start(); };
  recog.start();
}

async function loadZXing() {
  return new Promise((resolve, reject) => {
    if (typeof ZXing !== 'undefined') { resolve(); return; }
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/@zxing/library@0.19.1/umd/index.min.js';
    script.onload = resolve;
    script.onerror = reject;
    document.head.appendChild(script);
  });
}

async function startCameraSearch() {
  if (stockSearchState.scanning) return;
  if (!navigator.mediaDevices?.getUserMedia) { toast('Caméra non disponible (page non HTTPS ?)', 'error'); return; }

  stockSearchState.scanning = true;
  renderStockSearchBar();

  // ── Construction de l'overlay (synchrone, geste utilisateur encore actif) ──
  const modal = document.createElement('div');
  modal.className = 'camera-modal';
  const videoWrap = document.createElement('div');
  videoWrap.className = 'camera-video-wrap';
  const video = document.createElement('video');
  video.className = 'camera-video';
  video.autoplay = true;
  video.playsInline = true;
  const overlay = document.createElement('div');
  overlay.className = 'camera-overlay';
  const frame = document.createElement('div');
  frame.className = 'camera-frame';
  overlay.appendChild(frame);
  videoWrap.appendChild(video);
  videoWrap.appendChild(overlay);
  const hint = document.createElement('p');
  hint.className = 'camera-hint';
  hint.textContent = 'Pointez la caméra vers un code — emplacement (A121) ou référence produit';
  const resultEl = document.createElement('div');
  resultEl.className = 'camera-result';
  resultEl.textContent = 'En attente de scan...';
  const closeBtn = document.createElement('button');
  closeBtn.className = 'camera-close';
  closeBtn.textContent = '✕ Fermer';
  closeBtn.onclick = () => stopCamera(modal);
  modal.appendChild(videoWrap);
  modal.appendChild(hint);
  modal.appendChild(resultEl);
  modal.appendChild(closeBtn);
  document.body.appendChild(modal);

  try {
    // getUserMedia en PREMIER (avant tout await long) — Android exige que la demande
    // de permission intervienne dans le même tick que le geste utilisateur
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
    stockSearchState.cameraStream = stream;
    video.srcObject = stream;

    // ── Latence 1,5s — évite les scans parasites au démarrage ──────────────────
    const SCAN_DELAY_MS = 1500;
    const scanStartTime = Date.now();
    resultEl.textContent = 'Positionnez-vous devant le code…';
    setTimeout(() => { if (stockSearchState.scanning) resultEl.textContent = 'En attente…'; }, SCAN_DELAY_MS);

    let detected = false;
    const onCode = (text) => {
      if (Date.now() - scanStartTime < SCAN_DELAY_MS) return;
      if (detected) return;
      detected = true;
      stockSearchState.scanning = false;
      if (stockSearchState.barcodeReader) { try { stockSearchState.barcodeReader.reset(); } catch(e) {} stockSearchState.barcodeReader = null; }
      if (stockSearchState.cameraStream) { stockSearchState.cameraStream.getTracks().forEach(t => t.stop()); stockSearchState.cameraStream = null; }
      resultEl.textContent = '✅ ' + text.trim().toUpperCase();
      resultEl.style.color = 'var(--success)';
      setTimeout(() => { modal.remove(); renderStockSearchBar(); handleBarcodeResult(text); }, 600);
    };

    // ── Chargement ZXing (nécessaire sur iOS et pour QR sur Android) ─────────
    if (typeof ZXing === 'undefined') {
      resultEl.textContent = 'Chargement scanner…';
      await new Promise((res, rej) => {
        const s = document.createElement('script');
        s.src = 'https://cdn.jsdelivr.net/npm/@zxing/library@0.19.1/umd/index.min.js';
        s.onload = res; s.onerror = rej; document.head.appendChild(s);
      });
      if (stockSearchState.scanning) resultEl.textContent = 'Positionnez-vous devant le code…';
    }

    const isAndroidDev = /Android/.test(navigator.userAgent);
    const useNativeDetector = isAndroidDev && ('BarcodeDetector' in window);

    if (useNativeDetector) {
      // ── Android : BarcodeDetector (codes 1D) + ZXing decodeFromStream (QR) ──
      const qrHints = new Map();
      qrHints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS, [ZXing.BarcodeFormat.QR_CODE]);
      qrHints.set(ZXing.DecodeHintType.TRY_HARDER, true);
      const qrReader = new ZXing.BrowserMultiFormatReader(qrHints);
      stockSearchState.barcodeReader = qrReader;

      const detector = new BarcodeDetector({ formats: ['code_128','ean_13','ean_8','data_matrix','code_39','upc_a','upc_e'] });
      const barcodeLoop = async () => {
        if (!stockSearchState.scanning) return;
        if (video.readyState < 2 || !video.videoWidth) { setTimeout(barcodeLoop, 100); return; }
        try { const found = await detector.detect(video); if (found.length > 0) { onCode(found[0].rawValue); return; } } catch(e) {}
        if (stockSearchState.scanning) setTimeout(barcodeLoop, 150);
      };
      setTimeout(barcodeLoop, 500);
      qrReader.decodeFromStream(stream, video, (result) => { if (result) onCode(result.getText()); });

    } else {
      // ── iOS + fallback : ZXing canvas loop tous formats ──────────────────────
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d', { willReadFrequently: true });
      const hints = new Map();
      hints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS, [ZXing.BarcodeFormat.CODE_128, ZXing.BarcodeFormat.EAN_13, ZXing.BarcodeFormat.EAN_8, ZXing.BarcodeFormat.QR_CODE, ZXing.BarcodeFormat.DATA_MATRIX, ZXing.BarcodeFormat.CODE_39]);
      hints.set(ZXing.DecodeHintType.TRY_HARDER, true);
      const reader = new ZXing.BrowserMultiFormatReader(hints);
      stockSearchState.barcodeReader = reader;
      const loop = () => {
        if (!stockSearchState.scanning) return;
        if (video.readyState < 2 || !video.videoWidth) { setTimeout(loop, 100); return; }
        try {
          canvas.width = video.videoWidth; canvas.height = video.videoHeight;
          ctx.drawImage(video, 0, 0);
          const img = ctx.getImageData(0, 0, canvas.width, canvas.height);
          const lum = new ZXing.RGBLuminanceSource(img.data, canvas.width, canvas.height);
          const bmp = new ZXing.BinaryBitmap(new ZXing.HybridBinarizer(lum));
          const result = reader.decode(bmp);
          if (result) { onCode(result.getText()); return; }
        } catch(e) {}
        if (stockSearchState.scanning) setTimeout(loop, 150);
      };
      setTimeout(loop, 400);
    }
  } catch (err) {
    toast(err.message?.includes('HTTPS') ? err.message : 'Accès caméra refusé ou non disponible', 'error');
    stopCamera(modal);
  }
}

function stopCamera(modal) {
  if (stockSearchState.cameraStream) {
    stockSearchState.cameraStream.getTracks().forEach(t => t.stop());
    stockSearchState.cameraStream = null;
  }
  if (stockSearchState.barcodeReader) {
    try { stockSearchState.barcodeReader.reset(); } catch(e) {}
    stockSearchState.barcodeReader = null;
  }
  stockSearchState.scanning = false;
  if (modal) modal.remove();
  renderStockSearchBar();
}

function handleBarcodeResult(text) {
  const cleaned = String(text || '').trim().toUpperCase();
  if (!cleaned) return;

  if (isStockEmplacementCode(cleaned)) {
    toast('Emplacement détecté : ' + cleaned);
    loadStockEmplacement(cleaned).then(() => render()).catch(()=>{});
  } else {
    toast('Référence détectée : ' + cleaned);
    set({ stockView: 'produit', stockSearch: cleaned });
    loadStockProduits(cleaned).then(() => render());
  }
}

async function doStockSearch(q) {
  stockSearchState.query = q;
  const cleaned = String(q || '').trim();
  // Suggestions : ≥1 caractère (appel /api/stock/search). Filtre grille seul : toujours ≥2 (scheduleGrilleFilterFromSearch).
  if (!cleaned) {
    stockSearchState.suggestionProduits = [];
    stockSearchState.suggestionEmplacements = [];
    clearTimeout(stockGrilleFilterTimer);
    renderStockSearchBar();
    if (S.stockView === 'grille') set({ stockGrilleFilter: '' });
    return;
  }
  try {
    const r = await api('/api/stock/search?q=' + encodeURIComponent(cleaned) + '&limit=14');
    if (!r) {
      stockSearchState.suggestionProduits = [];
      stockSearchState.suggestionEmplacements = mergeCustomEmplIntoSearch([], cleaned);
    } else {
      stockSearchState.suggestionProduits = r.produits || [];
      stockSearchState.suggestionEmplacements = mergeCustomEmplIntoSearch(r.emplacements || [], cleaned);
    }
  } catch (e) {
    stockSearchState.suggestionProduits = [];
    stockSearchState.suggestionEmplacements = mergeCustomEmplIntoSearch([], cleaned);
  }
  renderStockSearchBar();
  if (S.stockView === 'grille') scheduleGrilleFilterFromSearch();
}

function renderStockSearchBar() {
  const bar = document.getElementById('stock-search-bar');
  if (!bar) return;

  // Si la barre existe déjà avec l'input, ne recréer que les suggestions
  const existingInput = document.getElementById('stock-search-input');
  if (existingInput) {
    // Mettre à jour boutons (état listening/scanning)
    const micBtn = document.getElementById('stock-mic-btn');
    if (micBtn) {
      micBtn.className = 'stock-search-btn' + (stockSearchState.listening ? ' active' : '');
      micBtn.innerHTML = stockSearchState.listening ? stockIconSvg('record') : stockIconSvg('dictaphone');
      micBtn.style.color = stockSearchState.listening ? 'var(--danger)' : '';
      micBtn.setAttribute('aria-pressed', stockSearchState.listening ? 'true' : 'false');
    }
    const camBtn = document.getElementById('stock-cam-btn');
    if (camBtn) {
      camBtn.className = 'stock-search-btn' + (stockSearchState.scanning ? ' active' : '');
      camBtn.innerHTML = stockIconSvg('camera');
      camBtn.setAttribute('aria-pressed', stockSearchState.scanning ? 'true' : 'false');
    }
    let suggEl = document.getElementById('stock-suggestions');
    const pList = stockSearchState.suggestionProduits || [];
    const eList = stockSearchState.suggestionEmplacements || [];
    const hasSug = pList.length > 0 || eList.length > 0;
    if (hasSug) {
      if (!suggEl) {
        suggEl = document.createElement('div');
        suggEl.id = 'stock-suggestions';
        suggEl.className = 'search-suggestions';
        existingInput.parentNode.appendChild(suggEl);
      }
      suggEl.innerHTML = '';
      const clearSug = () => {
        stockSearchState.suggestionProduits = [];
        stockSearchState.suggestionEmplacements = [];
        try{
          const s = document.getElementById('stock-suggestions');
          if(s) s.remove();
        }catch(e){}
      };
      if (eList.length) {
        const sec = document.createElement('div');
        sec.className = 'search-suggestion-section';
        sec.textContent = 'Emplacements';
        suggEl.appendChild(sec);
        eList.forEach(em => {
          const code = em.emplacement || '';
          const nb = em.nb_refs != null ? em.nb_refs : 0;
          const tu = em.total_unites != null ? em.total_unites : 0;
          const item = document.createElement('div');
          item.className = 'search-suggestion-item search-suggestion-empl';
          item.innerHTML = `<div><div class="search-suggestion-ref">${code}</div><div class="search-suggestion-des">${nb} réf. · ${Number(tu).toLocaleString('fr-FR')} u. stock</div></div><span class="stock-badge">📍</span>`;
          item.addEventListener('mousedown', ev => { ev.preventDefault(); });
          item.addEventListener('click', () => {
            existingInput.value = code;
            stockSearchState.query = code;
            clearSug();
            loadStockEmplacement(code).then(() => render());
          });
          suggEl.appendChild(item);
        });
      }
      if (pList.length) {
        const sec = document.createElement('div');
        sec.className = 'search-suggestion-section';
        sec.textContent = 'Produits';
        suggEl.appendChild(sec);
        pList.forEach(p => {
          const item = document.createElement('div');
          item.className = 'search-suggestion-item';
          item.innerHTML = `<div><div class="search-suggestion-ref">${p.reference}</div><div class="search-suggestion-des">${p.designation}</div></div><span class="stock-badge">${p.stock_total||0} ${p.unite}</span>`;
          item.addEventListener('mousedown', ev => { ev.preventDefault(); });
          item.addEventListener('click', async () => {
            stockSearchState.query = p.reference;
            if (existingInput) existingInput.value = p.reference;
            clearSug();
            await loadStockProduit(p.id);
            set({ stockView: 'produit' });
          });
          suggEl.appendChild(item);
        });
      }
    } else {
      if (suggEl) suggEl.remove();
    }
    return;
  }

  // Première création
  bar.innerHTML = '';
  const wrap = document.createElement('div');
  wrap.className = 'stock-search-wrap';

  const input = document.createElement('input');
  input.type = 'text';
  input.id = 'stock-search-input';
  input.className = 'stock-search-input';
  input.placeholder = '🔍  Emplacement (A121) ou référence…';
  input.value = stockSearchState.query || S.stockSearch || '';
  input.addEventListener('input', (e) => doStockSearch(e.target.value));
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      stockSearchState.suggestionProduits = [];
      stockSearchState.suggestionEmplacements = [];
      try{
        const s = document.getElementById('stock-suggestions');
        if(s) s.remove();
      }catch(e){}
      const q = String(input.value || '').trim();
      const qu = q.toUpperCase();
      if (q) {
        if (S.stockView === 'grille') {
          clearTimeout(stockGrilleFilterTimer);
          set({ stockGrilleFilter: q.length >= 2 ? qu : '' });
          return;
        }
        if (isStockEmplacementCode(qu)) {
          loadStockEmplacement(qu).then(() => render());
        } else {
          set({ stockView: 'produit', stockSearch: q });
          loadStockProduits(q).then(() => render());
        }
      }
    }
    if (e.key === 'Escape') {
      stockSearchState.suggestionProduits = [];
      stockSearchState.suggestionEmplacements = [];
      try{
        const s = document.getElementById('stock-suggestions');
        if(s) s.remove();
      }catch(e){}
    }
  });
  wrap.appendChild(input);

  const micBtn = document.createElement('button');
  micBtn.id = 'stock-mic-btn';
  micBtn.className = 'stock-search-btn' + (stockSearchState.listening ? ' active' : '');
  micBtn.type = 'button';
  micBtn.title = 'Recherche vocale';
  micBtn.innerHTML = stockSearchState.listening ? stockIconSvg('record') : stockIconSvg('dictaphone');
  if (stockSearchState.listening) micBtn.style.color = 'var(--danger)';
  micBtn.setAttribute('aria-pressed', stockSearchState.listening ? 'true' : 'false');
  micBtn.addEventListener('click', () => startVoiceSearch());

  const camBtn = document.createElement('button');
  camBtn.id = 'stock-cam-btn';
  camBtn.className = 'stock-search-btn' + (stockSearchState.scanning ? ' active' : '');
  camBtn.type = 'button';
  camBtn.title = 'Scanner un code';
  camBtn.innerHTML = stockIconSvg('camera');
  camBtn.setAttribute('aria-pressed', stockSearchState.scanning ? 'true' : 'false');
  camBtn.addEventListener('click', () => startCameraSearch());

  bar.appendChild(wrap);
  bar.appendChild(micBtn);
  bar.appendChild(camBtn);
}

function initStockSearchBar() {
  const bar = document.getElementById('stock-search-bar');
  if (bar) renderStockSearchBar();
}

const PROFILE_FIELDS=['nom','email','telephone','adresse','date_naissance'];
function profileFieldFilled(val){return String(val==null?'':val).trim().length>0;}
function profileCompletionPercent(u){
  if(!u||typeof u!=='object')return 0;
  let n=0;
  PROFILE_FIELDS.forEach(k=>{if(profileFieldFilled(u[k]))n+=1;});
  return Math.round((n/PROFILE_FIELDS.length)*100);
}
function profileRingTier(pct){
  if(pct>=80)return 'high';
  if(pct>=40)return 'mid';
  return 'low';
}
function profileRingHtml(pct){
  const p=Math.max(0,Math.min(100,Number(pct)||0));
  const r=14;const c=2*Math.PI*r;const off=c*(1-p/100);
  const tier=profileRingTier(p);
  return '<span class="prof-ring" data-tier="'+tier+'" title="Profil complété à '+p+' %">'+
    '<svg viewBox="0 0 34 34" aria-hidden="true">'+
    '<circle class="prof-ring-track" cx="17" cy="17" r="'+r+'" fill="none" stroke-width="3"/>'+
    '<circle class="prof-ring-bar" cx="17" cy="17" r="'+r+'" fill="none" stroke-width="3"'+
    ' stroke-dasharray="'+c.toFixed(2)+'" stroke-dashoffset="'+off.toFixed(2)+'"'+
    ' transform="rotate(-90 17 17)"/>'+
    '</svg>'+
    '<span class="prof-ring-label">'+p+'%</span>'+
    '</span>';
}
function portalProfileRingEl(pct){
  const wrap=document.createElement('span');
  wrap.innerHTML=profileRingHtml(pct);
  const ring=wrap.firstElementChild;
  if(ring)ring.classList.add('portal-prof-ring');
  return ring;
}

function portalOrderTileSpecs(specs, order){
  const byId=new Map(specs.map(s=>[s.id,s]));
  const out=[];
  const seen=new Set();
  if(Array.isArray(order)){
    order.forEach(id=>{
      const sp=byId.get(id);
      if(sp&&!seen.has(id)){out.push(sp);seen.add(id);}
    });
  }
  specs.forEach(sp=>{
    if(!seen.has(sp.id)){out.push(sp);seen.add(sp.id);}
  });
  return out;
}
function portalGetDragInsertBefore(container,x,y){
  const elems=[...container.querySelectorAll('.portal-app')].filter(ch=>
    ch.style.display!=='none' && !ch.classList.contains('portal-app--placeholder')
  );
  if(!elems.length)return null;
  // Regrouper par ligne (flex-wrap) selon la coordonnée top, puis choisir la ligne
  // la plus proche du curseur en Y. Cela évite les cas "bords extérieurs" où un
  // test de tolérance peut rater la bonne ligne.
  const rowTol=10;
  const rows=[];
  elems.forEach(el=>{
    const b=el.getBoundingClientRect();
    if(!b||!b.width||!b.height)return;
    const top=b.top;
    const r=rows.find(g=>Math.abs(g.top-top)<=rowTol);
    if(r)r.items.push({el,b});
    else rows.push({top,items:[{el,b}]});
  });
  if(!rows.length)return null;
  rows.forEach(r=>{
    r.items.sort((a,b)=>a.b.left-b.b.left);
    r.centerY=r.items.reduce((acc,it)=>acc+(it.b.top+it.b.height/2),0)/r.items.length;
  });
  rows.sort((a,b)=>a.centerY-b.centerY);
  let bestRow=rows[0], bestDy=Math.abs(y-rows[0].centerY);
  for(const r of rows){
    const dy=Math.abs(y-r.centerY);
    if(dy<bestDy){bestDy=dy;bestRow=r;}
  }
  const rowItems=bestRow.items;
  const first=rowItems[0], last=rowItems[rowItems.length-1];
  const firstMid=first.b.left+first.b.width/2;
  const lastMid=last.b.left+last.b.width/2;
  // Extrémité gauche
  if(x<firstMid)return first.el;
  // Extrémité droite: insérer "après la dernière tuile de la ligne"
  if(x>lastMid){
    let maxIdx=-1;
    for(const it of rowItems){
      const idx=elems.indexOf(it.el);
      if(idx>maxIdx)maxIdx=idx;
    }
    return (maxIdx>=0 && maxIdx+1<elems.length) ? elems[maxIdx+1] : null;
  }
  // Milieu de ligne: première tuile dont le milieu est à droite du curseur
  for(const it of rowItems){
    const mid=it.b.left+it.b.width/2;
    if(x<mid)return it.el;
  }
  // Fallback: après la ligne
  let maxIdx=-1;
  for(const it of rowItems){
    const idx=elems.indexOf(it.el);
    if(idx>maxIdx)maxIdx=idx;
  }
  return (maxIdx>=0 && maxIdx+1<elems.length) ? elems[maxIdx+1] : null;
}
async function savePortalAppsOrder(ids){
  try{
    const prev=(S.user&&S.user.portal_apps_order)?S.user.portal_apps_order:[];
    await api('/api/auth/me',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({portal_apps_order:ids})});
    S.user={...S.user,portal_apps_order:ids};
    const same=prev.length===ids.length&&prev.every((v,i)=>v===ids[i]);
    if(!same)toast('Ordre du portail enregistré');
  }catch(e){toast(e.message||'Enregistrement impossible','danger');}
}
function attachPortalReorder(appsWrap){
  if(appsWrap._portalDndBound)return;
  appsWrap._portalDndBound=true;
  const DRAG_THRESHOLD=6;
  let dragState=null;

  function ensurePlaceholder(){
    let ph=appsWrap.querySelector('.portal-app--placeholder');
    if(ph)return ph;
    ph=document.createElement('div');
    ph.className='portal-app portal-app--placeholder';
    ph.setAttribute('aria-hidden','true');
    ph.innerHTML='<div class="portal-ph-plus">+</div><div class="portal-ph-label">Déplacer ici</div>';
    return ph;
  }

  function clearDocumentListeners(){
    document.removeEventListener('pointermove',onPointerMove,true);
    document.removeEventListener('pointerup',onPointerUp,true);
    document.removeEventListener('pointercancel',onPointerUp,true);
  }

  function activateDrag(tile,e){
    const rect=tile.getBoundingClientRect();
    dragState.offX=e.clientX-rect.left;
    dragState.offY=e.clientY-rect.top;
    dragState.active=true;

    const ghost=tile.cloneNode(true);
    ghost.classList.add('portal-app--ghost');
    ghost.setAttribute('aria-hidden','true');
    ghost.style.cssText=[
      'position:fixed',
      'left:'+rect.left+'px',
      'top:'+rect.top+'px',
      'width:'+rect.width+'px',
      'height:'+rect.height+'px',
      'margin:0',
      'z-index:10000',
      'pointer-events:none',
      'cursor:grabbing',
      'opacity:.92',
      'transform:scale(1.02)',
      'box-shadow:0 12px 36px rgba(0,0,0,.35)',
    ].join(';');
    document.body.appendChild(ghost);
    dragState.ghost=ghost;

    const ph=ensurePlaceholder();
    ph.style.width=rect.width+'px';
    ph.style.minHeight=rect.height+'px';
    appsWrap.insertBefore(ph,tile);
    tile.style.display='none';
    dragState.placeholder=ph;
  }

  function movePlaceholder(clientX,clientY){
    const ph=dragState&&dragState.placeholder;
    if(!ph)return;
    const after=portalGetDragInsertBefore(appsWrap,clientX,clientY);
    if(after==null||after===ph)appsWrap.appendChild(ph);
    else appsWrap.insertBefore(ph,after);
  }

  function finishDrag(){
    if(!dragState)return;
    const {tile,active,ghost,placeholder:ph}=dragState;
    dragState=null;
    clearDocumentListeners();
    if(!active)return;

    tile.style.display='';
    if(ph&&ph.parentNode){
      appsWrap.insertBefore(tile,ph);
      ph.parentNode.removeChild(ph);
    }
    if(ghost&&ghost.parentNode)ghost.parentNode.removeChild(ghost);

    const ids=[...appsWrap.querySelectorAll('.portal-app')]
      .filter(n=>!n.classList.contains('portal-app--placeholder'))
      .map(n=>n.getAttribute('data-portal-id')).filter(Boolean);
    const prev=(S.user&&S.user.portal_apps_order)?S.user.portal_apps_order:[];
    const same=prev.length===ids.length&&prev.every((v,i)=>v===ids[i]);
    if(!same){
      _portalDragSuppressClick=true;
      setTimeout(()=>{_portalDragSuppressClick=false;},450);
      savePortalAppsOrder(ids);
    }
  }

  function onPointerMove(e){
    if(!dragState||e.pointerId!==dragState.pointerId)return;
    const dx=e.clientX-dragState.startX;
    const dy=e.clientY-dragState.startY;
    if(!dragState.active){
      if(Math.abs(dx)<DRAG_THRESHOLD&&Math.abs(dy)<DRAG_THRESHOLD)return;
      activateDrag(dragState.tile,e);
    }
    e.preventDefault();
    const {ghost,offX,offY}=dragState;
    ghost.style.left=(e.clientX-offX)+'px';
    ghost.style.top=(e.clientY-offY)+'px';
    movePlaceholder(e.clientX,e.clientY);
  }

  function onPointerUp(e){
    if(!dragState||e.pointerId!==dragState.pointerId)return;
    finishDrag();
  }

  appsWrap.addEventListener('dragstart',e=>e.preventDefault());

  appsWrap.addEventListener('pointerdown',e=>{
    if(e.button!==0)return;
    const tile=e.target.closest('.portal-app');
    if(!tile||!appsWrap.contains(tile))return;
    if(tile.classList.contains('portal-app--busy'))return;
    if(tile.getAttribute('draggable')==='false')return;
    dragState={
      tile,
      startX:e.clientX,
      startY:e.clientY,
      active:false,
      pointerId:e.pointerId,
    };
    document.addEventListener('pointermove',onPointerMove,true);
    document.addEventListener('pointerup',onPointerUp,true);
    document.addEventListener('pointercancel',onPointerUp,true);
  });
}

function renderPortal(){
  const aa = S.user && S.user.app_access ? S.user.app_access : null;
  const urole = S.user && S.user.role ? S.user.role : '';
  const isSuper = urole === 'superadmin';
  const isStock = aa ? !!aa.stock : (isSuper || !!(urole && ['direction','administration','logistique','expedition','commercial'].includes(urole)));
  const isProd  = aa ? !!aa.prod : (isSuper || !!(urole && ['direction','administration','fabrication','expedition','commercial'].includes(urole)));
  const isCompta = aa ? !!aa.compta : (isSuper || !!(urole && ['direction','administration','comptabilite'].includes(urole)));
  const isExpe = aa ? !!aa.expe : (isSuper || !!(urole && ['direction','administration','expedition','logistique','commercial'].includes(urole)));
  const isFab = aa ? !!aa.fabrication : (isSuper || urole==='fabrication' || !!(urole && ['direction','administration'].includes(urole)));
  const isPrint = isSuper || !!(urole && ['fabrication','logistique','expedition'].includes(urole));
  const isCom = urole==='commercial';
  const isRH   = aa ? !!aa.planning_rh : (isSuper || !!(urole && ['direction','administration','fabrication','logistique','expedition','comptabilite'].includes(urole)));
  const isComptaPlan = urole === 'comptabilite';
  const isPaie = isSuper || !!(urole && ['direction','administration','comptabilite'].includes(urole));
  const isPricing = aa ? !!(aa.pricing ?? aa.devis) : (isSuper || urole==='direction');
  const isAo = isSuper || urole === 'direction';
  const isBAT = isSuper || !!(urole && ['direction','administration','commercial'].includes(urole));
  const isQualite = isSuper || !!(urole && ['direction','administration','commercial'].includes(urole));
  const _uident = (S.user && S.user.identifiant) ? String(S.user.identifiant).trim().toLowerCase() : '';
  const isMaintenance = isSuper || _uident === 'loic.gognau';
  const isLight=document.body.classList.contains('light');

  const order=(S.user&&Array.isArray(S.user.portal_apps_order))?S.user.portal_apps_order:[];
  const tileSpecs=[];

  if(isFab){
    const id='fabrication';
    tileSpecs.push({id,el:h('div',{
      className:'portal-app',
      'data-portal-id':id,
      draggable:'true',
      onClick:()=>{if(_portalDragSuppressClick)return;window.location.href='/fabrication';}
    },
      h('div',{className:'portal-app-icon'},iconEl('edit',28)),
      h('div',{className:'portal-app-name'},'Saisie Prod'),
      h('div',{className:'portal-app-desc'},'Saisie opérateur — machine')
    )});
  }

  if(isProd){
    const id='prod';
    tileSpecs.push({id,el:h('div',{
      className:'portal-app'+(S.portalLoading==='prod'?' portal-app--busy':''),
      'data-portal-id':id,
      draggable:S.portalLoading==='prod'?'false':'true',
      onClick:async()=>{if(_portalDragSuppressClick)return;window.location.href=isComptaPlan?'/planning':'/prod';}
    },
      h('div',{className:'portal-app-icon'},iconEl('wrench',28)),
      h('div',{className:'portal-app-name'},'MyProd'),
      h('div',{className:'portal-app-desc'},isComptaPlan?'Planning production — lecture seule':'Suivi de production & Planning')
    )});
  }

  if(isStock){
    const id='stock';
    tileSpecs.push({id,el:h('div',{
      className:'portal-app'+(S.portalLoading==='stock'?' portal-app--busy':''),
      'data-portal-id':id,
      draggable:S.portalLoading==='stock'?'false':'true',
      onClick:async()=>{if(_portalDragSuppressClick)return;window.location.href='/stock';}
    },
      h('div',{className:'portal-app-icon'},iconEl('package',28)),
      h('div',{className:'portal-app-name'},'MyStock'),
      h('div',{className:'portal-app-desc'},'Gestion des stocks produits')
    )});
  }

  if(isPrint){
    const id='print';
    tileSpecs.push({id,el:h('div',{
      className:'portal-app',
      'data-portal-id':id,
      draggable:'true',
      onClick:()=>{if(_portalDragSuppressClick)return;window.location.href='/stock?tab=traca';}
    },
      h('div',{className:'portal-app-icon'},iconEl('printer',28)),
      h('div',{className:'portal-app-name'},'MyPrint'),
      h('div',{className:'portal-app-desc'},'Étiquettes de traçabilité')
    )});
  }

  // Messagerie: icône dans le coin (sous Paramètres) pour le super admin

  if(isCompta){
    const id='compta';
    tileSpecs.push({id,el:h('div',{
      className:'portal-app'+(S.portalLoading==='compta'?' portal-app--busy':''),
      'data-portal-id':id,
      draggable:S.portalLoading==='compta'?'false':'true',
      onClick:async()=>{if(_portalDragSuppressClick)return;window.location.href='/compta';}
    },
      h('div',{className:'portal-app-icon'},iconEl('calculator',28)),
      h('div',{className:'portal-app-name'},'MyCompta'),
      h('div',{className:'portal-app-desc'},'Comptabilité — accès réservé')
    )});
  }

  if(isExpe){
    const id='expe';
    tileSpecs.push({id,el:h('div',{
      className:'portal-app'+(S.portalLoading==='expe'?' portal-app--busy':''),
      'data-portal-id':id,
      draggable:S.portalLoading==='expe'?'false':'true',
      onClick:async()=>{if(_portalDragSuppressClick)return;window.location.href='/expe';}
    },
      h('div',{className:'portal-app-icon'},iconEl('truck',28)),
      h('div',{className:'portal-app-name'},'MyExpé'),
      h('div',{className:'portal-app-desc'},
        ((urole==='logistique'||urole==='commercial')&&!isSuper)?'Expédition & suivi — lecture seule':'Expédition & Suivi')
    )});
  }

  if(isRH){
    const id='planning_rh';
    tileSpecs.push({id,el:h('div',{
      className:'portal-app',
      'data-portal-id':id,
      draggable:'true',
      onClick:()=>{if(_portalDragSuppressClick)return;window.location.href='/planning-rh';}
    },
      h('div',{className:'portal-app-icon'},iconEl('users',28)),
      h('div',{className:'portal-app-name'},'Planning RH'),
      h('div',{className:'portal-app-desc'},'Planning personnel & Congés')
    )});
  }

  if(isPricing){
    const id='pricing';
    tileSpecs.push({id,el:h('div',{
      className:'portal-app',
      'data-portal-id':id,
      draggable:'true',
      onClick:()=>{if(_portalDragSuppressClick)return;window.location.href='/pricing';}
    },
      h('div',{className:'portal-app-icon'},iconEl('file-text',28)),
      h('div',{className:'portal-app-name'},'Coûts matières'),
      h('div',{className:'portal-app-desc'},'Matières, produits et calcul €/m²')
    )});
  }

  if(isAo){
    const id='ao';
    tileSpecs.push({id,el:h('div',{
      className:'portal-app',
      'data-portal-id':id,
      draggable:'true',
      onClick:()=>{if(_portalDragSuppressClick)return;window.location.href='/ao';}
    },
      h('div',{className:'portal-app-icon'},iconEl('clipboard',28)),
      h('div',{className:'portal-app-name'},'MyAO'),
      h('div',{className:'portal-app-desc'},'Appels d\'offre fournisseurs')
    )});
  }

  if(isBAT){
    const id='bat';
    tileSpecs.push({id,el:h('div',{
      className:'portal-app',
      'data-portal-id':id,
      draggable:'true',
      onClick:()=>{if(_portalDragSuppressClick)return;window.location.href='/bat';}
    },
      h('div',{className:'portal-app-icon'},iconEl('palette',28)),
      h('div',{className:'portal-app-name'},'MyBAT'),
      h('div',{className:'portal-app-desc'},'Bons À Tirer — suivi client')
    )});
  }

  if(isQualite){
    const id='qualite';
    const qIcoEl=h('div',{className:'portal-app-icon'},iconEl('shield-check',28));
    const qBadge=h('span',{className:'portal-app-badge','id':'portal-qualite-badge',style:{display:'none'}},'0');
    qIcoEl.appendChild(qBadge);
    tileSpecs.push({id,el:h('div',{
      className:'portal-app',
      'data-portal-id':id,
      draggable:'true',
      onClick:()=>{if(_portalDragSuppressClick)return;window.location.href='/qualite';}
    },
      qIcoEl,
      h('div',{className:'portal-app-name'},'MyQualité'),
      h('div',{className:'portal-app-desc'},'Non-conformités & audits client')
    )});
    // Charger le compteur des badges Qualité (NC + audits + affectations)
    setTimeout(()=>{
      fetch('/api/qualite/badges',{credentials:'include'})
        .then(r=>r.ok?r.json():null)
        .then(d=>{
          if(!d) return;
          const el=document.getElementById('portal-qualite-badge');
          if(!el) return;
          const total=(d.nc_unread||0)+(d.audits_unread||0)+(d.audits_assigned_open||0);
          if(total>0){el.style.display='inline-flex';el.textContent=total>99?'99+':String(total);}
          else el.style.display='none';
        })
        .catch(()=>{});
    },0);
  }

  if(isMaintenance){
    const id='maintenance';
    tileSpecs.push({id,el:h('div',{
      className:'portal-app',
      'data-portal-id':id,
      draggable:'true',
      onClick:()=>{if(_portalDragSuppressClick)return;window.location.href='/maintenance';}
    },
      h('div',{className:'portal-app-icon'},iconEl('tool',28)),
      h('div',{className:'portal-app-name'},'Maintenance'),
      h('div',{className:'portal-app-desc'},'Suivi et planification (en cours)')
    )});
  }

  const orderedTiles=portalOrderTileSpecs(tileSpecs,order);
  const apps=orderedTiles.map(s=>s.el);
  const appsWrap=h('div',{className:'portal-apps portal-apps--reorderable'},...apps);
  const appsBlock=h('div',{className:'portal-apps-block',style:{width:'100%',maxWidth:'900px',margin:'0 auto'}},
    appsWrap,
    apps.length?h('div',{className:'portal-apps-hint'},'Maintenir une tuile et la glisser pour réorganiser les accès (ordre enregistré pour votre compte).'):null
  );
  setTimeout(()=>{if(apps.length)attachPortalReorder(appsWrap);},0);
  // Initialiser les dashboards flottants (post-its)
  setTimeout(() => { if (typeof dbInit === 'function') dbInit(); }, 100);

  function logPortalGoogleSearch(query){
    if(!S.user||!query) return;
    fetch('/api/portal/google-search',{
      method:'POST',
      credentials:'include',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({q:query}),
    }).catch(()=>{});
  }
  function openGoogle(q){
    const query = String(q||'').trim();
    if(!query) return;
    logPortalGoogleSearch(query);
    const url = 'https://www.google.com/search?q=' + encodeURIComponent(query);
    // Ouvre un nouvel onglet (Chrome)
    window.open(url, '_blank', 'noopener');
  }

  const gForm = h('form',{onSubmit:(e)=>{
    e.preventDefault();
    const inp = e.target && e.target.querySelector && e.target.querySelector('input');
    openGoogle(inp ? inp.value : '');
  }});
  const gInp = h('input',{type:'search',placeholder:'Rechercher sur Google…',autocomplete:'off',spellcheck:'false'});
  gInp.addEventListener('keydown',(e)=>{
    if(e.key==='Enter'){
      e.preventDefault();
      openGoogle(gInp.value);
    }
  });
  const gLogoEl = document.createElement('span');
  gLogoEl.className = 'portal-search-glogo';
  gLogoEl.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>';
  const gInputWrap = h('div',{className:'portal-search-input-wrap'});
  gInputWrap.appendChild(gLogoEl);
  gInputWrap.appendChild(gInp);
  // ⌘K / Ctrl+K shortcut hint — clicking opens the command palette
  const _cmdkBadge=h('button',{
    type:'button',
    className:'portal-search-cmdk-badge',
    'aria-label':'Ouvrir la palette de commandes',
    title:'Palette de commandes',
    'data-cmdk-open':'1',
    onClick:(ev)=>{ev.preventDefault();if(window.MysifaCmdK)window.MysifaCmdK.open();}
  },document.createTextNode(/Mac|iPod|iPhone|iPad/.test(navigator.platform||'')?'⌘ K':'Ctrl K'));
  gInputWrap.appendChild(_cmdkBadge);
  gForm.appendChild(gInputWrap);
  // Bouton invisible pour conserver le submit natif du form (Entrée)
  gForm.appendChild(h('input',{type:'submit',className:'portal-search-submit',value:'Rechercher'}));
  const gBox = h('div',{className:'portal-search'},
    gForm,
    h('div',{className:'portal-search-hint'},'Astuce : tape puis Entrée pour ouvrir Google.')
  );

  const profPct=profileCompletionPercent(S.user);
  const profRingBadge=(profPct<100)?portalProfileRingEl(profPct):null;
  const profTitle=profPct<100?('Mon profil — '+profPct+' % complété'):'Mon profil';
  // Badge humeur sur l'icône profil
  const _todayIso=(()=>{const d=new Date();return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');})();
  const _humeurVal=(S.user&&S.user.humeur_active&&S.user.humeur_valeur&&S.user.humeur_date===_todayIso)?S.user.humeur_valeur:null;
  const profHumeurBadge=_humeurVal?(()=>{const sp=document.createElement('span');sp.className='portal-humeur-badge';sp.textContent=_humeurVal;return sp;})():null;

  // ── Header mobile (portrait) : logo + Google icone + badge profil ──
  const _mobInitials=(function(){
    const nom=(S.user&&S.user.nom)||'';
    const parts=String(nom).trim().split(/\s+/).filter(Boolean);
    if(!parts.length) return 'EL';
    if(parts.length===1) return parts[0].slice(0,2).toUpperCase();
    return (parts[0][0]+parts[parts.length-1][0]).toUpperCase();
  })();
  const _mobFirstName=(function(){
    const nom=String((S.user&&S.user.nom)||'').trim();
    return nom.split(/\s+/)[0]||'';
  })();
  const _googleLogoSvg=(()=>{const w=document.createElement('span');w.className='mob-google-svg';w.innerHTML='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>';return w;})();
  const _mobGoogleBtn=h('button',{
    type:'button',
    className:'portal-mobile-google-btn',
    'aria-label':'Recherche Google',
    title:'Recherche Google',
    onClick:(e)=>{openGoogleSearch(e&&e.currentTarget?e.currentTarget:null);}
  }, _googleLogoSvg);
  // Avatar : photo si dispo, sinon initiales ; badge humeur si active + aujourd'hui
  const _mobTodayIso=(()=>{const d=new Date();return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');})();
  const _mobAvatarUrl=(S.user&&S.user.avatar_url)?String(S.user.avatar_url).trim():'';
  const _mobHumeur=(S.user&&S.user.humeur_active&&S.user.humeur_valeur&&S.user.humeur_date===_mobTodayIso)?String(S.user.humeur_valeur):'';
  const _mobAvatarInner=_mobAvatarUrl?h('img',{src:_mobAvatarUrl,alt:'',draggable:'false'}):document.createTextNode(_mobInitials);
  const _mobAvatarEl=h('span',{className:'portal-mobile-profile-avatar'},_mobAvatarInner);
  if(_mobHumeur){
    const hb=document.createElement('span');
    hb.className='portal-mobile-profile-humeur';
    hb.textContent=_mobHumeur;
    _mobAvatarEl.appendChild(hb);
  }
  const _mobProfileBtn=h('button',{
    type:'button',
    className:'portal-mobile-profile-btn',
    'aria-label':'Menu profil',
    onClick:()=>{openProfileSheet();}
  },
    _mobAvatarEl,
    h('span',{className:'portal-mobile-profile-name'},_mobFirstName)
  );
  const _mobileHeader=h('div',{className:'portal-mobile-header'},
    h('div',{className:'portal-mobile-header-brand'},'My',h('span',null,'Sifa')),
    h('div',{className:'portal-mobile-header-actions'},_mobGoogleBtn,_mobProfileBtn)
  );

  const portalEl=h('div',{className:'portal-page'},
    _mobileHeader,
    h('div',{className:'portal-corner-stack'},
      h('button',{
        type:'button',
        className:'portal-settings-corner',
        'aria-label':profTitle,
        title:profTitle,
        onClick:()=>{window.location.href='/profil';}
      },profRingBadge,profHumeurBadge,iconEl('user',24)),
      (isSuper||urole==='direction')?h('button',{
        type:'button',
        className:'portal-settings-corner',
        'aria-label':'Paramètres',
        title:'Paramètres',
        onClick:()=>{window.location.href='/settings';}
      },iconEl('sliders',24)):null,
      isSuper?h('button',{
        type:'button',
        className:'portal-settings-corner',
        'aria-label':'Messagerie',
        title:'Messagerie',
        onClick:async()=>{
          set({app:'messages'});
          await loadMessagesUnread().catch(()=>{});
          await loadMessages().catch(()=>{});
        }
      },
        (S.msgUnread>0)?h('span',{className:'portal-corner-badge'},S.msgUnread>9?'9+':String(S.msgUnread)):null,
        iconEl('mail',24)
      ):null,
      (isSuper||urole==='direction'||urole==='administration')?h('button',{
        type:'button',
        className:'portal-settings-corner',
        'aria-label':'Calendrier',
        title:'Calendrier',
        onClick:()=>{window.location.href='/calendrier';}
      },iconEl('calendar',24)):null,
      (isSuper||urole==='direction')?h('button',{
        type:'button',
        className:'portal-settings-corner',
        'aria-label':'Base de données',
        title:'Base de données',
        onClick:()=>{window.location.href='/db';}
      },iconEl('database',24)):null
    ),
    h('div',{className:'portal-logo'},
      h('div',{className:'brand'},'My',h('span',null,'Sifa')),
      h('div',{className:'tagline'},'Portail interne — Production, stocks et outils métier')
    ),
    gBox,
    appsBlock,
    h('div',{className:'portal-user'},
      h('span',{style:{display:'inline-flex',alignItems:'center',gap:'8px'}},iconEl('user',14),document.createTextNode(' '+((S.user&&S.user.nom)?S.user.nom:''))),
      h('button',{className:'portal-logout',onClick:()=>{MySifaTheme.toggleMode();render();}},
        h('span',{className:'theme-ico'},iconEl(isLight?'sun':'moon',16)),
        h('span',{className:'theme-label'},isLight?'Mode clair':'Mode sombre')
      ),
      h('button',{className:'portal-logout',onClick:doLogout},'Déconnexion')
    )
  );
  return portalEl;
}

// ══════════════════════════════════════════════════════
// DASHBOARDS FLOTTANTS — Post-its personnalisés
// ══════════════════════════════════════════════════════

const DB = {
  panels: {},        // dashboard_id → { el, data, dragging }
  visible: true,     // tous visibles ou tous cachés
  fabEl: null,
  badgeEl: null,
};

// Labels lisibles pour les types de widgets
const DB_WIDGET_LABELS = {
  stock_alerts:     'Stocks',
  planning_summary: 'Planning',
  expe_today:       'Expéditions',
};

// Icône SVG selon le type de widget (inline, taille 18px)
function dbWidgetIcon(type) {
  const icons = {
    stock_alerts:     '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>',
    planning_summary: '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>',
    expe_today:       '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="1" y="3" width="15" height="13"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/></svg>',
  };
  return icons[type] || '';
}

// ── Initialisation ─────────────────────────────────────

async function dbInit() {
  let dashboards = [];
  try {
    const r = await fetch('/api/dashboards/me', { credentials: 'include' });
    if (r.ok) dashboards = await r.json();
  } catch(e) { return; }

  if (!dashboards.length) return;

  // Créer le bouton FAB
  dbCreateFab(dashboards.length);

  // Créer un panel pour chaque dashboard
  dashboards.forEach(d => dbCreatePanel(d));
}

function dbCreateFab(count) {
  const fab = document.createElement('button');
  fab.className = 'db-fab';
  fab.title = 'Mes tableaux de bord';
  fab.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>';

  const badge = document.createElement('span');
  badge.className = 'db-fab-badge';
  badge.textContent = count;
  fab.appendChild(badge);
  DB.badgeEl = badge;

  // Bouton + (ajouter un dashboard)
  const fabAdd = document.createElement('button');
  fabAdd.className = 'db-fab';
  fabAdd.style.cssText = 'bottom:80px;right:24px;width:38px;height:38px;background:var(--card);border:1px solid var(--border);box-shadow:0 2px 8px rgba(0,0,0,.2)';
  fabAdd.title = 'Ajouter un tableau de bord';
  fabAdd.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>';
  fabAdd.addEventListener('click', (e) => { e.stopPropagation(); dbOpenAddModal(); });

  fab.addEventListener('click', dbToggleAll);

  document.body.appendChild(fab);
  document.body.appendChild(fabAdd);
  DB.fabEl = fab;
  DB.fabAddEl = fabAdd;
}

function dbUpdateBadge() {
  if (!DB.badgeEl) return;
  const count = Object.keys(DB.panels).length;
  DB.badgeEl.textContent = count;
}

// ── Création d'un panel ───────────────────────────────

function dbCreatePanel(data) {
  const id = data.id;
  const panel = document.createElement('div');
  panel.className = 'db-panel';
  panel.style.cssText = `left:${data.pos_x}px;top:${data.pos_y}px`;
  panel.dataset.dbId = id;

  // En-tête
  const head = document.createElement('div');
  head.className = 'db-panel-head';

  const iconWrap = document.createElement('span');
  iconWrap.innerHTML = dbWidgetIcon(data.widget_type);
  iconWrap.style.cssText = 'color:var(--accent);display:flex;flex-shrink:0';

  const title = document.createElement('span');
  title.className = 'db-panel-title';
  title.textContent = data.titre;

  const typeLabel = document.createElement('span');
  typeLabel.className = 'db-panel-type';
  typeLabel.textContent = DB_WIDGET_LABELS[data.widget_type] || data.widget_type;

  // Bouton minimiser
  const btnMini = document.createElement('button');
  btnMini.className = 'db-panel-btn';
  btnMini.title = data.minimized ? 'Développer' : 'Réduire';
  btnMini.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"/></svg>';
  btnMini.addEventListener('click', (e) => { e.stopPropagation(); dbToggleMini(id, btnMini); });

  // Bouton fermer (désactiver définitivement)
  const btnClose = document.createElement('button');
  btnClose.className = 'db-panel-btn db-panel-btn--danger';
  btnClose.title = 'Désactiver ce tableau de bord';
  btnClose.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
  btnClose.addEventListener('click', (e) => { e.stopPropagation(); dbRemovePanel(id); });

  head.appendChild(iconWrap);
  head.appendChild(title);
  head.appendChild(typeLabel);
  head.appendChild(btnMini);
  head.appendChild(btnClose);

  // Corps
  const body = document.createElement('div');
  body.className = 'db-panel-body';
  body.innerHTML = '<div class="db-widget-empty">Chargement…</div>';

  panel.appendChild(head);
  panel.appendChild(body);
  document.body.appendChild(panel);

  // État minimized
  if (data.minimized) {
    panel.classList.add('db-panel--mini');
    btnMini.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>';
  }

  DB.panels[id] = { el: panel, data, btnMini };

  // Drag
  dbAttachDrag(panel, head, id);

  // Charger les données du widget
  dbLoadWidget(id, data.widget_type, data.config_json, body);
}

// ── Drag & drop ───────────────────────────────────────

function dbAttachDrag(panel, handle, id) {
  let startX, startY, startLeft, startTop, dragging = false;

  function onMouseDown(e) {
    if (e.target.closest('.db-panel-btn')) return;
    e.preventDefault();
    dragging = true;
    startX = e.clientX;
    startY = e.clientY;
    const r = panel.getBoundingClientRect();
    startLeft = r.left;
    startTop = r.top;
    panel.style.transition = 'none';
    panel.style.zIndex = 350;
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  }

  function onMouseMove(e) {
    if (!dragging) return;
    const dx = e.clientX - startX;
    const dy = e.clientY - startY;
    const newX = Math.max(0, Math.min(window.innerWidth - 310, startLeft + dx));
    const newY = Math.max(0, Math.min(window.innerHeight - 60, startTop + dy));
    panel.style.left = newX + 'px';
    panel.style.top  = newY + 'px';
  }

  function onMouseUp(e) {
    if (!dragging) return;
    dragging = false;
    panel.style.transition = '';
    panel.style.zIndex = 290;
    const r = panel.getBoundingClientRect();
    window.removeEventListener('mousemove', onMouseMove);
    window.removeEventListener('mouseup', onMouseUp);
    // Sauvegarder la position
    fetch(`/api/dashboards/me/${id}/state`, {
      method: 'PATCH', credentials: 'include',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ pos_x: r.left, pos_y: r.top }),
    }).catch(() => {});
  }

  handle.addEventListener('mousedown', onMouseDown);

  // Touch support
  handle.addEventListener('touchstart', (e) => {
    if (e.target.closest('.db-panel-btn')) return;
    const t = e.touches[0];
    startX = t.clientX; startY = t.clientY;
    const r = panel.getBoundingClientRect();
    startLeft = r.left; startTop = r.top;
    panel.style.transition = 'none';
  }, { passive: true });
  handle.addEventListener('touchmove', (e) => {
    const t = e.touches[0];
    const dx = t.clientX - startX; const dy = t.clientY - startY;
    const newX = Math.max(0, Math.min(window.innerWidth - 310, startLeft + dx));
    const newY = Math.max(0, Math.min(window.innerHeight - 60, startTop + dy));
    panel.style.left = newX + 'px'; panel.style.top = newY + 'px';
    e.preventDefault();
  }, { passive: false });
  handle.addEventListener('touchend', () => {
    panel.style.transition = '';
    const r = panel.getBoundingClientRect();
    fetch(`/api/dashboards/me/${id}/state`, {
      method: 'PATCH', credentials: 'include',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ pos_x: r.left, pos_y: r.top }),
    }).catch(() => {});
  });
}

// ── Minimiser / développer ────────────────────────────

function dbToggleMini(id, btnMini) {
  const p = DB.panels[id];
  if (!p) return;
  const isMini = p.el.classList.toggle('db-panel--mini');
  btnMini.title = isMini ? 'Développer' : 'Réduire';
  const arrowUp = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"/></svg>';
  const arrowDn = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>';
  btnMini.innerHTML = isMini ? arrowDn : arrowUp;
  fetch(`/api/dashboards/me/${id}/state`, {
    method: 'PATCH', credentials: 'include',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ minimized: isMini }),
  }).catch(() => {});
}

// ── Afficher / cacher tous les panels ─────────────────

function dbToggleAll() {
  DB.visible = !DB.visible;
  Object.values(DB.panels).forEach(p => {
    p.el.classList.toggle('db-panel--hidden', !DB.visible);
  });
  if (DB.fabAddEl) DB.fabAddEl.style.display = DB.visible ? '' : 'none';
}

// ── Supprimer définitivement un panel ─────────────────

async function dbRemovePanel(id) {
  const p = DB.panels[id];
  if (!p) return;
  // Animation de sortie
  p.el.classList.add('db-panel--hidden');
  await new Promise(r => setTimeout(r, 200));
  p.el.remove();
  delete DB.panels[id];
  dbUpdateBadge();
  // Masquer le FAB si plus aucun panel
  if (Object.keys(DB.panels).length === 0 && DB.fabEl) {
    DB.fabEl.style.display = 'none';
    if (DB.fabAddEl) DB.fabAddEl.style.display = 'none';
  }
  // Appel API
  fetch(`/api/dashboards/me/${id}`, { method: 'DELETE', credentials: 'include' }).catch(() => {});
}

// ── Chargement des données du widget ──────────────────

async function dbLoadWidget(id, widgetType, config, bodyEl) {
  try {
    let url = `/api/dashboards/widget/${widgetType}`;
    if (widgetType === 'stock_alerts' && config && config.categories && config.categories.length) {
      url += '?categories=' + encodeURIComponent(config.categories.join(','));
    }
    const r = await fetch(url, { credentials: 'include' });
    if (!r.ok) { bodyEl.innerHTML = '<div class="db-widget-empty">Erreur de chargement.</div>'; return; }
    const data = await r.json();
    bodyEl.innerHTML = dbRenderWidget(widgetType, data);
  } catch(e) {
    bodyEl.innerHTML = '<div class="db-widget-empty">Erreur réseau.</div>';
  }
}

function dbRenderWidget(type, data) {
  if (type === 'stock_alerts') {
    if (!data.length) return '<div class="db-widget-empty">Aucun article sous le seuil d\'alerte.</div>';
    return data.map(item => {
      const pct = item.seuil_alerte > 0 ? Math.round((item.quantite_actuelle / item.seuil_alerte) * 100) : 0;
      const cls = pct === 0 ? 'danger' : pct < 50 ? 'warn' : 'ok';
      const cat = { mandrin: 'Mandrin', palette: 'Palette', adhesif: 'Adhésif', carton: 'Carton' }[item.categorie] || item.categorie;
      return `<div class="db-widget-row">
        <span class="db-widget-badge db-widget-badge--${cls}">${cat}</span>
        <span class="db-widget-label">${escHtml(item.designation)}<br><span style="font-size:11px;color:var(--muted)">Stock : ${item.quantite_actuelle} / seuil : ${item.seuil_alerte}</span></span>
      </div>`;
    }).join('');
  }

  if (type === 'planning_summary') {
    const { en_cours, attente_count, termine_today } = data;
    if (!en_cours.length && !attente_count && !termine_today) {
      return '<div class="db-widget-empty">Aucun dossier en cours.</div>';
    }
    let html = '';
    en_cours.forEach(d => {
      html += `<div class="db-widget-row">
        <span class="db-widget-badge db-widget-badge--ok">En cours</span>
        <span class="db-widget-label">${escHtml(d.reference)} — ${escHtml(d.machine || '')}<br><span style="font-size:11px;color:var(--muted)">${escHtml(d.client || '')}</span></span>
      </div>`;
    });
    if (attente_count) {
      html += `<div class="db-widget-row">
        <span class="db-widget-badge db-widget-badge--warn">Attente</span>
        <span class="db-widget-label">${attente_count} dossier${attente_count > 1 ? 's' : ''} en attente</span>
      </div>`;
    }
    if (termine_today) {
      html += `<div class="db-widget-row">
        <span class="db-widget-badge db-widget-badge--ok">Terminé</span>
        <span class="db-widget-label">${termine_today} dossier${termine_today > 1 ? 's' : ''} terminé${termine_today > 1 ? 's' : ''} aujourd'hui</span>
      </div>`;
    }
    return html;
  }

  if (type === 'expe_today') {
    if (!data.length) return '<div class="db-widget-empty">Aucun départ prévu aujourd\'hui ni demain.</div>';
    return data.map(d => {
      const label = d.est_aujourd_hui ? "Aujourd'hui" : "Demain";
      const cls = d.est_aujourd_hui ? 'danger' : 'warn';
      return `<div class="db-widget-row">
        <span class="db-widget-badge db-widget-badge--${cls}">${label}</span>
        <span class="db-widget-label">${escHtml(d.client || '—')}<br><span style="font-size:11px;color:var(--muted)">${escHtml(d.transporteur || '')} · ${d.nb_palette || 0} pal. · ${d.poids_total_kg || 0} kg</span></span>
      </div>`;
    }).join('');
  }

  return '<div class="db-widget-empty">Type de widget non reconnu.</div>';
}

// ── Modal "Ajouter un tableau de bord" ────────────────

async function dbOpenAddModal() {
  let available = [];
  try {
    const r = await fetch('/api/dashboards/available', { credentials: 'include' });
    if (r.ok) available = await r.json();
  } catch(e) {}

  const overlay = document.createElement('div');
  overlay.className = 'db-add-modal-overlay';
  overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });

  const modal = document.createElement('div');
  modal.className = 'db-add-modal';

  const head = document.createElement('div');
  head.className = 'db-add-modal-head';
  head.innerHTML = `<span class="db-add-modal-title">Ajouter un tableau de bord</span>`;
  const btnCloseModal = document.createElement('button');
  btnCloseModal.className = 'db-panel-btn';
  btnCloseModal.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
  btnCloseModal.addEventListener('click', () => overlay.remove());
  head.appendChild(btnCloseModal);

  const body = document.createElement('div');
  body.className = 'db-add-modal-body';

  if (!available.length) {
    body.innerHTML = '<div class="db-add-empty">Tous les tableaux de bord disponibles sont déjà sur votre portail.</div>';
  } else {
    available.forEach(d => {
      const item = document.createElement('div');
      item.className = 'db-add-item';
      item.innerHTML = `
        <div class="db-add-item-icon" style="color:var(--accent)">${dbWidgetIcon(d.widget_type)}</div>
        <div>
          <div class="db-add-item-name">${escHtml(d.titre)}</div>
          <div class="db-add-item-desc">${escHtml(d.description || DB_WIDGET_LABELS[d.widget_type] || '')}</div>
        </div>`;
      item.addEventListener('click', async () => {
        item.style.opacity = '0.5';
        try {
          const r = await fetch(`/api/dashboards/me/${d.id}/add`, {
            method: 'POST', credentials: 'include',
          });
          if (r.ok) {
            overlay.remove();
            // Recharger les dashboards et recréer le panel
            const r2 = await fetch('/api/dashboards/me', { credentials: 'include' });
            const all = await r2.json();
            const newD = all.find(x => x.id === d.id);
            if (newD) {
              dbCreatePanel(newD);
              dbUpdateBadge();
              if (DB.fabEl) DB.fabEl.style.display = '';
              if (DB.fabAddEl) DB.fabAddEl.style.display = '';
            }
            showToast('Tableau de bord ajouté.', 'success');
          } else {
            showToast('Erreur lors de l\'ajout.', 'danger');
          }
        } catch(e) {
          showToast('Erreur réseau.', 'danger');
        }
      });
      body.appendChild(item);
    });
  }

  modal.appendChild(head);
  modal.appendChild(body);
  overlay.appendChild(modal);
  document.body.appendChild(overlay);
}

function renderStock(){
  const g=S.stockGlobale;
  const isLight=document.body.classList.contains('light');

  const sidebar=h('nav',{className:'sidebar'},
    h('div',{className:'logo'},
      h('div',{className:'logo-brand'},'My',h('span',null,'Stock')),
      h('div',{className:'logo-sub'},'by SIFA')
    ),
    h('button',{className:'nav-btn'+(S.stockView==='grille'?' active':''),
      onClick:async()=>{
        clearTimeout(stockGrilleFilterTimer);
        stockSearchState.query='';
        await loadStockGlobale();
        set({stockView:'grille',stockSelProduit:null,stockSelEmpl:null,stockGrilleFilter:''});
      }},
      iconEl('grid',15),'  Tableau de bord'),
    h('button',{className:'nav-btn'+(S.stockView==='produit'?' active':''),
      onClick:async()=>{await loadStockProduits();set({stockView:'produit',stockSelProduit:null});}},
      iconEl('tag',15),'  Par référence'),
    h('button',{className:'nav-btn'+(S.stockView==='emplacement'?' active':''),
      onClick:()=>set({stockView:'emplacement',stockSelEmpl:null})},
      iconEl('map-pin',15),'  Par emplacement'),
    h('div',{className:'sidebar-bottom'},
      (S.user&&['direction','fabrication','logistique','superadmin'].includes(S.user.role))?
        h('button',{className:'nav-btn',onClick:()=>{window.location.href='/planning-rh'}},
          iconEl('users',15),'  Planning RH')
        :null,
      h('button',{className:'nav-btn back-mysifa',onClick:()=>{window.location.href='/' }},
        '← Retour ',
        h('span',{className:'wm'},'My',h('span',null,'Sifa'))
      ),
      sidebarUserChip(S.user),
      (() => {
        const b=h('button',{
          className:'support-btn',
          title:'Contacter le support',
          onClick:()=>set({contactOpen:true})
        });
        const ico=h('span',{className:'support-ico'});
        try{
          ico.innerHTML=(window.MySifaSupport && typeof window.MySifaSupport.iconSvg==='function')?window.MySifaSupport.iconSvg():'';
        }catch(e){ ico.innerHTML=''; }
        b.appendChild(ico);
        b.appendChild(h('span',null,'Contacter le support'));
        return b;
      })(),
      h('button',{className:'theme-btn',onClick:()=>{MySifaTheme.toggleMode();render();}},
        h('span',{className:'theme-ico'},iconEl(isLight?'sun':'moon',16)),
        h('span',{className:'theme-label'},isLight?'Mode clair':'Mode sombre')
      ),
      h('button',{className:'logout-btn',onClick:doLogout},iconEl('log-out',14),' Déconnexion'),
      h('div',{className:'version'},'MyStock v1.0')
    )
  );

  let content;

  if(S.stockView==='grille'){
    const grille=(g&&g.grille)?g.grille:[];
    const stats=(g&&g.stats)?g.stats:{};
    let mvts=(g&&g.derniers_mouvements)?g.derniers_mouvements:[];
    const filt=(S.stockGrilleFilter||'').trim().toUpperCase();

    const byEmpl={};
    grille.forEach(r=>{
      if(!byEmpl[r.emplacement])byEmpl[r.emplacement]=[];
      byEmpl[r.emplacement].push(r);
    });
    for(const e of [...STOCK_EMPLACEMENTS,...loadStockEmplCustom()]){
      if(!byEmpl[e])byEmpl[e]=[];
    }

    let statBar;
    let invBarRow=null;
    if(filt){
      const nref=new Set();
      const visibleEmpl=[];
      let nempl=0,tun=0;
      Object.entries(byEmpl).forEach(([empl,items])=>{
        if(!stockBoardEmplVisible(empl,items,filt))return;
        visibleEmpl.push(empl);
        nempl++;
        stockBoardItemsForCell(empl,items,filt).forEach(i=>{
          nref.add(i.reference);
          tun+=Number(i.quantite)||0;
        });
      });
      visibleEmpl.sort((a,b)=>String(a).localeCompare(String(b),'fr'));
      let invCible=null;
      if(visibleEmpl.length===1){
        invCible={type:'empl',code:visibleEmpl[0]};
      }else if(nref.size===1){
        invCible={type:'prod',reference:[...nref][0]};
      }
      statBar=h('div',{className:'stats',style:{marginBottom:'20px'}},
        h('div',{className:'stat'},h('div',{className:'stat-label'},'Filtre actif'),h('div',{className:'stat-value',style:{color:'var(--warn)'}},filt)),
        h('div',{className:'stat'},h('div',{className:'stat-label'},'Réf. correspondantes'),h('div',{className:'stat-value',style:{color:'var(--c1)'}},nref.size)),
        h('div',{className:'stat'},h('div',{className:'stat-label'},'Cases affichées'),h('div',{className:'stat-value',style:{color:'var(--c2)'}},nempl)),
        h('div',{className:'stat'},h('div',{className:'stat-label'},'Unités (filtre)'),h('div',{className:'stat-value',style:{color:'var(--c3)'}},fN(tun)))
      );
      if(invCible){
        const bt=(invCible.type==='empl')
          ?('📋 Inventaire emplacement '+invCible.code)
          :('📋 Inventaire réf. '+invCible.reference);
        invBarRow=h('div',{style:{marginBottom:'16px',display:'flex',flexWrap:'wrap',gap:'12px',alignItems:'center',justifyContent:'space-between'}},
          h('p',{style:{fontSize:'12px',color:'var(--muted)',margin:0,maxWidth:'560px',lineHeight:'1.5'}},
            invCible.type==='empl'
              ?'Une seule case est affichée : vous pouvez lancer un inventaire ciblé sur tous les articles à cet emplacement.'
              :'Une seule référence ressort du filtre : vous pouvez inventorier cette référence sur tous les emplacements où elle est stockée.'),
          h('button',{
            className:'btn-sm',
            style:{border:'1px solid var(--c2)',color:'var(--c2)',background:'rgba(167,139,250,.14)',fontWeight:'700',flexShrink:'0'},
            onClick:()=>{openInventaireCibleModal(invCible);}
          },bt)
        );
      }
    }else{
      statBar=h('div',{className:'stats',style:{marginBottom:'20px'}},
        h('div',{className:'stat'},h('div',{className:'stat-label'},'Références'),h('div',{className:'stat-value',style:{color:'var(--c1)'}},stats.nb_refs||0)),
        h('div',{className:'stat'},h('div',{className:'stat-label'},'Emplacements occupés'),h('div',{className:'stat-value',style:{color:'var(--c2)'}},stats.nb_empl||0)),
        h('div',{className:'stat'},h('div',{className:'stat-label'},'Total unités'),h('div',{className:'stat-value',style:{color:'var(--c3)'}},fN(stats.total_unites||0)))
      );
    }

    const invPrior=S.stockInvPriorites||[];
    const invCard=h('div',{className:'card',style:{marginBottom:'16px'}},
      h('div',{className:'card-header'},
        h('h3',null,'Inventaire — priorités (réf. en stock)'),
        h('span',{className:'stock-badge'},'Du plus urgent au moins urgent')
      ),
      h('p',{style:{fontSize:'12px',color:'var(--muted)',margin:'0 18px 12px',lineHeight:'1.5'}},
        'Toutes les références actuellement en stock, triées : jamais inventorié d’abord, puis le plus ancien inventaire. Les entrées récentes sont considérées comme déjà « comptées » (date d’inventaire = aujourd’hui).'),
      invPrior.length===0
        ? h('div',{className:'card-empty'},'Aucune ligne de stock.')
        : h('div',{style:{maxHeight:'360px',overflowY:'auto'}},h('table',null,
            h('thead',null,h('tr',null,
              h('th',null,'Référence'),h('th',null,'Emplacement'),h('th',null,'Quantité'),
              h('th',null,'Dernier inventaire'),h('th',null,'Depuis (jours)'))),
            h('tbody',null,...invPrior.map(r=>{
              const j=r.jours_depuis_inv;
              const urg=(j==null||j>=999999||j>=180);
              return h('tr',null,
                h('td',{style:{fontFamily:'monospace',fontWeight:'700',color:'var(--accent)'}},r.reference),
                h('td',{style:{fontFamily:'monospace'}},r.emplacement),
                h('td',{style:{fontFamily:'monospace'}},fN(r.quantite)+' '+String(r.unite||'')),
                h('td',{style:{fontSize:'11px',color:'var(--muted)'}},r.derniere_inventaire?fD(r.derniere_inventaire):'—'),
                h('td',{style:{fontSize:'12px',fontWeight:'700',color:urg?'var(--danger)':'var(--muted)'}},
                  (j==null||j>=999999)?'Jamais':String(j))
              );
            }))
          ))
    );

    const grid=h('div',{className:'stock-grid'},
      ...Object.entries(byEmpl)
        .filter(([empl,items])=>stockBoardEmplVisible(empl,items,filt))
        .sort((a,b)=>String(a[0]).localeCompare(String(b[0]),'fr'))
        .map(([empl,items])=>{
          const shown=stockBoardItemsForCell(empl,items,filt);
          return h('div',{className:'stock-cell',onClick:async()=>{
            await loadStockEmplacement(empl);
          }},
            h('div',{className:'stock-cell-label'},empl),
            shown.length===0
              ? h('div',{className:'stock-cell-empty'},'Vide')
              : h('div',{className:'stock-cell-items'},
                  ...shown.map(i=>h('div',null,
                    i.reference,
                    h('span',{className:'stock-badge'},fN(i.quantite)+' '+i.unite)
                  ))
                )
          );
        })
    );

    if(filt){
      const u=filt;
      mvts=mvts.filter(m=>
        String(m.reference||'').toUpperCase().includes(u)||
        String(m.emplacement||'').toUpperCase().includes(u)||
        String(m.created_by||'').toUpperCase().includes(u));
    }

    const mvtTable=mvts.length?h('div',{className:'card'},
      h('div',{className:'card-header'},h('h3',null,filt?'Mouvements (filtre)':'Derniers mouvements')),
      h('div',{style:{overflowX:'auto'}},h('table',null,
        h('thead',null,h('tr',null,h('th',null,'Date'),h('th',null,'Réf'),h('th',null,'Emplacement'),h('th',null,'Type'),h('th',null,'Qté'),h('th',null,'Par'))),
        h('tbody',null,...mvts.map(m=>h('tr',null,
          h('td',{style:{fontFamily:'monospace',fontSize:'11px'}},fD(m.created_at)),
          h('td',{style:{fontFamily:'monospace',fontWeight:'700'}},m.reference),
          h('td',{style:{fontFamily:'monospace'}},m.emplacement),
          h('td',null,h('span',{className:'mvt-type-'+(m.type_mouvement==='entree'||m.type_mouvement==='sortie'?'pf-'+m.type_mouvement:m.type_mouvement)},m.type_mouvement)),
          h('td',{style:{fontFamily:'monospace'}},fN(m.quantite)),
          h('td',{style:{fontSize:'11px',color:'var(--muted)'}},stockActor(m))
        )))
      ))
    ):null;

    content=h('div',null,statBar,invCard,invBarRow,grid,mvtTable);
  }

  else if(S.stockView==='produit'){
    const produits=S.stockProduits||[];
    const sel=S.stockSelProduit;

    const newRef=h('input',{type:'text',placeholder:'Référence *',style:{textTransform:'uppercase',flex:'1',minWidth:'140px'}});
    const newDes=h('input',{type:'text',placeholder:'Désignation *'});
    const newUnit=h('input',{type:'text',placeholder:'Unité (ex: m, rouleau, carton)',value:'unité'});
    if(S.stockPrefillRef) newRef.value=S.stockPrefillRef;
    if(S.stockPrefillDes) newDes.value=S.stockPrefillDes;
    if(S.stockPrefillUnit) newUnit.value=S.stockPrefillUnit;
    const emplInput=h('input',{type:'text',id:'stock-add-empl-input',
      className:'stock-search-input stock-add-empl-input',
      placeholder:'Emplacement * (ex. a121…)',autocomplete:'off',title:'Obligatoire — suggestions ou + Ajouter emplacement',
      style:{width:'100%',minWidth:'160px'}});
    const emplSugg=h('div',{id:'stock-add-empl-suggestions',className:'search-suggestions',style:{display:'none'}});
    const emplComboWrap=h('div',{className:'stock-search-wrap',style:{flex:'1',minWidth:'180px'}},emplInput,emplSugg);
    const newQtyEmpl=h('input',{type:'number',placeholder:'Qté *',min:'0',step:'any',style:{width:'110px'},title:'Quantité d’entrée en stock à l’emplacement (obligatoire, > 0)'});
    const newFormBtn=h('button',{className:'btn-sm',onClick:()=>{
      if(!newRef.value||!newDes.value)return;
      const empl=String((document.getElementById('stock-add-empl-input')||{}).value||'').trim().toUpperCase();
      if(!empl||!isStockEmplacementCode(empl)){toast('Emplacement obligatoire (ex. Z999)','error');return;}
      const qv=newQtyEmpl.value;
      const qn=parseFloat(String(qv||'').replace(',','.'));
      if(qv===''||qv==null||Number.isNaN(qn)||qn<=0){toast('Quantité obligatoire (nombre > 0)','error');return;}
      createProduit({
        reference:newRef.value,designation:newDes.value,unite:newUnit.value||'unité',
        emplacement:empl,
        quantite_emplacement:qv
      });
      newRef.value='';newDes.value='';newQtyEmpl.value='';
      const ei=document.getElementById('stock-add-empl-input');if(ei)ei.value='';
    }},'+ Créer');
    if(S.stockPrefillEmpl) emplInput.value=S.stockPrefillEmpl;
    S.stockPrefillRef=null;S.stockPrefillDes=null;S.stockPrefillUnit=null;S.stockPrefillEmpl=null;

    const newForm=h('div',{className:'card stock-new-produit-card',style:{padding:'16px',marginBottom:'16px',overflow:'visible'}},
      h('div',{className:'form-section-title'},'Nouveau produit (ou entrée sur réf. existante)'),
      h('div',{style:{display:'flex',flexDirection:'column',gap:'8px'}},
        h('div',{style:{display:'flex',gap:'8px',flexWrap:'wrap',alignItems:'center'}},
          newRef,newDes,newUnit,emplComboWrap,newQtyEmpl),
        h('div',{style:{display:'flex',alignItems:'center'}},newFormBtn)
      )
    );

    const searchI=h('input',{type:'text',className:'search-bar',
      placeholder:'🔍 Référence, désignation ou code-barres…',value:S.stockSearch||''});
    searchI.addEventListener('input',e=>{
      S.stockSearch=e.target.value;
      loadStockProduits(e.target.value);
    });
    const searchRow=h('div',{className:'stock-search-row'},searchI);

    const liste=h('div',{className:'card',style:{maxHeight:'500px',overflowY:'auto'}},
      produits.length===0?h('div',{className:'card-empty'},'Aucun produit'):
      h('div',null,...produits.map(p=>h('div',{
        className:'produit-row'+(((sel&&sel.produit&&sel.produit.id)===p.id)?' active':''),
        onClick:async()=>await loadStockProduit(p.id)
      },
        h('div',null,
          h('div',{className:'produit-ref'},p.reference),
          h('div',{className:'produit-des'},p.designation)
        ),
        h('span',{className:'stock-badge'},fN(p.stock_total)+' '+p.unite)
      )))
    );

    let detail=h('div',{className:'card-empty',style:{padding:'40px'}},'← Sélectionnez un produit');
    if(sel){
      const p=sel.produit;
      const empls=sel.emplacements||[];

      const empl_sel=h('select',{className:'form-sel'},
        h('option',{value:''},'— Emplacement —'),
        ...['A121','A122','A123','B121','B122','B123','C121','C122','C123'].map(e=>h('option',{value:e},e))
      );
      const qte_inp=h('input',{type:'number',placeholder:'Quantité',min:'0',style:{width:'120px'}});
      const note_inp=h('input',{type:'text',placeholder:'Note (optionnel)',style:{flex:1}});

      const pfMvtActiveCls={entree:'pf-entree',sortie:'pf-sortie',inventaire:'inventaire'};
      const mvtBtns=h('div',{className:'mvt-btns'},
        ...[['entree','Entrée ↓'],['sortie','Sortie ↑'],['inventaire','Inventaire =']].map(([t,l])=>{
          const btn=h('button',{className:'mvt-btn'+(S.stockMvtType===t?' active-'+pfMvtActiveCls[t]:'')},l);
          btn.addEventListener('click',()=>{S.stockMvtType=t;render();});
          return btn;
        })
      );

      const sendBtn=h('button',{className:'btn-sm',onClick:()=>{
        if(!empl_sel.value||!qte_inp.value)return;
        doMouvement({produit_id:p.id,emplacement:empl_sel.value,
          type_mouvement:S.stockMvtType,quantite:parseFloat(qte_inp.value),
          note:note_inp.value});
        qte_inp.value='';note_inp.value='';
      }},'✓ Valider');

      const mvtForm=h('div',{className:'mouvement-form'},
        h('div',{className:'form-section-title'},'Mouvement de stock'),
        mvtBtns,
        h('div',{style:{display:'flex',gap:'8px',flexWrap:'wrap',alignItems:'center'}},
          empl_sel,qte_inp,note_inp,sendBtn)
      );

      const emplTable=empls.length?h('div',{className:'card'},
        h('div',{className:'card-header'},
          h('h3',null,'Stock par emplacement'),
          h('span',{className:'stock-badge'},fN(sel.stock_total)+' '+p.unite+' total · '+empls.length+' empl.')
        ),
        h('table',null,
          h('thead',null,h('tr',null,h('th',null,'Emplacement'),h('th',null,'Quantité'),h('th',null,'FIFO lot'),h('th',null,'Dernier mouv.'),h('th',null,'Par'))),
          h('tbody',null,...empls.map(e=>h('tr',null,
            h('td',{
              style:{fontFamily:'monospace',fontWeight:'700',color:'var(--accent)',cursor:'pointer',textDecoration:'underline'},
              title:'Voir la fiche emplacement',
              onClick:(ev)=>{
                ev.preventDefault();ev.stopPropagation();
                try{hideStockAddEmplDropdown();}catch(err){}
                loadStockEmplacement(e.emplacement);
              }
            },e.emplacement),
            h('td',{style:{fontFamily:'monospace',fontWeight:'700'}},fN(e.quantite)+' '+p.unite),
            h('td',{style:{fontSize:'11px',color:'var(--muted)'}},fD(e.date_fifo_empl)),
            h('td',{style:{fontSize:'11px',color:'var(--muted)'}},fD(e.updated_at||e.date_fifo_empl)),
            h('td',{style:{fontSize:'11px',color:'var(--muted)'}},e.updated_by||'—')
          )))
        )
      ):h('div',{className:'card-empty'},'Aucun stock pour ce produit');

      const mvts=sel.mouvements||[];
      const mvtHistory=mvts.length?h('div',{className:'card',style:{marginTop:'12px'}},
        h('div',{className:'card-header'},
          h('h3',null,'Historique des mouvements'),
          h('span',{className:'stock-badge'},mvts.length+' enregistrement'+(mvts.length>1?'s':''))
        ),
        h('div',{style:{overflowX:'auto'}},h('table',null,
          h('thead',null,h('tr',null,
            h('th',null,'Date'),h('th',null,'Type'),h('th',null,'Empl.'),
            h('th',null,'Qté'),h('th',null,'Avant → Après'),h('th',null,'Note'),h('th',null,'Utilisateur'))),
          h('tbody',null,...mvts.map(m=>h('tr',null,
            h('td',{style:{fontSize:'11px',fontFamily:'monospace',whiteSpace:'nowrap'}},fD(m.created_at)),
            h('td',null,h('span',{className:'mvt-type-'+(m.type_mouvement==='entree'||m.type_mouvement==='sortie'?'pf-'+m.type_mouvement:m.type_mouvement)},m.type_mouvement)),
            h('td',{style:{fontFamily:'monospace',fontSize:'12px'}},m.emplacement),
            h('td',{style:{fontFamily:'monospace'}},fN(m.quantite)),
            h('td',{style:{fontSize:'11px',fontFamily:'monospace'}},fN(m.quantite_avant)+' → '+fN(m.quantite_apres)),
            h('td',{style:{fontSize:'11px',color:'var(--muted)',maxWidth:'140px'}},m.note||'—'),
            h('td',{style:{fontSize:'11px',color:'var(--muted)'}},stockActor(m))
          )))
        ))
      ):null;

      const btnAddQty=h('button',{
        className:'btn-sm',
        style:{flexShrink:0},
        onClick:()=>{
          S.stockPrefillRef=p.reference;
          S.stockPrefillDes=p.designation||'';
          S.stockPrefillUnit=p.unite||'unité';
          render();
          requestAnimationFrame(()=>{
            const el=document.querySelector('.stock-new-produit-card');
            if(el&&el.scrollIntoView) el.scrollIntoView({behavior:'smooth',block:'center'});
            try{const ei=document.getElementById('stock-add-empl-input');if(ei){ei.focus();}}catch(e){}
          });
        }
      },'+ Ajouter une quantité');

      detail=h('div',null,
        h('div',{className:'card',style:{padding:'16px',marginBottom:'12px'}},
          h('div',{style:{display:'flex',alignItems:'flex-start',justifyContent:'space-between',gap:'12px',flexWrap:'wrap'}},
            h('div',{style:{flex:'1',minWidth:'200px'}},
          h('h3',{style:{fontSize:'16px',fontWeight:'800',marginBottom:'4px'}},p.reference),
          h('p',{style:{fontSize:'13px',color:'var(--muted)'}},p.designation),
              h('p',{style:{fontSize:'11px',color:'var(--muted)',marginTop:'4px'}},'Unité : '+p.unite)
            ),
            btnAddQty
          ),
          h('div',{style:{display:'flex',gap:'20px',flexWrap:'wrap',marginTop:'14px'}},
            h('div',null,
              h('div',{style:{fontSize:'10px',fontWeight:'700',color:'var(--muted)',textTransform:'uppercase',letterSpacing:'.04em'}},'Stock total'),
              h('div',{style:{fontSize:'18px',fontWeight:'800',fontFamily:'monospace',color:'var(--accent)'}},fN(sel.stock_total)+' '+p.unite)),
            h('div',null,
              h('div',{style:{fontSize:'10px',fontWeight:'700',color:'var(--muted)',textTransform:'uppercase',letterSpacing:'.04em'}},'Lots actifs'),
              h('div',{style:{fontSize:'16px',fontWeight:'700',fontFamily:'monospace'}},String(sel.nb_lots||0))),
            sel.date_fifo?h('div',null,
              h('div',{style:{fontSize:'10px',fontWeight:'700',color:'var(--muted)',textTransform:'uppercase',letterSpacing:'.04em'}},'Plus ancien lot (FIFO)'),
              h('div',{style:{fontSize:'13px',fontFamily:'monospace'}},fD(sel.date_fifo))):null,
            sel.jours_stock!=null?h('div',null,
              h('div',{style:{fontSize:'10px',fontWeight:'700',color:'var(--muted)',textTransform:'uppercase',letterSpacing:'.04em'}},'Ancienneté stock'),
              h('div',{style:{fontSize:'16px',fontWeight:'700'}},String(sel.jours_stock)+' j')):null
          )
        ),
        mvtForm,
        emplTable,
        mvtHistory
      );
    }

    content=h('div',null,
      newForm,searchRow,
      h('div',{className:'stock-panel'},
        h('div',{className:'stock-left'},liste),
        h('div',{className:'stock-right'},detail)
      )
    );
  }

  else if(S.stockView==='emplacement'){
    const EMPL_GRID=[...new Set([...STOCK_EMPLACEMENTS,...loadStockEmplCustom()])].sort();
    const sel=S.stockSelEmpl;

    const empl_list=h('div',{className:'card',style:{marginBottom:'16px',overflow:'visible'}},
      h('div',{className:'card-header'},h('h3',null,'Raccourcis emplacements')),
      h('div',{style:{display:'flex',gap:'8px',flexWrap:'wrap',padding:'16px'}},
        ...EMPL_GRID.map(e=>h('button',{
          className:'mvt-btn'+(((sel&&sel.emplacement)===e)?' active-pf-entree':''),
          onClick:async()=>await loadStockEmplacement(e)
        },e))
      )
    );

    let detail=h('div',{className:'card-empty',style:{padding:'40px'}},
      'Recherchez un emplacement dans la barre en haut, ou choisissez un raccourci.');

    if(sel&&sel.emplacement!=null){
      const refs=sel.refs||[];
      const mvts=sel.mouvements||[];
      const refsTable=refs.length===0
        ? h('div',{className:'card-empty'},'Aucune unité stockée à cet emplacement.')
        : h('div',{style:{overflowX:'auto'}},h('table',null,
            h('thead',null,h('tr',null,h('th',null,'Référence'),h('th',null,'Désignation'),h('th',null,'Quantité'),h('th',null,'FIFO lot'),h('th',null,'Dernier mouv.'),h('th',null,'Par'))),
            h('tbody',null,...refs.map(pr=>h('tr',{
              className:'produit-row',
              style:{cursor:'pointer'},
              title:'Voir la fiche produit',
              onClick:async()=>{await loadStockProduit(pr.id);set({stockView:'produit'});}
            },
              h('td',{style:{fontFamily:'monospace',fontWeight:'700',color:'var(--accent)'}},pr.reference),
              h('td',null,pr.designation),
              h('td',{style:{fontFamily:'monospace',fontWeight:'700'}},fN(pr.quantite)+' '+pr.unite),
              h('td',{style:{fontSize:'11px',color:'var(--muted)'}},fD(pr.date_fifo)),
              h('td',{style:{fontSize:'11px',color:'var(--muted)'}},fD(pr.updated_at||pr.date_fifo)),
              h('td',{style:{fontSize:'11px',color:'var(--muted)'}},pr.updated_by||'—')
            )))
          ));

      const mvtBlock=mvts.length?h('div',{className:'card',style:{marginTop:'12px'}},
        h('div',{className:'card-header'},
          h('h3',null,'Historique des mouvements'),
          h('span',{className:'stock-badge'},mvts.length+' enregistrements')
        ),
        h('div',{style:{overflowX:'auto'}},h('table',null,
          h('thead',null,h('tr',null,
            h('th',null,'Date'),h('th',null,'Type'),h('th',null,'Réf.'),h('th',null,'Qté'),
            h('th',null,'Avant → Après'),h('th',null,'Note'),h('th',null,'Utilisateur'))),
          h('tbody',null,...mvts.map(m=>h('tr',null,
            h('td',{style:{fontSize:'11px',fontFamily:'monospace',whiteSpace:'nowrap'}},fD(m.created_at)),
            h('td',null,h('span',{className:'mvt-type-'+(m.type_mouvement==='entree'||m.type_mouvement==='sortie'?'pf-'+m.type_mouvement:m.type_mouvement)},m.type_mouvement)),
            h('td',{style:{fontFamily:'monospace',fontSize:'12px'}},m.reference||'—'),
            h('td',{style:{fontFamily:'monospace'}},fN(m.quantite)),
            h('td',{style:{fontSize:'11px',fontFamily:'monospace'}},fN(m.quantite_avant)+' → '+fN(m.quantite_apres)),
            h('td',{style:{fontSize:'11px',color:'var(--muted)',maxWidth:'120px'}},m.note||'—'),
            h('td',{style:{fontSize:'11px',color:'var(--muted)'}},stockActor(m))
          )))
        ))
      ):h('div',{className:'card',style:{marginTop:'12px'}},
        h('div',{className:'card-header'},h('h3',null,'Historique des mouvements')),
        h('div',{className:'card-empty'},'Aucun mouvement enregistré pour cet emplacement.')
      );

      detail=h('div',null,
        h('div',{className:'card',style:{marginBottom:'12px'}},
          h('div',{className:'card-header'},
            h('h3',null,'Emplacement '+sel.emplacement),
            h('div',{style:{display:'flex',gap:'8px',alignItems:'center',flexWrap:'wrap'}},
              h('span',{className:'stock-badge'},fN(sel.total_unites||0)+' u. · '+refs.length+' réf.'),
              h('button',{
                className:'btn-sm',
                onClick:async()=>{
                  S.stockPrefillEmpl=sel.emplacement;
                  S.stockSelProduit=null;
                  await loadStockProduits('');
                  set({stockView:'produit'});
                  requestAnimationFrame(()=>{
                    const el=document.querySelector('.stock-new-produit-card');
                    if(el&&el.scrollIntoView) el.scrollIntoView({behavior:'smooth',block:'center'});
                    try{hideStockAddEmplDropdown();}catch(e){}
                    try{const ei=document.getElementById('stock-add-empl-input');if(ei){ei.focus();}}catch(e){}
                  });
                }
              },'+ Ajouter une réf.')
            )
          ),
          h('p',{style:{fontSize:'12px',color:'var(--muted)',padding:'0 16px 14px'}},
            'Stocks actifs (lots FIFO) et historique des mouvements en base.')
        ),
        h('div',{className:'card',style:{marginBottom:'12px'}},
          h('div',{className:'card-header'},h('h3',null,'Produits stockés')),
          refsTable
        ),
        mvtBlock
      );
    }

    content=h('div',null,empl_list,detail);
  }

  const topbar=h('div',{className:'mobile-topbar'},
    h('button',{type:'button',className:'mobile-menu-btn',onClick:toggleSidebar,'aria-label':'Menu'},iconEl(S.sidebarOpen?'x':'menu',20)),
    h('div',{style:{flex:1,minWidth:0}},
      h('div',{className:'mobile-topbar-title'},'MyStock'),
      h('div',{className:'mobile-topbar-sub'},
        S.stockView==='grille'?'Tableau de bord':S.stockView==='produit'?'Par référence':'Par emplacement'
      ),
      h('div',{id:'stock-search-bar',className:'stock-search-bar'})
    ),
    h('button',{type:'button',className:'mobile-home-btn',onClick:()=>{window.location.href='/'},'aria-label':'Accueil'},iconEl('home',20))
  );
  // Motion : cascade au changement de vue MyStock uniquement (le re-render
  // intra-vue ne doit pas relancer l'animation, sinon perte de focus inputs).
  const _moStockKey=(S.stockView||'')+'|'+(S.stockSelProduit||'')+'|'+(S.stockSelEmpl||'');
  const _moStockEnter=(window._moStockLastKey!==_moStockKey);
  window._moStockLastKey=_moStockKey;
  // Niveau 2 : pose data-page-enter sur le 1er element du content pour
  // cascader ses propres enfants (stats, mouvements, grille, etc.).
  if(_moStockEnter && content && content.nodeType===1){
    try{ content.setAttribute('data-page-enter',''); }catch(_){}
  }
  const _stockContainerProps={className:'container',style:{padding:'24px 28px'}};
  if(_moStockEnter) _stockContainerProps['data-page-enter']='';
  const mainEl=h('main',{className:'main'},
    topbar,
    h('div',_stockContainerProps,
      h('h1',null,S.stockView==='grille'?'Tableau de bord':S.stockView==='produit'?'Par référence':'Par emplacement'),
      h('div',{className:'subtitle'},
        S.stockView==='grille'?(S.stockGrilleFilter&&String(S.stockGrilleFilter).trim().length>=2
          ? 'Données filtrées sur « '+String(S.stockGrilleFilter).trim().toUpperCase()+' » — grille, stats et mouvements'
          : 'Tous les emplacements et leur contenu — suggestions dès 1 caractère ; filtre grille à partir de 2 caractères'):
        S.stockView==='produit'?'Recherche, micro, scan code (caméra), mouvements de stock':
        'Voir le contenu d\'un emplacement'
      ),
      content
    )
  );
  requestAnimationFrame(()=>{
    initStockSearchBar();
    if(S.stockView==='produit')wireStockAddEmplCombo();
  });
  return h('div',null,
    S.sidebarOpen?h('div',{className:'sidebar-overlay',onClick:closeSidebar}):null,
    h('div',{className:'app'},sidebar,
      mainEl
    ),
  );
}

// ── MyCompta (placeholder v0) ─────────────────────────────────────
// ══════════════════════════════════════════════════════════════════
// ── PAIE (onglet MyCompta) ────────────────────────────────────────
// ══════════════════════════════════════════════════════════════════
const PAIE_MOIS_FR=['','Janvier','Février','Mars','Avril','Mai','Juin','Juillet','Août','Septembre','Octobre','Novembre','Décembre'];

const PAIE_SECTIONS=[
  {title:'📋 Contrat & Salaire',fields:[
    {key:'matricule',       label:'Matricule',          type:'text',   fixed:true},
    {key:'contrat_type',    label:'Type de contrat',    type:'select', fixed:true, opts:['CDI','CDD','Intérim','Stage','Apprentissage']},
    {key:'date_debut',      label:'Date de début',      type:'date',   fixed:true},
    {key:'date_fin',        label:'Date de fin',        type:'date',   fixed:true},
    {key:'nb_heures_base',  label:'Heures de base',     type:'number', fixed:true, step:'0.01'},
    {key:'taux_horaire',    label:'Taux horaire (€)',   type:'number', fixed:true, step:'0.01'},
    {key:'salaire_mensuel', label:'Salaire mensuel (€)',type:'number', fixed:true, step:'0.01'},
    {key:'mutuelle',        label:'Mutuelle',           type:'select', fixed:true, opts:['Non','Oui']},
    {key:'avantage_voiture',label:'Avantage voiture (€)',type:'number',fixed:true, step:'0.01'},
    {key:'prime_anciennete',label:'Prime ancienneté (%)',type:'number',fixed:true, step:'0.01'},
  ]},
  {title:'⏱ Heures & Compteurs',fields:[
    {key:'compteur_hs_m1',              label:'Compteur HS M-1',        type:'text'},
    {key:'nb_heures_payer',             label:'Nb heures à payer',      type:'number',step:'0.01'},
    {key:'heures_nuit',                 label:'Heures de nuit',         type:'text'},
    {key:'heures_nuit_ferie',           label:'Nuit férié',             type:'text'},
    {key:'heures_nuit_dimanche',        label:'Nuit dimanche',          type:'text'},
    {key:'heures_nuit_dimanche_ferie',  label:'Nuit dim. férié',        type:'text'},
    {key:'heures_sup_25',               label:'Heures sup 25%',         type:'text'},
    {key:'heures_sup_50',               label:'Heures sup 50%',         type:'text'},
    {key:'heures_sup_nuit',             label:'Heures sup nuit',        type:'text'},
    {key:'heures_ferie',                label:'Heures j. férié (+150%)',type:'text'},
  ]},
  {title:'💰 Primes & Commissions',fields:[
    {key:'augmentation_salaire', label:'Augmentation salaire (€)',  type:'number',step:'0.01'},
    {key:'commissions_ventes',   label:'Commissions ventes (€)',    type:'number',step:'0.01'},
    {key:'prime_objectifs',      label:"Prime d'objectifs (€)",     type:'number',step:'0.01'},
    {key:'prime_inflation',      label:'Prime inflation (€)',       type:'number',step:'0.01'},
    {key:'prime_exceptionnelle', label:'Prime exceptionnelle (€)',  type:'number',step:'0.01'},
    {key:'prime_equipe',         label:'Prime équipe (€)',          type:'number',step:'0.01'},
    {key:'panier',               label:'Panier (6,47€/j)',          type:'number',step:'0.01'},
    {key:'solde_tout_compte',    label:'Solde tout compte',         type:'select', opts:['','Oui','Non']},
  ]},
  {title:'🏖 Absences',fields:[
    {key:'absence_heures',          label:'Absence (heures)',          type:'text'},
    {key:'absence_maladie_heures',  label:'Maladie (heures)',          type:'text'},
    {key:'absence_maladie_jours',   label:'Maladie (jours)',           type:'text'},
    {key:'absence_deces_mariage',   label:'Décès / Mariage',          type:'text'},
    {key:'absence_cp_heures',       label:'Congés payés (h)',          type:'text'},
    {key:'absence_cp_jours',        label:'Congés payés (j)',          type:'text'},
    {key:'date_conges_payes',       label:'Dates des CP',              type:'text'},
    {key:'absence_rtt',             label:'RTT',                       type:'text'},
    {key:'absence_css_heures',      label:'Congés sans solde (h)',     type:'text'},
    {key:'absence_css_jours',       label:'Congés sans solde (j)',     type:'text'},
    {key:'absence_non_justifie_h',  label:'Non justifiée (h)',         type:'text'},
    {key:'absence_non_justifie_j',  label:'Non justifiée (j)',         type:'text'},
    {key:'absence_justifiee_np_h',  label:'Justifiée non payée (h)',   type:'text'},
    {key:'absence_justifiee_np_j',  label:'Justifiée non payée (j)',   type:'text'},
    {key:'absence_at_heures',       label:'AT (heures)',               type:'text'},
    {key:'absence_at_jours',        label:'AT (jours)',                type:'text'},
    {key:'mi_temps_therapeutique',  label:'Mi-temps thérapeutique',   type:'text'},
    {key:'absence_chomage_partiel', label:'Chômage partiel',          type:'text'},
    {key:'absence_conge_parentale', label:'Congé parental',           type:'text'},
  ]},
  {title:'💳 Frais & Divers',fields:[
    {key:'frais_pro',           label:'Frais pro (€)',            type:'number',step:'0.01'},
    {key:'frais_transport',     label:'Remb. transport (€)',      type:'number',step:'0.01'},
    {key:'pret_sifa',           label:'Prêt SIFA (€)',            type:'number',step:'0.01'},
    {key:'atd',                 label:'ATD (€)',                  type:'number',step:'0.01'},
    {key:'acompte_exceptionnel',label:'Acompte exceptionnel (€)', type:'number',step:'0.01'},
  ]},
  {title:'📝 Information',fields:[
    {key:'information',label:'Note libre',type:'textarea',full:true},
  ]},
];

async function paieLoadEmployes(){
  if(S.paieEmpLoaded) return;
  try{
    const d=await api('/api/paie/employes');
    S.paieEmployes=d.employes||[];
    S.paieEmpLoaded=true;
    render();
  }catch(e){toast('Erreur chargement employés: '+e.message,'error');}
}

async function paieLoadVars(){
  const pk=S.paieAnnee+'_'+S.paieMois;
  if(S.paieVarsCache[pk]!==undefined) return;
  S.paieVarsCache[pk]={};
  try{
    const d=await api('/api/paie/variables/'+S.paieAnnee+'/'+S.paieMois);
    S.paieVarsCache[pk]=d.variables||{};
  }catch(e){}
}

function paieGetFixed(userId){
  const pk=S.paieAnnee+'_'+S.paieMois;
  // Priorité aux données fixes historiques pour ce mois, sinon les données globales
  const cached=((S.paieVarsCache[pk]||{})[String(userId)]||{}).fixed||{};
  const e=S.paieEmployes.find(x=>x.user_id===userId)||{};
  return {
    matricule:cached.matricule??e.matricule,
    contrat_type:cached.contrat_type??e.contrat_type??'CDI',
    date_debut:cached.date_debut??e.date_debut,
    date_fin:cached.date_fin??e.date_fin,
    nb_heures_base:cached.nb_heures_base??e.nb_heures_base,
    taux_horaire:cached.taux_horaire??e.taux_horaire,
    salaire_mensuel:cached.salaire_mensuel??e.salaire_mensuel,
    prime_anciennete:cached.prime_anciennete??e.prime_anciennete,
    mutuelle:cached.mutuelle??e.mutuelle??'Non',
    avantage_voiture:cached.avantage_voiture??e.avantage_voiture
  };
}
function paieGetVar(userId){
  const pk=S.paieAnnee+'_'+S.paieMois;
  const cached=((S.paieVarsCache[pk]||{})[String(userId)]||{}).data||{};
  return {...cached,...(S.paiePendingVar[userId]||{})};
}

async function paieSaveEmp(userId,btnEl){
  if(btnEl){btnEl.disabled=true;btnEl.textContent='Enregistrement…';}
  try{
    const isReadonly=S.paieMonthReadonly;
    
    // Si mois passé, ne pas sauvegarder les données fixes (elles sont historiques)
    if(!isReadonly){
      const fixPending=S.paiePendingFixed[userId]||{};
      const emp=S.paieEmployes.find(x=>x.user_id===userId)||{};
      const fixBody={
        matricule:fixPending.matricule??emp.matricule,
        contrat_type:fixPending.contrat_type??emp.contrat_type,
        date_debut:fixPending.date_debut??emp.date_debut,
        date_fin:fixPending.date_fin??emp.date_fin,
        nb_heures_base:fixPending.nb_heures_base??emp.nb_heures_base,
        taux_horaire:fixPending.taux_horaire??emp.taux_horaire,
        salaire_mensuel:fixPending.salaire_mensuel??emp.salaire_mensuel,
        prime_anciennete:fixPending.prime_anciennete??emp.prime_anciennete,
        mutuelle:fixPending.mutuelle??emp.mutuelle,
        avantage_voiture:fixPending.avantage_voiture??emp.avantage_voiture,
      };
      await api('/api/paie/employes/'+userId+'/fixed',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(fixBody)});
      Object.assign(emp,fixBody);
    }
    
    // Sauvegarder toujours les variables (même pour mois passés si on veut corriger une erreur)
    const varData=paieGetVar(userId);
    await api('/api/paie/variables/'+S.paieAnnee+'/'+S.paieMois+'/'+userId,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({data:varData})});
    const pk=S.paieAnnee+'_'+S.paieMois;
    if(!S.paieVarsCache[pk])S.paieVarsCache[pk]={};
    S.paieVarsCache[pk][String(userId)]={data:varData};
    
    delete S.paiePendingFixed[userId];
    delete S.paiePendingVar[userId];
    toast('Enregistré','success');
    if(btnEl){btnEl.disabled=false;btnEl.textContent='✅ Enregistré';btnEl.className='paie-svbtn saved';setTimeout(()=>{if(btnEl){btnEl.textContent='💾 Enregistrer';btnEl.className='paie-svbtn';}},2500);}
    render();
  }catch(e){
    toast('Erreur: '+e.message,'error');
    if(btnEl){btnEl.disabled=false;btnEl.textContent='💾 Enregistrer';}
  }
}

async function paieExport(){
  S.paieExporting=true;render();
  try{
    const r=await fetch('/api/paie/export/'+S.paieAnnee+'/'+S.paieMois,{credentials:'include'});
    if(!r.ok)throw new Error('Erreur '+r.status);
    const blob=await r.blob();
    const a=document.createElement('a');
    a.href=URL.createObjectURL(blob);
    a.download='paie_'+S.paieAnnee+'_'+String(S.paieMois).padStart(2,'0')+'_'+PAIE_MOIS_FR[S.paieMois]+'.xlsx';
    a.click();
    toast('Export téléchargé','success');
  }catch(e){toast('Export échoué: '+e.message,'error');}
  S.paieExporting=false;render();
}

async function paieShowHistory(){
  S.paieShowHist=true;S.paieHistData=null;render();
  try{
    const d=await api('/api/paie/historique');
    S.paieHistData=d.periodes||[];
    render();
  }catch(e){S.paieHistData=[];render();}
}

function paieChangePeriod(delta){
  let m=S.paieMois+delta,y=S.paieAnnee;
  if(m<1){m=12;y--;}if(m>12){m=1;y++;}
  S.paieMois=m;S.paieAnnee=y;
  S.paiePendingVar={};
  paieLoadVars().then(()=>render());
}

function renderPaieForm(userId){
  const emp=S.paieEmployes.find(x=>x.user_id===userId);
  if(!emp)return h('div',{className:'paie-ph'},'Employé introuvable');
  const varD=paieGetVar(userId);
  const fixD=paieGetFixed(userId);
  const wrap=h('div',null);
  // Header
  const btnSave=h('button',{className:'paie-svbtn'});
  btnSave.textContent='💾 Enregistrer';
  btnSave.onclick=()=>paieSaveEmp(userId,btnSave);
  const meta=h('div',{className:'paie-emp-hdr-meta'});
  [emp.contrat_type||'CDI', emp.salaire_mensuel?Number(emp.salaire_mensuel).toLocaleString('fr-FR')+' €':null, emp.date_debut?'Depuis '+emp.date_debut:null].filter(Boolean)
    .forEach(t=>{const b=h('span',{className:'paie-badge'});b.textContent=t;meta.appendChild(b);});
  const nm=h('div',{className:'paie-emp-hdr-name'});nm.textContent=emp.nom_complet||'';
  const nmWrap=h('div',null,nm,meta);
  const hdr=h('div',{className:'paie-emp-hdr'},nmWrap,btnSave);
  wrap.appendChild(hdr);
  // Sections
  PAIE_SECTIONS.forEach(sec=>{
    const sEl=h('div',{className:'paie-sec'});
    const tEl=h('div',{className:'paie-sec-title'});tEl.textContent=sec.title;sEl.appendChild(tEl);
    const grid=h('div',{className:'paie-fgrid'});
    sec.fields.forEach(f=>{
      const cell=h('div',{className:'paie-f'+(f.full?' full':'')});
      const lbl=h('div',{className:'paie-flbl'});lbl.textContent=f.label;cell.appendChild(lbl);
      const val=f.fixed?(fixD[f.key]??''):(varD[f.key]??'');
      let inp;
      if(f.type==='select'){
        inp=document.createElement('select');
        (f.opts||[]).forEach(o=>{const op=document.createElement('option');op.value=o;op.textContent=o;if(String(val)===o)op.selected=true;inp.appendChild(op);});
      }else if(f.type==='textarea'){
        inp=document.createElement('textarea');inp.value=val||'';
      }else{
        inp=document.createElement('input');inp.type=f.type||'text';if(f.step)inp.step=f.step;inp.value=val!=null?val:'';
      }
      inp.addEventListener('input',()=>{
        if(f.fixed){if(!S.paiePendingFixed[userId])S.paiePendingFixed[userId]={};S.paiePendingFixed[userId][f.key]=inp.value;}
        else{if(!S.paiePendingVar[userId])S.paiePendingVar[userId]={};S.paiePendingVar[userId][f.key]=inp.value;}
      });
      cell.appendChild(inp);grid.appendChild(cell);
    });
    sEl.appendChild(grid);wrap.appendChild(sEl);
  });
  return wrap;
}

function renderPaieEmployeeList(){
  const tokens=(S.paieEmpSearch||'').toLowerCase().trim().split(/\s+/).filter(Boolean);
  const scoreM=(hay,toks)=>{if(!toks.length)return 1;const h2=(hay||'').toLowerCase();let s=0;for(const t of toks)if(h2.includes(t))s+=(h2.startsWith(t)?2:1);return s;};
  let list=S.paieEmployes.filter(e=>{if(!tokens.length)return true;return scoreM([e.nom_complet,e.contrat_type,e.email].join(' '),tokens)>0;})
    .sort((a,b)=>{if(!tokens.length)return(a.nom_complet||'').localeCompare(b.nom_complet||'','fr');const sa=scoreM([a.nom_complet,a.contrat_type].join(' '),tokens);const sb=scoreM([b.nom_complet,b.contrat_type].join(' '),tokens);return sb-sa;});
  const ul=h('div',{className:'paie-emp-list'});
  if(!list.length){const em=h('div',{style:{padding:'12px',fontSize:'11px',color:'var(--muted)',textAlign:'center'}});em.textContent='Aucun résultat';ul.appendChild(em);return ul;}
  list.forEach(emp=>{
    const div=h('div',{className:'paie-emp-item'+(emp.user_id===S.paieCurrentEmpId?' active':'')});
    const dirty=!!(S.paiePendingVar[emp.user_id]||S.paiePendingFixed[emp.user_id]);
    const nm=h('div',{className:'paie-emp-name'});nm.textContent=emp.nom_complet||(emp.nom+' '+emp.prenom);
    if(dirty){const dot=h('span',{className:'paie-unsaved'});nm.appendChild(dot);}
    const sub=h('div',{className:'paie-emp-sub'});sub.textContent=(emp.contrat_type||'CDI')+' · '+(emp.email||'');
    div.appendChild(nm);div.appendChild(sub);
    div.onclick=()=>{S.paieCurrentEmpId=emp.user_id;render();};
    ul.appendChild(div);
  });
  return ul;
}

function renderPaieTab(){
  // Load data if needed
  if(!S.paieEmpLoaded){paieLoadEmployes();return h('div',{className:'paie-ph'},'Chargement…');}

  // Déterminer le type de mois (passé, en cours, futur)
  const now=new Date();
  const currentYear=now.getFullYear();
  const currentMonth=now.getMonth()+1;
  let monthStatus='';
  let monthStatusColor='';
  if(S.paieAnnee<currentYear||(S.paieAnnee===currentYear&&S.paieMois<currentMonth)){
    monthStatus='Mois passé - Lecture seule';
    monthStatusColor='var(--warn)';
  }else if(S.paieAnnee===currentYear&&S.paieMois===currentMonth){
    monthStatus='Mois en cours';
    monthStatusColor='var(--ok)';
  }else{
    monthStatus='Mois futur';
    monthStatusColor='var(--accent)';
  }
  S.paieMonthStatus=monthStatus;
  S.paieMonthReadonly=(monthStatus==='Mois passé - Lecture seule');

  // Period bar
  const periodStr=PAIE_MOIS_FR[S.paieMois]+' '+S.paieAnnee;
  const prevBtn=h('button',{className:'paie-pbtn',onClick:()=>paieChangePeriod(-1)});prevBtn.textContent='‹';
  const nextBtn=h('button',{className:'paie-pbtn',onClick:()=>paieChangePeriod(+1)});nextBtn.textContent='›';
  const lbl=h('div',{className:'paie-plbl'});lbl.textContent=periodStr;
  const histBtn=h('button',{className:'paie-hist-btn',onClick:paieShowHistory});histBtn.innerHTML=icon('clock',13)+' Historique';
  const xBtn=h('button',{className:'paie-xbtn',disabled:S.paieExporting,onClick:paieExport});
  xBtn.innerHTML=icon('download',13)+' Exporter Excel';
  if(S.paieExporting)xBtn.innerHTML='Génération…';
  const periodBar=h('div',{className:'paie-period-bar'},h('div',{className:'paie-period-nav'},prevBtn,lbl,nextBtn),histBtn,xBtn);

  // Employee list panel
  const srch=h('input',{type:'search',placeholder:'Rechercher un employé…',style:{width:'100%',padding:'7px 10px',background:'var(--bg)',border:'1.5px solid var(--border)',borderRadius:'8px',color:'var(--text)',fontSize:'12px',fontFamily:'inherit',outline:'none'}});
  srch.value=S.paieEmpSearch||'';
  srch.addEventListener('input',()=>{S.paieEmpSearch=srch.value;const list=srch.closest('.paie-layout').querySelector('.paie-emp-list');if(list){const ul=renderPaieEmployeeList();list.replaceWith(ul);}});
  const hint=h('div',{className:'paie-emp-hint'});hint.textContent='Cherchez par nom, prénom ou contrat';
  const empHead=h('div',{className:'paie-emp-head'},srch,hint);
  const empList=renderPaieEmployeeList();
  const empPanel=h('div',{className:'paie-emp-panel'},empHead,empList);

  // Right column
  const formScroll=h('div',{className:'paie-form-scroll'});
  if(S.paieCurrentEmpId){
    formScroll.appendChild(renderPaieForm(S.paieCurrentEmpId));
  }else{
    const ph=h('div',{className:'paie-ph'});ph.textContent='← Sélectionnez un employé';
    formScroll.appendChild(ph);
  }
  const formCol=h('div',{className:'paie-form-col'},periodBar,formScroll);
  const layout=h('div',{className:'paie-layout'},empPanel,formCol);

  // History modal
  if(S.paieShowHist){
    const histEl=h('div',{className:'paie-hist-modal'});
    histEl.onclick=(e)=>{if(e.target===histEl){S.paieShowHist=false;render();}};
    const card=h('div',{className:'paie-hist-card'});
    const htit=h('div',{style:{fontSize:'14px',fontWeight:800,marginBottom:'12px'}});htit.textContent='📋 Historique des périodes';
    const hlist=h('div',{style:{overflowY:'auto',flex:1}});
    if(S.paieHistData===null){const ld=h('div',{style:{padding:'12px',color:'var(--muted)',fontSize:'12px'}});ld.textContent='Chargement…';hlist.appendChild(ld);}
    else if(!S.paieHistData.length){const em=h('div',{style:{padding:'12px',color:'var(--muted)',fontSize:'12px'}});em.textContent='Aucune période enregistrée.';hlist.appendChild(em);}
    else{S.paieHistData.forEach(p=>{const active=p.annee===S.paieAnnee&&p.mois===S.paieMois;const it=h('div',{className:'paie-hist-item'+(active?' active':'')});const ilab=h('div');const iname=h('div',{style:{fontSize:'13px',fontWeight:700,color:'var(--accent)'}});iname.textContent=p.mois_label+' '+p.annee;const isub=h('div',{style:{fontSize:'11px',color:'var(--muted)'}});isub.textContent=p.nb_employes+' employé(s) · '+(p.last_update||'').slice(0,10);ilab.append(iname,isub);const iact=h('span',{style:{fontSize:'11px',color:'var(--accent)'}});iact.textContent=active?'✓ Période actuelle':'→ Aller';it.append(ilab,iact);it.onclick=()=>{S.paieAnnee=p.annee;S.paieMois=p.mois;S.paiePendingVar={};S.paieShowHist=false;paieLoadVars().then(()=>render());};hlist.appendChild(it);});}
    const closeBtn=h('button',{style:{marginTop:'12px',padding:'9px',borderRadius:'8px',border:'1px solid var(--border)',background:'transparent',color:'var(--text2)',cursor:'pointer',fontFamily:'inherit',fontSize:'12px',width:'100%'},onClick:()=>{S.paieShowHist=false;render();}});closeBtn.textContent='Fermer';
    card.append(htit,hlist,closeBtn);histEl.appendChild(card);
    return h('div',null,layout,histEl);
  }
  return layout;
}

function closeComptaAcheteurModal(){set({comptaEditAcheteurId:null});}
function closeComptaCompteModal(){set({comptaEditCompteId:null});}
function closeComptaBanqueModal(){set({comptaEditBanqueId:null});}

function renderComptaBanqueModal(){
  const editId=S.comptaEditBanqueId;
  if(!editId)return null;
  const cur=(S.comptaBanques||[]).find(x=>String(x.id)===String(editId));
  if(!cur)return null;
  const codeI=h('input',{type:'text',placeholder:'Code vendeur (ex: 98, 100)',value:cur.code_vendeur||''});
  const numI=h('input',{type:'text',placeholder:'Numéro de compte',value:cur.numero_compte||''});
  const libI=h('input',{type:'text',placeholder:'Libellé (optionnel)',value:cur.libelle||''});
  const overlay=h('div',{className:'add-row-modal',style:{zIndex:12000}});
  overlay.addEventListener('click',e=>{if(e.target===overlay)closeComptaBanqueModal();});
  const form=h('div',{className:'add-row-form',style:{maxWidth:'560px'},onClick:e=>e.stopPropagation()},
    h('button',{type:'button',className:'add-row-close',onClick:closeComptaBanqueModal},'×'),
    h('h3',null,'Modifier un code de banque'),
    h('div',{className:'form-row'},
      h('div',null,h('label',null,'Code vendeur'),codeI),
      h('div',null,h('label',null,'Numéro de compte'),numI)
    ),
    h('div',{className:'form-row'},
      h('div',{style:{gridColumn:'span 2'}},h('label',null,'Libellé'),libI)
    ),
    h('div',{className:'form-actions'},
      h('button',{type:'button',className:'btn-ghost',onClick:closeComptaBanqueModal},'Annuler'),
      h('button',{type:'button',className:'btn-sm',onClick:()=>{
        const payload={code_vendeur:codeI.value,numero_compte:numI.value,libelle:libI.value||null};
        if(!payload.code_vendeur||!payload.numero_compte){toast('Code vendeur et numéro de compte obligatoires','error');return;}
        comptaUpdateBanque(editId,payload);
      }},'Enregistrer')
    )
  );
  overlay.appendChild(form);
  return overlay;
}

function renderComptaAcheteurModal(){
  const editId=S.comptaEditAcheteurId;
  if(!editId)return null;
  const cur=(S.comptaAcheteurs||[]).find(x=>String(x.id)===String(editId));
  if(!cur)return null;
  const codeI=h('input',{type:'text',placeholder:'Code vendeur (optionnel)',value:cur.code_vendeur||''});
  const numCompteI=h('input',{type:'text',placeholder:'Numéro de compte',value:cur.identifiant||''});
  const rsI=h('input',{type:'text',placeholder:'Raison sociale',value:cur.raison_sociale||''});
  const overlay=h('div',{className:'add-row-modal',style:{zIndex:12000}});
  overlay.addEventListener('click',e=>{if(e.target===overlay)closeComptaAcheteurModal();});
  const form=h('div',{className:'add-row-form',style:{maxWidth:'560px'},onClick:e=>e.stopPropagation()},
    h('button',{type:'button',className:'add-row-close',onClick:closeComptaAcheteurModal},'×'),
    h('h3',null,'Modifier un acheteur'),
    h('div',{className:'form-row'},
      h('div',null,h('label',null,'Code vendeur'),codeI),
      h('div',null,h('label',null,'Numéro de compte'),numCompteI)
    ),
    h('div',{className:'form-row'},
      h('div',{style:{gridColumn:'span 2'}},h('label',null,'Raison sociale'),rsI)
    ),
    h('div',{className:'form-actions'},
      h('button',{type:'button',className:'btn-ghost',onClick:closeComptaAcheteurModal},'Annuler'),
      h('button',{type:'button',className:'btn-sm',onClick:()=>{
        const payload={code_vendeur:codeI.value||null,identifiant:numCompteI.value,raison_sociale:rsI.value};
        if(!payload.identifiant||!payload.raison_sociale){toast('Numéro de compte et raison sociale obligatoires','error');return;}
        comptaUpdateAcheteur(editId,payload);
      }},'Enregistrer')
    )
  );
  overlay.appendChild(form);
  return overlay;
}

function renderComptaCompteModal(){
  const editId=S.comptaEditCompteId;
  if(!editId)return null;
  const cur=(S.comptaComptes||[]).find(x=>String(x.id)===String(editId));
  if(!cur)return null;
  const libI=h('input',{type:'text',placeholder:'Libellé condensé',value:cur.libelle_condense||''});
  const numI=h('input',{type:'text',placeholder:'Numéro de compte',value:cur.numero_compte||''});
  const overlay=h('div',{className:'add-row-modal',style:{zIndex:12000}});
  overlay.addEventListener('click',e=>{if(e.target===overlay)closeComptaCompteModal();});
  const form=h('div',{className:'add-row-form',style:{maxWidth:'560px'},onClick:e=>e.stopPropagation()},
    h('button',{type:'button',className:'add-row-close',onClick:closeComptaCompteModal},'×'),
    h('h3',null,'Modifier un compte'),
    h('div',{className:'form-row'},
      h('div',null,h('label',null,'Libellé condensé'),libI),
      h('div',null,h('label',null,'Numéro de compte'),numI)
    ),
    h('div',{className:'form-actions'},
      h('button',{type:'button',className:'btn-ghost',onClick:closeComptaCompteModal},'Annuler'),
      h('button',{type:'button',className:'btn-sm',onClick:()=>{
        const payload={libelle_condense:libI.value,numero_compte:numI.value};
        if(!payload.libelle_condense||!payload.numero_compte){toast('Libellé et numéro de compte obligatoires','error');return;}
        comptaUpdateCompte(editId,payload);
      }},'Enregistrer')
    )
  );
  overlay.appendChild(form);
  return overlay;
}

function renderCompta(){
  const isLight=document.body.classList.contains('light');
  const tab = S.comptaTab || 'factor';
  const sidebar=h('nav',{className:'sidebar'},
    h('div',{className:'logo'},
      h('div',{className:'logo-row'},
        h('div',{className:'logo-brand'},'My',h('span',null,'Compta')),
      ),
      h('div',{className:'logo-sub'},'by SIFA')
    ),
    h('div',{className:'nav-scroll tabs',style:{width:'100%',margin:0}},
      h('div',{className:'nav-group-label'},'Import'),
      h('button',{className:'nav-btn'+(tab==='factor'?' active':''),onClick:()=>{set({comptaTab:'factor'});}},
        iconEl('upload',15),'  Import Factor'),
      h('button',{className:'nav-btn'+(tab==='acheteurs'?' active':''),onClick:()=>{set({comptaTab:'acheteurs'});loadComptaAcheteurs();}},
        iconEl('users',15),'  Acheteurs'),
      h('button',{className:'nav-btn'+(tab==='comptes'?' active':''),onClick:()=>{set({comptaTab:'comptes'});loadComptaComptes();}},
        iconEl('file',15),'  Table des comptes'),
      h('button',{className:'nav-btn'+(tab==='banques'?' active':''),onClick:()=>{set({comptaTab:'banques'});loadComptaBanques();}},
        iconEl('credit-card',15),'  Code de banque'),
      h('div',{className:'nav-group-label'},'Autres modules'),
      h('button',{className:'nav-btn'+(tab==='cession'?' active':''),onClick:()=>{set({comptaTab:'cession'});}},
        iconEl('clock',15),'  Cession (en cours)'),
      h('button',{className:'nav-btn'+(tab==='paie'?' active':''),onClick:()=>{if(!S.paieEmpLoaded){paieLoadEmployes();}paieLoadVars().then(()=>render());set({comptaTab:'paie'});}},
        iconEl('credit-card',15),'  Paies')
    ),
    h('div',{className:'sidebar-bottom'},
      h('button',{className:'nav-btn back-mysifa',onClick:()=>{window.location.href='/' }},
        '← Retour ',
        h('span',{className:'wm'},'My',h('span',null,'Sifa'))
      ),
      sidebarUserChip(S.user),
      (() => {
        const b=h('button',{
          className:'support-btn',
          title:'Contacter le support',
          onClick:()=>set({contactOpen:true})
        });
        const ico=h('span',{className:'support-ico'});
        try{
          ico.innerHTML=(window.MySifaSupport && typeof window.MySifaSupport.iconSvg==='function')?window.MySifaSupport.iconSvg():'';
        }catch(e){ ico.innerHTML=''; }
        b.appendChild(ico);
        b.appendChild(h('span',null,'Contacter le support'));
        return b;
      })(),
      h('button',{
        className:'theme-btn',
        onClick:()=>{MySifaTheme.toggleMode();render();},
        title:'Changer le thème'
      },
        h('span',{className:'theme-ico'},iconEl(isLight?'sun':'moon',16)),
        h('span',{className:'theme-label'},isLight?'Mode clair':'Mode sombre')
      ),
      h('button',{className:'logout-btn',onClick:doLogout},iconEl('log-out',14),' Déconnexion')
    )
  );

  const topbar=h('div',{className:'mobile-topbar'},
    h('button',{type:'button',className:'mobile-menu-btn',onClick:toggleSidebar,'aria-label':'Menu'},iconEl('menu',20)),
    h('div',null,
      h('div',{className:'mobile-topbar-title'},'MyCompta'),
      h('div',{className:'mobile-topbar-sub'},'Comptabilité')
    ),
    h('button',{type:'button',className:'mobile-home-btn',onClick:()=>{window.location.href='/'},'aria-label':'Accueil'},iconEl('home',20))
  );

  let content;
  if(tab==='factor'){
    const factorMode=S.comptaFactorMode||'file';
    const modeBar=h('div',{style:{display:'flex',gap:'8px',marginBottom:'12px',flexWrap:'wrap'}},
      h('button',{className:factorMode==='file'?'btn-sm':'btn-ghost btn-sm',type:'button',onClick:()=>set({comptaFactorMode:'file'})},
        iconEl('upload',13),' Fichier'),
      h('button',{className:factorMode==='paste'?'btn-sm':'btn-ghost btn-sm',type:'button',onClick:()=>set({comptaFactorMode:'paste'})},
        iconEl('clipboard',13),' Coller')
    );
    const inp=h('input',{type:'file',accept:'.xlsx,.xlsm,.xls,.csv,.txt',style:{display:'none'}});
    const zone=h('div',{className:'drop-zone',style:{marginBottom:'16px'}},
      h('div',{className:'dz-icon'},iconEl('cloud-upload',36)),
      h('div',{className:'dz-title'},'Dépose le fichier Factor'),
      h('div',{className:'dz-sub'},'Excel (.xlsx, .xls) ou CSV (.csv)')
    );
    zone.addEventListener('click',()=>inp.click());
    zone.addEventListener('dragover',e=>{e.preventDefault();zone.classList.add('drag');});
    zone.addEventListener('dragleave',()=>zone.classList.remove('drag'));
    zone.addEventListener('drop',e=>{
      e.preventDefault();zone.classList.remove('drag');
      const f=e.dataTransfer.files[0];if(f)comptaTransform(f);
    });
    inp.addEventListener('change',e=>{const f=e.target.files[0];if(f)comptaTransform(f);});
    const pasteTa=h('textarea',{
      className:'form-sel',
      style:{width:'100%',minHeight:'180px',fontFamily:'ui-monospace,monospace',fontSize:'12px',resize:'vertical',boxSizing:'border-box'},
      placeholder:'Collez ici les lignes Factor (ligne d\'en-tête incluse). Séparateur ; , ou tabulation.',
      value:S.comptaPasteText||''
    });
    pasteTa.addEventListener('input',e=>{S.comptaPasteText=e.target.value;});
    const pasteFromClip=h('button',{className:'btn-ghost btn-sm',type:'button',onClick:async()=>{
      try{
        const t=await navigator.clipboard.readText();
        S.comptaPasteText=t||'';
        set({comptaPasteText:S.comptaPasteText});
      }catch(e){toast('Impossible de lire le presse-papiers','error');}
    }},iconEl('clipboard',13),' Lire le presse-papiers');
    const pasteGo=h('button',{className:'btn-sm',type:'button',onClick:()=>comptaTransformPaste(pasteTa.value)},
      iconEl('upload',13),' Transformer');
    const pasteBlock=h('div',{className:'card',style:{marginBottom:'16px',padding:'14px 18px'}},
      h('div',{style:{fontSize:'13px',fontWeight:'600',color:'var(--text)',marginBottom:'8px'}},'Coller les lignes Factor'),
      h('div',{style:{fontSize:'12px',color:'var(--muted)',marginBottom:'10px',lineHeight:'1.5'}},
        'Copiez les lignes depuis Factor ou Excel, puis collez-les ci-dessous (en-têtes requis).'),
      pasteTa,
      h('div',{style:{display:'flex',gap:'8px',marginTop:'10px',flexWrap:'wrap'}},pasteFromClip,pasteGo)
    );
    const importBlock=factorMode==='paste'?pasteBlock:zone;

    const r=S.comptaResult;
    const miss=r && r.missing ? r.missing : null;
    const missBox = miss ? h('div',{className:'card',style:{marginBottom:'16px'}},
      h('div',{className:'card-header'},h('h3',null,'Contrôles')),
      h('div',{style:{padding:'14px 18px',fontSize:'12px',color:'var(--muted)',lineHeight:'1.6'}},
        (miss.comptes && miss.comptes.length)
          ? h('div',null,
              h('div',{style:{fontWeight:'700',color:'var(--text)',marginBottom:'6px'}},'Libellés manquants dans Table des comptes'),
              ...miss.comptes.slice(0,12).map(x=>h('div',null,'- ',x.libelle_key,' (',x.count,')'))
            )
          : h('div',null,'✅ Aucun libellé manquant dans la table des comptes.'),
        h('div',{style:{height:'10px'}}),
        (miss.acheteurs && miss.acheteurs.length)
          ? h('div',null,
              h('div',{style:{fontWeight:'700',color:'var(--text)',marginBottom:'6px'}},'Acheteurs non reconnus'),
              ...miss.acheteurs.slice(0,12).map(x=>h('div',null,'- ',x.buyer,' (',x.count,')'))
            )
          : h('div',null,'✅ Aucun acheteur manquant.'),
        h('div',{style:{height:'10px'}}),
        (miss.banques && miss.banques.length)
          ? h('div',null,
              h('div',{style:{fontWeight:'700',color:'var(--text)',marginBottom:'6px'}},'Codes vendeur sans compte CAF (Code de banque)'),
              ...miss.banques.slice(0,12).map(x=>h('div',null,'- ',x.code_vendeur,' (',x.count,')'))
            )
          : h('div',null,'✅ Tous les codes vendeur ont un compte CAF.')
      )
    ) : null;

    const cw = r && r.cw_text ? r.cw_text : '';
    const copyBtn=h('button',{className:'btn-sm',onClick:async()=>{
      try{ await navigator.clipboard.writeText(cw); toast('Copié pour CW'); }
      catch(e){ toast('Impossible de copier','error'); }
    }},iconEl('copy',13),' Copier pour CW');

    function fmtAmt(v){
      const n = (typeof v==='number') ? v : (v==null?0:Number(v));
      if(!isFinite(n) || n===0) return '';
      try{
        return new Intl.NumberFormat('fr-FR',{minimumFractionDigits:0,maximumFractionDigits:2}).format(n);
      }catch(e){
        return String(n);
      }
    }

    const rows = (r && Array.isArray(r.rows)) ? r.rows : [];
    const tbl = rows.length ? (()=>{
      const head=h('thead',null,
        h('tr',null,
          h('th',null,'Date'),
          h('th',null,'Code vendeur'),
          h('th',null,'Compte'),
          h('th',null,'Libellé'),
          h('th',null,'Débit'),
          h('th',null,'Crédit')
        )
      );
      const body=h('tbody',null,
        ...rows.map((rr,idx)=>{
          const pb = rr && rr.problem ? String(rr.problem) : '';
          const cls = pb ? ('cw-row-bad') : '';
          const title = pb
            ? ((pb==='compte_manquant'?'Compte manquant (Table des comptes)'
              : pb==='banque_manquante'?'Compte CAF manquant (Code de banque)'
              : 'Acheteur non reconnu') + (rr.problem_detail?(' — '+rr.problem_detail):''))
            : '';
          return h('tr',{className:cls, title},
            h('td',null, rr.date||''),
            h('td',null, rr.code_vendeur||''),
            h('td',null, rr.compte||''),
            h('td',null, rr.libelle||''),
            h('td',null, fmtAmt(rr.debit)),
            h('td',null, fmtAmt(rr.credit))
          );
        })
      );

      const table=h('table',{style:{minWidth:'980px'}}, head, body);
      const top=h('div',{className:'tbl-scroll top'}); // barre de scroll horizontale
      const bot=h('div',{className:'tbl-scroll bot'}, table);
      top.addEventListener('scroll',()=>{ bot.scrollLeft = top.scrollLeft; });
      bot.addEventListener('scroll',()=>{ top.scrollLeft = bot.scrollLeft; });
      // sync initial width
      requestAnimationFrame(()=>{ top.scrollLeft = bot.scrollLeft; });
      return h('div',{className:'cw-table'},
        top,
        bot
      );
    })() : h('div',{className:'card-empty'},'Aucun résultat. Importez un fichier ou collez des lignes.');

    content=h('div',null, modeBar, importBlock, inp,
      missBox,
      h('div',{className:'card'},
        h('div',{className:'card-header'},h('h3',null,'Résultat (à coller dans CW)'), copyBtn),
        h('div',{style:{padding:'14px 18px'}}, tbl)
      )
    );
  }else if(tab==='acheteurs'){
    const list=S.comptaAcheteurs||[];
    const imp=h('input',{type:'file',accept:'.xlsx,.xlsm,.xls',style:{display:'none'}});
    const impBtn=h('button',{className:'btn-ghost',onClick:()=>imp.click()},iconEl('upload',13),' Importer Excel');
    imp.addEventListener('change',e=>{const f=e.target.files[0];if(f)comptaImportAcheteurs(f);});
    const code=h('input',{type:'text',placeholder:'Code vendeur (optionnel)'});
    const numCompte=h('input',{type:'text',placeholder:'Numéro de compte'});
    const rs=h('input',{type:'text',placeholder:'Raison sociale (ex: COME BACK GRAPHIC ASSOCIES)'});
    const form=h('div',{className:'compta-add-bar'},
      h('h3',null,'Ajouter un acheteur'),
      h('div',{className:'compta-add-bar-meta'},
        h('span',{className:'hint'},'Feuille: ACHETEURS'),
        impBtn,
        imp
      ),
      h('div',{className:'compta-add-bar-fields'},
        h('div',null,h('label',null,'Code vendeur'),code),
        h('div',null,h('label',null,'Numéro de compte'),numCompte),
        h('div',null,h('label',null,'Raison sociale'),rs)
      ),
      h('div',{className:'compta-add-bar-actions'},
        h('button',{className:'btn-sm',onClick:()=>{
          const payload={code_vendeur:code.value||null,identifiant:numCompte.value,raison_sociale:rs.value};
          if(!payload.identifiant||!payload.raison_sociale){toast('Numéro de compte et raison sociale obligatoires','error');return;}
          comptaUpsertAcheteurs([payload]);
          code.value='';numCompte.value='';rs.value='';
        }},'Ajouter')
      )
    );
    const rows=list.length? h('div',{className:'card'},
      h('div',{className:'card-header'},h('h3',null,'Acheteurs ('+list.length+')')),
      h('div',{style:{padding:'10px 16px'}},...list.slice(0,500).map(a=>h('div',{className:'import-row'},
        h('div',{style:{flex:1}},h('div',{style:{fontSize:'13px',fontWeight:'600'}},a.raison_sociale),h('div',{style:{fontSize:'11px',color:'var(--muted)',fontFamily:'monospace'}},(a.code_vendeur||'—')+' · '+a.identifiant)),
        h('button',{className:'btn-ghost',onClick:()=>set({comptaEditAcheteurId:a.id})},iconEl('edit',13),' Modifier'),
        h('button',{className:'btn-danger',onClick:()=>comptaDeleteAcheteur(a.id)},iconEl('trash',13),' Supprimer')
      )))
    ) : h('div',{className:'card-empty'},'Aucun acheteur');
    content=h('div',null,form,rows);
  }else if(tab==='comptes'){
    const list=S.comptaComptes||[];
    const imp=h('input',{type:'file',accept:'.xlsx,.xlsm,.xls',style:{display:'none'}});
    const impBtn=h('button',{className:'btn-ghost',onClick:()=>imp.click()},iconEl('upload',13),' Importer Excel');
    imp.addEventListener('change',e=>{const f=e.target.files[0];if(f)comptaImportComptes(f);});
    const lib=h('input',{type:'text',placeholder:'Libellé condensé (ex: Achat de Factures)'});
    const num=h('input',{type:'text',placeholder:'Numéro de compte (ex: 519320000000)'});
    const form=h('div',{className:'compta-add-bar'},
      h('h3',null,'Ajouter un libellé'),
      h('div',{className:'compta-add-bar-meta'},
        h('span',{className:'hint'},'Feuille: TABLE DES COMPTES'),
        impBtn,
        imp
      ),
      h('div',{className:'compta-add-bar-fields'},
        h('div',null,h('label',null,'Libellé condensé'),lib),
        h('div',null,h('label',null,'Numéro de compte'),num)
      ),
      h('div',{className:'compta-add-bar-actions'},
        h('button',{className:'btn-sm',onClick:()=>{
          const payload={libelle_condense:lib.value,numero_compte:num.value};
          if(!payload.libelle_condense||!payload.numero_compte){toast('Libellé et numéro de compte obligatoires','error');return;}
          comptaUpsertComptes([payload]);
          lib.value='';num.value='';
        }},'Ajouter')
      )
    );
    const rows=list.length? h('div',{className:'card'},
      h('div',{className:'card-header'},h('h3',null,'Table des comptes ('+list.length+')')),
      h('div',{style:{padding:'10px 16px'}},...list.slice(0,500).map(a=>h('div',{className:'import-row'},
        h('div',{style:{flex:1}},h('div',{style:{fontSize:'13px',fontWeight:'600'}},a.libelle_condense),h('div',{style:{fontSize:'11px',color:'var(--muted)',fontFamily:'monospace'}},a.numero_compte)),
        h('button',{className:'btn-ghost',onClick:()=>set({comptaEditCompteId:a.id})},iconEl('edit',13),' Modifier'),
        h('button',{className:'btn-danger',onClick:()=>comptaDeleteCompte(a.id)},iconEl('trash',13),' Supprimer')
      )))
    ) : h('div',{className:'card-empty'},'Aucun compte');
    content=h('div',null,form,rows);
  }else if(tab==='banques'){
    const list=S.comptaBanques||[];
    const code=h('input',{type:'text',placeholder:'Code vendeur (ex: 98, 100)'});
    const num=h('input',{type:'text',placeholder:'Numéro de compte (ex: 519320000000)'});
    const lib=h('input',{type:'text',placeholder:'Libellé (optionnel)'});
    const form=h('div',{className:'compta-add-bar'},
      h('h3',null,'Ajouter un code de banque'),
      h('div',{className:'compta-add-bar-meta'},
        h('span',{className:'hint'},'Compte CAF de contrepartie selon le code vendeur Factor')
      ),
      h('div',{className:'compta-add-bar-fields'},
        h('div',null,h('label',null,'Code vendeur'),code),
        h('div',null,h('label',null,'Numéro de compte'),num),
        h('div',null,h('label',null,'Libellé'),lib)
      ),
      h('div',{className:'compta-add-bar-actions'},
        h('button',{className:'btn-sm',onClick:()=>{
          const payload={code_vendeur:code.value,numero_compte:num.value,libelle:lib.value||null};
          if(!payload.code_vendeur||!payload.numero_compte){toast('Code vendeur et numéro de compte obligatoires','error');return;}
          comptaUpsertBanques([payload]);
          code.value='';num.value='';lib.value='';
        }},'Ajouter')
      )
    );
    const rows=list.length? h('div',{className:'card'},
      h('div',{className:'card-header'},h('h3',null,'Codes de banque ('+list.length+')')),
      h('div',{style:{padding:'10px 16px'}},...list.map(b=>h('div',{className:'import-row'},
        h('div',{style:{flex:1}},
          h('div',{style:{fontSize:'13px',fontWeight:'600'}},'Vendeur ',b.code_vendeur,(b.libelle?(' — '+b.libelle):'')),
          h('div',{style:{fontSize:'11px',color:'var(--muted)',fontFamily:'monospace'}},b.numero_compte)
        ),
        h('button',{className:'btn-ghost',onClick:()=>set({comptaEditBanqueId:b.id})},iconEl('edit',13),' Modifier'),
        h('button',{className:'btn-danger',onClick:()=>comptaDeleteBanque(b.id)},iconEl('trash',13),' Supprimer')
      )))
    ) : h('div',{className:'card-empty'},'Aucun code de banque — ajoutez au moins 98 et 100');
    content=h('div',null,form,rows);
  }else if(tab==='cession'){
    content=h('div',null,
      h('div',{className:'card',style:{padding:'40px',textAlign:'center'}},
        h('div',{style:{fontSize:'48px',marginBottom:'20px'}},'🚧'),
        h('h2',{style:{color:'var(--muted)'}},'Cession'),
        h('p',{style:{color:'var(--muted)',marginTop:'10px'}},'En cours de développement...')
      )
    );
  }else if(tab==='paie'){
    content=renderPaieTab();
  }

  const body=h('div',{className:'app'},
    sidebar,
    h('main',{className:'main'},
      h('div',{className:'container'},
        topbar,
          h('h1',null,S.comptaTab==='paie'?'Gestion des Paies':'MyCompta'),
        h('div',{className:'subtitle'},S.comptaTab==='paie'?'Saisie mensuelle · Export xlsx':'Import Factor → mise en forme → copier vers CW'),
        content
      )
    )
  );

  return h('div',null,
    S.sidebarOpen?h('div',{className:'sidebar-overlay',onClick:closeSidebar}):null,
    body,
    renderComptaAcheteurModal(),
    renderComptaCompteModal(),
    renderComptaBanqueModal()
  );
}

// ── MyExpé ────────────────────────────────────────────────────────
const EXPE_CONTACTS_KEY='mysifa_transport_contacts';
const EXPE_DEFAULT_CONTACTS={
  'Coupé':{type:'url',value:'https://coupe.station-chargeur.com/coupe/',label:'Portail Coupé'},
  'Ceva':{type:'url',value:'https://connect.gefco.net/psc-portal/login.html#LogIn',label:'Portail Ceva/Gefco'},
  'Coquelle':{type:'email',value:'eugeneleconte@outlook.com',label:'Mail Coquelle'},
  'Dimotrans':{type:'email',value:'eugeneleconte@outlook.com',label:'Mail Dimotrans'},
};
const EXPE_COLORS={'Coupé':'#22d3ee','Coquelle':'#a78bfa','Ceva':'#34d399','Dimotrans':'#fbbf24'};
function expeCC(c){return EXPE_COLORS[c]||'#94a3b8';}
function expeLoadContacts(){
  try{return {...EXPE_DEFAULT_CONTACTS,...JSON.parse(localStorage.getItem(EXPE_CONTACTS_KEY)||'{}')};}
  catch(e){return {...EXPE_DEFAULT_CONTACTS};}
}
function expeEnsureContacts(){if(!S.expeContacts)S.expeContacts=expeLoadContacts();return S.expeContacts;}
function expeOpenContact(carrier){
  if(typeof T!=='undefined'&&Array.isArray(T.list)){
    const tr=T.list.find(x=>String(x.nom||'')===String(carrier||''));
    if(tr&&typeof expeTrpOpenContact==='function'){expeTrpOpenContact(tr);return;}
  }
  const c=expeEnsureContacts()[carrier];if(!c)return;
  if(c.type==='url')window.open(c.value,'_blank','noopener');
  else{
    const s=encodeURIComponent('Demande de tarif SIFA - '+carrier);
    const b=encodeURIComponent('Bonjour,\n\nNous souhaitons obtenir un tarif pour :\n- Département : '+(S.expeDept||'')+'\n- Poids : '+(S.expeKg||'?')+' kg\n- Palettes : '+(S.expeNbPal||'?')+'\n\nCordialement,\nSIFA Roubaix');
    window.location.href='mailto:'+c.value+'?subject='+s+'&body='+b;
  }
}
async function ensureExpeRawData(){
  if(S.expeRaw||S.expeRawLoading)return;
  S.expeRawLoading=true;S.expeRawError=null;render();
  try{
    const r=await fetch('/static/transport_tarifs.json?v=4',{credentials:'same-origin'});
    if(!r.ok)throw new Error('HTTP '+r.status);
    S.expeRaw=await r.json();S.expeRawLoading=false;render();
  }catch(e){S.expeRawLoading=false;S.expeRawError='Impossible de charger les grilles.';render();}
}

// ── Calcul poids ─────────────────────────────────────────────────
function _calcCoupePoids(raw,dept,kg){
  const p=raw.coupe_poids&&raw.coupe_poids[dept];if(!p)return null;
  const b=raw.coupe_poids_brackets;
  for(let i=0;i<b.length;i++){
    if(kg<=b[i]){
      if(i<10)return p[i];
      return p[i]!=null?(kg/100)*p[i]:null;
    }
  }
  return null;
}
function _calcCevaPoids(raw,dept,kg){
  const p=raw.ceva_poids&&raw.ceva_poids[dept];if(!p)return null;
  const b=raw.ceva_poids_brackets;
  for(let i=0;i<b.length;i++){
    if(kg<=b[i]){
      if(i<10)return p[i];
      return p[i]!=null?(kg/100)*p[i]:null;
    }
  }
  return null;
}

// ── Calcul palette ───────────────────────────────────────────────
function _calcCoupePal(raw,dept,n){
  const p=raw.coupe_pal&&raw.coupe_pal[dept];
  if(!p||n<1||n>5)return null;
  return p[n-1]||null;
}
function _calcCevaPal(raw,dept,n){
  const p=raw.ceva_pal&&raw.ceva_pal[dept];
  if(!p||n<1||n>4)return null;
  return p[n-1]||null;
}
function _calcCoquellePal(raw,dept,n){
  const p=raw.coquelle_pal&&raw.coquelle_pal[dept];
  if(!p||n<1||n>33)return null;
  return p[n-1]||null;
}
function _calcDimotransPal(raw,dept,n){
  const p=raw.dimotrans_pal&&raw.dimotrans_pal[dept];
  if(!p||n<1||n>28)return null;
  return p[Math.min(n,28)-1]||null;
}

function expeCompute(){
  if(!S.expeRaw){toast('Grilles non chargées','warn');return;}
  const raw=S.expeRaw;
  const d=String(S.expeDept||'').trim().padStart(2,'0');
  const kg=Number(S.expeKg)||0;
  const nbPal=parseInt(S.expeNbPal,10)||0;
  const fuel=(Number(S.expeFuelPct)||0)/100;
  const r2=v=>v!=null?Math.round(v*100)/100:null;
  const af=v=>v!=null?r2(v*(1+fuel)):null;

  const poids=[];
  if(kg>0){
    [{c:'Coupé',fn:_calcCoupePoids},{c:'Ceva',fn:_calcCevaPoids}].forEach(({c,fn})=>{
      const p=af(fn(raw,d,kg));
      if(p!=null&&p>0)poids.push({carrier:c,price:p});
    });
    poids.sort((a,b)=>a.price-b.price);
  }
  const palette=[];
  if(nbPal>0){
    [
      {c:'Coupé',fn:_calcCoupePal,max:5},
      {c:'Coquelle',fn:_calcCoquellePal,max:33},
      {c:'Ceva',fn:_calcCevaPal,max:4},
      {c:'Dimotrans',fn:_calcDimotransPal,max:28},
    ].forEach(({c,fn})=>{
      const p=af(fn(raw,d,nbPal));
      if(p!=null&&p>0)palette.push({carrier:c,price:p});
    });
    palette.sort((a,b)=>a.price-b.price);
  }
  set({expeResults:{dept:d,kg,nbPal,fuel:Number(S.expeFuelPct)||0,poids,palette}});
}

// ── UI helpers ───────────────────────────────────────────────────
function renderExpeScore(item,rank){
  const col=expeCC(item.carrier);
  const medals=['\u{1F947}','\u{1F948}','\u{1F949}'];
  return h('div',{className:'expe-score'},
    h('div',{className:'stripe',style:{background:col}}),
    h('div',{className:'body'},
      h('div',{style:{display:'flex',justifyContent:'space-between',alignItems:'flex-start'}},
        h('div',{className:'carrier',style:{color:col}},item.carrier),
        rank<3?h('span',{className:'medal'},medals[rank]):null
      ),
      h('div',{className:'price',style:{color:'var(--text)'}},
        item.price.toFixed(2),
        h('span',{className:'unit'},'\u20ac HT')
      ),
      h('button',{className:'btn-ghost',
        style:{width:'100%',borderColor:col+'55',color:col},
        onClick:()=>expeOpenContact(item.carrier)
      },expeEnsureContacts()[item.carrier]&&expeEnsureContacts()[item.carrier].type==='url'?'Portail':'Contacter')
    )
  );
}
function renderExpeRankTable(title,rows){
  if(!rows||!rows.length)return h('div',{className:'card-empty'},'Aucun tarif disponible.');
  return h('div',{className:'card',style:{marginTop:10}},
    h('div',{className:'card-header'},h('h3',null,title+' ('+rows.length+')')),
    h('div',{style:{overflowX:'auto'}},
      h('table',{style:{minWidth:500}},
        h('thead',null,h('tr',null,
          h('th',null,'#'),h('th',null,'Transporteur'),h('th',null,'Prix HT'),h('th',null,'Contact')
        )),
        h('tbody',null,...rows.map((r,i)=>{
          const col=expeCC(r.carrier);
          return h('tr',null,
            h('td',null,String(i+1)),
            h('td',null,h('span',{style:{fontWeight:700,color:col}},r.carrier)),
            h('td',null,h('span',{style:{fontFamily:'monospace',fontWeight:800,color:col}},r.price.toFixed(2)+' \u20ac')),
            h('td',null,h('button',{className:'btn-ghost',style:{borderColor:col+'44',color:col},
              onClick:()=>expeOpenContact(r.carrier)
            },expeEnsureContacts()[r.carrier]&&expeEnsureContacts()[r.carrier].type==='url'?'Portail':'Email'))
          );
        }))
      )
    )
  );
}
function renderExpeContactModal(){
  const cur=JSON.parse(JSON.stringify(expeEnsureContacts()));
  const overlay=h('div',{className:'contact-modal-overlay'});
  const box=h('div',{className:'contact-modal',style:{maxWidth:520}});
  box.appendChild(h('div',{className:'contact-modal-head'},
    h('h3',null,'Contacts transporteurs'),
    h('button',{className:'contact-close-btn',onClick:()=>set({expeShowContacts:false})},'\u2715')
  ));
  const body=h('div',{className:'contact-modal-body',style:{display:'grid',gap:10}});
  Object.keys(cur).forEach(name=>{
    const row=h('div',{style:{border:'1px solid var(--border)',borderRadius:10,padding:10}});
    row.appendChild(h('div',{style:{fontSize:13,fontWeight:700,color:expeCC(name),marginBottom:8}},name));
    const sel=h('select',{className:'form-sel',style:{width:110}},
      h('option',{value:'email',selected:cur[name].type==='email'},'Email'),
      h('option',{value:'url',selected:cur[name].type==='url'},'Site web'));
    const inp=h('input',{value:cur[name].value||'',placeholder:cur[name].type==='url'?'https://...':'contact@...',style:{flex:1,minWidth:0}});
    sel.addEventListener('change',e=>{cur[name].type=e.target.value;});
    inp.addEventListener('input',e=>{cur[name].value=e.target.value;});
    row.appendChild(h('div',{style:{display:'flex',gap:8,flexWrap:'wrap'}},sel,inp));
    body.appendChild(row);
  });
  box.appendChild(body);
  box.appendChild(h('div',{className:'contact-modal-actions'},
    h('button',{className:'btn-ghost',onClick:()=>set({expeShowContacts:false})},'Annuler'),
    h('button',{className:'btn-sm',onClick:()=>{
      try{localStorage.setItem(EXPE_CONTACTS_KEY,JSON.stringify(cur));}catch(e){}
      set({expeContacts:{...EXPE_DEFAULT_CONTACTS,...cur},expeShowContacts:false});
    }},'Enregistrer')
  ));
  overlay.appendChild(box);
  overlay.addEventListener('click',e=>{if(e.target===overlay)set({expeShowContacts:false});});
  return overlay;
}
function renderExpeComparateur(){
  return renderExpeComparateurTarifs();
}
__EXPE_COMPARATEUR_JS__
__EXPE_DEVIS_JS__
__EXPE_TRANSPORTEURS_JS__
__EXPE_CARTE_FRANCE_JS__
function renderExpePoids(){
  const rows=S.expePoidsRows||[];
  const fKg=v=>v.toFixed(3)+'\u00a0kg';
  const wNum=x=>{const v=parseFloat(x);return Number.isFinite(v)?v:0;};

  // Recalcul sans rerender (garde le focus dans les inputs)
  const weightEls=[];
  let etiqTotalEl=null, palTotalEl=null, grandTotalEl=null, grandPalPartEl=null;
  function recalc(){
    const gram=wNum(S.expePoidsGram)||155;
    const coeff=wNum(S.expePoidsCoeff)||1.05;
    let etiqTotal=0;
    for(let i=0;i<rows.length;i++){
      const r=rows[i]||{};
      const q=wNum(r.qty), l=wNum(r.laize), d=wNum(r.dev);
      const w = (q&&l&&d) ? (q*l*d*coeff*gram/1e6) : null;
      if(w!=null) etiqTotal += w;
      if(weightEls[i]) weightEls[i].textContent = w!=null ? fKg(w) : '—';
      if(weightEls[i]){
        weightEls[i].style.opacity = w!=null ? '1' : '0.25';
        weightEls[i].style.fontWeight = w!=null ? '600' : 'normal';
      }
    }
    const palNb=wNum(S.expoPoidsPalNb)||0;
    const palKg=wNum(S.expoPoidsPalKg)||0;
    const palTotal=palNb*palKg;
    const grandTotal=etiqTotal+palTotal;
    if(etiqTotalEl) etiqTotalEl.textContent = etiqTotal>0 ? fKg(etiqTotal) : '—';
    if(palTotalEl) palTotalEl.textContent = palTotal>0 ? fKg(palTotal) : '—';
    if(grandTotalEl) grandTotalEl.textContent = grandTotal>0 ? grandTotal.toFixed(3)+'\u00a0kg' : '—';
    if(grandPalPartEl) grandPalPartEl.textContent = (grandTotal>0&&palTotal>0) ? ('dont palette\u00a0: '+fKg(palTotal)) : '';
  }

  const inp=(val,cb,extra={})=>{
    const el=h('input',Object.assign({type:'number',min:'0',step:'any',placeholder:'0',value:val,
      style:{width:'100%',padding:'0.3rem 0.5rem',borderRadius:'6px',border:'1px solid var(--border)',
             background:'var(--card)',color:'var(--fg)',fontSize:'0.85rem',boxSizing:'border-box'}},extra));
    el.addEventListener('input',e=>cb(e.target.value));
    return el;
  };
  const paramCard=h('div',{className:'card',style:{marginBottom:'1rem'}},
    h('div',{className:'card-header'},h('span',null,'Paramètres')),
    h('div',{style:{padding:'1rem 1rem 1.25rem'}},
      h('div',{style:{marginBottom:'1rem'}},
        h('div',{style:{display:'flex',alignItems:'center',gap:'0.5rem'}},
          (()=>{
            const el=h('input',{type:'number',min:'1',step:'any',placeholder:'155',
              value:S.expePoidsGram||'',
              style:{width:'90px',padding:'0.3rem 0.5rem',borderRadius:'6px',border:'1px solid var(--border)',
                     background:'var(--card)',color:'var(--fg)',fontSize:'0.85rem'}});
            el.addEventListener('input',e=>{S.expePoidsGram=e.target.value;recalc();});
            return el;
          })(),
          h('span',{style:{fontSize:'0.85rem',opacity:0.75}},'g/m²')
        )
      ),
      h('div',null,
        h('label',{style:{display:'block',fontSize:'0.75rem',opacity:0.65,marginBottom:'0.45rem'}},'Coefficient'),
        (()=>{const el=h('input',{type:'number',step:'0.01',min:'0.1',value:S.expePoidsCoeff,
          style:{width:'90px',padding:'0.3rem 0.5rem',borderRadius:'6px',border:'1px solid var(--border)',
                 background:'var(--card)',color:'var(--fg)',fontSize:'0.85rem'}});
          el.addEventListener('input',e=>{S.expePoidsCoeff=e.target.value;recalc();});return el;})()
      )
    )
  );

  const thStyle={padding:'0.4rem 0.5rem',textAlign:'left',fontSize:'0.75rem',opacity:0.6,fontWeight:'600',borderBottom:'1px solid var(--border)'};
  const tdStyle={padding:'0.3rem 0.4rem',verticalAlign:'middle'};
  const thead=h('thead',null,h('tr',null,
    h('th',{style:{...thStyle,width:'1.8rem',textAlign:'center'}},'#'),
    h('th',{style:thStyle},'Qté (mille)'),
    h('th',{style:thStyle},'Laize (mm)'),
    h('th',{style:thStyle},'Développé (mm)'),
    h('th',{style:{...thStyle,textAlign:'right'}},'Poids (kg)')
  ));
  const tbody=h('tbody',null,...rows.map((r,i)=>{
    const updateRow=(key,val)=>{
      if(!S.expePoidsRows) S.expePoidsRows=[];
      if(!S.expePoidsRows[i]) S.expePoidsRows[i]={qty:'',laize:'',dev:''};
      S.expePoidsRows[i][key]=val;
      recalc();
    };
    const wEl=h('span',null,'—');
    weightEls[i]=wEl;
    return h('tr',null,
      h('td',{style:{...tdStyle,textAlign:'center',fontSize:'0.75rem',opacity:0.4}},String(i+1)),
      h('td',{style:tdStyle},inp(r.qty,v=>updateRow('qty',v))),
      h('td',{style:tdStyle},inp(r.laize,v=>updateRow('laize',v))),
      h('td',{style:tdStyle},inp(r.dev,v=>updateRow('dev',v))),
      h('td',{style:{...tdStyle,textAlign:'right',fontWeight:'normal',opacity:0.25,fontSize:'0.85rem',whiteSpace:'nowrap'}},wEl)
    );
  }));

  const resetBtn=h('button',{className:'btn-ghost',style:{padding:'0.25rem 0.65rem',fontSize:'0.8rem',marginRight:'0.4rem'}},'Remettre à 0');
  resetBtn.addEventListener('click',()=>{
    set({expePoidsRows:[{qty:'',laize:'',dev:''},{qty:'',laize:'',dev:''},{qty:'',laize:'',dev:''},{qty:'',laize:'',dev:''}]});
  });
  const addBtn=h('button',{style:{padding:'0.25rem 0.65rem',fontSize:'0.8rem',borderRadius:'6px',cursor:'pointer',
    border:'1px solid var(--border)',background:'transparent',color:'var(--fg)'}},'+\u00a0Ligne');
  addBtn.addEventListener('click',()=>set({expePoidsRows:[...rows,{qty:'',laize:'',dev:''}]}));
  const delBtn=(rows.length>1)?h('button',{style:{padding:'0.25rem 0.65rem',fontSize:'0.8rem',borderRadius:'6px',cursor:'pointer',
    border:'1px solid var(--border)',background:'transparent',color:'var(--fg)',marginLeft:'0.4rem'}},'\u2212\u00a0Ligne'):null;
  if(delBtn)delBtn.addEventListener('click',()=>set({expePoidsRows:rows.slice(0,-1)}));

  const rowsCard=h('div',{className:'card',style:{marginBottom:'1rem'}},
    h('div',{className:'card-header',style:{display:'flex',alignItems:'center',justifyContent:'space-between'}},
      h('span',null,'Étiquettes'),
      h('div',null,resetBtn,addBtn,delBtn||null)
    ),
    h('div',{style:{overflowX:'auto',padding:'0.25rem 0.75rem 0.75rem'}},
      h('table',{style:{width:'100%',borderCollapse:'collapse',fontSize:'0.88rem'}},thead,tbody)
    ),
    (()=>{
      etiqTotalEl=h('strong',null,'—');
      return h('div',{style:{padding:'0.1rem 1rem 0.75rem',textAlign:'right',fontSize:'0.88rem',opacity:0.75}},
        'Sous-total étiquettes\u00a0: ',etiqTotalEl
      );
    })()
  );

  const palCard=h('div',{className:'card',style:{marginBottom:'1rem'}},
    h('div',{className:'card-header'},h('span',null,'Palette (optionnel)')),
    h('div',{style:{padding:'1rem',display:'flex',gap:'1rem',flexWrap:'wrap',alignItems:'flex-end'}},
      h('div',{style:{flex:'0 0 100px'}},
        h('label',{style:{display:'block',fontSize:'0.75rem',opacity:0.65,marginBottom:'0.4rem'}},'Nb palettes'),
        (()=>{const el=h('input',{type:'number',min:'0',step:'1',placeholder:'0',value:S.expoPoidsPalNb,
          style:{width:'100%',padding:'0.3rem 0.5rem',borderRadius:'6px',border:'1px solid var(--border)',
                 background:'var(--card)',color:'var(--fg)',fontSize:'0.85rem'}});
          el.addEventListener('input',e=>{S.expoPoidsPalNb=e.target.value;recalc();});return el;})()
      ),
      h('div',{style:{flex:'0 0 120px'}},
        h('label',{style:{display:'block',fontSize:'0.75rem',opacity:0.65,marginBottom:'0.4rem'}},'Poids / palette (kg)'),
        (()=>{const el=h('input',{type:'number',min:'0',step:'any',placeholder:'0',value:S.expoPoidsPalKg,
          style:{width:'100%',padding:'0.3rem 0.5rem',borderRadius:'6px',border:'1px solid var(--border)',
                 background:'var(--card)',color:'var(--fg)',fontSize:'0.85rem'}});
          el.addEventListener('input',e=>{S.expoPoidsPalKg=e.target.value;recalc();});return el;})()
      ),
      (()=>{
        palTotalEl=h('strong',null,'—');
        return h('div',{style:{paddingBottom:'0.2rem',fontSize:'0.88rem',opacity:0.75}},
          'Sous-total\u00a0: ',palTotalEl
        );
      })()
    )
  );

  const totalCard=h('div',{className:'card',style:{textAlign:'center',padding:'1.5rem 1rem',
    background:'var(--accent)',color:'#fff',borderRadius:'12px',marginBottom:'0.5rem'}},
    h('div',{style:{fontSize:'0.78rem',letterSpacing:'0.08em',opacity:0.85,marginBottom:'0.4rem'}},'POIDS TOTAL ESTIMÉ'),
    (()=>{
      grandTotalEl=h('div',{style:{fontSize:'2.4rem',fontWeight:'700',letterSpacing:'-1px',lineHeight:1.1}},'—');
      grandPalPartEl=h('div',{style:{fontSize:'0.8rem',opacity:0.8,marginTop:'0.35rem'}},'');
      return h('div',null,grandTotalEl,grandPalPartEl);
    })()
  );

  const root=h('div',{style:{maxWidth:'680px'}},
    h('p',{style:{opacity:0.55,fontSize:'0.82rem',marginBottom:'1.25rem',fontStyle:'italic'}},
      'Formule\u00a0: Qté\u2009(mille)\u2009×\u2009Laize\u2009×\u2009Développé\u2009×\u2009Coeff\u2009×\u2009Grammage\u2009/\u20091\u202f000\u202f000'),
    paramCard,rowsCard,palCard,totalCard
  );
  // Initial calc after DOM is built
  queueMicrotask(recalc);
  return root;
}

function expeParisDayISO(){
  try{return new Date().toLocaleDateString('sv-SE',{timeZone:'Europe/Paris'});}
  catch(e){const d=new Date();return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');}
}
async function loadExpePaletteTypes(){
  if(S.app!=='expe')return;
  if(S.expePaletteTypesLoading) return;
  if((S.expePaletteTypes||[]).length) return;
  set({expePaletteTypesLoading:true});
  try{
    const rows=await api('/api/expe/matieres-palettes');
    set({expePaletteTypes:Array.isArray(rows)?rows:[],expePaletteTypesLoading:false});
  }catch(e){
    set({expePaletteTypesLoading:false});
  }
}
function expePaletteTypeLabel(row){
  if(!row) return '—';
  if((row.type_colis||'').trim().toLowerCase()==='vrac') return 'Vrac';
  if(row.type_palette_label) return row.type_palette_label;
  const id=row.type_palette_matiere_id;
  if(id==null||id==='') return '—';
  const items=S.expePaletteTypes||[];
  const m=items.find(x=>String(x.id)===String(id));
  if(!m) return '—';
  const ref=(m.reference||'').trim();
  const des=(m.designation||'').trim();
  return ref?(des?ref+' — '+des:ref):'—';
}
async function loadExpeDepartJour(){
  if(S.app!=='expe')return;
  void loadExpePaletteTypes();
  if(_expeJourInflight)return await _expeJourInflight;
  _expeJourInflight=(async()=>{
    set({expeDepartLoading:true});
    try{
      const rows=await api('/api/expe/departs/jour');
      set({expeDepartList:Array.isArray(rows)?rows:[],expeDepartLoading:false});
    }catch(e){
      set({expeDepartLoading:false});
      toast(e.message||'Chargement impossible','error');
    }
  })();
  try{return await _expeJourInflight;}finally{_expeJourInflight=null;}
}
async function loadExpeDepartHistorique(resetPage){
  if(S.app!=='expe')return;
  void loadExpePaletteTypes();
  if(resetPage) S.expeDepartHistPage=1;
  // Préserver le focus/caret de la searchbar pendant les re-renders (chargement + résultats)
  const qEl = document.getElementById('expe-hist-search');
  const hadFocus = !!(qEl && document.activeElement === qEl);
  const caret = (hadFocus && typeof qEl.selectionStart === 'number') ? [qEl.selectionStart, qEl.selectionEnd] : null;

  set({expeDepartHistLoading:true});
  try{
    const qq=(S.expeDepartHistQ||'').trim();
    const page=S.expeDepartHistPage||1;
    const data=await api('/api/expe/departs/historique?q='+encodeURIComponent(qq)+'&page='+page+'&limit=50');
    const rows=Array.isArray(data)?data:(data&&data.rows)||[];
    set({
      expeDepartHist:rows,
      expeDepartHistTotal:data&&data.total!=null?data.total:rows.length,
      expeDepartHistPage:data&&data.page!=null?data.page:page,
      expeDepartHistPages:data&&data.pages!=null?data.pages:1,
      expeDepartHistLoading:false
    });
  }catch(e){
    set({expeDepartHistLoading:false});
    toast(e.message||'Chargement impossible','error');
  }
  if(hadFocus){
    requestAnimationFrame(()=>{
      const ne = document.getElementById('expe-hist-search');
      if(!ne) return;
      try{
        ne.focus();
        if(caret){
          const a=Math.min(caret[0]!=null?caret[0]:0, ne.value.length);
          const b=Math.min(caret[1]!=null?caret[1]:a, ne.value.length);
          ne.setSelectionRange(a,b);
        }
      }catch(e){}
    });
  }
}
function scheduleExpeHistSearch(){
  if(_expeHistSearchT)clearTimeout(_expeHistSearchT);
  _expeHistSearchT=setTimeout(()=>{loadExpeDepartHistorique(true);},380);
}
function expeHistChangePage(delta){
  const pages=S.expeDepartHistPages||1;
  const next=(S.expeDepartHistPage||1)+delta;
  if(next<1||next>pages)return;
  S.expeDepartHistPage=next;
  void loadExpeDepartHistorique();
}
async function expeValiderDepart(id){
  try{
    await api('/api/expe/departs/'+id+'/valider',{method:'POST'});
    toast('Départ validé — entrée dans l\'historique');
    await loadExpeDepartJour();
  }catch(e){toast(e.message||'Validation impossible','error');}
}
async function expeInvaliderDepart(id){
  if(!confirm('Remettre ce départ dans le suivi du jour ?\n\nIl disparaîtra de l\'historique et pourra être modifié ou validé à nouveau.')) return;
  try{
    await api('/api/expe/departs/'+id+'/invalider',{method:'POST'});
    toast('Départ remis dans le suivi du jour');
    await loadExpeDepartHistorique();
    if((S.expeDepartSubTab||'jour')==='jour') await loadExpeDepartJour();
  }catch(e){toast(e.message||'Action impossible','error');}
}

function expeOpenDepartModal(prefill, mode){
  const dayVal=(S.expeDepartJourDate&&String(S.expeDepartJourDate).trim())||expeParisDayISO();
  const src = prefill || {};
  const srcDate = (src.date_enlevement||'') ? String(src.date_enlevement).slice(0,10) : '';
  void loadExpePaletteTypes();
  // En édition ou duplication : onglet manuel direct ; nouveau départ : onglet picker dossier
  const isEdit = !!(mode==='edit' && src && src.id);
  const initialTab = (mode==='new' && !prefill) ? 'dossier' : 'manuel';
  if(initialTab==='dossier'){
    void loadExpeDepartDossiers();
  }
  set({
    expeDepartModalOpen:true,
    expeDepartEditId: isEdit ? src.id : null,
    expeDepartFormTab: initialTab,
    expeDepartDossierQuery:'',
    expeDepartDossierHi:-1,
    expeDepartForm:{
      date_enlevement: srcDate || dayVal,
      affreteurs: src.affreteurs||'',
      transporteur: src.transporteur||'',
      client: src.client||'',
      code_postal_destination: src.code_postal_destination||'',
      ref_sifa: src.ref_sifa||'',
      arc: src.arc||'',
      no_cde_transport: src.no_cde_transport||'',
      no_bl: src.no_bl||'',
      type_palette_matiere_id: (src.type_colis||'').trim().toLowerCase()==='vrac'
        ? '__vrac__'
        : (src.type_palette_matiere_id!=null && src.type_palette_matiere_id!=='')
          ? String(src.type_palette_matiere_id) : '',
      nb_palette: (src.nb_palette!=null && src.nb_palette!=='') ? String(src.nb_palette) : '',
      poids_total_kg: (src.poids_total_kg!=null && src.poids_total_kg!=='') ? String(src.poids_total_kg) : '',
      date_livraison: (src.date_livraison||'') ? String(src.date_livraison).slice(0,10) : '',
      planning_entry_id: (src.planning_entry_id!=null && src.planning_entry_id!=='') ? String(src.planning_entry_id) : '',
      palette_europe: src.palette_europe ? 1 : 0,
    }
  });
}
function expeCloseDepartModal(){
  set({expeDepartModalOpen:false, expeDepartEditId:null, expeDepartFormTab:'dossier'});
}

// Charge la liste des dossiers disponibles pour le picker MyExpé
async function loadExpeDepartDossiers(force){
  if(S.expeDepartDossiersLoading) return;
  if(!force && (S.expeDepartDossiers||[]).length) return;
  set({expeDepartDossiersLoading:true});
  try{
    const data = await api('/api/expe/dossiers-disponibles');
    const list = (data && Array.isArray(data.dossiers)) ? data.dossiers : [];
    set({expeDepartDossiers:list, expeDepartDossiersLoading:false});
  }catch(e){
    set({expeDepartDossiersLoading:false});
    toast(e.message||'Chargement des dossiers impossible','error');
  }
}

// Filtre + tri pour le picker (recherche libre)
function _expeFilterDossiers(q){
  const list = S.expeDepartDossiers || [];
  const term = (q||'').trim().toLowerCase();
  if(!term) return list.slice();
  const norm = s => String(s||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
  const lqNorm = norm(term);
  return list.filter(d=>{
    const fields = [
      d.reference, d.client, d.ref_produit, d.description,
      d.numero_of, d.machine_nom, d.date_livraison,
    ];
    return fields.some(f=>{
      if(f==null||f==='') return false;
      const s = String(f).toLowerCase();
      return s.includes(term) || norm(s).includes(lqNorm);
    });
  });
}

// Au clic sur un dossier : pré-remplit le form et bascule onglet "Saisie manuelle"
function expeSelectDossier(d){
  if(!d) return;
  const f = S.expeDepartForm || {};
  // ARC = pe.reference (numéro de dossier). On surcharge toujours.
  f.arc = d.reference || f.arc || '';
  f.client = d.client || f.client || '';
  f.ref_sifa = d.ref_produit || f.ref_sifa || '';
  f.date_livraison = (d.date_livraison||'').slice(0,10) || f.date_livraison || '';
  f.planning_entry_id = d.id ? String(d.id) : '';
  // Estimation nb palettes via fiche technique si dispo (cartons sol × hauteur ÷ ratio)
  // Si pas de donnée fiche : laisser vide pour saisie manuelle
  if(!f.nb_palette){
    const nSol = parseFloat(d.ft_palette_nb_cartons_sol || d.ft_nb_au_sol || 0);
    const nHaut = parseFloat(d.ft_palette_nb_cartons_hauteur || d.ft_nb_etage || 0);
    if(nSol > 0 && nHaut > 0){
      // Fiche technique donne 1 palette ; quantité réelle dépend de l'OF
      f.nb_palette = '1';
    }
  }
  // type_palette : si fiche technique donne palette_type connu, essayer de matcher la réf MyStock
  if(!f.type_palette_matiere_id && d.ft_palette_type){
    const pt = String(d.ft_palette_type||'').toLowerCase().trim();
    const items = S.expePaletteTypes || [];
    const match = items.find(m=>{
      const ref = String(m.reference||'').toLowerCase();
      const des = String(m.designation||'').toLowerCase();
      return pt && (ref.includes(pt) || des.includes(pt) || pt.includes(ref));
    });
    if(match){
      f.type_palette_matiere_id = String(match.id);
      if(match.is_europe) f.palette_europe = 1;
    }
  }
  set({expeDepartForm:f, expeDepartFormTab:'manuel'});
  toast('Champs préremplis depuis le dossier '+(d.reference||''));
}

// Recherche dans le picker — re-render incrémental sans reconstruire la searchbar
function _expeRefreshDossierPickerList(){
  const list = document.getElementById('expe-picker-list-inner');
  if(!list) return;
  list.innerHTML = '';
  _expeBuildDossierPickerItems(S.expeDepartDossierQuery).forEach(el=>list.appendChild(el));
}

function _expeBuildDossierPickerItems(q){
  const filtered = _expeFilterDossiers(q);
  if(!filtered.length){
    const empty = document.createElement('div');
    empty.className = 'expe-picker-empty';
    empty.textContent = q ? ('Aucun résultat pour « '+q+' »')
                          : (S.expeDepartDossiersLoading ? 'Chargement…' : 'Aucun dossier disponible');
    return [empty];
  }
  const sectionLabel = (sec)=>{
    if(sec==='en_cours') return 'En cours';
    if(sec==='prochain') return 'Prochain en attente';
    if(sec==='termine_recent') return 'Récemment terminés';
    return 'Autres dossiers';
  };
  const sectionOrder = ['en_cours','prochain','termine_recent','autre'];
  // Regrouper par section uniquement si pas de recherche active
  const groups = {};
  filtered.forEach(d=>{
    const k = d.displayed_section || 'autre';
    (groups[k] = groups[k]||[]).push(d);
  });
  const els = [];
  sectionOrder.forEach(sec=>{
    const arr = groups[sec];
    if(!arr || !arr.length) return;
    if(!q){
      const lbl = document.createElement('div');
      lbl.className = 'expe-picker-section';
      lbl.textContent = sectionLabel(sec);
      els.push(lbl);
    }
    arr.forEach(d=>{
      const dossierBlocked = d.departs_count && d.departs_count > 0;
      const ref = d.reference || '—';
      const client = d.client || 'Client non renseigné';
      const refProd = d.ref_produit || d.description || '';
      const livr = d.date_livraison ? d.date_livraison.slice(0,10) : '';
      const wrap = document.createElement('div');
      wrap.className = 'expe-picker-item'+(sec==='en_cours'?' expe-picker-item--active':'');
      wrap.onclick = ()=>expeSelectDossier(d);
      const line1 = document.createElement('div');
      line1.className = 'expe-picker-line1';
      line1.innerHTML = '<span class="expe-picker-ref">'+escHtml(ref)+'</span>'
                     + '<span class="expe-picker-sep">·</span>'
                     + '<span class="expe-picker-client">'+escHtml(client)+'</span>';
      wrap.appendChild(line1);
      const line2 = document.createElement('div');
      line2.className = 'expe-picker-line2';
      const parts = [];
      if(refProd) parts.push(escHtml(refProd));
      if(d.machine_nom) parts.push(escHtml(d.machine_nom));
      if(livr) parts.push('Livr. '+escHtml(livr));
      line2.innerHTML = parts.join('  ·  ');
      if(parts.length) wrap.appendChild(line2);
      const meta = document.createElement('div');
      meta.className = 'expe-picker-meta';
      const statutLbl = d.statut==='en_cours'?'En cours'
                      : d.statut==='termine'?'Terminé'
                      : d.statut==='attente'?'En attente':(d.statut||'');
      meta.innerHTML = '<span class="expe-picker-statut expe-picker-statut--'+escAttr(d.statut||'')+'">'+escHtml(statutLbl)+'</span>'
                     + (dossierBlocked ? '<span class="expe-picker-warn">Déjà expédié ('+d.departs_count+')</span>' : '');
      wrap.appendChild(meta);
      els.push(wrap);
    });
  });
  return els;
}

function renderExpeDepartModal(){
  if(!S.expeDepartModalOpen) return null;
  const dayVal=(S.expeDepartJourDate&&String(S.expeDepartJourDate).trim())||expeParisDayISO();
  const f=S.expeDepartForm||{};
  const isEdit = !!S.expeDepartEditId;
  const formTab = S.expeDepartFormTab || (isEdit ? 'manuel' : 'dossier');

  function mk(label,key,type,ph){
    const i=h('input',{type:type||'text',placeholder:ph||'',value:(f[key]!=null?String(f[key]):''),name:key});
    i.addEventListener('input',e=>{S.expeDepartForm[key]=e.target.value; expeScheduleSaveLocal();});
    return h('div',{className:'expe-field'},h('label',null,label),i);
  }

  const paletteItems=S.expePaletteTypes||[];
  const palSel=h('select',{name:'type_palette_matiere_id'});
  palSel.appendChild(h('option',{value:''},'— Sélectionner —'));
  paletteItems.forEach(m=>{
    const ref=(m.reference||'').trim();
    const des=(m.designation||'').trim();
    const lbl=ref?(des?ref+' — '+des:ref):('Réf. #'+m.id);
    const opt=h('option',{value:String(m.id)},lbl);
    if(String(f.type_palette_matiere_id||'')===String(m.id)) opt.selected=true;
    palSel.appendChild(opt);
  });
  const vracOpt=h('option',{value:'__vrac__'},'Vrac (sans palette — UPS…)');
  if(f.type_palette_matiere_id==='__vrac__') vracOpt.selected=true;
  palSel.appendChild(vracOpt);
  palSel.addEventListener('change',e=>{
    S.expeDepartForm.type_palette_matiere_id=e.target.value;
    expeScheduleSaveLocal();
  });
  const palField=h('div',{className:'expe-field'},
    h('label',null,'Type de palette'),
    palSel
  );
  if(!paletteItems.length && S.expePaletteTypesLoading){
    palField.appendChild(h('div',{style:{fontSize:'12px',color:'var(--muted)',marginTop:'4px'}},'Chargement des références…'));
  }else if(!paletteItems.length){
    palField.appendChild(h('div',{style:{fontSize:'12px',color:'var(--muted)',marginTop:'4px'}},
      'Aucune référence palette active (MyStock > Matières premières).'));
  }

  const overlay=h('div',{className:'add-row-modal',style:{zIndex:12000}});
  overlay.addEventListener('click',e=>{if(e.target===overlay)expeCloseDepartModal();});

  const box=h('div',{className:'add-row-form',style:{maxWidth:'760px'}});
  const closeBtn=h('button',{type:'button',className:'add-row-close',onClick:expeCloseDepartModal},'×');
  const header=h('div',{className:'add-row-header'},
    h('h3',null,isEdit?'Modifier un départ':'Ajouter un départ'),
    h('div',{className:'badge',style:{marginLeft:'auto'}},'Jour : ',dayVal)
  );

  const form=h('form',{onSubmit:async(e)=>{
    e.preventDefault();
    if(S.expeDepartSubmitting) return;
    const dateEnl = (S.expeDepartForm.date_enlevement||'').trim() || dayVal;
    const body={
      date_enlevement: dateEnl,
      affreteurs:(S.expeDepartForm.affreteurs||'').trim()||null,
      transporteur:(S.expeDepartForm.transporteur||'').trim()||null,
      client:(S.expeDepartForm.client||'').trim()||null,
      code_postal_destination:(S.expeDepartForm.code_postal_destination||'').trim()||null,
      ref_sifa:(S.expeDepartForm.ref_sifa||'').trim()||null,
      arc:(S.expeDepartForm.arc||'').trim()||null,
      no_cde_transport:(S.expeDepartForm.no_cde_transport||'').trim()||null,
      no_bl:(S.expeDepartForm.no_bl||'').trim()||null,
      type_palette_matiere_id:(S.expeDepartForm.type_palette_matiere_id||'')==='__vrac__'?null:(S.expeDepartForm.type_palette_matiere_id||'').trim()||null,
      type_colis:(S.expeDepartForm.type_palette_matiere_id||'')==='__vrac__'?'vrac':null,
      nb_palette:(S.expeDepartForm.nb_palette||'').trim()||null,
      poids_total_kg:(S.expeDepartForm.poids_total_kg||'').trim()||null,
      date_livraison:(S.expeDepartForm.date_livraison||'').trim()||null,
      planning_entry_id:(S.expeDepartForm.planning_entry_id||'').trim()||null,
      palette_europe: S.expeDepartForm.palette_europe ? 1 : 0
    };
    if(!body.date_enlevement){toast("Date d'enlèvement obligatoire",'error');return;}
    set({expeDepartSubmitting:true});
    try{
      if(isEdit){
        await api('/api/expe/departs/'+S.expeDepartEditId,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
        toast('Départ modifié');
      }else{
        await api('/api/expe/departs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
        toast('Départ enregistré');
      }
      set({expeDepartSubmitting:false});
      expeCloseDepartModal();
      if((S.expeDepartSubTab||'jour')==='historique') await loadExpeDepartHistorique();
      else await loadExpeDepartJour();
    }catch(err){
      set({expeDepartSubmitting:false});
      toast(err.message||'Erreur','error');
    }
  }});

  // Case à cocher palette Europe (modifiable manuellement)
  const europeCheck = h('input',{type:'checkbox',id:'expe-form-pal-europe'});
  europeCheck.checked = !!(f.palette_europe);
  europeCheck.addEventListener('change',e=>{
    S.expeDepartForm.palette_europe = e.target.checked ? 1 : 0;
    expeScheduleSaveLocal();
  });
  const europeField = h('div',{className:'expe-field'},
    h('label',null,'Palette Europe (consignée)'),
    h('div',{style:{display:'flex',alignItems:'center',gap:'8px',padding:'8px 0'}},
      europeCheck,
      h('label',{htmlFor:'expe-form-pal-europe',style:{fontSize:'12px',color:'var(--text2)',cursor:'pointer'}},
        'Suivre le retour de cette palette dans l\'onglet Palettes Europe')
    )
  );

  const fields=h('div',{className:'expe-fields'},
    mk("Date d'enlèvement",'date_enlevement','date'),
    mk('Affréteurs','affreteurs'),
    mk('Transporteur','transporteur'),
    mk('Client','client'),
    mk('Code postal / destination','code_postal_destination'),
    mk('Réf. SIFA','ref_sifa'),
    mk('ARC','arc'),
    mk('N° commande transporteur','no_cde_transport'),
    mk('N° BL','no_bl'),
    palField,
    mk('Nombre de palettes','nb_palette','number','ex: 2'),
    mk('Poids total (kg)','poids_total_kg','number','ex: 1325'),
    mk('Date livraison (prévue)','date_livraison','date'),
    europeField
  );

  // Onglets internes : "Depuis un dossier" / "Saisie manuelle" — masqués en édition
  const tabsNav = !isEdit ? h('div',{className:'expe-form-tabs'},
    h('button',{type:'button',
      className:'expe-form-tab'+(formTab==='dossier'?' active':''),
      onClick:()=>{
        set({expeDepartFormTab:'dossier', expeDepartDossierQuery:'', expeDepartDossierHi:-1});
        void loadExpeDepartDossiers();
      }},
      iconEl('folder',13),' Depuis un dossier'),
    h('button',{type:'button',
      className:'expe-form-tab'+(formTab==='manuel'?' active':''),
      onClick:()=>set({expeDepartFormTab:'manuel'})},
      iconEl('edit',13),' Saisie manuelle')
  ) : null;

  // Picker dossier (onglet "Depuis un dossier")
  let pickerBody = null;
  if(!isEdit && formTab==='dossier'){
    const searchInp = h('input',{
      type:'text',
      id:'expe-picker-search',
      className:'expe-picker-search',
      placeholder:'Rechercher (réf dossier, client, réf produit, OF…)',
      autoComplete:'off',
      value:S.expeDepartDossierQuery||'',
    });
    searchInp.addEventListener('input',e=>{
      S.expeDepartDossierQuery = e.target.value;
      _expeRefreshDossierPickerList();
    });
    const listEl = h('div',{className:'expe-picker-list',id:'expe-picker-list-inner'});
    requestAnimationFrame(()=>{
      _expeRefreshDossierPickerList();
      document.getElementById('expe-picker-search')?.focus();
    });
    pickerBody = h('div',{className:'expe-picker-wrap'},
      h('div',{className:'expe-picker-hint'},
        'Sélectionnez un dossier pour préremplir ARC, client, réf. SIFA, type et nb de palettes, livraison prévue. Vous pourrez ensuite ajuster manuellement.'),
      searchInp,
      listEl,
      h('div',{style:{display:'flex',justifyContent:'flex-end',marginTop:'10px'}},
        h('button',{type:'button',className:'btn-ghost',
          style:{fontSize:'12px',padding:'6px 12px'},
          onClick:()=>set({expeDepartFormTab:'manuel'})},
          'Continuer en saisie manuelle →')
      )
    );
  }

  const actions=h('div',{className:'form-actions'},
    h('button',{type:'button',className:'btn-ghost',onClick:expeCloseDepartModal},'Annuler'),
    h('button',{type:'submit',className:'btn',disabled:!!S.expeDepartSubmitting},S.expeDepartSubmitting?'Enregistrement…':'Enregistrer le départ')
  );

  if(tabsNav) form.appendChild(tabsNav);
  if(pickerBody) form.appendChild(pickerBody);
  if(formTab==='manuel' || isEdit){
    form.appendChild(fields);
    form.appendChild(actions);
  }
  box.appendChild(closeBtn);
  box.appendChild(header);
  box.appendChild(form);
  overlay.appendChild(box);
  return overlay;
}

// Résolution couleur transporteur : JOIN DB en priorité, sinon lookup par nom dans T.list
function trpColorFromRow(r){
  if(r.transporteur_couleur)return r.transporteur_couleur;
  const nom=(r.transporteur||'').trim().toLowerCase();
  if(!nom)return '';
  const t=(T.list||[]).find(x=>(x.nom||'').trim().toLowerCase()===nom);
  return t?(t.couleur||''):'';
}

function expeDepartActsGrid(buttons,validerBtn){
  const kids=(buttons||[]).filter(Boolean);
  if(!kids.length&&!validerBtn) return null;
  return h('div',{className:'expe-dep-actions-cell'},
    kids.length?h('div',{className:'expe-dep-acts'},...kids):null,
    validerBtn||null
  );
}

// ── MyExpé : suivi des palettes Europe ────────────────────────
async function loadExpePalettesEurope(){
  if(S.app!=='expe')return;
  if(S.expePalettesEuropeLoading) return;
  set({expePalettesEuropeLoading:true});
  try{
    const params = new URLSearchParams();
    if(S.expePalettesEuropeStatutFilter) params.set('statut', S.expePalettesEuropeStatutFilter);
    if(S.expePalettesEuropeClientFilter) params.set('client', S.expePalettesEuropeClientFilter);
    if(S.expePalettesEuropeQuery) params.set('q', S.expePalettesEuropeQuery);
    const qs = params.toString();
    const data = await api('/api/expe/palettes-europe'+(qs?'?'+qs:''));
    set({expePalettesEuropeData:data, expePalettesEuropeLoading:false});
  }catch(e){
    set({expePalettesEuropeLoading:false});
    toast(e.message||'Chargement palettes Europe impossible','error');
  }
}

async function expeChangePaletteEuropeStatut(departId, statut, dateRetour){
  try{
    const body = {statut: statut};
    if(dateRetour !== undefined) body.date_retour = dateRetour;
    await api('/api/expe/departs/'+departId+'/palette-europe', {
      method:'PATCH',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify(body)
    });
    toast('Statut palette mis à jour');
    await loadExpePalettesEurope();
  }catch(e){
    toast(e.message||'Mise à jour impossible','error');
  }
}

function _expePalEuropeStatutLabel(s){
  if(s==='retournee') return 'Retournée';
  if(s==='perdue') return 'Perdue';
  return 'En attente';
}

function _expePalEuropeStatutBadge(s){
  const lbl = _expePalEuropeStatutLabel(s);
  const cls = 'expe-pal-eur-badge expe-pal-eur-badge--'+(s||'en_attente');
  return h('span',{className:cls},lbl);
}

function renderExpePalettesEurope(){
  const data = S.expePalettesEuropeData || {departs:[], recap_clients:[], totaux:{}};
  const departs = data.departs || [];
  const recap = data.recap_clients || [];
  const tot = data.totaux || {};
  const subTab = S.expePalEurSubTab || 'suivi';

  // Sous-onglets
  const subTabs = [
    {key:'suivi', label:'Suivi', icon:'clipboard'},
    {key:'recap', label:'Récap clients', icon:'users'},
  ];
  const subNav = h('div',{className:'nav-tabs',style:{marginBottom:'16px'}},
    ...subTabs.map(t=>h('button',{
      type:'button',
      className:'nav-tab'+(subTab===t.key?' active':''),
      onClick:()=>set({expePalEurSubTab:t.key})
    },iconEl(t.icon,14),' ',t.label))
  );

  // Bandeau totaux (commun aux deux sous-onglets)
  const totauxBlock = h('div',{className:'expe-pal-eur-totaux'},
    h('div',{className:'expe-pal-eur-tot-card'},
      h('div',{className:'expe-pal-eur-tot-lbl'},'Total envoyées'),
      h('div',{className:'expe-pal-eur-tot-val'},String(tot.nb_pal_envoyees||0))
    ),
    h('div',{className:'expe-pal-eur-tot-card expe-pal-eur-tot-card--ok'},
      h('div',{className:'expe-pal-eur-tot-lbl'},'Retournées'),
      h('div',{className:'expe-pal-eur-tot-val'},String(tot.nb_pal_retournees||0))
    ),
    h('div',{className:'expe-pal-eur-tot-card expe-pal-eur-tot-card--warn'},
      h('div',{className:'expe-pal-eur-tot-lbl'},'En attente'),
      h('div',{className:'expe-pal-eur-tot-val'},String(tot.nb_pal_en_attente||0))
    ),
    h('div',{className:'expe-pal-eur-tot-card expe-pal-eur-tot-card--bad'},
      h('div',{className:'expe-pal-eur-tot-lbl'},'Perdues'),
      h('div',{className:'expe-pal-eur-tot-val'},String(tot.nb_pal_perdues||0))
    )
  );

  // Filtres
  const statutSel = h('select',{
    value:S.expePalettesEuropeStatutFilter||'',
    onChange:e=>{
      S.expePalettesEuropeStatutFilter = e.target.value;
      void loadExpePalettesEurope();
    }
  });
  ['','en_attente','retournee','perdue'].forEach(v=>{
    const lbl = v===''?'Tous statuts':_expePalEuropeStatutLabel(v);
    const opt = h('option',{value:v},lbl);
    if((S.expePalettesEuropeStatutFilter||'')===v) opt.selected=true;
    statutSel.appendChild(opt);
  });

  const searchInp = h('input',{
    id:'expe-pal-eur-search',
    type:'search',
    placeholder:'Rechercher (client, ARC, BL…)',
    value:S.expePalettesEuropeQuery||'',
    style:{flex:'1',minWidth:'240px',padding:'8px 12px',borderRadius:'8px',
      border:'1px solid var(--border)',background:'var(--bg)',color:'var(--text)',fontSize:'13px'}
  });
  let _palEurSearchT = null;
  searchInp.addEventListener('input',e=>{
    S.expePalettesEuropeQuery = e.target.value;
    if(_palEurSearchT) clearTimeout(_palEurSearchT);
    _palEurSearchT = setTimeout(()=>void loadExpePalettesEurope(), 380);
  });

  // Vue récap par client (cards)
  const recapCards = recap.length ? h('div',{className:'expe-pal-eur-recap'},
    ...recap.map(r=>{
      const solde = (parseFloat(r.nb_pal_en_attente)||0);
      return h('div',{className:'expe-pal-eur-recap-card'+(solde>0?' expe-pal-eur-recap-card--debt':'')},
        h('div',{className:'expe-pal-eur-recap-client'},r.client||'—'),
        h('div',{className:'expe-pal-eur-recap-row'},
          h('span',{className:'expe-pal-eur-recap-lbl'},'Envoyées'),
          h('span',{className:'expe-pal-eur-recap-val'},String(r.nb_pal_envoyees||0))
        ),
        h('div',{className:'expe-pal-eur-recap-row'},
          h('span',{className:'expe-pal-eur-recap-lbl'},'Retournées'),
          h('span',{className:'expe-pal-eur-recap-val expe-pal-eur-recap-val--ok'},String(r.nb_pal_retournees||0))
        ),
        h('div',{className:'expe-pal-eur-recap-row'},
          h('span',{className:'expe-pal-eur-recap-lbl'},'Perdues'),
          h('span',{className:'expe-pal-eur-recap-val expe-pal-eur-recap-val--bad'},String(r.nb_pal_perdues||0))
        ),
        h('div',{className:'expe-pal-eur-recap-row expe-pal-eur-recap-row--solde'},
          h('span',{className:'expe-pal-eur-recap-lbl'},'En attente'),
          h('span',{className:'expe-pal-eur-recap-val'+(solde>0?' expe-pal-eur-recap-val--warn':'')},String(solde))
        ),
        h('button',{type:'button',className:'btn-ghost',
          style:{fontSize:'11px',padding:'4px 8px',marginTop:'8px',width:'100%'},
          onClick:()=>{S.expePalettesEuropeClientFilter = r.client || ''; void loadExpePalettesEurope();}
        },'Filtrer ses départs')
      );
    })
  ) : h('div',{style:{padding:'18px',color:'var(--muted)',fontSize:'13px',textAlign:'center'}},
    'Aucune palette Europe enregistrée.');

  // Tableau des départs palette Europe
  const head = h('tr',null,
    ...['Date enl.','Client','Transp.','ARC','N° BL','Pal.','Statut','Date retour','Note','Actions'].map(t=>h('th',null,t))
  );
  const bodyRows = departs.length ? departs.map(r=>{
    const statut = r.palette_europe_statut || 'en_attente';
    const noteInp = h('input',{
      type:'text',
      placeholder:'Note…',
      value:r.palette_europe_note||'',
      style:{width:'100%',padding:'4px 8px',fontSize:'11px',background:'var(--bg)',
        border:'1px solid var(--border)',borderRadius:'6px',color:'var(--text)'}
    });
    let _noteT = null;
    noteInp.addEventListener('input',e=>{
      const v = e.target.value;
      if(_noteT) clearTimeout(_noteT);
      _noteT = setTimeout(async()=>{
        try{
          await api('/api/expe/departs/'+r.id+'/palette-europe',{
            method:'PATCH',
            headers:{'Content-Type':'application/json'},
            body: JSON.stringify({note: v})
          });
        }catch(e){ /* silencieux */ }
      }, 800);
    });
    const dateInp = h('input',{
      type:'date',
      value:(r.palette_europe_date_retour||'').slice(0,10),
      style:{padding:'4px 8px',fontSize:'12px',background:'var(--bg)',
        border:'1px solid var(--border)',borderRadius:'6px',color:'var(--text)'}
    });
    dateInp.addEventListener('change',async(e)=>{
      const v = e.target.value;
      try{
        await api('/api/expe/departs/'+r.id+'/palette-europe',{
          method:'PATCH',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify({date_retour: v, statut: v ? 'retournee' : statut})
        });
        toast('Date retour enregistrée');
        await loadExpePalettesEurope();
      }catch(e){ toast(e.message||'Erreur','error'); }
    });
    return h('tr',null,
      h('td',null,(r.date_enlevement||'').slice(0,10)),
      h('td',null,r.client||'—'),
      h('td',null,(c=>c?trpTag(r.transporteur||'—',c):(r.transporteur||'—'))(trpColorFromRow(r))),
      h('td',{style:{fontFamily:'monospace',fontSize:'12px'}},r.arc||'—'),
      h('td',{style:{fontFamily:'monospace',fontSize:'12px'}},r.no_bl||'—'),
      h('td',{style:{textAlign:'right',fontWeight:'700'}},r.nb_palette!=null?String(r.nb_palette):'—'),
      h('td',null,_expePalEuropeStatutBadge(statut)),
      h('td',null,dateInp),
      h('td',{style:{minWidth:'140px'}},noteInp),
      h('td',{className:'expe-pal-eur-acts-cell'},
        h('div',{className:'expe-pal-eur-acts'},
          statut!=='retournee' ? h('button',{type:'button',className:'expe-pal-eur-act expe-pal-eur-act--ok',
            title:'Marquer comme retournée (date du jour)',
            onClick:()=>expeChangePaletteEuropeStatut(r.id,'retournee',expeParisDayISO())
          },iconEl('check-circle',14)) : null,
          statut!=='perdue' ? h('button',{type:'button',className:'expe-pal-eur-act expe-pal-eur-act--bad',
            title:'Marquer comme perdue',
            onClick:()=>{
              if(!confirm('Marquer cette palette comme perdue ?')) return;
              expeChangePaletteEuropeStatut(r.id,'perdue', null);
            }
          },iconEl('x',14)) : null,
          statut!=='en_attente' ? h('button',{type:'button',className:'expe-pal-eur-act',
            title:'Réinitialiser le statut (en attente)',
            onClick:()=>expeChangePaletteEuropeStatut(r.id,'en_attente', '')
          },iconEl('rotate-ccw',13)) : null
        )
      )
    );
  }) : [h('tr',null,h('td',{colSpan:10,style:{color:'var(--muted)',padding:'18px',textAlign:'center'}},
    S.expePalettesEuropeLoading?'Chargement…':'Aucun départ palette Europe pour ces filtres'))];

  // Bloc Suivi : filtre + tableau détaillé
  const suiviBlock = h('div',{className:'card'},
    h('div',{className:'card-header',style:{display:'flex',gap:'10px',alignItems:'center',flexWrap:'wrap'}},
      h('h3',{className:'expe-mobile-hide-head'},'Départs détaillés'),
      h('div',{style:{display:'flex',gap:'10px',alignItems:'center',marginLeft:'auto',flexWrap:'wrap'}},
        statutSel,
        searchInp,
        S.expePalettesEuropeClientFilter ? h('button',{type:'button',className:'btn-ghost',
          style:{fontSize:'12px',padding:'4px 10px'},
          onClick:()=>{S.expePalettesEuropeClientFilter=''; void loadExpePalettesEurope();}
        },'× Filtre : '+S.expePalettesEuropeClientFilter) : null
      )
    ),
    h('div',{style:{overflowX:'auto'}},
      h('table',{className:'table-std expe-departs-table'},
        h('thead',null,head),
        h('tbody',null,...bodyRows)
      )
    )
  );

  // Bloc Récap : cards par client
  const recapBlock = h('div',{className:'card'},
    h('div',{className:'card-header'},
      h('h3',{className:'expe-mobile-hide-head'},'Récap par client'),
      h('div',{style:{fontSize:'11px',color:'var(--muted)',marginLeft:'auto'}},
        recap.length+' client'+(recap.length>1?'s':'')+' avec palette Europe')
    ),
    h('div',{style:{padding:'14px 18px'}}, recapCards)
  );

  return h('div',null,
    subNav,
    totauxBlock,
    subTab==='recap' ? recapBlock : suiviBlock
  );
}

function renderExpeSuiviDeparts(){
  const btnBarStyle={display:'flex',gap:'10px',alignItems:'center',flexWrap:'wrap'};
  const btnPairStyle={
    minWidth:'160px',
    padding:'10px 16px',
    fontSize:'13px',
    borderRadius:'10px',
    fontWeight:'800',
    whiteSpace:'nowrap',
    display:'inline-flex',
    alignItems:'center',
    justifyContent:'center',
    gap:'8px',
    lineHeight:1
  };
  const topBar=h('div',{className:'card',style:{marginBottom:'12px'}},
    h('div',{className:'card-header',style:{display:'flex',justifyContent:'flex-start',alignItems:'center',gap:'12px',flexWrap:'wrap'}},
      h('h3',{className:'expe-mobile-hide-head'},'Départs programmés'),
      expeCanWrite()?h('div',{style:btnBarStyle},
        h('button',{className:'btn',type:'button',style:btnPairStyle,onClick:()=>expeOpenDepartModal(null,'new')},iconEl('plus',14),' Ajouter')
      ):null
    )
  );
  const rows=S.expeDepartList||[];
  const head=h('tr',null,
    ...['Date enl.','Affr.','Transp.','Client','Destination','Réf SIFA','ARC','Cde transp.','N° BL','Type pal.','Pal.','Poids kg','Liv. prév.',''].map(t=>h('th',null,t))
  );
  function formatDateFr(iso){
    if(!iso||iso.length<10)return iso||'—';
    const d=new Date(iso+'T00:00:00');
    const jours=['Dimanche','Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi'];
    const mois=['janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre'];
    return jours[d.getDay()]+' '+d.getDate()+' '+mois[d.getMonth()]+' '+d.getFullYear();
  }
  let prevDate=null;
  const bodyRows=[];
  rows.forEach(r=>{
    const dateEnl=(r.date_enlevement||'').slice(0,10);
    if(dateEnl!==prevDate){
      bodyRows.push(
        h('tr',{className:'expe-day-sep-row'},
          h('td',{colSpan:14,className:'expe-day-sep-cell'},
            h('span',{className:'expe-day-sep-label'},formatDateFr(dateEnl))
          )
        )
      );
      prevDate=dateEnl;
    }
    bodyRows.push(h('tr',null,
      h('td',null,dateEnl),
      h('td',null,r.affreteurs||'—'),
      h('td',null,(c=>c?trpTag(r.transporteur||'—',c):(r.transporteur||'—'))(trpColorFromRow(r))),
      h('td',null,r.client||'—'),
      h('td',{style:{maxWidth:'140px',fontSize:'12px'}},r.code_postal_destination||'—'),
      h('td',{style:{fontFamily:'monospace',fontSize:'12px'}},r.ref_sifa||'—'),
      h('td',{style:{fontFamily:'monospace',fontSize:'12px'}},r.arc||'—'),
      h('td',{style:{fontFamily:'monospace',fontSize:'12px'}},r.no_cde_transport||'—'),
      h('td',{style:{fontFamily:'monospace',fontSize:'12px'}},r.no_bl||'—'),
      h('td',{style:{fontSize:'12px',maxWidth:'120px'}},expePaletteTypeLabel(r)),
      h('td',null,r.nb_palette!=null?String(r.nb_palette):'—'),
      h('td',null,r.poids_total_kg!=null?String(r.poids_total_kg):'—'),
      h('td',null,(r.date_livraison||'').slice(0,10)||'—'),
      expeCanWrite()?h('td',{className:'expe-dep-actions-td'},
        expeDepartActsGrid([
          r.code_postal_destination?h('button',{className:'btn-ghost expe-dep-ab',type:'button',
            title:'Ouvrir une demande de devis préremplie avec les données de ce départ',
            onClick:()=>ouvrirDevisDepuisDepart(r.id,parseFloat(r.poids_total_kg)||0,parseFloat(r.nb_palette)||0,String(r.code_postal_destination||''))},expeDevisIcon(14)):null,
          (r.code_postal_destination&&(r.poids_total_kg||r.nb_palette))?h('button',{className:'btn-ghost expe-dep-ab',type:'button',
            title:'Comparer les tarifs des transporteurs pour ce départ',
            onClick:()=>ouvrirComparateurDepuisDepart(r.id,parseFloat(r.poids_total_kg)||0,parseFloat(r.nb_palette)||0,String(r.code_postal_destination||''))},expeCompareIcon(14)):null,
          h('button',{className:'btn-ghost expe-dep-ab',type:'button',title:'Dupliquer ce départ en nouvelle saisie',
            onClick:()=>expeOpenDepartModal(r,'new')},iconEl('copy',14)),
          h('button',{className:'btn-ghost expe-dep-ab',type:'button',title:'Modifier les informations de ce départ',
            onClick:()=>expeOpenDepartModal(r,'edit')},iconEl('edit',14)),
          h('button',{className:'btn-danger expe-dep-ab',type:'button',title:'Supprimer définitivement ce départ',onClick:async()=>{
            if(!confirm('Supprimer ce départ ?')) return;
            try{
              await api('/api/expe/departs/'+r.id,{method:'DELETE'});
              toast('Départ supprimé');
              await loadExpeDepartJour();
            }catch(e){toast(e.message||'Suppression impossible','error');}
          }},iconEl('trash',14))
        ],h('button',{className:'btn expe-dep-valider-btn',type:'button',
          title:'Valider ce départ et l\'archiver dans l\'historique',
          onClick:()=>expeValiderDepart(r.id)},'Valider'))
      ):h('td',null,'—')
    ));
  });
  const body=rows.length?bodyRows:[h('tr',null,h('td',{colSpan:14,style:{color:'var(--muted)'}},S.expeDepartLoading?'Chargement…':'Aucun départ en attente pour ce jour'))];
  const listCard=h('div',{className:'card'},
    h('div',{className:'card-header'},h('h3',{className:'expe-mobile-hide-head'},'Départs programmés (en attente de validation)')),
    h('div',{style:{overflowX:'auto'}},h('table',{className:'table-std expe-departs-table'},h('thead',null,head),h('tbody',null,...body)))
  );
  return h('div',null,topBar,listCard);
}

function renderExpeHistoriqueDeparts(){
  const qInp=h('input',{
    id:'expe-hist-search',
    type:'search',
    placeholder:'Réf. SIFA, client, ARC, BL, type palette, transporteur…',
    value:S.expeDepartHistQ||'',
    style:{width:'100%',maxWidth:'560px',padding:'10px 12px',borderRadius:'8px',border:'1px solid var(--border)',background:'var(--bg)',color:'var(--text)',marginBottom:'12px'},
    onInput:e=>{
      // Ne pas déclencher un render à chaque caractère (sinon perte de focus).
      S.expeDepartHistQ = e.target.value;
      scheduleExpeHistSearch();
    }
  });
  const rows=S.expeDepartHist||[];
  const total=S.expeDepartHistTotal||0;
  const page=S.expeDepartHistPage||1;
  const pages=S.expeDepartHistPages||1;
  const limit=50;
  const from=total===0?0:(page-1)*limit+1;
  const to=Math.min(page*limit,total);
  const head=h('tr',null,
    ...['Validé le','Date enl.','Client','Réf SIFA','ARC','Cde transp.','N° BL','Transp.','Type pal.','Pal.','Poids','Liv. prév.',''].map(t=>h('th',null,t))
  );
  const body=rows.length?rows.map(r=>h('tr',null,
    h('td',{style:{fontSize:'12px',whiteSpace:'nowrap'}},(r.validated_at||'').replace('T',' ').slice(0,16)||'—'),
    h('td',null,(r.date_enlevement||'').slice(0,10)),
    h('td',null,r.client||'—'),
    h('td',{style:{fontFamily:'monospace',fontSize:'12px'}},r.ref_sifa||'—'),
    h('td',{style:{fontFamily:'monospace',fontSize:'12px'}},r.arc||'—'),
    h('td',{style:{fontFamily:'monospace',fontSize:'12px'}},r.no_cde_transport||'—'),
    h('td',{style:{fontFamily:'monospace',fontSize:'12px'}},r.no_bl||'—'),
    h('td',null,(c=>c?trpTag(r.transporteur||'—',c):(r.transporteur||'—'))(trpColorFromRow(r))),
    h('td',{style:{fontSize:'12px',maxWidth:'120px'}},expePaletteTypeLabel(r)),
    h('td',null,r.nb_palette!=null?String(r.nb_palette):'—'),
    h('td',null,r.poids_total_kg!=null?String(r.poids_total_kg):'—'),
    h('td',null,(r.date_livraison||'').slice(0,10)||'—'),
    expeCanWrite()?h('td',{className:'expe-dep-actions-td'},
      expeDepartActsGrid([
        h('button',{className:'btn-ghost expe-dep-ab',type:'button',title:'Dupliquer ce départ en nouvelle saisie',
          onClick:()=>expeOpenDepartModal(r,'new')},iconEl('copy',14)),
        h('button',{className:'btn-ghost expe-dep-ab',type:'button',title:'Modifier les informations de ce départ',
          onClick:()=>expeOpenDepartModal(r,'edit')},iconEl('edit',14)),
        h('button',{className:'btn-danger expe-dep-ab',type:'button',title:'Supprimer définitivement ce départ de l\'historique',onClick:async()=>{
          if(!confirm('Supprimer ce départ ?')) return;
          try{
            await api('/api/expe/departs/'+r.id,{method:'DELETE'});
            toast('Départ supprimé');
            await loadExpeDepartHistorique();
          }catch(e){toast(e.message||'Suppression impossible','error');}
        }},iconEl('trash',14))
      ],
      h('button',{className:'btn expe-dep-invalider-btn',type:'button',
        title:'Annuler la validation et remettre ce départ dans le suivi du jour',
        onClick:()=>void expeInvaliderDepart(r.id)},'Invalider'))
    ):h('td',null,'—')
  )):[h('tr',null,h('td',{colSpan:13,style:{color:'var(--muted)'}},S.expeDepartHistLoading?'Chargement…':'Aucune entrée (ou affiner la recherche)'))];
  const pager=h('div',{className:'expe-hist-pager'},
    h('span',{className:'page-info'},
      total===0?'Aucun résultat':(from+'–'+to+' / '+total.toLocaleString('fr')+(pages>1?' · page '+page+'/'+pages:''))
    ),
    h('button',{type:'button',className:'page-btn',disabled:page<=1,onClick:()=>expeHistChangePage(-1)},'‹ Précédent'),
    h('button',{type:'button',className:'page-btn',disabled:page>=pages,onClick:()=>expeHistChangePage(1)},'Suivant ›')
  );
  return h('div',null,
    h('div',{className:'card',style:{marginBottom:'12px',padding:'14px 18px'}},
      h('h3',{style:{fontSize:'14px',fontWeight:'700',marginBottom:'8px'}},'Recherche'),
      h('div',{className:'expe-help',style:{marginBottom:'8px'}},'Mots séparés par des espaces : tous doivent être trouvés (ref., client, ARC, BL, etc.). Insensible à la casse. Résultats paginés par 50.'),
      qInp
    ),
    h('div',{className:'card'},
      h('div',{className:'card-header'},h('h3',{className:'expe-mobile-hide-head'},'Historique des départs validés')),
      h('div',{style:{overflowX:'auto'}},h('table',{className:'table-std expe-hist-table'},h('thead',null,head),h('tbody',null,...body))),
      pager
    )
  );
}

function renderExpeSuiviDepartsWithSubtabs(){
  const sub=S.expeDepartSubTab||'jour';
  const tabs=[
    {key:'jour',label:'Départs programmés',icon:'clipboard'},
    {key:'historique',label:'Historique',icon:'folder'},
  ];
  const subNav=h('div',{className:'nav-tabs',style:{marginBottom:'16px'}},
    ...tabs.map(t=>h('button',{
      type:'button',
      className:'nav-tab'+(sub===t.key?' active':''),
      onClick:()=>set({expeDepartSubTab:t.key})
    },iconEl(t.icon,14),' ',t.label))
  );
  const body=sub==='historique'?renderExpeHistoriqueDeparts():renderExpeSuiviDeparts();
  // Modal monté au niveau parent : reste accessible quel que soit le sous-onglet
  // (sinon, modifier une ligne depuis l'Historique forçait à revenir sur "Départs du jour").
  return h('div',null,subNav,body,renderExpeDepartModal());
}

function renderExpe(){
  const isLight=document.body.classList.contains('light');
  if(S.expeTab==='historique_departs'){
    S.expeTab='suivi_departs';
    S.expeDepartSubTab='historique';
  }
  if(S.expeTab==='dashboard')S.expeTab='suivi_departs';
  const tab=S.expeTab||'suivi_departs';
  const sub=S.expeDepartSubTab||'jour';
  const loadKey=tab==='suivi_departs'?tab+'_'+sub:tab;
  if(loadKey!==_expeLastRenderedInnerTab){
    _expeLastRenderedInnerTab=loadKey;
    if(tab==='suivi_departs'){
      if(!T.list.length&&!T.loading)void loadTransporteurs();
      if(sub==='jour')void loadExpeDepartJour();
      else void loadExpeDepartHistorique();
    }else if(tab==='comparateur'){if(!T.list.length&&!T.loading)void loadTransporteurs();}
    else if(tab==='devis'){void chargerDemandes();if(!T.list.length&&!T.loading)void loadTransporteurs();}
    else if(tab==='prospects'){void chargerProspects();}
    else if(tab==='transporteurs'&&!T.pageLoaded){T.pageLoaded=true;void loadTransporteurs();}
    else if(tab==='palettes_europe'){void loadExpePalettesEurope();}
  }

  const sidebar=h('nav',{className:'sidebar'},
    h('div',{className:'logo'},
      h('div',{className:'logo-brand'},'My',h('span',null,'Expé')),
      h('div',{className:'logo-sub'},'by SIFA')
    ),
    // Sections collapsibles
    (()=>{
      const SECTIONS = [
        { key:'ops', label:'Opérations', items:[
          {tab:'suivi_departs',  ico:'clipboard', label:'Départs'},
          {tab:'palettes_europe',ico:'pallet',    label:'Palettes Europe'},
        ]},
        { key:'prep', label:'Préparation envoi', items:[
          {tab:'comparateur',ico:'sliders',   label:'Comparateur tarifs'},
          {tab:'devis',      ico:'mail',      label:'Devis transporteurs'},
          {tab:'poids',      ico:'calculator',label:'Calcul poids'},
        ]},
        { key:'ref', label:'Référentiel', items:[
          {tab:'transporteurs',ico:'truck',label:'Transporteurs'},
          {tab:'prospects',    ico:'users',label:'Prospects'},
        ]},
      ];
      const lsKey = (k)=>'mysifa.expe.section.'+k;
      const isCollapsed = (k)=>{
        try{ return localStorage.getItem(lsKey(k)) === 'collapsed'; }catch(e){ return false; }
      };
      const toggleSection = (k)=>{
        try{
          const cur = isCollapsed(k);
          localStorage.setItem(lsKey(k), cur?'expanded':'collapsed');
        }catch(e){}
        render();
      };
      const wrap = h('div',{className:'expe-sidebar-sections'});
      SECTIONS.forEach(sec=>{
        const collapsed = isCollapsed(sec.key);
        const hasActive = sec.items.some(it=>it.tab===tab);
        const header = h('button',{
          type:'button',
          className:'expe-sec-header'+(collapsed?' collapsed':'')+(hasActive?' has-active':''),
          onClick:()=>toggleSection(sec.key),
          'aria-expanded': String(!collapsed)
        },
          h('span',{className:'expe-sec-chev'},iconEl(collapsed?'chevron-right':'chevron-down',12)),
          h('span',{className:'expe-sec-label'},sec.label)
        );
        wrap.appendChild(header);
        if(!collapsed){
          const body = h('div',{className:'expe-sec-body'});
          sec.items.forEach(it=>{
            body.appendChild(
              h('button',{
                className:'nav-btn'+(tab===it.tab?' active':''),
                onClick:()=>set({expeTab:it.tab})
              }, iconEl(it.ico,15), '  ', it.label)
            );
          });
          wrap.appendChild(body);
        }
      });
      return wrap;
    })(),
    renderExpePlanningNav(),
    h('div',{className:'sidebar-bottom'},
      h('button',{className:'nav-btn back-mysifa',onClick:()=>{window.location.href='/'}},
        '← Retour ',h('span',{className:'wm'},'My',h('span',null,'Sifa'))
      ),
      sidebarUserChip(S.user),
      (()=>{
        const b=h('button',{className:'support-btn',title:'Contacter le support',onClick:()=>set({contactOpen:true})});
        const ico=h('span',{className:'support-ico'});
        try{ico.innerHTML=(window.MySifaSupport&&typeof window.MySifaSupport.iconSvg==='function')?window.MySifaSupport.iconSvg():'';}catch(e){ico.innerHTML='';}
        b.appendChild(ico);b.appendChild(h('span',null,'Contacter le support'));return b;
      })(),
      h('button',{className:'theme-btn',onClick:()=>{MySifaTheme.toggleMode();render();}},
        h('span',{className:'theme-ico'},iconEl(isLight?'sun':'moon',16)),
        h('span',{className:'theme-label'},isLight?'Mode clair':'Mode sombre')
      ),
      h('button',{className:'logout-btn',onClick:doLogout},iconEl('log-out',14),' Déconnexion')
    )
  );
  const topbar=h('div',{className:'mobile-topbar'},
    h('button',{type:'button',className:'mobile-menu-btn',onClick:toggleSidebar,'aria-label':'Menu'},iconEl('menu',20)),
    h('div',null,
      h('div',{className:'mobile-topbar-title'},'MyExpé'),
      h('div',{className:'mobile-topbar-sub'},
        tab==='suivi_departs'?(sub==='historique'?'Historique départs':'Départs programmés'):
        tab==='palettes_europe'?'Suivi des palettes Europe consignées':
        tab==='transporteurs'?'Transporteurs':tab==='devis'?'Demandes de devis':tab==='prospects'?'Prospects transporteurs':tab==='poids'?'Calcul poids':'Comparateur tarifs')
    ),
    h('button',{type:'button',className:'mobile-home-btn',onClick:()=>{window.location.href='/'},'aria-label':'Accueil'},iconEl('home',20))
  );

  const content=tab==='suivi_departs'?renderExpeSuiviDepartsWithSubtabs():
    tab==='palettes_europe'?renderExpePalettesEurope():
    tab==='transporteurs'?renderExpeTransporteurs():tab==='poids'?renderExpePoids():
    tab==='devis'?renderExpeDevisSection():tab==='prospects'?renderExpeProspectsSection():
    renderExpeComparateur();
  // Motion : cascade d'entree au changement d'onglet uniquement. On pose
  // data-page-enter sur la .container (topbar, h1, sous-titre, contenu
  // cascadent ensemble) — effet plus visible que sur le seul wrapper du tab.
  const _moExpeKey=tab+'|'+(tab==='suivi_departs'?sub:'');
  const _moExpeEnter=(window._moExpeLastKey!==_moExpeKey);
  window._moExpeLastKey=_moExpeKey;
  // 2e niveau : data-page-enter sur le contenu du tab — les sous-onglets et
  // les cartes internes cascadent en parallele de la cascade .container.
  if(_moExpeEnter && content && content.nodeType===1){
    try{ content.setAttribute('data-page-enter',''); }catch(_){}
  }
  const contentWrap=content;

  return h('div',null,
    S.sidebarOpen?h('div',{className:'sidebar-overlay',onClick:closeSidebar}):null,
    h('div',{className:'app'},
      sidebar,
      h('main',{className:'main'},
        h('div',Object.assign({className:'container'},_moExpeEnter?{'data-page-enter':''}:{},(tab==='suivi_departs'||tab==='palettes_europe')?{style:{maxWidth:'1600px'}}:{}),
          topbar,
          h('h1',null,'MyExpé'),
          !expeCanWrite()?h('div',{className:'readonly-notice',style:{marginBottom:'12px'}},iconEl('eye',13),' Lecture seule — consultation des départs, transporteurs et délais'):null,
          h('div',{className:'subtitle'},
            tab==='suivi_departs'?(sub==='historique'?'Recherche multi-critères sur les départs validés'
              :'Enregistrement des enlèvements et validation vers l\'historique')
            :tab==='palettes_europe'?'Suivi des palettes Europe consignées — quels clients, combien, et combien sont revenues'
            :tab==='comparateur'?'Comparaison des transporteurs selon les grilles tarifaires actives en base'
            :tab==='devis'?'Prospection parallèle — demandes de tarif aux transporteurs'
            :tab==='prospects'?'Transporteurs hors référentiel — suivi de démarchage'
            :tab==='poids'?'Estimation du poids d\'un envoi d\'étiquettes'
            :'Référentiel transporteurs, zones et tarifs'),
          contentWrap
        )
      )
    ),
    renderExpeTranspPanel(),
    renderExpeTransporteurModal(),
    renderExpeDevisModal(),
    S.expeShowContacts?renderExpeContactModal():null
  );
}

// ── Loaders ─────────────────────────────────────────────────────
async function loadFilters(){
  try{
    S.filters=await api('/api/filters')||{};
    S.OPS_CONFIG=await api('/api/config/operations')||{};
    // Pour utilisateur fabrication: auto-sélectionner son nom comme filtre opérateur
    // pour qu'il voie immédiatement ses données de saisie
    if(isFab(S.user) && S.user && S.user.nom){
      const userOp = S.user.nom;
      const ops = S.filters.operators || [];
      // Si l'utilisateur n'est pas déjà dans la sélection et qu'il existe dans la liste
      if(!S.fv.operateurs.length && ops.includes(userOp)){
        S.fv.operateurs = [userOp];
      }
    }
  }catch{}
}
function buildParams(){
  const p=new URLSearchParams();
  if(canViewAllProd(S.user)){
    (S.fv.operateurs||[]).forEach(o=>p.append('operateur',o));
    (S.fv.dossiers||[]).forEach(d=>p.append('no_dossier',d));
  }
  (S.fv.machines||[]).forEach(m=>p.append('machine',m));
  if(S.fv.date_from)p.set('date_from',S.fv.date_from);
  if(S.fv.date_to)p.set('date_to',S.fv.date_to);
  return p;
}

async function loadHist(){const d=await api('/api/dashboard/historique?'+buildParams());if(d)S.historique=d;}
async function loadProd(){const d=await api('/api/dashboard/production?'+buildParams());if(d)S.production=d;}
async function loadMachineStatus(){
  try{
    const d=await api('/api/production/machine-status');
    if(d){
      S.machineStatus=d;
      // Mise à jour DOM ciblée sans re-render global
      updateMachineStatusDOM();
    }
  }catch(e){}
}
function updateMachineStatusDOM(){
  const ms=S.machineStatus;
  const ICONS={production:'▶',calage:'⚙',arret:'⛔',changement:'↻',nettoyage:'🧹',eteinte:'○',autre:'·'};
  const DUREE_LABEL={production:'En production depuis',calage:'En calage depuis',arret:'En arrêt depuis',changement:'En changement depuis',nettoyage:'En nettoyage depuis',eteinte:'Éteinte depuis',autre:'Depuis'};
  function fmtDuree(min){
    if(min==null||min<0)return null;
    if(min<1)return 'à l\'instant';
    const h=Math.floor(min/60),m=min%60;
    if(h===0)return m+' min';
    return m===0?(h+'h'):(h+'h '+m+'min');
  }
  const grid=document.querySelector('.mst-grid');
  if(!grid)return;
  const cards=grid.querySelectorAll('.mst-card');
  cards.forEach((card,idx)=>{
    const mkey=idx===0?'C1':'C2';
    const m=ms&&ms[mkey];
    const sk=m?(m.statut_key||'eteinte'):'eteinte';
    const label=m?(m.statut_label||'Éteinte'):'Éteinte';
    const nom=m?m.nom:(mkey==='C1'?'Cohésio 1':'Cohésio 2');
    const op=m?(m.operateur||''):'';
    const dos=m?m.dossier:null;
    const icon=ICONS[sk]||'·';
    const isOn=sk!=='eteinte';
    const dureeStr=m?fmtDuree(m.duree_min):null;
    const dureeLabel=DUREE_LABEL[sk]||'Depuis';
    // Mise à jour classes et contenu
    card.className='mst-card mst-'+sk;
    const headNom=card.querySelector('.mst-nom');
    if(headNom)headNom.textContent=nom;
    const dotWrap=card.querySelector('.mst-head div');
    if(dotWrap){
      dotWrap.innerHTML=isOn?'<span style="font-size:8px;color:#22c55e;animation:pulse 2s infinite;display:inline-block;border-radius:50%;width:8px;height:8px;background:#22c55e"></span><span class="mst-dot"></span>':'<span class="mst-dot"></span>';
    }
    const body=card.querySelector('.mst-body');
    if(body){
      let html='<div class="mst-statut">'+icon+' '+label+'</div>';
      if(dureeStr)html+='<div class="mst-duree">'+dureeLabel+' <span class="mst-duree-val">'+dureeStr+'</span></div>';
      if(op)html+='<div class="mst-op">👤 '+escapeHtml(op)+'</div>';
      if(dos&&dos.no_dossier){
        const isChangement=sk==='changement';
        const dosStyle=isChangement?' style="opacity:.6;filter:grayscale(.4)"':'';
        const dosPrefix=isChangement?'dossier précédent : #':'Dossier #';
        html+='<div class="mst-dos"'+dosStyle+'><div class="mst-dos-ref">'+dosPrefix+escapeHtml(dos.no_dossier)+'</div>';
        if(dos.client)html+='<div class="mst-dos-cli">'+escapeHtml(dos.client)+'</div>';
        if(dos.designation)html+='<div class="mst-dos-des">'+escapeHtml(dos.designation)+'</div>';
        html+='</div>';
      }
      body.innerHTML=html;
    }
  });
}
function escapeHtml(t){return(t||'').replace(/[&<>"']/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
async function loadImports(){const d=await api('/api/imports');if(d)set({imports:d});}
async function loadDos(){const d=await api('/api/dossiers');if(d)set({dossiers:d});}
async function loadMachines(){try{const d=await api('/api/planning/machines');if(d)set({machines:d});}catch(e){}}
async function loadRentPlanning(){
  try{
    const d=await api('/api/rentabilite/planning-entries');
    if(d)set({rentList:d});
  }catch(e){
    toast(e.message,'error');
  }
}
async function loadSaisies(opts){
  const off = (opts && typeof opts.offset==='number') ? opts.offset : (S.saisiesOffset||0);
  const lim = (opts && typeof opts.limit==='number') ? opts.limit : (S.saisiesLimit||200);
  const d=await api('/api/saisies?'+buildParams()+'&limit='+encodeURIComponent(String(lim))+'&offset='+encodeURIComponent(String(off)));
  if(!d)return;
  S.saisiesOffset = off;
  S.saisiesLimit = lim;
  if(opts&&opts.noRender)S.saisies=d;
  else set({saisies:d});
}
async function loadDevis(){const d=await api('/api/rentabilite/devis');if(d)set({devisList:d});}

async function loadComptaAcheteurs(){try{const d=await api('/api/compta/acheteurs');if(d)set({comptaAcheteurs:d});}catch(e){}}
async function loadComptaComptes(){try{const d=await api('/api/compta/comptes');if(d)set({comptaComptes:d});}catch(e){}}
async function loadComptaBanques(){try{const d=await api('/api/compta/banques');if(d)set({comptaBanques:d});}catch(e){}}

async function comptaTransformPaste(text){
  try{
    const t=String(text||'').trim();
    if(!t){toast('Collez au moins une ligne','error');return;}
    const r=await api('/api/compta/transform-paste',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t})});
    if(!r)return;
    set({comptaResult:r,comptaPasteText:t});
    toast('Transformation OK');
  }catch(e){toast(e.message,'error');}
}
async function comptaTransform(file){
  try{
    const fd=new FormData();
    fd.append('file',file);
    const r=await api('/api/compta/transform',{method:'POST',body:fd});
    if(!r)return;
    set({comptaResult:r});
    // Télécharger une copie du fichier importé (trace)
    try{
      const rows = Array.isArray(r.rows) ? r.rows : [];
      const dates = rows.map(x=>String((x&&x.date)||'').slice(0,10)).filter(d=>/^\d{4}-\d{2}-\d{2}$/.test(d));
      const dateFrom = dates.length ? dates.reduce((a,b)=>a<b?a:b) : '';
      const dateTo   = dates.length ? dates.reduce((a,b)=>a>b?a:b) : '';
      const sellers = [...new Set(rows.map(x=>String((x&&x.code_vendeur)||'').trim()).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'fr',{numeric:true}));
      const sellersTag = sellers.slice(0,6).join('-') + (sellers.length>6?('-'+String(sellers.length)+'v'):'');
      const errCount = rows.filter(x=>x && x.problem && String(x.compte||'').trim()==='').length;
      const today = (new Date()).toISOString().slice(0,10);
      const safe = (s)=>String(s||'').replace(/[\\/:*?"<>|]+/g,'_').replace(/\s+/g,' ').trim();
      const base = safe((file && file.name) ? file.name.replace(/\.(xlsx|xlsm|xls)$/i,'') : 'factor');
      const parts = [
        base,
        today,
        (dateFrom&&dateTo)?('du_'+dateFrom+'_au_'+dateTo):'',
        sellersTag?('vendeurs-'+sellersTag):'',
        'erreurs-'+String(errCount||0),
      ].filter(Boolean);
      const ext = (file && file.name && /\.[A-Za-z0-9]+$/.test(file.name)) ? file.name.slice(file.name.lastIndexOf('.')) : '.xlsx';
      const fname = safe(parts.join('_')) + ext;
      const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(file), download: fname });
      document.body.appendChild(a);
      a.click();
      setTimeout(()=>{ try{URL.revokeObjectURL(a.href);}catch(e){}; try{a.remove();}catch(e){}; }, 800);
    }catch(e){}
    toast('Transformation OK');
  }catch(e){
    toast(e.message,'error');
  }
}

async function comptaUpsertAcheteurs(items){
  try{
    await api('/api/compta/acheteurs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({items})});
    toast('Acheteurs mis à jour');
    loadComptaAcheteurs();
  }catch(e){toast(e.message,'error');}
}
async function comptaUpdateAcheteur(id,item){
  try{
    await api('/api/compta/acheteurs/'+id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(item)});
    toast('Acheteur modifié');
    set({comptaEditAcheteurId:null});
    loadComptaAcheteurs();
  }catch(e){toast(e.message,'error');}
}
async function comptaUpsertComptes(items){
  try{
    await api('/api/compta/comptes',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({items})});
    toast('Comptes mis à jour');
    loadComptaComptes();
  }catch(e){toast(e.message,'error');}
}
async function comptaUpdateCompte(id,item){
  try{
    await api('/api/compta/comptes/'+id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(item)});
    toast('Compte modifié');
    set({comptaEditCompteId:null});
    loadComptaComptes();
  }catch(e){toast(e.message,'error');}
}

async function comptaUpsertBanques(items){
  try{
    await api('/api/compta/banques',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({items})});
    toast('Code de banque enregistré.');
    loadComptaBanques();
  }catch(e){toast(e.message,'error');}
}
async function comptaUpdateBanque(id,item){
  try{
    await api('/api/compta/banques/'+id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(item)});
    toast('Code de banque modifié.');
    set({comptaEditBanqueId:null});
    loadComptaBanques();
  }catch(e){toast(e.message,'error');}
}
async function comptaDeleteBanque(id){
  if(!confirm('Supprimer ce code de banque ?'))return;
  try{await api('/api/compta/banques/'+id,{method:'DELETE'});loadComptaBanques();}catch(e){toast(e.message,'error');}
}

async function comptaDeleteAcheteur(id){
  if(!confirm('Supprimer cet acheteur ?'))return;
  try{await api('/api/compta/acheteurs/'+id,{method:'DELETE'});loadComptaAcheteurs();}catch(e){toast(e.message,'error');}
}
async function comptaDeleteCompte(id){
  if(!confirm('Supprimer ce compte ?'))return;
  try{await api('/api/compta/comptes/'+id,{method:'DELETE'});loadComptaComptes();}catch(e){toast(e.message,'error');}
}

async function comptaImportAcheteurs(file){
  try{
    const fd=new FormData();
    fd.append('file',file);
    const r=await api('/api/compta/import-acheteurs',{method:'POST',body:fd});
    if(!r)return;
    toast('Acheteurs importés');
    loadComptaAcheteurs();
  }catch(e){toast(e.message,'error');}
}
async function comptaImportComptes(file){
  try{
    const fd=new FormData();
    fd.append('file',file);
    const r=await api('/api/compta/import-comptes',{method:'POST',body:fd});
    if(!r)return;
    toast('Comptes importés');
    loadComptaComptes();
  }catch(e){toast(e.message,'error');}
}

async function deleteImport(id,fn){
  if(!confirm('Supprimer "'+fn+'" et toutes ses lignes ?'))return;
  try{const r=await api('/api/imports/'+id,{method:'DELETE'});if(!r)return;toast(r.lignes_supprimees+' lignes supprimées');loadImports();}
  catch(e){toast(e.message,'error');}
}
async function exportBlob(url,filename){
  try{const blob=await api(url);if(!blob)return;const a=Object.assign(document.createElement('a'),{href:URL.createObjectURL(blob),download:filename});document.body.appendChild(a);a.click();setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove();},1000);toast('Export téléchargé');}
  catch(e){toast(e.message,'error');}
}
async function saveSaisie(id,field,value){
  try{
    await api('/api/saisies/'+id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({[field]:value})});
    toast('Sauvegardé');
  }catch(e){toast(e.message,'error');}
}
async function addSaisie(body) {
  try {
    const r = await api('/api/saisies', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    if (!r) return;
    // Pousser dans undo avec l'id retourné par l'API
    pushUndo('add', { ...body, id: r.id });
    toast('Ligne ajoutée');
    await loadSaisies();
  } catch(e) { toast(e.message, 'error'); }
}
async function upload(f){
  try{const fd=new FormData();fd.append('file',f);const r=await api('/api/import',{method:'POST',body:fd});if(!r)return;let msg=r.rows_imported+' lignes importées';if(r.doublons_ignores>0)msg+=' ('+r.doublons_ignores+' doublons ignorés)';toast(msg);loadImports();loadFilters();}
  catch(e){toast(e.message,'error');}
}
async function createDos(d){try{await api('/api/dossiers',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});toast('Dossier créé');loadDos();}catch(e){toast(e.message,'error');}}
async function updStatut(id,s){try{await api('/api/dossiers/'+id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({statut:s})});loadDos();}catch{}}
async function applyF(){
  const needSais=S.page==='saisies' || (S.page==='production' && (S.subPage||'kpis')==='saisies');
  // Quand on change les filtres, repartir en haut (offset 0)
  S.saisiesOffset = 0;
  await Promise.all([
    loadHist(),
    loadProd(),
    needSais?loadSaisies({noRender:true}):Promise.resolve()
  ]);
  render();
}

// ── Login ───────────────────────────────────────────────────────
function renderLogin(){
  const isLight=document.body.classList.contains('light');
  const errEl=h('div',{className:'login-error'+(S.loginError?' show':''),id:'login-error'},S.loginError||'');
  const emailI=h('input',{type:'text',id:'login-email',name:'email',autocomplete:'username',placeholder:'identifiant ou email'});
  const pwdI=h('input',{type:'password',id:'login-password',name:'password',autocomplete:'current-password',placeholder:'••••••••'});
  const pwdToggle=h('button',{type:'button',className:'pwd-toggle','aria-label':'Afficher le mot de passe','aria-pressed':'false',
    onClick:()=>{
      const shown=pwdI.type==='text';
      pwdI.type=shown?'password':'text';
      pwdToggle.setAttribute('aria-pressed',shown?'false':'true');
      pwdToggle.setAttribute('aria-label',shown?'Afficher le mot de passe':'Masquer le mot de passe');
      pwdToggle.innerHTML='';
      pwdToggle.appendChild(iconEl(shown?'eye':'eye-off',18));
      try{pwdI.focus();const v=pwdI.value;pwdI.value='';pwdI.value=v;}catch(e){}
    }
  });
  pwdToggle.appendChild(iconEl('eye',18));
  const pwdWrap=h('div',{className:'pwd-wrap'},pwdI,pwdToggle);
  const submit=e=>{
    e.preventDefault();
    if(S.loginSubmitting)return;
    doLogin(emailI.value,pwdI.value);
  };
  const themeBtn=h('button',{type:'button',className:'login-theme-btn','aria-label':'Basculer thème clair/sombre',
    onClick:()=>{
      try{
        const _p=MySifaTheme.loadPrefs();
        const _nm=_p.mode==='light'?'dark':'light';
        // Sauver UNIQUEMENT le mode (la palette/style restent ceux du user pour le post-login),
        // puis ré-appliquer le rendu neutre pétrole sur la page de login.
        MySifaTheme.setPrefs({mode:_nm});
        MySifaTheme.applyPrefs({mode:_nm,palette:'mysifa',style:'defaut',bgAnim:_p.bgAnim});
      }catch(e){}
      render();
    }},
    h('span',{className:'theme-ico'},iconEl(isLight?'sun':'moon',16)),
    h('span',{className:'theme-label'},isLight?'Mode clair':'Mode sombre')
  );
  return h('div',{className:'login-page'},
    themeBtn,
    h('div',{className:'login-box'},
      h('div',{className:'login-logo'},
        h('div',{className:'brand'},'My',h('span',null,'Sifa')),
        h('div',{className:'tagline'},'Portail interne — Production, stocks et outils métier')
      ),
      h('div',{className:'login-card'},
        h('h2',null,'Connexion'),
        h('p',null,'Accès réservé au personnel SIFA'),
        errEl,
        h('form',{onSubmit:submit},
          h('div',{className:'field'},h('label',{'for':'login-email'},'Identifiant ou email'),emailI),
          h('div',{className:'field'},h('label',{'for':'login-password'},'Mot de passe'),pwdWrap),
          h('button',{type:'submit',className:'login-btn',disabled:!!S.loginSubmitting},S.loginSubmitting?'Connexion…':'Se connecter')
        )
      ),
      h('div',{className:'login-footer'},'© SIFA — MySifa __V_LABEL__')
    )
  );
}

// ── Sidebar ─────────────────────────────────────────────────────
function renderSidebar(){
  const admin=isAdmin(S.user);
  const isSuper=isSuperAdmin(S.user);
  const comptaPlan=isComptaPlanning(S.user);
  const items=comptaPlan
    ? (canPlanningNav(S.user)?[{key:'_planning',label:'Planning',icon:'calendar'}]:[])
    : [
    ...(canPlanningNav(S.user)?[{key:'_planning',label:'Planning',icon:'calendar'}]:[]),
    {key:'production',label:'Production',icon:'wrench'},
    {key:'traceabilite',label:'Traçabilité',icon:'layers'},
    ...(admin?[{key:'rentabilite',label:'Rentabilité',icon:'trending-up'}]:[]),
    ...(canAccessOfTab()?[{key:'of',label:'Fiches + OF',icon:'file',withPendingOfBadge:true}]:[]),
  ];
  const isLight=document.body.classList.contains('light');
  return h('nav',{className:'sidebar'},
    h('div',{className:'logo'},h('div',{className:'logo-brand'},'My',h('span',null,'Prod')),h('div',{className:'logo-sub'},'by SIFA')),
    ...items.map(i=>{
      const btn=h('button',{className:'nav-btn'+(S.page===i.key?' active':''),onClick:()=>{
        if(i.key==='_planning'){window.location.href='/planning';return;}
        S.sidebarOpen=false;
        set({page:i.key});nav();
      }});
      btn.appendChild(iconEl(i.icon,15));
      btn.appendChild(document.createTextNode('  '+i.label));
      if(i.withPendingOfBadge){
        const cnt=Number(S.pendingOfCount||0);
        if(cnt>0){
          btn.appendChild(h('span',{
            style:'margin-left:auto;padding:1px 7px;border-radius:9px;background:var(--danger);color:#fff;font-size:10px;font-weight:700;line-height:1.5;flex-shrink:0',
            title:cnt+' OF à associer manuellement',
          }, String(cnt)));
        }
      }
      return btn;
    }),
    h('div',{className:'sidebar-bottom'},
      h('button',{className:'nav-btn back-mysifa',onClick:()=>{window.location.href='/' }},
        '← Retour ',
        h('span',{className:'wm'},'My',h('span',null,'Sifa'))
      ),
      sidebarUserChip(S.user),
      (() => {
        const b=h('button',{
          className:'support-btn',
          title:'Contacter le support',
          onClick:()=>set({contactOpen:true})
        });
        const ico=h('span',{className:'support-ico'});
        try{
          ico.innerHTML=(window.MySifaSupport && typeof window.MySifaSupport.iconSvg==='function')?window.MySifaSupport.iconSvg():'';
        }catch(e){ ico.innerHTML=''; }
        b.appendChild(ico);
        b.appendChild(h('span',null,'Contacter le support'));
        return b;
      })(),
      h('button',{className:'theme-btn',onClick:()=>{MySifaTheme.toggleMode();render();}},
        h('span',{className:'theme-ico'},iconEl(isLight?'sun':'moon',16)),
        h('span',{className:'theme-label'},isLight?'Mode clair':'Mode sombre')
      ),
      h('button',{className:'logout-btn',onClick:doLogout},iconEl('log-out',14),' Déconnexion'),
      h('div',{className:'version'},'__V_LABEL__')
    )
  );
}

// ── Messagerie interne (support) ─────────────────────────────────
function renderContactModal(){
  const box=h('div',{className:'add-row-modal',onClick:(e)=>{if(e.target===box)set({contactOpen:false});}});
  const form=h('div',{className:'add-row-form',style:{maxWidth:'520px'}});
  const close=h('button',{type:'button',className:'add-row-close',onClick:()=>set({contactOpen:false})},'×');
  form.appendChild(close);
  form.appendChild(h('div',{className:'add-row-header',style:{cursor:'default'}},
    h('h3',null,'Contacter le support')
  ));
  form.appendChild(h('div',null,
    h('label',null,'Objet (facultatif)'),
    h('input',{type:'text',value:S.contactSubject||'',onInput:(e)=>{S.contactSubject=e.target.value;},placeholder:'Ex: Problème sur MyStock…'})
  ));
  form.appendChild(h('div',{style:{marginTop:'10px'}},
    h('label',null,'Message *'),
    h('textarea',{rows:'6',style:{width:'100%',background:'var(--bg)',border:'1px solid var(--border)',borderRadius:'8px',padding:'9px 12px',color:'var(--text)',fontSize:'13px',fontFamily:'inherit',outline:'none',resize:'vertical'},
      onInput:(e)=>{S.contactMessage=e.target.value;},placeholder:'Décris ton besoin, avec contexte.'},S.contactMessage||'')
  ));
  form.appendChild(h('div',{className:'form-actions'},
    h('button',{type:'button',className:'btn-ghost',onClick:()=>set({contactOpen:false})},'Annuler'),
    h('button',{type:'button',className:'btn',disabled:!!S.contactSending,onClick:sendContact},S.contactSending?'Envoi…':'Envoyer')
  ));
  box.appendChild(form);
  return box;
}

function renderMessages(){
  if(!isSuperAdmin(S.user)){
    return h('div',{className:'card-blocked'},
      h('div',{className:'cb-icon'},'🔒'),
      h('div',{className:'cb-msg'},'Accès réservé au super administrateur.')
    );
  }
  const list=S.msgList||[];
  const sel=list.find(x=>x.id===S.msgSelId)||null;
  const left=h('div',{style:{width:'360px',maxWidth:'40vw',borderRight:'1px solid var(--border)',paddingRight:'12px'}},
    h('div',{className:'card-header',style:{padding:'0 0 12px',borderBottom:'none'}},
      h('div',{className:'card-title'},'📨 Messages'),
      h('div',null,
        h('button',{className:'btn-sec',type:'button',onClick:markAllRead,style:{padding:'8px 10px',fontSize:'12px'}},'Tout lire')
      )
    ),
    S.msgLoading?h('div',{className:'card-empty'},'Chargement…'):
    (list.length? h('div',{style:{display:'flex',flexDirection:'column',gap:'6px',maxHeight:'520px',overflow:'auto'}},
      ...list.map(m=>{
        const unread=!m.read_at;
        const row=h('button',{type:'button',className:'nav-btn'+(S.msgSelId===m.id?' active':''),onClick:async()=>{
          set({msgSelId:m.id});
          if(unread) await markMessageRead(m.id);
        }});
        row.appendChild(iconEl('mail',15));
        const who=(m.from_name||m.from_email||'Utilisateur').trim();
        const subj=(m.subject||'Sans objet').trim();
        row.appendChild(h('div',{style:{display:'flex',flexDirection:'column',gap:'2px',minWidth:'0'}},
          h('div',{style:{fontSize:'12px',fontWeight:'700',color:unread?'var(--text)':'var(--text2)',whiteSpace:'nowrap',overflow:'hidden',textOverflow:'ellipsis'}},who+' — '+subj),
          h('div',{style:{fontSize:'11px',color:'var(--muted)'}},fD(m.created_at))
        ));
        if(unread) row.appendChild(h('span',{className:'nav-badge'},'NEW'));
        return row;
      })
    ) : h('div',{className:'card-empty'},'Aucun message'))
  );
  const right=h('div',{style:{flex:'1',paddingLeft:'12px'}},
    !sel? h('div',{className:'card-empty'},'Sélectionne un message à gauche.'):
    h('div',{className:'card'},
      h('div',{className:'card-header'},
        h('div',null,
          h('h3',null,(sel.subject||'Sans objet')),
          h('div',{style:{fontSize:'12px',color:'var(--muted)',marginTop:'4px'}},
            (sel.from_name||sel.from_email||'Utilisateur')+' · '+fD(sel.created_at)
          )
        ),
        h('div',{style:{display:'flex',gap:'8px'}},
          h('button',{className:'btn-sec',type:'button',onClick:()=>deleteMessage(sel.id)},'Supprimer')
        )
      ),
      h('div',{style:{padding:'16px 20px',whiteSpace:'pre-wrap',color:'var(--text)'}},sel.body||'')
    )
  );
  return h('div',{style:{display:'flex',gap:'12px'}},left,right);
}

function renderMessagesApp(){
  // App dédiée (portail MySifa) — super admin uniquement
  if(!isSuperAdmin(S.user)){
    return h('div',{className:'portal-page'},
      h('div',{className:'card-blocked'},
        h('div',{className:'cb-icon'},'🔒'),
        h('div',{className:'cb-msg'},'Accès réservé au super administrateur.')
      )
    );
  }
  const isLight=document.body.classList.contains('light');
  const sidebar=h('nav',{className:'sidebar'},
    h('div',{className:'logo'},h('div',{className:'logo-brand'},'My',h('span',null,'Sifa')),h('div',{className:'logo-sub'},'by SIFA')),
      h('button',{className:'nav-btn back-mysifa',onClick:()=>{set({app:'portal',sidebarOpen:false});}},
      '← Retour ',h('span',{className:'wm'},'My',h('span',null,'Sifa'))
    ),
    h('div',{className:'sidebar-bottom'},
      sidebarUserChip(S.user),
      h('button',{className:'theme-btn',onClick:()=>{MySifaTheme.toggleMode();render();}},
        h('span',{className:'theme-ico'},iconEl(isLight?'sun':'moon',16)),
        h('span',{className:'theme-label'},isLight?'Mode clair':'Mode sombre')
      ),
      h('button',{className:'logout-btn',onClick:doLogout},iconEl('log-out',14),' Déconnexion'),
      h('div',{className:'version'},'Messagerie · __V_LABEL__')
    )
  );
  const topbar=h('div',{className:'mobile-topbar'},
    h('button',{type:'button',className:'mobile-menu-btn',onClick:toggleSidebar,'aria-label':'Menu'},iconEl('menu',20)),
    h('div',null,
      h('div',{className:'mobile-topbar-title'},'Messagerie'),
      h('div',{className:'mobile-topbar-sub'},'Support interne — messages reçus')
    ),
    h('button',{type:'button',className:'mobile-home-btn',onClick:()=>{set({app:'portal',sidebarOpen:false});},'aria-label':'Accueil'},iconEl('home',20))
  );

  const filterRow=h('div',{className:'card',style:{padding:'10px 14px',marginBottom:'12px'}},
    h('div',{className:'msg-filter-wrap',style:{display:'flex',gap:'10px',alignItems:'center',flexWrap:'wrap',justifyContent:'space-between'}},
      h('div',{style:{display:'flex',gap:'6px',alignItems:'center',flexWrap:'wrap'}},
        h('span',{className:'badge'},'Filtre'),
        h('button',{type:'button',className:'btn-sec'+(S.msgFilter==='unread'?' is-active':''),onClick:()=>set({msgFilter:'unread',msgSelIds:[],msgMobileView:'list'})},'Non traités'),
        h('button',{type:'button',className:'btn-sec'+(S.msgFilter==='read'?' is-active':''),onClick:()=>set({msgFilter:'read',msgSelIds:[],msgMobileView:'list'})},'Traités'),
        h('button',{type:'button',className:'btn-sec'+(S.msgFilter==='all'?' is-active':''),onClick:()=>set({msgFilter:'all',msgSelIds:[],msgMobileView:'list'})},'Tous')
      ),
      h('div',{className:'msg-filter-actions',style:{display:'flex',gap:'8px',flexShrink:0}},
        h('button',{type:'button',className:'btn-sec',onClick:async()=>{await loadMessagesUnread();await loadMessages();}},'Rafraîchir'),
        h('button',{type:'button',className:'btn-sec',onClick:markAllRead},'Tout lire')
      )
    )
  );

  const listAll=(S.msgList||[]);
  const filt=(S.msgFilter||'unread');
  const list=listAll.filter(m=>{
    if(filt==='all')return true;
    if(filt==='read')return !!m.read_at;
    return !m.read_at;
  });
  const sel=listAll.find(x=>x.id===S.msgSelId)||null;

  const visIds=list.map(m=>m.id);
  const selIdx= S.msgSelId ? visIds.indexOf(S.msgSelId) : -1;
  const selPos=(selIdx>=0)? (selIdx+1)+'/'+visIds.length : '—/'+visIds.length;

  const selSet=new Set((S.msgSelIds||[]).filter(id=>visIds.includes(id)));
  const selectedIds=[...selSet];
  const allVisibleSelected = visIds.length>0 && selectedIds.length===visIds.length;

  function toggleSelect(id){
    const a=[...selSet];
    const i=a.indexOf(id);
    if(i>=0)a.splice(i,1); else a.push(id);
    set({msgSelIds:a});
  }
  function toggleSelectAllVisible(){
    if(allVisibleSelected){ set({msgSelIds:[]}); return; }
    set({msgSelIds:[...visIds]});
  }
  async function bulkSetTreated(toTreated){
    if(!selectedIds.length) return;
    // Traité => read_at non-null ; Non traité => read_at null
    for(const id of selectedIds){
      const m=listAll.find(x=>x.id===id);
      if(!m) continue;
      const isRead=!!m.read_at;
      if(toTreated && !isRead){
        await api('/api/messages/'+id+'/toggle-treated',{method:'POST'});
      }else if(!toTreated && isRead){
        await api('/api/messages/'+id+'/toggle-treated',{method:'POST'});
      }
    }
    set({msgSelIds:[]});
    await loadMessagesUnread();
    await loadMessages();
  }
  async function bulkDelete(){
    if(!selectedIds.length) return;
    if(!confirm('Supprimer '+selectedIds.length+' message(s) ?')) return;
    for(const id of selectedIds){
      await deleteMessage(id);
    }
    set({msgSelIds:[]});
    await loadMessagesUnread();
    await loadMessages();
  }
  function goPrev(){
    if(!visIds.length) return;
    const i = (selIdx>=0?selIdx:0);
    const ni = (i-1+visIds.length)%visIds.length;
    set({msgSelId:visIds[ni]});
  }
  function goNext(){
    if(!visIds.length) return;
    const i = (selIdx>=0?selIdx:-1);
    const ni = (i+1)%visIds.length;
    set({msgSelId:visIds[ni]});
  }

  // Raccourcis clavier (Ctrl+←/→ peut être capturé par le navigateur selon OS)
  // - Alt+← / Alt+→
  // - PageUp / PageDown
  if(!S._msgKeyHandler){
    S._msgKeyHandler = (e)=>{
      try{
        if(!e) return;
        if(S.app!=='messages') return;
        const t = e.target;
        if(t && t.closest && t.closest('input,textarea,select,[contenteditable=true]')) return;

        const isPrev = (e.altKey && e.key==='ArrowLeft') || (e.key==='PageUp') || (e.ctrlKey && e.key==='ArrowLeft');
        const isNext = (e.altKey && e.key==='ArrowRight') || (e.key==='PageDown') || (e.ctrlKey && e.key==='ArrowRight');
        if(!isPrev && !isNext) return;

        const all = (S.msgList||[]);
        const f = (S.msgFilter||'unread');
        const visible = all.filter(m=>{
          if(f==='all') return true;
          if(f==='read') return !!m.read_at;
          return !m.read_at;
        });
        const ids = visible.map(m=>m.id);
        if(!ids.length) return;
        const idx = S.msgSelId ? ids.indexOf(S.msgSelId) : -1;
        const i = (idx>=0?idx:(isPrev?0:-1));
        const ni = isNext ? ((i+1)%ids.length) : ((i-1+ids.length)%ids.length);
        e.preventDefault();
        e.stopPropagation();
        set({msgSelId:ids[ni]});
      }catch(err){}
    };
    document.addEventListener('keydown', S._msgKeyHandler, true);
  }

  const isMobile = window.innerWidth <= 900;
  const mobileView = S.msgMobileView || 'list';

  const left=h('div',{className:'msg-left'},
    h('div',{className:'card'},
      h('div',{className:'card-header',style:{gap:'8px',flexWrap:'nowrap'}},
        h('div',{className:'card-title',style:{flexShrink:0}},'📨 Messages'),
        h('div',{style:{display:'flex',gap:'6px',alignItems:'center',marginLeft:'auto',flexShrink:0}},
          h('button',{type:'button',className:'add-row-nav-btn',title:'Précédent (Alt+← / PageUp)',onClick:(e)=>{e.stopPropagation();goPrev();}},'‹'),
          h('div',{style:{fontSize:'12px',fontWeight:'700',color:'var(--text2)',minWidth:'44px',textAlign:'center'}},selPos),
          h('button',{type:'button',className:'add-row-nav-btn',title:'Suivant (Alt+→ / PageDown)',onClick:(e)=>{e.stopPropagation();goNext();}},'›')
        )
      ),
      h('div',{style:{display:'flex',gap:'6px',alignItems:'center',padding:'0 12px 10px 12px',flexWrap:'wrap'}},
        h('button',{type:'button',className:'btn-sec',style:{fontSize:'11px',padding:'5px 8px'},onClick:toggleSelectAllVisible,disabled:!visIds.length},
          allVisibleSelected?'Tout -':'Tout +'
        ),
        h('button',{type:'button',className:'btn-sec',style:{fontSize:'11px',padding:'5px 8px'},onClick:()=>bulkSetTreated(true),disabled:!selectedIds.length},'Traité'),
        h('button',{type:'button',className:'btn-sec',style:{fontSize:'11px',padding:'5px 8px'},onClick:()=>bulkSetTreated(false),disabled:!selectedIds.length},'Non traité'),
        h('button',{type:'button',className:'btn-danger',style:{fontSize:'11px'},onClick:bulkDelete,disabled:!selectedIds.length},'Supprimer')
      ),
      S.msgLoading?h('div',{className:'card-empty'},'Chargement…'):
      (list.length? h('div',{className:'msg-list-scroll'},
        ...list.map(m=>{
          const unread=!m.read_at;
          const wrap=h('div',{style:{display:'flex',gap:'8px',alignItems:'center'}});
          const selBtn=h('button',{type:'button',className:'msg-sel-btn'+(selSet.has(m.id)?' on':''),title:selSet.has(m.id)?'Désélectionner':'Sélectionner',onClick:(e)=>{e.stopPropagation();toggleSelect(m.id);}}, selSet.has(m.id)?'✓':'');
          const row=h('button',{type:'button',className:'nav-btn'+(S.msgSelId===m.id?' active':''),onClick:async()=>{
            set({msgSelId:m.id,...(isMobile?{msgMobileView:'detail'}:{})});
          }});
          row.appendChild(iconEl('mail',15));
          const who=(m.from_name||m.from_email||'Utilisateur').trim();
          const subj=(m.subject||'Sans objet').trim();
          row.appendChild(h('div',{style:{display:'flex',flexDirection:'column',gap:'2px',minWidth:'0'}},
            h('div',{style:{fontSize:'12px',fontWeight:'700',color:unread?'var(--text)':'var(--text2)',whiteSpace:'nowrap',overflow:'hidden',textOverflow:'ellipsis'}},who+' — '+subj),
            h('div',{style:{fontSize:'11px',color:'var(--muted)'}},fD(m.created_at))
          ));
          if(unread) row.appendChild(h('span',{className:'nav-badge'},'NEW'));
          wrap.appendChild(selBtn);
          wrap.appendChild(row);
          return wrap;
        })
      ) : h('div',{className:'card-empty'},'Aucun message'))
    )
  );
  const right=h('div',{className:'msg-right'},
    !sel? h('div',{className:'card-empty',style:{marginTop:'8px'}},
      isMobile?h('button',{className:'btn-sec',style:{marginBottom:'12px'},type:'button',onClick:()=>set({msgMobileView:'list'})},iconEl('arrow-left',13),' Retour'):null,
      h('div',null,'Sélectionne un message.')
    ):
    h('div',{className:'card'},
      h('div',{className:'card-header',style:{flexWrap:'wrap',gap:'8px'}},
        h('div',{style:{minWidth:0,flex:'1'}},
          h('h3',{style:{wordBreak:'break-word'}},(sel.subject||'Sans objet')),
          h('div',{style:{fontSize:'12px',color:'var(--muted)',marginTop:'4px'}},
            (sel.from_name||sel.from_email||'Utilisateur')+' · '+fD(sel.created_at)
          )
        ),
        h('div',{style:{display:'flex',gap:'6px',flexWrap:'wrap',justifyContent:'flex-end',alignItems:'center',flexShrink:0}},
          isMobile?h('button',{className:'btn-sec',type:'button',style:{fontSize:'11px',padding:'5px 8px'},onClick:()=>set({msgMobileView:'list'})},iconEl('arrow-left',11),' Liste'):null,
          h('div',{style:{display:'flex',gap:'6px',alignItems:'center'}},
            h('button',{type:'button',className:'add-row-nav-btn',title:'Précédent (Alt+← / PageUp)',onClick:(e)=>{e.stopPropagation();goPrev();}},'‹'),
            h('div',{style:{fontSize:'12px',fontWeight:'700',color:'var(--text2)',minWidth:'44px',textAlign:'center'}},selPos),
            h('button',{type:'button',className:'add-row-nav-btn',title:'Suivant (Alt+→ / PageDown)',onClick:(e)=>{e.stopPropagation();goNext();}},'›')
          ),
          h('button',{className:'btn-sec',type:'button',style:{fontSize:'11px',padding:'5px 10px'},onClick:async()=>{
            await api('/api/messages/'+sel.id+'/toggle-treated',{method:'POST'});
            await loadMessagesUnread();
            await loadMessages();
          }}, sel.read_at?'Non traité':'Traité'),
          h('button',{className:'btn-danger',type:'button',style:{fontSize:'11px'},onClick:()=>deleteMessage(sel.id)},'Supprimer')
        )
      ),
      h('div',{style:{padding:'14px 16px',whiteSpace:'pre-wrap',color:'var(--text)',lineHeight:'1.55',wordBreak:'break-word',overflowWrap:'break-word'}},sel.body||'')
    )
  );

  // Layout responsive: sur mobile, vue unique liste ou détail
  const content=h('div',{className:'container'},
    topbar,
    !isMobile?h('div',{style:{marginBottom:'14px'}},
      h('h1',{style:{marginBottom:'2px'}},'Messagerie'),
      h('div',{className:'subtitle'},'Support interne — messages reçus')
    ):null,
    filterRow,
    h('div',{className:'msg-grid'},
      (!isMobile || mobileView==='list') ? left : null,
      (!isMobile || mobileView==='detail') ? right : null
    )
  );
  return h('div',null,
    S.sidebarOpen?h('div',{className:'sidebar-overlay',onClick:closeSidebar}):null,
    h('div',{className:'app'},sidebar,h('main',{className:'main'},content))
  );
}

// ── Filters ─────────────────────────────────────────────────────
function makeDateSelect(value, onChange){
  const parts=(value||'').split('-');
  const yyyy=parts[0]||'', mm=parts[1]||'', dd=parts[2]||'';

  const jSel=h('select',{style:{background:'var(--bg)',border:'1px solid var(--border)',borderRadius:'6px',padding:'7px 6px',color:'var(--text)',fontSize:'12px',fontFamily:'inherit'}});
  const mSel=h('select',{style:{background:'var(--bg)',border:'1px solid var(--border)',borderRadius:'6px',padding:'7px 6px',color:'var(--text)',fontSize:'12px',fontFamily:'inherit'}});
  const aSel=h('select',{style:{background:'var(--bg)',border:'1px solid var(--border)',borderRadius:'6px',padding:'7px 6px',color:'var(--text)',fontSize:'12px',fontFamily:'inherit'}});

  jSel.appendChild(h('option',{value:''},'JJ'));
  for(let i=1;i<=31;i++){
    const v=String(i).padStart(2,'0');
    const opt=h('option',{value:v},v);
    if(v===dd)opt.selected=true;
    jSel.appendChild(opt);
  }

  const mois=['Jan','Fév','Mar','Avr','Mai','Jun','Jul','Aoû','Sep','Oct','Nov','Déc'];
  mSel.appendChild(h('option',{value:''},'MM'));
  mois.forEach((m,i)=>{
    const v=String(i+1).padStart(2,'0');
    const opt=h('option',{value:v},m);
    if(v===mm)opt.selected=true;
    mSel.appendChild(opt);
  });

  const y=new Date().getFullYear();
  aSel.appendChild(h('option',{value:''},'AAAA'));
  for(let i=y-1;i<=y+1;i++){
    const opt=h('option',{value:String(i)},String(i));
    if(String(i)===yyyy)opt.selected=true;
    aSel.appendChild(opt);
  }

  const update=()=>{
    const v=(aSel.value&&mSel.value&&jSel.value)
      ? aSel.value+'-'+mSel.value+'-'+jSel.value : '';
    onChange(v);
  };
  jSel.addEventListener('change',update);
  mSel.addEventListener('change',update);
  aSel.addEventListener('change',update);

  return h('div',{style:{display:'flex',gap:'4px',alignItems:'center'}},jSel,mSel,aSel);
}

function makeDateInput(value, onChange, ariaLabel){
  const inp = h('input',{
    type:'date',
    className:'filter-input',
    value: value || '',
    ...(ariaLabel ? {'aria-label': ariaLabel, title: ariaLabel} : {}),
  });
  inp.addEventListener('change',()=>onChange(inp.value||''));
  // Ouvrir le calendrier au clic (Chrome/Safari supportent showPicker).
  const openPicker = ()=>{
    try{
      if(typeof inp.showPicker === 'function') inp.showPicker();
      else inp.focus();
    }catch(e){ try{inp.focus();}catch(_){} }
  };
  inp.addEventListener('click',openPicker);
  // Sur certains navigateurs, click ouvre déjà; mousedown améliore la réactivité.
  inp.addEventListener('mousedown',()=>{ /* user gesture */ });
  return inp;
}

function renderFilters(){
  const viewAll=canViewAllProd(S.user);
  const ops=S.filters.operators||[];
  const dos=S.filters.dossiers||[];
  const MACHINE_FILTER_ORDER=['Cohésio 1','Cohésio 2','DSI','Repiquage'];
  const machList=(S.filters.machines&&S.filters.machines.length)?S.filters.machines:MACHINE_FILTER_ORDER;
  const machs=machList.map(m=>({value:m,label:m}));
  const parts=[];
 
  if(viewAll){
    // ── Multi-select opérateurs ──────────────────────────────────
    parts.push(makeMultiSelect(
      'Opérateurs',
      ops.map(o=>({value:o,label:opName(o)})),
      ()=>S.fv.operateurs,
      (sel)=>{ S.fv.operateurs=sel; }
    ));

    parts.push(makeDossierFilterSearch(dos));
  }

  if(machs.length){
    parts.push(makeMultiSelect(
      'Machines',
      machs,
      ()=>S.fv.machines,
      (sel)=>{ S.fv.machines=sel; }
    ));
  }
 
  const df=makeDateInput(S.fv.date_from, v=>{S.fv.date_from=v;}, 'Du');
  const dt=makeDateInput(S.fv.date_to,   v=>{S.fv.date_to=v;}, 'Au');
  parts.push(h('div',{className:'filter-group'},h('label',null,'Du'),df));
  parts.push(h('div',{className:'filter-group'},h('label',null,'Au'),dt));
  parts.push(h('button',{className:'filters-apply-btn',onClick:applyF},'Filtrer'));

  const row = h('div',{className:'filters'},...parts);
  const chipsRow = viewAll ? renderDossierFilterChipsRow() : null;
  return h('div',{className:'filters-panel'},row,chipsRow||null);
}

function renderDossierFilterChipsRow(){
  const sel = S.fv.dossiers || [];
  if(!sel.length) return null;
  const chips = h('div',{className:'prod-dossier-chips',id:'prod-filter-dossier-chips'});
  sel.forEach(ref=>{
    const rm = h('button',{type:'button',className:'prod-dossier-chip-remove',title:'Retirer','aria-label':'Retirer '+ref,
      onClick:()=>removeDossierFilter(ref)},'×');
    chips.appendChild(h('span',{className:'prod-dossier-chip'},ref,rm));
  });
  return h('div',{className:'filters-chips-row',id:'prod-filter-dossier-chips-row'},chips);
}
 
// ── Composant multi-select avec cases à cocher ──────────────────
function makeMultiSelect(label, options, selected, onChange){
  // NOTE: `selected` peut être un getter () => array ou un array direct.
  // On utilise toujours le getter pour lire la valeur courante après chaque onChange,
  // sinon la closure capturait l'ancienne référence de tableau.
  const getSelected = typeof selected === 'function'
    ? ()=>{ const v=selected(); return Array.isArray(v)?v:[]; }
    : ()=> Array.isArray(selected) ? selected : [];
  const isSelected = v => getSelected().includes(v);
  const count = getSelected().length;
 
  const triggerLabel = h('span',null, count>0 ? label+' ('+count+')' : label);
  const trigger = h('button',{
    type:'button',
    className:'filter-input multisel-trigger',
  },
    triggerLabel,
    h('span',{className:'multisel-trigger-caret'},'▾')
  );
 
  // Dropdown
  const dropdown = h('div',{
    className:'multisel-dropdown',
    style:{
      position:'absolute',top:'100%',left:'0',zIndex:'50',
      background:'var(--card)',border:'1px solid var(--border)',borderRadius:'10px',
      padding:'8px 0',minWidth:'200px',maxHeight:'220px',overflowY:'auto',
      boxShadow:'0 8px 24px rgba(0,0,0,.3)',display:'none'
    }
  });
 
  // Option "Tout sélectionner / Désélectionner"
  const allChk = h('label',{style:{display:'flex',alignItems:'center',gap:'8px',padding:'6px 14px',cursor:'pointer',fontSize:'12px',color:'var(--muted)',fontWeight:'600'}},
    h('input',{type:'checkbox'}),
    'Tout sélectionner'
  );
  allChk.querySelector('input').checked = count === options.length;
  allChk.querySelector('input').addEventListener('change',e=>{
    const newSel = e.target.checked ? options.map(o=>o.value) : [];
    onChange(newSel);
    // Mettre à jour les checkboxes enfants
    dropdown.querySelectorAll('input[type=checkbox]').forEach((cb,i)=>{if(i>0)cb.checked=e.target.checked;});
    triggerLabel.textContent = newSel.length>0?label+' ('+newSel.length+')':label;
  });
  dropdown.appendChild(allChk);
 
  options.forEach(opt=>{
    const lbl = h('label',{style:{display:'flex',alignItems:'center',gap:'8px',padding:'6px 14px',cursor:'pointer',fontSize:'12px',color:'var(--text2)'}},
      h('input',{type:'checkbox'}),
      h('span',null,opt.label)
    );
    const chk = lbl.querySelector('input');
    chk.checked = isSelected(opt.value);
    chk.addEventListener('change',()=>{
      const curSel = getSelected();
      let newSel = curSel.filter(v=>v!==opt.value);
      if(chk.checked) newSel.push(opt.value);
      onChange(newSel);
      triggerLabel.textContent = newSel.length>0?label+' ('+newSel.length+')':label;
      allChk.querySelector('input').checked = newSel.length===options.length;
    });
    dropdown.appendChild(lbl);
  });
 
  // Toggle dropdown au clic
  let open=false;
  trigger.addEventListener('click',e=>{
    e.stopPropagation();
    open=!open;
    dropdown.style.display=open?'block':'none';
  });
  // Fermer uniquement si le clic est en dehors du composant (trigger + dropdown).
  // Important: on garde `capture:true` car l'app a d'autres listeners globaux,
  // donc on doit filtrer correctement plutôt que compter sur stopPropagation().
  const onDocClick = (e)=>{
    try{
      if(!open) return;
      if(rel && rel.contains && rel.contains(e.target)) return;
      open=false;
      dropdown.style.display='none';
    }catch(_){}
  };
  document.addEventListener('click', onDocClick, {once:false,capture:true,passive:true});
 
  const wrapper=h('div',{className:'filter-group'},h('label',null,label));
  const rel=h('div',{style:{position:'relative'}},trigger,dropdown);
  wrapper.appendChild(rel);
  return wrapper;
}

function syncDossierFilterSuggest(){
  const dd = document.getElementById('prod-filter-dossier-suggest');
  const inp = document.getElementById('prod-filter-dossier-search');
  if(!dd || !inp) return;
  const all = (S.filters && S.filters.dossiers) ? S.filters.dossiers : [];
  const q = (inp.value || '').trim().toLowerCase();
  const selected = new Set((S.fv.dossiers || []).map(d=>String(d)));
  let matches = all;
  if(q) matches = all.filter(d=>String(d).toLowerCase().includes(q));
  matches = matches.filter(d=>!selected.has(String(d))).slice(0, 24);
  dd.innerHTML = '';
  if(!q){
    dd.classList.remove('open');
    return;
  }
  if(!matches.length){
    const empty = document.createElement('div');
    empty.className = 'prod-dossier-suggest-empty';
    empty.textContent = 'Aucun résultat pour « ' + (inp.value || '').trim() + ' »';
    dd.appendChild(empty);
    dd.classList.add('open');
    return;
  }
  const hi = Number(S.dossierFilterHi);
  matches.forEach((ref, i)=>{
    const row = document.createElement('div');
    row.className = 'prod-dossier-suggest-item' + (i === hi ? ' prod-dossier-suggest-item--hi' : '');
    row.textContent = ref;
    row.addEventListener('mousedown', e=>{
      e.preventDefault();
      pickDossierFilter(ref);
    });
    dd.appendChild(row);
  });
  dd.classList.add('open');
}

function pickDossierFilter(ref){
  const v = String(ref || '').trim();
  if(!v) return;
  const cur = (S.fv.dossiers || []).slice();
  if(!cur.includes(v)) cur.push(v);
  S.fv.dossiers = cur;
  S.fv.dossierSearchQ = '';
  S.dossierFilterHi = -1;
  applyF();
}

function removeDossierFilter(ref){
  S.fv.dossiers = (S.fv.dossiers || []).filter(d=>d !== ref);
  applyF();
}

function makeDossierFilterSearch(allDossiers){
  const wrap = h('div', { className: 'filter-group filter-group--dossier', id: 'prod-filter-dossier-wrap' });
  wrap.appendChild(h('label', null, 'Dossier'));

  const rel = h('div', { className: 'prod-dossier-filter' });

  const inp = h('input', {
    type: 'text',
    id: 'prod-filter-dossier-search',
    className: 'search-bar',
    placeholder: 'Rechercher (n° dossier…)',
    autocomplete: 'off',
    value: S.fv.dossierSearchQ || '',
  });
  const dd = h('div', { id: 'prod-filter-dossier-suggest', className: 'prod-dossier-suggest' });

  inp.addEventListener('input', ()=>{
    S.fv.dossierSearchQ = inp.value;
    S.dossierFilterHi = -1;
    syncDossierFilterSuggest();
  });
  inp.addEventListener('focus', ()=>{
    if((inp.value || '').trim()) syncDossierFilterSuggest();
  });
  inp.addEventListener('keydown', e=>{
    const ddEl = document.getElementById('prod-filter-dossier-suggest');
    const items = ddEl ? [...ddEl.querySelectorAll('.prod-dossier-suggest-item')] : [];
    if(e.key === 'Escape'){
      e.preventDefault();
      inp.value = '';
      S.fv.dossierSearchQ = '';
      S.dossierFilterHi = -1;
      if(ddEl){ ddEl.classList.remove('open'); ddEl.innerHTML = ''; }
      return;
    }
    if(!items.length) return;
    if(e.key === 'ArrowDown'){
      e.preventDefault();
      S.dossierFilterHi = Math.min(items.length - 1, (S.dossierFilterHi < 0 ? 0 : S.dossierFilterHi + 1));
      syncDossierFilterSuggest();
    } else if(e.key === 'ArrowUp'){
      e.preventDefault();
      S.dossierFilterHi = Math.max(0, (S.dossierFilterHi < 0 ? 0 : S.dossierFilterHi - 1));
      syncDossierFilterSuggest();
    } else if(e.key === 'Enter'){
      e.preventDefault();
      const i = S.dossierFilterHi >= 0 ? S.dossierFilterHi : 0;
      const ref = items[i] ? items[i].textContent : '';
      if(ref) pickDossierFilter(ref);
    }
  });

  rel.appendChild(inp);
  rel.appendChild(dd);
  wrap.appendChild(rel);

  if(!window._mysifaDossierFilterDocClick){
    window._mysifaDossierFilterDocClick = true;
    document.addEventListener('click', e=>{
      const w = document.getElementById('prod-filter-dossier-wrap');
      if(w && !w.contains(e.target)){
        const dds = document.getElementById('prod-filter-dossier-suggest');
        if(dds) dds.classList.remove('open');
      }
    }, { capture: true, passive: true });
  }

  requestAnimationFrame(()=>{
    if((S.fv.dossierSearchQ || '').trim()) syncDossierFilterSuggest();
  });

  return wrap;
}

// ── Sanity ──────────────────────────────────────────────────────
function renderSanity(sanity, title){
  if(!sanity)return null;
  const score=sanity.score||0;
  const colorMap={success:'var(--success)',warn:'var(--warn)',danger:'var(--danger)'};
  const col=colorMap[sanity.color]||'var(--muted)';
  const r=34,circ=2*Math.PI*r,offset=circ-(score/100)*circ;
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
  svg.setAttribute('width','80');svg.setAttribute('height','80');svg.setAttribute('viewBox','0 0 80 80');svg.style.transform='rotate(-90deg)';
  const bg=document.createElementNS('http://www.w3.org/2000/svg','circle');bg.setAttribute('cx','40');bg.setAttribute('cy','40');bg.setAttribute('r',String(r));bg.setAttribute('fill','none');bg.setAttribute('stroke','var(--border)');bg.setAttribute('stroke-width','8');svg.appendChild(bg);
  const fill=document.createElementNS('http://www.w3.org/2000/svg','circle');fill.setAttribute('cx','40');fill.setAttribute('cy','40');fill.setAttribute('r',String(r));fill.setAttribute('fill','none');fill.setAttribute('stroke',col);fill.setAttribute('stroke-width','8');fill.setAttribute('stroke-linecap','round');fill.setAttribute('stroke-dasharray',String(circ));fill.setAttribute('stroke-dashoffset',String(offset));svg.appendChild(fill);
  return h('div',{className:'sanity-banner'},
    h('div',{className:'sanity-circle'},svg,h('div',{className:'sanity-num',style:{color:col}},String(score))),
    h('div',null,
      h('div',{className:'si-mention',style:{color:col}},(title?title+' — ':'')+(sanity.mention||'')),
      h('div',{className:'si-label'},sanity.weighted?'Qualité de saisie — moyenne pondérée (temps d\'activité)':'Qualité de saisie — Sanity Score')
    )
  );
}

// ── Détails sanity (liste par type) ──────────────────────────────
const SANITY_LABELS={
  jour_first_last:{label:"Arrivée personnel / Départ personnel"},
  jour_second_penult:{label:"Début de dossier / Fin de dossier"},
  jour_need_prod_cal_tech:{label:"Saisie vide"},
  jour_short_shift:{label:"Arrivée → Départ < 5h"},
  jour_arret_50:{label:"Arrêt machine (code 50)"},
  jour_missing_metrage:{label:"Métrage manquant (fin dossier)"},
  jour_missing_etiquettes:{label:"Nombre d’étiquettes manquant (fin dossier)"},
  jour_empty_dossier:{label:"Dossier vide (début → fin sans saisie)"},
};
function renderSanityEventsBlock(sanity){
  const events=sanity&&sanity.events?sanity.events:{};
  const keys=Object.keys(events||{}).filter(k=>(events[k]||[]).length>0);
  if(!keys.length){
    return h('div',{className:'card-empty',style:{display:'flex',alignItems:'center',gap:'8px',justifyContent:'center'}},iconEl('check-circle',18),'Aucune anomalie détectée');
  }
  const blocks=keys.map(k=>{
    const lbl=(SANITY_LABELS[k]&&SANITY_LABELS[k].label)?SANITY_LABELS[k].label:k;
    const rows=(events[k]||[]).slice(0,120);
    const items=rows.map(e=>{
      const dos=(e.no_dossier||"").trim();
      return h('div',{style:{display:'flex',gap:'10px',flexWrap:'wrap',alignItems:'center',padding:'6px 0',borderBottom:'1px solid var(--border)'}},
        h('span',{style:{fontFamily:'monospace',fontSize:'11px',color:'var(--muted)'}},e.jour||''),
        h('span',{style:{fontWeight:'700'}},opName(e.operateur||'')),
        dos?h('span',{style:{fontFamily:'monospace',color:'var(--text2)'}},'Dos. '+dos):null
      );
    });
    return h('div',{style:{padding:'14px 20px',borderBottom:'1px solid var(--border)'}},
      h('div',{style:{fontSize:'12px',fontWeight:'800',color:'var(--danger)',marginBottom:'8px'}},lbl+' ('+rows.length+')'),
      h('div',null,...items)
    );
  });
  return h('div',null,...blocks);
}

// ── Production (page wrapper avec sous-onglets) ───────────────────
// ── Traçabilité ─────────────────────────────────────────────────
async function loadTracabilite(machineId){
  S.traceabilite = null; S.tracShowAttente = false; render();
  try{
    let url = '/api/fabrication/traceability';
    const params = [];
    if(machineId) params.push('machine_id='+machineId);
    if(params.length) url += '?'+params.join('&');
    const d = await api(url);
    S.traceabilite = d;
  }catch(e){ S.traceabilite = {error:e.message}; }
  render();
}

async function loadTracabiliteDossier(ref){
  S.traceabiliteDossier = null; render();
  try{
    // Charger les deux en parallèle : vue production + vue FSC
    const [d, fsc] = await Promise.all([
      api('/api/fabrication/traceability?no_dossier='+encodeURIComponent(ref)),
      api('/api/fabrication/tracabilite/'+encodeURIComponent(ref)),
    ]);
    const fscMap = {};
    (fsc && fsc.bobines ? fsc.bobines : []).forEach(b => {
      const key = String(b.code_barre||'').trim();
      if(key) fscMap[key] = b;
    });
    (d && d.matieres ? d.matieres : []).forEach(m => {
      const key = String(m.code_barre||'').trim();
      const b = fscMap[key];
      if(!b) return;
      if(b.fsc_conforme !== undefined) m.fsc_conforme = b.fsc_conforme;
      if(b.fsc_type_claim != null) m.fsc_type_claim = b.fsc_type_claim;
      if(b.fournisseur != null) m.fournisseur = b.fournisseur;
      if(b.certificat_fsc != null) m.certificat_fsc = b.certificat_fsc;
      if(b.fournisseur_licence != null) m.fournisseur_licence = b.fournisseur_licence;
      if(b.fournisseur_certificat != null) m.fournisseur_certificat = b.fournisseur_certificat;
    });
    d.fsc_synthese = (fsc && fsc.synthese) ? fsc.synthese : null;
    S.traceabiliteDossier = d;
  }catch(e){ S.traceabiliteDossier = {error:e.message}; }
  render();
}

function openFscRapportModal(data, ref){
  try{
    const syn = (data && data.synthese) ? data.synthese : {};
    const bobines = (data && data.bobines) ? data.bobines : [];
    const dos = (data && data.dossier) ? data.dossier : {};

    const sg = syn.statut_global || 'non_applicable';
    const statutColor = sg === 'conforme' ? 'var(--success)'
      : sg === 'non_conforme' ? 'var(--danger)' : 'var(--muted)';
    const statutBg = sg === 'conforme' ? 'rgba(52,211,153,.12)'
      : sg === 'non_conforme' ? 'rgba(248,113,113,.12)' : 'rgba(148,163,184,.12)';
    let statutText = 'Non applicable';
    if(sg === 'conforme'){
      statutText = 'Conforme FSC — ' + (syn.nb_bobines_fsc_conformes ?? 0) + '/' + (syn.nb_bobines_total ?? 0) + ' bobine(s)';
    }else if(sg === 'non_conforme'){
      statutText = 'Non conforme — ' + (syn.nb_bobines_non_conformes ?? 0) + ' bobine(s) en écart';
    }else if(sg === 'en_attente'){
      statutText = 'En attente — aucune bobine scannée';
    }else if((syn.nb_bobines_total ?? 0) === 0){
      statutText = 'Aucune bobine scannée';
    }

    const typeReq = dos.fsc_type_requis ? String(dos.fsc_type_requis) : '';
    const genAt = syn.genere_a ? String(syn.genere_a).replace('T',' ').slice(0,16) : '';

    const overlay = h('div',{className:'contact-modal-overlay',onClick:(e)=>{ if(e.target===e.currentTarget) overlay.remove(); }},
      h('div',{className:'contact-modal',onClick:(e)=>e.stopPropagation(),style:{maxWidth:'760px'}},
        h('div',{className:'contact-modal-head'},
          h('h3',null,'Rapport traçabilité FSC'),
          h('div',{style:{display:'flex',gap:'8px',flexShrink:0,flexWrap:'wrap'}},
            h('button',{className:'btn btn-sm btn-ghost',style:{fontSize:'12px'},onClick:()=>window.print()},'Exporter PDF'),
            h('button',{className:'btn btn-sm btn-ghost',style:{fontSize:'12px'},onClick:()=>overlay.remove()},'Fermer')
          )
        ),
        h('div',{style:{fontSize:'12px',color:'var(--muted)',marginTop:'-6px',marginBottom:'12px'}},
          (ref||'') + (dos.client ? (' — ' + dos.client) : '') + (typeReq ? (' · Requis : ' + typeReq) : '')
        ),
        h('div',{style:{padding:'10px 14px',borderRadius:'8px',marginBottom:'14px',fontWeight:'800',fontSize:'13px',
          background:statutBg,border:'1px solid '+statutColor,color:statutColor}}, statutText),
        h('div',{className:'table-wrap',style:{border:'1px solid var(--border)',borderRadius:'12px'}},
          h('table',{className:'table-std',style:{fontSize:'13px'}},
            h('thead',null,h('tr',null,
              h('th',null,'Code barre'),
              h('th',null,'Fournisseur'),
              h('th',null,'Claim FSC'),
              h('th',null,'Statut FSC'),
              h('th',null,'Scanné le')
            )),
            h('tbody',null,
              ...(bobines.length ? bobines.map(b=>{
                const claim = b.fsc_type_claim || 'Non FSC';
                const conf = b.fsc_conforme;
                const confCell = conf === true
                  ? h('span',{style:{color:'var(--success)',fontWeight:'800'}},'\u2713')
                  : conf === false
                    ? h('span',{style:{color:'var(--danger)',fontWeight:'800'}},'\u2717'+(b.fsc_warning?' (confirmé)':''))
                    : h('span',{style:{color:'var(--muted)'}},'\u2014');
                const scan = (b.scanned_at||'').slice(0,16).replace('T',' ');
                return h('tr',null,
                  h('td',null,h('span',{style:{fontFamily:'ui-monospace,monospace',fontWeight:'800'}},b.code_barre||'')),
                  h('td',null,b.fournisseur||'—'),
                  h('td',null,claim),
                  h('td',null,confCell),
                  h('td',{style:{fontSize:'11px',color:'var(--muted)'}},scan||'—'),
                );
              }) : [
                h('tr',null,h('td',{colSpan:'5',style:{padding:'20px',textAlign:'center',color:'var(--muted)',fontSize:'12px'}},
                  'Aucune bobine scannée sur ce dossier.'
                ))
              ])
            )
          )
        ),
        h('div',{style:{marginTop:'14px',paddingTop:'10px',borderTop:'1px solid var(--border)',fontSize:'11px',color:'var(--muted)'}},
          'Généré le ', genAt, ' · MySifa · SIFA'
        )
      )
    );
    document.body.appendChild(overlay);
  }catch(e){
    showToast('Rapport FSC indisponible.','danger');
  }
}

function renderTracabilite(){
  // Si on a un dossier sélectionné, afficher son détail
  if(S.traceabiliteDossier !== undefined && S.traceabiliteDossier !== null){
    return renderTracabiliteDossierDetail();
  }

  const d = S.traceabilite;
  if(!d) return h('div',{className:'card-empty'},'Chargement de la traçabilité…');
  if(d.error) return h('div',{className:'card'},h('div',{style:{padding:'20px',color:'var(--danger)'}},d.error));

  const allDossiers = d.dossiers||[];

  // ── Valeurs uniques pour les selects ───────────────────────────
  const machinesUniq = [...new Set(allDossiers.map(x=>x.machine_nom).filter(Boolean))].sort();
  const statuts = [
    {val:'',label:'Tous statuts'},
    {val:'attente',label:'En attente'},
    {val:'en_cours',label:'En cours'},
    {val:'termine',label:'Terminé'},
  ];

  // ── État filtres ────────────────────────────────────────────────
  if(!S.tracFilters) S.tracFilters={ref:'',client:'',machine:'',statut:''};
  if(!S.tracSort)    S.tracSort={col:null,dir:'asc'};
  const F = S.tracFilters;
  const Srt = S.tracSort;

  // ── Filtre ──────────────────────────────────────────────────────
  let dossiers = allDossiers.filter(dos=>{
    if(F.ref    && !(dos.reference||'').toLowerCase().includes(F.ref.toLowerCase()))    return false;
    if(F.client && !(dos.client||'').toLowerCase().includes(F.client.toLowerCase()))    return false;
    if(F.machine && dos.machine_nom !== F.machine) return false;
    if(F.statut  && dos.statut !== F.statut)       return false;
    return true;
  });

  // ── Tri / visibilité en attente ─────────────────────────────────
  const _tracPos = d=>{
    const p = Number(d && d.position);
    if(!isNaN(p)) return p;
    return Number(d && d.id) || 0;
  };
  const attenteDossiers = dossiers.filter(dos=>dos.statut==='attente');
  const mainDossiers = dossiers.filter(dos=>dos.statut!=='attente');
  const forceShowAttente = F.statut==='attente';
  const showAttente = forceShowAttente || !!S.tracShowAttente;
  const hiddenAttenteCount = (!showAttente && !F.statut) ? attenteDossiers.length : 0;

  const COL_KEY = {ref:'reference',client:'client',designation:'designation',machine:'machine_nom',statut:'statut',matieres:'nb_matieres'};
  if(Srt.col){
    const key = COL_KEY[Srt.col]||Srt.col;
    dossiers = [...dossiers].sort((a,b)=>{
      let av=a[key]||'', bv=b[key]||'';
      if(typeof av==='number'||typeof bv==='number'){av=Number(av)||0;bv=Number(bv)||0;}
      else{av=String(av).toLowerCase();bv=String(bv).toLowerCase();}
      return Srt.dir==='asc'?(av>bv?1:av<bv?-1:0):(av<bv?1:av>bv?-1:0);
    });
    if(!showAttente && !F.statut){
      dossiers = dossiers.filter(dos=>dos.statut!=='attente');
    }
  } else {
    const sortDescPos = (a,b)=>_tracPos(b)-_tracPos(a);
    const sortedAttente = [...attenteDossiers].sort(sortDescPos);
    const sortedMain = [...mainDossiers].sort(sortDescPos);
    dossiers = showAttente ? [...sortedAttente, ...sortedMain] : sortedMain;
  }

  // ── Pagination (sur la liste filtrée/triée) ─────────────────────
  const PAGE_SIZE = 50;
  if(S.tracPage == null) S.tracPage = 0;
  const totalFiltered = dossiers.length;
  const maxPage = Math.max(0, Math.ceil(totalFiltered / PAGE_SIZE) - 1);
  if(S.tracPage > maxPage) S.tracPage = maxPage;
  if(S.tracPage < 0) S.tracPage = 0;
  const pageStart = S.tracPage * PAGE_SIZE;
  const pageEnd = Math.min(pageStart + PAGE_SIZE, totalFiltered);
  const dossiersPage = dossiers.slice(pageStart, pageEnd);

  // ── Helper : badge statut ───────────────────────────────────────
  function statutBadge(st){
    if(st==='en_cours')  return h('span',{className:'badge',style:{color:'var(--success)',background:'rgba(52,211,153,.12)',display:'inline-flex',alignItems:'center',gap:'5px'}},
      h('span',{style:{width:'6px',height:'6px',borderRadius:'50%',background:'var(--success)',display:'inline-block',animation:'pulse 2s infinite'}}),
      'En cours');
    if(st==='termine')   return h('span',{className:'badge badge-ok'},'Terminé');
    return h('span',{className:'badge badge-warn'},'En attente');
  }

  // ── Header cliquable (tri) ──────────────────────────────────────
  function thSort(colKey, label){
    const active = Srt.col===colKey;
    const arrow  = active ? (Srt.dir==='asc'?'↑':'↓') : '';
    return h('th',{
      style:{cursor:'pointer',userSelect:'none',whiteSpace:'nowrap',color:active?'var(--accent)':''},
      onClick:()=>{
        S.tracPage = 0;
        if(Srt.col===colKey) S.tracSort={col:colKey,dir:Srt.dir==='asc'?'desc':'asc'};
        else S.tracSort={col:colKey,dir:'asc'};
        render();
      }
    }, label+(arrow?' '+arrow:''));
  }

  // ── Barre de filtres ────────────────────────────────────────────
  // Helper : input texte avec conservation du focus et position du curseur
  const filterInput = (inputId, label, val, onChange)=>{
    const inp = h('input',{
      type:'text', id:inputId, value:val, placeholder:'Rechercher…', className:'filter-input',
      autocomplete:'off', spellcheck:'false'
    });
    inp.addEventListener('input', e=>{
      const selStart = e.target.selectionStart;
      S.tracPage = 0;
      onChange(e.target.value);
      render();
      // Restaurer le focus et la position du curseur après le re-render
      const restored = document.getElementById(inputId);
      if(restored){ restored.focus(); try{restored.setSelectionRange(selStart,selStart);}catch(ex){} }
    });
    return h('div',{className:'filter-group'},
      h('label',null,label),
      inp
    );
  };
  const filterSelect = (inputId, label, options, val, onChange)=>{
    const sel = h('select',{id:inputId, className:'filter-input'},
      ...options.map(o=>h('option',{value:o.val,selected:val===o.val},o.label)));
    sel.addEventListener('change', e=>{ S.tracPage = 0; onChange(e.target.value); render(); });
    return h('div',{className:'filter-group'},
      h('label',null,label),
      sel
    );
  };
  const hasActiveFilter = !!(F.ref||F.client||F.machine||F.statut);

  const filterBar = h('div',{className:'filters-panel',style:{padding:'14px 20px',borderBottom:'1px solid var(--border)'}},
    h('div',{className:'filters'},
      filterInput('trac-f-ref',    'Référence',  F.ref,    v=>{S.tracFilters.ref=v;}),
      filterInput('trac-f-client', 'Client',     F.client, v=>{S.tracFilters.client=v;}),
      filterSelect('trac-f-machine','Machine',
        [{val:'',label:'Toutes machines'},...machinesUniq.map(m=>({val:m,label:m}))],
        F.machine, v=>{S.tracFilters.machine=v;}
      ),
      filterSelect('trac-f-statut','Statut', statuts, F.statut, v=>{S.tracFilters.statut=v;}),
      hasActiveFilter ? h('button',{
        className:'btn btn-sm btn-ghost',
        style:{alignSelf:'flex-end',marginTop:'0'},
        onClick:()=>{ S.tracFilters={ref:'',client:'',machine:'',statut:''}; S.tracShowAttente=false; S.tracPage=0; render(); }
      }, iconEl('x',14),' Effacer') : null
    )
  );

  // ── Lignes tableau ──────────────────────────────────────────────
  const rows = dossiersPage.map(dos=>{
    const hasMatieres = (dos.nb_matieres||0)>0;
    return h('tr',{style:{cursor:'pointer'},
      onClick:async()=>{
        S.traceabiliteDossier = null;
        render();
        await loadTracabiliteDossier(dos.reference);
      }
    },
      h('td',null, h('span',{style:{fontWeight:'800',color:'var(--accent)'}}, dos.reference||'—')),
      h('td',null, dos.client||'—'),
      h('td',null, dos.designation||'—'),
      h('td',null, dos.machine_nom||'—'),
      h('td', null,
        h('div', { style: { display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' } },
          statutBadge(dos.statut || 'attente'),
          (dos.fsc_requis === 1 || dos.fsc_requis === true)
            ? h('span', {
                title: 'Certification FSC requise — ' + (dos.fsc_type_requis || ''),
                style: {
                  background: 'var(--accent-bg)', color: 'var(--accent)',
                  fontSize: '10px', fontWeight: '700',
                  padding: '1px 6px', borderRadius: '4px',
                }
              }, 'FSC')
            : null
        )
      ),
      h('td',null,
        hasMatieres
          ? h('span',{className:'badge badge-ok'}, (dos.nb_matieres||0)+' bobine'+(dos.nb_matieres>1?'s':''))
          : h('span',{className:'badge',style:{opacity:.5}},'Aucune')
      )
    );
  });

  const attenteToggleBar = hiddenAttenteCount > 0
    ? h('div',{
        className:'show-trac-attente-btn',
        onClick:()=>{ S.tracPage=0; S.tracShowAttente=true; render(); }
      }, '▲ '+hiddenAttenteCount+' dossier'+(hiddenAttenteCount>1?'s':'')+' en attente masqué'+(hiddenAttenteCount>1?'s':'')+' — cliquer pour afficher')
    : (showAttente && !forceShowAttente && attenteDossiers.length > 0
      ? h('div',{
          className:'show-trac-attente-btn',
          onClick:()=>{ S.tracPage=0; S.tracShowAttente=false; render(); }
        }, '▼ Masquer les dossiers en attente')
      : null);

  const table = rows.length
    ? h('table',{className:'table-std'},
        h('thead',null,h('tr',null,
          thSort('ref','Référence'),
          thSort('client','Client'),
          thSort('designation','Désignation'),
          thSort('machine','Machine'),
          thSort('statut','Statut'),
          thSort('matieres','Matières')
        )),
        h('tbody',null,...rows)
      )
    : h('div',{className:'card-empty'},allDossiers.length?'Aucun résultat pour ces filtres':'Aucun dossier dans le planning');

  const matchingCount = attenteDossiers.length + mainDossiers.length;
  let badgeSuffix = '';
  if(hiddenAttenteCount > 0 && matchingCount !== totalFiltered){
    badgeSuffix = '/'+matchingCount;
  } else if(matchingCount !== allDossiers.length){
    badgeSuffix = '/'+allDossiers.length;
  }

  return h('div',{className:'card'},
    h('div',{className:'card-header'},
      h('h3',null,'Traçabilité par dossier'),
      h('div',{style:{display:'flex',alignItems:'center',gap:'10px',flexWrap:'wrap'}},
        h('span',{className:'badge'},
          totalFiltered + badgeSuffix + ' dossier' + (totalFiltered!==1?'s':'')
        ),
        totalFiltered > PAGE_SIZE
          ? h('div',{style:{display:'flex',alignItems:'center',gap:'8px'}},
              h('span',{style:{fontSize:'11px',color:'var(--muted)',fontFamily:'monospace'}},
                (pageStart+1)+'–'+pageEnd+' / '+totalFiltered
              ),
              h('button',{
                className:'btn btn-sm btn-ghost',
                disabled:S.tracPage<=0,
                style:{marginTop:'0',padding:'6px 10px'},
                onClick:()=>{ if(S.tracPage>0){ S.tracPage--; render(); } },
                title:'Précédent'
              }, '<'),
              h('button',{
                className:'btn btn-sm btn-ghost',
                disabled:S.tracPage>=maxPage,
                style:{marginTop:'0',padding:'6px 10px'},
                onClick:()=>{ if(S.tracPage<maxPage){ S.tracPage++; render(); } },
                title:'Suivant'
              }, '>')
            )
          : null
      )
    ),
    filterBar,
    attenteToggleBar,
    h('div',{style:{overflowX:'auto',padding:'0 0 8px'}}, table)
  );
}

function closeTracMatieresEditModal(){
  document.getElementById('trac-mat-edit-modal')?.remove();
}

function tracResolveMachineId(dos, matieres){
  const dmid = dos && dos.machine_id;
  if(dmid!=null && dmid!==''){
    const n = Number(dmid);
    return Number.isFinite(n) && n>0 ? n : null;
  }
  const m0 = (matieres||[]).find(x=>x.machine_id!=null && x.machine_id!=='');
  if(m0){
    const n = Number(m0.machine_id);
    return Number.isFinite(n) && n>0 ? n : null;
  }
  return null;
}

async function openTracMatieresEditModal(dos, matieres){
  closeTracMatieresEditModal();
  const ref = (dos.reference||'').trim();
  if(!ref){ showToast('Référence dossier manquante.','danger'); return; }

  let fournisseurs = [];
  try{
    const fd = await api('/api/fabrication/fournisseurs-fsc');
    fournisseurs = Array.isArray(fd) ? fd : (fd.fournisseurs||[]);
  }catch(e){ /* liste optionnelle */ }

  const rows = (matieres||[]).map(m=>{
    const mid = Number(m.id);
    const code = String(m.code_barre||'').trim();
    return {id: (Number.isFinite(mid) && mid > 0) ? mid : null, code, origCode: code, deleted:false};
  });
  const newRows = [];

  const overlay = document.createElement('div');
  overlay.id = 'trac-mat-edit-modal';
  overlay.className = 'contact-modal-overlay';
  overlay.style.zIndex = '9200';

  const box = document.createElement('div');
  box.className = 'contact-modal';
  box.style.maxWidth = '520px';
  box.onclick = (e)=> e.stopPropagation();

  const head = document.createElement('div');
  head.className = 'contact-modal-head';
  const title = document.createElement('h3');
  title.textContent = 'Bobines — '+ref;
  const closeBtn = document.createElement('button');
  closeBtn.className = 'contact-close-btn';
  closeBtn.textContent = '\u2715';
  closeBtn.onclick = closeTracMatieresEditModal;
  head.append(title, closeBtn);

  const body = document.createElement('div');
  body.className = 'contact-modal-body';
  body.style.display = 'grid';
  body.style.gap = '10px';

  const hint = document.createElement('p');
  hint.style.cssText = 'margin:0;font-size:12px;color:var(--muted);line-height:1.5';
  hint.textContent = 'Modifiez les codes barres ou ajoutez une bobine. Les lignes supprimées seront retirées du dossier.';
  body.appendChild(hint);

  const listWrap = document.createElement('div');
  listWrap.style.display = 'grid';
  listWrap.style.gap = '8px';

  const fournWrap = document.createElement('div');
  fournWrap.style.display = 'none';
  const fournLbl = document.createElement('label');
  fournLbl.style.cssText = 'font-size:10px;color:var(--muted);font-weight:700;letter-spacing:.4px;text-transform:uppercase;display:block;margin-bottom:6px';
  fournLbl.textContent = 'Fournisseur (liaison manuelle)';
  const fournSel = document.createElement('select');
  fournSel.className = 'form-sel';
  fournSel.style.width = '100%';
  fournSel.innerHTML = '<option value="">— Choisir —</option>' +
    fournisseurs.map(f=>'<option value="'+Number(f.id)+'">'+escapeHtml(f.nom||'')+'</option>').join('');
  fournWrap.append(fournLbl, fournSel);

  function mkCodeInput(val, placeholder){
    const inp = document.createElement('input');
    inp.type = 'text';
    inp.value = val||'';
    inp.placeholder = placeholder||'Code barre';
    inp.style.cssText = 'flex:1;min-width:0;padding:10px 12px;border-radius:10px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-family:monospace;font-size:13px';
    return inp;
  }

  function renderRows(){
    listWrap.innerHTML = '';
    rows.forEach((row, idx)=>{
      if(row.deleted) return;
      const line = document.createElement('div');
      line.style.cssText = 'display:flex;gap:8px;align-items:center';
      const inp = mkCodeInput(row.code, 'Code barre bobine');
      inp.addEventListener('input', ()=>{ row.code = inp.value; });
      const del = document.createElement('button');
      del.type = 'button';
      del.className = 'btn btn-sm btn-ghost';
      del.title = 'Supprimer';
      del.style.padding = '8px 10px';
      del.innerHTML = '';
      del.appendChild(iconEl('trash',14));
      del.onclick = ()=>{
        if(!confirm('Supprimer cette bobine du dossier ?')) return;
        row.deleted = true;
        renderRows();
      };
      line.append(inp, del);
      listWrap.appendChild(line);
    });
    newRows.forEach((row)=>{
      const line = document.createElement('div');
      line.style.cssText = 'display:flex;gap:8px;align-items:center';
      const inp = mkCodeInput(row.code, 'Nouveau code barre');
      inp.addEventListener('input', ()=>{ row.code = inp.value; });
      const del = document.createElement('button');
      del.type = 'button';
      del.className = 'btn btn-sm btn-ghost';
      del.title = 'Retirer';
      del.style.padding = '8px 10px';
      del.appendChild(iconEl('trash',14));
      del.onclick = ()=>{
        const i = newRows.indexOf(row);
        if(i>=0) newRows.splice(i,1);
        renderRows();
      };
      line.append(inp, del);
      listWrap.appendChild(line);
    });
    if(!rows.some(r=>!r.deleted) && !newRows.length){
      const empty = document.createElement('div');
      empty.style.cssText = 'font-size:12px;color:var(--muted);font-style:italic;padding:4px 0';
      empty.textContent = 'Aucune bobine — ajoutez-en une ci-dessous.';
      listWrap.appendChild(empty);
    }
  }
  renderRows();
  body.appendChild(listWrap);

  const addBtn = document.createElement('button');
  addBtn.type = 'button';
  addBtn.className = 'btn btn-sm btn-ghost';
  addBtn.style.justifySelf = 'start';
  addBtn.appendChild(iconEl('plus',14));
  addBtn.appendChild(document.createTextNode(' Ajouter une bobine'));
  addBtn.onclick = ()=>{ newRows.push({code:''}); renderRows(); };
  body.appendChild(addBtn);
  body.appendChild(fournWrap);

  const actions = document.createElement('div');
  actions.className = 'contact-modal-actions';
  const cancelBtn = document.createElement('button');
  cancelBtn.className = 'btn-ghost';
  cancelBtn.textContent = 'Annuler';
  cancelBtn.onclick = closeTracMatieresEditModal;
  const saveBtn = document.createElement('button');
  saveBtn.className = 'btn-sm';
  saveBtn.textContent = 'Enregistrer';
  saveBtn.onclick = async ()=>{
    const machineId = tracResolveMachineId(dos, matieres);

    const toDelete = rows.filter(r=>r.deleted && r.id).map(r=>r.id);
    const toPatch = rows.filter(r=>{
      if(r.deleted || !r.id) return false;
      const code = String(r.code||'').trim();
      if(!code) return false;
      return code !== String(r.origCode||'').trim();
    });
    const toAdd = [
      ...rows.filter(r=>!r.deleted && !r.id && (r.code||'').trim()).map(r=>(r.code||'').trim()),
      ...newRows.map(r=>(r.code||'').trim()).filter(Boolean),
    ];

    if(!toDelete.length && !toPatch.length && !toAdd.length){
      showToast('Aucune modification.','info');
      closeTracMatieresEditModal();
      return;
    }
    if(toAdd.length && !machineId){
      showToast('Machine du dossier introuvable — impossible d\'ajouter une bobine. Utilisez la saisie sur la machine ou renseignez la machine au planning.','danger');
      return;
    }

    const fid = fournSel.value ? Number(fournSel.value) : null;
    saveBtn.disabled = true;
    saveBtn.textContent = 'Enregistrement…';
    fournWrap.style.display = 'none';

    const postMatiere = async (code)=>{
      const body = {code_barre: code, no_dossier: ref, machine_id: machineId, tracabilite: true};
      if(fid) body.fournisseur_fsc_id = fid;
      try{
        await api('/api/fabrication/matieres', {
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify(body),
        });
      }catch(e){
        const msg = String((e && e.message) || '');
        if(msg.toLowerCase().includes('fournisseur requis')){
          fournWrap.style.display = 'block';
          showToast('Sélectionnez un fournisseur pour les codes non liés à une réception.','danger');
        }
        throw e;
      }
    };

    const patchMatiere = async (row)=>{
      const body = {code_barre: String(row.code||'').trim(), tracabilite: true};
      if(fid) body.fournisseur_fsc_id = fid;
      try{
        await api('/api/fabrication/matieres/'+row.id, {
          method:'PATCH',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify(body),
        });
      }catch(e){
        const msg = String((e && e.message) || '');
        if(msg.toLowerCase().includes('fournisseur requis')){
          fournWrap.style.display = 'block';
          showToast('Sélectionnez un fournisseur pour les codes non liés à une réception.','danger');
        }
        throw e;
      }
    };

    try{
      for(const id of toDelete){
        await api('/api/fabrication/matieres/'+id+'?tracabilite=1', {method:'DELETE'});
      }
      for(const row of toPatch){
        await patchMatiere(row);
      }
      for(const code of toAdd){
        await postMatiere(code);
      }
      closeTracMatieresEditModal();
      showToast('Bobines enregistrées.','success');
      await loadTracabiliteDossier(ref);
    }catch(e){
      if(!String((e&&e.message)||'').toLowerCase().includes('fournisseur requis')){
        showToast((e&&e.message)||'Enregistrement impossible.','danger');
      }
    }finally{
      saveBtn.disabled = false;
      saveBtn.textContent = 'Enregistrer';
    }
  };
  actions.append(cancelBtn, saveBtn);

  box.append(head, body, actions);
  overlay.appendChild(box);
  overlay.addEventListener('click', (e)=>{ if(e.target===overlay) closeTracMatieresEditModal(); });
  document.body.appendChild(overlay);
  requestAnimationFrame(()=>{
    const first = listWrap.querySelector('input');
    if(first) first.focus();
  });
}

function renderTracabiliteDossierDetail(){
  const d = S.traceabiliteDossier;

  const backBtn = h('button',{
    className:'btn btn-sm btn-ghost',
    style:{marginBottom:'12px'},
    onClick:()=>{ S.traceabiliteDossier=undefined; render(); }
  }, iconEl('arrow-left',14),' Retour');

  if(!d) return h('div',null, backBtn, h('div',{className:'card-empty'},'Chargement…'));
  if(d.error) return h('div',null, backBtn, h('div',{style:{color:'var(--danger)',padding:'20px'}},d.error));

  const dos = d.dossier||{};
  const matieres = d.matieres||[];
  const prod = d.production||[];
  const fscSyn = d.fsc_synthese || null;

  // Production summary
  const debutRow = prod.find(r=>r.operation_code==='01');
  const finRow   = prod.filter(r=>r.operation_code==='89').pop();
  const operateurs = [...new Set(prod.map(r=>r.operateur).filter(Boolean))];

  const metrageDebut = debutRow ? debutRow.metrage_prevu : null;
  const metrageFin   = finRow   ? finRow.metrage_reel : null;
  const metrageCalc  = (metrageDebut!=null&&metrageFin!=null) ? Math.max(0,metrageFin-metrageDebut) : null;
  const etiquettes   = finRow   ? finRow.quantite_traitee : null;

  const infoGrid = h('div',{style:{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(160px,1fr))',gap:'8px',margin:'12px 0'}},
    ...[
      {label:'Référence',  val:dos.reference||'—'},
      {label:'Client',     val:dos.client||'—'},
      {label:'Machine',    val:dos.machine_nom||dos.machine||'—'},
      {label:'Opérateur(s)', val:operateurs.join(', ')||'—'},
      {label:'Métrage produit', val:metrageCalc!=null ? fN(metrageCalc)+' m' : '—'},
      {label:'Étiquettes', val:etiquettes!=null ? fN(etiquettes) : '—'},
    ].map(item=>h('div',{style:{background:'var(--bg2)',borderRadius:'8px',padding:'10px 12px'}},
      h('div',{style:{fontSize:'10px',color:'var(--muted)',fontWeight:'700',textTransform:'uppercase',letterSpacing:'.4px',marginBottom:'3px'}},item.label),
      h('div',{style:{fontSize:'13px',fontWeight:'800',color:'var(--text)'}},item.val)
    ))
  );

  // Matières table
  const matiereRows = matieres.map(m=>{
    const dt = m.scanned_at ? new Date(m.scanned_at) : null;
    const dateStr = dt&&!isNaN(dt) ? dt.toLocaleDateString('fr-FR',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}) : '—';
    const claim = m.fsc_type_claim || 'Non FSC';
    const conf = m.fsc_conforme;
    const confCell = conf === true
      ? h('span',{style:{color:'var(--success)',fontWeight:'800'}},'\u2713')
      : conf === false
        ? h('span',{style:{color:'var(--danger)',fontWeight:'800'}},'\u2717'+(m.fsc_warning?' (confirmé)':''))
        : h('span',{style:{color:'var(--muted)'}},'\u2014');
    return h('tr',null,
      h('td',null,h('span',{style:{fontFamily:'monospace',fontWeight:'700',color:'var(--accent)'}},m.code_barre)),
      h('td',null,m.machine_nom||'—'),
      h('td',null,m.operateur||'—'),
      h('td',null,m.fournisseur||'—'),
      h('td',null,claim),
      h('td',null,confCell),
      h('td',null,dateStr)
    );
  });

  const matiereTable = matieres.length
    ? h('table',{className:'table-std'},
        h('thead',null,h('tr',null,
          h('th',null,'Code barre'),
          h('th',null,'Machine'),
          h('th',null,'Opérateur'),
          h('th',null,'Fournisseur'),
          h('th',null,'Claim FSC'),
          h('th',null,'Statut FSC'),
          h('th',null,'Heure scan')
        )),
        h('tbody',null,...matiereRows)
      )
    : h('div',{className:'card-empty',style:{padding:'16px'}},'Aucune bobine matière scannée pour ce dossier');

  const fscBanner = fscSyn ? (()=>{
    const sg = fscSyn.statut_global || 'non_applicable';
    const statutColor = sg === 'conforme' ? 'var(--success)'
      : sg === 'non_conforme' ? 'var(--danger)' : 'var(--muted)';
    const statutBg = sg === 'conforme' ? 'rgba(52,211,153,.12)'
      : sg === 'non_conforme' ? 'rgba(248,113,113,.12)' : 'rgba(148,163,184,.12)';
    let txt = 'Non applicable';
    if(sg === 'conforme'){
      txt = 'Conforme FSC — ' + (fscSyn.nb_bobines_fsc_conformes ?? 0) + '/' + (fscSyn.nb_bobines_total ?? 0) + ' bobine(s)';
    }else if(sg === 'non_conforme'){
      txt = 'Non conforme — ' + (fscSyn.nb_bobines_non_conformes ?? 0) + ' bobine(s) en écart';
    }else if(sg === 'en_attente'){
      txt = 'En attente — aucune bobine scannée';
    }else if((fscSyn.nb_bobines_total ?? 0) === 0){
      txt = 'Aucune bobine scannée';
    }
    return h('div',{style:{margin:'10px 0 0',padding:'10px 14px',borderRadius:'10px',
      background:statutBg,border:'1px solid '+statutColor,color:statutColor,fontWeight:'800',fontSize:'13px'}}, txt);
  })() : null;

  return h('div',null,
    backBtn,
    h('div',{className:'card'},
      h('div',{className:'card-header'},
        h('h3',null,dos.reference||'Dossier'),
        h('div',{style:{display:'flex',alignItems:'center',gap:'8px'}},
          h('span',{className:'badge badge-ok'},finRow?'Terminé':'En cours'),
          (dos.fsc_requis === 1 || dos.fsc_requis === true)
            ? h('button', {
                className: 'btn btn-sm',
                style: {
                  background: 'var(--accent-bg)', color: 'var(--accent)',
                  border: '1px solid var(--accent)', borderRadius: '6px',
                  fontSize: '12px', fontWeight: '700', padding: '4px 10px',
                  cursor: 'pointer',
                },
                onClick: async () => {
                  try {
                    const ref = dos.reference || '';
                    const data = await api('/api/fabrication/tracabilite/' + encodeURIComponent(ref));
                    if (!data) return;
                    openFscRapportModal(data, ref);
                  } catch(e) { showToast('Rapport FSC indisponible.', 'danger'); }
                }
              }, iconEl('file-text', 13), ' Rapport FSC')
            : null
        )
      ),
      infoGrid,
      h('div',{style:{padding:'0 20px 16px'}},
        h('div',{style:{display:'flex',alignItems:'center',justifyContent:'space-between',gap:'10px',marginBottom:'10px'}},
          h('div',{style:{fontWeight:'800',fontSize:'12px',color:'var(--text2)',
            textTransform:'uppercase',letterSpacing:'.4px',display:'flex',alignItems:'center',gap:'6px'}},
            iconEl('box',12),' Bobines matières utilisées ('+matieres.length+')'
          ),
          h('button',{
            type:'button',
            className:'btn btn-sm btn-ghost',
            title:'Modifier les bobines',
            'aria-label':'Modifier les bobines',
            style:{display:'inline-flex',alignItems:'center',gap:'6px',flexShrink:0},
            onClick:()=>openTracMatieresEditModal(dos, matieres)
          }, iconEl('sliders',14), ' Modifier')
        ),
        fscBanner,
        h('div',{style:{overflowX:'auto'}}, matiereTable)
      )
    )
  );
}

function renderProdPage(){
  const subPage = S.subPage || 'kpis';
  // Gestion du polling temps réel machines
  if(subPage==='kpis'){startMachineStatusPolling();}
  else{stopMachineStatusPolling();}
  const tabs = [
    {key:'kpis',    label:"Vue d'ensemble", icon:'wrench'},
    {key:'saisies', label:'Saisies', icon:'pencil'},
    {key:'erreurs', label:'Erreurs & Qualité', icon:'alert-triangle'},
  ];
  const subNav = h('div',{className:'nav-tabs'},
    ...tabs.map(t=>h('button',{
      type:'button',
      className:'nav-tab'+(subPage===t.key?' active':''),
      onClick:async()=>{
        S.subPage=t.key;
        if(t.key==='kpis'){if(!S.production)await loadProd(); await loadMachineStatus(); startMachineStatusPolling();}
        else{stopMachineStatusPolling();}
        if(t.key==='saisies'&&!S.saisies)  await loadSaisies();
        if(t.key==='erreurs'&&!S.historique) await loadHist();
        render();
      }
    }, iconEl(t.icon,14),' '+t.label))
  );
  let content;
  if(subPage==='saisies')  content = renderSaisiesWithImport();
  else if(subPage==='erreurs') content = renderHist();
  else content = renderProdKpis();
  return h('div',null, subNav, content);
}

// ── Historique ──────────────────────────────────────────────────
function renderHist(){
  const d=S.historique;
  if(!d)return h('div',{className:'card-empty'},'Importez un fichier XLSX pour voir les données');
  if(d.blocked)return h('div',{className:'card'},h('div',{className:'card-blocked'},h('div',{className:'cb-icon'},iconEl('lock',32)),h('div',{className:'cb-msg'},d.message)));
  const sc=d.severity_counts||{};const seCount=d.saisie_errors_count||0;const parts=[];
  if(d.sanity_by_operateur){
    const ops=Object.keys(d.sanity_by_operateur||{});
    ops.forEach(op=>parts.push(renderSanity(d.sanity_by_operateur[op], opName(op))));
  }else if(d.sanity){
    parts.push(renderSanity(d.sanity));
  }
  parts.push(h('div',{className:'stats'},
    h('div',{className:'stat'},h('div',{className:'stat-label'},'Total opérations'),h('div',{className:'stat-value',style:{color:'var(--c1)'}},fN(d.total_operations))),
    h('div',{className:'stat',style:{borderColor:'var(--danger)33'}},h('div',{className:'stat-label'},'🔴 Critique'),h('div',{className:'stat-value',style:{color:'var(--danger)'}},fN(sc.critique))),
    h('div',{className:'stat',style:{borderColor:'var(--warn)33'}},h('div',{className:'stat-label'},'🟡 Attention'),h('div',{className:'stat-value',style:{color:'var(--warn)'}},fN(sc.attention))),
    h('div',{className:'stat'},h('div',{className:'stat-label'},'🟢 Normal'),h('div',{className:'stat-value',style:{color:'var(--success)'}},fN(sc.info))),
    h('div',{className:'stat',style:{borderColor:'var(--danger)55'}},h('div',{className:'stat-label'},'⛔ Erreurs saisie'),h('div',{className:'stat-value',style:{color:seCount>0?'var(--danger)':'var(--success)'}},fN(seCount))),
  ));
  parts.push(h('div',{className:'section-title'},'⛔ Erreurs de saisie'));
  const sanityForList = (d.sanity_by_operateur && d.sanity_by_operateur[Object.keys(d.sanity_by_operateur||{})[0]]) ? null : d.sanity;
  parts.push(h('div',{className:'card'},
    h('div',{className:'card-header'},
      h('h3',null,'Contrôles de saisie'),
      seCount>0?h('span',{className:'badge-danger'},seCount+' erreur'+(seCount>1?'s':'')):h('span',{className:'badge'},'OK')
    ),
    d.sanity_by_operateur
      ? h('div',null,
          ...Object.keys(d.sanity_by_operateur||{}).map(op=>
            h('div',{style:{borderTop:'1px solid var(--border)'}},
              h('div',{style:{padding:'12px 20px',fontWeight:'800',color:'var(--text)'}},opName(op)),
              renderSanityEventsBlock(d.sanity_by_operateur[op])
            )
          )
        )
      : renderSanityEventsBlock(sanityForList||d.sanity)
  ));
  if(d.operator_arrets&&d.operator_arrets.length){
    const byOp={};
    (d.operator_arrets||[]).forEach(r=>{
      const op=String(r.operateur||'?');
      if(!byOp[op]) byOp[op]=[];
      byOp[op].push(r);
    });
    const ops=Object.keys(byOp).sort((a,b)=>opName(a).localeCompare(opName(b)));
    parts.push(h('div',{className:'card'},
      h('div',{className:'card-header'},h('h3',null,'Arrêts machine')),
      h('div',{style:{padding:'10px 16px'}},
        ...ops.map(op=>{
          const rows=byOp[op]||[];
          const total=rows.reduce((s,x)=>s+(+x.c||0),0);
          return h('div',{style:{padding:'12px 4px',borderBottom:'1px solid var(--border)'}},
            h('div',{style:{display:'flex',justifyContent:'space-between',alignItems:'center',gap:'12px',flexWrap:'wrap'}},
              h('div',{style:{fontWeight:'800',color:'var(--text)'}},opName(op)),
              h('span',{className:'badge-danger',style:{background:'rgba(251,191,36,.12)',border:'1px solid rgba(251,191,36,.25)',color:'var(--warn)'}},total+' arrêt'+(total>1?'s':''))
            ),
            h('div',{style:{marginTop:'8px',overflowX:'auto'}},
              h('table',null,
                h('thead',null,h('tr',null,h('th',null,'Type'),h('th',null,'Nb'),h('th',null,'Durée'))),
                h('tbody',null,...rows.map(x=>{
                  const code=String(x.operation_code||'');
                  const lbl=(x.operation||'') || (S.OPS_CONFIG && S.OPS_CONFIG[code] && S.OPS_CONFIG[code].label) || ('Code '+code);
                  return h('tr',null,
                    h('td',null,lbl),
                    h('td',{style:{fontFamily:'monospace',fontWeight:'800',color:'var(--warn)'}},String(x.c||0)),
                    h('td',{style:{fontFamily:'monospace',fontWeight:'800',color:'var(--warn)'}},fMin(x.duree_min))
                  );
                }))
              )
            )
          );
        })
      )
    ));
  }
  if(d.issues&&d.issues.length){
    parts.push(h('div',{className:'card'},h('div',{className:'card-header'},h('h3',null,'Détail incidents ('+d.issues.length+')')),
      h('div',{style:{overflowX:'auto'}},h('table',null,
        h('thead',null,h('tr',null,h('th',null,'Sévérité'),h('th',null,'Date'),h('th',null,'Opérateur'),h('th',null,'Opération'),h('th',null,'Machine'),h('th',null,'Dossier'),h('th',null,'Durée'))),
        h('tbody',null,...d.issues.map(r=>h('tr',null,h('td',null,h('span',{className:'sev-dot '+r.operation_severity}),h('span',{className:'sev-'+r.operation_severity},r.operation_severity.toUpperCase())),h('td',null,fD(r.date_operation)),h('td',null,opName(r.operateur)),h('td',null,r.operation||''),h('td',null,r.machine||''),h('td',null,r.no_dossier||''),h('td',null,fMin(r.duree_min)))))
      ))
    ));
  }
  return h('div',null,...parts);
}

// ── Production ──────────────────────────────────────────────────
function renderMachineStatusCards(){
  const ms = S.machineStatus;
  const ICONS = {
    production:  '▶',
    calage:      '⚙',
    arret:       '⛔',
    changement:  '↻',
    nettoyage:   '🧹',
    eteinte:     '○',
    autre:       '·',
  };
  function fmtDuree(min){
    if(min==null||min<0) return null;
    if(min<1) return 'à l\'instant';
    const h=Math.floor(min/60), m=min%60;
    if(h===0) return `${m} min`;
    return m===0?`${h}h`:`${h}h ${m}min`;
  }
  const DUREE_LABEL = {
    production:  'En production depuis',
    calage:      'En calage depuis',
    arret:       'En arrêt depuis',
    changement:  'En changement depuis',
    nettoyage:   'En nettoyage depuis',
    eteinte:     'Éteinte depuis',
    autre:       'Depuis',
  };
  function mkCard(mkey){
    const m = ms && ms[mkey];
    const sk = m ? (m.statut_key||'eteinte') : 'eteinte';
    const label = m ? (m.statut_label||'Éteinte') : 'Éteinte';
    const nom   = m ? m.nom : (mkey==='C1'?'Cohésio 1':'Cohésio 2');
    const op    = m ? (m.operateur||'') : '';
    const dos   = m ? m.dossier : null;
    const icon  = ICONS[sk]||'·';
    const isOn  = sk!=='eteinte';
    const dureeStr = m ? fmtDuree(m.duree_min) : null;
    const dureeLabel = DUREE_LABEL[sk]||'Depuis';
    return h('div',{className:`mst-card mst-${sk}`},
      h('div',{className:'mst-head'},
        h('span',{className:'mst-nom'},nom),
        h('div',{style:{display:'flex',alignItems:'center',gap:'6px'}},
          isOn?h('span',{style:{fontSize:'8px',color:'#22c55e',animation:'pulse 2s infinite',display:'inline-block',borderRadius:'50%',width:'8px',height:'8px',background:'#22c55e'}}):null,
          h('span',{className:'mst-dot'})
        )
      ),
      h('div',{className:'mst-body'},
        h('div',{className:'mst-statut'},icon,' ',label),
        dureeStr?h('div',{className:'mst-duree'},dureeLabel,' ',h('span',{className:'mst-duree-val'},dureeStr)):null,
        op?h('div',{className:'mst-op'},'👤 ',op):null,
        dos?h('div',{className:'mst-dos',style:sk==='changement'?{opacity:'.6',filter:'grayscale(.4)'}:null},
          h('div',{className:'mst-dos-ref'},sk==='changement'?'dossier précédent : #':(h('span',null,'Dossier #')),dos.no_dossier),
          dos.client?h('div',{className:'mst-dos-cli'},dos.client):null,
          dos.designation?h('div',{className:'mst-dos-des'},dos.designation):null
        ):null,
        !ms?h('div',{style:{fontSize:'11px',color:'var(--muted)'}},'Chargement…'):null
      )
    );
  }
  // Carte DSI : placeholder en cours de developpement
  function mkCardDsi(){
    const m = ms && ms.DSI;
    const label = (m && m.statut_label) || 'En cours de développement';
    return h('div',{className:'mst-card mst-en_dev',style:{opacity:.7}},
      h('div',{className:'mst-head'},
        h('span',{className:'mst-nom'},'DSI'),
      ),
      h('div',{className:'mst-body'},
        h('div',{className:'mst-statut',style:{color:'var(--muted)',fontStyle:'italic'}},
          '⚙ ', label)
      )
    );
  }
  // Carte Repiquage : liste des dossiers du jour avec cartons cumules
  function mkCardRepiquage(){
    const m = ms && ms.REP;
    const dossiers = (m && m.dossiers_du_jour) || [];
    const total = m ? Number(m.total_cartons||0) : 0;
    const isOn = dossiers.length > 0;
    const sk = isOn ? 'production' : 'eteinte';
    const fmtNumR = n => Number(n||0).toLocaleString('fr-FR');
    const lines = dossiers.length
      ? dossiers.slice(0,10).map(d => h('div',{
          style:{
            display:'flex',justifyContent:'space-between',alignItems:'center',
            gap:'8px',padding:'4px 0',borderTop:'1px solid var(--border)',
            fontSize:'11px',
          }
        },
          h('div',{style:{display:'flex',flexDirection:'column',gap:'1px',minWidth:'0',flex:'1'}},
            h('div',{style:{fontWeight:'700',color:'var(--accent)',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}},
              d.no_dossier||'—'),
            d.client ? h('div',{style:{fontSize:'10px',color:'var(--text2)',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}, d.client) : null,
          ),
          h('div',{style:{fontFamily:'monospace',fontWeight:'800',color:'var(--text)',whiteSpace:'nowrap'}},
            fmtNumR(d.cartons)+' carton'+(Math.abs(d.cartons)>1?'s':'')),
        ))
      : [h('div',{style:{padding:'8px 0',fontSize:'11px',color:'var(--muted)',fontStyle:'italic'}},
          'Aucune saisie aujourd\u2019hui')];
    return h('div',{className:`mst-card mst-${sk}`},
      h('div',{className:'mst-head'},
        h('span',{className:'mst-nom'},'Repiquage'),
        h('div',{style:{display:'flex',alignItems:'center',gap:'6px'}},
          isOn?h('span',{style:{fontSize:'8px',color:'#22c55e',animation:'pulse 2s infinite',display:'inline-block',borderRadius:'50%',width:'8px',height:'8px',background:'#22c55e'}}):null,
          h('span',{className:'mst-dot'})
        )
      ),
      h('div',{className:'mst-body'},
        h('div',{style:{display:'flex',justifyContent:'space-between',alignItems:'baseline',marginBottom:'4px'}},
          h('span',{style:{fontSize:'11px',color:'var(--muted)',textTransform:'uppercase',letterSpacing:'.5px',fontWeight:'700'}},
            'Aujourd\u2019hui'),
          h('span',{style:{fontFamily:'monospace',fontWeight:'800',color:'var(--accent)'}},
            fmtNumR(total)+' cartons')
        ),
        ...lines,
        !ms?h('div',{style:{fontSize:'11px',color:'var(--muted)'}},'Chargement…'):null
      )
    );
  }
  return h('div',null,
    h('div',{className:'section-title',style:{display:'flex',alignItems:'center',justifyContent:'space-between'}},
      h('span',null,iconEl('cpu',13),' Statut machines'),
      h('div',{style:{display:'flex',gap:'8px'}},
        h('button',{
          type:'button',
          id:'mst-refresh-btn',
          style:{fontSize:'10px',color:'var(--accent)',background:'none',border:'none',cursor:'pointer',padding:'2px 6px',fontFamily:'inherit'},
          onClick:async()=>{
            const btn=document.getElementById('mst-refresh-btn');
            if(btn){btn.textContent='↺ Actualisation…';btn.disabled=true;}
            await loadMachineStatus();
            if(btn){btn.textContent='↺ Actualiser';btn.disabled=false;}
          }
        },'↺ Actualiser')
      )
    ),
    h('div',{className:'mst-grid'},
      mkCard('C1'),
      mkCard('C2')
    ),
    h('div',{className:'mst-grid',style:{marginTop:'12px'}},
      mkCardDsi(),
      mkCardRepiquage()
    )
  );
}

function formatJourLabel(j){
  if(!j)return '—';
  const m=String(j).match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if(m)return m[3]+'/'+m[2]+'/'+m[1];
  return String(j);
}
function prodSynthPeriodLabel(){
  const f=S.fv||{};
  if(f.date_from&&f.date_to)return formatJourLabel(f.date_from)+' → '+formatJourLabel(f.date_to);
  if(f.date_from)return 'Depuis le '+formatJourLabel(f.date_from);
  if(f.date_to)return 'Jusqu\'au '+formatJourLabel(f.date_to);
  return 'Période des filtres actifs';
}
function prodSynthDisplayKey(type,key){
  if(type==='operator')return opName(key)||'—';
  if(type==='day')return formatJourLabel(key);
  return String(key||'—');
}
function prodSynthFilterSessions(type,key){
  const rows=(S.production&&S.production.by_dossier)||[];
  const k=String(key||'').trim();
  return rows.filter(r=>{
    if(type==='dossier')return String(r.no_dossier||'').trim()===k;
    if(type==='operator')return String(r.operateur||'?').trim()===k;
    if(type==='machine')return String(r.machine||'?').trim()===k;
    if(type==='day')return String(r.jour||'').trim()===k;
    return false;
  }).sort((a,b)=>{
    const dj=String(b.jour||'').localeCompare(String(a.jour||''));
    if(dj!==0)return dj;
    return opName(a.operateur).localeCompare(opName(b.operateur),'fr');
  });
}
function prodSynthTotals(sessions){
  const t={sessions:sessions.length,etiquettes:0,metrage_m:0,calage_min:0,prod_min:0,arret_min:0};
  sessions.forEach(s=>{
    t.etiquettes+=Number(s.etiquettes||0);
    t.metrage_m+=Number(s.metrage_m||0);
    t.calage_min+=Number(s.temps_calage_min||0);
    t.prod_min+=Number(s.temps_prod_min||0);
    t.arret_min+=Number(s.temps_arret_min||0);
  });
  t.metrage_m=Math.round(t.metrage_m*10)/10;
  const den=t.prod_min+t.arret_min;
  t.vitesse=den>0?(t.metrage_m/den).toFixed(2):'0.00';
  return t;
}
function prodSynthCleanClient(c){
  if(!c)return '';
  const p=String(c).split(' - ');
  if(p.length===2&&/^\d+$/.test(p[0].trim()))return p[1].trim();
  return String(c).trim();
}
function closeProdSynthModal(){
  try{
    const m=document.querySelector('.prod-synth-modal');
    if(m&&m._navKeyHandler){
      document.removeEventListener('keydown',m._navKeyHandler,true);
    }
    if(m)m.remove();
  }catch(e){}
}
function openProdSynthDetail(type,keys,index){
  const list=(keys||[]).map(k=>String(k));
  if(!list.length)return;
  let idx=Number(index);
  if(!Number.isFinite(idx)||idx<0)idx=0;
  if(idx>=list.length)idx=list.length-1;
  const key=list[idx];
  closeProdSynthModal();
  const TYPE_TITLES={dossier:'Dossier',operator:'Opérateur',machine:'Machine',day:'Jour'};
  const sessions=prodSynthFilterSessions(type,key);
  const tot=prodSynthTotals(sessions);
  const total=list.length;
  const goPrev=()=>{if(total>1)openProdSynthDetail(type,list,(idx-1+total)%total);};
  const goNext=()=>{if(total>1)openProdSynthDetail(type,list,(idx+1)%total);};
  const overlay=h('div',{className:'add-row-modal prod-synth-modal'});
  overlay.addEventListener('click',e=>{if(e.target===overlay)closeProdSynthModal();});
  const counter=h('span',{className:'add-row-counter',title:'← → pour naviguer'},
    h('button',{type:'button',className:'add-row-nav-btn',title:'Précédent (←)',disabled:total<=1,onClick:e=>{e.stopPropagation();goPrev();}},'<'),
    h('span',null,String(idx+1)+'/'+String(total)),
    h('button',{type:'button',className:'add-row-nav-btn',title:'Suivant (→)',disabled:total<=1,onClick:e=>{e.stopPropagation();goNext();}},'>')
  );
  const titleRow=h('div',{className:'prod-synth-detail-head'},
    h('div',{className:'prod-synth-detail-title-main'},
      h('span',{className:'prod-synth-detail-eyebrow'}, TYPE_TITLES[type]||'Synthèse'),
      h('h3',{className:'prod-synth-detail-h3'}, prodSynthDisplayKey(type,key))
    ),
    counter
  );
  const kpi=(lbl,val)=>h('div',{className:'prod-synth-kpi'},
    h('div',{className:'lbl'},lbl),
    h('div',{className:'val'},val)
  );
  const showDossierCol=type!=='dossier';
  const sessionRows=sessions.length?sessions.map(s=>{
    const den=Number(s.temps_prod_min||0)+Number(s.temps_arret_min||0);
    const vit=den>0?(Number(s.metrage_m||0)/den).toFixed(2):'0.00';
    const cli=prodSynthCleanClient(s.client);
    const des=(s.designation||'').replace(/^,\s*/,'').trim();
    return h('tr',null,
      h('td',{className:'prod-synth-detail-td-text'},formatJourLabel(s.jour)),
      h('td',{className:'prod-synth-detail-td-text'},opName(s.operateur)),
      h('td',{className:'prod-synth-detail-td-text'},s.machine||'—'),
      showDossierCol?h('td',{className:'prod-synth-detail-td-mono'},s.no_dossier||'—'):null,
      h('td',{className:'prod-synth-detail-td-text'},cli||'—'),
      h('td',{className:'prod-synth-detail-td-wrap'},des||'—'),
      h('td',{className:'prod-synth-detail-td-num'},fN(s.etiquettes||0)),
      h('td',{className:'prod-synth-detail-td-num'},fN(s.metrage_m||0)+' m'),
      h('td',{className:'prod-synth-detail-td-num'},fMin(s.temps_calage_min)),
      h('td',{className:'prod-synth-detail-td-num'},fMin(s.temps_prod_min)),
      h('td',{className:'prod-synth-detail-td-num'},fMin(s.temps_arret_min)),
      h('td',{className:'prod-synth-detail-td-vit'},vit+' m/min')
    );
  }):[h('tr',null,h('td',{colSpan:showDossierCol?11:10,className:'prod-synth-detail-empty'},'Aucune session sur la période filtrée.'))];
  const isMobileSynth=window.innerWidth<=900;
  if(isMobileSynth) overlay.classList.add('prod-synth-modal--compact');
  const sessionsBlock=h('div',{className:'prod-synth-detail-sessions'},
    h('div',{className:'prod-synth-detail-section-h'},'Détail par session'),
    h('div',{className:'prod-synth-detail-table-wrap'},
      h('table',{className:'table-std prod-synth-detail-table'},
        h('thead',null,h('tr',null,
          h('th',null,'Jour'),h('th',null,'Opérateur'),h('th',null,'Machine'),
          showDossierCol?h('th',null,'Dossier'):null,
          h('th',null,'Client'),h('th',null,'Désignation'),
          h('th',{style:{textAlign:'right'}},'Étiquettes'),h('th',{style:{textAlign:'right'}},'Métrage'),h('th',{style:{textAlign:'right'}},'Calage'),
          h('th',{style:{textAlign:'right'}},'Prod'),h('th',{style:{textAlign:'right'}},'Arrêts'),h('th',{style:{textAlign:'right'}},'Vitesse')
        )),
        h('tbody',null,...sessionRows)
      )
    )
  );
  const kpisBlock=h('div',{className:'prod-synth-kpis'},
    kpi('Sessions',String(tot.sessions)),
    kpi('Étiquettes',fN(tot.etiquettes)),
    kpi('Métrage',fN(tot.metrage_m)+' m'),
    kpi('Calage',fMin(tot.calage_min)),
    kpi('Production',fMin(tot.prod_min)),
    kpi('Arrêts',fMin(tot.arret_min)),
    kpi('Vitesse',tot.vitesse+' m/min')
  );
  const formKids=[
    h('button',{type:'button',className:'add-row-close',title:'Fermer (Échap)',onClick:e=>{e.stopPropagation();closeProdSynthModal();}},'×'),
    titleRow,
    h('div',{className:'prod-synth-sub'},prodSynthPeriodLabel(),' · ',sessions.length,' session'+(sessions.length>1?'s':'')),
    kpisBlock,
  ];
  if(isMobileSynth&&sessions.length){
    const sessLbl=sessions.length===1?'1 session':'Détail par session ('+sessions.length+')';
    formKids.push(h('button',{
      type:'button',
      className:'btn-ghost prod-synth-sessions-toggle',
      onClick:e=>{
        e.stopPropagation();
        const open=overlay.classList.toggle('prod-synth-modal--sessions-open');
        const btn=e.currentTarget;
        if(btn) btn.textContent=open?'Masquer le détail par session':sessLbl;
      },
    },sessLbl));
  }
  formKids.push(sessionsBlock);
  if(!isMobileSynth){
    formKids.push(h('div',{className:'prod-synth-detail-footer'},
      'Navigation : flèches gauche et droite — Fermer : Échap'));
  }
  const form=h('div',{className:'add-row-form prod-synth-detail-form'},...formKids);
  overlay.appendChild(form);
  const handler=(e)=>{
    if(e.key==='Escape'){e.preventDefault();closeProdSynthModal();return;}
    if(e.key==='ArrowLeft'){e.preventDefault();goPrev();return;}
    if(e.key==='ArrowRight'){e.preventDefault();goNext();}
  };
  document.addEventListener('keydown',handler,true);
  overlay._navKeyHandler=handler;
  document.getElementById('root').appendChild(overlay);
}
function makeProdSynthKeyCell(label,type,keys,index){
  return h('td',{
    className:'prod-synth-key',
    title:'Voir le détail — flèches pour naviguer',
    onClick:e=>{e.stopPropagation();openProdSynthDetail(type,keys,index);}
  },label);
}

// ── Helper : wrapper "section repliable" avec chevron + persistance ──────
function _prodSectionState(key, defOpen){
  try{
    const v = localStorage.getItem('mysifa.prod.section.'+key);
    if(v === '0') return false;
    if(v === '1') return true;
  }catch(e){}
  return defOpen!==false;
}
function _prodSetSectionState(key, open){
  try{ localStorage.setItem('mysifa.prod.section.'+key, open?'1':'0'); }catch(e){}
}
function makeCollapsibleSection(titleNode, contentNode, storageKey, defaultOpen){
  const isOpen = _prodSectionState(storageKey, defaultOpen!==false);
  const chev = h('span',{
    style:{
      display:'inline-flex',alignItems:'center',justifyContent:'center',
      width:'18px',height:'18px',color:'var(--muted)',
      transition:'transform .15s',
      transform: isOpen?'rotate(90deg)':'rotate(0deg)',
      flexShrink:0,
    }
  },'▶');
  const header = h('div',{
    style:{
      display:'flex',alignItems:'center',gap:'8px',cursor:'pointer',
      userSelect:'none',
    },
    onClick:(ev)=>{
      const wrap = ev.currentTarget.parentNode;
      const ct = wrap.querySelector('.prod-section-content');
      const cv = wrap.querySelector('.prod-section-chev');
      const nowOpen = !(ct.style.display !== 'none');
      const next = !nowOpen;
      ct.style.display = next ? '' : 'none';
      cv.style.transform = next ? 'rotate(90deg)' : 'rotate(0deg)';
      _prodSetSectionState(storageKey, next);
    },
  }, h('span',{className:'prod-section-chev',style:chev.style.cssText? null : chev.style},'▶'), titleNode);
  // Patcher : on a duplique le chev, on utilise celui dans le DOM final
  // Plus simple: reconstruire via innerHTML pour fiabilite
  const wrap = h('div',{className:'prod-section-wrap',style:{marginBottom:'14px'}},
    h('div',{
      className:'prod-section-header',
      style:{
        display:'flex',alignItems:'center',gap:'8px',cursor:'pointer',
        userSelect:'none',padding:'2px 0',
      },
      onClick:(ev)=>{
        const root = ev.currentTarget.parentNode;
        const ct = root.querySelector('.prod-section-content');
        const cv = root.querySelector('.prod-section-chev');
        const isVisible = ct.style.display !== 'none';
        const next = !isVisible;
        ct.style.display = next ? '' : 'none';
        if(cv) cv.style.transform = next ? 'rotate(90deg)' : 'rotate(0deg)';
        _prodSetSectionState(storageKey, next);
      },
    },
      h('span',{
        className:'prod-section-chev',
        style:{
          display:'inline-block',width:'14px',textAlign:'center',
          color:'var(--muted)',fontSize:'11px',
          transition:'transform .15s',
          transform: isOpen?'rotate(90deg)':'rotate(0deg)',
        }
      },'▶'),
      titleNode,
    ),
    h('div',{
      className:'prod-section-content',
      style:{display: isOpen ? '' : 'none', marginTop:'6px'},
    }, contentNode),
  );
  return wrap;
}

function renderProdKpis(){
  const d=S.production;
  if(!d)return h('div',{className:'card-empty'},'Chargement des données de production…');
  if(d.blocked)return h('div',{className:'card'},h('div',{className:'card-blocked'},h('div',{className:'cb-icon'},iconEl('lock',32)),h('div',{className:'cb-msg'},d.message)));
  const prod = d.produit||{};
  const tt=d.temps_totaux||{};const parts=[];
  if(canViewAllProd(S.user)){
    parts.push(renderMachineStatusCards());
  }

  // ── Sanity score cliquable ─────────────────────────────────────
  if(S.historique&&S.historique.sanity){
    const sc=renderSanity(S.historique.sanity);
    if(sc){
      sc.style.cursor='pointer';
      sc.title='Voir le détail des erreurs → Historique & Erreurs';
      sc.addEventListener('click',async()=>{
        S.subPage='erreurs';
        if(!S.historique) await loadHist();
        render();
      });
      sc.appendChild(h('div',{style:{fontSize:'11px',color:'var(--accent)',marginTop:'6px',textDecoration:'underline'}},'Voir le détail →'));
      parts.push(sc);
    }
  }
  parts.push(makeCollapsibleSection(
    h('span',{className:'section-title',style:{display:'inline-flex',alignItems:'center',gap:'4px',margin:0,padding:0,border:'none'}},iconEl('box',13),' Quantités'),
    h('div',{className:'stats'},
      h('div',{className:'stat'},h('div',{className:'stat-label'},'Dossiers produits'),h('div',{className:'stat-value'},fN(prod.dossiers||0))),
      h('div',{className:'stat'},h('div',{className:'stat-label'},'Qté étiquettes'),h('div',{className:'stat-value'},fN(prod.etiquettes||0))),
      h('div',{className:'stat'},h('div',{className:'stat-label'},'Métrage'),h('div',{className:'stat-value'},fN(prod.metrage_m||0)+' m')),
      h('div',{className:'stat'},h('div',{className:'stat-label'},'Vitesse'),h('div',{className:'stat-value'},((d.vitesse_m_min!=null)?Number(d.vitesse_m_min).toFixed(2):'0.00')+' m/min')),
    ),
    'quantites'
  ));
  const prodInclArrets = (Number(tt.production_min||0) + Number(tt.arret_min||0));
  parts.push(makeCollapsibleSection(
    h('span',{className:'section-title',style:{display:'inline-flex',alignItems:'center',gap:'4px',margin:0,padding:0,border:'none'}},iconEl('clock',13),' Temps'),
    h('div',{className:'time-kpi'},
      h('div',{className:'time-card'},h('div',{className:'tc-label',style:{display:'inline-flex',alignItems:'center',gap:'6px'}},iconEl('wrench',12),' Calage'),h('div',{className:'tc-value'},fMin(tt.calage_min))),
      h('div',{className:'time-card'},h('div',{className:'tc-label',style:{display:'inline-flex',alignItems:'center',gap:'6px'}},iconEl('play',12),' Production'),h('div',{className:'tc-value'},fMin(prodInclArrets))),
      h('div',{className:'time-card'},h('div',{className:'tc-label',style:{display:'inline-flex',alignItems:'center',gap:'6px'}},iconEl('alert-triangle',12),' Arrêts'),h('div',{className:'tc-value'},fMin(tt.arret_min))),
    ),
    'temps'
  ));
  const byDos = d.by_dossier || d.dossier_times || [];

  function renderAggCard(title, rows, keyLabel, synthType){
    if(!rows||!rows.length) return null;
    const keys=rows.map(r=>String(r.key));
    const typeMap={'Opérateur':'operator','Machine':'machine','Jour':'day'};
    const st=synthType||(typeMap[keyLabel]||'');
    return h('div',{className:'card'},
      h('div',{className:'card-header'},h('h3',null,title),h('span',{style:{fontSize:'11px',color:'var(--muted)'}},rows.length+' items')),
      h('div',{style:{overflowX:'auto'}},h('table',null,
        h('thead',null,h('tr',null,h('th',null,keyLabel),h('th',null,'Dossiers'),h('th',null,'Étiquettes'),h('th',null,'Métrage'),h('th',null,'Calage'),h('th',null,'Prod'),h('th',null,'Arrêts'),h('th',null,'Vitesse'))),
        h('tbody',null,...rows.map((r,i)=>h('tr',{className: r.is_repiquage_team?'rep-team-row':''},
          makeProdSynthKeyCell(keyLabel==='Opérateur'?(r.is_repiquage_team?r.key:opName(r.key)):(keyLabel==='Jour'?formatJourLabel(r.key):r.key),st,keys,i),
          h('td',{style:{fontFamily:'monospace'}},fN(r.dossiers||0)),
          h('td',{style:{fontFamily:'monospace'}},fN(r.etiquettes||0)),
          h('td',{style:{fontFamily:'monospace'}},fN(r.metrage_m||0)+' m'),
          h('td',{style:{fontFamily:'monospace'}},fMin(r.calage_min)),
          h('td',{style:{fontFamily:'monospace'}},fMin(r.prod_min)),
          h('td',{style:{fontFamily:'monospace'}},fMin(r.arret_min)),
          h('td',{style:{fontFamily:'monospace',fontWeight:'800',color:'var(--warn)'}},String(r.vitesse_m_min||0)+' m/min')
        )))
      ))
    );
  }

  // ── Synthèse détaillée : wrapper repliable global qui englobe tous les tableaux
  const synthParts = [];
  // Détail par dossier en premier
  if(byDos&&byDos.length){
    // Agrégation par no_dossier
    const byRef = {};
    byDos.forEach(r=>{
      const k = String(r.no_dossier||'').trim();
      if(!k) return;
      if(!byRef[k]){
        byRef[k] = {
          no_dossier: k,
          etiquettes: 0,
          metrage_m: 0,
          temps_calage_min: 0,
          temps_prod_min: 0,
          temps_arret_min: 0,
        };
      }
      byRef[k].etiquettes += Number(r.etiquettes||0);
      byRef[k].metrage_m += Number(r.metrage_m||0);
      byRef[k].temps_calage_min += Number(r.temps_calage_min||0);
      byRef[k].temps_prod_min += Number(r.temps_prod_min||0);
      byRef[k].temps_arret_min += Number(r.temps_arret_min||0);
    });
    const rowsAgg = Object.values(byRef).sort((a,b)=>String(a.no_dossier).localeCompare(String(b.no_dossier), 'fr', {numeric:true,sensitivity:'base'}));
    const dossierKeys=rowsAgg.map(r=>String(r.no_dossier));

    synthParts.push(h('div',{className:'card'},h('div',{className:'card-header'},h('h3',null,'Par numéro de dossier'),h('span',{style:{fontSize:'11px',color:'var(--muted)'}},rowsAgg.length+' dossiers')),
      h('div',{style:{overflowX:'auto'}},h('table',null,
        h('thead',null,h('tr',null,
          h('th',null,'Dossier'),
          h('th',null,'Étiquettes'),
          h('th',null,'Métrage'),
          h('th',null,'Calage'),
          h('th',null,'Prod'),
          h('th',null,'Arrêts'),
          h('th',null,'Vitesse')
        )),
        h('tbody',null,...rowsAgg.map((r,i)=>h('tr',null,
          makeProdSynthKeyCell(r.no_dossier||'','dossier',dossierKeys,i),
          h('td',{style:{fontFamily:'monospace'}},fN(r.etiquettes||0)),
          h('td',{style:{fontFamily:'monospace'}},fN(r.metrage_m||0)+' m'),
          h('td',{style:{fontFamily:'monospace',color:'var(--text2)'}},fMin(r.temps_calage_min)),
          h('td',{style:{fontFamily:'monospace',color:'var(--text2)'}},fMin(r.temps_prod_min)),
          h('td',{style:{fontFamily:'monospace',color:'var(--text2)'}},fMin(r.temps_arret_min)),
          h('td',{style:{fontFamily:'monospace',fontWeight:'800',color:'var(--warn)'}},(()=>{const den=Number(r.temps_prod_min||0)+Number(r.temps_arret_min||0);return (den>0?(Number(r.metrage_m||0)/den).toFixed(2):'0.00')+' m/min';})())
        )))
      ))
    ));
  }
  const byOp=d.by_operator||[];
  const byMach=d.by_machine||[];
  const byDay=d.by_day||[];
  synthParts.push(renderAggCard('Par opérateur',byOp,'Opérateur'));
  synthParts.push(renderAggCard('Par machine',byMach,'Machine'));
  synthParts.push(renderAggCard('Par jour',byDay,'Jour'));

  parts.push(makeCollapsibleSection(
    h('span',{className:'section-title',style:{margin:0,padding:0,border:'none'}},'📌 Synthèse détaillée'),
    h('div',null,...synthParts.filter(Boolean)),
    'synthese'
  ));

  return h('div',null,...parts);
}

// ── Modal ajout ligne ───────────────────────────────────────────

// ── Undo / Redo (session uniquement, tout en mémoire) ──────────
let undoStack = [];  // [{id, snapshot}, ...]
let redoStack = [];
 
function pushUndo(action, data) {
  // action : 'edit' | 'add' | 'delete'
  // data   : pour edit/delete = snapshot de la ligne
  //          pour add = { id } (on supprimera)
  undoStack.push({ action, data: JSON.parse(JSON.stringify(data)) });
  redoStack = [];
  updateUndoRedoBtns();
}
 
function updateUndoRedoBtns() {
  const btnU = document.getElementById('btn-undo');
  const btnR = document.getElementById('btn-redo');
  if (btnU) btnU.disabled = undoStack.length === 0;
  if (btnR) btnR.disabled = redoStack.length === 0;
}
 
async function doUndo() {
  if (!undoStack.length) return;
  const entry = undoStack.pop();
  const curRows = (S.saisies && S.saisies.rows) ? S.saisies.rows : [];
  const current = curRows.find(r => r.id === entry.data.id);

  // Pour edit : sauvegarder l'état actuel avant restauration
  if (entry.action === 'edit' && current) {
    redoStack.push({ action: 'edit', data: JSON.parse(JSON.stringify(current)) });
  } else if (entry.action === 'add') {
    redoStack.push({ action: 'delete_then_recreate', data: entry.data });
  } else if (entry.action === 'delete') {
    // On pousse un placeholder — applyUndo va corriger l'id après le POST
    redoStack.push({ action: 'delete', data: { ...entry.data } });
  }

  await applyUndo(entry);
}

async function doRedo() {
  if (!redoStack.length) return;
  const entry = redoStack.pop();
  const curRows2 = (S.saisies && S.saisies.rows) ? S.saisies.rows : [];
  const current = curRows2.find(r => r.id === entry.data.id);
  if (entry.action === 'edit' && current) {
    undoStack.push({ action: 'edit', data: JSON.parse(JSON.stringify(current)) });
    await api('/api/saisies/' + entry.data.id, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...entry.data, note: 'Restauration redo' })
    });
  } else if (entry.action === 'delete') {
    // Redo d'une suppression = supprimer à nouveau
    await api('/api/saisies/' + entry.data.id, { method: 'DELETE' });
  } else if (entry.action === 'delete_then_recreate') {
    // Redo d'un ajout = recréer
    await api('/api/saisies', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...entry.data, note: 'Restauration redo (ajout)' })
    });
  }
  toast('Action rétablie');
  await loadSaisies();
}

 async function applyUndo(entry) {
  try {
    if (entry.action === 'edit') {
      // Restaurer l'ancien état
      await api('/api/saisies/' + entry.data.id, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          operation:          entry.data.operation,
          date_operation:     entry.data.date_operation,
          operateur:          entry.data.operateur,
          machine:            entry.data.machine,
          no_dossier:         entry.data.no_dossier,
          quantite_a_traiter: entry.data.quantite_a_traiter,
          quantite_traitee:   entry.data.quantite_traitee,
          metrage_prevu:     entry.data.metrage_prevu ?? null,
          metrage_reel:      entry.data.metrage_reel ?? null,
          commentaire:       entry.data.commentaire || '',
          note:               'Restauration undo',
        })
      });
    } else if (entry.action === 'add') {
      // Annuler un ajout = supprimer la ligne créée
      await api('/api/saisies/' + entry.data.id, { method: 'DELETE' });
    } else if (entry.action === 'delete') {
      // Annuler une suppression = recréer la ligne
      const r = await api('/api/saisies', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          operation:          entry.data.operation,
          date_operation:     entry.data.date_operation,
          operateur:          entry.data.operateur,
          machine:            entry.data.machine,
          no_dossier:         entry.data.no_dossier,
          quantite_a_traiter: entry.data.quantite_a_traiter,
          quantite_traitee:   entry.data.quantite_traitee,
          metrage_prevu:     entry.data.metrage_prevu ?? null,
          metrage_reel:      entry.data.metrage_reel ?? null,
          commentaire:       entry.data.commentaire || '',
          note:               'Restauration undo (suppression annulée)',
        })
      });
      // Mettre à jour le redo avec le NOUVEL id retourné par l'API
      // car l'ancien id n'existe plus en base
      if (r && r.id) {
        // Corriger l'entrée redo qui vient d'être poussée dans doUndo
        const lastRedo = redoStack[redoStack.length - 1];
        if (lastRedo && lastRedo.action === 'delete') {
          lastRedo.data = { ...entry.data, id: r.id };
        }
      }
    }
    toast('Action annulée');
    await loadSaisies();
  } catch(e) { toast(e.message, 'error'); }
}
 
// ── Helpers date 24h ───────────────────────────────────────────
function dateToInputVal(dateStr) {
  // Convertit '01/04/2026 12:53:45' → {date:'2026-04-01', time:'12:53:45'}
  if (!dateStr) return { date: '', time: '' };
  const s = dateStr.replace(/C$/, '').trim();
  const m = s.match(/^(\d{2})\/(\d{2})\/(\d{4})\s+(\d{2}):(\d{2})(?::(\d{2}))?/);
  if (m) return { date: m[3]+'-'+m[2]+'-'+m[1], time: m[4]+':'+m[5]+':'+(m[6]!=null?m[6]:'00') };
  const m2 = s.match(/^(\d{4}-\d{2}-\d{2})(?:T(\d{2}):(\d{2})(?::(\d{2}))?)?/);
  if (m2) return { date: m2[1], time: (m2[2]&&m2[3]) ? m2[2]+':'+m2[3]+':'+(m2[4]!=null?m2[4]:'00') : '00:00:00' };
  return { date: '', time: '' };
}
 
function inputValToFrDate(dateVal, timeVal) {
  // Convertit '2026-04-01' + '12:53:45' → '01/04/2026 12:53:45'
  if (!dateVal) return datetime_now_fr();
  const [y, mo, d] = dateVal.split('-');
  const parts = String(timeVal || '00:00:00').split(':');
  const hh = (parts[0] || '00').padStart(2, '0');
  const mm = (parts[1] || '00').padStart(2, '0');
  const ss = (parts[2] != null ? parts[2] : '00').padStart(2, '0');
  return d+'/'+mo+'/'+y+' '+hh+':'+mm+':'+ss;
}
 
function datetime_now_fr() {
  const now = new Date();
  return String(now.getDate()).padStart(2,'0')+'/'+
         String(now.getMonth()+1).padStart(2,'0')+'/'+
         now.getFullYear()+' '+
         String(now.getHours()).padStart(2,'0')+':'+
         String(now.getMinutes()).padStart(2,'0')+':00';
}
 
function makeDateTimeFields(existingDateStr) {
  // Retourne {wrapper, getVal()} avec deux inputs date + time en 24h
  const { date: dv, time: tv } = dateToInputVal(existingDateStr);
  const dateI = h('input', { type: 'date', value: dv, lang: 'fr', style: { flex: '1' } });
  // IMPORTANT: input[type=time] peut afficher AM/PM selon OS/locale (iOS/Safari).
  // On force donc une saisie manuelle HH:MM (24h) via un input texte.
  const timeI = h('input', {
    type: 'text',
    inputmode: 'numeric',
    autocomplete: 'off',
    placeholder: 'HH:MM:SS',
    value: (String(tv || '00:00:00').slice(0,8) || ''),
    style: { width: '96px', fontFamily: 'monospace' }
  });
  timeI.setAttribute('maxlength', '8');

  function normalizeTime(raw){
    const s = String(raw||'').trim().replace(/[^\d:]/g,'');
    const digits = s.replace(/:/g,'');
    if(/^\d+$/.test(digits)){
      if(digits.length <= 4){
        const z = digits.padStart(4,'0');
        return z.slice(0,2)+':'+z.slice(2,4)+':00';
      }
      if(digits.length <= 6){
        const z = digits.padStart(6,'0');
        return z.slice(0,2)+':'+z.slice(2,4)+':'+z.slice(4,6);
      }
    }
    const m = s.match(/^(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?$/);
    if(m){
      const hh = String(m[1]).padStart(2,'0');
      const mm = String(m[2]).padStart(2,'0');
      const ss = m[3]!=null ? String(m[3]).padStart(2,'0') : '00';
      return hh+':'+mm+':'+ss;
    }
    if(/^\d{2}:\d{2}:\d{2}$/.test(s)) return s;
    return '';
  }
  function isValidHHMMSS(s){
    const m = String(s||'').match(/^(\d{2}):(\d{2}):(\d{2})$/);
    if(!m) return false;
    const hh = parseInt(m[1],10), mm = parseInt(m[2],10), ss = parseInt(m[3],10);
    return hh>=0 && hh<=23 && mm>=0 && mm<=59 && ss>=0 && ss<=59;
  }
  function getTimeVal(){
    const norm = normalizeTime(timeI.value);
    if(norm) timeI.value = norm;
    return isValidHHMMSS(timeI.value) ? timeI.value : null;
  }
  timeI.addEventListener('input', ()=>{
    let v = String(timeI.value||'').replace(/[^\d]/g,'').slice(0,6);
    if(v.length >= 5) v = v.slice(0,2)+':'+v.slice(2,4)+':'+v.slice(4);
    else if(v.length >= 3) v = v.slice(0,2)+':'+v.slice(2);
    timeI.value = v;
  });
  timeI.addEventListener('blur', ()=>{ getTimeVal(); });

  const wrapper = h('div', { style: { display:'flex', gap:'8px' } }, dateI, timeI);
  return { wrapper, getVal: () => {
    const t = getTimeVal();
    if(!t) return null;
    return inputValToFrDate(dateI.value, t);
  }};
}
 
// ── Modal générique (add + edit) ───────────────────────────────
function buildSaisieForm(prefill, title, submitLabel, onSubmit, extraBtn) {
  const ops = S.OPS_CONFIG;
  const ops_list = S.filters.operators || [];
  const inputs = {};
 
  // Sélect opération
  const opSel = h('select', null,
    h('option', { value: '' }, '— Choisir une opération —'),
    ...Object.entries(ops).map(([code, cfg]) => {
      const opt = h('option', { value: code+'           '+cfg.label }, code+' — '+cfg.label);
      // Pré-sélection si edit
      if (prefill && prefill.operation && prefill.operation.startsWith(code)) opt.selected = true;
      return opt;
    })
  );
  const opPreview = h('div', { className: 'op-preview' });
  opSel.addEventListener('change', () => {
    const code = opSel.value.split(' ')[0];
    const cfg = ops[code];
    opPreview.textContent = cfg
      ? (cfg.severity==='critique'?'🔴 Critique':cfg.severity==='attention'?'🟡 Attention':'🟢 '+cfg.category)
      : '';
  });
  // Déclencher preview si pré-rempli
  if (prefill && prefill.operation) {
    const m = prefill.operation.match(/^(\d+)/);
    const code = (m && m[1]) ? m[1] : null;
    const cfg = code && ops[code];
    if (cfg) opPreview.textContent = cfg.severity==='critique'?'🔴 Critique':cfg.severity==='attention'?'🟡 Attention':'🟢 '+cfg.category;
  }
 
  // Opérateur
  let opField;
  if (isAdmin(S.user)) {
    opField = h('select', null,
      h('option', { value: '' }, '— Choisir —'),
      ...ops_list.map(o => {
        const opt = h('option', { value: o }, opName(o));
        if (o === ((prefill && prefill.operateur) ? prefill.operateur : '')) opt.selected = true;
        return opt;
      })
    );
  } else {
    // Pour fabrication: utiliser nom si operateur_lie n'est pas défini
    const userOp = (S.user && (S.user.operateur_lie || S.user.nom)) || '';
    opField = h('input', { type: 'text', value: userOp });
    opField.disabled = true;
  }
 
  // Date 24h
  const { wrapper: dateWrapper, getVal: getDateVal } = makeDateTimeFields((prefill && prefill.date_operation) ? prefill.date_operation : '');
 
  const machI  = h('input', { type: 'text', placeholder: 'ex: 1 - COHESIO 1', value: (prefill && prefill.machine) ? prefill.machine : '' });
  const dosI   = h('input', { type: 'text', placeholder: 'ex: 1060',           value: (prefill && prefill.no_dossier) ? prefill.no_dossier : '' });
  const qteTI  = h('input', { type: 'number', placeholder: '0',                value: (prefill && prefill.quantite_traitee!=null)   ? prefill.quantite_traitee   : 0 });
  const noteI  = h('input', { type: 'text', placeholder: 'Raison (optionnel)',  value: '' });
  const commentaireI = h('input', { type: 'text', placeholder: 'Observation, remarque...', value: (prefill && prefill.commentaire) ? prefill.commentaire : '' });
  const metrageReelI      = h('input', { type: 'number', placeholder: '0', value: (prefill && prefill.metrage_reel!=null)        ? prefill.metrage_reel        : '' });
  const metrageDebutI     = h('input', { type: 'number', placeholder: '0', value: (prefill && prefill.metrage_total_debut!=null) ? prefill.metrage_total_debut : '' });
  const metrageFinI       = h('input', { type: 'number', placeholder: '0', value: (prefill && prefill.metrage_total_fin!=null)   ? prefill.metrage_total_fin   : '' });
  inputs.metrage_reel         = metrageReelI;
  inputs.metrage_total_debut  = metrageDebutI;
  inputs.metrage_total_fin    = metrageFinI;
 
  const form = h('div', { className: 'add-row-form' },
      h('button',{type:'button',className:'add-row-close',title:'Fermer',onClick:(e)=>{e.stopPropagation();closeModal();}},'×'),
      // Header (sert aussi de zone "grab" pour déplacer la fenêtre)
      (title && typeof title === 'object' && title.nodeType)
        ? h('div',{className:'add-row-header'}, title)
        : (title && title.tagName)
          ? h('div',{className:'add-row-header'}, title)
          : h('div',{className:'add-row-header'}, h('h3', null, title)),
      h('div', { className: 'form-row' },
        h('div', null, h('label', null, 'Opération *'), opSel, opPreview),
        h('div', null, h('label', null, 'Opérateur *'), opField)
      ),
      h('div', { className: 'form-row' },
        h('div', null, h('label', null, 'Date & heure (JJ/MM/AAAA HH:MM:SS)'), dateWrapper),
        h('div', null, h('label', null, 'Machine'), machI)
      ),
      h('div', { className: 'form-row' },
        h('div', null, h('label', null, 'No Dossier'), dosI)
      ),
      h('div', { className: 'form-row' },
        h('div', null, h('label', null, 'Qté traitée'), qteTI),
        h('div', null, h('label', null, 'Note'), noteI)
      ),
      h('div', { className: 'form-row' },
        h('div', null,
          h('label', null, 'Métrage réel (m)'),
          metrageReelI
        )
      ),
      h('div', { className: 'form-row' },
        h('div', null,
          h('label', null, 'Compteur début (m)'),
          metrageDebutI
        ),
        h('div', null,
          h('label', null, 'Compteur fin (m)'),
          metrageFinI
        )
      ),
      h('div', { className: 'form-row' },
        h('div', { style:{ gridColumn:'span 2' } },
          h('label', null, 'Commentaire'),
          commentaireI
        )
      ),
      h('div', { className: 'form-actions' },
        extraBtn || h('div', null), // bouton gauche (ex: Supprimer)
        h('div', { style: { display:'flex', gap:'8px' } },
          h('button', { className: 'btn-ghost', onClick: closeModal }, 'Annuler'),
          h('button', { className: 'btn-sm', onClick: () => {
            const opVal = opSel.value;
            if (!opVal) { toast('Sélectionnez une opération', 'error'); return; }
            const opText = opVal.replace('           ', ' ');
            const dtVal = getDateVal();
            if(!dtVal){ toast('Heure invalide (format HH:MM:SS, 24h)', 'error'); return; }
            onSubmit({
              operation:          opText,
              operateur:          opField.value || '',
              date_operation:     dtVal,
              machine:            machI.value  || '',
              no_dossier:         dosI.value   || '',
              quantite_traitee:   parseFloat(qteTI.value) || 0,
              note:               noteI.value  || '',
              commentaire:       commentaireI.value || '',
              metrage_reel:         parseFloat((inputs.metrage_reel         && inputs.metrage_reel.value)         ? inputs.metrage_reel.value         : '') || null,
              metrage_total_debut:  parseFloat((inputs.metrage_total_debut  && inputs.metrage_total_debut.value)  ? inputs.metrage_total_debut.value  : '') || null,
              metrage_total_fin:    parseFloat((inputs.metrage_total_fin    && inputs.metrage_total_fin.value)    ? inputs.metrage_total_fin.value    : '') || null,
            });
          }}, submitLabel)
        )
      )
    )
  ;
  const modal = h('div', { className: 'add-row-modal', onClick: e => { if (e.target === modal) closeModal(); } }, form);
  modal._formEl = form;
  return modal;
}
 
function getVisibleSaisiesRowsForNav(){
  // Base : déjà filtré côté API (/api/saisies + filtres). Ici on applique seulement tri + enrichissements UI.
  const d = S.saisies;
  if(!d) return [];
  let rows = (d.rows || []).slice();
  // Reprend la logique UI (durées) si la fonction existe (ajoutée dans renderSaisies).
  try{
    if(typeof addDurations === 'function') rows = addDurations(rows);
  }catch(e){}
  if(S.sortState && S.sortState.col) rows = sortRows(rows, S.sortState.col, S.sortState.asc);
  return rows;
}

function attachSaisieNav(modal, currentId){
  // Ctrl+← / Ctrl+→ : naviguer sur la liste affichée (bouclage).
  const handler = (e)=>{
    if(!e || !e.ctrlKey) return;
    if(e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
    const list = getVisibleSaisiesRowsForNav();
    if(!list || !list.length) return;
    const idx = list.findIndex(r=>String(r.id)===String(currentId));
    if(idx < 0) return;
    e.preventDefault();
    e.stopPropagation();
    const nextIdx = (e.key === 'ArrowRight')
      ? ((idx + 1) % list.length)
      : ((idx - 1 + list.length) % list.length);
    const nxt = list[nextIdx];
    if(nxt) openEditModal(nxt);
  };
  // Éviter d'empiler des listeners si on remplace la modale.
  document.addEventListener('keydown', handler, true);
  modal._navKeyHandler = handler;
}

function attachModalDrag(modal){
  const form = modal && modal._formEl ? modal._formEl : (modal ? modal.querySelector('.add-row-form') : null);
  if(!form) return;
  // Appliquer la dernière position (si l'utilisateur a déjà déplacé la fenêtre)
  try{
    if(S && S._saisieModalPos && isFinite(S._saisieModalPos.left) && isFinite(S._saisieModalPos.top)){
      form.style.position = 'fixed';
      form.style.margin = '0';
      form.style.left = S._saisieModalPos.left + 'px';
      form.style.top  = S._saisieModalPos.top + 'px';
      form.style.transform = 'none';
    }
  }catch(e){}
  let dragging = false;
  let sx = 0, sy = 0, startLeft = 0, startTop = 0;
  const onMove = (e)=>{
    if(!dragging) return;
    const dx = e.clientX - sx;
    const dy = e.clientY - sy;
    const left = (startLeft + dx);
    const top  = (startTop  + dy);
    form.style.left = left + 'px';
    form.style.top  = top  + 'px';
    try{ S._saisieModalPos = { left, top }; }catch(_){}
  };
  const onUp = ()=>{
    if(!dragging) return;
    dragging = false;
    document.removeEventListener('mousemove', onMove, true);
    document.removeEventListener('mouseup', onUp, true);
  };
  const onDown = (e)=>{
    // Drag uniquement si on clique sur une zone qui n'est pas un champ/bouton.
    const t = e.target;
    if(t && (t.closest && t.closest('input,select,textarea,button'))) return;
    // Laisser la sélection de texte dans un champ intacte.
    if(e.button !== 0) return;
    const r = form.getBoundingClientRect();
    // Passer en position fixe pour pouvoir bouger, sans dépendre du flex-center.
    form.style.position = 'fixed';
    form.style.margin = '0';
    form.style.left = r.left + 'px';
    form.style.top  = r.top  + 'px';
    form.style.transform = 'none';
    dragging = true;
    sx = e.clientX; sy = e.clientY;
    startLeft = r.left; startTop = r.top;
    try{ S._saisieModalPos = { left: startLeft, top: startTop }; }catch(_){}
    document.addEventListener('mousemove', onMove, true);
    document.addEventListener('mouseup', onUp, true);
    e.preventDefault();
  };
  form.addEventListener('mousedown', onDown, true);
  modal._dragDownHandler = onDown;
  modal._dragMoveHandler = onMove;
  modal._dragUpHandler = onUp;
}
 
function closeModal() {
  try{
    const m = document.querySelector('.add-row-modal');
    if(m && m._navKeyHandler){
      try{ document.removeEventListener('keydown', m._navKeyHandler, true); }catch(e){}
    }
    if(m && m._dragDownHandler){
      try{
        const form = m._formEl || m.querySelector('.add-row-form');
        if(form) form.removeEventListener('mousedown', m._dragDownHandler, true);
      }catch(e){}
      try{ document.removeEventListener('mousemove', m._dragMoveHandler, true); }catch(e){}
      try{ document.removeEventListener('mouseup', m._dragUpHandler, true); }catch(e){}
    }
    if(m) m.remove();
  }catch(e){}
}
 
function openAddModal(templateRow) {
  try{
    const m = document.querySelector('.add-row-modal');
    if(m) m.remove();
  }catch(e){}
  const modal = buildSaisieForm(
    templateRow,
    '➕ Ajouter une saisie',
    '✓ Ajouter',
    async (body) => { await addSaisie(body); }
  );
  document.getElementById('root').appendChild(modal);
}
 
function openEditModal(row) {
  try{
    const m = document.querySelector('.add-row-modal');
    if(m) m.remove();
  }catch(e){}
 
  const list = getVisibleSaisiesRowsForNav();
  const total = list.length || 0;
  const curIdx0 = total ? list.findIndex(r=>String(r.id)===String(row.id)) : -1;
  const idx = (curIdx0>=0) ? (curIdx0 + 1) : 0;
  const prevRow = (total && curIdx0>=0) ? list[(curIdx0 - 1 + total) % total] : null;
  const nextRow = (total && curIdx0>=0) ? list[(curIdx0 + 1) % total] : null;

  const counter = h('span',{className:'add-row-counter',title:'Ctrl+← / Ctrl+→'},
    h('button',{type:'button',className:'add-row-nav-btn',title:'Précédente (Ctrl+←)',onClick:(e)=>{e.stopPropagation(); if(prevRow) openEditModal(prevRow);}},'‹'),
    h('span',null,(idx>0?String(idx):'—')+'/'+String(total)),
    h('button',{type:'button',className:'add-row-nav-btn',title:'Suivante (Ctrl+→)',onClick:(e)=>{e.stopPropagation(); if(nextRow) openEditModal(nextRow);}},'›')
  );
  const titleNode = h('div',{style:{display:'flex',alignItems:'center',justifyContent:'space-between',gap:'12px',width:'100%'}},
    h('h3',null,'Modifier la saisie'),
    counter
  );
 
  const deleteBtn = h('button', {
    className: 'btn-danger',
    onClick: async e => {
      e.stopPropagation();
      if (!confirm('Supprimer cette saisie ?')) return;
      pushUndo('delete', row);  // ← ajouter cette ligne
      try {
        await api('/api/saisies/' + row.id, { method: 'DELETE' });
        toast('Saisie supprimée');
        await loadSaisies();
      } catch(err) { 
        undoStack.pop(); // annuler le pushUndo si l'API échoue
        toast(err.message, 'error'); 
      }
    }
  }, iconEl('trash',13),' Supprimer');
 
  const modal = buildSaisieForm(
    row,
    titleNode,
    'Enregistrer',
    async (body) => {
      pushUndo('edit', row);  //
      try {
        await api('/api/saisies/' + row.id, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
        toast('Saisie modifiée');
        await loadSaisies();
      } catch(e) { toast(e.message, 'error'); }
    },
    deleteBtn
  );
  attachSaisieNav(modal, row.id);
  attachModalDrag(modal);
  document.getElementById('root').appendChild(modal);
}

// ── Saisies ─────────────────────────────────────────────────────
function makeEditable(row,field,displayVal){
  const td=h('td',{className:'editable'});
  td.appendChild(h('span',null,displayVal||'-'));
  td.addEventListener('click',()=>{
    if(td.classList.contains('editing'))return;
    td.classList.add('editing');td.innerHTML='';
    const inp=h('input',{type:'text',value:row[field]||''});
    td.appendChild(inp);inp.focus();inp.select();
    const save=()=>{const val=inp.value;td.classList.remove('editing');td.innerHTML='';td.appendChild(h('span',null,val||'-'));if(val!==String(row[field]||''))saveSaisie(row.id,field,val);};
    inp.addEventListener('blur',save);
    inp.addEventListener('keydown',e=>{if(e.key==='Enter')inp.blur();if(e.key==='Escape'){td.classList.remove('editing');td.innerHTML='';td.appendChild(h('span',null,displayVal||'-'));}});
  });
  return td;
}

// Commentaire — éditable inline (spécifique pour éviter les modifs autres champs)
function makeEditableComment(row){
  const td=h('td',{className:'editable',style:{maxWidth:'220px',minWidth:'120px'}});
  const span=h('span',{style:{color:'var(--muted)',fontStyle:'italic'}},row.commentaire||'—');
  td.appendChild(span);
  td.addEventListener('click',e=>{
    e.stopPropagation(); // ne pas ouvrir le modal modification
    if(td.classList.contains('editing'))return;
    td.classList.add('editing');td.innerHTML='';
    const inp=h('input',{type:'text',value:row.commentaire||'',placeholder:'Ajouter un commentaire...'});
    td.appendChild(inp);inp.focus();inp.select();
    const save=()=>{
      const val=inp.value;
      td.classList.remove('editing');td.innerHTML='';
      td.appendChild(h('span',{style:{color:'var(--muted)',fontStyle:'italic'}},val||'—'));
      const old=(row.commentaire||'');
      if(val!==old) saveSaisie(row.id,'commentaire',val);
      // Mettre à jour l'objet local pour que la prochaine édition reflète la valeur
      row.commentaire = val;
    };
    inp.addEventListener('blur',save);
    inp.addEventListener('keydown',e=>{
      if(e.key==='Enter')inp.blur();
      if(e.key==='Escape'){
        td.classList.remove('editing');
        td.innerHTML='';
        td.appendChild(h('span',{style:{color:'var(--muted)',fontStyle:'italic'}},row.commentaire||'—'));
      }
    });
  });
  return td;
}


// Codes sans dossier ni quantité
const CODES_PERSONNEL = new Set(['86','87']);
// Seul code avec quantité
const CODE_FIN_DOS = '89';
 
// ── Masquage champs selon opération dans le modal ───────────────
function applyOpRules(opCode, form){
  const isPers  = CODES_PERSONNEL.has(opCode);
  const isFin   = opCode === CODE_FIN_DOS;
  const fields  = ['no_dossier','quantite_a_traiter','quantite_traitee'];
  fields.forEach(f=>{
    const row = form.querySelector('[data-field="'+f+'"]');
    if(!row) return;
    if(isPers){
      row.style.display='none';
    } else if(!isFin && (f==='quantite_a_traiter'||f==='quantite_traitee')){
      row.style.opacity='.4';
      row.querySelector('input').disabled=true;
      row.querySelector('input').value='0';
    } else {
      row.style.display='';row.style.opacity='';
      if(row.querySelector('input')) row.querySelector('input').disabled=false;
    }
  });
}
 
// ── Tri tableau ─────────────────────────────────────────────────
function sortRows(rows, col, asc){
  return [...rows].sort((a,b)=>{
    let va=a[col]||'', vb=b[col]||'';
    if(typeof va==='number'||!isNaN(va)) {va=parseFloat(va)||0; vb=parseFloat(vb)||0;}
    if(va<vb)return asc?-1:1;
    if(va>vb)return asc?1:-1;
    return 0;
  });
}
 
// ── Suppression groupée ─────────────────────────────────────────
async function bulkDelete(){
  const ids=[...S.selectedRows];
  if(!ids.length) return;
  if(!confirm('Supprimer '+ids.length+' saisie(s) ?')) return;
 
  // Sauvegarder pour undo
  const snaps=(((S.saisies && S.saisies.rows) ? S.saisies.rows : [])).filter(r=>ids.includes(r.id));
  snaps.forEach(row=>pushUndo('delete',row));
 
  try{
    const r=await api('/api/saisies/bulk',{method:'DELETE',headers:{'Content-Type':'application/json'},body:JSON.stringify({ids})});
    if(!r)return;
    toast(r.deleted+' saisie(s) supprimée(s)');
    S.selectedRows=new Set();
    await loadSaisies();
  }catch(e){
    // Annuler les pushUndo si erreur
    snaps.forEach(()=>undoStack.pop());
    toast(e.message,'error');
  }
}

const SAISIE_FICTIF_PREFIX = 'FICTIF:';
function isFictifDossierRef(ref){
  if(!ref) return false;
  return String(ref).trim().toUpperCase().startsWith(SAISIE_FICTIF_PREFIX);
}
function isFictifSaisieRow(row){
  if(!row) return false;
  return isFictifDossierRef(row.no_dossier) || isFictifDossierRef(row.reference);
}

function fictifOfDisplay(ref){
  const s=String(ref||'').trim();
  if(isFictifDossierRef(s)) return s.slice(SAISIE_FICTIF_PREFIX.length);
  return s;
}

async function openFictifReassignModal(){
  if(isFab(S.user)) return;
  try{
    const m=document.querySelector('.add-row-modal');
    if(m) m.remove();
  }catch(e){}
  const sources=await api('/api/saisies/reassign/fictif-sources')||[];
  const fromSel=h('select',{className:'form-sel',style:{width:'100%'}},
    h('option',{value:''},'— Choisir un dossier fictif —'),
    ...sources.map(s=>{
      const opt=h('option',{value:s.no_dossier},
        'OF fictif '+fictifOfDisplay(s.no_dossier)+' ('+s.nb_saisies+' saisie'+(s.nb_saisies>1?'s':'')+')');
      return opt;
    })
  );
  const toInp=h('input',{type:'text',className:'form-sel',style:{width:'100%'},
    placeholder:'N° dossier planning (référence ou OF)…'});
  const sugWrap=h('div',{className:'fictif-reassign-suggest'});
  let sugTok=0;
  const refreshSug=async()=>{
    const q=String(toInp.value||'').trim();
    const tok=++sugTok;
    if(q.length<1){ sugWrap.innerHTML=''; return; }
    const sugs=await api('/api/saisies/reassign/target-dossiers?q='+encodeURIComponent(q)+'&limit=12')||[];
    if(tok!==sugTok) return;
    sugWrap.innerHTML='';
    (sugs||[]).slice(0,10).forEach(d=>{
      const lbl=[d.no_dossier,d.client].filter(Boolean).join(' — ');
      const btn=h('button',{type:'button',onClick:()=>{ toInp.value=d.no_dossier; sugWrap.innerHTML=''; }},
        lbl+(d.statut?(' ['+d.statut+']'):''));
      sugWrap.appendChild(btn);
    });
  };
  toInp.addEventListener('input',()=>{ refreshSug(); });
  const msg=h('p',{style:{fontSize:'12px',color:'var(--muted)',margin:'0 0 12px',lineHeight:1.5}},
    'Toutes les saisies du dossier fictif seront rattachées au dossier réel choisi (production, matières traça, liens rentabilité).');
  const form=h('div',{className:'add-row-form',style:{minWidth:'min(480px,92vw)'}},
    h('button',{type:'button',className:'add-row-close',title:'Fermer',onClick:(e)=>{e.stopPropagation();closeModal();}},'×'),
    h('h3',{style:{marginBottom:'12px',color:'#a78bfa'}},iconEl('file-text',16),' Rattacher un dossier fictif'),
    msg,
    h('div',{className:'fd'},h('label',null,'Dossier fictif'),fromSel),
    h('div',{className:'fd',style:{marginTop:'14px'}},h('label',null,'Dossier réel existant'),toInp,sugWrap),
    h('div',{style:{display:'flex',gap:'8px',justifyContent:'flex-end',marginTop:'18px'}},
      h('button',{type:'button',className:'btn-ghost',onClick:()=>closeModal()},'Annuler'),
      h('button',{type:'button',className:'btn-fictif-sm',onClick:async()=>{
        const from=String(fromSel.value||'').trim();
        const to=String(toInp.value||'').trim();
        if(!from){ toast('Choisissez un dossier fictif','error'); return; }
        if(!to){ toast('Indiquez le dossier cible','error'); return; }
        if(!confirm('Rattacher « '+fictifOfDisplay(from)+' » → « '+to+' » ?\n\nToutes les saisies concernées seront modifiées.')) return;
        try{
          const r=await api('/api/saisies/reassign/fictif',{
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({from_no_dossier:from,to_no_dossier:to})
          });
          closeModal();
          toast((r.updated_saisies||0)+' saisie(s) rattachée(s) → '+r.to_no_dossier,'success');
          await loadFilters();
          await loadSaisies();
        }catch(err){ toast(err.message||'Rattachement impossible','error'); }
      }},'Rattacher')
    )
  );
  const modal=h('div',{className:'add-row-modal',onClick:e=>{if(e.target===modal)closeModal();}},form);
  document.getElementById('root').appendChild(modal);
  if(sources.length===1) fromSel.value=sources[0].no_dossier;
}
 
function renderSaisies(){
  const d=S.saisies;
  if(!d) return h('div',{className:'card-empty'},'Chargement...');
  // Pour fabrication: utiliser nom si operateur_lie n'est pas défini
  const userOperateur = (S.user && (S.user.operateur_lie || S.user.nom)) || '';
  if(!canViewAllProd(S.user) && !userOperateur)
    return h('div',{className:'card'},h('div',{className:'card-blocked'},h('div',{className:'cb-icon'},iconEl('lock',32)),h('div',{className:'cb-msg'},'Compte non lié à un opérateur.')));
 
  const readOnly=isFab(S.user);
 
  function fmtDurMin(m){
    if(m==null||!isFinite(m)||m<=0) return '-';
    const mm = Math.round(Number(m));
    if(mm < 60) return mm+' min';
    const hh = Math.floor(mm/60);
    const rm = mm%60;
    return hh+' h '+String(rm).padStart(2,'0')+' min';
  }

  function addDurations(baseRows){
    const rows = (baseRows||[]).slice();
    // Durée = écart avec la saisie suivante du même opérateur (en minutes)
    const byOp = new Map();
    rows.forEach(r=>{
      const k = String(r.operateur||'').trim();
      if(!byOp.has(k)) byOp.set(k, []);
      byOp.get(k).push(r);
    });
    byOp.forEach(list=>{
      list.sort((a,b)=>{
        const da = Date.parse(String(a.date_operation||'')) || 0;
        const db = Date.parse(String(b.date_operation||'')) || 0;
        if(da !== db) return da - db;
        return (Number(a.id)||0) - (Number(b.id)||0);
      });
      for(let i=0;i<list.length;i++){
        const cur = list[i];
        const nxt = list[i+1];
        let dur = null;
        if(nxt){
          const t1 = Date.parse(String(cur.date_operation||'')) || NaN;
          const t2 = Date.parse(String(nxt.date_operation||'')) || NaN;
          if(isFinite(t1) && isFinite(t2) && t2 >= t1){
            const m = Math.round((t2 - t1)/60000);
            // Filtre anti-absurde (ex: oubli badgeage) : > 12h => on masque
            dur = (m > 0 && m <= 12*60) ? m : null;
          }
        }
        cur.duree_min = dur;
      }
    });
    return rows;
  }
 
  // ── Tri ──────────────────────────────────────────────────────
  let rows=addDurations(d.rows||[]);
  if(S.sortState.col) rows=sortRows(rows,S.sortState.col,S.sortState.asc);

  // ── Calcul métrage dossier (Fin dossier = compteur fin - compteur début) ──
  // Priorité aux colonnes dédiées metrage_total_debut / metrage_total_fin.
  // Fallback sur metrage_prevu / metrage_reel pour les anciennes lignes sans compteurs.
  (function(){
    const debutByDossier = {}; // no_dossier → compteur début (metrage_total_debut ?? metrage_prevu)
    const chrono = [...rows].sort((a,b)=>(a.date_operation||'').localeCompare(b.date_operation||''));
    chrono.forEach(r=>{
      if(r.operation_code==='01' && r.no_dossier){
        const ctr = r.metrage_total_debut ?? r.metrage_prevu;
        if(ctr!=null) debutByDossier[r.no_dossier] = parseFloat(ctr);
      }
      if(r.operation_code==='89' && r.no_dossier){
        const finCtr  = r.metrage_total_fin ?? null;   // compteur fin uniquement
        const debutCtr = debutByDossier[r.no_dossier] ?? null;
        if(finCtr!=null && debutCtr!=null){
          r._metrage_dossier = parseFloat(finCtr) - debutCtr;  // fin_counter − debut_counter
        } else if(r.metrage_reel!=null && debutCtr!=null && !r.metrage_total_fin){
          // Ancien format : metrage_reel était le compteur fin (avant introduction des nouvelles colonnes)
          r._metrage_dossier = parseFloat(r.metrage_reel) - debutCtr;
        }
        // Si metrage_total_fin absent et metrage_reel = valeur directe produite : pas de calcul
      }
    });
  })();

  const COLS=[
    {key:'date_operation',  label:'Date'},
    {key:'operation',       label:'Opération'},
    {key:'duree_min',       label:'Durée'},
    {key:'operateur',       label:'Opérateur'},
    {key:'machine',         label:'Machine'},
    {key:'no_dossier',      label:'Dossier'},
    {key:'quantite_traitee',   label:'Qté traitée'},
    {key:'metrage_reel',    label:'Métrage (m)'},
    {key:'commentaire',     label:'Commentaire'},
    {key:'_badge',          label:''},
  ];
 
  // ── Header avec tri ──────────────────────────────────────────
  const ths=COLS.map(col=>{
    if(col.key==='_badge') return h('th',null,'');
    const isSorted=S.sortState.col===col.key;
    const arrow=isSorted?(S.sortState.asc?' ↑':' ↓'):'';
    const th=h('th',{style:{cursor:'pointer',userSelect:'none',whiteSpace:'nowrap'}},col.label+arrow);
    th.addEventListener('click',()=>{
      if(S.sortState.col===col.key){S.sortState.asc=!S.sortState.asc;}
      else{S.sortState={col:col.key,asc:true};}
      render();
    });
    return th;
  });
 
  // ── Checkbox "tout sélectionner" ─────────────────────────────
  const allIds=rows.map(r=>r.id);
  const allChecked=allIds.length>0&&allIds.every(id=>S.selectedRows.has(id));
  const chkAll=h('input',{type:'checkbox'});
  chkAll.checked=allChecked;
  chkAll.addEventListener('change',()=>{
    if(chkAll.checked) allIds.forEach(id=>S.selectedRows.add(id));
    else S.selectedRows.clear();
    render();
  });
  const thChk=h('th',null,chkAll);
  ths.unshift(thChk);
 
  const tbody=h('tbody',null);
 
  rows.forEach(row=>{
    const fictifRow = isFictifSaisieRow(row);
    const tr=h('tr',{className:'data-row'+(fictifRow?' saisie-row-fictif':''),style:{cursor:readOnly?'default':'pointer'}});
    // PAR — contrastes plus forts + catégorie production en vert
    const opCode = row.operation_code || '';
    const cat    = row.operation_category || '';

    let rowBg = '';
    if (fictifRow) {
      rowBg = 'rgba(167,139,250,.10)';          // dossier fictif (FICTIF:)
    } else if (row.operation_severity === 'critique') {
      rowBg = 'rgba(248,113,113,.18)';          // rouge soutenu
    } else if (row.operation_severity === 'attention') {
      rowBg = 'rgba(251,191,36,.18)';           // jaune soutenu
    } else if (cat === 'production' || opCode === '03' || opCode === '88') {
      rowBg = 'rgba(52,211,153,.12)';           // vert production
    } else if (cat === 'personnel' || opCode === '86' || opCode === '87') {
      rowBg = 'rgba(167,139,250,.10)';          // violet discret arrivée/départ
    } else if (cat === 'calage' || opCode === '02') {
      rowBg = 'rgba(251,191,36,.08)';           // jaune doux calage
    }
    if (rowBg) tr.style.background = rowBg;
    if (S.selectedRows.has(row.id)) tr.style.background = 'rgba(34,211,238,.12)';
 
    if(!readOnly) tr.addEventListener('click',()=>openEditModal(row));
 
    // Checkbox ligne
    const chk=h('input',{type:'checkbox'});
    chk.checked=S.selectedRows.has(row.id);
    chk.addEventListener('click',e=>e.stopPropagation());
    chk.addEventListener('change',()=>{
      if(chk.checked) S.selectedRows.add(row.id);
      else S.selectedRows.delete(row.id);
      render();
    });
    const tdChk=h('td',null,chk);
    tdChk.addEventListener('click',e=>e.stopPropagation());
    tr.appendChild(tdChk);
 
    let badge=null;
    if(row.est_manuel) badge=h('span',{className:'badge-manuel'},'+ Manuel');
    else if(row.modifie_par) badge=h('span',{className:'badge-modif',title:'Modifié par '+row.modifie_par+' le '+fD(row.modifie_le)},'✏ Corrigé');
 
    tr.appendChild(h('td',{style:{fontSize:'11px',color:'var(--muted)',whiteSpace:'nowrap',fontFamily:'monospace'}},fDSecs(row.date_operation)));
    tr.appendChild(h('td',null,row.operation||'-'));
    tr.appendChild(h('td',{style:{whiteSpace:'nowrap',color:'var(--muted)'}},fmtDurMin(row.duree_min)));
    tr.appendChild(h('td',null,opName(row.operateur)));
    tr.appendChild(h('td',null,row.machine||'-'));
    tr.appendChild(h('td',null,row.no_dossier||'-'));
    tr.appendChild(h('td',null,fN(row.quantite_traitee)));
    tr.appendChild(h('td',{style:{color:'var(--c3)'}},
      row._metrage_dossier!=null
        ? (()=>{
            const finCtr   = row.metrage_total_fin   ?? row.metrage_reel;
            const debutCtr = row.metrage_total_debut != null
              ? row.metrage_total_debut
              : (finCtr!=null ? finCtr - row._metrage_dossier : null);
            const tip = 'Métrage produit = compteur fin − compteur début'
              + (finCtr!=null   ? '\nFin : '+fN(finCtr)+' m'   : '')
              + (debutCtr!=null ? '\nDébut : '+fN(debutCtr)+' m' : '');
            return h('span',{title:tip},'⇒ '+fN(row._metrage_dossier)+' m');
          })()
        : row.metrage_total_fin!=null   ? fN(row.metrage_total_fin)+' m (cpt fin)'
        : row.metrage_reel!=null        ? fN(row.metrage_reel)+' m'
        : row.metrage_total_debut!=null ? h('span',{style:{color:'var(--muted)',fontSize:'11px'}},fN(row.metrage_total_debut)+' m (déb.)')
        : row.metrage_prevu!=null       ? h('span',{style:{color:'var(--muted)',fontSize:'11px'}},fN(row.metrage_prevu)+' m (déb.)')
        : '-'));
    if(readOnly){
      tr.appendChild(h('td',{style:{maxWidth:'200px',overflow:'hidden',textOverflow:'ellipsis'}},row.commentaire||''));
    }else{
      tr.appendChild(makeEditableComment(row));
    }
    tr.appendChild(h('td',null,badge));
 
    if(!readOnly){
      const addBtn=h('button',{className:'add-row-btn',title:'Insérer une ligne après',onClick:e=>{e.stopPropagation();openAddModal(row);}},'+');
      const delBtn=h('button',{className:'add-row-btn',title:'Supprimer cette ligne',
        style:{left:'calc(50% + 18px)',background:'var(--danger)',borderColor:'var(--bg)'},
        onClick:async e=>{
          e.stopPropagation();
          if(!confirm('Supprimer cette saisie ?'))return;
          pushUndo('delete',row);
          try{
            await api('/api/saisies/'+row.id,{method:'DELETE'});
            toast('Saisie supprimée');await loadSaisies();
          }catch(err){undoStack.pop();toast(err.message,'error');}
        }
      },'−');
      const firstTd=tr.querySelector('td:nth-child(2)');
      if(firstTd){firstTd.style.position='relative';firstTd.appendChild(addBtn);firstTd.appendChild(delBtn);}
    }
    tbody.appendChild(tr);
  });
 
  // ── Barre d'actions ──────────────────────────────────────────
  const selCount=S.selectedRows.size;
  const headerRight=h('div',{style:{display:'flex',gap:'8px',alignItems:'center',flexWrap:'wrap'}});

  // Pagination (offset/limit) : évite de scroller toute la page
  const total = Number(d.total||0);
  const off = Number(S.saisiesOffset||0);
  const lim = Number(S.saisiesLimit||200);
  const from = total ? Math.min(total, off+1) : 0;
  const to = total ? Math.min(total, off + (rows||[]).length) : 0;
  const pager = h('div',{style:{display:'inline-flex',alignItems:'center',gap:'6px'}},
    h('button',{className:'btn-ghost',title:'Page précédente',disabled:off<=0,onClick:async()=>{
      const n = Math.max(0, off - lim);
      await loadSaisies({offset:n,limit:lim});
      render();
    }},'‹'),
    h('span',{style:{fontSize:'11px',color:'var(--muted)',fontFamily:'monospace'}}, total?(`${from}-${to}/${total}`):'0'),
    h('button',{className:'btn-ghost',title:'Page suivante',disabled:(off+lim)>=total,onClick:async()=>{
      const n = Math.min(Math.max(0,total-lim), off + lim);
      await loadSaisies({offset:n,limit:lim});
      render();
    }},'›'),
  );
  headerRight.appendChild(pager);
 
  if(readOnly){
    headerRight.appendChild(h('span',{className:'readonly-notice'},iconEl('eye',13),' Lecture seule'));
  }else{
    const btnUndo=h('button',{id:'btn-undo',className:'btn-ghost',title:'Annuler ('+undoStack.length+')',onClick:doUndo},iconEl('rotate-ccw',13),' Annuler ('+undoStack.length+')');
    if(undoStack.length===0) btnUndo.setAttribute('disabled','true');
    const btnRedo=h('button',{id:'btn-redo',className:'btn-ghost',title:'Rétablir ('+redoStack.length+')',onClick:doRedo},iconEl('rotate-cw',13),' Rétablir ('+redoStack.length+')');
    if(redoStack.length===0) btnRedo.setAttribute('disabled','true');
 
    headerRight.appendChild(btnUndo);
    headerRight.appendChild(btnRedo);
 
    if(selCount>0){
      headerRight.appendChild(h('button',{className:'btn-danger',onClick:bulkDelete},iconEl('trash',13),' Supprimer ('+selCount+')'));
    }
    headerRight.appendChild(h('button',{className:'btn-sm',onClick:()=>openAddModal(rows[rows.length-1]||null)},iconEl('plus',13),' Ajouter'));
    headerRight.appendChild(h('button',{className:'btn-fictif-sm',onClick:()=>openFictifReassignModal()},iconEl('file-text',13),' Dossier fictif'));
    headerRight.appendChild(h('button',{className:'btn-ghost',onClick:()=>exportBlob('/api/saisies/export?'+buildParams(),'saisies.xlsx')},iconEl('download',13),' Export'));
  }
 
  return h('div',null,
    h('div',{className:'card'},
      h('div',{className:'card-header'},
        h('h3',null,'Saisies'),
        h('div',{style:{display:'flex',gap:'12px',alignItems:'center'}},
          headerRight
        )
      ),
      // Wrapper synchronisé : scrollbar miroir en haut ↔ bas
      (() => {
        const tableEl = h('table',null,
          h('thead',null,h('tr',null,...ths)),
          tbody
        );
        const bot = h('div',{className:'saisies-bot'},h('div',{style:{overflowX:'auto',paddingBottom:'4px'}},tableEl));
        const topInner = h('div',{style:{height:'1px',width:tableEl.scrollWidth+'px'}});
        const top = h('div',{style:{overflowX:'auto',height:'10px',marginBottom:'0'}},topInner);
        // Synchronisation scroll
        const botX = bot.firstChild;
        top.addEventListener('scroll',()=>{ botX.scrollLeft = top.scrollLeft; });
        botX.addEventListener('scroll',()=>{ top.scrollLeft = botX.scrollLeft; });
        // Mettre à jour la largeur fantôme après rendu
        requestAnimationFrame(()=>{
          topInner.style.width = tableEl.offsetWidth+'px';
        });
        return h('div',{className:'saisies-table-wrap'},top,bot);
      })()
    )
  );
}

// ── Saisies + Import intégré ─────────────────────────────────────
function renderSaisiesWithImport(){
  const admin = isAdmin(S.user);
  const parts = [];

  if(admin){
    const isOpen = !!S.importOpen;
    const header = h('div',{
      className:'card-header',
      style:{cursor:'pointer'},
      onClick:()=>{S.importOpen=!S.importOpen;render();}
    },
      h('h3',null,'⬆ Importer des saisies (CSV / Excel)'),
      h('span',{style:{fontSize:'12px',color:'var(--muted)'}},isOpen?'▲ Masquer':'▼ Afficher')
    );

    if(isOpen){
      const zone=h('div',{className:'drop-zone'},
        h('div',{className:'dz-icon'},iconEl('cloud-upload',36)),
        h('div',{className:'dz-title'},'Glisser un fichier ici'),
        h('div',{className:'dz-sub'},'CSV, Excel (.xlsx, .xls, .xlsm) — ou cliquer pour parcourir')
      );
      const inp=h('input',{type:'file',accept:'.csv,.xlsx,.xls,.xlsm',style:{display:'none'}});
      inp.addEventListener('change',e=>{if(e.target.files[0])upload(e.target.files[0]);});
      zone.addEventListener('click',()=>inp.click());
      zone.addEventListener('dragover',e=>{e.preventDefault();zone.classList.add('drag');});
      zone.addEventListener('dragleave',()=>zone.classList.remove('drag'));
      zone.addEventListener('drop',e=>{
        e.preventDefault();zone.classList.remove('drag');
        const f=e.dataTransfer.files[0];if(f)upload(f);
      });
      parts.push(h('div',{className:'card',style:{marginBottom:'16px'}},
        header,
        h('div',{style:{padding:'0 20px 20px'}}, zone, inp)
      ));
    } else {
      parts.push(h('div',{className:'card',style:{marginBottom:'16px'}}, header));
    }
  }

  parts.push(renderSaisies());
  return h('div',null,...parts);
}

// ── Import ──────────────────────────────────────────────────────
function renderImport(){
  const zone=h('div',{className:'drop-zone'},h('div',{className:'dz-icon'},iconEl('cloud-upload',36)),h('div',{className:'dz-title'},'Glisser un fichier ici'),h('div',{className:'dz-sub'},'CSV, Excel (.xlsx, .xls, .xlsm) — ou cliquer pour parcourir'));
  const inp=h('input',{type:'file',accept:'.csv,.xlsx,.xls,.xlsm',style:{display:'none'}});
  inp.addEventListener('change',e=>{if(e.target.files[0])upload(e.target.files[0]);});
  zone.addEventListener('click',()=>inp.click());zone.addEventListener('dragover',e=>{e.preventDefault();zone.classList.add('drag');});zone.addEventListener('dragleave',()=>zone.classList.remove('drag'));
  zone.addEventListener('drop',e=>{e.preventDefault();zone.classList.remove('drag');if(e.dataTransfer.files[0])upload(e.dataTransfer.files[0]);});
  zone.appendChild(inp);
  const list=h('div',{className:'card'},h('div',{className:'card-header'},h('h3',null,'Historique des imports ('+S.imports.length+')')),
    S.imports.length===0?h('div',{className:'card-empty'},'Aucun import encore'):
    h('div',null,...S.imports.map(i=>h('div',{className:'import-row'},
      h('div',{style:{flex:1}},h('div',{style:{fontSize:'14px',fontWeight:'500',color:'var(--text)'}},i.filename),h('div',{style:{fontSize:'11px',color:'var(--muted)',fontFamily:'monospace',marginTop:'2px'}},(i.imported_at||'').slice(0,16).replace('T',' ')+'  —  '+i.row_count+' lignes')),
      h('div',{style:{display:'flex',gap:'8px'}},h('button',{className:'btn-ghost',onClick:()=>exportBlob('/api/imports/'+i.id+'/export',i.filename.replace(/\.[^.]+$/,'')+'_export.xlsx')},iconEl('download',13),' Export'),h('button',{className:'btn-danger',onClick:()=>deleteImport(i.id,i.filename)},iconEl('trash',13),' Supprimer'))
    )))
  );
  return h('div',null,zone,list);
}

// ── Dossiers ────────────────────────────────────────────────────
function renderDos(){
  const inputs={};
  const form=h('div',{className:'card',style:{padding:'20px'}},h('h3',{style:{fontSize:'14px',fontWeight:'600',marginBottom:'16px'}},'Nouveau dossier'),
    h('div',{className:'form-grid'},...Object.entries({reference:'Référence *',client:'Client',description:'Description',devis_montant:'Montant devis (€)'}).map(([k,l])=>{const i=h('input',{placeholder:l,type:k==='devis_montant'?'number':'text'});inputs[k]=i;return i;})),
    h('button',{className:'btn',onClick:()=>{if(!inputs.reference.value)return;createDos({reference:inputs.reference.value,client:inputs.client.value,description:inputs.description.value,devis_montant:parseFloat(inputs.devis_montant.value)||0});Object.values(inputs).forEach(i=>i.value='');}},'Créer')
  );
  const sC={devis:'var(--c4)',en_cours:'var(--c1)',termine:'var(--c3)',annule:'var(--c5)'};const sL={devis:'Devis',en_cours:'En cours',termine:'Terminé',annule:'Annulé'};
  const list=h('div',{className:'card'},h('div',{className:'card-header'},h('h3',null,'Dossiers ('+S.dossiers.length+')')),
    S.dossiers.length===0?h('div',{className:'card-empty'},'Aucun dossier'):
    h('div',null,...S.dossiers.map(d=>{
      const sel=h('select',null,...Object.entries(sL).map(([k,v])=>{const o=h('option',{value:k},v);if(k===d.statut)o.selected=true;return o;}));
      sel.addEventListener('change',e=>updStatut(d.id,e.target.value));
      return h('div',{className:'dossier-row'},h('div',null,h('div',{style:{display:'flex',gap:'8px',alignItems:'center',marginBottom:'4px'}},h('span',{style:{fontFamily:'monospace',fontWeight:'600',fontSize:'14px'}},d.reference),h('span',{style:{fontSize:'11px',padding:'2px 10px',borderRadius:'20px',fontWeight:'600',background:(sC[d.statut]||'var(--muted)')+'22',color:sC[d.statut]||'var(--muted)'}},sL[d.statut]||d.statut)),h('div',{style:{fontSize:'13px',color:'var(--text2)'}},[d.client,d.description].filter(Boolean).join(' — '))),h('div',{style:{display:'flex',gap:'12px',alignItems:'center'}},d.devis_montant>0?h('span',{style:{fontFamily:'monospace',fontSize:'14px',color:'var(--success)',fontWeight:'600'}},d.devis_montant.toLocaleString()+' €'):null,sel));
    }))
  );
  return h('div',null,form,list);
}

// ── Import OF PDF ────────────────────────────────────────────────
function canAccessOfTab(){
  return isAdmin(S.user);
}
function prodOfFmtDate(iso){
  if(!iso) return '—';
  const d=String(iso).slice(0,10);
  const m=d.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  return m ? m[3]+'/'+m[2]+'/'+m[1] : d;
}
const OF_FIELD_LABELS={
  of_numero:'OF n°',date_creation:'Date création',delai_client:'Délai client',
  reference:'Référence',machine:'Machine',laize:'Laize',format:'Format',
  matiere:'Matière',ref_matiere:'Réf. matière',glassine:'Glassine',
  ref_adhesif:'Réf. adhésif',qte_adhesif_g:'Qté adhésif (g)',qte_adhesif_kg:'Qté adhésif (kg)',
  adhesif_label:'Adhésif',qte_au_mille:'Quantité au mille',nb_levees:'Nb levées',
  qte_etiquettes:'Qté étiquettes',qte_bobines:'Qté bobines',metrage:'Métrage',
  conditionnement:'Conditionnement',tolerance:'Tolérance',cartons_type:'Type cartons',
  nb_cartons:'Nb cartons',mandrins_dia:'Mandrins dia.',mandrin_longueur:'Mandrin long.',
  nb_mandrins:'Nb mandrins',nb_tubes:'Nb tubes',bobinettes_completes:'Bobinettes complètes',
  outil_1_forme:'Outil 1 — forme',outil_1_numero:'Outil 1 — n°',outil_1_angle:'Outil 1 — angle',
  outil_1_mag:'Outil 1 — mag.',outil_1_cp:'Outil 1 — CP',outil_1_hauteur:'Outil 1 — hauteur',
  outil_1_fournisseur:'Outil 1 — fournisseur',outil_2_forme:'Outil 2 — forme',
  outil_2_numero:'Outil 2 — n°',outil_2_angle:'Outil 2 — angle',outil_2_cp:'Outil 2 — CP',
  outil_alt_forme:'Outil alt. — forme',outil_alt_numero:'Outil alt. — n°',
  outil_alt_angle:'Outil alt. — angle',outil_alt_fournisseur:'Outil alt. — fournisseur',
};
function prodOfStatutLabel(st){
  const m={en_attente:'En attente',valide:'Validé',rejete:'Rejeté'};
  return m[st]||st||'—';
}
function prodOfStatutClass(st){
  if(st==='valide') return 'prod-of-statut prod-of-statut--valide';
  if(st==='rejete') return 'prod-of-statut prod-of-statut--rejete';
  return 'prod-of-statut prod-of-statut--attente';
}
async function loadOfImports(){
  set({ofImportsLoading:true});
  try{
    const q=encodeURIComponent(S.ofSearch||'');
    const offset=(S.ofPage||0)*50;
    const url='/api/of/list?limit=50&offset='+offset+(q?'&q='+q:'');
    const data=await api(url);
    set({
      ofImports: Array.isArray(data.rows)?data.rows:[],
      ofTotal:   data.total||0,
      ofImportsLoading:false,
    });
  }catch(e){
    set({ofImportsLoading:false});
    toast(e.message||'Erreur chargement des OF','error');
  }
}

async function loadFiches(){
  set({fichesLoading:true});
  try{
    const q=encodeURIComponent(S.ficheSearch||'');
    const offset=(S.fichePage||0)*50;
    const url='/api/fiches-techniques/list?limit=50&offset='+offset+(q?'&q='+q:'');
    const data=await api(url);
    set({fiches:Array.isArray(data.rows)?data.rows:[],ficheTotal:data.total||0,fichesLoading:false});
  }catch(e){
    set({fichesLoading:false});
    toast(e.message||'Erreur chargement fiches techniques','error');
  }
}
async function loadPendingOfCount(){
  try{
    const data=await api('/api/admin/of-link-pending/count');
    set({
      pendingOfCount:Number(data&&data.count||0),
      pendingOfAmbigus:Number(data&&data.ambigus||0),
      pendingOfSansOf:Number(data&&data.sans_of||0),
    });
  }catch(e){
    set({pendingOfCount:0,pendingOfAmbigus:0,pendingOfSansOf:0});
  }
}

async function loadPendingOfMappings(){
  set({pendingOfLoading:true});
  try{
    const data=await api('/api/admin/of-link-pending');
    set({
      pendingOfMappings:Array.isArray(data&&data.items)?data.items:[],
      pendingOfCount:Number(data&&data.total||0),
      pendingOfLoading:false,
    });
  }catch(e){
    set({pendingOfLoading:false});
    toast(e.message||'Erreur chargement mappings à valider','error');
  }
}

async function submitOfMapping(planningId, ofId){
  try{
    await api('/api/admin/link-planning-of',{
      method:'POST',
      body:JSON.stringify({planning_id:planningId, of_id:ofId}),
    });
    toast(ofId==null?'Planning délié.':'OF lié.');
    await loadPendingOfMappings();
    render();
  }catch(e){
    toast(e.message||'Erreur enregistrement','error');
  }
}
async function submitOfMappingMulti(planningId, ofIds){
  if(!ofIds || !ofIds.length){ toast('Aucun OF sélectionné.','error'); return; }
  try{
    const data=await api('/api/admin/planning-of-links',{
      method:'POST',
      body:JSON.stringify({planning_id:planningId, of_ids:ofIds}),
    });
    const added=Number(data&&data.added||0);
    const skip=Number(data&&data.skipped_existing||0);
    let msg='';
    if(added) msg=added+' OF lié'+(added>1?'s':'')+'.';
    if(skip)  msg+=(msg?' ':'')+skip+' déjà liés ignorés.';
    toast(msg||'Aucun changement.');
    await loadPendingOfMappings();
    await loadDossiersSansOf();
    loadPendingOfCount();
    render();
  }catch(e){
    toast(e.message||'Erreur enregistrement','error');
  }
}

async function loadDossiersSansOf(){
  set({dossiersSansOfLoading:true});
  try{
    const data=await api('/api/admin/dossiers-sans-of');
    set({
      dossiersSansOf:Array.isArray(data&&data.items)?data.items:[],
      dossiersSansOfLoading:false,
    });
  }catch(e){
    set({dossiersSansOfLoading:false});
    toast(e.message||'Erreur chargement dossiers sans OF','error');
  }
}

async function searchOfsForAttach(planningId, term){
  const key='attach-'+planningId;
  const inputId='attach-search-'+planningId;
  // Helpers focus : capture la position du caret avant chaque render,
  // restaure après. Évite l'inversion des caractères en saisie rapide.
  function captureFocus(){
    const ae=document.activeElement;
    if(ae && ae.id===inputId){
      return {focused:true, start:ae.selectionStart, end:ae.selectionEnd, value:ae.value};
    }
    return null;
  }
  function restoreFocus(snap){
    if(!snap||!snap.focused) return;
    requestAnimationFrame(()=>{
      const el=document.getElementById(inputId);
      if(!el) return;
      try{
        el.focus();
        if(snap.start!=null){
          const end=snap.end!=null?snap.end:snap.start;
          el.setSelectionRange(snap.start, end);
        }
      }catch(e){}
    });
  }
  let snap=captureFocus();
  S[key+'-loading']=true; render();
  restoreFocus(snap);
  try{
    const q=encodeURIComponent(term||'');
    const data=await api('/api/of/search?limit=20'+(q?'&q='+q:''));
    // Recapture juste avant le 2e render (l'utilisateur a pu taper pendant le fetch)
    snap=captureFocus()||snap;
    S[key+'-results']=Array.isArray(data&&data.items)?data.items:[];
    S[key+'-loading']=false;
    render();
    restoreFocus(snap);
  }catch(e){
    snap=captureFocus()||snap;
    S[key+'-loading']=false; render();
    restoreFocus(snap);
    toast(e.message||'Erreur de recherche','error');
  }
}

async function attachOfsToDossier(planningId, ofIds){
  if(!ofIds || !ofIds.length){ toast('Coche au moins un OF.','error'); return; }
  try{
    const data=await api('/api/admin/planning-of-links',{
      method:'POST',
      body:JSON.stringify({planning_id:planningId, of_ids:ofIds}),
    });
    const added=Number(data&&data.added||0);
    toast(added+' OF attaché'+(added>1?'s':'')+' au dossier.');
    // Reset l'état du picker pour ce dossier
    delete S['attach-'+planningId];
    delete S['attach-'+planningId+'-results'];
    delete S['attach-'+planningId+'-search'];
    delete S['attach-'+planningId+'-loading'];
    await loadDossiersSansOf();
    loadPendingOfCount();
    render();
  }catch(e){
    toast(e.message||'Erreur enregistrement','error');
  }
}

function toggleAttachOfPicker(planningId){
  const key='attach-'+planningId;
  if(S[key]){
    delete S[key];
    delete S[key+'-results'];
    delete S[key+'-search'];
    delete S[key+'-loading'];
    render();
    return;
  }
  S[key]=true;
  S[key+'-search']='';
  // search initiale (vide → 20 plus récents)
  searchOfsForAttach(planningId, '');
}

function renderDossiersSansOfTab(){
  if(S.dossiersSansOfLoading){
    return h('div',{className:'card',style:{padding:'24px',textAlign:'center',color:'var(--muted)'}},'Chargement…');
  }
  const items=S.dossiersSansOf||[];
  if(items.length===0){
    return h('div',{className:'card',style:{padding:'24px',textAlign:'center',color:'var(--muted)'}},
      h('div',{style:{fontSize:'15px',fontWeight:600,color:'var(--text2)',marginBottom:'6px'}},'Aucun dossier sans OF'),
      h('div',null,'Tous les dossiers actifs ont au moins un OF lié.')
    );
  }
  const intro=h('div',{style:{marginBottom:'16px',padding:'12px 16px',background:'var(--accent-bg)',border:'1px solid var(--border)',borderRadius:'10px',fontSize:'13px',color:'var(--text2)',lineHeight:1.6}},
    h('div',{style:{fontWeight:600,color:'var(--text)',marginBottom:'4px'}},
      items.length+' dossier'+(items.length>1?'s':'')+' actif'+(items.length>1?'s':'')+' sans OF lié'),
    'Recherche dans tous les OF existants pour en attacher un (ou plusieurs), ou importe un nouvel OF PDF.'
  );

  const cards=items.map(it=>{
    const key='attach-'+it.planning_id;
    const pickerOpen=!!S[key];
    const results=S[key+'-results']||[];
    const isLoading=!!S[key+'-loading'];
    const searchVal=S[key+'-search']||'';

    const head=h('div',{style:'display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap'},
      h('div',{style:'min-width:0'},
        h('div',{style:'font-size:12px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px'},'Planning #'+it.planning_id),
        h('div',{style:'font-size:14px;font-weight:600;color:var(--text)'},'OF attendu : '+escHtml(it.numero_of||'—')),
        h('div',{style:'font-size:12px;color:var(--muted);margin-top:2px'},
          'Réf produit : ',escHtml(it.ref_produit||'—'),
          it.machine?' · Machine : '+escHtml(it.machine):'',
          it.statut?' · '+escHtml(it.statut):''
        )
      ),
      h('div',{style:'display:flex;gap:8px;align-items:center;flex-wrap:wrap'},
        h('button',{
          style:'padding:8px 14px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text);cursor:pointer;font-size:12px;font-weight:600;white-space:nowrap',
          onClick:openOfImportModal,
          title:'Importer un nouvel OF PDF (la liaison sera à faire ensuite)'
        },iconEl('upload',12),' Importer OF PDF'),
        h('button',{
          style:'padding:8px 14px;border-radius:8px;border:none;background:var(--accent);color:#fff;cursor:pointer;font-size:12px;font-weight:700;white-space:nowrap',
          onClick:()=>toggleAttachOfPicker(it.planning_id)
        },pickerOpen?'Fermer la recherche':'Chercher un OF')
      )
    );

    if(!pickerOpen){
      return h('div',{className:'card',style:{padding:'14px 18px',marginBottom:'12px'}}, head);
    }

    const searchInput=h('input',{
      id:'attach-search-'+it.planning_id,
      type:'text',
      placeholder:'Rechercher par OF n°, référence, machine…',
      value:searchVal,
      style:'width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:9px 12px;color:var(--text);font-size:13px;font-family:inherit;outline:none;margin-bottom:10px',
      oninput:function(e){
        const v=e.target.value;
        S[key+'-search']=v;
        clearTimeout(window['__attachDeb-'+it.planning_id]);
        window['__attachDeb-'+it.planning_id]=setTimeout(()=>searchOfsForAttach(it.planning_id, v), 180);
      },
    });

    const resultRows=isLoading
      ? [h('div',{style:'padding:14px;color:var(--muted);font-size:13px;text-align:center'},'Recherche en cours…')]
      : (results.length===0
          ? [h('div',{style:'padding:14px;color:var(--muted);font-size:13px;text-align:center'},'Aucun résultat')]
          : results.map(c=>{
              const dateImp=(c.date_import||'').slice(0,10)||'—';
              return h('label',{
                style:'display:flex;align-items:center;gap:10px;padding:8px 10px;border:1px solid var(--border);border-radius:8px;margin-bottom:5px;cursor:pointer;background:var(--bg)',
              },
                h('input',{type:'checkbox','data-attach-plan':String(it.planning_id),value:String(c.id),style:'margin:0;flex-shrink:0;cursor:pointer'}),
                h('div',{style:'flex:1;min-width:0'},
                  h('div',{style:'font-weight:600;color:var(--text);font-size:13px'},escHtml(c.of_numero||'—')),
                  h('div',{style:'font-size:12px;color:var(--muted);margin-top:2px'},
                    'Réf : ',escHtml(c.reference||'—'),
                    c.machine?' · '+escHtml(c.machine):'',
                    ' · importé ',dateImp
                  )
                )
              );
            })
        );

    const attachBtn=h('button',{
      style:'margin-top:10px;padding:9px 14px;border-radius:8px;border:none;background:var(--accent);color:#fff;cursor:pointer;font-size:12px;font-weight:700',
      onClick:()=>{
        const boxes=document.querySelectorAll('[data-attach-plan="'+it.planning_id+'"]:checked');
        const ofIds=Array.from(boxes).map(b=>parseInt(b.value,10)).filter(x=>!isNaN(x));
        attachOfsToDossier(it.planning_id, ofIds);
      }
    },'Attacher les OF sélectionnés au dossier');

    return h('div',{className:'card',style:{padding:'14px 18px',marginBottom:'12px'}},
      head,
      h('div',{style:'margin-top:14px;padding-top:12px;border-top:1px dashed var(--border)'},
        searchInput,
        h('div',null, ...resultRows),
        attachBtn
      )
    );
  });

  return h('div',null, intro, ...cards);
}

function renderPendingOfMappingsTab(){
  if(S.pendingOfLoading){
    return h('div',{className:'card',style:{padding:'24px',textAlign:'center',color:'var(--muted)'}},'Chargement…');
  }
  const items=S.pendingOfMappings||[];
  if(items.length===0){
    return h('div',{className:'card',style:{padding:'24px',textAlign:'center',color:'var(--muted)'}},
      h('div',{style:{fontSize:'15px',fontWeight:600,color:'var(--text2)',marginBottom:'6px'}},'Aucun mapping à valider'),
      h('div',null,'Tous les plannings avec un numero_of sont liés automatiquement à un OF, ou n\'ont aucun OF candidat.')
    );
  }
  const intro=h('div',{style:{marginBottom:'16px',padding:'12px 16px',background:'var(--accent-bg)',border:'1px solid var(--border)',borderRadius:'10px',fontSize:'13px',color:'var(--text2)',lineHeight:1.6}},
    h('div',{style:{fontWeight:600,color:'var(--text)',marginBottom:'4px'}},
      items.length+' planning'+(items.length>1?'s':'')+' à associer manuellement'),
    'Le moteur a trouvé plusieurs OF candidats sans pouvoir choisir. Sélectionne le bon OF pour chaque ligne.'
  );

  const cards=items.map(it=>{
    const candRows=(it.candidates||[]).map(c=>{
      const dateImp=(c.date_import||'').slice(0,10)||'—';
      return h('label',{
        style:'display:flex;align-items:center;gap:10px;padding:8px 10px;border:1px solid var(--border);border-radius:8px;margin-bottom:6px;cursor:pointer;background:var(--bg)',
      },
        h('input',{type:'checkbox','data-pending-plan':String(it.planning_id),value:String(c.id),style:'margin:0;flex-shrink:0;cursor:pointer'}),
        h('div',{style:'flex:1;min-width:0'},
          h('div',{style:'font-weight:600;color:var(--text);font-size:13px'},escHtml(c.of_numero||'—')),
          h('div',{style:'font-size:12px;color:var(--muted);margin-top:2px'},
            'Réf : ',escHtml(c.reference||'—'),
            c.machine?' · '+escHtml(c.machine):'',
            ' · importé ',dateImp,
            c.imported_by?' par '+escHtml(c.imported_by):''
          )
        )
      );
    });

    return h('div',{className:'card',style:{padding:'16px 18px',marginBottom:'14px'}},
      h('div',{style:'display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-bottom:12px;flex-wrap:wrap'},
        h('div',null,
          h('div',{style:'font-size:12px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px'},'Planning #'+it.planning_id),
          h('div',{style:'font-size:14px;font-weight:600;color:var(--text)'},escHtml(it.numero_of||'—')),
          h('div',{style:'font-size:12px;color:var(--muted);margin-top:2px'},
            'Réf produit : ',escHtml(it.ref_produit||'—'),
            it.machine?' · Machine : '+escHtml(it.machine):''
          )
        ),
        h('div',{style:'display:flex;gap:8px;align-items:center;flex-wrap:wrap'},
          h('button',{
            style:'padding:8px 14px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--muted);cursor:pointer;font-size:12px;font-weight:600',
            title:'Ignorer (laisse non lié, sera reproposé au prochain chargement)',
            onClick:()=>submitOfMapping(it.planning_id, null)
          },'Ignorer'),
          h('button',{
            style:'padding:8px 14px;border-radius:8px;border:none;background:var(--accent);color:#fff;cursor:pointer;font-size:12px;font-weight:700',
            onClick:()=>{
              const boxes=document.querySelectorAll('[data-pending-plan="'+it.planning_id+'"]:checked');
              const ofIds=Array.from(boxes).map(b=>parseInt(b.value,10)).filter(x=>!isNaN(x));
              if(!ofIds.length){ toast('Coche au moins un OF.','error'); return; }
              submitOfMappingMulti(it.planning_id, ofIds);
            }
          },'Lier les OF sélectionnés')
        )
      ),
      h('div',{style:'font-size:11px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px'},
        (it.candidates||[]).length+' candidat'+((it.candidates||[]).length>1?'s':'')+' trouvé'+((it.candidates||[]).length>1?'s':'')),
      ...candRows
    );
  });

  return h('div',null, intro, ...cards);
}
function _csvEscape(v){
  if(v==null) return '';
  const s=String(v);
  if(s.includes(';')||s.includes('"')||s.includes('\n')||s.includes('\r'))
    return '"'+s.replace(/"/g,'""')+'"';
  return s;
}
function _downloadCsv(filename, headers, cols, rows){
  const lines=[headers.join(';')];
  for(const r of rows){
    lines.push(cols.map(c=>_csvEscape(r[c])).join(';'));
  }
  const csv='\ufeff'+lines.join('\r\n');
  const blob=new Blob([csv],{type:'text/csv;charset=utf-8'});
  const a=document.createElement('a');
  a.href=URL.createObjectURL(blob);
  a.download=filename;
  document.body.appendChild(a);
  a.click();
  setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove();},800);
}
async function exportFichesCsv(){
  try{
    const q=encodeURIComponent(S.ficheSearch||'');
    const all=[];
    let offset=0;
    const limit=200;
    while(true){
      const url='/api/fiches-techniques/list?limit='+limit+'&offset='+offset+(q?'&q='+q:'');
      const data=await api(url);
      const rows=Array.isArray(data.rows)?data.rows:[];
      all.push(...rows);
      if(rows.length<limit||all.length>=(data.total||0)) break;
      offset+=limit;
    }
    if(!all.length){toast('Aucune fiche à exporter.','info');return;}
    const cols=['id','reference','designation','client','format','eti_laize','eti_longueur','support','matiere','machine','nb_couleurs','source','date_import'];
    const headers=['ID','Référence','Désignation','Client','Format','Laize eti. (mm)','Longueur eti.','Support','Matière','Machine','Nb couleurs','Source','Date import'];
    const ymd=new Date().toISOString().slice(0,10);
    _downloadCsv('fiches_techniques_'+ymd+'.csv',headers,cols,all);
    toast(all.length+' fiche'+(all.length>1?'s':'')+' exportée'+(all.length>1?'s':'')+'.');
  }catch(e){
    toast(e.message||'Erreur export.','error');
  }
}
async function exportOfCsv(){
  try{
    const q=encodeURIComponent(S.ofSearch||'');
    const all=[];
    let offset=0;
    const limit=200;
    while(true){
      const url='/api/of/list?limit='+limit+'&offset='+offset+(q?'&q='+q:'');
      const data=await api(url);
      const rows=Array.isArray(data.rows)?data.rows:[];
      all.push(...rows);
      if(rows.length<limit||all.length>=(data.total||0)) break;
      offset+=limit;
    }
    if(!all.length){toast('Aucun OF à exporter.','info');return;}
    const cols=['id','of_numero','reference','machine','delai_client','format','date_creation','qte_etiquettes','qte_bobines','metrage','matiere','conditionnement','outil_1_numero','nb_mandrins','nb_cartons','nb_tubes','statut','date_import','imported_by'];
    const headers=['ID','OF n°','Référence','Machine','Délai client','Format','Date création','Qté étiquettes','Qté bobines','Métrage','Matière','Conditionnement','Outil 1','Nb mandrins','Nb cartons','Nb tubes','Statut','Date import','Importé par'];
    const ymd=new Date().toISOString().slice(0,10);
    _downloadCsv('of_imports_'+ymd+'.csv',headers,cols,all);
    toast(all.length+' OF exporté'+(all.length>1?'s':'')+'.');
  }catch(e){
    toast(e.message||'Erreur export.','error');
  }
}
function openOfEditModal(row){
  set({ofEditModal:{...row}});
  renderOfEditModal();
}
function closeOfEditModal(){
  const existing=document.getElementById('of-edit-overlay');
  if(existing) existing.remove();
  set({ofEditModal:null});
  render();
}
window.closeOfEditModal = closeOfEditModal;

async function saveOfEdit(){
  const m=S.ofEditModal;
  if(!m) return;
  const tv=id=>{const el=document.getElementById(id);return el?el.value.trim()||null:null;};
  const nv=id=>{const el=document.getElementById(id);return el&&el.value!==''?parseFloat(el.value)||null:null;};
  const iv=id=>{const el=document.getElementById(id);return el&&el.value!==''?parseInt(el.value)||null:null;};
  const payload={
    of_numero:            tv('ofe-numero'),
    reference:            tv('ofe-reference'),
    date_creation:        tv('ofe-date'),
    delai_client:         tv('ofe-delai'),
    machine:              tv('ofe-machine'),
    laize:                nv('ofe-laize'),
    format:               tv('ofe-format'),
    matiere:              tv('ofe-matiere'),
    ref_matiere:          tv('ofe-ref-matiere'),
    glassine:             tv('ofe-glassine'),
    ref_adhesif:          tv('ofe-ref-adhesif'),
    qte_adhesif_g:        nv('ofe-qte-adhesif-g'),
    qte_adhesif_kg:       nv('ofe-qte-adhesif-kg'),
    adhesif_label:        tv('ofe-adhesif-label'),
    qte_au_mille:         nv('ofe-qte-mille'),
    nb_levees:            iv('ofe-nb-levees'),
    qte_etiquettes:       iv('ofe-qte'),
    qte_bobines:          nv('ofe-bobines'),
    metrage:              iv('ofe-metrage'),
    tolerance:            tv('ofe-tolerance'),
    bobinettes_completes: tv('ofe-bobinettes'),
    conditionnement:      tv('ofe-cond'),
    cartons_type:         tv('ofe-cartons-type'),
    nb_cartons:           iv('ofe-cartons'),
    mandrins_dia:         tv('ofe-mandrins-dia'),
    mandrin_longueur:     nv('ofe-mandrin-longueur'),
    nb_mandrins:          iv('ofe-mandrins'),
    nb_tubes:             iv('ofe-tubes'),
    outil_1_forme:        tv('ofe-outil1-forme'),
    outil_1_numero:       tv('ofe-outil1-numero'),
    outil_1_angle:        tv('ofe-outil1-angle'),
    outil_1_mag:          tv('ofe-outil1-mag'),
    outil_1_cp:           tv('ofe-outil1-cp'),
    outil_1_hauteur:      nv('ofe-outil1-hauteur'),
    outil_1_fournisseur:  tv('ofe-outil1-fournisseur'),
    outil_2_forme:        tv('ofe-outil2-forme'),
    outil_2_numero:       tv('ofe-outil2-numero'),
    outil_2_angle:        tv('ofe-outil2-angle'),
    outil_2_cp:           tv('ofe-outil2-cp'),
    outil_alt_forme:      tv('ofe-outa-forme'),
    outil_alt_numero:     tv('ofe-outa-numero'),
    outil_alt_angle:      tv('ofe-outa-angle'),
    outil_alt_fournisseur:tv('ofe-outa-fournisseur'),
  };
  try{
    await api('/api/of/'+m.id,{method:'PATCH',body:JSON.stringify(payload)});
    toast('OF mis à jour.');
    closeOfEditModal();
    await loadOfImports();
    render();
  }catch(e){
    toast(e.message||'Erreur mise à jour.','error');
  }
}
window.saveOfEdit = saveOfEdit;
function renderOfEditModal(){
  const existing=document.getElementById('of-edit-overlay');
  if(existing) existing.remove();
  const m=S.ofEditModal;
  if(!m) return;
  const _f=(id,lbl,val,type='text')=>`<div>
    <label style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">${lbl}</label>
    <input id="${id}" type="${type}" value="${String(val==null?'':val).replace(/"/g,'&quot;')}"
      style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:8px 11px;color:var(--text);font-size:13px;font-family:inherit;outline:none;box-sizing:border-box">
  </div>`;
  const _sec=(title,fields,open=true)=>`
    <div class="ofe-sec" style="border:1px solid var(--border);border-radius:10px;margin-bottom:8px;overflow:hidden">
      <div class="ofe-sec-hd" style="display:flex;justify-content:space-between;align-items:center;padding:11px 16px;cursor:pointer;background:var(--accent-bg);border-bottom:1px solid var(--border);user-select:none">
        <span style="font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.8px;color:var(--accent)">${title}</span>
        <svg class="sec-chev" viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.5" style="color:var(--accent);transition:transform .18s;flex-shrink:0;${open?'transform:rotate(180deg)':''}"><polyline points="6 9 12 15 18 9"/></svg>
      </div>
      <div class="ofe-sec-body" style="display:${open?'grid':'none'};grid-template-columns:1fr 1fr 1fr;gap:10px 14px;padding:14px;background:var(--card)">
        ${fields}
      </div>
    </div>`;
  const overlay=document.createElement('div');
  overlay.id='of-edit-overlay';
  overlay.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:1000;display:flex;align-items:center;justify-content:center;padding:16px;box-sizing:border-box';
  overlay.onclick=e=>{if(e.target===overlay)closeOfEditModal();};
  overlay.innerHTML=`
    <div style="background:var(--card);border:1px solid var(--border);border-radius:14px;padding:22px 24px 18px;max-width:900px;width:100%;max-height:92vh;overflow-y:auto;box-sizing:border-box">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
        <div style="font-size:15px;font-weight:700;color:var(--text)">Modifier l'OF</div>
        <button onclick="closeOfEditModal()" style="background:none;border:none;color:var(--muted);cursor:pointer;padding:4px;font-size:20px;line-height:1;font-family:inherit">×</button>
      </div>
      ${_sec('Identification',[
        _f('ofe-numero','OF n°',m.of_numero),
        _f('ofe-reference','Référence',m.reference),
        _f('ofe-date','Date création',(m.date_creation||'').slice(0,10),'date'),
        _f('ofe-delai','Délai client',m.delai_client),
        _f('ofe-machine','Machine',m.machine),
      ].join(''),true)}
      ${_sec('Matière / Support',[
        _f('ofe-laize','Laize',m.laize,'number'),
        _f('ofe-format','Format',m.format),
        _f('ofe-matiere','Matière',m.matiere),
        _f('ofe-ref-matiere','Réf. matière',m.ref_matiere),
        _f('ofe-glassine','Glassine',m.glassine),
      ].join(''))}
      ${_sec('Adhésif',[
        _f('ofe-ref-adhesif','Réf. adhésif',m.ref_adhesif),
        _f('ofe-qte-adhesif-g','Qté adhésif (g)',m.qte_adhesif_g,'number'),
        _f('ofe-qte-adhesif-kg','Qté adhésif (kg)',m.qte_adhesif_kg,'number'),
        _f('ofe-adhesif-label','Label adhésif',m.adhesif_label),
      ].join(''))}
      ${_sec('Quantités',[
        _f('ofe-qte-mille','Qté au mille',m.qte_au_mille,'number'),
        _f('ofe-nb-levees','Nb levées',m.nb_levees,'number'),
        _f('ofe-qte','Qté étiquettes',m.qte_etiquettes,'number'),
        _f('ofe-bobines','Qté bobines',m.qte_bobines,'number'),
        _f('ofe-metrage','Métrage',m.metrage,'number'),
        _f('ofe-tolerance','Tolérance',m.tolerance),
        _f('ofe-bobinettes','Bobinettes complètes',m.bobinettes_completes),
      ].join(''))}
      ${_sec('Conditionnement',[
        _f('ofe-cond','Conditionnement',m.conditionnement),
        _f('ofe-cartons-type','Type cartons',m.cartons_type),
        _f('ofe-cartons','Nb cartons',m.nb_cartons,'number'),
        _f('ofe-mandrins-dia','Mandrins dia.',m.mandrins_dia),
        _f('ofe-mandrin-longueur','Mandrin long.',m.mandrin_longueur,'number'),
        _f('ofe-mandrins','Nb mandrins',m.nb_mandrins,'number'),
        _f('ofe-tubes','Nb tubes',m.nb_tubes,'number'),
      ].join(''))}
      ${_sec('Outillage',[
        _f('ofe-outil1-forme','Outil 1 — forme',m.outil_1_forme),
        _f('ofe-outil1-numero','Outil 1 — n°',m.outil_1_numero),
        _f('ofe-outil1-angle','Outil 1 — angle',m.outil_1_angle),
        _f('ofe-outil1-mag','Outil 1 — mag.',m.outil_1_mag),
        _f('ofe-outil1-cp','Outil 1 — CP',m.outil_1_cp),
        _f('ofe-outil1-hauteur','Outil 1 — hauteur',m.outil_1_hauteur,'number'),
        _f('ofe-outil1-fournisseur','Outil 1 — fournisseur',m.outil_1_fournisseur),
        _f('ofe-outil2-forme','Outil 2 — forme',m.outil_2_forme),
        _f('ofe-outil2-numero','Outil 2 — n°',m.outil_2_numero),
        _f('ofe-outil2-angle','Outil 2 — angle',m.outil_2_angle),
        _f('ofe-outil2-cp','Outil 2 — CP',m.outil_2_cp),
        _f('ofe-outa-forme','Outil alt. — forme',m.outil_alt_forme),
        _f('ofe-outa-numero','Outil alt. — n°',m.outil_alt_numero),
        _f('ofe-outa-angle','Outil alt. — angle',m.outil_alt_angle),
        _f('ofe-outa-fournisseur','Outil alt. — fournisseur',m.outil_alt_fournisseur),
      ].join(''))}
      <div style="display:flex;justify-content:flex-end;gap:10px;margin-top:12px;padding-top:12px;border-top:1px solid var(--border)">
        <button id="ofe-cancel-btn" style="padding:9px 16px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-family:inherit;font-size:13px">Annuler</button>
        <button id="ofe-save-btn" style="padding:9px 16px;border-radius:8px;border:none;background:var(--accent);color:#fff;cursor:pointer;font-family:inherit;font-size:13px;font-weight:700">Enregistrer</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);
  overlay.querySelectorAll('.ofe-sec-hd').forEach(hd=>{
    hd.addEventListener('click',()=>{
      const body=hd.nextElementSibling;
      const chev=hd.querySelector('.sec-chev');
      const open=body.style.display!=='none';
      body.style.display=open?'none':'grid';
      chev.style.transform=open?'':'rotate(180deg)';
    });
  });
  overlay.querySelector('#ofe-cancel-btn').onclick=closeOfEditModal;
  overlay.querySelector('#ofe-save-btn').onclick=saveOfEdit;
}

function openFicheEditModal(row){
  set({ficheEditModal:{...row}});
  renderFicheEditModal();
}
function closeFicheEditModal(){
  const existing=document.getElementById('fiche-edit-overlay');
  if(existing) existing.remove();
  set({ficheEditModal:null});
  render();
}
async function saveFicheEdit(){
  const m=S.ficheEditModal;
  if(!m) return;
  const tv=id=>{const el=document.getElementById(id);return el?el.value.trim()||null:null;};
  const nv=id=>{const el=document.getElementById(id);return el&&el.value!==''?parseFloat(el.value)||null:null;};
  const iv=id=>{const el=document.getElementById(id);return el&&el.value!==''?parseInt(el.value)||null:null;};
  const bv=id=>{const el=document.getElementById(id);return el?parseInt(el.value)||0:0;};
  const payload={
    reference:                  tv('fce-ref'),
    designation:                tv('fce-desig'),
    client:                     tv('fce-client'),
    machine:                    tv('fce-machine'),
    date_modif:                 tv('fce-date-modif'),
    format:                     tv('fce-format'),
    eti_laize:                  nv('fce-eti-laize'),
    eti_longueur:               nv('fce-eti-longueur'),
    eti_rayons:                 nv('fce-eti-rayons'),
    eti_perforations:           tv('fce-eti-perforations'),
    mod_laize:                  nv('fce-mod-laize'),
    mod_longueur:               nv('fce-mod-longueur'),
    mod_nb_front:               iv('fce-mod-front'),
    lateral_ext:                nv('fce-lat-ext'),
    horizontal:                 nv('fce-horizontal'),
    lateral_int:                nv('fce-lat-int'),
    support:                    tv('fce-support'),
    matiere:                    tv('fce-matiere'),
    adhesif:                    tv('fce-adhesif'),
    glassine:                   tv('fce-glassine'),
    laize_optimale:             nv('fce-laize-opt'),
    laize_optionnelle:          nv('fce-laize-optn'),
    epaisseur:                  nv('fce-epaisseur'),
    qte_au_mille:               nv('fce-qte-mille'),
    outil1_forme:               tv('fce-o1-forme'),
    outil1_numero_sifa:         tv('fce-o1-numero'),
    outil1_laize:               nv('fce-o1-laize'),
    outil1_epaisseur:           nv('fce-o1-epaisseur'),
    outil1_nb_dents:            iv('fce-o1-dents'),
    outil1_nb_front:            iv('fce-o1-front'),
    outil1_nb_avance:           iv('fce-o1-avance'),
    outil2_forme:               tv('fce-o2-forme'),
    outil2_numero_sifa:         tv('fce-o2-numero'),
    outil2_epaisseur:           nv('fce-o2-epaisseur'),
    outil2_nb_dents:            iv('fce-o2-dents'),
    outil2_nb_front:            iv('fce-o2-front'),
    outil2_nb_avance:           iv('fce-o2-avance'),
    outil3_forme:               tv('fce-o3-forme'),
    outil3_numero_sifa:         tv('fce-o3-numero'),
    outil3_epaisseur:           nv('fce-o3-epaisseur'),
    outil3_nb_dents:            iv('fce-o3-dents'),
    outil3_nb_front:            iv('fce-o3-front'),
    outil3_nb_avance:           iv('fce-o3-avance'),
    nb_couleurs:                iv('fce-nb-couleurs'),
    recto:                      bv('fce-recto'),
    verso:                      bv('fce-verso'),
    tete1_pantone:              tv('fce-t1-pantone'),
    tete1_couleur:              tv('fce-t1-couleur'),
    tete1_anilox:               tv('fce-t1-anilox'),
    tete1_composition:          tv('fce-t1-compo'),
    tete2_pantone:              tv('fce-t2-pantone'),
    tete2_couleur:              tv('fce-t2-couleur'),
    tete2_anilox:               tv('fce-t2-anilox'),
    tete2_composition:          tv('fce-t2-compo'),
    tete3_pantone:              tv('fce-t3-pantone'),
    tete3_couleur:              tv('fce-t3-couleur'),
    tete3_anilox:               tv('fce-t3-anilox'),
    tete3_composition:          tv('fce-t3-compo'),
    remarque:                   tv('fce-remarque'),
    conditionnement:            tv('fce-cond'),
    mandrin_dia:                tv('fce-mandrin-dia'),
    mandrin_longueur:           nv('fce-mandrin-longueur'),
    enroulement:                tv('fce-enroulement'),
    nb_etiq_bobin:              iv('fce-nb-etiq-bobin'),
    dia_ext:                    nv('fce-dia-ext'),
    poids:                      nv('fce-poids'),
    cales_sachets:              tv('fce-cales-sachets'),
    cartons:                    tv('fce-cartons'),
    nb_au_sol:                  iv('fce-nb-sol'),
    nb_etage:                   iv('fce-nb-etage'),
    nb_bobines_carton:          iv('fce-nb-bob-carton'),
    palette_type:               tv('fce-palette-type'),
    palette_nb_cartons_sol:     iv('fce-palette-sol'),
    palette_nb_cartons_hauteur: iv('fce-palette-hauteur'),
    palette_hauteur_max:        nv('fce-palette-hmax'),
    particularite:              tv('fce-particularite'),
    notes:                      tv('fce-notes'),
  };
  try{
    await api('/api/fiches-techniques/'+m.id,{method:'PATCH',body:JSON.stringify(payload)});
    toast('Fiche mise à jour.');
    closeFicheEditModal();
    await loadFiches();
    render();
  }catch(e){
    toast(e.message||'Erreur mise à jour.','error');
  }
}
function renderFicheEditModal(){
  const existing=document.getElementById('fiche-edit-overlay');
  if(existing) existing.remove();
  const m=S.ficheEditModal;
  if(!m) return;
  const _f=(id,lbl,val,type='text')=>`<div>
    <label style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">${lbl}</label>
    <input id="${id}" type="${type}" value="${String(val==null?'':val).replace(/"/g,'&quot;')}"
      style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:8px 11px;color:var(--text);font-size:13px;font-family:inherit;outline:none;box-sizing:border-box">
  </div>`;
  const _cb=(id,lbl,val)=>`<div>
    <label style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">${lbl}</label>
    <select id="${id}" style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:8px 11px;color:var(--text);font-size:13px;font-family:inherit;outline:none;box-sizing:border-box">
      <option value="0" ${!val||val==0?'selected':''}>Non</option>
      <option value="1" ${val==1?'selected':''}>Oui</option>
    </select>
  </div>`;
  const _sec=(title,fields,open=true)=>`
    <div class="fce-sec" style="border:1px solid var(--border);border-radius:10px;margin-bottom:8px;overflow:hidden">
      <div class="fce-sec-hd" style="display:flex;justify-content:space-between;align-items:center;padding:11px 16px;cursor:pointer;background:var(--accent-bg);border-bottom:1px solid var(--border);user-select:none">
        <span style="font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.8px;color:var(--accent)">${title}</span>
        <svg class="sec-chev" viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.5" style="color:var(--accent);transition:transform .18s;flex-shrink:0;${open?'transform:rotate(180deg)':''}"><polyline points="6 9 12 15 18 9"/></svg>
      </div>
      <div class="fce-sec-body" style="display:${open?'grid':'none'};grid-template-columns:1fr 1fr 1fr;gap:10px 14px;padding:14px;background:var(--card)">
        ${fields}
      </div>
    </div>`;
  const overlay=document.createElement('div');
  overlay.id='fiche-edit-overlay';
  overlay.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:1000;display:flex;align-items:center;justify-content:center;padding:16px;box-sizing:border-box';
  overlay.onclick=e=>{if(e.target===overlay)closeFicheEditModal();};
  overlay.innerHTML=`
    <div style="background:var(--card);border:1px solid var(--border);border-radius:14px;padding:22px 24px 18px;max-width:900px;width:100%;max-height:92vh;overflow-y:auto;box-sizing:border-box">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
        <div style="font-size:15px;font-weight:700;color:var(--text)">Modifier la fiche technique</div>
        <button onclick="closeFicheEditModal()" style="background:none;border:none;color:var(--muted);cursor:pointer;padding:4px;font-size:20px;line-height:1;font-family:inherit">×</button>
      </div>
      ${_sec('Identification',[
        _f('fce-ref','Référence',m.reference),
        _f('fce-desig','Désignation',m.designation),
        _f('fce-client','Client',m.client),
        _f('fce-machine','Machine',m.machine),
        _f('fce-date-modif','Date modif.',m.date_modif),
      ].join(''),true)}
      ${_sec('Étiquette',[
        _f('fce-format','Format',m.format),
        _f('fce-eti-laize','Laize eti. (mm)',m.eti_laize,'number'),
        _f('fce-eti-longueur','Longueur eti. (mm)',m.eti_longueur,'number'),
        _f('fce-eti-rayons','Rayons (mm)',m.eti_rayons,'number'),
        _f('fce-eti-perforations','Perforations',m.eti_perforations),
      ].join(''))}
      ${_sec('Module',[
        _f('fce-mod-laize','Laize module',m.mod_laize,'number'),
        _f('fce-mod-longueur','Longueur module',m.mod_longueur,'number'),
        _f('fce-mod-front','Nb front',m.mod_nb_front,'number'),
      ].join(''))}
      ${_sec('Échenillage',[
        _f('fce-lat-ext','Latéral ext.',m.lateral_ext,'number'),
        _f('fce-horizontal','Horizontal',m.horizontal,'number'),
        _f('fce-lat-int','Latéral int.',m.lateral_int,'number'),
      ].join(''))}
      ${_sec('Matière',[
        _f('fce-support','Support',m.support||m.matiere),
        _f('fce-matiere','Matière',m.matiere),
        _f('fce-adhesif','Adhésif',m.adhesif),
        _f('fce-glassine','Glassine',m.glassine),
        _f('fce-laize-opt','Laize optimale',m.laize_optimale,'number'),
        _f('fce-laize-optn','Laize optionnelle',m.laize_optionnelle,'number'),
        _f('fce-epaisseur','Épaisseur',m.epaisseur,'number'),
        _f('fce-qte-mille','Qté au mille',m.qte_au_mille,'number'),
      ].join(''))}
      ${_sec('Outil 1',[
        _f('fce-o1-forme','Forme',m.outil1_forme),
        _f('fce-o1-numero','N° SIFA',m.outil1_numero_sifa),
        _f('fce-o1-laize','Laize',m.outil1_laize,'number'),
        _f('fce-o1-epaisseur','Épaisseur',m.outil1_epaisseur,'number'),
        _f('fce-o1-dents','Nb dents',m.outil1_nb_dents,'number'),
        _f('fce-o1-front','Nb front',m.outil1_nb_front,'number'),
        _f('fce-o1-avance','Nb avance',m.outil1_nb_avance,'number'),
      ].join(''))}
      ${_sec('Outil 2',[
        _f('fce-o2-forme','Forme',m.outil2_forme),
        _f('fce-o2-numero','N° SIFA',m.outil2_numero_sifa),
        _f('fce-o2-epaisseur','Épaisseur',m.outil2_epaisseur,'number'),
        _f('fce-o2-dents','Nb dents',m.outil2_nb_dents,'number'),
        _f('fce-o2-front','Nb front',m.outil2_nb_front,'number'),
        _f('fce-o2-avance','Nb avance',m.outil2_nb_avance,'number'),
      ].join(''))}
      ${_sec('Outil 3',[
        _f('fce-o3-forme','Forme',m.outil3_forme),
        _f('fce-o3-numero','N° SIFA',m.outil3_numero_sifa),
        _f('fce-o3-epaisseur','Épaisseur',m.outil3_epaisseur,'number'),
        _f('fce-o3-dents','Nb dents',m.outil3_nb_dents,'number'),
        _f('fce-o3-front','Nb front',m.outil3_nb_front,'number'),
        _f('fce-o3-avance','Nb avance',m.outil3_nb_avance,'number'),
      ].join(''))}
      ${_sec('Impression',[
        _f('fce-nb-couleurs','Nb couleurs',m.nb_couleurs,'number'),
        _cb('fce-recto','Recto',m.recto),
        _cb('fce-verso','Verso',m.verso),
        _f('fce-t1-pantone','Tête 1 — Pantone',m.tete1_pantone),
        _f('fce-t1-couleur','Tête 1 — Couleur',m.tete1_couleur),
        _f('fce-t1-anilox','Tête 1 — Anilox',m.tete1_anilox),
        _f('fce-t1-compo','Tête 1 — Composition',m.tete1_composition),
        _f('fce-t2-pantone','Tête 2 — Pantone',m.tete2_pantone),
        _f('fce-t2-couleur','Tête 2 — Couleur',m.tete2_couleur),
        _f('fce-t2-anilox','Tête 2 — Anilox',m.tete2_anilox),
        _f('fce-t2-compo','Tête 2 — Composition',m.tete2_composition),
        _f('fce-t3-pantone','Tête 3 — Pantone',m.tete3_pantone),
        _f('fce-t3-couleur','Tête 3 — Couleur',m.tete3_couleur),
        _f('fce-t3-anilox','Tête 3 — Anilox',m.tete3_anilox),
        _f('fce-t3-compo','Tête 3 — Composition',m.tete3_composition),
        _f('fce-remarque','Remarque',m.remarque),
      ].join(''))}
      ${_sec('Conditionnement',[
        _f('fce-cond','Conditionnement',m.conditionnement),
        _f('fce-mandrin-dia','Mandrin dia.',m.mandrin_dia),
        _f('fce-mandrin-longueur','Mandrin long.',m.mandrin_longueur,'number'),
        _f('fce-enroulement','Enroulement',m.enroulement),
        _f('fce-nb-etiq-bobin','Nb étiq./bobine',m.nb_etiq_bobin,'number'),
        _f('fce-dia-ext','Dia. ext.',m.dia_ext,'number'),
        _f('fce-poids','Poids',m.poids,'number'),
        _f('fce-cales-sachets','Cales / sachets',m.cales_sachets),
        _f('fce-cartons','Cartons',m.cartons),
        _f('fce-nb-sol','Nb au sol',m.nb_au_sol,'number'),
        _f('fce-nb-etage','Nb étages',m.nb_etage,'number'),
        _f('fce-nb-bob-carton','Nb bob./carton',m.nb_bobines_carton,'number'),
      ].join(''))}
      ${_sec('Palettisation',[
        _f('fce-palette-type','Type palette',m.palette_type),
        _f('fce-palette-sol','Nb cartons/sol',m.palette_nb_cartons_sol,'number'),
        _f('fce-palette-hauteur','Nb cartons/hauteur',m.palette_nb_cartons_hauteur,'number'),
        _f('fce-palette-hmax','Hauteur max. (cm)',m.palette_hauteur_max,'number'),
        _f('fce-particularite','Particularité',m.particularite),
      ].join(''))}
      ${_sec('Notes',[
        `<div style="grid-column:1/-1"><label style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Notes</label>
        <textarea id="fce-notes" rows="3" style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:8px 11px;color:var(--text);font-size:13px;font-family:inherit;outline:none;box-sizing:border-box;resize:vertical">${String(m.notes||'').replace(/</g,'&lt;')}</textarea></div>`,
      ].join(''))}
      <div style="display:flex;justify-content:flex-end;gap:10px;margin-top:12px;padding-top:12px;border-top:1px solid var(--border)">
        <button id="fce-cancel-btn" style="padding:9px 16px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-family:inherit;font-size:13px">Annuler</button>
        <button id="fce-save-btn" style="padding:9px 16px;border-radius:8px;border:none;background:var(--accent);color:#fff;cursor:pointer;font-family:inherit;font-size:13px;font-weight:700">Enregistrer</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);
  overlay.querySelectorAll('.fce-sec-hd').forEach(hd=>{
    hd.addEventListener('click',()=>{
      const body=hd.nextElementSibling;
      const chev=hd.querySelector('.sec-chev');
      const open=body.style.display!=='none';
      body.style.display=open?'none':'grid';
      chev.style.transform=open?'':'rotate(180deg)';
    });
  });
  overlay.querySelector('#fce-cancel-btn').onclick=closeFicheEditModal;
  overlay.querySelector('#fce-save-btn').onclick=saveFicheEdit;
}
function openOfImportModal(){
  set({ofImportModal:{step:1,file:null,parsed:null,parsing:false}});
  render();
}
function closeOfImportModal(){
  set({ofImportModal:null});
  render();
}
async function ofHandlePdfFile(file){
  if(!file||!/\.pdf$/i.test(file.name||'')){toast('Fichier PDF requis.','error');return;}
  set({ofImportModal:{step:1,file,parsed:null,parsing:true}});
  render();
  const fd=new FormData();
  fd.append('file',file);
  try{
    const parsed=await fetch('/api/of/parse',{method:'POST',credentials:'include',body:fd})
      .then(async r=>{
        if(r.status===401){window.location.href='/';return null;}
        if(!r.ok){
          const err=await r.json().catch(()=>({}));
          throw new Error(err.detail||('Erreur '+r.status));
        }
        return r.json();
      });
    if(!parsed) return;
    set({ofImportModal:{step:2,file,parsed,parsing:false}});
    render();
  }catch(e){
    set({ofImportModal:{step:1,file:null,parsed:null,parsing:false}});
    toast(e.message||'Analyse PDF impossible.','error');
    render();
  }
}
async function ofValidateImport(){
  const m=S.ofImportModal;
  if(!m||!m.file) return;
  const data={};
  Object.keys(OF_FIELD_LABELS).forEach(k=>{
    const el=document.getElementById('of-f-'+k);
    if(el) data[k]=el.value;
  });
  const fd=new FormData();
  fd.append('file',m.file);
  fd.append('data',JSON.stringify(data));
  try{
    const r=await fetch('/api/of/validate',{method:'POST',credentials:'include',body:fd});
    if(!r.ok){
      const err=await r.json().catch(()=>({}));
      throw new Error(err.detail||('Erreur '+r.status));
    }
    toast('OF importé.');
    set({ofImportModal:null});
    await loadOfImports();
    render();
  }catch(e){
    toast(e.message||'Import impossible.','error');
  }
}
async function ofDeleteImport(id){
  if(!confirm('Supprimer cet import OF de la base ?')) return;
  try{
    await api('/api/of/'+id,{method:'DELETE'});
    toast('Import supprimé.');
    await loadOfImports();
    render();
  }catch(e){
    toast(e.message||'Suppression impossible.','error');
  }
}
function renderPaginationBar(page, total, pageSize, onPrev, onNext){
  const totalPages=Math.max(1,Math.ceil(total/pageSize));
  const start=total===0?0:page*pageSize+1;
  const end=Math.min((page+1)*pageSize,total);
  return h('div',{style:{display:'flex',alignItems:'center',gap:'10px',padding:'12px 0',fontSize:'12px',color:'var(--muted)'}},
    h('button',{
      style:'padding:6px 12px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-size:12px',
      disabled:page===0, onClick:onPrev
    },'← Préc.'),
    h('span',null,total===0?'Aucun résultat':`${start}–${end} sur ${total}`),
    h('button',{
      style:'padding:6px 12px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-size:12px',
      disabled:page>=totalPages-1, onClick:onNext
    },'Suiv. →'),
  );
}

function renderOfTab(){
  const PAGE_SIZE=50;
  const total=S.ofTotal||0;
  const page=S.ofPage||0;

  const toolbar=h('div',{style:{display:'flex',alignItems:'center',gap:'10px',marginBottom:'16px',flexWrap:'wrap'}},
    h('input',{
      id:'of-search-html',
      type:'text',
      placeholder:'Rechercher (OF n°, référence, machine…)',
      value:S.ofSearch||'',
      style:'flex:1;min-width:200px;max-width:320px;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:9px 12px;color:var(--text);font-size:13px;font-family:inherit;outline:none',
      oninput:async function(e){
        const v=e.target.value;
        const ss=e.target.selectionStart, se=e.target.selectionEnd;
        set({ofSearch:v,ofPage:0});
        await loadOfImports();
        render();
        requestAnimationFrame(()=>{
          const el=document.getElementById('of-search-html');
          if(el){el.focus();try{el.setSelectionRange(ss,se);}catch(x){}}
        });
      },
      onkeydown:function(e){
        if(e.key==='Escape'){set({ofSearch:'',ofPage:0});loadOfImports().then(()=>render());e.target.value='';}
      },
    }),
    h('button',{
      style:'padding:9px 14px;border-radius:8px;border:none;background:var(--accent);color:#fff;cursor:pointer;font-size:13px;font-weight:700;white-space:nowrap',
      onClick:openOfImportModal
    },iconEl('upload',13),' Importer un OF'),
    h('button',{
      style:'padding:9px 14px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text);cursor:pointer;font-size:13px;font-weight:600;white-space:nowrap',
      title:'Exporter tous les OF (filtre appliqué) en CSV',
      onClick:exportOfCsv
    },iconEl('download',13),' Exporter CSV'),
    S.user&&S.user.role==='superadmin'&&S.ofSelected.size>0
      ? h('button',{
          style:'padding:9px 14px;border-radius:8px;border:none;background:var(--danger);color:#fff;cursor:pointer;font-size:13px;font-weight:700;white-space:nowrap',
          onClick:async()=>{
            const n=S.ofSelected.size;
            if(!confirm(`Supprimer ${n} OF${n>1?'s':''} ?`)) return;
            try{
              await api('/api/of/bulk',{method:'DELETE',body:JSON.stringify({ids:[...S.ofSelected]})});
              toast(`${n} OF${n>1?'s':''} supprimé${n>1?'s':''}.`);
              set({ofSelected:new Set()});
              await loadOfImports();
              render();
            }catch(e){toast(e.message||'Erreur.','error');}
          }
        },iconEl('trash',13),` Supprimer (${S.ofSelected.size})`)
      : null
  );

  const rows=(S.ofImports||[]).map(row=>{
    const stCls=prodOfStatutClass(row.statut);
    const dateCrea=(row.date_creation||'').slice(0,10)||'—';
    const acts=[
      h('button',{
        style:'padding:4px 8px;border-radius:6px;border:1px solid var(--border);background:transparent;cursor:pointer',
        title:'Modifier', onClick:()=>openOfEditModal(row)
      },iconEl('edit',13)),
    ];
    acts.push(h('button',{
      style:'padding:4px 8px;border-radius:6px;border:1px solid var(--border);background:transparent;cursor:pointer',
      title:'Aperçu OF', onClick:()=>{window.open('/api/of/'+row.id+'/pdf-preview','_blank');}
    },iconEl('eye',13)));
    if(row.pdf_filename){
      acts.push(h('button',{
        style:'padding:4px 8px;border-radius:6px;border:1px solid var(--border);background:transparent;cursor:pointer',
        title:'Télécharger PDF', onClick:()=>{window.open('/api/of/'+row.id+'/pdf','_blank');}
      },iconEl('download',13)));
    }
    if(S.user&&S.user.role==='superadmin'){
      acts.push(h('button',{
        style:'padding:4px 8px;border-radius:6px;border:1px solid rgba(248,113,113,.3);background:transparent;cursor:pointer;color:var(--danger)',
        title:'Supprimer', onClick:()=>ofDeleteImport(row.id)
      },iconEl('trash',13)));
    }
    return h('tr',null,
      h('td',{style:{width:'36px'}},
        h('input',{type:'checkbox',checked:S.ofSelected.has(row.id),style:'cursor:pointer',
          onChange:function(e){
            const sel=new Set(S.ofSelected);
            if(e.target.checked)sel.add(row.id);else sel.delete(row.id);
            set({ofSelected:sel});render();
          }
        })
      ),
      h('td',null,
        h('div',null,escHtml(row.of_numero||'—')),
        row.imported_by?h('div',{style:{fontSize:'11px',color:'var(--muted)'}},escHtml(row.imported_by)):null,
      ),
      h('td',null,escHtml(row.reference||'—')),
      h('td',null,escHtml(row.machine||'—')),
      h('td',null,escHtml(row.delai_client||'—')),
      h('td',null,row.qte_etiquettes!=null?escHtml(String(row.qte_etiquettes)):'—'),
      h('td',null,escHtml(dateCrea)),
      h('td',null,h('span',{className:stCls},prodOfStatutLabel(row.statut))),
      h('td',null,h('div',{style:{display:'flex',gap:'4px'}},...acts)),
    );
  });

  const empty=h('tr',null,
    h('td',{colSpan:'9',style:{textAlign:'center',color:'var(--muted)',padding:'24px'}},
      S.ofImportsLoading?'Chargement…':(S.ofSearch?`Aucun résultat pour « ${escHtml(S.ofSearch)} »`:'Aucun OF importé')
    )
  );

  return h('div',{className:'card',style:{padding:'18px 20px'}},
    toolbar,
    renderPaginationBar(page,total,50,
      async()=>{if(page>0){set({ofPage:page-1});await loadOfImports();render();}},
      async()=>{if(page<Math.ceil(total/50)-1){set({ofPage:page+1});await loadOfImports();render();}}
    ),
    h('div',{style:{overflowX:'auto'}},
      h('table',{className:'table-std'},
        h('thead',null,h('tr',null,
          h('th',{style:{width:'36px'}},
            h('input',{type:'checkbox',style:'cursor:pointer',
              checked:(S.ofImports||[]).length>0&&(S.ofImports||[]).every(r=>S.ofSelected.has(r.id)),
              onChange:function(e){
                const ids=(S.ofImports||[]).map(r=>r.id);
                set({ofSelected:e.target.checked?new Set(ids):new Set()});render();
              }
            })
          ),
          h('th',null,'OF n°'),h('th',null,'Référence'),h('th',null,'Machine'),
          h('th',null,'Délai client'),h('th',null,'Qté étiquettes'),h('th',null,'Date création'),
          h('th',null,'Statut'),h('th',null,'Actions')
        )),
        h('tbody',null,...(rows.length?rows:[empty]))
      )
    ),
  );
}

function renderFichesTab(){
  const PAGE_SIZE=50;
  const total=S.ficheTotal||0;
  const page=S.fichePage||0;

  const toolbar=h('div',{style:{display:'flex',alignItems:'center',gap:'10px',marginBottom:'16px',flexWrap:'wrap'}},
    h('input',{
      id:'fiche-search-html',
      type:'text',
      placeholder:'Rechercher (référence, désignation, client…)',
      value:S.ficheSearch||'',
      style:'flex:1;min-width:200px;max-width:320px;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:9px 12px;color:var(--text);font-size:13px;font-family:inherit;outline:none',
      oninput:async function(e){
        const v=e.target.value;
        const ss=e.target.selectionStart,se=e.target.selectionEnd;
        set({ficheSearch:v,fichePage:0});
        await loadFiches();render();
        requestAnimationFrame(()=>{
          const el=document.getElementById('fiche-search-html');
          if(el){el.focus();try{el.setSelectionRange(ss,se);}catch(x){}}
        });
      },
      onkeydown:function(e){
        if(e.key==='Escape'){set({ficheSearch:'',fichePage:0});loadFiches().then(()=>render());e.target.value='';}
      },
    }),
    h('button',{
      style:'padding:9px 14px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text);cursor:pointer;font-size:13px;font-weight:600;white-space:nowrap',
      title:'Exporter toutes les fiches (filtre appliqué) en CSV',
      onClick:exportFichesCsv
    },iconEl('download',13),' Exporter CSV'),
    S.user&&S.user.role==='superadmin'&&S.ficheSelected.size>0
      ? h('button',{
          style:'padding:9px 14px;border-radius:8px;border:none;background:var(--danger);color:#fff;cursor:pointer;font-size:13px;font-weight:700;white-space:nowrap',
          onClick:async()=>{
            const n=S.ficheSelected.size;
            if(!confirm(`Supprimer ${n} fiche${n>1?'s':''} ?`)) return;
            try{
              await api('/api/fiches-techniques/bulk',{method:'DELETE',body:JSON.stringify({ids:[...S.ficheSelected]})});
              toast(`${n} fiche${n>1?'s':''} supprimée${n>1?'s':''}.`);
              set({ficheSelected:new Set()});
              await loadFiches();render();
            }catch(e){toast(e.message||'Erreur.','error');}
          }
        },iconEl('trash',13),` Supprimer (${S.ficheSelected.size})`)
      : null
  );

  const rows=(S.fiches||[]).map(row=>{
    const acts=[
      h('button',{
        style:'padding:4px 8px;border-radius:6px;border:1px solid var(--border);background:transparent;cursor:pointer',
        title:'Prévisualiser PDF',onClick:()=>window.open('/api/fiches-techniques/'+row.id+'/pdf-preview','_blank')
      },iconEl('file',13)),
      h('button',{
        style:'padding:4px 8px;border-radius:6px;border:1px solid var(--border);background:transparent;cursor:pointer',
        title:'Modifier',onClick:()=>openFicheEditModal(row)
      },iconEl('edit',13)),
    ];
    if(S.user&&S.user.role==='superadmin'){
      acts.push(h('button',{
        style:'padding:4px 8px;border-radius:6px;border:1px solid rgba(248,113,113,.3);background:transparent;cursor:pointer;color:var(--danger)',
        title:'Supprimer',
        onClick:async()=>{
          if(!confirm('Supprimer cette fiche ?')) return;
          try{await api('/api/fiches-techniques/'+row.id,{method:'DELETE'});toast('Fiche supprimée.');await loadFiches();render();}
          catch(e){toast(e.message||'Erreur.','error');}
        }
      },iconEl('trash',13)));
    }
    return h('tr',null,
      h('td',{style:{width:'36px'}},
        h('input',{type:'checkbox',checked:S.ficheSelected.has(row.id),style:'cursor:pointer',
          onChange:function(e){
            const sel=new Set(S.ficheSelected);
            if(e.target.checked)sel.add(row.id);else sel.delete(row.id);
            set({ficheSelected:sel});render();
          }
        })
      ),
      h('td',null,escHtml(row.reference||'—')),
      h('td',null,escHtml(row.format||'—')),
      h('td',null,row.eti_laize!=null?escHtml(String(row.eti_laize)+' mm'):'—'),
      h('td',null,escHtml(row.support||row.matiere||'—')),
      h('td',null,escHtml(row.machine||'—')),
      h('td',null,row.nb_couleurs!=null?escHtml(String(row.nb_couleurs)):'—'),
      h('td',null,escHtml(row.source||'—')),
      h('td',null,h('div',{style:{display:'flex',gap:'4px'}},...acts)),
    );
  });

  const empty=h('tr',null,
    h('td',{colSpan:'9',style:{textAlign:'center',color:'var(--muted)',padding:'24px'}},
      S.fichesLoading?'Chargement…':(S.ficheSearch?`Aucun résultat pour « ${escHtml(S.ficheSearch)} »`:'Aucune fiche technique importée')
    )
  );

  return h('div',{className:'card',style:{padding:'18px 20px'}},
    toolbar,
    renderPaginationBar(page,total,50,
      async()=>{if(page>0){set({fichePage:page-1});await loadFiches();render();}},
      async()=>{if(page<Math.ceil(total/50)-1){set({fichePage:page+1});await loadFiches();render();}}
    ),
    h('div',{style:{overflowX:'auto'}},
      h('table',{className:'table-std'},
        h('thead',null,h('tr',null,
          h('th',{style:{width:'36px'}},
            h('input',{type:'checkbox',style:'cursor:pointer',
              checked:(S.fiches||[]).length>0&&(S.fiches||[]).every(r=>S.ficheSelected.has(r.id)),
              onChange:function(e){
                const ids=(S.fiches||[]).map(r=>r.id);
                set({ficheSelected:e.target.checked?new Set(ids):new Set()});render();
              }
            })
          ),
          h('th',null,'Référence'),h('th',null,'Format'),h('th',null,'Laize eti.'),
          h('th',null,'Support'),h('th',null,'Machine'),h('th',null,'Nb coul.'),
          h('th',null,'Source'),h('th',null,'Actions')
        )),
        h('tbody',null,...(rows.length?rows:[empty]))
      )
    ),
  );
}

function renderOfPage(){
  const ambigusN = Number(S.pendingOfAmbigus || 0);
  const sansOfN  = Number(S.pendingOfSansOf  || 0);
  const pendingBadge = ambigusN > 0
    ? h('span',{style:'display:inline-block;margin-left:8px;padding:2px 8px;border-radius:10px;background:var(--danger);color:#fff;font-size:11px;font-weight:700;line-height:1.4'}, String(ambigusN))
    : null;
  const sansOfBadge = sansOfN > 0
    ? h('span',{style:'display:inline-block;margin-left:8px;padding:2px 8px;border-radius:10px;background:var(--danger);color:#fff;font-size:11px;font-weight:700;line-height:1.4'}, String(sansOfN))
    : null;
  const subNav=h('div',{style:{display:'flex',gap:'0',borderBottom:'1px solid var(--border)',marginBottom:'20px',flexWrap:'wrap'}},
    h('button',{
      style:`padding:10px 18px;font-size:13px;font-weight:600;border:none;background:transparent;cursor:pointer;border-bottom:2px solid ${S.ofSubTab==='of'?'var(--accent)':'transparent'};color:${S.ofSubTab==='of'?'var(--accent)':'var(--muted)'};font-family:inherit`,
      onClick:()=>{set({ofSubTab:'of'});render();}
    },'Ordres de fabrication'),
    h('button',{
      style:`padding:10px 18px;font-size:13px;font-weight:600;border:none;background:transparent;cursor:pointer;border-bottom:2px solid ${S.ofSubTab==='fiche'?'var(--accent)':'transparent'};color:${S.ofSubTab==='fiche'?'var(--accent)':'var(--muted)'};font-family:inherit`,
      onClick:async()=>{set({ofSubTab:'fiche'});await loadFiches();render();}
    },'Fiches techniques'),
    h('button',{
      style:`padding:10px 18px;font-size:13px;font-weight:600;border:none;background:transparent;cursor:pointer;border-bottom:2px solid ${S.ofSubTab==='pending'?'var(--accent)':'transparent'};color:${S.ofSubTab==='pending'?'var(--accent)':'var(--muted)'};font-family:inherit;display:inline-flex;align-items:center`,
      onClick:async()=>{set({ofSubTab:'pending'});await loadPendingOfMappings();render();}
    },'Mappings à valider', pendingBadge),
    h('button',{
      style:`padding:10px 18px;font-size:13px;font-weight:600;border:none;background:transparent;cursor:pointer;border-bottom:2px solid ${S.ofSubTab==='sansof'?'var(--accent)':'transparent'};color:${S.ofSubTab==='sansof'?'var(--accent)':'var(--muted)'};font-family:inherit;display:inline-flex;align-items:center`,
      onClick:async()=>{set({ofSubTab:'sansof'});await loadDossiersSansOf();render();}
    },'Dossiers sans OF', sansOfBadge),
  );
  return h('div',{style:{paddingLeft:'12px',paddingRight:'4px'}},
    subNav,
    S.ofSubTab==='fiche'   ? renderFichesTab()
      : S.ofSubTab==='pending' ? renderPendingOfMappingsTab()
      : S.ofSubTab==='sansof'  ? renderDossiersSansOfTab()
      : renderOfTab()
  );
}
function renderOfImportModal(){
  const m=S.ofImportModal;
  if(!m) return null;
  let body;
  if(m.parsing){
    body=h('div',{style:{display:'flex',alignItems:'center',justifyContent:'center',gap:10,padding:'40px',color:'var(--muted)'}},
      'Analyse du PDF…');
  }else if(m.step===1){
    const fileInput=h('input',{type:'file',accept:'.pdf,application/pdf',style:{display:'none'},id:'of-file-input'});
    const pickFile=()=>fileInput.click();
    fileInput.onchange=()=>{
      const f=fileInput.files&&fileInput.files[0];
      if(f) ofHandlePdfFile(f);
    };
    const dropzone=h('div',{className:'prod-of-dropzone',onClick:pickFile,
      onDragover:e=>{e.preventDefault();e.currentTarget.classList.add('prod-of-dropzone--active');},
      onDragleave:e=>{e.currentTarget.classList.remove('prod-of-dropzone--active');},
      onDrop:e=>{
        e.preventDefault();
        e.currentTarget.classList.remove('prod-of-dropzone--active');
        const f=e.dataTransfer&&e.dataTransfer.files&&e.dataTransfer.files[0];
        if(f) ofHandlePdfFile(f);
      }},
      iconEl('file',28),
      h('div',{className:'prod-of-dropzone-title'},'Déposer un PDF ici'),
      h('div',{className:'prod-of-dropzone-sub'},'ou cliquer pour sélectionner — .pdf uniquement')
    );
    body=h('div',null,fileInput,dropzone,
      h('div',{style:{marginTop:'14px',textAlign:'center'}},
        h('button',{className:'btn-ghost',onClick:pickFile},'Sélectionner un fichier')
      )
    );
  }else{
    const parsed=m.parsed||{};
    const previewRows=Object.keys(OF_FIELD_LABELS).map(k=>{
      const val=parsed[k];
      const missing=val==null||val==='';
      const display=val==null?'':String(val);
      return h('tr',{className:missing?'prod-of-missing':''},
        h('th',null,OF_FIELD_LABELS[k]),
        h('td',null,h('input',{type:'text',id:'of-f-'+k,value:display}))
      );
    });
    body=h('div',null,
      h('p',{className:'subtitle',style:{marginBottom:'8px'}},
        'Vérifiez les champs extraits. Les lignes surlignées indiquent une extraction manquante.'),
      h('table',{className:'prod-of-preview-table'},
        h('tbody',null,...previewRows)
      ),
      h('div',{className:'contact-modal-actions',style:{marginTop:'12px'}},
        h('button',{className:'btn-ghost',onClick:closeOfImportModal},'Annuler'),
        h('button',{className:'btn-sm',onClick:()=>ofValidateImport()},'Valider l\'import')
      )
    );
  }
  const overlay=h('div',{className:'contact-modal-overlay',onClick:e=>{
    if(e.target===e.currentTarget) closeOfImportModal();
  }});
  const box=h('div',{className:'contact-modal',style:{maxWidth:'720px',maxHeight:'88vh',overflowY:'auto'}},
    h('div',{className:'contact-modal-head'},
      h('h3',null,m.step===2?'Prévisualisation OF':'Importer un OF PDF'),
      h('button',{className:'contact-close-btn',onClick:closeOfImportModal},'×')
    ),
    h('div',{className:'contact-modal-body'},body)
  );
  overlay.appendChild(box);
  return overlay;
}

// ── Rentabilité ──────────────────────────────────────────────────
async function loadComparaison(devisId){
  const d=await api('/api/rentabilite/devis/'+devisId+'/comparaison');
  if(d)set({comparaison:d});
}

async function uploadDevis(file){
  try{
    const fd=new FormData();fd.append('file',file);
    const r=await api('/api/rentabilite/devis/import',{method:'POST',body:fd});
    if(!r)return;
    if(r.parse_errors&&r.parse_errors.length){
      toast('Parsed avec avertissements : '+r.parse_errors[0],'warn');
    }
    set({devisPreview:r.preview,selDevis:null,comparaison:null});
  }catch(e){toast(e.message,'error');}
}

async function saveDevis(body){
  try{
    const r=await api('/api/rentabilite/devis',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!r)return;
    toast('Devis enregistré');
    set({devisPreview:null});
    await loadDevis();
  }catch(e){toast(e.message,'error');}
}

async function linkDossiers(devisId, dossiers){
  try{
    await api('/api/rentabilite/devis/'+devisId+'/dossiers',{method:'PUT',
      headers:{'Content-Type':'application/json'},body:JSON.stringify({dossiers})});
    toast('Dossiers liés');
    await loadDevis();
    await loadComparaison(devisId);
  }catch(e){toast(e.message,'error');}
}

async function deleteDevis(id){
  if(!confirm('Supprimer ce devis ?'))return;
  try{
    await api('/api/rentabilite/devis/'+id,{method:'DELETE'});
    toast('Devis supprimé');
    set({selDevis:null,comparaison:null});
    await loadDevis();
  }catch(e){toast(e.message,'error');}
}

function renderDevisForm(preview){
  const inputs={};
  const mkField=(label,key,type='text',val)=>{
    const i=h('input',{type,value:val!=null?String(val):''});
    inputs[key]=i;
    return h('div',{className:'field-item'},h('label',null,label),i);
  };

  return h('div',{className:'card',style:{padding:'24px'}},
    h('h3',{style:{fontSize:'16px',fontWeight:'700',marginBottom:'4px'}},'📋 Valider le devis importé'),
    h('p',{style:{fontSize:'12px',color:'var(--muted)',marginBottom:'20px'}},
      preview.filename+(((preview && preview.parse_errors && preview.parse_errors.length)?preview.parse_errors.length:0)?' — ⚠ '+preview.parse_errors.length+' avertissement(s)':' — Données extraites automatiquement')),

    h('div',{className:'form-section'},
      h('div',{className:'form-section-title'},'Informations générales'),
      h('div',{className:'field-row'},mkField('Client','client','text',preview.client),mkField('Date devis','date_devis','text',preview.date_devis)),
      h('div',{className:'field-row three'},
        mkField('Format H (mm)','format_h','number',preview.format_h),
        mkField('Format V (mm)','format_v','number',preview.format_v),
        mkField('Laize (mm)','laize','number',preview.laize)
      ),
    ),

    h('div',{className:'form-section'},
      h('div',{className:'form-section-title'},'Données théoriques de production'),
      h('div',{className:'field-row'},
        mkField('Temps calage (mn)','temps_calage_mn','number',preview.temps_calage_mn),
        mkField('Métrage calage (ml)','metrage_calage_ml','number',preview.metrage_calage_ml)
      ),
      h('div',{className:'field-row'},
        mkField('Temps production (mn)','temps_production_mn','number',preview.temps_production_mn),
        mkField('Métrage production (ml)','metrage_production_ml','number',preview.metrage_production_ml)
      ),
      h('div',{className:'field-row three'},
        mkField('Vitesse (m/mn)','vitesse_theorique','number',preview.vitesse_theorique),
        mkField('Qté étiquettes','qte_etiquettes','number',preview.qte_etiquettes),
        mkField('Gâche (%)','gache','number',preview.gache)
      ),
    ),

    h('div',{style:{display:'flex',gap:'10px',justifyContent:'flex-end',marginTop:'8px'}},
      h('button',{className:'btn-ghost',onClick:()=>set({devisPreview:null})},'Annuler'),
      h('button',{className:'btn-sm',onClick:()=>{
        const body={};
        Object.entries(inputs).forEach(([k,el])=>{
          body[k]=el.type==='number'?parseFloat(el.value)||0:el.value;
        });
        body.filename=preview.filename;
        saveDevis(body);
      }},'✓ Enregistrer le devis')
    )
  );
}

function renderComparaison(comp){
  if(!comp) return null;
  if(comp.message) return h('div',{className:'card-empty'},comp.message);

  const {theorique:th,reel:re,ecarts:ec,conclusion:co,devis:dv,dossiers}=comp;

  const ROWS=[
    {label:'⏱ Temps calage',     unit:'mn',  key:'temps_calage_mn', invert:true},
    {label:'▶ Temps production', unit:'mn',  key:'temps_production_mn', invert:true},
    {label:'📏 Métrage',         unit:'ml',  key:'metrage_ml'},
    {label:'🏷 Qté étiquettes',  unit:'ex',  key:'qte_etiquettes'},
    {label:'⚡ Vitesse',         unit:'m/mn',key:'vitesse'},
    {label:'⚡ Vitesse + calage',unit:'m/mn',key:'vitesse_avec_calage'},
  ];

  const fN2=v=>v!=null?Number(v).toLocaleString('fr-FR',{maximumFractionDigits:1}):'-';
  const ecartEl=(key,invert)=>{
    const v=ec[key];
    if(!v)return h('span',{className:'ecart-neu'},'—');
    const num=parseFloat(v);
    const good = invert ? num<0 : num>0;
    return h('span',{className:good?'ecart-pos':'ecart-neg'},v);
  };

  const colMap={success:'var(--success)',warn:'var(--warn)',danger:'var(--danger)'};
  const concl=h('div',{className:'conclusion-card',
    style:{borderColor:colMap[co.color]+'66',background:colMap[co.color]+'0D'}},
    h('div',null,
      h('div',{className:'conclusion-label',style:{color:colMap[co.color]}},co.label),
      h('div',{className:'conclusion-sub'},'Dossier'+(dossiers.length>1?'s':'')+' : '+dossiers.join(', '))
    )
  );

  const table=h('div',{style:{overflowX:'auto'}},
    h('table',{className:'compa-table'},
      h('thead',null,h('tr',null,
        h('th',null,'Indicateur'),
        h('th',null,'Unité'),
        h('th',null,'📋 Devis (théorique)'),
        h('th',null,'🏭 Réel'),
        h('th',null,'Écart'),
      )),
      h('tbody',null,...ROWS.map(row=>h('tr',null,
        h('td',{className:'compa-row-label'},row.label),
        h('td',{style:{color:'var(--muted)',fontSize:'11px'}},row.unit),
        h('td',{className:'compa-val-theo'},fN2(th[row.key])),
        h('td',{className:'compa-val-reel'},fN2(re[row.key])),
        h('td',null,ecartEl(row.key,row.invert||false)),
      )))
    )
  );

  return h('div',null,concl,
    h('div',{className:'card'},
      h('div',{className:'card-header'},
        h('h3',null,'Comparaison Devis / Réel'),
        h('span',{style:{fontSize:'11px',color:'var(--muted)'}},(dv.client||'')+' — '+(dv.filename||''))
      ),
      table
    )
  );
}

function renderLiaisonDossiers(devisId, dossiersLies, allDossiers){
  let current=[...dossiersLies];
  const wrap=h('div',null);
  const refresh=()=>{
    wrap.innerHTML='';
    const chips=h('div',{style:{marginBottom:'8px'}},
      ...current.map(d=>h('span',{className:'dos-chip'},
        'Dos. '+d,
        h('button',{onClick:()=>{current=current.filter(x=>x!==d);refresh();}},'×')
      ))
    );
    const sel=h('select',null,
      h('option',{value:''},'+ Ajouter un dossier'),
      ...allDossiers.filter(d=>!current.includes(d)).map(d=>h('option',{value:d},'Dos. '+d))
    );
    sel.addEventListener('change',()=>{
      if(sel.value&&!current.includes(sel.value)){
        current.push(sel.value);sel.value='';refresh();
      }
    });
    const saveBtn=h('button',{className:'btn-sm',onClick:()=>linkDossiers(devisId,current)},'💾 Enregistrer les liaisons');
    wrap.appendChild(h('div',null,chips,h('div',{className:'dos-add-row'},sel,saveBtn)));
  };
  refresh();
  return wrap;
}



function renderRentabilite(){
  const list = S.rentList || [];
  const devisList = S.devisList || [];

  const tags = Array.isArray(S.rentTags) ? S.rentTags : [];
  const q = String(S.rentQuery||'').trim().toLowerCase();

  function norm(x){return String(x||'').toLowerCase().trim();}
  function fmtFormat(e){
    const l=e.format_l!=null?String(e.format_l):'';
    const h=e.format_h!=null?String(e.format_h):'';
    if(!l&&!h) return '';
    return l+'×'+h;
  }

  // Suggestions (machines, clients, refs, format, laize, date)
  const pool=[];
  const pushSug=(kind,value,label)=>{
    if(!value) return;
    const k=kind+'|'+String(value);
    if(pool.some(x=>x._k===k)) return;
    pool.push({_k:k,kind,value,label});
  };
  list.forEach(e=>{
    pushSug('machine', e.machine_nom||e.machine_code, e.machine_nom||e.machine_code);
    if(e.reference) pushSug('ref', e.reference, e.reference);
    if(e.client) pushSug('client', e.client, e.client);
    const ff=fmtFormat(e); if(ff) pushSug('format', ff, 'Format '+ff);
    if(e.laize!=null && String(e.laize)!=='') pushSug('laize', String(e.laize), 'Laize '+String(e.laize));
    if(e.date_livraison) pushSug('date', e.date_livraison, 'Livraison '+e.date_livraison);
  });

  const kindLabel = {machine:'Machine',client:'Client',ref:'Dossier',format:'Format',laize:'Laize',date:'Date'};
  const kindOrder = {machine:0,client:1,ref:2,format:3,laize:4,date:5};
  const filteredSuggestions = q
    ? pool
        .filter(s=>norm(s.label).includes(q) || norm(s.value).includes(q))
        .sort((a,b)=>{
          const ka = (kindOrder[a.kind]!=null)?kindOrder[a.kind]:99;
          const kb = (kindOrder[b.kind]!=null)?kindOrder[b.kind]:99;
          if(ka!==kb) return ka-kb;
          return String(a.label||'').localeCompare(String(b.label||''), 'fr', {sensitivity:'base'});
        })
        .slice(0,12)
    : [];

  function addTag(sug){
    const exists = tags.some(t=>t.kind===sug.kind && String(t.value)===String(sug.value));
    if(exists) return;
    set({rentTags:[...tags,{kind:sug.kind,value:sug.value,label:sug.label}],rentQuery:'',rentOffset:0});
  }
  function removeTag(i){
    const nt=tags.slice(); nt.splice(i,1);
    set({rentTags:nt,rentOffset:0});
  }

  // Group split entries by group_id (same dossier). Display group row.
  const groups = {};
  list.forEach(e=>{
    const gid = String(e.group_id||e.id);
    if(!groups[gid]) groups[gid]=[];
    groups[gid].push(e);
  });
  const groupList = Object.entries(groups).map(([group_id, entries])=>{
    entries.sort((a,b)=>Number(a.position||0)-Number(b.position||0));
    const head=entries[0];
    return {group_id, entries, head};
  });

  function matchesTags(g){
    for(const t of tags){
      const head=g.head;
      if(t.kind==='machine'){
        const v = norm(head.machine_nom||head.machine_code);
        if(!v.includes(norm(t.value))) return false;
      }else if(t.kind==='ref'){
        if(!norm(head.reference).includes(norm(t.value))) return false;
      }else if(t.kind==='client'){
        const v = norm(head.client);
        if(!v.includes(norm(t.value))) return false;
      }else if(t.kind==='format'){
        if(norm(fmtFormat(head))!==norm(t.value)) return false;
      }else if(t.kind==='laize'){
        if(norm(String(head.laize||''))!==norm(String(t.value))) return false;
      }else if(t.kind==='date'){
        if(norm(head.date_livraison)!==norm(t.value)) return false;
      }
    }
    return true;
  }

  const shown = groupList.filter(matchesTags);
  const totalShown = shown.length;
  const lim = Number(S.rentLimit||12) || 12;
  const off = Math.max(0, Number(S.rentOffset||0) || 0);
  const pageStart = Math.min(totalShown, off);
  const pageEnd = Math.min(totalShown, off + lim);
  const shownPage = shown.slice(pageStart, pageEnd);

  const searchBox = (()=>{
    const wrap=h('div',{className:'card',style:{padding:'12px 14px',marginBottom:'14px'}});
    const row=h('div',{style:{display:'flex',gap:'10px',alignItems:'center',flexWrap:'wrap'}});
    const inp=h('input',{type:'text',placeholder:'Rechercher (machine, dossier, format, client, date, laize)…',value:S.rentQuery||'',style:{flex:'1',minWidth:'260px'}});
    inp.addEventListener('input',()=>set({rentQuery:inp.value}));
    const chips=h('div',{style:{display:'flex',gap:'8px',flexWrap:'wrap'}},
      ...tags.map((t,i)=>h('span',{className:'dos-chip',style:{display:'inline-flex',alignItems:'center',gap:'6px'}},
        t.label,
        h('button',{onClick:()=>removeTag(i)},'×')
      ))
    );
    row.appendChild(inp);
    wrap.appendChild(row);
    if(tags.length) wrap.appendChild(h('div',{style:{marginTop:'10px'}},chips));
    if(filteredSuggestions.length){
      const dd=h('div',{style:{marginTop:'10px',display:'flex',gap:'8px',flexWrap:'wrap'}},
        ...filteredSuggestions.map(s=>h('button',{type:'button',className:'btn-sec',onClick:()=>addTag(s)},
          (kindLabel[s.kind]? (kindLabel[s.kind]+' · ') : ''),
          s.label
        ))
      );
      wrap.appendChild(dd);
    }
    return wrap;
  })();

  function getLink(entryId){
    const m = (S.rentLinksById||{})[entryId];
    return m || {devis_id:null,no_dossiers:[]};
  }

  // In-flight de-duplication: évite de lancer 2x la même requête si ensureLinks est appelé
  // depuis le clic + le prefetch simultanément.
  if(!window._rentLinksPending) window._rentLinksPending = {};
  async function ensureLinks(entryId){
    const mp = S.rentLinksById || {};
    if(mp[entryId]) return mp[entryId];
    const key = String(entryId);
    if(window._rentLinksPending[key]) return window._rentLinksPending[key];
    const p = api('/api/rentabilite/links/'+entryId).then(d=>{
      delete window._rentLinksPending[key];
      const entry = {devis_id:d.devis_id||null,no_dossiers:d.no_dossiers||[]};
      S.rentLinksById = {...(S.rentLinksById||{}), [entryId]:entry};
      render();
      return entry;
    }).catch(e=>{
      delete window._rentLinksPending[key];
      throw e;
    });
    window._rentLinksPending[key] = p;
    return p;
  }

  async function saveLinks(entryId, devis_id, no_dossiers){
    await api('/api/rentabilite/links/'+entryId,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({devis_id,no_dossiers})});
    const mp = S.rentLinksById || {};
    set({rentLinksById:{...mp,[entryId]:{devis_id:devis_id||null,no_dossiers:no_dossiers||[]}}});
    toast('Liaisons enregistrées');
  }

  async function loadRentComparaison(entryId){
    const d = await api('/api/rentabilite/planning/'+entryId+'/comparaison');
    const mp = S.rentCompById || {};
    set({rentCompById:{...mp,[entryId]:d}});
  }

  async function rentSuggestNoDossiers(q){
    try{
      const qq=String(q||'').trim();
      if(!qq) return [];
      const d = await api('/api/rentabilite/no-dossiers?q='+encodeURIComponent(qq)+'&limit=12');
      return Array.isArray(d)?d:[];
    }catch(e){return [];}
  }

  function renderPanel(g){
    const head=g.head;
    const entryId = Number(head.id);
    const panel=h('div',{style:{borderLeft:'3px solid var(--accent)',background:'rgba(34,211,238,.04)',padding:'16px 20px',marginBottom:'2px'}});

    // Links editor
    const linkState = getLink(entryId);
    const curDevis = linkState.devis_id;
    let curDossiers = (linkState.no_dossiers||[]).slice();

    const devisSel=h('select',{className:'form-sel',style:{minWidth:'280px'}},
      h('option',{value:''},'Relier à un devis existant…'),
      ...devisList.map(dv=>{
        const opt=h('option',{value:String(dv.id)},(dv.client||dv.filename||('Devis #'+dv.id))+' (#'+dv.id+')');
        if(curDevis && Number(curDevis)===Number(dv.id)) opt.selected=true;
        return opt;
      })
    );
    devisSel.addEventListener('change',()=>{ /* local */ });

    const dosInput=h('input',{type:'text',placeholder:'Ajouter un n° dossier production (ex: 1003/0002)…',style:{minWidth:'260px'}});
    const dosSugWrap=h('div',{style:{display:'none',gap:'8px',flexWrap:'wrap'}});
    let dosSugToken=0;
    const refreshDosSug=async()=>{
      const v=String(dosInput.value||'').trim();
      const tok=++dosSugToken;
      if(v.length<2){ dosSugWrap.style.display='none'; dosSugWrap.innerHTML=''; return; }
      const sugs=await rentSuggestNoDossiers(v);
      if(tok!==dosSugToken) return;
      dosSugWrap.innerHTML='';
      if(!sugs.length){ dosSugWrap.style.display='none'; return; }
      dosSugWrap.style.display='flex';
      sugs.slice(0,8).forEach(s=>{
        dosSugWrap.appendChild(h('button',{type:'button',className:'btn-sec',onClick:()=>{
          const vv=String(s||'').trim();
          if(vv && !curDossiers.includes(vv)){curDossiers.push(vv);refreshChips();}
          dosInput.value='';
          dosSugWrap.style.display='none';
          dosSugWrap.innerHTML='';
        }},s));
      });
    };
    dosInput.addEventListener('input',()=>{ refreshDosSug(); });
    const addDosBtn=h('button',{type:'button',className:'btn-sec',onClick:()=>{
      const v=String(dosInput.value||'').trim();
      if(!v) return;
      if(!curDossiers.includes(v)){curDossiers.push(v);refreshChips();}
      dosInput.value='';
      dosSugWrap.style.display='none';
      dosSugWrap.innerHTML='';
    }},'+ Ajouter');

    const chipsWrap=h('div',{style:{display:'flex',gap:'8px',flexWrap:'wrap'}});
    const refreshChips=()=>{
      chipsWrap.innerHTML='';
      curDossiers.forEach((d,i)=>{
        chipsWrap.appendChild(h('span',{className:'dos-chip'},'Dos. '+d,h('button',{onClick:()=>{curDossiers.splice(i,1);refreshChips();}},'×')));
      });
    };
    refreshChips();

    // Auto-détection : si aucun dossier n'est lié, chercher dans la prod via la référence planning
    if(curDossiers.length===0 && (head.reference||'').trim()){
      queueMicrotask(async()=>{
        try{
          const sugs = await rentSuggestNoDossiers((head.reference||'').trim());
          if(sugs.length && curDossiers.length===0){
            sugs.forEach(s=>{ if(!curDossiers.includes(s)) curDossiers.push(s); });
            refreshChips();
          }
        }catch(_){}
      });
    }

    const saveBtn=h('button',{type:'button',className:'btn-sm',onClick:async()=>{
      const did = devisSel.value ? Number(devisSel.value) : null;
      await saveLinks(entryId, did, curDossiers);
      await loadRentComparaison(entryId).catch(()=>{});
    }},'💾 Enregistrer');

    const compBtn=h('button',{type:'button',className:'btn-sec',onClick:async()=>{
      await ensureLinks(entryId);
      await loadRentComparaison(entryId);
    }},'Comparer');

    // Import devis: keep existing workflow (creates devis + links via old devis_dossiers)
    // For v2, we still allow import, then we set rent_links.devis_id to the created devis.
    const dz=h('div',{className:'drop-zone',style:{padding:'20px',marginTop:'12px'}},
      h('div',{className:'dz-icon',style:{fontSize:'24px'}},'📄'),
      h('div',{className:'dz-title',style:{fontSize:'13px'}},'Importer un devis (Excel)'),
      h('div',{className:'dz-sub'},'Le devis pourra être lié à cette ligne rentabilité')
    );
    const dzInp=h('input',{type:'file',accept:'.xlsx,.xls',style:{display:'none'}});
    dzInp.addEventListener('change',async e=>{
      const f=(e && e.target && e.target.files && e.target.files[0]) ? e.target.files[0] : null;
      if(!f) return;
      try{
        const fd=new FormData();fd.append('file',f);
        const preview=await api('/api/rentabilite/devis/import',{method:'POST',body:fd});
        if(!preview||!preview.preview) return toast('Erreur import','error');
        const r=await api('/api/rentabilite/devis',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...preview.preview,filename:f.name})});
        if(!r||!r.devis_id) return toast('Erreur sauvegarde devis','error');
        // Link in rent_links
        await saveLinks(entryId, Number(r.devis_id), curDossiers);
        toast('Devis importé');
        await loadDevis();
        await loadRentComparaison(entryId).catch(()=>{});
      }catch(err){toast(err.message,'error');}
    });
    dz.addEventListener('click',()=>dzInp.click());
    dz.addEventListener('dragover',e=>{e.preventDefault();dz.classList.add('drag');});
    dz.addEventListener('dragleave',()=>dz.classList.remove('drag'));
    dz.addEventListener('drop',e=>{
      e.preventDefault();dz.classList.remove('drag');
      const f=(e && e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) ? e.dataTransfer.files[0] : null;
      if(!f) return;
      dzInp.files=e.dataTransfer.files;
      dzInp.dispatchEvent(new Event('change'));
    });
    panel.appendChild(h('div',{className:'form-section-title'},'🔗 Liaisons'));
    panel.appendChild(h('div',{style:{display:'flex',gap:'10px',flexWrap:'wrap',alignItems:'center'}},devisSel,dosInput,addDosBtn,saveBtn,compBtn));
    panel.appendChild(h('div',{style:{marginTop:'10px'}},dosSugWrap));
    panel.appendChild(h('div',{style:{marginTop:'10px'}},chipsWrap));
    panel.appendChild(dz);
    panel.appendChild(dzInp);

    const comp = (S.rentCompById||{})[entryId];
    if(comp){
      if(comp.reel) panel.appendChild(renderComparaison(comp));
      else panel.appendChild(h('div',{className:'card-empty',style:{padding:'18px'}},comp.message||'Aucune donnée.'));
    }else{
      panel.appendChild(h('div',{className:'card-empty',style:{padding:'18px'}},'Clique sur “Comparer” après avoir lié un devis + des dossiers production.'));
    }
    return panel;
  }

  const rows = shownPage.map(g=>{
    const head=g.head;
    const isExp = String(S.rentSelEntryId||'')===String(head.id);
    const topLine = [
      (head.client||'').trim(),
      (fmtFormat(head)?(fmtFormat(head)+' mm'):''),
      (head.reference||'').trim()
    ].filter(Boolean).join(' - ') || (head.reference||'(sans référence)');
    const subBits = [
      (head.machine_nom||'').trim(),
      (head.duree_heures!=null?('durée '+String(head.duree_heures)+'h'):''),
      (head.laize!=null?('laize '+head.laize):''),
      (head.date_livraison?('date '+head.date_livraison):'')
    ].filter(Boolean);

    const link = (S.rentLinksById||{})[Number(head.id)] || null;
    const devisLinked = link ? !!link.devis_id : null;
    const prodLinked = link ? ((link.no_dossiers||[]).length>0) : null;
    const stRaw = String(head.statut||'attente');
    const stLbl = (stRaw==='en_cours')?'En cours':(stRaw==='termine')?'Terminé':'En attente';
    const stCol = (stRaw==='termine')?'var(--success)':(stRaw==='en_cours')?'var(--warn)':'var(--muted)';
    const mkBadge=(txt, okNull, okCol, noCol)=>{
      const isOk = okNull===true;
      const isNo = okNull===false;
      const col = isOk?okCol:(isNo?noCol:'var(--muted)');
      const bg = isOk?(okCol+'1A'):(isNo?(noCol+'1A'):'rgba(100,116,139,.10)');
      return h('span',{style:{fontSize:'10px',fontWeight:'800',color:col,background:bg,border:'1px solid '+(col+'33'),padding:'3px 8px',borderRadius:'999px',whiteSpace:'nowrap'}},txt);
    };
    const row = h('div',{
      className:'dossier-row',
      style:{cursor:'pointer',background:isExp?'var(--accent-bg)':'',
             borderLeft:isExp?'3px solid var(--accent)':'3px solid transparent',
             transition:'all .15s'},
      onClick:async()=>{
        const next = isExp ? null : head.id;
        set({rentSelEntryId:next});
        if(next){
          await ensureLinks(Number(next)).catch(()=>{});
        }
      }
    },
      h('div',{style:{flex:'1',minWidth:0}},
        h('div',{style:{fontWeight:'700',color:'var(--text)',fontSize:'13px'}},topLine),
        h('div',{style:{fontSize:'11px',color:'var(--muted)',marginTop:'2px'}},
          subBits.length?subBits.join(' — '):'—')
      ),
      h('div',{style:{display:'flex',alignItems:'center',gap:'10px',flexShrink:0}},
        h('div',{style:{display:'flex',flexDirection:'column',alignItems:'flex-end',gap:'6px'}},
          mkBadge(stLbl, true, stCol, stCol),
          mkBadge(devisLinked===null?'Devis …':(devisLinked?'Devis lié':'Devis non lié'), devisLinked, 'var(--success)', 'var(--danger)'),
          (stRaw==='termine')
            ? mkBadge(prodLinked===null?'Prod …':(prodLinked?'Prod liée':'Prod non liée'), prodLinked, 'var(--success)', 'var(--danger)')
            : null
        ),
        h('span',{style:{fontSize:'14px',color:'var(--muted)',transition:'transform .15s',
          transform:isExp?'rotate(180deg)':'rotate(0deg)'}},'▾')
      )
    );
    if(!isExp) return row;
    return h('div',null,row,renderPanel(g));
  });

  // Précharger les liens avec une concurrence max de 3 pour ne pas saturer le navigateur.
  try{
    const CONCURRENCY = 3;
    const toFetch = shownPage
      .map(g=>Number(g.head&&g.head.id))
      .filter(id=>id && !(S.rentLinksById||{})[id] && !((window._rentLinksPending||{})[id]));
    if(toFetch.length){
      queueMicrotask(async()=>{
        let i = 0;
        async function runNext(){
          if(i >= toFetch.length) return;
          const id = toFetch[i++];
          await ensureLinks(id).catch(()=>{});
          await runNext();
        }
        const workers = Array.from({length:Math.min(CONCURRENCY,toFetch.length)},()=>runNext());
        await Promise.allSettled(workers);
      });
    }
  }catch(e){}

  const pager=h('div',{style:{display:'inline-flex',alignItems:'center',gap:'6px'}},
    h('button',{className:'btn-ghost',title:'Page précédente',disabled:off<=0,onClick:()=>{
      set({rentOffset:Math.max(0, off - lim)});
    }},'‹'),
    h('span',{style:{fontSize:'11px',color:'var(--muted)',fontFamily:'monospace'}},
      totalShown?(`${pageStart+1}-${pageEnd}/${totalShown}`):'0'
    ),
    h('button',{className:'btn-ghost',title:'Page suivante',disabled:(off+lim)>=totalShown,onClick:()=>{
      set({rentOffset:Math.min(Math.max(0,totalShown-lim), off + lim)});
    }},'›'),
  );

  return h('div',null,
    searchBox,
    h('div',{className:'card'},
      h('div',{className:'card-header'},
        h('h3',null,'Rentabilité — Dossiers planning ('+totalShown+')'),
        h('div',{style:{display:'flex',gap:'10px',alignItems:'center',flexWrap:'wrap'}},
          pager,
          h('button',{type:'button',className:'btn-sec',onClick:async()=>{await loadRentPlanning();toast('Planning rechargé');}},'Rafraîchir')
        )
      ),
      rows.length? h('div',null,...rows) : h('div',{className:'card-empty'},'Aucun dossier ne correspond aux filtres.')
    )
  );
}

// ── Suivi (fusion Dossiers + Rentabilité) ─────────────────────────
function renderSuivi(){
  const admin = isAdmin(S.user);
  const dos = S.dossiers || [];
  const devisList = S.devisList || [];
  const parts = [];

  if(admin){
    const refI=h('input',{type:'text',placeholder:'Référence *',style:{width:'160px'}});
    const cliI=h('input',{type:'text',placeholder:'Client',style:{flex:'1'}});
    const desI=h('input',{type:'text',placeholder:'Description',style:{flex:'2'}});
    const btnC=h('button',{className:'btn-sm',onClick:()=>{
      if(!refI.value)return toast('Référence requise','error');
      createDos({reference:refI.value,client:cliI.value,description:desI.value});
      refI.value='';cliI.value='';desI.value='';
    }},'+ Nouveau dossier');
    parts.push(h('div',{className:'card',style:{padding:'16px',marginBottom:'16px'}},
      h('div',{className:'form-section-title'},'Nouveau dossier'),
      h('div',{style:{display:'flex',gap:'8px',flexWrap:'wrap',alignItems:'center'}},
        refI,cliI,desI,btnC)
    ));
  }

  if(!dos.length){
    parts.push(h('div',{className:'card-empty'},'Aucun dossier.'));
    return h('div',null,...parts);
  }

  const statMap={devis:'📋 Devis',en_cours:'▶ En cours',termine:'✅ Terminé',annule:'⛔ Annulé',archive:'🗄 Archivé'};
  const statChoices=['devis','en_cours','termine','archive','annule'];

  const rows = dos.map(d=>{
    const isExp = S.selDossier===d.id;
    const row = h('div',{
      className:'dossier-row',
      style:{cursor:'pointer',background:isExp?'var(--accent-bg)':'',
             borderLeft:isExp?'3px solid var(--accent)':'3px solid transparent',
             transition:'all .15s'},
      onClick:async()=>{
        if(isExp){set({selDossier:null,selDevis:null,comparaison:null});}
        else{set({selDossier:d.id,selDevis:null,comparaison:null});}
      }
    },
      h('div',{style:{flex:'1',minWidth:0}},
        h('div',{style:{fontWeight:'600',color:'var(--text)',fontSize:'13px'}},d.reference),
        h('div',{style:{fontSize:'11px',color:'var(--muted)',marginTop:'2px'}},
          [d.client,d.description].filter(Boolean).join(' — ')||'—')
      ),
      h('div',{style:{display:'flex',alignItems:'center',gap:'10px',flexShrink:0}},
        admin?h('select',{
          className:'form-sel',
          style:{fontSize:'11px',padding:'4px 8px'},
          onClick:e=>e.stopPropagation(),
          onChange:e=>{e.stopPropagation();updStatut(d.id,e.target.value);}
        },
          ...statChoices.map(s=>{
            const opt=h('option',{value:s},statMap[s]||s);
            if(d.statut===s)opt.selected=true;
            return opt;
          })
        ):h('span',{style:{fontSize:'11px',color:'var(--text2)'}},statMap[d.statut]||d.statut||''),
        h('span',{style:{fontSize:'14px',color:'var(--muted)',transition:'transform .15s',
          transform:isExp?'rotate(180deg)':'rotate(0deg)'}},'▾')
      )
    );

    if(!isExp) return row;

    const panel = h('div',{style:{
      borderLeft:'3px solid var(--accent)',background:'rgba(34,211,238,.04)',
      padding:'16px 20px',marginBottom:'2px'
    }});

    // Import devis (admin)
    if(admin){
      const dz=h('div',{className:'drop-zone',style:{padding:'20px',marginBottom:'12px'}},
        h('div',{className:'dz-icon',style:{fontSize:'24px'}},'📄'),
        h('div',{className:'dz-title',style:{fontSize:'13px'}},'Importer un devis (Excel)'),
        h('div',{className:'dz-sub'},'Le devis sera lié au dossier '+d.reference)
      );
      const dzInp=h('input',{type:'file',accept:'.xlsx,.xls',style:{display:'none'}});
      dzInp.addEventListener('change',async e=>{
        const f=(e && e.target && e.target.files && e.target.files[0]) ? e.target.files[0] : null;
        if(!f)return;
        try{
          const fd=new FormData();fd.append('file',f);
          const preview=await api('/api/rentabilite/devis/import',{method:'POST',body:fd});
          if(!preview||!preview.preview)return toast('Erreur import','error');
          const r=await api('/api/rentabilite/devis',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...preview.preview,filename:f.name})});
          if(!r||!r.devis_id)return toast('Erreur sauvegarde devis','error');
          await api('/api/rentabilite/devis/'+r.devis_id+'/dossiers',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({dossiers:[d.reference]})});
          toast('Devis importé et lié à '+d.reference);
          await loadDevis();
          await loadComparaison(r.devis_id);
          set({selDevis:r.devis_id});
        }catch(err){toast(err.message,'error');}
      });
      dz.addEventListener('click',()=>dzInp.click());
      dz.addEventListener('dragover',e=>{e.preventDefault();dz.classList.add('drag');});
      dz.addEventListener('dragleave',()=>dz.classList.remove('drag'));
      dz.addEventListener('drop',e=>{
        e.preventDefault();dz.classList.remove('drag');
        const f=(e && e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) ? e.dataTransfer.files[0] : null;
        if(!f)return;
        dzInp.files=e.dataTransfer.files;
        dzInp.dispatchEvent(new Event('change'));
      });
      panel.appendChild(dz);
      panel.appendChild(dzInp);
    }

    // Liaison manuelle à un devis existant
    const sel=h('select',{className:'form-sel',style:{minWidth:'280px'}},
      h('option',{value:''},'Lier un devis existant…'),
      ...devisList.map(dv=>h('option',{value:String(dv.id)},(dv.client||dv.filename||('Devis #'+dv.id))+' (#'+dv.id+')'))
    );
    const linkBtn=h('button',{className:'btn-sm',onClick:async()=>{
      const id=Number(sel.value||0);
      if(!id)return toast('Choisis un devis','warn');
      try{
        await api('/api/rentabilite/devis/'+id+'/dossiers',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({dossiers:[d.reference]})});
        toast('Devis lié à '+d.reference);
        await loadDevis();
        set({selDevis:id});
        await loadComparaison(id);
      }catch(e){toast(e.message,'error');}
    }},'🔗 Lier');
    panel.appendChild(h('div',{style:{display:'flex',gap:'10px',flexWrap:'wrap',alignItems:'center',marginBottom:'12px'}},sel,linkBtn));

    // Comparaison
    if(S.selDevis && S.comparaison){
      if(S.comparaison.reel) panel.appendChild(renderComparaison(S.comparaison));
      else panel.appendChild(h('div',{className:'card-empty',style:{padding:'18px'}},'📂 Aucune donnée de production correspondante pour ce dossier'));
      panel.appendChild(h('button',{className:'btn-danger',style:{marginTop:'10px'},onClick:()=>deleteDevis(S.selDevis)},'🗑 Supprimer ce devis'));
    } else {
      panel.appendChild(h('div',{className:'card-empty',style:{padding:'18px'}},'Liez/importez un devis pour afficher la comparaison.'));
    }

    return h('div',null,row,panel);
  });

  parts.push(h('div',{className:'card'},
    h('div',{className:'card-header'},
      h('h3',null,'Dossiers ('+dos.length+')')
    ),
    ...rows
  ));

  return h('div',null,...parts);
}



// ══════════════════════════════════════════════════════════════════
// Google search — modal centré avec animation depuis le bouton
// ══════════════════════════════════════════════════════════════════
const _gsmRecentsKey='mysifa_google_recents_v1';
function _gsmLoadRecents(){
  try{const r=JSON.parse(localStorage.getItem(_gsmRecentsKey)||'[]');return Array.isArray(r)?r.slice(0,5):[];}catch(_){return [];}
}
function _gsmSaveRecent(q){
  try{
    const list=_gsmLoadRecents().filter(x=>x!==q);
    list.unshift(q);
    localStorage.setItem(_gsmRecentsKey,JSON.stringify(list.slice(0,5)));
  }catch(_){}
}
function _gsmEsc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');}
function _gsmRun(q){
  const query=String(q||'').trim();
  if(!query)return;
  _gsmSaveRecent(query);
  try{fetch('/api/portal/google-search',{method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify({q:query})}).catch(()=>{});}catch(e){}
  window.open('https://www.google.com/search?q='+encodeURIComponent(query),'_blank','noopener');
  closeGoogleSearch();
}
function openGoogleSearch(originEl){
  const modal=document.getElementById('gsm-modal');
  const bd=document.getElementById('gsm-backdrop');
  if(!modal||!bd)return;
  const recents=_gsmLoadRecents();
  const recentsHtml=recents.length?(
    '<div class="gsm-recents">'+
      '<div class="gsm-recents-label">Recherches récentes</div>'+
      '<div class="gsm-recents-chips">'+recents.map(q=>(
        '<button type="button" class="gsm-recent-chip" data-gsm-recent="'+_gsmEsc(q)+'">'+
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 15 15"/></svg>'+
          '<span class="gsm-recent-chip-text">'+_gsmEsc(q)+'</span>'+
        '</button>'
      )).join('')+'</div>'+
    '</div>'
  ):'';
  modal.innerHTML=
    '<div class="gsm-modal-head">'+
      '<span class="gsm-modal-logo">'+
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="28" height="28"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>'+
      '</span>'+
      '<div class="gsm-modal-title">Rechercher sur Google</div>'+
      '<button type="button" class="gsm-modal-close" aria-label="Fermer">'+
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>'+
      '</button>'+
    '</div>'+
    '<form class="gsm-form" autocomplete="off">'+
      '<div class="gsm-input-wrap">'+
        '<span class="gsm-input-search-ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg></span>'+
        '<input class="gsm-input" type="search" autocomplete="off" spellcheck="false" placeholder="Tapez votre recherche…">'+
      '</div>'+
      '<div class="gsm-hint"><span><kbd>Entrée</kbd> Rechercher</span><span><kbd>Esc</kbd> Fermer</span></div>'+
    '</form>'+
    recentsHtml;

  // Animation d'origine : partir de la position du bouton pour le premier frame
  if(originEl){
    const r=originEl.getBoundingClientRect();
    const cx=r.left+r.width/2,cy=r.top+r.height/2;
    const vx=window.innerWidth/2,vy=window.innerHeight/2;
    const dx=cx-vx,dy=cy-vy;
    modal.style.transformOrigin=(vx+dx)+'px '+(vy+dy)+'px';
    // On force scale plus petit + translation depuis le bouton
    modal.style.transform='translate(-50%,-50%) translate('+dx+'px,'+dy+'px) scale(.35)';
  }
  bd.classList.add('open');
  bd.setAttribute('aria-hidden','false');
  // Reset transform pour laisser la transition CSS jouer vers le centre
  requestAnimationFrame(()=>{
    modal.style.transform='';
    modal.classList.add('open');
    modal.setAttribute('aria-hidden','false');
    const inp=modal.querySelector('.gsm-input');
    if(inp)setTimeout(()=>inp.focus(),20);
  });

  // Handlers
  bd.onclick=closeGoogleSearch;
  const closeBtn=modal.querySelector('.gsm-modal-close');
  if(closeBtn)closeBtn.onclick=(e)=>{e.preventDefault();closeGoogleSearch();};
  const form=modal.querySelector('.gsm-form');
  if(form)form.onsubmit=(e)=>{e.preventDefault();const inp=modal.querySelector('.gsm-input');_gsmRun(inp?inp.value:'');};
  modal.querySelectorAll('[data-gsm-recent]').forEach(chip=>{
    chip.addEventListener('click',(e)=>{e.preventDefault();_gsmRun(chip.getAttribute('data-gsm-recent'));});
  });
  // Esc global
  const _escHandler=(e)=>{if(e.key==='Escape'){e.preventDefault();closeGoogleSearch();document.removeEventListener('keydown',_escHandler,true);}};
  document.addEventListener('keydown',_escHandler,true);
  modal._gsmEscHandler=_escHandler;
}
function closeGoogleSearch(){
  const modal=document.getElementById('gsm-modal');
  const bd=document.getElementById('gsm-backdrop');
  if(!modal||!bd)return;
  modal.classList.remove('open');
  bd.classList.remove('open');
  modal.setAttribute('aria-hidden','true');
  bd.setAttribute('aria-hidden','true');
  if(modal._gsmEscHandler){try{document.removeEventListener('keydown',modal._gsmEscHandler,true);}catch(_){}modal._gsmEscHandler=null;}
  setTimeout(()=>{modal.innerHTML='';modal.style.transform='';modal.style.transformOrigin='';},220);
}

// ══════════════════════════════════════════════════════════════════
// Mobile bottom nav bar — Accueil / Changer d'app / Messagerie / Agent IA
// Rendue à chaque render() sur mobile portrait uniquement.
// ══════════════════════════════════════════════════════════════════
function _mnbInitials(nom){
  if(!nom) return 'EL';
  const parts=String(nom).trim().split(/\s+/).filter(Boolean);
  if(!parts.length) return 'EL';
  if(parts.length===1) return parts[0].slice(0,2).toUpperCase();
  return (parts[0][0]+parts[parts.length-1][0]).toUpperCase();
}
function _mnbAiEnabled(){
  const AI_ROLES=['superadmin','direction','administration','expedition'];
  const role=(S.user&&S.user.role)||'';
  return AI_ROLES.indexOf(role)>=0;
}
function _mnbToggleAi(){
  // Le widget IA écoute document.click pour se fermer. Si on déclenche le clic du
  // FAB dans la même pile d'événements, l'event remonte au document et onDocClick
  // referme le panel aussitôt ouvert. On défère donc le clic dans setTimeout(0).
  const runClick=()=>{
    const btn=document.getElementById('ai-chat-btn');
    if(btn){btn.click();return;}
    if(typeof initAiChatWidget==='function'){
      initAiChatWidget();
      setTimeout(()=>{document.getElementById('ai-chat-btn')?.click();},50);
    }
  };
  setTimeout(runClick,0);
}
function _mnbOpenCmdK(){
  if(window.MysifaCmdK&&typeof window.MysifaCmdK.open==='function'){
    window.MysifaCmdK.open('');
  }
}
function renderMobileNavbar(){
  const root=document.getElementById('mobile-navbar-root');
  if(!root) return;
  // Login = pas de nav bar
  if(!S.user||S.app==='login'){
    root.innerHTML='';
    document.body.classList.remove('has-mobile-navbar');
    document.body.classList.add('mysifa-hide-navbar');
    return;
  }
  document.body.classList.remove('mysifa-hide-navbar');
  document.body.classList.add('has-mobile-navbar');
  // Force-hide widgets flottants sur portrait mobile (bypass CSS specificity)
  const _isPortraitMobile=window.matchMedia&&window.matchMedia('(max-width:900px) and (orientation:portrait)').matches;
  if(_isPortraitMobile){
    ['cw-bubble','cw-bar','ai-chat-btn'].forEach(id=>{
      const el=document.getElementById(id);
      if(el){el.style.setProperty('display','none','important');}
    });
    // Observer les futures apparitions (chat_widget s'auto-mount plus tard)
    if(!window.__MYSIFA_HIDE_WIDGETS_OBS__){
      window.__MYSIFA_HIDE_WIDGETS_OBS__=true;
      const hide=()=>{['cw-bubble','cw-bar','ai-chat-btn'].forEach(id=>{const el=document.getElementById(id);if(el)el.style.setProperty('display','none','important');});};
      const mo=new MutationObserver(()=>{if(window.matchMedia&&window.matchMedia('(max-width:900px) and (orientation:portrait)').matches)hide();});
      mo.observe(document.body,{childList:true,subtree:false});
    }
  }
  const isPortal=S.app==='portal';
  const isMessages=S.app==='messages';
  const isAiOn=!!(document.getElementById('ai-chat-panel')&&document.getElementById('ai-chat-panel').classList.contains('open'));
  const isCmdKOpen=!!(window.MysifaCmdK&&window.MysifaCmdK.isOpen&&window.MysifaCmdK.isOpen());
  const aiEnabled=_mnbAiEnabled();
  const msgUnread=Number(S.msgUnread||0);
  const ICO={
    home:'<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 10.5L12 3l9 7.5"/><path d="M5 10v11h14V10"/><path d="M10 21v-6h4v6"/></svg>',
    grid:'<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>',
    chat:'<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
    ai:'<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
  };
  function tab(id,ico,label,active,badge){
    const bdg=badge>0?('<span class="mobile-navbar-tab-badge">'+(badge>9?'9+':badge)+'</span>'):'';
    return '<button type="button" class="mobile-navbar-tab'+(active?' active':'')+'" data-nav="'+id+'" aria-label="'+label+'">'+
      '<span class="mobile-navbar-tab-ico">'+ico+bdg+'</span>'+
      '<span class="mobile-navbar-tab-label">'+label+'</span>'+
    '</button>';
  }
  const tabs=[
    tab('home',   ICO.home, 'Accueil',      isPortal, 0),
    tab('switch', ICO.grid, "Changer d'app", isCmdKOpen, 0),
    tab('msg',    ICO.chat, 'Messagerie',   isMessages, msgUnread),
  ];
  if(aiEnabled){
    tabs.push(tab('ai', ICO.ai, 'Agent IA', isAiOn, 0));
  }
  root.innerHTML='<nav class="mobile-navbar">'+tabs.join('')+'</nav>';
  root.querySelectorAll('.mobile-navbar-tab').forEach(btn=>{
    btn.addEventListener('click',(e)=>{
      e.preventDefault();
      e.stopPropagation();
      const id=btn.getAttribute('data-nav');
      if(id==='home'){
        if(S.app==='portal'){window.scrollTo({top:0,behavior:'smooth'});return;}
        window.location.href='/';
      } else if(id==='switch'){
        if(window.MysifaCmdK&&typeof window.MysifaCmdK.toggle==='function'){
          window.MysifaCmdK.toggle('');
        } else {
          _mnbOpenCmdK();
        }
        // Refresh l'état actif du tab après ouverture/fermeture
        setTimeout(()=>{try{renderMobileNavbar();}catch(_){}},60);
      } else if(id==='msg'){
        // Ouvre l'outil de chat (chat_widget), pas le module emails
        const trigger=document.getElementById('cw-bubble')||document.getElementById('cw-bar');
        if(trigger){trigger.click();return;}
        // Fallback si le chat n'est pas monté (utilisateur sans droit)
        if(S.app==='messages'){window.scrollTo({top:0,behavior:'smooth'});return;}
        set({app:'messages'});
        loadMessagesUnread().catch(()=>{});
        loadMessages().catch(()=>{});
      } else if(id==='ai'){
        _mnbToggleAi();
      }
    });
  });
}

// ══════════════════════════════════════════════════════════════════
// Bottom sheet profil (menu badge EL Eugène)
// ══════════════════════════════════════════════════════════════════
function _sheetRoles(){
  const role=(S.user&&S.user.role)||'';
  return {
    isSuper: role==='superadmin',
    isDir: role==='direction',
    isAdmin: role==='administration',
    role,
  };
}
function openProfileSheet(){
  const sheet=document.getElementById('msf-sheet-root');
  const bd=document.getElementById('msf-sheet-backdrop');
  if(!sheet||!bd) return;
  const {isSuper,isDir,isAdmin,role}=_sheetRoles();
  const nom=(S.user&&S.user.nom)||'';
  const initials=_mnbInitials(nom);
  const msgUnread=Number(S.msgUnread||0);
  const ICO={
    user:'<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
    sliders:'<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/></svg>',
    mail:'<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6h16v12H4z"/><path d="M4 7l8 6 8-6"/></svg>',
    calendar:'<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>',
    database:'<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14a9 3 0 0 0 18 0V5"/><path d="M3 12a9 3 0 0 0 18 0"/></svg>',
    logout:'<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>',
  };
  function item(id,ico,label,extra,klass){
    const badge=extra?('<span class="msf-sheet-item-badge">'+extra+'</span>'):'';
    return '<button type="button" class="msf-sheet-item'+(klass?' '+klass:'')+'" data-sheet="'+id+'">'+
      '<span class="msf-sheet-item-ico">'+ico+'</span>'+
      '<span class="msf-sheet-item-label">'+label+'</span>'+badge+
    '</button>';
  }
  const items=[];
  items.push(item('profil', ICO.user, 'Mon profil', ''));
  if(isSuper||isDir){
    items.push(item('settings', ICO.sliders, 'Paramètres', ''));
  }
  items.push(item('messagerie', ICO.mail, 'Messagerie', msgUnread>0?(msgUnread>9?'9+':String(msgUnread)):''));
  if(isSuper||isDir||isAdmin){
    items.push(item('calendrier', ICO.calendar, 'Calendrier', ''));
  }
  if(isSuper||isDir){
    items.push(item('db', ICO.database, 'Base de données', ''));
  }
  items.push('<div class="msf-sheet-sep"></div>');
  items.push(item('logout', ICO.logout, 'Déconnexion', '', 'danger'));

  sheet.innerHTML=
    '<div class="msf-sheet-handle"></div>'+
    '<div class="msf-sheet-user">'+
      '<div class="msf-sheet-user-avatar">'+initials+'</div>'+
      '<div class="msf-sheet-user-info">'+
        '<div class="msf-sheet-user-name">'+String(nom||'').replace(/</g,'&lt;')+'</div>'+
        '<div class="msf-sheet-user-role">'+String(role||'').replace(/</g,'&lt;')+'</div>'+
      '</div>'+
    '</div>'+
    '<div class="msf-sheet-list">'+items.join('')+'</div>';

  // Actions
  sheet.querySelectorAll('.msf-sheet-item').forEach(btn=>{
    btn.addEventListener('click',(e)=>{
      const id=btn.getAttribute('data-sheet');
      closeProfileSheet();
      if(id==='profil')      window.location.href='/profil';
      else if(id==='settings')window.location.href='/settings';
      else if(id==='messagerie'){set({app:'messages'});loadMessagesUnread().catch(()=>{});loadMessages().catch(()=>{});}
      else if(id==='calendrier')window.location.href='/calendrier';
      else if(id==='db')      window.location.href='/db';
      else if(id==='logout')  doLogout();
    });
  });
  // Ouverture animée
  bd.classList.add('open');
  bd.setAttribute('aria-hidden','false');
  requestAnimationFrame(()=>{sheet.classList.add('open');});
  bd.onclick=closeProfileSheet;
  // Fermeture au swipe-down basique
  let startY=null;
  sheet.ontouchstart=(e)=>{startY=e.touches[0].clientY;};
  sheet.ontouchmove=(e)=>{
    if(startY==null) return;
    const dy=e.touches[0].clientY-startY;
    if(dy>60){closeProfileSheet();startY=null;}
  };
}
function closeProfileSheet(){
  const sheet=document.getElementById('msf-sheet-root');
  const bd=document.getElementById('msf-sheet-backdrop');
  if(!sheet||!bd) return;
  sheet.classList.remove('open');
  bd.classList.remove('open');
  bd.setAttribute('aria-hidden','true');
  setTimeout(()=>{sheet.innerHTML='';},250);
}

// ── Render ──────────────────────────────────────────────────────
function render(){
  const _dfAe = document.activeElement;
  const _dfFocus = _dfAe && _dfAe.id === 'prod-filter-dossier-search';
  const _dfCaret = _dfFocus ? [_dfAe.selectionStart, _dfAe.selectionEnd] : null;

  const root=document.getElementById('root');root.innerHTML='';
  document.body.classList.toggle('sb-open', !!S.sidebarOpen);
  document.body.classList.toggle('has-topbar', S.app==='prod' || S.app==='stock' || S.app==='compta' || S.app==='expe' || S.app==='devis');
  document.body.classList.toggle('mysifa-app-prod', S.app==='prod');
  document.body.classList.toggle('mysifa-app-expe', S.app==='expe');
  const _prodFilterPages=['production','historique','saisies'];
  document.body.classList.toggle('mysifa-prod-filters-page', S.app==='prod' && _prodFilterPages.includes(S.page));
  window.__MYSIFA_APP__ = S.app;
  window.__MYSIFA_USER__ = S.user ? { nom: (S.user.nom || ''), role: (S.user.role || '') } : {};
  if(S.user){
    window.__MYSIFA_UID__ = S.user.id;
    window.__MYSIFA_NOM__ = S.user.nom || '';
    window.__MYSIFA_ROLE__ = S.user.role || '';
    if(window._CW && typeof window._CW.syncUser === 'function') window._CW.syncUser();
  } else {
    if(window._CW && typeof window._CW.destroy === 'function') window._CW.destroy();
    window.__MYSIFA_UID__ = 0;
    window.__MYSIFA_NOM__ = '';
    window.__MYSIFA_ROLE__ = '';
  }
  if(window.MySifaDock&&typeof window.MySifaDock.bootPageWidgets==='function') window.MySifaDock.bootPageWidgets();
  else{
    if(typeof initAiChatWidget === 'function') initAiChatWidget();
    if(typeof initPostitDock === 'function') initPostitDock();
    if(typeof initPostitsApp === 'function') initPostitsApp();
  }
  if(S.app!=='expe'){_expeLastRenderedInnerTab=null;window._moExpeLastKey=null;}
  if(S.app!=='prod'){window._moProdLastKey=null;}
  if(S.app!=='stock'){window._moStockLastKey=null;}

  // Nettoyage polling machine quand on quitte MyProd
  if(S.app!=='prod'){stopMachineStatusPolling();}

  if(!S.user||S.app==='login'){
    // Sur le login : forcer la palette pétrole (mysifa) + style défaut, ne garder que le mode.
    // Évite que la palette/style d'un compte précédemment loggé persiste sur l'écran de connexion.
    try{
      const _lp=MySifaTheme.loadPrefs();
      MySifaTheme.applyPrefs({mode:_lp.mode,palette:'mysifa',style:'defaut',bgAnim:_lp.bgAnim});
    }catch(e){}
    root.appendChild(renderLogin());
  }
  else if(S.app==='portal'){
    root.appendChild(renderPortal());
    if(window._postitDragCleanup) window._postitDragCleanup();
  }
  else if(S.app==='stock'){root.appendChild(renderStock());}
  else if(S.app==='compta'){root.appendChild(renderCompta());}
  else if(S.app==='expe'){root.appendChild(renderExpe());}
  else if(S.app==='devis'){window.location.href='/pricing';return;}
  else if(S.app==='messages'){root.appendChild(renderMessagesApp());}
  else if(S.app==='prod'){
    if(isComptaPlanning(S.user)){window.location.href='/planning';return;}
    const titles={
      production: S.subPage==='saisies'?'Saisies':S.subPage==='erreurs'?'Historique & Erreurs':'Production',
      suivi:'Rentabilité & Dossiers',
      traceabilite:'Traçabilité',
      // rétrocompat URL directe
      historique:'Historique & Erreurs',saisies:'Saisies',import:'Import XLSX',
      dossiers:'Dossiers',rentabilite:'Rentabilité',of:'Ordres de fabrication',
    };
    const subs={
      production: S.subPage==='saisies'?'Consulter, corriger et importer des saisies':
                  S.subPage==='erreurs'?'Sanity Score, incidents et erreurs de saisie':
                  'KPIs, temps, quantités et qualité de saisie',
      suivi:'Dossiers de production et comparaison devis / réel',
      traceabilite:'Matières utilisées par dossier',
      of:'Import PDF et consultation des OF',
      historique:'',saisies:'',import:'',dossiers:'',rentabilite:'',
    };
    const topbar=h('div',{className:'mobile-topbar'},
      h('button',{type:'button',className:'mobile-menu-btn',onClick:toggleSidebar,'aria-label':'Menu'},iconEl('menu',20)),
      h('div',null,
        h('div',{className:'mobile-topbar-title'},titles[S.page]||''),
        h('div',{className:'mobile-topbar-sub'},subs[S.page]||'')
      ),
      h('button',{type:'button',className:'mobile-home-btn',onClick:()=>{window.location.href='/'},'aria-label':'Accueil'},iconEl('home',20))
    );
    const prodFilterPages=['production','historique','saisies'];
    const hasProdFilters=prodFilterPages.includes(S.page);
    const prodPageContent=[];
    if(S.page==='production') prodPageContent.push(renderProdPage());
    if(S.page==='suivi') prodPageContent.push(renderSuivi());
    if(S.page==='traceabilite') prodPageContent.push(renderTracabilite());
    if(S.page==='historique') prodPageContent.push(renderHist());
    if(S.page==='saisies') prodPageContent.push(renderSaisies());
    if(S.page==='import') prodPageContent.push(renderImport());
    if(S.page==='dossiers') prodPageContent.push(renderDos());
    if(S.page==='rentabilite') prodPageContent.push(renderRentabilite());
    if(S.page==='of'){
      if(canAccessOfTab()) prodPageContent.push(renderOfPage());
      else prodPageContent.push(h('div',{className:'card-empty'},'Accès réservé à l\'administration.'));
    }
    const containerKids=[
      topbar,
      h('h1',null,titles[S.page]||''),
      h('div',{className:'subtitle'},subs[S.page]||''),
    ];
    // Motion : cascade d'entree au changement d'onglet uniquement (le re-render
    // intra-tab ne doit pas relancer l'animation, sinon perte de focus inputs).
    const _moProdKey=(S.page||'')+'|'+(S.subPage||'');
    const _moProdEnter=(window._moProdLastKey!==_moProdKey);
    window._moProdLastKey=_moProdKey;
    if(hasProdFilters) containerKids.push(renderFilters());
    if(hasProdFilters){
      // Wrapper scroll : 2e niveau de cascade sur les cartes top-level.
      const _scrollProps=Object.assign({className:'prod-main-scroll'},_moProdEnter?{'data-page-enter':''}:{});
      containerKids.push(h('div',_scrollProps,...prodPageContent));
    } else {
      // Pas de wrapper : on pose data-page-enter directement sur le 1er
      // element retourne par le renderer du tab pour cascader ses enfants.
      if(_moProdEnter && prodPageContent[0] && prodPageContent[0].nodeType===1){
        try{ prodPageContent[0].setAttribute('data-page-enter',''); }catch(_){}
      }
      containerKids.push(...prodPageContent);
    }
    const _prodContainerProps=Object.assign({className:'container'},_moProdEnter?{'data-page-enter':''}:{});
    root.appendChild(h('div',null,
      S.sidebarOpen?h('div',{className:'sidebar-overlay',onClick:closeSidebar}):null,
      h('div',{className:'app'},renderSidebar(),
        h('main',{className:'main'},h('div',_prodContainerProps,...containerKids))
      )
    ));
  }

  if(S.toast){const c={success:'var(--success)',error:'var(--danger)'};root.appendChild(h('div',{className:'toast',style:{borderLeft:'3px solid '+(c[S.toast.type]||'var(--accent)')}},h('span',{style:{fontSize:'14px',color:c[S.toast.type]||'var(--accent)'}},S.toast.message)));}

  if(S.contactOpen){
    root.appendChild(renderContactModal());
  }
  if(S.app==='prod' && S.ofImportModal){
    const ofModal=renderOfImportModal();
    if(ofModal) root.appendChild(ofModal);
  }
  // contact modal for expe is rendered inside renderExpe()

  // Calculette flottante (MyStock + MyProd + MyCompta + MyExpé)
  if(S.app==='stock'||S.app==='prod'||S.app==='compta'||S.app==='expe'){
    window._calc_mount && window._calc_mount();
  } else if(window._calc_unmount){
    window._calc_unmount();
  }
  // Carte France — widget dock MyExpé uniquement
  if(S.app==='expe'){
    window._expe_carte_mount && window._expe_carte_mount();
  } else if(window._expe_carte_unmount){
    window._expe_carte_unmount();
  }
  if(window.MySifaDock && typeof window.MySifaDock.layout==='function') window.MySifaDock.layout();

  if(S.app==='prod'||S.app==='expe'){
    if(window.MySifaLandscape&&typeof window.MySifaLandscape.enable==='function') window.MySifaLandscape.enable();
  }else{
    if(window.MySifaLandscape&&typeof window.MySifaLandscape.disable==='function') window.MySifaLandscape.disable();
    else{
      document.body.classList.remove('mysifa-landscape-required');
      document.body.classList.remove('mysifa-portrait');
      document.body.classList.remove('mysifa-force-landscape');
    }
  }

  // PWA: feature temporairement retirée. (setupInstallButton supprimé)

  if(_dfFocus){
    requestAnimationFrame(()=>{
      const el = document.getElementById('prod-filter-dossier-search');
      if(!el) return;
      try{
        el.focus();
        if(_dfCaret){
          const a = Math.min(_dfCaret[0] != null ? _dfCaret[0] : 0, el.value.length);
          const b = Math.min(_dfCaret[1] != null ? _dfCaret[1] : a, el.value.length);
          el.setSelectionRange(a, b);
        }
      }catch(e){}
      syncDossierFilterSuggest();
    });
  }
  // Mobile nav bar : sync sur toutes les pages (portrait mobile only)
  try{ renderMobileNavbar(); }catch(_){}
  // Sync visuel de l'onglet "Changer d'app" quand la palette se ferme (Escape, backdrop, close)
  if(!window.__MYSIFA_CMDK_NAV_SYNC__){
    window.__MYSIFA_CMDK_NAV_SYNC__=true;
    const _syncNav=()=>{try{renderMobileNavbar();}catch(_){}};
    const _installObs=()=>{
      const ov=document.getElementById('cmdk-overlay');
      if(!ov){setTimeout(_installObs,300);return;}
      if(!window.MutationObserver)return;
      new MutationObserver(_syncNav).observe(ov,{attributes:true,attributeFilter:['class']});
    };
    setTimeout(_installObs,200);
  }
  // Motion : (re)scan apres chaque render — pose --i pour les cascades,
  // arme les IntersectionObserver pour mo-reveal et data-count-to, et place
  // l'indicateur de navigation glissant. No-op si window.Motion absent.
  try{ if(window.Motion) window.Motion.scan(document); }catch(_){}
}

async function nav(){
  if(S.page==='production'){
    if(S.subPage==='kpis'||!S.subPage){await loadProd();if(!S.historique)await loadHist();loadMachineStatus();}
    else if(S.subPage==='saisies'){await loadSaisies();}
    else if(S.subPage==='erreurs'){await loadHist();}
  }
  else if(S.page==='suivi'){await loadDos();await loadDevis();}
  else if(S.page==='historique')await loadHist();
  else if(S.page==='saisies')await loadSaisies();
  else if(S.page==='import')await loadImports();
  else if(S.page==='rentabilite'){await loadDevis();await loadRentPlanning();}
  else if(S.page==='dossiers')await loadDos();
  else if(S.page==='traceabilite'){S.traceabilite=null;S.traceabiliteDossier=undefined;S.tracShowAttente=false;await loadTracabilite();}
  else if(S.page==='of' && canAccessOfTab()){
    await loadOfImports();
    if(S.ofSubTab==='fiche') await loadFiches();
    else if(S.ofSubTab==='pending') await loadPendingOfMappings();
    else if(S.ofSubTab==='sansof') await loadDossiersSansOf();
    // rafraîchit le badge unifié (ambigus + sans OF)
    loadPendingOfCount();
  }
  render();
}

// Désactive le service worker pour éviter des effets de cache —
// SAUF si l'utilisateur a activé les notifications push (le SW est alors requis).
try{
  if('serviceWorker' in navigator){
    let pushEnabled=false;
    try{ pushEnabled=localStorage.getItem('mysifa_push_enabled')==='1'; }catch(e){}
    if(!pushEnabled){
      const k='mysifa_sw_unreg_v1';
      if(!sessionStorage.getItem(k)){
        sessionStorage.setItem(k,'1');
        navigator.serviceWorker.getRegistrations()
          .then(rs=>Promise.all(rs.map(r=>r.unregister().catch(()=>false))))
          .then(()=>{ try{ location.reload(); }catch(e){} });
      }
    }
  }
}catch(e){}

// Quand on revient sur l'accueil (bfcache / retour onglet), on rafraîchit le badge et la session.
try{
  window.addEventListener('pageshow', ()=>{
    if(S && S.user && S.app==='portal'){
      refreshPortalData().catch(()=>{});
    }
  });
  document.addEventListener('visibilitychange', ()=>{
    if(document.visibilityState==='visible' && S && S.user && S.app==='portal'){
      refreshPortalData().catch(()=>{});
    }
  });
}catch(e){}
checkAuth();
</script>
<!-- Agent IA -->
<div id="ai-chat-root">
  <button id="ai-chat-btn" type="button" aria-label="Assistant IA" title="Assistant MySifa">
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
    </svg>
  </button>
  <div id="ai-chat-panel" role="dialog" aria-label="Assistant MySifa">
      <div id="ai-chat-header">
      <span class="ai-dot"></span>
      <div class="ai-title">Assistant MySifa<span class="ai-sub">Posez vos questions sur la production, le stock…</span></div>
      <button id="ai-chat-close" type="button" aria-label="Fermer">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="1" y1="1" x2="13" y2="13"/><line x1="13" y1="1" x2="1" y2="13"/></svg>
      </button>
    </div>
    <div id="ai-messages"></div>
    <div id="ai-typing"><span class="ai-dot-t"></span><span class="ai-dot-t"></span><span class="ai-dot-t"></span></div>
      <div id="ai-input-area">
      <textarea id="ai-input" placeholder="Votre question…" rows="1" aria-label="Message"></textarea>
      <button id="ai-send" type="button" aria-label="Envoyer">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M22 2L11 13"/><path d="M22 2L15 22l-4-9-9-4 20-7z"/></svg>
      </button>
    </div>
  </div>
</div>
</body>
</html>"""

_MODULE_CONFIG: dict[str, dict] = {
    # initial_app → config spécifique au module
    "expe": {
        "touch_icon": 'sizes="180x180" href="/static/expe_favicon-180.png"',
        "app_title": "MyExpé",
        "manifest": "/manifest-expe.webmanifest",
    },
}
_DEFAULT_CONFIG = {
    "touch_icon": 'href="/static/mys_icon_180.png"',
    "app_title": "MySifa",
    "manifest": "/manifest.webmanifest",
}


def render_frontend_html(initial_app: str = "portal") -> str:
    cfg = _MODULE_CONFIG.get(initial_app, _DEFAULT_CONFIG)
    # Bandeau : toujours dans le DOM. Visibilité initiale = IS_STAGING (rouge).
    # En prod : caché par défaut ; le JS d'impersonation le révèle pour le superadmin.
    if IS_STAGING:
        staging_body_class = "has-staging-bandeau"
        staging_initial_class = ""  # rouge par défaut (staging)
        staging_initial_hidden = ""
        staging_initial_msg = "v1 — Environnement de test — DB partagée avec la prod"
    else:
        staging_body_class = ""
        staging_initial_class = "env-prod"
        staging_initial_hidden = "hidden"
        staging_initial_msg = ""
    # Favicons : en staging v1, on sert la variante "light" (fond clair, texte foncé)
    # pour distinguer visuellement l'onglet Chrome de celui de la prod.
    fav_sfx = "-light" if IS_STAGING else ""
    # touch_icon : en staging, remplacer mys_icon_180.png par mys_icon-light_180.png
    # (idem pour les icônes de module si un jour on en fait des variantes light).
    touch_icon = cfg["touch_icon"]
    if IS_STAGING:
        touch_icon = touch_icon.replace("mys_icon_180.png", "mys_icon-light_180.png")
    # Marque affichée dans le titre onglet + apple-mobile-web-app-title.
    # Prod → "MySifa" ; staging v1 → "MySifa test" (impossible de confondre les 2 onglets).
    brand = "MySifa test" if IS_STAGING else "MySifa"
    # Page-title : si l'app_title == "MySifa", pas de doublon (on affiche la brand seule).
    # Sinon on préfixe : "MyExpé — MySifa" / "MyExpé — MySifa test".
    if cfg["app_title"] == "MySifa":
        page_title = brand
    else:
        page_title = f"{cfg['app_title']} — {brand}"
    return (
        _FRONTEND_HTML_TEMPLATE.replace("__META_DESCRIPTION__", APP_META_DESCRIPTION)
        .replace("__THEME_COLOR__", THEME_COLOR_META)
        .replace("__V_LABEL__", f"v{APP_VERSION}")
        .replace("__STAGING_BODY_CLASS__", staging_body_class)
        .replace("__STAGING_INITIAL_CLASS__", staging_initial_class)
        .replace("__STAGING_INITIAL_HIDDEN__", staging_initial_hidden)
        .replace("__STAGING_INITIAL_MSG__", staging_initial_msg)
        .replace("__ENV_NAME_VALUE__", ENV_NAME)
        .replace("__INITIAL_APP_VALUE__", initial_app)
        .replace("__FAV_SFX__", fav_sfx)
        .replace("__FAV_SFX2__", fav_sfx)
        .replace("__TOUCH_ICON__", touch_icon)
        .replace("__PAGE_TITLE__", page_title)
        .replace("__BRAND__", brand)
        .replace("__APP_TITLE__", cfg["app_title"])
        .replace("__MANIFEST__", cfg["manifest"])
        .replace("__EXPE_TRANSPORTEURS_CSS__", EXPE_TRANSPORTEURS_CSS)
        .replace("__EXPE_COMPARATEUR_CSS__", EXPE_COMPARATEUR_CSS)
        .replace("__EXPE_DEVIS_CSS__", EXPE_DEVIS_CSS)
        .replace("__EXPE_CARTE_FRANCE_CSS__", EXPE_CARTE_FRANCE_CSS)
        .replace("__EXPE_COMPARATEUR_JS__", EXPE_COMPARATEUR_JS)
        .replace("__EXPE_DEVIS_JS__", EXPE_DEVIS_JS)
        .replace("__EXPE_TRANSPORTEURS_JS__", EXPE_TRANSPORTEURS_JS)
        .replace("__EXPE_CARTE_FRANCE_JS__", EXPE_CARTE_FRANCE_JS)
    )


FRONTEND_HTML = render_frontend_html("portal")

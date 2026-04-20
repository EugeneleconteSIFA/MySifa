from config import APP_VERSION, APP_META_DESCRIPTION, APP_PAGE_TITLE, THEME_COLOR_META

_FRONTEND_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="__META_DESCRIPTION__">
<link rel="icon" href="/static/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/static/favicon-32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/static/favicon-16.png">
<link rel="icon" type="image/png" sizes="512x512" href="/static/mys_icon_512.png">
<link rel="apple-touch-icon" href="/static/mys_icon_180.png">
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="icon" type="image/png" sizes="1024x1024" href="/static/mys_icon_1024.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="MySifa">
<meta name="theme-color" content="#0a0e17">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="mobile-web-app-capable" content="yes">
<title>__PAGE_TITLE__</title>
<link rel="stylesheet" href="/static/support_widget.css">
<style>
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;
  --muted:#94a3b8;--accent:#22d3ee;--accent-bg:rgba(34,211,238,0.12);
  --success:#34d399;--warn:#fbbf24;--danger:#f87171;
  --c1:#22d3ee;--c2:#a78bfa;--c3:#34d399;--c4:#fbbf24;--c5:#f87171
}
body.light{
  --bg:#f1f5f9;--card:#ffffff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;
  --muted:#94a3b8;--accent:#0891b2;--accent-bg:rgba(8,145,178,0.10);
  --success:#059669;--warn:#d97706;--danger:#dc2626;
  --c1:#0891b2;--c2:#7c3aed;--c3:#059669;--c4:#d97706;--c5:#dc2626
}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;overflow-x:hidden}
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
.login-page{min-height:100vh;display:flex;align-items:center;justify-content:center}
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
.app{display:flex;min-height:100vh}
.sidebar{width:220px;background:var(--card);border-right:1px solid var(--border);padding:20px 12px;display:flex;flex-direction:column;flex-shrink:0;height:100vh;position:sticky;top:0;overflow-y:auto}
.sidebar::-webkit-scrollbar{width:0}
.sidebar{scrollbar-width:none}
.mobile-topbar{display:none;align-items:center;gap:10px;margin-bottom:14px}
.mobile-menu-btn{display:none;align-items:center;justify-content:center;width:40px;height:40px;border-radius:10px;
  border:1px solid var(--border);background:var(--card);color:var(--text2);cursor:pointer;font-family:inherit}
.mobile-menu-btn:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.mobile-home-btn{display:none;align-items:center;justify-content:center;width:40px;height:40px;border-radius:10px;
  border:1px solid var(--border);background:var(--card);color:var(--text2);cursor:pointer;font-family:inherit;margin-left:auto}
.mobile-home-btn:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.mobile-topbar-title{font-size:14px;font-weight:800}
.mobile-topbar-sub{font-size:11px;color:var(--muted);margin-top:2px}
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
  .mobile-topbar{display:flex;position:fixed;top:0;left:0;right:0;z-index:120;background:var(--bg);padding:10px 18px;border-bottom:1px solid var(--border)}
  .mobile-menu-btn{display:inline-flex}
  .mobile-home-btn{display:inline-flex}
  .sidebar-overlay{display:block;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:8999}
  body:not(.sb-open) .sidebar-overlay{display:none}
  body.has-topbar .main{padding-top:74px}
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
body.light .nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(8,145,178,.32),0 0 16px rgba(8,145,178,.12)}
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
body.light .theme-btn:hover{box-shadow:0 0 0 1px rgba(8,145,178,.28),0 0 18px rgba(8,145,178,.12)}
.theme-btn .theme-ico{font-size:14px;line-height:1}
.theme-btn .theme-label{white-space:nowrap}
@media (display-mode: standalone), (max-width: 900px){
  .theme-btn .theme-label{display:none}
  .theme-btn{justify-content:center}
}
.logout-btn{border:none}.logout-btn:hover{color:var(--danger);background:rgba(248,113,113,.1);box-shadow:0 0 0 1px rgba(248,113,113,.35),0 0 18px rgba(248,113,113,.12)}
.version{font-size:10px;color:var(--muted);font-family:monospace;padding:4px 12px}
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
.card-header h3{font-size:14px;font-weight:600}
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
.filters{display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end;margin-bottom:20px}
.filter-group{display:flex;flex-direction:column;gap:4px}
.filter-group label{font-size:10px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
.filters select,.filters input[type=date]{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:8px 12px;color:var(--text);font-size:12px;font-family:inherit;min-width:140px}
.filters select:focus,.filters input:focus{border-color:var(--accent);outline:none}
.filters button{
  background:var(--accent);color:var(--bg);
  border:none;border-radius:8px;
  padding:9px 16px;font-size:12px;font-weight:600;
  cursor:pointer;font-family:inherit;align-self:flex-end;
  transition:filter .15s,box-shadow .15s,transform .05s;
}
.filters button:hover{filter:brightness(1.05);box-shadow:0 0 0 4px rgba(34,211,238,.18)}
.filters button:active{transform:translateY(1px)}
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
/* ── Calculette flottante ── */
.calc-fab{position:fixed;bottom:max(24px,env(safe-area-inset-bottom,0px));right:max(24px,env(safe-area-inset-right,0px));width:52px;height:52px;border-radius:50%;background:var(--accent);color:var(--bg);border:none;font-size:22px;cursor:pointer;z-index:8000;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 18px rgba(0,0,0,.35);transition:transform .15s,filter .15s}
.calc-fab:hover{filter:brightness(1.1);transform:scale(1.07)}
.calc-fab:active{transform:scale(.96)}
.calc-panel{position:fixed;bottom:86px;right:max(20px,env(safe-area-inset-right,0px));width:260px;background:var(--card);border:1px solid var(--border);border-radius:16px;box-shadow:0 12px 40px rgba(0,0,0,.45);z-index:7999;overflow:hidden;animation:fadeUp .2s ease-out}
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
.portal-page{min-height:100vh;display:flex;flex-direction:column;
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
.portal-apps{display:flex;gap:14px;flex-wrap:wrap;justify-content:center;align-items:stretch}
.portal-app{display:flex;flex-direction:column;align-items:center;gap:8px;
  background:var(--card);border:1px solid var(--border);border-radius:16px;
  padding:16px 14px;cursor:pointer;transition:all .2s;text-decoration:none;
  width:168px;height:152px;flex:0 0 168px;box-sizing:border-box;
  justify-content:center}
.portal-app--disabled{cursor:default;opacity:.6;position:relative}
.portal-app--disabled:hover{border-color:var(--border);background:var(--card)}
.badge-dev{position:absolute;top:8px;right:8px;font-size:9px;font-weight:700;padding:2px 8px;border-radius:20px;background:var(--warn);color:#0a0e17;text-transform:uppercase;letter-spacing:.5px}
.portal-app:hover{border-color:var(--accent);background:var(--accent-bg);
  transform:translateY(-3px);box-shadow:0 10px 32px rgba(34,211,238,.14)}
.portal-app--busy{pointer-events:none;opacity:.8;position:relative;transform:none!important;box-shadow:none!important}
.portal-app--busy::after{
  content:'Chargement…';position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
  background:rgba(10,14,23,.72);border-radius:16px;font-size:12px;font-weight:700;color:var(--accent);letter-spacing:.02em}
body.light .portal-app--busy::after{background:rgba(255,255,255,.88);color:var(--accent)}
.portal-app-icon{display:flex;align-items:center;justify-content:center;line-height:1;flex-shrink:0}
.portal-app-name{font-size:15px;font-weight:800;color:var(--text);flex-shrink:0;text-align:center;line-height:1.2}
.portal-app-desc{font-size:11px;color:var(--muted);text-align:center;max-width:152px;line-height:1.3;
  display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;
  flex:0 0 auto;margin:0}
.portal-user{font-size:12px;color:var(--muted);display:flex;align-items:center;gap:8px}
.portal-logout{background:none;border:none;color:var(--muted);cursor:pointer;
  font-size:12px;font-family:inherit;text-decoration:underline;
  display:inline-flex;align-items:center;gap:6px;line-height:1;padding:4px 6px;border-radius:6px;
  transition:color .15s,box-shadow .2s,background .15s}
.portal-logout:hover{color:var(--accent);text-shadow:0 0 12px rgba(34,211,238,.45);background:rgba(34,211,238,.08)}
.portal-logout:hover:last-of-type{color:var(--danger);text-shadow:0 0 12px rgba(248,113,113,.4);background:rgba(248,113,113,.08)}
body.light .portal-logout:hover{text-shadow:0 0 12px rgba(8,145,178,.35)}
body.light .portal-logout:hover:last-of-type{text-shadow:0 0 12px rgba(220,38,38,.35)}

@media (max-width:420px){
  /* Portail mobile : 2 colonnes au lieu d'une pile */
  .portal-apps{
    display:grid;
    grid-template-columns:repeat(2, minmax(0, 1fr));
    gap:12px;
    width:100%;
    max-width:420px;
  }
  .portal-app{
    width:auto;
    flex:none;
  }
  .portal-app-desc{max-width:100%}
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
.expe-top3{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;margin-bottom:18px}
.expe-score{background:var(--card);border:1px solid var(--border);border-radius:14px;overflow:hidden;position:relative}
.expe-score .stripe{height:4px}
.expe-score .body{padding:16px 20px}
.expe-score .carrier{font-size:18px;font-weight:800;letter-spacing:-.5px}
.expe-score .price{font-size:28px;font-weight:800;font-family:monospace;margin:8px 0}
.expe-score .price .unit{font-size:13px;font-weight:500;color:var(--muted);margin-left:4px}
.expe-score .medal{font-size:24px;flex-shrink:0}
.expe-note{font-size:10px;color:rgba(148,163,184,.8);margin-top:12px}
</style>
</head>
<body>
<div id="root"></div>
<script src="/static/support_widget.js"></script>
<script>
const API=window.location.origin;
const INITIAL_APP="__INITIAL_APP_VALUE__";
const HAS_INITIAL_APP = !!(INITIAL_APP && INITIAL_APP !== "__INITIAL_APP__");
function isAuthMePath(p){
  return p==='/api/auth/me'||p.startsWith('/api/auth/me?');
}
let authEpoch=0;
async function api(p,o){
  try{
    const r=await fetch(API+p,{credentials:'include',...o});
    if(r.status===401){
      // Ne pas forcer la déconnexion sur /me : une réponse 401 tardive (requête lancée avant la connexion)
      // écrasait l’état après un login réussi. checkAuth() gère l’absence de session via authEpoch.
      if(!isAuthMePath(p)){S.user=null;S.app='login';render();}
      return null;
    }
    if(!r.ok){const e=await r.json().catch(()=>({}));throw new Error(e.detail||'Erreur '+r.status);}
    const ct=r.headers.get('content-type')||'';
    if(ct.includes('spreadsheet')||ct.includes('octet-stream'))return r.blob();
    return await r.json();
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
  importOpen:false,
  selDossier:null,
  loginSubmitting:false,loginError:null,portalLoading:null,
  sidebarOpen:false,
  expeTab:'comparateur',
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
  comptaTab:'factor',
  comptaAcheteurs:[],
  comptaComptes:[],
  comptaResult:null,
  comptaEditAcheteurId:null,
  comptaEditCompteId:null,
  stockView:'grille',
  stockProduits:[],stockSelProduit:null,stockSelEmpl:null,
  stockGlobale:null,stockInvPriorites:[],stockSearch:'',stockGrilleFilter:'',stockMvtType:'entree',
  stockPrefillEmpl:null,stockPrefillRef:null,stockPrefillDes:null,stockPrefillUnit:null,
  filters:{},OPS_CONFIG:{},
  fv:{operateurs:[],dossiers:[],date_from:getYesterday(),date_to:getYesterday()},
  saisiesOffset:0,
  saisiesLimit:200,
  historique:null,production:null,traceabilite:null,
  tracFilters:{ref:'',client:'',machine:'',statut:''},
  tracSort:{col:null,dir:'asc'},
  imports:[],selImp:null,impData:null,
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
};

function set(u){Object.assign(S,u);render();}
function toast(m,t='success'){set({toast:{message:m,type:t}});setTimeout(()=>set({toast:null}),3500);}

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
  };
  return `<svg ${a} aria-hidden="true" style="display:inline-block;vertical-align:middle;flex-shrink:0">${p[name]||p['alert-circle']}</svg>`;
}
function iconEl(name,size=16){
  const s=document.createElement('span');
  s.style.cssText='display:inline-flex;align-items:center;flex-shrink:0';
  s.innerHTML=icon(name,size);
  return s;
}

const fN=n=>n?Number(n).toLocaleString('fr-FR'):'0';
const fD=d=>d?d.replace(/C$/,'').replace('T',' ').slice(0,16):'-';
const opName=s=>{if(!s)return'';const p=s.split(' - ');return p.length>1?p.slice(1).join(' - '):s;};
const fMin=m=>{if(!m&&m!==0)return'-';const hh=Math.floor(m/60),mm=Math.round(m%60);return hh>0?hh+'h '+String(mm).padStart(2,'0')+'min':mm+'min';};
const isAdmin=u=>u&&(u.role==='direction'||u.role==='administration'||u.role==='superadmin');
const canPlanningNav=u=>!!(u&&u.app_access&&u.app_access.planning);
const isFab=u=>u&&u.role==='fabrication';

const ROLE_LABELS={direction:'Direction',administration:'Administration',fabrication:'Fabrication',logistique:'Logistique',comptabilite:'Comptabilité',expedition:'Expédition',commercial:'Commercial',superadmin:'Super admin'};
const isCommercial=u=>u&&u.role==='commercial';
const ROLE_BADGE={direction:'badge-direction',administration:'badge-administration',fabrication:'badge-fabrication',logistique:'badge-fabrication',comptabilite:'badge-administration',expedition:'badge-administration',superadmin:'badge-direction'};

// ── Auth ────────────────────────────────────────────────────────
async function checkAuth(){
  const epoch=authEpoch;
  const user=await api('/api/auth/me');
  if(epoch!==authEpoch)return;
  if(user){
    S.user=user;
    S.app=HAS_INITIAL_APP ? INITIAL_APP : 'portal';
    // Garder le badge Messagerie à jour, même sur le portail
    try{ startMessagesPolling(); }catch(e){}
    // Support : redirection post-login (ex: /?next=/planning)
    try{
      const sp=new URLSearchParams(window.location.search||'');
      const nxt=(sp.get('next')||'').trim();
      if(nxt && nxt.startsWith('/')){
        window.location.href=nxt;
        return;
      }
    }catch(e){}
    try{
      const sp=new URLSearchParams(window.location.search||'');
      const p=(sp.get('page')||'').trim();
      if(S.app==='prod' && p==='users'){window.location.href='/settings';return;}
      const allowed=new Set(['production','suivi','profil','historique','saisies','import','rentabilite','dossiers','traceabilite']);
      if(S.app==='prod' && allowed.has(p)) S.page=p;
    }catch(e){}
    if(S.app==='prod'){
      await loadFilters();
      await loadProd();
      await loadHist();
    }else if(S.app==='stock'){
      await loadStockGlobale();
      await loadStockProduits();
    }
  }
  else{S.user=null;S.app='login';}
  render();
}

let _msgPollStarted=false;
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
    S.user=r.user;
    S.app=HAS_INITIAL_APP ? INITIAL_APP : 'portal';
    // Support : redirection post-login (ex: /?next=/planning)
    try{
      const sp=new URLSearchParams(window.location.search||'');
      const nxt=(sp.get('next')||'').trim();
      if(nxt && nxt.startsWith('/')){
        window.location.href=nxt;
        return;
      }
    }catch(e){}
    // Support /prod?page=xxx après login
    try{
      const sp=new URLSearchParams(window.location.search||'');
      const p=(sp.get('page')||'').trim();
      if(S.app==='prod' && p==='users'){window.location.href='/settings';return;}
      const allowed=new Set(['production','suivi','profil','historique','saisies','import','rentabilite','dossiers','traceabilite']);
      if(S.app==='prod' && allowed.has(p)) S.page=p;
    }catch(e){}
    S.loginError=null;
    S.fv={
      operateurs:[],
      dossiers:[],
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
    render();
    if(S.app==='prod'){
      await loadFilters();
      await loadProd();
      await loadHist();
    }else if(S.app==='stock'){
      await loadStockGlobale();
      await loadStockProduits();
    }
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
  try {
    if (typeof ZXing === 'undefined') {
      toast('Chargement du scanner...', 'warn');
      await loadZXing();
    }
  } catch (e) {
    toast('Impossible de charger le scanner', 'error');
    return;
  }

  stockSearchState.scanning = true;
  renderStockSearchBar();

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
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } }
    });
    stockSearchState.cameraStream = stream;
    video.srcObject = stream;

    const hints = new Map();
    const formats = [
      ZXing.BarcodeFormat.CODE_128,
      ZXing.BarcodeFormat.EAN_13,
      ZXing.BarcodeFormat.EAN_8,
      ZXing.BarcodeFormat.QR_CODE,
      ZXing.BarcodeFormat.DATA_MATRIX,
    ];
    hints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS, formats);
    const reader = new ZXing.BrowserMultiFormatReader(hints);
    stockSearchState.barcodeReader = reader;

    reader.decodeFromVideoDevice(null, video, (result) => {
      if (result) {
        const text = result.getText();
        resultEl.textContent = '✅ ' + text;
        resultEl.style.borderColor = 'var(--success)';
        resultEl.style.color = 'var(--success)';
        setTimeout(() => { stopCamera(modal); handleBarcodeResult(text); }, 600);
      }
    });
  } catch (err) {
    toast('Accès caméra refusé ou non disponible', 'error');
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

function renderPortal(){
  const aa = S.user && S.user.app_access ? S.user.app_access : null;
  const urole = S.user && S.user.role ? S.user.role : '';
  const isSuper = urole === 'superadmin';
  const isStock = aa ? !!aa.stock : (isSuper || !!(urole && ['direction','administration','logistique','commercial'].includes(urole)));
  const isProd  = aa ? !!aa.prod : (isSuper || !!(urole && ['direction','administration','fabrication','commercial'].includes(urole)));
  const isCompta = aa ? !!aa.compta : (isSuper || !!(urole && ['direction','administration','comptabilite'].includes(urole)));
  const isExpe = aa ? !!aa.expe : (isSuper || !!(urole && ['direction','administration','expedition'].includes(urole)));
  const isFab = aa ? !!aa.fabrication : (isSuper || urole==='fabrication' || !!(urole && ['direction','administration'].includes(urole)));
  const isPrint = isSuper || !!(urole && ['fabrication','logistique'].includes(urole));
  const isCom = urole==='commercial';
  const isLight=document.body.classList.contains('light');

  const apps=[];

  if(isFab){
    apps.push(h('div',{
      className:'portal-app',
      onClick:()=>{ window.location.href='/fabrication'; }
    },
      h('div',{className:'portal-app-icon'},iconEl('edit',28)),
      h('div',{className:'portal-app-name'},'Saisie Prod'),
      h('div',{className:'portal-app-desc'},'Saisie opérateur — machine')
    ));
  }

  if(isProd){
    apps.push(h('div',{
      className:'portal-app'+(S.portalLoading==='prod'?' portal-app--busy':''),
      onClick:async()=>{
        window.location.href='/prod';
      }
    },
      h('div',{className:'portal-app-icon'},iconEl('wrench',28)),
      h('div',{className:'portal-app-name'},'MyProd'),
      h('div',{className:'portal-app-desc'},'Suivi de production & Planning')
    ));
  }

  if(isStock){
    apps.push(h('div',{
      className:'portal-app'+(S.portalLoading==='stock'?' portal-app--busy':''),
      onClick:async()=>{
        window.location.href='/stock';
      }
    },
      h('div',{className:'portal-app-icon'},iconEl('package',28)),
      h('div',{className:'portal-app-name'},'MyStock'),
      h('div',{className:'portal-app-desc'},'Gestion des stocks produits')
    ));
  }

  if(isPrint){
    apps.push(h('div',{
      className:'portal-app',
      onClick:()=>{ window.location.href='/stock?tab=traca'; }
    },
      h('div',{className:'portal-app-icon'},iconEl('printer',28)),
      h('div',{className:'portal-app-name'},'MyPrint'),
      h('div',{className:'portal-app-desc'},'Étiquettes de traçabilité')
    ));
  }

  // Messagerie: icône dans le coin (sous Paramètres) pour le super admin

  if(isCompta){
    apps.push(h('div',{
      className:'portal-app'+(S.portalLoading==='compta'?' portal-app--busy':''),
      onClick:async()=>{
        window.location.href='/compta';
      }
    },
      h('div',{className:'portal-app-icon'},iconEl('calculator',28)),
      h('div',{className:'portal-app-name'},'MyCompta'),
      h('div',{className:'portal-app-desc'},'Comptabilité — accès réservé')
    ));
  }

  if(isExpe){
    apps.push(h('div',{
      className:'portal-app'+(S.portalLoading==='expe'?' portal-app--busy':''),
      onClick:async()=>{
        window.location.href='/expe';
      }
    },
      h('div',{className:'portal-app-icon'},iconEl('truck',28)),
      h('div',{className:'portal-app-name'},'MyExpé'),
      h('div',{className:'portal-app-desc'},'Expédition & Suivi')
    ));
  }

  if(isCom){
    apps.push(h('div',{className:'portal-app portal-app--disabled'},
      h('div',{className:'portal-app-icon',style:{opacity:.4}},iconEl('truck',28)),
      h('div',{className:'portal-app-name',style:{opacity:.5}},'MyExpé'),
      h('div',{className:'portal-app-desc'},'Expédition & Suivi'),
      h('span',{className:'badge-dev'},'En développement')
    ));
    apps.push(h('div',{className:'portal-app portal-app--disabled'},
      h('div',{className:'portal-app-icon',style:{opacity:.4}},iconEl('file-text',28)),
      h('div',{className:'portal-app-name',style:{opacity:.5}},'MyDevis'),
      h('div',{className:'portal-app-desc'},'Devis & Chiffrage'),
      h('span',{className:'badge-dev'},'En développement')
    ));
  }

  function openGoogle(q){
    const query = String(q||'').trim();
    if(!query) return;
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
  gForm.appendChild(gInp);
  // Bouton invisible pour conserver le submit natif du form (Entrée)
  gForm.appendChild(h('input',{type:'submit',className:'portal-search-submit',value:'Rechercher'}));
  const gBox = h('div',{className:'portal-search'},
    gForm,
    h('div',{className:'portal-search-hint'},'Astuce : tape puis Entrée pour ouvrir Google.')
  );

  return h('div',{className:'portal-page'},
    isSuper?h('div',{className:'portal-corner-stack'},
      h('button',{
        type:'button',
        className:'portal-settings-corner',
        'aria-label':'Paramètres',
        title:'Paramètres',
        onClick:()=>{window.location.href='/settings';}
      },iconEl('sliders',24)),
      h('button',{
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
      )
    ):null,
    h('div',{className:'portal-logo'},
      h('div',{className:'brand'},'My',h('span',null,'Sifa')),
      h('div',{className:'tagline'},'Portail interne — Production, stocks et outils métier')
    ),
    gBox,
    h('div',{className:'portal-apps'},...apps),
    h('div',{className:'portal-user'},
      h('span',{style:{display:'inline-flex',alignItems:'center',gap:'8px'}},iconEl('user',14),document.createTextNode(' '+((S.user&&S.user.nom)?S.user.nom:''))),
      h('button',{className:'portal-logout',onClick:()=>{document.body.classList.toggle('light');localStorage.setItem('theme',document.body.classList.contains('light')?'light':'dark');render();}},
        h('span',{className:'theme-ico'},iconEl(isLight?'sun':'moon',16)),
        h('span',{className:'theme-label'},isLight?'Mode clair':'Mode sombre')
      ),
      h('button',{className:'portal-logout',onClick:doLogout},'Déconnexion')
    )
  );
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
      h('button',{className:'nav-btn back-mysifa',onClick:()=>{window.location.href='/' }},
        '← Retour ',
        h('span',{className:'wm'},'My',h('span',null,'Sifa'))
      ),
      h('div',{className:'user-chip'},
        h('div',{className:'uc-name'},(S.user&&S.user.nom)?S.user.nom:''),
        h('div',{className:'uc-role'},(S.user&&S.user.role)?(ROLE_LABELS[S.user.role]||S.user.role):'')
      ),
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
      h('button',{className:'theme-btn',onClick:()=>{document.body.classList.toggle('light');localStorage.setItem('theme',document.body.classList.contains('light')?'light':'dark');render();}},
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
          h('td',null,h('span',{className:'mvt-type-'+m.type_mouvement},m.type_mouvement)),
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

      const mvtBtns=h('div',{className:'mvt-btns'},
        ...[['entree','Entrée ↓'],['sortie','Sortie ↑'],['inventaire','Inventaire =']].map(([t,l])=>{
          const btn=h('button',{className:'mvt-btn'+(S.stockMvtType===t?' active-'+t:'')},l);
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
            h('td',null,h('span',{className:'mvt-type-'+m.type_mouvement},m.type_mouvement)),
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
          className:'mvt-btn'+(((sel&&sel.emplacement)===e)?' active-entree':''),
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
            h('td',null,h('span',{className:'mvt-type-'+m.type_mouvement},m.type_mouvement)),
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
  const mainEl=h('main',{className:'main'},
    topbar,
    h('div',{className:'container',style:{padding:'24px 28px'}},
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
    h('button',{className:'nav-btn'+(tab==='factor'?' active':''),onClick:()=>{set({comptaTab:'factor'});}},
      iconEl('upload',15),'  Import Factor'),
    h('button',{className:'nav-btn'+(tab==='acheteurs'?' active':''),onClick:()=>{set({comptaTab:'acheteurs'});loadComptaAcheteurs();}},
      iconEl('users',15),'  Acheteurs'),
    h('button',{className:'nav-btn'+(tab==='comptes'?' active':''),onClick:()=>{set({comptaTab:'comptes'});loadComptaComptes();}},
      iconEl('file',15),'  Table des comptes'),
    h('div',{className:'sidebar-bottom'},
      h('button',{className:'nav-btn back-mysifa',onClick:()=>{window.location.href='/' }},
        '← Retour ',
        h('span',{className:'wm'},'My',h('span',null,'Sifa'))
      ),
      h('div',{className:'user-chip'},
        h('div',{className:'uc-name'},(S.user&&S.user.nom)?S.user.nom:''),
        h('div',{className:'uc-role'},(S.user&&S.user.role)?(ROLE_LABELS[S.user.role]||S.user.role):'')
      ),
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
        onClick:()=>{document.body.classList.toggle('light');localStorage.setItem('theme',document.body.classList.contains('light')?'light':'dark');render();},
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
    const inp=h('input',{type:'file',accept:'.xlsx,.xlsm,.xls',style:{display:'none'}});
    const zone=h('div',{className:'drop-zone',style:{marginBottom:'16px'}},
      h('div',{className:'dz-icon'},iconEl('cloud-upload',36)),
      h('div',{className:'dz-title'},'Dépose le fichier Excel Factor'),
      h('div',{className:'dz-sub'},'Clique ou glisse-dépose un fichier .xlsx')
    );
    zone.addEventListener('click',()=>inp.click());
    zone.addEventListener('dragover',e=>{e.preventDefault();zone.classList.add('drag');});
    zone.addEventListener('dragleave',()=>zone.classList.remove('drag'));
    zone.addEventListener('drop',e=>{
      e.preventDefault();zone.classList.remove('drag');
      const f=e.dataTransfer.files[0];if(f)comptaTransform(f);
    });
    inp.addEventListener('change',e=>{const f=e.target.files[0];if(f)comptaTransform(f);});

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
          : h('div',null,'✅ Aucun acheteur manquant.')
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
            ? ((pb==='compte_manquant'?'Compte manquant (Table des comptes)':'Acheteur non reconnu') + (rr.problem_detail?(' — '+rr.problem_detail):''))
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
    })() : h('div',{className:'card-empty'},'Aucun résultat. Charge un fichier Excel.');

    content=h('div',null, zone, inp,
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
    const code=h('input',{placeholder:'Code vendeur (optionnel)',className:'form-sel'});
    const siret=h('input',{placeholder:'SIRET (14 chiffres)',className:'form-sel'});
    const rs=h('input',{placeholder:'Raison sociale (ex: COME BACK GRAPHIC ASSOCIES)',className:'form-sel'});
    const editId=S.comptaEditAcheteurId;
    if(editId){
      const cur=(list||[]).find(x=>String(x.id)===String(editId));
      if(cur){
        code.value=cur.code_vendeur||'';
        siret.value=cur.identifiant||'';
        rs.value=cur.raison_sociale||'';
      }
    }
    const form=h('div',{className:'card',style:{padding:'16px',marginBottom:'16px'}},
      h('h3',{style:{fontSize:'14px',fontWeight:'700',marginBottom:'10px'}},editId?'Modifier un acheteur':'Ajouter / mettre à jour un acheteur'),
      h('div',{style:{display:'flex',gap:'10px',flexWrap:'wrap',alignItems:'center',marginBottom:'10px'}},
        h('span',{style:{fontSize:'12px',color:'var(--muted)'}},'Feuille: ACHETEURS'),
        impBtn,
        imp,
        editId ? h('button',{className:'btn-ghost',onClick:()=>set({comptaEditAcheteurId:null})},'Annuler') : null
      ),
      h('div',{className:'form-grid'},code,siret,rs),
      h('div',{style:{marginTop:'10px',display:'flex',gap:'10px'}},
        h('button',{className:'btn-sm',onClick:()=>{
          const payload={code_vendeur:code.value||null,identifiant:siret.value,raison_sociale:rs.value};
          if(editId){ comptaUpdateAcheteur(editId,payload); }
          else { comptaUpsertAcheteurs([payload]); }
          code.value='';siret.value='';rs.value='';
        }},editId?'Enregistrer':'Ajouter')
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
    const lib=h('input',{placeholder:'Libellé condensé (ex: Achat de Factures)',className:'form-sel'});
    const num=h('input',{placeholder:'Numéro de compte (ex: 519320000000)',className:'form-sel'});
    const editId=S.comptaEditCompteId;
    if(editId){
      const cur=(list||[]).find(x=>String(x.id)===String(editId));
      if(cur){
        lib.value=cur.libelle_condense||'';
        num.value=cur.numero_compte||'';
      }
    }
    const form=h('div',{className:'card',style:{padding:'16px',marginBottom:'16px'}},
      h('h3',{style:{fontSize:'14px',fontWeight:'700',marginBottom:'10px'}},editId?'Modifier un compte':'Ajouter / mettre à jour un libellé'),
      h('div',{style:{display:'flex',gap:'10px',flexWrap:'wrap',alignItems:'center',marginBottom:'10px'}},
        h('span',{style:{fontSize:'12px',color:'var(--muted)'}},'Feuille: TABLE DES COMPTES'),
        impBtn,
        imp,
        editId ? h('button',{className:'btn-ghost',onClick:()=>set({comptaEditCompteId:null})},'Annuler') : null
      ),
      h('div',{className:'form-grid'},lib,num),
      h('div',{style:{marginTop:'10px',display:'flex',gap:'10px'}},
        h('button',{className:'btn-sm',onClick:()=>{
          const payload={libelle_condense:lib.value,numero_compte:num.value};
          if(editId){ comptaUpdateCompte(editId,payload); }
          else { comptaUpsertComptes([payload]); }
          lib.value='';num.value='';
        }},editId?'Enregistrer':'Ajouter')
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
  }

  const body=h('div',{className:'app'},
    sidebar,
    h('main',{className:'main'},
      h('div',{className:'container'},
        topbar,
          h('h1',null,'MyCompta'),
        h('div',{className:'subtitle'},'Import Factor → mise en forme → copier vers CW'),
        content
      )
    )
  );

  return h('div',null,
    S.sidebarOpen?h('div',{className:'sidebar-overlay',onClick:closeSidebar}):null,
    body
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
  if(!S.expeRaw&&!S.expeRawLoading&&!S.expeRawError)queueMicrotask(()=>ensureExpeRawData());
  const results=S.expeResults;

  const deptInp=h('input',{type:'text',value:S.expeDept||'',placeholder:'59',onInput:e=>{S.expeDept=e.target.value;}});
  const fuelInp=h('input',{type:'number',step:'0.01',value:S.expeFuelPct||'',placeholder:'12.80',onInput:e=>{S.expeFuelPct=e.target.value;}});
  const kgInp=h('input',{type:'number',step:'1',value:S.expeKg||'',placeholder:'500',onInput:e=>{S.expeKg=e.target.value;}});
  const palInp=h('input',{type:'number',step:'1',value:S.expeNbPal||'',placeholder:'3',onInput:e=>{S.expeNbPal=e.target.value;}});
  [deptInp,fuelInp,kgInp,palInp].forEach(el=>el.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();expeCompute();}}));

  const form=h('div',{className:'card'},
    h('div',{className:'card-header'},
      h('h3',null,'Param\u00e8tres'),
      h('div',{style:{display:'flex',gap:10,alignItems:'center',flexWrap:'wrap'}},
        S.expeRawLoading?h('span',{className:'readonly-notice'},'Chargement des grilles\u2026'):null,
        S.expeRawError?h('span',{className:'badge-danger'},S.expeRawError):null,
        h('button',{className:'btn-ghost',onClick:()=>set({expeShowContacts:true})},iconEl('settings',13),' Contacts')
      )
    ),
    h('div',{style:{padding:'14px 18px'}},
      h('div',{className:'expe-fields'},
        h('div',{className:'expe-field'},h('label',null,'D\u00e9partement',h('span',{style:{fontWeight:400,marginLeft:6,fontSize:9,letterSpacing:0,textTransform:'none',color:'var(--text2)'}},'01 \u00e0 95')),deptInp),
        h('div',{className:'expe-field'},h('label',null,'Taxe carburant (%)'),fuelInp,h('div',{className:'expe-help'},'Appliqu\u00e9e au tarif de base')),
        h('div',{className:'expe-field'},h('label',null,'Poids (kg)'),kgInp,h('div',{className:'expe-help'},'Pour classement poids')),
        h('div',{className:'expe-field'},h('label',null,'Palettes'),palInp,h('div',{className:'expe-help'},'Coup\u00e9 max 5 / Ceva max 4'))
      ),
      h('div',{style:{display:'flex',gap:16,marginTop:14,flexWrap:'wrap'}},
        h('button',{className:'btn-sm',onClick:expeCompute,disabled:!!S.expeRawLoading||!S.expeRaw},'Calculer'),
        h('button',{className:'btn-sec',style:{marginLeft:4},onClick:()=>set({expeResults:null})},'R\u00e9initialiser')
      ),
      h('div',{className:'expe-note'},'Tarifs HT \u00b7 taxe carburant appliqu\u00e9e \u00b7 Coup\u00e9 max 5 pal \u00b7 Ceva max 4 pal \u00b7 Coquelle max 33 pal \u00b7 Dimotrans max 28 pal')
    )
  );

  if(!results)return h('div',null,form);

  const poidsCards=results.poids&&results.poids.length
    ? h('div',null,
        h('div',{className:'section-title'},'Classement au poids \u00b7 '+results.kg+' kg \u00b7 dept '+results.dept+' \u00b7 taxe '+results.fuel+'%'),
        h('div',{className:'expe-top3'},...results.poids.slice(0,3).map((r,i)=>renderExpeScore(r,i))),
        results.poids.length>3?renderExpeRankTable('Tous les tarifs (poids)',results.poids):null
      )
    : h('div',{className:'card-empty'},'Renseigne le poids pour voir le classement.');

  const palCards=results.palette&&results.palette.length
    ? h('div',{style:{marginTop:18}},
        h('div',{className:'section-title'},'Classement palette \u00b7 '+results.nbPal+' palette'+(results.nbPal>1?'s':'')+' \u00b7 dept '+results.dept+' \u00b7 taxe '+results.fuel+'%'),
        h('div',{className:'expe-top3'},...results.palette.slice(0,3).map((r,i)=>renderExpeScore(r,i))),
        results.palette.length>3?renderExpeRankTable('Tous les tarifs (palette)',results.palette):null
      )
    : h('div',{className:'card-empty',style:{marginTop:14}},'Renseigne le nombre de palettes pour voir le classement.');

  return h('div',null,form,poidsCards,palCards);
}
function renderExpeTransporteurs(){
  const contacts=expeEnsureContacts();
  const carriers=[
    {name:'Coupé',desc:'Express messagerie France, 24h',services:'Poids (max 1000 kg) \u00b7 Palette (max 5)'},
    {name:'Ceva',desc:'Messagerie France (Gefco)',services:'Poids (max 2000 kg) \u00b7 Palette (max 4)'},
    {name:'Coquelle',desc:'Réseau France, palette uniquement',services:'Palette (max 33)'},
    {name:'Dimotrans',desc:'France palette, 80\u00d7120',services:'Palette (max 28)'},
  ];
  return h('div',{className:'card'},
    h('div',{className:'card-header'},
      h('h3',null,'Mes transporteurs ('+carriers.length+')'),
      h('button',{className:'btn-ghost',onClick:()=>set({expeShowContacts:true})},iconEl('settings',13),' Modifier les contacts')
    ),
    h('div',{style:{padding:0}},...carriers.map(c=>{
      const col=expeCC(c.name);const ct=contacts[c.name];
      return h('div',{className:'import-row',style:{gap:14}},
        h('div',{style:{flex:1,minWidth:0}},
          h('div',{style:{fontWeight:700,color:'var(--text)',fontSize:14}},c.name),
          h('div',{style:{fontSize:11,color:'var(--muted)',marginTop:2}},c.desc),
          h('div',{style:{fontSize:10,color:'var(--text2)',marginTop:4,fontFamily:'monospace'}},c.services)
        ),
        ct?h('button',{className:'btn-ghost',style:{borderColor:col+'55',color:col,flexShrink:0},
          onClick:()=>expeOpenContact(c.name)},ct.type==='url'?'Portail':'Email'):null
      );
    }))
  );
}
function renderExpePoids(){
  const gram=parseFloat(S.expePoidsGram)||155;
  const coeff=parseFloat(S.expePoidsCoeff)||1.05;
  const rows=S.expePoidsRows||[];
  const rowWeights=rows.map(r=>{
    const q=parseFloat(r.qty)||0,l=parseFloat(r.laize)||0,d=parseFloat(r.dev)||0;
    if(!q||!l||!d)return null;
    return q*l*d*coeff*gram/1e6;
  });
  const palNb=parseFloat(S.expoPoidsPalNb)||0;
  const palKg=parseFloat(S.expoPoidsPalKg)||0;
  const palTotal=palNb*palKg;
  const etiqTotal=rowWeights.reduce((a,w)=>a+(w||0),0);
  const grandTotal=etiqTotal+palTotal;
  const fKg=v=>v.toFixed(3)+'\u00a0kg';
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
            el.addEventListener('input',e=>set({expePoidsGram:e.target.value}));
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
          el.addEventListener('input',e=>set({expePoidsCoeff:e.target.value}));return el;})()
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
    const w=rowWeights[i];
    const updateRow=(key,val)=>{const nr=rows.map((row,j)=>j===i?{...row,[key]:val}:row);set({expePoidsRows:nr});};
    return h('tr',null,
      h('td',{style:{...tdStyle,textAlign:'center',fontSize:'0.75rem',opacity:0.4}},String(i+1)),
      h('td',{style:tdStyle},inp(r.qty,v=>updateRow('qty',v))),
      h('td',{style:tdStyle},inp(r.laize,v=>updateRow('laize',v))),
      h('td',{style:tdStyle},inp(r.dev,v=>updateRow('dev',v))),
      h('td',{style:{...tdStyle,textAlign:'right',fontWeight:w?'600':'normal',opacity:w?1:0.25,fontSize:'0.85rem',whiteSpace:'nowrap'}},
        w?fKg(w):'—')
    );
  }));

  const addBtn=h('button',{style:{padding:'0.25rem 0.65rem',fontSize:'0.8rem',borderRadius:'6px',cursor:'pointer',
    border:'1px solid var(--border)',background:'transparent',color:'var(--fg)'}},'+\u00a0Ligne');
  addBtn.addEventListener('click',()=>set({expePoidsRows:[...rows,{qty:'',laize:'',dev:''}]}));
  const delBtn=(rows.length>1)?h('button',{style:{padding:'0.25rem 0.65rem',fontSize:'0.8rem',borderRadius:'6px',cursor:'pointer',
    border:'1px solid var(--border)',background:'transparent',color:'var(--fg)',marginLeft:'0.4rem'}},'\u2212\u00a0Ligne'):null;
  if(delBtn)delBtn.addEventListener('click',()=>set({expePoidsRows:rows.slice(0,-1)}));

  const rowsCard=h('div',{className:'card',style:{marginBottom:'1rem'}},
    h('div',{className:'card-header',style:{display:'flex',alignItems:'center',justifyContent:'space-between'}},
      h('span',null,'Étiquettes'),
      h('div',null,addBtn,delBtn||null)
    ),
    h('div',{style:{overflowX:'auto',padding:'0.25rem 0.75rem 0.75rem'}},
      h('table',{style:{width:'100%',borderCollapse:'collapse',fontSize:'0.88rem'}},thead,tbody)
    ),
    etiqTotal>0?h('div',{style:{padding:'0.1rem 1rem 0.75rem',textAlign:'right',fontSize:'0.88rem',opacity:0.75}},
      'Sous-total étiquettes\u00a0: ',h('strong',null,fKg(etiqTotal))):null
  );

  const palCard=h('div',{className:'card',style:{marginBottom:'1rem'}},
    h('div',{className:'card-header'},h('span',null,'Palette (optionnel)')),
    h('div',{style:{padding:'1rem',display:'flex',gap:'1rem',flexWrap:'wrap',alignItems:'flex-end'}},
      h('div',{style:{flex:'0 0 100px'}},
        h('label',{style:{display:'block',fontSize:'0.75rem',opacity:0.65,marginBottom:'0.4rem'}},'Nb palettes'),
        (()=>{const el=h('input',{type:'number',min:'0',step:'1',placeholder:'0',value:S.expoPoidsPalNb,
          style:{width:'100%',padding:'0.3rem 0.5rem',borderRadius:'6px',border:'1px solid var(--border)',
                 background:'var(--card)',color:'var(--fg)',fontSize:'0.85rem'}});
          el.addEventListener('input',e=>set({expoPoidsPalNb:e.target.value}));return el;})()
      ),
      h('div',{style:{flex:'0 0 120px'}},
        h('label',{style:{display:'block',fontSize:'0.75rem',opacity:0.65,marginBottom:'0.4rem'}},'Poids / palette (kg)'),
        (()=>{const el=h('input',{type:'number',min:'0',step:'any',placeholder:'0',value:S.expoPoidsPalKg,
          style:{width:'100%',padding:'0.3rem 0.5rem',borderRadius:'6px',border:'1px solid var(--border)',
                 background:'var(--card)',color:'var(--fg)',fontSize:'0.85rem'}});
          el.addEventListener('input',e=>set({expoPoidsPalKg:e.target.value}));return el;})()
      ),
      palTotal>0?h('div',{style:{paddingBottom:'0.2rem',fontSize:'0.88rem',opacity:0.75}},
        'Sous-total\u00a0: ',h('strong',null,fKg(palTotal))):null
    )
  );

  const totalCard=h('div',{className:'card',style:{textAlign:'center',padding:'1.5rem 1rem',
    background:'var(--accent)',color:'#fff',borderRadius:'12px',marginBottom:'0.5rem'}},
    h('div',{style:{fontSize:'0.78rem',letterSpacing:'0.08em',opacity:0.85,marginBottom:'0.4rem'}},'POIDS TOTAL ESTIMÉ'),
    h('div',{style:{fontSize:'2.4rem',fontWeight:'700',letterSpacing:'-1px',lineHeight:1.1}},
      grandTotal>0?grandTotal.toFixed(3)+'\u00a0kg':'—'),
    grandTotal>0&&palTotal>0?h('div',{style:{fontSize:'0.8rem',opacity:0.8,marginTop:'0.35rem'}},
      'dont palette\u00a0: '+fKg(palTotal)):null
  );

  return h('div',{style:{maxWidth:'680px'}},
    h('p',{style:{opacity:0.55,fontSize:'0.82rem',marginBottom:'1.25rem',fontStyle:'italic'}},
      'Formule\u00a0: Qté\u2009(mille)\u2009×\u2009Laize\u2009×\u2009Développé\u2009×\u2009Coeff\u2009×\u2009Grammage\u2009/\u20091\u202f000\u202f000'),
    paramCard,rowsCard,palCard,totalCard
  );
}

function renderExpe(){
  const isLight=document.body.classList.contains('light');
  const tab=S.expeTab||'comparateur';

  const sidebar=h('nav',{className:'sidebar'},
    h('div',{className:'logo'},
      h('div',{className:'logo-brand'},'My',h('span',null,'Expé')),
      h('div',{className:'logo-sub'},'by SIFA')
    ),
    h('button',{className:'nav-btn'+(tab==='comparateur'?' active':''),onClick:()=>set({expeTab:'comparateur'})},
      iconEl('package',15),'  Comparateur'),
    h('button',{className:'nav-btn'+(tab==='transporteurs'?' active':''),onClick:()=>set({expeTab:'transporteurs'})},
      iconEl('truck',15),'  Transporteurs'),
    h('button',{className:'nav-btn'+(tab==='poids'?' active':''),onClick:()=>set({expeTab:'poids'})},
      iconEl('calculator',15),'  Poids envoi'),
    h('div',{className:'sidebar-bottom'},
      h('button',{className:'nav-btn back-mysifa',onClick:()=>{window.location.href='/'}},
        '← Retour ',h('span',{className:'wm'},'My',h('span',null,'Sifa'))
      ),
      h('div',{className:'user-chip'},
        h('div',{className:'uc-name'},(S.user&&S.user.nom)?S.user.nom:''),
        h('div',{className:'uc-role'},(S.user&&S.user.role)?(ROLE_LABELS[S.user.role]||S.user.role):'')
      ),
      (()=>{
        const b=h('button',{className:'support-btn',title:'Contacter le support',onClick:()=>set({contactOpen:true})});
        const ico=h('span',{className:'support-ico'});
        try{ico.innerHTML=(window.MySifaSupport&&typeof window.MySifaSupport.iconSvg==='function')?window.MySifaSupport.iconSvg():'';}catch(e){ico.innerHTML='';}
        b.appendChild(ico);b.appendChild(h('span',null,'Contacter le support'));return b;
      })(),
      h('button',{className:'theme-btn',onClick:()=>{document.body.classList.toggle('light');localStorage.setItem('theme',document.body.classList.contains('light')?'light':'dark');render();}},
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
      h('div',{className:'mobile-topbar-sub'},tab==='transporteurs'?'Transporteurs':tab==='poids'?'Poids envoi':'Comparateur tarifs')
    ),
    h('button',{type:'button',className:'mobile-home-btn',onClick:()=>{window.location.href='/'},'aria-label':'Accueil'},iconEl('home',20))
  );

  const content=tab==='transporteurs'?renderExpeTransporteurs():tab==='poids'?renderExpePoids():renderExpeComparateur();

  return h('div',null,
    S.sidebarOpen?h('div',{className:'sidebar-overlay',onClick:closeSidebar}):null,
    h('div',{className:'app'},
      sidebar,
      h('main',{className:'main'},
        h('div',{className:'container'},
          topbar,
          h('h1',null,'MyExpé'),
          h('div',{className:'subtitle'},tab==='comparateur'
            ?'Coupé · Coquelle · Ceva · Dimotrans — meilleur prix au poids et à la palette'
            :tab==='poids'?'Estimation du poids d\'un envoi d\'étiquettes'
            :'Vos transporteurs et moyens de contact'),
          content
        )
      )
    ),
    S.expeShowContacts?renderExpeContactModal():null
  );
}

// ── Loaders ─────────────────────────────────────────────────────
async function loadFilters(){try{S.filters=await api('/api/filters')||{};S.OPS_CONFIG=await api('/api/config/operations')||{};}catch{}}
function buildParams(){
  const p=new URLSearchParams();
  if(isAdmin(S.user)){
    (S.fv.operateurs||[]).forEach(o=>p.append('operateur',o));
    (S.fv.dossiers||[]).forEach(d=>p.append('no_dossier',d));
  }
  if(S.fv.date_from)p.set('date_from',S.fv.date_from);
  if(S.fv.date_to)p.set('date_to',S.fv.date_to);
  return p;
}

async function loadHist(){const d=await api('/api/dashboard/historique?'+buildParams());if(d)S.historique=d;}
async function loadProd(){const d=await api('/api/dashboard/production?'+buildParams());if(d)S.production=d;}
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
  const errEl=h('div',{className:'login-error'+(S.loginError?' show':''),id:'login-error'},S.loginError||'');
  const emailI=h('input',{type:'text',id:'login-email',name:'email',autocomplete:'username',placeholder:'identifiant ou email'});
  const pwdI=h('input',{type:'password',id:'login-password',name:'password',autocomplete:'current-password',placeholder:'••••••••'});
  const submit=e=>{
    e.preventDefault();
    if(S.loginSubmitting)return;
    doLogin(emailI.value,pwdI.value);
  };
  return h('div',{className:'login-page'},
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
          h('div',{className:'field'},h('label',{'for':'login-password'},'Mot de passe'),pwdI),
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
  const items=[
    ...(canPlanningNav(S.user)?[{key:'_planning',label:'Planning',icon:'calendar'}]:[]),
    {key:'production',label:'Production',icon:'wrench'},
    {key:'traceabilite',label:'Traçabilité',icon:'layers'},
    ...(admin?[{key:'rentabilite',label:'Rentabilité',icon:'trending-up'}]:[]),
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
      return btn;
    }),
    h('div',{className:'sidebar-bottom'},
      h('button',{className:'nav-btn back-mysifa',onClick:()=>{window.location.href='/' }},
        '← Retour ',
        h('span',{className:'wm'},'My',h('span',null,'Sifa'))
      ),
      h('div',{
        className:'user-chip',
        style:{cursor:'pointer'},
        title:'Modifier mon profil',
        onClick:()=>{set({page:'profil'});}
      },
        h('div',{className:'uc-name'},(S.user&&S.user.nom)?S.user.nom:''),
        h('div',{className:'uc-role'},(S.user&&S.user.role)?(ROLE_LABELS[S.user.role]||S.user.role):''),
        h('div',{style:{fontSize:'10px',color:'var(--accent)',marginTop:'3px',display:'flex',alignItems:'center',gap:'4px'}},iconEl('edit',10),' Mon profil')
      ),
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
      h('button',{className:'theme-btn',onClick:()=>{document.body.classList.toggle('light');localStorage.setItem('theme',document.body.classList.contains('light')?'light':'dark');render();}},
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
      h('div',{className:'user-chip'},
        h('div',{className:'uc-name'},(S.user&&S.user.nom)?S.user.nom:''),
        h('div',{className:'uc-role'},'Super admin')
      ),
      h('button',{className:'theme-btn',onClick:()=>{document.body.classList.toggle('light');localStorage.setItem('theme',document.body.classList.contains('light')?'light':'dark');render();}},
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

function makeDateInput(value, onChange){
  const inp = h('input',{
    type:'date',
    value: value || '',
    style:{
      background:'var(--bg)',
      border:'1px solid var(--border)',
      borderRadius:'8px',
      padding:'8px 10px',
      color:'var(--text)',
      fontSize:'12px',
      fontFamily:'inherit',
      outline:'none',
      minWidth:'148px',
    }
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
  const admin=isAdmin(S.user);
  const ops=S.filters.operators||[];
  const dos=S.filters.dossiers||[];
  const parts=[];
 
  if(admin){
    // ── Multi-select opérateurs ──────────────────────────────────
    parts.push(makeMultiSelect(
      'Opérateurs',
      ops.map(o=>({value:o,label:opName(o)})),
      S.fv.operateurs,
      (sel)=>{ S.fv.operateurs=sel; }
    ));
 
    // ── Multi-select dossiers ────────────────────────────────────
    parts.push(makeMultiSelect(
      'Dossiers',
      dos.map(d=>({value:d,label:'Dos. '+d})),
      S.fv.dossiers,
      (sel)=>{ S.fv.dossiers=sel; }
    ));
  }
 
  const df=makeDateInput(S.fv.date_from, v=>{S.fv.date_from=v;});
  const dt=makeDateInput(S.fv.date_to,   v=>{S.fv.date_to=v;});
  parts.push(h('div',{className:'filter-group'},h('label',null,'Du'),df));
  parts.push(h('div',{className:'filter-group'},h('label',null,'Au'),dt));
  parts.push(h('button',{onClick:applyF},'Filtrer'));
  return h('div',{className:'filters'},...parts);
}
 
// ── Composant multi-select avec cases à cocher ──────────────────
function makeMultiSelect(label, options, selected, onChange){
  // NOTE: `selected` est un tableau stocké dans S.fv.* et muté via onChange(sel).
  // Ce composant doit rester fluide (multi-clic) => on lit toujours la valeur actuelle via getSelected().
  const getSelected = ()=> Array.isArray(selected) ? selected : [];
  const isSelected = v => getSelected().includes(v);
  const count = getSelected().length;
 
  // Bouton déclencheur
  const trigger = h('button',{
    className:'multisel-trigger',
    style:{
      background:'var(--bg)',border:'1px solid var(--border)',borderRadius:'8px',
      padding:'8px 12px',color:'var(--text)',fontSize:'12px',fontFamily:'inherit',
      cursor:'pointer',display:'flex',alignItems:'center',gap:'6px',minWidth:'160px',
      justifyContent:'space-between'
    }
  },
    h('span',null, count>0 ? label+' ('+count+')' : label),
    h('span',{style:{opacity:'.5'}},'▾')
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
    trigger.querySelector('span').textContent = newSel.length>0?label+' ('+newSel.length+')':label;
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
      trigger.querySelector('span').textContent = newSel.length>0?label+' ('+newSel.length+')':label;
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
      h('div',{className:'si-label'},'Qualité de saisie — Sanity Score')
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
  S.traceabilite = null; render();
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
    const d = await api('/api/fabrication/traceability?no_dossier='+encodeURIComponent(ref));
    S.traceabiliteDossier = d;
  }catch(e){ S.traceabiliteDossier = {error:e.message}; }
  render();
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

  // ── Tri ─────────────────────────────────────────────────────────
  const COL_KEY = {ref:'reference',client:'client',designation:'designation',machine:'machine_nom',statut:'statut',matieres:'nb_matieres'};
  if(Srt.col){
    const key = COL_KEY[Srt.col]||Srt.col;
    dossiers = [...dossiers].sort((a,b)=>{
      let av=a[key]||'', bv=b[key]||'';
      if(typeof av==='number'||typeof bv==='number'){av=Number(av)||0;bv=Number(bv)||0;}
      else{av=String(av).toLowerCase();bv=String(bv).toLowerCase();}
      return Srt.dir==='asc'?(av>bv?1:av<bv?-1:0):(av<bv?1:av>bv?-1:0);
    });
  }

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
      type:'text', id:inputId, value:val, placeholder:'Rechercher…'
    });
    inp.addEventListener('input', e=>{
      const selStart = e.target.selectionStart;
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
    const sel = h('select',{id:inputId},
      ...options.map(o=>h('option',{value:o.val,selected:val===o.val},o.label)));
    sel.addEventListener('change', e=>{ onChange(e.target.value); render(); });
    return h('div',{className:'filter-group'},
      h('label',null,label),
      sel
    );
  };
  const hasActiveFilter = !!(F.ref||F.client||F.machine||F.statut);

  const filterBar = h('div',{className:'filters',style:{marginBottom:'18px'}},
    filterInput('trac-f-ref',    'Référence',  F.ref,    v=>{S.tracFilters.ref=v;}),
    filterInput('trac-f-client', 'Client',     F.client, v=>{S.tracFilters.client=v;}),
    filterSelect('trac-f-machine','Machine',
      [{val:'',label:'Toutes machines'},...machinesUniq.map(m=>({val:m,label:m}))],
      F.machine, v=>{S.tracFilters.machine=v;}
    ),
    filterSelect('trac-f-statut','Statut', statuts, F.statut, v=>{S.tracFilters.statut=v;}),
    hasActiveFilter ? h('button',{
      style:{alignSelf:'flex-end'},
      onClick:()=>{ S.tracFilters={ref:'',client:'',machine:'',statut:''}; render(); }
    },'✕ Effacer') : null
  );

  // ── Lignes tableau ──────────────────────────────────────────────
  const rows = dossiers.map(dos=>{
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
      h('td',null, statutBadge(dos.statut||'attente')),
      h('td',null,
        hasMatieres
          ? h('span',{className:'badge badge-ok'}, (dos.nb_matieres||0)+' bobine'+(dos.nb_matieres>1?'s':''))
          : h('span',{className:'badge',style:{opacity:.5}},'Aucune')
      )
    );
  });

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

  return h('div',{className:'card'},
    h('div',{className:'card-header'},
      h('h3',null,'Traçabilité par dossier'),
      h('span',{className:'badge'},dossiers.length+(dossiers.length!==allDossiers.length?'/'+allDossiers.length:'')+' dossier'+(allDossiers.length!==1?'s':''))
    ),
    filterBar,
    h('div',{style:{overflowX:'auto',padding:'0 0 8px'}}, table)
  );
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
    return h('tr',null,
      h('td',null,h('span',{style:{fontFamily:'monospace',fontWeight:'700',color:'var(--accent)'}},m.code_barre)),
      h('td',null,m.machine_nom||'—'),
      h('td',null,m.operateur||'—'),
      h('td',null,dateStr)
    );
  });

  const matiereTable = matieres.length
    ? h('table',{className:'table-std'},
        h('thead',null,h('tr',null,
          h('th',null,'Code barre'),h('th',null,'Machine'),h('th',null,'Opérateur'),h('th',null,'Heure scan')
        )),
        h('tbody',null,...matiereRows)
      )
    : h('div',{className:'card-empty',style:{padding:'16px'}},'Aucune bobine matière scannée pour ce dossier');

  return h('div',null,
    backBtn,
    h('div',{className:'card'},
      h('div',{className:'card-header'},
        h('h3',null,dos.reference||'Dossier'),
        h('span',{className:'badge badge-ok'},finRow?'Terminé':'En cours')
      ),
      infoGrid,
      h('div',{style:{padding:'0 20px 16px'}},
        h('div',{style:{fontWeight:'800',fontSize:'12px',color:'var(--text2)',
          textTransform:'uppercase',letterSpacing:'.4px',marginBottom:'10px'}},
          iconEl('box',12),' Bobines matières utilisées ('+matieres.length+')'
        ),
        h('div',{style:{overflowX:'auto'}}, matiereTable)
      )
    )
  );
}

function renderProdPage(){
  const subPage = S.subPage || 'kpis';
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
        if(t.key==='kpis'&&!S.production) await loadProd();
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
function renderProdKpis(){
  const d=S.production;
  if(!d)return h('div',{className:'card-empty'},'Chargement des données de production…');
  if(d.blocked)return h('div',{className:'card'},h('div',{className:'card-blocked'},h('div',{className:'cb-icon'},iconEl('lock',32)),h('div',{className:'cb-msg'},d.message)));
  const prod = d.produit||{};
  const tt=d.temps_totaux||{};const parts=[];

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
  parts.push(h('div',{className:'section-title'},iconEl('box',13),' Quantités'));
  parts.push(h('div',{className:'stats'},
    h('div',{className:'stat'},h('div',{className:'stat-label'},'Dossiers produits'),h('div',{className:'stat-value'},fN(prod.dossiers||0))),
    h('div',{className:'stat'},h('div',{className:'stat-label'},'Qté étiquettes'),h('div',{className:'stat-value'},fN(prod.etiquettes||0))),
    h('div',{className:'stat'},h('div',{className:'stat-label'},'Métrage'),h('div',{className:'stat-value'},fN(prod.metrage_m||0)+' m')),
    h('div',{className:'stat'},h('div',{className:'stat-label'},'Vitesse'),h('div',{className:'stat-value'},((d.vitesse_m_min!=null)?Number(d.vitesse_m_min).toFixed(2):'0.00')+' m/min')),
  ));
  parts.push(h('div',{className:'section-title'},iconEl('clock',13),' Temps'));
  const prodInclArrets = (Number(tt.production_min||0) + Number(tt.arret_min||0));
  parts.push(h('div',{className:'time-kpi'},
    h('div',{className:'time-card'},h('div',{className:'tc-label',style:{display:'inline-flex',alignItems:'center',gap:'6px'}},iconEl('wrench',12),' Calage'),h('div',{className:'tc-value'},fMin(tt.calage_min))),
    h('div',{className:'time-card'},h('div',{className:'tc-label',style:{display:'inline-flex',alignItems:'center',gap:'6px'}},iconEl('play',12),' Production'),h('div',{className:'tc-value'},fMin(prodInclArrets))),
    h('div',{className:'time-card'},h('div',{className:'tc-label',style:{display:'inline-flex',alignItems:'center',gap:'6px'}},iconEl('alert-triangle',12),' Arrêts'),h('div',{className:'tc-value'},fMin(tt.arret_min))),
  ));
  const byDos = d.by_dossier || d.dossier_times || [];

  function renderAggCard(title, rows, keyLabel){
    if(!rows||!rows.length) return null;
    return h('div',{className:'card'},
      h('div',{className:'card-header'},h('h3',null,title),h('span',{style:{fontSize:'11px',color:'var(--muted)'}},rows.length+' items')),
      h('div',{style:{overflowX:'auto'}},h('table',null,
        h('thead',null,h('tr',null,h('th',null,keyLabel),h('th',null,'Dossiers'),h('th',null,'Étiquettes'),h('th',null,'Métrage'),h('th',null,'Calage'),h('th',null,'Prod'),h('th',null,'Arrêts'),h('th',null,'Vitesse'))),
        h('tbody',null,...rows.map(r=>h('tr',null,
          h('td',{style:{fontWeight:'700'}},keyLabel==='Opérateur'?opName(r.key):r.key),
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

  parts.push(h('div',{className:'section-title'},'📌 Synthèse détaillée'));
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

    parts.push(h('div',{className:'card'},h('div',{className:'card-header'},h('h3',null,'Par numéro de dossier'),h('span',{style:{fontSize:'11px',color:'var(--muted)'}},rowsAgg.length+' dossiers')),
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
        h('tbody',null,...rowsAgg.map(r=>h('tr',null,
          h('td',{style:{fontWeight:'600',fontFamily:'monospace',color:'var(--text)'}},r.no_dossier||''),
          h('td',{style:{fontFamily:'monospace'}},fN(r.etiquettes||0)),
          h('td',{style:{fontFamily:'monospace'}},fN(r.metrage_m||0)+' m'),
          h('td',{style:{fontFamily:'monospace',color:'var(--text2)'}},fMin(r.temps_calage_min)),
          h('td',{style:{fontFamily:'monospace',color:'var(--text2)'}},fMin(r.temps_prod_min)),
          h('td',{style:{fontFamily:'monospace',color:'var(--text2)'}},fMin(r.temps_arret_min)),
          h('td',{style:{fontFamily:'monospace',fontWeight:'800',color:'var(--warn)'}},(Number(r.temps_prod_min||0)>0? (Number(r.metrage_m||0)/Number(r.temps_prod_min||1)).toFixed(2):'0.00')+' m/min')
        )))
      ))
    ));
  }
  const byOp=d.by_operator||[];
  const byMach=d.by_machine||[];
  const byDay=d.by_day||[];
  parts.push(renderAggCard('Par opérateur',byOp,'Opérateur'));
  parts.push(renderAggCard('Par machine',byMach,'Machine'));
  parts.push(renderAggCard('Par jour',byDay,'Jour'));

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
  // Convertit '01/04/2026 12:53:00C' → {date:'2026-04-01', time:'12:53'}
  if (!dateStr) return { date: '', time: '' };
  const s = dateStr.replace(/C$/, '').trim();
  // Format DD/MM/YYYY HH:MM:SS
  const m = s.match(/^(\d{2})\/(\d{2})\/(\d{4})\s+(\d{2}):(\d{2})/);
  if (m) return { date: m[3]+'-'+m[2]+'-'+m[1], time: m[4]+':'+m[5] };
  // Format ISO YYYY-MM-DD
  const m2 = s.match(/^(\d{4}-\d{2}-\d{2})(?:T(\d{2}:\d{2}))?/);
  if (m2) return { date: m2[1], time: m2[2] || '00:00' };
  return { date: '', time: '' };
}
 
function inputValToFrDate(dateVal, timeVal) {
  // Convertit '2026-04-01' + '12:53' → '01/04/2026 12:53:00'
  if (!dateVal) return datetime_now_fr();
  const [y, mo, d] = dateVal.split('-');
  const t = timeVal || '00:00';
  return d+'/'+mo+'/'+y+' '+t+':00';
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
    placeholder: 'HH:MM',
    value: (String(tv || '00:00').slice(0,5) || ''),
    style: { width: '110px', fontFamily: 'monospace' }
  });
  timeI.setAttribute('maxlength', '5');

  function normalizeTime(raw){
    const s = String(raw||'').trim().replace(/[^\d:]/g,'');
    // Accepter "930" => "09:30", "9:30" => "09:30"
    if(/^\d{3,4}$/.test(s)){
      const z = s.padStart(4,'0');
      return z.slice(0,2)+':'+z.slice(2,4);
    }
    const m = s.match(/^(\d{1,2}):(\d{1,2})$/);
    if(m){
      const hh = String(m[1]).padStart(2,'0');
      const mm = String(m[2]).padStart(2,'0');
      return hh+':'+mm;
    }
    if(/^\d{2}:\d{2}$/.test(s)) return s;
    return '';
  }
  function isValidHHMM(s){
    const m = String(s||'').match(/^(\d{2}):(\d{2})$/);
    if(!m) return false;
    const hh = parseInt(m[1],10), mm = parseInt(m[2],10);
    return hh>=0 && hh<=23 && mm>=0 && mm<=59;
  }
  function getTimeVal(){
    const norm = normalizeTime(timeI.value);
    if(norm) timeI.value = norm;
    return isValidHHMM(timeI.value) ? timeI.value : null;
  }
  timeI.addEventListener('input', ()=>{
    // Filtrer et auto-inserer ":" après 2 chiffres (sans être intrusif).
    let v = String(timeI.value||'').replace(/[^\d]/g,'').slice(0,4);
    if(v.length >= 3) v = v.slice(0,2)+':'+v.slice(2);
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
    opField = h('input', { type: 'text', value: (S.user && S.user.operateur_lie) ? S.user.operateur_lie : '' });
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
        h('div', null, h('label', null, 'Date & Heure (JJ/MM/AAAA HH:MM)'), dateWrapper),
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
            if(!dtVal){ toast('Heure invalide (format HH:MM, 24h)', 'error'); return; }
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
 
function renderSaisies(){
  const d=S.saisies;
  if(!d) return h('div',{className:'card-empty'},'Chargement...');
  if(!isAdmin(S.user)&&!(S.user && S.user.operateur_lie))
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
  // Pour chaque dossier on cherche la saisie "Début dossier" (code 01) et on
  // soustrait son metrage_prevu au metrage_reel de la saisie "Fin dossier" (code 89).
  (function(){
    const debutByDossier = {}; // no_dossier → metrage_prevu (dernier début)
    // Parcours chronologique pour associer début/fin
    const chrono = [...rows].sort((a,b)=>(a.date_operation||'').localeCompare(b.date_operation||''));
    chrono.forEach(r=>{
      if(r.operation_code==='01' && r.no_dossier && r.metrage_prevu!=null){
        debutByDossier[r.no_dossier] = r.metrage_prevu;
      }
      if(r.operation_code==='89' && r.no_dossier && r.metrage_reel!=null){
        const debut = debutByDossier[r.no_dossier];
        if(debut!=null) r._metrage_dossier = r.metrage_reel - debut;
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
    const tr=h('tr',{className:'data-row',style:{cursor:readOnly?'default':'pointer'}});
    // PAR — contrastes plus forts + catégorie production en vert
    const opCode = row.operation_code || '';
    const cat    = row.operation_category || '';

    let rowBg = '';
    if (row.operation_severity === 'critique') {
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
 
    tr.appendChild(h('td',{style:{fontSize:'11px',color:'var(--muted)',whiteSpace:'nowrap'}},fD(row.date_operation)));
    tr.appendChild(h('td',null,row.operation||'-'));
    tr.appendChild(h('td',{style:{whiteSpace:'nowrap',color:'var(--muted)'}},fmtDurMin(row.duree_min)));
    tr.appendChild(h('td',null,opName(row.operateur)));
    tr.appendChild(h('td',null,row.machine||'-'));
    tr.appendChild(h('td',null,row.no_dossier||'-'));
    tr.appendChild(h('td',null,fN(row.quantite_traitee)));
    tr.appendChild(h('td',{style:{color:'var(--c3)'}},
      row._metrage_dossier!=null
        ? h('span',{title:'Métrage dossier = compteur fin − compteur début\nFin: '+fN(row.metrage_reel)+' m — Début: '+fN(row.metrage_reel - row._metrage_dossier)+' m'},
            '⇒ '+fN(row._metrage_dossier)+' m')
        : row.metrage_reel!=null ? fN(row.metrage_reel)+' m'
        : row.metrage_prevu!=null ? h('span',{style:{color:'var(--muted)',fontSize:'11px'}},fN(row.metrage_prevu)+' m (déb.)')
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
    headerRight.appendChild(h('button',{className:'btn-ghost',onClick:()=>exportBlob('/api/saisies/export-modifiees','saisies_modifiees.xlsx')},iconEl('download',13),' Export'));
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

// ── Page profil (utilisateur courant) ──────────────────────────
async function saveProfil(body){
  try{
    const r=await api('/api/auth/me',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!r)return;
    toast('Profil mis à jour');
    // Recharger les infos user
    const u=await api('/api/auth/me');
    if(u)S.user={...S.user,...u};
    render();
  }catch(e){toast(e.message,'error');}
}

function renderProfil(userData){
  const inputs={};

  const mkField=(label,key,type='text',val='')=>{
    const i=h('input',{type,placeholder:label,value:(userData && (key in userData) ? (userData[key]||'') : '') || val});
    inputs[key]=i;
    return h('div',{style:{marginBottom:'14px'}},
      h('label',{style:{display:'block',fontSize:'11px',fontWeight:'600',color:'var(--muted)',textTransform:'uppercase',letterSpacing:'.5px',marginBottom:'5px'}},label),
      i
    );
  };

  const fields=[
    mkField('Nom complet','nom'),
    mkField('Email','email','email'),
    mkField('Téléphone','telephone','tel'),
  ];

  // Champ mot de passe
  const pwdI=h('input',{type:'password',placeholder:'Nouveau mot de passe (laisser vide = inchangé)'});
  const pwdCI=h('input',{type:'password',placeholder:'Confirmer le mot de passe'});
  inputs.password=pwdI;inputs.password_confirm=pwdCI;

  const pwdSection=h('div',null,
    h('div',{style:{marginBottom:'14px'}},
      h('label',{style:{display:'block',fontSize:'11px',fontWeight:'600',color:'var(--muted)',textTransform:'uppercase',letterSpacing:'.5px',marginBottom:'5px'}},'Nouveau mot de passe'),
      pwdI
    ),
    h('div',{style:{marginBottom:'14px'}},
      h('label',{style:{display:'block',fontSize:'11px',fontWeight:'600',color:'var(--muted)',textTransform:'uppercase',letterSpacing:'.5px',marginBottom:'5px'}},'Confirmer le mot de passe'),
      pwdCI
    )
  );

  const saveBtn=h('button',{className:'btn',onClick:async()=>{
    const body={};
    Object.entries(inputs).forEach(([k,el])=>{
      if(el.type==='checkbox') body[k]=el.checked?1:0;
      else if(el.value!==undefined) body[k]=el.value;
    });
    if(!body.password) delete body.password;
    if(!body.password_confirm) delete body.password_confirm;
    await saveProfil(body);
  }},'💾 Enregistrer');

  const infos=userData?[
    userData.created_at?h('p',{style:{fontSize:'11px',color:'var(--muted)',marginTop:'8px'}},'Créé le '+fD(userData.created_at)):null,
    userData.last_login?h('p',{style:{fontSize:'11px',color:'var(--muted)'}},'Dernière connexion : '+fD(userData.last_login)):null,
  ]:[];

  return h('div',{className:'card',style:{padding:'28px',maxWidth:'520px'}},
    h('h2',{style:{fontSize:'18px',fontWeight:'700',marginBottom:'6px',display:'inline-flex',alignItems:'center',gap:'8px'}},iconEl('user',18),'Mon profil'),
    h('p',{style:{fontSize:'13px',color:'var(--muted)',marginBottom:'24px'}},'Modifiez vos informations personnelles'),
    ...fields,
    h('hr',{style:{border:'none',borderTop:'1px solid var(--border)',margin:'20px 0'}}),
    pwdSection,
    saveBtn,
    ...infos
  );
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

// ── Calculette flottante (MyStock + MyExpé) ──────────────────────
(function(){
  let _open = false, _expr = '', _val = '0', _justEq = false;
  const KEYS = [
    ['C','⌫','%','÷'],
    ['7','8','9','×'],
    ['4','5','6','−'],
    ['1','2','3','+'],
    ['0','.','='],
  ];
  function _calc_press(k){
    if(k==='C'){_expr='';_val='0';_justEq=false;return;}
    if(k==='⌫'){_val=_val.length>1?_val.slice(0,-1):'0';return;}
    if(k==='±'){_val=_val.startsWith('-')?_val.slice(1):'-'+_val;return;}
    if(k==='%'){try{_val=String(parseFloat(_val)/100);}catch(e){}return;}
    if(k==='='){
      try{
        let expr=(_justEq?_val:_expr+_val)
          .replace(/÷/g,'/').replace(/×/g,'*').replace(/−/g,'-');
        // eslint-disable-next-line no-new-func
        let r=Function('"use strict";return ('+expr+')')();
        _expr=expr+'=';_val=String(Math.round(r*1e10)/1e10);_justEq=true;
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
  function _calc_render(){
    const fab=document.getElementById('_calc_fab');
    if(!fab)return;
    const panel=document.getElementById('_calc_panel');
    if(!panel)return;
    panel.style.display=_open?'':'none';
    panel.querySelector('._cv').textContent=_val;
    panel.querySelector('._ce').textContent=_expr;
  }
  function _calc_mount(){
    if(document.getElementById('_calc_fab'))return;
    const fab=document.createElement('button');
    fab.id='_calc_fab';fab.className='calc-fab';fab.title='Calculette';
    fab.innerHTML='<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="2" width="16" height="20" rx="2"/><line x1="8" y1="6" x2="16" y2="6"/><circle cx="8.5" cy="11" r=".8" fill="currentColor" stroke="none"/><circle cx="12" cy="11" r=".8" fill="currentColor" stroke="none"/><circle cx="15.5" cy="11" r=".8" fill="currentColor" stroke="none"/><circle cx="8.5" cy="15" r=".8" fill="currentColor" stroke="none"/><circle cx="12" cy="15" r=".8" fill="currentColor" stroke="none"/><circle cx="15.5" cy="15" r=".8" fill="currentColor" stroke="none"/><line x1="8" y1="19" x2="16" y2="19"/></svg>';
    fab.onclick=()=>{_open=!_open;_calc_render();};
    document.body.appendChild(fab);
    const panel=document.createElement('div');
    panel.id='_calc_panel';panel.className='calc-panel';panel.style.display='none';
    const disp=document.createElement('div');disp.className='calc-display';
    const ce=document.createElement('div');ce.className='calc-expr _ce';
    const cv=document.createElement('div');cv.className='calc-val _cv';cv.textContent='0';
    disp.append(ce,cv);panel.appendChild(disp);
    const grid=document.createElement('div');grid.className='calc-grid';
    KEYS.forEach(row=>row.forEach(k=>{
      const btn=document.createElement('button');
      btn.className='calc-key'+(k==='='?' eq':['+','-','×','÷','−'].includes(k)?' op':['C','⌫','±','%'].includes(k)?' fn':'');
      btn.textContent=k;
      if(k==='0'){btn.style.gridColumn='span 2';}
      btn.onclick=()=>{_calc_press(k);_calc_render();};
      grid.appendChild(btn);
    }));
    panel.appendChild(grid);document.body.appendChild(panel);
    // keyboard support
    document.addEventListener('keydown',e=>{
      if(!_open)return;
      if(e.key>='0'&&e.key<='9'){_calc_press(e.key);_calc_render();}
      else if(e.key==='.'){_calc_press('.');_calc_render();}
      else if(e.key==='+'||e.key==='-'){_calc_press(e.key==='+'?'+':'−');_calc_render();}
      else if(e.key==='*'){_calc_press('×');_calc_render();}
      else if(e.key==='/'){e.preventDefault();_calc_press('÷');_calc_render();}
      else if(e.key==='Enter'||e.key==='='){_calc_press('=');_calc_render();}
      else if(e.key==='Escape'){_open=false;_calc_render();}
      else if(e.key==='Backspace'){_calc_press('⌫');_calc_render();}
    });
  }
  window._calc_mount=_calc_mount;
})();

// ── Render ──────────────────────────────────────────────────────
function render(){
  const root=document.getElementById('root');root.innerHTML='';
  document.body.classList.toggle('sb-open', !!S.sidebarOpen);
  document.body.classList.toggle('has-topbar', S.app==='prod' || S.app==='stock' || S.app==='compta' || S.app==='expe');
  window.__MYSIFA_APP__ = S.app;

  if(!S.user||S.app==='login'){root.appendChild(renderLogin());}
  else if(S.app==='portal'){root.appendChild(renderPortal());}
  else if(S.app==='stock'){root.appendChild(renderStock());}
  else if(S.app==='compta'){root.appendChild(renderCompta());}
  else if(S.app==='expe'){root.appendChild(renderExpe());}
  else if(S.app==='messages'){root.appendChild(renderMessagesApp());}
  else if(S.app==='prod'){
    const titles={
      production: S.subPage==='saisies'?'Saisies':S.subPage==='erreurs'?'Historique & Erreurs':'Production',
      suivi:'Rentabilité & Dossiers',
      profil:'Mon profil',
      traceabilite:'Traçabilité',
      // rétrocompat URL directe
      historique:'Historique & Erreurs',saisies:'Saisies',import:'Import XLSX',
      dossiers:'Dossiers',rentabilite:'Rentabilité',
    };
    const subs={
      production: S.subPage==='saisies'?'Consulter, corriger et importer des saisies':
                  S.subPage==='erreurs'?'Sanity Score, incidents et erreurs de saisie':
                  'KPIs, temps, quantités et qualité de saisie',
      suivi:'Dossiers de production et comparaison devis / réel',
      profil:'Informations personnelles et mot de passe',
      traceabilite:'Matières utilisées par dossier',
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
    root.appendChild(h('div',null,
      S.sidebarOpen?h('div',{className:'sidebar-overlay',onClick:closeSidebar}):null,
      h('div',{className:'app'},renderSidebar(),
        h('main',{className:'main'},h('div',{className:'container'},
          topbar,
                h('h1',null,titles[S.page]||''),
            h('div',{className:'subtitle'},subs[S.page]||''),
        (S.page==='production'||S.page==='historique'||S.page==='saisies')?renderFilters():null,
        S.page==='production'?renderProdPage():null,
        S.page==='suivi'?renderSuivi():null,
        S.page==='profil'?renderProfil(S.user):null,
        S.page==='traceabilite'?renderTracabilite():null,
        // Rétrocompat accès direct par URL :
        S.page==='historique'?renderHist():null,
        S.page==='saisies'?renderSaisies():null,
        S.page==='import'?renderImport():null,
        S.page==='dossiers'?renderDos():null,
        S.page==='rentabilite'?renderRentabilite():null,
        ))
      )
    ));
  }

  if(S.toast){const c={success:'var(--success)',error:'var(--danger)'};root.appendChild(h('div',{className:'toast',style:{borderLeft:'3px solid '+(c[S.toast.type]||'var(--accent)')}},h('span',{style:{fontSize:'14px',color:c[S.toast.type]||'var(--accent)'}},S.toast.message)));}

  if(S.contactOpen){
    root.appendChild(renderContactModal());
  }
  // contact modal for expe is rendered inside renderExpe()

  // Calculette flottante (MyStock + MyExpé)
  if(S.app==='stock'||S.app==='expe'){
    window._calc_mount && window._calc_mount();
  } else {
    const fab=document.getElementById('_calc_fab');
    const panel=document.getElementById('_calc_panel');
    if(fab)fab.remove();
    if(panel)panel.remove();
  }

  // PWA: feature temporairement retirée. (setupInstallButton supprimé)
}

async function nav(){
  if(S.page==='production'){
    if(S.subPage==='kpis'||!S.subPage){await loadProd();if(!S.historique)await loadHist();}
    else if(S.subPage==='saisies'){await loadSaisies();}
    else if(S.subPage==='erreurs'){await loadHist();}
  }
  else if(S.page==='suivi'){await loadDos();await loadDevis();}
  else if(S.page==='historique')await loadHist();
  else if(S.page==='saisies')await loadSaisies();
  else if(S.page==='import')await loadImports();
  else if(S.page==='rentabilite'){await loadDevis();await loadRentPlanning();}
  else if(S.page==='dossiers')await loadDos();
  else if(S.page==='traceabilite'){S.traceabilite=null;S.traceabiliteDossier=undefined;await loadTracabilite();}
  render();
}

if(localStorage.getItem('theme')==='light')document.body.classList.add('light');
// Désactive temporairement toute trace PWA (service worker) pour éviter des effets de cache.
// Certains navigateurs gardent un SW enregistré même après suppression du manifest.
try{
  if('serviceWorker' in navigator){
    const k='mysifa_sw_unreg_v1';
    if(!sessionStorage.getItem(k)){
      sessionStorage.setItem(k,'1');
      navigator.serviceWorker.getRegistrations()
        .then(rs=>Promise.all(rs.map(r=>r.unregister().catch(()=>false))))
        .then(()=>{ try{ location.reload(); }catch(e){} });
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
<!-- Chatbot temporairement désactivé -->
</body>
</html>"""

def render_frontend_html(initial_app: str = "portal") -> str:
    return (
        _FRONTEND_HTML_TEMPLATE.replace("__META_DESCRIPTION__", APP_META_DESCRIPTION)
        .replace("__THEME_COLOR__", THEME_COLOR_META)
        .replace("__PAGE_TITLE__", APP_PAGE_TITLE)
        .replace("__V_LABEL__", f"v{APP_VERSION}")
        .replace("__INITIAL_APP_VALUE__", initial_app)
    )


FRONTEND_HTML = render_frontend_html("portal")

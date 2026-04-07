from config import APP_VERSION, APP_META_DESCRIPTION, APP_PAGE_TITLE, THEME_COLOR_META

_FRONTEND_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="__META_DESCRIPTION__">
<link rel="icon" type="image/png" sizes="512x512" href="/static/mys_icon_512.png">
<link rel="apple-touch-icon" href="/static/mys_icon_180.png">
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="MySifa">
<meta name="theme-color" content="#0a0e17">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="mobile-web-app-capable" content="yes">
<title>__PAGE_TITLE__</title>
<style>
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#94a3b8;
  --muted:#64748b;--accent:#22d3ee;--accent-bg:rgba(34,211,238,0.12);
  --success:#34d399;--warn:#fbbf24;--danger:#f87171;
  --c1:#22d3ee;--c2:#a78bfa;--c3:#34d399;--c4:#fbbf24;--c5:#f87171
}
body.light{
  --bg:#f1f5f9;--card:#ffffff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;
  --muted:#94a3b8;--accent:#0891b2;--accent-bg:rgba(8,145,178,0.10);
  --success:#059669;--warn:#d97706;--danger:#dc2626;
  --c1:#0891b2;--c2:#7c3aed;--c3:#059669;--c4:#d97706;--c5:#dc2626
}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
button:focus-visible,.nav-btn:focus-visible,.login-btn:focus-visible,.portal-logout:focus-visible,.theme-btn:focus-visible,.logout-btn:focus-visible,a:focus-visible{
  outline:2px solid var(--accent);outline-offset:2px}
button:focus:not(:focus-visible){outline:none}
::-webkit-scrollbar{width:6px}::-webkit-scrollbar-track{background:var(--bg)}::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
#saisies-scroll-top{overflow-x:auto}
#saisies-scroll-top::-webkit-scrollbar{height:6px}
#saisies-scroll-top::-webkit-scrollbar-thumb{background:var(--accent);border-radius:3px}
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
  .sidebar-overlay{display:block;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:8999}
  body:not(.sb-open) .sidebar-overlay{display:none}
  body.has-topbar .main{padding-top:74px}
}
.logo{padding:0 8px;margin-bottom:32px}
.logo-brand{font-size:15px;font-weight:800}.logo-brand span{color:var(--accent)}
.logo-sub{font-size:10px;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase}
.nav-btn{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:8px;border:none;background:transparent;color:var(--text2);cursor:pointer;font-size:13px;font-weight:500;width:100%;text-align:left;font-family:inherit;transition:all .15s;margin-bottom:2px}
.nav-btn:hover,.nav-btn.active{background:var(--accent-bg);color:var(--accent)}
.sidebar-bottom{margin-top:auto;display:flex;flex-direction:column;gap:6px;padding-bottom:8px}
.user-chip{padding:10px 12px;border-radius:8px;background:var(--accent-bg)}
.user-chip .uc-name{font-size:12px;font-weight:600;color:var(--text)}
.user-chip .uc-role{font-size:10px;color:var(--accent);text-transform:uppercase;letter-spacing:.5px}
.theme-btn,.logout-btn{display:flex;align-items:center;gap:8px;padding:10px 12px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-size:12px;width:100%;font-family:inherit;transition:all .15s}
.theme-btn:hover{background:var(--accent-bg);color:var(--accent);border-color:var(--accent)}
.theme-btn .theme-ico{font-size:14px;line-height:1}
.theme-btn .theme-label{white-space:nowrap}
@media (display-mode: standalone), (max-width: 900px){
  .theme-btn .theme-label{display:none}
  .theme-btn{justify-content:center}
}
.logout-btn{border:none}.logout-btn:hover{color:var(--danger);background:rgba(248,113,113,.1)}
.version{font-size:10px;color:var(--muted);font-family:monospace;padding:4px 12px}
.main{flex:1;padding:28px;overflow-y:auto}.container{max-width:1200px;margin:0 auto}
h1{font-size:22px;font-weight:700;margin-bottom:4px}
.subtitle{font-size:13px;color:var(--muted);margin-bottom:24px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:14px;margin-bottom:24px}
.stat{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px 20px}
.stat-label{font-size:11px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px}
.stat-value{font-size:26px;font-weight:700;font-family:monospace;line-height:1.1}
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
.cb-icon{font-size:32px;margin-bottom:12px}.cb-msg{font-size:14px;color:var(--muted)}
.filters{display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end;margin-bottom:20px}
.filter-group{display:flex;flex-direction:column;gap:4px}
.filter-group label{font-size:10px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
.filters select,.filters input[type=date]{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:8px 12px;color:var(--text);font-size:12px;font-family:inherit;min-width:140px}
.filters select:focus,.filters input:focus{border-color:var(--accent);outline:none}
.filters button{background:var(--accent);color:var(--bg);border:none;border-radius:8px;padding:9px 16px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;align-self:flex-end}
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
.add-row-form{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:28px;width:100%;max-width:540px;box-shadow:0 24px 64px rgba(0,0,0,.4)}
.add-row-form h3{font-size:16px;font-weight:700;margin-bottom:20px}
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
.tc-label{font-size:10px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px}
.tc-value{font-size:22px;font-weight:700;font-family:monospace}
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
input[type=text],input[type=number],input[type=email],input[type=password]{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px 14px;color:var(--text);font-size:13px;width:100%;outline:none;font-family:inherit}
select.form-sel{
  background:var(--bg);border:1px solid var(--border);border-radius:8px;
  padding:8px 12px;padding-right:32px;
  color:var(--text);font-size:13px;outline:none;font-family:inherit;
  cursor:pointer;appearance:none;-webkit-appearance:none;
  background-image:url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%2364748b' d='M6 8L1 3h10z'/%3E%3C/svg%3E\");
  background-repeat:no-repeat;background-position:right 10px center;
}
select.form-sel:focus{border-color:var(--accent)}
.btn{background:var(--accent);color:var(--bg);border:none;border-radius:8px;padding:10px 24px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;margin-top:12px}
.btn-sm{background:var(--accent);color:var(--bg);border:none;border-radius:6px;padding:6px 14px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit}
.btn-ghost{background:transparent;color:var(--text2);border:1px solid var(--border);border-radius:6px;padding:6px 14px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit}
.btn-ghost:hover{border-color:var(--accent);color:var(--accent)}
.btn-danger{background:rgba(248,113,113,.15);color:var(--danger);border:1px solid rgba(248,113,113,.3);border-radius:6px;padding:5px 12px;font-size:11px;font-weight:600;cursor:pointer;font-family:inherit}
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
  align-items:center;justify-content:center;gap:48px;padding:40px}
.portal-logo{text-align:center}
.portal-logo .brand{font-size:42px;font-weight:800;letter-spacing:-2px}
.portal-logo .brand span{color:var(--accent)}
.portal-logo .tagline{font-size:14px;color:var(--muted);margin-top:8px;letter-spacing:1px}
.portal-apps{display:flex;gap:32px;flex-wrap:wrap;justify-content:center}
.portal-app{display:flex;flex-direction:column;align-items:center;gap:16px;
  background:var(--card);border:1px solid var(--border);border-radius:24px;
  padding:40px 48px;cursor:pointer;transition:all .2s;text-decoration:none;
  min-width:200px}
.portal-app:hover{border-color:var(--accent);background:var(--accent-bg);
  transform:translateY(-4px);box-shadow:0 12px 40px rgba(34,211,238,.15)}
.portal-app--busy{pointer-events:none;opacity:.8;position:relative;transform:none!important;box-shadow:none!important}
.portal-app--busy::after{
  content:'Chargement…';position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
  background:rgba(10,14,23,.72);border-radius:24px;font-size:13px;font-weight:700;color:var(--accent);letter-spacing:.02em}
body.light .portal-app--busy::after{background:rgba(255,255,255,.88);color:var(--accent)}
.portal-app-icon{font-size:48px;line-height:1}
.portal-app-name{font-size:20px;font-weight:800;color:var(--text)}
.portal-app-desc{font-size:12px;color:var(--muted);text-align:center}
.portal-user{font-size:12px;color:var(--muted);display:flex;align-items:center;gap:8px}
.portal-logout{background:none;border:none;color:var(--muted);cursor:pointer;
  font-size:12px;font-family:inherit;text-decoration:underline}
.portal-logout:hover{color:var(--danger)}

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
.stock-search-wrap{position:relative;flex:1}
</style>
</head>
<body>
<div id="root"></div>
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
  page:'historique',user:null,
  loginSubmitting:false,loginError:null,portalLoading:null,
  sidebarOpen:false,
  stockView:'grille',
  stockProduits:[],stockSelProduit:null,stockSelEmpl:null,
  stockGlobale:null,stockSearch:'',stockMvtType:'entree',
  filters:{},OPS_CONFIG:{},
  fv:{operateurs:[],dossiers:[],date_from:getYesterday(),date_to:getYesterday()},
  historique:null,production:null,
  imports:[],selImp:null,impData:null,
  saisies:null,
  dossiers:[],users:[],
  devisList:[],selDevis:null,comparaison:null,devisPreview:null,
  toast:null,
  selectedRows:new Set(),   // ids des lignes sélectionnées
  sortState:{col:null,asc:true}, // tri tableau saisies
  addRowTemplate:null,
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
const fN=n=>n?Number(n).toLocaleString('fr-FR'):'0';
const fD=d=>d?d.replace(/C$/,'').replace('T',' ').slice(0,16):'-';
const opName=s=>{if(!s)return'';const p=s.split(' - ');return p.length>1?p.slice(1).join(' - '):s;};
const fMin=m=>{if(!m&&m!==0)return'-';const hh=Math.floor(m/60),mm=Math.round(m%60);return hh>0?hh+'h '+String(mm).padStart(2,'0')+'min':mm+'min';};
const isAdmin=u=>u&&(u.role==='direction'||u.role==='administration');
const isFab=u=>u&&u.role==='fabrication';

const ROLE_LABELS={direction:'👑 Direction',administration:'🔧 Administration',fabrication:'⚙ Fabrication',logistique:'📦 Logistique'};
const ROLE_BADGE={direction:'badge-direction',administration:'badge-administration',fabrication:'badge-fabrication',logistique:'badge-fabrication'};

// ── Auth ────────────────────────────────────────────────────────
async function checkAuth(){
  const epoch=authEpoch;
  const user=await api('/api/auth/me');
  if(epoch!==authEpoch)return;
  if(user){
    S.user=user;
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
    // Permet d'ouvrir directement une section depuis /planning → /prod?page=users
    try{
      const sp=new URLSearchParams(window.location.search||'');
      const p=(sp.get('page')||'').trim();
      const allowed=new Set(['historique','production','saisies','import','rentabilite','dossiers','users','profil']);
      if(S.app==='prod' && allowed.has(p)) S.page=p;
    }catch(e){}
    if(S.app==='prod'){
      await loadFilters();
      await loadHist();
    }else if(S.app==='stock'){
      await loadStockGlobale();
      await loadStockProduits();
    }
  }
  else{S.user=null;S.app='login';}
  render();
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
      const allowed=new Set(['historique','production','saisies','import','rentabilite','dossiers','users','profil']);
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
    S.saisies=null;
    S.selectedRows=new Set();
    S.sortState={col:null,asc:true};
    // Déverrouiller tout de suite — avant loadFilters/loadHist (sinon bouton « Connexion… » bloqué le temps des APIs)
    S.loginSubmitting=false;
    render();
    if(S.app==='prod'){
      await loadFilters();
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
  S.user=null;S.app='login';S.historique=null;S.production=null;
  S.stockGlobale=null;S.stockProduits=[];S.stockSelProduit=null;S.stockSelEmpl=null;
  S.loginSubmitting=false;S.loginError=null;S.portalLoading=null;
  render();
}

async function loadStockProduits(q=''){
  const url='/api/stock/produits'+(q?'?q='+encodeURIComponent(q):'');
  const d=await api(url);
  if(d)set({stockProduits:d});
}
async function loadStockGlobale(){
  const d=await api('/api/stock/vue-globale');
  if(d)set({stockGlobale:d});
}
async function loadStockProduit(id){
  const d=await api('/api/stock/produits/'+id+'/emplacements');
  if(d)set({stockSelProduit:d});
}
async function loadStockEmplacement(empl){
  const d=await api('/api/stock/emplacements/'+encodeURIComponent(empl));
  if(d)set({stockSelEmpl:d});
}

async function createProduit(body){
  try{
    await api('/api/stock/produits',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    toast('Produit créé');await loadStockProduits();await loadStockGlobale();
  }catch(e){toast(e.message,'error');}
}

async function doMouvement(body){
  try{
    const r=await api('/api/stock/mouvement',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!r)return;
    toast('Stock mis à jour — Avant: '+r.quantite_avant+' → Après: '+r.quantite_apres);
    await loadStockGlobale();
    if(S.stockSelProduit) await loadStockProduit(S.stockSelProduit.produit.id);
    if(S.stockSelEmpl) await loadStockEmplacement(S.stockSelEmpl.emplacement);
  }catch(e){toast(e.message,'error');}
}

// ── Barre de recherche MyStock (texte + micro + caméra ZXing) ────────────────
let stockSearchState = {
  query: '',
  listening: false,
  scanning: false,
  suggestions: [],
  cameraStream: null,
  barcodeReader: null,
};

const STOCK_EMPLACEMENTS = ['A121','A122','A123','B121','B122','B123','C121','C122','C123'];
const isValidStockEmplacement = (s) => STOCK_EMPLACEMENTS.includes(String(s||'').trim().toUpperCase());

function startVoiceSearch(inputEl) {
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
  const recog = new SpeechRecognition();
  recog.lang = 'fr-FR';
  recog.interimResults = false;
  recog.maxAlternatives = 1;

  stockSearchState.listening = true;
  renderStockSearchBar();

  recog.onresult = (e) => {
    const transcript = e.results[0][0].transcript;
    inputEl.value = transcript;
    stockSearchState.query = transcript;
    stockSearchState.listening = false;
    doStockSearch(transcript);
    renderStockSearchBar();
  };
  recog.onerror = () => { stockSearchState.listening = false; renderStockSearchBar(); };
  recog.onend = () => { stockSearchState.listening = false; renderStockSearchBar(); };
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

  if (isValidStockEmplacement(cleaned)) {
    toast('Emplacement détecté : ' + cleaned);
    set({ stockView: 'emplacement' });
    loadStockEmplacement(cleaned).then(() => render()).catch(()=>{});
  } else {
    toast('Référence détectée : ' + cleaned);
    set({ stockView: 'produit', stockSearch: cleaned });
    loadStockProduits(cleaned).then(() => render());
  }
}

async function doStockSearch(q) {
  stockSearchState.query = q;
  const cleaned = String(q || '').trim().toUpperCase();
  if (!cleaned || cleaned.length < 2) {
    stockSearchState.suggestions = [];
    renderStockSearchBar();
    return;
  }

  // Emplacements : ne déclencher la vue emplacement QUE si l'emplacement est valide (sinon ça spam l'API en 404)
  if (/^[ABC]\d{3}$/i.test(cleaned) && isValidStockEmplacement(cleaned)) {
    try{
      await loadStockEmplacement(cleaned);
      set({ stockView: 'emplacement' });
    }catch(e){/* ignore */}
    stockSearchState.suggestions = [];
    renderStockSearchBar();
    return;
  }

  await loadStockProduits(cleaned);
  stockSearchState.suggestions = (S.stockProduits || []).slice(0, 6);
  renderStockSearchBar();
}

function renderStockSearchBar() {
  const bar = document.getElementById('stock-search-bar');
  if (!bar) return;

  // Si la barre existe déjà avec l'input, ne recréer que les suggestions
  const existingInput = document.getElementById('stock-search-input');
  if (existingInput) {
    // Mettre à jour seulement le bouton micro (état listening)
    const micBtn = document.getElementById('stock-mic-btn');
    if (micBtn) {
      micBtn.className = 'stock-search-btn' + (stockSearchState.listening ? ' active' : '');
      micBtn.textContent = stockSearchState.listening ? '🔴' : '🎤';
    }
    // Mettre à jour suggestions
    let suggEl = document.getElementById('stock-suggestions');
    if (stockSearchState.suggestions && stockSearchState.suggestions.length > 0) {
      if (!suggEl) {
        suggEl = document.createElement('div');
        suggEl.id = 'stock-suggestions';
        suggEl.className = 'search-suggestions';
        existingInput.parentNode.appendChild(suggEl);
      }
      suggEl.innerHTML = '';
      stockSearchState.suggestions.forEach(p => {
        const item = document.createElement('div');
        item.className = 'search-suggestion-item';
        item.innerHTML = `<div><div class="search-suggestion-ref">${p.reference}</div><div class="search-suggestion-des">${p.designation}</div></div><span class="stock-badge">${p.stock_total||0} ${p.unite}</span>`;
        item.addEventListener('click', () => {
          stockSearchState.query = p.reference;
          stockSearchState.suggestions = [];
          if (existingInput) existingInput.value = p.reference;
          const s = document.getElementById('stock-suggestions');
          if (s) s.remove();
          loadStockProduit(p.id).then(() => set({ stockView: 'produit' }));
        });
        suggEl.appendChild(item);
      });
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
      stockSearchState.suggestions = [];
      const s = document.getElementById('stock-suggestions');
      if (s) s.remove();
      const q = String(input.value || '').trim();
      if (q) { set({ stockView: 'produit', stockSearch: q }); loadStockProduits(q).then(() => render()); }
    }
    if (e.key === 'Escape') {
      stockSearchState.suggestions = [];
      const s = document.getElementById('stock-suggestions');
      if (s) s.remove();
    }
  });
  wrap.appendChild(input);

  const micBtn = document.createElement('button');
  micBtn.id = 'stock-mic-btn';
  micBtn.className = 'stock-search-btn' + (stockSearchState.listening ? ' active' : '');
  micBtn.type = 'button';
  micBtn.title = 'Recherche vocale';
  micBtn.textContent = stockSearchState.listening ? '🔴' : '🎤';
  micBtn.addEventListener('click', () => startVoiceSearch(input));

  const camBtn = document.createElement('button');
  camBtn.className = 'stock-search-btn' + (stockSearchState.scanning ? ' active' : '');
  camBtn.type = 'button';
  camBtn.title = 'Scanner un code';
  camBtn.textContent = '📷';
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
  const isStock = S.user?.role && ['direction','administration','logistique'].includes(S.user.role);
  const isProd  = S.user?.role && ['direction','administration','fabrication'].includes(S.user.role);
  const isLight=document.body.classList.contains('light');

  const apps=[];

  if(isProd){
    apps.push(h('div',{
      className:'portal-app'+(S.portalLoading==='prod'?' portal-app--busy':''),
      onClick:async()=>{
        window.location.href='/prod';
      }
    },
      h('div',{className:'portal-app-icon'},'📊'),
      h('div',{className:'portal-app-name'},'MyProd'),
      h('div',{className:'portal-app-desc'},'Suivi de production — Historique et saisies')
    ));
  }

  if(isStock){
    apps.push(h('div',{
      className:'portal-app'+(S.portalLoading==='stock'?' portal-app--busy':''),
      onClick:async()=>{
        window.location.href='/stock';
      }
    },
      h('div',{className:'portal-app-icon'},'📦'),
      h('div',{className:'portal-app-name'},'MyStock'),
      h('div',{className:'portal-app-desc'},'Gestion des stocks — Emplacements et références')
    ));
  }

  return h('div',{className:'portal-page'},
    h('div',{className:'portal-logo'},
      h('div',{className:'brand'},'My',h('span',null,'Sifa')),
      h('div',{className:'tagline'},'Choisissez votre application')
    ),
    h('div',{className:'portal-apps'},...apps),
    h('div',{className:'portal-user'},
      '👤 '+S.user?.nom,
      h('button',{className:'portal-logout',onClick:()=>{document.body.classList.toggle('light');localStorage.setItem('theme',document.body.classList.contains('light')?'light':'dark');render();}},
        h('span',{className:'theme-ico'},isLight?'☀':'🌙'),
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
      onClick:async()=>{await loadStockGlobale();set({stockView:'grille',stockSelProduit:null,stockSelEmpl:null});}},
      '🗺  Vue globale'),
    h('button',{className:'nav-btn'+(S.stockView==='produit'?' active':''),
      onClick:async()=>{await loadStockProduits();set({stockView:'produit',stockSelProduit:null});}},
      '🏷  Par référence'),
    h('button',{className:'nav-btn'+(S.stockView==='emplacement'?' active':''),
      onClick:()=>set({stockView:'emplacement',stockSelEmpl:null})},
      '📍  Par emplacement'),
    h('div',{className:'sidebar-bottom'},
      h('button',{className:'nav-btn back-mysifa',onClick:()=>{window.location.href='/' }},
        '← Retour ',
        h('span',{className:'wm'},'My',h('span',null,'Sifa'))
      ),
      h('div',{className:'user-chip'},
        h('div',{className:'uc-name'},S.user?.nom||''),
        h('div',{className:'uc-role'},ROLE_LABELS[S.user?.role]||S.user?.role||'')
      ),
      h('button',{className:'theme-btn',onClick:()=>{document.body.classList.toggle('light');localStorage.setItem('theme',document.body.classList.contains('light')?'light':'dark');render();}},
        h('span',{className:'theme-ico'},isLight?'☀':'🌙'),
        h('span',{className:'theme-label'},isLight?'Mode clair':'Mode sombre')
      ),
      h('button',{className:'logout-btn',onClick:doLogout},'⎋  Déconnexion'),
      h('div',{className:'version'},'MyStock v1.0')
    )
  );

  let content;

  if(S.stockView==='grille'){
    const grille=g?.grille||[];
    const stats=g?.stats||{};
    const mvts=g?.derniers_mouvements||[];

    const byEmpl={};
    ['A121','A122','A123','B121','B122','B123','C121','C122','C123'].forEach(e=>{byEmpl[e]=[];});
    grille.forEach(r=>{if(byEmpl[r.emplacement])byEmpl[r.emplacement].push(r);});

    const statBar=h('div',{className:'stats',style:{marginBottom:'20px'}},
      h('div',{className:'stat'},h('div',{className:'stat-label'},'Références'),h('div',{className:'stat-value',style:{color:'var(--c1)'}},stats.nb_refs||0)),
      h('div',{className:'stat'},h('div',{className:'stat-label'},'Emplacements occupés'),h('div',{className:'stat-value',style:{color:'var(--c2)'}},stats.nb_empl||0)),
      h('div',{className:'stat'},h('div',{className:'stat-label'},'Total unités'),h('div',{className:'stat-value',style:{color:'var(--c3)'}},fN(stats.total_unites||0)))
    );

    const grid=h('div',{className:'stock-grid'},
      ...Object.entries(byEmpl).map(([empl,items])=>
        h('div',{className:'stock-cell',onClick:async()=>{
          await loadStockEmplacement(empl);
          set({stockView:'emplacement'});
        }},
          h('div',{className:'stock-cell-label'},empl),
          items.length===0
            ? h('div',{className:'stock-cell-empty'},'Vide')
            : h('div',{className:'stock-cell-items'},
                ...items.map(i=>h('div',null,
                  i.reference,
                  h('span',{className:'stock-badge'},fN(i.quantite)+' '+i.unite)
                ))
              )
        )
      )
    );

    const mvtTable=mvts.length?h('div',{className:'card'},
      h('div',{className:'card-header'},h('h3',null,'Derniers mouvements')),
      h('div',{style:{overflowX:'auto'}},h('table',null,
        h('thead',null,h('tr',null,h('th',null,'Date'),h('th',null,'Réf'),h('th',null,'Emplacement'),h('th',null,'Type'),h('th',null,'Qté'),h('th',null,'Par'))),
        h('tbody',null,...mvts.map(m=>h('tr',null,
          h('td',{style:{fontFamily:'monospace',fontSize:'11px'}},fD(m.created_at)),
          h('td',{style:{fontFamily:'monospace',fontWeight:'700'}},m.reference),
          h('td',{style:{fontFamily:'monospace'}},m.emplacement),
          h('td',null,h('span',{className:'mvt-type-'+m.type_mouvement},m.type_mouvement)),
          h('td',{style:{fontFamily:'monospace'}},fN(m.quantite)),
          h('td',{style:{fontSize:'11px',color:'var(--muted)'}},m.created_by||'')
        )))
      ))
    ):null;

    content=h('div',null,statBar,grid,mvtTable);
  }

  else if(S.stockView==='produit'){
    const produits=S.stockProduits||[];
    const sel=S.stockSelProduit;

    const newRef=h('input',{type:'text',placeholder:'Référence *',style:{textTransform:'uppercase',flex:'1',minWidth:'140px'}});
    const newDes=h('input',{type:'text',placeholder:'Désignation *'});
    const newUnit=h('input',{type:'text',placeholder:'Unité (ex: m, rouleau, carton)',value:'unité'});
    const newForm=h('div',{className:'card',style:{padding:'16px',marginBottom:'16px'}},
      h('div',{className:'form-section-title'},'Nouveau produit'),
      h('div',{style:{display:'flex',gap:'8px',flexWrap:'wrap',alignItems:'center'}},newRef,newDes,newUnit,
        h('button',{className:'btn-sm',onClick:()=>{
          if(!newRef.value||!newDes.value)return;
          createProduit({reference:newRef.value,designation:newDes.value,unite:newUnit.value||'unité'});
          newRef.value='';newDes.value='';
        }},'+ Créer')
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
        className:'produit-row'+(sel?.produit?.id===p.id?' active':''),
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
          h('h3',null,'Localisations'),
          h('span',{className:'stock-badge'},fN(sel.stock_total)+' '+p.unite+' total')
        ),
        h('table',null,
          h('thead',null,h('tr',null,h('th',null,'Emplacement'),h('th',null,'Quantité'),h('th',null,'Mis à jour'),h('th',null,'Par'))),
          h('tbody',null,...empls.map(e=>h('tr',null,
            h('td',{style:{fontFamily:'monospace',fontWeight:'700',color:'var(--accent)'}},e.emplacement),
            h('td',{style:{fontFamily:'monospace',fontWeight:'700'}},fN(e.quantite)+' '+p.unite),
            h('td',{style:{fontSize:'11px',color:'var(--muted)'}},fD(e.updated_at)),
            h('td',{style:{fontSize:'11px',color:'var(--muted)'}},e.updated_by||'')
          )))
        )
      ):h('div',{className:'card-empty'},'Aucun stock pour ce produit');

      detail=h('div',null,
        h('div',{className:'card',style:{padding:'16px',marginBottom:'12px'}},
          h('h3',{style:{fontSize:'16px',fontWeight:'800',marginBottom:'4px'}},p.reference),
          h('p',{style:{fontSize:'13px',color:'var(--muted)'}},p.designation),
          h('p',{style:{fontSize:'11px',color:'var(--muted)',marginTop:'4px'}},'Unité : '+p.unite)
        ),
        mvtForm,
        emplTable
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
    const EMPLS=['A121','A122','A123','B121','B122','B123','C121','C122','C123'];
    const sel=S.stockSelEmpl;

    const empl_list=h('div',{className:'card',style:{marginBottom:'16px'}},
      h('div',{className:'card-header'},h('h3',null,'Sélectionner un emplacement')),
      h('div',{style:{display:'flex',gap:'8px',flexWrap:'wrap',padding:'16px'}},
        ...EMPLS.map(e=>h('button',{
          className:'mvt-btn'+(sel?.emplacement===e?' active-entree':''),
          onClick:async()=>await loadStockEmplacement(e)
        },e))
      )
    );

    let detail=h('div',{className:'card-empty',style:{padding:'40px'}},'← Sélectionnez un emplacement');
    if(sel&&sel.produits!==undefined){
      const produits=sel.produits||[];
      detail=h('div',{className:'card'},
        h('div',{className:'card-header'},
          h('h3',null,'Emplacement '+sel.emplacement),
          h('span',{className:'stock-badge'},produits.length+' référence'+(produits.length>1?'s':''))
        ),
        produits.length===0?h('div',{className:'card-empty'},'Emplacement vide'):
        h('table',null,
          h('thead',null,h('tr',null,h('th',null,'Référence'),h('th',null,'Désignation'),h('th',null,'Quantité'),h('th',null,'Mis à jour'))),
          h('tbody',null,...produits.map(p=>h('tr',null,
            h('td',{style:{fontFamily:'monospace',fontWeight:'700',color:'var(--accent)'}},p.reference),
            h('td',null,p.designation),
            h('td',{style:{fontFamily:'monospace',fontWeight:'700'}},fN(p.quantite)+' '+p.unite),
            h('td',{style:{fontSize:'11px',color:'var(--muted)'}},fD(p.updated_at))
          )))
        )
      );
    }

    content=h('div',null,empl_list,detail);
  }

  const topbar=h('div',{className:'mobile-topbar'},
    h('button',{type:'button',className:'mobile-menu-btn',onClick:toggleSidebar,'aria-label':'Menu'},S.sidebarOpen?'✕':'☰'),
    h('div',{style:{flex:1,minWidth:0}},
      h('div',{className:'mobile-topbar-title'},'MyStock'),
      h('div',{className:'mobile-topbar-sub'},
        S.stockView==='grille'?'Vue globale':S.stockView==='produit'?'Par référence':'Par emplacement'
      ),
      h('div',{id:'stock-search-bar',className:'stock-search-bar'})
    )
  );
  const mainEl=h('main',{className:'main'},
    topbar,
    h('div',{className:'container',style:{padding:'24px 28px'}},
      h('h1',null,S.stockView==='grille'?'Vue globale':S.stockView==='produit'?'Par référence':'Par emplacement'),
      h('div',{className:'subtitle'},
        S.stockView==='grille'?'Tous les emplacements et leur contenu — raccourci scan ci-dessous':
        S.stockView==='produit'?'Recherche, micro, scan code (caméra), mouvements de stock':
        'Voir le contenu d\'un emplacement'
      ),
      content
    )
  );
  requestAnimationFrame(()=>initStockSearchBar());
  return h('div',null,
    S.sidebarOpen?h('div',{className:'sidebar-overlay',onClick:closeSidebar}):null,
    h('div',{className:'app'},sidebar,
      mainEl
    ),
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
async function loadUsers(){const d=await api('/api/users');if(d)set({users:d});}
async function loadMachines(){try{const d=await api('/api/planning/machines');if(d)set({machines:d});}catch(e){}}
async function loadSaisies(){const d=await api('/api/saisies?'+buildParams()+'&limit=500');if(d)set({saisies:d});}
async function loadDevis(){const d=await api('/api/rentabilite/devis');if(d)set({devisList:d});}

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
async function createUser(u){try{await api('/api/users',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(u)});toast('Utilisateur créé');loadUsers();}catch(e){toast(e.message,'error');}}
async function toggleUser(id,actif){try{await api('/api/users/'+id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({actif:actif?1:0})});loadUsers();}catch(e){toast(e.message,'error');}}

function applyF(){loadHist();loadProd();if(S.page==='saisies')loadSaisies();render();}

// ── Login ───────────────────────────────────────────────────────
function renderLogin(){
  const errEl=h('div',{className:'login-error'+(S.loginError?' show':''),id:'login-error'},S.loginError||'');
  const emailI=h('input',{type:'email',id:'login-email',name:'email',autocomplete:'username',placeholder:'votre@email.fr'});
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
          h('div',{className:'field'},h('label',{'for':'login-email'},'Adresse e-mail'),emailI),
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
  const items=[
    {key:'historique',label:'Historique & Erreurs',icon:'⚠'},
    {key:'production',label:'Production',icon:'📊'},
    {key:'saisies',label:'Saisies',icon:'✏'},
    ...(admin?[
      {key:'import',label:'Import XLSX',icon:'↑'},
      {key:'_planning',label:'Planning',icon:'🗓'},
      {key:'rentabilite',label:'Rentabilité',icon:'📈'},
      {key:'dossiers',label:'Dossiers',icon:'◫'},
      {key:'users',label:'Utilisateurs',icon:'👥'},
    ]:[]),
  ];
  const isLight=document.body.classList.contains('light');
  return h('nav',{className:'sidebar'},
    h('div',{className:'logo'},h('div',{className:'logo-brand'},'My',h('span',null,'Prod')),h('div',{className:'logo-sub'},'by SIFA')),
    ...items.map(i=>h('button',{className:'nav-btn'+(S.page===i.key?' active':''),onClick:()=>{
      if(i.key==='_planning'){window.location.href='/planning';return;}
      S.sidebarOpen=false;
      set({page:i.key});nav();
    }},i.icon+'  '+i.label)),
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
        h('div',{className:'uc-name'},S.user?.nom||''),
        h('div',{className:'uc-role'},ROLE_LABELS[S.user?.role]||S.user?.role||''),
        h('div',{style:{fontSize:'10px',color:'var(--accent)',marginTop:'3px'}},'✎ Mon profil')
      ),
      h('button',{className:'theme-btn',onClick:()=>{document.body.classList.toggle('light');localStorage.setItem('theme',document.body.classList.contains('light')?'light':'dark');render();}},
        h('span',{className:'theme-ico'},isLight?'☀':'🌙'),
        h('span',{className:'theme-label'},isLight?'Mode clair':'Mode sombre')
      ),
      h('button',{className:'logout-btn',onClick:doLogout},'⎋  Déconnexion'),
      h('div',{className:'version'},'__V_LABEL__')
    )
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
 
  const df=makeDateSelect(S.fv.date_from, v=>{S.fv.date_from=v;});
  const dt=makeDateSelect(S.fv.date_to,   v=>{S.fv.date_to=v;});
  parts.push(h('div',{className:'filter-group'},h('label',null,'Du'),df));
  parts.push(h('div',{className:'filter-group'},h('label',null,'Au'),dt));
  parts.push(h('button',{onClick:applyF},'Filtrer'));
  return h('div',{className:'filters'},...parts);
}
 
// ── Composant multi-select avec cases à cocher ──────────────────
function makeMultiSelect(label, options, selected, onChange){
  const isSelected = v => selected.includes(v);
  const count = selected.length;
 
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
      let newSel = selected.filter(v=>v!==opt.value);
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
  document.addEventListener('click',()=>{open=false;dropdown.style.display='none';},{once:false,capture:true,passive:true});
 
  const wrapper=h('div',{className:'filter-group'},h('label',null,label));
  const rel=h('div',{style:{position:'relative'}},trigger,dropdown);
  wrapper.appendChild(rel);
  return wrapper;
}

// ── Sanity ──────────────────────────────────────────────────────
function renderSanity(sanity){
  if(!sanity)return null;
  const score=sanity.score||0;
  const colorMap={success:'var(--success)',warn:'var(--warn)',danger:'var(--danger)'};
  const col=colorMap[sanity.color]||'var(--muted)';
  const r=34,circ=2*Math.PI*r,offset=circ-(score/100)*circ;
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
  svg.setAttribute('width','80');svg.setAttribute('height','80');svg.setAttribute('viewBox','0 0 80 80');svg.style.transform='rotate(-90deg)';
  const bg=document.createElementNS('http://www.w3.org/2000/svg','circle');bg.setAttribute('cx','40');bg.setAttribute('cy','40');bg.setAttribute('r',String(r));bg.setAttribute('fill','none');bg.setAttribute('stroke','var(--border)');bg.setAttribute('stroke-width','8');svg.appendChild(bg);
  const fill=document.createElementNS('http://www.w3.org/2000/svg','circle');fill.setAttribute('cx','40');fill.setAttribute('cy','40');fill.setAttribute('r',String(r));fill.setAttribute('fill','none');fill.setAttribute('stroke',col);fill.setAttribute('stroke-width','8');fill.setAttribute('stroke-linecap','round');fill.setAttribute('stroke-dasharray',String(circ));fill.setAttribute('stroke-dashoffset',String(offset));svg.appendChild(fill);
  const pills=(sanity.penalites||[]).map(p=>h('div',{className:'sanity-pill'},'-'+p.total+' '+p.label+' ×'+p.count));
  return h('div',{className:'sanity-banner'},
    h('div',{className:'sanity-circle'},svg,h('div',{className:'sanity-num',style:{color:col}},String(score))),
    h('div',null,h('div',{className:'si-mention',style:{color:col}},sanity.mention||''),h('div',{className:'si-label'},'Qualité de saisie — Sanity Score'),h('div',{className:'sanity-pills'},...(pills.length?pills:[h('span',{style:{fontSize:'12px',color:'var(--success)'}},'✅ Aucune pénalité')])))
  );
}

// ── Erreurs saisie ──────────────────────────────────────────────
const ERROR_LABELS={absence_arrivee:{icon:'🔴',label:'Arrivée manquante'},absence_depart:{icon:'🔴',label:'Départ manquant'},dossier_sans_debut:{icon:'🔴',label:'Début dossier manquant'},dossier_sans_fin:{icon:'🔴',label:'Fin dossier manquante'},dossier_sans_debut_fin:{icon:'🔴',label:'Début + Fin manquants'}};
function renderSaisieErrors(errors){
  if(!errors||!errors.length)return h('div',{className:'card-empty'},'✅ Aucune erreur de saisie détectée');
  const typeCount={};errors.forEach(e=>{typeCount[e.type]=(typeCount[e.type]||0)+1;});
  const summary=h('div',{style:{display:'flex',gap:'10px',flexWrap:'wrap',padding:'14px 20px',borderBottom:'1px solid var(--border)'}},
    ...Object.entries(typeCount).map(([t,c])=>{const info=ERROR_LABELS[t]||{icon:'🔴',label:t};return h('div',{style:{background:'rgba(248,113,113,.1)',borderRadius:'8px',padding:'6px 12px',fontSize:'12px',color:'var(--danger)',fontWeight:'600'}},info.icon+' '+info.label+' ('+c+')');})
  );
  const list=h('div',{style:{padding:'16px 20px',display:'flex',flexDirection:'column',gap:'8px'}},
    ...errors.slice(0,50).map(e=>{const info=ERROR_LABELS[e.type]||{icon:'🔴',label:e.type};return h('div',{className:'error-card'},h('div',{className:'ec-type'},info.icon+' '+info.label),h('div',{className:'ec-msg'},e.message),h('div',{className:'ec-detail'},e.detail||''),h('div',{className:'ec-meta'},h('span',null,'👤 '+opName(e.operateur)),h('span',null,'📅 '+e.jour),e.no_dossier?h('span',null,'📁 Dos. '+e.no_dossier):null,e.machine?h('span',null,'⚙ '+e.machine):null));})
  );
  return h('div',null,summary,list);
}

// ── Historique ──────────────────────────────────────────────────
function renderHist(){
  const d=S.historique;
  if(!d)return h('div',{className:'card-empty'},'Importez un fichier XLSX pour voir les données');
  if(d.blocked)return h('div',{className:'card'},h('div',{className:'card-blocked'},h('div',{className:'cb-icon'},'🔒'),h('div',{className:'cb-msg'},d.message)));
  const sc=d.severity_counts||{};const seCount=d.saisie_errors_count||0;const parts=[];
  if(d.sanity)parts.push(renderSanity(d.sanity));
  parts.push(h('div',{className:'stats'},
    h('div',{className:'stat'},h('div',{className:'stat-label'},'Total opérations'),h('div',{className:'stat-value',style:{color:'var(--c1)'}},fN(d.total_operations))),
    h('div',{className:'stat',style:{borderColor:'var(--danger)33'}},h('div',{className:'stat-label'},'🔴 Critique'),h('div',{className:'stat-value',style:{color:'var(--danger)'}},fN(sc.critique))),
    h('div',{className:'stat',style:{borderColor:'var(--warn)33'}},h('div',{className:'stat-label'},'🟡 Attention'),h('div',{className:'stat-value',style:{color:'var(--warn)'}},fN(sc.attention))),
    h('div',{className:'stat'},h('div',{className:'stat-label'},'🟢 Normal'),h('div',{className:'stat-value',style:{color:'var(--success)'}},fN(sc.info))),
    h('div',{className:'stat',style:{borderColor:'var(--danger)55'}},h('div',{className:'stat-label'},'⛔ Erreurs saisie'),h('div',{className:'stat-value',style:{color:seCount>0?'var(--danger)':'var(--success)'}},fN(seCount))),
  ));
  parts.push(h('div',{className:'section-title'},'⛔ Erreurs de saisie'));
  parts.push(h('div',{className:'card'},h('div',{className:'card-header'},h('h3',null,'Contrôle Arrivée / Départ / Dossiers'),seCount>0?h('span',{className:'badge-danger'},seCount+' erreur'+(seCount>1?'s':'')):h('span',{className:'badge'},'OK')),renderSaisieErrors(d.saisie_errors||[])));
  if(d.operator_issues&&d.operator_issues.length){
    const m={};d.operator_issues.forEach(r=>{if(!m[r.operateur])m[r.operateur]={critique:0,attention:0};m[r.operateur][r.operation_severity]=r.c;});
    const mx=Math.max(...Object.values(m).map(v=>v.critique+v.attention),1);
    parts.push(h('div',{className:'card'},h('div',{className:'card-header'},h('h3',null,'Incidents par opérateur')),h('div',{style:{padding:'16px 0'}},...Object.entries(m).map(([op,v])=>{const t=v.critique+v.attention;return h('div',{className:'bar-row'},h('div',{className:'bar-label'},opName(op)),h('div',{className:'bar-track'},h('div',{className:'bar-fill',style:{width:(t/mx*100)+'%',background:v.critique>0?'var(--danger)':'var(--warn)',minWidth:'30px'}},h('span',{className:'bar-val'},String(t)))));}))));
  }
  if(d.issues&&d.issues.length){
    parts.push(h('div',{className:'card'},h('div',{className:'card-header'},h('h3',null,'Détail incidents ('+d.issues.length+')')),
      h('div',{style:{overflowX:'auto'}},h('table',null,
        h('thead',null,h('tr',null,h('th',null,'Sévérité'),h('th',null,'Date'),h('th',null,'Opérateur'),h('th',null,'Opération'),h('th',null,'Machine'),h('th',null,'Dossier'))),
        h('tbody',null,...d.issues.map(r=>h('tr',null,h('td',null,h('span',{className:'sev-dot '+r.operation_severity}),h('span',{className:'sev-'+r.operation_severity},r.operation_severity.toUpperCase())),h('td',null,fD(r.date_operation)),h('td',null,opName(r.operateur)),h('td',null,r.operation||''),h('td',null,r.machine||''),h('td',null,r.no_dossier||''))))
      ))
    ));
  }
  return h('div',null,...parts);
}

// ── Production ──────────────────────────────────────────────────
function renderProd(){
  const d=S.production;
  if(!d)return h('div',{className:'card-empty'},'Importez un fichier XLSX pour voir les données');
  if(d.blocked)return h('div',{className:'card'},h('div',{className:'card-blocked'},h('div',{className:'cb-icon'},'🔒'),h('div',{className:'cb-msg'},d.message)));
  const taux=d.total_prevue>0?Math.round(d.total_realisee/d.total_prevue*100):0;
  const tt=d.temps_totaux||{};const parts=[];
  parts.push(h('div',{className:'section-title'},'📦 Quantités'));
  parts.push(h('div',{className:'stats'},
    h('div',{className:'stat'},h('div',{className:'stat-label'},'Dossiers'),h('div',{className:'stat-value',style:{color:'var(--c1)'}},fN(d.dossier_count))),
    h('div',{className:'stat'},h('div',{className:'stat-label'},'Qté prévue'),h('div',{className:'stat-value',style:{color:'var(--c2)'}},fN(d.total_prevue))),
    h('div',{className:'stat'},h('div',{className:'stat-label'},'Qté réalisée'),h('div',{className:'stat-value',style:{color:'var(--c3)'}},fN(d.total_realisee))),
    h('div',{className:'stat'},h('div',{className:'stat-label'},'Taux'),h('div',{className:'stat-value',style:{color:taux>=90?'var(--success)':taux>=50?'var(--warn)':'var(--danger)'}},taux+'%')),
  ));
  parts.push(h('div',{className:'section-title'},'⏱ Temps'));
  parts.push(h('div',{className:'time-kpi'},
    h('div',{className:'time-card'},h('div',{className:'tc-label'},'🔧 Calage'),h('div',{className:'tc-value',style:{color:'var(--c4)'}},fMin(tt.calage_min)),h('div',{className:'tc-sub'},'Code 02')),
    h('div',{className:'time-card'},h('div',{className:'tc-label'},'▶ Production'),h('div',{className:'tc-value',style:{color:'var(--c3)'}},fMin(tt.production_min)),h('div',{className:'tc-sub'},'Codes 03+88')),
    h('div',{className:'time-card'},h('div',{className:'tc-label'},'📂 Hors calage'),h('div',{className:'tc-value',style:{color:'var(--c1)'}},fMin(tt.hors_calage_min)),h('div',{className:'tc-sub'},'01→89 - calage')),
    h('div',{className:'time-card'},h('div',{className:'tc-label'},'📂 Total'),h('div',{className:'tc-value',style:{color:'var(--c2)'}},fMin(tt.avec_calage_min)),h('div',{className:'tc-sub'},'01→89')),
  ));
  if(d.dossier_times&&d.dossier_times.length){
    parts.push(h('div',{className:'card'},h('div',{className:'card-header'},h('h3',null,'Temps par dossier'),h('span',{style:{fontSize:'11px',color:'var(--muted)'}},d.dossier_times.length+' dossiers')),
      h('div',{style:{overflowX:'auto'}},h('table',null,
        h('thead',null,h('tr',null,h('th',null,'Dossier'),h('th',null,'Opérateur'),h('th',null,'Machine'),h('th',null,'Date'),h('th',null,'⏱ Total'),h('th',null,'🔧 Calage'),h('th',null,'▶ Prod'),h('th',null,'📂 Hors calage'))),
        h('tbody',null,...d.dossier_times.map(r=>h('tr',null,h('td',{style:{fontWeight:'600',fontFamily:'monospace',color:'var(--text)'}},r.no_dossier||''),h('td',null,opName(r.operateur)),h('td',null,r.machine||''),h('td',{style:{fontFamily:'monospace',fontSize:'11px'}},r.jour||''),h('td',{style:{fontFamily:'monospace',color:'var(--c2)',fontWeight:'600'}},fMin(r.temps_total_calage_min)),h('td',{style:{fontFamily:'monospace',color:r.temps_calage_min>30?'var(--warn)':'var(--text2)'}},fMin(r.temps_calage_min)),h('td',{style:{fontFamily:'monospace',color:'var(--c3)'}},fMin(r.temps_prod_min)),h('td',{style:{fontFamily:'monospace',color:'var(--c1)'}},fMin(r.temps_total_min)))))
      ))
    ));
  }
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
  const current = (S.saisies?.rows || []).find(r => r.id === entry.data.id);

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
  const current = (S.saisies?.rows || []).find(r => r.id === entry.data.id);
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
  const timeI = h('input', { type: 'time', value: tv, style: { width: '110px' } });
  // force 24h sur Safari via pattern
  timeI.setAttribute('step', '60');
  const wrapper = h('div', { style: { display:'flex', gap:'8px' } }, dateI, timeI);
  return { wrapper, getVal: () => inputValToFrDate(dateI.value, timeI.value) };
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
      if (prefill?.operation && prefill.operation.startsWith(code)) opt.selected = true;
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
  if (prefill?.operation) {
    const code = prefill.operation.match(/^(\d+)/)?.[1];
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
        if (o === (prefill?.operateur || '')) opt.selected = true;
        return opt;
      })
    );
  } else {
    opField = h('input', { type: 'text', value: S.user?.operateur_lie || '' });
    opField.disabled = true;
  }
 
  // Date 24h
  const { wrapper: dateWrapper, getVal: getDateVal } = makeDateTimeFields(prefill?.date_operation || '');
 
  const machI  = h('input', { type: 'text', placeholder: 'ex: 1 - COHESIO 1', value: prefill?.machine      || '' });
  const dosI   = h('input', { type: 'text', placeholder: 'ex: 1060',           value: prefill?.no_dossier  || '' });
  const qteAI  = h('input', { type: 'number', placeholder: '0',                value: prefill?.quantite_a_traiter ?? 0 });
  const qteTI  = h('input', { type: 'number', placeholder: '0',                value: prefill?.quantite_traitee   ?? 0 });
  const noteI  = h('input', { type: 'text', placeholder: 'Raison (optionnel)',  value: '' });
  const commentaireI = h('input', { type: 'text', placeholder: 'Observation, remarque...', value: prefill?.commentaire || '' });
  const metragePrevuI = h('input', { type: 'number', placeholder: '0', value: prefill?.metrage_prevu ?? '' });
  const metrageReelI  = h('input', { type: 'number', placeholder: '0', value: prefill?.metrage_reel  ?? '' });
  inputs.metrage_prevu = metragePrevuI;
  inputs.metrage_reel  = metrageReelI;
 
  const modal = h('div', { className: 'add-row-modal', onClick: e => { if (e.target === modal) closeModal(); } },
    h('div', { className: 'add-row-form' },
      h('h3', null, title),
      h('div', { className: 'form-row' },
        h('div', null, h('label', null, 'Opération *'), opSel, opPreview),
        h('div', null, h('label', null, 'Opérateur *'), opField)
      ),
      h('div', { className: 'form-row' },
        h('div', null, h('label', null, 'Date & Heure (JJ/MM/AAAA HH:MM)'), dateWrapper),
        h('div', null, h('label', null, 'Machine'), machI)
      ),
      h('div', { className: 'form-row' },
        h('div', null, h('label', null, 'No Dossier'), dosI),
        h('div', null, h('label', null, 'Qté à traiter'), qteAI)
      ),
      h('div', { className: 'form-row' },
        h('div', null, h('label', null, 'Qté traitée'), qteTI),
        h('div', null, h('label', null, 'Note'), noteI)
      ),
      h('div', { className: 'form-row' },
        h('div', null,
          h('label', null, 'Métrage prévu (m)'),
          metragePrevuI
        ),
        h('div', null,
          h('label', null, 'Métrage réel (m)'),
          metrageReelI
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
            onSubmit({
              operation:          opText,
              operateur:          opField.value || '',
              date_operation:     getDateVal(),
              machine:            machI.value  || '',
              no_dossier:         dosI.value   || '',
              quantite_a_traiter: parseFloat(qteAI.value) || 0,
              quantite_traitee:   parseFloat(qteTI.value) || 0,
              note:               noteI.value  || '',
              commentaire:       commentaireI.value || '',
              metrage_prevu:     parseFloat(inputs.metrage_prevu?.value) || null,
              metrage_reel:      parseFloat(inputs.metrage_reel?.value)  || null,
            });
          }}, submitLabel)
        )
      )
    )
  );
  return modal;
}
 
function closeModal() {
  document.querySelector('.add-row-modal')?.remove();
}
 
function openAddModal(templateRow) {
  document.querySelector('.add-row-modal')?.remove();
  const modal = buildSaisieForm(
    templateRow,
    '➕ Ajouter une saisie',
    '✓ Ajouter',
    (body) => { addSaisie(body); closeModal(); }
  );
  document.getElementById('root').appendChild(modal);
}
 
function openEditModal(row) {
  document.querySelector('.add-row-modal')?.remove();
 
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
  }, '🗑 Supprimer');
 
  const modal = buildSaisieForm(
    row,
    '✏ Modifier la saisie',
    '✓ Enregistrer',
    async (body) => {
      pushUndo('edit', row);  //
      closeModal();
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
  const snaps=(S.saisies?.rows||[]).filter(r=>ids.includes(r.id));
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
  if(!isAdmin(S.user)&&!S.user?.operateur_lie)
    return h('div',{className:'card'},h('div',{className:'card-blocked'},h('div',{className:'cb-icon'},'🔒'),h('div',{className:'cb-msg'},'Compte non lié à un opérateur.')));
 
  const readOnly=isFab(S.user);
 
  // ── Tri ──────────────────────────────────────────────────────
  let rows=d.rows||[];
  if(S.sortState.col) rows=sortRows(rows,S.sortState.col,S.sortState.asc);
 
  const COLS=[
    {key:'date_operation',  label:'Date'},
    {key:'operation',       label:'Opération'},
    {key:'operateur',       label:'Opérateur'},
    {key:'machine',         label:'Machine'},
    {key:'no_dossier',      label:'Dossier'},
    {key:'quantite_a_traiter', label:'Qté prévue'},
    {key:'quantite_traitee',   label:'Qté traitée'},
    {key:'metrage_prevu',   label:'Métrage prévu (m)'},
    {key:'metrage_reel',    label:'Métrage réel (m)'},
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
 
    tr.appendChild(h('td',{style:{fontFamily:'monospace',fontSize:'11px',color:'var(--muted)',whiteSpace:'nowrap'}},fD(row.date_operation)));
    tr.appendChild(h('td',null,row.operation||'-'));
    tr.appendChild(h('td',null,opName(row.operateur)));
    tr.appendChild(h('td',null,row.machine||'-'));
    tr.appendChild(h('td',{style:{fontFamily:'monospace'}},row.no_dossier||'-'));
    tr.appendChild(h('td',{style:{fontFamily:'monospace'}},fN(row.quantite_a_traiter)));
    tr.appendChild(h('td',{style:{fontFamily:'monospace'}},fN(row.quantite_traitee)));
    tr.appendChild(h('td',{style:{fontFamily:'monospace',color:'var(--c2)'}},
      row.metrage_prevu!=null ? fN(row.metrage_prevu)+' m' : '-'));
    tr.appendChild(h('td',{style:{fontFamily:'monospace',color:'var(--c3)'}},
      row.metrage_reel!=null  ? fN(row.metrage_reel) +' m' : '-'));
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
 
  if(readOnly){
    headerRight.appendChild(h('span',{className:'readonly-notice'},'👁 Lecture seule'));
  }else{
    const btnUndo=h('button',{id:'btn-undo',className:'btn-ghost',title:'Annuler ('+undoStack.length+')',onClick:doUndo},'← Annuler ('+undoStack.length+')');
    if(undoStack.length===0) btnUndo.setAttribute('disabled','true');
    const btnRedo=h('button',{id:'btn-redo',className:'btn-ghost',title:'Rétablir ('+redoStack.length+')',onClick:doRedo},'Rétablir → ('+redoStack.length+')');
    if(redoStack.length===0) btnRedo.setAttribute('disabled','true');
 
    headerRight.appendChild(btnUndo);
    headerRight.appendChild(btnRedo);
 
    if(selCount>0){
      headerRight.appendChild(h('button',{className:'btn-danger',onClick:bulkDelete},'🗑 Supprimer ('+selCount+')'));
    }
    headerRight.appendChild(h('button',{className:'btn-sm',onClick:()=>openAddModal(rows[rows.length-1]||null)},'+ Ajouter'));
    headerRight.appendChild(h('button',{className:'btn-ghost',onClick:()=>exportBlob('/api/saisies/export-modifiees','saisies_modifiees.xlsx')},'⬇ Export'));
  }
 
  return h('div',null,
    h('div',{className:'card'},
      h('div',{className:'card-header'},
        h('h3',null,'Saisies ('+d.total+')'),
        h('div',{style:{display:'flex',gap:'12px',alignItems:'center'}},
          !readOnly?h('span',{style:{fontSize:'11px',color:'var(--muted)'}},'Clic pour modifier'):null,
          headerRight
        )
      ),
      // Wrapper synchronisé : scrollbar miroir en haut ↔ bas
      (() => {
        const tableEl = h('table',null,
          h('thead',null,h('tr',null,...ths)),
          tbody
        );
        const bot = h('div',{style:{overflowX:'auto',paddingBottom:'4px'}},tableEl);
        const topInner = h('div',{style:{height:'1px',width:tableEl.scrollWidth+'px'}});
        const top = h('div',{style:{overflowX:'auto',height:'10px',marginBottom:'0'}},topInner);
        // Synchronisation scroll
        top.addEventListener('scroll',()=>{ bot.scrollLeft = top.scrollLeft; });
        bot.addEventListener('scroll',()=>{ top.scrollLeft = bot.scrollLeft; });
        // Mettre à jour la largeur fantôme après rendu
        requestAnimationFrame(()=>{
          topInner.style.width = tableEl.offsetWidth+'px';
        });
        return h('div',null,top,bot);
      })()
    )
  );
}

// ── Import ──────────────────────────────────────────────────────
function renderImport(){
  const zone=h('div',{className:'drop-zone'},h('div',{className:'dz-icon'},'☁'),h('div',{className:'dz-title'},'Glisser un fichier ici'),h('div',{className:'dz-sub'},'CSV, Excel (.xlsx, .xls, .xlsm) — ou cliquer pour parcourir'));
  const inp=h('input',{type:'file',accept:'.csv,.xlsx,.xls,.xlsm',style:{display:'none'}});
  inp.addEventListener('change',e=>{if(e.target.files[0])upload(e.target.files[0]);});
  zone.addEventListener('click',()=>inp.click());zone.addEventListener('dragover',e=>{e.preventDefault();zone.classList.add('drag');});zone.addEventListener('dragleave',()=>zone.classList.remove('drag'));
  zone.addEventListener('drop',e=>{e.preventDefault();zone.classList.remove('drag');if(e.dataTransfer.files[0])upload(e.dataTransfer.files[0]);});
  zone.appendChild(inp);
  const list=h('div',{className:'card'},h('div',{className:'card-header'},h('h3',null,'Historique des imports ('+S.imports.length+')')),
    S.imports.length===0?h('div',{className:'card-empty'},'Aucun import encore'):
    h('div',null,...S.imports.map(i=>h('div',{className:'import-row'},
      h('div',{style:{flex:1}},h('div',{style:{fontSize:'14px',fontWeight:'500',color:'var(--text)'}},i.filename),h('div',{style:{fontSize:'11px',color:'var(--muted)',fontFamily:'monospace',marginTop:'2px'}},(i.imported_at||'').slice(0,16).replace('T',' ')+'  —  '+i.row_count+' lignes')),
      h('div',{style:{display:'flex',gap:'8px'}},h('button',{className:'btn-ghost',onClick:()=>exportBlob('/api/imports/'+i.id+'/export',i.filename.replace(/\.[^.]+$/,'')+'_export.xlsx')},'⬇ Export'),h('button',{className:'btn-danger',onClick:()=>deleteImport(i.id,i.filename)},'🗑 Supprimer'))
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

// ── Users ───────────────────────────────────────────────────────
function renderUsers(){
  const inputs={};
  const ops=S.filters.operators||[];
  const opSel=h('select',{className:'form-sel'},h('option',{value:''},'— Lier un opérateur (optionnel) —'),...ops.map(o=>h('option',{value:o},opName(o))));inputs.operateur_lie=opSel;
  const roleSel=h('select',{className:'form-sel'},h('option',{value:'fabrication'},'⚙ Fabrication'),h('option',{value:'administration'},'🔧 Administration'),h('option',{value:'direction'},'👑 Direction'),h('option',{value:'logistique'},'📦 Logistique'));inputs.role=roleSel;
  const hint=h('p',{style:{fontSize:'12px',color:'var(--muted)',marginTop:'10px'}},'');
  const opWrap=h('div',null,opSel);
  // Charger les machines depuis l'API planning
  const machines = S.machines || [];
  const machineSel = h('select', {className:'form-sel'},
    h('option', {value:''}, '— Machine par défaut (Fabrication) —'),
    ...machines.map(m => h('option', {value: String(m.id)}, m.nom))
  );
  inputs.machine_id = machineSel;
  // Wrapper machine — visible seulement pour Fabrication
  const machineWrap = h('div', null,
    h('label', {style:{display:'block',fontSize:'11px',fontWeight:'600',color:'var(--muted)',textTransform:'uppercase',letterSpacing:'.5px',marginBottom:'4px'}}, 'Machine par défaut'),
    machineSel
  );
  const syncRoleUI=()=>{
    const r=inputs.role.value;
    const hideOp=(r==='direction'||r==='administration'||r==='logistique');
    const showMachine = r === 'fabrication';
    opWrap.style.display = hideOp ? 'none' : '';
    machineWrap.style.display = showMachine ? '' : 'none';
    hint.textContent = (r==='fabrication')
      ? '💡 Fabrication = lecture seule. Sans opérateur lié → accès bloqué.'
      : '💡 Direction / Administration / Logistique : pas de liaison opérateur.';
    if(hideOp) opSel.value='';
  };
  roleSel.addEventListener('change',syncRoleUI);
  const form=h('div',{className:'card',style:{padding:'20px'}},h('h3',{style:{fontSize:'14px',fontWeight:'600',marginBottom:'16px'}},'Créer un compte'),
    h('div',{className:'form-grid'},...[['nom','Nom complet *','text'],['email','Email *','email'],['password','Mot de passe * (min. 8 car.)','password']].map(([k,l,t])=>{const i=h('input',{placeholder:l,type:t});inputs[k]=i;return i;}),roleSel,opWrap,machineWrap),
    hint,
    h('button',{className:'btn',onClick:()=>{if(!inputs.nom.value||!inputs.email.value||!inputs.password.value)return;createUser({nom:inputs.nom.value,email:inputs.email.value,password:inputs.password.value,role:inputs.role.value,operateur_lie:inputs.operateur_lie.value||null,machine_id: inputs.machine_id?.value || null});['nom','email','password'].forEach(k=>inputs[k].value='');}},'Créer le compte')
  );
  setTimeout(syncRoleUI,0);
  const list=h('div',{className:'card'},h('div',{className:'card-header'},h('h3',null,'Utilisateurs ('+S.users.length+')'),h('span',{style:{fontSize:'11px',color:'var(--muted)'}},'Dernière connexion')),
    S.users.length===0?h('div',{className:'card-empty'},'Aucun utilisateur'):
    h('div',null,...S.users.map(u=>{
      const rb=h('span',{className:ROLE_BADGE[u.role]||'badge'},ROLE_LABELS[u.role]||u.role);
      const ab=!u.actif?h('span',{className:'badge-inactif'},'Inactif'):null;
      const showOpLink = !(u.role==='direction'||u.role==='administration'||u.role==='logistique');
      const lb=!showOpLink
        ? h('span',{style:{fontSize:'11px',color:'var(--muted)'}},'—')
        : (u.operateur_lie
          ? h('span',{style:{fontSize:'11px',color:'var(--accent)',cursor:'pointer',textDecoration:'underline'},onClick:()=>openUserDetail(u.id)},'🔗 '+opName(u.operateur_lie))
          : h('span',{style:{fontSize:'11px',color:'var(--danger)',cursor:'pointer',textDecoration:'underline'},onClick:()=>openUserDetail(u.id)},'⚠ Non lié — Configurer'));
      const mach = (u.role==='fabrication' && (u.machine_nom || u.machine_id))
        ? h('div',{className:'ui-last'},'🧷 '+(u.machine_nom || ('Machine #'+u.machine_id)))
        : null;
      return h('div',{className:'user-row'},
        h('div',null,h('div',{className:'ui-name'},u.nom,rb,ab),h('div',{className:'ui-email'},u.email),h('div',{className:'ui-last'},lb),mach,h('div',{className:'ui-last'},u.last_login?'🕐 '+fD(u.last_login):'🕐 Jamais connecté')),
        h('div',{className:'user-actions'},u.actif?h('button',{className:'btn-danger',onClick:()=>toggleUser(u.id,false)},'Désactiver'):h('button',{className:'btn-sm',onClick:()=>toggleUser(u.id,true)},'Réactiver'))
      );
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

function renderProfil(userData, isAdminView=false, onSave=null){
  // userData = objet user à afficher/modifier
  // isAdminView = true quand admin modifie un autre user
  const ops=S.filters.operators||[];
  const inputs={};

  const mkField=(label,key,type='text',val='')=>{
    const i=h('input',{type,placeholder:label,value:userData?.[key]||val});
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

  const adminFields=[];
  if(isAdminView){
    // Rôle
    const roleSel=h('select',{className:'form-sel'},
      h('option',{value:'fabrication'},'⚙ Fabrication'),
      h('option',{value:'administration'},'🔧 Administration'),
      h('option',{value:'direction'},'👑 Direction'),
      h('option',{value:'logistique'},'📦 Logistique'),
    );
    roleSel.value=userData?.role||'fabrication';
    inputs.role=roleSel;

    // Opérateur lié
    const opSel=h('select',{className:'form-sel'},
      h('option',{value:''},'— Sans liaison —'),
      ...ops.map(o=>{const opt=h('option',{value:o},opName(o));if(o===userData?.operateur_lie)opt.selected=true;return opt;})
    );
    inputs.operateur_lie=opSel;

    // Machine par défaut (Fabrication)
    const machines = S.machines || [];
    const machineSel = h('select', {className:'form-sel'},
      h('option', {value:''}, '— Machine par défaut (Fabrication) —'),
      ...machines.map(m => {
        const opt=h('option', {value: String(m.id)}, m.nom);
        if(String(m.id)===String(userData?.machine_id||'')) opt.selected=true;
        return opt;
      })
    );
    inputs.machine_id = machineSel;

    // Actif
    const actifChk=h('input',{type:'checkbox'});
    actifChk.checked=userData?.actif!==0;
    inputs.actif=actifChk;

    const opFieldWrap=h('div',{style:{marginBottom:'14px'}},h('label',{style:{display:'block',fontSize:'11px',fontWeight:'600',color:'var(--muted)',textTransform:'uppercase',letterSpacing:'.5px',marginBottom:'5px'}},'Opérateur lié'),opSel);
    const machineWrap=h('div',{style:{marginBottom:'14px'}},h('label',{style:{display:'block',fontSize:'11px',fontWeight:'600',color:'var(--muted)',textTransform:'uppercase',letterSpacing:'.5px',marginBottom:'5px'}},'Machine par défaut'),machineSel);
    const syncAdminRole=()=>{
      const r=roleSel.value;
      const hide=(r==='direction'||r==='administration'||r==='logistique');
      opFieldWrap.style.display = hide ? 'none' : '';
      if(hide) opSel.value='';
      const showMachine = (r==='fabrication');
      machineWrap.style.display = showMachine ? '' : 'none';
      if(!showMachine) machineSel.value='';
    };
    roleSel.addEventListener('change',syncAdminRole);
    syncAdminRole();

    adminFields.push(
      h('div',{style:{marginBottom:'14px'}},h('label',{style:{display:'block',fontSize:'11px',fontWeight:'600',color:'var(--muted)',textTransform:'uppercase',letterSpacing:'.5px',marginBottom:'5px'}},'Rôle'),roleSel),
      opFieldWrap,
      machineWrap,
      h('label',{style:{display:'flex',alignItems:'center',gap:'8px',fontSize:'13px',color:'var(--text2)',marginBottom:'14px'}},actifChk,'Compte actif')
    );
  }

  const saveBtn=h('button',{className:'btn',onClick:async()=>{
    const body={};
    Object.entries(inputs).forEach(([k,el])=>{
      if(el.type==='checkbox') body[k]=el.checked?1:0;
      else if(el.value!==undefined) body[k]=el.value;
    });
    if(!body.password) delete body.password;
    if(!body.password_confirm) delete body.password_confirm;
    if(onSave) await onSave(body);
    else await saveProfil(body);
  }},'💾 Enregistrer');

  const infos=userData?[
    userData.created_at?h('p',{style:{fontSize:'11px',color:'var(--muted)',marginTop:'8px'}},'Créé le '+fD(userData.created_at)):null,
    userData.last_login?h('p',{style:{fontSize:'11px',color:'var(--muted)'}},'Dernière connexion : '+fD(userData.last_login)):null,
  ]:[];

  return h('div',{className:'card',style:{padding:'28px',maxWidth:'520px'}},
    h('h2',{style:{fontSize:'18px',fontWeight:'700',marginBottom:'6px'}},isAdminView?'✎ Fiche utilisateur':'👤 Mon profil'),
    h('p',{style:{fontSize:'13px',color:'var(--muted)',marginBottom:'24px'}},isAdminView?'Modification par l\'administrateur':'Modifiez vos informations personnelles'),
    ...fields,
    ...adminFields,
    h('hr',{style:{border:'none',borderTop:'1px solid var(--border)',margin:'20px 0'}}),
    pwdSection,
    saveBtn,
    ...infos
  );
}

async function openUserDetail(userId){
  try{
    const u=await api('/api/users/'+userId);
    if(!u)return;
    // Afficher dans un modal
    const modal=h('div',{className:'add-row-modal',onClick:e=>{if(e.target===modal)modal.remove();}},
      h('div',{style:{background:'var(--card)',border:'1px solid var(--border)',borderRadius:'16px',padding:'8px',width:'100%',maxWidth:'560px',boxShadow:'0 24px 64px rgba(0,0,0,.4)',maxHeight:'90vh',overflowY:'auto'}},
        renderProfil(u, true, async(body)=>{
          try{
            await api('/api/users/'+userId,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
            toast('Utilisateur mis à jour');
            modal.remove();
            await loadUsers();
          }catch(e){toast(e.message,'error');}
        })
      )
    );
    document.getElementById('root').appendChild(modal);
  }catch(e){toast(e.message,'error');}
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
      preview.filename+(preview.parse_errors?.length?' — ⚠ '+preview.parse_errors.length+' avertissement(s)':' — Données extraites automatiquement')),

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
  const iconMap={success:'✅',warn:'⚠️',danger:'❌'};
  const concl=h('div',{className:'conclusion-card',
    style:{borderColor:colMap[co.color]+'66',background:colMap[co.color]+'0D'}},
    h('div',{className:'conclusion-icon'},iconMap[co.color]),
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
  const devisList=S.devisList||[];
  const allDossiers=S.filters.dossiers||[];
  const parts=[];

  if(S.devisPreview){
    parts.push(renderDevisForm(S.devisPreview));
    return h('div',null,...parts);
  }

  const zone=h('div',{className:'drop-zone',style:{marginBottom:'20px',padding:'28px'}},
    h('div',{className:'dz-icon',style:{fontSize:'28px'}},'📋'),
    h('div',{className:'dz-title'},'Importer un devis'),
    h('div',{className:'dz-sub'},'Fichiers Excel (.xlsx, .xls) — glisser ou cliquer')
  );
  const inp=h('input',{type:'file',accept:'.xlsx,.xls',style:{display:'none'}});
  inp.addEventListener('change',e=>{if(e.target.files[0])uploadDevis(e.target.files[0]);});
  zone.addEventListener('click',()=>inp.click());
  zone.addEventListener('dragover',e=>{e.preventDefault();zone.classList.add('drag');});
  zone.addEventListener('dragleave',()=>zone.classList.remove('drag'));
  zone.addEventListener('drop',e=>{e.preventDefault();zone.classList.remove('drag');if(e.dataTransfer.files[0])uploadDevis(e.dataTransfer.files[0]);});
  zone.appendChild(inp);
  parts.push(zone);

  const liste=h('div',{style:{flex:'0 0 320px'}});
  const detail=h('div',{style:{flex:1}});

  if(devisList.length===0){
    liste.appendChild(h('div',{className:'card-empty'},'Aucun devis importé'));
  }else{
    devisList.forEach(dv=>{
      const isSelected=S.selDevis===dv.id;
      const card=h('div',{
        className:'devis-card'+(isSelected?' selected':''),
        onClick:async()=>{
          set({selDevis:dv.id,comparaison:null});
          await loadComparaison(dv.id);
        }
      },
        h('div',{className:'devis-title'},dv.client||dv.filename),
        h('div',{className:'devis-meta'},dv.filename),
        h('div',{className:'devis-meta'},dv.date_devis?'📅 '+dv.date_devis:''),
        h('div',{className:'devis-badges'},
          h('span',{className:dv.statut==='lie'?'badge-lie':'badge-attente'},
            dv.statut==='lie'
              ? '✅ Lié ('+dv.nb_dossiers_lies+' dossier'+(dv.nb_dossiers_lies>1?'s':'')+')'
              : '⏳ En attente de liaison'
          ),
          dv.format_h&&dv.format_v?h('span',{className:'badge'},dv.format_h+'×'+dv.format_v+' mm'):null
        )
      );
      liste.appendChild(card);
    });
  }

  if(S.selDevis&&S.comparaison){
    const comp=S.comparaison;
    const dosLies=(comp.dossiers||[]);
    detail.appendChild(h('div',{className:'card',style:{padding:'20px',marginBottom:'16px'}},
      h('div',{className:'form-section-title'},'🔗 Dossiers de production liés'),
      renderLiaisonDossiers(S.selDevis, dosLies, allDossiers)
    ));
    if(comp.reel){
      detail.appendChild(renderComparaison(comp));
    }else{
      detail.appendChild(h('div',{className:'card-empty',style:{padding:'32px'}},
        '📂 Liez des dossiers de production pour voir la comparaison'));
    }
    detail.appendChild(
      h('button',{className:'btn-danger',style:{marginTop:'8px'},onClick:()=>deleteDevis(S.selDevis)},
        '🗑 Supprimer ce devis'
      )
    );
  }else if(S.selDevis){
    detail.appendChild(h('div',{className:'card-empty'},'Chargement...'));
  }else{
    detail.appendChild(h('div',{className:'card-empty',style:{padding:'48px'}},
      '← Sélectionnez un devis pour voir la comparaison'));
  }

  parts.push(h('div',{style:{display:'flex',gap:'16px',alignItems:'flex-start'}},liste,detail));
  return h('div',null,...parts);
}

// ── Render ──────────────────────────────────────────────────────
function render(){
  const root=document.getElementById('root');root.innerHTML='';
  document.body.classList.toggle('sb-open', !!S.sidebarOpen);
  document.body.classList.toggle('has-topbar', S.app==='prod' || S.app==='stock');
  window.__MYSIFA_APP__ = S.app;

  if(!S.user||S.app==='login'){root.appendChild(renderLogin());}
  else if(S.app==='portal'){root.appendChild(renderPortal());}
  else if(S.app==='stock'){root.appendChild(renderStock());}
  else if(S.app==='prod'){
    const titles={historique:'Historique & Erreurs',production:'Production',saisies:'Saisies',import:'Import XLSX',dossiers:'Dossiers',users:'Utilisateurs',rentabilite:'Rentabilité',profil:'Mon profil'};
    const subs={historique:'Sanity Score, incidents et erreurs de saisie',production:'KPIs, temps et quantités',saisies:'Consulter et corriger les saisies',import:'Importer, exporter et supprimer',dossiers:'Suivi des dossiers',users:'Gestion des comptes et accès',rentabilite:'Comparaison devis / production réelle',profil:'Informations personnelles et mot de passe'};
    const topbar=h('div',{className:'mobile-topbar'},
      h('button',{type:'button',className:'mobile-menu-btn',onClick:toggleSidebar,'aria-label':'Menu'},'☰'),
      h('div',null,
        h('div',{className:'mobile-topbar-title'},titles[S.page]||''),
        h('div',{className:'mobile-topbar-sub'},subs[S.page]||'')
      )
    );
    root.appendChild(h('div',null,
      S.sidebarOpen?h('div',{className:'sidebar-overlay',onClick:closeSidebar}):null,
      h('div',{className:'app'},renderSidebar(),
        h('main',{className:'main'},h('div',{className:'container'},
          topbar,
          h('h1',null,titles[S.page]||''),h('div',{className:'subtitle'},subs[S.page]||''),
        (S.page==='historique'||S.page==='production'||S.page==='saisies')?renderFilters():null,
        S.page==='historique'?renderHist():null,
        S.page==='production'?renderProd():null,
        S.page==='saisies'?renderSaisies():null,
        S.page==='import'?renderImport():null,
        S.page==='dossiers'?renderDos():null,
        S.page==='users'?renderUsers():null,
        S.page==='rentabilite'?renderRentabilite():null,
        S.page==='profil'?renderProfil(S.user,false):null,
        ))
      )
    ));
  }

  if(S.toast){const c={success:'var(--success)',error:'var(--danger)'};root.appendChild(h('div',{className:'toast',style:{borderLeft:'3px solid '+(c[S.toast.type]||'var(--accent)')}},h('span',{style:{fontSize:'14px',color:c[S.toast.type]||'var(--accent)'}},S.toast.message)));}
}

async function nav(){
  if(S.page==='historique')await loadHist();
  else if(S.page==='production')await loadProd();
  else if(S.page==='saisies')await loadSaisies();
  else if(S.page==='import')await loadImports();
  else if(S.page==='rentabilite')await loadDevis();
  else if(S.page==='dossiers')await loadDos();
  else if(S.page==='users'){await loadMachines();await loadUsers();}
  render();
}

if(localStorage.getItem('theme')==='light')document.body.classList.add('light');
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

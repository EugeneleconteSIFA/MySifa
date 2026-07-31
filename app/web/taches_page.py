"""MySifa — Gestionnaire de tâches (page).

Route : /taches — super administrateur uniquement.

Trois vues : Kanban (glisser-déposer), Liste (filtrable / triable) et un
panneau de détail (description, checklist, sous-tâches, fichiers de contexte,
commentaires, journal d'activité).

Shell MySifa standard : sidebar invariable + topbar mobile + MySifaTheme +
MySifaUserChip + guides in-app partagés (mysifa_guides.js).
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import APP_VERSION, ROLE_SUPERADMIN
from services.auth_service import get_current_user

router = APIRouter()


@router.get("/taches", response_class=HTMLResponse)
def taches_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/taches", status_code=302)
        raise
    if (user.get("role") or "") != ROLE_SUPERADMIN:
        from app.web.access_denied import access_denied_response
        return access_denied_response("Gestionnaire de tâches")
    html = (
        TACHES_HTML
        .replace("__V_LABEL__", f"v{APP_VERSION}")
        .replace("__USER_ROLE__", str(user.get("role") or ""))
    )
    return HTMLResponse(content=html)


TACHES_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17">
<title>Gestionnaire de tâches — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="stylesheet" href="/static/mysifa_theme.css">
<link rel="stylesheet" href="/static/mysifa_user_chip.css">
<link rel="stylesheet" href="/static/mysifa_mobile_topbar.css">
<style>
:root{--bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;--muted:#94a3b8;--accent:#22d3ee;--accent-bg:rgba(34,211,238,.12);--ok:#34d399;--success:#34d399;--danger:#f87171;--warn:#fbbf24}
body.light{--bg:#f1f5f9;--card:#fff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;--muted:#64748b;--accent:#0891b2;--accent-bg:rgba(8,145,178,.10);--ok:#059669;--success:#059669;--danger:#dc2626;--warn:#d97706}
*{box-sizing:border-box}
body{margin:0;font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}

/* ── Shell ── */
.layout{display:flex;min-height:100vh}
.sidebar{width:220px;background:var(--card);border-right:1px solid var(--border);padding:20px 12px;display:flex;flex-direction:column;flex-shrink:0;height:100vh;position:sticky;top:0;overflow-y:auto;scrollbar-width:none}
.sidebar::-webkit-scrollbar{width:0}
.logo{padding:0 8px;margin-bottom:24px;border-radius:8px;cursor:pointer;transition:background .15s,color .15s}
.logo:hover{background:var(--accent-bg)}
.logo:hover .logo-brand{color:var(--accent)}
.logo-brand{font-size:15px;font-weight:800;transition:color .15s}.logo-brand span{color:var(--accent)}
.logo-sub{font-size:10px;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase;margin-top:2px}
.nav-btn{display:flex;align-items:center;gap:10px;width:100%;text-align:left;padding:10px 12px;border-radius:8px;border:none;background:transparent;color:var(--text2);font-size:13px;font-weight:500;cursor:pointer;font-family:inherit;transition:background .15s,color .15s,box-shadow .2s;margin-bottom:2px}
.nav-btn:hover,.nav-btn.active{background:var(--accent-bg);color:var(--accent)}
.nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(34,211,238,.25),0 0 18px rgba(34,211,238,.15)}
body.light .nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(8,145,178,.32),0 0 16px rgba(8,145,178,.12)}
.nav-badge{margin-left:auto;padding:1px 7px;border-radius:9px;background:var(--accent-bg);color:var(--accent);font-size:10px;font-weight:700;line-height:1.5}
.nav-badge.warn{background:rgba(251,191,36,.16);color:var(--warn)}
.back-mysifa{border:none!important;background:transparent!important;font-weight:400!important;color:var(--text2)!important;padding:8px 10px!important}
.back-mysifa:hover{color:var(--text)!important;background:transparent!important}
.back-mysifa .wm{font-weight:800;color:var(--text)}.back-mysifa .wm span{color:var(--accent)}
.sidebar-bottom{margin-top:auto;display:flex;flex-direction:column;gap:6px;padding-bottom:8px}
.user-chip{padding:10px 12px;border-radius:8px;background:var(--accent-bg);cursor:pointer}
.user-chip .uc-name{font-size:12px;font-weight:600;color:var(--text)}
.user-chip .uc-role{font-size:10px;color:var(--accent);text-transform:uppercase;letter-spacing:.5px}
.theme-btn,.logout-btn{display:flex;align-items:center;gap:8px;padding:10px 12px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-size:12px;width:100%;font-family:inherit;transition:background .15s,color .15s,border-color .15s}
.theme-btn:hover{background:var(--accent-bg);color:var(--accent);border-color:var(--accent)}
.logout-btn{border:none}
.logout-btn:hover{color:var(--danger);background:rgba(248,113,113,.1)}
.version{font-size:10px;color:var(--muted);font-family:monospace;padding:4px 12px}
.sidebar-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:200}
body.sb-open .sidebar-overlay{display:block}

.main{flex:1;min-width:0;padding:24px 26px 40px;overflow-x:hidden}
h1{font-size:22px;font-weight:700;margin:0}
.subtitle{font-size:13px;color:var(--muted);margin-top:4px}

/* ── En-tête ── */
.page-head{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-bottom:16px}
.head-title-row{display:flex;align-items:center;gap:10px}
.stats-row{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px}
.stat{display:flex;align-items:center;gap:8px;padding:8px 13px;background:var(--card);border:1px solid var(--border);border-radius:10px;font-size:12px;color:var(--text2);cursor:pointer;transition:border-color .15s,color .15s}
.stat:hover{border-color:var(--accent);color:var(--accent)}
.stat.active{border-color:var(--accent);background:var(--accent-bg);color:var(--accent)}
.stat b{font-size:15px;font-weight:800;color:var(--text)}
.stat.active b,.stat:hover b{color:var(--accent)}
.stat.alert b{color:var(--danger)}

/* ── Barre d'outils ── */
.toolbar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:16px}
.search-wrap{position:relative;flex:1;min-width:220px;max-width:380px}
.search-wrap svg{position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--muted);pointer-events:none}
input.search{width:100%;background:var(--card);border:1px solid var(--border);border-radius:10px;padding:10px 14px 10px 36px;color:var(--text);font-size:13px;font-family:inherit;outline:none;transition:border-color .15s}
input.search:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-bg)}
select.filter{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:10px 12px;color:var(--text2);font-size:12px;font-family:inherit;outline:none;cursor:pointer;transition:border-color .15s}
select.filter:focus,select.filter:hover{border-color:var(--accent)}
select.filter.on{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.seg{display:inline-flex;background:var(--card);border:1px solid var(--border);border-radius:10px;overflow:hidden}
.seg button{padding:9px 14px;border:none;background:var(--card);color:var(--text2);font-size:12px;font-weight:600;font-family:inherit;cursor:pointer;display:inline-flex;align-items:center;gap:7px;transition:background .15s,color .15s}
.seg button:hover{background:var(--bg)}
.seg button.active{background:var(--accent-bg);color:var(--accent)}
.btn{padding:10px 16px;border-radius:10px;border:none;background:var(--accent);color:var(--bg);font-weight:700;font-size:13px;cursor:pointer;font-family:inherit;transition:filter .15s;display:inline-flex;align-items:center;gap:7px;white-space:nowrap}
.btn:hover{filter:brightness(1.08)}
.btn.ghost{background:var(--card);border:1px solid var(--border);color:var(--text2)}
.btn.ghost:hover{background:var(--bg);border-color:var(--accent);color:var(--accent);filter:none}
.btn.danger{background:var(--danger);color:#fff}
.btn.small{padding:6px 11px;font-size:11px;border-radius:8px}
.btn:disabled{opacity:.5;cursor:not-allowed;filter:none}

/* ── Kanban ── */
.board{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(172px,1fr);gap:12px;align-items:start;overflow-x:auto;padding-bottom:14px}
.col{min-width:0;background:var(--card);border:1px solid var(--border);border-radius:14px;display:flex;flex-direction:column;max-height:calc(100vh - 250px)}
.col.drop{border-color:var(--accent);box-shadow:0 0 0 2px var(--accent-bg)}
.col-head{display:flex;align-items:center;gap:8px;padding:13px 14px;border-bottom:1px solid var(--border);flex-shrink:0}
.col-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.col-title{font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.5px;color:var(--text)}
.col-count{margin-left:auto;font-size:11px;font-weight:700;color:var(--muted);background:var(--bg);padding:2px 8px;border-radius:8px}
.col-body{padding:10px;display:flex;flex-direction:column;gap:9px;overflow-y:auto;min-height:80px;flex:1}
.col-add{margin:0 10px 10px;padding:9px;border:1px dashed var(--border);border-radius:9px;background:transparent;color:var(--muted);font-size:12px;font-family:inherit;cursor:pointer;transition:all .15s;flex-shrink:0}
.col-add:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}

.tcard{background:var(--bg);border:1px solid var(--border);border-left:3px solid var(--border);border-radius:10px;padding:11px 12px;cursor:pointer;transition:border-color .15s,transform .1s,box-shadow .15s}
.tcard:hover{border-color:var(--accent);box-shadow:0 4px 14px rgba(0,0,0,.18)}
.tcard.dragging{opacity:.45}
.tcard.prio-critique{border-left-color:var(--danger)}
.tcard.prio-haute{border-left-color:var(--warn)}
.tcard.prio-normale{border-left-color:var(--accent)}
.tcard.prio-basse{border-left-color:var(--muted)}
.tcard-top{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:7px}
.tcard-title{font-size:13px;font-weight:600;color:var(--text);line-height:1.4;margin-bottom:8px;word-break:break-word}
.tcard-foot{display:flex;align-items:center;gap:10px;flex-wrap:wrap;font-size:11px;color:var(--muted)}
.tcard-foot .mi{display:inline-flex;align-items:center;gap:4px}
.tcard-foot .mi svg{width:12px;height:12px}
.avatar{width:22px;height:22px;border-radius:50%;background:var(--accent-bg);color:var(--accent);font-size:9px;font-weight:800;display:inline-flex;align-items:center;justify-content:center;flex-shrink:0;overflow:hidden;letter-spacing:-.2px}
.avatar img{width:100%;height:100%;object-fit:cover}
.avatar.none{background:var(--bg);color:var(--muted);border:1px dashed var(--border)}
.tag{display:inline-flex;align-items:center;padding:2px 7px;border-radius:6px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.3px;background:var(--bg);color:var(--muted);border:1px solid var(--border)}
.tag.accent{background:var(--accent-bg);color:var(--accent);border-color:transparent}
.tag.warn{background:rgba(251,191,36,.15);color:var(--warn);border-color:transparent}
.tag.danger{background:rgba(248,113,113,.15);color:var(--danger);border-color:transparent}
.tag.ok{background:rgba(52,211,153,.15);color:var(--ok);border-color:transparent}
.tag.muted{background:var(--bg);color:var(--muted)}
.due{font-weight:700}
.due.late{color:var(--danger)}
.due.soon{color:var(--warn)}
.progress{height:4px;border-radius:3px;background:var(--border);overflow:hidden;margin-top:8px}
.progress i{display:block;height:100%;background:var(--accent);border-radius:3px}

/* ── Liste ── */
.table-wrap{background:var(--card);border:1px solid var(--border);border-radius:14px;overflow:auto}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:11px 12px;background:var(--bg);color:var(--muted);font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid var(--border);white-space:nowrap;cursor:pointer;user-select:none}
th:hover{color:var(--accent)}
th .sort{opacity:.4;margin-left:4px}
th.sorted .sort{opacity:1;color:var(--accent)}
td{padding:11px 12px;border-bottom:1px solid var(--border);color:var(--text2);vertical-align:middle}
tbody tr{cursor:pointer;transition:background .12s}
tbody tr:hover td{background:var(--accent-bg)}
td.t-titre{color:var(--text);font-weight:600;max-width:420px}
td.t-titre .sub{display:block;font-size:11px;color:var(--muted);font-weight:400;margin-top:2px}

.empty{text-align:center;padding:44px 20px;color:var(--muted);font-size:13px}
.empty b{display:block;color:var(--text2);font-size:14px;margin-bottom:6px}

/* ── Panneau de détail ── */
.drawer-back{position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:500;backdrop-filter:blur(3px);animation:fade .15s}
@keyframes fade{from{opacity:0}to{opacity:1}}
.drawer{position:fixed;top:0;right:0;bottom:0;width:min(680px,100vw);background:var(--card);border-left:1px solid var(--border);z-index:501;display:flex;flex-direction:column;box-shadow:-16px 0 48px rgba(0,0,0,.4);animation:slideL .18s ease}
@keyframes slideL{from{transform:translateX(30px);opacity:.4}to{transform:translateX(0);opacity:1}}
.dr-head{padding:16px 20px;border-bottom:1px solid var(--border);display:flex;align-items:flex-start;gap:12px;flex-shrink:0}
.dr-head-main{flex:1;min-width:0}
.dr-title{font-size:16px;font-weight:700;color:var(--text);line-height:1.35;word-break:break-word;border-radius:7px;padding:3px 5px;margin:-3px -5px;cursor:text}
.dr-title:hover{background:var(--bg)}
.dr-meta{font-size:11px;color:var(--muted);margin-top:5px}
.dr-close{width:32px;height:32px;border-radius:9px;border:1px solid var(--border);background:var(--bg);color:var(--text2);cursor:pointer;display:inline-flex;align-items:center;justify-content:center;flex-shrink:0;font-size:16px;line-height:1;transition:all .15s}
.dr-close:hover{border-color:var(--danger);color:var(--danger)}
.dr-tabs{display:flex;gap:2px;padding:0 14px;border-bottom:1px solid var(--border);flex-shrink:0;overflow-x:auto}
.dr-tab{padding:11px 13px;border:none;background:transparent;color:var(--muted);font-size:12px;font-weight:600;font-family:inherit;cursor:pointer;border-bottom:2px solid transparent;white-space:nowrap;display:inline-flex;align-items:center;gap:6px;transition:color .15s,border-color .15s}
.dr-tab:hover{color:var(--text2)}
.dr-tab.active{color:var(--accent);border-bottom-color:var(--accent)}
.dr-tab .n{background:var(--bg);border-radius:8px;padding:0 6px;font-size:10px;font-weight:700}
.dr-body{flex:1;overflow-y:auto;padding:18px 20px 26px}
.dr-pane{display:none}
.dr-pane.active{display:block}

.fgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-bottom:18px}
.field label{display:block;font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px}
.field input,.field select,.field textarea{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:9px;padding:9px 11px;color:var(--text);font-size:13px;font-family:inherit;outline:none;transition:border-color .15s}
.field input:focus,.field select:focus,.field textarea:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-bg)}
.field textarea{min-height:96px;resize:vertical;line-height:1.55}
.field.full{grid-column:1/-1}
.sec{margin-bottom:20px}
.sec-hd{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:9px}
.sec-hd h3{margin:0;font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.5px;color:var(--text2)}

.chk{display:flex;align-items:center;gap:9px;padding:8px 10px;background:var(--bg);border:1px solid var(--border);border-radius:9px;margin-bottom:6px}
.chk input[type=checkbox]{width:15px;height:15px;accent-color:var(--accent);cursor:pointer;flex-shrink:0}
.chk .lbl{flex:1;font-size:12.5px;color:var(--text2);word-break:break-word}
.chk.done .lbl{text-decoration:line-through;color:var(--muted)}
.chk .x{border:none;background:transparent;color:var(--muted);cursor:pointer;font-size:15px;line-height:1;padding:2px 4px;border-radius:5px}
.chk .x:hover{color:var(--danger);background:rgba(248,113,113,.12)}
.inline-add{display:flex;gap:7px;margin-top:8px}
.inline-add input{flex:1;background:var(--bg);border:1px solid var(--border);border-radius:9px;padding:8px 11px;color:var(--text);font-size:12.5px;font-family:inherit;outline:none}
.inline-add input:focus{border-color:var(--accent)}

.sub-item{display:flex;align-items:center;gap:9px;padding:9px 11px;background:var(--bg);border:1px solid var(--border);border-radius:9px;margin-bottom:6px;cursor:pointer;transition:border-color .15s}
.sub-item:hover{border-color:var(--accent)}
.sub-item .st{flex:1;font-size:12.5px;color:var(--text2);word-break:break-word}
.sub-item.done .st{text-decoration:line-through;color:var(--muted)}

.file-item{display:flex;align-items:center;gap:11px;padding:10px 12px;background:var(--bg);border:1px solid var(--border);border-radius:10px;margin-bottom:7px}
.file-ico{width:32px;height:32px;border-radius:8px;background:var(--accent-bg);color:var(--accent);display:flex;align-items:center;justify-content:center;flex-shrink:0}
.file-info{flex:1;min-width:0}
.file-name{font-size:12.5px;font-weight:600;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.file-meta{font-size:10.5px;color:var(--muted);margin-top:2px}
.drop-zone{border:1.5px dashed var(--border);border-radius:11px;padding:22px 16px;text-align:center;font-size:12.5px;color:var(--muted);cursor:pointer;transition:all .15s}
.drop-zone:hover,.drop-zone.over{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}

.cmt{display:flex;gap:10px;margin-bottom:14px}
.cmt-body{flex:1;min-width:0}
.cmt-hd{display:flex;align-items:baseline;gap:8px;margin-bottom:4px}
.cmt-auteur{font-size:12px;font-weight:700;color:var(--text)}
.cmt-date{font-size:10.5px;color:var(--muted)}
.cmt-msg{font-size:13px;color:var(--text2);line-height:1.6;white-space:pre-wrap;word-break:break-word}
.cmt-del{border:none;background:transparent;color:var(--muted);cursor:pointer;font-size:11px;padding:2px 5px;border-radius:5px;margin-left:auto}
.cmt-del:hover{color:var(--danger)}
.cmt-form{position:sticky;bottom:0;background:var(--card);padding-top:10px;border-top:1px solid var(--border);margin-top:6px}
.cmt-form textarea{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px 12px;color:var(--text);font-size:13px;font-family:inherit;outline:none;min-height:74px;resize:vertical}
.cmt-form textarea:focus{border-color:var(--accent)}

.act{display:flex;gap:10px;padding:9px 0;border-bottom:1px solid var(--border);font-size:12px;color:var(--text2)}
.act:last-child{border-bottom:none}
.act-dot{width:7px;height:7px;border-radius:50%;background:var(--accent);flex-shrink:0;margin-top:6px}
.act-date{margin-left:auto;font-size:10.5px;color:var(--muted);white-space:nowrap;flex-shrink:0}
.act b{color:var(--text)}

/* ── Modale ── */
.modal-back{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:600;display:flex;align-items:center;justify-content:center;padding:18px;backdrop-filter:blur(3px)}
.modal{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:22px;max-width:560px;width:100%;max-height:92vh;overflow:auto}
.modal h3{margin:0 0 16px;font-size:16px;font-weight:700}
.modal-actions{display:flex;gap:8px;justify-content:flex-end;margin-top:18px;flex-wrap:wrap}

.toast{position:fixed;top:22px;right:22px;background:var(--card);border:1px solid var(--border);border-left:3px solid var(--accent);border-radius:9px;padding:12px 18px;font-size:13px;color:var(--text);z-index:900;box-shadow:0 10px 26px rgba(0,0,0,.32);animation:slideIn .18s}
.toast.err{border-left-color:var(--danger)}
@keyframes slideIn{from{transform:translateX(18px);opacity:0}to{transform:translateX(0);opacity:1}}

@media (max-width:1400px) and (min-width:901px){
  .main{padding-left:16px;padding-right:16px}
  .board{gap:10px}
  .col-body{padding:8px;gap:8px}
  .col-head{padding:11px 11px}
  .col-add{margin:0 8px 8px}
}
@media (max-width:900px){
  body.has-topbar .main{padding-top:74px}
  .main{padding:16px 14px 34px}
  .sidebar{position:fixed;left:0;top:0;bottom:0;height:auto;max-height:100vh;z-index:300;transform:translateX(-105%);transition:transform .18s ease;box-shadow:0 16px 48px rgba(0,0,0,.55)}
  body.sb-open .sidebar{transform:translateX(0)}
  .board{display:flex;overflow-x:auto}
  .col{flex:0 0 264px;width:264px;max-height:none}
  .fgrid{grid-template-columns:1fr}
  .drawer{width:100vw;border-left:none}
  .search-wrap{max-width:none}
}
@media (min-width:901px){.mobile-topbar{display:none}}
</style>
</head>
<body class="has-topbar">
<script src="/static/mysifa_theme.js"></script>
<script src="/static/mysifa_user_chip.js"></script>
<script src="/static/mysifa_guides.js"></script>

<div class="sidebar-overlay" id="sb-ov" onclick="closeSidebar()"></div>

<div class="layout">
  <aside class="sidebar">
    <div class="logo" onclick="showView('kanban')" title="Vue Kanban">
      <div class="logo-brand">My<span>Tâches</span></div>
      <div class="logo-sub">Gestionnaire</div>
    </div>

    <button type="button" class="nav-btn active" id="nav-kanban" onclick="showView('kanban')">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="3" width="6" height="18" rx="1"/><rect x="10" y="3" width="6" height="12" rx="1"/><rect x="17" y="3" width="4" height="8" rx="1"/></svg>
      Kanban
    </button>
    <button type="button" class="nav-btn" id="nav-liste" onclick="showView('liste')">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
      Liste
      <span class="nav-badge" id="badge-total">0</span>
    </button>
    <button type="button" class="nav-btn" id="nav-archives" onclick="showView('archives')">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5" rx="1"/><line x1="10" y1="12" x2="14" y2="12"/></svg>
      Archives
    </button>

    <div class="sidebar-bottom">
      <button type="button" class="nav-btn back-mysifa" onclick="location.href='/'">
        ← Retour <span class="wm">My<span>Sifa</span></span>
      </button>
      <div class="user-chip" onclick="location.href='/profil'" title="Mon profil">
        <div class="uc-name" id="uc-name">—</div>
        <div class="uc-role" id="uc-role">—</div>
      </div>
      <button type="button" class="theme-btn" id="btn-theme">
        <span class="theme-ico" id="theme-ico"></span>
        <span class="theme-label" id="theme-label">Mode clair</span>
      </button>
      <button type="button" class="logout-btn" id="btn-logout">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
        Déconnexion
      </button>
      <div class="version">Tâches · __V_LABEL__</div>
    </div>
  </aside>

  <main class="main">
    <div class="mobile-topbar">
      <button type="button" class="mobile-menu-btn" onclick="toggleSidebar()" aria-label="Menu">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
      </button>
      <div>
        <div class="mobile-topbar-title">Tâches</div>
        <div class="mobile-topbar-sub" id="mobile-sub">Kanban</div>
      </div>
      <button type="button" class="mobile-home-btn" onclick="location.href='/'" aria-label="Accueil">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 10.5L12 3l9 7.5"/><path d="M5 10v11h14V10"/><path d="M10 21v-6h4v6"/></svg>
      </button>
    </div>

    <div class="page-head">
      <div>
        <div class="head-title-row">
          <h1 id="page-title">Kanban</h1>
          <span id="guide-btn-slot"></span>
        </div>
        <div class="subtitle" id="page-sub">Ce que l'équipe doit faire, en cours et terminé.</div>
      </div>
      <button type="button" class="btn" onclick="openTacheModal()">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        Nouvelle tâche
      </button>
    </div>

    <div class="stats-row" id="stats-row"></div>

    <div class="toolbar" id="toolbar">
      <div class="search-wrap">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.7" y2="16.7"/></svg>
        <input type="text" class="search" id="f-q" placeholder="Rechercher (titre, description…)" autocomplete="off">
      </div>
      <select class="filter" id="f-assigne"><option value="">Tout le monde</option></select>
      <select class="filter" id="f-priorite"><option value="">Toutes priorités</option></select>
      <select class="filter" id="f-type"><option value="">Tous types</option></select>
      <select class="filter" id="f-module"><option value="">Tous modules</option></select>
      <button type="button" class="btn ghost small" id="btn-sous" title="Afficher ou masquer les sous-tâches dans le board et la liste">Sous-tâches affichées</button>
      <button type="button" class="btn ghost small" id="btn-reset" onclick="resetFiltres()">Réinitialiser</button>
    </div>

    <div id="view-kanban"><div class="board" id="board"></div></div>
    <div id="view-liste" style="display:none">
      <div class="table-wrap">
        <table>
          <thead><tr id="liste-head"></tr></thead>
          <tbody id="liste-body"></tbody>
        </table>
      </div>
    </div>
  </main>
</div>

<div id="drawer-root"></div>
<div id="modal-root"></div>

<script>
// ══════════════════════════════════════════════════════════════════
// MyTâches — état central, rendu, API
// Convention api() : retourne le JSON parsé, throw sur HTTP != 2xx.
// ══════════════════════════════════════════════════════════════════
const USER_ROLE = "__USER_ROLE__";

const S = {
  meta: null,
  taches: [],
  stats: {par_statut:{}, en_retard:0, non_assignees:0},
  view: 'kanban',
  detail: null,          // objet complet de la tâche ouverte
  detailTab: 'detail',
  filtres: {q:'', assigne:'', priorite:'', type:'', module:'', rapide:''},
  sousTaches: true,     // les sous-tâches apparaissent aussi comme cartes / lignes
  tri: {champ:'ordre', sens:'asc'},
  drag: null,
  me: null,
};

const ICO_SUN = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>';
const ICO_MOON = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>';

function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function toast(msg,type){const t=document.createElement('div');t.className='toast'+(type==='err'?' err':'');t.textContent=msg;document.body.appendChild(t);setTimeout(()=>t.remove(),3400);}
async function api(url,opts){
  opts=opts||{};opts.credentials='include';
  const r=await fetch(url,opts);
  if(!r.ok){let m='Erreur';try{const j=await r.json();m=j.detail||j.message||m;}catch(e){}throw new Error(m);}
  return r.json();
}
function jpost(url,body,method){
  return api(url,{method:method||'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body||{})});
}

// ── Référentiels : jamais de valeur en dur, tout vient de /api/taches/meta ──
function statutDef(code){return (S.meta&&S.meta.statuts||[]).find(s=>s.code===code)||{code:code,label:code,couleur:'muted',final:false};}
function prioriteDef(code){return (S.meta&&S.meta.priorites||[]).find(p=>p.code===code)||{code:code,label:code,couleur:'muted'};}
function typeLabel(code){const t=(S.meta&&S.meta.types||[]).find(x=>x.code===code);return t?t.label:(code||'');}
function moduleLabel(code){const m=(S.meta&&S.meta.modules||[]).find(x=>x.code===code);return m?m.label:(code||'');}
function statutsFinaux(){return (S.meta&&S.meta.statuts||[]).filter(s=>s.final).map(s=>s.code);}
function couleurVar(c){return c==='muted'?'var(--muted)':'var('+'--'+c+')';}

// ── Formats ──
const MOIS_COURT=['janv.','févr.','mars','avr.','mai','juin','juil.','août','sept.','oct.','nov.','déc.'];
function fmtDate(s){if(!s)return '';const d=new Date(String(s).substr(0,10));if(isNaN(d))return s;return d.getDate()+' '+MOIS_COURT[d.getMonth()]+' '+d.getFullYear();}
function fmtDateTime(s){
  if(!s)return '';const d=new Date(s);if(isNaN(d))return s;
  return d.getDate()+' '+MOIS_COURT[d.getMonth()]+' '+String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0');
}
function joursRestants(iso){
  if(!iso)return null;
  const d=new Date(String(iso).substr(0,10));if(isNaN(d))return null;
  const auj=new Date();auj.setHours(0,0,0,0);d.setHours(0,0,0,0);
  return Math.round((d-auj)/86400000);
}
function initiales(nom){
  const p=String(nom||'').trim().split(/\s+/).filter(Boolean);
  if(!p.length)return '?';
  if(p.length===1)return p[0].slice(0,2).toUpperCase();
  return (p[0][0]+p[p.length-1][0]).toUpperCase();
}
function avatarHtml(nom,url,titre){
  if(!nom)return '<span class="avatar none" title="Non assigné">—</span>';
  const t=esc(titre||nom);
  if(url)return '<span class="avatar" title="'+t+'"><img src="'+esc(url)+'" alt=""></span>';
  return '<span class="avatar" title="'+t+'">'+esc(initiales(nom))+'</span>';
}
function fmtTaille(o){
  const n=Number(o)||0;
  if(n<1024)return n+' o';
  if(n<1048576)return Math.round(n/1024)+' Ko';
  return (n/1048576).toFixed(1)+' Mo';
}
function fmtH(h){const n=Number(h)||0;return n?(Number.isInteger(n)?n:n.toFixed(1))+' h':'';}

// ── Shell ──
function getPrefs(){return window.MySifaTheme?MySifaTheme.loadPrefs():{mode:'dark'};}
function syncThemeBtn(){
  const isLight=getPrefs().mode==='light';
  const i=document.getElementById('theme-ico');const l=document.getElementById('theme-label');
  if(i)i.innerHTML=isLight?ICO_SUN:ICO_MOON;
  if(l)l.textContent=isLight?'Mode sombre':'Mode clair';
}
function toggleSidebar(){document.body.classList.toggle('sb-open');}
function closeSidebar(){document.body.classList.remove('sb-open');}

const VIEW_META={
  kanban:{titre:'Kanban',sub:"Ce que l'équipe doit faire, en cours et terminé.",guide:'taches-kanban'},
  liste:{titre:'Liste',sub:'Toutes les tâches actives, filtrables et triables.',guide:'taches-liste'},
  archives:{titre:'Archives',sub:'Tâches archivées — conservées pour l’historique.',guide:'taches-liste'},
};
const VALID_VIEWS=['kanban','liste','archives'];
function readView(){
  try{const h=(location.hash||'').replace(/^#/,'').trim();if(VALID_VIEWS.indexOf(h)!==-1)return h;}catch(e){}
  return 'kanban';
}
function showView(v,opts){
  if(VALID_VIEWS.indexOf(v)===-1)v='kanban';
  S.view=v;
  VALID_VIEWS.forEach(id=>{const n=document.getElementById('nav-'+id);if(n)n.classList.toggle('active',id===v);});
  document.getElementById('view-kanban').style.display=(v==='kanban')?'':'none';
  document.getElementById('view-liste').style.display=(v==='kanban')?'none':'';
  const m=VIEW_META[v];
  document.getElementById('page-title').textContent=m.titre;
  document.getElementById('page-sub').textContent=m.sub;
  const ms=document.getElementById('mobile-sub');if(ms)ms.textContent=m.titre;
  syncGuideBtn();
  closeSidebar();
  if(!(opts&&opts.silent)){try{if(location.hash!=='#'+v)history.replaceState(null,'','#'+v);}catch(e){}}
  chargerTaches();
}

// ══════════════════════════════════════════════════════════════════
// Chargement
// ══════════════════════════════════════════════════════════════════
function remplirFiltres(){
  const fa=document.getElementById('f-assigne');
  fa.innerHTML='<option value="">Tout le monde</option><option value="0">Non assignées</option>'+
    (S.meta.users||[]).map(u=>'<option value="'+u.id+'">'+esc(u.nom||'')+'</option>').join('');
  document.getElementById('f-priorite').innerHTML='<option value="">Toutes priorités</option>'+
    (S.meta.priorites||[]).map(p=>'<option value="'+esc(p.code)+'">'+esc(p.label)+'</option>').join('');
  document.getElementById('f-type').innerHTML='<option value="">Tous types</option>'+
    (S.meta.types||[]).map(t=>'<option value="'+esc(t.code)+'">'+esc(t.label)+'</option>').join('');
  document.getElementById('f-module').innerHTML='<option value="">Tous modules</option>'+
    (S.meta.modules||[]).map(m=>'<option value="'+esc(m.code)+'">'+esc(m.label)+'</option>').join('');
}

function queryFiltres(){
  const p=new URLSearchParams();
  const f=S.filtres;
  if(f.q)p.set('q',f.q);
  if(f.assigne&&f.assigne!=='0')p.set('assigne',f.assigne);
  if(f.priorite)p.set('priorite',f.priorite);
  if(f.type)p.set('type',f.type);
  if(f.module)p.set('module',f.module);
  if(S.view==='archives')p.set('archivees','1');
  return p.toString();
}

async function chargerTaches(){
  try{
    const j=await api('/api/taches?'+queryFiltres());
    S.taches=j.taches||[];
    // « Non assignées » et les raccourcis de compteur se filtrent côté client :
    // ils ne changent pas la requête, seulement la sélection affichée.
    render();
  }catch(e){
    toast(e.message,'err');
    const b=document.getElementById('board');
    if(b)b.innerHTML='<div class="empty">Erreur de chargement : '+esc(e.message)+'</div>';
  }
}

async function chargerStats(){
  try{S.stats=await api('/api/taches/stats');renderStats();}catch(e){}
}

function tachesVisibles(){
  let list=S.taches.slice();
  const f=S.filtres;
  if(!S.sousTaches)list=list.filter(t=>!t.parent_id);
  if(f.assigne==='0')list=list.filter(t=>!t.assigne_user_id);
  if(f.rapide==='retard'){
    const finaux=statutsFinaux();
    list=list.filter(t=>t.echeance&&joursRestants(t.echeance)<0&&finaux.indexOf(t.statut)===-1);
  }else if(f.rapide==='non_assignees'){
    list=list.filter(t=>!t.assigne_user_id);
  }else if(f.rapide&&f.rapide.indexOf('statut:')===0){
    const code=f.rapide.slice(7);
    list=list.filter(t=>t.statut===code);
  }
  return list;
}

// ══════════════════════════════════════════════════════════════════
// Rendu
// ══════════════════════════════════════════════════════════════════
function render(){
  document.getElementById('badge-total').textContent=String(S.taches.length);
  if(S.view==='kanban')renderKanban();
  else renderListe();
}

function renderStats(){
  if(!S.meta)return;
  const row=document.getElementById('stats-row');
  const parts=[];
  (S.meta.statuts||[]).forEach(st=>{
    const n=S.stats.par_statut[st.code]||0;
    const on=S.filtres.rapide==='statut:'+st.code;
    parts.push('<div class="stat'+(on?' active':'')+'" data-rapide="statut:'+esc(st.code)+'">'+
      '<span class="col-dot" style="background:'+couleurVar(st.couleur)+'"></span>'+
      esc(st.label)+' <b>'+n+'</b></div>');
  });
  if(S.stats.en_retard>0){
    const on=S.filtres.rapide==='retard';
    parts.push('<div class="stat alert'+(on?' active':'')+'" data-rapide="retard">En retard <b>'+S.stats.en_retard+'</b></div>');
  }
  if(S.stats.non_assignees>0){
    const on=S.filtres.rapide==='non_assignees';
    parts.push('<div class="stat'+(on?' active':'')+'" data-rapide="non_assignees">Non assignées <b>'+S.stats.non_assignees+'</b></div>');
  }
  row.innerHTML=parts.join('');
  row.querySelectorAll('.stat').forEach(el=>{
    el.onclick=()=>{
      const v=el.getAttribute('data-rapide');
      S.filtres.rapide=(S.filtres.rapide===v)?'':v;
      renderStats();render();
    };
  });
}

function carteHtml(t){
  const prio=prioriteDef(t.priorite);
  const jr=joursRestants(t.echeance);
  const finaux=statutsFinaux();
  const clos=finaux.indexOf(t.statut)!==-1;
  let dueCls='';
  if(!clos&&jr!==null){if(jr<0)dueCls=' late';else if(jr<=2)dueCls=' soon';}
  const tags=[];
  if(t.priorite&&t.priorite!=='normale')tags.push('<span class="tag '+esc(prio.couleur)+'">'+esc(prio.label)+'</span>');
  if(t.type)tags.push('<span class="tag">'+esc(typeLabel(t.type))+'</span>');
  if(t.module)tags.push('<span class="tag muted">'+esc(moduleLabel(t.module))+'</span>');

  const metas=[];
  if(t.echeance)metas.push('<span class="mi due'+dueCls+'"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>'+esc(fmtDate(t.echeance))+'</span>');
  if(t.nb_commentaires)metas.push('<span class="mi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 11.5a8.4 8.4 0 0 1-9 8.4 8.5 8.5 0 0 1-3.8-.9L3 21l1.9-5.2A8.4 8.4 0 0 1 12 3a8.4 8.4 0 0 1 9 8.5z"/></svg>'+t.nb_commentaires+'</span>');
  if(t.nb_fichiers)metas.push('<span class="mi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21.4 11.05 12.25 20.2a5.5 5.5 0 0 1-7.78-7.78l9.19-9.19a3.67 3.67 0 0 1 5.18 5.18l-9.2 9.19a1.83 1.83 0 0 1-2.59-2.59l8.49-8.48"/></svg>'+t.nb_fichiers+'</span>');
  if(t.nb_sous_taches)metas.push('<span class="mi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 5h6M3 12h10M3 19h6"/><path d="M17 8v11a2 2 0 0 0 2 2h2"/></svg>'+t.nb_sous_taches_faites+'/'+t.nb_sous_taches+'</span>');
  if(t.estimation_h)metas.push('<span class="mi" title="Estimation"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15 14"/></svg>'+esc(fmtH(t.estimation_h))+'</span>');

  let prog='';
  if(t.nb_checklist>0){
    const pct=Math.round(100*t.nb_checklist_faits/t.nb_checklist);
    prog='<div class="progress" title="Checklist '+t.nb_checklist_faits+'/'+t.nb_checklist+'"><i style="width:'+pct+'%"></i></div>';
  }

  return '<div class="tcard prio-'+esc(t.priorite||'normale')+'" draggable="true" data-id="'+t.id+'">'+
    (tags.length?'<div class="tcard-top">'+tags.join('')+'</div>':'')+
    '<div class="tcard-title">'+esc(t.titre)+'</div>'+
    (t.parent_titre?'<div style="font-size:10.5px;color:var(--muted);margin:-4px 0 8px">↳ '+esc(t.parent_titre)+'</div>':'')+
    '<div class="tcard-foot">'+avatarHtml(t.assigne_nom,t.assigne_avatar)+metas.join('')+'</div>'+
    prog+
  '</div>';
}

function renderKanban(){
  const board=document.getElementById('board');
  if(!S.meta){board.innerHTML='<div class="empty">Chargement…</div>';return;}
  const list=tachesVisibles();
  board.innerHTML=(S.meta.statuts||[]).map(st=>{
    const items=list.filter(t=>t.statut===st.code);
    return '<section class="col" data-statut="'+esc(st.code)+'">'+
      '<div class="col-head">'+
        '<span class="col-dot" style="background:'+couleurVar(st.couleur)+'"></span>'+
        '<span class="col-title">'+esc(st.label)+'</span>'+
        '<span class="col-count">'+items.length+'</span>'+
      '</div>'+
      '<div class="col-body" data-statut="'+esc(st.code)+'">'+
        (items.length?items.map(carteHtml).join(''):'<div style="font-size:11.5px;color:var(--muted);text-align:center;padding:14px 6px">Aucune tâche</div>')+
      '</div>'+
      '<button type="button" class="col-add" data-add="'+esc(st.code)+'">+ Ajouter une tâche</button>'+
    '</section>';
  }).join('');

  board.querySelectorAll('.tcard').forEach(c=>{
    c.addEventListener('click',()=>openDetail(Number(c.dataset.id)));
    c.addEventListener('dragstart',e=>{
      S.drag=Number(c.dataset.id);
      c.classList.add('dragging');
      try{e.dataTransfer.effectAllowed='move';e.dataTransfer.setData('text/plain',c.dataset.id);}catch(err){}
    });
    c.addEventListener('dragend',()=>{c.classList.remove('dragging');S.drag=null;
      board.querySelectorAll('.col').forEach(col=>col.classList.remove('drop'));});
  });
  board.querySelectorAll('.col-add').forEach(b=>{
    b.addEventListener('click',()=>openTacheModal(null,{statut:b.dataset.add}));
  });
  board.querySelectorAll('.col-body').forEach(zone=>{
    zone.addEventListener('dragover',e=>{
      e.preventDefault();
      try{e.dataTransfer.dropEffect='move';}catch(err){}
      zone.closest('.col').classList.add('drop');
    });
    zone.addEventListener('dragleave',e=>{
      if(!zone.contains(e.relatedTarget))zone.closest('.col').classList.remove('drop');
    });
    zone.addEventListener('drop',e=>{
      e.preventDefault();
      zone.closest('.col').classList.remove('drop');
      if(!S.drag)return;
      const voisins=[...zone.querySelectorAll('.tcard')].filter(c=>Number(c.dataset.id)!==S.drag);
      let apres=null,avant=null;
      for(const c of voisins){
        const r=c.getBoundingClientRect();
        if(e.clientY>r.top+r.height/2)apres=Number(c.dataset.id);
        else{avant=Number(c.dataset.id);break;}
      }
      deplacer(S.drag,zone.dataset.statut,apres,avant);
    });
  });
}

async function deplacer(id,statut,apres_id,avant_id){
  try{
    await jpost('/api/taches/'+id+'/move',{statut:statut,apres_id:apres_id,avant_id:avant_id});
    await Promise.all([chargerTaches(),chargerStats()]);
    if(S.detail&&S.detail.tache&&S.detail.tache.id===id)openDetail(id,{silent:true});
  }catch(e){toast(e.message,'err');chargerTaches();}
}

const COLONNES_LISTE=[
  {champ:'titre',label:'Tâche'},
  {champ:'statut',label:'Statut'},
  {champ:'priorite',label:'Priorité'},
  {champ:'assigne_nom',label:'Assigné'},
  {champ:'module',label:'Module'},
  {champ:'echeance',label:'Échéance'},
  {champ:'temps_passe_h',label:'Temps'},
];

function renderListe(){
  const head=document.getElementById('liste-head');
  head.innerHTML=COLONNES_LISTE.map(c=>{
    const on=S.tri.champ===c.champ;
    return '<th data-champ="'+c.champ+'"'+(on?' class="sorted"':'')+'>'+esc(c.label)+
      '<span class="sort">'+(on?(S.tri.sens==='asc'?'↑':'↓'):'↕')+'</span></th>';
  }).join('');
  head.querySelectorAll('th').forEach(th=>{
    th.onclick=()=>{
      const c=th.dataset.champ;
      if(S.tri.champ===c)S.tri.sens=(S.tri.sens==='asc'?'desc':'asc');
      else{S.tri.champ=c;S.tri.sens='asc';}
      renderListe();
    };
  });

  const list=tachesVisibles().slice().sort((a,b)=>{
    const c=S.tri.champ;
    let va=a[c],vb=b[c];
    if(c==='priorite'){
      const poids=o=>{const p=(S.meta.priorites||[]).find(x=>x.code===o);return p?p.poids:0;};
      va=poids(a.priorite);vb=poids(b.priorite);
    }
    if(c==='statut'){
      const rang=o=>(S.meta.statuts||[]).findIndex(x=>x.code===o);
      va=rang(a.statut);vb=rang(b.statut);
    }
    if(va==null)va='';if(vb==null)vb='';
    let r;
    if(typeof va==='number'&&typeof vb==='number')r=va-vb;
    else r=String(va).localeCompare(String(vb),'fr',{numeric:true});
    return S.tri.sens==='asc'?r:-r;
  });

  const body=document.getElementById('liste-body');
  if(!list.length){
    body.innerHTML='<tr><td colspan="'+COLONNES_LISTE.length+'"><div class="empty"><b>Aucune tâche</b>'+
      (S.view==='archives'?'Rien d’archivé pour l’instant.':'Créez la première avec « Nouvelle tâche ».')+'</div></td></tr>';
    return;
  }
  const finaux=statutsFinaux();
  body.innerHTML=list.map(t=>{
    const st=statutDef(t.statut),prio=prioriteDef(t.priorite);
    const jr=joursRestants(t.echeance);
    const clos=finaux.indexOf(t.statut)!==-1;
    let dueCls='';
    if(!clos&&jr!==null){if(jr<0)dueCls=' late';else if(jr<=2)dueCls=' soon';}
    const sousTitre=[];
    if(t.parent_titre)sousTitre.push('↳ '+t.parent_titre);
    if(t.type)sousTitre.push(typeLabel(t.type));
    if(t.nb_checklist)sousTitre.push('checklist '+t.nb_checklist_faits+'/'+t.nb_checklist);
    return '<tr data-id="'+t.id+'">'+
      '<td class="t-titre">'+esc(t.titre)+(sousTitre.length?'<span class="sub">'+esc(sousTitre.join(' · '))+'</span>':'')+'</td>'+
      '<td><span class="tag '+esc(st.couleur)+'">'+esc(st.label)+'</span></td>'+
      '<td><span class="tag '+esc(prio.couleur)+'">'+esc(prio.label)+'</span></td>'+
      '<td>'+(t.assigne_nom?('<span style="display:inline-flex;align-items:center;gap:7px">'+avatarHtml(t.assigne_nom,t.assigne_avatar)+esc(t.assigne_nom)+'</span>'):'<span style="color:var(--muted)">—</span>')+'</td>'+
      '<td>'+esc(t.module?moduleLabel(t.module):'—')+'</td>'+
      '<td class="due'+dueCls+'">'+(t.echeance?esc(fmtDate(t.echeance)):'—')+'</td>'+
      '<td>'+(t.temps_passe_h?esc(fmtH(t.temps_passe_h)):(t.estimation_h?'0 h':'—'))+(t.estimation_h?'<span style="color:var(--muted)"> / '+esc(fmtH(t.estimation_h))+'</span>':'')+'</td>'+
    '</tr>';
  }).join('');
  body.querySelectorAll('tr[data-id]').forEach(tr=>{
    tr.onclick=()=>openDetail(Number(tr.dataset.id));
  });
}

// ══════════════════════════════════════════════════════════════════
// Panneau de détail
// ══════════════════════════════════════════════════════════════════
async function openDetail(id,opts){
  try{
    const j=await api('/api/taches/'+id);
    S.detail=j;
    if(!(opts&&opts.silent))S.detailTab='detail';
    renderDrawer();
  }catch(e){toast(e.message,'err');}
}
function closeDetail(){
  S.detail=null;
  document.getElementById('drawer-root').innerHTML='';
  document.removeEventListener('keydown',onDrawerKey);
}
function onDrawerKey(e){
  if(e.key!=='Escape')return;
  if(document.getElementById('modal-root').firstElementChild)return;
  closeDetail();
}

function renderDrawer(){
  const root=document.getElementById('drawer-root');
  if(!S.detail){root.innerHTML='';return;}
  const d=S.detail,t=d.tache;
  const st=statutDef(t.statut);

  const onglets=[
    {id:'detail',label:'Détail',n:null},
    {id:'commentaires',label:'Commentaires',n:d.commentaires.length},
    {id:'fichiers',label:'Fichiers',n:d.fichiers.length},
    {id:'activite',label:'Activité',n:null},
  ];

  root.innerHTML=
  '<div class="drawer-back" id="dr-back"></div>'+
  '<aside class="drawer" role="dialog" aria-label="Détail de la tâche">'+
    '<div class="dr-head">'+
      '<div class="dr-head-main">'+
        '<div class="dr-title" id="dr-titre" title="Cliquer pour renommer">'+esc(t.titre)+'</div>'+
        '<div class="dr-meta">'+
          '<span class="tag '+esc(st.couleur)+'">'+esc(st.label)+'</span> · '+
          'Créée le '+esc(fmtDateTime(t.created_at))+(t.createur_nom?' par '+esc(t.createur_nom):'')+
          (t.archived_at?' · <span class="tag warn">Archivée</span>':'')+
        '</div>'+
      '</div>'+
      '<button type="button" class="dr-close" id="dr-close" aria-label="Fermer">×</button>'+
    '</div>'+
    '<div class="dr-tabs">'+
      onglets.map(o=>'<button type="button" class="dr-tab'+(S.detailTab===o.id?' active':'')+'" data-tab="'+o.id+'">'+
        esc(o.label)+(o.n?'<span class="n">'+o.n+'</span>':'')+'</button>').join('')+
    '</div>'+
    '<div class="dr-body">'+
      '<div class="dr-pane'+(S.detailTab==='detail'?' active':'')+'" id="pane-detail">'+paneDetail(d)+'</div>'+
      '<div class="dr-pane'+(S.detailTab==='commentaires'?' active':'')+'" id="pane-commentaires">'+paneCommentaires(d)+'</div>'+
      '<div class="dr-pane'+(S.detailTab==='fichiers'?' active':'')+'" id="pane-fichiers">'+paneFichiers(d)+'</div>'+
      '<div class="dr-pane'+(S.detailTab==='activite'?' active':'')+'" id="pane-activite">'+paneActivite(d)+'</div>'+
    '</div>'+
  '</aside>';

  root.querySelector('#dr-back').onclick=closeDetail;
  root.querySelector('#dr-close').onclick=closeDetail;
  root.querySelectorAll('.dr-tab').forEach(b=>{
    b.onclick=()=>{S.detailTab=b.dataset.tab;renderDrawer();};
  });
  document.addEventListener('keydown',onDrawerKey);
  brancherDetail();
}

function paneDetail(d){
  const t=d.tache;
  const opt=(items,val,vide)=>(vide?'<option value="">'+esc(vide)+'</option>':'')+
    items.map(i=>'<option value="'+esc(i.code!=null?i.code:i.id)+'"'+
      (String(val||'')===String(i.code!=null?i.code:i.id)?' selected':'')+'>'+esc(i.label||i.nom)+'</option>').join('');

  const chk=d.checklist;
  const nbFaits=chk.filter(c=>c.fait).length;

  return ''+
  '<div class="fgrid">'+
    '<div class="field"><label>Statut</label><select id="d-statut">'+opt(S.meta.statuts,t.statut)+'</select></div>'+
    '<div class="field"><label>Priorité</label><select id="d-priorite">'+opt(S.meta.priorites,t.priorite)+'</select></div>'+
    '<div class="field"><label>Assigné à</label><select id="d-assigne"><option value="">Non assigné</option>'+
      (S.meta.users||[]).map(u=>'<option value="'+u.id+'"'+(String(t.assigne_user_id||'')===String(u.id)?' selected':'')+'>'+esc(u.nom||'')+'</option>').join('')+
    '</select></div>'+
    '<div class="field"><label>Échéance</label><input type="date" id="d-echeance" value="'+esc(t.echeance||'')+'"></div>'+
    '<div class="field"><label>Type</label><select id="d-type">'+opt(S.meta.types,t.type)+'</select></div>'+
    '<div class="field"><label>Module</label><select id="d-module">'+opt(S.meta.modules,t.module,'Aucun')+'</select></div>'+
    '<div class="field"><label>Estimation (h)</label><input type="number" step="0.25" min="0" id="d-estimation" value="'+esc(t.estimation_h!=null?t.estimation_h:'')+'"></div>'+
    '<div class="field"><label>Temps passé</label>'+
      '<div style="display:flex;gap:6px">'+
        '<input type="number" step="0.25" min="0" id="d-temps-ajout" placeholder="+ heures">'+
        '<button type="button" class="btn ghost small" id="d-temps-btn" style="white-space:nowrap">Ajouter</button>'+
      '</div>'+
      '<div style="font-size:11px;color:var(--muted);margin-top:5px">Cumul : <b style="color:var(--text2)">'+esc(fmtH(t.temps_passe_h)||'0 h')+'</b>'+
      (t.estimation_h?' sur '+esc(fmtH(t.estimation_h))+' estimées':'')+'</div>'+
    '</div>'+
    '<div class="field full"><label>Description</label><textarea id="d-description" placeholder="Contexte, attendu, critères d’acceptation…">'+esc(t.description||'')+'</textarea></div>'+
  '</div>'+

  '<div class="sec">'+
    '<div class="sec-hd"><h3>Checklist'+(chk.length?' · '+nbFaits+'/'+chk.length:'')+'</h3></div>'+
    (chk.length?chk.map(c=>
      '<div class="chk'+(c.fait?' done':'')+'" data-chk="'+c.id+'">'+
        '<input type="checkbox"'+(c.fait?' checked':'')+'>'+
        '<span class="lbl">'+esc(c.libelle)+'</span>'+
        (c.fait&&c.fait_par_nom?'<span style="font-size:10px;color:var(--muted)">'+esc(c.fait_par_nom)+'</span>':'')+
        '<button type="button" class="x" title="Supprimer">×</button>'+
      '</div>').join(''):'<div style="font-size:12px;color:var(--muted);padding:2px 0 4px">Aucun point de contrôle.</div>')+
    '<div class="inline-add"><input type="text" id="chk-new" placeholder="Ajouter un point de contrôle…"><button type="button" class="btn ghost small" id="chk-add">Ajouter</button></div>'+
  '</div>'+

  (t.parent_id?'':
  '<div class="sec">'+
    '<div class="sec-hd"><h3>Sous-tâches'+(d.sous_taches.length?' · '+d.sous_taches.length:'')+'</h3></div>'+
    (d.sous_taches.length?d.sous_taches.map(s=>{
      const sst=statutDef(s.statut);
      const clos=statutsFinaux().indexOf(s.statut)!==-1;
      return '<div class="sub-item'+(clos?' done':'')+'" data-sous="'+s.id+'">'+
        '<span class="tag '+esc(sst.couleur)+'">'+esc(sst.label)+'</span>'+
        '<span class="st">'+esc(s.titre)+'</span>'+
        (s.assigne_nom?avatarHtml(s.assigne_nom,null):'')+
      '</div>';
    }).join(''):'<div style="font-size:12px;color:var(--muted);padding:2px 0 4px">Aucune sous-tâche.</div>')+
    '<div class="inline-add"><input type="text" id="sous-new" placeholder="Ajouter une sous-tâche…"><button type="button" class="btn ghost small" id="sous-add">Ajouter</button></div>'+
  '</div>')+

  '<div style="display:flex;gap:8px;flex-wrap:wrap;padding-top:6px;border-top:1px solid var(--border)">'+
    '<button type="button" class="btn ghost small" id="d-archive">'+(t.archived_at?'Désarchiver':'Archiver')+'</button>'+
    '<button type="button" class="btn danger small" id="d-delete" style="margin-left:auto">Supprimer</button>'+
  '</div>';
}

function paneCommentaires(d){
  return ''+
  '<div id="cmt-list">'+
    (d.commentaires.length?d.commentaires.map(c=>
      '<div class="cmt">'+avatarHtml(c.auteur_nom,c.auteur_avatar)+
        '<div class="cmt-body">'+
          '<div class="cmt-hd"><span class="cmt-auteur">'+esc(c.auteur_nom||'—')+'</span>'+
            '<span class="cmt-date">'+esc(fmtDateTime(c.created_at))+'</span>'+
            '<button type="button" class="cmt-del" data-cmt="'+c.id+'">Supprimer</button></div>'+
          '<div class="cmt-msg">'+esc(c.message)+'</div>'+
        '</div>'+
      '</div>').join(''):'<div class="empty"><b>Aucun commentaire</b>Ouvrez la discussion ci-dessous.</div>')+
  '</div>'+
  '<div class="cmt-form">'+
    '<textarea id="cmt-new" placeholder="Écrire un commentaire… (Ctrl+Entrée pour envoyer)"></textarea>'+
    '<div style="display:flex;justify-content:flex-end;margin-top:8px"><button type="button" class="btn small" id="cmt-send">Commenter</button></div>'+
  '</div>';
}

const IMG_RE=/\.(png|jpe?g|gif|webp|bmp|svg)$/i;
function paneFichiers(d){
  return ''+
  '<div class="drop-zone" id="fic-drop">'+
    '<div style="font-weight:600;margin-bottom:4px">Déposer un fichier de contexte</div>'+
    '<div style="font-size:11px">ou cliquer pour choisir — '+(S.meta.max_file_mb||25)+' Mo maximum</div>'+
    '<input type="file" id="fic-input" style="display:none">'+
  '</div>'+
  '<div style="margin-top:14px">'+
    (d.fichiers.length?d.fichiers.map(f=>
      '<div class="file-item">'+
        '<div class="file-ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></div>'+
        '<div class="file-info"><div class="file-name">'+esc(f.nom)+'</div>'+
          '<div class="file-meta">'+esc(fmtTaille(f.taille_bytes))+' · '+esc(f.uploaded_nom||'')+' · '+esc(fmtDateTime(f.created_at))+'</div></div>'+
        '<button type="button" class="btn ghost small" data-preview="'+f.id+'" data-nom="'+esc(f.nom)+'">Ouvrir</button>'+
        '<button type="button" class="btn ghost small" data-fic-del="'+f.id+'">×</button>'+
      '</div>').join(''):'<div class="empty"><b>Aucun fichier</b>Maquettes, exports, captures : tout ce qui aide à comprendre la demande.</div>')+
  '</div>';
}

function paneActivite(d){
  if(!d.activite.length)return '<div class="empty"><b>Aucune activité</b>Les changements apparaîtront ici.</div>';
  return d.activite.map(a=>{
    let txt;
    if(a.action==='creation')txt='<b>'+esc(a.auteur_nom||'—')+'</b> a créé la tâche';
    else if(a.action==='commentaire')txt='<b>'+esc(a.auteur_nom||'—')+'</b> a commenté';
    else if(a.action==='commentaire_supprime')txt='<b>'+esc(a.auteur_nom||'—')+'</b> a supprimé un commentaire';
    else if(a.action==='fichier')txt='<b>'+esc(a.auteur_nom||'—')+'</b> a ajouté '+esc(a.apres||'un fichier');
    else if(a.action==='fichier_supprime')txt='<b>'+esc(a.auteur_nom||'—')+'</b> a retiré '+esc(a.avant||'un fichier');
    else if(a.action==='archivage')txt='<b>'+esc(a.auteur_nom||'—')+'</b> a archivé la tâche';
    else if(a.action==='desarchivage')txt='<b>'+esc(a.auteur_nom||'—')+'</b> a désarchivé la tâche';
    else if(a.action==='suppression')txt='<b>'+esc(a.auteur_nom||'—')+'</b> a supprimé la tâche';
    else if(a.action==='statut')txt='<b>'+esc(a.auteur_nom||'—')+'</b> : statut '+esc(statutDef(a.avant).label)+' → '+esc(statutDef(a.apres).label);
    else if(a.action==='temps')txt='<b>'+esc(a.auteur_nom||'—')+'</b> a pointé du temps ('+esc(a.apres||'')+' h)';
    else if(a.action&&a.action.indexOf('checklist')===0)txt='<b>'+esc(a.auteur_nom||'—')+'</b> · checklist : '+esc(a.avant||a.apres||'');
    else txt='<b>'+esc(a.auteur_nom||'—')+'</b> a modifié '+esc(a.champ||'')+
      (a.avant?' — <span style="color:var(--muted)">'+esc(a.avant)+'</span> →':' →')+' '+esc(a.apres||'vide');
    return '<div class="act"><span class="act-dot"></span><span>'+txt+'</span><span class="act-date">'+esc(fmtDateTime(a.created_at))+'</span></div>';
  }).join('');
}

// ── Interactions du panneau ──
function brancherDetail(){
  const d=S.detail;if(!d)return;
  const t=d.tache;
  const root=document.getElementById('drawer-root');

  async function patch(champ,valeur){
    try{
      const body={};body[champ]=valeur;
      await api('/api/taches/'+t.id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
      await Promise.all([chargerTaches(),chargerStats()]);
      await openDetail(t.id,{silent:true});
    }catch(e){toast(e.message,'err');}
  }

  const bind=(id,champ,transform)=>{
    const el=root.querySelector('#'+id);
    if(!el)return;
    el.addEventListener('change',()=>{
      let v=el.value;
      if(transform)v=transform(v);
      patch(champ,v);
    });
  };
  bind('d-statut','statut');
  bind('d-priorite','priorite');
  bind('d-type','type');
  bind('d-module','module',v=>v||null);
  bind('d-assigne','assigne_user_id',v=>v?Number(v):null);
  bind('d-echeance','echeance',v=>v||null);
  bind('d-estimation','estimation_h',v=>v===''?null:Number(v));

  const desc=root.querySelector('#d-description');
  if(desc){
    desc.addEventListener('blur',()=>{
      if((desc.value||'')===(t.description||''))return;
      patch('description',desc.value);
    });
  }

  // Titre éditable en place
  const titre=root.querySelector('#dr-titre');
  if(titre){
    titre.addEventListener('click',()=>{
      if(titre.querySelector('input'))return;
      const val=t.titre;
      titre.innerHTML='<input type="text" style="width:100%;background:var(--bg);border:1px solid var(--accent);border-radius:8px;padding:6px 9px;color:var(--text);font-size:15px;font-weight:700;font-family:inherit;outline:none">';
      const inp=titre.querySelector('input');
      inp.value=val;inp.focus();inp.select();
      const valider=()=>{
        const nv=(inp.value||'').trim();
        if(!nv||nv===val){renderDrawer();return;}
        patch('titre',nv);
      };
      inp.addEventListener('blur',valider);
      inp.addEventListener('keydown',e=>{
        if(e.key==='Enter'){e.preventDefault();inp.blur();}
        if(e.key==='Escape'){e.preventDefault();inp.value=val;renderDrawer();}
      });
    });
  }

  // Temps passé
  const tbtn=root.querySelector('#d-temps-btn');
  if(tbtn){
    tbtn.onclick=async()=>{
      const inp=root.querySelector('#d-temps-ajout');
      const h=Number(inp.value);
      if(!h||h<=0){toast('Temps invalide — valeur supérieure à 0 attendue.','err');return;}
      try{
        await jpost('/api/taches/'+t.id+'/temps',{heures:h});
        inp.value='';
        await Promise.all([chargerTaches(),openDetail(t.id,{silent:true})]);
        toast('Temps ajouté.');
      }catch(e){toast(e.message,'err');}
    };
  }

  // Checklist
  root.querySelectorAll('.chk').forEach(el=>{
    const id=Number(el.dataset.chk);
    const box=el.querySelector('input[type=checkbox]');
    box.onchange=async()=>{
      try{
        await api('/api/taches/checklist/'+id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({fait:box.checked})});
        await Promise.all([chargerTaches(),openDetail(t.id,{silent:true})]);
      }catch(e){toast(e.message,'err');box.checked=!box.checked;}
    };
    el.querySelector('.x').onclick=async()=>{
      try{
        await api('/api/taches/checklist/'+id,{method:'DELETE'});
        await Promise.all([chargerTaches(),openDetail(t.id,{silent:true})]);
      }catch(e){toast(e.message,'err');}
    };
  });
  const chkAdd=root.querySelector('#chk-add'),chkNew=root.querySelector('#chk-new');
  if(chkAdd){
    const envoyer=async()=>{
      const v=(chkNew.value||'').trim();
      if(!v)return;
      try{
        await jpost('/api/taches/'+t.id+'/checklist',{libelle:v});
        chkNew.value='';
        await Promise.all([chargerTaches(),openDetail(t.id,{silent:true})]);
        requestAnimationFrame(()=>{const n=document.getElementById('chk-new');if(n)n.focus();});
      }catch(e){toast(e.message,'err');}
    };
    chkAdd.onclick=envoyer;
    chkNew.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();envoyer();}});
  }

  // Sous-tâches
  root.querySelectorAll('.sub-item').forEach(el=>{
    el.onclick=()=>openDetail(Number(el.dataset.sous));
  });
  const sousAdd=root.querySelector('#sous-add'),sousNew=root.querySelector('#sous-new');
  if(sousAdd){
    const envoyer=async()=>{
      const v=(sousNew.value||'').trim();
      if(!v)return;
      try{
        await jpost('/api/taches',{titre:v,parent_id:t.id,statut:'a_faire',module:t.module,type:t.type});
        sousNew.value='';
        await Promise.all([chargerTaches(),chargerStats(),openDetail(t.id,{silent:true})]);
        requestAnimationFrame(()=>{const n=document.getElementById('sous-new');if(n)n.focus();});
      }catch(e){toast(e.message,'err');}
    };
    sousAdd.onclick=envoyer;
    sousNew.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();envoyer();}});
  }

  // Archiver / supprimer
  const arch=root.querySelector('#d-archive');
  if(arch)arch.onclick=async()=>{
    try{
      const j=await jpost('/api/taches/'+t.id+'/archive',{});
      toast(j.archivee?'Tâche archivée.':'Tâche désarchivée.');
      closeDetail();
      await Promise.all([chargerTaches(),chargerStats()]);
    }catch(e){toast(e.message,'err');}
  };
  const del=root.querySelector('#d-delete');
  if(del)del.onclick=()=>{
    confirmer('Supprimer la tâche « '+t.titre+' » ?','Ses sous-tâches, commentaires et fichiers seront également retirés.',async()=>{
      try{
        await api('/api/taches/'+t.id,{method:'DELETE'});
        toast('Tâche supprimée.');
        closeDetail();
        await Promise.all([chargerTaches(),chargerStats()]);
      }catch(e){toast(e.message,'err');}
    });
  };

  // Commentaires
  const send=root.querySelector('#cmt-send'),area=root.querySelector('#cmt-new');
  if(send){
    const envoyer=async()=>{
      const v=(area.value||'').trim();
      if(!v)return;
      send.disabled=true;
      try{
        await jpost('/api/taches/'+t.id+'/commentaires',{message:v});
        area.value='';
        await Promise.all([chargerTaches(),openDetail(t.id,{silent:true})]);
      }catch(e){toast(e.message,'err');}
      finally{send.disabled=false;}
    };
    send.onclick=envoyer;
    area.addEventListener('keydown',e=>{if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)){e.preventDefault();envoyer();}});
  }
  root.querySelectorAll('.cmt-del').forEach(b=>{
    b.onclick=()=>confirmer('Supprimer ce commentaire ?','',async()=>{
      try{
        await api('/api/taches/commentaires/'+b.dataset.cmt,{method:'DELETE'});
        await Promise.all([chargerTaches(),openDetail(t.id,{silent:true})]);
      }catch(e){toast(e.message,'err');}
    });
  });

  // Fichiers
  const drop=root.querySelector('#fic-drop'),input=root.querySelector('#fic-input');
  if(drop){
    drop.onclick=()=>input.click();
    input.onchange=()=>{if(input.files&&input.files[0])televerser(input.files[0]);};
    ['dragenter','dragover'].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.add('over');}));
    ['dragleave','drop'].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.remove('over');}));
    drop.addEventListener('drop',e=>{
      const f=e.dataTransfer&&e.dataTransfer.files&&e.dataTransfer.files[0];
      if(f)televerser(f);
    });
  }
  async function televerser(file){
    const fd=new FormData();fd.append('fichier',file);
    try{
      const r=await fetch('/api/taches/'+t.id+'/fichiers',{method:'POST',credentials:'include',body:fd});
      if(!r.ok){let m='Erreur';try{const j=await r.json();m=j.detail||m;}catch(e){}throw new Error(m);}
      toast('Fichier ajouté.');
      await Promise.all([chargerTaches(),openDetail(t.id,{silent:true})]);
    }catch(e){toast(e.message,'err');}
  }
  root.querySelectorAll('[data-preview]').forEach(b=>{
    b.onclick=()=>{
      const id=b.dataset.preview,nom=b.dataset.nom||'';
      window.open('/api/taches/fichiers/'+id+'/download?inline=1','_blank','noopener');
    };
  });
  root.querySelectorAll('[data-fic-del]').forEach(b=>{
    b.onclick=()=>confirmer('Retirer ce fichier ?','',async()=>{
      try{
        await api('/api/taches/fichiers/'+b.dataset.ficDel,{method:'DELETE'});
        await Promise.all([chargerTaches(),openDetail(t.id,{silent:true})]);
      }catch(e){toast(e.message,'err');}
    });
  });
}

// ══════════════════════════════════════════════════════════════════
// Modales
// ══════════════════════════════════════════════════════════════════
function fermerModal(){document.getElementById('modal-root').innerHTML='';}

function confirmer(titre,detail,onOui){
  const root=document.getElementById('modal-root');
  root.innerHTML='<div class="modal-back"><div class="modal" style="max-width:420px">'+
    '<h3>'+esc(titre)+'</h3>'+
    (detail?'<p style="font-size:13px;color:var(--text2);line-height:1.55;margin:0 0 4px">'+esc(detail)+'</p>':'')+
    '<div class="modal-actions"><button type="button" class="btn ghost" id="cf-non">Annuler</button>'+
    '<button type="button" class="btn danger" id="cf-oui">Confirmer</button></div>'+
  '</div></div>';
  root.querySelector('#cf-non').onclick=fermerModal;
  root.querySelector('#cf-oui').onclick=()=>{fermerModal();onOui();};
  root.querySelector('.modal-back').onclick=e=>{if(e.target===root.querySelector('.modal-back'))fermerModal();};
}

function openTacheModal(_ignored,defauts){
  defauts=defauts||{};
  const root=document.getElementById('modal-root');
  const optList=(items,val,vide)=>(vide?'<option value="">'+esc(vide)+'</option>':'')+
    items.map(i=>'<option value="'+esc(i.code)+'"'+(String(val||'')===String(i.code)?' selected':'')+'>'+esc(i.label)+'</option>').join('');
  const statutDefaut=defauts.statut||(S.meta.statuts[0]&&S.meta.statuts[0].code)||'backlog';

  root.innerHTML='<div class="modal-back"><div class="modal">'+
    '<h3>Nouvelle tâche</h3>'+
    '<form id="tache-form">'+
      '<div class="fgrid">'+
        '<div class="field full"><label>Titre</label><input type="text" id="n-titre" required maxlength="300" placeholder="Ex. Corriger le tri des OF dans le planning"></div>'+
        '<div class="field full"><label>Description</label><textarea id="n-description" placeholder="Contexte, comportement attendu, critères d’acceptation…"></textarea></div>'+
        '<div class="field"><label>Statut</label><select id="n-statut">'+optList(S.meta.statuts,statutDefaut)+'</select></div>'+
        '<div class="field"><label>Priorité</label><select id="n-priorite">'+optList(S.meta.priorites,'normale')+'</select></div>'+
        '<div class="field"><label>Type</label><select id="n-type">'+optList(S.meta.types,'evolution')+'</select></div>'+
        '<div class="field"><label>Module</label><select id="n-module">'+optList(S.meta.modules,'','Aucun')+'</select></div>'+
        '<div class="field"><label>Assigné à</label><select id="n-assigne"><option value="">Non assigné</option>'+
          (S.meta.users||[]).map(u=>'<option value="'+u.id+'">'+esc(u.nom||'')+'</option>').join('')+'</select></div>'+
        '<div class="field"><label>Échéance</label><input type="date" id="n-echeance"></div>'+
        '<div class="field"><label>Estimation (h)</label><input type="number" step="0.25" min="0" id="n-estimation" placeholder="ex. 3"></div>'+
      '</div>'+
      '<div class="modal-actions">'+
        '<button type="button" class="btn ghost" id="n-cancel">Annuler</button>'+
        '<button type="submit" class="btn">Créer la tâche</button>'+
      '</div>'+
    '</form>'+
  '</div></div>';

  root.querySelector('#n-cancel').onclick=fermerModal;
  root.querySelector('.modal-back').onclick=e=>{if(e.target===root.querySelector('.modal-back'))fermerModal();};
  requestAnimationFrame(()=>{const el=document.getElementById('n-titre');if(el)el.focus();});

  root.querySelector('#tache-form').addEventListener('submit',async e=>{
    e.preventDefault();
    const g=id=>{const el=document.getElementById(id);return el?el.value:'';};
    const titre=(g('n-titre')||'').trim();
    if(!titre){toast('Titre obligatoire.','err');return;}
    const body={
      titre:titre,
      description:(g('n-description')||'').trim()||null,
      statut:g('n-statut'),priorite:g('n-priorite'),type:g('n-type'),
      module:g('n-module')||null,
      assigne_user_id:g('n-assigne')?Number(g('n-assigne')):null,
      echeance:g('n-echeance')||null,
      estimation_h:g('n-estimation')?Number(g('n-estimation')):null,
    };
    try{
      const j=await jpost('/api/taches',body);
      fermerModal();
      toast('Tâche créée.');
      await Promise.all([chargerTaches(),chargerStats()]);
      openDetail(j.id);
    }catch(err){toast(err.message,'err');}
  });
}

// ══════════════════════════════════════════════════════════════════
// Filtres
// ══════════════════════════════════════════════════════════════════
let _debounce=null;
function brancherFiltres(){
  const q=document.getElementById('f-q');
  q.addEventListener('input',()=>{
    S.filtres.q=q.value.trim();
    clearTimeout(_debounce);
    _debounce=setTimeout(chargerTaches,220);
  });
  q.addEventListener('keydown',e=>{
    if(e.key==='Escape'){q.value='';S.filtres.q='';chargerTaches();}
  });
  [['f-assigne','assigne'],['f-priorite','priorite'],['f-type','type'],['f-module','module']].forEach(([id,champ])=>{
    const el=document.getElementById(id);
    el.addEventListener('change',()=>{
      S.filtres[champ]=el.value;
      el.classList.toggle('on',!!el.value);
      chargerTaches();
    });
  });
}
function brancherSousTaches(){
  const b=document.getElementById('btn-sous');
  if(!b)return;
  const sync=()=>{
    b.textContent=S.sousTaches?'Sous-tâches affichées':'Sous-tâches masquées';
    b.classList.toggle('ghost',S.sousTaches);
  };
  b.onclick=()=>{
    S.sousTaches=!S.sousTaches;
    try{localStorage.setItem('mysifa_taches_sous',S.sousTaches?'1':'0');}catch(e){}
    sync();render();
  };
  try{if(localStorage.getItem('mysifa_taches_sous')==='0')S.sousTaches=false;}catch(e){}
  sync();
}

function resetFiltres(){
  S.filtres={q:'',assigne:'',priorite:'',type:'',module:'',rapide:''};
  ['f-q','f-assigne','f-priorite','f-type','f-module'].forEach(id=>{
    const el=document.getElementById(id);if(el){el.value='';el.classList.remove('on');}
  });
  renderStats();
  chargerTaches();
}

// ══════════════════════════════════════════════════════════════════
// Guides in-app (moteur partagé mysifa_guides.js)
// ══════════════════════════════════════════════════════════════════
const TACHES_GUIDES = {
  'taches-kanban': { steps: [
    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="6" height="18" rx="1"/><rect x="10" y="3" width="6" height="12" rx="1"/><rect x="17" y="3" width="4" height="8" rx="1"/></svg>',
      title: 'Gestionnaire de tâches',
      body: '<p>Cette application suit <strong>ce que vous demandez à l’équipe de développement</strong> : une tâche par demande, de son arrivée en <span class="mguide-tag">Boîte à idées</span> jusqu’à <span class="mguide-tag">Terminé</span>. Elle est réservée au super administrateur.</p>',
      extra: '<div class="mguide-tasks"><div class="mguide-svc"><div class="mguide-svc-hd"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>Ce que vous avez à faire ici</div><ul class="mguide-svc-list"><li>Créer une tâche pour chaque demande, avec le contexte nécessaire.</li><li>Assigner la tâche à un développeur et poser une échéance.</li><li>Suivre l’avancement colonne par colonne, sans réunion.</li><li>Joindre les fichiers de contexte et commenter au fil de l’eau.</li></ul></div></div>'
    },
    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M5 9l-3 3 3 3"/><path d="M9 5l3-3 3 3"/><path d="M15 19l-3 3-3-3"/><path d="M19 9l3 3-3 3"/></svg>',
      title: 'Déplacer une tâche',
      body: '<p>Chaque colonne est un statut. <strong>Glissez une carte</strong> d’une colonne à l’autre pour la faire avancer — le statut, la date de démarrage et la date de clôture se mettent à jour seuls. À l’intérieur d’une colonne, la position que vous donnez à la carte est conservée.</p>',
      illu: '<svg viewBox="0 0 340 160" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI"><rect x="8" y="10" width="100" height="140" rx="10" fill="var(--card)" stroke="var(--border)"/><rect x="120" y="10" width="100" height="140" rx="10" fill="var(--card)" stroke="var(--accent)"/><rect x="232" y="10" width="100" height="140" rx="10" fill="var(--card)" stroke="var(--border)"/><text x="20" y="28" font-size="9" fill="var(--muted)" font-weight="700">À FAIRE</text><text x="132" y="28" font-size="9" fill="var(--accent)" font-weight="700">EN COURS</text><text x="244" y="28" font-size="9" fill="var(--muted)" font-weight="700">TERMINÉ</text><rect x="16" y="38" width="84" height="34" rx="7" fill="var(--bg)" stroke="var(--border)"/><text x="24" y="52" font-size="8" fill="var(--text2)">Tri des OF</text><rect x="24" y="58" width="30" height="7" rx="3" fill="var(--warn)" opacity=".5"/><rect x="128" y="38" width="84" height="34" rx="7" fill="var(--accent-bg)" stroke="var(--accent)" stroke-dasharray="4 3"/><text x="136" y="52" font-size="8" fill="var(--accent)" font-weight="700">Export PDF</text><rect x="136" y="58" width="42" height="7" rx="3" fill="var(--accent)" opacity=".6"/><path d="M104 55 L124 55" stroke="var(--accent)" stroke-width="2" marker-end="url(#a)"/><defs><marker id="a" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6z" fill="var(--accent)"/></marker></defs><rect x="240" y="38" width="84" height="34" rx="7" fill="var(--bg)" stroke="var(--border)"/><text x="248" y="52" font-size="8" fill="var(--muted)">Badge stock</text><rect x="248" y="58" width="26" height="7" rx="3" fill="var(--ok)" opacity=".5"/></svg>'
    },
    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 8v4l3 2"/></svg>',
      title: 'Lire une carte',
      body: '<p>Une carte affiche l’essentiel d’un coup d’œil : le <strong>liseré de gauche</strong> donne la priorité, les étiquettes le type et le module, et le pied de carte l’assigné, l’échéance et les compteurs (commentaires, fichiers, sous-tâches). Une échéance <span class="mguide-hl">dépassée</span> passe en rouge, à deux jours ou moins en orange.</p>',
      illu: '<svg viewBox="0 0 340 160" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI"><rect x="40" y="18" width="260" height="124" rx="11" fill="var(--bg)" stroke="var(--border)"/><rect x="40" y="18" width="4" height="124" rx="2" fill="var(--danger)"/><text x="58" y="16" font-size="8" fill="var(--danger)">priorité</text><rect x="58" y="32" width="46" height="15" rx="5" fill="rgba(248,113,113,.15)"/><text x="81" y="43" font-size="8" fill="var(--danger)" text-anchor="middle" font-weight="700">CRITIQUE</text><rect x="110" y="32" width="34" height="15" rx="5" fill="var(--card)" stroke="var(--border)"/><text x="127" y="43" font-size="8" fill="var(--muted)" text-anchor="middle">BUG</text><rect x="150" y="32" width="52" height="15" rx="5" fill="var(--card)" stroke="var(--border)"/><text x="176" y="43" font-size="8" fill="var(--muted)" text-anchor="middle">MYSTOCK</text><text x="58" y="70" font-size="11" fill="var(--text)" font-weight="700">Doublon à l’entrée Z1</text><circle cx="66" cy="96" r="10" fill="var(--accent-bg)"/><text x="66" y="99" font-size="8" fill="var(--accent)" text-anchor="middle" font-weight="800">EL</text><text x="86" y="99" font-size="9" fill="var(--danger)" font-weight="700">12 mars 2026</text><text x="176" y="99" font-size="9" fill="var(--muted)">3 commentaires</text><text x="262" y="99" font-size="9" fill="var(--muted)">2 fichiers</text><rect x="58" y="116" width="224" height="5" rx="2.5" fill="var(--border)"/><rect x="58" y="116" width="140" height="5" rx="2.5" fill="var(--accent)"/><text x="58" y="136" font-size="8" fill="var(--muted)">progression de la checklist</text></svg>'
    },
    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
      title: 'Le panneau de détail',
      body: '<p>Cliquez une carte pour ouvrir son panneau. Tout s’y modifie directement — <strong>chaque changement est enregistré immédiatement</strong>, il n’y a pas de bouton « Enregistrer ». Quatre onglets : <span class="mguide-tag">Détail</span> (champs, checklist, sous-tâches), <span class="mguide-tag">Commentaires</span>, <span class="mguide-tag">Fichiers</span> et <span class="mguide-tag">Activité</span>, qui trace qui a changé quoi.</p>',
      illu: '<svg viewBox="0 0 340 160" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI"><rect x="0" y="0" width="150" height="160" rx="0" fill="var(--bg)" opacity=".5"/><rect x="150" y="0" width="190" height="160" rx="0" fill="var(--card)" stroke="var(--border)"/><text x="164" y="24" font-size="11" fill="var(--text)" font-weight="700">Doublon à l’entrée Z1</text><rect x="164" y="34" width="42" height="14" rx="5" fill="var(--accent-bg)"/><text x="185" y="44" font-size="8" fill="var(--accent)" text-anchor="middle" font-weight="700">EN COURS</text><line x1="150" y1="58" x2="340" y2="58" stroke="var(--border)"/><text x="164" y="72" font-size="8" fill="var(--accent)" font-weight="700">Détail</text><line x1="162" y1="76" x2="192" y2="76" stroke="var(--accent)" stroke-width="2"/><text x="204" y="72" font-size="8" fill="var(--muted)">Commentaires</text><text x="272" y="72" font-size="8" fill="var(--muted)">Fichiers</text><rect x="164" y="88" width="80" height="20" rx="6" fill="var(--bg)" stroke="var(--border)"/><text x="170" y="101" font-size="8" fill="var(--text2)">Assigné</text><rect x="250" y="88" width="76" height="20" rx="6" fill="var(--bg)" stroke="var(--border)"/><text x="256" y="101" font-size="8" fill="var(--text2)">Échéance</text><rect x="164" y="116" width="162" height="30" rx="6" fill="var(--bg)" stroke="var(--border)"/><text x="170" y="130" font-size="8" fill="var(--muted)">Description, checklist,</text><text x="170" y="141" font-size="8" fill="var(--muted)">sous-tâches…</text></svg>'
    },
    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M21.4 11.05 12.25 20.2a5.5 5.5 0 0 1-7.78-7.78l9.19-9.19a3.67 3.67 0 0 1 5.18 5.18l-9.2 9.19a1.83 1.83 0 0 1-2.59-2.59l8.49-8.48"/></svg>',
      title: 'Contexte et suivi du temps',
      body: '<p>Dans l’onglet <strong>Fichiers</strong>, glissez maquettes, exports ou captures : le développeur trouve tout au même endroit. Dans <strong>Détail</strong>, l’<span class="mguide-hl">estimation</span> se saisit une fois et le <span class="mguide-hl">temps passé</span> se cumule au fil des pointages — l’écart entre les deux se lit directement dans la vue Liste.</p>',
      illu: '<svg viewBox="0 0 340 160" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI"><rect x="20" y="14" width="300" height="52" rx="10" fill="var(--accent-bg)" stroke="var(--accent)" stroke-dasharray="5 4"/><text x="170" y="38" font-size="10" fill="var(--accent)" text-anchor="middle" font-weight="700">Déposer un fichier de contexte</text><text x="170" y="54" font-size="8" fill="var(--accent)" text-anchor="middle" opacity=".8">ou cliquer pour choisir</text><rect x="20" y="78" width="300" height="30" rx="8" fill="var(--bg)" stroke="var(--border)"/><rect x="28" y="84" width="18" height="18" rx="5" fill="var(--accent-bg)"/><text x="56" y="96" font-size="9" fill="var(--text)">maquette-planning.png</text><text x="312" y="96" font-size="8" fill="var(--muted)" text-anchor="end">248 Ko</text><rect x="20" y="118" width="145" height="30" rx="8" fill="var(--bg)" stroke="var(--border)"/><text x="30" y="131" font-size="8" fill="var(--muted)">ESTIMATION</text><text x="30" y="143" font-size="10" fill="var(--text)" font-weight="700">4 h</text><rect x="175" y="118" width="145" height="30" rx="8" fill="var(--bg)" stroke="var(--border)"/><text x="185" y="131" font-size="8" fill="var(--muted)">TEMPS PASSÉ</text><text x="185" y="143" font-size="10" fill="var(--warn)" font-weight="700">6,5 h</text></svg>'
    }
  ]},

  'taches-liste': { steps: [
    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>',
      title: 'Vue Liste',
      body: '<p>La liste montre les mêmes tâches que le Kanban, mais <strong>à plat et triables</strong>. Cliquez un en-tête de colonne pour trier — un second clic inverse le sens. Elle sert à répondre à « qu’est-ce qui traîne ? » plutôt qu’à « où en est-on ? ».</p>',
      extra: '<div class="mguide-tasks"><div class="mguide-svc"><div class="mguide-svc-hd"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>Ce que vous avez à faire ici</div><ul class="mguide-svc-list"><li>Trier par échéance pour repérer les retards.</li><li>Comparer temps passé et estimation, tâche par tâche.</li><li>Filtrer sur une personne pour préparer un point d’équipe.</li></ul></div></div>'
    },
    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>',
      title: 'Filtrer et chercher',
      body: '<p>La barre de recherche filtre sur le <strong>titre et la description</strong>, dès le premier caractère ; <span class="mguide-tag">Échap</span> la vide. Les listes déroulantes cumulent les critères, et les compteurs du haut sont eux aussi cliquables : un clic sur <span class="mguide-hl">En retard</span> ne garde que les tâches en retard.</p>',
      illu: '<svg viewBox="0 0 340 160" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI"><rect x="14" y="14" width="70" height="26" rx="8" fill="var(--card)" stroke="var(--border)"/><text x="24" y="31" font-size="9" fill="var(--text2)">Idées 4</text><rect x="90" y="14" width="74" height="26" rx="8" fill="var(--card)" stroke="var(--border)"/><text x="100" y="31" font-size="9" fill="var(--text2)">En cours 3</text><rect x="170" y="14" width="80" height="26" rx="8" fill="var(--accent-bg)" stroke="var(--accent)"/><text x="180" y="31" font-size="9" fill="var(--accent)" font-weight="700">En retard 2</text><rect x="14" y="52" width="180" height="28" rx="9" fill="var(--card)" stroke="var(--accent)"/><circle cx="30" cy="66" r="5" fill="none" stroke="var(--muted)" stroke-width="1.6"/><line x1="34" y1="70" x2="38" y2="74" stroke="var(--muted)" stroke-width="1.6"/><text x="46" y="70" font-size="9" fill="var(--text2)">export</text><rect x="202" y="52" width="60" height="28" rx="9" fill="var(--card)" stroke="var(--border)"/><text x="212" y="70" font-size="9" fill="var(--muted)">Priorité</text><rect x="270" y="52" width="56" height="28" rx="9" fill="var(--card)" stroke="var(--border)"/><text x="280" y="70" font-size="9" fill="var(--muted)">Module</text><rect x="14" y="92" width="312" height="22" rx="5" fill="var(--bg)" stroke="var(--border)"/><text x="24" y="107" font-size="9" fill="var(--text)">Export PDF des OF</text><text x="316" y="107" font-size="9" fill="var(--danger)" text-anchor="end" font-weight="700">retard 3 j</text><rect x="14" y="118" width="312" height="22" rx="5" fill="var(--bg)" stroke="var(--border)"/><text x="24" y="133" font-size="9" fill="var(--text)">Doublon à l’entrée Z1</text><text x="316" y="133" font-size="9" fill="var(--danger)" text-anchor="end" font-weight="700">retard 1 j</text></svg>'
    },
    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5" rx="1"/><line x1="10" y1="12" x2="14" y2="12"/></svg>',
      title: 'Archiver plutôt que supprimer',
      body: '<p>Une tâche terminée qui encombre le board s’<strong>archive</strong> depuis son panneau de détail : elle disparaît du Kanban et de la liste, mais reste consultable dans <span class="mguide-tag">Archives</span> avec tout son historique. La suppression, elle, retire aussi les sous-tâches, commentaires et fichiers — réservez-la aux tâches créées par erreur.</p>',
      illu: '<svg viewBox="0 0 340 160" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI"><rect x="30" y="24" width="280" height="46" rx="10" fill="var(--bg)" stroke="var(--border)"/><rect x="42" y="38" width="94" height="18" rx="6" fill="var(--card)" stroke="var(--border)"/><text x="89" y="51" font-size="9" fill="var(--text2)" text-anchor="middle">Archiver</text><text x="152" y="51" font-size="9" fill="var(--muted)">conserve tout, masque la tâche</text><rect x="30" y="86" width="280" height="46" rx="10" fill="var(--bg)" stroke="var(--danger)" stroke-opacity=".5"/><rect x="42" y="100" width="94" height="18" rx="6" fill="rgba(248,113,113,.15)"/><text x="89" y="113" font-size="9" fill="var(--danger)" text-anchor="middle" font-weight="700">Supprimer</text><text x="152" y="113" font-size="9" fill="var(--muted)">retire sous-tâches et fichiers</text></svg>'
    }
  ]}
};

function syncGuideBtn(){
  const slot=document.getElementById('guide-btn-slot');
  if(!slot)return;
  const cle=(VIEW_META[S.view]||VIEW_META.kanban).guide;
  slot.innerHTML=(window.MySifaGuides&&typeof MySifaGuides.bookBtn==='function')?MySifaGuides.bookBtn(cle):'';
}

function initGuides(){
  try{
    if(!window.MySifaGuides)return;
    MySifaGuides.configure({role:USER_ROLE});
    MySifaGuides.registerMany(TACHES_GUIDES);
    MySifaGuides.boot().then(function(){
      syncGuideBtn();
      MySifaGuides.autoOpen((VIEW_META[S.view]||VIEW_META.kanban).guide);
    });
  }catch(e){}
}

// ══════════════════════════════════════════════════════════════════
// Boot
// ══════════════════════════════════════════════════════════════════
function updateUserChip(){
  if(!S.me)return;
  const chip=document.querySelector('.user-chip');
  if(chip&&window.MySifaUserChip){MySifaUserChip.fill(chip,S.me,{showProfil:false});return;}
  const n=document.getElementById('uc-name');if(n)n.textContent=S.me.nom||'—';
  const r=document.getElementById('uc-role');if(r)r.textContent=S.me.role||'—';
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
  syncThemeBtn();
  try{
    S.me=await api('/api/auth/me');
    if(S.me&&window.MySifaTheme)MySifaTheme.mergeFromUser(S.me);
    syncThemeBtn();
    updateUserChip();
  }catch(e){}
  try{
    S.meta=await api('/api/taches/meta');
    remplirFiltres();
  }catch(e){toast(e.message,'err');return;}
  brancherFiltres();
  brancherSousTaches();
  showView(readView(),{silent:true});
  await chargerStats();
  initGuides();
})();
window.addEventListener('hashchange',function(){try{showView(readView(),{silent:true});}catch(e){}});
</script>
</body>
</html>
"""

"""MySifa — Page Saisie Production (Fabrication) v1.0

Route dédiée : /fabrication
Accessible : rôle fabrication + admins
Page standalone (architecture identique à stock_page.py).
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.services.auth_service import get_current_user, is_fabrication, is_admin
from app.web.access_denied import access_denied_response

router = APIRouter()


@router.get("/fabrication", response_class=HTMLResponse)
def fabrication_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/fabrication", status_code=302)
        raise
    if not (is_fabrication(user) or is_admin(user)):
        return access_denied_response("Saisie Production")
    return HTMLResponse(
        content=FABRICATION_HTML,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


FABRICATION_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#0a0e17">
<title>Saisie Production — MySifa</title>
<link rel="icon" type="image/png" sizes="512x512" href="/static/mys_icon_512.png">
<link rel="apple-touch-icon" href="/static/mys_icon_180.png">
<style>
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;
  --muted:#94a3b8;--accent:#22d3ee;--accent-bg:rgba(34,211,238,.12);
  --success:#34d399;--warn:#fbbf24;--danger:#f87171;
  --c1:#38bdf8;--c2:#a78bfa;--c3:#34d399;--c4:#fbbf24;--c5:#f87171;
  --footer-h:190px;
}
body.light{
  --bg:#f1f5f9;--card:#fff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;
  --muted:#94a3b8;--accent:#0891b2;--accent-bg:rgba(8,145,178,.10);
  --success:#059669;--warn:#d97706;--danger:#dc2626;--c2:#7c3aed;
}
html,body{height:100%;overflow:hidden}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text)}
::-webkit-scrollbar{width:4px;height:4px}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px}
button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
button:focus:not(:focus-visible){outline:none}
input,select,textarea{font-family:inherit;color:var(--text)}

/* ── Root grid ──────────────────────────────────────────────── */
#root{
  display:grid;
  grid-template-columns:248px 1fr;
  grid-template-rows:1fr var(--footer-h);
  height:100vh;
  overflow:hidden;
}

/* ── Sidebar ────────────────────────────────────────────────── */
.fab-sidebar{
  grid-column:1;grid-row:1;
  background:var(--card);
  border-right:1px solid var(--border);
  display:flex;flex-direction:column;
  overflow:hidden;
}
.fab-sidebar-head{
  padding:14px 12px 10px;
  border-bottom:1px solid var(--border);
  flex-shrink:0;
}
.fab-sidebar-brand{font-size:14px;font-weight:800;line-height:1.2}
.fab-sidebar-brand span{color:var(--accent)}
.fab-sidebar-sub{font-size:10px;color:var(--muted);letter-spacing:1.2px;text-transform:uppercase;margin-top:2px}
.fab-sidebar-list{flex:1;overflow-y:auto;padding:6px 6px}
.fab-ops-group{margin-bottom:2px}
.fab-ops-label{font-size:9px;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase;
  padding:8px 8px 4px;font-weight:700}
.fab-op-btn{
  display:flex;align-items:center;gap:8px;
  width:100%;padding:7px 8px;border-radius:6px;
  border:none;background:transparent;cursor:pointer;
  font-family:inherit;text-align:left;font-size:12px;
  color:var(--text2);transition:all .12s;
  user-select:none;
}
.fab-op-btn:hover{background:var(--accent-bg);color:var(--text)}
.fab-op-btn:active{transform:scale(.97)}
.fab-op-btn--disabled{opacity:.35;cursor:not-allowed}
.fab-op-btn--disabled:hover{background:transparent;color:var(--text2)}
.fab-op-code{
  font-family:monospace;font-size:11px;font-weight:700;
  min-width:24px;text-align:center;
}
.fab-op-label{font-size:12px;line-height:1.3;flex:1}
.fab-sidebar-bottom{
  padding:10px 8px;border-top:1px solid var(--border);flex-shrink:0;
  display:flex;flex-direction:column;gap:6px;
}
.fab-back-btn{
  display:flex;align-items:center;gap:8px;padding:9px 10px;border-radius:8px;
  border:none;background:transparent;color:var(--text2);
  cursor:pointer;font-size:12px;font-family:inherit;transition:color .15s;width:100%;
}
.fab-back-btn:hover{color:var(--text);background:transparent}
.fab-back-btn .wm{font-weight:800;color:var(--text)}
.fab-back-btn .wm span{color:var(--accent)}
.fab-user-chip{padding:8px 10px;border-radius:8px;background:var(--accent-bg)}
.fab-user-name{font-size:11px;font-weight:700;color:var(--text)}
.fab-user-machine{font-size:10px;color:var(--accent);font-weight:600;margin-top:1px}

/* ── Main ───────────────────────────────────────────────────── */
.fab-main{
  grid-column:2;grid-row:1;
  display:flex;flex-direction:column;
  overflow:hidden;
}
.fab-main-head{
  padding:14px 20px 10px;
  border-bottom:1px solid var(--border);
  flex-shrink:0;
  display:flex;align-items:center;gap:12px;
}
.fab-main-title{font-size:15px;font-weight:800}
.fab-main-sub{font-size:11px;color:var(--muted);margin-left:auto}
.fab-etat-badge{
  font-size:10px;font-weight:700;padding:3px 10px;border-radius:20px;
  text-transform:uppercase;letter-spacing:.5px;
}
.fab-table-wrap{flex:1;overflow-y:auto;padding:0}
table.fab-table{width:100%;border-collapse:collapse}
table.fab-table th{
  position:sticky;top:0;z-index:10;
  background:var(--bg);
  font-size:10px;color:var(--muted);
  letter-spacing:1px;text-transform:uppercase;
  padding:8px 14px;text-align:left;
  border-bottom:1px solid var(--border);
  font-weight:700;
}
table.fab-table td{
  padding:8px 14px;font-size:13px;
  border-bottom:1px solid rgba(255,255,255,.04);
  vertical-align:middle;
  color:var(--text2);
}
table.fab-table tr:last-child td{border-bottom:none}
table.fab-table tr.fab-row-last td{
  background:rgba(34,211,238,.04);
}
.fab-time{font-family:monospace;font-size:12px;font-weight:700;color:var(--text);white-space:nowrap;letter-spacing:.2px}
.fab-op-chip{
  display:inline-flex;align-items:center;gap:5px;
  font-size:11px;font-weight:700;padding:2px 8px;border-radius:12px;
}
.fab-op-chip-code{font-family:monospace;font-weight:800;font-size:11px}
.fab-metrage{font-family:monospace;font-size:11px;color:var(--muted)}
.fab-comment-cell{font-size:11px;color:var(--muted);max-width:200px;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.fab-comment-btn{
  border:none;background:transparent;cursor:pointer;color:var(--muted);
  padding:3px 6px;border-radius:4px;font-size:11px;font-family:inherit;
  transition:all .1s;
}
.fab-comment-btn:hover{color:var(--accent);background:var(--accent-bg)}
.fab-empty{
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  padding:60px 20px;color:var(--muted);gap:10px;
  font-size:13px;text-align:center;
}
.fab-empty-icon{font-size:36px;opacity:.4}

/* ── Footer ─────────────────────────────────────────────────── */
.fab-footer{
  grid-column:1/-1;grid-row:2;
  background:var(--card);
  border-top:2px solid var(--border);
  display:grid;
  grid-template-columns:1fr auto 1fr;
  gap:16px;
  padding:12px 16px;
  overflow:hidden;
}
/* Left: dossier info */
.fab-footer-info{
  display:flex;flex-direction:column;gap:4px;overflow:hidden;
  min-width:0;
}
.fab-dossier-ref{
  font-size:13px;font-weight:800;color:var(--accent);
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
}
.fab-dossier-client{
  font-size:12px;font-weight:700;color:var(--text);
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
}
.fab-dossier-meta{display:flex;flex-wrap:wrap;gap:4px 12px;margin-top:4px}
.fab-meta-item{
  font-size:10px;color:var(--muted);
  display:flex;align-items:center;gap:4px;white-space:nowrap;
}
.fab-meta-label{font-weight:700;text-transform:uppercase;letter-spacing:.4px;color:var(--text2)}
.fab-no-dossier{font-size:12px;color:var(--muted);font-style:italic}

/* Center: action buttons */
.fab-footer-actions{
  display:flex;flex-direction:column;align-items:center;gap:8px;
  min-width:240px;
}
.fab-footer-btns{display:flex;gap:8px;flex-wrap:wrap;justify-content:center}
.fab-btn{
  display:inline-flex;align-items:center;gap:7px;
  padding:10px 18px;border-radius:10px;
  border:none;cursor:pointer;font-family:inherit;font-size:13px;
  font-weight:700;transition:all .15s;white-space:nowrap;
}
.fab-btn:hover{filter:brightness(1.1);transform:translateY(-1px)}
.fab-btn:active{transform:translateY(0);filter:brightness(.95)}
.fab-btn:disabled{opacity:.4;cursor:not-allowed;transform:none;filter:none}
.fab-btn-primary{background:var(--accent);color:var(--bg)}
.fab-btn-success{background:var(--success);color:var(--bg)}
.fab-btn-warn{background:var(--warn);color:var(--bg)}
.fab-btn-danger{background:var(--danger);color:#fff}
.fab-btn-ghost{background:var(--accent-bg);color:var(--accent);border:1px solid rgba(34,211,238,.3)}
.fab-btn-muted{background:transparent;color:var(--text2);border:1px solid var(--border)}
.fab-btn-muted:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.fab-btn-sm{padding:7px 12px;font-size:12px;border-radius:8px}

/* Theme toggle button */
.fab-theme-btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;padding:8px 12px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-size:12px;font-family:inherit;transition:all .15s}
.fab-theme-btn:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}

/* Right: search + comment */
.fab-footer-tools{
  display:flex;flex-direction:column;gap:8px;justify-content:center;
  min-width:0;
}
.fab-search-wrap{display:flex;gap:6px;align-items:center}
.fab-search-input{
  flex:1;background:var(--bg);border:1.5px solid var(--border);
  border-radius:8px;padding:8px 12px;font-size:12px;color:var(--text);
  outline:none;transition:border-color .15s;font-family:inherit;
}
.fab-search-input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12)}
.fab-search-input::placeholder{color:var(--muted)}
.fab-search-btn{
  padding:8px 14px;background:var(--accent);color:#0a0e17;
  border:none;border-radius:8px;cursor:pointer;font-size:12px;
  font-weight:700;font-family:inherit;white-space:nowrap;transition:filter .15s;
}
.fab-search-btn:hover{filter:brightness(1.1)}
.fab-comment-row{display:flex;gap:6px;align-items:center}
.fab-comment-hint{font-size:10px;color:var(--muted);flex:1}

/* ── Modals ─────────────────────────────────────────────────── */
.fab-modal-overlay{
  position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1000;
  display:flex;align-items:center;justify-content:center;
  padding:20px;
}
.fab-modal{
  background:var(--card);border:1px solid var(--border);border-radius:16px;
  padding:24px;min-width:320px;max-width:560px;width:100%;
  box-shadow:0 24px 64px rgba(0,0,0,.5);
  animation:fadeUp .18s ease-out;
}
@keyframes fadeUp{from{transform:translateY(8px);opacity:0}to{transform:translateY(0);opacity:1}}
.fab-modal-title{font-size:16px;font-weight:800;margin-bottom:16px;color:var(--text)}
.fab-modal-sub{font-size:12px;color:var(--muted);margin-bottom:16px;line-height:1.5}
.fab-field{margin-bottom:14px}
.fab-field label{font-size:11px;font-weight:700;color:var(--text2);display:block;
  margin-bottom:5px;text-transform:uppercase;letter-spacing:.5px}
.fab-field input,.fab-field textarea,.fab-field select{
  width:100%;background:var(--bg);border:1.5px solid var(--border);
  border-radius:8px;padding:10px 12px;font-size:13px;color:var(--text);
  outline:none;font-family:inherit;transition:border-color .15s;
}
.fab-field input:focus,.fab-field textarea:focus,.fab-field select:focus{
  border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12)
}
.fab-field textarea{resize:vertical;min-height:70px}
.fab-modal-btns{display:flex;gap:8px;justify-content:flex-end;margin-top:18px}

/* Dossier picker */
.fab-picker-list{
  max-height:300px;overflow-y:auto;margin:10px 0;
  display:flex;flex-direction:column;gap:4px;
}
.fab-picker-item{
  padding:10px 12px;border-radius:8px;border:1px solid var(--border);
  cursor:pointer;transition:all .12s;background:var(--bg);
  display:flex;flex-direction:column;gap:3px;
}
.fab-picker-item:hover{border-color:var(--accent);background:var(--accent-bg)}
.fab-picker-line1{font-size:13px;font-weight:800;color:var(--accent);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.fab-picker-line1 .fab-picker-ref{color:var(--accent)}
.fab-picker-line1 .fab-picker-sep{color:var(--muted);font-weight:400;margin:0 4px}
.fab-picker-line1 .fab-picker-client{color:var(--text);font-weight:600}
.fab-picker-line2{font-size:12px;color:var(--text2);margin-top:1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.fab-picker-meta{font-size:10px;color:var(--muted);display:flex;gap:10px;margin-top:2px;flex-wrap:wrap}
.fab-picker-empty{font-size:12px;color:var(--muted);padding:20px;text-align:center}
.fab-picker-search{
  width:100%;background:var(--bg);border:1.5px solid var(--border);
  border-radius:8px;padding:9px 12px;font-size:13px;color:var(--text);
  outline:none;font-family:inherit;margin-bottom:8px;
  transition:border-color .15s;
}
.fab-picker-search:focus{border-color:var(--accent)}

/* Toast */
.fab-toast{
  position:fixed;bottom:210px;left:50%;
  transform:translateX(-50%);
  background:var(--card);border:1px solid var(--border);border-radius:10px;
  padding:10px 20px;font-size:13px;font-weight:600;
  box-shadow:0 8px 32px rgba(0,0,0,.4);z-index:2000;white-space:nowrap;
  animation:fadeUp .2s ease-out;
}

/* Loading overlay */
.fab-loading{
  position:fixed;inset:0;background:rgba(10,14,23,.8);z-index:3000;
  display:flex;align-items:center;justify-content:center;
  font-size:14px;font-weight:700;color:var(--accent);gap:12px;
}
.fab-spinner{
  width:20px;height:20px;border:2px solid var(--border);
  border-top-color:var(--accent);border-radius:50%;
  animation:spin .7s linear infinite;
}
@keyframes spin{to{transform:rotate(360deg)}}

/* Etat badges */
.eb-production{background:rgba(52,211,153,.15);color:#34d399}
.eb-arret{background:rgba(251,191,36,.15);color:#fbbf24}
.eb-arrive{background:rgba(56,189,248,.15);color:#38bdf8}
.eb-fin{background:rgba(167,139,250,.15);color:#a78bfa}
.eb-sans{background:rgba(148,163,184,.15);color:#94a3b8}

/* Category colors for ops */
.cat-production{color:#34d399}
.cat-personnel{color:#38bdf8}
.cat-calage{color:#a78bfa}
.cat-arret{color:#fbbf24}
.cat-appro{color:#22d3ee}
.cat-nettoyage{color:#2dd4bf}
.cat-technique{color:#f87171}
.cat-pause{color:#94a3b8}
.cat-annulation{color:#e879f9}

/* ── Footer tab nav ─────────────────────────────────────────── */
.fab-tab-nav{
  display:inline-flex;border:1px solid var(--border);border-radius:10px;
  overflow:hidden;background:var(--bg);
}
.fab-tab-btn{
  width:72px;padding:7px 4px 5px;display:flex;flex-direction:column;
  align-items:center;gap:2px;background:none;border:none;cursor:pointer;
  font-family:inherit;font-size:9px;font-weight:800;
  text-transform:uppercase;letter-spacing:.5px;color:var(--muted);
  transition:color .15s,background .15s;
}
.fab-tab-btn+.fab-tab-btn{border-left:1px solid var(--border)}
.fab-tab-btn.active{color:var(--accent);background:var(--accent-bg)}
.fab-tab-btn:hover:not(.active){color:var(--text2);background:rgba(255,255,255,.04)}
.fab-tab-btn svg{opacity:.65}
.fab-tab-btn.active svg{opacity:1}

/* ── Print panel ─────────────────────────────────────────────── */
.fab-panel{
  flex:1;overflow-y:auto;padding:16px 20px;
  display:flex;flex-direction:column;gap:14px;
}
.fab-panel-title{font-size:14px;font-weight:800;color:var(--text);
  display:flex;align-items:center;gap:8px}
.fab-print-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px}
.fab-print-card{
  border:1.5px solid var(--border);border-radius:12px;padding:14px 12px;
  background:var(--bg);cursor:pointer;text-align:center;transition:all .15s;
  display:flex;flex-direction:column;align-items:center;gap:6px;
}
.fab-print-card:hover{border-color:var(--accent);background:var(--accent-bg);transform:translateY(-1px)}
.fab-print-card-icon{font-size:24px;line-height:1}
.fab-print-card-name{font-size:12px;font-weight:800;color:var(--text)}
.fab-print-card-format{font-size:10px;color:var(--muted)}

/* ── Traça panel ──────────────────────────────────────────────── */
.fab-traca-layout{display:flex;flex-direction:column;gap:12px;padding:12px 16px;flex:1;overflow:hidden}
.fab-traca-scan-row{display:flex;gap:8px;align-items:center;flex-shrink:0}
.fab-traca-manual{
  flex:1;background:var(--bg);border:1.5px solid var(--border);
  border-radius:8px;padding:9px 12px;font-size:13px;color:var(--text);
  outline:none;font-family:inherit;transition:border-color .15s;
}
.fab-traca-manual:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12)}
.fab-traca-video-wrap{position:relative;border-radius:10px;overflow:hidden;background:#000;height:140px;flex-shrink:0}
.fab-traca-video-wrap video{width:100%;height:100%;object-fit:cover;display:block}
.fab-traca-scan-line{
  position:absolute;left:0;right:0;height:2px;background:rgba(34,211,238,.8);
  animation:scanLine 1.8s ease-in-out infinite;
}
@keyframes scanLine{0%{top:10%}50%{top:85%}100%{top:10%}}
.fab-traca-table-wrap{flex:1;overflow-y:auto;min-height:0}
table.fab-traca-table{width:100%;border-collapse:collapse;font-size:12px}
table.fab-traca-table th{font-size:10px;color:var(--muted);font-weight:700;
  text-transform:uppercase;letter-spacing:.4px;padding:6px 10px;
  border-bottom:1px solid var(--border);text-align:left;position:sticky;top:0;background:var(--card)}
table.fab-traca-table td{padding:7px 10px;border-bottom:1px solid var(--border)}
table.fab-traca-table tr:last-child td{border-bottom:none}
.fab-traca-code{font-family:monospace;font-weight:700;color:var(--accent)}
.fab-traca-del{background:none;border:none;cursor:pointer;color:var(--muted);padding:2px 6px;
  border-radius:4px;transition:color .12s}
.fab-traca-del:hover{color:var(--danger)}
.fab-traca-empty{text-align:center;padding:24px;color:var(--muted);font-size:12px}
.fab-traca-status{font-size:11px;color:var(--muted);display:flex;align-items:center;gap:6px;flex-shrink:0}
.fab-traca-saving{color:var(--accent)}

/* Alert banner */
.fab-alert{
  margin:10px 16px 0;padding:10px 14px;border-radius:8px;
  font-size:12px;font-weight:600;display:flex;align-items:center;gap:8px;
}
.fab-alert-warn{background:rgba(251,191,36,.15);border:1px solid rgba(251,191,36,.3);color:#fbbf24}
.fab-alert-danger{background:rgba(248,113,113,.15);border:1px solid rgba(248,113,113,.3);color:#f87171}

/* Mobile topbar */
.fab-topbar{
  display:none;position:fixed;top:0;left:0;right:0;z-index:200;
  background:var(--bg);border-bottom:1px solid var(--border);
  padding:10px 14px;align-items:center;gap:10px;
}
.fab-topbar-btn{
  width:38px;height:38px;border-radius:9px;border:1px solid var(--border);
  background:var(--card);color:var(--text2);cursor:pointer;
  display:inline-flex;align-items:center;justify-content:center;
  font-family:inherit;flex-shrink:0;
}
.fab-topbar-btn:hover{border-color:var(--accent);color:var(--accent)}
.fab-topbar-title{font-size:13px;font-weight:800;flex:1;text-align:center}
.fab-sidebar-overlay{
  display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:190;
}

/* Responsive */
@media(max-width:900px){
  :root{--footer-h:auto}
  #root{
    grid-template-columns:1fr;
    grid-template-rows:48px 1fr auto;
  }
  .fab-topbar{display:flex}
  .fab-sidebar{
    grid-column:1;grid-row:1/-1;
    position:fixed;left:0;top:0;bottom:0;height:auto;
    width:260px;z-index:300;
    transform:translateX(-105%);
    transition:transform .18s ease;
    box-shadow:0 16px 48px rgba(0,0,0,.55);
  }
  body.sb-open .fab-sidebar{transform:translateX(0)}
  body.sb-open .fab-sidebar-overlay{display:block}
  .fab-main{
    grid-column:1;grid-row:2;
    padding-top:0;
  }
  .fab-footer{
    grid-column:1;grid-row:3;
    grid-template-columns:1fr;
    min-height:unset;
    padding:10px 12px;
    gap:10px;
  }
  .fab-footer-actions{min-width:0;width:100%}
  .fab-footer-info{display:none}
  .fab-footer-tools{flex-direction:row;gap:6px;align-items:center}
  .fab-comment-hint{display:none}
}
</style>
</head>
<body>
<div id="root"></div>
<script>
'use strict';

/* ── Operations config ───────────────────────────────────────── */
const OPS = {
  "01":{"label":"Début dossier","category":"personnel","severity":"info","required":true},
  "02":{"label":"Calage","category":"calage","severity":"info"},
  "03":{"label":"Production","category":"production","severity":"info"},
  "10":{"label":"Calage Errepi","category":"calage","severity":"info"},
  "11":{"label":"Calage Bunsch","category":"calage","severity":"info"},
  "50":{"label":"Arrêt machine","category":"arret","severity":"attention"},
  "51":{"label":"Casse Echenillage","category":"arret","severity":"attention"},
  "52":{"label":"Problème raccord","category":"arret","severity":"attention"},
  "53":{"label":"Casse bande","category":"arret","severity":"attention"},
  "54":{"label":"Problème Impressions","category":"arret","severity":"attention"},
  "55":{"label":"Surdosage colle","category":"arret","severity":"attention"},
  "56":{"label":"Appro mandrins","category":"appro","severity":"info"},
  "58":{"label":"Changement bobines","category":"appro","severity":"info"},
  "59":{"label":"Changement Contre-Partie","category":"calage","severity":"info"},
  "60":{"label":"Changement Plaque","category":"calage","severity":"info"},
  "61":{"label":"Nettoyage","category":"nettoyage","severity":"info"},
  "62":{"label":"Remplissage colle Errépi","category":"arret","severity":"info"},
  "63":{"label":"Pause","category":"pause","severity":"info"},
  "64":{"label":"Intervention technique","category":"technique","severity":"info"},
  "65":{"label":"Débordement adhésif","category":"arret","severity":"attention"},
  "66":{"label":"Attente matière","category":"appro","severity":"critique"},
  "67":{"label":"Vidange four colle","category":"nettoyage","severity":"info"},
  "68":{"label":"Casse Claquant métal","category":"arret","severity":"attention"},
  "69":{"label":"Arrêt urgence Errepi","category":"arret","severity":"info"},
  "70":{"label":"Problème UV1","category":"arret","severity":"info"},
  "71":{"label":"Problème UV2","category":"arret","severity":"info"},
  "72":{"label":"Problème UV3","category":"arret","severity":"info"},
  "73":{"label":"Problème Turret","category":"technique","severity":"attention"},
  "74":{"label":"Changement Magnétique","category":"calage","severity":"info"},
  "75":{"label":"Changement Cliché","category":"calage","severity":"info"},
  "76":{"label":"Rétraction couteaux","category":"technique","severity":"info"},
  "77":{"label":"Nettoyage Bunch","category":"nettoyage","severity":"info"},
  "86":{"label":"Arrivée personnel","category":"personnel","severity":"info","required":true},
  "87":{"label":"Départ personnel","category":"personnel","severity":"info","required":true},
  "88":{"label":"Reprise production","category":"production","severity":"info"},
  "89":{"label":"Fin dossier","category":"personnel","severity":"info","required":true},
  "90":{"label":"Annulation saisie","category":"annulation","severity":"info"},
};

const CAT_ORDER = ["personnel","production","calage","arret","appro","nettoyage","technique","pause","annulation"];
const CAT_LABELS = {
  personnel:"Personnel",production:"Production",calage:"Calage",arret:"Arrêts machine",
  appro:"Approvisionnement",nettoyage:"Nettoyage",technique:"Technique",pause:"Pauses",annulation:"Annulation"
};

/* ── State ───────────────────────────────────────────────────── */
let S = {
  user: null,
  saisies: [],
  etat: 'loading',   // loading | sans_session | arrive | en_cours_production | en_arret | fin_dossier
  dossier: null,     // planning_entry actif
  dossiers: [],      // liste pour picker
  machine: null,     // machine liée
  machines: [],      // liste machines (pour sélecteur admin)
  adminMachineId: null,  // machine sélectionnée par l'admin (override)
  operateur: '',
  lastSaisie: null,

  // Modals
  showDossierPicker: false,
  pickerQuery: '',
  showDebutModal: false,
  showFinModal: false,
  showCommentModal: false,
  commentSaisieId: null,

  // Form values
  metrageDebut: '',
  metrageFinVal: '',
  nbEtiquettes: '',
  commentText: '',
  searchQuery: '',

  // Footer tabs
  fabTab: 'saisie',   // 'saisie' | 'print' | 'traca'

  // Traça matières
  tracaMatieres: [],
  tracaLoading: false,
  tracaScanning: false,
  tracaStream: null,
  tracaManual: '',
  tracaAutoSaving: false,
  tracaLastCode: null,  // anti-dup

  // UI
  sidebarOpen: false,
  loading: false,
  toast: null,
  toastType: 'success',

  // Pending op from picker
  _pendingPickerOp: null,
};

/* ── Helpers ─────────────────────────────────────────────────── */
function set(u){ Object.assign(S, u); render(); }
function api_path(p){ return p; }

function fmtTime(iso){
  if(!iso) return '--/--/---- --:--';
  const d = new Date(iso);
  if(isNaN(d)) return iso.slice(0,16)||'--';
  const dd = String(d.getDate()).padStart(2,'0');
  const mo = String(d.getMonth()+1).padStart(2,'0');
  const yr = d.getFullYear();
  const hh = String(d.getHours()).padStart(2,'0');
  const mm = String(d.getMinutes()).padStart(2,'0');
  return dd+'/'+mo+'/'+yr+' '+hh+':'+mm;
}
function fmtDate(iso){
  if(!iso) return '';
  const d = new Date(iso);
  if(isNaN(d)) return iso.slice(0,10)||'';
  return d.toLocaleDateString('fr-FR',{day:'2-digit',month:'2-digit',year:'numeric'});
}
function fN(v){ if(v==null||v===''||isNaN(Number(v))) return '—'; return Number(v).toLocaleString('fr-FR'); }

function catColor(cat){
  const m = {production:'var(--success)',personnel:'var(--c1)',calage:'var(--c2)',
    arret:'var(--warn)',appro:'var(--accent)',nettoyage:'#2dd4bf',
    technique:'var(--danger)',pause:'var(--muted)',annulation:'#e879f9'};
  return m[cat]||'var(--muted)';
}
function severityColor(sev){
  if(sev==='critique') return 'var(--danger)';
  if(sev==='attention') return 'var(--warn)';
  return null;
}

function etatLabel(e){
  const m = {
    loading:'Chargement…',
    sans_session:'Hors session',
    arrive:'Arrivé',
    en_cours_production:'En production',
    en_arret:'Arrêt en cours',
    fin_dossier:'Dossier terminé',
  };
  return m[e]||e;
}
function etatClass(e){
  const m = {
    sans_session:'eb-sans',arrive:'eb-arrive',
    en_cours_production:'eb-production',en_arret:'eb-arret',
    fin_dossier:'eb-fin',loading:'eb-sans',
  };
  return m[e]||'eb-sans';
}

/* ── DOM builder ─────────────────────────────────────────────── */
function h(tag, attrs, ...children){
  const el = document.createElement(tag);
  if(attrs) Object.entries(attrs).forEach(([k,v])=>{
    if(!v && v!==0 && v!==false) return;
    if(k==='className') el.className=v;
    else if(k==='style'&&typeof v==='object') Object.assign(el.style,v);
    else if(k.startsWith('on')) el.addEventListener(k.slice(2).toLowerCase(),v);
    else if(k==='disabled'||k==='checked'||k==='readonly'||k==='selected'){
      if(v) el.setAttribute(k,''); else el.removeAttribute(k);
    }
    else el.setAttribute(k,String(v));
  });
  children.flat(Infinity).forEach(c=>{
    if(c==null||c===false||c===undefined) return;
    el.appendChild(typeof c==='string'?document.createTextNode(c):c);
  });
  return el;
}
function txt(t){ return document.createTextNode(String(t||'')); }

function icon(name,size=16){
  const ICONS = {
    home:'<polyline points="3 9 12 2 21 9"/><polyline points="9 22 9 12 15 12 15 22"/><path d="M3 9v13h18V9"/>',
    menu:'<line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>',
    x:'<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
    check:'<polyline points="20 6 9 17 4 12"/>',
    play:'<polygon points="5 3 19 12 5 21 5 3"/>',
    pause:'<rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/>',
    'flag-off':'<line x1="4" y1="4" x2="4" y2="20"/><path d="M4 15s4-4 8 0 8 0 8 0V4s-4 4-8 0-8 0-8 0"/>',
    flag:'<path d="M4 15s4-4 8 0 8 0 8 0V4s-4 4-8 0-8 0-8 0"/><line x1="4" y1="4" x2="4" y2="20"/>',
    user:'<circle cx="12" cy="8" r="4"/><path d="M20 21a8 8 0 1 0-16 0"/>',
    search:'<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
    'message-square':'<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    'arrow-left':'<line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>',
    clock:'<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    tool:'<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
    'log-out':'<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
    edit:'<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>',
    alert:'<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
    sun:'<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>',
    moon:'<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>',
    'plus-circle':'<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/>',
    printer:'<polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/>',
    scan:'<rect x="3" y="3" width="5" height="5"/><rect x="16" y="3" width="5" height="5"/><rect x="3" y="16" width="5" height="5"/><line x1="21" y1="16" x2="21" y2="21"/><line x1="16" y1="21" x2="21" y2="21"/><line x1="11" y1="3" x2="11" y2="7"/><line x1="11" y1="11" x2="11" y2="17"/><line x1="3" y1="11" x2="7" y2="11"/><line x1="11" y1="11" x2="17" y2="11"/>',
    camera:'<path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/>',
    'video-off':'<path d="M16 16v1a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h2"/><path d="M7.5 4H14a2 2 0 0 1 2 2v3.5"/><polyline points="22 8 22 16 18 13"/><line x1="2" y1="2" x2="22" y2="22"/>',
    trash:'<polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/>',
  };
  const svg = document.createElementNS('http://www.w3.org/2000/svg','svg');
  svg.setAttribute('width',String(size));svg.setAttribute('height',String(size));
  svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('fill','none');
  svg.setAttribute('stroke','currentColor');svg.setAttribute('stroke-width','2');
  svg.setAttribute('stroke-linecap','round');svg.setAttribute('stroke-linejoin','round');
  svg.innerHTML = ICONS[name]||'';
  return svg;
}

function svgIcon(name,size=16){
  const el = document.createElement('span');
  el.style.display='inline-flex';el.style.alignItems='center';
  el.appendChild(icon(name,size));
  return el;
}

/* ── API calls ───────────────────────────────────────────────── */
async function apiFetch(path, opts={}){
  const r = await fetch(path, {credentials:'include', ...opts});
  if(r.status===401){ window.location.href='/'; return null; }
  if(!r.ok){
    const e = await r.json().catch(()=>({}));
    throw new Error(e.detail||'Erreur '+r.status);
  }
  return r.json();
}

async function loadSession(){
  let url = '/api/fabrication/session';
  if(S.adminMachineId) url += '?machine_id='+S.adminMachineId;
  const d = await apiFetch(url).catch(e=>{
    showToast('Erreur session: '+e.message,'danger');
    return null;
  });
  if(!d){ set({etat:'sans_session'}); return; }
  set({
    saisies: d.saisies||[],
    etat: d.etat||'sans_session',
    dossier: d.dossier||null,
    lastSaisie: d.last_saisie||null,
    operateur: d.operateur||'',
    machine: d.machine||null,
  });
}

async function loadDossiers(){
  const d = await apiFetch('/api/fabrication/dossiers').catch(()=>null);
  if(d) set({dossiers: d.dossiers||[]});
}

async function loadMachines(){
  const d = await apiFetch('/api/fabrication/machines').catch(()=>null);
  if(d) set({machines: d.machines||[]});
}

async function triggerOp(opCode, opLabel, extra={}){
  const opStr = opCode+' - '+opLabel;
  set({loading:true});
  try{
    const body = {operation: opStr, ...extra};
    if(S.dossier) body.no_dossier = S.dossier.reference;
    if(S.machine) body.machine = S.machine.nom;
    if(S.dossier) body.client = S.dossier.client||'';
    if(S.dossier) body.designation = S.dossier.description||'';
    // Admin sans machine liée : passer le machine_id sélectionné
    if(S.adminMachineId) body.machine_id = S.adminMachineId;

    const d = await apiFetch('/api/fabrication/saisie',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body: JSON.stringify(body),
    });
    if(d && d.success){
      showToast('Saisie enregistrée : '+opStr);
    }
  }catch(e){
    showToast('Erreur : '+e.message,'danger');
  }finally{
    set({loading:false});
    await loadSession(); // toujours rafraîchir l'état après saisie (succès ou erreur)
  }
}

async function saveComment(){
  const id = S.commentSaisieId;
  if(!id) return;
  set({loading:true});
  try{
    await apiFetch('/api/fabrication/saisie/'+id+'/commentaire',{
      method:'PUT',headers:{'Content-Type':'application/json'},
      body: JSON.stringify({commentaire: S.commentText}),
    });
    showToast('Commentaire enregistré');
    set({showCommentModal:false, commentText:'', commentSaisieId:null});
    await loadSession();
  }catch(e){
    showToast('Erreur : '+e.message,'danger');
  }finally{
    set({loading:false});
  }
}

function showToast(msg, type='success'){
  set({toast:msg, toastType:type});
  setTimeout(()=>set({toast:null}),3200);
}

/* ── Sidebar ─────────────────────────────────────────────────── */
function renderSidebar(){
  const grouped = {};
  CAT_ORDER.forEach(c=>{ grouped[c]=[]; });
  Object.entries(OPS).forEach(([code,op])=>{
    const c = op.category||'autre';
    if(!grouped[c]) grouped[c]=[];
    grouped[c].push({code,...op});
  });

  // Les opérations de la sidebar ne sont actives qu'en cours de production/arrêt
  const opsEnabled = S.etat==='en_cours_production' || S.etat==='en_arret';

  const groups = [];
  CAT_ORDER.forEach(cat=>{
    const ops = grouped[cat]||[];
    if(!ops.length) return;
    // Masquer les ops de personnel/annulation de la sidebar (gérées par les boutons footer)
    const sidebarExclude = new Set(['86','87','01','89','88','90']);
    const filteredOps = ops.filter(o=>!sidebarExclude.has(o.code));
    if(!filteredOps.length) return;
    const items = filteredOps.map(op=>{
      const btn = h('button',{
        className:'fab-op-btn'+(opsEnabled?'':' fab-op-btn--disabled'),
        title: opsEnabled ? 'Double-clic pour déclencher' : 'Commencez un dossier pour saisir des opérations',
        disabled: !opsEnabled,
      },
        h('span',{className:'fab-op-code', style:{color: opsEnabled ? catColor(op.category) : 'var(--muted)'}},op.code),
        h('span',{className:'fab-op-label'},op.label)
      );
      let clickTimer = null;
      btn.addEventListener('click',()=>{
        if(!opsEnabled) return;
        if(clickTimer){
          clearTimeout(clickTimer);
          clickTimer=null;
          handleOpTrigger(op.code, op.label, op.category);
        } else {
          clickTimer = setTimeout(()=>{clickTimer=null;},400);
        }
      });
      return btn;
    });
    if(!items.length) return;
    groups.push(
      h('div',{className:'fab-ops-group'},
        h('div',{className:'fab-ops-label'},CAT_LABELS[cat]||cat),
        ...items
      )
    );
  });

  if(!opsEnabled){
    groups.unshift(
      h('div',{style:{padding:'10px 8px 8px',fontSize:'11px',color:'var(--muted)',
        background:'rgba(255,255,255,.03)',borderRadius:'6px',margin:'0 0 8px',
        borderLeft:'2px solid var(--border)',lineHeight:'1.5'}},
        S.etat==='sans_session' ? '👋 Commencez par enregistrer votre arrivée'
        : S.etat==='arrive' ? '📂 Sélectionnez un dossier pour commencer la saisie'
        : S.etat==='fin_dossier' ? '✅ Dossier clôturé — démarrez un nouveau ou partez'
        : '⏳ En attente…'
      )
    );
  }

  const machineName = S.machine ? S.machine.nom : (S.user&&S.user.machine_id?'Machine liée':'Sans machine');
  const userName = S.user ? S.user.nom : '';

  return h('nav',{className:'fab-sidebar'},
    h('div',{className:'fab-sidebar-head'},
      h('div',{className:'fab-sidebar-brand'},'Saisie',h('span',null,' Prod')),
      h('div',{className:'fab-sidebar-sub'},'by SIFA')
    ),
    h('div',{className:'fab-sidebar-list'},...groups),
    h('div',{className:'fab-sidebar-bottom'},
      h('div',{className:'fab-user-chip'},
        h('div',{className:'fab-user-name'},userName),
        h('div',{className:'fab-user-machine'},machineName)
      ),
      h('button',{className:'fab-back-btn',onClick:()=>{window.location.href='/'}},
        '← Retour ',
        h('span',{className:'wm'},'My',h('span',null,'Sifa'))
      )
    )
  );
}

/* ── Op trigger logic ────────────────────────────────────────── */
function handleOpTrigger(code, label, cat){
  // Opérations nécessitant une action spéciale
  if(code==='01'){
    // Début dossier → picker dossier
    set({showDossierPicker:true, _pendingPickerOp:{code,label}, pickerQuery:''});
    loadDossiers();
    return;
  }
  if(code==='89'){
    // Fin dossier → modal metrage + étiquettes
    set({showFinModal:true, metrageFinVal:'', nbEtiquettes:''});
    return;
  }
  if(code==='86'||code==='87'||code==='88'||code==='03'){
    // Actions directes
    triggerOp(code, label);
    return;
  }
  // Toutes les autres : direct
  if(['arret','calage','appro','nettoyage','pause','technique'].includes(cat)){
    triggerOp(code, label);
    return;
  }
  triggerOp(code, label);
}

/* ── Main table ──────────────────────────────────────────────── */
/* ── Tab navigation ──────────────────────────────────────────── */
function switchFabTab(tab){
  if(tab!=='traca' && S.tracaScanning) tracaStopCamera();
  set({fabTab:tab});
  if(tab==='traca' && S.tracaMatieres.length===0) loadMatieres();
}

/* ── Print panel ─────────────────────────────────────────────── */
function _fabPrintWin(title, pageSize, css, bodyHtml){
  const w = window.open('','_blank','width=800,height=600');
  if(!w) return;
  w.document.write('<!DOCTYPE html><html><head><meta charset="UTF-8"><title>'+title+'</title><style>'
    +'@page{size:'+pageSize+';margin:0}body{margin:0;padding:0;font-family:Arial,sans-serif}'+css+'</style></head><body>'
    +bodyHtml+'<script>window.onload=function(){window.focus();window.print();}<\/script></body></html>');
  w.document.close();
}

function _fabInp(id, label, placeholder, value){
  return '<div style="margin-bottom:10px"><label style="font-size:11px;font-weight:700;display:block;margin-bottom:3px">'+label+'</label>'
    +'<input id="'+id+'" type="text" value="'+String(value||'').replace(/"/g,'&quot;')+'" placeholder="'+placeholder+'" '
    +'style="width:100%;padding:8px 10px;border:1.5px solid #ccc;border-radius:6px;font-size:13px;font-family:inherit;box-sizing:border-box"></div>';
}

function openFabPrint(type){
  const dos = S.dossier;
  const ref = dos ? dos.reference : '';
  const client = dos ? (dos.client||'') : '';

  if(type==='id_bobine'){
    // Formulaire : ref + étiq/bobine + format
    const form = '<div style="font-family:Arial,sans-serif;padding:20px;max-width:380px">'
      +'<h3 style="margin:0 0 16px;font-size:15px">Identification bobine</h3>'
      +_fabInp('ref','Référence dossier','ex : 9931521',ref)
      +_fabInp('client','Client','ex : Acme',client)
      +'<div style="margin-bottom:10px"><label style="font-size:11px;font-weight:700;display:block;margin-bottom:3px">Format papier</label>'
      +'<select id="fmt" style="width:100%;padding:8px 10px;border:1.5px solid #ccc;border-radius:6px;font-size:13px">'
      +'<option value="40x20">40×20 mm</option><option value="40x30">40×30 mm</option></select></div>'
      +_fabInp('etiq','Étiquettes / bobine','ex : 500','')
      +'<button onclick="doPrint()" style="background:#0891b2;color:#fff;border:none;padding:10px 20px;border-radius:8px;font-size:13px;font-weight:700;cursor:pointer;width:100%">🖨 Imprimer</button></div>'
      +'<script>function doPrint(){'
      +'const ref=document.getElementById("ref").value.trim();'
      +'const client=document.getElementById("client").value.trim();'
      +'const etiq=document.getElementById("etiq").value.trim();'
      +'const fmt=document.getElementById("fmt").value;'
      +'const w=fmt==="40x30"?"40mm":"40mm";const h=fmt==="40x30"?"30mm":"20mm";'
      +'const pw=window.open("","_blank","width=600,height=400");'
      +'pw.document.write(\'<!DOCTYPE html><html><head><meta charset="UTF-8"><style>@page{size:\'+w+\' \'+h+\';margin:0}body{margin:0;padding:2mm;width:\'+w+\';height:\'+h+\';display:flex;flex-direction:column;justify-content:center;font-family:Arial,sans-serif;box-sizing:border-box}.r{font-size:11pt;font-weight:900;margin-bottom:1mm}.c{font-size:8pt;color:#333}.e{font-size:7pt;margin-top:1mm;color:#555}</style></head><body>\'+'
      +'\'<div class="r">\'+ref+\'</div>\'+'
      +'\'<div class="c">\'+client+\'</div>\'+'
      +'(etiq?\'<div class="e">\'+etiq+\' étiq/bob</div>\':"")'
      +'+"<script>window.onload=function(){window.print();}<\/script>"'
      +'+"</body></html>");pw.document.close();}'
      +'<\/script>';
    const fw = window.open('','_blank','width=440,height=340');
    fw.document.write('<!DOCTYPE html><html><head><meta charset="UTF-8"><style>body{font-family:Arial,sans-serif;background:#f9fafb;}</style></head><body>'+form+'</body></html>');
    fw.document.close();
    return;
  }

  if(type==='id_carton'){
    const form = '<div style="font-family:Arial,sans-serif;padding:20px;max-width:380px">'
      +'<h3 style="margin:0 0 16px;font-size:15px">Identification carton</h3>'
      +_fabInp('ref','Référence dossier','ex : 9931521',ref)
      +_fabInp('client','Client','ex : Acme',client)
      +_fabInp('bobs','Bobines / carton','ex : 12','')
      +_fabInp('etiq','Étiquettes / bobine','ex : 500','')
      +'<button onclick="doPrint()" style="background:#0891b2;color:#fff;border:none;padding:10px 20px;border-radius:8px;font-size:13px;font-weight:700;cursor:pointer;width:100%">🖨 Imprimer</button></div>'
      +'<script>function doPrint(){'
      +'const ref=document.getElementById("ref").value.trim();'
      +'const client=document.getElementById("client").value.trim();'
      +'const bobs=document.getElementById("bobs").value.trim();'
      +'const etiq=document.getElementById("etiq").value.trim();'
      +'const pw=window.open("","_blank","width=600,height=400");'
      +'pw.document.write(\'<!DOCTYPE html><html><head><meta charset="UTF-8"><style>@page{size:105mm 50mm;margin:0}body{margin:0;padding:3mm;width:105mm;height:50mm;font-family:Arial,sans-serif;box-sizing:border-box;display:flex;flex-direction:column;justify-content:center}.r{font-size:14pt;font-weight:900;margin-bottom:1mm}.c{font-size:9pt;color:#333}.m{font-size:8pt;color:#555;margin-top:2mm;display:flex;gap:8mm}</style></head><body>\'+'
      +'\'<div class="r">\'+ref+\'</div>\'+'
      +'\'<div class="c">\'+client+\'</div>\'+'
      +'(bobs||etiq?\'<div class="m">\'+(bobs?\'<span>\'+bobs+\' bob/carton</span>\':"")"+(etiq?\'<span>\'+etiq+\' étiq/bob</span>\':"")+"</div>":"")'
      +'+"<script>window.onload=function(){window.print();}<\/script>"'
      +'+"</body></html>");pw.document.close();}'
      +'<\/script>';
    const fw = window.open('','_blank','width=440,height=380');
    fw.document.write('<!DOCTYPE html><html><head><meta charset="UTF-8"><style>body{font-family:Arial,sans-serif;background:#f9fafb;}</style></head><body>'+form+'</body></html>');
    fw.document.close();
    return;
  }

  if(type==='nb_palettes_c'){
    const form = '<div style="font-family:Arial,sans-serif;padding:20px;max-width:380px">'
      +'<h3 style="margin:0 0 16px;font-size:15px">Compteur palette</h3>'
      +_fabInp('ref','Référence dossier','ex : 9931521',ref)
      +_fabInp('total','Nombre total de palettes','ex : 5','')
      +'<button onclick="doPrint()" style="background:#0891b2;color:#fff;border:none;padding:10px 20px;border-radius:8px;font-size:13px;font-weight:700;cursor:pointer;width:100%">🖨 Imprimer (1 étiquette / palette)</button></div>'
      +'<script>function doPrint(){'
      +'const ref=document.getElementById("ref").value.trim();'
      +'const n=parseInt(document.getElementById("total").value)||1;'
      +'let body="";'
      +'for(let i=1;i<=n;i++){'
      +'body+=\'<div class="lbl"><div class="ref">\'+ref+\'</div><div class="pal">PALETTE</div><div class="cnt">\'+i+\' / \'+n+\'</div></div>\';}'
      +'const pw=window.open("","_blank","width=600,height=400");'
      +'pw.document.write(\'<!DOCTYPE html><html><head><meta charset="UTF-8"><style>@page{size:105mm 50mm;margin:0}.lbl{page-break-after:always;margin:0;padding:3mm;width:105mm;height:50mm;font-family:Arial,sans-serif;box-sizing:border-box;display:flex;flex-direction:column;align-items:center;justify-content:center}.lbl:last-child{page-break-after:auto}.ref{font-size:10pt;font-weight:700;margin-bottom:2mm}.pal{font-size:18pt;font-weight:900;letter-spacing:2px}.cnt{font-size:13pt;font-weight:700;margin-top:3mm;color:#444}</style></head><body>\'+body+\'<script>window.onload=function(){window.print();}<\\/script></body></html>\');'
      +'pw.document.close();}'
      +'<\/script>';
    const fw = window.open('','_blank','width=440,height=320');
    fw.document.write('<!DOCTYPE html><html><head><meta charset="UTF-8"><style>body{font-family:Arial,sans-serif;background:#f9fafb;}</style></head><body>'+form+'</body></html>');
    fw.document.close();
    return;
  }
}

function renderPrintPanel(){
  const machine = S.machine || {};
  const machineName = machine.nom || '';
  const isCohesio = machineName.toLowerCase().includes('coh');

  const cards = [
    {type:'id_bobine', icon:'🧻', name:'Identification bobine', format:'40×20 ou 40×30 mm'},
    {type:'id_carton', icon:'📦', name:'Identification carton', format:'105×50 mm'},
  ];
  if(isCohesio || !machineName){
    cards.push({type:'nb_palettes_c', icon:'🏷', name:'Compteur palette', format:'105×50 mm'});
  }

  return h('div',{className:'fab-main'},
    h('div',{className:'fab-main-head'},
      h('span',{className:'fab-main-title'}, svgIcon('printer',16),' Impressions'),
      h('span',{className:'fab-main-sub'}, machineName || 'Toutes machines')
    ),
    h('div',{className:'fab-panel'},
      S.dossier ? h('div',{style:{fontSize:'12px',color:'var(--muted)',marginBottom:'4px'}},
        '📂 Dossier actif : ',
        h('strong',{style:{color:'var(--accent)'}},S.dossier.reference),
        ' — ',S.dossier.client||''
      ) : h('div',{style:{fontSize:'12px',color:'var(--muted)',marginBottom:'4px'}},
        'Pas de dossier actif — les champs seront vides par défaut'
      ),
      h('div',{className:'fab-print-grid'},
        ...cards.map(c=>h('div',{className:'fab-print-card',onClick:()=>openFabPrint(c.type)},
          h('div',{className:'fab-print-card-icon'},c.icon),
          h('div',{className:'fab-print-card-name'},c.name),
          h('div',{className:'fab-print-card-format'},c.format)
        ))
      )
    )
  );
}

/* ── Traça matières panel ─────────────────────────────────────── */
async function loadMatieres(){
  set({tracaLoading:true});
  try{
    const mid = (S.user&&S.user.machine_id) || S.adminMachineId;
    const url = '/api/fabrication/matieres'+(mid?'?machine_id='+mid:'');
    const d = await apiFetch(url);
    set({tracaMatieres: d.matieres||[]});
  }catch(e){ showToast(e.message,'danger'); }
  finally{ set({tracaLoading:false}); }
}

async function tracaSaveCode(code){
  if(!code||!code.trim()) return;
  const clean = code.trim();
  set({tracaAutoSaving:true});
  try{
    const body = {code_barre:clean};
    const mid = (S.user&&S.user.machine_id) || S.adminMachineId;
    if(mid) body.machine_id = mid;
    if(S.dossier) body.no_dossier = S.dossier.reference;
    const d = await apiFetch('/api/fabrication/matieres',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(d.success){
      S.tracaMatieres = [...S.tracaMatieres, d.matiere];
      S.tracaLastCode = clean;
      S.tracaManual = '';
      render();
      showToast('✓ Bobine enregistrée','success');
    }
  }catch(e){ showToast(e.message,'danger'); }
  finally{ set({tracaAutoSaving:false}); }
}

async function tracaDeleteMatiere(id){
  try{
    await apiFetch('/api/fabrication/matieres/'+id,{method:'DELETE'});
    S.tracaMatieres = S.tracaMatieres.filter(m=>m.id!==id);
    render();
  }catch(e){ showToast(e.message,'danger'); }
}

function tracaStartCamera(){
  if(!('BarcodeDetector' in window)){
    showToast('Scanner non disponible — utilisez la saisie manuelle','danger');
    return;
  }
  set({tracaScanning:true});
  render(); // render first so video el exists
  const video = document.getElementById('tracaVideo');
  if(!video){ set({tracaScanning:false}); return; }
  navigator.mediaDevices.getUserMedia({video:{facingMode:'environment'}})
    .then(stream=>{
      video.srcObject = stream;
      S.tracaStream = stream;
      video.play();
      tracaScanLoop(video);
    })
    .catch(err=>{ set({tracaScanning:false}); showToast('Caméra inaccessible','danger'); });
}

function tracaStopCamera(){
  if(S.tracaStream){ S.tracaStream.getTracks().forEach(t=>t.stop()); }
  set({tracaScanning:false, tracaStream:null});
}

async function tracaScanLoop(video){
  const detector = new BarcodeDetector({formats:['code_128','ean_13','ean_8','qr_code','data_matrix','pdf417','code_39','code_93']});
  let lastCode = null; let lastTime = 0;
  async function tick(){
    if(!S.tracaScanning) return;
    try{
      const codes = await detector.detect(video);
      if(codes.length>0){
        const code = codes[0].rawValue;
        const now = Date.now();
        // Anti-dup : même code, même seconde → ignorer
        if(code!==lastCode || now-lastTime>3000){
          lastCode=code; lastTime=now;
          await tracaSaveCode(code);
        }
      }
    }catch(e){}
    if(S.tracaScanning) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

function renderTracaPanel(){
  const matieres = S.tracaMatieres;
  const machineName = (S.machine&&S.machine.nom)||(S.user&&S.user.machine_nom)||'—';

  // Build table rows
  const tableRows = matieres.length
    ? matieres.slice().reverse().map(m=>{
        const dt = m.scanned_at ? new Date(m.scanned_at) : null;
        const timeStr = dt&&!isNaN(dt) ? dt.toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit'}) : '—';
        return h('tr',null,
          h('td',null,h('span',{className:'fab-traca-code'},m.code_barre)),
          h('td',null,m.no_dossier||h('span',{style:{color:'var(--muted)',fontStyle:'italic'}},'—')),
          h('td',null,timeStr),
          h('td',null,h('button',{className:'fab-traca-del',title:'Supprimer',
            onClick:()=>tracaDeleteMatiere(m.id)},svgIcon('trash',12)))
        );
      })
    : [h('tr',null,h('td',{colSpan:'4',className:'fab-traca-empty'},
        S.tracaLoading ? '⏳ Chargement…' : 'Aucune bobine scannée aujourd\'hui'
      ))];

  // Manual input
  const manualInp = h('input',{
    type:'text',className:'fab-traca-manual',
    placeholder:'Code barre manuel (Entrée)',
    value:S.tracaManual||'',
  });
  manualInp.addEventListener('input',e=>{ S.tracaManual=e.target.value; });
  manualInp.addEventListener('keydown',async e=>{
    if(e.key==='Enter'){e.preventDefault();await tracaSaveCode(S.tracaManual);}
  });

  const camBtn = S.tracaScanning
    ? h('button',{className:'fab-btn fab-btn-danger fab-btn-sm',onClick:()=>tracaStopCamera()},
        svgIcon('video-off',14),' Stopper')
    : h('button',{className:'fab-btn fab-btn-primary fab-btn-sm',onClick:()=>tracaStartCamera()},
        svgIcon('camera',14),' Scanner');

  const addBtn = h('button',{
    className:'fab-btn fab-btn-ghost fab-btn-sm',
    disabled:!(S.tracaManual&&S.tracaManual.trim()),
    onClick:()=>tracaSaveCode(S.tracaManual)
  }, svgIcon('plus-circle',14),' Ajouter');

  return h('div',{className:'fab-main'},
    h('div',{className:'fab-main-head'},
      h('span',{className:'fab-main-title'}, svgIcon('scan',16),' Traçabilité matières'),
      S.dossier ? h('span',{style:{fontSize:'12px',color:'var(--accent)',fontWeight:'700'}},
        S.dossier.reference) : null,
      h('span',{className:'fab-main-sub'},machineName)
    ),
    h('div',{className:'fab-traca-layout'},
      // Scan row
      h('div',{className:'fab-traca-scan-row'},
        manualInp,
        addBtn,
        camBtn
      ),
      // Camera preview
      S.tracaScanning ? h('div',{className:'fab-traca-video-wrap'},
        h('video',{id:'tracaVideo',autoplay:true,playsinline:true,muted:true}),
        h('div',{className:'fab-traca-scan-line'})
      ) : null,
      // Status
      S.tracaAutoSaving ? h('div',{className:'fab-traca-status fab-traca-saving'},
        h('div',{className:'fab-spinner',style:{width:'12px',height:'12px',borderWidth:'1.5px'}}),'Enregistrement…'
      ) : h('div',{className:'fab-traca-status'},
        matieres.length+' bobine'+(matieres.length!==1?'s':''),' enregistrée'+(matieres.length!==1?'s':''),' aujourd\'hui',
        S.dossier ? ' — Dossier '+S.dossier.reference : ''
      ),
      // Table
      h('div',{className:'fab-traca-table-wrap'},
        h('table',{className:'fab-traca-table'},
          h('thead',null,h('tr',null,
            h('th',null,'Code barre'),h('th',null,'Dossier'),h('th',null,'Heure'),h('th',null,'')
          )),
          h('tbody',null,...tableRows)
        )
      )
    )
  );
}

function renderMain(){
  if(S.fabTab==='print') return renderPrintPanel();
  if(S.fabTab==='traca') return renderTracaPanel();

  const hasAlert = S.etat==='en_arret' && S.saisies.length>0;
  const arrLen = S.saisies.filter(s=>s.operation_category==='arret').length;

  let alert = null;
  if(S.etat==='en_arret'){
    const last = S.lastSaisie;
    const since = last ? fmtTime(last.date_operation) : '';
    alert = h('div',{className:'fab-alert fab-alert-warn'},
      svgIcon('alert',14),
      'Arrêt en cours depuis '+since+' — '+((S.lastSaisie&&S.lastSaisie.operation)||'')
    );
  }
  const isAdminUserMain = S.user && (S.user.role==='superadmin'||S.user.role==='administration'||S.user.role==='direction');
  if(S.operateur && !S.machine && !isAdminUserMain){
    alert = h('div',{className:'fab-alert fab-alert-warn'},
      svgIcon('alert',14),
      'Aucune machine liée à votre compte — contactez un administrateur'
    );
  }

  const rows = [...S.saisies]; // chronologique : première saisie en haut, dernière en bas

  const tableHead = h('tr',null,
    h('th',null,'Heure'),
    h('th',null,'Code'),
    h('th',null,'Opération'),
    h('th',null,'Métrages'),
    h('th',null,'Commentaire'),
    h('th',null,'')
  );

  const tableBody = rows.length
    ? rows.map((s,i)=>{
        const isLast = i===rows.length-1; // dernière saisie = en bas
        const code = s.operation_code||'';
        const cat = s.operation_category||'';
        const op = OPS[code]||{};
        const chipColor = severityColor(s.operation_severity) || catColor(cat);

        let metrageText = '';
        if(s.metrage_prevu!=null) metrageText += 'Déb. '+fN(s.metrage_prevu)+' m';
        if(s.metrage_reel!=null) metrageText += (metrageText?' | ':'')+' Fin '+fN(s.metrage_reel)+' m';
        if(s.quantite_traitee&&Number(s.quantite_traitee)>0) metrageText += (metrageText?' | ':'')+fN(s.quantite_traitee)+' étiq.';

        const commentBtn = h('button',{
          className:'fab-comment-btn',
          title:'Ajouter/modifier un commentaire',
          onClick:()=>set({showCommentModal:true, commentSaisieId:s.id, commentText:s.commentaire||''})
        }, svgIcon(s.commentaire?'edit':'message-square',13));

        return h('tr',{className:'fab-table-row'+(isLast?' fab-row-last':'')},
          h('td',null, h('span',{className:'fab-time'}, fmtTime(s.date_operation))),
          h('td',null,
            h('span',{className:'fab-op-chip',style:{background:chipColor+'22',color:chipColor}},
              h('span',{className:'fab-op-chip-code'},code)
            )
          ),
          h('td',null, h('span',{style:{color:isLast?'var(--text)':'var(--text2)',fontWeight:isLast?'700':'500'}},
            op.label||s.operation||code)),
          h('td',null, metrageText ? h('span',{className:'fab-metrage'},metrageText) : null),
          h('td',null, s.commentaire
            ? h('span',{className:'fab-comment-cell',title:s.commentaire}, s.commentaire)
            : h('span',{style:{color:'var(--muted)',fontSize:'11px'}},'—')
          ),
          h('td',null, commentBtn)
        );
      })
    : [h('tr',null,
        h('td',{colspan:'6'},
          h('div',{className:'fab-empty'},
            h('div',{className:'fab-empty-icon'},'📋'),
            S.etat==='sans_session'
              ? 'Commencez par enregistrer votre arrivée'
              : 'Aucune saisie aujourd\'hui'
          )
        )
      )];

  return h('div',{className:'fab-main'},
    h('div',{className:'fab-main-head'},
      h('span',{className:'fab-main-title'}, S.dossier
        ? ('Dossier : '+S.dossier.reference)
        : "Saisie de production"
      ),
      alert ? null : null,
      h('span',{className:'fab-etat-badge '+etatClass(S.etat)}, etatLabel(S.etat)),
      h('span',{className:'fab-main-sub'}, S.saisies.length+' saisie'+(S.saisies.length!==1?'s':'')+' aujourd\'hui')
    ),
    alert,
    h('div',{className:'fab-table-wrap'},
      h('table',{className:'fab-table'},
        h('thead',null, tableHead),
        h('tbody',null, ...tableBody)
      )
    )
  );
}

/* ── Footer ──────────────────────────────────────────────────── */
function renderFooter(){
  // Left: dossier info
  let infoSection;
  if(S.dossier){
    const d = S.dossier;
    const metas = [];
    if(d.laize) metas.push({label:'Laize',val:d.laize+' mm'});
    if(d.format_l&&d.format_h) metas.push({label:'Format',val:d.format_l+' × '+d.format_h+' mm'});
    if(d.date_livraison) metas.push({label:'Livraison',val:fmtDate(d.date_livraison)});
    if(d.numero_of) metas.push({label:'N° OF',val:d.numero_of});
    if(d.machine_nom) metas.push({label:'Machine',val:d.machine_nom});

    infoSection = h('div',{className:'fab-footer-info'},
      h('div',{className:'fab-dossier-ref'},d.reference||'—'),
      h('div',{className:'fab-dossier-client'},d.client||'Client non renseigné'),
      h('div',{className:'fab-dossier-meta'},
        ...metas.map(m=>h('span',{className:'fab-meta-item'},
          h('span',{className:'fab-meta-label'},m.label),
          ' ',m.val
        ))
      ),
      d.commentaire ? h('div',{style:{fontSize:'11px',color:'var(--muted)',marginTop:'4px',
        overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap',maxWidth:'280px'}},
        '💬 '+d.commentaire) : null
    );
  } else {
    infoSection = h('div',{className:'fab-footer-info'},
      h('div',{className:'fab-no-dossier'}, S.etat==='en_cours_production'||S.etat==='en_arret'
        ? 'Dossier actif (données non trouvées dans le planning)'
        : 'Aucun dossier actif')
    );
  }

  // Center: context buttons — machine à états stricte
  const btns = [];
  const e = S.etat;

  // Résoudre la machine effective (liée au compte ou sélectionnée par l'admin)
  const isAdminUser = S.user && (S.user.role==='superadmin'||S.user.role==='administration'||S.user.role==='direction');
  // Admin/direction/superadmin : machine liée au compte OU machine sélectionnée via le sélecteur
  const hasMachine = !!(S.user && S.user.machine_id) || !!(isAdminUser && S.adminMachineId);

  // ── Sélecteur machine admin ──────────────────────────────────────────────
  // Affiché dans la zone centre si l'utilisateur est admin et n'a pas de machine liée
  let machineSelectorRow = null;
  if(isAdminUser && !(S.user && S.user.machine_id)){
    const sel = h('select',{
      style:{
        background:'var(--bg)',border:'1.5px solid var(--border)',borderRadius:'8px',
        padding:'7px 10px',fontSize:'12px',color:'var(--text)',fontFamily:'inherit',
        outline:'none',cursor:'pointer',minWidth:'160px',
      }
    },
      h('option',{value:''},'— Sélectionner une machine —'),
      ...S.machines.map(m=>h('option',{value:String(m.id), selected: S.adminMachineId===m.id},
        m.nom+(m.dernier_metrage!=null?' ('+Math.round(m.dernier_metrage).toLocaleString('fr-FR')+' m)':'')
      ))
    );
    sel.addEventListener('change', async e=>{
      const mid = e.target.value ? parseInt(e.target.value) : null;
      set({adminMachineId: mid});
      await loadSession();
    });
    machineSelectorRow = h('div',{style:{display:'flex',alignItems:'center',gap:'8px',marginBottom:'4px'}},
      svgIcon('tool',13),
      h('span',{style:{fontSize:'11px',color:'var(--muted)'}},'Machine :'),
      sel
    );
  }

  // ── État : pas encore arrivé (ou après départ) ──
  if(e==='sans_session'||e==='loading'){
    btns.push(h('button',{
      className:'fab-btn fab-btn-primary',
      disabled: e==='loading' || !hasMachine,
      title: !hasMachine ? 'Sélectionnez une machine avant de commencer' : '',
      onClick:()=>triggerOp('86','Arrivée personnel')
    }, svgIcon('user',16),' Arrivée personnel'));
  }

  // ── État : arrivé, pas de dossier actif ──
  else if(e==='arrive'){
    btns.push(h('button',{
      className:'fab-btn fab-btn-success',
      onClick:()=>handleOpTrigger('01','Début dossier','personnel')
    }, svgIcon('plus-circle',16),' Début de dossier'));
    btns.push(h('button',{
      className:'fab-btn fab-btn-muted fab-btn-sm',
      onClick:()=>triggerOp('87','Départ personnel')
    }, svgIcon('log-out',14),' Départ personnel'));
  }

  // ── État : en production (dossier actif, aucun arrêt) ──
  else if(e==='en_cours_production'){
    btns.push(h('button',{
      className:'fab-btn fab-btn-warn',
      onClick:()=>handleOpTrigger('89','Fin dossier','personnel')
    }, svgIcon('flag',16),' Fin de dossier'));
  }

  // ── État : arrêt en cours ──
  else if(e==='en_arret'){
    btns.push(h('button',{
      className:'fab-btn fab-btn-success',
      onClick:()=>triggerOp('88','Reprise production')
    }, svgIcon('play',16),' Reprise production'));
    btns.push(h('button',{
      className:'fab-btn fab-btn-warn fab-btn-sm',
      onClick:()=>handleOpTrigger('89','Fin dossier','personnel')
    }, svgIcon('flag',14),' Fin de dossier'));
  }

  // ── État : dossier terminé ──
  else if(e==='fin_dossier'){
    btns.push(h('button',{
      className:'fab-btn fab-btn-success',
      onClick:()=>handleOpTrigger('01','Début dossier','personnel')
    }, svgIcon('plus-circle',16),' Nouveau dossier'));
    btns.push(h('button',{
      className:'fab-btn fab-btn-muted fab-btn-sm',
      onClick:()=>triggerOp('87','Départ personnel')
    }, svgIcon('log-out',14),' Départ personnel'));
  }

  const centerSection = h('div',{className:'fab-footer-actions'},
    machineSelectorRow,
    h('div',{className:'fab-footer-btns'},...btns)
  );

  // Right: search + comment
  const searchInput = h('input',{
    type:'text',className:'fab-search-input',
    placeholder:'Code ou libellé op. (Entrée)',
    value: S.searchQuery||'',
  });
  searchInput.addEventListener('input',e=>{ S.searchQuery=e.target.value; });
  searchInput.addEventListener('keydown',e=>{
    if(e.key==='Enter'){
      e.preventDefault();
      handleSearchSubmit(S.searchQuery);
    }
  });

  const lastId = S.lastSaisie ? S.lastSaisie.id : null;
  const commentBtn = h('button',{
    className:'fab-btn fab-btn-ghost fab-btn-sm',
    disabled: !lastId,
    title:'Commenter la dernière saisie',
    onClick:()=>{ if(lastId) set({showCommentModal:true,commentSaisieId:lastId,commentText:(S.lastSaisie&&S.lastSaisie.commentaire)||''}); }
  }, svgIcon('message-square',14),' Commenter');

  const toolsSection = h('div',{className:'fab-footer-tools'},
    h('div',{className:'fab-search-wrap'},
      searchInput,
    ),
    h('div',{className:'fab-comment-row'},
      commentBtn
    )
  );

  // Tab nav (always visible at bottom of footer)
  const tabNav = h('div',{className:'fab-tab-nav'},
    h('button',{className:'fab-tab-btn'+(S.fabTab==='saisie'?' active':''),onClick:()=>switchFabTab('saisie')},
      svgIcon('edit',16),'Saisie'),
    h('button',{className:'fab-tab-btn'+(S.fabTab==='print'?' active':''),onClick:()=>switchFabTab('print')},
      svgIcon('printer',16),'Imprimer'),
    h('button',{className:'fab-tab-btn'+(S.fabTab==='traca'?' active':''),onClick:()=>switchFabTab('traca')},
      svgIcon('scan',16),'Traça')
  );

  // Wrapper centré commun pour la tab nav
  const tabNavWrap = h('div',{style:{display:'flex',justifyContent:'center',
    alignItems:'center',padding:'6px 0 8px'}}, tabNav);

  // Theme toggle button
  const isLight = document.body.classList.contains('light');
  const themeBtn = h('button',{
    className:'fab-theme-btn',
    onClick:()=>{
      document.body.classList.toggle('light');
      localStorage.setItem('theme',document.body.classList.contains('light')?'light':'dark');
      render();
    }
  }, svgIcon(isLight?'sun':'moon',14), isLight?'Clair':'Sombre');

  // When on non-saisie tabs, show a minimal status line instead of full footer
  if(S.fabTab!=='saisie'){
    const machineName = (S.machine&&S.machine.nom)||(S.user&&S.user.machine_nom)||'—';
    const dossierLabel = S.dossier ? S.dossier.reference : 'Aucun dossier';
    return h('div',{className:'fab-footer',style:{gridTemplateColumns:'1fr',padding:'4px 16px 0'}},
      h('div',{style:{display:'flex',alignItems:'center',justifyContent:'center',gap:'16px',
        fontSize:'11px',color:'var(--muted)',padding:'4px 0'}},
        h('span',null, svgIcon('tool',11),' '+machineName),
        h('span',{style:{color:'var(--border)'}},'/'),
        h('span',null,dossierLabel),
        h('span',{style:{color:'var(--border)'}},'/'),
        h('span',{className:'fab-etat-badge '+etatClass(S.etat),style:{fontSize:'9px',padding:'2px 8px'}}, etatLabel(S.etat)),
        h('span',{style:{color:'var(--border)'}},'/'),
        themeBtn
      ),
      tabNavWrap
    );
  }

  return h('div',{className:'fab-footer'},
    infoSection,
    h('div',{className:'fab-footer-actions',style:{display:'flex',flexDirection:'column',alignItems:'center',gap:'8px'}},
      machineSelectorRow,
      h('div',{className:'fab-footer-btns'},...btns),
      h('div',{style:{display:'flex',alignItems:'center',gap:'8px'}}, tabNavWrap, themeBtn)
    ),
    toolsSection
  );
}

function handleSearchSubmit(query){
  if(!query||!query.trim()) return;
  const q = query.trim().toLowerCase();
  let found = null;

  // Try numeric code first
  if(/^\d+$/.test(q)){
    const padded = q.padStart(2,'0');
    if(OPS[padded]) found = {code:padded, ...OPS[padded]};
    else if(OPS[q]) found = {code:q, ...OPS[q]};
  }

  // Try label match
  if(!found){
    const entries = Object.entries(OPS);
    // Exact match
    let m = entries.find(([c,o])=>o.label.toLowerCase()===q);
    if(!m) m = entries.find(([c,o])=>o.label.toLowerCase().includes(q));
    if(!m) m = entries.find(([c,o])=>c.startsWith(q));
    if(m) found = {code:m[0], ...m[1]};
  }

  if(found){
    // Vérifier qu'une machine est sélectionnée avant de déclencher l'opération
    const hasMachine = S.machine || S.adminMachineId || (S.user && S.user.machine_nom);
    if(!hasMachine && found.code!=='86' && found.code!=='87'){
      showToast('Sélectionnez une machine avant de saisir une opération','warn');
      return;
    }
    set({searchQuery:''});
    handleOpTrigger(found.code, found.label, found.category);
  } else {
    showToast('Opération introuvable : "'+query+'"','danger');
  }
}

/* ── Modals ──────────────────────────────────────────────────── */

// Variable locale pour la query du picker — mise à jour sans re-render complet
let _pickerQ = '';

function _buildPickerItems(q){
  const lq = (q||'').toLowerCase();
  const filtered = S.dossiers.filter(d=>{
    if(!lq) return true;
    return (d.reference||'').toLowerCase().includes(lq)||
           (d.client||'').toLowerCase().includes(lq)||
           (d.description||'').toLowerCase().includes(lq);
  });
  if(!filtered.length){
    const empty = document.createElement('div');
    empty.className = 'fab-picker-empty';
    empty.textContent = S.dossiers.length===0
      ? 'Aucun dossier disponible dans le planning'
      : 'Aucun dossier ne correspond à la recherche';
    return [empty];
  }
  return filtered.map(d=>{
    const refProd = d.ref_produit||d.description||'';
    const fmtParts = [];
    if(d.format_l) fmtParts.push(d.format_l+' mm');
    if(d.format_h) fmtParts.push(d.format_h+' mm');
    if(d.laize && !fmtParts.length) fmtParts.push('Laize '+d.laize+' mm');
    const line2 = [refProd, fmtParts.join(' x ')].filter(Boolean).join('  —  ');
    const metaParts = [];
    if(d.machine_nom) metaParts.push(d.machine_nom);
    if(d.date_livraison) metaParts.push('Livr. '+fmtDate(d.date_livraison));
    if(d.duree_heures) metaParts.push(d.duree_heures+' h');
    return h('div',{className:'fab-picker-item',onClick:()=>selectDossier(d)},
      h('div',{className:'fab-picker-line1'},
        h('span',{className:'fab-picker-ref'},d.reference),
        h('span',{className:'fab-picker-sep'},'|'),
        h('span',{className:'fab-picker-client'},d.client||'Client non renseigné')
      ),
      line2 ? h('div',{className:'fab-picker-line2'},line2) : null,
      metaParts.length ? h('div',{className:'fab-picker-meta'},
        ...metaParts.map(s=>h('span',null,s))
      ) : null
    );
  });
}

function renderDossierPickerModal(){
  // Réinitialise la query locale à l'ouverture du picker
  _pickerQ = '';

  const listEl = h('div',{className:'fab-picker-list',id:'fab-picker-list-inner'},
    ..._buildPickerItems(''));

  const searchInp = h('input',{type:'text',className:'fab-picker-search',
    placeholder:'Rechercher un dossier…'});

  searchInp.addEventListener('input',e=>{
    _pickerQ = e.target.value;
    // Met à jour uniquement la liste — sans toucher au reste de la page
    const list = document.getElementById('fab-picker-list-inner');
    if(list){
      list.innerHTML = '';
      _buildPickerItems(_pickerQ).forEach(item=>list.appendChild(item));
    }
  });

  // Autofocus à l'ouverture (après insertion dans le DOM)
  requestAnimationFrame(()=>{ searchInp.focus(); });

  return h('div',{className:'fab-modal-overlay',onClick:(e)=>{if(e.target===e.currentTarget)set({showDossierPicker:false});}},
    h('div',{className:'fab-modal'},
      h('div',{className:'fab-modal-title'},icon('plus-circle',18),' Sélectionner le dossier'),
      h('div',{className:'fab-modal-sub'},
        'Choisissez le dossier à démarrer parmi ceux disponibles dans le planning.'
      ),
      searchInp,
      listEl,
      h('div',{className:'fab-modal-btns'},
        h('button',{className:'fab-btn fab-btn-muted fab-btn-sm',
          onClick:()=>set({showDossierPicker:false})},'Annuler')
      )
    )
  );
}

function selectDossier(dossier){
  // After selecting dossier, ask for metrage début
  set({showDossierPicker:false, _selectedDossier:dossier, showDebutModal:true, metrageDebut:''});
}

function renderDebutModal(){
  const d = S._selectedDossier;
  const inp = h('input',{type:'number',placeholder:'Ex: 15000',step:'1',min:'0',
    style:{textAlign:'right'}});
  inp.value = S.metrageDebut||'';
  inp.addEventListener('input',e=>{ S.metrageDebut=e.target.value; });
  inp.focus();

  const submit = async()=>{
    const dos = S._selectedDossier;
    if(!dos){ set({showDebutModal:false}); return; }

    // Validation locale : métrage < dernier_metrage machine
    const machine = S.machine || (S.adminMachineId && S.machines.find(m=>m.id===S.adminMachineId));
    const dernierM = machine ? machine.dernier_metrage : null;
    const mDebut = S.metrageDebut ? parseFloat(String(S.metrageDebut).replace(',','.')) : null;
    if(mDebut !== null && dernierM !== null && mDebut < dernierM){
      showToast('Métrage invalide : le compteur était à '+Math.round(dernierM).toLocaleString('fr-FR')+' m — valeur saisie trop petite','danger');
      return;
    }

    set({showDebutModal:false, loading:true});
    try{
      const body = {
        operation:'01 - Début dossier',
        no_dossier: dos.reference,
        machine: dos.machine_nom||'',
        client: dos.client||'',
        designation: dos.description||'',
      };
      if(mDebut !== null) body.metrage_debut = mDebut;
      if(S.adminMachineId) body.machine_id = S.adminMachineId;
      const r = await apiFetch('/api/fabrication/saisie',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify(body),
      });
      if(r&&r.success){
        showToast('Début de dossier enregistré');
        await loadSession();
      }
    }catch(e){
      showToast('Erreur : '+e.message,'danger');
    }finally{
      set({loading:false, _selectedDossier:null, metrageDebut:''});
    }
  };

  return h('div',{className:'fab-modal-overlay',onClick:(e)=>{if(e.target===e.currentTarget)set({showDebutModal:false});}},
    h('div',{className:'fab-modal'},
      h('div',{className:'fab-modal-title'},'📦 Début de dossier'),
      d ? h('div',{className:'fab-modal-sub'},
        'Dossier : ',h('strong',null,d.reference),
        d.client ? (' — '+d.client) : ''
      ) : null,
      h('div',{className:'fab-field'},
        h('label',null,(()=>{
          const m = S.machine||(S.adminMachineId&&S.machines.find(x=>x.id===S.adminMachineId));
          const dm = m&&m.dernier_metrage!=null?'  (dernier enregistré : '+Math.round(m.dernier_metrage).toLocaleString('fr-FR')+' m)':'';
          return 'Métrage total de la machine — compteur au début, en mètres'+dm;
        })()),
        inp
      ),
      h('div',{className:'fab-modal-btns'},
        h('button',{className:'fab-btn fab-btn-muted fab-btn-sm',
          onClick:()=>set({showDebutModal:false, _selectedDossier:null})},
          'Annuler'),
        h('button',{className:'fab-btn fab-btn-success',
          onClick:submit},
          svgIcon('play',15),' Démarrer')
      )
    )
  );
}

function renderFinModal(){
  const metInp = h('input',{type:'number',placeholder:'Ex: 14200',step:'1',min:'0',
    style:{textAlign:'right'}});
  metInp.value = S.metrageFinVal||'';
  metInp.addEventListener('input',e=>{ S.metrageFinVal=e.target.value; });

  const etiqInp = h('input',{type:'number',placeholder:'Ex: 50000',step:'1',min:'0',
    style:{textAlign:'right'}});
  etiqInp.value = S.nbEtiquettes||'';
  etiqInp.addEventListener('input',e=>{ S.nbEtiquettes=e.target.value; });

  const submit = async()=>{
    const mFin = S.metrageFinVal ? parseFloat(String(S.metrageFinVal).replace(',','.')) : null;

    // Validation locale 1 : métrage fin < dernier_metrage machine
    const machine = S.machine || (S.adminMachineId && S.machines.find(m=>m.id===S.adminMachineId));
    const dernierM = machine ? machine.dernier_metrage : null;
    if(mFin !== null && dernierM !== null && mFin < dernierM){
      showToast('Métrage invalide : le compteur était à '+Math.round(dernierM).toLocaleString('fr-FR')+' m — valeur saisie trop petite','danger');
      return;
    }

    // Validation locale 2 : métrage fin < métrage début du dossier
    if(mFin !== null && S.saisies.length){
      const debutRow = [...S.saisies].reverse().find(s=>s.operation_code==='01'&&s.metrage_prevu!=null);
      if(debutRow && mFin < parseFloat(debutRow.metrage_prevu)){
        showToast('Métrage fin ('+Math.round(mFin).toLocaleString('fr-FR')+' m) inférieur au début de dossier ('+Math.round(debutRow.metrage_prevu).toLocaleString('fr-FR')+' m)','danger');
        return;
      }
    }

    set({showFinModal:false, loading:true});
    try{
      const body = {
        operation:'89 - Fin dossier',
        no_dossier: S.dossier ? S.dossier.reference : null,
        machine: S.machine ? S.machine.nom : null,
        client: S.dossier ? (S.dossier.client||'') : '',
        designation: S.dossier ? (S.dossier.description||'') : '',
      };
      if(mFin !== null) body.metrage_fin = mFin;
      if(S.nbEtiquettes) body.qte_etiquettes = parseFloat(String(S.nbEtiquettes).replace(',','.'));
      if(S.adminMachineId) body.machine_id = S.adminMachineId;
      const r = await apiFetch('/api/fabrication/saisie',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify(body),
      });
      if(r&&r.success){
        showToast('Fin de dossier enregistrée');
        await loadSession();
      }
    }catch(e){
      showToast('Erreur : '+e.message,'danger');
    }finally{
      set({loading:false, metrageFinVal:'', nbEtiquettes:''});
    }
  };

  return h('div',{className:'fab-modal-overlay',onClick:(e)=>{if(e.target===e.currentTarget)set({showFinModal:false});}},
    h('div',{className:'fab-modal'},
      h('div',{className:'fab-modal-title'},'🏁 Fin de dossier'),
      S.dossier ? h('div',{className:'fab-modal-sub'},
        'Clôture du dossier ',h('strong',null,S.dossier.reference),
        S.dossier.client ? (' — '+S.dossier.client) : ''
      ) : null,
      h('div',{className:'fab-field'},
        h('label',null,(()=>{
          const m = S.machine||(S.adminMachineId&&S.machines.find(x=>x.id===S.adminMachineId));
          const dm = m&&m.dernier_metrage!=null?'  (dernier enregistré : '+Math.round(m.dernier_metrage).toLocaleString('fr-FR')+' m)':'';
          return 'Métrage total de la machine — compteur en fin, en mètres'+dm;
        })()),
        metInp
      ),
      h('div',{className:'fab-field'},
        h('label',null,'Quantité d\'étiquettes produites'),
        etiqInp
      ),
      h('div',{className:'fab-modal-btns'},
        h('button',{className:'fab-btn fab-btn-muted fab-btn-sm',
          onClick:()=>set({showFinModal:false})},'Annuler'),
        h('button',{className:'fab-btn fab-btn-danger',
          onClick:submit},
          svgIcon('flag',15),' Clôturer le dossier')
      )
    )
  );
}

function renderCommentModal(){
  const ta = h('textarea',{placeholder:'Votre commentaire…',rows:'3'});
  ta.value = S.commentText||'';
  ta.addEventListener('input',e=>{ S.commentText=e.target.value; });
  setTimeout(()=>ta.focus(),50);

  return h('div',{className:'fab-modal-overlay',onClick:(e)=>{if(e.target===e.currentTarget)set({showCommentModal:false});}},
    h('div',{className:'fab-modal'},
      h('div',{className:'fab-modal-title'},svgIcon('message-square',18),' Commenter la saisie'),
      h('div',{className:'fab-modal-sub'},'Ce commentaire sera visible dans la fiche de production MyProd.'),
      h('div',{className:'fab-field'},
        h('label',null,'Commentaire'),
        ta
      ),
      h('div',{className:'fab-modal-btns'},
        h('button',{className:'fab-btn fab-btn-muted fab-btn-sm',
          onClick:()=>set({showCommentModal:false})},'Annuler'),
        h('button',{className:'fab-btn fab-btn-primary',
          onClick:saveComment},
          svgIcon('check',15),' Enregistrer')
      )
    )
  );
}

/* ── Mobile topbar ───────────────────────────────────────────── */
function renderTopbar(){
  return h('div',{className:'fab-topbar'},
    h('button',{className:'fab-topbar-btn',onClick:()=>{
      S.sidebarOpen=!S.sidebarOpen;
      document.body.classList.toggle('sb-open',S.sidebarOpen);
      render();
    }},icon('menu',20)),
    h('span',{className:'fab-topbar-title'},'Saisie Production'),
    h('button',{className:'fab-topbar-btn',onClick:()=>{window.location.href='/'}},icon('home',18))
  );
}

/* ── Loading overlay ─────────────────────────────────────────── */
function renderLoading(){
  return h('div',{className:'fab-loading'},
    h('div',{className:'fab-spinner'}),
    'Enregistrement…'
  );
}

/* ── Main render ─────────────────────────────────────────────── */
function render(){
  const root = document.getElementById('root');
  root.innerHTML = '';

  if(S.etat==='loading' && !S.user){
    root.appendChild(h('div',{className:'fab-loading'},
      h('div',{className:'fab-spinner'}),
      'Chargement…'
    ));
    return;
  }

  root.appendChild(renderSidebar());
  root.appendChild(renderMain());
  root.appendChild(renderFooter());
  root.appendChild(renderTopbar());

  const overlay = h('div',{className:'fab-sidebar-overlay',onClick:()=>{
    S.sidebarOpen=false;
    document.body.classList.remove('sb-open');
    render();
  }});
  root.appendChild(overlay);

  if(S.showDossierPicker) root.appendChild(renderDossierPickerModal());
  if(S.showDebutModal)    root.appendChild(renderDebutModal());
  if(S.showFinModal)      root.appendChild(renderFinModal());
  if(S.showCommentModal)  root.appendChild(renderCommentModal());

  if(S.loading) root.appendChild(renderLoading());

  if(S.toast){
    const c = S.toastType==='danger'?'var(--danger)':'var(--success)';
    root.appendChild(h('div',{className:'fab-toast',style:{borderLeft:'3px solid '+c,color:c}},
      S.toast
    ));
  }
}

/* ── Auth + init ─────────────────────────────────────────────── */
async function init(){
  // Theme
  if(localStorage.getItem('theme')==='light') document.body.classList.add('light');

  render(); // show loading

  // Auth check
  let user = null;
  try{
    user = await apiFetch('/api/auth/me');
  }catch(e){
    window.location.href='/';
    return;
  }
  if(!user){ window.location.href='/'; return; }
  set({user});

  // Charger la liste des machines (nécessaire pour le sélecteur admin)
  const isAdm = user.role==='superadmin'||user.role==='administration'||user.role==='direction';
  if(isAdm && !user.machine_id){
    await loadMachines();
  }

  // Load session
  await loadSession();
}

init();
</script>
</body>
</html>"""

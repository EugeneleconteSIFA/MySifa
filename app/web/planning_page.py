"""SIFA — Page Planning v1.1 (standalone)

Ajouter dans main.py :
    from frontend.planning_page import router as planning_page_router
    app.include_router(planning_page_router)

Accès : /planning  ou  /planning?machine=<id SQLite réel>
"""

from typing import Optional

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from services.auth_service import get_current_user, user_has_app_access
from config import APP_META_DESCRIPTION, APP_PLANNING_PAGE_TITLE, APP_VERSION, THEME_COLOR_META
from app.web.access_denied import access_denied_response

router = APIRouter()


@router.get("/planning", response_class=HTMLResponse)
def planning_page(request: Request, machine: Optional[int] = None):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            nxt = "/planning"
            if machine is not None:
                nxt = f"/planning?machine={machine}"
            return RedirectResponse(url=f"/?next={nxt}", status_code=302)
        raise
    if not user_has_app_access(user, "planning"):
        return access_denied_response("Planning (MyProd)")
    # 0 = laisser le JS choisir l’id réel après /api/planning/machines (évite de forcer
    # ?machine=1 implicite alors que l’id SQLite « Cohésio 1 » n’est pas 1 en prod).
    ssr_mid = str(machine) if machine is not None else "0"
    html = (
        PLANNING_HTML.replace("__MACHINE_ID__", ssr_mid)
        .replace("__PLANNING_TITLE__", APP_PLANNING_PAGE_TITLE)
        .replace("__META_DESCRIPTION__", APP_META_DESCRIPTION)
        .replace("__THEME_COLOR__", THEME_COLOR_META)
        .replace("__V_LABEL__", f"v{APP_VERSION}")
    )
    return HTMLResponse(content=html)


PLANNING_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="__META_DESCRIPTION__">
<meta name="theme-color" content="__THEME_COLOR__">
<link rel="icon" type="image/png" sizes="512x512" href="/static/mys_icon_512.png">
<link rel="apple-touch-icon" href="/static/mys_icon_180.png">
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<title>__PLANNING_TITLE__</title>
<script src="https://cdn.sheetjs.com/xlsx-0.20.3/package/dist/xlsx.full.min.js"></script>
<link rel="stylesheet" href="/static/support_widget.css">
<style>
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;
  --muted:#94a3b8;--accent:#22d3ee;--accent-bg:rgba(34,211,238,0.12);
  --success:#34d399;--warn:#fbbf24;--danger:#f87171;
  --c1:#22d3ee;--c2:#a78bfa;--c3:#34d399;--c4:#fbbf24;--c5:#f87171;
  --blue:#38bdf8;--purple:#a78bfa;--mono:ui-monospace,'Cascadia Code',monospace;--sans:'Segoe UI',system-ui,sans-serif;
  --bg-dark:#080c12;--border2:#334155;--dim:#cbd5e1;
  --green:var(--success);--red:var(--danger);--amber:var(--warn);
}
body.light{
  --bg:#f1f5f9;--card:#ffffff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;
  --muted:#94a3b8;--accent:#0891b2;--accent-bg:rgba(8,145,178,0.10);
  --success:#059669;--warn:#d97706;--danger:#dc2626;
  --c1:#0891b2;--c2:#7c3aed;--c3:#059669;--c4:#d97706;--c5:#dc2626;
  --blue:#0ea5e9;--purple:#7c3aed;--bg-dark:#e2e8f0;--border2:#cbd5e1;--dim:#64748b;
}
body{font-family:var(--sans);background:var(--bg);color:var(--text);min-height:100vh}
::-webkit-scrollbar{width:6px}::-webkit-scrollbar-track{background:var(--bg)}::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
.app{display:flex;min-height:100vh}
.sidebar{width:220px;background:var(--card);border-right:1px solid var(--border);padding:20px 12px;display:flex;flex-direction:column;flex-shrink:0;height:100vh;position:sticky;top:0;overflow-y:auto}
.sidebar::-webkit-scrollbar{width:0}.sidebar{scrollbar-width:none}
.sidebar-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:200}
body.sb-open .sidebar-overlay{display:block}
.mobile-topbar{display:none;align-items:center;gap:10px;margin-bottom:14px}
.mobile-menu-btn{display:none;align-items:center;justify-content:center;width:40px;height:40px;border-radius:10px;
  border:1px solid var(--border);background:var(--card);color:var(--text2);cursor:pointer;font-family:inherit}
.mobile-menu-btn:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.mobile-home-btn{display:none;align-items:center;justify-content:center;width:40px;height:40px;border-radius:10px;
  border:1px solid var(--border);background:var(--card);color:var(--text2);cursor:pointer;font-family:inherit;margin-left:auto}
.mobile-home-btn:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.mobile-topbar-title{font-size:14px;font-weight:800}
.mobile-topbar-sub{font-size:11px;color:var(--muted);margin-top:2px}
.logo{padding:0 8px;margin-bottom:32px}
.logo-brand{font-size:15px;font-weight:800}.logo-brand span{color:var(--accent)}
.logo-sub{font-size:10px;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase}
.nav-btn{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:8px;border:none;background:transparent;color:var(--text2);cursor:pointer;font-size:13px;font-weight:500;width:100%;text-align:left;font-family:inherit;transition:all .15s;margin-bottom:2px}
.nav-btn:hover,.nav-btn.active{background:var(--accent-bg);color:var(--accent)}
.nav-btn--mysifa-portal{align-items:baseline;flex-wrap:wrap;gap:4px 8px;line-height:1.35}
.nav-btn--mysifa-portal:hover{background:var(--accent-bg)}
.nav-btn--mysifa-portal:hover .mysifa-back-preamble{color:var(--text2)}
.nav-btn--mysifa-portal:hover .mysifa-back-brand{color:var(--text)}
.nav-btn--mysifa-portal:hover .mysifa-back-accent{color:var(--accent)}
.mysifa-back-preamble{font-size:13px;font-weight:500;color:var(--text2);letter-spacing:0}
.mysifa-back-brand{font-size:14px;font-weight:800;letter-spacing:-.5px;color:var(--text);white-space:nowrap}
.mysifa-back-accent{color:var(--accent)}
.sidebar-bottom{margin-top:auto;display:flex;flex-direction:column;gap:6px;padding-bottom:8px}
.support-btn{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:8px;border:1px solid var(--border);
  background:transparent;color:var(--text2);cursor:pointer;font-size:12px;width:100%;font-family:inherit;transition:all .15s}
.support-btn:hover{background:var(--accent-bg);color:var(--accent);border-color:var(--accent)}
.support-ico{display:inline-flex;align-items:center;justify-content:center}
.user-chip{padding:10px 12px;border-radius:8px;background:var(--accent-bg);cursor:pointer}
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
.main{flex:1;padding:28px;overflow-y:auto}
.planning-container{max-width:1400px;margin:0 auto}

/* Contact support (messagerie interne) */
.contact-ov{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:950;display:flex;align-items:center;justify-content:center;padding:18px}
.contact-box{width:100%;max-width:560px;background:var(--card);border:1px solid var(--border);border-radius:16px;padding:18px 18px 16px;box-shadow:0 24px 64px rgba(0,0,0,.4);position:relative}
.contact-box h3{font-size:16px;font-weight:800;margin:0 0 12px;padding-right:34px}
.contact-close{position:absolute;top:14px;right:14px;width:32px;height:32px;border-radius:10px;border:1px solid var(--border);background:var(--bg);color:var(--muted);cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:18px;line-height:1}
.contact-close:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.contact-box label{display:block;font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin:10px 0 4px}
.contact-box input,.contact-box textarea{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px 12px;color:var(--text);font-size:13px;font-family:inherit;outline:none}
.contact-box textarea{min-height:140px;resize:vertical}
.contact-box input:focus,.contact-box textarea:focus{border-color:var(--accent)}
.contact-actions{display:flex;gap:10px;justify-content:flex-end;margin-top:14px}
.btn-sec{background:transparent;border:1px solid var(--border);color:var(--muted);border-radius:12px;
  padding:12px 14px;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit;transition:box-shadow .2s,border-color .15s,color .15s,filter .15s}
.btn-sec:hover{box-shadow:0 0 0 1px rgba(34,211,238,.32),0 0 20px rgba(34,211,238,.2);border-color:rgba(34,211,238,.45);color:var(--accent)}
.btn-sec:active{transform:translateY(1px)}
.btn-ghost{background:transparent;border:1px solid var(--border);border-radius:8px;padding:9px 14px;font-size:12px;font-weight:600;
  color:var(--text2);cursor:pointer;font-family:inherit;transition:border-color .15s,color .15s,box-shadow .2s,transform .05s}
.btn-ghost:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg);
  box-shadow:0 0 0 1px rgba(34,211,238,.22),0 0 18px rgba(34,211,238,.12)}
.btn-ghost:active{transform:translateY(1px)}
.btn{background:var(--accent);color:var(--bg);border:none;border-radius:12px;padding:12px 16px;font-size:13px;font-weight:800;cursor:pointer;font-family:inherit}
.btn:disabled{opacity:.7;cursor:not-allowed}
.btn:hover{filter:brightness(1.05)}

.header{padding:0 0 20px;margin-bottom:4px;border-bottom:1px solid var(--border);display:flex;align-items:center;
  justify-content:space-between;flex-wrap:wrap;gap:12px}
.h-left{display:flex;align-items:center;gap:16px}
.m-title{font-size:22px;font-weight:700;color:var(--text)}
.m-sel{
  font-size:14px;font-weight:800;color:var(--text);
  font-family:var(--mono);
  background:var(--card);border:1px solid var(--border2);border-radius:12px;
  padding:10px 12px;cursor:pointer;outline:none;
  transition:all .15s;max-width:min(520px,72vw)
}
.m-sel:hover{border-color:var(--accent);background:var(--accent-bg)}
.m-sel:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12)}
.m-sel option{background:var(--card);color:var(--text)}
.m-sub{font-size:12px;color:var(--muted)}
.h-right{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.gear-btn{
  width:36px;height:36px;border-radius:10px;display:inline-flex;align-items:center;justify-content:center;
  border:1px solid var(--border2);background:var(--card);color:var(--dim);cursor:pointer;
  transition:all .15s;font-size:16px;line-height:1
}
.gear-btn:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.reset-days-btn{
  height:36px;border-radius:10px;display:inline-flex;align-items:center;justify-content:center;
  padding:0 12px;gap:8px;
  border:1px solid rgba(248,113,113,.35);
  background:rgba(248,113,113,.10);
  color:rgba(248,113,113,.95);
  cursor:pointer;font-size:12px;font-family:var(--mono);font-weight:700;
  transition:all .15s;line-height:1;white-space:nowrap
}
.reset-days-btn:hover{border-color:rgba(248,113,113,.55);background:rgba(248,113,113,.16)}
.reset-days-btn:active{transform:translateY(1px)}

.sat-tog{display:flex;align-items:center;gap:10px;padding:8px 16px;border-radius:10px;cursor:pointer;
  border:1px solid var(--border2);background:var(--card);transition:all .3s;user-select:none}
.sat-tog.on{background:#1a1a3a;border-color:rgba(124,58,237,.4)}
.track{width:38px;height:20px;border-radius:10px;position:relative;background:#3a3a5a;transition:background .3s}
.sat-tog.on .track{background:var(--purple)}
.thumb{width:16px;height:16px;border-radius:50%;background:#fff;position:absolute;top:2px;left:2px;
  transition:left .3s;box-shadow:0 1px 4px rgba(0,0,0,.3)}
.sat-tog.on .thumb{left:20px}
.sat-lbl{font-size:12px;font-weight:600;font-family:var(--mono);color:#6b7280;transition:color .3s}
.sat-tog.on .sat-lbl{color:#c4b5fd}

.badge{padding:8px 16px;border-radius:10px;font-size:13px;font-family:var(--mono)}
.badge-run{background:#0f2a1a;border:1px solid #166534;color:#86efac;display:flex;align-items:center;gap:8px}
body.light .badge-run{background:rgba(16,185,129,.14);border-color:#059669;color:#047857}
.badge-run .dot{width:8px;height:8px;border-radius:50%;background:var(--green);animation:pulse 2s infinite}
.badge-info{background:var(--card);border:1px solid var(--border2);color:var(--dim)}

.sec{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:24px;margin-bottom:28px}
.sec-hdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;flex-wrap:wrap;gap:12px}
.sec-title{font-size:16px;font-weight:600;color:var(--text2)}

.wk-nav{display:flex;gap:0;align-items:center}
.wk-nav button{padding:6px 12px;background:var(--card);border:1px solid var(--border2);
  color:var(--dim);cursor:pointer;font-size:14px;font-family:var(--mono)}
.wk-nav button:first-child{border-radius:8px 0 0 8px}
.wk-nav button:last-child{border-radius:0 8px 8px 0}
.wk-nav button:hover{background:var(--border)}
.wk-nav .today{padding:6px 16px;font-size:12px}

.wk-lbl{font-size:13px;font-weight:600;font-family:var(--mono);margin-bottom:8px}
.wk-lbl.cur{color:var(--blue)}.wk-lbl.nxt{color:var(--dim)}
.tl-wrap{position:relative;margin-bottom:16px}
.dh{display:flex;margin-bottom:4px}
.dh-cell{text-align:center;padding:6px 0;font-size:12px;font-weight:600;font-family:var(--mono);
  color:var(--muted);border-bottom:1px solid var(--border)}
.dh-cell.today{color:var(--blue);border-bottom:2px solid var(--accent)}
.dh-cell.sat{color:#c084fc;border-bottom:2px solid rgba(124,58,237,.3)}
.dh-cell small{display:block;font-size:10px;opacity:.6;margin-top:2px}
.dh-hours-btn{display:block;margin:2px auto 0;padding:2px 8px;border-radius:6px;border:1px solid var(--border2);
  background:transparent;color:var(--muted);font-size:10px;font-family:var(--mono);cursor:pointer;opacity:.85;transition:all .15s}
.dh-hours-btn:hover{color:var(--accent);border-color:var(--accent);background:var(--accent-bg);opacity:1}
.tl-bar{position:relative;height:84px;background:var(--bg-dark);border-radius:8px;
  border:1px solid var(--border);overflow:visible}
.d-bg{position:absolute;top:0;bottom:0;z-index:1;pointer-events:none}
.d-bg.a0{background:rgba(148,163,184,.02)}
.d-bg.a1{background:rgba(148,163,184,.16)}
body.light .d-bg.a0{background:rgba(2,6,23,.015)}
body.light .d-bg.a1{background:rgba(2,6,23,.085)}
.d-sep{position:absolute;top:0;bottom:0;width:2px;background:rgba(148,163,184,.45);z-index:2;pointer-events:none}
body.light .d-sep{background:rgba(71,85,105,.35)}
.d-sep::after{content:'';position:absolute;top:0;bottom:0;left:-6px;width:14px;background:linear-gradient(90deg,rgba(34,211,238,0),rgba(34,211,238,.08),rgba(34,211,238,0));opacity:.35}
.slot{position:absolute;top:8px;bottom:8px;border-radius:6px;display:flex;align-items:center;
  justify-content:center;cursor:pointer;transition:all .15s;overflow:visible;padding:3px 6px}
.slot[draggable="true"]{cursor:grab}
.slot[draggable="true"]:active{cursor:grabbing}
.slot-resize-handle{position:absolute;right:-10px;top:2px;bottom:2px;width:36px;box-sizing:border-box;cursor:ew-resize;display:flex;
  align-items:center;justify-content:center;opacity:0;transition:opacity .15s;z-index:10}
.slot-resize-handle:active{cursor:ew-resize}
.slot:hover .slot-resize-handle,.slot-resize-handle:hover{opacity:1}
.slot-resize-handle::after{content:'⇔';font-size:17px;font-weight:700;line-height:1;color:rgba(255,255,255,.88);pointer-events:none}
body.light .slot-resize-handle::after{color:rgba(30,41,59,.85)}
.slot-resize-preview{position:absolute;top:4px;right:34px;background:var(--card);border:1px solid var(--border2);
  border-radius:4px;padding:2px 7px;font-size:11px;color:var(--text);white-space:nowrap;pointer-events:none;z-index:100}
.slot.slot-termine-movable{cursor:grab}
.slot.slot-termine-movable:active{cursor:grabbing}
.p-toast{position:fixed;bottom:22px;right:22px;z-index:20000;max-width:min(420px,92vw);padding:11px 16px;border-radius:10px;
  font-size:13px;font-weight:600;box-shadow:0 10px 36px rgba(0,0,0,.45);border:1px solid var(--border2);animation:p-toast-in .2s ease}
.p-toast.success{background:rgba(34,197,94,.14);color:var(--ok, #22c55e)}
.p-toast.danger{background:rgba(248,113,113,.14);color:var(--danger)}
.p-toast.info{background:rgba(56,189,248,.12);color:var(--accent)}
@keyframes p-toast-in{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.slot:hover{top:5px;bottom:5px;z-index:20}
.slot-inner{display:flex;flex-direction:column;align-items:center;justify-content:center;line-height:1.15;
  text-align:center;max-width:100%;pointer-events:none}
.slot .line1{font-size:13px;color:#1e293b;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%}
.slot .line2{font-size:10px;font-weight:600;color:#334155;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%}
.slot .line3{font-size:9px;font-weight:500;color:#64748b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;margin-top:1px}
body.light .slot .line1{color:#1e293b}body.light .slot .line2{color:#334155}body.light .slot .line3{color:#64748b}
.now-l{position:absolute;top:0;bottom:0;width:2px;background:var(--red);z-index:15;box-shadow:0 0 8px var(--red)}
.now-d{position:absolute;top:-4px;left:-4px;width:10px;height:10px;border-radius:50%;background:var(--red)}

.tip{position:absolute;z-index:100;background:var(--card);border:1px solid var(--border2);border-radius:12px;padding:14px 18px;
  min-width:240px;max-width:320px;pointer-events:none;animation:tipIn .15s ease;
  box-shadow:0 12px 40px rgba(0,0,0,.6)}
.tip-hdr{display:flex;align-items:center;gap:10px;margin-bottom:10px}
.tip-bar{width:6px;height:32px;border-radius:3px;flex-shrink:0}
.tip-ref{font-size:13px;font-weight:700;color:var(--text);font-family:var(--mono)}
.tip-lbl{font-size:12px;color:var(--text2);margin-top:2px}
.tip-grid{display:grid;grid-template-columns:auto 1fr;gap:6px 12px;font-size:11px;
  border-top:1px solid var(--border2);padding-top:10px}
.tip-grid .k{color:var(--muted)}.tip-grid .v{color:var(--text2);font-family:var(--mono)}

.legend{display:flex;flex-wrap:wrap;gap:12px;margin-top:16px;padding-top:16px;border-top:1px solid var(--border)}
.lg-i{display:flex;align-items:center;gap:6px;font-size:11px;color:var(--dim)}
.lg-d{width:14px;height:14px;border-radius:4px;cursor:pointer;transition:transform .15s,box-shadow .15s;flex-shrink:0;border:1.5px solid rgba(148,163,184,.35)}
.lg-d:hover{transform:scale(1.3);box-shadow:0 0 0 2px rgba(255,255,255,.5)}
body.light .lg-d{border-color:rgba(71,85,105,.3)}
.lg-i span{font-family:var(--mono)}
/* ── Color picker popup ── */
.cpk{position:fixed;z-index:9999;background:var(--card);border:1px solid var(--border2);border-radius:12px;
  padding:10px;box-shadow:0 8px 32px rgba(0,0,0,.45);display:flex;flex-direction:column;gap:8px;min-width:180px}
.cpk-title{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;font-weight:700;padding:0 2px}
.cpk-grid{display:grid;grid-template-columns:repeat(7,22px);gap:5px}
.cpk-sw{width:22px;height:22px;border-radius:5px;border:2px solid transparent;cursor:pointer;transition:transform .12s,border-color .12s}
.cpk-sw:hover{transform:scale(1.2);border-color:rgba(255,255,255,.5)}
.cpk-sw.sel{border-color:#fff;transform:scale(1.15)}
.cpk-reset{font-size:10px;color:var(--muted);background:transparent;border:1px solid var(--border2);border-radius:6px;
  padding:4px 8px;cursor:pointer;text-align:center;font-family:inherit;transition:color .15s,border-color .15s}
.cpk-reset:hover{color:var(--accent);border-color:var(--accent)}

.th{display:grid;grid-template-columns:22px 14px minmax(110px,1.3fr) minmax(55px,.65fr) minmax(72px,.82fr) minmax(62px,.72fr) 38px minmax(62px,.6fr) minmax(80px,.9fr) 42px minmax(95px,.88fr) minmax(120px,auto);
  gap:6px;padding:10px 10px;background:var(--bg-dark);border-radius:10px 10px 0 0;
  font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;font-weight:600;font-family:var(--mono);align-items:center}
.th>span{min-width:0}
.th .act-c{text-align:center}
#tbody{
  /* Plus haut pour afficher ~10 dossiers visibles */
  max-height:min(820px, calc(100vh - 260px));
  overflow:auto;
  border-radius:0 0 10px 10px;
  scroll-behavior:auto;
  overscroll-behavior:contain;
}
.show-termine-btn{padding:7px 14px;font-size:11px;color:var(--muted);cursor:pointer;text-align:center;
  border-bottom:1px solid var(--border);background:var(--bg);user-select:none;letter-spacing:.3px}
.show-termine-btn:hover{color:var(--accent);background:var(--accent-bg)}
.tr{display:grid;grid-template-columns:22px 14px minmax(110px,1.3fr) minmax(55px,.65fr) minmax(72px,.82fr) minmax(62px,.72fr) 38px minmax(62px,.6fr) minmax(80px,.9fr) 42px minmax(95px,.88fr) minmax(120px,auto);
  gap:6px;padding:10px 10px;border-bottom:1px solid var(--border);font-size:12px;align-items:center;
  cursor:grab;transition:background .2s;background:var(--bg-dark)}
.tr:first-child{background:var(--accent-bg)}
.tr.dov{background:var(--accent-bg);opacity:.95}.tr.dra{opacity:.5}
.tr.drop-before{box-shadow:0 -3px 0 0 var(--accent) inset}
.tr.drop-after{box-shadow:0 3px 0 0 var(--accent) inset}
/* Nouvel indicateur de drop précis - ligne horizontale */
.drop-indicator{position:absolute;left:0;right:0;height:3px;background:var(--accent);border-radius:2px;pointer-events:none;z-index:100;box-shadow:0 0 8px var(--accent);animation:dropPulse 1s ease-in-out infinite}
.drop-indicator::before{content:'';position:absolute;left:-6px;top:-4px;width:12px;height:12px;border-radius:50%;background:var(--accent);border:2px solid var(--card)}
.drop-indicator::after{content:'';position:absolute;right:-6px;top:-4px;width:12px;height:12px;border-radius:50%;background:var(--accent);border:2px solid var(--card)}
@keyframes dropPulse{0%,100%{opacity:1}50%{opacity:.6}}
.dh-handle{color:var(--muted);font-size:14px;cursor:grab;user-select:none}
body.light .tr{background:var(--card)}
body.light .tr:first-child{background:var(--accent-bg)}
body.light .th{background:var(--bg)}
.cd{width:8px;height:8px;border-radius:50%}
.ref{font-family:var(--mono);font-weight:600;color:var(--text2)}
.cell-mini{font-size:11px;color:var(--text2);font-family:var(--mono);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ref.run{color:var(--blue)}
.lbl{overflow:hidden;max-width:100%}
.lbl-main{display:block;font-weight:600;color:var(--text);font-size:13px;white-space:nowrap;text-overflow:ellipsis;overflow:hidden}
.lbl-sub{display:block;font-size:11px;color:var(--muted);font-family:var(--mono);margin-top:2px;white-space:nowrap;text-overflow:ellipsis;overflow:hidden}
.lbl-meta{display:block;font-size:11px;color:var(--text2);margin-top:2px;white-space:nowrap;text-overflow:ellipsis;overflow:hidden}
.fmt{font-family:var(--mono);color:var(--dim);font-size:12px}
.dur{font-family:var(--mono);color:var(--dim)}
.st{display:inline-flex;align-items:center;gap:6px;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600}
.st.run{background:#0f2a1a;color:var(--green);border:1px solid #166534}
.st.att{background:#1a1520;color:var(--amber);border:1px solid #78350f}
.st.ter{background:var(--card);color:#6b7280;border:1px solid var(--border2)}
.statut-select{width:100%;min-width:110px;max-width:140px;padding:6px 10px;background:var(--bg);border:1px solid var(--border2);
  border-radius:10px;color:var(--text2);font-size:11px;font-family:var(--mono);outline:none}
.statut-select:focus{border-color:var(--accent);color:var(--text)}
.acts{display:grid;grid-template-columns:repeat(3,1fr);gap:4px}
.acts .ab{width:32px;height:30px;display:flex;align-items:center;justify-content:center;padding:0}
.ab{padding:4px 8px;background:transparent;border:1px solid var(--border2);color:var(--text2);
  cursor:pointer;border-radius:6px;font-family:var(--mono);display:flex;align-items:center;justify-content:center}
.ab svg{width:14px;height:14px;flex-shrink:0}
.ab:hover{background:var(--accent-bg);color:var(--accent)}
.ab.del{color:var(--red)}.ab.del:hover{background:rgba(248,113,113,.12)}
.ab.mov{display:none}
@media (max-width:900px){.ab.mov{display:flex}}
.ab:disabled{opacity:.4;cursor:not-allowed;color:var(--muted)}
.ab:disabled:hover{background:transparent;color:var(--muted);border-color:var(--border2)}
/* Tooltip actions */
.ab[title]{position:relative;overflow:visible}
.ab[title]:hover::after{
  content:attr(title);position:absolute;bottom:calc(100% + 7px);left:50%;transform:translateX(-50%);
  background:var(--card);border:1px solid var(--border2);border-radius:7px;
  padding:5px 9px;font-size:10px;color:var(--text2);white-space:nowrap;
  pointer-events:none;z-index:200;box-shadow:0 4px 16px rgba(0,0,0,.35);
  font-family:var(--sans);font-weight:500;letter-spacing:0}
.ab[title]:hover::before{
  content:'';position:absolute;bottom:calc(100% + 2px);left:50%;transform:translateX(-50%);
  border:5px solid transparent;border-top-color:var(--border2);pointer-events:none;z-index:200}

.btn-p{padding:8px 20px;background:var(--accent);color:var(--bg);border:none;border-radius:8px;
  cursor:pointer;font-size:13px;font-weight:600;font-family:var(--mono);display:flex;align-items:center;gap:8px}
.btn-p:hover{filter:brightness(1.08)}
body.light .btn-p{color:#fff}

.mo{position:fixed;inset:0;background:rgba(0,0,0,.6);display:flex;align-items:center;
  justify-content:center;z-index:1000;backdrop-filter:blur(4px)}
.md{background:var(--card);border:1px solid var(--border2);border-radius:16px;padding:32px;
  width:480px;max-width:90vw;box-shadow:0 24px 80px rgba(0,0,0,.5)}
.md h3{color:var(--text);font-size:18px;font-family:var(--mono);margin-bottom:24px}
.fd{margin-bottom:16px}
.fd label{display:block;margin-bottom:6px;color:var(--dim);font-size:12px;text-transform:uppercase;letter-spacing:1px}
.fd input,.fd select{width:100%;padding:10px 14px;background:var(--bg);border:1px solid var(--border2);
  border-radius:8px;color:var(--text);font-size:14px;font-family:var(--mono);outline:none}
.fd select option{background:var(--card);color:var(--text)}
.dur-b{margin-top:6px;height:4px;border-radius:2px;background:var(--border);overflow:hidden}
.dur-f{height:100%;border-radius:2px;background:linear-gradient(90deg,#059669,#d97706,#dc2626);transition:width .2s}
.md-acts{display:grid;grid-template-columns:repeat(3,1fr);gap:4px;margin-top:28px}
.btn-s{padding:10px 24px;background:transparent;color:var(--dim);border:1px solid var(--border2);
  border-radius:8px;cursor:pointer;font-size:14px;font-family:var(--mono)}
.empty{text-align:center;padding:48px;color:var(--muted);font-size:14px;width:100%}

@keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}
@keyframes tipIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
@keyframes slideIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
@keyframes activePulse{0%,100%{border-color:#22d3ee;box-shadow:0 0 5px rgba(34,211,238,.3)}50%{border-color:rgba(34,211,238,.35);box-shadow:none}}
/* Timeline search highlighting */
.slot.tl-match{outline:3px solid rgba(255,255,255,.9);outline-offset:2px;z-index:12}
.slot.tl-no-match{opacity:0.18;filter:grayscale(50%)}
.slot.tl-drop-over{outline:3px solid #22d3ee;outline-offset:3px;z-index:30;filter:brightness(1.15)}
/* À placer au planning — zébré */
.tr.tr-aplacer{background:repeating-linear-gradient(135deg,var(--bg-dark),var(--bg-dark) 10px,rgba(34,211,238,.07) 10px,rgba(34,211,238,.07) 20px)!important}
body.light .tr.tr-aplacer{background:repeating-linear-gradient(135deg,var(--card),var(--card) 10px,rgba(8,145,178,.08) 10px,rgba(8,145,178,.08) 20px)!important}
.slot.slot-aplacer{background-image:repeating-linear-gradient(135deg,transparent,transparent 5px,rgba(0,0,0,.12) 5px,rgba(0,0,0,.12) 10px)!important}
/* Réellement terminé (saisie opérateur confirmée) */
.slot.slot-reel-termine{opacity:.55!important;filter:grayscale(35%) brightness(.82)!important}
.tr.tr-reel-termine{opacity:.45;filter:grayscale(40%)}
/* ── Popup Mise à jour ── */
.upd-overlay{position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:9000;display:flex;align-items:center;justify-content:center;padding:16px}
.upd-card{background:var(--card);border:1px solid var(--border2);border-radius:18px;padding:28px 28px 22px;width:min(560px,100%);max-height:88vh;overflow-y:auto;box-shadow:0 24px 64px rgba(0,0,0,.55)}
.upd-card h2{font-size:18px;margin:0 0 4px}
.upd-card .upd-sub{font-size:12px;color:var(--dim);margin:0 0 18px}
.upd-card .upd-body{font-size:13px;line-height:1.7;color:var(--fg2)}
.upd-card .upd-body ul{padding-left:18px;margin:8px 0}
.upd-card .upd-body li{margin-bottom:6px}
.upd-card .upd-body strong{color:var(--fg)}
.upd-card .upd-body kbd{background:rgba(255,255,255,.12);border-radius:4px;padding:1px 5px;font-family:monospace;font-size:11px}
.upd-ok-btn{display:block;width:100%;margin-top:20px;padding:13px;border-radius:12px;border:none;background:var(--accent);color:#0a0e17;font-size:14px;font-weight:800;cursor:pointer;font-family:inherit;transition:filter .15s}
.upd-ok-btn:hover{filter:brightness(1.08)}
body.light .upd-card kbd{background:rgba(0,0,0,.1)}
.view-tabs{display:flex;gap:0;align-items:center}
.view-tab{padding:6px 14px;background:var(--card);border:1px solid var(--border2);color:var(--dim);
  cursor:pointer;font-size:12px;font-family:var(--mono);transition:all .15s}
.view-tab:first-child{border-radius:8px 0 0 8px}
.view-tab:last-child{border-radius:0 8px 8px 0}
.view-tab:not(:first-child){margin-left:-1px}
.view-tab.active{background:var(--accent-bg);color:var(--accent);border-color:var(--accent);z-index:1;position:relative}
.view-tab:hover:not(.active){background:var(--border);color:var(--text2)}

@media (max-width:900px){
  .mobile-topbar{display:flex;position:fixed;top:0;left:0;right:0;z-index:120;background:var(--bg);padding:10px 18px;border-bottom:1px solid var(--border)}
  .mobile-menu-btn{display:inline-flex}
  .mobile-home-btn{display:inline-flex}
  body.has-topbar .main{padding-top:74px}
  .main{padding:14px}
  .header{padding:0 0 14px}
  .sec{padding:16px}
  .wk-nav button{padding:6px 10px}
  .tl-bar{height:78px}
  .dh-cell{font-size:11px}
  /* Sidebar en tiroir */
  .sidebar{position:fixed;left:0;top:0;bottom:0;height:auto;max-height:100vh;z-index:300;
    transform:translateX(-105%);transition:transform .18s ease;
    box-shadow:0 16px 48px rgba(0,0,0,.55)}
  body.sb-open .sidebar{transform:translateX(0)}
}
</style>
</head>
<body>
<div class="sidebar-overlay" id="sb-ov"></div>
<div id="app"></div>
<script src="/static/support_widget.js"></script>
<script>
// Handler d'erreurs installé *avant* le script principal (capte aussi les erreurs de parsing).
function showFatal(message, lineno, colno, extra){
  try{
    const msg = message ? String(message) : "Erreur inconnue";
    const loc = (lineno||colno) ? (`\\n\\nLigne: ${lineno||'?'}, Col: ${colno||'?'}`) : "";
    const more = extra ? (`\\n\\n${String(extra)}`) : "";
    const pre = document.createElement("pre");
    pre.style.cssText="position:fixed;inset:12px;z-index:9999;background:rgba(17,24,39,.96);color:#f1f5f9;border:1px solid rgba(148,163,184,.25);border-radius:14px;padding:14px;overflow:auto;font:12px/1.45 ui-monospace,Consolas,monospace;white-space:pre-wrap";
    pre.textContent="MySifa / Planning — erreur JS\\n\\n"+msg+loc+more+"\\n\\nOuvrez la console (F12) pour le détail.";
    document.body.appendChild(pre);
  }catch(e){}
}
window.addEventListener("error", (e)=>showFatal(e.message, e.lineno, e.colno, (e.error && e.error.stack) ? e.error.stack : ""));
window.addEventListener("unhandledrejection", (e)=>showFatal("Promise rejection", 0, 0, e.reason||""));
</script>
<script>
let MID=__MACHINE_ID__;
const DN=["Dim","Lun","Mar","Mer","Jeu","Ven","Sam"];
const MIND=2,MAXD=720;
const CC=["#93c5fd","#c4b5fd","#6ee7b7","#fde68a","#fca5a5","#67e8f9","#a5b4fc","#bbf7d0","#f0abfc","#fdba74"];
// Palette étendue pour le picker de couleurs (pastels en premier, saturés ensuite)
const PALETTE=[
  // Pastels (cohérents avec la palette par défaut)
  "#93c5fd","#c4b5fd","#6ee7b7","#fde68a","#fca5a5","#67e8f9",
  "#a5b4fc","#bbf7d0","#f0abfc","#fdba74","#99f6e4","#fef08a",
  "#bfdbfe","#ddd6fe","#a7f3d0","#fecaca","#fed7aa","#e9d5ff",
  // Saturés (pour surcharge manuelle)
  "#3b82f6","#8b5cf6","#10b981","#f59e0b","#ef4444","#06b6d4",
  "#6366f1","#22c55e","#d946ef","#f97316","#64748b","#94a3b8",
];
const MACHINE_ORDER=["Cohésio 1","Cohésio 2","DSI","Repiquage"];
const DEFAULTS_BY_KEY={
  "C1":{pair:{week:{s:5,e:20},fri:{s:7,e:19}},impair:{week:{s:5,e:20},fri:{s:7,e:19}}}, // Cohésio 1
  // Cohésio 2
  // - semaine paire  : lun–jeu 05:00–13:00 ; ven 06:00–13:00
  // - semaine impaire: lun–jeu 13:00–20:00 ; ven 14:00–20:00
  "C2":{pair:{week:{s:5,e:13},fri:{s:6,e:13}},impair:{week:{s:13,e:20},fri:{s:14,e:20}}},
  "DSI":{pair:{week:{s:8,e:14},fri:{s:8,e:14}},impair:{week:{s:8,e:14},fri:{s:8,e:14}}}, // DSI
  "REP":{pair:{week:{s:6,e:20},fri:{s:7,e:19}},impair:{week:{s:6,e:20},fri:{s:7,e:19}}}, // Repiquage
};
const DAY_API={1:"lundi",2:"mardi",3:"mercredi",4:"jeudi",5:"vendredi",6:"samedi"};
const DAY_FIELD={1:"horaires_lundi",2:"horaires_mardi",3:"horaires_mercredi",4:"horaires_jeudi",5:"horaires_vendredi",6:"horaires_samedi"};
let S={machine:null,machines:[],entries:[],timeline:[],wo:0,loading:true,holidays:{},dayWorked:{},dayHoraires:{},view:localStorage.getItem("mysifa.planning.view")||"2w",
  contactOpen:false,contactSubject:"",contactMessage:"",contactSending:false,searchQuery:"",tlSearchQuery:"",tlSearchIdx:0,activeDossier:null,
  tlTotalDays:5,machineHoursPerDay:16};
let _allTlMatches=[];
let ME=null;
let CAN_EDIT=false;
let IS_DIR_OR_SUPER=false;
let SHOW_DOSSIERS=false;
let _autoScrollKey=null;
let _suppressAutoScroll=false;
let _showAllTermine=false;   // true = montrer tous les terminés; false = seulement les 2 derniers
const TERMINE_KEEP=2;        // nombre de terminés toujours visibles en bas de la pile

const api=(p,o={})=>fetch(`/api/planning${p}`,{credentials:"include",headers:{"Content-Type":"application/json",...(o.headers||{})},...o}).then(r=>{if(!r.ok)throw r;return r.json()});

let _pToastTimer=null;
function showToast(message,type){
  const t=type==="danger"?"danger":type==="info"?"info":"success";
  let el=document.getElementById("p-toast");
  if(!el){
    el=document.createElement("div");
    el.id="p-toast";
    el.className="p-toast";
    document.body.appendChild(el);
  }
  el.className="p-toast "+t;
  el.textContent=message;
  el.style.display="block";
  if(_pToastTimer) clearTimeout(_pToastTimer);
  _pToastTimer=setTimeout(()=>{el.style.display="none";_pToastTimer=null;},3400);
}

(function initSlotResize(){
  if(window.__mysifaPlanResize) return;
  window.__mysifaPlanResize=true;
  let resizing=null;
  document.addEventListener("mousedown",function(e){
    if(!CAN_EDIT||!MID) return;
    const handle=e.target&&e.target.closest&&e.target.closest("[data-resize='1']");
    if(!handle) return;
    const slot=handle.closest(".slot");
    if(!slot) return;
    const tlBar=slot.closest(".tl-bar");
    if(!tlBar) return;
    const eidStr=String(handle.dataset.eid||"");
    let entry=(S.timeline||[]).find(s=>String(s.entry_id||"")===eidStr);
    if(!entry&&S.entries&&S.entries.length){
      const ent=S.entries.find(x=>String(x.id)===eidStr);
      if(ent) entry={entry_id:ent.id,duree_heures:ent.duree_heures};
    }
    if(!entry) return;
    e.preventDefault();
    e.stopPropagation();
    const tlRect=tlBar.getBoundingClientRect();
    const pxPerPct=tlRect.width/100||1;
    const startWpct=parseFloat(slot.style.width)||1;
    const startLeftpct=parseFloat(slot.style.left)||0;
    const startDuree=Math.max(0.25,parseFloat(entry.duree_heures)||0.5);
    slot.style.position="relative";
    const preview=document.createElement("div");
    preview.className="slot-resize-preview";
    preview.textContent=startDuree.toFixed(1)+" h";
    slot.appendChild(preview);
    slot.style.cursor="ew-resize";
    resizing={
      slot,
      eid:eidStr,
      startX:e.clientX,
      startWpct,
      startLeftpct,
      pxPerPct,
      startDuree,
      preview,
      maxRightPct:Math.max(0.55,100-startLeftpct-0.08)
    };
  },true);
  document.addEventListener("mousemove",function(e){
    if(!resizing) return;
    const dx=e.clientX-resizing.startX;
    const deltaPct=dx/resizing.pxPerPct;
    const newWpct=Math.min(resizing.maxRightPct,Math.max(0.5,resizing.startWpct+deltaPct));
    const newDuree=Math.max(0.25,resizing.startDuree*(newWpct/resizing.startWpct));
    resizing.slot.style.width=newWpct+"%";
    resizing.preview.textContent=newDuree.toFixed(1)+" h";
    resizing._liveNewDuree=newDuree;
  });
  document.addEventListener("mouseup",async function(){
    if(!resizing) return;
    const{slot,eid,preview,startDuree,startWpct}=resizing;
    preview.remove();
    slot.style.cursor="";
    const live=resizing._liveNewDuree;
    resizing=null;
    if(live==null){
      slot.style.width=startWpct+"%";
      return;
    }
    const rounded=Math.round(live*4)/4;
    if(Math.abs(rounded-startDuree)<1e-6){
      slot.style.width=startWpct+"%";
      return;
    }
    try{
      const res=await fetch(`/api/planning/machines/${MID}/entries/${eid}`,{
        method:"PUT",
        credentials:"include",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({duree_heures:rounded})
      });
      if(!res.ok){
        const j=await res.json().catch(()=>({}));
        const d=j.detail;
        const msg=typeof d==="string"?d:(Array.isArray(d)?d.map(x=>x.msg||JSON.stringify(x)).join(" "):"Erreur mise à jour durée.");
        showToast(msg,"danger");
      }else{
        showToast("Durée mise à jour : "+rounded.toFixed(1)+" h","success");
      }
    }catch(_){
      showToast("Erreur réseau.","danger");
    }
    await load();
  });
})();

function fmtPlanningIso(d){
  if(!d||!(d instanceof Date)||isNaN(d.getTime())) return"";
  const y=d.getFullYear(),mo=String(d.getMonth()+1).padStart(2,"0"),da=String(d.getDate()).padStart(2,"0");
  const hh=String(d.getHours()).padStart(2,"0"),mi=String(d.getMinutes()).padStart(2,"0"),ss=String(d.getSeconds()).padStart(2,"0");
  return y+"-"+mo+"-"+da+"T"+hh+":"+mi+":"+ss;
}

(function initTermineTlSlide(){
  if(window.__mysifaTermineSlide) return;
  window.__mysifaTermineSlide=true;
  let st=null;
  document.addEventListener("mousedown",function(e){
    if(!CAN_EDIT||!MID) return;
    if(e.target&&e.target.closest&&e.target.closest("[data-resize='1']")) return;
    const slot=e.target&&e.target.closest&&e.target.closest("#tl-blocks-container .slot.slot-termine-movable");
    if(!slot) return;
    const tlBar=slot.closest(".tl-bar"),tlWrap=slot.closest(".tl-wrap");
    if(!tlBar||!tlWrap) return;
    const p0=slot.dataset.plannedStart,p1=slot.dataset.plannedEnd;
    if(!p0||!p1) return;
    const o0=new Date(p0),o1=new Date(p1);
    if(isNaN(o0.getTime())||isNaN(o1.getTime())) return;
    const mon=new Date(+tlWrap.dataset.mon);
    if(isNaN(mon.getTime())) return;
    e.preventDefault();
    try{hideTip();}catch(_){}
    const tlRect=tlBar.getBoundingClientRect();
    const origLeftPct=parseFloat(slot.style.left)||0;
    const wPct=parseFloat(slot.style.width)||0.5;
    st={
      slot,
      eid:String(slot.dataset.eid||""),
      startX:e.clientX,
      tlRect,
      origLeftPct,
      wPct,
      origStartMs:o0.getTime(),
      origEndMs:o1.getTime()
    };
  });
  document.addEventListener("mousemove",function(e){
    if(!st) return;
    const dx=e.clientX-st.startX;
    if(Math.abs(dx)<3) return;
    st.moved=true;
    const tw=st.tlRect.width||1;
    const rawLeft=st.origLeftPct+dx/tw*100;
    const newLeft=Math.max(0,Math.min(100-st.wPct,rawLeft));
    st.slot.style.left=newLeft+"%";
    st._effLeft=newLeft;
  });
  document.addEventListener("mouseup",async function(){
    if(!st) return;
    const ctx=st;
    st=null;
    if(!ctx.moved){
      ctx.slot.style.left=ctx.origLeftPct+"%";
      return;
    }
    const newLeft=ctx._effLeft!=null?ctx._effLeft:ctx.origLeftPct;
    const tlWrap2=ctx.slot.closest(".tl-wrap");
    const mon=new Date(+(tlWrap2&&tlWrap2.dataset?tlWrap2.dataset.mon:NaN));
    let ns,ne,skip=false;
    if(isNaN(mon.getTime())) skip=true;
    else{
      const wm=computeTlWeekModel(mon);
      if(wm.err){
        const weekEnd=addD(mon,7);
        const weekSpanMs=weekEnd.getTime()-mon.getTime();
        if(weekSpanMs<=0) skip=true;
        else{
          const effMs=((newLeft-ctx.origLeftPct)/100)*weekSpanMs;
          if(Math.abs(effMs)<3e4) skip=true;
          else{ns=new Date(ctx.origStartMs+effMs);ne=new Date(ctx.origEndMs+effMs);}
        }
      }else{
        const{tot,cols}=wm;
        const sp0=(ctx.origLeftPct/100)*tot;
        const ep0=((ctx.origLeftPct+ctx.wPct)/100)*tot;
        const dWork=ep0-sp0;
        const sp1=(newLeft/100)*tot;
        const ep1=Math.min(tot,sp1+dWork);
        if(Math.abs(sp1-sp0)<0.03) skip=true;
        else{ns=invCumulativeWorkH(sp1,cols,tot);ne=invCumulativeWorkH(ep1,cols,tot);}
      }
    }
    const ps=fmtPlanningIso(ns),pe=fmtPlanningIso(ne);
    ctx.slot.style.left=ctx.origLeftPct+"%";
    if(skip||!ps||!pe) return;
    try{
      const res=await fetch(`/api/planning/machines/${MID}/entries/${ctx.eid}`,{
        method:"PUT",
        credentials:"include",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({planned_start:ps,planned_end:pe})
      });
      if(!res.ok){
        const j=await res.json().catch(()=>({}));
        const d=j.detail;
        const msg=typeof d==="string"?d:(Array.isArray(d)?d.map(x=>x.msg||JSON.stringify(x)).join(" "):"Impossible de déplacer le créneau.");
        showToast(msg,"danger");
      }else{
        showToast("Créneau déplacé.","success");
      }
    }catch(_){
      showToast("Erreur réseau.","danger");
    }
    await load();
  });
})();

async function load(){
  if(!MID){
    console.warn("Planning: aucune machine sélectionnée (MID=0)");
    S.loading=false;
    render();
    return;
  }
  S.loading=true;_showAllTermine=false;render();
  try{
    const showDossiers = !!(ME && isAdmin(ME));
    // Important: la timeline persiste planned_start/planned_end en DB.
    // Pour que les statuts calculés (en_cours/termine) soient à jour après un reorder,
    // on charge d'abord la timeline, puis la liste des entrées (admin uniquement).
    const [m, tl, activeDoss] = await Promise.all([
      api(`/machines/${MID}`), 
      api(`/machines/${MID}/timeline`),
      loadActiveDossier()
    ]);
    S.machine = m;
    S.timeline = (tl && tl.slots) ? tl.slots : [];
    S.activeDossier = activeDoss;
    if(showDossiers){
      const en = await api(`/machines/${MID}/entries`);
      S.entries = en || [];
    }else{
      S.entries = [];
    }
    await Promise.all([loadHolidays(),loadDayWorked(),loadDayHoraires()]);
    // Cohésio 2: les horaires alternent paire/impair → ne pas les "figer" en base.
  }catch(e){console.error(e)}
  S.loading=false;render();
}

async function loadDayWorked(){
  const mon=addD(getMon(new Date()),S.wo*7);
  const nb=S.view==="1w"?6:S.view==="4w"?27:13;
  const start=ymd(mon), end=ymd(addD(mon,nb));
  const rows=await api(`/machines/${MID}/day-work?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`);
  const map={};
  (rows||[]).forEach(r=>{map[String(r.date)]=!!(+r.is_worked);});
  S.dayWorked=map;
}

async function loadDayHoraires(){
  const mon=addD(getMon(new Date()),S.wo*7);
  const nb=S.view==="1w"?6:S.view==="4w"?27:13;
  const start=ymd(mon), end=ymd(addD(mon,nb));
  const rows=await api(`/machines/${MID}/day-horaires?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`);
  const map={};
  (rows||[]).forEach(r=>{ map[String(r.date)]={s:r.heure_debut, e:r.heure_fin}; });
  S.dayHoraires=map;
}

async function loadHolidays(){
  const mon=addD(getMon(new Date()),S.wo*7);
  const start=ymd(mon);
  const nb=S.view==="1w"?6:S.view==="4w"?27:13;
  const end=ymd(addD(mon,nb));
  const rows=await api(`/machines/${MID}/holidays?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`);
  const map={};
  (rows||[]).forEach(r=>{map[String(r.date)]=!!(+r.is_off);});
  S.holidays=map;
}

async function loadActiveDossier(){
  if(!MID) return null;
  try{
    const data=await api(`/machines/${MID}/active-dossier`);
    return data.dossier||null;
  }catch(e){ return null; }
}

async function setDayNonTravail(dateStr,isSaturday,nonTravailChecked){
  if(!CAN_EDIT) return;
  if(isSaturday){
    await api(`/machines/${MID}/day-work`,{method:"PUT",body:JSON.stringify({date:dateStr,is_worked:nonTravailChecked?0:1})});
  }else{
    await api(`/machines/${MID}/holidays`,{method:"PUT",body:JSON.stringify({date:dateStr,is_off:nonTravailChecked?1:0})});
  }
  await load();
}

async function resetDefaultDaysCohesio2(){
  if(!CAN_EDIT) return;
  if(machineKey()!=="C2") return;
  if(!confirm("Réinitialiser Cohésio 2 : remettre tous les jours sur la base des réglages (horaires + samedi travaillé) ?\\n\\nCela supprime les jours off et overrides (samedi) saisis manuellement pour cette machine.")) return;
  try{
    await api(`/machines/${MID}/reset-default-days`,{method:"POST"});
    await load();
  }catch(e){
    console.error(e);
    alert("Réinitialisation impossible (voir console).");
  }
}

function isDefaultMachineHoursC2(m){
  if(!m) return false;
  // Valeurs « génériques » issues du schéma (pas spécifiques Cohésio 2)
  return String(m.horaires_lundi||"").trim()==="5,21"
    && String(m.horaires_mardi||"").trim()==="5,21"
    && String(m.horaires_mercredi||"").trim()==="5,21"
    && String(m.horaires_jeudi||"").trim()==="5,21"
    && String(m.horaires_vendredi||"").trim()==="6,20";
}

function hhmmFromFloat(f){
  const h=Math.floor(f+1e-6),m=Math.round((f-h)*60);
  const hh=h+(m>=60?1:0),mm=((m%60)+60)%60;
  return pad(hh)+":"+pad(mm);
}

async function bootstrapCohesio2HoursFromDefaultsIfNeeded(){
  // Désactivé volontairement.
  // Cohésio 2 alterne les horaires selon semaine paire/impair.
  // Écrire un seul bloc horaires_* en base fige un seul planning et provoque des mélanges.
  return;
}

function colorForId(id){
  const custom=localStorage.getItem("mysifa.slot.color."+id);
  if(custom) return custom;
  const n=(id*2654435761)>>>0;
  return CC[n%CC.length];
}

// ── Color picker ─────────────────────────────────────────────────
let _cpkEl=null,_cpkEntryId=null;
function openColorPicker(entryId,anchorEl){
  closeColorPicker();
  _cpkEntryId=entryId;
  const cur=colorForId(entryId);
  const div=document.createElement("div");
  div.className="cpk";
  div.innerHTML=`<div class="cpk-title">Couleur du dossier</div>
<div class="cpk-grid">${PALETTE.map(c=>`<div class="cpk-sw${c===cur?" sel":""}" style="background:${c}" title="${c}" onclick="pickColor(${entryId},'${c}')"></div>`).join("")}</div>
<button class="cpk-reset" onclick="pickColor(${entryId},null)">Réinitialiser</button>`;
  document.body.appendChild(div);
  _cpkEl=div;
  // Positionner au-dessus/dessous de l'ancre
  const rect=anchorEl.getBoundingClientRect();
  const dw=div.offsetWidth||190,dh=div.offsetHeight||160;
  let left=rect.left,top=rect.bottom+6;
  if(left+dw>window.innerWidth-8) left=window.innerWidth-dw-8;
  if(top+dh>window.innerHeight-8) top=rect.top-dh-6;
  div.style.left=Math.max(8,left)+"px";
  div.style.top=Math.max(8,top)+"px";
  // Fermer au clic extérieur
  setTimeout(()=>document.addEventListener("click",_cpkOutside,{once:true,capture:true}),0);
}
function _cpkOutside(e){
  if(_cpkEl&&!_cpkEl.contains(e.target)) closeColorPicker();
  else setTimeout(()=>document.addEventListener("click",_cpkOutside,{once:true,capture:true}),0);
}
function closeColorPicker(){
  if(_cpkEl){_cpkEl.remove();_cpkEl=null;}
  document.removeEventListener("click",_cpkOutside,{capture:true});
}
function pickColor(entryId,color){
  if(color) localStorage.setItem("mysifa.slot.color."+entryId,color);
  else localStorage.removeItem("mysifa.slot.color."+entryId);
  closeColorPicker();
  load(); // redessine la timeline + légende
}

const pad=n=>String(n).padStart(2,"0");
function ymdate(d){return d.getFullYear()+"-"+pad(d.getMonth()+1)+"-"+pad(d.getDate());}
const ymd=ymdate;

// ── Filtrage intelligent des entrées ─────────────────────────────
function filterEntries(entries, query){
  if(!query||!query.trim()) return entries||[];
  const q=String(query).toLowerCase().trim();
  const qNorm=q.normalize("NFD").replace(/[\u0300-\u036f]/g,"");
  return (entries||[]).filter(e=>{
    const fields=[
      e.client,e.reference,e.numero_of,e.ref_produit,e.description,
      e.format_l?String(e.format_l):"",e.format_h?String(e.format_h):"",
      e.laize?String(e.laize):"",e.date_livraison
    ];
    return fields.some(f=>{
      if(!f) return false;
      const s=String(f).toLowerCase();
      const sNorm=s.normalize("NFD").replace(/[\u0300-\u036f]/g,"");
      return s.includes(q)||sNorm.includes(qNorm);
    });
  });
}

function renderEntries(){
  const tbody=document.getElementById("tbody");
  if(!tbody) return;
  const sl=S.timeline;
  const filtered=filterEntries(S.entries,S.searchQuery);

  // ── Sauvegarde du scroll courant (avant toute modification du DOM) ────────
  const prevScroll=tbody.scrollTop;

  if(filtered.length===0){
    tbody.innerHTML=S.searchQuery?'<div class="empty">Aucun résultat pour \"'+escAttr(S.searchQuery)+'\"</div>':'<div class="empty">Aucun dossier au planning</div>';
    setupDD();setupStatutSelects();
    return;
  }

  // ── Partition terminés / actifs ───────────────────────────────────────────
  // On recherche dans la liste COMPLÈTE (S.entries) pour conserver les bons data-idx.
  const terminated=filtered.filter(e=>e.statut==="termine");
  const active=filtered.filter(e=>e.statut!=="termine");
  const hiddenCount=_showAllTermine?0:Math.max(0,terminated.length-TERMINE_KEEP);
  const visibleTerminated=_showAllTermine?terminated:terminated.slice(-TERMINE_KEEP);
  const visible=[...visibleTerminated,...active];

  // ── Construction HTML ─────────────────────────────────────────────────────
  let html="";
  if(hiddenCount>0){
    html+=`<div class="show-termine-btn" onclick="_showAllTermine=true;renderEntries()">▲ ${hiddenCount} dossier${hiddenCount>1?"s":""} terminé${hiddenCount>1?"s":""} masqué${hiddenCount>1?"s":""} — cliquer pour afficher</div>`;
  } else if(_showAllTermine&&terminated.length>TERMINE_KEEP){
    html+=`<div class="show-termine-btn" onclick="_showAllTermine=false;renderEntries()">▼ Masquer les anciens dossiers terminés</div>`;
  }
  html+=visible.map(e=>{
    // Toujours utiliser l'index ORIGINAL de S.entries pour que data-idx soit cohérent
    // avec le drag & drop et l'auto-scroll (qui travaillent sur S.entries complet).
    const origIdx=S.entries.findIndex(x=>x.id===e.id);
    return mkRow(e,origIdx,sl);
  }).join("");
  tbody.innerHTML=html;

  // ── Restauration du scroll : on ne bouge pas si l'utilisateur avait déjà scrollé ──
  // autoScrollDossiersIfNeeded() s'occupera du scroll initial (changement de dossier actif).
  if(prevScroll>0) tbody.scrollTop=prevScroll;

  setupDD();
  setupStatutSelects();
}
function escAttr(s){return String(s??"").replace(/&/g,"&amp;").replace(/"/g,"&quot;").replace(/</g,"&lt;");}
function escHtml(s){
  return String(s??"")
    .replace(/&/g,"&amp;")
    .replace(/</g,"&lt;")
    .replace(/>/g,"&gt;");
}

// ── Icônes SVG (Feather style) ───────────────────────────────────
function icon(name,size=16){
  const a=`width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"`;
  const p={
    'menu': '<line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line>',
    'bar-chart-2': '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
    'package': '<line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/>',
    'wrench': '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
    'calendar': '<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>',
    'trending-up': '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>',
    'users': '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    'sun': '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>',
    'moon': '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>',
    'log-out': '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
    'edit': '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>',
    'settings': '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
    'home': '<path d="M3 10.5L12 3l9 7.5"/><path d="M5 10v11h14V10"/><path d="M10 21v-6h4v6"/>',
    'layers': '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
    'arrow-up': '<line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/>',
    'arrow-down': '<line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/>',
    'copy': '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 0 2 2v1"/>',
    'scissors': '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><line x1="20" y1="4" x2="8.12" y2="15.88"/><line x1="14.47" y1="14.48" x2="20" y2="20"/><line x1="8.12" y1="8.12" x2="12" y2="12"/>',
    'repeat': '<polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/>',
    'trash-2': '<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/>',
    'corner-down-right': '<polyline points="15 10 20 15 15 20"/><path d="M4 4v7a4 4 0 0 0 4 4h12"/>',
    'ban': '<circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/>',
    'search': '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
    'chevron-left': '<polyline points="15 18 9 12 15 6"/>',
    'chevron-right': '<polyline points="9 18 15 12 9 6"/>',
    'download': '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
  };
  return `<svg ${a} aria-hidden="true" style="display:inline-block;vertical-align:middle;flex-shrink:0">${p[name]||p['calendar']}</svg>`;
}
const fd=d=>`${pad(d.getDate())}/${pad(d.getMonth()+1)}`;
const fdt=d=>`${DN[d.getDay()]} ${pad(d.getDate())}/${pad(d.getMonth()+1)} ${d.getHours()}h`;
function getMon(d){const x=new Date(d),dy=x.getDay();x.setDate(x.getDate()-dy+(dy===0?-6:1));x.setHours(0,0,0,0);return x}
function wkNum(d){const x=new Date(Date.UTC(d.getFullYear(),d.getMonth(),d.getDate()));const n=x.getUTCDay()||7;
  x.setUTCDate(x.getUTCDate()+4-n);const y=new Date(Date.UTC(x.getUTCFullYear(),0,1));return Math.ceil(((x-y)/864e5+1)/7)}
function addD(d,n){const r=new Date(d);r.setDate(r.getDate()+n);return r}
function fmtDl(s){if(!s)return"—";const p=String(s).slice(0,10).split("-");return p.length===3?p[2]+"/"+p[1]+"/"+p[0]:s;}
function fmtDur(h){const hrs=Math.floor(+h||0);const mins=Math.round(((+h||0)-hrs)*60);return mins>0?`${hrs}h${String(mins).padStart(2,"0")}`:`${hrs}h`;}

function parseHorairesPair(raw,di){
  const fb=[5,21];
  const d=String(raw??"").trim();
  if(!d)return{s:fb[0],e:fb[1]};
  const parts=d.split(",");
  if(parts.length<2)return{s:fb[0],e:fb[1]};
  function toH(x){
    x=String(x).trim();
    if(x.indexOf(":")>=0){const hp=x.split(":");return(+hp[0]||0)+((+hp[1]||0)/60);}
    return parseInt(x,10)||0;
  }
  let s=toH(parts[0]),e=toH(parts[1]);
  if(!(e>s))return{s:fb[0],e:fb[1]};
  return{s,e};
}
function floatFromTimeInput(hm){
  const s=String(hm||"").trim();
  if(!s||s.indexOf(":")<0)return null;
  const [h,m]=s.split(":");
  const hh=+h,mm=+m;
  if(!isFinite(hh)||!isFinite(mm))return null;
  return hh+(mm/60);
}
function timeInputFromFloat(f){
  const h=Math.floor(f+1e-6),m=Math.round((f-h)*60);
  const hh=h+(m>=60?1:0),mm=((m%60)+60)%60;
  return pad(hh)+":"+pad(mm);
}
function machineKey(){
  const m=S.machine||{};
  const raw=String(m.code||m.nom||String(MID)||"").trim();
  const norm=raw
    .normalize("NFD").replace(/[\u0300-\u036f]/g,"") // remove accents (Cohésio -> Cohesio)
    .toLowerCase();
  // Map human names → known default keys
  if(norm.includes("cohesio 1")||norm==="c1") return "C1";
  if(norm.includes("cohesio 2")||norm==="c2") return "C2";
  if(norm.includes("repiquage")||norm==="rep") return "REP";
  if(norm.includes("dsi")) return "DSI";
  return raw;
}
function getMachineDefaults(){
  const mk=machineKey();
  const key=`mysifa.planning.defaults.${mk}`;
  try{
    const raw=localStorage.getItem(key);
    if(raw){
      const j=JSON.parse(raw);
      if(j&&j.pair&&j.impair){
        // Migration Cohésio 2: corrige d'anciens défauts erronés (vendredi figé à 05:00–13:00)
        if(mk==="C2"){
          const isOld =
            j?.pair?.week?.s===5 && j?.pair?.week?.e===13 &&
            j?.pair?.fri?.s===5  && j?.pair?.fri?.e===13 &&
            j?.impair?.week?.s===13 && j?.impair?.week?.e===20 &&
            j?.impair?.fri?.s===5   && j?.impair?.fri?.e===13;
          if(isOld){
            const fixed = DEFAULTS_BY_KEY["C2"];
            localStorage.setItem(key, JSON.stringify(fixed));
            return fixed;
          }
        }
        return j;
      }
    }
  }catch(e){}
  return DEFAULTS_BY_KEY[mk]||DEFAULTS_BY_KEY["C1"];
}
function saveMachineDefaults(defs){
  const mk=machineKey();
  const key=`mysifa.planning.defaults.${mk}`;
  localStorage.setItem(key,JSON.stringify(defs));
}
function isWeekPair(d){
  const w=wkNum(d);
  return (w%2)===0;
}
function getWhForDate(di,dateObj,ds){
  // Priorité 1 : override ponctuel par date (planning_day_horaires)
  if(ds && S.dayHoraires && S.dayHoraires[ds]){
    return S.dayHoraires[ds];
  }
  // Priorité 2 : horaires hebdo stockés en base pour cette machine (si non vides)
  const m=S.machine,key=DAY_FIELD[di];
  const raw=m&&m[key]!=null?String(m[key]):"";
  if(raw && raw.trim()){
    // Cohesio 2 : les horaires alternent selon semaine paire/impaire.
    // Les valeurs DB sont volontairement génériques — toujours utiliser les défauts paire/impaire.
    if(machineKey()!=="C2"){
      return parseHorairesPair(raw||null,di);
    }
    // C2 : fall-through vers la logique paire/impaire ci-dessous
  }

  // Défauts par machine (semaine paire/impair + vendredi)
  const defs=getMachineDefaults();
  const par=isWeekPair(dateObj)?"pair":"impair";
  const isFri=(di===5);
  const w=isFri?(defs[par].fri):(defs[par].week);
  return {s:w.s,e:w.e};
}
function fmtHm(f){
  const h=Math.floor(f+1e-6),m=Math.round((f-h)*60);
  let mm=m,hh=h;
  if(mm>=60){hh+=Math.floor(mm/60);mm=mm%60;}
  if(mm<=0)return hh+"h";
  return pad(hh)+":"+pad(mm);
}
function fmtWindow(s,e){return fmtHm(s)+"–"+fmtHm(e);}
function fracToTimeInput(f){
  const h=Math.floor(f+1e-6),m=Math.round((f-h)*60)%60;
  return pad(h)+":"+pad(m);
}
function isHHMM(s){return /^\d{2}:\d{2}$/.test(String(s||"").trim());}

function isAdmin(u){return u&&(u.role==="direction"||u.role==="administration"||u.role==="superadmin");}
function canPlanningNav(u){return !!(u&&u.app_access&&u.app_access.planning);}
function roleLabel(role){const R={direction:"Direction",administration:"Administration",fabrication:"Fabrication",superadmin:"Super admin"};return R[role]||role||"";}
function renderSidebar(){
  if(!ME){
    return `<nav class="sidebar"><div class="logo"><div class="logo-brand">My<span>Prod</span></div><div class="logo-sub">by SIFA</div></div>
      <div style="padding:10px 12px;color:var(--muted);font-size:12px">Chargement…</div>
      <div class="sidebar-bottom">
        <button type="button" class="nav-btn nav-btn--mysifa-portal" onclick="location.href='/'"><span class="mysifa-back-preamble">← Retour </span><span class="mysifa-back-brand">My<span class="mysifa-back-accent">Sifa</span></span></button>
        <div class="version">__V_LABEL__</div>
      </div></nav>`;
  }
  const admin=isAdmin(ME);
  const items=[
    ...(canPlanningNav(ME)?[{key:"_planning",label:"Planning",icon:"calendar",href:"/planning"}]:[]),
    {key:"production",label:"Production",icon:"wrench",href:"/prod?page=production"},
    {key:"traceabilite",label:"Traçabilité",icon:"layers",href:"/prod?page=traceabilite"},
    ...(admin?[{key:"rentabilite",label:"Rentabilité",icon:"trending-up",href:"/prod?page=rentabilite"}]:[]),
  ];
  const isLight=document.body.classList.contains("light");
  return`<nav class="sidebar"><div class="logo"><div class="logo-brand">My<span>Prod</span></div><div class="logo-sub">by SIFA</div></div>${
    items.map(i=>`<button type="button" class="nav-btn${i.key==="_planning"?" active":""}" onclick="location.href='${i.href}'"><span style="display:inline-flex;align-items:center;gap:10px">${icon(i.icon,16)}${i.label}</span></button>`).join("")
  }<div class="sidebar-bottom"><button type="button" class="nav-btn nav-btn--mysifa-portal" onclick="location.href='/'"><span class="mysifa-back-preamble">← Retour </span><span class="mysifa-back-brand">My<span class="mysifa-back-accent">Sifa</span></span></button><div class="user-chip" onclick="location.href='/'" title="Retour à l'accueil MySifa"><div class="uc-name">${escAttr(ME.nom||"")}</div><div class="uc-role">${roleLabel(ME.role)}</div><div style="font-size:10px;color:var(--accent);margin-top:3px;display:flex;align-items:center;gap:4px">${icon('edit',12)}Mon profil</div></div><button type="button" class="support-btn" onclick="openSupport()"><span class="support-ico">${(window.MySifaSupport&&window.MySifaSupport.iconSvg)?window.MySifaSupport.iconSvg():""}</span><span>Contacter le support</span></button><button type="button" class="theme-btn" onclick="toggleTheme()"><span class="theme-ico">${isLight?icon('sun',16):icon('moon',16)}</span><span class="theme-label">${isLight?"Mode clair":"Mode sombre"}</span></button><button type="button" class="logout-btn" onclick="doLogout()">${icon('log-out',14)} Déconnexion</button><div class="version">__V_LABEL__</div></div></nav>`;
}
function toggleTheme(){document.body.classList.toggle("light");localStorage.setItem("theme",document.body.classList.contains("light")?"light":"dark");render();}
async function doLogout(){try{await fetch("/api/auth/logout",{method:"POST",credentials:"include"});}catch(e){}location.href="/";}

function openSupport(){
  if(!ME) return;
  S.contactOpen=true;
  render();
}
function closeSupport(){
  S.contactOpen=false;
  S.contactSending=false;
  render();
}
async function sendSupport(){
  if(S.contactSending) return;
  const subject=String(S.contactSubject||"").trim();
  const message=String(S.contactMessage||"").trim();
  if(!message){ alert("Message obligatoire"); return; }
  S.contactSending=true; render();
  try{
    const r=await fetch("/api/messages/contact",{method:"POST",credentials:"include",headers:{"Content-Type":"application/json"},body:JSON.stringify({subject,message})});
    if(!r.ok){ throw new Error("err"); }
    S.contactOpen=false;
    S.contactSending=false;
    S.contactSubject="";
    S.contactMessage="";
    render();
    alert("Message envoyé au support");
  }catch(e){
    S.contactSending=false; render();
    alert("Envoi impossible");
  }
}

function renderContactModal(){
  if(!S.contactOpen) return "";
  return `<div class="contact-ov" onclick="if(event.target===this)closeSupport()">
    <div class="contact-box" onclick="event.stopPropagation()">
      <button type="button" class="contact-close" onclick="closeSupport()">×</button>
      <h3>Contacter le support</h3>
      <label>Objet (facultatif)</label>
      <input type="text" value="${escAttr(S.contactSubject||"")}" oninput="S.contactSubject=this.value" placeholder="Ex: Problème sur MyStock…">
      <label>Message *</label>
      <textarea oninput="S.contactMessage=this.value" placeholder="Décris ton besoin, avec contexte.">${escHtml(S.contactMessage||"")}</textarea>
      <div class="contact-actions">
        <button type="button" class="btn-ghost" onclick="closeSupport()">Annuler</button>
        <button type="button" class="btn" onclick="sendSupport()" ${S.contactSending?"disabled":""}>${S.contactSending?"Envoi…":"Envoyer"}</button>
      </div>
    </div>
  </div>`;
}

function render(){
  const a=document.getElementById("app");
  if(S.loading){
    a.innerHTML=`<div class="app">${renderSidebar()}<main class="main"><div class="mobile-topbar"><button type="button" class="mobile-menu-btn" onclick="toggleSidebar()" aria-label="Menu"><span style="display: inline-flex; align-items: center; flex-shrink: 0;">${icon('menu',20)}</span></button><div><div class="mobile-topbar-title">Planning</div><div class="mobile-topbar-sub">KPIs, temps, quantités et qualité de saisie</div></div><button type="button" class="mobile-home-btn" onclick="location.href='/'" aria-label="Accueil"><span style="display: inline-flex; align-items: center; flex-shrink: 0;">${icon('home',20)}</span></button></div><div class="planning-container" style="display:flex;align-items:center;justify-content:center;min-height:50vh;color:var(--muted)">Chargement…</div>${renderContactModal()}</main></div><div id="mroot"></div>`;
    return;
  }
  const m=S.machine||{nom:"?"};
  CAN_EDIT = isAdmin(ME);
  IS_DIR_OR_SUPER = !!(ME && (ME.role==="superadmin" || ME.role==="direction"));
  SHOW_DOSSIERS = CAN_EDIT;
  let runLbl="";
  if(SHOW_DOSSIERS){
    const run=S.entries.find(e=>e.statut==="en_cours");
    runLbl=run?(run.client||run.numero_of||run.reference||""):"";
  }else{
    const runSlot=(S.timeline||[]).find(s=>s.statut==="en_cours");
    runLbl=runSlot?(runSlot.client||runSlot.numero_of||runSlot.reference||""):"";
  }
  const totH=S.entries.filter(e=>e.statut!=="termine").reduce((s,e)=>s+e.duree_heures,0);
  const nb=S.entries.filter(e=>e.statut!=="termine").length;
  const sl=S.timeline;
  const m1=addD(getMon(new Date()),S.wo*7),m2=addD(m1,7);
  const w1=wkNum(m1),w2=wkNum(m2);
  const nw=S.view==="1w"?1:S.view==="4w"?4:2;
  const navLbl=S.wo===0?"actuelle":(S.view==="4w"?`${fd(m1)}–${fd(addD(m1,27))}`:`S${w1}`);
  let tlBlocks="";
  for(let wi=0;wi<nw;wi++){
    const mn=addD(m1,wi*7),wn=wkNum(mn);
    const lblCls=wi===0?"cur":"nxt";
    const wkParamBtn2=CAN_EDIT?`<button type="button" class="gear-btn" style="padding:3px 6px;flex-shrink:0" onclick="openWeekSettingsModal(${mn.getTime()})" title="Paramètres semaine S${wn}">${icon('settings',13)}</button>`:"";
    tlBlocks+=`<div ${wi<nw-1?'style="margin-bottom:16px"':""}>
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:8px">${wkParamBtn2}<div class="wk-lbl ${lblCls}" style="margin-bottom:0">S${wn} — ${fd(mn)} au ${fd(addD(mn,4))}</div></div>
      ${mkTL(mn,sl)}
    </div>`;
  }

  if(SHOW_DOSSIERS){
    try{
      const ent = S.entries || [];
      let firstNonTerm = ent.findIndex(e => (e && e.statut) !== "termine");
      let anchorIdx;
      if(firstNonTerm === -1) anchorIdx = Math.max(0, ent.length - 2);
      else anchorIdx = Math.max(0, firstNonTerm - 2);
      S._scrollAnchorIdx = anchorIdx;
    }catch(e){ S._scrollAnchorIdx = null; }
  }else S._scrollAnchorIdx = null;

  if(!MID || !(S.machines&&S.machines.length)){
    const fabMsg=`<p style="color:var(--muted);line-height:1.5;margin:0">Aucune machine n’est associée à votre compte pour l’instant. Les machines s’affichent lorsque le champ <strong>machine</strong> de vos <strong>saisies de production</strong> correspond au nom ou au code d’une machine du planning, ou lorsqu’une machine par défaut est renseignée sur votre fiche utilisateur.</p>`;
    const admMsg=`<p style="color:var(--muted);line-height:1.5;margin:0">Aucune machine active n’est disponible dans l’application.</p>`;
    const isFab=ME&&ME.role==="fabrication";
    a.innerHTML=`<div class="app">${renderSidebar()}<main class="main"><div class="mobile-topbar"><button type="button" class="mobile-menu-btn" onclick="toggleSidebar()" aria-label="Menu"><span style="display: inline-flex; align-items: center; flex-shrink: 0;">${icon('menu',20)}</span></button><div><div class="mobile-topbar-title">Planning</div><div class="mobile-topbar-sub">KPIs, temps, quantités et qualité de saisie</div></div><button type="button" class="mobile-home-btn" onclick="location.href='/'" aria-label="Accueil"><span style="display: inline-flex; align-items: center; flex-shrink: 0;">${icon('home',20)}</span></button></div><div class="planning-container" style="max-width:560px;margin:40px auto;padding:0 16px;color:var(--text)">
      <h1 style="font-size:18px;margin:0 0 12px">Planning</h1>
      ${isFab?fabMsg:admMsg}
    </div>${renderContactModal()}</main></div><div id="mroot"></div>`;
    return;
  }

  a.innerHTML=`<div class="app">${renderSidebar()}<main class="main"><div class="mobile-topbar"><button type="button" class="mobile-menu-btn" onclick="toggleSidebar()" aria-label="Menu"><span style="display: inline-flex; align-items: center; flex-shrink: 0;">${icon('menu',20)}</span></button><div><div class="mobile-topbar-title">Planning</div><div class="mobile-topbar-sub">KPIs, temps, quantités et qualité de saisie</div></div><button type="button" class="mobile-home-btn" onclick="location.href='/'" aria-label="Accueil"><span style="display: inline-flex; align-items: center; flex-shrink: 0;">${icon('home',20)}</span></button></div><div class="planning-container">
  <header class="header">
    <div class="h-left">
      <div>
        <select class="m-sel" onchange="changeMachine(this.value)" aria-label="Sélection de la machine">
          ${(S.machines||[]).map(x=>`<option value="${x.id}" ${x.id===MID?"selected":""}>${escAttr(x.nom||'')}</option>`).join("")}
        </select>
        <div class="m-sub">Planning de production — MyProd by SIFA</div>
      </div>
    </div>
    <div class="h-right">
      ${CAN_EDIT&&machineKey()==="C2"?`<button type="button" class="reset-days-btn" onclick="resetDefaultDaysCohesio2()" title="Réinitialiser jours (Cohésio 2)">↺ Base jours</button>`:""}
      ${CAN_EDIT?`<button type="button" class="gear-btn" onclick="openDefaultsModal()" title="Réglages horaires par défaut" aria-label="Réglages">${icon('settings',16)}</button>`:""}
      ${runLbl?`<div class="badge badge-run"><div class="dot"></div>${escAttr(runLbl)}</div>`:""}
      ${SHOW_DOSSIERS?`<div class="badge badge-info">${totH}h · ${nb} dossiers</div>`:""}
    </div>
  </header>
    <section class="sec">
      <div class="sec-hdr">
        <div class="sec-title">Vue Planning</div>
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
          <div class="view-tabs">
            <button type="button" class="view-tab ${S.view==="1w"?"active":""}" onclick="setView('1w')">Semaine</button>
            <button type="button" class="view-tab ${S.view==="2w"?"active":""}" onclick="setView('2w')">2 semaines</button>
            <button type="button" class="view-tab ${S.view==="4w"?"active":""}" onclick="setView('4w')">Mois</button>
          </div>
          <div class="wk-nav">
            <button type="button" onclick="S.wo--;load()">◀</button>
            <button type="button" class="today" onclick="S.wo=0;load()">${navLbl}</button>
            <button type="button" onclick="S.wo++;load()">▶</button>
          </div>
          ${CAN_EDIT?`<button type="button" class="btn-s" onclick="openImportOrphan()" style="display:inline-flex;align-items:center;gap:5px;padding:6px 12px;font-size:11px" title="Ajouter un dossier terminé depuis les saisies de production"><span style="font-size:15px;line-height:1">+</span> Importer dossier</button>`:""}
        </div>
      </div>
      <div style="font-size:11px;color:var(--muted);margin:-8px 0 12px">Gérez les jours et horaires via l'icône ⚙ de chaque semaine.</div>
      <div style="margin-bottom:12px;display:flex;align-items:center;gap:10px;flex-wrap:wrap">
        <div style="position:relative;max-width:360px;flex:1;min-width:160px">
          <input type="text" id="tl-search" placeholder="Rechercher dans la timeline…" value="${escAttr(S.tlSearchQuery||"")}"
            oninput="S.tlSearchIdx=0;S.tlSearchQuery=this.value;renderTL()"
            onkeydown="if(event.key==='Enter'){event.shiftKey?tlSearchPrev():tlSearchNext();event.preventDefault()}"
            style="width:100%;padding:8px 34px 8px 12px;border:1px solid var(--border2);border-radius:8px;background:var(--bg);color:var(--text);font-size:12px;font-family:var(--mono);outline:none">
          <button type="button" onclick="tlSearchNext()" title="Résultat suivant (Entrée)"
            style="position:absolute;right:8px;top:50%;transform:translateY(-50%);background:transparent;border:none;color:var(--muted);cursor:pointer;padding:2px;display:flex;align-items:center;line-height:1">
            ${icon('search',14)}
          </button>
        </div>
        <span id="tl-match-count" style="font-size:12px;font-weight:700;color:#67e8f9;font-family:var(--mono);display:none;white-space:nowrap"></span>
        <div id="tl-match-nav" style="display:none;align-items:center;gap:6px">
          <button type="button" onclick="tlSearchPrev()" title="Précédent (Shift+Entrée)"
            style="display:flex;align-items:center;gap:4px;font-size:11px;padding:5px 10px;border-radius:6px;border:1px solid var(--border2);background:transparent;color:var(--text2);cursor:pointer;font-family:inherit">
            ${icon('chevron-left',13)} Préc.
          </button>
          <button type="button" onclick="tlSearchNext()" title="Suivant (Entrée)"
            style="display:flex;align-items:center;gap:4px;font-size:11px;padding:5px 10px;border-radius:6px;border:1px solid var(--border2);background:transparent;color:var(--text2);cursor:pointer;font-family:inherit">
            Suiv. ${icon('chevron-right',13)}
          </button>
          <button type="button" onclick="S.tlSearchQuery='';S.tlSearchIdx=0;document.getElementById('tl-search').value='';renderTL()"
            style="font-size:11px;padding:5px 10px;border-radius:6px;border:1px solid var(--border2);background:transparent;color:var(--muted);cursor:pointer;font-family:inherit">✕</button>
        </div>
      </div>
      <div id="tl-blocks-container">${tlBlocks}</div>
      <div class="legend" id="tl-legend"></div>
    </section>
    ${SHOW_DOSSIERS?`<section class="sec">
      <div class="sec-hdr">
        <div class="sec-title">Dossiers de production</div>
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
          <div style="position:relative;max-width:360px;flex:1;min-width:160px">
            <input type="text" id="planning-search" placeholder="Rechercher (client, ref, OF, format…)" value="${escAttr(S.searchQuery)}"
              oninput="S.searchQuery=this.value;renderEntries();"
              style="width:100%;padding:8px 34px 8px 12px;border:1px solid var(--border2);border-radius:8px;background:var(--bg);color:var(--text);font-size:12px;font-family:var(--mono);outline:none">
            <span style="position:absolute;right:10px;top:50%;transform:translateY(-50%);color:var(--muted);font-size:14px">🔍</span>
          </div>
          ${CAN_EDIT?`<button type="button" class="btn-p" onclick="openAdd()"><span style="font-size:18px;line-height:1">+</span> Ajouter</button>`:""}
          <button type="button" class="btn-s" onclick="exportDossiers()" style="display:inline-flex;align-items:center;gap:6px;padding:8px 14px;font-size:12px">${icon('download',14)} Exporter</button>
        </div>
      </div>
      <div class="th"><span></span><span></span><span>Client</span><span>Format</span><span>Ref OF</span><span>Ref prod.</span><span>Laize</span><span>Livraison</span><span>Commentaire</span><span>Durée</span><span>Statut</span><span class="act-c">Actions</span></div>
      <div id="tbody"></div>
    </section>`:""}
  ${renderContactModal()}</div></main></div><div id="mroot"></div>`;
  if(SHOW_DOSSIERS) renderEntries();
  buildLegend(sl, m1, nw);
  if(SHOW_DOSSIERS) autoScrollDossiersIfNeeded();
  // Nouveau container → réinitialise le flag de liaison DnD timeline
  _tlDDContainerBound=false;
  // Réappliquer la recherche timeline + DnD après re-render complet
  requestAnimationFrame(()=>{computeAllTlMatches();updateTlMatchInfo();setupTlDD();});
}

// ── Timeline search — scan ALL slots (across all week offsets) ──────────────
function computeAllTlMatches(){
  const q=(S.tlSearchQuery||"").toLowerCase().trim();
  if(!q){_allTlMatches=[];return;}
  _allTlMatches=(S.timeline||[]).filter(s=>{
    const cli=(s.client||"").trim()||(s.numero_of||s.reference||"");
    const fm=s.format_l&&s.format_h?`${s.format_l} × ${s.format_h} mm`:"";
    const lz=s.laize?String(s.laize):"";
    const fields=[cli,s.numero_of||"",s.reference||"",s.description||"",fm,lz].map(f=>f.toLowerCase());
    return fields.some(f=>f.includes(q));
  });
}

function woForSlot(s){
  // Calcule le S.wo qui rend ce slot visible (aligne la semaine du slot sur la vue)
  const slotMon=getMon(new Date(s.start));
  const curMon=getMon(new Date());
  const diffDays=Math.round((slotMon.getTime()-curMon.getTime())/864e5);
  return Math.floor(diffDays/7);
}

function updateTlMatchInfo(){
  const n=_allTlMatches.length;
  const q=!!(S.tlSearchQuery&&S.tlSearchQuery.trim());
  if(S.tlSearchIdx>=n) S.tlSearchIdx=Math.max(0,n-1);
  // Compteur
  const cntEl=document.getElementById("tl-match-count");
  if(cntEl){
    cntEl.textContent=q?(n>0?`${S.tlSearchIdx+1} / ${n}`:"0 résultat"):"";
    cntEl.style.display=q?"inline":"none";
  }
  // Boutons nav
  const navEl=document.getElementById("tl-match-nav");
  if(navEl) navEl.style.display=(q&&n>0)?"flex":"none";
  // Highlight : cyan sur le courant, blanc atténué sur les autres visibles
  const curId=n>0?String(_allTlMatches[S.tlSearchIdx].entry_id):"";
  document.querySelectorAll("#tl-blocks-container .slot.tl-match").forEach(el=>{
    const isCur=el.dataset.eid===curId;
    el.style.outline=isCur?"3px solid #22d3ee":"3px solid rgba(255,255,255,.7)";
    el.style.outlineOffset="2px";
  });
  // Scroll vers le slot courant (s'il est dans le DOM)
  if(curId){
    const curDom=document.querySelector(`#tl-blocks-container .slot[data-eid="${curId}"]`);
    if(curDom) requestAnimationFrame(()=>curDom.scrollIntoView({behavior:"smooth",block:"nearest"}));
  }
}

async function tlNavTo(rawIdx){
  if(!_allTlMatches.length) return;
  const n=_allTlMatches.length;
  S.tlSearchIdx=((rawIdx%n)+n)%n;
  const s=_allTlMatches[S.tlSearchIdx];
  // Si le slot est hors de la vue courante → déplacer la vue
  const targetWo=woForSlot(s);
  const nw=S.view==="1w"?1:S.view==="4w"?4:2;
  const m1=addD(getMon(new Date()),S.wo*7);
  const viewEnd=addD(m1,nw*7);
  const ss=new Date(s.start),se=new Date(s.end);
  const visible=ss<viewEnd&&se>m1;
  if(!visible){
    S.wo=targetWo;
    try{ await Promise.all([loadDayWorked(),loadDayHoraires(),loadHolidays()]); }catch(e){}
  }
  renderTL();
}
function tlSearchNext(){ tlNavTo(S.tlSearchIdx+1); }
function tlSearchPrev(){ tlNavTo(S.tlSearchIdx-1); }

function renderTL(){
  computeAllTlMatches();
  const m1=addD(getMon(new Date()),S.wo*7);
  const nw=S.view==="1w"?1:S.view==="4w"?4:2;
  const sl=S.timeline;
  let tlBlocks="";
  for(let wi=0;wi<nw;wi++){
    const mn=addD(m1,wi*7),wn=wkNum(mn);
    const lblCls=wi===0?"cur":"nxt";
    const wkParamBtn=CAN_EDIT?`<button type="button" class="gear-btn" style="padding:3px 6px;flex-shrink:0" onclick="openWeekSettingsModal(${mn.getTime()})" title="Paramètres semaine S${wn}">${icon('settings',13)}</button>`:"";
    tlBlocks+=`<div ${wi<nw-1?'style="margin-bottom:16px"':""}>
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:8px">${wkParamBtn}<div class="wk-lbl ${lblCls}" style="margin-bottom:0">S${wn} — ${fd(mn)} au ${fd(addD(mn,4))}</div></div>
      ${mkTL(mn,sl)}
    </div>`;
  }
  const container=document.getElementById("tl-blocks-container");
  if(container) container.innerHTML=tlBlocks;
  buildLegend(sl, m1, nw);
  requestAnimationFrame(()=>{updateTlMatchInfo();setupTlDD();});
}

// ── Drag & Drop timeline slots ──
// Les listeners dragover/drop sont sur le conteneur (stable) et non sur les slots
// (recréés à chaque render). _tlDDContainerBound évite les doublons de listeners.
let _tlDragEid=null;
let _tlDDContainerBound=false;
function setupTlDD(){
  if(!CAN_EDIT) return;
  const container=document.getElementById("tl-blocks-container");
  if(!container) return;

  // dragstart / dragend : toujours sur les slots (nouveaux éléments après chaque render)
  document.querySelectorAll("#tl-blocks-container .slot[draggable='true']").forEach(el=>{
    el.addEventListener("dragstart",ev=>{
      if(ev.target&&ev.target.closest&&ev.target.closest(".slot-resize-handle")){ev.preventDefault();return;}
      _tlDragEid=+el.dataset.eid;
      el.style.opacity="0.45";
      ev.dataTransfer.effectAllowed="move";
      ev.dataTransfer.setData("text/plain",String(_tlDragEid));
    });
    el.addEventListener("dragend",()=>{
      el.style.opacity="";
      _tlDragEid=null;
      document.querySelectorAll("#tl-blocks-container .slot.tl-drop-over").forEach(e=>e.classList.remove("tl-drop-over"));
    });
  });

  // dragover / drop : une seule fois par container (render() reset _tlDDContainerBound)
  if(_tlDDContainerBound) return;
  _tlDDContainerBound=true;

  container.addEventListener("dragover",ev=>{
    if(!_tlDragEid) return;
    ev.preventDefault();
    ev.dataTransfer.dropEffect="move";
    const target=ev.target.closest(".slot[data-eid]");
    document.querySelectorAll("#tl-blocks-container .slot.tl-drop-over").forEach(e=>e.classList.remove("tl-drop-over"));
    if(target && +target.dataset.eid!==_tlDragEid){
      target.classList.add("tl-drop-over");
    }
  });
  container.addEventListener("dragleave",ev=>{
    if(!container.contains(ev.relatedTarget)){
      document.querySelectorAll("#tl-blocks-container .slot.tl-drop-over").forEach(e=>e.classList.remove("tl-drop-over"));
    }
  });
  container.addEventListener("drop",async ev=>{
    ev.preventDefault();
    document.querySelectorAll("#tl-blocks-container .slot.tl-drop-over").forEach(e=>e.classList.remove("tl-drop-over"));
    const target=ev.target.closest(".slot[data-eid]");
    const fromEid=_tlDragEid;
    _tlDragEid=null;
    if(!target||!fromEid) return;
    const eid=+target.dataset.eid;
    if(eid===fromEid) return;
    const ids=S.entries.map(e=>e.id);
    const fromIdx=ids.indexOf(fromEid);
    const toIdx=ids.indexOf(eid);
    if(fromIdx<0||toIdx<0) return;
    const [moved]=ids.splice(fromIdx,1);
    ids.splice(toIdx,0,moved);
    try{
      await api(`/machines/${MID}/reorder`,{method:"POST",body:JSON.stringify({entry_ids:ids})});
      await load();
    }catch(e){ alert("Réordonnancement impossible"); await load(); }
  });
}

async function toggleDestockage(entryId){
  if(!CAN_EDIT) return;
  try{
    const r=await api(`/machines/${MID}/entries/${entryId}/destockage`,{method:"PUT"});
    (S.timeline||[]).forEach(s=>{if((s.entry_id||0)===entryId) s.destockage=r.destockage;});
    const ent=(S.entries||[]).find(x=>x.id===entryId);
    if(ent) ent.destockage=r.destockage;
    renderTL();
    updateDestockBtn(entryId, r.destockage);
  }catch(e){ console.error("toggleDestockage",e); }
}
function updateDestockBtn(entryId, val){
  const btn=document.getElementById("destock-btn-"+entryId);
  if(!btn) return;
  const done=val==="done";
  btn.style.borderColor=done?"#38bdf8":"#fb923c";
  btn.style.background=done?"rgba(56,189,248,.12)":"rgba(251,146,60,.10)";
  btn.style.color=done?"#38bdf8":"#fb923c";
  btn.title=done?"Matières destockées — cliquer pour annuler":"Matières à destocker — cliquer pour valider";
  const ico=done?'<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>':'<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/></svg>';
  btn.innerHTML=ico+'<span>'+(done?"Destocké":"À destocker")+'</span>';
}

async function resetSaisieFromModal(entryId){
  if(!IS_DIR_OR_SUPER) return;
  if(!confirm("Remettre ce dossier en attente et effacer le statut de saisie réelle ?")) return;
  try{
    await api(`/machines/${MID}/entries/${entryId}/reset-saisie`,{method:"POST"});
    closeM();load();
  }catch(e){
    let msg="Erreur lors du reset.";
    try{const j=await e.json();if(j&&j.detail)msg=typeof j.detail==="string"?j.detail:JSON.stringify(j.detail);}catch(x){}
    alert(msg);
  }
}

function buildLegend(sl, m1, nw){
  const lgEl=document.getElementById("tl-legend");
  if(!lgEl) return;
  // Fenêtre de temps affichée
  const viewStart=m1, viewEnd=addD(m1, nw*7);
  // Slots visibles dans la fenêtre (en dédupliquant par entry_id)
  const seen=new Set();
  const visible=[];
  (sl||[]).forEach(s=>{
    const ss=new Date(s.start), se=new Date(s.end);
    if(ss<viewEnd && se>viewStart && !seen.has(s.entry_id)){
      seen.add(s.entry_id);
      visible.push(s);
    }
  });
  if(!visible.length){ lgEl.innerHTML=""; return; }
  lgEl.innerHTML=visible.map(s=>{
    const co=colorForId(s.entry_id||0);
    const lb=escAttr(s.client||s.numero_of||s.reference||"—");
    return`<div class="lg-i">
      <div class="lg-d" style="background:${co}" title="Changer la couleur"
        onclick="openColorPicker(${s.entry_id},this);event.stopPropagation()"></div>
      <span>${lb}</span>
    </div>`;
  }).join("");
}

function autoScrollDossiersIfNeeded(){
  try{
    if(_suppressAutoScroll) return;
    const ent = S.entries || [];
    if(!ent.length) return;
    const main = document.querySelector(".main");
    const tbody = document.getElementById("tbody");
    if(!main || !tbody) return;

    // ── Clé basée uniquement sur le dossier en_cours ──────────────────────
    // On ne veut PAS re-scroller après un simple reorder ou edit — seulement
    // quand le dossier actif change (ou au premier chargement de cette machine).
    const enCoursId = (ent.find(e=>e.statut==="en_cours")||{}).id ?? "none";
    const key = `${MID}|${enCoursId}`;
    if(_autoScrollKey === key) return;
    _autoScrollKey = key;

    // Attendre que le DOM soit réellement peint (desktop/mobile).
    const scrollIt = ()=>{
      const row = tbody.querySelector('[data-scroll-anchor="1"]') || tbody.querySelector(`.tr[data-idx="${S._scrollAnchorIdx}"]`);
      if(!row) return;
      // Important: on NE scroll PAS la page (.main). On scroll uniquement la zone #tbody.
      try{ main.scrollTop = 0; }catch(e){}
      try{
        const tb = tbody.getBoundingClientRect();
        const rb = row.getBoundingClientRect();
        const targetTop = (rb.top - tb.top) + tbody.scrollTop;
        tbody.scrollTop = Math.max(0, targetTop - 2);
      }catch(e){}
    };
    requestAnimationFrame(()=>requestAnimationFrame(scrollIt));
  }catch(e){}
}

function setSidebarOpen(open){
  document.body.classList.toggle("sb-open", !!open);
}
function toggleSidebar(){
  setSidebarOpen(!document.body.classList.contains("sb-open"));
}
try{
  const ov=document.getElementById("sb-ov");
  if(ov) ov.addEventListener("click",()=>setSidebarOpen(false));
}catch(e){}

/** Modèle semaine timeline (heures ouvrées cumulées + gp) — partagé par mkTL et le déplacement des terminés. */
function computeTlWeekModel(mon){
  const we=addD(mon,7),HF=.42,days=[];
  for(let i=0;i<7;i++){
    const d=addD(mon,i),di=d.getDay();
    if(di===0)continue;
    const ds=ymd(d);
    const isSat=di===6;
    const w=getWhForDate(di,d,ds);
    if(!w)continue;
    const off=isSat?!S.dayWorked[ds]:!!S.holidays[ds];
    const dayT=off?0:(w.e-w.s);
    const hourLbl=off?"—":fmtWindow(w.s,w.e);
    const nonTravail=isSat?!S.dayWorked[ds]:!!S.holidays[ds];
    days.push({date:d,di,ds,s:w.s,e:w.e,tWork:dayT,flex:off?HF:dayT,off,hourLbl,nonTravail,isSat});
  }
  if(!days.length) return{err:"nodays"};
  const tot=days.reduce((s,d)=>s+d.tWork,0);
  if(tot<=0) return{err:"notot"};
  let c=0;
  const cols=days.filter(d=>d.tWork>0).map(d=>{const cs=c;c+=d.tWork;return{...d,cs,ce:c}});
  const wkStart=new Date(mon);wkStart.setHours(0,0,0,0);
  function gp(dt){
    let acc=0,t=dt.getTime();
    if(t<wkStart.getTime())return 0;
    for(const col of cols){
      const sod=new Date(col.date);sod.setHours(0,0,0,0);
      const dStart=new Date(sod.getTime()+col.s*36e5);
      const dEnd=new Date(sod.getTime()+col.e*36e5);
      if(t>=dEnd.getTime()){acc+=col.tWork;continue;}
      if(t<dStart.getTime())return acc;
      const h=(dt-sod)/36e5;
      const hh=Math.max(col.s,Math.min(col.e,h));
      return acc+(hh-col.s);
    }
    return Math.min(acc,tot);
  }
  return{err:null,we,days,tot,cols,wkStart,gp};
}

/** h = heures ouvrées cumulées depuis le lundi 0h de la semaine [0,tot[ → Date locale */
function invCumulativeWorkH(h,cols,tot){
  const H=Math.max(0,Math.min(Number(h)||0,tot-1e-9));
  for(let i=0;i<cols.length;i++){
    const col=cols[i];
    if(H<col.cs-1e-9) continue;
    if(H>col.ce+1e-9) continue;
    const into=Math.max(0,Math.min(H-col.cs,col.tWork-1e-9));
    const sod=new Date(col.date);sod.setHours(0,0,0,0);
    const hourDec=col.s+into;
    return new Date(sod.getTime()+hourDec*36e5);
  }
  const last=cols[cols.length-1];
  const sod=new Date(last.date);sod.setHours(0,0,0,0);
  return new Date(sod.getTime()+last.e*36e5);
}

function mkTL(mon,slots){
  const wm=computeTlWeekModel(mon);
  if(wm.err==="nodays")return'<div style="color:var(--dim);padding:8px;font-size:13px">Aucun jour ouvré</div>';
  if(wm.err==="notot")return'<div style="color:var(--muted);padding:8px;font-size:13px">Aucun créneau calculable (semaine entièrement non travaillée ou fermée).</div>';
  const{we,days,tot,cols,wkStart,gp}=wm;
  const now=new Date(),ts=now.toDateString();
  const ws=slots.filter(s=>{const ss=new Date(s.start),se=new Date(s.end);return ss<we&&se>mon});

  let h=`<div class="tl-wrap" data-mon="${mon.getTime()}"><div class="dh">`;
  days.filter(d=>!d.off).forEach(d=>{
    const td=d.date.toDateString()===ts,sa=d.di===6;
    h+=`<div class="dh-cell ${td?"today":""} ${sa?"sat":""}" style="flex:${d.tWork}">
      <div style="display:flex;flex-direction:column;align-items:center;gap:2px">
        <div>${DN[d.di]} ${fd(d.date)}</div>
        ${CAN_EDIT?`<button type="button" class="dh-hours-btn" onclick="openHorairesModal('${d.ds}',${d.di})">${escAttr(d.hourLbl)}</button>`:`<small>${escAttr(d.hourLbl)}</small>`}
      </div>
    </div>`;
  });
  h+=`</div><div class="tl-bar">`;
  cols.forEach((col,i)=>{
    const l=(col.cs/tot)*100, w=((col.ce-col.cs)/tot)*100;
    h+=`<div class="d-bg ${(i%2)===0?'a0':'a1'}" style="left:${l}%;width:${w}%"></div>`;
  });
  cols.slice(1).forEach(col=>{h+=`<div class="d-sep" style="left:${(col.cs/tot)*100}%"></div>`;});

  const tlQ=(S.tlSearchQuery||"").toLowerCase().trim();
  /** Dossier sur >=2 semaines calendaires : ne pas afficher un segment dont la duree ouvree visible sur cette semaine est < 0,5 h. */
  const TL_MIN_VISIBLE_H_WHEN_SPLIT = 0.5;
  ws.forEach((s,idx)=>{
    const ss=new Date(s.start),se=new Date(s.end);
    const cs=ss<mon?mon:ss,ce=se>we?we:se;
    let sp=gp(cs),ep=gp(ce);
    if(ep<sp){ const t=sp;sp=ep;ep=t; }
    const visibleWorkH = ep - sp;
    const spansMultipleWeeks = getMon(ss).getTime() !== getMon(se).getTime();
    if(spansMultipleWeeks && visibleWorkH < TL_MIN_VISIBLE_H_WHEN_SPLIT) return;
    const l=(sp/tot)*100,w=Math.max(.5,((ep-sp)/tot)*100);
    const co=colorForId(s.entry_id||idx+1);
    const fm=s.format_l&&s.format_h?`${s.format_l} × ${s.format_h} mm`:"";
    const lz=s.laize?`${s.laize} mm`:"";
    // Ligne 2 : format + laize
    const line2Txt=[fm,lz].filter(Boolean).join(" | ");
    // Ligne 3 : date livraison + commentaire
    const dateLiv=s.date_livraison?`à livrer pour ${s.date_livraison}`:"";
    const com=s.commentaire?String(s.commentaire).trim():"";
    const line3Parts=[dateLiv,com].filter(Boolean);
    const line3Txt=line3Parts.join(" | ");
    const subTxt=line2Txt; // pour compatibilité tooltip
    const fmTip=fm||"—";
    const st=s.statut==="en_cours"?"En cours":s.statut==="termine"?"Terminé":"En attente";
    const cli=(s.client||"").trim()||(s.numero_of||s.reference||"—");
    const meta=[s.numero_of||s.reference,s.description].filter(Boolean).join(" | ");
    const noOf=(s.numero_of||s.reference||"").trim().toLowerCase();
    const activeNo=S.activeDossier?(S.activeDossier.no_dossier||"").trim().toLowerCase():"";
    const isActive=!!(activeNo&&noOf&&activeNo===noOf);
    // Search match
    let matchCls="";
    if(tlQ){
      const fields=[cli,s.numero_of||"",s.reference||"",s.description||"",fm,lz,s.laize?String(s.laize):""].map(f=>f.toLowerCase());
      matchCls=fields.some(f=>f.includes(tlQ))?"tl-match":"tl-no-match";
    }
    // a_placer striped
    const aplacerCls=s.a_placer?"slot-aplacer":"";
    const reelTermineCls=((s.statut_reel==="reellement_termine"&&s.statut!=="en_cours")||s.statut==="termine")?"slot-reel-termine":"";
    const destock=s.destockage==="done";
    const reelForDrag=(s.statut_reel||"reellement_en_attente")==="reellement_en_attente";
    const canDragSlot=CAN_EDIT&&s.statut!=="en_cours"&&s.statut!=="termine"&&reelForDrag;
    const canResizeSlot=CAN_EDIT&&s.statut!=="termine"&&(s.statut==="en_cours"||(s.statut==="attente"&&reelForDrag));
    const termineSlideCls=(CAN_EDIT&&s.statut==="termine")?"slot-termine-movable":"";
    const resizeHint="Bord droit : ajuster la durée. Reste du créneau : réordonner (si disponible).";
    const resizeHandle=canResizeSlot?`<div class="slot-resize-handle" data-eid="${s.entry_id||idx}" data-resize="1" title="${escAttr(resizeHint)}"></div>`:"";
    const termineTitle=termineSlideCls?"Dossier terminé — glisser pour décaler le créneau sur la ligne de temps":"";
    h+=`<div class="slot ${matchCls} ${aplacerCls} ${reelTermineCls} ${termineSlideCls}" data-eid="${s.entry_id||idx}" data-statut="${escAttr(s.statut||"attente")}" data-statut-reel="${escAttr(s.statut_reel||"reellement_en_attente")}" ${canDragSlot?'draggable="true"':''} style="left:${l}%;width:${w}%;background:${co};box-shadow:0 2px 8px ${co}55;${isActive?"border:2px solid #22d3ee;animation:activePulse 2.2s ease-in-out infinite;":"border:1.5px solid rgba(148,163,184,.35);"}"
      onmouseenter="showTip(event,this)" onmousemove="moveTip(event)" onmouseleave="hideTip()"
      ondblclick="hideTip();openEdit(${s.entry_id||idx});event.stopPropagation()"
      data-ref="${escAttr(cli)}" data-lbl="${escAttr(meta)}" data-rfp="${escAttr(s.ref_produit||"")}" data-fmt="${escAttr(fmTip)}" data-dur="${escAttr(fmtDur(s.duree_heures))}"
      data-planned-start="${escAttr(String(s.start||""))}" data-planned-end="${escAttr(String(s.end||""))}"
      data-deb="${escAttr(fdt(ss))}" data-fin="${escAttr(fdt(se))}" data-st="${escAttr(st)}" data-co="${escAttr(co)}"${termineTitle?` title="${escAttr(termineTitle)}"`:""}>
      ${destock?`<div style="position:absolute;top:4px;right:4px;width:7px;height:7px;border-radius:50%;background:rgba(71,85,105,.9);pointer-events:none;z-index:5;flex-shrink:0"></div>`:""}
      ${resizeHandle}
      ${w>5?`<div class="slot-inner"><span class="line1">${escAttr(cli)}</span>${line2Txt?`<span class="line2">${escAttr(line2Txt)}</span>`:""}${line3Txt?`<span class="line3">${escAttr(line3Txt)}</span>`:""}</div>`:""}</div>`;
  });

  const np=gp(now);
  if(np>0&&np<tot){
    let state="En pause";
    try{
      for(const col of cols){
        const sod=new Date(col.date);sod.setHours(0,0,0,0);
        const dStart=new Date(sod.getTime()+col.s*36e5);
        const dEnd=new Date(sod.getTime()+col.e*36e5);
        if(now>=dStart && now<=dEnd){ state="En prod"; break; }
      }
    }catch(e){}
    const tLabel=`${pad(now.getHours())}:${pad(now.getMinutes())}`;
    h+=`<div class="now-l" style="left:${(np/tot)*100}%"
      onmouseenter="showNowTip(event,this)" onmousemove="moveNowTip(event)" onmouseleave="hideNowTip()"
      data-time="${tLabel}" data-state="${state}"><div class="now-d"></div></div>`;
  }
  h+=`</div></div>`;return h;
}

function mkRow(e,i,slots){
  const fm=e.format_l&&e.format_h?`${e.format_l}×${e.format_h}`:"—";
  const sc=e.statut==="en_cours"?"run":e.statut==="termine"?"ter":"att";
  const sl={run:"En cours",ter:"Terminé",att:"En attente"}[sc];
  const isLocked=(e.statut==="en_cours"||e.statut==="termine");
  const next = S.entries && S.entries[i+1] ? S.entries[i+1] : null;
  const nextLocked = !!(next && (next.statut==="en_cours" || next.statut==="termine"));
  const isAnchor = (S._scrollAnchorIdx!=null) && (i===S._scrollAnchorIdx);
  const co=colorForId(e.id||i+1);
  const cli=(e.client||"").trim()||"—";
  const of=escAttr(e.numero_of||e.reference||"—");
  const rfp=escAttr(e.ref_produit||"")||"—";
  const lz=e.laize!=null&&e.laize!==""?escAttr(String(e.laize)):"—";
  const reelAvance=(e.statut_reel==="reellement_en_saisie"||e.statut_reel==="reellement_termine");
  const statutLockedForReel=reelAvance && !IS_DIR_OR_SUPER;
  const showStatutSelect=CAN_EDIT&&!statutLockedForReel&&((!isLocked)||IS_DIR_OR_SUPER);
  const statutCell=!showStatutSelect
    ? `<span class="st ${sc}">${sc==="run"?'<span style="width:6px;height:6px;border-radius:50%;background:var(--green);animation:pulse 2s infinite;display:inline-block"></span>':""}${sl} 🔒</span>`
    : `<select class="statut-select" data-eid="${e.id}" data-current="${escAttr(e.statut||"attente")}">
         <option value="attente" ${e.statut==="attente"?"selected":""}>Attente</option>
         <option value="en_cours" ${e.statut==="en_cours"?"selected":""}>En cours</option>
         <option value="termine" ${e.statut==="termine"?"selected":""}>Terminé</option>
       </select>`;
  const com=escAttr(e.commentaire||"");
  const aplacerRowCls=e.a_placer?"tr-aplacer":"";
  const reelTermineRowCls=e.statut_reel==="reellement_termine"?"tr-reel-termine":"";
  const reelBadge=(()=>{
    const r=e.statut_reel||"reellement_en_attente";
    if(r==="reellement_termine") return`<span style="font-size:9px;padding:2px 6px;border-radius:4px;background:rgba(148,163,184,.15);color:var(--muted);font-weight:600;letter-spacing:.5px;white-space:nowrap">✓ saisie terminé</span>`;
    if(r==="reellement_en_saisie") return`<span style="font-size:9px;padding:2px 6px;border-radius:4px;background:rgba(52,211,153,.12);color:var(--success);font-weight:600;letter-spacing:.5px;white-space:nowrap">⚙ en saisie</span>`;
    return"";
  })();
  return`<div class="tr ${aplacerRowCls} ${reelTermineRowCls}" draggable="true" data-eid="${e.id}" data-idx="${i}" ${isAnchor?'data-scroll-anchor="1"':''}
    data-statut="${escAttr(e.statut||'attente')}"
    style="animation:slideIn .3s ease ${i*.03}s both;${i===0?`border-left:3px solid ${co}`:"border-left:3px solid transparent"};${isLocked?"cursor:not-allowed;opacity:.9":""}">
    <span class="dh-handle">⠿</span>
    <div><div class="cd" style="background:${co}"></div></div>
    <span class="lbl-main">${escAttr(cli)}${reelBadge?`<br><span style="display:inline-block;margin-top:2px">${reelBadge}</span>`:""}</span>
    <span class="cell-mini">${escAttr(fm)}${fm!=="—"?" mm":""}</span>
    <span class="cell-mini">${of}</span>
    <span class="cell-mini">${rfp}</span>
    <span class="cell-mini">${lz}</span>
    <span class="cell-mini">${escAttr(fmtDl(e.date_livraison||""))}</span>
    <span class="cell-mini" style="font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${com}">${com}</span>
    <span class="cell-mini">${fmtDur(e.duree_heures)}</span>
    ${statutCell}
    <div class="acts">
      ${CAN_EDIT?(()=>{
        const BAN=icon('ban',14);
        const blkSwitch=isLocked;
        const blkUp=i<=0||isLocked;
        const blkDown=i>=S.entries.length-1||isLocked;
        const blkSplit=isLocked;
        const blkInsert=isLocked||nextLocked;
        const blkDel=e.statut==="termine";
        return`
      <button type="button" class="ab" onclick="openEdit(${e.id})" title="Modifier">${icon('edit',14)}</button>
      <button type="button" class="ab" onclick="duplicateEntry(${e.id})" title="Dupliquer">${icon('copy',14)}</button>
      <button type="button" class="ab${blkSwitch?" disabled-btn":""}" ${blkSwitch?`disabled title="Non disponible — dossier verrouillé"`:`onclick="openSwitchMachine(${e.id})" title="Changer de machine"`}>${blkSwitch?BAN:icon('repeat',14)}</button>
      <button type="button" class="ab mov${blkUp?" disabled-btn":""}" ${blkUp?`disabled title="Non disponible"`:`onclick="moveEntry(${e.id},-1)" title="Monter"`}>${blkUp?BAN:icon('arrow-up',14)}</button>
      <button type="button" class="ab mov${blkDown?" disabled-btn":""}" ${blkDown?`disabled title="Non disponible"`:`onclick="moveEntry(${e.id},+1)" title="Descendre"`}>${blkDown?BAN:icon('arrow-down',14)}</button>
      <button type="button" class="ab${blkSplit?" disabled-btn":""}" ${blkSplit?`disabled title="Non disponible — dossier verrouillé"`:`onclick="splitEntry(${e.id})" title="Diviser en 2"`}>${blkSplit?BAN:icon('scissors',14)}</button>
      <button type="button" class="ab${blkInsert?" disabled-btn":""}" ${blkInsert?`disabled title="Non disponible"`:`onclick="openInsert(${e.id})" title="Insérer après"`}>${blkInsert?BAN:icon('corner-down-right',14)}</button>
      ${e.statut==="termine"
        ?`<button type="button" class="ab" disabled title="Non disponible — dossier terminé">${BAN}</button>`
        :e.statut==="en_cours"
          ?`<button type="button" class="ab del" onclick="if(confirm('Supprimer ce dossier en cours ? Le suivant passera automatiquement en cours.'))delEntry(${e.id})" title="Supprimer (en cours)">${icon('trash-2',14)}</button>`
          :`<button type="button" class="ab del" onclick="if(confirm('Supprimer ?'))delEntry(${e.id})" title="Supprimer">${icon('trash-2',14)}</button>`
      }`;
      })():""}
    </div></div>`;
}

async function moveEntry(entryId,delta){
  if(!CAN_EDIT) return;
  const idx = S.entries.findIndex(e=>e.id===entryId);
  if(idx<0) return;
  const cur = S.entries[idx];
  if(!cur || cur.statut==="en_cours" || cur.statut==="termine") return;
  const ni = idx + delta;
  if(ni<0 || ni>=S.entries.length) return;
  const target = S.entries[ni];
  if(target && (target.statut==="en_cours" || target.statut==="termine")) return;

  const ids=S.entries.map(e=>e.id);
  const [m]=ids.splice(idx,1);
  ids.splice(ni,0,m);
  const savedScroll = document.querySelector(".main")?.scrollTop ?? 0;
  const savedTbodyScroll = document.getElementById("tbody")?.scrollTop ?? 0;
  _suppressAutoScroll = true;
  try{
    await api(`/machines/${MID}/reorder`,{method:"POST",body:JSON.stringify({entry_ids:ids})});
    await load();
  }catch(e){
    alert("Réordonnancement impossible");
    await load();
  }finally{
    _suppressAutoScroll = false;
    requestAnimationFrame(()=>requestAnimationFrame(()=>{
      const main=document.querySelector(".main");
      if(main) main.scrollTop=savedScroll;
      const tbody=document.getElementById("tbody");
      if(tbody&&savedTbodyScroll>0) tbody.scrollTop=savedTbodyScroll;
    }));
  }
}

// ── Tooltip ──
let tipEl=null;
let _hoveredSlotEid=null;
function showTip(ev,el){hideTip();const d=el.dataset;_hoveredSlotEid=d.eid?+d.eid:null;tipEl=document.createElement("div");tipEl.className="tip";
  tipEl.style.borderColor=(d.co||"#888")+"55";
  const sub=d.lbl?`<div class="tip-lbl">${d.lbl}</div>`:"";
  tipEl.innerHTML=`<div class="tip-hdr"><div class="tip-bar" style="background:${d.co||"#888"}"></div><div><div class="tip-ref">${d.ref||"—"}</div>${sub}</div></div>
    <div class="tip-grid">${d.rfp?`<span class="k">Réf produit</span><span class="v">${d.rfp}</span>`:""}<span class="k">Format</span><span class="v">${d.fmt||"—"}</span><span class="k">Durée</span><span class="v">${d.dur||""}</span>
    <span class="k">Début</span><span class="v">${d.deb||""}</span><span class="k">Fin</span><span class="v">${d.fin||""}</span>
    <span class="k">Statut</span><span class="v" style="color:${d.st==="En cours"?"var(--green)":d.st==="Terminé"?"var(--muted)":"var(--amber)"};font-weight:600">${d.st||""}</span>
    ${(()=>{const r=d.statutReel||"";if(r==="reellement_termine")return`<span class="k">Saisie</span><span class="v" style="color:var(--muted)">✓ Terminé</span>`;if(r==="reellement_en_saisie")return`<span class="k">Saisie</span><span class="v" style="color:var(--success)">⚙ En cours</span>`;return"";})()} </div>
    ${CAN_EDIT&&d.st!=="Terminé"?`<div style="margin-top:10px;font-size:10px;color:var(--muted);text-align:center;letter-spacing:.5px">↵ Entrée · double-clic pour modifier</div>`:""}`
  el.closest(".tl-wrap").appendChild(tipEl);moveTip(ev)}
function moveTip(ev){if(!tipEl)return;const c=tipEl.parentElement.getBoundingClientRect();
  let x=ev.clientX-c.left+12,y=ev.clientY-c.top-tipEl.offsetHeight-12;
  if(x+tipEl.offsetWidth>c.width)x=c.width-tipEl.offsetWidth-8;if(x<0)x=8;if(y<0)y=ev.clientY-c.top+20;
  tipEl.style.left=x+"px";tipEl.style.top=y+"px"}
function hideTip(){if(tipEl){tipEl.remove();tipEl=null;}_hoveredSlotEid=null;}
document.addEventListener("keydown",ev=>{
  if(ev.key==="Enter"&&_hoveredSlotEid!=null&&CAN_EDIT){
    hideTip();
    openEdit(_hoveredSlotEid);
    ev.preventDefault();
  }
});

// ── Tooltip "ligne maintenant" ──
let nowTipEl=null;
function showNowTip(ev,el){
  hideNowTip();
  const d=el.dataset||{};
  nowTipEl=document.createElement("div");
  nowTipEl.className="tip";
  nowTipEl.style.borderColor="rgba(248,113,113,.35)";
  nowTipEl.innerHTML=`<div class="tip-hdr"><div class="tip-bar" style="background:var(--red)"></div><div>
    <div class="tip-ref">${escAttr(d.time||"—")}</div>
    <div class="tip-lbl">${escAttr(d.state||"")}</div>
  </div></div>`;
  el.closest(".tl-wrap").appendChild(nowTipEl);
  moveNowTip(ev);
}
function moveNowTip(ev){
  if(!nowTipEl)return;
  const c=nowTipEl.parentElement.getBoundingClientRect();
  let x=ev.clientX-c.left+12,y=ev.clientY-c.top-nowTipEl.offsetHeight-12;
  if(x+nowTipEl.offsetWidth>c.width)x=c.width-nowTipEl.offsetWidth-8;
  if(x<0)x=8;
  if(y<0)y=ev.clientY-c.top+20;
  nowTipEl.style.left=x+"px";
  nowTipEl.style.top=y+"px";
}
function hideNowTip(){if(nowTipEl){nowTipEl.remove();nowTipEl=null}}

// ── Drag & Drop ──
// Variables globales pour le DnD de la liste des dossiers
let _ddDragIdx=null;      // Index de l'élément draggué dans S.entries
let _ddDropIdx=null;      // Index d'insertion calculé
let _ddIndicator=null;    // Élément DOM de l'indicateur de drop
let _ddAutoScrollInterval=null; // Timer pour l'auto-scroll

function setupDD(){
  if(!CAN_EDIT) return;

  const tbody=document.getElementById("tbody");
  if(!tbody) return;

  // Créer l'indicateur de drop s'il n'existe pas
  if(!_ddIndicator){
    _ddIndicator=document.createElement("div");
    _ddIndicator.className="drop-indicator";
    _ddIndicator.style.display="none";
    tbody.style.position="relative";
    tbody.appendChild(_ddIndicator);
  }

  // Récupérer toutes les lignes visibles (filtrées)
  const getVisibleRows=()=>Array.from(tbody.querySelectorAll(".tr[draggable]"));

  // Nettoyage
  function clearState(){
    _ddDragIdx=null;
    _ddDropIdx=null;
    if(_ddIndicator) _ddIndicator.style.display="none";
    tbody.querySelectorAll(".tr.dra").forEach(r=>r.classList.remove("dra"));
    tbody.querySelectorAll(".tr.dov").forEach(r=>r.classList.remove("dov"));
    stopAutoScroll();
  }

  // Arrêter l'auto-scroll
  function stopAutoScroll(){
    if(_ddAutoScrollInterval){
      clearInterval(_ddAutoScrollInterval);
      _ddAutoScrollInterval=null;
    }
  }

  // Démarrer l'auto-scroll
  function startAutoScroll(direction){
    stopAutoScroll();
    const scrollSpeed=8; // pixels par frame
    _ddAutoScrollInterval=setInterval(()=>{
      const currentScroll=tbody.scrollTop;
      const maxScroll=tbody.scrollHeight-tbody.clientHeight;
      if(direction==="up" && currentScroll>0){
        tbody.scrollTop=Math.max(0,currentScroll-scrollSpeed);
      }else if(direction==="down" && currentScroll<maxScroll){
        tbody.scrollTop=Math.min(maxScroll,currentScroll+scrollSpeed);
      }
    },16);
  }

  // Mettre à jour la position de l'indicateur
  function updateIndicator(yPosition){
    if(!_ddIndicator) return;
    _ddIndicator.style.display="block";
    _ddIndicator.style.top=yPosition+"px";
  }

  // Calculer l'index d'insertion basé sur la position Y
  function calculateDropIndex(clientY){
    const rows=getVisibleRows();
    if(rows.length===0) return 0;

    const tbodyRect=tbody.getBoundingClientRect();
    const relativeY=clientY-tbodyRect.top+tbody.scrollTop;

    // Trouver la ligne survolée
    for(let i=0;i<rows.length;i++){
      const row=rows[i];
      const rect=row.getBoundingClientRect();
      const rowTop=rect.top-tbodyRect.top+tbody.scrollTop;
      const rowBottom=rowTop+rect.height;

      // Si on est au-dessus de cette ligne, insérer avant
      if(relativeY<rowTop+rect.height/2){
        // Convertir l'index visible en index réel
        const realIdx=parseInt(row.dataset.idx,10);
        return {insertIdx:realIdx,indicatorY:rowTop-1};
      }
    }

    // Si on est en dessous de toutes les lignes, insérer à la fin
    const lastRow=rows[rows.length-1];
    const lastRect=lastRow.getBoundingClientRect();
    const lastBottom=(lastRect.top-tbodyRect.top+tbody.scrollTop)+lastRect.height;
    const lastRealIdx=parseInt(lastRow.dataset.idx,10);
    return {insertIdx:lastRealIdx+1,indicatorY:lastBottom-1};
  }

  // Event delegation sur le tbody
  tbody.addEventListener("dragstart",(e)=>{
    const row=e.target.closest(".tr[draggable]");
    if(!row) return;
    _ddDragIdx=parseInt(row.dataset.idx,10);
    row.classList.add("dra");
    e.dataTransfer.effectAllowed="move";
  });

  tbody.addEventListener("dragover",(e)=>{
    e.preventDefault();
    if(_ddDragIdx===null) return;
    e.dataTransfer.dropEffect="move";

    // Auto-scroll quand on approche des bords
    const tbodyRect=tbody.getBoundingClientRect();
    const relativeY=e.clientY-tbodyRect.top;
    const scrollZone=40; // pixels depuis le bord pour déclencher l'auto-scroll

    if(relativeY<scrollZone){
      startAutoScroll("up");
    }else if(relativeY>tbodyRect.height-scrollZone){
      startAutoScroll("down");
    }else{
      stopAutoScroll();
    }

    // Calculer et afficher l'indicateur
    const result=calculateDropIndex(e.clientY);
    _ddDropIdx=result.insertIdx;
    updateIndicator(result.indicatorY);

    // Highlight visuel sur la ligne survolée
    const targetRow=e.target.closest(".tr[draggable]");
    tbody.querySelectorAll(".tr.dov").forEach(r=>r.classList.remove("dov"));
    if(targetRow) targetRow.classList.add("dov");
  });

  tbody.addEventListener("dragleave",(e)=>{
    if(!tbody.contains(e.relatedTarget)){
      stopAutoScroll();
    }
  });

  tbody.addEventListener("drop",async (e)=>{
    e.preventDefault();
    stopAutoScroll();

    if(_ddDragIdx===null || _ddDropIdx===null){
      clearState();
      return;
    }

    // Ajuster l'index d'insertion si nécessaire
    let insertAt=_ddDropIdx;
    if(insertAt>_ddDragIdx) insertAt--;
    insertAt=Math.max(0,Math.min(insertAt,S.entries.length-1));

    // Ne rien faire si on drop au même endroit
    if(insertAt===_ddDragIdx){
      clearState();
      return;
    }

    // Sauvegarder les positions de scroll
    const savedScroll=document.querySelector(".main")?.scrollTop??0;
    const savedTbodyScroll=tbody.scrollTop??0;

    // Réordonner
    const ids=S.entries.map(en=>en.id);
    const [moved]=ids.splice(_ddDragIdx,1);
    ids.splice(insertAt,0,moved);

    clearState();
    _suppressAutoScroll=true;

    try{
      await api(`/machines/${MID}/reorder`,{method:"POST",body:JSON.stringify({entry_ids:ids})});
    }catch(err){
      console.error("Reorder failed",err);
    }finally{
      await load();
      _suppressAutoScroll=false;
      requestAnimationFrame(()=>{
        const main=document.querySelector(".main");
        if(main) main.scrollTop=savedScroll;
        if(tbody&&savedTbodyScroll>0) tbody.scrollTop=savedTbodyScroll;
      });
    }
  });

  tbody.addEventListener("dragend",()=>{
    clearState();
  });
}

function setupStatutSelects(){
  if(!CAN_EDIT) return;
  document.querySelectorAll(".statut-select").forEach(sel=>{
    sel.addEventListener("change", async function(){
      const eid=this.dataset.eid;
      const newStat=this.value;
      const oldStat=this.dataset.current||"attente";
      const el=this;
      const doUpdate=async(override=false)=>{
        try{
          const data=await api(`/machines/${MID}/entries/${eid}/statut`,{
            method:"PUT",
            body:JSON.stringify({statut:newStat,force:true,override})
          });
          if(data.warning&&data.code==="NO_SAISIE"){
            const confirmed=confirm(data.message+"\n\nCliquer OK pour terminer quand même, Annuler pour stopper.");
            if(confirmed) await doUpdate(true);
            else{
              el.value=oldStat;
              showToast("Action annulée.","info");
            }
            return;
          }
          if(data.saisie_found===false&&newStat==="termine"){
            showToast("Dossier terminé — aucune saisie de production associée.","info");
          }else if(data.saisie_found===true&&newStat==="termine"){
            showToast("Dossier terminé — saisie trouvée.","success");
          }else{
            showToast("Statut mis à jour.","success");
          }
          el.dataset.current=newStat;
          await load();
        }catch(err){
          let msg="Erreur statut.";
          try{
            if(err&&typeof err.json==="function"){
              const j=await err.json();
              const d=j.detail;
              msg=typeof d==="string"?d:(Array.isArray(d)?d.map(x=>x.msg||JSON.stringify(x)).join(" "):msg);
            }
          }catch(x){}
          showToast(typeof msg==="string"?msg:JSON.stringify(msg),"danger");
          el.value=oldStat;
          await load();
        }
      };
      await doUpdate();
    });
  });
}

// ── API actions ──
async function delEntry(id){await api(`/machines/${MID}/entries/${id}`,{method:"DELETE"});load()}
async function splitEntry(id){
  if(!CAN_EDIT) return;
  const e=S.entries.find(x=>x.id===id);
  if(!e) return;
  if(e.statut==="en_cours"||e.statut==="termine") return alert("Dossier verrouillé");
  if(!confirm("Spliter ce dossier en 2 (mêmes infos) avec durée /2 ?")) return;
  try{
    await api(`/machines/${MID}/entries/${id}/split`,{method:"POST"});
    await load();
  }catch(e){
    console.error(e);
    alert("Split impossible");
    await load();
  }
}

// ── Duplicate entry ──
function duplicateEntry(id){
  if(!CAN_EDIT) return;
  const e=S.entries.find(x=>x.id===id);
  if(!e) return;
  document.getElementById("mroot").innerHTML=modalHTML(
    "Dupliquer le dossier",
    dossierFields(e.numero_of||e.reference||"",e.client||"",e.ref_produit||"",e.laize||"",e.date_livraison||"",e.commentaire||"",e.format_l||"",e.format_h||"",e.duree_heures,"attente",false),
    "Ajouter","submitDuplicate()"
  );
}
async function submitDuplicate(){
  const d=getFormData(false);
  if(!d.numero_of)return alert("Numero d'OF requis");
  await api(`/machines/${MID}/entries`,{method:"POST",body:JSON.stringify({reference:d.numero_of,...d})});
  closeM();load();
}

// ── Switch machine ──
let _switchEntryId=null;
function openSwitchMachine(entryId){
  if(!CAN_EDIT) return;
  const e=S.entries.find(x=>x.id===entryId);
  if(!e) return;
  if(e.statut==="en_cours"||e.statut==="termine") return alert("Dossier verrouille - impossible de changer de machine");
  _switchEntryId=entryId;
  const otherMachines=S.machines.filter(m=>m.id!==MID);
  if(otherMachines.length===0) return alert("Aucune autre machine disponible");
  const machineOptions=otherMachines.map(m=>`<option value="${m.id}">${escAttr(m.nom||'')}</option>`).join("");
  document.getElementById("mroot").innerHTML=`<div class="mo" onclick="if(event.target===this)closeM()"><div class="md"><h3>Changer de machine</h3>
    <div class="fd"><label>Selectionner la machine cible</label>
    <select id="f-target-machine" style="width:100%;padding:10px 14px;background:var(--bg);border:1px solid var(--border2);border-radius:8px;color:var(--text);font-size:14px;font-family:var(--mono)">
      ${machineOptions}
    </select></div>
    <div class="md-acts"><button class="btn-s" onclick="closeM()">Annuler</button>
    <button class="btn-p" onclick="showTargetDossiers()">Continuer</button></div></div></div>`;
}
async function showTargetDossiers(){
  const targetMachineId=parseInt(document.getElementById("f-target-machine").value);
  if(!targetMachineId) return;
  const e=S.entries.find(x=>x.id===_switchEntryId);
  if(!e) return closeM();
  document.getElementById("mroot").innerHTML=`<div class="mo" onclick="if(event.target===this)closeM()"><div class="md" style="width:600px;max-width:95vw;"><h3>Inserer apres quel dossier ?</h3>
    <p style="font-size:12px;color:var(--muted);margin:-12px 0 12px">Cliquez sur un dossier pour inserer <strong>${escAttr(e.client||e.numero_of||'')}</strong> apres celui-ci.</p>
    <div id="switch-dossier-list" style="max-height:400px;overflow:auto;border:1px solid var(--border2);border-radius:8px;">
      <div style="padding:20px;text-align:center;color:var(--muted)">Chargement...</div>
    </div>
    <div class="md-acts"><button class="btn-s" onclick="closeM()">Annuler</button></div></div></div>`;
  try{
    const targetEntries=await api(`/machines/${targetMachineId}/entries`);
    const listEl=document.getElementById("switch-dossier-list");
    const pendingEntries=(targetEntries||[]).filter(en=>en.statut!=="termine");
    if(pendingEntries.length===0){
      listEl.innerHTML=`<div style="padding:20px;text-align:center;color:var(--muted)">Aucun dossier en attente/en cours sur cette machine.<br><br><button class="btn-p" onclick="confirmSwitch(${targetMachineId},null)">Ajouter en premiere position</button></div>`;
    }else{
      listEl.innerHTML=`<div style="padding:8px;border-bottom:1px solid var(--border2);background:var(--accent-bg);cursor:pointer;" onclick="confirmSwitch(${targetMachineId},null)">
        <strong>Ajouter en premiere position</strong> (avant tous les dossiers)
      </div>`+pendingEntries.map((en,idx)=>{
        const fm=en.format_l&&en.format_h?`${en.format_l}x${en.format_h}`:"—";
        const stat=en.statut==="en_cours"?"🔴 En cours":"⚪ Attente";
        const nextEn=pendingEntries[idx+1];
        const nextId=nextEn?nextEn.id:null;
        return`<div style="padding:10px 12px;border-bottom:1px solid var(--border2);cursor:pointer;background:var(--bg);" onmouseover="this.style.background='var(--accent-bg)'" onmouseout="this.style.background='var(--bg)'" onclick="confirmSwitch(${targetMachineId},${en.id})">
          <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
            <span style="font-weight:600">${escAttr(en.client||"—")}</span>
            <span style="color:var(--muted);font-size:12px">| OF: ${escAttr(en.numero_of||en.reference||"—")}</span>
            <span style="color:var(--muted);font-size:12px">| ${escAttr(fm)}</span>
            <span style="margin-left:auto;font-size:12px">${stat}</span>
          </div>
          <div style="font-size:11px;color:var(--muted);margin-top:4px">Cliquez pour inserer apres ce dossier</div>
        </div>`;
      }).join("");
    }
  }catch(err){
    document.getElementById("switch-dossier-list").innerHTML=`<div style="padding:20px;text-align:center;color:var(--danger)">Erreur de chargement</div>`;
  }
}
async function confirmSwitch(targetMachineId,afterEntryId){
  if(!_switchEntryId) return;
  if(!confirm("Confirmer le deplacement de ce dossier vers l'autre machine ?")) return;
  try{
    const e=S.entries.find(x=>x.id===_switchEntryId);
    if(!e) throw new Error("Dossier introuvable");
    await api(`/machines/${MID}/entries/${_switchEntryId}`,{method:"DELETE"});
    if(afterEntryId){
      await api(`/machines/${targetMachineId}/insert-after/${afterEntryId}`,{method:"POST",body:JSON.stringify({
        reference:e.numero_of||e.reference||"",
        numero_of:e.numero_of||e.reference||"",
        client:e.client||"",
        ref_produit:e.ref_produit||"",
        laize:e.laize||null,
        date_livraison:e.date_livraison||"",
        commentaire:e.commentaire||"",
        format_l:e.format_l||null,
        format_h:e.format_h||null,
        duree_heures:e.duree_heures||8,
        statut:"attente"
      })});
    }else{
      await api(`/machines/${targetMachineId}/entries`,{method:"POST",body:JSON.stringify({
        reference:e.numero_of||e.reference||"",
        numero_of:e.numero_of||e.reference||"",
        client:e.client||"",
        ref_produit:e.ref_produit||"",
        laize:e.laize||null,
        date_livraison:e.date_livraison||"",
        commentaire:e.commentaire||"",
        format_l:e.format_l||null,
        format_h:e.format_h||null,
        duree_heures:e.duree_heures||8,
        statut:"attente"
      })});
    }
    closeM();
    _switchEntryId=null;
    load();
  }catch(err){
    alert("Erreur lors du deplacement: "+(err.message||"Erreur"));
    closeM();
  }
}

// ── Modals ──
function durBar(v){return((v-MIND)/(MAXD-MIND)*100)+"%"}

function modalHTML(title,fields,submitLabel,onSubmitFn,headerAction="",footerLeft=""){
  return`<div class="mo" onclick="if(event.target===this)closeM()"><div class="md">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:24px;gap:12px;flex-wrap:wrap">
      <h3 style="margin:0;font-size:18px;font-family:var(--mono);color:var(--text);line-height:1.3">${title}</h3>
      ${headerAction?`<div style="flex-shrink:0">${headerAction}</div>`:""}
    </div>
    ${fields}
    <div class="md-acts" style="display:flex;align-items:center;justify-content:${footerLeft?"space-between":"flex-end"};gap:10px;flex-wrap:wrap">
      ${footerLeft?`<div>${footerLeft}</div>`:""}
      <div style="display:flex;align-items:center;gap:10px">
        <button class="btn-s" onclick="closeM()">Annuler</button>
        <button class="btn-p" onclick="${onSubmitFn}">${submitLabel}</button>
      </div>
    </div></div></div>`
}

function dossierFields(numero_of,client,ref_produit,laize,date_livraison,commentaire,fl,fh,dur,statut,showStatut,aPlacer=1){
  return`
    <div class="fd"><label>Numéro d'OF</label><input id="f-of" value="${numero_of}" placeholder="9936280"></div>
    <div class="fd"><label>Client</label><input id="f-cli" value="${client}" placeholder="Nom du client"></div>
    <div class="fd"><label>Réf produit</label><input id="f-rp" value="${ref_produit}" placeholder="REF-PROD"></div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
      <div class="fd"><label>Largeur (mm)</label><input type="number" id="f-fl" value="${fl}" placeholder="100"></div>
      <div class="fd"><label>Hauteur (mm)</label><input type="number" id="f-fh" value="${fh}" placeholder="70"></div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
      <div class="fd"><label>Laize (mm)</label><input type="number" id="f-laize" value="${laize}" placeholder="510"></div>
      <div class="fd"><label>Date livraison</label><input type="date" id="f-dl" value="${/^\d{4}-\d{2}-\d{2}$/.test(date_livraison)?date_livraison:''}"></div>
    </div>
    <div class="fd"><label>Commentaire</label><input id="f-com" value="${commentaire}" placeholder="Bobine, contraintes, etc."></div>
    <div class="fd"><label>Durée (${MIND}–${MAXD}h)</label>
      <input type="number" id="f-dur" min="${MIND}" max="${MAXD}" step="0.25" value="${dur}" oninput="document.getElementById('f-dur-fill').style.width=((Math.max(${MIND},Math.min(${MAXD},+this.value||${MIND}))-${MIND})/(${MAXD}-${MIND})*100)+'%'">
      <div class="dur-b"><div class="dur-f" id="f-dur-fill" style="width:${durBar(dur)}"></div></div>
    </div>
    <div class="fd" style="margin-top:4px">
      <label style="display:flex;align-items:center;gap:10px;cursor:pointer;font-size:13px;color:var(--text2);text-transform:none;letter-spacing:0">
        <input type="checkbox" id="f-aplacer" ${aPlacer?"checked":""} style="width:16px;height:16px;accent-color:var(--accent);cursor:pointer">
        À placer au planning
      </label>
    </div>
    ${showStatut?`<div class="fd"><label>Statut</label><select id="f-stat">
      <option value="attente" ${statut==="attente"?"selected":""}>En attente</option>
      <option value="en_cours" ${statut==="en_cours"?"selected":""}>En cours</option>
      <option value="termine" ${statut==="termine"?"selected":""}>Terminé</option>
    </select></div>`:""}`
}

function getFormData(withStatut){
  const d={
    numero_of:(document.getElementById("f-of").value||"").trim(),
    client:document.getElementById("f-cli").value||"",
    ref_produit:document.getElementById("f-rp").value||"",
    format_l:parseFloat(document.getElementById("f-fl").value)||null,
    format_h:parseFloat(document.getElementById("f-fh").value)||null,
    laize:parseFloat(document.getElementById("f-laize").value)||null,
    date_livraison:document.getElementById("f-dl").value||"",
    commentaire:document.getElementById("f-com").value||"",
    duree_heures:Math.max(MIND,Math.min(MAXD,parseFloat(document.getElementById("f-dur").value)||8)),
    a_placer:document.getElementById("f-aplacer")?.checked?1:0,
  };
  if(withStatut)d.statut=document.getElementById("f-stat").value;
  return d;
}

function openAdd(){
  if(!CAN_EDIT) return;
  document.getElementById("mroot").innerHTML=modalHTML(
    "Ajouter un dossier",
    dossierFields("","","","","","","","",8,"attente",false),
    '<span style="font-size:18px;line-height:1">+</span> Ajouter',"submitAdd()"
  );
}
async function submitAdd(){
  const d=getFormData(false);
  if(!d.numero_of)return alert("Numéro d'OF requis");
  await api(`/machines/${MID}/entries`,{method:"POST",body:JSON.stringify({reference:d.numero_of,...d})});
  closeM();load();
}

function openEdit(id){
  if(!CAN_EDIT) return;
  const e=S.entries.find(x=>x.id===id);if(!e)return;

  const isLocked=(e.statut==="en_cours"||e.statut==="termine");
  const isTermine=e.statut==="termine";
  const statLabel=isTermine?"Terminé":e.statut==="en_cours"?"En cours":"";
  const statColor=isTermine?"var(--danger)":"var(--accent)";

  const fieldsHtml=dossierFields(e.numero_of||e.reference||"",e.client||"",e.ref_produit||"",e.laize||"",e.date_livraison||"",e.commentaire||"",e.format_l||"",e.format_h||"",e.duree_heures,e.statut,true,e.a_placer??1);

  // Bouton déstockage compact en en-tête
  const destockDone=e.destockage==="done";
  const destockBg=destockDone?"rgba(56,189,248,.12)":"rgba(251,146,60,.10)";
  const destockBorder=destockDone?"#38bdf8":"#fb923c";
  const destockColor=destockDone?"#38bdf8":"#fb923c";
  const destockIcon=destockDone?`<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`:`<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/></svg>`;
  const reelNonDefault=e.statut_reel&&e.statut_reel!=="reellement_en_attente";
  const resetBlock=(IS_DIR_OR_SUPER&&reelNonDefault)?`<button type="button" class="btn-reset-saisie" data-eid="${id}" onclick="resetSaisieFromModal(${id})" style="margin-top:8px;width:100%;padding:7px;border-radius:6px;border:1px solid rgba(248,113,113,.4);background:rgba(248,113,113,.08);color:var(--danger);font-size:11px;cursor:pointer;font-family:inherit;display:flex;align-items:center;justify-content:center;gap:6px">${icon('repeat',12)} Réinitialiser la saisie réelle</button>`:"";
  const headerAction=`<div style="display:flex;gap:8px;flex-wrap:wrap"><button type="button" id="destock-btn-${id}" onclick="toggleDestockage(${id})"
    title="${destockDone?"Matières destockées — cliquer pour annuler":"Matières à destocker — cliquer pour valider"}"
    style="display:flex;align-items:center;gap:6px;padding:6px 12px;border-radius:6px;border:1.5px solid ${destockBorder};background:${destockBg};color:${destockColor};font-size:12px;font-weight:600;cursor:pointer;transition:all .2s;font-family:inherit;white-space:nowrap"
    onmouseenter="this.style.opacity='.75'" onmouseleave="this.style.opacity='1'">
    ${destockIcon}
    <span>${destockDone?"Destocké":"À destocker"}</span>
  </button></div>`;

  // Traçabilité création/modification
  const fmtDate=(iso)=>{
    if(!iso) return null;
    const d=new Date(iso);
    return d.toLocaleDateString('fr-FR',{day:'2-digit',month:'2-digit'});
  };
  const fmtDateTime=(iso)=>{
    if(!iso) return null;
    const d=new Date(iso);
    return d.toLocaleDateString('fr-FR',{day:'2-digit',month:'2-digit'})+' '+d.toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit'});
  };
  const createdAt=fmtDate(e.created_at);
  const updatedAt=fmtDateTime(e.updated_at);
  const createdBy=e.created_by||"—";
  const updatedBy=e.updated_by||e.created_by||"—";
  const traceParts=[];
  if(createdAt) traceParts.push(`créé par ${escAttr(createdBy)} le ${createdAt}`);
  if(updatedAt && e.updated_at!==e.created_at) traceParts.push(`Dernière modification le ${escAttr(updatedAt)} par ${escAttr(updatedBy)}`);
  const traceHtml=traceParts.length?`<div style="margin-top:16px;padding-top:12px;border-top:1px solid var(--border2);font-size:11px;color:var(--muted);line-height:1.5">${traceParts.join(' | ')}</div>`:"";

  const titlePrefix=statLabel?`<span style="color:${statColor};font-size:11px;font-weight:600;letter-spacing:.5px;text-transform:uppercase;margin-right:6px">${statLabel}</span>`:"";

  const delBtn=isTermine
    ?`<button type="button" disabled style="display:flex;align-items:center;gap:5px;padding:6px 12px;border-radius:6px;border:1px solid var(--border2);background:transparent;color:var(--muted);font-size:12px;cursor:not-allowed;opacity:.4;font-family:inherit" title="Suppression impossible — dossier terminé">${icon('trash-2',14)} Supprimer</button>`
    :`<button type="button" onclick="if(confirm('Supprimer ce dossier ?')){closeM();delEntry(${id})}" style="display:flex;align-items:center;gap:5px;padding:6px 12px;border-radius:6px;border:1px solid var(--danger);background:rgba(248,113,113,.08);color:var(--danger);font-size:12px;font-weight:600;cursor:pointer;transition:all .15s;font-family:inherit" onmouseenter="this.style.background='rgba(248,113,113,.18)'" onmouseleave="this.style.background='rgba(248,113,113,.08)'" title="Supprimer ce dossier">${icon('trash-2',14)} Supprimer</button>`;

  document.getElementById("mroot").innerHTML=modalHTML(
    `${titlePrefix}${(e.numero_of||e.reference)||''}`,
    fieldsHtml+traceHtml+resetBlock,
    "Enregistrer",`submitEdit(${id})`,
    headerAction,
    delBtn
  );
}

async function submitEditDuree(id){
  const dur=parseInt(document.getElementById("f-dur").value)||0;
  if(dur<MIND||dur>720)return alert(`Durée entre ${MIND} et 720h`);
  try{
    await api(`/machines/${MID}/entries/${id}`,{method:"PUT",body:JSON.stringify({duree_heures:dur})});
    closeM();load();
  }catch(err){
    let msg="Modification impossible.";
    try{const j=await err.json();if(j&&j.detail)msg=typeof j.detail==="string"?j.detail:JSON.stringify(j.detail);}catch(x){}
    alert(msg);
  }
}

async function submitEdit(id){
  const d=getFormData(true);
  if(!d.numero_of)return alert("Numéro d'OF requis");
  try{
    await api(`/machines/${MID}/entries/${id}`,{method:"PUT",body:JSON.stringify({reference:d.numero_of,...d})});
    closeM();load();
  }catch(err){
    let msg="Modification impossible.";
    try{const j=await err.json();if(j&&j.detail)msg=typeof j.detail==="string"?j.detail:JSON.stringify(j.detail);}catch(x){}
    alert(msg);
  }
}

function openInsert(afterId){
  if(!CAN_EDIT) return;
  try{
    const idx = S.entries.findIndex(e=>e.id===afterId);
    if(idx>=0){
      const nxt = S.entries[idx+1];
      if(nxt && (nxt.statut==="en_cours" || nxt.statut==="termine")){
        alert("⦸ Impossible d'insérer une ligne avant un dossier En cours / Terminé.");
        return;
      }
    }
  }catch(e){}
  document.getElementById("mroot").innerHTML=modalHTML(
    "Insérer un dossier après",
    dossierFields("","","","","","","","",8,"attente",false),
    "Insérer",`submitInsert(${afterId})`
  );
}
async function submitInsert(afterId){
  const d=getFormData(false);
  if(!d.numero_of)return alert("Numéro d'OF requis");
  await api(`/machines/${MID}/insert-after/${afterId}`,{method:"POST",body:JSON.stringify({reference:d.numero_of,...d})});
  closeM();load();
}

function closeM(){document.getElementById("mroot").innerHTML=""}

function exportDossiers(){
  if(!S.entries||!S.entries.length) return alert("Aucun dossier à exporter");
  const statLabel=s=>s==="en_cours"?"En cours":s==="termine"?"Terminé":"En attente";
  const reelLabel=r=>{
    if(r==="reellement_termine") return "Saisie terminée";
    if(r==="reellement_en_saisie") return "En saisie";
    return "";
  };
  const rows=S.entries.map(e=>({
    "Client":       e.client||"",
    "Format":       e.format_l&&e.format_h?`${e.format_l}×${e.format_h} mm`:"",
    "Réf OF":       e.numero_of||e.reference||"",
    "Réf produit":  e.ref_produit||"",
    "Laize":        e.laize!=null?e.laize:"",
    "Livraison":    e.date_livraison||"",
    "Commentaire":  e.commentaire||"",
    "Durée (h)":    e.duree_heures||0,
    "Statut":       statLabel(e.statut),
    "Saisie réelle":reelLabel(e.statut_reel),
    "Déstockage":   e.destockage==="done"?"Oui":"Non",
  }));
  const ws=XLSX.utils.json_to_sheet(rows);
  const colW=[18,16,14,14,8,12,24,10,12,14,10];
  ws["!cols"]=colW.map(w=>({wch:w}));
  const wb=XLSX.utils.book_new();
  const mName=(S.machine&&S.machine.nom)||"planning";
  XLSX.utils.book_append_sheet(wb,ws,mName.slice(0,31));
  const d=new Date();
  const ts=`${d.getFullYear()}${String(d.getMonth()+1).padStart(2,"0")}${String(d.getDate()).padStart(2,"0")}`;
  XLSX.writeFile(wb,`planning_${mName.replace(/[^a-zA-Z0-9]/g,"_")}_${ts}.xlsx`);
}

async function openImportOrphan(){
  if(!CAN_EDIT) return;
  document.getElementById("mroot").innerHTML=`<div class="mo" onclick="if(event.target===this)closeM()"><div class="md" style="max-width:620px">
    <h3 style="margin:0 0 6px;font-size:16px;font-family:var(--mono)">Importer un dossier depuis les saisies</h3>
    <p style="margin:0 0 16px;font-size:12px;color:var(--muted)">Dossiers saisis en production sur cette machine, non encore au planning.</p>
    <div id="orphan-list" style="max-height:50vh;overflow-y:auto"><div style="padding:24px;text-align:center;color:var(--muted)">Chargement…</div></div>
    <div class="md-acts" style="display:flex;justify-content:flex-end;margin-top:16px"><button class="btn-s" onclick="closeM()">Fermer</button></div>
  </div></div>`;
  try{
    const r=await api(`/machines/${MID}/orphan-dossiers`);
    const list=r.dossiers||[];
    const el=document.getElementById("orphan-list");
    if(!el) return;
    if(list.length===0){
      el.innerHTML='<div style="padding:24px;text-align:center;color:var(--muted)">Aucun dossier orphelin trouvé sur cette machine.</div>';
      return;
    }
    el.innerHTML=`<table style="width:100%;border-collapse:collapse;font-size:12px">
      <thead><tr style="border-bottom:2px solid var(--border2);text-align:left">
        <th style="padding:8px 6px;color:var(--muted);font-weight:600">Réf / OF</th>
        <th style="padding:8px 6px;color:var(--muted);font-weight:600">Client</th>
        <th style="padding:8px 6px;color:var(--muted);font-weight:600">Début</th>
        <th style="padding:8px 6px;color:var(--muted);font-weight:600">Fin</th>
        <th style="padding:8px 6px;color:var(--muted);font-weight:600">Durée</th>
        <th style="padding:8px 6px"></th>
      </tr></thead><tbody>${list.map(d=>{
        const fdt=s=>{if(!s)return"—";try{const x=new Date(s);return x.toLocaleDateString("fr-FR",{day:"2-digit",month:"2-digit"})+" "+x.toLocaleTimeString("fr-FR",{hour:"2-digit",minute:"2-digit"})}catch(e){return s}};
        const dur=d.duree_reelle?d.duree_reelle.toFixed(1)+"h":"—";
        const st=d.has_end?'<span style="color:var(--muted)">Terminé</span>':'<span style="color:var(--accent)">En cours</span>';
        return`<tr style="border-bottom:1px solid var(--border)">
          <td style="padding:8px 6px;font-weight:600;font-family:var(--mono)">${escAttr(d.no_dossier)}</td>
          <td style="padding:8px 6px">${escAttr(d.client||"—")}</td>
          <td style="padding:8px 6px;font-size:11px">${fdt(d.first_start)}</td>
          <td style="padding:8px 6px;font-size:11px">${fdt(d.last_end)}</td>
          <td style="padding:8px 6px;font-family:var(--mono)">${dur}</td>
          <td style="padding:8px 6px;text-align:right">
            <button type="button" class="btn-p" style="padding:5px 12px;font-size:11px" onclick="submitImportOrphan('${escAttr(d.no_dossier)}',this)">Ajouter</button>
          </td>
        </tr>`;
      }).join("")}</tbody></table>`;
  }catch(e){
    const el=document.getElementById("orphan-list");
    if(el) el.innerHTML='<div style="padding:24px;text-align:center;color:var(--danger)">Erreur de chargement.</div>';
  }
}

async function submitImportOrphan(ref,btn){
  if(!CAN_EDIT) return;
  btn.disabled=true;btn.textContent="…";
  try{
    await api(`/machines/${MID}/import-orphan`,{method:"POST",body:JSON.stringify({no_dossier:ref})});
    closeM();load();
  }catch(e){
    btn.disabled=false;btn.textContent="Ajouter";
    let msg="Erreur lors de l'import.";
    try{const j=await e.json();if(j&&j.detail)msg=typeof j.detail==="string"?j.detail:JSON.stringify(j.detail);}catch(x){}
    alert(msg);
  }
}

function changeMachine(v){
  const id=parseInt(v,10);
  if(!id||!isFinite(id))return;
  localStorage.setItem("mysifa.planning.lastMachine",String(id));
  location.href=`/planning?machine=${encodeURIComponent(String(id))}`;
}

function setView(v){
  S.view=v;
  localStorage.setItem("mysifa.planning.view",v);
  load();
}

function openHorairesModal(ds, di){
  if(!CAN_EDIT) return;
  if(!S.machine) return;
  // Lire les horaires actuels pour cette date (override ou hebdo)
  const dateObj = ds ? new Date(ds) : new Date();
  const {s,e} = getWhForDate(di, dateObj, ds);
  const dn = {1:"Lundi",2:"Mardi",3:"Mercredi",4:"Jeudi",5:"Vendredi",6:"Samedi"}[di]||"Jour";
  // Afficher la date lisible
  const dateLabel = ds ? new Date(ds+'T12:00:00').toLocaleDateString('fr-FR',{weekday:'long',day:'numeric',month:'long'}) : dn;
  const hasOverride = !!(ds && S.dayHoraires && S.dayHoraires[ds]);
  document.getElementById("mroot").innerHTML=modalHTML(
    `Plage horaire — ${dateLabel}`,
    `<p style="font-size:12px;color:var(--muted);margin:-8px 0 16px">
      Horaire pour ce jour uniquement${hasOverride?' <span style="color:var(--accent);font-weight:700">· Override actif</span>':''}.
    </p>
    <div class="fd"><label>Début (HH:MM)</label><input type="text" inputmode="numeric" placeholder="07:00" id="f-h-start" value="${fracToTimeInput(s)}"></div>
    <div class="fd"><label>Fin de journée (HH:MM)</label><input type="text" inputmode="numeric" placeholder="19:00" id="f-h-end" value="${fracToTimeInput(e)}"></div>
    ${hasOverride?`<div style="margin-top:10px;text-align:right"><button type="button" class="btn-s" style="color:var(--danger);border-color:var(--danger)" onclick="resetHorairesDate('${ds}')">Réinitialiser au modèle hebdo</button></div>`:''}`,
    "Enregistrer",
    `submitHoraires('${ds}')`
  );
}
async function submitHoraires(ds){
  if(!CAN_EDIT) return;
  const st=(document.getElementById("f-h-start").value||"").trim();
  const en=(document.getElementById("f-h-end").value||"").trim();
  if(!st||!en) return void alert("Indiquez début et fin.");
  if(!isHHMM(st)||!isHHMM(en)) return void alert("Format attendu : HH:MM (24h). Exemple : 07:00");
  // Convertir HH:MM → fraction décimale
  const toFrac = hhmm => { const [h,m]=hhmm.split(":").map(Number); return h+m/60; };
  const hd = toFrac(st), hf = toFrac(en);
  if(hf <= hd) return void alert("L'heure de fin doit être après le début.");
  try{
    await api(`/machines/${MID}/day-horaires`,{method:"PUT",body:JSON.stringify({date:ds,heure_debut:hd,heure_fin:hf})});
    closeM(); load();
  }catch(err){
    let msg="Modification impossible.";
    try{const j=await err.json();if(j&&j.detail)msg=typeof j.detail==="string"?j.detail:JSON.stringify(j.detail);}catch(x){}
    alert(msg);
  }
}
async function resetHorairesDate(ds){
  try{
    await api(`/machines/${MID}/day-horaires`,{method:"PUT",body:JSON.stringify({date:ds,heure_debut:null})});
    closeM(); load();
  }catch(err){ alert("Impossible de réinitialiser."); }
}

// ── Paramètres semaine ──
function openWeekSettingsModal(monTs){
  if(!CAN_EDIT) return;
  const mon=new Date(monTs);
  const wn=wkNum(mon);
  const DN_FULL={1:"Lundi",2:"Mardi",3:"Mercredi",4:"Jeudi",5:"Vendredi",6:"Samedi"};
  let rows="";
  for(let i=0;i<6;i++){
    const d=addD(mon,i);
    const di=d.getDay();
    if(di===0) continue;
    const ds=ymd(d);
    const isSat=di===6;
    const isOff=isSat?!S.dayWorked[ds]:!!S.holidays[ds];
    const worked=!isOff;
    const wh=getWhForDate(di,d,ds);
    const startVal=fracToTimeInput(wh.s);
    const endVal=fracToTimeInput(wh.e);
    const hasOv=!!(S.dayHoraires&&S.dayHoraires[ds]);
    rows+=`<div style="display:grid;grid-template-columns:72px 90px 1fr 1fr;gap:6px 10px;align-items:center;padding:7px 0;border-bottom:1px solid var(--border)">
      <span style="font-size:12px;font-weight:600;color:var(--text)">${DN_FULL[di]||""}</span>
      <label style="display:flex;align-items:center;gap:6px;font-size:12px;cursor:pointer;color:var(--text2)">
        <input type="checkbox" id="wks-w-${ds}" ${worked?"checked":""}> travaillé
      </label>
      <input type="text" inputmode="numeric" id="wks-s-${ds}" value="${startVal}" placeholder="07:00"
        style="padding:5px 8px;border:1px solid var(--border2);border-radius:6px;background:var(--bg);color:var(--text);font-size:12px;font-family:var(--mono);outline:none;width:100%;min-width:0;box-sizing:border-box"${hasOv?' title="Override actif"':''}>
      <input type="text" inputmode="numeric" id="wks-e-${ds}" value="${endVal}" placeholder="19:00"
        style="padding:5px 8px;border:1px solid var(--border2);border-radius:6px;background:var(--bg);color:var(--text);font-size:12px;font-family:var(--mono);outline:none;width:100%;min-width:0;box-sizing:border-box">
    </div>`;
  }
  document.getElementById("mroot").innerHTML=modalHTML(
    `Paramètres — Semaine S${wn}`,
    `<p style="font-size:12px;color:var(--muted);margin:-8px 0 12px">Jours travaillés et horaires précis pour la semaine S${wn}. Ces réglages supplantent les horaires par défaut.</p>
    <div style="display:grid;grid-template-columns:72px 90px 1fr 1fr;gap:4px 10px;padding:0 0 6px;border-bottom:1px solid var(--border2)">
      <span style="font-size:10px;color:var(--muted)">Jour</span>
      <span style="font-size:10px;color:var(--muted)">État</span>
      <span style="font-size:10px;color:var(--muted)">Début</span>
      <span style="font-size:10px;color:var(--muted)">Fin</span>
    </div>${rows}`,
    "Enregistrer",`submitWeekSettings(${monTs})`
  );
}

async function submitWeekSettings(monTs){
  if(!CAN_EDIT) return;
  const mon=new Date(monTs);
  const toFrac=hhmm=>{const [h,m]=hhmm.split(":").map(Number);return h+m/60;};
  const errors=[];
  const ops=[];
  for(let i=0;i<6;i++){
    const d=addD(mon,i);
    const di=d.getDay();
    if(di===0) continue;
    const ds=ymd(d);
    const isSat=di===6;
    const wEl=document.getElementById(`wks-w-${ds}`);
    const sEl=document.getElementById(`wks-s-${ds}`);
    const eEl=document.getElementById(`wks-e-${ds}`);
    if(!wEl) continue;
    const worked=wEl.checked;
    const st=(sEl?.value||"").trim();
    const en=(eEl?.value||"").trim();
    if(st&&(!isHHMM(st)||!isHHMM(en))){errors.push(`Format horaire invalide — ${ds}`);continue;}
    ops.push({ds,isSat,worked,st,en});
  }
  if(errors.length){alert(errors.join("\n"));return;}
  try{
    for(const op of ops){
      if(op.isSat){
        await api(`/machines/${MID}/day-work`,{method:"PUT",body:JSON.stringify({date:op.ds,is_worked:op.worked?1:0})});
      }else{
        await api(`/machines/${MID}/holidays`,{method:"PUT",body:JSON.stringify({date:op.ds,is_off:op.worked?0:1})});
      }
      if(op.st&&op.en){
        const hd=toFrac(op.st),hf=toFrac(op.en);
        if(hf>hd) await api(`/machines/${MID}/day-horaires`,{method:"PUT",body:JSON.stringify({date:op.ds,heure_debut:hd,heure_fin:hf})});
      }
    }
    closeM(); load();
  }catch(err){
    let msg="Modification impossible.";
    try{const j=await err.json();if(j&&j.detail)msg=typeof j.detail==="string"?j.detail:JSON.stringify(j.detail);}catch(x){}
    alert(msg);
  }
}

function openDefaultsModal(){
  const defs=getMachineDefaults();
  function row(lbl,id,val){
    return `<div class="fd"><label>${lbl} (HH:MM)</label><input type="text" inputmode="numeric" placeholder="07:00" id="${id}" value="${timeInputFromFloat(val)}"></div>`;
  }
  const f=`
    <p style="font-size:12px;color:var(--muted);margin:-8px 0 16px">
      Valeurs par défaut utilisées quand les horaires hebdo (base) sont vides. Elles impactent les fuseaux affichés sur le planning.
    </p>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
      <div style="border:1px solid var(--border2);border-radius:14px;padding:14px">
        <div style="font-family:var(--mono);font-size:12px;color:var(--text);margin-bottom:10px">Semaine paire</div>
        ${row("Semaine paire — début","dp-w-s",defs.pair.week.s)}
        ${row("Semaine paire — fin","dp-w-e",defs.pair.week.e)}
        ${row("Vendredi (paire) — début","dp-f-s",defs.pair.fri.s)}
        ${row("Vendredi (paire) — fin","dp-f-e",defs.pair.fri.e)}
      </div>
      <div style="border:1px solid var(--border2);border-radius:14px;padding:14px">
        <div style="font-family:var(--mono);font-size:12px;color:var(--text);margin-bottom:10px">Semaine impaire</div>
        ${row("Semaine impaire — début","di-w-s",defs.impair.week.s)}
        ${row("Semaine impaire — fin","di-w-e",defs.impair.week.e)}
        ${row("Vendredi (impaire) — début","di-f-s",defs.impair.fri.s)}
        ${row("Vendredi (impaire) — fin","di-f-e",defs.impair.fri.e)}
      </div>
    </div>
    <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:14px">
      <button class="btn-s" onclick="resetDefaults()">Réinitialiser</button>
    </div>
  `;
  const lbl=(S.machine&&S.machine.nom)?S.machine.nom:("Machine "+MID);
  document.getElementById("mroot").innerHTML=modalHTML(
    `Réglages — ${escAttr(lbl)}`,
    f,
    "Enregistrer",
    "submitDefaults()"
  );
}
function resetDefaults(){
  const mk=machineKey();
  const d=DEFAULTS_BY_KEY[mk]||DEFAULTS_BY_KEY["C1"];
  saveMachineDefaults(d);
  closeM();render();
}
function submitDefaults(){
  function v(id){
    const raw=(document.getElementById(id).value||"").trim();
    if(!isHHMM(raw)) return null;
    const f=floatFromTimeInput(raw);
    return (f==null)?0:f;
  }
  const nd={
    pair:{week:{s:v("dp-w-s"),e:v("dp-w-e")},fri:{s:v("dp-f-s"),e:v("dp-f-e")}},
    impair:{week:{s:v("di-w-s"),e:v("di-w-e")},fri:{s:v("di-f-s"),e:v("di-f-e")}},
  };
  function okRange(r){return isFinite(r.s)&&isFinite(r.e)&&r.e>r.s&&r.s>=0&&r.e<=24;}
  if([nd.pair.week,nd.pair.fri,nd.impair.week,nd.impair.fri].some(r=>r.s==null||r.e==null)){
    return alert("Format attendu : HH:MM (24h). Exemple : 07:00");
  }
  if(!okRange(nd.pair.week)||!okRange(nd.pair.fri)||!okRange(nd.impair.week)||!okRange(nd.impair.fri)){
    return alert("Plages invalides (fin > début, entre 0 et 24).");
  }
  saveMachineDefaults(nd);
  closeM();render();
}

async function boot(){
  if(localStorage.getItem("theme")==="light")document.body.classList.add("light");
  document.body.classList.add("has-topbar");
  try{ render(); }catch(e){}
  let r;
  try{r=await fetch("/api/auth/me",{credentials:"include"});}catch(e){location.href="/";return;}
  if(!r.ok){location.href="/";return;}
  ME=await r.json();
  try{
    const list=await api(`/machines`);
    const byName=new Map((list||[]).map(m=>[String(m.nom||""),m]));
    const ordered=[];
    MACHINE_ORDER.forEach(n=>{if(byName.has(n))ordered.push(byName.get(n));});
    (list||[]).forEach(m=>{if(!ordered.find(x=>x.id===m.id))ordered.push(m);});
    S.machines=ordered;

    const sp=new URLSearchParams(location.search||"");
    const raw=sp.get("machine");
    const num=raw?parseInt(raw,10):NaN;
    const ids=new Set(ordered.map(m=>m.id));
    const saved=parseInt(localStorage.getItem("mysifa.planning.lastMachine")||"",10);
    if(!ordered.length){
      MID=0;
    }else if(isFinite(num)&&ids.has(num)){
      MID=num;
    }else if(isFinite(num)&&num>=1&&num<=4){
      const wantedName=MACHINE_ORDER[num-1];
      const wanted=ordered.find(m=>String(m.nom||"")===wantedName);
      if(wanted) MID=wanted.id;
    }else if(isFinite(saved)&&ids.has(saved)){
      MID=saved;
    }else{
      const wanted=ordered[0];
      if(wanted) MID=wanted.id;
    }
  }catch(e){console.error(e);MID=0;}
  await load();
  // Vérifier les annonces de mise à jour après le chargement initial
  checkUpdates();
  // Actualise le dossier actif + allonge le slot en_cours toutes les 30 s
  setInterval(async()=>{
    if(!MID) return;
    try{
      // 1. Vérifier si la durée du dossier en_cours a grandi (live-refresh)
      const lr=await api(`/machines/${MID}/live-refresh`,{method:"POST"});
      if(lr&&lr.updated){
        await load();
        return; // load() actualise aussi activeDossier
      }
    }catch(e){}
    try{
      // 2. Sinon, juste mettre à jour le dossier actif affiché
      const d=await api(`/machines/${MID}/active-dossier`);
      const prev=S.activeDossier?S.activeDossier.no_dossier:null;
      const next=d.dossier?d.dossier.no_dossier:null;
      if(prev!==next){S.activeDossier=d.dossier||null;render();}
    }catch(e){}
  },30000);
}

// ── Popup mises à jour ────────────────────────────────────────────────────────
async function checkUpdates(){
  try{
    const updates=await fetch("/api/updates/pending?scope=planning",{credentials:"include"}).then(r=>r.ok?r.json():[]);
    if(!updates||!updates.length) return;
    showUpdatePopup(updates);
  }catch(e){}
}

function showUpdatePopup(updates){
  const overlay=document.createElement("div");
  overlay.className="upd-overlay";
  const ids=updates.map(u=>u.id);
  const firstTitle=updates[0].titre||"Nouveautés MySifa";
  const bodies=updates.map(u=>`<div class="upd-body">${u.message}</div>`).join("<hr style='border:none;border-top:1px solid var(--border2);margin:16px 0'>");
  overlay.innerHTML=`
    <div class="upd-card">
      <div style="font-size:28px;margin-bottom:8px;text-align:center">🎉</div>
      <h2 style="text-align:center">${firstTitle}</h2>
      <p class="upd-sub" style="text-align:center">Lisez les nouveautés ci-dessous, puis confirmez.</p>
      ${bodies}
      <button class="upd-ok-btn" onclick="acknowledgeUpdates([${ids.join(",")}],this.closest('.upd-overlay'))">
        ✅ J'ai compris — C'est parti !
      </button>
    </div>`;
  document.body.appendChild(overlay);
}

async function acknowledgeUpdates(ids,overlay){
  try{
    await Promise.all(ids.map(id=>fetch(`/api/updates/${id}/acknowledge`,{method:"POST",credentials:"include"})));
  }catch(e){}
  if(overlay) overlay.remove();
}

boot();
</script>
</body>
</html>
"""

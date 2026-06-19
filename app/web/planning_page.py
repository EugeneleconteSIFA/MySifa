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
    of_admin_js = (
        "true"
        if user.get("role") in {"superadmin", "direction", "administration"}
        else "false"
    )
    html = (
        PLANNING_HTML.replace("__MACHINE_ID__", ssr_mid)
        .replace("__IS_OF_ADMIN__", of_admin_js)
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
<link rel="stylesheet" href="/static/mysifa_theme.css">
<link rel="stylesheet" href="/static/mysifa_user_chip.css">
<link rel="stylesheet" href="/static/motion.css">
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
  --slot-l1:#1e293b;--slot-l2:#334155;--slot-l3:#475569;
  --slot-l1-h:#020617;--slot-l2-h:#0f172a;--slot-l3-h:#1e293b;
  --tip-k:#cbd5e1;--tip-v:#f1f5f9;--tip-lbl:#e2e8f0;
  --fd-label:#e2e8f0;
}
body.light{
  --bg:#f1f5f9;--card:#ffffff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;
  --muted:#94a3b8;--accent:#0891b2;--accent-bg:rgba(8,145,178,0.10);
  --success:#059669;--warn:#d97706;--danger:#dc2626;
  --c1:#0891b2;--c2:#7c3aed;--c3:#059669;--c4:#d97706;--c5:#dc2626;
  --blue:#0ea5e9;--purple:#7c3aed;--bg-dark:#e2e8f0;--border2:#cbd5e1;--dim:#64748b;
  --slot-l1:#0f172a;--slot-l2:#1e293b;--slot-l3:#334155;
  --slot-l1-h:#020617;--slot-l2-h:#0f172a;--slot-l3-h:#1e293b;
  --tip-k:#475569;--tip-v:#0f172a;--tip-lbl:#334155;
  --fd-label:#334155;
}
body{font-family:var(--sans);background:var(--bg);color:var(--text);min-height:100vh}
::-webkit-scrollbar{width:6px}::-webkit-scrollbar-track{background:var(--bg)}::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
.app{display:flex;min-height:100vh}
.sidebar{width:220px;background:var(--card);border-right:1px solid var(--border);padding:20px 12px;display:flex;flex-direction:column;flex-shrink:0;height:100vh;position:sticky;top:0;overflow-y:auto}
.sidebar::-webkit-scrollbar{width:0}.sidebar{scrollbar-width:none}
.sidebar-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:200}
body.sb-open .sidebar-overlay{display:block}
/* topbar mobile : mysifa_mobile_topbar.css */
.logo{padding:0 8px;margin-bottom:32px}
.logo-brand{font-size:15px;font-weight:800}.logo-brand span{color:var(--accent)}
.logo-sub{font-size:10px;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase}
.nav-btn{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:8px;border:none;background:transparent;color:var(--text2);cursor:pointer;font-size:13px;font-weight:500;width:100%;text-align:left;font-family:inherit;transition:all .15s;margin-bottom:2px}
.nav-btn:hover,.nav-btn.active{background:var(--accent-bg);color:var(--accent)}
.tip-cols{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:8px}
.tip-col-hdr{font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.6px;color:var(--accent);margin-bottom:8px;padding-bottom:5px;border-bottom:1.5px solid var(--accent)}
@media (max-width:540px){.tip-cols{grid-template-columns:1fr}}
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
.cmt-del-btn{color:var(--danger)!important;border-color:rgba(248,113,113,.35)!important}
.cmt-del-btn:hover{border-color:var(--danger)!important;color:var(--danger)!important;background:rgba(248,113,113,.12)!important}
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
.slot .line1{font-size:13px;color:var(--slot-l1);font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%}
.slot .line2{font-size:10px;font-weight:600;color:var(--slot-l2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%}
.slot .line3{font-size:9px;font-weight:500;color:var(--slot-l3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;margin-top:1px}
.slot:hover .line1{color:var(--slot-l1-h)}
.slot:hover .line2{color:var(--slot-l2-h)}
.slot:hover .line3{color:var(--slot-l3-h)}
.slot:hover .line1,.slot:hover .line2,.slot:hover .line3{text-shadow:0 0 1px rgba(255,255,255,.85),0 1px 2px rgba(0,0,0,.12)}
body.light .slot:hover .line1,body.light .slot:hover .line2,body.light .slot:hover .line3{text-shadow:0 1px 1px rgba(255,255,255,.9),0 0 1px rgba(0,0,0,.08)}
.slot-vert-txt{font-size:9px;font-weight:700;color:var(--slot-l1);overflow:hidden;max-height:100%;pointer-events:none;white-space:nowrap}
.slot:hover .slot-vert-txt{color:var(--slot-l1-h);text-shadow:0 0 1px rgba(255,255,255,.85),0 1px 2px rgba(0,0,0,.12)}
.slot .line-exig{display:block;width:calc(100% - 4px);max-width:100%;margin-top:4px;padding:3px 5px;border-radius:5px;
  background:#fef08a;color:#713f12;font-size:10px;font-weight:800;line-height:1.25;text-align:center;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;border:1.5px solid #eab308;
  box-shadow:0 1px 4px rgba(0,0,0,.35);letter-spacing:.2px}
body.light .slot .line-exig{background:#fef9c3;color:#713f12;border-color:#ca8a04}
.slot .line-no-of{display:block;width:calc(100% - 4px);max-width:100%;margin-top:4px;padding:3px 5px;border-radius:5px;
  font-size:10px;font-style:italic;color:var(--muted);background:rgba(148,163,184,.12);
  border:1px solid rgba(148,163,184,.25);text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-weight:500}
.tip-exig{margin-top:10px;padding:8px 10px;border-radius:8px;background:rgba(251,191,36,.18);border:1.5px solid var(--warn);
  font-size:12px;font-weight:700;color:var(--warn);line-height:1.4}
.tip-exig .k{display:block;font-size:10px;text-transform:uppercase;letter-spacing:.5px;color:var(--text2);margin-bottom:4px;font-weight:600}
.now-l{position:absolute;top:0;bottom:0;width:2px;background:var(--red);z-index:15;box-shadow:0 0 8px var(--red)}
.now-d{position:absolute;top:-4px;left:-4px;width:10px;height:10px;border-radius:50%;background:var(--red)}

.tip{position:absolute;z-index:100;background:var(--card);border:1px solid var(--border2);border-radius:12px;padding:14px 18px;
  min-width:240px;max-width:520px;pointer-events:none;animation:tipIn .15s ease;
  box-shadow:0 12px 40px rgba(0,0,0,.6)}
.tip:has(.tip-cols){max-width:600px}
.tip-hdr{display:flex;align-items:center;gap:10px;margin-bottom:10px}
.tip-bar{width:6px;height:32px;border-radius:3px;flex-shrink:0}
.tip-ref{font-size:13px;font-weight:700;color:var(--text);font-family:var(--mono)}
.tip-lbl{font-size:12px;color:var(--tip-lbl);margin-top:2px;font-weight:500}
.tip-grid{display:grid;grid-template-columns:auto 1fr;gap:6px 12px;font-size:11px;
  border-top:1px solid var(--border2);padding-top:10px;align-items:start}
.tip-grid .k{color:var(--tip-k);font-weight:600;white-space:nowrap;padding-top:1px}
.tip-grid .v{color:var(--tip-v);font-family:var(--mono);font-weight:500;
  word-wrap:break-word;overflow-wrap:anywhere;line-height:1.45}
/* Vue 2 colonnes : font standard pour les phrases longues (Conditionnement…) */
.tip-cols .tip-grid .v{font-family:inherit;font-weight:600}
.tip-cols .tip-grid{padding-top:0;border-top:none}
.tip-livraison{margin-top:8px;padding:4px 0 2px;font-size:12px;color:var(--text);font-weight:600;line-height:1.35}
.tip-livraison+.tip-grid{border-top:none;padding-top:6px}

.cmt-btn{display:inline-flex;align-items:center;justify-content:center;padding:3px 6px;border-radius:6px;
  border:1px solid var(--border2);background:transparent;color:var(--muted);cursor:pointer;flex-shrink:0;transition:all .15s}
.cmt-btn:hover,.cmt-btn.has-cmt{color:var(--accent);border-color:var(--accent);background:var(--accent-bg)}
.cmt-dot{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--accent);margin-left:4px;vertical-align:middle}
.wk-lbl.has-cmt,.dh-cell.has-cmt .dh-date-lbl{color:var(--accent)}
.wk-hdr-row{display:flex;align-items:flex-start;gap:8px;margin-bottom:8px}
.wk-hdr-actions{display:flex;align-items:center;gap:6px;flex-shrink:0;height:28px}
.wk-hdr-text{flex:1;min-width:0;display:flex;flex-direction:column;align-items:flex-start;text-align:left;justify-content:center;min-height:28px}
.wk-hdr-text--solo{align-items:flex-start;text-align:left;justify-content:center}
.wk-hdr-text--solo .wk-lbl{width:100%;text-align:left;margin-bottom:0}
.wk-hdr-row.has-wk-cmt .wk-hdr-text{align-items:flex-start;text-align:left;min-height:0;justify-content:flex-start}
.wk-hdr-row.has-wk-cmt .wk-lbl{margin:0;line-height:1.35;width:100%;text-align:left}
.cal-cmt-text{color:var(--blue);font-weight:700;font-size:11px;line-height:1.35;word-break:break-word;max-width:100%}
.wk-hdr-text .wk-cmt-text{text-align:left;margin:2px 0 0;padding:0;width:100%}
.dh-cell .cal-cmt-text,.day-cmt-text{text-align:center}
.day-cmt-text{padding:3px 6px 5px;width:100%}

.legend{display:flex;flex-wrap:wrap;gap:12px;margin-top:16px;padding-top:16px;border-top:1px solid var(--border)}
.lg-i{display:flex;align-items:center;gap:6px;font-size:11px;color:var(--dim)}
.lg-d{width:14px;height:14px;border-radius:4px;cursor:pointer;transition:transform .15s,box-shadow .15s;flex-shrink:0;border:1.5px solid rgba(148,163,184,.35)}
.lg-d:hover{transform:scale(1.3);box-shadow:0 0 0 2px rgba(255,255,255,.5)}
body.light .lg-d{border-color:rgba(71,85,105,.3)}
.lg-i span{font-family:var(--mono)}
/* ── Planning tab nav ── */
.planning-tab-nav{
  display:inline-flex;border:1px solid var(--border);border-radius:10px;
  overflow:hidden;background:var(--bg);
}
.planning-tab-btn{
  width:auto;min-width:72px;padding:7px 12px 5px;display:flex;flex-direction:row;
  align-items:center;gap:6px;background:none;border:none;cursor:pointer;
  font-family:inherit;font-size:12px;font-weight:700;
  text-transform:uppercase;letter-spacing:.3px;color:var(--muted);
  transition:color .15s,background .15s;
}
.planning-tab-btn+.planning-tab-btn{border-left:1px solid var(--border)}
.planning-tab-btn.active{color:var(--accent);background:var(--accent-bg)}
.planning-tab-btn:hover:not(.active){color:var(--text2);background:rgba(255,255,255,.04)}
.planning-tab-btn svg{opacity:.65}
.planning-tab-btn.active svg{opacity:1}
/* ── OF panel ── */
.planning-of-panel{flex:1;display:flex;flex-direction:column;min-height:0;overflow:hidden;padding:16px 20px}
.planning-of-toolbar{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:12px 14px;border-bottom:1px solid var(--border);flex-wrap:wrap;margin-bottom:16px}
.planning-of-toolbar-title{font-size:15px;font-weight:700;color:var(--text)}
.planning-of-table-wrap{flex:1;overflow-y:auto;padding:0}
table.planning-of-table{width:100%;border-collapse:collapse;font-size:12px}
table.planning-of-table th{font-size:10px;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.4px;
  padding:8px 10px;text-align:left;border-bottom:1px solid var(--border);background:var(--bg);position:sticky;top:0;z-index:1}
table.planning-of-table td{padding:8px 10px;border-bottom:1px solid var(--border);color:var(--text2);vertical-align:middle}
table.planning-of-table tr:last-child td{border-bottom:none}
.planning-of-statut{font-size:11px;font-weight:700;padding:2px 8px;border-radius:8px;display:inline-block}
.planning-of-statut--lie{color:var(--accent);background:var(--accent-bg)}
.planning-of-statut--nonlie{color:var(--muted);background:rgba(148,163,184,.10)}
.planning-of-actions{display:flex;gap:6px;align-items:center}
.planning-of-row-sub{font-size:11px;color:var(--muted);margin-top:3px;line-height:1.35}
.planning-of-empty{text-align:center;padding:40px 20px;color:var(--muted);font-size:13px}
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
.md--compact{padding:22px 24px;width:min(460px,95vw)}
.md--compact .md-hdr{margin-bottom:14px!important}
.md--compact .fd{margin-bottom:10px}
.md--compact .fd label{margin-bottom:4px;font-size:11px}
.md--compact .fd input,.md--compact .fd select{padding:7px 10px;font-size:13px}
.md--compact .fd-row{gap:8px!important}
.md--compact .dur-b{margin-top:4px}
.md--compact .md-acts{margin-top:18px}
.md.md--stats{width:min(720px,95vw);max-height:90vh;overflow-y:auto}
.ds-section{margin:20px 0 0;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:var(--muted);display:flex;align-items:center;gap:6px}
.ds-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin-top:10px}
.ds-stat{background:var(--bg);border:1px solid var(--border2);border-radius:10px;padding:12px 14px}
.ds-stat-lbl{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.4px;margin-bottom:4px}
.ds-stat-val{font-size:20px;font-weight:800;font-family:var(--mono);color:var(--text)}
.ds-time-kpi{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-top:10px}
.ds-time-card{background:var(--bg);border:1px solid var(--border2);border-radius:10px;padding:14px 16px}
.ds-tc-lbl{font-size:11px;color:var(--muted);margin-bottom:6px;display:flex;align-items:center;gap:6px}
.ds-tc-val{font-size:18px;font-weight:700;font-family:var(--mono);color:var(--text)}
.ds-tbl{width:100%;border-collapse:collapse;font-size:12px;margin-top:10px}
.ds-tbl th,.ds-tbl td{padding:8px 10px;text-align:left;border-bottom:1px solid var(--border2)}
.ds-tbl th{font-size:10px;text-transform:uppercase;letter-spacing:.4px;color:var(--muted);font-weight:600}
.ds-tbl td{font-family:var(--mono);color:var(--text2)}
.ds-tbl-wrap{overflow-x:auto;margin-top:8px;border:1px solid var(--border2);border-radius:10px}
.ds-empty{padding:24px;text-align:center;color:var(--muted);font-size:13px}
.ds-cat-calage{color:var(--warn)}
.ds-cat-production{color:var(--success)}
.ds-cat-arret{color:var(--danger)}
.md h3{color:var(--text);font-size:18px;font-family:var(--mono);margin-bottom:24px}
.fd{margin-bottom:14px}
.fd label{display:block;margin-bottom:6px;color:var(--dim);font-size:12px;text-transform:uppercase;letter-spacing:1px}
.fd input,.fd select{width:100%;padding:10px 14px;background:var(--bg);border:1px solid var(--border2);
  border-radius:8px;color:var(--text);font-size:14px;font-family:var(--mono);outline:none}
.fd select option{background:var(--card);color:var(--text)}
.dur-b{margin-top:6px;height:4px;border-radius:2px;background:var(--border);overflow:hidden}
.dur-f{height:100%;border-radius:2px;background:linear-gradient(90deg,#059669,#d97706,#dc2626);transition:width .2s}
.dossier-fgrid{display:grid;grid-template-columns:1fr;gap:12px}
@media(min-width:901px){.dossier-fgrid--2{grid-template-columns:1fr 1fr}}
.dossier-fgrid .fd--full{grid-column:1/-1}
.dossier-fgrid .fd{margin-bottom:0}
.dossier-sections{display:grid;grid-template-columns:1fr;gap:0}
.dossier-section{margin:0!important;padding:14px 0 0}
.dossier-section:first-child{padding-top:0}
.dossier-section:not(:first-child){border-top:1px solid var(--border)}
.dossier-section-label{font-size:10px;text-transform:uppercase;letter-spacing:.6px;font-weight:700;color:var(--accent);margin-bottom:12px;display:block}
.dossier-section > .fd{margin-bottom:16px}
.dossier-section > .fd:last-child{margin-bottom:0}
@media (min-width:901px){
  .dossier-sections{grid-template-columns:1fr 1fr;column-gap:18px;row-gap:0}
  .dossier-section{padding-top:0}
  .dossier-section:nth-child(2){border-top:none}
  .dossier-section:nth-child(3){border-top:1px solid var(--border);padding-top:14px;margin-top:14px}
  .dossier-section:nth-child(4){border-top:1px solid var(--border);padding-top:14px;margin-top:14px}
}
.md.md--dossier{width:min(860px,95vw);max-height:calc(100vh - 56px);overflow-y:auto;padding:22px 24px}
.md--dossier .dossier-section-label{
  font-family:var(--sans);font-size:15px;font-weight:700;text-transform:none;letter-spacing:0;
  color:var(--text);margin-bottom:14px;padding-left:11px;border-left:3px solid var(--accent);line-height:1.3}
.md--dossier .fd label{
  color:var(--fd-label);font-family:var(--sans);font-size:12px;font-weight:600;
  text-transform:none;letter-spacing:.2px;margin-bottom:7px}
.md--dossier .fd input,.md--dossier .fd select,.md--dossier .fd textarea{
  font-family:var(--sans)}
.md--dossier .dossier-check-lbl{
  display:flex;align-items:center;gap:10px;cursor:pointer;font-size:13px;font-weight:600;
  color:var(--fd-label);font-family:var(--sans);text-transform:none;letter-spacing:0;margin-bottom:0}
.md--dossier .dossier-sub-lbl{
  font-size:12px;font-weight:600;color:var(--fd-label);font-family:var(--sans);
  text-transform:none;letter-spacing:.2px;display:block;margin-bottom:8px}
.md--dossier .dossier-ta{
  width:100%;padding:9px 10px;border:1px solid var(--border2);border-radius:10px;
  background:var(--bg);color:var(--text);font-size:13px;font-family:var(--sans);
  resize:none;outline:none;min-height:54px}
.md--dossier .dossier-ta:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-bg)}
.md-acts{display:grid;grid-template-columns:repeat(3,1fr);gap:4px;margin-top:28px}
.btn-s{padding:10px 24px;background:transparent;color:var(--dim);border:1px solid var(--border2);
  border-radius:8px;cursor:pointer;font-size:14px;font-family:var(--mono)}
.empty{text-align:center;padding:48px;color:var(--muted);font-size:14px;width:100%}

@keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}
@keyframes tipIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
@keyframes slideIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
/* Dossier réellement en cours : contour accent (thème) */
@keyframes activePulse{
  0%,100%{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-bg)}
  50%{border-color:var(--border2);box-shadow:none}
}
/* Timeline search highlighting */
.slot.tl-match{outline:3px solid rgba(255,255,255,.9);outline-offset:2px;z-index:12}
.slot.tl-no-match{opacity:0.18;filter:grayscale(50%)}
.slot.tl-drop-over{outline:3px solid var(--accent);outline-offset:3px;z-index:30;filter:brightness(1.15)}
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
.planning-vue-sel{
  appearance:none;-webkit-appearance:none;
  font-size:16px;font-weight:600;color:var(--text2);
  background:var(--card);border:1px solid var(--border);border-radius:10px;
  padding:8px 36px 8px 14px;cursor:pointer;max-width:100%;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right 12px center;
  transition:border-color .15s,box-shadow .15s
}
.planning-vue-sel:hover{border-color:var(--accent)}
.planning-vue-sel:focus{border-color:var(--accent);outline:none;box-shadow:0 0 0 3px rgba(34,211,238,.12)}
.of-dropzone{border:2px dashed var(--border);border-radius:12px;padding:36px 20px;text-align:center;cursor:pointer;transition:border-color .15s,background .15s}
.of-dropzone:hover,.of-dropzone.of-dropzone--active{border-color:var(--accent);background:var(--accent-bg)}

@media (max-width:900px){
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
.of-preview-overlay{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:9000;
  display:flex;align-items:center;justify-content:center;padding:16px}
.of-preview-modal{background:var(--card);border:1px solid var(--border);border-radius:14px;
  width:100%;max-width:860px;max-height:90vh;display:flex;flex-direction:column;overflow:hidden}
.of-preview-header{display:flex;align-items:center;justify-content:space-between;
  padding:14px 18px;border-bottom:1px solid var(--border);flex-shrink:0}
.of-preview-title{font-size:15px;font-weight:700;color:var(--text)}
.of-preview-actions{display:flex;gap:8px;align-items:center}
.of-preview-iframe{flex:1;border:none;min-height:480px;width:100%}
.of-empty-state{display:flex;flex-direction:column;align-items:center;justify-content:center;
  gap:14px;padding:48px 24px;text-align:center}
.of-empty-state-icon{color:var(--muted);opacity:.5}
.of-empty-state-msg{font-size:14px;color:var(--muted);line-height:1.6}
.of-tabs-bar{display:flex;gap:0;border-bottom:1px solid var(--border);flex-shrink:0;padding:0 18px}
.of-tab-btn{padding:10px 16px;font-size:13px;font-weight:600;color:var(--muted);background:none;
  border:none;border-bottom:2px solid transparent;cursor:pointer;font-family:inherit;
  margin-bottom:-1px;transition:color .15s,border-color .15s}
.of-tab-btn:hover{color:var(--text)}
.of-tab-btn.active{color:var(--accent);border-bottom-color:var(--accent)}
.of-tab-pane{flex:1;display:flex;flex-direction:column;overflow:hidden}
.of-tab-pane.hidden{display:none}
.of-mismatch-modal{background:var(--card);border:1px solid var(--border);border-radius:14px;
  max-width:440px;width:100%;padding:28px 24px;display:flex;flex-direction:column;gap:16px}
</style>
</head>
<body>
<script src="/static/mysifa_theme.js"></script>
<script src="/static/mysifa_favicon_badge.js"></script>
<script src="/static/mysifa_user_chip.js"></script>
<script src="/static/motion.js" defer></script>
<div class="sidebar-overlay" id="sb-ov"></div>
<div id="app"></div>
<script src="/static/support_widget.js"></script>
<script>window.__MYSIFA_APP__='planning';</script>
<link rel="stylesheet" href="/static/mysifa_landscape.css">
<link rel="stylesheet" href="/static/mysifa_dock.css">
<link rel="stylesheet" href="/static/mysifa_postit.css">
<script src="/static/mysifa_dock.js"></script>
<script src="/static/mysifa_postit.js"></script>
<script src="/static/mysifa_calc.js"></script>
<script src="/static/mysifa_ai_chat.js"></script>
<script src="/static/chat_mentions.js"></script>
<script src="/static/chat_widget.js?v=5"></script>
<script src="/static/chat_widget_v2.js"></script>
<script src="/static/mysifa_landscape.js?v=2"></script>
<script>window.MySifaLandscape&&MySifaLandscape.enable();</script>
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
window.addEventListener("unhandledrejection", (e)=>{
  const r=e.reason;
  let extra="";
  if(r instanceof Error) extra=r.message+(r.stack?("\\n"+r.stack):"");
  else if(r&&typeof r.json==="function") extra="Réponse HTTP "+(r.status||"?")+" — détail dans la console (F12)";
  else extra=String(r||"");
  showFatal("Promise rejection", 0, 0, extra);
});
</script>
<script>
let MID=__MACHINE_ID__;
const DN=["Dim","Lun","Mar","Mer","Jeu","Ven","Sam"];
const MIND=0.75,MAXD=720;
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
const PLANNING_VUES=[
  {key:"prod", label:"Planning : Production"},
  {key:"expe", label:"Planning : Expédition"},
  {key:"prod_expe", label:"Planning : Production + Expédition"},
];
function parsePlanningVueParam(){
  const v=new URLSearchParams(location.search||"").get("vue");
  if(v==="expe") return "expe";
  if(v==="prod_expe") return "prod_expe";
  return "prod";
}
function planningVueLabel(){
  const item=PLANNING_VUES.find(x=>x.key===S.planningVue);
  return item?item.label:"Planning : Production";
}
function planningVueTopbarTitle(){ return planningVueLabel(); }
function renderPlanningVueSelect(){
  return `<select class="planning-vue-sel" aria-label="Mode planning" onchange="setPlanningVue(this.value)">${
    PLANNING_VUES.map(v=>`<option value="${escAttr(v.key)}"${S.planningVue===v.key?" selected":""}>${escHtml(v.label)}</option>`).join("")
  }</select>`;
}
function setPlanningVue(key){
  if(!PLANNING_VUES.some(x=>x.key===key)) key="prod";
  const sp=new URLSearchParams(location.search||"");
  if(key==="expe") sp.set("vue","expe");
  else if(key==="prod_expe") sp.set("vue","prod_expe");
  else sp.delete("vue");
  location.href="/planning?"+sp.toString();
}
function setPlanningTab(tab){
  S.planningTab=tab;
  render();
}
function renderPlanningMobileTopbar(sub){
  const subTxt=sub||"Timeline machines, dossiers et horaires";
  return `<div class="mobile-topbar"><button type="button" class="mobile-menu-btn" onclick="toggleSidebar()" aria-label="Menu"><span style="display: inline-flex; align-items: center; flex-shrink: 0;">${icon('menu',20)}</span></button><div><div class="mobile-topbar-title">${escHtml(planningVueTopbarTitle())}</div><div class="mobile-topbar-sub">${escHtml(subTxt)}</div></div><button type="button" class="mobile-home-btn" onclick="location.href='/'" aria-label="Accueil"><span style="display: inline-flex; align-items: center; flex-shrink: 0;">${icon('home',20)}</span></button></div>`;
}
function appendPlanningVueParam(sp){
  if(S.planningVue==="expe") sp.set("vue","expe");
  else if(S.planningVue==="prod_expe") sp.set("vue","prod_expe");
  return sp;
}
let _planView=localStorage.getItem("mysifa.planning.view")||"2w";
let S={machine:null,machines:[],entries:[],timeline:[],wo:0,loading:true,holidays:{},dayWorked:{},dayHoraires:{},weekComments:{},dayComments:{},view:_planView,
  planningVue:parsePlanningVueParam(),
  planningTab:"timeline",
  contactOpen:false,contactSubject:"",contactMessage:"",contactSending:false,searchQuery:"",tlSearchQuery:"",tlSearchIdx:0,activeDossier:null,
  tlTotalDays:5,machineHoursPerDay:16};
let _allTlMatches=[];
let ME=null;
let PENDING_OF_COUNT=0;
let CAN_EDIT=false;
let IS_DIR_OR_SUPER=false;
const IS_OF_ADMIN=__IS_OF_ADMIN__;
let SHOW_DOSSIERS=false;
let _autoScrollKey=null;
let _suppressAutoScroll=false;
let _showAllTermine=false;   // true = montrer tous les terminés; false = seulement les 2 derniers
const TERMINE_KEEP=2;        // nombre de terminés toujours visibles en bas de la pile

async function parseApiError(res){
  let msg="Erreur "+res.status;
  try{
    const j=await res.json();
    const d=j&&j.detail;
    if(typeof d==="string") msg=d;
    else if(Array.isArray(d)) msg=d.map(x=>(x&&x.msg)?x.msg:JSON.stringify(x)).join(" ");
    else if(d) msg=JSON.stringify(d);
  }catch(_){}
  const err=new Error(msg);
  err.status=res.status;
  return err;
}
function apiErrorMessage(e,fallback){
  if(e&&e.message) return e.message;
  return fallback||"Erreur";
}
const api=(p,o={})=>fetch(`/api/planning${p}`,{credentials:"include",headers:{"Content-Type":"application/json",...(o.headers||{})},...o}).then(async r=>{
  if(!r.ok) throw await parseApiError(r);
  const ct=r.headers.get("content-type")||"";
  if(ct.includes("application/json")) return r.json();
  return null;
});

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

async function packTerminesToNow(){
  if(!CAN_EDIT||!MID) return;
  if(!confirm("Recaler les dossiers terminés les uns derrière les autres (fin = maintenant) ?")) return;
  try{
    const res=await fetch(`/api/planning/machines/${MID}/pack-termines`,{
      method:"POST",
      credentials:"include",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({})
    });
    if(!res.ok){
      const j=await res.json().catch(()=>({}));
      const d=j.detail;
      const msg=typeof d==="string"?d:(Array.isArray(d)?d.map(x=>x.msg||JSON.stringify(x)).join(" "):"Erreur recalage terminés.");
      showToast(msg,"danger");
      return;
    }
    const j=await res.json().catch(()=>({}));
    showToast(`Terminés recalés (${j.updated||0}).`,"success");
  }catch(_){
    showToast("Erreur réseau.","danger");
  }
  await load();
}

async function packAttenteAfterEnCours(){
  if(!CAN_EDIT||!MID) return;
  if(!confirm("Recaler les dossiers en attente les uns derrière les autres (après le dossier en cours) ?")) return;
  try{
    const res=await fetch(`/api/planning/machines/${MID}/pack-attente`,{
      method:"POST",
      credentials:"include",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({})
    });
    if(!res.ok){
      const j=await res.json().catch(()=>({}));
      const d=j.detail;
      const msg=typeof d==="string"?d:(Array.isArray(d)?d.map(x=>x.msg||JSON.stringify(x)).join(" "):"Erreur recalage en attente.");
      showToast(msg,"danger");
      return;
    }
    const j=await res.json().catch(()=>({}));
    showToast(`En attente recalés (${j.updated||0}).`,"success");
  }catch(_){
    showToast("Erreur réseau.","danger");
  }
  await load();
}

async function packTerminesBeforeEnCoursAll(){
  if(!CAN_EDIT) return;
  if(!confirm("Replacer les dossiers terminés avant le dossier en cours sur chaque machine ?")) return;
  try{
    const res=await fetch(`/api/planning/pack-termines-before-en-cours`,{
      method:"POST",
      credentials:"include",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({})
    });
    if(!res.ok){
      const j=await res.json().catch(()=>({}));
      const d=j.detail;
      const msg=typeof d==="string"?d:(Array.isArray(d)?d.map(x=>x.msg||JSON.stringify(x)).join(" "):"Erreur recalage terminés (toutes machines).");
      showToast(msg,"danger");
      return;
    }
    const j=await res.json().catch(()=>({}));
    const arr=Array.isArray(j.machines)?j.machines:[];
    const tot=arr.reduce((s,x)=>s+(Number(x.updated)||0),0);
    showToast(`Terminés replacés (total: ${tot}).`,"success");
  }catch(_){
    showToast("Erreur réseau.","danger");
  }
  await load();
}

(function initSlotResize(){
  if(window.__mysifaPlanResize) return;
  window.__mysifaPlanResize=true;
  let resizing=null;
  const MIN_DUREE_H=0.75; // aligné avec la validation backend (planning.update_entry)
  const MAX_DUREE_H=720;
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
    // Modèle semaine : sert à convertir les pixels en heures OUVRÉES.
    // Le delta de durée est ainsi correct même si le slot est tronqué
    // (dossier à cheval sur 2 semaines) — on ajoute des heures, on ne
    // fait plus de règle de trois sur la largeur visible.
    const tlWrap=slot.closest(".tl-wrap");
    const mon=tlWrap?new Date(+tlWrap.dataset.mon):null;
    let weekTot=null;
    if(mon&&!isNaN(mon.getTime())){
      const wm=computeTlWeekModel(mon);
      if(!wm.err&&wm.tot>0) weekTot=wm.tot;
    }
    if(weekTot==null) return;
    e.preventDefault();
    e.stopPropagation();
    const tlRect=tlBar.getBoundingClientRect();
    const pxPerPct=tlRect.width/100||1;
    const startWpct=parseFloat(slot.style.width)||1;
    const startDuree=Math.max(MIN_DUREE_H,parseFloat(entry.duree_heures)||MIN_DUREE_H);
    const _prevCursor=slot.style.cursor||"";
    const preview=document.createElement("div");
    preview.className="slot-resize-preview";
    preview.textContent=fmtDur(startDuree);
    slot.appendChild(preview);
    slot.style.cursor="ew-resize";
    resizing={
      slot,
      eid:eidStr,
      startX:e.clientX,
      startWpct,
      pxPerPct,
      startDuree,
      weekTot,
      preview,
      _prevCursor
    };
  },true);
  document.addEventListener("mousemove",function(e){
    if(!resizing) return;
    const dx=e.clientX-resizing.startX;
    // px → % de la barre semaine → heures ouvrées de la semaine
    const deltaH=(dx/resizing.pxPerPct)/100*resizing.weekTot;
    const newDuree=Math.min(MAX_DUREE_H,Math.max(MIN_DUREE_H,resizing.startDuree+deltaH));
    const snapped=Math.round(newDuree*4)/4; // aperçu = valeur qui sera enregistrée (pas de quart d'heure fantôme)
    const effDeltaPct=((newDuree-resizing.startDuree)/resizing.weekTot)*100;
    // La largeur peut dépasser la fin de semaine pendant le drag : au relâchement,
    // le rechargement redécoupe le slot sur la/les semaine(s) suivante(s).
    resizing.slot.style.width=Math.max(0.5,resizing.startWpct+effDeltaPct)+"%";
    resizing.preview.textContent=fmtDur(snapped);
    resizing._liveNewDuree=newDuree;
  });
  document.addEventListener("mouseup",async function(){
    if(!resizing) return;
    const{slot,eid,preview,startDuree,startWpct,_prevCursor}=resizing;
    preview.remove();
    slot.style.cursor=_prevCursor||"";
    const live=resizing._liveNewDuree;
    resizing=null;
    if(live==null){
      slot.style.width=startWpct+"%";
      return;
    }
    const rounded=Math.min(MAX_DUREE_H,Math.max(MIN_DUREE_H,Math.round(live*4)/4));
    if(Math.abs(rounded-startDuree)<1e-6){
      slot.style.width=startWpct+"%";
      return;
    }
    // Durée seule : le backend recalcule planned_end en heures ouvrées machine
    // (il traverse les semaines, dimanches et jours non travaillés exclus).
    // planned_end_manual:false purge aussi un éventuel ancien override manuel.
    const payload={duree_heures:rounded,planned_end_manual:false};
    let ok=false;
    try{
      const res=await fetch(`/api/planning/machines/${MID}/entries/${eid}`,{
        method:"PUT",
        credentials:"include",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify(payload)
      });
      if(!res.ok){
        const j=await res.json().catch(()=>({}));
        const d=j.detail;
        const msg=typeof d==="string"?d:(Array.isArray(d)?d.map(x=>x.msg||JSON.stringify(x)).join(" "):"Erreur mise à jour durée.");
        showToast(msg,"danger");
      }else{
        showToast("Durée mise à jour : "+fmtDur(rounded),"success");
        ok=true;
      }
    }catch(_){
      showToast("Erreur réseau.","danger");
    }
    if(!ok){
      slot.style.width=startWpct+"%";
      return;
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
    await Promise.all([loadHolidays(),loadDayWorked(),loadDayHoraires(),loadCalendarComments()]);
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

async function loadCalendarComments(){
  if(!MID) return;
  const mon=addD(getMon(new Date()),S.wo*7);
  const nb=S.view==="1w"?6:S.view==="4w"?27:13;
  const start=ymd(mon), end=ymd(addD(mon,nb));
  try{
    const data=await api(`/machines/${MID}/calendar-comments?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`);
    S.weekComments=(data&&data.week_comments)||{};
    S.dayComments=(data&&data.day_comments)||{};
  }catch(e){
    S.weekComments={};
    S.dayComments={};
  }
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
    await api(`/machines/${MID}/day-work`,{method:"PUT",body:JSON.stringify({date:dateStr,is_worked:nonTravailChecked?0:1})});
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
  const activeRun=active.filter(e=>e.statut==="en_cours");
  const activeWait=active.filter(e=>e.statut!=="en_cours");
  const hiddenCount=_showAllTermine?0:Math.max(0,terminated.length-TERMINE_KEEP);
  const visibleTerminated=_showAllTermine?terminated:terminated.slice(-TERMINE_KEEP);
  // Ordre UX attendu : "En cours" puis "En attente", puis les derniers "Terminé" en bas.
  // Ne pas trier S.entries : on reconstruit uniquement l'ordre d'affichage (data-idx reste cohérent).
  const visible=[...activeRun,...activeWait,...visibleTerminated];

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
    'file': '<path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/>',
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
    'upload': '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>',
    'message-square': '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    'play': '<polygon points="5 3 19 12 5 21 5 3"/>',
    'alert-triangle': '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
    'clock': '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    'box': '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/>',
    'truck': '<path d="M3 7h11v10H3z"/><path d="M14 10h4l3 3v4h-7z"/><circle cx="7.5" cy="17" r="2"/><circle cx="17.5" cy="17" r="2"/>',
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
function fmtLivraisonLong(s){
  if(!s)return"";
  const iso=String(s).slice(0,10);
  if(!/^\d{4}-\d{2}-\d{2}$/.test(iso))return String(s);
  try{
    const d=new Date(iso+"T12:00:00");
    return d.toLocaleDateString("fr-FR",{weekday:"long",day:"numeric",month:"long",year:"numeric"});
  }catch(e){return iso;}
}
function semaineKey(d){
  const x=new Date(Date.UTC(d.getFullYear(),d.getMonth(),d.getDate()));
  const n=x.getUTCDay()||7;
  x.setUTCDate(x.getUTCDate()+4-n);
  const y=x.getUTCFullYear();
  const w=Math.ceil(((x-Date.UTC(y,0,1))/864e5+1)/7);
  return `${y}-W${String(w).padStart(2,"0")}`;
}
function weekCommentBtn(sk,monTs){
  const has=!!((S.weekComments||{})[sk]||"").trim();
  const title=has?"Commentaire semaine":"Ajouter un commentaire semaine";
  return `<button type="button" class="cmt-btn${has?" has-cmt":""}" onclick="event.stopPropagation();openWeekCommentModal('${escAttr(sk)}',${monTs})" title="${escAttr(title)}">${icon("message-square",12)}</button>`;
}
function weekHeaderRow(mn,lblCls){
  const wn=wkNum(mn);
  const sk=semaineKey(mn);
  const weekCmt=((S.weekComments||{})[sk]||"").trim();
  const hasCmt=!!weekCmt;
  const wkParamBtn=CAN_EDIT?`<button type="button" class="gear-btn" style="padding:3px 6px;flex-shrink:0" onclick="openWeekSettingsModal(${mn.getTime()})" title="Paramètres semaine S${wn}">${icon("settings",13)}</button>`:"";
  const lbl=`<div class="wk-lbl ${lblCls}${hasCmt?" has-cmt":""}" style="margin-bottom:0;cursor:pointer" onclick="openWeekCommentModal('${escAttr(sk)}',${mn.getTime()})" title="Commentaire semaine S${wn}">S${wn} — ${fd(mn)} au ${fd(addD(mn,4))}</div>`;
  const actions=`<div class="wk-hdr-actions">${wkParamBtn}${weekCommentBtn(sk,mn.getTime())}</div>`;
  const textCls=hasCmt?"wk-hdr-text":"wk-hdr-text wk-hdr-text--solo";
  const cmtHtml=hasCmt?`<div class="cal-cmt-text wk-cmt-text">${escHtml(weekCmt)}</div>`:"";
  return `<div class="wk-hdr-row${hasCmt?" has-wk-cmt":""}">
    ${actions}
    <div class="${textCls}">${lbl}${cmtHtml}</div>
  </div>`;
}
function fmtDur(h){const hrs=Math.floor(+h||0);const mins=Math.round(((+h||0)-hrs)*60);return mins>0?`${hrs}h${String(mins).padStart(2,"0")}`:`${hrs}h`}
function fmtQty(n){if(n==null||n===""||isNaN(n))return"";return Math.round(Number(n)).toLocaleString("fr-FR");}

// Durée "ouvrée" entre 2 timestamps (créneaux de production), pour l'affichage uniquement.
// IMPORTANT: ne pas impacter la timeline (taille slots, positions, etc.).
function workHoursBetween(startDt,endDt){
  try{
    if(!(startDt instanceof Date) || !(endDt instanceof Date)) return null;
    if(!(startDt<endDt)) return 0;
    let cur = new Date(startDt);
    cur.setSeconds(0,0);
    const end = new Date(endDt);
    end.setSeconds(0,0);
    let total = 0;
    while(cur < end){
      const day = new Date(cur); day.setHours(0,0,0,0);
      const ds = ymdate(day);
      const di = day.getDay(); // 0..6 (lun=1 ... sam=6)
      if(di === 0){ cur = addD(day,1); continue; } // dimanche
      const isOff = isPlanningDayOff(di, ds);
      if(isOff){ cur = addD(day,1); continue; }
      const wh = getWhForDate(di, day, ds);
      const ws = new Date(day.getTime() + (wh.s||0)*36e5);
      const we = new Date(day.getTime() + (wh.e||0)*36e5);
      const segS = (cur > ws) ? cur : ws;
      const segE = (end < we) ? end : we;
      if(segE > segS) total += (segE - segS) / 36e5;
      cur = addD(day,1);
    }
    return total;
  }catch(e){
    return null;
  }
}

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
function hasSaisieReelle(){
  const mk=machineKey();
  return mk==="C1" || mk==="C2";
}
function normalizeParityDefs(raw){
  if(!raw||typeof raw!=="object") return null;
  const out={pair:{},impair:{}};
  for(const par of ["pair","impair"]){
    const block=raw[par];
    if(!block) return null;
    for(const slot of ["week","fri"]){
      const w=block[slot];
      let s,e;
      if(Array.isArray(w)&&w.length>=2){s=+w[0];e=+w[1];}
      else if(w&&typeof w==="object"){s=+w.s;e=+w.e;}
      else return null;
      if(!isFinite(s)||!isFinite(e)||e<=s) return null;
      out[par][slot]={s,e};
    }
  }
  return out;
}
function getMachineDefaults(){
  const mk=machineKey();
  const m=S.machine;
  if(m&&m.horaires_parity){
    try{
      const j=typeof m.horaires_parity==="string"?JSON.parse(m.horaires_parity):m.horaires_parity;
      const norm=normalizeParityDefs(j);
      if(norm) return norm;
    }catch(e){}
  }
  const key=`mysifa.planning.defaults.${mk}`;
  try{
    const raw=localStorage.getItem(key);
    if(raw){
      const norm=normalizeParityDefs(JSON.parse(raw));
      if(norm) return norm;
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
/** Jour non travaillé — aligné backend (fériés + planning_day_worked). */
function isPlanningDayOff(di,ds){
  const isSat=di===6;
  if(isSat) return !S.dayWorked[ds];
  if(!!S.holidays[ds]) return true;
  if(Object.prototype.hasOwnProperty.call(S.dayWorked||{},ds)&&!S.dayWorked[ds]) return true;
  return false;
}
/** forEdit=true : horaires pour formulaire (modale semaine / jour), même si jour non travaillé. */
function getWhForDate(di,dateObj,ds,forEdit){
  if(!forEdit&&ds&&isPlanningDayOff(di,ds)) return null;
  // Priorité 1 : override ponctuel par date (planning_day_horaires)
  if(ds && S.dayHoraires && S.dayHoraires[ds]){
    return S.dayHoraires[ds];
  }
  const mk=machineKey();
  const mrec=S.machine;
  // Priorité 2 : horaires paire/impaire — toute machine ayant horaires_parity en base
  // (+ Cohésio 2 via ses défauts), lun–ven uniquement : aligné backend
  // (_hours_for_date_factory applique la parité avant les horaires hebdo, jamais le samedi).
  if(di>=1&&di<=5&&(mk==="C2"||(mrec&&mrec.horaires_parity))){
    const defs=getMachineDefaults();
    const par=isWeekPair(dateObj)?"pair":"impair";
    const isFri=(di===5);
    const w=isFri?(defs[par].fri):(defs[par].week);
    return {s:w.s,e:w.e};
  }
  // Priorité 3 : horaires hebdo par jour (machines.horaires_*)
  const m=S.machine,key=DAY_FIELD[di];
  const raw=m&&m[key]!=null?String(m[key]):"";
  if(raw&&raw.trim()){
    return parseHorairesPair(raw,di);
  }
  // Repli samedi : défaut backend (_parse_horaires_val "6,18")
  if(di===6) return {s:6,e:18};
  // Repli lun–ven : défauts paire/impair (localStorage ou constantes)
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
function canAccessOfTab(){return isAdmin(ME);}
function isComptaUser(u){return !!(u&&u.role==="comptabilite");}
function canPlanningNav(u){return !!(u&&u.app_access&&u.app_access.planning);}
function roleLabel(role){const R={direction:"Direction",administration:"Administration",fabrication:"Fabrication",logistique:"Logistique",comptabilite:"Comptabilité",expedition:"Expédition",commercial:"Commercial",superadmin:"Super admin"};return R[role]||role||"";}
function planningUserChipHtml(){
  if(!ME)return "";
  const editIco=icon("edit",12);
  const inner=window.MySifaUserChip
    ? MySifaUserChip.innerHtml(ME,{roleLabels:{direction:"Direction",administration:"Administration",fabrication:"Fabrication",logistique:"Logistique",comptabilite:"Comptabilité",expedition:"Expédition",commercial:"Commercial",superadmin:"Super admin"},editIconHtml:editIco})
    : '<div class="uc-name">'+escAttr(ME.nom||"")+'</div><div class="uc-role">'+roleLabel(ME.role)+'</div><div class="uc-profil">'+editIco+' Mon profil</div>';
  return '<div class="user-chip" onclick="location.href=\'/profil\'" title="Mon profil">'+inner+'</div>';
}
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
  const comptaOnly=isComptaUser(ME);
  const items=[
    ...(canPlanningNav(ME)?[{key:"_planning",label:"Planning",icon:"calendar",href:"/planning"}]:[]),
    ...(comptaOnly?[]:[
      {key:"production",label:"Production",icon:"wrench",href:"/prod?page=production"},
      {key:"traceabilite",label:"Traçabilité",icon:"layers",href:"/prod?page=traceabilite"},
      ...(admin?[{key:"rentabilite",label:"Rentabilité",icon:"trending-up",href:"/prod?page=rentabilite"}]:[]),
      ...(canAccessOfTab()?[{key:"of",label:"Fiches + OF",icon:"file",href:"/prod?page=of",withPendingBadge:true}]:[]),
    ]),
  ];
  const isLight=document.body.classList.contains("light");
  return`<nav class="sidebar"><div class="logo"><div class="logo-brand">My<span>Prod</span></div><div class="logo-sub">by SIFA</div></div>${
    items.map(i=>{
      const badge=(i.withPendingBadge && PENDING_OF_COUNT>0)
        ? `<span style="margin-left:auto;padding:1px 7px;border-radius:9px;background:var(--danger);color:#fff;font-size:10px;font-weight:700;line-height:1.5;flex-shrink:0" title="${PENDING_OF_COUNT} OF à associer manuellement">${PENDING_OF_COUNT}</span>`
        : "";
      return `<button type="button" class="nav-btn${i.key==="_planning"?" active":""}" onclick="location.href='${i.href}'"><span style="display:inline-flex;align-items:center;gap:10px;width:100%">${icon(i.icon,16)}<span>${i.label}</span>${badge}</span></button>`;
    }).join("")
  }<div class="sidebar-bottom">${(S.planningVue==='expe'||S.planningVue==='prod_expe')?`<button type="button" class="nav-btn nav-btn--mysifa-portal" onclick="location.href='/expe'" title="Retour MyExpé"><span class="mysifa-back-preamble">← Retour </span><span class="mysifa-back-brand" style="display:inline-flex;align-items:center;gap:6px">${icon('truck',14)}My<span class="mysifa-back-accent">Expé</span></span></button>`:''}<button type="button" class="nav-btn nav-btn--mysifa-portal" onclick="location.href='/'"><span class="mysifa-back-preamble">← Retour </span><span class="mysifa-back-brand">My<span class="mysifa-back-accent">Sifa</span></span></button>${planningUserChipHtml()}<button type="button" class="support-btn" onclick="openSupport()"><span class="support-ico">${(window.MySifaSupport&&window.MySifaSupport.iconSvg)?window.MySifaSupport.iconSvg():""}</span><span>Contacter le support</span></button><button type="button" class="theme-btn" onclick="toggleTheme()"><span class="theme-ico">${isLight?icon('sun',16):icon('moon',16)}</span><span class="theme-label">${isLight?"Mode clair":"Mode sombre"}</span></button><button type="button" class="logout-btn" onclick="doLogout()">${icon('log-out',14)} Déconnexion</button><div class="version">__V_LABEL__</div></div></nav>`;
}
async function loadPendingOfCount(){
  if(!canAccessOfTab())return;
  try{
    const r=await fetch("/api/admin/of-link-pending/count",{credentials:"include"});
    if(!r.ok){PENDING_OF_COUNT=0;return;}
    const data=await r.json();
    PENDING_OF_COUNT=Number(data&&data.count||0);
    try{render();}catch(e){}
  }catch(e){PENDING_OF_COUNT=0;}
}
function toggleTheme(){if(window.MySifaTheme)MySifaTheme.toggleMode();render();}
function renderPlanningOfPanel(){
  return `<div class="planning-of-panel">
    <div class="planning-of-toolbar">
      <div class="planning-of-toolbar-title">Fiches et OF</div>
      <div style="font-size:12px;color:var(--muted)">Accès aux ordres de fabrication et fiches techniques</div>
    </div>
    <div class="planning-of-empty">
      <div style="font-size:24px;margin-bottom:12px">${icon('file',32)}</div>
      <div>La fonctionnalité Fiches et OF est disponible via l'onglet OF dans le menu Production.</div>
      <div style="margin-top:8px"><a href="/prod?page=of" style="color:var(--accent);text-decoration:none;font-weight:700">Accéder à OF →</a></div>
    </div>
  </div>`;
}
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
    a.innerHTML=`<div class="app">${renderSidebar()}<main class="main">${renderPlanningMobileTopbar()}<div class="planning-container" data-page-enter style="display:flex;align-items:center;justify-content:center;min-height:50vh;color:var(--muted)">Chargement…</div>${renderContactModal()}</main></div><div id="mroot"></div>`;
    return;
  }
  const m=S.machine||{nom:"?"};
  CAN_EDIT = isAdmin(ME);
  IS_DIR_OR_SUPER = !!(ME && (ME.role==="superadmin" || ME.role==="direction"));
  const IS_COMPTA_RO = !!(ME && ME.role==="comptabilite");
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
  const navLbl=S.wo===0?"actuelle":`S${w1}`;
  let tlBlocks="";
  for(let wi=0;wi<nw;wi++){
    const mn=addD(m1,wi*7);
    const lblCls=wi===0?"cur":"nxt";
    tlBlocks+=`<div ${wi<nw-1?'style="margin-bottom:16px"':""}>
      ${weekHeaderRow(mn,lblCls)}
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
    a.innerHTML=`<div class="app">${renderSidebar()}<main class="main">${renderPlanningMobileTopbar()}<div class="planning-container" data-page-enter style="max-width:560px;margin:40px auto;padding:0 16px;color:var(--text)">
      <h1 style="font-size:18px;margin:0 0 12px">Planning</h1>
      ${isFab?fabMsg:admMsg}
    </div>${renderContactModal()}</main></div><div id="mroot"></div>`;
    return;
  }

  // Motion : cascade d'entree au changement d'onglet / vue uniquement.
  const _moPlanKey=(S.planningTab||'')+'|'+(S.view||'')+'|'+(S.planningVue||'');
  const _moPlanEnter=(window._moPlanLastKey!==_moPlanKey);
  window._moPlanLastKey=_moPlanKey;
  const _moPlanAttr=_moPlanEnter?' data-page-enter':'';
  a.innerHTML=`<div class="app">${renderSidebar()}<main class="main">${renderPlanningMobileTopbar()}<div class="planning-container"${_moPlanAttr}>
  <header class="header">
    <div class="h-left">
      <div>
        <select class="m-sel" onchange="changeMachine(this.value)" aria-label="Sélection de la machine">
          ${(S.machines||[]).map(x=>`<option value="${x.id}" ${x.id===MID?"selected":""}>${escAttr(x.nom||'')}</option>`).join("")}
        </select>
        <div class="m-sub">${escHtml(planningVueLabel())} — MyProd by SIFA</div>
      </div>
    </div>
    <div class="h-right">
      ${CAN_EDIT&&machineKey()==="C2"?`<button type="button" class="reset-days-btn" onclick="resetDefaultDaysCohesio2()" title="Réinitialiser jours (Cohésio 2)">↺ Base jours</button>`:""}
      ${SHOW_DOSSIERS?`<button type="button" class="reset-days-btn" onclick="packAttenteAfterEnCours()" title="Recaler les en attente derrière le en cours">⇥ En attente</button>`:""}
      ${SHOW_DOSSIERS?`<button type="button" class="reset-days-btn" onclick="packTerminesToNow()" title="Recaler les terminés jusqu'à maintenant">⇤ Terminés</button>`:""}
      ${SHOW_DOSSIERS?`<button type="button" class="reset-days-btn" onclick="packTerminesBeforeEnCoursAll()" title="Replacer les terminés avant le en cours (toutes machines)">⇤ Terminés → en cours</button>`:""}
      ${CAN_EDIT?`<button type="button" class="gear-btn" onclick="openDefaultsModal()" title="Réglages horaires par défaut" aria-label="Réglages">${icon('settings',16)}</button>`:""}
      ${IS_COMPTA_RO?`<div class="badge" style="background:var(--accent-bg);color:var(--accent);border:1px solid var(--border)">Lecture seule</div>`:""}
      ${runLbl?`<div class="badge badge-run"><div class="dot"></div>${escAttr(runLbl)}</div>`:""}
      ${SHOW_DOSSIERS?`<div class="badge badge-info">${totH}h · ${nb} dossiers</div>`:""}
    </div>
  </header>
  <div style="padding:0 0 16px">
    <div class="planning-tab-nav">
      <button type="button" class="planning-tab-btn ${S.planningTab==='timeline'?' active':''}" onclick="setPlanningTab('timeline')">${icon('calendar',16)} Timeline</button>
    </div>
  </div>
    <section class="sec"${_moPlanAttr}>
      <div class="sec-hdr">
        ${renderPlanningVueSelect()}
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
          <div class="view-tabs">
            <button type="button" class="view-tab ${S.view==="1w"?"active":""}" onclick="setView('1w')">Semaine</button>
            <button type="button" class="view-tab ${S.view==="2w"?"active":""}" onclick="setView('2w')">2 semaines</button>
            <button type="button" class="view-tab ${S.view==="4w"?"active":""}" onclick="setView('4w')">4 semaines</button>
          </div>
          <div class="wk-nav">
            <button type="button" onclick="S.wo--;load()">◀</button>
            <button type="button" class="today" onclick="S.wo=0;load()">${navLbl}</button>
            <button type="button" onclick="S.wo++;load()">▶</button>
          </div>
          ${CAN_EDIT&&hasSaisieReelle()?`<button type="button" class="btn-s" onclick="openImportOrphan()" style="display:inline-flex;align-items:center;gap:5px;padding:6px 12px;font-size:11px" title="Ajouter un dossier terminé depuis les saisies de production"><span style="font-size:15px;line-height:1">+</span> Importer dossier</button>`:""}
        </div>
      </div>
      <div style="font-size:11px;color:var(--muted);margin:-8px 0 12px">Gérez les jours et horaires via l'icône ⚙ de chaque semaine.</div>
      <div style="margin-bottom:12px;display:flex;align-items:center;gap:10px;flex-wrap:wrap">
        <div style="position:relative;max-width:360px;flex:1;min-width:160px">
          <input type="text" id="tl-search" placeholder="Rechercher dans la timeline (client, OF, réf produit…)" value="${escAttr(S.tlSearchQuery||"")}"
            oninput="S.tlSearchIdx=0;S.tlSearchQuery=this.value;renderTL()"
            onkeydown="if(event.key==='Enter'){event.shiftKey?tlSearchPrev():tlSearchNext();event.preventDefault()}"
            style="width:100%;padding:8px 34px 8px 12px;border:1px solid var(--border2);border-radius:8px;background:var(--bg);color:var(--text);font-size:12px;font-family:var(--mono);outline:none">
          <button type="button" onclick="tlSearchNext()" title="Résultat suivant (Entrée)"
            style="position:absolute;right:8px;top:50%;transform:translateY(-50%);background:transparent;border:none;color:var(--muted);cursor:pointer;padding:2px;display:flex;align-items:center;line-height:1">
            ${icon('search',14)}
          </button>
        </div>
        <span id="tl-match-count" style="font-size:12px;font-weight:700;color:#67e8f9;font-family:var(--mono);display:none;white-space:nowrap"></span>
        <div id="tl-other-machines" style="display:none;align-items:center;gap:6px;flex-wrap:wrap"></div>
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
    ${SHOW_DOSSIERS?`<section class="sec"${_moPlanAttr}>
      <div class="sec-hdr">
        <div class="sec-title">Dossiers de production</div>
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
          <div style="position:relative;max-width:360px;flex:1;min-width:160px">
            <input type="text" id="planning-search" placeholder="Rechercher (client, ref, OF, réf produit, format…)" value="${escAttr(S.searchQuery)}"
              oninput="S.searchQuery=this.value;renderEntries();"
              style="width:100%;padding:8px 34px 8px 12px;border:1px solid var(--border2);border-radius:8px;background:var(--bg);color:var(--text);font-size:12px;font-family:var(--mono);outline:none">
            <span style="position:absolute;right:10px;top:50%;transform:translateY(-50%);color:var(--muted);font-size:14px">🔍</span>
          </div>
          <div id="list-other-machines" style="display:none;align-items:center;gap:6px;flex-wrap:wrap"></div>
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
  // Motion : (re)scan apres chaque render — pose --i pour les cascades et
  // arme les Observers. No-op si window.Motion absent (defer non charge).
  try{ if(window.Motion) window.Motion.scan(document); }catch(_){}
}

// ── Timeline search — scan ALL slots (across all week offsets) ──────────────
function computeAllTlMatches(){
  const q=(S.tlSearchQuery||"").toLowerCase().trim();
  if(!q){_allTlMatches=[];return;}
  _allTlMatches=(S.timeline||[]).filter(s=>{
    const cli=(s.client||"").trim()||(s.numero_of||s.reference||"");
    const fm=s.format_l&&s.format_h?`${s.format_l} × ${s.format_h} mm`:"";
    const lz=s.laize?String(s.laize):"";
    const fields=[cli,s.numero_of||"",s.reference||"",s.ref_produit||"",s.description||"",fm,lz].map(f=>f.toLowerCase());
    return fields.some(f=>f.includes(q));
  });
  scheduleCrossMachineSearch();
}

// ── Cross-machine search (chips) ─────────────────────────────────────────────
let _xmsT=null;
let _xmsInflight=null;
let _xmsLastKey="";
async function crossMachineSearchNow(){
  if(!MID) return;
  const q1=(S.searchQuery||"").trim();
  const q2=(S.tlSearchQuery||"").trim();
  const key=(q1||"")+"\n"+(q2||"")+"\n"+String(MID||"");
  if(key===_xmsLastKey) return;
  _xmsLastKey=key;

  // Rien à chercher → cacher les chips.
  const tlEl=document.getElementById("tl-other-machines");
  const lsEl=document.getElementById("list-other-machines");
  if(!q1 && !q2){
    if(tlEl) tlEl.style.display="none";
    if(lsEl) lsEl.style.display="none";
    return;
  }

  const q = (q2 || q1).trim();
  if(!q){
    if(tlEl) tlEl.style.display="none";
    if(lsEl) lsEl.style.display="none";
    return;
  }

  if(_xmsInflight) return await _xmsInflight;
  _xmsInflight=(async()=>{
    try{
      const rows=await api(`/search?q=`+encodeURIComponent(q)+`&limit_per_machine=3`);
      const list=Array.isArray(rows)?rows:[];
      const other=list.filter(r=>String(r.machine_id)!==String(MID) && (r.count||0)>0);

      function mkChip(r){
        const label=(r.count||0)+' dossier'+((r.count||0)>1?'s':'')+' en '+(r.nom||('Machine '+r.machine_id));
        const b=document.createElement("button");
        b.type="button";
        b.className="btn-s";
        b.textContent=label;
        b.style.padding="6px 10px";
        b.style.fontSize="11px";
        b.style.borderRadius="999px";
        b.style.whiteSpace="nowrap";
        b.title="Ouvrir cette machine avec la même recherche";
        b.onclick=()=>{
          const sp=new URLSearchParams();
          sp.set("machine", String(r.machine_id));
          if(q1) sp.set("q", q1);
          if(q2) sp.set("tlq", q2);
          sp.set("auto","1");
          appendPlanningVueParam(sp);
          location.href="/planning?"+sp.toString();
        };
        return b;
      }

      // Timeline chips
      if(tlEl){
        tlEl.innerHTML="";
        if(other.length){
          other.forEach(r=>tlEl.appendChild(mkChip(r)));
          tlEl.style.display="flex";
        }else tlEl.style.display="none";
      }
      // List chips
      if(lsEl){
        lsEl.innerHTML="";
        if(other.length){
          other.forEach(r=>lsEl.appendChild(mkChip(r)));
          lsEl.style.display="flex";
        }else lsEl.style.display="none";
      }
    }catch(e){
      if(tlEl) tlEl.style.display="none";
      if(lsEl) lsEl.style.display="none";
    }
  })();
  try{return await _xmsInflight;}finally{_xmsInflight=null;}
}
function scheduleCrossMachineSearch(){
  if(_xmsT) clearTimeout(_xmsT);
  _xmsT=setTimeout(()=>{_xmsT=null;crossMachineSearchNow();},280);
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
    el.style.outline=isCur?"3px solid var(--accent)":"3px solid rgba(255,255,255,.7)";
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
    const mn=addD(m1,wi*7);
    const lblCls=wi===0?"cur":"nxt";
    tlBlocks+=`<div ${wi<nw-1?'style="margin-bottom:16px"':""}>
      ${weekHeaderRow(mn,lblCls)}
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
function lockedPositionsFromIds(ids){
  const locked = (S.entries||[]).filter(e=>e.statut==="en_cours"||e.statut==="termine").map(e=>e.id);
  const pos={};
  locked.forEach(id=>{ const i=ids.indexOf(id); if(i>=0) pos[id]=i; });
  return pos;
}
function reorderKeepsLocked(idsBefore, idsAfter){
  const p0=lockedPositionsFromIds(idsBefore);
  for(const k in p0){
    const id=+k;
    if(idsAfter.indexOf(id)!==p0[k]) return false;
  }
  return true;
}
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
    const targetStat=(target.dataset&&target.dataset.statut)?String(target.dataset.statut):"";
    if(targetStat && targetStat!=="attente"){
      showToast("Déplacement impossible — cible verrouillée (en cours/terminé).","info");
      return;
    }
    const eid=+target.dataset.eid;
    if(eid===fromEid) return;
    const ids=S.entries.map(e=>e.id);
    const fromIdx=ids.indexOf(fromEid);
    const toIdx=ids.indexOf(eid);
    if(fromIdx<0||toIdx<0) return;
    const [moved]=ids.splice(fromIdx,1);
    ids.splice(toIdx,0,moved);
    if(!reorderKeepsLocked(S.entries.map(e=>e.id), ids)){
      showToast("Déplacement impossible — cela déplacerait un dossier en cours/terminé.","danger");
      await load();
      return;
    }
    try{
      await api(`/machines/${MID}/reorder`,{method:"POST",body:JSON.stringify({entry_ids:ids})});
      await load();
      showToast("Ordre enregistré.","success");
    }catch(e){
      showToast(apiErrorMessage(e,"Réordonnancement impossible."),"danger");
      await load();
    }
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
    const off=isPlanningDayOff(di,ds);
    const w=getWhForDate(di,d,ds);
    if(!w)continue;
    const dayT=off?0:(w.e-w.s);
    const hourLbl=off?"—":fmtWindow(w.s,w.e);
    const nonTravail=off;
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
    const dayCmt=((S.dayComments||{})[d.ds]||"").trim();
    const hasDayCmt=!!dayCmt;
    h+=`<div class="dh-cell ${td?"today":""} ${sa?"sat":""}${hasDayCmt?" has-cmt":""}" style="flex:${d.tWork}">
      <div style="display:flex;flex-direction:column;align-items:center;gap:2px">
        <div class="dh-date-lbl" style="cursor:pointer" onclick="openDayCommentModal('${d.ds}',${d.di})" title="Commentaire jour">${DN[d.di]} ${fd(d.date)}</div>
        <div style="display:flex;align-items:center;gap:4px;justify-content:center">
          ${CAN_EDIT?`<button type="button" class="dh-hours-btn" onclick="event.stopPropagation();openHorairesModal('${d.ds}',${d.di})">${escAttr(d.hourLbl)}</button>`:`<small>${escAttr(d.hourLbl)}</small>`}
          <button type="button" class="cmt-btn${hasDayCmt?" has-cmt":""}" onclick="event.stopPropagation();openDayCommentModal('${d.ds}',${d.di})" title="${hasDayCmt?"Modifier le commentaire":"Commentaire jour"}">${icon("message-square",11)}</button>
        </div>
        ${dayCmt?`<div class="cal-cmt-text day-cmt-text">${escHtml(dayCmt)}</div>`:""}
      </div>
    </div>`;;
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
    // IMPORTANT: un dossier "terminé" peut légitimement chevaucher 2 semaines.
    // On n'applique pas le seuil de masquage sur les terminés (affichage uniquement).
    if(spansMultipleWeeks && (s.statut!=="termine") && visibleWorkH < TL_MIN_VISIBLE_H_WHEN_SPLIT) return;
    const l=(sp/tot)*100,w=Math.max(.5,((ep-sp)/tot)*100);
    const co=colorForId(s.entry_id||idx+1);
    const fm=s.format_l&&s.format_h?`${s.format_l} × ${s.format_h} mm`:"";
    const lz=s.laize?`${s.laize} mm`:"";
    // Ligne 2 : format + laize (vue prod)
    const line2Txt=[fm,lz].filter(Boolean).join(" | ");
    // Ligne 3 : date livraison + commentaire (vue prod)
    const dateLiv=s.date_livraison?`à livrer pour ${s.date_livraison}`:"";
    const com=s.commentaire?String(s.commentaire).trim():"";
    const line3Parts=[dateLiv,com].filter(Boolean);
    const line3Txt=line3Parts.join(" | ");
    const exig=s.exigences_production?String(s.exigences_production).trim():"";
    const subTxt=line2Txt; // pour compatibilité tooltip
    const fmTip=fm||"—";
    const st=s.statut==="en_cours"?"En cours":s.statut==="termine"?"Terminé":"En attente";
    const cli=(s.client||"").trim()||(s.numero_of||s.reference||"—");
    const qteEtiq=(s.has_of&&s.qte_etiquettes!=null&&s.qte_etiquettes!==0)?s.qte_etiquettes:null;
    const meta=[s.numero_of||s.reference,s.ref_produit,s.description].filter(Boolean).join(" | ");
    const noOf=(s.numero_of||s.reference||"").trim().toLowerCase();
    const activeNo=S.activeDossier?(S.activeDossier.no_dossier||"").trim().toLowerCase():"";
    const isActive=!!(activeNo&&noOf&&activeNo===noOf);
    // Search match
    let matchCls="";
    if(tlQ){
      const fields=[cli,s.numero_of||"",s.reference||"",s.ref_produit||"",s.description||"",fm,lz,s.laize?String(s.laize):"",exig,com].map(f=>f.toLowerCase());
      matchCls=fields.some(f=>f.includes(tlQ))?"tl-match":"tl-no-match";
    }
    // Zébré « à placer / non validé » : levé seulement si placé (a_placer=0) ET validé (valide=1)
    const aplacerCls=(Number(s.a_placer||0)===0&&Number(s.valide||0)===1)?"":"slot-aplacer";
    const reelTermineCls=(hasSaisieReelle() && (s.statut_reel==="reellement_termine") && s.statut!=="en_cours")||s.statut==="termine"?"slot-reel-termine":"";
    const destock=s.destockage==="done";
    const reelForDrag=hasSaisieReelle() ? ((s.statut_reel||"reellement_en_attente")==="reellement_en_attente") : true;
    const canDragSlot=CAN_EDIT&&s.statut!=="en_cours"&&s.statut!=="termine"&&reelForDrag;
    const canResizeSlot=CAN_EDIT&&s.statut!=="termine"&&(s.statut==="en_cours"||(s.statut==="attente"&&reelForDrag));
    const termineSlideCls=(CAN_EDIT&&s.statut==="termine")?"slot-termine-movable":"";
    const resizeHint="Bord droit : ajuster la durée. Reste du créneau : réordonner (si disponible).";
    const resizeHandle=canResizeSlot?`<div class="slot-resize-handle" data-eid="${s.entry_id||idx}" data-resize="1" title="${escAttr(resizeHint)}"></div>`:"";
    const termineTitle=termineSlideCls?"Dossier terminé — glisser pour décaler le créneau sur la ligne de temps":"";
    const sr = hasSaisieReelle() ? (s.statut_reel||"reellement_en_attente") : "reellement_en_attente";
    const durAff = (s.statut==="termine") ? (workHoursBetween(ss,se) ?? s.duree_heures) : s.duree_heures;

    // ── Vue Expédition : luminosité palettes + infos expé ─────────────
    const isExpeVue = S.planningVue==="expe" || S.planningVue==="prod_expe";
    const nbPalettes = (s.nb_palettes!=null && s.nb_palettes!==undefined) ? s.nb_palettes : null;
    let expeBrightnessStyle="";
    if(isExpeVue && nbPalettes!==null){
      expeBrightnessStyle = nbPalettes>=6 ? "" : "filter:brightness(0.4);";
    }
    // Date de livraison imposée — la date passe en rouge dans le slot et le tooltip
    const dlImp=!!s.date_livraison_imposee;
    const dlRed=dlImp?"color:var(--danger);font-weight:700":"";
    // Lignes en vue expé : line2 = date livraison + département, line3 = RDV si coché
    let line2SlotHtml="", line3SlotHtml="";
    if(isExpeVue){
      const dlPart=s.date_livraison?`<span style="${dlRed}">${escHtml(s.date_livraison)}</span>`:"";
      const deptPart=s.departement_livraison?escHtml(s.departement_livraison):"";
      const parts=[dlPart,deptPart].filter(Boolean);
      line2SlotHtml=parts.length?parts.join(" · "):"";
      line3SlotHtml=s.prise_rdv?"RDV à prendre":"";
    } else {
      line2SlotHtml=line2Txt?escHtml(line2Txt):"";
      const dateLivHtml=s.date_livraison?`<span style="${dlRed}">${escHtml("à livrer pour "+s.date_livraison)}</span>`:"";
      const comHtml=com?escHtml(com):"";
      const l3parts=[dateLivHtml,comHtml].filter(Boolean);
      line3SlotHtml=l3parts.length?l3parts.join(" | "):"";
    }

    h+=`<div class="slot ${matchCls} ${aplacerCls} ${reelTermineCls} ${termineSlideCls}" data-eid="${s.entry_id||idx}" data-statut="${escAttr(s.statut||"attente")}" data-statut-reel="${escAttr(sr)}" ${canDragSlot?'draggable="true"':''} style="left:${l}%;width:${w}%;background:${co};box-shadow:0 2px 8px ${co}55;${expeBrightnessStyle}${isActive?"border:2px solid var(--accent);animation:activePulse 2.2s ease-in-out infinite;":"border:1.5px solid rgba(148,163,184,.35);"}"
      onmouseenter="showTip(event,this)" onmousemove="moveTip(event)" onmouseleave="hideTip()"
      ondblclick="hideTip();openEdit(${s.entry_id||idx});event.stopPropagation()"
      data-livraison="${escAttr(fmtLivraisonLong(s.date_livraison||""))}" data-ref="${escAttr(cli)}" data-lbl="${escAttr(meta)}" data-rfp="${escAttr(s.ref_produit||"")}" data-fmt="${escAttr(fmTip)}" data-dur="${escAttr(fmtDur(durAff))}" data-exigences="${escAttr(exig)}" data-qte-etiq="${escAttr(qteEtiq!=null?fmtQty(qteEtiq):"")}" data-nb-palettes="${escAttr(nbPalettes!=null?String(nbPalettes):"")}"`+
      ` data-prise-rdv="${s.prise_rdv?'1':'0'}" data-dept="${escAttr(s.departement_livraison||"")}" data-dl-imp="${dlImp?'1':'0'}" data-support="${escAttr(s.ft_support||"")}" data-adhesif="${escAttr(s.ft_adhesif||"")}" data-palette-type="${escAttr(s.ft_palette_type||"")}" data-mandrin="${escAttr(s.ft_mandrin_dia||"")}" data-cond="${escAttr(s.ft_conditionnement_phrase||"")}" data-laize="${escAttr(s.laize?String(s.laize)+' mm':"")}"`+
      ` data-planned-start="${escAttr(String(s.start||""))}" data-planned-end="${escAttr(String(s.end||""))}"
      data-deb="${escAttr(fdt(ss))}" data-fin="${escAttr(fdt(se))}" data-st="${escAttr(st)}" data-co="${escAttr(co)}"${termineTitle?` title="${escAttr(termineTitle)}"`:""}>
      ${destock?`<div style="position:absolute;top:4px;right:4px;width:10px;height:10px;border-radius:50%;background:rgba(71,85,105,.9);pointer-events:none;z-index:5;flex-shrink:0"></div>`:""}
      ${resizeHandle}
      ${w>5?`<div class="slot-inner"><span class="line1">${escAttr(cli)}${fscBadgeHtml(s)}</span>${line2SlotHtml?`<span class="line2">${line2SlotHtml}</span>`:""}${line3SlotHtml?`<span class="line3">${line3SlotHtml}</span>`:""}${(()=>{const _isExpe=(S.planningVue==="expe"||S.planningVue==="prod_expe");if(_isExpe){return qteEtiq==null?`<span class="line-no-of">pas d'OF lié</span>`:"";}return exig?`<span class="line-exig" title="${escAttr(exig)}">${escAttr(exig)}</span>`:"";})()}</div>`:w>1.8?`<div style="overflow:hidden;height:100%;display:flex;align-items:center;justify-content:center"><div class="slot-vert-txt" style="writing-mode:vertical-rl;text-orientation:mixed;transform:rotate(180deg)">${escAttr((cli.slice(0,6)+(cli.length>6?".":"")).toUpperCase())}</div></div>`:""}</div>`;
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
  const reelAvance=hasSaisieReelle() && (e.statut_reel==="reellement_en_saisie"||e.statut_reel==="reellement_termine");
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
  const aplacerRowCls=(Number(e.a_placer||0)===0&&Number(e.valide||0)===1)?"":"tr-aplacer";
  const reelTermineRowCls=(hasSaisieReelle() && e.statut_reel==="reellement_termine")?"tr-reel-termine":"";
  const reelBadge=(()=>{
    if(!hasSaisieReelle()) return "";
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
    <span class="lbl-main">${escAttr(cli)}${fscBadgeHtml(e)}${reelBadge?`<br><span style="display:inline-block;margin-top:2px">${reelBadge}</span>`:""}</span>
    <span class="cell-mini">${escAttr(fm)}${fm!=="—"?" mm":""}</span>
    <span class="cell-mini">${of}</span>
    <span class="cell-mini">${rfp}</span>
    <span class="cell-mini">${lz}</span>
    <span class="cell-mini">${escAttr(fmtDl(e.date_livraison||""))}</span>
    <span class="cell-mini" style="font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${com}">${com}</span>
    <span class="cell-mini">${fmtDur((e.statut==="termine" && e.planned_start && e.planned_end)?(workHoursBetween(new Date(e.planned_start), new Date(e.planned_end)) ?? e.duree_heures):e.duree_heures)}</span>
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
    showToast("Ordre enregistré.","success");
  }catch(e){
    showToast(apiErrorMessage(e,"Réordonnancement impossible."),"danger");
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
  const liv=(d.livraison||"").trim();
  const exigTip=(d.exigences||"").trim();
  const isExpeVueTip=S.planningVue==="expe"||S.planningVue==="prod_expe";
  const nbPalTip=(d.nbPalettes||"").trim();
  const deptTip=(d.dept||"").trim();
  const rdvTip=d.priseRdv==="1";
  const dlImpTip=d.dlImp==="1";
  // Vue expé : on retire 'Palettes prévues' de la colonne générale (déplacé dans Infos expéditions)
  const expeTipRows=isExpeVueTip?`${deptTip?`<span class="k">Département</span><span class="v">${escHtml(deptTip)}</span>`:""}${rdvTip?`<span class="k">RDV</span><span class="v" style="color:var(--warn);font-weight:600">À prendre</span>`:""}`:"" ;
  const livStyle=dlImpTip?"color:var(--danger);font-weight:700":"";
  const livSuffix=dlImpTip?' <span style="font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.5px">(imposée)</span>':"";
  // Colonne gauche : infos générales (réf produit, format, dates, statut)
  const colGen = `${d.rfp?`<span class="k">Réf produit</span><span class="v">${d.rfp}</span>`:""}
    <span class="k">Format</span><span class="v">${d.fmt||"—"}</span>
    <span class="k">Durée</span><span class="v">${d.dur||""}</span>
    <span class="k">Début</span><span class="v">${d.deb||""}</span>
    <span class="k">Fin</span><span class="v">${d.fin||""}</span>
    <span class="k">Statut</span><span class="v" style="color:${d.st==="En cours"?"var(--green)":d.st==="Terminé"?"var(--muted)":"var(--amber)"};font-weight:600">${d.st||""}</span>
    ${(()=>{const r=d.statutReel||"";if(r==="reellement_termine")return`<span class="k">Saisie</span><span class="v" style="color:var(--muted)">✓ Terminé</span>`;if(r==="reellement_en_saisie")return`<span class="k">Saisie</span><span class="v" style="color:var(--success)">⚙ En cours</span>`;return"";})()}
    ${expeTipRows}`;
  // Colonne droite : infos techniques (frontal/adhésif depuis fiche, qté étiquettes)
  const supTxt=(d.support||"").trim();
  const adhTxt=(d.adhesif||"").trim();
  const palTxt=(d.paletteType||"").trim();
  const manTxt=(d.mandrin||"").trim();
  const qteTxt=(d.qteEtiq||"").trim();
  const condTxt=(d.cond||"").trim();
  // Colonne technique (vue prod)
  const lzTxt=(d.laize||"").trim();
  const colTech = `${lzTxt?`<span class="k">Laize</span><span class="v">${escHtml(lzTxt)}</span>`:""}
    ${supTxt?`<span class="k">Frontal</span><span class="v">${escHtml(supTxt)}</span>`:""}
    ${adhTxt?`<span class="k">Adhésif</span><span class="v">${escHtml(adhTxt)}</span>`:""}
    ${manTxt?`<span class="k">Ø mandrin</span><span class="v">${escHtml(manTxt)}</span>`:""}
    ${palTxt?`<span class="k">Type palette</span><span class="v">${escHtml(palTxt)}</span>`:""}
    ${qteTxt?`<span class="k">Qté étiquettes</span><span class="v" style="color:var(--accent);font-weight:600">${escHtml(qteTxt)}</span>`:""}`;
  // Colonne expédition (vue expé)
  const colExpe = `${nbPalTip?`<span class="k">Nb palettes</span><span class="v" style="color:${+nbPalTip>=6?'var(--success)':'var(--muted)'};font-weight:700">${escHtml(nbPalTip)}</span>`:""}
    ${palTxt?`<span class="k">Type palette</span><span class="v">${escHtml(palTxt)}</span>`:""}
    <span class="k">Qté étiquettes</span><span class="v" style="color:${qteTxt?'var(--accent)':'var(--muted)'};font-weight:${qteTxt?600:500};font-style:${qteTxt?'normal':'italic'}">${qteTxt?escHtml(qteTxt):"pas d'OF relié"}</span>
    ${condTxt?`<span class="k">Conditionnement</span><span class="v">${escHtml(condTxt)}</span>`:""}`;
  const hasTech = !!(lzTxt || supTxt || adhTxt || palTxt || manTxt || qteTxt);
  const hasExpe = !!(nbPalTip || palTxt || qteTxt || condTxt);
  // Branchement selon la vue : expé → 'Infos expéditions', sinon → 'Infos techniques'
  const showExpeCol = isExpeVueTip && hasExpe;
  const showTechCol = !isExpeVueTip && hasTech;
  const colSide = showExpeCol ? colExpe : (showTechCol ? colTech : null);
  const colTitle = showExpeCol ? 'Infos expéditions' : 'Infos techniques';
  const bodyHtml = colSide
    ? `<div class="tip-cols">
         <div><div class="tip-col-hdr">Infos générales</div><div class="tip-grid">${colGen}</div></div>
         <div><div class="tip-col-hdr">${colTitle}</div><div class="tip-grid">${colSide}</div></div>
       </div>`
    : `<div class="tip-grid">${colGen}${qteTxt?`<span class="k">Qté étiquettes</span><span class="v" style="color:var(--accent);font-weight:600">${escHtml(qteTxt)}</span>`:""}</div>`;
  tipEl.innerHTML=`<div class="tip-hdr"><div class="tip-bar" style="background:${d.co||"#888"}"></div><div><div class="tip-ref">${d.ref||"—"}</div>${sub}</div></div>
    ${liv?`<div class="tip-livraison" style="${livStyle}">Livraison : ${escHtml(liv)}${livSuffix}</div>`:""}
    ${(exigTip && !isExpeVueTip)?`<div class="tip-exig"><span class="k">Exigences de production</span>${escHtml(exigTip)}</div>`:""}
    ${bodyHtml}
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
  if(tbody.dataset.ddBound==="1") return;
  tbody.dataset.ddBound="1";

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
    const st = (row.dataset&&row.dataset.statut)?String(row.dataset.statut):"";
    if(st==="en_cours" || st==="termine"){
      e.preventDefault();
      showToast("Déplacement impossible — dossier en cours/terminé.","info");
      return;
    }
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
    const idsBefore=S.entries.map(en=>en.id);
    const ids=idsBefore.slice();
    const [moved]=ids.splice(_ddDragIdx,1);
    ids.splice(insertAt,0,moved);
    if(!reorderKeepsLocked(idsBefore, ids)){
      clearState();
      showToast("Déplacement impossible — cela déplacerait un dossier en cours/terminé.","danger");
      await load();
      return;
    }

    clearState();
    _suppressAutoScroll=true;

    let reorderOk=false;
    try{
      await api(`/machines/${MID}/reorder`,{method:"POST",body:JSON.stringify({entry_ids:ids})});
      reorderOk=true;
    }catch(err){
      console.error("Reorder failed",err);
      showToast(apiErrorMessage(err,"Réordonnancement impossible."),"danger");
    }
    try{
      await load();
    }catch(e){
      console.error("load after reorder",e);
    }
    _suppressAutoScroll=false;
    if(reorderOk) showToast("Ordre enregistré.","success");
    requestAnimationFrame(()=>{
      const main=document.querySelector(".main");
      if(main) main.scrollTop=savedScroll;
      if(tbody&&savedTbodyScroll>0) tbody.scrollTop=savedTbodyScroll;
    });
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
          if(hasSaisieReelle() && data.saisie_found===false && newStat==="termine"){
            showToast("Dossier terminé — aucune saisie de production associée.","info");
          }else if(hasSaisieReelle() && data.saisie_found===true && newStat==="termine"){
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
    dossierFields(e.numero_of||e.reference||"",e.client||"",e.ref_produit||"",e.laize||"",e.date_livraison||"",e.commentaire||"",e.exigences_production||"",e.format_l||"",e.format_h||"",e.duree_heures,"attente",false,1,e.fsc_requis||0,e.fsc_type_requis||"",e.departement_livraison||"",e.prise_rdv||0,e.date_livraison_imposee||0,0,e.etiquettes_par_carton??null),
    "Ajouter","submitDuplicate()"
  ,"","",false,"md--dossier");
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
    // Report fidèle de tous les attributs du dossier source, sinon la cible
    // repart sur les défauts (a_placer=1 → relégué en fin de timeline, perte FSC/RDV/etc.).
    const payload={
      reference:e.numero_of||e.reference||"",
      numero_of:e.numero_of||e.reference||"",
      client:e.client||"",
      ref_produit:e.ref_produit||"",
      laize:e.laize||null,
      date_livraison:e.date_livraison||"",
      commentaire:e.commentaire||"",
      exigences_production:e.exigences_production||"",
      format_l:e.format_l||null,
      format_h:e.format_h||null,
      duree_heures:e.duree_heures||8,
      statut:"attente",
      dos_rvgi:e.dos_rvgi||"",
      a_placer:Number(e.a_placer||0),
      valide:Number(e.valide||0),
      fsc_requis:Number(e.fsc_requis||0),
      fsc_type_requis:e.fsc_type_requis||"",
      departement_livraison:e.departement_livraison||"",
      prise_rdv:Number(e.prise_rdv||0),
      date_livraison_imposee:Number(e.date_livraison_imposee||0)
    };
    await api(`/machines/${MID}/entries/${_switchEntryId}`,{method:"DELETE"});
    if(afterEntryId){
      await api(`/machines/${targetMachineId}/insert-after/${afterEntryId}`,{method:"POST",body:JSON.stringify(payload)});
    }else{
      await api(`/machines/${targetMachineId}/entries`,{method:"POST",body:JSON.stringify({...payload,position:1})});
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

function modalHTML(title,fields,submitLabel,onSubmitFn,headerAction="",footerLeft="",compact=false,extraMdClass=""){
  const cls=`md${compact?' md--compact':''}${extraMdClass?(' '+extraMdClass):''}`;
  return`<div class="mo" onclick="if(event.target===this)closeM()"><div class="${cls}">
    <div class="md-hdr" style="display:flex;align-items:center;justify-content:space-between;margin-bottom:24px;gap:12px;flex-wrap:wrap">
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

function onFscRequisChange(){
  const chk=document.getElementById("fsc-requis-chk");
  const wrap=document.getElementById("fsc-type-wrap");
  if(!chk||!wrap) return;
  wrap.style.display=chk.checked?"block":"none";
}

function fscBadgeHtml(e){
  if(!e||!(e.fsc_requis===1||e.fsc_requis===true)) return "";
  const typ=(e.fsc_type_requis||"").trim();
  const typeLbl=typ==="fsc_100"?"FSC 100%":typ==="fsc_mix"?"FSC Mix":typ==="fsc_recycled"?"FSC Recycled":"";
  const title="Certification FSC requise"+(typeLbl?" — "+typeLbl:"");
  return `<span title="${escAttr(title)}" style="background:var(--accent-bg);color:var(--accent);font-size:10px;font-weight:700;padding:1px 5px;border-radius:4px;margin-left:4px;vertical-align:middle">FSC</span>`;
}

function fscTypeRequisLabel(t){
  const typ=(t||"").trim();
  if(typ==="fsc_100") return "FSC 100%";
  if(typ==="fsc_mix") return "FSC Mix";
  if(typ==="fsc_recycled") return "FSC Recycled";
  return typ;
}

function dossierFields(numero_of,client,ref_produit,laize,date_livraison,commentaire,exigences_production,fl,fh,dur,statut,showStatut,aPlacer=1,fscRequis=0,fscType="",deptLivraison="",priseRdv=0,dlImposee=0,valide=0,etiqParCarton=null){
  const fscOn=fscRequis===1||fscRequis===true;
  const fscTyp=(fscType&&["fsc_100","fsc_mix","fsc_recycled"].includes(fscType))?fscType:"fsc_mix";
  const rdvOn=priseRdv===1||priseRdv===true;
  const dlImpOn=dlImposee===1||dlImposee===true;
  const valideOn=valide===1||valide===true;
  const dlVal=/^\d{4}-\d{2}-\d{2}$/.test(date_livraison)?date_livraison:"";
  return`
    <div class="dossier-sections">
      <div class="dossier-section">
        <span class="dossier-section-label">Informations générales</span>
        <div class="fd"><label>Numéro d'OF</label><input id="f-of" value="${escAttr(numero_of)}" placeholder="9936280"></div>
        <div class="fd"><label>Client</label><input id="f-cli" value="${escAttr(client)}" placeholder="Nom du client"></div>
        <div class="fd"><label>Durée (${MIND}–${MAXD}h)</label>
          <input type="number" id="f-dur" min="${MIND}" max="${MAXD}" step="0.25" value="${dur}" oninput="document.getElementById('f-dur-fill').style.width=((Math.max(${MIND},Math.min(${MAXD},+this.value||${MIND}))-${MIND})/(${MAXD}-${MIND})*100)+'%'">
          <div class="dur-b"><div class="dur-f" id="f-dur-fill" style="width:${durBar(dur)}"></div></div>
        </div>
        ${showStatut?`<div class="fd"><label>Statut</label><select id="f-stat">
          <option value="attente" ${statut==="attente"?"selected":""}>En attente</option>
          <option value="en_cours" ${statut==="en_cours"?"selected":""}>En cours</option>
          <option value="termine" ${statut==="termine"?"selected":""}>Terminé</option>
        </select></div>`:""}
        <div class="fd">
          <div style="display:flex;flex-wrap:wrap;gap:18px;align-items:center">
            <label class="dossier-check-lbl" style="margin:0">
              <input type="checkbox" id="f-aplacer" ${aPlacer?"checked":""} style="width:16px;height:16px;accent-color:var(--accent);cursor:pointer">
              À placer au planning
            </label>
            <label class="dossier-check-lbl" style="margin:0">
              <input type="checkbox" id="f-valide" ${valideOn?"checked":""} style="width:16px;height:16px;accent-color:var(--success);cursor:pointer">
              Dossier validé
            </label>
          </div>
        </div>
      </div>
      <div class="dossier-section">
        <span class="dossier-section-label">Fiche produit</span>
        <div class="dossier-fgrid dossier-fgrid--2">
          <div class="fd"><label>Réf produit</label><input id="f-rp" value="${escAttr(ref_produit)}" placeholder="REF-PROD"></div>
          <div class="fd"><label>Laize (mm)</label><input type="number" id="f-laize" value="${escAttr(laize)}" placeholder="510"></div>
          <div class="fd"><label>Largeur (mm)</label><input type="number" id="f-fl" value="${escAttr(fl)}" placeholder="100"></div>
          <div class="fd"><label>Hauteur (mm)</label><input type="number" id="f-fh" value="${escAttr(fh)}" placeholder="70"></div>
          ${machineKey()==="REP"?`<div class="fd fd--full">
            <label>Étiquettes par carton (Repiquage)</label>
            <input type="number" id="f-epc" min="1" step="1" value="${etiqParCarton!=null?escAttr(String(etiqParCarton)):''}" placeholder="Ex : 240">
            <span style="font-size:11px;color:var(--muted);display:block;margin-top:4px">Paramétrage utilisé par la saisie de production Repiquage pour compter les cartons. Laisser vide si non concerné.</span>
          </div>`:""}
          <div class="fd fd--full">
            <span class="dossier-sub-lbl">Certification FSC</span>
            <div style="display:flex;align-items:center;gap:12px">
              <input type="checkbox" id="fsc-requis-chk" ${fscOn?"checked":""} onchange="onFscRequisChange()" style="width:16px;height:16px;accent-color:var(--accent);cursor:pointer">
              <label for="fsc-requis-chk" class="dossier-check-lbl" style="margin:0">Certification FSC requise sur ce dossier</label>
            </div>
            <div id="fsc-type-wrap" style="display:${fscOn?"block":"none"};margin-top:8px">
              <label class="dossier-sub-lbl" style="margin-bottom:4px">Type requis</label>
              <select id="fsc-type-requis" class="form-sel" style="width:100%">
                <option value="fsc_100" ${fscTyp==="fsc_100"?"selected":""}>FSC 100%</option>
                <option value="fsc_mix" ${fscTyp==="fsc_mix"?"selected":""}>FSC Mix</option>
                <option value="fsc_recycled" ${fscTyp==="fsc_recycled"?"selected":""}>FSC Recycled</option>
              </select>
            </div>
          </div>
        </div>
      </div>
      <div class="dossier-section">
        <span class="dossier-section-label">Livraison</span>
        <div class="dossier-fgrid dossier-fgrid--2">
          <div class="fd"><label>Date de livraison</label><input type="date" id="f-dl" value="${escAttr(dlVal)}"></div>
          <div class="fd"><label>Département de livraison</label><input id="f-dept" value="${escAttr(deptLivraison)}" placeholder="Ex : 75, 69, Rhône…"></div>
          <div class="fd fd--full">
            <div style="display:flex;flex-wrap:wrap;gap:18px;align-items:center">
              <label class="dossier-check-lbl" style="margin:0">
                <input type="checkbox" id="f-rdv" ${rdvOn?"checked":""} style="width:16px;height:16px;accent-color:var(--accent);cursor:pointer">
                Prendre un Rendez-Vous
              </label>
              <label class="dossier-check-lbl" style="margin:0">
                <input type="checkbox" id="f-dl-imp" ${dlImpOn?"checked":""} style="width:16px;height:16px;accent-color:var(--danger);cursor:pointer">
                Date de livraison imposée
              </label>
            </div>
          </div>
        </div>
      </div>
      <div class="dossier-section">
        <span class="dossier-section-label">Particularités et commentaires</span>
        <div class="fd"><label>Commentaire</label><input id="f-com" value="${escAttr(commentaire)}" placeholder="Bobine, contraintes, etc."></div>
        <div class="fd"><label>Exigences de production</label><textarea id="f-exig" class="dossier-ta" rows="2" placeholder="Consignes impératives pour l'atelier (visibles en priorité sur la timeline)">${escHtml(exigences_production||"")}</textarea></div>
      </div>
    </div>`
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
    exigences_production:(document.getElementById("f-exig")?.value||"").trim(),
    duree_heures:Math.max(MIND,Math.min(MAXD,parseFloat(document.getElementById("f-dur").value)||8)),
    a_placer:document.getElementById("f-aplacer")?.checked?1:0,
    valide:document.getElementById("f-valide")?.checked?1:0,
    departement_livraison:(document.getElementById("f-dept")?.value||"").trim(),
    prise_rdv:document.getElementById("f-rdv")?.checked?1:0,
    date_livraison_imposee:document.getElementById("f-dl-imp")?.checked?1:0,
    etiquettes_par_carton:(()=>{
      const v=document.getElementById("f-epc")?.value;
      if(v==null||String(v).trim()==='')return null;
      const n=parseInt(String(v).trim(),10);
      return (Number.isFinite(n)&&n>0)?n:null;
    })(),
  };
  const fscChk=document.getElementById("fsc-requis-chk");
  const fscOn=!!(fscChk&&fscChk.checked);
  d.fsc_requis=fscOn?1:0;
  d.fsc_type_requis=fscOn?(document.getElementById("fsc-type-requis")?.value||"fsc_mix"):"";
  if(withStatut)d.statut=document.getElementById("f-stat").value;
  return d;
}

let _addTab='manual';
let _addOfFile=null,_addOfParsed=null,_addOfParsing=false;

function addOfDelaiToDateInput(raw){
  const s=(raw!=null?String(raw):'').trim();
  const m=s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if(m) return `${m[3]}-${String(m[2]).padStart(2,'0')}-${String(m[1]).padStart(2,'0')}`;
  return /^\d{4}-\d{2}-\d{2}$/.test(s)?s:'';
}

function dossierFieldsFromOfParsed(p){
  const numero=(p.of_numero!=null?String(p.of_numero):'').trim();
  const ref=(p.reference!=null?String(p.reference):'').trim();
  const laize=p.laize!=null?String(p.laize):'';
  let fl='',fh='';
  const fmt=(p.format!=null?String(p.format):'').trim();
  const fm=fmt.match(/(\d+(?:[.,]\d+)?)\s*[x×]\s*(\d+(?:[.,]\d+)?)/i);
  if(fm){ fl=fm[1].replace(',','.'); fh=fm[2].replace(',','.'); }
  const dl=addOfDelaiToDateInput(p.delai_client);
  const com=[p.matiere,p.conditionnement].filter(Boolean).map(x=>String(x).trim()).join(' — ');
  return dossierFields(numero,'',ref,laize,dl,com,'',fl,fh,8,'attente',false);
}

function renderAddModalBody(){
  if(_addTab==='manual'){
    return dossierFields('','','','','','','','','',8,'attente',false);
  }
  if(_addOfParsing){
    return `<div style="padding:32px 16px;text-align:center;color:var(--muted);font-size:13px">Analyse en cours…</div>`;
  }
  if(!_addOfParsed){
    return `<div class="of-dropzone" id="add-of-dropzone"
      onclick="document.getElementById('add-of-file-input').click()"
      ondragover="event.preventDefault();this.classList.add('of-dropzone--active')"
      ondragleave="this.classList.remove('of-dropzone--active')"
      ondrop="addOfHandleDrop(event)">
      <div style="display:flex;justify-content:center;margin-bottom:10px;color:var(--accent)">${icon('upload',28)}</div>
      <div style="font-size:14px;font-weight:700;color:var(--text);margin-bottom:6px">Déposer le PDF de l'OF ici</div>
      <div style="font-size:12px;color:var(--muted)">ou cliquer pour sélectionner</div>
      <div style="font-size:11px;color:var(--muted);margin-top:8px">.pdf uniquement</div>
    </div>
    <input type="file" accept=".pdf" id="add-of-file-input" style="display:none"
      onchange="addOfHandleFile(this.files[0])">`;
  }
  return `<div style="font-size:12px;color:var(--text2);margin-bottom:14px;padding:10px 12px;background:var(--accent-bg);border:1px solid var(--border);border-radius:8px">Vérifiez les informations avant de valider</div>`
    +dossierFieldsFromOfParsed(_addOfParsed);
}

function renderAddModal(){
  const tabs=`<div class="view-tabs" style="margin-bottom:18px">
    <button type="button" class="view-tab ${_addTab==='manual'?'active':''}" onclick="openAddSwitchTab('manual')">Manuel</button>
    <button type="button" class="view-tab ${_addTab==='of'?'active':''}" onclick="openAddSwitchTab('of')">Depuis un OF PDF</button>
  </div>`;
  const footerBtn=_addTab==='manual'
    ? `<button type="button" class="btn-p" onclick="submitAdd()"><span style="font-size:18px;line-height:1">+</span> Ajouter</button>`
    : (_addOfParsed?`<button type="button" class="btn-p" onclick="submitAddFromOf()">Valider et créer le dossier</button>`:'');
  document.getElementById("mroot").innerHTML=`<div class="mo modal-backdrop">
    <div class="md md--dossier" style="max-width:860px;width:100%;max-height:92vh;overflow-y:auto;padding:28px 32px">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;gap:12px">
        <h3 style="margin:0;font-size:18px;font-family:var(--mono);color:var(--text)">Ajouter un dossier</h3>
        <button type="button" onclick="closeM()" aria-label="Fermer"
          style="background:none;border:none;color:var(--muted);cursor:pointer;font-size:22px;line-height:1;font-family:inherit">×</button>
      </div>
      ${tabs}
      <div id="add-modal-body">${renderAddModalBody()}</div>
      <div style="display:flex;justify-content:flex-end;align-items:center;gap:10px;margin-top:24px;flex-wrap:wrap">
        <button type="button" class="btn-s" onclick="closeM()">Annuler</button>
        ${footerBtn}
      </div>
    </div>
  </div>`;
}

function openAdd(){
  if(!CAN_EDIT) return;
  _addTab='manual';
  _addOfFile=null;_addOfParsed=null;_addOfParsing=false;
  renderAddModal();
}

function openAddSwitchTab(tab){
  _addTab=tab;
  _addOfFile=null;_addOfParsed=null;_addOfParsing=false;
  renderAddModal();
}

function addOfHandleDrop(evt){
  evt.preventDefault();
  const dz=document.getElementById('add-of-dropzone');
  if(dz) dz.classList.remove('of-dropzone--active');
  const f=evt.dataTransfer?.files?.[0];
  if(f && f.name.toLowerCase().endsWith('.pdf')) addOfHandleFile(f);
  else showToast('Fichier PDF requis.','danger');
}

async function addOfHandleFile(file){
  if(!file) return;
  if(!file.name.toLowerCase().endsWith('.pdf')){ showToast('Fichier PDF requis.','danger'); return; }
  _addOfFile=file;
  _addOfParsing=true;
  _addOfParsed=null;
  renderAddModal();
  const fd=new FormData();
  fd.append('file',file);
  try{
    const r=await fetch('/api/of/parse',{method:'POST',credentials:'include',body:fd});
    if(!r.ok) throw new Error('parse');
    _addOfParsed=await r.json();
    _addOfParsing=false;
    renderAddModal();
  }catch(e){
    _addOfFile=null;_addOfParsed=null;_addOfParsing=false;
    showToast('Erreur lecture PDF.','danger');
    renderAddModal();
  }
}

function buildAddOfValidatePayload(){
  const data={...(_addOfParsed||{})};
  const d=getFormData(false);
  if(d.numero_of) data.of_numero=d.numero_of;
  if(d.ref_produit) data.reference=d.ref_produit;
  if(d.laize!=null) data.laize=d.laize;
  if(d.format_l&&d.format_h) data.format=`${d.format_l} x ${d.format_h} mm`;
  if(d.date_livraison){
    const p=d.date_livraison.split('-');
    if(p.length===3) data.delai_client=`${p[2]}/${p[1]}/${p[0]}`;
  }
  return data;
}

async function submitAddFromOf(){
  if(!_addOfFile || !_addOfParsed) return;
  const d=getFormData(false);
  if(!d.numero_of){ showToast("Numéro d'OF requis.","danger"); return; }
  let addRes=null;
  try{
    addRes=await api(`/machines/${MID}/entries`,{method:"POST",body:JSON.stringify({reference:d.numero_of,...d})});
  }catch(e){
    showToast(apiErrorMessage(e,"Ajout impossible."),"danger");
    return;
  }
  const fd=new FormData();
  fd.append('file',_addOfFile);
  fd.append('data',JSON.stringify(buildAddOfValidatePayload()));
  try{
    const r=await fetch('/api/of/validate',{method:'POST',credentials:'include',body:fd});
    if(!r.ok) throw new Error('validate');
    closeM();load();
    if(addRes&&addRes.warning&&addRes.warning.message){ showToast(addRes.warning.message,"danger"); }
    else { showToast('Dossier ajouté.','success'); }
  }catch(e){
    closeM();load();
    showToast('Dossier créé — liaison OF impossible. Vérifiez le numéro d\'OF.','info');
  }
}

async function submitAdd(){
  const d=getFormData(false);
  if(!d.numero_of){ showToast("Numéro d'OF requis.","danger"); return; }
  try{
    const res=await api(`/machines/${MID}/entries`,{method:"POST",body:JSON.stringify({reference:d.numero_of,...d})});
    closeM();load();
    if(res&&res.warning&&res.warning.message){ showToast(res.warning.message,"danger"); }
    else { showToast("Dossier ajouté.","success"); }
  }catch(e){
    showToast(apiErrorMessage(e,"Ajout impossible."),"danger");
  }
}

async function openFscRapport(noDossier){
  const ref=(noDossier||"").trim();
  if(!ref){ showToast("Référence dossier manquante.","danger"); return; }
  try{
    const res=await fetch("/api/fabrication/tracabilite/"+encodeURIComponent(ref),{
      credentials:"include",
      headers:{"Content-Type":"application/json"},
    });
    if(!res.ok) throw await parseApiError(res);
    const ct=res.headers.get("content-type")||"";
    const data=ct.includes("application/json")?await res.json():null;
    if(!data) return;
    const syn=data.synthese||{};
    const bobines=data.bobines||[];
    const dos=data.dossier||{};
    const typeReq=fscTypeRequisLabel(dos.fsc_type_requis||"");
    const sg=syn.statut_global||"";
    const isConforme=sg==="conforme";
    const isNonConforme=sg==="non_conforme";
    const statutColor=isConforme?"var(--success)":isNonConforme?"var(--danger)":"var(--muted)";
    const genHuman=(()=>{
      const raw=String(syn.genere_a||"").trim();
      if(!raw) return "";
      try{
        const d=new Date(raw);
        if(isNaN(d)) return raw.replace("T"," ").slice(0,16);
        const dd=pad(d.getDate()),mo=pad(d.getMonth()+1),yr=d.getFullYear();
        const hh=pad(d.getHours()),mm=pad(d.getMinutes());
        return dd+"/"+mo+"/"+yr+" "+hh+":"+mm;
      }catch(e){return raw.replace("T"," ").slice(0,16);}
    })();
    const statutText=isConforme
      ? ("Conforme FSC — "+(syn.nb_bobines_fsc_conformes??0)+"/"+(syn.nb_bobines_total??0)+" bobine(s)")
      : isNonConforme
        ? ("Non conforme — "+(syn.nb_bobines_non_conformes??0)+" bobine(s) en écart")
        : ((syn.nb_bobines_total??0)===0?"Aucune bobine scannée":"Non applicable");

    const lignes=bobines.map(b=>{
      const confBadge=b.fsc_conforme===true
        ? `<span style="color:var(--success);font-weight:700">\u2713</span>`
        : b.fsc_conforme===false
          ? `<span style="color:var(--danger);font-weight:700">\u2717${b.fsc_warning?" (confirmé)":""}</span>`
          : `<span style="color:var(--muted)">\u2014</span>`;
      const scan=(b.scanned_at||"").slice(0,16).replace("T"," ");
      return `<tr style="border-bottom:1px solid var(--border2)">
        <td style="padding:7px 8px;font-family:var(--mono);font-size:12px">${escAttr(b.code_barre||"")}</td>
        <td style="padding:7px 8px;font-size:12px">${escAttr(b.fournisseur||"\u2014")}</td>
        <td style="padding:7px 8px;font-size:12px">${escAttr(b.fsc_type_claim||"Non FSC")}</td>
        <td style="padding:7px 8px;font-size:12px">${confBadge}</td>
        <td style="padding:7px 8px;font-size:11px;color:var(--muted)">${escAttr(scan)}</td>
      </tr>`;
    }).join("");

    document.getElementById("mroot").innerHTML=`
      <div class="mo" onclick="if(event.target===this)closeM()" style="z-index:2000">
        <div class="md" onclick="event.stopPropagation()" style="width:min(760px,95vw);max-width:760px;max-height:88vh;overflow-y:auto;padding:24px 28px">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:14px;flex-wrap:wrap">
            <div>
              <div style="font-size:15px;font-weight:700;color:var(--text)">Rapport traçabilité FSC</div>
              <div style="font-size:12px;color:var(--muted);margin-top:2px">
                ${escAttr(ref)}${dos.client?" — "+escAttr(dos.client):""}
                ${typeReq?" \u00b7 Requis : "+escAttr(typeReq):""}
              </div>
            </div>
            <div style="display:flex;gap:8px;flex-shrink:0;flex-wrap:wrap">
              <button type="button" class="btn-s" style="font-size:12px" onclick="window.print()">Exporter PDF</button>
              <button type="button" class="btn-s" style="font-size:12px" onclick="closeM()">Fermer</button>
            </div>
          </div>
          <div style="padding:10px 14px;border-radius:8px;margin-bottom:14px;font-weight:700;font-size:13px;
            background:${statutColor}20;border:1px solid ${statutColor};color:${statutColor}">
            ${statutText}
          </div>
          <table style="width:100%;border-collapse:collapse;font-size:13px">
            <thead>
              <tr style="border-bottom:2px solid var(--border2)">
                <th style="text-align:left;padding:7px 8px;font-size:10px;text-transform:uppercase;letter-spacing:.4px;color:var(--muted);font-weight:700">Code barre</th>
                <th style="text-align:left;padding:7px 8px;font-size:10px;text-transform:uppercase;letter-spacing:.4px;color:var(--muted);font-weight:700">Fournisseur</th>
                <th style="text-align:left;padding:7px 8px;font-size:10px;text-transform:uppercase;letter-spacing:.4px;color:var(--muted);font-weight:700">Claim</th>
                <th style="text-align:left;padding:7px 8px;font-size:10px;text-transform:uppercase;letter-spacing:.4px;color:var(--muted);font-weight:700">Statut</th>
                <th style="text-align:left;padding:7px 8px;font-size:10px;text-transform:uppercase;letter-spacing:.4px;color:var(--muted);font-weight:700">Scanné le</th>
              </tr>
            </thead>
            <tbody>${lignes||'<tr><td colspan="5" style="padding:20px;text-align:center;color:var(--muted);font-size:12px">Aucune bobine scannée sur ce dossier.</td></tr>'}</tbody>
          </table>
          <div style="margin-top:14px;padding-top:10px;border-top:1px solid var(--border2);font-size:11px;color:var(--muted)">
            Généré le ${escAttr(genHuman||syn.genere_a||"")} \u00b7 MySifa \u00b7 SIFA
          </div>
        </div>
      </div>`;
  }catch(err){
    showToast(apiErrorMessage(err,"Rapport FSC indisponible."),"danger");
  }
}

function openEdit(id){
  if(!CAN_EDIT) return;
  const e=S.entries.find(x=>x.id===id);if(!e)return;

  const isLocked=(e.statut==="en_cours"||e.statut==="termine");
  const isTermine=e.statut==="termine";
  const statLabel=isTermine?"Terminé":e.statut==="en_cours"?"En cours":"";
  const statColor=isTermine?"var(--danger)":"var(--accent)";

  const fieldsHtml=dossierFields(e.numero_of||e.reference||"",e.client||"",e.ref_produit||"",e.laize||"",e.date_livraison||"",e.commentaire||"",e.exigences_production||"",e.format_l||"",e.format_h||"",e.duree_heures,e.statut,true,e.a_placer??1,e.fsc_requis||0,e.fsc_type_requis||"",e.departement_livraison||"",e.prise_rdv||0,e.date_livraison_imposee||0,e.valide??0,e.etiquettes_par_carton??null);

  // Bouton déstockage compact en en-tête
  const destockDone=e.destockage==="done";
  const destockBg=destockDone?"rgba(56,189,248,.12)":"rgba(251,146,60,.10)";
  const destockBorder=destockDone?"#38bdf8":"#fb923c";
  const destockColor=destockDone?"#38bdf8":"#fb923c";
  const destockIcon=destockDone?`<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`:`<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/></svg>`;
  const reelNonDefault=hasSaisieReelle() && e.statut_reel && e.statut_reel!=="reellement_en_attente";
  const resetBlock=(hasSaisieReelle() && IS_DIR_OR_SUPER && reelNonDefault)?`<button type="button" class="btn-reset-saisie" data-eid="${id}" onclick="resetSaisieFromModal(${id})" style="margin-top:8px;width:100%;padding:7px;border-radius:6px;border:1px solid rgba(248,113,113,.4);background:rgba(248,113,113,.08);color:var(--danger);font-size:11px;cursor:pointer;font-family:inherit;display:flex;align-items:center;justify-content:center;gap:6px">${icon('repeat',12)} Réinitialiser la saisie réelle</button>`:"";
  const statsBtn=isTermine?`<button type="button" onclick="openDossierStatsModal(${id})" title="Statistiques de production"
    style="display:flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:6px;border:1.5px solid var(--border2);background:var(--accent-bg);color:var(--accent);cursor:pointer;transition:opacity .15s;font-family:inherit;flex-shrink:0"
    onmouseenter="this.style.opacity='.75'" onmouseleave="this.style.opacity='1'">${icon('bar-chart-2',16)}</button>`:"";
  const refFsc=(e.reference||e.numero_of||"").trim();
  const refFscEnc=encodeURIComponent(refFsc);
  const fscBtn=(e.fsc_requis===1||e.fsc_requis===true)
    ?`<button type="button" onclick="closeM();openFscRapport(decodeURIComponent('${escAttr(refFscEnc)}'))"
      style="display:flex;align-items:center;gap:6px;padding:6px 12px;border-radius:6px;
             border:1.5px solid var(--accent);background:var(--accent-bg);color:var(--accent);
             font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;white-space:nowrap"
      onmouseenter="this.style.opacity='.75'" onmouseleave="this.style.opacity='1'">
      Rapport FSC
    </button>`
    :"";
  const ofEyeBtn=`<button type="button"
    onclick="openOfPreview(${id})"
    title="Voir l'OF relié à ce dossier"
    style="display:flex;align-items:center;justify-content:center;width:36px;height:36px;
           border-radius:6px;border:1.5px solid var(--border2);background:var(--card);
           color:var(--muted);cursor:pointer;transition:all .15s;font-family:inherit;flex-shrink:0"
    onmouseenter="this.style.borderColor='var(--accent)';this.style.color='var(--accent)'"
    onmouseleave="this.style.borderColor='var(--border2)';this.style.color='var(--muted)'">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
      <circle cx="12" cy="12" r="3"/>
    </svg>
  </button>`;
  const headerAction=`<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">${fscBtn}${statsBtn}${ofEyeBtn}<button type="button" id="destock-btn-${id}" onclick="toggleDestockage(${id})"
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
    delBtn,
    true,
    "md--dossier"
  );
}

async function submitEditDuree(id){
  const dur=parseFloat(document.getElementById("f-dur").value)||0;
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

async function openOfPreview(entryId){
  const ov=document.createElement('div');
  ov.className='of-preview-overlay';
  ov.id='of-preview-overlay';
  ov.onclick=function(evt){ if(evt.target===ov) closeOfPreview(); };
  document.body.appendChild(ov);

  ov.innerHTML=`<div class="of-preview-modal">
    <div class="of-preview-header">
      <span class="of-preview-title">Ordre de fabrication</span>
      <button onclick="closeOfPreview()" style="background:none;border:none;color:var(--muted);
        cursor:pointer;font-size:20px;line-height:1;font-family:inherit">×</button>
    </div>
    <div style="display:flex;align-items:center;justify-content:center;padding:48px;color:var(--muted);font-size:13px">
      Chargement…
    </div>
  </div>`;

  let data;
  try{
    const r=await fetch('/api/of/planning/'+entryId,{credentials:'include'});
    data=await r.json();
  }catch(e){
    ov.querySelector('.of-preview-modal').innerHTML+=
      `<div style="padding:24px;color:var(--danger);font-size:13px">Erreur de chargement.</div>`;
    return;
  }

  // ── Stocker l'état pour le multi-OF (sous-onglets, picker, etc.)
  window._ofPlanningState = {
    entryId: entryId,
    ofs: Array.isArray(data.ofs) ? data.ofs.slice() : [],
    activeOfId: null,
    pickerOpen: false,
    pickerSearch: '',
    pickerResults: [],
    pickerLoading: false,
    fiche_id: data.fiche_id || null,
    ref_produit: data.ref_produit || null,
    entry_numero_of: data.entry_numero_of || null,
  };
  if(window._ofPlanningState.ofs.length > 0){
    window._ofPlanningState.activeOfId = window._ofPlanningState.ofs[0].id;
  }

  // ── Contenu de l'onglet OF (multi-OF) ─────────────────────────────
  const ofTabContent = renderPlanningOfPaneInner();

  // ── Contenu de l'onglet Fiche technique ──────────────────────────
  const ficheId = data.fiche_id || null;
  const refProduit = data.ref_produit || null;

  let ficheTabContent;
  if(ficheId){
    ficheTabContent=`<iframe class="of-preview-iframe" src="/api/fiches-techniques/${ficheId}/pdf-preview"></iframe>`;
  }else{
    const msgFiche = refProduit
      ? `Aucune fiche technique trouvée pour la référence <strong style="color:var(--text)">${escHtml(refProduit)}</strong>.`
      : `Aucune référence produit renseignée sur ce dossier.`;
    ficheTabContent=`<div class="of-empty-state">
      <div class="of-empty-state-icon">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
          <line x1="3" y1="9" x2="21" y2="9"/>
          <line x1="9" y1="21" x2="9" y2="9"/>
        </svg>
      </div>
      <div class="of-empty-state-msg">${msgFiche}</div>
    </div>`;
  }

  // ── Titres header (titre OF = OF actif courant) ─────────────────
  const titleOf    = computePlanningOfTitle();
  const titleFiche = refProduit ? `Fiche technique — ${escHtml(refProduit)}` : 'Fiche technique';

  // ── Bouton téléchargement PDF de l'OF actif ─────────────────────
  const dlBtn = computePlanningOfDlBtn();

  // ── Barre d'onglets (masquée si pas de ref_produit) ───────────────
  const showTabs = !!refProduit;
  // Stocker les titres dans une variable globale pour éviter tout pb d'échappement dans onclick
  window._ofPreviewTitles = {of: titleOf, fiche: titleFiche};
  const tabsBar = showTabs
    ? `<div class="of-tabs-bar">
        <button class="of-tab-btn active" id="of-tab-btn-of"
          onclick="switchOfPreviewTab('of')">OF</button>
        <button class="of-tab-btn" id="of-tab-btn-fiche"
          onclick="switchOfPreviewTab('fiche')">Fiche technique</button>
      </div>`
    : '';

  ov.innerHTML=`<div class="of-preview-modal" style="max-height:92vh">
    <div class="of-preview-header">
      <span class="of-preview-title" id="of-preview-title-txt">${titleOf}</span>
      <div class="of-preview-actions">
        <span id="of-dl-btn-wrap">${dlBtn}</span>
        <button onclick="closeOfPreview()" style="background:none;border:none;color:var(--muted);
          cursor:pointer;font-size:22px;line-height:1;font-family:inherit;padding:0 4px">×</button>
      </div>
    </div>
    ${tabsBar}
    <div class="of-tab-pane" id="of-tab-pane-of">${ofTabContent}</div>
    <div class="of-tab-pane hidden" id="of-tab-pane-fiche">${ficheTabContent}</div>
  </div>`;
}

function switchOfPreviewTab(tab){
  const paneOf    = document.getElementById('of-tab-pane-of');
  const paneFiche = document.getElementById('of-tab-pane-fiche');
  const btnOf     = document.getElementById('of-tab-btn-of');
  const btnFiche  = document.getElementById('of-tab-btn-fiche');
  const titleEl   = document.getElementById('of-preview-title-txt');
  const dlWrap    = document.getElementById('of-dl-btn-wrap');
  const titles    = window._ofPreviewTitles || {};
  if(!paneOf||!paneFiche) return;
  if(tab==='of'){
    paneOf.classList.remove('hidden');
    paneFiche.classList.add('hidden');
    btnOf&&btnOf.classList.add('active');
    btnFiche&&btnFiche.classList.remove('active');
    if(titleEl) titleEl.innerHTML=titles.of||'Ordre de fabrication';
    if(dlWrap) dlWrap.style.display='';
  }else{
    paneOf.classList.add('hidden');
    paneFiche.classList.remove('hidden');
    btnOf&&btnOf.classList.remove('active');
    btnFiche&&btnFiche.classList.add('active');
    if(titleEl) titleEl.innerHTML=titles.fiche||'Fiche technique';
    if(dlWrap) dlWrap.style.display='none';
  }
}

function closeOfPreview(){
  const ov=document.getElementById('of-preview-overlay');
  if(ov) ov.remove();
  window._ofPlanningState = null;
}

function _ofPlanningActiveOf(){
  const st = window._ofPlanningState; if(!st) return null;
  const id = st.activeOfId;
  return (st.ofs || []).find(o => o.id === id) || null;
}

function computePlanningOfTitle(){
  const st = window._ofPlanningState;
  if(!st) return 'Ordre de fabrication';
  const a = _ofPlanningActiveOf();
  if(a){
    const num = escHtml(a.of_numero || '—');
    const ref = a.reference ? ' — '+escHtml(a.reference) : '';
    return `OF ${num}${ref}`;
  }
  const exp = st.entry_numero_of ? escHtml(st.entry_numero_of) : '—';
  return `OF ${exp}`;
}

function computePlanningOfDlBtn(){
  const a = _ofPlanningActiveOf();
  if(!a || !a.pdf_filename) return '';
  return `<a href="/api/of/${a.id}/pdf" target="_blank" download
          style="display:flex;align-items:center;gap:6px;padding:6px 14px;border-radius:8px;
                 border:1.5px solid var(--accent);background:var(--accent-bg);color:var(--accent);
                 font-size:12px;font-weight:700;text-decoration:none;white-space:nowrap">
         <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
              stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
           <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
           <polyline points="7 10 12 15 17 10"/>
           <line x1="12" y1="15" x2="12" y2="3"/>
         </svg>
         Télécharger
       </a>`;
}

function renderPlanningOfPaneInner(){
  const st = window._ofPlanningState;
  if(!st) return '';
  const isAdmin = (typeof IS_OF_ADMIN !== 'undefined' && IS_OF_ADMIN);
  const ofs = st.ofs || [];

  // Si pas d'OF du tout : empty state avec boutons admin
  if(ofs.length === 0){
    const importBtn = isAdmin
      ?`<button type="button" onclick="openOfImportFromPlanning(${st.entryId})"
           style="display:flex;align-items:center;gap:8px;padding:9px 18px;border-radius:8px;
                  border:1.5px solid var(--accent);background:var(--accent-bg);color:var(--accent);
                  font-size:13px;font-weight:700;cursor:pointer;font-family:inherit">
           <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
             <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
             <polyline points="17 8 12 3 7 8"/>
             <line x1="12" y1="3" x2="12" y2="15"/>
           </svg>
           Importer un OF PDF
         </button>`
      :'';
    const searchBtn = isAdmin
      ?`<button type="button" onclick="togglePlanningOfPicker()"
           style="display:flex;align-items:center;gap:8px;padding:9px 18px;border-radius:8px;
                  border:1.5px solid var(--border);background:var(--bg);color:var(--text);
                  font-size:13px;font-weight:700;cursor:pointer;font-family:inherit">
           Chercher un OF existant
         </button>`
      :'';
    const pickerHtml = st.pickerOpen ? renderPlanningOfPickerHtml() : '';
    return `<div class="of-empty-state">
      <div class="of-empty-state-icon">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
          <line x1="9" y1="13" x2="15" y2="13"/>
        </svg>
      </div>
      <div class="of-empty-state-msg">
        Aucun OF relié à ce dossier de production.<br>
        <span style="font-size:12px;color:var(--muted)">
          Le numéro d'OF attendu est
          <strong style="color:var(--text)">${escHtml(st.entry_numero_of||'non renseigné')}</strong>.
        </span>
      </div>
      <div style="display:flex;gap:10px;flex-wrap:wrap;justify-content:center">${importBtn}${searchBtn}</div>
      ${pickerHtml}
    </div>`;
  }

  // Au moins 1 OF : barre de sous-onglets + iframe + (admin) picker
  const subTabs = ofs.map(o => {
    const isActive = (o.id === st.activeOfId);
    const closeBtn = isAdmin
      ? `<span onclick="event.stopPropagation();removeOfFromCurrentPlanning(${o.id})"
             style="margin-left:6px;padding:1px 5px;border-radius:50%;color:var(--muted);cursor:pointer;font-size:13px;line-height:1"
             onmouseenter="this.style.background='var(--danger)';this.style.color='#fff'"
             onmouseleave="this.style.background='';this.style.color='var(--muted)'"
             title="Retirer cet OF du dossier">×</span>`
      : '';
    return `<button type="button" onclick="switchPlanningOfSubtab(${o.id})"
        style="display:inline-flex;align-items:center;padding:6px 12px;border-radius:8px;
               border:1px solid var(--border);background:${isActive?'var(--accent-bg)':'var(--bg)'};
               color:${isActive?'var(--accent)':'var(--text2)'};
               font-size:12px;font-weight:${isActive?'700':'600'};cursor:pointer;font-family:inherit;white-space:nowrap">
        ${escHtml(o.of_numero||'OF #'+o.id)}${closeBtn}</button>`;
  }).join('');

  const addBtn = isAdmin
    ? `<button type="button" onclick="togglePlanningOfPicker()"
          style="display:inline-flex;align-items:center;gap:4px;padding:6px 12px;border-radius:8px;
                 border:1px dashed var(--accent);background:transparent;color:var(--accent);
                 font-size:12px;font-weight:700;cursor:pointer;font-family:inherit;white-space:nowrap">
         ${st.pickerOpen ? 'Fermer' : '+ OF'}
       </button>`
    : '';

  const activeOf = _ofPlanningActiveOf();
  const iframeHtml = activeOf
    ? `<iframe class="of-preview-iframe" src="/api/of/${activeOf.id}/pdf-preview"></iframe>`
    : '<div style="padding:24px;color:var(--muted);text-align:center">Sélectionne un OF</div>';

  const pickerHtml = st.pickerOpen ? renderPlanningOfPickerHtml() : '';

  return `<div style="display:flex;flex-direction:column;height:100%">
    <div style="display:flex;gap:6px;padding:8px 12px;border-bottom:1px solid var(--border);
                background:var(--card);flex-wrap:wrap;align-items:center">
      ${subTabs}${addBtn}
    </div>
    ${pickerHtml}
    <div style="flex:1;min-height:0">${iframeHtml}</div>
  </div>`;
}

function renderPlanningOfPickerHtml(){
  const st = window._ofPlanningState;
  if(!st) return '';
  const results = st.pickerResults || [];
  let resultsHtml;
  if(st.pickerLoading){
    resultsHtml = '<div style="padding:12px;text-align:center;color:var(--muted);font-size:13px">Recherche…</div>';
  }else if(results.length === 0){
    resultsHtml = '<div style="padding:12px;text-align:center;color:var(--muted);font-size:13px">Aucun résultat</div>';
  }else{
    const linkedIds = new Set((st.ofs||[]).map(o => o.id));
    resultsHtml = results.map(c => {
      const already = linkedIds.has(c.id);
      const dateImp = (c.date_import||'').slice(0,10) || '—';
      const disabledAttr = already ? 'disabled' : '';
      const opacityStyle = already ? 'opacity:.5;cursor:not-allowed' : 'cursor:pointer';
      const labelSuffix = already ? ' <em style="color:var(--muted);font-style:normal">(déjà lié)</em>' : '';
      return `<label style="display:flex;align-items:center;gap:10px;padding:6px 8px;border:1px solid var(--border);
               border-radius:6px;margin-bottom:4px;background:var(--bg);${opacityStyle}">
        <input type="checkbox" data-of-picker="1" value="${c.id}" ${disabledAttr}
               style="margin:0;flex-shrink:0">
        <div style="flex:1;min-width:0">
          <div style="font-weight:600;color:var(--text);font-size:12px">${escHtml(c.of_numero||'—')}${labelSuffix}</div>
          <div style="font-size:11px;color:var(--muted);margin-top:1px">
            Réf : ${escHtml(c.reference||'—')}${c.machine?' · '+escHtml(c.machine):''} · importé ${dateImp}
          </div>
        </div>
      </label>`;
    }).join('');
  }
  return `<div style="padding:10px 14px;border-bottom:1px solid var(--border);background:var(--bg)">
    <div style="display:flex;gap:8px;align-items:center;margin-bottom:8px">
      <input id="planning-of-picker-search" type="text" value="${escAttr(st.pickerSearch||'')}"
        placeholder="Rechercher par OF n°, référence, machine…"
        oninput="onPlanningOfPickerSearchInput(this.value)"
        style="flex:1;background:var(--card);border:1px solid var(--border);border-radius:6px;
               padding:7px 10px;color:var(--text);font-size:12px;font-family:inherit;outline:none">
      <button type="button" onclick="submitAttachOfsToPlanning()"
        style="padding:7px 14px;border-radius:6px;border:none;background:var(--accent);color:#fff;
               cursor:pointer;font-size:12px;font-weight:700">Attacher</button>
    </div>
    <div style="max-height:200px;overflow-y:auto">${resultsHtml}</div>
  </div>`;
}

function _rerenderPlanningOfPane(){
  const pane = document.getElementById('of-tab-pane-of');
  if(pane) pane.innerHTML = renderPlanningOfPaneInner();
  const titleEl = document.getElementById('of-preview-title-txt');
  if(titleEl) titleEl.innerHTML = computePlanningOfTitle();
  const dlWrap = document.getElementById('of-dl-btn-wrap');
  if(dlWrap) dlWrap.innerHTML = computePlanningOfDlBtn();
}

function switchPlanningOfSubtab(ofId){
  const st = window._ofPlanningState; if(!st) return;
  st.activeOfId = ofId;
  _rerenderPlanningOfPane();
}

function togglePlanningOfPicker(){
  const st = window._ofPlanningState; if(!st) return;
  st.pickerOpen = !st.pickerOpen;
  if(st.pickerOpen && (st.pickerResults||[]).length === 0){
    searchOfsForPlanningPicker('');
    return;
  }
  _rerenderPlanningOfPane();
}

let _planningOfPickerDeb = null;
function onPlanningOfPickerSearchInput(value){
  const st = window._ofPlanningState; if(!st) return;
  st.pickerSearch = value;
  clearTimeout(_planningOfPickerDeb);
  _planningOfPickerDeb = setTimeout(() => searchOfsForPlanningPicker(value), 200);
}

async function searchOfsForPlanningPicker(term){
  const st = window._ofPlanningState; if(!st) return;
  st.pickerLoading = true; _rerenderPlanningOfPane();
  try{
    const q = encodeURIComponent(term||'');
    const r = await fetch('/api/of/search?limit=20'+(q?'&q='+q:''), {credentials:'include'});
    const data = await r.json();
    st.pickerResults = Array.isArray(data && data.items) ? data.items : [];
  }catch(e){
    st.pickerResults = [];
  }
  st.pickerLoading = false; _rerenderPlanningOfPane();
  // Restore focus + caret
  requestAnimationFrame(() => {
    const el = document.getElementById('planning-of-picker-search');
    if(el){ try{ el.focus(); el.setSelectionRange(el.value.length, el.value.length); }catch(e){} }
  });
}

async function submitAttachOfsToPlanning(){
  const st = window._ofPlanningState; if(!st) return;
  const boxes = document.querySelectorAll('[data-of-picker="1"]:checked');
  const ofIds = Array.from(boxes).map(b => parseInt(b.value, 10)).filter(x => !isNaN(x));
  if(!ofIds.length){ alert('Coche au moins un OF.'); return; }
  try{
    const r = await fetch('/api/admin/planning-of-links', {
      method: 'POST',
      credentials: 'include',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({planning_id: st.entryId, of_ids: ofIds}),
    });
    if(!r.ok){ const j = await r.json().catch(()=>({})); throw new Error(j.detail||'Erreur'); }
    // Re-fetch data complète pour avoir la nouvelle liste
    await refreshPlanningOfData();
  }catch(e){
    alert((e && e.message) || 'Erreur enregistrement');
  }
}

async function removeOfFromCurrentPlanning(ofId){
  const st = window._ofPlanningState; if(!st) return;
  if(!confirm('Retirer cet OF du dossier ?')) return;
  try{
    const r = await fetch('/api/admin/planning-of-links', {
      method: 'DELETE',
      credentials: 'include',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({planning_id: st.entryId, of_id: ofId}),
    });
    if(!r.ok){ const j = await r.json().catch(()=>({})); throw new Error(j.detail||'Erreur'); }
    await refreshPlanningOfData();
  }catch(e){
    alert((e && e.message) || 'Erreur enregistrement');
  }
}

async function refreshPlanningOfData(){
  const st = window._ofPlanningState; if(!st) return;
  try{
    const r = await fetch('/api/of/planning/' + st.entryId, {credentials:'include'});
    const data = await r.json();
    st.ofs = Array.isArray(data.ofs) ? data.ofs.slice() : [];
    st.fiche_id = data.fiche_id || null;
    // Si l'OF actif n'est plus dans la liste, prendre le premier
    const stillExists = st.ofs.some(o => o.id === st.activeOfId);
    if(!stillExists){
      st.activeOfId = st.ofs.length > 0 ? st.ofs[0].id : null;
    }
    st.pickerOpen = false;
    st.pickerSearch = '';
    st.pickerResults = [];
    _rerenderPlanningOfPane();
    // Refresh aussi le badge si la fonction existe
    try{ if(typeof loadPendingOfCount === 'function') loadPendingOfCount(); }catch(e){}
  }catch(e){}
}

let _ofPlanningFile=null, _ofPlanningParsed=null, _ofPlanningEntryId=null;

async function openOfImportFromPlanning(entryId){
  _ofPlanningFile=null; _ofPlanningParsed=null; _ofPlanningEntryId=entryId;
  closeOfPreview();

  const ov=document.createElement('div');
  ov.className='of-preview-overlay';
  ov.id='of-planning-import-overlay';
  ov.innerHTML=`<div class="of-preview-modal" style="max-width:560px">
    <div class="of-preview-header">
      <span class="of-preview-title">Importer un OF</span>
      <button onclick="closeOfPlanningImport()" style="background:none;border:none;
        color:var(--muted);cursor:pointer;font-size:22px;line-height:1;font-family:inherit">×</button>
    </div>
    <div style="padding:24px">
      <div id="of-pl-dropzone"
           style="border:2px dashed var(--border);border-radius:12px;padding:36px 20px;
                  text-align:center;cursor:pointer;transition:all .15s"
           onclick="document.getElementById('of-pl-file').click()"
           ondragover="event.preventDefault();this.style.borderColor='var(--accent)';this.style.background='var(--accent-bg)'"
           ondragleave="this.style.borderColor='var(--border)';this.style.background=''"
           ondrop="ofPlanningHandleDrop(event)">
        <div style="font-size:14px;font-weight:700;color:var(--text);margin-bottom:6px">
          Déposer le PDF de l'OF ici
        </div>
        <div style="font-size:12px;color:var(--muted)">ou cliquer pour parcourir</div>
        <input type="file" id="of-pl-file" accept=".pdf" style="display:none"
               onchange="ofPlanningHandleFile(this.files[0])">
      </div>
      <div id="of-pl-status" style="margin-top:12px;font-size:12px;color:var(--muted);text-align:center"></div>
    </div>
  </div>`;
  document.body.appendChild(ov);
}

function closeOfPlanningImport(){
  const ov=document.getElementById('of-planning-import-overlay');
  if(ov) ov.remove();
}

function ofPlanningHandleDrop(evt){
  evt.preventDefault();
  const dz=document.getElementById('of-pl-dropzone');
  if(dz){ dz.style.borderColor='var(--border)'; dz.style.background=''; }
  const f=evt.dataTransfer?.files?.[0];
  if(f && f.name.toLowerCase().endsWith('.pdf')) ofPlanningHandleFile(f);
  else showToast('Fichier PDF requis.','danger');
}

async function ofPlanningHandleFile(file){
  if(!file) return;
  _ofPlanningFile=file;
  const st=document.getElementById('of-pl-status');
  if(st) st.textContent='Analyse du PDF en cours…';

  const fd=new FormData();
  fd.append('file',file);
  let parsed;
  try{
    const r=await fetch('/api/of/parse',{method:'POST',credentials:'include',body:fd});
    if(!r.ok){ const j=await r.json(); throw new Error(j.detail||'Erreur parsing'); }
    parsed=await r.json();
  }catch(e){
    if(st) st.textContent='';
    showToast(e.message||'Erreur lecture PDF.','danger');
    return;
  }

  let entryNoOf='';
  try{
    const re=await fetch('/api/of/planning/'+_ofPlanningEntryId,{credentials:'include'});
    const de=await re.json();
    entryNoOf=(de.entry_numero_of||'').trim();
  }catch(e){}

  const pdfNoOf=(parsed.of_numero||'').trim();

  // Stocker dès maintenant pour que 'C'est correct' puisse enchaîner directement
  _ofPlanningParsed=parsed;

  if(entryNoOf && pdfNoOf && entryNoOf.toLowerCase()!==pdfNoOf.toLowerCase()){
    const ov2=document.createElement('div');
    ov2.className='of-preview-overlay';
    ov2.id='of-mismatch-overlay';
    ov2.innerHTML=`<div class="of-mismatch-modal">
      <div style="font-size:15px;font-weight:700;color:var(--warn)">
        ⚠ Numéros d'OF différents
      </div>
      <div style="font-size:13px;color:var(--text2);line-height:1.6">
        Le PDF importé correspond à l'OF
        <strong style="color:var(--warn)">${escHtml(pdfNoOf||'inconnu')}</strong>,
        mais ce dossier est associé à l'OF
        <strong style="color:var(--text)">${escHtml(entryNoOf)}</strong>.
        <br><br>
        Si c'est volontaire (correction de référence, OF reliquat, etc.) tu peux continuer.
        Sinon, annule et vérifie le fichier.
      </div>
      <div style="display:flex;justify-content:flex-end;gap:10px">
        <button onclick="(function(){const o=document.getElementById('of-mismatch-overlay');if(o)o.remove();closeOfPlanningImport();})()"
          style="padding:9px 20px;border-radius:8px;border:1.5px solid var(--border);
                 background:transparent;color:var(--text);font-size:13px;font-weight:600;
                 cursor:pointer;font-family:inherit">
          Annuler
        </button>
        <button onclick="(function(){const o=document.getElementById('of-mismatch-overlay');if(o)o.remove();ofPlanningShowValidationForm();})()"
          style="padding:9px 20px;border-radius:8px;border:none;background:var(--accent);
                 color:#000;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit">
          C'est correct
        </button>
      </div>
    </div>`;
    document.body.appendChild(ov2);
    return;
  }

  ofPlanningShowValidationForm();
}

function ofPlanningShowValidationForm(){
  const p=_ofPlanningParsed||{};
  const OF_FIELD_LABELS={
    of_numero:'OF n°', date_creation:'Date création', delai_client:'Délai client',
    reference:'Référence', machine:'Machine', laize:'Laize (mm)',
    format:'Format', matiere:'Matière', qte_etiquettes:'Qté étiquettes',
    qte_bobines:'Qté bobines', metrage:'Métrage',
    conditionnement:'Conditionnement', nb_mandrins:'Nb mandrins',
  };
  const rows=Object.entries(OF_FIELD_LABELS).map(([k,lbl])=>{
    const val=p[k]!=null?String(p[k]):'';
    const missing=!val;
    return `<tr style="${missing?'background:rgba(251,191,36,.06)':''}">
      <td style="padding:7px 10px;font-size:11px;font-weight:700;color:var(--muted);
                 text-transform:uppercase;letter-spacing:.4px;width:40%">${escHtml(lbl)}</td>
      <td style="padding:7px 10px">
        <input id="of-pl-field-${k}" value="${escAttr(val)}" data-key="${k}"
               style="width:100%;padding:7px 10px;border:1px solid ${missing?'var(--warn)':'var(--border)'};
                      border-radius:8px;background:var(--bg);color:var(--text);font-size:13px;
                      font-family:inherit;box-sizing:border-box">
      </td>
    </tr>`;
  }).join('');

  const ov=document.getElementById('of-planning-import-overlay');
  if(!ov) return;
  ov.querySelector('.of-preview-modal').innerHTML=`
    <div class="of-preview-header">
      <span class="of-preview-title">Vérifier et valider l'OF</span>
      <button onclick="closeOfPlanningImport()" style="background:none;border:none;
        color:var(--muted);cursor:pointer;font-size:22px;line-height:1;font-family:inherit">×</button>
    </div>
    <div style="flex:1;overflow-y:auto;padding:0 24px">
      <table style="width:100%;border-collapse:collapse;margin:12px 0">${rows}</table>
    </div>
    <div style="padding:16px 24px;border-top:1px solid var(--border);display:flex;
                justify-content:flex-end;gap:10px">
      <button onclick="closeOfPlanningImport()"
        style="padding:9px 18px;border-radius:8px;border:1.5px solid var(--border);
               background:transparent;color:var(--text);font-size:13px;font-weight:600;
               cursor:pointer;font-family:inherit">
        Annuler
      </button>
      <button onclick="ofPlanningSubmitImport()"
        style="padding:9px 20px;border-radius:8px;border:none;background:var(--accent);
               color:#000;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit">
        Valider l'import
      </button>
    </div>`;
}

async function ofPlanningSubmitImport(){
  if(!_ofPlanningFile || !_ofPlanningParsed) return;
  const data={..._ofPlanningParsed};
  document.querySelectorAll('[id^="of-pl-field-"]').forEach(inp=>{
    data[inp.dataset.key]=inp.value.trim()||null;
  });

  const fd=new FormData();
  fd.append('file',_ofPlanningFile);
  fd.append('data',JSON.stringify(data));
  try{
    const r=await fetch('/api/of/validate',{method:'POST',credentials:'include',body:fd});
    if(!r.ok){ const j=await r.json(); throw new Error(j.detail||'Erreur import'); }
    closeOfPlanningImport();
    showToast('OF importé et relié au dossier.','success');
  }catch(e){
    showToast(e.message||'Erreur lors de l\'import.','danger');
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
    dossierFields("","","","","","","","","",8,"attente",false),
    "Insérer",`submitInsert(${afterId})`
  ,"","",false,"md--dossier");
}
async function submitInsert(afterId){
  const d=getFormData(false);
  if(!d.numero_of){ showToast("Numéro d'OF requis.","danger"); return; }
  try{
    await api(`/machines/${MID}/insert-after/${afterId}`,{method:"POST",body:JSON.stringify({reference:d.numero_of,...d})});
    closeM();load();
    showToast("Dossier inséré.","success");
  }catch(e){
    showToast(apiErrorMessage(e,"Insertion impossible."),"danger");
  }
}

function fMin(m){
  if(m==null||m===""||isNaN(m)) return "—";
  const n=Number(m);
  const hh=Math.floor(n/60),mm=Math.round(n%60);
  return hh>0?hh+"h "+String(mm).padStart(2,"0")+"min":mm+"min";
}
function fN(n){
  if(n==null||n===""||isNaN(n)) return "0";
  const x=Number(n);
  return x>=1e6?x.toLocaleString("fr-FR"):String(Math.round(x*10)/10);
}
function dsCatCls(cat){
  const c=String(cat||"").toLowerCase();
  if(c==="calage") return "ds-cat-calage";
  if(c==="production") return "ds-cat-production";
  if(c==="arret") return "ds-cat-arret";
  return "";
}
function renderDossierStatsBody(d){
  if(!d) return '<div class="ds-empty">Chargement…</div>';
  const tt=d.temps_totaux||{};
  const q=d.quantites||{};
  const prodInclArrets=Number(tt.production_min||0)+Number(tt.arret_min||0);
  if(!d.nb_saisies){
    return '<div class="ds-empty">Aucune saisie de production trouvée pour ce dossier sur cette machine.</div>';
  }
  let html=`<div class="ds-stats">
    <div class="ds-stat"><div class="ds-stat-lbl">Durée totale</div><div class="ds-stat-val">${fMin(tt.duree_totale_min)}</div></div>
    <div class="ds-stat"><div class="ds-stat-lbl">Saisies</div><div class="ds-stat-val">${fN(d.nb_saisies)}</div></div>
    <div class="ds-stat"><div class="ds-stat-lbl">Étiquettes</div><div class="ds-stat-val">${fN(q.etiquettes)}</div></div>
    <div class="ds-stat"><div class="ds-stat-lbl">Métrage</div><div class="ds-stat-val">${fN(q.metrage_m)} m</div></div>
    <div class="ds-stat"><div class="ds-stat-lbl">Vitesse</div><div class="ds-stat-val">${Number(d.vitesse_m_min||0).toFixed(2)} m/min</div></div>
  </div>`;
  html+=`<div class="ds-section">${icon("clock",13)} Temps</div>
  <div class="ds-time-kpi">
    <div class="ds-time-card"><div class="ds-tc-lbl">${icon("wrench",12)} Calage</div><div class="ds-tc-val">${fMin(tt.calage_min)}</div></div>
    <div class="ds-time-card"><div class="ds-tc-lbl">${icon("play",12)} Production</div><div class="ds-tc-val">${fMin(prodInclArrets)}</div></div>
    <div class="ds-time-card"><div class="ds-tc-lbl">${icon("alert-triangle",12)} Arrêts</div><div class="ds-tc-val">${fMin(tt.arret_min)}</div></div>
  </div>`;
  const cats=d.by_category||[];
  if(cats.length){
    html+=`<div class="ds-section">${icon("layers",13)} Répartition par catégorie</div>
    <div class="ds-tbl-wrap"><table class="ds-tbl"><thead><tr><th>Catégorie</th><th>Durée</th></tr></thead><tbody>`;
    cats.forEach(c=>{
      if(!c.minutes) return;
      html+=`<tr><td class="${dsCatCls(c.category)}">${escHtml(c.label||c.category)}</td><td>${fMin(c.minutes)}</td></tr>`;
    });
    html+=`</tbody></table></div>`;
  }
  const ops=d.by_operation||[];
  if(ops.length){
    html+=`<div class="ds-section">${icon("bar-chart-2",13)} Répartition par code opération</div>
    <div class="ds-tbl-wrap"><table class="ds-tbl"><thead><tr><th>Code</th><th>Opération</th><th>Cat.</th><th>Saisies</th><th>Durée</th></tr></thead><tbody>`;
    ops.forEach(r=>{
      html+=`<tr>
        <td style="font-weight:700;color:var(--text)">${escHtml(r.code)}</td>
        <td>${escHtml(r.label||"")}</td>
        <td class="${dsCatCls(r.category)}">${escHtml(r.category||"")}</td>
        <td>${fN(r.count)}</td>
        <td>${fMin(r.minutes)}</td>
      </tr>`;
    });
    html+=`</tbody></table></div>`;
  }
  const ops2=d.operateurs||[];
  if(ops2.length){
    html+=`<div class="ds-section">${icon("users",13)} Opérateurs</div>
    <div class="ds-tbl-wrap"><table class="ds-tbl"><thead><tr><th>Opérateur</th><th>Saisies</th><th>Calage</th><th>Prod</th><th>Arrêts</th><th>Total</th></tr></thead><tbody>`;
    ops2.forEach(r=>{
      html+=`<tr>
        <td style="font-weight:600;color:var(--text)">${escHtml(r.operateur||"?")}</td>
        <td>${fN(r.nb_saisies)}</td>
        <td>${fMin(r.calage_min)}</td>
        <td>${fMin(r.prod_min)}</td>
        <td>${fMin(r.arret_min)}</td>
        <td>${fMin(r.minutes)}</td>
      </tr>`;
    });
    html+=`</tbody></table></div>`;
  }
  return html;
}
async function openDossierStatsModal(entryId){
  const e=S.entries.find(x=>x.id===entryId);
  const ref=(e&&(e.numero_of||e.reference))||"Dossier";
  document.getElementById("mroot").innerHTML=`<div class="mo" onclick="if(event.target===this)closeM()"><div class="md md--stats">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;gap:12px">
      <h3 style="margin:0;font-size:18px;font-family:var(--mono);color:var(--text);display:flex;align-items:center;gap:8px">${icon("bar-chart-2",18)} ${escHtml(ref)}</h3>
      <button type="button" class="btn-s" onclick="closeM()">Fermer</button>
    </div>
    <div id="ds-body"><div class="ds-empty">Chargement des statistiques…</div></div>
  </div></div>`;
  try{
    const d=await api(`/machines/${MID}/entries/${entryId}/production-stats`);
    const el=document.getElementById("ds-body");
    if(el) el.innerHTML=renderDossierStatsBody(d);
  }catch(err){
    const el=document.getElementById("ds-body");
    const msg=err&&err.message?err.message:"Erreur lors du chargement";
    if(el) el.innerHTML=`<div class="ds-empty">${escHtml(msg)}</div>`;
  }
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
  const rows=S.entries.map(e=>{
    const base={
    "Client":       e.client||"",
    "Format":       e.format_l&&e.format_h?`${e.format_l}×${e.format_h} mm`:"",
    "Réf OF":       e.numero_of||e.reference||"",
    "Réf produit":  e.ref_produit||"",
    "Laize":        e.laize!=null?e.laize:"",
    "Livraison":    e.date_livraison||"",
    "Commentaire":  e.commentaire||"",
    "Exigences prod.": e.exigences_production||"",
    "Durée (h)":    e.duree_heures||0,
    "Statut":       statLabel(e.statut),
    "Déstockage":   e.destockage==="done"?"Oui":"Non",
    };
    if(hasSaisieReelle()) base["Saisie réelle"]=reelLabel(e.statut_reel);
    return base;
  });
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
  const sp=new URLSearchParams();
  sp.set("machine",String(id));
  appendPlanningVueParam(sp);
  location.href="/planning?"+sp.toString();
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
  const wh=getWhForDate(di,dateObj,ds,true);
  const s=wh.s,e=wh.e;
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


// ── Commentaires timeline (semaine / jour) ──
function commentModalDeleteBtn(onDeleteFn,hasExisting){
  if(!hasExisting||!onDeleteFn) return "";
  return `<button type="button" class="gear-btn cmt-del-btn" onclick="${onDeleteFn}" title="Supprimer le commentaire" aria-label="Supprimer le commentaire">${icon("trash-2",15)}</button>`;
}
function openWeekCommentModal(sk,monTs){
  const mon=monTs?new Date(monTs):getMon(new Date());
  const wn=wkNum(mon);
  const existing=((S.weekComments||{})[sk]||"").trim();
  const readOnly=!CAN_EDIT;
  const footerLeft=readOnly?"":commentModalDeleteBtn(`deleteWeekComment('${escAttr(sk)}')`,!!existing);
  document.getElementById("mroot").innerHTML=modalHTML(
    `Commentaire — Semaine S${wn}`,
    `<p style="font-size:12px;color:var(--muted);margin:-8px 0 12px">Note visible sur la timeline pour toute la semaine S${wn}.</p>
    <div class="fd"><label>Commentaire</label><textarea id="f-wk-cmt" rows="4" placeholder="Ex : maintenance prévue, priorité client…" style="width:100%;padding:10px 12px;border:1px solid var(--border2);border-radius:10px;background:var(--bg);color:var(--text);font-size:13px;font-family:inherit;resize:vertical;outline:none"${readOnly?" readonly":""}>${escHtml(existing)}</textarea></div>`,
    readOnly?"Fermer":"Enregistrer",
    readOnly?"closeM()":`submitWeekComment('${escAttr(sk)}')`,
    "",
    footerLeft
  );
}
async function deleteWeekComment(sk){
  if(!CAN_EDIT) return;
  if(!confirm("Supprimer le commentaire de cette semaine ?")) return;
  try{
    await api(`/machines/${MID}/week-comment`,{method:"PUT",body:JSON.stringify({semaine:sk,comment:""})});
    const m={...(S.weekComments||{})};
    delete m[sk];
    S.weekComments=m;
    closeM();
    renderTL();
  }catch(err){
    let msg="Suppression impossible.";
    try{const j=await err.json();if(j&&j.detail)msg=typeof j.detail==="string"?j.detail:JSON.stringify(j.detail);}catch(x){}
    alert(msg);
  }
}
async function submitWeekComment(sk){
  if(!CAN_EDIT) return;
  const comment=(document.getElementById("f-wk-cmt")?.value||"").trim();
  try{
    await api(`/machines/${MID}/week-comment`,{method:"PUT",body:JSON.stringify({semaine:sk,comment})});
    if(comment) S.weekComments={...(S.weekComments||{}),[sk]:comment};
    else{const m={...(S.weekComments||{})};delete m[sk];S.weekComments=m;}
    closeM();renderTL();
  }catch(err){
    let msg="Enregistrement impossible.";
    try{const j=await err.json();if(j&&j.detail)msg=typeof j.detail==="string"?j.detail:JSON.stringify(j.detail);}catch(x){}
    alert(msg);
  }
}
function openDayCommentModal(ds,di){
  const dn={1:"Lundi",2:"Mardi",3:"Mercredi",4:"Jeudi",5:"Vendredi",6:"Samedi"}[di]||"Jour";
  const dateLabel=ds?new Date(ds+"T12:00:00").toLocaleDateString("fr-FR",{weekday:"long",day:"numeric",month:"long",year:"numeric"}):dn;
  const existing=((S.dayComments||{})[ds]||"").trim();
  const readOnly=!CAN_EDIT;
  const footerLeft=readOnly?"":commentModalDeleteBtn(`deleteDayComment('${escAttr(ds)}')`,!!existing);
  document.getElementById("mroot").innerHTML=modalHTML(
    `Commentaire — ${dateLabel}`,
    `<p style="font-size:12px;color:var(--muted);margin:-8px 0 12px">Note du jour affichée sur la timeline.</p>
    <div class="fd"><label>Commentaire</label><textarea id="f-day-cmt" rows="4" placeholder="Ex : réunion matin, manque matière…" style="width:100%;padding:10px 12px;border:1px solid var(--border2);border-radius:10px;background:var(--bg);color:var(--text);font-size:13px;font-family:inherit;resize:vertical;outline:none"${readOnly?" readonly":""}>${escHtml(existing)}</textarea></div>`,
    readOnly?"Fermer":"Enregistrer",
    readOnly?"closeM()":`submitDayComment('${escAttr(ds)}')`,
    "",
    footerLeft
  );
}
async function deleteDayComment(ds){
  if(!CAN_EDIT) return;
  if(!confirm("Supprimer le commentaire de ce jour ?")) return;
  try{
    await api(`/machines/${MID}/day-comment`,{method:"PUT",body:JSON.stringify({date:ds,comment:""})});
    const m={...(S.dayComments||{})};
    delete m[ds];
    S.dayComments=m;
    closeM();
    renderTL();
  }catch(err){
    let msg="Suppression impossible.";
    try{const j=await err.json();if(j&&j.detail)msg=typeof j.detail==="string"?j.detail:JSON.stringify(j.detail);}catch(x){}
    alert(msg);
  }
}
async function submitDayComment(ds){
  if(!CAN_EDIT) return;
  const comment=(document.getElementById("f-day-cmt")?.value||"").trim();
  try{
    await api(`/machines/${MID}/day-comment`,{method:"PUT",body:JSON.stringify({date:ds,comment})});
    if(comment) S.dayComments={...(S.dayComments||{}),[ds]:comment};
    else{const m={...(S.dayComments||{})};delete m[ds];S.dayComments=m;}
    closeM();renderTL();
  }catch(err){
    let msg="Enregistrement impossible.";
    try{const j=await err.json();if(j&&j.detail)msg=typeof j.detail==="string"?j.detail:JSON.stringify(j.detail);}catch(x){}
    alert(msg);
  }
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
    const worked=!isPlanningDayOff(di,ds);
    const wh=getWhForDate(di,d,ds,true);
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
        await api(`/machines/${MID}/day-work`,{method:"PUT",body:JSON.stringify({date:op.ds,is_worked:op.worked?1:0})});
      }
      if(op.worked&&op.st&&op.en){
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
      Horaires de production enregistrés en base pour cette machine. Ils déterminent la largeur des jours sur la timeline (semaines paires / impaires pour Cohésio 2).
    </p>
    <div class="fd-row" style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
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
async function resetDefaults(){
  const mk=machineKey();
  const d=DEFAULTS_BY_KEY[mk]||DEFAULTS_BY_KEY["C1"];
  saveMachineDefaults(d);
  try{
    if(MID){
      await api(`/machines/${MID}/horaires-parity`,{method:"PUT",body:JSON.stringify(d)});
      if(mk!=="C2"){
        const p=d.pair||d.impair||null;
        const week=p&&p.week?p.week:null;
        const fri=p&&p.fri?p.fri:null;
        const hs=(week&&isFinite(week.s))?week.s:null, he=(week&&isFinite(week.e))?week.e:null;
        const fs=(fri&&isFinite(fri.s))?fri.s:hs, fe=(fri&&isFinite(fri.e))?fri.e:he;
        function hmPair(a,b){
          if(a==null||b==null) return null;
          return timeInputFromFloat(a)+","+timeInputFromFloat(b);
        }
        const payload={
          horaires_lundi:hmPair(hs,he),
          horaires_mardi:hmPair(hs,he),
          horaires_mercredi:hmPair(hs,he),
          horaires_jeudi:hmPair(hs,he),
          horaires_vendredi:hmPair(fs,fe),
        };
        Object.keys(payload).forEach(k=>{ if(!payload[k]) delete payload[k]; });
        if(Object.keys(payload).length){
          await api(`/machines/${MID}/horaires-bulk`,{method:"PUT",body:JSON.stringify(payload)});
        }
      }
    }
  }catch(e){
    console.error(e);
    alert("Enregistrement des horaires impossible.");
  }
  closeM();
  await load();
}
async function submitDefaults(){
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
  try{
    const mk=machineKey();
    if(MID){
      await api(`/machines/${MID}/horaires-parity`,{method:"PUT",body:JSON.stringify(nd)});
      if(mk!=="C2"){
        const p=nd.pair||nd.impair||null;
        const week=p&&p.week?p.week:null;
        const fri=p&&p.fri?p.fri:null;
        const hs=(week&&isFinite(week.s))?week.s:null, he=(week&&isFinite(week.e))?week.e:null;
        const fs=(fri&&isFinite(fri.s))?fri.s:hs, fe=(fri&&isFinite(fri.e))?fri.e:he;
        function hmPair(a,b){
          if(a==null||b==null) return null;
          return timeInputFromFloat(a)+","+timeInputFromFloat(b);
        }
        const payload={
          horaires_lundi:hmPair(hs,he),
          horaires_mardi:hmPair(hs,he),
          horaires_mercredi:hmPair(hs,he),
          horaires_jeudi:hmPair(hs,he),
          horaires_vendredi:hmPair(fs,fe),
        };
        Object.keys(payload).forEach(k=>{ if(!payload[k]) delete payload[k]; });
        if(Object.keys(payload).length){
          await api(`/machines/${MID}/horaires-bulk`,{method:"PUT",body:JSON.stringify(payload)});
        }
      }
    }
  }catch(e){
    console.error(e);
    alert("Enregistrement des horaires impossible.");
  }
  closeM();
  await load();
}

async function boot(){
  document.body.classList.add("has-topbar");
  try{ render(); }catch(e){}
  let r;
  try{r=await fetch("/api/auth/me",{credentials:"include"});}catch(e){location.href="/";return;}
  if(!r.ok){location.href="/";return;}
  ME=await r.json();
  if(ME&&ME.id){
    window.__MYSIFA_UID__=ME.id;
    window.__MYSIFA_NOM__=ME.nom||"";
    window.__MYSIFA_ROLE__=ME.role||"";
    window.__MYSIFA_USER__={nom:ME.nom||"",role:ME.role||""};
    if(window._CW&&typeof window._CW.ensureReady==="function")await window._CW.ensureReady();
    else if(window._CW&&typeof window._CW.syncUser==="function")window._CW.syncUser();
    if(window.MySifaDock&&typeof window.MySifaDock.bootPageWidgets==="function")window.MySifaDock.bootPageWidgets();
    else if(window.MySifaDock&&typeof window.MySifaDock.layout==="function")window.MySifaDock.layout();
  }
  if(window.MySifaTheme)MySifaTheme.mergeFromUser(ME);
  // Badge 'Mappings OF à valider' pour admin/direction/superadmin
  try{ loadPendingOfCount(); }catch(e){}
  try{
    const list=await api(`/machines`);
    const byName=new Map((list||[]).map(m=>[String(m.nom||""),m]));
    const ordered=[];
    MACHINE_ORDER.forEach(n=>{if(byName.has(n))ordered.push(byName.get(n));});
    (list||[]).forEach(m=>{if(!ordered.find(x=>x.id===m.id))ordered.push(m);});
    S.machines=ordered;

    const sp=new URLSearchParams(location.search||"");
    S.planningVue=parsePlanningVueParam();
    const raw=sp.get("machine");
    // Pré-remplissage recherche depuis URL (navigation cross-machine).
    const qParam=sp.get("q");
    const tlqParam=sp.get("tlq");
    if(typeof qParam==="string" && qParam.trim()) S.searchQuery=qParam;
    if(typeof tlqParam==="string" && tlqParam.trim()) S.tlSearchQuery=tlqParam;
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
  // Si on arrive via un chip cross-machine, naviguer directement vers le 1er match.
  try{
    const sp=new URLSearchParams(location.search||"");
    if(sp.get("auto")==="1" && (S.tlSearchQuery||"").trim()){
      setTimeout(()=>{try{computeAllTlMatches();if(_allTlMatches&&_allTlMatches.length) tlNavTo(0);}catch(e){}},220);
    }
    // Toujours recalculer les chips après le 1er load.
    scheduleCrossMachineSearch();
  }catch(e){}
  // Vérifier les annonces de mise à jour après le chargement initial
  checkUpdates();
  // Actualise le dossier actif + allonge le slot en_cours toutes les 30 s
  setInterval(async()=>{
    if(!MID) return;
    // Ne pas interrompre une saisie (ajout/édition) en cours dans une modale.
    // Le refresh provoque un re-render et peut faire perdre la saisie.
    try{
      const mr=document.getElementById("mroot");
      const modalOpen=!!(mr && mr.firstElementChild);
      const ae=document.activeElement;
      const inModal=!!(ae && mr && mr.contains(ae));
      const typing=!!(ae && (ae.tagName==="INPUT"||ae.tagName==="TEXTAREA"||ae.tagName==="SELECT") && ae.isConnected);
      if(modalOpen && (inModal || typing)) return;
    }catch(e){}
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

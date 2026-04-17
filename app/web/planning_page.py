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
.contact-close{position:absolute;top:14px;right:14px;width:32px;height:32px;border-radius:10px;border:1px solid var(--border);
  background:var(--bg);color:var(--muted);cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:18px;line-height:1}
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
.tl-bar{position:relative;height:56px;background:var(--bg-dark);border-radius:8px;
  border:1px solid var(--border);overflow:visible}
.d-bg{position:absolute;top:0;bottom:0;z-index:1;pointer-events:none}
.d-bg.a0{background:rgba(148,163,184,.02)}
.d-bg.a1{background:rgba(148,163,184,.16)}
body.light .d-bg.a0{background:rgba(2,6,23,.015)}
body.light .d-bg.a1{background:rgba(2,6,23,.085)}
.d-sep{position:absolute;top:0;bottom:0;width:2px;background:rgba(148,163,184,.45);z-index:2;pointer-events:none}
body.light .d-sep{background:rgba(71,85,105,.35)}
.d-sep::after{content:'';position:absolute;top:0;bottom:0;left:-6px;width:14px;background:linear-gradient(90deg,rgba(34,211,238,0),rgba(34,211,238,.08),rgba(34,211,238,0));opacity:.35}
.slot{position:absolute;top:6px;bottom:6px;border-radius:6px;display:flex;align-items:center;
  justify-content:center;cursor:pointer;transition:all .15s;overflow:hidden;padding:2px 4px}
.slot:hover{top:4px;bottom:4px;z-index:20}
.slot-inner{display:flex;flex-direction:column;align-items:center;justify-content:center;line-height:1.15;
  text-align:center;max-width:100%;pointer-events:none}
.slot .line1{font-size:11px;color:#fff;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%}
.slot .line2{font-size:9px;font-weight:500;color:rgba(255,255,255,.88);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%}
body.light .slot .line1{color:#0f172a}body.light .slot .line2{color:#334155}
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
.lg-d{width:10px;height:10px;border-radius:3px}.lg-i span{font-family:var(--mono)}

.th{display:grid;grid-template-columns:22px 22px 14px minmax(96px,1.2fr) minmax(64px,.75fr) minmax(72px,.7fr) minmax(64px,.75fr) minmax(64px,.75fr) minmax(44px,.45fr) minmax(72px,.65fr) 40px minmax(110px,1.0fr) 74px;
  gap:6px;padding:10px 10px;background:var(--bg-dark);border-radius:10px 10px 0 0;
  font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;font-weight:600;font-family:var(--mono);align-items:center}
.th>span{min-width:0}
.th .act-c{text-align:right}
#tbody{
  /* Plus haut pour afficher ~10 dossiers visibles */
  max-height:min(820px, calc(100vh - 260px));
  overflow:auto;
  border-radius:0 0 10px 10px;
  scroll-behavior:auto;
  overscroll-behavior:contain;
}
.tr{display:grid;grid-template-columns:22px 22px 14px minmax(96px,1.2fr) minmax(64px,.75fr) minmax(72px,.7fr) minmax(64px,.75fr) minmax(64px,.75fr) minmax(44px,.45fr) minmax(72px,.65fr) 40px minmax(110px,1.0fr) 74px;
  gap:6px;padding:10px 10px;border-bottom:1px solid var(--border);font-size:12px;align-items:center;
  cursor:grab;transition:background .2s;background:var(--bg-dark)}
.tr:first-child{background:var(--accent-bg)}
.tr.dov{background:var(--accent-bg);opacity:.95}.tr.dra{opacity:.5}
.tr.drop-before{box-shadow:0 -3px 0 0 var(--accent) inset}
.tr.drop-after{box-shadow:0 3px 0 0 var(--accent) inset}
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
.acts{display:flex;gap:6px;justify-content:flex-end;flex-wrap:wrap;align-items:center}
.acts .ab{flex:0 0 auto}
.ab{padding:4px 8px;background:transparent;border:1px solid var(--border2);color:var(--text2);
  cursor:pointer;font-size:11px;border-radius:6px;font-family:var(--mono)}
.ab:hover{background:var(--accent-bg);color:var(--accent)}
.ab.del{color:var(--red)}.ab.del:hover{background:rgba(248,113,113,.12)}
.ab.mov{width:28px;display:none;align-items:center;justify-content:center;padding:4px 0}
.ab.mov{display:none}
@media (max-width:900px){
  .ab.mov{display:inline-flex}
}
.ab:disabled{opacity:.45;cursor:not-allowed}
.ab:disabled:hover{background:transparent;color:var(--text2);border-color:var(--border2)}

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
.md-acts{display:flex;gap:12px;justify-content:flex-end;margin-top:28px}
.btn-s{padding:10px 24px;background:transparent;color:var(--dim);border:1px solid var(--border2);
  border-radius:8px;cursor:pointer;font-size:14px;font-family:var(--mono)}
.empty{text-align:center;padding:48px;color:var(--muted);font-size:14px;width:100%}

@keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}
@keyframes tipIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
@keyframes slideIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
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
  .tl-bar{height:52px}
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
const CC=["#2563eb","#7c3aed","#059669","#d97706","#dc2626","#0891b2","#4f46e5","#65a30d","#c026d3","#ea580c"];
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
let S={machine:null,machines:[],entries:[],timeline:[],wo:0,loading:true,holidays:{},dayWorked:{},view:localStorage.getItem("mysifa.planning.view")||"2w",
  contactOpen:false,contactSubject:"",contactMessage:"",contactSending:false};
let ME=null;
let CAN_EDIT=false;
let SHOW_DOSSIERS=false;
let _autoScrollKey=null;
let _suppressAutoScroll=false;

const api=(p,o={})=>fetch(`/api/planning${p}`,{credentials:"include",headers:{"Content-Type":"application/json",...(o.headers||{})},...o}).then(r=>{if(!r.ok)throw r;return r.json()});

async function load(){
  if(!MID){
    console.warn("Planning: aucune machine sélectionnée (MID=0)");
    S.loading=false;
    render();
    return;
  }
  S.loading=true;render();
  try{
    const showDossiers = !!(ME && isAdmin(ME));
    // Important: la timeline persiste planned_start/planned_end en DB.
    // Pour que les statuts calculés (en_cours/termine) soient à jour après un reorder,
    // on charge d'abord la timeline, puis la liste des entrées (admin uniquement).
    const [m, tl] = await Promise.all([api(`/machines/${MID}`), api(`/machines/${MID}/timeline`)]);
    S.machine = m;
    S.timeline = (tl && tl.slots) ? tl.slots : [];
    if(showDossiers){
      const en = await api(`/machines/${MID}/entries`);
      S.entries = en || [];
    }else{
      S.entries = [];
    }
    await Promise.all([loadHolidays(),loadDayWorked()]);
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
  const n=(id*2654435761)>>>0;
  return CC[n%CC.length];
}

const pad=n=>String(n).padStart(2,"0");
function ymdate(d){return d.getFullYear()+"-"+pad(d.getMonth()+1)+"-"+pad(d.getDate());}
const ymd=ymdate;
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
function getWhForDate(di,dateObj){
  // Priorité: horaires "hebdo" stockés en base pour cette machine (si non vides)
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
    tlBlocks+=`<div ${wi<nw-1?'style="margin-bottom:16px"':""}>
      <div class="wk-lbl ${lblCls}">S${wn} — ${fd(mn)} au ${fd(addD(mn,4))}</div>
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
        </div>
      </div>
      <div style="font-size:11px;color:var(--muted);margin:-8px 0 12px">Samedi non travaillé par défaut — décochez pour l'activer.</div>
      ${tlBlocks}
      <div class="legend">${sl.slice(0,8).map(s=>{const co=colorForId(s.entry_id||0);const lb=escAttr(s.client||s.numero_of||s.reference||"—");return`<div class="lg-i"><div class="lg-d" style="background:${co}"></div><span>${lb}</span></div>`;}).join("")}</div>
    </section>
    ${SHOW_DOSSIERS?`<section class="sec">
      <div class="sec-hdr">
        <div class="sec-title">Dossiers de production</div>
        ${CAN_EDIT?`<button type="button" class="btn-p" onclick="openAdd()"><span style="font-size:18px;line-height:1">+</span> Ajouter</button>`:""}
      </div>
      <div class="th"><span></span><span>#</span><span></span><span>Client</span><span>Format prod.</span><span>Dos. RVGI</span><span>Ref OF</span><span>Ref prod.</span><span>Laize</span><span>Livraison</span><span>Durée</span><span>Statut</span><span class="act-c">Actions</span></div>
      <div id="tbody">${S.entries.length===0?'<div class="empty">Aucun dossier au planning</div>':""}
        ${S.entries.map((e,i)=>mkRow(e,i,sl)).join("")}
      </div>
    </section>`:""}
  ${renderContactModal()}</div></main></div><div id="mroot"></div>`;
  setupDD();
  setupStatutSelects();
  if(SHOW_DOSSIERS)autoScrollDossiersIfNeeded();
}

function autoScrollDossiersIfNeeded(){
  try{
    if(_suppressAutoScroll) return;
    const ent = S.entries || [];
    if(!ent.length) return;
    const main = document.querySelector(".main");
    const tbody = document.getElementById("tbody");
    if(!main || !tbody) return;

    const key = String(MID||"") + "|" + ent.map(e=>String(e.id||"")+"-"+String(e.statut||"")).join(",");
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

function mkTL(mon,slots){
  const we=addD(mon,7),HF=.42,days=[];
  for(let i=0;i<7;i++){
    const d=addD(mon,i),di=d.getDay();
    if(di===0)continue;
    const ds=ymd(d);
    const isSat=di===6;
    const w=getWhForDate(di,d);
    if(!w)continue;
    const off=isSat?!S.dayWorked[ds]:!!S.holidays[ds];
    const dayT=off?0:(w.e-w.s);
    const hourLbl=off?"—":fmtWindow(w.s,w.e);
    const nonTravail=isSat?!S.dayWorked[ds]:!!S.holidays[ds];
    days.push({date:d,di,ds,s:w.s,e:w.e,tWork:dayT,flex:off?HF:dayT,off,hourLbl,nonTravail,isSat});
  }
  if(!days.length)return'<div style="color:var(--dim);padding:8px;font-size:13px">Aucun jour ouvré</div>';
  const tot=days.reduce((s,d)=>s+d.tWork,0);
  if(tot<=0)return'<div style="color:var(--muted);padding:8px;font-size:13px">Aucun créneau calculable (semaine entièrement non travaillée ou fermée).</div>';
  let c=0;
  const cols=days.filter(d=>d.tWork>0).map(d=>{const cs=c;c+=d.tWork;return{...d,cs,ce:c}});
  const now=new Date(),ts=now.toDateString();
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
  const ws=slots.filter(s=>{const ss=new Date(s.start),se=new Date(s.end);return ss<we&&se>mon});

  let h=`<div class="tl-wrap" data-mon="${mon.getTime()}"><div class="dh">`;
  days.forEach(d=>{
    const td=d.date.toDateString()===ts,sa=d.di===6;
    const off=d.off;
    h+=`<div class="dh-cell ${td?"today":""} ${sa?"sat":""}" style="flex:${d.flex};opacity:${off?0.45:1}">
      <div style="display:flex;flex-direction:column;align-items:center;gap:2px">
        <div>${DN[d.di]} ${fd(d.date)}</div>
        ${d.off?`<small>${d.hourLbl}</small>`:(CAN_EDIT?`<button type="button" class="dh-hours-btn" onclick="openHorairesModal(${d.di})">${escAttr(d.hourLbl)}</button>`:`<small>${escAttr(d.hourLbl)}</small>`)}
        <label style="display:flex;align-items:center;gap:6px;font-size:10px;opacity:.85;cursor:pointer;white-space:nowrap">
          <input type="checkbox" ${d.nonTravail?"checked":""} ${CAN_EDIT?"":"disabled"} onchange="setDayNonTravail('${d.ds}',${d.isSat},this.checked)"> non travaillé
        </label>
      </div>
    </div>`;
  });
  h+=`</div><div class="tl-bar">`;
  cols.forEach((col,i)=>{
    const l=(col.cs/tot)*100, w=((col.ce-col.cs)/tot)*100;
    h+=`<div class="d-bg ${(i%2)===0?'a0':'a1'}" style="left:${l}%;width:${w}%"></div>`;
  });
  cols.slice(1).forEach(col=>{h+=`<div class="d-sep" style="left:${(col.cs/tot)*100}%"></div>`;});

  ws.forEach((s,idx)=>{
    const ss=new Date(s.start),se=new Date(s.end);
    const cs=ss<mon?mon:ss,ce=se>we?we:se;
    const sp=gp(cs),ep=gp(ce),l=(sp/tot)*100,w=Math.max(.5,((ep-sp)/tot)*100);
    const co=colorForId(s.entry_id||idx+1);
    const fm=s.format_l&&s.format_h?`${s.format_l} × ${s.format_h} mm`:"—";
    const st=s.statut==="en_cours"?"En cours":"En attente";
    const cli=(s.client||"").trim()||(s.numero_of||s.reference||"—");
    const subTxt=fm!=="—"?fm:"";
    const meta=[s.numero_of||s.reference,s.description].filter(Boolean).join(" · ");
    h+=`<div class="slot" style="left:${l}%;width:${w}%;background:${co}cc;border:1px solid ${co};box-shadow:0 2px 12px ${co}33"
      onmouseenter="showTip(event,this)" onmousemove="moveTip(event)" onmouseleave="hideTip()"
      data-ref="${escAttr(cli)}" data-lbl="${escAttr(meta)}" data-fmt="${escAttr(fm)}" data-dur="${escAttr(String(s.duree_heures)+"h")}"
      data-deb="${escAttr(fdt(ss))}" data-fin="${escAttr(fdt(se))}" data-st="${escAttr(st)}" data-co="${escAttr(co)}">
      ${w>5?`<div class="slot-inner"><span class="line1">${escAttr(cli)}</span>${subTxt?`<span class="line2">${escAttr(subTxt)}</span>`:""}</div>`:""}</div>`;
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
  const rvgi=escAttr(e.dos_rvgi||"")||"—";
  const of=escAttr(e.numero_of||e.reference||"—");
  const rfp=escAttr(e.ref_produit||"")||"—";
  const lz=e.laize!=null&&e.laize!==""?escAttr(String(e.laize)):"—";
  const statutCell=(isLocked||!CAN_EDIT)
    ? `<span class="st ${sc}">${sc==="run"?'<span style="width:6px;height:6px;border-radius:50%;background:var(--green);animation:pulse 2s infinite;display:inline-block"></span>':""}${sl} 🔒</span>`
    : `<select class="statut-select" data-eid="${e.id}">
         <option value="attente" ${e.statut==="attente"?"selected":""}>Attente</option>
         <option value="en_cours" ${e.statut==="en_cours"?"selected":""}>En cours</option>
         <option value="termine" ${e.statut==="termine"?"selected":""}>Terminé</option>
       </select>`;
  return`<div class="tr" draggable="true" data-eid="${e.id}" data-idx="${i}" ${isAnchor?'data-scroll-anchor="1"':''}
    data-statut="${escAttr(e.statut||'attente')}"
    style="animation:slideIn .3s ease ${i*.03}s both;${i===0?`border-left:3px solid ${co}`:"border-left:3px solid transparent"};${isLocked?"cursor:not-allowed;opacity:.9":""}">
    <span class="dh-handle">⠿</span>
    <span class="cell-mini">${i+1}</span>
    <div><div class="cd" style="background:${co}"></div></div>
    <span class="lbl-main">${escAttr(cli)}</span>
    <span class="cell-mini">${escAttr(fm)}${fm!=="—"?" mm":""}</span>
    <span class="cell-mini">${rvgi}</span>
    <span class="cell-mini">${of}</span>
    <span class="cell-mini">${rfp}</span>
    <span class="cell-mini">${lz}</span>
    <span class="cell-mini">${escAttr(fmtDl(e.date_livraison||""))}</span>
    <span class="cell-mini">${e.duree_heures}h</span>
    ${statutCell}
    <div class="acts">
      ${CAN_EDIT?`
      <button type="button" class="ab mov" onclick="moveEntry(${e.id},-1)" title="Monter" ${i<=0||isLocked?"disabled":""}>▲</button>
      <button type="button" class="ab mov" onclick="moveEntry(${e.id},+1)" title="Descendre" ${i>=S.entries.length-1||isLocked?"disabled":""}>▼</button>
      <button type="button" class="ab" onclick="openInsert(${e.id})" title="${nextLocked?"⦸ Impossible : dossier En cours / Terminé juste après":"Insérer après"}" ${isLocked||nextLocked?"disabled":""}>${nextLocked?"⦸":"↳+"}</button>
      <button type="button" class="ab" onclick="splitEntry(${e.id})" title="Spliter en 2">½</button>
      <button type="button" class="ab" onclick="openEdit(${e.id})" title="Modifier">${icon('edit',14)}</button>
      ${(e.statut==="en_cours")?`<button type="button" class="ab del" onclick="if(confirm('Supprimer ce dossier en cours ? Le suivant passera automatiquement en cours.'))delEntry(${e.id})" title="Supprimer (en cours)">✕</button>`:`<button type="button" class="ab del" onclick="if(confirm('Supprimer ?'))delEntry(${e.id})" title="Supprimer" ${e.statut==="termine"?"disabled":""}>✕</button>`}`:""}
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
    }));
  }
}

// ── Tooltip ──
let tipEl=null;
function showTip(ev,el){hideTip();const d=el.dataset;tipEl=document.createElement("div");tipEl.className="tip";
  tipEl.style.borderColor=(d.co||"#888")+"55";
  const sub=d.lbl?`<div class="tip-lbl">${d.lbl}</div>`:"";
  tipEl.innerHTML=`<div class="tip-hdr"><div class="tip-bar" style="background:${d.co||"#888"}"></div><div><div class="tip-ref">${d.ref||"—"}</div>${sub}</div></div>
    <div class="tip-grid"><span class="k">Format</span><span class="v">${d.fmt||"—"}</span><span class="k">Durée</span><span class="v">${d.dur||""}</span>
    <span class="k">Début</span><span class="v">${d.deb||""}</span><span class="k">Fin</span><span class="v">${d.fin||""}</span>
    <span class="k">Statut</span><span class="v" style="color:${d.st==="En cours"?"var(--green)":"var(--amber)"};font-weight:600">${d.st||""}</span></div>`;
  el.closest(".tl-wrap").appendChild(tipEl);moveTip(ev)}
function moveTip(ev){if(!tipEl)return;const c=tipEl.parentElement.getBoundingClientRect();
  let x=ev.clientX-c.left+12,y=ev.clientY-c.top-tipEl.offsetHeight-12;
  if(x+tipEl.offsetWidth>c.width)x=c.width-tipEl.offsetWidth-8;if(x<0)x=8;if(y<0)y=ev.clientY-c.top+20;
  tipEl.style.left=x+"px";tipEl.style.top=y+"px"}
function hideTip(){if(tipEl){tipEl.remove();tipEl=null}}

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
function setupDD(){
  if(!CAN_EDIT) return;
  const rows=document.querySelectorAll(".tr[draggable]");let di=null;
  let overEl=null, overPos=null;
  function clearOver(){
    if(overEl){overEl.classList.remove("drop-before","drop-after");}
    overEl=null;overPos=null;
  }
  rows.forEach(r=>{
    const st=(r.dataset.statut||"").toLowerCase();
    const locked=(st==="en_cours"||st==="termine");
    if(locked){
      r.removeAttribute("draggable");
      return;
    }
    r.addEventListener("dragstart",e=>{di=+r.dataset.idx;r.classList.add("dra");e.dataTransfer.effectAllowed="move"});
    r.addEventListener("dragover",e=>{
      e.preventDefault();
      r.classList.add("dov");
      const rect=r.getBoundingClientRect();
      const before = (e.clientY - rect.top) < rect.height/2;
      if(overEl!==r || overPos!==(before?"before":"after")){
        clearOver();
        overEl=r;overPos=before?"before":"after";
        r.classList.add(before?"drop-before":"drop-after");
      }
    });
    r.addEventListener("dragleave",()=>{
      r.classList.remove("dov");
      // Ne pas clearOver ici : le navigateur peut déclencher dragleave juste avant drop,
      // et on perdrait l'information "avant/après" (trait bleu).
    });
    r.addEventListener("drop", async (e)=>{
      e.preventDefault();
      r.classList.remove("dov");
      const tgt = overEl || r;
      const ti = +(tgt.dataset.idx||r.dataset.idx||"0");
      if(di===null){ clearOver(); return; }
      if(di===ti){ clearOver(); return; }
      const ids = S.entries.map(e=>e.id);
      const [m] = ids.splice(di, 1);
      let insertAt = ti;
      // Se fier EXACTEMENT au trait bleu (overPos) calculé au dragover.
      const after = (tgt===overEl && overPos==="after");
      if(after) insertAt = ti + 1;
      if(di < insertAt) insertAt -= 1;
      ids.splice(insertAt, 0, m);
      clearOver();
      const savedScroll = document.querySelector(".main")?.scrollTop ?? 0;
      _suppressAutoScroll = true;
      try{
        await api(`/machines/${MID}/reorder`,{method:"POST",body:JSON.stringify({entry_ids:ids})});
      }finally{
        await load();
        _suppressAutoScroll = false;
        requestAnimationFrame(()=>requestAnimationFrame(()=>{
          const main=document.querySelector(".main");
          if(main) main.scrollTop=savedScroll;
        }));
      }
    });
    r.addEventListener("dragend",()=>{
      r.classList.remove("dra");
      di=null;
      clearOver();
      rows.forEach(x=>x.classList.remove("dov"));
    })
  })
}

function setupStatutSelects(){
  if(!CAN_EDIT) return;
  document.querySelectorAll(".statut-select").forEach(sel=>{
    sel.addEventListener("change", async()=>{
      const eid=sel.dataset.eid;
      try{
        await api(`/machines/${MID}/entries/${eid}/statut`,{
          method:"PUT",
          body: JSON.stringify({statut: sel.value, force: true})
        });
        await load();
      }catch(e){
        alert("Erreur statut");
        await load();
      }
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

// ── Modals ──
function durBar(v){return((v-MIND)/(MAXD-MIND)*100)+"%"}

function modalHTML(title,fields,submitLabel,onSubmitFn){
  return`<div class="mo" onclick="if(event.target===this)closeM()"><div class="md"><h3>${title}</h3>
    ${fields}
    <div class="md-acts"><button class="btn-s" onclick="closeM()">Annuler</button>
    <button class="btn-p" onclick="${onSubmitFn}">${submitLabel}</button></div></div></div>`
}

function dossierFields(numero_of,dos_rvgi,client,ref_produit,laize,date_livraison,commentaire,fl,fh,dur,statut,showStatut){
  return`
    <div class="fd"><label>Numéro d'OF</label><input id="f-of" value="${numero_of}" placeholder="961/0001"></div>
    <div class="fd"><label>Dos. RVGI</label><input id="f-rvgi" value="${dos_rvgi}" placeholder="N° dossier production"></div>
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
      <input type="number" id="f-dur" min="${MIND}" max="${MAXD}" value="${dur}" oninput="document.getElementById('f-dur-fill').style.width=((Math.max(${MIND},Math.min(${MAXD},+this.value||${MIND}))-${MIND})/(${MAXD}-${MIND})*100)+'%'">
      <div class="dur-b"><div class="dur-f" id="f-dur-fill" style="width:${durBar(dur)}"></div></div>
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
    dos_rvgi:(document.getElementById("f-rvgi").value||"").trim(),
    client:document.getElementById("f-cli").value||"",
    ref_produit:document.getElementById("f-rp").value||"",
    format_l:parseFloat(document.getElementById("f-fl").value)||null,
    format_h:parseFloat(document.getElementById("f-fh").value)||null,
    laize:parseFloat(document.getElementById("f-laize").value)||null,
    date_livraison:document.getElementById("f-dl").value||"",
    commentaire:document.getElementById("f-com").value||"",
    duree_heures:Math.max(MIND,Math.min(MAXD,parseInt(document.getElementById("f-dur").value)||8)),
  };
  if(withStatut)d.statut=document.getElementById("f-stat").value;
  return d;
}

function openAdd(){
  if(!CAN_EDIT) return;
  document.getElementById("mroot").innerHTML=modalHTML(
    "Ajouter un dossier",
    dossierFields("","","","","","","","","",8,"attente",false),
    "Ajouter","submitAdd()"
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
  document.getElementById("mroot").innerHTML=modalHTML(
    `Modifier — ${(e.numero_of||e.reference)||''}`,
    dossierFields(e.numero_of||e.reference||"",e.dos_rvgi||"",e.client||"",e.ref_produit||"",e.laize||"",e.date_livraison||"",e.commentaire||"",e.format_l||"",e.format_h||"",e.duree_heures,e.statut,true),
    "Enregistrer",`submitEdit(${id})`
  );
}
async function submitEdit(id){
  const d=getFormData(true);
  if(!d.numero_of)return alert("Numéro d'OF requis");
  await api(`/machines/${MID}/entries/${id}`,{method:"PUT",body:JSON.stringify({reference:d.numero_of,...d})});
  closeM();load();
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
  );
}
async function submitInsert(afterId){
  const d=getFormData(false);
  if(!d.numero_of)return alert("Numéro d'OF requis");
  await api(`/machines/${MID}/insert-after/${afterId}`,{method:"POST",body:JSON.stringify({reference:d.numero_of,...d})});
  closeM();load();
}

function closeM(){document.getElementById("mroot").innerHTML=""}

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

function openHorairesModal(di){
  if(!CAN_EDIT) return;
  if(!S.machine)return;
  const {s,e}=getWhForDate(di,new Date());
  const dn={1:"Lundi",2:"Mardi",3:"Mercredi",4:"Jeudi",5:"Vendredi",6:"Samedi"}[di]||"Jour";
  document.getElementById("mroot").innerHTML=modalHTML(
    `Plage horaire — ${dn}`,
    `<p style="font-size:12px;color:var(--muted);margin:-8px 0 16px">Modèle hebdo pour cette machine (tous les ${dn.toLowerCase()}s).</p>
    <div class="fd"><label>Début (HH:MM)</label><input type="text" inputmode="numeric" placeholder="07:00" id="f-h-start" value="${fracToTimeInput(s)}"></div>
    <div class="fd"><label>Fin de journée (HH:MM)</label><input type="text" inputmode="numeric" placeholder="19:00" id="f-h-end" value="${fracToTimeInput(e)}"></div>`,
    "Enregistrer",
    `submitHoraires(${di})`
  );
}
async function submitHoraires(di){
  if(!CAN_EDIT) return;
  const st=(document.getElementById("f-h-start").value||"").trim();
  const en=(document.getElementById("f-h-end").value||"").trim();
  if(!st||!en)return void alert("Indiquez début et fin.");
  if(!isHHMM(st)||!isHHMM(en))return void alert("Format attendu : HH:MM (24h). Exemple : 07:00");
  try{
    await api(`/machines/${MID}/horaires`,{method:"PUT",body:JSON.stringify({day:DAY_API[di],start:st,end:en})});
    closeM();load();
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
}
boot();
</script>
</body>
</html>
"""

"""Paramètres MySifa — super administrateur uniquement."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import APP_VERSION
from services.auth_service import get_current_user, is_superadmin
from app.web.access_denied import access_denied_response
from app.web.traca_guide_js import TRACA_GUIDE_SCRIPT_BLOCK

router = APIRouter()


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/settings", status_code=302)
        raise
    if not is_superadmin(user):
        return access_denied_response(
            "Paramètres (super admin)",
            detail=(
                "Cette application est réservée au super administrateur. "
                "Merci de contacter un administrateur en cas de besoin."
            ),
        )
    return HTMLResponse(
        content=SETTINGS_HTML.replace("__V_LABEL__", f"v{APP_VERSION}").replace(
            "/*__TRACA_GUIDE__*/", TRACA_GUIDE_SCRIPT_BLOCK
        )
    )


SETTINGS_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17">
<title>Paramètres — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="stylesheet" href="/static/support_widget.css">
<link rel="stylesheet" href="/static/mysifa_theme.css">
<link rel="stylesheet" href="/static/mysifa_user_chip.css">
<style>
:root{--bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;--muted:#94a3b8;--accent:#22d3ee;--accent-fg:#0a0e17;--ok:#34d399;--warn:#fbbf24;--danger:#f87171;--danger-fg:#fff;}
body.light{--bg:#f1f5f9;--card:#fff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;--muted:#64748b;--accent:#0891b2;--accent-fg:#fff;--ok:#059669;--warn:#d97706;--danger:#dc2626;--danger-fg:#fff;}
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,-apple-system,'Segoe UI',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;}
.layout{display:flex;min-height:100vh}
.sidebar{width:220px;background:var(--card);border-right:1px solid var(--border);padding:20px 12px;display:flex;flex-direction:column;flex-shrink:0;height:100vh;position:sticky;top:0;overflow-y:auto;scrollbar-width:none}
.sidebar::-webkit-scrollbar{width:0}
.logo{font-size:15px;font-weight:800;margin-bottom:20px;padding:0 8px}.logo span{color:var(--accent)}
.logo-sub{font-size:10px;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase;margin-top:2px}
.nav-scroll{flex:1;min-height:0;overflow-y:auto;display:flex;flex-direction:column;gap:6px;margin-bottom:8px}
.nav-btn{display:flex;align-items:center;gap:10px;width:100%;text-align:left;padding:10px 12px;border-radius:8px;border:none;background:transparent;color:var(--text2);font-size:13px;font-weight:500;cursor:pointer;font-family:inherit;transition:background .15s,color .15s,box-shadow .2s;margin-bottom:2px;position:relative;z-index:1}
.nav-btn:hover,.nav-btn.active{background:rgba(34,211,238,.12);color:var(--accent)}
.nav-btn:hover:not(.active){box-shadow:inset 0 0 0 1.5px rgba(34,211,238,.45),0 0 12px rgba(34,211,238,.2)}
body.light .nav-btn:hover:not(.active){box-shadow:inset 0 0 0 1.5px rgba(8,145,178,.5),0 0 10px rgba(8,145,178,.15)}
.back-mysifa{border:none!important;background:transparent!important;font-weight:400!important;color:var(--text2)!important;padding:8px 10px!important}
.back-mysifa:hover{color:var(--text)!important;background:transparent!important}
.back-mysifa .wm{font-weight:800;color:var(--text)}.back-mysifa .wm span{color:var(--accent)}
.sidebar-bottom{margin-top:auto;display:flex;flex-direction:column;gap:6px;padding-bottom:8px}
.user-chip{padding:10px 12px;border-radius:8px;background:rgba(34,211,238,.12);cursor:pointer}
.user-chip .uc-name{font-size:12px;font-weight:600;color:var(--text)}
.user-chip .uc-role{font-size:10px;color:var(--accent);text-transform:uppercase;letter-spacing:.5px}
.theme-btn,.logout-btn{display:flex;align-items:center;gap:8px;padding:10px 12px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-size:12px;width:100%;font-family:inherit;transition:background .15s,color .15s,border-color .15s,box-shadow .2s}
.theme-btn:hover{background:rgba(34,211,238,.12);color:var(--accent);border-color:var(--accent);box-shadow:0 0 0 1px rgba(34,211,238,.22),0 0 20px rgba(34,211,238,.14)}
body.light .theme-btn:hover{box-shadow:0 0 0 1px rgba(8,145,178,.28),0 0 18px rgba(8,145,178,.12)}
.theme-btn .theme-ico{font-size:14px;line-height:1;display:inline-flex;align-items:center}
@media (display-mode:standalone),(max-width:900px){
  .theme-btn .theme-label{display:none}.theme-btn{justify-content:center}
}
.logout-btn{border:none}.logout-btn:hover{color:var(--danger);background:rgba(248,113,113,.1);box-shadow:0 0 0 1px rgba(248,113,113,.35),0 0 18px rgba(248,113,113,.12)}
.version{font-size:10px;color:var(--muted);font-family:monospace;padding:4px 12px}
.main{flex:1;padding:24px 28px;overflow:auto}
/* topbar mobile : mysifa_mobile_topbar.css */
.sidebar-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:200}
body.sb-open .sidebar-overlay{display:block}
h1{font-size:22px;margin:0 0 6px}
.sub{color:var(--muted);font-size:13px;margin-bottom:22px}
.card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:18px 20px;margin-bottom:16px}
.card h2{font-size:15px;margin:0 0 14px}
.table-wrap{overflow:auto;border-radius:10px;border:1px solid var(--border)}
table{width:100%;border-collapse:collapse;font-size:12px}
th,td{padding:8px 10px;border-bottom:1px solid var(--border);text-align:left;white-space:nowrap}
th{background:rgba(15,23,42,.35);font-weight:700;color:var(--muted);position:sticky;top:0}
body.light th{background:#f1f5f9}
td.chk{text-align:center}.dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--ok)}.dot.no{background:var(--border)}
.chk-edit{width:16px;height:16px;cursor:pointer;accent-color:var(--accent)}
.cell-ov{font-size:9px;color:var(--accent);font-weight:700;letter-spacing:.02em;margin-left:6px;text-transform:uppercase}
/* Matrice d'accès v2 (migration 184) */
.acc-matrix{width:100%;border-collapse:separate;border-spacing:0;font-size:12px}
.acc-matrix th{padding:8px 10px}.acc-matrix .acc-th-lbl{margin-right:6px}
.acc-matrix .acc-expand{background:var(--accent-bg);color:var(--accent);border:none;border-radius:6px;width:20px;height:20px;font-weight:700;font-size:14px;cursor:pointer;line-height:1}
.acc-matrix .acc-expand:hover{filter:brightness(1.15)}
.acc-matrix td.acc-cell{padding:6px 8px;vertical-align:middle}
.acc-matrix td.acc-cell.readonly{opacity:.75}
.acc-matrix .acc-lvl,.acc-matrix .rd-lvl{width:auto;min-width:130px;padding:4px 8px;font-size:11px;background:var(--bg);border:1px solid var(--border);border-radius:6px}
.acc-matrix .acc-lvl.is-ov{border-color:var(--accent);box-shadow:0 0 0 2px rgba(34,211,238,.15)}
.acc-matrix .lvl-badge{display:inline-block;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:600;border:1px solid var(--border);color:var(--text2)}
.acc-matrix .lvl-badge.lvl-admin{background:rgba(139,92,246,.15);color:#a78bfa;border-color:rgba(139,92,246,.4)}
.acc-matrix .lvl-badge.lvl-write{background:var(--accent-bg);color:var(--accent);border-color:rgba(34,211,238,.35)}
.acc-matrix .lvl-badge.lvl-read{background:rgba(34,197,94,.12);color:#4ade80;border-color:rgba(34,197,94,.3)}
.acc-matrix .lvl-badge.lvl-none{background:transparent;color:var(--muted)}
.acc-matrix .acc-sub-tr td{background:rgba(15,23,42,.25);border-top:1px dashed var(--border);padding:8px 10px}
body.light .acc-matrix .acc-sub-tr td{background:#f8fafc}
.acc-matrix .acc-sub-title{font-size:11px;font-weight:600;color:var(--accent);text-transform:uppercase;letter-spacing:.5px}
.acc-matrix td.acc-sub{padding:6px 10px}
.acc-matrix .acc-sub-row{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:3px 0;border-bottom:1px dotted rgba(148,163,184,.15)}
.acc-matrix .acc-sub-row:last-child{border-bottom:none}
.acc-matrix .acc-sub-label{font-size:11px;color:var(--text2);flex:1;min-width:120px}
.acc-matrix td.acc-sub-empty{background:transparent}
.acc-hint{padding:10px 12px;margin:0 0 14px;background:rgba(34,211,238,.08);border-left:3px solid var(--accent);border-radius:0 8px 8px 0;color:var(--text2);font-size:12px;line-height:1.55}
/* Référentiel rôles (vue transposée : apps en lignes, rôles en colonnes) */
.acc-matrix-defaults th.acc-app-col{min-width:220px;text-align:left}
.acc-matrix-defaults th.acc-role-th{min-width:130px;text-align:center;font-size:11px}
.acc-matrix-defaults th.acc-role-th span{display:inline-block}
.acc-matrix-defaults td.acc-app-cell{min-width:220px;background:rgba(15,23,42,.15);vertical-align:middle}
body.light .acc-matrix-defaults td.acc-app-cell{background:#f8fafc}
.acc-matrix-defaults td.acc-app-cell strong{font-weight:600;color:var(--text)}
.acc-matrix-defaults td.acc-sub-label-cell{padding-left:24px;font-size:11px;color:var(--text2);background:rgba(15,23,42,.08)}
body.light .acc-matrix-defaults td.acc-sub-label-cell{background:#fafbfc}
.acc-matrix-defaults tr.acc-sub-tr td.acc-sub-cell{background:rgba(15,23,42,.08)}
body.light .acc-matrix-defaults tr.acc-sub-tr td.acc-sub-cell{background:#fafbfc}
.acc-matrix-defaults .acc-cell{text-align:center;padding:6px 8px}
.acc-lock{font-size:11px;opacity:.6}
/* Table wrap horizontal scroll pour les 2 matrices */
#matrix-table,#role-legend .table-wrap{max-width:100%;overflow-x:auto}
#matrix-table table.acc-matrix,#role-legend table.acc-matrix{min-width:max-content}
.form-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;margin-bottom:12px}
input,select{width:100%;padding:10px 12px;border-radius:10px;border:1.5px solid var(--border);background:var(--bg);color:var(--text);font-size:13px;font-family:inherit}
.btn{background:var(--accent);color:var(--accent-fg);border:none;border-radius:10px;padding:10px 18px;font-weight:700;font-size:13px;cursor:pointer;font-family:inherit}
.btn:hover{filter:brightness(1.06)}
.btn-danger{background:var(--danger);color:var(--danger-fg)}
.btn-danger:hover{filter:brightness(1.08)}
.btn-ok{background:var(--ok);color:#fff}
.btn-ok:hover{filter:brightness(1.05)}
.btn-sec{background:transparent;border:1px solid var(--border);color:var(--muted);transition:box-shadow .2s,border-color .15s,color .15s,filter .15s}
.btn-sec:hover{box-shadow:0 0 0 1px rgba(34,211,238,.32),0 0 20px rgba(34,211,238,.2);border-color:rgba(34,211,238,.45);color:var(--accent)}
body.light .btn-sec:hover{box-shadow:0 0 0 1px rgba(8,145,178,.35),0 0 18px rgba(8,145,178,.15);border-color:rgba(8,145,178,.4);color:var(--accent)}
.row-user{display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border)}
.row-user:last-child{border-bottom:none}
.prof-ring{position:relative;flex-shrink:0;width:34px;height:34px;cursor:default}
.prof-ring svg{display:block;width:34px;height:34px}
.prof-ring-track{stroke:var(--border)}
.prof-ring-bar{stroke:var(--accent);stroke-linecap:round;transition:stroke-dashoffset .25s ease}
.prof-ring[data-tier="low"] .prof-ring-bar{stroke:var(--danger)}
.prof-ring[data-tier="mid"] .prof-ring-bar{stroke:var(--warn)}
.prof-ring[data-tier="high"] .prof-ring-bar{stroke:var(--ok)}
.prof-ring-label{
  position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
  font-size:9px;font-weight:800;color:var(--text);letter-spacing:-.02em;
  opacity:0;transition:opacity .15s;pointer-events:none;
}
.prof-ring:hover .prof-ring-label{opacity:1}
.op-toolbar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:14px}
.op-filter{flex:1;min-width:200px;padding:10px 14px;border-radius:10px;border:1.5px solid var(--border);background:var(--bg);color:var(--text);font-size:13px;font-family:inherit;outline:none;transition:border-color .15s,box-shadow .15s}
.op-filter:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12)}
body.light .op-filter:focus{box-shadow:0 0 0 3px rgba(8,145,178,.1)}
.maint-doc-add-btn{display:inline-flex;align-items:center;gap:8px;padding:9px 16px;background:var(--accent);color:var(--accent-fg);border:1px solid var(--accent);border-radius:8px;font-size:13px;font-weight:700;cursor:pointer;transition:filter .12s,transform .06s;font-family:inherit;user-select:none}
.maint-doc-add-btn:hover{filter:brightness(1.06)}
.maint-doc-add-btn:active{transform:translateY(1px)}
.maint-doc-add-btn:disabled{opacity:.55;cursor:not-allowed;filter:none}
.maint-doc-row{display:flex;align-items:center;gap:10px;padding:9px 12px;border:1px solid var(--border);border-radius:8px;background:var(--card)}
.maint-doc-row-info{flex:1;min-width:0}
.maint-doc-row-name{font-size:13px;font-weight:600;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block}
.maint-doc-row-meta{font-size:10px;color:var(--muted);margin-top:2px;display:block}
.maint-doc-row-link{padding:4px 10px;font-size:11px;font-weight:600;color:var(--accent);border:1px solid var(--border);border-radius:6px;text-decoration:none;transition:border-color .12s}
.maint-doc-row-link:hover{border-color:var(--accent)}
.maint-doc-row-del{padding:4px 8px;font-size:11px;color:var(--danger);border:1px solid transparent;border-radius:6px;background:transparent;cursor:pointer;font-family:inherit}
.maint-doc-row-del:hover{border-color:var(--danger);background:rgba(248,113,113,.08)}
.op-form-panel{margin-bottom:16px;padding:16px 18px;border:1px solid var(--border);border-radius:12px;background:var(--bg)}
.op-form-panel h3{margin:0 0 12px;font-size:13px;font-weight:700;color:var(--text);text-transform:uppercase;letter-spacing:.5px}
.op-table-wrap{margin-top:4px}
.op-table{font-size:12px}
.op-table th{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);padding:10px 12px;white-space:nowrap}
.op-table td{padding:10px 12px;vertical-align:middle}
.op-table tbody tr:hover td{background:rgba(34,211,238,.04)}
body.light .op-table tbody tr:hover td{background:rgba(8,145,178,.05)}
.op-table tr.op-cat-row td{
  padding:14px 12px 6px;font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.6px;
  color:var(--accent);background:rgba(34,211,238,.06);border-bottom:1px solid var(--border)
}
body.light .op-table tr.op-cat-row td{background:rgba(8,145,178,.06)}
.op-table tr.op-cat-row:first-child td{padding-top:8px}
.op-code-cell{font-family:ui-monospace,monospace;font-weight:800;font-size:13px;color:var(--accent);width:56px}
.op-lbl-cell{font-weight:600;color:var(--text);max-width:280px;white-space:normal}
.op-pill{
  display:inline-flex;align-items:center;font-size:10px;font-weight:700;padding:3px 10px;border-radius:999px;
  border:1px solid var(--border);text-transform:uppercase;letter-spacing:.3px;line-height:1.3
}
.op-pill.info{color:var(--text2);border-color:rgba(148,163,184,.4);background:rgba(148,163,184,.1)}
.op-pill.attention{color:var(--warn);border-color:rgba(251,191,36,.4);background:rgba(251,191,36,.12)}
.op-pill.critique{color:var(--danger);border-color:rgba(248,113,113,.45);background:rgba(248,113,113,.12)}
.op-pill.calage{color:var(--ok);border-color:rgba(52,211,153,.4);background:rgba(52,211,153,.1)}
.op-pill.arret{color:var(--warn);border-color:rgba(251,191,36,.4);background:rgba(251,191,36,.1)}
.op-pill.production{color:#60a5fa;border-color:rgba(96,165,250,.4);background:rgba(96,165,250,.1)}
.op-pill.changement{color:#a78bfa;border-color:rgba(167,139,250,.4);background:rgba(167,139,250,.1)}
.op-pill.nettoyage{color:#c084fc;border-color:rgba(192,132,252,.4);background:rgba(192,132,252,.1)}
.op-pill.autre{color:var(--muted);border-color:var(--border);background:rgba(148,163,184,.08)}
.op-pill.controles{color:var(--ok,#34d399);border-color:rgba(52,211,153,.4);background:rgba(52,211,153,.12)}
.op-pill.interventions{color:#a78bfa;border-color:rgba(167,139,250,.4);background:rgba(167,139,250,.12)}
.op-pill.entretien{color:#a78bfa;border-color:rgba(167,139,250,.4);background:rgba(167,139,250,.12)}
.op-pill.remplacements{color:#fb923c;border-color:rgba(251,146,60,.4);background:rgba(251,146,60,.12)}
.op-req{font-size:11px;font-weight:600;color:var(--muted)}
.fsc-kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}
@media(max-width:1000px){.fsc-kpi-grid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:520px){.fsc-kpi-grid{grid-template-columns:1fr}}
.fsc-kpi-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px 18px}
.fsc-kpi-label{font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px}
.fsc-kpi-val{font-size:28px;font-weight:800;color:var(--text);line-height:1}
.fsc-kpi-badge{display:inline-block;margin-top:8px;font-size:10px;font-weight:700;padding:3px 10px;border-radius:999px}
.fsc-kpi-badge.accent{color:var(--accent);background:rgba(34,211,238,.12)}
.fsc-kpi-badge.ok{color:var(--ok);background:rgba(52,211,153,.12)}
.fsc-kpi-badge.danger{color:var(--danger);background:rgba(248,113,113,.12)}
.fsc-kpi-badge.muted{color:var(--muted);background:rgba(148,163,184,.12)}
.fsc-claim-badge{display:inline-flex;align-items:center;font-size:10px;font-weight:700;padding:3px 10px;border-radius:6px;line-height:1.3}
.fsc-section-title{font-size:13px;font-weight:700;color:var(--text);text-transform:uppercase;letter-spacing:.5px;margin:0 0 10px}
.fsc-date-inp{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:7px 10px;color:var(--text);font-size:12px;font-family:inherit}
.fsc-date-inp:focus{border-color:var(--accent);outline:none;box-shadow:0 0 0 3px rgba(34,211,238,.12)}
.fsc-toolbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:12px;padding-bottom:10px;border-bottom:1px solid var(--border)}
.fsc-toolbar-dates{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.fsc-toolbar-dates .fsc-range-sep{color:var(--muted);font-size:12px}
.fsc-toolbar .btn-sec{font-size:12px;padding:7px 14px}
body.settings-tab-fsc .desktop-head{display:none}
body.settings-tab-menu .desktop-head{display:none}
body.settings-tab-fsc .main{padding-top:20px}
body.settings-tab-fsc .fsc-kpi-grid{margin-bottom:14px}
@media(min-width:901px){
  body.settings-tab-fsc .main{padding-top:24px}
}
tr.fsc-row-alert td{background:rgba(248,113,113,.08)}
body.light tr.fsc-row-alert td{background:rgba(220,38,38,.06)}
.op-req.yes{color:var(--ok)}
.op-req.no{color:var(--muted)}
.op-table th:last-child,.op-table td:last-child{text-align:right}
.op-act{display:inline-flex;gap:6px;justify-content:flex-end;flex-wrap:nowrap}
.btn-sm{padding:6px 12px;font-size:11px;font-weight:700;border-radius:8px}
.btn-ghost{background:transparent;border:1px solid var(--border);color:var(--text2);transition:border-color .15s,color .15s,box-shadow .15s,filter .15s}
.btn-ghost:hover{border-color:var(--accent);color:var(--accent);filter:none;box-shadow:0 0 0 1px rgba(34,211,238,.28),0 0 14px rgba(34,211,238,.14)}
body.light .btn-ghost:hover{box-shadow:0 0 0 1px rgba(8,145,178,.3),0 0 12px rgba(8,145,178,.1)}
.btn-ghost.danger:hover{border-color:var(--danger);color:var(--danger);box-shadow:0 0 0 1px rgba(248,113,113,.35),0 0 14px rgba(248,113,113,.12)}

.pill{font-size:10px;font-weight:800;padding:2px 8px;border-radius:999px;border:1px solid var(--border);display:inline-flex;align-items:center;gap:6px;line-height:1.4}
.empl-pill{display:inline-flex;align-items:center;gap:5px;padding:4px 8px 4px 10px;border-radius:8px;border:1px solid var(--border);background:var(--bg);transition:border-color .15s,background .15s}
.empl-pill:hover{border-color:var(--accent);background:rgba(34,211,238,.06)}
body.light .empl-pill:hover{background:rgba(8,145,178,.06)}
.empl-pill-code{font-family:ui-monospace,monospace;font-size:12px;font-weight:700;color:var(--text);letter-spacing:.03em}
.empl-pill-del{display:inline-flex;align-items:center;justify-content:center;width:18px;height:18px;border:none;background:transparent;color:var(--muted);cursor:pointer;border-radius:4px;padding:0;transition:color .15s,background .15s;flex-shrink:0}
.empl-pill-del:hover{color:var(--danger);background:rgba(248,113,113,.14)}
/* #empl-add-form .btn,#empl-import-btn : override retiré — .btn utilise désormais --accent-fg */
.empl-allee{flex:0 0 auto;width:fit-content;min-width:120px;background:var(--card);border:1px solid var(--border);border-radius:12px;padding:12px 14px;overflow:hidden}
.empl-allee-hd{display:flex;align-items:center;gap:10px;margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid var(--border)}
.empl-allee-letter{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:8px;background:rgba(34,211,238,.12);color:var(--accent);font-size:14px;font-weight:800;font-family:ui-monospace,monospace;flex-shrink:0}
body.light .empl-allee-letter{background:rgba(8,145,178,.12)}
.empl-allee-label{font-size:12px;font-weight:700;color:var(--text);text-transform:uppercase;letter-spacing:.5px}
.empl-allee-body{display:flex;flex-direction:column;gap:5px}
.empl-rangee{display:flex;align-items:flex-start}
.empl-rangee-pills{display:flex;flex-wrap:nowrap;gap:4px}
.pill--direction{border-color:rgba(244,114,182,.35);color:#f472b6;background:rgba(244,114,182,.12)}
.pill--administration{border-color:rgba(167,139,250,.38);color:#a78bfa;background:rgba(167,139,250,.12)}
.pill--administration_ventes{border-color:rgba(167,139,250,.38);color:#a78bfa;background:rgba(167,139,250,.12)}
.pill--administration_technique{border-color:rgba(99,102,241,.38);color:#818cf8;background:rgba(99,102,241,.12)}
.pill--fabrication{border-color:rgba(52,211,153,.35);color:var(--ok);background:rgba(52,211,153,.12)}
.pill--logistique{border-color:rgba(96,165,250,.35);color:#60a5fa;background:rgba(96,165,250,.12)}
.pill--comptabilite{border-color:rgba(251,191,36,.38);color:#fbbf24;background:rgba(251,191,36,.12)}
.pill--expedition{border-color:rgba(249,115,22,.38);color:#fb923c;background:rgba(249,115,22,.12)}
.pill--commercial{border-color:rgba(202,138,4,.38);color:#eab308;background:rgba(202,138,4,.12)}
.pill--encadrement_atelier{border-color:rgba(20,184,166,.38);color:#2dd4bf;background:rgba(20,184,166,.12)}
.pill--superadmin{border-color:rgba(34,211,238,.45);color:var(--accent);background:rgba(34,211,238,.14)}
.pill--inactive{border-color:rgba(148,163,184,.35);color:var(--muted);background:rgba(148,163,184,.10)}
.users-head{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
.users-head h2{margin:0}
.users-search{display:flex;align-items:center;gap:8px;min-width:min(520px,100%)}
.users-search input{flex:1;min-width:220px;padding:9px 12px;border-radius:10px;border:1.5px solid var(--border);
  background:var(--bg);color:var(--text);font-size:13px;font-family:inherit;outline:none}
.users-search input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.14)}
body.light .users-search input:focus{box-shadow:0 0 0 3px rgba(8,145,178,.12)}
.users-search .hint{font-size:11px;color:var(--muted);white-space:nowrap}
.users-search select{min-width:140px;padding:9px 12px;border-radius:10px;border:1.5px solid var(--border);
  background:var(--bg);color:var(--text);font-size:13px;font-family:inherit;outline:none}
.users-search select:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.14)}
body.light .users-search select:focus{box-shadow:0 0 0 3px rgba(8,145,178,.12)}
.tabs{display:flex;gap:8px;margin-bottom:18px;flex-wrap:wrap}
.tabs .btn{display:inline-flex;align-items:center;gap:8px;vertical-align:middle}
.tabs .btn svg{flex-shrink:0}
.nav-group-label{font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:1.2px;color:var(--muted);padding:6px 10px 4px;opacity:.7;display:flex;align-items:center;justify-content:space-between;cursor:pointer;border-radius:6px;user-select:none;transition:opacity .15s,background .15s}
.nav-group-label:hover{opacity:1;background:rgba(148,163,184,.08)}
.nav-group-chevron{display:inline-flex;flex-shrink:0;transition:transform .2s;opacity:.6}
.nav-group-label.ngl-collapsed .nav-group-chevron{transform:rotate(-90deg)}
.nav-subgroup-label{font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:var(--muted);padding:4px 10px 2px 14px;opacity:.55;display:flex;align-items:center;justify-content:space-between;cursor:pointer;border-radius:6px;user-select:none;transition:opacity .15s,background .15s;margin-top:2px}
.nav-subgroup-label:hover{opacity:.85;background:rgba(148,163,184,.06)}
.nav-subgroup-chevron{display:inline-flex;flex-shrink:0;transition:transform .2s;opacity:.55}
.nav-subgroup-label.nsl-collapsed .nav-subgroup-chevron{transform:rotate(-90deg)}
.hidden{display:none}
.legend{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px}
.legend .item{padding:12px;border:1px solid var(--border);border-radius:10px;font-size:12px}
.legend .item strong{display:block;margin-bottom:6px;font-size:13px}
.toast{position:fixed;bottom:22px;left:50%;transform:translateX(-50%);background:var(--card);border:1px solid var(--border);padding:12px 20px;border-radius:12px;font-size:13px;font-weight:600;box-shadow:0 8px 32px rgba(0,0,0,.35);z-index:900}.toast.err{border-left:3px solid var(--danger)}
@media(max-width:900px){
  body.has-topbar .main{padding-top:74px}
  .main{padding:12px 14px}
  .desktop-head{display:none}
  h1{font-size:18px}
  .sub{font-size:12px;margin-bottom:14px}
  .sidebar{width:min(280px,88vw);position:fixed;left:0;top:0;bottom:0;height:auto;max-height:100vh;z-index:300;
    transform:translateX(-105%);transition:transform .18s ease;
    box-shadow:0 16px 48px rgba(0,0,0,.55);padding:16px 10px}
  body.sb-open .sidebar{transform:translateX(0)}
  .layout{min-height:100vh}
  .nav-btn{padding:12px 14px;font-size:14px}
  .nav-scroll{gap:4px}
  /* Masquer les sous-onglets Utilisateurs dupliqués (navigation = sidebar) */
  .main section>.tabs:has(.sub-tab-btn){display:none}
  .tabs{overflow-x:auto;flex-wrap:nowrap;-webkit-overflow-scrolling:touch;gap:6px;margin-bottom:12px}
  .tabs .btn{flex-shrink:0;font-size:12px;padding:8px 12px}
  .form-grid{grid-template-columns:1fr}
  .users-search{flex-direction:column;min-width:0;align-items:stretch;width:100%}
  .users-search input,.users-search select{min-width:0;width:100%}
  .users-head{flex-direction:column;align-items:stretch}
  .card{padding:14px 16px}
  .table-wrap{-webkit-overflow-scrolling:touch;max-width:100%}
  table{font-size:11px}
  th,td{padding:6px 8px}
  .op-act{flex-wrap:wrap}
  .op-lbl-cell{max-width:160px}
  .legend{grid-template-columns:1fr}
  .four-sub-btn,.mac-sub-btn,.sub-tab-btn{flex-shrink:0}
}
/* ── Onglet Alertes maintenance ───────────────────────────────────── */
.maint-subtab{display:block}
.alert-row{display:flex;align-items:center;gap:14px;padding:12px 14px;background:var(--bg);border:1px solid var(--border);border-radius:10px;margin-bottom:8px;transition:border-color .15s}
.alert-row:hover{border-color:var(--accent)}
.alert-row.is-active{border-left:3px solid var(--success)}
.alert-row.is-inactive{border-left:3px solid var(--border)}
.alert-info{flex:1;min-width:0}
.alert-nom{font-size:14px;font-weight:600;color:var(--text);margin:0 0 2px 0}
.alert-meta{font-size:11px;color:var(--muted)}
.alert-status{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px}
.alert-status.on{color:var(--success)}
.alert-status.off{color:var(--muted)}
.alert-actions{display:grid;grid-template-columns:110px 92px 92px;gap:6px;align-items:center;flex-shrink:0}
.alert-actions .btn-sm{width:100%;text-align:center;white-space:nowrap}
@media(max-width:900px){.alert-actions{grid-template-columns:1fr 1fr 1fr;width:100%}}
/* Toggle switch */
.toggle{position:relative;display:inline-block;width:38px;height:22px;flex-shrink:0;cursor:pointer}
.toggle input{opacity:0;width:0;height:0;position:absolute}
.toggle-track{position:absolute;inset:0;background:var(--border);border-radius:22px;transition:background .18s}
.toggle-thumb{position:absolute;top:2px;left:2px;width:18px;height:18px;background:var(--card);border-radius:50%;transition:transform .18s;box-shadow:0 1px 3px rgba(0,0,0,.25)}
.toggle input:checked + .toggle-track{background:var(--success)}
.toggle input:checked + .toggle-track .toggle-thumb{transform:translateX(16px)}
.toggle input:disabled + .toggle-track{opacity:.5;cursor:not-allowed}
/* Modal d'aperçu / édition alerte */
.alert-modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:1000;display:flex;align-items:center;justify-content:center;padding:20px}
.alert-modal{background:var(--card);border:1px solid var(--border);border-radius:14px;max-width:560px;width:100%;max-height:90vh;overflow:auto;box-shadow:0 24px 64px rgba(0,0,0,.5)}
.alert-modal-head{display:flex;justify-content:space-between;align-items:center;padding:16px 20px;border-bottom:1px solid var(--border)}
.alert-modal-head h3{margin:0;font-size:15px;color:var(--text)}
.alert-modal-body{padding:18px 20px}
.alert-modal-foot{display:flex;gap:8px;justify-content:flex-end;padding:14px 20px;border-top:1px solid var(--border)}
.alert-preview-empty{padding:24px;text-align:center;color:var(--muted);font-size:13px;background:var(--bg);border-radius:10px;border:1px dashed var(--border)}
.alert-badge{display:inline-block;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;padding:2px 7px;border-radius:6px;margin-left:6px;vertical-align:1px}
.alert-field{margin-bottom:14px}
.alert-field-label{display:block;font-size:11px;font-weight:600;color:var(--text2);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}
.alert-field-input,.alert-field-select{width:100%;padding:10px 12px;border-radius:10px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-size:14px;box-sizing:border-box}
.alert-field-input:disabled{color:var(--muted);cursor:not-allowed}
.alert-field-row{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.alert-field-sub{margin-top:8px;padding:10px 12px;background:var(--bg);border:1px dashed var(--border);border-radius:8px}
.alert-field-help{font-size:11px;color:var(--muted);margin-top:4px;line-height:1.5}
@media(max-width:700px){.alert-field-row{grid-template-columns:1fr}}
.alert-badge.auto{background:var(--accent-bg);color:var(--accent)}
.alert-badge.todo{background:rgba(251,191,36,.18);color:var(--warn);margin-left:4px}
.alert-row.is-todo{border-left:3px solid var(--warn)}
.alerts-filter-btn.active{background:var(--accent-bg);color:var(--accent);border-color:var(--accent)}
.af-md-wrap{position:relative;width:100%}
.af-md-trigger{width:100%;padding:10px 12px;border-radius:10px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-size:14px;font-family:inherit;cursor:pointer;display:flex;align-items:center;justify-content:space-between;gap:8px;box-sizing:border-box}
.af-md-trigger:hover{border-color:var(--accent)}
.af-md-trigger-label{flex:1 1 auto;min-width:0;text-align:left;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.af-md-trigger-caret{flex:0 0 auto;color:var(--muted);font-size:10px}
.af-md-panel{position:absolute;top:calc(100% + 4px);left:0;right:0;background:var(--card);border:1px solid var(--border);border-radius:10px;padding:6px;z-index:100;max-height:280px;overflow-y:auto;box-shadow:0 8px 24px rgba(0,0,0,.35);display:none}
.af-md-panel.open{display:block}
.af-md-row{display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:6px;font-size:13px;color:var(--text);cursor:pointer;user-select:none}
.af-md-row:hover{background:var(--bg)}
.af-md-row input{flex:0 0 auto;width:16px;height:16px;margin:0;cursor:pointer}
.af-md-row-text{flex:1 1 auto;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.af-md-row-hint{margin-left:6px;color:var(--muted);font-weight:400;font-size:11px}
.af-md-row.is-disabled{cursor:not-allowed;opacity:.55}
.af-md-row.is-disabled .af-md-row-text{color:var(--muted)}
.af-md-sep{height:1px;background:var(--border);margin:4px 6px}
/* ── Tester sur moi : simulation pure ────────────────────────────── */
/* Pattern always-flex : un seul wrapper full-screen ; le placement est piloté
   par align-items / justify-content. Évite les conflits entre inset:0 (backdrop)
   et top/right/bottom/left (positions de coin). */
.ta-sim{position:fixed;inset:0;display:flex;z-index:2000;pointer-events:none;padding:20px;box-sizing:border-box}
.ta-sim.ta-blocking{background:rgba(0,0,0,.45);pointer-events:auto;animation:taSimFade .15s ease-out}
.ta-sim.ta-pl-center{align-items:center;justify-content:center}
.ta-sim.ta-pl-top-right{align-items:flex-start;justify-content:flex-end}
.ta-sim.ta-pl-bottom-right{align-items:flex-end;justify-content:flex-end}
.ta-sim-alert{background:var(--card);border:2px solid var(--accent);border-radius:12px;box-shadow:0 16px 48px rgba(0,0,0,.5);padding:16px 18px;max-height:calc(100vh - 40px);overflow-y:auto;animation:taSimSlide .2s ease-out;pointer-events:auto}
.ta-sz-small .ta-sim-alert{max-width:260px;width:100%}
.ta-sz-medium .ta-sim-alert{max-width:340px;width:100%}
.ta-sz-large .ta-sim-alert{max-width:440px;width:100%}
.ta-sim-title{font-size:18px;font-weight:700;color:var(--text);margin-bottom:16px;padding-bottom:12px;border-bottom:2px solid var(--accent);line-height:1.3;letter-spacing:-0.01em}
.ta-sim-actions{display:flex;gap:6px;margin-top:10px}
.ta-sim-btn{flex:1;padding:9px;border-radius:8px;font-size:13px;font-weight:600;border:none;cursor:pointer;font-family:inherit;background:var(--accent);color:#fff}
.ta-sim-btn:hover{filter:brightness(1.05)}
.ta-sim-exit{position:fixed;top:12px;left:12px;z-index:2100;background:rgba(0,0,0,.7);color:#fff;border:none;padding:6px 12px;border-radius:6px;font-size:12px;font-family:inherit;cursor:pointer;pointer-events:auto}
.ta-sim-exit:hover{background:rgba(0,0,0,.9)}
.af-cl-nc-lbl:has(input:checked){border-color:var(--danger);background:rgba(248,113,113,0.10);color:var(--danger)}
.ta-chip{display:inline-flex;align-items:center;padding:5px 11px;border-radius:999px;border:1.5px solid var(--border);background:var(--bg);color:var(--text);font-size:12px;font-weight:500;cursor:pointer;user-select:none;transition:background .12s ease,color .12s ease,border-color .12s ease;font-family:inherit;line-height:1.2}
.ta-chip input{position:absolute;opacity:0;width:0;height:0;pointer-events:none}
.ta-chip:hover{border-color:var(--accent)}
.ta-chip:has(input:checked){background:var(--accent);color:#fff;border-color:var(--accent)}
.ta-chip span{white-space:nowrap}
@keyframes taSimFade{from{opacity:0}to{opacity:1}}
@keyframes taSimSlide{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:translateY(0)}}
@media(max-width:600px){
  .ta-sim{padding:12px}
  .ta-sz-small .ta-sim-alert,.ta-sz-medium .ta-sim-alert,.ta-sz-large .ta-sim-alert{max-width:calc(100vw - 24px)}
}
@media(max-width:900px){
  .alert-row{flex-wrap:wrap}
  .alert-actions{width:100%;justify-content:flex-end}
}

/* ── Sidebar : scroll vertical propre + affordance visuelle ──────── */
.sidebar{scrollbar-width:thin;scrollbar-color:transparent transparent}
.sidebar:hover{scrollbar-color:var(--border) transparent}
.sidebar::-webkit-scrollbar{width:6px;height:0}
.sidebar::-webkit-scrollbar-thumb{background:transparent;border-radius:3px;transition:background .2s}
.sidebar:hover::-webkit-scrollbar-thumb{background:var(--border)}
.sidebar::-webkit-scrollbar-thumb:hover{background:var(--muted)}
.nav-scroll{scrollbar-width:thin;scrollbar-color:transparent transparent}
.nav-scroll:hover{scrollbar-color:var(--border) transparent}
.nav-scroll::-webkit-scrollbar{width:6px}
.nav-scroll::-webkit-scrollbar-thumb{background:transparent;border-radius:3px;transition:background .2s}
.nav-scroll:hover::-webkit-scrollbar-thumb{background:var(--border)}
.nav-scroll::-webkit-scrollbar-thumb:hover{background:var(--muted)}
/* Bouton Menu général — visuellement distinct */
.nav-btn.nav-menu{background:rgba(34,211,238,.06);border:1px solid transparent;margin-bottom:6px;font-weight:700;color:var(--text)}
.nav-btn.nav-menu:hover{background:rgba(34,211,238,.14);color:var(--accent)}
.nav-btn.nav-menu.active{background:rgba(34,211,238,.16);color:var(--accent);border-color:rgba(34,211,238,.35)}
/* ── Page Menu général ─────────────────────────────────────────── */
.menu-hero{margin-bottom:22px}
.menu-hero h1{font-size:22px;margin:0 0 6px}
.menu-hero p{color:var(--muted);font-size:13px;margin:0}
.menu-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:14px}
.menu-group{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:16px 18px;transition:border-color .18s,box-shadow .2s;display:flex;flex-direction:column}
.menu-group:hover{border-color:rgba(34,211,238,.35);box-shadow:0 0 0 1px rgba(34,211,238,.15),0 8px 24px rgba(0,0,0,.18)}
body.light .menu-group:hover{box-shadow:0 0 0 1px rgba(8,145,178,.18),0 8px 24px rgba(0,0,0,.08)}
.menu-group-head{display:flex;align-items:flex-start;gap:12px;margin-bottom:12px;padding-bottom:10px;border-bottom:1px solid var(--border)}
.menu-group-head .mg-ico{display:inline-flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:10px;background:rgba(34,211,238,.14);color:var(--accent);flex-shrink:0}
body.light .menu-group-head .mg-ico{background:rgba(8,145,178,.12)}
.menu-group-head .mg-lbl{font-size:14px;font-weight:800;color:var(--text);letter-spacing:.3px;line-height:1.2}
.menu-group-head .mg-desc{display:block;font-size:11px;color:var(--muted);font-weight:500;letter-spacing:normal;text-transform:none;margin-top:3px;line-height:1.4}
.menu-items{display:flex;flex-direction:column;gap:2px;flex:1}
.menu-item{display:flex;align-items:flex-start;gap:12px;padding:10px 12px;border-radius:10px;border:1px solid transparent;background:transparent;color:var(--text2);cursor:pointer;font-family:inherit;text-align:left;transition:background .12s,border-color .12s,color .12s;width:100%}
.menu-item:hover{background:rgba(34,211,238,.06);border-color:rgba(34,211,238,.28);color:var(--text)}
body.light .menu-item:hover{background:rgba(8,145,178,.06);border-color:rgba(8,145,178,.28)}
.menu-item .mi-ico{display:inline-flex;align-items:center;justify-content:center;width:30px;height:30px;border-radius:8px;background:var(--bg);color:var(--accent);flex-shrink:0;margin-top:1px}
.menu-item .mi-body{flex:1;min-width:0}
.menu-item .mi-lbl{display:block;font-size:13px;font-weight:700;color:var(--text);letter-spacing:.1px}
.menu-item .mi-desc{display:block;font-size:11px;color:var(--muted);margin-top:2px;line-height:1.4}
.menu-item .mi-chev{color:var(--muted);opacity:.5;flex-shrink:0;margin-top:8px;transition:transform .12s,color .12s,opacity .12s}
.menu-item:hover .mi-chev{color:var(--accent);opacity:1;transform:translateX(3px)}
@media(max-width:900px){
  .menu-grid{grid-template-columns:1fr;gap:10px}
  .menu-group{padding:14px 16px}
}
/* ── Fournisseurs — nouvelle vue ──────────────────────────────── */
.four-head{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:16px}
.four-head-info h2{margin:0 0 4px;font-size:15px}
.four-head-info p{margin:0;font-size:12px;color:var(--muted)}
.four-head-info .four-count{color:var(--accent);font-weight:700}
.four-head-actions{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.four-toolbar{display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap;align-items:center}
.four-toolbar input.four-search,.four-toolbar select.four-filter{padding:9px 12px;border-radius:10px;border:1.5px solid var(--border);background:var(--bg);color:var(--text);font-size:13px;font-family:inherit;outline:none;transition:border-color .15s,box-shadow .15s}
.four-toolbar input.four-search{flex:1;min-width:240px}
.four-toolbar input.four-search:focus,.four-toolbar select.four-filter:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12)}
body.light .four-toolbar input.four-search:focus,body.light .four-toolbar select.four-filter:focus{box-shadow:0 0 0 3px rgba(8,145,178,.1)}
.four-view-toggle{display:inline-flex;border:1.5px solid var(--border);border-radius:10px;overflow:hidden}
.four-view-toggle button{background:transparent;border:none;color:var(--text2);font-size:12px;font-weight:600;padding:8px 14px;cursor:pointer;font-family:inherit;transition:background .12s,color .12s}
.four-view-toggle button.active{background:rgba(34,211,238,.14);color:var(--accent)}
body.light .four-view-toggle button.active{background:rgba(8,145,178,.12)}
.four-pill{display:inline-block;padding:3px 9px;border-radius:6px;font-size:10px;font-weight:700;letter-spacing:.3px;text-transform:uppercase}
.four-pill.fsc{background:rgba(52,211,153,.15);color:var(--ok);border:1px solid rgba(52,211,153,.28)}
.four-pill.nofsc{background:var(--bg);color:var(--muted);border:1px solid var(--border)}
.four-pill.traca{background:rgba(34,211,238,.1);color:var(--accent);border:1px solid rgba(34,211,238,.28)}
.four-pill.traca-no{background:transparent;color:var(--muted);border:1px dashed var(--border)}
.four-groupe-tag{display:inline-flex;align-items:center;gap:5px;font-size:11px;font-weight:600;color:var(--text2);padding:3px 9px;border-radius:999px;background:var(--bg);border:1px solid var(--border)}
.four-groupe-tag .fgt-branche{color:var(--muted);font-weight:500;font-size:10px}
.four-empty{padding:36px 24px;text-align:center;color:var(--muted);font-size:13px;background:var(--bg);border-radius:10px;border:1px dashed var(--border);margin:8px 0}
.four-empty svg{opacity:.35;margin:0 auto 10px;display:block}
.four-groupe-row td{background:rgba(34,211,238,.06);font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.6px;color:var(--accent);padding:9px 12px;border-bottom:1px solid var(--border)}
body.light .four-groupe-row td{background:rgba(8,145,178,.06)}
.four-groupe-row .fgh-count{color:var(--muted);font-weight:600;margin-left:6px}
.four-add-panel{background:var(--bg);border:1px solid var(--border);border-radius:12px;padding:16px 18px;margin-bottom:14px;transition:max-height .2s ease,opacity .15s ease,margin .2s ease,padding .2s ease;overflow:hidden}
.four-add-panel.hidden{max-height:0;padding:0 18px;margin-bottom:0;opacity:0;border-color:transparent;pointer-events:none}
.four-add-panel h3{margin:0 0 12px;font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--text)}
.four-add-actions{display:flex;gap:8px;margin-top:10px;justify-content:flex-end}
.four-table{width:100%;border-collapse:collapse;font-size:12px}
.four-table th{background:rgba(15,23,42,.35);font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);padding:10px 12px;text-align:left;white-space:nowrap;position:sticky;top:0}
body.light .four-table th{background:#f1f5f9}
.four-table td{padding:10px 12px;vertical-align:middle;border-bottom:1px solid var(--border)}
.four-table tbody tr:hover td{background:rgba(34,211,238,.04)}
body.light .four-table tbody tr:hover td{background:rgba(8,145,178,.04)}
.four-table .four-nom-cell{font-weight:600;color:var(--text)}
.four-table .four-nom-cell small{display:block;font-weight:500;color:var(--muted);font-size:10px;margin-top:2px}
.four-table .four-code-cell code{font-family:ui-monospace,monospace;font-size:11px;color:var(--text2)}
.four-table td.four-act{text-align:right;white-space:nowrap}
.four-table td.four-act .btn-sm{margin-left:4px}
@media(max-width:900px){
  .four-toolbar input.four-search{min-width:0;width:100%;flex:1 1 100%}
  .four-head{flex-direction:column;align-items:stretch}
}

.btn-danger-solid{background:var(--danger);color:#fff;border:1px solid var(--danger);cursor:pointer}
.btn-danger-solid:hover{filter:brightness(1.08)}
.btn-danger-solid:disabled{opacity:.6;cursor:wait}
</style>
</head>
<body>
<script src="/static/mysifa_theme.js"></script>
<script src="/static/mysifa_favicon_badge.js"></script>
<script src="/static/mysifa_user_chip.js"></script>
<div class="sidebar-overlay" id="sb-ov"></div>
<div class="layout">
  <aside class="sidebar">
    <div class="logo">My<span>Sifa</span><div class="logo-sub">by SIFA</div></div>
    <div class="nav-scroll" style="width:100%;margin:0">
      <button type="button" class="nav-btn nav-menu active" data-tab="menu">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
        Menu général
      </button>
      <div class="nav-group-label"><span>Base</span><svg class="nav-group-chevron" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg></div>
      <div class="nav-subgroup-label"><span>Fabrication</span><svg class="nav-subgroup-chevron" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg></div>
      <button type="button" class="nav-btn" data-tab="operations">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
        Opérations
      </button>
      <button type="button" class="nav-btn" data-tab="maintenance">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="8" width="20" height="12" rx="2"/><path d="M8 8V6a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="12" y1="12" x2="12" y2="16"/><line x1="10" y1="14" x2="14" y2="14"/></svg>
        Maintenance
      </button>
      <button type="button" class="nav-btn" data-tab="machines">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
        Machines
      </button>
      <div class="nav-subgroup-label"><span>Logistique</span><svg class="nav-subgroup-chevron" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg></div>
      <button type="button" class="nav-btn" data-tab="emplacements">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/><line x1="12" y1="12" x2="12" y2="16"/><line x1="10" y1="14" x2="14" y2="14"/></svg>
        Emplacements
      </button>
      <button type="button" class="nav-btn" data-tab="laizes">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="2 12 22 12"/><line x1="6" y1="9" x2="6" y2="15"/><line x1="10" y1="7" x2="10" y2="17"/><line x1="14" y1="9" x2="14" y2="15"/><line x1="18" y1="7" x2="18" y2="17"/></svg>
        Laizes matières
      </button>
      <button type="button" class="nav-btn" data-tab="importations">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>
        Importations
      </button>
      <button type="button" class="nav-btn" data-tab="bridge" title="Rapprochement MyStock ↔ Coûts matières">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 3v18"/><path d="M18 3v18"/><path d="M6 8h12"/><path d="M6 16h12"/></svg>
        Appairage matières
      </button>
      <div class="nav-subgroup-label"><span>Contacts</span><svg class="nav-subgroup-chevron" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg></div>
      <button type="button" class="nav-btn" data-tab="users">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
        Utilisateurs
      </button>
      <button type="button" class="nav-btn" data-tab="fournisseurs">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>
        Fournisseurs
      </button>
      <button type="button" class="nav-btn" data-tab="clients">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 21V7l9-4 9 4v14"/><path d="M9 21V12h6v9"/><path d="M3 21h18"/></svg>
        Clients
      </button>
      <div class="nav-group-label" style="margin-top:8px"><span>Accès</span><svg class="nav-group-chevron" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg></div>
      <button type="button" class="nav-btn" data-tab="matrix">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
        Matrice d'accès
      </button>
      <button type="button" class="nav-btn" data-tab="defaults">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>
        Référentiel rôles
      </button>
      <div class="nav-group-label" style="margin-top:8px"><span>Communication</span><svg class="nav-group-chevron" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg></div>
      <button type="button" class="nav-btn" data-tab="updates">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
        Mises à jour
      </button>
      <div class="nav-group-label" style="margin-top:8px"><span>Audit</span><svg class="nav-group-chevron" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg></div>
      <button type="button" class="nav-btn" data-tab="audit">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
          <line x1="16" y1="13" x2="8" y2="13"/>
          <line x1="16" y1="17" x2="8" y2="17"/>
          <polyline points="10 9 9 9 8 9"/>
        </svg>
        Log
      </button>
      <button type="button" class="nav-btn" data-tab="dashboards">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
        Tableaux de bord
      </button>
      <button type="button" class="nav-btn" data-tab="fsc">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10z"/>
          <path d="M2 21c0-3 2.5-5 5-5"/>
        </svg>
        Registre FSC
      </button>
      <button type="button" class="nav-btn" data-tab="api">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
        Clés API
      </button>
      <div class="nav-group-label" style="margin-top:8px"><span>Impression</span><svg class="nav-group-chevron" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg></div>
      <button type="button" class="nav-btn" data-tab="printers">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/></svg>
        Imprimantes
      </button>
      <div class="nav-group-label" style="margin-top:8px"><span>Déploiement</span><svg class="nav-group-chevron" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg></div>
      <button type="button" class="nav-btn" data-tab="promote">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14"/><path d="M12 5l7 7-7 7"/></svg>
        Promouvoir v1 → v2
      </button>
    </div>
    <div class="sidebar-bottom">
      <button type="button" class="nav-btn back-mysifa" onclick="location.href='/'">
        ← Retour <span class="wm">My<span>Sifa</span></span>
      </button>
      <div class="user-chip" id="sb-user-chip" title="Modifier mon profil" onclick="location.href='/profil'"></div>
      <button type="button" class="support-btn" id="sb-support" title="Contacter le support (email)">
        <span class="support-ico" id="sb-support-ico"></span>
        <span>Contacter le support</span>
      </button>
      <button type="button" class="theme-btn" id="theme-btn">
        <span class="theme-ico" id="theme-ico-slot"></span>
        <span class="theme-label" id="theme-label">Mode sombre</span>
      </button>
      <button type="button" class="logout-btn" id="logout-btn">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
        Déconnexion
      </button>
      <div class="version">Paramètres · MySifa __V_LABEL__</div>
    </div>
  </aside>
  <main class="main">
    <div class="mobile-topbar">
      <button type="button" class="mobile-menu-btn" id="sb-burger" aria-label="Menu">
        <span style="display: inline-flex; align-items: center; flex-shrink: 0;">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="display:inline-block;vertical-align:middle;flex-shrink:0"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
        </span>
      </button>
      <div>
        <div class="mobile-topbar-title">Paramètres</div>
        <div class="mobile-topbar-sub">Gestion des comptes et des accès</div>
      </div>
      <button type="button" class="mobile-home-btn" id="sb-home" aria-label="Accueil">
        <span style="display: inline-flex; align-items: center; flex-shrink: 0;">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="display:inline-block;vertical-align:middle;flex-shrink:0"><path d="M3 10.5L12 3l9 7.5"></path><path d="M5 10v11h14V10"></path><path d="M10 21v-6h4v6"></path></svg>
        </span>
      </button>
    </div>
    <div class="desktop-head">
      <h1>Paramètres</h1>
      <p class="sub">Gestion des comptes et visualisation des accès applications — réservé au super administrateur.</p>
    </div>

    <section id="panel-menu">
      <div class="menu-hero">
        <h1>Paramètres</h1>
        <p>Configuration MySifa — sélectionnez une catégorie ou utilisez la barre latérale.</p>
      </div>
      <div class="menu-grid">

        <div class="menu-group">
          <div class="menu-group-head">
            <span class="mg-ico"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg></span>
            <div><span class="mg-lbl">Fabrication</span><span class="mg-desc">Codes opérations, maintenance et parc machines.</span></div>
          </div>
          <div class="menu-items">
            <button type="button" class="menu-item" data-goto="operations">
              <span class="mi-ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg></span>
              <span class="mi-body"><span class="mi-lbl">Opérations</span><span class="mi-desc">Référentiel des codes saisis en production.</span></span>
              <svg class="mi-chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
            </button>
            <button type="button" class="menu-item" data-goto="maintenance">
              <span class="mi-ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="8" width="20" height="12" rx="2"/><path d="M8 8V6a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="12" y1="12" x2="12" y2="16"/><line x1="10" y1="14" x2="14" y2="14"/></svg></span>
              <span class="mi-body"><span class="mi-lbl">Maintenance</span><span class="mi-desc">Codes d'incident et alertes opérateurs.</span></span>
              <svg class="mi-chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
            </button>
            <button type="button" class="menu-item" data-goto="machines">
              <span class="mi-ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg></span>
              <span class="mi-body"><span class="mi-lbl">Machines</span><span class="mi-desc">Horaires, capacité et rentabilité par machine.</span></span>
              <svg class="mi-chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
            </button>
          </div>
        </div>

        <div class="menu-group">
          <div class="menu-group-head">
            <span class="mg-ico"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg></span>
            <div><span class="mg-lbl">Logistique</span><span class="mg-desc">Stock, emplacements et imports transporteurs.</span></div>
          </div>
          <div class="menu-items">
            <button type="button" class="menu-item" data-goto="emplacements">
              <span class="mi-ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/><line x1="12" y1="12" x2="12" y2="16"/><line x1="10" y1="14" x2="14" y2="14"/></svg></span>
              <span class="mi-body"><span class="mi-lbl">Emplacements</span><span class="mi-desc">Plan d'allées et rangées du magasin.</span></span>
              <svg class="mi-chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
            </button>
            <button type="button" class="menu-item" data-goto="laizes">
              <span class="mi-ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="2 12 22 12"/><line x1="6" y1="9" x2="6" y2="15"/><line x1="10" y1="7" x2="10" y2="17"/><line x1="14" y1="9" x2="14" y2="15"/><line x1="18" y1="7" x2="18" y2="17"/></svg></span>
              <span class="mi-body"><span class="mi-lbl">Laizes matières</span><span class="mi-desc">Formats standards par matière.</span></span>
              <svg class="mi-chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
            </button>
            <button type="button" class="menu-item" data-goto="importations">
              <span class="mi-ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg></span>
              <span class="mi-body"><span class="mi-lbl">Importations</span><span class="mi-desc">Grilles tarifaires transporteurs, historiques.</span></span>
              <svg class="mi-chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
            </button>
            <button type="button" class="menu-item" data-goto="bridge">
              <span class="mi-ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3v18"/><path d="M18 3v18"/><path d="M6 8h12"/><path d="M6 16h12"/></svg></span>
              <span class="mi-body"><span class="mi-lbl">Appairage matières</span><span class="mi-desc">Rapprocher les références MyStock avec Coûts matières.</span></span>
              <svg class="mi-chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
            </button>
          </div>
        </div>

        <div class="menu-group">
          <div class="menu-group-head">
            <span class="mg-ico"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg></span>
            <div><span class="mg-lbl">Contacts</span><span class="mg-desc">Utilisateurs, fournisseurs et clients (ERP).</span></div>
          </div>
          <div class="menu-items">
            <button type="button" class="menu-item" data-goto="users">
              <span class="mi-ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg></span>
              <span class="mi-body"><span class="mi-lbl">Utilisateurs</span><span class="mi-desc">Comptes, rôles et rattachement opérateur.</span></span>
              <svg class="mi-chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
            </button>
            <button type="button" class="menu-item" data-goto="fournisseurs">
              <span class="mi-ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg></span>
              <span class="mi-body"><span class="mi-lbl">Fournisseurs</span><span class="mi-desc">Certifications FSC, groupes, guide traçabilité.</span></span>
              <svg class="mi-chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
            </button>
            <button type="button" class="menu-item" data-goto="clients">
              <span class="mi-ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21V7l9-4 9 4v14"/><path d="M9 21V12h6v9"/><path d="M3 21h18"/></svg></span>
              <span class="mi-body"><span class="mi-lbl">Clients</span><span class="mi-desc">Référentiel ERP partagé MyProd / MyExpé / MyCompta.</span></span>
              <svg class="mi-chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
            </button>
          </div>
        </div>

        <div class="menu-group">
          <div class="menu-group-head">
            <span class="mg-ico"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg></span>
            <div><span class="mg-lbl">Accès &amp; permissions</span><span class="mg-desc">Matrice des accès et rôles par défaut.</span></div>
          </div>
          <div class="menu-items">
            <button type="button" class="menu-item" data-goto="matrix">
              <span class="mi-ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg></span>
              <span class="mi-body"><span class="mi-lbl">Matrice d'accès</span><span class="mi-desc">Qui voit quoi, application par application.</span></span>
              <svg class="mi-chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
            </button>
            <button type="button" class="menu-item" data-goto="defaults">
              <span class="mi-ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg></span>
              <span class="mi-body"><span class="mi-lbl">Référentiel rôles</span><span class="mi-desc">Accès par défaut pour chaque rôle.</span></span>
              <svg class="mi-chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
            </button>
          </div>
        </div>

        <div class="menu-group">
          <div class="menu-group-head">
            <span class="mg-ico"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg></span>
            <div><span class="mg-lbl">Communication</span><span class="mg-desc">Annonces MAJ diffusées aux utilisateurs.</span></div>
          </div>
          <div class="menu-items">
            <button type="button" class="menu-item" data-goto="updates">
              <span class="mi-ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg></span>
              <span class="mi-body"><span class="mi-lbl">Mises à jour</span><span class="mi-desc">Rédiger et publier une annonce de release.</span></span>
              <svg class="mi-chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
            </button>
          </div>
        </div>

        <div class="menu-group">
          <div class="menu-group-head">
            <span class="mg-ico"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v20M2 12h20"/><circle cx="12" cy="12" r="10"/></svg></span>
            <div><span class="mg-lbl">Audit &amp; qualité</span><span class="mg-desc">Log d'activité, tableaux de bord, registre FSC.</span></div>
          </div>
          <div class="menu-items">
            <button type="button" class="menu-item" data-goto="audit">
              <span class="mi-ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg></span>
              <span class="mi-body"><span class="mi-lbl">Log d'activité</span><span class="mi-desc">Historique complet des actions superadmin.</span></span>
              <svg class="mi-chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
            </button>
            <button type="button" class="menu-item" data-goto="dashboards">
              <span class="mi-ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg></span>
              <span class="mi-body"><span class="mi-lbl">Tableaux de bord</span><span class="mi-desc">Widgets consolidés par périmètre.</span></span>
              <svg class="mi-chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
            </button>
            <button type="button" class="menu-item" data-goto="fsc">
              <span class="mi-ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10z"/><path d="M2 21c0-3 2.5-5 5-5"/></svg></span>
              <span class="mi-body"><span class="mi-lbl">Registre FSC</span><span class="mi-desc">Traçabilité des flux et audits certifiés.</span></span>
              <svg class="mi-chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
            </button>
            <button type="button" class="menu-item" data-goto="formations">
              <span class="mi-ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg></span>
              <span class="mi-body"><span class="mi-lbl">Formations & guides</span><span class="mi-desc">Suivi des tutos in-app lus par utilisateur (reset possible).</span></span>
              <svg class="mi-chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
            </button>
            <button type="button" class="menu-item" data-goto="api">
              <span class="mi-ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg></span>
              <span class="mi-body"><span class="mi-lbl">Clés API</span><span class="mi-desc">Tokens d'intégration externe.</span></span>
              <svg class="mi-chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
            </button>
          </div>
        </div>

        <div class="menu-group">
          <div class="menu-group-head">
            <span class="mg-ico"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/></svg></span>
            <div><span class="mg-lbl">Impression &amp; déploiement</span><span class="mg-desc">Imprimantes, templates et promotion v1 → v2.</span></div>
          </div>
          <div class="menu-items">
            <button type="button" class="menu-item" data-goto="printers">
              <span class="mi-ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/></svg></span>
              <span class="mi-body"><span class="mi-lbl">Imprimantes</span><span class="mi-desc">Configuration Zebra / Brother, templates étiquettes.</span></span>
              <svg class="mi-chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
            </button>
            <button type="button" class="menu-item" data-goto="promote">
              <span class="mi-ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M12 5l7 7-7 7"/></svg></span>
              <span class="mi-body"><span class="mi-lbl">Promouvoir v1 → v2</span><span class="mi-desc">Publier le staging en production après validation.</span></span>
              <svg class="mi-chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
            </button>
          </div>
        </div>

      </div>
    </section>

    <section id="panel-users" class="hidden">
    <div class="tabs" style="margin-bottom:14px">
      <button type="button" class="btn btn-sec sub-tab-btn active" data-subtab="users-list">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>
        Liste
      </button>
      <button type="button" class="btn btn-sec sub-tab-btn" data-subtab="users-matrix">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
        Matrice
      </button>
      <button type="button" class="btn btn-sec sub-tab-btn" data-subtab="users-defaults">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>
        Référentiel
      </button>
    </div>
      <div class="card">
        <h2>Ajouter un utilisateur</h2>
        <div class="form-grid">
          <input type="text" id="cu-nom" placeholder="Nom complet" autocomplete="name">
          <input type="text" id="cu-ident" placeholder="Identifiant (auto si vide)" autocomplete="off">
          <input type="email" id="cu-email" placeholder="Email" autocomplete="off">
          <input type="password" id="cu-pwd" placeholder="Mot de passe (8+)" autocomplete="new-password">
          <select id="cu-role"></select>
          <select id="cu-op"><option value="">— Opérateur lié —</option></select>
          <select id="cu-mac"><option value="">— Machine (fabrication) —</option></select>
        </div>
        <button type="button" class="btn" id="cu-go">Créer le compte</button>
      </div>
      <div class="card">
        <div class="users-head">
          <h2>Utilisateurs</h2>
          <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
            <div class="users-search">
              <input type="search" id="users-q" placeholder="Rechercher (nom, email, rôle, opérateur, machine…)" autocomplete="off" spellcheck="false">
              <select id="users-role-filter"><option value="">Tous les services</option></select>
              <span class="hint" id="users-q-hint"></span>
            </div>
            <button type="button" class="btn btn-sec" onclick="downloadUsersCSV()" title="Télécharger la liste">Télécharger</button>
          </div>
        </div>
        <div id="users-list"></div>
      </div>
    </section>

    <section id="panel-matrix" class="hidden">
    <div class="tabs" style="margin-bottom:14px">
      <button type="button" class="btn btn-sec sub-tab-btn" data-subtab="users-list">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>
        Liste
      </button>
      <button type="button" class="btn btn-sec sub-tab-btn active" data-subtab="users-matrix">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
        Matrice
      </button>
      <button type="button" class="btn btn-sec sub-tab-btn" data-subtab="users-defaults">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>
        Référentiel
      </button>
    </div>
      <div class="card">
        <h2>Qui a accès à quoi</h2>
        <p class="sub" style="margin-top:-8px">Cases à cocher : accès effectif (héritage du rôle ou surcharges). « Perso » = différent du défaut du rôle. Paramètres reste réservé au rôle super admin. Les super admins ont tout ; la ligne est en lecture seule.</p>
        <div class="table-wrap" id="matrix-table"></div>
      </div>
    </section>

    <section id="panel-defaults" class="hidden">
    <div class="tabs" style="margin-bottom:14px">
      <button type="button" class="btn btn-sec sub-tab-btn" data-subtab="users-list">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>
        Liste
      </button>
      <button type="button" class="btn btn-sec sub-tab-btn" data-subtab="users-matrix">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
        Matrice
      </button>
      <button type="button" class="btn btn-sec sub-tab-btn active" data-subtab="users-defaults">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>
        Référentiel
      </button>
    </div>
      <div class="card">
        <h2>Accès par défaut selon le rôle</h2>
        <p class="sub" style="margin-top:-8px">Chaque utilisateur hérite de ces accès selon son rôle assigné.</p>
        <div class="legend" id="role-legend"></div>
      </div>
    </section>

    <section id="panel-fournisseurs" class="hidden">
    <div class="tabs" style="margin-bottom:14px">
      <button type="button" class="btn btn-sec four-sub-btn active" data-foursub="four-certifs">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
        Répertoire
      </button>
      <button type="button" class="btn btn-sec four-sub-btn" data-foursub="four-hist">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
        Historique réceptions
      </button>
      <button type="button" class="btn btn-sec four-sub-btn" data-foursub="four-contacts">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
        Contacts & infos
      </button>
    </div>
      <div id="four-certifs">
        <div class="card">
          <div class="four-head">
            <div class="four-head-info">
              <h2>Fournisseurs</h2>
              <p>Certifications FSC, rattachement de groupe et guide de traçabilité utilisés par MyStock, MyProd et le registre FSC. <span id="four-count" class="four-count"></span></p>
            </div>
            <div class="four-head-actions">
              <div class="four-view-toggle" role="tablist" aria-label="Mode d'affichage">
                <button type="button" data-fourview="flat" class="active" title="Liste alphabétique">Liste</button>
                <button type="button" data-fourview="groupe" title="Groupé par maison mère">Par groupe</button>
              </div>
              <button type="button" class="btn btn-sm" id="four-add-toggle">+ Nouveau fournisseur</button>
            </div>
          </div>

          <div class="four-toolbar">
            <input type="text" id="four-search" class="four-search" placeholder="Rechercher (nom, licence, certificat, groupe...)" autocomplete="off">
            <select id="four-filter-fsc" class="four-filter" title="Filtrer par certification FSC">
              <option value="">Tous</option>
              <option value="1">Certifiés FSC</option>
              <option value="0">Non certifiés</option>
            </select>
            <select id="four-filter-groupe" class="four-filter" title="Filtrer par groupe"><option value="">Tous les groupes</option></select>
            <select id="four-filter-traca" class="four-filter" title="Filtrer par guide traçabilité">
              <option value="">Traçabilité : tous</option>
              <option value="1">Guide renseigné</option>
              <option value="0">Guide manquant</option>
            </select>
          </div>

          <div class="four-add-panel hidden" id="four-add-panel">
            <h3>Nouveau fournisseur</h3>
            <div class="form-grid">
              <input type="text" id="cf-nom" placeholder="Nom du fournisseur *" autocomplete="off">
              <input type="text" id="cf-groupe" placeholder="Groupe (ex: Fedrigoni) — optionnel" autocomplete="off" list="four-groupes-dl">
              <input type="text" id="cf-branche" placeholder="Branche du groupe (ex: Italy) — optionnel" autocomplete="off">
              <datalist id="four-groupes-dl"></datalist>
            </div>
            <label style="display:inline-flex;align-items:center;gap:8px;margin:12px 0 10px;font-size:13px;color:var(--text);cursor:pointer">
              <input type="checkbox" id="cf-has-fsc" checked style="width:16px;height:16px;cursor:pointer">
              Fournisseur certifié FSC
            </label>
            <div id="cf-fsc-fields" class="form-grid">
              <input type="text" id="cf-licence" placeholder="Code Licence FSC (ex: FSC-C004451)" autocomplete="off">
              <input type="text" id="cf-certificat" placeholder="Code Certificat FSC (ex: CU-COC-807907)" autocomplete="off">
            </div>
            <p class="sub" style="margin:10px 0 0;font-size:11px">Le guide de traçabilité (photo, code exemple) se configure ensuite via « Modifier ».</p>
            <div class="four-add-actions">
              <button type="button" class="btn btn-sec btn-sm" id="cf-cancel">Annuler</button>
              <button type="button" class="btn btn-sm" id="cf-go">Ajouter le fournisseur</button>
            </div>
          </div>

          <div class="table-wrap" id="four-table-wrap"></div>
        </div>
      </div>
      <div id="four-hist" class="hidden">
        <div class="card">
          <h2>Historique des réceptions par fournisseur</h2>
          <p class="sub" style="margin-top:-8px">Les 50 dernières réceptions enregistrées dans MyStock, tous opérateurs confondus.</p>
          <div class="form-grid" style="margin-bottom:12px;grid-template-columns:1fr">
            <select id="fh-four"><option value="">— Choisir un fournisseur —</option></select>
          </div>
          <div id="fh-results"></div>
        </div>
      </div>
      <div id="four-contacts" class="hidden">
        <div class="card">
          <div class="four-head">
            <div class="four-head-info">
              <h2>Contacts &amp; infos fournisseurs</h2>
              <p>Coordonnées postales, contacts multiples par fournisseur, langue par défaut (FR/EN) pour le portail AO et tags de spécialités. <span id="four-contacts-count" class="four-count"></span></p>
            </div>
            <div class="four-head-actions">
              <button type="button" class="btn btn-sec btn-sm" id="four-contacts-export">Exporter CSV</button>
            </div>
          </div>
          <div class="four-toolbar">
            <input type="text" id="four-contacts-search" class="four-search" placeholder="Rechercher (nom, ville, tag, contact…)" autocomplete="off">
            <select id="four-contacts-filter-langue" class="four-filter" title="Filtrer par langue par défaut">
              <option value="">Langue : toutes</option>
              <option value="fr">FR</option>
              <option value="en">EN</option>
            </select>
            <select id="four-contacts-filter-tag" class="four-filter" title="Filtrer par tag / spécialité">
              <option value="">Tag : tous</option>
            </select>
            <select id="four-contacts-filter-actif" class="four-filter" title="Filtrer par statut">
              <option value="">Statut : tous</option>
              <option value="1" selected>Actifs</option>
              <option value="0">Inactifs</option>
            </select>
          </div>
          <div id="four-contacts-table-wrap"></div>
        </div>
      </div>
    </section>

    <section id="panel-clients" class="hidden">
      <div class="card">
        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:16px">
          <div>
            <h2 style="margin:0 0 4px">Clients (ERP)</h2>
            <p class="sub" style="margin:0;font-size:12px">Référentiel clients utilisé par MyProd, MyExpé et MyCompta. <span id="cli-count" style="color:var(--accent);font-weight:700"></span></p>
          </div>
          <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
            <button type="button" class="btn btn-sec btn-sm" id="cli-export-csv">Exporter CSV</button>
            <button type="button" class="btn btn-sec btn-sm" id="cli-import-btn">Importer xlsx</button>
            <input type="file" id="cli-import-input" accept=".xlsx,.xlsm" style="display:none">
            <button type="button" class="btn btn-sm" id="cli-new-btn">+ Nouveau client</button>
          </div>
        </div>
        <div style="display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap;align-items:center">
          <input type="text" id="cli-search" placeholder="Rechercher (raison sociale, code, ville, SIRET, TVA, email…)" autocomplete="off"
            style="flex:1;min-width:260px;padding:9px 12px;border-radius:10px;border:1.5px solid var(--border);background:var(--bg);color:var(--text);font-size:13px;font-family:inherit;outline:none;transition:border-color .15s,box-shadow .15s">
          <select id="cli-filter-etat" style="padding:9px 12px;border-radius:10px;border:1.5px solid var(--border);background:var(--bg);color:var(--text);font-size:13px;font-family:inherit;outline:none">
            <option value="">Tous les états</option>
          </select>
        </div>
        <div class="table-wrap">
          <table id="cli-table" style="min-width:780px">
            <thead>
              <tr style="background:rgba(34,211,238,.06)">
                <th style="text-align:left;padding:10px 12px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);white-space:nowrap">N°</th>
                <th style="text-align:left;padding:10px 12px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);white-space:nowrap">Code</th>
                <th style="text-align:left;padding:10px 12px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted)">Raison sociale</th>
                <th style="text-align:left;padding:10px 12px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);white-space:nowrap">Ville</th>
                <th style="text-align:left;padding:10px 12px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);white-space:nowrap">Pays</th>
                <th style="text-align:left;padding:10px 12px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);white-space:nowrap">Téléphone</th>
                <th style="text-align:left;padding:10px 12px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted)">Email</th>
                <th style="text-align:left;padding:10px 12px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);white-space:nowrap">État</th>
                <th style="padding:10px 12px;width:1px"></th>
              </tr>
            </thead>
            <tbody id="cli-tbody">
              <tr><td colspan="9" style="padding:24px 12px;color:var(--muted);font-size:13px;text-align:center">Chargement…</td></tr>
            </tbody>
          </table>
        </div>
        <p id="cli-empty" class="sub" style="display:none;margin:16px 0 4px;font-size:13px"></p>
      </div>
    </section>

    <!-- Modal client (création / édition) -->
    <div id="cli-modal-overlay" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:800;align-items:center;justify-content:center" class="hidden">
      <div style="background:var(--card);border:1px solid var(--border);border-radius:16px;padding:24px;width:min(880px,96vw);max-height:92vh;overflow:auto">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;gap:12px">
          <h2 id="cli-modal-title" style="margin:0;font-size:17px">Nouveau client</h2>
          <button type="button" class="btn btn-sec btn-sm" onclick="closeCliModal()">×</button>
        </div>
        <div class="tabs" style="margin-bottom:14px">
          <button type="button" class="btn btn-sec sub-tab-btn active" data-clisub="cli-tab-info">Identité</button>
          <button type="button" class="btn btn-sec sub-tab-btn" data-clisub="cli-tab-addr">Adresse</button>
          <button type="button" class="btn btn-sec sub-tab-btn" data-clisub="cli-tab-contact">Contact</button>
          <button type="button" class="btn btn-sec sub-tab-btn" data-clisub="cli-tab-commerce">Commerce</button>
          <button type="button" class="btn btn-sec sub-tab-btn" data-clisub="cli-tab-notes">Notes</button>
        </div>

        <div id="cli-tab-info" class="cli-tab">
          <div class="form-grid" style="grid-template-columns:1fr 1fr 1fr;gap:10px">
            <div><label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">N°</label>
              <input type="number" id="cli-numero" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Code</label>
              <input type="text" id="cli-code" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">État</label>
              <select id="cli-etat" style="width:100%">
                <option value="Normal">Normal</option>
                <option value="Bloqué">Bloqué</option>
                <option value="Inactif">Inactif</option>
              </select></div>
            <div style="grid-column:span 3"><label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Raison sociale *</label>
              <input type="text" id="cli-raison" required style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">SIRET</label>
              <input type="text" id="cli-siret" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">N° TVA</label>
              <input type="text" id="cli-tva" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">RCS</label>
              <input type="text" id="cli-rcs" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">EAN</label>
              <input type="text" id="cli-ean" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">NIF</label>
              <input type="text" id="cli-nif" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Groupe</label>
              <input type="text" id="cli-groupe" style="width:100%"></div>
          </div>
        </div>

        <div id="cli-tab-addr" class="cli-tab" style="display:none">
          <div class="form-grid" style="grid-template-columns:1fr 1fr;gap:10px">
            <div style="grid-column:span 2"><label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Adresse 1</label>
              <input type="text" id="cli-adresse1" style="width:100%"></div>
            <div style="grid-column:span 2"><label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Adresse 2</label>
              <input type="text" id="cli-adresse2" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">B.P.</label>
              <input type="text" id="cli-bp" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Code postal</label>
              <input type="text" id="cli-cp" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Ville</label>
              <input type="text" id="cli-ville" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Code pays</label>
              <input type="text" id="cli-code-pays" maxlength="3" style="width:100%"></div>
            <div style="grid-column:span 2"><label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Pays</label>
              <input type="text" id="cli-pays" style="width:100%"></div>
          </div>
        </div>

        <div id="cli-tab-contact" class="cli-tab" style="display:none">
          <div class="form-grid" style="grid-template-columns:1fr 1fr;gap:10px">
            <div><label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Téléphone</label>
              <input type="text" id="cli-tel" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Télécopie</label>
              <input type="text" id="cli-fax" style="width:100%"></div>
            <div style="grid-column:span 2"><label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Email</label>
              <input type="email" id="cli-email" style="width:100%"></div>
            <div style="grid-column:span 2" class="sub" style="font-size:11px;color:var(--muted);margin-top:4px">Contact principal (interlocuteur)</div>
            <div><label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Nom du contact</label>
              <input type="text" id="cli-contact-nom" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Fonction</label>
              <input type="text" id="cli-contact-fonction" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Email contact</label>
              <input type="email" id="cli-contact-email" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Téléphone contact</label>
              <input type="text" id="cli-contact-tel" style="width:100%"></div>
          </div>
        </div>

        <div id="cli-tab-commerce" class="cli-tab" style="display:none">
          <div class="form-grid" style="grid-template-columns:1fr 1fr;gap:10px">
            <div><label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Représentant</label>
              <input type="text" id="cli-rep" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">ADV</label>
              <input type="text" id="cli-adv" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Mode de livraison</label>
              <input type="text" id="cli-mode-liv" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Mode de règlement</label>
              <input type="text" id="cli-mode-reg" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Devise</label>
              <input type="text" id="cli-devise" maxlength="4" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Encours autorisé</label>
              <input type="number" id="cli-encours" step="0.01" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Code comptable</label>
              <input type="text" id="cli-codecpta" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Catégorie 1</label>
              <input type="text" id="cli-cat1" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Catégorie 2</label>
              <input type="text" id="cli-cat2" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Catégorie 3</label>
              <input type="text" id="cli-cat3" style="width:100%"></div>
          </div>
        </div>

        <div id="cli-tab-notes" class="cli-tab" style="display:none">
          <label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Notes internes</label>
          <textarea id="cli-notes" rows="8" placeholder="Remarques, conditions particulières…" style="width:100%;padding:10px 12px;border-radius:10px;border:1.5px solid var(--border);background:var(--bg);color:var(--text);font-size:13px;font-family:inherit;resize:vertical"></textarea>
        </div>

        <div style="display:flex;gap:10px;justify-content:space-between;align-items:center;margin-top:18px;padding-top:14px;border-top:1px solid var(--border)">
          <button type="button" class="btn btn-danger btn-sm" id="cli-delete-btn" style="display:none" onclick="deleteCliFromModal()">Supprimer</button>
          <div style="display:flex;gap:10px;margin-left:auto">
            <button type="button" class="btn btn-sec" onclick="closeCliModal()">Annuler</button>
            <button type="button" class="btn" onclick="saveCliModal()">Enregistrer</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal import xlsx clients -->
    <div id="cli-import-overlay" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:801;align-items:center;justify-content:center" class="hidden">
      <div style="background:var(--card);border:1px solid var(--border);border-radius:16px;padding:24px;width:min(520px,95vw)">
        <h2 style="margin:0 0 14px;font-size:17px">Import clients xlsx</h2>
        <p class="sub" style="margin:0 0 14px;font-size:12px">Fichier : <strong id="cli-import-filename" style="color:var(--text)"></strong></p>
        <label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:6px">Mode d'import</label>
        <div style="display:flex;flex-direction:column;gap:8px;margin-bottom:18px">
          <label style="display:flex;gap:10px;align-items:flex-start;cursor:pointer;padding:10px 12px;border:1.5px solid var(--border);border-radius:10px">
            <input type="radio" name="cli-import-mode" value="merge" checked style="margin-top:2px">
            <span><strong style="color:var(--text);font-size:13px">Fusionner (recommandé)</strong><br><span style="font-size:12px;color:var(--muted)">Les clients existants (même code) sont mis à jour, les nouveaux sont ajoutés. Aucune perte de données.</span></span>
          </label>
          <label style="display:flex;gap:10px;align-items:flex-start;cursor:pointer;padding:10px 12px;border:1.5px solid var(--border);border-radius:10px">
            <input type="radio" name="cli-import-mode" value="replace" style="margin-top:2px">
            <span><strong style="color:var(--danger);font-size:13px">Remplacer</strong><br><span style="font-size:12px;color:var(--muted)">Supprime tous les clients existants puis importe le fichier. Action irréversible.</span></span>
          </label>
        </div>
        <div style="display:flex;gap:10px;justify-content:flex-end">
          <button type="button" class="btn btn-sec" onclick="closeCliImportModal()">Annuler</button>
          <button type="button" class="btn" id="cli-import-confirm" onclick="confirmCliImport()">Lancer l'import</button>
        </div>
      </div>
    </div>

    <section id="panel-machines" class="hidden">
      <div class="tabs" style="margin-bottom:14px">
        <button type="button" class="btn btn-sec mac-sub-btn active" data-macsub="mac-horaires">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          Horaires
        </button>
        <button type="button" class="btn btn-sec mac-sub-btn" data-macsub="mac-metrage">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
          Métrage total
        </button>
        <button type="button" class="btn btn-sec mac-sub-btn" data-macsub="mac-nom">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
          Renommer
        </button>
      </div>
      <div class="card">
        <div style="display:flex;align-items:flex-end;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:16px">
          <div style="flex:1;min-width:200px">
            <label class="sub" style="display:block;margin-bottom:6px">Machine</label>
            <select id="mac-select" style="width:100%;max-width:320px"></select>
          </div>
          <span class="hint" id="mac-hint"></span>
        </div>
        <div id="mac-horaires-wrap">
          <p class="sub" style="margin-top:-4px;margin-bottom:14px">Horaires par défaut du planning de production (lun–sam). Cohésio 2 : semaines paires / impaires.</p>
          <label id="mac-je-row" style="display:flex;align-items:center;gap:8px;padding:10px 12px;border:1px solid var(--border);border-radius:10px;background:var(--bg);cursor:pointer;margin-bottom:14px;font-size:13px">
            <input type="checkbox" id="mac-je">
            <span style="font-weight:600;color:var(--text)">Journée entière par défaut (00:00 → 23:59, 3 équipes 8 h)</span>
          </label>
          <p id="mac-je-hint" class="sub" style="margin-top:-8px;margin-bottom:14px;font-size:11px;color:var(--muted)">
            Quand activé, cette machine tourne en continu tous les jours travaillés. Les horaires ci-dessous ne sont utilisés que si un override journalier ou hebdomadaire les rétablit.
          </p>
          <div id="mac-horaires-weekly"></div>
          <div id="mac-horaires-parity" class="hidden" style="margin-top:16px"></div>
          <div style="display:flex;gap:8px;margin-top:16px;flex-wrap:wrap">
            <button type="button" class="btn" id="mac-hor-save">Enregistrer les horaires</button>
            <button type="button" class="btn btn-sec" id="mac-hor-reset">Réinitialiser (défauts machine)</button>
          </div>
        </div>
        <div id="mac-metrage-wrap" class="hidden">
          <p class="sub" style="margin-top:-4px;margin-bottom:14px">Compteur machine utilisé à la saisie production (début / fin de dossier). Mis à jour automatiquement à chaque saisie ; correction manuelle en cas d'erreur.</p>
          <div style="max-width:360px">
            <label class="sub" style="display:block;margin-bottom:6px">Métrage total actuel (m)</label>
            <input type="text" id="mac-metrage-inp" inputmode="decimal" placeholder="Ex. 1254300" autocomplete="off"
              style="width:100%;font-family:ui-monospace,monospace;font-size:15px">
            <p class="hint" id="mac-metrage-hint" style="margin-top:8px"></p>
          </div>
          <button type="button" class="btn" id="mac-metr-save" style="margin-top:14px">Enregistrer le métrage</button>
        </div>
        <div id="mac-nom-wrap" class="hidden">
          <p class="sub" style="margin-top:-4px;margin-bottom:14px">Nom affiché dans toutes les applications MySifa (planning, saisie production, planning RH…). Le changement prend effet immédiatement partout.</p>
          <div style="max-width:360px">
            <label class="sub" style="display:block;margin-bottom:6px">Nom de la machine</label>
            <input type="text" id="mac-nom-inp" maxlength="80" placeholder="Ex. Cohésio 1" autocomplete="off"
              style="width:100%;font-size:14px">
            <p class="hint" id="mac-nom-hint" style="margin-top:8px"></p>
          </div>
          <button type="button" class="btn" id="mac-nom-save" style="margin-top:14px">Enregistrer le nom</button>
        </div>
      </div>
    </section>

    <section id="panel-emplacements" class="hidden">
      <div class="card">
        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:16px">
          <div>
            <h2 style="margin:0 0 4px">Emplacements magasin</h2>
            <p class="sub" style="margin:0;font-size:12px">Référentiel des emplacements utilisé dans MyStock. <span id="empl-count" style="color:var(--accent);font-weight:700"></span></p>
          </div>
          <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
            <button type="button" class="btn btn-sec btn-sm" id="empl-export-csv">Exporter CSV</button>
            <button type="button" class="btn btn-sec btn-sm" id="empl-reload-csv">Recharger depuis CSV</button>
            <button type="button" class="btn btn-sm" id="empl-import-btn">Importer nouveau CSV</button>
            <input type="file" id="empl-import-input" accept=".csv" style="display:none">
          </div>
        </div>
        <div style="display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap">
          <input type="text" id="empl-search" placeholder="Filtrer les emplacements…" autocomplete="off"
            style="flex:1;min-width:180px;max-width:300px;padding:9px 12px;border-radius:10px;border:1.5px solid var(--border);background:var(--bg);color:var(--text);font-size:13px;font-family:inherit;outline:none;transition:border-color .15s,box-shadow .15s">
          <form id="empl-add-form" style="display:flex;gap:6px">
            <input type="text" id="empl-new-code" placeholder="Nouveau code (ex. A12)" maxlength="20" autocomplete="off"
              style="width:160px;padding:9px 12px;border-radius:10px;border:1.5px solid var(--border);background:var(--bg);color:var(--text);font-size:13px;font-family:ui-monospace,monospace;outline:none;transition:border-color .15s,box-shadow .15s;text-transform:uppercase">
            <button type="submit" class="btn btn-sm">Ajouter</button>
          </form>
        </div>
        <div id="empl-grid" style="display:flex;flex-wrap:wrap;gap:20px;align-items:flex-start;min-height:40px"></div>
        <p id="empl-empty" class="sub" style="display:none;margin:16px 0 4px;font-size:13px">Aucun emplacement trouvé.</p>
      </div>
    </section>

    <section id="panel-laizes" class="hidden">
      <div class="card">
        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:16px">
          <div>
            <h2 style="margin:0 0 4px">Laizes matières</h2>
            <p class="sub" style="margin:0;font-size:12px">Référentiel des laizes (en mm) utilisé pour les frontaux, glassines et complexes dans MyStock.</p>
          </div>
        </div>
        <form id="laizes-add-form" style="display:flex;gap:8px;align-items:end;flex-wrap:wrap;margin-bottom:18px;padding:14px;border:1px solid var(--border);border-radius:10px;background:var(--bg)">
          <div style="flex:1;min-width:140px">
            <label style="display:block;font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px">Valeur (mm)</label>
            <input type="number" id="laizes-add-mm" min="1" step="1" required placeholder="Ex. 600"
              style="width:100%;padding:9px 12px;border-radius:8px;border:1.5px solid var(--border);background:var(--card);color:var(--text);font-size:14px;outline:none;transition:border-color .15s">
          </div>
          <div style="flex:1;min-width:140px">
            <label style="display:block;font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px">Label (optionnel)</label>
            <input type="text" id="laizes-add-label" placeholder="Auto : « 600 mm »"
              style="width:100%;padding:9px 12px;border-radius:8px;border:1.5px solid var(--border);background:var(--card);color:var(--text);font-size:14px;outline:none">
          </div>
          <div style="width:90px">
            <label style="display:block;font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px">Ordre</label>
            <input type="number" id="laizes-add-ordre" step="10" value="0"
              style="width:100%;padding:9px 12px;border-radius:8px;border:1.5px solid var(--border);background:var(--card);color:var(--text);font-size:14px;outline:none">
          </div>
          <button type="submit" class="btn">Ajouter</button>
        </form>
        <div id="laizes-list" style="display:flex;flex-direction:column;gap:8px"></div>
        <p id="laizes-empty" class="sub" style="display:none;margin:16px 0 4px;font-size:13px">Aucune laize définie.</p>
      </div>
    </section>

    <section id="panel-importations" class="hidden">
      <div class="card">
        <div style="margin-bottom:16px">
          <h2 style="margin:0 0 4px">Importations</h2>
          <p class="sub" style="margin:0;font-size:12px">Quantités de matière (m²) contenues dans un container standard. Utilisées côté MyStock → Valorisation pour afficher le coût EUR/m² à partir du coût container.</p>
        </div>
        <div id="importations-loading" class="sub" style="padding:12px 0;font-size:13px">Chargement…</div>
        <form id="importations-form" style="display:none;flex-direction:column;gap:16px;max-width:520px">
          <div>
            <label for="imp-qte-full" style="display:block;font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px">Quantité matière dans un container complet (m²)</label>
            <input type="number" id="imp-qte-full" min="0" step="0.01" placeholder="Ex. 12000"
              style="width:100%;padding:10px 12px;border-radius:8px;border:1.5px solid var(--border);background:var(--bg);color:var(--text);font-size:14px;outline:none;transition:border-color .15s;font-variant-numeric:tabular-nums">
          </div>
          <div>
            <label for="imp-qte-half" style="display:block;font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px">Quantité matière dans un demi-container (m²)</label>
            <input type="number" id="imp-qte-half" min="0" step="0.01" placeholder="Ex. 6000"
              style="width:100%;padding:10px 12px;border-radius:8px;border:1.5px solid var(--border);background:var(--bg);color:var(--text);font-size:14px;outline:none;transition:border-color .15s;font-variant-numeric:tabular-nums">
          </div>
          <div style="display:flex;gap:8px;align-items:center">
            <button type="submit" class="btn" id="imp-save-btn">Enregistrer</button>
            <span id="imp-status" class="sub" style="font-size:12px"></span>
          </div>
        </form>
        <div id="importations-error" class="sub" style="display:none;color:var(--danger);font-size:13px;padding:12px 0"></div>
      </div>
    </section>

    <section id="panel-bridge" class="hidden">
      <div class="card">
        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:12px">
          <div>
            <h2 style="margin:0 0 4px">Appairage matières — MyStock ↔ Coûts matières</h2>
            <p class="sub" style="margin:0;font-size:12px">Rapprochement des références opérationnelles (MyStock) avec les matières du module Coûts matières. Un appairage permet la synchronisation automatique des prix dans les deux sens.</p>
          </div>
          <div style="display:flex;gap:8px;align-items:center">
            <button type="button" class="btn btn-sec" id="bridge-refresh" title="Recharger">Actualiser</button>
          </div>
        </div>

        <div id="bridge-summary" class="sub" style="display:flex;flex-wrap:wrap;gap:16px;padding:12px 14px;background:var(--bg);border:1px solid var(--border);border-radius:10px;margin-bottom:16px;font-size:12px">
          <span>Chargement…</span>
        </div>

        <div style="margin-bottom:8px;font-size:12px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px">Matières MyStock non appairées</div>
        <div id="bridge-orphans-mp" style="display:flex;flex-direction:column;gap:6px"></div>
        <p id="bridge-orphans-mp-empty" class="sub" style="display:none;margin:12px 0 0;font-size:13px">Toutes les matières MyStock avec un rôle pricing sont déjà appairées.</p>

        <div style="margin:22px 0 8px;font-size:12px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px">Matières Coûts matières sans référence MyStock</div>
        <div id="bridge-orphans-mc" style="display:flex;flex-direction:column;gap:6px"></div>
        <p id="bridge-orphans-mc-empty" class="sub" style="display:none;margin:12px 0 0;font-size:13px">Toutes les matières Coûts matières sont référencées côté MyStock.</p>
      </div>
    </section>

    <section id="panel-operations" class="hidden">
      <div class="card">
        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:12px">
          <h2 style="margin:0">Codes opération (calage, arrêt, production…)</h2>
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <button type="button" class="btn btn-sec" onclick="importOpsJson()">Sync. operations.json</button>
            <button type="button" class="btn" onclick="openOpForm()">+ Ajouter un code</button>
          </div>
        </div>
        <p class="sub" style="margin-top:-4px;margin-bottom:14px">Référentiel utilisé par la saisie production et les imports. Modifiable ici ou via Database Viewer → table <code>operation_codes</code>.</p>
        <div id="op-form-wrap" class="hidden op-form-panel">
          <h3 id="op-form-title">Nouveau code</h3>
          <div class="form-grid" style="grid-template-columns:repeat(auto-fill,minmax(140px,1fr))">
            <input type="text" id="op-code" placeholder="Code (ex. 82)" inputmode="numeric" maxlength="3">
            <input type="text" id="op-label" placeholder="Libellé">
            <select id="op-severity"><option value="info">info</option><option value="attention">attention</option><option value="critique">critique</option></select>
            <select id="op-category"></select>
            <label style="display:flex;align-items:center;gap:8px;font-size:12px;color:var(--text2)"><input type="checkbox" id="op-required"> Obligatoire</label>
          </div>
          <div style="display:flex;gap:8px;margin-top:12px;flex-wrap:wrap">
            <button type="button" class="btn" onclick="saveOpForm()">Enregistrer</button>
            <button type="button" class="btn btn-sec" onclick="closeOpForm()">Annuler</button>
          </div>
        </div>
        <div class="op-toolbar">
          <input type="search" id="op-filter" class="op-filter" placeholder="Filtrer (code, libellé, catégorie…)" oninput="renderOpList()">
        </div>
        <div id="op-list"><p style="color:var(--muted);font-size:13px">Chargement…</p></div>
      </div>
    </section>

    <section id="panel-maintenance" class="hidden">
    <div class="tabs" style="margin-bottom:14px">
      <button type="button" class="btn btn-sec sub-tab-btn active" data-maintsub="maint-subtab-codes">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
        Codes
      </button>
      <button type="button" class="btn btn-sec sub-tab-btn" data-maintsub="maint-subtab-libres">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
        Interventions libres
      </button>
      <button type="button" class="btn btn-sec sub-tab-btn" data-maintsub="maint-subtab-alertes">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>
        Alertes
      </button>
    </div>
      <div id="maint-subtab-codes" class="maint-subtab">
      <div class="card">
        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:12px">
          <h2 style="margin:0">Codes maintenance</h2>
          <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
            <button type="button" class="btn" onclick="openMaintForm()">+ Ajouter un code</button>
          </div>
        </div>
        <p class="sub" style="margin-top:-4px;margin-bottom:14px">Référentiel des codes d'opérations de maintenance regroupés en trois catégories : Contrôles, Nettoyage et Interventions.</p>
        <div id="maint-form-wrap" class="hidden op-form-panel">
          <h3 id="maint-form-title">Nouveau code</h3>
          <div class="form-grid" style="grid-template-columns:repeat(auto-fill,minmax(140px,1fr))">
            <input type="text" id="maint-code" placeholder="Code (ex. 10)" inputmode="numeric" maxlength="4">
            <input type="text" id="maint-label" placeholder="Libellé">
            <select id="maint-niveau">
              <option value="1">N1</option>
              <option value="2">N2</option>
              <option value="3">N3</option>
            </select>
            <select id="maint-categorie">
              <option value="controles">Contrôles</option>
              <option value="entretien">Nettoyage</option>
              <option value="remplacements">Interventions</option>
            </select>
            <input type="text" id="maint-intervalle" placeholder="Intervalle (ex. Hebdo, 30 jours, 6 mois)" maxlength="80">
            <input type="text" id="maint-metrage-ref" placeholder="Réf. métrage (ex. 5000 m, 10 km)" maxlength="80">
          </div>
          <div style="display:flex;gap:8px;margin-top:12px;flex-wrap:wrap">
            <button type="button" class="btn" onclick="saveMaintForm()">Enregistrer</button>
            <button type="button" class="btn btn-sec" onclick="closeMaintForm()">Annuler</button>
          </div>
          <div id="maint-form-docs" style="display:none;margin-top:18px;padding-top:16px;border-top:1px solid var(--border)">
            <div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:12px;gap:12px">
              <div>
                <div style="font-size:12px;font-weight:700;color:var(--text);text-transform:uppercase;letter-spacing:.5px">Documents attaches</div>
                <div id="maint-form-docs-hint" style="font-size:11px;color:var(--muted);margin-top:2px">Fichiers explicatifs consultes par les operateurs.</div>
              </div>
              <span style="font-size:11px;color:var(--muted);white-space:nowrap">20 Mo max</span>
            </div>
            <input type="file" id="maint-form-doc-file" style="position:absolute;left:-9999px;top:auto;width:1px;height:1px;overflow:hidden" onchange="_maintOnDocFileChange()">
            <div id="maint-form-docs-list" style="display:flex;flex-direction:column;gap:6px;margin-bottom:12px">
              <p style="color:var(--muted);font-size:12px;font-style:italic">Chargement…</p>
            </div>
            <button type="button" class="maint-doc-add-btn" id="maint-form-doc-add-btn" onclick="_maintTriggerDocPicker()">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              <span>Ajouter un fichier</span>
            </button>
          </div>
        </div>
        <div class="op-toolbar">
          <input type="search" id="maint-filter" class="op-filter" placeholder="Filtrer (code, libellé, niveau, catégorie…)" oninput="renderMaintList()">
        </div>
        <div id="maint-list"><p style="color:var(--muted);font-size:13px">Chargement…</p></div>
      </div>
      </div>
      <div id="maint-subtab-alertes" class="maint-subtab" style="display:none">
        <div class="card">
          <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:12px">
            <h2 style="margin:0">Alertes maintenance</h2>
            <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
              <button type="button" class="btn btn-sec" onclick="openAlertSettingsModal()" title="Placement, taille des alertes, et blocage de la production.">Réglages</button>
              <button type="button" class="btn" onclick="disableAllAlerts()" title="Bascule toutes les alertes en inactif. Aucune n'est supprimée — c'est un kill switch d'urgence.">Désactiver toutes les alertes</button>
              <button type="button" class="btn" onclick="openNewAlertModal()">+ Nouvelle alerte</button>
            </div>
          </div>
          <p class="sub" style="margin-top:-4px;margin-bottom:14px">Messages et formulaires affichés aux opérateurs lors de tâches de maintenance (contrôles qualité, vérifications, rappels…). Chaque alerte est créée manuellement depuis « + Nouvelle alerte » puis paramétrée (déclencheur, cible, formulaire de validation).</p>
          <div class="op-toolbar" style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:10px">
            <input type="search" id="alerts-filter-q" class="op-filter" placeholder="Filtrer par nom d'alerte…" oninput="renderAlertsList()">
          </div>
          <div id="alerts-list"><p style="color:var(--muted);font-size:13px">Chargement…</p></div>
        </div>
      </div>
      <!-- v182 Lot 2 : Sous-onglet Interventions libres -->
      <div id="maint-subtab-libres" class="maint-subtab" style="display:none">
        <div class="card">
          <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:12px">
            <h2 style="margin:0">Interventions libres</h2>
            <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
              <button type="button" class="btn btn-sec" id="libres-merge-btn" disabled onclick="libresMergeSelected()" title="Fusionne les 2 titres selectionnes en un seul (les saisies passees sont reaffectees).">Fusionner sélection</button>
              <span id="libres-selection-count" style="font-size:11px;color:var(--muted)"></span>
            </div>
          </div>
          <p class="sub" style="margin-top:-4px;margin-bottom:14px">Titres saisis ponctuellement par les operateurs, hors catalogue. Coche 2 lignes pour les fusionner ; renomme depuis la ligne pour uniformiser la terminologie ; archive uniquement les titres sans saisie associee.</p>
          <div class="op-toolbar">
            <input type="search" id="libres-filter" class="op-filter" placeholder="Filtrer (titre, code…)" oninput="renderLibresList()">
          </div>
          <div id="libres-list"><p style="color:var(--muted);font-size:13px">Chargement…</p></div>
        </div>
      </div>
    </section>

    <section id="panel-updates" class="hidden">
      <div class="card">
        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:16px">
          <h2 style="margin:0">Annonces de mise à jour</h2>
          <button type="button" class="btn" id="upd-new-btn" onclick="openNewUpdateModal()">+ Nouvelle annonce</button>
        </div>
        <p class="sub" style="margin-top:-8px;margin-bottom:16px">Gérez les messages affichés aux utilisateurs lors de leur prochaine connexion. Cliquez sur une ligne pour voir qui l'a lu.</p>
        <div id="upd-list"><p style="color:var(--muted);font-size:13px">Chargement…</p></div>
      </div>
    </section>

    <section id="panel-audit" class="hidden">
      <div class="card">
        <div style="display:flex;align-items:center;justify-content:space-between;
                gap:12px;margin-bottom:16px;flex-wrap:wrap">
          <div style="font-size:15px;font-weight:700;color:var(--text)">Journal des actions</div>
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <input type="text" id="audit-search"
                   placeholder="Rechercher (utilisateur, objet, requête Google…)"
                   style="background:var(--bg);border:1px solid var(--border);border-radius:8px;
                          padding:7px 12px;color:var(--text);font-size:12px;width:200px;
                          font-family:inherit;outline:none"
                   oninput="debouncedAuditSearch()">
            <select id="audit-filter-module" onchange="loadAuditLogs()"
                    style="background:var(--bg);border:1px solid var(--border);border-radius:8px;
                           padding:7px 10px;color:var(--text);font-size:12px;font-family:inherit">
              <option value="">Tous les modules</option>
              <option value="planning">Planning</option>
              <option value="fabrication">Fabrication</option>
              <option value="stock">Stock</option>
              <option value="expe">Expéditions</option>
              <option value="rh">RH</option>
              <option value="settings">Paramètres</option>
              <option value="auth">Auth</option>
              <option value="portal">Portail</option>
            </select>
            <select id="audit-filter-action" onchange="loadAuditLogs()"
                    style="background:var(--bg);border:1px solid var(--border);border-radius:8px;
                           padding:7px 10px;color:var(--text);font-size:12px;font-family:inherit">
              <option value="">Toutes les actions</option>
              <option value="CREATE">Création</option>
              <option value="UPDATE">Modification</option>
              <option value="DELETE">Suppression</option>
              <option value="CLOSE">Clôture</option>
              <option value="VALIDATE">Validation</option>
              <option value="REORDER">Réorganisation</option>
              <option value="SEARCH">Recherche</option>
            </select>
          </div>
        </div>
        <div id="audit-table-wrap" style="overflow-x:auto">
          <div id="audit-loading" style="color:var(--muted);font-size:13px;padding:20px 0">
            Chargement…
          </div>
        </div>
        <div id="audit-pagination"
             style="display:flex;align-items:center;justify-content:space-between;
                    margin-top:12px;font-size:12px;color:var(--muted)"></div>
      </div>
    </section>

    <section id="panel-fsc" class="hidden">
      <div class="fsc-toolbar">
        <div class="fsc-toolbar-dates">
          <input type="date" id="fsc-du" class="fsc-date-inp" onchange="loadFscRegistre()" aria-label="Date de début">
          <span class="fsc-range-sep">au</span>
          <input type="date" id="fsc-au" class="fsc-date-inp" onchange="loadFscRegistre()" aria-label="Date de fin">
        </div>
        <button type="button" class="btn btn-sec" onclick="exportFscCsv()">Exporter CSV</button>
      </div>
      <div id="fsc-kpi-grid" class="fsc-kpi-grid"></div>
      <div class="card" style="margin-bottom:16px">
        <h2 class="fsc-section-title">Réceptions FSC certifiées</h2>
        <div id="fsc-recep-wrap" class="table-wrap">
          <p style="color:var(--muted);font-size:13px;padding:12px 0">Chargement…</p>
        </div>
      </div>
      <div class="card">
        <h2 class="fsc-section-title">Dossiers de production FSC</h2>
        <div id="fsc-dossiers-wrap" class="table-wrap">
          <p style="color:var(--muted);font-size:13px;padding:12px 0">Chargement…</p>
        </div>
      </div>
    </section>

    <!-- ═══════════════════════ PANEL API ═══════════════════════ -->
    <section id="panel-api" class="hidden">
      <div style="max-width:860px">
        <div style="margin-bottom:24px">
          <div style="font-size:18px;font-weight:700;color:var(--text);margin-bottom:6px">Clés API</div>
          <div style="font-size:13px;color:var(--muted)">
            Générez des clés pour permettre à des scripts externes (pont Access) d'accéder à MySifa.
            La clé secrète n'est affichée qu'une seule fois à la création — conservez-la.
          </div>
        </div>

        <!-- Formulaire création -->
        <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:24px">
          <div style="font-size:13px;font-weight:600;color:var(--text);margin-bottom:14px;text-transform:uppercase;letter-spacing:.5px">Nouvelle clé</div>
          <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end">
            <div style="flex:1;min-width:200px">
              <label style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:6px">Nom</label>
              <input id="ak-name" type="text" placeholder="ex: Pont Access Usine"
                style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px 14px;color:var(--text);font-size:13px;outline:none;font-family:inherit"
                onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'">
            </div>
            <button class="btn btn-accent" onclick="createApiKey()" style="white-space:nowrap">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="margin-right:6px"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              Générer la clé
            </button>
          </div>
        </div>

        <!-- Alerte clé générée (affichée une seule fois) -->
        <div id="ak-reveal" style="display:none;background:rgba(34,211,238,.1);border:1px solid var(--accent);border-radius:12px;padding:16px 20px;margin-bottom:24px">
          <div style="font-size:12px;font-weight:600;color:var(--accent);margin-bottom:8px;text-transform:uppercase;letter-spacing:.5px">
            Copiez cette clé maintenant — elle ne sera plus affichée
          </div>
          <div style="display:flex;gap:10px;align-items:center">
            <code id="ak-reveal-value" style="flex:1;font-family:monospace;font-size:13px;color:var(--text);word-break:break-all;background:var(--bg);padding:10px 14px;border-radius:8px;border:1px solid var(--border)"></code>
            <button class="btn btn-ghost" onclick="copyApiKey()" title="Copier" style="border:1px solid var(--border);padding:10px 12px">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
            </button>
          </div>
        </div>

        <!-- Liste des clés -->
        <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden">
          <div style="padding:16px 20px;border-bottom:1px solid var(--border);font-size:13px;font-weight:600;color:var(--text)">Clés existantes</div>
          <div id="ak-list" style="padding:8px 0">
            <div style="padding:24px;text-align:center;color:var(--muted);font-size:13px">Chargement…</div>
          </div>
        </div>
      </div>
    </section>

    <section id="panel-dashboards" class="hidden">
      <div id="settings-tab-content"></div>
    </section>

    <section id="panel-promote" class="hidden">
      <div class="card" style="margin-bottom:16px">
        <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:14px">
          <div>
            <div style="font-size:17px;font-weight:700;color:var(--text)">Promouvoir v1 → v2</div>
            <div style="font-size:12px;color:var(--muted);margin-top:4px">Bascule en production les commits déjà en place sur v1.</div>
          </div>
          <button type="button" class="btn btn-sec" id="pr-refresh-btn" onclick="loadPromoteStatus()" style="font-size:12px">
            Rafraîchir
          </button>
        </div>

        <div id="pr-status" style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:18px">
          <div style="background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px 14px;flex:1;min-width:140px">
            <div style="font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px">v2 actuelle</div>
            <div id="pr-v2-version" style="font-size:15px;font-weight:700;color:var(--text);font-family:'SFMono-Regular',Menlo,monospace">…</div>
            <div id="pr-v2-head" style="font-size:11px;color:var(--muted);font-family:'SFMono-Regular',Menlo,monospace;margin-top:2px">…</div>
          </div>
          <div style="background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px 14px;flex:1;min-width:140px">
            <div style="font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px">Prochaine version</div>
            <div id="pr-next-version" style="font-size:15px;font-weight:700;color:var(--accent);font-family:'SFMono-Regular',Menlo,monospace">…</div>
            <div id="pr-origin-head" style="font-size:11px;color:var(--muted);font-family:'SFMono-Regular',Menlo,monospace;margin-top:2px">…</div>
          </div>
        </div>

        <div style="font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px">Commits en avance sur v2</div>
        <div id="pr-commits" style="background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:8px;margin-bottom:18px;max-height:240px;overflow:auto">
          <div style="padding:24px;text-align:center;color:var(--muted);font-size:13px">Chargement…</div>
        </div>

        <div style="margin-bottom:14px">
          <label for="pr-notes" style="font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;display:block;margin-bottom:6px">Notes de release (optionnelles — postées en annonce si remplies)</label>
          <textarea id="pr-notes" placeholder="ex. Correction du planning sur mobile, nouvelle vue Compta&hellip;" style="width:100%;min-height:70px;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px 14px;color:var(--text);font-size:13px;font-family:inherit;resize:vertical"></textarea>
        </div>

        <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
          <button type="button" id="pr-go-btn" class="btn btn-accent" onclick="runPromote()" disabled style="font-size:14px;padding:11px 22px;font-weight:700">
            Promouvoir maintenant
          </button>
          <span id="pr-blocked-reason" style="font-size:12px;color:var(--warn)"></span>
        </div>
      </div>

      <div class="card" id="pr-output-card" style="display:none">
        <div style="font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px">Sortie du script</div>
        <pre id="pr-output" style="background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:14px;font-size:12px;line-height:1.5;color:var(--text2);font-family:'SFMono-Regular',Menlo,monospace;max-height:420px;overflow:auto;margin:0;white-space:pre-wrap;word-break:break-word"></pre>
      </div>

      <!-- v2 : bloc Synchroniser DB v2 → v1 (déplacé depuis Maintenance) -->
      <div class="card" style="margin-top:16px">
        <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:14px">
          <div>
            <div style="font-size:17px;font-weight:700;color:var(--text)">Synchroniser DB v2 → v1</div>
            <div style="font-size:12px;color:var(--muted);margin-top:4px">Aligner la base de staging sur la production pour repartir d'un état réel.</div>
          </div>
          <span id="db-sync-status" style="font-size:11px;color:var(--muted)"></span>
        </div>

        <!-- Bandeau warn : cas d'usage + risque -->
        <div style="background:rgba(251,191,36,.10);border:1px solid rgba(251,191,36,.40);border-left:4px solid var(--warn);border-radius:10px;padding:12px 16px;margin-bottom:16px;color:var(--text);font-size:13px;line-height:1.55">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;font-weight:800;color:var(--warn);text-transform:uppercase;letter-spacing:.4px;font-size:11px">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            <span>Attention — action irréversible</span>
          </div>
          <div>
            Cette action écrase intégralement la DB v1 avec la copie live de v2. Utilisée pour aligner l'environnement de test sur la production réelle. Toutes les données de test créées sur v1 depuis la dernière resync (auto la nuit) seront irréversiblement perdues.
          </div>
        </div>

        <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
          <button type="button" id="db-sync-btn" class="btn btn-danger-solid" onclick="syncDbV1()" style="font-size:14px;padding:11px 22px;font-weight:700;background:var(--danger);color:#fff;border:1px solid var(--danger)">
            Synchroniser DB v2 → v1
          </button>
          <span style="font-size:12px;color:var(--muted)">Un backup pré-resync est conservé automatiquement · v1 redémarrera dans ~15s après le lancement</span>
        </div>
      </div>
    </section>

    <section id="panel-printers" class="hidden">
      <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:16px">
        <div>
          <div style="font-size:17px;font-weight:700;color:var(--text)">Imprimantes</div>
          <div style="font-size:12px;color:var(--muted);margin-top:4px">
            Configure les imprimantes réseau et locales (USB/LPT) de l'usine, et les agents qui font le pont avec MySifa.
          </div>
        </div>
      </div>

      <!-- Bandeau : lien vers le wizard "Comment connecter mon imprimante" -->
      <div style="margin-bottom:16px;background:linear-gradient(135deg, rgba(240,165,0,0.08), rgba(45,111,187,0.05));border:1px solid var(--border);border-radius:12px;padding:14px 18px;display:flex;align-items:center;gap:14px;flex-wrap:wrap">
        <div style="width:40px;height:40px;background:var(--accent);border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0;color:#fff">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
        </div>
        <div style="flex:1;min-width:200px">
          <div style="font-size:13px;font-weight:700;color:var(--text);margin-bottom:2px">Première fois ? On t'accompagne pas à pas.</div>
          <div style="font-size:12px;color:var(--muted)">Assistant guidé pour connecter une imprimante réseau ou locale (USB / LPT) — 3 étapes, prise en main de A à Z.</div>
        </div>
        <button class="btn btn-accent" onclick="prWizardStart()" style="padding:10px 18px;font-size:13px;font-weight:700;white-space:nowrap;flex-shrink:0">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="margin-right:6px;vertical-align:-2px"><polyline points="9 18 15 12 9 6"/></svg>
          Comment connecter mon imprimante à MySifa
        </button>
      </div>

      <!-- Sous-onglets Imprimantes / Templates / Agents -->
      <div style="display:flex;gap:6px;margin-bottom:16px;border-bottom:1px solid var(--border)">
        <button type="button" class="pr-sub active" data-prsub="imp" onclick="prSetSub('imp')" style="background:transparent;border:none;padding:10px 14px;color:var(--text);font-size:13px;font-weight:600;cursor:pointer;border-bottom:2px solid var(--accent);font-family:inherit">Imprimantes</button>
        <button type="button" class="pr-sub" data-prsub="tpl" onclick="prSetSub('tpl')" style="background:transparent;border:none;padding:10px 14px;color:var(--muted);font-size:13px;font-weight:600;cursor:pointer;border-bottom:2px solid transparent;font-family:inherit">Templates</button>
        <button type="button" class="pr-sub" data-prsub="ag" onclick="prSetSub('ag')" style="background:transparent;border:none;padding:10px 14px;color:var(--muted);font-size:13px;font-weight:600;cursor:pointer;border-bottom:2px solid transparent;font-family:inherit">Agents locaux</button>
      </div>

      <!-- Sous-panneau : Imprimantes -->
      <div id="pr-panel-imp">
        <div style="display:flex;justify-content:flex-end;margin-bottom:12px">
          <button class="btn btn-accent" onclick="prEditImprimante(null)" style="padding:8px 14px;font-size:13px">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="margin-right:6px;vertical-align:-2px"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            Nouvelle imprimante
          </button>
        </div>
        <div id="pr-imp-list" style="display:flex;flex-direction:column;gap:10px">
          <div style="padding:24px;text-align:center;color:var(--muted);font-size:13px">Chargement…</div>
        </div>
      </div>

      <!-- Sous-panneau : Templates -->
      <div id="pr-panel-tpl" style="display:none">
        <div id="pr-tpl-list" style="display:flex;flex-direction:column;gap:10px">
          <div style="padding:24px;text-align:center;color:var(--muted);font-size:13px">Chargement…</div>
        </div>
      </div>

      <!-- Sous-panneau : Agents locaux -->
      <div id="pr-panel-ag">
        <div id="pr-ag-panel" style="display:none">
          <div style="display:flex;justify-content:flex-end;margin-bottom:12px">
            <button class="btn btn-accent" onclick="prCreateAgent()" style="padding:8px 14px;font-size:13px">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="margin-right:6px;vertical-align:-2px"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              Nouvel agent
            </button>
          </div>
          <div id="pr-ag-token-reveal" style="display:none;background:rgba(34,211,238,.1);border:1px solid var(--accent);border-radius:12px;padding:16px 20px;margin-bottom:16px">
            <div style="font-size:12px;font-weight:600;color:var(--accent);margin-bottom:8px;text-transform:uppercase;letter-spacing:.5px">
              Copiez ce token — il ne sera plus affiché
            </div>
            <div style="display:flex;gap:10px;align-items:center">
              <code id="pr-ag-token-value" style="flex:1;font-family:monospace;font-size:13px;color:var(--text);word-break:break-all;background:var(--bg);padding:10px 14px;border-radius:8px;border:1px solid var(--border)"></code>
              <button class="btn btn-ghost" onclick="prCopyToken()" style="border:1px solid var(--border);padding:10px 12px">Copier</button>
            </div>
          </div>
          <div id="pr-ag-list" style="display:flex;flex-direction:column;gap:10px">
            <div style="padding:24px;text-align:center;color:var(--muted);font-size:13px">Chargement…</div>
          </div>
        </div>
      </div>

      <!-- Modal imprimante -->
      <div id="pr-imp-modal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:900;align-items:center;justify-content:center;padding:20px" onclick="if(event.target===this)prCloseModal()">
        <div style="background:var(--card);border:1px solid var(--border);border-radius:16px;padding:24px;width:min(640px,95vw);max-height:90vh;overflow:auto">
          <h2 id="pr-imp-modal-title" style="margin:0 0 18px;font-size:17px">Nouvelle imprimante</h2>
          <div class="form-grid" style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px">
            <div style="grid-column:span 2">
              <label class="pr-lbl">Nom</label>
              <input id="pr-f-nom" type="text" class="pr-inp" placeholder="Ex : Zebra Réception matière">
            </div>
            <div>
              <label class="pr-lbl">Poste / atelier</label>
              <input id="pr-f-poste" type="text" class="pr-inp" placeholder="Ex : Réception">
            </div>
            <div>
              <label class="pr-lbl">Agent local</label>
              <select id="pr-f-agent" class="pr-inp"><option value="">Aucun</option></select>
            </div>
            <div style="grid-column:span 2">
              <label class="pr-lbl">Type de connexion</label>
              <div style="display:flex;gap:16px;align-items:center;font-size:13px;color:var(--text);padding:6px 0">
                <label style="display:flex;gap:6px;align-items:center;cursor:pointer">
                  <input type="radio" name="pr-f-type" value="tcp_ip" id="pr-f-type-tcp" checked onchange="prToggleTypeConnexion()">
                  Réseau (TCP/IP)
                </label>
                <label style="display:flex;gap:6px;align-items:center;cursor:pointer">
                  <input type="radio" name="pr-f-type" value="windows_local" id="pr-f-type-win" onchange="prToggleTypeConnexion()">
                  Locale (USB / LPT via PC hôte)
                </label>
              </div>
            </div>
            <div id="pr-f-tcp-ip-row">
              <label class="pr-lbl">Adresse IP</label>
              <input id="pr-f-ip" type="text" class="pr-inp" placeholder="192.168.1.42">
            </div>
            <div id="pr-f-tcp-port-row">
              <label class="pr-lbl">Port</label>
              <input id="pr-f-port" type="number" class="pr-inp" value="9100">
            </div>
            <div id="pr-f-queue-row" style="grid-column:span 2;display:none">
              <label class="pr-lbl">Nom de la queue Windows (côté PC hôte)</label>
              <input id="pr-f-queue" type="text" class="pr-inp" placeholder="Ex : Zebra QL-800 ou ZDesigner GK420t">
              <div style="font-size:11px;color:var(--muted);margin-top:4px">Exact nom tel qu'il apparaît dans <em>Panneau de configuration &gt; Périphériques et imprimantes</em> sur le PC hôte. L'agent MySifa doit être installé sur ce PC (voir <code>tools/print_agent/install_agent_windows.ps1</code>).</div>
            </div>
            <div>
              <label class="pr-lbl">Langage</label>
              <select id="pr-f-langage" class="pr-inp">
                <option value="zpl">ZPL — Zebra</option>
                <option value="epl">EPL — vieilles Zebra</option>
                <option value="escpos">ESC/POS — Brother, tickets</option>
              </select>
            </div>
            <div>
              <label class="pr-lbl">DPI</label>
              <select id="pr-f-dpi" class="pr-inp">
                <option value="203">203 dpi (standard)</option>
                <option value="300">300 dpi</option>
                <option value="600">600 dpi</option>
              </select>
            </div>
            <div>
              <label class="pr-lbl">Largeur (mm)</label>
              <input id="pr-f-largeur" type="number" class="pr-inp" value="102">
            </div>
            <div>
              <label class="pr-lbl">Hauteur (mm)</label>
              <input id="pr-f-hauteur" type="number" class="pr-inp" value="152">
            </div>
            <div style="grid-column:span 2">
              <label class="pr-lbl">Note (optionnel)</label>
              <input id="pr-f-note" type="text" class="pr-inp">
            </div>
          </div>
          <div style="display:flex;gap:8px;justify-content:space-between;margin-top:18px">
            <button id="pr-f-del" class="btn btn-ghost" style="color:var(--danger);display:none" onclick="prDeleteImprimante()">Supprimer</button>
            <div style="display:flex;gap:8px;margin-left:auto">
              <button class="btn btn-ghost" onclick="prCloseModal()">Annuler</button>
              <button class="btn btn-accent" onclick="prSaveImprimante()">Enregistrer</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Modal template -->
      <div id="pr-tpl-modal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:900;align-items:center;justify-content:center;padding:20px" onclick="if(event.target===this)prCloseTplModal()">
        <div style="background:var(--card);border:1px solid var(--border);border-radius:16px;padding:24px;width:min(1200px,97vw);max-height:92vh;overflow:auto">
          <h2 id="pr-tpl-modal-title" style="margin:0 0 18px;font-size:17px">Éditer le template</h2>

          <!-- Galerie de modèles de départ (visible uniquement à la création) -->
          <div id="pr-tpl-gallery-row" style="margin-bottom:14px;display:none">
            <label class="pr-lbl">Partir d'un modèle prédéfini</label>
            <select id="pr-tpl-gallery" class="pr-inp" onchange="prLoadFromGallery()" style="width:100%">
              <option value="">— Vide (je pars de zéro) —</option>
            </select>
            <div id="pr-tpl-gallery-desc" style="font-size:11px;color:var(--muted);margin-top:4px"></div>
          </div>

          <!-- Ligne du haut : nom + usage -->
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px">
            <div>
              <label class="pr-lbl">Nom</label>
              <input id="pr-tpl-nom" type="text" class="pr-inp">
            </div>
            <div>
              <label class="pr-lbl">Usage métier</label>
              <select id="pr-tpl-usage" class="pr-inp"></select>
            </div>
          </div>

          <div style="margin-bottom:6px">
            <label class="pr-lbl">Placeholders disponibles (clique pour insérer)</label>
            <div id="pr-tpl-placeholders" style="display:flex;flex-wrap:wrap;gap:6px;padding:8px;background:var(--bg);border:1px solid var(--border);border-radius:8px;font-size:11px"></div>
          </div>

          <!-- Corps : éditeur à gauche, aperçu à droite -->
          <div style="display:grid;grid-template-columns:1.3fr 1fr;gap:14px;margin-bottom:12px">

            <!-- Éditeur ZPL -->
            <div>
              <label class="pr-lbl">Contenu (ZPL / EPL / ESC-POS)</label>
              <textarea id="pr-tpl-contenu" class="pr-inp" spellcheck="false" style="min-height:420px;font-family:'SFMono-Regular',Menlo,monospace;font-size:12px;line-height:1.5;white-space:pre;resize:vertical;width:100%"></textarea>
              <div style="font-size:11px;color:var(--muted);margin-top:4px">
                Placeholders : <code>{{champ}}</code>, <code>{{barcode:champ,CODE128,140}}</code>, <code>{{qrcode:champ}}</code>, <code>{{now:%d/%m/%Y}}</code>.
              </div>
            </div>

            <!-- Aperçu WYSIWYG -->
            <div>
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
                <label class="pr-lbl" style="margin:0">Aperçu (rendu réel via labelary.com)</label>
                <button type="button" class="btn btn-ghost" onclick="prTplRefreshPreview()" style="padding:4px 10px;font-size:11px">
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="margin-right:4px;vertical-align:-1px"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
                  Actualiser
                </button>
              </div>
              <!-- Dimensions pour l'aperçu (ajustables) -->
              <div style="display:flex;gap:6px;align-items:center;margin-bottom:6px;font-size:11px;color:var(--muted)">
                <span>Format :</span>
                <input type="number" id="pr-tpl-prev-w" value="102" min="20" max="300" style="width:60px;padding:4px 6px;border:1px solid var(--border);border-radius:4px;background:var(--bg);color:var(--text);font-size:11px"> ×
                <input type="number" id="pr-tpl-prev-h" value="152" min="20" max="300" style="width:60px;padding:4px 6px;border:1px solid var(--border);border-radius:4px;background:var(--bg);color:var(--text);font-size:11px"> mm
                @
                <select id="pr-tpl-prev-dpi" style="padding:4px 6px;border:1px solid var(--border);border-radius:4px;background:var(--bg);color:var(--text);font-size:11px">
                  <option value="203">203 dpi</option>
                  <option value="300">300 dpi</option>
                  <option value="600">600 dpi</option>
                </select>
              </div>
              <div id="pr-tpl-preview-box" style="background:#fff;border:1px solid var(--border);border-radius:8px;padding:8px;min-height:420px;display:flex;align-items:center;justify-content:center;overflow:auto">
                <div id="pr-tpl-preview-placeholder" style="color:var(--muted);font-size:12px;text-align:center;padding:20px">
                  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="opacity:.4;margin-bottom:8px"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 15h18"/><path d="M9 3v18"/></svg>
                  <div>Clique sur <strong>Actualiser</strong> pour voir<br>l'aperçu de ton template.</div>
                </div>
                <img id="pr-tpl-preview-img" style="display:none;max-width:100%;max-height:100%" alt="Aperçu">
              </div>
              <div id="pr-tpl-preview-err" style="font-size:11px;color:var(--danger);margin-top:4px"></div>
            </div>
          </div>

          <div style="display:flex;gap:8px;justify-content:space-between;margin-top:18px">
            <button id="pr-tpl-del" class="btn btn-ghost" style="color:var(--danger);display:none" onclick="prDeleteTemplate()">Supprimer</button>
            <div style="display:flex;gap:8px;margin-left:auto">
              <button class="btn btn-ghost" onclick="prCloseTplModal()">Annuler</button>
              <button class="btn btn-accent" onclick="prSaveTemplate()">Enregistrer</button>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══════════════════════════════════════════════════════════════════════
           WIZARD : Comment connecter mon imprimante à MySifa
           4 étapes : Type → Agent (+ installer si Locale) → Imprimante → Test
           ═══════════════════════════════════════════════════════════════════════ -->
      <div id="pr-wiz-modal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:950;align-items:center;justify-content:center;padding:20px" onclick="if(event.target===this)prWizClose()">
        <div style="background:var(--card);border:1px solid var(--border);border-radius:16px;padding:0;width:min(760px,95vw);max-height:92vh;overflow:hidden;display:flex;flex-direction:column">

          <!-- Header du wizard -->
          <div style="padding:20px 24px 12px;border-bottom:1px solid var(--border)">
            <div style="display:flex;align-items:center;justify-content:space-between;gap:12px">
              <h2 style="margin:0;font-size:16px;font-weight:700;color:var(--text)">Connecter une imprimante à MySifa</h2>
              <button onclick="prWizClose()" style="background:transparent;border:none;color:var(--muted);cursor:pointer;font-size:20px;padding:0;line-height:1">×</button>
            </div>
            <!-- Barre de progression étapes -->
            <div id="pr-wiz-progress" style="display:flex;gap:6px;margin-top:14px">
              <div class="pr-wiz-dot" data-s="1" style="flex:1;height:4px;background:var(--accent);border-radius:2px;transition:all .2s"></div>
              <div class="pr-wiz-dot" data-s="2" style="flex:1;height:4px;background:var(--border);border-radius:2px;transition:all .2s"></div>
              <div class="pr-wiz-dot" data-s="3" style="flex:1;height:4px;background:var(--border);border-radius:2px;transition:all .2s"></div>
              <div class="pr-wiz-dot" data-s="4" style="flex:1;height:4px;background:var(--border);border-radius:2px;transition:all .2s"></div>
            </div>
            <div id="pr-wiz-step-label" style="font-size:11px;color:var(--muted);margin-top:6px;text-transform:uppercase;letter-spacing:.5px;font-weight:700">Étape 1 / 4 · Type d'imprimante</div>
          </div>

          <!-- Corps du wizard : 4 étapes, une seule visible à la fois -->
          <div id="pr-wiz-body" style="padding:20px 24px;overflow-y:auto;flex:1">

            <!-- ─── ÉTAPE 1 : Type d'imprimante ─── -->
            <div class="pr-wiz-page" data-step="1">
              <div style="font-size:14px;font-weight:700;color:var(--text);margin-bottom:6px">Comment est branchée ton imprimante ?</div>
              <div style="font-size:12px;color:var(--muted);margin-bottom:16px">Choisis le cas qui correspond à ta situation.</div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
                <button type="button" class="pr-wiz-typebtn" onclick="prWizSelectType('tcp_ip')" style="text-align:left;background:var(--bg);border:2px solid var(--border);border-radius:10px;padding:16px;cursor:pointer;transition:all .15s;font-family:inherit">
                  <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
                    <div style="width:36px;height:36px;background:rgba(45,111,187,0.12);border-radius:8px;display:flex;align-items:center;justify-content:center;color:var(--warn)">
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
                    </div>
                    <div style="font-size:14px;font-weight:700;color:var(--text)">Réseau (IP)</div>
                  </div>
                  <div style="font-size:12px;color:var(--text2);line-height:1.5">Mon imprimante a sa propre adresse IP sur le LAN de l'usine (câble Ethernet ou Wifi).</div>
                  <div style="font-size:11px;color:var(--muted);margin-top:8px"><em>Ex : Zebra ZT230 avec option réseau</em></div>
                </button>
                <button type="button" class="pr-wiz-typebtn" onclick="prWizSelectType('windows_local')" style="text-align:left;background:var(--bg);border:2px solid var(--border);border-radius:10px;padding:16px;cursor:pointer;transition:all .15s;font-family:inherit">
                  <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
                    <div style="width:36px;height:36px;background:rgba(240,165,0,0.15);border-radius:8px;display:flex;align-items:center;justify-content:center;color:var(--accent)">
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
                    </div>
                    <div style="font-size:14px;font-weight:700;color:var(--text)">Locale (USB / LPT)</div>
                  </div>
                  <div style="font-size:12px;color:var(--text2);line-height:1.5">Mon imprimante est branchée physiquement sur un PC de l'usine, via USB ou port parallèle (LPT).</div>
                  <div style="font-size:11px;color:var(--muted);margin-top:8px"><em>Ex : imprimante USB, matricielle en LPT</em></div>
                </button>
              </div>
            </div>

            <!-- ─── ÉTAPE 2 : Agent MySifa ─── -->
            <div class="pr-wiz-page" data-step="2" style="display:none">
              <div style="font-size:14px;font-weight:700;color:var(--text);margin-bottom:6px" id="pr-wiz-agent-title">Un agent MySifa doit être en place</div>
              <div style="font-size:12px;color:var(--muted);margin-bottom:16px" id="pr-wiz-agent-intro">L'agent est un petit programme qui fait le pont entre MySifa et l'imprimante. Il tourne en arrière-plan.</div>

              <!-- Choix : agent existant ou nouveau (layout table pour éviter les collisions CSS input radio) -->
              <div style="background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:14px;margin-bottom:12px">

                <!-- Option 1 : Agent existant -->
                <div style="display:flex;align-items:flex-start;gap:12px;padding-bottom:12px;border-bottom:1px solid var(--border);cursor:pointer" onclick="document.getElementById('pr-wiz-agent-existing').click()">
                  <input type="radio" name="pr-wiz-agent-choice" value="existing" id="pr-wiz-agent-existing" onchange="prWizToggleAgentMode()" style="width:16px;height:16px;flex-shrink:0;margin-top:2px;accent-color:var(--accent)">
                  <div style="flex:1;min-width:0">
                    <div style="font-size:13px;font-weight:700;color:var(--text);margin-bottom:2px">Utiliser un agent existant</div>
                    <div style="font-size:11px;color:var(--muted);margin-bottom:8px">Si tu as déjà installé un agent MySifa sur un PC ou Pi accessible.</div>
                    <div id="pr-wiz-agent-existing-row" style="display:none">
                      <select id="pr-wiz-agent-select" class="pr-inp" style="width:100%;max-width:400px" onclick="event.stopPropagation()"><option value="">— Sélectionner un agent —</option></select>
                    </div>
                  </div>
                </div>

                <!-- Option 2 : Nouvel agent -->
                <div style="display:flex;align-items:flex-start;gap:12px;padding-top:12px;cursor:pointer" onclick="document.getElementById('pr-wiz-agent-new').click()">
                  <input type="radio" name="pr-wiz-agent-choice" value="new" id="pr-wiz-agent-new" checked onchange="prWizToggleAgentMode()" style="width:16px;height:16px;flex-shrink:0;margin-top:2px;accent-color:var(--accent)">
                  <div style="flex:1;min-width:0">
                    <div style="font-size:13px;font-weight:700;color:var(--text);margin-bottom:2px">Créer un nouvel agent</div>
                    <div style="font-size:11px;color:var(--muted);margin-bottom:8px">Recommandé si c'est ta première fois ou si tu ajoutes un nouveau PC hôte.</div>
                    <div id="pr-wiz-agent-new-row" onclick="event.stopPropagation()">
                      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
                        <input type="text" id="pr-wiz-agent-name" class="pr-inp" placeholder="Ex : PC-Reception, PC-Quai-Expedition..." style="flex:1;min-width:200px">
                        <button type="button" class="btn btn-accent" onclick="prWizCreateAgent()" style="padding:8px 14px;font-size:12px;white-space:nowrap">Créer l'agent</button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Bloc affiché après création : token + installer (surtout pour Locale) -->
              <div id="pr-wiz-agent-created" style="display:none;margin-top:12px">
                <div style="background:rgba(5,150,105,0.08);border-left:3px solid var(--success);border-radius:6px;padding:10px 12px;margin-bottom:12px">
                  <div style="font-size:12px;font-weight:700;color:var(--success);margin-bottom:4px">✓ Agent créé</div>
                  <div style="font-size:11px;color:var(--text2)">Le token ci-dessous ne sera plus lisible après avoir fermé cet assistant. Copie-le maintenant.</div>
                </div>

                <div style="margin-bottom:12px">
                  <div style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;font-weight:700;margin-bottom:4px">Token de l'agent</div>
                  <div style="display:flex;gap:6px;align-items:center">
                    <input type="text" id="pr-wiz-token-display" readonly style="flex:1;padding:8px 10px;border-radius:6px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-family:monospace;font-size:12px">
                    <button type="button" class="btn btn-ghost" onclick="prWizCopyToken()" style="padding:8px 12px;font-size:12px">📋 Copier</button>
                  </div>
                </div>

                <!-- Instructions install (visibles pour Locale, cachées pour Réseau si agent existant utilisé) -->
                <div id="pr-wiz-install-block">
                  <div style="font-size:12px;font-weight:700;color:var(--text);margin-bottom:8px">Installer l'agent sur le PC hôte</div>

                  <div style="background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:12px;margin-bottom:10px">
                    <div style="display:flex;gap:10px;align-items:flex-start">
                      <div style="width:24px;height:24px;background:var(--accent);color:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:11px;flex-shrink:0">1</div>
                      <div style="flex:1;font-size:12px;color:var(--text2);line-height:1.5">
                        Télécharge l'installeur :
                        <div style="margin-top:6px">
                          <a href="/api/print/installer/windows" download="install_agent_windows.ps1" class="btn btn-accent" style="padding:6px 12px;font-size:12px;text-decoration:none;display:inline-flex;align-items:center;gap:6px">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                            install_agent_windows.ps1
                          </a>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div style="background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:12px;margin-bottom:10px">
                    <div style="display:flex;gap:10px;align-items:flex-start">
                      <div style="width:24px;height:24px;background:var(--accent);color:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:11px;flex-shrink:0">2</div>
                      <div style="flex:1;font-size:12px;color:var(--text2);line-height:1.5">
                        Copie le fichier sur le <strong>PC hôte de l'imprimante</strong> (clé USB, partage réseau, ou téléchargement direct sur ce PC).
                      </div>
                    </div>
                  </div>

                  <div style="background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:12px;margin-bottom:10px">
                    <div style="display:flex;gap:10px;align-items:flex-start">
                      <div style="width:24px;height:24px;background:var(--accent);color:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:11px;flex-shrink:0">3</div>
                      <div style="flex:1;font-size:12px;color:var(--text2);line-height:1.5">
                        Sur le PC hôte, ouvre <strong>PowerShell en tant qu'Administrateur</strong> (Menu Démarrer → tape "powershell" → clic droit → Exécuter en admin), puis colle cette commande :
                        <div style="display:flex;gap:6px;align-items:flex-start;margin-top:6px">
                          <textarea id="pr-wiz-install-cmd" readonly style="flex:1;padding:8px 10px;border-radius:6px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-family:monospace;font-size:11px;resize:vertical;min-height:60px;line-height:1.4"></textarea>
                          <button type="button" class="btn btn-ghost" onclick="prWizCopyInstallCmd()" style="padding:8px 12px;font-size:12px;white-space:nowrap">📋 Copier</button>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div style="background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:12px">
                    <div style="display:flex;gap:10px;align-items:flex-start">
                      <div style="width:24px;height:24px;background:var(--accent);color:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:11px;flex-shrink:0">4</div>
                      <div style="flex:1;font-size:12px;color:var(--text2);line-height:1.5">
                        Attends la fin du script (~3-5 min : Python + pywin32 + NSSM + service Windows). Le message final doit indiquer <code style="background:var(--bg);border:1px solid var(--border);padding:1px 5px;border-radius:3px;font-family:monospace">SERVICE_RUNNING</code>.
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- ─── ÉTAPE 3 : Créer l'imprimante ─── -->
            <div class="pr-wiz-page" data-step="3" style="display:none">
              <div style="font-size:14px;font-weight:700;color:var(--text);margin-bottom:6px">Créer l'imprimante dans MySifa</div>
              <div style="font-size:12px;color:var(--muted);margin-bottom:16px">Renseigne les infos de ton imprimante. L'agent que tu as sélectionné à l'étape précédente est rattaché automatiquement.</div>

              <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px">
                <div style="grid-column:span 2">
                  <label style="display:block;font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;font-weight:700;margin-bottom:4px">Nom de l'imprimante *</label>
                  <input type="text" id="pr-wiz-imp-nom" class="pr-inp" placeholder="Ex : Zebra Réception matière" style="width:100%">
                </div>
                <div>
                  <label style="display:block;font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;font-weight:700;margin-bottom:4px">Poste / atelier</label>
                  <input type="text" id="pr-wiz-imp-poste" class="pr-inp" placeholder="Ex : Réception" style="width:100%">
                </div>
                <div>
                  <label style="display:block;font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;font-weight:700;margin-bottom:4px">Langage *</label>
                  <select id="pr-wiz-imp-langage" class="pr-inp" style="width:100%">
                    <option value="zpl">ZPL — Zebra</option>
                    <option value="epl">EPL — vieilles Zebra</option>
                    <option value="escpos">ESC/POS — Brother, tickets</option>
                  </select>
                </div>

                <!-- Champs Réseau (IP + port) -->
                <div id="pr-wiz-imp-ip-row">
                  <label style="display:block;font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;font-weight:700;margin-bottom:4px">Adresse IP *</label>
                  <input type="text" id="pr-wiz-imp-ip" class="pr-inp" placeholder="192.168.1.42" style="width:100%">
                </div>
                <div id="pr-wiz-imp-port-row">
                  <label style="display:block;font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;font-weight:700;margin-bottom:4px">Port</label>
                  <input type="number" id="pr-wiz-imp-port" class="pr-inp" value="9100" style="width:100%">
                </div>

                <!-- Champ Locale (nom queue Windows) -->
                <div id="pr-wiz-imp-queue-row" style="display:none;grid-column:span 2">
                  <label style="display:block;font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;font-weight:700;margin-bottom:4px">Nom exact de la queue Windows *</label>
                  <input type="text" id="pr-wiz-imp-queue" class="pr-inp" placeholder="Ex : Zebra Z4M (300 dpi)" style="width:100%">
                  <div style="font-size:13px;color:var(--text2);margin-top:8px;line-height:1.6;padding:12px 14px;background:var(--bg);border:1px solid var(--border);border-radius:8px">
                    <div style="font-weight:700;color:var(--text);margin-bottom:8px;font-size:14px">Comment récupérer le nom exact ?</div>
                    <div style="margin-bottom:10px">
                      Sur le PC hôte, ouvre <strong>l'invite de commande</strong> (Menu Démarrer → tape <code style="background:var(--card);border:1px solid var(--border);padding:1px 6px;border-radius:3px;font-family:monospace;font-size:12px">cmd</code>) et lance :
                    </div>
                    <div style="display:flex;align-items:center;justify-content:center;padding:10px 14px;background:var(--card);border:1px solid var(--border);border-radius:6px;margin-bottom:10px">
                      <code style="font-family:monospace;font-size:14px;color:var(--text);font-weight:600">wmic printer get name</code>
                    </div>
                    <div style="margin-bottom:8px">
                      Copie-colle le nom retourné (attention aux <strong>espaces</strong>, <strong>majuscules</strong> et <strong>parenthèses</strong>).
                    </div>
                    <div style="padding-top:8px;border-top:1px dashed var(--border);color:var(--warn)">
                      ⚠️ Ce n'est <strong>PAS</strong> le "Nom de partage" avec underscores dans l'onglet <em>Partage</em> — c'est le nom local original.
                    </div>
                  </div>
                </div>

                <div>
                  <label style="display:block;font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;font-weight:700;margin-bottom:4px">DPI</label>
                  <select id="pr-wiz-imp-dpi" class="pr-inp" style="width:100%">
                    <option value="203">203 dpi (standard)</option>
                    <option value="300">300 dpi</option>
                    <option value="600">600 dpi</option>
                  </select>
                </div>
                <div>
                  <label style="display:block;font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;font-weight:700;margin-bottom:4px">Largeur × Hauteur (mm)</label>
                  <div style="display:flex;gap:6px;align-items:center">
                    <input type="number" id="pr-wiz-imp-largeur" class="pr-inp" value="102" style="width:100%">
                    <span style="color:var(--muted)">×</span>
                    <input type="number" id="pr-wiz-imp-hauteur" class="pr-inp" value="152" style="width:100%">
                  </div>
                </div>
              </div>
            </div>

            <!-- ─── ÉTAPE 4 : Test d'impression ─── -->
            <div class="pr-wiz-page" data-step="4" style="display:none">
              <div style="text-align:center;padding:16px 0">
                <div style="width:60px;height:60px;background:rgba(5,150,105,0.15);border-radius:50%;display:inline-flex;align-items:center;justify-content:center;margin-bottom:12px;color:var(--success)">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                </div>
                <div style="font-size:16px;font-weight:700;color:var(--text);margin-bottom:6px">Imprimante configurée !</div>
                <div style="font-size:13px;color:var(--text2);margin-bottom:20px">
                  L'imprimante <strong id="pr-wiz-created-name">—</strong> a été ajoutée à MySifa.
                </div>
                <button type="button" class="btn btn-accent" onclick="prWizTestPrint()" style="padding:12px 24px;font-size:13px;font-weight:700">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="margin-right:6px;vertical-align:-2px"><polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/></svg>
                  Lancer un test d'impression
                </button>
                <div id="pr-wiz-test-result" style="margin-top:12px;font-size:12px;color:var(--muted)"></div>
              </div>
            </div>

          </div>

          <!-- Footer navigation -->
          <div style="padding:14px 24px;border-top:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;gap:10px">
            <button type="button" id="pr-wiz-back-btn" onclick="prWizBack()" class="btn btn-ghost" style="padding:9px 18px;font-size:13px;visibility:hidden">← Retour</button>
            <div style="flex:1"></div>
            <button type="button" id="pr-wiz-next-btn" onclick="prWizNext()" class="btn btn-accent" style="padding:9px 18px;font-size:13px">Continuer →</button>
          </div>
        </div>
      </div>

    </section>

    <section id="panel-formations" class="hidden">
      <div class="card">
        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:16px">
          <div>
            <h2 style="margin:0 0 4px">Formations &amp; guides in-app</h2>
            <p class="sub" style="margin:0;font-size:12px">Suivi des tutos lus dans MyQualité. Vous pouvez remettre à zéro un guide pour un utilisateur (il le reverra à sa prochaine visite).</p>
          </div>
          <button type="button" class="btn btn-sec btn-sm" id="fmt-refresh">Actualiser</button>
        </div>
        <div style="display:flex;gap:10px;margin-bottom:14px;flex-wrap:wrap;align-items:center">
          <input type="text" id="fmt-search" placeholder="Rechercher (nom, email, rôle, guide...)" autocomplete="off"
            style="flex:1;min-width:260px;padding:9px 12px;border-radius:10px;border:1.5px solid var(--border);background:var(--bg);color:var(--text);font-size:13px;font-family:inherit;outline:none;transition:border-color .15s">
          <select id="fmt-filter-status" style="padding:9px 12px;border-radius:10px;border:1.5px solid var(--border);background:var(--bg);color:var(--text);font-size:13px;font-family:inherit;outline:none">
            <option value="">Tous les statuts</option>
            <option value="acked">Validé (ack)</option>
            <option value="completed">Complété (non ack)</option>
            <option value="in_progress">En cours</option>
            <option value="open">Ouvert (jamais parcouru)</option>
            <option value="never">Jamais ouvert</option>
          </select>
        </div>
        <div class="table-wrap">
          <table id="fmt-table" style="min-width:820px">
            <thead>
              <tr>
                <th>Utilisateur</th>
                <th>Rôle</th>
                <th>Guide</th>
                <th>Statut</th>
                <th>Étapes vues</th>
                <th>Temps passé</th>
                <th>Ouvertures</th>
                <th>Ouvert le</th>
                <th>Validé le</th>
                <th></th>
              </tr>
            </thead>
            <tbody id="fmt-tbody"></tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- Modal nouvelle annonce -->
    <div id="upd-modal-overlay" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:800;align-items:center;justify-content:center" class="hidden">
      <div style="background:var(--card);border:1px solid var(--border);border-radius:16px;padding:28px;width:min(560px,95vw);max-height:90vh;overflow:auto">
        <h2 style="margin:0 0 18px;font-size:17px">Nouvelle annonce</h2>
        <div class="form-grid" style="grid-template-columns:1fr 1fr;margin-bottom:12px">
          <div>
            <label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Application</label>
            <select id="nm-app" style="width:100%" onchange="onAppChange()">
              <option value="planning">Planning Production</option>
              <option value="fabrication">Saisie Production</option>
              <option value="stock">Stock & Inventaire</option>
              <option value="myexpe">MyExpé (Transport)</option>
              <option value="planning_rh">Planning RH</option>
              <option value="paie">Paie</option>
              <option value="global">Toutes les applications</option>
            </select>
          </div>
          <div>
            <label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Page</label>
            <select id="nm-page" style="width:100%">
              <option value="">Toutes les pages</option>
            </select>
          </div>
        </div>
        <div style="margin-bottom:12px">
          <label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Active</label>
          <select id="nm-active" style="width:100%">
            <option value="1">Oui — visible par les utilisateurs</option>
            <option value="0">Non — masquée</option>
          </select>
        </div>
        <div style="margin-bottom:12px">
          <label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Titre</label>
          <input type="text" id="nm-titre" placeholder="Ex : Mise à jour du 15 mai 2026 — Planning" style="width:100%">
        </div>
        <div style="margin-bottom:18px">
          <label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Message (HTML autorisé)</label>
          <textarea id="nm-message" rows="8" placeholder="&lt;p&gt;Bonjour ! Voici les nouveautés…&lt;/p&gt;" style="width:100%;padding:10px 12px;border-radius:10px;border:1.5px solid var(--border);background:var(--bg);color:var(--text);font-size:13px;font-family:monospace;resize:vertical"></textarea>
        </div>
        <div style="display:flex;gap:10px;justify-content:flex-end">
          <button type="button" class="btn btn-sec" onclick="closeNewUpdateModal()">Annuler</button>
          <button type="button" class="btn" onclick="submitNewUpdate()">Créer l'annonce</button>
        </div>
      </div>
    </div>

    <!-- Modal modifier annonce -->
    <div id="edit-upd-modal-overlay" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:800;align-items:center;justify-content:center" class="hidden">
      <div style="background:var(--card);border:1px solid var(--border);border-radius:16px;padding:28px;width:min(560px,95vw);max-height:90vh;overflow:auto">
        <h2 style="margin:0 0 18px;font-size:17px">Modifier l'annonce</h2>
        <div class="form-grid" style="grid-template-columns:1fr 1fr;margin-bottom:12px">
          <div>
            <label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Application</label>
            <select id="edit-nm-app" style="width:100%" onchange="onEditAppChange()">
              <option value="planning">Planning Production</option>
              <option value="fabrication">Saisie Production</option>
              <option value="stock">Stock & Inventaire</option>
              <option value="myexpe">MyExpé (Transport)</option>
              <option value="planning_rh">Planning RH</option>
              <option value="paie">Paie</option>
              <option value="global">Toutes les applications</option>
            </select>
          </div>
          <div>
            <label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Page</label>
            <select id="edit-nm-page" style="width:100%">
              <option value="">Toutes les pages</option>
            </select>
          </div>
        </div>
        <div style="margin-bottom:12px">
          <label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Active</label>
          <select id="edit-nm-active" style="width:100%">
            <option value="1">Oui — visible par les utilisateurs</option>
            <option value="0">Non — masquée</option>
          </select>
        </div>
        <div style="margin-bottom:12px">
          <label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Titre</label>
          <input type="text" id="edit-nm-titre" placeholder="Ex : Mise à jour du 15 mai 2026 — Planning" style="width:100%">
        </div>
        <div style="margin-bottom:18px">
          <label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Message (HTML autorisé)</label>
          <textarea id="edit-nm-message" rows="8" placeholder="&lt;p&gt;Bonjour ! Voici les nouveautés…&lt;/p&gt;" style="width:100%;padding:10px 12px;border-radius:10px;border:1.5px solid var(--border);background:var(--bg);color:var(--text);font-size:13px;font-family:monospace;resize:vertical"></textarea>
        </div>
        <div style="display:flex;gap:10px;justify-content:flex-end">
          <button type="button" class="btn btn-sec" onclick="closeEditUpdateModal()">Annuler</button>
          <button type="button" class="btn" onclick="submitEditUpdate()">Enregistrer</button>
        </div>
      </div>
    </div>
  </main>
</div>
<script src="/static/support_widget.js"></script>
<script>window.__MYSIFA_APP__='settings';</script>
<link rel="stylesheet" href="/static/mysifa_dock.css">
<link rel="stylesheet" href="/static/mysifa_postit.css">
<link rel="stylesheet" href="/static/mysifa_cmdk.css">
<script src="/static/mysifa_dock.js"></script>
<script src="/static/mysifa_postit.js"></script>
<script src="/static/mysifa_cmdk.js"></script>
<script src="/static/chat_mentions.js"></script>
<script src="/static/chat_widget.js?v=11"></script>
<script src="/static/chat_widget_v2.js?v=8"></script>
<script>
/*__TRACA_GUIDE__*/
const API = window.location.origin;
async function api(path, opt) {
  const r = await fetch(API + path, { credentials: 'include', ...opt });
  if (r.status === 401) { location.href = '/?next=/settings'; return null; }
  const ct = r.headers.get('content-type') || '';
  const j = ct.includes('json') ? await r.json().catch(() => ({})) : {};
  if (!r.ok) throw new Error(j.detail || ('Erreur ' + r.status));
  return j;
}
function toast(msg, err) {
  const t = document.createElement('div');
  t.className = 'toast' + (err ? ' err' : '');
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}
let assignableRoles = [];
let roleLabels = {};
let apps = [];
let operators = [];
let machines = [];
let matrixSnapshot = [];
let superadminEmailRef = '';
let usersAll = [];
let usersQuery = '';
let usersRoleFilter = '';

function _norm(s){
  return String(s||'')
    .toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g,'')
    .replace(/[^a-z0-9@._\- ]+/g,' ')
    .replace(/\s+/g,' ')
    .trim();
}

function userHaystack(u){
  const role = (u && u.role) ? String(u.role) : '';
  const roleLbl = (roleLabels && roleLabels[role]) ? String(roleLabels[role]) : role;
  return _norm([
    u && u.nom,
    u && u.email,
    role,
    roleLbl,
    u && u.operateur_lie,
    u && u.telephone,
    u && u.machine_nom,
    u && u.machine_id,
    (u && Number(u.actif)===1) ? 'actif' : 'inactif',
  ].filter(Boolean).join(' '));
}

function scoreMatch(hay, tokens){
  let score = 0;
  for(const t of tokens){
    const i = hay.indexOf(t);
    if(i < 0) return null;
    score += i;
    if(i === 0) score -= 6;
  }
  return score;
}

function syncSettingsPageHead(tabId) {
  document.body.classList.toggle('settings-tab-fsc', tabId === 'fsc');
  document.body.classList.toggle('settings-tab-menu', tabId === 'menu');
  const titleEl = document.querySelector('.mobile-topbar-title');
  const subEl = document.querySelector('.mobile-topbar-sub');
  const HEADS = {
    menu:         { title: 'Paramètres',      sub: 'Menu général — sélectionnez une catégorie' },
    users:        { title: 'Paramètres',      sub: 'Comptes utilisateurs et accès' },
    matrix:       { title: 'Paramètres',      sub: 'Matrice des accès applicatifs' },
    defaults:     { title: 'Paramètres',      sub: 'Référentiel des rôles' },
    fournisseurs: { title: 'Fournisseurs',    sub: 'Répertoire, certifications FSC et traçabilité' },
    clients:      { title: 'Clients',         sub: 'Référentiel ERP' },
    operations:   { title: 'Opérations',      sub: 'Codes saisis en production' },
    maintenance:  { title: 'Maintenance',     sub: 'Codes opérations et alertes opérateurs' },
    machines:     { title: 'Machines',        sub: 'Horaires, capacité, rentabilité' },
    emplacements: { title: 'Emplacements',    sub: 'Plan du magasin' },
    laizes:       { title: 'Laizes matières', sub: 'Formats standards' },
    importations: { title: 'Importations',    sub: 'Grilles tarifaires transporteurs' },
    updates:      { title: 'Mises à jour',    sub: 'Annonces de release' },
    audit:        { title: 'Audit',           sub: 'Log d\'activité' },
    fsc:          { title: 'Registre FSC',    sub: '' },
    dashboards:   { title: 'Tableaux de bord', sub: 'Widgets consolidés' },
    api:          { title: 'Clés API',        sub: 'Tokens d\'intégration' },
    printers:     { title: 'Imprimantes',     sub: 'Configuration et templates' },
    promote:      { title: 'Déploiement',     sub: 'Promouvoir v1 → v2' },
  };
  const h = HEADS[tabId] || { title: 'Paramètres', sub: 'Gestion des comptes et des accès' };
  if (titleEl) titleEl.textContent = h.title;
  if (subEl) {
    if (h.sub) {
      subEl.textContent = h.sub;
      subEl.style.display = '';
    } else {
      subEl.textContent = '';
      subEl.style.display = 'none';
    }
  }
}

const VALID_TABS = ['menu','users','matrix','defaults','fournisseurs','clients','operations','maintenance','machines','emplacements','laizes','importations','bridge','updates','audit','fsc','dashboards','api','promote','printers','formations'];

function setTab(id, opts) {
  if (!VALID_TABS.includes(id)) id = 'menu';
  const silent = !!(opts && opts.silent);
  document.querySelectorAll('.nav-btn[data-tab]').forEach(b => {
    b.classList.toggle('active', b.dataset.tab === id);
  });
  if (!silent) {
    // Persistance dans l'URL : hard refresh, partage de lien, back/forward
    try {
      const target = '#' + id;
      if (location.hash !== target) {
        // replaceState pour éviter d'ajouter chaque clic à l'historique
        history.replaceState(null, '', target);
      }
    } catch(e){}
  }
  ['menu', 'users', 'matrix', 'defaults', 'fournisseurs', 'clients', 'operations', 'maintenance', 'machines', 'emplacements', 'laizes', 'importations', 'bridge', 'updates', 'audit', 'fsc', 'dashboards', 'api', 'promote', 'printers', 'formations'].forEach(p => {
    const el = document.getElementById('panel-' + p);
    if (el) el.classList.toggle('hidden', p !== id);
  });
  syncSettingsPageHead(id);
  if (id === 'fournisseurs') loadFournisseurs();
loadFournisseursGroupes();
  if (id === 'clients') initClientsPanel();
  if (id === 'operations') loadOperationCodes();
  if (id === 'maintenance') { loadMaintCodes(); loadAlerts(); }
  if (id === 'machines') initMachinesPanel();
  if (id === 'emplacements') initEmplacementsPanel();
  if (id === 'laizes') initLaizesPanel();
  if (id === 'importations') initImportationsPanel();
  if (id === 'bridge') initBridgePanel();
  if (id === 'updates') loadUpdates();
  if (id === 'audit') loadAuditLogs();
  if (id === 'fsc') initFscPanel();
  if (id === 'printers') initPrintersPanel();
  if (id === 'formations') loadFormationsAdmin();
  if (id === 'dashboards') renderSettingsDashboards();
  if (id === 'api') loadApiKeys();
  if (id === 'promote') loadPromoteStatus();
}

document.querySelectorAll('.nav-btn[data-tab]').forEach(b => {
  b.addEventListener('click', () => setTab(b.dataset.tab));
});

// Sub-tabs Utilisateurs / Matrice / Référentiel : 3 boutons dans chacun des
// 3 panels, mapping vers les IDs de panel effectifs (users-list → users, etc.).
const _SUBTAB_TO_PANEL = { 'users-list': 'users', 'users-matrix': 'matrix', 'users-defaults': 'defaults' };
document.querySelectorAll('.sub-tab-btn[data-subtab]').forEach(b => {
  b.addEventListener('click', () => {
    const target = _SUBTAB_TO_PANEL[b.dataset.subtab];
    if (target) setTab(target);
  });
});

// Onglet initial : lu depuis location.hash (hard refresh, deep-link)
function _readHashTab(){
  try {
    const h = (location.hash || '').replace(/^#/, '').trim();
    return VALID_TABS.includes(h) ? h : 'menu';
  } catch(e){ return 'menu'; }
}
// Différé pour attendre que toutes les 'let' globales du script (fournisseursAll, etc.)
// soient effectivement déclarées — sinon TDZ ReferenceError.
window.addEventListener('DOMContentLoaded', () => {
  try { setTab(_readHashTab(), { silent: true }); }
  catch(e){ try { syncSettingsPageHead('menu'); } catch(e2){} }
});
// Fallback si DOMContentLoaded a déjà tiré (page cache/back-forward)
if (document.readyState === 'complete' || document.readyState === 'interactive') {
  setTimeout(() => {
    try { setTab(_readHashTab(), { silent: true }); }
    catch(e){ try { syncSettingsPageHead('menu'); } catch(e2){} }
  }, 0);
}

// Navigation clavier (back/forward) : synchroniser
window.addEventListener('hashchange', () => {
  const id = _readHashTab();
  setTab(id, { silent: true });
});

function setSidebarOpen(open){
  document.body.classList.toggle('sb-open', !!open);
}
try{
  document.body.classList.add('has-topbar');
  const ov = document.getElementById('sb-ov');
  if(ov) ov.addEventListener('click', ()=>setSidebarOpen(false));
  const burger = document.getElementById('sb-burger');
  if(burger) burger.addEventListener('click', ()=>setSidebarOpen(!document.body.classList.contains('sb-open')));
  const home = document.getElementById('sb-home');
  if(home) home.addEventListener('click', ()=>{ window.location.href = '/'; });
  // Fermer le menu après clic sur un onglet (mobile)
  document.querySelectorAll('.nav-btn[data-tab]').forEach(b => {
    b.addEventListener('click', () => setSidebarOpen(false));
  });
  // Cartes du Menu général
  document.querySelectorAll('.menu-item[data-goto]').forEach(b => {
    b.addEventListener('click', () => {
      setTab(b.dataset.goto);
      setSidebarOpen(false);
      try { window.scrollTo({ top: 0, behavior: 'smooth' }); } catch(e){ window.scrollTo(0,0); }
    });
  });
}catch(e){}

function iconSvg(name, size) {
  const s = size || 16;
  const a = 'width="' + s + '" height="' + s + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"';
  if (name === 'moon') return '<svg ' + a + '><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
  if (name === 'sun') return '<svg ' + a + '><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>';
  if (name === 'edit') return '<svg ' + a + '><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>';
  return '';
}
function syncThemeBtn() {
  const light = document.body.classList.contains('light');
  const slot = document.getElementById('theme-ico-slot');
  if (slot) slot.innerHTML = iconSvg(light ? 'sun' : 'moon', 16);
  const lb = document.getElementById('theme-label');
  if (lb) lb.textContent = light ? 'Mode clair' : 'Mode sombre';
}

document.getElementById('theme-btn').onclick = () => {
  if (window.MySifaTheme) MySifaTheme.toggleMode();
  syncThemeBtn();
};
document.getElementById('logout-btn').onclick = async () => {
  try { await api('/api/auth/logout', { method: 'POST' }); } catch (e) {}
  location.href = '/';
};
syncThemeBtn();

document.getElementById('sb-user-chip').onclick = () => { location.href = '/profil'; };

function initSupportSidebar() {
  const ico = document.getElementById('sb-support-ico');
  if (ico) {
    try {
      ico.innerHTML = (window.MySifaSupport && window.MySifaSupport.iconSvg) ? window.MySifaSupport.iconSvg() : '';
    } catch (e) { ico.innerHTML = ''; }
  }
  document.getElementById('sb-support').onclick = () => {
    try {
      if (window.MySifaSupport && typeof window.MySifaSupport.open === 'function') {
        window.MySifaSupport.open({
          user: window.__meUser,
          page: 'Paramètres',
          notify: (m, t) => toast(m, t === 'error'),
          api: api,
        });
      }
    } catch (e) {}
  };
}

async function refreshSidebarUser() {
  const me = await api('/api/auth/me');
  if (!me || typeof me !== 'object') return;
  if (window.MySifaTheme) MySifaTheme.mergeFromUser(me);
  window.__meUser = me;
  if (me.id) {
    window.__MYSIFA_UID__ = me.id;
    window.__MYSIFA_NOM__ = me.nom || '';
    window.__MYSIFA_ROLE__ = me.role || '';
    window.__MYSIFA_USER__ = { nom: me.nom || '', role: me.role || '' };
  }
  const chip = document.getElementById('sb-user-chip');
  if (chip && window.MySifaUserChip) {
    MySifaUserChip.fill(chip, me, {
      roleLabels: roleLabels,
      editIconHtml: iconSvg('edit', 10),
    });
  }
}

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s == null ? '' : String(s);
  return d.innerHTML;
}

function escHtml(s) {
  const d = document.createElement('div');
  d.textContent = s == null ? '' : String(s);
  return d.innerHTML;
}

function escAttr(s) {
  return String(s || '').replace(/"/g, '&quot;');
}

async function loadFilters() {
  try {
    const f = await api('/api/filters');
    if (f && f.operators) operators = f.operators;
  } catch (e) { operators = []; }
  const opSel = document.getElementById('cu-op');
  opSel.innerHTML = '<option value="">— Opérateur lié —</option>' +
    operators.map(o => '<option value="' + esc(o) + '">' + esc(o) + '</option>').join('');
}

async function loadMachines() {
  try {
    const m = await api('/api/planning/machines');
    machines = Array.isArray(m) ? m : [];
  } catch (e) { machines = []; }
  const ms = document.getElementById('cu-mac');
  ms.innerHTML = '<option value="">— Machine (fabrication) —</option>' +
    machines.map(x => '<option value="' + esc(x.id) + '">' + esc(x.nom) + '</option>').join('');
  fillMacSelect();
}

// ── Machines (horaires planning + métrage total) ─────────────────────────────
const MAC_DAY_ROWS = [
  { key: 'horaires_lundi', label: 'Lundi' },
  { key: 'horaires_mardi', label: 'Mardi' },
  { key: 'horaires_mercredi', label: 'Mercredi' },
  { key: 'horaires_jeudi', label: 'Jeudi' },
  { key: 'horaires_vendredi', label: 'Vendredi' },
  { key: 'horaires_samedi', label: 'Samedi' },
];
const MAC_DEFAULTS_BY_KEY = {
  C1: { pair: { week: { s: 5, e: 20 }, fri: { s: 7, e: 19 } }, impair: { week: { s: 5, e: 20 }, fri: { s: 7, e: 19 } } },
  C2: { pair: { week: { s: 5, e: 13 }, fri: { s: 6, e: 13 } }, impair: { week: { s: 13, e: 20 }, fri: { s: 14, e: 20 } } },
  DSI: { pair: { week: { s: 8, e: 14 }, fri: { s: 8, e: 14 } }, impair: { week: { s: 8, e: 14 }, fri: { s: 8, e: 14 } } },
  REP: { pair: { week: { s: 6, e: 20 }, fri: { s: 7, e: 19 } }, impair: { week: { s: 6, e: 20 }, fri: { s: 7, e: 19 } } },
};
let macSubTab = 'mac-horaires';
let macMachine = null;
let _macPanelReady = false;

function macMachineKey(m) {
  const raw = String((m && (m.code || m.nom)) || '').trim();
  const norm = raw.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  if (norm.includes('cohesio 1') || norm === 'c1') return 'C1';
  if (norm.includes('cohesio 2') || norm === 'c2') return 'C2';
  if (norm.includes('repiquage') || norm === 'rep') return 'REP';
  if (norm.includes('dsi')) return 'DSI';
  return raw;
}

function macPad(n) { return String(n).padStart(2, '0'); }

function macFloatToHm(f) {
  if (!isFinite(f)) return '';
  const h = Math.floor(f + 1e-6);
  const m = Math.round((f - h) * 60);
  const hh = h + (m >= 60 ? 1 : 0);
  const mm = ((m % 60) + 60) % 60;
  return macPad(hh) + ':' + macPad(mm);
}

function macHmToFloat(raw) {
  const s = String(raw || '').trim();
  if (!/^\d{1,2}:\d{2}$/.test(s)) return null;
  const p = s.split(':');
  const hh = parseInt(p[0], 10);
  const mm = parseInt(p[1], 10);
  if (!isFinite(hh) || !isFinite(mm)) return null;
  return hh + mm / 60;
}

function macParseHorairesCol(val) {
  if (!val || !String(val).trim()) return { start: '', end: '' };
  const parts = String(val).trim().split(',');
  function toHm(x) {
    const t = String(x || '').trim();
    if (/^\d{1,2}:\d{2}$/.test(t)) return t;
    const f = parseFloat(t.replace(',', '.'));
    return isFinite(f) ? macFloatToHm(f) : '';
  }
  return { start: toHm(parts[0]), end: toHm(parts[1] || '') };
}

function macNormalizeParity(raw) {
  if (!raw || typeof raw !== 'object') return null;
  const out = { pair: {}, impair: {} };
  for (const par of ['pair', 'impair']) {
    const block = raw[par];
    if (!block) return null;
    for (const slot of ['week', 'fri']) {
      const w = block[slot];
      let s, e;
      if (Array.isArray(w) && w.length >= 2) { s = +w[0]; e = +w[1]; }
      else if (w && typeof w === 'object') { s = +w.s; e = +w.e; }
      else return null;
      if (!isFinite(s) || !isFinite(e) || e <= s) return null;
      out[par][slot] = { s, e };
    }
  }
  return out;
}

function macGetParityDefaults(m) {
  if (m && m.horaires_parity) {
    try {
      const j = typeof m.horaires_parity === 'string' ? JSON.parse(m.horaires_parity) : m.horaires_parity;
      const norm = macNormalizeParity(j);
      if (norm) return norm;
    } catch (e) { /* ignore */ }
  }
  const mk = macMachineKey(m);
  return MAC_DEFAULTS_BY_KEY[mk] || MAC_DEFAULTS_BY_KEY.C1;
}

function fillMacSelect() {
  const sel = document.getElementById('mac-select');
  if (!sel) return;
  const prev = sel.value;
  sel.innerHTML = machines.map(x =>
    '<option value="' + esc(x.id) + '">' + esc(x.nom) + '</option>'
  ).join('');
  if (prev && machines.some(x => String(x.id) === String(prev))) sel.value = prev;
  else if (machines.length) sel.value = String(machines[0].id);
}

function setMacSubTab(id) {
  macSubTab = id;
  document.querySelectorAll('.mac-sub-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.macsub === id);
  });
  const hor = document.getElementById('mac-horaires-wrap');
  const met = document.getElementById('mac-metrage-wrap');
  const nom = document.getElementById('mac-nom-wrap');
  if (hor) hor.classList.toggle('hidden', id !== 'mac-horaires');
  if (met) met.classList.toggle('hidden', id !== 'mac-metrage');
  if (nom) nom.classList.toggle('hidden', id !== 'mac-nom');
}

function renderMacHorairesForm() {
  const m = macMachine;
  const weekly = document.getElementById('mac-horaires-weekly');
  const parityBox = document.getElementById('mac-horaires-parity');
  const jeBox = document.getElementById('mac-je');
  if (jeBox) jeBox.checked = !!(m && +m.journee_entiere === 1);
  if (!weekly || !m) return;
  const mk = macMachineKey(m);
  const isC2 = mk === 'C2';
  if (parityBox) parityBox.classList.toggle('hidden', !isC2);

  let rows = '';
  MAC_DAY_ROWS.forEach(d => {
    const p = macParseHorairesCol(m[d.key]);
    rows += '<tr><td style="font-weight:600">' + esc(d.label) + '</td>' +
      '<td><input type="text" class="mac-h-start" data-field="' + esc(d.key) + '" value="' + esc(p.start) + '" placeholder="05:00" inputmode="numeric" style="width:100%"></td>' +
      '<td><input type="text" class="mac-h-end" data-field="' + esc(d.key) + '" value="' + esc(p.end) + '" placeholder="21:00" inputmode="numeric" style="width:100%"></td></tr>';
  });
  weekly.innerHTML = '<div class="table-wrap"><table><thead><tr><th>Jour</th><th>Début (HH:MM)</th><th>Fin (HH:MM)</th></tr></thead><tbody>' + rows + '</tbody></table></div>';

  if (isC2 && parityBox) {
    const defs = macGetParityDefaults(m);
    function pr(lbl, id, val) {
      return '<div class="fd" style="margin-bottom:8px"><label class="sub" style="display:block;margin-bottom:4px">' + lbl + '</label>' +
        '<input type="text" id="' + id + '" value="' + esc(macFloatToHm(val)) + '" placeholder="07:00" inputmode="numeric" style="width:100%"></div>';
    }
    parityBox.innerHTML =
      '<div style="font-size:12px;font-weight:700;color:var(--text);margin-bottom:10px;text-transform:uppercase;letter-spacing:.5px">Semaines paires / impaires (Cohésio 2)</div>' +
      '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">' +
      '<div style="border:1px solid var(--border);border-radius:12px;padding:14px">' +
      '<div style="font-weight:600;margin-bottom:8px;font-size:13px">Semaine paire</div>' +
      pr('Lun–jeu début', 'mac-dp-w-s', defs.pair.week.s) +
      pr('Lun–jeu fin', 'mac-dp-w-e', defs.pair.week.e) +
      pr('Vendredi début', 'mac-dp-f-s', defs.pair.fri.s) +
      pr('Vendredi fin', 'mac-dp-f-e', defs.pair.fri.e) +
      '</div><div style="border:1px solid var(--border);border-radius:12px;padding:14px">' +
      '<div style="font-weight:600;margin-bottom:8px;font-size:13px">Semaine impaire</div>' +
      pr('Lun–jeu début', 'mac-di-w-s', defs.impair.week.s) +
      pr('Lun–jeu fin', 'mac-di-w-e', defs.impair.week.e) +
      pr('Vendredi début', 'mac-di-f-s', defs.impair.fri.s) +
      pr('Vendredi fin', 'mac-di-f-e', defs.impair.fri.e) +
      '</div></div>';
  } else if (parityBox) {
    parityBox.innerHTML = '';
  }
}

function renderMacMetrageForm() {
  const inp = document.getElementById('mac-metrage-inp');
  const hint = document.getElementById('mac-metrage-hint');
  if (!inp || !macMachine) return;
  const v = macMachine.dernier_metrage;
  inp.value = (v != null && isFinite(Number(v))) ? String(Math.round(Number(v))) : '';
  if (hint) {
    hint.textContent = v != null
      ? 'Valeur en base : ' + Math.round(Number(v)).toLocaleString('fr-FR') + ' m'
      : 'Aucune valeur enregistrée — la première saisie définira le compteur.';
  }
}

function renderMacNomForm() {
  const inp = document.getElementById('mac-nom-inp');
  const hint = document.getElementById('mac-nom-hint');
  if (!inp || !macMachine) return;
  inp.value = macMachine.nom || '';
  if (hint) hint.textContent = macMachine.code ? 'Code interne : ' + macMachine.code : '';
}

async function saveMacNom() {
  const inp = document.getElementById('mac-nom-inp');
  if (!inp || !macMachine) return;
  const newNom = inp.value.trim();
  if (!newNom) { toast('Le nom ne peut pas être vide', true); return; }
  const btn = document.getElementById('mac-nom-save');
  if (btn) btn.disabled = true;
  try {
    await api('/api/settings/machines/' + macMachine.id + '/nom', {
      method: 'PUT',
      body: JSON.stringify({ nom: newNom }),
    });
    toast('Nom enregistré.');
    await loadMacMachineDetail();
    await loadMachines();
  } catch (e) {
    toast(e.message || 'Erreur lors du renommage', true);
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function loadMacMachineDetail() {
  const sel = document.getElementById('mac-select');
  const hint = document.getElementById('mac-hint');
  if (!sel || !sel.value) {
    macMachine = null;
    return;
  }
  const id = Number(sel.value);
  try {
    macMachine = await api('/api/planning/machines/' + id);
    if (hint) hint.textContent = (macMachine && macMachine.code) ? ('Code ' + macMachine.code) : '';
    renderMacHorairesForm();
    renderMacMetrageForm();
    renderMacNomForm();
  } catch (e) {
    macMachine = null;
    if (hint) hint.textContent = '';
    toast(e.message || 'Erreur chargement machine', true);
  }
}

function macCollectHorairesPayload() {
  const payload = {};
  document.querySelectorAll('.mac-h-start').forEach(inp => {
    const field = inp.dataset.field;
    const endInp = document.querySelector('.mac-h-end[data-field="' + field + '"]');
    const st = (inp.value || '').trim();
    const en = endInp ? (endInp.value || '').trim() : '';
    if (st && en) payload[field] = st + ',' + en;
  });
  return payload;
}

function macCollectParityPayload() {
  function v(id) {
    const f = macHmToFloat(document.getElementById(id) && document.getElementById(id).value);
    return f == null ? null : f;
  }
  return {
    pair: { week: { s: v('mac-dp-w-s'), e: v('mac-dp-w-e') }, fri: { s: v('mac-dp-f-s'), e: v('mac-dp-f-e') } },
    impair: { week: { s: v('mac-di-w-s'), e: v('mac-di-w-e') }, fri: { s: v('mac-di-f-s'), e: v('mac-di-f-e') } },
  };
}

async function saveMacHoraires() {
  if (!macMachine) return;
  const id = macMachine.id;
  const mk = macMachineKey(macMachine);
  const bulk = macCollectHorairesPayload();
  try {
    if (mk === 'C2') {
      const nd = macCollectParityPayload();
      function okR(r) { return r.s != null && r.e != null && r.e > r.s && r.s >= 0 && r.e <= 24; }
      if (![nd.pair.week, nd.pair.fri, nd.impair.week, nd.impair.fri].every(okR)) {
        toast('Plages paire/impair invalides (format HH:MM, fin > début)', true);
        return;
      }
      await api('/api/planning/machines/' + id + '/horaires-parity', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(nd),
      });
    }
    if (Object.keys(bulk).length) {
      await api('/api/planning/machines/' + id + '/horaires-bulk', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(bulk),
      });
    }
    if (mk !== 'C2' && !Object.keys(bulk).length && !document.getElementById('mac-je')?.checked) {
      toast('Renseignez au moins un créneau horaire.', true);
      return;
    }
    // Journée entière par défaut sur la machine
    const jeBox = document.getElementById('mac-je');
    const je = jeBox && jeBox.checked ? 1 : 0;
    await api('/api/planning/machines/' + id + '/journee-entiere', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ journee_entiere: je }),
    });
    toast('Horaires enregistrés.');
    await loadMacMachineDetail();
    await loadMachines();
  } catch (e) {
    toast(e.message || 'Erreur enregistrement horaires', true);
  }
}

async function resetMacHoraires() {
  if (!macMachine || !confirm('Réinitialiser les horaires de cette machine aux valeurs par défaut ?')) return;
  const mk = macMachineKey(macMachine);
  const d = MAC_DEFAULTS_BY_KEY[mk] || MAC_DEFAULTS_BY_KEY.C1;
  const id = macMachine.id;
  try {
    if (mk === 'C2') {
      await api('/api/planning/machines/' + id + '/horaires-parity', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(d),
      });
    } else {
      const p = d.pair || d.impair;
      const week = p && p.week ? p.week : null;
      const fri = p && p.fri ? p.fri : null;
      const hs = week && isFinite(week.s) ? week.s : null;
      const he = week && isFinite(week.e) ? week.e : null;
      const fs = fri && isFinite(fri.s) ? fri.s : hs;
      const fe = fri && isFinite(fri.e) ? fri.e : he;
      function pair(a, b) {
        if (a == null || b == null) return null;
        return macFloatToHm(a) + ',' + macFloatToHm(b);
      }
      const payload = {
        horaires_lundi: pair(hs, he),
        horaires_mardi: pair(hs, he),
        horaires_mercredi: pair(hs, he),
        horaires_jeudi: pair(hs, he),
        horaires_vendredi: pair(fs, fe),
      };
      Object.keys(payload).forEach(k => { if (!payload[k]) delete payload[k]; });
      if (Object.keys(payload).length) {
        await api('/api/planning/machines/' + id + '/horaires-bulk', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      }
    }
    toast('Horaires réinitialisés.');
    await loadMacMachineDetail();
    await loadMachines();
  } catch (e) {
    toast(e.message || 'Erreur réinitialisation', true);
  }
}

async function saveMacMetrage() {
  if (!macMachine) return;
  const raw = (document.getElementById('mac-metrage-inp').value || '').trim().replace(/\s/g, '').replace(',', '.');
  let val = null;
  if (raw !== '') {
    val = parseFloat(raw);
    if (!isFinite(val) || val < 0) {
      toast('Métrage invalide — valeur positive ou nulle attendue.', true);
      return;
    }
  }
  const lbl = macMachine.nom || ('Machine ' + macMachine.id);
  const msg = val == null
    ? 'Effacer le compteur de « ' + lbl + ' » ?'
    : 'Enregistrer le compteur à ' + Math.round(val).toLocaleString('fr-FR') + ' m pour « ' + lbl + ' » ?';
  if (!confirm(msg)) return;
  try {
    await api('/api/settings/machines/' + macMachine.id + '/dernier-metrage', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dernier_metrage: val }),
    });
    toast('Métrage enregistré.');
    await loadMacMachineDetail();
    await loadMachines();
  } catch (e) {
    toast(e.message || 'Erreur enregistrement métrage', true);
  }
}

function initMachinesPanel() {
  fillMacSelect();
  if (!_macPanelReady) {
    _macPanelReady = true;
    document.querySelectorAll('.mac-sub-btn').forEach(b => {
      b.addEventListener('click', () => setMacSubTab(b.dataset.macsub));
    });
    const sel = document.getElementById('mac-select');
    if (sel) sel.addEventListener('change', () => loadMacMachineDetail());
    const hs = document.getElementById('mac-hor-save');
    const hr = document.getElementById('mac-hor-reset');
    const ms = document.getElementById('mac-metr-save');
    const ns = document.getElementById('mac-nom-save');
    if (hs) hs.addEventListener('click', saveMacHoraires);
    if (hr) hr.addEventListener('click', resetMacHoraires);
    if (ms) ms.addEventListener('click', saveMacMetrage);
    if (ns) ns.addEventListener('click', saveMacNom);
  }
  setMacSubTab(macSubTab);
  loadMacMachineDetail();
}

function fillRoleSelect() {
  const s = document.getElementById('cu-role');
  s.innerHTML = assignableRoles.map(r =>
    '<option value="' + esc(r) + '">' + esc(roleLabels[r] || r) + '</option>'
  ).join('');
}

const PROFILE_FIELDS = ['nom', 'email', 'telephone', 'adresse', 'date_naissance'];

function profileFieldFilled(val) {
  return String(val == null ? '' : val).trim().length > 0;
}

function profileCompletionPercent(u) {
  if (!u || typeof u !== 'object') return 0;
  let n = 0;
  PROFILE_FIELDS.forEach((k) => { if (profileFieldFilled(u[k])) n += 1; });
  return Math.round((n / PROFILE_FIELDS.length) * 100);
}

function profileRingTier(pct) {
  if (pct >= 80) return 'high';
  if (pct >= 40) return 'mid';
  return 'low';
}

function profileRingHtml(pct) {
  const p = Math.max(0, Math.min(100, Number(pct) || 0));
  const r = 14;
  const c = 2 * Math.PI * r;
  const off = c * (1 - p / 100);
  const tier = profileRingTier(p);
  return '<span class="prof-ring" data-tier="' + tier + '" title="Profil complété à ' + p + ' %">' +
    '<svg viewBox="0 0 34 34" aria-hidden="true">' +
    '<circle class="prof-ring-track" cx="17" cy="17" r="' + r + '" fill="none" stroke-width="3"/>' +
    '<circle class="prof-ring-bar" cx="17" cy="17" r="' + r + '" fill="none" stroke-width="3"' +
    ' stroke-dasharray="' + c.toFixed(2) + '" stroke-dashoffset="' + off.toFixed(2) + '"' +
    ' transform="rotate(-90 17 17)"/>' +
    '</svg>' +
    '<span class="prof-ring-label">' + p + '%</span>' +
    '</span>';
}

async function loadUsers() {
  const list = await api('/api/users');
  usersAll = Array.isArray(list) ? list.slice() : [];
  usersAll.sort((a,b)=>{
    // Tri par service (rôle) d'abord, puis par nom alphabétique
    const roleA = String(a && a.role || '').toLowerCase();
    const roleB = String(b && b.role || '').toLowerCase();
    if(roleA !== roleB) return roleA.localeCompare(roleB,'fr');
    const an = _norm(a && a.nom);
    const bn = _norm(b && b.nom);
    if(an !== bn) return an.localeCompare(bn,'fr');
    return _norm(a && a.email).localeCompare(_norm(b && b.email),'fr');
  });
  renderUsersList();
}

function renderUsersList(){
  const box = document.getElementById('users-list');
  const hint = document.getElementById('users-q-hint');
  if(!box) return;
  if(!usersAll.length){
    box.innerHTML = '<p class="sub">Aucun utilisateur.</p>';
    if(hint) hint.textContent = '';
    return;
  }

  const q = _norm(usersQuery);
  const tokens = q ? q.split(' ').filter(Boolean) : [];
  let list = usersAll;

  // Filtrage par service (rôle)
  if(usersRoleFilter && usersRoleFilter !== ''){
    list = list.filter(u => (u.role || '') === usersRoleFilter);
  }

  if(tokens.length){
    const scored = [];
    for(const u of list){
      const hay = userHaystack(u);
      const sc = scoreMatch(hay, tokens);
      if(sc != null) scored.push({u, sc});
    }
    scored.sort((a,b)=> (a.sc - b.sc) || _norm(a.u.nom).localeCompare(_norm(b.u.nom),'fr'));
    list = scored.map(x=>x.u);
  }
  if(hint) hint.textContent = (list.length + '/' + usersAll.length);

  box.innerHTML = list.map(u => {
    const act = Number(u.actif) === 1;
    const role = String(u.role || '').toLowerCase().trim();
    const pillCls = 'pill pill--' + esc(role || 'fabrication');
    const meta = [
      u.identifiant ? ('Id: ' + esc(u.identifiant)) : '',
      u.operateur_lie ? ('Op: ' + esc(u.operateur_lie)) : '',
      u.machine_nom ? ('Machine: ' + esc(u.machine_nom)) : '',
      u.telephone ? ('Tel: ' + esc(u.telephone)) : '',
    ].filter(Boolean).join(' · ');
    const profPct = profileCompletionPercent(u);
    return '<div class="row-user">' +
      '<div style="display:flex;align-items:center;gap:10px">' +
        profileRingHtml(profPct) +
        '<div><strong>' + esc(u.nom) + '</strong> <span class="' + pillCls + '">' + esc(roleLabels[u.role] || u.role) + '</span>' +
        (u.nc_service_override === 'encadrement_atelier'
          ? ' <span class="pill pill--encadrement_atelier" title="Service NC : chef d\'équipe atelier / responsable technique">Chef d\'équipe atelier / Resp. tech.</span>'
          : '') +
        (act ? '' : ' <span class="pill pill--inactive">Inactif</span>') +
        '<div style="font-size:11px;color:var(--muted);margin-top:4px">' + esc(u.email) + (meta ? (' · ' + meta) : '') + '</div></div>' +
        '<button type="button" class="btn btn-sec copy-user-btn" data-copy="' + u.id + '" title="Copier les identifiants" style="padding:6px 8px">' +
          '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>' +
        '</button>' +
      '</div>' +
      '<div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">' +
      '<button type="button" class="btn btn-sec" data-edit="' + u.id + '">Modifier</button>' +
      '<button type="button" class="btn btn-sec" data-reset="' + u.id + '">Reset MDP</button>' +
      (act ? '<button type="button" class="btn btn-sec" data-off="' + u.id + '">Désactiver</button>'
        : '<button type="button" class="btn btn-sec" data-on="' + u.id + '">Réactiver</button>') +
      '<button type="button" class="btn btn-sec" data-del="' + u.id + '" title="Supprimer" style="color:var(--danger);padding:6px 8px">' +
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>' +
      '</button>' +
      '</div></div>';
  }).join('');

  box.querySelectorAll('[data-edit]').forEach(b => b.onclick = () => openEdit(Number(b.dataset.edit)));
  box.querySelectorAll('[data-reset]').forEach(b => b.onclick = () => resetPwd(Number(b.dataset.reset)));
  box.querySelectorAll('[data-off]').forEach(b => b.onclick = () => setActif(Number(b.dataset.off), 0));
  box.querySelectorAll('[data-on]').forEach(b => b.onclick = () => setActif(Number(b.dataset.on), 1));
  box.querySelectorAll('[data-copy]').forEach(b => b.onclick = () => copyUserCredentials(Number(b.dataset.copy)));
  box.querySelectorAll('[data-del]').forEach(b => b.onclick = () => deleteUser(Number(b.dataset.del)));
}

async function deleteUser(id) {
  const u = usersAll.find(x => x.id === id);
  if (!u) return;
  const isAdmin = (u.email || '').toLowerCase().includes('admin') || (u.nom || '').toLowerCase() === 'administrateur';
  if (isAdmin) {
    toast('Impossible de supprimer un administrateur', 'error');
    return;
  }
  const hasLinkages = u.operateur_lie || u.identifiant || (u.machine_nom && u.machine_nom !== '—');
  const warningMsg = hasLinkages ? '\n\n⚠️ Cet utilisateur est lié à des données (opérateur, machine...). La suppression peut affecter l\'historique.' : '';
  if (!confirm('Supprimer définitivement l\'utilisateur "' + u.nom + '" (' + u.email + ') ?' + warningMsg + '\n\nCette action est irréversible.')) return;
  try {
    await api('/api/users/' + id, { method: 'DELETE' });
    toast('Utilisateur supprimé', 'success');
    await loadUsers();
    await loadMatrix();
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function setActif(id, v) {
  try {
    await api('/api/users/' + id, { method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ actif: v }) });
    toast(v ? 'Compte réactivé' : 'Compte désactivé');
    await loadUsers();
    await loadMatrix();
  } catch (e) { toast(e.message, true); }
}

async function resetPwd(id) {
  if (!confirm('Générer un mot de passe temporaire ?')) return;
  try {
    const r = await api('/api/users/' + id + '/reset-password', { method: 'POST' });
    if (r && r.temp_password) alert('Mot de passe temporaire : ' + r.temp_password);
    toast('Mot de passe régénéré');
  } catch (e) { toast(e.message, true); }
}

async function copyUserCredentials(id) {
  const u = usersAll.find(x => x.id === id);
  if (!u) return;
  const lines = [
    'Nom : ' + (u.nom || ''),
    'Email : ' + (u.email || ''),
    'Identifiant : ' + (u.identifiant || ''),
    'Rôle : ' + (roleLabels[u.role] || u.role || ''),
  ];
  if (u.operateur_lie) lines.push('Opérateur : ' + u.operateur_lie);
  if (u.machine_nom) lines.push('Machine : ' + u.machine_nom);
  if (u.telephone) lines.push('Téléphone : ' + u.telephone);
  const text = lines.join('\n');
  try {
    await navigator.clipboard.writeText(text);
    toast('Identifiants copiés');
  } catch (e) {
    toast('Erreur copie : ' + e.message, true);
  }
}

function downloadUsersCSV(){
  // Exporter tous les utilisateurs (pas seulement les filtrés)
  if(!usersAll || usersAll.length===0){
    toast('Aucun utilisateur à exporter', true);
    return;
  }
  const headers=['Nom','Email','Rôle','Actif','Dernière connexion','Opérateur lié','Machine'];
  const rows=usersAll.map(u=>{
    const nom=esc(u.nom||'');
    const email=esc(u.email||'');
    const role=esc(roleLabels[u.role]||u.role||'');
    const actif=u.actif?'Oui':'Non';
    const lastLogin=u.last_login?new Date(u.last_login).toLocaleString('fr-FR'):'Jamais';
    const op=esc(u.operateur||'');
    const mac=esc(u.machine_nom||'');
    return [nom,email,role,actif,lastLogin,op,mac].map(f=>'"'+f.replace(/"/g,'""')+'"').join(';');
  });
  const csv=[headers.join(';')].concat(rows).join('\n');
  const blob=new Blob([csv],{type:'text/csv;charset=utf-8;'});
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a');
  a.href=url;
  a.download='utilisateurs_mysifa_'+new Date().toISOString().slice(0,10)+'.csv';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  toast(usersAll.length+' utilisateurs exportés');
}

function syncCuRoleUI() {
  const r = document.getElementById('cu-role').value;
  // Cacher opérateur lié pour fabrication et les autres rôles hors production
  const hideOp = ['fabrication', 'direction', 'administration', 'administration_ventes', 'administration_technique', 'logistique', 'comptabilite', 'expedition', 'superadmin'].indexOf(r) >= 0;
  document.getElementById('cu-op').style.display = hideOp ? 'none' : '';
  document.getElementById('cu-mac').style.display = r === 'fabrication' ? '' : 'none';
}
document.getElementById('cu-role').addEventListener('change', syncCuRoleUI);

document.getElementById('cu-go').onclick = async () => {
  const nom = document.getElementById('cu-nom').value.trim();
  const identifiant = document.getElementById('cu-ident').value.trim();
  const email = document.getElementById('cu-email').value.trim();
  const password = document.getElementById('cu-pwd').value;
  const role = document.getElementById('cu-role').value;
  const operateur_lie = document.getElementById('cu-op').value || null;
  const mid = document.getElementById('cu-mac').value;
  const machine_id = mid ? Number(mid) : null;
  if (!nom || !email || !password || !role) return toast('Champs requis', true);
  try {
    await api('/api/users', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nom, identifiant, email, password, role, operateur_lie, machine_id }) });
    toast('Utilisateur créé');
    document.getElementById('cu-nom').value = '';
    document.getElementById('cu-ident').value = '';
    document.getElementById('cu-email').value = '';
    document.getElementById('cu-pwd').value = '';
    await loadUsers();
    await loadMatrix();
  } catch (e) { toast(e.message, true); }
};

// Recherche utilisateurs (client-side, sur toutes les colonnes)
try{
  const uq = document.getElementById('users-q');
  if(uq){
    uq.addEventListener('input', ()=>{
      usersQuery = uq.value || '';
      renderUsersList();
    });
  }
}catch(e){}

// Filtre par service
function fillRoleFilterSelect() {
  const sel = document.getElementById('users-role-filter');
  if(!sel) return;
  sel.innerHTML = '<option value="">Tous les services</option>' +
    assignableRoles.map(r => '<option value="' + esc(r) + '">' + esc(roleLabels[r] || r) + '</option>').join('');
}
try{
  const rf = document.getElementById('users-role-filter');
  if(rf){
    rf.addEventListener('change', ()=>{
      usersRoleFilter = rf.value || '';
      renderUsersList();
    });
  }
}catch(e){}

async function openEdit(id) {
  let u;
  try { u = await api('/api/users/' + id); } catch (e) { toast(e.message, true); return; }
  const backdrop = document.createElement('div');
  backdrop.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:800;display:flex;align-items:center;justify-content:center;padding:16px';
  const dlg = document.createElement('div');
  dlg.style.cssText = 'background:var(--card);border:1px solid var(--border);border-radius:16px;padding:20px;max-width:440px;width:100%;max-height:90vh;overflow:auto';
  const isDesignatedSup = superadminEmailRef && String(u.email || '').trim().toLowerCase() === superadminEmailRef && u.role === 'superadmin';
  const roleOpts = isDesignatedSup
    ? '<option value="superadmin" selected>Super admin</option>'
    : assignableRoles.map(r => '<option value="' + esc(r) + '"' + (u.role === r ? ' selected' : '') + '>' + esc(roleLabels[r] || r) + '</option>').join('');

  dlg.innerHTML = '<h3 style="margin:0 0 12px;font-size:16px">Modifier</h3>' +
    '<label class="sub">Nom</label><input id="ed-nom" value="' + esc(u.nom) + '" style="margin-bottom:10px">' +
    '<label class="sub">Identifiant</label><input id="ed-ident" value="' + esc(u.identifiant || '') + '" style="margin-bottom:10px" placeholder="auto si vide">' +
    '<label class="sub">Email</label><input id="ed-email" type="email" value="' + esc(u.email) + '" style="margin-bottom:10px"' + (isDesignatedSup ? ' disabled' : '') + '>' +
    '<label class="sub">Téléphone</label><input id="ed-tel" value="' + esc(u.telephone || '') + '" style="margin-bottom:10px" placeholder="">' +
    '<label class="sub">Adresse</label><input id="ed-adr" value="' + esc(u.adresse || '') + '" style="margin-bottom:10px" placeholder="">' +
    '<label class="sub">Date de naissance</label><input id="ed-birth" type="date" value="' + esc(u.date_naissance || '') + '" style="margin-bottom:10px">' +
    '<label class="sub">Rôle</label><select id="ed-role" style="margin-bottom:10px"' + (isDesignatedSup ? ' disabled' : '') + '>' + roleOpts + '</select>' +
    '<div id="ed-op-wrap"><label class="sub">Opérateur lié</label><select id="ed-op" style="margin-bottom:10px">' +
    '<option value="">—</option>' + operators.map(o => '<option value="' + esc(o) + '"' + (u.operateur_lie === o ? ' selected' : '') + '>' + esc(o) + '</option>').join('') + '</select></div>' +
    '<div id="ed-mac-wrap"><label class="sub" title="Machine par défaut utilisée uniquement si l\'opérateur n\'est pas planifié au Planning RH du jour. Sinon, la machine réelle vient du Planning RH (matin/après-midi/nuit).">Machine par défaut <span style="color:var(--muted);font-weight:400;font-size:11px">(fallback si non planifié RH)</span></label><select id="ed-mac" style="margin-bottom:10px">' +
    '<option value="">—</option>' + machines.map(m => '<option value="' + esc(m.id) + '"' + (String(u.machine_id) === String(m.id) ? ' selected' : '') + '>' + esc(m.nom) + '</option>').join('') + '</select></div>' +
    '<label class="sub" style="display:flex;align-items:center;gap:8px"><input type="checkbox" id="ed-act" ' + (Number(u.actif) === 1 ? 'checked' : '') + '> Compte actif</label>' +
    '<label class="sub">Nouveau mot de passe (optionnel)</label><input id="ed-pwd" type="password" style="margin-bottom:10px">' +
    '<label class="sub">Service NC (surcharge)</label>' +
    '<select id="ed-nc-svc" style="margin-bottom:4px">' +
    '<option value=""' + (!u.nc_service_override ? ' selected' : '') + '>— Aucune (utilise le rôle) —</option>' +
    '<option value="encadrement_atelier"' + (u.nc_service_override === "encadrement_atelier" ? ' selected' : '') + '>Chef d\'équipe atelier / Resp. technique</option>' +
    '</select>' +
    '<div class="sub" style="font-size:10px;color:var(--muted);margin-bottom:10px;line-height:1.4">Rattache l\'utilisateur à un service de prise en connaissance des NC indépendamment de son rôle métier.</div>' +
    '<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:14px">' +
    '<button type="button" class="btn btn-sec" id="ed-cancel">Annuler</button>' +
    '<button type="button" class="btn" id="ed-save">Enregistrer</button></div>';

  function syncEd() {
    const r = dlg.querySelector('#ed-role').value;
    // Cacher opérateur lié pour fabrication et les autres rôles hors production
    const hideOp = ['fabrication', 'direction', 'administration', 'administration_ventes', 'administration_technique', 'logistique', 'comptabilite', 'expedition', 'superadmin'].indexOf(r) >= 0;
    dlg.querySelector('#ed-op-wrap').style.display = hideOp ? 'none' : '';
    dlg.querySelector('#ed-mac-wrap').style.display = (r === 'fabrication') ? '' : 'none';
  }
  dlg.querySelector('#ed-role').addEventListener('change', syncEd);
  syncEd();

  dlg.querySelector('#ed-cancel').onclick = () => backdrop.remove();
  dlg.querySelector('#ed-save').onclick = async () => {
    const body = {
      nom: dlg.querySelector('#ed-nom').value.trim(),
      identifiant: dlg.querySelector('#ed-ident').value.trim(),
      email: dlg.querySelector('#ed-email').value.trim(),
      telephone: dlg.querySelector('#ed-tel').value.trim(),
      adresse: dlg.querySelector('#ed-adr').value.trim(),
      date_naissance: dlg.querySelector('#ed-birth').value.trim(),
      role: dlg.querySelector('#ed-role').value,
      operateur_lie: dlg.querySelector('#ed-op').value || null,
      machine_id: dlg.querySelector('#ed-mac').value ? Number(dlg.querySelector('#ed-mac').value) : null,
      actif: dlg.querySelector('#ed-act').checked ? 1 : 0,
      nc_service_override: dlg.querySelector('#ed-nc-svc').value || null,
    };
    const np = dlg.querySelector('#ed-pwd').value;
    if (np) body.password = np;
    try {
      await api('/api/users/' + id, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      toast('Utilisateur mis à jour');
      backdrop.remove();
      await loadUsers();
      await loadMatrix();
    } catch (e) { toast(e.message, true); }
  };

  backdrop.appendChild(dlg);
  backdrop.onclick = (e) => { if (e.target === backdrop) backdrop.remove(); };
  document.body.appendChild(backdrop);
}

// ─── Matrice d'accès v2 (database-driven, 4 niveaux) ─────────────
// none / read / write / admin. Chaque cellule = un select. Bouton [+] dans le
// header d'une app pour déplier les sous-modules (onglets). Le référentiel
// des rôles est édité dans le panneau Référentiel (loadRoleDefaults).

const LEVEL_TITLE = { none: 'Aucun accès', read: 'Lecture', write: 'Écriture', admin: 'Admin' };
const LEVEL_LIST = ['none', 'read', 'write', 'admin'];
let matrixExpandedApp = null;
let roleDefaultsSnapshot = [];

function _lvlOpts(cur, includeDefault) {
  const opts = LEVEL_LIST.map(l => (
    '<option value="' + l + '"' + (cur === l ? ' selected' : '') + '>' + esc(LEVEL_TITLE[l]) + '</option>'
  )).join('');
  return (includeDefault ? '<option value="">— Défaut du rôle —</option>' : '') + opts;
}

function _cellUserSelect(uid, app_id, module_id, cur, isOverride, isDisabled) {
  return '<select class="acc-lvl' + (isOverride ? ' is-ov' : '') + '" ' +
    'data-uid="' + uid + '" data-app="' + esc(app_id) + '" data-mod="' + esc(module_id) + '"' +
    (isDisabled ? ' disabled' : '') + '>' + _lvlOpts(isOverride ? cur : '', true) + '</select>' +
    (isOverride ? '<span class="cell-ov" title="Surcharge personnelle">perso</span>' : '');
}

async function setUserAccess(uid, app_id, module_id, level) {
  try {
    await api('/api/settings/access-matrix/user/' + uid, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ app_id, module_id, level: level || null }),
    });
    toast(level ? 'Accès mis à jour' : 'Retour au défaut du rôle');
    await loadMatrix();
    await loadUsers();
  } catch (e) {
    toast(e.message, true);
    await loadMatrix();
  }
}

async function setRoleDefault(role, app_id, module_id, level) {
  try {
    await api('/api/settings/role-defaults/' + encodeURIComponent(role), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ app_id, module_id, level: level || null }),
    });
    toast('Défaut du rôle mis à jour');
    await loadMatrix();
    await loadUsers();
  } catch (e) {
    toast(e.message, true);
    await loadMatrix();
  }
}

async function loadMatrix() {
  const data = await api('/api/settings/access-matrix');
  if (!data) return;
  apps = data.apps || [];
  roleLabels = data.role_labels || roleLabels;
  matrixSnapshot = data.users || [];

  const appTh = apps.map(a => {
    const openable = a.modules && a.modules.length;
    const btn = openable
      ? '<button type="button" class="acc-expand" data-app="' + esc(a.id) + '" title="Détails par onglet">'
        + (matrixExpandedApp === a.id ? '−' : '+') + '</button>'
      : '';
    return '<th><span class="acc-th-lbl">' + esc(a.label) + '</span>' + btn + '</th>';
  }).join('');
  const th = '<th>Utilisateur</th><th>Rôle</th>' + appTh;

  const rowsHtml = matrixSnapshot.map(row => {
    const isRowSuper = row.role === 'superadmin';
    const isInactive = Number(row.actif) !== 1;
    const overrideSet = new Set((row.overrides || []).map(o => o.app_id + '|' + o.module_id));

    const cellsApp = apps.map(a => {
      const cur = (row.access[a.id] && row.access[a.id]['_app']) || 'none';
      if (a.id === 'settings' || isRowSuper) {
        return '<td class="acc-cell readonly" title="Non modifiable"><span class="lvl-badge lvl-' + cur + '">' + esc(LEVEL_TITLE[cur] || cur) + '</span></td>';
      }
      const isOv = overrideSet.has(a.id + '|_app');
      return '<td class="acc-cell">' + _cellUserSelect(row.id, a.id, '_app', cur, isOv, isInactive) + '</td>';
    }).join('');

    let base = '<tr' + (isInactive ? ' style="opacity:.55"' : '') + '>' +
      '<td><strong>' + esc(row.nom) + '</strong><div style="font-size:11px;color:var(--muted)">' + esc(row.email) + '</div></td>' +
      '<td>' + esc(row.role_label || row.role) + '</td>' + cellsApp + '</tr>';

    if (matrixExpandedApp) {
      const app = apps.find(a => a.id === matrixExpandedApp);
      if (app && app.modules && app.modules.length) {
        const subCells = apps.map(a => {
          if (a.id !== matrixExpandedApp) return '<td class="acc-sub-empty"></td>';
          const subRows = app.modules.map(m => {
            const cur = (row.access[a.id] && row.access[a.id][m.id]) || 'none';
            const isOv = overrideSet.has(a.id + '|' + m.id);
            const editor = (isRowSuper || a.id === 'settings')
              ? '<span class="lvl-badge lvl-' + cur + '">' + esc(LEVEL_TITLE[cur]) + '</span>'
              : _cellUserSelect(row.id, a.id, m.id, cur, isOv, isInactive);
            return '<div class="acc-sub-row"><span class="acc-sub-label">' + esc(m.label) + '</span>' + editor + '</div>';
          }).join('');
          return '<td class="acc-sub">' + subRows + '</td>';
        }).join('');
        base += '<tr class="acc-sub-tr"><td colspan="2" class="acc-sub-title">' + esc(app.label) + ' · onglets</td>' + subCells + '</tr>';
      }
    }
    return base;
  }).join('');

  const wrap = document.getElementById('matrix-table');
  wrap.innerHTML = '<table class="acc-matrix"><thead><tr>' + th + '</tr></thead><tbody>' + rowsHtml + '</tbody></table>';
  wrap.querySelectorAll('.acc-lvl').forEach(sel => {
    sel.addEventListener('change', () => setUserAccess(Number(sel.dataset.uid), sel.dataset.app, sel.dataset.mod, sel.value || ''));
  });
  wrap.querySelectorAll('.acc-expand').forEach(btn => {
    btn.addEventListener('click', () => {
      const aid = btn.dataset.app;
      matrixExpandedApp = (matrixExpandedApp === aid) ? null : aid;
      loadMatrix();
    });
  });

  await loadRoleDefaults();
}

let defaultsExpandedApp = null;

async function loadRoleDefaults() {
  const data = await api('/api/settings/role-defaults');
  if (!data) return;
  roleDefaultsSnapshot = data.roles || [];
  const leg = document.getElementById('role-legend');
  if (!leg) return;

  const appList = data.apps || apps;
  const roles = roleDefaultsSnapshot;

  // Vue transposée : lignes = apps (avec sous-modules dépliables), colonnes = rôles.
  const rolesTh = roles.map(r => (
    '<th class="acc-role-th" title="' + esc(r.role) + '"><span>' + esc(r.label) + '</span>' +
    (r.readonly ? ' <span class="acc-lock" title="Non modifiable">🔒</span>' : '') + '</th>'
  )).join('');
  const th = '<th class="acc-app-col">Application</th>' + rolesTh;

  const rowsHtml = appList.map(app => {
    const openable = app.modules && app.modules.length;
    const isExpanded = defaultsExpandedApp === app.id;
    const btn = openable
      ? '<button type="button" class="acc-expand" data-app="' + esc(app.id) + '" title="Détails par onglet">' + (isExpanded ? '−' : '+') + '</button>'
      : '';
    const appCell = '<td class="acc-app-cell"><strong>' + esc(app.label) + '</strong>' + btn + '</td>';
    const cellsPerRole = roles.map(r => {
      const cur = (r.access[app.id] && r.access[app.id]['_app']) || 'none';
      if (app.id === 'settings' || r.readonly) {
        return '<td class="acc-cell readonly"><span class="lvl-badge lvl-' + cur + '">' + esc(LEVEL_TITLE[cur] || cur) + '</span></td>';
      }
      return '<td class="acc-cell"><select class="rd-lvl" data-role="' + esc(r.role) + '" data-app="' + esc(app.id) + '" data-mod="_app">' + _lvlOpts(cur, false) + '</select></td>';
    }).join('');
    let out = '<tr class="acc-app-row">' + appCell + cellsPerRole + '</tr>';
    if (isExpanded && openable) {
      out += app.modules.map(m => {
        const subCells = roles.map(r => {
          const cur = (r.access[app.id] && r.access[app.id][m.id]) || 'none';
          if (app.id === 'settings' || r.readonly) {
            return '<td class="acc-cell readonly acc-sub-cell"><span class="lvl-badge lvl-' + cur + '">' + esc(LEVEL_TITLE[cur] || cur) + '</span></td>';
          }
          return '<td class="acc-cell acc-sub-cell"><select class="rd-lvl" data-role="' + esc(r.role) + '" data-app="' + esc(app.id) + '" data-mod="' + esc(m.id) + '">' + _lvlOpts(cur, false) + '</select></td>';
        }).join('');
        return '<tr class="acc-sub-tr"><td class="acc-app-cell acc-sub-label-cell">↳ ' + esc(m.label) + '</td>' + subCells + '</tr>';
      }).join('');
    }
    return out;
  }).join('');

  leg.innerHTML = '<div class="acc-hint">Modifier un défaut ici change tous les utilisateurs du rôle qui n\'ont pas de surcharge personnelle. ' +
    'Le super admin est intouchable. Bouton [+] pour éditer les niveaux onglet par onglet.</div>' +
    '<div class="table-wrap"><table class="acc-matrix acc-matrix-defaults"><thead><tr>' + th + '</tr></thead><tbody>' + rowsHtml + '</tbody></table></div>';

  leg.querySelectorAll('.rd-lvl').forEach(sel => {
    sel.addEventListener('change', () => setRoleDefault(sel.dataset.role, sel.dataset.app, sel.dataset.mod, sel.value));
  });
  leg.querySelectorAll('.acc-expand').forEach(btn => {
    btn.addEventListener('click', () => {
      const aid = btn.dataset.app;
      defaultsExpandedApp = (defaultsExpandedApp === aid) ? null : aid;
      loadRoleDefaults();
    });
  });
}

// ─── Fournisseurs FSC ──────────────────────────────────────────────

let fournisseursAll = [];

// Sub-tab navigation for fournisseurs
document.querySelectorAll('.four-sub-btn').forEach(b => {
  b.addEventListener('click', () => {
    document.querySelectorAll('.four-sub-btn').forEach(x => x.classList.toggle('active', x.dataset.foursub === b.dataset.foursub));
    ['four-certifs', 'four-hist', 'four-contacts'].forEach(id => {
      if (id === 'four-contacts' && b.dataset.foursub === 'four-contacts') { renderFournisseursContactsTable(); }
      const el = document.getElementById(id);
      if (el) el.classList.toggle('hidden', id !== b.dataset.foursub);
    });
    if (b.dataset.foursub === 'four-hist') fillFourHistSelect();
  });
});

let fourViewMode = 'flat';
let fourSearchQuery = '';
let fourFilterFsc = '';
let fourFilterGroupe = '';
let fourFilterTraca = '';

async function loadFournisseurs() {
  try {
    const data = await api('/api/fournisseurs');
    fournisseursAll = Array.isArray(data) ? data : [];
  } catch (e) { fournisseursAll = []; toast(e.message, true); }
  fillFourGroupeFilter();
  renderFournisseursTable();
  fillFourHistSelect();
}

function fillFourGroupeFilter() {
  const sel = document.getElementById('four-filter-groupe');
  if (!sel) return;
  const cur = sel.value;
  const groupes = new Set();
  fournisseursAll.forEach(f => { if (f.groupe && f.groupe.trim()) groupes.add(f.groupe.trim()); });
  const list = [...groupes].sort((a,b) => a.localeCompare(b, 'fr', {sensitivity:'base'}));
  sel.innerHTML = '<option value="">Tous les groupes</option>' +
    list.map(g => '<option value="' + esc(g) + '">' + esc(g) + '</option>').join('');
  if (list.includes(cur)) sel.value = cur;
}

function _fourNorm(s){
  return String(s||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
}
function _fourHay(f){
  const hasFsc = (f.has_fsc == null) ? true : !!f.has_fsc;
  return _fourNorm([f.nom, f.groupe, f.branche, hasFsc ? f.licence : '', hasFsc ? f.certificat : '', hasFsc ? 'fsc certifie' : 'non certifie'].filter(Boolean).join(' '));
}
function _fourHasTraca(f){ return !!(f.traca_photo_url || f.traca_explication || f.traca_exemple_code); }

function _fourFiltered(){
  const q = _fourNorm(fourSearchQuery).trim();
  return fournisseursAll.filter(f => {
    const hasFsc = (f.has_fsc == null) ? true : !!f.has_fsc;
    if (fourFilterFsc === '1' && !hasFsc) return false;
    if (fourFilterFsc === '0' && hasFsc) return false;
    if (fourFilterGroupe && (f.groupe || '') !== fourFilterGroupe) return false;
    const hasT = _fourHasTraca(f);
    if (fourFilterTraca === '1' && !hasT) return false;
    if (fourFilterTraca === '0' && hasT) return false;
    if (q && !_fourHay(f).includes(q)) return false;
    return true;
  });
}

function _fourRowHTML(f){
  const hasFsc = (f.has_fsc == null) ? true : !!f.has_fsc;
  const fscBadge = hasFsc
    ? '<span class="four-pill fsc">FSC</span>'
    : '<span class="four-pill nofsc">— Non</span>';
  const groupeCell = f.groupe
    ? '<span class="four-groupe-tag">' + esc(f.groupe) + (f.branche ? '<span class="fgt-branche">· ' + esc(f.branche) + '</span>' : '') + '</span>'
    : '<span style="color:var(--muted);font-size:11px">—</span>';
  const tracaCell = _fourHasTraca(f)
    ? '<span class="four-pill traca">✓ Guide</span>'
    : '<span class="four-pill traca-no">—</span>';
  return '<tr>' +
    '<td class="four-nom-cell"><strong>' + esc(f.nom) + '</strong>' +
      (f.branche && !f.groupe ? '<small>Branche : ' + esc(f.branche) + '</small>' : '') + '</td>' +
    '<td>' + fscBadge + '</td>' +
    '<td class="four-code-cell"><code>' + esc(hasFsc ? (f.licence || '—') : '—') + '</code></td>' +
    '<td class="four-code-cell"><code>' + esc(hasFsc ? (f.certificat || '—') : '—') + '</code></td>' +
    '<td>' + groupeCell + '</td>' +
    '<td>' + tracaCell + '</td>' +
    '<td class="four-act">' +
      '<button type="button" class="btn btn-sec btn-sm" data-fedit="' + f.id + '">Modifier</button>' +
      '<button type="button" class="btn btn-sec btn-sm" data-fdel="' + f.id + '" style="color:var(--danger)">Supprimer</button>' +
    '</td></tr>';
}

function renderFournisseursTable() {
  const wrap = document.getElementById('four-table-wrap');
  const countEl = document.getElementById('four-count');
  if (!wrap) return;
  const rows = _fourFiltered();
  if (countEl) {
    const total = fournisseursAll.length;
    countEl.textContent = rows.length === total
      ? '· ' + total + ' fournisseur' + (total>1?'s':'')
      : '· ' + rows.length + ' / ' + total + ' fournisseur' + (total>1?'s':'');
  }
  if (!fournisseursAll.length) {
    wrap.innerHTML = '<div class="four-empty"><svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>Aucun fournisseur enregistré. Cliquez « Nouveau fournisseur » pour commencer.</div>';
    return;
  }
  if (!rows.length) {
    wrap.innerHTML = '<div class="four-empty">Aucun fournisseur ne correspond aux filtres.<br><button type="button" class="btn btn-sec btn-sm" style="margin-top:12px" id="four-reset-filters">Réinitialiser les filtres</button></div>';
    const btn = document.getElementById('four-reset-filters');
    if (btn) btn.onclick = () => {
      fourSearchQuery=''; fourFilterFsc=''; fourFilterGroupe=''; fourFilterTraca='';
      const s=document.getElementById('four-search'); if(s) s.value='';
      const f=document.getElementById('four-filter-fsc'); if(f) f.value='';
      const g=document.getElementById('four-filter-groupe'); if(g) g.value='';
      const t=document.getElementById('four-filter-traca'); if(t) t.value='';
      renderFournisseursTable();
    };
    return;
  }
  const head = '<table class="four-table"><thead><tr>' +
    '<th>Nom</th><th>FSC</th><th>Licence FSC</th><th>Certificat FSC</th><th>Groupe / branche</th><th>Traçabilité</th><th></th>' +
    '</tr></thead>';
  let body = '';
  if (fourViewMode === 'groupe') {
    const grouped = {};
    rows.forEach(f => {
      const k = (f.groupe && f.groupe.trim()) || '__none__';
      if (!grouped[k]) grouped[k] = [];
      grouped[k].push(f);
    });
    const keys = Object.keys(grouped).sort((a,b) => {
      if (a === '__none__') return 1;
      if (b === '__none__') return -1;
      return a.localeCompare(b, 'fr', {sensitivity:'base'});
    });
    body = '<tbody>' + keys.map(k => {
      const label = k === '__none__' ? 'Sans groupe' : k;
      const items = grouped[k].sort((a,b) => (a.nom||'').localeCompare(b.nom||'', 'fr', {sensitivity:'base'}));
      return '<tr class="four-groupe-row"><td colspan="7">' + esc(label) + '<span class="fgh-count">· ' + items.length + '</span></td></tr>' +
        items.map(_fourRowHTML).join('');
    }).join('') + '</tbody>';
  } else {
    const sorted = rows.slice().sort((a,b) => (a.nom||'').localeCompare(b.nom||'', 'fr', {sensitivity:'base'}));
    body = '<tbody>' + sorted.map(_fourRowHTML).join('') + '</tbody>';
  }
  wrap.innerHTML = head + body + '</table>';
  wrap.querySelectorAll('[data-fedit]').forEach(b => b.onclick = () => openEditFournisseur(Number(b.dataset.fedit)));
  wrap.querySelectorAll('[data-fdel]').forEach(b => b.onclick = () => deleteFournisseur(Number(b.dataset.fdel)));
}

// Toolbar : recherche + filtres
(function bindFourToolbar(){
  const s = document.getElementById('four-search');
  if (s) s.addEventListener('input', () => {
    const ae = document.activeElement;
    const isSearch = ae && ae.id === 'four-search';
    const caret = isSearch ? [ae.selectionStart, ae.selectionEnd] : null;
    fourSearchQuery = s.value;
    renderFournisseursTable();
    if (isSearch) {
      const el = document.getElementById('four-search');
      if (el) { el.focus(); if (caret) try { el.setSelectionRange(caret[0], caret[1]); } catch(e){} }
    }
  });
  const fFsc = document.getElementById('four-filter-fsc');
  if (fFsc) fFsc.addEventListener('change', () => { fourFilterFsc = fFsc.value; renderFournisseursTable(); });
  const fGrp = document.getElementById('four-filter-groupe');
  if (fGrp) fGrp.addEventListener('change', () => { fourFilterGroupe = fGrp.value; renderFournisseursTable(); });
  const fTra = document.getElementById('four-filter-traca');
  if (fTra) fTra.addEventListener('change', () => { fourFilterTraca = fTra.value; renderFournisseursTable(); });
  document.querySelectorAll('.four-view-toggle [data-fourview]').forEach(b => {
    b.addEventListener('click', () => {
      fourViewMode = b.dataset.fourview;
      document.querySelectorAll('.four-view-toggle [data-fourview]').forEach(x => x.classList.toggle('active', x.dataset.fourview === fourViewMode));
      renderFournisseursTable();
    });
  });
  // Panneau ajout collapsible
  const addToggle = document.getElementById('four-add-toggle');
  const addPanel = document.getElementById('four-add-panel');
  const addCancel = document.getElementById('cf-cancel');
  function showAdd(show) {
    if (!addPanel) return;
    if (show) {
      addPanel.classList.remove('hidden');
      addPanel.style.maxHeight = addPanel.scrollHeight + 'px';
      setTimeout(() => { const n = document.getElementById('cf-nom'); if(n) n.focus(); }, 100);
    } else {
      addPanel.style.maxHeight = '';
      addPanel.classList.add('hidden');
    }
  }
  if (addToggle && addPanel) addToggle.addEventListener('click', () => showAdd(addPanel.classList.contains('hidden')));
  if (addCancel) addCancel.addEventListener('click', () => showAdd(false));
  // Toggle FSC : masquer/afficher les champs licence/certificat dans l'ajout
  const cfFsc = document.getElementById('cf-has-fsc');
  const cfFscFields = document.getElementById('cf-fsc-fields');
  if (cfFsc && cfFscFields) {
    const sync = () => {
      cfFscFields.style.opacity = cfFsc.checked ? '' : '.4';
      cfFscFields.style.pointerEvents = cfFsc.checked ? '' : 'none';
    };
    cfFsc.addEventListener('change', sync);
    sync();
  }
})();

document.getElementById('cf-go').onclick = async () => {
  const nom = document.getElementById('cf-nom').value.trim();
  const licence = document.getElementById('cf-licence').value.trim();
  const certificat = document.getElementById('cf-certificat').value.trim();
  const has_fsc = !!(document.getElementById('cf-has-fsc') || {}).checked;
  const groupe = (document.getElementById('cf-groupe')?.value || '').trim();
  const branche = (document.getElementById('cf-branche')?.value || '').trim();
  if (!nom) return toast('Nom du fournisseur requis', true);
  try {
    await api('/api/fournisseurs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nom, licence, certificat, has_fsc, groupe, branche }),
    });
    toast('Fournisseur ajouté');
    document.getElementById('cf-nom').value = '';
    document.getElementById('cf-licence').value = '';
    document.getElementById('cf-certificat').value = '';
    const cbo = document.getElementById('cf-has-fsc'); if (cbo) cbo.checked = true;
    const cg = document.getElementById('cf-groupe'); if(cg) cg.value = '';
    const cb = document.getElementById('cf-branche'); if(cb) cb.value = '';
    await loadFournisseurs();
    await loadFournisseursGroupes();
    // Replier le panneau d'ajout après succès
    try {
      const ap = document.getElementById('four-add-panel');
      if (ap) { ap.style.maxHeight=''; ap.classList.add('hidden'); }
    } catch(e){}
  } catch (e) { toast(e.message, true); }
};

async function loadFournisseursGroupes(){
  try{
    const r = await api('/api/fournisseurs/groupes');
    if(!r.ok) return;
    const groupes = await r.json();
    const dl = document.getElementById('four-groupes-dl');
    if(dl) dl.innerHTML = groupes.map(g => `<option value="${esc(g.groupe)}">`).join('');
  }catch(e){}
}

async function openEditFournisseur(id) {
  const f = fournisseursAll.find(x => x.id === id);
  if (!f) return;
  const backdrop = document.createElement('div');
  backdrop.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:800;display:flex;align-items:center;justify-content:center;padding:16px';
  const dlg = document.createElement('div');
  dlg.style.cssText = 'background:var(--card);border:1px solid var(--border);border-radius:16px;padding:20px;max-width:440px;width:100%;max-height:90vh;overflow:auto';
  const hasFscInit = (f.has_fsc == null) ? true : !!f.has_fsc;
  dlg.innerHTML = '<h3 style="margin:0 0 12px;font-size:16px">Modifier le fournisseur</h3>' +
    '<label class="sub">Nom</label><input id="ef-nom" value="' + esc(f.nom) + '" style="margin-bottom:10px">' +
    '<label style="display:flex;align-items:center;gap:8px;margin:6px 0 12px;font-size:13px;color:var(--text);cursor:pointer">' +
      '<input type="checkbox" id="ef-has-fsc" ' + (hasFscInit ? 'checked' : '') + ' style="width:16px;height:16px;cursor:pointer">' +
      'Fournisseur certifié FSC</label>' +
    '<div id="ef-fsc-fields" style="' + (hasFscInit ? '' : 'opacity:.4;pointer-events:none') + '">' +
    '<label class="sub">Licence FSC</label><input id="ef-licence" value="' + esc(f.licence || '') + '" style="margin-bottom:10px" placeholder="ex: FSC-C004451">' +
    '<label class="sub">Certificat FSC</label><input id="ef-certificat" value="' + esc(f.certificat || '') + '" style="margin-bottom:10px" placeholder="ex: CU-COC-807907">' +
    '</div>' +
    '<div style="margin-top:14px;padding-top:12px;border-top:1px solid var(--border)">' +
    '<p style="margin:0 0 10px;font-size:13px;font-weight:600;color:var(--text)">Rattachement à un groupe</p>' +
    '<p style="margin:0 0 10px;font-size:12px;color:var(--text2)">Si ce fournisseur est une branche d\'un groupe (ex: Fedrigoni Italy → groupe Fedrigoni, branche Italy).</p>' +
    '<label class="sub">Groupe</label><input id="ef-groupe" value="' + esc(f.groupe || '') + '" style="margin-bottom:10px" placeholder="ex: Fedrigoni" list="four-groupes-dl">' +
    '<label class="sub">Branche</label><input id="ef-branche" value="' + esc(f.branche || '') + '" style="margin-bottom:10px" placeholder="ex: Italy">' +
    '</div>' +
    '<div style="margin-top:16px;padding-top:14px;border-top:1px solid var(--border)">' +
    '<p style="margin:0 0 10px;font-size:13px;font-weight:600;color:var(--text)">Code-barre de traçabilité</p>' +
    '<p style="margin:0 0 10px;font-size:12px;color:var(--text2)">Aide pour les opérateurs : quel code scanner sur les bobines de ce fournisseur.</p>' +
    '<label class="sub">Photo de l\'étiquette</label>' +
    '<div id="ef-photo-preview" style="margin-bottom:10px"></div>' +
    '<input type="file" id="ef-photo-input" accept="image/*" style="display:none">' +
    '<div style="display:flex;gap:8px;margin-bottom:12px">' +
    '<button type="button" class="btn btn-sec" id="ef-photo-pick" style="font-size:12px">Choisir une photo</button>' +
    '<button type="button" class="btn btn-sec" id="ef-photo-del" style="font-size:12px;color:var(--danger);display:none">Supprimer la photo</button></div>' +
    '<label class="sub">Explication (emplacement, description du code)</label>' +
    '<textarea id="ef-traca-exp" placeholder="Ex: Scanner le code en bas à gauche de l\'étiquette bobine — code EAN-13 commençant par 376" ' +
    'style="width:100%;min-height:72px;resize:vertical;margin-bottom:10px;padding:8px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-family:inherit;font-size:13px;box-sizing:border-box"></textarea>' +
    '<label class="sub">Exemple de code (scanner une vraie étiquette pour le remplir)</label>' +
    '<div style="display:flex;gap:8px;align-items:center;margin-bottom:4px">' +
    '<input type="text" id="ef-traca-code" placeholder="Ex: 3760123456789" style="flex:1;font-family:monospace">' +
    '<button type="button" class="btn btn-sec" id="ef-scan-example" style="font-size:12px;white-space:nowrap">Scanner</button></div>' +
    '<p class="sub" style="margin-top:4px;font-size:11px">Utilisez « Scanner » pour remplir automatiquement en scannant une vraie bobine.</p></div>' +
    '<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:14px">' +
    '<button type="button" class="btn btn-sec" id="ef-cancel">Annuler</button>' +
    '<button type="button" class="btn" id="ef-save">Enregistrer</button></div>';

  const expEl = dlg.querySelector('#ef-traca-exp');
  const codeEl = dlg.querySelector('#ef-traca-code');
  const photoPreview = dlg.querySelector('#ef-photo-preview');
  const photoInput = dlg.querySelector('#ef-photo-input');
  const photoDelBtn = dlg.querySelector('#ef-photo-del');
  expEl.value = f.traca_explication || '';
  codeEl.value = f.traca_exemple_code || '';

  function refreshPhotoPreview(url) {
    if (url) {
      photoPreview.innerHTML = '<img src="' + esc(url) + '" alt="" style="max-width:100%;max-height:200px;border-radius:8px;border:1px solid var(--border);display:block;margin-bottom:4px">';
      photoDelBtn.style.display = '';
    } else {
      photoPreview.innerHTML = '<p class="sub" style="margin:0 0 8px;font-size:12px">Aucune photo</p>';
      photoDelBtn.style.display = 'none';
    }
  }
  refreshPhotoPreview(f.traca_photo_url || null);

  dlg.querySelector('#ef-photo-pick').onclick = () => photoInput.click();
  photoInput.onchange = async () => {
    const file = photoInput.files[0];
    photoInput.value = '';
    if (!file) return;
    const fd = new FormData();
    fd.append('photo', file);
    try {
      const res = await fetch(API + '/api/fournisseurs/' + id + '/traca-photo', { method: 'POST', credentials: 'include', body: fd });
      const j = await res.json().catch(() => ({}));
      if (!res.ok) {
        const d = j.detail;
        const msg = typeof d === 'string' ? d : (Array.isArray(d) && d[0] && d[0].msg ? d[0].msg : 'Erreur upload');
        throw new Error(msg);
      }
      refreshPhotoPreview(j.url);
      const fi = fournisseursAll.find(x => x.id === id);
      if (fi) fi.traca_photo_url = j.url;
      toast('Photo enregistrée');
    } catch (e) { toast(e.message, true); }
  };

  photoDelBtn.onclick = async () => {
    if (!confirm('Supprimer la photo ?')) return;
    try {
      const res = await fetch(API + '/api/fournisseurs/' + id + '/traca-photo', { method: 'DELETE', credentials: 'include' });
      const j = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(typeof j.detail === 'string' ? j.detail : 'Erreur');
      refreshPhotoPreview(null);
      const fi = fournisseursAll.find(x => x.id === id);
      if (fi) fi.traca_photo_url = null;
      toast('Photo supprimée');
    } catch (e) { toast(e.message, true); }
  };

  dlg.querySelector('#ef-scan-example').onclick = async () => {
    try {
      if (typeof startTracaExampleScan !== 'function') return;
      await startTracaExampleScan(function(code) { if (code) codeEl.value = code; });
    } catch (e) {}
  };

  const efHasFscCbo = dlg.querySelector('#ef-has-fsc');
  const efFscFields = dlg.querySelector('#ef-fsc-fields');
  if (efHasFscCbo) efHasFscCbo.onchange = () => {
    if (!efFscFields) return;
    efFscFields.style.opacity = efHasFscCbo.checked ? '' : '.4';
    efFscFields.style.pointerEvents = efHasFscCbo.checked ? '' : 'none';
  };

  dlg.querySelector('#ef-cancel').onclick = () => backdrop.remove();
  dlg.querySelector('#ef-save').onclick = async () => {
    const has_fsc = efHasFscCbo ? !!efHasFscCbo.checked : true;
    const body = {
      nom: dlg.querySelector('#ef-nom').value.trim(),
      licence: has_fsc ? dlg.querySelector('#ef-licence').value.trim() : '',
      certificat: has_fsc ? dlg.querySelector('#ef-certificat').value.trim() : '',
      has_fsc,
      traca_explication: expEl.value.trim(),
      traca_exemple_code: codeEl.value.trim(),
      groupe: (dlg.querySelector('#ef-groupe')?.value || '').trim(),
      branche: (dlg.querySelector('#ef-branche')?.value || '').trim(),
    };
    if (!body.nom) return toast('Nom requis', true);
    try {
      await api('/api/fournisseurs/' + id, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const fi = fournisseursAll.find(x => x.id === id);
      if (fi) {
        fi.traca_explication = body.traca_explication || null;
        fi.traca_exemple_code = body.traca_exemple_code || null;
        fi.nom = body.nom;
        fi.licence = body.licence || null;
        fi.certificat = body.certificat || null;
        fi.has_fsc = body.has_fsc ? 1 : 0;
        fi.groupe = body.groupe || null;
        fi.branche = body.branche || null;
      }
      await loadFournisseursGroupes();
      toast('Fournisseur mis à jour');
      backdrop.remove();
      await loadFournisseurs();
    } catch (e) { toast(e.message, true); }
  };
  backdrop.appendChild(dlg);
  backdrop.onclick = (e) => { if (e.target === backdrop) backdrop.remove(); };
  document.body.appendChild(backdrop);
}

async function deleteFournisseur(id) {
  const f = fournisseursAll.find(x => x.id === id);
  if (!f) return;
  if (!confirm('Supprimer le fournisseur "' + f.nom + '" ?')) return;
  try {
    await api('/api/fournisseurs/' + id, { method: 'DELETE' });
    toast('Fournisseur supprimé');
    await loadFournisseurs();
  } catch (e) { toast(e.message, true); }
}

// Historique par fournisseur
function fillFourHistSelect() {
  const sel = document.getElementById('fh-four');
  if (!sel) return;
  const val = sel.value;
  sel.innerHTML = '<option value="">— Choisir un fournisseur —</option>' +
    fournisseursAll.map(f => '<option value="' + f.id + '">' + esc(f.nom) + '</option>').join('');
  sel.value = val;
}

document.getElementById('fh-four').addEventListener('change', async function() {
  const id = Number(this.value);
  const box = document.getElementById('fh-results');
  if (!id) { box.innerHTML = ''; return; }
  box.innerHTML = '<p class="sub">Chargement…</p>';
  try {
    const data = await api('/api/fournisseurs/' + id + '/receptions');
    const recs = data.receptions || [];
    if (!recs.length) {
      box.innerHTML = '<p class="sub">Aucune réception pour ce fournisseur.</p>';
      return;
    }
    box.innerHTML = '<div class="table-wrap"><table><thead><tr><th>Date</th><th>Opérateur</th><th>Bobines</th><th>Certificat FSC</th><th>Note</th></tr></thead><tbody>' +
      recs.map(r => '<tr>' +
        '<td style="font-family:monospace;font-size:12px">' + esc((r.created_at || '').slice(0, 16).replace('T', ' ')) + '</td>' +
        '<td>' + esc(r.created_by_name || '—') + '</td>' +
        '<td>' + esc(r.nb_bobines) + '</td>' +
        '<td><code>' + esc(r.certificat_fsc || '—') + '</code></td>' +
        '<td style="max-width:200px;overflow:hidden;text-overflow:ellipsis">' + esc(r.note || '') + '</td>' +
      '</tr>').join('') + '</tbody></table></div>';
  } catch (e) { box.innerHTML = '<p class="sub" style="color:var(--danger)">' + esc(e.message) + '</p>'; }
});

// ── Fournisseurs — Contacts & infos (Phase 2) ─────────────────────
let fourContactsSearch = '';
let fourContactsFilterLangue = '';
let fourContactsFilterTag = '';
let fourContactsFilterActif = '1';
let _fourContactsCache = {}; // fournisseur_id → contacts[]

function _fourContactsRebuildTagOptions() {
  const sel = document.getElementById('four-contacts-filter-tag');
  if (!sel) return;
  const tags = new Set();
  (fournisseursAll || []).forEach(f => {
    (f.tags || []).forEach(t => { if (t) tags.add(t); });
  });
  const cur = sel.value;
  const opts = ['<option value="">Tag : tous</option>']
    .concat([...tags].sort((a,b)=>a.localeCompare(b,'fr',{sensitivity:'base'}))
      .map(t => '<option value="' + escAttr(t) + '">' + esc(t) + '</option>'));
  sel.innerHTML = opts.join('');
  sel.value = cur;
}

function _fourContactsFilter() {
  const q = (fourContactsSearch || '').trim().toLowerCase();
  const langue = fourContactsFilterLangue;
  const tag = fourContactsFilterTag;
  const actif = fourContactsFilterActif;
  return (fournisseursAll || []).filter(f => {
    if (actif !== '' && String(actif) !== String(f.actif == null ? 1 : (f.actif ? 1 : 0))) return false;
    if (langue && (f.langue_default || 'fr') !== langue) return false;
    if (tag && !((f.tags || []).includes(tag))) return false;
    if (q) {
      const hay = [f.nom, f.ville, f.code_postal, f.groupe, f.branche, f.notes,
                   (f.tags || []).join(' ')].filter(Boolean).join(' ').toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

function _fourContactsRowHTML(f) {
  const actif = f.actif == null || f.actif;
  const nbC = f.nb_contacts || 0;
  const tagsHtml = (f.tags && f.tags.length)
    ? f.tags.slice(0, 3).map(t => '<span class="four-groupe-tag" style="background:var(--accent-bg);color:var(--accent);border-color:var(--accent)">' + esc(t) + '</span>').join(' ')
      + (f.tags.length > 3 ? ' <span class="sub" style="font-size:10px">+' + (f.tags.length - 3) + '</span>' : '')
    : '<span style="color:var(--muted);font-size:11px">—</span>';
  const langueBadge = '<span class="four-pill" style="background:var(--bg);color:var(--text2);border:1px solid var(--border)">'
    + ((f.langue_default || 'fr').toUpperCase()) + '</span>';
  const villeCell = f.ville
    ? esc(f.ville) + (f.code_postal ? '<small style="color:var(--muted);display:block;font-size:10px">' + esc(f.code_postal) + '</small>' : '')
    : '<span style="color:var(--muted);font-size:11px">—</span>';
  const actifBadge = actif
    ? '<span class="four-pill fsc" style="background:rgba(52,211,153,.12);color:var(--ok)">✓ Actif</span>'
    : '<span class="four-pill nofsc">Archivé</span>';
  return '<tr>' +
    '<td class="four-nom-cell"><strong>' + esc(f.nom) + '</strong>' +
      (f.groupe ? '<small>' + esc(f.groupe) + (f.branche ? ' · ' + esc(f.branche) : '') + '</small>' : '') + '</td>' +
    '<td>' + villeCell + '</td>' +
    '<td>' + langueBadge + '</td>' +
    '<td style="max-width:220px">' + tagsHtml + '</td>' +
    '<td style="text-align:center;font-weight:600">' + nbC + '</td>' +
    '<td>' + actifBadge + '</td>' +
    '<td class="four-act">' +
      '<button type="button" class="btn btn-sec btn-sm" data-fcontacts-edit="' + f.id + '">Modifier</button>' +
    '</td></tr>';
}

function renderFournisseursContactsTable() {
  const wrap = document.getElementById('four-contacts-table-wrap');
  const countEl = document.getElementById('four-contacts-count');
  if (!wrap) return;
  _fourContactsRebuildTagOptions();
  const rows = _fourContactsFilter();
  if (countEl) {
    const total = (fournisseursAll || []).length;
    countEl.textContent = rows.length === total
      ? '· ' + total + ' fournisseur' + (total>1?'s':'')
      : '· ' + rows.length + ' / ' + total + ' fournisseur' + (total>1?'s':'');
  }
  if (!(fournisseursAll || []).length) {
    wrap.innerHTML = '<div class="four-empty">Aucun fournisseur. Créez-en depuis l\'onglet Répertoire.</div>';
    return;
  }
  if (!rows.length) {
    wrap.innerHTML = '<div class="four-empty">Aucun fournisseur ne correspond aux filtres.</div>';
    return;
  }
  const sorted = rows.slice().sort((a,b) => (a.nom||'').localeCompare(b.nom||'', 'fr', {sensitivity:'base'}));
  wrap.innerHTML = '<table class="four-table"><thead><tr>' +
    '<th>Nom</th><th>Ville</th><th>Langue</th><th>Tags</th><th style="text-align:center">Contacts</th><th>Statut</th><th></th>' +
    '</tr></thead><tbody>' +
    sorted.map(_fourContactsRowHTML).join('') +
    '</tbody></table>';
  wrap.querySelectorAll('[data-fcontacts-edit]').forEach(b => {
    b.onclick = () => openEditFournisseurInfos(Number(b.dataset['fcontactsEdit']));
  });
}

// Toolbar bindings for contacts sub-tab
(function bindFourContactsToolbar(){
  const s = document.getElementById('four-contacts-search');
  if (s) s.addEventListener('input', () => {
    const ae = document.activeElement;
    const caret = (ae && ae.id === 'four-contacts-search') ? [ae.selectionStart, ae.selectionEnd] : null;
    fourContactsSearch = s.value;
    renderFournisseursContactsTable();
    if (caret) {
      const el = document.getElementById('four-contacts-search');
      if (el) { el.focus(); try { el.setSelectionRange(caret[0], caret[1]); } catch(e){} }
    }
  });
  const fL = document.getElementById('four-contacts-filter-langue');
  if (fL) fL.addEventListener('change', () => { fourContactsFilterLangue = fL.value; renderFournisseursContactsTable(); });
  const fT = document.getElementById('four-contacts-filter-tag');
  if (fT) fT.addEventListener('change', () => { fourContactsFilterTag = fT.value; renderFournisseursContactsTable(); });
  const fA = document.getElementById('four-contacts-filter-actif');
  if (fA) fA.addEventListener('change', () => { fourContactsFilterActif = fA.value; renderFournisseursContactsTable(); });
  const btnCsv = document.getElementById('four-contacts-export');
  if (btnCsv) btnCsv.onclick = () => {
    window.location.href = API + '/api/fournisseurs/export.csv';
  };
})();

async function openEditFournisseurInfos(id) {
  const f = (fournisseursAll || []).find(x => x.id === id);
  if (!f) return;
  let contacts = _fourContactsCache[id];
  if (!contacts) {
    try {
      contacts = await api('/api/fournisseurs/' + id + '/contacts');
      _fourContactsCache[id] = contacts;
    } catch (e) { toast(e.message, true); return; }
  }

  const backdrop = document.createElement('div');
  backdrop.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:800;display:flex;align-items:center;justify-content:center;padding:16px';
  const dlg = document.createElement('div');
  dlg.style.cssText = 'background:var(--card);border:1px solid var(--border);border-radius:16px;padding:20px;max-width:640px;width:100%;max-height:90vh;overflow:auto';
  const actif = f.actif == null || f.actif;
  const langue = f.langue_default || 'fr';
  const tagsCsv = (f.tags || []).join(', ');

  dlg.innerHTML = '<h3 style="margin:0 0 4px;font-size:16px">Modifier — ' + esc(f.nom) + '</h3>' +
    '<p class="sub" style="margin:0 0 14px">Adresse, langue, tags & contacts. La partie FSC/traçabilité reste dans l\'onglet Répertoire.</p>' +
    '<div class="form-grid" style="grid-template-columns:1fr 1fr;gap:10px">' +
    '<div><label class="sub">Nom</label><input id="fi-nom" value="' + escAttr(f.nom) + '"></div>' +
    '<div><label class="sub">Langue AO</label><select id="fi-langue"><option value="fr"' + (langue==='fr'?' selected':'') + '>Français</option><option value="en"' + (langue==='en'?' selected':'') + '>English</option></select></div>' +
    '<div style="grid-column:span 2"><label class="sub">Adresse</label><input id="fi-adresse" value="' + escAttr(f.adresse || '') + '" placeholder="12 rue de l\'Industrie"></div>' +
    '<div><label class="sub">Code postal</label><input id="fi-cp" value="' + escAttr(f.code_postal || '') + '"></div>' +
    '<div><label class="sub">Ville</label><input id="fi-ville" value="' + escAttr(f.ville || '') + '"></div>' +
    '<div><label class="sub">Pays</label><input id="fi-pays" value="' + escAttr(f.pays || 'FR') + '" placeholder="FR"></div>' +
    '<div style="display:flex;align-items:end"><label style="display:flex;align-items:center;gap:8px;font-size:13px;cursor:pointer;user-select:none"><input type="checkbox" id="fi-actif" ' + (actif?'checked':'') + ' style="width:16px;height:16px;cursor:pointer">Actif</label></div>' +
    '<div style="grid-column:span 2"><label class="sub">Tags / spécialités <span style="color:var(--muted);font-weight:400">(séparés par virgules — ex: adhesif, frontal, complexes)</span></label><input id="fi-tags" value="' + escAttr(tagsCsv) + '"></div>' +
    '<div style="grid-column:span 2"><label class="sub">Notes</label><textarea id="fi-notes" style="width:100%;min-height:60px;padding:8px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-family:inherit;font-size:13px;box-sizing:border-box">' + esc(f.notes || '') + '</textarea></div>' +
    '</div>' +
    '<div style="margin-top:18px;padding-top:14px;border-top:1px solid var(--border)">' +
    '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">' +
    '<strong style="font-size:14px">Contacts (' + contacts.length + ')</strong>' +
    '<button type="button" class="btn btn-sec btn-sm" id="fi-add-contact">+ Nouveau contact</button>' +
    '</div>' +
    '<div id="fi-contacts-list"></div>' +
    '</div>' +
    '<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px">' +
    '<button type="button" class="btn btn-sec" id="fi-cancel">Fermer</button>' +
    '<button type="button" class="btn" id="fi-save">Enregistrer les infos</button>' +
    '</div>';

  backdrop.appendChild(dlg);
  document.body.appendChild(backdrop);
  const close = () => backdrop.remove();
  backdrop.addEventListener('click', e => { if (e.target === backdrop) close(); });
  dlg.querySelector('#fi-cancel').onclick = close;

  function renderContactsList() {
    const wrap = dlg.querySelector('#fi-contacts-list');
    if (!contacts.length) {
      wrap.innerHTML = '<p class="sub" style="text-align:center;padding:14px;background:var(--bg);border-radius:8px;border:1px dashed var(--border)">Aucun contact enregistré.</p>';
      return;
    }
    wrap.innerHTML = contacts.map(c => {
      const emails = (c.emails || []).map(e => '<span style="display:inline-block;padding:1px 8px;border-radius:6px;background:var(--accent-bg);color:var(--accent);font-size:11px;margin:1px 2px">' + esc(e) + '</span>').join('');
      const tels = (c.tels || []).map(t => '<span style="display:inline-block;padding:1px 8px;border-radius:6px;background:var(--bg);border:1px solid var(--border);font-size:11px;margin:1px 2px">' + esc(t) + '</span>').join('');
      const pill = c.is_principal ? '<span class="four-pill fsc" style="background:rgba(34,211,238,.14);color:var(--accent);margin-right:6px">★ Principal</span>' : '';
      const inactif = !c.actif ? '<span class="four-pill nofsc" style="margin-right:6px">Archivé</span>' : '';
      return '<div style="padding:10px 12px;border:1px solid var(--border);border-radius:10px;margin-bottom:6px;background:var(--bg)">' +
        '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px">' +
          '<div>' + pill + inactif + '<strong style="font-size:13px">' + esc(c.nom) + '</strong>' +
            (c.fonction ? '<span class="sub" style="margin-left:6px">· ' + esc(c.fonction) + '</span>' : '') +
            '<span class="sub" style="margin-left:6px">· ' + (c.langue || 'fr').toUpperCase() + '</span>' +
          '</div>' +
          '<div>' +
            '<button type="button" class="btn btn-sec" style="padding:3px 8px;font-size:11px" data-fic-edit="' + c.id + '">Modifier</button> ' +
            '<button type="button" class="btn btn-sec" style="padding:3px 8px;font-size:11px;color:var(--danger)" data-fic-del="' + c.id + '">Suppr.</button>' +
          '</div>' +
        '</div>' +
        (emails ? '<div style="margin-top:4px">' + emails + '</div>' : '') +
        (tels ? '<div style="margin-top:4px">' + tels + '</div>' : '') +
      '</div>';
    }).join('');
    wrap.querySelectorAll('[data-fic-edit]').forEach(b => b.onclick = () => openContactSubModal(id, Number(b.dataset.ficEdit), refreshContacts));
    wrap.querySelectorAll('[data-fic-del]').forEach(b => b.onclick = async () => {
      const cid = Number(b.dataset.ficDel);
      if (!confirm('Supprimer ce contact ?')) return;
      try {
        await api('/api/fournisseurs/' + id + '/contacts/' + cid, {method: 'DELETE'});
        await refreshContacts();
      } catch (e) { toast(e.message, true); }
    });
  }

  async function refreshContacts() {
    try {
      contacts = await api('/api/fournisseurs/' + id + '/contacts');
      _fourContactsCache[id] = contacts;
      dlg.querySelector('#fi-contacts-list').closest('div').previousElementSibling
        ?.querySelector('strong')?.replaceChildren(document.createTextNode('Contacts (' + contacts.length + ')'));
      renderContactsList();
    } catch (e) { toast(e.message, true); }
  }
  renderContactsList();

  dlg.querySelector('#fi-add-contact').onclick = () => openContactSubModal(id, null, refreshContacts);

  dlg.querySelector('#fi-save').onclick = async () => {
    const body = {
      nom: dlg.querySelector('#fi-nom').value.trim(),
      langue_default: dlg.querySelector('#fi-langue').value,
      adresse: dlg.querySelector('#fi-adresse').value.trim(),
      code_postal: dlg.querySelector('#fi-cp').value.trim(),
      ville: dlg.querySelector('#fi-ville').value.trim(),
      pays: dlg.querySelector('#fi-pays').value.trim() || 'FR',
      tags: dlg.querySelector('#fi-tags').value,
      notes: dlg.querySelector('#fi-notes').value.trim(),
      actif: dlg.querySelector('#fi-actif').checked,
    };
    if (!body.nom) return toast('Nom requis', true);
    try {
      await api('/api/fournisseurs/' + id, {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
      toast('Fournisseur mis à jour');
      close();
      await loadFournisseurs();
      renderFournisseursContactsTable();
    } catch (e) { toast(e.message, true); }
  };
}

function openContactSubModal(fournisseurId, contactId, onSaved) {
  const contacts = _fourContactsCache[fournisseurId] || [];
  const c = contactId ? contacts.find(x => x.id === contactId) : null;
  const backdrop = document.createElement('div');
  backdrop.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:850;display:flex;align-items:center;justify-content:center;padding:16px';
  const dlg = document.createElement('div');
  dlg.style.cssText = 'background:var(--card);border:1px solid var(--border);border-radius:14px;padding:18px;max-width:460px;width:100%;max-height:90vh;overflow:auto';
  const langue = c ? (c.langue || 'fr') : 'fr';
  const isPrincipal = c ? !!c.is_principal : (contacts.length === 0);
  const actif = c ? (c.actif == null ? true : !!c.actif) : true;
  dlg.innerHTML = '<h3 style="margin:0 0 12px;font-size:15px">' + (c ? 'Modifier le contact' : 'Nouveau contact') + '</h3>' +
    '<label class="sub">Nom *</label><input id="fic-nom" value="' + escAttr(c ? c.nom : '') + '" style="margin-bottom:10px">' +
    '<label class="sub">Fonction</label><input id="fic-fonction" value="' + escAttr(c ? (c.fonction || '') : '') + '" placeholder="Commercial, Achats…" style="margin-bottom:10px">' +
    '<label class="sub">Emails <span style="color:var(--muted);font-weight:400">(séparés par virgules)</span></label>' +
    '<input id="fic-emails" value="' + escAttr(c ? (c.emails || []).join(', ') : '') + '" placeholder="contact@..., commercial@..." style="margin-bottom:10px">' +
    '<label class="sub">Téléphones <span style="color:var(--muted);font-weight:400">(séparés par virgules)</span></label>' +
    '<input id="fic-tels" value="' + escAttr(c ? (c.tels || []).join(', ') : '') + '" placeholder="+33 1 23 45 67 89" style="margin-bottom:10px">' +
    '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px">' +
    '<div><label class="sub">Langue</label><select id="fic-langue"><option value="fr"' + (langue==='fr'?' selected':'') + '>Français</option><option value="en"' + (langue==='en'?' selected':'') + '>English</option></select></div>' +
    '<div style="display:flex;flex-direction:column;justify-content:space-between">' +
    '<label style="display:flex;align-items:center;gap:8px;font-size:13px;cursor:pointer;user-select:none;margin-top:16px"><input type="checkbox" id="fic-principal" ' + (isPrincipal?'checked':'') + ' style="width:16px;height:16px;cursor:pointer">Contact principal</label>' +
    '<label style="display:flex;align-items:center;gap:8px;font-size:13px;cursor:pointer;user-select:none"><input type="checkbox" id="fic-actif" ' + (actif?'checked':'') + ' style="width:16px;height:16px;cursor:pointer">Actif</label>' +
    '</div></div>' +
    '<label class="sub">Notes</label><textarea id="fic-notes" style="width:100%;min-height:50px;padding:8px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-family:inherit;font-size:13px;box-sizing:border-box;margin-bottom:12px">' + esc(c ? (c.notes || '') : '') + '</textarea>' +
    '<div style="display:flex;gap:8px;justify-content:flex-end">' +
    '<button type="button" class="btn btn-sec" id="fic-cancel">Annuler</button>' +
    '<button type="button" class="btn" id="fic-save">' + (c ? 'Enregistrer' : 'Créer') + '</button>' +
    '</div>';
  backdrop.appendChild(dlg);
  document.body.appendChild(backdrop);
  const close = () => backdrop.remove();
  backdrop.addEventListener('click', e => { if (e.target === backdrop) close(); });
  dlg.querySelector('#fic-cancel').onclick = close;
  dlg.querySelector('#fic-save').onclick = async () => {
    const body = {
      nom: dlg.querySelector('#fic-nom').value.trim(),
      fonction: dlg.querySelector('#fic-fonction').value.trim(),
      emails: dlg.querySelector('#fic-emails').value,
      tels: dlg.querySelector('#fic-tels').value,
      langue: dlg.querySelector('#fic-langue').value,
      is_principal: dlg.querySelector('#fic-principal').checked,
      actif: dlg.querySelector('#fic-actif').checked,
      notes: dlg.querySelector('#fic-notes').value.trim(),
    };
    if (!body.nom) return toast('Nom requis', true);
    try {
      const path = '/api/fournisseurs/' + fournisseurId + '/contacts' + (contactId ? '/' + contactId : '');
      await api(path, {method: contactId ? 'PUT' : 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
      toast(contactId ? 'Contact mis à jour' : 'Contact ajouté');
      close();
      if (onSaved) await onSaved();
    } catch (e) { toast(e.message, true); }
  };
}

// Reset cache when the fournisseurs list reloads
const _origLoadFour = loadFournisseurs;
loadFournisseurs = async function() {
  _fourContactsCache = {};
  await _origLoadFour();
  if (typeof renderFournisseursContactsTable === 'function') {
    renderFournisseursContactsTable();
  }
};


(async function init() {
  try {
    const meta = await api('/api/settings/access-matrix');
    superadminEmailRef = String(meta.superadmin_email || '').trim().toLowerCase();
    assignableRoles = meta.roles || meta.assignable_roles || [];
    roleLabels = meta.role_labels || {};
    apps = meta.apps || [];
    fillRoleSelect();
    fillRoleFilterSelect();
    await refreshSidebarUser();
    if (window.MySifaDock && typeof window.MySifaDock.bootPageWidgets === 'function') {
      window.MySifaDock.bootPageWidgets();
    }
    initSupportSidebar();
    await loadFilters();
    await loadMachines();
    syncCuRoleUI();
    await loadUsers();
    await loadMatrix();
  } catch (e) {
    toast(e.message || 'Erreur chargement', true);
  }
})();

// ── Mises à jour ──────────────────────────────────────────────────────────────
const SCOPE_LABELS = { planning: '📋 Planning', fabrication: '⚙️ Saisie de prod.', global: '🌐 Global' };

let _updatesData = [];
let _openAckId = null;

async function loadUpdates() {
  const box = document.getElementById('upd-list');
  if (!box) return;
  try {
    _updatesData = await api('/api/updates') || [];
    renderUpdatesList();
  } catch(e) {
    box.innerHTML = '<p style="color:var(--danger);font-size:13px">' + esc(e.message) + '</p>';
  }
}

function toParisTime(isoStr) {
  if (!isoStr) return '—';
  try {
    // acknowledged_at est stocké en UTC (datetime.now() côté serveur)
    const d = new Date(isoStr.includes('T') ? isoStr + 'Z' : isoStr);
    return d.toLocaleString('fr-FR', {
      timeZone: 'Europe/Paris',
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit'
    });
  } catch(e) { return isoStr.slice(0, 16).replace('T', ' '); }
}

function renderUpdatesList() {
  const box = document.getElementById('upd-list');
  if (!_updatesData.length) {
    box.innerHTML = '<p style="color:var(--muted);font-size:13px">Aucune annonce pour le moment.</p>';
    return;
  }
  box.innerHTML = _updatesData.map(u => {
    const scopeLbl = SCOPE_LABELS[u.scope] || u.scope;
    const dt = u.created_at ? u.created_at.slice(0, 10).split('-').reverse().join('/') : '—';
    const activeTag = u.active
      ? '<span style="font-size:10px;padding:2px 7px;border-radius:999px;background:rgba(52,211,153,.15);color:#34d399;border:1px solid rgba(52,211,153,.3);font-weight:700">Actif</span>'
      : '<span style="font-size:10px;padding:2px 7px;border-radius:999px;background:rgba(148,163,184,.12);color:var(--muted);border:1px solid var(--border);font-weight:700">Archivé</span>';
    const ackCount = u.nb_ack || 0;
    const isOpen = _openAckId === u.id;
    return `
<div style="border:1px solid var(--border);border-radius:12px;overflow:hidden;margin-bottom:10px">
  <div style="display:flex;align-items:center;gap:12px;padding:14px 16px;cursor:pointer;background:var(--card)" onclick="toggleAck(${u.id})">
    <div style="flex:1;min-width:0">
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:4px">
        <span style="font-size:12px;color:var(--muted)">${esc(scopeLbl)}</span>
        <span style="font-size:11px;color:var(--muted)">·</span>
        <span style="font-size:12px;color:var(--muted)">${dt}</span>
        ${activeTag}
      </div>
      <div style="font-weight:700;font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(u.titre)}</div>
    </div>
    <div style="text-align:right;flex-shrink:0">
      <div style="font-size:18px;font-weight:800;color:var(--accent)">${ackCount}</div>
      <div style="font-size:10px;color:var(--muted)">lecture(s)</div>
    </div>
    <button type="button" class="btn btn-sec" style="padding:5px 10px;font-size:11px" onclick="event.stopPropagation();showUpdatePreview(${u.id})">Aperçu</button>
    ${ackCount === 0 ? `<button type="button" class="btn btn-sec" style="padding:5px 10px;font-size:11px" onclick="event.stopPropagation();openEditUpdateModal(${u.id})">Modifier</button><button type="button" class="btn btn-sec" style="padding:5px 10px;font-size:11px;color:var(--danger);border-color:var(--danger)" onclick="event.stopPropagation();deleteUpdate(${u.id})">Supprimer</button>` : ''}
    <button type="button" class="btn btn-sec" style="padding:5px 10px;font-size:11px" onclick="event.stopPropagation();toggleActive(${u.id},${u.active})">${u.active ? 'Archiver' : 'Réactiver'}</button>
    <span style="font-size:16px;color:var(--muted);transition:transform .2s;${isOpen ? 'transform:rotate(180deg)' : ''}">▾</span>
  </div>
  <div id="ack-panel-${u.id}" style="display:${isOpen ? 'block' : 'none'};border-top:1px solid var(--border);padding:14px 16px;background:rgba(0,0,0,.08)">
    <div id="ack-content-${u.id}"><em style="color:var(--muted);font-size:13px">Chargement…</em></div>
  </div>
</div>`;
  }).join('');
}

function showUpdatePreview(id) {
  const u = _updatesData.find(x => x.id === id);
  if (!u) return;
  const ov = document.createElement('div');
  ov.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:900;display:flex;align-items:center;justify-content:center';
  ov.innerHTML = `<div style="background:var(--card);border:1px solid var(--border2);border-radius:16px;padding:28px;width:min(560px,95vw);max-height:88vh;overflow-y:auto;box-shadow:0 24px 64px rgba(0,0,0,.6)">
    <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:16px">
      <div>
        <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);margin-bottom:4px">${esc(SCOPE_LABELS[u.scope]||u.scope)}</div>
        <h2 style="font-size:16px;margin:0">${esc(u.titre)}</h2>
      </div>
      <button onclick="this.closest('[style*=fixed]').remove()" style="border:none;background:none;color:var(--muted);font-size:22px;cursor:pointer;padding:0 0 0 12px;line-height:1;flex-shrink:0">×</button>
    </div>
    <div style="font-size:13px;line-height:1.7;color:var(--text2)">${u.message}</div>
    <button class="btn" style="width:100%;margin-top:20px;padding:12px;font-size:14px" onclick="this.closest('[style*=fixed]').remove()">Fermer</button>
  </div>`;
  ov.addEventListener('click', e => { if (e.target === ov) ov.remove(); });
  document.body.appendChild(ov);
}

async function toggleAck(id) {
  if (_openAckId === id) {
    _openAckId = null;
    renderUpdatesList();
    return;
  }
  _openAckId = id;
  renderUpdatesList();
  const contentEl = document.getElementById('ack-content-' + id);
  if (!contentEl) return;
  try {
    const data = await api('/api/updates/' + id + '/acknowledgements');
    const acks = data.acknowledgements || [];
    if (!acks.length) {
      contentEl.innerHTML = '<p style="color:var(--muted);font-size:13px;margin:0">Personne n\'a encore lu cette annonce.</p>';
      return;
    }
    contentEl.innerHTML = '<div style="font-size:12px;font-weight:700;color:var(--muted);margin-bottom:8px;text-transform:uppercase;letter-spacing:.5px">' + acks.length + ' lecture(s)</div>' +
      '<div style="display:flex;flex-wrap:wrap;gap:6px">' +
      acks.map(a => {
        const dt = toParisTime(a.acknowledged_at);
        return `<div style="padding:6px 10px;border-radius:8px;background:var(--bg);border:1px solid var(--border);font-size:12px">
          <strong>${esc(a.user_nom || a.email || '—')}</strong>
          ${a.email && a.user_nom ? '<span style="color:var(--muted);margin-left:4px">' + esc(a.email) + '</span>' : ''}
          <div style="font-size:10px;color:var(--muted);margin-top:2px">${esc(dt)}</div>
        </div>`;
      }).join('') + '</div>';
  } catch(e) {
    contentEl.innerHTML = '<p style="color:var(--danger);font-size:13px">' + esc(e.message) + '</p>';
  }
}

const APP_PAGES = {
  planning: [
    {value: '', label: 'Toutes les pages'},
    {value: 'planning', label: 'Planning'}
  ],
  fabrication: [
    {value: '', label: 'Toutes les pages'},
    {value: 'prod', label: 'Saisie Production'},
    {value: 'recap', label: 'Récapitulatif'},
    {value: 'tracabilite', label: 'Traçabilité'},
    {value: 'profil', label: 'Profil Opérateur'}
  ],
  stock: [
    {value: '', label: 'Toutes les pages'},
    {value: 'inventaire', label: 'Inventaire'},
    {value: 'alertes', label: 'Alertes de stock'},
    {value: 'reappro', label: 'Réapprovisionnement'},
    {value: 'mouvements', label: 'Mouvements'},
    {value: 'historique', label: 'Historique'},
    {value: 'parametres', label: 'Paramètres'}
  ],
  myexpe: [
    {value: '', label: 'Toutes les pages'},
    {value: 'suivi_departs', label: 'Suivi départs — départs du jour'},
    {value: 'historique_departs', label: 'Suivi départs — historique'},
    {value: 'comparateur', label: 'Comparateur tarifs'},
    {value: 'transporteurs', label: 'Transporteurs'},
    {value: 'poids', label: 'Poids envoi'}
  ],
  planning_rh: [
    {value: '', label: 'Toutes les pages'},
    {value: 'planning', label: 'Planning personnel'},
    {value: 'conges', label: 'Gestion des congés'},
    {value: 'soldes', label: 'Soldes congés'}
  ],
  paie: [
    {value: '', label: 'Toutes les pages'},
    {value: 'bulletins', label: 'Bulletins de paie'},
    {value: 'employes', label: 'Employés'},
    {value: 'parametres', label: 'Paramètres'}
  ],
  global: [
    {value: '', label: 'Toutes les pages'}
  ]
};

function populatePageSelect(appSelectId, pageSelectId, selectedPage) {
  const app = document.getElementById(appSelectId).value;
  const pageSelect = document.getElementById(pageSelectId);
  const pages = APP_PAGES[app] || [{value: '', label: 'Toutes les pages'}];
  pageSelect.innerHTML = pages.map(p => 
    `<option value="${p.value}"${p.value === (selectedPage || '') ? ' selected' : ''}>${p.label}</option>`
  ).join('');
}

function onAppChange() {
  populatePageSelect('nm-app', 'nm-page', '');
}

function onEditAppChange() {
  populatePageSelect('edit-nm-app', 'edit-nm-page', '');
}

function getScopeFromAppPage(appId, pageId) {
  const app = document.getElementById(appId).value;
  const page = document.getElementById(pageId).value;
  if (app === 'global') return 'global';
  if (!page) return app;
  return app + '_' + page;
}

function setAppPageFromScope(scope) {
  if (!scope || scope === 'global') {
    return { app: 'global', page: '' };
  }
  const parts = scope.split('_');
  const knownApps = Object.keys(APP_PAGES);
  // Check if first part is an app
  if (knownApps.includes(parts[0])) {
    const app = parts[0];
    const page = parts.slice(1).join('_');
    // Check if page exists for this app
    const pages = APP_PAGES[app] || [];
    const pageExists = pages.some(p => p.value === page);
    return { app: app, page: pageExists ? page : '' };
  }
  // Legacy scope (just app name)
  if (knownApps.includes(scope)) {
    return { app: scope, page: '' };
  }
  return { app: 'global', page: '' };
}

async function toggleActive(id, current) {
  try {
    await api('/api/updates/' + id, { method: 'PATCH', body: JSON.stringify({ active: !current }), headers: { 'Content-Type': 'application/json' } });
    toast(current ? 'Annonce archivée' : 'Annonce réactivée');
    await loadUpdates();
  } catch(e) { toast(e.message, true); }
}

function openNewUpdateModal() {
  const ov = document.getElementById('upd-modal-overlay');
  if (ov) { 
    ov.style.display = 'flex'; 
    ov.classList.remove('hidden'); 
  }
  // Initialize page select based on current app
  onAppChange();
}
function closeNewUpdateModal() {
  const ov = document.getElementById('upd-modal-overlay');
  if (ov) { ov.style.display = 'none'; ov.classList.add('hidden'); }
}
async function submitNewUpdate() {
  const scope   = getScopeFromAppPage('nm-app', 'nm-page');
  const titre   = (document.getElementById('nm-titre').value || '').trim();
  const message = (document.getElementById('nm-message').value || '').trim();
  const active  = Number(document.getElementById('nm-active').value);
  if (!titre || !message) { toast('Titre et message sont requis', true); return; }
  try {
    await api('/api/updates', { method: 'POST', body: JSON.stringify({ scope, titre, message, active }), headers: { 'Content-Type': 'application/json' } });
    toast('Annonce créée ✅');
    closeNewUpdateModal();
    document.getElementById('nm-titre').value = '';
    document.getElementById('nm-message').value = '';
    await loadUpdates();
  } catch(e) { toast(e.message, true); }
}

let _editingUpdateId = null;

function openEditUpdateModal(id) {
  const u = _updatesData.find(x => x.id === id);
  if (!u) return;
  _editingUpdateId = id;
  const { app, page } = setAppPageFromScope(u.scope);
  document.getElementById('edit-nm-app').value = app;
  populatePageSelect('edit-nm-app', 'edit-nm-page', page);
  document.getElementById('edit-nm-titre').value = u.titre || '';
  document.getElementById('edit-nm-message').value = u.message || '';
  document.getElementById('edit-nm-active').value = u.active ? '1' : '0';
  const ov = document.getElementById('edit-upd-modal-overlay');
  if (ov) { ov.style.display = 'flex'; ov.classList.remove('hidden'); }
}

function closeEditUpdateModal() {
  const ov = document.getElementById('edit-upd-modal-overlay');
  if (ov) { ov.style.display = 'none'; ov.classList.add('hidden'); }
  _editingUpdateId = null;
}

async function submitEditUpdate() {
  if (!_editingUpdateId) return;
  const scope   = getScopeFromAppPage('edit-nm-app', 'edit-nm-page');
  const titre   = (document.getElementById('edit-nm-titre').value || '').trim();
  const message = (document.getElementById('edit-nm-message').value || '').trim();
  const active  = Number(document.getElementById('edit-nm-active').value);
  if (!titre || !message) { toast('Titre et message sont requis', true); return; }
  try {
    await api('/api/updates/' + _editingUpdateId, { method: 'PATCH', body: JSON.stringify({ scope, titre, message, active }), headers: { 'Content-Type': 'application/json' } });
    toast('Annonce modifiée ✅');
    closeEditUpdateModal();
    await loadUpdates();
  } catch(e) { toast(e.message, true); }
}


let _opItems = [];
let _opCategories = [];
let _opEditCode = null;

async function loadOperationCodes() {
  const el = document.getElementById('op-list');
  if (!el) return;
  try {
    const d = await api('/api/settings/operation-codes');
    _opItems = (d && d.items) ? d.items : [];
    _opCategories = (d && d.categories) ? d.categories : [];
    const sel = document.getElementById('op-category');
    if (sel) {
      sel.innerHTML = _opCategories.map(c => `<option value="${c}">${c}</option>`).join('');
    }
    renderOpList();
  } catch (e) {
    el.innerHTML = `<p style="color:var(--danger)">${esc(e.message)}</p>`;
  }
}

function renderOpList() {
  const el = document.getElementById('op-list');
  if (!el) return;
  const q = (document.getElementById('op-filter')?.value || '').trim().toLowerCase();
  let items = [..._opItems];
  if (q) {
    items = items.filter(o =>
      String(o.code).includes(q) ||
      (o.label || '').toLowerCase().includes(q) ||
      (o.category || '').toLowerCase().includes(q) ||
      (o.severity || '').toLowerCase().includes(q)
    );
  }
  const byCat = {};
  items.forEach(o => {
    const c = o.category || 'autre';
    if (!byCat[c]) byCat[c] = [];
    byCat[c].push(o);
  });
  const cats = Object.keys(byCat).sort((a, b) => a.localeCompare(b, 'fr'));
  if (!cats.length) {
    el.innerHTML = '<p style="color:var(--muted);font-size:13px">Aucun code' + (q ? ' pour ce filtre' : '') + '.</p>';
    return;
  }
  let body = '';
  cats.forEach(cat => {
    body += '<tr class="op-cat-row"><td colspan="6">' + esc(cat) + '</td></tr>';
    byCat[cat].forEach(o => {
      const c = esc(o.code);
      const sev = esc(o.severity || 'info');
      const reqCls = o.required ? 'op-req yes' : 'op-req';
      body += '<tr>'
        + '<td class="op-code-cell">' + c + '</td>'
        + '<td class="op-lbl-cell">' + esc(o.label) + '</td>'
        + '<td><span class="op-pill ' + sev + '">' + sev + '</span></td>'
        + '<td><span class="op-pill ' + esc(cat) + '">' + esc(cat) + '</span></td>'
        + '<td><span class="' + reqCls + '">' + (o.required ? 'Oui' : '—') + '</span></td>'
        + '<td><div class="op-act">'
        + '<button type="button" class="btn-sm btn-ghost" data-op-edit="' + c + '">Modifier</button>'
        + '<button type="button" class="btn-sm btn-ghost danger" data-op-del="' + c + '">Supprimer</button>'
        + '</div></td></tr>';
    });
  });
  el.innerHTML = '<div class="table-wrap op-table-wrap"><table class="op-table"><thead><tr>'
    + '<th>Code</th><th>Libellé</th><th>Sévérité</th><th>Catégorie</th><th>Obligatoire</th><th>Actions</th>'
    + '</tr></thead><tbody>' + body + '</tbody></table></div>';
  el.querySelectorAll('[data-op-edit]').forEach(btn => {
    btn.addEventListener('click', () => openOpForm(btn.getAttribute('data-op-edit')));
  });
  el.querySelectorAll('[data-op-del]').forEach(btn => {
    btn.addEventListener('click', () => deleteOpCode(btn.getAttribute('data-op-del')));
  });
}

function openOpForm(code) {
  _opEditCode = code || null;
  const wrap = document.getElementById('op-form-wrap');
  const title = document.getElementById('op-form-title');
  const codeInp = document.getElementById('op-code');
  if (!wrap) return;
  wrap.classList.remove('hidden');
  if (code) {
    const o = _opItems.find(x => String(x.code) === String(code));
    if (!o) return;
    title.textContent = 'Modifier le code ' + code;
    codeInp.value = o.code;
    codeInp.disabled = true;
    document.getElementById('op-label').value = o.label || '';
    document.getElementById('op-severity').value = o.severity || 'info';
    document.getElementById('op-category').value = o.category || 'autre';
    document.getElementById('op-required').checked = !!o.required;
  } else {
    title.textContent = 'Nouveau code';
    codeInp.value = '';
    codeInp.disabled = false;
    document.getElementById('op-label').value = '';
    document.getElementById('op-severity').value = 'info';
    document.getElementById('op-category').value = _opCategories[0] || 'autre';
    document.getElementById('op-required').checked = false;
  }
}

function closeOpForm() {
  _opEditCode = null;
  const wrap = document.getElementById('op-form-wrap');
  if (wrap) wrap.classList.add('hidden');
}

async function saveOpForm() {
  const body = {
    code: document.getElementById('op-code').value.trim(),
    label: document.getElementById('op-label').value.trim(),
    severity: document.getElementById('op-severity').value,
    category: document.getElementById('op-category').value,
    required: document.getElementById('op-required').checked,
  };
  try {
    if (_opEditCode) {
      await api('/api/settings/operation-codes/' + encodeURIComponent(_opEditCode), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      toast('Code mis à jour');
    } else {
      await api('/api/settings/operation-codes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      toast('Code ajouté');
    }
    closeOpForm();
    await loadOperationCodes();
  } catch (e) { toast(e.message, true); }
}

async function deleteOpCode(code) {
  if (!confirm('Supprimer le code ' + code + ' ?')) return;
  try {
    await api('/api/settings/operation-codes/' + encodeURIComponent(code), { method: 'DELETE' });
    toast('Code supprimé');
    await loadOperationCodes();
  } catch (e) { toast(e.message, true); }
}

async function importOpsJson() {
  if (!confirm('Importer / mettre à jour tous les codes depuis operations.json sur le serveur ?')) return;
  try {
    const r = await api('/api/settings/operation-codes/import-json', { method: 'POST' });
    toast('Sync. OK (' + (r.upserted || 0) + ' codes)');
    await loadOperationCodes();
  } catch (e) { toast(e.message, true); }
}

// ── Codes maintenance (stockage SQLite cote serveur) ─────────────────
// Cle localStorage conservee pour migration one-shot des codes existants
// (anciennement stockes cote navigateur, perdus entre v1/v2 et entre appareils).
const MAINT_CODES_STORAGE_KEY = 'mysifa_settings_maint_codes_v1';
let _maintItems = [];
let _maintEditCode = null;
async function loadMaintCodes() {
  try {
    const r = await api('/api/maintenance/codes');
    _maintItems = (r && Array.isArray(r.items)) ? r.items : [];
  } catch (e) {
    toast('Erreur de chargement des codes maintenance : ' + (e && e.message ? e.message : e), true);
    _maintItems = [];
  }
  // Migration one-shot : si la liste serveur est vide ET qu'on a des codes en
  // localStorage (heritage de l'ancienne implementation), on propose l'import.
  if (_maintItems.length === 0) {
    try {
      const raw = localStorage.getItem(MAINT_CODES_STORAGE_KEY);
      const local = raw ? JSON.parse(raw) : [];
      if (Array.isArray(local) && local.length > 0) {
        if (confirm(local.length + ' code(s) maintenance trouve(s) dans le stockage local du navigateur.\n\nLes importer dans la base de donnees ? (recommande, ils seront ensuite disponibles sur tous les navigateurs et synchronises v2 -> v1)')) {
          try {
            const res = await api('/api/maintenance/codes/bulk-import', {
              method: 'POST',
              body: JSON.stringify({ items: local }),
            });
            toast((res?.imported || 0) + ' code(s) importe(s)');
            try { localStorage.removeItem(MAINT_CODES_STORAGE_KEY); } catch (e) {}
            const r2 = await api('/api/maintenance/codes');
            _maintItems = (r2 && Array.isArray(r2.items)) ? r2.items : [];
          } catch (e) {
            toast('Echec de l\'import : ' + (e && e.message ? e.message : e), true);
          }
        }
      }
    } catch (e) {}
  }
  renderMaintList();
}
// ─── Interventions libres (Lot 2) ────────────────────────────────
// Curation admin des codes libre=1 : lister, renommer, archiver, fusionner.
let _libresItems = [];
let _libresSelection = new Set();

async function loadLibres() {
  const listEl = document.getElementById('libres-list');
  if (!listEl) return;
  try {
    const r = await api('/api/maintenance/codes/libres');
    _libresItems = (r && Array.isArray(r.items)) ? r.items : [];
  } catch (e) {
    _libresItems = [];
  }
  _libresSelection.clear();
  _updateLibresSelectionUI();
  renderLibresList();
}

function _fmtLibreDate(iso) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return '—';
    const pad = n => (n < 10 ? '0' + n : '' + n);
    return pad(d.getDate()) + '/' + pad(d.getMonth() + 1) + '/' + d.getFullYear();
  } catch (e) { return '—'; }
}

function _updateLibresSelectionUI() {
  const btn = document.getElementById('libres-merge-btn');
  const cnt = document.getElementById('libres-selection-count');
  const n = _libresSelection.size;
  if (btn) btn.disabled = (n !== 2);
  if (cnt) {
    if (n === 0) cnt.textContent = '';
    else if (n === 1) cnt.textContent = '1 titre selectionne - coche un 2e pour fusionner';
    else if (n === 2) cnt.textContent = '2 titres selectionnes - pret a fusionner';
    else cnt.textContent = n + ' selectionnes (max 2)';
  }
}

function libresToggleSelection(code, checked) {
  if (checked) {
    _libresSelection.add(code);
    if (_libresSelection.size > 2) {
      const arr = Array.from(_libresSelection);
      _libresSelection = new Set(arr.slice(-2));
      renderLibresList();
    }
  } else {
    _libresSelection.delete(code);
  }
  _updateLibresSelectionUI();
}

function renderLibresList() {
  const el = document.getElementById('libres-list');
  if (!el) return;
  const q = (document.getElementById('libres-filter') && document.getElementById('libres-filter').value || '').trim().toLowerCase();
  let items = _libresItems.slice();
  if (q) {
    items = items.filter(o =>
      String(o.label || '').toLowerCase().includes(q) ||
      String(o.code || '').toLowerCase().includes(q)
    );
  }
  if (!items.length) {
    el.innerHTML = '<p style="color:var(--muted);font-size:13px">' +
      (q ? 'Aucun titre pour ce filtre.' : 'Aucune intervention libre saisie pour l\u2019instant.') + '</p>';
    return;
  }
  const rows = items.map(o => {
    const codeEsc = esc(String(o.code));
    const labelEsc = esc(String(o.label || ''));
    const checked = _libresSelection.has(o.code) ? ' checked' : '';
    const usage = o.usage_count;
    const usageChip = usage > 0
      ? '<span style="display:inline-flex;align-items:center;padding:2px 8px;border-radius:12px;background:var(--accent-bg);color:var(--accent);font-size:11px;font-weight:700">' + usage + ' saisie' + (usage > 1 ? 's' : '') + '</span>'
      : '<span style="color:var(--muted);font-size:11px;font-style:italic">Jamais utilise</span>';
    // v2.2.41 : bouton Archiver retiré — un libre est créé au moment de sa 1ère
    // utilisation, donc usage_count >= 1 dès la naissance, le bouton était mort.
    // Nettoyage désormais uniquement via Fusion.
    const delBtn = '';
    return '<tr>' +
      '<td style="width:34px;padding:4px 8px"><input type="checkbox" data-libre-sel="' + codeEsc + '"' + checked + '></td>' +
      '<td style="font-family:monospace;font-size:11px;color:var(--muted)">' + codeEsc + '</td>' +
      '<td><span style="color:var(--text);font-weight:500">' + labelEsc + '</span></td>' +
      '<td>' + usageChip + '</td>' +
      '<td style="font-size:12px;color:var(--text2);white-space:nowrap">' + _fmtLibreDate(o.last_used_at) + '</td>' +
      '<td style="font-size:12px;color:var(--muted);white-space:nowrap">' + _fmtLibreDate(o.created_at) + '</td>' +
      '<td style="text-align:right;white-space:nowrap">' +
        '<button type="button" class="btn-sm btn-ghost" data-libre-rename="' + codeEsc + '">Renommer</button> ' +
        delBtn +
      '</td>' +
    '</tr>';
  }).join('');
  el.innerHTML = '<div class="table-wrap op-table-wrap"><table class="op-table">' +
    '<thead><tr>' +
      '<th></th>' +
      '<th>Code</th>' +
      '<th>Titre</th>' +
      '<th>Usage</th>' +
      '<th>Derniere utilisation</th>' +
      '<th>Cree le</th>' +
      '<th style="text-align:right">Actions</th>' +
    '</tr></thead>' +
    '<tbody>' + rows + '</tbody></table></div>';
  // Bind event delegation (checkbox + rename + delete)
  el.querySelectorAll('[data-libre-sel]').forEach(cb => {
    cb.addEventListener('change', () => {
      libresToggleSelection(cb.getAttribute('data-libre-sel'), cb.checked);
    });
  });
  el.querySelectorAll('[data-libre-rename]').forEach(btn => {
    btn.addEventListener('click', () => {
      const code = btn.getAttribute('data-libre-rename');
      const it = _libresItems.find(x => x.code === code);
      if (it) libresRename(code, it.label);
    });
  });
  el.querySelectorAll('[data-libre-del]').forEach(btn => {
    btn.addEventListener('click', () => {
      const code = btn.getAttribute('data-libre-del');
      const it = _libresItems.find(x => x.code === code);
      if (it) libresDelete(code, it.label);
    });
  });
}

async function libresRename(code, currentLabel) {
  const newLabel = prompt('Nouveau titre pour l\u2019intervention libre :', currentLabel || '');
  if (newLabel === null) return;
  const trimmed = (newLabel || '').trim();
  if (!trimmed) { toast('Titre obligatoire', true); return; }
  if (trimmed === currentLabel) return;
  try {
    await api('/api/maintenance/codes/libres/' + encodeURIComponent(code), {
      method: 'PATCH',
      body: JSON.stringify({ label: trimmed }),
    });
    toast('Titre modifie');
    await loadLibres();
  } catch (e) {
    toast(e && e.message ? e.message : 'Erreur', true);
  }
}

async function libresDelete(code, label) {
  if (!confirm('Archiver definitivement "' + label + '" (' + code + ') ?\n\nCette action est reversible uniquement via SQL manuel.')) return;
  try {
    await api('/api/maintenance/codes/libres/' + encodeURIComponent(code), { method: 'DELETE' });
    toast('Titre archive');
    _libresSelection.delete(code);
    await loadLibres();
  } catch (e) {
    toast(e && e.message ? e.message : 'Erreur', true);
  }
}

async function libresMergeSelected() {
  if (_libresSelection.size !== 2) return;
  const codes = Array.from(_libresSelection);
  const items = codes.map(c => _libresItems.find(x => x.code === c)).filter(Boolean);
  if (items.length !== 2) { toast('Selection invalide', true); return; }
  const opts = items.map((it, i) => (i + 1) + '. ' + it.label + ' (' + it.usage_count + ' saisie' + (it.usage_count > 1 ? 's' : '') + ')').join('\n');
  const choice = prompt(
    'Quel titre garder pour la fusion ?\n\n' + opts + '\n\nSaisis 1 ou 2 :',
    items[0].usage_count >= items[1].usage_count ? '1' : '2'
  );
  if (choice === null) return;
  const idx = parseInt(choice, 10) - 1;
  if (idx !== 0 && idx !== 1) { toast('Choix invalide (1 ou 2 attendu)', true); return; }
  const winner = items[idx];
  const loser = items[1 - idx];
  if (!confirm(
    'Fusionner "' + loser.label + '" (' + loser.usage_count + ' saisie' + (loser.usage_count > 1 ? 's' : '') + ') vers "' + winner.label + '" ?\n\n' +
    'Toutes les saisies passees de "' + loser.label + '" seront desormais attribuees a "' + winner.label + '".\n' +
    'Le titre "' + loser.label + '" (' + loser.code + ') sera supprime.'
  )) return;
  try {
    await api('/api/maintenance/codes/libres/merge', {
      method: 'POST',
      body: JSON.stringify({ winner_code: winner.code, loser_code: loser.code }),
    });
    toast('Fusion effectuee');
    _libresSelection.clear();
    await loadLibres();
  } catch (e) {
    toast(e && e.message ? e.message : 'Erreur', true);
  }
}

function _maintCatLabel(cat) {
  // Depuis v178 : "interventions" est scindée en "entretien" (UI: Nettoyage)
  // et "remplacements" (UI: Interventions). Labels renommés v179.
  // 'interventions' et 'suivi' (legacy) sont remappés vers Nettoyage à l'affichage.
  if (cat === 'remplacements') return 'Interventions';
  if (cat === 'entretien' || cat === 'interventions' || cat === 'suivi') return 'Nettoyage';
  return 'Contrôles';
}
let _lastAckByCode = {};
function renderMaintList() {
  const el = document.getElementById('maint-list');
  if (!el) return;
  // Reconstruire la map code -> dernière intervention depuis les alertes auto.
  _lastAckByCode = {};
  if (Array.isArray(_alertsData)) {
    _alertsData.forEach(a => {
      if (a && a.linked_maint_code) {
        _lastAckByCode[String(a.linked_maint_code)] = a.last_ack_at || '';
      }
    });
  }
  const q = (document.getElementById('maint-filter')?.value || '').trim().toLowerCase();
  let items = _maintItems.slice();
  // Normaliser la catégorie sur les anciens enregistrements
  items.forEach(o => { if (!o.categorie) o.categorie = 'controles'; });
  if (q) {
    items = items.filter(o => {
      const periodLbl = (o.periodique ? 'oui' : 'non');
      return String(o.code || '').toLowerCase().includes(q) ||
        String(o.label || '').toLowerCase().includes(q) ||
        ('n' + (o.niveau || '')).toLowerCase().includes(q) ||
        _maintCatLabel(o.categorie).toLowerCase().includes(q) ||
        // v2.2.17 — periodique retiré du filtre
        String(o.intervalle || '').toLowerCase().includes(q) ||
        String(o.metrage_ref || '').toLowerCase().includes(q);
    });
  }
  // Ordre des catégories : Contrôles → Entretien → Remplacements. Les codes
  // legacy ('interventions', 'suivi') sont remappés vers 'entretien' à l'affichage.
  const _normCat = (c) => {
    if (c === 'remplacements') return 'remplacements';
    if (c === 'entretien' || c === 'interventions' || c === 'suivi') return 'entretien';
    return 'controles';
  };
  const _catOrder = (c) => {
    const n = _normCat(c);
    return n === 'controles' ? 0 : (n === 'entretien' ? 1 : 2);
  };
  items.sort((a, b) => {
    const da = _catOrder(a.categorie);
    const db = _catOrder(b.categorie);
    if (da !== db) return da - db;
    const ac = String(a.code || '').padStart(6, '0');
    const bc = String(b.code || '').padStart(6, '0');
    return ac.localeCompare(bc, 'fr');
  });
  if (!items.length) {
    el.innerHTML = '<p style="color:var(--muted);font-size:13px">Aucun code' + (q ? ' pour ce filtre' : '') + '.</p>';
    return;
  }
  const byCat = { controles: [], entretien: [], remplacements: [] };
  items.forEach(o => { byCat[_normCat(o.categorie)].push(o); });
  let body = '';
  ['controles', 'entretien', 'remplacements'].forEach(cat => {
    if (!byCat[cat].length) return;
    body += '<tr class="op-cat-row"><td colspan="8">' + esc(_maintCatLabel(cat)) + '</td></tr>';
    byCat[cat].forEach(o => {
      const c = esc(String(o.code));
      const niv = parseInt(o.niveau, 10) || 1;
      const catCls = cat;
      // v2.2.17 — Périodicité retirée : tous les codes sont périodiques.
      const intervalleDisplay = o.intervalle ? esc(o.intervalle) : '<span style="color:var(--muted);font-style:italic">À compléter</span>';
      const metrageDisplay = o.metrage_ref ? esc(o.metrage_ref) : '<span style="color:var(--muted);font-style:italic">À compléter</span>';
      body += '<tr>'
        + '<td class="op-code-cell">' + c + '</td>'
        + '<td class="op-lbl-cell">' + esc(o.label || '') + '</td>'
        + '<td><span class="niv-badge" data-niv="' + niv + '">N' + niv + '</span></td>'
        + '<td><span class="op-pill ' + catCls + '">' + esc(_maintCatLabel(cat)) + '</span></td>'
        + '<td>' + intervalleDisplay + '</td>'
        + '<td>' + metrageDisplay + '</td>'
        + '<td><button type="button" class="btn-sm btn-ghost maint-docs-btn" data-maint-docs="' + c + '" title="Gerer les documents attaches a ce code">'
        +   '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>'
        +   ' <span class="maint-docs-count" data-count="' + (o.docs_count || 0) + '">' + (o.docs_count || 0) + '</span>'
        + '</button></td>'
        + '<td><div class="op-act">'
        + '<button type="button" class="btn-sm btn-ghost" data-maint-edit="' + c + '">Modifier</button>'
        + '<button type="button" class="btn-sm btn-ghost danger" data-maint-del="' + c + '">Supprimer</button>'
        + '</div></td></tr>';
    });
  });
  el.innerHTML = '<div class="table-wrap op-table-wrap"><table class="op-table"><thead><tr>'
    + '<th>Code</th><th>Libellé</th><th>Niveau</th><th>Catégorie</th><th>Intervalle de temps</th><th>Réf. métrage</th><th>Documents</th><th>Actions</th>'
    + '</tr></thead><tbody>' + body + '</tbody></table></div>';
  el.querySelectorAll('[data-maint-edit]').forEach(btn => {
    btn.addEventListener('click', () => openMaintForm(btn.getAttribute('data-maint-edit')));
  });
  el.querySelectorAll('[data-maint-del]').forEach(btn => {
    btn.addEventListener('click', () => deleteMaintCode(btn.getAttribute('data-maint-del')));
  });
  el.querySelectorAll('[data-maint-docs]').forEach(btn => {
    btn.addEventListener('click', () => openMaintDocsModal(btn.getAttribute('data-maint-docs')));
  });
}

// ── Documents attaches aux codes maintenance ─────────────────────────────
async function openMaintDocsModal(code) {
  const item = _maintItems.find(x => String(x.code) === String(code));
  const label = item ? item.label : '';
  const overlay = document.createElement('div');
  overlay.className = 'alert-modal-overlay';
  overlay.innerHTML = '<div class="alert-modal" style="max-width:560px">'
    + '<div class="alert-modal-head"><h3>Documents · ' + esc(code) + (label ? ' – ' + esc(label) : '') + '</h3><button type="button" class="btn-sm btn-ghost" data-close>×</button></div>'
    + '<div class="alert-modal-body">'
    +   '<div id="maint-docs-list" style="display:flex;flex-direction:column;gap:6px;margin-bottom:12px"><p style="color:var(--muted);font-size:12px">Chargement…</p></div>'
    +   '<input type="file" id="maint-doc-file" style="position:absolute;left:-9999px;top:auto;width:1px;height:1px;overflow:hidden">'
    +   '<button type="button" class="maint-doc-add-btn" id="maint-doc-add-btn">'
    +     '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>'
    +     '<span>Ajouter un fichier</span>'
    +   '</button>'
    +   '<div style="font-size:11px;color:var(--muted);margin-top:8px">20 Mo max par fichier.</div>'
    + '</div>'
    + '<div class="alert-modal-foot">'
    +   '<button type="button" class="btn btn-sec" data-close>Fermer</button>'
    + '</div></div>';
  document.body.appendChild(overlay);
  const close = () => overlay.remove();
  overlay.querySelectorAll('[data-close]').forEach(el => el.addEventListener('click', close));
  overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });

  const listEl = overlay.querySelector('#maint-docs-list');
  const renderDocs = (items) => {
    if (!items.length) {
      listEl.innerHTML = '<p style="color:var(--muted);font-size:12px;font-style:italic">Aucun document pour l\'instant.</p>';
      return;
    }
    listEl.innerHTML = items.map(d => {
      const sz = d.size_bytes != null ? (Math.round(d.size_bytes / 1024) + ' Ko') : '';
      const dt = d.uploaded_at ? esc(d.uploaded_at.slice(0, 16).replace('T', ' ')) : '';
      return '<div class="maint-doc-row" style="display:flex;align-items:center;gap:8px;padding:8px 10px;border:1px solid var(--border);border-radius:8px;background:var(--card)">'
        +   '<div style="flex:1;min-width:0"><div style="font-size:13px;font-weight:600;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis" title="' + esc(d.filename) + '">' + esc(d.filename) + '</div>'
        +   '<div style="font-size:10px;color:var(--muted)">' + sz + (dt ? ' · ' + dt : '') + (d.uploaded_by ? ' · ' + esc(d.uploaded_by) : '') + '</div></div>'
        +   '<a class="btn-sm btn-ghost" href="/api/maintenance/docs/' + d.id + '/download" target="_blank" rel="noopener" style="text-decoration:none">Telecharger</a>'
        +   '<button type="button" class="btn-sm btn-ghost danger" data-doc-del="' + d.id + '">Supprimer</button>'
        + '</div>';
    }).join('');
    listEl.querySelectorAll('[data-doc-del]').forEach(b => {
      b.addEventListener('click', async () => {
        if (!confirm('Supprimer ce document ?')) return;
        try {
          await api('/api/maintenance/docs/' + b.getAttribute('data-doc-del'), { method: 'DELETE' });
          toast('Document supprime');
          await refresh();
          if (typeof loadMaintCodes === 'function') await loadMaintCodes();
        } catch(e) { toast(e && e.message ? e.message : 'Erreur', true); }
      });
    });
  };
  const refresh = async () => {
    try {
      const r = await api('/api/maintenance/codes/' + encodeURIComponent(code) + '/docs');
      renderDocs(Array.isArray(r.items) ? r.items : []);
    } catch(e) {
      listEl.innerHTML = '<p style="color:var(--danger);font-size:12px">' + esc(e.message || 'Erreur') + '</p>';
    }
  };
  await refresh();

  const fileInp = overlay.querySelector('#maint-doc-file');
  const addBtn = overlay.querySelector('#maint-doc-add-btn');
  addBtn.addEventListener('click', () => fileInp.click());
  fileInp.addEventListener('change', async () => {
    const f = fileInp.files && fileInp.files[0];
    if (!f) return;
    if (f.size > 20 * 1024 * 1024) { toast('Fichier trop volumineux (max 20 Mo)', true); fileInp.value=''; return; }
    addBtn.disabled = true;
    const fd = new FormData();
    fd.append('file', f);
    try {
      const res = await fetch('/api/maintenance/codes/' + encodeURIComponent(code) + '/docs', {
        method: 'POST', credentials: 'same-origin', body: fd
      });
      if (!res.ok) {
        let msg = 'Upload echoue';
        try { const j = await res.json(); msg = j.detail || msg; } catch(e){}
        toast(msg, true); return;
      }
      toast('Document ajoute');
      fileInp.value = '';
      await refresh();
      if (typeof loadMaintCodes === 'function') await loadMaintCodes();
    } catch(e) { toast('Erreur reseau', true); } finally { addBtn.disabled = false; }
  });
}
function openMaintForm(code) {
  _maintEditCode = code || null;
  const wrap = document.getElementById('maint-form-wrap');
  const title = document.getElementById('maint-form-title');
  const codeInp = document.getElementById('maint-code');
  if (!wrap) return;
  wrap.classList.remove('hidden');
  const catSel = document.getElementById('maint-categorie');
  // v2.2.17 — perSel retiré (périodicité cachée).
  const intInp = document.getElementById('maint-intervalle');
  const mInp   = document.getElementById('maint-metrage-ref');
  if (code) {
    const o = _maintItems.find(x => String(x.code) === String(code));
    if (!o) return;
    title.textContent = 'Modifier le code ' + code;
    codeInp.value = o.code;
    codeInp.disabled = true;
    document.getElementById('maint-label').value = o.label || '';
    document.getElementById('maint-niveau').value = String(o.niveau || 1);
    if (catSel) {
      // Depuis v178 : 3 catégories ('controles', 'entretien', 'remplacements').
      // Codes legacy ('interventions', 'suivi') sont remappés vers 'entretien' à l'édition.
      let c;
      if (o.categorie === 'remplacements') c = 'remplacements';
      else if (o.categorie === 'entretien' || o.categorie === 'interventions' || o.categorie === 'suivi') c = 'entretien';
      else c = 'controles';
      catSel.value = c;
    }
    if (intInp) intInp.value = o.intervalle || '';
    if (mInp)   mInp.value   = o.metrage_ref || '';
  } else {
    title.textContent = 'Nouveau code';
    codeInp.value = '';
    codeInp.disabled = false;
    document.getElementById('maint-label').value = '';
    document.getElementById('maint-niveau').value = '1';
    if (catSel) catSel.value = 'controles';
    if (intInp) intInp.value = '';
    if (mInp)   mInp.value   = '';
  }
  // Section Documents : visible dans les 2 modes.
  // En creation : la liste est masquee (aucun doc encore), l'upload est
  // possible des que le code est saisi. En edition : la liste est chargee
  // et l'upload attache directement au code existant.
  const docsWrap = document.getElementById('maint-form-docs');
  const docsList = document.getElementById('maint-form-docs-list');
  const docsHint = document.getElementById('maint-form-docs-hint');
  if (docsWrap) {
    docsWrap.style.display = '';
    _maintResetDocPicker();
    _bindMaintFormDocUpload(code);
    if (code) {
      if (docsHint) docsHint.textContent = 'Fichiers explicatifs consultes par les operateurs quand ils executent l\'operation.';
      if (docsList) docsList.style.display = '';
      _renderMaintFormDocs(code);
    } else {
      if (docsHint) docsHint.textContent = 'Saisis le code puis attache un document. L\'envoi cree le code s\'il n\'existe pas encore.';
      if (docsList) docsList.style.display = 'none';
    }
  }
  // v2.2.34 : le scroller varie selon la page (window en Paramètres, .main en MyMaintenance).
  // On tente les 2 : celui qui n'est pas le vrai scroller no-op silencieusement.
  try {
    window.scrollTo({ top: 0, behavior: 'smooth' });
    const m = document.querySelector('.main');
    if (m) { if (m.scrollTo) m.scrollTo({ top: 0, behavior: 'smooth' }); else m.scrollTop = 0; }
  } catch(e) {
    try { window.scrollTo(0, 0); } catch(e2) {}
    try { document.querySelector('.main').scrollTop = 0; } catch(e3) {}
  }
  codeInp.focus();
}

async function _renderMaintFormDocs(code) {
  const list = document.getElementById('maint-form-docs-list');
  if (!list) return;
  list.innerHTML = '<p style="color:var(--muted);font-size:12px;font-style:italic">Chargement…</p>';
  try {
    const r = await api('/api/maintenance/codes/' + encodeURIComponent(code) + '/docs');
    const items = Array.isArray(r.items) ? r.items : [];
    if (!items.length) {
      list.innerHTML = '<p style="color:var(--muted);font-size:12px;font-style:italic">Aucun document attache pour l\'instant.</p>';
      return;
    }
    list.innerHTML = items.map(d => {
      const sz = d.size_bytes != null ? (Math.round(d.size_bytes/1024) + ' Ko') : '';
      const dt = d.uploaded_at ? esc(d.uploaded_at.slice(0,16).replace('T',' ')) : '';
      const meta = [sz, dt, d.uploaded_by ? esc(d.uploaded_by) : ''].filter(Boolean).join(' · ');
      return '<div class="maint-doc-row">'
        + '<div class="maint-doc-row-info">'
        +   '<span class="maint-doc-row-name" title="' + esc(d.filename) + '">' + esc(d.filename) + '</span>'
        +   '<span class="maint-doc-row-meta">' + meta + '</span>'
        + '</div>'
        + '<a class="maint-doc-row-link" href="/api/maintenance/docs/' + d.id + '/download" target="_blank" rel="noopener">Telecharger</a>'
        + '<button type="button" class="maint-doc-row-del" data-form-doc-del="' + d.id + '">Supprimer</button>'
        + '</div>';
    }).join('');
    list.querySelectorAll('[data-form-doc-del]').forEach(b => {
      b.addEventListener('click', async () => {
        if (!confirm('Supprimer ce document ?')) return;
        try {
          await api('/api/maintenance/docs/' + b.getAttribute('data-form-doc-del'), { method: 'DELETE' });
          toast('Document supprime');
          await _renderMaintFormDocs(code);
          if (typeof loadMaintCodes === 'function') await loadMaintCodes();
        } catch(e) { toast(e && e.message ? e.message : 'Erreur', true); }
      });
    });
  } catch(e) {
    list.innerHTML = '<p style="color:var(--danger);font-size:12px">Impossible de charger les documents.</p>';
  }
}

// Clic sur le bouton "+ Ajouter un fichier" -> ouvre le picker natif cache.
async function _maintTriggerDocPicker() {
  const codeInp = document.getElementById('maint-code');
  const codeNow = codeInp ? (codeInp.value || '').trim() : '';
  if (!codeNow) { toast('Renseigne d\'abord le code', true); return; }
  // En creation : sauvegarde le code en base avant l'upload, pour eviter
  // a l'utilisateur de devoir fermer le form et rouvrir en Modifier.
  const codeExists = Array.isArray(_maintItems) && _maintItems.some(x => String(x.code) === String(codeNow));
  if (!codeExists) {
    const labelInp = document.getElementById('maint-label');
    const labelNow = labelInp ? (labelInp.value || '').trim() : '';
    if (!labelNow) { toast('Renseigne le libelle avant d\'attacher un fichier', true); return; }
    const niveau = parseInt(document.getElementById('maint-niveau').value, 10) || 1;
    const rawCat = (document.getElementById('maint-categorie')?.value || '').trim();
    const categorie = (rawCat === 'entretien' || rawCat === 'remplacements' || rawCat === 'controles')
      ? rawCat
      : (rawCat === 'interventions' ? 'entretien' : 'controles');
    // v2.2.17 — periodique forcé à true (concept retiré côté UI).
    const periodique = true;
    const intervalle  = (document.getElementById('maint-intervalle')?.value  || '').trim();
    const metrage_ref = (document.getElementById('maint-metrage-ref')?.value || '').trim();
    const payload = { code: codeNow, label: labelNow, niveau, categorie, periodique, intervalle, metrage_ref };
    try {
      await api('/api/maintenance/codes', { method: 'POST', body: JSON.stringify(payload) });
      toast('Code enregistre - upload en cours');
      _maintEditCode = codeNow;
      codeInp.disabled = true;
      await loadMaintCodes();
      const listEl = document.getElementById('maint-form-docs-list');
      if (listEl) { listEl.style.display = ''; listEl.innerHTML = '<p style="color:var(--muted);font-size:12px;font-style:italic">Aucun document attache pour l\'instant.</p>'; }
    } catch(e) {
      toast(e && e.message ? e.message : 'Impossible d\'enregistrer le code', true);
      return;
    }
  }
  const inp = document.getElementById('maint-form-doc-file');
  if (inp) inp.click();
}

// Compat : appele par openMaintForm, mais l'upload est declenche directement
// par onchange du <input type=file>. No-op.
function _bindMaintFormDocUpload(code) { /* upload direct via _maintOnDocFileChange */ }

// Picker onchange -> upload immediat (pas de bouton Envoyer intermediaire).
async function _maintOnDocFileChange() {
  const inp = document.getElementById('maint-form-doc-file');
  const f = inp && inp.files && inp.files[0];
  if (!f) return;
  if (f.size > 20 * 1024 * 1024) {
    toast('Fichier trop volumineux (max 20 Mo)', true);
    inp.value = '';
    return;
  }
  const codeInp = document.getElementById('maint-code');
  const codeNow = codeInp ? (codeInp.value || '').trim() : '';
  if (!codeNow) {
    toast('Renseigne d\'abord le code', true);
    inp.value = '';
    return;
  }
  const btn = document.getElementById('maint-form-doc-add-btn');
  if (btn) btn.disabled = true;
  const fd = new FormData();
  fd.append('file', f);
  try {
    const res = await fetch('/api/maintenance/codes/' + encodeURIComponent(codeNow) + '/docs', {
      method: 'POST', credentials: 'same-origin', body: fd
    });
    if (!res.ok) {
      let msg = 'Upload echoue';
      try { const j = await res.json(); msg = j.detail || msg; } catch(e){}
      toast(msg, true); return;
    }
    toast('Document ajoute');
    inp.value = '';
    const listEl = document.getElementById('maint-form-docs-list');
    if (listEl) listEl.style.display = '';
    await _renderMaintFormDocs(codeNow);
    if (typeof loadMaintCodes === 'function') await loadMaintCodes();
  } catch(e) {
    toast('Erreur reseau', true);
  } finally {
    if (btn) btn.disabled = false;
  }
}

function _maintResetDocPicker() {
  const inp = document.getElementById('maint-form-doc-file');
  if (inp) inp.value = '';
}
// Active/désactive Intervalle et Réf. métrage selon Périodique :
//   - Périodique = OUI : les deux champs sont actifs (l'utilisateur peut
//     remplir l'intervalle de temps et/ou la référence métrage).
//   - Périodique = NON : les deux champs sont vidés et grisés.
function _maintTogglePeriodiqueUI(){
  // v2.2.17 — perSel retiré (périodicité cachée).
  const intInp = document.getElementById('maint-intervalle');
  const mInp   = document.getElementById('maint-metrage-ref');
  if (!perSel || !intInp || !mInp) return;
  perSel.disabled = false;
  const isPeriodic = (perSel.value === 'oui');
  intInp.disabled = !isPeriodic;
  intInp.style.opacity = isPeriodic ? '1' : '0.5';
  mInp.disabled   = !isPeriodic;
  mInp.style.opacity = isPeriodic ? '1' : '0.5';
  mInp.style.display = '';
  if (!isPeriodic) {
    intInp.value = '';
    mInp.value   = '';
  }
}
function closeMaintForm() {
  _maintEditCode = null;
  const wrap = document.getElementById('maint-form-wrap');
  if (wrap) wrap.classList.add('hidden');
}
async function saveMaintForm() {
  const code = (document.getElementById('maint-code').value || '').trim();
  const label = (document.getElementById('maint-label').value || '').trim();
  const niveau = parseInt(document.getElementById('maint-niveau').value, 10) || 1;
  const rawCat = (document.getElementById('maint-categorie')?.value || '').trim();
  // Depuis v178 : 3 catégories ('controles', 'entretien', 'remplacements').
  // Legacy 'interventions' est remappée vers 'entretien' pour rester compat.
  const categorie = (rawCat === 'entretien' || rawCat === 'remplacements' || rawCat === 'controles')
    ? rawCat
    : (rawCat === 'interventions' ? 'entretien' : 'controles');
  // v2.2.17 — periodique forcé à true (concept retiré côté UI).
  const periodique = true;
  const intervalle  = (document.getElementById('maint-intervalle')?.value  || '').trim();
  const metrage_ref = (document.getElementById('maint-metrage-ref')?.value || '').trim();
  if (!code) { toast('Code obligatoire', true); return; }
  if (!label) { toast('Libellé obligatoire', true); return; }
  if (niveau < 1 || niveau > 3) { toast('Niveau invalide (1-3)', true); return; }
  const payload = { code, label, niveau, categorie, periodique, intervalle, metrage_ref };
  try {
    if (_maintEditCode) {
      await api('/api/maintenance/codes/' + encodeURIComponent(_maintEditCode), {
        method: 'PUT',
        body: JSON.stringify(payload),
      });
      toast('Code mis à jour');
    } else {
      await api('/api/maintenance/codes', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      toast('Code ajouté');
    }
  } catch (e) {
    toast(e && e.message ? e.message : 'Erreur lors de l\'enregistrement', true);
    return;
  }
  closeMaintForm();
  await loadMaintCodes();
  // Sync côté Alertes : une création/modif de code peut créer, renommer
  // ou supprimer l'alerte auto-liée (via le hook backend _sync_alert_for_code).
  if(typeof loadAlerts === 'function') await loadAlerts();
}
async function deleteMaintCode(code) {
  if (!confirm('Supprimer le code ' + code + ' ?')) return;
  try {
    await api('/api/maintenance/codes/' + encodeURIComponent(code), { method: 'DELETE' });
    toast('Code supprimé');
  } catch (e) {
    toast(e && e.message ? e.message : 'Erreur lors de la suppression', true);
    return;
  }
  await loadMaintCodes();
  // La suppression d'un code déclenche la cascade DELETE de l'alerte liée
  // côté backend — on force le rechargement pour que la liste se mette à jour.
  if(typeof loadAlerts === 'function') await loadAlerts();
}

// ── Sous-onglets Maintenance (Codes / Alertes) ─────────────────────
document.addEventListener('click', (ev) => {
  const btn = ev.target.closest('[data-maintsub]');
  if (!btn) return;
  const target = btn.dataset.maintsub;
  document.querySelectorAll('[data-maintsub]').forEach(b => b.classList.toggle('active', b === btn));
  document.querySelectorAll('.maint-subtab').forEach(p => {
    p.style.display = (p.id === target) ? '' : 'none';
  });
  // v182 Lot 2 : charge la liste des libres a la premiere ouverture du sous-onglet
  if (target === 'maint-subtab-libres' && typeof loadLibres === 'function') {
    loadLibres();
  }
});

// ── Alertes maintenance (gestion super admin) ──────────────────────
let _alertsData = [];

async function loadAlerts() {
  const box = document.getElementById('alerts-list');
  if (!box) return;
  try {
    const r = await api('/api/maintenance/alerts');
    _alertsData = (r && Array.isArray(r.items)) ? r.items : [];
  } catch (e) {
    box.innerHTML = '<p style="color:var(--danger);font-size:13px">Erreur de chargement : ' + esc(e && e.message ? e.message : String(e)) + '</p>';
    return;
  }
  renderAlertsList();
  // Re-render aussi la table des codes pour rafraîchir la colonne
  // "Dernière intervention" qui dépend des alertes liées.
  if (typeof renderMaintList === 'function') renderMaintList();
}

function _fmtAlertDate(s) {
  if (!s) return '';
  const t = String(s).replace('T', ' ').slice(0, 16);
  return t;
}

let _alertsFilterKind = 'all';

function _alertIsConfigured(a) {
  // Une alerte est "configurée" dès qu'elle a au moins une clé de paramètre
  // (trigger / target / validation / checklist) renseignée par l'admin.
  // Les alertes auto-créées par la migration v133 démarrent avec params={}.
  if (!a || !a.params || typeof a.params !== 'object') return false;
  return Object.keys(a.params).length > 0;
}

function renderAlertsList() {
  const box = document.getElementById('alerts-list');
  if (!box) return;
  if (!_alertsData.length) {
    box.innerHTML = '<div class="alert-preview-empty">Aucune alerte pour l\'instant. Clique sur « + Nouvelle alerte » pour en créer une.</div>';
    return;
  }
  const q = (document.getElementById('alerts-filter-q')?.value || '').trim().toLowerCase();
  const filtered = _alertsData.filter(a => {
    // v2.2.16 — Filtre Auto/Manuelles retiré. Seul le search reste actif.
    if (q) {
      const hay = (a.nom || '').toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
  if (!filtered.length) {
    box.innerHTML = '<div class="alert-preview-empty">Aucune alerte pour ce filtre.</div>';
    return;
  }
  const html = filtered.map(a => {
    const isAuto = !!a.linked_maint_code;
    const configured = _alertIsConfigured(a);
    let cls = a.active ? 'is-active' : 'is-inactive';
    if (!configured) cls += ' is-todo';
    const created = _fmtAlertDate(a.created_at);
    // v2.2.16 — Badge Auto retiré (système d'alertes auto supprimé).
    const autoBadge = '';
    const todoBadge = (!configured)
      ? '<span class="alert-badge todo" title="Cette alerte n\'a pas encore été configurée — cliquez sur Modifier pour renseigner ses paramètres.">À configurer</span>'
      : '';
    const badge = autoBadge + todoBadge;
    const lastAck = a.last_ack_at
      ? ' · Dernière intervention : ' + esc(_fmtAlertDate(a.last_ack_at))
      : (isAuto ? ' · Jamais effectuée' : '');
    const delBtn = isAuto
      ? ''
      : '<button type="button" class="btn-sm btn-ghost danger" data-alert-del="' + a.id + '">Supprimer</button>';
    return '<div class="alert-row ' + cls + '" data-alert-id="' + a.id + '">'
      + '<label class="toggle" title="' + (a.active ? 'Désactiver' : 'Activer') + '">'
      +   '<input type="checkbox" ' + (a.active ? 'checked' : '') + ' data-alert-toggle="' + a.id + '">'
      +   '<span class="toggle-track"><span class="toggle-thumb"></span></span>'
      + '</label>'
      + '<div class="alert-info">'
      +   '<p class="alert-nom">' + esc(a.nom) + ' ' + badge + '</p>'
      +   '<span class="alert-meta">Créée le ' + esc(created) + (a.created_by_display ? ' · ' + esc(a.created_by_display) : '') + lastAck + '</span>'
      + '</div>'
      + '<div class="alert-actions">'
      +   '<button type="button" class="btn-sm btn-ghost" data-alert-preview="' + a.id + '" title="Ouvre l\'alerte sur ton écran avec les vrais champs interactifs. Aucune donnée n\'est enregistrée.">Tester sur moi</button>'
      +   '<button type="button" class="btn-sm btn-ghost" data-alert-edit="' + a.id + '">Modifier</button>'
      +   delBtn
      + '</div>'
      + '</div>';
  }).join('');
  box.innerHTML = html;
  box.querySelectorAll('[data-alert-toggle]').forEach(el => {
    el.addEventListener('change', () => toggleAlert(parseInt(el.getAttribute('data-alert-toggle'), 10), el.checked));
  });
  box.querySelectorAll('[data-alert-preview]').forEach(btn => {
    btn.addEventListener('click', () => previewAlert(parseInt(btn.getAttribute('data-alert-preview'), 10)));
  });
  box.querySelectorAll('[data-alert-edit]').forEach(btn => {
    btn.addEventListener('click', () => openEditAlertModal(parseInt(btn.getAttribute('data-alert-edit'), 10)));
  });
  box.querySelectorAll('[data-alert-del]').forEach(btn => {
    btn.addEventListener('click', () => deleteAlert(parseInt(btn.getAttribute('data-alert-del'), 10)));
  });
}

function _taOnOtherChange(inp){
  const item = inp.closest('.ta-cl-item');
  if(!item) return;
  const txt = item.querySelector('.ta-cl-other-text');
  if(!txt) return;
  const isMulti = inp.type === 'checkbox';
  let show;
  if(isMulti){
    show = inp.checked;
  } else {
    // radio : Autre est le seul coché à cet instant
    show = inp.checked;
  }
  txt.style.display = show ? '' : 'none';
  if(show){ setTimeout(() => txt.focus(), 30); }
  else { txt.value = ''; }
}

function _taOnValueInput(inp) {
  // Feedback visuel en mode test : bordure rouge si valeur hors tolérance.
  // Aucun blocage — purement informatif.
  const item = inp.closest('.ta-cl-item');
  if (!item) return;
  const minAttr = item.getAttribute('data-min');
  const maxAttr = item.getAttribute('data-max');
  const v = parseFloat(inp.value);
  let outOfRange = false;
  if (!isNaN(v)) {
    if (minAttr !== null && minAttr !== '' && v < parseFloat(minAttr)) outOfRange = true;
    if (maxAttr !== null && maxAttr !== '' && v > parseFloat(maxAttr)) outOfRange = true;
  }
  inp.style.borderColor = outOfRange ? 'var(--danger)' : 'var(--border)';
  inp.style.color = outOfRange ? 'var(--danger)' : 'var(--text)';
}

// Bascule filtre Toutes / Auto / Manuelles
document.addEventListener('click', (ev) => {
  const btn = ev.target.closest('[data-alerts-filter]');
  if (!btn) return;
  _alertsFilterKind = btn.getAttribute('data-alerts-filter');
  document.querySelectorAll('[data-alerts-filter]').forEach(b => b.classList.toggle('active', b === btn));
  renderAlertsList();
});

// Référentiels pour les formulaires d'alerte
const _ALERT_TRIGGER_TYPES = [
  { v: 'manual',   l: 'Manuel — déclenché par l\'opérateur' },
  { v: 'periodic', l: 'Périodique — toutes les X minutes' },
  { v: 'calendar', l: 'Calendaire — à heure fixe' },
  { v: 'event',    l: 'Événementiel — sur action métier' },
];
const _ALERT_TRIGGER_EVENTS = [
  { v: 'dossier_start',  l: 'Début de dossier' },
  { v: 'dossier_end',    l: 'Fin de dossier' },
];
const _ALERT_MACHINES = ['*', 'Cohésio 1', 'Cohésio 2', 'DSI', 'Repiquage'];
const _ALERT_ROLES = ['*', 'fabrication', 'logistique', 'expedition', 'comptabilite', 'commercial', 'administration', 'administration_ventes', 'administration_technique', 'direction', 'superadmin'];
const _ALERT_DAYS = [
  { v: 'mon', l: 'Lun' }, { v: 'tue', l: 'Mar' }, { v: 'wed', l: 'Mer' },
  { v: 'thu', l: 'Jeu' }, { v: 'fri', l: 'Ven' }, { v: 'sat', l: 'Sam' }, { v: 'sun', l: 'Dim' },
];

function _alertDefaults(existing) {
  const p = existing || {};
  const trig = Object.assign({}, p.trigger || {});
  // Compat rétro : si seul interval_hours est présent, on convertit en minutes.
  if (trig.interval_minutes == null && trig.interval_hours != null) {
    trig.interval_minutes = Math.round(Number(trig.interval_hours) * 60);
    delete trig.interval_hours;
  }
  // Target : nouveau format = { machines: [...] }. Compat avec ancien { machine, role }.
  const rawTarget = p.target || {};
  let machines = rawTarget.machines;
  if (!Array.isArray(machines)) {
    if (typeof rawTarget.machine === 'string' && rawTarget.machine) {
      machines = [rawTarget.machine];
    } else {
      machines = ['*'];
    }
  }
  // Checklist : normalisation des items pour inclure le champ type (choice/value)
  // et la conversion des anciens items "string" en objets.
  const cl = Object.assign({ enabled: false, items: [] }, p.checklist || {});
  if (!Array.isArray(cl.items)) cl.items = [];
  cl.items = cl.items.map(it => {
    if (typeof it === 'string') {
      return { type: 'choice', label: it, responses: ['Conforme'] };
    }
    const t = (it && it.type) || 'choice';
    if (t === 'value') {
      return {
        type: 'value',
        label: (it && it.label) || '',
        unit: (it && it.unit) || '',
        min: (it && it.min != null && it.min !== '') ? Number(it.min) : null,
        max: (it && it.max != null && it.max !== '') ? Number(it.max) : null,
      };
    }
    const responses = Array.isArray(it && it.responses) ? it.responses.filter(r => typeof r === 'string' && r.trim()) : [];
    const ncResp = (it && Array.isArray(it.nc_responses))
      ? it.nc_responses.filter(r => typeof r === 'string' && r.trim())
      : [];
    return {
      type: 'choice',
      label: (it && it.label) || '',
      responses: responses.length ? responses : ['Conforme'],
      multi: (it && it.multi === false) ? false : true,
      allow_other: !!(it && it.allow_other),
      other_is_nc: !!(it && it.other_is_nc),
      nc_responses: ncResp,
    };
  });
  return {
    description: (typeof p.description === 'string') ? p.description : '',
    trigger: Object.assign({ type: 'manual', interval_minutes: 120, grace_minutes: 5, time: '08:00', days: ['mon','tue','wed','thu','fri'], event: 'dossier_start' }, trig),
    target: { machines: machines },
    validation: Object.assign({ button_label: 'Valider' }, p.validation || {}),
    dismiss_button: Object.assign({ enabled: false, label: 'Fermer l\'alerte' }, p.dismiss_button || {}),
    checklist: cl,
  };
}

function _renderAlertFormFields(params, opts) {
  opts = opts || {};
  const d = _alertDefaults(params);
  // Machines (multi-sélection via dropdown)
  const machineList = _ALERT_MACHINES.filter(m => m !== '*');
  const selectedMachines = (d.target && Array.isArray(d.target.machines)) ? d.target.machines : ['*'];
  const isAllMachines = selectedMachines.includes('*');
  const machineCheckboxes = machineList.map(m => {
    const checked = (!isAllMachines && selectedMachines.includes(m)) ? 'checked' : '';
    const disabled = isAllMachines ? ' disabled' : '';
    const rowCls = isAllMachines ? 'af-md-row is-disabled' : 'af-md-row';
    const safeM = escAttr(m);
    return '<div class="' + rowCls + '" onclick="_afRowClickByValue(event, \'' + safeM + '\')">'
      + '<input type="checkbox" class="af-machine" value="' + safeM + '"' + (checked ? ' ' + checked : '') + disabled + ' onchange="_afOnMachineChange()">'
      + '<div class="af-md-row-text">' + esc(m) + '</div>'
      + '</div>';
  }).join('');
  let machinesInitialLabel;
  if (isAllMachines) {
    machinesInitialLabel = 'Toutes les machines';
  } else if (selectedMachines.length === 0) {
    machinesInitialLabel = 'Aucune machine sélectionnée';
  } else if (selectedMachines.length === 1) {
    machinesInitialLabel = selectedMachines[0];
  } else if (selectedMachines.length <= 3) {
    machinesInitialLabel = selectedMachines.join(', ');
  } else {
    machinesInitialLabel = selectedMachines.length + ' machines';
  }
  const triggerOpts = _ALERT_TRIGGER_TYPES.map(t =>
    '<option value="' + t.v + '"' + (t.v === d.trigger.type ? ' selected' : '') + '>' + esc(t.l) + '</option>'
  ).join('');
  const eventOpts = _ALERT_TRIGGER_EVENTS.map(e =>
    '<option value="' + e.v + '"' + (e.v === d.trigger.event ? ' selected' : '') + '>' + esc(e.l) + '</option>'
  ).join('');
  const daysHtml = _ALERT_DAYS.map(day => {
    const checked = (d.trigger.days || []).indexOf(day.v) >= 0 ? 'checked' : '';
    return '<label style="display:inline-flex;align-items:center;gap:4px;padding:4px 8px;background:var(--card);border:1px solid var(--border);border-radius:6px;cursor:pointer;font-size:12px"><input type="checkbox" class="af-day" value="' + day.v + '" ' + checked + ' style="margin:0">' + day.l + '</label>';
  }).join(' ');

  const nomBlock = opts.nomReadonly
    ? '<div class="alert-field"><label class="alert-field-label">Titre <span style="color:var(--muted);text-transform:none;letter-spacing:0;font-weight:400">— synchronisé avec le code</span></label><input type="text" class="alert-field-input" value="' + escAttr(opts.nomValue || '') + '" disabled></div>'
    : '<div class="alert-field"><label class="alert-field-label">Titre de l\'alerte <span style="color:var(--danger)">*</span></label><input type="text" id="af-nom" class="alert-field-input" maxlength="120" placeholder="Ex. Contrôle qualité Cohésio 1" value="' + escAttr(opts.nomValue || '') + '"></div>';

  const descBlock = '<div class="alert-field">'
    +   '<label class="alert-field-label">Description <span style="color:var(--muted);text-transform:none;letter-spacing:0;font-weight:400">— contexte affiché à l\'opérateur</span></label>'
    +   '<textarea id="af-description" class="alert-field-input" rows="2" maxlength="800" placeholder="Ex. Vérifier la tension Errepi et le serrage de la bobine — noter la valeur exacte pour analyse.">' + esc(d.description || '') + '</textarea>'
    +   '<div class="alert-field-help">Optionnel. Affiché sous le titre de l\'alerte quand elle apparaît chez l\'opérateur.</div>'
    + '</div>';
  return nomBlock
    + descBlock
    + '<div class="alert-field">'
    +   '<label class="alert-field-label">Déclencheur <span style="color:var(--danger)">*</span></label>'
    +   '<select id="af-trigger-type" class="alert-field-input" onchange="_afOnTriggerChange()">' + triggerOpts + '</select>'
    +   '<div id="af-trigger-sub" class="alert-field-sub">'
    +     '<div data-trigger-for="manual" style="font-size:12px;color:var(--muted)">Aucun déclenchement automatique — l\'opérateur ouvrira l\'alerte lui-même.</div>'
    +     '<div data-trigger-for="periodic">'
    +       '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">'
    +         '<div>'
    +           '<label class="alert-field-label" style="text-transform:none;letter-spacing:0;font-size:12px;color:var(--text2)">Intervalle entre alertes (min)</label>'
    +           '<input type="number" id="af-trigger-interval-minutes" class="alert-field-input" min="1" max="10080" step="1" value="' + d.trigger.interval_minutes + '">'
    +         '</div>'
    +         '<div>'
    +           '<label class="alert-field-label" style="text-transform:none;letter-spacing:0;font-size:12px;color:var(--text2)">Délai avant 1ère alerte (min)</label>'
    +           '<input type="number" id="af-trigger-grace-minutes" class="alert-field-input" min="0" max="120" step="1" value="' + (d.trigger.grace_minutes != null ? d.trigger.grace_minutes : 5) + '">'
    +         '</div>'
    +       '</div>'
    +       '<div class="alert-field-help">La <strong>première alerte</strong> de chaque session de production s\'affiche après le délai indiqué (par défaut 5 min). Les alertes suivantes s\'affichent toutes les X minutes après la dernière validation. Une nouvelle session redémarre après chaque interruption de production. Utiliser des délais différents entre alertes pour les espacer naturellement au démarrage.</div>'
    +     '</div>'
    +     '<div data-trigger-for="calendar">'
    +       '<div class="alert-field-row">'
    +         '<div><label class="alert-field-label" style="text-transform:none;letter-spacing:0;font-size:12px;color:var(--text2)">Heure</label><input type="time" id="af-trigger-time" class="alert-field-input" value="' + esc(d.trigger.time) + '"></div>'
    +         '<div></div>'
    +       '</div>'
    +       '<label class="alert-field-label" style="text-transform:none;letter-spacing:0;font-size:12px;color:var(--text2);margin-top:8px">Jours</label>'
    +       '<div style="display:flex;flex-wrap:wrap;gap:6px">' + daysHtml + '</div>'
    +     '</div>'
    +     '<div data-trigger-for="event">'
    +       '<label class="alert-field-label" style="text-transform:none;letter-spacing:0;font-size:12px;color:var(--text2)">Événement</label>'
    +       '<select id="af-trigger-event" class="alert-field-input" onchange="_afOnTriggerEventChange()">' + eventOpts + '</select>'
    +       '<!-- v2.2.42 : Filtre produit retiré (jamais fonctionné) -->'
    +     '</div>'
    +   '</div>'
    + '</div>'
    + '<div class="alert-field">'
    +   '<label class="alert-field-label">Machines ciblées <span style="color:var(--danger)">*</span></label>'
    +   '<div class="af-md-wrap">'
    +     '<button type="button" class="af-md-trigger" onclick="_afToggleMachinesPanel(event)">'
    +       '<span id="af-md-label" class="af-md-trigger-label">' + esc(machinesInitialLabel) + '</span>'
    +       '<span class="af-md-trigger-caret">▼</span>'
    +     '</button>'
    +     '<div id="af-md-panel" class="af-md-panel">'
    +       '<div class="af-md-row" onclick="_afRowClick(event, \'af-target-all\')">'
    +         '<input type="checkbox" id="af-target-all" ' + (isAllMachines ? 'checked' : '') + ' onchange="_afOnAllMachinesToggle()">'
    +         '<div class="af-md-row-text"><strong>Toutes les machines</strong><span class="af-md-row-hint">présentes et futures</span></div>'
    +       '</div>'
    +       '<div class="af-md-sep"></div>'
    +       machineCheckboxes
    +     '</div>'
    +   '</div>'
    +   '<div class="alert-field-help">Les alertes sont toujours visibles par les opérateurs <strong>fabrication</strong> ainsi que par le super administrateur (pour les tests).</div>'
    + '</div>'
    + '<div class="alert-field">'
    +   '<label class="alert-field-label">Validation <span style="color:var(--danger)">*</span></label>'
    +   '<input type="text" id="af-validation-label" class="alert-field-input" maxlength="40" value="' + escAttr(d.validation.button_label) + '" placeholder="Valider">'
    +   '<div class="alert-field-help">Libellé du bouton que l\'opérateur cliquera pour fermer l\'alerte une fois le contrôle effectué.</div>'
    + '</div>'
    + '<div class="alert-field" style="border-top:1px solid var(--border);padding-top:14px;margin-top:14px">'
    +   '<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:8px">'
    +     '<div>'
    +       '<label class="alert-field-label" style="margin-bottom:2px">Autoriser la fermeture sans saisie</label>'
    +       '<span style="font-size:11px;color:var(--muted)">Ajoute un 2e bouton pour esquiver l\'alerte. Aucune trace nulle part.</span>'
    +     '</div>'
    +     '<label class="toggle"><input type="checkbox" id="af-dismiss-enabled" ' + (d.dismiss_button.enabled ? 'checked' : '') + ' onchange="_afOnDismissToggle()"><span class="toggle-track"><span class="toggle-thumb"></span></span></label>'
    +   '</div>'
    +   '<div id="af-dismiss-wrap" style="' + (d.dismiss_button.enabled ? '' : 'display:none;') + '">'
    +     '<input type="text" id="af-dismiss-label" class="alert-field-input" maxlength="40" value="' + escAttr(d.dismiss_button.label) + '" placeholder="Fermer l\'alerte">'
    +     '<div class="alert-field-help">Libellé du bouton d\'esquive (bouton orange à côté du bouton principal Valider).</div>'
    +   '</div>'
    + '</div>'
    + '<div class="alert-field" style="border-top:1px solid var(--border);padding-top:14px;margin-top:14px">'
    +   '<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:8px">'
    +     '<div>'
    +       '<label class="alert-field-label" style="margin-bottom:2px">Questionnaire (points de contrôle)</label>'
    +       '<span style="font-size:11px;color:var(--muted)">Ex. découpe nette, colle conforme, centrage OK… L\'opérateur cochera chaque point lors de la validation.</span>'
    +     '</div>'
    +     '<label class="toggle"><input type="checkbox" id="af-checklist-enabled" ' + (d.checklist.enabled ? 'checked' : '') + ' onchange="_afOnChecklistToggle()"><span class="toggle-track"><span class="toggle-thumb"></span></span></label>'
    +   '</div>'
    +   '<div id="af-checklist-wrap" style="' + (d.checklist.enabled ? '' : 'display:none;') + '">'
    +     '<div id="af-checklist-items" style="display:flex;flex-direction:column;gap:6px;margin-bottom:8px">' + _afRenderChecklistItems(d.checklist.items) + '</div>'
    +     '<button type="button" class="btn-sm btn-ghost" onclick="_afAddChecklistItem()" style="margin-bottom:10px"><span style="font-weight:700;margin-right:4px">+</span> Ajouter un point de contrôle</button>'
    +   '</div>'
    + '</div>'
    + '<div class="alert-field-sub" style="border-style:solid;background:var(--accent-bg);border-color:var(--accent);margin-top:14px">'
    +   '<p style="margin:0;font-size:12px;color:var(--text)"><strong>Zone de commentaires</strong> — toujours disponible pour l\'opérateur (champ texte libre, optionnel, joint à chaque acquittement).</p>'
    + '</div>';
}

function _afResponseRow(value, isNc) {
  const safeVal = (value || '').replace(/"/g, '&quot;');
  const ncChecked = isNc ? ' checked' : '';
  return '<div class="af-cl-resp-row" style="display:flex;gap:6px;align-items:center">'
    + '<input type="text" class="alert-field-input af-cl-resp-input" maxlength="100" placeholder="Ex. Nette" value="' + safeVal + '" style="flex:1;padding:6px 10px;font-size:13px">'
    + '<label class="af-cl-nc-lbl" title="Cocher si cette réponse signale une non-conformité" style="display:inline-flex;align-items:center;gap:4px;padding:4px 8px;border-radius:6px;border:1px solid var(--border);background:var(--bg);cursor:pointer;font-size:11px;color:var(--text2);white-space:nowrap;user-select:none">'
    +   '<input type="checkbox" class="af-cl-resp-nc"' + ncChecked + ' style="width:12px;height:12px;accent-color:var(--danger);cursor:pointer">'
    +   '<span>NC</span>'
    + '</label>'
    + '<button type="button" class="btn-sm btn-ghost danger" onclick="_afRemoveResponse(this)" title="Supprimer cette réponse">×</button>'
    + '</div>';
}

function _afChecklistCardBody(item) {
  const type = (item && item.type) || 'choice';
  if (type === 'value') {
    const safeUnit = ((item && item.unit) || '').replace(/"/g, '&quot;');
    const safeMin = (item && item.min != null && item.min !== '') ? String(item.min) : '';
    const safeMax = (item && item.max != null && item.max !== '') ? String(item.max) : '';
    return '<div class="af-cl-body" data-type="value">'
      + '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px">'
      +   '<div><div style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px">Unité</div><input type="text" class="alert-field-input af-cl-unit" maxlength="20" placeholder="bar, °C, mm…" value="' + safeUnit + '" style="padding:6px 10px;font-size:13px"></div>'
      +   '<div><div style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px">Min</div><input type="number" step="any" class="alert-field-input af-cl-min" placeholder="2.5" value="' + safeMin + '" style="padding:6px 10px;font-size:13px"></div>'
      +   '<div><div style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px">Max</div><input type="number" step="any" class="alert-field-input af-cl-max" placeholder="3.2" value="' + safeMax + '" style="padding:6px 10px;font-size:13px"></div>'
      + '</div>'
      + '<div class="alert-field-help" style="margin-top:6px">Pour pression, température, dimension… L\'opérateur saisira une valeur. Min/Max sont optionnels (vide = pas de borne).</div>'
      + '</div>';
  }
  // type "choice"
  const responses = (item && Array.isArray(item.responses) && item.responses.length) ? item.responses : ['Conforme'];
  const ncList = (item && Array.isArray(item.nc_responses)) ? item.nc_responses.map(String) : [];
  const responsesHtml = responses.map((r) => _afResponseRow(r, ncList.indexOf(String(r)) !== -1)).join('');
  const multi = (item && item.multi === false) ? false : true;
  return '<div class="af-cl-body" data-type="choice">'
    + '<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:6px;flex-wrap:wrap">'
    +   '<div style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px">Réponses possibles</div>'
    +   '<select class="alert-field-input af-cl-multi-sel" style="flex:0 0 auto;width:auto;padding:5px 8px;font-size:12px">'
    +     '<option value="multi"' + (multi ? ' selected' : '') + '>Plusieurs réponses (cases)</option>'
    +     '<option value="single"' + (!multi ? ' selected' : '') + '>Une seule réponse (radio)</option>'
    +   '</select>'
    + '</div>'
    + '<div class="af-cl-responses" style="display:flex;flex-direction:column;gap:4px">' + responsesHtml + '</div>'
    + '<button type="button" class="btn-sm btn-ghost" onclick="_afAddResponse(this)" style="margin-top:6px;font-size:12px"><span style="font-weight:700;margin-right:4px">+</span> Ajouter une réponse</button>'
    + '<label style="display:flex;align-items:center;gap:8px;margin-top:8px;padding-top:8px;border-top:1px dashed var(--border);cursor:pointer;font-size:12px;color:var(--text2)">'
    +   '<input type="checkbox" class="af-cl-other-toggle"' + ((item && item.allow_other) ? ' checked' : '') + ' onchange="_afOnOtherToggle(this)" style="width:14px;height:14px;accent-color:var(--accent);cursor:pointer">'
    +   '<span>Ajouter une réponse <strong style="color:var(--text)">« Autre »</strong> avec zone d\'explication optionnelle</span>'
    + '</label>'
    + '<label class="af-cl-other-nc-lbl" style="display:' + ((item && item.allow_other) ? 'flex' : 'none') + ';align-items:center;gap:8px;margin-top:4px;margin-left:22px;cursor:pointer;font-size:12px;color:var(--text2)">'
    +   '<input type="checkbox" class="af-cl-other-nc"' + ((item && item.other_is_nc) ? ' checked' : '') + ' style="width:13px;height:13px;accent-color:var(--danger);cursor:pointer">'
    +   '<span>Traiter <strong style="color:var(--text)">« Autre »</strong> comme une <strong style="color:var(--danger)">non-conformité</strong></span>'
    + '</label>'
    + '</div>';
}

function _afOnOtherToggle(cb){
  const body = cb.closest('.af-cl-body');
  if(!body) return;
  const ncLbl = body.querySelector('.af-cl-other-nc-lbl');
  if(!ncLbl) return;
  if(cb.checked){ ncLbl.style.display = 'flex'; }
  else {
    ncLbl.style.display = 'none';
    const inp = ncLbl.querySelector('.af-cl-other-nc');
    if(inp) inp.checked = false;
  }
}

function _afChecklistCard(item) {
  const safeLabel = ((item && item.label) || '').replace(/"/g, '&quot;');
  const type = (item && item.type) || 'choice';
  const typeOpts = '<option value="choice"' + (type === 'choice' ? ' selected' : '') + '>Cases à cocher</option>'
                 + '<option value="value"' + (type === 'value' ? ' selected' : '') + '>Valeur à saisir</option>';
  return '<div class="af-cl-card" style="background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px 12px;display:flex;flex-direction:column;gap:8px">'
    + '<div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap">'
    +   '<input type="text" class="alert-field-input af-cl-label" maxlength="200" placeholder="Ex. Découpe" value="' + safeLabel + '" style="flex:1;min-width:140px;font-weight:500">'
    +   '<select class="alert-field-input af-cl-type" onchange="_afOnTypeChange(this)" style="flex:0 0 auto;width:auto;padding:8px 10px;font-size:13px">' + typeOpts + '</select>'
    +   '<button type="button" class="btn-sm btn-ghost danger" onclick="_afRemoveItem(this)" title="Supprimer ce point de contrôle" style="flex:0 0 auto">×</button>'
    + '</div>'
    + _afChecklistCardBody(item)
    + '</div>';
}

function _afOnTypeChange(sel) {
  const card = sel.closest('.af-cl-card');
  if (!card) return;
  const oldBody = card.querySelector('.af-cl-body');
  if (!oldBody) return;
  const newType = sel.value;
  const defaultItem = (newType === 'value')
    ? { type: 'value', label: '', unit: '', min: null, max: null }
    : { type: 'choice', label: '', responses: ['Conforme'], multi: true, allow_other: false };
  const tmp = document.createElement('div');
  tmp.innerHTML = _afChecklistCardBody(defaultItem);
  const newBody = tmp.firstElementChild;
  if (newBody) oldBody.replaceWith(newBody);
}

function _afRenderChecklistItems(items) {
  const list = (items && items.length) ? items : [{ label: '', responses: ['Conforme'] }];
  return list.map(_afChecklistCard).join('');
}

function _afAddChecklistItem() {
  const wrap = document.getElementById('af-checklist-items');
  if (!wrap) return;
  const tmp = document.createElement('div');
  tmp.innerHTML = _afChecklistCard({ type: 'choice', label: '', responses: ['Conforme'], multi: true, allow_other: false });
  const card = tmp.firstElementChild;
  wrap.appendChild(card);
  card.querySelector('.af-cl-label')?.focus();
}

function _afAddResponse(btn) {
  const card = btn.closest('.af-cl-card');
  if (!card) return;
  const list = card.querySelector('.af-cl-responses');
  if (!list) return;
  const tmp = document.createElement('div');
  tmp.innerHTML = _afResponseRow('');
  const row = tmp.firstElementChild;
  list.appendChild(row);
  row.querySelector('.af-cl-resp-input')?.focus();
}

function _afRemoveResponse(btn) {
  const row = btn.closest('.af-cl-resp-row');
  if (!row) return;
  const list = row.parentElement;
  if (!list) { row.remove(); return; }
  // Garde au moins une réponse par point
  if (list.querySelectorAll('.af-cl-resp-row').length <= 1) {
    toast('Un point doit garder au moins une réponse', true);
    return;
  }
  row.remove();
}

function _afRemoveItem(btn) {
  const card = btn.closest('.af-cl-card');
  if (card) card.remove();
}

function _afOnChecklistToggle() {
  const enabled = document.getElementById('af-checklist-enabled')?.checked;
  const wrap = document.getElementById('af-checklist-wrap');
  if (wrap) wrap.style.display = enabled ? '' : 'none';
  if (enabled) {
    const cards = document.querySelectorAll('.af-cl-card');
    if (!cards.length) _afAddChecklistItem();
  }
}

// v164 : toggle du bouton dismiss (fermeture sans saisie)
function _afOnDismissToggle() {
  const en = document.getElementById('af-dismiss-enabled')?.checked;
  const wrap = document.getElementById('af-dismiss-wrap');
  if (wrap) wrap.style.display = en ? '' : 'none';
}

// v2.2.42 : no-op depuis le retrait du filtre produit.
function _afOnTriggerEventChange() { /* no-op */ }

function _afRowClick(ev, inputId) {
  // Click n'importe où sur la ligne → toggle l'input. On ignore le click direct
  // sur l'input pour éviter le double toggle (l'input gère son propre click).
  if (ev.target.tagName === 'INPUT') return;
  const inp = document.getElementById(inputId);
  if (!inp || inp.disabled) return;
  inp.checked = !inp.checked;
  inp.dispatchEvent(new Event('change', { bubbles: true }));
}

function _afRowClickByValue(ev, value) {
  if (ev.target.tagName === 'INPUT') return;
  const row = ev.currentTarget;
  const inp = row.querySelector('input.af-machine');
  if (!inp || inp.disabled) return;
  inp.checked = !inp.checked;
  inp.dispatchEvent(new Event('change', { bubbles: true }));
}

function _afOnAllMachinesToggle() {
  const allChk = document.getElementById('af-target-all');
  if (!allChk) return;
  document.querySelectorAll('.af-machine').forEach(el => {
    el.disabled = allChk.checked;
    if (allChk.checked) el.checked = false;
    const row = el.closest('.af-md-row');
    if (row) row.classList.toggle('is-disabled', allChk.checked);
  });
  _afUpdateMachinesLabel();
}

function _afOnMachineChange() {
  const allChk = document.getElementById('af-target-all');
  if (allChk && allChk.checked) {
    const anyIndividual = Array.from(document.querySelectorAll('.af-machine:checked')).length > 0;
    if (anyIndividual) allChk.checked = false;
  }
  _afUpdateMachinesLabel();
}

function _afUpdateMachinesLabel() {
  const lbl = document.getElementById('af-md-label');
  if (!lbl) return;
  const all = !!document.getElementById('af-target-all')?.checked;
  lbl.style.color = '';
  if (all) { lbl.textContent = 'Toutes les machines'; return; }
  const selected = Array.from(document.querySelectorAll('.af-machine:checked')).map(el => el.value);
  if (!selected.length) {
    lbl.textContent = 'Aucune machine sélectionnée';
    lbl.style.color = 'var(--danger)';
    return;
  }
  if (selected.length === 1) lbl.textContent = selected[0];
  else if (selected.length <= 3) lbl.textContent = selected.join(', ');
  else lbl.textContent = selected.length + ' machines';
}

function _afToggleMachinesPanel(ev) {
  if (ev) ev.stopPropagation();
  const panel = document.getElementById('af-md-panel');
  if (!panel) return;
  panel.classList.toggle('open');
}

// Fermeture du dropdown sur clic à l'extérieur (un seul listener global, idempotent)
if (!window._afMachinesDropdownInit) {
  window._afMachinesDropdownInit = true;
  document.addEventListener('click', (ev) => {
    const panel = document.getElementById('af-md-panel');
    if (!panel || !panel.classList.contains('open')) return;
    if (ev.target.closest('.af-md-wrap')) return;
    panel.classList.remove('open');
  });
}

function _afOnTriggerChange() {
  const t = document.getElementById('af-trigger-type')?.value || 'manual';
  document.querySelectorAll('#af-trigger-sub > [data-trigger-for]').forEach(el => {
    el.style.display = (el.getAttribute('data-trigger-for') === t) ? '' : 'none';
  });
}

function _afReadParams() {
  const t = document.getElementById('af-trigger-type').value || 'manual';
  const trig = { type: t };
  if (t === 'periodic') {
    const mInp = document.getElementById('af-trigger-interval-minutes');
    const m = parseInt(mInp.value, 10);
    if (!(m >= 1 && m <= 10080)) { toast('Intervalle invalide (1 ≤ minutes ≤ 10080)', true); return null; }
    trig.interval_minutes = m;
    const gInp = document.getElementById('af-trigger-grace-minutes');
    if (gInp) {
      const g = parseInt(gInp.value, 10);
      if (isNaN(g) || g < 0 || g > 120) { toast('Délai avant 1ère alerte invalide (0 à 120 min)', true); return null; }
      trig.grace_minutes = g;
    }
  } else if (t === 'calendar') {
    const tm = document.getElementById('af-trigger-time').value || '';
    if (!/^\d{2}:\d{2}$/.test(tm)) { toast('Heure invalide (HH:MM)', true); return null; }
    trig.time = tm;
    const days = Array.from(document.querySelectorAll('.af-day:checked')).map(el => el.value);
    if (!days.length) { toast('Au moins un jour requis', true); return null; }
    trig.days = days;
  } else if (t === 'event') {
    trig.event = document.getElementById('af-trigger-event').value || 'dossier_start';
    // v2.2.42 : filter_conditionnement (Filtre produit) retiré.
    delete trig.filter_conditionnement;
  }
  // Lecture du questionnaire (cartes : label + réponses possibles)
  const clEnabled = !!document.getElementById('af-checklist-enabled')?.checked;
  const items = [];
  if (clEnabled) {
    document.querySelectorAll('.af-cl-card').forEach(card => {
      const label = (card.querySelector('.af-cl-label')?.value || '').trim();
      if (!label) return;
      const type = card.querySelector('.af-cl-type')?.value || 'choice';
      if (type === 'value') {
        const unit = (card.querySelector('.af-cl-unit')?.value || '').trim();
        const minStr = (card.querySelector('.af-cl-min')?.value || '').trim();
        const maxStr = (card.querySelector('.af-cl-max')?.value || '').trim();
        const item = { type: 'value', label: label };
        if (unit) item.unit = unit;
        if (minStr !== '' && !isNaN(parseFloat(minStr))) item.min = parseFloat(minStr);
        if (maxStr !== '' && !isNaN(parseFloat(maxStr))) item.max = parseFloat(maxStr);
        items.push(item);
        return;
      }
      const responses = [];
      const ncResponses = [];
      card.querySelectorAll('.af-cl-resp-row').forEach(row => {
        const r = (row.querySelector('.af-cl-resp-input')?.value || '').trim();
        if (!r) return;
        responses.push(r);
        if (row.querySelector('.af-cl-resp-nc')?.checked) ncResponses.push(r);
      });
      if (!responses.length) return;
      const multiSel = card.querySelector('.af-cl-multi-sel')?.value;
      const multi = (multiSel === 'single') ? false : true;
      const allowOther = !!card.querySelector('.af-cl-other-toggle')?.checked;
      const otherIsNc = allowOther && !!card.querySelector('.af-cl-other-nc')?.checked;
      items.push({ type: 'choice', label: label, responses: responses, multi: multi, allow_other: allowOther, other_is_nc: otherIsNc, nc_responses: ncResponses });
    });
  }
  // Cible (lue en premier — interrompt si rien sélectionné)
  let _tgt;
  {
    const all = !!document.getElementById('af-target-all')?.checked;
    if (all) {
      _tgt = { machines: ['*'] };
    } else {
      const ms = Array.from(document.querySelectorAll('.af-machine:checked')).map(el => el.value);
      if (!ms.length) { toast('Sélectionne au moins une machine', true); return null; }
      _tgt = { machines: ms };
    }
  }
  const descEl = document.getElementById('af-description');
  const descVal = descEl ? (descEl.value || '').trim() : '';
  return {
    description: descVal.slice(0, 800),
    trigger: trig,
    target: _tgt,
    validation: {
      button_label: (document.getElementById('af-validation-label').value || 'Valider').trim() || 'Valider',
    },
    dismiss_button: (function(){
      const en = !!document.getElementById('af-dismiss-enabled')?.checked;
      if(!en) return { enabled: false, label: '' };
      const lbl = (document.getElementById('af-dismiss-label').value || 'Fermer l\'alerte').trim() || 'Fermer l\'alerte';
      return { enabled: true, label: lbl };
    })(),
    checklist: {
      enabled: clEnabled && items.length > 0,
      items: items,
    },
  };
}

function openNewAlertModal() {
  const overlay = document.createElement('div');
  overlay.className = 'alert-modal-overlay';
  overlay.innerHTML = '<div class="alert-modal">'
    + '<div class="alert-modal-head"><h3>Nouvelle alerte</h3><button type="button" class="btn-sm btn-ghost" data-close>×</button></div>'
    + '<div class="alert-modal-body">'
    +   _renderAlertFormFields(null, { nomReadonly: false, nomValue: '' })
    +   '<p style="font-size:11px;color:var(--muted);margin-top:10px">L\'alerte sera créée à l\'état <strong>inactif</strong>. Active-la via son interrupteur une fois prête.</p>'
    + '</div>'
    + '<div class="alert-modal-foot">'
    +   '<button type="button" class="btn btn-sec" data-close>Annuler</button>'
    +   '<button type="button" class="btn" id="new-alert-confirm">Créer</button>'
    + '</div></div>';
  document.body.appendChild(overlay);
  const close = () => overlay.remove();
  overlay.querySelectorAll('[data-close]').forEach(el => el.addEventListener('click', close));
  overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });
  _afOnTriggerChange();
  document.getElementById('new-alert-confirm').addEventListener('click', async () => {
    const nom = (document.getElementById('af-nom').value || '').trim();
    if (!nom) { toast('Titre obligatoire', true); return; }
    const params = _afReadParams();
    if (!params) return;
    try {
      await api('/api/maintenance/alerts', { method: 'POST', body: JSON.stringify({ nom, params }) });
      toast('Alerte créée');
      close();
      await loadAlerts();
    } catch (e) { toast(e && e.message ? e.message : 'Erreur', true); }
  });
  setTimeout(() => document.getElementById('af-nom')?.focus(), 30);
}

async function toggleAlert(id, active) {
  try {
    await api('/api/maintenance/alerts/' + id, { method: 'PATCH', body: JSON.stringify({ active: !!active }) });
    toast(active ? 'Alerte activée' : 'Alerte désactivée');
  } catch (e) {
    toast(e && e.message ? e.message : 'Erreur', true);
  }
  await loadAlerts();
}

async function deleteAlert(id) {
  const a = _alertsData.find(x => x.id === id);
  if (!a) return;
  if (!confirm('Supprimer définitivement l\'alerte « ' + a.nom + ' » ?')) return;
  try {
    await api('/api/maintenance/alerts/' + id, { method: 'DELETE' });
    toast('Alerte supprimée');
  } catch (e) {
    toast(e && e.message ? e.message : 'Erreur', true);
    return;
  }
  await loadAlerts();
}

async function disableAllAlerts() {
  const nbActive = _alertsData.filter(a => a.active).length;
  if (nbActive === 0) { toast('Aucune alerte active actuellement', true); return; }
  if (!confirm('Désactiver les ' + nbActive + ' alerte(s) active(s) ? Aucune ne sera supprimée — c\'est un kill switch d\'urgence.')) return;
  try {
    const r = await api('/api/maintenance/alerts/disable-all', { method: 'POST' });
    toast((r?.disabled || 0) + ' alerte(s) désactivée(s)');
  } catch (e) {
    toast(e && e.message ? e.message : 'Erreur', true);
    return;
  }
  await loadAlerts();
}

let _alertGlobalSettings = { placement: 'top-right', size: 'medium', block_production: false, stack_mode: 'queue', min_gap_minutes: 5 };

async function loadAlertSettings() {
  try {
    const r = await api('/api/maintenance/alert-settings');
    let placement = r.placement || 'center';
    if (placement !== 'center' && placement !== 'top-right' && placement !== 'bottom-right') {
      placement = 'center';
    }
    let minGap = 5;
    if(r.min_gap_minutes != null){
      const parsed = parseInt(r.min_gap_minutes, 10);
      if(!isNaN(parsed) && parsed >= 0) minGap = parsed;
    }
    _alertGlobalSettings = {
      placement: placement,
      size: r.size || 'medium',
      block_production: !!r.block_production,
      stack_mode: 'queue',
      min_gap_minutes: minGap,
    };
  } catch (e) {
    // En cas d'erreur, on garde les valeurs par défaut.
  }
}

function openAlertSettingsModal() {
  loadAlertSettings().then(() => {
    const overlay = document.createElement('div');
    overlay.className = 'alert-modal-overlay';
    const placements = [
      { v: 'center',       l: 'Centre (modal)' },
      { v: 'top-right',    l: 'Coin haut droit' },
      { v: 'bottom-right', l: 'Coin bas droit' },
    ];
    const sizes = [
      { v: 'small',  l: 'Petite' },
      { v: 'medium', l: 'Moyenne' },
      { v: 'large',  l: 'Grande' },
    ];
const placementOpts = placements.map(p =>
      '<option value="' + p.v + '"' + (p.v === _alertGlobalSettings.placement ? ' selected' : '') + '>' + esc(p.l) + '</option>'
    ).join('');
    const sizeOpts = sizes.map(s =>
      '<option value="' + s.v + '"' + (s.v === _alertGlobalSettings.size ? ' selected' : '') + '>' + esc(s.l) + '</option>'
    ).join('');
    overlay.innerHTML = '<div class="alert-modal">'
      + '<div class="alert-modal-head"><h3>Réglages des alertes</h3><button type="button" class="btn-sm btn-ghost" data-close>×</button></div>'
      + '<div class="alert-modal-body">'
      +   '<p style="font-size:12px;color:var(--muted);margin:0 0 14px 0">Réglages globaux appliqués à toutes les alertes actives.</p>'
      +   '<div class="alert-field">'
      +     '<label class="alert-field-label">Placement à l\'écran</label>'
      +     '<select id="ags-placement" class="alert-field-input">' + placementOpts + '</select>'
      +   '</div>'
      +   '<div class="alert-field">'
      +     '<label class="alert-field-label">Taille</label>'
      +     '<select id="ags-size" class="alert-field-input">' + sizeOpts + '</select>'
      +   '</div>'
      +   '<div class="alert-field">'
      +     '<label class="alert-field-label">Délai minimum entre deux alertes (minutes)</label>'
      +     '<input type="number" id="ags-gap" class="alert-field-input" min="0" max="120" step="1" value="' + _alertGlobalSettings.min_gap_minutes + '">'
      +     '<div class="alert-field-help">Après chaque validation d\'alerte, aucune autre alerte n\'apparaît sur l\'écran de l\'opérateur pendant ce délai. Évite qu\'il soit surchargé quand plusieurs alertes deviennent dues en même temps (typiquement à la reprise de production). 0 = pas de délai.</div>'
      +   '</div>'
      +   '<div class="alert-field" style="display:flex;align-items:center;gap:12px;justify-content:space-between">'
      +     '<div>'
      +       '<label class="alert-field-label" style="margin-bottom:2px">Bloque la production</label>'
      +       '<span style="font-size:11px;color:var(--muted)">Quand activé, l\'opérateur ne peut pas saisir de production tant que l\'alerte n\'a pas été validée.</span>'
      +     '</div>'
      +     '<label class="toggle"><input type="checkbox" id="ags-block" ' + (_alertGlobalSettings.block_production ? 'checked' : '') + '><span class="toggle-track"><span class="toggle-thumb"></span></span></label>'
      +   '</div>'
      + '</div>'
      + '<div class="alert-modal-foot">'
      +   '<button type="button" class="btn btn-sec" data-close>Annuler</button>'
      +   '<button type="button" class="btn" id="ags-save">Enregistrer</button>'
      + '</div></div>';
    document.body.appendChild(overlay);
    const close = () => overlay.remove();
    overlay.querySelectorAll('[data-close]').forEach(el => el.addEventListener('click', close));
    overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });
    document.getElementById('ags-save').addEventListener('click', async () => {
      const gapInput = document.getElementById('ags-gap');
      const gapVal = gapInput ? parseInt(gapInput.value, 10) : 5;
      const payload = {
        placement: document.getElementById('ags-placement').value,
        size: document.getElementById('ags-size').value,
        block_production: document.getElementById('ags-block').checked,
        min_gap_minutes: (isNaN(gapVal) || gapVal < 0) ? 5 : Math.min(gapVal, 120),
      };
      try {
        await api('/api/maintenance/alert-settings', { method: 'PUT', body: JSON.stringify(payload) });
        _alertGlobalSettings = payload;
        toast('Réglages enregistrés');
        close();
      } catch (e) { toast(e && e.message ? e.message : 'Erreur', true); }
    });
  });
}

function _stripAutoPrefix(nom) {
  if (!nom) return '';
  return String(nom).replace(/^Contr[oôö]le\s*:\s*\d+\s*[–\-]\s*/i, '');
}

function _alertTriggerLabel(t) {
  if (!t || !t.type) return 'Manuel';
  if (t.type === 'manual')   return 'Manuel — déclenché par l\'opérateur';
  if (t.type === 'periodic') {
    const m = (t.interval_minutes != null) ? t.interval_minutes
              : (t.interval_hours != null ? Math.round(t.interval_hours * 60) : '?');
    return 'Périodique — toutes les ' + m + ' min';
  }
  if (t.type === 'calendar') return 'Calendaire — ' + (t.time || '??:??') + ' (' + (t.days || []).join(', ') + ')';
  if (t.type === 'event') {
    const ev = (_ALERT_TRIGGER_EVENTS.find(e => e.v === t.event) || {}).l || t.event;
    return 'Événementiel — ' + ev;
  }
  return t.type;
}

async function previewAlert(id) {
  const a = _alertsData.find(x => x.id === id);
  if (!a) return;
  // Charger les réglages globaux : placement, taille, bloque-production
  await loadAlertSettings();
  const settings = _alertGlobalSettings || { placement: 'center', size: 'medium', block_production: true };
  const d = _alertDefaults(a.params);
  const machines = (d.target && Array.isArray(d.target.machines)) ? d.target.machines : ['*'];
  const machinesLbl = machines.includes('*') ? 'Toutes les machines' : machines.map(esc).join(', ');
  const clEnabled = !!(d.checklist.enabled && d.checklist.items && d.checklist.items.length);

  const checklistHtml = clEnabled
    ? '<label style="display:block;font-size:10px;font-weight:600;color:var(--text2);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px">Points de contrôle</label>'
      + '<div style="display:flex;flex-direction:column;gap:10px;margin-bottom:10px" id="ta-checklist">'
      +   d.checklist.items.map((it, idx) => {
            const itType = it.type || 'choice';
            if (itType === 'value') {
              const unit = it.unit ? '<span style="font-size:12px;color:var(--text2);font-weight:500;min-width:24px">' + esc(it.unit) + '</span>' : '';
              let toleranceHint = '';
              if (it.min != null || it.max != null) {
                const minStr = (it.min != null) ? String(it.min) : '−∞';
                const maxStr = (it.max != null) ? String(it.max) : '+∞';
                toleranceHint = '<div style="font-size:10px;color:var(--muted);margin-top:3px">Tolérance : ' + esc(minStr) + ' à ' + esc(maxStr) + (it.unit ? ' ' + esc(it.unit) : '') + '</div>';
              }
              return '<div class="ta-cl-item" data-point-idx="' + idx + '" data-type="value"'
                + (it.min != null ? ' data-min="' + esc(String(it.min)) + '"' : '')
                + (it.max != null ? ' data-max="' + esc(String(it.max)) + '"' : '') + '>'
                + '<div style="font-size:14px;font-weight:700;color:var(--text);margin-bottom:6px;display:flex;align-items:center;gap:6px"><span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--accent);flex-shrink:0"></span>' + esc(it.label) + '</div>'
                + '<div style="display:flex;align-items:center;gap:8px">'
                +   '<input type="number" step="any" class="ta-cl-val" data-point="' + idx + '" placeholder="Valeur" style="flex:1;padding:6px 10px;border-radius:7px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-size:13px;font-family:inherit;box-sizing:border-box" oninput="_taOnValueInput(this)">'
                +   unit
                + '</div>'
                + toleranceHint
                + '</div>';
            }
            const isMulti = it.multi !== false;
            const inputType = isMulti ? 'checkbox' : 'radio';
            const inputName = isMulti ? '' : ' name="ta-cl-resp-' + idx + '"';
            const respHtml = it.responses.map((r) =>
              '<label class="ta-chip">'
              + '<input type="' + inputType + '" class="ta-cl-resp" data-point="' + idx + '"' + inputName + '>'
              + '<span>' + esc(r) + '</span>'
              + '</label>'
            ).join('');
            let otherHtml = '';
            if (it.allow_other) {
              otherHtml = '<label class="ta-chip ta-chip-other">'
                + '<input type="' + inputType + '" class="ta-cl-resp ta-cl-resp-other" data-point="' + idx + '"' + inputName + ' onchange="_taOnOtherChange(this)">'
                + '<span>Autre</span>'
                + '</label>';
            }
            const otherArea = it.allow_other
              ? '<textarea class="ta-cl-other-text" data-point="' + idx + '" rows="2" placeholder="Précise (optionnel)" style="display:none;width:100%;margin-top:6px;padding:7px 10px;border-radius:7px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-size:12px;box-sizing:border-box;resize:vertical;font-family:inherit"></textarea>'
              : '';
            return '<div class="ta-cl-item" data-point-idx="' + idx + '" data-type="choice"' + (it.allow_other ? ' data-allow-other="1"' : '') + '>'
              + '<div style="font-size:14px;font-weight:700;color:var(--text);margin-bottom:6px;display:flex;align-items:center;gap:6px"><span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--accent);flex-shrink:0"></span>' + esc(it.label) + '</div>'
              + '<div style="display:flex;flex-wrap:wrap;gap:5px">' + respHtml + otherHtml + '</div>'
              + otherArea
              + '</div>';
          }).join('')
      + '</div>'
    : '';

  // Construction du wrapper de simulation (positionnement, taille, backdrop)
  const wrap = document.createElement('div');
  wrap.className = 'ta-sim ta-pl-' + (settings.placement || 'center') + ' ta-sz-' + (settings.size || 'medium');
  if (settings.block_production) wrap.classList.add('ta-blocking');

  // Bouton "Quitter le test" — toujours visible, en dehors de l'alerte
  const exitBtn = '<button type="button" class="ta-sim-exit" id="ta-sim-exit" title="Sortir du mode test">× Quitter le test</button>';

  // Description eventuelle (contexte affiche a l'operateur)
  const _descText = (a.params && typeof a.params.description === 'string') ? a.params.description.trim() : '';
  const _descHtml = _descText
    ? '<div class="ta-sim-desc" style="font-size:13px;color:var(--text2);line-height:1.5;margin:-8px 0 14px 0;padding:10px 12px;border-left:3px solid var(--accent);background:var(--accent-bg);border-radius:0 6px 6px 0;white-space:pre-wrap">' + esc(_descText) + '</div>'
    : '';

  // Contenu de l'alerte (sans aucune chrome admin)
  const alertHtml = '<div class="ta-sim-alert">'
    + '<div class="ta-sim-title">' + esc(_stripAutoPrefix(a.nom)) + '</div>'
    + _descHtml
    + checklistHtml
    + '<label style="display:block;font-size:10px;font-weight:600;color:var(--text2);text-transform:uppercase;letter-spacing:.5px;margin:8px 0 4px 0">Commentaire (optionnel)</label>'
    + '<textarea id="ta-comment" rows="2" placeholder="Ajoute un commentaire libre" style="width:100%;padding:7px 10px;border-radius:7px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-size:12px;box-sizing:border-box;resize:vertical;font-family:inherit"></textarea>'
    + '<div class="ta-sim-actions">'
    +   '<button type="button" id="ta-validate" class="ta-sim-btn">' + esc(d.validation.button_label) + '</button>'
    +   (d.dismiss_button && d.dismiss_button.enabled
        ? '<button type="button" id="ta-dismiss" class="ta-sim-btn" style="background:#f97316;color:#fff;border-color:#f97316">' + esc(d.dismiss_button.label || 'Fermer l\'alerte') + '</button>'
        : '')
    + '</div>'
    + '</div>';

  wrap.innerHTML = exitBtn + alertHtml;
  document.body.appendChild(wrap);

  const close = () => wrap.remove();

  // Sortie par le bouton "Quitter le test" — escape hatch admin universel
  document.getElementById('ta-sim-exit').addEventListener('click', close);

  // Sortie par ESC : seulement si l'alerte n'est PAS bloquante (simulation fidèle)
  const onKey = (ev) => {
    if (ev.key === 'Escape' && !settings.block_production) {
      close();
      document.removeEventListener('keydown', onKey);
    }
  };
  document.addEventListener('keydown', onKey);

  // Si non bloquant + placement coin : cliquer en dehors ferme
  if (!settings.block_production) {
    setTimeout(() => {
      const outsideClick = (ev) => {
        if (!wrap.contains(ev.target)) return;
        if (ev.target.closest('.ta-sim-alert')) return;
        if (ev.target.closest('.ta-sim-exit')) return;
        // Pour les placements en coin / haut / bas : clic sur la zone vide hors alerte
        if ((settings.placement || '').indexOf('right') >= 0) return; // pas de zone vide cliquable
        close();
        document.removeEventListener('keydown', onKey);
      };
      wrap.addEventListener('click', outsideClick);
    }, 100);
  }

  // Valider
  function _taIsComplete() {
    if (!clEnabled) return true;
    const items = wrap.querySelectorAll('.ta-cl-item');
    for (const it of items) {
      const t = it.getAttribute('data-type') || 'choice';
      if (t === 'value') {
        const v = (it.querySelector('.ta-cl-val')?.value || '').trim();
        if (v === '') return false;
      } else {
        if (!it.querySelectorAll('.ta-cl-resp:checked').length) return false;
      }
    }
    return true;
  }
  function _taFinalize() {
    toast('Test terminé — aucune donnée enregistrée.');
    close();
    document.removeEventListener('keydown', onKey);
  }
  function _taRenderValidate(actions) {
    actions.innerHTML = '<button type="button" id="ta-validate" class="ta-sim-btn">' + esc(d.validation.button_label) + '</button>';
    document.getElementById('ta-validate').addEventListener('click', _taOnValidate);
  }
  function _taRenderConfirm(actions) {
    actions.innerHTML = '<div style="display:flex;flex-direction:column;gap:8px;width:100%">'
      + '<div style="font-size:12px;color:var(--warn);line-height:1.4;text-align:center">Certains points ne sont pas remplis. Valider quand même ?</div>'
      + '<div style="display:flex;gap:6px">'
      +   '<button type="button" id="ta-edit" class="ta-sim-btn" style="flex:1;background:var(--bg);color:var(--text);border:1px solid var(--border)">Modifier</button>'
      +   '<button type="button" id="ta-confirm" class="ta-sim-btn" style="flex:1">Valider quand même</button>'
      + '</div>'
      + '</div>';
    document.getElementById('ta-confirm').addEventListener('click', _taFinalize);
    document.getElementById('ta-edit').addEventListener('click', () => _taRenderValidate(actions));
  }
  function _taOnValidate() {
    if (_taIsComplete()) { _taFinalize(); return; }
    const actions = wrap.querySelector('.ta-sim-actions');
    if (!actions) { _taFinalize(); return; }
    _taRenderConfirm(actions);
  }
  document.getElementById('ta-validate').addEventListener('click', _taOnValidate);
  // v164 : bouton dismiss dans la preview
  const taDismiss = document.getElementById('ta-dismiss');
  if (taDismiss) {
    taDismiss.addEventListener('click', () => {
      toast('Test terminé (bouton Fermer cliqué — aucune donnée enregistrée).');
      close();
      document.removeEventListener('keydown', onKey);
    });
  }
}

function openEditAlertModal(id) {
  const a = _alertsData.find(x => x.id === id);
  if (!a) return;
  const isAuto = !!a.linked_maint_code;
  const overlay = document.createElement('div');
  overlay.className = 'alert-modal-overlay';
  overlay.innerHTML = '<div class="alert-modal">'
    + '<div class="alert-modal-head"><h3>Modifier l\'alerte' + (isAuto ? ' (auto)' : '') + '</h3><button type="button" class="btn-sm btn-ghost" data-close>×</button></div>'
    + '<div class="alert-modal-body">'
    +   _renderAlertFormFields(a.params, { nomReadonly: isAuto, nomValue: a.nom })
    + '</div>'
    + '<div class="alert-modal-foot">'
    +   '<button type="button" class="btn btn-sec" data-close>Annuler</button>'
    +   '<button type="button" class="btn" id="edit-alert-save">Enregistrer</button>'
    + '</div></div>';
  document.body.appendChild(overlay);
  const close = () => overlay.remove();
  overlay.querySelectorAll('[data-close]').forEach(el => el.addEventListener('click', close));
  overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });
  _afOnTriggerChange();
  document.getElementById('edit-alert-save').addEventListener('click', async () => {
    const body = {};
    if (!isAuto) {
      const nom = (document.getElementById('af-nom').value || '').trim();
      if (!nom) { toast('Titre obligatoire', true); return; }
      body.nom = nom;
    }
    const params = _afReadParams();
    if (!params) return;
    body.params = params;
    try {
      await api('/api/maintenance/alerts/' + id, { method: 'PATCH', body: JSON.stringify(body) });
      toast('Alerte mise à jour');
      close();
      await loadAlerts();
    } catch (e) { toast(e && e.message ? e.message : 'Erreur', true); }
  });
  setTimeout(() => (document.getElementById('af-nom') || document.getElementById('af-trigger-type'))?.focus(), 30);
}

async function deleteUpdate(id) {
  const u = _updatesData.find(x => x.id === id);
  if (!u) return;
  if (u.nb_ack > 0) { toast('Impossible de supprimer une annonce déjà lue', true); return; }
  if (!confirm('Supprimer définitivement cette annonce ?')) return;
  try {
    await api('/api/updates/' + id, { method: 'DELETE' });
    toast('Annonce supprimée ✅');
    await loadUpdates();
  } catch(e) { toast(e.message, true); }
}

// ── Audit log ─────────────────────────────────────────────
let _auditOffset = 0;
const _auditLimit = 50;
let _auditSearchTimer = null;

function debouncedAuditSearch() {
  clearTimeout(_auditSearchTimer);
  _auditSearchTimer = setTimeout(() => { _auditOffset = 0; loadAuditLogs(); }, 300);
}

const ACTION_COLORS = {
  CREATE:   'var(--ok)',
  UPDATE:   'var(--accent)',
  DELETE:   'var(--danger)',
  CLOSE:    'var(--muted)',
  VALIDATE: 'var(--warn)',
  REORDER:  'var(--text2)',
  SEARCH:   'var(--accent)',
  LOGIN:    'var(--text2)',
  LOGOUT:   'var(--muted)',
};
const ACTION_LABELS = {
  CREATE:'Création', UPDATE:'Modification', DELETE:'Suppression',
  CLOSE:'Clôture', VALIDATE:'Validation', REORDER:'Réorganisation',
  SEARCH:'Recherche', LOGIN:'Connexion', LOGOUT:'Déconnexion',
};
const MODULE_LABELS = {
  planning:'Planning', fabrication:'Fabrication', stock:'Stock',
  expe:'Expéditions', rh:'RH', settings:'Paramètres', auth:'Auth',
  portal:'Portail',
};

async function loadAuditLogs() {
  const wrap = document.getElementById('audit-table-wrap');
  const pag  = document.getElementById('audit-pagination');
  const search = (document.getElementById('audit-search')?.value || '').trim();
  const module = document.getElementById('audit-filter-module')?.value || '';
  const action = document.getElementById('audit-filter-action')?.value || '';

  wrap.innerHTML = '<div style="color:var(--muted);font-size:13px;padding:20px 0">Chargement…</div>';

  const params = new URLSearchParams({
    limit: _auditLimit,
    offset: _auditOffset,
    ...(module && { module }),
    ...(action && { action }),
    ...(search && { search }),
  });

  const res = await fetch('/api/settings/audit?' + params, { credentials: 'include' });
  if (!res.ok) { wrap.innerHTML = '<div style="color:var(--danger);font-size:13px">Erreur de chargement.</div>'; return; }
  const { total, logs } = await res.json();

  if (!logs.length) {
    wrap.innerHTML = '<div style="color:var(--muted);font-size:13px;padding:20px 0">Aucune action enregistrée.</div>';
    pag.innerHTML = '';
    return;
  }

  const rows = logs.map(l => {
    const color = ACTION_COLORS[l.action] || 'var(--text2)';
    const actionLabel = ACTION_LABELS[l.action] || l.action;
    const moduleLabel = MODULE_LABELS[l.module] || l.module;
    const dt = l.created_at_display != null && l.created_at_display !== ''
      ? l.created_at_display
      : (l.created_at ? l.created_at.replace('T', ' ').slice(0, 16) : '—');
    const detailHtml = l.detail
      ? `<span style="color:var(--muted);font-size:11px;display:block;margin-top:2px;
                      white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:260px"
               title="${escAttr(l.detail)}">${esc(l.detail)}</span>` : '';
    return `<tr>
      <td style="white-space:nowrap;font-family:monospace;font-size:11px;color:var(--muted)">${dt}</td>
      <td style="font-size:13px;font-weight:600;color:var(--text)">${esc(l.user_nom||'—')}</td>
      <td><span style="font-size:10px;font-weight:700;color:var(--bg);background:${color};
                       padding:2px 7px;border-radius:20px;text-transform:uppercase">${actionLabel}</span></td>
      <td><span style="font-size:11px;color:var(--text2);background:var(--accent-bg);
                       padding:2px 6px;border-radius:6px">${moduleLabel}</span></td>
      <td style="font-size:13px;color:var(--text);max-width:280px">
        ${esc(l.objet||'—')}${detailHtml}
      </td>
    </tr>`;
  }).join('');

  wrap.innerHTML = `
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <thead>
        <tr style="border-bottom:2px solid var(--border)">
          <th style="text-align:left;padding:8px 12px 8px 0;font-size:11px;font-weight:700;
                     color:var(--muted);text-transform:uppercase;letter-spacing:.5px;white-space:nowrap">Date</th>
          <th style="text-align:left;padding:8px 12px;font-size:11px;font-weight:700;
                     color:var(--muted);text-transform:uppercase;letter-spacing:.5px">Utilisateur</th>
          <th style="text-align:left;padding:8px 12px;font-size:11px;font-weight:700;
                     color:var(--muted);text-transform:uppercase;letter-spacing:.5px">Action</th>
          <th style="text-align:left;padding:8px 12px;font-size:11px;font-weight:700;
                     color:var(--muted);text-transform:uppercase;letter-spacing:.5px">Module</th>
          <th style="text-align:left;padding:8px 12px;font-size:11px;font-weight:700;
                     color:var(--muted);text-transform:uppercase;letter-spacing:.5px">Objet</th>
        </tr>
      </thead>
      <tbody>
        ${rows.replace(/<tr>/g, '<tr style="border-bottom:1px solid var(--border)">')}
      </tbody>
    </table>`;

  const from = _auditOffset + 1;
  const to   = Math.min(_auditOffset + logs.length, total);
  pag.innerHTML = `
    <span>${from}–${to} sur ${total} actions</span>
    <div style="display:flex;gap:6px">
      <button type="button" onclick="_auditOffset=Math.max(0,_auditOffset-_auditLimit);loadAuditLogs()"
              ${_auditOffset === 0 ? 'disabled' : ''}
              style="background:var(--card);border:1px solid var(--border);border-radius:6px;
                     padding:4px 10px;color:var(--text2);cursor:pointer;font-family:inherit;font-size:12px">
        ← Précédent
      </button>
      <button type="button" onclick="_auditOffset=Math.min(total-_auditLimit,_auditOffset+_auditLimit);loadAuditLogs()"
              ${to >= total ? 'disabled' : ''}
              style="background:var(--card);border:1px solid var(--border);border-radius:6px;
                     padding:4px 10px;color:var(--text2);cursor:pointer;font-family:inherit;font-size:12px">
        Suivant →
      </button>
    </div>`;
}

// ── Registre FSC ─────────────────────────────────────────────
const FSC_CLAIM_LABELS = {
  non_fsc: 'Non FSC',
  fsc_100: 'FSC 100%',
  fsc_mix_credit: 'FSC Mix Credit',
  fsc_mix: 'FSC Mix',
  fsc_recycled: 'FSC Recycled',
};
const FSC_STATUT_LABELS = {
  attente: 'En attente',
  en_cours: 'En cours',
  termine: 'Terminé',
};
let _fscDatesInit = false;

function initFscDates() {
  const duEl = document.getElementById('fsc-du');
  const auEl = document.getElementById('fsc-au');
  if (!duEl || !auEl) return;
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  if (!duEl.value) duEl.value = `${y}-01-01`;
  if (!auEl.value) auEl.value = `${y}-${m}-${d}`;
}

function initFscPanel() {
  initFscDates();
  if (!_fscDatesInit) {
    _fscDatesInit = true;
  }
  loadFscStats();
  loadFscRegistre();
}

async function renderSettingsDashboards() {
  const root = document.getElementById('settings-tab-content');
  if (!root) return;
  root.innerHTML = '<div style="padding:20px;color:var(--muted);font-size:13px">Chargement…</div>';

  let dashboards = [];
  try {
    const r = await fetch('/api/dashboards/admin', { credentials: 'include' });
    if (r.ok) dashboards = await r.json();
  } catch(e) {}

  const WIDGET_TYPES = [
    { value: 'stock_alerts',     label: 'Alertes stock matières premières' },
    { value: 'planning_summary', label: 'Résumé planning production' },
    { value: 'expe_today',       label: 'Départs expédition du jour' },
  ];
  const CATEGORIES_MP = ['mandrin','palette','adhesif','carton'];

  function renderList() {
    const listEl = document.createElement('div');
    listEl.style.cssText = 'display:flex;flex-direction:column;gap:10px;margin-top:16px';

    if (!dashboards.length) {
      listEl.innerHTML = '<div style="color:var(--muted);font-size:13px;text-align:center;padding:24px 0">Aucun tableau de bord créé.</div>';
    } else {
      dashboards.forEach(d => {
        const card = document.createElement('div');
        card.style.cssText = 'background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px 16px;display:flex;align-items:center;gap:12px';

        const typeInfo = WIDGET_TYPES.find(t => t.value === d.widget_type) || { label: d.widget_type };
        const statusBadge = d.actif
          ? '<span style="font-size:11px;font-weight:700;padding:2px 8px;border-radius:6px;background:rgba(52,211,153,.15);color:var(--success)">Actif</span>'
          : '<span style="font-size:11px;font-weight:700;padding:2px 8px;border-radius:6px;background:var(--accent-bg);color:var(--muted)">Inactif</span>';

        card.innerHTML = `
          <div style="flex:1;min-width:0">
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
              <span style="font-size:14px;font-weight:700;color:var(--text)">${escHtml(d.titre)}</span>
              ${statusBadge}
            </div>
            <div style="font-size:12px;color:var(--muted);margin-top:4px">${escHtml(typeInfo.label)}</div>
            ${d.description ? `<div style="font-size:12px;color:var(--text2);margin-top:2px">${escHtml(d.description)}</div>` : ''}
          </div>
          <div style="display:flex;gap:8px;flex-shrink:0">
            <button class="btn btn-ghost" style="padding:6px 12px;font-size:12px" data-edit="${d.id}">Modifier</button>
            <button class="btn btn-ghost" style="padding:6px 12px;font-size:12px;color:var(--danger)" data-del="${d.id}">Supprimer</button>
          </div>`;

        card.querySelector('[data-edit]').addEventListener('click', () => openDashboardModal(d));
        card.querySelector('[data-del]').addEventListener('click', () => deleteDashboard(d.id, d.titre));
        listEl.appendChild(card);
      });
    }
    return listEl;
  }

  async function deleteDashboard(id, titre) {
    if (!confirm(`Supprimer le tableau de bord "${titre}" ? Il sera retiré du portail de tous les utilisateurs.`)) return;
    try {
      const r = await fetch(`/api/dashboards/admin/${id}`, { method: 'DELETE', credentials: 'include' });
      if (r.ok) {
        dashboards = dashboards.filter(d => d.id !== id);
        rebuildPage();
        toast('Tableau de bord supprimé.', false);
      } else {
        toast('Erreur lors de la suppression.', true);
      }
    } catch(e) { toast('Erreur réseau.', true); }
  }

  function openDashboardModal(existing) {
    const isEdit = !!existing;
    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;inset:0;z-index:400;background:rgba(0,0,0,.55);backdrop-filter:blur(3px);display:flex;align-items:center;justify-content:center';
    overlay.addEventListener('click', e => { if(e.target===overlay) overlay.remove(); });

    const modal = document.createElement('div');
    modal.style.cssText = 'background:var(--card);border:1px solid var(--border);border-radius:16px;width:420px;max-width:92vw;box-shadow:0 16px 48px rgba(0,0,0,.4);display:flex;flex-direction:column;overflow:hidden';

    const head = document.createElement('div');
    head.style.cssText = 'display:flex;align-items:center;justify-content:space-between;padding:16px 20px;border-bottom:1px solid var(--border)';
    head.innerHTML = `<span style="font-size:15px;font-weight:700;color:var(--text)">${isEdit ? 'Modifier' : 'Nouveau tableau de bord'}</span>`;
    const btnX = document.createElement('button');
    btnX.className = 'db-panel-btn';
    btnX.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
    btnX.addEventListener('click', () => overlay.remove());
    head.appendChild(btnX);

    const body = document.createElement('div');
    body.style.cssText = 'padding:20px;display:flex;flex-direction:column;gap:14px';

    // Champ titre
    const fTitre = document.createElement('div');
    fTitre.innerHTML = `<label style="font-size:12px;font-weight:600;color:var(--text);text-transform:uppercase;letter-spacing:.5px;display:block;margin-bottom:6px">Titre</label>
      <input id="db-f-titre" type="text" placeholder="Ex: Stocks à réapprovisionner" value="${escAttr(existing?.titre||'')}" style="width:100%;box-sizing:border-box;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px 14px;color:var(--text);font-size:14px">`;

    // Champ description
    const fDesc = document.createElement('div');
    fDesc.innerHTML = `<label style="font-size:12px;font-weight:600;color:var(--text);text-transform:uppercase;letter-spacing:.5px;display:block;margin-bottom:6px">Description <span style="color:var(--muted);font-weight:400">(optionnel)</span></label>
      <input id="db-f-desc" type="text" placeholder="Ex: Mandrins, cartons, palettes et adhésif" value="${escAttr(existing?.description||'')}" style="width:100%;box-sizing:border-box;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px 14px;color:var(--text);font-size:14px">`;

    // Champ type (désactivé en édition)
    const fType = document.createElement('div');
    const typeOpts = WIDGET_TYPES.map(t =>
      `<option value="${t.value}" ${(existing?.widget_type===t.value||(!existing&&t.value==='stock_alerts'))?'selected':''}>${t.label}</option>` 
    ).join('');
    fType.innerHTML = `<label style="font-size:12px;font-weight:600;color:var(--text);text-transform:uppercase;letter-spacing:.5px;display:block;margin-bottom:6px">Type de widget</label>
      <select id="db-f-type" ${isEdit?'disabled':''} style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px 14px;color:var(--text);font-size:14px">${typeOpts}</select>
      ${isEdit?'<div style="font-size:11px;color:var(--muted);margin-top:4px">Le type ne peut pas être modifié après création.</div>':''}`;

    // Config dynamique selon le type (stock_alerts → catégories)
    const fConfig = document.createElement('div');
    fConfig.id = 'db-f-config';

    function renderConfigFields(type, currentConfig) {
      fConfig.innerHTML = '';
      if (type === 'stock_alerts') {
        const cats = currentConfig?.categories || [];
        fConfig.innerHTML = `<div>
          <label style="font-size:12px;font-weight:600;color:var(--text);text-transform:uppercase;letter-spacing:.5px;display:block;margin-bottom:8px">Catégories affichées</label>
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            ${CATEGORIES_MP.map(c => `
              <label style="display:flex;align-items:center;gap:6px;font-size:13px;color:var(--text2);cursor:pointer;padding:6px 10px;border-radius:8px;border:1px solid var(--border);background:var(--bg)">
                <input type="checkbox" value="${c}" ${cats.includes(c)||!cats.length?'checked':''} style="accent-color:var(--accent)">
                ${c.charAt(0).toUpperCase()+c.slice(1)}
              </label>`).join('')}
          </div>
          <div style="font-size:11px;color:var(--muted);margin-top:6px">Si aucune sélectionnée, toutes les catégories sont affichées.</div>
        </div>`;
      }
      // Pour planning_summary et expe_today : pas de config supplémentaire pour l'instant
    }

    const initType = existing?.widget_type || 'stock_alerts';
    renderConfigFields(initType, existing?.config_json || {});

    fType.querySelector('select')?.addEventListener('change', (e) => {
      renderConfigFields(e.target.value, {});
    });

    // Champ actif
    const fActif = document.createElement('div');
    fActif.innerHTML = `<label style="display:flex;align-items:center;gap:10px;cursor:pointer;font-size:13px;color:var(--text2)">
      <input id="db-f-actif" type="checkbox" ${(existing?.actif!==false)?'checked':''} style="accent-color:var(--accent);width:16px;height:16px">
      Dashboard actif (visible par les utilisateurs)
    </label>`;

    // Bouton soumettre
    const footer = document.createElement('div');
    footer.style.cssText = 'padding:0 20px 20px;display:flex;justify-content:flex-end;gap:10px';
    const btnCancel = document.createElement('button');
    btnCancel.className = 'btn btn-ghost';
    btnCancel.textContent = 'Annuler';
    btnCancel.addEventListener('click', () => overlay.remove());

    const btnSave = document.createElement('button');
    btnSave.className = 'btn btn-accent';
    btnSave.textContent = isEdit ? 'Enregistrer' : 'Créer';
    btnSave.addEventListener('click', async () => {
      const titre = document.getElementById('db-f-titre')?.value?.trim();
      if (!titre) { toast('Le titre est requis.', true); return; }
      const widget_type = document.getElementById('db-f-type')?.value || initType;
      const desc = document.getElementById('db-f-desc')?.value?.trim() || '';
      const actif = document.getElementById('db-f-actif')?.checked !== false;

      // Collecter config
      let config_json = {};
      if (widget_type === 'stock_alerts') {
        const checked = [...document.querySelectorAll('#db-f-config input[type=checkbox]:checked')].map(el => el.value);
        if (checked.length && checked.length < CATEGORIES_MP.length) {
          config_json.categories = checked;
        }
      }

      btnSave.disabled = true;
      btnSave.textContent = isEdit ? 'Enregistrement…' : 'Création…';

      try {
        let r;
        if (isEdit) {
          r = await fetch(`/api/dashboards/admin/${existing.id}`, {
            method: 'PATCH', credentials: 'include',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ titre, description: desc, config_json, actif }),
          });
        } else {
          r = await fetch('/api/dashboards/admin', {
            method: 'POST', credentials: 'include',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ titre, description: desc, widget_type, config_json, actif }),
          });
        }
        if (r.ok) {
          overlay.remove();
          // Recharger la liste
          const r2 = await fetch('/api/dashboards/admin', { credentials: 'include' });
          if (r2.ok) dashboards = await r2.json();
          rebuildPage();
          toast(isEdit ? 'Tableau de bord modifié.' : 'Tableau de bord créé.', false);
        } else {
          const err = await r.json().catch(() => ({}));
          toast(err.detail || 'Erreur lors de la sauvegarde.', true);
          btnSave.disabled = false;
          btnSave.textContent = isEdit ? 'Enregistrer' : 'Créer';
        }
      } catch(e) {
        toast('Erreur réseau.', true);
        btnSave.disabled = false;
        btnSave.textContent = isEdit ? 'Enregistrer' : 'Créer';
      }
    });

    body.appendChild(fTitre);
    body.appendChild(fDesc);
    body.appendChild(fType);
    body.appendChild(fConfig);
    body.appendChild(fActif);
    footer.appendChild(btnCancel);
    footer.appendChild(btnSave);
    modal.appendChild(head);
    modal.appendChild(body);
    modal.appendChild(footer);
    overlay.appendChild(modal);
    document.body.appendChild(overlay);
    requestAnimationFrame(() => document.getElementById('db-f-titre')?.focus());
  }

  function rebuildPage() {
    root.innerHTML = '';
    buildPage();
  }

  function buildPage() {
    const wrap = document.createElement('div');
    wrap.style.cssText = 'max-width:760px;margin:0 auto;padding:0 0 40px';

    const topRow = document.createElement('div');
    topRow.style.cssText = 'display:flex;align-items:center;justify-content:space-between;margin-bottom:4px';
    const h = document.createElement('div');
    h.innerHTML = '<div style="font-size:16px;font-weight:700;color:var(--text)">Tableaux de bord</div><div style="font-size:13px;color:var(--muted);margin-top:4px">Créez des tableaux de bord que les utilisateurs peuvent ajouter à leur portail.</div>';
    const btnNew = document.createElement('button');
    btnNew.className = 'btn btn-accent';
    btnNew.innerHTML = '+ Nouveau';
    btnNew.style.cssText = 'flex-shrink:0;padding:8px 16px;font-size:13px';
    btnNew.addEventListener('click', () => openDashboardModal(null));
    topRow.appendChild(h);
    topRow.appendChild(btnNew);
    wrap.appendChild(topRow);
    wrap.appendChild(renderList());
    root.appendChild(wrap);
  }

  buildPage();
}

function fscClaimBadgeHtml(claim) {
  const c = (claim || 'non_fsc').trim();
  const label = FSC_CLAIM_LABELS[c] || esc(c);
  let bg = 'rgba(148,163,184,.12)';
  let color = 'var(--muted)';
  if (c === 'fsc_100') {
    bg = 'rgba(52,211,153,.12)';
    color = 'var(--ok)';
  } else if (c === 'fsc_recycled' || c.startsWith('fsc_mix')) {
    bg = 'rgba(34,211,238,.12)';
    color = 'var(--accent)';
  }
  return `<span class="fsc-claim-badge" style="background:${bg};color:${color}">${esc(label)}</span>`;
}

async function loadFscStats() {
  const grid = document.getElementById('fsc-kpi-grid');
  if (!grid) return;
  try {
    const d = await api('/api/fsc/stats');
    if (!d) return;
    const alertBadge = (d.alertes_ecart_total || 0) > 0 ? 'danger' : 'muted';
    grid.innerHTML = `
      <div class="fsc-kpi-card">
        <div class="fsc-kpi-label">Réceptions FSC ce mois</div>
        <div class="fsc-kpi-val">${esc(String(d.recep_fsc_ce_mois ?? 0))}</div>
        <span class="fsc-kpi-badge accent">Mois en cours</span>
      </div>
      <div class="fsc-kpi-card">
        <div class="fsc-kpi-label">Dossiers FSC actifs</div>
        <div class="fsc-kpi-val">${esc(String(d.dossiers_fsc_actifs ?? 0))}</div>
        <span class="fsc-kpi-badge accent">Non terminés</span>
      </div>
      <div class="fsc-kpi-card">
        <div class="fsc-kpi-label">Dossiers FSC terminés</div>
        <div class="fsc-kpi-val">${esc(String(d.dossiers_termines_fsc ?? 0))}</div>
        <span class="fsc-kpi-badge ok">Historique</span>
      </div>
      <div class="fsc-kpi-card">
        <div class="fsc-kpi-label">Alertes écart total</div>
        <div class="fsc-kpi-val">${esc(String(d.alertes_ecart_total ?? 0))}</div>
        <span class="fsc-kpi-badge ${alertBadge}">Confirmées</span>
      </div>`;
  } catch (e) {
    grid.innerHTML = `<p style="color:var(--danger);font-size:13px">${esc(e.message || 'Erreur chargement KPIs')}</p>`;
  }
}

function renderFscReceptions(rows) {
  const wrap = document.getElementById('fsc-recep-wrap');
  if (!wrap) return;
  if (!rows.length) {
    wrap.innerHTML = '<p style="color:var(--muted);font-size:13px;padding:12px 0">Aucune réception FSC sur la période.</p>';
    return;
  }
  const trs = rows.map(r => {
    const dt = (r.created_at || '').replace('T', ' ').slice(0, 10);
    return `<tr>
      <td style="font-family:monospace;font-size:11px;color:var(--muted)">${esc(dt)}</td>
      <td>${esc(r.fournisseur || '—')}</td>
      <td style="font-family:monospace;font-size:11px">${esc(r.fournisseur_licence || '—')}</td>
      <td>${esc(r.certificat_fsc || '—')}</td>
      <td>${fscClaimBadgeHtml(r.fsc_type_claim)}</td>
      <td style="text-align:center">${esc(String(r.nb_bobines ?? 0))}</td>
      <td>${esc(r.created_by_name || '—')}</td>
    </tr>`;
  }).join('');
  wrap.innerHTML = `<table>
    <thead><tr>
      <th>Date</th><th>Fournisseur</th><th>Licence FSC</th><th>Certificat</th>
      <th>Type claim</th><th>Nb bobines</th><th>Réceptionné par</th>
    </tr></thead>
    <tbody>${trs}</tbody>
  </table>`;
}

function renderFscDossiers(rows) {
  const wrap = document.getElementById('fsc-dossiers-wrap');
  if (!wrap) return;
  if (!rows.length) {
    wrap.innerHTML = '<p style="color:var(--muted);font-size:13px;padding:12px 0">Aucun dossier FSC sur la période.</p>';
    return;
  }
  const trs = rows.map(d => {
    const alertes = Number(d.nb_alertes) || 0;
    const rowCls = alertes > 0 ? ' class="fsc-row-alert"' : '';
    const statut = FSC_STATUT_LABELS[d.statut] || d.statut || '—';
    return `<tr${rowCls}>
      <td style="font-weight:700;color:var(--accent)">${esc(d.reference || '—')}</td>
      <td>${esc(d.client || '—')}</td>
      <td>${fscClaimBadgeHtml(d.fsc_type_requis)}</td>
      <td>${esc(statut)}</td>
      <td style="font-family:monospace;font-size:11px">${esc(d.date_livraison || '—')}</td>
      <td style="text-align:center">${esc(String(d.nb_bobines_scannees ?? 0))}</td>
      <td style="text-align:center;font-weight:700;color:${alertes > 0 ? 'var(--danger)' : 'var(--muted)'}">${esc(String(alertes))}</td>
    </tr>`;
  }).join('');
  wrap.innerHTML = `<table>
    <thead><tr>
      <th>Référence</th><th>Client</th><th>Type FSC requis</th><th>Statut</th>
      <th>Date livraison</th><th>Bobines scannées</th><th>Alertes</th>
    </tr></thead>
    <tbody>${trs}</tbody>
  </table>`;
}

async function loadFscRegistre() {
  const du = document.getElementById('fsc-du')?.value || '';
  const au = document.getElementById('fsc-au')?.value || '';
  const recepWrap = document.getElementById('fsc-recep-wrap');
  const dossWrap = document.getElementById('fsc-dossiers-wrap');
  if (recepWrap) recepWrap.innerHTML = '<p style="color:var(--muted);font-size:13px;padding:12px 0">Chargement…</p>';
  if (dossWrap) dossWrap.innerHTML = '<p style="color:var(--muted);font-size:13px;padding:12px 0">Chargement…</p>';
  try {
    const params = new URLSearchParams();
    if (du) params.set('du', du);
    if (au) params.set('au', au);
    const d = await api('/api/fsc/registre?' + params.toString());
    if (!d) return;
    renderFscReceptions(d.receptions || []);
    renderFscDossiers(d.dossiers || []);
  } catch (e) {
    const msg = `<p style="color:var(--danger);font-size:13px;padding:12px 0">${esc(e.message || 'Erreur chargement')}</p>`;
    if (recepWrap) recepWrap.innerHTML = msg;
    if (dossWrap) dossWrap.innerHTML = msg;
  }
}

function exportFscCsv() {
  const du = document.getElementById('fsc-du')?.value || '';
  const au = document.getElementById('fsc-au')?.value || '';
  const params = new URLSearchParams({ format: 'csv' });
  if (du) params.set('du', du);
  if (au) params.set('au', au);
  window.location.href = '/api/fsc/registre?' + params.toString();
}

// ── Clés API ──────────────────────────────────────────────────────
async function loadApiKeys() {
  const res = await fetch('/api/settings/api-keys', {credentials:'include'});
  const data = await res.json();
  const list = document.getElementById('ak-list');
  if (!data.keys || data.keys.length === 0) {
    list.innerHTML = '<div style="padding:24px;text-align:center;color:var(--muted);font-size:13px">Aucune clé créée.</div>';
    return;
  }
  list.innerHTML = data.keys.map(k => `
    <div style="display:flex;align-items:center;gap:14px;padding:12px 20px;border-bottom:1px solid var(--border);flex-wrap:wrap">
      <div style="flex:1;min-width:160px">
        <div style="font-size:13px;font-weight:600;color:var(--text)">${escHtml(k.name)}</div>
        <div style="font-size:11px;color:var(--muted);margin-top:2px;font-family:monospace">${escHtml(k.key_prefix)}…</div>
      </div>
      <div style="font-size:11px;color:var(--muted)">${escHtml(k.scopes||'')}</div>
      <div style="font-size:11px;color:var(--muted)">${k.last_used_at ? 'Dernière utilisation : '+escHtml(k.last_used_at.replace('T',' ').slice(0,16)) : 'Jamais utilisée'}</div>
      <div>
        <span style="display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;${k.is_active ? 'background:rgba(52,211,153,.15);color:var(--ok)' : 'background:rgba(248,113,113,.15);color:var(--danger)'}">
          ${k.is_active ? 'Active' : 'Révoquée'}
        </span>
      </div>
      <div style="display:flex;gap:6px">
        ${k.is_active ? `<button class="btn btn-ghost" style="padding:6px 12px;font-size:12px;border:1px solid var(--border)" onclick="revokeApiKey(${k.id})">Révoquer</button>` : ''}
        <button class="btn btn-ghost" style="padding:6px 12px;font-size:12px;border:1px solid rgba(248,113,113,.4);color:var(--danger)" onclick="deleteApiKey(${k.id})">Supprimer</button>
      </div>
    </div>
  `).join('');
}

async function createApiKey() {
  const name = document.getElementById('ak-name').value.trim();
  if (!name) { toast('Donnez un nom à cette clé.', true); return; }
  const res = await fetch('/api/settings/api-keys', {
    method:'POST', credentials:'include',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({name})
  });
  if (!res.ok) { toast('Erreur lors de la création.', true); return; }
  const data = await res.json();
  document.getElementById('ak-name').value = '';
  document.getElementById('ak-reveal-value').textContent = data.key;
  document.getElementById('ak-reveal').style.display = 'block';
  toast('Clé créée. Copiez-la maintenant.', false);
  loadApiKeys();
}

// ── Sidebar sections collapse ──
(function initNavGroups() {
  // Groupes principaux
  document.querySelectorAll('.nav-group-label').forEach(function(label) {
    label.addEventListener('click', function() {
      const collapsed = label.classList.toggle('ngl-collapsed');
      // Parcourir les frères jusqu'au prochain nav-group-label
      let el = label.nextElementSibling;
      while (el && !el.classList.contains('nav-group-label')) {
        if (collapsed) {
          el.style.display = 'none';
        } else {
          el.style.display = '';
        }
        el = el.nextElementSibling;
      }
      // Re-appliquer l'état des sous-groupes (qu'on aurait pu écraser en expandant)
      if (!collapsed) {
        let el2 = label.nextElementSibling;
        let subCollapsed = null;
        while (el2 && !el2.classList.contains('nav-group-label')) {
          if (el2.classList.contains('nav-subgroup-label')) {
            subCollapsed = el2.classList.contains('nsl-collapsed');
          } else if (subCollapsed && el2.classList.contains('nav-btn')) {
            el2.style.display = 'none';
          }
          el2 = el2.nextElementSibling;
        }
      }
    });
  });
  // Sous-groupes (à l'intérieur d'un groupe principal)
  document.querySelectorAll('.nav-subgroup-label').forEach(function(label) {
    label.addEventListener('click', function(ev) {
      ev.stopPropagation();
      const collapsed = label.classList.toggle('nsl-collapsed');
      let el = label.nextElementSibling;
      while (el && !el.classList.contains('nav-subgroup-label') && !el.classList.contains('nav-group-label')) {
        if (el.classList.contains('nav-btn')) {
          el.style.display = collapsed ? 'none' : '';
        }
        el = el.nextElementSibling;
      }
    });
  });
})();

function copyApiKey() {
  const val = document.getElementById('ak-reveal-value').textContent;
  navigator.clipboard.writeText(val).then(() => toast('Clé copiée.', false));
}

async function revokeApiKey(id) {
  if (!confirm('Révoquer cette clé ? Le pont Access ne pourra plus s\'authentifier.')) return;
  const res = await fetch(`/api/settings/api-keys/${id}/revoke`, {method:'PATCH', credentials:'include'});
  if (!res.ok) { toast('Erreur lors de la révocation.', true); return; }
  toast('Clé révoquée.', false);
  loadApiKeys();
}

async function deleteApiKey(id) {
  if (!confirm('Supprimer définitivement cette clé ?')) return;
  const res = await fetch(`/api/settings/api-keys/${id}`, {method:'DELETE', credentials:'include'});
  if (!res.ok) { toast('Erreur lors de la suppression.', true); return; }
  toast('Clé supprimée.', false);
  loadApiKeys();
}

// ──────────────────────────────────────────────────
// Emplacements
// ──────────────────────────────────────────────────
let _emplData = [];
let _emplReady = false;

// ── Laizes matières ────────────────────────────────────────────
let _laizesReady = false;
let _laizesList = [];

async function initLaizesPanel() {
  if (!_laizesReady) {
    _laizesReady = true;
    const form = document.getElementById('laizes-add-form');
    if (form) {
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const mm = parseFloat(document.getElementById('laizes-add-mm').value);
        const label = document.getElementById('laizes-add-label').value.trim();
        const ordre = parseInt(document.getElementById('laizes-add-ordre').value, 10) || 0;
        if (!mm || mm <= 0) { alert('Valeur (mm) invalide.'); return; }
        try {
          const r = await fetch('/api/admin/mp_laizes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ valeur_mm: mm, label: label || null, ordre }),
          });
          if (!r.ok) {
            const err = await r.json().catch(() => ({ detail: 'erreur' }));
            alert('Erreur : ' + (err.detail || r.statusText));
            return;
          }
          document.getElementById('laizes-add-mm').value = '';
          document.getElementById('laizes-add-label').value = '';
          document.getElementById('laizes-add-ordre').value = '0';
          await loadLaizesList();
        } catch (e) { alert('Erreur : ' + e.message); }
      });
    }
  }
  await loadLaizesList();
}

async function loadLaizesList() {
  try {
    const r = await fetch('/api/admin/mp_laizes?all=1', { credentials: 'include' });
    if (!r.ok) throw new Error('chargement impossible');
    _laizesList = await r.json();
  } catch (e) {
    _laizesList = [];
  }
  renderLaizesList();
}

function renderLaizesList() {
  const wrap = document.getElementById('laizes-list');
  const empty = document.getElementById('laizes-empty');
  if (!wrap) return;
  wrap.innerHTML = '';
  if (!_laizesList.length) {
    if (empty) empty.style.display = '';
    return;
  }
  if (empty) empty.style.display = 'none';
  _laizesList.forEach(l => {
    const row = document.createElement('div');
    row.style.cssText = 'display:flex;align-items:center;gap:12px;padding:10px 14px;border:1px solid var(--border);border-radius:10px;background:var(--card)';
    if (!l.actif) row.style.opacity = '0.5';
    const main = document.createElement('div');
    main.style.cssText = 'flex:1;display:flex;align-items:center;gap:10px';
    const lab = document.createElement('div');
    lab.style.cssText = 'font-size:14px;font-weight:700;color:var(--text);min-width:80px';
    lab.textContent = l.label;
    const val = document.createElement('div');
    val.style.cssText = 'font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums';
    val.textContent = l.valeur_mm + ' mm · ordre ' + l.ordre;
    main.append(lab, val);
    row.appendChild(main);
    const actions = document.createElement('div');
    actions.style.cssText = 'display:flex;gap:6px';
    const toggleBtn = document.createElement('button');
    toggleBtn.type = 'button';
    toggleBtn.className = 'btn btn-sec btn-sm';
    toggleBtn.textContent = l.actif ? 'Désactiver' : 'Réactiver';
    toggleBtn.addEventListener('click', async () => {
      try {
        const r = await fetch('/api/admin/mp_laizes/' + l.id, {
          method: 'PUT', credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ actif: l.actif ? false : true }),
        });
        if (!r.ok) { const err = await r.json().catch(() => ({})); alert(err.detail || 'erreur'); return; }
        await loadLaizesList();
      } catch (e) { alert(e.message); }
    });
    const delBtn = document.createElement('button');
    delBtn.type = 'button';
    delBtn.className = 'btn btn-sec btn-sm';
    delBtn.style.color = 'var(--danger)';
    delBtn.textContent = 'Supprimer';
    delBtn.addEventListener('click', async () => {
      if (!confirm('Supprimer la laize ' + l.label + ' ?')) return;
      try {
        const r = await fetch('/api/admin/mp_laizes/' + l.id, { method: 'DELETE', credentials: 'include' });
        if (!r.ok) { const err = await r.json().catch(() => ({})); alert(err.detail || 'erreur'); return; }
        await loadLaizesList();
      } catch (e) { alert(e.message); }
    });
    actions.append(toggleBtn, delBtn);
    row.appendChild(actions);
    wrap.appendChild(row);
  });
}

// ── Importations (Logistique) ─────────────────────────────────
let _impReady = false;
async function initImportationsPanel() {
  const loading = document.getElementById('importations-loading');
  const form = document.getElementById('importations-form');
  const errBox = document.getElementById('importations-error');
  const inpFull = document.getElementById('imp-qte-full');
  const inpHalf = document.getElementById('imp-qte-half');
  const saveBtn = document.getElementById('imp-save-btn');
  const status = document.getElementById('imp-status');
  if (!form || !inpFull || !inpHalf) return;

  const showError = (msg) => {
    if (loading) loading.style.display = 'none';
    form.style.display = 'none';
    if (errBox) { errBox.style.display = 'block'; errBox.textContent = msg; }
  };

  try {
    const r = await fetch('/api/pricing/settings', { credentials: 'include' });
    if (r.status === 403) { showError('Accès réservé à la Direction et au super admin.'); return; }
    if (!r.ok) { showError('Erreur de chargement (' + r.status + ').'); return; }
    const data = await r.json();
    inpFull.value = String(Number(data.logistique_qte_m2_container_complet || 0));
    inpHalf.value = String(Number(data.logistique_qte_m2_demi_container || 0));
    if (loading) loading.style.display = 'none';
    if (errBox) errBox.style.display = 'none';
    form.style.display = 'flex';
  } catch (e) {
    showError('Erreur de chargement : ' + (e?.message || 'inconnue'));
    return;
  }

  if (_impReady) return;
  _impReady = true;

  form.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const full = parseFloat(inpFull.value || '0');
    const half = parseFloat(inpHalf.value || '0');
    if (isNaN(full) || full < 0 || isNaN(half) || half < 0) {
      status.textContent = 'Valeurs invalides.';
      status.style.color = 'var(--danger)';
      return;
    }
    saveBtn.disabled = true;
    status.textContent = 'Enregistrement…';
    status.style.color = 'var(--muted)';
    try {
      const r = await fetch('/api/pricing/settings', {
        method: 'PATCH',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          logistique_qte_m2_container_complet: full,
          logistique_qte_m2_demi_container: half,
        }),
      });
      if (!r.ok) {
        const j = await r.json().catch(() => ({}));
        throw new Error(j.detail || ('HTTP ' + r.status));
      }
      status.textContent = 'Enregistré.';
      status.style.color = 'var(--ok, #34d399)';
      setTimeout(() => { status.textContent = ''; }, 2500);
    } catch (e) {
      status.textContent = 'Erreur : ' + (e?.message || 'enregistrement impossible');
      status.style.color = 'var(--danger)';
    } finally {
      saveBtn.disabled = false;
    }
  });
}

async function initEmplacementsPanel() {
  if (!_emplReady) {
    _emplReady = true;
    const search = document.getElementById('empl-search');
    if (search) {
      search.addEventListener('input', () => renderEmplGrid());
      search.addEventListener('keydown', e => { if (e.key === 'Escape') { search.value = ''; renderEmplGrid(); } });
    }
    const form = document.getElementById('empl-add-form');
    if (form) form.addEventListener('submit', e => { e.preventDefault(); addEmplacement(); });
    const reloadBtn = document.getElementById('empl-reload-csv');
    if (reloadBtn) reloadBtn.addEventListener('click', reloadEmplacementsCsv);
    const importBtn = document.getElementById('empl-import-btn');
    const importInput = document.getElementById('empl-import-input');
    if (importBtn && importInput) {
      importBtn.addEventListener('click', () => importInput.click());
      importInput.addEventListener('change', () => importEmplacementsCsv(importInput));
    }
    const exportBtn = document.getElementById('empl-export-csv');
    if (exportBtn) exportBtn.addEventListener('click', exportEmplacementsCsv);
    // focus style
    ['empl-search', 'empl-new-code'].forEach(id => {
      const el = document.getElementById(id);
      if (!el) return;
      el.addEventListener('focus', () => { el.style.borderColor = 'var(--accent)'; el.style.boxShadow = '0 0 0 3px rgba(34,211,238,.12)'; });
      el.addEventListener('blur',  () => { el.style.borderColor = ''; el.style.boxShadow = ''; });
    });
    const codeInp = document.getElementById('empl-new-code');
    if (codeInp) codeInp.addEventListener('input', () => { codeInp.value = codeInp.value.toUpperCase(); });
  }
  await loadEmplacements();
}

async function loadEmplacements() {
  const grid = document.getElementById('empl-grid');
  if (grid) grid.innerHTML = '<span style="color:var(--muted);font-size:13px">Chargement…</span>';
  try {
    const r = await fetch('/api/settings/emplacements', { credentials: 'include' });
    if (!r.ok) throw new Error('err');
    _emplData = await r.json();
  } catch(e) {
    _emplData = [];
    toast('Erreur lors du chargement des emplacements.', true);
  }
  renderEmplGrid();
}

function renderEmplGrid() {
  const grid = document.getElementById('empl-grid');
  const empty = document.getElementById('empl-empty');
  const count = document.getElementById('empl-count');
  if (!grid) return;

  const q = (document.getElementById('empl-search')?.value || '').trim().toLowerCase();

  const filtered = q
    ? _emplData.filter(e => e.code.toLowerCase().includes(q))
    : _emplData.slice();

  if (count) count.textContent = _emplData.length + ' emplacement' + (_emplData.length > 1 ? 's' : '');

  if (!filtered.length) {
    grid.innerHTML = '';
    if (empty) { empty.style.display = ''; empty.textContent = q ? 'Aucun résultat pour « ' + escHtml(q) + ' ».' : 'Aucun emplacement. Ajoutez-en un ou rechargez depuis le CSV.'; }
    return;
  }
  if (empty) empty.style.display = 'none';

  // Grouper : allée = préfixe lettres, rangée = 2 premiers chiffres qui suivent
  const byAllee = {};
  for (const e of filtered) {
    const code = e.code;
    const m = code.match(/^([A-Z]+)(\d{1,2})/i);
    const allee  = m ? m[1].toUpperCase() : code[0].toUpperCase();
    const rangee = m ? m[2].padStart(2, '0') : '??';
    if (!byAllee[allee]) byAllee[allee] = {};
    if (!byAllee[allee][rangee]) byAllee[allee][rangee] = [];
    byAllee[allee][rangee].push(code);
  }

  const EMPL_LABELS = { 'Z0': 'Z0 – au sol pour expédition', 'Z1': 'Z1 – sortie de production' };

  function pillHtml(code) {
    const c = escHtml(code);
    const label = escHtml(EMPL_LABELS[code] || code);
    const title = EMPL_LABELS[code] ? escHtml(EMPL_LABELS[code]) : c;
    return `<span class="empl-pill" data-code="${c}" title="${title}">
      <span class="empl-pill-code">${label}</span>
      <button type="button" class="empl-pill-del" aria-label="Supprimer ${c}" onclick="deleteEmplacement('${c}')">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </span>`;
  }

  let html = '';
  for (const allee of Object.keys(byAllee).sort()) {
    const rangees = byAllee[allee];
    html += `<div class="empl-allee">
      <div class="empl-allee-hd">
        <span class="empl-allee-letter">${escHtml(allee)}</span>
        <span class="empl-allee-label">Allée ${escHtml(allee)}</span>
      </div>
      <div class="empl-allee-body">`;
    for (const rangee of Object.keys(rangees).sort()) {
      const codes = rangees[rangee].slice().sort();
      html += `<div class="empl-rangee">
        <div class="empl-rangee-pills">${codes.map(pillHtml).join('')}</div>
      </div>`;
    }
    html += `</div></div>`;
  }
  grid.innerHTML = html;
}

async function addEmplacement() {
  const inp = document.getElementById('empl-new-code');
  const code = (inp?.value || '').trim().toUpperCase();
  if (!code) { toast('Saisissez un code emplacement.', true); inp?.focus(); return; }
  const r = await fetch('/api/settings/emplacements', {
    method: 'POST', credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code }),
  });
  if (r.status === 409) { toast(`L'emplacement ${code} existe déjà.`, true); return; }
  if (!r.ok) {
    let msg = 'Erreur lors de l\'ajout.';
    try { const d = await r.json(); if (d.detail) msg = d.detail; } catch(e) {}
    toast(msg, true); return;
  }
  if (inp) inp.value = '';
  toast(`Emplacement ${code} ajouté.`, false);
  await loadEmplacements();
}

async function deleteEmplacement(code) {
  if (!confirm(`Supprimer l'emplacement ${code} ?`)) return;
  const r = await fetch('/api/settings/emplacements/' + encodeURIComponent(code), {
    method: 'DELETE', credentials: 'include',
  });
  if (!r.ok) { toast('Erreur lors de la suppression.', true); return; }
  toast(`Emplacement ${code} supprimé.`, false);
  await loadEmplacements();
}

async function reloadEmplacementsCsv() {
  const btn = document.getElementById('empl-reload-csv');
  if (btn) { btn.disabled = true; btn.textContent = 'Rechargement…'; }
  try {
    const r = await fetch('/api/settings/emplacements/reload-csv', { method: 'POST', credentials: 'include' });
    if (r.status === 422) {
      toast('CSV introuvable ou vide — aucun emplacement importé.', true);
    } else if (!r.ok) {
      toast('Erreur lors du rechargement.', true);
    } else {
      const d = await r.json();
      toast(d.imported + ' emplacement' + (d.imported > 1 ? 's' : '') + ' importé' + (d.imported > 1 ? 's' : '') + ' depuis le CSV.', false);
      await loadEmplacements();
    }
  } catch(e) { toast('Erreur réseau.', true); }
  finally {
    if (btn) { btn.disabled = false; btn.textContent = 'Recharger depuis CSV'; }
  }
}

async function importEmplacementsCsv(input) {
  const file = input.files && input.files[0];
  if (!file) return;
  if (!confirm(`Remplacer le plan actuel par "${file.name}" ? Cette action écrasera tous les emplacements existants.`)) {
    input.value = '';
    return;
  }
  const btn = document.getElementById('empl-import-btn');
  if (btn) { btn.disabled = true; btn.textContent = 'Import en cours…'; }
  try {
    const fd = new FormData();
    fd.append('file', file);
    const r = await fetch('/api/settings/emplacements/import-csv', {
      method: 'POST', credentials: 'include', body: fd,
    });
    const data = r.ok ? await r.json() : null;
    if (!r.ok) {
      let msg = 'Erreur lors de l\'import.';
      try { const e = await r.clone().json(); if (e.detail) msg = e.detail; } catch(_) {}
      toast(msg, true);
    } else {
      toast(data.imported + ' emplacement' + (data.imported > 1 ? 's' : '') + ' importé' + (data.imported > 1 ? 's' : '') + ' — nouveau plan enregistré.', false);
      await loadEmplacements();
    }
  } catch(e) { toast('Erreur réseau.', true); }
  finally {
    input.value = '';
    if (btn) { btn.disabled = false; btn.textContent = 'Importer nouveau CSV'; }
  }
}

function exportEmplacementsCsv() {
  if (!_emplData.length) { toast('Aucun emplacement à exporter.', true); return; }
  const rows = [['code'], ..._emplData.map(e => [e.code])];
  const csv = rows.map(r => r.map(v => '"' + String(v).replace(/"/g, '""') + '"').join(',')).join('\r\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'emplacements_' + new Date().toISOString().slice(0, 10) + '.csv';
  document.body.appendChild(a);
  a.click();
  setTimeout(() => { document.body.removeChild(a); URL.revokeObjectURL(url); }, 100);
}

// ═══════════════════════════════════════════════════════════
// Référentiel Clients (ERP)
// ═══════════════════════════════════════════════════════════
let _cliReady = false;
let _cliData = [];
let _cliEditing = null;        // id en cours d'édition, ou null pour création
let _cliImportFile = null;
let _cliSearchDebounce = null;

async function initClientsPanel() {
  if (!_cliReady) {
    _cliReady = true;
    const search = document.getElementById('cli-search');
    if (search) {
      search.addEventListener('input', () => {
        clearTimeout(_cliSearchDebounce);
        _cliSearchDebounce = setTimeout(loadClients, 220);
      });
      search.addEventListener('keydown', e => {
        if (e.key === 'Escape') { search.value = ''; loadClients(); }
      });
    }
    const etat = document.getElementById('cli-filter-etat');
    if (etat) etat.addEventListener('change', loadClients);
    const newBtn = document.getElementById('cli-new-btn');
    if (newBtn) newBtn.addEventListener('click', () => openCliModal(null));
    const importBtn = document.getElementById('cli-import-btn');
    const importInput = document.getElementById('cli-import-input');
    if (importBtn && importInput) {
      importBtn.addEventListener('click', () => importInput.click());
      importInput.addEventListener('change', () => onCliImportFile(importInput));
    }
    const exportBtn = document.getElementById('cli-export-csv');
    if (exportBtn) exportBtn.addEventListener('click', exportClientsCsv);

    // Sous-onglets du modal
    document.querySelectorAll('#cli-modal-overlay [data-clisub]').forEach(b => {
      b.addEventListener('click', () => {
        document.querySelectorAll('#cli-modal-overlay [data-clisub]').forEach(x => x.classList.remove('active'));
        b.classList.add('active');
        document.querySelectorAll('#cli-modal-overlay .cli-tab').forEach(p => p.style.display = 'none');
        const target = document.getElementById(b.dataset.clisub);
        if (target) target.style.display = '';
      });
    });

    // ESC ferme les modals
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') {
        const m = document.getElementById('cli-modal-overlay');
        const im = document.getElementById('cli-import-overlay');
        if (m && m.style.display === 'flex') closeCliModal();
        else if (im && im.style.display === 'flex') closeCliImportModal();
      }
    });
  }
  await loadClients();
}

async function loadClients() {
  const tbody = document.getElementById('cli-tbody');
  const search = (document.getElementById('cli-search')?.value || '').trim();
  const etat = document.getElementById('cli-filter-etat')?.value || '';
  if (tbody) tbody.innerHTML = '<tr><td colspan="9" style="padding:24px 12px;color:var(--muted);font-size:13px;text-align:center">Chargement…</td></tr>';
  try {
    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (etat) params.set('etat', etat);
    params.set('limit', '2000');
    const r = await fetch('/api/clients?' + params.toString(), { credentials: 'include' });
    if (!r.ok) throw new Error('err');
    const data = await r.json();
    _cliData = data.items || [];
    // Mettre à jour le filtre état si on a la liste complète
    const sel = document.getElementById('cli-filter-etat');
    if (sel && data.etats) {
      const cur = sel.value;
      const opts = ['<option value="">Tous les états</option>'].concat(
        data.etats.map(e => `<option value="${escAttr(e)}"${e === cur ? ' selected' : ''}>${escHtml(e)}</option>`)
      );
      sel.innerHTML = opts.join('');
    }
    const count = document.getElementById('cli-count');
    if (count) {
      const n = data.total || 0;
      count.textContent = n + ' client' + (n > 1 ? 's' : '') + (search || etat ? ' filtré' + (n > 1 ? 's' : '') : '');
    }
  } catch(e) {
    _cliData = [];
    toast('Erreur lors du chargement des clients.', true);
  }
  renderCliTable();
}

function renderCliTable() {
  const tbody = document.getElementById('cli-tbody');
  const empty = document.getElementById('cli-empty');
  if (!tbody) return;
  if (!_cliData.length) {
    tbody.innerHTML = '';
    if (empty) {
      empty.style.display = '';
      const q = (document.getElementById('cli-search')?.value || '').trim();
      empty.textContent = q
        ? 'Aucun résultat pour « ' + q + ' ».'
        : 'Aucun client. Cliquez sur « + Nouveau client » ou importez un fichier xlsx.';
    }
    return;
  }
  if (empty) empty.style.display = 'none';
  const html = _cliData.map(c => {
    const etat = c.etat || '';
    const etatBg = etat === 'Bloqué' ? 'rgba(248,113,113,.15);color:#f87171;border-color:rgba(248,113,113,.35)'
                : etat === 'Inactif' ? 'rgba(148,163,184,.18);color:var(--muted);border-color:rgba(148,163,184,.35)'
                : 'rgba(52,211,153,.15);color:var(--success);border-color:rgba(52,211,153,.35)';
    return `<tr style="border-bottom:1px solid var(--border);cursor:pointer" onclick="openCliModal(${c.id})">
      <td style="padding:9px 12px;font-family:ui-monospace,monospace;font-size:12px;color:var(--muted);white-space:nowrap">${c.numero == null ? '' : escHtml(String(c.numero))}</td>
      <td style="padding:9px 12px;font-family:ui-monospace,monospace;font-size:12px;white-space:nowrap">${escHtml(c.code || '')}</td>
      <td style="padding:9px 12px;font-weight:600">${escHtml(c.raison_sociale || '')}</td>
      <td style="padding:9px 12px;white-space:nowrap">${escHtml(c.ville || '')}</td>
      <td style="padding:9px 12px;white-space:nowrap">${escHtml(c.pays || '')}</td>
      <td style="padding:9px 12px;font-family:ui-monospace,monospace;font-size:12px;white-space:nowrap">${escHtml(c.telephone || '')}</td>
      <td style="padding:9px 12px;font-size:12px">${escHtml(c.email || '')}</td>
      <td style="padding:9px 12px;white-space:nowrap"><span style="display:inline-block;padding:3px 8px;border-radius:6px;font-size:11px;font-weight:700;background:${etatBg};border:1px solid">${escHtml(etat)}</span></td>
      <td style="padding:9px 12px;white-space:nowrap"><button type="button" class="btn btn-sec btn-sm" onclick="event.stopPropagation();openCliModal(${c.id})">Modifier</button></td>
    </tr>`;
  }).join('');
  tbody.innerHTML = html;
}

function openCliModal(id) {
  _cliEditing = id;
  const overlay = document.getElementById('cli-modal-overlay');
  if (!overlay) return;
  overlay.style.display = 'flex';
  overlay.classList.remove('hidden');
  // Reset onglets sur Identité
  document.querySelectorAll('#cli-modal-overlay [data-clisub]').forEach(x => x.classList.remove('active'));
  const firstTab = document.querySelector('#cli-modal-overlay [data-clisub="cli-tab-info"]');
  if (firstTab) firstTab.classList.add('active');
  document.querySelectorAll('#cli-modal-overlay .cli-tab').forEach(p => p.style.display = 'none');
  const t = document.getElementById('cli-tab-info');
  if (t) t.style.display = '';
  // Reset values
  const setV = (id, v) => { const el = document.getElementById(id); if (el) el.value = (v == null ? '' : v); };
  setV('cli-numero', ''); setV('cli-code', ''); setV('cli-etat', 'Normal');
  setV('cli-raison', ''); setV('cli-siret', ''); setV('cli-tva', '');
  setV('cli-rcs', ''); setV('cli-ean', ''); setV('cli-nif', ''); setV('cli-groupe', '');
  setV('cli-adresse1', ''); setV('cli-adresse2', ''); setV('cli-bp', '');
  setV('cli-cp', ''); setV('cli-ville', ''); setV('cli-code-pays', ''); setV('cli-pays', '');
  setV('cli-tel', ''); setV('cli-fax', ''); setV('cli-email', '');
  setV('cli-contact-nom', ''); setV('cli-contact-fonction', '');
  setV('cli-contact-email', ''); setV('cli-contact-tel', '');
  setV('cli-rep', ''); setV('cli-adv', ''); setV('cli-mode-liv', ''); setV('cli-mode-reg', '');
  setV('cli-devise', ''); setV('cli-encours', ''); setV('cli-codecpta', '');
  setV('cli-cat1', ''); setV('cli-cat2', ''); setV('cli-cat3', '');
  setV('cli-notes', '');
  const delBtn = document.getElementById('cli-delete-btn');
  const title = document.getElementById('cli-modal-title');

  if (id == null) {
    if (title) title.textContent = 'Nouveau client';
    if (delBtn) delBtn.style.display = 'none';
    requestAnimationFrame(() => document.getElementById('cli-raison')?.focus());
    return;
  }
  if (title) title.textContent = 'Modifier le client';
  if (delBtn) delBtn.style.display = '';
  // Charger les données
  fetch('/api/clients/' + id, { credentials: 'include' })
    .then(r => r.json())
    .then(c => {
      setV('cli-numero', c.numero); setV('cli-code', c.code); setV('cli-etat', c.etat || 'Normal');
      setV('cli-raison', c.raison_sociale); setV('cli-siret', c.siret); setV('cli-tva', c.tva);
      setV('cli-rcs', c.rcs); setV('cli-ean', c.ean); setV('cli-nif', c.nif); setV('cli-groupe', c.groupe);
      setV('cli-adresse1', c.adresse1); setV('cli-adresse2', c.adresse2); setV('cli-bp', c.bp);
      setV('cli-cp', c.cp); setV('cli-ville', c.ville); setV('cli-code-pays', c.code_pays); setV('cli-pays', c.pays);
      setV('cli-tel', c.telephone); setV('cli-fax', c.telecopie); setV('cli-email', c.email);
      setV('cli-contact-nom', c.contact_nom); setV('cli-contact-fonction', c.contact_fonction);
      setV('cli-contact-email', c.contact_email); setV('cli-contact-tel', c.contact_tel);
      setV('cli-rep', c.representant); setV('cli-adv', c.adv);
      setV('cli-mode-liv', c.mode_livraison); setV('cli-mode-reg', c.mode_reglement);
      setV('cli-devise', c.devise); setV('cli-encours', c.encours_autorise); setV('cli-codecpta', c.code_comptable);
      setV('cli-cat1', c.categorie1); setV('cli-cat2', c.categorie2); setV('cli-cat3', c.categorie3);
      setV('cli-notes', c.notes);
      requestAnimationFrame(() => document.getElementById('cli-raison')?.focus());
    })
    .catch(() => toast('Impossible de charger ce client.', true));
}

function closeCliModal() {
  const overlay = document.getElementById('cli-modal-overlay');
  if (!overlay) return;
  overlay.style.display = 'none';
  overlay.classList.add('hidden');
  _cliEditing = null;
}

async function saveCliModal() {
  const val = id => (document.getElementById(id)?.value || '').trim();
  const raison = val('cli-raison');
  if (!raison) {
    toast('Raison sociale obligatoire.', true);
    document.querySelector('#cli-modal-overlay [data-clisub="cli-tab-info"]')?.click();
    document.getElementById('cli-raison')?.focus();
    return;
  }
  const num = val('cli-numero');
  const encours = val('cli-encours');
  const payload = {
    numero: num === '' ? null : parseInt(num, 10),
    code: val('cli-code') || null,
    raison_sociale: raison,
    siret: val('cli-siret') || null,
    tva: val('cli-tva') || null,
    rcs: val('cli-rcs') || null,
    ean: val('cli-ean') || null,
    nif: val('cli-nif') || null,
    groupe: val('cli-groupe') || null,
    adresse1: val('cli-adresse1') || null,
    adresse2: val('cli-adresse2') || null,
    bp: val('cli-bp') || null,
    cp: val('cli-cp') || null,
    ville: val('cli-ville') || null,
    code_pays: val('cli-code-pays') || null,
    pays: val('cli-pays') || null,
    telephone: val('cli-tel') || null,
    telecopie: val('cli-fax') || null,
    email: val('cli-email') || null,
    contact_nom: val('cli-contact-nom') || null,
    contact_fonction: val('cli-contact-fonction') || null,
    contact_email: val('cli-contact-email') || null,
    contact_tel: val('cli-contact-tel') || null,
    representant: val('cli-rep') || null,
    adv: val('cli-adv') || null,
    mode_livraison: val('cli-mode-liv') || null,
    mode_reglement: val('cli-mode-reg') || null,
    devise: val('cli-devise') || null,
    encours_autorise: encours === '' ? null : parseFloat(encours.replace(',', '.')),
    code_comptable: val('cli-codecpta') || null,
    categorie1: val('cli-cat1') || null,
    categorie2: val('cli-cat2') || null,
    categorie3: val('cli-cat3') || null,
    etat: val('cli-etat') || 'Normal',
    notes: val('cli-notes') || null,
  };
  const url = _cliEditing == null ? '/api/clients' : '/api/clients/' + _cliEditing;
  const method = _cliEditing == null ? 'POST' : 'PUT';
  try {
    const r = await fetch(url, {
      method, credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!r.ok) {
      let msg = 'Erreur lors de l\'enregistrement.';
      try { const d = await r.json(); if (d.detail) msg = d.detail; } catch(_) {}
      toast(msg, true);
      return;
    }
    toast(_cliEditing == null ? 'Client créé.' : 'Client mis à jour.', false);
    closeCliModal();
    await loadClients();
  } catch(e) {
    toast('Erreur réseau.', true);
  }
}

async function deleteCliFromModal() {
  if (_cliEditing == null) return;
  const raison = (document.getElementById('cli-raison')?.value || '').trim();
  if (!confirm(`Supprimer le client « ${raison} » ? Cette action est irréversible.`)) return;
  try {
    const r = await fetch('/api/clients/' + _cliEditing, { method: 'DELETE', credentials: 'include' });
    if (!r.ok) { toast('Erreur lors de la suppression.', true); return; }
    toast('Client supprimé.', false);
    closeCliModal();
    await loadClients();
  } catch(e) { toast('Erreur réseau.', true); }
}

function onCliImportFile(input) {
  const file = input.files && input.files[0];
  if (!file) return;
  _cliImportFile = file;
  const fn = document.getElementById('cli-import-filename');
  if (fn) fn.textContent = file.name;
  const overlay = document.getElementById('cli-import-overlay');
  if (overlay) { overlay.style.display = 'flex'; overlay.classList.remove('hidden'); }
}

function closeCliImportModal() {
  const overlay = document.getElementById('cli-import-overlay');
  if (overlay) { overlay.style.display = 'none'; overlay.classList.add('hidden'); }
  _cliImportFile = null;
  const inp = document.getElementById('cli-import-input');
  if (inp) inp.value = '';
}

async function confirmCliImport() {
  if (!_cliImportFile) { closeCliImportModal(); return; }
  const mode = (document.querySelector('input[name="cli-import-mode"]:checked')?.value || 'merge');
  if (mode === 'replace' && !confirm('Mode REMPLACER : tous les clients existants seront supprimés avant import. Continuer ?')) return;
  const btn = document.getElementById('cli-import-confirm');
  if (btn) { btn.disabled = true; btn.textContent = 'Import en cours…'; }
  try {
    const fd = new FormData();
    fd.append('file', _cliImportFile);
    const r = await fetch('/api/clients/import-xlsx?mode=' + encodeURIComponent(mode), {
      method: 'POST', credentials: 'include', body: fd,
    });
    if (!r.ok) {
      let msg = 'Erreur lors de l\'import.';
      try { const d = await r.json(); if (d.detail) msg = d.detail; } catch(_) {}
      toast(msg, true);
      return;
    }
    const data = await r.json();
    let msg = `${data.inserted} créé${data.inserted > 1 ? 's' : ''}, ${data.updated} mis à jour`;
    if (data.skipped) msg += `, ${data.skipped} ignoré${data.skipped > 1 ? 's' : ''}`;
    msg += '.';
    toast(msg, false);
    if (data.errors && data.errors.length) {
      console.warn('Erreurs import clients :', data.errors);
    }
    closeCliImportModal();
    await loadClients();
  } catch(e) { toast('Erreur réseau.', true); }
  finally {
    if (btn) { btn.disabled = false; btn.textContent = 'Lancer l\'import'; }
  }
}

function exportClientsCsv() {
  if (!_cliData.length) { toast('Aucun client à exporter.', true); return; }
  const cols = [
    ['numero', 'N°'], ['code', 'Code'], ['raison_sociale', 'Raison sociale'],
    ['adresse1', 'Adresse 1'], ['adresse2', 'Adresse 2'], ['bp', 'B.P.'],
    ['cp', 'C.P.'], ['ville', 'Ville'], ['code_pays', 'C.Pays'], ['pays', 'Pays'],
    ['siret', 'Siret'], ['tva', 'N.TVA'], ['telephone', 'Téléphone'],
    ['email', 'Email'], ['representant', 'Représentant'], ['adv', 'ADV'],
    ['mode_reglement', 'Mode de règlement'], ['devise', 'Devise'],
    ['encours_autorise', 'Encours autorisé'], ['code_comptable', 'Code Comptable'],
    ['contact_nom', 'Contact'], ['contact_email', 'Email contact'],
    ['contact_tel', 'Tél contact'], ['etat', 'État'],
  ];
  const head = cols.map(c => c[1]);
  const rows = [head, ..._cliData.map(c => cols.map(([k]) => c[k] == null ? '' : c[k]))];
  const csv = rows.map(r => r.map(v => '"' + String(v).replace(/"/g, '""') + '"').join(';')).join('\r\n');
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'clients_' + new Date().toISOString().slice(0, 10) + '.csv';
  document.body.appendChild(a);
  a.click();
  setTimeout(() => { document.body.removeChild(a); URL.revokeObjectURL(url); }, 100);
}

// ─── Promotion v1 → v2 ──────────────────────────────────────────────
function _prEsc(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

async function loadPromoteStatus() {
  const v2v = document.getElementById('pr-v2-version');
  const v2h = document.getElementById('pr-v2-head');
  const nxv = document.getElementById('pr-next-version');
  const orh = document.getElementById('pr-origin-head');
  const commitsEl = document.getElementById('pr-commits');
  const goBtn = document.getElementById('pr-go-btn');
  const blocked = document.getElementById('pr-blocked-reason');
  if (commitsEl) commitsEl.innerHTML = '<div style="padding:24px;text-align:center;color:var(--muted);font-size:13px">Chargement…</div>';
  let data;
  try {
    data = await api('/api/promote/status');
    if (!data) return;
  } catch (e) {
    commitsEl.innerHTML = '<div style="padding:18px;color:var(--danger);font-size:13px">Erreur de chargement : ' + _prEsc(e && e.message ? e.message : String(e)) + '</div>';
    return;
  }
  v2v.textContent = data.v2_version ? 'v' + data.v2_version : '—';
  v2h.textContent = data.v2_head || '';
  nxv.textContent = data.next_version ? 'v' + data.next_version : '—';
  orh.textContent = data.origin_head || '';

  if (!data.commits_ahead || data.commits_ahead.length === 0) {
    commitsEl.innerHTML = '<div style="padding:24px;text-align:center;color:var(--muted);font-size:13px">Rien à promouvoir — v2 est déjà à jour.</div>';
  } else {
    commitsEl.innerHTML = data.commits_ahead.map(c => (
      '<div style="display:flex;gap:10px;padding:8px 10px;border-bottom:1px solid var(--border);align-items:flex-start">'
        + '<span style="font-family:\'SFMono-Regular\',Menlo,monospace;font-size:11px;color:var(--accent);min-width:60px">' + _prEsc(c.hash) + '</span>'
        + '<div style="flex:1;min-width:0">'
          + '<div style="font-size:13px;color:var(--text);overflow:hidden;text-overflow:ellipsis">' + _prEsc(c.subject) + '</div>'
          + '<div style="font-size:11px;color:var(--muted);margin-top:2px">' + _prEsc(c.author) + ' · ' + _prEsc(c.date) + '</div>'
        + '</div>'
      + '</div>'
    )).join('');
  }

  goBtn.disabled = !data.can_promote;
  blocked.textContent = data.can_promote ? '' : (data.reason || '');
}

async function runPromote() {
  const goBtn = document.getElementById('pr-go-btn');
  const notesEl = document.getElementById('pr-notes');
  const outCard = document.getElementById('pr-output-card');
  const outEl = document.getElementById('pr-output');
  const notes = (notesEl.value || '').trim();

  // Garde-fou confirm
  if (!confirm('Promouvoir v1 → v2 maintenant ?\\nBackup DB, pull, bump patch, restart, healthcheck.\\nRollback auto si KO.')) return;

  goBtn.disabled = true;
  goBtn.textContent = 'Promotion en cours…';
  outCard.style.display = 'block';
  outEl.textContent = '';

  try {
    const r = await fetch(API + '/api/promote', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notes }),
    });
    if (!r.ok) {
      outEl.textContent += '[HTTP ' + r.status + '] ' + (await r.text().catch(() => '')) + '\\n';
      goBtn.disabled = false;
      goBtn.textContent = 'Promouvoir maintenant';
      return;
    }
    // Stream la réponse ligne par ligne
    const reader = r.body.getReader();
    const decoder = new TextDecoder();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      outEl.textContent += decoder.decode(value, { stream: true });
      outEl.scrollTop = outEl.scrollHeight;
    }
  } catch (e) {
    outEl.textContent += '\\n[Erreur réseau : ' + (e && e.message ? e.message : String(e)) + ']\\n';
  } finally {
    goBtn.textContent = 'Promouvoir maintenant';
    // Recharger le statut (commits zéro après succès, ou inchangé après rollback)
    setTimeout(() => loadPromoteStatus(), 500);
  }
}

// ─── Sync DB v2 → v1 ──────────────────────────────────────────────
async function syncDbV1() {
  const btn = document.getElementById('db-sync-btn');
  const status = document.getElementById('db-sync-status');
  if (!btn) return;
  if (!confirm('⚠ Synchroniser DB v2 → v1 ?\n\nCette action écrase intégralement la DB v1 par la copie live de v2.\nToutes les données créées sur v1 depuis la dernière resync seront perdues.\n\nUn backup pré-resync est conservé automatiquement.\nv1 redémarrera dans ~15s.\n\nContinuer ?')) return;
  const original = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Synchronisation…';
  if (status) status.textContent = '';
  try {
    const r = await fetch(API + '/api/sync-db-v1', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
    });
    const text = await r.text().catch(() => '');
    if (!r.ok) {
      if (status) {
        status.textContent = 'Echec (HTTP ' + r.status + ')';
        status.style.color = 'var(--danger)';
      }
      if (typeof showToast === 'function') showToast('Sync DB echouee : ' + (text || r.status), 'danger');
      else alert('Sync DB echouee : ' + (text || r.status));
    } else {
      if (status) {
        status.textContent = 'OK · ' + new Date().toLocaleTimeString();
        status.style.color = 'var(--success, var(--ok))';
      }
      if (typeof showToast === 'function') showToast('Resync lancee. v1 redemarrera dans ~15s.', 'success');
    }
  } catch (e) {
    if (status) {
      status.textContent = 'Erreur reseau';
      status.style.color = 'var(--danger)';
    }
    if (typeof showToast === 'function') showToast('Erreur reseau : ' + (e && e.message ? e.message : String(e)), 'danger');
  } finally {
    btn.disabled = false;
    btn.textContent = original;
  }
}

// ═════════════════════════════════════════════════════════════════════
// PRINTERS — CRUD imprimantes / templates / agents (superadmin)
// ═════════════════════════════════════════════════════════════════════
const PR = {
  imprimantes: [], templates: [], agents: [], usages: [],
  sub: 'imp',
  editingImp: null, editingTpl: null,
};

function prNoStore() { return { credentials: 'include', headers: {} }; }

async function prFetch(url, opts) {
  const o = { credentials: 'include', headers: { 'Content-Type': 'application/json' }, ...(opts || {}) };
  const r = await fetch(url, o);
  const txt = await r.text().catch(() => '');
  let data = null; try { data = txt ? JSON.parse(txt) : null; } catch(e) {}
  if (!r.ok) {
    // v2 — remonte plus d'infos : detail JSON en priorite, sinon debut du body texte
    let msg;
    if (data && data.detail) {
      msg = data.detail;
    } else if (txt && txt.length < 300) {
      msg = 'HTTP ' + r.status + ' : ' + txt.trim();
    } else {
      msg = 'HTTP ' + r.status + ' (voir logs serveur)';
    }
    console.error('[printers] prFetch error', url, r.status, txt);
    throw new Error(msg);
  }
  return data;
}

function prToast(msg, kind) {
  if (typeof showToast === 'function') showToast(msg, kind || 'success');
  else console.log('[printers]', msg);
}

function _escH(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, c => (
  {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]
)); }

async function initPrintersPanel() {
  // Un seul chargement d'entrée : on tire tout en parallèle.
  document.getElementById('pr-panel-ag').querySelector('#pr-ag-panel').style.display = '';
  try {
    const [imp, tpl, ag, us] = await Promise.all([
      prFetch('/api/print/imprimantes'),
      prFetch('/api/print/templates'),
      prFetch('/api/print/agents'),
      prFetch('/api/print/usages'),
    ]);
    PR.imprimantes = imp || [];
    PR.templates = tpl || [];
    PR.agents = ag || [];
    PR.usages = us || [];
  } catch (e) {
    prToast('Chargement imprimantes: ' + e.message, 'danger');
  }
  prRenderImprimantes();
  prRenderTemplates();
  prRenderAgents();
}

function prSetSub(sub) {
  PR.sub = sub;
  document.querySelectorAll('.pr-sub').forEach(b => {
    const on = b.dataset.prsub === sub;
    b.style.color = on ? 'var(--text)' : 'var(--muted)';
    b.style.borderBottom = '2px solid ' + (on ? 'var(--accent)' : 'transparent');
    b.classList.toggle('active', on);
  });
  document.getElementById('pr-panel-imp').style.display = (sub === 'imp') ? '' : 'none';
  document.getElementById('pr-panel-tpl').style.display = (sub === 'tpl') ? '' : 'none';
  document.getElementById('pr-panel-ag').style.display = (sub === 'ag') ? '' : 'none';
}

// ─── Imprimantes ─────────────────────────────────────────────────
function prRenderImprimantes() {
  const root = document.getElementById('pr-imp-list');
  if (!root) return;
  if (!PR.imprimantes.length) {
    root.innerHTML = '<div style="padding:24px;text-align:center;color:var(--muted);font-size:13px;background:var(--card);border:1px dashed var(--border);border-radius:12px">Aucune imprimante configurée. Clique sur « Nouvelle imprimante ».</div>';
    return;
  }
  const agentMap = {};
  PR.agents.forEach(a => { agentMap[a.id] = a; });
  root.innerHTML = PR.imprimantes.map(i => {
    const agent = i.agent_id ? agentMap[i.agent_id] : null;
    const agentLbl = agent ? _escH(agent.nom) : '<em style="color:var(--muted)">Non rattachée</em>';
    const status = i.actif
      ? '<span style="font-size:11px;font-weight:700;padding:2px 8px;border-radius:6px;background:rgba(52,211,153,.15);color:var(--success)">Active</span>'
      : '<span style="font-size:11px;font-weight:700;padding:2px 8px;border-radius:6px;background:var(--accent-bg);color:var(--muted)">Inactive</span>';
    return `
      <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px 16px">
        <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
          <div style="flex:1;min-width:200px">
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
              <span style="font-size:14px;font-weight:700;color:var(--text)">${_escH(i.nom)}</span>
              ${status}
              <span style="font-size:11px;background:var(--bg);border:1px solid var(--border);padding:2px 6px;border-radius:5px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px">${_escH(i.langage)}</span>
            </div>
            <div style="font-size:12px;color:var(--muted);margin-top:4px">
              ${_escH(i.poste || 'Sans poste')} · ${(i.type_connexion === 'windows_local') ? ('Queue Windows : ' + _escH(i.nom_queue_windows || '?')) : (_escH(i.ip_locale || '?') + ':' + (i.port || 9100))} · ${i.largeur_mm}×${i.hauteur_mm}mm @ ${i.dpi}dpi · Agent : ${agentLbl}
            </div>
          </div>
          <div style="display:flex;gap:6px;flex-shrink:0">
            <button class="btn btn-ghost" style="padding:6px 12px;font-size:12px" onclick="prTestPrint(${i.id})">Test d'impression</button>
            <button class="btn btn-ghost" style="padding:6px 12px;font-size:12px" onclick="prEditImprimante(${i.id})">Modifier</button>
          </div>
        </div>
      </div>`;
  }).join('');
}

function prToggleTypeConnexion() {
  const isWin = document.getElementById('pr-f-type-win').checked;
  document.getElementById('pr-f-tcp-ip-row').style.display = isWin ? 'none' : '';
  document.getElementById('pr-f-tcp-port-row').style.display = isWin ? 'none' : '';
  document.getElementById('pr-f-queue-row').style.display = isWin ? '' : 'none';
}

function prEditImprimante(id) {
  PR.editingImp = id;
  const i = id ? PR.imprimantes.find(x => x.id === id) : null;
  document.getElementById('pr-imp-modal-title').textContent = i ? ('Modifier — ' + i.nom) : 'Nouvelle imprimante';
  document.getElementById('pr-f-nom').value = i ? i.nom : '';
  document.getElementById('pr-f-poste').value = (i && i.poste) || '';
  const agSel = document.getElementById('pr-f-agent');
  agSel.innerHTML = '<option value="">Aucun</option>' + PR.agents.map(a =>
    `<option value="${a.id}">${_escH(a.nom)}</option>`).join('');
  agSel.value = (i && i.agent_id) ? String(i.agent_id) : '';
  // v1.6 — type de connexion (tcp_ip par defaut pour retrocompat)
  const tc = (i && i.type_connexion) || 'tcp_ip';
  document.getElementById('pr-f-type-tcp').checked = (tc === 'tcp_ip');
  document.getElementById('pr-f-type-win').checked = (tc === 'windows_local');
  document.getElementById('pr-f-ip').value = (i && i.ip_locale) ? i.ip_locale : '';
  document.getElementById('pr-f-port').value = (i && i.port) ? i.port : 9100;
  document.getElementById('pr-f-queue').value = (i && i.nom_queue_windows) || '';
  prToggleTypeConnexion();
  document.getElementById('pr-f-langage').value = i ? i.langage : 'zpl';
  document.getElementById('pr-f-dpi').value = i ? i.dpi : 203;
  document.getElementById('pr-f-largeur').value = i ? i.largeur_mm : 102;
  document.getElementById('pr-f-hauteur').value = i ? i.hauteur_mm : 152;
  document.getElementById('pr-f-note').value = (i && i.note) || '';
  document.getElementById('pr-f-del').style.display = i ? '' : 'none';
  document.getElementById('pr-imp-modal').style.display = 'flex';
}

function prCloseModal() {
  document.getElementById('pr-imp-modal').style.display = 'none';
  PR.editingImp = null;
}

async function prSaveImprimante() {
  const isWin = document.getElementById('pr-f-type-win').checked;
  const tc = isWin ? 'windows_local' : 'tcp_ip';
  const body = {
    nom: document.getElementById('pr-f-nom').value.trim(),
    poste: document.getElementById('pr-f-poste').value.trim() || null,
    agent_id: parseInt(document.getElementById('pr-f-agent').value, 10) || null,
    type_connexion: tc,
    ip_locale: isWin ? null : document.getElementById('pr-f-ip').value.trim(),
    port: isWin ? null : (parseInt(document.getElementById('pr-f-port').value, 10) || 9100),
    nom_queue_windows: isWin ? document.getElementById('pr-f-queue').value.trim() : null,
    langage: document.getElementById('pr-f-langage').value,
    dpi: parseInt(document.getElementById('pr-f-dpi').value, 10) || 203,
    largeur_mm: parseInt(document.getElementById('pr-f-largeur').value, 10) || 102,
    hauteur_mm: parseInt(document.getElementById('pr-f-hauteur').value, 10) || 152,
    note: document.getElementById('pr-f-note').value.trim() || null,
  };
  if (!body.nom) { prToast('Nom requis.', 'danger'); return; }
  if (tc === 'tcp_ip' && !body.ip_locale) { prToast('IP requise pour une imprimante réseau.', 'danger'); return; }
  if (tc === 'windows_local' && !body.nom_queue_windows) { prToast('Nom de la queue Windows requis.', 'danger'); return; }
  if (tc === 'windows_local' && !body.agent_id) { prToast('Un agent local doit être rattaché — c\'est le PC hôte qui possède la queue.', 'danger'); return; }
  try {
    if (PR.editingImp) {
      await prFetch('/api/print/imprimantes/' + PR.editingImp, {
        method: 'PATCH', body: JSON.stringify(body),
      });
      prToast('Imprimante modifiée.');
    } else {
      await prFetch('/api/print/imprimantes', {
        method: 'POST', body: JSON.stringify(body),
      });
      prToast('Imprimante créée.');
    }
    prCloseModal();
    await initPrintersPanel();
  } catch (e) {
    prToast('Erreur : ' + e.message, 'danger');
  }
}

async function prDeleteImprimante() {
  if (!PR.editingImp) return;
  if (!confirm('Supprimer cette imprimante ? Les templates associés seront également supprimés.')) return;
  try {
    await prFetch('/api/print/imprimantes/' + PR.editingImp, { method: 'DELETE' });
    prToast('Imprimante supprimée.');
    prCloseModal();
    await initPrintersPanel();
  } catch (e) {
    prToast('Erreur : ' + e.message, 'danger');
  }
}

async function prTestPrint(imprimanteId) {
  try {
    const r = await prFetch('/api/print/test', {
      method: 'POST', body: JSON.stringify({ imprimante_id: imprimanteId }),
    });
    prToast(r.message || 'Test envoyé.', 'success');
  } catch (e) {
    prToast('Erreur : ' + e.message, 'danger');
  }
}

// ═══════════════════════════════════════════════════════════════════════
// WIZARD "Comment connecter mon imprimante à MySifa"
// 4 étapes : Type → Agent (+ install si Locale) → Imprimante → Test
// ═══════════════════════════════════════════════════════════════════════

const PR_WIZ = {
  step: 1,
  type: null,           // 'tcp_ip' | 'windows_local'
  agentId: null,        // id de l'agent sélectionné ou créé
  agentToken: null,     // token en clair (récupéré à la création)
  agentName: null,      // nom de l'agent pour affichage
  imprimanteId: null,   // id de l'imprimante créée à l'étape 3
  imprimanteName: null,
};

function prWizardStart() {
  // Réinitialise l'état
  PR_WIZ.step = 1;
  PR_WIZ.type = null;
  PR_WIZ.agentId = null;
  PR_WIZ.agentToken = null;
  PR_WIZ.agentName = null;
  PR_WIZ.imprimanteId = null;
  PR_WIZ.imprimanteName = null;
  // Reset UI
  document.querySelectorAll('.pr-wiz-typebtn').forEach(b => {
    b.style.borderColor = 'var(--border)';
    b.style.background = 'var(--bg)';
  });
  document.getElementById('pr-wiz-agent-created').style.display = 'none';
  document.getElementById('pr-wiz-agent-name').value = '';
  document.getElementById('pr-wiz-token-display').value = '';
  document.getElementById('pr-wiz-install-cmd').value = '';
  document.getElementById('pr-wiz-imp-nom').value = '';
  document.getElementById('pr-wiz-imp-poste').value = '';
  document.getElementById('pr-wiz-imp-ip').value = '';
  document.getElementById('pr-wiz-imp-port').value = '9100';
  document.getElementById('pr-wiz-imp-queue').value = '';
  document.getElementById('pr-wiz-test-result').innerHTML = '';
  // Recharge la liste des agents pour le dropdown (au cas où)
  prWizPopulateAgents();
  // Affiche l'étape 1
  prWizGotoStep(1);
  document.getElementById('pr-wiz-modal').style.display = 'flex';
}

function prWizClose() {
  document.getElementById('pr-wiz-modal').style.display = 'none';
  // Si une imprimante a été créée, rafraîchit la liste principale
  if (PR_WIZ.imprimanteId) {
    initPrintersPanel();
  }
}

function prWizGotoStep(n) {
  PR_WIZ.step = n;
  // Cache toutes les pages, affiche celle demandée
  document.querySelectorAll('.pr-wiz-page').forEach(p => {
    p.style.display = (parseInt(p.dataset.step, 10) === n) ? '' : 'none';
  });
  // Progress bar
  document.querySelectorAll('.pr-wiz-dot').forEach(d => {
    const s = parseInt(d.dataset.s, 10);
    d.style.background = (s <= n) ? 'var(--accent)' : 'var(--border)';
  });
  // Label
  const labels = {
    1: 'Étape 1 / 4 · Type d\'imprimante',
    2: 'Étape 2 / 4 · Agent MySifa',
    3: 'Étape 3 / 4 · Créer l\'imprimante',
    4: 'Étape 4 / 4 · Test',
  };
  document.getElementById('pr-wiz-step-label').textContent = labels[n];
  // Nav buttons
  document.getElementById('pr-wiz-back-btn').style.visibility = (n === 1 || n === 4) ? 'hidden' : 'visible';
  const nextBtn = document.getElementById('pr-wiz-next-btn');
  if (n === 1) {
    nextBtn.textContent = 'Continuer →';
    nextBtn.style.display = PR_WIZ.type ? '' : 'none';
  } else if (n === 2) {
    nextBtn.textContent = 'Continuer →';
    nextBtn.style.display = PR_WIZ.agentId ? '' : 'none';
  } else if (n === 3) {
    nextBtn.textContent = 'Créer l\'imprimante';
    nextBtn.style.display = '';
    nextBtn.onclick = prWizCreateImprimante;
  } else if (n === 4) {
    nextBtn.textContent = 'Terminer';
    nextBtn.style.display = '';
    nextBtn.onclick = prWizClose;
  }
  if (n !== 3 && n !== 4) nextBtn.onclick = prWizNext;
}

function prWizNext() {
  if (PR_WIZ.step === 1) {
    if (!PR_WIZ.type) { prToast('Choisis un type d\'imprimante.', 'danger'); return; }
    // Adapte les textes de l'étape 2 selon le type
    if (PR_WIZ.type === 'windows_local') {
      document.getElementById('pr-wiz-agent-title').textContent = 'Installer l\'agent MySifa sur le PC hôte';
      document.getElementById('pr-wiz-agent-intro').textContent = 'Comme ton imprimante est branchée sur un PC (USB / LPT), l\'agent MySifa doit tourner SUR CE PC. Il communiquera avec l\'imprimante via le driver Windows installé.';
    } else {
      document.getElementById('pr-wiz-agent-title').textContent = 'Choisir ou installer un agent MySifa';
      document.getElementById('pr-wiz-agent-intro').textContent = 'L\'agent est un petit programme qui poll MySifa depuis un PC/Raspberry Pi du LAN, et envoie les jobs à ton imprimante réseau. Un seul agent suffit pour plusieurs imprimantes.';
    }
    prWizGotoStep(2);
  } else if (PR_WIZ.step === 2) {
    if (!PR_WIZ.agentId) { prToast('Sélectionne ou crée un agent.', 'danger'); return; }
    // Adapte le formulaire imprimante selon le type
    const isWin = (PR_WIZ.type === 'windows_local');
    document.getElementById('pr-wiz-imp-ip-row').style.display = isWin ? 'none' : '';
    document.getElementById('pr-wiz-imp-port-row').style.display = isWin ? 'none' : '';
    document.getElementById('pr-wiz-imp-queue-row').style.display = isWin ? '' : 'none';
    prWizGotoStep(3);
  }
}

function prWizBack() {
  if (PR_WIZ.step > 1) prWizGotoStep(PR_WIZ.step - 1);
}

function prWizSelectType(type) {
  PR_WIZ.type = type;
  // Style visuel : highlight le bouton sélectionné
  document.querySelectorAll('.pr-wiz-typebtn').forEach(b => {
    b.style.borderColor = 'var(--border)';
    b.style.background = 'var(--bg)';
  });
  const btn = document.querySelector(`.pr-wiz-typebtn[onclick*="${type}"]`);
  if (btn) {
    btn.style.borderColor = 'var(--accent)';
    btn.style.background = 'var(--accent-bg)';
  }
  // v2 — auto-advance : petit délai pour que l'utilisateur voie le highlight
  setTimeout(() => prWizNext(), 250);
}

function prWizPopulateAgents() {
  const sel = document.getElementById('pr-wiz-agent-select');
  if (!sel) return;
  const opts = ['<option value="">— Sélectionner —</option>'];
  (PR.agents || []).forEach(a => {
    opts.push(`<option value="${a.id}">${_escH(a.nom)}</option>`);
  });
  sel.innerHTML = opts.join('');
  sel.onchange = () => {
    const v = parseInt(sel.value, 10);
    if (v) {
      PR_WIZ.agentId = v;
      const ag = PR.agents.find(a => a.id === v);
      PR_WIZ.agentName = ag ? ag.nom : null;
      PR_WIZ.agentToken = null; // pas de token pour un agent existant
      document.getElementById('pr-wiz-agent-created').style.display = 'none';
      document.getElementById('pr-wiz-next-btn').style.display = '';
    } else {
      PR_WIZ.agentId = null;
      document.getElementById('pr-wiz-next-btn').style.display = 'none';
    }
  };
}

function prWizToggleAgentMode() {
  const existing = document.getElementById('pr-wiz-agent-existing').checked;
  document.getElementById('pr-wiz-agent-existing-row').style.display = existing ? '' : 'none';
  document.getElementById('pr-wiz-agent-new-row').style.display = existing ? 'none' : '';
  // Reset agentId quand on change de mode
  PR_WIZ.agentId = null;
  PR_WIZ.agentToken = null;
  document.getElementById('pr-wiz-agent-created').style.display = 'none';
  document.getElementById('pr-wiz-next-btn').style.display = 'none';
}

async function prWizCreateAgent() {
  const nom = document.getElementById('pr-wiz-agent-name').value.trim();
  if (!nom) { prToast('Nom de l\'agent requis.', 'danger'); return; }
  try {
    const r = await prFetch('/api/print/agents', {
      method: 'POST', body: JSON.stringify({ nom }),
    });
    PR_WIZ.agentId = r.id;
    PR_WIZ.agentToken = r.token;
    PR_WIZ.agentName = nom;
    // Affiche le bloc token + installer
    document.getElementById('pr-wiz-token-display').value = r.token;
    // Génère la commande d'install pré-remplie avec le token
    const cmd = `powershell -ExecutionPolicy Bypass -File .\\install_agent_windows.ps1 -Token "${r.token}"`;
    document.getElementById('pr-wiz-install-cmd').value = cmd;
    document.getElementById('pr-wiz-agent-created').style.display = '';
    // Cache le bloc install si c'est TCP/IP (l'agent tourne peut-être ailleurs, on ne force pas)
    document.getElementById('pr-wiz-install-block').style.display = '';
    // Active le bouton Continuer
    document.getElementById('pr-wiz-next-btn').style.display = '';
    // Rafraîchit la liste principale des agents (pour que l'onglet Agents locaux le voie)
    await initPrintersPanel();
    // Re-populate le dropdown
    prWizPopulateAgents();
    prToast('Agent créé. Token affiché ci-dessous.', 'success');
  } catch (e) {
    prToast('Erreur : ' + e.message, 'danger');
  }
}

function prWizCopyToken() {
  const el = document.getElementById('pr-wiz-token-display');
  el.select();
  try { document.execCommand('copy'); prToast('Token copié.', 'success'); }
  catch (e) { prToast('Copie manuelle nécessaire.', 'danger'); }
}

function prWizCopyInstallCmd() {
  const el = document.getElementById('pr-wiz-install-cmd');
  el.select();
  try { document.execCommand('copy'); prToast('Commande copiée.', 'success'); }
  catch (e) { prToast('Copie manuelle nécessaire.', 'danger'); }
}

async function prWizCreateImprimante() {
  const isWin = (PR_WIZ.type === 'windows_local');
  const body = {
    nom: document.getElementById('pr-wiz-imp-nom').value.trim(),
    poste: document.getElementById('pr-wiz-imp-poste').value.trim() || null,
    agent_id: PR_WIZ.agentId,
    type_connexion: PR_WIZ.type,
    ip_locale: isWin ? null : document.getElementById('pr-wiz-imp-ip').value.trim(),
    port: isWin ? null : (parseInt(document.getElementById('pr-wiz-imp-port').value, 10) || 9100),
    nom_queue_windows: isWin ? document.getElementById('pr-wiz-imp-queue').value.trim() : null,
    langage: document.getElementById('pr-wiz-imp-langage').value,
    dpi: parseInt(document.getElementById('pr-wiz-imp-dpi').value, 10) || 203,
    largeur_mm: parseInt(document.getElementById('pr-wiz-imp-largeur').value, 10) || 102,
    hauteur_mm: parseInt(document.getElementById('pr-wiz-imp-hauteur').value, 10) || 152,
  };
  if (!body.nom) { prToast('Nom de l\'imprimante requis.', 'danger'); return; }
  if (!isWin && !body.ip_locale) { prToast('Adresse IP requise.', 'danger'); return; }
  if (isWin && !body.nom_queue_windows) { prToast('Nom de la queue Windows requis.', 'danger'); return; }
  try {
    const r = await prFetch('/api/print/imprimantes', {
      method: 'POST', body: JSON.stringify(body),
    });
    PR_WIZ.imprimanteId = r.id;
    PR_WIZ.imprimanteName = body.nom;
    document.getElementById('pr-wiz-created-name').textContent = body.nom;
    prWizGotoStep(4);
    // Rafraîchit la liste principale
    await initPrintersPanel();
  } catch (e) {
    prToast('Erreur : ' + e.message, 'danger');
  }
}

async function prWizTestPrint() {
  if (!PR_WIZ.imprimanteId) return;
  const resultEl = document.getElementById('pr-wiz-test-result');
  resultEl.textContent = 'Envoi du test…';
  resultEl.style.color = 'var(--muted)';
  try {
    const r = await prFetch('/api/print/test', {
      method: 'POST', body: JSON.stringify({ imprimante_id: PR_WIZ.imprimanteId }),
    });
    resultEl.innerHTML = '✓ ' + (r.message || 'Test envoyé.') + ' — regarde l\'imprimante physique.';
    resultEl.style.color = 'var(--success)';
  } catch (e) {
    resultEl.innerHTML = '⚠ Erreur : ' + e.message + '. Vérifie que l\'agent tourne bien.';
    resultEl.style.color = 'var(--danger)';
  }
}

// ─── Templates ──────────────────────────────────────────────────
function prRenderTemplates() {
  const root = document.getElementById('pr-tpl-list');
  if (!root) return;
  if (!PR.imprimantes.length) {
    root.innerHTML = '<div style="padding:24px;text-align:center;color:var(--muted);font-size:13px">Ajoute d\'abord une imprimante.</div>';
    return;
  }
  const impMap = {};
  PR.imprimantes.forEach(i => { impMap[i.id] = i; });
  const grouped = {};
  PR.imprimantes.forEach(i => { grouped[i.id] = { imp: i, templates: [] }; });
  PR.templates.forEach(t => { if (grouped[t.imprimante_id]) grouped[t.imprimante_id].templates.push(t); });
  root.innerHTML = Object.values(grouped).map(g => {
    const tplHtml = g.templates.length
      ? g.templates.map(t => `
        <div style="display:flex;align-items:center;gap:10px;padding:8px 12px;background:var(--bg);border-radius:8px;margin-top:6px">
          <div style="flex:1;min-width:0">
            <div style="font-size:13px;font-weight:600;color:var(--text)">${_escH(t.nom)}</div>
            <div style="font-size:11px;color:var(--muted)">${_escH(t.usage_label)} — ${t.actif ? 'Actif' : 'Inactif'}</div>
          </div>
          <button class="btn btn-ghost" style="padding:4px 10px;font-size:11px" onclick="prEditTemplate(${t.id})">Modifier</button>
        </div>`).join('')
      : '<div style="padding:8px 12px;color:var(--muted);font-size:12px;font-style:italic">Aucun template pour cette imprimante.</div>';
    return `
      <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px 16px">
        <div style="display:flex;align-items:center;justify-content:space-between;gap:8px">
          <div>
            <div style="font-size:13px;font-weight:700;color:var(--text)">${_escH(g.imp.nom)}</div>
            <div style="font-size:11px;color:var(--muted)">${_escH(g.imp.langage.toUpperCase())} — ${_escH(g.imp.poste || 'Sans poste')}</div>
          </div>
          <button class="btn btn-ghost" style="padding:4px 10px;font-size:11px" onclick="prNewTemplate(${g.imp.id})">+ Template</button>
        </div>
        ${tplHtml}
      </div>`;
  }).join('');
}

async function prNewTemplate(imprimanteId) {
  PR.editingTpl = { imprimanteId };
  document.getElementById('pr-tpl-modal-title').textContent = 'Nouveau template';
  document.getElementById('pr-tpl-nom').value = '';
  document.getElementById('pr-tpl-contenu').value = '';
  const usel = document.getElementById('pr-tpl-usage');
  usel.innerHTML = PR.usages.map(u => `<option value="${_escH(u.key)}">${_escH(u.label)}</option>`).join('');
  usel.value = PR.usages[0] ? PR.usages[0].key : '';
  usel.disabled = false;
  prRenderPlaceholders(usel.value);
  usel.onchange = () => prRenderPlaceholders(usel.value);
  document.getElementById('pr-tpl-del').style.display = 'none';
  // Charge la galerie de modeles predefinis
  document.getElementById('pr-tpl-gallery-row').style.display = '';
  await prLoadGallery();
  // Reset preview
  prTplClearPreview();
  document.getElementById('pr-tpl-modal').style.display = 'flex';
}

function prEditTemplate(id) {
  const t = PR.templates.find(x => x.id === id);
  if (!t) return;
  PR.editingTpl = { id: t.id, imprimanteId: t.imprimante_id };
  document.getElementById('pr-tpl-modal-title').textContent = 'Modifier — ' + t.nom;
  document.getElementById('pr-tpl-nom').value = t.nom;
  document.getElementById('pr-tpl-contenu').value = t.contenu;
  const usel = document.getElementById('pr-tpl-usage');
  usel.innerHTML = PR.usages.map(u => `<option value="${_escH(u.key)}">${_escH(u.label)}</option>`).join('');
  usel.value = t.usage_key;
  usel.disabled = true; // usage fixe une fois créé
  prRenderPlaceholders(usel.value);
  document.getElementById('pr-tpl-del').style.display = '';
  // Cache la galerie en edition (on ne change pas de modele quand on edite un existant)
  document.getElementById('pr-tpl-gallery-row').style.display = 'none';
  // Prefill des dimensions apercu depuis l'imprimante liee si dispo
  const imp = PR.imprimantes.find(x => x.id === t.imprimante_id);
  if (imp) {
    document.getElementById('pr-tpl-prev-w').value = imp.largeur_mm || 102;
    document.getElementById('pr-tpl-prev-h').value = imp.hauteur_mm || 152;
    document.getElementById('pr-tpl-prev-dpi').value = imp.dpi || 203;
  }
  // Reset preview et auto-charge
  prTplClearPreview();
  document.getElementById('pr-tpl-modal').style.display = 'flex';
  setTimeout(() => prTplRefreshPreview(), 200);
}

function prRenderPlaceholders(usageKey) {
  const usage = PR.usages.find(u => u.key === usageKey);
  const root = document.getElementById('pr-tpl-placeholders');
  if (!root) return;
  if (!usage) { root.innerHTML = '<span style="color:var(--muted)">Aucun placeholder défini.</span>'; return; }
  root.innerHTML = usage.placeholders.map(p => {
    const raw = p.startsWith('{{') ? p : `{{${p}}}`;
    return `<button type="button" onclick="prInsertPh('${raw.replace(/'/g,"\\'")}')" style="background:var(--bg);border:1px solid var(--border);border-radius:5px;padding:3px 8px;font-family:monospace;font-size:11px;color:var(--accent);cursor:pointer">${_escH(raw)}</button>`;
  }).join('');
}

function prInsertPh(placeholder) {
  const ta = document.getElementById('pr-tpl-contenu');
  const s = ta.selectionStart, e = ta.selectionEnd;
  ta.value = ta.value.slice(0, s) + placeholder + ta.value.slice(e);
  ta.focus();
  ta.setSelectionRange(s + placeholder.length, s + placeholder.length);
}

function prCloseTplModal() {
  document.getElementById('pr-tpl-modal').style.display = 'none';
  document.getElementById('pr-tpl-usage').disabled = false;
  PR.editingTpl = null;
}

async function prSaveTemplate() {
  const nom = document.getElementById('pr-tpl-nom').value.trim();
  const contenu = document.getElementById('pr-tpl-contenu').value;
  const usage_key = document.getElementById('pr-tpl-usage').value;
  if (!nom) { prToast('Nom requis.', 'danger'); return; }
  if (!contenu.trim()) { prToast('Contenu requis.', 'danger'); return; }
  try {
    if (PR.editingTpl && PR.editingTpl.id) {
      await prFetch('/api/print/templates/' + PR.editingTpl.id, {
        method: 'PATCH', body: JSON.stringify({ nom, contenu }),
      });
      prToast('Template enregistré.');
    } else {
      await prFetch('/api/print/templates', {
        method: 'POST',
        body: JSON.stringify({
          imprimante_id: PR.editingTpl.imprimanteId,
          usage_key, nom, contenu,
        }),
      });
      prToast('Template créé.');
    }
    prCloseTplModal();
    await initPrintersPanel();
  } catch (e) {
    prToast('Erreur : ' + e.message, 'danger');
  }
}

async function prDeleteTemplate() {
  if (!PR.editingTpl || !PR.editingTpl.id) return;
  if (!confirm('Supprimer ce template ?')) return;
  try {
    await prFetch('/api/print/templates/' + PR.editingTpl.id, { method: 'DELETE' });
    prToast('Template supprimé.');
    prCloseTplModal();
    await initPrintersPanel();
  } catch (e) {
    prToast('Erreur : ' + e.message, 'danger');
  }
}

// âââ Galerie de templates prÃ©dÃ©finis (nouveau template) ââââ
let PR_TPL_GALLERY = [];

async function prLoadGallery() {
  const sel = document.getElementById('pr-tpl-gallery');
  const desc = document.getElementById('pr-tpl-gallery-desc');
  if (!sel) return;
  try {
    const r = await prFetch('/api/print/templates/defaults');
    PR_TPL_GALLERY = r.templates || [];
    const opts = ['<option value="">â Vide (je pars de zÃ©ro) â</option>'];
    PR_TPL_GALLERY.forEach(t => {
      opts.push(`<option value="${_escH(t.key)}">${_escH(t.nom)} (${t.largeur_mm}Ã${t.hauteur_mm}mm)</option>`);
    });
    sel.innerHTML = opts.join('');
    sel.value = '';
    if (desc) desc.textContent = 'Choisis un modÃ¨le pour prÃ©remplir le contenu ci-dessous. Tu peux ensuite l\'adapter Ã  ton usage.';
  } catch (e) {
    sel.innerHTML = '<option value="">â Vide â</option>';
    if (desc) desc.textContent = 'Impossible de charger les modÃ¨les prÃ©dÃ©finis.';
  }
}

async function prLoadFromGallery() {
  const sel = document.getElementById('pr-tpl-gallery');
  const desc = document.getElementById('pr-tpl-gallery-desc');
  const key = sel.value;
  if (!key) {
    if (desc) desc.textContent = 'Choisis un modÃ¨le pour prÃ©remplir le contenu ci-dessous.';
    return;
  }
  try {
    const t = await prFetch('/api/print/templates/defaults/' + encodeURIComponent(key));
    if (!document.getElementById('pr-tpl-nom').value.trim()) {
      document.getElementById('pr-tpl-nom').value = t.nom;
    }
    document.getElementById('pr-tpl-contenu').value = t.contenu;
    const usel = document.getElementById('pr-tpl-usage');
    if (t.usage_key) usel.value = t.usage_key;
    document.getElementById('pr-tpl-prev-w').value = t.largeur_mm || 102;
    document.getElementById('pr-tpl-prev-h').value = t.hauteur_mm || 152;
    if (desc) desc.textContent = t.description || '';
    prRenderPlaceholders(usel.value);
    setTimeout(() => prTplRefreshPreview(), 100);
  } catch (e) {
    prToast('Erreur chargement modÃ¨le : ' + e.message, 'danger');
  }
}

// âââ AperÃ§u WYSIWYG du template (via labelary) ââââ
function prTplClearPreview() {
  const img = document.getElementById('pr-tpl-preview-img');
  const ph = document.getElementById('pr-tpl-preview-placeholder');
  const err = document.getElementById('pr-tpl-preview-err');
  if (img) { img.style.display = 'none'; img.src = ''; }
  if (ph) ph.style.display = '';
  if (err) err.textContent = '';
}

async function prTplRefreshPreview() {
  const contenu = document.getElementById('pr-tpl-contenu').value;
  const largeur_mm = parseInt(document.getElementById('pr-tpl-prev-w').value, 10) || 102;
  const hauteur_mm = parseInt(document.getElementById('pr-tpl-prev-h').value, 10) || 152;
  const dpi = parseInt(document.getElementById('pr-tpl-prev-dpi').value, 10) || 203;
  const img = document.getElementById('pr-tpl-preview-img');
  const ph = document.getElementById('pr-tpl-preview-placeholder');
  const err = document.getElementById('pr-tpl-preview-err');
  if (!contenu.trim()) {
    err.textContent = 'Le contenu est vide.';
    return;
  }
  err.textContent = 'GÃ©nÃ©ration de l\'aperÃ§uâ¦';
  err.style.color = 'var(--muted)';
  try {
    const r = await fetch('/api/print/preview', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contenu, langage: 'zpl', largeur_mm, hauteur_mm, dpi }),
    });
    if (!r.ok) {
      let msg = 'HTTP ' + r.status;
      try { const j = await r.json(); if (j.detail) msg = j.detail; } catch(e){}
      throw new Error(msg);
    }
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    if (img) {
      img.onload = () => { URL.revokeObjectURL(url); };
      img.src = url;
      img.style.display = '';
    }
    if (ph) ph.style.display = 'none';
    err.textContent = `AperÃ§u ${largeur_mm}Ã${hauteur_mm}mm @ ${dpi}dpi (rendu labelary.com)`;
    err.style.color = 'var(--muted)';
  } catch (e) {
    err.textContent = 'Erreur aperÃ§u : ' + e.message;
    err.style.color = 'var(--danger)';
  }
}

// ─── Agents ─────────────────────────────────────────────────────
function prRenderAgents() {
  const root = document.getElementById('pr-ag-list');
  if (!root) return;
  if (!PR.agents.length) {
    root.innerHTML = '<div style="padding:24px;text-align:center;color:var(--muted);font-size:13px;background:var(--card);border:1px dashed var(--border);border-radius:12px">Aucun agent local configuré. Crée un agent pour connecter un poste de l\'usine.</div>';
    return;
  }
  const now = Date.now();
  root.innerHTML = PR.agents.map(a => {
    const hb = a.last_heartbeat ? new Date(a.last_heartbeat) : null;
    const ageMin = hb ? Math.round((now - hb.getTime()) / 60000) : null;
    let live;
    if (!hb) live = '<span style="color:var(--muted);font-size:11px">Jamais connecté</span>';
    else if (ageMin < 3) live = '<span style="display:inline-flex;align-items:center;gap:6px;color:var(--success);font-size:11px"><span style="width:8px;height:8px;border-radius:50%;background:var(--success);display:inline-block"></span>En ligne</span>';
    else live = `<span style="color:var(--warn);font-size:11px">Hors ligne (${ageMin}min)</span>`;
    return `
      <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px 16px;display:flex;align-items:center;gap:12px">
        <div style="flex:1;min-width:0">
          <div style="display:flex;align-items:center;gap:10px">
            <span style="font-size:14px;font-weight:700;color:var(--text)">${_escH(a.nom)}</span>
            ${live}
          </div>
          <div style="font-size:11px;color:var(--muted);margin-top:4px">
            ${a.last_ip ? 'IP: ' + _escH(a.last_ip) + ' · ' : ''}Créé le ${_escH((a.created_at || '').slice(0,10))}
          </div>
        </div>
        <button class="btn btn-ghost" style="padding:6px 12px;font-size:12px;color:var(--danger)" onclick="prDeleteAgent(${a.id})">Supprimer</button>
      </div>`;
  }).join('');
}

async function prCreateAgent() {
  const nom = prompt('Nom de l\'agent (ex : Pi-Réception) :');
  if (!nom || !nom.trim()) return;
  try {
    const r = await prFetch('/api/print/agents', {
      method: 'POST', body: JSON.stringify({ nom: nom.trim() }),
    });
    // Reveal token
    const reveal = document.getElementById('pr-ag-token-reveal');
    const val = document.getElementById('pr-ag-token-value');
    val.textContent = r.token;
    reveal.style.display = '';
    prToast('Agent créé. Copie le token maintenant.', 'success');
    await initPrintersPanel();
  } catch (e) {
    prToast('Erreur : ' + e.message, 'danger');
  }
}

function prCopyToken() {
  const val = document.getElementById('pr-ag-token-value').textContent;
  if (navigator.clipboard) navigator.clipboard.writeText(val).then(() => prToast('Token copié.'));
  else {
    const ta = document.createElement('textarea');
    ta.value = val; document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); prToast('Token copié.'); } catch(e) {}
    document.body.removeChild(ta);
  }
}

async function prDeleteAgent(id) {
  if (!confirm('Supprimer cet agent ? Les imprimantes rattachées perdront leur agent (à réaffecter).')) return;
  try {
    await prFetch('/api/print/agents/' + id, { method: 'DELETE' });
    prToast('Agent supprimé.');
    await initPrintersPanel();
  } catch (e) {
    prToast('Erreur : ' + e.message, 'danger');
  }
}

// Styles utilitaires pour la modale printers
(function _prInjectCss(){
  const s = document.createElement('style');
  s.textContent = `
    .pr-lbl{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px}
    .pr-inp{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:9px 12px;color:var(--text);font-size:13px;box-sizing:border-box;font-family:inherit;outline:none}
    .pr-inp:focus{border-color:var(--accent)}
  `;
  document.head.appendChild(s);
})();

</script>
<script>
// ─── Formations & guides in-app (admin) ────────────────────────────
let _fmtData = null;
let _fmtSearch = '';
let _fmtStatus = '';

async function loadFormationsAdmin(){
  try {
    // api() dans settings_page retourne le JSON parse directement (pas un Response)
    _fmtData = await api('/api/guides/admin/overview');
    renderFormationsAdmin();
  } catch(e){ toast('Erreur chargement : ' + (e.message||''), true); }
}

function _fmtStatusPill(status){
  if(status==='acked') return '<span style="display:inline-flex;align-items:center;gap:5px;padding:2px 8px;border-radius:999px;background:rgba(52,211,153,.15);color:var(--ok);font-size:11px;font-weight:700">✓ Validé</span>';
  if(status==='completed') return '<span style="display:inline-flex;align-items:center;gap:5px;padding:2px 8px;border-radius:999px;background:rgba(34,211,238,.15);color:var(--accent);font-size:11px;font-weight:700">Complété</span>';
  if(status==='in_progress') return '<span style="display:inline-flex;align-items:center;gap:5px;padding:2px 8px;border-radius:999px;background:rgba(251,191,36,.15);color:var(--warn);font-size:11px;font-weight:700">En cours</span>';
  if(status==='open') return '<span style="display:inline-flex;align-items:center;gap:5px;padding:2px 8px;border-radius:999px;background:rgba(148,163,184,.18);color:var(--muted);font-size:11px;font-weight:700">Ouvert</span>';
  return '<span style="color:var(--muted);font-size:11px">Jamais ouvert</span>';
}

function _fmtTimeMs(ms){
  const s = Math.floor((ms||0) / 1000);
  if(s < 60) return s + 's';
  const m = Math.floor(s/60); const rs = s%60;
  if(m < 60) return m + 'min ' + rs + 's';
  const h = Math.floor(m/60); const rm = m%60;
  return h + 'h' + String(rm).padStart(2,'0');
}

function _fmtDate(iso){
  if(!iso) return '—';
  try{ const d = new Date(iso.replace(' ','T')); return d.toLocaleDateString('fr-FR', {day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit'}); }catch(e){ return iso; }
}

// Guides connus (label lisible)
const _FMT_GUIDES = {
  'qualite-overview': 'MyQualité — Vue d\'ensemble',
  'ressources': 'Ressources fournisseurs',
  'nc-list': 'MyQualité — Non-conformités',
  'audits': 'MyQualité — Audits client',
  'ref-rse': 'MyQualité — Référentiel RSE',
};

function _fmtGuideLabel(key){ return _FMT_GUIDES[key] || key; }

// Rôles utilisateur : liste synthétique
function _fmtRoleLabel(r){
  const m = {
    superadmin: 'Super admin', direction: 'Direction',
    administration: 'Administration', administration_ventes: 'Admin. ventes',
    administration_technique: 'Admin. technique', fabrication: 'Fabrication',
    commercial: 'Commercial', logistique: 'Logistique', expedition: 'Expédition',
    comptabilite: 'Comptabilité',
  };
  return m[r] || r || '—';
}

function renderFormationsAdmin(){
  if(!_fmtData) return;
  const users = _fmtData.users || [];
  const progress = _fmtData.progress || [];
  const progByUser = new Map();
  for(const p of progress){
    if(!progByUser.has(p.user_id)) progByUser.set(p.user_id, []);
    progByUser.get(p.user_id).push(p);
  }
  // Guides connus, y compris les valeurs presentes dans progress
  const guideKeys = new Set(Object.keys(_FMT_GUIDES));
  for(const p of progress) guideKeys.add(p.guide_key);
  const guides = Array.from(guideKeys);

  const q = _fmtSearch.toLowerCase();
  const rows = [];
  for(const u of users){
    const uProg = progByUser.get(u.id) || [];
    for(const gk of guides){
      const p = uProg.find(x => x.guide_key === gk);
      const status = p ? p.status : 'never';
      // Filter status
      if(_fmtStatus && status !== _fmtStatus) continue;
      const uName = `${u.prenom||''} ${u.nom||''}`.trim() || u.email || ('#'+u.id);
      const gLabel = _fmtGuideLabel(gk);
      // Filter search (matche user + role + guide)
      if(q){
        const hay = (uName + ' ' + (u.email||'') + ' ' + _fmtRoleLabel(u.role) + ' ' + gLabel + ' ' + gk).toLowerCase();
        if(!hay.includes(q)) continue;
      }
      rows.push({user:u, guide:gk, gLabel, prog:p, status, uName});
    }
  }

  const tbody = document.getElementById('fmt-tbody');
  if(!tbody) return;
  if(!rows.length){
    tbody.innerHTML = '<tr><td colspan="10" style="text-align:center;color:var(--muted);padding:24px">Aucun résultat</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(r => {
    const p = r.prog;
    const stepsHtml = p && p.total_steps > 0
      ? `${p.steps_seen}/${p.total_steps}`
      : '—';
    const time = p ? _fmtTimeMs(p.total_time_ms) : '—';
    const openCount = p ? (p.open_count || 0) : 0;
    const canReset = !!p;
    return `<tr>
      <td><strong>${esc(r.uName)}</strong>${r.user.email?`<div style="font-size:11px;color:var(--muted)">${esc(r.user.email)}</div>`:''}</td>
      <td style="font-size:12px;color:var(--text2)">${esc(_fmtRoleLabel(r.user.role))}</td>
      <td>${esc(r.gLabel)}<div style="font-size:10px;color:var(--muted);font-family:ui-monospace,monospace">${esc(r.guide)}</div></td>
      <td>${_fmtStatusPill(r.status)}</td>
      <td style="font-family:ui-monospace,monospace;font-size:12px">${stepsHtml}</td>
      <td style="font-family:ui-monospace,monospace;font-size:12px">${time}</td>
      <td style="font-family:ui-monospace,monospace;font-size:12px;text-align:center">${openCount}</td>
      <td style="font-size:11px;color:var(--text2)">${_fmtDate(p && p.opened_at)}</td>
      <td style="font-size:11px;color:var(--text2)">${_fmtDate(p && p.acknowledged_at)}</td>
      <td style="text-align:right">${canReset ? `<button type="button" class="btn btn-sec btn-sm" onclick="resetFormation(${r.user.id}, '${esc(r.guide)}', '${esc(r.uName.replace(/'/g,"\\'"))}', '${esc(r.gLabel.replace(/'/g,"\\'"))}')">Reset</button>` : '<span style="color:var(--muted);font-size:11px">—</span>'}</td>
    </tr>`;
  }).join('');
}

async function resetFormation(userId, guideKey, uName, gLabel){
  if(!confirm(`Réinitialiser la progression du guide « ${gLabel} » pour ${uName} ?\n\nL'utilisateur reverra le tuto à sa prochaine visite.`)) return;
  try {
    await api('/api/guides/admin/reset', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({user_id: userId, guide_key: guideKey})
    });
    toast('Progression remise à zéro');
    await loadFormationsAdmin();
  } catch(e){ toast('Erreur réinitialisation : ' + (e.message||''), true); }
}

// Wire up filtres
try {
  const s = document.getElementById('fmt-search');
  if(s) s.oninput = () => { _fmtSearch = s.value; renderFormationsAdmin(); };
  const st = document.getElementById('fmt-filter-status');
  if(st) st.onchange = () => { _fmtStatus = st.value; renderFormationsAdmin(); };
  const rf = document.getElementById('fmt-refresh');
  if(rf) rf.onclick = () => loadFormationsAdmin();
} catch(e){}


// ─── Appairage matières (bridge MyStock <-> Coûts matières) ────────────
let _bridgeCache = null;

async function initBridgePanel() {
  const btn = document.getElementById('bridge-refresh');
  if (btn && !btn._wired) {
    btn._wired = true;
    btn.addEventListener('click', () => loadBridge(true));
  }
  await loadBridge(false);
}

async function loadBridge(force) {
  const sum = document.getElementById('bridge-summary');
  if (sum) sum.innerHTML = '<span>Chargement…</span>';
  try {
    const r = await fetch('/api/pricing/bridge/orphans', { credentials: 'include' });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    _bridgeCache = await r.json();
  } catch (e) {
    if (sum) sum.innerHTML = '<span style="color:var(--danger)">Erreur de chargement : ' + (e && e.message || e) + '</span>';
    return;
  }
  renderBridge();
}

function renderBridge() {
  const data = _bridgeCache || { mp: [], mc: [] };
  const sum = document.getElementById('bridge-summary');
  if (sum) {
    sum.innerHTML =
      '<span><strong>' + data.mp.length + '</strong> matière(s) MyStock à appairer</span>' +
      '<span style="color:var(--muted)">·</span>' +
      '<span><strong>' + data.mc.length + '</strong> matière(s) Coûts matières sans référence MyStock</span>';
  }
  _renderBridgeMpList(data.mp);
  _renderBridgeMcList(data.mc);
}

function _bridgeEsc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function _renderBridgeMpList(items) {
  const host = document.getElementById('bridge-orphans-mp');
  const empty = document.getElementById('bridge-orphans-mp-empty');
  if (!host) return;
  host.innerHTML = '';
  if (!items || items.length === 0) {
    if (empty) empty.style.display = 'block';
    return;
  }
  if (empty) empty.style.display = 'none';
  items.forEach(mp => {
    const row = document.createElement('div');
    row.style.cssText = 'display:flex;align-items:center;gap:12px;padding:10px 12px;background:var(--card);border:1px solid var(--border);border-radius:8px';
    row.innerHTML =
      '<div style="flex:1;min-width:0">' +
        '<div style="font-weight:600;font-size:13px;color:var(--text)">' + _bridgeEsc(mp.reference) + ' — ' + _bridgeEsc(mp.designation) + '</div>' +
        '<div style="font-size:11px;color:var(--muted);margin-top:2px">' +
          _bridgeEsc(mp.categorie) + (mp.pricing_role ? ' · rôle ' + _bridgeEsc(mp.pricing_role) : '') +
          (mp.sous_section ? ' · ' + _bridgeEsc(mp.sous_section) : '') +
          (mp.couleur ? ' · ' + _bridgeEsc(mp.couleur) : '') +
        '</div>' +
      '</div>' +
      '<button type="button" class="btn btn-sec" data-mp-id="' + mp.id + '">Rapprocher…</button>';
    row.querySelector('button').addEventListener('click', () => openBridgeSuggestModal(mp));
    host.appendChild(row);
  });
}

function _renderBridgeMcList(items) {
  const host = document.getElementById('bridge-orphans-mc');
  const empty = document.getElementById('bridge-orphans-mc-empty');
  if (!host) return;
  host.innerHTML = '';
  if (!items || items.length === 0) {
    if (empty) empty.style.display = 'block';
    return;
  }
  if (empty) empty.style.display = 'none';
  items.forEach(mc => {
    const row = document.createElement('div');
    row.style.cssText = 'display:flex;align-items:center;gap:12px;padding:10px 12px;background:var(--card);border:1px solid var(--border);border-radius:8px';
    const price = (mc.unit_price != null) ? (Number(mc.unit_price).toFixed(4) + ' ' + (mc.price_currency || 'EUR') + '/' + (mc.price_basis === 'PER_M2' ? 'm²' : 'kg')) : '—';
    row.innerHTML =
      '<div style="flex:1;min-width:0">' +
        '<div style="font-weight:600;font-size:13px;color:var(--text)">' + _bridgeEsc(mc.name) + '</div>' +
        '<div style="font-size:11px;color:var(--muted);margin-top:2px">' +
          _bridgeEsc(mc.category_code) +
          (mc.appellation_code ? ' · code ' + _bridgeEsc(mc.appellation_code) : '') +
          ' · ' + price +
        '</div>' +
      '</div>' +
      '<span class="sub" style="font-size:11px;color:var(--muted)">Aucun mp lié</span>';
    host.appendChild(row);
  });
}

async function openBridgeSuggestModal(mp) {
  // Modal dédié (jamais on ne fait innerHTML='' sur document.body).
  const existing = document.getElementById('bridge-modal-overlay');
  if (existing) existing.remove();
  const modal = document.createElement('div');
  modal.id = 'bridge-modal-overlay';
  modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.5);display:flex;align-items:center;justify-content:center;z-index:9999;padding:20px';
  modal.innerHTML =
    '<div style="background:var(--card);border:1px solid var(--border);border-radius:12px;max-width:720px;width:100%;max-height:85vh;overflow:hidden;display:flex;flex-direction:column">' +
      '<div style="padding:16px 18px;border-bottom:1px solid var(--border)">' +
        '<div style="font-weight:700;font-size:15px;color:var(--text)">Appairer avec une matière Coûts matières</div>' +
        '<div style="font-size:12px;color:var(--muted);margin-top:4px">' + _bridgeEsc(mp.reference) + ' — ' + _bridgeEsc(mp.designation) + '</div>' +
        '<input type="search" id="bridge-sugg-search" placeholder="Filtrer (nom, appellation, catégorie…)" ' +
          'style="width:100%;margin-top:12px;padding:9px 12px;border-radius:8px;border:1.5px solid var(--border);background:var(--bg);color:var(--text);font-size:13px;outline:none">' +
      '</div>' +
      '<div id="bridge-sugg-body" style="flex:1;overflow:auto;padding:12px 18px">' +
        '<div class="sub" style="font-size:13px;color:var(--muted)">Chargement des propositions…</div>' +
      '</div>' +
      '<div style="padding:12px 18px;border-top:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;gap:8px">' +
        '<span id="bridge-sugg-count" class="sub" style="font-size:11px;color:var(--muted)"></span>' +
        '<button type="button" class="btn btn-sec" id="bridge-sugg-close">Annuler</button>' +
      '</div>' +
    '</div>';
  document.body.appendChild(modal);

  const close = () => { try { modal.remove(); } catch(e) {} };
  modal.querySelector('#bridge-sugg-close').addEventListener('click', close);
  modal.addEventListener('click', (e) => { if (e.target === modal) close(); });
  const searchInput = modal.querySelector('#bridge-sugg-search');
  const countLabel = modal.querySelector('#bridge-sugg-count');

  let allSugg = [];
  try {
    const r = await fetch('/api/pricing/bridge/suggest/' + mp.id, { credentials: 'include' });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const data = await r.json();
    allSugg = data.suggestions || [];
  } catch (e) {
    modal.querySelector('#bridge-sugg-body').innerHTML = '<div class="sub" style="color:var(--danger);font-size:13px">Erreur : ' + _bridgeEsc(e && e.message || e) + '</div>';
    return;
  }

  const body = modal.querySelector('#bridge-sugg-body');
  const _renderList = (items) => {
    if (items.length === 0) {
      body.innerHTML = '<div class="sub" style="font-size:13px">Aucun résultat pour ce filtre.</div>';
      countLabel.textContent = '0 sur ' + allSugg.length + ' matière(s)';
      return;
    }
    body.innerHTML = '';
    items.forEach(s => {
      const item = document.createElement('div');
      const highlight = (s._score || 0) >= 15;
      item.style.cssText = 'display:flex;align-items:center;gap:12px;padding:10px 12px;background:var(--bg);border:1px solid ' + (highlight ? 'var(--accent)' : 'var(--border)') + ';border-radius:8px;margin-bottom:6px';
      const price = (s.unit_price != null) ? (Number(s.unit_price).toFixed(4) + ' ' + (s.price_currency || 'EUR') + '/' + (s.price_basis === 'PER_M2' ? 'm²' : 'kg')) : '—';
      const scoreBadge = highlight ? '<span style="background:var(--accent-bg);color:var(--accent);padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;margin-left:6px">MATCH</span>' : '';
      item.innerHTML =
        '<div style="flex:1;min-width:0">' +
          '<div style="font-weight:600;font-size:13px;color:var(--text)">' + _bridgeEsc(s.name) + scoreBadge + '</div>' +
          '<div style="font-size:11px;color:var(--muted);margin-top:2px">' + _bridgeEsc(s.category_code) + (s.appellation_code ? ' · code ' + _bridgeEsc(s.appellation_code) : '') + ' · ' + price + '</div>' +
        '</div>' +
        '<button type="button" class="btn" data-mc-id="' + s.id + '">Appairer</button>';
      item.querySelector('button').addEventListener('click', async () => {
        await linkBridge(mp.id, s.id);
        close();
      });
      body.appendChild(item);
    });
    countLabel.textContent = items.length + ' sur ' + allSugg.length + ' matière(s)';
  };

  const _filter = (query) => {
    const q = (query || '').trim().toLowerCase();
    if (!q) return _renderList(allSugg);
    const filtered = allSugg.filter(s =>
      (s.name || '').toLowerCase().includes(q) ||
      (s.appellation_code || '').toLowerCase().includes(q) ||
      (s.category_code || '').toLowerCase().includes(q)
    );
    _renderList(filtered);
  };

  searchInput.addEventListener('input', (e) => _filter(e.target.value));
  // Autofocus + rendu initial
  _renderList(allSugg);
  requestAnimationFrame(() => searchInput.focus());
}
async function linkBridge(mp_id, mc_id) {
  try {
    const r = await fetch('/api/pricing/bridge/link', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mp_id, mc_id }),
    });
    if (!r.ok) {
      const err = await r.text();
      throw new Error(err || ('HTTP ' + r.status));
    }
    if (typeof showToast === 'function') showToast('Appairage enregistré.', 'success');
    await loadBridge(true);
  } catch (e) {
    if (typeof showToast === 'function') showToast('Erreur : ' + (e && e.message || e), 'danger');
    else alert('Erreur : ' + (e && e.message || e));
  }
}

async function unlinkBridge(mp_id) {
  if (!confirm('Casser le lien avec Coûts matières ? Les caractéristiques déjà copiées côté MyStock restent.')) return;
  try {
    const r = await fetch('/api/pricing/bridge/link/' + mp_id, {
      method: 'DELETE',
      credentials: 'include',
    });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    if (typeof showToast === 'function') showToast('Lien supprimé.', 'success');
    await loadBridge(true);
  } catch (e) {
    if (typeof showToast === 'function') showToast('Erreur : ' + (e && e.message || e), 'danger');
    else alert('Erreur : ' + (e && e.message || e));
  }
}

</script>
<script src="/static/mysifa_impersonate.js"></script>
</body>
</html>
"""

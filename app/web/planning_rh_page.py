"""MySifa — Planning RH (Personnel) v1.0

Route : /planning-rh
Vue configurateur (direction/superadmin) : grille semaines × postes/machines,
  gestion congés, navigation multi-semaines, impression.
Vue opérateur (fabrication/logistique) : planning personnel hebdomadaire.
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from app.services.auth_service import get_current_user
from config import ROLES_PLANNING_RH_VIEW

router = APIRouter()


@router.get("/planning-rh", response_class=HTMLResponse)
def planning_rh_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/planning-rh", status_code=302)
        raise
    from app.services.auth_service import user_has_app_access
    if not user_has_app_access(user, "planning_rh"):
        from app.web.access_denied import access_denied_response
        return access_denied_response("Planning RH")
    return HTMLResponse(
        content=PLANNING_RH_HTML,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


PLANNING_RH_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#0a0e17">
<title>Planning RH — MySifa</title>
<link rel="icon" type="image/png" sizes="512x512" href="/static/mys_icon_512.png">
<link rel="apple-touch-icon" href="/static/mys_icon_180.png">
<style>
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;
  --muted:#94a3b8;--accent:#22d3ee;--accent-bg:rgba(34,211,238,.12);
  --success:#34d399;--warn:#fbbf24;--danger:#f87171;
  --c1:#38bdf8;--c2:#a78bfa;--c3:#34d399;--c4:#fbbf24;--c5:#f87171;
  --sidebar-w:220px;
}
body.light{
  --bg:#f1f5f9;--card:#fff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;
  --muted:#94a3b8;--accent:#0891b2;--accent-bg:rgba(8,145,178,.10);
  --success:#059669;--warn:#d97706;--danger:#dc2626;--c2:#7c3aed;
}
html,body{height:100%;overflow:hidden}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text)}
::-webkit-scrollbar{width:5px;height:5px}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
button:focus:not(:focus-visible){outline:none}
input,select,textarea{font-family:inherit;color:var(--text)}

/* ── Layout ──────────────────────────────────────────── */
#root{display:flex;height:100vh;overflow:hidden}

/* ── Sidebar ──────────────────────────────────────────── */
.rh-sb{
  width:var(--sidebar-w);flex-shrink:0;
  background:var(--card);border-right:1px solid var(--border);
  display:flex;flex-direction:column;overflow:hidden;height:100vh;
}
.rh-sb-head{padding:16px 14px 12px;border-bottom:1px solid var(--border);flex-shrink:0}
.rh-sb-brand{font-size:15px;font-weight:800;line-height:1.2}
.rh-sb-brand span{color:var(--accent)}
.rh-sb-sub{font-size:10px;color:var(--muted);letter-spacing:1.2px;text-transform:uppercase;margin-top:2px}
.rh-sb-nav{flex:1;overflow-y:auto;padding:8px 6px}
.rh-nav-btn{
  display:flex;align-items:center;gap:9px;width:100%;padding:9px 10px;
  border-radius:8px;border:none;background:transparent;
  color:var(--text2);cursor:pointer;font-size:13px;font-weight:500;
  font-family:inherit;transition:all .15s;margin-bottom:2px;text-align:left;
}
.rh-nav-btn:hover,.rh-nav-btn.active{background:var(--accent-bg);color:var(--accent)}
.rh-sb-bot{margin-top:auto;padding:10px 6px 12px;border-top:1px solid var(--border);display:flex;flex-direction:column;gap:6px}
.rh-user-chip{padding:8px 10px;border-radius:8px;background:var(--accent-bg)}
.rh-user-chip .ucn{font-size:12px;font-weight:600;color:var(--text)}
.rh-user-chip .ucr{font-size:10px;color:var(--accent);text-transform:uppercase;letter-spacing:.5px}
.rh-theme-btn,.rh-back-btn{
  display:flex;align-items:center;gap:5px;padding:6px 10px;border-radius:10px;
  border:none;background:transparent;color:var(--text2);cursor:pointer;
  font-size:13px;font-weight:600;font-family:inherit;transition:background .1s
}
.rh-theme-btn:hover,.rh-back-btn:hover{background:var(--accent-bg);color:var(--accent)}
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
.rh-back-btn:hover{color:var(--danger);background:rgba(248,113,113,.08);border-color:var(--danger)}

/* ── Main ──────────────────────────────────────────── */
.rh-main{flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0}
.rh-hdr{
  padding:14px 20px 12px;border-bottom:1px solid var(--border);
  display:flex;align-items:center;gap:12px;flex-wrap:wrap;flex-shrink:0;
  background:var(--card);
}
.rh-hdr-title{font-size:18px;font-weight:800;flex:1;min-width:120px}
.rh-hdr-title span{color:var(--accent)}
.rh-hdr-right{display:flex;align-items:center;gap:8px;flex-wrap:wrap}

/* Nav semaines */
.rh-wk-nav{display:flex;align-items:center;gap:0}
.rh-wk-nav button{
  padding:6px 10px;background:var(--card);border:1px solid var(--border);
  color:var(--text2);cursor:pointer;font-size:13px;font-family:inherit;
  transition:all .15s;
}
.rh-wk-nav button:first-child{border-radius:8px 0 0 8px}
.rh-wk-nav button:last-child{border-radius:0 8px 8px 0}
.rh-wk-nav button:not(:first-child){margin-left:-1px}
.rh-wk-nav button:hover{background:var(--accent-bg);color:var(--accent);border-color:var(--accent);z-index:1;position:relative}
.rh-wk-today{font-size:11px;padding:6px 12px!important}

/* Range tabs */
.rh-range-tabs{display:flex;align-items:center;gap:0}
.rh-range-tab{
  padding:6px 12px;background:var(--card);border:1px solid var(--border);
  color:var(--text2);cursor:pointer;font-size:12px;font-weight:600;
  font-family:inherit;transition:all .15s;
}
.rh-range-tab:first-child{border-radius:8px 0 0 8px}
.rh-range-tab:last-child{border-radius:0 8px 8px 0}
.rh-range-tab:not(:first-child){margin-left:-1px}
.rh-range-tab.active{background:var(--accent-bg);color:var(--accent);border-color:var(--accent);z-index:1;position:relative}
.rh-range-tab:hover:not(.active){background:var(--border)}

/* Print + detail btns */
.rh-icon-btn{
  display:inline-flex;align-items:center;justify-content:center;gap:6px;
  padding:6px 12px;border-radius:8px;border:1px solid var(--border);
  background:var(--card);color:var(--text2);cursor:pointer;font-size:12px;
  font-family:inherit;font-weight:600;transition:all .15s;white-space:nowrap;
}
.rh-icon-btn:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.rh-icon-btn.active{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}

/* ── Content ──────────────────────────────────────────── */
.rh-content{flex:1;overflow:auto;padding:16px 20px}

/* ── Planning grid ──────────────────────────────────── */
.rh-grid-wrap{overflow:auto;border-radius:12px;border:1px solid var(--border)}
.rh-grid{border-collapse:collapse;width:100%;min-width:600px}
.rh-grid th,.rh-grid td{border:1px solid var(--border)}
.rh-grid thead th{
  background:var(--card);padding:10px 12px;font-size:11px;
  font-weight:700;text-transform:uppercase;letter-spacing:.7px;
  color:var(--muted);text-align:center;position:sticky;top:0;z-index:5;
  white-space:nowrap;
}
.rh-grid thead th.rh-poste-col{text-align:left;width:180px;position:sticky;left:0;z-index:6;background:var(--card)}
.rh-grid thead th.rh-week-col{min-width:160px}
.rh-week-num{font-size:13px;font-weight:800;color:var(--text)}
.rh-week-dates{font-size:10px;color:var(--muted);margin-top:2px}
.rh-week-col.current-week{background:var(--accent-bg)!important}
.rh-week-col.current-week .rh-week-num{color:var(--accent)}

/* Machine section header */
.rh-machine-hdr td{
  padding:8px 12px;font-size:12px;font-weight:800;
  text-transform:uppercase;letter-spacing:1px;
  background:var(--bg);color:var(--text2);
}
.rh-machine-dot{
  display:inline-block;width:8px;height:8px;border-radius:50%;
  margin-right:8px;vertical-align:middle;
}

/* Créneau subheader */
.rh-creneau-hdr td{
  padding:5px 12px 5px 20px;font-size:10px;font-weight:700;
  text-transform:uppercase;letter-spacing:.8px;
  background:var(--card);color:var(--muted);
}
.rh-creneau-hdr .rh-creneau-hrs{font-weight:400;font-size:9px;opacity:.7;margin-left:6px}

/* Poste row */
.rh-poste-row td{
  padding:6px 8px;vertical-align:middle;background:var(--bg);
}
.rh-poste-label{
  padding:6px 12px 6px 28px!important;font-size:12px;font-weight:600;
  color:var(--text2);white-space:nowrap;
  position:sticky;left:0;z-index:2;background:var(--bg)!important;
  vertical-align:middle;
}
.rh-poste-label-inner{
  display:flex;align-items:center;justify-content:space-between;gap:8px;
}
.rh-label-content{flex:1}
.rh-cell{min-height:36px;display:flex;flex-wrap:wrap;gap:5px;align-items:center;padding:4px 6px}
.rh-chip{
  display:inline-flex;align-items:center;gap:5px;padding:4px 8px;
  border-radius:20px;font-size:12px;font-weight:600;background:var(--accent-bg);
  color:var(--accent);border:1px solid rgba(34,211,238,.25);
  transition:all .15s;white-space:nowrap;
}
.rh-chip.warn{background:rgba(251,191,36,.12);color:var(--warn);border-color:rgba(251,191,36,.3)}
.rh-chip-del{
  display:inline-flex;align-items:center;justify-content:center;
  width:14px;height:14px;border-radius:50%;border:none;background:transparent;
  color:inherit;cursor:pointer;font-size:11px;opacity:.7;padding:0;
  transition:opacity .15s;
}
.rh-chip-del:hover{opacity:1}
.rh-add-btn{
  display:inline-flex;align-items:center;justify-content:center;
  width:26px;height:26px;border-radius:8px;border:1px dashed var(--border);
  background:transparent;color:var(--muted);cursor:pointer;font-size:16px;
  transition:all .15s;
}
.rh-add-btn:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.rh-dup-btn{
  display:inline-flex;align-items:center;justify-content:center;
  width:22px;height:22px;border-radius:6px;border:1px solid var(--success);
  background:var(--success-bg);color:var(--success);cursor:pointer;font-size:14px;
  transition:all .15s;margin-left:4px;
}
.rh-dup-btn:hover{background:var(--success);color:var(--bg)}
.rh-sep-row{border:none}
.rh-sep-cell{
  padding:8px 12px;background:var(--accent-bg);border:1px solid var(--border);
  text-align:center;
}
.rh-sep-dup-btn{
  background:var(--card);border:1px solid var(--accent);color:var(--accent);
  border-radius:8px;padding:6px 12px;font-size:12px;font-weight:600;
  cursor:pointer;display:inline-flex;align-items:center;gap:6px;
  transition:all .15s;
}
.rh-sep-dup-btn:hover{background:var(--accent);color:var(--bg)}
.rh-sep-dup-icon{font-size:14px}
.rh-machine-toolbar{
  display:flex;gap:8px;padding:8px 12px;background:var(--bg);
  border-bottom:1px solid var(--border);
}
.rh-toolbar-btn{
  background:var(--card);border:1px solid var(--border);color:var(--text);
  border-radius:6px;padding:6px 12px;font-size:12px;font-weight:600;
  cursor:pointer;display:inline-flex;align-items:center;gap:6px;
  transition:all .15s;
}
.rh-toolbar-btn:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.rh-toolbar-icon{font-size:14px}
.rh-row-dup-btn{
  background:transparent;border:1px solid #666;color:#666;
  border-radius:4px;width:18px;height:18px;font-size:12px;font-weight:700;
  cursor:pointer;display:inline-flex;align-items:center;justify-content:center;
  transition:all .15s;
}
.rh-row-dup-btn:hover{border-color:var(--accent);color:var(--accent)}
.rh-row-btns{
  display:inline-flex;gap:4px;margin-left:8px;vertical-align:middle;
}
.rh-row-del-btn{
  background:transparent;border:1px solid #666;color:#666;
  border-radius:4px;width:18px;height:18px;font-size:14px;font-weight:700;
  cursor:pointer;display:inline-flex;align-items:center;justify-content:center;
  transition:all .15s;
}
.rh-row-del-btn:hover{border-color:var(--danger);color:var(--danger)}

/* Congé indicator on cell */
.rh-conge-badge{
  display:inline-flex;align-items:center;gap:4px;padding:3px 7px;
  border-radius:20px;font-size:11px;font-weight:600;
  background:rgba(251,191,36,.12);color:var(--warn);
  border:1px solid rgba(251,191,36,.25);white-space:nowrap;
}

/* ── Congés tab ──────────────────────────────────────── */
.rh-conges-wrap{display:flex;flex-direction:column;gap:20px}
.rh-section{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden}
.rh-section-hdr{
  padding:12px 16px;border-bottom:1px solid var(--border);
  display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;
}
.rh-section-title{font-size:13px;font-weight:700;color:var(--text2);text-transform:uppercase;letter-spacing:.7px}
.rh-table{width:100%;border-collapse:collapse}
.rh-table th{
  padding:9px 12px;font-size:10px;font-weight:700;text-transform:uppercase;
  letter-spacing:.6px;color:var(--muted);background:var(--bg);text-align:left;
  border-bottom:1px solid var(--border);
}
.rh-table td{padding:9px 12px;font-size:13px;border-bottom:1px solid var(--border);vertical-align:middle}
.rh-table tr:last-child td{border-bottom:none}
.rh-table tr:hover td{background:rgba(255,255,255,.02)}
body.light .rh-table tr:hover td{background:rgba(0,0,0,.02)}
.rh-solde-bar{
  display:flex;align-items:center;gap:8px;
}
.rh-bar-wrap{flex:1;height:6px;background:var(--border);border-radius:3px;overflow:hidden;min-width:60px}
.rh-bar-fill{height:100%;border-radius:3px;background:var(--success);transition:width .3s}
.rh-bar-fill.warn{background:var(--warn)}
.rh-bar-fill.danger{background:var(--danger)}
.rh-badge{
  display:inline-flex;align-items:center;padding:2px 8px;border-radius:10px;
  font-size:11px;font-weight:600;
}
.rh-badge.cp{background:var(--accent-bg);color:var(--accent)}
.rh-badge.rtt{background:rgba(167,139,250,.12);color:var(--c2)}
.rh-badge.mal{background:rgba(248,113,113,.12);color:var(--danger)}
.rh-badge.aut{background:rgba(148,163,184,.12);color:var(--muted)}
.rh-badge.pose{background:rgba(251,191,36,.12);color:var(--warn)}
.rh-badge.valide{background:rgba(52,211,153,.12);color:var(--success)}
.rh-badge.refuse{background:rgba(248,113,113,.12);color:var(--danger)}
.rh-act-btn{
  padding:4px 10px;border-radius:6px;border:1px solid var(--border);
  background:transparent;color:var(--text2);cursor:pointer;font-size:11px;
  font-family:inherit;font-weight:600;transition:all .15s;
}
.rh-act-btn:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.rh-act-btn.del:hover{border-color:var(--danger);color:var(--danger);background:rgba(248,113,113,.08)}
.rh-empty{text-align:center;padding:32px;color:var(--muted);font-size:13px}

/* ── Toast ──────────────────────────────────────────── */
#rh-toast{
  position:fixed;bottom:24px;left:50%;transform:translateX(-50%);
  padding:12px 20px;border-radius:12px;font-size:13px;font-weight:600;
  box-shadow:0 8px 32px rgba(0,0,0,.4);z-index:9999;
  pointer-events:none;transition:opacity .3s;opacity:0;
  white-space:nowrap;
}
#rh-toast.show{opacity:1}
#rh-toast.success{background:#0d2a1a;color:var(--success);border:1px solid rgba(52,211,153,.3)}
#rh-toast.error{background:#2a0d0d;color:var(--danger);border:1px solid rgba(248,113,113,.3)}
#rh-toast.warn{background:#2a200d;color:var(--warn);border:1px solid rgba(251,191,36,.3)}
body.light #rh-toast.success{background:#ecfdf5;color:#065f46;border-color:#6ee7b7}
body.light #rh-toast.error{background:#fef2f2;color:#991b1b;border-color:#fca5a5}
body.light #rh-toast.warn{background:#fffbeb;color:#92400e;border-color:#fcd34d}

/* ── Modal ──────────────────────────────────────────── */
.rh-modal-ov{
  position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:1000;
  display:flex;align-items:center;justify-content:center;padding:16px;
  backdrop-filter:blur(4px);
}
.rh-modal-box{
  background:var(--card);border:1px solid var(--border);border-radius:16px;
  padding:24px;width:100%;max-width:480px;
  box-shadow:0 24px 80px rgba(0,0,0,.5);
  max-height:90vh;overflow-y:auto;
}
.rh-modal-box h3{font-size:16px;font-weight:800;margin-bottom:16px;padding-right:32px}
.rh-modal-close{
  position:absolute;top:14px;right:14px;width:30px;height:30px;
  border-radius:8px;border:1px solid var(--border);background:transparent;
  color:var(--muted);cursor:pointer;font-size:18px;display:flex;
  align-items:center;justify-content:center;
}
.rh-modal-close:hover{border-color:var(--danger);color:var(--danger);background:rgba(248,113,113,.08)}
.rh-modal-box{position:relative}
.rh-field{margin-bottom:14px}
.rh-field label{
  display:block;font-size:11px;font-weight:700;text-transform:uppercase;
  letter-spacing:.6px;color:var(--muted);margin-bottom:6px;
}
.rh-field input,.rh-field select,.rh-field textarea{
  width:100%;padding:9px 12px;background:var(--bg);
  border:1px solid var(--border);border-radius:8px;
  color:var(--text);font-size:13px;outline:none;transition:border-color .15s;
}
.rh-field select option{background:var(--card);color:var(--text)}
.rh-field input:focus,.rh-field select:focus,.rh-field textarea:focus{border-color:var(--accent)}
.rh-modal-acts{display:flex;gap:10px;justify-content:flex-end;margin-top:20px}
.rh-btn{
  padding:9px 20px;border-radius:8px;border:none;cursor:pointer;
  font-size:13px;font-weight:700;font-family:inherit;transition:all .15s;
}
.rh-btn.primary{background:var(--accent);color:var(--bg)}
.rh-btn.primary:hover{filter:brightness(1.08)}
.rh-btn.secondary{background:transparent;border:1px solid var(--border);color:var(--text2)}
.rh-btn.secondary:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.rh-btn:disabled{opacity:.5;cursor:not-allowed}

/* Person search list in modal */
.rh-person-list{display:flex;flex-direction:column;gap:4px;max-height:280px;overflow-y:auto;margin-top:8px}
.rh-person-item{
  display:flex;align-items:center;justify-content:space-between;
  padding:8px 12px;border-radius:8px;border:1px solid var(--border);
  cursor:pointer;transition:all .15s;
}
.rh-person-item:hover:not(.blocked){border-color:var(--accent);background:var(--accent-bg)}
.rh-person-item.blocked{opacity:.5;cursor:not-allowed}
.rh-person-name{font-size:13px;font-weight:600;color:var(--text)}
.rh-person-info{font-size:11px;color:var(--muted);margin-top:2px}
.rh-person-status{font-size:11px;font-weight:600}
.rh-person-status.ok{color:var(--success)}
.rh-person-status.blocked{color:var(--danger)}
.rh-person-status.conge{color:var(--warn)}
.rh-search-inp{
  width:100%;padding:9px 12px;background:var(--bg);border:1px solid var(--border);
  border-radius:8px;color:var(--text);font-size:13px;outline:none;
  margin-bottom:8px;
}
.rh-search-inp:focus{border-color:var(--accent)}

/* ── Opérateur view ──────────────────────────────────── */
.rh-op-wrap{max-width:520px;margin:0 auto;padding:8px 0}
.rh-op-card{
  background:var(--card);border:1px solid var(--border);border-radius:14px;
  padding:20px;margin-bottom:16px;
}
.rh-op-card-title{
  font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;
  color:var(--muted);margin-bottom:12px;display:flex;align-items:center;gap:7px;
}
.rh-op-no-plan{
  padding:28px;text-align:center;color:var(--muted);font-size:13px;
  border:1px dashed var(--border);border-radius:10px;
}
.rh-op-row{display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid var(--border)}
.rh-op-row:last-child{border-bottom:none}
.rh-op-key{font-size:12px;color:var(--muted);min-width:110px}
.rh-op-val{font-size:13px;font-weight:600;color:var(--text)}
.rh-op-val.accent{color:var(--accent)}
.rh-op-wk-nav{display:flex;align-items:center;gap:10px;margin-bottom:16px}
.rh-op-wk-lbl{font-size:14px;font-weight:700;flex:1;text-align:center}
.rh-op-nav-btn{
  padding:6px 14px;border-radius:8px;border:1px solid var(--border);
  background:var(--card);color:var(--text2);cursor:pointer;font-size:13px;
  font-family:inherit;transition:all .15s;
}
.rh-op-nav-btn:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}

/* ── Print ──────────────────────────────────────────── */
@media print{
  body{background:#fff!important;color:#000!important;overflow:auto!important;font-size:9px}
  html,body{height:auto!important;overflow:visible!important}
  #root{display:block!important;height:auto!important;overflow:visible!important}
  .rh-sb,.rh-hdr,.rh-conges-wrap .rh-section:not(.print-target){display:none!important}
  .rh-main{overflow:visible!important;padding:0!important;margin:0!important}
  .rh-content{overflow:visible!important;padding:0!important;margin:0!important}
  .rh-grid-wrap{border:none!important;overflow:visible!important;padding:0!important;margin:0!important}

  .rh-machine-block{page-break-inside:avoid;margin-bottom:8px}
  .rh-machine-section-hdr{padding:4px 8px;margin-bottom:4px;font-size:11px}
  .rh-grid{border:1px solid #000!important;border-collapse:collapse!important;width:100%}
  .rh-grid th{font-size:8px!important;padding:2px 4px!important;border:1px solid #000!important;background:#f5f5f5!important}
  .rh-grid td{font-size:8px!important;padding:0!important;border:1px solid #ddd!important}

  .rh-poste-col{width:70px!important;padding:2px 4px!important}
  .rh-week-col{min-width:45px!important}
  .rh-poste-label{padding:2px 4px!important;font-size:8px!important;white-space:normal!important;background:transparent!important}
  .rh-label-content{font-size:8px}
  .rh-week-hdr{padding:4px 8px;font-size:10px}
  .rh-creneau-hdr td{padding:2px 4px!important;font-size:8px}
  .rh-chip{font-size:7px!important;padding:1px 3px!important;border:1px solid #000!important}
  .rh-conge-badge{font-size:7px!important;padding:1px 3px!important}
  .rh-add-btn,.rh-chip-del,.rh-row-btns,.rh-act-btn{display:none!important}
  .rh-section.print-target{display:block!important}
  .rh-section-hdr .rh-icon-btn{display:none!important}
  .print-header{display:block!important;margin-bottom:8px;font-size:12px;font-weight:800}
  .rh-print-pivot-wrap{display:block}
  .rh-print-header{font-size:14px;font-weight:800;margin-bottom:12px}
  .rh-pivot-table{border-collapse:collapse;width:100%;margin-bottom:16px}
  .rh-pivot-table th,.rh-pivot-table td{border:1px solid #000;font-size:9px;padding:3px 5px}
  .rh-pivot-table th{background:#e0e0e0!important;font-weight:bold!important}

  @page{margin:0.5cm;size:A4 landscape}
}
.print-header{display:none}

/* ── Responsive ──────────────────────────────────────── */
@media(max-width:700px){
  .rh-sb{position:fixed;left:0;top:0;bottom:0;z-index:900;transform:translateX(-105%);transition:transform .18s ease;box-shadow:0 16px 48px rgba(0,0,0,.55)}
  .rh-sb.open{transform:translateX(0)}
  .rh-sb-overlay{position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:899;display:none}
  .rh-sb.open~.rh-sb-overlay{display:block}
  .rh-mobile-menu{display:inline-flex!important}
  .rh-range-tabs{display:none}
}
.rh-mobile-menu{display:none;align-items:center;justify-content:center;width:36px;height:36px;border-radius:8px;border:1px solid var(--border);background:var(--card);color:var(--text2);cursor:pointer;font-size:18px}
.rh-mobile-menu:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}

/* ── Loading ──────────────────────────────────────────── */
.rh-loading{display:flex;align-items:center;justify-content:center;padding:60px;color:var(--muted);font-size:13px;gap:10px}
.rh-spinner{width:20px;height:20px;border:2px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin .7s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}

/* ── Année selector ──────────────────────────────────── */
.rh-annee-sel{
  padding:5px 10px;background:var(--bg);border:1px solid var(--border);
  border-radius:8px;color:var(--text);font-size:12px;font-family:inherit;outline:none;
}
.rh-annee-sel:focus{border-color:var(--accent)}

/* ── Grille inversée (colonne=poste, ligne=horaire) ── */
.rh-machine-block{border-bottom:2px solid var(--border)}
.rh-machine-block:last-child{border-bottom:none}
.rh-machine-section-hdr{
  padding:8px 14px;font-size:13px;font-weight:800;text-transform:uppercase;
  letter-spacing:1px;background:var(--card);color:var(--text);
  display:flex;align-items:center;border-bottom:1px solid var(--border);
}
.rh-week-cur{color:var(--accent)}
.rh-cur-week-row td{background:var(--accent-bg)!important}
.rh-cur-week-row .rh-poste-label{background:var(--accent-bg)!important}


/* ── Cross-app sidebar section ──────────────────────── */
.rh-sb-section-title{
  font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1px;
  color:var(--muted);padding:0 10px 4px;margin-top:12px;
}
</style>
</head>
<body>
<div id="root">
  <nav class="rh-sb" id="rh-sb">
    <div class="rh-sb-head">
      <div class="rh-sb-brand">My<span>Sifa</span></div>
      <div class="rh-sb-sub">Planning RH</div>
    </div>
    <div class="rh-sb-nav" id="rh-sb-nav"><!-- injecté JS --></div>
    <div class="rh-sb-bot" id="rh-sb-bot"><!-- injecté JS --></div>
  </nav>
  <div class="rh-sb-overlay" id="rh-sb-overlay" onclick="closeSidebar()"></div>

  <div class="rh-main">
    <div class="rh-hdr" id="rh-hdr"><!-- injecté JS --></div>
    <div class="rh-content" id="rh-content"><!-- injecté JS --></div>
  </div>
</div>
<div id="rh-toast"></div>
<div id="rh-modal-root"></div>

<script>
// ── Constantes grille ─────────────────────────────────────
const GRID_DEF = [
  { code:'RESP', label:"Responsable d'atelier", color:'var(--c5)', special:true,
    creneaux:[ { key:'journee', label:'Journée', hours:null, postes:['resp_atelier'] } ]
  },
  { code:'LOG', label:'Logistique / Expédition', color:'var(--accent)', special:true,
    creneaux:[ { key:'journee', label:'Journée', hours:'08:00 – 16:00', postes:['logistique'], multi:true } ]
  },
  { code:'C1',  label:'Cohésio 1',             color:'var(--c1)',
    creneaux:[
      { key:'matin', label:'Matin',       hours:'05:25 – 13:00', hours_fri:'06:40 – 13:00', postes:['conducteur','aide','emballage'] },
      { key:'aprem', label:'Après-midi',  hours:'13:00 – 20:35', hours_fri:'13:00 – 19:20', postes:['conducteur','aide','emballage'] }
    ]
  },
  { code:'C2',  label:'Cohésio 2',             color:'var(--c2)',
    creneaux:[
      { key:'matin', label:'Matin',       hours:'05:25 – 13:00', hours_fri:'06:40 – 13:00', postes:['conducteur','emballage'] },
      { key:'aprem', label:'Après-midi',  hours:'13:00 – 20:35', hours_fri:'13:00 – 19:20', postes:['conducteur','emballage'] }
    ]
  },
  { code:'DSI', label:'DSI',                   color:'var(--c3)',
    creneaux:[ { key:'journee', label:'Journée', hours:null, postes:['conducteur'] } ]
  },
  { code:'REP', label:'Repiquage',             color:'var(--c4)',
    creneaux:[ { key:'journee', label:'Journée', hours:null, postes:['conducteur'] } ]
  },
];
const POSTE_LABELS = {
  conducteur:'Conducteur', aide:'Aide', emballage:'Emballage',
  resp_atelier:"Resp. d'atelier", logistique:'Logistique'
};
const TYPE_CONGE_LABELS = { CP:'Congés payés', maladie:'Maladie', autre:'Autre' };
const STATUT_CONGE_LABELS = { pose:'Posé', valide:'Validé', refuse:'Refusé' };

// ── État global ────────────────────────────────────────
const S = {
  user: null, isEditor: false, tab: 'planning',
  viewRange: 4, baseOffset: 0, detailMode: false,
  machines: [], personnel: [], planning: [], conges: [], soldes: [],
  annee: new Date().getFullYear(),
  modal: null, toast: null, loading: false,
  opOffset: 0,          // opérateur : décalage semaine
  opViewRange: 1,       // opérateur : plage de vue (1, 2 ou 4 semaines)
  editConge: null,      // congé en cours d'édition
  editSolde: null,      // solde en cours d'édition
  congeForm: { user_id:'', date_debut:'', date_fin:'', nb_jours:'', type_conge:'CP', note:'' },
  soldeForm: { user_id:'', quota_cp:25, quota_rtt:0, note:'' },
  personSearch: '',
  modalTarget: null,    // { semaine, machineCode, poste, creneau, machineId }
};

// ── Helpers semaines ───────────────────────────────────
function getISOWeek(d){
  const dt=new Date(d); dt.setHours(0,0,0,0);
  dt.setDate(dt.getDate()+3-(dt.getDay()+6)%7);
  const w1=new Date(dt.getFullYear(),0,4);
  return{year:dt.getFullYear(),week:1+Math.round(((dt-w1)/86400000-3+(w1.getDay()+6)%7)/7)};
}
function weekStr(d){const{year,week}=getISOWeek(d);return`${year}-W${String(week).padStart(2,'0')}`;}
function weekMonday(ws){
  const[ys,wn]=ws.split('-W');
  const y=parseInt(ys),w=parseInt(wn);
  const jan4=new Date(y,0,4);
  const sw1=new Date(jan4); sw1.setDate(jan4.getDate()-(jan4.getDay()+6)%7);
  const mon=new Date(sw1); mon.setDate(sw1.getDate()+(w-1)*7);
  return mon;
}
function addWeeks(ws,n){const m=weekMonday(ws);m.setDate(m.getDate()+n*7);return weekStr(m);}
function fmtDateShort(d){return`${d.getDate().toString().padStart(2,'0')}/${(d.getMonth()+1).toString().padStart(2,'0')}`;}
function fmtDateFull(iso){if(!iso)return'';const d=new Date(iso);return`${d.getDate().toString().padStart(2,'0')}/${(d.getMonth()+1).toString().padStart(2,'0')}/${d.getFullYear()}`;}
function fmtWeekLabel(ws){
  const mon=weekMonday(ws),sun=new Date(mon);sun.setDate(mon.getDate()+6);
  const wn=ws.split('W')[1];
  return`S${wn} · ${fmtDateShort(mon)}–${fmtDateShort(sun)}`;
}
function fmtWeekLong(ws){
  const mon=weekMonday(ws),sun=new Date(mon);sun.setDate(mon.getDate()+6);
  const wn=ws.split('W')[1]; const yr=ws.split('-W')[0];
  const mois=['janv.','févr.','mars','avr.','mai','juin','juil.','août','sept.','oct.','nov.','déc.'];
  return`Semaine ${wn} — ${mon.getDate()} ${mois[mon.getMonth()]} au ${sun.getDate()} ${mois[sun.getMonth()]} ${yr}`;
}
function getWeeksToShow(){
  // For operators in read-only view, use opViewRange and opOffset
  const isOperator = !S.isEditor && S.user;
  const range = isOperator ? S.opViewRange : S.viewRange;
  const offset = isOperator ? S.opOffset : S.baseOffset;
  const base=addWeeks(weekStr(new Date()),offset);
  return Array.from({length:range},(_,i)=>addWeeks(base,i));
}
function isCurrentWeek(ws){return ws===weekStr(new Date());}

// ── Helpers planning ───────────────────────────────────
function planningKey(a){
  let mc=a.machine_code;
  if(!mc&&a.machine_id){
    // fallback : retrouver le code depuis S.machines (cas où la JOIN n'a pas retourné le code)
    const m=S.machines.find(x=>x.id===a.machine_id||x.id===Number(a.machine_id));
    if(m)mc=m.code;
  }
  if(!mc){ if(a.poste==='logistique')mc='LOG'; else if(a.poste==='resp_atelier')mc='RESP'; else mc='NULL'; }
  return`${mc}|${a.creneau}|${a.poste}|${a.semaine}`;
}
function getAssignments(machineCode,creneau,poste,semaine){
  return S.planning.filter(a=>planningKey(a)===`${machineCode}|${creneau}|${poste}|${semaine}`);
}
function getMachineId(code){
  if(code==='LOG'||code==='RESP')return null;
  const m=S.machines.find(x=>x.code===code);
  return m?m.id:null;
}
function userCongesThisWeek(userId,ws){
  const mon=weekMonday(ws); const sun=new Date(mon); sun.setDate(mon.getDate()+6);
  const monS=mon.toISOString().split('T')[0]; const sunS=sun.toISOString().split('T')[0];
  return S.conges.filter(c=>c.user_id===userId&&c.statut!=='refuse'&&c.date_debut<=sunS&&c.date_fin>=monS);
}
function userAssignedThisWeek(userId,ws){
  return S.planning.find(p=>p.user_id===userId&&p.semaine===ws)||null;
}

// ── API ────────────────────────────────────────────────
const API='/api/rh';
async function api(path,opts={}){
  const r=await fetch(API+path,{credentials:'include',...opts});
  if(r.status===401){window.location.href='/';return null;}
  if(!r.ok){const e=await r.json().catch(()=>({}));throw new Error(e.detail||'Erreur '+r.status);}
  return r.json();
}

async function loadMachines(){
  try{
    const d=await fetch('/api/planning/machines',{credentials:'include'}).then(r=>r.json());
    // L'API retourne un tableau plat (pas enveloppé dans {machines:[...]})
    if(Array.isArray(d)) S.machines=d;
    else if(d&&d.machines) S.machines=d.machines;
  }catch(e){}
}

async function loadData(){
  S.loading=true; render();
  try{
    const weeks=getWeeksToShow();
    const from=weeks[0]; const to=weeks[weeks.length-1];
    const [pers,plan,conges]=await Promise.all([
      api('/personnel').catch(()=>({personnel:[]})),
      api(`/planning?from_week=${from}&to_week=${to}`).catch(()=>({planning:[]})),
      api('/conges').catch(()=>({conges:[]})),
    ]);
    S.personnel=pers?.personnel||[];
    S.planning=plan?.planning||[];
    S.conges=conges?.conges||[];
  }catch(e){toast('Erreur chargement : '+e.message,'error');}
  S.loading=false; render();
}

async function loadSoldes(){
  try{const d=await api(`/soldes?annee=${S.annee}`);if(d)S.soldes=d.soldes||[];}
  catch(e){toast('Erreur soldes : '+e.message,'error');}
  render();
}

async function addAssignment(target){
  const p=target.person;
  try{
    const d=await api('/planning',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        user_id:p.id,semaine:target.semaine,
        machine_id:target.machineId,poste:target.poste,creneau:target.creneau
      })
    });
    if(d){S.planning.push(d);toast(p.nom+' affecté','success');}
  }catch(e){toast(e.message,'error');}
  S.modal=null; render();
}

async function removeAssignment(id){
  try{
    await api('/planning/'+id,{method:'DELETE'});
    S.planning=S.planning.filter(p=>p.id!==id);
    toast('Affectation supprimée','success');
  }catch(e){toast(e.message,'error');}
  render();
}

async function duplicateAssignmentsToNextWeek(semaine, machineCode, poste, creneau, machineId){
  const nextWeek = addWeeks(semaine, 1);
  const assignments = getAssignments(machineCode, creneau, poste, semaine);
  if(!assignments.length){
    toast('Aucune affectation à dupliquer','warn');
    return;
  }
  // Pour Cohésio, alterner matin/aprem
  let targetCreneau = creneau;
  if(machineCode === 'C1' || machineCode === 'C2'){
    targetCreneau = creneau === 'matin' ? 'aprem' : 'matin';
  }
  let count = 0;
  for(const a of assignments){
    try{
      const d = await api('/planning',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({
          user_id:a.user_id,semaine:nextWeek,
          machine_id:machineId,poste:poste,creneau:targetCreneau
        })
      });
      if(d){S.planning.push(d);count++;}
    }catch(e){toast('Erreur pour '+a.user_nom+': '+e.message,'error');}
  }
  if(count>0) toast(count+' affectation(s) copiée(s) vers '+nextWeek,'success');
  render();
}

async function duplicateAllAssignmentsToNextWeek(semaine, machineCode, machineId){
  const nextWeek = addWeeks(semaine, 1);
  const weekAssignments = S.planning.filter(a => a.semaine === semaine && (a.machine_code === machineCode || (machineCode === 'LOG' && a.poste === 'logistique') || (machineCode === 'RESP' && a.poste === 'resp_atelier')));
  if(!weekAssignments.length){
    toast('Aucune affectation à dupliquer','warn');
    return;
  }
  let count = 0;
  for(const a of weekAssignments){
    // Pour Cohésio, alterner matin/aprem
    let targetCreneau = a.creneau;
    if(machineCode === 'C1' || machineCode === 'C2'){
      targetCreneau = a.creneau === 'matin' ? 'aprem' : 'matin';
    }
    try{
      const d = await api('/planning',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({
          user_id:a.user_id,semaine:nextWeek,
          machine_id:machineId,poste:a.poste,creneau:targetCreneau
        })
      });
      if(d){S.planning.push(d);count++;}
    }catch(e){toast('Erreur pour '+a.user_nom+': '+e.message,'error');}
  }
  if(count>0) toast(count+' affectation(s) copiée(s) vers '+nextWeek,'success');
  render();
}

async function deleteRowAssignments(semaine, machineCode, creneau){
  const rowAssignments = S.planning.filter(a => a.semaine === semaine && (a.machine_code === machineCode || (machineCode === 'LOG' && a.poste === 'logistique') || (machineCode === 'RESP' && a.poste === 'resp_atelier')) && a.creneau === creneau);
  if(!rowAssignments.length){
    toast('Aucune affectation à supprimer','warn');
    return;
  }
  let count = 0;
  for(const a of rowAssignments){
    try{
      await api('/planning/'+a.id,{method:'DELETE'});
      S.planning = S.planning.filter(p => p.id !== a.id);
      count++;
    }catch(e){toast('Erreur pour '+a.user_nom+': '+e.message,'error');}
  }
  if(count>0) toast(count+' affectation(s) supprimée(s)','success');
  render();
}

async function submitConge(){
  const f=S.congeForm;
  if(!f.user_id||!f.date_debut||!f.date_fin||!f.nb_jours){toast('Remplissez tous les champs obligatoires','error');return;}
  try{
    if(S.editConge){
      await api('/conges/'+S.editConge.id,{
        method:'PUT',headers:{'Content-Type':'application/json'},
        body:JSON.stringify(f)
      });
      toast('Congé mis à jour','success');
    }else{
      const d=await api('/conges',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify(f)
      });
      if(d)S.conges.unshift(d);
      toast('Congé ajouté','success');
    }
    S.modal=null; S.editConge=null;
    S.congeForm={user_id:'',date_debut:'',date_fin:'',nb_jours:'',type_conge:'CP',note:''};
    await loadData();
    await loadSoldes();
  }catch(e){toast(e.message,'error');}
  render();
}

async function deleteConge(id){
  if(!confirm('Supprimer ce congé ?'))return;
  try{
    await api('/conges/'+id,{method:'DELETE'});
    S.conges=S.conges.filter(c=>c.id!==id);
    toast('Congé supprimé','success');
    loadSoldes();
  }catch(e){toast(e.message,'error');}
  render();
}

async function submitSolde(){
  const f=S.soldeForm;
  if(!f.user_id){toast('Sélectionnez un employé','error');return;}
  try{
    await api('/soldes',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({...f,annee:S.annee})});
    toast('Solde mis à jour','success');
    S.modal=null; S.editSolde=null;
    await loadSoldes();
  }catch(e){toast(e.message,'error');}
  render();
}

// ── Fonctions utilisateur ──────────────────────────────
async function loadMe(){
  try{const d=await fetch('/api/auth/me',{credentials:'include'}).then(r=>r.json());
  if(d&&d.role){
    S.user=d;
    const hasPlanningRHOverride = d.access_overrides && d.access_overrides.planning_rh === true;
    S.isEditor=(['direction','superadmin'].includes(d.role) || hasPlanningRHOverride);
  }}
  catch(e){}
}

// ── Rendu principal ────────────────────────────────────
function render(){
  renderSidebar();
  renderHeader();
  renderContent();
}

function icon(name,sz=14){
  const icons={
    calendar:'<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>',
    umbrella:'<path d="M12 2a10 10 0 0 1 10 10H2A10 10 0 0 1 12 2z"/><line x1="12" y1="12" x2="12" y2="19"/>',
    users:'<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    sun:'<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>',
    moon:'<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>',
    home:'<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
    plus:'<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
    printer:'<polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/>',
    edit:'<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>',
    trash:'<polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/>',
    chevron_left:'<polyline points="15 18 9 12 15 6"/>',
    chevron_right:'<polyline points="9 18 15 12 9 6"/>',
    menu:'<line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/>',
    x:'<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
    check:'<polyline points="20 6 9 17 4 12"/>',
  };
  return`<svg width="${sz}" height="${sz}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${icons[name]||''}</svg>`;
}

// ── Sidebar ────────────────────────────────────────────
function renderSidebar(){
  const nav=document.getElementById('rh-sb-nav');
  const bot=document.getElementById('rh-sb-bot');
  if(!nav||!bot)return;
  const isOp=S.user&&!S.isEditor;

  nav.innerHTML=`
    <button class="rh-nav-btn${S.tab==='planning'?' active':''}" onclick="setTab('planning')">
      ${icon('calendar',14)} Planning
    </button>
    ${S.isEditor?`<button class="rh-nav-btn${S.tab==='conges'?' active':''}" onclick="setTab('conges')">
      ${icon('umbrella',14)} Congés
    </button>`:''}
  `;

  const isLight=document.body.classList.contains('light');
  bot.innerHTML=`
    ${S.user?`<div class="rh-user-chip"><div class="ucn">${S.user.nom||''}</div><div class="ucr">${S.user.role||''}</div></div>`:''}
    <button class="rh-theme-btn" onclick="toggleTheme()">
      ${icon(isLight?'moon':'sun',13)} ${isLight?'Mode sombre':'Mode clair'}
    </button>
    <button class="nav-btn nav-btn--mysifa-portal" onclick="window.location.href='/'">
      <span class="mysifa-back-preamble">← Retour </span>
      <span class="mysifa-back-brand">My<span class="mysifa-back-accent">Sifa</span></span>
    </button>
  `;
}

// ── Header ────────────────────────────────────────────
function renderHeader(){
  const hdr=document.getElementById('rh-hdr');
  if(!hdr)return;
  const isEditor=S.isEditor;

  if(!isEditor){
    // Vue opérateur — header simplifié
    hdr.innerHTML=`
      <button class="rh-mobile-menu" onclick="openSidebar()">${icon('menu',18)}</button>
      <div class="rh-hdr-title">Planning RH · <span>Ma semaine</span></div>
    `;
    return;
  }

  const weeks=getWeeksToShow();
  const rangeLabel=weeks.length===1?fmtWeekLong(weeks[0]):`${fmtWeekLabel(weeks[0])} → ${fmtWeekLabel(weeks[weeks.length-1])}`;

  hdr.innerHTML=`
    <button class="rh-mobile-menu" onclick="openSidebar()">${icon('menu',18)}</button>
    <div class="rh-hdr-title">Planning <span>RH</span></div>
    <div class="rh-hdr-right">
      <div class="rh-wk-nav">
        <button onclick="navWeeks(-S.viewRange)" title="Période précédente">${icon('chevron_left',14)}</button>
        <button class="rh-wk-today" onclick="navWeeks(0)">Aujourd'hui</button>
        <button onclick="navWeeks(S.viewRange)" title="Période suivante">${icon('chevron_right',14)}</button>
      </div>
      <span style="font-size:12px;color:var(--muted);font-weight:600">${rangeLabel}</span>
      <div class="rh-range-tabs">
        ${[1,2,4].map(n=>`<button class="rh-range-tab${S.viewRange===n?' active':''}" onclick="setRange(${n})">${n} sem.</button>`).join('')}
      </div>
      ${S.tab==='planning'?`
        <button class="rh-icon-btn${S.detailMode?' active':''}" onclick="toggleDetail()" title="Vue détaillée jour/semaine">
          ${icon('calendar',13)} Détail
        </button>
        <button class="rh-icon-btn" onclick="printPlanning()" title="Imprimer le planning">
          ${icon('printer',13)} Imprimer
        </button>
      `:''}
      ${S.tab==='conges'?`
        <select class="rh-annee-sel" onchange="changeAnnee(this.value)">
          ${[S.annee-1,S.annee,S.annee+1].map(y=>`<option value="${y}"${y===S.annee?' selected':''}>${y}</option>`).join('')}
        </select>
        <button class="rh-icon-btn" onclick="printConges()">
          ${icon('printer',13)} Imprimer
        </button>
      `:''}
    </div>
  `;
}

// ── Content ────────────────────────────────────────────
function renderContent(){
  const c=document.getElementById('rh-content');
  if(!c)return;
  if(S.loading){c.innerHTML=`<div class="rh-loading"><div class="rh-spinner"></div> Chargement…</div>`;renderModals();return;}
  if(!S.isEditor){c.innerHTML='';c.appendChild(buildOperatorView());renderModals();return;}
  if(S.tab==='planning'){c.innerHTML='';c.appendChild(buildPlanningGrid());}
  else if(S.tab==='conges'){c.innerHTML='';c.appendChild(buildCongesTab());}
  renderModals();
}

// ── Grille planning (configurateur) ───────────────────
// Nouvelle disposition : colonnes = postes, lignes = semaine × créneau
function buildPlanningGrid(){
  const weeks=getWeeksToShow();
  const outer=document.createElement('div');

  const ph=document.createElement('div');
  ph.className='print-header';
  ph.textContent='Planning du personnel — '+fmtWeekLabel(weeks[0])+(weeks.length>1?' au '+fmtWeekLabel(weeks[weeks.length-1]):'');
  outer.appendChild(ph);

  const gw=document.createElement('div');
  gw.className='rh-grid-wrap';

  GRID_DEF.forEach(mdef=>{
    // Postes uniques (union de tous les creneaux de cette machine)
    const allPostes=[];
    mdef.creneaux.forEach(cr=>{
      cr.postes.forEach(p=>{if(!allPostes.includes(p))allPostes.push(p);});
    });

    const block=document.createElement('div');
    block.className='rh-machine-block';

    // En-tête machine
    const mhdr=document.createElement('div');
    mhdr.className='rh-machine-section-hdr';
    mhdr.innerHTML=`<span class="rh-machine-dot" style="background:${mdef.color}"></span>${mdef.label}`;
    block.appendChild(mhdr);

    const table=document.createElement('table');
    table.className='rh-grid';

    // Thead : Semaine/Créneau | Poste1 | Poste2 | ...
    const thead=document.createElement('thead');
    const headRow=document.createElement('tr');
    const thLabel=document.createElement('th');
    thLabel.className='rh-poste-col';
    thLabel.textContent='Semaine / Créneau';
    headRow.appendChild(thLabel);
    allPostes.forEach(poste=>{
      const th=document.createElement('th');
      th.className='rh-week-col';
      th.textContent=POSTE_LABELS[poste]||poste;
      headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);

    const tbody=document.createElement('tbody');

    // Une ligne par (semaine × créneau)
    weeks.forEach((ws, idx)=>{
      const isCur=isCurrentWeek(ws);
      const wn=ws.split('W')[1];
      const mon=weekMonday(ws),sun=new Date(mon);sun.setDate(mon.getDate()+6);

      mdef.creneaux.forEach(cr=>{
        const row=document.createElement('tr');
        row.className='rh-poste-row'+(isCur?' rh-cur-week-row':'');

        // Label de ligne
        const lbl=document.createElement('td');
        lbl.className='rh-poste-label';
        // Inner wrapper for flex layout
        const lblInner=document.createElement('div');
        lblInner.className='rh-poste-label-inner';
        if(S.detailMode){
          const hrsStr=cr.hours
            ?`<div style="font-size:9px;color:var(--muted);font-weight:400;margin-top:1px">Lun-Jeu ${cr.hours}${cr.hours_fri?' · Ven '+cr.hours_fri:''}</div>`
            :'';
          lblInner.innerHTML=`<div class="rh-label-content"><div class="${isCur?'rh-week-cur':''}"><strong>S${wn}</strong> <span style="font-weight:400;font-size:10px">${fmtDateShort(mon)}–${fmtDateShort(sun)}</span></div><div style="font-size:11px;color:var(--muted)">${cr.label}</div>${hrsStr}</div>`;
        }else{
          lblInner.innerHTML=`<div class="rh-label-content"><div class="${isCur?'rh-week-cur':''}"><strong>S${wn}</strong></div><div style="font-size:11px;color:var(--muted)">${cr.label}</div></div>`;
        }
        // Boutons d'action dans la première colonne
        if(S.isEditor){
          const btns=document.createElement('div');
          btns.className='rh-row-btns';
          // Vérifier s'il y a des affectations dans cette ligne (tous postes)
          let hasAssignments=false;
          allPostes.forEach(poste=>{
            const ass=getAssignments(mdef.code,cr.key,poste,ws);
            if(ass.length>0)hasAssignments=true;
          });
          // Bouton de suppression (seulement s'il y a des affectations)
          if(hasAssignments){
            const delBtn=document.createElement('button');
            delBtn.className='rh-row-del-btn';
            delBtn.title='Supprimer toutes les affectations';
            delBtn.innerHTML='×';
            delBtn.onclick=()=>deleteRowAssignments(ws,mdef.code,cr.key);
            btns.appendChild(delBtn);
          }
          // Bouton de duplication (sauf dernière semaine)
          if(idx < weeks.length - 1){
            const dupBtn=document.createElement('button');
            dupBtn.className='rh-row-dup-btn';
            dupBtn.title='Copier vers semaine suivante';
            dupBtn.innerHTML='↓';
            dupBtn.onclick=()=>duplicateAllAssignmentsToNextWeek(ws,mdef.code,getMachineId(mdef.code));
            btns.appendChild(dupBtn);
          }
          if(btns.children.length>0)lblInner.appendChild(btns);
        }
        lbl.appendChild(lblInner);
        row.appendChild(lbl);

        // Cellule par poste
        allPostes.forEach(poste=>{
          const td=document.createElement('td');
          if(!cr.postes.includes(poste)){
            // Poste absent de ce créneau : cellule grisée
            td.style.cssText='background:var(--bg);opacity:.2';
            row.appendChild(td);
            return;
          }
          const cell=document.createElement('div');
          cell.className='rh-cell';

          const assignments=getAssignments(mdef.code,cr.key,poste,ws);
          assignments.forEach(a=>{
            const chip=document.createElement('span');
            chip.className='rh-chip';
            chip.textContent=a.user_nom;
            if(S.isEditor){
              const delBtn=document.createElement('button');
              delBtn.className='rh-chip-del';
              delBtn.title='Retirer '+a.user_nom;
              delBtn.innerHTML='×';
              delBtn.onclick=(e)=>{e.stopPropagation();removeAssignment(a.id);};
              chip.appendChild(delBtn);
            }
            cell.appendChild(chip);
          });

          if(S.isEditor){
            const addBtn=document.createElement('button');
            addBtn.className='rh-add-btn';
            addBtn.title='Ajouter';
            addBtn.innerHTML='+';
            addBtn.onclick=()=>openAddPersonModal({semaine:ws,machineCode:mdef.code,poste,creneau:cr.key,machineId:getMachineId(mdef.code)});
            cell.appendChild(addBtn);
          }

          td.appendChild(cell);
          row.appendChild(td);
        });

        tbody.appendChild(row);
      });
    });

    table.appendChild(tbody);
    block.appendChild(table);
    gw.appendChild(block);
  });

  outer.appendChild(gw);
  return outer;
}

// ── Modal ajout personne ───────────────────────────────
function openAddPersonModal(target){
  S.modalTarget=target; S.personSearch=''; S.modal='add_person'; render();
  setTimeout(()=>{const i=document.getElementById('rh-person-search');if(i)i.focus();},60);
}

function buildAddPersonModal(){
  if(S.modal!=='add_person'||!S.modalTarget)return null;
  const t=S.modalTarget;
  const ov=document.createElement('div'); ov.className='rh-modal-ov';
  ov.addEventListener('mousedown',e=>{if(e.target===ov){S.modal=null;render();}});

  const box=document.createElement('div'); box.className='rh-modal-box';
  const title=POSTE_LABELS[t.poste]||t.poste;
  const wkLabel=fmtWeekLabel(t.semaine);
  box.innerHTML=`
    <button class="rh-modal-close" onclick="S.modal=null;render();">${icon('x',16)}</button>
    <h3>Affecter — ${title}<br><small style="font-size:12px;font-weight:400;color:var(--muted)">${wkLabel}</small></h3>
    <input id="rh-person-search" class="rh-search-inp" type="text" placeholder="Rechercher un employé…"
      value="${S.personSearch}"
      oninput="S.personSearch=this.value;renderPersonList();">
    <div id="rh-person-list" class="rh-person-list"></div>
  `;
  ov.appendChild(box);

  setTimeout(()=>renderPersonList(),0);
  return ov;
}

function renderPersonList(){
  const el=document.getElementById('rh-person-list');
  if(!el)return;
  const t=S.modalTarget;
  const q=S.personSearch.toLowerCase().trim();
  let persons=S.personnel;
  if(q)persons=persons.filter(p=>p.nom.toLowerCase().includes(q)||p.role.toLowerCase().includes(q));

  if(!persons.length){el.innerHTML='<div class="rh-empty">Aucun employé trouvé</div>';return;}

  el.innerHTML='';
  persons.forEach(p=>{
    const assigned=userAssignedThisWeek(p.id,t.semaine);
    const conges=userCongesThisWeek(p.id,t.semaine);
    const blocked=!!(assigned||conges.length);

    const item=document.createElement('div');
    item.className='rh-person-item'+(blocked?' blocked':'');
    item.title=blocked?(assigned?'Déjà affecté : '+assigned.poste+(assigned.machine_nom?' ('+assigned.machine_nom+')':''):'En congé cette semaine'):'';

    let statusHtml='<span class="rh-person-status ok">✓ Disponible</span>';
    if(assigned) statusHtml=`<span class="rh-person-status blocked">Affecté (${POSTE_LABELS[assigned.poste]||assigned.poste})</span>`;
    else if(conges.length) statusHtml=`<span class="rh-person-status conge">🏖 En congé</span>`;

    item.innerHTML=`
      <div><div class="rh-person-name">${p.nom}</div><div class="rh-person-info">${p.role}</div></div>
      ${statusHtml}
    `;
    if(!blocked) item.onclick=()=>{addAssignment({...t,person:p});};
    el.appendChild(item);
  });
}

// ── Congés tab ─────────────────────────────────────────
function buildCongesTab(){
  const wrap=document.createElement('div'); wrap.className='rh-conges-wrap';

  // === Section 1: Soldes ===
  const soldesSection=document.createElement('div'); soldesSection.className='rh-section print-target';
  soldesSection.innerHTML=`
    <div class="rh-section-hdr">
      <span class="rh-section-title">${icon('users',13)} Soldes congés ${S.annee}</span>
      ${S.isEditor?`<button class="rh-icon-btn" onclick="openSoldeModal(null)">
        ${icon('edit',12)} Modifier un solde
      </button>`:''}
    </div>
  `;
  const soldeTable=document.createElement('table'); soldeTable.className='rh-table';
  soldeTable.innerHTML=`<thead><tr>
    <th>Employé</th><th>CP — Quota</th><th>CP — Posé</th><th>CP — Restant</th>
    <th>Maladie</th>
    ${S.isEditor?'<th>Actions</th>':''}
  </tr></thead>`;
  const stbody=document.createElement('tbody');
  if(!S.soldes.length){
    stbody.innerHTML=`<tr><td colspan="${S.isEditor?6:5}" class="rh-empty">Aucun employé planifiable — vérifiez les rôles utilisateurs</td></tr>`;
  }else{
    S.soldes.forEach(s=>{
      const pctCP=s.quota_cp>0?Math.min(100,s.poses_cp/s.quota_cp*100):0;
      const fillCls=pctCP>=100?'danger':pctCP>=80?'warn':'';
      const tr=document.createElement('tr');
      tr.innerHTML=`
        <td style="font-weight:600">${s.user_nom}</td>
        <td>${s.quota_cp}j</td>
        <td><span class="rh-badge cp">${s.poses_cp}j</span></td>
        <td onclick="openSoldeModal(${s.user_id})" style="cursor:pointer" title="Cliquer pour modifier">
          <div class="rh-solde-bar">
            <div class="rh-bar-wrap"><div class="rh-bar-fill ${fillCls}" style="width:${pctCP}%"></div></div>
            <span style="font-size:12px;font-weight:700;color:${s.restant_cp<0?'var(--danger)':s.restant_cp<5?'var(--warn)':'var(--success)'}">${s.restant_cp}j</span>
          </div>
        </td>
        <td><span class="rh-badge mal">${s.poses_maladie}j</span></td>
        ${S.isEditor?`<td><button class="rh-act-btn" onclick="openSoldeModal(${s.user_id})">Modifier</button></td>`:''}
      `;
      stbody.appendChild(tr);
    });
  }
  soldeTable.appendChild(stbody);
  soldesSection.appendChild(soldeTable);
  wrap.appendChild(soldesSection);

  // === Section 2: Ajouter un congé (configurateur) ===
  if(S.isEditor){
    const addSection=document.createElement('div'); addSection.className='rh-section';
    addSection.innerHTML=`
      <div class="rh-section-hdr">
        <span class="rh-section-title">${icon('plus',13)} ${S.editConge?'Modifier un congé':'Ajouter un congé'}</span>
        ${S.editConge?`<button class="rh-icon-btn" onclick="cancelEditConge()">Annuler</button>`:''}
      </div>
      <div style="padding:16px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;align-items:end">
        <div class="rh-field" style="margin:0">
          <label>Employé *</label>
          <select onchange="S.congeForm.user_id=this.value">
            <option value="">Sélectionner…</option>
            ${S.personnel.map(p=>`<option value="${p.id}"${S.congeForm.user_id==p.id?' selected':''}>${p.nom}</option>`).join('')}
          </select>
        </div>
        <div class="rh-field" style="margin:0">
          <label>Type</label>
          <select onchange="S.congeForm.type_conge=this.value">
            ${Object.entries(TYPE_CONGE_LABELS).map(([k,v])=>`<option value="${k}"${(S.congeForm.type_conge||'CP')===k?' selected':''}>${v}</option>`).join('')}
          </select>
        </div>
        <div class="rh-field" style="margin:0">
          <label>Nb jours *</label>
          <input type="number" min="0.5" step="0.5" value="${S.congeForm.nb_jours}" placeholder="ex: 5"
            onchange="S.congeForm.nb_jours=this.value">
        </div>
        <div class="rh-field" style="margin:0">
          <label>Date début *</label>
          <input type="date" value="${S.congeForm.date_debut}" onchange="S.congeForm.date_debut=this.value">
        </div>
        <div class="rh-field" style="margin:0">
          <label>Date fin *</label>
          <input type="date" value="${S.congeForm.date_fin}" onchange="S.congeForm.date_fin=this.value">
        </div>
        <div class="rh-field" style="margin:0">
          <label>Note</label>
          <input type="text" value="${S.congeForm.note||''}" placeholder="Optionnel" onchange="S.congeForm.note=this.value">
        </div>
      </div>
      <div style="padding:0 16px 16px;display:flex;justify-content:flex-end">
        <button class="rh-btn primary" onclick="submitConge()">
          ${icon('check',13)} ${S.editConge?'Enregistrer':'Ajouter le congé'}
        </button>
      </div>
    `;
    wrap.appendChild(addSection);
  }

  // === Section 3: Liste des congés ===
  const listSection=document.createElement('div'); listSection.className='rh-section print-target';
  listSection.innerHTML=`
    <div class="rh-section-hdr">
      <span class="rh-section-title">${icon('umbrella',13)} Congés posés ${S.annee}</span>
    </div>
  `;
  const congesThisYear=S.conges.filter(c=>{
    const y=c.date_debut?c.date_debut.split('-')[0]:null;
    return y==String(S.annee)||c.date_fin&&c.date_fin.split('-')[0]==String(S.annee);
  });

  const congeTable=document.createElement('table'); congeTable.className='rh-table';
  congeTable.innerHTML=`<thead><tr>
    <th>Employé</th><th>Début</th><th>Fin</th><th>Jours</th><th>Type</th>
    <th>Note</th><th>Statut</th>${S.isEditor?'<th>Actions</th>':''}
  </tr></thead>`;
  const ctbody=document.createElement('tbody');
  if(!congesThisYear.length){
    ctbody.innerHTML=`<tr><td colspan="${S.isEditor?8:7}" class="rh-empty">Aucun congé pour ${S.annee}</td></tr>`;
  }else{
    congesThisYear.forEach(c=>{
      const tr=document.createElement('tr');
      tr.innerHTML=`
        <td style="font-weight:600">${c.user_nom}</td>
        <td>${fmtDateFull(c.date_debut)}</td>
        <td>${fmtDateFull(c.date_fin)}</td>
        <td><strong>${c.nb_jours}j</strong></td>
        <td><span class="rh-badge ${c.type_conge.toLowerCase()}">${TYPE_CONGE_LABELS[c.type_conge]||c.type_conge}</span></td>
        <td style="color:var(--muted);font-size:12px">${c.note||'—'}</td>
        <td><span class="rh-badge ${c.statut}">${STATUT_CONGE_LABELS[c.statut]||c.statut}</span></td>
        ${S.isEditor?`<td style="white-space:nowrap">
          <button class="rh-act-btn" onclick="editConge(${c.id})">✏️</button>
          <button class="rh-act-btn del" onclick="deleteConge(${c.id})">🗑</button>
        </td>`:''}
      `;
      ctbody.appendChild(tr);
    });
  }
  congeTable.appendChild(ctbody);
  listSection.appendChild(congeTable);
  wrap.appendChild(listSection);

  return wrap;
}

// ── Modal solde ────────────────────────────────────────
function openSoldeModal(userId){
  if(userId){
    const s=S.soldes.find(x=>x.user_id===userId)||{user_id:userId,quota_cp:25,quota_rtt:0,note:''};
    S.soldeForm={user_id:userId,quota_cp:s.quota_cp,quota_rtt:s.quota_rtt,note:s.note||''};
  }else{
    S.soldeForm={user_id:'',quota_cp:25,quota_rtt:0,note:''};
  }
  S.modal='solde'; render();
}

function buildSoldeModal(){
  const ov=document.createElement('div'); ov.className='rh-modal-ov';
  ov.addEventListener('mousedown',e=>{if(e.target===ov){S.modal=null;render();}});
  const box=document.createElement('div'); box.className='rh-modal-box';
  box.innerHTML=`
    <button class="rh-modal-close" onclick="S.modal=null;render();">${icon('x',16)}</button>
    <h3>Modifier le solde de congés</h3>
    <div class="rh-field">
      <label>Employé *</label>
      <select onchange="S.soldeForm.user_id=this.value">
        <option value="">Sélectionner…</option>
        ${S.personnel.map(p=>`<option value="${p.id}"${S.soldeForm.user_id==p.id?' selected':''}>${p.nom}</option>`).join('')}
      </select>
    </div>
    <div class="rh-field">
      <label>Quota CP (jours)</label>
      <input type="number" min="0" step="0.5" value="${S.soldeForm.quota_cp}"
        onchange="S.soldeForm.quota_cp=parseFloat(this.value)||0">
      <small style="color:var(--muted);font-size:11px">Mettez 0 pour désactiver les congés payés</small>
    </div>
    <div class="rh-field">
      <label>Note</label>
      <input type="text" value="${S.soldeForm.note||''}" placeholder="Optionnel"
        onchange="S.soldeForm.note=this.value">
    </div>
    <div class="rh-modal-acts">
      <button class="rh-btn secondary" onclick="S.modal=null;render();">Annuler</button>
      <button class="rh-btn primary" onclick="submitSolde()">${icon('check',13)} Enregistrer</button>
    </div>
  `;
  ov.appendChild(box);
  return ov;
}

function editConge(id){
  const c=S.conges.find(x=>x.id===id);
  if(!c)return;
  S.editConge=c;
  S.congeForm={user_id:c.user_id,date_debut:c.date_debut,date_fin:c.date_fin,nb_jours:c.nb_jours,type_conge:c.type_conge,note:c.note||''};
  render();
  // Scroll to form
  setTimeout(()=>{const f=document.querySelector('.rh-section:nth-child(2)');if(f)f.scrollIntoView({behavior:'smooth'});},60);
}
function cancelEditConge(){S.editConge=null;S.congeForm={user_id:'',date_debut:'',date_fin:'',nb_jours:'',type_conge:'CP',note:''};render();}

// ── Vue opérateur ──────────────────────────────────────
function buildOperatorView(){
  const wrap=document.createElement('div'); wrap.className='rh-op-wrap';
  const baseWeek=addWeeks(weekStr(new Date()),S.opOffset);
  const weeks=Array.from({length:S.opViewRange},(_,i)=>addWeeks(baseWeek,i));

  // Nav semaine + sélecteur de plage
  const nav=document.createElement('div'); nav.className='rh-op-wk-nav';
  nav.innerHTML=`
    <button class="rh-op-nav-btn" onclick="S.opOffset-=S.opViewRange;loadData();">${icon('chevron_left',14)}</button>
    <div class="rh-op-wk-lbl">${S.opViewRange===1?fmtWeekLong(weeks[0]):fmtWeekLong(weeks[0])+' → '+fmtWeekLong(weeks[weeks.length-1])}</div>
    <button class="rh-op-nav-btn" onclick="S.opOffset+=S.opViewRange;loadData();">${icon('chevron_right',14)}</button>
  `;
  if(S.opOffset!==0){
    const todayBtn=document.createElement('button');
    todayBtn.className='rh-op-nav-btn'; todayBtn.textContent='Cette semaine';
    todayBtn.onclick=()=>{S.opOffset=0;loadData();};
    nav.appendChild(todayBtn);
  }
  
  // Sélecteur de plage (1/2/4 semaines)
  const rangeSelector=document.createElement('div');
  rangeSelector.className='rh-op-range-tabs';
  rangeSelector.style.cssText='display:flex;gap:4px;margin-left:12px;';
  [1,2,4].forEach(n=>{
    const btn=document.createElement('button');
    btn.className='rh-op-range-btn'+(S.opViewRange===n?' active':'');
    btn.textContent=n+' sem.';
    btn.style.cssText='padding:4px 8px;font-size:11px;border:1px solid var(--border);border-radius:6px;background:'+(S.opViewRange===n?'var(--accent)':'var(--card)')+';color:'+(S.opViewRange===n?'#fff':'var(--text1)')+';cursor:pointer;font-weight:600;';
    btn.onclick=()=>{S.opViewRange=n;loadData();};
    rangeSelector.appendChild(btn);
  });
  nav.appendChild(rangeSelector);
  wrap.appendChild(nav);

  // Planning des semaines
  const planCard=document.createElement('div'); planCard.className='rh-op-card';
  planCard.innerHTML=`<div class="rh-op-card-title">${icon('calendar',13)} Mon planning (${S.opViewRange} semaine${S.opViewRange>1?'s':''})</div>`;

  let hasAnyPlan=false;
  weeks.forEach(ws=>{
    const myPlan=S.planning.find(p=>S.user&&p.user_id===S.user.id&&p.semaine===ws);
    const weekHeader=document.createElement('div');
    weekHeader.className='rh-op-week-header';
    weekHeader.style.cssText='font-size:12px;font-weight:700;color:var(--muted);margin:8px 0 4px;padding-top:4px;border-top:1px solid var(--border);';
    weekHeader.textContent=fmtWeekLong(ws);
    if(isCurrentWeek(ws)) weekHeader.innerHTML+=' <span style="color:var(--accent)">(cette semaine)</span>';
    planCard.appendChild(weekHeader);
    
    if(myPlan){
      hasAnyPlan=true;
      const rows=[
        {k:'Machine',v:myPlan.machine_nom||'—'},
        {k:'Poste',v:POSTE_LABELS[myPlan.poste]||myPlan.poste},
        {k:'Créneau',v:myPlan.creneau==='matin'?'Matin':myPlan.creneau==='aprem'?'Après-midi':'Journée'},
      ];
      // Trouver les horaires
      const gdef=GRID_DEF.find(g=>g.code===myPlan.machine_code||(myPlan.poste==='logistique'&&g.code==='LOG')||(myPlan.poste==='resp_atelier'&&g.code==='RESP'));
      if(gdef){
        const cr=gdef.creneaux.find(c=>c.key===myPlan.creneau);
        if(cr&&cr.hours) rows.push({k:'Horaires',v:cr.hours});
      }
      rows.forEach(r=>{
        const row=document.createElement('div'); row.className='rh-op-row';
        row.innerHTML=`<span class="rh-op-key">${r.k}</span><span class="rh-op-val accent">${r.v}</span>`;
        planCard.appendChild(row);
      });
    }else{
      const noPlanDiv=document.createElement('div');
      noPlanDiv.className='rh-op-no-plan';
      noPlanDiv.style.cssText='font-size:12px;color:var(--muted);font-style:italic;padding:4px 0;';
      noPlanDiv.textContent='Aucune affectation';
      planCard.appendChild(noPlanDiv);
    }
  });
  if(!hasAnyPlan && weeks.length===1){
    planCard.innerHTML+=`<div class="rh-op-no-plan">Aucune affectation cette semaine</div>`;
  }
  wrap.appendChild(planCard);

  // Congés à venir
  const congeCard=document.createElement('div'); congeCard.className='rh-op-card';
  congeCard.innerHTML=`<div class="rh-op-card-title">${icon('umbrella',13)} Mes congés</div>`;
  const myConges=S.conges.filter(c=>S.user&&c.user_id===S.user.id&&c.statut!=='refuse');
  if(myConges.length){
    myConges.forEach(c=>{
      const row=document.createElement('div'); row.className='rh-op-row';
      row.innerHTML=`
        <span class="rh-op-key">${fmtDateFull(c.date_debut)} → ${fmtDateFull(c.date_fin)}</span>
        <span class="rh-op-val">${c.nb_jours}j <span class="rh-badge ${c.type_conge.toLowerCase()}">${TYPE_CONGE_LABELS[c.type_conge]||c.type_conge}</span></span>
      `;
      congeCard.appendChild(row);
    });
  }else{
    congeCard.innerHTML+=`<div class="rh-op-no-plan">Aucun congé enregistré</div>`;
  }
  wrap.appendChild(congeCard);

  return wrap;
}

// ── Modals rendu ───────────────────────────────────────
function renderModals(){
  const mr=document.getElementById('rh-modal-root');
  if(!mr)return;
  if(S.modal==='add_person'){
    const m=buildAddPersonModal();
    mr.innerHTML=''; if(m)mr.appendChild(m);
  }else if(S.modal==='solde'){
    const m=buildSoldeModal();
    mr.innerHTML=''; if(m)mr.appendChild(m);
  }else{
    mr.innerHTML='';
  }
}

// ── Toast ──────────────────────────────────────────────
let _toastTimer=null;
function toast(msg,type='success'){
  const el=document.getElementById('rh-toast');
  if(!el)return;
  el.textContent=msg; el.className='show '+type;
  clearTimeout(_toastTimer);
  _toastTimer=setTimeout(()=>{el.className='';},3500);
}

// ── Actions ────────────────────────────────────────────
function setTab(t){
  S.tab=t;
  if(t==='conges'&&!S.soldes.length)loadSoldes();
  render();
}
function setRange(n){S.viewRange=n;loadData();}
function navWeeks(n){
  if(n===0)S.baseOffset=0;
  else S.baseOffset+=n;
  loadData();
}
function toggleDetail(){S.detailMode=!S.detailMode;render();}
function changeAnnee(y){S.annee=parseInt(y);loadSoldes();render();}
function toggleTheme(){document.body.classList.toggle('light');localStorage.setItem('theme',document.body.classList.contains('light')?'light':'dark');renderSidebar();}
function openSidebar(){document.getElementById('rh-sb').classList.add('open');}
function closeSidebar(){document.getElementById('rh-sb').classList.remove('open');}
function printPlanning(){
  const c=document.getElementById('rh-content');
  if(!c)return;
  const originalContent=c.innerHTML;
  c.innerHTML='';
  c.appendChild(buildPrintPivotLayout());
  window.print();
  c.innerHTML=originalContent;
}

function fmtWeekLabelPrint(ws){
  const mon=weekMonday(ws),sun=new Date(mon);sun.setDate(mon.getDate()+6);
  const wn=ws.split('W')[1];
  return`S${wn} · <u>${fmtDateShort(mon)}</u>–<u>${fmtDateShort(sun)}</u>`;
}

function buildPrintPivotLayout(){
  const weeks=getWeeksToShow();
  const wrap=document.createElement('div');
  wrap.className='rh-print-pivot-wrap';

  const header=document.createElement('div');
  header.className='rh-print-header';
  header.style.cssText='text-align:center;font-size:18px;font-weight:bold;margin-bottom:16px';
  // Dates soulignées dans le titre
  const weekLabel1=fmtWeekLabelPrint(weeks[0]);
  const weekLabel2=weeks.length>1?fmtWeekLabelPrint(weeks[weeks.length-1]):'';
  header.innerHTML='Planning du personnel — '+weekLabel1+(weeks.length>1?' au '+weekLabel2:'');
  wrap.appendChild(header);
  
  // Group 1: LOG, RESP, REP (all have journee only)
  const group1Machines=GRID_DEF.filter(m=>['LOG','RESP','REP'].includes(m.code));
  if(group1Machines.length){
    wrap.appendChild(buildPivotTable(group1Machines,weeks,false));
  }
  
  // Spacer row between groups
  const spacer=document.createElement('div');
  spacer.style.cssText='height:20px';
  wrap.appendChild(spacer);
  
  // Group 2: C1, C2, DSI (C1/C2 have matin/aprem, DSI has journee only)
  const group2Machines=GRID_DEF.filter(m=>['C1','C2','DSI'].includes(m.code));
  if(group2Machines.length){
    wrap.appendChild(buildPivotTable(group2Machines,weeks,true));
  }
  
  // Section Congés pour la période affichée
  wrap.appendChild(buildPrintCongesList(weeks));
  
  return wrap;
}

function buildPrintCongesList(weeks){
  const section=document.createElement('div');
  section.style.cssText='margin-top:24px;padding-top:16px;border-top:2px solid #e0e0e0';
  
  const title=document.createElement('div');
  title.style.cssText='font-size:14px;font-weight:bold;color:#333;margin-bottom:12px';
  title.textContent='Congés sur la période';
  section.appendChild(title);
  
  // Get date range of displayed weeks
  const firstWeekStart=weekMonday(weeks[0]);
  const lastWeekEnd=new Date(weekMonday(weeks[weeks.length-1]));
  lastWeekEnd.setDate(lastWeekEnd.getDate()+6);
  
  const rangeStart=firstWeekStart.toISOString().split('T')[0];
  const rangeEnd=lastWeekEnd.toISOString().split('T')[0];
  
  // Filter congés that overlap with this range (and not refused)
  const periodConges=S.conges.filter(c=>{
    if(c.statut==='refuse')return false;
    return c.date_debut<=rangeEnd && c.date_fin>=rangeStart;
  });
  
  if(!periodConges.length){
    const emptyMsg=document.createElement('div');
    emptyMsg.style.cssText='font-size:11px;color:#666;font-style:italic';
    emptyMsg.textContent='Aucun congé sur cette période';
    section.appendChild(emptyMsg);
    return section;
  }
  
  // Sort by date start
  periodConges.sort((a,b)=>a.date_debut.localeCompare(b.date_debut));
  
  // Create table for congés
  const table=document.createElement('table');
  table.style.cssText='border-collapse:collapse;font-size:10px';
  
  // Helper for short date format (DD/MM)
  const fmtDateShortFromIso=(iso)=>{
    if(!iso)return'';
    const d=new Date(iso);
    return`${d.getDate().toString().padStart(2,'0')}/${(d.getMonth()+1).toString().padStart(2,'0')}`;
  };

  // Header
  const thead=document.createElement('thead');
  thead.innerHTML=`
    <tr style="background:#f5f5f5">
      <th style="border:1px solid #000;padding:4px 6px;text-align:left;font-weight:bold;width:150px">Employé</th>
      <th style="border:1px solid #000;padding:4px 6px;text-align:left;font-weight:bold;width:70px">Du</th>
      <th style="border:1px solid #000;padding:4px 6px;text-align:left;font-weight:bold;width:70px">Au</th>
      <th style="border:1px solid #000;padding:4px 6px;text-align:center;font-weight:bold;width:50px">Jours</th>
    </tr>
  `;
  table.appendChild(thead);
  
  // Body
  const tbody=document.createElement('tbody');
  periodConges.forEach((c,idx)=>{
    const user=S.personnel.find(p=>p.id===c.user_id);
    const userName=user?user.nom:'Employé #'+c.user_id;
    const bgColor=idx%2===0?'#ffffff':'#f9f9f9';
    
    const tr=document.createElement('tr');
    tr.style.background=bgColor;
    tr.innerHTML=`<td style="border:1px solid #000;padding:4px 6px;width:150px">${userName}</td>
      <td style="border:1px solid #000;padding:4px 6px;width:70px">${fmtDateShortFromIso(c.date_debut)}</td>
      <td style="border:1px solid #000;padding:4px 6px;width:70px">${fmtDateShortFromIso(c.date_fin)}</td>
      <td style="border:1px solid #000;padding:4px 6px;text-align:center;width:50px">${c.nb_jours}j</td>
    `;
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  
  section.appendChild(table);
  return section;
}

function buildPivotTable(machines,weeks,hasMatinAprem){
  const table=document.createElement('table');
  table.className='rh-pivot-table';
  table.style.cssText='border-collapse:collapse;width:100%;margin-bottom:16px';
  
  // Calculate total UNIQUE postes per machine for colspan
  const machineCols=[];
  machines.forEach(m=>{
    const uniquePostes=[];
    m.creneaux.forEach(cr=>{
      cr.postes.forEach(p=>{
        if(!uniquePostes.includes(p))uniquePostes.push(p);
      });
    });
    machineCols.push({machine:m,posteCount:uniquePostes.length,uniquePostes});
  });
  
  const thead=document.createElement('thead');
  
  // Row 1: Machine headers with colspan
  const machineRow=document.createElement('tr');
  // Week column - no top/left/right border (first cell), keep bottom - background transparent
  const emptyTh=document.createElement('th');
  emptyTh.style.cssText='border-top:none;border-left:none;border-right:none;border-bottom:1px solid #000;background:transparent;font-size:9px;padding:2px 4px;font-weight:bold;min-width:36px';
  emptyTh.rowSpan=hasMatinAprem?2:1;
  machineRow.appendChild(emptyTh);

  if(hasMatinAprem){
    // Creneau column - no top/left border (transparent left to merge with week col), keep bottom/right - background transparent
    const creneauTh=document.createElement('th');
    creneauTh.style.cssText='border-top:none;border-left:1px solid transparent;border-bottom:1px solid #000;border-right:1px solid #000;background:transparent;font-size:9px;padding:2px;font-weight:bold;min-width:24px';
    creneauTh.rowSpan=2;
    machineRow.appendChild(creneauTh);
  }

  machineCols.forEach((mc,idx)=>{
    const th=document.createElement('th');
    // Smaller width for RESP and DSI columns
    const isNarrow=['RESP','DSI'].includes(mc.machine.code);
    // Bordure plus épaisse entre machines (3px) sauf première
    const borderLeft=idx===0?'1px':'3px';
    // Taille de police augmentée pour les machines
    th.style.cssText='border-top:1px solid #000;border-bottom:1px solid #000;border-left:'+borderLeft+' solid #000;border-right:1px solid #000;background:#e8e8e8;font-size:12px;padding:4px 6px;font-weight:bold;text-align:center;min-width:'+(isNarrow?'50px':'70px');
    th.colSpan=mc.posteCount;
    th.textContent=mc.machine.label;
    machineRow.appendChild(th);
  });
  thead.appendChild(machineRow);
  
  // Row 2: Poste headers (unique postes only) - only for matin/aprem tables
  if(hasMatinAprem){
    const posteRow=document.createElement('tr');
    machineCols.forEach((mc,midx)=>{
      mc.uniquePostes.forEach((p,pidx)=>{
        const th=document.createElement('th');
        // Bordure plus épaisse à gauche du premier poste de chaque machine (sauf première)
        const isFirstPosteOfMachine=pidx===0;
        const borderLeft=(isFirstPosteOfMachine&&midx>0)?'3px':'1px';
        th.style.cssText='border-top:1px solid #000;border-bottom:1px solid #000;border-left:'+borderLeft+' solid #000;border-right:1px solid #000;background:#e8e8e8;font-size:9px;padding:3px 5px;font-weight:bold';
        th.textContent=POSTE_LABELS[p]||p;
        posteRow.appendChild(th);
      });
    });
    thead.appendChild(posteRow)
  }
  table.appendChild(thead);
  
  const tbody=document.createElement('tbody');
  
  weeks.forEach((ws,weekIdx)=>{
    const wn=ws.split('W')[1];
    const isEvenWeek=weekIdx%2===0;
    
    if(hasMatinAprem){
      // Two rows per week: matin and après-midi
      const creneauxList=[
        {key:'matin',label:'Matin'},
        {key:'aprem',label:'Après-midi'}
      ];
      
      creneauxList.forEach((cr,crIdx)=>{
        const row=document.createElement('tr');
        const isFirstRow=crIdx===0;
        // Matin = lightgrey, Aprem = transparent (tableau 2 uniquement)
        const bgColor=cr.key==='matin'?'#d3d3d3':'transparent';

        // Week number cell with date details (only on first row, rowspan=2) - left black, right none - dates soulignées - background transparent
        if(isFirstRow){
          const weekCell=document.createElement('td');
          const mon=weekMonday(ws),sun=new Date(mon);sun.setDate(mon.getDate()+6);
          const wn=ws.split('W')[1];
          const weekLabelHtml=`S${wn} · <u>${fmtDateShort(mon)}</u>–<u>${fmtDateShort(sun)}</u>`;
          weekCell.style.cssText='border-top:none;border-bottom:1px solid #000;border-left:1px solid #000;border-right:none;font-size:8px;padding:1px 2px;background:transparent;font-weight:bold;vertical-align:middle;width:50px;white-space:nowrap;overflow:hidden';
          weekCell.rowSpan=2;
          weekCell.innerHTML=weekLabelHtml;
          row.appendChild(weekCell);
        }

        // Creneau label cell - no top/left border, transparent left to merge with week
        const creneauCell=document.createElement('td');
        creneauCell.style.cssText='border-top:none;border-left:1px solid transparent;border-bottom:1px solid #000;border-right:1px solid #000;font-size:8px;padding:2px;background:'+bgColor+';font-weight:bold;min-width:24px';
        creneauCell.textContent=cr.label;
        row.appendChild(creneauCell);
        
        // Add cells for each machine's unique postes
        machineCols.forEach((mc,midx)=>{
          const m=mc.machine;
          const machineCreneaux=m.creneaux.find(c=>c.key===cr.key);

          if(machineCreneaux){
            // Machine has this creneau (C1, C2) - iterate through UNIQUE postes
            mc.uniquePostes.forEach((poste,pidx)=>{
              const td=document.createElement('td');
              // Bordure plus épaisse à gauche du premier poste de chaque machine (sauf première)
              const borderLeft=(pidx===0&&midx>0)?'3px':'1px';
              // Colonne DSI avec background transparent
              const isDSI=m.code==='DSI';
              const cellBg=isDSI?'transparent':bgColor;
              td.style.cssText='border-top:1px solid #000;border-bottom:1px solid #000;border-left:'+borderLeft+' solid #000;border-right:1px solid #000;font-size:9px;padding:3px 5px;min-width:60px;background:'+cellBg;
              // Check if this poste exists in current creneau
              if(machineCreneaux.postes.includes(poste)){
                const ass=getAssignments(m.code,cr.key,poste,ws);
                if(ass.length){
                  ass.forEach(a=>{
                    const chip=document.createElement('span');
                    chip.style.cssText='display:inline-block;font-size:11px;padding:2px 4px;background:transparent;margin:1px;font-weight:bold;color:#000';
                    chip.textContent=a.user_nom.split(' ')[0];
                    td.appendChild(chip);
                  });
                }
              }
              row.appendChild(td);
            });
          }else if(m.creneaux.length===1 && m.creneaux[0].key==='journee' && isFirstRow){
            // DSI-like machine with only journee - merge both rows
            const journeeCr=m.creneaux[0];
            journeeCr.postes.forEach((poste,pidx)=>{
              const td=document.createElement('td');
              // Bordure plus épaisse à gauche du premier poste de chaque machine (sauf première)
              const borderLeft=(pidx===0&&midx>0)?'3px':'1px';
              td.style.cssText='border-top:1px solid #000;border-bottom:1px solid #000;border-left:'+borderLeft+' solid #000;border-right:1px solid #000;font-size:9px;padding:3px 5px;min-width:50px;background:'+bgColor+';vertical-align:middle';
              td.rowSpan=2;
              const ass=getAssignments(m.code,'journee',poste,ws);
              if(ass.length){
                ass.forEach(a=>{
                  const chip=document.createElement('span');
                  chip.style.cssText='display:inline-block;font-size:11px;padding:2px 4px;background:transparent;margin:1px;font-weight:bold;color:#000';
                  chip.textContent=a.user_nom.split(' ')[0];
                  td.appendChild(chip);
                });
              }
              row.appendChild(td);
            });
          }
          // For journee-only machines on second row: cells were merged, skip
        });
        
        tbody.appendChild(row);
      });
    }else{
      // One row per week (LOG, RESP, REP) - Tableau 1
      const row=document.createElement('tr');
      const bgColor=isEvenWeek?'#f5f5f5':'#ffffff';

      // Week number cell with date details - full black borders - background transparent, dates soulignées
      const weekCell=document.createElement('td');
      const mon=weekMonday(ws),sun=new Date(mon);sun.setDate(mon.getDate()+6);
      const wn=ws.split('W')[1];
      const weekLabelHtml=`S${wn} · <u>${fmtDateShort(mon)}</u>–<u>${fmtDateShort(sun)}</u>`;
      weekCell.style.cssText='border:1px solid #000;font-size:9px;padding:2px 4px;background:transparent;font-weight:bold;min-width:60px';
      weekCell.innerHTML=weekLabelHtml;
      row.appendChild(weekCell);

      // Add cells for each machine/poste (all use 'journee')
      machines.forEach((m,midx)=>{
        const journeeCr=m.creneaux.find(c=>c.key==='journee');
        if(journeeCr){
          journeeCr.postes.forEach((poste,pidx)=>{
            const td=document.createElement('td');
            // Bordure plus épaisse à gauche du premier poste de chaque machine (sauf première)
            const isFirstPosteOfMachine=pidx===0;
            const borderLeft=(isFirstPosteOfMachine&&midx>0)?'3px':'1px';
            // Smaller width for RESP columns
            const isNarrow=m.code==='RESP';
            // Colonne DSI avec background transparent
            const isDSI=m.code==='DSI';
            const cellBg=isDSI?'transparent':bgColor;
            td.style.cssText='border-top:1px solid #000;border-bottom:1px solid #000;border-left:'+borderLeft+' solid #000;border-right:1px solid #000;font-size:9px;padding:3px 5px;min-width:'+(isNarrow?'50px':'60px')+';background:'+cellBg;
            const ass=getAssignments(m.code,'journee',poste,ws);
            if(ass.length){
              ass.forEach(a=>{
                const chip=document.createElement('span');
                chip.style.cssText='display:inline-block;font-size:11px;padding:2px 4px;background:transparent;margin:1px;font-weight:bold;color:#000';
                chip.textContent=a.user_nom.split(' ')[0];
                td.appendChild(chip);
              });
            }
            row.appendChild(td);
          });
        }
      });

      tbody.appendChild(row);
    }
  });
  
  table.appendChild(tbody);
  return table;
}

function userCongesThisWeekForUser(userId,ws){
  if(!userId)return[];
  const mon=weekMonday(ws);
  const sun=new Date(mon);sun.setDate(mon.getDate()+6);
  const monS=mon.toISOString().split('T')[0];
  const sunS=sun.toISOString().split('T')[0];
  return S.conges.filter(c=>c.user_id===userId&&c.statut!=='refuse'&&c.date_debut<=sunS&&c.date_fin>=monS);
}
function printConges(){
  document.querySelectorAll('.rh-section').forEach(s=>s.classList.remove('print-target'));
  document.querySelectorAll('.rh-conges-wrap .rh-section').forEach(s=>s.classList.add('print-target'));
  window.print();
}

// ── Init ───────────────────────────────────────────────
(async()=>{
  if(localStorage.getItem('theme')==='light') document.body.classList.add('light');
  await loadMe();
  if(S.isEditor)S.viewRange=4; else S.viewRange=1;
  await loadMachines();
  await loadData();
  if(S.tab==='conges')await loadSoldes();
})();
</script>
</body>
</html>"""

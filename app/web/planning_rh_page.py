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
    if user.get("role") not in ROLES_PLANNING_RH_VIEW:
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
  display:flex;align-items:center;gap:8px;padding:9px 10px;border-radius:8px;
  border:1px solid var(--border);background:transparent;color:var(--text2);
  cursor:pointer;font-size:12px;width:100%;font-family:inherit;transition:all .15s;
}
.rh-theme-btn:hover{background:var(--accent-bg);color:var(--accent);border-color:var(--accent)}
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
.rh-grid thead th.rh-poste-col{text-align:left;min-width:160px;position:sticky;left:0;z-index:6;background:var(--card)}
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
  padding:6px 8px;vertical-align:top;background:var(--bg);
}
.rh-poste-label{
  padding:6px 12px 6px 28px!important;font-size:12px;font-weight:600;
  color:var(--text2);white-space:nowrap;
  position:sticky;left:0;z-index:2;background:var(--bg)!important;
}
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
  body{background:#fff!important;color:#000!important;overflow:auto!important}
  html,body{height:auto!important;overflow:visible!important}
  #root{display:block!important;height:auto!important;overflow:visible!important}
  .rh-sb,.rh-hdr,.rh-conges-wrap .rh-section:not(.print-target){display:none!important}
  .rh-main{overflow:visible!important}
  .rh-content{overflow:visible!important;padding:0!important}
  .rh-grid-wrap{border:none!important;overflow:visible!important}
  .rh-add-btn,.rh-chip-del{display:none!important}
  .rh-grid th,.rh-grid td{font-size:10px!important;padding:4px 6px!important}
  .rh-section.print-target{display:block!important}
  .rh-section-hdr .rh-icon-btn{display:none!important}
  .rh-act-btn{display:none!important}
  .print-header{display:block!important;margin-bottom:12px;font-size:14px;font-weight:800}
  @page{margin:1cm;size:A4 landscape}
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
  padding:8px 14px;font-size:12px;font-weight:800;text-transform:uppercase;
  letter-spacing:1px;background:var(--bg);color:var(--text2);
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
  { code:'RESP', label:"Responsable d'atelier", color:'var(--c5)', special:true,
    creneaux:[ { key:'journee', label:'Journée', hours:null, postes:['resp_atelier'] } ]
  },
  { code:'LOG', label:'Logistique / Expédition', color:'var(--accent)', special:true,
    creneaux:[ { key:'journee', label:'Journée', hours:'08:00 – 16:00', postes:['logistique'], multi:true } ]
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
  const base=addWeeks(weekStr(new Date()),S.baseOffset);
  return Array.from({length:S.viewRange},(_,i)=>addWeeks(base,i));
}
function isCurrentWeek(ws){return ws===weekStr(new Date());}

// ── Helpers planning ───────────────────────────────────
function planningKey(a){
  let mc=a.machine_code;
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
  try{const d=await fetch('/api/planning/machines',{credentials:'include'}).then(r=>r.json());
  if(d&&d.machines)S.machines=d.machines;}catch(e){}
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
  if(d&&d.role){S.user=d;S.isEditor=(['direction','superadmin'].includes(d.role));}}
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
    umbrella:'<polyline points="23 12 11 12 11 19a1 1 0 0 0 2 0"/><path d="M12 2a10 10 0 0 1 10 10H2A10 10 0 0 1 12 2z"/>',
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
    <div style="margin-top:14px;padding-top:12px;border-top:1px solid var(--border)">
      <div class="rh-sb-section-title">Autres applis</div>
      <button class="rh-nav-btn" onclick="window.location.href='/planning'">
        ${icon('calendar',14)} Planning Machine
      </button>
      <button class="rh-nav-btn" onclick="window.location.href='/stock'">
        ${icon('users',14)} Stock
      </button>
    </div>
  `;

  const isLight=document.body.classList.contains('light');
  bot.innerHTML=`
    ${S.user?`<div class="rh-user-chip"><div class="ucn">${S.user.nom||''}</div><div class="ucr">${S.user.role||''}</div></div>`:''}
    <button class="rh-theme-btn" onclick="toggleTheme()">
      ${icon(isLight?'moon':'sun',13)} ${isLight?'Mode sombre':'Mode clair'}
    </button>
    <button class="rh-back-btn" onclick="window.location.href='/'">
      ${icon('home',13)} Retour MySifa
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
    weeks.forEach(ws=>{
      const isCur=isCurrentWeek(ws);
      const wn=ws.split('W')[1];
      const mon=weekMonday(ws),sun=new Date(mon);sun.setDate(mon.getDate()+6);

      mdef.creneaux.forEach(cr=>{
        const row=document.createElement('tr');
        row.className='rh-poste-row'+(isCur?' rh-cur-week-row':'');

        // Label de ligne
        const lbl=document.createElement('td');
        lbl.className='rh-poste-label';
        if(S.detailMode){
          const hrsStr=cr.hours
            ?`<div style="font-size:9px;color:var(--muted);font-weight:400;margin-top:1px">Lun-Jeu ${cr.hours}${cr.hours_fri?' · Ven '+cr.hours_fri:''}</div>`
            :'';
          lbl.innerHTML=`<div class="${isCur?'rh-week-cur':''}"><strong>S${wn}</strong> <span style="font-weight:400;font-size:10px">${fmtDateShort(mon)}–${fmtDateShort(sun)}</span></div><div style="font-size:11px;color:var(--muted)">${cr.label}</div>${hrsStr}`;
        }else{
          lbl.innerHTML=`<div class="${isCur?'rh-week-cur':''}"><strong>S${wn}</strong></div><div style="font-size:11px;color:var(--muted)">${cr.label}</div>`;
        }
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
        <td>
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
  const ws=addWeeks(weekStr(new Date()),S.opOffset);

  // Nav semaine
  const nav=document.createElement('div'); nav.className='rh-op-wk-nav';
  nav.innerHTML=`
    <button class="rh-op-nav-btn" onclick="S.opOffset--;renderContent();">${icon('chevron_left',14)}</button>
    <div class="rh-op-wk-lbl">${fmtWeekLong(ws)}</div>
    <button class="rh-op-nav-btn" onclick="S.opOffset++;renderContent();">${icon('chevron_right',14)}</button>
  `;
  if(S.opOffset!==0){
    const todayBtn=document.createElement('button');
    todayBtn.className='rh-op-nav-btn'; todayBtn.textContent='Cette semaine';
    todayBtn.onclick=()=>{S.opOffset=0;renderContent();};
    nav.appendChild(todayBtn);
  }
  wrap.appendChild(nav);

  // Planning de la semaine
  const planCard=document.createElement('div'); planCard.className='rh-op-card';
  planCard.innerHTML=`<div class="rh-op-card-title">${icon('calendar',13)} Mon planning</div>`;

  const myPlan=S.planning.find(p=>S.user&&p.user_id===S.user.id&&p.semaine===ws);
  if(myPlan){
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
function printPlanning(){window.print();}
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

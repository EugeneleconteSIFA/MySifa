"""MySifa — Page /reports/weekly (preview + envoi + archive)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import APP_VERSION
from services.auth_service import effective_role, get_current_user, is_superadmin
from app.web.access_denied import access_denied_response

router = APIRouter()

# V1 : accès restreint au super administrateur uniquement (test interne).
# À élargir plus tard aux autres rôles quand le rapport sera validé.


@router.get("/reports/weekly", response_class=HTMLResponse)
def weekly_report_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/reports/weekly", status_code=302)
        raise
    if not is_superadmin(user):
        return access_denied_response(
            "Rapport hebdomadaire",
            detail=(
                "Ce module est en phase de test et réservé au super administrateur. "
                "Il sera étendu aux autres rôles prochainement."
            ),
        )
    role = effective_role(user)
    can_send = True
    can_switch_role = True
    return HTMLResponse(
        content=REPORTS_HTML
        .replace("__V_LABEL__", f"v{APP_VERSION}")
        .replace("__ROLE__", role)
        .replace("__CAN_SEND__", "true" if can_send else "false")
        .replace("__CAN_SWITCH__", "true" if can_switch_role else "false")
    )


REPORTS_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17">
<title>Rapport hebdomadaire — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="stylesheet" href="/static/mysifa_theme.css">
<link rel="stylesheet" href="/static/mysifa_user_chip.css">
<script src="/static/mysifa_theme.js"></script>
<script>try{ if(window.MySifaTheme){ MySifaTheme.initFromStorage(); } }catch(e){}</script>
<style>
:root{--bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;--muted:#94a3b8;--accent:#22d3ee;--accent-bg:rgba(34,211,238,.12);--ok:#34d399;--success:#34d399;--warn:#fbbf24;--danger:#f87171;}
body.light{--bg:#f1f5f9;--card:#fff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;--muted:#64748b;--accent:#0891b2;--ok:#059669;--success:#059669;--warn:#d97706;--danger:#dc2626;}
*{box-sizing:border-box}
body{margin:0;font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
.layout{display:flex;min-height:100vh}
.sidebar{width:220px;background:var(--card);border-right:1px solid var(--border);padding:20px 12px;display:flex;flex-direction:column;flex-shrink:0;height:100vh;position:sticky;top:0;overflow-y:auto;scrollbar-width:none}
.sidebar::-webkit-scrollbar{width:0}
.logo{font-size:15px;font-weight:800;margin-bottom:20px;padding:0 8px}
.logo span{color:var(--accent)}
.logo-sub{font-size:10px;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase;margin-top:2px}
.nav-scroll{flex:1;min-height:0;overflow-y:auto;display:flex;flex-direction:column;gap:6px;margin-bottom:8px}
.nav-btn{display:flex;align-items:center;gap:10px;width:100%;text-align:left;padding:10px 12px;border-radius:8px;border:none;background:transparent;color:var(--text2);font-size:13px;font-weight:500;cursor:pointer;font-family:inherit;transition:background .15s,color .15s;margin-bottom:2px}
.nav-btn:hover,.nav-btn.active{background:var(--accent-bg);color:var(--accent)}
.sidebar-bottom{margin-top:auto;display:flex;flex-direction:column;gap:6px;padding-bottom:8px}
.user-chip{padding:10px 12px;border-radius:8px;background:var(--accent-bg);cursor:pointer}
.user-chip .uc-name{font-size:12px;font-weight:600;color:var(--text)}
.user-chip .uc-role{font-size:10px;color:var(--accent);text-transform:uppercase;letter-spacing:.5px}
.theme-btn,.logout-btn{display:flex;align-items:center;gap:8px;padding:10px 12px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-size:12px;width:100%;font-family:inherit}
.theme-btn:hover{background:var(--accent-bg);color:var(--accent);border-color:var(--accent)}
.logout-btn{border:none}
.logout-btn:hover{color:var(--danger);background:rgba(248,113,113,.1)}
.version{font-size:10px;color:var(--muted);font-family:monospace;padding:4px 12px}
.main{flex:1;padding:24px 28px;overflow:auto}
.sidebar-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:200}
body.sb-open .sidebar-overlay{display:block}
h1{font-size:22px;margin:0 0 6px}
.sub{color:var(--muted);font-size:13px;margin-bottom:22px}
.toolbar{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:20px;padding:14px 16px;background:var(--card);border:1px solid var(--border);border-radius:12px}
.toolbar label{font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
.toolbar input,.toolbar select{background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:8px 12px;color:var(--text);font-size:13px;font-family:inherit}
.toolbar input:focus,.toolbar select:focus{border-color:var(--accent);outline:none;box-shadow:0 0 0 3px rgba(34,211,238,.12)}
.btn{background:var(--accent);color:var(--bg);border:none;border-radius:10px;padding:9px 16px;font-weight:700;font-size:13px;cursor:pointer;font-family:inherit;transition:filter .15s}
.btn:hover{filter:brightness(1.06)}
.btn-ghost{background:transparent;color:var(--text2);border:1px solid var(--border)}
.btn-ghost:hover{border-color:var(--accent);color:var(--accent)}
.btn-danger{background:var(--danger);color:#fff}
.btn:disabled{opacity:.5;cursor:not-allowed}
.tabs{display:flex;gap:6px;margin-bottom:16px;border-bottom:1px solid var(--border)}
.tab-btn{background:transparent;border:none;color:var(--muted);padding:10px 14px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;border-bottom:2px solid transparent}
.tab-btn.active{color:var(--accent);border-bottom-color:var(--accent)}
.tab-panel{display:none}
.tab-panel.active{display:block}
#preview{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px 24px;min-height:200px}
#preview .loading{color:var(--muted);font-size:13px;text-align:center;padding:40px 0}
.archive-item{display:flex;justify-content:space-between;align-items:center;padding:12px 16px;background:var(--card);border:1px solid var(--border);border-radius:10px;margin-bottom:8px}
.archive-item .arch-lbl{font-size:14px;font-weight:600;color:var(--text)}
.archive-item .arch-meta{font-size:11px;color:var(--muted)}
#toast{position:fixed;top:20px;right:20px;padding:12px 20px;border-radius:10px;color:#fff;font-size:13px;font-weight:600;z-index:9999;display:none;box-shadow:0 6px 24px rgba(0,0,0,.35)}
#toast.success{background:var(--ok)}
#toast.danger{background:var(--danger)}
#toast.info{background:var(--accent);color:var(--bg)}
.modal-ov{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:800;align-items:center;justify-content:center}
.modal-ov.open{display:flex}
.modal-card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:22px 24px;width:min(480px,92vw)}
.modal-card h3{margin:0 0 10px;font-size:16px;color:var(--text)}
.modal-card p{color:var(--text2);font-size:13px;margin:0 0 18px;line-height:1.5}
.modal-actions{display:flex;gap:10px;justify-content:flex-end}
.mobile-topbar{display:none}
@media (max-width:900px){
  .sidebar{width:min(280px,88vw);position:fixed;left:0;top:0;bottom:0;z-index:300;transform:translateX(-105%);transition:transform .2s}
  body.sb-open .sidebar{transform:translateX(0)}
  .mobile-topbar{display:flex;align-items:center;gap:12px;padding:12px 16px;background:var(--card);border-bottom:1px solid var(--border)}
  .mobile-menu-btn{background:transparent;border:none;color:var(--text);cursor:pointer}
  .main{padding:16px}
}
</style>
</head>
<body>
<div class="sidebar-overlay" id="sb-ov"></div>
<div class="layout">
  <aside class="sidebar">
    <div class="logo">My<span>Sifa</span><div class="logo-sub">Rapport hebdo</div></div>
    <div class="nav-scroll">
      <button type="button" class="nav-btn active" onclick="switchTab('preview')">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
        Aperçu
      </button>
      <button type="button" class="nav-btn" onclick="switchTab('archive')">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/></svg>
        Archive
      </button>
    </div>
    <div class="sidebar-bottom">
      <button type="button" class="nav-btn" onclick="location.href='/'">← Retour <b>MySifa</b></button>
      <div class="user-chip" id="sb-user-chip" onclick="location.href='/profil'"></div>
      <button type="button" class="theme-btn" id="theme-btn">
        <span id="theme-label">Mode sombre</span>
      </button>
      <button type="button" class="logout-btn" id="logout-btn">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
        Déconnexion
      </button>
      <div class="version">Rapport · MySifa __V_LABEL__</div>
    </div>
  </aside>
  <main class="main">
    <div class="mobile-topbar">
      <button type="button" class="mobile-menu-btn" onclick="document.body.classList.toggle('sb-open')">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
      </button>
      <div><b>Rapport hebdomadaire</b><div style="font-size:11px;color:var(--muted)">Semaine passée</div></div>
    </div>
    <h1>Rapport hebdomadaire</h1>
    <div class="sub">Semaine passée — envoyée automatiquement chaque mercredi matin.</div>

    <div id="tab-preview" class="tab-panel active">
      <div class="toolbar">
        <div>
          <label style="display:block;margin-bottom:4px">Semaine ISO</label>
          <input type="week" id="wk-input">
        </div>
        <div id="role-selector-wrap" style="display:none">
          <label style="display:block;margin-bottom:4px">Rôle</label>
          <select id="role-select">
            <option value="superadmin">superadmin</option>
            <option value="direction">direction</option>
            <option value="administration">administration</option>
            <option value="administration_ventes">administration des ventes</option>
            <option value="administration_technique">administration technique</option>
            <option value="fabrication">fabrication</option>
            <option value="logistique">logistique</option>
            <option value="comptabilite">comptabilite</option>
            <option value="expedition">expedition</option>
            <option value="commercial">commercial</option>
          </select>
        </div>
        <div style="flex:1"></div>
        <button class="btn btn-ghost" id="btn-refresh">Actualiser l'aperçu</button>
        <button class="btn btn-ghost" id="btn-copy">Copier HTML</button>
        <button class="btn" id="btn-send" style="display:none">Envoyer maintenant</button>
      </div>
      <div id="preview"><div class="loading">Chargement de l'aperçu…</div></div>
    </div>

    <div id="tab-archive" class="tab-panel">
      <div id="archive-list"><div class="loading" style="color:var(--muted);padding:40px 0;text-align:center">Chargement…</div></div>
    </div>
  </main>
</div>

<div class="modal-ov" id="send-modal">
  <div class="modal-card">
    <h3>Envoyer le rapport ?</h3>
    <p id="send-modal-msg">Le rapport sera envoyé par email à tous les utilisateurs actifs et une annonce sera publiée. Cette action est irréversible.</p>
    <div class="modal-actions">
      <button class="btn btn-ghost" onclick="closeSendModal()">Annuler</button>
      <button class="btn" id="btn-send-confirm">Confirmer l'envoi</button>
    </div>
  </div>
</div>

<div id="toast"></div>

<script>
const ROLE = "__ROLE__";
const CAN_SEND = __CAN_SEND__;
const CAN_SWITCH = __CAN_SWITCH__;

function showToast(msg, type='info'){
  const t = document.getElementById('toast');
  t.textContent = msg; t.className = type;
  t.style.display = 'block';
  setTimeout(() => { t.style.display = 'none'; }, 3800);
}

var REPORTS_VALID_TABS=['preview','archive'];
function _readReportsTab(){
  try{var h=(location.hash||'').replace(/^#/,'').trim();
    if(REPORTS_VALID_TABS.indexOf(h)!==-1)return h;}catch(e){}
  return 'preview';
}
function switchTab(name, opts){
  var silent=!!(opts&&opts.silent);
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  if(event&&event.target&&event.target.closest('.nav-btn')){
    event.target.closest('.nav-btn').classList.add('active');
  }else{
    document.querySelectorAll('.nav-btn').forEach(function(b){if(b.getAttribute('onclick')&&b.getAttribute('onclick').indexOf(name)!==-1)b.classList.add('active');});
  }
  if (name === 'archive') loadArchive();
  if(!silent){try{var target='#'+name;if(location.hash!==target)history.replaceState(null,'',target);}catch(e){}}
}

function getSelectedWeek(){
  const v = document.getElementById('wk-input').value;
  if (!v) return null;
  const m = v.match(/^(\d{4})-W(\d{2})$/);
  if (!m) return null;
  return { year: parseInt(m[1]), week: parseInt(m[2]) };
}

function isoWeekFromDate(d){
  const target = new Date(d.valueOf());
  const dayNr = (d.getDay() + 6) % 7;
  target.setDate(target.getDate() - dayNr + 3);
  const firstThursday = target.valueOf();
  target.setMonth(0, 1);
  if (target.getDay() !== 4){
    target.setMonth(0, 1 + ((4 - target.getDay()) + 7) % 7);
  }
  const week = 1 + Math.ceil((firstThursday - target) / (7 * 86400000));
  const year = new Date(firstThursday).getFullYear();
  return { year, week };
}

function initDefaultWeek(){
  const now = new Date();
  now.setDate(now.getDate() - 7);
  const { year, week } = isoWeekFromDate(now);
  document.getElementById('wk-input').value = year + '-W' + String(week).padStart(2, '0');
}

async function loadPreview(){
  const pv = document.getElementById('preview');
  pv.innerHTML = '<div class="loading">Chargement de l\'aperçu…</div>';
  const w = getSelectedWeek();
  if (!w){ pv.innerHTML = '<div class="loading">Choisissez une semaine.</div>'; return; }
  const role = document.getElementById('role-select').value || ROLE;
  try {
    const r = await fetch(`/api/reports/weekly/preview?year=${w.year}&week=${w.week}&role=${encodeURIComponent(role)}`, { credentials: 'include' });
    if (!r.ok){
      const err = await r.text();
      pv.innerHTML = `<div class="loading" style="color:var(--danger)">Erreur : ${err}</div>`;
      return;
    }
    const j = await r.json();
    pv.innerHTML = j.html || '<div class="loading">Aucun contenu.</div>';
  } catch(e){
    pv.innerHTML = `<div class="loading" style="color:var(--danger)">Erreur réseau : ${e.message}</div>`;
  }
}

async function loadArchive(){
  const box = document.getElementById('archive-list');
  box.innerHTML = '<div class="loading" style="color:var(--muted);padding:40px 0;text-align:center">Chargement…</div>';
  try {
    const r = await fetch('/api/reports/weekly/list', { credentials: 'include' });
    if (!r.ok){ box.innerHTML = '<div class="loading">Erreur de chargement.</div>'; return; }
    const list = await r.json();
    if (!list || !list.length){
      box.innerHTML = '<div class="loading">Aucun rapport archivé.</div>';
      return;
    }
    box.innerHTML = list.map(it => `
      <div class="archive-item">
        <div>
          <div class="arch-lbl">Semaine ${it.week} (${it.year})</div>
          <div class="arch-meta">Généré le ${it.generated_at || '—'}</div>
        </div>
        <button class="btn btn-ghost" onclick="reloadWeek(${it.year}, ${it.week})">Voir l'aperçu</button>
      </div>
    `).join('');
  } catch(e){
    box.innerHTML = `<div class="loading" style="color:var(--danger)">Erreur : ${e.message}</div>`;
  }
}

function reloadWeek(year, week){
  document.getElementById('wk-input').value = year + '-W' + String(week).padStart(2, '0');
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.querySelector('.nav-btn').classList.add('active');
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.getElementById('tab-preview').classList.add('active');
  loadPreview();
}

async function copyPreviewHtml(){
  const html = document.getElementById('preview').innerHTML;
  try {
    await navigator.clipboard.writeText(html);
    showToast('HTML copié dans le presse-papier.', 'success');
  } catch(e){
    showToast('Impossible de copier : ' + e.message, 'danger');
  }
}

function openSendModal(){
  document.getElementById('send-modal').classList.add('open');
}
function closeSendModal(){
  document.getElementById('send-modal').classList.remove('open');
}

async function confirmSend(){
  const w = getSelectedWeek();
  if (!w){ showToast('Choisissez une semaine.', 'danger'); return; }
  const btn = document.getElementById('btn-send-confirm');
  btn.disabled = true; btn.textContent = 'Envoi en cours…';
  try {
    const r = await fetch('/api/reports/weekly/send', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ year: w.year, week: w.week, dry_run: false }),
    });
    if (!r.ok){
      const err = await r.text();
      showToast('Erreur : ' + err, 'danger');
    } else {
      const j = await r.json();
      showToast(`Rapport envoyé à ${j.count_sent} destinataire(s).`, 'success');
      closeSendModal();
    }
  } catch(e){
    showToast('Erreur réseau : ' + e.message, 'danger');
  } finally {
    btn.disabled = false; btn.textContent = 'Confirmer l\'envoi';
  }
}

document.getElementById('btn-refresh').onclick = loadPreview;
document.getElementById('btn-copy').onclick = copyPreviewHtml;
document.getElementById('wk-input').onchange = loadPreview;

if (CAN_SEND){
  const bs = document.getElementById('btn-send');
  bs.style.display = 'inline-block';
  bs.onclick = openSendModal;
  document.getElementById('btn-send-confirm').onclick = confirmSend;
}
if (CAN_SWITCH){
  document.getElementById('role-selector-wrap').style.display = 'block';
  const sel = document.getElementById('role-select');
  sel.value = ROLE;
  sel.onchange = loadPreview;
}

document.getElementById('theme-btn').onclick = () => {
  try {
    if (window.MySifaTheme) { MySifaTheme.toggleMode(); }
    else { document.body.classList.toggle('light'); }
  } catch(e) { document.body.classList.toggle('light'); }
};
try { if (window.MySifaTheme) MySifaTheme.initFromStorage(); } catch(e){}

document.getElementById('logout-btn').onclick = async () => {
  try { await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' }); } catch(e){}
  location.href = '/';
};

document.getElementById('sb-ov').onclick = () => document.body.classList.remove('sb-open');

// User chip + synchronisation du thème/palette depuis les préférences serveur
(async () => {
  try {
    const r = await fetch('/api/auth/me', { credentials: 'include' });
    if (!r.ok) return;
    const u = await r.json();
    const chip = document.getElementById('sb-user-chip');
    chip.innerHTML = `<div class="uc-name">${u.nom || u.email || 'Utilisateur'}</div><div class="uc-role">${u.role || ''}</div>`;
    // Applique la palette / le mode enregistrés côté serveur (theme_prefs) si disponibles
    try { if (window.MySifaTheme) MySifaTheme.mergeFromUser(u); } catch(e){}
  } catch(e){}
})();

initDefaultWeek();
loadPreview();
try{switchTab(_readReportsTab(),{silent:true});}catch(e){}
window.addEventListener('hashchange',function(){try{switchTab(_readReportsTab(),{silent:true});}catch(e){}});
</script>
</body>
</html>
"""

"""Paramètres MySifa — super administrateur uniquement."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import APP_VERSION
from services.auth_service import get_current_user, is_superadmin
from app.web.access_denied import access_denied_response

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
    return HTMLResponse(content=SETTINGS_HTML.replace("__V_LABEL__", f"v{APP_VERSION}"))


SETTINGS_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0f172a">
<title>Paramètres — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="stylesheet" href="/static/support_widget.css">
<style>
:root{--bg:#0f172a;--card:#1e293b;--border:#334155;--text:#f1f5f9;--muted:#cbd5e1;--accent:#22d3ee;--ok:#34d399;--danger:#f87171;}
body.light{--bg:#f8fafc;--card:#fff;--border:#e2e8f0;--text:#0f172a;--muted:#64748b;--accent:#0891b2;--ok:#059669;--danger:#dc2626;}
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,-apple-system,'Segoe UI',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;}
.layout{display:flex;min-height:100vh}
.sidebar{width:220px;background:var(--card);border-right:1px solid var(--border);padding:20px 12px;display:flex;flex-direction:column;flex-shrink:0;height:100vh;position:sticky;top:0;overflow-y:auto;scrollbar-width:none}
.sidebar::-webkit-scrollbar{width:0}
.logo{font-size:15px;font-weight:800;margin-bottom:20px;padding:0 8px}.logo span{color:var(--accent)}
.nav-scroll{flex:1;min-height:0;overflow-y:auto;display:flex;flex-direction:column;gap:6px;margin-bottom:8px}
.nav-btn{display:flex;align-items:center;gap:10px;width:100%;text-align:left;padding:10px 12px;border-radius:8px;border:none;background:transparent;color:var(--text2);font-size:13px;font-weight:500;cursor:pointer;font-family:inherit;transition:background .15s,color .15s,box-shadow .2s;margin-bottom:2px}
.nav-btn:hover,.nav-btn.active{background:rgba(34,211,238,.12);color:var(--accent)}
.nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(34,211,238,.25),0 0 18px rgba(34,211,238,.15)}
body.light .nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(8,145,178,.32),0 0 16px rgba(8,145,178,.12)}
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
.cell-ov{font-size:9px;color:var(--accent);font-weight:700;letter-spacing:.02em}
.form-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;margin-bottom:12px}
input,select{width:100%;padding:10px 12px;border-radius:10px;border:1.5px solid var(--border);background:var(--bg);color:var(--text);font-size:13px;font-family:inherit}
.btn{background:var(--accent);color:#0f172a;border:none;border-radius:10px;padding:10px 18px;font-weight:700;font-size:13px;cursor:pointer;font-family:inherit}
.btn:hover{filter:brightness(1.06)}
.btn-sec{background:transparent;border:1px solid var(--border);color:var(--muted);transition:box-shadow .2s,border-color .15s,color .15s,filter .15s}
.btn-sec:hover{box-shadow:0 0 0 1px rgba(34,211,238,.32),0 0 20px rgba(34,211,238,.2);border-color:rgba(34,211,238,.45);color:var(--accent)}
body.light .btn-sec:hover{box-shadow:0 0 0 1px rgba(8,145,178,.35),0 0 18px rgba(8,145,178,.15);border-color:rgba(8,145,178,.4);color:var(--accent)}
.row-user{display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border)}
.row-user:last-child{border-bottom:none}
.pill{font-size:10px;font-weight:700;padding:2px 8px;border-radius:999px;border:1px solid var(--border)}
.tabs{display:flex;gap:8px;margin-bottom:18px;flex-wrap:wrap}
.hidden{display:none}
.legend{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px}
.legend .item{padding:12px;border:1px solid var(--border);border-radius:10px;font-size:12px}
.legend .item strong{display:block;margin-bottom:6px;font-size:13px}
.toast{position:fixed;bottom:22px;left:50%;transform:translateX(-50%);background:var(--card);border:1px solid var(--border);padding:12px 20px;border-radius:12px;font-size:13px;font-weight:600;box-shadow:0 8px 32px rgba(0,0,0,.35);z-index:900}.toast.err{border-left:3px solid var(--danger)}
@media(max-width:760px){.layout{flex-direction:column}.sidebar{width:100%;flex-direction:row;flex-wrap:wrap;align-items:center}}
</style>
</head>
<body>
<div class="layout">
  <aside class="sidebar">
    <div class="logo">My<span>Sifa</span></div>
    <div class="nav-scroll tabs" style="width:100%;margin:0">
      <button type="button" class="nav-btn active" data-tab="users">Utilisateurs</button>
      <button type="button" class="nav-btn" data-tab="matrix">Matrice d'accès</button>
      <button type="button" class="nav-btn" data-tab="defaults">Référentiel rôles</button>
    </div>
    <div class="sidebar-bottom">
      <button type="button" class="nav-btn back-mysifa" onclick="location.href='/'">
        ← Retour <span class="wm">My<span>Sifa</span></span>
      </button>
      <div class="user-chip" id="sb-user-chip" title="Modifier mon profil">
        <div class="uc-name" id="sb-uc-name">—</div>
        <div class="uc-role" id="sb-uc-role">—</div>
        <div style="font-size:10px;color:var(--accent);margin-top:3px;display:flex;align-items:center;gap:4px">
          <span id="sb-edit-ico"></span> Mon profil
        </div>
      </div>
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
    <h1>Paramètres</h1>
    <p class="sub">Gestion des comptes et visualisation des accès applications — réservé au super administrateur.</p>

    <section id="panel-users">
      <div class="card">
        <h2>Ajouter un utilisateur</h2>
        <div class="form-grid">
          <input type="text" id="cu-nom" placeholder="Nom complet" autocomplete="name">
          <input type="email" id="cu-email" placeholder="Email" autocomplete="off">
          <input type="password" id="cu-pwd" placeholder="Mot de passe (8+)" autocomplete="new-password">
          <select id="cu-role"></select>
          <select id="cu-op"><option value="">— Opérateur lié —</option></select>
          <select id="cu-mac"><option value="">— Machine (fabrication) —</option></select>
        </div>
        <button type="button" class="btn" id="cu-go">Créer le compte</button>
      </div>
      <div class="card">
        <h2>Utilisateurs</h2>
        <div id="users-list"></div>
      </div>
    </section>

    <section id="panel-matrix" class="hidden">
      <div class="card">
        <h2>Qui a accès à quoi</h2>
        <p class="sub" style="margin-top:-8px">Cases à cocher : accès effectif (héritage du rôle ou surcharges). « Perso » = différent du défaut du rôle. Paramètres reste réservé au rôle super admin. Les super admins ont tout ; la ligne est en lecture seule.</p>
        <div class="table-wrap" id="matrix-table"></div>
      </div>
    </section>

    <section id="panel-defaults" class="hidden">
      <div class="card">
        <h2>Accès par défaut selon le rôle</h2>
        <p class="sub" style="margin-top:-8px">Chaque utilisateur hérite de ces accès selon son rôle assigné.</p>
        <div class="legend" id="role-legend"></div>
      </div>
    </section>
  </main>
</div>
<script src="/static/support_widget.js"></script>
<script>
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

function setTab(id) {
  document.querySelectorAll('.nav-btn[data-tab]').forEach(b => {
    b.classList.toggle('active', b.dataset.tab === id);
  });
  ['users', 'matrix', 'defaults'].forEach(p => {
    document.getElementById('panel-' + p).classList.toggle('hidden', p !== id);
  });
}

document.querySelectorAll('.nav-btn[data-tab]').forEach(b => {
  b.addEventListener('click', () => setTab(b.dataset.tab));
});

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
  document.body.classList.toggle('light');
  localStorage.setItem('theme', document.body.classList.contains('light') ? 'light' : 'dark');
  syncThemeBtn();
};
document.getElementById('logout-btn').onclick = async () => {
  try { await api('/api/auth/logout', { method: 'POST' }); } catch (e) {}
  location.href = '/';
};
if (localStorage.getItem('theme') === 'light') document.body.classList.add('light');
syncThemeBtn();

document.getElementById('sb-user-chip').onclick = () => { location.href = '/prod?page=profil'; };

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
  window.__meUser = me;
  const nm = document.getElementById('sb-uc-name');
  const rr = document.getElementById('sb-uc-role');
  const ed = document.getElementById('sb-edit-ico');
  if (nm) nm.textContent = me.nom || '';
  if (rr) rr.textContent = roleLabels[me.role] || me.role || '';
  if (ed) ed.innerHTML = iconSvg('edit', 10);
}

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s == null ? '' : String(s);
  return d.innerHTML;
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
}

function fillRoleSelect() {
  const s = document.getElementById('cu-role');
  s.innerHTML = assignableRoles.map(r =>
    '<option value="' + esc(r) + '">' + esc(roleLabels[r] || r) + '</option>'
  ).join('');
}

async function loadUsers() {
  const list = await api('/api/users');
  const box = document.getElementById('users-list');
  if (!Array.isArray(list) || !list.length) {
    box.innerHTML = '<p class="sub">Aucun utilisateur.</p>';
    return;
  }
  box.innerHTML = list.map(u => {
    const act = Number(u.actif) === 1;
    return '<div class="row-user">' +
      '<div><strong>' + esc(u.nom) + '</strong> <span class="pill">' + esc(roleLabels[u.role] || u.role) + '</span>' +
      (act ? '' : ' <span class="pill">Inactif</span>') +
      '<div style="font-size:11px;color:var(--muted);margin-top:4px">' + esc(u.email) + '</div></div>' +
      '<div style="display:flex;gap:6px;flex-wrap:wrap">' +
      '<button type="button" class="btn btn-sec" data-edit="' + u.id + '">Modifier</button>' +
      '<button type="button" class="btn btn-sec" data-reset="' + u.id + '">Reset MDP</button>' +
      (act ? '<button type="button" class="btn btn-sec" data-off="' + u.id + '">Désactiver</button>'
        : '<button type="button" class="btn btn-sec" data-on="' + u.id + '">Réactiver</button>') +
      '</div></div>';
  }).join('');

  box.querySelectorAll('[data-edit]').forEach(b => b.onclick = () => openEdit(Number(b.dataset.edit)));
  box.querySelectorAll('[data-reset]').forEach(b => b.onclick = () => resetPwd(Number(b.dataset.reset)));
  box.querySelectorAll('[data-off]').forEach(b => b.onclick = () => setActif(Number(b.dataset.off), 0));
  box.querySelectorAll('[data-on]').forEach(b => b.onclick = () => setActif(Number(b.dataset.on), 1));
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

function syncCuRoleUI() {
  const r = document.getElementById('cu-role').value;
  const hideOp = ['direction', 'administration', 'logistique', 'comptabilite', 'expedition', 'superadmin'].indexOf(r) >= 0;
  document.getElementById('cu-op').style.display = hideOp ? 'none' : '';
  document.getElementById('cu-mac').style.display = r === 'fabrication' ? '' : 'none';
}
document.getElementById('cu-role').addEventListener('change', syncCuRoleUI);

document.getElementById('cu-go').onclick = async () => {
  const nom = document.getElementById('cu-nom').value.trim();
  const email = document.getElementById('cu-email').value.trim();
  const password = document.getElementById('cu-pwd').value;
  const role = document.getElementById('cu-role').value;
  const operateur_lie = document.getElementById('cu-op').value || null;
  const mid = document.getElementById('cu-mac').value;
  const machine_id = mid ? Number(mid) : null;
  if (!nom || !email || !password || !role) return toast('Champs requis', true);
  try {
    await api('/api/users', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nom, email, password, role, operateur_lie, machine_id }) });
    toast('Utilisateur créé');
    document.getElementById('cu-nom').value = '';
    document.getElementById('cu-email').value = '';
    document.getElementById('cu-pwd').value = '';
    await loadUsers();
    await loadMatrix();
  } catch (e) { toast(e.message, true); }
};

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
    '<label class="sub">Email</label><input id="ed-email" type="email" value="' + esc(u.email) + '" style="margin-bottom:10px"' + (isDesignatedSup ? ' disabled' : '') + '>' +
    '<label class="sub">Rôle</label><select id="ed-role" style="margin-bottom:10px"' + (isDesignatedSup ? ' disabled' : '') + '>' + roleOpts + '</select>' +
    '<div id="ed-op-wrap"><label class="sub">Opérateur lié</label><select id="ed-op" style="margin-bottom:10px">' +
    '<option value="">—</option>' + operators.map(o => '<option value="' + esc(o) + '"' + (u.operateur_lie === o ? ' selected' : '') + '>' + esc(o) + '</option>').join('') + '</select></div>' +
    '<div id="ed-mac-wrap"><label class="sub">Machine</label><select id="ed-mac" style="margin-bottom:10px">' +
    '<option value="">—</option>' + machines.map(m => '<option value="' + esc(m.id) + '"' + (String(u.machine_id) === String(m.id) ? ' selected' : '') + '>' + esc(m.nom) + '</option>').join('') + '</select></div>' +
    '<label class="sub" style="display:flex;align-items:center;gap:8px"><input type="checkbox" id="ed-act" ' + (Number(u.actif) === 1 ? 'checked' : '') + '> Compte actif</label>' +
    '<label class="sub">Nouveau mot de passe (optionnel)</label><input id="ed-pwd" type="password" style="margin-bottom:10px">' +
    '<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:14px">' +
    '<button type="button" class="btn btn-sec" id="ed-cancel">Annuler</button>' +
    '<button type="button" class="btn" id="ed-save">Enregistrer</button></div>';

  function syncEd() {
    const r = dlg.querySelector('#ed-role').value;
    const hideOp = ['direction', 'administration', 'logistique', 'comptabilite', 'expedition', 'superadmin'].indexOf(r) >= 0;
    dlg.querySelector('#ed-op-wrap').style.display = hideOp ? 'none' : '';
    dlg.querySelector('#ed-mac-wrap').style.display = (r === 'fabrication') ? '' : 'none';
  }
  dlg.querySelector('#ed-role').addEventListener('change', syncEd);
  syncEd();

  dlg.querySelector('#ed-cancel').onclick = () => backdrop.remove();
  dlg.querySelector('#ed-save').onclick = async () => {
    const body = {
      nom: dlg.querySelector('#ed-nom').value.trim(),
      email: dlg.querySelector('#ed-email').value.trim(),
      role: dlg.querySelector('#ed-role').value,
      operateur_lie: dlg.querySelector('#ed-op').value || null,
      machine_id: dlg.querySelector('#ed-mac').value ? Number(dlg.querySelector('#ed-mac').value) : null,
      actif: dlg.querySelector('#ed-act').checked ? 1 : 0,
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

async function onAccessToggle(ev) {
  const t = ev.target;
  if (!t || !t.classList || !t.classList.contains('chk-edit')) return;
  const uid = Number(t.dataset.uid);
  const appId = t.dataset.app;
  const checked = t.checked;
  const row = matrixSnapshot.find(r => r.id === uid);
  if (!row || !row.access_default) return;
  const def = !!row.access_default[appId];
  const ov = Object.assign({}, row.access_overrides || {});
  if (checked === def) delete ov[appId];
  else ov[appId] = checked;
  try {
    await api('/api/users/' + uid, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ access_overrides: ov }),
    });
    toast('Accès mis à jour');
    await loadMatrix();
    await loadUsers();
  } catch (e) {
    toast(e.message, true);
    t.checked = !checked;
  }
}

async function loadMatrix() {
  const data = await api('/api/settings/access-matrix');
  if (!data) return;
  apps = data.apps || [];
  roleLabels = data.role_labels || roleLabels;
  const matrix = data.matrix || [];
  matrixSnapshot = matrix;

  const th = '<th>Utilisateur</th><th>Rôle</th>' + apps.map(a => '<th title="' + esc(a.hint || '') + '">' + esc(a.label) + '</th>').join('');
  const tr = matrix.map(row => {
    const isRowSuper = row.role === 'superadmin';
    const cells = apps.map(a => {
      const ok = row.access && row.access[a.id];
      const hasOv = row.access_overrides && Object.prototype.hasOwnProperty.call(row.access_overrides, a.id);
      if (a.id === 'settings' || isRowSuper) {
        return '<td class="chk"><span class="dot' + (ok ? '' : ' no') + '" title="Non modifiable ici"></span></td>';
      }
      const perso = hasOv ? '<span class="cell-ov">perso</span>' : '';
      return '<td class="chk"><label style="display:flex;flex-direction:column;align-items:center;gap:3px;cursor:pointer;margin:0">' +
        '<input type="checkbox" class="chk-edit" data-uid="' + row.id + '" data-app="' + esc(a.id) + '" ' + (ok ? 'checked' : '') + (Number(row.actif) !== 1 ? ' disabled' : '') + ' />' +
        perso + '</label></td>';
    }).join('');
    const dim = Number(row.actif) !== 1 ? 'opacity:.55' : '';
    return '<tr style="' + dim + '"><td><strong>' + esc(row.nom) + '</strong><div style="font-size:11px;color:var(--muted)">' + esc(row.email) + '</div></td><td>' + esc(row.role_label || row.role) + '</td>' + cells + '</tr>';
  }).join('');
  const wrap = document.getElementById('matrix-table');
  wrap.innerHTML = '<table><thead><tr>' + th + '</tr></thead><tbody>' + tr + '</tbody></table>';
  wrap.querySelectorAll('.chk-edit').forEach(cb => { cb.addEventListener('change', onAccessToggle); });

  const leg = document.getElementById('role-legend');
  leg.innerHTML = (data.role_defaults || []).map(d => {
    const bits = apps.map(a => {
      const ok = d.access && d.access[a.id];
      return '<span class="dot' + (ok ? '' : ' no') + '" style="margin-right:4px"></span>' + esc(a.label);
    }).join(' · ');
    return '<div class="item"><strong>' + esc(d.label) + '</strong> <code style="font-size:11px">' + esc(d.role) + '</code><div style="margin-top:8px;line-height:1.6">' + bits + '</div></div>';
  }).join('');
}

(async function init() {
  try {
    const meta = await api('/api/settings/access-matrix');
    superadminEmailRef = String(meta.superadmin_email || '').trim().toLowerCase();
    assignableRoles = meta.assignable_roles || [];
    roleLabels = meta.role_labels || {};
    apps = meta.apps || [];
    fillRoleSelect();
    await refreshSidebarUser();
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
</script>
</body>
</html>
"""

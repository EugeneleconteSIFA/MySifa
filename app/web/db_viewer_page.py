"""MySifa — Database Viewer
Route  : /db
Accès  : superadmin + direction
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.services.auth_service import get_current_user
from config import ROLE_SUPERADMIN, ROLE_DIRECTION, APP_VERSION

router = APIRouter()

_ROLES_DB = {ROLE_SUPERADMIN, ROLE_DIRECTION}


@router.get("/db", response_class=HTMLResponse)
def db_viewer_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/db", status_code=302)
        raise
    if user.get("role") not in _ROLES_DB:
        from app.web.access_denied import access_denied_response
        return access_denied_response("Database Viewer")

    user_name = user.get("display_name") or user.get("email", "—")
    user_role = user.get("role", "")
    version   = APP_VERSION

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17">
<title>Database — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<style>
*,*::before,*::after{{margin:0;padding:0;box-sizing:border-box}}
:root{{
  --bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;
  --muted:#94a3b8;--accent:#22d3ee;--accent-bg:rgba(34,211,238,.10);
  --ok:#34d399;--danger:#f87171;--warn:#fbbf24;--success:#34d399;
  --sidebar-w:260px;
}}
body.light{{
  --bg:#f1f5f9;--card:#fff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;
  --muted:#64748b;--accent:#0891b2;--accent-bg:rgba(8,145,178,.09);
}}
html,body{{height:100%;overflow:hidden}}
body{{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;font-size:13px}}

/* ── Layout ── */
#app{{display:grid;grid-template-columns:var(--sidebar-w) 1fr;height:100vh;overflow:hidden}}

/* ── Sidebar ── */
.sidebar{{
  background:var(--card);border-right:1px solid var(--border);
  display:flex;flex-direction:column;overflow:hidden;
}}
.sidebar-head{{padding:18px 16px 14px;border-bottom:1px solid var(--border);flex-shrink:0}}
.brand{{font-size:18px;font-weight:900;letter-spacing:-.5px;color:var(--text)}}
.brand span{{color:var(--accent)}}
.brand-sub{{font-size:11px;color:var(--muted);margin-top:2px;display:flex;align-items:center;gap:5px}}
.brand-badge{{
  font-size:9px;font-weight:700;padding:2px 6px;border-radius:4px;
  background:rgba(248,113,113,.15);color:var(--danger);
  border:1px solid rgba(248,113,113,.3);letter-spacing:.3px;text-transform:uppercase;
}}

/* Table search */
.tbl-search{{
  width:100%;margin-top:12px;padding:8px 10px;
  background:var(--bg);border:1px solid var(--border);border-radius:8px;
  color:var(--text);font-size:12px;font-family:inherit;outline:none;
}}
.tbl-search:focus{{border-color:var(--accent)}}

/* Table list */
.tbl-list{{flex:1;overflow-y:auto;padding:6px}}
.tbl-item{{
  display:flex;align-items:center;gap:8px;
  padding:9px 10px;border-radius:8px;cursor:pointer;
  border:1px solid transparent;transition:all .12s;margin-bottom:1px;
}}
.tbl-item:hover{{background:var(--accent-bg);border-color:rgba(34,211,238,.2)}}
.tbl-item.active{{background:var(--accent-bg);border-color:var(--accent)}}
.tbl-item-ico{{
  width:28px;height:28px;border-radius:6px;
  background:var(--bg);border:1px solid var(--border);
  display:flex;align-items:center;justify-content:center;flex-shrink:0;
  color:var(--muted);transition:color .12s;
}}
.tbl-item.active .tbl-item-ico,.tbl-item:hover .tbl-item-ico{{color:var(--accent);border-color:rgba(34,211,238,.3)}}
.tbl-item-info{{flex:1;min-width:0}}
.tbl-item-name{{font-size:12px;font-weight:600;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.tbl-item-meta{{font-size:10px;color:var(--muted);margin-top:1px}}
.tbl-item.active .tbl-item-name{{color:var(--accent)}}
.tbl-rows-badge{{
  font-size:10px;font-weight:700;padding:2px 7px;border-radius:12px;
  background:rgba(34,211,238,.1);color:var(--accent);flex-shrink:0;
}}
body.light .tbl-rows-badge{{background:rgba(8,145,178,.1)}}

/* Sidebar bottom */
.sidebar-bottom{{margin-top:auto;padding:10px 12px;border-top:1px solid var(--border);display:flex;flex-direction:column;gap:6px}}
.user-chip{{padding:9px 10px;border-radius:8px;background:var(--accent-bg)}}
.user-chip .uc-name{{font-size:11px;font-weight:600;color:var(--text)}}
.user-chip .uc-role{{font-size:10px;color:var(--accent);text-transform:uppercase;letter-spacing:.5px}}
.theme-btn,.logout-btn{{
  display:flex;align-items:center;gap:8px;padding:9px 10px;border-radius:8px;
  border:1px solid var(--border);background:transparent;color:var(--text2);
  cursor:pointer;font-size:12px;width:100%;font-family:inherit;transition:all .12s;
}}
.theme-btn:hover{{background:var(--accent-bg);color:var(--accent);border-color:var(--accent)}}
.logout-btn{{border:none}}
.logout-btn:hover{{color:var(--danger);background:rgba(248,113,113,.1)}}
.version{{font-size:10px;color:var(--muted);text-align:center;font-family:monospace;padding-top:2px}}

/* ── Main ── */
.main{{display:flex;flex-direction:column;overflow:hidden}}

/* Stats bar */
.stats-bar{{
  padding:14px 24px;border-bottom:1px solid var(--border);
  display:flex;align-items:center;gap:10px;flex-wrap:wrap;flex-shrink:0;
  background:var(--card);
}}
.stat-pill{{
  display:flex;align-items:center;gap:7px;
  padding:6px 12px;border-radius:8px;
  background:var(--bg);border:1px solid var(--border);
}}
.stat-pill-ico{{color:var(--muted);display:flex}}
.stat-pill-val{{font-size:13px;font-weight:700;color:var(--text)}}
.stat-pill-lbl{{font-size:11px;color:var(--muted)}}
.stat-pill.accent{{background:var(--accent-bg);border-color:rgba(34,211,238,.25)}}
.stat-pill.accent .stat-pill-val{{color:var(--accent)}}

/* Topbar */
.topbar{{
  padding:12px 24px;border-bottom:1px solid var(--border);
  display:flex;align-items:center;gap:10px;flex-shrink:0;
  background:var(--bg);
}}
.topbar-title{{
  font-size:14px;font-weight:700;color:var(--text);
  display:flex;align-items:center;gap:8px;
}}
.topbar-title-tbl{{color:var(--accent)}}
.topbar-title-sep{{color:var(--muted);font-weight:400}}
.topbar-actions{{display:flex;align-items:center;gap:8px;margin-left:auto;flex-wrap:wrap}}

/* Row search */
.row-search{{
  padding:8px 12px;background:var(--card);border:1px solid var(--border);border-radius:8px;
  color:var(--text);font-size:12px;font-family:inherit;outline:none;width:220px;
}}
.row-search:focus{{border-color:var(--accent)}}

/* Page nav */
.page-nav{{display:flex;align-items:center;gap:4px}}
.page-btn{{
  padding:6px 10px;border-radius:7px;border:1px solid var(--border);
  background:transparent;color:var(--text2);cursor:pointer;font-size:12px;
  font-family:inherit;transition:all .12s;
}}
.page-btn:hover:not(:disabled){{border-color:var(--accent);color:var(--accent)}}
.page-btn:disabled{{opacity:.35;cursor:not-allowed}}
.page-info{{font-size:12px;color:var(--muted);padding:0 6px;white-space:nowrap}}

/* Limit select */
.limit-sel{{
  padding:6px 8px;border-radius:7px;border:1px solid var(--border);
  background:var(--card);color:var(--text2);font-size:12px;font-family:inherit;
  cursor:pointer;outline:none;
}}
.limit-sel:focus{{border-color:var(--accent)}}

/* Table area */
.tbl-area{{flex:1;overflow:auto;padding:0}}
.data-table{{width:100%;border-collapse:collapse;font-size:12px}}
.data-table th{{
  position:sticky;top:0;z-index:2;
  padding:9px 12px;
  background:var(--card);border-bottom:2px solid var(--border);
  font-size:10px;font-weight:700;color:var(--muted);
  text-transform:uppercase;letter-spacing:.5px;
  text-align:left;white-space:nowrap;cursor:pointer;user-select:none;
  transition:color .12s;
}}
.data-table th:hover{{color:var(--accent)}}
.data-table th.sorted{{color:var(--accent)}}
.th-inner{{display:flex;align-items:center;gap:4px}}
.sort-ico{{opacity:.5;font-size:10px}}
.data-table td{{
  padding:8px 12px;border-bottom:1px solid var(--border);
  color:var(--text2);vertical-align:top;max-width:320px;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
}}
.data-table tr:hover td{{background:var(--accent-bg);color:var(--text)}}
.data-table tr:last-child td{{border-bottom:none}}
.td-null{{color:var(--muted);font-style:italic;font-size:11px}}
.td-num{{color:var(--accent);font-family:monospace}}
.td-pk{{
  font-family:monospace;font-size:11px;font-weight:700;
  color:var(--warn);
}}
.td-bool-t{{color:var(--ok);font-weight:700}}
.td-bool-f{{color:var(--danger);font-weight:700}}

/* Schema panel */
.schema-panel{{
  padding:20px 24px;overflow-y:auto;height:100%;
}}
.schema-title{{font-size:14px;font-weight:700;color:var(--text);margin-bottom:16px;display:flex;align-items:center;gap:8px}}
.schema-tbl{{width:100%;border-collapse:collapse;font-size:12px}}
.schema-tbl th{{
  padding:7px 12px;border-bottom:2px solid var(--border);
  font-size:10px;font-weight:700;color:var(--muted);
  text-transform:uppercase;letter-spacing:.5px;text-align:left;
}}
.schema-tbl td{{padding:8px 12px;border-bottom:1px solid var(--border);color:var(--text2)}}
.schema-tbl tr:hover td{{background:var(--accent-bg)}}
.schema-tbl tr:last-child td{{border-bottom:none}}
.type-badge{{
  display:inline-block;padding:2px 7px;border-radius:5px;font-size:10px;font-weight:700;
  font-family:monospace;background:var(--bg);border:1px solid var(--border);color:var(--muted);
}}
.pk-dot{{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--warn);margin-right:4px}}
.nn-dot{{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--ok)}}

/* Empty / loading states */
.state-center{{
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  height:100%;gap:14px;color:var(--muted);
}}
.state-center svg{{opacity:.25}}
.state-center p{{font-size:13px}}
.spinner{{
  width:28px;height:28px;border:3px solid var(--border);border-top-color:var(--accent);
  border-radius:50%;animation:spin .7s linear infinite;
}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}

/* Toast */
.toast-wrap{{position:fixed;bottom:24px;right:24px;z-index:9999;display:flex;flex-direction:column;gap:8px;pointer-events:none}}
.toast{{
  padding:10px 16px;border-radius:10px;font-size:13px;font-weight:600;
  background:var(--card);border:1px solid var(--border);color:var(--text);
  box-shadow:0 4px 20px rgba(0,0,0,.3);animation:slideIn .2s ease;
  pointer-events:auto;
}}
.toast.success{{border-color:var(--ok);color:var(--ok)}}
.toast.danger{{border-color:var(--danger);color:var(--danger)}}
@keyframes slideIn{{from{{transform:translateX(20px);opacity:0}}to{{transform:translateX(0);opacity:1}}}}

/* View toggle */
.view-tabs{{display:flex;gap:4px}}
.view-tab{{
  padding:6px 12px;border-radius:7px;border:1px solid var(--border);
  background:transparent;color:var(--text2);cursor:pointer;font-size:12px;
  font-family:inherit;font-weight:600;transition:all .12s;
}}
.view-tab.active{{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}}
.view-tab:hover:not(.active){{border-color:rgba(34,211,238,.3);color:var(--text)}}

/* Mobile topbar */
.mobile-topbar{{
  display:none;padding:12px 16px;background:var(--card);
  border-bottom:1px solid var(--border);align-items:center;gap:12px;
}}
.mobile-menu-btn{{
  background:none;border:1px solid var(--border);color:var(--text2);
  padding:7px;border-radius:8px;cursor:pointer;display:flex;
}}
@media(max-width:768px){{
  #app{{grid-template-columns:1fr}}
  .sidebar{{
    position:fixed;top:0;left:0;height:100%;width:var(--sidebar-w);
    transform:translateX(-105%);transition:transform .25s;z-index:100;
  }}
  body.sb-open .sidebar{{transform:translateX(0)}}
  .sidebar-overlay{{
    display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:99;
  }}
  body.sb-open .sidebar-overlay{{display:block}}
  .mobile-topbar{{display:flex}}
  .main{{grid-column:1}}
}}
</style>
</head>
<body>

<!-- Mobile topbar -->
<div class="mobile-topbar">
  <button class="mobile-menu-btn" onclick="document.body.classList.toggle('sb-open')">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
  </button>
  <div style="font-size:14px;font-weight:700">My<span style="color:var(--accent)">Sifa</span> <span style="color:var(--muted);font-weight:400">· Base de données</span></div>
</div>
<div class="sidebar-overlay" onclick="document.body.classList.remove('sb-open')"></div>

<div id="app">
  <!-- ── Sidebar ── -->
  <nav class="sidebar">
    <div class="sidebar-head">
      <div class="brand">My<span>Sifa</span> <span style="color:var(--text2);font-size:13px;font-weight:500">Base</span></div>
      <div class="brand-sub">
        <span>Database Viewer</span>
        <span class="brand-badge">lecture seule</span>
      </div>
      <input class="tbl-search" type="search" id="tbl-search"
             placeholder="Filtrer les tables…" oninput="filterTables()" autocomplete="off">
    </div>

    <div class="tbl-list" id="tbl-list">
      <div class="state-center" style="height:120px">
        <div class="spinner"></div>
      </div>
    </div>

    <div class="sidebar-bottom">
      <div class="user-chip">
        <div class="uc-name">{user_name}</div>
        <div class="uc-role">{user_role}</div>
      </div>
      <button class="theme-btn" onclick="toggleTheme()">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
        <span id="theme-label">Thème clair</span>
      </button>
      <button class="logout-btn" onclick="window.location.href='/'">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="15 18 9 12 15 6"/></svg>
        Retour au portail
      </button>
      <div class="version">v{version}</div>
    </div>
  </nav>

  <!-- ── Main ── -->
  <main class="main">
    <!-- Stats bar -->
    <div class="stats-bar" id="stats-bar">
      <div class="spinner" style="width:18px;height:18px;border-width:2px"></div>
    </div>

    <!-- Topbar (table active) -->
    <div class="topbar" id="topbar" style="display:none">
      <div class="topbar-title" id="topbar-title">—</div>
      <div class="topbar-actions">
        <div class="view-tabs">
          <button class="view-tab active" id="tab-data" onclick="switchView('data')">Données</button>
          <button class="view-tab" id="tab-schema" onclick="switchView('schema')">Schéma</button>
        </div>
        <input class="row-search" type="search" id="row-search"
               placeholder="Rechercher dans les données…"
               oninput="onSearchInput()" autocomplete="off">
        <div class="page-nav" id="page-nav">
          <button class="page-btn" id="btn-prev" onclick="changePage(-1)">‹</button>
          <span class="page-info" id="page-info">—</span>
          <button class="page-btn" id="btn-next" onclick="changePage(1)">›</button>
        </div>
        <select class="limit-sel" id="limit-sel" onchange="onLimitChange()">
          <option value="25">25 / page</option>
          <option value="50" selected>50 / page</option>
          <option value="100">100 / page</option>
          <option value="200">200 / page</option>
        </select>
      </div>
    </div>

    <!-- Content -->
    <div id="content" style="flex:1;overflow:hidden;display:flex;flex-direction:column">
      <div class="state-center">
        <svg width="52" height="52" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2">
          <ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14a9 3 0 0 0 18 0V5"/><path d="M3 12a9 3 0 0 0 18 0"/>
        </svg>
        <p>Sélectionnez une table</p>
      </div>
    </div>
  </main>
</div>

<div class="toast-wrap" id="toast-wrap"></div>

<script>
'use strict';

/* ── State ── */
const S = {{
  tables: [],
  filteredTables: [],
  activeTable: null,
  view: 'data',         // 'data' | 'schema'
  page: 1,
  limit: 50,
  search: '',
  orderCol: null,
  orderDir: 'ASC',
  schema: [],
  data: null,           // {{columns, rows, total, pages}}
  loading: false,
}};

/* ── Boot ── */
(async () => {{
  applyStoredTheme();
  await Promise.all([loadStats(), loadTables()]);
}})();

/* ── Theme ── */
function applyStoredTheme() {{
  const t = localStorage.getItem('theme');
  if (t === 'light') document.body.classList.add('light');
  document.getElementById('theme-label').textContent =
    document.body.classList.contains('light') ? 'Thème sombre' : 'Thème clair';
}}
function toggleTheme() {{
  document.body.classList.toggle('light');
  const isLight = document.body.classList.contains('light');
  localStorage.setItem('theme', isLight ? 'light' : 'dark');
  document.getElementById('theme-label').textContent = isLight ? 'Thème sombre' : 'Thème clair';
}}

/* ── API ── */
async function api(path) {{
  const r = await fetch(path, {{credentials:'same-origin'}});
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}}

/* ── Stats ── */
async function loadStats() {{
  try {{
    const d = await api('/api/db/stats');
    const fmt = n => n >= 1e6 ? (n/1e6).toFixed(1)+'M' : n >= 1e3 ? (n/1e3).toFixed(1)+'K' : String(n);
    const size = d.size_mb < 1 ? (d.size_bytes/1024).toFixed(0)+' KB' : d.size_mb.toFixed(2)+' MB';
    document.getElementById('stats-bar').innerHTML = `
      <div class="stat-pill accent">
        <div class="stat-pill-ico">${{dbIco()}}</div>
        <div>
          <div class="stat-pill-val">${{size}}</div>
          <div class="stat-pill-lbl">Taille DB</div>
        </div>
      </div>
      <div class="stat-pill">
        <div class="stat-pill-ico">${{tableIco()}}</div>
        <div>
          <div class="stat-pill-val">${{d.table_count}}</div>
          <div class="stat-pill-lbl">Tables</div>
        </div>
      </div>
      <div class="stat-pill">
        <div class="stat-pill-ico">${{rowsIco()}}</div>
        <div>
          <div class="stat-pill-val">${{fmt(d.total_rows)}}</div>
          <div class="stat-pill-lbl">Lignes totales</div>
        </div>
      </div>
      <div class="stat-pill" style="margin-left:auto">
        <div>
          <div class="stat-pill-val" style="font-family:monospace;font-size:11px">SQLite ${{d.sqlite_version}}</div>
          <div class="stat-pill-lbl">Page size: ${{d.page_size}}B &middot; ${{d.page_count}} pages</div>
        </div>
      </div>
    `;
  }} catch(e) {{
    document.getElementById('stats-bar').innerHTML =
      `<span style="color:var(--danger);font-size:12px">Erreur stats : ${{escHtml(e.message)}}</span>`;
  }}
}}

/* ── Tables list ── */
async function loadTables() {{
  try {{
    S.tables = await api('/api/db/tables');
    S.filteredTables = [...S.tables];
    renderTables();
  }} catch(e) {{
    document.getElementById('tbl-list').innerHTML =
      `<div class="state-center" style="height:120px"><p style="color:var(--danger)">${{escHtml(e.message)}}</p></div>`;
  }}
}}

function renderTables() {{
  const el = document.getElementById('tbl-list');
  if (!S.filteredTables.length) {{
    el.innerHTML = `<div class="state-center" style="height:80px"><p>Aucune table</p></div>`;
    return;
  }}
  el.innerHTML = S.filteredTables.map(t => {{
    const active = S.activeTable === t.name ? ' active' : '';
    const rows = t.row_count >= 1000 ? (t.row_count/1000).toFixed(1)+'K' : String(t.row_count);
    return `<div class="tbl-item${{active}}" onclick="selectTable('${{escAttr(t.name)}}')" title="${{escAttr(t.name)}}">
      <div class="tbl-item-ico">${{tableIco(14)}}</div>
      <div class="tbl-item-info">
        <div class="tbl-item-name">${{escHtml(t.name)}}</div>
        <div class="tbl-item-meta">${{t.col_count}} col · ${{t.row_count.toLocaleString('fr')}} lignes</div>
      </div>
      <div class="tbl-rows-badge">${{rows}}</div>
    </div>`;
  }}).join('');
}}

function filterTables() {{
  const q = (document.getElementById('tbl-search').value || '').toLowerCase();
  S.filteredTables = q ? S.tables.filter(t => t.name.toLowerCase().includes(q)) : [...S.tables];
  renderTables();
}}

/* ── Select table ── */
async function selectTable(name) {{
  if (S.activeTable === name && !S.loading) return;
  S.activeTable = name;
  S.page = 1;
  S.search = '';
  S.orderCol = null;
  S.orderDir = 'ASC';
  S.schema = [];
  S.data = null;
  document.getElementById('row-search').value = '';
  document.getElementById('topbar').style.display = 'flex';
  renderTables();
  updateTopbarTitle();
  if (S.view === 'data') await loadRows();
  else await loadSchema();
}}

function updateTopbarTitle() {{
  const t = S.tables.find(x => x.name === S.activeTable);
  document.getElementById('topbar-title').innerHTML = t
    ? `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14a9 3 0 0 0 18 0V5"/><path d="M3 12a9 3 0 0 0 18 0"/></svg>
       <span class="topbar-title-tbl">${{escHtml(S.activeTable)}}</span>
       <span class="topbar-title-sep">·</span>
       <span style="font-weight:400;color:var(--muted)">${{t.row_count.toLocaleString('fr')}} lignes</span>`
    : escHtml(S.activeTable);
}}

/* ── View toggle ── */
function switchView(v) {{
  S.view = v;
  document.getElementById('tab-data').classList.toggle('active', v==='data');
  document.getElementById('tab-schema').classList.toggle('active', v==='schema');
  document.getElementById('row-search').style.display = v==='data' ? '' : 'none';
  document.getElementById('page-nav').style.display = v==='data' ? '' : 'none';
  document.getElementById('limit-sel').style.display = v==='data' ? '' : 'none';
  if (!S.activeTable) return;
  if (v === 'data') loadRows();
  else loadSchema();
}}

/* ── Rows ── */
let _searchTimer = null;
function onSearchInput() {{
  clearTimeout(_searchTimer);
  _searchTimer = setTimeout(() => {{
    S.search = document.getElementById('row-search').value;
    S.page = 1;
    loadRows();
  }}, 300);
}}

function onLimitChange() {{
  S.limit = parseInt(document.getElementById('limit-sel').value, 10);
  S.page = 1;
  loadRows();
}}

function changePage(delta) {{
  if (!S.data) return;
  const np = S.page + delta;
  if (np < 1 || np > S.data.pages) return;
  S.page = np;
  loadRows();
}}

async function loadRows() {{
  if (!S.activeTable || S.loading) return;
  S.loading = true;
  renderLoading();
  try {{
    let url = `/api/db/table/${{encodeURIComponent(S.activeTable)}}/rows?page=${{S.page}}&limit=${{S.limit}}`;
    if (S.search) url += `&search=${{encodeURIComponent(S.search)}}`;
    if (S.orderCol) url += `&order_col=${{encodeURIComponent(S.orderCol)}}&order_dir=${{S.orderDir}}`;
    S.data = await api(url);
    renderRows();
  }} catch(e) {{
    renderError(e.message);
  }} finally {{
    S.loading = false;
  }}
}}

function renderLoading() {{
  document.getElementById('content').innerHTML =
    `<div class="state-center"><div class="spinner"></div></div>`;
  document.getElementById('page-info').textContent = '—';
}}

function renderError(msg) {{
  document.getElementById('content').innerHTML =
    `<div class="state-center"><p style="color:var(--danger)">${{escHtml(msg)}}</p></div>`;
}}

function renderRows() {{
  const d = S.data;
  if (!d) return;

  // Page info
  const from = d.total === 0 ? 0 : (d.page-1)*d.limit+1;
  const to   = Math.min(d.page*d.limit, d.total);
  document.getElementById('page-info').textContent =
    d.total === 0 ? 'Aucun résultat' : `${{from}}–${{to}} / ${{d.total.toLocaleString('fr')}}`;
  document.getElementById('btn-prev').disabled = d.page <= 1;
  document.getElementById('btn-next').disabled = d.page >= d.pages;

  if (d.total === 0) {{
    document.getElementById('content').innerHTML =
      `<div class="state-center">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <p>Aucun résultat${{S.search ? ` pour « ${{escHtml(S.search)}} »` : ''}}</p>
       </div>`;
    return;
  }}

  // Detect PK columns from schema
  const pkCols = new Set(S.schema.filter(c=>c.pk).map(c=>c.name));

  const thead = `<thead><tr>${{d.columns.map(col => {{
    const sorted = S.orderCol === col;
    const ico = sorted ? (S.orderDir==='ASC'?'↑':'↓') : '↕';
    return `<th class="${{sorted?'sorted':''}}" onclick="sortBy('${{escAttr(col)}}')">
      <div class="th-inner">${{escHtml(col)}}<span class="sort-ico">${{ico}}</span></div>
    </th>`;
  }}).join('')}}</tr></thead>`;

  const tbody = `<tbody>${{d.rows.map(row => {{
    return `<tr>${{row.map((cell, i) => {{
      const col = d.columns[i];
      const isPk = pkCols.has(col);
      if (cell === null || cell === undefined)
        return `<td><span class="td-null">null</span></td>`;
      if (isPk)
        return `<td><span class="td-pk">${{escHtml(String(cell))}}</span></td>`;
      if (typeof cell === 'number' || (typeof cell === 'string' && cell !== '' && !isNaN(Number(cell)) && !/^0\d/.test(cell) && !/[T\-\/:]/.test(cell)))
        return `<td><span class="td-num">${{escHtml(String(cell))}}</span></td>`;
      if (cell === true || cell === 1) return `<td><span class="td-bool-t">✓</span></td>`;
      if (cell === false || cell === 0 && typeof cell === 'boolean') return `<td><span class="td-bool-f">✗</span></td>`;
      const str = String(cell);
      return `<td title="${{escAttr(str.length > 80 ? str : '')}}">${{escHtml(str.length > 120 ? str.slice(0,117)+'…' : str)}}</td>`;
    }}).join('')}}</tr>`;
  }}).join('')}}</tbody>`;

  document.getElementById('content').innerHTML =
    `<div class="tbl-area"><table class="data-table">${{thead}}${{tbody}}</table></div>`;
}}

function sortBy(col) {{
  if (S.orderCol === col) {{
    S.orderDir = S.orderDir === 'ASC' ? 'DESC' : 'ASC';
  }} else {{
    S.orderCol = col;
    S.orderDir = 'ASC';
  }}
  S.page = 1;
  loadRows();
}}

/* ── Schema ── */
async function loadSchema() {{
  if (!S.activeTable) return;
  if (S.schema.length) {{ renderSchema(); return; }}
  S.loading = true;
  renderLoading();
  try {{
    S.schema = await api(`/api/db/table/${{encodeURIComponent(S.activeTable)}}/schema`);
    renderSchema();
  }} catch(e) {{
    renderError(e.message);
  }} finally {{
    S.loading = false;
  }}
}}

function renderSchema() {{
  const cols = S.schema;
  const rows = cols.map(c => {{
    const pkMark = c.pk ? '<span class="pk-dot" title="Clé primaire"></span>' : '';
    const nnMark = c.notnull ? '<span class="nn-dot" title="NOT NULL"></span>' : '<span style="opacity:.2;display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--muted)"></span>';
    const dflt  = c.dflt_value != null ? `<code style="font-size:10px;color:var(--muted)">${{escHtml(String(c.dflt_value))}}</code>` : '<span style="color:var(--muted);font-size:11px">—</span>';
    return `<tr>
      <td style="color:var(--text);font-weight:600">${{pkMark}}${{escHtml(c.name)}}</td>
      <td><span class="type-badge">${{escHtml(c.type)}}</span></td>
      <td style="text-align:center">${{nnMark}}</td>
      <td>${{dflt}}</td>
      <td style="text-align:center;color:var(--muted);font-size:11px">${{c.cid}}</td>
    </tr>`;
  }}).join('');

  const legend = `
    <div style="margin-top:16px;display:flex;gap:16px;font-size:11px;color:var(--muted)">
      <div style="display:flex;align-items:center;gap:5px"><span class="pk-dot"></span> Clé primaire</div>
      <div style="display:flex;align-items:center;gap:5px"><span class="nn-dot"></span> NOT NULL</div>
    </div>`;

  document.getElementById('content').innerHTML = `
    <div class="schema-panel">
      <div class="schema-title">
        ${{tableIco(16)}}
        Schéma — <span style="color:var(--accent)">${{escHtml(S.activeTable)}}</span>
        <span style="font-size:12px;font-weight:400;color:var(--muted)">${{cols.length}} colonne${{cols.length>1?'s':''}}</span>
      </div>
      <table class="schema-tbl">
        <thead><tr>
          <th>Colonne</th><th>Type</th><th style="text-align:center">NN</th>
          <th>Défaut</th><th style="text-align:center">#</th>
        </tr></thead>
        <tbody>${{rows}}</tbody>
      </table>
      ${{legend}}
    </div>`;
}}

/* ── Toast ── */
function showToast(msg, type='info') {{
  const el = document.createElement('div');
  el.className = `toast ${{type}}`;
  el.textContent = msg;
  document.getElementById('toast-wrap').appendChild(el);
  setTimeout(() => el.remove(), 3500);
}}

/* ── Escape helpers ── */
function escHtml(s) {{
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}
function escAttr(s) {{
  return String(s).replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}}

/* ── SVG icons ── */
function dbIco(s=14) {{
  return `<svg width="${{s}}" height="${{s}}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14a9 3 0 0 0 18 0V5"/><path d="M3 12a9 3 0 0 0 18 0"/></svg>`;
}}
function tableIco(s=14) {{
  return `<svg width="${{s}}" height="${{s}}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="3" y1="15" x2="21" y2="15"/><line x1="9" y1="3" x2="9" y2="21"/></svg>`;
}}
function rowsIco(s=14) {{
  return `<svg width="${{s}}" height="${{s}}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><circle cx="3" cy="6" r="1" fill="currentColor"/><circle cx="3" cy="12" r="1" fill="currentColor"/><circle cx="3" cy="18" r="1" fill="currentColor"/></svg>`;
}}
</script>
</body>
</html>"""
    return HTMLResponse(
        content=html,
        headers={{
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        }},
    )

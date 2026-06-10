/* ────────────────────────────────────────────────────────────────────
 * MySifa — Page /prod (standalone) — socle JS
 *
 * Contenu de l'étape 2e :
 *   1. Constantes & helpers globaux (API, isAuthMePath, apiDetailMsg)
 *   2. escHtml / escAttr / api / getYesterday
 *   3. Le state S filtré aux champs MyProd uniquement
 *   4. set / toast / showToast (set sans persistance Expé)
 *   5. Favicon badge + alerts polling + sidebar toggles
 *   6. DOM helper h
 *   7. Icônes SVG (icon, iconEl) + sidebarUserChip
 *   8. Helpers utilitaires (fN, fD, fDSecs, opName, fMin)
 *   9. Rôles (isAdmin, isFabrication, isComptaPlanning, isCommercial,
 *      isSuperAdmin, canViewAllProd, canPlanningNav, canAccessOfTab)
 *  10. ROLE_LABELS, ROLE_BADGE
 *  11. Stub render() — n'affecte pas le placeholder visuel à cette étape
 *
 * Le code est copié littéralement depuis app/web/html.py (lignes 1999-2443
 * principalement) — pas de retraduction manuelle = pas de bug d'inattention.
 *
 * Activation : via le flag PROD_STANDALONE dans .env (par défaut OFF).
 * ──────────────────────────────────────────────────────────────────── */

(function(){
  'use strict';

  // ── 1. Constantes globales ─────────────────────────────────────────
  const API = window.location.origin;

  // À ce stade (étape 2e), on est toujours sur la coquille standalone.
  // INITIAL_APP est fixé à 'prod' — pas de bascule possible via le markup.
  const INITIAL_APP = 'prod';
  const HAS_INITIAL_APP = true;

  function isAuthMePath(p){
    return p === '/api/auth/me' || p.startsWith('/api/auth/me?');
  }

  let authEpoch = 0;

  function apiDetailMsg(detail){
    if(!detail) return '';
    if(typeof detail === 'string') return detail;
    if(Array.isArray(detail)){
      return detail.map(x => {
        if(typeof x === 'string') return x;
        if(x && typeof x === 'object'){
          const loc = Array.isArray(x.loc) ? x.loc.filter(p => p !== 'body').join('.') : '';
          return (loc ? loc + ': ' : '') + (x.msg || x.message || JSON.stringify(x));
        }
        return String(x);
      }).join(' · ');
    }
    if(typeof detail === 'object') return detail.msg || detail.message || JSON.stringify(detail);
    return String(detail);
  }

  // ── 2. Échappement HTML ────────────────────────────────────────────
  function escHtml(s){
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
  function escAttr(s){
    return escHtml(s).replace(/'/g, '&#39;');
  }

  // ── api : appel fetch wrappé avec gestion 401 + auto-refresh badge ─
  async function api(p, o){
    try{
      const r = await fetch(API + p, {credentials: 'include', ...o});
      if(r.status === 401){
        // Ne pas forcer la déconnexion sur /me : une réponse 401 tardive
        // (requête lancée avant la connexion) écrasait l'état après un
        // login réussi. checkAuth() gère l'absence de session via authEpoch.
        if(!isAuthMePath(p)){
          S.user = null;
          S.app = 'login';
          render();
        }
        return null;
      }
      if(!r.ok){
        const e = await r.json().catch(() => ({}));
        throw new Error(apiDetailMsg(e.detail) || ('Erreur ' + r.status));
      }
      const ct = r.headers.get('content-type') || '';
      let out;
      if(ct.includes('spreadsheet') || ct.includes('octet-stream')) out = await r.blob();
      else out = await r.json();
      if(shouldRefreshAlertsFromApi(p, o)) refreshAlertsBadge().catch(() => {});
      return out;
    }catch(e){
      if(e.message.includes('Failed to fetch')) throw new Error('API non disponible');
      throw e;
    }
  }

  // ── getYesterday : date au format YYYY-MM-DD ────────────────────────
  function getYesterday(){
    const d = new Date();
    d.setDate(d.getDate() - 1);
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    return yyyy + '-' + mm + '-' + dd;
  }

  // ── 3. State S — filtré aux champs MyProd uniquement ───────────────
  // Pas de champs expe*/compta*/stock*/paie*/msg* (autres pages standalone).
  let S = {
    // Routing / session
    app: HAS_INITIAL_APP ? INITIAL_APP : 'login',
    page: 'production',
    subPage: 'kpis',          // 'kpis' | 'saisies' | 'erreurs'
    user: null,
    sidebarOpen: false,

    // Authentification
    loginSubmitting: false,
    loginError: null,
    portalLoading: null,

    // Filtres (saisies, production, historique)
    filters: {},
    OPS_CONFIG: {},
    fv: {
      operateurs: [],
      dossiers: [],
      dossierSearchQ: '',
      machines: [],
      date_from: getYesterday(),
      date_to: getYesterday(),
    },
    dossierFilterHi: -1,

    // Pagination saisies
    saisiesOffset: 0,
    saisiesLimit: 200,

    // Données chargées depuis les APIs
    historique: null,
    production: null,
    traceabilite: null,
    machineStatus: null,
    saisies: null,
    imports: [],
    selImp: null,
    impData: null,
    dossiers: [],

    // Traçabilité
    tracFilters: {ref: '', client: '', machine: '', statut: ''},
    tracSort: {col: null, dir: 'asc'},
    tracShowAttente: false,

    // OF (Ordres de Fabrication)
    ofImports: [],
    ofImportsLoading: false,
    ofImportModal: null,
    ofSearch: '',
    ofPage: 0,
    ofTotal: 0,
    ofSubTab: 'of',
    ofSelected: new Set(),
    ofEditModal: null,

    // Fiches techniques
    fiches: [],
    fichesLoading: false,
    ficheSearch: '',
    fichePage: 0,
    ficheTotal: 0,
    ficheSelected: new Set(),
    ficheEditModal: null,

    // Devis / Rentabilité
    devisList: [],
    selDevis: null,
    comparaison: null,
    devisPreview: null,
    rentList: null,
    rentSelEntryId: null,
    rentLinksById: {},
    rentCompById: {},
    rentQuery: '',
    rentTags: [],
    rentOffset: 0,
    rentLimit: 12,

    // UI commune
    importOpen: false,
    selDossier: null,
    toast: null,
    alertsCount: 0,
    msgUnread: 0,
    selectedRows: new Set(),
    sortState: {col: null, asc: true},
    addRowTemplate: null,

    // Contact / support (modal réutilisé sur toutes les pages)
    contactOpen: false,
    contactSubject: '',
    contactMessage: '',
    contactSending: false,
  };
  window.S = S;

  // ── 4. set / toast / showToast ─────────────────────────────────────
  // set() est volontairement simplifié par rapport au monolithe : pas
  // d'appel à expeScheduleSaveLocal (Expé est sur une autre page). Le
  // render() final est un stub à ce stade (étape 2e) — il sera étoffé
  // à l'étape 2f.
  function set(u){
    Object.assign(S, u);
    render();
  }
  function toast(m, t = 'success'){
    set({toast: {message: m, type: t}});
    setTimeout(() => set({toast: null}), 3500);
  }
  function showToast(message, type){
    const t = type === 'danger' ? 'error' : (type === 'success' ? 'success' : 'success');
    toast(message, t);
  }

  // ── 5. Favicon badge + alerts polling + sidebar toggles ────────────
  function updateFaviconBadge(count){
    const canvas = document.createElement('canvas');
    canvas.width = 32; canvas.height = 32;
    const ctx = canvas.getContext('2d');
    if(!ctx) return;

    ctx.fillStyle = '#0a0e17';
    ctx.beginPath();
    if(typeof ctx.roundRect === 'function') ctx.roundRect(0, 0, 32, 32, 6);
    else ctx.rect(0, 0, 32, 32);
    ctx.fill();

    ctx.fillStyle = '#f1f5f9';
    ctx.font = 'bold 20px system-ui';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('M', 16, 17);

    if(count > 0){
      ctx.fillStyle = '#f87171';
      ctx.beginPath();
      ctx.arc(24, 8, 7, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 9px system-ui';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(count > 9 ? '9+' : String(count), 24, 8);
    }

    let link = document.querySelector('link[rel="icon"]');
    if(!link){
      link = document.createElement('link');
      link.rel = 'icon';
      document.head.appendChild(link);
    }
    link.href = canvas.toDataURL();
  }

  async function refreshAlertsBadge(){
    try{
      const r = await api('/api/alerts/count');
      if(r && typeof r.total === 'number'){
        S.alertsCount = r.total;
        updateFaviconBadge(r.total);
      }
    }catch(e){}
  }

  let _alertsBadgeInterval = null;
  function startAlertsBadgePolling(){
    refreshAlertsBadge().catch(() => {});
    if(_alertsBadgeInterval) return;
    _alertsBadgeInterval = setInterval(() => {
      refreshAlertsBadge().catch(() => {});
    }, 60000);
  }

  function shouldRefreshAlertsFromApi(path, opts){
    const m = String((opts && opts.method) || 'GET').toUpperCase();
    if(m === 'GET') return false;
    const p = String(path || '');
    if(p.includes('/api/alerts/count')) return false;
    return /\/api\/(messages|expe\/departs|dossiers|planning)/.test(p);
  }

  // Polling temps réel statut machines (15 s) — admin uniquement.
  // Repris de app/web/html.py (lignes 2519, 2532-2540).
  let _mstInterval = null;
  function startMachineStatusPolling(){
    if(_mstInterval) return;
    if(!isAdmin(S.user)) return;
    loadMachineStatus().catch(() => {});
    _mstInterval = setInterval(() => { loadMachineStatus().catch(() => {}); }, 15000);
  }
  function stopMachineStatusPolling(){
    if(_mstInterval){ clearInterval(_mstInterval); _mstInterval = null; }
  }

  function closeSidebar(){
    if(S.sidebarOpen){ S.sidebarOpen = false; render(); }
  }
  function toggleSidebar(){
    S.sidebarOpen = !S.sidebarOpen;
    render();
  }

  // ── 6. DOM helper h ────────────────────────────────────────────────
  function h(t, a, ...c){
    const el = document.createElement(t);
    if(a) Object.entries(a).forEach(([k, v]) => {
      if(k === 'className') el.className = v;
      else if(k === 'style' && typeof v === 'object') Object.assign(el.style, v);
      else if(k.startsWith('on')) el.addEventListener(k.slice(2).toLowerCase(), v);
      else if(k === 'disabled' || k === 'checked' || k === 'readonly' || k === 'selected'){
        if(v) el.setAttribute(k, '');
        else el.removeAttribute(k);
      }
      else el.setAttribute(k, v);
    });
    c.flat().forEach(c => {
      if(c == null) return;
      const prim = typeof c === 'string' || typeof c === 'number' || typeof c === 'boolean';
      el.appendChild(prim ? document.createTextNode(String(c)) : c);
    });
    return el;
  }

  // ── 7. Icônes SVG (Feather style) ──────────────────────────────────
  function icon(name, size = 16){
    const a = `width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"`;
    const p = {
      'bar-chart-2': '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
      'calendar': '<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>',
      'trending-up': '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>',
      'users': '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
      'user': '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
      'pencil': '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>',
      'alert-triangle': '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
      'alert-circle': '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>',
      'wrench': '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
      'package': '<line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/>',
      'search': '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
      'sun': '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>',
      'moon': '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>',
      'log-out': '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
      'trash': '<polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>',
      'cloud-upload': '<polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/>',
      'upload': '<polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/>',
      'download': '<polyline points="8 17 12 21 16 17"/><line x1="12" y1="21" x2="12" y2="12"/><path d="M20.88 18.09A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.29"/>',
      'copy': '<rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
      'save': '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>',
      'eye': '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
      'clock': '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
      'folder': '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>',
      'file': '<path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/>',
      'play': '<polygon points="5 3 19 12 5 21 5 3"/>',
      'check-circle': '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
      'x': '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
      'arrow-right': '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>',
      'menu': '<line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/>',
      'home': '<path d="M3 10.5L12 3l9 7.5"/><path d="M5 10v11h14V10"/><path d="M10 21v-6h4v6"/>',
      'mail': '<path d="M4 6h16v12H4z"/><path d="M4 7l8 6 8-6"/><path d="M4 17l6-5"/><path d="M20 17l-6-5"/>',
      'send': '<line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>',
      'plus': '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
      'edit': '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>',
      'rotate-ccw': '<polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-4.5"/>',
      'rotate-cw': '<polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-.49-4.5"/>',
      'lock': '<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
      'box': '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>',
      'calculator': '<rect x="6" y="2.5" width="12" height="19" rx="2"/><line x1="8" y1="7" x2="16" y2="7"/><line x1="9" y1="11" x2="10" y2="11"/><line x1="12" y1="11" x2="13" y2="11"/><line x1="15" y1="11" x2="16" y2="11"/><line x1="9" y1="14" x2="10" y2="14"/><line x1="12" y1="14" x2="13" y2="14"/><line x1="15" y1="14" x2="16" y2="14"/><line x1="9" y1="17" x2="10" y2="17"/><line x1="12" y1="17" x2="13" y2="17"/><line x1="15" y1="17" x2="16" y2="17"/>',
      'truck': '<path d="M3 7h11v10H3z"/><path d="M14 10h4l3 3v4h-7z"/><circle cx="7.5" cy="17" r="2"/><circle cx="17.5" cy="17" r="2"/>',
      'sliders': '<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/>',
      'layers': '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
      'arrow-left': '<line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>',
      'printer': '<polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/>',
      'clipboard': '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/>',
      'activity': '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
      'tool': '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
      'credit-card': '<rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/>',
      'file-text': '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>',
      'grid': '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>',
      'tag': '<path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/>',
      'map-pin': '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>',
      'database': '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14a9 3 0 0 0 18 0V5"/><path d="M3 12a9 3 0 0 0 18 0"/>',
      'palette': '<circle cx="13.5" cy="6.5" r=".5" fill="currentColor"/><circle cx="17.5" cy="10.5" r=".5" fill="currentColor"/><circle cx="8.5" cy="7.5" r=".5" fill="currentColor"/><circle cx="6.5" cy="12.5" r=".5" fill="currentColor"/><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z"/>',
      'shield-check': '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/>',
    };
    return `<svg ${a} aria-hidden="true" style="display:inline-block;vertical-align:middle;flex-shrink:0">${p[name] || p['alert-circle']}</svg>`;
  }

  function iconEl(name, size = 16){
    const s = document.createElement('span');
    s.style.cssText = 'display:inline-flex;align-items:center;flex-shrink:0';
    s.innerHTML = icon(name, size);
    return s;
  }

  function sidebarUserChip(user, opts){
    if(!user) return null;
    opts = opts || {};
    if(window.MySifaUserChip){
      return MySifaUserChip.element(user, h, iconEl, Object.assign({
        title: 'Mon profil',
        onClick: () => { window.location.href = '/profil'; }
      }, opts));
    }
    return h('div', {
      className: opts.chipClass || 'user-chip',
      style: {cursor: 'pointer'},
      title: 'Mon profil',
      onClick: () => { window.location.href = '/profil'; }
    },
      h('div', {className: 'uc-name'}, user.nom || ''),
      h('div', {className: 'uc-role'}, ROLE_LABELS[user.role] || user.role || ''),
      h('div', {className: 'uc-profil'}, iconEl('edit', 10), ' Mon profil')
    );
  }

  // ── 8. Helpers utilitaires de format ───────────────────────────────
  const fN = n => n ? Number(n).toLocaleString('fr-FR') : '0';
  const fD = d => d ? d.replace(/C$/, '').replace('T', ' ').slice(0, 16) : '-';
  const fDSecs = d => {
    if(!d) return '-';
    const s = String(d).replace(/C$/, '').trim().replace('T', ' ');
    const fr = s.match(/^(\d{2}\/\d{2}\/\d{4})\s+(\d{2}):(\d{2})(?::(\d{2}))?/);
    if(fr) return fr[1] + ' ' + fr[2] + ':' + fr[3] + ':' + (fr[4] != null ? fr[4] : '00');
    const iso = s.match(/^(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})(?::(\d{2}))?/);
    if(iso) return iso[3] + '/' + iso[2] + '/' + iso[1] + ' ' + iso[4] + ':' + iso[5] + ':' + (iso[6] != null ? iso[6] : '00');
    return s.slice(0, 19);
  };
  const opName = s => {
    if(!s) return '';
    const p = s.split(' - ');
    return p.length > 1 ? p.slice(1).join(' - ') : s;
  };
  const fMin = m => {
    if(!m && m !== 0) return '-';
    const hh = Math.floor(m / 60);
    const mm = Math.round(m % 60);
    return hh > 0 ? hh + 'h ' + String(mm).padStart(2, '0') + 'min' : mm + 'min';
  };

  // ── 9. Rôles ───────────────────────────────────────────────────────
  const isAdmin = u => u && (u.role === 'direction' || u.role === 'administration' || u.role === 'superadmin');
  const canViewAllProd = u => u && (isAdmin(u) || u.role === 'commercial' || u.role === 'expedition');
  const isComptaPlanning = u => u && (u.role === 'comptabilite' || u.role === 'logistique');
  const canPlanningNav = u => !!(u && u.app_access && u.app_access.planning);
  const isFab = u => u && u.role === 'fabrication';
  const isFabrication = isFab;       // alias plus explicite
  const isCommercial = u => u && u.role === 'commercial';
  const isSuperAdmin = u => !!(u && u.role === 'superadmin');

  // ── 10. Référentiels rôles ─────────────────────────────────────────
  const ROLE_LABELS = {
    direction: 'Direction',
    administration: 'Administration',
    fabrication: 'Fabrication',
    logistique: 'Logistique',
    comptabilite: 'Comptabilité',
    expedition: 'Expédition',
    commercial: 'Commercial',
    superadmin: 'Super admin',
  };
  const ROLE_BADGE = {
    direction: 'badge-direction',
    administration: 'badge-administration',
    fabrication: 'badge-fabrication',
    logistique: 'badge-fabrication',
    comptabilite: 'badge-administration',
    expedition: 'badge-administration',
    superadmin: 'badge-direction',
  };

  function canAccessOfTab(){
    return isAdmin(S.user);
  }


  // ────────────────────────────────────────────────────────────────────
  // ÉTAPE 2g — Loads + Page Production (KPIs)
  //
  // Code extrait littéralement de app/web/html.py :
  //   - Loads + buildParams : lignes 6871-6985
  //   - renderProdPage : lignes 8787-8816
  //   - Helpers prodSynth : lignes 8988-9170
  //   - renderProdKpis : lignes 9172-9294
  //
  // Stubs temporaires (remplacés en 2h/2i) :
  //   - renderMachineStatusCards (2h)
  //   - renderSanity (2h)
  //   - renderHist (2i)
  //   - renderSaisiesWithImport (2i)
  // ────────────────────────────────────────────────────────────────────

  // ── Stubs renvoyant un placeholder visuel ──────────────────────────
  function renderMachineStatusCards(){
    return h('div', {className: 'card-empty', style: {padding: '16px', fontStyle: 'italic'}},
      'Statut machines — sera ajouté à l\u0027étape 2h.');
  }
  function renderSanity(sanity, title){
    return null;  // Sanity reviendra en 2h via renderSanityEventsBlock
  }
  function renderHist(){
    return h('div', {className: 'card-empty', style: {padding: '24px'}},
      'Historique & Erreurs — sera ajouté à l\u0027étape 2i.');
  }
  function renderSaisiesWithImport(){
    return h('div', {className: 'card-empty', style: {padding: '24px'}},
      'Saisies — sera ajouté à l\u0027étape 2i.');
  }
  function renderSaisies(){ return renderSaisiesWithImport(); }

async function loadFilters(){
  try{
    S.filters=await api('/api/filters')||{};
    S.OPS_CONFIG=await api('/api/config/operations')||{};
    // Pour utilisateur fabrication: auto-sélectionner son nom comme filtre opérateur
    // pour qu'il voie immédiatement ses données de saisie
    if(isFab(S.user) && S.user && S.user.nom){
      const userOp = S.user.nom;
      const ops = S.filters.operators || [];
      // Si l'utilisateur n'est pas déjà dans la sélection et qu'il existe dans la liste
      if(!S.fv.operateurs.length && ops.includes(userOp)){
        S.fv.operateurs = [userOp];
      }
    }
  }catch{}
}
function buildParams(){
  const p=new URLSearchParams();
  if(canViewAllProd(S.user)){
    (S.fv.operateurs||[]).forEach(o=>p.append('operateur',o));
    (S.fv.dossiers||[]).forEach(d=>p.append('no_dossier',d));
  }
  (S.fv.machines||[]).forEach(m=>p.append('machine',m));
  if(S.fv.date_from)p.set('date_from',S.fv.date_from);
  if(S.fv.date_to)p.set('date_to',S.fv.date_to);
  return p;
}

async function loadHist(){const d=await api('/api/dashboard/historique?'+buildParams());if(d)S.historique=d;}
async function loadProd(){const d=await api('/api/dashboard/production?'+buildParams());if(d)S.production=d;}
async function loadMachineStatus(){
  try{
    const d=await api('/api/production/machine-status');
    if(d){
      S.machineStatus=d;
      // Mise à jour DOM ciblée sans re-render global
      updateMachineStatusDOM();
    }
  }catch(e){}
}
function updateMachineStatusDOM(){
  const ms=S.machineStatus;
  const ICONS={production:'▶',calage:'⚙',arret:'⛔',changement:'↻',nettoyage:'🧹',eteinte:'○',autre:'·'};
  const DUREE_LABEL={production:'En production depuis',calage:'En calage depuis',arret:'En arrêt depuis',changement:'En changement depuis',nettoyage:'En nettoyage depuis',eteinte:'Éteinte depuis',autre:'Depuis'};
  function fmtDuree(min){
    if(min==null||min<0)return null;
    if(min<1)return 'à l\'instant';
    const h=Math.floor(min/60),m=min%60;
    if(h===0)return m+' min';
    return m===0?(h+'h'):(h+'h '+m+'min');
  }
  const grid=document.querySelector('.mst-grid');
  if(!grid)return;
  const cards=grid.querySelectorAll('.mst-card');
  cards.forEach((card,idx)=>{
    const mkey=idx===0?'C1':'C2';
    const m=ms&&ms[mkey];
    const sk=m?(m.statut_key||'eteinte'):'eteinte';
    const label=m?(m.statut_label||'Éteinte'):'Éteinte';
    const nom=m?m.nom:(mkey==='C1'?'Cohésio 1':'Cohésio 2');
    const op=m?(m.operateur||''):'';
    const dos=m?m.dossier:null;
    const icon=ICONS[sk]||'·';
    const isOn=sk!=='eteinte';
    const dureeStr=m?fmtDuree(m.duree_min):null;
    const dureeLabel=DUREE_LABEL[sk]||'Depuis';
    // Mise à jour classes et contenu
    card.className='mst-card mst-'+sk;
    const headNom=card.querySelector('.mst-nom');
    if(headNom)headNom.textContent=nom;
    const dotWrap=card.querySelector('.mst-head div');
    if(dotWrap){
      dotWrap.innerHTML=isOn?'<span style="font-size:8px;color:#22c55e;animation:pulse 2s infinite;display:inline-block;border-radius:50%;width:8px;height:8px;background:#22c55e"></span><span class="mst-dot"></span>':'<span class="mst-dot"></span>';
    }
    const body=card.querySelector('.mst-body');
    if(body){
      let html='<div class="mst-statut">'+icon+' '+label+'</div>';
      if(dureeStr)html+='<div class="mst-duree">'+dureeLabel+' <span class="mst-duree-val">'+dureeStr+'</span></div>';
      if(op)html+='<div class="mst-op">👤 '+escapeHtml(op)+'</div>';
      if(dos&&dos.no_dossier){
        const isChangement=sk==='changement';
        const dosStyle=isChangement?' style="opacity:.6;filter:grayscale(.4)"':'';
        const dosPrefix=isChangement?'dossier précédent : #':'Dossier #';
        html+='<div class="mst-dos"'+dosStyle+'><div class="mst-dos-ref">'+dosPrefix+escapeHtml(dos.no_dossier)+'</div>';
        if(dos.client)html+='<div class="mst-dos-cli">'+escapeHtml(dos.client)+'</div>';
        if(dos.designation)html+='<div class="mst-dos-des">'+escapeHtml(dos.designation)+'</div>';
        html+='</div>';
      }
      body.innerHTML=html;
    }
  });
}
function escapeHtml(t){return(t||'').replace(/[&<>"']/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
async function loadImports(){const d=await api('/api/imports');if(d)set({imports:d});}
async function loadDos(){const d=await api('/api/dossiers');if(d)set({dossiers:d});}
async function loadMachines(){try{const d=await api('/api/planning/machines');if(d)set({machines:d});}catch(e){}}
async function loadRentPlanning(){
  try{
    const d=await api('/api/rentabilite/planning-entries');
    if(d)set({rentList:d});
  }catch(e){
    toast(e.message,'error');
  }
}
async function loadSaisies(opts){
  const off = (opts && typeof opts.offset==='number') ? opts.offset : (S.saisiesOffset||0);
  const lim = (opts && typeof opts.limit==='number') ? opts.limit : (S.saisiesLimit||200);
  const d=await api('/api/saisies?'+buildParams()+'&limit='+encodeURIComponent(String(lim))+'&offset='+encodeURIComponent(String(off)));
  if(!d)return;
  S.saisiesOffset = off;
  S.saisiesLimit = lim;
  if(opts&&opts.noRender)S.saisies=d;
  else set({saisies:d});
}
async function loadDevis(){const d=await api('/api/rentabilite/devis');if(d)set({devisList:d});}

function renderProdPage(){
  const subPage = S.subPage || 'kpis';
  // Gestion du polling temps réel machines
  if(subPage==='kpis'){startMachineStatusPolling();}
  else{stopMachineStatusPolling();}
  const tabs = [
    {key:'kpis',    label:"Vue d'ensemble", icon:'wrench'},
    {key:'saisies', label:'Saisies', icon:'pencil'},
    {key:'erreurs', label:'Erreurs & Qualité', icon:'alert-triangle'},
  ];
  const subNav = h('div',{className:'nav-tabs'},
    ...tabs.map(t=>h('button',{
      type:'button',
      className:'nav-tab'+(subPage===t.key?' active':''),
      onClick:async()=>{
        S.subPage=t.key;
        if(t.key==='kpis'){if(!S.production)await loadProd(); await loadMachineStatus(); startMachineStatusPolling();}
        else{stopMachineStatusPolling();}
        if(t.key==='saisies'&&!S.saisies)  await loadSaisies();
        if(t.key==='erreurs'&&!S.historique) await loadHist();
        render();
      }
    }, iconEl(t.icon,14),' '+t.label))
  );
  let content;
  if(subPage==='saisies')  content = renderSaisiesWithImport();
  else if(subPage==='erreurs') content = renderHist();
  else content = renderProdKpis();
  return h('div',null, subNav, content);
}

function formatJourLabel(j){
  if(!j)return '—';
  const m=String(j).match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if(m)return m[3]+'/'+m[2]+'/'+m[1];
  return String(j);
}
function prodSynthPeriodLabel(){
  const f=S.fv||{};
  if(f.date_from&&f.date_to)return formatJourLabel(f.date_from)+' → '+formatJourLabel(f.date_to);
  if(f.date_from)return 'Depuis le '+formatJourLabel(f.date_from);
  if(f.date_to)return 'Jusqu\'au '+formatJourLabel(f.date_to);
  return 'Période des filtres actifs';
}
function prodSynthDisplayKey(type,key){
  if(type==='operator')return opName(key)||'—';
  if(type==='day')return formatJourLabel(key);
  return String(key||'—');
}
function prodSynthFilterSessions(type,key){
  const rows=(S.production&&S.production.by_dossier)||[];
  const k=String(key||'').trim();
  return rows.filter(r=>{
    if(type==='dossier')return String(r.no_dossier||'').trim()===k;
    if(type==='operator')return String(r.operateur||'?').trim()===k;
    if(type==='machine')return String(r.machine||'?').trim()===k;
    if(type==='day')return String(r.jour||'').trim()===k;
    return false;
  }).sort((a,b)=>{
    const dj=String(b.jour||'').localeCompare(String(a.jour||''));
    if(dj!==0)return dj;
    return opName(a.operateur).localeCompare(opName(b.operateur),'fr');
  });
}
function prodSynthTotals(sessions){
  const t={sessions:sessions.length,etiquettes:0,metrage_m:0,calage_min:0,prod_min:0,arret_min:0};
  sessions.forEach(s=>{
    t.etiquettes+=Number(s.etiquettes||0);
    t.metrage_m+=Number(s.metrage_m||0);
    t.calage_min+=Number(s.temps_calage_min||0);
    t.prod_min+=Number(s.temps_prod_min||0);
    t.arret_min+=Number(s.temps_arret_min||0);
  });
  t.metrage_m=Math.round(t.metrage_m*10)/10;
  const den=t.prod_min+t.arret_min;
  t.vitesse=den>0?(t.metrage_m/den).toFixed(2):'0.00';
  return t;
}
function prodSynthCleanClient(c){
  if(!c)return '';
  const p=String(c).split(' - ');
  if(p.length===2&&/^\d+$/.test(p[0].trim()))return p[1].trim();
  return String(c).trim();
}
function closeProdSynthModal(){
  try{
    const m=document.querySelector('.prod-synth-modal');
    if(m&&m._navKeyHandler){
      document.removeEventListener('keydown',m._navKeyHandler,true);
    }
    if(m)m.remove();
  }catch(e){}
}
function openProdSynthDetail(type,keys,index){
  const list=(keys||[]).map(k=>String(k));
  if(!list.length)return;
  let idx=Number(index);
  if(!Number.isFinite(idx)||idx<0)idx=0;
  if(idx>=list.length)idx=list.length-1;
  const key=list[idx];
  closeProdSynthModal();
  const TYPE_TITLES={dossier:'Dossier',operator:'Opérateur',machine:'Machine',day:'Jour'};
  const sessions=prodSynthFilterSessions(type,key);
  const tot=prodSynthTotals(sessions);
  const total=list.length;
  const goPrev=()=>{if(total>1)openProdSynthDetail(type,list,(idx-1+total)%total);};
  const goNext=()=>{if(total>1)openProdSynthDetail(type,list,(idx+1)%total);};
  const overlay=h('div',{className:'add-row-modal prod-synth-modal'});
  overlay.addEventListener('click',e=>{if(e.target===overlay)closeProdSynthModal();});
  const counter=h('span',{className:'add-row-counter',title:'← → pour naviguer'},
    h('button',{type:'button',className:'add-row-nav-btn',title:'Précédent (←)',disabled:total<=1,onClick:e=>{e.stopPropagation();goPrev();}},'<'),
    h('span',null,String(idx+1)+'/'+String(total)),
    h('button',{type:'button',className:'add-row-nav-btn',title:'Suivant (→)',disabled:total<=1,onClick:e=>{e.stopPropagation();goNext();}},'>')
  );
  const titleRow=h('div',{className:'prod-synth-detail-head'},
    h('div',{className:'prod-synth-detail-title-main'},
      h('span',{className:'prod-synth-detail-eyebrow'}, TYPE_TITLES[type]||'Synthèse'),
      h('h3',{className:'prod-synth-detail-h3'}, prodSynthDisplayKey(type,key))
    ),
    counter
  );
  const kpi=(lbl,val)=>h('div',{className:'prod-synth-kpi'},
    h('div',{className:'lbl'},lbl),
    h('div',{className:'val'},val)
  );
  const showDossierCol=type!=='dossier';
  const sessionRows=sessions.length?sessions.map(s=>{
    const den=Number(s.temps_prod_min||0)+Number(s.temps_arret_min||0);
    const vit=den>0?(Number(s.metrage_m||0)/den).toFixed(2):'0.00';
    const cli=prodSynthCleanClient(s.client);
    const des=(s.designation||'').replace(/^,\s*/,'').trim();
    return h('tr',null,
      h('td',{className:'prod-synth-detail-td-text'},formatJourLabel(s.jour)),
      h('td',{className:'prod-synth-detail-td-text'},opName(s.operateur)),
      h('td',{className:'prod-synth-detail-td-text'},s.machine||'—'),
      showDossierCol?h('td',{className:'prod-synth-detail-td-mono'},s.no_dossier||'—'):null,
      h('td',{className:'prod-synth-detail-td-text'},cli||'—'),
      h('td',{className:'prod-synth-detail-td-wrap'},des||'—'),
      h('td',{className:'prod-synth-detail-td-num'},fN(s.etiquettes||0)),
      h('td',{className:'prod-synth-detail-td-num'},fN(s.metrage_m||0)+' m'),
      h('td',{className:'prod-synth-detail-td-num'},fMin(s.temps_calage_min)),
      h('td',{className:'prod-synth-detail-td-num'},fMin(s.temps_prod_min)),
      h('td',{className:'prod-synth-detail-td-num'},fMin(s.temps_arret_min)),
      h('td',{className:'prod-synth-detail-td-vit'},vit+' m/min')
    );
  }):[h('tr',null,h('td',{colSpan:showDossierCol?11:10,className:'prod-synth-detail-empty'},'Aucune session sur la période filtrée.'))];
  const isMobileSynth=window.innerWidth<=900;
  if(isMobileSynth) overlay.classList.add('prod-synth-modal--compact');
  const sessionsBlock=h('div',{className:'prod-synth-detail-sessions'},
    h('div',{className:'prod-synth-detail-section-h'},'Détail par session'),
    h('div',{className:'prod-synth-detail-table-wrap'},
      h('table',{className:'table-std prod-synth-detail-table'},
        h('thead',null,h('tr',null,
          h('th',null,'Jour'),h('th',null,'Opérateur'),h('th',null,'Machine'),
          showDossierCol?h('th',null,'Dossier'):null,
          h('th',null,'Client'),h('th',null,'Désignation'),
          h('th',{style:{textAlign:'right'}},'Étiquettes'),h('th',{style:{textAlign:'right'}},'Métrage'),h('th',{style:{textAlign:'right'}},'Calage'),
          h('th',{style:{textAlign:'right'}},'Prod'),h('th',{style:{textAlign:'right'}},'Arrêts'),h('th',{style:{textAlign:'right'}},'Vitesse')
        )),
        h('tbody',null,...sessionRows)
      )
    )
  );
  const kpisBlock=h('div',{className:'prod-synth-kpis'},
    kpi('Sessions',String(tot.sessions)),
    kpi('Étiquettes',fN(tot.etiquettes)),
    kpi('Métrage',fN(tot.metrage_m)+' m'),
    kpi('Calage',fMin(tot.calage_min)),
    kpi('Production',fMin(tot.prod_min)),
    kpi('Arrêts',fMin(tot.arret_min)),
    kpi('Vitesse',tot.vitesse+' m/min')
  );
  const formKids=[
    h('button',{type:'button',className:'add-row-close',title:'Fermer (Échap)',onClick:e=>{e.stopPropagation();closeProdSynthModal();}},'×'),
    titleRow,
    h('div',{className:'prod-synth-sub'},prodSynthPeriodLabel(),' · ',sessions.length,' session'+(sessions.length>1?'s':'')),
    kpisBlock,
  ];
  if(isMobileSynth&&sessions.length){
    const sessLbl=sessions.length===1?'1 session':'Détail par session ('+sessions.length+')';
    formKids.push(h('button',{
      type:'button',
      className:'btn-ghost prod-synth-sessions-toggle',
      onClick:e=>{
        e.stopPropagation();
        const open=overlay.classList.toggle('prod-synth-modal--sessions-open');
        const btn=e.currentTarget;
        if(btn) btn.textContent=open?'Masquer le détail par session':sessLbl;
      },
    },sessLbl));
  }
  formKids.push(sessionsBlock);
  if(!isMobileSynth){
    formKids.push(h('div',{className:'prod-synth-detail-footer'},
      'Navigation : flèches gauche et droite — Fermer : Échap'));
  }
  const form=h('div',{className:'add-row-form prod-synth-detail-form'},...formKids);
  overlay.appendChild(form);
  const handler=(e)=>{
    if(e.key==='Escape'){e.preventDefault();closeProdSynthModal();return;}
    if(e.key==='ArrowLeft'){e.preventDefault();goPrev();return;}
    if(e.key==='ArrowRight'){e.preventDefault();goNext();}
  };
  document.addEventListener('keydown',handler,true);
  overlay._navKeyHandler=handler;
  document.getElementById('root').appendChild(overlay);
}
function makeProdSynthKeyCell(label,type,keys,index){
  return h('td',{
    className:'prod-synth-key',
    title:'Voir le détail — flèches pour naviguer',
    onClick:e=>{e.stopPropagation();openProdSynthDetail(type,keys,index);}
  },label);
}

function renderProdKpis(){
  const d=S.production;
  if(!d)return h('div',{className:'card-empty'},'Chargement des données de production…');
  if(d.blocked)return h('div',{className:'card'},h('div',{className:'card-blocked'},h('div',{className:'cb-icon'},iconEl('lock',32)),h('div',{className:'cb-msg'},d.message)));
  const prod = d.produit||{};
  const tt=d.temps_totaux||{};const parts=[];
  if(canViewAllProd(S.user)){
    parts.push(renderMachineStatusCards());
  }

  // ── Sanity score cliquable ─────────────────────────────────────
  if(S.historique&&S.historique.sanity){
    const sc=renderSanity(S.historique.sanity);
    if(sc){
      sc.style.cursor='pointer';
      sc.title='Voir le détail des erreurs → Historique & Erreurs';
      sc.addEventListener('click',async()=>{
        S.subPage='erreurs';
        if(!S.historique) await loadHist();
        render();
      });
      sc.appendChild(h('div',{style:{fontSize:'11px',color:'var(--accent)',marginTop:'6px',textDecoration:'underline'}},'Voir le détail →'));
      parts.push(sc);
    }
  }
  parts.push(h('div',{className:'section-title'},iconEl('box',13),' Quantités'));
  parts.push(h('div',{className:'stats'},
    h('div',{className:'stat'},h('div',{className:'stat-label'},'Dossiers produits'),h('div',{className:'stat-value'},fN(prod.dossiers||0))),
    h('div',{className:'stat'},h('div',{className:'stat-label'},'Qté étiquettes'),h('div',{className:'stat-value'},fN(prod.etiquettes||0))),
    h('div',{className:'stat'},h('div',{className:'stat-label'},'Métrage'),h('div',{className:'stat-value'},fN(prod.metrage_m||0)+' m')),
    h('div',{className:'stat'},h('div',{className:'stat-label'},'Vitesse'),h('div',{className:'stat-value'},((d.vitesse_m_min!=null)?Number(d.vitesse_m_min).toFixed(2):'0.00')+' m/min')),
  ));
  parts.push(h('div',{className:'section-title'},iconEl('clock',13),' Temps'));
  const prodInclArrets = (Number(tt.production_min||0) + Number(tt.arret_min||0));
  parts.push(h('div',{className:'time-kpi'},
    h('div',{className:'time-card'},h('div',{className:'tc-label',style:{display:'inline-flex',alignItems:'center',gap:'6px'}},iconEl('wrench',12),' Calage'),h('div',{className:'tc-value'},fMin(tt.calage_min))),
    h('div',{className:'time-card'},h('div',{className:'tc-label',style:{display:'inline-flex',alignItems:'center',gap:'6px'}},iconEl('play',12),' Production'),h('div',{className:'tc-value'},fMin(prodInclArrets))),
    h('div',{className:'time-card'},h('div',{className:'tc-label',style:{display:'inline-flex',alignItems:'center',gap:'6px'}},iconEl('alert-triangle',12),' Arrêts'),h('div',{className:'tc-value'},fMin(tt.arret_min))),
  ));
  const byDos = d.by_dossier || d.dossier_times || [];

  function renderAggCard(title, rows, keyLabel, synthType){
    if(!rows||!rows.length) return null;
    const keys=rows.map(r=>String(r.key));
    const typeMap={'Opérateur':'operator','Machine':'machine','Jour':'day'};
    const st=synthType||(typeMap[keyLabel]||'');
    return h('div',{className:'card'},
      h('div',{className:'card-header'},h('h3',null,title),h('span',{style:{fontSize:'11px',color:'var(--muted)'}},rows.length+' items')),
      h('div',{style:{overflowX:'auto'}},h('table',null,
        h('thead',null,h('tr',null,h('th',null,keyLabel),h('th',null,'Dossiers'),h('th',null,'Étiquettes'),h('th',null,'Métrage'),h('th',null,'Calage'),h('th',null,'Prod'),h('th',null,'Arrêts'),h('th',null,'Vitesse'))),
        h('tbody',null,...rows.map((r,i)=>h('tr',null,
          makeProdSynthKeyCell(keyLabel==='Opérateur'?opName(r.key):(keyLabel==='Jour'?formatJourLabel(r.key):r.key),st,keys,i),
          h('td',{style:{fontFamily:'monospace'}},fN(r.dossiers||0)),
          h('td',{style:{fontFamily:'monospace'}},fN(r.etiquettes||0)),
          h('td',{style:{fontFamily:'monospace'}},fN(r.metrage_m||0)+' m'),
          h('td',{style:{fontFamily:'monospace'}},fMin(r.calage_min)),
          h('td',{style:{fontFamily:'monospace'}},fMin(r.prod_min)),
          h('td',{style:{fontFamily:'monospace'}},fMin(r.arret_min)),
          h('td',{style:{fontFamily:'monospace',fontWeight:'800',color:'var(--warn)'}},String(r.vitesse_m_min||0)+' m/min')
        )))
      ))
    );
  }

  parts.push(h('div',{className:'section-title'},'📌 Synthèse détaillée'));
  // Détail par dossier en premier
  if(byDos&&byDos.length){
    // Agrégation par no_dossier
    const byRef = {};
    byDos.forEach(r=>{
      const k = String(r.no_dossier||'').trim();
      if(!k) return;
      if(!byRef[k]){
        byRef[k] = {
          no_dossier: k,
          etiquettes: 0,
          metrage_m: 0,
          temps_calage_min: 0,
          temps_prod_min: 0,
          temps_arret_min: 0,
        };
      }
      byRef[k].etiquettes += Number(r.etiquettes||0);
      byRef[k].metrage_m += Number(r.metrage_m||0);
      byRef[k].temps_calage_min += Number(r.temps_calage_min||0);
      byRef[k].temps_prod_min += Number(r.temps_prod_min||0);
      byRef[k].temps_arret_min += Number(r.temps_arret_min||0);
    });
    const rowsAgg = Object.values(byRef).sort((a,b)=>String(a.no_dossier).localeCompare(String(b.no_dossier), 'fr', {numeric:true,sensitivity:'base'}));
    const dossierKeys=rowsAgg.map(r=>String(r.no_dossier));

    parts.push(h('div',{className:'card'},h('div',{className:'card-header'},h('h3',null,'Par numéro de dossier'),h('span',{style:{fontSize:'11px',color:'var(--muted)'}},rowsAgg.length+' dossiers')),
      h('div',{style:{overflowX:'auto'}},h('table',null,
        h('thead',null,h('tr',null,
          h('th',null,'Dossier'),
          h('th',null,'Étiquettes'),
          h('th',null,'Métrage'),
          h('th',null,'Calage'),
          h('th',null,'Prod'),
          h('th',null,'Arrêts'),
          h('th',null,'Vitesse')
        )),
        h('tbody',null,...rowsAgg.map((r,i)=>h('tr',null,
          makeProdSynthKeyCell(r.no_dossier||'','dossier',dossierKeys,i),
          h('td',{style:{fontFamily:'monospace'}},fN(r.etiquettes||0)),
          h('td',{style:{fontFamily:'monospace'}},fN(r.metrage_m||0)+' m'),
          h('td',{style:{fontFamily:'monospace',color:'var(--text2)'}},fMin(r.temps_calage_min)),
          h('td',{style:{fontFamily:'monospace',color:'var(--text2)'}},fMin(r.temps_prod_min)),
          h('td',{style:{fontFamily:'monospace',color:'var(--text2)'}},fMin(r.temps_arret_min)),
          h('td',{style:{fontFamily:'monospace',fontWeight:'800',color:'var(--warn)'}},(()=>{const den=Number(r.temps_prod_min||0)+Number(r.temps_arret_min||0);return (den>0?(Number(r.metrage_m||0)/den).toFixed(2):'0.00')+' m/min';})())
        )))
      ))
    ));
  }
  const byOp=d.by_operator||[];
  const byMach=d.by_machine||[];
  const byDay=d.by_day||[];
  parts.push(renderAggCard('Par opérateur',byOp,'Opérateur'));
  parts.push(renderAggCard('Par machine',byMach,'Machine'));
  parts.push(renderAggCard('Par jour',byDay,'Jour'));

  return h('div',null,...parts);
}

  // ── 11. Auth (checkAuth / doLogin / doLogout) ──────────────────────
  async function checkAuth(){
    const epoch = authEpoch;
    const user = await api('/api/auth/me');
    if(epoch !== authEpoch) return;
    if(user){
      S.user = user;
      try{ if(window.MySifaTheme) MySifaTheme.mergeFromUser(user); }catch(e){}
      S.app = 'prod';
      // Compta/logistique : redirection /prod -> /planning (cohérent monolithe).
      if(isComptaPlanning(S.user)){ window.location.href = '/planning'; return; }
      // Support : redirection post-login (?next=/xxx)
      try{
        const sp = new URLSearchParams(window.location.search || '');
        const nxt = (sp.get('next') || '').trim();
        if(nxt && nxt.startsWith('/') && nxt !== '/prod'){
          window.location.href = nxt;
          return;
        }
      }catch(e){}
      // ?page=xxx : redirige hors-MyProd vers les routes dédiées, ou applique
      // la sous-page MyProd si autorisée.
      try{
        const sp = new URLSearchParams(window.location.search || '');
        const p = (sp.get('page') || '').trim();
        if(p === 'users'){ window.location.href = '/settings'; return; }
        if(p === 'matiere_prix'){ window.location.href = '/pricing'; return; }
        if(p === 'profil'){ window.location.href = '/profil'; return; }
        const allowed = new Set(['production','suivi','historique','saisies','import','rentabilite','dossiers','traceabilite','of']);
        if(allowed.has(p)) S.page = p;
      }catch(e){}
      // Charger les données initiales pour la sous-page courante (étape 2g).
      try{ startAlertsBadgePolling(); }catch(e){}
      try{
        await loadFilters();
        if(S.page === 'production'){
          await loadProd();
          await loadHist();
          await loadMachineStatus();
        }
      }catch(e){
        console.warn('[mysifa_prod_core] checkAuth load erreur:', e && e.message);
      }
    }else{
      S.user = null;
      S.app = 'login';
    }
    render();
  }

  async function doLogin(email, password){
    if(S.loginSubmitting) return;
    S.loginError = null;
    S.loginSubmitting = true;
    render();
    try{
      const r = await api('/api/auth/login', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({email, password}),
      });
      if(!r || !r.user){
        S.loginSubmitting = false;
        if(r && !r.user) S.loginError = 'Réponse serveur invalide';
        render();
        return;
      }
      authEpoch++;
      // Profil complet via /me (login partial reply)
      try{
        const me = await api('/api/auth/me');
        S.user = me || r.user;
      }catch(e){
        S.user = r.user;
      }
      S.app = 'prod';
      // Compta/logistique : redirection vers /planning
      if(isComptaPlanning(S.user)){ window.location.href = '/planning'; return; }
      // Support ?next=/xxx
      try{
        const sp = new URLSearchParams(window.location.search || '');
        const nxt = (sp.get('next') || '').trim();
        if(nxt && nxt.startsWith('/') && nxt !== '/prod'){
          window.location.href = nxt;
          return;
        }
      }catch(e){}
      // ?page=xxx
      try{
        const sp = new URLSearchParams(window.location.search || '');
        const p = (sp.get('page') || '').trim();
        if(p === 'users'){ window.location.href = '/settings'; return; }
        if(p === 'matiere_prix'){ window.location.href = '/pricing'; return; }
        if(p === 'profil'){ window.location.href = '/profil'; return; }
        const allowed = new Set(['production','suivi','historique','saisies','import','rentabilite','dossiers','traceabilite','of']);
        if(allowed.has(p)) S.page = p;
      }catch(e){}
      S.loginError = null;
      S.loginSubmitting = false;
      render();
      try{ startAlertsBadgePolling(); }catch(e){}
      try{
        await loadFilters();
        if(S.page === 'production'){
          await loadProd();
          await loadHist();
          await loadMachineStatus();
          render();
        }
      }catch(e){
        console.warn('[mysifa_prod_core] doLogin load erreur:', e && e.message);
      }
    }catch(e){
      S.loginError = e.message || 'Erreur de connexion';
      S.loginSubmitting = false;
      render();
    }
  }

  async function doLogout(){
    authEpoch++;
    await api('/api/auth/logout', {method: 'POST'});
    S.user = null;
    S.app = 'login';
    S.historique = null;
    S.production = null;
    S.traceabilite = null;
    S.machineStatus = null;
    S.loginSubmitting = false;
    S.loginError = null;
    render();
  }

  // ── 12. nav() — déclencheur de chargement par sous-page ────────────
  // Appelé par renderSidebar quand l'utilisateur change d'onglet. Charge
  // les données nécessaires à la nouvelle page puis re-render.
  async function nav(){
    try{
      if(S.page === 'production'){
        if(S.subPage === 'kpis' || !S.subPage){
          await loadProd();
          if(!S.historique) await loadHist();  // pour sanity
          await loadMachineStatus();
        }
        // Sous-onglets saisies/erreurs : stubs en 2g, étoffés en 2i
      }
      // Autres pages (suivi/historique/saisies/etc.) : chargements ajoutés en 2i+
    }catch(e){
      console.warn('[mysifa_prod_core] nav() erreur:', e && e.message);
    }
    render();
  }

  // ── 13. renderLogin / renderSidebar ────────────────────────────────
  // Repris littéralement de app/web/html.py (lignes 7169-7263).
  function renderLogin(){
    const errEl = h('div', {
      className: 'login-error' + (S.loginError ? ' show' : ''),
      id: 'login-error',
    }, S.loginError || '');
    const emailI = h('input', {
      type: 'text', id: 'login-email', name: 'email',
      autocomplete: 'username', placeholder: 'identifiant ou email',
    });
    const pwdI = h('input', {
      type: 'password', id: 'login-password', name: 'password',
      autocomplete: 'current-password', placeholder: '\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022',
    });
    const submit = e => {
      e.preventDefault();
      if(S.loginSubmitting) return;
      doLogin(emailI.value, pwdI.value);
    };
    return h('div', {className: 'login-page'},
      h('div', {className: 'login-box'},
        h('div', {className: 'login-logo'},
          h('div', {className: 'brand'}, 'My', h('span', null, 'Sifa')),
          h('div', {className: 'tagline'}, 'Portail interne \u2014 Production, stocks et outils m\u00e9tier')
        ),
        h('div', {className: 'login-card'},
          h('h2', null, 'Connexion'),
          h('p', null, 'Acc\u00e8s r\u00e9serv\u00e9 au personnel SIFA'),
          errEl,
          h('form', {onSubmit: submit},
            h('div', {className: 'field'}, h('label', {'for': 'login-email'}, 'Identifiant ou email'), emailI),
            h('div', {className: 'field'}, h('label', {'for': 'login-password'}, 'Mot de passe'), pwdI),
            h('button', {
              type: 'submit', className: 'login-btn',
              disabled: !!S.loginSubmitting,
            }, S.loginSubmitting ? 'Connexion\u2026' : 'Se connecter')
          )
        ),
        h('div', {className: 'login-footer'}, '\u00a9 SIFA \u2014 MySifa ' + (window.__APP_VERSION__ || ''))
      )
    );
  }

  function renderSidebar(){
    const admin = isAdmin(S.user);
    const comptaPlan = isComptaPlanning(S.user);
    const items = comptaPlan
      ? (canPlanningNav(S.user) ? [{key: '_planning', label: 'Planning', icon: 'calendar'}] : [])
      : [
          ...(canPlanningNav(S.user) ? [{key: '_planning', label: 'Planning', icon: 'calendar'}] : []),
          {key: 'production', label: 'Production', icon: 'wrench'},
          {key: 'traceabilite', label: 'Tra\u00e7abilit\u00e9', icon: 'layers'},
          ...(admin ? [{key: 'rentabilite', label: 'Rentabilit\u00e9', icon: 'trending-up'}] : []),
          ...(canAccessOfTab() ? [{key: 'of', label: 'Fiches + OF', icon: 'file', withPendingOfBadge: true}] : []),
        ];
    const isLight = document.body.classList.contains('light');
    return h('nav', {className: 'sidebar'},
      h('div', {className: 'logo'},
        h('div', {className: 'logo-brand'}, 'My', h('span', null, 'Prod')),
        h('div', {className: 'logo-sub'}, 'by SIFA')
      ),
      ...items.map(i => {
        const btn = h('button', {
          className: 'nav-btn' + (S.page === i.key ? ' active' : ''),
          onClick: () => {
            if(i.key === '_planning'){ window.location.href = '/planning'; return; }
            S.sidebarOpen = false;
            set({page: i.key});
            nav();
          }
        });
        btn.appendChild(iconEl(i.icon, 15));
        btn.appendChild(document.createTextNode('  ' + i.label));
        if(i.withPendingOfBadge){
          const cnt = Number(S.pendingOfCount || 0);
          if(cnt > 0){
            btn.appendChild(h('span', {
              style: 'margin-left:auto;padding:1px 7px;border-radius:9px;background:var(--danger);color:#fff;font-size:10px;font-weight:700;line-height:1.5;flex-shrink:0',
              title: cnt + ' OF \u00e0 associer manuellement',
            }, String(cnt)));
          }
        }
        return btn;
      }),
      h('div', {className: 'sidebar-bottom'},
        h('button', {
          className: 'nav-btn back-mysifa',
          onClick: () => { window.location.href = '/'; }
        },
          '\u2190 Retour ',
          h('span', {className: 'wm'}, 'My', h('span', null, 'Sifa'))
        ),
        sidebarUserChip(S.user),
        h('button', {
          className: 'theme-btn',
          onClick: () => {
            try{ if(window.MySifaTheme) MySifaTheme.toggleMode(); }catch(e){}
            render();
          }
        },
          h('span', {className: 'theme-ico'}, iconEl(isLight ? 'sun' : 'moon', 16)),
          h('span', {className: 'theme-label'}, isLight ? 'Mode clair' : 'Mode sombre')
        ),
        h('button', {className: 'logout-btn', onClick: doLogout}, iconEl('log-out', 14), ' D\u00e9connexion'),
        h('div', {className: 'version'}, window.__APP_VERSION__ || '')
      )
    );
  }

  // ── 14. render() — squelette ─────────────────────────────────────────
  // \u00c9tape 2f : pas connect\u00e9 -> renderLogin ; connect\u00e9 -> sidebar + main vide.
  // Les sous-pages MyProd (Production, Historique, etc.) seront ajout\u00e9es aux
  // \u00e9tapes 2g \u00e0 2l.
  function render(){
    const root = document.getElementById('root');
    if(!root) return;
    root.innerHTML = '';
    document.body.classList.toggle('sb-open', !!S.sidebarOpen);

    if(!S.user || S.app === 'login'){
      root.appendChild(renderLogin());
      return;
    }
    // Layout app + sidebar + main (container vide pour l'instant)
    const topbar = h('div', {className: 'mobile-topbar'},
      h('button', {
        type: 'button', className: 'mobile-menu-btn',
        onClick: toggleSidebar, 'aria-label': 'Menu',
      }, iconEl('menu', 20)),
      h('div', null,
        h('div', {className: 'mobile-topbar-title'}, 'MyProd'),
        h('div', {className: 'mobile-topbar-sub'}, S.page || '')
      ),
      h('button', {
        type: 'button', className: 'mobile-home-btn',
        onClick: () => { window.location.href = '/'; },
        'aria-label': 'Accueil',
      }, iconEl('home', 20))
    );
    // Page Production = sous-onglets KPIs/Saisies/Erreurs via renderProdPage()
    let pageContent;
    let pageTitle = 'MyProd';
    let pageSubtitle = 'Page standalone';
    if(S.page === 'production'){
      pageTitle = (S.subPage === 'saisies' ? 'Saisies' :
                   S.subPage === 'erreurs' ? 'Historique & Erreurs' :
                   'Production');
      pageSubtitle = (S.subPage === 'saisies' ? 'Consulter, corriger et importer des saisies' :
                      S.subPage === 'erreurs' ? 'Sanity Score, incidents et erreurs de saisie' :
                      'KPIs, temps, quantit\u00e9s et qualit\u00e9 de saisie');
      pageContent = renderProdPage();
    }else{
      pageContent = h('div', {className: 'card', style: {padding: '32px', textAlign: 'center'}},
        h('h2', {style: {marginBottom: '8px'}}, 'Sous-page : ' + (S.page || '')),
        h('p', {style: {color: 'var(--text2)', fontSize: '13px'}},
          'Le contenu de cette sous-page sera ajout\u00e9 aux \u00e9tapes ult\u00e9rieures (2i \u00e0 2l). ' +
          'Bascule sur l\u0027onglet Production pour voir les KPIs r\u00e9els.'
        )
      );
    }
    const containerKids = [
      topbar,
      h('h1', null, pageTitle),
      h('div', {className: 'subtitle'}, pageSubtitle),
      pageContent,
    ];
    root.appendChild(h('div', null,
      S.sidebarOpen ? h('div', {className: 'sidebar-overlay', onClick: closeSidebar}) : null,
      h('div', {className: 'app'},
        renderSidebar(),
        h('main', {className: 'main'}, h('div', {className: 'container'}, ...containerKids))
      )
    ));

    // Toast
    if(S.toast){
      const c = {success: 'var(--success)', error: 'var(--danger)'};
      root.appendChild(h('div', {
        className: 'toast',
        style: {borderLeft: '3px solid ' + (c[S.toast.type] || 'var(--accent)')},
      }, h('span', {style: {fontSize: '14px', color: c[S.toast.type] || 'var(--accent)'}}, S.toast.message)));
    }
  }

  // ── Exposition globale pour debugging et étapes suivantes ──────────
  // Les fonctions sont mises en `window` pour que les étapes 2f+ puissent
  // les compléter / les utiliser. À la fin du refactor (étape 2n), ces
  // exports pourront être retirés si plus nécessaire.
  window.__MYSIFA_PROD_STANDALONE__ = {
    stage: '2g',
    description: 'Loads + Page Production (KPIs)',
    loadedAt: new Date().toISOString(),
  };
  window.__prodCore = {
    API, authEpoch, isAuthMePath, apiDetailMsg,
    escHtml, escAttr, api, getYesterday,
    S, set, toast, showToast,
    updateFaviconBadge, refreshAlertsBadge, startAlertsBadgePolling, shouldRefreshAlertsFromApi,
    closeSidebar, toggleSidebar,
    h, icon, iconEl, sidebarUserChip,
    fN, fD, fDSecs, opName, fMin,
    isAdmin, canViewAllProd, isComptaPlanning, canPlanningNav, isFab, isFabrication, isCommercial, isSuperAdmin,
    ROLE_LABELS, ROLE_BADGE,
    canAccessOfTab,
    checkAuth, doLogin, doLogout, nav,
    renderLogin, renderSidebar, render,
    buildParams, loadFilters, loadHist, loadProd, loadMachineStatus,
    loadImports, loadDos, loadMachines, loadRentPlanning, loadSaisies, loadDevis,
    renderProdPage, renderProdKpis,
    startMachineStatusPolling, stopMachineStatusPolling, updateMachineStatusDOM,
    formatJourLabel, prodSynthPeriodLabel, prodSynthDisplayKey,
    prodSynthFilterSessions, prodSynthTotals, prodSynthCleanClient,
    closeProdSynthModal, openProdSynthDetail, makeProdSynthKeyCell,
  };

  console.info('[mysifa_prod_core] page Production chargee - etape 2g', {
    helpers: Object.keys(window.__prodCore).length,
    stateFields: Object.keys(S).length,
  });

  // ── Bootstrap : declenche checkAuth au chargement ──────────────────
  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', () => { checkAuth().catch(() => {}); });
  }else{
    checkAuth().catch(() => {});
  }
})();

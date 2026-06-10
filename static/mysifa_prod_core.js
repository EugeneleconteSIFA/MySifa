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
  // ÉTAPE 2i — Onglets Historique + Saisies + Import
  //
  // Code extrait littéralement de app/web/html.py :
  //   - Actions API saisies : l. 7121-7153 (saveSaisie, addSaisie, upload,
  //     deleteImport, exportBlob)
  //   - renderHist : l. 8819-8902 (historique des erreurs + sanity)
  //   - Helpers saisies : l. 9296-10044 (undoStack, pushUndo, doUndo,
  //     doRedo, applyUndo, helpers date, buildSaisieForm, openAddModal,
  //     openEditModal, makeEditable*, applyOpRules, sortRows, bulkDelete,
  //     fictif*, openFictifReassignModal)
  //   - renderSaisies : l. 10046-10338 (tableau saisies + actions inline)
  //   - renderSaisiesWithImport : l. 10341-10382 (saisies + dropzone)
  //   - renderImport : l. 10385-10400 (page Import XLSX)
  // ────────────────────────────────────────────────────────────────────

async function deleteImport(id,fn){
  if(!confirm('Supprimer "'+fn+'" et toutes ses lignes ?'))return;
  try{const r=await api('/api/imports/'+id,{method:'DELETE'});if(!r)return;toast(r.lignes_supprimees+' lignes supprimées');loadImports();}
  catch(e){toast(e.message,'error');}
}
async function exportBlob(url,filename){
  try{const blob=await api(url);if(!blob)return;const a=Object.assign(document.createElement('a'),{href:URL.createObjectURL(blob),download:filename});document.body.appendChild(a);a.click();setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove();},1000);toast('Export téléchargé');}
  catch(e){toast(e.message,'error');}
}
async function saveSaisie(id,field,value){
  try{
    await api('/api/saisies/'+id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({[field]:value})});
    toast('Sauvegardé');
  }catch(e){toast(e.message,'error');}
}
async function addSaisie(body) {
  try {
    const r = await api('/api/saisies', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    if (!r) return;
    // Pousser dans undo avec l'id retourné par l'API
    pushUndo('add', { ...body, id: r.id });
    toast('Ligne ajoutée');
    await loadSaisies();
  } catch(e) { toast(e.message, 'error'); }
}
async function upload(f){
  try{const fd=new FormData();fd.append('file',f);const r=await api('/api/import',{method:'POST',body:fd});if(!r)return;let msg=r.rows_imported+' lignes importées';if(r.doublons_ignores>0)msg+=' ('+r.doublons_ignores+' doublons ignorés)';toast(msg);loadImports();loadFilters();}
  catch(e){toast(e.message,'error');}
}

function renderHist(){
  const d=S.historique;
  if(!d)return h('div',{className:'card-empty'},'Importez un fichier XLSX pour voir les données');
  if(d.blocked)return h('div',{className:'card'},h('div',{className:'card-blocked'},h('div',{className:'cb-icon'},iconEl('lock',32)),h('div',{className:'cb-msg'},d.message)));
  const sc=d.severity_counts||{};const seCount=d.saisie_errors_count||0;const parts=[];
  if(d.sanity_by_operateur){
    const ops=Object.keys(d.sanity_by_operateur||{});
    ops.forEach(op=>parts.push(renderSanity(d.sanity_by_operateur[op], opName(op))));
  }else if(d.sanity){
    parts.push(renderSanity(d.sanity));
  }
  parts.push(h('div',{className:'stats'},
    h('div',{className:'stat'},h('div',{className:'stat-label'},'Total opérations'),h('div',{className:'stat-value',style:{color:'var(--c1)'}},fN(d.total_operations))),
    h('div',{className:'stat',style:{borderColor:'var(--danger)33'}},h('div',{className:'stat-label'},'🔴 Critique'),h('div',{className:'stat-value',style:{color:'var(--danger)'}},fN(sc.critique))),
    h('div',{className:'stat',style:{borderColor:'var(--warn)33'}},h('div',{className:'stat-label'},'🟡 Attention'),h('div',{className:'stat-value',style:{color:'var(--warn)'}},fN(sc.attention))),
    h('div',{className:'stat'},h('div',{className:'stat-label'},'🟢 Normal'),h('div',{className:'stat-value',style:{color:'var(--success)'}},fN(sc.info))),
    h('div',{className:'stat',style:{borderColor:'var(--danger)55'}},h('div',{className:'stat-label'},'⛔ Erreurs saisie'),h('div',{className:'stat-value',style:{color:seCount>0?'var(--danger)':'var(--success)'}},fN(seCount))),
  ));
  parts.push(h('div',{className:'section-title'},'⛔ Erreurs de saisie'));
  const sanityForList = (d.sanity_by_operateur && d.sanity_by_operateur[Object.keys(d.sanity_by_operateur||{})[0]]) ? null : d.sanity;
  parts.push(h('div',{className:'card'},
    h('div',{className:'card-header'},
      h('h3',null,'Contrôles de saisie'),
      seCount>0?h('span',{className:'badge-danger'},seCount+' erreur'+(seCount>1?'s':'')):h('span',{className:'badge'},'OK')
    ),
    d.sanity_by_operateur
      ? h('div',null,
          ...Object.keys(d.sanity_by_operateur||{}).map(op=>
            h('div',{style:{borderTop:'1px solid var(--border)'}},
              h('div',{style:{padding:'12px 20px',fontWeight:'800',color:'var(--text)'}},opName(op)),
              renderSanityEventsBlock(d.sanity_by_operateur[op])
            )
          )
        )
      : renderSanityEventsBlock(sanityForList||d.sanity)
  ));
  if(d.operator_arrets&&d.operator_arrets.length){
    const byOp={};
    (d.operator_arrets||[]).forEach(r=>{
      const op=String(r.operateur||'?');
      if(!byOp[op]) byOp[op]=[];
      byOp[op].push(r);
    });
    const ops=Object.keys(byOp).sort((a,b)=>opName(a).localeCompare(opName(b)));
    parts.push(h('div',{className:'card'},
      h('div',{className:'card-header'},h('h3',null,'Arrêts machine')),
      h('div',{style:{padding:'10px 16px'}},
        ...ops.map(op=>{
          const rows=byOp[op]||[];
          const total=rows.reduce((s,x)=>s+(+x.c||0),0);
          return h('div',{style:{padding:'12px 4px',borderBottom:'1px solid var(--border)'}},
            h('div',{style:{display:'flex',justifyContent:'space-between',alignItems:'center',gap:'12px',flexWrap:'wrap'}},
              h('div',{style:{fontWeight:'800',color:'var(--text)'}},opName(op)),
              h('span',{className:'badge-danger',style:{background:'rgba(251,191,36,.12)',border:'1px solid rgba(251,191,36,.25)',color:'var(--warn)'}},total+' arrêt'+(total>1?'s':''))
            ),
            h('div',{style:{marginTop:'8px',overflowX:'auto'}},
              h('table',null,
                h('thead',null,h('tr',null,h('th',null,'Type'),h('th',null,'Nb'),h('th',null,'Durée'))),
                h('tbody',null,...rows.map(x=>{
                  const code=String(x.operation_code||'');
                  const lbl=(x.operation||'') || (S.OPS_CONFIG && S.OPS_CONFIG[code] && S.OPS_CONFIG[code].label) || ('Code '+code);
                  return h('tr',null,
                    h('td',null,lbl),
                    h('td',{style:{fontFamily:'monospace',fontWeight:'800',color:'var(--warn)'}},String(x.c||0)),
                    h('td',{style:{fontFamily:'monospace',fontWeight:'800',color:'var(--warn)'}},fMin(x.duree_min))
                  );
                }))
              )
            )
          );
        })
      )
    ));
  }
  if(d.issues&&d.issues.length){
    parts.push(h('div',{className:'card'},h('div',{className:'card-header'},h('h3',null,'Détail incidents ('+d.issues.length+')')),
      h('div',{style:{overflowX:'auto'}},h('table',null,
        h('thead',null,h('tr',null,h('th',null,'Sévérité'),h('th',null,'Date'),h('th',null,'Opérateur'),h('th',null,'Opération'),h('th',null,'Machine'),h('th',null,'Dossier'),h('th',null,'Durée'))),
        h('tbody',null,...d.issues.map(r=>h('tr',null,h('td',null,h('span',{className:'sev-dot '+r.operation_severity}),h('span',{className:'sev-'+r.operation_severity},r.operation_severity.toUpperCase())),h('td',null,fD(r.date_operation)),h('td',null,opName(r.operateur)),h('td',null,r.operation||''),h('td',null,r.machine||''),h('td',null,r.no_dossier||''),h('td',null,fMin(r.duree_min)))))
      ))
    ));
  }
  return h('div',null,...parts);
}

// ── Modal ajout ligne ───────────────────────────────────────────

// ── Undo / Redo (session uniquement, tout en mémoire) ──────────
let undoStack = [];  // [{id, snapshot}, ...]
let redoStack = [];
 
function pushUndo(action, data) {
  // action : 'edit' | 'add' | 'delete'
  // data   : pour edit/delete = snapshot de la ligne
  //          pour add = { id } (on supprimera)
  undoStack.push({ action, data: JSON.parse(JSON.stringify(data)) });
  redoStack = [];
  updateUndoRedoBtns();
}
 
function updateUndoRedoBtns() {
  const btnU = document.getElementById('btn-undo');
  const btnR = document.getElementById('btn-redo');
  if (btnU) btnU.disabled = undoStack.length === 0;
  if (btnR) btnR.disabled = redoStack.length === 0;
}
 
async function doUndo() {
  if (!undoStack.length) return;
  const entry = undoStack.pop();
  const curRows = (S.saisies && S.saisies.rows) ? S.saisies.rows : [];
  const current = curRows.find(r => r.id === entry.data.id);

  // Pour edit : sauvegarder l'état actuel avant restauration
  if (entry.action === 'edit' && current) {
    redoStack.push({ action: 'edit', data: JSON.parse(JSON.stringify(current)) });
  } else if (entry.action === 'add') {
    redoStack.push({ action: 'delete_then_recreate', data: entry.data });
  } else if (entry.action === 'delete') {
    // On pousse un placeholder — applyUndo va corriger l'id après le POST
    redoStack.push({ action: 'delete', data: { ...entry.data } });
  }

  await applyUndo(entry);
}

async function doRedo() {
  if (!redoStack.length) return;
  const entry = redoStack.pop();
  const curRows2 = (S.saisies && S.saisies.rows) ? S.saisies.rows : [];
  const current = curRows2.find(r => r.id === entry.data.id);
  if (entry.action === 'edit' && current) {
    undoStack.push({ action: 'edit', data: JSON.parse(JSON.stringify(current)) });
    await api('/api/saisies/' + entry.data.id, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...entry.data, note: 'Restauration redo' })
    });
  } else if (entry.action === 'delete') {
    // Redo d'une suppression = supprimer à nouveau
    await api('/api/saisies/' + entry.data.id, { method: 'DELETE' });
  } else if (entry.action === 'delete_then_recreate') {
    // Redo d'un ajout = recréer
    await api('/api/saisies', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...entry.data, note: 'Restauration redo (ajout)' })
    });
  }
  toast('Action rétablie');
  await loadSaisies();
}

 async function applyUndo(entry) {
  try {
    if (entry.action === 'edit') {
      // Restaurer l'ancien état
      await api('/api/saisies/' + entry.data.id, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          operation:          entry.data.operation,
          date_operation:     entry.data.date_operation,
          operateur:          entry.data.operateur,
          machine:            entry.data.machine,
          no_dossier:         entry.data.no_dossier,
          quantite_a_traiter: entry.data.quantite_a_traiter,
          quantite_traitee:   entry.data.quantite_traitee,
          metrage_prevu:     entry.data.metrage_prevu ?? null,
          metrage_reel:      entry.data.metrage_reel ?? null,
          commentaire:       entry.data.commentaire || '',
          note:               'Restauration undo',
        })
      });
    } else if (entry.action === 'add') {
      // Annuler un ajout = supprimer la ligne créée
      await api('/api/saisies/' + entry.data.id, { method: 'DELETE' });
    } else if (entry.action === 'delete') {
      // Annuler une suppression = recréer la ligne
      const r = await api('/api/saisies', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          operation:          entry.data.operation,
          date_operation:     entry.data.date_operation,
          operateur:          entry.data.operateur,
          machine:            entry.data.machine,
          no_dossier:         entry.data.no_dossier,
          quantite_a_traiter: entry.data.quantite_a_traiter,
          quantite_traitee:   entry.data.quantite_traitee,
          metrage_prevu:     entry.data.metrage_prevu ?? null,
          metrage_reel:      entry.data.metrage_reel ?? null,
          commentaire:       entry.data.commentaire || '',
          note:               'Restauration undo (suppression annulée)',
        })
      });
      // Mettre à jour le redo avec le NOUVEL id retourné par l'API
      // car l'ancien id n'existe plus en base
      if (r && r.id) {
        // Corriger l'entrée redo qui vient d'être poussée dans doUndo
        const lastRedo = redoStack[redoStack.length - 1];
        if (lastRedo && lastRedo.action === 'delete') {
          lastRedo.data = { ...entry.data, id: r.id };
        }
      }
    }
    toast('Action annulée');
    await loadSaisies();
  } catch(e) { toast(e.message, 'error'); }
}
 
// ── Helpers date 24h ───────────────────────────────────────────
function dateToInputVal(dateStr) {
  // Convertit '01/04/2026 12:53:45' → {date:'2026-04-01', time:'12:53:45'}
  if (!dateStr) return { date: '', time: '' };
  const s = dateStr.replace(/C$/, '').trim();
  const m = s.match(/^(\d{2})\/(\d{2})\/(\d{4})\s+(\d{2}):(\d{2})(?::(\d{2}))?/);
  if (m) return { date: m[3]+'-'+m[2]+'-'+m[1], time: m[4]+':'+m[5]+':'+(m[6]!=null?m[6]:'00') };
  const m2 = s.match(/^(\d{4}-\d{2}-\d{2})(?:T(\d{2}):(\d{2})(?::(\d{2}))?)?/);
  if (m2) return { date: m2[1], time: (m2[2]&&m2[3]) ? m2[2]+':'+m2[3]+':'+(m2[4]!=null?m2[4]:'00') : '00:00:00' };
  return { date: '', time: '' };
}
 
function inputValToFrDate(dateVal, timeVal) {
  // Convertit '2026-04-01' + '12:53:45' → '01/04/2026 12:53:45'
  if (!dateVal) return datetime_now_fr();
  const [y, mo, d] = dateVal.split('-');
  const parts = String(timeVal || '00:00:00').split(':');
  const hh = (parts[0] || '00').padStart(2, '0');
  const mm = (parts[1] || '00').padStart(2, '0');
  const ss = (parts[2] != null ? parts[2] : '00').padStart(2, '0');
  return d+'/'+mo+'/'+y+' '+hh+':'+mm+':'+ss;
}
 
function datetime_now_fr() {
  const now = new Date();
  return String(now.getDate()).padStart(2,'0')+'/'+
         String(now.getMonth()+1).padStart(2,'0')+'/'+
         now.getFullYear()+' '+
         String(now.getHours()).padStart(2,'0')+':'+
         String(now.getMinutes()).padStart(2,'0')+':00';
}
 
function makeDateTimeFields(existingDateStr) {
  // Retourne {wrapper, getVal()} avec deux inputs date + time en 24h
  const { date: dv, time: tv } = dateToInputVal(existingDateStr);
  const dateI = h('input', { type: 'date', value: dv, lang: 'fr', style: { flex: '1' } });
  // IMPORTANT: input[type=time] peut afficher AM/PM selon OS/locale (iOS/Safari).
  // On force donc une saisie manuelle HH:MM (24h) via un input texte.
  const timeI = h('input', {
    type: 'text',
    inputmode: 'numeric',
    autocomplete: 'off',
    placeholder: 'HH:MM:SS',
    value: (String(tv || '00:00:00').slice(0,8) || ''),
    style: { width: '96px', fontFamily: 'monospace' }
  });
  timeI.setAttribute('maxlength', '8');

  function normalizeTime(raw){
    const s = String(raw||'').trim().replace(/[^\d:]/g,'');
    const digits = s.replace(/:/g,'');
    if(/^\d+$/.test(digits)){
      if(digits.length <= 4){
        const z = digits.padStart(4,'0');
        return z.slice(0,2)+':'+z.slice(2,4)+':00';
      }
      if(digits.length <= 6){
        const z = digits.padStart(6,'0');
        return z.slice(0,2)+':'+z.slice(2,4)+':'+z.slice(4,6);
      }
    }
    const m = s.match(/^(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?$/);
    if(m){
      const hh = String(m[1]).padStart(2,'0');
      const mm = String(m[2]).padStart(2,'0');
      const ss = m[3]!=null ? String(m[3]).padStart(2,'0') : '00';
      return hh+':'+mm+':'+ss;
    }
    if(/^\d{2}:\d{2}:\d{2}$/.test(s)) return s;
    return '';
  }
  function isValidHHMMSS(s){
    const m = String(s||'').match(/^(\d{2}):(\d{2}):(\d{2})$/);
    if(!m) return false;
    const hh = parseInt(m[1],10), mm = parseInt(m[2],10), ss = parseInt(m[3],10);
    return hh>=0 && hh<=23 && mm>=0 && mm<=59 && ss>=0 && ss<=59;
  }
  function getTimeVal(){
    const norm = normalizeTime(timeI.value);
    if(norm) timeI.value = norm;
    return isValidHHMMSS(timeI.value) ? timeI.value : null;
  }
  timeI.addEventListener('input', ()=>{
    let v = String(timeI.value||'').replace(/[^\d]/g,'').slice(0,6);
    if(v.length >= 5) v = v.slice(0,2)+':'+v.slice(2,4)+':'+v.slice(4);
    else if(v.length >= 3) v = v.slice(0,2)+':'+v.slice(2);
    timeI.value = v;
  });
  timeI.addEventListener('blur', ()=>{ getTimeVal(); });

  const wrapper = h('div', { style: { display:'flex', gap:'8px' } }, dateI, timeI);
  return { wrapper, getVal: () => {
    const t = getTimeVal();
    if(!t) return null;
    return inputValToFrDate(dateI.value, t);
  }};
}
 
// ── Modal générique (add + edit) ───────────────────────────────
function buildSaisieForm(prefill, title, submitLabel, onSubmit, extraBtn) {
  const ops = S.OPS_CONFIG;
  const ops_list = S.filters.operators || [];
  const inputs = {};
 
  // Sélect opération
  const opSel = h('select', null,
    h('option', { value: '' }, '— Choisir une opération —'),
    ...Object.entries(ops).map(([code, cfg]) => {
      const opt = h('option', { value: code+'           '+cfg.label }, code+' — '+cfg.label);
      // Pré-sélection si edit
      if (prefill && prefill.operation && prefill.operation.startsWith(code)) opt.selected = true;
      return opt;
    })
  );
  const opPreview = h('div', { className: 'op-preview' });
  opSel.addEventListener('change', () => {
    const code = opSel.value.split(' ')[0];
    const cfg = ops[code];
    opPreview.textContent = cfg
      ? (cfg.severity==='critique'?'🔴 Critique':cfg.severity==='attention'?'🟡 Attention':'🟢 '+cfg.category)
      : '';
  });
  // Déclencher preview si pré-rempli
  if (prefill && prefill.operation) {
    const m = prefill.operation.match(/^(\d+)/);
    const code = (m && m[1]) ? m[1] : null;
    const cfg = code && ops[code];
    if (cfg) opPreview.textContent = cfg.severity==='critique'?'🔴 Critique':cfg.severity==='attention'?'🟡 Attention':'🟢 '+cfg.category;
  }
 
  // Opérateur
  let opField;
  if (isAdmin(S.user)) {
    opField = h('select', null,
      h('option', { value: '' }, '— Choisir —'),
      ...ops_list.map(o => {
        const opt = h('option', { value: o }, opName(o));
        if (o === ((prefill && prefill.operateur) ? prefill.operateur : '')) opt.selected = true;
        return opt;
      })
    );
  } else {
    // Pour fabrication: utiliser nom si operateur_lie n'est pas défini
    const userOp = (S.user && (S.user.operateur_lie || S.user.nom)) || '';
    opField = h('input', { type: 'text', value: userOp });
    opField.disabled = true;
  }
 
  // Date 24h
  const { wrapper: dateWrapper, getVal: getDateVal } = makeDateTimeFields((prefill && prefill.date_operation) ? prefill.date_operation : '');
 
  const machI  = h('input', { type: 'text', placeholder: 'ex: 1 - COHESIO 1', value: (prefill && prefill.machine) ? prefill.machine : '' });
  const dosI   = h('input', { type: 'text', placeholder: 'ex: 1060',           value: (prefill && prefill.no_dossier) ? prefill.no_dossier : '' });
  const qteTI  = h('input', { type: 'number', placeholder: '0',                value: (prefill && prefill.quantite_traitee!=null)   ? prefill.quantite_traitee   : 0 });
  const noteI  = h('input', { type: 'text', placeholder: 'Raison (optionnel)',  value: '' });
  const commentaireI = h('input', { type: 'text', placeholder: 'Observation, remarque...', value: (prefill && prefill.commentaire) ? prefill.commentaire : '' });
  const metrageReelI      = h('input', { type: 'number', placeholder: '0', value: (prefill && prefill.metrage_reel!=null)        ? prefill.metrage_reel        : '' });
  const metrageDebutI     = h('input', { type: 'number', placeholder: '0', value: (prefill && prefill.metrage_total_debut!=null) ? prefill.metrage_total_debut : '' });
  const metrageFinI       = h('input', { type: 'number', placeholder: '0', value: (prefill && prefill.metrage_total_fin!=null)   ? prefill.metrage_total_fin   : '' });
  inputs.metrage_reel         = metrageReelI;
  inputs.metrage_total_debut  = metrageDebutI;
  inputs.metrage_total_fin    = metrageFinI;
 
  const form = h('div', { className: 'add-row-form' },
      h('button',{type:'button',className:'add-row-close',title:'Fermer',onClick:(e)=>{e.stopPropagation();closeModal();}},'×'),
      // Header (sert aussi de zone "grab" pour déplacer la fenêtre)
      (title && typeof title === 'object' && title.nodeType)
        ? h('div',{className:'add-row-header'}, title)
        : (title && title.tagName)
          ? h('div',{className:'add-row-header'}, title)
          : h('div',{className:'add-row-header'}, h('h3', null, title)),
      h('div', { className: 'form-row' },
        h('div', null, h('label', null, 'Opération *'), opSel, opPreview),
        h('div', null, h('label', null, 'Opérateur *'), opField)
      ),
      h('div', { className: 'form-row' },
        h('div', null, h('label', null, 'Date & heure (JJ/MM/AAAA HH:MM:SS)'), dateWrapper),
        h('div', null, h('label', null, 'Machine'), machI)
      ),
      h('div', { className: 'form-row' },
        h('div', null, h('label', null, 'No Dossier'), dosI)
      ),
      h('div', { className: 'form-row' },
        h('div', null, h('label', null, 'Qté traitée'), qteTI),
        h('div', null, h('label', null, 'Note'), noteI)
      ),
      h('div', { className: 'form-row' },
        h('div', null,
          h('label', null, 'Métrage réel (m)'),
          metrageReelI
        )
      ),
      h('div', { className: 'form-row' },
        h('div', null,
          h('label', null, 'Compteur début (m)'),
          metrageDebutI
        ),
        h('div', null,
          h('label', null, 'Compteur fin (m)'),
          metrageFinI
        )
      ),
      h('div', { className: 'form-row' },
        h('div', { style:{ gridColumn:'span 2' } },
          h('label', null, 'Commentaire'),
          commentaireI
        )
      ),
      h('div', { className: 'form-actions' },
        extraBtn || h('div', null), // bouton gauche (ex: Supprimer)
        h('div', { style: { display:'flex', gap:'8px' } },
          h('button', { className: 'btn-ghost', onClick: closeModal }, 'Annuler'),
          h('button', { className: 'btn-sm', onClick: () => {
            const opVal = opSel.value;
            if (!opVal) { toast('Sélectionnez une opération', 'error'); return; }
            const opText = opVal.replace('           ', ' ');
            const dtVal = getDateVal();
            if(!dtVal){ toast('Heure invalide (format HH:MM:SS, 24h)', 'error'); return; }
            onSubmit({
              operation:          opText,
              operateur:          opField.value || '',
              date_operation:     dtVal,
              machine:            machI.value  || '',
              no_dossier:         dosI.value   || '',
              quantite_traitee:   parseFloat(qteTI.value) || 0,
              note:               noteI.value  || '',
              commentaire:       commentaireI.value || '',
              metrage_reel:         parseFloat((inputs.metrage_reel         && inputs.metrage_reel.value)         ? inputs.metrage_reel.value         : '') || null,
              metrage_total_debut:  parseFloat((inputs.metrage_total_debut  && inputs.metrage_total_debut.value)  ? inputs.metrage_total_debut.value  : '') || null,
              metrage_total_fin:    parseFloat((inputs.metrage_total_fin    && inputs.metrage_total_fin.value)    ? inputs.metrage_total_fin.value    : '') || null,
            });
          }}, submitLabel)
        )
      )
    )
  ;
  const modal = h('div', { className: 'add-row-modal', onClick: e => { if (e.target === modal) closeModal(); } }, form);
  modal._formEl = form;
  return modal;
}
 
function getVisibleSaisiesRowsForNav(){
  // Base : déjà filtré côté API (/api/saisies + filtres). Ici on applique seulement tri + enrichissements UI.
  const d = S.saisies;
  if(!d) return [];
  let rows = (d.rows || []).slice();
  // Reprend la logique UI (durées) si la fonction existe (ajoutée dans renderSaisies).
  try{
    if(typeof addDurations === 'function') rows = addDurations(rows);
  }catch(e){}
  if(S.sortState && S.sortState.col) rows = sortRows(rows, S.sortState.col, S.sortState.asc);
  return rows;
}

function attachSaisieNav(modal, currentId){
  // Ctrl+← / Ctrl+→ : naviguer sur la liste affichée (bouclage).
  const handler = (e)=>{
    if(!e || !e.ctrlKey) return;
    if(e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
    const list = getVisibleSaisiesRowsForNav();
    if(!list || !list.length) return;
    const idx = list.findIndex(r=>String(r.id)===String(currentId));
    if(idx < 0) return;
    e.preventDefault();
    e.stopPropagation();
    const nextIdx = (e.key === 'ArrowRight')
      ? ((idx + 1) % list.length)
      : ((idx - 1 + list.length) % list.length);
    const nxt = list[nextIdx];
    if(nxt) openEditModal(nxt);
  };
  // Éviter d'empiler des listeners si on remplace la modale.
  document.addEventListener('keydown', handler, true);
  modal._navKeyHandler = handler;
}

function attachModalDrag(modal){
  const form = modal && modal._formEl ? modal._formEl : (modal ? modal.querySelector('.add-row-form') : null);
  if(!form) return;
  // Appliquer la dernière position (si l'utilisateur a déjà déplacé la fenêtre)
  try{
    if(S && S._saisieModalPos && isFinite(S._saisieModalPos.left) && isFinite(S._saisieModalPos.top)){
      form.style.position = 'fixed';
      form.style.margin = '0';
      form.style.left = S._saisieModalPos.left + 'px';
      form.style.top  = S._saisieModalPos.top + 'px';
      form.style.transform = 'none';
    }
  }catch(e){}
  let dragging = false;
  let sx = 0, sy = 0, startLeft = 0, startTop = 0;
  const onMove = (e)=>{
    if(!dragging) return;
    const dx = e.clientX - sx;
    const dy = e.clientY - sy;
    const left = (startLeft + dx);
    const top  = (startTop  + dy);
    form.style.left = left + 'px';
    form.style.top  = top  + 'px';
    try{ S._saisieModalPos = { left, top }; }catch(_){}
  };
  const onUp = ()=>{
    if(!dragging) return;
    dragging = false;
    document.removeEventListener('mousemove', onMove, true);
    document.removeEventListener('mouseup', onUp, true);
  };
  const onDown = (e)=>{
    // Drag uniquement si on clique sur une zone qui n'est pas un champ/bouton.
    const t = e.target;
    if(t && (t.closest && t.closest('input,select,textarea,button'))) return;
    // Laisser la sélection de texte dans un champ intacte.
    if(e.button !== 0) return;
    const r = form.getBoundingClientRect();
    // Passer en position fixe pour pouvoir bouger, sans dépendre du flex-center.
    form.style.position = 'fixed';
    form.style.margin = '0';
    form.style.left = r.left + 'px';
    form.style.top  = r.top  + 'px';
    form.style.transform = 'none';
    dragging = true;
    sx = e.clientX; sy = e.clientY;
    startLeft = r.left; startTop = r.top;
    try{ S._saisieModalPos = { left: startLeft, top: startTop }; }catch(_){}
    document.addEventListener('mousemove', onMove, true);
    document.addEventListener('mouseup', onUp, true);
    e.preventDefault();
  };
  form.addEventListener('mousedown', onDown, true);
  modal._dragDownHandler = onDown;
  modal._dragMoveHandler = onMove;
  modal._dragUpHandler = onUp;
}
 
function closeModal() {
  try{
    const m = document.querySelector('.add-row-modal');
    if(m && m._navKeyHandler){
      try{ document.removeEventListener('keydown', m._navKeyHandler, true); }catch(e){}
    }
    if(m && m._dragDownHandler){
      try{
        const form = m._formEl || m.querySelector('.add-row-form');
        if(form) form.removeEventListener('mousedown', m._dragDownHandler, true);
      }catch(e){}
      try{ document.removeEventListener('mousemove', m._dragMoveHandler, true); }catch(e){}
      try{ document.removeEventListener('mouseup', m._dragUpHandler, true); }catch(e){}
    }
    if(m) m.remove();
  }catch(e){}
}
 
function openAddModal(templateRow) {
  try{
    const m = document.querySelector('.add-row-modal');
    if(m) m.remove();
  }catch(e){}
  const modal = buildSaisieForm(
    templateRow,
    '➕ Ajouter une saisie',
    '✓ Ajouter',
    async (body) => { await addSaisie(body); }
  );
  document.getElementById('root').appendChild(modal);
}
 
function openEditModal(row) {
  try{
    const m = document.querySelector('.add-row-modal');
    if(m) m.remove();
  }catch(e){}
 
  const list = getVisibleSaisiesRowsForNav();
  const total = list.length || 0;
  const curIdx0 = total ? list.findIndex(r=>String(r.id)===String(row.id)) : -1;
  const idx = (curIdx0>=0) ? (curIdx0 + 1) : 0;
  const prevRow = (total && curIdx0>=0) ? list[(curIdx0 - 1 + total) % total] : null;
  const nextRow = (total && curIdx0>=0) ? list[(curIdx0 + 1) % total] : null;

  const counter = h('span',{className:'add-row-counter',title:'Ctrl+← / Ctrl+→'},
    h('button',{type:'button',className:'add-row-nav-btn',title:'Précédente (Ctrl+←)',onClick:(e)=>{e.stopPropagation(); if(prevRow) openEditModal(prevRow);}},'‹'),
    h('span',null,(idx>0?String(idx):'—')+'/'+String(total)),
    h('button',{type:'button',className:'add-row-nav-btn',title:'Suivante (Ctrl+→)',onClick:(e)=>{e.stopPropagation(); if(nextRow) openEditModal(nextRow);}},'›')
  );
  const titleNode = h('div',{style:{display:'flex',alignItems:'center',justifyContent:'space-between',gap:'12px',width:'100%'}},
    h('h3',null,'Modifier la saisie'),
    counter
  );
 
  const deleteBtn = h('button', {
    className: 'btn-danger',
    onClick: async e => {
      e.stopPropagation();
      if (!confirm('Supprimer cette saisie ?')) return;
      pushUndo('delete', row);  // ← ajouter cette ligne
      try {
        await api('/api/saisies/' + row.id, { method: 'DELETE' });
        toast('Saisie supprimée');
        await loadSaisies();
      } catch(err) { 
        undoStack.pop(); // annuler le pushUndo si l'API échoue
        toast(err.message, 'error'); 
      }
    }
  }, iconEl('trash',13),' Supprimer');
 
  const modal = buildSaisieForm(
    row,
    titleNode,
    'Enregistrer',
    async (body) => {
      pushUndo('edit', row);  //
      try {
        await api('/api/saisies/' + row.id, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
        toast('Saisie modifiée');
        await loadSaisies();
      } catch(e) { toast(e.message, 'error'); }
    },
    deleteBtn
  );
  attachSaisieNav(modal, row.id);
  attachModalDrag(modal);
  document.getElementById('root').appendChild(modal);
}

// ── Saisies ─────────────────────────────────────────────────────
function makeEditable(row,field,displayVal){
  const td=h('td',{className:'editable'});
  td.appendChild(h('span',null,displayVal||'-'));
  td.addEventListener('click',()=>{
    if(td.classList.contains('editing'))return;
    td.classList.add('editing');td.innerHTML='';
    const inp=h('input',{type:'text',value:row[field]||''});
    td.appendChild(inp);inp.focus();inp.select();
    const save=()=>{const val=inp.value;td.classList.remove('editing');td.innerHTML='';td.appendChild(h('span',null,val||'-'));if(val!==String(row[field]||''))saveSaisie(row.id,field,val);};
    inp.addEventListener('blur',save);
    inp.addEventListener('keydown',e=>{if(e.key==='Enter')inp.blur();if(e.key==='Escape'){td.classList.remove('editing');td.innerHTML='';td.appendChild(h('span',null,displayVal||'-'));}});
  });
  return td;
}

// Commentaire — éditable inline (spécifique pour éviter les modifs autres champs)
function makeEditableComment(row){
  const td=h('td',{className:'editable',style:{maxWidth:'220px',minWidth:'120px'}});
  const span=h('span',{style:{color:'var(--muted)',fontStyle:'italic'}},row.commentaire||'—');
  td.appendChild(span);
  td.addEventListener('click',e=>{
    e.stopPropagation(); // ne pas ouvrir le modal modification
    if(td.classList.contains('editing'))return;
    td.classList.add('editing');td.innerHTML='';
    const inp=h('input',{type:'text',value:row.commentaire||'',placeholder:'Ajouter un commentaire...'});
    td.appendChild(inp);inp.focus();inp.select();
    const save=()=>{
      const val=inp.value;
      td.classList.remove('editing');td.innerHTML='';
      td.appendChild(h('span',{style:{color:'var(--muted)',fontStyle:'italic'}},val||'—'));
      const old=(row.commentaire||'');
      if(val!==old) saveSaisie(row.id,'commentaire',val);
      // Mettre à jour l'objet local pour que la prochaine édition reflète la valeur
      row.commentaire = val;
    };
    inp.addEventListener('blur',save);
    inp.addEventListener('keydown',e=>{
      if(e.key==='Enter')inp.blur();
      if(e.key==='Escape'){
        td.classList.remove('editing');
        td.innerHTML='';
        td.appendChild(h('span',{style:{color:'var(--muted)',fontStyle:'italic'}},row.commentaire||'—'));
      }
    });
  });
  return td;
}


// Codes sans dossier ni quantité
const CODES_PERSONNEL = new Set(['86','87']);
// Seul code avec quantité
const CODE_FIN_DOS = '89';
 
// ── Masquage champs selon opération dans le modal ───────────────
function applyOpRules(opCode, form){
  const isPers  = CODES_PERSONNEL.has(opCode);
  const isFin   = opCode === CODE_FIN_DOS;
  const fields  = ['no_dossier','quantite_a_traiter','quantite_traitee'];
  fields.forEach(f=>{
    const row = form.querySelector('[data-field="'+f+'"]');
    if(!row) return;
    if(isPers){
      row.style.display='none';
    } else if(!isFin && (f==='quantite_a_traiter'||f==='quantite_traitee')){
      row.style.opacity='.4';
      row.querySelector('input').disabled=true;
      row.querySelector('input').value='0';
    } else {
      row.style.display='';row.style.opacity='';
      if(row.querySelector('input')) row.querySelector('input').disabled=false;
    }
  });
}
 
// ── Tri tableau ─────────────────────────────────────────────────
function sortRows(rows, col, asc){
  return [...rows].sort((a,b)=>{
    let va=a[col]||'', vb=b[col]||'';
    if(typeof va==='number'||!isNaN(va)) {va=parseFloat(va)||0; vb=parseFloat(vb)||0;}
    if(va<vb)return asc?-1:1;
    if(va>vb)return asc?1:-1;
    return 0;
  });
}
 
// ── Suppression groupée ─────────────────────────────────────────
async function bulkDelete(){
  const ids=[...S.selectedRows];
  if(!ids.length) return;
  if(!confirm('Supprimer '+ids.length+' saisie(s) ?')) return;
 
  // Sauvegarder pour undo
  const snaps=(((S.saisies && S.saisies.rows) ? S.saisies.rows : [])).filter(r=>ids.includes(r.id));
  snaps.forEach(row=>pushUndo('delete',row));
 
  try{
    const r=await api('/api/saisies/bulk',{method:'DELETE',headers:{'Content-Type':'application/json'},body:JSON.stringify({ids})});
    if(!r)return;
    toast(r.deleted+' saisie(s) supprimée(s)');
    S.selectedRows=new Set();
    await loadSaisies();
  }catch(e){
    // Annuler les pushUndo si erreur
    snaps.forEach(()=>undoStack.pop());
    toast(e.message,'error');
  }
}

const SAISIE_FICTIF_PREFIX = 'FICTIF:';
function isFictifDossierRef(ref){
  if(!ref) return false;
  return String(ref).trim().toUpperCase().startsWith(SAISIE_FICTIF_PREFIX);
}
function isFictifSaisieRow(row){
  if(!row) return false;
  return isFictifDossierRef(row.no_dossier) || isFictifDossierRef(row.reference);
}

function fictifOfDisplay(ref){
  const s=String(ref||'').trim();
  if(isFictifDossierRef(s)) return s.slice(SAISIE_FICTIF_PREFIX.length);
  return s;
}

async function openFictifReassignModal(){
  if(isFab(S.user)) return;
  try{
    const m=document.querySelector('.add-row-modal');
    if(m) m.remove();
  }catch(e){}
  const sources=await api('/api/saisies/reassign/fictif-sources')||[];
  const fromSel=h('select',{className:'form-sel',style:{width:'100%'}},
    h('option',{value:''},'— Choisir un dossier fictif —'),
    ...sources.map(s=>{
      const opt=h('option',{value:s.no_dossier},
        'OF fictif '+fictifOfDisplay(s.no_dossier)+' ('+s.nb_saisies+' saisie'+(s.nb_saisies>1?'s':'')+')');
      return opt;
    })
  );
  const toInp=h('input',{type:'text',className:'form-sel',style:{width:'100%'},
    placeholder:'N° dossier planning (référence ou OF)…'});
  const sugWrap=h('div',{className:'fictif-reassign-suggest'});
  let sugTok=0;
  const refreshSug=async()=>{
    const q=String(toInp.value||'').trim();
    const tok=++sugTok;
    if(q.length<1){ sugWrap.innerHTML=''; return; }
    const sugs=await api('/api/saisies/reassign/target-dossiers?q='+encodeURIComponent(q)+'&limit=12')||[];
    if(tok!==sugTok) return;
    sugWrap.innerHTML='';
    (sugs||[]).slice(0,10).forEach(d=>{
      const lbl=[d.no_dossier,d.client].filter(Boolean).join(' — ');
      const btn=h('button',{type:'button',onClick:()=>{ toInp.value=d.no_dossier; sugWrap.innerHTML=''; }},
        lbl+(d.statut?(' ['+d.statut+']'):''));
      sugWrap.appendChild(btn);
    });
  };
  toInp.addEventListener('input',()=>{ refreshSug(); });
  const msg=h('p',{style:{fontSize:'12px',color:'var(--muted)',margin:'0 0 12px',lineHeight:1.5}},
    'Toutes les saisies du dossier fictif seront rattachées au dossier réel choisi (production, matières traça, liens rentabilité).');
  const form=h('div',{className:'add-row-form',style:{minWidth:'min(480px,92vw)'}},
    h('button',{type:'button',className:'add-row-close',title:'Fermer',onClick:(e)=>{e.stopPropagation();closeModal();}},'×'),
    h('h3',{style:{marginBottom:'12px',color:'#a78bfa'}},iconEl('file-text',16),' Rattacher un dossier fictif'),
    msg,
    h('div',{className:'fd'},h('label',null,'Dossier fictif'),fromSel),
    h('div',{className:'fd',style:{marginTop:'14px'}},h('label',null,'Dossier réel existant'),toInp,sugWrap),
    h('div',{style:{display:'flex',gap:'8px',justifyContent:'flex-end',marginTop:'18px'}},
      h('button',{type:'button',className:'btn-ghost',onClick:()=>closeModal()},'Annuler'),
      h('button',{type:'button',className:'btn-fictif-sm',onClick:async()=>{
        const from=String(fromSel.value||'').trim();
        const to=String(toInp.value||'').trim();
        if(!from){ toast('Choisissez un dossier fictif','error'); return; }
        if(!to){ toast('Indiquez le dossier cible','error'); return; }
        if(!confirm('Rattacher « '+fictifOfDisplay(from)+' » → « '+to+' » ?\n\nToutes les saisies concernées seront modifiées.')) return;
        try{
          const r=await api('/api/saisies/reassign/fictif',{
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({from_no_dossier:from,to_no_dossier:to})
          });
          closeModal();
          toast((r.updated_saisies||0)+' saisie(s) rattachée(s) → '+r.to_no_dossier,'success');
          await loadFilters();
          await loadSaisies();
        }catch(err){ toast(err.message||'Rattachement impossible','error'); }
      }},'Rattacher')
    )
  );
  const modal=h('div',{className:'add-row-modal',onClick:e=>{if(e.target===modal)closeModal();}},form);
  document.getElementById('root').appendChild(modal);
  if(sources.length===1) fromSel.value=sources[0].no_dossier;
}

function renderSaisies(){
  const d=S.saisies;
  if(!d) return h('div',{className:'card-empty'},'Chargement...');
  // Pour fabrication: utiliser nom si operateur_lie n'est pas défini
  const userOperateur = (S.user && (S.user.operateur_lie || S.user.nom)) || '';
  if(!canViewAllProd(S.user) && !userOperateur)
    return h('div',{className:'card'},h('div',{className:'card-blocked'},h('div',{className:'cb-icon'},iconEl('lock',32)),h('div',{className:'cb-msg'},'Compte non lié à un opérateur.')));
 
  const readOnly=isFab(S.user);
 
  function fmtDurMin(m){
    if(m==null||!isFinite(m)||m<=0) return '-';
    const mm = Math.round(Number(m));
    if(mm < 60) return mm+' min';
    const hh = Math.floor(mm/60);
    const rm = mm%60;
    return hh+' h '+String(rm).padStart(2,'0')+' min';
  }

  function addDurations(baseRows){
    const rows = (baseRows||[]).slice();
    // Durée = écart avec la saisie suivante du même opérateur (en minutes)
    const byOp = new Map();
    rows.forEach(r=>{
      const k = String(r.operateur||'').trim();
      if(!byOp.has(k)) byOp.set(k, []);
      byOp.get(k).push(r);
    });
    byOp.forEach(list=>{
      list.sort((a,b)=>{
        const da = Date.parse(String(a.date_operation||'')) || 0;
        const db = Date.parse(String(b.date_operation||'')) || 0;
        if(da !== db) return da - db;
        return (Number(a.id)||0) - (Number(b.id)||0);
      });
      for(let i=0;i<list.length;i++){
        const cur = list[i];
        const nxt = list[i+1];
        let dur = null;
        if(nxt){
          const t1 = Date.parse(String(cur.date_operation||'')) || NaN;
          const t2 = Date.parse(String(nxt.date_operation||'')) || NaN;
          if(isFinite(t1) && isFinite(t2) && t2 >= t1){
            const m = Math.round((t2 - t1)/60000);
            // Filtre anti-absurde (ex: oubli badgeage) : > 12h => on masque
            dur = (m > 0 && m <= 12*60) ? m : null;
          }
        }
        cur.duree_min = dur;
      }
    });
    return rows;
  }
 
  // ── Tri ──────────────────────────────────────────────────────
  let rows=addDurations(d.rows||[]);
  if(S.sortState.col) rows=sortRows(rows,S.sortState.col,S.sortState.asc);

  // ── Calcul métrage dossier (Fin dossier = compteur fin - compteur début) ──
  // Priorité aux colonnes dédiées metrage_total_debut / metrage_total_fin.
  // Fallback sur metrage_prevu / metrage_reel pour les anciennes lignes sans compteurs.
  (function(){
    const debutByDossier = {}; // no_dossier → compteur début (metrage_total_debut ?? metrage_prevu)
    const chrono = [...rows].sort((a,b)=>(a.date_operation||'').localeCompare(b.date_operation||''));
    chrono.forEach(r=>{
      if(r.operation_code==='01' && r.no_dossier){
        const ctr = r.metrage_total_debut ?? r.metrage_prevu;
        if(ctr!=null) debutByDossier[r.no_dossier] = parseFloat(ctr);
      }
      if(r.operation_code==='89' && r.no_dossier){
        const finCtr  = r.metrage_total_fin ?? null;   // compteur fin uniquement
        const debutCtr = debutByDossier[r.no_dossier] ?? null;
        if(finCtr!=null && debutCtr!=null){
          r._metrage_dossier = parseFloat(finCtr) - debutCtr;  // fin_counter − debut_counter
        } else if(r.metrage_reel!=null && debutCtr!=null && !r.metrage_total_fin){
          // Ancien format : metrage_reel était le compteur fin (avant introduction des nouvelles colonnes)
          r._metrage_dossier = parseFloat(r.metrage_reel) - debutCtr;
        }
        // Si metrage_total_fin absent et metrage_reel = valeur directe produite : pas de calcul
      }
    });
  })();

  const COLS=[
    {key:'date_operation',  label:'Date'},
    {key:'operation',       label:'Opération'},
    {key:'duree_min',       label:'Durée'},
    {key:'operateur',       label:'Opérateur'},
    {key:'machine',         label:'Machine'},
    {key:'no_dossier',      label:'Dossier'},
    {key:'quantite_traitee',   label:'Qté traitée'},
    {key:'metrage_reel',    label:'Métrage (m)'},
    {key:'commentaire',     label:'Commentaire'},
    {key:'_badge',          label:''},
  ];
 
  // ── Header avec tri ──────────────────────────────────────────
  const ths=COLS.map(col=>{
    if(col.key==='_badge') return h('th',null,'');
    const isSorted=S.sortState.col===col.key;
    const arrow=isSorted?(S.sortState.asc?' ↑':' ↓'):'';
    const th=h('th',{style:{cursor:'pointer',userSelect:'none',whiteSpace:'nowrap'}},col.label+arrow);
    th.addEventListener('click',()=>{
      if(S.sortState.col===col.key){S.sortState.asc=!S.sortState.asc;}
      else{S.sortState={col:col.key,asc:true};}
      render();
    });
    return th;
  });
 
  // ── Checkbox "tout sélectionner" ─────────────────────────────
  const allIds=rows.map(r=>r.id);
  const allChecked=allIds.length>0&&allIds.every(id=>S.selectedRows.has(id));
  const chkAll=h('input',{type:'checkbox'});
  chkAll.checked=allChecked;
  chkAll.addEventListener('change',()=>{
    if(chkAll.checked) allIds.forEach(id=>S.selectedRows.add(id));
    else S.selectedRows.clear();
    render();
  });
  const thChk=h('th',null,chkAll);
  ths.unshift(thChk);
 
  const tbody=h('tbody',null);
 
  rows.forEach(row=>{
    const fictifRow = isFictifSaisieRow(row);
    const tr=h('tr',{className:'data-row'+(fictifRow?' saisie-row-fictif':''),style:{cursor:readOnly?'default':'pointer'}});
    // PAR — contrastes plus forts + catégorie production en vert
    const opCode = row.operation_code || '';
    const cat    = row.operation_category || '';

    let rowBg = '';
    if (fictifRow) {
      rowBg = 'rgba(167,139,250,.10)';          // dossier fictif (FICTIF:)
    } else if (row.operation_severity === 'critique') {
      rowBg = 'rgba(248,113,113,.18)';          // rouge soutenu
    } else if (row.operation_severity === 'attention') {
      rowBg = 'rgba(251,191,36,.18)';           // jaune soutenu
    } else if (cat === 'production' || opCode === '03' || opCode === '88') {
      rowBg = 'rgba(52,211,153,.12)';           // vert production
    } else if (cat === 'personnel' || opCode === '86' || opCode === '87') {
      rowBg = 'rgba(167,139,250,.10)';          // violet discret arrivée/départ
    } else if (cat === 'calage' || opCode === '02') {
      rowBg = 'rgba(251,191,36,.08)';           // jaune doux calage
    }
    if (rowBg) tr.style.background = rowBg;
    if (S.selectedRows.has(row.id)) tr.style.background = 'rgba(34,211,238,.12)';
 
    if(!readOnly) tr.addEventListener('click',()=>openEditModal(row));
 
    // Checkbox ligne
    const chk=h('input',{type:'checkbox'});
    chk.checked=S.selectedRows.has(row.id);
    chk.addEventListener('click',e=>e.stopPropagation());
    chk.addEventListener('change',()=>{
      if(chk.checked) S.selectedRows.add(row.id);
      else S.selectedRows.delete(row.id);
      render();
    });
    const tdChk=h('td',null,chk);
    tdChk.addEventListener('click',e=>e.stopPropagation());
    tr.appendChild(tdChk);
 
    let badge=null;
    if(row.est_manuel) badge=h('span',{className:'badge-manuel'},'+ Manuel');
    else if(row.modifie_par) badge=h('span',{className:'badge-modif',title:'Modifié par '+row.modifie_par+' le '+fD(row.modifie_le)},'✏ Corrigé');
 
    tr.appendChild(h('td',{style:{fontSize:'11px',color:'var(--muted)',whiteSpace:'nowrap',fontFamily:'monospace'}},fDSecs(row.date_operation)));
    tr.appendChild(h('td',null,row.operation||'-'));
    tr.appendChild(h('td',{style:{whiteSpace:'nowrap',color:'var(--muted)'}},fmtDurMin(row.duree_min)));
    tr.appendChild(h('td',null,opName(row.operateur)));
    tr.appendChild(h('td',null,row.machine||'-'));
    tr.appendChild(h('td',null,row.no_dossier||'-'));
    tr.appendChild(h('td',null,fN(row.quantite_traitee)));
    tr.appendChild(h('td',{style:{color:'var(--c3)'}},
      row._metrage_dossier!=null
        ? (()=>{
            const finCtr   = row.metrage_total_fin   ?? row.metrage_reel;
            const debutCtr = row.metrage_total_debut != null
              ? row.metrage_total_debut
              : (finCtr!=null ? finCtr - row._metrage_dossier : null);
            const tip = 'Métrage produit = compteur fin − compteur début'
              + (finCtr!=null   ? '\nFin : '+fN(finCtr)+' m'   : '')
              + (debutCtr!=null ? '\nDébut : '+fN(debutCtr)+' m' : '');
            return h('span',{title:tip},'⇒ '+fN(row._metrage_dossier)+' m');
          })()
        : row.metrage_total_fin!=null   ? fN(row.metrage_total_fin)+' m (cpt fin)'
        : row.metrage_reel!=null        ? fN(row.metrage_reel)+' m'
        : row.metrage_total_debut!=null ? h('span',{style:{color:'var(--muted)',fontSize:'11px'}},fN(row.metrage_total_debut)+' m (déb.)')
        : row.metrage_prevu!=null       ? h('span',{style:{color:'var(--muted)',fontSize:'11px'}},fN(row.metrage_prevu)+' m (déb.)')
        : '-'));
    if(readOnly){
      tr.appendChild(h('td',{style:{maxWidth:'200px',overflow:'hidden',textOverflow:'ellipsis'}},row.commentaire||''));
    }else{
      tr.appendChild(makeEditableComment(row));
    }
    tr.appendChild(h('td',null,badge));
 
    if(!readOnly){
      const addBtn=h('button',{className:'add-row-btn',title:'Insérer une ligne après',onClick:e=>{e.stopPropagation();openAddModal(row);}},'+');
      const delBtn=h('button',{className:'add-row-btn',title:'Supprimer cette ligne',
        style:{left:'calc(50% + 18px)',background:'var(--danger)',borderColor:'var(--bg)'},
        onClick:async e=>{
          e.stopPropagation();
          if(!confirm('Supprimer cette saisie ?'))return;
          pushUndo('delete',row);
          try{
            await api('/api/saisies/'+row.id,{method:'DELETE'});
            toast('Saisie supprimée');await loadSaisies();
          }catch(err){undoStack.pop();toast(err.message,'error');}
        }
      },'−');
      const firstTd=tr.querySelector('td:nth-child(2)');
      if(firstTd){firstTd.style.position='relative';firstTd.appendChild(addBtn);firstTd.appendChild(delBtn);}
    }
    tbody.appendChild(tr);
  });
 
  // ── Barre d'actions ──────────────────────────────────────────
  const selCount=S.selectedRows.size;
  const headerRight=h('div',{style:{display:'flex',gap:'8px',alignItems:'center',flexWrap:'wrap'}});

  // Pagination (offset/limit) : évite de scroller toute la page
  const total = Number(d.total||0);
  const off = Number(S.saisiesOffset||0);
  const lim = Number(S.saisiesLimit||200);
  const from = total ? Math.min(total, off+1) : 0;
  const to = total ? Math.min(total, off + (rows||[]).length) : 0;
  const pager = h('div',{style:{display:'inline-flex',alignItems:'center',gap:'6px'}},
    h('button',{className:'btn-ghost',title:'Page précédente',disabled:off<=0,onClick:async()=>{
      const n = Math.max(0, off - lim);
      await loadSaisies({offset:n,limit:lim});
      render();
    }},'‹'),
    h('span',{style:{fontSize:'11px',color:'var(--muted)',fontFamily:'monospace'}}, total?(`${from}-${to}/${total}`):'0'),
    h('button',{className:'btn-ghost',title:'Page suivante',disabled:(off+lim)>=total,onClick:async()=>{
      const n = Math.min(Math.max(0,total-lim), off + lim);
      await loadSaisies({offset:n,limit:lim});
      render();
    }},'›'),
  );
  headerRight.appendChild(pager);
 
  if(readOnly){
    headerRight.appendChild(h('span',{className:'readonly-notice'},iconEl('eye',13),' Lecture seule'));
  }else{
    const btnUndo=h('button',{id:'btn-undo',className:'btn-ghost',title:'Annuler ('+undoStack.length+')',onClick:doUndo},iconEl('rotate-ccw',13),' Annuler ('+undoStack.length+')');
    if(undoStack.length===0) btnUndo.setAttribute('disabled','true');
    const btnRedo=h('button',{id:'btn-redo',className:'btn-ghost',title:'Rétablir ('+redoStack.length+')',onClick:doRedo},iconEl('rotate-cw',13),' Rétablir ('+redoStack.length+')');
    if(redoStack.length===0) btnRedo.setAttribute('disabled','true');
 
    headerRight.appendChild(btnUndo);
    headerRight.appendChild(btnRedo);
 
    if(selCount>0){
      headerRight.appendChild(h('button',{className:'btn-danger',onClick:bulkDelete},iconEl('trash',13),' Supprimer ('+selCount+')'));
    }
    headerRight.appendChild(h('button',{className:'btn-sm',onClick:()=>openAddModal(rows[rows.length-1]||null)},iconEl('plus',13),' Ajouter'));
    headerRight.appendChild(h('button',{className:'btn-fictif-sm',onClick:()=>openFictifReassignModal()},iconEl('file-text',13),' Dossier fictif'));
    headerRight.appendChild(h('button',{className:'btn-ghost',onClick:()=>exportBlob('/api/saisies/export?'+buildParams(),'saisies.xlsx')},iconEl('download',13),' Export'));
  }
 
  return h('div',null,
    h('div',{className:'card'},
      h('div',{className:'card-header'},
        h('h3',null,'Saisies'),
        h('div',{style:{display:'flex',gap:'12px',alignItems:'center'}},
          headerRight
        )
      ),
      // Wrapper synchronisé : scrollbar miroir en haut ↔ bas
      (() => {
        const tableEl = h('table',null,
          h('thead',null,h('tr',null,...ths)),
          tbody
        );
        const bot = h('div',{className:'saisies-bot'},h('div',{style:{overflowX:'auto',paddingBottom:'4px'}},tableEl));
        const topInner = h('div',{style:{height:'1px',width:tableEl.scrollWidth+'px'}});
        const top = h('div',{style:{overflowX:'auto',height:'10px',marginBottom:'0'}},topInner);
        // Synchronisation scroll
        const botX = bot.firstChild;
        top.addEventListener('scroll',()=>{ botX.scrollLeft = top.scrollLeft; });
        botX.addEventListener('scroll',()=>{ top.scrollLeft = botX.scrollLeft; });
        // Mettre à jour la largeur fantôme après rendu
        requestAnimationFrame(()=>{
          topInner.style.width = tableEl.offsetWidth+'px';
        });
        return h('div',{className:'saisies-table-wrap'},top,bot);
      })()
    )
  );
}

function renderSaisiesWithImport(){
  const admin = isAdmin(S.user);
  const parts = [];

  if(admin){
    const isOpen = !!S.importOpen;
    const header = h('div',{
      className:'card-header',
      style:{cursor:'pointer'},
      onClick:()=>{S.importOpen=!S.importOpen;render();}
    },
      h('h3',null,'⬆ Importer des saisies (CSV / Excel)'),
      h('span',{style:{fontSize:'12px',color:'var(--muted)'}},isOpen?'▲ Masquer':'▼ Afficher')
    );

    if(isOpen){
      const zone=h('div',{className:'drop-zone'},
        h('div',{className:'dz-icon'},iconEl('cloud-upload',36)),
        h('div',{className:'dz-title'},'Glisser un fichier ici'),
        h('div',{className:'dz-sub'},'CSV, Excel (.xlsx, .xls, .xlsm) — ou cliquer pour parcourir')
      );
      const inp=h('input',{type:'file',accept:'.csv,.xlsx,.xls,.xlsm',style:{display:'none'}});
      inp.addEventListener('change',e=>{if(e.target.files[0])upload(e.target.files[0]);});
      zone.addEventListener('click',()=>inp.click());
      zone.addEventListener('dragover',e=>{e.preventDefault();zone.classList.add('drag');});
      zone.addEventListener('dragleave',()=>zone.classList.remove('drag'));
      zone.addEventListener('drop',e=>{
        e.preventDefault();zone.classList.remove('drag');
        const f=e.dataTransfer.files[0];if(f)upload(f);
      });
      parts.push(h('div',{className:'card',style:{marginBottom:'16px'}},
        header,
        h('div',{style:{padding:'0 20px 20px'}}, zone, inp)
      ));
    } else {
      parts.push(h('div',{className:'card',style:{marginBottom:'16px'}}, header));
    }
  }

  parts.push(renderSaisies());
  return h('div',null,...parts);
}

function renderImport(){
  const zone=h('div',{className:'drop-zone'},h('div',{className:'dz-icon'},iconEl('cloud-upload',36)),h('div',{className:'dz-title'},'Glisser un fichier ici'),h('div',{className:'dz-sub'},'CSV, Excel (.xlsx, .xls, .xlsm) — ou cliquer pour parcourir'));
  const inp=h('input',{type:'file',accept:'.csv,.xlsx,.xls,.xlsm',style:{display:'none'}});
  inp.addEventListener('change',e=>{if(e.target.files[0])upload(e.target.files[0]);});
  zone.addEventListener('click',()=>inp.click());zone.addEventListener('dragover',e=>{e.preventDefault();zone.classList.add('drag');});zone.addEventListener('dragleave',()=>zone.classList.remove('drag'));
  zone.addEventListener('drop',e=>{e.preventDefault();zone.classList.remove('drag');if(e.dataTransfer.files[0])upload(e.dataTransfer.files[0]);});
  zone.appendChild(inp);
  const list=h('div',{className:'card'},h('div',{className:'card-header'},h('h3',null,'Historique des imports ('+S.imports.length+')')),
    S.imports.length===0?h('div',{className:'card-empty'},'Aucun import encore'):
    h('div',null,...S.imports.map(i=>h('div',{className:'import-row'},
      h('div',{style:{flex:1}},h('div',{style:{fontSize:'14px',fontWeight:'500',color:'var(--text)'}},i.filename),h('div',{style:{fontSize:'11px',color:'var(--muted)',fontFamily:'monospace',marginTop:'2px'}},(i.imported_at||'').slice(0,16).replace('T',' ')+'  —  '+i.row_count+' lignes')),
      h('div',{style:{display:'flex',gap:'8px'}},h('button',{className:'btn-ghost',onClick:()=>exportBlob('/api/imports/'+i.id+'/export',i.filename.replace(/\.[^.]+$/,'')+'_export.xlsx')},iconEl('download',13),' Export'),h('button',{className:'btn-danger',onClick:()=>deleteImport(i.id,i.filename)},iconEl('trash',13),' Supprimer'))
    )))
  );
  return h('div',null,zone,list);
}

  // ────────────────────────────────────────────────────────────────────
  // ÉTAPE 2h — Filtres + Sanity + Statut machines (page Production complète)
  //
  // Code extrait littéralement de app/web/html.py :
  //   - applyF : lignes 7156-7166
  //   - makeDateSelect / makeDateInput : 7596-7660
  //   - renderFilters : 7662-7701
  //   - renderDossierFilterChipsRow : 7703-7713
  //   - makeMultiSelect : 7716-7804
  //   - syncDossierFilterSuggest : 7805-7840
  //   - pickDossierFilter / removeDossierFilter : 7842-7857
  //   - makeDossierFilterSearch : 7858-7932
  //   - renderSanity : 7933-7950
  //   - renderSanityEventsBlock : 7962-7985
  //   - renderMachineStatusCards : 8905-8986
  // ────────────────────────────────────────────────────────────────────

async function applyF(){
  const needSais=S.page==='saisies' || (S.page==='production' && (S.subPage||'kpis')==='saisies');
  // Quand on change les filtres, repartir en haut (offset 0)
  S.saisiesOffset = 0;
  await Promise.all([
    loadHist(),
    loadProd(),
    needSais?loadSaisies({noRender:true}):Promise.resolve()
  ]);
  render();
}

function makeDateSelect(value, onChange){
  const parts=(value||'').split('-');
  const yyyy=parts[0]||'', mm=parts[1]||'', dd=parts[2]||'';

  const jSel=h('select',{style:{background:'var(--bg)',border:'1px solid var(--border)',borderRadius:'6px',padding:'7px 6px',color:'var(--text)',fontSize:'12px',fontFamily:'inherit'}});
  const mSel=h('select',{style:{background:'var(--bg)',border:'1px solid var(--border)',borderRadius:'6px',padding:'7px 6px',color:'var(--text)',fontSize:'12px',fontFamily:'inherit'}});
  const aSel=h('select',{style:{background:'var(--bg)',border:'1px solid var(--border)',borderRadius:'6px',padding:'7px 6px',color:'var(--text)',fontSize:'12px',fontFamily:'inherit'}});

  jSel.appendChild(h('option',{value:''},'JJ'));
  for(let i=1;i<=31;i++){
    const v=String(i).padStart(2,'0');
    const opt=h('option',{value:v},v);
    if(v===dd)opt.selected=true;
    jSel.appendChild(opt);
  }

  const mois=['Jan','Fév','Mar','Avr','Mai','Jun','Jul','Aoû','Sep','Oct','Nov','Déc'];
  mSel.appendChild(h('option',{value:''},'MM'));
  mois.forEach((m,i)=>{
    const v=String(i+1).padStart(2,'0');
    const opt=h('option',{value:v},m);
    if(v===mm)opt.selected=true;
    mSel.appendChild(opt);
  });

  const y=new Date().getFullYear();
  aSel.appendChild(h('option',{value:''},'AAAA'));
  for(let i=y-1;i<=y+1;i++){
    const opt=h('option',{value:String(i)},String(i));
    if(String(i)===yyyy)opt.selected=true;
    aSel.appendChild(opt);
  }

  const update=()=>{
    const v=(aSel.value&&mSel.value&&jSel.value)
      ? aSel.value+'-'+mSel.value+'-'+jSel.value : '';
    onChange(v);
  };
  jSel.addEventListener('change',update);
  mSel.addEventListener('change',update);
  aSel.addEventListener('change',update);

  return h('div',{style:{display:'flex',gap:'4px',alignItems:'center'}},jSel,mSel,aSel);
}

function makeDateInput(value, onChange, ariaLabel){
  const inp = h('input',{
    type:'date',
    className:'filter-input',
    value: value || '',
    ...(ariaLabel ? {'aria-label': ariaLabel, title: ariaLabel} : {}),
  });
  inp.addEventListener('change',()=>onChange(inp.value||''));
  // Ouvrir le calendrier au clic (Chrome/Safari supportent showPicker).
  const openPicker = ()=>{
    try{
      if(typeof inp.showPicker === 'function') inp.showPicker();
      else inp.focus();
    }catch(e){ try{inp.focus();}catch(_){} }
  };
  inp.addEventListener('click',openPicker);
  // Sur certains navigateurs, click ouvre déjà; mousedown améliore la réactivité.
  inp.addEventListener('mousedown',()=>{ /* user gesture */ });
  return inp;
}

function renderFilters(){
  const viewAll=canViewAllProd(S.user);
  const ops=S.filters.operators||[];
  const dos=S.filters.dossiers||[];
  const MACHINE_FILTER_ORDER=['Cohésio 1','Cohésio 2','DSI','Repiquage'];
  const machList=(S.filters.machines&&S.filters.machines.length)?S.filters.machines:MACHINE_FILTER_ORDER;
  const machs=machList.map(m=>({value:m,label:m}));
  const parts=[];
 
  if(viewAll){
    // ── Multi-select opérateurs ──────────────────────────────────
    parts.push(makeMultiSelect(
      'Opérateurs',
      ops.map(o=>({value:o,label:opName(o)})),
      ()=>S.fv.operateurs,
      (sel)=>{ S.fv.operateurs=sel; }
    ));

    parts.push(makeDossierFilterSearch(dos));
  }

  if(machs.length){
    parts.push(makeMultiSelect(
      'Machines',
      machs,
      ()=>S.fv.machines,
      (sel)=>{ S.fv.machines=sel; }
    ));
  }
 
  const df=makeDateInput(S.fv.date_from, v=>{S.fv.date_from=v;}, 'Du');
  const dt=makeDateInput(S.fv.date_to,   v=>{S.fv.date_to=v;}, 'Au');
  parts.push(h('div',{className:'filter-group'},h('label',null,'Du'),df));
  parts.push(h('div',{className:'filter-group'},h('label',null,'Au'),dt));
  parts.push(h('button',{className:'filters-apply-btn',onClick:applyF},'Filtrer'));

  const row = h('div',{className:'filters'},...parts);
  const chipsRow = viewAll ? renderDossierFilterChipsRow() : null;
  return h('div',{className:'filters-panel'},row,chipsRow||null);
}

function renderDossierFilterChipsRow(){
  const sel = S.fv.dossiers || [];
  if(!sel.length) return null;
  const chips = h('div',{className:'prod-dossier-chips',id:'prod-filter-dossier-chips'});
  sel.forEach(ref=>{
    const rm = h('button',{type:'button',className:'prod-dossier-chip-remove',title:'Retirer','aria-label':'Retirer '+ref,
      onClick:()=>removeDossierFilter(ref)},'×');
    chips.appendChild(h('span',{className:'prod-dossier-chip'},ref,rm));
  });
  return h('div',{className:'filters-chips-row',id:'prod-filter-dossier-chips-row'},chips);
}

function makeMultiSelect(label, options, selected, onChange){
  // NOTE: `selected` peut être un getter () => array ou un array direct.
  // On utilise toujours le getter pour lire la valeur courante après chaque onChange,
  // sinon la closure capturait l'ancienne référence de tableau.
  const getSelected = typeof selected === 'function'
    ? ()=>{ const v=selected(); return Array.isArray(v)?v:[]; }
    : ()=> Array.isArray(selected) ? selected : [];
  const isSelected = v => getSelected().includes(v);
  const count = getSelected().length;
 
  const triggerLabel = h('span',null, count>0 ? label+' ('+count+')' : label);
  const trigger = h('button',{
    type:'button',
    className:'filter-input multisel-trigger',
  },
    triggerLabel,
    h('span',{className:'multisel-trigger-caret'},'▾')
  );
 
  // Dropdown
  const dropdown = h('div',{
    className:'multisel-dropdown',
    style:{
      position:'absolute',top:'100%',left:'0',zIndex:'50',
      background:'var(--card)',border:'1px solid var(--border)',borderRadius:'10px',
      padding:'8px 0',minWidth:'200px',maxHeight:'220px',overflowY:'auto',
      boxShadow:'0 8px 24px rgba(0,0,0,.3)',display:'none'
    }
  });
 
  // Option "Tout sélectionner / Désélectionner"
  const allChk = h('label',{style:{display:'flex',alignItems:'center',gap:'8px',padding:'6px 14px',cursor:'pointer',fontSize:'12px',color:'var(--muted)',fontWeight:'600'}},
    h('input',{type:'checkbox'}),
    'Tout sélectionner'
  );
  allChk.querySelector('input').checked = count === options.length;
  allChk.querySelector('input').addEventListener('change',e=>{
    const newSel = e.target.checked ? options.map(o=>o.value) : [];
    onChange(newSel);
    // Mettre à jour les checkboxes enfants
    dropdown.querySelectorAll('input[type=checkbox]').forEach((cb,i)=>{if(i>0)cb.checked=e.target.checked;});
    triggerLabel.textContent = newSel.length>0?label+' ('+newSel.length+')':label;
  });
  dropdown.appendChild(allChk);
 
  options.forEach(opt=>{
    const lbl = h('label',{style:{display:'flex',alignItems:'center',gap:'8px',padding:'6px 14px',cursor:'pointer',fontSize:'12px',color:'var(--text2)'}},
      h('input',{type:'checkbox'}),
      h('span',null,opt.label)
    );
    const chk = lbl.querySelector('input');
    chk.checked = isSelected(opt.value);
    chk.addEventListener('change',()=>{
      const curSel = getSelected();
      let newSel = curSel.filter(v=>v!==opt.value);
      if(chk.checked) newSel.push(opt.value);
      onChange(newSel);
      triggerLabel.textContent = newSel.length>0?label+' ('+newSel.length+')':label;
      allChk.querySelector('input').checked = newSel.length===options.length;
    });
    dropdown.appendChild(lbl);
  });
 
  // Toggle dropdown au clic
  let open=false;
  trigger.addEventListener('click',e=>{
    e.stopPropagation();
    open=!open;
    dropdown.style.display=open?'block':'none';
  });
  // Fermer uniquement si le clic est en dehors du composant (trigger + dropdown).
  // Important: on garde `capture:true` car l'app a d'autres listeners globaux,
  // donc on doit filtrer correctement plutôt que compter sur stopPropagation().
  const onDocClick = (e)=>{
    try{
      if(!open) return;
      if(rel && rel.contains && rel.contains(e.target)) return;
      open=false;
      dropdown.style.display='none';
    }catch(_){}
  };
  document.addEventListener('click', onDocClick, {once:false,capture:true,passive:true});
 
  const wrapper=h('div',{className:'filter-group'},h('label',null,label));
  const rel=h('div',{style:{position:'relative'}},trigger,dropdown);
  wrapper.appendChild(rel);
  return wrapper;
}


function syncDossierFilterSuggest(){
  const dd = document.getElementById('prod-filter-dossier-suggest');
  const inp = document.getElementById('prod-filter-dossier-search');
  if(!dd || !inp) return;
  const all = (S.filters && S.filters.dossiers) ? S.filters.dossiers : [];
  const q = (inp.value || '').trim().toLowerCase();
  const selected = new Set((S.fv.dossiers || []).map(d=>String(d)));
  let matches = all;
  if(q) matches = all.filter(d=>String(d).toLowerCase().includes(q));
  matches = matches.filter(d=>!selected.has(String(d))).slice(0, 24);
  dd.innerHTML = '';
  if(!q){
    dd.classList.remove('open');
    return;
  }
  if(!matches.length){
    const empty = document.createElement('div');
    empty.className = 'prod-dossier-suggest-empty';
    empty.textContent = 'Aucun résultat pour « ' + (inp.value || '').trim() + ' »';
    dd.appendChild(empty);
    dd.classList.add('open');
    return;
  }
  const hi = Number(S.dossierFilterHi);
  matches.forEach((ref, i)=>{
    const row = document.createElement('div');
    row.className = 'prod-dossier-suggest-item' + (i === hi ? ' prod-dossier-suggest-item--hi' : '');
    row.textContent = ref;
    row.addEventListener('mousedown', e=>{
      e.preventDefault();
      pickDossierFilter(ref);
    });
    dd.appendChild(row);
  });
  dd.classList.add('open');
}

function pickDossierFilter(ref){
  const v = String(ref || '').trim();
  if(!v) return;
  const cur = (S.fv.dossiers || []).slice();
  if(!cur.includes(v)) cur.push(v);
  S.fv.dossiers = cur;
  S.fv.dossierSearchQ = '';
  S.dossierFilterHi = -1;
  applyF();
}


function removeDossierFilter(ref){
  S.fv.dossiers = (S.fv.dossiers || []).filter(d=>d !== ref);
  applyF();
}


function makeDossierFilterSearch(allDossiers){
  const wrap = h('div', { className: 'filter-group filter-group--dossier', id: 'prod-filter-dossier-wrap' });
  wrap.appendChild(h('label', null, 'Dossier'));

  const rel = h('div', { className: 'prod-dossier-filter' });

  const inp = h('input', {
    type: 'text',
    id: 'prod-filter-dossier-search',
    className: 'search-bar',
    placeholder: 'Rechercher (n° dossier…)',
    autocomplete: 'off',
    value: S.fv.dossierSearchQ || '',
  });
  const dd = h('div', { id: 'prod-filter-dossier-suggest', className: 'prod-dossier-suggest' });

  inp.addEventListener('input', ()=>{
    S.fv.dossierSearchQ = inp.value;
    S.dossierFilterHi = -1;
    syncDossierFilterSuggest();
  });
  inp.addEventListener('focus', ()=>{
    if((inp.value || '').trim()) syncDossierFilterSuggest();
  });
  inp.addEventListener('keydown', e=>{
    const ddEl = document.getElementById('prod-filter-dossier-suggest');
    const items = ddEl ? [...ddEl.querySelectorAll('.prod-dossier-suggest-item')] : [];
    if(e.key === 'Escape'){
      e.preventDefault();
      inp.value = '';
      S.fv.dossierSearchQ = '';
      S.dossierFilterHi = -1;
      if(ddEl){ ddEl.classList.remove('open'); ddEl.innerHTML = ''; }
      return;
    }
    if(!items.length) return;
    if(e.key === 'ArrowDown'){
      e.preventDefault();
      S.dossierFilterHi = Math.min(items.length - 1, (S.dossierFilterHi < 0 ? 0 : S.dossierFilterHi + 1));
      syncDossierFilterSuggest();
    } else if(e.key === 'ArrowUp'){
      e.preventDefault();
      S.dossierFilterHi = Math.max(0, (S.dossierFilterHi < 0 ? 0 : S.dossierFilterHi - 1));
      syncDossierFilterSuggest();
    } else if(e.key === 'Enter'){
      e.preventDefault();
      const i = S.dossierFilterHi >= 0 ? S.dossierFilterHi : 0;
      const ref = items[i] ? items[i].textContent : '';
      if(ref) pickDossierFilter(ref);
    }
  });

  rel.appendChild(inp);
  rel.appendChild(dd);
  wrap.appendChild(rel);

  if(!window._mysifaDossierFilterDocClick){
    window._mysifaDossierFilterDocClick = true;
    document.addEventListener('click', e=>{
      const w = document.getElementById('prod-filter-dossier-wrap');
      if(w && !w.contains(e.target)){
        const dds = document.getElementById('prod-filter-dossier-suggest');
        if(dds) dds.classList.remove('open');
      }
    }, { capture: true, passive: true });
  }

  requestAnimationFrame(()=>{
    if((S.fv.dossierSearchQ || '').trim()) syncDossierFilterSuggest();
  });

  return wrap;
}

// ── Sanity ──────────────────────────────────────────────────────

function renderSanity(sanity, title){
  if(!sanity)return null;
  const score=sanity.score||0;
  const colorMap={success:'var(--success)',warn:'var(--warn)',danger:'var(--danger)'};
  const col=colorMap[sanity.color]||'var(--muted)';
  const r=34,circ=2*Math.PI*r,offset=circ-(score/100)*circ;
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
  svg.setAttribute('width','80');svg.setAttribute('height','80');svg.setAttribute('viewBox','0 0 80 80');svg.style.transform='rotate(-90deg)';
  const bg=document.createElementNS('http://www.w3.org/2000/svg','circle');bg.setAttribute('cx','40');bg.setAttribute('cy','40');bg.setAttribute('r',String(r));bg.setAttribute('fill','none');bg.setAttribute('stroke','var(--border)');bg.setAttribute('stroke-width','8');svg.appendChild(bg);
  const fill=document.createElementNS('http://www.w3.org/2000/svg','circle');fill.setAttribute('cx','40');fill.setAttribute('cy','40');fill.setAttribute('r',String(r));fill.setAttribute('fill','none');fill.setAttribute('stroke',col);fill.setAttribute('stroke-width','8');fill.setAttribute('stroke-linecap','round');fill.setAttribute('stroke-dasharray',String(circ));fill.setAttribute('stroke-dashoffset',String(offset));svg.appendChild(fill);
  return h('div',{className:'sanity-banner'},
    h('div',{className:'sanity-circle'},svg,h('div',{className:'sanity-num',style:{color:col}},String(score))),
    h('div',null,
      h('div',{className:'si-mention',style:{color:col}},(title?title+' — ':'')+(sanity.mention||'')),
      h('div',{className:'si-label'},sanity.weighted?'Qualité de saisie — moyenne pondérée (temps d\'activité)':'Qualité de saisie — Sanity Score')
    )
  );
}

function renderSanityEventsBlock(sanity){
  const events=sanity&&sanity.events?sanity.events:{};
  const keys=Object.keys(events||{}).filter(k=>(events[k]||[]).length>0);
  if(!keys.length){
    return h('div',{className:'card-empty',style:{display:'flex',alignItems:'center',gap:'8px',justifyContent:'center'}},iconEl('check-circle',18),'Aucune anomalie détectée');
  }
  const blocks=keys.map(k=>{
    const lbl=(SANITY_LABELS[k]&&SANITY_LABELS[k].label)?SANITY_LABELS[k].label:k;
    const rows=(events[k]||[]).slice(0,120);
    const items=rows.map(e=>{
      const dos=(e.no_dossier||"").trim();
      return h('div',{style:{display:'flex',gap:'10px',flexWrap:'wrap',alignItems:'center',padding:'6px 0',borderBottom:'1px solid var(--border)'}},
        h('span',{style:{fontFamily:'monospace',fontSize:'11px',color:'var(--muted)'}},e.jour||''),
        h('span',{style:{fontWeight:'700'}},opName(e.operateur||'')),
        dos?h('span',{style:{fontFamily:'monospace',color:'var(--text2)'}},'Dos. '+dos):null
      );
    });
    return h('div',{style:{padding:'14px 20px',borderBottom:'1px solid var(--border)'}},
      h('div',{style:{fontSize:'12px',fontWeight:'800',color:'var(--danger)',marginBottom:'8px'}},lbl+' ('+rows.length+')'),
      h('div',null,...items)
    );
  });
  return h('div',null,...blocks);
}

function renderMachineStatusCards(){
  const ms = S.machineStatus;
  const ICONS = {
    production:  '▶',
    calage:      '⚙',
    arret:       '⛔',
    changement:  '↻',
    nettoyage:   '🧹',
    eteinte:     '○',
    autre:       '·',
  };
  function fmtDuree(min){
    if(min==null||min<0) return null;
    if(min<1) return 'à l\'instant';
    const h=Math.floor(min/60), m=min%60;
    if(h===0) return `${m} min`;
    return m===0?`${h}h`:`${h}h ${m}min`;
  }
  const DUREE_LABEL = {
    production:  'En production depuis',
    calage:      'En calage depuis',
    arret:       'En arrêt depuis',
    changement:  'En changement depuis',
    nettoyage:   'En nettoyage depuis',
    eteinte:     'Éteinte depuis',
    autre:       'Depuis',
  };
  function mkCard(mkey){
    const m = ms && ms[mkey];
    const sk = m ? (m.statut_key||'eteinte') : 'eteinte';
    const label = m ? (m.statut_label||'Éteinte') : 'Éteinte';
    const nom   = m ? m.nom : (mkey==='C1'?'Cohésio 1':'Cohésio 2');
    const op    = m ? (m.operateur||'') : '';
    const dos   = m ? m.dossier : null;
    const icon  = ICONS[sk]||'·';
    const isOn  = sk!=='eteinte';
    const dureeStr = m ? fmtDuree(m.duree_min) : null;
    const dureeLabel = DUREE_LABEL[sk]||'Depuis';
    return h('div',{className:`mst-card mst-${sk}`},
      h('div',{className:'mst-head'},
        h('span',{className:'mst-nom'},nom),
        h('div',{style:{display:'flex',alignItems:'center',gap:'6px'}},
          isOn?h('span',{style:{fontSize:'8px',color:'#22c55e',animation:'pulse 2s infinite',display:'inline-block',borderRadius:'50%',width:'8px',height:'8px',background:'#22c55e'}}):null,
          h('span',{className:'mst-dot'})
        )
      ),
      h('div',{className:'mst-body'},
        h('div',{className:'mst-statut'},icon,' ',label),
        dureeStr?h('div',{className:'mst-duree'},dureeLabel,' ',h('span',{className:'mst-duree-val'},dureeStr)):null,
        op?h('div',{className:'mst-op'},'👤 ',op):null,
        dos?h('div',{className:'mst-dos',style:sk==='changement'?{opacity:'.6',filter:'grayscale(.4)'}:null},
          h('div',{className:'mst-dos-ref'},sk==='changement'?'dossier précédent : #':(h('span',null,'Dossier #')),dos.no_dossier),
          dos.client?h('div',{className:'mst-dos-cli'},dos.client):null,
          dos.designation?h('div',{className:'mst-dos-des'},dos.designation):null
        ):null,
        !ms?h('div',{style:{fontSize:'11px',color:'var(--muted)'}},'Chargement…'):null
      )
    );
  }
  return h('div',null,
    h('div',{className:'section-title',style:{display:'flex',alignItems:'center',justifyContent:'space-between'}},
      h('span',null,iconEl('cpu',13),' Statut machines'),
      h('div',{style:{display:'flex',gap:'8px'}},
        h('button',{
          type:'button',
          id:'mst-refresh-btn',
          style:{fontSize:'10px',color:'var(--accent)',background:'none',border:'none',cursor:'pointer',padding:'2px 6px',fontFamily:'inherit'},
          onClick:async()=>{
            const btn=document.getElementById('mst-refresh-btn');
            if(btn){btn.textContent='↺ Actualisation…';btn.disabled=true;}
            await loadMachineStatus();
            if(btn){btn.textContent='↺ Actualiser';btn.disabled=false;}
          }
        },'↺ Actualiser')
      )
    ),
    h('div',{className:'mst-grid'},
      mkCard('C1'),
      mkCard('C2')
    )
  );
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
          if(!S.historique) await loadHist();
          await loadMachineStatus();
        }else if(S.subPage === 'saisies'){
          await loadSaisies();
        }else if(S.subPage === 'erreurs'){
          await loadHist();
        }
      }
      // Sous-pages "héritées" (compat ?page=xxx)
      else if(S.page === 'historique'){
        await loadHist();
      }else if(S.page === 'saisies'){
        await loadSaisies();
      }else if(S.page === 'import'){
        await loadImports();
      }
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
    ];
    // Filtres haut de page pour les sous-onglets Production qui consomment fv.*
    if(S.page === 'production'){
      containerKids.push(renderFilters());
    }
    containerKids.push(pageContent);
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
    stage: '2i',
    description: 'Onglets Historique + Saisies + Import',
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
    applyF, makeDateSelect, makeDateInput, renderFilters,
    renderDossierFilterChipsRow, makeMultiSelect, syncDossierFilterSuggest,
    pickDossierFilter, removeDossierFilter, makeDossierFilterSearch,
    renderSanity, renderSanityEventsBlock,
    saveSaisie, addSaisie, upload, deleteImport, exportBlob,
    renderHist, renderSaisies, renderSaisiesWithImport, renderImport,
    pushUndo, doUndo, doRedo, applyUndo,
    buildSaisieForm, openAddModal, openEditModal,
    bulkDelete, openFictifReassignModal,
  };

  console.info('[mysifa_prod_core] saisies / hist / import charges - etape 2i', {
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

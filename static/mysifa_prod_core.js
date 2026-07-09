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

    // Mappings OF en attente / dossiers sans OF (étape 2l)
    pendingOfCount: 0,
    pendingOfMappings: [],
    pendingOfAmbigus: [],
    pendingOfSansOf: [],
    pendingOfLoading: false,
    dossiersSansOf: [],
    dossiersSansOfLoading: false,

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
  // Base = vrai PNG "MyS" (dark ou light selon window.__MYSIFA_ENV__) en résolution
  // 192, downscalé sur un canvas 64×64 pour un rendu net, pastille superposée.
  // Détection env : window.__MYSIFA_ENV__ (portail) sinon fallback hostname.
  const __IS_STAGING_FAV = (window.__MYSIFA_ENV__ === 'v1')
    || /^v1\./i.test((window.location && window.location.hostname) || '');
  const __FAV_SFX = __IS_STAGING_FAV ? '-light' : '';
  const __FAV_BASE_SRC = '/static/mys_icon' + __FAV_SFX + '_192.png';
  const __favBaseImg = new Image();
  let __favBaseReady = false;
  __favBaseImg.onload = function(){ __favBaseReady = true; try { refreshAlertsBadge(); } catch(e){} };
  __favBaseImg.src = __FAV_BASE_SRC;

  function __drawFavFallback(ctx){
    const bg = __IS_STAGING_FAV ? '#f1f5f9' : '#0a0e17';
    const fg = __IS_STAGING_FAV ? '#0f172a' : '#f1f5f9';
    ctx.fillStyle = bg;
    ctx.beginPath();
    if(typeof ctx.roundRect === 'function') ctx.roundRect(0, 0, 64, 64, 12);
    else ctx.rect(0, 0, 64, 64);
    ctx.fill();
    ctx.fillStyle = fg;
    ctx.font = 'bold 40px system-ui';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('M', 32, 34);
  }

  function updateFaviconBadge(count){
    // Pastille de comptage désactivée (juillet 2026). Le favicon reste celui servi
    // par le <link rel="icon"> du HTML — pas de canvas overlay, pas d'écrasement.
    return;
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
  const isAdmin = u => u && (u.role === 'direction' || u.role === 'administration' || u.role === 'administration_ventes' || u.role === 'administration_technique' || u.role === 'superadmin');
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
  // ÉTAPE 2l — Onglet Fiches + OF (le dernier !)
  //
  // Code extrait littéralement de app/web/html.py (lignes 10425-11790) :
  //   - Helpers OF : prodOfFmtDate, prodOfStatutLabel, prodOfStatutClass
  //   - Loaders : loadOfImports, loadFiches, loadPendingOfCount,
  //     loadPendingOfMappings, loadDossiersSansOf
  //   - Mapping OF : submitOfMapping, submitOfMappingMulti
  //   - Liaison OF -> dossiers : searchOfsForAttach, attachOfsToDossier,
  //     toggleAttachOfPicker
  //   - Sous-onglets : renderDossiersSansOfTab, renderPendingOfMappingsTab
  //   - Export CSV : _csvEscape, _downloadCsv, exportFichesCsv, exportOfCsv
  //   - Modals OF : openOfEditModal, closeOfEditModal, saveOfEdit,
  //     renderOfEditModal
  //   - Modals fiches : openFicheEditModal, closeFicheEditModal,
  //     saveFicheEdit, renderFicheEditModal
  //   - Modal import PDF : openOfImportModal, closeOfImportModal,
  //     ofHandlePdfFile, ofValidateImport, ofDeleteImport, renderOfImportModal
  //   - Renders : renderPaginationBar, renderOfTab, renderFichesTab,
  //     renderOfPage
  //
  // Note : canAccessOfTab est déjà défini dans le socle 2e — ici on
  // s'appuie dessus.
  // ────────────────────────────────────────────────────────────────────

function prodOfFmtDate(iso){
  if(!iso) return '—';
  const d=String(iso).slice(0,10);
  const m=d.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  return m ? m[3]+'/'+m[2]+'/'+m[1] : d;
}
const OF_FIELD_LABELS={
  of_numero:'OF n°',date_creation:'Date création',delai_client:'Délai client',
  reference:'Référence',machine:'Machine',laize:'Laize',format:'Format',
  matiere:'Matière',ref_matiere:'Réf. matière',glassine:'Glassine',
  ref_adhesif:'Réf. adhésif',qte_adhesif_g:'Qté adhésif (g)',qte_adhesif_kg:'Qté adhésif (kg)',
  adhesif_label:'Adhésif',qte_au_mille:'Quantité au mille',nb_levees:'Nb levées',
  qte_etiquettes:'Qté étiquettes',qte_bobines:'Qté bobines',metrage:'Métrage',
  conditionnement:'Conditionnement',tolerance:'Tolérance',cartons_type:'Type cartons',
  nb_cartons:'Nb cartons',mandrins_dia:'Mandrins dia.',mandrin_longueur:'Mandrin long.',
  nb_mandrins:'Nb mandrins',nb_tubes:'Nb tubes',bobinettes_completes:'Bobinettes complètes',
  outil_1_forme:'Outil 1 — forme',outil_1_numero:'Outil 1 — n°',outil_1_angle:'Outil 1 — angle',
  outil_1_mag:'Outil 1 — mag.',outil_1_cp:'Outil 1 — CP',outil_1_hauteur:'Outil 1 — hauteur',
  outil_1_fournisseur:'Outil 1 — fournisseur',outil_2_forme:'Outil 2 — forme',
  outil_2_numero:'Outil 2 — n°',outil_2_angle:'Outil 2 — angle',outil_2_cp:'Outil 2 — CP',
  outil_alt_forme:'Outil alt. — forme',outil_alt_numero:'Outil alt. — n°',
  outil_alt_angle:'Outil alt. — angle',outil_alt_fournisseur:'Outil alt. — fournisseur',
};
function prodOfStatutLabel(st){
  const m={en_attente:'En attente',valide:'Validé',rejete:'Rejeté'};
  return m[st]||st||'—';
}
function prodOfStatutClass(st){
  if(st==='valide') return 'prod-of-statut prod-of-statut--valide';
  if(st==='rejete') return 'prod-of-statut prod-of-statut--rejete';
  return 'prod-of-statut prod-of-statut--attente';
}
async function loadOfImports(){
  set({ofImportsLoading:true});
  try{
    const q=encodeURIComponent(S.ofSearch||'');
    const offset=(S.ofPage||0)*50;
    const url='/api/of/list?limit=50&offset='+offset+(q?'&q='+q:'');
    const data=await api(url);
    set({
      ofImports: Array.isArray(data.rows)?data.rows:[],
      ofTotal:   data.total||0,
      ofImportsLoading:false,
    });
  }catch(e){
    set({ofImportsLoading:false});
    toast(e.message||'Erreur chargement des OF','error');
  }
}

async function loadFiches(){
  set({fichesLoading:true});
  try{
    const q=encodeURIComponent(S.ficheSearch||'');
    const offset=(S.fichePage||0)*50;
    const url='/api/fiches-techniques/list?limit=50&offset='+offset+(q?'&q='+q:'');
    const data=await api(url);
    set({fiches:Array.isArray(data.rows)?data.rows:[],ficheTotal:data.total||0,fichesLoading:false});
  }catch(e){
    set({fichesLoading:false});
    toast(e.message||'Erreur chargement fiches techniques','error');
  }
}
async function loadPendingOfCount(){
  try{
    const data=await api('/api/admin/of-link-pending/count');
    set({
      pendingOfCount:Number(data&&data.count||0),
      pendingOfAmbigus:Number(data&&data.ambigus||0),
      pendingOfSansOf:Number(data&&data.sans_of||0),
    });
  }catch(e){
    set({pendingOfCount:0,pendingOfAmbigus:0,pendingOfSansOf:0});
  }
}

async function loadPendingOfMappings(){
  set({pendingOfLoading:true});
  try{
    const data=await api('/api/admin/of-link-pending');
    set({
      pendingOfMappings:Array.isArray(data&&data.items)?data.items:[],
      pendingOfCount:Number(data&&data.total||0),
      pendingOfLoading:false,
    });
  }catch(e){
    set({pendingOfLoading:false});
    toast(e.message||'Erreur chargement mappings à valider','error');
  }
}

async function submitOfMapping(planningId, ofId){
  try{
    await api('/api/admin/link-planning-of',{
      method:'POST',
      body:JSON.stringify({planning_id:planningId, of_id:ofId}),
    });
    toast(ofId==null?'Planning délié.':'OF lié.');
    await loadPendingOfMappings();
    render();
  }catch(e){
    toast(e.message||'Erreur enregistrement','error');
  }
}
async function submitOfMappingMulti(planningId, ofIds){
  if(!ofIds || !ofIds.length){ toast('Aucun OF sélectionné.','error'); return; }
  try{
    const data=await api('/api/admin/planning-of-links',{
      method:'POST',
      body:JSON.stringify({planning_id:planningId, of_ids:ofIds}),
    });
    const added=Number(data&&data.added||0);
    const skip=Number(data&&data.skipped_existing||0);
    let msg='';
    if(added) msg=added+' OF lié'+(added>1?'s':'')+'.';
    if(skip)  msg+=(msg?' ':'')+skip+' déjà liés ignorés.';
    toast(msg||'Aucun changement.');
    await loadPendingOfMappings();
    await loadDossiersSansOf();
    loadPendingOfCount();
    render();
  }catch(e){
    toast(e.message||'Erreur enregistrement','error');
  }
}

async function loadDossiersSansOf(){
  set({dossiersSansOfLoading:true});
  try{
    const data=await api('/api/admin/dossiers-sans-of');
    set({
      dossiersSansOf:Array.isArray(data&&data.items)?data.items:[],
      dossiersSansOfLoading:false,
    });
  }catch(e){
    set({dossiersSansOfLoading:false});
    toast(e.message||'Erreur chargement dossiers sans OF','error');
  }
}

async function searchOfsForAttach(planningId, term){
  const key='attach-'+planningId;
  const inputId='attach-search-'+planningId;
  // Helpers focus : capture la position du caret avant chaque render,
  // restaure après. Évite l'inversion des caractères en saisie rapide.
  function captureFocus(){
    const ae=document.activeElement;
    if(ae && ae.id===inputId){
      return {focused:true, start:ae.selectionStart, end:ae.selectionEnd, value:ae.value};
    }
    return null;
  }
  function restoreFocus(snap){
    if(!snap||!snap.focused) return;
    requestAnimationFrame(()=>{
      const el=document.getElementById(inputId);
      if(!el) return;
      try{
        el.focus();
        if(snap.start!=null){
          const end=snap.end!=null?snap.end:snap.start;
          el.setSelectionRange(snap.start, end);
        }
      }catch(e){}
    });
  }
  let snap=captureFocus();
  S[key+'-loading']=true; render();
  restoreFocus(snap);
  try{
    const q=encodeURIComponent(term||'');
    const data=await api('/api/of/search?limit=20'+(q?'&q='+q:''));
    // Recapture juste avant le 2e render (l'utilisateur a pu taper pendant le fetch)
    snap=captureFocus()||snap;
    S[key+'-results']=Array.isArray(data&&data.items)?data.items:[];
    S[key+'-loading']=false;
    render();
    restoreFocus(snap);
  }catch(e){
    snap=captureFocus()||snap;
    S[key+'-loading']=false; render();
    restoreFocus(snap);
    toast(e.message||'Erreur de recherche','error');
  }
}

async function attachOfsToDossier(planningId, ofIds){
  if(!ofIds || !ofIds.length){ toast('Coche au moins un OF.','error'); return; }
  try{
    const data=await api('/api/admin/planning-of-links',{
      method:'POST',
      body:JSON.stringify({planning_id:planningId, of_ids:ofIds}),
    });
    const added=Number(data&&data.added||0);
    toast(added+' OF attaché'+(added>1?'s':'')+' au dossier.');
    // Reset l'état du picker pour ce dossier
    delete S['attach-'+planningId];
    delete S['attach-'+planningId+'-results'];
    delete S['attach-'+planningId+'-search'];
    delete S['attach-'+planningId+'-loading'];
    await loadDossiersSansOf();
    loadPendingOfCount();
    render();
  }catch(e){
    toast(e.message||'Erreur enregistrement','error');
  }
}

function toggleAttachOfPicker(planningId){
  const key='attach-'+planningId;
  if(S[key]){
    delete S[key];
    delete S[key+'-results'];
    delete S[key+'-search'];
    delete S[key+'-loading'];
    render();
    return;
  }
  S[key]=true;
  S[key+'-search']='';
  // search initiale (vide → 20 plus récents)
  searchOfsForAttach(planningId, '');
}

function renderDossiersSansOfTab(){
  if(S.dossiersSansOfLoading){
    return h('div',{className:'card',style:{padding:'24px',textAlign:'center',color:'var(--muted)'}},'Chargement…');
  }
  const items=S.dossiersSansOf||[];
  if(items.length===0){
    return h('div',{className:'card',style:{padding:'24px',textAlign:'center',color:'var(--muted)'}},
      h('div',{style:{fontSize:'15px',fontWeight:600,color:'var(--text2)',marginBottom:'6px'}},'Aucun dossier sans OF'),
      h('div',null,'Tous les dossiers actifs ont au moins un OF lié.')
    );
  }
  const intro=h('div',{style:{marginBottom:'16px',padding:'12px 16px',background:'var(--accent-bg)',border:'1px solid var(--border)',borderRadius:'10px',fontSize:'13px',color:'var(--text2)',lineHeight:1.6}},
    h('div',{style:{fontWeight:600,color:'var(--text)',marginBottom:'4px'}},
      items.length+' dossier'+(items.length>1?'s':'')+' actif'+(items.length>1?'s':'')+' sans OF lié'),
    'Recherche dans tous les OF existants pour en attacher un (ou plusieurs), ou importe un nouvel OF PDF.'
  );

  const cards=items.map(it=>{
    const key='attach-'+it.planning_id;
    const pickerOpen=!!S[key];
    const results=S[key+'-results']||[];
    const isLoading=!!S[key+'-loading'];
    const searchVal=S[key+'-search']||'';

    const head=h('div',{style:'display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap'},
      h('div',{style:'min-width:0'},
        h('div',{style:'font-size:12px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px'},'Planning #'+it.planning_id),
        h('div',{style:'font-size:14px;font-weight:600;color:var(--text)'},'OF attendu : '+escHtml(it.numero_of||'—')),
        h('div',{style:'font-size:12px;color:var(--muted);margin-top:2px'},
          'Réf produit : ',escHtml(it.ref_produit||'—'),
          it.machine?' · Machine : '+escHtml(it.machine):'',
          it.statut?' · '+escHtml(it.statut):''
        )
      ),
      h('div',{style:'display:flex;gap:8px;align-items:center;flex-wrap:wrap'},
        h('button',{
          style:'padding:8px 14px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text);cursor:pointer;font-size:12px;font-weight:600;white-space:nowrap',
          onClick:openOfImportModal,
          title:'Importer un nouvel OF PDF (la liaison sera à faire ensuite)'
        },iconEl('upload',12),' Importer OF PDF'),
        h('button',{
          style:'padding:8px 14px;border-radius:8px;border:none;background:var(--accent);color:#fff;cursor:pointer;font-size:12px;font-weight:700;white-space:nowrap',
          onClick:()=>toggleAttachOfPicker(it.planning_id)
        },pickerOpen?'Fermer la recherche':'Chercher un OF')
      )
    );

    if(!pickerOpen){
      return h('div',{className:'card',style:{padding:'14px 18px',marginBottom:'12px'}}, head);
    }

    const searchInput=h('input',{
      id:'attach-search-'+it.planning_id,
      type:'text',
      placeholder:'Rechercher par OF n°, référence, machine…',
      value:searchVal,
      style:'width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:9px 12px;color:var(--text);font-size:13px;font-family:inherit;outline:none;margin-bottom:10px',
      oninput:function(e){
        const v=e.target.value;
        S[key+'-search']=v;
        clearTimeout(window['__attachDeb-'+it.planning_id]);
        window['__attachDeb-'+it.planning_id]=setTimeout(()=>searchOfsForAttach(it.planning_id, v), 180);
      },
    });

    const resultRows=isLoading
      ? [h('div',{style:'padding:14px;color:var(--muted);font-size:13px;text-align:center'},'Recherche en cours…')]
      : (results.length===0
          ? [h('div',{style:'padding:14px;color:var(--muted);font-size:13px;text-align:center'},'Aucun résultat')]
          : results.map(c=>{
              const dateImp=(c.date_import||'').slice(0,10)||'—';
              return h('label',{
                style:'display:flex;align-items:center;gap:10px;padding:8px 10px;border:1px solid var(--border);border-radius:8px;margin-bottom:5px;cursor:pointer;background:var(--bg)',
              },
                h('input',{type:'checkbox','data-attach-plan':String(it.planning_id),value:String(c.id),style:'margin:0;flex-shrink:0;cursor:pointer'}),
                h('div',{style:'flex:1;min-width:0'},
                  h('div',{style:'font-weight:600;color:var(--text);font-size:13px'},escHtml(c.of_numero||'—')),
                  h('div',{style:'font-size:12px;color:var(--muted);margin-top:2px'},
                    'Réf : ',escHtml(c.reference||'—'),
                    c.machine?' · '+escHtml(c.machine):'',
                    ' · importé ',dateImp
                  )
                )
              );
            })
        );

    const attachBtn=h('button',{
      style:'margin-top:10px;padding:9px 14px;border-radius:8px;border:none;background:var(--accent);color:#fff;cursor:pointer;font-size:12px;font-weight:700',
      onClick:()=>{
        const boxes=document.querySelectorAll('[data-attach-plan="'+it.planning_id+'"]:checked');
        const ofIds=Array.from(boxes).map(b=>parseInt(b.value,10)).filter(x=>!isNaN(x));
        attachOfsToDossier(it.planning_id, ofIds);
      }
    },'Attacher les OF sélectionnés au dossier');

    return h('div',{className:'card',style:{padding:'14px 18px',marginBottom:'12px'}},
      head,
      h('div',{style:'margin-top:14px;padding-top:12px;border-top:1px dashed var(--border)'},
        searchInput,
        h('div',null, ...resultRows),
        attachBtn
      )
    );
  });

  return h('div',null, intro, ...cards);
}

function renderPendingOfMappingsTab(){
  if(S.pendingOfLoading){
    return h('div',{className:'card',style:{padding:'24px',textAlign:'center',color:'var(--muted)'}},'Chargement…');
  }
  const items=S.pendingOfMappings||[];
  if(items.length===0){
    return h('div',{className:'card',style:{padding:'24px',textAlign:'center',color:'var(--muted)'}},
      h('div',{style:{fontSize:'15px',fontWeight:600,color:'var(--text2)',marginBottom:'6px'}},'Aucun mapping à valider'),
      h('div',null,'Tous les plannings avec un numero_of sont liés automatiquement à un OF, ou n\'ont aucun OF candidat.')
    );
  }
  const intro=h('div',{style:{marginBottom:'16px',padding:'12px 16px',background:'var(--accent-bg)',border:'1px solid var(--border)',borderRadius:'10px',fontSize:'13px',color:'var(--text2)',lineHeight:1.6}},
    h('div',{style:{fontWeight:600,color:'var(--text)',marginBottom:'4px'}},
      items.length+' planning'+(items.length>1?'s':'')+' à associer manuellement'),
    'Le moteur a trouvé plusieurs OF candidats sans pouvoir choisir. Sélectionne le bon OF pour chaque ligne.'
  );

  const cards=items.map(it=>{
    const candRows=(it.candidates||[]).map(c=>{
      const dateImp=(c.date_import||'').slice(0,10)||'—';
      return h('label',{
        style:'display:flex;align-items:center;gap:10px;padding:8px 10px;border:1px solid var(--border);border-radius:8px;margin-bottom:6px;cursor:pointer;background:var(--bg)',
      },
        h('input',{type:'checkbox','data-pending-plan':String(it.planning_id),value:String(c.id),style:'margin:0;flex-shrink:0;cursor:pointer'}),
        h('div',{style:'flex:1;min-width:0'},
          h('div',{style:'font-weight:600;color:var(--text);font-size:13px'},escHtml(c.of_numero||'—')),
          h('div',{style:'font-size:12px;color:var(--muted);margin-top:2px'},
            'Réf : ',escHtml(c.reference||'—'),
            c.machine?' · '+escHtml(c.machine):'',
            ' · importé ',dateImp,
            c.imported_by?' par '+escHtml(c.imported_by):''
          )
        )
      );
    });

    return h('div',{className:'card',style:{padding:'16px 18px',marginBottom:'14px'}},
      h('div',{style:'display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-bottom:12px;flex-wrap:wrap'},
        h('div',null,
          h('div',{style:'font-size:12px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px'},'Planning #'+it.planning_id),
          h('div',{style:'font-size:14px;font-weight:600;color:var(--text)'},escHtml(it.numero_of||'—')),
          h('div',{style:'font-size:12px;color:var(--muted);margin-top:2px'},
            'Réf produit : ',escHtml(it.ref_produit||'—'),
            it.machine?' · Machine : '+escHtml(it.machine):''
          )
        ),
        h('div',{style:'display:flex;gap:8px;align-items:center;flex-wrap:wrap'},
          h('button',{
            style:'padding:8px 14px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--muted);cursor:pointer;font-size:12px;font-weight:600',
            title:'Ignorer (laisse non lié, sera reproposé au prochain chargement)',
            onClick:()=>submitOfMapping(it.planning_id, null)
          },'Ignorer'),
          h('button',{
            style:'padding:8px 14px;border-radius:8px;border:none;background:var(--accent);color:#fff;cursor:pointer;font-size:12px;font-weight:700',
            onClick:()=>{
              const boxes=document.querySelectorAll('[data-pending-plan="'+it.planning_id+'"]:checked');
              const ofIds=Array.from(boxes).map(b=>parseInt(b.value,10)).filter(x=>!isNaN(x));
              if(!ofIds.length){ toast('Coche au moins un OF.','error'); return; }
              submitOfMappingMulti(it.planning_id, ofIds);
            }
          },'Lier les OF sélectionnés')
        )
      ),
      h('div',{style:'font-size:11px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px'},
        (it.candidates||[]).length+' candidat'+((it.candidates||[]).length>1?'s':'')+' trouvé'+((it.candidates||[]).length>1?'s':'')),
      ...candRows
    );
  });

  return h('div',null, intro, ...cards);
}
function _csvEscape(v){
  if(v==null) return '';
  const s=String(v);
  if(s.includes(';')||s.includes('"')||s.includes('\n')||s.includes('\r'))
    return '"'+s.replace(/"/g,'""')+'"';
  return s;
}
function _downloadCsv(filename, headers, cols, rows){
  const lines=[headers.join(';')];
  for(const r of rows){
    lines.push(cols.map(c=>_csvEscape(r[c])).join(';'));
  }
  const csv='\ufeff'+lines.join('\r\n');
  const blob=new Blob([csv],{type:'text/csv;charset=utf-8'});
  const a=document.createElement('a');
  a.href=URL.createObjectURL(blob);
  a.download=filename;
  document.body.appendChild(a);
  a.click();
  setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove();},800);
}
async function exportFichesCsv(){
  try{
    const q=encodeURIComponent(S.ficheSearch||'');
    const all=[];
    let offset=0;
    const limit=200;
    while(true){
      const url='/api/fiches-techniques/list?limit='+limit+'&offset='+offset+(q?'&q='+q:'');
      const data=await api(url);
      const rows=Array.isArray(data.rows)?data.rows:[];
      all.push(...rows);
      if(rows.length<limit||all.length>=(data.total||0)) break;
      offset+=limit;
    }
    if(!all.length){toast('Aucune fiche à exporter.','info');return;}
    const cols=['id','reference','designation','client','format','eti_laize','eti_longueur','support','matiere','machine','nb_couleurs','source','date_import'];
    const headers=['ID','Référence','Désignation','Client','Format','Laize eti. (mm)','Longueur eti.','Support','Matière','Machine','Nb couleurs','Source','Date import'];
    const ymd=new Date().toISOString().slice(0,10);
    _downloadCsv('fiches_techniques_'+ymd+'.csv',headers,cols,all);
    toast(all.length+' fiche'+(all.length>1?'s':'')+' exportée'+(all.length>1?'s':'')+'.');
  }catch(e){
    toast(e.message||'Erreur export.','error');
  }
}
async function exportOfCsv(){
  try{
    const q=encodeURIComponent(S.ofSearch||'');
    const all=[];
    let offset=0;
    const limit=200;
    while(true){
      const url='/api/of/list?limit='+limit+'&offset='+offset+(q?'&q='+q:'');
      const data=await api(url);
      const rows=Array.isArray(data.rows)?data.rows:[];
      all.push(...rows);
      if(rows.length<limit||all.length>=(data.total||0)) break;
      offset+=limit;
    }
    if(!all.length){toast('Aucun OF à exporter.','info');return;}
    const cols=['id','of_numero','reference','machine','delai_client','format','date_creation','qte_etiquettes','qte_bobines','metrage','matiere','conditionnement','outil_1_numero','nb_mandrins','nb_cartons','nb_tubes','statut','date_import','imported_by'];
    const headers=['ID','OF n°','Référence','Machine','Délai client','Format','Date création','Qté étiquettes','Qté bobines','Métrage','Matière','Conditionnement','Outil 1','Nb mandrins','Nb cartons','Nb tubes','Statut','Date import','Importé par'];
    const ymd=new Date().toISOString().slice(0,10);
    _downloadCsv('of_imports_'+ymd+'.csv',headers,cols,all);
    toast(all.length+' OF exporté'+(all.length>1?'s':'')+'.');
  }catch(e){
    toast(e.message||'Erreur export.','error');
  }
}
function openOfEditModal(row){
  set({ofEditModal:{...row}});
  renderOfEditModal();
}
function closeOfEditModal(){
  const existing=document.getElementById('of-edit-overlay');
  if(existing) existing.remove();
  set({ofEditModal:null});
  render();
}
window.closeOfEditModal = closeOfEditModal;

async function saveOfEdit(){
  const m=S.ofEditModal;
  if(!m) return;
  const tv=id=>{const el=document.getElementById(id);return el?el.value.trim()||null:null;};
  const nv=id=>{const el=document.getElementById(id);return el&&el.value!==''?parseFloat(el.value)||null:null;};
  const iv=id=>{const el=document.getElementById(id);return el&&el.value!==''?parseInt(el.value)||null:null;};
  const payload={
    of_numero:            tv('ofe-numero'),
    reference:            tv('ofe-reference'),
    date_creation:        tv('ofe-date'),
    delai_client:         tv('ofe-delai'),
    machine:              tv('ofe-machine'),
    laize:                nv('ofe-laize'),
    format:               tv('ofe-format'),
    matiere:              tv('ofe-matiere'),
    ref_matiere:          tv('ofe-ref-matiere'),
    glassine:             tv('ofe-glassine'),
    ref_adhesif:          tv('ofe-ref-adhesif'),
    qte_adhesif_g:        nv('ofe-qte-adhesif-g'),
    qte_adhesif_kg:       nv('ofe-qte-adhesif-kg'),
    adhesif_label:        tv('ofe-adhesif-label'),
    qte_au_mille:         nv('ofe-qte-mille'),
    nb_levees:            iv('ofe-nb-levees'),
    qte_etiquettes:       iv('ofe-qte'),
    qte_bobines:          nv('ofe-bobines'),
    metrage:              iv('ofe-metrage'),
    tolerance:            tv('ofe-tolerance'),
    bobinettes_completes: tv('ofe-bobinettes'),
    conditionnement:      tv('ofe-cond'),
    cartons_type:         tv('ofe-cartons-type'),
    nb_cartons:           iv('ofe-cartons'),
    mandrins_dia:         tv('ofe-mandrins-dia'),
    mandrin_longueur:     nv('ofe-mandrin-longueur'),
    nb_mandrins:          iv('ofe-mandrins'),
    nb_tubes:             iv('ofe-tubes'),
    outil_1_forme:        tv('ofe-outil1-forme'),
    outil_1_numero:       tv('ofe-outil1-numero'),
    outil_1_angle:        tv('ofe-outil1-angle'),
    outil_1_mag:          tv('ofe-outil1-mag'),
    outil_1_cp:           tv('ofe-outil1-cp'),
    outil_1_hauteur:      nv('ofe-outil1-hauteur'),
    outil_1_fournisseur:  tv('ofe-outil1-fournisseur'),
    outil_2_forme:        tv('ofe-outil2-forme'),
    outil_2_numero:       tv('ofe-outil2-numero'),
    outil_2_angle:        tv('ofe-outil2-angle'),
    outil_2_cp:           tv('ofe-outil2-cp'),
    outil_alt_forme:      tv('ofe-outa-forme'),
    outil_alt_numero:     tv('ofe-outa-numero'),
    outil_alt_angle:      tv('ofe-outa-angle'),
    outil_alt_fournisseur:tv('ofe-outa-fournisseur'),
  };
  try{
    await api('/api/of/'+m.id,{method:'PATCH',body:JSON.stringify(payload)});
    toast('OF mis à jour.');
    closeOfEditModal();
    await loadOfImports();
    render();
  }catch(e){
    toast(e.message||'Erreur mise à jour.','error');
  }
}
window.saveOfEdit = saveOfEdit;
function renderOfEditModal(){
  const existing=document.getElementById('of-edit-overlay');
  if(existing) existing.remove();
  const m=S.ofEditModal;
  if(!m) return;
  const _f=(id,lbl,val,type='text')=>`<div>
    <label style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">${lbl}</label>
    <input id="${id}" type="${type}" value="${String(val==null?'':val).replace(/"/g,'&quot;')}"
      style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:8px 11px;color:var(--text);font-size:13px;font-family:inherit;outline:none;box-sizing:border-box">
  </div>`;
  const _sec=(title,fields,open=true)=>`
    <div class="ofe-sec" style="border:1px solid var(--border);border-radius:10px;margin-bottom:8px;overflow:hidden">
      <div class="ofe-sec-hd" style="display:flex;justify-content:space-between;align-items:center;padding:11px 16px;cursor:pointer;background:var(--accent-bg);border-bottom:1px solid var(--border);user-select:none">
        <span style="font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.8px;color:var(--accent)">${title}</span>
        <svg class="sec-chev" viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.5" style="color:var(--accent);transition:transform .18s;flex-shrink:0;${open?'transform:rotate(180deg)':''}"><polyline points="6 9 12 15 18 9"/></svg>
      </div>
      <div class="ofe-sec-body" style="display:${open?'grid':'none'};grid-template-columns:1fr 1fr 1fr;gap:10px 14px;padding:14px;background:var(--card)">
        ${fields}
      </div>
    </div>`;
  const overlay=document.createElement('div');
  overlay.id='of-edit-overlay';
  overlay.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:1000;display:flex;align-items:center;justify-content:center;padding:16px;box-sizing:border-box';
  overlay.onclick=e=>{if(e.target===overlay)closeOfEditModal();};
  overlay.innerHTML=`
    <div style="background:var(--card);border:1px solid var(--border);border-radius:14px;padding:22px 24px 18px;max-width:900px;width:100%;max-height:92vh;overflow-y:auto;box-sizing:border-box">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
        <div style="font-size:15px;font-weight:700;color:var(--text)">Modifier l'OF</div>
        <button onclick="closeOfEditModal()" style="background:none;border:none;color:var(--muted);cursor:pointer;padding:4px;font-size:20px;line-height:1;font-family:inherit">×</button>
      </div>
      ${_sec('Identification',[
        _f('ofe-numero','OF n°',m.of_numero),
        _f('ofe-reference','Référence',m.reference),
        _f('ofe-date','Date création',(m.date_creation||'').slice(0,10),'date'),
        _f('ofe-delai','Délai client',m.delai_client),
        _f('ofe-machine','Machine',m.machine),
      ].join(''),true)}
      ${_sec('Matière / Support',[
        _f('ofe-laize','Laize',m.laize,'number'),
        _f('ofe-format','Format',m.format),
        _f('ofe-matiere','Matière',m.matiere),
        _f('ofe-ref-matiere','Réf. matière',m.ref_matiere),
        _f('ofe-glassine','Glassine',m.glassine),
      ].join(''))}
      ${_sec('Adhésif',[
        _f('ofe-ref-adhesif','Réf. adhésif',m.ref_adhesif),
        _f('ofe-qte-adhesif-g','Qté adhésif (g)',m.qte_adhesif_g,'number'),
        _f('ofe-qte-adhesif-kg','Qté adhésif (kg)',m.qte_adhesif_kg,'number'),
        _f('ofe-adhesif-label','Label adhésif',m.adhesif_label),
      ].join(''))}
      ${_sec('Quantités',[
        _f('ofe-qte-mille','Qté au mille',m.qte_au_mille,'number'),
        _f('ofe-nb-levees','Nb levées',m.nb_levees,'number'),
        _f('ofe-qte','Qté étiquettes',m.qte_etiquettes,'number'),
        _f('ofe-bobines','Qté bobines',m.qte_bobines,'number'),
        _f('ofe-metrage','Métrage',m.metrage,'number'),
        _f('ofe-tolerance','Tolérance',m.tolerance),
        _f('ofe-bobinettes','Bobinettes complètes',m.bobinettes_completes),
      ].join(''))}
      ${_sec('Conditionnement',[
        _f('ofe-cond','Conditionnement',m.conditionnement),
        _f('ofe-cartons-type','Type cartons',m.cartons_type),
        _f('ofe-cartons','Nb cartons',m.nb_cartons,'number'),
        _f('ofe-mandrins-dia','Mandrins dia.',m.mandrins_dia),
        _f('ofe-mandrin-longueur','Mandrin long.',m.mandrin_longueur,'number'),
        _f('ofe-mandrins','Nb mandrins',m.nb_mandrins,'number'),
        _f('ofe-tubes','Nb tubes',m.nb_tubes,'number'),
      ].join(''))}
      ${_sec('Outillage',[
        _f('ofe-outil1-forme','Outil 1 — forme',m.outil_1_forme),
        _f('ofe-outil1-numero','Outil 1 — n°',m.outil_1_numero),
        _f('ofe-outil1-angle','Outil 1 — angle',m.outil_1_angle),
        _f('ofe-outil1-mag','Outil 1 — mag.',m.outil_1_mag),
        _f('ofe-outil1-cp','Outil 1 — CP',m.outil_1_cp),
        _f('ofe-outil1-hauteur','Outil 1 — hauteur',m.outil_1_hauteur,'number'),
        _f('ofe-outil1-fournisseur','Outil 1 — fournisseur',m.outil_1_fournisseur),
        _f('ofe-outil2-forme','Outil 2 — forme',m.outil_2_forme),
        _f('ofe-outil2-numero','Outil 2 — n°',m.outil_2_numero),
        _f('ofe-outil2-angle','Outil 2 — angle',m.outil_2_angle),
        _f('ofe-outil2-cp','Outil 2 — CP',m.outil_2_cp),
        _f('ofe-outa-forme','Outil alt. — forme',m.outil_alt_forme),
        _f('ofe-outa-numero','Outil alt. — n°',m.outil_alt_numero),
        _f('ofe-outa-angle','Outil alt. — angle',m.outil_alt_angle),
        _f('ofe-outa-fournisseur','Outil alt. — fournisseur',m.outil_alt_fournisseur),
      ].join(''))}
      <div style="display:flex;justify-content:flex-end;gap:10px;margin-top:12px;padding-top:12px;border-top:1px solid var(--border)">
        <button id="ofe-cancel-btn" style="padding:9px 16px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-family:inherit;font-size:13px">Annuler</button>
        <button id="ofe-save-btn" style="padding:9px 16px;border-radius:8px;border:none;background:var(--accent);color:#fff;cursor:pointer;font-family:inherit;font-size:13px;font-weight:700">Enregistrer</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);
  overlay.querySelectorAll('.ofe-sec-hd').forEach(hd=>{
    hd.addEventListener('click',()=>{
      const body=hd.nextElementSibling;
      const chev=hd.querySelector('.sec-chev');
      const open=body.style.display!=='none';
      body.style.display=open?'none':'grid';
      chev.style.transform=open?'':'rotate(180deg)';
    });
  });
  overlay.querySelector('#ofe-cancel-btn').onclick=closeOfEditModal;
  overlay.querySelector('#ofe-save-btn').onclick=saveOfEdit;
}

function openFicheEditModal(row){
  set({ficheEditModal:{...row}});
  renderFicheEditModal();
}
function closeFicheEditModal(){
  const existing=document.getElementById('fiche-edit-overlay');
  if(existing) existing.remove();
  set({ficheEditModal:null});
  render();
}
async function saveFicheEdit(){
  const m=S.ficheEditModal;
  if(!m) return;
  const tv=id=>{const el=document.getElementById(id);return el?el.value.trim()||null:null;};
  const nv=id=>{const el=document.getElementById(id);return el&&el.value!==''?parseFloat(el.value)||null:null;};
  const iv=id=>{const el=document.getElementById(id);return el&&el.value!==''?parseInt(el.value)||null:null;};
  const bv=id=>{const el=document.getElementById(id);return el?parseInt(el.value)||0:0;};
  const payload={
    reference:                  tv('fce-ref'),
    designation:                tv('fce-desig'),
    client:                     tv('fce-client'),
    machine:                    tv('fce-machine'),
    date_modif:                 tv('fce-date-modif'),
    format:                     tv('fce-format'),
    eti_laize:                  nv('fce-eti-laize'),
    eti_longueur:               nv('fce-eti-longueur'),
    eti_rayons:                 nv('fce-eti-rayons'),
    eti_perforations:           tv('fce-eti-perforations'),
    mod_laize:                  nv('fce-mod-laize'),
    mod_longueur:               nv('fce-mod-longueur'),
    mod_nb_front:               iv('fce-mod-front'),
    lateral_ext:                nv('fce-lat-ext'),
    horizontal:                 nv('fce-horizontal'),
    lateral_int:                nv('fce-lat-int'),
    support:                    tv('fce-support'),
    matiere:                    tv('fce-matiere'),
    adhesif:                    tv('fce-adhesif'),
    glassine:                   tv('fce-glassine'),
    laize_optimale:             nv('fce-laize-opt'),
    laize_optionnelle:          nv('fce-laize-optn'),
    epaisseur:                  nv('fce-epaisseur'),
    qte_au_mille:               nv('fce-qte-mille'),
    outil1_forme:               tv('fce-o1-forme'),
    outil1_numero_sifa:         tv('fce-o1-numero'),
    outil1_laize:               nv('fce-o1-laize'),
    outil1_epaisseur:           nv('fce-o1-epaisseur'),
    outil1_nb_dents:            iv('fce-o1-dents'),
    outil1_nb_front:            iv('fce-o1-front'),
    outil1_nb_avance:           iv('fce-o1-avance'),
    outil2_forme:               tv('fce-o2-forme'),
    outil2_numero_sifa:         tv('fce-o2-numero'),
    outil2_epaisseur:           nv('fce-o2-epaisseur'),
    outil2_nb_dents:            iv('fce-o2-dents'),
    outil2_nb_front:            iv('fce-o2-front'),
    outil2_nb_avance:           iv('fce-o2-avance'),
    outil3_forme:               tv('fce-o3-forme'),
    outil3_numero_sifa:         tv('fce-o3-numero'),
    outil3_epaisseur:           nv('fce-o3-epaisseur'),
    outil3_nb_dents:            iv('fce-o3-dents'),
    outil3_nb_front:            iv('fce-o3-front'),
    outil3_nb_avance:           iv('fce-o3-avance'),
    nb_couleurs:                iv('fce-nb-couleurs'),
    recto:                      bv('fce-recto'),
    verso:                      bv('fce-verso'),
    tete1_pantone:              tv('fce-t1-pantone'),
    tete1_couleur:              tv('fce-t1-couleur'),
    tete1_anilox:               tv('fce-t1-anilox'),
    tete1_composition:          tv('fce-t1-compo'),
    tete2_pantone:              tv('fce-t2-pantone'),
    tete2_couleur:              tv('fce-t2-couleur'),
    tete2_anilox:               tv('fce-t2-anilox'),
    tete2_composition:          tv('fce-t2-compo'),
    tete3_pantone:              tv('fce-t3-pantone'),
    tete3_couleur:              tv('fce-t3-couleur'),
    tete3_anilox:               tv('fce-t3-anilox'),
    tete3_composition:          tv('fce-t3-compo'),
    remarque:                   tv('fce-remarque'),
    conditionnement:            tv('fce-cond'),
    mandrin_dia:                tv('fce-mandrin-dia'),
    mandrin_longueur:           nv('fce-mandrin-longueur'),
    enroulement:                tv('fce-enroulement'),
    nb_etiq_bobin:              iv('fce-nb-etiq-bobin'),
    dia_ext:                    nv('fce-dia-ext'),
    poids:                      nv('fce-poids'),
    cales_sachets:              tv('fce-cales-sachets'),
    cartons:                    tv('fce-cartons'),
    nb_au_sol:                  iv('fce-nb-sol'),
    nb_etage:                   iv('fce-nb-etage'),
    nb_bobines_carton:          iv('fce-nb-bob-carton'),
    palette_type:               tv('fce-palette-type'),
    palette_nb_cartons_sol:     iv('fce-palette-sol'),
    palette_nb_cartons_hauteur: iv('fce-palette-hauteur'),
    palette_hauteur_max:        nv('fce-palette-hmax'),
    particularite:              tv('fce-particularite'),
    notes:                      tv('fce-notes'),
  };
  try{
    await api('/api/fiches-techniques/'+m.id,{method:'PATCH',body:JSON.stringify(payload)});
    toast('Fiche mise à jour.');
    closeFicheEditModal();
    await loadFiches();
    render();
  }catch(e){
    toast(e.message||'Erreur mise à jour.','error');
  }
}
function renderFicheEditModal(){
  const existing=document.getElementById('fiche-edit-overlay');
  if(existing) existing.remove();
  const m=S.ficheEditModal;
  if(!m) return;
  const _f=(id,lbl,val,type='text')=>`<div>
    <label style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">${lbl}</label>
    <input id="${id}" type="${type}" value="${String(val==null?'':val).replace(/"/g,'&quot;')}"
      style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:8px 11px;color:var(--text);font-size:13px;font-family:inherit;outline:none;box-sizing:border-box">
  </div>`;
  const _cb=(id,lbl,val)=>`<div>
    <label style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">${lbl}</label>
    <select id="${id}" style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:8px 11px;color:var(--text);font-size:13px;font-family:inherit;outline:none;box-sizing:border-box">
      <option value="0" ${!val||val==0?'selected':''}>Non</option>
      <option value="1" ${val==1?'selected':''}>Oui</option>
    </select>
  </div>`;
  const _sec=(title,fields,open=true)=>`
    <div class="fce-sec" style="border:1px solid var(--border);border-radius:10px;margin-bottom:8px;overflow:hidden">
      <div class="fce-sec-hd" style="display:flex;justify-content:space-between;align-items:center;padding:11px 16px;cursor:pointer;background:var(--accent-bg);border-bottom:1px solid var(--border);user-select:none">
        <span style="font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.8px;color:var(--accent)">${title}</span>
        <svg class="sec-chev" viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.5" style="color:var(--accent);transition:transform .18s;flex-shrink:0;${open?'transform:rotate(180deg)':''}"><polyline points="6 9 12 15 18 9"/></svg>
      </div>
      <div class="fce-sec-body" style="display:${open?'grid':'none'};grid-template-columns:1fr 1fr 1fr;gap:10px 14px;padding:14px;background:var(--card)">
        ${fields}
      </div>
    </div>`;
  const overlay=document.createElement('div');
  overlay.id='fiche-edit-overlay';
  overlay.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:1000;display:flex;align-items:center;justify-content:center;padding:16px;box-sizing:border-box';
  overlay.onclick=e=>{if(e.target===overlay)closeFicheEditModal();};
  overlay.innerHTML=`
    <div style="background:var(--card);border:1px solid var(--border);border-radius:14px;padding:22px 24px 18px;max-width:900px;width:100%;max-height:92vh;overflow-y:auto;box-sizing:border-box">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
        <div style="font-size:15px;font-weight:700;color:var(--text)">Modifier la fiche technique</div>
        <button onclick="closeFicheEditModal()" style="background:none;border:none;color:var(--muted);cursor:pointer;padding:4px;font-size:20px;line-height:1;font-family:inherit">×</button>
      </div>
      ${_sec('Identification',[
        _f('fce-ref','Référence',m.reference),
        _f('fce-desig','Désignation',m.designation),
        _f('fce-client','Client',m.client),
        _f('fce-machine','Machine',m.machine),
        _f('fce-date-modif','Date modif.',m.date_modif),
      ].join(''),true)}
      ${_sec('Étiquette',[
        _f('fce-format','Format',m.format),
        _f('fce-eti-laize','Laize eti. (mm)',m.eti_laize,'number'),
        _f('fce-eti-longueur','Longueur eti. (mm)',m.eti_longueur,'number'),
        _f('fce-eti-rayons','Rayons (mm)',m.eti_rayons,'number'),
        _f('fce-eti-perforations','Perforations',m.eti_perforations),
      ].join(''))}
      ${_sec('Module',[
        _f('fce-mod-laize','Laize module',m.mod_laize,'number'),
        _f('fce-mod-longueur','Longueur module',m.mod_longueur,'number'),
        _f('fce-mod-front','Nb front',m.mod_nb_front,'number'),
      ].join(''))}
      ${_sec('Échenillage',[
        _f('fce-lat-ext','Latéral ext.',m.lateral_ext,'number'),
        _f('fce-horizontal','Horizontal',m.horizontal,'number'),
        _f('fce-lat-int','Latéral int.',m.lateral_int,'number'),
      ].join(''))}
      ${_sec('Matière',[
        _f('fce-support','Support',m.support||m.matiere),
        _f('fce-matiere','Matière',m.matiere),
        _f('fce-adhesif','Adhésif',m.adhesif),
        _f('fce-glassine','Glassine',m.glassine),
        _f('fce-laize-opt','Laize optimale',m.laize_optimale,'number'),
        _f('fce-laize-optn','Laize optionnelle',m.laize_optionnelle,'number'),
        _f('fce-epaisseur','Épaisseur',m.epaisseur,'number'),
        _f('fce-qte-mille','Qté au mille',m.qte_au_mille,'number'),
      ].join(''))}
      ${_sec('Outil 1',[
        _f('fce-o1-forme','Forme',m.outil1_forme),
        _f('fce-o1-numero','N° SIFA',m.outil1_numero_sifa),
        _f('fce-o1-laize','Laize',m.outil1_laize,'number'),
        _f('fce-o1-epaisseur','Épaisseur',m.outil1_epaisseur,'number'),
        _f('fce-o1-dents','Nb dents',m.outil1_nb_dents,'number'),
        _f('fce-o1-front','Nb front',m.outil1_nb_front,'number'),
        _f('fce-o1-avance','Nb avance',m.outil1_nb_avance,'number'),
      ].join(''))}
      ${_sec('Outil 2',[
        _f('fce-o2-forme','Forme',m.outil2_forme),
        _f('fce-o2-numero','N° SIFA',m.outil2_numero_sifa),
        _f('fce-o2-epaisseur','Épaisseur',m.outil2_epaisseur,'number'),
        _f('fce-o2-dents','Nb dents',m.outil2_nb_dents,'number'),
        _f('fce-o2-front','Nb front',m.outil2_nb_front,'number'),
        _f('fce-o2-avance','Nb avance',m.outil2_nb_avance,'number'),
      ].join(''))}
      ${_sec('Outil 3',[
        _f('fce-o3-forme','Forme',m.outil3_forme),
        _f('fce-o3-numero','N° SIFA',m.outil3_numero_sifa),
        _f('fce-o3-epaisseur','Épaisseur',m.outil3_epaisseur,'number'),
        _f('fce-o3-dents','Nb dents',m.outil3_nb_dents,'number'),
        _f('fce-o3-front','Nb front',m.outil3_nb_front,'number'),
        _f('fce-o3-avance','Nb avance',m.outil3_nb_avance,'number'),
      ].join(''))}
      ${_sec('Impression',[
        _f('fce-nb-couleurs','Nb couleurs',m.nb_couleurs,'number'),
        _cb('fce-recto','Recto',m.recto),
        _cb('fce-verso','Verso',m.verso),
        _f('fce-t1-pantone','Tête 1 — Pantone',m.tete1_pantone),
        _f('fce-t1-couleur','Tête 1 — Couleur',m.tete1_couleur),
        _f('fce-t1-anilox','Tête 1 — Anilox',m.tete1_anilox),
        _f('fce-t1-compo','Tête 1 — Composition',m.tete1_composition),
        _f('fce-t2-pantone','Tête 2 — Pantone',m.tete2_pantone),
        _f('fce-t2-couleur','Tête 2 — Couleur',m.tete2_couleur),
        _f('fce-t2-anilox','Tête 2 — Anilox',m.tete2_anilox),
        _f('fce-t2-compo','Tête 2 — Composition',m.tete2_composition),
        _f('fce-t3-pantone','Tête 3 — Pantone',m.tete3_pantone),
        _f('fce-t3-couleur','Tête 3 — Couleur',m.tete3_couleur),
        _f('fce-t3-anilox','Tête 3 — Anilox',m.tete3_anilox),
        _f('fce-t3-compo','Tête 3 — Composition',m.tete3_composition),
        _f('fce-remarque','Remarque',m.remarque),
      ].join(''))}
      ${_sec('Conditionnement',[
        _f('fce-cond','Conditionnement',m.conditionnement),
        _f('fce-mandrin-dia','Mandrin dia.',m.mandrin_dia),
        _f('fce-mandrin-longueur','Mandrin long.',m.mandrin_longueur,'number'),
        _f('fce-enroulement','Enroulement',m.enroulement),
        _f('fce-nb-etiq-bobin','Nb étiq./bobine',m.nb_etiq_bobin,'number'),
        _f('fce-dia-ext','Dia. ext.',m.dia_ext,'number'),
        _f('fce-poids','Poids',m.poids,'number'),
        _f('fce-cales-sachets','Cales / sachets',m.cales_sachets),
        _f('fce-cartons','Cartons',m.cartons),
        _f('fce-nb-sol','Nb au sol',m.nb_au_sol,'number'),
        _f('fce-nb-etage','Nb étages',m.nb_etage,'number'),
        _f('fce-nb-bob-carton','Nb bob./carton',m.nb_bobines_carton,'number'),
      ].join(''))}
      ${_sec('Palettisation',[
        _f('fce-palette-type','Type palette',m.palette_type),
        _f('fce-palette-sol','Nb cartons/sol',m.palette_nb_cartons_sol,'number'),
        _f('fce-palette-hauteur','Nb cartons/hauteur',m.palette_nb_cartons_hauteur,'number'),
        _f('fce-palette-hmax','Hauteur max. (cm)',m.palette_hauteur_max,'number'),
        _f('fce-particularite','Particularité',m.particularite),
      ].join(''))}
      ${_sec('Notes',[
        `<div style="grid-column:1/-1"><label style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Notes</label>
        <textarea id="fce-notes" rows="3" style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:8px 11px;color:var(--text);font-size:13px;font-family:inherit;outline:none;box-sizing:border-box;resize:vertical">${String(m.notes||'').replace(/</g,'&lt;')}</textarea></div>`,
      ].join(''))}
      <div style="display:flex;justify-content:flex-end;gap:10px;margin-top:12px;padding-top:12px;border-top:1px solid var(--border)">
        <button id="fce-cancel-btn" style="padding:9px 16px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-family:inherit;font-size:13px">Annuler</button>
        <button id="fce-save-btn" style="padding:9px 16px;border-radius:8px;border:none;background:var(--accent);color:#fff;cursor:pointer;font-family:inherit;font-size:13px;font-weight:700">Enregistrer</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);
  overlay.querySelectorAll('.fce-sec-hd').forEach(hd=>{
    hd.addEventListener('click',()=>{
      const body=hd.nextElementSibling;
      const chev=hd.querySelector('.sec-chev');
      const open=body.style.display!=='none';
      body.style.display=open?'none':'grid';
      chev.style.transform=open?'':'rotate(180deg)';
    });
  });
  overlay.querySelector('#fce-cancel-btn').onclick=closeFicheEditModal;
  overlay.querySelector('#fce-save-btn').onclick=saveFicheEdit;
}
function openOfImportModal(){
  set({ofImportModal:{step:1,file:null,parsed:null,parsing:false}});
  render();
}
function closeOfImportModal(){
  set({ofImportModal:null});
  render();
}
async function ofHandlePdfFile(file){
  if(!file||!/\.pdf$/i.test(file.name||'')){toast('Fichier PDF requis.','error');return;}
  set({ofImportModal:{step:1,file,parsed:null,parsing:true}});
  render();
  const fd=new FormData();
  fd.append('file',file);
  try{
    const parsed=await fetch('/api/of/parse',{method:'POST',credentials:'include',body:fd})
      .then(async r=>{
        if(r.status===401){window.location.href='/';return null;}
        if(!r.ok){
          const err=await r.json().catch(()=>({}));
          throw new Error(err.detail||('Erreur '+r.status));
        }
        return r.json();
      });
    if(!parsed) return;
    set({ofImportModal:{step:2,file,parsed,parsing:false}});
    render();
  }catch(e){
    set({ofImportModal:{step:1,file:null,parsed:null,parsing:false}});
    toast(e.message||'Analyse PDF impossible.','error');
    render();
  }
}
async function ofValidateImport(){
  const m=S.ofImportModal;
  if(!m||!m.file) return;
  const data={};
  Object.keys(OF_FIELD_LABELS).forEach(k=>{
    const el=document.getElementById('of-f-'+k);
    if(el) data[k]=el.value;
  });
  const fd=new FormData();
  fd.append('file',m.file);
  fd.append('data',JSON.stringify(data));
  try{
    const r=await fetch('/api/of/validate',{method:'POST',credentials:'include',body:fd});
    if(!r.ok){
      const err=await r.json().catch(()=>({}));
      throw new Error(err.detail||('Erreur '+r.status));
    }
    toast('OF importé.');
    set({ofImportModal:null});
    await loadOfImports();
    render();
  }catch(e){
    toast(e.message||'Import impossible.','error');
  }
}
async function ofDeleteImport(id){
  if(!confirm('Supprimer cet import OF de la base ?')) return;
  try{
    await api('/api/of/'+id,{method:'DELETE'});
    toast('Import supprimé.');
    await loadOfImports();
    render();
  }catch(e){
    toast(e.message||'Suppression impossible.','error');
  }
}
function renderPaginationBar(page, total, pageSize, onPrev, onNext){
  const totalPages=Math.max(1,Math.ceil(total/pageSize));
  const start=total===0?0:page*pageSize+1;
  const end=Math.min((page+1)*pageSize,total);
  return h('div',{style:{display:'flex',alignItems:'center',gap:'10px',padding:'12px 0',fontSize:'12px',color:'var(--muted)'}},
    h('button',{
      style:'padding:6px 12px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-size:12px',
      disabled:page===0, onClick:onPrev
    },'← Préc.'),
    h('span',null,total===0?'Aucun résultat':`${start}–${end} sur ${total}`),
    h('button',{
      style:'padding:6px 12px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-size:12px',
      disabled:page>=totalPages-1, onClick:onNext
    },'Suiv. →'),
  );
}

function renderOfTab(){
  const PAGE_SIZE=50;
  const total=S.ofTotal||0;
  const page=S.ofPage||0;

  const toolbar=h('div',{style:{display:'flex',alignItems:'center',gap:'10px',marginBottom:'16px',flexWrap:'wrap'}},
    h('input',{
      id:'of-search-html',
      type:'text',
      placeholder:'Rechercher (OF n°, référence, machine…)',
      value:S.ofSearch||'',
      style:'flex:1;min-width:200px;max-width:320px;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:9px 12px;color:var(--text);font-size:13px;font-family:inherit;outline:none',
      oninput:async function(e){
        const v=e.target.value;
        const ss=e.target.selectionStart, se=e.target.selectionEnd;
        set({ofSearch:v,ofPage:0});
        await loadOfImports();
        render();
        requestAnimationFrame(()=>{
          const el=document.getElementById('of-search-html');
          if(el){el.focus();try{el.setSelectionRange(ss,se);}catch(x){}}
        });
      },
      onkeydown:function(e){
        if(e.key==='Escape'){set({ofSearch:'',ofPage:0});loadOfImports().then(()=>render());e.target.value='';}
      },
    }),
    h('button',{
      style:'padding:9px 14px;border-radius:8px;border:none;background:var(--accent);color:#fff;cursor:pointer;font-size:13px;font-weight:700;white-space:nowrap',
      onClick:openOfImportModal
    },iconEl('upload',13),' Importer un OF'),
    h('button',{
      style:'padding:9px 14px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text);cursor:pointer;font-size:13px;font-weight:600;white-space:nowrap',
      title:'Exporter tous les OF (filtre appliqué) en CSV',
      onClick:exportOfCsv
    },iconEl('download',13),' Exporter CSV'),
    S.user&&S.user.role==='superadmin'&&S.ofSelected.size>0
      ? h('button',{
          style:'padding:9px 14px;border-radius:8px;border:none;background:var(--danger);color:#fff;cursor:pointer;font-size:13px;font-weight:700;white-space:nowrap',
          onClick:async()=>{
            const n=S.ofSelected.size;
            if(!confirm(`Supprimer ${n} OF${n>1?'s':''} ?`)) return;
            try{
              await api('/api/of/bulk',{method:'DELETE',body:JSON.stringify({ids:[...S.ofSelected]})});
              toast(`${n} OF${n>1?'s':''} supprimé${n>1?'s':''}.`);
              set({ofSelected:new Set()});
              await loadOfImports();
              render();
            }catch(e){toast(e.message||'Erreur.','error');}
          }
        },iconEl('trash',13),` Supprimer (${S.ofSelected.size})`)
      : null
  );

  const rows=(S.ofImports||[]).map(row=>{
    const stCls=prodOfStatutClass(row.statut);
    const dateCrea=(row.date_creation||'').slice(0,10)||'—';
    const acts=[
      h('button',{
        style:'padding:4px 8px;border-radius:6px;border:1px solid var(--border);background:transparent;cursor:pointer',
        title:'Modifier', onClick:()=>openOfEditModal(row)
      },iconEl('edit',13)),
    ];
    acts.push(h('button',{
      style:'padding:4px 8px;border-radius:6px;border:1px solid var(--border);background:transparent;cursor:pointer',
      title:'Aperçu OF', onClick:()=>{window.open('/api/of/'+row.id+'/pdf-preview','_blank');}
    },iconEl('eye',13)));
    if(row.pdf_filename){
      acts.push(h('button',{
        style:'padding:4px 8px;border-radius:6px;border:1px solid var(--border);background:transparent;cursor:pointer',
        title:'Télécharger PDF', onClick:()=>{window.open('/api/of/'+row.id+'/pdf','_blank');}
      },iconEl('download',13)));
    }
    if(S.user&&S.user.role==='superadmin'){
      acts.push(h('button',{
        style:'padding:4px 8px;border-radius:6px;border:1px solid rgba(248,113,113,.3);background:transparent;cursor:pointer;color:var(--danger)',
        title:'Supprimer', onClick:()=>ofDeleteImport(row.id)
      },iconEl('trash',13)));
    }
    return h('tr',null,
      h('td',{style:{width:'36px'}},
        h('input',{type:'checkbox',checked:S.ofSelected.has(row.id),style:'cursor:pointer',
          onChange:function(e){
            const sel=new Set(S.ofSelected);
            if(e.target.checked)sel.add(row.id);else sel.delete(row.id);
            set({ofSelected:sel});render();
          }
        })
      ),
      h('td',null,
        h('div',null,escHtml(row.of_numero||'—')),
        row.imported_by?h('div',{style:{fontSize:'11px',color:'var(--muted)'}},escHtml(row.imported_by)):null,
      ),
      h('td',null,escHtml(row.reference||'—')),
      h('td',null,escHtml(row.machine||'—')),
      h('td',null,escHtml(row.delai_client||'—')),
      h('td',null,row.qte_etiquettes!=null?escHtml(String(row.qte_etiquettes)):'—'),
      h('td',null,escHtml(dateCrea)),
      h('td',null,h('span',{className:stCls},prodOfStatutLabel(row.statut))),
      h('td',null,h('div',{style:{display:'flex',gap:'4px'}},...acts)),
    );
  });

  const empty=h('tr',null,
    h('td',{colSpan:'9',style:{textAlign:'center',color:'var(--muted)',padding:'24px'}},
      S.ofImportsLoading?'Chargement…':(S.ofSearch?`Aucun résultat pour « ${escHtml(S.ofSearch)} »`:'Aucun OF importé')
    )
  );

  return h('div',{className:'card',style:{padding:'18px 20px'}},
    toolbar,
    renderPaginationBar(page,total,50,
      async()=>{if(page>0){set({ofPage:page-1});await loadOfImports();render();}},
      async()=>{if(page<Math.ceil(total/50)-1){set({ofPage:page+1});await loadOfImports();render();}}
    ),
    h('div',{style:{overflowX:'auto'}},
      h('table',{className:'table-std'},
        h('thead',null,h('tr',null,
          h('th',{style:{width:'36px'}},
            h('input',{type:'checkbox',style:'cursor:pointer',
              checked:(S.ofImports||[]).length>0&&(S.ofImports||[]).every(r=>S.ofSelected.has(r.id)),
              onChange:function(e){
                const ids=(S.ofImports||[]).map(r=>r.id);
                set({ofSelected:e.target.checked?new Set(ids):new Set()});render();
              }
            })
          ),
          h('th',null,'OF n°'),h('th',null,'Référence'),h('th',null,'Machine'),
          h('th',null,'Délai client'),h('th',null,'Qté étiquettes'),h('th',null,'Date création'),
          h('th',null,'Statut'),h('th',null,'Actions')
        )),
        h('tbody',null,...(rows.length?rows:[empty]))
      )
    ),
  );
}

function renderFichesTab(){
  const PAGE_SIZE=50;
  const total=S.ficheTotal||0;
  const page=S.fichePage||0;

  const toolbar=h('div',{style:{display:'flex',alignItems:'center',gap:'10px',marginBottom:'16px',flexWrap:'wrap'}},
    h('input',{
      id:'fiche-search-html',
      type:'text',
      placeholder:'Rechercher (référence, désignation, client…)',
      value:S.ficheSearch||'',
      style:'flex:1;min-width:200px;max-width:320px;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:9px 12px;color:var(--text);font-size:13px;font-family:inherit;outline:none',
      oninput:async function(e){
        const v=e.target.value;
        const ss=e.target.selectionStart,se=e.target.selectionEnd;
        set({ficheSearch:v,fichePage:0});
        await loadFiches();render();
        requestAnimationFrame(()=>{
          const el=document.getElementById('fiche-search-html');
          if(el){el.focus();try{el.setSelectionRange(ss,se);}catch(x){}}
        });
      },
      onkeydown:function(e){
        if(e.key==='Escape'){set({ficheSearch:'',fichePage:0});loadFiches().then(()=>render());e.target.value='';}
      },
    }),
    h('button',{
      style:'padding:9px 14px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text);cursor:pointer;font-size:13px;font-weight:600;white-space:nowrap',
      title:'Exporter toutes les fiches (filtre appliqué) en CSV',
      onClick:exportFichesCsv
    },iconEl('download',13),' Exporter CSV'),
    S.user&&S.user.role==='superadmin'&&S.ficheSelected.size>0
      ? h('button',{
          style:'padding:9px 14px;border-radius:8px;border:none;background:var(--danger);color:#fff;cursor:pointer;font-size:13px;font-weight:700;white-space:nowrap',
          onClick:async()=>{
            const n=S.ficheSelected.size;
            if(!confirm(`Supprimer ${n} fiche${n>1?'s':''} ?`)) return;
            try{
              await api('/api/fiches-techniques/bulk',{method:'DELETE',body:JSON.stringify({ids:[...S.ficheSelected]})});
              toast(`${n} fiche${n>1?'s':''} supprimée${n>1?'s':''}.`);
              set({ficheSelected:new Set()});
              await loadFiches();render();
            }catch(e){toast(e.message||'Erreur.','error');}
          }
        },iconEl('trash',13),` Supprimer (${S.ficheSelected.size})`)
      : null
  );

  const rows=(S.fiches||[]).map(row=>{
    const acts=[
      h('button',{
        style:'padding:4px 8px;border-radius:6px;border:1px solid var(--border);background:transparent;cursor:pointer',
        title:'Prévisualiser PDF',onClick:()=>window.open('/api/fiches-techniques/'+row.id+'/pdf-preview','_blank')
      },iconEl('file',13)),
      h('button',{
        style:'padding:4px 8px;border-radius:6px;border:1px solid var(--border);background:transparent;cursor:pointer',
        title:'Modifier',onClick:()=>openFicheEditModal(row)
      },iconEl('edit',13)),
    ];
    if(S.user&&S.user.role==='superadmin'){
      acts.push(h('button',{
        style:'padding:4px 8px;border-radius:6px;border:1px solid rgba(248,113,113,.3);background:transparent;cursor:pointer;color:var(--danger)',
        title:'Supprimer',
        onClick:async()=>{
          if(!confirm('Supprimer cette fiche ?')) return;
          try{await api('/api/fiches-techniques/'+row.id,{method:'DELETE'});toast('Fiche supprimée.');await loadFiches();render();}
          catch(e){toast(e.message||'Erreur.','error');}
        }
      },iconEl('trash',13)));
    }
    return h('tr',null,
      h('td',{style:{width:'36px'}},
        h('input',{type:'checkbox',checked:S.ficheSelected.has(row.id),style:'cursor:pointer',
          onChange:function(e){
            const sel=new Set(S.ficheSelected);
            if(e.target.checked)sel.add(row.id);else sel.delete(row.id);
            set({ficheSelected:sel});render();
          }
        })
      ),
      h('td',null,escHtml(row.reference||'—')),
      h('td',null,escHtml(row.format||'—')),
      h('td',null,row.eti_laize!=null?escHtml(String(row.eti_laize)+' mm'):'—'),
      h('td',null,escHtml(row.support||row.matiere||'—')),
      h('td',null,escHtml(row.machine||'—')),
      h('td',null,row.nb_couleurs!=null?escHtml(String(row.nb_couleurs)):'—'),
      h('td',null,escHtml(row.source||'—')),
      h('td',null,h('div',{style:{display:'flex',gap:'4px'}},...acts)),
    );
  });

  const empty=h('tr',null,
    h('td',{colSpan:'9',style:{textAlign:'center',color:'var(--muted)',padding:'24px'}},
      S.fichesLoading?'Chargement…':(S.ficheSearch?`Aucun résultat pour « ${escHtml(S.ficheSearch)} »`:'Aucune fiche technique importée')
    )
  );

  return h('div',{className:'card',style:{padding:'18px 20px'}},
    toolbar,
    renderPaginationBar(page,total,50,
      async()=>{if(page>0){set({fichePage:page-1});await loadFiches();render();}},
      async()=>{if(page<Math.ceil(total/50)-1){set({fichePage:page+1});await loadFiches();render();}}
    ),
    h('div',{style:{overflowX:'auto'}},
      h('table',{className:'table-std'},
        h('thead',null,h('tr',null,
          h('th',{style:{width:'36px'}},
            h('input',{type:'checkbox',style:'cursor:pointer',
              checked:(S.fiches||[]).length>0&&(S.fiches||[]).every(r=>S.ficheSelected.has(r.id)),
              onChange:function(e){
                const ids=(S.fiches||[]).map(r=>r.id);
                set({ficheSelected:e.target.checked?new Set(ids):new Set()});render();
              }
            })
          ),
          h('th',null,'Référence'),h('th',null,'Format'),h('th',null,'Laize eti.'),
          h('th',null,'Support'),h('th',null,'Machine'),h('th',null,'Nb coul.'),
          h('th',null,'Source'),h('th',null,'Actions')
        )),
        h('tbody',null,...(rows.length?rows:[empty]))
      )
    ),
  );
}

function renderOfPage(){
  const ambigusN = Number(S.pendingOfAmbigus || 0);
  const sansOfN  = Number(S.pendingOfSansOf  || 0);
  const pendingBadge = ambigusN > 0
    ? h('span',{style:'display:inline-block;margin-left:8px;padding:2px 8px;border-radius:10px;background:var(--danger);color:#fff;font-size:11px;font-weight:700;line-height:1.4'}, String(ambigusN))
    : null;
  const sansOfBadge = sansOfN > 0
    ? h('span',{style:'display:inline-block;margin-left:8px;padding:2px 8px;border-radius:10px;background:var(--danger);color:#fff;font-size:11px;font-weight:700;line-height:1.4'}, String(sansOfN))
    : null;
  const subNav=h('div',{style:{display:'flex',gap:'0',borderBottom:'1px solid var(--border)',marginBottom:'20px',flexWrap:'wrap'}},
    h('button',{
      style:`padding:10px 18px;font-size:13px;font-weight:600;border:none;background:transparent;cursor:pointer;border-bottom:2px solid ${S.ofSubTab==='of'?'var(--accent)':'transparent'};color:${S.ofSubTab==='of'?'var(--accent)':'var(--muted)'};font-family:inherit`,
      onClick:()=>{set({ofSubTab:'of'});render();}
    },'Ordres de fabrication'),
    h('button',{
      style:`padding:10px 18px;font-size:13px;font-weight:600;border:none;background:transparent;cursor:pointer;border-bottom:2px solid ${S.ofSubTab==='fiche'?'var(--accent)':'transparent'};color:${S.ofSubTab==='fiche'?'var(--accent)':'var(--muted)'};font-family:inherit`,
      onClick:async()=>{set({ofSubTab:'fiche'});await loadFiches();render();}
    },'Fiches techniques'),
    h('button',{
      style:`padding:10px 18px;font-size:13px;font-weight:600;border:none;background:transparent;cursor:pointer;border-bottom:2px solid ${S.ofSubTab==='pending'?'var(--accent)':'transparent'};color:${S.ofSubTab==='pending'?'var(--accent)':'var(--muted)'};font-family:inherit;display:inline-flex;align-items:center`,
      onClick:async()=>{set({ofSubTab:'pending'});await loadPendingOfMappings();render();}
    },'Mappings à valider', pendingBadge),
    h('button',{
      style:`padding:10px 18px;font-size:13px;font-weight:600;border:none;background:transparent;cursor:pointer;border-bottom:2px solid ${S.ofSubTab==='sansof'?'var(--accent)':'transparent'};color:${S.ofSubTab==='sansof'?'var(--accent)':'var(--muted)'};font-family:inherit;display:inline-flex;align-items:center`,
      onClick:async()=>{set({ofSubTab:'sansof'});await loadDossiersSansOf();render();}
    },'Dossiers sans OF', sansOfBadge),
  );
  return h('div',{style:{paddingLeft:'12px',paddingRight:'4px'}},
    subNav,
    S.ofSubTab==='fiche'   ? renderFichesTab()
      : S.ofSubTab==='pending' ? renderPendingOfMappingsTab()
      : S.ofSubTab==='sansof'  ? renderDossiersSansOfTab()
      : renderOfTab()
  );
}
function renderOfImportModal(){
  const m=S.ofImportModal;
  if(!m) return null;
  let body;
  if(m.parsing){
    body=h('div',{style:{display:'flex',alignItems:'center',justifyContent:'center',gap:10,padding:'40px',color:'var(--muted)'}},
      'Analyse du PDF…');
  }else if(m.step===1){
    const fileInput=h('input',{type:'file',accept:'.pdf,application/pdf',style:{display:'none'},id:'of-file-input'});
    const pickFile=()=>fileInput.click();
    fileInput.onchange=()=>{
      const f=fileInput.files&&fileInput.files[0];
      if(f) ofHandlePdfFile(f);
    };
    const dropzone=h('div',{className:'prod-of-dropzone',onClick:pickFile,
      onDragover:e=>{e.preventDefault();e.currentTarget.classList.add('prod-of-dropzone--active');},
      onDragleave:e=>{e.currentTarget.classList.remove('prod-of-dropzone--active');},
      onDrop:e=>{
        e.preventDefault();
        e.currentTarget.classList.remove('prod-of-dropzone--active');
        const f=e.dataTransfer&&e.dataTransfer.files&&e.dataTransfer.files[0];
        if(f) ofHandlePdfFile(f);
      }},
      iconEl('file',28),
      h('div',{className:'prod-of-dropzone-title'},'Déposer un PDF ici'),
      h('div',{className:'prod-of-dropzone-sub'},'ou cliquer pour sélectionner — .pdf uniquement')
    );
    body=h('div',null,fileInput,dropzone,
      h('div',{style:{marginTop:'14px',textAlign:'center'}},
        h('button',{className:'btn-ghost',onClick:pickFile},'Sélectionner un fichier')
      )
    );
  }else{
    const parsed=m.parsed||{};
    const previewRows=Object.keys(OF_FIELD_LABELS).map(k=>{
      const val=parsed[k];
      const missing=val==null||val==='';
      const display=val==null?'':String(val);
      return h('tr',{className:missing?'prod-of-missing':''},
        h('th',null,OF_FIELD_LABELS[k]),
        h('td',null,h('input',{type:'text',id:'of-f-'+k,value:display}))
      );
    });
    body=h('div',null,
      h('p',{className:'subtitle',style:{marginBottom:'8px'}},
        'Vérifiez les champs extraits. Les lignes surlignées indiquent une extraction manquante.'),
      h('table',{className:'prod-of-preview-table'},
        h('tbody',null,...previewRows)
      ),
      h('div',{className:'contact-modal-actions',style:{marginTop:'12px'}},
        h('button',{className:'btn-ghost',onClick:closeOfImportModal},'Annuler'),
        h('button',{className:'btn-sm',onClick:()=>ofValidateImport()},'Valider l\'import')
      )
    );
  }
  const overlay=h('div',{className:'contact-modal-overlay',onClick:e=>{
    if(e.target===e.currentTarget) closeOfImportModal();
  }});
  const box=h('div',{className:'contact-modal',style:{maxWidth:'720px',maxHeight:'88vh',overflowY:'auto'}},
    h('div',{className:'contact-modal-head'},
      h('h3',null,m.step===2?'Prévisualisation OF':'Importer un OF PDF'),
      h('button',{className:'contact-close-btn',onClick:closeOfImportModal},'×')
    ),
    h('div',{className:'contact-modal-body'},body)
  );
  overlay.appendChild(box);
  return overlay;
}


  // ────────────────────────────────────────────────────────────────────
  // ÉTAPE 2k — Onglet Traçabilité (matières + FSC)
  //
  // Code extrait littéralement de app/web/html.py (lignes 7989-8785) :
  //   - loadTracabilite / loadTracabiliteDossier
  //   - openFscRapportModal (rapport FSC dossier)
  //   - renderTracabilite (liste par machine)
  //   - closeTracMatieresEditModal / tracResolveMachineId
  //   - openTracMatieresEditModal (édition bobines matières)
  //   - renderTracabiliteDossierDetail (détail dossier)
  // ────────────────────────────────────────────────────────────────────

async function loadTracabilite(machineId){
  S.traceabilite = null; S.tracShowAttente = false; render();
  try{
    let url = '/api/fabrication/traceability';
    const params = [];
    if(machineId) params.push('machine_id='+machineId);
    if(params.length) url += '?'+params.join('&');
    const d = await api(url);
    S.traceabilite = d;
  }catch(e){ S.traceabilite = {error:e.message}; }
  render();
}

async function loadTracabiliteDossier(ref){
  S.traceabiliteDossier = null; render();
  try{
    // Charger les deux en parallèle : vue production + vue FSC
    const [d, fsc] = await Promise.all([
      api('/api/fabrication/traceability?no_dossier='+encodeURIComponent(ref)),
      api('/api/fabrication/tracabilite/'+encodeURIComponent(ref)),
    ]);
    const fscMap = {};
    (fsc && fsc.bobines ? fsc.bobines : []).forEach(b => {
      const key = String(b.code_barre||'').trim();
      if(key) fscMap[key] = b;
    });
    (d && d.matieres ? d.matieres : []).forEach(m => {
      const key = String(m.code_barre||'').trim();
      const b = fscMap[key];
      if(!b) return;
      if(b.fsc_conforme !== undefined) m.fsc_conforme = b.fsc_conforme;
      if(b.fsc_type_claim != null) m.fsc_type_claim = b.fsc_type_claim;
      if(b.fournisseur != null) m.fournisseur = b.fournisseur;
      if(b.certificat_fsc != null) m.certificat_fsc = b.certificat_fsc;
      if(b.fournisseur_licence != null) m.fournisseur_licence = b.fournisseur_licence;
      if(b.fournisseur_certificat != null) m.fournisseur_certificat = b.fournisseur_certificat;
    });
    d.fsc_synthese = (fsc && fsc.synthese) ? fsc.synthese : null;
    S.traceabiliteDossier = d;
  }catch(e){ S.traceabiliteDossier = {error:e.message}; }
  render();
}

function openFscRapportModal(data, ref){
  try{
    const syn = (data && data.synthese) ? data.synthese : {};
    const bobines = (data && data.bobines) ? data.bobines : [];
    const dos = (data && data.dossier) ? data.dossier : {};

    const sg = syn.statut_global || 'non_applicable';
    const statutColor = sg === 'conforme' ? 'var(--success)'
      : sg === 'non_conforme' ? 'var(--danger)' : 'var(--muted)';
    const statutBg = sg === 'conforme' ? 'rgba(52,211,153,.12)'
      : sg === 'non_conforme' ? 'rgba(248,113,113,.12)' : 'rgba(148,163,184,.12)';
    let statutText = 'Non applicable';
    if(sg === 'conforme'){
      statutText = 'Conforme FSC — ' + (syn.nb_bobines_fsc_conformes ?? 0) + '/' + (syn.nb_bobines_total ?? 0) + ' bobine(s)';
    }else if(sg === 'non_conforme'){
      statutText = 'Non conforme — ' + (syn.nb_bobines_non_conformes ?? 0) + ' bobine(s) en écart';
    }else if(sg === 'en_attente'){
      statutText = 'En attente — aucune bobine scannée';
    }else if((syn.nb_bobines_total ?? 0) === 0){
      statutText = 'Aucune bobine scannée';
    }

    const typeReq = dos.fsc_type_requis ? String(dos.fsc_type_requis) : '';
    const genAt = syn.genere_a ? String(syn.genere_a).replace('T',' ').slice(0,16) : '';

    const overlay = h('div',{className:'contact-modal-overlay',onClick:(e)=>{ if(e.target===e.currentTarget) overlay.remove(); }},
      h('div',{className:'contact-modal',onClick:(e)=>e.stopPropagation(),style:{maxWidth:'760px'}},
        h('div',{className:'contact-modal-head'},
          h('h3',null,'Rapport traçabilité FSC'),
          h('div',{style:{display:'flex',gap:'8px',flexShrink:0,flexWrap:'wrap'}},
            h('button',{className:'btn btn-sm btn-ghost',style:{fontSize:'12px'},onClick:()=>window.print()},'Exporter PDF'),
            h('button',{className:'btn btn-sm btn-ghost',style:{fontSize:'12px'},onClick:()=>overlay.remove()},'Fermer')
          )
        ),
        h('div',{style:{fontSize:'12px',color:'var(--muted)',marginTop:'-6px',marginBottom:'12px'}},
          (ref||'') + (dos.client ? (' — ' + dos.client) : '') + (typeReq ? (' · Requis : ' + typeReq) : '')
        ),
        h('div',{style:{padding:'10px 14px',borderRadius:'8px',marginBottom:'14px',fontWeight:'800',fontSize:'13px',
          background:statutBg,border:'1px solid '+statutColor,color:statutColor}}, statutText),
        h('div',{className:'table-wrap',style:{border:'1px solid var(--border)',borderRadius:'12px'}},
          h('table',{className:'table-std',style:{fontSize:'13px'}},
            h('thead',null,h('tr',null,
              h('th',null,'Code barre'),
              h('th',null,'Fournisseur'),
              h('th',null,'Claim FSC'),
              h('th',null,'Statut FSC'),
              h('th',null,'Scanné le')
            )),
            h('tbody',null,
              ...(bobines.length ? bobines.map(b=>{
                const claim = b.fsc_type_claim || 'Non FSC';
                const conf = b.fsc_conforme;
                const confCell = conf === true
                  ? h('span',{style:{color:'var(--success)',fontWeight:'800'}},'\u2713')
                  : conf === false
                    ? h('span',{style:{color:'var(--danger)',fontWeight:'800'}},'\u2717'+(b.fsc_warning?' (confirmé)':''))
                    : h('span',{style:{color:'var(--muted)'}},'\u2014');
                const scan = (b.scanned_at||'').slice(0,16).replace('T',' ');
                return h('tr',null,
                  h('td',null,h('span',{style:{fontFamily:'ui-monospace,monospace',fontWeight:'800'}},b.code_barre||'')),
                  h('td',null,b.fournisseur||'—'),
                  h('td',null,claim),
                  h('td',null,confCell),
                  h('td',{style:{fontSize:'11px',color:'var(--muted)'}},scan||'—'),
                );
              }) : [
                h('tr',null,h('td',{colSpan:'5',style:{padding:'20px',textAlign:'center',color:'var(--muted)',fontSize:'12px'}},
                  'Aucune bobine scannée sur ce dossier.'
                ))
              ])
            )
          )
        ),
        h('div',{style:{marginTop:'14px',paddingTop:'10px',borderTop:'1px solid var(--border)',fontSize:'11px',color:'var(--muted)'}},
          'Généré le ', genAt, ' · MySifa · SIFA'
        )
      )
    );
    document.body.appendChild(overlay);
  }catch(e){
    showToast('Rapport FSC indisponible.','danger');
  }
}

function renderTracabilite(){
  // Si on a un dossier sélectionné, afficher son détail
  if(S.traceabiliteDossier !== undefined && S.traceabiliteDossier !== null){
    return renderTracabiliteDossierDetail();
  }

  const d = S.traceabilite;
  if(!d) return h('div',{className:'card-empty'},'Chargement de la traçabilité…');
  if(d.error) return h('div',{className:'card'},h('div',{style:{padding:'20px',color:'var(--danger)'}},d.error));

  const allDossiers = d.dossiers||[];

  // ── Valeurs uniques pour les selects ───────────────────────────
  const machinesUniq = [...new Set(allDossiers.map(x=>x.machine_nom).filter(Boolean))].sort();
  const statuts = [
    {val:'',label:'Tous statuts'},
    {val:'attente',label:'En attente'},
    {val:'en_cours',label:'En cours'},
    {val:'termine',label:'Terminé'},
  ];

  // ── État filtres ────────────────────────────────────────────────
  if(!S.tracFilters) S.tracFilters={ref:'',client:'',machine:'',statut:''};
  if(!S.tracSort)    S.tracSort={col:null,dir:'asc'};
  const F = S.tracFilters;
  const Srt = S.tracSort;

  // ── Filtre ──────────────────────────────────────────────────────
  let dossiers = allDossiers.filter(dos=>{
    if(F.ref    && !(dos.reference||'').toLowerCase().includes(F.ref.toLowerCase()))    return false;
    if(F.client && !(dos.client||'').toLowerCase().includes(F.client.toLowerCase()))    return false;
    if(F.machine && dos.machine_nom !== F.machine) return false;
    if(F.statut  && dos.statut !== F.statut)       return false;
    return true;
  });

  // ── Tri / visibilité en attente ─────────────────────────────────
  const _tracPos = d=>{
    const p = Number(d && d.position);
    if(!isNaN(p)) return p;
    return Number(d && d.id) || 0;
  };
  const attenteDossiers = dossiers.filter(dos=>dos.statut==='attente');
  const mainDossiers = dossiers.filter(dos=>dos.statut!=='attente');
  const forceShowAttente = F.statut==='attente';
  const showAttente = forceShowAttente || !!S.tracShowAttente;
  const hiddenAttenteCount = (!showAttente && !F.statut) ? attenteDossiers.length : 0;

  const COL_KEY = {ref:'reference',client:'client',designation:'designation',machine:'machine_nom',statut:'statut',matieres:'nb_matieres'};
  if(Srt.col){
    const key = COL_KEY[Srt.col]||Srt.col;
    dossiers = [...dossiers].sort((a,b)=>{
      let av=a[key]||'', bv=b[key]||'';
      if(typeof av==='number'||typeof bv==='number'){av=Number(av)||0;bv=Number(bv)||0;}
      else{av=String(av).toLowerCase();bv=String(bv).toLowerCase();}
      return Srt.dir==='asc'?(av>bv?1:av<bv?-1:0):(av<bv?1:av>bv?-1:0);
    });
    if(!showAttente && !F.statut){
      dossiers = dossiers.filter(dos=>dos.statut!=='attente');
    }
  } else {
    const sortDescPos = (a,b)=>_tracPos(b)-_tracPos(a);
    const sortedAttente = [...attenteDossiers].sort(sortDescPos);
    const sortedMain = [...mainDossiers].sort(sortDescPos);
    dossiers = showAttente ? [...sortedAttente, ...sortedMain] : sortedMain;
  }

  // ── Pagination (sur la liste filtrée/triée) ─────────────────────
  const PAGE_SIZE = 50;
  if(S.tracPage == null) S.tracPage = 0;
  const totalFiltered = dossiers.length;
  const maxPage = Math.max(0, Math.ceil(totalFiltered / PAGE_SIZE) - 1);
  if(S.tracPage > maxPage) S.tracPage = maxPage;
  if(S.tracPage < 0) S.tracPage = 0;
  const pageStart = S.tracPage * PAGE_SIZE;
  const pageEnd = Math.min(pageStart + PAGE_SIZE, totalFiltered);
  const dossiersPage = dossiers.slice(pageStart, pageEnd);

  // ── Helper : badge statut ───────────────────────────────────────
  function statutBadge(st){
    if(st==='en_cours')  return h('span',{className:'badge',style:{color:'var(--success)',background:'rgba(52,211,153,.12)',display:'inline-flex',alignItems:'center',gap:'5px'}},
      h('span',{style:{width:'6px',height:'6px',borderRadius:'50%',background:'var(--success)',display:'inline-block',animation:'pulse 2s infinite'}}),
      'En cours');
    if(st==='termine')   return h('span',{className:'badge badge-ok'},'Terminé');
    return h('span',{className:'badge badge-warn'},'En attente');
  }

  // ── Header cliquable (tri) ──────────────────────────────────────
  function thSort(colKey, label){
    const active = Srt.col===colKey;
    const arrow  = active ? (Srt.dir==='asc'?'↑':'↓') : '';
    return h('th',{
      style:{cursor:'pointer',userSelect:'none',whiteSpace:'nowrap',color:active?'var(--accent)':''},
      onClick:()=>{
        S.tracPage = 0;
        if(Srt.col===colKey) S.tracSort={col:colKey,dir:Srt.dir==='asc'?'desc':'asc'};
        else S.tracSort={col:colKey,dir:'asc'};
        render();
      }
    }, label+(arrow?' '+arrow:''));
  }

  // ── Barre de filtres ────────────────────────────────────────────
  // Helper : input texte avec conservation du focus et position du curseur
  const filterInput = (inputId, label, val, onChange)=>{
    const inp = h('input',{
      type:'text', id:inputId, value:val, placeholder:'Rechercher…', className:'filter-input',
      autocomplete:'off', spellcheck:'false'
    });
    inp.addEventListener('input', e=>{
      const selStart = e.target.selectionStart;
      S.tracPage = 0;
      onChange(e.target.value);
      render();
      // Restaurer le focus et la position du curseur après le re-render
      const restored = document.getElementById(inputId);
      if(restored){ restored.focus(); try{restored.setSelectionRange(selStart,selStart);}catch(ex){} }
    });
    return h('div',{className:'filter-group'},
      h('label',null,label),
      inp
    );
  };
  const filterSelect = (inputId, label, options, val, onChange)=>{
    const sel = h('select',{id:inputId, className:'filter-input'},
      ...options.map(o=>h('option',{value:o.val,selected:val===o.val},o.label)));
    sel.addEventListener('change', e=>{ S.tracPage = 0; onChange(e.target.value); render(); });
    return h('div',{className:'filter-group'},
      h('label',null,label),
      sel
    );
  };
  const hasActiveFilter = !!(F.ref||F.client||F.machine||F.statut);

  const filterBar = h('div',{className:'filters-panel',style:{padding:'14px 20px',borderBottom:'1px solid var(--border)'}},
    h('div',{className:'filters'},
      filterInput('trac-f-ref',    'Référence',  F.ref,    v=>{S.tracFilters.ref=v;}),
      filterInput('trac-f-client', 'Client',     F.client, v=>{S.tracFilters.client=v;}),
      filterSelect('trac-f-machine','Machine',
        [{val:'',label:'Toutes machines'},...machinesUniq.map(m=>({val:m,label:m}))],
        F.machine, v=>{S.tracFilters.machine=v;}
      ),
      filterSelect('trac-f-statut','Statut', statuts, F.statut, v=>{S.tracFilters.statut=v;}),
      hasActiveFilter ? h('button',{
        className:'btn btn-sm btn-ghost',
        style:{alignSelf:'flex-end',marginTop:'0'},
        onClick:()=>{ S.tracFilters={ref:'',client:'',machine:'',statut:''}; S.tracShowAttente=false; S.tracPage=0; render(); }
      }, iconEl('x',14),' Effacer') : null
    )
  );

  // ── Lignes tableau ──────────────────────────────────────────────
  const rows = dossiersPage.map(dos=>{
    const hasMatieres = (dos.nb_matieres||0)>0;
    return h('tr',{style:{cursor:'pointer'},
      onClick:async()=>{
        S.traceabiliteDossier = null;
        render();
        await loadTracabiliteDossier(dos.reference);
      }
    },
      h('td',null, h('span',{style:{fontWeight:'800',color:'var(--accent)'}}, dos.reference||'—')),
      h('td',null, dos.client||'—'),
      h('td',null, dos.designation||'—'),
      h('td',null, dos.machine_nom||'—'),
      h('td', null,
        h('div', { style: { display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' } },
          statutBadge(dos.statut || 'attente'),
          (dos.fsc_requis === 1 || dos.fsc_requis === true)
            ? h('span', {
                title: 'Certification FSC requise — ' + (dos.fsc_type_requis || ''),
                style: {
                  background: 'var(--accent-bg)', color: 'var(--accent)',
                  fontSize: '10px', fontWeight: '700',
                  padding: '1px 6px', borderRadius: '4px',
                }
              }, 'FSC')
            : null
        )
      ),
      h('td',null,
        hasMatieres
          ? h('span',{className:'badge badge-ok'}, (dos.nb_matieres||0)+' bobine'+(dos.nb_matieres>1?'s':''))
          : h('span',{className:'badge',style:{opacity:.5}},'Aucune')
      )
    );
  });

  const attenteToggleBar = hiddenAttenteCount > 0
    ? h('div',{
        className:'show-trac-attente-btn',
        onClick:()=>{ S.tracPage=0; S.tracShowAttente=true; render(); }
      }, '▲ '+hiddenAttenteCount+' dossier'+(hiddenAttenteCount>1?'s':'')+' en attente masqué'+(hiddenAttenteCount>1?'s':'')+' — cliquer pour afficher')
    : (showAttente && !forceShowAttente && attenteDossiers.length > 0
      ? h('div',{
          className:'show-trac-attente-btn',
          onClick:()=>{ S.tracPage=0; S.tracShowAttente=false; render(); }
        }, '▼ Masquer les dossiers en attente')
      : null);

  const table = rows.length
    ? h('table',{className:'table-std'},
        h('thead',null,h('tr',null,
          thSort('ref','Référence'),
          thSort('client','Client'),
          thSort('designation','Désignation'),
          thSort('machine','Machine'),
          thSort('statut','Statut'),
          thSort('matieres','Matières')
        )),
        h('tbody',null,...rows)
      )
    : h('div',{className:'card-empty'},allDossiers.length?'Aucun résultat pour ces filtres':'Aucun dossier dans le planning');

  const matchingCount = attenteDossiers.length + mainDossiers.length;
  let badgeSuffix = '';
  if(hiddenAttenteCount > 0 && matchingCount !== totalFiltered){
    badgeSuffix = '/'+matchingCount;
  } else if(matchingCount !== allDossiers.length){
    badgeSuffix = '/'+allDossiers.length;
  }

  return h('div',{className:'card'},
    h('div',{className:'card-header'},
      h('h3',null,'Traçabilité par dossier'),
      h('div',{style:{display:'flex',alignItems:'center',gap:'10px',flexWrap:'wrap'}},
        h('span',{className:'badge'},
          totalFiltered + badgeSuffix + ' dossier' + (totalFiltered!==1?'s':'')
        ),
        totalFiltered > PAGE_SIZE
          ? h('div',{style:{display:'flex',alignItems:'center',gap:'8px'}},
              h('span',{style:{fontSize:'11px',color:'var(--muted)',fontFamily:'monospace'}},
                (pageStart+1)+'–'+pageEnd+' / '+totalFiltered
              ),
              h('button',{
                className:'btn btn-sm btn-ghost',
                disabled:S.tracPage<=0,
                style:{marginTop:'0',padding:'6px 10px'},
                onClick:()=>{ if(S.tracPage>0){ S.tracPage--; render(); } },
                title:'Précédent'
              }, '<'),
              h('button',{
                className:'btn btn-sm btn-ghost',
                disabled:S.tracPage>=maxPage,
                style:{marginTop:'0',padding:'6px 10px'},
                onClick:()=>{ if(S.tracPage<maxPage){ S.tracPage++; render(); } },
                title:'Suivant'
              }, '>')
            )
          : null
      )
    ),
    filterBar,
    attenteToggleBar,
    h('div',{style:{overflowX:'auto',padding:'0 0 8px'}}, table)
  );
}

function closeTracMatieresEditModal(){
  document.getElementById('trac-mat-edit-modal')?.remove();
}

function tracResolveMachineId(dos, matieres){
  const dmid = dos && dos.machine_id;
  if(dmid!=null && dmid!==''){
    const n = Number(dmid);
    return Number.isFinite(n) && n>0 ? n : null;
  }
  const m0 = (matieres||[]).find(x=>x.machine_id!=null && x.machine_id!=='');
  if(m0){
    const n = Number(m0.machine_id);
    return Number.isFinite(n) && n>0 ? n : null;
  }
  return null;
}

async function openTracMatieresEditModal(dos, matieres){
  closeTracMatieresEditModal();
  const ref = (dos.reference||'').trim();
  if(!ref){ showToast('Référence dossier manquante.','danger'); return; }

  let fournisseurs = [];
  try{
    const fd = await api('/api/fabrication/fournisseurs-fsc');
    fournisseurs = Array.isArray(fd) ? fd : (fd.fournisseurs||[]);
  }catch(e){ /* liste optionnelle */ }

  const rows = (matieres||[]).map(m=>{
    const mid = Number(m.id);
    const code = String(m.code_barre||'').trim();
    return {id: (Number.isFinite(mid) && mid > 0) ? mid : null, code, origCode: code, deleted:false};
  });
  const newRows = [];

  const overlay = document.createElement('div');
  overlay.id = 'trac-mat-edit-modal';
  overlay.className = 'contact-modal-overlay';
  overlay.style.zIndex = '9200';

  const box = document.createElement('div');
  box.className = 'contact-modal';
  box.style.maxWidth = '520px';
  box.onclick = (e)=> e.stopPropagation();

  const head = document.createElement('div');
  head.className = 'contact-modal-head';
  const title = document.createElement('h3');
  title.textContent = 'Bobines — '+ref;
  const closeBtn = document.createElement('button');
  closeBtn.className = 'contact-close-btn';
  closeBtn.textContent = '\u2715';
  closeBtn.onclick = closeTracMatieresEditModal;
  head.append(title, closeBtn);

  const body = document.createElement('div');
  body.className = 'contact-modal-body';
  body.style.display = 'grid';
  body.style.gap = '10px';

  const hint = document.createElement('p');
  hint.style.cssText = 'margin:0;font-size:12px;color:var(--muted);line-height:1.5';
  hint.textContent = 'Modifiez les codes barres ou ajoutez une bobine. Les lignes supprimées seront retirées du dossier.';
  body.appendChild(hint);

  const listWrap = document.createElement('div');
  listWrap.style.display = 'grid';
  listWrap.style.gap = '8px';

  const fournWrap = document.createElement('div');
  fournWrap.style.display = 'none';
  const fournLbl = document.createElement('label');
  fournLbl.style.cssText = 'font-size:10px;color:var(--muted);font-weight:700;letter-spacing:.4px;text-transform:uppercase;display:block;margin-bottom:6px';
  fournLbl.textContent = 'Fournisseur (liaison manuelle)';
  const fournSel = document.createElement('select');
  fournSel.className = 'form-sel';
  fournSel.style.width = '100%';
  fournSel.innerHTML = '<option value="">— Choisir —</option>' +
    fournisseurs.map(f=>'<option value="'+Number(f.id)+'">'+escapeHtml(f.nom||'')+'</option>').join('');
  fournWrap.append(fournLbl, fournSel);

  function mkCodeInput(val, placeholder){
    const inp = document.createElement('input');
    inp.type = 'text';
    inp.value = val||'';
    inp.placeholder = placeholder||'Code barre';
    inp.style.cssText = 'flex:1;min-width:0;padding:10px 12px;border-radius:10px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-family:monospace;font-size:13px';
    return inp;
  }

  function renderRows(){
    listWrap.innerHTML = '';
    rows.forEach((row, idx)=>{
      if(row.deleted) return;
      const line = document.createElement('div');
      line.style.cssText = 'display:flex;gap:8px;align-items:center';
      const inp = mkCodeInput(row.code, 'Code barre bobine');
      inp.addEventListener('input', ()=>{ row.code = inp.value; });
      const del = document.createElement('button');
      del.type = 'button';
      del.className = 'btn btn-sm btn-ghost';
      del.title = 'Supprimer';
      del.style.padding = '8px 10px';
      del.innerHTML = '';
      del.appendChild(iconEl('trash',14));
      del.onclick = ()=>{
        if(!confirm('Supprimer cette bobine du dossier ?')) return;
        row.deleted = true;
        renderRows();
      };
      line.append(inp, del);
      listWrap.appendChild(line);
    });
    newRows.forEach((row)=>{
      const line = document.createElement('div');
      line.style.cssText = 'display:flex;gap:8px;align-items:center';
      const inp = mkCodeInput(row.code, 'Nouveau code barre');
      inp.addEventListener('input', ()=>{ row.code = inp.value; });
      const del = document.createElement('button');
      del.type = 'button';
      del.className = 'btn btn-sm btn-ghost';
      del.title = 'Retirer';
      del.style.padding = '8px 10px';
      del.appendChild(iconEl('trash',14));
      del.onclick = ()=>{
        const i = newRows.indexOf(row);
        if(i>=0) newRows.splice(i,1);
        renderRows();
      };
      line.append(inp, del);
      listWrap.appendChild(line);
    });
    if(!rows.some(r=>!r.deleted) && !newRows.length){
      const empty = document.createElement('div');
      empty.style.cssText = 'font-size:12px;color:var(--muted);font-style:italic;padding:4px 0';
      empty.textContent = 'Aucune bobine — ajoutez-en une ci-dessous.';
      listWrap.appendChild(empty);
    }
  }
  renderRows();
  body.appendChild(listWrap);

  const addBtn = document.createElement('button');
  addBtn.type = 'button';
  addBtn.className = 'btn btn-sm btn-ghost';
  addBtn.style.justifySelf = 'start';
  addBtn.appendChild(iconEl('plus',14));
  addBtn.appendChild(document.createTextNode(' Ajouter une bobine'));
  addBtn.onclick = ()=>{ newRows.push({code:''}); renderRows(); };
  body.appendChild(addBtn);
  body.appendChild(fournWrap);

  const actions = document.createElement('div');
  actions.className = 'contact-modal-actions';
  const cancelBtn = document.createElement('button');
  cancelBtn.className = 'btn-ghost';
  cancelBtn.textContent = 'Annuler';
  cancelBtn.onclick = closeTracMatieresEditModal;
  const saveBtn = document.createElement('button');
  saveBtn.className = 'btn-sm';
  saveBtn.textContent = 'Enregistrer';
  saveBtn.onclick = async ()=>{
    const machineId = tracResolveMachineId(dos, matieres);

    const toDelete = rows.filter(r=>r.deleted && r.id).map(r=>r.id);
    const toPatch = rows.filter(r=>{
      if(r.deleted || !r.id) return false;
      const code = String(r.code||'').trim();
      if(!code) return false;
      return code !== String(r.origCode||'').trim();
    });
    const toAdd = [
      ...rows.filter(r=>!r.deleted && !r.id && (r.code||'').trim()).map(r=>(r.code||'').trim()),
      ...newRows.map(r=>(r.code||'').trim()).filter(Boolean),
    ];

    if(!toDelete.length && !toPatch.length && !toAdd.length){
      showToast('Aucune modification.','info');
      closeTracMatieresEditModal();
      return;
    }
    if(toAdd.length && !machineId){
      showToast('Machine du dossier introuvable — impossible d\'ajouter une bobine. Utilisez la saisie sur la machine ou renseignez la machine au planning.','danger');
      return;
    }

    const fid = fournSel.value ? Number(fournSel.value) : null;
    saveBtn.disabled = true;
    saveBtn.textContent = 'Enregistrement…';
    fournWrap.style.display = 'none';

    const postMatiere = async (code)=>{
      const body = {code_barre: code, no_dossier: ref, machine_id: machineId, tracabilite: true};
      if(fid) body.fournisseur_fsc_id = fid;
      try{
        await api('/api/fabrication/matieres', {
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify(body),
        });
      }catch(e){
        const msg = String((e && e.message) || '');
        if(msg.toLowerCase().includes('fournisseur requis')){
          fournWrap.style.display = 'block';
          showToast('Sélectionnez un fournisseur pour les codes non liés à une réception.','danger');
        }
        throw e;
      }
    };

    const patchMatiere = async (row)=>{
      const body = {code_barre: String(row.code||'').trim(), tracabilite: true};
      if(fid) body.fournisseur_fsc_id = fid;
      try{
        await api('/api/fabrication/matieres/'+row.id, {
          method:'PATCH',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify(body),
        });
      }catch(e){
        const msg = String((e && e.message) || '');
        if(msg.toLowerCase().includes('fournisseur requis')){
          fournWrap.style.display = 'block';
          showToast('Sélectionnez un fournisseur pour les codes non liés à une réception.','danger');
        }
        throw e;
      }
    };

    try{
      for(const id of toDelete){
        await api('/api/fabrication/matieres/'+id+'?tracabilite=1', {method:'DELETE'});
      }
      for(const row of toPatch){
        await patchMatiere(row);
      }
      for(const code of toAdd){
        await postMatiere(code);
      }
      closeTracMatieresEditModal();
      showToast('Bobines enregistrées.','success');
      await loadTracabiliteDossier(ref);
    }catch(e){
      if(!String((e&&e.message)||'').toLowerCase().includes('fournisseur requis')){
        showToast((e&&e.message)||'Enregistrement impossible.','danger');
      }
    }finally{
      saveBtn.disabled = false;
      saveBtn.textContent = 'Enregistrer';
    }
  };
  actions.append(cancelBtn, saveBtn);

  box.append(head, body, actions);
  overlay.appendChild(box);
  overlay.addEventListener('click', (e)=>{ if(e.target===overlay) closeTracMatieresEditModal(); });
  document.body.appendChild(overlay);
  requestAnimationFrame(()=>{
    const first = listWrap.querySelector('input');
    if(first) first.focus();
  });
}

function renderTracabiliteDossierDetail(){
  const d = S.traceabiliteDossier;

  const backBtn = h('button',{
    className:'btn btn-sm btn-ghost',
    style:{marginBottom:'12px'},
    onClick:()=>{ S.traceabiliteDossier=undefined; render(); }
  }, iconEl('arrow-left',14),' Retour');

  if(!d) return h('div',null, backBtn, h('div',{className:'card-empty'},'Chargement…'));
  if(d.error) return h('div',null, backBtn, h('div',{style:{color:'var(--danger)',padding:'20px'}},d.error));

  const dos = d.dossier||{};
  const matieres = d.matieres||[];
  const prod = d.production||[];
  const fscSyn = d.fsc_synthese || null;

  // Production summary
  const debutRow = prod.find(r=>r.operation_code==='01');
  const finRow   = prod.filter(r=>r.operation_code==='89').pop();
  const operateurs = [...new Set(prod.map(r=>r.operateur).filter(Boolean))];

  const metrageDebut = debutRow ? debutRow.metrage_prevu : null;
  const metrageFin   = finRow   ? finRow.metrage_reel : null;
  const metrageCalc  = (metrageDebut!=null&&metrageFin!=null) ? Math.max(0,metrageFin-metrageDebut) : null;
  const etiquettes   = finRow   ? finRow.quantite_traitee : null;

  const infoGrid = h('div',{style:{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(160px,1fr))',gap:'8px',margin:'12px 0'}},
    ...[
      {label:'Référence',  val:dos.reference||'—'},
      {label:'Client',     val:dos.client||'—'},
      {label:'Machine',    val:dos.machine_nom||dos.machine||'—'},
      {label:'Opérateur(s)', val:operateurs.join(', ')||'—'},
      {label:'Métrage produit', val:metrageCalc!=null ? fN(metrageCalc)+' m' : '—'},
      {label:'Étiquettes', val:etiquettes!=null ? fN(etiquettes) : '—'},
    ].map(item=>h('div',{style:{background:'var(--bg2)',borderRadius:'8px',padding:'10px 12px'}},
      h('div',{style:{fontSize:'10px',color:'var(--muted)',fontWeight:'700',textTransform:'uppercase',letterSpacing:'.4px',marginBottom:'3px'}},item.label),
      h('div',{style:{fontSize:'13px',fontWeight:'800',color:'var(--text)'}},item.val)
    ))
  );

  // Matières table
  const matiereRows = matieres.map(m=>{
    const dt = m.scanned_at ? new Date(m.scanned_at) : null;
    const dateStr = dt&&!isNaN(dt) ? dt.toLocaleDateString('fr-FR',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}) : '—';
    const claim = m.fsc_type_claim || 'Non FSC';
    const conf = m.fsc_conforme;
    const confCell = conf === true
      ? h('span',{style:{color:'var(--success)',fontWeight:'800'}},'\u2713')
      : conf === false
        ? h('span',{style:{color:'var(--danger)',fontWeight:'800'}},'\u2717'+(m.fsc_warning?' (confirmé)':''))
        : h('span',{style:{color:'var(--muted)'}},'\u2014');
    return h('tr',null,
      h('td',null,h('span',{style:{fontFamily:'monospace',fontWeight:'700',color:'var(--accent)'}},m.code_barre)),
      h('td',null,m.machine_nom||'—'),
      h('td',null,m.operateur||'—'),
      h('td',null,m.fournisseur||'—'),
      h('td',null,claim),
      h('td',null,confCell),
      h('td',null,dateStr)
    );
  });

  const matiereTable = matieres.length
    ? h('table',{className:'table-std'},
        h('thead',null,h('tr',null,
          h('th',null,'Code barre'),
          h('th',null,'Machine'),
          h('th',null,'Opérateur'),
          h('th',null,'Fournisseur'),
          h('th',null,'Claim FSC'),
          h('th',null,'Statut FSC'),
          h('th',null,'Heure scan')
        )),
        h('tbody',null,...matiereRows)
      )
    : h('div',{className:'card-empty',style:{padding:'16px'}},'Aucune bobine matière scannée pour ce dossier');

  const fscBanner = fscSyn ? (()=>{
    const sg = fscSyn.statut_global || 'non_applicable';
    const statutColor = sg === 'conforme' ? 'var(--success)'
      : sg === 'non_conforme' ? 'var(--danger)' : 'var(--muted)';
    const statutBg = sg === 'conforme' ? 'rgba(52,211,153,.12)'
      : sg === 'non_conforme' ? 'rgba(248,113,113,.12)' : 'rgba(148,163,184,.12)';
    let txt = 'Non applicable';
    if(sg === 'conforme'){
      txt = 'Conforme FSC — ' + (fscSyn.nb_bobines_fsc_conformes ?? 0) + '/' + (fscSyn.nb_bobines_total ?? 0) + ' bobine(s)';
    }else if(sg === 'non_conforme'){
      txt = 'Non conforme — ' + (fscSyn.nb_bobines_non_conformes ?? 0) + ' bobine(s) en écart';
    }else if(sg === 'en_attente'){
      txt = 'En attente — aucune bobine scannée';
    }else if((fscSyn.nb_bobines_total ?? 0) === 0){
      txt = 'Aucune bobine scannée';
    }
    return h('div',{style:{margin:'10px 0 0',padding:'10px 14px',borderRadius:'10px',
      background:statutBg,border:'1px solid '+statutColor,color:statutColor,fontWeight:'800',fontSize:'13px'}}, txt);
  })() : null;

  return h('div',null,
    backBtn,
    h('div',{className:'card'},
      h('div',{className:'card-header'},
        h('h3',null,dos.reference||'Dossier'),
        h('div',{style:{display:'flex',alignItems:'center',gap:'8px'}},
          h('span',{className:'badge badge-ok'},finRow?'Terminé':'En cours'),
          (dos.fsc_requis === 1 || dos.fsc_requis === true)
            ? h('button', {
                className: 'btn btn-sm',
                style: {
                  background: 'var(--accent-bg)', color: 'var(--accent)',
                  border: '1px solid var(--accent)', borderRadius: '6px',
                  fontSize: '12px', fontWeight: '700', padding: '4px 10px',
                  cursor: 'pointer',
                },
                onClick: async () => {
                  try {
                    const ref = dos.reference || '';
                    const data = await api('/api/fabrication/tracabilite/' + encodeURIComponent(ref));
                    if (!data) return;
                    openFscRapportModal(data, ref);
                  } catch(e) { showToast('Rapport FSC indisponible.', 'danger'); }
                }
              }, iconEl('file-text', 13), ' Rapport FSC')
            : null
        )
      ),
      infoGrid,
      h('div',{style:{padding:'0 20px 16px'}},
        h('div',{style:{display:'flex',alignItems:'center',justifyContent:'space-between',gap:'10px',marginBottom:'10px'}},
          h('div',{style:{fontWeight:'800',fontSize:'12px',color:'var(--text2)',
            textTransform:'uppercase',letterSpacing:'.4px',display:'flex',alignItems:'center',gap:'6px'}},
            iconEl('box',12),' Bobines matières utilisées ('+matieres.length+')'
          ),
          h('button',{
            type:'button',
            className:'btn btn-sm btn-ghost',
            title:'Modifier les bobines',
            'aria-label':'Modifier les bobines',
            style:{display:'inline-flex',alignItems:'center',gap:'6px',flexShrink:0},
            onClick:()=>openTracMatieresEditModal(dos, matieres)
          }, iconEl('sliders',14), ' Modifier')
        ),
        fscBanner,
        h('div',{style:{overflowX:'auto'}}, matiereTable)
      )
    )
  );
}

  // ────────────────────────────────────────────────────────────────────
  // ÉTAPE 2j — Onglets Dossiers + Suivi + Rentabilité
  //
  // Code extrait littéralement de app/web/html.py :
  //   - createDos / updStatut : l. 7154-7155
  //   - renderDos : l. 10403-10419
  //   - loadComparaison / uploadDevis / saveDevis / linkDossiers / deleteDevis : l. 11792-11838
  //   - renderDevisForm / renderComparaison / renderLiaisonDossiers : l. 11840-11982
  //   - renderRentabilite : l. 11986-12404
  //   - renderSuivi : l. 12407-12555
  // ────────────────────────────────────────────────────────────────────

async function createDos(d){try{await api('/api/dossiers',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});toast('Dossier créé');loadDos();}catch(e){toast(e.message,'error');}}
async function updStatut(id,s){try{await api('/api/dossiers/'+id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({statut:s})});loadDos();}catch{}}

function renderDos(){
  const inputs={};
  const form=h('div',{className:'card',style:{padding:'20px'}},h('h3',{style:{fontSize:'14px',fontWeight:'600',marginBottom:'16px'}},'Nouveau dossier'),
    h('div',{className:'form-grid'},...Object.entries({reference:'Référence *',client:'Client',description:'Description',devis_montant:'Montant devis (€)'}).map(([k,l])=>{const i=h('input',{placeholder:l,type:k==='devis_montant'?'number':'text'});inputs[k]=i;return i;})),
    h('button',{className:'btn',onClick:()=>{if(!inputs.reference.value)return;createDos({reference:inputs.reference.value,client:inputs.client.value,description:inputs.description.value,devis_montant:parseFloat(inputs.devis_montant.value)||0});Object.values(inputs).forEach(i=>i.value='');}},'Créer')
  );
  const sC={devis:'var(--c4)',en_cours:'var(--c1)',termine:'var(--c3)',annule:'var(--c5)'};const sL={devis:'Devis',en_cours:'En cours',termine:'Terminé',annule:'Annulé'};
  const list=h('div',{className:'card'},h('div',{className:'card-header'},h('h3',null,'Dossiers ('+S.dossiers.length+')')),
    S.dossiers.length===0?h('div',{className:'card-empty'},'Aucun dossier'):
    h('div',null,...S.dossiers.map(d=>{
      const sel=h('select',null,...Object.entries(sL).map(([k,v])=>{const o=h('option',{value:k},v);if(k===d.statut)o.selected=true;return o;}));
      sel.addEventListener('change',e=>updStatut(d.id,e.target.value));
      return h('div',{className:'dossier-row'},h('div',null,h('div',{style:{display:'flex',gap:'8px',alignItems:'center',marginBottom:'4px'}},h('span',{style:{fontFamily:'monospace',fontWeight:'600',fontSize:'14px'}},d.reference),h('span',{style:{fontSize:'11px',padding:'2px 10px',borderRadius:'20px',fontWeight:'600',background:(sC[d.statut]||'var(--muted)')+'22',color:sC[d.statut]||'var(--muted)'}},sL[d.statut]||d.statut)),h('div',{style:{fontSize:'13px',color:'var(--text2)'}},[d.client,d.description].filter(Boolean).join(' — '))),h('div',{style:{display:'flex',gap:'12px',alignItems:'center'}},d.devis_montant>0?h('span',{style:{fontFamily:'monospace',fontSize:'14px',color:'var(--success)',fontWeight:'600'}},d.devis_montant.toLocaleString()+' €'):null,sel));
    }))
  );
  return h('div',null,form,list);
}

async function loadComparaison(devisId){
  const d=await api('/api/rentabilite/devis/'+devisId+'/comparaison');
  if(d)set({comparaison:d});
}

async function uploadDevis(file){
  try{
    const fd=new FormData();fd.append('file',file);
    const r=await api('/api/rentabilite/devis/import',{method:'POST',body:fd});
    if(!r)return;
    if(r.parse_errors&&r.parse_errors.length){
      toast('Parsed avec avertissements : '+r.parse_errors[0],'warn');
    }
    set({devisPreview:r.preview,selDevis:null,comparaison:null});
  }catch(e){toast(e.message,'error');}
}

async function saveDevis(body){
  try{
    const r=await api('/api/rentabilite/devis',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!r)return;
    toast('Devis enregistré');
    set({devisPreview:null});
    await loadDevis();
  }catch(e){toast(e.message,'error');}
}

async function linkDossiers(devisId, dossiers){
  try{
    await api('/api/rentabilite/devis/'+devisId+'/dossiers',{method:'PUT',
      headers:{'Content-Type':'application/json'},body:JSON.stringify({dossiers})});
    toast('Dossiers liés');
    await loadDevis();
    await loadComparaison(devisId);
  }catch(e){toast(e.message,'error');}
}

async function deleteDevis(id){
  if(!confirm('Supprimer ce devis ?'))return;
  try{
    await api('/api/rentabilite/devis/'+id,{method:'DELETE'});
    toast('Devis supprimé');
    set({selDevis:null,comparaison:null});
    await loadDevis();
  }catch(e){toast(e.message,'error');}
}

function renderDevisForm(preview){
  const inputs={};
  const mkField=(label,key,type='text',val)=>{
    const i=h('input',{type,value:val!=null?String(val):''});
    inputs[key]=i;
    return h('div',{className:'field-item'},h('label',null,label),i);
  };

  return h('div',{className:'card',style:{padding:'24px'}},
    h('h3',{style:{fontSize:'16px',fontWeight:'700',marginBottom:'4px'}},'📋 Valider le devis importé'),
    h('p',{style:{fontSize:'12px',color:'var(--muted)',marginBottom:'20px'}},
      preview.filename+(((preview && preview.parse_errors && preview.parse_errors.length)?preview.parse_errors.length:0)?' — ⚠ '+preview.parse_errors.length+' avertissement(s)':' — Données extraites automatiquement')),

    h('div',{className:'form-section'},
      h('div',{className:'form-section-title'},'Informations générales'),
      h('div',{className:'field-row'},mkField('Client','client','text',preview.client),mkField('Date devis','date_devis','text',preview.date_devis)),
      h('div',{className:'field-row three'},
        mkField('Format H (mm)','format_h','number',preview.format_h),
        mkField('Format V (mm)','format_v','number',preview.format_v),
        mkField('Laize (mm)','laize','number',preview.laize)
      ),
    ),

    h('div',{className:'form-section'},
      h('div',{className:'form-section-title'},'Données théoriques de production'),
      h('div',{className:'field-row'},
        mkField('Temps calage (mn)','temps_calage_mn','number',preview.temps_calage_mn),
        mkField('Métrage calage (ml)','metrage_calage_ml','number',preview.metrage_calage_ml)
      ),
      h('div',{className:'field-row'},
        mkField('Temps production (mn)','temps_production_mn','number',preview.temps_production_mn),
        mkField('Métrage production (ml)','metrage_production_ml','number',preview.metrage_production_ml)
      ),
      h('div',{className:'field-row three'},
        mkField('Vitesse (m/mn)','vitesse_theorique','number',preview.vitesse_theorique),
        mkField('Qté étiquettes','qte_etiquettes','number',preview.qte_etiquettes),
        mkField('Gâche (%)','gache','number',preview.gache)
      ),
    ),

    h('div',{style:{display:'flex',gap:'10px',justifyContent:'flex-end',marginTop:'8px'}},
      h('button',{className:'btn-ghost',onClick:()=>set({devisPreview:null})},'Annuler'),
      h('button',{className:'btn-sm',onClick:()=>{
        const body={};
        Object.entries(inputs).forEach(([k,el])=>{
          body[k]=el.type==='number'?parseFloat(el.value)||0:el.value;
        });
        body.filename=preview.filename;
        saveDevis(body);
      }},'✓ Enregistrer le devis')
    )
  );
}

function renderComparaison(comp){
  if(!comp) return null;
  if(comp.message) return h('div',{className:'card-empty'},comp.message);

  const {theorique:th,reel:re,ecarts:ec,conclusion:co,devis:dv,dossiers}=comp;

  const ROWS=[
    {label:'⏱ Temps calage',     unit:'mn',  key:'temps_calage_mn', invert:true},
    {label:'▶ Temps production', unit:'mn',  key:'temps_production_mn', invert:true},
    {label:'📏 Métrage',         unit:'ml',  key:'metrage_ml'},
    {label:'🏷 Qté étiquettes',  unit:'ex',  key:'qte_etiquettes'},
    {label:'⚡ Vitesse',         unit:'m/mn',key:'vitesse'},
    {label:'⚡ Vitesse + calage',unit:'m/mn',key:'vitesse_avec_calage'},
  ];

  const fN2=v=>v!=null?Number(v).toLocaleString('fr-FR',{maximumFractionDigits:1}):'-';
  const ecartEl=(key,invert)=>{
    const v=ec[key];
    if(!v)return h('span',{className:'ecart-neu'},'—');
    const num=parseFloat(v);
    const good = invert ? num<0 : num>0;
    return h('span',{className:good?'ecart-pos':'ecart-neg'},v);
  };

  const colMap={success:'var(--success)',warn:'var(--warn)',danger:'var(--danger)'};
  const concl=h('div',{className:'conclusion-card',
    style:{borderColor:colMap[co.color]+'66',background:colMap[co.color]+'0D'}},
    h('div',null,
      h('div',{className:'conclusion-label',style:{color:colMap[co.color]}},co.label),
      h('div',{className:'conclusion-sub'},'Dossier'+(dossiers.length>1?'s':'')+' : '+dossiers.join(', '))
    )
  );

  const table=h('div',{style:{overflowX:'auto'}},
    h('table',{className:'compa-table'},
      h('thead',null,h('tr',null,
        h('th',null,'Indicateur'),
        h('th',null,'Unité'),
        h('th',null,'📋 Devis (théorique)'),
        h('th',null,'🏭 Réel'),
        h('th',null,'Écart'),
      )),
      h('tbody',null,...ROWS.map(row=>h('tr',null,
        h('td',{className:'compa-row-label'},row.label),
        h('td',{style:{color:'var(--muted)',fontSize:'11px'}},row.unit),
        h('td',{className:'compa-val-theo'},fN2(th[row.key])),
        h('td',{className:'compa-val-reel'},fN2(re[row.key])),
        h('td',null,ecartEl(row.key,row.invert||false)),
      )))
    )
  );

  return h('div',null,concl,
    h('div',{className:'card'},
      h('div',{className:'card-header'},
        h('h3',null,'Comparaison Devis / Réel'),
        h('span',{style:{fontSize:'11px',color:'var(--muted)'}},(dv.client||'')+' — '+(dv.filename||''))
      ),
      table
    )
  );
}

function renderLiaisonDossiers(devisId, dossiersLies, allDossiers){
  let current=[...dossiersLies];
  const wrap=h('div',null);
  const refresh=()=>{
    wrap.innerHTML='';
    const chips=h('div',{style:{marginBottom:'8px'}},
      ...current.map(d=>h('span',{className:'dos-chip'},
        'Dos. '+d,
        h('button',{onClick:()=>{current=current.filter(x=>x!==d);refresh();}},'×')
      ))
    );
    const sel=h('select',null,
      h('option',{value:''},'+ Ajouter un dossier'),
      ...allDossiers.filter(d=>!current.includes(d)).map(d=>h('option',{value:d},'Dos. '+d))
    );
    sel.addEventListener('change',()=>{
      if(sel.value&&!current.includes(sel.value)){
        current.push(sel.value);sel.value='';refresh();
      }
    });
    const saveBtn=h('button',{className:'btn-sm',onClick:()=>linkDossiers(devisId,current)},'💾 Enregistrer les liaisons');
    wrap.appendChild(h('div',null,chips,h('div',{className:'dos-add-row'},sel,saveBtn)));
  };
  refresh();
  return wrap;
}

function renderRentabilite(){
  const list = S.rentList || [];
  const devisList = S.devisList || [];

  const tags = Array.isArray(S.rentTags) ? S.rentTags : [];
  const q = String(S.rentQuery||'').trim().toLowerCase();

  function norm(x){return String(x||'').toLowerCase().trim();}
  function fmtFormat(e){
    const l=e.format_l!=null?String(e.format_l):'';
    const h=e.format_h!=null?String(e.format_h):'';
    if(!l&&!h) return '';
    return l+'×'+h;
  }

  // Suggestions (machines, clients, refs, format, laize, date)
  const pool=[];
  const pushSug=(kind,value,label)=>{
    if(!value) return;
    const k=kind+'|'+String(value);
    if(pool.some(x=>x._k===k)) return;
    pool.push({_k:k,kind,value,label});
  };
  list.forEach(e=>{
    pushSug('machine', e.machine_nom||e.machine_code, e.machine_nom||e.machine_code);
    if(e.reference) pushSug('ref', e.reference, e.reference);
    if(e.client) pushSug('client', e.client, e.client);
    const ff=fmtFormat(e); if(ff) pushSug('format', ff, 'Format '+ff);
    if(e.laize!=null && String(e.laize)!=='') pushSug('laize', String(e.laize), 'Laize '+String(e.laize));
    if(e.date_livraison) pushSug('date', e.date_livraison, 'Livraison '+e.date_livraison);
  });

  const kindLabel = {machine:'Machine',client:'Client',ref:'Dossier',format:'Format',laize:'Laize',date:'Date'};
  const kindOrder = {machine:0,client:1,ref:2,format:3,laize:4,date:5};
  const filteredSuggestions = q
    ? pool
        .filter(s=>norm(s.label).includes(q) || norm(s.value).includes(q))
        .sort((a,b)=>{
          const ka = (kindOrder[a.kind]!=null)?kindOrder[a.kind]:99;
          const kb = (kindOrder[b.kind]!=null)?kindOrder[b.kind]:99;
          if(ka!==kb) return ka-kb;
          return String(a.label||'').localeCompare(String(b.label||''), 'fr', {sensitivity:'base'});
        })
        .slice(0,12)
    : [];

  function addTag(sug){
    const exists = tags.some(t=>t.kind===sug.kind && String(t.value)===String(sug.value));
    if(exists) return;
    set({rentTags:[...tags,{kind:sug.kind,value:sug.value,label:sug.label}],rentQuery:'',rentOffset:0});
  }
  function removeTag(i){
    const nt=tags.slice(); nt.splice(i,1);
    set({rentTags:nt,rentOffset:0});
  }

  // Group split entries by group_id (same dossier). Display group row.
  const groups = {};
  list.forEach(e=>{
    const gid = String(e.group_id||e.id);
    if(!groups[gid]) groups[gid]=[];
    groups[gid].push(e);
  });
  const groupList = Object.entries(groups).map(([group_id, entries])=>{
    entries.sort((a,b)=>Number(a.position||0)-Number(b.position||0));
    const head=entries[0];
    return {group_id, entries, head};
  });

  function matchesTags(g){
    for(const t of tags){
      const head=g.head;
      if(t.kind==='machine'){
        const v = norm(head.machine_nom||head.machine_code);
        if(!v.includes(norm(t.value))) return false;
      }else if(t.kind==='ref'){
        if(!norm(head.reference).includes(norm(t.value))) return false;
      }else if(t.kind==='client'){
        const v = norm(head.client);
        if(!v.includes(norm(t.value))) return false;
      }else if(t.kind==='format'){
        if(norm(fmtFormat(head))!==norm(t.value)) return false;
      }else if(t.kind==='laize'){
        if(norm(String(head.laize||''))!==norm(String(t.value))) return false;
      }else if(t.kind==='date'){
        if(norm(head.date_livraison)!==norm(t.value)) return false;
      }
    }
    return true;
  }

  const shown = groupList.filter(matchesTags);
  const totalShown = shown.length;
  const lim = Number(S.rentLimit||12) || 12;
  const off = Math.max(0, Number(S.rentOffset||0) || 0);
  const pageStart = Math.min(totalShown, off);
  const pageEnd = Math.min(totalShown, off + lim);
  const shownPage = shown.slice(pageStart, pageEnd);

  const searchBox = (()=>{
    const wrap=h('div',{className:'card',style:{padding:'12px 14px',marginBottom:'14px'}});
    const row=h('div',{style:{display:'flex',gap:'10px',alignItems:'center',flexWrap:'wrap'}});
    const inp=h('input',{type:'text',placeholder:'Rechercher (machine, dossier, format, client, date, laize)…',value:S.rentQuery||'',style:{flex:'1',minWidth:'260px'}});
    inp.addEventListener('input',()=>set({rentQuery:inp.value}));
    const chips=h('div',{style:{display:'flex',gap:'8px',flexWrap:'wrap'}},
      ...tags.map((t,i)=>h('span',{className:'dos-chip',style:{display:'inline-flex',alignItems:'center',gap:'6px'}},
        t.label,
        h('button',{onClick:()=>removeTag(i)},'×')
      ))
    );
    row.appendChild(inp);
    wrap.appendChild(row);
    if(tags.length) wrap.appendChild(h('div',{style:{marginTop:'10px'}},chips));
    if(filteredSuggestions.length){
      const dd=h('div',{style:{marginTop:'10px',display:'flex',gap:'8px',flexWrap:'wrap'}},
        ...filteredSuggestions.map(s=>h('button',{type:'button',className:'btn-sec',onClick:()=>addTag(s)},
          (kindLabel[s.kind]? (kindLabel[s.kind]+' · ') : ''),
          s.label
        ))
      );
      wrap.appendChild(dd);
    }
    return wrap;
  })();

  function getLink(entryId){
    const m = (S.rentLinksById||{})[entryId];
    return m || {devis_id:null,no_dossiers:[]};
  }

  // In-flight de-duplication: évite de lancer 2x la même requête si ensureLinks est appelé
  // depuis le clic + le prefetch simultanément.
  if(!window._rentLinksPending) window._rentLinksPending = {};
  async function ensureLinks(entryId){
    const mp = S.rentLinksById || {};
    if(mp[entryId]) return mp[entryId];
    const key = String(entryId);
    if(window._rentLinksPending[key]) return window._rentLinksPending[key];
    const p = api('/api/rentabilite/links/'+entryId).then(d=>{
      delete window._rentLinksPending[key];
      const entry = {devis_id:d.devis_id||null,no_dossiers:d.no_dossiers||[]};
      S.rentLinksById = {...(S.rentLinksById||{}), [entryId]:entry};
      render();
      return entry;
    }).catch(e=>{
      delete window._rentLinksPending[key];
      throw e;
    });
    window._rentLinksPending[key] = p;
    return p;
  }

  async function saveLinks(entryId, devis_id, no_dossiers){
    await api('/api/rentabilite/links/'+entryId,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({devis_id,no_dossiers})});
    const mp = S.rentLinksById || {};
    set({rentLinksById:{...mp,[entryId]:{devis_id:devis_id||null,no_dossiers:no_dossiers||[]}}});
    toast('Liaisons enregistrées');
  }

  async function loadRentComparaison(entryId){
    const d = await api('/api/rentabilite/planning/'+entryId+'/comparaison');
    const mp = S.rentCompById || {};
    set({rentCompById:{...mp,[entryId]:d}});
  }

  async function rentSuggestNoDossiers(q){
    try{
      const qq=String(q||'').trim();
      if(!qq) return [];
      const d = await api('/api/rentabilite/no-dossiers?q='+encodeURIComponent(qq)+'&limit=12');
      return Array.isArray(d)?d:[];
    }catch(e){return [];}
  }

  function renderPanel(g){
    const head=g.head;
    const entryId = Number(head.id);
    const panel=h('div',{style:{borderLeft:'3px solid var(--accent)',background:'rgba(34,211,238,.04)',padding:'16px 20px',marginBottom:'2px'}});

    // Links editor
    const linkState = getLink(entryId);
    const curDevis = linkState.devis_id;
    let curDossiers = (linkState.no_dossiers||[]).slice();

    const devisSel=h('select',{className:'form-sel',style:{minWidth:'280px'}},
      h('option',{value:''},'Relier à un devis existant…'),
      ...devisList.map(dv=>{
        const opt=h('option',{value:String(dv.id)},(dv.client||dv.filename||('Devis #'+dv.id))+' (#'+dv.id+')');
        if(curDevis && Number(curDevis)===Number(dv.id)) opt.selected=true;
        return opt;
      })
    );
    devisSel.addEventListener('change',()=>{ /* local */ });

    const dosInput=h('input',{type:'text',placeholder:'Ajouter un n° dossier production (ex: 1003/0002)…',style:{minWidth:'260px'}});
    const dosSugWrap=h('div',{style:{display:'none',gap:'8px',flexWrap:'wrap'}});
    let dosSugToken=0;
    const refreshDosSug=async()=>{
      const v=String(dosInput.value||'').trim();
      const tok=++dosSugToken;
      if(v.length<2){ dosSugWrap.style.display='none'; dosSugWrap.innerHTML=''; return; }
      const sugs=await rentSuggestNoDossiers(v);
      if(tok!==dosSugToken) return;
      dosSugWrap.innerHTML='';
      if(!sugs.length){ dosSugWrap.style.display='none'; return; }
      dosSugWrap.style.display='flex';
      sugs.slice(0,8).forEach(s=>{
        dosSugWrap.appendChild(h('button',{type:'button',className:'btn-sec',onClick:()=>{
          const vv=String(s||'').trim();
          if(vv && !curDossiers.includes(vv)){curDossiers.push(vv);refreshChips();}
          dosInput.value='';
          dosSugWrap.style.display='none';
          dosSugWrap.innerHTML='';
        }},s));
      });
    };
    dosInput.addEventListener('input',()=>{ refreshDosSug(); });
    const addDosBtn=h('button',{type:'button',className:'btn-sec',onClick:()=>{
      const v=String(dosInput.value||'').trim();
      if(!v) return;
      if(!curDossiers.includes(v)){curDossiers.push(v);refreshChips();}
      dosInput.value='';
      dosSugWrap.style.display='none';
      dosSugWrap.innerHTML='';
    }},'+ Ajouter');

    const chipsWrap=h('div',{style:{display:'flex',gap:'8px',flexWrap:'wrap'}});
    const refreshChips=()=>{
      chipsWrap.innerHTML='';
      curDossiers.forEach((d,i)=>{
        chipsWrap.appendChild(h('span',{className:'dos-chip'},'Dos. '+d,h('button',{onClick:()=>{curDossiers.splice(i,1);refreshChips();}},'×')));
      });
    };
    refreshChips();

    // Auto-détection : si aucun dossier n'est lié, chercher dans la prod via la référence planning
    if(curDossiers.length===0 && (head.reference||'').trim()){
      queueMicrotask(async()=>{
        try{
          const sugs = await rentSuggestNoDossiers((head.reference||'').trim());
          if(sugs.length && curDossiers.length===0){
            sugs.forEach(s=>{ if(!curDossiers.includes(s)) curDossiers.push(s); });
            refreshChips();
          }
        }catch(_){}
      });
    }

    const saveBtn=h('button',{type:'button',className:'btn-sm',onClick:async()=>{
      const did = devisSel.value ? Number(devisSel.value) : null;
      await saveLinks(entryId, did, curDossiers);
      await loadRentComparaison(entryId).catch(()=>{});
    }},'💾 Enregistrer');

    const compBtn=h('button',{type:'button',className:'btn-sec',onClick:async()=>{
      await ensureLinks(entryId);
      await loadRentComparaison(entryId);
    }},'Comparer');

    // Import devis: keep existing workflow (creates devis + links via old devis_dossiers)
    // For v2, we still allow import, then we set rent_links.devis_id to the created devis.
    const dz=h('div',{className:'drop-zone',style:{padding:'20px',marginTop:'12px'}},
      h('div',{className:'dz-icon',style:{fontSize:'24px'}},'📄'),
      h('div',{className:'dz-title',style:{fontSize:'13px'}},'Importer un devis (Excel)'),
      h('div',{className:'dz-sub'},'Le devis pourra être lié à cette ligne rentabilité')
    );
    const dzInp=h('input',{type:'file',accept:'.xlsx,.xls',style:{display:'none'}});
    dzInp.addEventListener('change',async e=>{
      const f=(e && e.target && e.target.files && e.target.files[0]) ? e.target.files[0] : null;
      if(!f) return;
      try{
        const fd=new FormData();fd.append('file',f);
        const preview=await api('/api/rentabilite/devis/import',{method:'POST',body:fd});
        if(!preview||!preview.preview) return toast('Erreur import','error');
        const r=await api('/api/rentabilite/devis',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...preview.preview,filename:f.name})});
        if(!r||!r.devis_id) return toast('Erreur sauvegarde devis','error');
        // Link in rent_links
        await saveLinks(entryId, Number(r.devis_id), curDossiers);
        toast('Devis importé');
        await loadDevis();
        await loadRentComparaison(entryId).catch(()=>{});
      }catch(err){toast(err.message,'error');}
    });
    dz.addEventListener('click',()=>dzInp.click());
    dz.addEventListener('dragover',e=>{e.preventDefault();dz.classList.add('drag');});
    dz.addEventListener('dragleave',()=>dz.classList.remove('drag'));
    dz.addEventListener('drop',e=>{
      e.preventDefault();dz.classList.remove('drag');
      const f=(e && e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) ? e.dataTransfer.files[0] : null;
      if(!f) return;
      dzInp.files=e.dataTransfer.files;
      dzInp.dispatchEvent(new Event('change'));
    });
    panel.appendChild(h('div',{className:'form-section-title'},'🔗 Liaisons'));
    panel.appendChild(h('div',{style:{display:'flex',gap:'10px',flexWrap:'wrap',alignItems:'center'}},devisSel,dosInput,addDosBtn,saveBtn,compBtn));
    panel.appendChild(h('div',{style:{marginTop:'10px'}},dosSugWrap));
    panel.appendChild(h('div',{style:{marginTop:'10px'}},chipsWrap));
    panel.appendChild(dz);
    panel.appendChild(dzInp);

    const comp = (S.rentCompById||{})[entryId];
    if(comp){
      if(comp.reel) panel.appendChild(renderComparaison(comp));
      else panel.appendChild(h('div',{className:'card-empty',style:{padding:'18px'}},comp.message||'Aucune donnée.'));
    }else{
      panel.appendChild(h('div',{className:'card-empty',style:{padding:'18px'}},'Clique sur “Comparer” après avoir lié un devis + des dossiers production.'));
    }
    return panel;
  }

  const rows = shownPage.map(g=>{
    const head=g.head;
    const isExp = String(S.rentSelEntryId||'')===String(head.id);
    const topLine = [
      (head.client||'').trim(),
      (fmtFormat(head)?(fmtFormat(head)+' mm'):''),
      (head.reference||'').trim()
    ].filter(Boolean).join(' - ') || (head.reference||'(sans référence)');
    const subBits = [
      (head.machine_nom||'').trim(),
      (head.duree_heures!=null?('durée '+String(head.duree_heures)+'h'):''),
      (head.laize!=null?('laize '+head.laize):''),
      (head.date_livraison?('date '+head.date_livraison):'')
    ].filter(Boolean);

    const link = (S.rentLinksById||{})[Number(head.id)] || null;
    const devisLinked = link ? !!link.devis_id : null;
    const prodLinked = link ? ((link.no_dossiers||[]).length>0) : null;
    const stRaw = String(head.statut||'attente');
    const stLbl = (stRaw==='en_cours')?'En cours':(stRaw==='termine')?'Terminé':'En attente';
    const stCol = (stRaw==='termine')?'var(--success)':(stRaw==='en_cours')?'var(--warn)':'var(--muted)';
    const mkBadge=(txt, okNull, okCol, noCol)=>{
      const isOk = okNull===true;
      const isNo = okNull===false;
      const col = isOk?okCol:(isNo?noCol:'var(--muted)');
      const bg = isOk?(okCol+'1A'):(isNo?(noCol+'1A'):'rgba(100,116,139,.10)');
      return h('span',{style:{fontSize:'10px',fontWeight:'800',color:col,background:bg,border:'1px solid '+(col+'33'),padding:'3px 8px',borderRadius:'999px',whiteSpace:'nowrap'}},txt);
    };
    const row = h('div',{
      className:'dossier-row',
      style:{cursor:'pointer',background:isExp?'var(--accent-bg)':'',
             borderLeft:isExp?'3px solid var(--accent)':'3px solid transparent',
             transition:'all .15s'},
      onClick:async()=>{
        const next = isExp ? null : head.id;
        set({rentSelEntryId:next});
        if(next){
          await ensureLinks(Number(next)).catch(()=>{});
        }
      }
    },
      h('div',{style:{flex:'1',minWidth:0}},
        h('div',{style:{fontWeight:'700',color:'var(--text)',fontSize:'13px'}},topLine),
        h('div',{style:{fontSize:'11px',color:'var(--muted)',marginTop:'2px'}},
          subBits.length?subBits.join(' — '):'—')
      ),
      h('div',{style:{display:'flex',alignItems:'center',gap:'10px',flexShrink:0}},
        h('div',{style:{display:'flex',flexDirection:'column',alignItems:'flex-end',gap:'6px'}},
          mkBadge(stLbl, true, stCol, stCol),
          mkBadge(devisLinked===null?'Devis …':(devisLinked?'Devis lié':'Devis non lié'), devisLinked, 'var(--success)', 'var(--danger)'),
          (stRaw==='termine')
            ? mkBadge(prodLinked===null?'Prod …':(prodLinked?'Prod liée':'Prod non liée'), prodLinked, 'var(--success)', 'var(--danger)')
            : null
        ),
        h('span',{style:{fontSize:'14px',color:'var(--muted)',transition:'transform .15s',
          transform:isExp?'rotate(180deg)':'rotate(0deg)'}},'▾')
      )
    );
    if(!isExp) return row;
    return h('div',null,row,renderPanel(g));
  });

  // Précharger les liens avec une concurrence max de 3 pour ne pas saturer le navigateur.
  try{
    const CONCURRENCY = 3;
    const toFetch = shownPage
      .map(g=>Number(g.head&&g.head.id))
      .filter(id=>id && !(S.rentLinksById||{})[id] && !((window._rentLinksPending||{})[id]));
    if(toFetch.length){
      queueMicrotask(async()=>{
        let i = 0;
        async function runNext(){
          if(i >= toFetch.length) return;
          const id = toFetch[i++];
          await ensureLinks(id).catch(()=>{});
          await runNext();
        }
        const workers = Array.from({length:Math.min(CONCURRENCY,toFetch.length)},()=>runNext());
        await Promise.allSettled(workers);
      });
    }
  }catch(e){}

  const pager=h('div',{style:{display:'inline-flex',alignItems:'center',gap:'6px'}},
    h('button',{className:'btn-ghost',title:'Page précédente',disabled:off<=0,onClick:()=>{
      set({rentOffset:Math.max(0, off - lim)});
    }},'‹'),
    h('span',{style:{fontSize:'11px',color:'var(--muted)',fontFamily:'monospace'}},
      totalShown?(`${pageStart+1}-${pageEnd}/${totalShown}`):'0'
    ),
    h('button',{className:'btn-ghost',title:'Page suivante',disabled:(off+lim)>=totalShown,onClick:()=>{
      set({rentOffset:Math.min(Math.max(0,totalShown-lim), off + lim)});
    }},'›'),
  );

  return h('div',null,
    searchBox,
    h('div',{className:'card'},
      h('div',{className:'card-header'},
        h('h3',null,'Rentabilité — Dossiers planning ('+totalShown+')'),
        h('div',{style:{display:'flex',gap:'10px',alignItems:'center',flexWrap:'wrap'}},
          pager,
          h('button',{type:'button',className:'btn-sec',onClick:async()=>{await loadRentPlanning();toast('Planning rechargé');}},'Rafraîchir')
        )
      ),
      rows.length? h('div',null,...rows) : h('div',{className:'card-empty'},'Aucun dossier ne correspond aux filtres.')
    )
  );
}

function renderSuivi(){
  const admin = isAdmin(S.user);
  const dos = S.dossiers || [];
  const devisList = S.devisList || [];
  const parts = [];

  if(admin){
    const refI=h('input',{type:'text',placeholder:'Référence *',style:{width:'160px'}});
    const cliI=h('input',{type:'text',placeholder:'Client',style:{flex:'1'}});
    const desI=h('input',{type:'text',placeholder:'Description',style:{flex:'2'}});
    const btnC=h('button',{className:'btn-sm',onClick:()=>{
      if(!refI.value)return toast('Référence requise','error');
      createDos({reference:refI.value,client:cliI.value,description:desI.value});
      refI.value='';cliI.value='';desI.value='';
    }},'+ Nouveau dossier');
    parts.push(h('div',{className:'card',style:{padding:'16px',marginBottom:'16px'}},
      h('div',{className:'form-section-title'},'Nouveau dossier'),
      h('div',{style:{display:'flex',gap:'8px',flexWrap:'wrap',alignItems:'center'}},
        refI,cliI,desI,btnC)
    ));
  }

  if(!dos.length){
    parts.push(h('div',{className:'card-empty'},'Aucun dossier.'));
    return h('div',null,...parts);
  }

  const statMap={devis:'📋 Devis',en_cours:'▶ En cours',termine:'✅ Terminé',annule:'⛔ Annulé',archive:'🗄 Archivé'};
  const statChoices=['devis','en_cours','termine','archive','annule'];

  const rows = dos.map(d=>{
    const isExp = S.selDossier===d.id;
    const row = h('div',{
      className:'dossier-row',
      style:{cursor:'pointer',background:isExp?'var(--accent-bg)':'',
             borderLeft:isExp?'3px solid var(--accent)':'3px solid transparent',
             transition:'all .15s'},
      onClick:async()=>{
        if(isExp){set({selDossier:null,selDevis:null,comparaison:null});}
        else{set({selDossier:d.id,selDevis:null,comparaison:null});}
      }
    },
      h('div',{style:{flex:'1',minWidth:0}},
        h('div',{style:{fontWeight:'600',color:'var(--text)',fontSize:'13px'}},d.reference),
        h('div',{style:{fontSize:'11px',color:'var(--muted)',marginTop:'2px'}},
          [d.client,d.description].filter(Boolean).join(' — ')||'—')
      ),
      h('div',{style:{display:'flex',alignItems:'center',gap:'10px',flexShrink:0}},
        admin?h('select',{
          className:'form-sel',
          style:{fontSize:'11px',padding:'4px 8px'},
          onClick:e=>e.stopPropagation(),
          onChange:e=>{e.stopPropagation();updStatut(d.id,e.target.value);}
        },
          ...statChoices.map(s=>{
            const opt=h('option',{value:s},statMap[s]||s);
            if(d.statut===s)opt.selected=true;
            return opt;
          })
        ):h('span',{style:{fontSize:'11px',color:'var(--text2)'}},statMap[d.statut]||d.statut||''),
        h('span',{style:{fontSize:'14px',color:'var(--muted)',transition:'transform .15s',
          transform:isExp?'rotate(180deg)':'rotate(0deg)'}},'▾')
      )
    );

    if(!isExp) return row;

    const panel = h('div',{style:{
      borderLeft:'3px solid var(--accent)',background:'rgba(34,211,238,.04)',
      padding:'16px 20px',marginBottom:'2px'
    }});

    // Import devis (admin)
    if(admin){
      const dz=h('div',{className:'drop-zone',style:{padding:'20px',marginBottom:'12px'}},
        h('div',{className:'dz-icon',style:{fontSize:'24px'}},'📄'),
        h('div',{className:'dz-title',style:{fontSize:'13px'}},'Importer un devis (Excel)'),
        h('div',{className:'dz-sub'},'Le devis sera lié au dossier '+d.reference)
      );
      const dzInp=h('input',{type:'file',accept:'.xlsx,.xls',style:{display:'none'}});
      dzInp.addEventListener('change',async e=>{
        const f=(e && e.target && e.target.files && e.target.files[0]) ? e.target.files[0] : null;
        if(!f)return;
        try{
          const fd=new FormData();fd.append('file',f);
          const preview=await api('/api/rentabilite/devis/import',{method:'POST',body:fd});
          if(!preview||!preview.preview)return toast('Erreur import','error');
          const r=await api('/api/rentabilite/devis',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...preview.preview,filename:f.name})});
          if(!r||!r.devis_id)return toast('Erreur sauvegarde devis','error');
          await api('/api/rentabilite/devis/'+r.devis_id+'/dossiers',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({dossiers:[d.reference]})});
          toast('Devis importé et lié à '+d.reference);
          await loadDevis();
          await loadComparaison(r.devis_id);
          set({selDevis:r.devis_id});
        }catch(err){toast(err.message,'error');}
      });
      dz.addEventListener('click',()=>dzInp.click());
      dz.addEventListener('dragover',e=>{e.preventDefault();dz.classList.add('drag');});
      dz.addEventListener('dragleave',()=>dz.classList.remove('drag'));
      dz.addEventListener('drop',e=>{
        e.preventDefault();dz.classList.remove('drag');
        const f=(e && e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) ? e.dataTransfer.files[0] : null;
        if(!f)return;
        dzInp.files=e.dataTransfer.files;
        dzInp.dispatchEvent(new Event('change'));
      });
      panel.appendChild(dz);
      panel.appendChild(dzInp);
    }

    // Liaison manuelle à un devis existant
    const sel=h('select',{className:'form-sel',style:{minWidth:'280px'}},
      h('option',{value:''},'Lier un devis existant…'),
      ...devisList.map(dv=>h('option',{value:String(dv.id)},(dv.client||dv.filename||('Devis #'+dv.id))+' (#'+dv.id+')'))
    );
    const linkBtn=h('button',{className:'btn-sm',onClick:async()=>{
      const id=Number(sel.value||0);
      if(!id)return toast('Choisis un devis','warn');
      try{
        await api('/api/rentabilite/devis/'+id+'/dossiers',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({dossiers:[d.reference]})});
        toast('Devis lié à '+d.reference);
        await loadDevis();
        set({selDevis:id});
        await loadComparaison(id);
      }catch(e){toast(e.message,'error');}
    }},'🔗 Lier');
    panel.appendChild(h('div',{style:{display:'flex',gap:'10px',flexWrap:'wrap',alignItems:'center',marginBottom:'12px'}},sel,linkBtn));

    // Comparaison
    if(S.selDevis && S.comparaison){
      if(S.comparaison.reel) panel.appendChild(renderComparaison(S.comparaison));
      else panel.appendChild(h('div',{className:'card-empty',style:{padding:'18px'}},'📂 Aucune donnée de production correspondante pour ce dossier'));
      panel.appendChild(h('button',{className:'btn-danger',style:{marginTop:'10px'},onClick:()=>deleteDevis(S.selDevis)},'🗑 Supprimer ce devis'));
    } else {
      panel.appendChild(h('div',{className:'card-empty',style:{padding:'18px'}},'Liez/importez un devis pour afficher la comparaison.'));
    }

    return h('div',null,row,panel);
  });

  parts.push(h('div',{className:'card'},
    h('div',{className:'card-header'},
      h('h3',null,'Dossiers ('+dos.length+')')
    ),
    ...rows
  ));

  return h('div',null,...parts);
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
 
  // Sélect opération -- prod codes + stock codes EP/SP/EM/SM
  const STOCK_CODES_UI = [
    { code:'EP', label:'Entrée Z1 (produit fini)' },
    { code:'SP', label:'Sortie produit fini' },
    { code:'EM', label:'Entrée matière première' },
    { code:'SM', label:'Sortie matière première' },
  ];
  const opSel = h('select', null,
    h('option', { value: '' }, '— Choisir une opération —'),
    ...Object.entries(ops).map(([code, cfg]) => {
      const opt = h('option', { value: code+'           '+cfg.label }, code+' — '+cfg.label);
      if (prefill && prefill.operation && prefill.operation.startsWith(code)) opt.selected = true;
      return opt;
    }),
    h('option', { disabled: true, style:'font-weight:600;color:var(--muted);background:var(--bg)' }, '── Mouvements stock ──'),
    ...STOCK_CODES_UI.map(o => {
      const opt = h('option', { value: o.code+'           '+o.label }, o.code+' — '+o.label);
      if (prefill && prefill.operation_code === o.code) opt.selected = true;
      return opt;
    })
  );
  const opPreview = h('div', { className: 'op-preview' });
  let stockRefCache = { code:null, items:[] };
  async function refreshStockRefDatalist(code){
    if(!['EP','SP','EM','SM'].includes(code)) return;
    if(stockRefCache.code === code && stockRefCache.items.length) return;
    try{
      const endpoint = (code==='EP'||code==='SP') ? '/api/stock/produits?limit=300' : '/api/stock/matieres';
      const data = await api(endpoint);
      const items = Array.isArray(data) ? data : (data.rows||[]);
      stockDatalist.innerHTML = '';
      items.forEach(it => {
        const ref = it.reference || '';
        if(!ref) return;
        const opt = h('option', { value: ref }, ref + (it.designation ? ' — '+it.designation : ''));
        stockDatalist.appendChild(opt);
      });
      stockRefCache = { code, items };
    }catch(_){}
  }
  function updateFormForOp(){
    const raw = opSel.value || '';
    const code = raw.split(/\s+/)[0] || '';
    const isStock = ['EP','SP','EM','SM'].includes(code);
    const cfg = ops[code];
    // Preview label
    if(isStock){
      opPreview.textContent = '🟣 Mouvement stock';
    } else {
      opPreview.textContent = cfg
        ? (cfg.severity==='critique'?'🔴 Critique':cfg.severity==='attention'?'🟡 Attention':'🟢 '+cfg.category)
        : '';
    }
    // Toggle prod-only / stock-only rows
    const formEl = opSel.closest('.add-row-form');
    if(formEl){
      formEl.querySelectorAll('[data-role="prod-only"]').forEach(el=>{ el.style.display = isStock ? 'none' : ''; });
      formEl.querySelectorAll('[data-role="stock-only"]').forEach(el=>{ el.style.display = isStock ? '' : 'none'; });
    }
    // Defaults for stock
    if(isStock){
      if(code === 'EP' && !stockEmplacementInput.value) stockEmplacementInput.value = 'Z1';
      if(code !== 'EP' && stockEmplacementInput.value === 'Z1') stockEmplacementInput.value = '';
      refreshStockRefDatalist(code);
    }
  }
  opSel.addEventListener('change', updateFormForOp);
  // Init si prefill == stock code
  setTimeout(updateFormForOp, 0);
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

  // -- Stock EP/SP/EM/SM : inputs specifiques --
  const stockRefInput = h('input', { type:'text', placeholder:'Ref produit ou matiere', list:'stock-ref-datalist-'+Math.random().toString(36).slice(2,7) });
  const stockDatalistId = stockRefInput.getAttribute('list');
  const stockDatalist = h('datalist', { id: stockDatalistId });
  const stockEmplacementInput = h('input', { type:'text', placeholder:'ex: Z1', value:'' });
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
      h('div', { className: 'form-row', 'data-role':'stock-only', style:{display:'none'} },
        h('div', null,
          h('label', null, 'Référence produit / matière *'),
          stockRefInput,
          stockDatalist
        ),
        h('div', null,
          h('label', null, 'Emplacement'),
          stockEmplacementInput
        )
      ),
      h('div', { className: 'form-row' },
        h('div', null, h('label', null, 'Qté traitée'), qteTI),
        h('div', null, h('label', null, 'Note'), noteI)
      ),
      h('div', { className: 'form-row', 'data-role':'prod-only' },
        h('div', null,
          h('label', null, 'Métrage réel (m)'),
          metrageReelI
        )
      ),
      h('div', { className: 'form-row', 'data-role':'prod-only' },
        h('div', null,
          h('label', null, 'Compteur début (m)'),
          metrageDebutI
        ),
        h('div', null,
          h('label', null, 'Compteur fin (m)'),
          metrageFinI
        )
      ),
      h('div', { className: 'form-row', 'data-role':'prod-only' },
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
            const code = opVal.split(/\s+/)[0] || '';
            const dtVal = getDateVal();
            if(!dtVal){ toast('Heure invalide (format HH:MM:SS, 24h)', 'error'); return; }
            // ── Route stock EP/SP/EM/SM vers /api/fabrication/saisie-stock ──
            if(['EP','SP','EM','SM'].includes(code)){
              const stockRef = (stockRefInput.value||'').trim();
              const noDossier = (dosI.value||'').trim();
              const qte = parseFloat(qteTI.value) || 0;
              const empl = (stockEmplacementInput.value||'').trim();
              if(!stockRef){ toast('Reference produit / matiere requise','error'); return; }
              if(!noDossier){ toast('No dossier obligatoire pour un mouvement stock','error'); return; }
              if(qte <= 0){ toast('Quantite doit etre positive','error'); return; }
              const stockBody = {
                code, no_dossier: noDossier, quantite: qte,
                note: (noteI.value||'').trim() || null,
                date_operation: dtVal,
                machine: (machI.value||'').trim() || null,
              };
              if(code === 'EP' || code === 'SP'){
                stockBody.produit_reference = stockRef;
                stockBody.emplacement = empl || (code==='EP' ? 'Z1' : '');
              } else {
                stockBody.matiere_reference = stockRef;
                if(code === 'EM') stockBody.emplacement_dest = empl || null;
                else stockBody.emplacement_source = empl || null;
              }
              (async ()=>{
                try{
                  await api('/api/fabrication/saisie-stock', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(stockBody) });
                  toast('Saisie stock ajoutee');
                  closeModal();
                  await loadSaisies();
                }catch(e){ toast(e.message||'Erreur','error'); }
              })();
              return;
            }
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
 
// ── openEditStockModal : modal dedie EP/SP/EM/SM ────────────────
// Edite les champs surs (note, no_dossier, ref_bl) via PATCH
// /api/fabrication/saisie-stock/{kind}/{id}, ou supprime via DELETE.
// Les champs verrouilles (quantite, produit/matiere, emplacement, laize)
// necessitent supprimer + recreer.
function openEditStockModal(row){
  try{ const m=document.querySelector('.add-row-modal'); if(m) m.remove(); }catch(e){}
  const kind = row.kind; // stock_pf | stock_mp
  const code = row.operation_code || '';
  const codeLabel = ({EP:'Entree Z1',SP:'Sortie produit fini',EM:'Entree matiere',SP:'Sortie produit fini',SM:'Sortie matiere'})[code] || code;
  const isMP = (kind === 'stock_mp');

  const overlay = h('div',{className:'add-row-modal',style:{position:'fixed',inset:'0',background:'rgba(0,0,0,.5)',display:'flex',alignItems:'center',justifyContent:'center',zIndex:9999}});
  const box = h('div',{style:{background:'var(--card)',border:'1px solid var(--border)',borderRadius:'12px',padding:'22px',width:'min(560px,92vw)',maxHeight:'86vh',overflow:'auto',boxShadow:'0 12px 40px rgba(0,0,0,.35)'}});

  // Titre + badge lettres (meme teinte violet pastel pour tous les codes stock)
  const badgeColor = '#c4b5fd';
  const badgeBg = 'rgba(196,181,253,.22)';
  box.appendChild(h('div',{style:{display:'flex',alignItems:'center',gap:'10px',marginBottom:'6px'}},
    h('span',{style:{padding:'3px 10px',borderRadius:'8px',background:badgeBg,color:badgeColor,fontWeight:'700',fontFamily:'monospace',fontSize:'13px'}},code),
    h('h3',{style:{margin:0}},codeLabel)
  ));
  box.appendChild(h('div',{style:{color:'var(--muted)',fontSize:'12px',marginBottom:'16px'}},
    (row.produit_reference||row.matiere_reference||'') + ' · ' +
    (row.produit_designation||row.matiere_designation||'') + ' · qte ' + (row.quantite_traitee||0)
  ));

  // Champs editables
  const fields = [];
  function addField(label, key, placeholder=''){
    const wrap = h('div',{style:{marginBottom:'12px'}});
    wrap.appendChild(h('label',{style:{display:'block',fontSize:'11px',fontWeight:'600',color:'var(--muted)',textTransform:'uppercase',letterSpacing:'.5px',marginBottom:'4px'}}, label));
    const inp = h('input',{type:'text',value:row[key]||'',placeholder:placeholder,style:{width:'100%',padding:'10px 12px',border:'1px solid var(--border)',borderRadius:'8px',background:'var(--bg)',color:'var(--text)',fontSize:'13px'}});
    wrap.appendChild(inp);
    box.appendChild(wrap);
    fields.push({key, inp});
  }
  addField('Dossier (no_dossier)','no_dossier','ex: 26000123');
  if(isMP){
    addField('Ref BL','ref_bl','Bordereau de livraison');
  }
  addField('Note','note','');

  // Info fields non editables
  const lockedInfo = h('div',{style:{marginTop:'8px',padding:'10px 12px',background:'rgba(148,163,184,.06)',border:'1px solid var(--border)',borderRadius:'8px',fontSize:'12px',color:'var(--muted)',lineHeight:'1.6'}},
    'Quantite, ' + (isMP?'matiere, laize':'produit fini, emplacement') + ' non modifiables ici. Pour les changer : supprimer puis recreer.'
  );
  box.appendChild(lockedInfo);

  // Actions
  const actions = h('div',{style:{display:'flex',justifyContent:'space-between',alignItems:'center',marginTop:'20px',gap:'12px'}});
  const delBtn = h('button',{className:'btn-danger',style:{padding:'10px 16px',borderRadius:'8px',fontWeight:'600'}},'Supprimer');
  delBtn.addEventListener('click', async ()=>{
    if(!confirm('Supprimer cette saisie stock ? Le stock sera restaure a la valeur precedente.')) return;
    try{
      await api('/api/fabrication/saisie-stock/'+kind+'/'+row.id,{method:'DELETE'});
      toast('Saisie supprimee');
      overlay.remove();
      await loadSaisies();
    }catch(e){ toast(e.message||'Erreur suppression','danger'); }
  });
  const rightWrap = h('div',{style:{display:'flex',gap:'8px'}});
  const cancelBtn = h('button',{style:{padding:'10px 16px',borderRadius:'8px',background:'transparent',border:'1px solid var(--border)',color:'var(--text2)',cursor:'pointer'}},'Annuler');
  cancelBtn.addEventListener('click',()=>overlay.remove());
  const saveBtn = h('button',{className:'btn-accent',style:{padding:'10px 18px',borderRadius:'8px',fontWeight:'700'}},'Enregistrer');
  saveBtn.addEventListener('click', async ()=>{
    const body = {};
    fields.forEach(f=>{ const v=(f.inp.value||'').trim(); if(v!==String(row[f.key]||'')) body[f.key]=v||null; });
    if(Object.keys(body).length===0){ overlay.remove(); return; }
    try{
      await api('/api/fabrication/saisie-stock/'+kind+'/'+row.id,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
      toast('Saisie modifiee');
      overlay.remove();
      await loadSaisies();
    }catch(e){ toast(e.message||'Erreur','danger'); }
  });
  rightWrap.appendChild(cancelBtn);
  rightWrap.appendChild(saveBtn);
  actions.appendChild(delBtn);
  actions.appendChild(rightWrap);
  box.appendChild(actions);

  overlay.appendChild(box);
  overlay.addEventListener('click', e=>{ if(e.target===overlay) overlay.remove(); });
  document.getElementById('root').appendChild(overlay);
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
    } else if (row.kind === 'stock_pf' || row.kind === 'stock_mp' || cat === 'stock_pf' || cat === 'stock_mp') {
      rowBg = 'rgba(196,181,253,.22)';          // violet pastel mouvements stock (EP/SP/EM/SM)
    } else if (cat === 'production' || opCode === '03' || opCode === '88') {
      rowBg = 'rgba(52,211,153,.12)';           // vert production
    } else if (cat === 'personnel' || opCode === '86' || opCode === '87') {
      rowBg = 'rgba(167,139,250,.10)';          // violet discret arrivée/départ
    } else if (cat === 'calage' || opCode === '02') {
      rowBg = 'rgba(251,191,36,.08)';           // jaune doux calage
    }
    if (rowBg) tr.style.background = rowBg;
    if (S.selectedRows.has(row.id)) tr.style.background = 'rgba(34,211,238,.12)';
 
    if(!readOnly) tr.addEventListener('click',()=>{ if(row.kind==='stock_pf'||row.kind==='stock_mp') openEditStockModal(row); else openEditModal(row); });
 
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

function _datePresets(){
  const now = new Date();
  const fmt = (d) => {
    const y = d.getFullYear();
    const m = String(d.getMonth()+1).padStart(2,'0');
    const dd = String(d.getDate()).padStart(2,'0');
    return y + '-' + m + '-' + dd;
  };
  const today = new Date(now);
  const yesterday = new Date(now); yesterday.setDate(now.getDate()-1);
  const last7Start = new Date(now); last7Start.setDate(now.getDate()-6);
  const last30Start = new Date(now); last30Start.setDate(now.getDate()-29);
  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
  const prevMonthEnd = new Date(now.getFullYear(), now.getMonth(), 0);
  const prevMonthStart = new Date(now.getFullYear(), now.getMonth()-1, 1);
  return [
    {key:'today',     label:"Aujourd'hui",       from:fmt(today),         to:fmt(today)},
    {key:'yesterday', label:'Hier',              from:fmt(yesterday),     to:fmt(yesterday)},
    {key:'last7',     label:'7 derniers jours',  from:fmt(last7Start),    to:fmt(today)},
    {key:'last30',    label:'30 derniers jours', from:fmt(last30Start),   to:fmt(today)},
    {key:'thisMonth', label:'Mois en cours',     from:fmt(monthStart),    to:fmt(today)},
    {key:'prevMonth', label:'Mois dernier',      from:fmt(prevMonthStart),to:fmt(prevMonthEnd)},
  ];
}

function renderDatePresets(){
  const presets = _datePresets();
  const curFrom = S.fv.date_from || '';
  const curTo = S.fv.date_to || '';
  const presetChip = (p) => {
    const isActive = curFrom === p.from && curTo === p.to;
    return h('button',{
      type:'button',
      title:'Du '+p.from+' au '+p.to,
      style:{
        padding:'4px 10px',
        fontSize:'11px',
        fontWeight: isActive ? '700' : '600',
        borderRadius:'14px',
        border:'1px solid '+(isActive ? 'var(--accent)' : 'var(--border)'),
        background: isActive ? 'var(--accent-bg)' : 'transparent',
        color: isActive ? 'var(--accent)' : 'var(--text2)',
        cursor:'pointer',
        fontFamily:'inherit',
        whiteSpace:'nowrap',
        transition:'all 120ms',
      },
      onClick:()=>{
        S.fv.date_from = p.from;
        S.fv.date_to = p.to;
        applyF();
      },
    }, p.label);
  };
  return h('div',{
    className:'filters-date-presets',
    style:{display:'flex',gap:'6px',flexWrap:'wrap',alignItems:'center',padding:'8px 20px 4px',borderTop:'1px dashed var(--border)',marginTop:'4px'},
  },
    h('span',{style:{color:'var(--muted)',fontSize:'10px',textTransform:'uppercase',letterSpacing:'.6px',fontWeight:'700',marginRight:'4px'}},'Période :'),
    ...presets.map(presetChip),
  );
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
  const presetsRow = renderDatePresets();
  const chipsRow = viewAll ? renderDossierFilterChipsRow() : null;
  return h('div',{className:'filters-panel'},row,presetsRow,chipsRow||null);
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

// ── Détails sanity (liste par type) ──────────────────────────────
const SANITY_LABELS={
  jour_first_last:{label:"Arrivée personnel / Départ personnel"},
  jour_second_penult:{label:"Début de dossier / Fin de dossier"},
  jour_need_prod_cal_tech:{label:"Saisie vide"},
  jour_short_shift:{label:"Arrivée → Départ < 5h"},
  jour_arret_50:{label:"Arrêt machine (code 50)"},
  jour_missing_metrage:{label:"Métrage manquant (fin dossier)"},
  jour_missing_etiquettes:{label:"Nombre d’étiquettes manquant (fin dossier)"},
  jour_empty_dossier:{label:"Dossier vide (début → fin sans saisie)"},
};
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


// ── Helpers Repiquage / agregations Vue d'ensemble Production ────────
function _isRepMachine(m){
  if(!m) return false;
  let n = String(m).toLowerCase()
    .replace(/é/g,'e').replace(/è/g,'e').replace(/ê/g,'e').trim();
  return n === 'repiquage' || n === 'rep' || n.startsWith('rep ') || n.startsWith('repiquage');
}
function _prodAggBy(rows, keyName){
  const m = {};
  rows.forEach(r => {
    const k = String(r[keyName]==null?'':r[keyName]).trim();
    if(!k || k==='?') return;
    const x = m[k] = m[k] || {
      key: k, _dosSet: new Set(),
      etiquettes: 0, metrage_m: 0, cartons: 0,
      calage_min: 0, prod_min: 0, arret_min: 0,
    };
    const dos = String(r.no_dossier||'').trim();
    if(dos) x._dosSet.add(dos);
    x.etiquettes += Number(r.etiquettes||0);
    x.metrage_m += Number(r.metrage_m||0);
    x.cartons += Number(r.cartons||0);
    x.calage_min += Number(r.temps_calage_min||0);
    x.prod_min += Number(r.temps_prod_min||0);
    x.arret_min += Number(r.temps_arret_min||0);
  });
  return Object.values(m).map(v => {
    v.dossiers = v._dosSet.size; delete v._dosSet;
    const den = Math.round(v.prod_min) + Math.round(v.arret_min);
    v.vitesse_m_min = den>0 ? Number((v.metrage_m/den).toFixed(2)) : 0;
    v.etiquettes = Math.round(v.etiquettes*10)/10;
    v.metrage_m = Math.round(v.metrage_m*10)/10;
    return v;
  });
}
function _prodAggDossier(rows){
  const m = {};
  rows.forEach(r => {
    const k = String(r.no_dossier||'').trim();
    if(!k) return;
    const x = m[k] = m[k] || {
      no_dossier: k,
      client: '',
      etiquettes: 0, metrage_m: 0, cartons: 0,
      temps_calage_min: 0, temps_prod_min: 0, temps_arret_min: 0,
    };
    if(!x.client && r.client) x.client = r.client;
    x.etiquettes += Number(r.etiquettes||0);
    x.metrage_m += Number(r.metrage_m||0);
    x.cartons += Number(r.cartons||0);
    x.temps_calage_min += Number(r.temps_calage_min||0);
    x.temps_prod_min += Number(r.temps_prod_min||0);
    x.temps_arret_min += Number(r.temps_arret_min||0);
  });
  return Object.values(m).sort((a,b)=>String(a.no_dossier).localeCompare(
    String(b.no_dossier),'fr',{numeric:true,sensitivity:'base'}));
}
function _repHighlightDay(key, on){
  if(!key) return;
  document.querySelectorAll('tr.rep-hier-day').forEach(el => {
    if(el.getAttribute('data-team-jour') === key){
      el.style.background = on ? 'var(--accent-bg)' : '';
      el.querySelectorAll('td').forEach(td => {
        td.style.color = on ? 'var(--accent)' : '';
      });
    }
  });
  document.querySelectorAll('circle.rep-chart-point').forEach(el => {
    if(el.getAttribute('data-team-jour') === key){
      if(on){
        el.setAttribute('r', '6');
        el.setAttribute('stroke-width', '2.5');
      }else{
        el.setAttribute('r', '3.5');
        el.setAttribute('stroke-width', '1.5');
      }
    }
  });
}
function _repHighlightTeam(team, on){
  if(!team) return;
  document.querySelectorAll('tr.rep-hier-team').forEach(el => {
    if(el.getAttribute('data-team') === team){
      el.style.background = on ? 'var(--accent-bg)' : '';
    }
  });
  document.querySelectorAll('polyline.rep-chart-line').forEach(el => {
    if(el.getAttribute('data-team') === team){
      el.setAttribute('stroke-width', on ? '3.5' : '2');
      el.setAttribute('opacity', on ? '1' : '0.95');
    }
  });
  document.querySelectorAll('circle.rep-chart-point').forEach(el => {
    if(el.getAttribute('data-team') === team){
      el.setAttribute('r', on ? '5' : '3.5');
    }
  });
}

function _prodSynthTabGet(hasRep, onlyRep){
  if(onlyRep) return 'repiquage';
  if(!hasRep) return 'machines';
  try{
    const v = localStorage.getItem('mysifa.prod.synthtab');
    if(v === 'repiquage' || v === 'machines') return v;
  }catch(e){}
  return 'machines';
}
function _prodSynthTabSet(v){
  try{ localStorage.setItem('mysifa.prod.synthtab', v); }catch(e){}
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
  function mkCardDsi(){
    const m = ms && ms.DSI;
    const label = (m && m.statut_label) || 'En cours de développement';
    return h('div',{className:'mst-card mst-en_dev',style:{opacity:.7}},
      h('div',{className:'mst-head'},
        h('span',{className:'mst-nom'},'DSI'),
      ),
      h('div',{className:'mst-body'},
        h('div',{className:'mst-statut',style:{color:'var(--muted)',fontStyle:'italic'}},
          '\u2699 ', label)
      )
    );
  }
  function mkCardRepiquage(){
    const m = ms && ms.REP;
    const dossiers = (m && m.dossiers_du_jour) || [];
    const total = m ? Number(m.total_cartons||0) : 0;
    const isOn = dossiers.length > 0;
    const sk = isOn ? 'production' : 'eteinte';
    const fmtNumR = n => Number(n||0).toLocaleString('fr-FR');
    // Repliage mobile : >6 dossiers → on en cache une partie derriere
    // un bouton "+ N autres" (etat memorise par carte le temps de la session).
    const isMobileRep = window.innerWidth <= 700;
    const FOLD_LIMIT = 6;
    if(typeof window._repCardExpanded === 'undefined') window._repCardExpanded = false;
    const expanded = !isMobileRep || !!window._repCardExpanded;
    const visible = (!isMobileRep || expanded) ? dossiers.slice(0,10) : dossiers.slice(0, FOLD_LIMIT);
    const hidden = (!isMobileRep || expanded) ? 0 : Math.max(0, dossiers.slice(0,10).length - FOLD_LIMIT);
    // Reutilise les classes CSS mst-dos / mst-dos-ref / mst-dos-cli / mst-dos-des
    // pour rester coherent avec Cohesio 1 et 2.
    const dossierBlocks = dossiers.length
      ? visible.map(d => h('div',{className:'mst-dos',style:{position:'relative',paddingRight:'90px'}},
          h('div',{className:'mst-dos-ref'},
            h('span',null,'Dossier #'), d.no_dossier||'—'),
          d.client ? h('div',{className:'mst-dos-cli'}, d.client) : null,
          d.designation ? h('div',{className:'mst-dos-des'}, d.designation) : null,
          h('div',{
            style:{
              position:'absolute', top:'10px', right:'12px',
              fontFamily:'monospace', fontWeight:'800',
              color:'var(--accent)', fontSize:'13px', whiteSpace:'nowrap',
            }
          }, fmtNumR(d.cartons)+' carton'+(Math.abs(d.cartons)>1?'s':'')),
        ))
      : [h('div',{style:{padding:'8px 0',fontSize:'11px',color:'var(--muted)',fontStyle:'italic'}}, 'Aucune saisie aujourd’hui')];
    if(hidden > 0){
      dossierBlocks.push(h('button',{
        type:'button',
        className:'btn-ghost',
        style:{marginTop:'4px',fontSize:'11px',padding:'4px 10px',alignSelf:'flex-start'},
        onClick:(e)=>{e.stopPropagation(); window._repCardExpanded=true; render();},
      }, '+ '+hidden+' autre'+(hidden>1?'s':'')));
    }
    // Masquer la ligne 'Aujourd’hui' si un seul dossier (redondant)
    const showTotalRow = dossiers.length > 1;
    return h('div',{className:`mst-card mst-${sk}`},
      h('div',{className:'mst-head'},
        h('span',{className:'mst-nom'},'Atelier Repiquage — aujourd’hui'),
        h('div',{style:{display:'flex',alignItems:'center',gap:'6px'}},
          isOn?h('span',{style:{fontSize:'8px',color:'#22c55e',animation:'pulse 2s infinite',display:'inline-block',borderRadius:'50%',width:'8px',height:'8px',background:'#22c55e'}}):null,
          h('span',{className:'mst-dot'})
        )
      ),
      h('div',{className:'mst-body',style:{display:'flex',flexDirection:'column',gap:'8px'}},
        showTotalRow ? h('div',{style:{display:'flex',justifyContent:'space-between',alignItems:'baseline'}},
          h('span',{style:{fontSize:'11px',color:'var(--muted)',textTransform:'uppercase',letterSpacing:'.5px',fontWeight:'700'}}, 'Aujourd’hui'),
          h('span',{style:{fontFamily:'monospace',fontWeight:'800',color:'var(--accent)'}}, fmtNumR(total)+' cartons')
        ) : null,
        ...dossierBlocks,
        !ms?h('div',{style:{fontSize:'11px',color:'var(--muted)'}},'Chargement…'):null
      )
    );
  }
  const titleNode = h('span',{className:'section-title',style:{display:'inline-flex',alignItems:'center',gap:'4px',margin:0,padding:0,border:'none',flex:'1'}},
    iconEl('cpu',13),' Statut machines',
    h('span',{
      style:{marginLeft:'auto',display:'inline-flex',gap:'8px'},
    },
      h('button',{
        type:'button',
        id:'mst-refresh-btn',
        style:{fontSize:'10px',color:'var(--accent)',background:'none',border:'none',cursor:'pointer',padding:'2px 6px',fontFamily:'inherit'},
        onClick:async(e)=>{
          e.stopPropagation();
          const btn=document.getElementById('mst-refresh-btn');
          if(btn){btn.textContent='↺ Actualisation…';btn.disabled=true;}
          await loadMachineStatus();
          if(btn){btn.textContent='↺ Actualiser';btn.disabled=false;}
        }
      },'↺ Actualiser')
    )
  );
  const contentNode = h('div',null,
    h('div',{className:'mst-grid'},
      mkCard('C1'),
      mkCard('C2')
    ),
    h('div',{className:'mst-grid',style:{marginTop:'12px'}},
      mkCardDsi(),
      mkCardRepiquage()
    )
  );
  return makeCollapsibleSection(titleNode, contentNode, 'machines', true);
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
async function loadWeeklyReport(opts){
  // Charge le rapport hebdomadaire (semaine ISO précédente par défaut).
  // opts = {year, week, role}
  const q = [];
  if(opts && opts.year)  q.push('year=' +encodeURIComponent(opts.year));
  if(opts && opts.week)  q.push('week=' +encodeURIComponent(opts.week));
  if(opts && opts.role)  q.push('role=' +encodeURIComponent(opts.role));
  const qs = q.length ? ('?'+q.join('&')) : '';
  const d = await api('/api/reports/weekly/preview'+qs);
  if(d){
    S.weeklyReport = {
      html: d.html || '',
      data: d.data || null,
      role: d.role || (opts&&opts.role) || 'superadmin',
      year: (d.data&&d.data.week&&d.data.week.year) || (opts&&opts.year) || null,
      week: (d.data&&d.data.week&&d.data.week.num)  || (opts&&opts.week) || null,
      loading: false,
    };
  }
}
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
  let subPage = S.subPage || 'kpis';
  // Rôle « commercial » : pas d'accès à la vue Erreurs & Qualité
  const hideErreurs = isCommercial(S.user);
  if(hideErreurs && subPage==='erreurs'){ subPage = 'kpis'; S.subPage = 'kpis'; }
  // Gestion du polling temps réel machines
  if(subPage==='kpis'){startMachineStatusPolling();}
  else{stopMachineStatusPolling();}
  const allTabs = [
    {key:'kpis',    label:"Vue d'ensemble", icon:'wrench'},
    {key:'saisies', label:'Saisies', icon:'pencil'},
    {key:'erreurs', label:'Erreurs & Qualité', icon:'alert-triangle'},
  ];
  // V1 : onglet Rapport hebdo réservé au super admin (phase de test).
  const isSuper = !!(S.user && String(S.user.role||'').toLowerCase()==='superadmin');
  if(isSuper){
    allTabs.push({key:'rapport', label:'Rapport hebdo', icon:'bar-chart-2'});
  }
  const tabs = hideErreurs ? allTabs.filter(t=>t.key!=='erreurs') : allTabs;
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
        if(t.key==='rapport'&&!S.weeklyReport) await loadWeeklyReport();
        render();
      }
    }, iconEl(t.icon,14),' '+t.label))
  );
  let content;
  if(subPage==='saisies')  content = renderSaisiesWithImport();
  else if(subPage==='erreurs' && !hideErreurs) content = renderHist();
  else if(subPage==='rapport') content = renderWeeklyReport();
  else content = renderProdKpis();
  return h('div',null, subNav, content);
}

// ── Rapport hebdomadaire ────────────────────────────────────────
function renderWeeklyReport(){
  const wr = S.weeklyReport;
  if(!wr){
    return h('div',{className:'card-empty'},'Chargement du rapport hebdomadaire...');
  }
  const isSuper = !!(S.user && String(S.user.role||'').toLowerCase()==='superadmin');
  const weekVal = (wr.year && wr.week)
    ? (wr.year + '-W' + String(wr.week).padStart(2,'0'))
    : '';
  const roles = ['superadmin','direction','administration','administration_ventes','administration_technique','fabrication','logistique','comptabilite','expedition','commercial'];
  const changeWeek = async (e)=>{
    const v = (e && e.target && e.target.value) || '';
    const m = /^(\d{4})-W(\d{1,2})$/.exec(v);
    if(!m) return;
    S.weeklyReport = null; render();
    await loadWeeklyReport({ year:parseInt(m[1],10), week:parseInt(m[2],10), role: wr.role });
    render();
  };
  const changeRole = async (e)=>{
    const role = (e && e.target && e.target.value) || wr.role;
    S.weeklyReport = null; render();
    await loadWeeklyReport({ year: wr.year, week: wr.week, role });
    render();
  };
  const toolbar = h('div',{style:{display:'flex',gap:'12px',flexWrap:'wrap',alignItems:'center',margin:'0 0 14px'}},
    h('label',{style:{fontSize:'11px',fontWeight:'700',color:'var(--muted)',textTransform:'uppercase',letterSpacing:'.5px'}},'Semaine'),
    h('input',{
      type:'week',
      defaultValue: weekVal,
      onChange: changeWeek,
      style:{background:'var(--bg)',border:'1px solid var(--border)',borderRadius:'8px',padding:'6px 10px',color:'var(--text)',fontSize:'13px',fontFamily:'inherit'}
    }),
    ...(isSuper ? [
      h('label',{style:{fontSize:'11px',fontWeight:'700',color:'var(--muted)',textTransform:'uppercase',letterSpacing:'.5px',marginLeft:'8px'}},'Vue'),
      h('select',{
        value: wr.role,
        onChange: changeRole,
        style:{background:'var(--bg)',border:'1px solid var(--border)',borderRadius:'8px',padding:'6px 10px',color:'var(--text)',fontSize:'13px',fontFamily:'inherit'}
      }, ...roles.map(r=>h('option',{value:r,selected:r===wr.role}, r)))
    ] : [])
  );
  // Fragment HTML retourné par le service — injecté via .innerHTML sur le noeud DOM
  // (h() du projet est un vDOM custom, pas React → pas de dangerouslySetInnerHTML).
  // Le fragment utilise déjà les CSS vars (--card, --text, --accent...)
  // donc il hérite automatiquement du thème/palette parent.
  const frag = h('div',{className:'card',style:{padding:'18px 20px'}});
  frag.innerHTML = wr.html || '<div class="card-empty">Aucun contenu.</div>';
  return h('div',null, toolbar, frag);
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
function prodSynthFilterSessions(type,key,opts){
  opts = opts || {};
  const wantRep = !!opts.isRep;
  const rows=(S.production&&S.production.by_dossier)||[];
  const k=String(key||'').trim();
  return rows.filter(r=>{
    const rIsRep = _isRepMachine(r.machine);
    if(wantRep && !rIsRep) return false;
    if(!wantRep && rIsRep) return false;
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
  const den=Math.round(t.prod_min)+Math.round(t.arret_min);
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
function openProdSynthDetail(type,keys,index,opts){
  opts = opts || {};
  const isRep = !!opts.isRep;
  const list=(keys||[]).map(k=>String(k));
  if(!list.length)return;
  let idx=Number(index);
  if(!Number.isFinite(idx)||idx<0)idx=0;
  if(idx>=list.length)idx=list.length-1;
  const key=list[idx];
  closeProdSynthModal();
  const TYPE_TITLES={dossier:'Dossier',operator:'Opérateur',machine:'Machine',day:'Jour',team:'Équipe'};
  // Sessions : custom (par equipe repiquage) OU filtre standard
  let sessions;
  if(typeof opts.customSessionsFn === 'function'){
    sessions = opts.customSessionsFn(key) || [];
  }else{
    sessions = prodSynthFilterSessions(type,key,{isRep:isRep});
  }
  const tot=prodSynthTotals(sessions);
  const totCartons = sessions.reduce((s,r)=>s+Number(r.cartons||0),0);
  const total=list.length;
  const goPrev=()=>{if(total>1)openProdSynthDetail(type,list,(idx-1+total)%total,opts);};
  const goNext=()=>{if(total>1)openProdSynthDetail(type,list,(idx+1)%total,opts);};
  const overlay=h('div',{className:'add-row-modal prod-synth-modal'});
  overlay.addEventListener('click',e=>{if(e.target===overlay)closeProdSynthModal();});
  const counter=h('span',{className:'add-row-counter',title:'← → pour naviguer'},
    h('button',{type:'button',className:'add-row-nav-btn',title:'Précédent (←)',disabled:total<=1,onClick:e=>{e.stopPropagation();goPrev();}},'<'),
    h('span',null,String(idx+1)+'/'+String(total)),
    h('button',{type:'button',className:'add-row-nav-btn',title:'Suivant (→)',disabled:total<=1,onClick:e=>{e.stopPropagation();goNext();}},'>')
  );
  const displayKey = (type==='team' || isRep && type==='operator') ? String(key||'—') : prodSynthDisplayKey(type,key);
  const titleRow=h('div',{className:'prod-synth-detail-head'},
    h('div',{className:'prod-synth-detail-title-main'},
      h('span',{className:'prod-synth-detail-eyebrow'}, (isRep?'Repiquage · ':'') + (TYPE_TITLES[type]||'Synthèse')),
      h('h3',{className:'prod-synth-detail-h3'}, displayKey)
    ),
    counter
  );
  const kpi=(lbl,val)=>h('div',{className:'prod-synth-kpi'},
    h('div',{className:'lbl'},lbl),
    h('div',{className:'val'},val)
  );
  // En mode repiquage on masque toujours la colonne Dossier (demande utilisateur).
  const showDossierCol = isRep ? false : (type!=='dossier');

  let sessionRows, headerCells, colSpan;
  if(isRep){
    // Cols : Jour, Opérateur, [Dossier], Client, Désignation, Cartons, Étiquettes
    headerCells = [
      h('th',null,'Jour'),
      h('th',null,'Opérateur'),
      showDossierCol?h('th',null,'Dossier'):null,
      h('th',null,'Client'),
      h('th',null,'Désignation'),
      h('th',{style:{textAlign:'right'}},'Cartons'),
      h('th',{style:{textAlign:'right'}},'Étiquettes'),
    ];
    colSpan = showDossierCol?7:6;
    sessionRows = sessions.length ? sessions.map(s=>{
      const cli=prodSynthCleanClient(s.client);
      const des=(s.designation||'').replace(/^,\s*/,'').trim();
      return h('tr',null,
        h('td',{className:'prod-synth-detail-td-text'},formatJourLabel(s.jour)),
        h('td',{className:'prod-synth-detail-td-text'},opName(s.operateur)),
        showDossierCol?h('td',{className:'prod-synth-detail-td-mono'},s.no_dossier||'—'):null,
        h('td',{className:'prod-synth-detail-td-text'},cli||'—'),
        h('td',{className:'prod-synth-detail-td-wrap'},des||'—'),
        h('td',{className:'prod-synth-detail-td-num'},fN(s.cartons||0)),
        h('td',{className:'prod-synth-detail-td-num'},fN(s.etiquettes||0)),
      );
    }) : [h('tr',null,h('td',{colSpan:colSpan,className:'prod-synth-detail-empty'},'Aucune saisie repiquage sur la période filtrée.'))];
  } else {
    // Cols : Jour, Opérateur, Machine, [Dossier], Client, Désignation, Métrage, Calage, Prod, Arrêts, Vitesse
    // (Étiquettes retirées)
    headerCells = [
      h('th',null,'Jour'),h('th',null,'Opérateur'),h('th',null,'Machine'),
      showDossierCol?h('th',null,'Dossier'):null,
      h('th',null,'Client'),h('th',null,'Désignation'),
      h('th',{style:{textAlign:'right'}},'Métrage'),
      h('th',{style:{textAlign:'right'}},'Calage'),
      h('th',{style:{textAlign:'right'}},'Prod'),
      h('th',{style:{textAlign:'right'}},'Arrêts'),
      h('th',{style:{textAlign:'right'}},'Vitesse'),
    ];
    colSpan = showDossierCol?11:10;
    sessionRows = sessions.length ? sessions.map(s=>{
      const den=Math.round(Number(s.temps_prod_min||0))+Math.round(Number(s.temps_arret_min||0));
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
        h('td',{className:'prod-synth-detail-td-num'},fN(s.metrage_m||0)+' m'),
        h('td',{className:'prod-synth-detail-td-num'},fMin(s.temps_calage_min)),
        h('td',{className:'prod-synth-detail-td-num'},fMin(s.temps_prod_min)),
        h('td',{className:'prod-synth-detail-td-num'},fMin(s.temps_arret_min)),
        h('td',{className:'prod-synth-detail-td-vit'},vit+' m/min')
      );
    }) : [h('tr',null,h('td',{colSpan:colSpan,className:'prod-synth-detail-empty'},'Aucune session sur la période filtrée.'))];
  }

  const isMobileSynth=window.innerWidth<=900;
  if(isMobileSynth) overlay.classList.add('prod-synth-modal--compact');
  const sessionsBlock=h('div',{className:'prod-synth-detail-sessions'},
    h('div',{className:'prod-synth-detail-section-h'},'Détail par session'),
    h('div',{className:'prod-synth-detail-table-wrap'},
      h('table',{className:'table-std prod-synth-detail-table'},
        h('thead',null,h('tr',null,...headerCells)),
        h('tbody',null,...sessionRows)
      )
    )
  );
  const kpisBlock=isRep
    ? h('div',{className:'prod-synth-kpis'},
        kpi('Sessions',String(tot.sessions)),
        kpi('Cartons',fN(totCartons)),
        kpi('Étiquettes',fN(tot.etiquettes)),
      )
    : h('div',{className:'prod-synth-kpis'},
        kpi('Sessions',String(tot.sessions)),
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
function makeProdSynthKeyCell(label,type,keys,index,opts){
  return h('td',{
    className:'prod-synth-key',
    title:'Voir le détail — flèches pour naviguer',
    onClick:e=>{e.stopPropagation();openProdSynthDetail(type,keys,index,opts);}
  },label);
}

// Helper : section repliable avec chevron + persistance localStorage
function _prodSectionState(key, defOpen){
  try{
    const v = localStorage.getItem('mysifa.prod.section.'+key);
    if(v === '0') return false;
    if(v === '1') return true;
  }catch(e){}
  return defOpen!==false;
}
function _prodSetSectionState(key, open){
  try{ localStorage.setItem('mysifa.prod.section.'+key, open?'1':'0'); }catch(e){}
}
function makeCollapsibleSection(titleNode, contentNode, storageKey, defaultOpen){
  const isOpen = _prodSectionState(storageKey, defaultOpen!==false);
  return h('div',{className:'prod-section-wrap',style:{marginBottom:'14px'}},
    h('div',{
      className:'prod-section-header',
      style:{display:'flex',alignItems:'center',gap:'8px',cursor:'pointer',userSelect:'none',padding:'2px 0'},
      onClick:(ev)=>{
        const root = ev.currentTarget.parentNode;
        const ct = root.querySelector('.prod-section-content');
        const cv = root.querySelector('.prod-section-chev');
        const isVisible = ct.style.display !== 'none';
        const next = !isVisible;
        ct.style.display = next ? '' : 'none';
        if(cv) cv.style.transform = next ? 'rotate(90deg)' : 'rotate(0deg)';
        _prodSetSectionState(storageKey, next);
      },
    },
      h('span',{
        className:'prod-section-chev',
        style:{display:'inline-block',width:'14px',textAlign:'center',color:'var(--muted)',fontSize:'11px',transition:'transform .15s',transform: isOpen?'rotate(90deg)':'rotate(0deg)'}
      },'\u25B6'),
      titleNode,
    ),
    h('div',{className:'prod-section-content',style:{display: isOpen ? '' : 'none', marginTop:'6px'}}, contentNode),
  );
}

function renderProdKpis(){
  const d=S.production;
  if(!d)return h('div',{className:'card-empty'},'Chargement des données de production…');
  if(d.blocked)return h('div',{className:'card'},h('div',{className:'card-blocked'},h('div',{className:'cb-icon'},iconEl('lock',32)),h('div',{className:'cb-msg'},d.message)));
  const prod = d.produit||{};
  const tt = d.temps_totaux||{};
  const parts = [];

  // ── Split rep / non-rep depuis by_dossier ────────────────────────
  const byDosAll   = d.by_dossier || d.dossier_times || [];
  const byDosRep   = byDosAll.filter(r => _isRepMachine(r.machine));
  const byDosNoRep = byDosAll.filter(r => !_isRepMachine(r.machine));
  const hasRep     = byDosRep.length > 0;
  const onlyRep    = hasRep && byDosNoRep.length === 0;

  // ── STATUT MACHINES (collapsible avec chevron) ───────────────────
  if(canViewAllProd(S.user)){
    parts.push(renderMachineStatusCards());
  }

  // ── Sanity score cliquable ───────────────────────────────────────
  // Le rôle « commercial » n'a pas accès à la vue Erreurs & Qualité : on retire le clic vers ce détail.
  if(S.historique&&S.historique.sanity && !isCommercial(S.user)){
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

  // Helper mention italique "(hors repiquage)" — affichee uniquement
  // si donnees mixtes (rep + autres machines).
  const horsRepMention = () => hasRep && !onlyRep
    ? h('span',{style:{fontStyle:'italic',color:'var(--muted)',fontSize:'11px',marginLeft:'8px',fontWeight:'400'}},'(hors repiquage)')
    : null;

  // ── QUANTITÉS — masque si seulement repiquage ────────────────────
  if(!onlyRep){
    parts.push(makeCollapsibleSection(
      h('span',{className:'section-title',style:{display:'inline-flex',alignItems:'center',gap:'4px',margin:0,padding:0,border:'none'}},
        iconEl('box',13),' Quantités', horsRepMention()
      ),
      h('div',{className:'stats'},
        h('div',{className:'stat'},h('div',{className:'stat-label'},'Dossiers produits'),h('div',{className:'stat-value'},fN(prod.dossiers||0))),
        h('div',{className:'stat'},h('div',{className:'stat-label'},'Métrage'),h('div',{className:'stat-value'},fN(prod.metrage_m||0)+' m')),
        h('div',{className:'stat'},h('div',{className:'stat-label'},'Vitesse'),h('div',{className:'stat-value'},((d.vitesse_m_min!=null)?Number(d.vitesse_m_min).toFixed(2):'0.00')+' m/min')),
      ),
      'quantites'
    ));
  }

  // ── TEMPS — masque si seulement repiquage ────────────────────────
  if(!onlyRep){
    const prodInclArrets = (Number(tt.production_min||0) + Number(tt.arret_min||0));
    parts.push(makeCollapsibleSection(
      h('span',{className:'section-title',style:{display:'inline-flex',alignItems:'center',gap:'4px',margin:0,padding:0,border:'none'}},
        iconEl('clock',13),' Temps', horsRepMention()
      ),
      h('div',{className:'time-kpi'},
        h('div',{className:'time-card'},h('div',{className:'tc-label',style:{display:'inline-flex',alignItems:'center',gap:'6px'}},iconEl('wrench',12),' Calage'),h('div',{className:'tc-value'},fMin(tt.calage_min))),
        h('div',{className:'time-card'},h('div',{className:'tc-label',style:{display:'inline-flex',alignItems:'center',gap:'6px'}},iconEl('play',12),' Production'),h('div',{className:'tc-value'},fMin(prodInclArrets))),
        h('div',{className:'time-card'},h('div',{className:'tc-label',style:{display:'inline-flex',alignItems:'center',gap:'6px'}},iconEl('alert-triangle',12),' Arrêts'),h('div',{className:'tc-value'},fMin(tt.arret_min))),
      ),
      'temps'
    ));
  }

  // ── SYNTHÈSE DÉTAILLÉE — sous-onglets Machines / Repiquage ───────
  const activeSubTab = _prodSynthTabGet(hasRep, onlyRep);
  // Builders pour chaque sous-onglet
  function buildMachinesPart(){
    const synthParts = [];
    // Par numéro de dossier (+ Client, − Étiquettes)
    const rowsAgg = _prodAggDossier(byDosNoRep);
    if(rowsAgg.length){
      const dossierKeys = rowsAgg.map(r=>String(r.no_dossier));
      synthParts.push(h('div',{className:'card'},
        h('div',{className:'card-header'},h('h3',null,'Par numéro de dossier'),h('span',{style:{fontSize:'11px',color:'var(--muted)'}},rowsAgg.length+' dossiers')),
        h('div',{style:{overflowX:'auto'}},h('table',null,
          h('thead',null,h('tr',null,
            h('th',null,'Dossier'),
            h('th',null,'Client'),
            h('th',null,'Métrage'),
            h('th',null,'Calage'),
            h('th',null,'Prod'),
            h('th',null,'Arrêts'),
            h('th',null,'Vitesse')
          )),
          h('tbody',null,...rowsAgg.map((r,i)=>h('tr',null,
            makeProdSynthKeyCell(r.no_dossier||'','dossier',dossierKeys,i),
            h('td',{className:'prod-synth-detail-td-text'}, prodSynthCleanClient(r.client) || '—'),
            h('td',{style:{fontFamily:'monospace'}},fN(r.metrage_m||0)+' m'),
            h('td',{style:{fontFamily:'monospace',color:'var(--text2)'}},fMin(r.temps_calage_min)),
            h('td',{style:{fontFamily:'monospace',color:'var(--text2)'}},fMin(r.temps_prod_min)),
            h('td',{style:{fontFamily:'monospace',color:'var(--text2)'}},fMin(r.temps_arret_min)),
            h('td',{style:{fontFamily:'monospace',fontWeight:'800',color:'var(--warn)'}},(()=>{const den=Math.round(Number(r.temps_prod_min||0))+Math.round(Number(r.temps_arret_min||0));return (den>0?(Number(r.metrage_m||0)/den).toFixed(2):'0.00')+' m/min';})())
          )))
        ))
      ));
    }
    // Helper card agrégation (Par opérateur / Par machine / Par jour) — sans Étiquettes
    function renderAggCard(title, rows, keyLabel, synthType){
      if(!rows||!rows.length) return null;
      const keys=rows.map(r=>String(r.key));
      const typeMap={'Opérateur':'operator','Machine':'machine','Jour':'day'};
      const st=synthType||(typeMap[keyLabel]||'');
      return h('div',{className:'card'},
        h('div',{className:'card-header'},h('h3',null,title),h('span',{style:{fontSize:'11px',color:'var(--muted)'}},rows.length+' items')),
        h('div',{style:{overflowX:'auto'}},h('table',null,
          h('thead',null,h('tr',null,
            h('th',null,keyLabel),h('th',null,'Dossiers'),
            h('th',null,'Métrage'),h('th',null,'Calage'),h('th',null,'Prod'),h('th',null,'Arrêts'),h('th',null,'Vitesse')
          )),
          h('tbody',null,...rows.map((r,i)=>h('tr',null,
            makeProdSynthKeyCell(keyLabel==='Opérateur'?opName(r.key):(keyLabel==='Jour'?formatJourLabel(r.key):r.key),st,keys,i),
            h('td',{style:{fontFamily:'monospace'}},fN(r.dossiers||0)),
            h('td',{style:{fontFamily:'monospace'}},fN(r.metrage_m||0)+' m'),
            h('td',{style:{fontFamily:'monospace'}},fMin(r.calage_min)),
            h('td',{style:{fontFamily:'monospace'}},fMin(r.prod_min)),
            h('td',{style:{fontFamily:'monospace'}},fMin(r.arret_min)),
            h('td',{style:{fontFamily:'monospace',fontWeight:'800',color:'var(--warn)'}},(Number(r.vitesse_m_min)||0).toFixed(2)+' m/min')
          )))
        ))
      );
    }
    const byOp   = _prodAggBy(byDosNoRep, 'operateur').sort((a,b)=>(b.metrage_m||0)-(a.metrage_m||0));
    const byMach = _prodAggBy(byDosNoRep, 'machine').sort((a,b)=>(b.metrage_m||0)-(a.metrage_m||0));
    const byDay  = _prodAggBy(byDosNoRep, 'jour').sort((a,b)=>String(b.key).localeCompare(String(a.key)));
    synthParts.push(renderAggCard('Par opérateur', byOp, 'Opérateur'));
    synthParts.push(renderAggCard('Par machine',   byMach, 'Machine'));
    synthParts.push(renderAggCard('Par jour',      byDay, 'Jour'));
    return h('div',null,...synthParts.filter(Boolean));
  }

  function buildRepiquagePart(){
    if(!hasRep){
      return h('div',{style:{padding:'18px 6px',fontSize:'13px',color:'var(--muted)',fontStyle:'italic'}},
        'Pas de repiquage avec les filtres actuels.');
    }
    if(!byDosRep.length){
      return h('div',{style:{padding:'18px 6px',fontSize:'13px',color:'var(--muted)',fontStyle:'italic'}},
        'Aucune donnée repiquage pour cette période.');
    }

    // ── Hiérarchie : Dossier → Équipe → Jour ────────────────────────
    const hier = {};  // dosKey -> { no_dossier, client, total, teams:{} }
    byDosRep.forEach(r => {
      const dos = String(r.no_dossier||'').trim();
      if(!dos) return;
      const team = String(r.team_label || 'Repiquage').trim() || 'Repiquage';
      const jour = String(r.jour||'').trim();
      if(!hier[dos]){
        hier[dos] = {
          no_dossier: dos,
          client: '',
          total: {cartons:0, etiquettes:0},
          teams: {},
        };
      }
      if(!hier[dos].client && r.client) hier[dos].client = r.client;
      hier[dos].total.cartons += Number(r.cartons||0);
      hier[dos].total.etiquettes += Number(r.etiquettes||0);
      if(!hier[dos].teams[team]){
        hier[dos].teams[team] = { total:{cartons:0,etiquettes:0}, days:{} };
      }
      hier[dos].teams[team].total.cartons += Number(r.cartons||0);
      hier[dos].teams[team].total.etiquettes += Number(r.etiquettes||0);
      if(!hier[dos].teams[team].days[jour]){
        hier[dos].teams[team].days[jour] = { cartons:0, etiquettes:0 };
      }
      hier[dos].teams[team].days[jour].cartons += Number(r.cartons||0);
      hier[dos].teams[team].days[jour].etiquettes += Number(r.etiquettes||0);
    });

    // ── Ordres de tri ─────────────────────────────────────────────────
    const dossierEntries = Object.values(hier).sort((a,b)=>String(a.no_dossier).localeCompare(
      String(b.no_dossier),'fr',{numeric:true,sensitivity:'base'}));

    // ── Helpers de filtrage pour les modales (lookup par ligne cliquee) ─
    const filterByDossier = (key) => byDosRep
      .filter(s => String(s.no_dossier||'').trim() === String(key||'').trim())
      .sort((a,b)=>String(b.jour||'').localeCompare(String(a.jour||'')));
    const filterByDossierTeam = (dos, team) => byDosRep
      .filter(s => String(s.no_dossier||'').trim() === dos
        && String(s.team_label||'Repiquage').trim() === team)
      .sort((a,b)=>String(b.jour||'').localeCompare(String(a.jour||'')));
    const filterByDossierTeamDay = (dos, team, jour) => byDosRep
      .filter(s => String(s.no_dossier||'').trim() === dos
        && String(s.team_label||'Repiquage').trim() === team
        && String(s.jour||'').trim() === jour);

    // ── Cellules de ligne (indented + clickable) ──────────────────────
    function detailCell(label, level, onClick, secondary){
      // level 0 = dossier (bold, accent), 1 = team, 2 = jour (mono, muted)
      const pad = 12 + level * 22;
      const style = {paddingLeft: pad+'px', cursor: onClick ? 'pointer' : 'default'};
      if(level === 0){
        style.fontWeight = '700';
        style.color = 'var(--text)';
        style.fontSize = '13px';
      }else if(level === 1){
        style.fontWeight = '600';
        style.color = 'var(--text2)';
        style.fontSize = '12.5px';
      }else{
        style.fontFamily = 'monospace';
        style.color = 'var(--muted)';
        style.fontSize = '12px';
      }
      const props = {style};
      if(onClick){
        props.className = 'prod-synth-key';
        props.title = 'Voir le détail';
        props.onClick = (e)=>{e.stopPropagation(); onClick();};
      }
      return h('td', props,
        h('span', null, label),
        secondary ? h('span',{style:{fontWeight:'400',color:'var(--text2)',marginLeft:'8px',fontSize:'12px'}}, '— ' + secondary) : null
      );
    }
    function numCell(val, level){
      const style = {textAlign:'right', fontFamily:'monospace'};
      if(level === 0){ style.fontWeight='800'; style.color='var(--accent)'; style.fontSize='13px'; }
      else if(level === 1){ style.fontWeight='700'; style.color='var(--text2)'; style.fontSize='12.5px'; }
      else { style.color='var(--muted)'; style.fontSize='12px'; }
      return h('td',{style}, fN(val||0));
    }

    const tbodyKids = [];
    const repOpenDos = (dos) => {
      const keys = dossierEntries.map(e => e.no_dossier);
      const idx = keys.indexOf(dos);
      openProdSynthDetail('dossier', keys, Math.max(0,idx), {isRep:true, customSessionsFn:filterByDossier});
    };
    const repOpenTeam = (dos, team) => {
      // Modal centree sur ce dossier+team
      openProdSynthDetail('team', [team], 0, {
        isRep:true,
        customSessionsFn: (k) => filterByDossierTeam(dos, k),
      });
    };
    const repOpenDay = (dos, team, jour) => {
      openProdSynthDetail('day', [jour], 0, {
        isRep:true,
        customSessionsFn: (k) => filterByDossierTeamDay(dos, team, k),
      });
    };

    dossierEntries.forEach((dosEntry, dosIdx) => {
      const dosLabel = dosEntry.no_dossier;
      const cli = prodSynthCleanClient(dosEntry.client) || '';
      // Ligne dossier — separateur fort en haut
      tbodyKids.push(h('tr',{className:'rep-hier-dossier', style:{borderTop:(dosIdx>0?'2px solid var(--border)':'none'), background:'var(--accent-bg)'}},
        detailCell(dosLabel, 0, () => repOpenDos(dosLabel), cli),
        numCell(dosEntry.total.cartons, 0),
        numCell(dosEntry.total.etiquettes, 0),
      ));
      // Equipes ordonnees (border-top entre 2 equipes d'un meme dossier)
      const teamEntries = Object.entries(dosEntry.teams).sort((a,b)=>a[0].localeCompare(b[0],'fr'));
      teamEntries.forEach(([teamLabel, teamData], teamIdx) => {
        const teamSep = teamIdx > 0 ? '1px solid var(--border)' : 'none';
        const teamCell = detailCell(teamLabel, 1, () => repOpenTeam(dosLabel, teamLabel));
        teamCell.style.borderTop = teamSep;
        const teamCartonsCell = numCell(teamData.total.cartons, 1);
        teamCartonsCell.style.borderTop = teamSep;
        const teamEtiqCell = numCell(teamData.total.etiquettes, 1);
        teamEtiqCell.style.borderTop = teamSep;
        tbodyKids.push(h('tr',{
          className:'rep-hier-team',
          'data-team': teamLabel,
          onmouseenter: () => _repHighlightTeam(teamLabel, true),
          onmouseleave: () => _repHighlightTeam(teamLabel, false),
          style:{transition:'background 120ms'},
        },
          teamCell, teamCartonsCell, teamEtiqCell,
        ));
        // Jours ordonnes desc
        const dayEntries = Object.entries(teamData.days).sort((a,b)=>String(b[0]).localeCompare(String(a[0])));
        dayEntries.forEach(([jour, dayData]) => {
          const dayKey = teamLabel + '|' + jour;
          tbodyKids.push(h('tr',{
            className:'rep-hier-day',
            'data-team-jour': dayKey,
            onmouseenter: () => _repHighlightDay(dayKey, true),
            onmouseleave: () => _repHighlightDay(dayKey, false),
            style:{transition:'background 120ms,color 120ms'},
          },
            detailCell(formatJourLabel(jour), 2, () => repOpenDay(dosLabel, teamLabel, jour)),
            numCell(dayData.cartons, 2),
            numCell(dayData.etiquettes, 2),
          ));
        });
      });
    });

    // Total general
    const grandTot = dossierEntries.reduce((acc,d) => ({
      cartons: acc.cartons + Number(d.total.cartons||0),
      etiquettes: acc.etiquettes + Number(d.total.etiquettes||0),
    }), {cartons:0, etiquettes:0});

    // ── Cartons par jour x dossier (pour le graphe) ──────────────────
    const byDayDosMap = {};
    byDosRep.forEach(r => {
      const j = String(r.jour||'').trim(); if(!j) return;
      const d = String(r.no_dossier||'').trim(); if(!d) return;
      if(!byDayDosMap[j]) byDayDosMap[j] = {};
      byDayDosMap[j][d] = (byDayDosMap[j][d]||0) + Number(r.cartons||0);
    });
    const allDossierKeys = dossierEntries.map(e => e.no_dossier);
    const allJours = Object.keys(byDayDosMap).sort();

    // Set de chips actives — reset auto si le scope (liste des dossiers) change
    const activeKey = allDossierKeys.join('|');
    if(!(window._repChartActive instanceof Set) || window._repChartActiveScope !== activeKey){
      window._repChartActive = new Set(allDossierKeys);
      window._repChartActiveScope = activeKey;
    }
    const activeSet = window._repChartActive;

    function buildChartSide(){
      // Palette : couleurs cohérentes avec le thème
      const palette = ['#22d3ee','#fbbf24','#a78bfa','#f472b6','#34d399','#f87171','#60a5fa','#fb923c','#ec4899','#14b8a6'];
      const dosColors = {};
      allDossierKeys.forEach((k,i) => { dosColors[k] = palette[i % palette.length]; });

      // ── Chips toggleables ──
      const chipsContainer = h('div',{style:{display:'flex',flexWrap:'wrap',gap:'6px',marginBottom:'14px',alignItems:'center'}});
      allDossierKeys.forEach(dosKey => {
        const isActive = activeSet.has(dosKey);
        const dosEntry = hier[dosKey];
        const cli = prodSynthCleanClient(dosEntry.client || '');
        const lbl = dosKey + (cli ? ' — ' + cli : '');
        const chip = h('button',{
          type:'button',
          title: 'Cliquer pour ' + (isActive?'masquer':'afficher'),
          style:{
            padding:'4px 10px',fontSize:'11px',fontWeight:'600',borderRadius:'14px',
            border:'1px solid ' + (isActive ? dosColors[dosKey] : 'var(--border)'),
            background: isActive ? (dosColors[dosKey] + '22') : 'transparent',
            color: isActive ? dosColors[dosKey] : 'var(--muted)',
            cursor:'pointer',fontFamily:'inherit',whiteSpace:'nowrap',
            opacity: isActive ? 1 : 0.7,
          },
          onClick:(e)=>{
            e.stopPropagation();
            if(activeSet.has(dosKey)) activeSet.delete(dosKey); else activeSet.add(dosKey);
            render();
          },
        });
        chip.innerHTML = '<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:' + (isActive?dosColors[dosKey]:'var(--muted)') + ';margin-right:6px;vertical-align:middle"></span>' + escHtml(lbl);
        chipsContainer.appendChild(chip);
      });
      chipsContainer.appendChild(h('span',{style:{flex:'1'}}));
      chipsContainer.appendChild(h('button',{
        type:'button',
        style:{padding:'4px 8px',fontSize:'10px',border:'1px solid var(--border)',background:'transparent',color:'var(--text2)',cursor:'pointer',borderRadius:'6px',fontFamily:'inherit'},
        onClick:(e)=>{e.stopPropagation(); window._repChartActive = new Set(allDossierKeys); render();},
      },'Tout'));
      chipsContainer.appendChild(h('button',{
        type:'button',
        style:{padding:'4px 8px',fontSize:'10px',border:'1px solid var(--border)',background:'transparent',color:'var(--text2)',cursor:'pointer',borderRadius:'6px',fontFamily:'inherit',marginLeft:'4px'},
        onClick:(e)=>{e.stopPropagation(); window._repChartActive = new Set(); render();},
      },'Aucun'));

      // ── États vides ──
      const wrap = h('div',null);
      wrap.appendChild(chipsContainer);
      if(!allJours.length){
        const empty = h('div',{style:{padding:'40px 20px',textAlign:'center',color:'var(--muted)',fontSize:'12px',fontStyle:'italic',background:'var(--bg)',borderRadius:'8px',border:'1px dashed var(--border)'}});
        empty.textContent = 'Aucune donnée pour le graphique.';
        wrap.appendChild(empty);
        return wrap;
      }
      if(activeSet.size === 0){
        const empty = h('div',{style:{padding:'40px 20px',textAlign:'center',color:'var(--muted)',fontSize:'12px',fontStyle:'italic',background:'var(--bg)',borderRadius:'8px',border:'1px dashed var(--border)'}});
        empty.textContent = 'Sélectionne au moins un dossier pour voir le graphique.';
        wrap.appendChild(empty);
        return wrap;
      }

      // ── Line chart : 1 ligne par équipe, X = jours, Y = cartons ──
      // Filtre par chips dossier : ne compte que les dossiers actifs.
      const teamSet = new Set();
      const byTeamDayMap = {};  // team -> { jour -> cartons }
      byDosRep.forEach(r => {
        const dos = String(r.no_dossier||'').trim();
        if(!activeSet.has(dos)) return;
        const team = (String(r.team_label || 'Repiquage').trim()) || 'Repiquage';
        const jour = String(r.jour||'').trim();
        if(!jour) return;
        teamSet.add(team);
        if(!byTeamDayMap[team]) byTeamDayMap[team] = {};
        byTeamDayMap[team][jour] = (byTeamDayMap[team][jour]||0) + Number(r.cartons||0);
      });
      const teamArr = Array.from(teamSet).sort((a,b)=>a.localeCompare(b,'fr'));
      // Jours actifs : ceux ou au moins une equipe a une saisie
      const activeJours = allJours.filter(j => teamArr.some(t => byTeamDayMap[t] && byTeamDayMap[t][j] != null));
      if(!teamArr.length || !activeJours.length){
        const empty = h('div',{style:{padding:'40px 20px',textAlign:'center',color:'var(--muted)',fontSize:'12px',fontStyle:'italic',background:'var(--bg)',borderRadius:'8px',border:'1px dashed var(--border)'}});
        empty.textContent = 'Aucune équipe à afficher pour les dossiers sélectionnés.';
        wrap.appendChild(empty);
        return wrap;
      }

      // Couleurs par equipe (palette stable)
      const teamPalette = ['#22d3ee','#fbbf24','#a78bfa','#f472b6','#34d399','#f87171','#60a5fa','#fb923c','#ec4899','#14b8a6'];
      const teamColors = {};
      teamArr.forEach((t,i) => { teamColors[t] = teamPalette[i % teamPalette.length]; });

      // Max Y
      let maxVal = 0;
      teamArr.forEach(t => activeJours.forEach(j => {
        const v = (byTeamDayMap[t] && byTeamDayMap[t][j]) || 0;
        if(v > maxVal) maxVal = v;
      }));
      function niceRound(v){
        if(v <= 0) return 10;
        const pow = Math.pow(10, Math.floor(Math.log10(v)));
        const norm = v / pow;
        let nice;
        if(norm <= 1) nice = 1;
        else if(norm <= 2) nice = 2;
        else if(norm <= 5) nice = 5;
        else nice = 10;
        return nice * pow;
      }
      const niceMax = niceRound(Math.max(1, maxVal));

      // SVG
      const W = 600, H = 240;
      const mL = 44, mR = 12, mT = 18, mB = 46;
      const innerW = W - mL - mR;
      const innerH = H - mT - mB;
      const n = activeJours.length;
      // Position X : centre des "slots"
      const xAt = (idx) => n === 1 ? mL + innerW/2 : mL + idx * (innerW / (n-1));
      const yAt = (v) => mT + innerH - (v/niceMax)*innerH;
      const yTicks = [0, niceMax/4, niceMax/2, niceMax*3/4, niceMax];

      let svg = '<svg viewBox="0 0 ' + W + ' ' + H + '" style="width:100%;height:240px;display:block;font-family:inherit" preserveAspectRatio="xMidYMid meet">';
      // Grille Y
      yTicks.forEach(t => {
        const y = yAt(t);
        svg += '<line x1="' + mL + '" x2="' + (W-mR) + '" y1="' + y + '" y2="' + y + '" stroke="var(--border)" stroke-width="1" stroke-dasharray="2,3" opacity="0.6"/>';
        svg += '<text x="' + (mL-6) + '" y="' + (y+3) + '" text-anchor="end" font-size="9" fill="var(--muted)">' + escHtml(fN(Math.round(t))) + '</text>';
      });
      svg += '<line x1="' + mL + '" x2="' + (W-mR) + '" y1="' + (mT+innerH) + '" y2="' + (mT+innerH) + '" stroke="var(--border)" stroke-width="1.5"/>';

      // X labels
      activeJours.forEach((j, i) => {
        const x = xAt(i);
        const lbl = formatJourLabel(j);
        const lblShort = lbl.length > 5 ? lbl.slice(0,5) : lbl;
        svg += '<text x="' + x + '" y="' + (H-mB+16) + '" text-anchor="middle" font-size="10" fill="var(--text2)">' + escHtml(lblShort) + '</text>';
      });

      // Une polyline par equipe (avec classes + data-attrs pour l'interactivite)
      teamArr.forEach(team => {
        const pts = [];
        activeJours.forEach((j, i) => {
          const raw = (byTeamDayMap[team] && byTeamDayMap[team][j]);
          if(raw == null) return;
          pts.push({x:xAt(i), y:yAt(raw), v:raw, j});
        });
        if(!pts.length) return;
        const teamAttr = escHtml(team);
        if(pts.length > 1){
          const polyD = pts.map(p => p.x.toFixed(2)+','+p.y.toFixed(2)).join(' ');
          svg += '<polyline class="rep-chart-line" data-team="' + teamAttr + '" points="' + polyD + '" fill="none" stroke="' + teamColors[team] + '" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" opacity="0.95" style="pointer-events:none"/>';
        }
        pts.forEach(p => {
          const tt = formatJourLabel(p.j) + ' — ' + team + ' : ' + fN(p.v) + ' cartons';
          const dayKey = team + '|' + p.j;
          svg += '<circle class="rep-chart-point" data-team="' + teamAttr + '" data-team-jour="' + escHtml(dayKey) + '" cx="' + p.x.toFixed(2) + '" cy="' + p.y.toFixed(2) + '" r="3.5" fill="' + teamColors[team] + '" stroke="var(--card)" stroke-width="1.5" style="cursor:pointer;transition:r 120ms,stroke-width 120ms"><title>' + escHtml(tt) + '</title></circle>';
        });
      });
      svg += '</svg>';

      // Fond transparent : le card parent fournit deja le conteneur.
      const chartBox = h('div',{style:{padding:'8px 4px 4px',borderRadius:'8px'}});
      chartBox.innerHTML = svg;
      // Delegation : hover d'un point chart -> highlight ligne table correspondante
      chartBox.addEventListener('mouseover', (e) => {
        const t = e.target;
        if(t && t.classList && t.classList.contains('rep-chart-point')){
          const key = t.getAttribute('data-team-jour');
          if(key) _repHighlightDay(key, true);
        }
      });
      chartBox.addEventListener('mouseout', (e) => {
        const t = e.target;
        if(t && t.classList && t.classList.contains('rep-chart-point')){
          const key = t.getAttribute('data-team-jour');
          if(key) _repHighlightDay(key, false);
        }
      });
      wrap.appendChild(chartBox);

      // Légende équipes (sous le graphe)
      const legend = h('div',{style:{display:'flex',flexWrap:'wrap',gap:'10px',justifyContent:'center',marginTop:'8px',fontSize:'11px'}});
      teamArr.forEach(team => {
        const item = h('span',{style:{display:'inline-flex',alignItems:'center',gap:'5px',color:'var(--text2)'}});
        item.innerHTML = '<span style="display:inline-block;width:10px;height:2px;background:' + teamColors[team] + ';border-radius:1px"></span> <span>' + escHtml(team) + '</span>';
        legend.appendChild(item);
      });
      wrap.appendChild(legend);

      return wrap;
    }

    // ── Layout : 2 cards séparées côte à côte (table | chart) ──
    const tableCard = h('div',{className:'card',style:{flex:'1 1 calc(50% - 8px)',minWidth:'320px'}},
      h('div',{className:'card-header'},
        h('h3',null,'Repiquage — synthèse détaillée'),
        h('span',{style:{fontSize:'11px',color:'var(--muted)'}},
          'Total : ', h('strong',{style:{color:'var(--accent)',fontFamily:'monospace'}}, fN(grandTot.cartons)+' cartons'),
          ' · ',
          h('strong',{style:{color:'var(--accent)',fontFamily:'monospace'}}, fN(grandTot.etiquettes)+' étiquettes'),
          ' · ',
          dossierEntries.length+' dossier'+(dossierEntries.length>1?'s':'')
        )
      ),
      h('div',{style:{overflowX:'auto'}},
        h('table',{className:'rep-synth-table',style:{width:'100%',borderCollapse:'collapse',fontSize:'12px'}},
          h('thead',null,h('tr',null,
            h('th',{style:{textAlign:'left',paddingLeft:'12px'}},'Détail'),
            h('th',{style:{textAlign:'right',paddingRight:'10px'}},'Cartons'),
            h('th',{style:{textAlign:'right',paddingRight:'10px'}},'Étiquettes')
          )),
          h('tbody',null,...tbodyKids)
        )
      )
    );
    const chartCard = h('div',{className:'card',style:{flex:'1 1 calc(50% - 8px)',minWidth:'320px'}},
      h('div',{className:'card-header'},
        h('h3',null,'Cartons par jour et par équipe'),
        h('span',{style:{fontSize:'11px',color:'var(--muted)'}},
          activeSet.size + ' / ' + allDossierKeys.length + ' dossier' + (allDossierKeys.length>1?'s':'') + ' actif' + (activeSet.size>1?'s':'')
        )
      ),
      h('div',{style:{padding:'4px 4px 8px'}}, buildChartSide())
    );
    return h('div',{style:{display:'flex',gap:'16px',flexWrap:'wrap',alignItems:'flex-start'}},
      tableCard,
      chartCard
    );
  }

  // Barre de sous-onglets [Machines] [Repiquage]
  const tabBtn = (key, label, disabled) => h('button',{
    type:'button',
    className: 'synth-subtab' + (activeSubTab===key?' active':'') + (disabled?' disabled':''),
    disabled: !!disabled,
    title: disabled ? 'Pas de repiquage avec les filtres actuels' : '',
    style: {
      padding:'6px 14px', background:'transparent',
      border:'1px solid var(--border)', borderRadius:'8px',
      color: disabled ? 'var(--muted)' : (activeSubTab===key ? 'var(--accent)' : 'var(--text2)'),
      fontWeight: activeSubTab===key ? 700 : 500,
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.55 : 1,
      fontSize:'12px',
      background: activeSubTab===key && !disabled ? 'var(--accent-bg)' : 'transparent',
      borderColor: activeSubTab===key && !disabled ? 'var(--accent)' : 'var(--border)',
    },
    onClick: disabled ? null : (e)=>{
      e.stopPropagation();
      _prodSynthTabSet(key);
      render();
    },
  }, label);

  const subTabsBar = h('div',{style:{display:'flex',gap:'8px',marginBottom:'10px',alignItems:'center'}},
    tabBtn('machines','Machines',false),
    tabBtn('repiquage','Repiquage', !hasRep),
  );

  const synthContent = activeSubTab === 'repiquage' ? buildRepiquagePart() : buildMachinesPart();

  parts.push(makeCollapsibleSection(
    h('span',{className:'section-title',style:{margin:0,padding:0,border:'none'}},'📌 Synthèse détaillée'),
    h('div',null, subTabsBar, synthContent),
    'synthese'
  ));

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
        }else if(S.page === 'dossiers'){
          await loadDos();
        }else if(S.page === 'suivi'){
          await loadDos();
          await loadDevis();
        }else if(S.page === 'rentabilite'){
          await loadDevis();
          await loadRentPlanning();
        }else if(S.page === 'historique'){
          await loadHist();
        }else if(S.page === 'saisies'){
          await loadSaisies();
        }else if(S.page === 'import'){
          await loadImports();
        }else if(S.page === 'traceabilite'){
          await loadTracabilite();
        }else if(S.page === 'of' && canAccessOfTab()){
          await loadOfImports();
          if(S.ofSubTab === 'fiche') await loadFiches();
        }
        // Badge "Mappings OF à valider" dans la sidebar
        try{ if(canAccessOfTab()) loadPendingOfCount(); }catch(e){}
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
        }else if(S.page === 'dossiers'){
          await loadDos();
        }else if(S.page === 'suivi'){
          await loadDos();
          await loadDevis();
        }else if(S.page === 'rentabilite'){
          await loadDevis();
          await loadRentPlanning();
        }else if(S.page === 'historique'){
          await loadHist();
        }else if(S.page === 'saisies'){
          await loadSaisies();
        }else if(S.page === 'import'){
          await loadImports();
        }else if(S.page === 'traceabilite'){
          await loadTracabilite();
        }else if(S.page === 'of' && canAccessOfTab()){
          await loadOfImports();
          if(S.ofSubTab === 'fiche') await loadFiches();
        }
        // Badge "Mappings OF à valider" dans la sidebar
        try{ if(canAccessOfTab()) loadPendingOfCount(); }catch(e){}
        render();
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
      }else if(S.page === 'dossiers'){
        await loadDos();
      }else if(S.page === 'suivi'){
        await loadDos();
        await loadDevis();
      }else if(S.page === 'rentabilite'){
        await loadDevis();
        await loadRentPlanning();
      }else if(S.page === 'traceabilite'){
        S.traceabilite = null;
        S.traceabiliteDossier = undefined;
        S.tracShowAttente = false;
        await loadTracabilite();
      }else if(S.page === 'of' && canAccessOfTab()){
        await loadOfImports();
        if(S.ofSubTab === 'fiche') await loadFiches();
        else if(S.ofSubTab === 'sans_of') await loadDossiersSansOf();
        else if(S.ofSubTab === 'mappings') await loadPendingOfMappings();
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
    }else if(S.page === 'of'){
      pageTitle = 'Ordres de fabrication';
      pageSubtitle = 'Import PDF et consultation des OF';
      pageContent = canAccessOfTab()
        ? renderOfPage()
        : h('div', {className: 'card-empty'}, 'Accès réservé à l\u0027administration.');
    }else if(S.page === 'traceabilite'){
      pageTitle = 'Traçabilité';
      pageSubtitle = 'Matières utilisées par dossier';
      pageContent = renderTracabilite();
    }else if(S.page === 'suivi'){
      pageTitle = 'Rentabilité & Dossiers';
      pageSubtitle = 'Dossiers de production et comparaison devis / réel';
      pageContent = renderSuivi();
    }else if(S.page === 'rentabilite'){
      pageTitle = 'Rentabilité';
      pageSubtitle = 'Suivi rentabilité par dossier (devis / réel)';
      pageContent = renderRentabilite();
    }else if(S.page === 'dossiers'){
      pageTitle = 'Dossiers';
      pageSubtitle = 'Liste et statuts des dossiers';
      pageContent = renderDos();
    }else{
      pageContent = h('div', {className: 'card', style: {padding: '32px', textAlign: 'center'}},
        h('h2', {style: {marginBottom: '8px'}}, 'Sous-page : ' + (S.page || '')),
        h('p', {style: {color: 'var(--text2)', fontSize: '13px'}},
          'Le contenu de cette sous-page sera ajout\u00e9 aux \u00e9tapes ult\u00e9rieures (2k - 2l). ' +
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

    // Modal d'import OF (mounted hors du flow, à la racine de #root)
    if(S.ofImportModal){
      const m = renderOfImportModal();
      if(m) root.appendChild(m);
    }

    // ── Couche d'animation (motion.css / motion.js) ──────────────────
    // Détecte les changements d'onglet et applique :
    //   pattern 1 (data-page-enter) sur le container,
    //   pattern 2 (.mo-reveal) sur les cards / stats,
    //   pattern 3 (count-up) sur les valeurs chiffrées.
    // Sur les re-renders intra-onglet (filtres, pagination), aucun
    // élément n'est animé : on évite les replays parasites.
    try { __moApplyPostRender(root); } catch(e){}
  }

  // État de nav pour détecter les transitions d'onglet
  let __moNavKey = null;
  function __moApplyPostRender(root){
    if(!root) return;
    if(typeof window === 'undefined' || !window.Motion) return;
    const container = root.querySelector('.app .container');
    if(!container) return;
    const navKey = (S.page || '') + '|' + (S.subPage || '') + '|' + (S.ofSubTab || '');
    const navChanged = navKey !== __moNavKey;
    __moNavKey = navKey;

    if(navChanged){
      // Pattern 1 : cascade d'entrée sur les enfants directs du container
      container.setAttribute('data-page-enter', '');
      // Pattern 2 : reveal au scroll sur cards et stats hors cascade directe
      const reveals = container.querySelectorAll('.card, .stat, .machine-card');
      for(let i=0; i<reveals.length; i++){
        const el = reveals[i];
        // Évite double-anim : si l'élément est déjà un enfant direct du container
        // il sera animé par data-page-enter.
        if(el.parentElement === container) continue;
        el.classList.add('mo-reveal');
      }
      // Pattern 3 : count-up sur les valeurs chiffrées (stat-value)
      const stats = container.querySelectorAll('.stat-value');
      for(let j=0; j<stats.length; j++){
        const el = stats[j];
        if(el.dataset.countTo) continue;
        // Skip si contenu HTML non purement texte (icônes, badges…)
        if(el.children && el.children.length > 0) continue;
        const txt = (el.textContent || '').trim();
        if(!txt || txt === '—' || txt === '-' || txt === '…') continue;
        // Match « 1 234,56 » ou « 1234.56 » ou « 92 » avec un suffixe non chiffre optionnel
        const m = txt.match(/^(-?[\d   ]+(?:[\.,]\d+)?)([^\d]*)$/);
        if(!m) continue;
        const raw = m[1].replace(/[   ]/g, '').replace(',', '.');
        const num = parseFloat(raw);
        if(!isFinite(num)) continue;
        const decimals = (raw.split('.')[1] || '').length;
        const suffix = m[2] || '';
        el.dataset.countTo = String(num);
        if(decimals) el.dataset.decimals = String(decimals);
        if(suffix) el.dataset.suffix = suffix;
        el.textContent = decimals ? '0,' + '0'.repeat(decimals) : '0';
      }
    } else {
      // Pas de changement d'onglet : on retire data-page-enter pour qu'aucune
      // cascade ne se rejoue sur ce re-render (filtres, pagination, etc.).
      container.removeAttribute('data-page-enter');
    }
    try { window.Motion.scan(root); } catch(e){}
  }

  // ── Exposition globale pour debugging et étapes suivantes ──────────
  // Les fonctions sont mises en `window` pour que les étapes 2f+ puissent
  // les compléter / les utiliser. À la fin du refactor (étape 2n), ces
  // exports pourront être retirés si plus nécessaire.
  window.__MYSIFA_PROD_STANDALONE__ = {
    stage: '2l',
    description: 'Onglet Fiches + OF (final)',
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
    createDos, updStatut,
    loadComparaison, uploadDevis, saveDevis, linkDossiers, deleteDevis,
    renderDos, renderDevisForm, renderComparaison, renderLiaisonDossiers,
    renderRentabilite, renderSuivi,
    loadTracabilite, loadTracabiliteDossier,
    renderTracabilite, renderTracabiliteDossierDetail,
    openFscRapportModal, openTracMatieresEditModal, closeTracMatieresEditModal,
    tracResolveMachineId,
    prodOfFmtDate, prodOfStatutLabel, prodOfStatutClass,
    loadOfImports, loadFiches, loadPendingOfCount, loadPendingOfMappings,
    submitOfMapping, submitOfMappingMulti, loadDossiersSansOf,
    searchOfsForAttach, attachOfsToDossier, toggleAttachOfPicker,
    renderDossiersSansOfTab, renderPendingOfMappingsTab,
    exportFichesCsv, exportOfCsv,
    openOfEditModal, closeOfEditModal, saveOfEdit, renderOfEditModal,
    openFicheEditModal, closeFicheEditModal, saveFicheEdit, renderFicheEditModal,
    openOfImportModal, closeOfImportModal, ofHandlePdfFile,
    ofValidateImport, ofDeleteImport, renderOfImportModal,
    renderPaginationBar, renderOfTab, renderFichesTab, renderOfPage,
  };

  console.info('[mysifa_prod_core] fiches + OF charges - etape 2l (final)', {
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


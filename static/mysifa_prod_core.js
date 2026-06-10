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

  // ── 11. Stub render() ──────────────────────────────────────────────
  // À l'étape 2e, render() est un no-op : le placeholder HTML reste
  // affiché tel qu'inscrit dans PROD_HTML. Aux étapes 2f+, render()
  // sera étoffé pour afficher la sidebar puis les sous-pages MyProd.
  function render(){
    // no-op à l'étape 2e
  }

  // ── Exposition globale pour debugging et étapes suivantes ──────────
  // Les fonctions sont mises en `window` pour que les étapes 2f+ puissent
  // les compléter / les utiliser. À la fin du refactor (étape 2n), ces
  // exports pourront être retirés si plus nécessaire.
  window.__MYSIFA_PROD_STANDALONE__ = {
    stage: '2e',
    description: 'Socle JS — helpers + state S filtré',
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
    render,
  };

  console.info('[mysifa_prod_core] socle JS chargé — étape 2e', {
    helpers: Object.keys(window.__prodCore).length,
    stateFields: Object.keys(S).length,
  });
})();

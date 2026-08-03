/* MySifa - Modales de mouvement de stock (matieres premieres + produits finis Z1)
 *
 * Source unique partagee par MyStock (/stock) et Saisie Production (/fabrication).
 * Extrait de app/web/stock_page.py : le code des modales y etait couple a l'etat
 * global de la page, ce qui interdisait de l'ouvrir depuis Saisie Prod autrement
 * qu'en redirigeant l'operateur vers MyStock.
 *
 * La page hote fournit ses helpers via configure() ; le module ne connait ni son
 * DOM ni sa boucle de rendu. Seul prerequis : un element #mroot ou monter les
 * overlays.
 *
 * Usage :
 *   MySifaStockModals.configure({
 *     el, api, showToast, closeMroot, fN, fDateTime, fU,
 *     getStockEmplacements, stockAtEmpl,
 *     state:  () => ({tab, matieres, selProduit, selEmpl, selMatiere, fabStockMode}),
 *     setMatieres: (list) => {...},
 *     reload: (quoi, arg) => {...},
 *     emplacements: () => [...],
 *     uniteVenteDefaut: 'etiquette',
 *     emplAuSol: 'Z0', emplSortieProd: 'Z1',
 *     emplAuSolLabel: '...', emplSortieProdLabel: '...',
 *   });
 *   MySifaStockModals.open('entree-z1');
 */
(function (global) {
  'use strict';

  // --- Adaptateur hote -------------------------------------------------
  var HOST = null;
  function _h() {
    if (!HOST) throw new Error('MySifaStockModals : configure() non appele.');
    return HOST;
  }

  // --- Helpers de rendu par defaut -------------------------------------
  // Repris a l'identique de MyStock : une page hote qui n'a pas le meme
  // contrat de constructeur DOM (Saisie Prod utilise h()) laisse le module
  // fournir les siens plutot que d'en reimplementer une variante.
  const _defFN = n => n != null ? Number(n).toLocaleString('fr-FR') : '0';

  function _defFU(qty, unite) {
    const u = String(unite || '').trim();
    if (!u) return fN(qty);
    const n = parseFloat(qty) || 0;
    // Abréviation pour les unités longues
    const uLow = u.toLowerCase();
    if(uLow === 'étiquettes' || uLow === 'etiquettes' || uLow === 'étiquette' || uLow === 'etiquette'){
      return fN(n) + '\u00a0eti.';
    }
    return fN(n) + '\u00a0' + (Math.abs(n) > 1 ? u + 's' : u);
  }

  function _defFDateTime(iso) {
    if (!iso) return '—';
    const s = String(iso);
    const parts = s.slice(0, 10).split('-');
    const hm = s.length >= 16 ? s.slice(11, 16) : '';
    if (parts.length === 3) {
      return parts[2] + '/' + parts[1] + '/' + parts[0] + (hm ? ' ' + hm : '');
    }
    return fD(iso);
  }

  function _defEl(tag, attrs, ...children) {
    const e = document.createElement(tag);
    if (attrs) {
      const { cls, className, on, style: s, html, attrs: subAttrs, ...rest } = attrs;
      const cn = cls || className;
      if (cn) e.className = cn;
      if (on) Object.entries(on).forEach(([ev,fn]) => e.addEventListener(ev, fn));
      if (s && typeof s === 'object') Object.assign(e.style, s);
      else if (typeof s === 'string') e.style.cssText = s;
      if (html) { e.innerHTML = html; }
      // Support legacy attrs: { key: val } — extrait et applique via setAttribute
      if (subAttrs && typeof subAttrs === 'object') {
        Object.entries(subAttrs).forEach(([k,v]) => {
          if (v === null || v === undefined || v === false) return;
          if (k === 'disabled' && v) { e.disabled = true; return; }
          if (k === 'id') { e.id = String(v); return; }
          e.setAttribute(k, v);
        });
      }
      Object.entries(rest).forEach(([k,v]) => {
        if (v === null || v === undefined || v === false) return;
        if (k === 'disabled' && v) { e.disabled = true; return; }
        if (k === 'id') { e.id = String(v); return; }
        e.setAttribute(k, v);
      });
    }
    children.flat(Infinity).forEach(c => {
      if (c == null || c === false || c === undefined) return;
      if (c instanceof Node) { e.appendChild(c); return; }
      if (typeof c === 'string' || typeof c === 'number') {
        e.appendChild(document.createTextNode(String(c)));
      }
    });
    return e;
  }

  function _defCloseMroot() {
    const m = document.getElementById('mroot');
    if (m) m.innerHTML = '';
    S.mpModal = null;
    S.pfModal = null;
    S.addPfModalOpen = false;
  }

  // Helpers generiques : delegues tels quels a la page hote.
  // Garde-fou : ne ferme la modale que si le geste COMMENCE ET FINIT sur le
  // fond. Sans ca, un clic-glisse depuis un champ (selection de texte,
  // curseur relache hors du cadre) fermait la modale et perdait la saisie.
  function _bindOverlayDismiss(overlay, onDismiss) {
    let downOnOverlay = false;
    let upOnOverlay = false;
    overlay.addEventListener('mousedown', (e) => { downOnOverlay = (e.target === overlay); });
    overlay.addEventListener('mouseup', (e) => { upOnOverlay = (e.target === overlay); });
    overlay.addEventListener('click', (e) => {
      const ok = downOnOverlay && upOnOverlay && e.target === overlay;
      downOnOverlay = false;
      upOnOverlay = false;
      if (ok) onDismiss();
    });
  }

  function el()         { return (_h().el || _defEl).apply(null, arguments); }
  function api()        { return _h().api.apply(null, arguments); }
  function showToast()  { return _h().showToast.apply(null, arguments); }
  function closeMroot() { return (_h().closeMroot || _defCloseMroot).apply(null, arguments); }
  function fN()         { return (_h().fN || _defFN).apply(null, arguments); }
  function fDateTime()  { return (_h().fDateTime || _defFDateTime).apply(null, arguments); }
  function fU()         { return (_h().fU || _defFU).apply(null, arguments); }
  function getStockEmplacements() { return _h().getStockEmplacements.apply(null, arguments); }
  function fetchPfStockAtEmpl(produitId, empl) { return _h().stockAtEmpl(produitId, empl); }

  // Rechargements post-ecriture : l'hote decide ce qu'il rafraichit. Un hote
  // qui ne connait pas une vue renvoie simplement undefined.
  function loadDashboard()      { return _h().reload('dashboard'); }
  function loadMatieres()       { return _h().reload('matieres'); }
  function loadProduitsFinis()  { return _h().reload('produits-finis'); }
  function loadProduction()     { return _h().reload('production'); }
  function loadInventaireList() { return _h().reload('inventaire'); }
  function loadProduit(id)      { return _h().reload('produit', id); }
  function loadEmplacement(e)   { return _h().reload('emplacement', e); }
  function refreshSelMatiere()  { return _h().reload('sel-matiere'); }
  function loadPageEmplCustom() { return _h().reload('empl-custom'); }

  // --- Etat -------------------------------------------------------------
  // pfModal / mpModal / modalMvt appartiennent aux modales ; les autres champs
  // sont lus (et pour matieres, ecrits) chez l'hote via des accesseurs, ce qui
  // permet de deplacer le code sans y toucher une ligne.
  var _own = { pfModal: null, mpModal: null, modalMvt: null };
  var S = {
    get pfModal()  { return _own.pfModal; },  set pfModal(v)  { _own.pfModal = v; },
    get mpModal()  { return _own.mpModal; },  set mpModal(v)  { _own.mpModal = v; },
    get modalMvt() { return _own.modalMvt; }, set modalMvt(v) { _own.modalMvt = v; },
    get tab()          { return (_h().state() || {}).tab; },
    get selProduit()   { return (_h().state() || {}).selProduit; },
    get selEmpl()      { return (_h().state() || {}).selEmpl; },
    get selMatiere()   { return (_h().state() || {}).selMatiere; },
    get fabStockMode() { return !!(_h().state() || {}).fabStockMode; },
    get matieres()     { return (_h().state() || {}).matieres; },
    set matieres(v)    { _h().setMatieres(v); },
  };

  // Valeurs de configuration, rafraichies a chaque ouverture.
  var _emplListFromDB = [];
  var STOCK_EMPL_AU_SOL = 'Z0';
  var STOCK_EMPL_AU_SOL_LABEL = 'Au sol - a expedier';
  var STOCK_EMPL_SORTIE_PROD = 'Z1';
  var STOCK_EMPL_SORTIE_PROD_LABEL = 'En attente - sortie de prod';
  var STOCK_UNITE_VENTE_DEFAUT = 'etiquette';

  const MP_CAT_LABELS = { mandrin: 'Mandrin', palette: 'Palette', adhesif: 'Adhésif', carton: 'Carton', frontal: 'Frontal', glassine: 'Glassine', complexe: 'Complexe', autre: 'Autre' };

  const MP_MVT_TITLES = {
    entree: 'Entrée en stock',
    sortie: 'Sortie de stock',
    ajustement: 'Ajustement d\'inventaire',
    transfert: 'Transfert',
  };

  const PF_MVT_TITLES = {
    entree: 'Entrée produit fini',
    sortie: 'Sortie produit fini',
  };

  const MP_CATEGORIES_LAIZEES = new Set(['frontal', 'glassine', 'complexe']);

  const _STOCK_ZONES_SPECIALES = [STOCK_EMPL_AU_SOL, STOCK_EMPL_SORTIE_PROD];

  async function submitMouvement(body) {
    try {
      const r = await api('/api/stock/mouvement', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body) });
      if (!r) return;
      if (r.fsc_ecart) {
        showToast('Sortie enregistrée AVEC écart FSC — complément non certifié tracé.', 'error');
      } else {
        showToast('Stock mis à jour → ' + fN(r.quantite_apres));
      }
      S.modalMvt = null;
      S.pfModal = null;
      document.querySelector('.modal-overlay')?.remove();
      closeMroot();
      if (S.selProduit) await loadProduit(S.selProduit.produit.id);
      else if (S.selEmpl) await loadEmplacement(S.selEmpl.emplacement);
      else if (S.tab === 'dashboard') await loadDashboard();
      else if (S.tab === 'produits-finis') await loadProduitsFinis();
      else if (S.tab === 'production') await loadProduction();
      else if (S.tab === 'inventaire') await loadInventaireList();
    } catch(e) {
      // 409 « stock FSC insuffisant » : ce n'est pas une erreur de saisie,
      // c'est un arbitrage. On rouvre la demande avec les chiffres réels et
      // on exige une justification — après quoi le mouvement passe, marqué
      // en écart. Bloquer sèchement immobiliserait l'atelier ; laisser
      // passer en silence rendrait le claim FSC faux.
      if (e && e.status === 409 && e.detail && e.detail.code === 'fsc_stock_insuffisant') {
        openFscEcartModal(body, e.detail);
        return;
      }
      showToast(e.message, 'error');
    }
  }

  // Demande de dérogation FSC : montre l'écart chiffré, impose une
  // justification écrite, puis rejoue le mouvement avec la confirmation.
  function openFscEcartModal(body, detail) {
    document.querySelector('.modal-overlay')?.remove();
    const overlay = el('div', { cls:'modal-overlay' });
    _bindOverlayDismiss(overlay, closeMroot);
    const sheet = el('div', { cls:'modal-sheet', style:{ maxWidth:'480px' } });
    sheet.addEventListener('click', e => e.stopPropagation());

    const noteInp = el('textarea', {
      cls:'field-input',
      attrs:{ rows:'3', placeholder:'Ex : rupture fournisseur, accord client du 12/06, dérogation responsable qualité…' },
      style:{ direction:'ltr', resize:'vertical' },
    });

    const valider = el('button', {
      cls:'btn-confirm',
      style:{ background:'#fb923c', color:'#fff' },
      on:{ click: async () => {
        const note = (noteInp.value || '').trim();
        if (!note) { showToast('Justification obligatoire', 'error'); return; }
        overlay.remove();
        await submitMouvement({ ...body, fsc_ecart_confirme: true, fsc_ecart_note: note });
      }},
    }, 'Confirmer l\'écart et sortir');

    sheet.append(
      el('span', { cls:'modal-handle' }),
      el('div', { cls:'modal-title' }, 'Stock FSC insuffisant'),
      el('div', { cls:'sm-fsc-alert' },
        el('div', { style:{fontWeight:'700', marginBottom:'6px'} },
          fN(detail.dispo_fsc) + ' certifié(s) disponible(s) pour ' + fN(detail.demande) + ' demandé(s).'),
        el('div', null,
          'Compléter avec ' + fN(detail.complement_non_fsc) + ' unité(s) non certifiée(s) rendrait '
          + 'le claim FSC de cette sortie inexact. L\'écart sera enregistré sur le mouvement '
          + 'et apparaîtra dans le traceur de traçabilité.')
      ),
      el('div', { cls:'modal-field', style:{marginTop:'12px'} },
        el('label', { cls:'field-label' }, 'Justification (obligatoire)'),
        noteInp
      ),
      el('div', { cls:'modal-actions', style:{marginTop:'16px'} },
        el('button', { cls:'btn-cancel', type:'button', on:{ click: () => overlay.remove() } }, 'Annuler la sortie'),
        valider
      )
    );
    overlay.appendChild(sheet);
    document.body.appendChild(overlay);
    noteInp.focus();
  }

  function fmtStockParisNow() {
    const d = new Date();
    try {
      const parts = new Intl.DateTimeFormat('fr-FR', {
        timeZone: 'Europe/Paris',
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', hour12: false,
      }).formatToParts(d);
      const g = (t) => (parts.find(p => p.type === t) || {}).value || '';
      return g('day') + '/' + g('month') + '/' + g('year') + ' ' + g('hour') + ':' + g('minute');
    } catch (e) {
      return fDateTime(d.toISOString().slice(0, 16));
    }
  }

  // ══════════════════════════════════════════════════════════════
  // FSC — helpers partagés
  // ══════════════════════════════════════════════════════════════
  // Un lot de produit fini est certifié ou non (booléen hérité du dossier de
  // fabrication). Deux lots d'un même produit peuvent cohabiter au même
  // emplacement : l'API les renvoie sur DEUX lignes distinctes, jamais
  // fusionnées, et ces helpers servent à les distinguer partout de la même
  // manière plutôt que de réécrire un badge par écran.

  function _fscSegSuffix(fscSeg) {
    if (fscSeg === 1) return ' dans le segment certifié FSC';
    if (fscSeg === 0) return ' dans le segment non certifié';
    return ' à cet emplacement';
  }

  // `opts.fsc` : segment de la ligne cliquée (1 = certifié, 0 = non certifié,
  // undefined = emplacement homogène ou appel historique). Il est transmis à
  // l'API pour que le lot déplacé soit celui affiché, et non le plus ancien de
  // l'emplacement tous segments confondus.
  async function openMoveLotModal(produitId, emplacement, qLot, unite, refLabel, nbLots, opts) {
    document.querySelector('.modal-overlay')?.remove();

    const fscSeg = (opts && opts.fsc != null) ? (opts.fsc ? 1 : 0) : null;
    const qLabel = fU(qLot, unite || '');
    const locLbl = stockEmplLabel(emplacement);
    const loc = refLabel ? (refLabel + ' · ' + locLbl) : locLbl;
  
    const overlay = el('div', { cls: 'modal-overlay' });
    _bindOverlayDismiss(overlay, closeMroot);
    const sheet = el('div', { cls:'modal-sheet', style: { maxWidth: '480px' } });
    sheet.addEventListener('click', e => e.stopPropagation());
  
    // Destination emplacement input with suggestions
    const destEmplInp = el('input', { 
      cls:'field-input', 
      type:'text', 
      placeholder:'Emplacement destination (ex. A001)', 
      autocomplete:'off',
      style:{direction:'ltr', textTransform:'uppercase'}
    });
    const suggWrap = el('div', { cls:'empl-suggestions', style:{position:'absolute', top:'100%', left:'0', right:'0', zIndex:'120'} });
    const destError = el('div', { cls:'field-error', style:{color:'var(--danger)',fontSize:'12px',marginTop:'4px',display:'none'} });
  
    let destTimer = null;
    let selectedDestEmpl = null;
  
    destEmplInp.addEventListener('input', () => {
      selectedDestEmpl = null;
      destError.style.display = 'none';
      clearTimeout(destTimer);
      const q = destEmplInp.value.trim().toUpperCase();
      if (!q) { suggWrap.innerHTML = ''; suggWrap.style.display = 'none'; return; }
      destTimer = setTimeout(() => {
        const empls = getStockEmplacements();
        const filtered = empls.filter(e => e.includes(q)).slice(0, 8);
        suggWrap.innerHTML = '';
        if (!filtered.length) { suggWrap.style.display = 'none'; return; }
        filtered.forEach(code => {
          const _dCls = 'empl-suggest-item' + (isStockEmplacementAuSol(code) ? ' empl-suggest-au-sol' : isStockEmplacementSortieProd(code) ? ' empl-suggest-sortie-prod' : '');
          const _dTxt = isStockEmplacementAuSol(code) ? (STOCK_EMPL_AU_SOL_LABEL + ' — stock à expédier') : isStockEmplacementSortieProd(code) ? STOCK_EMPL_SORTIE_PROD_LABEL : code;
          const row = el('div', { cls: _dCls,
            on:{ click: () => {
              destEmplInp.value = code;
              selectedDestEmpl = code;
              suggWrap.innerHTML = '';
              suggWrap.style.display = 'none';
            }}
          }, _dTxt);
          suggWrap.appendChild(row);
        });
        suggWrap.style.display = '';
      }, 150);
    });
  
    const confirmBtn = el('button', { 
      cls:'btn-confirm', 
      style:{background:'var(--violet)', color:'#fff'},
      on:{ click: async () => {
        const destEmpl = (destEmplInp.value.trim().toUpperCase() || selectedDestEmpl);
        if (!destEmpl) { showToast('Emplacement destination requis', 'error'); return; }
        if (destEmpl === emplacement) { showToast('Même emplacement que la source', 'error'); return; }
      
        // Confirmation modal
        const confirmOverlay = el('div', { cls:'modal-overlay', on:{ click: e => { if(e.target===confirmOverlay) closeMroot(); }}});
        const confirmSheet = el('div', { cls:'modal-sheet', style: { maxWidth: '420px' } });
        confirmSheet.addEventListener('click', e => e.stopPropagation());
      
        const qtyHighlight = el('span', { style:{fontWeight:'800', fontSize:'18px', color:'var(--violet)'} }, qLabel);
        const destHighlight = el('span', { style:{fontWeight:'700', color:'var(--violet)'} }, stockEmplLabel(destEmpl));
      
        confirmSheet.appendChild(el('div', { cls:'modal-title' }, 'Confirmer le déplacement'));
        confirmSheet.appendChild(el('div', { cls:'modal-sub' }, 
          'Déplacer ', qtyHighlight, ' vers ', destHighlight, ' ?'
        ));
        if (nbLots > 1) {
          confirmSheet.appendChild(el('div', { cls:'mp-hint', style:{marginTop:'8px'} },
            nbLots + ' lots actifs' + _fscSegSuffix(fscSeg) + ' — seul le plus ancien sera déplacé.'
          ));
        }
        if (fscSeg === 1) {
          confirmSheet.appendChild(el('div', { cls:'mp-hint sm-fsc-hint', style:{marginTop:'8px'} },
            'Le claim FSC et le dossier d\'origine suivent la palette : elle reste certifiée à destination.'
          ));
        }
      
        confirmSheet.appendChild(el('div', { cls:'modal-actions', style:{marginTop:'20px'} },
          el('button', { cls:'btn-cancel', type:'button', on:{ click:() => confirmOverlay.remove() } }, 'Annuler'),
          el('button', {
            cls:'btn-confirm',
            style:{background:'var(--violet)', color:'#fff'},
            on:{ click: async () => {
              try {
                const r = await api('/api/stock/deplacer-lot', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    produit_id: produitId,
                    emplacement_source: emplacement,
                    emplacement_destination: destEmpl,
                    ...(fscSeg != null ? { fsc: fscSeg } : {}),
                  }),
                });
                if (!r) return;
                showToast('Lot déplacé — stock : ' + fN(r.quantite_apres));
                confirmOverlay.remove();
                overlay.remove();
                if (S.selProduit) await loadProduit(S.selProduit.produit.id);
                else if (S.selEmpl) await loadEmplacement(S.selEmpl.emplacement);
                else if (S.tab === 'produits-finis') await loadProduitsFinis();
                else if (S.tab === 'production') await loadProduction();
                else if (S.tab === 'dashboard') await loadDashboard();
              } catch (e) { showToast(e.message, 'error'); }
            }}
          }, 'Faire le déplacement')
        ));
      
        confirmOverlay.appendChild(confirmSheet);
        document.body.appendChild(confirmOverlay);
      }}
    }, 'Déplacer');
  
    const destField = el('div', { cls:'modal-field', style:{position:'relative'} },
      el('label', { cls:'field-label' }, 'Emplacement destination'),
      destEmplInp,
      suggWrap,
      destError
    );
  
    sheet.appendChild(el('div', { cls:'modal-title' },
      'Déplacer le lot',
      fscSeg === 1 ? el('span', { cls:'sm-fsc-badge', style:{marginLeft:'8px'} }, 'FSC') : null
    ));
    sheet.appendChild(el('div', { cls:'modal-sub' },
      'Déplacer ', el('span', { style:{fontWeight:'700', fontSize:'16px', color:'var(--violet)'} }, qLabel),
      ' depuis ', el('span', { style:{fontWeight:'600'} }, loc)
    ));
    if (nbLots > 1) {
      sheet.appendChild(el('div', { cls:'mp-hint', style:{marginTop:'8px'} },
        nbLots + ' lots actifs' + _fscSegSuffix(fscSeg) + ' — seul le plus ancien sera déplacé.'
      ));
    }
    sheet.appendChild(destField);
    sheet.appendChild(el('div', { cls:'modal-actions', style:{marginTop:'20px'} },
      el('button', { cls:'btn-cancel', type:'button', on:{ click:() => overlay.remove() } }, 'Annuler'),
      confirmBtn
    ));
  
    overlay.appendChild(sheet);
    document.body.appendChild(overlay);
    destEmplInp.focus();
  }

  async function sortirLot(produitId, emplacement, qLot, unite, refLabel, nbLots, opts) {
    const expedition = !!(opts && opts.expedition);
    const fscSeg = (opts && opts.fsc != null) ? (opts.fsc ? 1 : 0) : null;
    const qLabel = fU(qLot, unite || '');
    const locLbl = stockEmplLabel(emplacement);
    const loc = refLabel ? (refLabel + ' · ' + locLbl) : locLbl;
    const segLbl = fscSeg === 1 ? ' [FSC]' : '';
    let msg = expedition
      ? ('Expédition transporteur — sortir le lot FIFO' + segLbl + ' (' + qLabel + ') — ' + loc + ' ?')
      : ('Sortir le lot FIFO' + segLbl + ' (' + qLabel + ') — ' + loc + ' ?');
    if (nbLots > 1) {
      msg += '\n\n' + nbLots + ' lots actifs' + _fscSegSuffix(fscSeg) + ' — seul le plus ancien sera retiré.';
    }
    if (!confirm(msg)) return;
    const payload = { produit_id: produitId, emplacement };
    // Sans `fsc`, l'API sortirait le lot le plus ancien tous segments
    // confondus — c'est-à-dire potentiellement du certifié alors que
    // l'opérateur a cliqué sur la ligne non certifiée.
    if (fscSeg != null) payload.fsc = fscSeg;
    if (expedition) {
      payload.note = 'Expédition transporteur — ' + fmtStockParisNow();
    }
    try {
      const r = await api('/api/stock/sortir-lot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!r) return;
      showToast(expedition ? 'Lot expédié — stock : ' + fN(r.quantite_apres) : 'Lot sorti — stock : ' + fN(r.quantite_apres));
      if (S.selProduit) await loadProduit(S.selProduit.produit.id);
      else if (S.selEmpl) await loadEmplacement(S.selEmpl.emplacement);
      else if (S.tab === 'produits-finis') await loadProduitsFinis();
      else if (S.tab === 'production') await loadProduction();
      else if (S.tab === 'dashboard') await loadDashboard();
    } catch (e) { showToast(e.message, 'error'); }
  }

  function allPageEmplacementChoices() {
    const base = [...new Set([..._emplListFromDB, ...loadPageEmplCustom()])]
      .filter(c => !_STOCK_ZONES_SPECIALES.includes(c))
      .sort();
    return [..._STOCK_ZONES_SPECIALES, ...base];
  }

  function isStockEmplacementAuSol(code) {
    return String(code || '').trim().toUpperCase() === STOCK_EMPL_AU_SOL;
  }

  function isStockEmplacementSortieProd(code) {
    return String(code || '').trim().toUpperCase() === STOCK_EMPL_SORTIE_PROD;
  }

  function isStockZoneSpeciale(code) {
    return _STOCK_ZONES_SPECIALES.includes(String(code || '').trim().toUpperCase());
  }

  function isStockEmplacementCode(s) {
    if (isStockZoneSpeciale(s)) return true;
    const t = String(s || '').trim().toUpperCase();
    if (t.length < 2) return false;
    const c0 = t.charCodeAt(0);
    if (c0 < 65 || c0 > 90) return false;
    for (let i = 1; i < t.length; i++) {
      const c = t.charCodeAt(i);
      if (c < 48 || c > 57) return false;
    }
    return true;
  }

  function stockEmplLabel(code) {
    if (isStockEmplacementAuSol(code)) return STOCK_EMPL_AU_SOL_LABEL;
    if (isStockEmplacementSortieProd(code)) return STOCK_EMPL_SORTIE_PROD_LABEL;
    return String(code || '').trim().toUpperCase();
  }

  async function resolvePfProduitByRef(ref) {
    const term = String(ref || '').trim();
    if (!term) return null;
    const upper = term.toUpperCase();
    try {
      const r = await api('/api/stock/search?q=' + encodeURIComponent(term) + '&limit=15');
      const list = (r && r.produits) ? r.produits : [];
      let found = list.find(p => String(p.reference || '').toUpperCase() === upper);
      if (found) return found;
      if (list.length === 1) return list[0];
      const rows = await api('/api/stock/produits?q=' + encodeURIComponent(term) + '&limit=15');
      const arr = Array.isArray(rows) ? rows : [];
      found = arr.find(p => String(p.reference || '').toUpperCase() === upper);
      if (found) return found;
      return arr.length === 1 ? arr[0] : null;
    } catch (e) {
      return null;
    }
  }

  function wireStockProduitSearch(refInp, suggWrap, onSelect) {
    let timer = null;
    const runSearch = async (q) => {
      if (!q || q.length < 1) {
        suggWrap.innerHTML = '';
        return;
      }
      try {
        const r = await api('/api/stock/search?q=' + encodeURIComponent(q) + '&limit=8');
        const list = (r && r.produits) ? r.produits : [];
        suggWrap.innerHTML = '';
        if (!list.length) {
          suggWrap.appendChild(el('div', { cls: 'empl-sugg-item muted' }, 'Aucun résultat pour « ' + q + ' »'));
          suggWrap.style.display = 'block';
          return;
        }
        list.forEach(p => {
          const label = (p.reference || '') + (p.designation ? ' — ' + p.designation : '');
          const unite = String(p.unite || '').trim();
          const row = el('div', {
            cls: 'empl-sugg-item empl-sugg-item-with-unit',
            on: { mousedown: (e) => { e.preventDefault(); onSelect(p); } },
          },
            el('span', { cls: 'empl-sugg-item-label' }, label),
            unite ? el('span', { cls: 'empl-sugg-item-unit-badge' }, unite) : null,
          );
          suggWrap.appendChild(row);
        });
        suggWrap.style.display = 'block';
      } catch (e) {
        suggWrap.innerHTML = '';
        suggWrap.style.display = 'none';
      }
    };
    refInp.addEventListener('input', () => {
      clearTimeout(timer);
      timer = setTimeout(() => runSearch(refInp.value.trim()), 220);
    });
    refInp.addEventListener('focus', () => {
      runSearch(refInp.value.trim());
    });
    refInp.addEventListener('keydown', async (e) => {
      if (e.key !== 'Enter') return;
      e.preventDefault();
      const p = await resolvePfProduitByRef(refInp.value);
      if (p) onSelect(p);
      else showToast('Référence introuvable.', 'error');
    });
    refInp.addEventListener('blur', () => {
      setTimeout(() => {
        if (document.activeElement === refInp) return;
        suggWrap.innerHTML = '';
        suggWrap.style.display = 'none';
      }, 220);
    });
  }

  function wireStockEmplSearch(emplInp, suggWrap) {
    let timer = null;
    const pick = (code) => {
      emplInp.value = String(code || '').toUpperCase();
      suggWrap.innerHTML = '';
      suggWrap.style.display = 'none';
    };
    const renderList = (codes) => {
      suggWrap.innerHTML = '';
      if (!codes.length) {
        suggWrap.appendChild(el('div', { cls: 'empl-sugg-item muted' }, 'Aucun emplacement'));
        suggWrap.style.display = 'block';
        return;
      }
      codes.forEach(code => {
        suggWrap.appendChild(el('div', {
          cls: 'empl-sugg-item',
          on: { mousedown: (e) => { e.preventDefault(); pick(code); } },
        }, stockEmplLabel(code)));
      });
      suggWrap.style.display = 'block';
    };
    const runLocal = (q) => {
      const qq = String(q || '').trim().toUpperCase();
      if (!qq) return allPageEmplacementChoices().slice(0, 12);
      return allPageEmplacementChoices().filter(c => c.includes(qq)).slice(0, 12);
    };
    const runSearch = async (q) => {
      const local = runLocal(q);
      if (!q) {
        renderList(local);
        return;
      }
      renderList(local);
      try {
        const r = await api('/api/stock/search?q=' + encodeURIComponent(q) + '&limit=8');
        const fromApi = (r?.emplacements || []).map(e => e.emplacement);
        renderList([...new Set([...local, ...fromApi])].slice(0, 12));
      } catch (e) {
        renderList(local);
      }
    };
    emplInp.addEventListener('focus', () => {
      runSearch(emplInp.value.trim());
    });
    emplInp.addEventListener('input', () => {
      emplInp.value = emplInp.value.toUpperCase();
      const q = emplInp.value.trim();
      clearTimeout(timer);
      timer = setTimeout(() => runSearch(q), 180);
    });
    emplInp.addEventListener('blur', () => {
      setTimeout(() => {
        if (document.activeElement === emplInp) return;
        suggWrap.innerHTML = '';
        suggWrap.style.display = 'none';
      }, 220);
    });
  }

  function mpCategorieKey(cat) {
    return String(cat || '').trim().toLowerCase();
  }

  function mpCtx(catOrMatiere) {
    if (catOrMatiere && typeof catOrMatiere === 'object') {
      return {
        categorie: mpCategorieKey(catOrMatiere.categorie),
        palettes_par_pile: parseFloat(catOrMatiere.palettes_par_pile) || 0,
        couleur: (catOrMatiere.couleur || '').trim(),
      };
    }
    return { categorie: mpCategorieKey(catOrMatiere), palettes_par_pile: 0, couleur: '' };
  }

  function mpIsBobineCategory(catOrMatiere) {
    const c = mpCtx(catOrMatiere).categorie;
    return c === 'frontal' || c === 'glassine' || c === 'complexe';
  }

  function mpIsAdhesifCategory(catOrMatiere) {
    return mpCtx(catOrMatiere).categorie === 'adhesif';
  }

  function mpUniteNom(catOrMatiere) {
    const c = mpCtx(catOrMatiere).categorie;
    if (mpIsBobineCategory(c)) return 'bobine';
    // Adhésif : le stock se tient au kilo. Palette et carton restent des unités
    // de SAISIE, converties côté serveur à la validation du mouvement.
    if (c === 'adhesif') return 'kg';
    if (c === 'carton') return 'palette';
    if (c === 'palette') return 'palette';
    if (c === 'autre') return 'unite';
    return 'palette';
  }

  function mpUniteShort(catOrMatiere) {
    const u = mpUniteNom(catOrMatiere);
    if (u === 'bobine') return 'bob.';
    if (u === 'palette') return 'pal.';
    if (u === 'kg') return 'kg';
    if (u === 'unite') return 'u.';
    return 'pal.';
  }

  function mpQuantiteFieldLabel(catOrMatiere, uniteSaisie) {
    if (uniteSaisie === 'palette') return 'Quantité (palettes)';
    if (uniteSaisie === 'carton') return 'Quantité (cartons)';
    const u = mpUniteNom(catOrMatiere);
    if (u === 'bobine') return 'Quantité (bobines)';
    if (u === 'palette') return 'Quantité (palettes)';
    if (u === 'kg') return 'Quantité (kg)';
    if (u === 'unite') return 'Quantité (unités)';
    return 'Quantité (palettes)';
  }

  function mpStockLine(qty, catOrMatiere) {
    const ctx = mpCtx(catOrMatiere);
    return fN(qty) + ' ' + mpUniteShort(ctx);
  }

  // ── Unités de saisie des adhésifs ───────────────────────────────────────
  // Le stock est en kg ; l'opérateur, lui, manipule des palettes complètes et
  // rend des palettes entamées. On lui laisse donc choisir son unité, et on
  // convertit. Palette et carton ne sont proposés que si le conditionnement
  // correspondant est renseigné : convertir sans savoir combien pèse une palette
  // produirait un stock faux et silencieux.
  const MP_UNITE_SAISIE_LABELS = { kg: 'Kilos', carton: 'Cartons', palette: 'Palettes' };

  function mpUnitesSaisie(matiere) {
    if (!matiere || !mpIsAdhesifCategory(matiere)) return [];
    if (Array.isArray(matiere.unites_saisie) && matiere.unites_saisie.length) {
      return matiere.unites_saisie;
    }
    const out = ['kg'];
    if (Number(matiere.kg_par_carton) > 0) out.push('carton');
    if (Number(matiere.kg_par_palette || matiere.unites_par_palette || 0) > 0) out.push('palette');
    return out;
  }

  function mpFacteurSaisie(matiere, unite) {
    if (!matiere) return 1;
    if (unite === 'carton') return Number(matiere.kg_par_carton) || 0;
    if (unite === 'palette') {
      return Number(matiere.kg_par_palette || matiere.unites_par_palette || 0);
    }
    return 1;
  }

  // Unité pré-sélectionnée, choisie d'après le geste réel plutôt que d'après
  // l'unité de stock :
  //  - sortie : toujours la palette. En atelier comme en logistique, on sort une
  //    palette complète.
  //  - entrée en fabrication : le carton. L'opérateur ne réceptionne pas, il
  //    remet en stock ce qu'il n'a pas consommé, c'est-à-dire des cartons entiers
  //    d'une palette entamée.
  //  - entrée hors fabrication : la palette. C'est une réception fournisseur sur BL.
  // Le kilo reste le repli quand le conditionnement visé n'est pas renseigné, et
  // le sélecteur reste modifiable dans tous les cas (pas de verrou : il faut
  // pouvoir saisir une pesée exacte sur un fond de palette).
  function mpUniteSaisieDefaut(typeMvt, unites) {
    const pref = (typeMvt === 'entree' && S.fabStockMode)
      ? ['carton', 'palette', 'kg']
      : ['palette', 'carton', 'kg'];
    return pref.find(u => unites.includes(u)) || unites[0] || 'kg';
  }

  function mpQuantiteInputAttrs(catOrMatiere, uniteSaisie) {
    const c = mpCtx(catOrMatiere).categorie;
    if (c === 'palette') return { type: 'number', min: '40', step: '1' };
    if (c === 'adhesif') {
      // Au kilo, le décimal est nécessaire (retour d'une palette entamée) ;
      // à la palette ou au carton, seules les unités entières ont un sens.
      if (uniteSaisie === 'palette' || uniteSaisie === 'carton') {
        return { type: 'number', min: '1', step: '1' };
      }
      return { type: 'number', min: '0', step: '0.1' };
    }
    if (mpIsBobineCategory(c) || c === 'mandrin' || c === 'carton') {
      return { type: 'number', min: '1', step: '1' };
    }
    if (c === 'autre') return { type: 'number', min: '0', step: '1' };
    return { type: 'number', min: '0.5', step: '0.5' };
  }

  function mpIsPaletteCategory(catOrMatiere) {
    return mpCtx(catOrMatiere).categorie === 'palette';
  }

  function mpIsLaizeeCategory(cat) {
    return MP_CATEGORIES_LAIZEES.has((cat || '').toLowerCase());
  }

  function buildMpEmplacementField() {
    const emplInp = el('input', {
      cls: 'field-input empl-upper',
      attrs: {
        type: 'text',
        placeholder: 'Emplacement (ex. A121, ' + STOCK_EMPL_AU_SOL + ', ' + STOCK_EMPL_SORTIE_PROD + ')…',
        autocomplete: 'off',
      },
      style: { direction: 'ltr' },
    });
    const suggWrap = el('div', { cls: 'empl-suggestions', style: { display: 'none' } });
    wireStockEmplSearch(emplInp, suggWrap);
    const combo = el('div', { cls: 'empl-combo-wrap' }, emplInp, suggWrap);
    const wrap = el('div', { cls: 'mp-field empl-field-wrap' },
      el('label', null, 'Emplacement'),
      combo,
    );
    return { wrap, emplInp };
  }

  function mpEmplacementValue(emplInp) {
    return String(emplInp?.value || '').trim().toUpperCase();
  }

  function validateMpEmplacement(empl) {
    // Emplacement optionnel pour toutes les matières premières : vide = OK.
    // Si présent, on vérifie le format (grille A121, zone au sol ou sortie prod).
    if (!empl) return null;
    if (!isStockEmplacementCode(empl)) {
      return 'Format invalide — grille (ex. A123), « ' + STOCK_EMPL_AU_SOL_LABEL + ' » (' + STOCK_EMPL_AU_SOL + ') ou « ' + STOCK_EMPL_SORTIE_PROD_LABEL + ' » (' + STOCK_EMPL_SORTIE_PROD + ').';
    }
    return null;
  }

  function openModalMouvement(type, matiere) {
    (async () => {
      if (!S.matieres) {
        try {
          const d = await api('/api/stock/matieres');
          S.matieres = Array.isArray(d) ? d : [];
        } catch (e) {
          S.matieres = [];
        }
      }
      renderMpMouvementModal(type, matiere);
    })();
  }

  // Construit le couple « unité de saisie + quantité » d'un mouvement.
  //
  // Cas général : un seul champ quantité, dans l'unité de gestion de la matière.
  // Adhésifs : un sélecteur palette / carton / kg pilote le champ quantité. Le pas
  // et le libellé s'adaptent, et une ligne d'équivalence rappelle en permanence ce
  // que la saisie représente en kilos — c'est le seul garde-fou visuel contre une
  // sortie de 2 kg saisie à la place de 2 palettes.
  //
  // Retourne { wrap, qInp, getUnite, getQuantiteGestion, refresh }.
  function buildMpQuantiteField(mat, typeMvt, extraChildren) {
    const unites = mpUnitesSaisie(mat);
    const multi = unites.length > 1;
    let unite = multi ? mpUniteSaisieDefaut(typeMvt, unites) : (unites[0] || null);

    const labelEl = el('label', null, mpQuantiteFieldLabel(mat, unite));
    const qInp = el('input', { attrs: mpQuantiteInputAttrs(mat, unite) });
    const equivEl = el('div', {
      cls: 'mp-hint',
      style: 'font-size:11px;color:var(--muted);margin-top:4px',
    }, '');

    function refreshEquivalence() {
      if (!multi || unite === 'kg') { equivEl.style.display = 'none'; return; }
      const f = mpFacteurSaisie(mat, unite);
      const q = parseFloat(qInp.value);
      equivEl.style.display = '';
      if (!f) { equivEl.textContent = ''; return; }
      const base = '1 ' + (unite === 'palette' ? 'palette' : 'carton') + ' = ' + fN(f) + ' kg';
      equivEl.textContent = (!q || q <= 0) ? base : (base + ' · soit ' + fN(q * f) + ' kg');
    }

    const uniteSel = multi ? el('select', { id: 'mp-modal-unite-saisie' }) : null;
    if (uniteSel) {
      unites.forEach(u => uniteSel.appendChild(el('option', {
        value: u, selected: u === unite ? true : null,
      }, MP_UNITE_SAISIE_LABELS[u] || u)));
      uniteSel.value = unite;
      uniteSel.addEventListener('change', () => {
        unite = uniteSel.value;
        labelEl.textContent = mpQuantiteFieldLabel(mat, unite);
        const attrs = mpQuantiteInputAttrs(mat, unite);
        Object.entries(attrs).forEach(([k, v]) => qInp.setAttribute(k, v));
        qInp.value = '';
        refreshEquivalence();
        if (typeof qInp._onMpUniteChange === 'function') qInp._onMpUniteChange();
      });
    }
    qInp.addEventListener('input', refreshEquivalence);
    refreshEquivalence();

    const children = [labelEl, qInp, equivEl].concat(extraChildren || []);
    const wrap = el('div', null,
      uniteSel
        ? el('div', { cls: 'mp-field' }, el('label', null, 'Unité de saisie'), uniteSel)
        : null,
      el('div', { cls: 'mp-field' }, ...children),
    );

    return {
      wrap,
      qInp,
      getUnite: () => (multi ? unite : null),
      // Quantité convertie dans l'unité de gestion — sert aux contrôles côté client
      // (stock insuffisant). La conversion qui fait foi reste celle du serveur.
      getQuantiteGestion: () => {
        const q = parseFloat(qInp.value);
        if (isNaN(q)) return NaN;
        return multi ? q * (mpFacteurSaisie(mat, unite) || 1) : q;
      },
      refresh: refreshEquivalence,
    };
  }

  // « Stock actuel : 1 200 kg » avec la valeur en gras (demande produit : la
  // quantité et son unité doivent sauter aux yeux avant la saisie).
  function mpStockActuelHint(stockActuel, mpCat) {
    return el('div', { cls: 'mp-hint' },
      'Stock actuel : ',
      el('strong', { style: 'color:var(--text);font-weight:800' }, mpStockLine(stockActuel, mpCat)),
    );
  }

  function renderMpMouvementModal(type, matiere, categorieFilter) {
    const typeMvt = (type || 'entree').toLowerCase();
    const allList = (S.matieres || []).filter(m => m.actif !== 0);
    let mat = matiere || null;
    // Catégorie du filtre : priorité au paramètre, sinon catégorie de la matière sélectionnée
    let cat = (categorieFilter != null) ? String(categorieFilter || '').toLowerCase() : null;
    if (cat == null && mat) cat = mpCategorieKey(mat.categorie);
    if (cat == null) cat = '';
    // Liste filtrée par catégorie (vide = toutes)
    const list = cat
      ? allList.filter(m => mpCategorieKey(m.categorie) === cat)
      : allList;
    // Si la matière courante ne matche plus le filtre, on la désélectionne
    if (mat && cat && mpCategorieKey(mat.categorie) !== cat) mat = null;
    if (!mat && list.length === 1) mat = list[0];
    closeMroot();
    const mroot = document.getElementById('mroot');
    if (!mroot) return;
    S.mpModal = {
      type: typeMvt, matiere: mat, matiereId: mat ? mat.id : null,
      categorie: cat || (mat ? mpCategorieKey(mat.categorie) : ''),
      laizeId: null,
    };
    const stockActuel = mat ? (parseFloat(mat.quantite) || 0) : 0;
    const mpCat = mat || list.find(x => x.id === S.mpModal.matiereId) || null;

    const overlay = el('div', { cls: 'mp-modal-overlay' });
    _bindOverlayDismiss(overlay, closeMroot);
    const headTypeCls = ['entree', 'sortie', 'ajustement', 'transfert'].includes(typeMvt) ? typeMvt : '';
    const box = el('div', { cls: 'mp-modal mp-modal-mvt' });
    box.appendChild(el('div', { cls: 'mp-modal-mvt-head mp-modal-mvt-head-' + headTypeCls },
      el('h3', null, MP_MVT_TITLES[typeMvt] || typeMvt),
      el('button', {
        cls: 'mp-modal-close',
        type: 'button',
        attrs: { title: 'Fermer', 'aria-label': 'Fermer' },
        on: { click: closeMroot },
      }, '×'),
    ));
    const body = el('div', { cls: 'mp-modal-mvt-body' });

    // Sélecteur de type de MP (catégorie) — toujours présent, et présélectionné
    // sur la catégorie de la matière quand le mouvement part d'une fiche matière.
    // NB : 'complexe' et 'autre' manquaient à cette liste, si bien qu'un mouvement
    // ouvert depuis un complexe retombait sur « — Tous les types — ».
    const catSel = el('select', { id: 'mp-modal-categorie-select' });
    catSel.appendChild(el('option', { value: '' }, '— Tous les types —'));
    const CAT_ORDER = ['frontal', 'glassine', 'complexe', 'mandrin', 'adhesif', 'carton', 'palette', 'autre'];
    CAT_ORDER.forEach(c => {
      catSel.appendChild(el('option', {
        value: c,
        selected: S.mpModal.categorie === c ? true : null,
      }, MP_CAT_LABELS[c] || c));
    });
    // Filet de sécurité : si la catégorie courante n'est pas dans CAT_ORDER (future
    // catégorie ajoutée en base), on force quand même la valeur du select.
    if (S.mpModal.categorie) catSel.value = S.mpModal.categorie;
    catSel.addEventListener('change', () => {
      renderMpMouvementModal(typeMvt, null, catSel.value || '');
    });
    body.appendChild(el('div', { cls: 'mp-field' },
      el('label', null, 'Type de matière'),
      catSel,
    ));

    if (mat) {
      body.appendChild(el('div', { cls: 'mp-field' },
        el('label', null, 'Matière'),
        el('div', { cls: 'mp-readonly' }, (mat.reference || '') + ' — ' + (mat.designation || '')),
        el('div', { style: { marginTop: '6px' } },
          el('button', {
            cls: 'btn-ghost', type: 'button',
            style: { fontSize: '11px', padding: '4px 8px', border: '1px solid var(--border)',
                     borderRadius: '6px', background: 'transparent', color: 'var(--muted)',
                     cursor: 'pointer', fontFamily: 'inherit' },
            on: { click: () => renderMpMouvementModal(typeMvt, null, S.mpModal.categorie || '') },
          }, '× Changer de matière'),
        ),
      ));
      // Sélecteur de laize pour les matières laizées
      if (mpIsLaizeeCategory(mat.categorie) && Array.isArray(mat.stock_par_laize) && mat.stock_par_laize.length > 0) {
        const laizeSel = el('select', { id: 'mp-modal-laize-select' });
        laizeSel.appendChild(el('option', { value: '' }, '— Choisir la laize —'));
        mat.stock_par_laize.forEach(spl => {
          laizeSel.appendChild(el('option', {
            value: String(spl.laize_id),
            selected: S.mpModal.laizeId === spl.laize_id ? true : null,
          }, (spl.label || (spl.valeur_mm + ' mm')) + ' (stock ' + fN(spl.quantite) + ' bob.)'));
        });
        laizeSel.addEventListener('change', () => {
          const v = parseInt(laizeSel.value, 10);
          S.mpModal.laizeId = v || null;
        });
        body.appendChild(el('div', { cls: 'mp-field' }, el('label', null, 'Laize'), laizeSel));
      } else if (mpIsLaizeeCategory(mat.categorie)) {
        body.appendChild(el('div', {
          cls: 'mp-hint err',
          style: 'background:rgba(251,146,60,0.10);border:1px solid rgba(251,146,60,0.4);padding:8px 10px;border-radius:8px;color:var(--text)' },
          'Aucune laize associée à cette matière. Édite-la pour ajouter ses laizes avant de saisir un mouvement.'));
      }
    } else {
      const sel = el('select', { id: 'mp-modal-matiere-select' });
      const placeholder = list.length
        ? '— Choisir une matière —'
        : (cat ? 'Aucune matière dans cette catégorie' : '— Choisir une matière —');
      sel.appendChild(el('option', { value: '' }, placeholder));
      // Pour les matières laizées, on déplie chaque référence par laize associée
      list.forEach(item => {
        if (item.laizee && Array.isArray(item.stock_par_laize) && item.stock_par_laize.length > 0) {
          item.stock_par_laize.forEach(spl => {
            const val = String(item.id) + ':' + String(spl.laize_id);
            const isSel = (S.mpModal.matiereId === item.id && S.mpModal.laizeId === spl.laize_id);
            sel.appendChild(el('option', { value: val, selected: isSel ? true : null },
              item.reference + ' — ' + (spl.label || (spl.valeur_mm + ' mm')) + ' (' + fN(spl.quantite) + ' bob.)',
            ));
          });
        } else {
          sel.appendChild(el('option', {
            value: String(item.id),
            selected: S.mpModal.matiereId === item.id ? true : null,
          }, item.reference + ' — ' + item.designation));
        }
      });
      sel.addEventListener('change', () => {
        const raw = sel.value;
        if (!raw) { renderMpMouvementModal(typeMvt, null, S.mpModal.categorie || ''); return; }
        const parts = raw.split(':');
        const id = parseInt(parts[0], 10);
        const laizeId = parts.length > 1 ? parseInt(parts[1], 10) : null;
        const found = list.find(x => x.id === id);
        if (found && laizeId) {
          S.mpModal.laizeId = laizeId;
          renderMpMouvementModal(typeMvt, found || null, S.mpModal.categorie || '');
          if (S.mpModal) S.mpModal.laizeId = laizeId;
        } else {
          S.mpModal.laizeId = null;
          renderMpMouvementModal(typeMvt, found || null, S.mpModal.categorie || '');
        }
      });
      body.appendChild(el('div', { cls: 'mp-field' }, el('label', null, 'Matière / laize'), sel));
    }

    const errEl = el('div', { cls: 'mp-hint err', style: { display: 'none' } }, '');

    if (typeMvt === 'entree') {
      const isLaizeeCat = mpIsLaizeeCategory(S.mpModal.categorie) || (mat && mpIsLaizeeCategory(mat.categorie));
      const blInp = el('input', { attrs: { type: 'text', placeholder: 'BL-2024-001' } });
      // Les matières premières ne se gèrent plus par emplacement : plus de champ.
      const qField = buildMpQuantiteField(mpCat, 'entree');
      const qInp = qField.qInp;
      // Prix €/m² de la réception — uniquement pour bobines laizées
      const showPrix = isLaizeeCat && !!mat;
      const prixInp = showPrix ? el('input', {
        attrs: { type: 'number', min: '0', step: '0.0001', placeholder: 'Ex. 0,0550' }
      }) : null;
      const prixHint = showPrix ? el('div', { cls: 'mp-hint',
        style: 'font-size:11px;color:var(--muted);margin-top:4px;line-height:1.4' }, '') : null;
      function computeCurrentPrix() {
        if (!mat) return 0;
        const parLaize = !!mat.prix_par_laize;
        if (parLaize && S.mpModal.laizeId && Array.isArray(mat.stock_par_laize)) {
          const spl = mat.stock_par_laize.find(s => s.laize_id === S.mpModal.laizeId);
          return spl && spl.prix_eur_m2 != null ? parseFloat(spl.prix_eur_m2) : 0;
        }
        return parseFloat(mat.prix_eur_m2 || 0);
      }
      function refreshPrixHint() {
        if (!prixHint) return;
        const p = computeCurrentPrix();
        const modeTxt = mat.prix_par_laize ? ' (par laize)' : ' (matière)';
        if (p > 0) {
          prixHint.textContent = 'Prix courant' + modeTxt + ' : ' + p.toLocaleString('fr-FR', { minimumFractionDigits: 4, maximumFractionDigits: 4 })
            + ' €/m². Laisser vide pour le conserver, sinon le PMP sera recalculé automatiquement.';
        } else {
          prixHint.textContent = 'Aucun prix courant enregistré. Si tu saisis un prix, il devient le prix de référence.';
        }
      }
      body.appendChild(el('div', { cls: 'mp-field' },
        el('label', null, 'Référence BL / Fournisseur'),
        blInp,
      ));
      body.appendChild(qField.wrap);
      if (prixInp) {
        body.appendChild(el('div', { cls: 'mp-field' },
          el('label', null, 'Prix €/m² de cette réception'),
          prixInp,
          prixHint,
        ));
        refreshPrixHint();
        // Le hint dépend de la laize choisie — on la met à jour au change
        const laizeSelEl = body.querySelector('#mp-modal-laize-select');
        if (laizeSelEl) laizeSelEl.addEventListener('change', refreshPrixHint);
      }
      S.mpModal.getBody = () => {
        const b = {
          matiere_id: S.mpModal.matiereId,
          type_mouvement: 'entree',
          quantite: parseFloat(qInp.value),
          unite_saisie: qField.getUnite(),
          ref_bl: (blInp.value || '').trim() || null,
          note: null,
          emplacement_source: null,
          emplacement_dest: null,
        };
        if (prixInp) {
          const raw = (prixInp.value || '').replace(',', '.').trim();
          if (raw !== '') {
            const v = parseFloat(raw);
            if (!isNaN(v) && v >= 0) b.prix_eur_m2 = v;
          }
        }
        return b;
      };
      S.mpModal.validate = () => {
        const q = parseFloat(qInp.value);
        if (!S.mpModal.matiereId) return 'Matière obligatoire.';
        if (!q || q <= 0) return 'Quantité invalide.';
        if (prixInp && prixInp.value) {
          const raw = prixInp.value.replace(',', '.').trim();
          const v = parseFloat(raw);
          if (isNaN(v) || v < 0) return 'Prix €/m² invalide.';
        }
        return null;
      };
    } else if (typeMvt === 'sortie') {
      // Le contrôle de stock se fait sur la quantité CONVERTIE : saisir 2 palettes
      // sur un stock de 1 500 kg doit alerter, même si « 2 » est petit.
      const qField = buildMpQuantiteField(mpCat, 'sortie');
      const qInp = qField.qInp;
      const checkQ = () => {
        const q = qField.getQuantiteGestion();
        if (!isNaN(q) && q > stockActuel) {
          errEl.style.display = '';
          errEl.textContent = 'Stock insuffisant.';
        } else {
          errEl.style.display = 'none';
        }
      };
      qInp.addEventListener('input', checkQ);
      qInp._onMpUniteChange = checkQ;
      qField.wrap.appendChild(el('div', { cls: 'mp-field' },
        mpStockActuelHint(stockActuel, mpCat),
        errEl,
      ));
      body.appendChild(qField.wrap);
      S.mpModal.getBody = () => ({
        matiere_id: S.mpModal.matiereId,
        type_mouvement: 'sortie',
        quantite: parseFloat(qInp.value),
        unite_saisie: qField.getUnite(),
        ref_bl: null,
        note: null,
        emplacement_source: null,
        emplacement_dest: null,
      });
      S.mpModal.validate = () => {
        const q = parseFloat(qInp.value);
        if (!S.mpModal.matiereId) return 'Matière obligatoire.';
        if (!q || q <= 0) return 'Quantité invalide.';
        if (qField.getQuantiteGestion() > stockActuel) return 'Stock insuffisant.';
        return null;
      };
    } else if (typeMvt === 'ajustement') {
      const stepAdj = mpIsPaletteCategory(mpCat) || ['carton', 'mandrin'].includes(mpCategorieKey(mpCat?.categorie)) ? '1' : '0.5';
      const qInp = el('input', { attrs: { type: 'number', min: '0', step: stepAdj } });
      const uniteAjLabel = mpUniteNom(mpCat) === 'kg' ? 'kg' : mpUniteNom(mpCat) + 's';
      body.appendChild(el('div', { cls: 'mp-field' },
        mpStockActuelHint(stockActuel, mpCat),
        el('label', null, 'Nouveau stock (' + uniteAjLabel + ')'),
        qInp,
      ));
      S.mpModal.getBody = () => ({
        matiere_id: S.mpModal.matiereId,
        type_mouvement: 'ajustement',
        quantite: parseFloat(qInp.value),
        ref_bl: null,
        note: null,
        emplacement_source: null,
        emplacement_dest: null,
      });
      S.mpModal.validate = () => {
        const q = parseFloat(qInp.value);
        if (!S.mpModal.matiereId) return 'Matière obligatoire.';
        if (Number.isNaN(q) || q < 0) return 'Quantité invalide.';
        return null;
      };
    } else if (typeMvt === 'transfert') {
      const qInp = el('input', { attrs: mpQuantiteInputAttrs(mpCat) });
      const srcInp = el('input', { attrs: { type: 'text' } });
      const dstInp = el('input', { attrs: { type: 'text' } });
      body.appendChild(el('div', { cls: 'mp-field' }, el('label', null, mpQuantiteFieldLabel(mpCat)), qInp));
      body.appendChild(el('div', { cls: 'mp-field' }, el('label', null, 'Emplacement source'), srcInp));
      body.appendChild(el('div', { cls: 'mp-field' }, el('label', null, 'Emplacement destination'), dstInp));
      S.mpModal.getBody = () => ({
        matiere_id: S.mpModal.matiereId,
        type_mouvement: 'transfert',
        quantite: parseFloat(qInp.value),
        ref_bl: null,
        note: null,
        emplacement_source: (srcInp.value || '').trim() || null,
        emplacement_dest: (dstInp.value || '').trim() || null,
      });
      S.mpModal.validate = () => {
        const q = parseFloat(qInp.value);
        if (!S.mpModal.matiereId) return 'Matière obligatoire.';
        if (!q || q <= 0) return 'Quantité invalide.';
        return null;
      };
    }

    const noteTa = el('textarea', { attrs: { placeholder: 'Commentaire (optionnel)' } });
    body.appendChild(el('div', { cls: 'mp-field' }, el('label', null, 'Note'), noteTa));
    const prevGetBody = S.mpModal.getBody;
    if (prevGetBody) {
      S.mpModal.getBody = () => {
        const b = prevGetBody();
        b.note = (noteTa.value || '').trim() || null;
        return b;
      };
    } else {
      S.mpModal.getBody = () => ({
        matiere_id: S.mpModal.matiereId,
        type_mouvement: typeMvt,
        quantite: 0,
        ref_bl: null,
        note: (noteTa.value || '').trim() || null,
        emplacement_source: null,
        emplacement_dest: null,
      });
      S.mpModal.validate = () => 'Type de mouvement non reconnu.';
    }

    const mpBtnCls = ['entree', 'sortie', 'ajustement', 'transfert'].includes(typeMvt)
      ? ' btn-mvt-' + typeMvt
      : '';
    body.appendChild(el('div', { cls: 'mp-modal-actions' },
      el('button', { cls: 'btn-cancel', type: 'button', on: { click: closeMroot } }, 'Annuler'),
      el('button', { cls: 'btn' + mpBtnCls, type: 'button', on: { click: submitMpMouvement } }, 'Valider'),
    ));
    box.appendChild(body);
    overlay.appendChild(box);
    mroot.appendChild(overlay);
  }

  async function submitMpMouvement() {
    if (!S.mpModal) return;
    const err = S.mpModal.validate ? S.mpModal.validate() : null;
    if (err) { showToast(err, 'error'); return; }
    const body = S.mpModal.getBody();
    // Injecte la laize pour les matières laizées (frontal/glassine/complexe)
    const mat = S.mpModal.matiere;
    if (mat && mpIsLaizeeCategory(mat.categorie)) {
      if (!S.mpModal.laizeId) {
        showToast('Laize obligatoire pour cette catégorie.', 'error');
        return;
      }
      body.laize_id = S.mpModal.laizeId;
    }
    try {
      const res = await api('/api/stock/matieres/mouvement', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (res && res.ok) {
        closeMroot();
        showToast('Mouvement enregistré.', 'success');
        if (S.selMatiere) {
          try {
            const d = await api('/api/stock/matieres');
            S.matieres = Array.isArray(d) ? d : [];
          } catch (e) { /* refreshSelMatiere affichera l'erreur */ }
          await refreshSelMatiere();
        } else {
          await loadMatieres();
          if (S.tab === 'dashboard') await loadDashboard();
        }
      }
    } catch (e) {
      showToast(e.message || 'Erreur lors de l\'enregistrement.', 'error');
    }
  }

  function _fmtDateFRz1(d) {
    const dd = String(d.getDate()).padStart(2, '0');
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    return dd + '/' + mm + '/' + d.getFullYear();
  }

  async function _fetchZ1DossierContext() {
    try {
      const r = await api('/api/fabrication/dossier-en-cours');
      return {
        dossier: (r && r.dossier) || null,
        precedents: Array.isArray(r && r.precedents) ? r.precedents : [],
        machine: (r && r.machine) || null,
        canSearchAll: !!(r && r.can_search_all),
      };
    } catch (e) {
      return { dossier: null, precedents: [], machine: null, canSearchAll: false };
    }
  }

  async function _fetchPaletteTypes() {
    try {
      const r = await api('/api/stock/matieres');
      if (!Array.isArray(r)) return [];
      return r.filter(m => (m.categorie || '').toLowerCase() === 'palette')
              .sort((a, b) => {
                const ea = a.is_europe ? 0 : 1;
                const eb = b.is_europe ? 0 : 1;
                if (ea !== eb) return ea - eb;
                return String(a.reference || '').localeCompare(String(b.reference || ''));
              });
    } catch (e) { return []; }
  }

  function _renderZ1PalettesBlock(container) {
    if (!container) return;
    container.innerHTML = '';
    const types = (S.pfModal && S.pfModal._paletteTypes) || [];
    const lines = (S.pfModal && S.pfModal.palettesLines) || [];

    const head = el('div', { style: { display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' } },
      el('label', { style: { margin: 0, flex: '1' } }, 'Palettes utilisees'),
      el('button', {
        cls: 'btn btn-ghost',
        type: 'button',
        style: { padding: '4px 10px', fontSize: '12px' },
        on: { click: () => {
          S.pfModal.palettesLines.push({ matiere_id: null, nombre: 1 });
          _renderZ1PalettesBlock(container);
        } },
      }, '+ Ajouter'),
    );
    container.appendChild(head);

    if (!types.length) {
      container.appendChild(el('div', { cls: 'mp-hint' },
        'Aucune palette referencee dans matieres premieres.'));
      return;
    }
    if (!lines.length) {
      container.appendChild(el('div', { cls: 'mp-hint' },
        'Aucune palette. Cliquez sur + Ajouter pour en saisir.'));
      return;
    }

    lines.forEach((line, idx) => {
      const row = el('div', { style: { display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '6px' } });
      const sel = el('select', { style: { flex: '1', padding: '8px', borderRadius: '8px', border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)' } });
      sel.appendChild(el('option', { attrs: { value: '' } }, 'Choisir une palette'));
      types.forEach(t => {
        const opt = el('option', { attrs: { value: String(t.id) } },
          (t.reference || '') + ' ' + (t.designation || '') + (t.is_europe ? ' (EUROPE)' : ''));
        if (line.matiere_id != null && Number(line.matiere_id) === Number(t.id)) opt.selected = true;
        sel.appendChild(opt);
      });
      sel.addEventListener('change', () => {
        const v = sel.value;
        S.pfModal.palettesLines[idx].matiere_id = v ? Number(v) : null;
      });

      const nbInp = el('input', {
        attrs: { type: 'number', min: '1', step: '1', value: String(line.nombre || 1) },
        style: { width: '80px', padding: '8px', borderRadius: '8px', border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)' },
      });
      nbInp.addEventListener('input', () => {
        const v = parseInt(nbInp.value, 10);
        S.pfModal.palettesLines[idx].nombre = Number.isFinite(v) && v > 0 ? v : 1;
      });

      const del = el('button', {
        cls: 'btn btn-ghost',
        type: 'button',
        style: { padding: '4px 10px', fontSize: '12px', color: 'var(--danger)' },
        attrs: { title: 'Supprimer cette palette', 'aria-label': 'Supprimer' },
        on: { click: () => {
          S.pfModal.palettesLines.splice(idx, 1);
          _renderZ1PalettesBlock(container);
        } },
      }, 'X');

      row.appendChild(sel);
      row.appendChild(nbInp);
      row.appendChild(del);
      container.appendChild(row);
    });
  }

  function _z1IsTermine(d) {
    return !!(d && String(d.statut_reel || '') === 'reellement_termine');
  }

  function _z1FormatDossierLine(d) {
    if (!d) return '';
    const refLine = (d.ref_produit || '') + (d.description ? ' - ' + d.description : '');
    return refLine;
  }

  function _z1UniteVente(d) {
    if (!d) return null;
    const ref = String(d.ref_produit || '').trim();
    if (!ref) return null;
    const connu = !!d.produit_connu;
    const unite = String((connu ? d.unite_vente : d.unite_vente_defaut) || '').trim();
    if (!unite) return null;
    return { unite: unite, connu: connu };
  }

  function _z1UniteLabel(uv) {
    return uv.connu ? uv.unite : uv.unite + ' - nouvelle ref';
  }

  function _z1UniteBadge(uv, opts) {
    const compact = !!(opts && opts.compact);
    return el('span', {
      style: {
        display: 'inline-block',
        padding: compact ? '2px 8px' : '3px 10px',
        borderRadius: '999px',
        background: uv.connu ? 'var(--accent)' : 'var(--warn)',
        color: 'var(--bg)',
        fontSize: compact ? '10px' : '11px',
        fontWeight: '700',
        textTransform: 'uppercase',
        letterSpacing: '.5px',
        whiteSpace: 'nowrap',
        flex: '0 0 auto',
      },
    }, _z1UniteLabel(uv));
  }

  function _z1MachineChip(nom, opts) {
    const compact = !!(opts && opts.compact);
    return el('span', {
      style: {
        display: 'inline-flex',
        alignItems: 'center',
        gap: '5px',
        padding: compact ? '2px 8px' : '3px 10px',
        borderRadius: '999px',
        background: 'var(--card)',
        border: '1px solid var(--border)',
        color: 'var(--text)',
        fontSize: compact ? '10px' : '11px',
        fontWeight: '700',
        textTransform: 'uppercase',
        letterSpacing: '.4px',
        whiteSpace: 'nowrap',
        flex: '0 0 auto',
      },
    },
      el('span', {
        style: { color: 'var(--muted)', fontWeight: '600', letterSpacing: '.4px' },
      }, 'Machine'),
      el('span', null, String(nom)),
    );
  }

  function _z1MakeNoteFromDossier(dossier) {
    if (!dossier || !dossier.no_dossier) return '';
    return 'Production dossier ' + dossier.no_dossier + ' - ' + _fmtDateFRz1(new Date());
  }

  function _renderZ1DossierBanner(container, ctx) {
    if (!container) return;
    container.innerHTML = '';
    container.style.display = '';

    const dossierSel = (S.pfModal && S.pfModal.dossier) || null;
    const hasSel = !!(dossierSel && dossierSel.no_dossier);
    const canPick = !!ctx && (
      !!ctx.dossier
      || (Array.isArray(ctx.precedents) && ctx.precedents.length > 0)
      || !!ctx.canSearchAll
      || !!S.pfModal._noDossierManual
    );

    // Cas "aucun dossier detecte ET pas selectionne" -> champ libre en direct.
    if (!hasSel && (!ctx || (!ctx.dossier && !(ctx.precedents || []).length && !ctx.canSearchAll))) {
      const inp = el('input', {
        cls: 'field-input',
        attrs: {
          type: 'text',
          placeholder: 'No de dossier (optionnel)',
          autocomplete: 'off',
          value: S.pfModal._noDossierManual || '',
        },
        style: { textTransform: 'uppercase' },
      });
      inp.addEventListener('input', () => {
        inp.value = inp.value.toUpperCase();
        S.pfModal._noDossierManual = inp.value.trim();
      });
      container.appendChild(el('div', { cls: 'mp-field' },
        el('label', null, 'Dossier de production (libre)'),
        inp,
        el('div', { cls: 'mp-hint' },
          'Aucun dossier detecte sur votre profil. Vous pouvez saisir le no manuellement.'),
      ));
      return;
    }

    const termine = _z1IsTermine(dossierSel);
    const bandeauStyle = termine
      ? { background: 'rgba(251,191,36,0.10)', borderColor: 'var(--warn)', color: 'var(--text)' }
      : { background: 'var(--accent-bg)', borderColor: 'var(--accent)', color: 'var(--text)' };

    const label = hasSel
      ? (termine ? 'Dossier selectionne (rattrapage)' : 'Dossier de production en cours')
      : (S.pfModal._noDossierManual
          ? 'Dossier de production (libre)'
          : 'Aucun dossier selectionne');

    const bodyLines = [];
    if (hasSel) {
      const refLine = _z1FormatDossierLine(dossierSel);

      // Colonne gauche : identification du dossier.
      const leftCol = el('div', { style: { flex: '1', minWidth: 0 } },
        el('div', { style: { fontWeight: '700', fontSize: '14px' } },
          (dossierSel.fictif ? '(hors planning) ' : '') + (dossierSel.no_dossier || '')),
        dossierSel.client
          ? el('div', { style: { fontSize: '12px', color: 'var(--text2)', marginTop: '2px' } },
              'Client : ' + dossierSel.client)
          : null,
        refLine
          ? el('div', { style: { fontSize: '12px', color: 'var(--text2)', marginTop: '2px' } },
              'Reference : ' + refLine)
          : null,
      );

      // Colonne droite : unite de vente + machine, alignees a droite et lisibles.
      const uv = _z1UniteVente(dossierSel);
      const rightCol = (uv || dossierSel.machine_nom)
        ? el('div', {
            style: {
              display: 'flex', flexDirection: 'column', alignItems: 'flex-end',
              gap: '6px', flex: '0 0 auto',
            },
          },
            uv ? _z1UniteBadge(uv) : null,
            dossierSel.machine_nom ? _z1MachineChip(dossierSel.machine_nom) : null,
          )
        : null;

      bodyLines.push(el('div', {
        style: { display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px' },
      }, leftCol, rightCol));

      if (termine) {
        bodyLines.push(el('div', {
          style: {
            fontSize: '11px',
            color: 'var(--warn)',
            marginTop: '6px',
            fontWeight: '600',
            textTransform: 'uppercase',
            letterSpacing: '.5px',
          },
        }, 'Dossier termine - entree rattrapee'));
      }
    } else if (S.pfModal._noDossierManual) {
      bodyLines.push(el('div', { style: { fontWeight: '700', fontSize: '14px' } },
        String(S.pfModal._noDossierManual).toUpperCase()));
      bodyLines.push(el('div', { style: { fontSize: '11px', color: 'var(--muted)', marginTop: '2px' } },
        'Saisie libre'));
    } else {
      bodyLines.push(el('div', { style: { fontSize: '12px', color: 'var(--muted)' } },
        'Cliquez sur "Choisir un autre dossier" pour en selectionner un.'));
    }

    const pickerLink = canPick
      ? el('button', {
          cls: 'btn btn-ghost',
          type: 'button',
          style: {
            padding: '4px 10px',
            fontSize: '11px',
            color: 'var(--accent)',
            background: 'transparent',
            border: '1px solid var(--border)',
            alignSelf: 'flex-start',
          },
          on: { click: (e) => {
            e.preventDefault();
            _openZ1DossierPicker(container, ctx);
          } },
        }, 'Choisir un autre dossier')
      : null;

    const bandeau = el('div', {
      cls: 'mp-readonly',
      style: bandeauStyle,
    }, ...bodyLines);

    container.appendChild(el('div', { cls: 'mp-field' },
      el('div', {
        style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', marginBottom: '4px' },
      },
        el('label', { style: { margin: 0 } }, label),
        pickerLink,
      ),
      bandeau,
    ));
  }

  function _z1SetDossier(container, ctx, dossier, manualRef) {
    if (!S.pfModal) return;
    const noteTa = S.pfModal._noteTa || null;
    const prevAuto = S.pfModal._noteAutoLast || '';
    S.pfModal.dossier = dossier || null;
    S.pfModal._noDossierManual = (manualRef || '').trim();
    _renderZ1DossierBanner(container, ctx);

    // Note auto : ne l'ecrase que si vide OU si elle correspond a la note auto precedente.
    if (noteTa) {
      const cur = (noteTa.value || '').trim();
      if (!cur || cur === prevAuto) {
        const newAuto = dossier ? _z1MakeNoteFromDossier(dossier) : '';
        noteTa.value = newAuto;
        S.pfModal._noteAutoLast = newAuto;
      }
    }
  }

  function _z1DossierRow(dossier, opts) {
    const termine = _z1IsTermine(dossier);
    const badgeText = opts && opts.badge
      ? opts.badge
      : (termine ? 'Termine' : (dossier.statut_reel === 'reellement_en_saisie' ? 'En cours' : ''));

    const refLine = _z1FormatDossierLine(dossier);
    const cli = dossier.client ? ' - ' + dossier.client : '';
    const uvRow = _z1UniteVente(dossier);

    return el('button', {
      type: 'button',
      cls: 'z1-picker-item',
      style: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '10px',
        padding: '10px 12px',
        background: 'var(--card)',
        border: '1px solid var(--border)',
        borderRadius: '8px',
        cursor: 'pointer',
        textAlign: 'left',
        color: 'var(--text)',
        width: '100%',
        boxShadow: '0 1px 3px rgba(0,0,0,0.12)',
      },
      on: { click: opts && opts.onClick },
    },
      el('div', { style: { flex: '1', minWidth: 0 } },
        el('div', { style: { fontWeight: '700', fontSize: '13px' } },
          (dossier.no_dossier || '') + cli),
        refLine
          ? el('div', {
              style: { fontSize: '11px', color: 'var(--text2)', marginTop: '2px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
            }, refLine)
          : null,
      ),
      (uvRow || badgeText || dossier.machine_nom)
        ? el('div', {
            style: {
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'flex-end',
              gap: '4px',
              flex: '0 0 auto',
            },
          },
            uvRow ? _z1UniteBadge(uvRow, { compact: true }) : null,
            dossier.machine_nom ? _z1MachineChip(dossier.machine_nom, { compact: true }) : null,
            badgeText
              ? el('div', {
                  style: {
                    fontSize: '10px',
                    fontWeight: '700',
                    textTransform: 'uppercase',
                    letterSpacing: '.5px',
                    whiteSpace: 'nowrap',
                    color: termine ? 'var(--warn)' : 'var(--accent)',
                  },
                }, badgeText)
              : null,
          )
        : null,
    );
  }

  function _z1SectionTitle(text) {
    return el('div', {
      style: {
        display: 'flex', alignItems: 'center', gap: '8px',
        marginTop: '8px', marginBottom: '2px',
      },
    },
      el('span', {
        style: {
          width: '3px', height: '14px', borderRadius: '2px',
          background: 'var(--accent)', flex: '0 0 auto',
        },
      }),
      el('span', {
        style: {
          fontSize: '12px', fontWeight: '800', color: 'var(--text)',
          textTransform: 'uppercase', letterSpacing: '.8px', whiteSpace: 'nowrap',
        },
      }, text),
      el('span', { style: { flex: '1', height: '1px', background: 'var(--border)' } }),
    );
  }

  function _ensureZ1PickerStyles() {
    if (document.getElementById('z1-picker-styles')) return;
    const st = document.createElement('style');
    st.id = 'z1-picker-styles';
    st.textContent = [
      '.z1-picker-item{transition:border-color .12s ease, box-shadow .12s ease, transform .12s ease;}',
      '.z1-picker-item:hover{border-color:var(--accent);box-shadow:0 3px 10px rgba(0,0,0,0.18);transform:translateY(-1px);}',
      '.z1-picker-input{background:var(--card) !important;border:1.5px solid var(--border) !important;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,0.10);transition:border-color .12s ease, box-shadow .12s ease;}',
      '.z1-picker-input::placeholder{color:var(--muted);opacity:1;}',
      '.z1-picker-input:focus{border-color:var(--accent) !important;box-shadow:0 0 0 3px var(--accent-bg);}',
    ].join('\n');
    document.head.appendChild(st);
  }

  function _openZ1DossierPicker(bannerContainer, ctx) {
    _ensureZ1PickerStyles();
    // Ferme l'eventuel picker precedent.
    const prev = document.getElementById('z1-picker-overlay');
    if (prev) prev.remove();

    const overlay = el('div', {
      attrs: { id: 'z1-picker-overlay' },
      style: {
        position: 'fixed', inset: '0', zIndex: '10001',
        background: 'rgba(0,0,0,0.55)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '20px',
      },
    });
    _bindOverlayDismiss(overlay, () => overlay.remove());

    const box = el('div', {
      style: {
        background: 'var(--card)', border: '1px solid var(--border)',
        borderRadius: '12px', width: 'min(520px, 100%)', maxHeight: '80vh',
        display: 'flex', flexDirection: 'column',
        overflow: 'hidden',
        boxShadow: '0 20px 60px rgba(0,0,0,0.45)',
      },
    });

    box.appendChild(el('div', {
      style: {
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '14px 16px', borderBottom: '1px solid var(--border)',
      },
    },
      el('div', { style: { fontWeight: '700', fontSize: '14px' } }, 'Choisir un autre dossier'),
      el('button', {
        cls: 'mp-modal-close', type: 'button',
        attrs: { 'aria-label': 'Fermer' },
        on: { click: () => overlay.remove() },
      }, 'x'),
    ));

    // Fond distinct de celui du modal : les cartes de dossiers (var(--card))
    // ressortent nettement sur la zone de liste (var(--bg)).
    const listWrap = el('div', {
      style: {
        padding: '14px 16px', overflowY: 'auto',
        display: 'flex', flexDirection: 'column', gap: '8px',
        background: 'var(--bg)',
      },
    });

    const pick = (dossier) => {
      _z1SetDossier(bannerContainer, ctx, dossier, '');
      overlay.remove();
    };

    // Dossier en cours (accent)
    if (ctx && ctx.dossier) {
      listWrap.appendChild(_z1SectionTitle('Dossier en cours'));
      listWrap.appendChild(_z1DossierRow(ctx.dossier, {
        badge: 'En cours', onClick: () => pick(ctx.dossier),
      }));
    }

    // Precedents (2 max)
    const precedents = (ctx && ctx.precedents) || [];
    if (precedents.length) {
      listWrap.appendChild(_z1SectionTitle('Precedents (' + (ctx.machine ? ctx.machine.nom : 'meme machine') + ')'));
      precedents.forEach(d => {
        listWrap.appendChild(_z1DossierRow(d, { badge: 'Termine', onClick: () => pick(d) }));
      });
    }

    // Saisie libre
    listWrap.appendChild(_z1SectionTitle('Saisie libre'));

    const manualInp = el('input', {
      cls: 'field-input z1-picker-input',
      attrs: {
        type: 'text',
        placeholder: 'No de dossier (ex : 12345-01)',
        autocomplete: 'off',
        value: S.pfModal._noDossierManual || '',
      },
      style: { textTransform: 'uppercase', flex: '1', fontWeight: '600' },
    });
    const manualBtn = el('button', {
      cls: 'btn btn-accent', type: 'button',
      style: { padding: '8px 14px', fontSize: '12px' },
      on: { click: () => {
        const v = (manualInp.value || '').trim().toUpperCase();
        if (!v) { manualInp.focus(); return; }
        _z1SetDossier(bannerContainer, ctx, null, v);
        overlay.remove();
      } },
    }, 'Valider');
    listWrap.appendChild(el('div', {
      style: { display: 'flex', gap: '8px', alignItems: 'center' },
    }, manualInp, manualBtn));

    // Recherche globale (chef d'atelier / admin)
    if (ctx && ctx.canSearchAll) {
      listWrap.appendChild(_z1SectionTitle('Recherche libre (toutes machines)'));

      const searchInp = el('input', {
        cls: 'field-input z1-picker-input',
        attrs: {
          type: 'text',
          placeholder: 'Reference, client, description...',
          autocomplete: 'off',
        },
      });
      const results = el('div', {
        style: { display: 'flex', flexDirection: 'column', gap: '6px' },
      });
      let searchDebounce = null;
      const runSearch = async () => {
        const q = (searchInp.value || '').trim();
        results.innerHTML = '';
        if (q.length < 2) return;
        try {
          const r = await api('/api/fabrication/dossiers-search?q=' + encodeURIComponent(q));
          const list = (r && r.dossiers) || [];
          if (!list.length) {
            results.appendChild(el('div', { cls: 'mp-hint' }, 'Aucun resultat pour "' + q + '"'));
            return;
          }
          list.forEach(d => results.appendChild(_z1DossierRow(d, { onClick: () => pick(d) })));
        } catch (e) {
          results.appendChild(el('div', { cls: 'mp-hint err' }, 'Erreur de recherche.'));
        }
      };
      searchInp.addEventListener('input', () => {
        clearTimeout(searchDebounce);
        searchDebounce = setTimeout(runSearch, 220);
      });
      listWrap.appendChild(searchInp);
      listWrap.appendChild(results);
      requestAnimationFrame(() => searchInp.focus());
    } else {
      requestAnimationFrame(() => manualInp.focus());
    }

    box.appendChild(listWrap);
    overlay.appendChild(box);
    document.body.appendChild(overlay);
  }

  async function _initZ1Enrichment(dossierBanner, palettesBlock, noteTa) {
    const [ctx, types] = await Promise.all([_fetchZ1DossierContext(), _fetchPaletteTypes()]);
    if (!S.pfModal) return;
    S.pfModal._z1Ctx = ctx;
    S.pfModal._paletteTypes = types || [];
    S.pfModal._noteTa = noteTa || null;
    // Selection par defaut : dossier actif s'il existe.
    S.pfModal.dossier = ctx.dossier || null;

    _renderZ1DossierBanner(dossierBanner, ctx);
    _renderZ1PalettesBlock(palettesBlock);

    if (ctx.dossier && ctx.dossier.no_dossier && noteTa && !((noteTa.value || '').trim())) {
      const auto = _z1MakeNoteFromDossier(ctx.dossier);
      noteTa.value = auto;
      S.pfModal._noteAutoLast = auto;
    }

    // Pre-remplit la reference produit depuis le dossier actif.
    if (ctx.dossier && ctx.dossier.ref_produit && S.pfModal.refInp
        && !((S.pfModal.refInp.value || '').trim())) {
      const refDossier = String(ctx.dossier.ref_produit).trim();
      S.pfModal.refInp.value = refDossier;
      try {
        const p = await resolvePfProduitByRef(refDossier);
        if (p && S.pfModal && S.pfModal.refInp
            && String(S.pfModal.refInp.value || '').trim().toUpperCase()
                === refDossier.toUpperCase()) {
          renderPfMouvementModal('entree', p, 'Z1');
        }
      } catch (e) {}
    }
  }

  function renderPfMouvementModal(type, produit, defaultEmpl) {
    const typeMvt = (type || 'entree').toLowerCase();
    if (!['entree', 'sortie'].includes(typeMvt)) return;
    closeMroot();
    const mroot = document.getElementById('mroot');
    if (!mroot) return;
    let prod = produit || null;
    S.pfModal = {
      type: typeMvt,
      produit: prod,
      produitId: prod ? prod.id : null,
      refInp: null,
      defaultEmpl: defaultEmpl || null,
      dossier: null,
      palettesLines: [],
      _paletteTypes: [],
      _noDossierManual: '',
    };
    const _isZ1Entree = typeMvt === 'entree'
      && String(defaultEmpl || '').toUpperCase() === 'Z1';

    const overlay = el('div', { cls: 'mp-modal-overlay' });
    _bindOverlayDismiss(overlay, closeMroot);
    const headTypeCls = typeMvt === 'entree' ? 'pf-entree' : 'pf-sortie';
    const box = el('div', { cls: 'mp-modal mp-modal-mvt' });
    box.appendChild(el('div', { cls: 'mp-modal-mvt-head mp-modal-mvt-head-' + headTypeCls },
      el('h3', null, PF_MVT_TITLES[typeMvt] || typeMvt),
      el('button', {
        cls: 'mp-modal-close',
        type: 'button',
        attrs: { title: 'Fermer', 'aria-label': 'Fermer' },
        on: { click: closeMroot },
      }, '×'),
    ));
    const body = el('div', { cls: 'mp-modal-mvt-body' });
    const hintEl = el('div', { cls: 'mp-hint' }, '');
    const errEl = el('div', { cls: 'mp-hint err', style: { display: 'none' } }, '');
    const dossierBanner = el('div', { cls: 'z1-dossier-banner', style: { display: 'none' } });
    if (_isZ1Entree) body.appendChild(dossierBanner);

    if (prod) {
      const unit = (prod.unite || '').trim();
      body.appendChild(el('div', { cls: 'mp-field' },
        el('label', null, 'Produit fini'),
        el('div', { cls: 'mp-readonly' },
          (prod.reference || '') + (prod.designation ? ' — ' + prod.designation : '')
          + (unit ? ' (' + unit + ')' : ''),
        ),
      ));
    } else {
      const refInp = el('input', {
        cls: 'field-input',
        attrs: {
          type: 'text',
          placeholder: 'Référence produit (comme la recherche en haut)…',
          autocomplete: 'off',
        },
        style: { direction: 'ltr' },
      });
      const suggWrap = el('div', { cls: 'empl-suggestions', style: { display: 'none' } });
      S.pfModal.refInp = refInp;
      wireStockProduitSearch(refInp, suggWrap, (p) => {
        renderPfMouvementModal(typeMvt, p, S.pfModal && S.pfModal.defaultEmpl);
      });
      const refCombo = el('div', { cls: 'empl-combo-wrap' }, refInp, suggWrap);
      body.appendChild(el('div', { cls: 'mp-field ref-field-wrap' },
        el('label', null, 'Produit fini'),
        refCombo,
      ));
      requestAnimationFrame(() => refInp.focus());
    }

    const { wrap: emplWrap, emplInp } = buildMpEmplacementField();
    if (defaultEmpl) {
      emplInp.value = String(defaultEmpl).toUpperCase();
    }
    // toISOString() renvoie la date UTC : faux jour entre 22h et minuit a Paris.
    const today = new Date().toLocaleDateString('sv-SE', { timeZone: 'Europe/Paris' });
    const dateInp = el('input', { attrs: { type: 'date', value: today } });
    const qInp = el('input', { attrs: { type: 'number', min: '0', step: 'any', inputmode: 'decimal' } });

    let stockEmpl = 0;
    const refreshStockHint = async () => {
      if (typeMvt !== 'sortie' || !S.pfModal.produitId) return;
      const empl = mpEmplacementValue(emplInp);
      if (!empl || !isStockEmplacementCode(empl)) {
        hintEl.textContent = '';
        errEl.style.display = 'none';
        return;
      }
      stockEmpl = await fetchPfStockAtEmpl(S.pfModal.produitId, empl);
      const unit = (S.pfModal.produit?.unite || prod?.unite || '').trim();
      hintEl.textContent = 'Stock à cet emplacement : ' + (unit ? fU(stockEmpl, unit) : fN(stockEmpl));
      checkSortieQte();
    };

    const checkSortieQte = () => {
      if (typeMvt !== 'sortie') return;
      const q = parseFloat(qInp.value);
      if (q > stockEmpl) {
        errEl.style.display = '';
        errEl.textContent = 'Stock insuffisant.';
      } else {
        errEl.style.display = 'none';
      }
    };

    emplInp.addEventListener('input', () => {
      emplInp.value = emplInp.value.toUpperCase();
      refreshStockHint();
    });
    emplInp.addEventListener('change', refreshStockHint);

    if (typeMvt === 'entree') {
      body.appendChild(emplWrap);
      body.appendChild(el('div', { cls: 'mp-field' },
        el('label', null, 'Quantité'),
        qInp,
      ));
      body.appendChild(el('div', { cls: 'mp-field' },
        el('label', null, 'Date du stock'),
        dateInp,
      ));
      S.pfModal.validate = () => {
        if (!S.pfModal.produitId) return 'Produit obligatoire.';
        const emplErr = validateMpEmplacement(mpEmplacementValue(emplInp));
        if (emplErr) return emplErr;
        const q = parseFloat(qInp.value);
        if (!q || q <= 0) return 'Quantité invalide.';
        return null;
      };
      S.pfModal.getBody = () => ({
        produit_id: S.pfModal.produitId,
        emplacement: mpEmplacementValue(emplInp),
        type_mouvement: 'entree',
        quantite: parseFloat(qInp.value),
        date_entree: dateInp.value || today,
        note: null,
      });
    } else {
      qInp.addEventListener('input', checkSortieQte);
      body.appendChild(emplWrap);
      body.appendChild(el('div', { cls: 'mp-field' },
        el('label', null, 'Quantité'),
        qInp,
        hintEl,
        errEl,
      ));
      if (S.pfModal.produitId) refreshStockHint();
      S.pfModal.validate = () => {
        if (!S.pfModal.produitId) return 'Produit obligatoire.';
        const emplErr = validateMpEmplacement(mpEmplacementValue(emplInp));
        if (emplErr) return emplErr;
        const q = parseFloat(qInp.value);
        if (!q || q <= 0) return 'Quantité invalide.';
        if (q > stockEmpl) return 'Stock insuffisant.';
        return null;
      };
      S.pfModal.getBody = () => ({
        produit_id: S.pfModal.produitId,
        emplacement: mpEmplacementValue(emplInp),
        type_mouvement: 'sortie',
        quantite: parseFloat(qInp.value),
        date_entree: today,
        note: null,
      });
    }

    const palettesBlock = el('div', { cls: 'z1-palettes-block' });
    if (_isZ1Entree) {
      body.appendChild(el('div', { cls: 'mp-field' }, palettesBlock));
    }
    const noteTa = el('textarea', { attrs: { placeholder: 'Commentaire (optionnel)' } });
    body.appendChild(el('div', { cls: 'mp-field' }, el('label', null, 'Note'), noteTa));
    const prevGetBody = S.pfModal.getBody;
    S.pfModal.getBody = () => {
      const b = prevGetBody();
      b.note = (noteTa.value || '').trim() || null;
      if (_isZ1Entree) {
        const noDos = (S.pfModal.dossier && S.pfModal.dossier.no_dossier)
          || S.pfModal._noDossierManual
          || null;
        b.no_dossier = noDos ? (String(noDos).trim() || null) : null;
        const cleanPalettes = (S.pfModal.palettesLines || [])
          .filter(l => l && l.matiere_id && Number(l.nombre) > 0)
          .map(l => ({ matiere_id: Number(l.matiere_id), nombre: Number(l.nombre) }));
        if (cleanPalettes.length) b.palettes = cleanPalettes;
      }
      return b;
    };

    const pfBtnCls = typeMvt === 'entree' ? 'btn-pf-entree' : 'btn-pf-sortie';
    body.appendChild(el('div', { cls: 'mp-modal-actions' },
      el('button', { cls: 'btn-cancel', type: 'button', on: { click: closeMroot } }, 'Annuler'),
      el('button', { cls: 'btn ' + pfBtnCls, type: 'button', on: { click: submitPfMouvement } }, 'Valider'),
    ));
    box.appendChild(body);
    overlay.appendChild(box);
    mroot.appendChild(overlay);

    if (_isZ1Entree) {
      requestAnimationFrame(() => {
        _initZ1Enrichment(dossierBanner, palettesBlock, noteTa);
      });
    }
  }

  async function submitPfMouvement() {
    if (!S.pfModal) return;
    const typeMvt = (S.pfModal.type || 'entree').toLowerCase();
    // Si pas de produit_id mais on a une référence saisie, on tente la résolution.
    // En entrée Z1, on autorise l'auto-création de la référence (unité = étiquette).
    if (!S.pfModal.produitId) {
      const refVal = (S.pfModal.refInp ? S.pfModal.refInp.value : '') || '';
      const refClean = String(refVal).trim().toUpperCase();
      if (!refClean) {
        showToast('Référence obligatoire.', 'error');
        return;
      }
      const p = await resolvePfProduitByRef(refVal);
      if (p) {
        S.pfModal.produitId = p.id;
        S.pfModal.produit = p;
      } else if (typeMvt === 'sortie') {
        showToast('Référence introuvable — sélectionnez un produit dans la liste ou vérifiez la saisie.', 'error');
        return;
      }
      // En entrée : on continuera avec la référence brute → l'endpoint auto-crée le produit.
    }
    // Validation (sauf produitId obligatoire si entrée + auto-create)
    let err = null;
    if (S.pfModal.validate) {
      const origErr = S.pfModal.validate();
      // En entrée auto-create, ignorer l'erreur "Produit obligatoire."
      if (origErr && !(typeMvt === 'entree' && !S.pfModal.produitId && /[Pp]roduit/.test(origErr))) {
        err = origErr;
      }
    }
    if (!err && typeMvt === 'sortie' && S.pfModal.getBody) {
      const b = S.pfModal.getBody();
      const stock = await fetchPfStockAtEmpl(b.produit_id, b.emplacement);
      if (b.quantite > stock) err = 'Stock insuffisant.';
    }
    if (err) { showToast(err, 'error'); return; }
    const body = S.pfModal.getBody();
    // Si entrée sans produit_id : passer par l'endpoint produits-finis/entree qui auto-crée.
    if (typeMvt === 'entree' && !S.pfModal.produitId) {
      const refVal = (S.pfModal.refInp ? S.pfModal.refInp.value : '') || '';
      const payload = {
        reference: String(refVal).trim().toUpperCase(),
        designation: String(refVal).trim().toUpperCase(),
        unite: STOCK_UNITE_VENTE_DEFAUT,
        emplacement: body.emplacement,
        quantite: body.quantite,
        note: body.note,
      };
      try {
        await api('/api/stock/produits-finis/entree', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        showToast('Entrée enregistrée — référence créée.', 'success');
        S.pfModal = null;
        closeMroot();
        if (S.tab === 'production') await loadProduction();
        else if (S.tab === 'produits-finis') await loadProduitsFinis();
        else if (S.tab === 'dashboard') await loadDashboard();
      } catch (e) {
        showToast(e.message || 'Erreur lors de l\'enregistrement.', 'error');
      }
      return;
    }
    await submitMouvement(body);
  }

  // --- API publique -----------------------------------------------------
  function _syncConfig() {
    var h = _h();
    _emplListFromDB = (h.emplacements && h.emplacements()) || [];
    if (h.uniteVenteDefaut)    STOCK_UNITE_VENTE_DEFAUT = h.uniteVenteDefaut;
    if (h.emplAuSol)           STOCK_EMPL_AU_SOL = h.emplAuSol;
    if (h.emplAuSolLabel)      STOCK_EMPL_AU_SOL_LABEL = h.emplAuSolLabel;
    if (h.emplSortieProd)      STOCK_EMPL_SORTIE_PROD = h.emplSortieProd;
    if (h.emplSortieProdLabel) STOCK_EMPL_SORTIE_PROD_LABEL = h.emplSortieProdLabel;
  }

  // kind : 'entree-mp' | 'sortie-mp' | 'entree-z1' | 'sortie-z1'
  function open(kind, opts) {
    _syncConfig();
    opts = opts || {};
    switch (String(kind || '')) {
      case 'entree-mp': return openModalMouvement('entree');
      case 'sortie-mp': return openModalMouvement('sortie');
      case 'entree-z1':
        return renderPfMouvementModal('entree', opts.produit || null, STOCK_EMPL_SORTIE_PROD);
      case 'sortie-z1':
        return renderPfMouvementModal('sortie', opts.produit || null, STOCK_EMPL_SORTIE_PROD);
      default:
        throw new Error('MySifaStockModals.open : type inconnu ' + kind);
    }
  }

  global.MySifaStockModals = {
    configure: function (h) { HOST = h; _syncConfig(); return this; },
    open: open,
    openMp: function () { _syncConfig(); return openModalMouvement.apply(null, arguments); },
    openPf: function () { _syncConfig(); return renderPfMouvementModal.apply(null, arguments); },
    sortirLot: function () { _syncConfig(); return sortirLot.apply(null, arguments); },
    openMoveLot: function () { _syncConfig(); return openMoveLotModal.apply(null, arguments); },
    // Utilitaires re-exportes : les pages hotes les aliasent au lieu
    // d'en garder une copie, ce qui interdit toute divergence.
    utils: {
      mpCategorieKey: mpCategorieKey,
      mpCtx: mpCtx,
      mpIsBobineCategory: mpIsBobineCategory,
      mpIsLaizeeCategory: mpIsLaizeeCategory,
      mpIsPaletteCategory: mpIsPaletteCategory,
      mpStockLine: mpStockLine,
      mpUniteNom: mpUniteNom,
      mpUniteShort: mpUniteShort,
      stockEmplLabel: stockEmplLabel,
      isStockEmplacementAuSol: isStockEmplacementAuSol,
      isStockEmplacementSortieProd: isStockEmplacementSortieProd,
      isStockEmplacementCode: isStockEmplacementCode,
      isStockZoneSpeciale: isStockZoneSpeciale,
      allPageEmplacementChoices: allPageEmplacementChoices,
      wireStockProduitSearch: wireStockProduitSearch,
      wireStockEmplSearch: wireStockEmplSearch,
      resolvePfProduitByRef: resolvePfProduitByRef,
      _fetchZ1DossierContext: _fetchZ1DossierContext,
      mpEmplacementValue: mpEmplacementValue,
      validateMpEmplacement: validateMpEmplacement,
      buildMpEmplacementField: buildMpEmplacementField,
      mpQuantiteFieldLabel: mpQuantiteFieldLabel,
      mpQuantiteInputAttrs: mpQuantiteInputAttrs,
      mpIsAdhesifCategory: mpIsAdhesifCategory,
      mpUnitesSaisie: mpUnitesSaisie,
      mpFacteurSaisie: mpFacteurSaisie,
      mpUniteSaisieDefaut: mpUniteSaisieDefaut,
      mpStockActuelHint: mpStockActuelHint,
      fmtStockParisNow: fmtStockParisNow,
    },
    // Referentiels d'affichage partages.
    constants: {
      MP_UNITE_SAISIE_LABELS: MP_UNITE_SAISIE_LABELS,
      MP_CAT_LABELS: MP_CAT_LABELS,
      MP_MVT_TITLES: MP_MVT_TITLES,
      PF_MVT_TITLES: PF_MVT_TITLES,
      MP_CATEGORIES_LAIZEES: MP_CATEGORIES_LAIZEES,
      _STOCK_ZONES_SPECIALES: _STOCK_ZONES_SPECIALES,
    },
    // Expose pour les hotes qui rebranchent leur propre UI dessus.
    submitMouvement: function () { return submitMouvement.apply(null, arguments); },
  };
})(window);

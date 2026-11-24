/* MySifa — ADV (/adv) : carnet de commandes et préparations.
 *
 * Deux onglets, tout l'état dans l'adresse (.claude/rules/url-etat.md) :
 *   /adv?onglet=commandes (défaut si droit ADV) &filtre=&tri=&sens=&ligne=<n°-lg>
 *   /adv?onglet=prepa &horizon=<jours> &groupe=<groupe> &ligne=<n°-lg>
 * Fenêtre : la fiche d'une ligne (`ligne`). Hors adresse : la recherche
 * texte (saisie en cours).
 *
 * Le calcul (carnet RVGI, stock MyStock, étapes) est fait côté serveur par
 * app/services/adv_commandes.py ; ici on affiche, on filtre et on trie.
 * Les saisies libres passent par textContent, jamais par innerHTML.
 */
(function () {
  'use strict';

  var BOOT = window.__ADV__ || {};
  var DROITS = BOOT.droits || {};
  var ETAPES = BOOT.etapes || [];
  var ETATS = {};
  (BOOT.etats || []).forEach(function (e) { ETATS[e.cle] = e.label; });
  var LIB_REPIQUAGE = {};
  (BOOT.statuts_repiquage || []).forEach(function (e) { LIB_REPIQUAGE[e.cle] = e.label; });
  var LIB_PREPA = {};
  (BOOT.statuts_prepa || []).forEach(function (e) { LIB_PREPA[e.cle] = e.label; });

  var ONGLETS = DROITS.adv ? ['commandes', 'prepa'] : ['prepa'];
  var FILTRES = ['tous', 'retard', 'semaine', 'pretes'].concat(ETAPES.map(function (e) { return 'etape_' + e.cle; }));
  var TRIS = ['commande', 'client', 'article', 'qte', 'stock', 'a_fabriquer', 'expedition', 'livraison', 'fin_prod'];
  var HORIZONS = [7, 14, 21, 30];
  var GROUPES = ['tous', 'preparable', 'en_cours', 'partiel', 'attente', 'pretes'];

  var S = {
    onglet: ONGLETS[0],
    filtre: 'tous',
    tri: 'expedition',
    sens: 'asc',
    q: '',
    ligne: null,                 // clé « numero-ligne » de la fiche ouverte
    reglages: null,              // 'mise_en_forme' : fenêtre des règles de couleur
    mef: [],                     // règles de mise en forme (communes au service)
    ordre: [],                   // ordre des colonnes du carnet, propre à la personne
    colDrag: null,
    ficheEtape: null,            // étape dépliée pour correction dans la fiche
    prepaDrag: null,             // préparation en cours de déplacement
    horizon: BOOT.horizon || 21,
    groupe: 'tous',
    carnet: null,
    prepa: null,
    erreur: null,
    charge: false
  };
  var minuteur = null;

  /* ── Outils ─────────────────────────────────────────────────── */

  function h(tag, attrs) {
    var el = document.createElement(tag);
    var a = attrs || {};
    Object.keys(a).forEach(function (k) {
      var v = a[k];
      if (v === null || v === undefined || v === false) return;
      if (k === 'className') el.className = v;
      else if (k === 'text') el.textContent = v;
      else if (k === 'html') el.innerHTML = v;            // SVG statiques uniquement
      else if (k.slice(0, 2) === 'on') el.addEventListener(k.slice(2).toLowerCase(), v);
      else if (k === 'value') el.value = v;
      else el.setAttribute(k, v === true ? '' : v);
    });
    for (var i = 2; i < arguments.length; i++) ajouter(el, arguments[i]);
    return el;
  }
  function ajouter(el, c) {
    if (c === null || c === undefined || c === false) return;
    if (Array.isArray(c)) { c.forEach(function (x) { ajouter(el, x); }); return; }
    el.appendChild(typeof c === 'string' || typeof c === 'number' ? document.createTextNode(String(c)) : c);
  }
  function toast(msg, type) {
    var w = document.getElementById('toast-wrap');
    if (!w) return;
    var t = h('div', {className: 'toast ' + (type || 'success'), text: msg});
    w.appendChild(t);
    setTimeout(function () { t.remove(); }, 3200);
  }
  async function api(chemin, init) {
    var opts = Object.assign({credentials: 'include', headers: {}}, init || {});
    if (opts.body && typeof opts.body !== 'string') {
      opts.body = JSON.stringify(opts.body);
      opts.headers['Content-Type'] = 'application/json';
    }
    var r = await fetch(chemin, opts);
    if (r.status === 401) { location.href = '/?next=' + encodeURIComponent(location.pathname + location.search); throw new Error('Session expirée.'); }
    var d = null;
    try { d = await r.json(); } catch (e) { d = null; }
    if (!r.ok) throw new Error((d && d.detail) || ('Erreur ' + r.status));
    return d;
  }
  function fN(v) {
    var n = Number(v) || 0;
    var s = (Math.round(n * 100) / 100).toLocaleString('fr-FR', {maximumFractionDigits: 2});
    return s;
  }
  function dateFr(s) {
    if (!s) return '';
    var d = String(s).slice(0, 10).split('-');
    return d.length === 3 ? d[2] + '/' + d[1] + '/' + d[0] : String(s);
  }
  function dateLongue(s) {
    if (!s) return '';
    var d = String(s).slice(0, 10).split('-');
    return d.length === 3 ? d[2] + '/' + d[1] + '/' + d[0] : String(s);
  }
  function heure(s) { return s && String(s).length >= 16 ? String(s).slice(11, 16) : ''; }
  function modalOuverte() { var m = document.getElementById('mroot'); return !!(m && m.firstElementChild); }
  function norm(s) {
    return String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  }
  // L'étiquette est l'unité par défaut : on ne l'écrit pas sur chaque ligne.
  function unite(l) {
    var u = l && l.stock && l.stock.unite;
    return u && !/^[ée]tiquette/i.test(u) ? u : '';
  }
  // « 650 cartons », « 1 carton » : en français, le pluriel commence à 2.
  function accord(mot, q) {
    if (!mot || Math.abs(Number(q) || 0) < 2 || /[sxz]$/i.test(mot)) return mot;
    return mot + 's';
  }
  // Quantité suivie de son unité accordée (rien pour l'étiquette, unité par défaut).
  function qteU(l, q) {
    var u = unite(l);
    return fN(q) + (u ? ' ' + accord(u, q) : '');
  }
  function libOrigine(o) { return o === 1 ? 'Fabrication' : o === 2 ? 'Stock' : o === 3 ? 'Sous-traitance' : '—'; }

  /* ── Infobulle instantanée ──────────────────────────────────── */

  var TIPS = {};               // id → [titre, texte, note]
  var tipEl = null;
  function tip(id, titre, texte, note) { TIPS[id] = [titre, texte, note]; return id; }
  function montrerTip(cible) {
    var t = TIPS[cible.getAttribute('data-tip')];
    if (!t) return;
    if (!tipEl) { tipEl = h('div', {id: 'adv-tip'}); document.body.appendChild(tipEl); }
    tipEl.textContent = '';
    ajouter(tipEl, [h('div', {className: 'tip-t', text: t[0]}), t[1] ? h('div', {text: t[1]}) : null,
      t[2] ? h('div', {className: 'tip-n', text: t[2]}) : null]);
    var r = cible.getBoundingClientRect();
    tipEl.classList.add('vu');
    var w = tipEl.offsetWidth, hh = tipEl.offsetHeight;
    var x = Math.min(Math.max(8, r.left + r.width / 2 - w / 2), window.innerWidth - w - 8);
    var y = r.bottom + 8;
    if (y + hh > window.innerHeight - 8) y = r.top - hh - 8;
    tipEl.style.left = x + 'px';
    tipEl.style.top = y + 'px';
  }
  function cacherTip() { if (tipEl) tipEl.classList.remove('vu'); }
  document.addEventListener('mouseover', function (ev) {
    if (window.matchMedia && window.matchMedia('(hover: none)').matches) return;
    var c = ev.target.closest && ev.target.closest('[data-tip]');
    if (c) montrerTip(c); else cacherTip();
  });
  document.addEventListener('scroll', cacherTip, true);

  /* ── Adresse ────────────────────────────────────────────────── */

  function lireUrl(complet) {
    var u = MySifaUrl.lire();
    var o = u.get('onglet', null, ONGLETS);
    if (o || complet) S.onglet = o || ONGLETS[0];
    var f = u.get('filtre', null, FILTRES);
    if (f || complet) S.filtre = f || 'tous';
    var t = u.get('tri', null, TRIS);
    if (t || complet) S.tri = t || 'expedition';
    var s = u.get('sens', null, ['asc', 'desc']);
    if (s || complet) S.sens = s || 'asc';
    var hz = parseInt(u.get('horizon', ''), 10);
    if (HORIZONS.indexOf(hz) !== -1) S.horizon = hz; else if (complet) S.horizon = BOOT.horizon || 21;
    var g = u.get('groupe', null, GROUPES);
    if (g || complet) S.groupe = g || 'tous';
    var l = u.get('ligne', null);
    S.ligne = (l && /^\d{1,12}-\d{1,4}$/.test(l)) ? l : null;
    S.reglages = (DROITS.adv && S.onglet === 'commandes' && !S.ligne)
      ? u.get('reglages', null, ['mise_en_forme']) : null;
  }
  function ecrireUrl() {
    var p = {};
    if (S.onglet !== ONGLETS[0]) p.onglet = S.onglet;
    if (S.onglet === 'commandes') {
      if (S.filtre !== 'tous') p.filtre = S.filtre;
      if (S.tri !== 'expedition') p.tri = S.tri;
      if (S.sens !== 'asc') p.sens = S.sens;
    } else {
      if (S.horizon !== (BOOT.horizon || 21)) p.horizon = String(S.horizon);
      if (S.groupe !== 'tous') p.groupe = S.groupe;
    }
    if (S.ligne) p.ligne = S.ligne;
    else if (S.reglages) p.reglages = S.reglages;
    MySifaUrl.ecrire(p, {navigation: S.onglet + (S.ligne ? ':fiche' : S.reglages ? ':reglages' : '')});
  }

  /* ── Données ────────────────────────────────────────────────── */

  async function charger() {
    S.erreur = null;
    try {
      if (S.onglet === 'commandes') {
        S.carnet = await api('/api/adv/commandes');
        S.mef = S.carnet.mises_en_forme || [];
        S.ordre = S.carnet.colonnes_ordre || [];
      }
      else S.prepa = await api('/api/adv/prepa?horizon=' + encodeURIComponent(S.horizon));
    } catch (e) {
      S.erreur = e.message || String(e);
    }
    S.charge = true;
  }
  function donnees() { return S.onglet === 'commandes' ? S.carnet : S.prepa; }
  function ligneParCle(cle) {
    var d = donnees();
    var l = d && (d.lignes || []).find(function (x) { return x.cle === cle; });
    if (l) return l;
    var autre = S.onglet === 'commandes' ? S.prepa : S.carnet;
    return autre && (autre.lignes || []).find(function (x) { return x.cle === cle; });
  }

  function planifierActualisation() {
    clearInterval(minuteur);
    minuteur = setInterval(async function () {
      if (document.hidden || modalOuverte()) return;
      var y = (document.querySelector('.adv-table-wrap') || {}).scrollTop;
      var ym = (document.querySelector('.main') || {}).scrollTop;
      await charger();
      if (modalOuverte()) return;          // une fiche s'est ouverte pendant le chargement
      render();
      var tw = document.querySelector('.adv-table-wrap');
      if (tw && y) tw.scrollTop = y;
      var mn = document.querySelector('.main');
      if (mn && ym) mn.scrollTop = ym;
    }, 120000);
  }

  /* ── Rendu commun ───────────────────────────────────────────── */

  function render() {
    document.querySelectorAll('#adv-nav .nav-btn[data-onglet]').forEach(function (b) {
      var o = b.getAttribute('data-onglet');
      b.style.display = ONGLETS.indexOf(o) === -1 ? 'none' : '';
      b.classList.toggle('active', o === S.onglet);
    });
    var sub = document.getElementById('mobile-sub');
    if (sub) sub.textContent = S.onglet === 'commandes' ? 'Commandes' : 'Prépa';
    document.title = (S.onglet === 'commandes' ? 'Commandes' : 'Prépa') + ' — ADV — MySifa';
    var c = document.getElementById('content');
    var focus = document.activeElement && document.activeElement.id === 'adv-q';
    var caret = focus ? [document.activeElement.selectionStart, document.activeElement.selectionEnd] : null;
    c.textContent = '';
    TIPS = {};
    if (!S.charge) { c.appendChild(h('div', {className: 'adv-chargement', text: 'Chargement…'})); ecrireUrl(); return; }
    if (S.erreur) {
      c.appendChild(h('div', {className: 'adv-avert', text: S.erreur}));
    } else if (S.onglet === 'commandes') {
      renderCommandes(c);
    } else {
      renderPrepa(c);
    }
    if (focus) {
      var q = document.getElementById('adv-q');
      if (q) { q.focus(); try { q.setSelectionRange(caret[0], caret[1]); } catch (e) {} }
    }
    compteursNav();
    monterRvgi();
    ecrireUrl();
    if (S.ligne && !modalOuverte()) ouvrirFiche(S.ligne, true);
    else if (S.reglages && !modalOuverte()) ouvrirReglages(true);
    if (!S.ligne && !S.reglages && modalOuverte()) fermerFiche(true);
  }

  // Date des données RVGI et « Mettre à jour » (static/mysifa_rvgi_synchro.js) :
  // quand le miroir a été reconstruit, la page relit ses données.
  function monterRvgi() {
    if (!window.MySifaRvgiSynchro) return;
    document.querySelectorAll('.adv-rvgi').forEach(function (hote) {
      MySifaRvgiSynchro.monter(hote, {
        peutDemander: !!BOOT.rvgi_demande,
        surErreur: function (m) { toast(m, 'danger'); },
        surMiseAJour: async function () {
          if (modalOuverte()) return;
          await charger();
          if (S.onglet === 'prepa') S.carnet = null; else S.prepa = null;
          render();
          toast('Données RVGI mises à jour.');
        }
      });
    });
  }

  function compteursNav() {
    var a = document.getElementById('adv-nb-commandes');
    if (a) a.textContent = S.carnet && S.carnet.compteurs ? String(S.carnet.compteurs.carnet.lignes) : '';
    var b = document.getElementById('adv-nb-prepa');
    if (b && S.prepa && S.prepa.groupes) {
      var n = S.prepa.groupes.filter(function (g) { return g.cle === 'preparable' || g.cle === 'en_cours'; })
        .reduce(function (s, g) { return s + g.lignes; }, 0);
      b.textContent = String(n);
    }
  }

  function avertissements(c, d) {
    if (d && d.present === false) {
      c.appendChild(h('div', {className: 'adv-avert',
        text: 'Miroir RVGI absent sur ce serveur : le carnet de commandes n’est pas disponible. Il se reconstruit à la prochaine synchronisation.'}));
      return true;
    }
    (d && d.indispo || []).forEach(function (m) { c.appendChild(h('div', {className: 'adv-avert', text: m})); });
    return false;
  }

  // Une étape = un nœud de la frise d'avancement, comme dans la fiche : rond
  // plein franchi, cerclé rouge à faire, pointillé sans objet ou probable. Le
  // libellé est dans l'en-tête de colonne, la valeur et le détail au survol.
  function noeudEtape(l, cle) {
    var e = l.etapes[cle];
    var lib = ETAPES.find(function (x) { return x.cle === cle; });
    var v = e.valeur;
    var note = null;
    if (e.force) {
      note = 'Fixé à la main' + (e.force_par ? ' par ' + e.force_par : '') + (e.force_le ? ' le ' + dateLongue(e.force_le) : '')
        + (e.force_note ? ' · ' + e.force_note : '') + ' · calcul : ' + (ETATS[e.calcul] || e.calcul);
    }
    var n = h('span', {className: 'adv-noeud ' + v + (e.force ? ' force' : ''), role: 'img',
      'aria-label': (lib ? lib.label : cle) + ' : ' + (ETATS[v] || v),
      'data-tip': tip(l.cle + '|' + cle, (lib ? lib.label : cle) + ' · ' + (ETATS[v] || v), e.detail, note)});
    n.innerHTML = ICONES_ETAT[v] || '';   // pictos SVG constants, aucune donnée
    jauge(n, e);
    return n;
  }
  // Stock et Prod en cours : le nœud se remplit de bas en haut à la part faite
  // (96 000 sur 100 000 → rempli à 96 %).
  function pctJauge(e) {
    return e && e.valeur === 'en_cours' && e.jauge !== null && e.jauge !== undefined
      ? Math.floor(Number(e.jauge) * 100 + 1e-9) : null;   // arrondi bas, comme le détail serveur
  }
  function jauge(el, e) {
    var p = pctJauge(e);
    if (p === null) return;
    el.classList.add('jauge');
    el.style.setProperty('--p', String(p));
  }

  function tuile(lib, val, sous, ton, actif, onClick, cle) {
    var attrs = {type: 'button', className: 'adv-tuile' + (ton ? ' ' + ton : '') + (actif ? ' active' : ''), onClick: onClick};
    return h('button', attrs, h('div', {className: 't-lib', text: lib}), h('div', {className: 't-val', text: String(val)}),
      sous ? h('div', {className: 't-sous', text: sous}) : null);
  }

  /* ── Onglet Commandes ───────────────────────────────────────── */

  function filtrer(lignes) {
    var q = norm(S.q).trim();
    return lignes.filter(function (l) {
      if (S.filtre === 'retard' && !l.retard) return false;
      if (S.filtre === 'semaine' && !l.semaine) return false;
      if (S.filtre === 'pretes' && !['bat', 'prod', 'stock', 'prepa'].every(function (k) {
        var v = l.etapes[k].valeur; return v === 'oui' || v === 'sans_objet' || v === 'probable';
      })) return false;
      if (S.filtre.indexOf('etape_') === 0) {
        var v = l.etapes[S.filtre.slice(6)].valeur;
        if (v !== 'non' && v !== 'en_cours') return false;
      }
      if (q) {
        var hay = norm([l.numero, l.client, l.article, l.designation, l.ref_client].join(' '));
        if (hay.indexOf(q) === -1) return false;
      }
      return true;
    });
  }
  function valeurTri(l) {
    switch (S.tri) {
      case 'commande': return l.numero + '-' + String(l.ligne).padStart(4, '0');
      case 'client': return norm(l.client);
      case 'article': return l.article;
      case 'qte': return l.qte;
      case 'stock': return l.stock ? l.stock.alloue : 0;
      case 'a_fabriquer': return l.a_fabriquer;
      case 'livraison': return l.livraison;
      case 'fin_prod': return l.fin_prod;
      default: return l.expedition;
    }
  }
  function trier(lignes) {
    var sens = S.sens === 'desc' ? -1 : 1;
    return lignes.slice().sort(function (a, b) {
      var va = valeurTri(a), vb = valeurTri(b);
      var na = va === null || va === undefined || va === '', nb = vb === null || vb === undefined || vb === '';
      if (na && nb) return 0;
      if (na) return 1;                 // les vides en bas, dans les deux sens
      if (nb) return -1;
      if (va < vb) return -1 * sens;
      if (va > vb) return 1 * sens;
      return 0;
    });
  }

  function renderCommandes(c) {
    var d = S.carnet || {};
    var tete = h('div', {className: 'adv-tete'},
      h('div', {}, h('h1', {text: 'Carnet de commandes'}),
        h('div', {className: 'adv-maj adv-rvgi'})),
      h('div', {className: 'adv-tete-actions'},
        h('button', {type: 'button', className: 'btn adv-btn-icone', 'aria-label': 'Mise en forme conditionnelle',
          'data-tip': tip('btn-mef', 'Mise en forme conditionnelle', S.mef.length ? S.mef.length + ' règle(s) actives' : 'Aucune règle'),
          html: ICONE_REGLAGES, onClick: function () { ouvrirReglages(); }}),
        S.ordre.length ? h('button', {type: 'button', className: 'btn btn-petit',
          'data-tip': tip('btn-ordre', 'Colonnes rangées à votre façon', 'Revenir à l’ordre par défaut'),
          onClick: function () { S.ordre = []; sauverOrdre(); render(); toast('Ordre des colonnes par défaut.'); }}, 'Ordre par défaut') : null,
        h('button', {type: 'button', className: 'btn', onClick: async function () { await charger(); render(); toast('Carnet actualisé.'); }}, 'Actualiser')));
    c.appendChild(tete);
    if (avertissements(c, d)) return;
    var k = d.compteurs || {carnet: {lignes: 0, commandes: 0}, retard: {lignes: 0, commandes: 0},
      semaine: {lignes: 0, commandes: 0}, pretes: {lignes: 0, commandes: 0}, etapes: {}};
    var basculer = function (f) { return function () { S.filtre = S.filtre === f ? 'tous' : f; render(); }; };
    var tuiles = h('div', {className: 'adv-tuiles', 'data-bloc': 'adv.commandes.kpis',
      'data-bloc-valeur-lignes': String(k.carnet.lignes),
      'data-bloc-valeur-commandes': String(k.carnet.commandes),
      'data-bloc-valeur-retard': String(k.retard.lignes),
      'data-bloc-valeur-semaine': String(k.semaine.lignes),
      'data-bloc-valeur-pretes': String(k.pretes.lignes)},
      tuile('Lignes à traiter', k.carnet.lignes, k.carnet.commandes + ' commandes', '', S.filtre === 'tous', basculer('tous')),
      tuile('En retard', k.retard.lignes, k.retard.commandes + ' commandes', k.retard.lignes ? 'danger' : '', S.filtre === 'retard', basculer('retard')),
      tuile('À expédier sous 7 jours', k.semaine.lignes, k.semaine.commandes + ' commandes', k.semaine.lignes ? 'warn' : '', S.filtre === 'semaine', basculer('semaine')),
      tuile('Prêtes à partir', k.pretes.lignes, k.pretes.commandes + ' commandes', k.pretes.lignes ? 'ok' : '', S.filtre === 'pretes', basculer('pretes')));
    c.appendChild(tuiles);

    var barre = h('div', {className: 'adv-barre'});
    var q = h('input', {type: 'search', id: 'adv-q', className: 'adv-recherche', value: S.q,
      placeholder: 'Rechercher (client, commande, article, désignation…)',
      onInput: function (ev) { S.q = ev.target.value; renderTableSeule(); },
      onKeydown: function (ev) { if (ev.key === 'Escape') { S.q = ''; ev.target.value = ''; renderTableSeule(); } }});
    barre.appendChild(q);
    var puces = h('div', {className: 'adv-puces'});
    ETAPES.forEach(function (e) {
      var f = 'etape_' + e.cle;
      var n = (k.etapes[e.cle] || {}).lignes || 0;
      puces.appendChild(h('button', {type: 'button', className: 'adv-puce' + (S.filtre === f ? ' active' : ''),
        'data-tip': tip('puce|' + e.cle, e.label + ' à faire', 'Lignes dont l’étape « ' + e.label + ' » est à faire ou en cours.'),
        onClick: basculer(f)}, e.label, h('span', {className: 'n', text: String(n)})));
    });
    barre.appendChild(puces);
    c.appendChild(barre);
    c.appendChild(h('div', {id: 'adv-table-hote'}));
    renderTableSeule();
  }

  // Seul le tableau se reconstruit à la frappe : la barre de recherche garde
  // son focus et son curseur.
  //
  // Les colonnes sont décrites une fois ici ; leur ORDRE appartient à chaque
  // personne (glisser un en-tête, enregistré en base par /api/adv/preferences).
  var COLONNES = [
    {cle: 'commande', famille: 'id', label: 'Commande', tri: 'commande', td: function (l) {
      return h('td', {className: 'adv-mono'}, l.numero, h('span', {className: 'adv-muet', text: ' · ' + l.ligne}));
    }},
    {cle: 'client', famille: 'id', label: 'Client', tri: 'client', td: function (l) {
      return h('td', {className: 'client', text: l.client});
    }},
    {cle: 'article', famille: 'id', label: 'Article', tri: 'article', td: function (l) {
      return h('td', {className: 'des', 'data-tip': tip(l.cle + '|des', l.article, l.designation, libOrigine(l.origine) + (l.ref_client ? ' · réf. client ' + l.ref_client : ''))},
        h('div', {className: 'adv-mono', text: l.article}), h('div', {className: 'des-l', text: l.designation}));
    }},
    {cle: 'expedition', famille: 'date', label: 'Expédition', tri: 'expedition', td: function (l) {
      return h('td', {className: 'date' + (l.retard ? ' adv-date-retard' : ''), text: dateFr(l.expedition) || '—'});
    }},
    {cle: 'livraison', famille: 'date', label: 'Livraison', tri: 'livraison', td: function (l) {
      return h('td', {className: 'date', text: dateFr(l.livraison) || '—'});
    }},
    {cle: 'fin_prod', famille: 'date', label: 'Fin de prod', tri: 'fin_prod', td: function (l) {
      var tard = l.fin_prod && l.expedition && String(l.fin_prod).slice(0, 10) > l.expedition;
      return h('td', {className: 'date' + (tard ? ' adv-date-tard' : (l.fin_prod ? '' : ' adv-muet')),
        'data-tip': l.fin_prod ? tip(l.cle + '|fin', l.fin_prod_reelle ? 'Fin de production saisie' : 'Fin de production planifiée',
          dateFr(l.fin_prod) + (heure(l.fin_prod) ? ' à ' + heure(l.fin_prod) : ''), tard ? 'Après la date d’expédition' : null) : null,
        text: l.fin_prod ? dateFr(l.fin_prod) : '—'});
    }},
    {cle: 'qte', famille: 'qte', label: 'Commandé', tri: 'qte', num: true, td: function (l) {
      return h('td', {className: 'num'}, fN(l.qte), unite(l) ? h('span', {className: 'adv-muet', text: ' ' + accord(unite(l), l.qte)}) : null);
    }},
    {cle: 'stock', famille: 'qte', label: 'En stock', tri: 'stock', num: true, td: function (l) {
      var a = l.stock ? l.stock.alloue : 0;
      return h('td', {className: 'num' + (a ? '' : ' adv-muet'),
        'data-tip': tip(l.cle + '|stock', 'Stock MyStock attribué à la ligne',
          fN(a) + ' sur ' + fN(l.stock ? l.stock.total : 0) + ' en stock pour cet article',
          l.livre ? 'Déjà livré : ' + fN(l.livre) + ' · reste à livrer ' + fN(l.reste) : 'Les lignes les plus urgentes sont servies d’abord.')},
        a ? fN(a) : '—');
    }},
    {cle: 'a_fabriquer', famille: 'qte', label: 'À fabriquer', tri: 'a_fabriquer', num: true, td: function (l) {
      return h('td', {className: 'num' + (l.a_fabriquer > 0 ? ' adv-fort' : ' adv-muet')}, l.a_fabriquer > 0 ? fN(l.a_fabriquer) : '—');
    }}
  ].concat(ETAPES.map(function (e) {
    return {cle: 'etape_' + e.cle, famille: 'etape', label: e.label, etape: true, td: function (l) {
      return h('td', {className: 'etape'}, noeudEtape(l, e.cle));
    }};
  }));
  var COL_PAR_CLE = {};
  // Une barre verticale sépare deux familles de colonnes (dates, quantités,
  // étapes) — sauf après l'identité de la ligne, qui ouvre le tableau. Calculé
  // sur l'ordre affiché : elle suit les colonnes si la personne les déplace.
  function separee(cols, i) {
    if (i === 0) return false;
    var prev = cols[i - 1].famille, cur = cols[i].famille;
    return cur !== prev && prev !== 'id';
  }
  COLONNES.forEach(function (c) { COL_PAR_CLE[c.cle] = c; });

  // L'ordre de la personne, complété des colonnes qu'il ne connaît pas encore
  // (une colonne ajoutée plus tard apparaît, à sa place par défaut, en fin).
  function colonnesOrdonnees() {
    var vus = {}, out = [];
    (S.ordre || []).forEach(function (k) { if (COL_PAR_CLE[k] && !vus[k]) { vus[k] = 1; out.push(COL_PAR_CLE[k]); } });
    COLONNES.forEach(function (c) { if (!vus[c.cle]) out.push(c); });
    return out;
  }
  var minuteurOrdre = null;
  function sauverOrdre() {
    clearTimeout(minuteurOrdre);
    minuteurOrdre = setTimeout(async function () {
      try { await api('/api/adv/preferences/colonnes', {method: 'PUT', body: {ordre: S.ordre}}); }
      catch (e) { toast('Ordre des colonnes non enregistré : ' + e.message, 'danger'); }
    }, 400);
  }
  function deplacerColonne(de, vers) {
    var ordre = colonnesOrdonnees().map(function (c) { return c.cle; });
    var i = ordre.indexOf(de), j = ordre.indexOf(vers);
    if (i === -1 || j === -1 || i === j) return;
    ordre.splice(i, 1);
    ordre.splice(ordre.indexOf(vers) + (i < j ? 1 : 0), 0, de);
    S.ordre = ordre;
    sauverOrdre();
    render();
  }

  function renderTableSeule() {
    var hote = document.getElementById('adv-table-hote');
    if (!hote) return;
    var ancien = hote.querySelector('.adv-table-wrap') || {};
    var y = ancien.scrollTop || 0, x = ancien.scrollLeft || 0;
    hote.textContent = '';
    var d = S.carnet || {};
    var lignes = trier(filtrer(d.lignes || []));
    if (!lignes.length) {
      hote.appendChild(h('div', {className: 'adv-vide', text: S.q ? 'Aucun résultat pour « ' + S.q + ' »' : 'Aucune ligne pour ce filtre.'}));
      return;
    }
    var cols = colonnesOrdonnees();
    var trTete = h('tr');
    cols.forEach(function (c, i) {
      var actif = c.tri && S.tri === c.tri;
      var sep = separee(cols, i);
      var th = h('th', {className: (c.num ? 'num' : '') + (c.etape ? ' etape' : '') + (sep ? ' sep' : '')
          + (c.tri ? ' triable' : '') + (actif ? ' trie' : ''),
        draggable: 'true', 'data-col': c.cle,
        title: 'Glisser pour déplacer la colonne' + (c.tri ? ' · cliquer pour trier' : '')},
        c.label + (actif ? (S.sens === 'asc' ? ' ↑' : ' ↓') : ''));
      if (c.tri) th.addEventListener('click', function () {
        if (S.tri !== c.tri) { S.tri = c.tri; S.sens = 'asc'; }
        else if (S.sens === 'asc') S.sens = 'desc';
        else { S.tri = 'expedition'; S.sens = 'asc'; }
        renderTableSeule(); ecrireUrl();
      });
      th.addEventListener('dragstart', function (ev) {
        S.colDrag = c.cle; th.classList.add('attrapee');
        try { ev.dataTransfer.effectAllowed = 'move'; ev.dataTransfer.setData('text/plain', c.cle); } catch (e) {}
      });
      th.addEventListener('dragend', function () {
        S.colDrag = null;
        trTete.querySelectorAll('th').forEach(function (t) { t.classList.remove('attrapee', 'cible'); });
      });
      th.addEventListener('dragover', function (ev) {
        if (!S.colDrag || S.colDrag === c.cle) return;
        ev.preventDefault(); th.classList.add('cible');
      });
      th.addEventListener('dragleave', function () { th.classList.remove('cible'); });
      th.addEventListener('drop', function (ev) {
        ev.preventDefault(); th.classList.remove('cible');
        if (S.colDrag && S.colDrag !== c.cle) deplacerColonne(S.colDrag, c.cle);
        S.colDrag = null;
      });
      trTete.appendChild(th);
    });
    var tbody = h('tbody');
    lignes.forEach(function (l) {
      var tr = h('tr', {onClick: function () { ouvrirFiche(l.cle); }});
      cols.forEach(function (c, i) {
        var td = c.td(l);
        if (separee(cols, i)) td.classList.add('sep');
        if (c.etape) {
          // Le trait relie deux étapes voisines ; il passe au vert quand
          // l'étape où il arrive est franchie, comme la frise de la fiche.
          var etat = function (col) { return l.etapes[col.cle.slice(6)].valeur; };
          td.classList.add('v-' + etat(c));
          if (cols[i - 1] && cols[i - 1].etape) td.classList.add('lien-g');
          if (cols[i + 1] && cols[i + 1].etape) td.classList.add('lien-d', 'suiv-' + etat(cols[i + 1]));
        }
        var ton = S.mef.length ? tonCellule(l, c.cle) : null;
        if (ton) {
          td.classList.add('mef', 'mef-' + ton);
          // Hors étapes (déjà en pastille), la valeur passe dans une pastille
          // teintée : on voit la règle sans perdre la lecture de la colonne.
          if (!c.etape) {
            var p = h('span', {className: 'mef-p'});
            while (td.firstChild) p.appendChild(td.firstChild);
            td.appendChild(p);
          }
        }
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    var wrap = h('div', {className: 'adv-table-wrap'}, h('table', {className: 'adv-table'}, h('thead', {}, trTete), tbody));
    hote.appendChild(wrap);
    if (y) wrap.scrollTop = y;
    if (x) wrap.scrollLeft = x;
  }

  /* ── Onglet Prépa ───────────────────────────────────────────── */

  async function changerPrepa(l, statut, bouton) {
    if (bouton) bouton.disabled = true;
    try {
      await api('/api/adv/prepa/' + encodeURIComponent(l.numero) + '/' + l.ligne, {method: 'PUT', body: {statut: statut}});
      toast('Prépa ' + l.numero + ' · ' + l.ligne + ' : ' + (LIB_PREPA[statut] || statut).toLowerCase() + '.');
      var y = (document.querySelector('.main') || {}).scrollTop;
      await charger();
      // L'autre onglet se relira à son ouverture : sa prépa est périmée.
      if (S.onglet === 'prepa') S.carnet = null; else S.prepa = null;
      render();
      if (modalOuverte()) { fermerFiche(true); ouvrirFiche(l.cle, true); }
      var mn = document.querySelector('.main');
      if (mn && y) mn.scrollTop = y;
    } catch (e) {
      toast(e.message, 'danger');
      if (bouton) bouton.disabled = false;
    }
  }

  function boutonsPrepa(l) {
    var s = l.prepa.statut;
    var b = function (lib, statut, cls) {
      var el = h('button', {type: 'button', className: 'btn btn-petit' + (cls ? ' ' + cls : ''),
        onClick: function (ev) { ev.stopPropagation(); changerPrepa(l, statut, el); }}, lib);
      return el;
    };
    // Un seul geste : « Prête ». Une prépa déjà prête peut être remise à préparer.
    if (s === 'prete') return [b('Remettre à préparer', 'a_preparer')];
    return [b('Prête', 'prete', 'btn-accent')];
  }

  // Une préparation = UNE ligne, une valeur par colonne, sans sous-texte :
  // rang, client, commande (« 9932425-L3 »), réf produit, commandé, unité, en
  // stock, à préparer, où prélever, expédition, et le bouton « Prête ». Le
  // détail (désignation, manque, fin de prod, enlèvement, auteur) est au
  // survol ou dans la fiche. L'administration et la direction peuvent changer
  // l'ordre : glisser la ligne, ou ses flèches ↑ ↓ ; il s'impose à la logistique.
  function cartePrepa(l, rang, ctx) {
    var st = l.stock || {};
    var uniteReelle = (st.unite || 'étiquette');
    var sortie = st.sortie_prod || 0;     // stock « probable » : sortie de production
    var manque = l.groupe !== 'attente' && st.alloue + sortie < l.reste ? l.reste - st.alloue - sortie : 0;
    var aPrep = h('div', {className: 'c-num c-fort c-aprep' + (l.groupe === 'attente' ? ' c-fab' : (manque ? ' adv-date-tard' : '')),
        'data-l': l.groupe === 'attente' ? 'À produire' : 'À préparer',
        'data-tip': l.groupe === 'attente'
          ? tip(l.cle + '|aprep', 'À produire', l.fin_prod ? 'Fin de prod ' + dateFr(l.fin_prod) + (heure(l.fin_prod) ? ' ' + heure(l.fin_prod) : '') : l.etapes.prod.detail)
          : (manque ? tip(l.cle + '|aprep', sortie ? 'Production un peu sous la commande' : 'Stock partiel',
              'Manque ' + fN(manque) + ' ' + accord(uniteReelle, manque)) : null)},
      fN(l.reste));
    var empl;
    if (st.emplacements && st.emplacements.length && l.groupe !== 'attente') {
      empl = h('div', {className: 'adv-empl'}, st.emplacements.map(function (e) {
        return h('span', {'data-tip': tip(l.cle + '|lot' + e.lot_id, 'Emplacement ' + e.emplacement, 'Prélever ' + qteU(l, e.quantite), e.date_entree ? 'Entré le ' + dateLongue(e.date_entree) + ' (FIFO)' : null)},
          h('b', {text: e.emplacement}), ' · ' + fN(e.quantite));
      }));
    } else if (!sortie) {
      empl = h('div', {className: 'adv-empl adv-muet', text: '—'});
    }
    if (sortie && l.groupe !== 'attente') {
      var puce = h('span', {className: 'adv-sortie-prod',
          'data-tip': tip(l.cle + '|sortie', 'Sortie de production', l.etapes.stock.detail,
            (st.dossiers_prod || []).length ? 'Dossier ' + st.dossiers_prod.join(', ') : null)},
        h('b', {text: 'Sortie prod'}), ' · ' + fN(sortie));
      if (empl) empl.appendChild(puce);
      else empl = h('div', {className: 'adv-empl'}, puce);
    }
    var dp = l.departs && l.departs.length ? l.departs[0] : null;
    var notesQuand = [];
    if (dp) notesQuand.push('Enlèvement ' + dateLongue(dp.date_enlevement) + (dp.transporteur ? ' · ' + dp.transporteur : '') + (dp.parti_le ? ' · parti' : ''));
    if (l.prepa.statut !== 'a_preparer' && l.prepa.maj_par) {
      notesQuand.push((LIB_PREPA[l.prepa.statut] || '') + ' · ' + l.prepa.maj_par + ' ' + dateFr(l.prepa.maj_le) + ' ' + heure(l.prepa.maj_le));
    }
    var quand = h('div', {className: 'c-quand' + (l.retard ? ' adv-date-retard' : ''),
      'data-tip': tip(l.cle + '|quand', 'Expédition ' + (dateLongue(l.expedition) || 'non datée') + (l.retard ? ' · en retard' : ''),
        notesQuand[0] || null, notesQuand[1] || null)},
      l.expedition ? dateFr(l.expedition) : 'Non datée');

    var manuel = l.priorite_manuelle !== null && l.priorite_manuelle !== undefined;
    var rangEl = h('div', {className: 'adv-rang' + (manuel ? ' manuel' : ''),
      'data-tip': tip(l.cle + '|rang', manuel ? 'Ordre fixé à la main' : 'Ordre automatique',
        manuel ? (l.priorite_par ? 'Par ' + l.priorite_par : '') + (l.priorite_le ? ' le ' + dateFr(l.priorite_le) : '') : 'Par date d’expédition',
        ctx && DROITS.adv ? 'Glisser la ligne ou utiliser ↑ ↓ pour changer l’ordre' : null)}, String(rang));
    var cellRang = h('div', {className: 'c-rang'}, rangEl);
    if (ctx && DROITS.adv) {
      var fleche = function (sens, lib) {
        var cible = ctx.index + sens;
        return h('button', {type: 'button', className: 'adv-fleche', 'aria-label': lib, disabled: cible < 0 || cible >= ctx.lignes.length,
          onClick: function (ev) { ev.stopPropagation(); deplacerPrepa(ctx.lignes, ctx.index, cible); }}, sens < 0 ? '↑' : '↓');
      };
      cellRang.appendChild(h('div', {className: 'adv-fleches'}, fleche(-1, 'Monter'), fleche(1, 'Descendre')));
    }

    var ligne = h('div', {className: 'adv-carte' + (l.retard ? ' retard' : ''), 'data-cle': l.cle,
        onClick: function () { ouvrirFiche(l.cle); }},
      cellRang,
      h('div', {className: 'c-client', text: l.client}),
      h('div', {className: 'c-cde adv-mono', text: l.numero + '-L' + l.ligne}),
      h('div', {className: 'c-ref adv-mono', text: l.article, 'data-tip': tip(l.cle + '|ref', l.article, l.designation)}),
      h('div', {className: 'c-num c-qte', 'data-l': 'Commandé · ' + accord(uniteReelle, l.qte)}, fN(l.qte)),
      h('div', {className: 'c-unite', 'data-l': 'Unité', text: accord(uniteReelle, l.qte)}),
      h('div', {className: 'c-num c-stk' + (st.alloue ? '' : ' adv-muet'), 'data-l': 'En stock'}, st.alloue ? fN(st.alloue) : '—'),
      aPrep,
      empl, quand,
      h('div', {className: 'adv-actions'}, boutonsPrepa(l)));

    // Glisser-déposer, dans le groupe seulement : on ne change pas une
    // préparation de groupe en la déplaçant (le groupe dit où elle en est).
    if (ctx && DROITS.adv) {
      ligne.setAttribute('draggable', 'true');
      ligne.addEventListener('dragstart', function (ev) {
        S.prepaDrag = {cle: l.cle, groupe: l.groupe, index: ctx.index};
        ligne.classList.add('attrapee');
        try { ev.dataTransfer.effectAllowed = 'move'; ev.dataTransfer.setData('text/plain', l.cle); } catch (e) {}
      });
      ligne.addEventListener('dragend', function () {
        S.prepaDrag = null;
        document.querySelectorAll('.adv-carte.attrapee, .adv-carte.cible-haut, .adv-carte.cible-bas').forEach(function (x) {
          x.classList.remove('attrapee', 'cible-haut', 'cible-bas');
        });
      });
      ligne.addEventListener('dragover', function (ev) {
        var d = S.prepaDrag;
        if (!d || d.groupe !== l.groupe || d.cle === l.cle) return;
        ev.preventDefault();
        var bas = d.index < ctx.index;
        ligne.classList.toggle('cible-bas', bas);
        ligne.classList.toggle('cible-haut', !bas);
      });
      ligne.addEventListener('dragleave', function () { ligne.classList.remove('cible-haut', 'cible-bas'); });
      ligne.addEventListener('drop', function (ev) {
        var d = S.prepaDrag;
        ligne.classList.remove('cible-haut', 'cible-bas');
        if (!d || d.groupe !== l.groupe || d.cle === l.cle) return;
        ev.preventDefault();
        S.prepaDrag = null;
        deplacerPrepa(ctx.lignes, d.index, ctx.index);
      });
    }
    return ligne;
  }

  // Déplace la ligne `de` à la place `vers` dans son groupe, puis enregistre
  // le rang des lignes du haut du groupe jusqu'à la plus basse des deux
  // positions : le reste du groupe garde l'ordre automatique, et une ligne
  // urgente qui arrive demain viendra encore se classer par sa date.
  async function deplacerPrepa(lignesGroupe, de, vers) {
    if (de === vers || vers < 0 || vers >= lignesGroupe.length) return;
    var ordre = lignesGroupe.map(function (x) { return x.cle; });
    var cle = ordre.splice(de, 1)[0];
    ordre.splice(vers, 0, cle);
    var envoi = ordre.slice(0, Math.max(de, vers) + 1);
    var y = (document.querySelector('.main') || {}).scrollTop;
    try {
      await api('/api/adv/prepa/ordre', {method: 'PUT', body: {lignes: envoi}});
      await charger();
      S.carnet = null;              // l'attribution du stock a pu bouger
      render();
      var mn = document.querySelector('.main');
      if (mn && y) mn.scrollTop = y;
    } catch (e) { toast(e.message, 'danger'); }
  }

  function entetePrepa(groupe) {
    return h('div', {className: 'adv-carte adv-carte-tete', 'aria-hidden': 'true'},
      h('div', {text: '#'}), h('div', {text: 'Client'}), h('div', {text: 'Commande'}), h('div', {text: 'Réf produit'}),
      h('div', {className: 'c-num', text: 'Commandé'}), h('div', {text: 'Unité'}), h('div', {className: 'c-num', text: 'En stock'}),
      h('div', {className: 'c-num', text: groupe === 'attente' ? 'À produire' : 'À préparer'}),
      h('div', {text: groupe === 'attente' ? '' : 'Où prélever'}),
      h('div', {text: 'Expédition'}), h('div'));
  }

  function renderPrepa(c) {
    var d = S.prepa || {};
    var tete = h('div', {className: 'adv-tete'},
      h('div', {}, h('h1', {text: 'Préparations'}),
        h('div', {className: 'adv-maj'}, h('span', {className: 'adv-rvgi'}),
          h('span', {text: ' · ' + (d.ordre_manuel ? 'Ordre fixé par l’ADV, puis date d’expédition' : 'Par date d’expédition, retards en tête')}))),
      h('div', {className: 'adv-puces'}, HORIZONS.map(function (n) {
        return h('button', {type: 'button', className: 'adv-puce' + (S.horizon === n ? ' active' : ''),
          onClick: async function () { S.horizon = n; S.charge = false; render(); await charger(); render(); }}, n + ' jours');
      }),
      DROITS.adv && d.ordre_manuel ? h('button', {type: 'button', className: 'btn btn-petit',
        'data-tip': tip('btn-ordre-auto', 'Revenir à l’ordre automatique', 'Retire tous les rangs fixés à la main : la Prépa se range de nouveau par date d’expédition.'),
        onClick: async function () {
          try {
            await api('/api/adv/prepa/ordre', {method: 'DELETE'});
            await charger(); S.carnet = null; render();
            toast('Ordre automatique rétabli.');
          } catch (e) { toast(e.message, 'danger'); }
        }}, 'Ordre automatique') : null,
      h('button', {type: 'button', className: 'btn btn-petit', onClick: async function () { await charger(); render(); toast('Préparations actualisées.'); }}, 'Actualiser')));
    c.appendChild(tete);
    if (avertissements(c, d)) return;
    var groupes = d.groupes || [];
    var n = function (cle) { var g = groupes.find(function (x) { return x.cle === cle; }); return g ? g.lignes : 0; };
    var basculer = function (g) { return function () { S.groupe = S.groupe === g ? 'tous' : g; render(); }; };
    c.appendChild(h('div', {className: 'adv-tuiles', 'data-bloc': 'adv.prepa.kpis',
      'data-bloc-valeur-preparable': String(n('preparable')),
      'data-bloc-valeur-en-cours': String(n('en_cours')),
      'data-bloc-valeur-partiel': String(n('partiel')),
      'data-bloc-valeur-attente': String(n('attente')),
      'data-bloc-valeur-pretes': String(n('pretes'))},
      tuile('En cours', n('en_cours'), null, '', S.groupe === 'en_cours', basculer('en_cours')),
      tuile('À préparer', n('preparable'), 'disponible', n('preparable') ? 'warn' : '', S.groupe === 'preparable', basculer('preparable')),
      tuile('Stock partiel', n('partiel'), null, '', S.groupe === 'partiel', basculer('partiel')),
      tuile('Attente de prod', n('attente'), null, '', S.groupe === 'attente', basculer('attente')),
      tuile('Prêtes', n('pretes'), 'en attente de départ', n('pretes') ? 'ok' : '', S.groupe === 'pretes', basculer('pretes'))));

    var lignes = d.lignes || [];
    if (!lignes.length) {
      c.appendChild(h('div', {className: 'adv-vide', text: 'Aucune préparation sur les ' + S.horizon + ' prochains jours.'}));
      return;
    }
    var rang = 0;
    var rangs = {};
    // Le rang suit l'ordre de travail : ce qui se prépare maintenant d'abord.
    ['en_cours', 'preparable', 'partiel'].forEach(function (g) {
      lignes.filter(function (l) { return l.groupe === g; }).forEach(function (l) { rangs[l.cle] = ++rang; });
    });
    groupes.forEach(function (g) {
      if (S.groupe !== 'tous' && S.groupe !== g.cle) return;
      var ls = lignes.filter(function (l) { return l.groupe === g.cle; });
      if (!ls.length) return;
      var bloc = h('div', {className: 'adv-groupe'}, h('h2', {}, g.label, h('span', {className: 'n', text: String(ls.length)})),
        entetePrepa(g.cle));
      ls.forEach(function (l, i) { bloc.appendChild(cartePrepa(l, rangs[l.cle] || '·', {lignes: ls, index: i})); });
      c.appendChild(bloc);
    });
  }

  /* ── Mise en forme conditionnelle ───────────────────────────── */

  var REF = BOOT.mef || {colonnes: [], operateurs: {}, cibles: [], tons: [], max: 40};
  var TYPE_COL = {}, LIB_COL = {};
  REF.colonnes.forEach(function (c) { TYPE_COL[c.cle] = c.type; LIB_COL[c.cle] = c.label; });
  var ICONE_REGLAGES = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/></svg>';

  function aujourdhuiPlus(n) {
    var d = new Date();
    d.setDate(d.getDate() + (parseInt(n, 10) || 0));
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  }
  // La valeur d'une cellule, telle qu'on la compare (nombre, date AAAA-MM-JJ, texte, état).
  function valeurMef(l, col) {
    switch (col) {
      case 'commande': return l.numero;
      case 'client': return l.client;
      case 'article': return l.article;
      case 'qte': return l.qte;
      case 'stock': return l.stock ? l.stock.alloue : 0;
      case 'a_fabriquer': return l.a_fabriquer;
      case 'expedition': return l.expedition;
      case 'livraison': return l.livraison;
      case 'fin_prod': return l.fin_prod ? String(l.fin_prod).slice(0, 10) : null;
      default:
        if (col.indexOf('etape_') === 0) { var e = l.etapes[col.slice(6)]; return e ? e.valeur : null; }
        return null;
    }
  }
  function vide(v) { return v === null || v === undefined || v === ''; }
  function regleVraie(rg, l) {
    var typ = TYPE_COL[rg.colonne];
    var v = valeurMef(l, rg.colonne);
    if (rg.operateur === 'vide') return vide(v);
    if (rg.operateur === 'non_vide') return !vide(v);
    if (vide(v)) return false;
    var c;
    if (rg.cible === 'colonne') c = valeurMef(l, rg.valeur);
    else if (rg.cible === 'aujourdhui') c = aujourdhuiPlus(rg.valeur);
    else c = rg.valeur;
    if (vide(c)) return false;
    if (typ === 'nombre') {
      v = Number(v); c = Number(String(c).replace(',', '.').replace(/[\s ]/g, ''));
      if (isNaN(v) || isNaN(c)) return false;
    }
    if (typ === 'texte') {
      v = norm(v); c = norm(c);
      if (rg.operateur === 'contient') return v.indexOf(c) !== -1;
      if (rg.operateur === 'commence') return v.indexOf(c) === 0;
      return v === c;
    }
    switch (rg.operateur) {
      case 'gt': return v > c;
      case 'ge': return v >= c;
      case 'lt': return v < c;
      case 'le': return v <= c;
      case 'eq': return v === c || v == c;
      case 'ne': return v !== c;
      default: return false;
    }
  }
  // La première règle qui s'applique à la cellule l'emporte.
  function tonCellule(l, col, regles) {
    var rs = regles || S.mef;
    for (var i = 0; i < rs.length; i++) {
      if (rs[i].colonne === col && regleVraie(rs[i], l)) return rs[i].ton;
    }
    return null;
  }
  function libRegle(rg) {
    var typ = TYPE_COL[rg.colonne];
    var op = (REF.operateurs[typ] || []).find(function (o) { return o.cle === rg.operateur; });
    var txt = (LIB_COL[rg.colonne] || rg.colonne) + ' ' + (op ? op.label : rg.operateur);
    if (rg.operateur === 'vide' || rg.operateur === 'non_vide') return txt;
    if (rg.cible === 'colonne') return txt + ' ' + (LIB_COL[rg.valeur] || rg.valeur);
    if (rg.cible === 'aujourdhui') {
      var n = parseInt(rg.valeur, 10) || 0;
      return txt + ' aujourd’hui' + (n ? (n > 0 ? ' + ' : ' − ') + Math.abs(n) + ' j' : '');
    }
    if (typ === 'etat') return txt + ' ' + (ETATS[rg.valeur] || rg.valeur);
    if (typ === 'date') return txt + ' ' + dateLongue(rg.valeur);
    return txt + ' ' + rg.valeur;
  }

  function regleParDefaut() {
    return {colonne: 'a_fabriquer', operateur: 'gt', cible: 'valeur', valeur: '0', ton: 'warn'};
  }
  function ciblesPour(typ) {
    if (typ === 'nombre') return ['valeur', 'colonne'];
    if (typ === 'date') return ['valeur', 'aujourdhui', 'colonne'];
    return ['valeur'];
  }
  function valeurParDefaut(typ, cible) {
    if (cible === 'aujourdhui') return '0';
    if (cible === 'colonne') return '';
    if (typ === 'nombre') return '0';
    if (typ === 'date') return aujourdhuiPlus(0);
    if (typ === 'etat') return 'non';
    return '';
  }

  function ouvrirReglages(sansAdresse) {
    if (!DROITS.adv) return;
    var m = document.getElementById('mroot');
    m.textContent = '';
    S.ligne = null;
    S.reglages = 'mise_en_forme';
    if (!sansAdresse) ecrireUrl();
    // Copie de travail : rien n'est appliqué au carnet avant « Enregistrer ».
    var E = S.mef.map(function (r) {
      return {colonne: r.colonne, operateur: r.operateur, cible: r.cible || 'valeur', valeur: r.valeur || '', ton: r.ton};
    });
    var liste = h('div', {className: 'mef-liste'});
    var pied = h('div', {className: 'mef-compte adv-muet'});
    var lignes = (S.carnet && S.carnet.lignes) || [];

    function nbCellules(rg) {
      var n = 0;
      lignes.forEach(function (l) { if (tonCellule(l, rg.colonne, [rg]) ) n++; });
      return n;
    }
    function select(options, valeur, onChange, label) {
      var el = h('select', {'aria-label': label});
      options.forEach(function (o) {
        var opt = h('option', {value: o.cle}, o.label);
        if (o.cle === valeur) opt.selected = true;
        el.appendChild(opt);
      });
      el.addEventListener('change', function () { onChange(el.value); });
      return el;
    }
    function dessiner() {
      liste.textContent = '';
      if (!E.length) {
        liste.appendChild(h('div', {className: 'adv-vide', text: 'Aucune règle. Exemple : « À fabriquer > 0 » en orange, « Fin de prod après Expédition » en rouge.'}));
      }
      E.forEach(function (rg, i) {
        var typ = TYPE_COL[rg.colonne];
        var sansCible = rg.operateur === 'vide' || rg.operateur === 'non_vide';
        var compte = h('span', {className: 'mef-n adv-muet'});
        function majCompte() { compte.textContent = nbCellules(rg) + ' cell.'; }
        var colSel = select(REF.colonnes, rg.colonne, function (v) {
          rg.colonne = v;
          var t = TYPE_COL[v];
          rg.operateur = (REF.operateurs[t] || [])[0].cle;
          rg.cible = 'valeur';
          rg.valeur = valeurParDefaut(t, 'valeur');
          dessiner();
        }, 'Colonne');
        var opSel = select(REF.operateurs[typ] || [], rg.operateur, function (v) { rg.operateur = v; dessiner(); }, 'Condition');
        var zoneValeur = h('div', {className: 'mef-valeur'});
        if (!sansCible) {
          var cibles = ciblesPour(typ);
          if (cibles.length > 1) {
            zoneValeur.appendChild(select(REF.cibles.filter(function (c) { return cibles.indexOf(c.cle) !== -1; }), rg.cible, function (v) {
              rg.cible = v; rg.valeur = valeurParDefaut(typ, v); dessiner();
            }, 'Comparer à'));
          }
          var champ;
          if (rg.cible === 'colonne') {
            var autres = REF.colonnes.filter(function (c) { return c.type === typ && c.cle !== rg.colonne; });
            if (!rg.valeur && autres.length) rg.valeur = autres[0].cle;
            champ = select(autres, rg.valeur, function (v) { rg.valeur = v; majCompte(); }, 'Colonne de comparaison');
          } else if (typ === 'etat') {
            champ = select(Object.keys(ETATS).map(function (k) { return {cle: k, label: ETATS[k]}; }), rg.valeur, function (v) { rg.valeur = v; majCompte(); }, 'État');
          } else {
            var type = rg.cible === 'aujourdhui' ? 'number' : (typ === 'nombre' ? 'number' : (typ === 'date' ? 'date' : 'text'));
            champ = h('input', {type: type, value: rg.valeur, 'aria-label': 'Valeur',
              placeholder: rg.cible === 'aujourdhui' ? '± jours' : (typ === 'texte' ? 'Texte' : '')});
            champ.addEventListener('input', function () { rg.valeur = champ.value; majCompte(); });
          }
          zoneValeur.appendChild(champ);
          if (rg.cible === 'aujourdhui') zoneValeur.appendChild(h('span', {className: 'adv-muet', text: 'jours'}));
        }
        var tons = h('div', {className: 'mef-tons', role: 'radiogroup', 'aria-label': 'Couleur'});
        REF.tons.forEach(function (t) {
          tons.appendChild(h('button', {type: 'button', className: 'mef-ton mef-' + t.cle + (rg.ton === t.cle ? ' actif' : ''),
            role: 'radio', 'aria-checked': rg.ton === t.cle ? 'true' : 'false', 'aria-label': t.label,
            'data-tip': tip('mef-ton|' + i + '|' + t.cle, t.label),
            onClick: function () { rg.ton = t.cle; dessiner(); }}));
        });
        var bouger = function (d) {
          return function () {
            var j = i + d;
            if (j < 0 || j >= E.length) return;
            var x = E[i]; E[i] = E[j]; E[j] = x;
            dessiner();
          };
        };
        liste.appendChild(h('div', {className: 'mef-regle'},
          h('span', {className: 'mef-rang', text: String(i + 1)}),
          colSel, opSel, zoneValeur, tons, compte,
          h('div', {className: 'mef-ordre'},
            h('button', {type: 'button', className: 'btn btn-petit', 'aria-label': 'Monter', disabled: i === 0, onClick: bouger(-1)}, '↑'),
            h('button', {type: 'button', className: 'btn btn-petit', 'aria-label': 'Descendre', disabled: i === E.length - 1, onClick: bouger(1)}, '↓'),
            h('button', {type: 'button', className: 'btn btn-petit', 'aria-label': 'Supprimer la règle',
              onClick: function () { E.splice(i, 1); dessiner(); }}, '×'))));
        majCompte();
      });
      pied.textContent = E.length + ' / ' + REF.max + ' règles · la première qui s’applique à une cellule l’emporte';
      ajout.disabled = E.length >= REF.max;
    }
    var ajout = h('button', {type: 'button', className: 'btn btn-petit', onClick: function () { E.push(regleParDefaut()); dessiner(); }}, '+ Ajouter une règle');
    var enregistrer = h('button', {type: 'button', className: 'btn btn-accent', onClick: async function () {
      enregistrer.disabled = true;
      try {
        var res = await api('/api/adv/mises-en-forme', {method: 'PUT', body: {regles: E}});
        S.mef = res.regles || [];
        if (S.carnet) S.carnet.mises_en_forme = S.mef;
        fermerFiche();
        render();
        toast('Mise en forme enregistrée.');
      } catch (e) {
        toast(e.message, 'danger');
        enregistrer.disabled = false;
      }
    }}, 'Enregistrer');
    var modal = h('div', {className: 'adv-modal adv-modal-large', role: 'dialog', 'aria-modal': 'true'},
      h('h3', {text: 'Mise en forme conditionnelle'}),
      h('div', {className: 'm-sous', text: 'Colore une cellule du carnet quand sa valeur remplit la condition. Règles communes à tout le service.'}),
      liste,
      h('div', {className: 'mef-bas'}, ajout, pied),
      h('div', {className: 'm-pied'},
        h('button', {type: 'button', className: 'btn', onClick: function () { fermerFiche(); }}, 'Annuler'),
        enregistrer));
    var voile = h('div', {className: 'adv-voile', onClick: function (ev) { if (ev.target === voile) fermerFiche(); }}, modal);
    m.appendChild(voile);
    dessiner();
  }

  /* ── Fiche d'une ligne ──────────────────────────────────────── */

  function fermerFiche(sansAdresse) {
    var m = document.getElementById('mroot');
    if (m) m.textContent = '';
    cacherTip();
    if (sansAdresse === true) return;
    S.ligne = null;
    S.reglages = null;
    ecrireUrl();
  }

  async function fixerRepiquage(l, statut) {
    try {
      await api('/api/adv/repiquage/' + encodeURIComponent(l.numero) + '/' + l.ligne, {method: 'PUT', body: {statut: statut}});
      toast(statut ? 'Repiquage : ' + (LIB_REPIQUAGE[statut] || statut).toLowerCase() + '.' : 'Statut du planning rétabli.');
      await charger();
      if (S.onglet === 'prepa') S.carnet = null; else S.prepa = null;
      render();
      fermerFiche(true);
      ouvrirFiche(l.cle, true);
    } catch (e) { toast(e.message, 'danger'); }
  }

  async function forcer(l, etape, valeur, note) {
    try {
      await api('/api/adv/forcage/' + encodeURIComponent(l.numero) + '/' + l.ligne + '/' + etape,
        {method: 'PUT', body: {valeur: valeur || null, note: note || null}});
      toast(valeur ? 'Étape fixée.' : 'Calcul rétabli.');
      S.ficheEtape = null;
      await charger();
      if (S.onglet === 'prepa') S.carnet = null; else S.prepa = null;
      render();
      fermerFiche(true);
      ouvrirFiche(l.cle, true);
    } catch (e) { toast(e.message, 'danger'); }
  }

  var ICONES_ETAT = {
    oui: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',
    en_cours: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="8"/><polyline points="12 8 12 12 15 14"/></svg>',
    non: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><line x1="7" y1="7" x2="17" y2="17"/><line x1="17" y1="7" x2="7" y2="17"/></svg>',
    sans_objet: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><line x1="7" y1="12" x2="17" y2="12"/></svg>',
    probable: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>'
  };
  // « dans 3 j », « il y a 5 j », « aujourd’hui » : on ne soustrait pas de tête.
  function relatif(s) {
    if (!s) return '';
    var a = new Date(String(s).slice(0, 10) + 'T00:00:00'), b = new Date();
    b.setHours(0, 0, 0, 0);
    var n = Math.round((a - b) / 86400000);
    if (n === 0) return 'aujourd’hui';
    if (n === 1) return 'demain';
    if (n === -1) return 'hier';
    return n > 0 ? 'dans ' + n + ' j' : 'il y a ' + (-n) + ' j';
  }

  function ouvrirFiche(cle, sansAdresse) {
    var l = ligneParCle(cle);
    if (!l) {
      if (!donnees()) return;               // données pas encore là : render() rouvrira
      S.ligne = null; ecrireUrl();
      toast('Cette ligne n’est plus dans le carnet.', 'danger');
      return;
    }
    var m = document.getElementById('mroot');
    m.textContent = '';
    cacherTip();
    S.reglages = null;
    if (S.ligne !== cle) S.ficheEtape = null;
    if (!sansAdresse) { S.ligne = cle; ecrireUrl(); }
    else S.ligne = cle;
    var st = l.stock || {};
    var fermer = function () { fermerFiche(); };

    // ── En-tête ──
    var puces = h('div', {className: 'fi-puces'},
      h('span', {className: 'adv-badge', text: libOrigine(l.origine)}),
      l.ref_client ? h('span', {className: 'adv-badge', text: 'Réf. client ' + l.ref_client}) : null,
      l.creee_le ? h('span', {className: 'adv-badge', text: 'Créée le ' + dateFr(l.creee_le)}) : null,
      l.retard ? h('span', {className: 'adv-badge danger', text: 'En retard'}) : null);
    var tete = h('div', {className: 'fi-tete'},
      h('div', {className: 'fi-titre'},
        h('h3', {text: l.client}),
        h('div', {className: 'fi-ref adv-mono', text: l.numero + ' · ligne ' + l.ligne + ' · ' + l.article}),
        h('div', {className: 'fi-des', text: l.designation}),
        puces),
      h('button', {type: 'button', className: 'fi-fermer', 'aria-label': 'Fermer', onClick: fermer, html:
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><line x1="6" y1="6" x2="18" y2="18"/><line x1="18" y1="6" x2="6" y2="18"/></svg>'}));

    // ── Chaîne de valeur : une frise de 5 étapes ──
    var frise = h('div', {className: 'fi-frise'});
    ETAPES.forEach(function (e) {
      var et = l.etapes[e.cle];
      var corrigeable = DROITS.adv && e.cle !== 'prepa';
      var noeud = h('div', {className: 'fi-etape ' + et.valeur + (et.force ? ' force' : '') + (S.ficheEtape === e.cle ? ' ouverte' : '') + (corrigeable ? ' cliquable' : ''),
        role: corrigeable ? 'button' : null, tabindex: corrigeable ? '0' : null,
        'data-tip': tip(l.cle + '|fi|' + e.cle, e.label + ' · ' + (ETATS[et.valeur] || et.valeur), et.detail,
          et.force ? 'Fixé à la main' + (et.force_par ? ' par ' + et.force_par : '') + (et.force_note ? ' · ' + et.force_note : '') + ' · calcul : ' + (ETATS[et.calcul] || et.calcul)
            : (corrigeable ? 'Cliquer pour corriger' : null))},
        h('div', {className: 'fi-rond', html: ICONES_ETAT[et.valeur] || ''}),
        h('div', {className: 'fi-etape-lib', text: e.label}),
        h('div', {className: 'fi-etape-val', text: (ETATS[et.valeur] || et.valeur) + (pctJauge(et) !== null ? ' · ' + pctJauge(et) + ' %' : '')}),
        h('div', {className: 'fi-etape-det', text: et.detail}));
      jauge(noeud.querySelector('.fi-rond'), et);
      if (corrigeable) {
        var basculer = function () { S.ficheEtape = S.ficheEtape === e.cle ? null : e.cle; ouvrirFiche(l.cle, true); };
        noeud.addEventListener('click', basculer);
        noeud.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); basculer(); } });
      }
      frise.appendChild(noeud);
    });

    var correction = null;
    if (S.ficheEtape && DROITS.adv) {
      var ec = ETAPES.find(function (x) { return x.cle === S.ficheEtape; });
      var et = l.etapes[S.ficheEtape];
      var sel = h('select', {'aria-label': 'Valeur de l’étape ' + ec.label});
      sel.appendChild(h('option', {value: ''}, 'Calcul : ' + (ETATS[et.calcul] || et.calcul)));
      Object.keys(ETATS).forEach(function (k) {
        if (k === 'probable') return;           // se calcule, ne se fixe pas
        var o = h('option', {value: k}, 'Fixer à « ' + ETATS[k] + ' »');
        if (et.force && et.valeur === k) o.selected = true;
        sel.appendChild(o);
      });
      var motif = h('input', {type: 'text', placeholder: 'Motif (facultatif) — ex. BAT validé par mail', value: et.force_note || '',
        'aria-label': 'Motif'});
      correction = h('div', {className: 'fi-correction'},
        h('div', {className: 'fi-correction-t', text: 'Corriger l’étape ' + ec.label}),
        h('div', {className: 'fi-correction-l'}, sel, motif,
          h('button', {type: 'button', className: 'btn btn-accent btn-petit', onClick: function () { forcer(l, S.ficheEtape, sel.value, sel.value ? motif.value : ''); }}, 'Appliquer'),
          et.force ? h('button', {type: 'button', className: 'btn btn-petit', onClick: function () { forcer(l, S.ficheEtape, '', ''); }}, 'Rétablir le calcul') : null),
        h('div', {className: 'fi-correction-n adv-muet', text: 'Calcul : ' + et.detail}));
    }

    // ── Quantités : une barre, quatre chiffres ──
    var qte = Math.max(l.qte || 0, 0.0001);
    var livre = Math.min(l.livre || 0, qte), dispo = Math.min(st.alloue || 0, qte - livre), fab = Math.min(l.a_fabriquer || 0, qte - livre - dispo);
    var pc = function (v) { return (100 * v / qte).toFixed(2) + '%'; };
    var chiffre = function (lib, val, cls) { return h('div', {className: 'fi-chiffre ' + (cls || '')}, h('div', {className: 'fi-chiffre-v', text: fN(val)}), h('div', {className: 'fi-chiffre-l', text: lib})); };
    var quantites = h('div', {className: 'fi-carte'},
      h('h4', {}, 'Quantités', unite(l) ? h('span', {className: 'adv-muet', text: ' · en ' + accord(unite(l), 2)}) : null),
      h('div', {className: 'fi-chiffres'},
        chiffre('Commandé', l.qte), chiffre('Déjà livré', l.livre, 'livre'), chiffre('En stock', st.alloue || 0, 'stock'), chiffre('À fabriquer', l.a_fabriquer || 0, 'fab')),
      h('div', {className: 'fi-barre', role: 'img', 'aria-label': 'Répartition de la quantité commandée'},
        livre ? h('span', {className: 'livre', style: 'width:' + pc(livre)}) : null,
        dispo ? h('span', {className: 'stock', style: 'width:' + pc(dispo)}) : null,
        fab ? h('span', {className: 'fab', style: 'width:' + pc(fab)}) : null),
      h('div', {className: 'fi-note adv-muet', text: 'Besoin calculé par RVGI (qtep) : ' + fN(l.besoin_rvgi) + ' · non utilisé'}));

    // ── Échéances : une frise datée ──
    var finTard = l.fin_prod && l.expedition && String(l.fin_prod).slice(0, 10) > l.expedition;
    // Un jalon = un libellé court, la date seule en gros, et dessous le
    // détail (heure, saisie ou prévue) suivi de l'écart à aujourd'hui. Rien
    // ne s'ajoute à la date : sinon elle déborde sur la colonne voisine.
    var jalon = function (lib, date, cls, detail) {
      return h('div', {className: 'fi-jalon ' + (cls || '') + (date ? '' : ' vide')},
        h('div', {className: 'fi-jalon-p'}),
        h('div', {className: 'fi-jalon-c'},
          h('div', {className: 'fi-jalon-l', text: lib}),
          h('div', {className: 'fi-jalon-d', text: date ? dateFr(date) : '—'}),
          date && detail ? h('div', {className: 'fi-jalon-r fi-jalon-x', text: detail}) : null,
          date ? h('div', {className: 'fi-jalon-r', text: relatif(date)}) : null));
    };
    var detailFin = l.fin_prod
      ? (l.fin_prod_reelle ? 'saisie' : 'prévue') + (heure(l.fin_prod) ? ' à ' + heure(l.fin_prod) : '')
      : '';
    var echeances = h('div', {className: 'fi-carte'},
      h('h4', {text: 'Échéances'}),
      h('div', {className: 'fi-jalons'},
        jalon('Commande', l.creee_le, ''),
        jalon('Fin de prod', l.fin_prod, finTard ? 'warn' : (l.fin_prod_reelle ? 'ok' : ''), detailFin),
        jalon('Expédition', l.expedition, l.retard ? 'danger' : 'fort'),
        jalon('Livraison', l.livraison, '')),
      finTard ? h('div', {className: 'fi-note fi-alerte', text: 'La production finit après la date d’expédition.'}) : null);

    // ── Préparation et stock ──
    var empl = (st.emplacements || []).length
      ? h('div', {className: 'adv-empl'}, st.emplacements.map(function (e) {
          return h('span', {'data-tip': tip(l.cle + '|fiempl' + e.lot_id, 'Emplacement ' + e.emplacement, 'Prélever ' + qteU(l, e.quantite), e.date_entree ? 'Entré le ' + dateFr(e.date_entree) + ' (FIFO)' : null)},
            h('b', {text: e.emplacement}), ' · ' + fN(e.quantite));
        }))
      : (st.sortie_prod ? null : h('div', {className: 'adv-muet', text: st.connu ? 'Rien d’attribué à cette ligne.' : 'Article absent de MyStock.'}));
    if (st.sortie_prod) {
      // Stock « probable » : la production finie n'est pas entrée dans MyStock.
      var puceSortie = h('span', {className: 'adv-sortie-prod',
          'data-tip': tip(l.cle + '|fisortie', 'Sortie de production', l.etapes.stock.detail)},
        h('b', {text: 'Sortie prod'}), ' · ' + fN(st.sortie_prod) + ((st.dossiers_prod || []).length ? ' · dossier ' + st.dossiers_prod.join(', ') : ''));
      if (empl) empl.appendChild(puceSortie);
      else empl = h('div', {className: 'adv-empl'}, puceSortie);
    }
    var prepa = h('div', {className: 'fi-carte'},
      h('h4', {text: 'Préparation'}),
      h('div', {className: 'fi-prepa'},
        h('span', {className: 'adv-badge ' + ({prete: 'ok', en_cours: 'warn'}[l.prepa.statut] || ''), text: LIB_PREPA[l.prepa.statut] || l.prepa.statut}),
        l.prepa.maj_par ? h('span', {className: 'adv-muet', text: l.prepa.maj_par + ' · ' + dateFr(l.prepa.maj_le) + ' ' + heure(l.prepa.maj_le)}) : null,
        h('div', {className: 'fi-prepa-b'}, boutonsPrepa(l))),
      h('div', {className: 'fi-sous-t', text: 'Où prélever' + (st.connu ? ' · ' + qteU(l, st.total) + ' en stock pour l’article' : '')}),
      empl);

    // ── Production et départs ──
    var STATUT_DOS = {attente: ['En attente', ''], en_cours: ['En cours', 'warn'], termine: ['Terminé', 'ok']};
    var rangees = h('div', {className: 'fi-rangees'});
    if (!l.dossiers.length) rangees.appendChild(h('div', {className: 'adv-muet', text: 'Aucun dossier au planning.'}));
    l.dossiers.forEach(function (d) {
      var sd = STATUT_DOS[d.statut] || [d.statut || '', ''];
      rangees.appendChild(h('a', {className: 'fi-rangee', href: '/planning?dossier=' + d.id},
        h('span', {className: 'fi-rangee-ico', text: d.repiquage ? 'Repiq.' : 'Prod'}),
        h('span', {className: 'fi-rangee-t', text: d.reference || ('Dossier ' + d.id)}),
        h('span', {className: 'adv-muet', text: (d.machine || '') + (d.fin ? ' · fin ' + (d.fin_reelle ? '' : 'prévue ') + dateFr(d.fin) : '')}),
        h('span', {className: 'adv-badge ' + sd[1], text: sd[0]})));
    });
    var auj = new Date(); auj.setHours(0, 0, 0, 0);
    if (!l.departs.length) rangees.appendChild(h('div', {className: 'adv-muet', text: 'Aucun départ MyExpé.'}));
    l.departs.forEach(function (d) {
      var passe = d.date_enlevement && new Date(d.date_enlevement + 'T00:00:00') < auj && !d.parti_le;
      var badge = d.parti_le ? ['Parti', 'ok'] : passe ? ['Passé', ''] : d.statut === 'valide' ? ['Validé', 'ok'] : ['À valider', 'warn'];
      rangees.appendChild(h('a', {className: 'fi-rangee' + (passe ? ' passe' : ''), href: '/expe?depart=' + d.id},
        h('span', {className: 'fi-rangee-ico', text: 'Départ'}),
        h('span', {className: 'fi-rangee-t', text: dateFr(d.date_enlevement)}),
        h('span', {className: 'adv-muet', text: (d.transporteur || '') + (d.no_bl ? ' · BL ' + d.no_bl : '')}),
        h('span', {className: 'adv-badge ' + badge[1], text: badge[0]})));
    });
    // Repiquage : son statut (du planning, ou fixé par l'ADV) et, pour
    // l'administration et la direction, de quoi le fixer à la main.
    var rep = l.repiquage || {};
    var repBloc = null;
    if (rep.requis || DROITS.adv) {
      var TON_REP = {a_faire: 'danger', en_cours: 'warn', termine: 'ok'};
      var info = rep.requis
        ? h('span', {className: 'adv-badge ' + (TON_REP[rep.statut] || ''), text: 'Repiquage · ' + (LIB_REPIQUAGE[rep.statut] || rep.statut)})
        : h('span', {className: 'adv-badge', text: 'Sans repiquage'});
      var sous = rep.manuel
        ? 'Fixé par ' + (rep.maj_par || 'l’ADV') + (rep.maj_le ? ' le ' + dateFr(rep.maj_le) : '') + (rep.calcul ? ' · planning : ' + (LIB_REPIQUAGE[rep.calcul] || rep.calcul) : '')
        : (rep.requis ? (rep.planifie ? 'Suivi par le dossier de repiquage du planning' : 'Prod cochée « pour repiquage » · repiquage pas encore planifié') : null);
      var boutons = null;
      if (DROITS.adv) {
        boutons = h('div', {className: 'fi-rep-b'}, Object.keys(LIB_REPIQUAGE).map(function (k) {
          return h('button', {type: 'button', className: 'btn btn-petit' + (rep.manuel && rep.statut === k ? ' btn-accent' : ''),
            onClick: function () { fixerRepiquage(l, k); }}, LIB_REPIQUAGE[k]);
        }), rep.manuel ? h('button', {type: 'button', className: 'btn btn-petit', onClick: function () { fixerRepiquage(l, null); }}, 'Statut du planning') : null);
      }
      repBloc = h('div', {className: 'fi-rep'}, h('div', {className: 'fi-rep-t'}, info, sous ? h('span', {className: 'adv-muet', text: sous}) : null), boutons);
    }
    var suivi = h('div', {className: 'fi-carte'}, h('h4', {text: 'Production et départs'}), repBloc, rangees);

    var liens = h('div', {className: 'adv-liens'},
      DROITS.adv ? h('a', {className: 'btn btn-petit', href: '/erp#/commandes?q=' + encodeURIComponent(l.numero)}, 'Commande dans l’ERP') : null,
      st.connu ? h('a', {className: 'btn btn-petit', href: '/stock?ref=' + encodeURIComponent(l.article)}, 'Article dans MyStock') : null);

    var modal = h('div', {className: 'adv-modal adv-fiche', role: 'dialog', 'aria-modal': 'true', 'aria-label': 'Ligne ' + l.numero + ' · ' + l.ligne},
      tete,
      h('div', {className: 'fi-carte fi-chaine'}, h('h4', {text: 'Chaîne de valeur'}), frise, correction),
      h('div', {className: 'fi-grille'}, quantites, echeances, prepa, suivi),
      h('div', {className: 'm-pied'}, liens, h('button', {type: 'button', className: 'btn', onClick: fermer}, 'Fermer')));
    var voile = h('div', {className: 'adv-voile', onClick: function (ev) { if (ev.target === voile) fermerFiche(); }}, modal);
    m.appendChild(voile);
  }
  document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape' && modalOuverte()) fermerFiche(); });

  /* ── Démarrage ──────────────────────────────────────────────── */

  document.querySelectorAll('#adv-nav .nav-btn[data-onglet]').forEach(function (b) {
    b.addEventListener('click', async function () {
      var o = b.getAttribute('data-onglet');
      if (ONGLETS.indexOf(o) === -1) return;
      fermerFiche(true);
      S.onglet = o; S.ligne = null;
      if (!donnees()) { S.charge = false; render(); await charger(); }
      render();
      if (document.body.classList.contains('sb-open') && window.closeSidebar) window.closeSidebar();
    });
  });

  MySifaUrl.surRetour(async function () {
    var avant = S.onglet, hz = S.horizon;
    lireUrl(true);
    if (S.onglet !== avant || !donnees() || (S.onglet === 'prepa' && hz !== S.horizon)) { await charger(); }
    if (!S.ligne && !S.reglages) fermerFiche(true);
    else if (modalOuverte()) fermerFiche(true);   // render() rouvrira la bonne
    render();
  });

  (async function init() {
    lireUrl(false);
    render();
    await charger();
    render();
    planifierActualisation();
  })();
})();

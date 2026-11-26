/* MySifa — ADV (/adv) : carnet de commandes et préparations.
 *
 * Deux onglets, tout l'état dans l'adresse (.claude/rules/url-etat.md) :
 *   /adv?onglet=commandes (défaut si droit ADV) &filtre=&tri=&sens=&ligne=<n°-lg>
 *   /adv?onglet=prepa &horizon=<jours> &groupe=<groupe> &ligne=<n°-lg>
 *   /adv?onglet=prepa&sous=historique &periode=last7|last90 (défaut last30)
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
  // Vue du planning de prépa (mêmes clés que le planning machine) ; elle fixe
  // aussi jusqu'où lire les préparations, en jours.
  var VUES_PREPA = {
    '1w': {sem: 1, jours: 14, lib: 'Semaine'},
    '2w': {sem: 2, jours: 21, lib: '2 semaines'},
    '4w': {sem: 4, jours: 35, lib: '4 semaines'}
  };
  // Anciennes adresses en jours (`horizon=7`…) : la vue la plus proche.
  var VUE_DES_JOURS = {7: '1w', 14: '1w', 21: '2w', 30: '4w'};
  var GROUPES = ['tous', 'preparable', 'en_cours', 'partiel', 'attente', 'pretes'];
  var HISTO_JOURS = [7, 30, 90];         // mêmes valeurs que adv.HISTORIQUE_JOURS
  // Onglets de la Prépa : un groupe (ou deux) par onglet, puis l'historique.
  var ONGLETS_PREPA = [
    {cle: 'preparable', label: 'À préparer', groupes: ['en_cours', 'preparable']},
    {cle: 'partiel', label: 'Stock partiel', groupes: ['partiel']},
    {cle: 'pretes', label: 'Prêtes', groupes: ['pretes']}
  ];
  // Anciennes adresses (`groupe=tous|en_cours|attente`) : onglet « À préparer ».
  var ONGLET_DU_GROUPE = {partiel: 'partiel', pretes: 'pretes'};

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
    horizon: 21,                 // jours lus, suivant la vue (VUES_PREPA)
    groupe: 'preparable',        // onglet de la Prépa (voir ONGLETS_PREPA)
    jour: null,                  // jour du planning de prépa : null = aujourd'hui, 'tous', ou AAAA-MM-JJ
    vue: '2w',                   // planning de prépa : '1w', '2w', '4w'
    semaine: null,               // lundi de la première semaine affichée (null : la semaine en cours)
    friseDrag: null,             // lignes de la commande glissée dans la frise
    ouverts: {},                 // envois dépliés dans le tableau (clé d'envoi → vrai)
    ordreExpe: null,             // ordre d'expé ouvert : clé d'une de ses lignes (S.ordre = colonnes du carnet)
    sous: null,                  // 'historique' : les préparations déjà faites
    histoJours: 30,
    historique: null,
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
  // Dans le carnet : jj/mm/aa, pour que toutes les colonnes tiennent à
  // l'écran (la date complète reste dans la fiche et au survol).
  function dateCourte(s) {
    if (!s) return '';
    var d = String(s).slice(0, 10).split('-');
    return d.length === 3 ? d[2] + '/' + d[1] + '/' + d[0].slice(2) : String(s);
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
    var hz = u.get('horizon', null);
    var vue = VUES_PREPA[hz] ? hz : VUE_DES_JOURS[parseInt(hz, 10)];
    if (vue || complet) { S.vue = vue || '2w'; S.horizon = VUES_PREPA[S.vue].jours; }
    var sem = u.get('semaine', null);
    if (sem || complet) S.semaine = /^\d{4}-\d{2}-\d{2}$/.test(sem || '') ? lundiDe(sem) : null;
    var g = u.get('groupe', null, GROUPES);
    if (g || complet) S.groupe = ONGLET_DU_GROUPE[g] || 'preparable';
    S.sous = S.onglet === 'prepa' && u.get('sous', null, ['historique']) ? 'historique' : null;
    var pe = u.get('periode', null, HISTO_JOURS.map(function (n) { return 'last' + n; }));
    if (pe || complet) S.histoJours = pe ? parseInt(pe.slice(4), 10) : 30;
    var jr = u.get('jour', null);
    if (jr || complet) S.jour = jr === 'tous' || /^\d{4}-\d{2}-\d{2}$/.test(jr || '') ? jr : null;
    var l = u.get('ligne', null);
    S.ligne = (l && /^\d{1,12}-\d{1,4}$/.test(l)) ? l : null;
    S.reglages = (DROITS.adv && S.onglet === 'commandes' && !S.ligne)
      ? u.get('reglages', null, ['mise_en_forme']) : null;
    var od = u.get('ordre', null);
    S.ordreExpe = (S.onglet === 'prepa' && !S.ligne && od && /^\d{1,12}-\d{1,4}$/.test(od)) ? od : null;
  }
  function ecrireUrl() {
    var p = {};
    if (S.onglet !== ONGLETS[0]) p.onglet = S.onglet;
    if (S.onglet === 'commandes') {
      if (S.filtre !== 'tous') p.filtre = S.filtre;
      if (S.tri !== 'expedition') p.tri = S.tri;
      if (S.sens !== 'asc') p.sens = S.sens;
    } else {
      if (S.vue !== '2w') p.horizon = S.vue;
      if (S.semaine && !S.sous) p.semaine = S.semaine;
      if (S.sous) {
        p.sous = S.sous;
        if (S.histoJours !== 30) p.periode = 'last' + S.histoJours;
      } else {
        if (S.groupe !== 'preparable') p.groupe = S.groupe;
        if (S.jour) p.jour = S.jour;
      }
    }
    if (S.ligne) p.ligne = S.ligne;
    else if (S.reglages) p.reglages = S.reglages;
    else if (S.ordreExpe) p.ordre = S.ordreExpe;
    var lieu = S.onglet === 'prepa' ? ':' + (S.sous || S.groupe) : '';
    MySifaUrl.ecrire(p, {navigation: S.onglet + lieu + (S.ligne ? ':fiche' : S.reglages ? ':reglages' : S.ordreExpe ? ':ordre' : '')});
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
      else if (S.sous === 'historique') {
        var r = await Promise.all([api('/api/adv/prepa/historique?jours=' + S.histoJours),
          api('/api/adv/prepa?horizon=' + encodeURIComponent(S.horizon))]);
        S.historique = r[0]; S.prepa = r[1];
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
    document.title = DROITS.adv ? (S.onglet === 'commandes' ? 'Commandes' : 'Prépa') + ' — ADV — MySifa' : 'Prépa — MySifa';
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
      ajusterBlocsFrise();          // la page est en place : les blocs ont leur largeur
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
    else if (S.ordreExpe && !modalOuverte()) ouvrirOrdre(S.ordreExpe, true);
    if (!S.ligne && !S.reglages && !S.ordreExpe && modalOuverte()) fermerFiche(true);
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
  // Stock et Prod en cours : le nœud se remplit de gauche à droite à la part faite
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
        var hay = norm([l.numero, l.client, l.article, l.designation, l.ref_client]
          .concat((l.infos || []).map(function (x) { return x.texte; })).join(' '));
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
        (S.ordre || []).length ? h('button', {type: 'button', className: 'btn btn-petit',
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
  /* ── Informations de suivi ──────────────────────────────────── */

  // Le « ? » jaune d'une ligne qui a une info de suivi (survol : la dernière,
  // clic : la fiche, sur le fil des infos). Sans info, l'ADV voit au survol de
  // la ligne un « ? » en pointillé pour en ajouter une.
  function iconeInfo(l) {
    var infos = l.infos || [];
    if (!infos.length && !DROITS.adv) return null;
    var d = infos[0];
    var b = h('button', {type: 'button', className: 'adv-info' + (infos.length ? '' : ' vide'),
      'aria-label': infos.length ? 'Info de suivi : ' + d.texte : 'Ajouter une info de suivi',
      'data-tip': infos.length
        ? tip(l.cle + '|info', 'Info de suivi', d.texte,
            (d.cree_par ? d.cree_par + ' · ' : '') + dateFr(d.cree_le) + (heure(d.cree_le) ? ' à ' + heure(d.cree_le) : '')
            + (infos.length > 1 ? ' · ' + (infos.length - 1) + ' autre' + (infos.length > 2 ? 's' : '') + ' dans la fiche' : ''))
        : tip(l.cle + '|info', 'Ajouter une info de suivi', 'Pourquoi la ligne n’est pas partie, où elle en est.'),
      onClick: function (ev) { ev.stopPropagation(); S.focusInfo = true; ouvrirFiche(l.cle); }}, '?');
    return b;
  }
  async function ajouterInfo(l, texte) {
    var r = await api('/api/adv/infos/' + encodeURIComponent(l.numero) + '/' + l.ligne, {method: 'POST', body: {texte: texte}});
    majInfos(l.cle, function (infos) { return [r.info].concat(infos); });
  }
  async function supprimerInfo(l, id) {
    await api('/api/adv/infos/' + id, {method: 'DELETE'});
    majInfos(l.cle, function (infos) { return infos.filter(function (x) { return x.id !== id; }); });
  }
  // Le carnet et la Prépa portent chacun leur copie de la ligne.
  function majInfos(cle, fn) {
    [S.carnet, S.prepa].forEach(function (d) {
      ((d && d.lignes) || []).forEach(function (x) { if (x.cle === cle) x.infos = fn(x.infos || []); });
    });
  }

  // Liens d'une cellule : la réf article vers sa fiche MyStock, la fin de prod
  // vers le dossier au planning. Le clic n'ouvre pas la fiche de la ligne.
  function lienCellule(href, texte, cls) {
    return h('a', {className: 'adv-lien' + (cls ? ' ' + cls : ''), href: href, text: texte,
      onClick: function (ev) { ev.stopPropagation(); }});
  }
  function lienArticle(l) {
    return l.stock && l.stock.connu ? lienCellule('/stock?ref=' + encodeURIComponent(l.article), l.article) : l.article;
  }
  // Le planning n'ouvre un dossier que sur SA machine : sans `machine=`, il
  // reprendrait la dernière machine consultée et ne trouverait pas le dossier.
  function lienPlanning(d) {
    return '/planning?' + (d.machine_id ? 'machine=' + encodeURIComponent(d.machine_id) + '&' : '') + 'dossier=' + encodeURIComponent(d.id);
  }
  // Le dossier qui fixe la fin de prod : celui qui finit le dernier.
  function dossierFin(l) {
    var ds = (l.dossiers || []).filter(function (d) { return d.fin; });
    if (!ds.length) return null;
    return ds.reduce(function (a, b) { return String(b.fin) > String(a.fin) ? b : a; });
  }

  var COLONNES = [
    {cle: 'commande', famille: 'id', label: 'Commande', tri: 'commande', td: function (l) {
      return h('td', {className: 'adv-mono c-commande'}, h('span', {className: 'cde-t'}, l.numero, h('span', {className: 'adv-muet', text: ' · ' + l.ligne})), iconeInfo(l));
    }},
    {cle: 'client', famille: 'id', label: 'Client', tri: 'client', td: function (l) {
      return h('td', {className: 'client', title: l.client}, h('span', {className: 'client-t', text: l.client}));
    }},
    {cle: 'article', famille: 'id', label: 'Article', tri: 'article', td: function (l) {
      return h('td', {className: 'des adv-mono', 'data-tip': tip(l.cle + '|des', l.article, l.designation, libOrigine(l.origine) + (l.ref_client ? ' · réf. client ' + l.ref_client : ''))},
        lienArticle(l));
    }},
    {cle: 'expedition', famille: 'date', label: 'Expédition', tri: 'expedition', td: function (l) {
      return h('td', {className: 'date' + (l.retard ? ' adv-date-retard' : ''), title: dateFr(l.expedition) || null, text: dateCourte(l.expedition) || '—'});
    }},
    {cle: 'livraison', famille: 'date', label: 'Livraison', tri: 'livraison', td: function (l) {
      return h('td', {className: 'date', title: dateFr(l.livraison) || null, text: dateCourte(l.livraison) || '—'});
    }},
    {cle: 'fin_prod', famille: 'date', label: 'Fin de prod', tri: 'fin_prod', td: function (l) {
      var tard = l.fin_prod && l.expedition && String(l.fin_prod).slice(0, 10) > l.expedition;
      var dfin = l.fin_prod ? dossierFin(l) : null;
      return h('td', {className: 'date' + (tard ? ' adv-date-tard' : (l.fin_prod ? '' : ' adv-muet')),
        'data-tip': l.fin_prod ? tip(l.cle + '|fin', l.fin_prod_reelle ? 'Fin de production saisie' : 'Fin de production planifiée',
          dateFr(l.fin_prod) + (heure(l.fin_prod) ? ' à ' + heure(l.fin_prod) : ''),
          (tard ? 'Après la date d’expédition · ' : '') + (dfin ? 'Cliquer : dossier ' + (dfin.reference || dfin.id) + ' au planning' : '')) : null},
        !l.fin_prod ? '—' : (dfin ? lienCellule(lienPlanning(dfin), dateCourte(l.fin_prod)) : dateCourte(l.fin_prod)));
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
      var rgLigne = S.mef.length ? regleLigne(l) : null;
      if (rgLigne) { tr.classList.add('mef-ligne'); habiller(tr, rgLigne); }
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
        var rg = S.mef.length ? regleCellule(l, c.cle) : null;
        if (rg) {
          td.classList.add('mef');
          habiller(td, rg);
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

  // Statut de préparation d'une ou plusieurs lignes (un envoi entier).
  async function changerPrepa(ls, statut, bouton) {
    ls = [].concat(ls);
    if (bouton) bouton.disabled = true;
    try {
      for (var i = 0; i < ls.length; i++) {
        await api('/api/adv/prepa/' + encodeURIComponent(ls[i].numero) + '/' + ls[i].ligne, {method: 'PUT', body: {statut: statut}});
      }
      var lib = (LIB_PREPA[statut] || statut).toLowerCase();
      toast(ls.length > 1 ? 'Envoi ' + ls[0].numero + ' · ' + ls.length + ' lignes : ' + lib + '.'
        : 'Prépa ' + ls[0].numero + ' · ' + ls[0].ligne + ' : ' + lib + '.');
      var y = (document.querySelector('.main') || {}).scrollTop;
      var yt = (document.querySelector('.adv-table-wrap') || {}).scrollTop;
      await charger();
      // L'autre onglet se relira à son ouverture : sa prépa est périmée.
      if (S.onglet === 'prepa') S.carnet = null; else S.prepa = null;
      // L'historique se relira à son ouverture (il recharge aussi la Prépa).
      if (!S.sous) S.historique = null;
      render();
      if (modalOuverte() && S.ligne) { fermerFiche(true); ouvrirFiche(S.ligne, true); }
      var mn = document.querySelector('.main');
      if (mn && y) mn.scrollTop = y;
      var tw = document.querySelector('.adv-table-wrap');
      if (tw && yt) tw.scrollTop = yt;
    } catch (e) {
      toast(e.message, 'danger');
      if (bouton) bouton.disabled = false;
      await charger(); render();
    }
  }

  var ICONES_ACTION = {
    // Ordre d'expé : le bordereau qui part (feuille, ses lignes, une flèche de sortie).
    ordre: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 21H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h8l4 4v5"/><path d="M14 3v4h4"/><path d="M8 9.5h6M8 13h4"/><path d="M14.5 18h6.5M18.5 15.5 21 18l-2.5 2.5"/></svg>',
    urgente: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.3 4 2 18.2A2 2 0 0 0 3.7 21h16.6a2 2 0 0 0 1.7-2.8L13.7 4a2 2 0 0 0-3.4 0z"/><line x1="12" y1="9.5" x2="12" y2="13.5"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    prete: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>'
  };

  // Les trois gestes d'une ligne, ou d'un envoi (ses lignes ensemble) :
  // l'ordre d'expé, l'urgence (ADV) et « Prête ». Dans le tableau, des icônes
  // (libellé au survol) ; dans la fiche (`libelles`), icône et libellé.
  function boutonsPrepa(ls, opts) {
    ls = [].concat(ls);
    opts = opts || {};
    var l0 = ls[0];
    var cleTip = (ls.length > 1 ? 'env|' : '') + l0.cle;
    var toutesPretes = ls.every(function (l) { return l.prepa.statut === 'prete'; });
    var aFaire = ls.filter(function (l) { return l.prepa.statut !== 'prete'; });
    var toutesUrgentes = ls.every(function (l) { return l.urgente_manuelle; });
    var pour = ls.length > 1 ? ' (' + ls.length + ' lignes)' : '';
    var bouton = function (cle, cls, lib, titre, texte, onClick) {
      var el = h('button', {type: 'button', className: 'btn btn-petit adv-act-btn ' + cls + (opts.libelles ? '' : ' btn-ico'),
          'aria-label': lib, 'data-tip': tip(cleTip + '|' + cle + (opts.libelles ? '|fi' : ''), titre, texte)},
        h('span', {className: 'ico', html: ICONES_ACTION[cle]}), opts.libelles ? h('span', {text: lib}) : null);
      el.addEventListener('click', function (ev) { ev.stopPropagation(); onClick(el); });
      return el;
    };
    var out = [bouton('ordre', 'adv-btn-ordre', 'Ordre d’expé', 'Ordre d’expé',
      'Tout ce qui part ce jour-là à cette adresse, prêt à imprimer', function () { ouvrirOrdre(l0.cle); })];
    // L'ADV marque une préparation urgente : elle passe en tête de son groupe
    // et compte dans la bulle rouge de la tuile « Prépa » du portail.
    if (DROITS.adv) {
      var u = bouton('urgente', 'adv-btn-urgence' + (toutesUrgentes ? ' on' : ''), toutesUrgentes ? 'Retirer l’urgence' : 'Urgente',
        toutesUrgentes ? 'Retirer l’urgence' + pour : 'Marquer urgente' + pour,
        toutesUrgentes ? (l0.urgente_par ? 'Marquée par ' + l0.urgente_par : null) : 'Passe en tête du groupe et dans la bulle rouge de la logistique',
        function (el) { marquerUrgente(ls, !toutesUrgentes, el); });
      u.setAttribute('aria-pressed', toutesUrgentes ? 'true' : 'false');
      if (toutesPretes) u.disabled = true;
      out.push(u);
    }
    // Un seul geste : « Prête ». Une prépa déjà prête peut être remise à préparer.
    var p = bouton('prete', 'btn-accent adv-btn-prete' + (toutesPretes ? ' on' : ''), toutesPretes ? 'Remettre à préparer' : 'Prête',
      toutesPretes ? 'Prête' + pour : 'Marquer prête' + pour,
      toutesPretes ? 'Cliquer pour remettre à préparer' : null,
      function (el) { changerPrepa(toutesPretes ? ls : aFaire, toutesPretes ? 'a_preparer' : 'prete', el); });
    p.setAttribute('aria-pressed', toutesPretes ? 'true' : 'false');
    out.push(p);
    return out;
  }

  async function marquerUrgente(ls, oui, bouton) {
    ls = [].concat(ls);
    if (bouton) bouton.disabled = true;
    try {
      for (var i = 0; i < ls.length; i++) {
        await api('/api/adv/prepa/urgence/' + encodeURIComponent(ls[i].numero) + '/' + ls[i].ligne, {method: 'PUT', body: {urgente: oui}});
      }
      var yt = (document.querySelector('.adv-table-wrap') || {}).scrollTop;
      await charger(); S.carnet = null; render();
      if (modalOuverte() && S.ligne) { fermerFiche(true); ouvrirFiche(S.ligne, true); }
      var tw = document.querySelector('.adv-table-wrap');
      if (tw && yt) tw.scrollTop = yt;
      toast((ls.length > 1 ? 'Envoi ' + ls[0].numero + ' (' + ls.length + ' lignes) ' : 'Préparation ')
        + (oui ? 'marqué' + (ls.length > 1 ? '' : 'e') + ' urgent' + (ls.length > 1 ? '' : 'e') + '.' : ': urgence retirée.'));
    } catch (e) {
      toast(e.message, 'danger');
      if (bouton) bouton.disabled = false;
      await charger(); render();
    }
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
    var aPrep = h('td', {className: 'c-num c-fort c-aprep' + (l.groupe === 'attente' ? ' c-fab' : (manque ? ' adv-date-tard' : '')),
        'data-l': l.groupe === 'attente' ? 'À produire' : 'À préparer',
        'data-tip': l.groupe === 'attente'
          ? tip(l.cle + '|aprep', 'À produire', l.fin_prod ? 'Fin de prod ' + dateFr(l.fin_prod) + (heure(l.fin_prod) ? ' ' + heure(l.fin_prod) : '') : l.etapes.prod.detail)
          : (manque ? tip(l.cle + '|aprep', sortie ? 'Production un peu sous la commande' : 'Stock partiel',
              'Manque ' + fN(manque) + ' ' + accord(uniteReelle, manque)) : null)},
      fN(l.reste));
    var empl;
    if (st.emplacements && st.emplacements.length && l.groupe !== 'attente') {
      // Deux emplacements, dans l'ordre FIFO ; les suivants se replient en
      // « +N », liste complète au survol.
      var lots = st.emplacements;
      empl = h('div', {className: 'adv-empl'}, lots.slice(0, 2).map(function (e) {
        return h('span', {'data-tip': tip(l.cle + '|lot' + e.lot_id, 'Emplacement ' + e.emplacement, 'Prélever ' + qteU(l, e.quantite), e.date_entree ? 'Entré le ' + dateLongue(e.date_entree) + ' (FIFO)' : null)},
          h('b', {text: e.emplacement}), ' · ' + fN(e.quantite));
      }), lots.length > 2 ? h('span', {className: 'adv-empl-plus',
        'data-tip': tip(l.cle + '|plus', lots.length + ' emplacements, dans l’ordre FIFO',
          lots.map(function (e) { return e.emplacement + ' · ' + qteU(l, e.quantite); }).join('\n'))},
        '+' + (lots.length - 2)) : null);
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
    // La cellule existe toujours : sans elle, les colonnes suivantes glissent
    // d'un cran (cas d'une ligne en attente de prod avec une sortie de prod).
    if (!empl) empl = h('div', {className: 'adv-empl adv-muet', text: '—'});
    var dp = l.departs && l.departs.length ? l.departs[0] : null;
    var notesQuand = [];
    if (dp) notesQuand.push('Enlèvement ' + dateLongue(dp.date_enlevement) + (dp.transporteur ? ' · ' + dp.transporteur : '') + (dp.parti_le ? ' · parti' : ''));
    if (l.prepa.statut !== 'a_preparer' && l.prepa.maj_par) {
      notesQuand.push((LIB_PREPA[l.prepa.statut] || '') + ' · ' + l.prepa.maj_par + ' ' + dateFr(l.prepa.maj_le) + ' ' + heure(l.prepa.maj_le));
    }
    var quand = h('td', {className: 'c-quand' + (l.retard ? ' adv-date-retard' : ''),
      'data-tip': tip(l.cle + '|quand', 'Expédition ' + (dateLongue(l.expedition) || 'non datée') + (l.retard ? ' · en retard' : ''),
        notesQuand[0] || null, notesQuand[1] || null)},
      l.expedition ? dateFr(l.expedition) : 'Non datée');

    var manuel = l.priorite_manuelle !== null && l.priorite_manuelle !== undefined;
    var rangEl = h('div', {className: 'adv-rang' + (manuel ? ' manuel' : '') + (l.urgence ? ' urgente' : ''),
      'data-tip': l.urgence
        ? tip(l.cle + '|rang', 'Urgente', l.urgence, ctx && DROITS.adv ? 'Glisser la ligne ou utiliser ↑ ↓ pour changer l’ordre' : null)
        : tip(l.cle + '|rang', manuel ? 'Ordre fixé à la main' : 'Ordre automatique',
          manuel ? (l.priorite_par ? 'Par ' + l.priorite_par : '') + (l.priorite_le ? ' le ' + dateFr(l.priorite_le) : '') : 'Par date d’expédition',
          ctx && DROITS.adv ? 'Glisser la ligne ou utiliser ↑ ↓ pour changer l’ordre' : null)}, String(rang));
    var celRang = h('div', {className: 'adv-rang-cel'}, rangEl);
    var cellRang = h('td', {className: 'c-rang'}, celRang);
    if (ctx && DROITS.adv) {
      var fleche = function (sens, lib) {
        var cible = ctx.index + sens;
        return h('button', {type: 'button', className: 'adv-fleche', 'aria-label': lib, disabled: cible < 0 || cible >= ctx.lignes.length,
          onClick: function (ev) { ev.stopPropagation(); deplacerPrepa(ctx.lignes, ctx.index, cible); }}, sens < 0 ? '↑' : '↓');
      };
      celRang.appendChild(h('div', {className: 'adv-fleches'}, fleche(-1, 'Monter'), fleche(1, 'Descendre')));
    }

    var ligne = h('tr', {className: 'adv-pl' + (l.retard ? ' retard' : '') + (l.urgence ? ' urgente' : ''), 'data-cle': l.cle,
        onClick: function () { ouvrirFiche(l.cle); }},
      DROITS.adv ? h('td', {className: 'c-poignee', 'aria-hidden': 'true', html: ICONE_POIGNEE}) : null,
      cellRang,
      h('td', {className: 'c-client'}, h('div', {className: 'c-client-t', text: l.client, title: l.client})),
      h('td', {className: 'c-cde adv-mono'}, h('span', {text: l.numero + '-L' + l.ligne}), (l.infos || []).length ? iconeInfo(l) : null),
      h('td', {className: 'c-ref adv-mono', 'data-tip': tip(l.cle + '|ref', l.article, l.designation)}, lienArticle(l)),
      h('td', {className: 'c-num c-qte', 'data-l': 'Commandé'}, qteU(l, l.qte)),
      h('td', {className: 'c-num c-stk' + (st.alloue ? '' : ' adv-muet'), 'data-l': 'En stock'}, st.alloue ? fN(st.alloue) : '—'),
      aPrep,
      h('td', {className: 'c-empl'}, empl), quand,
      h('td', {className: 'c-act'}, h('div', {className: 'adv-actions'}, boutonsPrepa(l))));

    // Glisser-déposer, dans le groupe seulement : on ne change pas une
    // préparation de groupe en la déplaçant (le groupe dit où elle en est).
    if (ctx && DROITS.adv) {
      ligne.setAttribute('draggable', 'true');
      ligne.addEventListener('dragstart', function (ev) {
        S.prepaDrag = {cle: l.cle, onglet: ctx.onglet, index: ctx.index};
        ligne.classList.add('attrapee');
        try { ev.dataTransfer.effectAllowed = 'move'; ev.dataTransfer.setData('text/plain', l.cle); } catch (e) {}
      });
      ligne.addEventListener('dragend', function () {
        S.prepaDrag = null;
        document.querySelectorAll('.adv-pl.attrapee, .adv-pl.cible-haut, .adv-pl.cible-bas').forEach(function (x) {
          x.classList.remove('attrapee', 'cible-haut', 'cible-bas');
        });
      });
      ligne.addEventListener('dragover', function (ev) {
        var d = S.prepaDrag;
        if (!d || d.onglet !== ctx.onglet || d.cle === l.cle) return;
        ev.preventDefault();
        var bas = d.index < ctx.index;
        ligne.classList.toggle('cible-bas', bas);
        ligne.classList.toggle('cible-haut', !bas);
      });
      ligne.addEventListener('dragleave', function () { ligne.classList.remove('cible-haut', 'cible-bas'); });
      ligne.addEventListener('drop', function (ev) {
        var d = S.prepaDrag;
        ligne.classList.remove('cible-haut', 'cible-bas');
        if (!d || d.onglet !== ctx.onglet || d.cle === l.cle) return;
        ev.preventDefault();
        S.prepaDrag = null;
        deplacerPrepa(ctx.lignes, d.index, ctx.index);
      });
    }
    return ligne;
  }

  // Poignée de glisser-déposer (ADV) : six points.
  var ICONE_POIGNEE = '<svg width="12" height="16" viewBox="0 0 12 16" fill="currentColor"><circle cx="3.5" cy="3" r="1.4"/><circle cx="8.5" cy="3" r="1.4"/><circle cx="3.5" cy="8" r="1.4"/><circle cx="8.5" cy="8" r="1.4"/><circle cx="3.5" cy="13" r="1.4"/><circle cx="8.5" cy="13" r="1.4"/></svg>';

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
    var yt = (document.querySelector('.adv-table-wrap') || {}).scrollTop;
    try {
      await api('/api/adv/prepa/ordre', {method: 'PUT', body: {lignes: envoi}});
      await charger();
      S.carnet = null;              // l'attribution du stock a pu bouger
      render();
      var mn = document.querySelector('.main');
      if (mn && y) mn.scrollTop = y;
      var tw = document.querySelector('.adv-table-wrap');
      if (tw && yt) tw.scrollTop = yt;
    } catch (e) { toast(e.message, 'danger'); }
  }

  // Un seul en-tête pour toute la liste, collé en haut quand elle défile.
  // Dans « En attente de production », la colonne « À préparer » donne ce qui
  // reste à produire (en orange, détail au survol).
  // Un seul en-tête, toujours visible. Libellés courts : la ligne doit tenir
  // à côté du menu ; le libellé complet est au survol.
  function entetePrepa() {
    var th = function (t, cls, titre) { return h('th', {className: cls || null, text: t, title: titre || null}); };
    return h('thead', {}, h('tr', {},
      DROITS.adv ? th('', 'c-poignee') : null,
      th('#', 'c-rang'), th('Client'), th('Commande'), th('Réf.', null, 'Référence produit'),
      th('Commandé', 'num'), th('Stock', 'num', 'En stock (MyStock)'), th('À prép.', 'num', 'À préparer'),
      th('Où prélever'), th('Expé.', null, 'Expédition'), th('', 'c-act')));
  }

  // Un groupe à la fois, en onglets ; l'historique est le dernier. Les
  // préparations déjà commencées (statut « en cours », d'avant la suppression
  // du bouton Démarrer) restent en tête de « À préparer ». L'attente de
  // production n'a pas d'onglet : rien à préparer tant qu'elle n'est pas finie.
  function ongletsPrepa(c) {
    var groupes = (S.prepa && S.prepa.groupes) || null;
    var n = function (cle) {
      if (!groupes) return null;
      var g = groupes.find(function (x) { return x.cle === cle; });
      return g ? g.lignes : 0;
    };
    var jour = jourActif();
    var nb = function (o) {
      if (!groupes) return null;
      if (jour) return (S.prepa.lignes || []).filter(function (l) { return o.groupes.indexOf(l.groupe) !== -1 && duJour(l, jour); }).length;
      return o.groupes.reduce(function (s, g) { return s + n(g); }, 0);
    };
    var bouton = function (cle, lib, compte, actif, onClick, cls) {
      return h('button', {type: 'button', className: 'adv-ongl-btn' + (cls ? ' ' + cls : '') + (actif ? ' active' : ''),
        'aria-pressed': actif ? 'true' : 'false', onClick: onClick},
        lib, compte !== null ? h('span', {className: 'n', text: String(compte)}) : null);
    };
    var attrs = {className: 'adv-ongl', role: 'group', 'aria-label': 'Groupes de préparations'};
    if (groupes) {
      // Bloc d'accueil (widget) : mêmes valeurs qu'avant les onglets, lues par l'API.
      attrs['data-bloc'] = 'adv.prepa.kpis';
      attrs['data-bloc-valeur-preparable'] = String(n('preparable'));
      attrs['data-bloc-valeur-en-cours'] = String(n('en_cours'));
      attrs['data-bloc-valeur-partiel'] = String(n('partiel'));
      attrs['data-bloc-valeur-attente'] = String(n('attente'));
      attrs['data-bloc-valeur-pretes'] = String(n('pretes'));
    }
    c.appendChild(h('div', attrs,
      ONGLETS_PREPA.map(function (o) {
        return bouton(o.cle, o.label, nb(o), !S.sous && S.groupe === o.cle, function () { allerOnglet(o.cle); });
      }),
      bouton('historique', 'Historique', null, S.sous === 'historique', function () { allerOnglet('historique'); }, 'histo')));
  }

  // Changer d'onglet : charge ce qui manque, remonte en haut de la liste.
  async function allerOnglet(cle) {
    if (cle === 'historique') {
      if (S.sous === 'historique') return;
      S.sous = 'historique';
    } else {
      if (!S.sous && S.groupe === cle) return;
      S.sous = null;
      S.groupe = cle;
    }
    var manque = S.sous ? !S.historique || S.historique.jours !== S.histoJours : !S.prepa;
    if (manque) { S.charge = false; render(); await charger(); }
    render();
    var tw = document.querySelector('.adv-table-wrap');
    if (tw) tw.scrollTop = 0;
  }

  // Les préparations passées « Prête », même parties ou sorties du carnet :
  // on les retrouve, et on corrige un statut posé par erreur. Remise « à
  // préparer », la ligne quitte l'historique et revient dans son onglet (si
  // elle est encore au carnet).
  function tableHistorique(c, d) {
    var lignes = d.lignes || [];
    if (!lignes.length) {
      c.appendChild(h('div', {className: 'adv-vide', text: 'Aucune préparation passée « Prête » ces ' + S.histoJours + ' derniers jours.'}));
      return;
    }
    var statuts = BOOT.statuts_prepa || [];
    var TONS = {parti: 'ok', attente_depart: '', sortie: ''};
    var corps = h('tbody', {}, lignes.map(function (l) {
      var uniteReelle = l.unite || 'étiquette';
      var sel = h('select', {className: 'adv-histo-statut', 'aria-label': 'Statut de la préparation ' + l.numero + '-L' + l.ligne},
        statuts.map(function (st) { return h('option', {value: st.cle, selected: st.cle === l.statut}, st.label); }));
      sel.addEventListener('change', function () { changerPrepa(l, sel.value, sel); });
      return h('tr', {},
        h('td', {className: 'date'}, dateFr(l.prete_le), h('span', {className: 'adv-muet', text: heure(l.prete_le) ? ' ' + heure(l.prete_le) : ''})),
        h('td', {className: l.prete_par ? '' : 'adv-muet', text: l.prete_par || '—'}),
        h('td', {className: 'client', text: l.client || '—', title: l.client || ''}),
        h('td', {className: 'adv-mono', text: l.numero + '-L' + l.ligne}),
        h('td', {className: 'adv-mono adv-muet', text: l.article || '—', title: l.designation || ''}),
        h('td', {className: 'num', text: fN(l.qte)}),
        h('td', {className: 'adv-muet', text: accord(uniteReelle, l.qte)}),
        h('td', {className: 'date', text: l.expedition ? dateFr(l.expedition) : '—'}),
        h('td', {}, h('span', {className: 'adv-badge' + (TONS[l.situation] ? ' ' + TONS[l.situation] : ''), text: l.situation_label})),
        h('td', {}, sel));
    }));
    var tete = ['Prête le', 'Par', 'Client', 'Commande', 'Réf produit', 'Commandé', 'Unité', 'Expédition', 'Devenue', 'Statut'];
    c.appendChild(h('div', {className: 'adv-table-wrap adv-histo'},
      h('table', {className: 'adv-table'},
        h('thead', {}, h('tr', {}, tete.map(function (t) { return h('th', {className: t === 'Commandé' ? 'num' : null, text: t}); }))),
        corps)));
  }

  /* ── Planning de prépa : la frise des semaines, comme le planning machine ── */

  var JOURS_COURTS = ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam'];
  var JOURS_LONGS = ['dimanche', 'lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi'];
  function isoJour(d) {
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  }
  function dateIso(iso) { var p = String(iso).split('-'); return new Date(+p[0], +p[1] - 1, +p[2]); }
  function decaler(iso, n) { var d = dateIso(iso); d.setDate(d.getDate() + n); return isoJour(d); }
  function lundiDe(iso) { var d = dateIso(iso); d.setDate(d.getDate() - (d.getDay() + 6) % 7); return isoJour(d); }
  function numSemaine(iso) {
    var d = dateIso(iso);
    d.setDate(d.getDate() + 3 - (d.getDay() + 6) % 7);
    var j4 = new Date(d.getFullYear(), 0, 4);
    return 1 + Math.round(((d - j4) / 86400000 - 3 + (j4.getDay() + 6) % 7) / 7);
  }
  function jourCourt(iso) { var d = dateIso(iso); return JOURS_COURTS[d.getDay()] + ' ' + dateFr(iso).slice(0, 5); }
  function jourLong(iso) { var d = dateIso(iso); return JOURS_LONGS[d.getDay()] + ' ' + dateFr(iso).slice(0, 5); }
  // Aujourd'hui selon le serveur (heure de Paris), à défaut selon le poste.
  function aujourdhuiPrepa() { return (S.prepa && S.prepa.aujourdhui) || isoJour(new Date()); }
  // Le jour dont le tableau montre les préparations — null : tous les jours.
  function jourActif() { return S.jour === 'tous' ? null : (S.jour || aujourdhuiPrepa()); }
  // Une préparation à faire ce jour-là (les prêtes comptent : c'est le travail du jour).
  function duJour(l, jour) { return !jour || l.jour_prepa === jour; }
  // Même client, même couleur, d'une semaine à l'autre : une des cinq teintes du thème.
  function teinteClient(nom) {
    var x = 0;
    String(nom || '').split('').forEach(function (ch) { x = (x * 31 + ch.charCodeAt(0)) >>> 0; });
    return 'c' + (1 + x % 5);
  }

  function choisirJour(jour) {
    S.jour = jour === aujourdhuiPrepa() ? null : jour;
    render();
    var tw = document.querySelector('.adv-table-wrap');
    if (tw) tw.scrollTop = 0;
  }

  // Déplace une ou plusieurs préparations (une commande entière) sur un jour.
  async function deplacerJour(cles, jour) {
    var ls = [].concat(cles).map(ligneParCle).filter(function (l) { return l && l.jour_prepa !== jour; });
    if (!ls.length) return;
    try {
      for (var i = 0; i < ls.length; i++) {
        await api('/api/adv/prepa/jour/' + encodeURIComponent(ls[i].numero) + '/' + ls[i].ligne, {method: 'PUT', body: {jour: jour}});
      }
      var yt = (document.querySelector('.adv-table-wrap') || {}).scrollTop;
      await charger(); S.carnet = null; render();
      var tw = document.querySelector('.adv-table-wrap');
      if (tw && yt) tw.scrollTop = yt;
      toast((ls.length > 1 ? 'Commande ' + ls[0].numero + ' (' + ls.length + ' lignes)' : 'Préparation ' + ls[0].numero + '-L' + ls[0].ligne)
        + ' déplacée au ' + jourLong(jour) + '.');
    } catch (e) {
      toast(e.message, 'danger');
      await charger(); render();
    }
  }

  var SOURCES_JOUR = {
    manuel: function (l) { return 'Jour fixé à la main' + (l.jour_manuel_par ? ' par ' + l.jour_manuel_par : ''); },
    enlevement: function () { return 'Veille de l’enlèvement prévu dans MyExpé'; },
    expedition: function () { return 'Veille de l’expédition'; }
  };
  function etatLigne(l) {
    return l.groupe === 'pretes' ? 'Prête' : l.groupe === 'partiel' ? 'Stock partiel'
      : l.groupe === 'en_cours' ? 'En cours de préparation' : 'À préparer';
  }

  // Ce qui part ensemble : même commande, même date d'expédition, même
  // adresse de livraison (celle de la ligne dans RVGI). Un envoi = un bloc de
  // la frise, une ligne repliable du tableau.
  function cleEnvoi(l) {
    return l.numero + '|' + (l.expedition || '') + '|' + ((l.destination && l.destination.cle) || '');
  }
  function parEnvoi(lignes) {
    var ordre = [], par = {};
    lignes.forEach(function (l) {
      var k = cleEnvoi(l);
      if (!par[k]) { par[k] = {cle: k, numero: l.numero, lignes: []}; ordre.push(par[k]); }
      par[k].lignes.push(l);
    });
    return ordre;
  }

  // Un envoi dans la frise, comme un dossier du planning machine : client
  // en gros, puis la quantité et la référence (une ligne) ou le nombre de
  // lignes, puis la date d'expédition ; le détail ligne par ligne au survol.
  // Trop étroit, le bloc ne garde que le client, à la verticale.
  function blocFrise(g) {
    var ls = g.lignes, l0 = ls[0], seule = ls.length === 1;
    var aFaire = ls.filter(function (l) { return l.groupe !== 'pretes'; });
    var faite = !aFaire.length;
    var urgente = ls.some(function (l) { return l.urgence; });
    var partiel = ls.some(function (l) { return l.groupe === 'partiel'; });
    var retard = ls.some(function (l) { return l.retard; });
    var exp = ls.map(function (l) { return l.expedition; }).filter(Boolean).sort()[0];
    var cls = 'pf-bloc ' + teinteClient(l0.client) + (faite ? ' faite' : partiel ? ' partiel' : '') + (urgente ? ' urgente' : '');
    var detail = ls.map(function (l) {
      return 'L' + l.ligne + ' · ' + l.article + ' · ' + qteU(l, l.reste) + ' · ' + etatLigne(l) + (l.urgence ? ' · urgente' : '');
    }).join('\n');
    var sources = ls.map(function (l) { return SOURCES_JOUR[l.jour_source] ? SOURCES_JOUR[l.jour_source](l) : ''; })
      .filter(function (x, i, t) { return x && t.indexOf(x) === i; }).join(' · ');
    var b = h('div', {className: cls, 'data-cde': g.numero,
      'data-tip': tip('pf|' + g.numero + '|' + l0.jour_prepa, l0.client + ' · commande ' + g.numero,
        detail + (exp ? '\nExpédition ' + dateFr(exp) : ''),
        sources + (DROITS.adv && !faite ? ' · glisser sur un autre jour pour ' + (seule ? 'la déplacer' : 'déplacer la commande') : '')),
      onClick: function () { ouvrirFiche(l0.cle); }},
      h('div', {className: 'pf-cli', text: l0.client}),
      h('div', {className: 'pf-l2', text: seule ? qteU(l0, l0.reste) + ' · ' + l0.article : ls.length + ' lignes · ' + g.numero}),
      h('div', {className: 'pf-l3' + (retard ? ' retard' : ''), text: exp ? 'à expédier le ' + dateFr(exp).slice(0, 5) : 'expédition non datée'}),
      urgente ? h('div', {className: 'pf-badge', text: 'Urgente'})
        : partiel ? h('div', {className: 'pf-badge partiel', text: 'Stock partiel'})
        : faite ? h('div', {className: 'pf-badge faite', text: 'Prête'}) : null);
    if (DROITS.adv && !faite) {
      b.setAttribute('draggable', 'true');
      b.addEventListener('dragstart', function (ev) {
        S.friseDrag = aFaire.map(function (l) { return l.cle; });
        b.classList.add('attrapee');
        try { ev.dataTransfer.effectAllowed = 'move'; ev.dataTransfer.setData('text/plain', g.numero); } catch (e) {}
      });
      b.addEventListener('dragend', function () {
        S.friseDrag = null;
        b.classList.remove('attrapee');
        document.querySelectorAll('.pf-seg.cible').forEach(function (x) { x.classList.remove('cible'); });
      });
    }
    return b;
  }

  // Une semaine : son titre, une ligne d'en-têtes de jour, puis une barre où
  // chaque jour est un segment et chaque commande un bloc. En-têtes et
  // segments se partagent la largeur de la même façon : ils tombent l'un
  // sous l'autre.
  function semaineFrise(lundi, lignes, auj, actif) {
    var jours = [];
    for (var i = 0; i < 7; i++) {
      var j = decaler(lundi, i);
      var ls = lignes.filter(function (l) { return l.jour_prepa === j; });
      if (i < 5 || ls.length) jours.push({jour: j, lignes: ls});
    }
    var etat = function (x) {
      return (x.jour === auj ? ' today' : '') + (x.jour === actif ? ' choisi' : '') + (x.jour < auj ? ' passe' : '');
    };
    var entetes = h('div', {className: 'pf-jours'}, jours.map(function (x) {
      var aFaire = x.lignes.filter(function (l) { return l.groupe !== 'pretes'; }).length;
      return h('button', {type: 'button', className: 'pf-jh' + etat(x), disabled: x.jour < auj,
        'aria-pressed': x.jour === actif ? 'true' : 'false',
        onClick: function () { choisirJour(x.jour === actif ? auj : x.jour); }},
        h('span', {className: 'pf-jh-lib', text: jourCourt(x.jour)}),
        h('span', {className: 'pf-jh-n', text: aFaire ? aFaire + ' à faire' : x.lignes.length ? 'fait' : '—'}));
    }));
    var barre = h('div', {className: 'pf-barre'}, jours.map(function (x) {
      var seg = h('div', {className: 'pf-seg' + etat(x), 'data-jour': x.jour}, parEnvoi(x.lignes).map(blocFrise));
      if (DROITS.adv && x.jour >= auj) {
        seg.addEventListener('dragover', function (ev) {
          if (!(S.friseDrag || S.prepaDrag)) return;
          ev.preventDefault();
          seg.classList.add('cible');
        });
        seg.addEventListener('dragleave', function (ev) { if (!seg.contains(ev.relatedTarget)) seg.classList.remove('cible'); });
        seg.addEventListener('drop', function (ev) {
          var cle = S.friseDrag || (S.prepaDrag && S.prepaDrag.cle);
          seg.classList.remove('cible');
          if (!cle) return;
          ev.preventDefault();
          S.friseDrag = null; S.prepaDrag = null;
          deplacerJour(cle, x.jour);
        });
      }
      return seg;
    }));
    return h('div', {className: 'pf-semaine'},
      h('div', {className: 'pf-sem' + (lundi === lundiDe(auj) ? ' courante' : ''),
        text: 'S' + numSemaine(lundi) + ' — ' + dateFr(lundi).slice(0, 5) + ' au ' + dateFr(decaler(lundi, 4)).slice(0, 5)}),
      entetes, barre);
  }

  // Le planning de prépa : une, deux ou quatre semaines, comme le planning
  // machine. Un clic sur un jour filtre le tableau ; l'ADV glisse une
  // préparation (de la frise ou du tableau) sur un autre jour pour la déplacer.
  function frisePrepa(c, d) {
    var auj = aujourdhuiPrepa();
    var actif = jourActif();
    var courant = lundiDe(auj);
    var lundi0 = S.semaine && S.semaine > courant ? S.semaine : courant;
    var lignes = (d.lignes || []).filter(function (l) { return l.jour_prepa && l.groupe !== 'attente'; });
    var sansDate = (d.lignes || []).filter(function (l) { return !l.jour_prepa && l.groupe !== 'attente' && l.groupe !== 'pretes'; }).length;
    var vue = VUES_PREPA[S.vue];
    var changerVue = async function (v) { S.vue = v; S.horizon = VUES_PREPA[v].jours; S.charge = false; render(); await charger(); render(); };
    var aller = function (lundi) { S.semaine = lundi > courant ? lundi : null; render(); };
    var outils = h('div', {className: 'pf-tete'},
      h('div', {className: 'pf-titre', text: 'Planning de prépa'}),
      h('span', {className: 'pf-espace'}),
      sansDate ? h('span', {className: 'pf-sans-date', text: sansDate + ' sans date d’expédition'}) : null,
      h('div', {className: 'pf-groupe'}, Object.keys(VUES_PREPA).map(function (v) {
        return h('button', {type: 'button', className: 'pf-gbtn' + (S.vue === v ? ' active' : ''), onClick: function () { if (S.vue !== v) changerVue(v); }},
          VUES_PREPA[v].lib);
      })),
      h('div', {className: 'pf-groupe'},
        h('button', {type: 'button', className: 'pf-gbtn', 'aria-label': 'Semaine précédente', disabled: lundi0 <= courant,
          onClick: function () { aller(decaler(lundi0, -7)); }}, '◀'),
        h('button', {type: 'button', className: 'pf-gbtn' + (lundi0 === courant ? ' active' : ''), onClick: function () { aller(courant); }}, 'actuelle'),
        h('button', {type: 'button', className: 'pf-gbtn', 'aria-label': 'Semaine suivante', onClick: function () { aller(decaler(lundi0, 7)); }}, '▶')),
      h('button', {type: 'button', className: 'adv-puce' + (actif ? '' : ' active'),
        onClick: function () { S.jour = actif ? 'tous' : null; render(); }}, 'Tous les jours'));
    var semaines = [];
    for (var w = 0; w < vue.sem; w++) semaines.push(semaineFrise(decaler(lundi0, 7 * w), lignes, auj, actif));
    c.appendChild(h('div', {className: 'pf'}, outils, semaines));
  }

  // Un bloc trop étroit ne garde que le client, à la verticale (comme le
  // planning machine). La largeur dépend de l'écran : on la mesure.
  function ajusterBlocsFrise() {
    document.querySelectorAll('.pf-bloc').forEach(function (b) { b.classList.toggle('etroit', b.clientWidth < 92); });
  }
  var _ajusteFrise = null;
  window.addEventListener('resize', function () {
    clearTimeout(_ajusteFrise);
    _ajusteFrise = setTimeout(ajusterBlocsFrise, 120);
  });

  // La ligne d'un envoi de plusieurs lignes : client, commande, totaux ; un
  // clic l'ouvre ou la referme sur ses lignes. « Ordre d'expé » montre tout
  // ce qui part ce jour-là à cette adresse.
  function ligneEnvoi(g, ouvert, rang) {
    var ls = g.lignes, l0 = ls[0];
    var unites = ls.map(function (l) { return unite(l); }).filter(function (u, i, t) { return t.indexOf(u) === i; });
    var somme = function (f) { return ls.reduce(function (s, l) { return s + (f(l) || 0); }, 0); };
    var memeUnite = unites.length === 1;
    var urgente = ls.some(function (l) { return l.urgence; });
    var retard = ls.some(function (l) { return l.retard; });
    var nbEmpl = somme(function (l) { return ((l.stock || {}).emplacements || []).length; });
    var sortie = somme(function (l) { return (l.stock || {}).sortie_prod; });
    var alloue = somme(function (l) { return (l.stock || {}).alloue; });
    var basculer = function () {
      S.ouverts[g.cle] = !S.ouverts[g.cle];
      var yt = (document.querySelector('.adv-table-wrap') || {}).scrollTop;
      render();
      var tw = document.querySelector('.adv-table-wrap');
      if (tw && yt) tw.scrollTop = yt;
    };
    return h('tr', {className: 'adv-pl adv-envoi' + (ouvert ? ' ouvert' : '') + (retard ? ' retard' : '') + (urgente ? ' urgente' : ''),
        'aria-expanded': ouvert ? 'true' : 'false', onClick: basculer,
        'data-tip': tip('envoi|' + g.cle, l0.client + ' · commande ' + l0.numero,
          ls.length + ' lignes qui partent ensemble (même date, même adresse)', ouvert ? 'Cliquer pour replier' : 'Cliquer pour voir les lignes')},
      DROITS.adv ? h('td', {className: 'c-poignee'}) : null,
      h('td', {className: 'c-rang'}, h('div', {className: 'adv-rang-cel'},
        h('div', {className: 'adv-rang' + (urgente ? ' urgente' : ''), text: String(rang)}),
        h('span', {className: 'adv-envoi-caret', 'aria-hidden': 'true', text: '▸'}))),
      h('td', {className: 'c-client'}, h('div', {className: 'c-client-t', text: l0.client, title: l0.client})),
      h('td', {className: 'c-cde adv-mono', text: l0.numero}),
      h('td', {className: 'c-ref adv-envoi-n', text: ls.length + ' lignes'}),
      h('td', {className: 'c-num c-qte', 'data-l': 'Commandé'}, memeUnite ? qteU(l0, somme(function (l) { return l.qte; })) : '—'),
      h('td', {className: 'c-num c-stk' + (alloue ? '' : ' adv-muet'), 'data-l': 'En stock'}, alloue && memeUnite ? fN(alloue) : '—'),
      h('td', {className: 'c-num c-fort c-aprep', 'data-l': 'À préparer'}, memeUnite ? fN(somme(function (l) { return l.reste; })) : '—'),
      h('td', {className: 'c-empl'}, h('div', {className: 'adv-empl'},
        sortie ? h('span', {className: 'adv-sortie-prod'}, h('b', {text: 'Sortie prod'}), ' · ' + fN(sortie)) : null,
        nbEmpl ? h('span', {}, h('b', {text: String(nbEmpl)}), ' emplacement' + (nbEmpl > 1 ? 's' : '')) : null)),
      h('td', {className: 'c-quand' + (retard ? ' adv-date-retard' : '')}, l0.expedition ? dateFr(l0.expedition) : 'Non datée'),
      h('td', {className: 'c-act'}, h('div', {className: 'adv-actions'}, boutonsPrepa(ls))));
  }

  var VIDES_PREPA = {
    preparable: 'Rien à préparer sur les %n prochains jours.',
    partiel: 'Aucune ligne en stock partiel sur les %n prochains jours.',
    pretes: 'Aucune préparation prête en attente de départ.'
  };
  var VIDES_JOUR = {
    preparable: 'Rien à préparer le %j.',
    partiel: 'Aucune ligne en stock partiel le %j.',
    pretes: 'Aucune préparation prête le %j.'
  };

  function renderPrepa(c) {
    var histo = S.sous === 'historique';
    var d = (histo ? S.historique : S.prepa) || {};
    var droite = histo
      ? [h('div', {className: 'adv-puces'}, HISTO_JOURS.map(function (n) {
          return h('button', {type: 'button', className: 'adv-puce' + (S.histoJours === n ? ' active' : ''),
            onClick: async function () { S.histoJours = n; S.charge = false; render(); await charger(); render(); }}, n + ' jours');
        }))]
      : [DROITS.adv && d.ordre_manuel ? h('button', {type: 'button', className: 'btn btn-petit',
          'data-tip': tip('btn-ordre-auto', 'Revenir à l’ordre automatique', 'Retire tous les rangs fixés à la main : la Prépa se range de nouveau par date d’expédition.'),
          onClick: async function () {
            try {
              await api('/api/adv/prepa/ordre', {method: 'DELETE'});
              await charger(); S.carnet = null; render();
              toast('Ordre automatique rétabli.');
            } catch (e) { toast(e.message, 'danger'); }
          }}, 'Ordre automatique') : null];
    c.appendChild(h('div', {className: 'adv-tete'},
      h('div', {}, h('h1', {text: 'Préparations'}),
        h('div', {className: 'adv-maj'}, h('span', {className: 'adv-rvgi'}),
          h('span', {text: ' · ' + (histo ? 'Passées « Prête » ces ' + S.histoJours + ' derniers jours, la plus récente en tête'
            : d.ordre_manuel ? 'Ordre fixé par l’ADV, puis date d’expédition' : 'Par date d’expédition, retards en tête')}))),
      h('div', {className: 'adv-puces'}, droite,
        h('button', {type: 'button', className: 'btn btn-petit', onClick: async function () {
          await charger(); render(); toast(histo ? 'Historique actualisé.' : 'Préparations actualisées.');
        }}, 'Actualiser'))));
    if (!histo && d.lignes) frisePrepa(c, d);
    ongletsPrepa(c);
    if (avertissements(c, d)) return;
    if (histo) { tableHistorique(c, d); return; }

    var onglet = ONGLETS_PREPA.find(function (o) { return o.cle === S.groupe; }) || ONGLETS_PREPA[0];
    var jour = jourActif();
    var ls = (d.lignes || []).filter(function (l) { return onglet.groupes.indexOf(l.groupe) !== -1 && duJour(l, jour); });
    if (!ls.length) {
      c.appendChild(h('div', {className: 'adv-vide', text: jour ? VIDES_JOUR[onglet.cle].replace('%j', jourLong(jour))
        : VIDES_PREPA[onglet.cle].replace('%n', S.horizon)}));
      return;
    }
    // Le rang suit l'ordre de travail dans l'onglet ; une prépa prête n'en a pas.
    // Les lignes qui partent ensemble se replient sous la ligne de leur envoi.
    var rangDe = function (l) { return onglet.cle === 'pretes' ? '·' : ls.indexOf(l) + 1; };
    var ctxDe = function (l) { return {lignes: ls, index: ls.indexOf(l), onglet: onglet.cle}; };
    var corps = h('tbody', {});
    parEnvoi(ls).forEach(function (g) {
      if (g.lignes.length === 1) { corps.appendChild(cartePrepa(g.lignes[0], rangDe(g.lignes[0]), ctxDe(g.lignes[0]))); return; }
      var ouvert = !!S.ouverts[g.cle];
      corps.appendChild(ligneEnvoi(g, ouvert, rangDe(g.lignes[0])));
      g.lignes.forEach(function (l) {
        var tr = cartePrepa(l, rangDe(l), ctxDe(l));
        tr.classList.add('adv-enfant');
        if (!ouvert) tr.classList.add('replie');
        corps.appendChild(tr);
      });
    });
    c.appendChild(h('div', {className: 'adv-table-wrap adv-prepa-wrap'},
      h('table', {className: 'adv-table adv-prepa-table'}, entetePrepa(), corps)));
  }

  /* ── Ordre d'expédition : ce qui part un jour pour une adresse ── */

  // Toutes les lignes de la Prépa qui partent le même jour que `cle`, à la
  // même adresse de livraison — toutes commandes confondues. Sans adresse
  // connue dans RVGI, on s'en tient à la commande.
  function lignesOrdre(cle) {
    var tous = (S.prepa && S.prepa.lignes) || [];
    var l = tous.find(function (x) { return x.cle === cle; });
    if (!l) return null;
    var dest = l.destination && l.destination.cle;
    var ls = tous.filter(function (x) {
      return x.expedition === l.expedition && (dest ? x.destination && x.destination.cle === dest : x.numero === l.numero);
    }).sort(function (a, b) { return a.numero === b.numero ? a.ligne - b.ligne : (a.numero < b.numero ? -1 : 1); });
    return {l: l, lignes: ls};
  }

  function ouvrirOrdre(cle, sansAdresse) {
    var o = lignesOrdre(cle);
    if (!o) {
      if (!S.prepa) return;                  // données pas encore là : render() rouvrira
      S.ordreExpe = null; ecrireUrl();
      toast('Cette ligne n’est plus dans la Prépa.', 'danger');
      return;
    }
    var m = document.getElementById('mroot');
    m.textContent = '';
    cacherTip();
    S.ligne = null; S.reglages = null;
    S.ordreExpe = cle;
    if (!sansAdresse) ecrireUrl();
    var l = o.l, d = l.destination || {};
    var adresse = [d.adr1, d.adr2, [d.cp, d.ville].filter(Boolean).join(' ') + (d.pays ? ' (' + d.pays + ')' : '')]
      .filter(function (x) { return x && x.trim(); });
    var auj = aujourdhuiPrepa();
    var deps = [];
    o.lignes.forEach(function (x) {
      (x.departs || []).forEach(function (dp) { if (!dp.parti_le && dp.date_enlevement && dp.date_enlevement >= auj) deps.push(dp); });
    });
    deps.sort(function (a, b) { return a.date_enlevement < b.date_enlevement ? -1 : 1; });
    var dep = deps[0];
    var commandes = o.lignes.map(function (x) { return x.numero; }).filter(function (n, i, t) { return t.indexOf(n) === i; });
    var ouPrelever = function (x) {
      var st = x.stock || {};
      var t = (st.emplacements || []).map(function (e) { return e.emplacement + ' · ' + fN(e.quantite); });
      if (st.sortie_prod) t.push('Sortie prod · ' + fN(st.sortie_prod));
      return t.join(', ') || '—';
    };
    var info = function (lib, val) { return h('div', {className: 'od-info'}, h('div', {className: 'od-l', text: lib}), h('div', {className: 'od-v', text: val})); };
    var fermer = function () { fermerFiche(); };
    var corps = h('tbody', {}, o.lignes.map(function (x) {
      return h('tr', {},
        h('td', {className: 'adv-mono', text: x.numero + '-L' + x.ligne}),
        h('td', {className: 'adv-mono', text: x.ref_client || '—'}),
        h('td', {className: 'adv-mono', text: x.article}),
        h('td', {className: 'od-des', text: x.designation || ''}),
        h('td', {className: 'num', text: qteU(x, x.reste)}),
        h('td', {className: 'od-empl', text: ouPrelever(x)}),
        h('td', {text: etatLigne(x)}));
    }));
    var modal = h('div', {className: 'adv-modal adv-ordre', role: 'dialog', 'aria-modal': 'true', 'aria-label': 'Ordre d’expédition'},
      h('div', {className: 'od-tete'},
        h('div', {},
          h('div', {className: 'od-org', text: BOOT.org || ''}),
          h('h3', {text: 'Ordre d’expédition'}),
          h('div', {className: 'od-date', text: l.expedition ? 'Expédition le ' + dateLongue(l.expedition) : 'Expédition non datée'})),
        h('button', {type: 'button', className: 'fi-fermer od-ecran', 'aria-label': 'Fermer', onClick: fermer, html:
          '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><line x1="6" y1="6" x2="18" y2="18"/><line x1="18" y1="6" x2="6" y2="18"/></svg>'})),
      h('div', {className: 'od-infos'},
        h('div', {className: 'od-info od-dest'}, h('div', {className: 'od-l', text: 'Destinataire'}),
          h('div', {className: 'od-v od-rs', text: d.rs || l.client}),
          adresse.length ? adresse.map(function (x) { return h('div', {className: 'od-adr', text: x}); })
            : h('div', {className: 'od-adr adv-muet', text: 'Adresse de livraison absente de RVGI'})),
        info('Client', l.client),
        info('Transport', dep ? (dep.transporteur || 'Transporteur à préciser') + ' · enlèvement le ' + dateFr(dep.date_enlevement) : 'Aucun enlèvement prévu dans MyExpé'),
        info('Commande' + (commandes.length > 1 ? 's' : ''), commandes.join(', '))),
      h('table', {className: 'od-table'},
        h('thead', {}, h('tr', {}, ['Cde-L', 'Réf client', 'Réf produit', 'Désignation', 'Quantité', 'Où prélever', 'État'].map(function (t) {
          return h('th', {className: t === 'Quantité' ? 'num' : null, text: t});
        }))), corps),
      h('div', {className: 'od-total', text: o.lignes.length + ' ligne' + (o.lignes.length > 1 ? 's' : '') + ' · ' + commandes.length + ' commande' + (commandes.length > 1 ? 's' : '')}),
      h('div', {className: 'm-pied od-ecran'},
        h('button', {type: 'button', className: 'btn', onClick: fermer}, 'Fermer'),
        h('button', {type: 'button', className: 'btn btn-accent', onClick: function () { window.print(); }}, 'Imprimer')));
    var voile = h('div', {className: 'adv-voile', onClick: function (ev) { if (ev.target === voile) fermerFiche(); }}, modal);
    m.appendChild(voile);
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
      case 'info': return (l.infos && l.infos[0]) ? l.infos[0].texte : null;
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
  // Ce que colore une règle : la colonne de sa condition (appliquer vide),
  // une autre colonne, ou toute la ligne. La première qui s'applique l'emporte.
  function regleCellule(l, col, regles) {
    var rs = regles || S.mef;
    for (var i = 0; i < rs.length; i++) {
      if ((rs[i].appliquer || rs[i].colonne) === col && regleVraie(rs[i], l)) return rs[i];
    }
    return null;
  }
  function regleLigne(l) {
    for (var i = 0; i < S.mef.length; i++) {
      if (S.mef[i].appliquer === 'ligne' && regleVraie(S.mef[i], l)) return S.mef[i];
    }
    return null;
  }
  // Ton « rouge-2 » de la palette élargie : teinte (angle, saturation) et nuance.
  var TEINTES = {};
  (REF.teintes || []).forEach(function (t) { TEINTES[t.cle] = t; });
  function teinteDe(ton) {
    var m = /^([a-z]+)-([123])$/.exec(ton || '');
    var t = m && TEINTES[m[1]];
    return t ? {h: t.h, c: t.c, n: m[2], label: t.label} : null;
  }
  // Pose sur une cellule, une ligne ou un échantillon les classes du ton et du
  // rendu ; la couleur elle-même est calculée par mysifa_adv.css.
  function habiller(el, rg) {
    var t = teinteDe(rg.ton);
    if (t) {
      el.classList.add('mef-t', 'mef-n' + t.n);
      el.style.setProperty('--mef-h', String(t.h));
      el.style.setProperty('--mef-c', String(t.c));
    } else el.classList.add('mef-' + rg.ton);
    el.classList.add('mef-r-' + (rg.rendu || 'fond'));
    return el;
  }
  function libTon(ton) {
    var t = teinteDe(ton);
    if (t) {
      var n = (REF.nuances || []).find(function (x) { return x.cle === t.n; });
      return t.label + (n ? ' · ' + n.label.toLowerCase() : '');
    }
    var o = REF.tons.find(function (x) { return x.cle === ton; });
    return o ? o.label + ' (thème)' : ton;
  }

  function regleParDefaut() {
    return {colonne: 'a_fabriquer', operateur: 'gt', cible: 'valeur', valeur: '0', ton: 'warn', appliquer: '', rendu: 'fond'};
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
      return {colonne: r.colonne, operateur: r.operateur, cible: r.cible || 'valeur', valeur: r.valeur || '',
              ton: r.ton, appliquer: r.appliquer || '', rendu: r.rendu || 'fond'};
    });
    var palette = -1;                 // règle dont la palette est dépliée
    var liste = h('div', {className: 'mef-liste'});
    var pied = h('div', {className: 'mef-compte adv-muet'});
    var lignes = (S.carnet && S.carnet.lignes) || [];

    function nbLignes(rg) {
      var n = 0;
      lignes.forEach(function (l) { if (regleVraie(rg, l)) n++; });
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
    // Ce qu'on peut colorer : la colonne de la condition si elle est affichée,
    // toute la ligne, ou une autre colonne du carnet.
    function optionsAppliquer(rg) {
      var o = [];
      if (COL_PAR_CLE[rg.colonne]) o.push({cle: '', label: 'cette colonne'});
      o.push({cle: 'ligne', label: 'toute la ligne'});
      colonnesOrdonnees().forEach(function (c) {
        if (c.cle !== rg.colonne) o.push({cle: c.cle, label: 'la colonne ' + c.label});
      });
      return o;
    }
    function echantillon(rg) {
      return habiller(h('span', {className: 'mef-ech-p'}, h('span', {className: 'mef-p', text: 'Aa'})), rg);
    }
    function dessinerPalette(rg, i) {
      var choisir = function (ton) { return function () { rg.ton = ton; palette = -1; dessiner(); }; };
      var theme = h('div', {className: 'mef-pal-theme'}, REF.tons.map(function (t) {
        return h('button', {type: 'button', className: 'mef-ton mef-' + t.cle + (rg.ton === t.cle ? ' actif' : ''),
          'aria-label': t.label + ' (thème)', 'data-tip': tip('mef-ton|' + i + '|' + t.cle, t.label, 'Suit la palette du thème'),
          onClick: choisir(t.cle)});
      }));
      var grille = h('div', {className: 'mef-pal-grille', role: 'radiogroup', 'aria-label': 'Teinte et nuance'});
      grille.style.setProperty('--mef-nb', String((REF.teintes || []).length));
      (REF.nuances || []).forEach(function (n) {
        (REF.teintes || []).forEach(function (t) {
          var ton = t.cle + '-' + n.cle;
          var b = habiller(h('button', {type: 'button', className: 'mef-ech' + (rg.ton === ton ? ' actif' : ''),
            role: 'radio', 'aria-checked': rg.ton === ton ? 'true' : 'false', 'aria-label': t.label + ' · ' + n.label,
            'data-tip': tip('mef-ech|' + i + '|' + ton, t.label, n.label), onClick: choisir(ton)}), {ton: ton, rendu: 'fond'});
          grille.appendChild(b);
        });
      });
      var rendus = h('div', {className: 'mef-pal-rendus', role: 'radiogroup', 'aria-label': 'Rendu'}, (REF.rendus || []).map(function (r) {
        return h('button', {type: 'button', className: 'btn btn-petit' + (rg.rendu === r.cle ? ' actif' : ''),
          role: 'radio', 'aria-checked': rg.rendu === r.cle ? 'true' : 'false',
          onClick: function () { rg.rendu = r.cle; dessiner(); }}, r.label);
      }));
      return h('div', {className: 'mef-palette'},
        h('div', {className: 'mef-pal-l', text: 'Thème'}), theme,
        h('div', {className: 'mef-pal-l', text: 'Palette · une colonne par teinte, du pâle au soutenu'}), grille,
        h('div', {className: 'mef-pal-l', text: 'Rendu'}), rendus);
    }
    function dessiner() {
      liste.textContent = '';
      if (!E.length) {
        liste.appendChild(h('div', {className: 'adv-vide', text: 'Aucune règle. Exemples : « À fabriquer > 0 » en orange ; si « Expédition avant aujourd’hui », colorer toute la ligne en rouge pâle.'}));
      }
      E.forEach(function (rg, i) {
        var typ = TYPE_COL[rg.colonne];
        var sansCible = rg.operateur === 'vide' || rg.operateur === 'non_vide';
        var compte = h('span', {className: 'mef-n adv-muet'});
        function majCompte() { var n = nbLignes(rg); compte.textContent = n + ' ligne' + (n > 1 ? 's' : ''); }
        var colSel = select(REF.colonnes, rg.colonne, function (v) {
          rg.colonne = v;
          var t = TYPE_COL[v];
          rg.operateur = (REF.operateurs[t] || [])[0].cle;
          rg.cible = 'valeur';
          rg.valeur = valeurParDefaut(t, 'valeur');
          if (rg.appliquer === v) rg.appliquer = '';
          if (!rg.appliquer && !COL_PAR_CLE[v]) rg.appliquer = 'ligne';
          dessiner();
        }, 'Colonne de la condition');
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
        var applSel = select(optionsAppliquer(rg), rg.appliquer || '', function (v) { rg.appliquer = v; }, 'Colorer');
        var choix = h('button', {type: 'button', className: 'mef-choix' + (palette === i ? ' ouvert' : ''),
          'aria-expanded': palette === i ? 'true' : 'false', 'aria-label': 'Couleur : ' + libTon(rg.ton),
          'data-tip': tip('mef-choix|' + i, 'Couleur', libTon(rg.ton) + ' · ' + ((REF.rendus || []).find(function (r) { return r.cle === rg.rendu; }) || {label: ''}).label),
          onClick: function () { palette = palette === i ? -1 : i; dessiner(); }},
          echantillon(rg), h('span', {className: 'mef-choix-f', text: '▾'}));
        var bouger = function (d) {
          return function () {
            var j = i + d;
            if (j < 0 || j >= E.length) return;
            var x = E[i]; E[i] = E[j]; E[j] = x;
            if (palette === i) palette = j; else if (palette === j) palette = i;
            dessiner();
          };
        };
        liste.appendChild(h('div', {className: 'mef-regle'},
          h('span', {className: 'mef-rang', text: String(i + 1)}),
          h('div', {className: 'mef-corps'},
            h('div', {className: 'mef-cond'}, h('span', {className: 'mef-mot', text: 'Si'}), colSel, opSel, zoneValeur),
            h('div', {className: 'mef-effet'}, h('span', {className: 'mef-mot', text: 'colorer'}), applSel,
              h('span', {className: 'mef-mot', text: 'en'}), choix, compte),
            palette === i ? dessinerPalette(rg, i) : null),
          h('div', {className: 'mef-ordre'},
            h('button', {type: 'button', className: 'btn btn-petit', 'aria-label': 'Monter', disabled: i === 0, onClick: bouger(-1)}, '↑'),
            h('button', {type: 'button', className: 'btn btn-petit', 'aria-label': 'Descendre', disabled: i === E.length - 1, onClick: bouger(1)}, '↓'),
            h('button', {type: 'button', className: 'btn btn-petit', 'aria-label': 'Supprimer la règle',
              onClick: function () { E.splice(i, 1); palette = -1; dessiner(); }}, '×'))));
        majCompte();
      });
      pied.textContent = E.length + ' / ' + REF.max + ' règles · la première qui s’applique à une cellule (ou à la ligne) l’emporte';
      ajout.disabled = E.length >= REF.max;
    }
    var ajout = h('button', {type: 'button', className: 'btn btn-petit', onClick: function () { E.push(regleParDefaut()); palette = -1; dessiner(); }}, '+ Ajouter une règle');
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
      h('div', {className: 'm-sous', text: 'Colore une cellule, une autre colonne ou toute la ligne quand la condition est remplie. Règles communes à tout le service.'}),
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
    S.ordreExpe = null;
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

  // L'adresse de livraison d'une ligne (RVGI), sur une ou deux lignes.
  function adresseLivraison(l) {
    var d = l.destination || {};
    var lignes = [d.rs, [d.adr1, d.adr2].filter(Boolean).join(', '), [d.cp, d.ville].filter(Boolean).join(' ') + (d.pays ? ' (' + d.pays + ')' : '')]
      .filter(function (x) { return x && x.trim(); });
    return lignes.length ? lignes.map(function (x) { return h('div', {text: x}); })
      : h('div', {className: 'adv-muet', text: 'Adresse absente de RVGI'});
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
    S.ordreExpe = null;
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
        h('b', {text: 'Sortie prod'}), ' · ' + fN(st.sortie_prod) + ((st.dossiers_prod || []).length
          ? ' · ' + (st.dossiers_prod.length > 1 ? st.dossiers_prod.length + ' dossiers' : 'dossier ' + st.dossiers_prod[0]) : ''));
      if ((st.dossiers_prod || []).length > 1) puceSortie.setAttribute('data-tip', tip(l.cle + '|fisortie', 'Sortie de production', l.etapes.stock.detail, 'Dossiers ' + st.dossiers_prod.join(', ')));
      if (empl) empl.appendChild(puceSortie);
      else empl = h('div', {className: 'adv-empl'}, puceSortie);
    }
    var prepa = h('div', {className: 'fi-carte'},
      h('h4', {text: 'Préparation'}),
      h('div', {className: 'fi-prepa'},
        h('span', {className: 'adv-badge ' + ({prete: 'ok', en_cours: 'warn'}[l.prepa.statut] || ''), text: LIB_PREPA[l.prepa.statut] || l.prepa.statut}),
        l.prepa.maj_par ? h('span', {className: 'adv-muet', text: l.prepa.maj_par + ' · ' + dateFr(l.prepa.maj_le) + ' ' + heure(l.prepa.maj_le)}) : null,
        h('div', {className: 'fi-prepa-b'}, boutonsPrepa(l, {libelles: true}))),
      h('div', {className: 'fi-sous-t', text: 'Où prélever' + (st.connu ? ' · ' + qteU(l, st.total) + ' en stock pour l’article' : '')}),
      empl,
      h('div', {className: 'fi-sous-t', text: 'Livrer à'}),
      h('div', {className: 'fi-livrer'}, adresseLivraison(l)));

    // ── Production et départs ──
    var STATUT_DOS = {attente: ['En attente', ''], en_cours: ['En cours', 'warn'], termine: ['Terminé', 'ok']};
    var rangees = h('div', {className: 'fi-rangees'});
    if (!l.dossiers.length) rangees.appendChild(h('div', {className: 'adv-muet', text: 'Aucun dossier au planning.'}));
    l.dossiers.forEach(function (d) {
      var sd = STATUT_DOS[d.statut] || [d.statut || '', ''];
      rangees.appendChild(h('a', {className: 'fi-rangee', href: lienPlanning(d)},
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

    // ── Infos de suivi : le fil, la plus récente en tête ──
    var infos = l.infos || [];
    var champInfo = null;
    var filInfos = h('div', {className: 'fi-infos-fil'});
    if (!infos.length) filInfos.appendChild(h('div', {className: 'adv-muet', text: DROITS.adv ? 'Aucune info. Notez ici pourquoi la ligne n’est pas partie, où elle en est.' : 'Aucune info de suivi.'}));
    infos.forEach(function (x) {
      var suppr = null;
      if (DROITS.adv) {
        // Deux temps : le premier clic demande confirmation, le second supprime.
        suppr = h('button', {type: 'button', className: 'fi-info-suppr', 'aria-label': 'Supprimer cette info', text: '×'});
        suppr.addEventListener('click', async function () {
          if (!suppr.classList.contains('confirmer')) {
            suppr.classList.add('confirmer'); suppr.textContent = 'Supprimer ?';
            setTimeout(function () { if (suppr.isConnected) { suppr.classList.remove('confirmer'); suppr.textContent = '×'; } }, 4000);
            return;
          }
          suppr.disabled = true;
          try { await supprimerInfo(l, x.id); toast('Info supprimée.'); render(); fermerFiche(true); ouvrirFiche(l.cle, true); }
          catch (e) { toast(e.message, 'danger'); suppr.disabled = false; }
        });
      }
      filInfos.appendChild(h('div', {className: 'fi-info'},
        h('span', {className: 'adv-info', 'aria-hidden': 'true', text: '?'}),
        h('div', {className: 'fi-info-c'},
          h('div', {className: 'fi-info-t', text: x.texte}),
          h('div', {className: 'fi-info-m adv-muet', text: (x.cree_par || '') + (x.cree_par ? ' · ' : '') + dateFr(x.cree_le) + (heure(x.cree_le) ? ' à ' + heure(x.cree_le) : '')})),
        suppr));
    });
    var saisieInfo = null;
    if (DROITS.adv) {
      champInfo = h('input', {type: 'text', maxlength: '500', className: 'fi-info-champ',
        placeholder: 'Ex. attente retour BAT client, palette bloquée, transporteur relancé…', 'aria-label': 'Nouvelle info de suivi'});
      var ajoutInfo = h('button', {type: 'button', className: 'btn btn-accent btn-petit', text: 'Ajouter'});
      var envoyer = async function () {
        var t = champInfo.value.trim();
        if (ajoutInfo.disabled) return;           // envoi déjà en cours
        if (!t) { champInfo.focus(); return; }
        ajoutInfo.disabled = true; champInfo.readOnly = true;
        try {
          await ajouterInfo(l, t);
          toast('Info ajoutée.');
          render(); fermerFiche(true); S.focusInfo = true; ouvrirFiche(l.cle, true);
        } catch (e) { toast(e.message, 'danger'); ajoutInfo.disabled = false; champInfo.readOnly = false; }
      };
      ajoutInfo.addEventListener('click', envoyer);
      champInfo.addEventListener('keydown', function (ev) { if (ev.key === 'Enter') { ev.preventDefault(); envoyer(); } });
      saisieInfo = h('div', {className: 'fi-info-saisie'}, champInfo, ajoutInfo);
    }
    var carteInfos = h('div', {className: 'fi-carte fi-infos' + (infos.length ? ' avec' : '')},
      h('h4', {}, h('span', {className: 'adv-info', 'aria-hidden': 'true', text: '?'}), ' Infos de suivi',
        infos.length ? h('span', {className: 'adv-muet', text: ' · ' + infos.length}) : null),
      saisieInfo, filInfos);

    var liens = h('div', {className: 'adv-liens'},
      DROITS.adv ? h('a', {className: 'btn btn-petit', href: '/erp#/commandes?q=' + encodeURIComponent(l.numero)}, 'Commande dans l’ERP') : null,
      st.connu ? h('a', {className: 'btn btn-petit', href: '/stock?ref=' + encodeURIComponent(l.article)}, 'Article dans MyStock') : null);

    var modal = h('div', {className: 'adv-modal adv-fiche', role: 'dialog', 'aria-modal': 'true', 'aria-label': 'Ligne ' + l.numero + ' · ' + l.ligne},
      tete,
      h('div', {className: 'fi-grille'}, carteInfos, prepa,
        h('div', {className: 'fi-carte'}, h('h4', {text: 'Chaîne de valeur'}), frise, correction),
        quantites, echeances, suivi),
      h('div', {className: 'm-pied'}, liens, h('button', {type: 'button', className: 'btn', onClick: fermer}, 'Fermer')));
    var voile = h('div', {className: 'adv-voile', onClick: function (ev) { if (ev.target === voile) fermerFiche(); }}, modal);
    m.appendChild(voile);
    if (S.focusInfo) {
      S.focusInfo = false;
      if (champInfo) requestAnimationFrame(function () { champInfo.focus(); });
      else carteInfos.scrollIntoView({block: 'nearest'});
    }
  }
  document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape' && modalOuverte()) fermerFiche(); });

  /* ── Démarrage ──────────────────────────────────────────────── */

  document.querySelectorAll('#adv-nav .nav-btn[data-onglet]').forEach(function (b) {
    b.addEventListener('click', async function () {
      var o = b.getAttribute('data-onglet');
      if (ONGLETS.indexOf(o) === -1) return;
      fermerFiche(true);
      S.onglet = o; S.ligne = null; S.sous = null;
      if (!donnees()) { S.charge = false; render(); await charger(); }
      render();
      if (document.body.classList.contains('sb-open') && window.closeSidebar) window.closeSidebar();
    });
  });

  MySifaUrl.surRetour(async function () {
    var avant = S.onglet, hz = S.horizon;
    lireUrl(true);
    var histo = S.onglet === 'prepa' && S.sous === 'historique';
    if (histo ? !S.historique || S.historique.jours !== S.histoJours
      : (S.onglet !== avant || !donnees() || (S.onglet === 'prepa' && hz !== S.horizon))) { await charger(); }
    if (!S.ligne && !S.reglages && !S.ordreExpe) fermerFiche(true);
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

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
  var LIB_PREPA = {};
  (BOOT.statuts_prepa || []).forEach(function (e) { LIB_PREPA[e.cle] = e.label; });

  var ONGLETS = DROITS.adv ? ['commandes', 'prepa'] : ['prepa'];
  var FILTRES = ['tous', 'retard', 'semaine', 'pretes'].concat(ETAPES.map(function (e) { return 'etape_' + e.cle; }));
  var TRIS = ['commande', 'client', 'article', 'reste', 'expedition', 'livraison', 'fin_prod'];
  var HORIZONS = [7, 14, 21, 30];
  var GROUPES = ['tous', 'preparable', 'en_cours', 'partiel', 'attente', 'pretes'];

  var S = {
    onglet: ONGLETS[0],
    filtre: 'tous',
    tri: 'expedition',
    sens: 'asc',
    q: '',
    ligne: null,                 // clé « numero-ligne » de la fiche ouverte
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
    return d.length === 3 ? d[2] + '/' + d[1] : String(s);
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
    MySifaUrl.ecrire(p, {navigation: S.onglet + (S.ligne ? ':fiche' : '')});
  }

  /* ── Données ────────────────────────────────────────────────── */

  async function charger() {
    S.erreur = null;
    try {
      if (S.onglet === 'commandes') S.carnet = await api('/api/adv/commandes');
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
    ecrireUrl();
    if (S.ligne && !modalOuverte()) ouvrirFiche(S.ligne, true);
    if (!S.ligne && modalOuverte()) fermerFiche(true);
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

  function pastille(l, cle) {
    var e = l.etapes[cle];
    var lib = ETAPES.find(function (x) { return x.cle === cle; });
    var v = e.valeur;
    var txt = v === 'sans_objet' ? '—' : (ETATS[v] || v);
    var note = null;
    if (e.force) {
      note = 'Fixé à la main' + (e.force_par ? ' par ' + e.force_par : '') + (e.force_le ? ' le ' + dateLongue(e.force_le) : '')
        + (e.force_note ? ' · ' + e.force_note : '') + ' · calcul : ' + (ETATS[e.calcul] || e.calcul);
    }
    return h('span', {className: 'adv-etat ' + v + (e.force ? ' force' : ''),
      'data-tip': tip(l.cle + '|' + cle, (lib ? lib.label : cle) + ' · ' + (ETATS[v] || v), e.detail, note)}, txt);
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
        var v = l.etapes[k].valeur; return v === 'oui' || v === 'sans_objet';
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
      case 'reste': return l.reste;
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
        h('div', {className: 'adv-maj', text: 'Lignes à traiter dans RVGI · stock MyStock · actualisé à ' + new Date().toLocaleTimeString('fr-FR', {hour: '2-digit', minute: '2-digit'})})),
      h('button', {type: 'button', className: 'btn', onClick: async function () { await charger(); render(); toast('Carnet actualisé.'); }}, 'Actualiser'));
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
  function renderTableSeule() {
    var hote = document.getElementById('adv-table-hote');
    if (!hote) return;
    var y = (hote.querySelector('.adv-table-wrap') || {}).scrollTop || 0;
    hote.textContent = '';
    var d = S.carnet || {};
    var lignes = trier(filtrer(d.lignes || []));
    if (!lignes.length) {
      hote.appendChild(h('div', {className: 'adv-vide', text: S.q ? 'Aucun résultat pour « ' + S.q + ' »' : 'Aucune ligne pour ce filtre.'}));
      return;
    }
    var th = function (lib, cle, cls) {
      var actif = S.tri === cle;
      return h('th', {className: (cls || '') + (cle ? ' triable' : '') + (actif ? ' trie' : ''),
        onClick: cle ? function () {
          if (S.tri !== cle) { S.tri = cle; S.sens = 'asc'; }
          else if (S.sens === 'asc') S.sens = 'desc';
          else { S.tri = 'expedition'; S.sens = 'asc'; }
          renderTableSeule(); ecrireUrl();
        } : null}, lib + (actif ? (S.sens === 'asc' ? ' ↑' : ' ↓') : ''));
    };
    var thead = h('thead', {}, h('tr', {},
      th('Commande', 'commande'), th('Client', 'client'), th('Article', 'article'),
      th('Reste', 'reste', 'num'), th('Expédition', 'expedition'), th('Livraison', 'livraison'), th('Fin de prod', 'fin_prod'),
      ETAPES.map(function (e, i) { return th(e.label, null, 'etape' + (i === 0 ? ' sep' : '')); })));
    var tbody = h('tbody');
    lignes.forEach(function (l) {
      var finTard = l.fin_prod && l.expedition && String(l.fin_prod).slice(0, 10) > l.expedition;
      var finTxt = l.fin_prod ? dateFr(l.fin_prod) : '';
      tbody.appendChild(h('tr', {onClick: function () { ouvrirFiche(l.cle); }},
        h('td', {className: 'adv-mono'}, l.numero, h('span', {className: 'adv-muet', text: ' · ' + l.ligne})),
        h('td', {className: 'client', text: l.client}),
        h('td', {className: 'des', 'data-tip': tip(l.cle + '|des', l.article, l.designation, libOrigine(l.origine) + (l.ref_client ? ' · réf. client ' + l.ref_client : ''))},
          h('div', {className: 'adv-mono', text: l.article}), h('div', {className: 'des-l', text: l.designation})),
        h('td', {className: 'num'}, fN(l.reste), unite(l) ? h('span', {className: 'adv-muet', text: ' ' + unite(l)}) : null),
        h('td', {className: l.retard ? 'adv-date-retard' : '', text: dateFr(l.expedition) || '—'}),
        h('td', {text: dateFr(l.livraison) || '—'}),
        h('td', {className: finTard ? 'adv-date-tard' : (l.fin_prod ? '' : 'adv-muet'),
          'data-tip': l.fin_prod ? tip(l.cle + '|fin', l.fin_prod_reelle ? 'Fin de production saisie' : 'Fin de production planifiée',
            dateLongue(l.fin_prod) + (heure(l.fin_prod) ? ' à ' + heure(l.fin_prod) : ''),
            finTard ? 'Après la date d’expédition' : null) : null,
          text: finTxt || '—'}),
        ETAPES.map(function (e, i) { return h('td', {className: 'etape' + (i === 0 ? ' sep' : '')}, pastille(l, e.cle)); })));
    });
    var wrap = h('div', {className: 'adv-table-wrap'}, h('table', {className: 'adv-table'}, thead, tbody));
    hote.appendChild(wrap);
    if (y) wrap.scrollTop = y;
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
    if (s === 'prete') return [b('Remettre à préparer', 'a_preparer')];
    if (s === 'en_cours') return [b('Prête', 'prete', 'btn-ok'), b('Remettre à préparer', 'a_preparer')];
    return [b('Démarrer', 'en_cours', 'btn-accent'), b('Prête', 'prete')];
  }

  function cartePrepa(l, rang) {
    var st = l.stock || {};
    var u = unite(l) ? ' ' + unite(l) : '';
    var badges = [];
    if (l.retard) badges.push(h('span', {className: 'adv-badge danger', text: 'En retard'}));
    badges.push(h('span', {className: 'adv-badge', text: 'Expédition ' + (dateLongue(l.expedition) || 'non datée')}));
    if (l.departs && l.departs.length) {
      var dp = l.departs[0];
      badges.push(h('span', {className: 'adv-badge ok', text: 'Enlèvement ' + dateLongue(dp.date_enlevement) + (dp.transporteur ? ' · ' + dp.transporteur : '')}));
    }
    if (l.prepa.statut !== 'a_preparer' && l.prepa.maj_par) {
      badges.push(h('span', {className: 'adv-badge', text: (LIB_PREPA[l.prepa.statut] || '') + ' · ' + l.prepa.maj_par + ' ' + dateFr(l.prepa.maj_le) + ' ' + heure(l.prepa.maj_le)}));
    }
    var qte;
    if (l.groupe === 'attente') {
      qte = h('div', {className: 'c-qte'}, 'À produire : ' + fN(l.reste) + u,
        l.fin_prod ? h('span', {className: 'adv-muet', text: ' · fin de prod ' + dateLongue(l.fin_prod) + (heure(l.fin_prod) ? ' ' + heure(l.fin_prod) : '')}) : h('span', {className: 'adv-muet', text: ' · ' + l.etapes.prod.detail.toLowerCase()}));
    } else {
      qte = h('div', {className: 'c-qte'}, 'À préparer : ' + fN(l.reste) + u,
        st.alloue < l.reste ? h('span', {className: 'adv-date-tard', text: ' · ' + fN(st.alloue) + u + ' en stock'}) : null);
    }
    var empl = null;
    if (st.emplacements && st.emplacements.length && l.groupe !== 'attente') {
      empl = h('div', {className: 'adv-empl'}, st.emplacements.map(function (e) {
        return h('span', {'data-tip': tip(l.cle + '|lot' + e.lot_id, 'Emplacement ' + e.emplacement, 'Prélever ' + fN(e.quantite) + u, e.date_entree ? 'Entré le ' + dateLongue(e.date_entree) + ' (FIFO)' : null)},
          h('b', {text: e.emplacement}), ' · ' + fN(e.quantite));
      }));
    }
    return h('div', {className: 'adv-carte' + (l.retard ? ' retard' : ''), onClick: function () { ouvrirFiche(l.cle); }, style: 'cursor:pointer'},
      h('div', {className: 'adv-rang', text: String(rang)}),
      h('div', {},
        h('div', {className: 'c-haut'}, h('span', {className: 'c-client', text: l.client}),
          h('span', {className: 'adv-mono adv-muet', text: l.numero + ' · ' + l.ligne + ' · ' + l.article})),
        h('div', {className: 'c-des', text: l.designation}),
        qte, empl,
        h('div', {className: 'adv-empl'}, badges)),
      h('div', {className: 'adv-actions'}, boutonsPrepa(l)));
  }

  function renderPrepa(c) {
    var d = S.prepa || {};
    var tete = h('div', {className: 'adv-tete'},
      h('div', {}, h('h1', {text: 'Préparations'}),
        h('div', {className: 'adv-maj', text: 'Par date d’expédition, retards en tête · emplacements MyStock en FIFO'})),
      h('div', {className: 'adv-puces'}, HORIZONS.map(function (n) {
        return h('button', {type: 'button', className: 'adv-puce' + (S.horizon === n ? ' active' : ''),
          onClick: async function () { S.horizon = n; S.charge = false; render(); await charger(); render(); }}, n + ' jours');
      }), h('button', {type: 'button', className: 'btn btn-petit', onClick: async function () { await charger(); render(); toast('Préparations actualisées.'); }}, 'Actualiser')));
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
      tuile('À préparer', n('preparable'), 'stock disponible', n('preparable') ? 'warn' : '', S.groupe === 'preparable', basculer('preparable')),
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
      var bloc = h('div', {className: 'adv-groupe'}, h('h2', {}, g.label, h('span', {className: 'n', text: String(ls.length)})));
      ls.forEach(function (l) { bloc.appendChild(cartePrepa(l, rangs[l.cle] || '·')); });
      c.appendChild(bloc);
    });
  }

  /* ── Fiche d'une ligne ──────────────────────────────────────── */

  function fermerFiche(sansAdresse) {
    var m = document.getElementById('mroot');
    if (m) m.textContent = '';
    cacherTip();
    if (sansAdresse === true) return;
    S.ligne = null;
    ecrireUrl();
  }

  async function forcer(l, etape, valeur, note) {
    try {
      await api('/api/adv/forcage/' + encodeURIComponent(l.numero) + '/' + l.ligne + '/' + etape,
        {method: 'PUT', body: {valeur: valeur || null, note: note || null}});
      toast(valeur ? 'Étape fixée.' : 'Calcul rétabli.');
      await charger();
      if (S.onglet === 'prepa') S.carnet = null; else S.prepa = null;
      render();
      fermerFiche(true);
      ouvrirFiche(l.cle, true);
    } catch (e) { toast(e.message, 'danger'); }
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
    if (!sansAdresse) { S.ligne = cle; ecrireUrl(); }
    else S.ligne = cle;
    var st = l.stock || {};
    var u = unite(l) ? ' ' + unite(l) : '';
    var g = function (lib, val) { return h('div', {}, h('div', {className: 'g-l', text: lib}), h('div', {className: 'g-v', text: val || '—'})); };

    var etapes = h('div', {});
    ETAPES.forEach(function (e) {
      var et = l.etapes[e.cle];
      var det = h('div', {className: 'e-det', text: et.detail});
      if (et.force) det.appendChild(h('span', {className: 'e-force',
        text: 'Fixé à la main' + (et.force_par ? ' par ' + et.force_par : '') + (et.force_le ? ' le ' + dateLongue(et.force_le) : '') + (et.force_note ? ' · ' + et.force_note : '')}));
      var zone = h('div');
      // La prépa se règle par ses boutons (c'est la logistique qui la tient) ;
      // les autres étapes peuvent être fixées par l'ADV, avec un motif.
      if (DROITS.adv && e.cle !== 'prepa') {
        var sel = h('select', {'aria-label': 'Fixer l’étape ' + e.label});
        var motif = h('input', {type: 'text', placeholder: 'Motif (facultatif)', value: et.force_note || '',
          style: 'margin-top:6px', 'aria-label': 'Motif pour l’étape ' + e.label});
        sel.addEventListener('change', function () { forcer(l, e.cle, sel.value, sel.value ? motif.value : ''); });
        motif.addEventListener('change', function () { if (sel.value) forcer(l, e.cle, sel.value, motif.value); });
        sel.appendChild(h('option', {value: ''}, 'Calcul : ' + (ETATS[et.calcul] || et.calcul)));
        Object.keys(ETATS).forEach(function (k) {
          var o = h('option', {value: k}, 'Fixer : ' + ETATS[k]);
          if (et.force && et.valeur === k) o.selected = true;
          sel.appendChild(o);
        });
        ajouter(zone, [sel, motif]);
      }
      etapes.appendChild(h('div', {className: 'adv-etape-ligne'},
        h('div', {className: 'e-lib', text: e.label}), h('div', {}, pastille(l, e.cle)), det, zone));
    });

    var dossiers = h('div', {className: 'adv-liste'});
    if (!l.dossiers.length) dossiers.appendChild(h('div', {className: 'adv-muet', text: 'Aucun dossier au planning pour cette ligne.'}));
    l.dossiers.forEach(function (d) {
      dossiers.appendChild(h('div', {},
        h('a', {href: '/planning?dossier=' + d.id, text: d.reference || ('Dossier ' + d.id)}),
        h('span', {className: 'adv-muet', text: ' · ' + ({attente: 'En attente', en_cours: 'En cours', termine: 'Terminé'}[d.statut] || d.statut || '')
          + (d.machine ? ' · ' + d.machine : '') + (d.fin ? ' · fin ' + (d.fin_reelle ? 'saisie ' : 'prévue ') + dateLongue(d.fin) + (heure(d.fin) ? ' ' + heure(d.fin) : '') : '')})));
    });

    var departs = h('div', {className: 'adv-liste'});
    if (!l.departs.length) departs.appendChild(h('div', {className: 'adv-muet', text: 'Aucun départ MyExpé rattaché.'}));
    l.departs.forEach(function (d) {
      departs.appendChild(h('div', {},
        h('a', {href: '/expe?depart=' + d.id, text: 'Départ du ' + dateLongue(d.date_enlevement)}),
        h('span', {className: 'adv-muet', text: (d.transporteur ? ' · ' + d.transporteur : '') + (d.parti_le ? ' · parti' : d.statut === 'valide' ? ' · validé' : ' · à valider') + (d.no_bl ? ' · BL ' + d.no_bl : '')})));
    });

    var stock = h('div', {className: 'adv-liste'});
    if (!st.connu) stock.appendChild(h('div', {className: 'adv-muet', text: 'Article absent de MyStock.'}));
    else {
      stock.appendChild(h('div', {text: 'En stock : ' + fN(st.total) + u + ' · attribué à cette ligne : ' + fN(st.alloue) + u}));
      if (st.emplacements && st.emplacements.length) {
        stock.appendChild(h('div', {className: 'adv-empl'}, st.emplacements.map(function (e) {
          return h('span', {}, h('b', {text: e.emplacement}), ' · ' + fN(e.quantite) + (e.date_entree ? ' · ' + dateFr(e.date_entree) : ''));
        })));
      }
    }

    var prepaZone = h('div', {className: 'adv-rangee', style: 'display:flex;gap:8px;flex-wrap:wrap;align-items:center'},
      h('span', {className: 'adv-badge', text: LIB_PREPA[l.prepa.statut] || l.prepa.statut}),
      l.prepa.maj_par ? h('span', {className: 'adv-muet', text: l.prepa.maj_par + ' · ' + dateLongue(l.prepa.maj_le) + ' ' + heure(l.prepa.maj_le)}) : null,
      boutonsPrepa(l));

    var liens = h('div', {className: 'adv-liens'},
      DROITS.adv ? h('a', {className: 'btn btn-petit', href: '/erp#/commandes?q=' + encodeURIComponent(l.numero)}, 'Commande dans l’ERP') : null,
      st.connu ? h('a', {className: 'btn btn-petit', href: '/stock?ref=' + encodeURIComponent(l.article)}, 'Article dans MyStock') : null);

    var modal = h('div', {className: 'adv-modal', role: 'dialog', 'aria-modal': 'true'},
      h('h3', {text: l.client + ' — ' + l.numero + ' · ligne ' + l.ligne}),
      h('div', {className: 'm-sous', text: l.article + ' · ' + l.designation}),
      h('h4', {text: 'Commande'}),
      h('div', {className: 'adv-grille'},
        g('Reste à livrer', fN(l.reste) + u), g('Commandé', fN(l.qte)), g('Déjà livré', fN(l.livre)),
        g('Besoin RVGI (qtep)', fN(l.besoin_rvgi)), g('Origine', libOrigine(l.origine)),
        g('Expédition', dateLongue(l.expedition)), g('Livraison', dateLongue(l.livraison)),
        g('Fin de prod', l.fin_prod ? dateLongue(l.fin_prod) + (heure(l.fin_prod) ? ' ' + heure(l.fin_prod) : '') + (l.fin_prod_reelle ? ' (saisie)' : ' (prévue)') : ''),
        g('Réf. client', l.ref_client), g('Créée le', dateLongue(l.creee_le))),
      h('h4', {text: 'Chaîne de valeur'}), etapes,
      h('h4', {text: 'Préparation'}), prepaZone,
      h('h4', {text: 'Stock MyStock'}), stock,
      h('h4', {text: 'Dossiers de production'}), dossiers,
      h('h4', {text: 'Départs'}), departs,
      h('div', {className: 'm-pied'}, liens, h('button', {type: 'button', className: 'btn', onClick: function () { fermerFiche(); }}, 'Fermer')));
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
    if (!S.ligne) fermerFiche(true);
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

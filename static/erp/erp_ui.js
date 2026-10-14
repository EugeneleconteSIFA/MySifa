/* Nouvel ERP — composants communs : formats, champs, autocomplétion,
 * fenêtres, cartes, pastilles d'état.
 *
 * Formats : en base tout est entier (centimes, millièmes, points de base).
 * Ces fonctions sont les seules à convertir saisie ↔ entier : un écran ne
 * fait jamais `* 100` lui-même.
 */
(function () {
  'use strict';
  var ERP = window.ERP, h = ERP.h;

  // ── Formats ──────────────────────────────────────────────────────
  var NF = {};
  function nf(dec) {
    var k = dec[0] + '-' + dec[1];
    return NF[k] || (NF[k] = new Intl.NumberFormat('fr-FR', {minimumFractionDigits: dec[0], maximumFractionDigits: dec[1]}));
  }
  function nombre(s) {
    if (s == null) return NaN;
    var t = String(s).replace(/[\s  €%]/g, '').replace(',', '.');
    return t === '' ? NaN : Number(t);
  }
  ERP.fmt = Object.assign(ERP.fmt || {}, {
    euros: function (c) { return c == null ? '' : nf([2, 2]).format(c / 100) + ' €'; },
    eurosNu: function (c) { return c == null ? '' : nf([2, 2]).format(c / 100); },
    qte: function (m, dec) { return m == null ? '' : nf([0, dec == null ? 3 : dec]).format(m / 1000); },
    pct: function (bp) { return bp ? nf([0, 2]).format(bp / 100) + ' %' : ''; },
    date: function (s) { return s ? String(s).slice(8, 10) + '/' + String(s).slice(5, 7) + '/' + String(s).slice(0, 4) : ''; },
  });
  ERP.lire = {
    euros: function (s) { var n = nombre(s); return isNaN(n) ? null : Math.round(n * 100); },
    qte: function (s) { var n = nombre(s); return isNaN(n) ? null : Math.round(n * 1000); },
    pct: function (s) { var n = nombre(s); return isNaN(n) ? 0 : Math.round(n * 100); },
    entier: function (s) { var n = nombre(s); return isNaN(n) ? null : Math.round(n); },
  };

  // Montant de ligne et totaux : copie conforme de app/services/gc/calculs.py.
  function divArrondi(num, den) {
    var s = num < 0 ? -1 : 1, n = Math.abs(num);
    return s * Math.floor((2 * n + den) / (2 * den));
  }
  ERP.calc = {
    montantLigne: function (qMilli, prixCents, base, remiseBp) {
      return divArrondi((qMilli || 0) * (prixCents || 0) * (10000 - (remiseBp || 0)), 1000 * Math.max(1, base || 1) * 10000);
    },
    totaux: function (lignes, remisePieceBp) {
      var par = {};
      lignes.forEach(function (l) {
        if (!l.article_id) return;
        var t = l.taux_tva_bp || 0;
        par[t] = (par[t] || 0) + (l.montant_ht_cents || 0);
      });
      var out = {ht: 0, tva: 0, ttc: 0, remise: 0, bases: []};
      Object.keys(par).map(Number).sort(function (a, b) { return a - b; }).forEach(function (t) {
        var brut = par[t], r = divArrondi(brut * (remisePieceBp || 0), 10000), net = brut - r, tv = divArrondi(net * t, 10000);
        out.bases.push({taux_bp: t, ht_brut: brut, remise: r, ht: net, tva: tv});
        out.ht += net; out.tva += tv; out.remise += r;
      });
      out.ttc = out.ht + out.tva;
      return out;
    },
  };

  // ── Méta (référentiels, types) : chargée une fois, rechargeable ──
  var metaP = null;
  ERP.meta = function (forcer) {
    if (!metaP || forcer) {
      metaP = ERP.api('/api/erp2/meta').then(function (m) { ERP.M = m; ERP.types = m.types; return m; });
      metaP.catch(function () { metaP = null; });
    }
    return metaP;
  };
  ERP.ref = function (nom, actifsSeuls) {
    var l = ((ERP.M || {}).referentiels || {})[nom] || [];
    return actifsSeuls ? l.filter(function (x) { return x.actif !== 0; }) : l;
  };
  ERP.refLibelle = function (nom, code) {
    var x = ERP.ref(nom).filter(function (r) { return r.code === code; })[0];
    return x ? x.libelle : (code || '');
  };

  // ── États des pièces ─────────────────────────────────────────────
  var ETATS = {
    brouillon: {l: 'Brouillon', ton: 'neutre'},
    valide: {l: 'Validé', ton: 'accent'},
    partiel: {l: 'Partiel', ton: 'warn'},
    solde: {l: 'Soldé', ton: 'ok'},
    annule: {l: 'Annulé', ton: 'danger'},
  };
  var ETATS_TYPE = {
    devis: {valide: 'Envoyé', partiel: 'Accepté en partie', solde: 'Accepté'},
    marche: {valide: 'En cours', partiel: 'Appelé en partie', solde: 'Épuisé'},
    commande: {valide: 'À livrer', partiel: 'Livrée en partie', solde: 'Livrée'},
    bl: {valide: 'À facturer', partiel: 'Facturé en partie', solde: 'Facturé'},
    facture: {valide: 'Émise', partiel: 'Réglée en partie', solde: 'Réglée'},
    avoir: {valide: 'Émis'},
    cde_fournisseur: {valide: 'À recevoir', partiel: 'Reçue en partie', solde: 'Reçue'},
    reception: {valide: 'À facturer', partiel: 'Facturée en partie', solde: 'Facturée'},
    facture_fournisseur: {valide: 'À payer', partiel: 'Payée en partie', solde: 'Payée'},
    of: {valide: 'Lancé', partiel: 'En production', solde: 'Terminé'},
  };
  ERP.etat = function (type, statut) {
    var e = ETATS[statut] || {l: statut, ton: 'neutre'};
    return {libelle: (ETATS_TYPE[type] || {})[statut] || e.l, ton: e.ton};
  };
  ERP.statutsPour = function (types) {
    var out = {};
    Object.keys(ETATS).forEach(function (s) { out[s] = ERP.etat(types[0], s); });
    return out;
  };
  ERP.pastille = function (type, statut) {
    var e = ERP.etat(type, statut);
    return h('span', {className: 'erp-pastille ton-' + e.ton, text: e.libelle});
  };

  // ── Champs ───────────────────────────────────────────────────────
  // champ('Libellé', element, {large: true, aide: '…'})
  ERP.champ = function (libelle, el, o) {
    o = o || {};
    if (el && el.id == null) el.id = '';
    var id = 'c' + Math.random().toString(36).slice(2, 9);
    if (el && !el.id) el.id = id;
    return h('div', {className: 'erp-champ' + (o.large ? ' large' : '') + (o.plein ? ' plein' : '')},
      h('label', {className: 'erp-label', for: el && el.id, text: libelle}), el,
      o.aide ? h('div', {className: 'erp-aide', text: o.aide}) : null);
  };

  // Champ lié à obj[cle]. type : texte | euros | qte | pct | date | entier | zone
  ERP.saisie = function (obj, cle, type, o) {
    o = o || {};
    var lecture = !!o.lecture;
    var val = obj[cle];
    var aff = type === 'euros' ? ERP.fmt.eurosNu(val) : type === 'qte' ? ERP.fmt.qte(val, o.dec) :
              type === 'pct' ? (val ? String(val / 100).replace('.', ',') + (lecture ? ' %' : '') : '') : (val == null ? '' : String(val));
    var el = type === 'zone' ? h('textarea', {className: 'erp-input', rows: o.lignes || 3, disabled: lecture})
                             : h('input', {className: 'erp-input' + (/euros|qte|pct|entier/.test(type) ? ' num' : ''),
                                           type: type === 'date' ? 'date' : 'text', disabled: lecture,
                                           placeholder: lecture ? '' : (o.placeholder || ''), inputmode: /euros|qte|pct|entier/.test(type) ? 'decimal' : null});
    el.value = aff;
    el.addEventListener('change', function () {
      var v = el.value;
      var n = type === 'euros' ? ERP.lire.euros(v) : type === 'qte' ? ERP.lire.qte(v) :
              type === 'pct' ? ERP.lire.pct(v) : type === 'entier' ? ERP.lire.entier(v) : v;
      if (/euros|qte|entier/.test(type) && v.trim() !== '' && n == null) {
        el.classList.add('erreur');
        ERP.toast('Nombre invalide : « ' + v + ' ».', 'danger');
        return;
      }
      el.classList.remove('erreur');
      obj[cle] = n;
      if (type === 'euros') el.value = ERP.fmt.eurosNu(n);
      if (type === 'qte') el.value = ERP.fmt.qte(n, o.dec);
      if (o.change) o.change(n);
    });
    return el;
  };

  // Liste déroulante. options : [{v, l}] ; avecVide : libellé de l'option vide.
  ERP.choix = function (obj, cle, options, o) {
    o = o || {};
    var el = h('select', {className: 'erp-input', disabled: !!o.lecture});
    if (o.avecVide != null) el.appendChild(h('option', {value: '', text: o.avecVide}));
    options.forEach(function (x) { el.appendChild(h('option', {value: String(x.v), text: x.l})); });
    el.value = obj[cle] == null ? '' : String(obj[cle]);
    el.addEventListener('change', function () {
      var v = el.value === '' ? null : el.value;
      obj[cle] = o.nombre && v != null ? Number(v) : v;
      if (o.change) o.change(obj[cle]);
    });
    return el;
  };
  ERP.optionsRef = function (nom) {
    return ERP.ref(nom, true).map(function (r) { return {v: r.code, l: r.libelle}; });
  };

  ERP.case = function (obj, cle, libelle, o) {
    o = o || {};
    var c = h('input', {type: 'checkbox', checked: !!obj[cle], disabled: !!o.lecture});
    c.addEventListener('change', function () { obj[cle] = c.checked ? 1 : 0; if (o.change) o.change(obj[cle]); });
    return h('label', {className: 'erp-case'}, c, h('span', {text: libelle}));
  };

  // ── Autocomplétion ───────────────────────────────────────────────
  // source(q) -> [{titre, sous, valeur}] (synchrone ou promesse)
  ERP.autocomplete = function (input, source, choisir, o) {
    o = o || {};
    var liste = null, items = [], sel = 0, seq = 0;
    function fermer() { if (liste) { liste.remove(); liste = null; } }
    function placer() {
      var r = input.getBoundingClientRect();
      liste.style.left = r.left + 'px';
      liste.style.top = (r.bottom + 2) + 'px';
      liste.style.minWidth = Math.max(r.width, o.largeur || 320) + 'px';
    }
    function dessiner() {
      if (!liste) { liste = h('div', {className: 'erp-ac'}); document.body.appendChild(liste); }
      placer();
      liste.textContent = '';
      if (!items.length) {
        liste.appendChild(h('div', {className: 'erp-ac-vide', text: input.value.trim() ? 'Aucun résultat pour « ' + input.value.trim() + ' »' : 'Tapez pour chercher'}));
        return;
      }
      items.forEach(function (it, i) {
        liste.appendChild(h('div', {className: 'erp-ac-item' + (i === sel ? ' sel' : ''),
          onmousedown: function (e) { e.preventDefault(); prendre(i); }},
          h('b', {text: it.titre}), it.sous ? h('span', {text: it.sous}) : null));
      });
    }
    function prendre(i) {
      var it = items[i];
      fermer();
      if (it) choisir(it.valeur, it);
    }
    async function chercher() {
      var n = ++seq;
      var r = await source(input.value.trim());
      if (n !== seq) return;
      items = (r || []).slice(0, o.max || 12);
      sel = 0;
      dessiner();
    }
    input.setAttribute('autocomplete', 'off');
    input.addEventListener('input', chercher);
    input.addEventListener('focus', function () { if (o.ouvrirAuFocus) chercher(); });
    input.addEventListener('blur', function () { setTimeout(fermer, 120); });
    input.addEventListener('keydown', function (e) {
      if (!liste) {
        if (e.key === 'ArrowDown') { e.preventDefault(); chercher(); }
        return;
      }
      if (e.key === 'ArrowDown') { e.preventDefault(); sel = Math.min(items.length - 1, sel + 1); dessiner(); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); sel = Math.max(0, sel - 1); dessiner(); }
      else if (e.key === 'Enter' || e.key === 'Tab') {
        if (items[sel] && input.value.trim()) { e.preventDefault(); e.stopPropagation(); prendre(sel); }
        else fermer();
      } else if (e.key === 'Escape') { e.stopPropagation(); fermer(); }
    });
    window.addEventListener('scroll', function () { if (liste) placer(); }, true);
    return {fermer: fermer};
  };

  // Filtre local insensible aux accents, sur plusieurs champs.
  function sansAccents(s) { return String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase(); }
  ERP.filtrer = function (liste, q, champs) {
    var n = sansAccents(q);
    if (!n) return liste;
    var mots = n.split(/\s+/);
    return liste.filter(function (x) {
      var t = sansAccents(champs.map(function (c) { return x[c]; }).join(' '));
      return mots.every(function (m) { return t.indexOf(m) >= 0; });
    });
  };

  // ── Fenêtres ─────────────────────────────────────────────────────
  // modal(titre, contenu, [{libelle, accent, danger, action}]) ; action() peut
  // renvoyer false (ou une promesse de false) pour garder la fenêtre ouverte.
  ERP.modal = function (titre, contenu, boutons, o) {
    o = o || {};
    var fond, corps = h('div', {className: 'erp-modal-corps'}, contenu);
    var pied = h('div', {className: 'erp-modal-pied'});
    function fermer() { fond.remove(); document.removeEventListener('keydown', echap, true); if (o.fermeture) o.fermeture(); }
    // Échap ferme d'abord une liste de suggestions ouverte, pas la fenêtre.
    function echap(e) { if (e.key === 'Escape' && !document.querySelector('.erp-ac')) { e.preventDefault(); e.stopPropagation(); fermer(); } }
    (boutons || [{libelle: 'Fermer'}]).forEach(function (b) {
      var btn = h('button', {type: 'button', className: 'erp-btn' + (b.accent ? ' erp-btn-accent' : '') + (b.danger ? ' erp-btn-danger' : ''),
        text: b.libelle});
      btn.addEventListener('click', async function () {
        if (!b.action) { fermer(); return; }
        btn.disabled = true;
        try {
          var r = await b.action();
          if (r !== false) fermer();
        } catch (e) { ERP.toast(e.message, 'danger'); }
        btn.disabled = false;
      });
      pied.appendChild(btn);
    });
    fond = h('div', {className: 'erp-modal-fond', onmousedown: function (e) { if (e.target === fond && !o.bloquante) fermer(); }},
      h('div', {className: 'erp-modal' + (o.large ? ' large' : ''), role: 'dialog', 'aria-modal': 'true'},
        h('div', {className: 'erp-modal-titre', text: titre}), corps, pied));
    document.addEventListener('keydown', echap, true);
    document.body.appendChild(fond);
    requestAnimationFrame(function () {
      var f = corps.querySelector('input,select,textarea') || pied.querySelector('.erp-btn-accent');
      if (f) f.focus();
    });
    return {fermer: fermer};
  };

  ERP.confirmer = function (message, o) {
    o = o || {};
    return new Promise(function (resoudre) {
      var fait = false;
      ERP.modal(o.titre || 'Confirmer', h('p', {className: 'erp-modal-texte', text: message}), [
        {libelle: 'Annuler', action: function () { fait = true; resoudre(false); }},
        {libelle: o.ok || 'Confirmer', accent: !o.danger, danger: !!o.danger, action: function () { fait = true; resoudre(true); }},
      ], {fermeture: function () { if (!fait) resoudre(false); }});
    });
  };

  // ── Mise en page ─────────────────────────────────────────────────
  ERP.carte = function (titre, contenu, actions) {
    return h('section', {className: 'erp-carte'},
      titre || actions ? h('div', {className: 'erp-carte-tete'}, h('h2', {text: titre || ''}),
        actions ? h('div', {className: 'erp-carte-actions'}, actions) : null) : null,
      h('div', {className: 'erp-carte-corps'}, contenu));
  };
  ERP.bouton = function (libelle, action, o) {
    o = o || {};
    var b = h('button', {type: 'button', title: o.titre || null,
      className: 'erp-btn' + (o.accent ? ' erp-btn-accent' : '') + (o.danger ? ' erp-btn-danger' : '') + (o.petit ? ' erp-btn-petit' : '')},
      libelle);
    b.addEventListener('click', async function () {
      if (b.disabled) return;
      b.disabled = true;
      try { await action(); } catch (e) { ERP.toast(e.message, 'danger'); }
      b.disabled = false;
    });
    return b;
  };
  ERP.chargement = function () { return h('div', {className: 'erp-chargement', text: 'Chargement…'}); };
  ERP.erreur = function (e) { return h('div', {className: 'erp-vide erreur', text: e.message || String(e)}); };
  ERP.lien = function (texte, chemin) {
    return h('a', {href: chemin, className: 'erp-lien', text: texte, onclick: function (e) { e.preventDefault(); ERP.aller(chemin); }});
  };
})();

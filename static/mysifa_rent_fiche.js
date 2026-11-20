/* MySifa — fiche rentabilité d'un dossier (devisé contre réel).
 *
 * Montée dans la fenêtre du dossier du Pilotage de Rentabilité, sous le
 * devis rattaché. Tout le calcul est côté serveur
 * (`GET /api/rentabilite/planning/{id}/fiche`, service
 * `app/services/rentabilite_reel.py`) : ce fichier ne fait que dessiner.
 *
 * Ce qu'il faut lire d'abord, dans l'ordre : le verdict, les paramètres qui
 * ont changé par rapport au devis, puis les deux jauges (marge brute, coût
 * horaire). Les jauges montrent une FOURCHETTE et non un point : les saisies
 * sont manuelles, le verdict ne tombe que quand toute la fourchette est du
 * même côté du seuil.
 *
 * Aucune donnée n'entre par innerHTML : tout passe par textContent.
 * API : MySifaRentFiche.monter(conteneur, planningEntryId)
 */
(function () {
  'use strict';

  var SVGNS = 'http://www.w3.org/2000/svg';

  function el(tag, cls, txt) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (txt != null) e.textContent = String(txt);
    return e;
  }
  function svg(tag, attrs) {
    var e = document.createElementNS(SVGNS, tag);
    Object.keys(attrs || {}).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    return e;
  }
  function nb(v, dec) {
    if (v === null || v === undefined || v === '' || !isFinite(Number(v))) return '—';
    return Number(v).toLocaleString('fr-FR', {
      minimumFractionDigits: dec || 0, maximumFractionDigits: dec || 0
    });
  }
  function signe(v, dec) {
    var n = Number(v);
    return (n > 0 ? '+' : n < 0 ? '−' : '') + nb(Math.abs(n), dec);
  }

  var VERDICT = {
    reussi: {lib: 'Réussi', cls: 'ok'},
    limite: {lib: 'À la limite', cls: 'warn'},
    sous_seuil: {lib: 'Sous le seuil', cls: 'bad'}
  };

  function api(path) {
    var core = window.__prodCore;
    if (core && typeof core.api === 'function') return core.api(path);
    return fetch(path, {credentials: 'same-origin'}).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    });
  }

  // ── Infobulle instantanée, au style du survol du Pilotage ──────────
  // Le détail chiffré (fourchette, devisé, seuil) se lit au survol, pas en
  // sous-texte : le graphique le montre déjà. Même panneau que le survol des
  // blocs du Pilotage (`.rent-tip` de mysifa_prod_core.css : en-tête, lignes
  // libellé / valeur, note) — un seul style d'infobulle dans Rentabilité.
  // Contenu : une chaîne (une note), ou {titre, sous, etat, ton, lignes:[[k, v]], note}.
  var bulle = null;
  function bulleEl() {
    if (bulle && bulle.isConnected) return bulle;
    bulle = el('div', 'rent-tip');
    document.body.appendChild(bulle);
    return bulle;
  }
  function contenuBulle(c) {
    if (typeof c === 'string') c = {note: c};
    var box = el('div', 'rent-tip-in');
    if (c.titre || c.sous || c.etat) {
      var tete = el('div', 'rent-tip-tete');
      if (c.titre) tete.appendChild(el('div', 'rent-tip-cli', c.titre));
      if (c.sous) tete.appendChild(el('div', 'rent-tip-ref', c.sous));
      if (c.etat) tete.appendChild(el('div', 'rent-tip-etat rent-tip-etat-' + (c.ton || 'inconnu'), c.etat));
      box.appendChild(tete);
    }
    var lignes = (c.lignes || []).filter(function (l) { return l && l[1] !== '' && l[1] != null; });
    if (lignes.length) {
      var sec = el('div', c.titre ? 'rent-tip-sec' : '');
      lignes.forEach(function (l) {
        var r = el('div', 'rent-tip-l');
        r.appendChild(el('span', 'rent-tip-k', l[0]));
        r.appendChild(el('span', 'rent-tip-v', l[1]));
        sec.appendChild(r);
      });
      box.appendChild(sec);
    }
    if (c.note) box.appendChild(el('div', (c.titre || lignes.length) ? 'rent-tip-ecart' : 'rent-tip-l', c.note));
    return box;
  }
  function placer(e) {
    if (!bulle) return;
    var marge = 14, r = bulle.getBoundingClientRect();
    var x = e.clientX + marge, y = e.clientY + marge;
    if (x + r.width > window.innerWidth - 8) x = e.clientX - r.width - marge;
    if (y + r.height > window.innerHeight - 8) y = Math.max(8, e.clientY - r.height - marge);
    bulle.style.left = Math.max(8, x) + 'px';
    bulle.style.top = y + 'px';
  }
  function infobulle(cible, contenu) {
    if (!cible || !contenu) return cible;
    cible.addEventListener('mouseenter', function (e) {
      var b = bulleEl();
      b.textContent = '';
      b.appendChild(contenuBulle(contenu));
      b.classList.add('is-on');
      placer(e);
    });
    cible.addEventListener('mousemove', placer);
    cible.addEventListener('mouseleave', function () { if (bulle) bulle.classList.remove('is-on'); });
    return cible;
  }
  // Une fenêtre ou un onglet qui se reconstruit sous la souris ne doit pas
  // laisser le panneau ouvert sur un élément disparu.
  window.addEventListener('scroll', function () { if (bulle) bulle.classList.remove('is-on'); }, true);

  // ── Jauge : fourchette, seuil, devis ───────────────────────────────
  function bornes(vals, pas, plancher) {
    var lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals);
    var marge = Math.max((hi - lo) * 0.25, pas);
    lo = Math.floor((lo - marge) / pas) * pas;
    hi = Math.ceil((hi + marge) / pas) * pas;
    if (plancher !== undefined) lo = Math.max(lo, plancher);
    return [lo, hi];
  }

  function jauge(titre, f, devis, seuil, unite, dec, pas, plancher) {
    var bloc = el('div', 'rf-jauge');
    var pos = f ? (f.bas >= seuil ? 'ok' : (f.haut < seuil ? 'bad' : 'warn')) : 'neutre';
    var tete = el('div', 'rf-jauge-tete');
    tete.appendChild(el('span', 'rf-jauge-titre', titre));
    tete.appendChild(el('span', 'rf-jauge-grand rf-' + pos, f ? nb(f.probable, dec) + ' ' + unite : '—'));
    bloc.appendChild(tete);
    if (!f) return bloc;
    infobulle(bloc, {titre: titre, etat: {ok: 'Au-dessus du seuil', warn: 'À cheval sur le seuil',
        bad: 'Sous le seuil'}[pos], ton: {ok: 'vert', warn: 'orange', bad: 'rouge'}[pos],
      lignes: [['Réel probable', nb(f.probable, dec) + ' ' + unite],
               ['Fourchette', nb(f.bas, dec) + ' – ' + nb(f.haut, dec) + ' ' + unite],
               ['Devisé', devis != null ? nb(devis, dec) + ' ' + unite : ''],
               ['Seuil', nb(seuil, dec) + ' ' + unite]]});
    var vals = [f.bas, f.haut, seuil];
    if (devis != null) vals.push(devis);
    var b = bornes(vals, pas, plancher), lo = b[0], hi = b[1];
    var W = 400, X = function (v) { return 6 + (v - lo) / (hi - lo) * (W - 12); };
    var s = svg('svg', {viewBox: '0 0 ' + W + ' 44', 'class': 'rf-jauge-svg', role: 'img',
      'aria-label': titre + ' : ' + nb(f.bas, dec) + ' à ' + nb(f.haut, dec) + ' ' + unite
        + ', seuil ' + nb(seuil, dec)});
    s.appendChild(svg('rect', {x: 6, y: 12, width: W - 12, height: 12, rx: 6, 'class': 'rf-piste'}));
    var x1 = X(f.bas), x2 = X(f.haut);
    s.appendChild(svg('rect', {x: x1, y: 13, width: Math.max(3, x2 - x1), height: 10, rx: 5,
      'class': 'rf-bande rf-bande-' + pos}));
    s.appendChild(svg('rect', {x: X(f.probable) - 1.5, y: 9, width: 3, height: 18, rx: 1.5,
      'class': 'rf-probable'}));
    s.appendChild(svg('line', {x1: X(seuil), x2: X(seuil), y1: 6, y2: 30, 'class': 'rf-seuil'}));
    if (devis != null) s.appendChild(svg('circle', {cx: X(devis), cy: 18, r: 5, 'class': 'rf-devis'}));
    var ts = svg('text', {x: X(seuil), y: 42, 'class': 'rf-axe rf-axe-seuil', 'text-anchor': 'middle'});
    ts.textContent = nb(seuil, 0);
    s.appendChild(ts);
    bloc.appendChild(s);
    return bloc;
  }

  // ── Cascade : une barre par cause ──────────────────────────────────
  function cascade(titre, etapes, unite, dec) {
    var bloc = el('div', 'rf-cascade');
    bloc.appendChild(el('div', 'rf-sous-titre', titre));
    if (!etapes || !etapes.length) {
      bloc.appendChild(el('div', 'rf-vide', 'Non calculable.'));
      return bloc;
    }
    var maxi = Math.max.apply(null, etapes.filter(function (e) { return e.nature !== 'total'; })
      .map(function (e) { return Math.abs(e.valeur); }).concat([1]));
    etapes.forEach(function (e) {
      var ligne = el('div', 'rf-casc-ligne' + (e.nature === 'total' ? ' rf-casc-total' : ''));
      ligne.appendChild(el('span', 'rf-casc-cause', e.cause));
      var piste = el('span', 'rf-casc-piste');
      if (e.nature !== 'total') {
        var barre = el('span', 'rf-casc-barre rf-nat-' + (e.valeur >= 0 ? 'gain' : e.nature));
        barre.style.width = Math.max(2, Math.abs(e.valeur) / maxi * 100) + '%';
        piste.appendChild(barre);
      }
      ligne.appendChild(piste);
      var txt = e.nature === 'total' ? nb(e.valeur, dec) + ' ' + unite : signe(e.valeur, dec);
      ligne.appendChild(el('span', 'rf-casc-val', txt));
      if (e.fourchette) infobulle(ligne, {titre: e.cause,
        lignes: [['Fourchette', signe(e.fourchette[0], 0) + ' à ' + signe(e.fourchette[1], 0) + ' ' + unite]],
        note: 'Dépend du moment où le passage calage → production a été saisi.'});
      bloc.appendChild(ligne);
    });
    return bloc;
  }

  // ── Table des paramètres ───────────────────────────────────────────
  function tableParametres(lignes) {
    var wrap = el('div', 'rf-table-wrap');
    var t = el('table', 'rf-table');
    var th = el('tr');
    ['Paramètre', 'Devisé', 'Réel', 'Fourchette', 'Source'].forEach(function (c, i) {
      th.appendChild(el('th', i > 0 && i < 3 ? 'rf-num' : '', c));
    });
    t.appendChild(th);
    (lignes || []).forEach(function (l) {
      var tr = el('tr', l.modifie ? 'rf-modifie' : '');
      var dec = l.unite === '€/m²' ? 4 : 0;
      tr.appendChild(el('td', '', l.parametre));
      tr.appendChild(el('td', 'rf-num', l.devis == null ? '—' : nb(l.devis, dec) + ' ' + l.unite));
      tr.appendChild(el('td', 'rf-num rf-reel', l.reel == null ? '—' : nb(l.reel, dec) + ' ' + l.unite));
      tr.appendChild(el('td', 'rf-num rf-muted', l.fourchette || ''));
      tr.appendChild(el('td', 'rf-muted', l.source || ''));
      t.appendChild(tr);
    });
    wrap.appendChild(t);
    return wrap;
  }

  // ── Fiche ──────────────────────────────────────────────────────────
  function dessiner(f) {
    var racine = el('div', 'rf-fiche');
    if (!f || f.etat === 'sans_devis' || f.etat === 'sans_chiffrage' || f.etat === 'sans_mesure') {
      racine.appendChild(el('div', 'rf-vide', (f && f.message) || 'Rentabilité non disponible.'));
      return racine;
    }

    var tete = el('div', 'rf-tete');
    var v = VERDICT[(f.verdict || {}).global];
    tete.appendChild(el('span', 'rf-verdict rf-' + (v ? v.cls : 'neutre'), v ? v.lib : 'Verdict non calculable'));
    if (f.etat === 'a_verifier') {
      tete.appendChild(infobulle(el('span', 'rf-etat rf-etat-bad', 'À vérifier'),
        {titre: 'Résultat hors norme', note: (f.hors_norme || []).join(', ')
          + ' : facture ou matière probablement rattachée au mauvais dossier.'}));
    } else if (f.etat === 'provisoire') {
      var raison = (f.manque && f.manque.length) ? 'il manque : ' + f.manque.join(', ')
        : 'marché partiellement facturé';
      tete.appendChild(infobulle(el('span', 'rf-etat', 'Provisoire'),
        {titre: 'Provisoire', note: raison.charAt(0).toUpperCase() + raison.slice(1)}));
    } else {
      tete.appendChild(infobulle(el('span', 'rf-etat rf-etat-ok', 'Complet'),
        {titre: 'Complet', lignes: [['Production', 'terminée'], ['Matière', 'déstockée'], ['Facture', 'RVGI']]}));
    }
    racine.appendChild(tete);

    var modifies = (f.parametres || []).filter(function (l) { return l.modifie; });
    if (modifies.length) {
      var chg = el('div', 'rf-changes');
      modifies.forEach(function (l) {
        var c = el('span', 'rf-chg');
        c.appendChild(el('span', '', l.parametre + ' '));
        c.appendChild(el('s', 'rf-muted', nb(l.devis, l.unite === '€/m²' ? 4 : 0)));
        c.appendChild(el('b', '', ' → ' + nb(l.reel, l.unite === '€/m²' ? 4 : 0) + ' ' + l.unite));
        chg.appendChild(c);
      });
      racine.appendChild(chg);
    }

    var r = f.reel || {}, d = f.devis_calcul || {}, s = f.seuils || {};
    var jauges = el('div', 'rf-jauges');
    jauges.appendChild(jauge('Marge brute', r.mb_pct, d.mb_pct, s.mb_pct, '%', 1, 10));
    jauges.appendChild(jauge('Coût horaire', r.cout_horaire, d.cout_horaire, s.cout_horaire, '€/h', 0, 100, 0));
    racine.appendChild(jauges);

    if (f.redevise && Math.abs(f.redevise.non_refacture) >= 1) {
      racine.appendChild(el('div', 'rf-redevise',
        'Avec la laize réelle, le devis aurait chiffré ' + nb(f.redevise.prix_vente) + ' € : '
        + nb(f.redevise.non_refacture) + ' € n\'ont pas été refacturés.'));
    }

    var cascades = el('div', 'rf-cascades');
    cascades.appendChild(cascade('Marge brute, du devis au réel', f.cascade_marge, '€', 0));
    cascades.appendChild(cascade('Coût horaire, du devis au réel', f.cascade_cout_horaire, '€/h', 0));
    racine.appendChild(cascades);
    var leg = el('div', 'rf-legende');
    [['decision', 'Décision (laize, matière)'], ['atelier', 'Atelier'],
     ['logistique', 'Logistique, prix'], ['gain', 'Gain']].forEach(function (x) {
      var i = el('span', 'rf-leg');
      i.appendChild(el('i', 'rf-nat-' + x[0]));
      i.appendChild(document.createTextNode(x[1]));
      leg.appendChild(i);
    });
    racine.appendChild(leg);

    (f.alertes || []).forEach(function (a) {
      racine.appendChild(el('div', 'rf-alerte rf-alerte-' + (a.niveau || 'info'), a.message));
    });

    racine.appendChild(tableParametres(f.parametres));
    return racine;
  }

  function monter(conteneur, entryId) {
    if (!conteneur) return;
    conteneur.textContent = '';
    conteneur.appendChild(el('div', 'form-section-title', 'Rentabilité'));
    var corps = el('div', 'rf-attente', 'Calcul de la rentabilité…');
    conteneur.appendChild(corps);
    api('/api/rentabilite/planning/' + Number(entryId) + '/fiche').then(function (f) {
      if (!conteneur.isConnected) return;
      corps.replaceWith(dessiner(f));
    }).catch(function () {
      if (!conteneur.isConnected) return;
      corps.className = 'rf-vide';
      corps.textContent = 'Rentabilité indisponible — réessayer en rouvrant le dossier.';
    });
  }

  window.MySifaRentFiche = {monter: monter, dessiner: dessiner, infobulle: infobulle};
})();
